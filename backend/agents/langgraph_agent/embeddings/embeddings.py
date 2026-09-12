import os

from dotenv import load_dotenv
from langchain_fireworks import FireworksEmbeddings

load_dotenv()

FIREWORKS_API_KEY = os.getenv("FIREWORKS_AI_API_KEY")

if not FIREWORKS_API_KEY:
    raise ValueError("No Fireworks key found.")

embedding_model = FireworksEmbeddings(
    api_key=FIREWORKS_API_KEY,
    model="accounts/fireworks/models/qwen3-embedding-8b",
)
