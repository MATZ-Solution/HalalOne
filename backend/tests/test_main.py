"""Unit tests for `main.py` — the application glue layer.

Tests the core pipeline functions that wire session_state, chat_store,
pubsub, and the agent together. Every external dependency is replaced by
the `main_mocks` fixture (AsyncMocks), so no network calls happen.

We deliberately DO NOT test the WebSocket handler here. It is a pure
router whose every branch delegates to the functions tested below. Testing
it would require 15+ simultaneous mocks for zero additional logic coverage.

Organised by function, grouped into behavioural classes.
"""
import json
import pytest
import asyncio

from main import (
    _history_to_messages,
    _rows_to_history,
    _session_exists_cached,
    _load_context,
    _stream_and_persist,
    run_prompt_pipeline,
    resume_after_confirm,
    resume_after_decline,
    ERROR_RESULT,
    SUMMARY_TOKEN_THRESHOLD,
    COMPACTION_ASK_MSG,
)
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from session_state import IDLE_COMPACTION

pytestmark = pytest.mark.unit


# ── helpers ──────────────────────────────────────────────────────────

def _fake_stream(*chunks):
    """Build a fake async generator that yields the given chunks.

    Usage:
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Hello!", "documents": []}
        )
    """
    async def gen(*args, **kwargs):
        for c in chunks:
            yield c
    return gen(*args if False else ())  # return the async generator object


# ═══════════════════════════════════════════════════════════════════════
# _history_to_messages — pure conversion, no mocking needed
# ═══════════════════════════════════════════════════════════════════════

class TestHistoryToMessages:
    def test_empty_history_returns_empty_list(self):
        result = _history_to_messages([])
        assert result == []

    def test_user_message_becomes_human_message(self):
        history = [{"role": "user", "content": "Hi"}]
        result = _history_to_messages(history)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hi"

    def test_assistant_message_becomes_ai_message(self):
        history = [{"role": "assistant", "content": "Hello!"}]
        result = _history_to_messages(history)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "Hello!"

    def test_summary_prepended_as_system_message(self):
        history = [{"role": "user", "content": "Hi"}]
        result = _history_to_messages(history, summary="Previous discussion about halal foods")

        assert len(result) == 2
        assert isinstance(result[0], SystemMessage)
        assert "Previous discussion about halal foods" in result[0].content
        assert isinstance(result[1], HumanMessage)

    def test_empty_summary_is_not_prepended(self):
        history = [{"role": "user", "content": "Hi"}]
        result = _history_to_messages(history, summary="")

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)


# ═══════════════════════════════════════════════════════════════════════
# _rows_to_history — pure conversion, no mocking needed
# ═══════════════════════════════════════════════════════════════════════

class TestRowsToHistory:
    def test_user_row_gets_plain_content(self):
        rows = [{"id": "m1", "role": "user", "content": "Is this halal?"}]
        result = _rows_to_history(rows)

        assert result == [{"id": "m1", "role": "user", "content": "Is this halal?"}]

    def test_assistant_row_gets_json_packed_content(self):
        rows = [{"id": "m2", "role": "assistant", "content": "Yes it is!", "search_results": [{"doc": "cert1"}]}]
        result = _rows_to_history(rows)

        assert result[0]["role"] == "assistant"
        packed = json.loads(result[0]["content"])
        assert packed["response"] == "Yes it is!"
        assert packed["documents"] == [{"doc": "cert1"}]

    def test_missing_search_results_defaults_to_empty_list(self):
        rows = [{"id": "m2", "role": "assistant", "content": "Hello"}]
        result = _rows_to_history(rows)

        packed = json.loads(result[0]["content"])
        assert packed["documents"] == []


# ═══════════════════════════════════════════════════════════════════════
# _session_exists_cached — Valkey shortcut for session ownership
# ═══════════════════════════════════════════════════════════════════════

