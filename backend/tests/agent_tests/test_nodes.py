"""Layer 4 — `agents/langgraph_agent/nodes/node.py`.

The node layer is where everything the previous layers pin actually runs: the tools get
invoked here, the routers here decide what happens next, and this is the only layer that
touches the LLM clients directly. So the tests split into three groups:

  * **pure functions** (`should_continue`, `_compact_candidate`, `_project`) tested
    without mocks;
  * **LLM-backed nodes** (`classify_intent`, `search_node`, `response_node`) tested with
    a fake LLM standing in for `with_structured_output` / `bind_tools`, so the *routing
    and state logic* is what is verified, not the provider;
  * **`tool_node`** tested with fake tools and a captured stream writer.

Three things are pinned deliberately:

  * **FINDINGS.md #4** — `classify_intent` reads `result.get("classification")`, so a
    schema-conformant reply (`{"intent": "direct"}`) is discarded and the `direct` intent
    is silently downgraded to a full search. Pinned with `xfail(strict=True)`.
  * **FINDINGS.md #11** — the search-loop cap drops the 4th search round's tool calls:
    only 3 of the 4 `MAX_SEARCH_ITERATIONS` rounds ever execute their tools, and the
    response LLM is handed an unanswered tool-call message. Pinned as characterisation
    (the behaviour is documented as intended; the wasted round is the finding).
  * **tool-failure propagation** — a tool that raises (findings 5/7) escapes `tool_node`
    and becomes a `NodeError` for `default_error_handler`; the escape is pinned as a
    characterisation test so it fails loudly once the tools stop crashing.
"""
import json
from types import SimpleNamespace

import pytest
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import NodeError
from langgraph.types import Command

import agents.langgraph_agent.nodes.node as node
from agents.langgraph_agent.models.models import OutputSchema, SelectedProducts, classify_intent_schema
from agents.langgraph_agent.prompts.prompt import CLASSIFICATION_PROMPT, SEARCH_PROMPT
from agents.langgraph_agent.tools.tools import KeywordFilterSearch, SemanticFilterSearch, WebSearch

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def fake_log(monkeypatch, recorder):
    """Silence node-level logging and capture it for the tests that assert on it."""
    log = SimpleNamespace(error=recorder(), warning=recorder(), info=recorder())
    monkeypatch.setattr(node, "log", log)
    return log


def _tool_call(name, args, id_="1"):
    return {"name": name, "args": args, "id": id_}


def _payload_of(output):
    """Parse the AIMessage content a node wrote as its final message."""
    msg = output["messages"][-1]
    assert isinstance(msg, AIMessage)
    return json.loads(msg.content)


# ---------------------------------------------------------------------------
# Top-level contracts
# ---------------------------------------------------------------------------


class TestConstants:
    def test_max_search_iterations_is_four(self):
        assert node.MAX_SEARCH_ITERATIONS == 4

    def test_search_tools_are_the_three_search_tools(self):
        assert node.search_tools == [KeywordFilterSearch, SemanticFilterSearch, WebSearch]

    def test_search_tools_by_name_indexes_every_tool(self):
        assert set(node.search_tools_by_name) == {t.name for t in node.search_tools}

    def test_fallback_n_is_three(self):
        assert node._FALLBACK_N == 3


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------


class _FakeStructuredLLM:
    """Stands in for an LLM that has `.with_structured_output(...).invoke(...)`."""

    def __init__(self):
        self.result = {}
        self.schema = None
        self.method = None
        self.messages_seen = None

    def with_structured_output(self, schema, method="json_mode"):
        self.schema = schema
        self.method = method
        return self

    def invoke(self, messages):
        self.messages_seen = messages
        return self.result


@pytest.fixture
def fake_extracter_llm(monkeypatch):
    fake = _FakeStructuredLLM()
    monkeypatch.setattr(node, "extracter_llm", fake)
    return fake


