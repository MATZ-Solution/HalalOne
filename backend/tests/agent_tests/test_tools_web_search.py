"""Layer 2 — `WebSearch` in `agents/langgraph_agent/tools/tools.py`.

The last-resort tool: when both DB search tools come back empty, the LLM escalates to
`WebSearch`, which asks Exa to *synthesise* a product from live web sources and streams
each source to the client as it is found. The product is unverified by definition and
carries per-field grounding.

These tests exercise the tool through `.invoke()` with `stream_web_search` replaced by a
scripted generator (the same pattern as the other tools, where the DB client is faked).
`get_stream_writer` is faked too, so the source-streaming behaviour can be asserted.

One outright defect is pinned here — FINDINGS.md #9. Exa's docs say `stream: true` returns
OpenAI-compatible chat-completion chunks (`data:` frames shaped
`{"object": "chat.completion.chunk", "choices": [{delta: ...}]}`), but the tool parses
hand-rolled `{"type": "results"|"done"}` events. `TestExaStreamingContract` pins both
sides of that gap.
"""
import pytest

from agents.langgraph_agent.tools.tools import WebSearch

pytestmark = pytest.mark.unit


def results_event(*sources):
    return {"type": "results", "results": list(sources)}


DONE_EVENT = {
    "type": "done",
    "output": {
        "content": {"norm_name": "KitKat", "companies": ["Nestle"]},
        "grounding": [{"field": "norm_name", "citations": ["https://a"]}],
    },
}

# The exact frame shape Exa's docs (Search API guide) document for `stream: true`.
EXA_DOCUMENTED_CHUNK = {
    "object": "chat.completion.chunk",
    "choices": [
        {
            "index": 0,
            "delta": {
                "role": "assistant",
                "content": '{"norm_name": "KitKat", "companies": ["Nestle"]}',
            },
            "finish_reason": None,
        }
    ],
}


@pytest.fixture
def fake_stream(monkeypatch):
    """Replace `stream_web_search` where WebSearch uses it, with a scripted sequence.

    `state["events"]` is what the generator yields per call; `state["calls"]` records the
    arguments so tests can assert the query is passed through.
    """
    state = {"events": [], "calls": []}

    def make_stream(*args, **kwargs):
        state["calls"].append({"args": args, "kwargs": kwargs})
        yield from state["events"]

    monkeypatch.setattr(
        "agents.langgraph_agent.tools.tools.stream_web_search", make_stream, raising=True
    )
    return state


class TestExaStreamingContract:
    """FINDINGS.md #9 — the SSE frame format the tool expects vs. the one Exa sends.

    Exa's docs state that `stream: true` returns OpenAI-compatible chat-completion chunks
    (each `data:` frame is `{"object": "chat.completion.chunk", "choices": [...]}`). The
    tool instead reads `event["type"]` for hand-rolled "results"/"done" events, so a real
    Exa frame matches neither branch and the tool returns `[]` — the web fallback can
    never synthesise a product against the real API.
    """

    def test_documented_exa_chunk_is_ignored(self, fake_stream, stream_writer):
        # Characterisation of the current behaviour: the documented chunk has no "type"
        # key, so `etype = event.get("type")` is None and neither branch fires.
        fake_stream["events"] = [EXA_DOCUMENTED_CHUNK]

        assert WebSearch.invoke({"query": "x"}) == []
        assert stream_writer.call_count == 0

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "BUG: stream_web_search/WebSearch parse {'type': 'results'|'done'} events, "
            "but Exa's docs say stream=true returns OpenAI-compatible chunks "
            "({'object': 'chat.completion.chunk', 'choices': [{'delta': {...}}]}). A real "
            "Exa frame therefore never matches either branch and WebSearch always returns "
            "[]. Fix: assemble choices[0].delta.content into a product (and stream "
            "sources from the deltas), matching the documented format."
        ),
    )
    def test_documented_exa_chunk_produces_a_product(self, fake_stream, stream_writer):
        fake_stream["events"] = [EXA_DOCUMENTED_CHUNK]

        result = WebSearch.invoke({"query": "x"})

        assert len(result) == 1
        assert result[0]["norm_name"] == "KitKat"


class TestHappyPath:
    def test_returns_the_synthesized_product(self, fake_stream, stream_writer):
        fake_stream["events"] = [
            results_event({"url": "https://a"}),
            DONE_EVENT,
        ]

        result = WebSearch.invoke({"query": "is kitkat halal"})

        assert len(result) == 1
        assert result[0]["norm_name"] == "KitKat"
        assert result[0]["companies"] == ["Nestle"]

    def test_query_is_passed_through_to_the_stream(self, fake_stream, stream_writer):
        fake_stream["events"] = [DONE_EVENT]

        WebSearch.invoke({"query": "is kitkat halal"})

        assert fake_stream["calls"][0]["args"] == ("is kitkat halal",)

    def test_product_is_marked_unverified_with_halal_canonical_id(
        self, fake_stream, stream_writer
    ):
        fake_stream["events"] = [DONE_EVENT]

        (product,) = WebSearch.invoke({"query": "x"})

        assert product["verified"] is False
        assert product["canonical_id"].startswith("halal_")
        assert len(product["canonical_id"]) == len("halal_") + 8
        assert all(c in "0123456789abcdef" for c in product["canonical_id"][6:])

    def test_grounding_is_attached(self, fake_stream, stream_writer):
        fake_stream["events"] = [DONE_EVENT]

        (product,) = WebSearch.invoke({"query": "x"})

        assert product["grounding"] == DONE_EVENT["output"]["grounding"]

    def test_missing_grounding_defaults_to_empty_list(self, fake_stream, stream_writer):
        fake_stream["events"] = [{"type": "done", "output": {"content": {"norm_name": "K"}}}]

        (product,) = WebSearch.invoke({"query": "x"})

        assert product["grounding"] == []

    def test_multiple_events_are_handled_in_order(self, fake_stream, stream_writer):
        # Sources stream first, the synthesis arrives last, product is returned once.
        fake_stream["events"] = [
            results_event({"url": "https://a"}, {"url": "https://b"}),
            DONE_EVENT,
        ]

        assert len(WebSearch.invoke({"query": "x"})) == 1


