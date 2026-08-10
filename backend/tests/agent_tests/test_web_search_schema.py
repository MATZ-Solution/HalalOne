"""Layer 2 — `WEB_OUTPUT_SCHEMA` in `agents/langgraph_agent/tools/web_search.py`.

The web-fallback path (`WebSearch`) asks Exa to synthesise a product object against a
structured-output schema; `WEB_OUTPUT_SCHEMA` is that contract. It is the one place a
syntax error, a field-name drift, or a schema that outgrows Exa's limits fails *silently*
at runtime — Exa rejects the request, `stream_web_search` yields nothing, `WebSearch`
returns `[]`, and the user just sees "no products found". So the schema is worth pinning
precisely, the same way `build_filter_string` was.

These tests are contract guards over read-only data. Two Exa constraints (from Exa's
docs) anchor them:

  * object schemas are capped at **10 properties** and **nesting depth 2**;
  * grounding / citation / confidence fields must **not** be in the schema — `/search`
    returns `output.grounding` automatically.

`TestPayloadUse` is the one class that exercises code: it fakes httpx to prove the schema
is actually the `outputSchema` sent to Exa, and that the failure paths yield nothing.
"""
import json
from types import SimpleNamespace

import pytest

from agents.langgraph_agent.tools import web_search
from agents.langgraph_agent.models.models import OutputSchema
from agents.langgraph_agent.tools.web_search import (
    WEB_OUTPUT_SCHEMA,
    _str_list,
    stream_web_search,
)
from agents.langgraph_agent.utils.utils import FILTER_FIELDS, KEYWORD_FIELDS

pytestmark = pytest.mark.unit

EXA_PROPERTY_CAP = 10

# Fields Exa cannot supply because the schema is exactly at the property cap; the DB path
# can. See FINDINGS.md #8.
_CAP_OFF_FIELDS = {"health_info", "typical_uses", "barcodes"}


def props():
    return WEB_OUTPUT_SCHEMA["properties"]


class TestSchemaShape:
    def test_is_an_object_schema(self):
        assert WEB_OUTPUT_SCHEMA["type"] == "object"

    def test_properties_is_a_non_empty_dict(self):
        assert isinstance(props(), dict)
        assert props()

    def test_required_is_a_list_of_existing_properties(self):
        required = WEB_OUTPUT_SCHEMA["required"]
        assert isinstance(required, list)
        assert required
        assert set(required) <= set(props())

    def test_norm_name_is_the_only_required_field(self):
        # WebSearch gates on `product.get("norm_name")`, so exactly this field must be
        # guaranteed present by the schema.
        assert WEB_OUTPUT_SCHEMA["required"] == ["norm_name"]


class TestExaConstraints:
    """Exa's structured-output limits, per its docs: 10 props, depth 2, no grounding."""

    def test_property_count_stays_within_exa_cap(self):
        # Today the schema sits exactly AT the cap — the three commented-out fields are
        # the entire remaining budget. Adding an 11th property makes Exa reject every
        # request, silently turning web search off. This guard is what makes that fail
        # loudly in CI instead.
        assert len(props()) <= EXA_PROPERTY_CAP

    def test_no_nested_object_properties(self):
        # Nesting depth 2: the root object's properties are only scalars or arrays of
        # scalars. A property whose type is object (or whose items are objects) exceeds
        # the cap.
        for field, schema in props().items():
            assert schema["type"] in ("string", "array"), field
            if schema["type"] == "array":
                assert schema["items"]["type"] == "string", field

    def test_every_property_has_a_description(self):
        # Exa synthesises each field from its description; a missing one weakens or
        # breaks the output.
        for field, schema in props().items():
            assert schema.get("description"), field

    def test_no_grounding_or_confidence_fields(self):
        # Exa returns `output.grounding` automatically; adding such fields to the schema
        # is explicitly discouraged and would duplicate the automatic output.
        assert not ({"grounding", "confidence", "citations"} & set(props()))

    def test_schema_serialises_to_json(self):
        json.dumps(WEB_OUTPUT_SCHEMA)


class TestFieldTypes:
    def test_string_fields(self):
        for field in ("norm_name", "halal_status", "category_l1", "category_l2"):
            assert props()[field]["type"] == "string", field

    def test_array_fields_have_string_items(self):
        for field in ("companies", "cert_bodies", "cert_numbers", "sold_in", "marketplace", "fda_numbers"):
            assert props()[field]["type"] == "array", field
            assert props()[field]["items"]["type"] == "string", field


class TestConsistencyWithProductModel:
    """The schema's output must land on `OutputSchema`, or `_project` drops it."""

    def test_every_property_exists_on_output_schema(self):
        # response_node's `_project` keeps only OutputSchema fields. A property Exa emits
        # that is not on the model would be silently discarded on the way to the client.
        assert set(props()) <= set(OutputSchema.model_fields)

    def test_no_stray_fields_outside_the_agent_field_sets(self):
        # The agent's DB fields are exactly KEYWORD_FIELDS | FILTER_FIELDS; a schema key
        # outside both would be a typo no downstream code reads.
        assert set(props()) <= (KEYWORD_FIELDS | FILTER_FIELDS)

    def test_tool_managed_fields_are_not_requested_from_exa(self):
        # canonical_id / verified / grounding are set deterministically by WebSearch, so
        # Exa must never be asked to invent them.
        assert not ({"canonical_id", "verified", "grounding"} & set(props()))

    def test_fallback_products_lack_health_info_typical_uses_and_barcodes(self):
        # FINDINGS.md #8 — the schema sits exactly at Exa's 10-property cap, so the three
        # "lower-value" DB fields are commented out. Web fallback products therefore
        # structurally cannot carry health_info / typical_uses / barcodes, which are
        # exactly the attributes a user asking for them needs. This is a characterisation
        # test: re-enabling any of the three trips the property-cap test above, forcing a
        # deliberate trade-off rather than a silent API break.
        assert set(props()) & _CAP_OFF_FIELDS == set()