class TestClassifyIntent:
    def test_returns_a_command_with_only_a_goto(self, fake_extracter_llm):
        fake_extracter_llm.result = {"classification": "search"}
        cmd = node.classify_intent(_state(["hi"]))
        assert isinstance(cmd, Command)
        assert cmd.goto == "search_node"
        assert cmd.update is None

    def test_direct_classification_routes_to_response_node(self, fake_extracter_llm):
        fake_extracter_llm.result = {"classification": "direct"}
        assert node.classify_intent(_state(["hi"])).goto == "response_node"

    def test_search_classification_routes_to_search_node(self, fake_extracter_llm):
        fake_extracter_llm.result = {"classification": "search"}
        assert node.classify_intent(_state(["hi"])).goto == "search_node"

    def test_unknown_classification_falls_back_to_search_node(self, fake_extracter_llm):
        fake_extracter_llm.result = {"classification": "banana"}
        assert node.classify_intent(_state(["hi"])).goto == "search_node"

    def test_a_reply_missing_the_classification_key_falls_back_to_search_node(
        self, fake_extracter_llm
    ):
        # Finding #4, re-diagnosed: `classification` is the key the prompt asks for and
        # json_mode returns verbatim, so the node reading it was always correct — the
        # schema was renamed to match instead. A reply that omits the key (malformed, or
        # keyed on the old schema's `intent`) must degrade to a search, never crash: a
        # needless search costs latency, a skipped one costs the answer.
        fake_extracter_llm.result = {"intent": "direct"}
        assert node.classify_intent(_state(["hi"])).goto == "search_node"

    @pytest.mark.parametrize("result", [None, {}, {"classification": None}])
    def test_empty_or_missing_results_fall_back_to_search_node(
        self, fake_extracter_llm, result
    ):
        fake_extracter_llm.result = result
        assert node.classify_intent(_state(["hi"])).goto == "search_node"

    def test_messages_are_prefixed_with_the_classification_prompt(self, fake_extracter_llm):
        state = _state(["hello"])
        node.classify_intent(state)
        seen = fake_extracter_llm.messages_seen
        assert isinstance(seen[0], SystemMessage)
        assert seen[0].content == CLASSIFICATION_PROMPT
        assert seen[1:] == state["messages"]

    def test_uses_json_mode_with_the_classify_intent_schema(self, fake_extracter_llm):
        node.classify_intent(_state(["hi"]))
        assert fake_extracter_llm.schema == classify_intent_schema
        assert fake_extracter_llm.method == "json_mode"

    def test_missing_messages_key_raises_keyerror(self, fake_extracter_llm):
        with pytest.raises(KeyError):
            node.classify_intent({"user_prompt": "hi"})


# ---------------------------------------------------------------------------
# search_node
# ---------------------------------------------------------------------------


class _FakeBindTools:
    def __init__(self):
        self.tools_seen = None
        self.message = AIMessage(content="searching")
        self.messages_seen = None

    def bind_tools(self, tools):
        self.tools_seen = tools
        return self

    def invoke(self, messages):
        self.messages_seen = messages
        return self.message


@pytest.fixture
def fake_standard_llm(monkeypatch):
    fake = _FakeBindTools()
    monkeypatch.setattr(node, "standard_llm", fake)
    return fake


class TestSearchNode:
    def test_returns_the_llm_message_and_increments_iterations(self, fake_standard_llm):
        state = _state(["find biryani"], iterations=2)
        out = node.search_node(state)
        assert out["messages"] == [fake_standard_llm.message]
        assert out["search_call_iterations"] == 3

    def test_missing_iterations_starts_at_one(self, fake_standard_llm):
        out = node.search_node(_state(["find biryani"]))
        assert out["search_call_iterations"] == 1

    def test_binds_the_three_search_tools(self, fake_standard_llm):
        node.search_node(_state(["x"]))
        assert fake_standard_llm.tools_seen == [KeywordFilterSearch, SemanticFilterSearch, WebSearch]

    def test_prompts_are_prefixed_with_the_search_prompt(self, fake_standard_llm):
        state = _state(["find biryani"])
        node.search_node(state)
        seen = fake_standard_llm.messages_seen
        assert isinstance(seen[0], SystemMessage)
        assert seen[0].content == SEARCH_PROMPT
        assert seen[1:] == state["messages"]

    def test_missing_messages_key_raises_keyerror(self, fake_standard_llm):
        with pytest.raises(KeyError):
            node.search_node({"user_prompt": "x"})


# ---------------------------------------------------------------------------
# should_continue
# ---------------------------------------------------------------------------


