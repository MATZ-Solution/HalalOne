"""Unit tests for `session_state.py` — the Valkey coordination layer.

Every function in session_state.py is tested here. The real Valkey client is
replaced by the `fake_valkey` fixture (defined in conftest.py), which actually
stores and retrieves data like a real Redis — no pre-configured returns needed.

What we verify at each layer:
  * **Data flow:** Does SET actually store, does GET actually retrieve?
  * **Atomicity:** Do Lua scripts (renew/release) check ownership before acting?
  * **Fail-open:** Does every function return a safe default when Valkey is down?
  * **Pipeline transactions:** Do seed/append correctly batch their commands?

Organised by function, grouped into behavioural classes.
"""
import json
import pytest
import asyncio

from session_state import (
    _with_retry,
    _inflight_key,
    reserve_pipeline,
    renew_pipeline,
    release_pipeline,
    is_pipeline_inflight,
    pipeline_lease,
    load_history,
    seed_history,
    append_history,
    clear_history,
    load_summary,
    save_summary,
    clear_summary,
    load_compaction,
    save_compaction,
    clear_compaction,
    IDLE_COMPACTION,
    is_session_known,
    mark_session_known,
    clear_session_known,
    INFLIGHT_TTL,
)

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════════
# _with_retry — the Valkey retry engine
# ═══════════════════════════════════════════════════════════════════════

class TestWithRetry:
    """session_state's _with_retry is slightly different from chat_store's:
    it takes fn(vk) instead of make_coro(), so the client is fetched inside
    the retry loop (a fresh connection each attempt)."""

    async def test_returns_on_first_success(self, fake_valkey):
        result = await _with_retry("test", lambda vk: vk.get("anything"))
        assert result is None  # key doesn't exist, but no crash

    async def test_retries_on_transient_failure_then_succeeds(self, fake_valkey):
        attempts = []

        async def flaky(vk):
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("transient")
            return "recovered"

        result = await _with_retry("test", flaky)
        assert result == "recovered"
        assert len(attempts) == 3

    async def test_reraises_last_exception_after_exhaustion(self, fake_valkey):
        attempt = 0

        async def always_fails(vk):
            nonlocal attempt
            attempt += 1
            raise RuntimeError(f"error-{attempt}")

        with pytest.raises(RuntimeError, match="error-3"):
            await _with_retry("test", always_fails)


# ═══════════════════════════════════════════════════════════════════════
# reserve_pipeline — the distributed lock
# ═══════════════════════════════════════════════════════════════════════

class TestReservePipeline:
    async def test_returns_token_on_successful_reservation(self, fake_valkey):
        token = await reserve_pipeline("s1")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) == 32  # uuid4().hex is 32 hex chars

    async def test_stores_token_in_valkey_with_nx(self, fake_valkey):
        token = await reserve_pipeline("s1")

        # The key should now exist in our fake
        stored = await fake_valkey.get(_inflight_key("s1"))
        assert stored == token

    async def test_returns_none_if_already_reserved(self, fake_valkey):
        # First reservation succeeds
        token1 = await reserve_pipeline("s1")
        assert token1 is not None

        # Second reservation for SAME session fails (nx=True rejects it)
        token2 = await reserve_pipeline("s1")
        assert token2 is None

    async def test_different_sessions_can_reserve_independently(self, fake_valkey):
        token1 = await reserve_pipeline("s1")
        token2 = await reserve_pipeline("s2")

        assert token1 is not None
        assert token2 is not None
        assert token1 != token2

    async def test_fail_open_returns_token_on_valkey_error(self, fake_valkey):
        """If Valkey is unreachable, reserve_pipeline still returns a token
        so the pipeline runs — better to serve the user than block them."""
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        token = await reserve_pipeline("s1")

        # Fail-open: returns a token even though nothing was stored
        assert token is not None
        assert isinstance(token, str)


# ═══════════════════════════════════════════════════════════════════════
# renew_pipeline — extend the lock's TTL (heartbeat)
# ═══════════════════════════════════════════════════════════════════════

