"""Layer 2 — `KeywordFilterSearch` in `agents/langgraph_agent/tools/tools.py`.

This tool does not search anything itself; it *decides* how to search and delegates to
`search_collection`. So these tests never assert on search quality — Typesense is faked.
They assert on the tool's own decisions:

  * which branch it takes (filters-only / nothing / keyword loop),
  * what it drops (unknown keys, falsy values),
  * how it builds each query, and
  * how it narrows results across multiple keyword fields.

The tool is exercised through `.invoke({...})` rather than by calling the underlying
function, because that is how `tool_node` calls it — so the `KeywordFilterInput` schema
coercion (a raw dict becoming a `FilterArgs`) is covered too.
"""
import pytest

from agents.langgraph_agent.tools.tools import KeywordFilterSearch

pytestmark = pytest.mark.unit


def calls_to(recorder):
    """The recorded `search_collection` calls as plain kwarg dicts."""
    return [c["kwargs"] for c in recorder.calls]


class TestNoKeywordsBranch:
    """`keyword_args` empty -> either one wildcard query, or no query at all."""

    def test_filters_only_issues_a_single_wildcard_query(
        self, fake_search_collection, make_product
    ):
        product = make_product()
        fake_search_collection.set(returns=[product])

        result = KeywordFilterSearch.invoke({"filter_args": {"halal_status": "halal"}})

        assert result == [product]
        assert fake_search_collection.call_count == 1
        assert calls_to(fake_search_collection)[0] == {
            "query": "*",
            "query_by": "norm_name",
            "collection_name": "halal_products",
            "filter_parameters": {"halal_status": "halal"},
        }

    def test_filters_only_passes_unset_filter_fields_through_as_absent(
        self, fake_search_collection
    ):
        # Unlike build_filter_string (see FINDINGS.md #1), this path drops falsy values,
        # so an unset field never reaches Typesense as the string "None".
        KeywordFilterSearch.invoke({"filter_args": {"halal_status": "halal"}})

        sent = calls_to(fake_search_collection)[0]["filter_parameters"]
        assert sent == {"halal_status": "halal"}
        assert "None" not in str(sent)

    def test_no_keywords_and_no_filters_short_circuits(self, fake_search_collection):
        assert KeywordFilterSearch.invoke({}) == []
        assert fake_search_collection.called is False, (
            "the empty-input case must not reach Typesense at all"
        )

    def test_explicit_nulls_are_treated_as_absent(self, fake_search_collection):
        # The prompt tells the LLM to pass null when a group is not present, so nulls
        # arrive routinely and must behave exactly like omitting the field.
        assert KeywordFilterSearch.invoke({"keyword_args": None, "filter_args": None}) == []
        assert fake_search_collection.called is False

    def test_empty_filter_model_is_not_mistaken_for_active_filters(
        self, fake_search_collection
    ):
        # A FilterArgs with every field None must not trigger the wildcard branch.
        assert KeywordFilterSearch.invoke({"filter_args": {}}) == []
        assert fake_search_collection.called is False


class TestKeywordFieldSelection:
    """Only the four whitelisted fields may become queries."""

    @pytest.mark.parametrize(
        "field", ["norm_name", "companies", "health_info", "typical_uses"]
    )
    def test_each_whitelisted_field_is_queried_against_itself(
        self, fake_search_collection, make_product, field
    ):
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke({"keyword_args": {field: "value"}})

        assert calls_to(fake_search_collection)[0]["query_by"] == field

    def test_unknown_keys_are_dropped(self, fake_search_collection):
        # `category_l1` is a FILTER field; the LLM putting it in keyword_args must not
        # produce a query against a non-searchable field.
        result = KeywordFilterSearch.invoke(
            {"keyword_args": {"category_l1": "food", "made_up_field": "x"}}
        )

        assert result == []
        assert fake_search_collection.called is False

    def test_unknown_keys_are_dropped_but_known_ones_survive(
        self, fake_search_collection, make_product
    ):
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke(
            {"keyword_args": {"made_up_field": "x", "norm_name": "nuggets"}}
        )

        assert fake_search_collection.call_count == 1
        assert calls_to(fake_search_collection)[0]["query_by"] == "norm_name"

    @pytest.mark.parametrize("falsy", ["", [], None])
    def test_falsy_values_are_dropped(self, fake_search_collection, falsy):
        result = KeywordFilterSearch.invoke({"keyword_args": {"norm_name": falsy}})

        assert result == []
        assert fake_search_collection.called is False, (
            "an empty keyword must not become an empty Typesense query"
        )