class TestShouldContinue:
    def test_routes_to_tool_node_when_last_message_has_tool_calls(self):
        state = {"messages": [_with_tools()], "search_call_iterations": 1}
        assert node.should_continue(state) == "tool_node"

    def test_routes_to_response_node_when_no_tool_calls(self):
        state = {"messages": [AIMessage(content="done")], "search_call_iterations": 1}
        assert node.should_continue(state) == "response_node"

    def test_missing_iterations_counts_as_zero(self):
        state = {"messages": [_with_tools()]}
        assert node.should_continue(state) == "tool_node"

    def test_caps_the_loop_past_max_search_iterations(self):
        # Finding #11, fixed: search_node increments the counter *before* this runs, so the
        # cap must bite at MAX + 1, not at MAX.
        state = {
            "messages": [_with_tools()],
            "search_call_iterations": node.MAX_SEARCH_ITERATIONS + 1,
        }
        assert node.should_continue(state) == "response_node"

    def test_the_final_permitted_round_still_executes_its_tool_calls(self):
        # This is the regression guard for #11. Before the fix this round returned
        # "response_node", so the LLM's tool calls were generated and then silently
        # discarded, leaving an unanswered tool-call message in the conversation that
        # response_node then had to interpret.
        state = {
            "messages": [_with_tools()],
            "search_call_iterations": node.MAX_SEARCH_ITERATIONS,
        }
        assert node.should_continue(state) == "tool_node"

    def test_effective_tool_budget_is_the_full_max_search_iterations(self):
        for iteration in range(1, node.MAX_SEARCH_ITERATIONS + 1):
            state = {"messages": [_with_tools()], "search_call_iterations": iteration}
            assert node.should_continue(state) == "tool_node", (
                f"round {iteration} of {node.MAX_SEARCH_ITERATIONS} must be allowed to run"
            )

    def test_the_cap_still_ends_the_loop(self):
        # The budget is finite: past the cap we stop even if the model keeps asking.
        for iteration in (node.MAX_SEARCH_ITERATIONS + 1, node.MAX_SEARCH_ITERATIONS + 5):
            state = {"messages": [_with_tools()], "search_call_iterations": iteration}
            assert node.should_continue(state) == "response_node"

    def test_last_message_without_tool_calls_is_safe(self):
        state = {"messages": [ToolMessage(content="No products found.", tool_call_id="1")]}
        assert node.should_continue(state) == "response_node"

    def test_empty_messages_raise_indexerror(self):
        with pytest.raises(IndexError):
            node.should_continue({"messages": []})


# ---------------------------------------------------------------------------
# tool_node
# ---------------------------------------------------------------------------


def _fake_tool(name, observation):
    return SimpleNamespace(name=name, invoke=lambda args: observation)


@pytest.fixture
def fake_tools(monkeypatch):
    def install(tool_map):
        monkeypatch.setattr(node, "search_tools_by_name", tool_map, raising=True)
    return install


@pytest.fixture
def node_stream_writer(monkeypatch, recorder):
    rec = recorder()
    monkeypatch.setattr(node, "get_stream_writer", lambda: rec, raising=True)
    return rec


