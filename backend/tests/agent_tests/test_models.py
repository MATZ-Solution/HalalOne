"""Layer 1 — `agents/langgraph_agent/models/models.py`.

The models module is the contract layer every other component leans on: the tools
build `FilterArgs`/`KeywordFilterInput`/`SemanticFilterInput`, `response_node` parses
`SelectedProducts`, the main graph parses `FinalAnswerInput`, and the LLM routers are
told to emit `classify_intent_schema`. A drift here — a renamed field, a required field
the tools never fill, a schema key that disagrees with the prompt — shows up as a silent
mismatch two layers down, not as an error in this file.

So the layer is pinned the same way `build_filter_string` was: pure data, read-only,
no mocks. Two findings are pinned with `xfail(strict=True)`:

  * `classify_intent_schema` declares `intent`, but the router (`node.py`) and
    `CLASSIFICATION_PROMPT` (`prompts/prompt.py`) both use `classification` — the
    schema is the odd one out (FINDINGS.md #4).
  * `FilterArgs`' list fields carry a comment promising empty-list defaults but actually
    default to `None` — a misleading contract for every consumer (FINDINGS.md #10).

`TestOutputSchema` imports `node` only to read the `_CANDIDATE_FIELDS` / `_ALLOWED_OUT`
constants it keys against, so drift between node and the model fails here.
"""
import operator
from typing import Annotated, get_args, get_origin, get_type_hints

import pytest

from agents.langgraph_agent.models.models import (
    FilterArgs,
    FinalAnswerInput,
    KeywordFilterInput,
    OutputSchema,
    SearchAgentState,
    SelectedProducts,
    SemanticFilterInput,
    WebSearchInput,
    classify_intent_schema,
)
from agents.langgraph_agent.nodes import node
from agents.langgraph_agent.utils.utils import FILTER_FIELDS

pytestmark = pytest.mark.unit


class TestFilterArgs:
    """Exact-match filter contract consumed by `KeywordFilterSearch`, the semantic
    tools and `build_filter_string`."""

    def test_none_of_the_fields_are_required(self):
        assert "required" not in FilterArgs.model_json_schema()

    def test_string_fields_are_optional_strings(self):
        for name in ("category_l1", "category_l2", "halal_status"):
            field = FilterArgs.model_fields[name]
            assert field.is_required() is False
            assert get_args(field.annotation) == (str, type(None))

    def test_list_fields_are_optional_string_lists(self):
        for name in (
            "sold_in", "cert_bodies", "cert_numbers",
            "fda_numbers", "barcodes", "marketplace",
        ):
            field = FilterArgs.model_fields[name]
            assert field.is_required() is False
            args = get_args(field.annotation)
            assert args[1] is type(None)
            assert get_origin(args[0]) is list
            assert get_args(args[0]) == (str,)

    def test_empty_instance_defaults_every_field_to_none(self):
        dumped = FilterArgs().model_dump()
        assert set(dumped) == set(dumped.keys())
        assert all(v is None for v in dumped.values())

    def test_model_dump_emits_all_nine_fields(self):
        dumped = FilterArgs().model_dump()
        assert len(dumped) == 9
        assert set(dumped) == {
            "category_l1", "category_l2", "halal_status",
            "sold_in", "cert_bodies", "cert_numbers",
            "fda_numbers", "barcodes", "marketplace",
        }

    def test_filter_fields_are_all_present_on_the_model(self):
        assert set(FILTER_FIELDS) <= set(FilterArgs.model_fields)

    def test_list_fields_default_to_none_like_the_string_fields(self):
        # Finding #10, resolved in favour of the code: `None` means "the LLM did not
        # supply this filter", which is the useful distinction, so the misleading comment
        # was corrected rather than the defaults changed. Both consumers
        # (build_filter_string, KeywordFilterSearch) skip falsy values, so None and []
        # behave identically downstream — this pins which one the model actually uses.
        empty = FilterArgs()
        assert empty.sold_in is None
        assert empty.cert_bodies is None
        assert empty.marketplace is None

    def test_none_and_empty_list_filters_are_equivalent_downstream(self):
        from agents.langgraph_agent.utils.utils import build_filter_string

        assert build_filter_string(FilterArgs(sold_in=None)) == build_filter_string(
            FilterArgs(sold_in=[])
        )


