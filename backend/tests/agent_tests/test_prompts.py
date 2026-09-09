"""Layer 3 — `agents/langgraph_agent/prompts/prompt.py`.

The prompts are pure string constants, so this layer is pinned the same way the schemas
were: as **contracts**. Each prompt is the half of the system that talks to the LLM, so a
prompt that drifts from the schema / utils / node wiring is a silent behaviour change one
layer down — the model is told one thing and the code does another.

The contracts checked here:

  * `CLASSIFICATION_PROMPT` must tell the model to emit the key the router reads
    (`classification`) with exactly the two values (`search`, `direct`) the router and
    the schema agree on. This is the *working* half of FINDINGS.md #4 — the schema
    (`intent`) is the odd one out, already pinned in the models/node layers.
  * `SEARCH_PROMPT`'s two field tables must be exactly the `KEYWORD_FIELDS` /
    `FILTER_FIELDS` the tools accept, and its tool names must be the three bound tools.
  * `FINAL_RESPONSE_PROMPT`'s placeholders must be exactly the keys `response_node`
    invokes its chain with, and its output fields must be exactly `SelectedProducts`
    (which `json_schema` then validates against).
  * `SUMMARIZE_CONVERSATION_PROMPT`'s fold markers must match what `summarize_conversation`
    actually prints.

Two findings are pinned:

  * **FINDINGS.md #12** — the prompt normalises `halal_status` to `"Haram"` (one `a`),
    but the collection stores `"Haraam"` (two `a`'s; the repo's own live search harness,
    `tests/search_tests/search_tests.py`, documents the canonical values as Halal,
    Haraam, Mushbooh). Exact-match haram filters silently match nothing.
    Pinned with `xfail(strict=True)`.
  * **FINDINGS.md #13** — `CLASSIFICATION_PROMPT` / `SEARCH_PROMPT` carry `{{...}}`
    template escapes that are never rendered (they are passed raw as `SystemMessage`),
    while `FINAL_RESPONSE_PROMPT` is a real `ChatPromptTemplate`. Pinned as a
    characterisation of the current, inconsistent split.
"""
import re

import pytest

from agents.langgraph_agent.models.models import SelectedProducts, classify_intent_schema
from agents.langgraph_agent.prompts.prompt import (
    CLASSIFICATION_PROMPT,
    FINAL_RESPONSE_PROMPT,
    SEARCH_PROMPT,
    SUMMARIZE_CONVERSATION_PROMPT,
)
from agents.langgraph_agent.utils.utils import FILTER_FIELDS, KEYWORD_FIELDS

pytestmark = pytest.mark.unit