class TestSessionExistsCached:
    async def test_returns_true_from_valkey_cache_without_db_call(self, main_mocks):
        main_mocks["is_session_known"].return_value = True

        result = await _session_exists_cached("s1", "u1")

        assert result is True
        # DB was never called because the cache hit
        main_mocks["cs_session_exists"].assert_not_called()

    async def test_falls_back_to_db_on_cache_miss_and_marks_known(self, main_mocks):
        main_mocks["is_session_known"].return_value = False
        main_mocks["cs_session_exists"].return_value = True

        result = await _session_exists_cached("s1", "u1")

        assert result is True
        main_mocks["cs_session_exists"].assert_called_once_with("s1", "u1")
        main_mocks["mark_session_known"].assert_called_once_with("s1")

    async def test_returns_false_if_not_in_cache_or_db(self, main_mocks):
        main_mocks["is_session_known"].return_value = False
        main_mocks["cs_session_exists"].return_value = False

        result = await _session_exists_cached("s1", "u1")

        assert result is False
        main_mocks["mark_session_known"].assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# _load_context — Valkey cache with DB fallback
# ═══════════════════════════════════════════════════════════════════════

class TestLoadContext:
    async def test_returns_cached_data_on_valkey_hit(self, main_mocks):
        cached_history = [{"id": "m1", "role": "user", "content": "Hi"}]
        cached_summary = {"summary": "Earlier discussion", "message_ids": ["m0"]}

        main_mocks["load_history"].return_value = cached_history
        main_mocks["load_summary"].return_value = cached_summary

        summary, history = await _load_context("s1", "u1")

        assert summary == "Earlier discussion"
        assert history == cached_history
        # No DB calls were made
        main_mocks["cs_get_latest_summary"].assert_not_called()
        main_mocks["cs_get_messages_excluding_ids"].assert_not_called()

    async def test_rebuilds_from_db_on_cache_miss(self, main_mocks):
        main_mocks["load_history"].return_value = None  # cache miss
        main_mocks["load_summary"].return_value = None

        main_mocks["cs_get_latest_summary"].return_value = {
            "summary": "Rebuilt summary", "message_ids": ["m0"]
        }
        main_mocks["cs_get_messages_excluding_ids"].return_value = [
            {"id": "m1", "role": "user", "content": "What is halal?"}
        ]

        summary, history = await _load_context("s1", "u1")

        assert summary == "Rebuilt summary"
        assert len(history) == 1
        assert history[0]["role"] == "user"
        # Cache was seeded
        main_mocks["seed_history"].assert_called_once()
        main_mocks["save_summary"].assert_called_once()

    async def test_no_summary_row_returns_empty_summary(self, main_mocks):
        main_mocks["load_history"].return_value = None
        main_mocks["load_summary"].return_value = None
        main_mocks["cs_get_latest_summary"].return_value = None
        main_mocks["cs_get_messages_excluding_ids"].return_value = []

        summary, history = await _load_context("s1", "u1")

        assert summary == ""
        assert history == []


# ═══════════════════════════════════════════════════════════════════════
# _stream_and_persist — run agent, save answer, publish chunks
# ═══════════════════════════════════════════════════════════════════════

class TestStreamAndPersist:
    async def test_persists_result_and_publishes(self, main_mocks):
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "It is halal.", "documents": [{"doc": "cert1"}]}
        )

        await _stream_and_persist("u1", "s1", "Is it halal?", [])

        # Agent's response was saved to the DB
        main_mocks["cs_insert_message"].assert_called_once()
        call_args = main_mocks["cs_insert_message"].call_args
        assert call_args[0][0] == "s1"  # session_id
        assert call_args[0][1] == "assistant"  # role
        assert call_args[0][2] == "It is halal."  # response text

        # Response was appended to the history cache
        main_mocks["append_history"].assert_called_once()

        # Result was published to the user via pubsub
        main_mocks["publish_chunk"].assert_called()

    async def test_publishes_intermediate_chunks(self, main_mocks):
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "searching", "message": "Looking up certifications..."},
            {"type": "results", "response": "Found it!", "documents": []},
        )

        await _stream_and_persist("u1", "s1", "test", [])

        # Both chunks were published
        publish_calls = main_mocks["publish_chunk"].call_args_list
        published_types = [c[0][2]["type"] for c in publish_calls]
        assert "searching" in published_types
        assert "results" in published_types

    async def test_publishes_error_on_agent_crash(self, main_mocks):
        async def crash(*args, **kwargs):
            raise RuntimeError("Agent exploded")
            yield  # make it an async generator  # noqa: unreachable

        main_mocks["stream_agent"].return_value = crash()

        await _stream_and_persist("u1", "s1", "test", [])

        # Error was published to the user
        main_mocks["publish_chunk"].assert_called()
        last_call = main_mocks["publish_chunk"].call_args_list[-1]
        assert last_call[0][2] == ERROR_RESULT

    async def test_awaits_pending_user_persist_before_assistant_write(self, main_mocks):
        order = []

        async def fake_persist():
            order.append("user_persist")

        main_mocks["cs_insert_message"].side_effect = lambda *a, **kw: order.append("assistant_insert") or asyncio.coroutine(lambda: "msg-002")()

        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Answer", "documents": []}
        )

        task = asyncio.create_task(fake_persist())
        await _stream_and_persist("u1", "s1", "test", [], pending_user_persist=task)

        # User message persisted BEFORE the assistant message
        assert order.index("user_persist") < order.index("assistant_insert")


