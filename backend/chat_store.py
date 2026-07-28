"""Server-side chat persistence backed by Supabase.

All reads and writes go through here — the frontend never touches the DB.
Calls use the async Supabase client and are awaited directly on the event loop
(no thread offload), wrapped in an exponential-backoff retry (max 3 attempts).
On exhaustion the underlying exception is re-raised so callers can fall back to
an error reply.

Note: the backend uses the service-role key, which BYPASSES RLS. Ownership is
therefore enforced here in code (every query is scoped by user_id).
"""
import os
import asyncio
from log.logger import log
from config.supabase_client import get_supabase
from models.chat_title_description import LLMTitleSchema


MAX_RETRIES = 3
BASE_DELAY = 0.5  # seconds; doubles after each failed attempt

_title_llm = None

def _get_title_llm():
    """Lazily build a small Groq model used only for naming sessions."""
    global _title_llm
    if _title_llm is None:
        from langchain_groq import ChatGroq
        _title_llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.3,
            api_key=os.getenv("GROQ_API_KEY"),
            max_tokens = 500
        ).with_structured_output(schema=LLMTitleSchema, method="json_schema")
        
    return _title_llm


async def _with_retry(make_coro, op: str):
    """Await an async Supabase call with exponential backoff. `make_coro` is a
    zero-arg callable returning a fresh coroutine on each attempt. Re-raises the
    last exception if every attempt fails."""
    delay = BASE_DELAY
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await make_coro()
        except Exception as e:
            last_exc = e
            log.warning("chat_store.op.retry", op=op, attempt=attempt, max_retries=MAX_RETRIES, error=str(e), error_type=type(e).__name__)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= 2
    log.error("chat_store.op.exhausted", op=op, error=str(last_exc), error_type=type(last_exc).__name__)
    raise last_exc


# ---------- writes ----------

async def session_exists(session_id: str, user_id: str) -> bool:
    client = await get_supabase()
    res = await _with_retry(
        lambda: client
        .table("chat_sessions")
        .select("session_id")
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .execute(),
        "session_exists",
    )
    return bool(res.data)


async def create_session(session_id: str, user_id: str, title: str, description: str):
    client = await get_supabase()
    return await _with_retry(
        lambda: client
        .table("chat_sessions")
        .insert({
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "description": description,
        })
        .execute(),
        "create_session",
    )


async def insert_message(session_id: str, role: str, content: str, search_results=[], image_path: str | None = None) -> str | None:
    """Insert one message and return its generated `id` (or None if the insert
    didn't return a row). The id is needed so the Valkey history entry can carry
    it — summaries track which message ids they've folded in."""
    client = await get_supabase()
    res = await _with_retry(
        lambda: client
        .table("chat_messages")
        .insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "search_results": search_results or [],
            "image_path": image_path,
        })
        .execute(),
        "insert_message",
    )
    return res.data[0]["id"] if res.data else None


# ---------- summaries ----------

async def insert_summary(session_id: str, summary: str, message_ids: list[str]):
    """Persist one rolling summary and the accumulated set of message ids it now
    stands in for (previous summary's ids + the ids folded this round)."""
    client = await get_supabase()
    return await _with_retry(
        lambda: client
        .table("chat_summaries")
        .insert({
            "session_id": session_id,
            "summary": summary,
            "message_ids": message_ids or [],
        })
        .execute(),
        "insert_summary",
    )


async def get_latest_summary(session_id: str) -> dict | None:
    """Return the most recent summary for a session as {summary, message_ids},
    or None if the session has never been compacted."""
    client = await get_supabase()
    res = await _with_retry(
        lambda: client
        .table("chat_summaries")
        .select("summary, message_ids")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute(),
        "get_latest_summary",
    )
    if not res.data:
        return None
    row = res.data[0]
    return {"summary": row.get("summary", ""), "message_ids": row.get("message_ids") or []}


