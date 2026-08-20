import operator
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from langchain.messages import AnyMessage
from typing import List, TypedDict, Annotated, Literal


# main search agent state
class SearchAgentState(TypedDict):
    # raw search data
    user_prompt: str
    search_results: Annotated[List[dict], operator.add]
    messages: Annotated[List[AnyMessage], operator.add]
    search_call_iterations: int

    # --- tool ladder + matched/relevant split ---
    classification: Optional[str]    # "search" | "direct" (set by classify_intent)
    tools_called: Annotated[List[str], operator.add]  # tool names run, in order
    first_tool: Optional[str]        # tool the first search call chose (sets the ladder + budget)
    keyword_params: Optional[dict]   # latest KeywordFilterSearch keyword_args (what the user wants)
    filters: Optional[dict]          # latest KeywordFilterSearch filter_args
    current_pool: List[dict]         # raw results of the latest tool call (judge input; never sent whole to an LLM)
    matched: List[dict]              # exact matches / variants (magnified in the UI)
    relevant: List[dict]             # similar-but-not-exact (diminished in the UI)

# classify intent schema
# The property name must stay in sync with CLASSIFICATION_PROMPT (which tells the model
# to emit `classification`) and with classify_intent in nodes/node.py (which reads it).
# with_structured_output(..., method='json_mode') parses the reply with a plain
# JsonOutputParser — it neither sends this schema to the provider nor validates against
# it — so the prompt is what actually shapes the reply and this schema documents it.
classify_intent_schema = {
    "title": "ClassifyIntent",
    "type": "object",
    "description": "Intent classifier",
    "properties": {
        "classification": {
            "type": "string",
            "description": "The intent classification of the user. `search` or `direct`",
            "enum": ["search", "direct"]
        }
    },
    "required": ["classification"]
}

class OutputSchema(BaseModel):
    canonical_id: Optional[str] = None
    norm_name: Optional[str] = None
    companies: Optional[List[str]] = None
    cert_bodies: Optional[List[str]] = None
    typical_uses: Optional[List[str]] = None
    marketplace: Optional[List[str]] = None
    category_l1: Optional[str] = None
    category_l2: Optional[str] = None
    halal_status: Optional[str] = None
    sold_in: Optional[List[str]] = None
    cert_numbers: Optional[List[str]] = None
    health_info: Optional[List[str]] = None
    source_ids: Optional[List[str]] = None
    source_files: Optional[List[str]] = None
    fda_numbers: Optional[List[str]] = None
    barcodes: Optional[List[str]] = None
    
    # Provenance: DB products are verified=True; web-fallback products are
    # verified=False and carry per-field grounding citations from Exa. These are
    # set deterministically in response_node, not by the LLM.
    verified: bool = True
    grounding: Optional[List[Dict[str, Any]]] = None

class WebSearchInput(BaseModel):
    query: str = Field(
        description=(
            "The web search query. Usually the product name/brand the user asked "
            "about. Use only after the database search tools found nothing relevant."
        )
    )

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

class SelectedProducts(BaseModel):
    """What the final LLM returns: a message plus the ids of the relevant
    products. The actual product objects are looked up by id in response_node
    (the LLM never re-emits product fields, avoiding mangling/hallucination)."""
    response: str = Field(
        description="Your natural language message to the user. Can't be none."
    )
    product_ids: List[str] = Field(
        default_factory=list,
        description=(
            "The canonical_id values of the products relevant to the user's query, "
            "copied verbatim from the [id: ...] of each candidate. Most relevant "
            "first, maximum 10. Empty list if nothing is relevant."
        ),
    )


class JudgeVerdict(BaseModel):
    """LLM-as-judge output: which candidate products exactly match the user's ask.
    The matched ids are validated against the candidate pool in judge_node."""
    reasoning: str = Field(
        ..., description="Step-by-step reasoning for the match decision."
    )
    matched_ids: List[str] = Field(
        default_factory=list,
        description=(
            "canonical_id of every candidate that is the SAME product the user "
            "asked for, or a variant of it. Copied verbatim from each candidate's "
            "`id:` line. Empty list if none match. Never invent or modify an id."
        ),
    )

class FinalResponse(BaseModel):
    """Response node output: only the natural-language message. Products are
    attached deterministically (already split into matched/relevant)."""
    response: str = Field(
        ..., description="Your natural language message to the user. Can't be none."
    )


# filter args model
class FilterArgs(BaseModel):
    # String fields
    category_l1: Optional[str] = None
    category_l2: Optional[str] = None
    halal_status: Optional[Literal["Halal", "Haram", "Haraam", "Mushbooh"]] = None
    
    # List fields. Like the string fields above these default to None, meaning "the LLM
    # did not supply this filter" — build_filter_string and KeywordFilterSearch both skip
    # falsy values, so None and [] are equivalent downstream. Consumers reading these
    # directly must still guard for None.
    sold_in: Optional[list[str]] = Field(None, description="Countries where product is sold")
    cert_bodies: Optional[list[str]] = Field(None, description="Certification bodies")
    cert_numbers: Optional[list[str]] = None
    fda_numbers: Optional[list[str]] = None
    barcodes: Optional[list[str]] = None
    marketplace: Optional[list[str]] = Field(None, description="Marketplaces like Amazon, eBay") 


class KeywordArgs(BaseModel):
    """Text-match keyword fields for KeywordFilterSearch. Both are optional — supply
    only what the user's query actually names."""
    norm_name: Optional[str] = Field(
        None,
        description=(
            "The product or ingredient name to text-match, reduced to its core terms "
            "(lowercase, brand removed). E.g. \"is Shan biryani masala halal?\" -> "
            "\"biryani masala\". Null if the query names no product or ingredient."
        ),
    )
    companies: Optional[List[str]] = Field(
        None,
        description=(
            "Brand or company names mentioned in the query, one per list item. "
            "E.g. [\"Shan\"], [\"Nestle\", \"Maggi\"]. Null if no brand is named."
        ),
    )


class KeywordFilterInput(BaseModel):
    keyword_args: Optional[KeywordArgs] = Field(
        None,
        description=(
            "Keyword text-match fields: norm_name (str) and companies (list[str]). "
            "Pass null if the query names no product/ingredient and no brand."
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