class TestClassifyIntentSchema:
    """Schema documenting what the intent-classifier LLM emits.

    Finding #4, re-diagnosed: `with_structured_output(..., method='json_mode')` attaches a
    plain `JsonOutputParser`. The schema is never sent to the provider and never validated
    against, so CLASSIFICATION_PROMPT alone shapes the reply — and it instructs the model
    to emit `classification`. The router reading `classification` was therefore correct all
    along; the schema was the one out of step, and it was renamed to match. These tests keep
    the three declarations (schema / prompt / router) from drifting apart again.
    """

    def test_is_an_object_schema(self):
        assert classify_intent_schema["type"] == "object"

    def test_classification_is_the_only_declared_property(self):
        assert set(classify_intent_schema["properties"]) == {"classification"}

    def test_classification_is_required(self):
        assert classify_intent_schema["required"] == ["classification"]

    def test_classification_enum_matches_the_router_branches(self):
        assert classify_intent_schema["properties"]["classification"]["enum"] == [
            "search",
            "direct",
        ]

    def test_schema_declares_the_key_the_router_reads(self):
        # The router branches on `.get("classification")` in nodes/node.py.
        assert "classification" in classify_intent_schema["properties"]


class TestOutputSchema:
    """The canonical product object the DB and web paths are projected onto."""

    def test_every_field_is_optional(self):
        assert "required" not in OutputSchema.model_json_schema()

    def test_verified_defaults_to_true(self):
        assert OutputSchema().verified is True

    def test_grounding_defaults_to_none(self):
        assert OutputSchema().grounding is None

    def test_candidate_fields_all_exist_on_the_model(self):
        missing = set(node._CANDIDATE_FIELDS) - set(OutputSchema.model_fields)
        assert missing == set()

    def test_allowed_output_fields_all_exist_on_the_model(self):
        missing = set(node._ALLOWED_OUT) - set(OutputSchema.model_fields)
        assert missing == set()


class TestFinalAnswerInput:
    """What the main agent's final message is parsed as
    (`FinalAnswerInput.model_validate_json(...)` in `main_langgraph_agent.py`)."""

    def test_response_is_required(self):
        assert FinalAnswerInput.model_fields["response"].is_required()

    def test_products_default_to_empty_list(self):
        assert FinalAnswerInput(response="ok").products == []

    def test_products_items_are_output_schema(self):
        annotation = FinalAnswerInput.model_fields["products"].annotation
        assert OutputSchema in get_args(annotation)


class TestSelectedProducts:
    """What the final-answer LLM returns before `response_node` looks the objects up."""

    def test_response_is_required(self):
        assert SelectedProducts.model_fields["response"].is_required()

    def test_product_ids_default_to_empty_list(self):
        assert SelectedProducts(response="ok").product_ids == []

    def test_product_ids_holds_strings(self):
        annotation = SelectedProducts.model_fields["product_ids"].annotation
        assert get_args(annotation)[0] is str


class TestWebSearchInput:
    def test_query_is_required(self):
        assert WebSearchInput.model_fields["query"].is_required()


class TestSemanticFilterInput:
    def test_semantic_query_is_required(self):
        assert SemanticFilterInput.model_fields["semantic_query"].is_required()

    def test_filter_args_is_optional(self):
        assert SemanticFilterInput.model_fields["filter_args"].is_required() is False

    def test_filter_args_coerces_a_raw_dict(self):
        parsed = SemanticFilterInput(semantic_query="x", filter_args={"halal_status": "Halal"})
        assert parsed.filter_args.halal_status == "Halal"


class TestKeywordFilterInput:
    def test_neither_argument_is_required(self):
        assert KeywordFilterInput.model_fields["keyword_args"].is_required() is False
        assert KeywordFilterInput.model_fields["filter_args"].is_required() is False

    def test_keyword_args_accepts_any_value_types(self):
        parsed = KeywordFilterInput(keyword_args={"companies": [123]})
        assert parsed.keyword_args == {"companies": [123]}

    def test_every_keyword_field_is_accepted(self):
        from agents.langgraph_agent.utils.utils import KEYWORD_FIELDS

        parsed = KeywordFilterInput(keyword_args={k: [] for k in KEYWORD_FIELDS})
        assert set(parsed.keyword_args) == set(KEYWORD_FIELDS)

    def test_filter_args_coerces_a_raw_dict(self):
        parsed = KeywordFilterInput(filter_args={"category_l1": "Food & Beverage"})
        assert parsed.filter_args.category_l1 == "Food & Beverage"


class TestSearchAgentState:
    """LangGraph state; the reducers decide whether nodes accumulate or overwrite."""

    def test_defines_the_four_state_keys(self):
        hints = get_type_hints(SearchAgentState)
        assert set(hints) == {
            "user_prompt", "search_results", "messages", "search_call_iterations",
        }

    def test_search_results_accumulates_via_operator_add(self):
        annotation = get_type_hints(SearchAgentState, include_extras=True)["search_results"]
        assert get_origin(annotation) is Annotated
        assert get_args(annotation)[1] is operator.add

    def test_messages_accumulates_via_operator_add(self):
        annotation = get_type_hints(SearchAgentState, include_extras=True)["messages"]
        assert get_origin(annotation) is Annotated
        assert get_args(annotation)[1] is operator.add

    def test_search_call_iterations_has_no_reducer(self):
        annotation = get_type_hints(SearchAgentState, include_extras=True)["search_call_iterations"]
        assert get_origin(annotation) is not Annotated
