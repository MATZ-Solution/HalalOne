from log.logger import logger
from langchain.tools import tool
from typing import Dict, Optional, List, Any
from config.typesense_client import TS_CLIENT
from ..embeddings.embeddings import embedding_model
from collection.search.search_collection import search_collection
from ..utils.utils import KEYWORD_FIELDS, COLLECTION, build_filter_string
from ..models.models import KeywordFilterInput, FilterArgs, SemanticFilterInput


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
