from config.typesense_client import TS_CLIENT
from log.logger import logger

def retrieve_collection_details(collection_name: str):
    try:
        logger.info("Retrieving collection details...")

        collection_details = TS_CLIENT.collections[collection_name].retrieve()

        print(f"{'='*50}\n{collection_details}\n{'='*50}")
    except Exception as e:
        logger.info(f"Collection retrieval failed, Error: {e}")



retrieve_collection_details("halal_products")

