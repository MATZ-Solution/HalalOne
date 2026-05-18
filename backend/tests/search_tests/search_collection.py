from config.typesense_client import TS_CLIENT


search_parameters = {
    "q": "melalucea",
    "query_by": "companies",
    "exclude_fields": "embedding",
}

results = TS_CLIENT.collections['halal_products'].documents.search(search_parameters)['hits']

print(f"Results: {results}")