class TestQueryConstruction:
    def test_string_value_is_used_verbatim(self, fake_search_collection, make_product):
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke({"keyword_args": {"norm_name": "chicken nuggets"}})

        assert calls_to(fake_search_collection)[0]["query"] == "chicken nuggets"

    def test_list_value_is_joined_with_spaces(self, fake_search_collection, make_product):
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke(
            {"keyword_args": {"companies": ["Crestwood", "Tesco"]}}
        )

        assert calls_to(fake_search_collection)[0]["query"] == "Crestwood Tesco"

    def test_collection_is_always_the_halal_products_collection(
        self, fake_search_collection, make_product
    ):
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke({"keyword_args": {"norm_name": "x"}})

        assert calls_to(fake_search_collection)[0]["collection_name"] == "halal_products"

    def test_filters_accompany_the_keyword_query(
        self, fake_search_collection, make_product
    ):
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke(
            {
                "keyword_args": {"norm_name": "nuggets"},
                "filter_args": {"halal_status": "halal", "sold_in": ["UK"]},
            }
        )

        sent = calls_to(fake_search_collection)[0]["filter_parameters"]
        assert sent["halal_status"] == "halal"
        assert sent["sold_in"] == ["UK"]


class TestNarrowingAcrossFields:
    """Multiple keyword fields are ANDed by feeding round N's ids into round N+1."""

    def test_second_field_is_filtered_by_first_fields_result_ids(
        self, fake_search_collection, make_product
    ):
        first = [make_product("p1"), make_product("p2")]
        second = [make_product("p1")]
        fake_search_collection.set(side_effect=[first, second])

        KeywordFilterSearch.invoke(
            {"keyword_args": {"norm_name": "nuggets", "companies": ["Crestwood"]}}
        )

        sent = calls_to(fake_search_collection)
        assert "canonical_id" not in sent[0]["filter_parameters"], (
            "the first round has nothing to narrow by yet"
        )
        assert sent[1]["filter_parameters"]["canonical_id"] == ["p1", "p2"]

    def test_narrowing_composes_with_user_filters(
        self, fake_search_collection, make_product
    ):
        fake_search_collection.set(
            side_effect=[[make_product("p1")], [make_product("p1")]]
        )

        KeywordFilterSearch.invoke(
            {
                "keyword_args": {"norm_name": "nuggets", "companies": ["Crestwood"]},
                "filter_args": {"halal_status": "halal"},
            }
        )

        second = calls_to(fake_search_collection)[1]["filter_parameters"]
        assert second["halal_status"] == "halal", "user filters must survive narrowing"
        assert second["canonical_id"] == ["p1"]

    def test_result_is_the_final_rounds_documents(
        self, fake_search_collection, make_product
    ):
        # The last round is already narrowed by every earlier one, so it *is* the
        # intersection — the tool returns it rather than merging rounds.
        final = [make_product("p1")]
        fake_search_collection.set(
            side_effect=[[make_product("p1"), make_product("p2")], final]
        )

        result = KeywordFilterSearch.invoke(
            {"keyword_args": {"norm_name": "nuggets", "companies": ["Crestwood"]}}
        )

        assert result == final

    def test_empty_round_aborts_immediately(self, fake_search_collection, make_product):
        # An AND across fields: if one field matches nothing, the intersection is empty,
        # so later fields must not be queried at all.
        fake_search_collection.set(side_effect=[[]])

        result = KeywordFilterSearch.invoke(
            {
                "keyword_args": {
                    "norm_name": "nonexistent",
                    "companies": ["Crestwood"],
                    "health_info": ["high protein"],
                }
            }
        )

        assert result == []
        assert fake_search_collection.call_count == 1, (
            "search must stop at the first field that matches nothing"
        )

    def test_late_empty_round_also_returns_empty(
        self, fake_search_collection, make_product
    ):
        fake_search_collection.set(side_effect=[[make_product("p1")], []])

        result = KeywordFilterSearch.invoke(
            {"keyword_args": {"norm_name": "nuggets", "companies": ["Nope"]}}
        )

        assert result == []
        assert fake_search_collection.call_count == 2