class TestSourceStreaming:
    """Each web source found is streamed to the client as a `web_source` message."""

    def test_results_are_streamed_to_the_writer(self, fake_stream, stream_writer):
        fake_stream["events"] = [
            results_event({"url": "https://a", "title": "A", "favicon": "f", "highlights": ["x"]}),
            DONE_EVENT,
        ]

        WebSearch.invoke({"query": "x"})

        assert stream_writer.call_count == 1
        assert stream_writer.calls[0]["args"][0] == {
            "type": "web_source",
            "url": "https://a",
            "title": "A",
            "favicon": "f",
            "highlights": ["x"],
        }

    def test_missing_source_fields_default_to_none_or_empty(self, fake_stream, stream_writer):
        fake_stream["events"] = [results_event({"url": "https://b"})]

        WebSearch.invoke({"query": "x"})

        msg = stream_writer.calls[0]["args"][0]
        assert msg["title"] is None
        assert msg["favicon"] is None
        assert msg["highlights"] == []

    def test_multiple_sources_each_get_a_message(self, fake_stream, stream_writer):
        fake_stream["events"] = [
            results_event({"url": "https://a"}, {"url": "https://b"}),
            DONE_EVENT,
        ]

        WebSearch.invoke({"query": "x"})

        assert [c["args"][0]["url"] for c in stream_writer.calls] == ["https://a", "https://b"]

    def test_results_without_writer_are_skipped_not_crashed(self, fake_stream, monkeypatch):
        # get_stream_writer raises when the graph isn't running in streaming mode; the
        # tool must still run the search, just without the live source feed.
        def boom():
            raise RuntimeError("no streaming context")

        monkeypatch.setattr("agents.langgraph_agent.tools.tools.get_stream_writer", boom, raising=True)
        fake_stream["events"] = [results_event({"url": "https://a"}), DONE_EVENT]

        assert len(WebSearch.invoke({"query": "x"})) == 1


class TestDegradedStreams:
    """No product, no synthesis event, no norm_name -> the honest answer is `[]`."""

    def test_no_events_returns_empty_list(self, fake_stream, stream_writer):
        assert WebSearch.invoke({"query": "x"}) == []

    def test_results_without_done_returns_empty_list(self, fake_stream, stream_writer):
        fake_stream["events"] = [results_event({"url": "https://a"})]

        assert WebSearch.invoke({"query": "x"}) == []

    def test_done_without_output_returns_empty_list(self, fake_stream, stream_writer):
        fake_stream["events"] = [{"type": "done"}]

        assert WebSearch.invoke({"query": "x"}) == []

    def test_done_without_norm_name_returns_empty_list(self, fake_stream, stream_writer):
        fake_stream["events"] = [
            {"type": "done", "output": {"content": {"companies": ["Nestle"]}}}
        ]

        assert WebSearch.invoke({"query": "x"}) == []

    def test_unknown_event_types_are_ignored(self, fake_stream, stream_writer):
        fake_stream["events"] = [
            {"type": "progress", "note": "searching..."},
            DONE_EVENT,
        ]

        assert len(WebSearch.invoke({"query": "x"})) == 1


class TestFailurePaths:
    def test_stream_exception_degrades_to_empty_and_logs(self, fake_stream, stream_writer, monkeypatch):
        logged = []

        class FakeLog:
            def error(self, event, **kw):
                logged.append((event, kw))

        monkeypatch.setattr("agents.langgraph_agent.tools.tools.log", FakeLog())

        def broken(*args, **kwargs):
            raise RuntimeError("exa stream died")
            yield

        monkeypatch.setattr(
            "agents.langgraph_agent.tools.tools.stream_web_search", broken, raising=True
        )

        assert WebSearch.invoke({"query": "x"}) == []
        assert logged == [
            (
                "tool.web_search.failed",
                {"error": "exa stream died", "error_type": "RuntimeError"},
            )
        ]

    def test_writer_failure_degrades_to_empty(self, fake_stream, stream_writer):
        # The client websocket write is inside the same try/except as the stream, so a
        # failed write aborts the whole search rather than crashing the node. This is a
        # characterisation: moving the writer out of the guard would change it.
        fake_stream["events"] = [results_event({"url": "https://a"}), DONE_EVENT]
        stream_writer.set(side_effect=[RuntimeError("websocket closed")])

        assert WebSearch.invoke({"query": "x"}) == []


class TestToolContract:
    """What the LLM and `tool_node` rely on."""

    def test_tool_name_is_stable(self):
        # `search_tools_by_name` in node.py keys on this, and the prompt names it.
        assert WebSearch.name == "WebSearch"

    def test_description_is_exposed_to_the_llm(self):
        assert WebSearch.description

    def test_query_is_required(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WebSearch.invoke({})

    def test_always_returns_a_list(self, fake_stream, stream_writer):
        # tool_node does `if not observation` then `search_results.extend(observation)`,
        # so anything non-list would corrupt state.
        assert isinstance(WebSearch.invoke({"query": "x"}), list)
