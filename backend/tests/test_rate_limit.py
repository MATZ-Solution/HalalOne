"""Unit tests for `rate_limit.py` — the Valkey-backed rate limiting layer.

Every function in rate_limit.py is tested here. The real Valkey client is
replaced by the `fake_rate_valkey` fixture (defined in conftest.py), which
simulates sorted sets, counters, and Lua scripts in memory.

Key difference from session_state.py tests: rate_limit.py FAILS CLOSED.
When Valkey is unreachable, every function rejects the request rather than
allowing it through. This is the critical behaviour to verify.

Organised by function, grouped into behavioural classes.
"""
import pytest
import asyncio

from rate_limit import (
    open_connection,
    close_connection,
    allow_user,
    allow_message,
    try_consume_user_llm,
    try_consume_llm,
    start_connection_sweeper,
    stop_connection_sweeper,
    _CONN_KEY,
    MAX_CONNECTIONS,
    MSG_RATE_PER_SEC,
    LLM_PER_USER_PER_MIN,
    LLM_RATE_PER_MIN,
)

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════════
# open_connection — the global connection cap
# ═══════════════════════════════════════════════════════════════════════

class TestOpenConnection:
    async def test_returns_conn_id_on_success(self, fake_rate_valkey):
        conn_id = await open_connection()

        assert conn_id is not None
        assert isinstance(conn_id, str)
        assert len(conn_id) == 32  # uuid4().hex

    async def test_adds_conn_to_sorted_set(self, fake_rate_valkey):
        conn_id = await open_connection()

        ss = fake_rate_valkey._sorted_sets.get(_CONN_KEY, {})
        assert conn_id in ss

    async def test_tracks_conn_in_local_conns(self, fake_rate_valkey):
        import rate_limit

        conn_id = await open_connection()

        assert conn_id in rate_limit._local_conns

    async def test_returns_none_at_capacity(self, fake_rate_valkey, monkeypatch):
        # Set a tiny capacity for testing
        monkeypatch.setattr("rate_limit.MAX_CONNECTIONS", 2)

        c1 = await open_connection()
        c2 = await open_connection()
        c3 = await open_connection()

        assert c1 is not None
        assert c2 is not None
        assert c3 is None  # rejected — at capacity

    async def test_fail_closed_returns_none_on_valkey_error(self, fake_rate_valkey):
        """Unlike session_state (fail open), rate_limit FAILS CLOSED:
        if we can't coordinate, we reject."""
        fake_rate_valkey.set_error(ConnectionError("Valkey is down"))

        conn_id = await open_connection()

        assert conn_id is None

    async def test_multiple_connections_get_unique_ids(self, fake_rate_valkey):
        c1 = await open_connection()
        c2 = await open_connection()

        assert c1 != c2


# ═══════════════════════════════════════════════════════════════════════
# close_connection — release a connection slot
# ═══════════════════════════════════════════════════════════════════════

class TestCloseConnection:
    async def test_removes_from_sorted_set_and_local_conns(self, fake_rate_valkey):
        import rate_limit

        conn_id = await open_connection()
        assert conn_id is not None

        await close_connection(conn_id)

        # Removed from the sorted set
        ss = fake_rate_valkey._sorted_sets.get(_CONN_KEY, {})
        assert conn_id not in ss
        # Removed from the local set
        assert conn_id not in rate_limit._local_conns

    async def test_frees_slot_for_new_connection(self, fake_rate_valkey, monkeypatch):
        monkeypatch.setattr("rate_limit.MAX_CONNECTIONS", 2)

        c1 = await open_connection()
        c2 = await open_connection()
        assert await open_connection() is None  # full

        await close_connection(c1)

        c3 = await open_connection()
        assert c3 is not None  # slot freed

    async def test_does_not_crash_on_valkey_error(self, fake_rate_valkey):
        import rate_limit
        # Manually add a conn_id to local set (simulating a successful open)
        rate_limit._local_conns.add("test-conn")
        fake_rate_valkey.set_error(ConnectionError("Valkey is down"))

        # Should not raise — just logs a warning
        await close_connection("test-conn")

        # Local set is still cleaned even if Valkey fails
        assert "test-conn" not in rate_limit._local_conns


# ═══════════════════════════════════════════════════════════════════════
# allow_user — per-user per-second rate limit
# ═══════════════════════════════════════════════════════════════════════

