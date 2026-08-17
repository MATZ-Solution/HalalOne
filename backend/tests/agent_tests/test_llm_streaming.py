"""Layer 5 — `LLMs/llm.py` + the streaming / summarization layer of
`main_langgraph_agent.py`.

Everything below `workflow.compile()` is pinned here: the LLM configuration the
graph binds, the langgraph v2 streaming contract the front end depends on, and
the two public entry points (`run_agent`, `stream_agent`) plus compaction
(`summarize_conversation`, `compact_session`).

Three findings are pinned:

  * **FINDINGS.md #14** — `main_langgraph_agent` calls `load_dotenv(override=True)`
    at import (line 19), so importing it silently clobbers `conftest.py`'s
    environment shim (`APP_ENV=test`, dummy API keys) with the repo `.env`
    (`APP_ENV=development`, real keys). Proven by `KEEP_MESSAGES`: the documented
    default is `SUMMARY_KEEP_TURNS * 2` = 20, but `.env` sets
    `SUMMARY_KEEP_TURNS=1`, so the module comes up with `KEEP_MESSAGES == 2`.
    Pinned with `xfail(strict=True)`; this module restores the shim after import
    so the rest of the session stays hermetic.
  * **FINDINGS.md #15** — `format_results` (line 55) is dead code — only a
    commented-out call — that crashes on `None` company fields (web-sourced
    products carry no `companies`). Pinned as a characterisation test.
  * **FINDINGS.md #16** — `stream_agent`'s empty-query event is the one event
    without a `"type"` discriminator (success events are `{"type": "results", ...}`).
    Pinned as a characterisation test.

The v2 streaming contract is verified against a real, offline compiled graph
(rather than a mock) so a langgraph upgrade that changes the chunk shape — which
`stream_agent` unpacks with `chunk["type"]` / `chunk["data"]` — fails loudly here.
"""
import json
import os
from types import SimpleNamespace
from typing import TypedDict

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

import agents.langgraph_agent.main_langgraph_agent as main

# Finding #14: `main_langgraph_agent` calls `load_dotenv(override=True)` at import,
# which overrides the conftest shim with the repo .env (APP_ENV -> development,
# real API keys). Restore the shim so the rest of this session stays hermetic.
os.environ["APP_ENV"] = "test"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["CEREBRAS_API_KEY"] = "test-cerebras-key"
os.environ["FIREWORKS_AI_API_KEY"] = "test-fireworks-key"
os.environ["LOG_LEVEL"] = "CRITICAL"

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# LLM configuration contract
# ---------------------------------------------------------------------------


class TestLLMConfig:
    def test_extracter_llm_model(self):
        from agents.langgraph_agent.LLMs.llm import extracter_llm

        assert extracter_llm.model == "openai/gpt-oss-20b"

    def test_extracter_llm_is_deterministic_and_bounded(self):
        from agents.langgraph_agent.LLMs.llm import extracter_llm

        assert extracter_llm.temperature in (0, 1e-08)  # ChatGroq clamps 0 -> 1e-08
        assert extracter_llm.max_tokens == 300

    def test_final_extracter_llm_model(self):
        from agents.langgraph_agent.LLMs.llm import final_extracter_llm

        assert final_extracter_llm.model == "openai/gpt-oss-120b"

    def test_standard_llm_model(self):
        from agents.langgraph_agent.LLMs.llm import standard_llm

        assert standard_llm.model == "openai/gpt-oss-120b"

    def test_summarizer_llm_model(self):
        from agents.langgraph_agent.LLMs.llm import summarizer_llm

        assert summarizer_llm.model == "openai/gpt-oss-20b"

    def test_all_llms_run_at_zero_temperature(self):
        from langchain_core.language_models.chat_models import BaseChatModel

        from agents.langgraph_agent.LLMs.llm import (
            extracter_llm,
            final_extracter_llm,
            standard_llm,
            summarizer_llm,
        )

        for llm in (extracter_llm, final_extracter_llm, standard_llm, summarizer_llm):
            assert isinstance(llm, BaseChatModel)
            assert llm.temperature in (0, 1e-08)


# ---------------------------------------------------------------------------
# langgraph v2 streaming contract — the shape `stream_agent` unpacks
# ---------------------------------------------------------------------------


