"""Cross-instance session coordination backed by Valkey.

In-flight guard: a session may have only one pipeline running at a time across
the whole fleet. The reservation is a single Valkey key holding a per-acquisition
token, kept alive by a heartbeat while the pipeline runs and released
(owner-checked) when it ends. If the owning instance dies, the heartbeat stops,
the key's TTL lapses, and the session frees automatically.

All ops fail OPEN: if Valkey is unreachable we prefer to serve the user over
blocking them.
"""
import json
import asyncio
import contextlib
from uuid import uuid4

from config.valkey_client import get_valkey
from log.logger import log

# TTL is a dead-owner detector, not a max pipeline time: the heartbeat renews it
# well within this window, so a live pipeline never expires; only a crashed
# instance (renewals stop) lets it lapse.
INFLIGHT_TTL = 300           # seconds
_HEARTBEAT_INTERVAL = 100    # seconds; comfortably < INFLIGHT_TTL to survive a missed beat

# Renew / release only if we still own the key (compare-and-act, atomically), so
# a stale renew/release can never touch a successor's reservation.
_RENEW_LUA = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end"
_RELEASE_LUA = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"

# Retry policy for the data-cache ops below (history / summary / compaction /
# session-known). Mirrors chat_store's DB retry so a transient Valkey blip is
# smoothed over before it can leave the cache inconsistent.
CACHE_MAX_RETRIES = 3
CACHE_BASE_DELAY = 0.1  # seconds; doubles each attempt (0.1s, 0.2s)


async def _with_retry(op: str, fn):
    """Run a Valkey call with exponential backoff. `fn` receives the client and
    returns the awaitable for one attempt. Re-raises the last exception if every
    attempt fails, so each caller's own try/except still applies its fail-open
    default — retry sits *underneath* the existing fail-open contract."""
    delay = CACHE_BASE_DELAY
    last_exc = None
    for attempt in range(1, CACHE_MAX_RETRIES + 1):
        try:
            vk = await get_valkey()
            return await fn(vk)
        except Exception as e:
            last_exc = e
            log.warning("valkey.op.retry", op=op, attempt=attempt, max_retries=CACHE_MAX_RETRIES, error=str(e), error_type=type(e).__name__)
            if attempt < CACHE_MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= 2
    raise last_exc


def _inflight_key(session_id: str) -> str:
    return f"inflight:{session_id}"


async def reserve_pipeline(session_id: str) -> str | None:
    """Atomically reserve a session. Returns a per-acquisition token on success,
    or None if a pipeline is already in flight for it on any instance. The token
    must be passed to renew/release so only this owner can touch the key."""
    token = uuid4().hex
    try:
        vk = await get_valkey()
        ok = await vk.set(_inflight_key(session_id), token, nx=True, ex=INFLIGHT_TTL)
        return token if ok else None
    except Exception as e:
        log.warning("valkey.reserve_pipeline.failed", error=str(e), error_type=type(e).__name__)
        return token  # fail open: behave as reserved so the pipeline still runs


async def renew_pipeline(session_id: str, token: str) -> None:
    """Extend the reservation's TTL — but only while we still own it."""
    try:
        vk = await get_valkey()
        await vk.eval(_RENEW_LUA, 1, _inflight_key(session_id), token, INFLIGHT_TTL)
    except Exception as e:
        log.warning("valkey.renew_pipeline.failed", error=str(e), error_type=type(e).__name__)


async def release_pipeline(session_id: str, token: str) -> None:
    """Release the reservation — only if we still own it, so a stale release can't
    delete a successor's lock. Best-effort; the TTL is the backstop."""
    try:
        vk = await get_valkey()
        await vk.eval(_RELEASE_LUA, 1, _inflight_key(session_id), token)
    except Exception as e:
        log.warning("valkey.release_pipeline.failed", error=str(e), error_type=type(e).__name__)


async def is_pipeline_inflight(session_id: str) -> bool:
    """Whether a pipeline is currently reserved for this session (any instance)."""
    try:
        vk = await get_valkey()
        return bool(await vk.exists(_inflight_key(session_id)))
    except Exception as e:
        log.warning("valkey.is_pipeline_inflight.failed", error=str(e), error_type=type(e).__name__)
        return False


