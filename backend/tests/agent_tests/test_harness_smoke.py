"""Harness self-check: proves the fixtures in `tests/conftest.py` still bind.

Every fixture patches with `raising=True`, so if a symbol in the agent module is renamed
or an import is dropped, these fail immediately with a clear message instead of the
Layer 2+ tests failing for a confusing reason (or, worse, silently hitting the network).
"""
import pytest

pytestmark = pytest.mark.unit


def test_tools_module_imports_without_credentials_or_network():
    # tools.py transitively imports embeddings.py and config.typesense_client, both of
    # which do work at import time. This is the check that conftest's env shim holds.
    from agents.langgraph_agent.tools import tools

    assert tools.KeywordFilterSearch.name == "KeywordFilterSearch"
    assert tools.SemanticFilterSearch.name == "SemanticFilterSearch"
    assert tools.WebSearch.name == "WebSearch"


def test_fake_search_collection_replaces_the_real_one(fake_search_collection):
    from agents.langgraph_agent.tools import tools

    assert tools.search_collection is fake_search_collection
    assert fake_search_collection.called is False


def test_fake_embedding_model_is_deterministic_and_offline(fake_embedding_model):
    from agents.langgraph_agent.tools import tools

    assert tools.embedding_model is fake_embedding_model
    assert tools.embedding_model.embed_query("anything") == [0.1, 0.2, 0.3]
    assert fake_embedding_model.calls == ["anything"]


def test_fake_ts_client_replaces_the_real_one(fake_ts_client):
    from agents.langgraph_agent.tools import tools

    assert tools.TS_CLIENT is fake_ts_client
    assert fake_ts_client.perform is fake_ts_client.multi_search.perform


def test_stream_writer_captures_emitted_payloads(stream_writer):
    from agents.langgraph_agent.tools import tools

    tools.get_stream_writer()({"type": "web_source", "url": "https://example.test"})
    assert stream_writer.call_count == 1
    assert stream_writer.calls[0]["args"][0]["url"] == "https://example.test"


class TestRecorderSemantics:
    """The Recorder is test infrastructure, so its own contract is worth pinning."""

    def test_returns_replays_the_same_value(self, recorder):
        rec = recorder(returns=[{"id": 1}])
        assert rec() == [{"id": 1}]
        assert rec() == [{"id": 1}]
        assert rec.call_count == 2

    def test_side_effect_is_consumed_in_order(self, recorder):
        rec = recorder(side_effect=[["first"], []])
        assert rec() == ["first"]
        assert rec() == []

    def test_side_effect_entry_that_is_an_exception_is_raised(self, recorder):
        rec = recorder(side_effect=[RuntimeError("typesense down")])
        with pytest.raises(RuntimeError, match="typesense down"):
            rec()

    def test_exhausted_side_effect_fails_loudly(self, recorder):
        rec = recorder(side_effect=[[]])
        rec()
        with pytest.raises(AssertionError, match="side_effect list is exhausted"):
            rec()

    def test_records_call_arguments(self, recorder):
        rec = recorder()
        rec("positional", query="nuggets")
        assert rec.calls[0]["args"] == ("positional",)
        assert rec.kwargs_at(0) == {"query": "nuggets"}
