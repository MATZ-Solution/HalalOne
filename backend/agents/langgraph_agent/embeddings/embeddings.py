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
# No timeout kwarg: FireworksEmbeddings builds its own internal openai.OpenAI
# client with no way to inject one (langchain_fireworks/embeddings.py), and a
# stray timeout= here would be silently dropped, not honored. Callers must
# bound embed_query/embed_documents themselves via
# asyncio.wait_for(asyncio.to_thread(embedding_model.embed_query, ...),
# timeout=EMBEDDING_TIMEOUT_S) — see config/timeouts.py.
