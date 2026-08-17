from config.typesense_client import TS_CLIENT
from log.logger import logger

STRING_ARRAY_FIELDS = {"companies", "typical_uses", "health_info"}

def search_collection(query: str, query_by: str, collection_name: str, filter_parameters: dict, limit: int = 10):
    try:
        if not query:
            raise ValueError("No query provided to search")
        if not query_by:
            raise ValueError("No fields provided to search against")
        if not collection_name:
            raise ValueError("No collection name provided")
        search_parameters = {
            'q': query,
            'query_by': query_by,
            "exclude_fields": "embedding",
            'limit': limit
        }
        if query_by not in STRING_ARRAY_FIELDS:
            search_parameters['drop_tokens_threshold'] = 0
        # initialize an empty documents array
        documents = []
        filter_string = ""
        if filter_parameters:
            for k,v in filter_parameters.items():
                if filter_string:
                    filter_string += " && "
                if isinstance(v, list):
                    quoted = ",".join(f'"{i}"' for i in v)
                    filter_string += f'{k}:=[{quoted}]'
                elif isinstance(v, str):
                    filter_string += f'{k}:="{v}"'
        if filter_string:
            search_parameters['filter_by'] = filter_string
        hits = TS_CLIENT.collections[collection_name].documents.search(search_parameters)["hits"]

        if not hits:
            print("[NO RESULTS FOUND]")
            return []
        for hit in hits:
            documents.append(hit["document"])
        # for i, hit in enumerate(hits, start=1):
        #     doc = hit['document']
        #     print(f"  [{i}] id={doc['canonical_id']} | name={doc.get('norm_name', '')[:60]}"
        #           f" | status={doc.get('halal_status', '')} | companies={doc.get('companies', [])[:2]}")
        return documents

    except Exception as e:
        logger.error(f"Some error occured while searching collection, Error: {e}")
        return []


# while True:
#     query = input("Please enter your cert_number to search cert numbers: ")
#     if query == "exit":
#         break
#     search_collection(query=query, query_by="norm_name", collection_name="halal_products")
