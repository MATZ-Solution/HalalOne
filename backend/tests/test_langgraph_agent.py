"""Unit tests for `agents/langgraph_agent/main_langgraph_agent.py`.

The individual graph nodes, tools, and prompts are already covered by
`tests/agent_tests/`. This file tests the orchestration layer:

  - Pure helpers: `_history_dicts_to_lc`, `context_token_count`
  - `run_agent`: graph entrypoint + Pydantic parsing
  - `compact_session`: the Valkey/Supabase compaction coordinator
  - `stream_agent`: the async-generator that routes LangGraph stream events

Every external dependency (session_state, chat_store, the compiled graph,
and the summarizer LLM) is replaced by the `agent_mocks` fixture.
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from langchain.messages import HumanMessage, AIMessage

from agents.langgraph_agent.main_langgraph_agent import (
    _history_dicts_to_lc,
    context_token_count,
    compact_session,
    stream_agent,
    run_agent,
    KEEP_MESSAGES,
)

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════════
# _history_dicts_to_lc — pure conversion helper
# ═══════════════════════════════════════════════════════════════════════

class TestHistoryDictsToLc:
    def test_user_entry_becomes_human_message(self):
        history = [{"role": "user", "content": "Is this halal?"}]
        result = _history_dicts_to_lc(history)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Is this halal?"

    def test_assistant_entry_unpacks_json_response(self):
        """Assistant content is JSON-packed by the agent. The summarizer only
        needs the response text, not the product list."""
        history = [{"role": "assistant", "content": json.dumps({"response": "Yes!", "documents": [{"name": "cert"}]})}]
        result = _history_dicts_to_lc(history)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "Yes!"  # documents stripped

    def test_malformed_json_falls_back_to_raw_content(self):
        history = [{"role": "assistant", "content": "not valid json"}]
        result = _history_dicts_to_lc(history)

        assert isinstance(result[0], AIMessage)
        assert result[0].content == "not valid json"

    def test_mixed_history_preserves_order(self):
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": json.dumps({"response": "A1", "documents": []})},
            {"role": "user", "content": "Q2"},
        ]
        result = _history_dicts_to_lc(history)

        assert len(result) == 3
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)
        assert isinstance(result[2], HumanMessage)


# ═══════════════════════════════════════════════════════════════════════
# context_token_count — pure helper
# ═══════════════════════════════════════════════════════════════════════

class TestContextTokenCount:
    def test_counts_messages_without_summary(self):
        msgs = [HumanMessage("Hello"), AIMessage("Hi there")]
        count = context_token_count("", msgs)

        assert isinstance(count, int)
        assert count > 0

    def test_summary_adds_tokens(self):
        msgs = [HumanMessage("Hello")]
        without = context_token_count("", msgs)
        with_summary = context_token_count("Long prior conversation about halal food", msgs)

        assert with_summary > without


# ═══════════════════════════════════════════════════════════════════════
# run_agent — graph entrypoint
# ═══════════════════════════════════════════════════════════════════════

class TestRunAgent:
    async def test_empty_query_returns_validation_error(self, agent_mocks):
        result = await run_agent("")

        assert result["response"] == "Please enter a valid query"
        assert result["documents"] == []
        # The graph was never invoked
        agent_mocks["search_agent"].invoke.assert_not_called()

    async def test_happy_path_parses_graph_output(self, agent_mocks):
        """Mock the graph to return a FinalAnswerInput JSON, prove run_agent
        parses it into the expected dict shape."""
        final_json = json.dumps({"response": "Chicken is halal.", "products": []})
        fake_result = {
            "messages": [AIMessage(content=final_json)]
        }
        agent_mocks["search_agent"].invoke.return_value = fake_result

        result = await run_agent("Is chicken halal?")

        assert result["response"] == "Chicken is halal."
        assert result["documents"] == []


# ═══════════════════════════════════════════════════════════════════════
# compact_session — the compaction orchestrator
# ═══════════════════════════════════════════════════════════════════════

def _make_history(n: int) -> list[dict]:
    """Generate a dummy history of n entries with sequential IDs."""
    history = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"Message {i}" if role == "user" else json.dumps({"response": f"Reply {i}", "documents": []})
        history.append({"id": f"m{i}", "role": role, "content": content})
    return history


class TestCompactSession:
    async def test_noop_when_history_under_keep_messages(self, agent_mocks):
        """If the history is short, there's nothing to fold."""
        short_history = _make_history(KEEP_MESSAGES - 2)
        agent_mocks["load_history"].return_value = short_history

        summary, kept, did_compact = await compact_session("s1")

        assert did_compact is False
        assert kept == short_history
        # The LLM was never called
        agent_mocks["summarize_conversation"].assert_not_called()
        # Nothing was written to DB or cache
        agent_mocks["cs_insert_summary"].assert_not_called()

    async def test_happy_path_folds_old_messages(self, agent_mocks):
        """History longer than KEEP_MESSAGES: fold the old part, keep the tail."""
        full_history = _make_history(KEEP_MESSAGES + 10)
        agent_mocks["load_history"].return_value = full_history
        agent_mocks["load_summary"].return_value = {"summary": "Old summary", "message_ids": ["m-old"]}

        summary, kept, did_compact = await compact_session("s1")

        assert did_compact is True
        assert summary == "Folded summary of the conversation."
        assert len(kept) == KEEP_MESSAGES
        # The kept messages are the tail
        assert kept == full_history[-KEEP_MESSAGES:]
        # Summary was written to DB
        agent_mocks["cs_insert_summary"].assert_called_once()
        db_call = agent_mocks["cs_insert_summary"].call_args
        assert db_call[0][0] == "s1"  # session_id
        assert db_call[0][1] == "Folded summary of the conversation."
        # Previous ids ("m-old") are accumulated with the newly folded ids
        new_ids = db_call[0][2]
        assert "m-old" in new_ids
        # Cache was updated
        agent_mocks["save_summary"].assert_called_once()
        agent_mocks["seed_history"].assert_called_once()

    async def test_raises_on_empty_summarizer_output(self, agent_mocks):
        """If the LLM returns nothing, compact_session raises so the caller
        can fall back to the full context instead of saving a blank summary."""
        agent_mocks["load_history"].return_value = _make_history(KEEP_MESSAGES + 10)
        agent_mocks["summarize_conversation"].return_value = []  # empty!

        with pytest.raises(RuntimeError, match="summarizer returned no content"):
            await compact_session("s1")

        # Nothing was persisted
        agent_mocks["cs_insert_summary"].assert_not_called()

    async def test_raises_on_timeout(self, agent_mocks, monkeypatch):
        """The summarizer LLM is capped at SUMMARY_TIMEOUT_S. If it hangs,
        compact_session raises TimeoutError for the caller to handle."""
        import agents.langgraph_agent.main_langgraph_agent as agent_mod
        monkeypatch.setattr(agent_mod, "SUMMARY_TIMEOUT_S", 0.01)  # tiny timeout

        agent_mocks["load_history"].return_value = _make_history(KEEP_MESSAGES + 10)

        # Make the summarizer block longer than the timeout
        import time
        def slow_summarizer(*args, **kwargs):
            time.sleep(0.5)
            return ["Should never return"]
        agent_mocks["summarize_conversation"].side_effect = slow_summarizer

        with pytest.raises(asyncio.TimeoutError):
            await compact_session("s1")

        agent_mocks["cs_insert_summary"].assert_not_called()

    async def test_cache_reconciliation_on_partial_failure(self, agent_mocks):
        """If save_summary succeeds but seed_history fails, both caches are
        invalidated so the next turn rebuilds from the DB."""
        agent_mocks["load_history"].return_value = _make_history(KEEP_MESSAGES + 10)
        agent_mocks["save_summary"].return_value = True
        agent_mocks["seed_history"].return_value = False  # cache write failed!

        summary, kept, did_compact = await compact_session("s1")

        # Still returns successfully (the DB write succeeded)
        assert did_compact is True
        # But both caches were invalidated
        agent_mocks["clear_summary"].assert_called_once_with("s1")
        agent_mocks["clear_history"].assert_called_once_with("s1")

    async def test_id_accumulation_across_multiple_folds(self, agent_mocks):
        """Prove that previously-covered message IDs are carried forward."""
        agent_mocks["load_history"].return_value = _make_history(KEEP_MESSAGES + 4)
        agent_mocks["load_summary"].return_value = {
            "summary": "First fold", "message_ids": ["m-a", "m-b"]
        }

        await compact_session("s1")

        new_ids = agent_mocks["cs_insert_summary"].call_args[0][2]
        # Old ids preserved
        assert "m-a" in new_ids
        assert "m-b" in new_ids
        # New ids from the folded slice added
        assert "m0" in new_ids


