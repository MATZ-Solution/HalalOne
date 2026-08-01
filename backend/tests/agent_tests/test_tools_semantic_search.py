"""Layer 2 — `SemanticFilterSearch` in `agents/langgraph_agent/tools/tools.py`.

The sibling of `KeywordFilterSearch` (see `test_tools_keyword_search.py`): instead of
keyword matching it turns the query into an embedding and asks Typesense for the 10
nearest vectors. Like its sibling, this file never asserts on search quality — the
embedding model and the Typesense client are both faked. It asserts on the tool's own
decisions:

  * what it embeds and how the vector is serialised,
  * the exact `multi_search.perform` payload it sends,
  * how `filter_args` becomes a `filter_by` expression,
  * how a raw Typesense response is unwrapped into documents, and
  * which failures degrade to `[]` vs. which ones escape (FINDINGS.md #7).

The tool is exercised through `.invoke({...})` because that is how `tool_node` calls it,
so `SemanticFilterInput` schema coercion (a raw dict becoming the args model) is covered
too.

Note the `filter_by` assertions only check that the meaningful clause survives. The full
string today also carries spurious `field:="None"` clauses for unset fields — that is the
bug pinned in `test_utils.py::TestKnownDefects` (FINDINGS.md #1), not a property of this
tool, and asserting it here would duplicate Layer 1's xfail.
"""
from types import SimpleNamespace

import pytest

from agents.langgraph_agent.tools.tools import SemanticFilterSearch

pytestmark = pytest.mark.unit


def search_entry(fake_ts_client, index=0):
    """The single search entry from the recorded `multi_search.perform` call.

    `perform` is called with two positional args: `({"searches": [...]}, {})`, so the
    entry lives at `args[0]["searches"][0]`.
    """
    return fake_ts_client.perform.calls[index]["args"][0]["searches"][0]


class TestEmbedding:
    """The semantic query is embedded, and the vector is serialised into the query."""

    def test_embeds_the_semantic_query(self, fake_embedding_model, fake_ts_client):
        SemanticFilterSearch.invoke({"semantic_query": "a calcium-rich snack for children"})

        assert fake_embedding_model.calls == ["a calcium-rich snack for children"]

    def test_vector_query_serialises_the_embedding(
        self, fake_embedding_model, fake_ts_client
    ):
        # fake_embedding_model is deterministic: [0.1, 0.2, 0.3].
        SemanticFilterSearch.invoke({"semantic_query": "x"})

        entry = search_entry(fake_ts_client)
        assert entry["vector_query"] == "embedding:([0.1,0.2,0.3], k:10)"

    def test_embedding_is_requested_before_any_search(self, fake_embedding_model, fake_ts_client):
        # The embed call must happen before the Typesense call, and its result must be
        # what reaches the vector_query.
        SemanticFilterSearch.invoke({"semantic_query": "x"})

        assert fake_embedding_model.calls == ["x"]
        assert fake_ts_client.perform.called


class TestRequestConstruction:
    """The payload sent to `multi_search.perform`."""

    def test_single_search_entry_with_static_fields(
        self, fake_embedding_model, fake_ts_client
    ):
        SemanticFilterSearch.invoke({"semantic_query": "x"})

        assert fake_ts_client.perform.call_count == 1
        searches = fake_ts_client.perform.calls[0]["args"][0]["searches"]
        assert len(searches) == 1
        assert searches[0]["collection"] == "halal_products"
        assert searches[0]["q"] == "*"
        assert searches[0]["per_page"] == 10
        assert searches[0]["exclude_fields"] == "embedding"

    def test_no_filters_omits_filter_by(self, fake_embedding_model, fake_ts_client):
        SemanticFilterSearch.invoke({"semantic_query": "x"})

        assert "filter_by" not in search_entry(fake_ts_client)

    def test_explicit_null_filters_omit_filter_by(
        self, fake_embedding_model, fake_ts_client
    ):
        # The prompt tells the LLM to pass null for an absent group, so nulls arrive
        # routinely and must behave exactly like omitting the argument.
        SemanticFilterSearch.invoke({"semantic_query": "x", "filter_args": None})

        assert "filter_by" not in search_entry(fake_ts_client)

    def test_filters_are_included_as_filter_by(
        self, fake_embedding_model, fake_ts_client
    ):
        # Only the meaningful clause is asserted; the spurious `:="None"` clauses are
        # FINDINGS.md #1, pinned at Layer 1 (see module docstring).
        SemanticFilterSearch.invoke(
            {"semantic_query": "x", "filter_args": {"halal_status": "halal"}}
        )

        filter_by = search_entry(fake_ts_client)["filter_by"]
        assert 'halal_status:="halal"' in filter_by

    def test_multiple_filters_are_combined(self, fake_embedding_model, fake_ts_client):
        SemanticFilterSearch.invoke(
            {
                "semantic_query": "x",
                "filter_args": {"halal_status": "halal", "category_l1": "food"},
            }
        )

        filter_by = search_entry(fake_ts_client)["filter_by"]
        assert 'halal_status:="halal"' in filter_by
        assert 'category_l1:="food"' in filter_by


