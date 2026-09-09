import os
import typesense
from dotenv import load_dotenv

load_dotenv()

TS_CLIENT = None
TYPESENSE_HOST=os.getenv('TYPESENSE_HOST', 'localhost')
TYPESENSE_PORT=os.getenv('TYPESENSE_PORT', 8108)
TYPESENSE_PROTOCOL=os.getenv('TYPESENSE_PROTOCOL', 'http')
TYPESENSE_API_KEY=os.getenv('TYPESENSE_API_KEY', 'abcd')

try:
    TS_CLIENT = typesense.Client({
        'nodes': [{
            'host': TYPESENSE_HOST,  # For Typesense Cloud use xxx.a1.typesense.net
            'port': TYPESENSE_PORT,       # For Typesense Cloud use 443
            'protocol': TYPESENSE_PROTOCOL    # For Typesense Cloud use https
        }],
        'api_key': TYPESENSE_API_KEY,
        'connection_timeout_seconds': 10
    })
except Exception as e:
    raise ValueError(f"Some error occured while initializing TypeSense, Error: {e}")