class TestToolNode:
    def test_executes_each_tool_call_and_collects_results(self, fake_tools, node_stream_writer):
        obs = [{"canonical_id": "p1"}]
        fake_tools({"KeywordFilterSearch": _fake_tool("KeywordFilterSearch", obs)})
        state = {"messages": [_with_tools(_tool_call("KeywordFilterSearch", {"keyword_args": None}))]}
        out = node.tool_node(state)
        assert out["search_results"] == obs
        assert len(out["messages"]) == 1
        assert isinstance(out["messages"][0], ToolMessage)

    def test_multiple_tools_in_one_message(self, fake_tools, node_stream_writer):
        fake_tools({
            "KeywordFilterSearch": _fake_tool("KeywordFilterSearch", [{"canonical_id": "a"}]),
            "WebSearch": _fake_tool("WebSearch", [{"canonical_id": "b"}]),
        })
        state = {"messages": [_with_tools(
            _tool_call("KeywordFilterSearch", {}),
            _tool_call("WebSearch", {}, id_="2"),
        )]}
        out = node.tool_node(state)
        assert [p["canonical_id"] for p in out["search_results"]] == ["a", "b"]
        assert len(out["messages"]) == 2

    def test_writes_each_non_empty_result_to_the_stream_writer(self, fake_tools, node_stream_writer):
        fake_tools({
            "KeywordFilterSearch": _fake_tool("KeywordFilterSearch", [{"canonical_id": "a"}]),
            "WebSearch": _fake_tool("WebSearch", [{"canonical_id": "b"}]),
        })
        state = {"messages": [_with_tools(
            _tool_call("KeywordFilterSearch", {}),
            _tool_call("WebSearch", {}, id_="2"),
        )]}
        node.tool_node(state)
        assert node_stream_writer.call_count == 2
        assert node_stream_writer.calls[0]["args"][0] == {"search_results": [{"canonical_id": "a"}], "tool": "KeywordFilterSearch"}
        assert node_stream_writer.calls[1]["args"][0]["tool"] == "WebSearch"

    def test_empty_observation_produces_no_products_found(self, fake_tools, node_stream_writer):
        fake_tools({"KeywordFilterSearch": _fake_tool("KeywordFilterSearch", [])})
        state = {"messages": [_with_tools(_tool_call("KeywordFilterSearch", {}))]}
        out = node.tool_node(state)
        assert out["search_results"] == []
        assert out["messages"][0].content == "No products found."

    def test_empty_observation_is_not_streamed(self, fake_tools, node_stream_writer):
        fake_tools({"KeywordFilterSearch": _fake_tool("KeywordFilterSearch", [])})
        state = {"messages": [_with_tools(_tool_call("KeywordFilterSearch", {}))]}
        node.tool_node(state)
        assert node_stream_writer.called is False

    def test_unknown_tool_produces_unknown_tool_message(self, fake_tools, node_stream_writer):
        fake_tools({})
        state = {"messages": [_with_tools(_tool_call("NotATool", {}))]}
        out = node.tool_node(state)
        assert out["messages"][0].content == "Unknown tool."
        assert out["search_results"] == []

    def test_unknown_tool_does_not_break_the_loop(self, fake_tools, node_stream_writer, fake_log):
        fake_tools({"KeywordFilterSearch": _fake_tool("KeywordFilterSearch", [{"canonical_id": "a"}])})
        state = {"messages": [_with_tools(
            _tool_call("NotATool", {}),
            _tool_call("KeywordFilterSearch", {}, id_="2"),
        )]}
        out = node.tool_node(state)
        assert out["messages"][0].content == "Unknown tool."
        assert out["messages"][1].content == json.dumps([{"canonical_id": "a"}])
        assert out["search_results"] == [{"canonical_id": "a"}]
        assert fake_log.warning.call_count == 1

    def test_tool_messages_carry_json_observation_and_call_id(self, fake_tools, node_stream_writer):
        obs = [{"canonical_id": "a", "norm_name": "x"}]
        fake_tools({"KeywordFilterSearch": _fake_tool("KeywordFilterSearch", obs)})
        state = {"messages": [_with_tools(_tool_call("KeywordFilterSearch", {}, id_="tc-7"))]}
        out = node.tool_node(state)
        assert out["messages"][0].content == json.dumps(obs)
        assert out["messages"][0].tool_call_id == "tc-7"

    def test_tool_failure_propagates_out_of_the_node(self, fake_tools, node_stream_writer):
        def boom(args):
            raise TypeError("sequence item 0: expected str instance, int found")
        fake_tools({"KeywordFilterSearch": SimpleNamespace(name="KeywordFilterSearch", invoke=boom)})
        state = {"messages": [_with_tools(_tool_call("KeywordFilterSearch", {}))]}
        with pytest.raises(TypeError, match="expected str instance"):
            node.tool_node(state)

    def test_observation_expected_to_be_a_list(self, fake_tools, node_stream_writer):
        fake_tools({"KeywordFilterSearch": _fake_tool("KeywordFilterSearch", {"canonical_id": "a"})})
        state = {"messages": [_with_tools(_tool_call("KeywordFilterSearch", {}))]}
        out = node.tool_node(state)
        assert out["search_results"] == ["canonical_id"]

    def test_last_message_without_tool_calls_raises(self, fake_tools, node_stream_writer):
        fake_tools({"KeywordFilterSearch": _fake_tool("KeywordFilterSearch", [])})
        state = {"messages": [HumanMessage("hi")]}
        with pytest.raises(AttributeError):
            node.tool_node(state)


# ---------------------------------------------------------------------------
# _compact_candidate
# ---------------------------------------------------------------------------


class TestCompactCandidate:
    def test_renders_id_line_and_present_fields(self):
        p = {"canonical_id": "p1", "norm_name": "nuggets", "halal_status": "Halal"}
        rendered = node._compact_candidate(p)
        assert rendered == "[id: p1]\nnorm_name: nuggets\nhalal_status: Halal"

    def test_joins_list_values_with_commas(self):
        p = {"canonical_id": "p1", "companies": ["Crestwood", "HalalCo"]}
        assert "companies: Crestwood, HalalCo" in node._compact_candidate(p)

    def test_skips_falsy_values(self):
        p = {"canonical_id": "p1", "companies": [], "halal_status": "", "norm_name": None}
        assert node._compact_candidate(p) == "[id: p1]"

    def test_missing_canonical_id_keeps_the_id_line(self):
        rendered = node._compact_candidate({"norm_name": "x"})
        assert rendered.startswith("[id: None]")

    def test_ignores_fields_outside_the_candidate_whitelist(self):
        p = {"canonical_id": "p1", "norm_name": "x", "embedding": [1], "verified": False}
        rendered = node._compact_candidate(p)
        assert "embedding" not in rendered
        assert "verified" not in rendered

    def test_renders_non_string_list_items(self):
        p = {"canonical_id": "p1", "barcodes": [123456, 789012]}
        assert "barcodes: 123456, 789012" in node._compact_candidate(p)


