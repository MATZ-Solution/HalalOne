import os
import json
import asyncio
import base64
import contextlib
import chat_store
from datetime import datetime, timezone
from log.logger import logger, log
from log.process import logged_process
from structlog.contextvars import bind_contextvars
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from agents.main_agent import build_image_url
from llms.vision_llm import invoke_llm_with_image
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBaseModel
from agents.langgraph_agent.main_langgraph_agent import stream_agent, compact_session
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Header
from config.supabase_client import get_supabase
from config.valkey_client import get_valkey, close_valkey
from session_state import (
    reserve_pipeline, pipeline_lease, is_pipeline_inflight,
    load_history, seed_history, append_history, clear_history,
    load_summary, save_summary, clear_summary,
    load_compaction, save_compaction, clear_compaction,
    is_session_known, mark_session_known, clear_session_known,
    IDLE_COMPACTION,
)
from pubsub import publish_chunk, subscribe_user, close_pubsub
from rate_limit import (
    open_connection, close_connection,
    start_connection_sweeper, stop_connection_sweeper,
    allow_message, allow_user, try_consume_user_llm, try_consume_llm,
)
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately

load_dotenv(override=True)

# Base token count that triggers a compaction prompt. Effective trigger is this
# value x (1 + declines), capped at 3x; after the 3rd decline it is forced.
SUMMARY_TOKEN_THRESHOLD = int(os.getenv("SUMMARY_TOKEN_THRESHOLD", "3000"))

# User-facing compaction copy.
COMPACTION_ASK_MSG = "Your conversation has hit the token limit. Compact it to a summary to keep chatting smoothly?"
COMPACTION_ASK_DISCLAIMER = "Older messages are folded into a summary and your recent messages are kept. This can take a few moments."
COMPACTION_RUNNING_MSG = "History is being compacted, please wait…"
# Sent when a prompt/image arrives for a session that is waiting on a compaction
# decision or actively compacting.
COMPACTION_BUSY_RESULT = {"type": "results", "response": "Please resolve the compaction prompt before sending another message.", "documents": []}




# How long a graceful shutdown waits for in-flight pipelines to land their answers.
# Bounds how long a deploy can be held up; anything still running past it is
# abandoned. Only ever helps on a graceful stop (SIGTERM / Ctrl+C — i.e. deploys,
# rollouts, autoscale-down). A hard kill or a crash cannot be caught by anything,
# and this does not pretend to.
SHUTDOWN_DRAIN_TIMEOUT = float(os.getenv("SHUTDOWN_DRAIN_TIMEOUT", "30"))


async def _drain_pipelines() -> None:
    """Let in-flight answers finish and persist before this instance exits.

    Without it a deploy kills the agent mid-answer and the reply is never written
    to the DB — the same data loss a reload used to cause, just triggered by us
    instead of the user. Deploys are routine, so this is the common case, not an
    exotic one.
    """
    pending = list(_DETACHED_PIPELINES)
    if not pending:
        return
    log.info("shutdown.draining", pipelines=len(pending), timeout_s=round(SHUTDOWN_DRAIN_TIMEOUT))
    _done, still_running = await asyncio.wait(pending, timeout=SHUTDOWN_DRAIN_TIMEOUT)
    if still_running:
        log.warning("shutdown.drain_incomplete", still_running=len(still_running))
        for t in still_running:
            t.cancel()
        await asyncio.gather(*still_running, return_exceptions=True)
    else:
        log.info("shutdown.drained")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Connect + ping Valkey at boot so a bad endpoint fails fast; run the
    # connection-cap sweeper for this instance's lifetime; close the pool cleanly.
    await get_valkey()
    start_connection_sweeper()
    yield
    # Drain BEFORE tearing anything down: a finishing pipeline still needs Valkey
    # to append history, publish its answer, and release its lease.
    await _drain_pipelines()
    await stop_connection_sweeper()
    await close_valkey()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL"), "http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8000", "http://localhost:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sent in the normal "results" protocol whenever a required persistence/agent
# step fails after all retries.
ERROR_RESULT = {"type": "results", "response": "Some error occured, please try again", "documents": []}

# Sent when a session already has a write/pipeline in flight and the client
# submits another prompt/image for it — reject the duplicate instead of queuing
# a second run.
BUSY_RESULT = {"type": "results", "response": "Still processing your previous message, please wait a moment.", "documents": []}

# The only message types the socket accepts; anything else closes the connection.
VALID_MESSAGE_TYPES = {"chat_sessions", "chat_history", "delete_session", "prompt", "image", "run_with_fields", "compact_confirm", "compact_decline"}

