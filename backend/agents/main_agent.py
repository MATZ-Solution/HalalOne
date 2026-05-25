import os
import uuid
import asyncio
import json
from typing import Literal, Optional, Dict, Any, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_fireworks import FireworksEmbeddings, ChatFireworks
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import InMemorySaver

from config.typesense_client import TS_CLIENT
from collection.search.search_collection import search_collection
from log.logger import logger
from models.agent_output import OutputSchema


load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────
COLLECTION = "halal_products"

KEYWORD_FIELDS = {"norm_name", "companies", "health_info", "typical_uses"}
FILTER_FIELDS = {
    "category_l1", "category_l2", "halal_status", "sold_in",
    "cert_bodies", "cert_numbers", "fda_numbers", "barcodes", "marketplace",
}

# ── Embedding model (same as used during document insertion) ──────────────────
embedding_model = FireworksEmbeddings(
    api_key=os.getenv("FIREWORKS_AI_API_KEY"),
    model="accounts/fireworks/models/qwen3-embedding-8b",
)


# filter args model
class FilterArgs(BaseModel):
    # String fields
    category_l1: Optional[str] = None
    category_l2: Optional[str] = None
    halal_status: Optional[str] = None
    
    # List fields (default to empty list instead of None for easier handling)
    sold_in: Optional[list[str]] = Field(None, description="Countries where product is sold")
    cert_bodies: Optional[list[str]] = Field(None, description="Certification bodies")
    cert_numbers: Optional[list[str]] = None
    fda_numbers: Optional[list[str]] = None
    barcodes: Optional[list[str]] = None
    marketplace: Optional[list[str]] = Field(None, description="Marketplaces like Amazon, eBay") 


# ── Helpers ───────────────────────────────────────────────────────────────────
def build_filter_string(filter_args: Optional[FilterArgs]) -> str:
    if not filter_args:
        return ""
    parts = []
    for k, v in filter_args.model_dump().items():
        if k not in FILTER_FIELDS:
            continue
        if isinstance(v, list):
            parts.append(f'{k}:=[{",".join(str(i) for i in v)}]')
        else:
            parts.append(f'{k}:="{v}"')
    return " && ".join(parts)


def format_results(docs: List[Dict]) -> str:
    if not docs:
        return "No products found."
    lines = []
    # return results from top4
    for doc in docs[:4]:
        companies = ", ".join(doc.get("companies", [])) or "N/A"
        lines.append(
            f"• [{doc['canonical_id']}] {doc.get('norm_name', 'N/A')}\n"
            f"  Status: {doc.get('halal_status', 'N/A')} | "
            f"Companies: {companies} | "
            f"Category: {doc.get('category_l1', '')} > {doc.get('category_l2', '')}"
        )
    return "\n".join(lines)


# ── Typesense search functions ────────────────────────────────────────────────
def _keyword_search(keyword_args: Optional[Dict], filter_args: Optional[Dict]) -> List[Dict]:
    logger.info(f"Raw Filters: {filter_args}")
    active_filters = {
        k: v for k, v in (dict(filter_args) if filter_args else {}).items()
        if v
    }
    valid = {k: v for k, v in keyword_args.items() if k in KEYWORD_FIELDS and v} if keyword_args else {}

    if not valid and active_filters:
        return search_collection(
            query="*",
            query_by="norm_name",
            collection_name=COLLECTION,
            filter_parameters=active_filters,
        )
    if not valid and not active_filters:
        return []
    logger.info(f"Keywords:\n {keyword_args}")
    logger.info(f"Filters:\n {active_filters}")
    documents = []
    for k, v in valid.items():
        query = " ".join(v) if isinstance(v, list) else v
        documents = search_collection(
            query=query,
            query_by=k,
            collection_name=COLLECTION,
            filter_parameters=active_filters,
        )
        top_results = documents if documents else []
        if top_results:
            active_filters["canonical_id"] = [doc["canonical_id"] for doc in top_results]
        else:
            return []

    return documents