async def _heartbeat(session_id: str, token: str) -> None:
    """Renew the reservation on an interval until cancelled."""
    while True:
        await asyncio.sleep(_HEARTBEAT_INTERVAL)
        await renew_pipeline(session_id, token)


@contextlib.asynccontextmanager
async def pipeline_lease(session_id: str, token: str):
    """Keep the reservation alive with a heartbeat while the body runs, then
    release it (owner-checked) on exit — even on error or cancellation."""
    hb = asyncio.create_task(_heartbeat(session_id, token))
    try:
        yield
    finally:
        hb.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hb
        await release_pipeline(session_id, token)


# ---- conversation-history cache ----
# The agent's multi-turn memory, shared across instances so any of them can serve
# any session. It's a cache: the DB (chat_messages) is the source of truth, so a
# miss/expiry just rebuilds from there. Stored as a Valkey LIST of {role, content}
# JSON entries — appends are atomic RPUSH, no read-modify-write of a blob. Only
# the pipeline writes this (and only one pipeline runs per session), so there is a
# single serialized writer and no rebuild-vs-append race.
_HISTORY_TTL = 3600  # seconds


def _history_key(session_id: str) -> str:
    return f"history:{session_id}"


async def load_history(session_id: str) -> list[dict] | None:
    """Return the cached history as [{role, content}], or None on a miss (so the
    caller rebuilds from the DB)."""
    try:
        raw = await _with_retry("load_history", lambda vk: vk.lrange(_history_key(session_id), 0, -1))
        return [json.loads(x) for x in raw] if raw else None
    except Exception as e:
        log.warning("valkey.load_history.failed", error=str(e), error_type=type(e).__name__)
        return None


async def seed_history(session_id: str, messages: list[dict]) -> bool:
    """Replace the cached history (used after a DB rebuild). Returns True on
    success, False if the write failed (so a caller like compact_session can
    invalidate the cache and let the next turn rebuild from the DB)."""
    key = _history_key(session_id)

    async def _run(vk):
        async with vk.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            if messages:
                pipe.rpush(key, *[json.dumps(m) for m in messages])
                pipe.expire(key, _HISTORY_TTL)
            return await pipe.execute()

    try:
        await _with_retry("seed_history", _run)
        return True
    except Exception as e:
        log.warning("valkey.seed_history.failed", error=str(e), error_type=type(e).__name__)
        return False


async def append_history(session_id: str, role: str, content: str, message_id: str | None = None) -> None:
    """Append one message and refresh the TTL. `message_id` is the DB row id, kept
    on the entry so a fold knows exactly which message ids it has absorbed; the
    summary-key TTL is refreshed alongside so the two never drift apart."""
    key = _history_key(session_id)

    async def _run(vk):
        async with vk.pipeline(transaction=True) as pipe:
            pipe.rpush(key, json.dumps({"id": message_id, "role": role, "content": content}))
            pipe.expire(key, _HISTORY_TTL)
            pipe.expire(_summary_key(session_id), _HISTORY_TTL)
            return await pipe.execute()

    try:
        await _with_retry("append_history", _run)
    except Exception as e:
        log.warning("valkey.append_history.failed", error=str(e), error_type=type(e).__name__)


async def clear_history(session_id: str) -> None:
    """Drop the cached history (e.g. on a brand-new session)."""
    try:
        await _with_retry("clear_history", lambda vk: vk.delete(_history_key(session_id)))
    except Exception as e:
        log.warning("valkey.clear_history.failed", error=str(e), error_type=type(e).__name__)


# ---- rolling-summary cache ----
# The "runtime summary key" from the spec: the current summary plus the set of
# message ids it covers. Kept next to the history list and rebuilt from the DB on
# a miss (chat_summaries is the source of truth). Same TTL as history so they
# expire together; append_history refreshes this key too.


def _summary_key(session_id: str) -> str:
    return f"summary:{session_id}"


async def load_summary(session_id: str) -> dict | None:
    """Return {summary, message_ids} for the session, or None on a miss."""
    try:
        raw = await _with_retry("load_summary", lambda vk: vk.get(_summary_key(session_id)))
        return json.loads(raw) if raw else None
    except Exception as e:
        log.warning("valkey.load_summary.failed", error=str(e), error_type=type(e).__name__)
        return None