# Max inbound WS message size (bytes). Sized to allow a base64 image (~1.33x the
# raw file) plus JSON overhead; oversized messages are dropped, not parsed.
MAX_MESSAGE_BYTES = int(os.getenv("RL_MAX_MESSAGE_BYTES", "16000000"))

# Sent when an inbound message exceeds MAX_MESSAGE_BYTES.
OVERSIZE_RESULT = {"type": "results", "response": "Your message is too large. Please try a smaller image.", "documents": []}

# Standardized payload for every in-band rate-limit rejection (per-user message
# rate, global LLM cap). `retry_after` is a hint in seconds.
def rate_limited(reason: str, retry_after: int) -> dict:
    return {"type": "rate_limited", "response": reason, "retry_after": retry_after}

MSG_RATE_REASON = "You're sending messages too quickly. Please retry shortly."
LLM_BUSY_REASON = "We're experiencing high load right now. Please retry shortly."
USER_LLM_REASON = "You've reached your request limit for now. Please wait a moment."


def _history_to_messages(history: list[dict], summary: str = "") -> list:
    """Agent-form {id, role, content} entries -> LangChain messages for the agent.
    A non-empty rolling summary is prepended as a SystemMessage so it flows into
    every node (classify/search/response all do [SystemMessage(prompt)] + messages)."""
    messages: list = []
    if summary:
        messages.append(SystemMessage(f"SUMMARY OF EARLIER CONVERSATION:\n{summary}"))
    messages.extend(
        HumanMessage(m.get("content", "")) if m.get("role") == "user" else AIMessage(m.get("content", ""))
        for m in history
    )
    return messages


def _rows_to_history(rows: list[dict]) -> list[dict]:
    """DB message rows -> agent-form history. Each entry carries its DB id so a
    fold knows which message ids it covers. Assistant content packs the response
    text plus its documents (the shape the agent emitted and expects back)."""
    history = []
    for r in rows:
        if r["role"] == "user":
            history.append({"id": r.get("id"), "role": "user", "content": r["content"]})
        else:
            # search_results is the new {matched, relevant} split OR (old rows) a
            # flat list. The agent only needs a merged blob, so flatten either shape.
            sr = r.get("search_results") or []
            documents = (sr.get("matched", []) + sr.get("relevant", [])) if isinstance(sr, dict) else sr
            history.append({"id": r.get("id"), "role": "assistant", "content": json.dumps({"response": r["content"], "documents": documents})})
    return history


# Pipelines that outlive the connection that started them. A reload disconnects
# the socket mid-answer, but the answer must still be computed and persisted, so
# these are deliberately NOT cancelled on disconnect — only held here so the event
# loop keeps a strong reference and they can't be garbage-collected mid-flight.
# Entries remove themselves on completion.
_DETACHED_PIPELINES: set[asyncio.Task] = set()


async def _session_exists_cached(session_id: str, user_id: str) -> bool:
    """session_exists, but short-circuited by a Valkey flag so the hot prompt path
    doesn't hit Supabase every turn. A cache miss falls back to the DB and, on a
    hit there, records the flag for next time. The flag is cleared on delete."""
    if await is_session_known(session_id):
        return True
    exists = await chat_store.session_exists(session_id, user_id)
    if exists:
        await mark_session_known(session_id)
    return exists


async def _load_context(session_id: str, user_id: str) -> tuple[str, list[dict]]:
    """Return (summary, history) for a session from the Valkey caches, rebuilding
    from the DB on a miss. The rebuild is the spec's bandwidth optimization: fetch
    the latest summary, then ONLY the messages whose id the summary doesn't cover."""
    history, summary_state = await asyncio.gather(
        load_history(session_id), load_summary(session_id)
    )

    if history is None:
        # Cache miss (older session / expiry): rebuild summary + verbatim tail.
        summary_row = await chat_store.get_latest_summary(session_id)
        summary_text = summary_row["summary"] if summary_row else ""
        covered_ids = summary_row["message_ids"] if summary_row else []
        rows = await chat_store.get_messages_excluding_ids(session_id, user_id, covered_ids)
        history = _rows_to_history(rows)
        await seed_history(session_id, history)
        await save_summary(session_id, summary_text, covered_ids)
        return summary_text, history

    summary_text = summary_state["summary"] if summary_state else ""
    return summary_text, history


