from log.logger import logger
from config.typesense_client import TS_CLIENT
from llms.main_llm import invoke_llm
from collection.search.search_collection import search_collection


def search_products(query: str) -> list:
    if not query:
        return []
        
    response = invoke_llm(query)

    if not response:
        return []

    print(f'{"="*25} RESPONSE {"="*25}\n\n{response}')
    clean_args = {k: v for k, v in response.model_dump().items() if v is not None}

    if not clean_args:
        print("No valid search terms provided")
        return []

    FILTER_FIELDS = {
        "cert_numbers", "fda_numbers", "barcodes", "halal_status",
        "category_l1", "category_l2", "cert_bodies", "marketplace",
        "sold_in", "source_ids", "source_files",
    }

    filter_parameters = {k: v for k, v in clean_args.items() if k in FILTER_FIELDS}

    documents = []
    for k, v in clean_args.items():
        if k in FILTER_FIELDS:
            continue
        query = " ".join(v) if isinstance(v, list) else v
        documents = search_collection(
            query=query,
            query_by=k,
            collection_name="halal_products",
            filter_parameters=filter_parameters,
        )
        top_results = documents[:4] if documents else []
        if top_results:
            filter_parameters["canonical_id"] = [doc["canonical_id"] for doc in top_results]
        else:
            return []

    if documents:
        for i, doc in enumerate(documents, 1):
            print(f"Doc {i}, Product ID: {doc['canonical_id']} | Product Name: {doc['norm_name']} | Companies: {','.join(doc['companies'])}")

    return documents
