"""
Valkey-backed rate limiters, shared across all instances.

Three limits, all FAIL CLOSED: Valkey holds our shared coordination state, so if
it's unreachable the fleet can't coordinate and we reject rather than serve
unbounded traffic.

  1. open_connection / close_connection  — global cap on concurrent WS connections.
  2. allow_message                       — per-user inbound WS message rate (per second).
  3. try_consume_llm                      — global rate cap on LLM-backed operations (per minute).
"""

import os
import time
import asyncio
import contextlib
from uuid import uuid4

from dotenv import load_dotenv

from config.valkey_client import get_valkey
from log.logger import log

load_dotenv()


# --- tunables (env-configurable; the values below are defaults) ---
MAX_CONNECTIONS = int(os.getenv("RL_MAX_CONNECTIONS", "10000"))    # fleet-wide concurrent WS connections
CONN_TTL = int(os.getenv("RL_CONN_TTL", "60"))                     # a connection's entry expires this long after its last heartbeat
CONN_HEARTBEAT = int(os.getenv("RL_CONN_HEARTBEAT", "20"))         # score-refresh interval; keep < CONN_TTL so a live conn is never pruned
MSG_RATE_PER_SEC = int(os.getenv("RL_MSG_RATE_PER_SEC", "10"))     # inbound WS messages per user per second
LLM_RATE_PER_MIN = int(os.getenv("RL_LLM_RATE_PER_MIN", "1000"))   # LLM-backed operations across the whole fleet per minute
LLM_PER_USER_PER_MIN = int(os.getenv("RL_LLM_PER_USER_PER_MIN", "5"))  # LLM-backed ops per user per minute (fairness under the global cap)

_CONN_KEY = "ws:conns"       # sorted set: member = conn_id, score = last-seen epoch seconds

# Admission (atomic): drop entries whose heartbeat lapsed, reject if at capacity,
# else add self. Self-healing — a crashed instance's connections age out.
_ADMIT_LUA = """
redis.call('zremrangebyscore', KEYS[1], 0, ARGV[1])
if redis.call('zcard', KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
redis.call('zadd', KEYS[1], ARGV[2], ARGV[4])
return 1
"""

# Fixed-window counter (atomic): INCR, set the window's expiry on first hit,
# reject once past the limit.
_WINDOW_LUA = """
local n = redis.call('incr', KEYS[1])
if n == 1 then redis.call('expire', KEYS[1], ARGV[2]) end
if n > tonumber(ARGV[1]) then return 0 end
return 1
"""

# This instance's live connection ids, re-scored by the sweeper so they don't age out.
_local_conns: set[str] = set()
_sweeper_task: "asyncio.Task | None" = None


# ---- global connection cap ----
async def open_connection() -> str | None:
    """Reserve a fleet-wide connection slot. Returns a conn_id on success, or None
    if at capacity / Valkey unreachable (fail closed)."""
    conn_id = uuid4().hex
    now = time.time()
    try:
        vk = await get_valkey()

        # redis.call('zremrangebyscore', KEYS[1], 0, ARGV[1])
        # if redis.call('zcard', KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
        # redis.call('zadd', KEYS[1], ARGV[2], ARGV[4])
        # return 1

        ok = await vk.eval(_ADMIT_LUA, 1, _CONN_KEY, now - CONN_TTL, now, MAX_CONNECTIONS, conn_id)            
        if ok:
            _local_conns.add(conn_id)
            return conn_id
        return None
    except Exception as e:
        log.error("rate.open_connection.failed", error=str(e), error_type=type(e).__name__)
        return None


async def close_connection(conn_id: str) -> None:
    """Release a connection slot on disconnect."""
    _local_conns.discard(conn_id)
    try:
        vk = await get_valkey()
        await vk.zrem(_CONN_KEY, conn_id)
    except Exception as e:
        log.warning("rate.close_connection.failed", error=str(e), error_type=type(e).__name__)


async def _sweep_connections() -> None:
    """Periodically re-score this instance's live connections so they aren't
    pruned as stale while the instance is healthy."""
    while True:
        await asyncio.sleep(CONN_HEARTBEAT)
        if not _local_conns:
            continue
        try:
            vk = await get_valkey()
            now = time.time()
            async with vk.pipeline(transaction=False) as pipe:
                for cid in list(_local_conns):
                    pipe.zadd(_CONN_KEY, {cid: now})
                await pipe.execute()
        except Exception as e:
            log.warning("rate.connection_sweep.failed", error=str(e), error_type=type(e).__name__)


def start_connection_sweeper() -> None:
    global _sweeper_task
    if _sweeper_task is None:
        _sweeper_task = asyncio.create_task(_sweep_connections())


async def stop_connection_sweeper() -> None:
    global _sweeper_task
    if _sweeper_task is not None:
        _sweeper_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _sweeper_task
        _sweeper_task = None


# ---- per-user request rate ----
async def allow_user(user_id: str, scope: str, limit: int = MSG_RATE_PER_SEC) -> bool:
    """True if the user is within their per-second budget for `scope`. Each scope
    (WS messages, an HTTP endpoint, …) gets its own independent bucket, defaulting
    to MSG_RATE_PER_SEC. Fail closed."""
    key = f"rl:{scope}:{user_id}:{int(time.time())}"
    try:
        vk = await get_valkey()
        return bool(await vk.eval(_WINDOW_LUA, 1, key, limit, 2))
    except Exception as e:
        log.error("rate.allow_user.failed", error=str(e), error_type=type(e).__name__)
        return False


async def allow_message(user_id: str) -> bool:
    """Per-user inbound WebSocket message rate."""
    return await allow_user(user_id, "ws")


# ---- per-user LLM operation rate ----
async def try_consume_user_llm(user_id: str) -> bool:
    """Consume one token from this user's per-minute LLM budget — a single bucket
    shared across ALL LLM ops (prompt, image, extract-image, …), so no one user
    can dominate the global budget. Fail closed."""
    key = f"rl:llmu:{user_id}:{int(time.time() // 60)}"
    try:
        vk = await get_valkey()
        return bool(await vk.eval(_WINDOW_LUA, 1, key, LLM_PER_USER_PER_MIN, 120))
    except Exception as e:
        log.error("rate.try_consume_user_llm.failed", error=str(e), error_type=type(e).__name__)
        return False


# ---- global LLM operation rate ----
async def try_consume_llm() -> bool:
    """Consume one token from the fleet-wide per-minute LLM budget. Fail closed."""
    key = f"rl:llm:{int(time.time() // 60)}"
    try:
        vk = await get_valkey()
        return bool(await vk.eval(_WINDOW_LUA, 1, key, LLM_RATE_PER_MIN, 120))
    except Exception as e:
        log.error("rate.try_consume_llm.failed", error=str(e), error_type=type(e).__name__)
        return False