class TestMalformedLLMArguments:
    """`keyword_args` is typed `Dict[str, Any]`, so Pydantic validates the container but
    not what is inside it. Findings #5 and #6 were crashes on this path; both are fixed,
    and these are now the regression guards. The bar is the same one the sibling tools
    already meet: bad input degrades to "no products found", it never fails the node.
    """

    def test_non_dict_keyword_args_is_rejected_at_the_schema_boundary(self):
        # This one was always handled well: Pydantic refuses it before any code runs.
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            KeywordFilterSearch.invoke({"keyword_args": "chicken nuggets"})

    @pytest.mark.parametrize(
        "value,expected_query",
        [
            pytest.param([123], "123", id="int-in-list"),
            pytest.param([123, "Tesco"], "123 Tesco", id="mixed-list"),
            pytest.param([1.5, True], "1.5 True", id="float-and-bool"),
        ],
    )
    def test_non_string_list_items_are_coerced_not_crashed(
        self, fake_search_collection, make_product, value, expected_query
    ):
        # Finding #5, fixed: `" ".join([123])` used to raise TypeError, and because
        # tool_node does not guard tool.invoke() the whole node failed — the user got
        # "Some error occured" where "no products found" was the honest answer.
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke({"keyword_args": {"companies": value}})

        assert calls_to(fake_search_collection)[0]["query"] == expected_query

    def test_non_string_scalar_is_coerced(self, fake_search_collection, make_product):
        fake_search_collection.set(returns=[make_product()])

        KeywordFilterSearch.invoke({"keyword_args": {"norm_name": 12345}})

        assert calls_to(fake_search_collection)[0]["query"] == "12345"

    @pytest.mark.parametrize(
        "keyword_args",
        [
            pytest.param({"norm_name": "a"}, id="single-field"),
            pytest.param({"norm_name": "a", "companies": ["b"]}, id="multi-field"),
        ],
    )
    def test_document_without_canonical_id_does_not_crash(
        self, fake_search_collection, keyword_args
    ):
        # Finding #6, fixed: narrowing used to index doc["canonical_id"] directly, so a
        # document missing the field raised KeyError — even on a single-field query,
        # because the id extraction runs after every round including the last.
        doc = {"norm_name": "no id here"}
        fake_search_collection.set(returns=[doc])

        assert KeywordFilterSearch.invoke({"keyword_args": keyword_args}) == [doc]

    def test_narrowing_skips_only_the_documents_missing_an_id(
        self, fake_search_collection, make_product
    ):
        # A partial result set still narrows on the ids it does have, rather than
        # dropping the filter entirely or crashing on the incomplete document.
        first = [make_product("p1"), {"norm_name": "no id"}]
        fake_search_collection.set(side_effect=[first, [make_product("p1")]])

        KeywordFilterSearch.invoke(
            {"keyword_args": {"norm_name": "a", "companies": ["b"]}}
        )

        assert calls_to(fake_search_collection)[1]["filter_parameters"]["canonical_id"] == ["p1"]

    def test_no_usable_ids_leaves_the_previous_filters_intact(
        self, fake_search_collection, make_product
    ):
        # If a whole round returns documents with no ids there is nothing to narrow by;
        # the user's own filters must survive rather than being replaced by an empty list
        # (`canonical_id:=[]` would match nothing).
        fake_search_collection.set(
            side_effect=[[{"norm_name": "no id"}], [make_product("p1")]]
        )

        KeywordFilterSearch.invoke(
            {
                "keyword_args": {"norm_name": "a", "companies": ["b"]},
                "filter_args": {"halal_status": "Halal"},
            }
        )

        second = calls_to(fake_search_collection)[1]["filter_parameters"]
        assert second["halal_status"] == "Halal"
        assert "canonical_id" not in second


class TestToolContract:
    """What the LLM and `tool_node` rely on."""

    def test_tool_name_is_stable(self):
        # `search_tools_by_name` in node.py keys on this, and the prompt names it.
        assert KeywordFilterSearch.name == "KeywordFilterSearch"

    def test_description_is_exposed_to_the_llm(self):
        assert KeywordFilterSearch.description

    def test_both_arguments_are_optional(self, fake_search_collection):
        # The prompt instructs the LLM to pass null for an absent group, so neither
        # argument may be required by the schema.
        schema = KeywordFilterSearch.args_schema.model_json_schema()
        assert not schema.get("required")

    def test_always_returns_a_list(self, fake_search_collection):
        # tool_node does `if not observation` then `search_results.extend(observation)`,
        # so anything non-list would corrupt state.
        assert isinstance(KeywordFilterSearch.invoke({}), list)
