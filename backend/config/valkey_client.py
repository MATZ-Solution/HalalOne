import os
import asyncio
import valkey.asyncio as valkey
from dotenv import load_dotenv

load_dotenv()

_client: "valkey.Valkey | None" = None
_lock = asyncio.Lock()


async def get_valkey() -> "valkey.Valkey":
    """Return a lazily-initialised async Valkey client (pooled, str-decoded).

    `from_url` builds a connection pool for us; the client is created once and
    reused on the running event loop. Pinged on creation so a bad endpoint fails
    fast rather than deep inside the first request.
    """
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                # `or` (not getenv's default): VALKEY_URL is present-but-empty in
                # local .env files, and from_url("") raises.
                url = os.getenv("VALKEY_URL") or "redis://localhost:6379/0"
                client = valkey.Valkey.from_url(url, decode_responses=True)
                await client.ping()
                _client = client
    return _client


async def close_valkey() -> None:
    """Close the client and its pool (called on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
