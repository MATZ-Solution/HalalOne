import uuid
from log.logger import log
from langsmith import traceable
from langchain.tools import tool
from .web_search import stream_web_search
from typing import Dict, Optional, List, Any
from config.typesense_client import TS_CLIENT
from langgraph.config import get_stream_writer
from ..embeddings.embeddings import embedding_model
from collection.search.search_collection import search_collection
from ..utils.utils import KEYWORD_FIELDS, COLLECTION, build_filter_string
from ..models.models import KeywordFilterInput, FilterArgs, SemanticFilterInput, WebSearchInput

@tool(args_schema=KeywordFilterInput)
def KeywordFilterSearch(keyword_args: Optional[Dict] = None, filter_args: Optional[FilterArgs] = None) -> List[Dict]:

    """Search halal products by keyword. USE THIS when the query names a specific
    product, brand/company, ingredient, health note, or use — anything concrete —
    or when the query is only exact filters (category, halal status, cert body,
    location, marketplace, barcode, etc.).

    Args:
      keyword_args: text-match fields. Keys: norm_name (str), companies (list[str]),
        health_info (list[str]), typical_uses (list[str]). Pass null if none.
        Example — "is Shan biryani masala halal?" → {"norm_name": "biryani masala",
        "companies": ["Shan"]}.
      filter_args: exact-match filters (category_l1/l2, halal_status; sold_in,
        cert_bodies, cert_numbers, fda_numbers, barcodes, marketplace). Pass null if none.
    """
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

    """Search halal products by semantic/vector similarity. USE THIS only when the
    query is conceptual or descriptive with NO specific product/brand named — e.g.
    "a calcium-rich snack for children", "natural red food colouring", "good for
    diabetics".

    Args:
      semantic_query: a natural-language phrase capturing the user's intent.
      filter_args: same exact-match filters as KeywordFilterSearch. Pass null if none.
    """
    embedding = embedding_model.embed_query(semantic_query)
    embedding_str = ",".join(map(str, embedding))
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
        log.error("tool.semantic_search.failed", error=str(e), error_type=type(e).__name__)
        return []


@tool(args_schema=WebSearchInput)
def WebSearch(query: str) -> List[Dict]:
    """Web search for a specific halal product, used only as a fallback
    when the database keyword search found no exact match. Streams the sources being
    searched to the client, then returns the product Exa synthesised (UNVERIFIED,
    with per-field grounding citations).

    Args:
      query: a natural-language web query, usually the product/brand the user asked
        about (e.g. "Barzula Turkish coffee halal status").
    """
    # Stream writer may be absent when the graph isn't run in streaming mode.
    try:
        writer = get_stream_writer()
    except Exception:
        writer = None

    product = None
    grounding: List[Dict] = []
    try:
        for event in stream_web_search(query):
            etype = event.get("type")
            if etype == "results" and writer:
                # Emit each source as a live loading message.
                for r in event.get("results", []):
                    writer({
                        "type": "web_source",
                        "url": r.get("url"),
                        "title": r.get("title"),
                        "favicon": r.get("favicon"),
                        "highlights": r.get("highlights") or [],
                    })
            elif etype == "done":
                output = event.get("output") or {}
                product = output.get("content")
                grounding = output.get("grounding") or []
    except Exception as e:
        log.error("tool.web_search.failed", error=str(e), error_type=type(e).__name__)
        return []

    if not product or not product.get("norm_name"):
        return []
    # Give the web product a stable id (like DB products) so response_node can
    # select it by id. The `halal_` prefix marks it as web-sourced.
    product["canonical_id"] = f"halal_{uuid.uuid4().hex[:8]}"
    product["verified"] = False
    product["grounding"] = grounding
    return [product]