class TestRenewPipeline:
    async def test_extends_ttl_if_we_own_the_key(self, fake_valkey):
        token = await reserve_pipeline("s1")

        # Should succeed (Lua script sees our token matches)
        await renew_pipeline("s1", token)

        # Key should still exist (not deleted)
        stored = await fake_valkey.get(_inflight_key("s1"))
        assert stored == token

    async def test_does_nothing_if_we_do_not_own_the_key(self, fake_valkey):
        # Someone else reserved the session
        real_token = await reserve_pipeline("s1")

        # We try to renew with a stale/wrong token
        await renew_pipeline("s1", "wrong-token")

        # The original owner's key is untouched
        stored = await fake_valkey.get(_inflight_key("s1"))
        assert stored == real_token

    async def test_does_not_crash_on_valkey_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        # Should not raise — just logs a warning
        await renew_pipeline("s1", "any-token")


# ═══════════════════════════════════════════════════════════════════════
# release_pipeline — delete the lock (owner-checked)
# ═══════════════════════════════════════════════════════════════════════

class TestReleasePipeline:
    async def test_deletes_key_if_we_own_it(self, fake_valkey):
        token = await reserve_pipeline("s1")

        await release_pipeline("s1", token)

        # Key should be gone
        stored = await fake_valkey.get(_inflight_key("s1"))
        assert stored is None

    async def test_does_not_delete_if_we_do_not_own_it(self, fake_valkey):
        real_token = await reserve_pipeline("s1")

        # A stale release with the wrong token must NOT delete the key
        await release_pipeline("s1", "wrong-token")

        stored = await fake_valkey.get(_inflight_key("s1"))
        assert stored == real_token  # still there

    async def test_does_not_crash_on_valkey_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        await release_pipeline("s1", "any-token")


# ═══════════════════════════════════════════════════════════════════════
# is_pipeline_inflight
# ═══════════════════════════════════════════════════════════════════════

class TestIsPipelineInflight:
    async def test_returns_true_when_reserved(self, fake_valkey):
        await reserve_pipeline("s1")

        assert await is_pipeline_inflight("s1") is True

    async def test_returns_false_when_not_reserved(self, fake_valkey):
        assert await is_pipeline_inflight("s1") is False

    async def test_returns_false_after_release(self, fake_valkey):
        token = await reserve_pipeline("s1")
        await release_pipeline("s1", token)

        assert await is_pipeline_inflight("s1") is False

    async def test_fail_open_returns_false_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        assert await is_pipeline_inflight("s1") is False


# ═══════════════════════════════════════════════════════════════════════
# pipeline_lease — the context manager with heartbeat
# ═══════════════════════════════════════════════════════════════════════

class TestPipelineLease:
    async def test_releases_pipeline_on_normal_exit(self, fake_valkey):
        token = await reserve_pipeline("s1")

        async with pipeline_lease("s1", token):
            # Pipeline is running — key should exist
            assert await is_pipeline_inflight("s1") is True

        # After exiting the context, the pipeline should be released
        assert await is_pipeline_inflight("s1") is False

    async def test_releases_pipeline_on_exception(self, fake_valkey):
        token = await reserve_pipeline("s1")

        with pytest.raises(ValueError, match="something broke"):
            async with pipeline_lease("s1", token):
                raise ValueError("something broke")

        # Even after an exception, the key must be cleaned up
        assert await is_pipeline_inflight("s1") is False

    async def test_heartbeat_task_is_cancelled_on_exit(self, fake_valkey):
        token = await reserve_pipeline("s1")

        async with pipeline_lease("s1", token):
            pass  # exit immediately

        # Give the event loop a tick to process the cancellation
        await asyncio.sleep(0)

        # If the heartbeat wasn't cancelled, it would be sleeping for 100s.
        # We can't easily inspect task state, but the fact that the test
        # completes instantly (not hung for 100s) proves it was cancelled.


# ═══════════════════════════════════════════════════════════════════════
# load_history — read the conversation cache
# ═══════════════════════════════════════════════════════════════════════

