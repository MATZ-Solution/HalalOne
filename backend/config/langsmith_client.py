import os
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

if not LANGSMITH_API_KEY:
    raise ValueError("LangSmith API KEY not provided")



_langsmith_client = None

def get_langsmith_client() -> Client:
    """Return an async langsmith client
    
    The client is created once and reused"""

    global _langsmith_client
    
    if _langsmith_client is None:
        _langsmith_client = Client(api_key=LANGSMITH_API_KEY)
    
    return _langsmith_client