class TestResponseParsing:
    """A raw Typesense `multi_search` response is unwrapped to documents."""

    def test_hits_are_unwrapped_to_documents(self, fake_embedding_model, fake_ts_client, make_product):
        product = make_product("p1")
        fake_ts_client.perform.set(
            returns={"results": [{"hits": [{"document": product}, {"document": make_product("p2")}]}]}
        )

        result = SemanticFilterSearch.invoke({"semantic_query": "x"})

        assert result == [product, make_product("p2")]
        assert all(isinstance(d, dict) for d in result)

    def test_no_hits_returns_empty_list(self, fake_embedding_model, fake_ts_client):
        # fake_ts_client defaults to `{"results": [{"hits": []}]}`.
        assert SemanticFilterSearch.invoke({"semantic_query": "x"}) == []

    def test_hits_null_returns_empty_list(self, fake_embedding_model, fake_ts_client):
        # A JSON `null` `hits` is not an iterable, but the `if hits else []` guard treats
        # it as "no results" rather than crashing on the list comprehension.
        fake_ts_client.perform.set(returns={"results": [{"hits": None}]})

        assert SemanticFilterSearch.invoke({"semantic_query": "x"}) == []


class TestDegradedResponses:
    """Malformed responses are swallowed by the try/except and return `[]`.

    Unlike `KeywordFilterSearch` (FINDINGS.md #5/#6), this tool's parsing lives inside a
    broad `except Exception`, so a surprising response shape degrades instead of crashing
    the node. These characterise that contract.
    """

    @pytest.mark.parametrize(
        "response",
        [
            pytest.param({}, id="missing-results-key"),
            pytest.param({"results": []}, id="empty-results-list"),
            pytest.param({"results": [{"hits": [{"id": "no-document-key"}]}]}, id="hit-without-document"),
        ],
    )
    def test_malformed_response_degrades_to_empty(
        self, fake_embedding_model, fake_ts_client, response
    ):
        fake_ts_client.perform.set(returns=response)

        assert SemanticFilterSearch.invoke({"semantic_query": "x"}) == []


class TestFailurePaths:
    """Which failures degrade to `[]` and which escape the tool."""

    def test_multi_search_failure_degrades_to_empty(
        self, fake_embedding_model, fake_ts_client, monkeypatch
    ):
        logged = []

        class FakeLog:
            def error(self, event, **kw):
                logged.append((event, kw))

        monkeypatch.setattr("agents.langgraph_agent.tools.tools.log", FakeLog())
        fake_ts_client.perform.set(side_effect=[RuntimeError("typesense down")])

        assert SemanticFilterSearch.invoke({"semantic_query": "x"}) == []

        (event, kw) = logged[0]
        assert event == "tool.semantic_search.failed"
        assert kw["error_type"] == "RuntimeError"

    def test_embedding_failure_degrades_to_no_results(
        self, fake_embedding_model, fake_ts_client, monkeypatch
    ):
        # Finding #7, fixed: `embed_query` is a network round-trip to Fireworks and now
        # runs inside the try/except. A provider outage degrades to "no products found"
        # like every other failure in this tool, instead of escaping and failing the node.
        logged = []

        class FakeLog:
            def error(self, event, **kw):
                logged.append((event, kw))

        class BoomEmbedding:
            def embed_query(self, text):
                raise RuntimeError("embedding provider down")

        monkeypatch.setattr("agents.langgraph_agent.tools.tools.log", FakeLog())
        monkeypatch.setattr(
            "agents.langgraph_agent.tools.tools.embedding_model", BoomEmbedding()
        )

        assert SemanticFilterSearch.invoke({"semantic_query": "x"}) == []

        # Degrading silently would hide a provider outage, so the failure must still log.
        (event, kw) = logged[0]
        assert event == "tool.semantic_search.failed"
        assert kw["error_type"] == "RuntimeError"

    def test_embedding_failure_never_reaches_typesense(
        self, fake_embedding_model, fake_ts_client, monkeypatch
    ):
        class BoomEmbedding:
            def embed_query(self, text):
                raise RuntimeError("embedding provider down")

        monkeypatch.setattr("agents.langgraph_agent.tools.tools.log", SimpleNamespace(error=lambda *a, **k: None))
        monkeypatch.setattr(
            "agents.langgraph_agent.tools.tools.embedding_model", BoomEmbedding()
        )

        SemanticFilterSearch.invoke({"semantic_query": "x"})
        assert fake_ts_client.perform.called is False


class TestSchemaCoercion:
    """`SemanticFilterInput` coercion, exercised via `.invoke()`."""

    def test_semantic_query_is_required(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SemanticFilterSearch.invoke({})

    def test_dict_filter_args_are_coerced_to_model(
        self, fake_embedding_model, fake_ts_client
    ):
        # A raw dict arrives from the LLM; Pydantic turns it into a FilterArgs.
        SemanticFilterSearch.invoke(
            {"semantic_query": "x", "filter_args": {"halal_status": "halal"}}
        )

        assert 'halal_status:="halal"' in search_entry(fake_ts_client)["filter_by"]

    def test_non_dict_filter_args_is_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SemanticFilterSearch.invoke({"semantic_query": "x", "filter_args": "food"})


class TestToolContract:
    """What the LLM and `tool_node` rely on."""

    def test_tool_name_is_stable(self):
        # `search_tools_by_name` in node.py keys on this, and the prompt names it.
        assert SemanticFilterSearch.name == "SemanticFilterSearch"

    def test_description_is_exposed_to_the_llm(self):
        assert SemanticFilterSearch.description

    def test_semantic_query_is_required_and_filter_args_is_optional(self):
        schema = SemanticFilterSearch.args_schema.model_json_schema()
        assert "semantic_query" in schema["required"]
        assert "filter_args" not in schema["required"]

    def test_always_returns_a_list(self, fake_embedding_model, fake_ts_client):
        # tool_node does `if not observation` then `search_results.extend(observation)`,
        # so anything non-list would corrupt state.
        assert isinstance(SemanticFilterSearch.invoke({"semantic_query": "x"}), list)