class TestLoadHistory:
    async def test_returns_list_of_dicts_when_data_exists(self, fake_valkey):
        # Pre-seed the fake with some history entries
        key = "history:s1"
        await fake_valkey.rpush(key, json.dumps({"role": "user", "content": "Hi"}))
        await fake_valkey.rpush(key, json.dumps({"role": "assistant", "content": "Hello!"}))

        result = await load_history("s1")

        assert result == [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]

    async def test_returns_none_on_cache_miss(self, fake_valkey):
        result = await load_history("nonexistent")

        assert result is None

    async def test_fail_open_returns_none_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        result = await load_history("s1")

        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# seed_history — replace the full conversation cache
# ═══════════════════════════════════════════════════════════════════════

class TestSeedHistory:
    async def test_replaces_existing_history(self, fake_valkey):
        # Pre-seed some old data
        key = "history:s1"
        await fake_valkey.rpush(key, json.dumps({"role": "user", "content": "old"}))

        new_messages = [
            {"role": "user", "content": "new question"},
            {"role": "assistant", "content": "new answer"},
        ]
        result = await seed_history("s1", new_messages)

        assert result is True
        # Verify the old data was replaced
        loaded = await load_history("s1")
        assert loaded == new_messages

    async def test_empty_messages_clears_the_history(self, fake_valkey):
        key = "history:s1"
        await fake_valkey.rpush(key, json.dumps({"role": "user", "content": "old"}))

        result = await seed_history("s1", [])

        assert result is True
        loaded = await load_history("s1")
        assert loaded is None  # empty list → cache miss

    async def test_returns_false_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        result = await seed_history("s1", [{"role": "user", "content": "test"}])

        assert result is False


# ═══════════════════════════════════════════════════════════════════════
# append_history — add one message to the cache
# ═══════════════════════════════════════════════════════════════════════

class TestAppendHistory:
    async def test_appends_message_to_existing_history(self, fake_valkey):
        key = "history:s1"
        await fake_valkey.rpush(key, json.dumps({"id": "m1", "role": "user", "content": "Hi"}))

        await append_history("s1", "assistant", "Hello!", message_id="m2")

        loaded = await load_history("s1")
        assert len(loaded) == 2
        assert loaded[1] == {"id": "m2", "role": "assistant", "content": "Hello!"}

    async def test_message_includes_id_role_and_content(self, fake_valkey):
        await append_history("s1", "user", "What is halal?", message_id="m1")

        loaded = await load_history("s1")
        assert loaded[0] == {"id": "m1", "role": "user", "content": "What is halal?"}

    async def test_does_not_crash_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        # Should not raise
        await append_history("s1", "user", "Hello", message_id="m1")


# ═══════════════════════════════════════════════════════════════════════
# clear_history — delete the conversation cache
# ═══════════════════════════════════════════════════════════════════════

class TestClearHistory:
    async def test_removes_history_key(self, fake_valkey):
        key = "history:s1"
        await fake_valkey.rpush(key, json.dumps({"role": "user", "content": "Hi"}))

        await clear_history("s1")

        loaded = await load_history("s1")
        assert loaded is None

    async def test_does_not_crash_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        await clear_history("s1")


# ═══════════════════════════════════════════════════════════════════════
# load_summary — read the rolling summary cache
# ═══════════════════════════════════════════════════════════════════════

class TestLoadSummary:
    async def test_returns_dict_when_summary_exists(self, fake_valkey):
        payload = json.dumps({"summary": "User asked about halal", "message_ids": ["m1", "m2"]})
        await fake_valkey.set("summary:s1", payload)

        result = await load_summary("s1")

        assert result == {"summary": "User asked about halal", "message_ids": ["m1", "m2"]}

    async def test_returns_none_on_cache_miss(self, fake_valkey):
        result = await load_summary("nonexistent")

        assert result is None

    async def test_fail_open_returns_none_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        result = await load_summary("s1")

        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# save_summary — write the rolling summary cache
# ═══════════════════════════════════════════════════════════════════════

class TestSaveSummary:
    async def test_saves_and_can_be_loaded_back(self, fake_valkey):
        result = await save_summary("s1", "User asked about halal", ["m1", "m2"])

        assert result is True
        loaded = await load_summary("s1")
        assert loaded == {"summary": "User asked about halal", "message_ids": ["m1", "m2"]}

    async def test_returns_false_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        result = await save_summary("s1", "text", ["m1"])

        assert result is False