def _table_fields(prompt, section_header):
    """Field names from a markdown pipe table under `section_header`."""
    lines = prompt.splitlines()
    header = next(i for i, line in enumerate(lines) if section_header in line)
    separator = next(
        i for i in range(header + 1, len(lines))
        if lines[i].strip().startswith("|")
        and re.fullmatch(r"[\|\s:>-]*", lines[i].strip())
    )
    fields = set()
    for line in lines[separator + 1:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        match = re.match(r"\|\s*([A-Za-z_0-9]+)\s*\|", stripped)
        if match:
            fields.add(match.group(1))
    return fields


class TestClassificationPrompt:
    def test_output_key_is_the_router_key(self):
        assert '"classification"' in CLASSIFICATION_PROMPT

    def test_instructs_exactly_the_two_classifications(self):
        values = set(re.findall(r'"classification": "(\w+)"', CLASSIFICATION_PROMPT))
        assert values == {"search", "direct"}

    def test_values_match_the_schema_enum(self):
        values = set(re.findall(r'"classification": "(\w+)"', CLASSIFICATION_PROMPT))
        assert values == set(classify_intent_schema["properties"]["classification"]["enum"])

    def test_prefers_direct_when_unsure(self):
        assert "When unsure, prefer `direct`" in CLASSIFICATION_PROMPT

    def test_json_examples_use_unrendered_double_braces(self):
        assert '{{"classification"' in CLASSIFICATION_PROMPT


class TestSearchPrompt:
    def test_keyword_fields_match_the_utils_contract(self):
        assert _table_fields(SEARCH_PROMPT, "Keyword-searchable fields") == KEYWORD_FIELDS

    def test_filter_fields_match_the_utils_contract(self):
        assert _table_fields(SEARCH_PROMPT, "Exact-filterable fields") == FILTER_FIELDS

    def test_mentions_every_bound_tool(self):
        for name in ("KeywordFilterSearch", "SemanticFilterSearch", "WebSearch"):
            assert name in SEARCH_PROMPT

    def test_web_search_is_marked_last_resort(self):
        assert "LAST RESORT" in SEARCH_PROMPT

    def test_web_search_is_forbidden_before_the_database(self):
        assert "NEVER call `WebSearch` before the database tools" in SEARCH_PROMPT

    def test_absent_fields_must_be_null(self):
        assert "pass `null` for that field" in SEARCH_PROMPT

    def test_ambiguous_filters_skip_the_tools(self):
        assert "do NOT call any tool" in SEARCH_PROMPT

    @pytest.mark.xfail(
        strict=True,
        reason="FINDINGS.md #12: collection stores 'Haraam' but the prompt normalises "
        "to 'Haram', so exact-match haram filters silently match nothing",
    )
    def test_halal_status_normalises_to_the_collection_spelling(self):
        assert '"Haraam"' in SEARCH_PROMPT


class TestFinalResponsePrompt:
    def test_placeholders_match_response_node_invoke_keys(self):
        placeholders = set(re.findall(r"\{([A-Za-z_][A-Za-z_0-9]*)\}", FINAL_RESPONSE_PROMPT))
        assert placeholders == {"halal_search_results", "conversation_history"}

    def test_output_fields_match_selected_products(self):
        assert "product_ids" in FINAL_RESPONSE_PROMPT
        assert "`response`" in FINAL_RESPONSE_PROMPT
        assert {"response", "product_ids"} == set(SelectedProducts.model_fields)

    def test_ids_reference_the_candidate_id_line(self):
        assert "[id:" in FINAL_RESPONSE_PROMPT

    def test_maximum_ten_products(self):
        assert "maximum 10" in FINAL_RESPONSE_PROMPT

    def test_ids_must_be_copied_exactly(self):
        assert "NEVER invent" in FINAL_RESPONSE_PROMPT


class TestSummarizeConversationPrompt:
    def test_folding_markers_match_the_compactor(self):
        assert "PREVIOUS SUMMARY" in SUMMARIZE_CONVERSATION_PROMPT
        assert "NEW TURNS" in SUMMARIZE_CONVERSATION_PROMPT

    def test_summary_only_output_instruction(self):
        assert "Output the summary only." in SUMMARIZE_CONVERSATION_PROMPT

    def test_no_unrendered_template_escapes(self):
        assert "{{" not in SUMMARIZE_CONVERSATION_PROMPT


class TestTemplateSplit:
    """Only FINAL_RESPONSE_PROMPT is a rendered template; the others are raw strings
    whose `{{...}}` escapes reach the model literally (FINDINGS.md #13)."""

    def test_only_final_response_prompt_has_single_brace_placeholders(self):
        assert re.findall(r"\{[A-Za-z_]", CLASSIFICATION_PROMPT) == []
        assert re.findall(r"\{[A-Za-z_]", SEARCH_PROMPT) == []
        assert len(re.findall(r"\{([A-Za-z_][A-Za-z_0-9]*)\}", FINAL_RESPONSE_PROMPT)) == 2

    def test_classification_and_search_prompts_carry_double_braces(self):
        assert "{{" in CLASSIFICATION_PROMPT
        assert "{{" in SEARCH_PROMPT
        assert "{{" not in FINAL_RESPONSE_PROMPT