# ═══════════════════════════════════════════════════════════════════════
# run_prompt_pipeline — the core decision engine
# ═══════════════════════════════════════════════════════════════════════

class TestRunPromptPipeline:
    async def test_creates_session_if_not_exists(self, main_mocks):
        """Brand-new session: generate title, create in DB, clear caches."""
        main_mocks["is_session_known"].return_value = False
        main_mocks["cs_session_exists"].return_value = False  # doesn't exist yet
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Welcome!", "documents": []}
        )

        await run_prompt_pipeline("s1", "u1", "Hello")

        main_mocks["cs_create_session"].assert_called_once()
        main_mocks["mark_session_known"].assert_called()
        main_mocks["clear_history"].assert_called_with("s1")
        main_mocks["clear_summary"].assert_called_with("s1")
        main_mocks["clear_compaction"].assert_called_with("s1")

    async def test_runs_agent_normally_when_under_token_threshold(self, main_mocks):
        """Existing session, low token count → straight to the agent."""
        main_mocks["is_session_known"].return_value = True  # cache hit
        main_mocks["count_tokens"].return_value = 100  # way under 3000
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Here's your answer!", "documents": []}
        )

        await run_prompt_pipeline("s1", "u1", "Is chicken halal?")

        # Agent was invoked
        main_mocks["stream_agent"].assert_called_once()
        # No compaction was triggered
        main_mocks["save_compaction"].assert_not_called()

    async def test_pauses_with_compaction_request_when_over_threshold(self, main_mocks):
        """Token count over threshold with 0 declines → ask the user."""
        main_mocks["is_session_known"].return_value = True
        main_mocks["count_tokens"].return_value = SUMMARY_TOKEN_THRESHOLD + 500
        main_mocks["load_compaction"].return_value = {"phase": "idle", "declines": 0, "pending": None}

        await run_prompt_pipeline("s1", "u1", "Another question")

        # The prompt was stashed, not answered
        main_mocks["save_compaction"].assert_called_once()
        saved = main_mocks["save_compaction"].call_args[0][1]
        assert saved["phase"] == "awaiting"
        assert saved["pending"]["prompt"] == "Another question"

        # A compaction_request was published to the user
        main_mocks["publish_chunk"].assert_called()
        published = main_mocks["publish_chunk"].call_args[0][2]
        assert published["type"] == "compaction_request"

        # The agent was NOT invoked (paused)
        main_mocks["stream_agent"].assert_not_called()

    async def test_forces_compaction_after_three_declines(self, main_mocks):
        """Token count over threshold with 3 declines → forced compaction."""
        main_mocks["is_session_known"].return_value = True
        main_mocks["count_tokens"].return_value = SUMMARY_TOKEN_THRESHOLD * 4  # way over 3x threshold
        main_mocks["load_compaction"].return_value = {"phase": "idle", "declines": 3, "pending": None}
        main_mocks["compact_session"].return_value = ("Compacted summary", [{"id": "m5", "role": "user", "content": "latest"}], True)
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Answer after compaction", "documents": []}
        )

        await run_prompt_pipeline("s1", "u1", "Yet another question")

        # Compaction was forced
        main_mocks["compact_session"].assert_called_once()
        # And the agent still answered
        main_mocks["stream_agent"].assert_called_once()

    async def test_publishes_error_on_context_load_failure(self, main_mocks):
        """If the initial context load fails entirely, publish ERROR_RESULT."""
        main_mocks["is_session_known"].side_effect = RuntimeError("Valkey exploded")

        await run_prompt_pipeline("s1", "u1", "Hello")

        main_mocks["publish_chunk"].assert_called()
        published = main_mocks["publish_chunk"].call_args[0][2]
        assert published == ERROR_RESULT

    async def test_escalating_threshold_with_declines(self, main_mocks):
        """1 decline → threshold is 2x, so at 1.5x tokens the agent runs normally."""
        main_mocks["is_session_known"].return_value = True
        main_mocks["count_tokens"].return_value = int(SUMMARY_TOKEN_THRESHOLD * 1.5)
        main_mocks["load_compaction"].return_value = {"phase": "idle", "declines": 1, "pending": None}
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Still under the raised threshold", "documents": []}
        )

        await run_prompt_pipeline("s1", "u1", "Another question")

        # At 1.5x tokens with 1 decline (threshold 2x), we should be under → agent runs normally
        main_mocks["stream_agent"].assert_called_once()
        main_mocks["save_compaction"].assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# resume_after_confirm — user accepted compaction