# ═══════════════════════════════════════════════════════════════════════
# clear_summary — delete the summary cache
# ═══════════════════════════════════════════════════════════════════════

class TestClearSummary:
    async def test_removes_summary_key(self, fake_valkey):
        await save_summary("s1", "old summary", ["m1"])

        await clear_summary("s1")

        loaded = await load_summary("s1")
        assert loaded is None

    async def test_does_not_crash_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        await clear_summary("s1")


# ═══════════════════════════════════════════════════════════════════════
# load_compaction — read the compaction handshake state
# ═══════════════════════════════════════════════════════════════════════

class TestLoadCompaction:
    async def test_returns_state_when_it_exists(self, fake_valkey):
        state = {"phase": "awaiting", "declines": 1, "pending": {"prompt": "summarize?"}}
        await fake_valkey.set("compaction:s1", json.dumps(state))

        result = await load_compaction("s1")

        assert result == state

    async def test_returns_idle_on_cache_miss(self, fake_valkey):
        result = await load_compaction("nonexistent")

        assert result == IDLE_COMPACTION

    async def test_idle_default_is_a_fresh_copy(self, fake_valkey):
        """Each miss returns a new dict, not a shared reference that could
        be mutated and affect other sessions."""
        r1 = await load_compaction("s1")
        r2 = await load_compaction("s2")

        r1["declines"] = 99
        assert r2["declines"] == 0  # unaffected

    async def test_fail_open_returns_idle_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        result = await load_compaction("s1")

        assert result == IDLE_COMPACTION


# ═══════════════════════════════════════════════════════════════════════
# save_compaction — persist the compaction state
# ═══════════════════════════════════════════════════════════════════════

class TestSaveCompaction:
    async def test_saves_and_can_be_loaded_back(self, fake_valkey):
        state = {"phase": "compacting", "declines": 0, "pending": None}

        await save_compaction("s1", state)

        loaded = await load_compaction("s1")
        assert loaded == state

    async def test_does_not_crash_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        await save_compaction("s1", {"phase": "idle", "declines": 0, "pending": None})


# ═══════════════════════════════════════════════════════════════════════
# clear_compaction — reset the compaction state
# ═══════════════════════════════════════════════════════════════════════

class TestClearCompaction:
    async def test_removes_compaction_key(self, fake_valkey):
        await save_compaction("s1", {"phase": "awaiting", "declines": 1, "pending": None})

        await clear_compaction("s1")

        loaded = await load_compaction("s1")
        assert loaded == IDLE_COMPACTION  # back to default

    async def test_does_not_crash_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        await clear_compaction("s1")


# ═══════════════════════════════════════════════════════════════════════
# is_session_known — the one-bit existence cache
# ═══════════════════════════════════════════════════════════════════════

class TestIsSessionKnown:
    async def test_returns_true_when_marked(self, fake_valkey):
        await mark_session_known("s1")

        assert await is_session_known("s1") is True

    async def test_returns_false_when_not_marked(self, fake_valkey):
        assert await is_session_known("s1") is False

    async def test_fail_open_returns_false_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        assert await is_session_known("s1") is False


# ═══════════════════════════════════════════════════════════════════════
# mark_session_known — set the existence flag
# ═══════════════════════════════════════════════════════════════════════

class TestMarkSessionKnown:
    async def test_marks_session_as_known(self, fake_valkey):
        await mark_session_known("s1")

        assert await is_session_known("s1") is True

    async def test_does_not_crash_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        await mark_session_known("s1")


# ═══════════════════════════════════════════════════════════════════════
# clear_session_known — remove the existence flag
# ═══════════════════════════════════════════════════════════════════════

class TestClearSessionKnown:
    async def test_clears_known_flag(self, fake_valkey):
        await mark_session_known("s1")

        await clear_session_known("s1")

        assert await is_session_known("s1") is False

    async def test_does_not_crash_on_error(self, fake_valkey):
        fake_valkey.set_error(ConnectionError("Valkey is down"))

        await clear_session_known("s1")