# ---------------------------------------------------------------------------
# _project
# ---------------------------------------------------------------------------


class TestProject:
    def test_keeps_only_output_schema_fields(self):
        raw = {"canonical_id": "p1", "norm_name": "x", "embedding": [1], "secret_key": "s"}
        proj = node._project(raw)
        assert set(proj) <= set(OutputSchema.model_fields)

    def test_defaults_missing_verified_to_true(self):
        assert node._project({"canonical_id": "p1"})["verified"] is True

    def test_preserves_web_products_verified_false(self):
        assert node._project({"canonical_id": "p1", "verified": False})["verified"] is False

    def test_keeps_grounding_citations(self):
        proj = node._project({"canonical_id": "p1", "grounding": [{"url": "http://x"}]})
        assert proj["grounding"] == [{"url": "http://x"}]


# ---------------------------------------------------------------------------
# response_node
# ---------------------------------------------------------------------------


class _FakeFinalChain:
    """Callable so `prompt | structured_llm` coerces it into the chain."""

    def __init__(self, result):
        self.result = result
        self.schema = None
        self.method = None
        self.last_input = None

    def __call__(self, prompt_value):
        self.last_input = prompt_value
        return self.result


class _FakeFinalLLM:
    def __init__(self):
        self.chain = _FakeFinalChain(SimpleNamespace(response="", product_ids=[]))

    def with_structured_output(self, schema, method=None):
        self.chain.schema = schema
        self.chain.method = method
        return self.chain


@pytest.fixture
def fake_final_llm(monkeypatch):
    fake = _FakeFinalLLM()
    monkeypatch.setattr(node, "final_extracter_llm", fake)
    return fake


def _db_products(make_product, count):
    return [make_product(canonical_id=f"p{i}") for i in range(1, count + 1)]


