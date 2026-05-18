from config.typesense_client import TS_CLIENT
from log.logger import logger

def retrieve_documents(collection_name: str):
    try:
        if not collection_name:
            raise ValueError("No collection name found.")
        logger.info(f"{'='*50} Retrieving documents {'='*50}")
        docs = TS_CLIENT.collections[collection_name].documents['9000'].retrieve()
        print(docs)
    except Exception as e:
        logger.error(f"Some error occured while retrieving collection documents, Error: {e}")

retrieve_documents(collection_name = "halal_products")