class TestAllowUser:
    async def test_allows_requests_under_limit(self, fake_rate_valkey):
        result = await allow_user("user1", "ws", limit=5)

        assert result is True

    async def test_rejects_after_limit_exceeded(self, fake_rate_valkey):
        # Hit the limit (5 calls)
        for _ in range(5):
            assert await allow_user("user1", "ws", limit=5) is True

        # 6th call should be rejected
        assert await allow_user("user1", "ws", limit=5) is False

    async def test_different_users_have_independent_limits(self, fake_rate_valkey):
        # Exhaust user1's limit
        for _ in range(3):
            await allow_user("user1", "ws", limit=3)

        # user2 should still be allowed
        assert await allow_user("user2", "ws", limit=3) is True

    async def test_different_scopes_have_independent_limits(self, fake_rate_valkey):
        # Exhaust the "ws" scope
        for _ in range(3):
            await allow_user("user1", "ws", limit=3)

        # Same user, different scope should still be allowed
        assert await allow_user("user1", "api", limit=3) is True

    async def test_fail_closed_returns_false_on_error(self, fake_rate_valkey):
        fake_rate_valkey.set_error(ConnectionError("Valkey is down"))

        result = await allow_user("user1", "ws")

        assert result is False


# ═══════════════════════════════════════════════════════════════════════
# allow_message — convenience wrapper for WS messages
# ═══════════════════════════════════════════════════════════════════════

class TestAllowMessage:
    async def test_delegates_to_allow_user_with_ws_scope(self, fake_rate_valkey):
        result = await allow_message("user1")

        assert result is True

    async def test_uses_msg_rate_per_sec_as_default_limit(self, fake_rate_valkey):
        import rate_limit
        limit = rate_limit.MSG_RATE_PER_SEC
        
        # Exhaust the default limit
        for _ in range(limit):
            assert await allow_message("user1") is True
            
        # The next one should be rejected
        assert await allow_message("user1") is False


# ═══════════════════════════════════════════════════════════════════════
# try_consume_user_llm — per-user LLM budget
# ═══════════════════════════════════════════════════════════════════════

class TestTryConsumeUserLlm:
    async def test_allows_under_limit(self, fake_rate_valkey):
        result = await try_consume_user_llm("user1")

        assert result is True

    async def test_rejects_after_per_user_limit_exceeded(self, fake_rate_valkey, monkeypatch):
        monkeypatch.setattr("rate_limit.LLM_PER_USER_PER_MIN", 3)

        for _ in range(3):
            assert await try_consume_user_llm("user1") is True

        assert await try_consume_user_llm("user1") is False

    async def test_different_users_have_independent_budgets(self, fake_rate_valkey, monkeypatch):
        monkeypatch.setattr("rate_limit.LLM_PER_USER_PER_MIN", 2)

        # Exhaust user1
        for _ in range(2):
            await try_consume_user_llm("user1")

        # user2 still has budget
        assert await try_consume_user_llm("user2") is True

    async def test_fail_closed_returns_false_on_error(self, fake_rate_valkey):
        fake_rate_valkey.set_error(ConnectionError("Valkey is down"))

        assert await try_consume_user_llm("user1") is False


# ═══════════════════════════════════════════════════════════════════════
# try_consume_llm — fleet-wide LLM budget
# ═══════════════════════════════════════════════════════════════════════

class TestTryConsumeLlm:
    async def test_allows_under_limit(self, fake_rate_valkey):
        result = await try_consume_llm()

        assert result is True

    async def test_rejects_after_global_limit_exceeded(self, fake_rate_valkey, monkeypatch):
        monkeypatch.setattr("rate_limit.LLM_RATE_PER_MIN", 3)

        for _ in range(3):
            assert await try_consume_llm() is True

        assert await try_consume_llm() is False

    async def test_fail_closed_returns_false_on_error(self, fake_rate_valkey):
        fake_rate_valkey.set_error(ConnectionError("Valkey is down"))

        assert await try_consume_llm() is False


# ═══════════════════════════════════════════════════════════════════════
# start / stop connection sweeper
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionSweeper:
    async def test_start_creates_a_background_task(self, fake_rate_valkey):
        import rate_limit

        # Ensure clean state
        rate_limit._sweeper_task = None

        start_connection_sweeper()

        assert rate_limit._sweeper_task is not None
        assert not rate_limit._sweeper_task.done()

        # Clean up
        await stop_connection_sweeper()

    async def test_stop_cancels_the_task(self, fake_rate_valkey):
        import rate_limit

        rate_limit._sweeper_task = None
        start_connection_sweeper()

        await stop_connection_sweeper()

        assert rate_limit._sweeper_task is None

    async def test_start_is_idempotent(self, fake_rate_valkey):
        import rate_limit

        rate_limit._sweeper_task = None
        start_connection_sweeper()
        first_task = rate_limit._sweeper_task

        start_connection_sweeper()  # second call
        second_task = rate_limit._sweeper_task

        # Should be the same task, not a new one
        assert first_task is second_task

        await stop_connection_sweeper()

    async def test_stop_is_safe_when_never_started(self, fake_rate_valkey):
        import rate_limit

        rate_limit._sweeper_task = None

        # Should not raise
        await stop_connection_sweeper()
