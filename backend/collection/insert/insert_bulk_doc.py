import os
import json
from log.logger import logger
from config.typesense_client import TS_CLIENT

# additional code for vector generation
from langchain_fireworks import FireworksEmbeddings

embedding_model = FireworksEmbeddings(api_key=os.getenv("FIREWORKS_AI_API_KEY", "fw_3ZmSsfu21ztf14QAbpRjTeDQ"), model = "accounts/fireworks/models/qwen3-embedding-8b")

with open("data/canonical_products_test.json", mode="r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    raise ValueError("Bulk data to be inserted not found!")

sliced_data = data[:1000]
concatenated_strings_array = []
for product in sliced_data:
    print(product["norm_name"])
    sentence = f"{product.get('norm_name', '')}. {', '.join(product.get('companies', []))}. {', '.join(product.get('typical_uses', []))}. {', '.join(product.get('health_info',[]))}"
    concatenated_strings_array.append(sentence or "")

embeddings_array = []
if concatenated_strings_array:
    embeddings_array = embedding_model.embed_documents(concatenated_strings_array)



new_product_array = []
if embeddings_array:
    for i,product in enumerate(sliced_data):
        product['embedding'] = embeddings_array[i]
        new_product_array.append(product)
with open("data/canonical_products_test.json", mode = "w", encoding="utf-8") as f:
    json.dump(new_product_array, f, indent=2, ensure_ascii=False)
# Add a confirmation message so you know it completed
print(f"Successfully saved {len(new_product_array)} products with embeddings to canonical_products_test.json")


def insert_bulk_docs(data: list[dict], collection_name: str):
    try:
        if not data:
            raise ValueError("Data to be inserted not found")
        if not collection_name:
            raise ValueError("No collection name given")
        logger.info(f"{'='*50} Initializing bulk documents insertion {'='*50}")
        TS_CLIENT.collections[collection_name].documents.import_(data, {'action': 'create'})
        logger.info("All documents inserted successfully!")
    except Exception as e:
        logger.error(f"Some error occured while bulk uploading documents, Error: {e}")

insert_bulk_docs(data, "halal_products")