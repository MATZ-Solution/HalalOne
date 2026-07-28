import asyncio
import typesense

TS_CLIENT = None


try:
    TS_CLIENT = typesense.Client({
        'nodes': [{
            'host': 'localhost',  # For Typesense Cloud use xxx.a1.typesense.net
            'port': '8108',       # For Typesense Cloud use 443
            'protocol': 'http'    # For Typesense Cloud use https
        }],
        'api_key': 'abcd',
        'connection_timeout_seconds': 10
    })
except Exception as e:
    raise ValueError(f"Some error occured while initializing TypeSense, Error: {e}")