class TestResponseNode:
    def test_writes_response_and_selected_products_as_the_final_message(
        self, fake_final_llm, make_product
    ):
        products = _db_products(make_product, 2)
        fake_final_llm.chain.result = SimpleNamespace(response="here you go", product_ids=["p1", "p2"])
        state = _state(["find nuggets"], results=products)
        payload = _payload_of(node.response_node(state))
        assert payload["response"] == "here you go"
        assert [p["canonical_id"] for p in payload["products"]] == ["p1", "p2"]

    def test_selected_products_are_projected_and_default_to_verified(
        self, fake_final_llm, make_product
    ):
        products = _db_products(make_product, 1)
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=["p1"])
        payload = _payload_of(node.response_node(_state(["x"], results=products)))
        assert payload["products"][0]["verified"] is True
        assert payload["products"][0]["norm_name"] == "halal chicken nuggets"

    def test_preserves_web_verified_false_and_grounding(self, fake_final_llm):
        web = [{
            "canonical_id": "halal_abc12345",
            "norm_name": "web kitkat",
            "verified": False,
            "grounding": [{"url": "http://exa.ai/1"}],
        }]
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=["halal_abc12345"])
        payload = _payload_of(node.response_node(_state(["x"], results=web)))
        assert payload["products"][0]["verified"] is False
        assert payload["products"][0]["grounding"] == [{"url": "http://exa.ai/1"}]

    def test_strips_non_output_fields_from_selected_products(self, fake_final_llm, make_product):
        products = _db_products(make_product, 1)
        products[0]["embedding"] = [0.1, 0.2]
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=["p1"])
        payload = _payload_of(node.response_node(_state(["x"], results=products)))
        assert "embedding" not in payload["products"][0]

    def test_unknown_ids_are_skipped(self, fake_final_llm, make_product, fake_log):
        products = _db_products(make_product, 1)
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=["p1", "ghost"])
        payload = _payload_of(node.response_node(_state(["x"], results=products)))
        assert [p["canonical_id"] for p in payload["products"]] == ["p1"]
        assert fake_log.warning.call_count == 1

    def test_duplicate_ids_are_deduplicated(self, fake_final_llm, make_product):
        products = _db_products(make_product, 2)
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=["p1", "p1", "p2"])
        payload = _payload_of(node.response_node(_state(["x"], results=products)))
        assert [p["canonical_id"] for p in payload["products"]] == ["p1", "p2"]

    def test_selection_is_capped_at_ten(self, fake_final_llm, make_product):
        products = _db_products(make_product, 12)
        fake_final_llm.chain.result = SimpleNamespace(
            response="ok", product_ids=[f"p{i}" for i in range(1, 13)]
        )
        payload = _payload_of(node.response_node(_state(["x"], results=products)))
        assert len(payload["products"]) == 10

    def test_falls_back_to_recent_results_when_all_ids_are_unknown(
        self, fake_final_llm, make_product, fake_log
    ):
        products = _db_products(make_product, 5)
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=["ghost1", "ghost2"])
        payload = _payload_of(node.response_node(_state(["x"], results=products)))
        assert [p["canonical_id"] for p in payload["products"]] == ["p5", "p4", "p3"]
        assert fake_log.warning.call_count == 3

    def test_no_fallback_when_the_llm_returns_no_ids(self, fake_final_llm, make_product):
        products = _db_products(make_product, 3)
        fake_final_llm.chain.result = SimpleNamespace(response="nothing relevant", product_ids=[])
        payload = _payload_of(node.response_node(_state(["x"], results=products)))
        assert payload["products"] == []

    def test_empty_results_send_no_products_found_candidates(self, fake_final_llm):
        fake_final_llm.chain.result = SimpleNamespace(response="sorry", product_ids=[])
        node.response_node(_state(["x"], results=[]))
        rendered = fake_final_llm.chain.last_input.messages[0].content
        assert "No products found." in rendered

    def test_candidates_include_the_compact_product_blocks(self, fake_final_llm, make_product):
        products = _db_products(make_product, 1)
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=[])
        node.response_node(_state(["x"], results=products))
        rendered = fake_final_llm.chain.last_input.messages[0].content
        assert "[id: p1]" in rendered
        assert "norm_name: halal chicken nuggets" in rendered

    def test_missing_search_results_default_to_empty(self, fake_final_llm):
        fake_final_llm.chain.result = SimpleNamespace(response="ok", product_ids=[])
        state = _state(["x"])
        del state["search_results"]
        payload = _payload_of(node.response_node(state))
        assert payload["products"] == []

    def test_missing_messages_key_raises_keyerror(self, fake_final_llm):
        with pytest.raises(KeyError):
            node.response_node({"user_prompt": "x", "search_results": []})

    def test_uses_json_schema_with_selected_products(self, fake_final_llm):
        node.response_node(_state(["x"], results=[]))
        assert fake_final_llm.chain.schema is SelectedProducts
        assert fake_final_llm.chain.method == "json_schema"


# ---------------------------------------------------------------------------
# default_error_handler
# ---------------------------------------------------------------------------


class TestDefaultErrorHandler:
    def test_returns_a_command_routing_to_end(self):
        cmd = node.default_error_handler(_state(["x"]), _node_error())
        assert isinstance(cmd, Command)
        assert cmd.goto == "__end__"

    def test_appends_the_generic_apology_message(self):
        cmd = node.default_error_handler(_state(["x"]), _node_error())
        payload = json.loads(cmd.update["messages"][-1].content)
        assert payload == {"response": "Some error occured, please try again.", "products": []}

    def test_logs_the_failed_node_and_error_details(self, fake_log):
        err = _node_error()
        node.default_error_handler(_state(["x"]), err)
        assert fake_log.error.call_count == 1
        kwargs = fake_log.error.calls[0]["kwargs"]
        assert kwargs["node"] == "search_node"
        assert kwargs["error_type"] == "RuntimeError"
        assert str(err) in kwargs["error"]


def _node_error():
    return NodeError(node="search_node", error=RuntimeError("boom"))


def _state(texts, iterations=None, results=None):
    messages = [HumanMessage(t) if isinstance(t, str) else t for t in texts]
    state = {"user_prompt": texts[0], "messages": messages, "search_results": results or []}
    if iterations is not None:
        state["search_call_iterations"] = iterations
    return state


def _with_tools(*calls):
    return AIMessage(content="", tool_calls=[dict(c) for c in calls] or [
        _tool_call("KeywordFilterSearch", {})
    ])
