import os
import json
import operator
from log.logger import logger
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.tools import tool
from langgraph.types import Command, RetryPolicy, default_retry_on
from langchain_groq import ChatGroq
from agents.main_agent import KEYWORD_FIELDS, COLLECTION, KeywordFilterInput, SemanticFilterInput, embedding_model, build_filter_string, FinalAnswerInput, FilterArgs
from langgraph.graph import StateGraph, START, END
from typing import Literal, Optional, Dict, TypedDict, List, Any, Annotated
from langchain.messages import SystemMessage, HumanMessage, ToolMessage, AnyMessage
from collection.search.search_collection import search_collection
from config.typesense_client import TS_CLIENT

load_dotenv()

# this goes in the models.py file
classify_intent_schema = {
    "title": "ClassifyIntent",
    "type": "object",
    "description": "Intent classifier",
    "properties": {
        "intent": {
            "type": "string",
            "description": "The intent classification of the user. `search` or `direct`",
            "enum": ["search", "direct"]
        }
    },
    "required": ["intent"] 
}
    
# product_review_schema = {
#     "type": "object",
#     "description": "Analysis of a product review.",
#     "properties": {
#         "rating": {
#             "type": ["integer", "null"],
#             "description": "The rating of the product (1-5)",
#             "minimum": 1,
#             "maximum": 5
#         },
#         "sentiment": {
#             "type": "string",
#             "enum": ["positive", "negative"],
#             "description": "The sentiment of the review"
#         },
#         "key_points": {
#             "type": "array",
#             "items": {"type": "string"},
#             "description": "The key points of the review"
#         }
#     },
#     "required": ["sentiment", "key_points"]
# }


class SearchAgentState(TypedDict):
    # raw search data
    user_prompt: str
    classification: classify_intent_schema
    messages: Annotated[List[AnyMessage], operator.add]

# ============================


# this goes in the prompts.py file
CLASSIFICATION_PROMPT = """
You are an Intent classifier for a Halal Searching Platform which has a search engine capable of performing a search over a database of 200K+ halal related products. Analyze the user's prompt and classifiy whether the user wants to search for any halal product(s) or not. 
If the user wants to search, **JUST** output `search`, otherwise if the prompt is a greeting, non-search query, **JUST** output `direct`

## EXAMPLES:
user_prompt: Are all chocolates halal?
classification: search

user_prompt: Is creme brule halal?
classification: search

user_prompt: I was wondering whether I can find some good biryani in NewYork or not?
classification: search

user_prompt: What is halal?
classification: direct

user_prompt: How are you doing? What are your specialities?
classification: direct

user_prompt: I want to find some delicious dishes of rice in Thailand
classification: search
"""


SEARCH_PROMPT = """
You are Halalify's intelligent product search assistant with access to a database of 200,000+ halal-certified products (food items, ingredients, additives, manufactured goods, creams, cosmetics or any type of halal product).

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
"""

FINAL_RESPONSE_PROMPT = """
You are **Halalify**, a Search & Conversational Assistant. You provide halal search services by searching over a Halal verified product database of 200K+ products. You deal with user queries related to a broad spectrum of Halal-related products including but **NOT** limited to food, beverages, cosmetics, tourism and chemicals. 

**STRICT GUIDELINES:**
- You do not deal with irrelevant queries which are outside your scope. 
- If user asks or prompts something irrelevant, politely inform him of your specific role. 
- Be polite, conversational, and assist users in their halal search.

## INPUTS
1. User Prompt: str (The actual user's prompt)
2. Halal Search results: list (The list of halal products retrieved from the search). This is an optional field and can be None or empty. 

The search results can contain relevant and/or irrelevant products relative to the user's prompt. Your job is to extract the relevant products into a structured format. 

**OUTPUT FIELDS**
- `response` — Your natural language message to the user
- `products` — Product objects you select from the search results to show the user. Pick the most relevant ones. **Maximum 10** unless the user explicitly asks for more. Pass an empty list if no products were found or the query is irrelevant. Only include products returned by the search tools — **DO NOT** fabricate or modify product data.

## RESPONSE FORMAT (for response field)

**If products were found:**
- 1 product → "Here is the relevant product I found for you."
- 2+ products → "Here are the relevant products I found for you."

**If no products were found:** Politely inform the user, suggest to try searching again with different keywords, terms or check for typos.
**If irrelevant query:** Politely inform the user you only assist with halal product searches.
"""
# ============================


