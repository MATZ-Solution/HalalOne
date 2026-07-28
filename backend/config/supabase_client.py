import os
import asyncio
from supabase import create_async_client, AsyncClient
from dotenv import load_dotenv

load_dotenv()

_supabase: AsyncClient | None = None
_lock = asyncio.Lock()


async def get_supabase() -> AsyncClient:
    """Return a lazily-initialised async Supabase client (service role key).

    The client is created once and reused: its underlying httpx pool is bound to
    the running event loop, so every query/auth/storage call awaits directly on
    the loop — no thread offload. The service role key is required for
    auth.get_user() to validate JWTs.
    """
    global _supabase
    if _supabase is None:
        async with _lock:
            if _supabase is None:
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                if not url or not key:
                    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
                _supabase = await create_async_client(url, key)
    return _supabase