def _semantic_search(semantic_query: str, filter_args: Optional[Dict]) -> List[Dict]:
    embedding = embedding_model.embed_query(semantic_query)
    embedding_str = ",".join(map(str, embedding))
    logger.info(f"Query: {semantic_query}")
    params: Dict[str, Any] = {
        "collection": COLLECTION,
        "q": "*",
        "vector_query": f"embedding:([{embedding_str}], k:10)",
        "per_page": 10,
        "exclude_fields": "embedding",
    }

    filter_str = build_filter_string(filter_args)
    if filter_str:
        params["filter_by"] = filter_str

    try:
        result = TS_CLIENT.multi_search.perform({"searches": [params]}, {})
        hits = result["results"][0].get("hits", [])
        return [h["document"] for h in hits] if hits else []
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return []




# ── Tool input schemas ────────────────────────────────────────────────────────
class KeywordFilterInput(BaseModel):
    keyword_args: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Keyword fields for text matching. Allowed keys: norm_name (str), companies (list[str]), "
            "health_info (list[str]), typical_uses (list[str]). Pass null if no keywords present."
        ),
    )
    filter_args: Optional[FilterArgs] = Field(
        None,
        description=(
            "Exact-match filters. Allowed keys: category_l1, category_l2, halal_status (str); "
            "sold_in, cert_bodies, cert_numbers, fda_numbers, barcodes, marketplace (list[str]). "
            "Pass null if no filters present."

        ),
    )


class SemanticFilterInput(BaseModel):
    semantic_query: str = Field(
        description=(
            "Natural language semantic query extracted from user intent. "
            "E.g. 'a calcium-rich snack for children', 'traditional Pakistani spice blend'."
        )
    )
    filter_args: Optional[FilterArgs] = Field(
        None,
        description="Same exact-match filters as KeywordFilterSearch. Pass null if no filters present.",
    )


# ── Tool implementations ──────────────────────────────────────────────────────
def keyword_filter_search(keyword_args: Optional[Dict], filter_args: Optional[Dict]) -> str:
    return json.dumps(_keyword_search(keyword_args, filter_args)[:10])


def semantic_filter_search(semantic_query: str, filter_args: Optional[Dict]) -> str:
    return json.dumps(_semantic_search(semantic_query, filter_args)[:10])


# ── FinalAnswer ───────────────────────────────────────────────────────────────
class FinalAnswerInput(BaseModel):
    response: str = Field(
        description="Your natural language message to the user. Can't be none"
    )
    products: List[OutputSchema] = Field(
        default_factory=list,
        description=(
            "Product objects selected from search results to show the user. "
            "Maximum 10 unless the user explicitly asks for more. "
            "Empty list if no products were found or the query is irrelevant."
        ),
    )


def final_answer(response: str, products: list) -> str:
    return "[DONE]"


tools = [
    StructuredTool.from_function(
        func=keyword_filter_search,
        name="KeywordFilterSearch",
        description=(
            "Searches halal products by keyword matching across product name, companies, health info, "
            "and typical uses, with optional exact filters. Use when specific product names, brand names, "
            "or keyword terms are mentioned. Also use when only exact filters are provided (keyword_args=null)."
        ),
        args_schema=KeywordFilterInput,
    ),
    StructuredTool.from_function(
        func=semantic_filter_search,
        name="SemanticFilterSearch",
        description=(
            "Searches halal products by semantic/vector similarity for conceptual or descriptive queries "
            "like 'good for diabetics' or 'natural red food coloring'. Accepts optional exact filters."
        ),
        args_schema=SemanticFilterInput,
    ),
    StructuredTool.from_function(
        func=final_answer,
        name="FinalAnswer",
        description=(
            "MUST be called as the absolute last action after all searches are complete "
            "(or when deciding not to search). Use this to submit your response text and "
            "the selected product results to the user."
        ),
        args_schema=FinalAnswerInput,
    ),
]


# ## IMAGE INPUT

# When the user sends an image, read visible product names, brand names, ingredient lists, certification labels, and halal logos. Extract any keyword or filter fields you can see, then call the appropriate search tool(s). If the image is unclear or unrelated to halal products, ask the user for a clearer photo.



# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Halalify's intelligent product search agent with access to a database of 200,000+ halal-certified products (food items, ingredients, additives, manufactured goods, creams, cosmetics or any type of halal product). You are a conversational-style assistant, but don't entertain queries that aren't related to halal products search.

## PRODUCT SCHEMA

**Keyword-searchable fields** (used for text matching):
| Field        | Type      | Description                              |
|--------------|-----------|------------------------------------------|
| norm_name    | string    | Normalized product name                  |
| companies    | string[]  | Manufacturer or brand names              |
| health_info  | string[]  | Health effects, warnings, and notes      |
| typical_uses | string[]  | Common usage contexts of the product     |

**Exact-filterable fields** (used for precise constraints):
| Field         | Type      | Example Values                              |
|---------------|-----------|---------------------------------------------|
| category_l1   | string    | "Food", "Additive", "Ingredient"            |
| category_l2   | string    | "Colorant", "Beverage", "Preservative"      |
| halal_status  | string    | "Halal", "Haram", "Mushbooh"               |
| sold_in       | string[]  | ["Pakistan", "UAE"]                         |
| cert_bodies   | string[]  | ["HFCI India", "SANHA South Africa"]        |
| cert_numbers  | string[]  | Certification reference numbers             |
| fda_numbers   | string[]  | FDA registration numbers                    |
| barcodes      | string[]  | Product barcodes                            |
| marketplace   | string[]  | ["Amazon", "Daraz"]                         |

## TOOL SELECTION RULES

Analyze the user's query and follow these rules strictly:

1. **Keywords only, no filters** → `KeywordFilterSearch(keyword_args={{...}}, filter_args=null)`
2. **Filters only, no keywords** → `KeywordFilterSearch(keyword_args=null, filter_args={{...}})`
3. **Pure semantic/conceptual query** → `SemanticFilterSearch(semantic_query="...", filter_args=null)`
4. **Semantic query + filters** → `SemanticFilterSearch(semantic_query="...", filter_args={{...}})`
5. **Keywords + semantic content + filters** → Call `KeywordFilterSearch` first; if the result is "No products found.", then call `SemanticFilterSearch` with the semantic portion and filters
6. **Irrelevant query** → Do NOT call any search tool. Call `FinalAnswer` directly with an empty products list and a polite response.

## CLASSIFICATION GUIDE

- **Keyword** = explicit product name, brand/company, known ingredient, or specific use mentioned directly. If a product name OR company name is explicitly mentioned, ALWAYS call `KeywordFilterSearch` first regardless of how the question is phrased.
- **Filter** = a category, certification body, halal status, barcode, location, or marketplace constraint
- **Semantic** = conceptual or descriptive intent (e.g. "good for bone health", "natural sweetener for diabetics"). Directly call the `SemanticFilterSearch`.
- **Irrelevant** = greetings, general questions, non-halal-product topics

## STRICT EXTRACTION RULES

- Only populate tool arguments with information **explicitly stated** in the user's query.
- Do NOT assume, infer, or fill in fields that are not directly mentioned.
- If a field's value is not present in the query, pass `null` for that field.
- Example: "is biryani masala halal?" → `norm_name = "biryani masala"`, all other fields `null`. Do NOT assume `category_l1 = "Food"` or for any other field.

## FILTER NORMALIZATION & TYPO HANDLING

Before passing any filter value to a tool, normalize it:

**`halal_status`** — only valid values are `"Halal"`, `"Haram"`, `"Mushbooh"`. Map common variants:
- "halal", "hlal", "hallal" → `"Halal"`
- "haram", "hraam", "haraam" → `"Haram"`
- "mushbooh", "mashbooh", "musbooh", "doubtful", "questionable" → `"Mushbooh"`

**`sold_in` / `marketplace` / `cert_bodies`** — correct obvious geographic or name typos:
- "pakstan", "pakistaan" → `"Pakistan"`
- "middeleast", "middle east", "middleeast" → `"Middle East"`
- "uae", "dubai" → `"UAE"`
- Apply similar common-sense corrections for other values.