# this goes in the tools file
@tool(args_schema=KeywordFilterInput)
def KeywordFilterSearch(keyword_args: Optional[Dict] = None, filter_args: Optional[FilterArgs] = None) -> List[Dict]:

    """
    Searches halal products by keyword matching across product name, companies, health info, "
            "and typical uses, with optional exact filters. Use when specific product names, brand names, "
            "or keyword terms are mentioned. Also use when only exact filters are provided (keyword_args=null).
    """
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


@tool(args_schema = SemanticFilterInput)
def SemanticFilterSearch(semantic_query: str, filter_args: Optional[FilterArgs] = None) -> List[Dict]:

    """
    "Searches halal products by semantic/vector similarity for conceptual or descriptive queries "
    "like 'good for diabetics' or 'natural red food coloring'. Accepts optional exact filters."
    """
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


# ============================


GROQ_API_KEY = os.getenv('GROQ_API_KEY')


if not GROQ_API_KEY:
    raise ValueError("Invalid GROQ API KEY")


extracter_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "llama-3.1-8b-instant",
    temperature = 0,
    max_tokens = 100
)

final_extracter_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "openai/gpt-oss-20b",
    temperature = 0,
)

standard_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "openai/gpt-oss-120b",
    temperature = 0,
)


def classify_intent(state: SearchAgentState) -> Command[Literal["search_node", "response_node"]]:
    """Use an llm to classify user's intent from prompt"""

    structured_llm = extracter_llm.with_structured_output(classify_intent_schema)
    messages = [SystemMessage(CLASSIFICATION_PROMPT), HumanMessage(state['user_prompt'])]
    classification = structured_llm.invoke(messages)
    logger.info(f"Classification: {classification['intent']}")
    if classification["intent"] == "search":
        goto = "search_node"
    elif classification["intent"] == "direct":
        goto = "response_node"

    return Command(
        update = {
            "classification": classification,
        },
        goto = goto
    )


# search tools
search_tools = [KeywordFilterSearch, SemanticFilterSearch]
search_tools_by_name = {tool.name: tool for tool in search_tools}

def search_node(state: SearchAgentState) -> dict:
    """Searches TypeSense to retrieve relevant halal products
    Two core components:
    1. Keyword + Filter based search
    2. Semantic + Filter based search
    """

    llm_with_tools = standard_llm.bind_tools(search_tools)
    result = llm_with_tools.invoke([SystemMessage(SEARCH_PROMPT)] + state['messages'])
    return {
        "messages": [result]
    }

def tool_node(state: SearchAgentState) -> dict:
    """Performs the tool call"""
    if not state["messages"][-1].tool_calls:
        return {"messages": []}
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = search_tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call['args'])
        result.append(ToolMessage(content=json.dumps(observation), tool_call_id = tool_call["id"]))
    return {"messages": result}


def response_node(state: SearchAgentState) -> dict:
    """Formats the final user-facing response"""
    
    structured_llm = final_extracter_llm.with_structured_output(FinalAnswerInput)
    messages = [SystemMessage(FINAL_RESPONSE_PROMPT)] + state['messages']
    result = structured_llm.invoke(messages)
    
    # return the result
    return {
        "messages": [result]
    }


workflow = StateGraph(SearchAgentState)
workflow.add_node(
    "classify_intent",
    classify_intent,
    retry_policy=RetryPolicy(max_attempts=3, retry_on=default_retry_on),

 )
workflow.add_node("search_node", search_node)
workflow.add_node("tool_node", tool_node, retry_policy=RetryPolicy(max_attempts=3, retry_on=default_retry_on))
workflow.add_node("response_node", response_node, retry_policy=RetryPolicy(max_attempts=3, retry_on=default_retry_on))

workflow.add_edge(START, "classify_intent")
workflow.add_edge("search_node", "tool_node")
workflow.add_edge("tool_node", "response_node")
workflow.add_edge("response_node", END)

search_agent = workflow.compile()


def search_halal_products(query):
    try:
        result = search_agent.invoke({"user_prompt": query, "messages": [HumanMessage(query)]})
        result = result["messages"][-1]
        print(f"""{'='*25} RESPONSE {'='*25}
        {result.response}
        """)
        format_results(result.products)
    except Exception as e:
        logger.error(f"Some error occured while searching for halal products: {e}")


def format_results(product_list: list) -> str:
    for i, product in enumerate(product_list, 1):
        print(f"{i}. Product name: {product.norm_name} Companies: {' '.join(product.companies)} Certified By: {' '.join(product.cert_bodies)}") 


while True:
    query = input("Enter your halal search query here: ")
    if query == "exit":
        break
    search_halal_products(query)