class TestV2StreamingContract:
    """Characterisation: `stream_agent` reads `chunk["type"]` / `chunk["data"]`
    from a `version="v2"` astream. Verified against a real offline graph so a
    langgraph upgrade that changes the shape trips this class."""

    @staticmethod
    def _build():
        class S(TypedDict):
            val: str

        def emit(state):
            get_stream_writer()({"evt": 1, "type": "web_source"})
            return {"val": "a"}

        graph = StateGraph(S)
        graph.add_node("node_a", emit)
        graph.add_edge(START, "node_a")
        graph.add_edge("node_a", END)
        return graph.compile()

    async def test_v2_chunks_are_dicts_with_type_and_data(self):
        app = self._build()
        chunks = [
            c
            async for c in app.astream(
                {"val": ""}, stream_mode=["updates", "custom"], version="v2"
            )
        ]
        assert chunks
        assert all(isinstance(c, dict) and {"type", "data"} <= set(c) for c in chunks)

    async def test_v2_custom_payload_passes_verbatim(self):
        app = self._build()
        custom = [
            c
            async for c in app.astream(
                {"val": ""}, stream_mode=["updates", "custom"], version="v2"
            )
            if c["type"] == "custom"
        ]
        assert custom[0]["data"] == {"evt": 1, "type": "web_source"}

    async def test_v2_updates_are_keyed_by_node_name(self):
        app = self._build()
        updates = [
            c
            async for c in app.astream(
                {"val": ""}, stream_mode=["updates", "custom"], version="v2"
            )
            if c["type"] == "updates"
        ]
        assert updates[0]["data"] == {"node_a": {"val": "a"}}


# ---------------------------------------------------------------------------
# stream_agent — the streaming entry point
# ---------------------------------------------------------------------------


class _FakeStreamAgent:
    def __init__(self, chunks):
        self._chunks = chunks
        self.calls = []

    async def astream(self, input, config=None, stream_mode=None, version=None):
        self.calls.append((input, config, stream_mode, version))
        for chunk in self._chunks:
            yield chunk


def _updates(node, state):
    return {"type": "updates", "ns": [], "data": {node: state}}


def _custom(data):
    return {"type": "custom", "ns": [], "data": data}


def _messages(message, node="search_node"):
    return {"type": "messages", "ns": [], "data": (message, {"langgraph_node": node})}


def _response_update(response="Done", products=None):
    payload = {"response": response, "products": products or []}
    return {"messages": [AIMessage(content=json.dumps(payload))]}