async def _stream_and_persist(
    user_id: str,
    session_id: str,
    prompt: str,
    conversation_history: list,
    pending_user_persist: "asyncio.Task | None" = None,
):
    """Run the agent and land the final answer. Does NOT persist the user message —
    the caller has either already done that (paused-turn resume) or handed us a
    `pending_user_persist` task that writes it concurrently with generation.

    Publishes rather than writing to a socket: this runs detached from whichever
    connection asked for it, which may already be gone (reload) or may reconnect
    to a different instance. The assistant insert stays ordered after the user
    message (we await the pending write first) so DB order is correct; the Valkey
    history append is then done CONCURRENTLY with the publish, so the answer isn't
    gated on that write reaching Valkey.
    """
    try:
        async for chunk in stream_agent(prompt, conversation_history):
            if chunk.get("type") == "results":
                try:
                    response = chunk.get("response", "")
                    matched = chunk.get("matched") or []
                    relevant = chunk.get("relevant") or []
                    # Merged list for the agent context cache (the agent only needs
                    # the products as a flat blob); the DB keeps the split for display.
                    documents = chunk.get("documents") or (matched + relevant)
                    # Ensure the user message is written (and ordered) before the
                    # assistant one. Best-effort: a failed user write is logged but
                    # doesn't sink the answer we already generated.
                    if pending_user_persist is not None:
                        try:
                            await pending_user_persist
                        except Exception as e:
                            log.error("ws.user_message.persist_failed", error=str(e), error_type=type(e).__name__)
                    # Persist the matched/relevant split (frontend display source of
                    # truth). JSONB column, so no schema change.
                    msg_id = await chat_store.insert_message(session_id, "assistant", response, {"matched": matched, "relevant": relevant})
                    # Carry the DB id so a client that already loaded this message
                    # via chat_history can drop the duplicate instead of appending
                    # the same answer twice.
                    chunk = {**chunk, "message_id": msg_id}
                    # Publish and cache-append together — the user gets the answer
                    # without waiting on the Valkey round-trip.
                    await asyncio.gather(
                        append_history(session_id, "assistant", json.dumps({"response": response, "documents": documents}), msg_id),
                        publish_chunk(user_id, session_id, chunk),
                    )
                    
                    continue
                except Exception as e:
                    log.error("ws.assistant_message.persist_failed", error=str(e), error_type=type(e).__name__)
                    await publish_chunk(user_id, session_id, ERROR_RESULT)
                    return
            await publish_chunk(user_id, session_id, chunk)
    except Exception as e:
        log.error("ws.agent_stream.failed", error=str(e), error_type=type(e).__name__)
        await publish_chunk(user_id, session_id, ERROR_RESULT)
    finally:
        # Never strand the deferred user-message write: if the agent errored (or
        # yielded no results) it was never awaited above. Await it so the message
        # still lands and the task can't be garbage-collected mid-flight.
        if pending_user_persist is not None and not pending_user_persist.done():
            try:
                await pending_user_persist
            except Exception as e:
                log.error("ws.user_message.persist_failed", error=str(e), error_type=type(e).__name__)


async def _run_compaction(user_id: str, session_id: str) -> tuple[str, list[dict]]:
    """Mark the session compacting, fold it, and return (summary, kept) for the
    resumed turn. On summarizer failure, surface it and fall back to the full
    (un-compacted) context so the turn is never stranded."""
    await save_compaction(session_id, {"phase": "compacting", "declines": 0, "pending": None, "message": COMPACTION_RUNNING_MSG})
    await publish_chunk(user_id, session_id, {"type": "compaction_running", "message": COMPACTION_RUNNING_MSG})
    try:
        summary, kept, _did = await compact_session(session_id)
        await clear_compaction(session_id)
        await publish_chunk(user_id, session_id, {"type": "compaction_done"})
        return summary, kept
    except Exception as e:
        log.error("compaction.failed", session_id=session_id, error=str(e), error_type=type(e).__name__)
        await clear_compaction(session_id)
        await publish_chunk(user_id, session_id, {"type": "compaction_failed", "message": "Compaction failed; continuing without it."})
        return await _load_context(session_id, user_id)  # summary/history straight from Valkey