async def save_summary(session_id: str, summary: str, message_ids: list[str]) -> bool:
    """Replace the cached summary and its covered message-id set. Returns True on
    success, False if the write failed (so compact_session can invalidate the
    cache and let the next turn rebuild from the DB)."""
    payload = json.dumps({"summary": summary, "message_ids": message_ids})
    try:
        await _with_retry("save_summary", lambda vk: vk.set(_summary_key(session_id), payload, ex=_HISTORY_TTL))
        return True
    except Exception as e:
        log.warning("valkey.save_summary.failed", error=str(e), error_type=type(e).__name__)
        return False


async def clear_summary(session_id: str) -> None:
    """Drop the cached summary (e.g. on session delete)."""
    try:
        await _with_retry("clear_summary", lambda vk: vk.delete(_summary_key(session_id)))
    except Exception as e:
        log.warning("valkey.clear_summary.failed", error=str(e), error_type=type(e).__name__)


# ---- compaction state ----
# Drives the user-confirmed compaction handshake and its escalating threshold.
# Lives in Valkey so it survives instance switches and reconnects (the WS
# connection may land on a different instance). Shape:
#   {"phase": "idle"|"awaiting"|"compacting", "declines": 0..3, "pending": {"prompt": str} | None}
# A longer TTL than history: a pending decision may sit while the user is away.
# If it lapses, the paused turn is simply lost and the user resends.
_COMPACTION_TTL = 86400  # seconds (1 day)

IDLE_COMPACTION = {"phase": "idle", "declines": 0, "pending": None}


def _compaction_key(session_id: str) -> str:
    return f"compaction:{session_id}"


async def load_compaction(session_id: str) -> dict:
    """Return the compaction state, defaulting to idle on a miss/error so callers
    can treat 'no state' and 'idle' identically."""
    try:
        raw = await _with_retry("load_compaction", lambda vk: vk.get(_compaction_key(session_id)))
        return json.loads(raw) if raw else dict(IDLE_COMPACTION)
    except Exception as e:
        log.warning("valkey.load_compaction.failed", error=str(e), error_type=type(e).__name__)
        return dict(IDLE_COMPACTION)


async def save_compaction(session_id: str, state: dict) -> None:
    """Persist the compaction state."""
    payload = json.dumps(state)
    try:
        await _with_retry("save_compaction", lambda vk: vk.set(_compaction_key(session_id), payload, ex=_COMPACTION_TTL))
    except Exception as e:
        log.warning("valkey.save_compaction.failed", error=str(e), error_type=type(e).__name__)


async def clear_compaction(session_id: str) -> None:
    """Reset compaction state to idle (delete the key)."""
    try:
        await _with_retry("clear_compaction", lambda vk: vk.delete(_compaction_key(session_id)))
    except Exception as e:
        log.warning("valkey.clear_compaction.failed", error=str(e), error_type=type(e).__name__)


# ---- session-existence cache ----
# A one-bit Valkey flag ("this session is known to exist in the DB") so the hot
# prompt path doesn't pay a Supabase round-trip every turn just to decide whether
# to create the session. Set when we confirm/create a session; cleared on delete.
# Fails OPEN as "unknown" so a Valkey blip just falls back to the DB check.
_SESSION_KNOWN_TTL = 86400  # seconds (1 day)


def _session_known_key(session_id: str) -> str:
    return f"session_known:{session_id}"


async def is_session_known(session_id: str) -> bool:
    """Whether we've already confirmed this session exists (cache only)."""
    try:
        return bool(await _with_retry("is_session_known", lambda vk: vk.exists(_session_known_key(session_id))))
    except Exception as e:
        log.warning("valkey.is_session_known.failed", error=str(e), error_type=type(e).__name__)
        return False


async def mark_session_known(session_id: str) -> None:
    """Record that this session exists so later turns can skip the DB check."""
    try:
        await _with_retry("mark_session_known", lambda vk: vk.set(_session_known_key(session_id), "1", ex=_SESSION_KNOWN_TTL))
    except Exception as e:
        log.warning("valkey.mark_session_known.failed", error=str(e), error_type=type(e).__name__)


async def clear_session_known(session_id: str) -> None:
    """Drop the existence flag (e.g. on session delete)."""
    try:
        await _with_retry("clear_session_known", lambda vk: vk.delete(_session_known_key(session_id)))
    except Exception as e:
        log.warning("valkey.clear_session_known.failed", error=str(e), error_type=type(e).__name__)