# ═══════════════════════════════════════════════════════════════════════
# stream_agent — async generator routing LangGraph events
# ═══════════════════════════════════════════════════════════════════════

async def _collect(async_gen):
    """Drain an async generator into a list."""
    items = []
    async for item in async_gen:
        items.append(item)
    return items


class TestStreamAgent:
    async def test_empty_query_yields_validation_result(self, agent_mocks):
        chunks = await _collect(stream_agent("", []))

        assert len(chunks) == 1
        assert chunks[0]["type"] == "results"
        assert chunks[0]["response"] == "Please enter a valid query"

    async def test_response_node_update_yields_final_result(self, agent_mocks):
        """When the graph yields an 'updates' chunk from response_node,
        stream_agent should yield the final result."""
        final_json = json.dumps({"response": "It is halal.", "products": []})

        async def fake_astream(*args, **kwargs):
            yield {
                "type": "updates",
                "data": {
                    "response_node": {
                        "messages": [AIMessage(content=final_json)]
                    }
                }
            }

        agent_mocks["search_agent"].astream = fake_astream

        chunks = await _collect(stream_agent("Is it halal?", [HumanMessage("Is it halal?")]))

        # The final_result is yielded after the stream ends
        result_chunks = [c for c in chunks if c["type"] == "results"]
        assert len(result_chunks) == 1
        assert result_chunks[0]["response"] == "It is halal."

    async def test_error_handler_update_yields_error_result(self, agent_mocks):
        """When the graph's default error handler fires, its output
        is routed as the final result."""
        error_json = json.dumps({"response": "Something went wrong.", "products": []})

        async def fake_astream(*args, **kwargs):
            yield {
                "type": "updates",
                "data": {
                    "__default_error_handler__": {
                        "messages": [AIMessage(content=error_json)]
                    }
                }
            }

        agent_mocks["search_agent"].astream = fake_astream

        chunks = await _collect(stream_agent("test", [HumanMessage("test")]))

        result_chunks = [c for c in chunks if c["type"] == "results"]
        assert len(result_chunks) == 1
        assert result_chunks[0]["response"] == "Something went wrong."

    async def test_tool_call_yields_tool_status(self, agent_mocks):
        """When the graph streams a messages chunk with a tool_call,
        stream_agent yields a tool_status event."""
        mock_msg = MagicMock()
        mock_msg.content_blocks = []
        mock_msg.tool_calls = [
            {
                "name": "KeywordFilterSearch", 
                "args": {
                    "keyword_args": {"norm_name": "chicken"}, 
                    "filter_args": {"category_l1": "Food"}
                }
            }
        ]

        async def fake_astream(*args, **kwargs):
            yield {
                "type": "messages",
                "data": (mock_msg, {"langgraph_node": "search_node"})
            }
            # Must also yield a final result to end cleanly
            final_json = json.dumps({"response": "Done", "products": []})
            yield {
                "type": "updates",
                "data": {"response_node": {"messages": [AIMessage(content=final_json)]}}
            }

        agent_mocks["search_agent"].astream = fake_astream

        chunks = await _collect(stream_agent("chicken", [HumanMessage("chicken")]))

        tool_chunks = [c for c in chunks if c["type"] == "tool_status"]
        assert len(tool_chunks) == 1
        assert tool_chunks[0]["tool"] == "KeywordFilterSearch"
        assert tool_chunks[0]["message"] == "Searching keywords"

    async def test_custom_web_source_yields_web_source_event(self, agent_mocks):
        """Custom events with type=web_source are forwarded as web_source chunks."""
        async def fake_astream(*args, **kwargs):
            yield {
                "type": "custom",
                "data": {
                    "type": "web_source",
                    "url": "https://example.com",
                    "title": "Halal Guide",
                    "favicon": "https://example.com/favicon.ico",
                    "highlights": ["relevant text"],
                }
            }
            final_json = json.dumps({"response": "Done", "products": []})
            yield {
                "type": "updates",
                "data": {"response_node": {"messages": [AIMessage(content=final_json)]}}
            }

        agent_mocks["search_agent"].astream = fake_astream

        chunks = await _collect(stream_agent("test", [HumanMessage("test")]))

        web_chunks = [c for c in chunks if c["type"] == "web_source"]
        assert len(web_chunks) == 1
        assert web_chunks[0]["url"] == "https://example.com"
        assert web_chunks[0]["title"] == "Halal Guide"

    async def test_custom_search_results_yields_search_results_event(self, agent_mocks):
        """Custom events with search_results are forwarded as search_results chunks."""
        async def fake_astream(*args, **kwargs):
            yield {
                "type": "custom",
                "data": {
                    "search_results": [{"name": "Product A"}],
                    "tool": "KeywordFilterSearch",
                }
            }
            final_json = json.dumps({"response": "Done", "products": []})
            yield {
                "type": "updates",
                "data": {"response_node": {"messages": [AIMessage(content=final_json)]}}
            }

        agent_mocks["search_agent"].astream = fake_astream

        chunks = await _collect(stream_agent("test", [HumanMessage("test")]))

        sr_chunks = [c for c in chunks if c["type"] == "search_results"]
        assert len(sr_chunks) == 1
        assert sr_chunks[0]["search_results"] == [{"name": "Product A"}]
        assert sr_chunks[0]["tool"] == "KeywordFilterSearch"

    async def test_reasoning_block_yields_reasoning_event(self, agent_mocks):
        """When the LLM emits reasoning content blocks, they are yielded as
        reasoning events."""
        mock_msg = MagicMock()
        mock_msg.content_blocks = [{"type": "reasoning", "reasoning": "Thinking about halal status..."}]
        mock_msg.tool_calls = []

        async def fake_astream(*args, **kwargs):
            yield {
                "type": "messages",
                "data": (mock_msg, {"langgraph_node": "classify_intent"})
            }
            final_json = json.dumps({"response": "Done", "products": []})
            yield {
                "type": "updates",
                "data": {"response_node": {"messages": [AIMessage(content=final_json)]}}
            }

        agent_mocks["search_agent"].astream = fake_astream

        chunks = await _collect(stream_agent("test", [HumanMessage("test")]))

        reasoning_chunks = [c for c in chunks if c["type"] == "reasoning"]
        assert len(reasoning_chunks) == 1
        assert reasoning_chunks[0]["reasoning"] == "Thinking about halal status..."
        assert reasoning_chunks[0]["node"] == "classify_intent"
