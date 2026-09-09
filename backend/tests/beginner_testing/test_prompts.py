"""Unit tests for agents.langgraph_agent.prompts.prompt.

Tests for valid/legit behavorial traits of `build_search_prompt`.
"""

import pytest

from agents.langgraph_agent.prompts.prompt import (
    build_search_prompt,
    SEARCH_PROMPT_BASE,
    PRODUCT_SCHEMA_HEADER,
    SEARCH_PROMPT_TRAILER,
    PRODUCT_SCHEMA_KEYWORD,
    PRODUCT_SCHEMA_FILTERS,
    CONTEXT,
    KEYWORD_TOOL_BLOCK,
    SEMANTIC_TOOL_BLOCK,
    WEB_TOOL_BLOCK,
)
from agents.langgraph_agent.utils.utils import KEYWORD, SEMANTIC, WEB


@pytest.mark.unit
def test_no_tools_yields_bare_scaffold():
    """With no tools bound, the prompt is just the cacheable base prefix followed
    by the trailer — no schema, no filter-normalization, no per-tool section.
    """
    out = build_search_prompt([])

    assert out.startswith(SEARCH_PROMPT_BASE)
    assert out.endswith(SEARCH_PROMPT_TRAILER)
    assert PRODUCT_SCHEMA_HEADER not in out
    assert PRODUCT_SCHEMA_KEYWORD not in out
    assert PRODUCT_SCHEMA_FILTERS not in out    
    assert CONTEXT not in out
    assert "## TOOLS" not in out
    assert KEYWORD_TOOL_BLOCK not in out
    assert SEMANTIC_TOOL_BLOCK not in out
    assert WEB_TOOL_BLOCK not in out


@pytest.mark.unit
def test_keyword_only_pulls_in_schema_and_its_block():
    """Keyword tool binds the keyword table, the filter table, filter
    normalization, and its own block — but not the other tools' blocks."""
    out = build_search_prompt([KEYWORD])

    assert PRODUCT_SCHEMA_KEYWORD in out
    assert PRODUCT_SCHEMA_HEADER in out
    assert PRODUCT_SCHEMA_FILTERS in out
    assert CONTEXT in out
    assert KEYWORD_TOOL_BLOCK in out
    assert SEMANTIC_TOOL_BLOCK not in out
    assert WEB_TOOL_BLOCK not in out


@pytest.mark.unit
def test_semantic_only_omits_the_keyword_table():
    """Semantic is a filter tool, so it gets the filter table and normalization
    but never the keyword table (that one is keyword-only)."""
    out = build_search_prompt([SEMANTIC])

    assert PRODUCT_SCHEMA_KEYWORD not in out
    assert PRODUCT_SCHEMA_HEADER in out
    assert PRODUCT_SCHEMA_FILTERS in out
    assert CONTEXT in out
    assert SEMANTIC_TOOL_BLOCK in out
    assert KEYWORD_TOOL_BLOCK not in out
    assert WEB_TOOL_BLOCK not in out


@pytest.mark.unit
def test_web_only_has_no_schema_section():
    """Web isn't a DB filter tool, so no schema and no normalization show up —
    only its own block under the tools section."""
    out = build_search_prompt([WEB])

    assert PRODUCT_SCHEMA_HEADER not in out
    assert PRODUCT_SCHEMA_KEYWORD not in out
    assert PRODUCT_SCHEMA_FILTERS not in out
    assert KEYWORD_TOOL_BLOCK not in out
    assert SEMANTIC_TOOL_BLOCK not in out
    assert CONTEXT not in out
    assert WEB_TOOL_BLOCK in out
    assert "## TOOLS" in out


@pytest.mark.unit
def test_blocks_follow_ladder_order_not_input_order():
    """Order is fixed keyword -> semantic -> web regardless of how the caller
    passes the names in."""
    out = build_search_prompt([WEB, SEMANTIC, KEYWORD])

    assert out.index(KEYWORD_TOOL_BLOCK) < out.index(SEMANTIC_TOOL_BLOCK) < out.index(WEB_TOOL_BLOCK)


@pytest.mark.unit
def test_all_tools_present_together():
    """Everything bound: all three blocks, both schema tables, and normalization
    all land in the prompt."""
    out = build_search_prompt([KEYWORD, SEMANTIC, WEB])

    for piece in (SEARCH_PROMPT_BASE, PRODUCT_SCHEMA_HEADER, SEARCH_PROMPT_TRAILER,PRODUCT_SCHEMA_KEYWORD,PRODUCT_SCHEMA_FILTERS,CONTEXT,KEYWORD_TOOL_BLOCK,SEMANTIC_TOOL_BLOCK,WEB_TOOL_BLOCK):
        assert piece in out


@pytest.mark.unit
def test_duplicates_and_unknown_names_are_ignored():
    """Input is deduped and filtered to known tools, so repeats change nothing
    and junk names are dropped."""
    assert build_search_prompt([KEYWORD, KEYWORD]) == build_search_prompt([KEYWORD])
    assert build_search_prompt(["not-a-tool"]) == build_search_prompt([])


@pytest.mark.unit
@pytest.mark.parametrize("bad", [None, KEYWORD, (KEYWORD,), {KEYWORD}, [KEYWORD, 5]])
def test_non_list_of_strings_raises(bad):
    """Wrong types are a caller bug, so they raise rather than degrade quietly —
    None, a bare string, a tuple/set, or a list holding a non-string."""
    with pytest.raises(TypeError):
        build_search_prompt(bad)