class TestStrListHelper:
    def test_str_list_shape(self):
        assert _str_list("desc") == {
            "type": "array",
            "items": {"type": "string"},
            "description": "desc",
        }

    def test_str_list_carries_the_description(self):
        assert _str_list("Certification bodies")["description"] == "Certification bodies"


@pytest.fixture
def fake_httpx(monkeypatch):
    """Stand-in for the httpx module inside web_search.py.

    Replaces `httpx.Client(...)` with a context manager whose `.stream()` yields a fake
    response scripted through `fake_httpx.state` (lines to stream, optional error for
    `raise_for_status`). The request payload is captured in `fake_httpx.captured`.
    `HTTPError` stays the real class so the function's `except httpx.HTTPError` binds.
    """
    import httpx as real_httpx

    captured = []
    state = {"lines": [], "error": None}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def raise_for_status(self):
            if state["error"]:
                raise state["error"]

        def iter_lines(self):
            return iter(state["lines"])

    class FakeClient:
        def __init__(self, *a, **k):
            self._resp = FakeResponse()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def stream(self, method, url, headers=None, json=None):
            captured.append(
                {"method": method, "url": url, "headers": headers, "json": json}
            )
            return self._resp

    monkeypatch.setattr(
        "agents.langgraph_agent.tools.web_search.httpx",
        SimpleNamespace(Client=FakeClient, HTTPError=real_httpx.HTTPError),
        raising=True,
    )
    return SimpleNamespace(captured=captured, state=state)


class TestPayloadUse:
    """The schema's one real use: the Exa request in `stream_web_search`."""

    def test_payload_sends_the_module_schema_as_output_schema(self, fake_httpx, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "test-key")

        list(stream_web_search("x"))

        payload = fake_httpx.captured[0]["json"]
        assert payload["outputSchema"] is WEB_OUTPUT_SCHEMA

    def test_payload_uses_exa_camel_case_keys(self, fake_httpx, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "test-key")

        list(stream_web_search("x"))

        payload = fake_httpx.captured[0]["json"]
        assert set(payload) == {
            "query", "numResults", "type", "stream", "outputSchema", "contents",
        }
        assert payload["stream"] is True
        assert payload["type"] == "auto"
        assert payload["contents"] == {"highlights": True}

    def test_num_results_flows_through(self, fake_httpx, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "test-key")

        list(stream_web_search("x", num_results=3))

        assert fake_httpx.captured[0]["json"]["numResults"] == 3

    def test_request_is_post_to_exa_with_api_key_header(self, fake_httpx, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "test-key")

        list(stream_web_search("x"))

        call = fake_httpx.captured[0]
        assert call["method"] == "POST"
        assert call["url"] == "https://api.exa.ai/search"
        assert call["headers"]["x-api-key"] == "test-key"

    def test_results_and_done_frames_are_yielded(self, fake_httpx, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "test-key")
        fake_httpx.state["lines"] = [
            'data: {"type": "results", "results": [{"url": "https://a", "title": "A"}]}',
            'data: {"type": "done", "output": {"content": {"norm_name": "KitKat"}, "grounding": []}}',
            "data: [DONE]",
        ]

        events = list(stream_web_search("x"))

        assert events == [
            {"type": "results", "results": [{"url": "https://a", "title": "A"}]},
            {"type": "done", "output": {"content": {"norm_name": "KitKat"}, "grounding": []}},
        ]

    def test_non_data_and_non_json_lines_are_skipped(self, fake_httpx, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "test-key")
        fake_httpx.state["lines"] = [
            "event: ping",
            "",
            "data: not-json",
            'data: {"type": "results", "results": []}',
        ]

        assert list(stream_web_search("x")) == [{"type": "results", "results": []}]

    def test_missing_api_key_yields_nothing_and_logs(self, fake_httpx, monkeypatch):
        logged = []

        class FakeLog:
            def error(self, event, **kw):
                logged.append((event, kw))

        monkeypatch.setattr("agents.langgraph_agent.tools.web_search.log", FakeLog())
        monkeypatch.delenv("EXA_API_KEY", raising=False)

        assert list(stream_web_search("x")) == []
        assert fake_httpx.captured == [], "no request may be sent without a key"
        assert logged == [("web_search.exa_api_key.missing", {})]

    def test_http_error_yields_nothing_and_logs(self, fake_httpx, monkeypatch):
        import httpx as real_httpx

        logged = []

        class FakeLog:
            def error(self, event, **kw):
                logged.append((event, kw))

        monkeypatch.setattr("agents.langgraph_agent.tools.web_search.log", FakeLog())
        monkeypatch.setenv("EXA_API_KEY", "test-key")
        fake_httpx.state["error"] = real_httpx.HTTPStatusError(
            "boom", request=None, response=None
        )

        assert list(stream_web_search("x")) == []
        (event, kw) = logged[0]
        assert event == "web_search.exa_stream.failed"
        assert kw["error_type"] == "HTTPStatusError"