# ═══════════════════════════════════════════════════════════════════════

class TestResumeAfterConfirm:
    async def test_runs_compaction_and_answers_paused_prompt(self, main_mocks):
        main_mocks["load_compaction"].return_value = {
            "phase": "awaiting", "declines": 0,
            "pending": {"prompt": "Is gelatin halal?"},
        }
        main_mocks["compact_session"].return_value = ("Summary after fold", [{"id": "m5", "role": "user", "content": "latest"}], True)
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Answer after compaction", "documents": []}
        )

        await resume_after_confirm("s1", "u1")

        main_mocks["compact_session"].assert_called_once()
        main_mocks["stream_agent"].assert_called_once()

    async def test_no_pending_prompt_clears_and_noops(self, main_mocks):
        main_mocks["load_compaction"].return_value = {
            "phase": "idle", "declines": 0, "pending": None,
        }

        await resume_after_confirm("s1", "u1")

        main_mocks["clear_compaction"].assert_called_once()
        main_mocks["compact_session"].assert_not_called()
        main_mocks["stream_agent"].assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# resume_after_decline — user rejected compaction
# ═══════════════════════════════════════════════════════════════════════

class TestResumeAfterDecline:
    async def test_bumps_declines_and_answers_with_full_context(self, main_mocks):
        main_mocks["load_compaction"].return_value = {
            "phase": "awaiting", "declines": 1,
            "pending": {"prompt": "What about E120?"},
        }
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Answer with full history", "documents": []}
        )

        await resume_after_decline("s1", "u1")

        # Declines was incremented from 1 → 2
        main_mocks["save_compaction"].assert_called_once()
        saved = main_mocks["save_compaction"].call_args[0][1]
        assert saved["declines"] == 2
        assert saved["phase"] == "idle"
        assert saved["pending"] is None

        # The agent ran with the full (un-compacted) context
        main_mocks["stream_agent"].assert_called_once()

    async def test_declines_capped_at_three(self, main_mocks):
        main_mocks["load_compaction"].return_value = {
            "phase": "awaiting", "declines": 3,
            "pending": {"prompt": "Another one"},
        }
        main_mocks["stream_agent"].return_value = _fake_stream(
            {"type": "results", "response": "Answer", "documents": []}
        )

        await resume_after_decline("s1", "u1")

        saved = main_mocks["save_compaction"].call_args[0][1]
        assert saved["declines"] == 3  # capped, not 4

    async def test_no_pending_prompt_clears_and_noops(self, main_mocks):
        main_mocks["load_compaction"].return_value = {
            "phase": "idle", "declines": 0, "pending": None,
        }

        await resume_after_decline("s1", "u1")

        main_mocks["clear_compaction"].assert_called_once()
        main_mocks["stream_agent"].assert_not_called()
