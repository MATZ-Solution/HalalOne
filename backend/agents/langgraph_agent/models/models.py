import operator
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from langchain.messages import AnyMessage
from typing import List, TypedDict, Annotated


# main search agent state
class SearchAgentState(TypedDict):
    # raw search data
    user_prompt: str
    search_results: List[dict]
    messages: Annotated[List[AnyMessage], operator.add]


# classify intent schema
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