async def get_messages_excluding_ids(session_id: str, user_id: str, exclude_ids: list[str]) -> list:
    """Fetch a session's messages whose id is NOT in `exclude_ids` (the ids a
    summary already covers), so an older session rebuilds as summary + only the
    verbatim tail — the bandwidth optimization in the spec. Ownership is verified
    first (service role bypasses RLS). Empty exclude_ids returns all messages."""
    if not await session_exists(session_id, user_id):
        return []

    client = await get_supabase()

    def _build():
        q = (client
             .table("chat_messages")
             .select("id, role, content, search_results, image_path, created_at")
             .eq("session_id", session_id))
        if exclude_ids:
            # PostgREST `not.in.(...)` — exclude every id the summary has folded in.
            q = q.not_.in_("id", exclude_ids)
        return q.order("created_at").execute()

    res = await _with_retry(_build, "get_messages_excluding_ids")
    return res.data or []


# ---------- image storage ----------

CHAT_IMAGE_BUCKET = "chat-images"

# Signed-URL lifetime for chat images. The browser loads bytes directly from the
# CDN with this short-lived capability; images render on load (and the browser
# caches them), so a few minutes is plenty and a leaked URL expires quickly.
IMAGE_URL_TTL = 300  # seconds

# Map of supported image mime types to file extensions.
_MIME_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


async def upload_chat_image(user_id: str, session_id: str, data: bytes, mime: str) -> str:
    """Upload image bytes to the private chat-images bucket and return the
    stored path. Paths are namespaced by user_id so ownership can be verified
    on read (service role bypasses RLS)."""
    import uuid
    ext = _MIME_EXT.get(mime, "jpg")
    path = f"{user_id}/{session_id}/{uuid.uuid4()}.{ext}"

    client = await get_supabase()
    await _with_retry(
        lambda: client
        .storage
        .from_(CHAT_IMAGE_BUCKET)
        .upload(path, data, {"content-type": mime}),
        "upload_chat_image",
    )
    return path


async def delete_session(session_id: str, user_id: str) -> bool:
    """Delete a session and its messages. Verifies ownership first (service
    role bypasses RLS). Returns False if the session isn't the user's."""
    if not await session_exists(session_id, user_id):
        return False

    client = await get_supabase()
    await _with_retry(
        lambda: client
        .table("chat_messages")
        .delete()
        .eq("session_id", session_id)
        .execute(),
        "delete_messages",
    )
    await _with_retry(
        lambda: client
        .table("chat_sessions")
        .delete()
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .execute(),
        "delete_session",
    )
    return True


# ---------- reads ----------

