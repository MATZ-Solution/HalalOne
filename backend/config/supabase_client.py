import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase: Client | None = None

def get_supabase() -> Client:
    """Return a lazily-initialised Supabase client using the service role key.
    The service role key is required for auth.get_user() to validate JWTs."""
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        _supabase = create_client(url, key)
    return _supabase
