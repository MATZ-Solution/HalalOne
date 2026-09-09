"""Unit tests for KeywordFilterSearch (agents.langgraph_agent.tools.tools).

search_collection is mocked; we assert on the tool's decisions — its return value
and how it called search_collection — never on Typesense. Logic goes through .func
(isolates the tool from its arg schema); two tests at the end drive .invoke on
purpose, to check the schema that guards the real agent call path.
"""

import copy
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from agents.langgraph_agent.tools.tools import KeywordFilterSearch

TOOL = KeywordFilterSearch.func
SEARCH = "agents.langgraph_agent.tools.tools.search_collection"

def _snapshot_search(results):
    """side_effect returning queued results while deep-copying each call's kwargs,
    so later in-place mutation of active_filters can't rewrite what we recorded."""
    calls = []
    it = iter(results)
    return (lambda **kw: (calls.append(copy.deepcopy(kw)), next(it))[1]), calls

@pytest.mark.unit
def test_no_keywords_no_filters_returns_empty_without_searching():
    """Nothing to search on: bail out with [] and never touch the collection."""
    with patch(SEARCH) as search:
        result = TOOL(keyword_args=None, filter_args=None)

    assert result == []
    search.assert_not_called()


@pytest.mark.unit
def test_filters_only_runs_one_wildcard_query():
    """No keywords but filters present → a single query='*' pass whose result is
    returned as-is."""
    with patch(SEARCH) as search:
        search.return_value = [{"canonical_id": "a"}]
        result = TOOL(keyword_args=None, filter_args={"halal_status": "Halal"})

    assert search.call_count == 1
    kw = search.call_args.kwargs
    assert kw["query"] == "*"
    assert kw["query_by"] == "norm_name"
    assert kw["filter_parameters"] == {"halal_status": "Halal"}
    assert result == [{"canonical_id": "a"}]


@pytest.mark.unit
def test_falsy_filter_values_are_dropped():
    """Empty string / empty list filters are discarded before the query is built."""
    with patch(SEARCH) as search:
        search.return_value = []
        TOOL(keyword_args=None, filter_args={"halal_status": "Halal", "sold_in": [], "category_l1": ""})

    assert search.call_args.kwargs["filter_parameters"] == {"halal_status": "Halal"}


@pytest.mark.unit
def test_fields_are_searched_in_canonical_order():
    """norm_name narrows before companies no matter the caller's dict order."""
    with patch(SEARCH) as search:
        search.side_effect = [[{"canonical_id": "a"}], [{"canonical_id": "b"}]]
        TOOL(keyword_args={"companies": ["Shan"], "norm_name": "biryani"}, filter_args=None)

    assert [c.kwargs["query_by"] for c in search.call_args_list] == ["norm_name", "companies"]


@pytest.mark.unit
def test_empty_pass_short_circuits_the_rest():
    """Fields are ANDed: an empty pass returns [] and skips the remaining fields."""
    with patch(SEARCH) as search:
        search.return_value = []
        result = TOOL(keyword_args={"norm_name": "x", "companies": ["y"]}, filter_args=None)

    assert result == []
    assert search.call_count == 1


@pytest.mark.unit
def test_next_field_is_narrowed_by_matched_ids():
    """Each pass feeds its matched canonical_ids into the next pass's filter."""
    fake, calls = _snapshot_search([[{"canonical_id": "a"}, {"canonical_id": "b"}], [{"canonical_id": "a"}]])
    with patch(SEARCH, side_effect=fake):
        TOOL(keyword_args={"norm_name": "rice", "companies": ["falak"]}, filter_args=None)

    assert calls[1]["filter_parameters"]["canonical_id"] == ["a", "b"]


@pytest.mark.unit
def test_documents_without_canonical_id_are_skipped():
    """A doc lacking canonical_id is dropped from the narrowing set, not raised on."""
    fake, calls = _snapshot_search([[{"canonical_id": "a"}, {"name": "no id"}], [{"canonical_id": "a"}]])
    with patch(SEARCH, side_effect=fake):
        TOOL(keyword_args={"norm_name": "rice", "companies": ["falak"]}, filter_args=None)

    assert calls[1]["filter_parameters"]["canonical_id"] == ["a"]


@pytest.mark.unit
def test_intermediate_passes_pull_wide_final_pass_pulls_narrow():
    """Non-final fields fetch 250 to avoid truncating a match; the last returns 10."""
    with patch(SEARCH) as search:
        search.side_effect = [[{"canonical_id": "a"}], [{"canonical_id": "b"}]]
        TOOL(keyword_args={"norm_name": "rice", "companies": ["falak"]}, filter_args=None)

    assert [c.kwargs["limit"] for c in search.call_args_list] == [250, 10]


@pytest.mark.unit
def test_list_values_are_space_joined_scalars_passed_through():
    """companies list → space-joined query; a scalar norm_name goes through as-is."""
    with patch(SEARCH) as search:
        search.return_value = [{"canonical_id": "a"}]
        TOOL(keyword_args={"companies": ["Shan", "Foods"]}, filter_args=None)
        assert search.call_args.kwargs["query"] == "Shan Foods"

    with patch(SEARCH) as search:
        search.return_value = [{"canonical_id": "a"}]
        TOOL(keyword_args={"norm_name": "biryani masala"}, filter_args=None)
        assert search.call_args.kwargs["query"] == "biryani masala"


@pytest.mark.unit
def test_returns_the_final_passs_documents():
    """The value returned is exactly the last pass's result, not an earlier one."""
    with patch(SEARCH) as search:
        search.side_effect = [[{"canonical_id": "early"}], [{"canonical_id": "final"}]]
        result = TOOL(keyword_args={"norm_name": "rice", "companies": ["falak"]}, filter_args=None)

    assert result == [{"canonical_id": "final"}]


@pytest.mark.unit
def test_invoke_accepts_valid_args_and_dispatches():
    """Through the real agent path (.invoke), a schema-valid call reaches the logic
    and returns its result."""
    with patch(SEARCH) as search:
        search.return_value = [{"canonical_id": "a"}]
        result = KeywordFilterSearch.invoke({"keyword_args": {"norm_name": "rice"}, "filter_args": None})

    assert result == [{"canonical_id": "a"}]


@pytest.mark.unit
def test_invoke_rejects_schema_violating_args():
    """The schema is the bouncer: a non-string inside companies never reaches the
    tool — it's rejected before dispatch."""
    with patch(SEARCH):
        with pytest.raises(ValidationError):
            KeywordFilterSearch.invoke({"keyword_args": {"companies": ["Shan", 5]}, "filter_args": None})