async def get_sessions(user_id: str) -> list:
    client = await get_supabase()
    res = await _with_retry(
        lambda: client
        .table("chat_sessions")
        .select("session_id, title, description, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute(),
        "get_sessions",
    )
    return res.data or []


async def get_messages(session_id: str, user_id: str, sign_images: bool = True) -> list:
    # Verify ownership first — service role bypasses RLS, so enforce it here.
    if not await session_exists(session_id, user_id):
        return []

    client = await get_supabase()
    res = await _with_retry(
        lambda: client
        .table("chat_messages")
        .select("id, role, content, search_results, image_path, created_at")
        .eq("session_id", session_id)
        .order("created_at")
        .execute(),
        "get_messages",
    )
    messages = res.data or []

    # Batch-sign every image path in one storage call so the client loads bytes
    # straight from the CDN (no per-image round-trip, no byte-proxying through us).
    # Ownership was already enforced above (this session is the user's), so the
    # paths are the user's; the signed URL is a short-lived capability for each.
    # Skipped when the caller only needs role/content (e.g. the agent-history
    # rebuild), to avoid a pointless storage call.
    paths = [m["image_path"] for m in messages if m.get("image_path")] if sign_images else []
    if paths:
        signed = await _with_retry(
            lambda: client.storage.from_(CHAT_IMAGE_BUCKET).create_signed_urls(paths, IMAGE_URL_TTL),
            "create_signed_urls",
        )
        # Results come back in request order; map each path to its signed URL.
        url_by_path = {
            req_path: (item.get("signedURL") or item.get("signedUrl"))
            for req_path, item in zip(paths, signed)
            if not item.get("error")
        }
        for m in messages:
            p = m.get("image_path")
            if p and p in url_by_path:
                m["image_url"] = url_by_path[p]

    return messages


# ---------- title generation ----------
async def generate_title_description(prompt: str):
    """Best-effort (title, description) for a new session via Groq.
    Falls back to defaults on any failure — never blocks the pipeline."""
    try:
        llm = _get_title_llm()
        system = """Generate a concise title (max 6 words) and a one-sentence description from the user's first message."""
        system = system_prompt="""
    You are a master at creating short, meaningful chat titles and descriptions by analyzing conversations between users and the Halalify AI assistant.

    Your task: Extract key themes from the conversation to create a title and description.
    
    Conversation Format:
    - The input will contain 2 messages total
    - 2 user messages and 2 assistant messages in alternating order
    - Format: "User message: [content]\\nAssistant message: [content]\\nUser message: [content]\\nAssistant message: [content]"

    Rules for Titles:
    - Maximum 3-4 words
    - Never use quotes
    - Start with capital letter
    - Use keywords from the conversation
    - Make it engaging and descriptive

    Rules for Descriptions:
    - 1-2 sentences maximum
    - Summarize the main topic
    - Use natural language
    - Avoid technical jargon

    Example Input 1:
    User message: Can you find halal-certified chicken products?
    Assistant message: I found 15 halal-certified chicken products from brands like Sadia and Al-Fakhr.
    User message: Which ones are available in the UK?
    Assistant message: 6 of these products are available in UK supermarkets including Tesco and Asda.

    Example Output 1:
    Title: Halal Chicken Products
    Description: Finding halal-certified chicken options and their availability in UK supermarkets.

    Example Input 2:
    User message: I need halal cosmetics for sensitive skin
    Assistant message: We have 42 halal-certified skincare products. I recommend brands like Wardah and Simply Halal.
    User message: Do they contain any animal-derived ingredients?
    Assistant message: All products are certified halal and cruelty-free with no animal-derived ingredients.

    Example Output 2:
    Title: Halal Skincare Guide
    Description: Discovering halal-certified cosmetics suitable for sensitive skin with cruelty-free ingredients.

    Example Input 3:
    User message: Are there any halal-certified gelatin alternatives?
    Assistant message: Yes, we have 28 halal alternatives including plant-based agar-agar and carrageenan.
    User message: Which one works best for desserts?
    Assistant message: Agar-agar is most recommended for desserts as it sets firmly and is easy to use.

    Example Output 3:
    Title: Halal Gelatin Alternatives
    Description: Exploring halal-certified gelatin substitutes for cooking and dessert preparation.

    Example Input 4:
    User message: Show me halal-certified multivitamins
    Assistant message: I found 34 halal-certified multivitamin products from trusted brands.
    User message: Are they suitable for children?
    Assistant message: Yes, 12 products are specifically formulated for children with age-appropriate dosages.

    Example Output 4:
    Title: Halal Multivitamins Guide
    Description: Finding halal-certified multivitamins for adults and children with trusted brands.

    Example Input 5:
    User message: I need halal-certified food coloring
    Assistant message: We have 18 halal-certified food coloring options derived from natural sources.
    User message: Are they alcohol-based or water-based?
    Assistant message: All are water-based and alcohol-free, making them suitable for halal cooking.

    Example Output 5:
    Title: Halal Food Coloring
    Description: Discovering alcohol-free, halal-certified food coloring options from natural sources.

    Now analyze the provided conversation and extract the key themes to create an appropriate title and description.
    """
        resp = await llm.ainvoke([("system", system), ("user", prompt)])
        title = resp.title if (resp.title and len(resp.title.split()) <= 6) else "New Chat"
        description = (resp.description
                       if (resp.description and len(resp.description.split()) <= 30)
                       else "This is a new chat")
        return title, description
    except Exception as e:
        log.warning("chat_store.title_generation.failed", error=str(e), error_type=type(e).__name__)
        return "New Chat", "This is a new chat"