**`category_l1` / `category_l2`** — capitalise correctly (e.g. "food" → `"Food"`, "additive" → `"Additive"`).

**If the typo or value is too ambiguous to correct confidently** — do NOT call any tool. Instead ask the user to clarify that specific field before proceeding.

## MANDATORY FINAL STEP

After completing all searches — or deciding not to search — you MUST call `FinalAnswer` as your absolute last action. Never skip this step.

**FinalAnswer fields:**
- `response` — Your natural language message to the user (follow the Response Format below)
- `products` — Product objects you select from the search results to show the user. Pick the most relevant ones. **Maximum 10** unless the user explicitly asks for more. Pass an empty list if no products were found or the query is irrelevant. Only include products returned by the search tools — do not fabricate or modify product data.

After the `FinalAnswer` tool call completes, output exactly: [DONE]

## RESPONSE FORMAT (for FinalAnswer.response)

**If products were found:**
- 1 product → "Here is the relevant product I found for you."
- 2+ products → "Here are the relevant products I found for you."

**If no products were found:** Explain why results may be missing and suggest how the user could refine their query.
**If irrelevant query:** Politely inform the user you only assist with halal product searches."""



llm = ChatFireworks(
    model="accounts/fireworks/models/kimi-k2p5",
    api_key=os.getenv("FIREWORKS_AI_API_KEY"),
    temperature=0,
)

# llm = ChatGroq(
#     model="meta-llama/llama-4-scout-17b-16e-instruct",
#     api_key=os.getenv("GROQ_API_KEY"),
#     temperature=0,
# )

agent = create_agent(model= llm, system_prompt=SYSTEM_PROMPT, tools=tools, checkpointer=InMemorySaver())



# def build_image_user_content(text: str, base64: str, mime_type: str) -> list:
#     return [
#         {"type": "text", "text": text},
#         {
#             "type": "image_url",
#             "image_url": {
#                 "url": f"data:{mime_type};base64,{base64}"
#             }
#         },
#     ]


async def run_agent(query: str | list, config: dict = None) -> dict:
    content = query if isinstance(query, list) else query
    result = await asyncio.to_thread(
        agent.invoke,
        {"messages": [{"role": "user", "content": content}]},
        config=config or {"configurable": {"thread_id": str(uuid.uuid4())}}
    )
    messages = result["messages"]

    for msg in reversed(messages):
        for tc in getattr(msg, "tool_calls", []):
            if tc.get("name") == "FinalAnswer":
                args = tc.get("args", {})
                return {
                    "response": args.get("response", ""),
                    "documents": args.get("products", []),
                }

    return {"response": messages[-1].content if messages else "", "documents": []}


async def stream_agent(query: str | list, config: dict = None):
    content = query if isinstance(query, list) else query
    final_result = {"response": "", "documents": []}

    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": content}]},
        config=config or {"configurable": {"thread_id": str(uuid.uuid4())}},
        stream_mode="updates",
    ):
        for _node, node_data in chunk.items():
            for msg in node_data.get("messages", []):
                for tc in getattr(msg, "tool_calls", []):
                    name = tc.get("name", "")
                    args = tc.get("args", {})
                    if name == "KeywordFilterSearch":
                        has_keywords = bool(args.get("keyword_args"))
                        has_filters = bool(args.get("filter_args"))
                        if has_keywords:
                            message = "Searching keywords"
                        elif has_filters:
                            message = "Applying filters"
                        else:
                            message = "Searching relevant products"
                        yield {"type": "status", "message": message, "tool": name, "args": args}
                    elif name == "SemanticFilterSearch":
                        yield {"type": "status", "message": "Searching semantics", "tool": name, "args": args}
                    elif name == "FinalAnswer":
                        print("Final Response", args.get("response", "No response"))
                        print("Final products", args.get("products", []))
                        args = tc.get("args", {})
                        final_result = {
                            "response": args.get("response", ""),
                            "documents": args.get("products", []),
                        }

    yield {"type": "results", **final_result}