async def run_prompt_pipeline(session_id: str, user_id: str, prompt: str, image_bytes: bytes | None = None, image_mime: str | None = None):
    """Persist the user prompt, then either answer it, force a compaction first, or
    pause and ask the user to compact — depending on the token count and how many
    times they've declined.

    The agent's multi-turn context comes from the shared Valkey caches (summary +
    history), rebuilt from the DB on a miss, so any instance reconstructs it.
    """
    # 1) Assemble the agent's prior context. The existence check, the context
    #    caches, and the compaction state are all independent reads, so fire them
    #    concurrently instead of paying their round-trips in series.
    try:
        exists, (summary, history), state = await asyncio.gather(
            _session_exists_cached(session_id, user_id),
            _load_context(session_id, user_id),
            load_compaction(session_id),
        )
        
        if not exists:
            # Title generation is an LLM call: draw from the shared budget, and fall
            # back to defaults (never block the prompt) if it's exhausted.
            if await try_consume_llm():
                title, description = await chat_store.generate_title_description(prompt)
            else:
                title, description = "New Chat", "This is a new chat"
            await chat_store.create_session(session_id, user_id, title, description)
            await mark_session_known(session_id)
            # Push the new session so the sidebar shows it immediately (the client
            # only fetched the session list once on connect, before this existed).
            await publish_chunk(user_id, session_id, {
                "type": "session_created",
                "session": {
                    "session_id": session_id,
                    "title": title,
                    "description": description,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            })
            await clear_history(session_id)   # brand-new session: no prior context
            await clear_summary(session_id)
            await clear_compaction(session_id)
            summary, history, state = "", [], dict(IDLE_COMPACTION)
    except Exception as e:
        log.error("ws.session_context.load_failed", error=str(e), error_type=type(e).__name__)
        await publish_chunk(user_id, session_id, ERROR_RESULT)
        return

    # Build this turn in memory so the agent can start immediately, and persist the
    # user message OFF the critical path — the agent reads context from this
    # in-memory list, not from the DB/Valkey write. The write (and any image
    # upload) runs concurrently with generation; _stream_and_persist awaits it
    # before writing the assistant message so DB/Valkey ordering stays correct.
    async def _persist_user_turn() -> None:
        image_path = None
        if image_bytes:
            image_path = await chat_store.upload_chat_image(user_id, session_id, image_bytes, image_mime or "image/jpeg")
        uid = await chat_store.insert_message(session_id, "user", prompt, image_path=image_path)
        await append_history(session_id, "user", prompt, uid)

    persist_user_task = asyncio.create_task(_persist_user_turn())
    
    history.append({"id": None, "role": "user", "content": prompt})
    conversation_history = _history_to_messages(history, summary)

    # 2) Compaction gate. The effective trigger rises with each decline; after the
    #    3rd decline it's forced (no prompt). Under the trigger, answer normally.
    declines = int(state.get("declines", 0))
    effective_threshold = SUMMARY_TOKEN_THRESHOLD * min(1 + declines, 3)
    token_count = count_tokens_approximately(conversation_history)

    if token_count >= effective_threshold:
        # Both branches need the user turn durably in Valkey first: a fold reads
        # history from Valkey, and a paused turn must not lose the message.
        try:
            await persist_user_task
        except Exception as e:
            log.error("ws.user_message.persist_failed", error=str(e), error_type=type(e).__name__)
        if declines >= 3:
            # Forced: compact inline (same lease), then answer with summary + tail.
            summary, kept = await _run_compaction(user_id, session_id)
            conversation_history = _history_to_messages(kept, summary)
            await _stream_and_persist(user_id, session_id, prompt, conversation_history)
            return
        # Pause this turn: stash the prompt and ask. Returning releases the
        # pipeline lease; the phase gate blocks new prompts until the user
        # decides. compact_confirm / compact_decline resume from here.
        await save_compaction(session_id, {
            "phase": "awaiting", "declines": declines, "pending": {"prompt": prompt},
            "message": COMPACTION_ASK_MSG, "disclaimer": COMPACTION_ASK_DISCLAIMER,
        })
        await publish_chunk(user_id, session_id, {
            "type": "compaction_request", "message": COMPACTION_ASK_MSG, "disclaimer": COMPACTION_ASK_DISCLAIMER,
        })
        return

    await _stream_and_persist(user_id, session_id, prompt, conversation_history, pending_user_persist=persist_user_task)


async def resume_after_confirm(session_id: str, user_id: str):
    """User accepted compaction: fold, then answer the paused prompt with the fresh
    summary + recent tail."""
    state = await load_compaction(session_id)
    pending = state.get("pending")
    if not pending:
        # Nothing paused (already resolved / expired). Clear and no-op.
        await clear_compaction(session_id)
        await publish_chunk(user_id, session_id, {"type": "compaction_done"})
        return
    summary, kept = await _run_compaction(user_id, session_id)
    conversation_history = _history_to_messages(kept, summary)
    await _stream_and_persist(user_id, session_id, pending["prompt"], conversation_history)


async def resume_after_decline(session_id: str, user_id: str):
    """User declined: raise the trigger (2x, then 3x, then forced next time) and
    answer the paused prompt with the full, un-compacted context."""
    state = await load_compaction(session_id)
    pending = state.get("pending")
    if not pending:
        await clear_compaction(session_id)
        await publish_chunk(user_id, session_id, {"type": "compaction_done"})
        return
    declines = min(int(state.get("declines", 0)) + 1, 3)
    await save_compaction(session_id, {"phase": "idle", "declines": declines, "pending": None})
    await publish_chunk(user_id, session_id, {"type": "compaction_done"})
    summary, history = await _load_context(session_id, user_id)
    conversation_history = _history_to_messages(history, summary)
    await _stream_and_persist(user_id, session_id, pending["prompt"], conversation_history)


class ExtractImageRequest(PydanticBaseModel):
    base64: str
    mime_type: str = "image/jpeg"


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/extract-image")
async def extract_image_endpoint(req: ExtractImageRequest, authorization: str = Header(default="")):
    async with logged_process("http.extract_image"):
        # Authenticate BEFORE consuming the LLM budget, so an unauthenticated caller
        # can't drain the shared per-minute LLM budget (DoS via our own limiter).
        token = authorization.removeprefix("Bearer ").strip()
        try:
            client = await get_supabase()
            user_response = await client.auth.get_user(token)
            if not user_response.user:
                raise HTTPException(status_code=401, detail="Unauthorized")
            user_id = user_response.user.id
        except HTTPException:
            raise
        except Exception as e:
            log.warning("http.extract_image.auth_failed", error=str(e), error_type=type(e).__name__)
            raise HTTPException(status_code=401, detail="Unauthorized")
        # Now that the caller is known, correlate the rest of this action to them.
        bind_contextvars(user_id=user_id)

        # Per-user request rate (10/sec) → per-user LLM budget (shared, per minute) →
        # global LLM budget. One user can neither spam the endpoint nor dominate the
        # shared LLM budget.
        if not await allow_user(user_id, "extract-image"):
            raise HTTPException(status_code=429, detail="Too many requests, please slow down")
        if not await try_consume_user_llm(user_id):
            raise HTTPException(status_code=429, detail="You've reached your request limit for now, please wait a moment")
        if not await try_consume_llm():
            raise HTTPException(status_code=429, detail="High load, please retry shortly")
        image_url = build_image_url(req.base64, req.mime_type)
        if not image_url:
            raise HTTPException(status_code=400, detail="Invalid image data")
        for _ in range(3):
            try:
                print("invoking llm with image")
                result = await invoke_llm_with_image(image_url)
                if "error" not in result:
                    return {"fields": result}
            except Exception as e:
                print("Some error occured while invoking image llm", e)
                log.error("http.extract_image.failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=422, detail="Failed to extract image information")


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    # Validate the Supabase JWT before accepting the connection, and keep the
    # user id — every DB query is scoped to it (service role bypasses RLS).
    try:
        client = await get_supabase()
        user_response = await client.auth.get_user(token)
        if not user_response.user:
            await websocket.close(code=1008, reason="Unauthorized")
            return
        user_id = user_response.user.id
    except Exception as e:
        log.warning("ws.auth.failed", error=str(e), error_type=type(e).__name__)
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # Global connection cap (fleet-wide). Reject before accepting if we're at
    # capacity or coordination state (Valkey) is unavailable.
    conn_id = await open_connection()
    if conn_id is None:
        await websocket.close(code=1013, reason="Server at capacity, please retry later")
        return

    await websocket.accept()
    # One connection serves all of a user's sessions; the session id travels in
    # each message. All per-session state (conversation history, the in-flight
    # guard) now lives in Valkey, so nothing session-scoped is kept in this
    # process — another instance sees the same state.

    # Every chunk this user's pipelines produce — on ANY instance — arrives here.
    # Subscribed before the receive loop starts so a pipeline that finishes during
    # this connection's startup still reaches us.
    pubsub = await subscribe_user(user_id)

    async def forward_published():
        """Relay this user's published pipeline chunks to their socket. Chunks are
        already tagged with session_id; the client routes on it.

        Polls with get_message rather than iterating pubsub.listen(): a search can
        sit silent for tens of seconds while the LLM reasons, and a blocking read
        raises a socket read-timeout on that silence — which ends the listen()
        generator for good, so every later chunk (including the answer) is lost
        until the user reloads. get_message(timeout=...) instead returns None on an
        idle tick, and any transient read error is swallowed so the loop lives for
        the whole connection.
        """
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Idle read timed out / transient blip — keep waiting, don't die.
                logger.debug(f"[WS] pubsub read hiccup (continuing): {e}")
                continue
            if not message:
                continue
            try:
                await websocket.send_text(message["data"])
            except Exception:
                logger.debug("[WS] forward skipped (socket closed)")
                return

    forwarder = asyncio.create_task(forward_published())

    # Each incoming message is handled in its own task so the receive loop never
    # blocks (e.g. opening the history cupboard while a prompt streams). Duplicate
    # pipelines for one session are rejected fleet-wide by the Valkey in-flight
    # guard, so no per-process lock is needed.
    tasks: set[asyncio.Task] = set()

    async def safe_send(payload: dict):
        """Send JSON, tolerating an already-closed socket (background tasks may
        outlive the connection)."""
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception:
            logger.debug("[WS] send skipped (socket closed)")

    async def llm_admit() -> bool:
        """Gate an LLM-backed op: per-user budget first (fairness), then the global
        budget (capacity). Sends the matching rejection and returns False if blocked."""
        if not await try_consume_user_llm(user_id):
            await safe_send(rate_limited(USER_LLM_REASON, 30))
            return False
        if not await try_consume_llm():
            await safe_send(rate_limited(LLM_BUSY_REASON, 30))
            return False
        return True

    def spawn(coro, label: str, session_id: str | None = None) -> asyncio.Task:
        """Run a handler as a tracked background task. The wrapper restores the
        'not fire-and-forget' guarantees: exceptions are logged and reported to
        the client instead of vanishing on the Task object.

        `session_id` marks this as a PIPELINE handler: it is registered on the
        module-level set instead of the per-connection one, so a disconnect does
        not cancel it (see the receive loop's finally) and it survives long enough
        to persist its answer. Its errors are published, not socket-sent, because
        by the time they happen the asking connection may be gone.
        """
        detached = session_id is not None

        async def runner():
            try:
                await coro
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("ws.handler.failed", handler=label)
                if detached:
                    await publish_chunk(user_id, session_id, ERROR_RESULT)
                else:
                    await safe_send(ERROR_RESULT)

        t = asyncio.create_task(runner())
        registry = _DETACHED_PIPELINES if detached else tasks
        registry.add(t)
        t.add_done_callback(registry.discard)
        return t

    # --- per-session handlers ------------------------------------------------
    async def handle_chat_sessions():
        # Global read (lists all sessions) — no session lock needed, so this
        # stays responsive even while a prompt is streaming.
        async with logged_process("ws.chat_sessions", user_id=user_id):
            try:
                sessions = await chat_store.get_sessions(user_id)
            except Exception as e:
                log.error("ws.chat_sessions.failed", error=str(e), error_type=type(e).__name__)
                sessions = []
            await safe_send({"type": "chat_sessions", "sessions": sessions})

    async def handle_chat_history(requested_session_id: str):
        # Display-only: read the session's messages from the DB (the source of
        # truth) and send them. Also surface the current compaction phase so a
        # fresh load (or another instance) re-shows a pending prompt / running
        # alert — the same reason the client stashes in-flight state on switch.
        async with logged_process("ws.chat_history", user_id=user_id, session_id=requested_session_id):
            try:
                messages = await chat_store.get_messages(requested_session_id, user_id)
            except Exception as e:
                log.error("ws.chat_history.failed", error=str(e), error_type=type(e).__name__)
                messages = []
            compaction = await load_compaction(requested_session_id)
            # A pipeline may still be running for this session on some instance (the
            # user reloaded mid-answer). Tell the client so it can restore the spinner
            # instead of showing a prompt with no reply; the answer itself arrives over
            # the pub/sub channel when it lands.
            inflight = await is_pipeline_inflight(requested_session_id)
            await safe_send({
                "type": "chat_history",
                "session_id": requested_session_id,
                "messages": messages,
                "inflight": inflight,
                "compaction": {
                    "phase": compaction.get("phase", "idle"),
                    "message": compaction.get("message"),
                    "disclaimer": compaction.get("disclaimer"),
                },
            })

    async def handle_delete_session(target_session_id: str):
        async with logged_process("ws.delete_session", user_id=user_id, session_id=target_session_id):
            try:
                await chat_store.delete_session(target_session_id, user_id)
                status = "acknowledged"
                # Drop every Valkey cache for the session too.
                await clear_history(target_session_id)
                await clear_summary(target_session_id)
                await clear_compaction(target_session_id)
                await clear_session_known(target_session_id)
            except Exception as e:
                log.error("ws.delete_session.failed", error=str(e), error_type=type(e).__name__)
                status = "failed"
            await safe_send({
                "type": "delete_session",
                "session_id": target_session_id,
                "status": status,
            })

    async def handle_prompt(session_id: str, message: str, token: str):
        async with logged_process("ws.prompt", user_id=user_id, session_id=session_id):
            async with pipeline_lease(session_id, token):
                await run_prompt_pipeline(session_id, user_id, message)

    async def handle_image(session_id: str, base64_data: str, mime_type: str, user_prompt: str, token: str):
      async with logged_process("ws.image", user_id=user_id, session_id=session_id):
        async with pipeline_lease(session_id, token):
            try:
                image_url = build_image_url(base64_data, mime_type)
                if not image_url:
                    await publish_chunk(user_id, session_id, {"type": "results", "response": "Try uploading another image", "documents": []})
                    return
                response = {}
                success = False
                # add retry logic here
                for i in range(3):
                    try:
                        response = await invoke_llm_with_image(image_url)
                        error = response.get("error")
                        if error:
                            if i == 2:
                                await publish_chunk(user_id, session_id, {"type": "results", "response": response["error"], "documents": []})
                                success = False
                                break
                            continue
                        else:
                            success = True
                            break
                    except Exception as e:
                        log.error("ws.image.extract_failed", error=str(e), error_type=type(e).__name__)
                        if i == 2:
                            await publish_chunk(user_id, session_id, {"type": "results", "response": "Error occured while parsing image details, try again.", "documents": []})
                            success = False
                            break
                        continue
                if not success:
                    return
                parts = []
                # v can only be string or an array of strings
                for k, v in response.items():
                    if isinstance(v, list):
                        if v:
                            parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                    elif v:
                        parts.append(f"{k}: {v}")
                product_info_string = "\n".join(parts)

                if user_prompt and product_info_string:
                    final_prompt = f"{user_prompt} \n Product Info: \n {product_info_string}"
                elif product_info_string:
                    final_prompt = f"Is the product with the following details halal? \n {product_info_string}"
                else:
                    await publish_chunk(user_id, session_id, {"type": "results", "response": "No product information found from the image, please try again.", "documents": []})
                    return

                try:
                    decoded_image = base64.b64decode(base64_data)
                except Exception:
                    decoded_image = None
                await run_prompt_pipeline(session_id, user_id, final_prompt, image_bytes=decoded_image, image_mime=mime_type)
            except Exception as e:
                log.error("ws.image.failed", error=str(e), error_type=type(e).__name__)
                await publish_chunk(user_id, session_id, ERROR_RESULT)

    async def handle_run_with_fields(session_id: str, fields: dict, user_prompt: str, image_base64: str, image_mime: str, token: str):
      async with logged_process("ws.run_with_fields", user_id=user_id, session_id=session_id):
        async with pipeline_lease(session_id, token):
            try:
                parts = []
                # v can only be string or an array of strings
                for k, v in fields.items():
                    if isinstance(v, list):
                        if v:
                            parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                    elif v:
                        parts.append(f"{k}: {v}")
                product_info_string = "\n".join(parts)

                if user_prompt and product_info_string:
                    final_prompt = f"{user_prompt} \n Product Info: \n {product_info_string}"
                elif product_info_string:
                    final_prompt = f"Is the product with the following details halal? \n {product_info_string}"
                else:
                    await publish_chunk(user_id, session_id, {"type": "results", "response": "No product information found from the image, please try again.", "documents": []})
                    return

                decoded_image = None
                if image_base64:
                    try:
                        decoded_image = base64.b64decode(image_base64)
                    except Exception:
                        decoded_image = None
                await run_prompt_pipeline(session_id, user_id, final_prompt, image_bytes=decoded_image, image_mime=image_mime)
            except Exception as e:
                log.error("ws.run_with_fields.failed", error=str(e), error_type=type(e).__name__)
                await publish_chunk(user_id, session_id, ERROR_RESULT)

    async def compaction_blocks(session_id: str) -> bool:
        """True (and notifies the client) if a compaction decision is pending or a
        compaction is running for this session — new prompts/images are blocked
        until it resolves."""
        state = await load_compaction(session_id)
        if state.get("phase") in ("awaiting", "compacting"):
            await safe_send({**COMPACTION_BUSY_RESULT, "session_id": session_id})
            return True
        return False

    async def handle_compact_confirm(session_id: str, token: str):
        async with logged_process("ws.compact_confirm", user_id=user_id, session_id=session_id):
            async with pipeline_lease(session_id, token):
                await resume_after_confirm(session_id, user_id)

    async def handle_compact_decline(session_id: str, token: str):
        async with logged_process("ws.compact_decline", user_id=user_id, session_id=session_id):
            async with pipeline_lease(session_id, token):
                await resume_after_decline(session_id, user_id)

    # --- receive loop --------------------------------------------------------
    try:
        while True:
            raw = await websocket.receive_text()

            # Reject oversized payloads before parsing so a huge blob can't spike
            # memory. Dropped (not a disconnect) so a too-big image doesn't kill
            # the session.
            if len(raw) > MAX_MESSAGE_BYTES:
                await safe_send(OVERSIZE_RESULT)
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.close(code=1008, reason="Malformed message")
                break

            msg_type = data.get("type")

            # Hard schema gate: only known types are allowed; anything else is a
            # misbehaving/incompatible client -> close the connection.
            if msg_type not in VALID_MESSAGE_TYPES:
                await websocket.close(code=1008, reason="Unsupported message type")
                break

            # Per-user inbound message rate. Over budget -> drop this message
            # (keep the socket) and tell the client to retry shortly.
            if not await allow_message(user_id):
                await safe_send(rate_limited(MSG_RATE_REASON, 1))
                continue

            # ---- read: list the user's sessions (cupboard opened) ----
            if msg_type == "chat_sessions":
                spawn(handle_chat_sessions(), "chat_sessions")
                continue

            # ---- read: load one session's messages (display only) ----
            elif msg_type == "chat_history":
                requested_session_id = data.get("session_id")
                if not requested_session_id:
                    continue
                spawn(handle_chat_history(requested_session_id), "chat_history")
                continue

            # ---- delete: remove a session and its messages ----
            elif msg_type == "delete_session":
                target_session_id = data.get("session_id")
                if not target_session_id:
                    continue
                spawn(handle_delete_session(target_session_id), "delete_session")
                continue

            # ---- write + run: a raw text prompt ----
            elif msg_type == "prompt":
                session_id = data.get("session_id")
                message = data.get("message", "").strip()
                if not session_id or not message:
                    continue
                if await compaction_blocks(session_id):
                    continue
                if not await llm_admit():
                    continue
                token = await reserve_pipeline(session_id)
                if token is None:
                    await safe_send(BUSY_RESULT)
                    continue
                spawn(handle_prompt(session_id, message, token), "prompt", session_id)
                continue

            # ---- write + run: an uploaded image ----
            elif msg_type == "image":
                session_id = data.get("session_id")
                base64_data = data.get("base64", "").strip()
                mime_type = data.get("mime_type", "image/jpeg").strip() or "image/jpeg"
                if not session_id or not base64_data:
                    continue
                if await compaction_blocks(session_id):
                    continue
                if not await llm_admit():
                    continue
                token = await reserve_pipeline(session_id)
                if token is None:
                    await safe_send(BUSY_RESULT)
                    continue
                user_prompt = data.get("message", "").strip()
                spawn(handle_image(session_id, base64_data, mime_type, user_prompt, token), "image", session_id)
                continue

            # ---- write + run: confirmed image-extraction fields ----
            elif msg_type == "run_with_fields":
                session_id = data.get("session_id")
                if not session_id:
                    continue
                if await compaction_blocks(session_id):
                    continue
                if not await llm_admit():
                    continue
                token = await reserve_pipeline(session_id)
                if token is None:
                    await safe_send(BUSY_RESULT)
                    continue
                fields = data.get("fields", {})
                user_prompt = data.get("message", "").strip()
                image_base64 = data.get("image_base64", "").strip()
                image_mime = data.get("image_mime", "image/jpeg").strip() or "image/jpeg"
                spawn(handle_run_with_fields(session_id, fields, user_prompt, image_base64, image_mime, token), "run_with_fields", session_id)
                continue

            # ---- compaction decision: user accepted the summary prompt ----
            elif msg_type == "compact_confirm":
                session_id = data.get("session_id")
                if not session_id:
                    continue
                # No llm_admit: compaction is system-initiated and the paused
                # prompt already passed the budget when first sent.
                token = await reserve_pipeline(session_id)
                if token is None:
                    await safe_send(BUSY_RESULT)
                    continue
                spawn(handle_compact_confirm(session_id, token), "compact_confirm", session_id)
                continue

            # ---- compaction decision: user declined; raise the trigger ----
            elif msg_type == "compact_decline":
                session_id = data.get("session_id")
                if not session_id:
                    continue
                token = await reserve_pipeline(session_id)
                if token is None:
                    await safe_send(BUSY_RESULT)
                    continue
                spawn(handle_compact_decline(session_id, token), "compact_decline", session_id)
                continue

    except WebSocketDisconnect:
        log.info("ws.disconnected")
    finally:
        # Release the global connection slot.
        await close_connection(conn_id)
        # Stop relaying to a socket nobody is listening on, and hand the pubsub
        # connection back to the pool.
        forwarder.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await forwarder
        await close_pubsub(pubsub)
        # Cancel the READ handlers only — their answer was for this connection and
        # is worthless now. Pipelines are deliberately left running: the user may
        # simply have reloaded, and cancelling here would kill the agent mid-answer
        # and lose a reply that was never persisted. They finish, persist, and
        # publish; whichever connection the user comes back on receives it.
        for t in list(tasks):
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
