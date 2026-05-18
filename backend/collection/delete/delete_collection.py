from config.typesense_client import TS_CLIENT
from log.logger import logger

def delete_collection(collection_name: str):
    if not collection_name:
        raise ValueError("Collection name not provided")
    try:
        TS_CLIENT.collections[collection_name].delete()
    except Exception as e:
        logger.error(f"Some error occured while deleting the collection, Error: {e}")

delete_collection("halal_products")