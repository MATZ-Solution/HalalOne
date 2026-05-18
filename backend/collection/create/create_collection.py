import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.typesense_client import TS_CLIENT
from models.product_model import model
from log.logger import logger

def create_collection():
    try:
        print(TS_CLIENT)
        logger.info(f"{'='*25}Initiated collection creation{'='*25}")
        TS_CLIENT.collections.create(model)
        logger.info(f"{'='*25}Successfully created collection!{'='*25}")
    except Exception as e:
        logger.error(f"Some error occured while creating collection, Error: {e}")
create_collection()