class TestStreamAgent:
    async def _collect(self, fake, query="q"):
        return [e async for e in main.stream_agent(query, [])]

    async def test_empty_query_yields_the_validation_event_without_streaming(self, monkeypatch):
        # Finding #16, fixed: this used to be the ONE event without a "type"
        # discriminator, so a client routing on event["type"] could not handle it with
        # the same branch it uses for every other event.
        fake = _FakeStreamAgent([])
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake, query="")
        assert events == [
            {"type": "results", "response": "Please enter a valid query", "documents": []}
        ]
        # The graph must not be started at all for an empty query.
        assert fake.calls == []

    async def test_every_streamed_event_carries_a_type(self, monkeypatch):
        # The invariant finding #16 was about: "type" is the protocol, so no event may
        # omit it. Guards the empty-query path and the normal path in one assertion.
        fake = _FakeStreamAgent(
            [_updates("response_node", _response_update("Found 1", [{"norm_name": "A"}]))]
        )
        monkeypatch.setattr(main, "search_agent", fake)

        for query in ("", "nuggets"):
            events = [e async for e in main.stream_agent(query, [])]
            assert events, f"{query!r} produced no events"
            assert all("type" in e for e in events), f"untyped event for query {query!r}"

    async def test_yields_final_results_from_response_node(self, monkeypatch):
        fake = _FakeStreamAgent(
            [_updates("response_node", _response_update("Found 2", [{"norm_name": "A"}]))]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events == [
            {"type": "results", "response": "Found 2", "documents": [{"norm_name": "A"}]}
        ]

    async def test_stops_after_the_first_response_node_update(self, monkeypatch):
        fake = _FakeStreamAgent(
            [
                _updates("response_node", _response_update("First")),
                _updates("response_node", _response_update("Second")),
            ]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events == [{"type": "results", "response": "First", "documents": []}]

    async def test_yields_results_from_the_error_handler(self, monkeypatch):
        apology = {"response": "Some error occured, please try again.", "products": []}
        fake = _FakeStreamAgent(
            [_updates("__default_error_handler__", {"messages": [AIMessage(content=json.dumps(apology))]})]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events == [{"type": "results", "response": apology["response"], "documents": []}]

    async def test_ignores_updates_from_unknown_nodes(self, monkeypatch):
        fake = _FakeStreamAgent(
            [
                _updates("some_other_node", {"messages": []}),
                _updates("response_node", _response_update("Ok")),
            ]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events == [{"type": "results", "response": "Ok", "documents": []}]

    async def test_yields_web_source_events(self, monkeypatch):
        source = {"type": "web_source", "url": "https://x", "title": "T", "favicon": "f", "highlights": ["h"]}
        fake = _FakeStreamAgent(
            [_custom(source), _updates("response_node", _response_update())]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events[0] == source
        assert events[-1]["type"] == "results"

    async def test_yields_search_results_events(self, monkeypatch):
        results = [{"canonical_id": "1"}]
        fake = _FakeStreamAgent(
            [
                _custom({"search_results": results, "tool": "KeywordFilterSearch"}),
                _updates("response_node", _response_update()),
            ]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events[0] == {"type": "search_results", "search_results": results, "tool": "KeywordFilterSearch"}

    async def test_empty_search_results_are_not_emitted(self, monkeypatch):
        fake = _FakeStreamAgent(
            [
                _custom({"search_results": [], "tool": "KeywordFilterSearch"}),
                _updates("response_node", _response_update("Nothing")),
            ]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events == [{"type": "results", "response": "Nothing", "documents": []}]

    async def test_keyword_tool_status_with_keywords_and_filters(self, monkeypatch):
        args = {"keyword_args": {"norm_name": "x"}, "filter_args": {"halal_status": "Halal"}}
        fake = _FakeStreamAgent(
            [_messages(SimpleNamespace(content_blocks=[], tool_calls=[{"name": "KeywordFilterSearch", "args": args, "id": "c1", "type": "tool_call"}])), _updates("response_node", _response_update())]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events[0] == {"type": "tool_status", "node": "search_node", "message": "Searching keywords", "tool": "KeywordFilterSearch", "args": args}

    async def test_keyword_tool_status_filters_only(self, monkeypatch):
        args = {"keyword_args": None, "filter_args": {"halal_status": "Halal"}}
        fake = _FakeStreamAgent(
            [_messages(SimpleNamespace(content_blocks=[], tool_calls=[{"name": "KeywordFilterSearch", "args": args, "id": "c1", "type": "tool_call"}])), _updates("response_node", _response_update())]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events[0]["message"] == "Applying filters"

    async def test_keyword_tool_status_keywords_only(self, monkeypatch):
        args = {"keyword_args": {"norm_name": "x"}, "filter_args": None}
        fake = _FakeStreamAgent(
            [_messages(SimpleNamespace(content_blocks=[], tool_calls=[{"name": "KeywordFilterSearch", "args": args, "id": "c1", "type": "tool_call"}])), _updates("response_node", _response_update())]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events[0]["message"] == "Searching relevant products"

    async def test_semantic_and_web_tool_status(self, monkeypatch):
        fake = _FakeStreamAgent(
            [
                _messages(SimpleNamespace(content_blocks=[], tool_calls=[{"name": "SemanticFilterSearch", "args": {"semantic_query": "x"}, "id": "c1", "type": "tool_call"}])),
                _messages(SimpleNamespace(content_blocks=[], tool_calls=[{"name": "WebSearch", "args": {"query": "x"}, "id": "c2", "type": "tool_call"}])),
                _updates("response_node", _response_update()),
            ]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events[0]["message"] == "Performing Semantic Search"
        assert events[1]["message"] == "Searching the web"

    async def test_yields_reasoning_events(self, monkeypatch):
        fake = _FakeStreamAgent(
            [
                _messages(SimpleNamespace(content_blocks=[{"type": "reasoning", "reasoning": "think step"}], tool_calls=[])),
                _updates("response_node", _response_update()),
            ]
        )
        monkeypatch.setattr(main, "search_agent", fake)
        events = await self._collect(fake)
        assert events[0] == {"type": "reasoning", "node": "search_node", "reasoning": "think step"}


# ---------------------------------------------------------------------------
# run_agent — the non-streaming entry point
# ---------------------------------------------------------------------------


class TestRunAgent:
    async def test_empty_query_short_circuits(self, monkeypatch):
        calls = []

        def invoke(*args, **kwargs):
            calls.append((args, kwargs))
            return {"messages": [AIMessage(content=json.dumps({"response": "x", "products": []}))]}

        monkeypatch.setattr(main, "search_agent", SimpleNamespace(invoke=invoke))
        result = await main.run_agent("")
        assert result == {"response": "Please enter a valid query", "documents": []}
        assert calls == []

    async def test_parses_final_message_into_response_and_documents(self, monkeypatch):
        products = [{"norm_name": "KitKat"}, {"norm_name": "Snickers"}]

        def invoke(input, config=None):
            assert input["user_prompt"] == "kitkat"
            return {"messages": [AIMessage(content=json.dumps({"response": "Found", "products": products}))]}

        monkeypatch.setattr(main, "search_agent", SimpleNamespace(invoke=invoke))
        result = await main.run_agent("kitkat")
        assert result["response"] == "Found"
        assert [p.norm_name for p in result["documents"]] == ["KitKat", "Snickers"]

    async def test_parses_the_apology_from_the_error_handler(self, monkeypatch):
        apology = {"response": "Some error occured, please try again.", "products": []}
        monkeypatch.setattr(
            main, "search_agent",
            SimpleNamespace(invoke=lambda input, config=None: {"messages": [AIMessage(content=json.dumps(apology))]}),
        )
        result = await main.run_agent("x")
        assert result == {"response": apology["response"], "documents": []}

    async def test_passes_the_supplied_config_through(self, monkeypatch):
        seen = {}

        def invoke(input, config=None):
            seen["config"] = config
            return {"messages": [AIMessage(content=json.dumps({"response": "r", "products": []}))]}

        monkeypatch.setattr(main, "search_agent", SimpleNamespace(invoke=invoke))
        await main.run_agent("q", config={"configurable": {"thread_id": "t-1"}})
        assert seen["config"] == {"configurable": {"thread_id": "t-1"}}


# ---------------------------------------------------------------------------
# summarize_conversation
# ---------------------------------------------------------------------------


class TestSummarizeConversation:
    def test_returns_the_summary_content(self, monkeypatch):
        monkeypatch.setattr(main, "summarizer_llm", SimpleNamespace(invoke=lambda msgs: AIMessage(content="Folded")))
        assert main.summarize_conversation([HumanMessage("hi")]) == ["Folded"]

    def test_returns_empty_list_when_the_model_says_nothing(self, monkeypatch):
        monkeypatch.setattr(main, "summarizer_llm", SimpleNamespace(invoke=lambda msgs: AIMessage(content="")))
        assert main.summarize_conversation([HumanMessage("hi")]) == []

    def test_builds_previous_summary_and_new_turns_markers(self, monkeypatch):
        captured = {}

        def invoke(msgs):
            captured["system"] = msgs[0].content
            captured["human"] = msgs[1].content
            return AIMessage(content="s")

        monkeypatch.setattr(main, "summarizer_llm", SimpleNamespace(invoke=invoke))
        main.summarize_conversation([HumanMessage("hi")], old_summary="Old")
        assert captured["system"] == main.SUMMARIZE_CONVERSATION_PROMPT
        assert captured["human"] == "PREVIOUS SUMMARY:\nOld\n\nNEW TURNS:\nUser: hi"

    def test_omits_the_previous_summary_block_when_absent(self, monkeypatch):
        captured = {}

        def invoke(msgs):
            captured["human"] = msgs[1].content
            return AIMessage(content="s")

        monkeypatch.setattr(main, "summarizer_llm", SimpleNamespace(invoke=invoke))
        main.summarize_conversation([HumanMessage("hi")])
        assert captured["human"] == "NEW TURNS:\nUser: hi"

    def test_ai_turns_are_labelled_halalify(self, monkeypatch):
        captured = {}

        def invoke(msgs):
            captured["human"] = msgs[1].content
            return AIMessage(content="s")

        monkeypatch.setattr(main, "summarizer_llm", SimpleNamespace(invoke=invoke))
        main.summarize_conversation([AIMessage(content="hi back")])
        assert captured["human"] == "NEW TURNS:\nHalalify: hi back"


class TestHistoryDictsToLc:
    def test_assistant_json_reduces_to_response_text(self):
        msgs = main._history_dicts_to_lc(
            [{"role": "assistant", "content": json.dumps({"response": "Answer", "products": []})}]
        )
        assert msgs[0].content == "Answer"

    def test_assistant_non_json_content_passes_through(self):
        msgs = main._history_dicts_to_lc([{"role": "assistant", "content": "plain text"}])
        assert msgs[0].content == "plain text"

    def test_human_role_maps_to_human_message(self):
        msgs = main._history_dicts_to_lc([{"role": "user", "content": "hi"}])
        assert isinstance(msgs[0], HumanMessage)
        assert msgs[0].content == "hi"

    def test_missing_content_defaults_to_empty(self):
        msgs = main._history_dicts_to_lc([{"role": "user"}])
        assert msgs[0].content == ""


class TestContextTokenCount:
    def test_prepends_the_summary_when_present(self):
        count = main.context_token_count("summary", [HumanMessage("hi")])
        assert isinstance(count, int) and count > 0


# ---------------------------------------------------------------------------
# compact_session
# ---------------------------------------------------------------------------


class TestCompactSession:
    async def test_noop_when_history_is_within_keep(self, monkeypatch):
        monkeypatch.setattr(main, "KEEP_MESSAGES", 2)
        history = [{"id": 1, "role": "user", "content": "hi"}]

        async def load_history(sid):
            return history

        async def load_summary(sid):
            return {"summary": "Old", "message_ids": [1]}

        async def unexpected(*args, **kwargs):
            raise AssertionError("should not persist on a no-op")

        monkeypatch.setattr(main.session_state, "load_history", load_history)
        monkeypatch.setattr(main.session_state, "load_summary", load_summary)
        monkeypatch.setattr(main.chat_store, "insert_summary", unexpected)
        monkeypatch.setattr(main.session_state, "save_summary", unexpected)
        monkeypatch.setattr(main.session_state, "seed_history", unexpected)

        summary, kept, did = await main.compact_session("s1")
        assert (summary, kept, did) == ("Old", history, False)

    async def test_folds_older_messages_and_persists(self, monkeypatch):
        monkeypatch.setattr(main, "KEEP_MESSAGES", 2)
        history = [{"id": i, "role": "user", "content": f"m{i}"} for i in range(1, 6)]
        calls = {}

        async def load_history(sid):
            return history

        async def load_summary(sid):
            return {"summary": "Old", "message_ids": [100]}

        async def insert_summary(sid, summary, ids):
            calls["insert"] = (sid, summary, ids)

        async def save_summary(sid, summary, ids):
            calls["save"] = (sid, summary, ids)

        async def seed_history(sid, kept):
            calls["seed"] = (sid, kept)

        monkeypatch.setattr(main, "KEEP_MESSAGES", 2)
        monkeypatch.setattr(main.session_state, "load_history", load_history)
        monkeypatch.setattr(main.session_state, "load_summary", load_summary)
        monkeypatch.setattr(main.session_state, "save_summary", save_summary)
        monkeypatch.setattr(main.session_state, "seed_history", seed_history)
        monkeypatch.setattr(main.chat_store, "insert_summary", insert_summary)
        monkeypatch.setattr(main, "summarize_conversation", lambda hist, old: ["New summary"])

        summary, kept, did = await main.compact_session("s1")
        assert did is True
        assert summary == "New summary"
        assert [m["id"] for m in kept] == [4, 5]
        assert calls["insert"] == ("s1", "New summary", [100, 1, 2, 3])
        assert calls["save"] == ("s1", "New summary", [100, 1, 2, 3])
        assert calls["seed"][0] == "s1"

    async def test_raises_when_the_summarizer_returns_nothing(self, monkeypatch):
        monkeypatch.setattr(main, "KEEP_MESSAGES", 2)
        history = [{"id": i, "role": "user", "content": "x"} for i in range(1, 6)]

        async def load_history(sid):
            return history

        async def load_summary(sid):
            return {}

        monkeypatch.setattr(main.session_state, "load_history", load_history)
        monkeypatch.setattr(main.session_state, "load_summary", load_summary)
        monkeypatch.setattr(main, "summarize_conversation", lambda hist, old: [])

        with pytest.raises(RuntimeError, match="summarizer returned no content"):
            await main.compact_session("s1")


# ---------------------------------------------------------------------------
# Finding pins
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="FINDINGS.md #14: load_dotenv(override=True) at import pulls SUMMARY_KEEP_TURNS=1 from .env, so KEEP_MESSAGES is 2 instead of the documented default of 20",
    strict=True,
)
def test_keep_messages_uses_the_documented_default_of_ten_turns():
    assert main.KEEP_MESSAGES == 20


@pytest.mark.parametrize(
    "companies,cert_bodies",
    [
        pytest.param(None, ["B"], id="no-companies"),
        pytest.param(["A"], None, id="no-cert-bodies"),
        pytest.param(None, None, id="neither"),
    ],
)
def test_format_results_tolerates_products_without_companies_or_cert_bodies(
    companies, cert_bodies
):
    # Finding #15, fixed: `' '.join(product.companies)` raised TypeError on web-sourced
    # products (verified=False), which carry neither field — precisely the products the
    # agent fell back to the web for. The helper is currently dead code (its only call
    # site is commented out), so this guards the crash for whoever re-enables it.
    product = SimpleNamespace(norm_name="X", companies=companies, cert_bodies=cert_bodies)
    main.format_results([product])  # must not raise


def test_format_results_still_logs_the_fields_it_has():
    product = SimpleNamespace(norm_name="X", companies=["Acme"], cert_bodies=["HFA"])
    main.format_results([product])  # must not raise
