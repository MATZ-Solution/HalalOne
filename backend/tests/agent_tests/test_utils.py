"""Layer 1 — `agents/langgraph_agent/utils/utils.py`.

Pure functions, no mocking, no I/O. `build_filter_string()` turns a `FilterArgs` model
into a Typesense `filter_by` expression, so its output is a wire format: if it is wrong,
`SemanticFilterSearch` silently returns nothing rather than raising. That makes it worth
pinning precisely.

Two real defects are pinned below with `xfail(strict=True)` — the tests describe the
*intended* behaviour and will flip to a failure (XPASS) the moment the bug is fixed,
which is the signal to delete the marker. See the module docstring of each for detail.
"""
import pytest

from agents.langgraph_agent.models.models import FilterArgs
from agents.langgraph_agent.utils.utils import (
    COLLECTION,
    FILTER_FIELDS,
    KEYWORD_FIELDS,
    build_filter_string,
)

pytestmark = pytest.mark.unit


def parts_of(filter_string: str) -> list[str]:
    """Split a filter expression into its `&&`-joined clauses."""
    return [p for p in filter_string.split(" && ") if p]


def meaningful_parts(filter_string: str) -> list[str]:
    """Clauses excluding the spurious `field:="None"` ones produced for unset fields.

    Lets the tests below assert real behaviour today without also asserting the bug that
    `test_unset_fields_are_omitted` pins. Once that bug is fixed this helper becomes a
    no-op, and the assertions keep passing unchanged.
    """
    return [p for p in parts_of(filter_string) if not p.endswith(':="None"')]


class TestEmptyInput:
    def test_none_returns_empty_string(self):
        assert build_filter_string(None) == ""

    def test_empty_string_is_falsy_so_callers_skip_filter_by(self):
        # SemanticFilterSearch does `if filter_str: params["filter_by"] = filter_str`,
        # so "" must mean "no filtering" rather than "match nothing".
        assert not build_filter_string(None)


class TestStringFields:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("category_l1", "food"),
            ("category_l2", "frozen"),
            ("halal_status", "halal"),
        ],
    )
    def test_string_field_is_quoted_and_exact_matched(self, field, value):
        result = build_filter_string(FilterArgs(**{field: value}))
        assert meaningful_parts(result) == [f'{field}:="{value}"']


class TestListFields:
    @pytest.mark.parametrize(
        "field",
        ["sold_in", "cert_bodies", "cert_numbers", "fda_numbers", "barcodes", "marketplace"],
    )
    def test_list_field_uses_bracket_syntax(self, field):
        # Asserts the `field:=[…]` shape and that the value is carried through, without
        # committing to whether items are quoted — quoting is pinned separately in
        # TestKnownDefects, so this test stays valid before and after that fix.
        (clause,) = meaningful_parts(build_filter_string(FilterArgs(**{field: ["HFA"]})))
        assert clause.startswith(f"{field}:=[")
        assert clause.endswith("]")
        assert "HFA" in clause

    def test_multiple_values_are_comma_separated(self):
        result = build_filter_string(FilterArgs(cert_bodies=["HFA", "HMC"]))
        (clause,) = meaningful_parts(result)
        assert clause.startswith("cert_bodies:=[")
        assert clause.endswith("]")
        assert clause.count(",") == 1


class TestCombining:
    def test_multiple_fields_are_joined_with_and(self):
        result = build_filter_string(
            FilterArgs(halal_status="halal", category_l1="food", sold_in=["UK"])
        )
        clauses = meaningful_parts(result)
        assert len(clauses) == 3
        assert 'halal_status:="halal"' in clauses
        assert 'category_l1:="food"' in clauses

    def test_field_order_follows_the_model_not_the_caller(self):
        # Two callers passing the same filters in different order must produce the same
        # string, otherwise identical searches would miss any response cache keyed on it.
        a = build_filter_string(FilterArgs(halal_status="halal", category_l1="food"))
        b = build_filter_string(FilterArgs(category_l1="food", halal_status="halal"))
        assert a == b


class TestFieldWhitelist:
    def test_non_filter_fields_are_never_emitted(self):
        # `norm_name` is a KEYWORD field, not a filter field. Pydantic drops it as an
        # unknown kwarg, and the FILTER_FIELDS guard is the second line of defence.
        result = build_filter_string(FilterArgs(**{"norm_name": "nuggets"}))
        assert "norm_name" not in result

    def test_keyword_and_filter_fields_do_not_overlap(self):
        # The two sets drive different code paths in KeywordFilterSearch; an overlap
        # would make a field ambiguous.
        assert KEYWORD_FIELDS.isdisjoint(FILTER_FIELDS)

    def test_every_filter_field_exists_on_the_model(self):
        # Guards against a field being renamed on FilterArgs but not in FILTER_FIELDS,
        # which would silently drop that filter instead of erroring.
        assert FILTER_FIELDS <= set(FilterArgs.model_fields)

    def test_collection_name(self):
        assert COLLECTION == "halal_products"


class TestRegressionGuards:
    """Findings 1-3, fixed. These were `xfail(strict=True)` until the fix landed; they now
    guard it. Each asserts the *exact* full string, so a regression that reintroduces the
    `:="None"` clauses or drops the quoting fails here first.
    """

    def test_unset_fields_are_omitted(self):
        # Finding #1: unset fields used to be emitted as `field:="None"`, which made every
        # filtered semantic search match zero documents.
        assert build_filter_string(FilterArgs(halal_status="halal")) == 'halal_status:="halal"'

    def test_all_unset_is_equivalent_to_no_filters(self):
        # Finding #2: FilterArgs() must mean "no filtering", exactly like None.
        assert build_filter_string(FilterArgs()) == ""
        assert build_filter_string(FilterArgs()) == build_filter_string(None)

    def test_list_values_containing_spaces_are_quoted(self):
        # Finding #3: unquoted values mis-parsed at the space.
        assert build_filter_string(FilterArgs(sold_in=["United Kingdom"])) == 'sold_in:=["United Kingdom"]'

    def test_multi_value_list_quotes_every_item(self):
        assert (
            build_filter_string(FilterArgs(cert_bodies=["HFA", "JAKIM Malaysia"]))
            == 'cert_bodies:=["HFA","JAKIM Malaysia"]'
        )

    def test_mixed_filters_emit_only_what_was_set(self):
        assert (
            build_filter_string(FilterArgs(halal_status="Halal", sold_in=["United Kingdom"]))
            == 'halal_status:="Halal" && sold_in:=["United Kingdom"]'
        )

    def test_empty_list_is_treated_as_unset(self):
        # An empty list is falsy, so it is skipped rather than emitting `field:=[]`,
        # which would have matched nothing.
        assert build_filter_string(FilterArgs(cert_bodies=[])) == ""
