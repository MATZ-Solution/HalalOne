import json
from typing import Literal
from log.logger import log
from pydantic import ValidationError
from langgraph.graph import END
from langgraph.types import Command
from langgraph.errors import NodeError
from langgraph.config import get_stream_writer
from langchain_core.exceptions import OutputParserException
from langchain.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from ..models.models import SearchAgentState, OutputSchema, JudgeVerdict, FinalResponse, classify_intent_schema
from ..LLMs.llm import extracter_llm, final_extracter_llm, standard_llm, judge_llm
from ..prompts.prompt import (
    CLASSIFICATION_PROMPT, SEARCH_PROMPT, FINAL_RESPONSE_PROMPT, JUDGE_PROMPT,
    NO_EXACT_SIMILAR_MSG, NO_RESULTS_MSG, SEMANTIC_RESULTS_MSG,
)
from ..tools.tools import KeywordFilterSearch, SemanticFilterSearch, WebSearch
from ..utils.utils import KEYWORD_FIELDS, select_tools, should_loop, validate_ids, apply_filter_check, dedup_by_id


TOOLS_BY_NAME = {t.name: t for t in [KeywordFilterSearch, SemanticFilterSearch, WebSearch]}

# Re-ask the judge at most this many times if it returns ids that aren't in the
# candidate pool (hallucinated), before falling back to the valid ids only.
JUDGE_MAX_RETRIES = 2


def classify_intent(state: SearchAgentState) -> Command[Literal["search_node", "response_node"]]:
    """Use an llm to classify user's intent from prompt: search or direct."""

    structured_llm = extracter_llm.with_structured_output(classify_intent_schema, method='json_mode')
    messages = [SystemMessage(CLASSIFICATION_PROMPT)] + state["messages"]
    result = structured_llm.invoke(messages)
    classification = result.get("classification")
    goto = "response_node" if classification == "direct" else "search_node"
    return Command(update={"classification": classification}, goto=goto)


def search_node(state: SearchAgentState) -> dict:
    """Issue exactly one search tool call.

    Which tools are available is decided by the ladder (select_tools), not by the
    LLM — only the allowed tool(s) are bound and a call is forced. So the fallback
    order is guaranteed while the LLM is still free to reformulate the args for the
    tool it's given. The first entry binds {keyword, semantic}: that pick sets the
    whole trajectory.
    """
    names = select_tools(state.get("first_tool"), state.get("tools_called", []))
    tools = [TOOLS_BY_NAME[n] for n in names]
    # "any" forces the model to call one of the bound tools, so the ladder order
    # holds; with a single tool bound it's effectively forced to that one.
    llm_with_tools = standard_llm.bind_tools(tools, tool_choice="any")
    result = llm_with_tools.invoke([SystemMessage(SEARCH_PROMPT)] + state["messages"])
    return {"messages": [result]}


def should_continue(state: SearchAgentState) -> Literal["tool_node", "response_node"]:
    """Run the pending tool call, or (safety only, since the call is forced) go
    straight to the response."""
    last_message = state["messages"][-1]
    return "tool_node" if getattr(last_message, "tool_calls", None) else "response_node"


def tool_node(state: SearchAgentState) -> dict:
    """Execute the tool call and keep the full results in state. The ToolMessage
    is written by judge_node instead (it knows the match verdict), so no message is
    appended here — judge_node runs next and never invokes an LLM on state messages
    in between, so the tool-call/tool-result protocol stays intact."""

    writer = get_stream_writer()
    tool_calls = state["messages"][-1].tool_calls
    pool: list = []
    ran = None
    keyword_params = None
    filters = None

    for tool_call in tool_calls:
        tool = TOOLS_BY_NAME.get(tool_call["name"])
        if tool is None:
            log.warning("agent.tool.unknown", tool=tool_call["name"])
            continue

        observation = tool.invoke(tool_call["args"]) or []
        ran = tool_call["name"]
        # The judge compares downstream results against the LATEST keyword criteria,
        # so capture them whenever a keyword search runs.
        if tool_call["name"] == KeywordFilterSearch.name:
            keyword_params = tool_call["args"].get("keyword_args")
            filters = tool_call["args"].get("filter_args")

        if observation:
            writer({"search_results": observation, "tool": tool_call["name"]})
            pool.extend(observation)

    update: dict = {
        "tools_called": [ran] if ran else [],
        "current_pool": pool,
    }
    # first tool call sets the trajectory (and its budget)
    if not state.get("first_tool") and ran:
        update["first_tool"] = ran
    # store the latest keyword criteria for the judge (only on a keyword call)
    if ran == KeywordFilterSearch.name:
        update["keyword_params"] = keyword_params
        update["filters"] = filters
    return update


def _compact_for_judge(product: dict, fields: list[str]) -> str:
    """One compact block per candidate for the judge: id + only the given fields.
    Keeps the prompt small and stops the judge matching on fields the user never
    provided."""
    lines = [f"id: {product.get('canonical_id')}"]
    for field in fields:
        value = product.get(field)
        if not value:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{field}: {value}")
    return "\n".join(lines)


def _judge_matches(keyword_params: dict, candidates: list) -> list:
    """LLM-as-judge: ids of the candidates that exactly match the user's keyword
    criteria. Re-asks with feedback if it invents ids, then keeps only valid ones."""
    if not candidates:
        return []

    # Show only the keyword fields the user actually gave: the judge compares each
    # provided field against the product's same field, nothing else.
    show_fields = [f for f in KEYWORD_FIELDS if keyword_params.get(f)]

    candidate_ids = [c.get("canonical_id") for c in candidates if c.get("canonical_id")]
    blob = "\n\n".join(_compact_for_judge(c, show_fields) for c in candidates)
    messages = [
        SystemMessage(JUDGE_PROMPT),
        HumanMessage(f"USER WANTS:\n{json.dumps(keyword_params)}\n\nCANDIDATES:\n{blob}"),
    ]

    valid: list = []
    for attempt in range(JUDGE_MAX_RETRIES + 1):
        try:
            # the judge llm is also emitting a reasoning field (extra tokens). Have to see whether to remove it or not.
            verdict: JudgeVerdict = judge_llm.invoke(messages)
        except (OutputParserException, ValidationError) as e:
            # The model's output didn't fit the required schema (bad JSON or wrong
            # shape) — its own fault, so feed the error back and let it correct.
            log.warning("judge.parse_failed", error=str(e), attempt=attempt + 1)
            messages.append(HumanMessage(
                "Your previous reply could not be parsed into the required schema. "
                f"Error: {e}. Reply with ONLY valid JSON of the form "
                + '{"reasoning": "<your reasoning>", "matched_ids": ["<id>", ...]} and nothing else.'
            ))
            continue
        except Exception as e:
            # Transient/infra (rate limit, timeout, network): not the model's fault
            # and nothing to feed back — bail with whatever's valid so far.
            log.error("judge.invoke.failed", error=str(e), error_type=type(e).__name__)
            return valid
        valid, hallucinated = validate_ids(verdict.matched_ids, candidate_ids)
        if not hallucinated:
            return valid
        log.warning("judge.hallucinated_ids", ids=hallucinated, attempt=attempt + 1)
        messages.append(AIMessage(content=json.dumps({"matched_ids": verdict.matched_ids})))
        messages.append(HumanMessage(
            f"You returned ids that are not in the candidates: {hallucinated}. "
            "Only return ids that appear verbatim on an `id:` line. Do not infer or invent."
        ))
    return valid


def judge_node(state: SearchAgentState) -> Command[Literal["response_node", "orchestration_node"]]:
    """Split the latest tool results into matched vs relevant.

    - Semantic-FIRST query: purely conceptual, no exact target → nothing "matches";
      everything found is a relevant/similar suggestion. (A downstream semantic
      call under a keyword-first query is still judged with the stored criteria.)
    - Filter-rejected products are dropped outright — they break the user's explicit
      filters, so they are neither matched nor relevant.
    - Keyword criteria (if given) are checked by the LLM judge; the passers that
      don't match become relevant/similar suggestions.

    On a match we return to response immediately (first match ends the loop);
    otherwise we accumulate relevant and hand off to orchestration.
    """
    pool = state.get("current_pool", [])
    prior_relevant = state.get("relevant", [])
    keyword_params = state.get("keyword_params")

    if state.get("first_tool") == SemanticFilterSearch.name:
        matched, non_matched = [], pool
    else:
        # Only filter-passers can be matched or relevant; rejected ones are dropped.
        passers, _rejected = apply_filter_check(pool, state.get("filters"))
        if keyword_params:
            matched_ids = set(_judge_matches(keyword_params, passers))
            matched = [p for p in passers if p.get("canonical_id") in matched_ids]
            non_matched = [p for p in passers if p.get("canonical_id") not in matched_ids]
        else:
            # filter-only query → the filter passers ARE the matches (no LLM needed)
            matched, non_matched = passers, []

    # Non-matching passers are always relevant/similar, accumulated across calls
    # and de-duplicated. Filter-rejected products never enter relevant.
    relevant = dedup_by_id(prior_relevant + non_matched)

    # Author the ToolMessage here (not in tool_node) so it states the JUDGED
    # outcome: on a no-match loop, search_node reads an authoritative "no products
    # matched" signal instead of a raw count it could mistake for success. Required
    # for the tool-call protocol, so it's emitted on both paths.
    last_tool = state.get("tools_called", [])[-1] if state.get("tools_called") else "search"
    summary = (
        f"{last_tool}: found {len(matched)} matching product(s)."
        if matched else
        f"{last_tool}: no products matched."
    )
    tool_calls = getattr(state["messages"][-1], "tool_calls", None) or []
    tool_messages = [ToolMessage(content=summary, tool_call_id=tc["id"]) for tc in tool_calls]

    if matched:
        return Command(update={"messages": tool_messages, "matched": matched, "relevant": relevant}, goto="response_node")
    return Command(update={"messages": tool_messages, "matched": [], "relevant": relevant}, goto="orchestration_node")


def orchestration_node(state: SearchAgentState) -> Command[Literal["search_node", "response_node"]]:
    """Loop controller: fall back to the next tool if the budget allows, else stop.

    Semantic-first is a special case: it produces no exact matches, so we stop as
    soon as it returned something (relevant non-empty). Only an EMPTY first semantic
    call earns a second (reformulated) attempt within the budget.
    """
    first_tool = state.get("first_tool")
    calls = len(state.get("tools_called", []))

    if first_tool == SemanticFilterSearch.name:
        loop = not state.get("relevant") and should_loop(first_tool, calls)
    else:
        loop = should_loop(first_tool, calls)

    return Command(goto="search_node" if loop else "response_node")

# Fields allowed out to the client (whitelist applied when returning products).
_ALLOWED_OUT = set(OutputSchema.model_fields)

def _project(raw: dict) -> dict:
    """Return only client-facing fields; default DB products to verified."""
    proj = {k: v for k, v in raw.items() if k in _ALLOWED_OUT}
    proj.setdefault("verified", True)
    return proj


def response_node(state: SearchAgentState) -> dict:
    """Attach the already-decided product buckets and set the message.

    The split (matched/relevant) was done in judge_node, so this node never
    re-selects products. It also avoids the LLM whenever the outcome is known:
      - exact matches found → empty response (the cards speak for themselves)
      - only similar found   → fixed "no exact match, here are similar" message
      - search found nothing → fixed "couldn't find it" message
      - direct chit-chat     → LLM for a contextual, conversational reply
    """
    matched = state.get("matched", [])
    relevant = state.get("relevant", [])

    if matched:
        response = ""
    elif relevant:
        # semantic-first query wanted "similar", so don't apologise for missing
        # exact matches the user never asked for.
        response = SEMANTIC_RESULTS_MSG if state.get("first_tool") == SemanticFilterSearch.name else NO_EXACT_SIMILAR_MSG
    elif state.get("classification") == "search":
        response = NO_RESULTS_MSG
    else:
        # direct classification: no products, so let the LLM answer conversationally
        structured_llm = final_extracter_llm.with_structured_output(FinalResponse, method="json_schema")
        result = structured_llm.invoke([SystemMessage(FINAL_RESPONSE_PROMPT), *state["messages"]])
        response = result.response

    final = {
        "response": response,
        "matched": [_project(p) for p in matched][:10],
        "relevant": [_project(p) for p in relevant][:10],
    }
    return {"messages": [AIMessage(content=json.dumps(final))]}


def default_error_handler(state: SearchAgentState, error: NodeError):
    """Recovery node, handles node failures."""

    log.error("agent.node.failed", node=error.node, error=str(error), error_type=type(error.error).__name__)
    response_object = {"response": "Some error occured, please try again.", "matched": [], "relevant": []}

    return Command(
        update={"messages": [AIMessage(content=json.dumps(response_object))]},
        goto=END,
    )
