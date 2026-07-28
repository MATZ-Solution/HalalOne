import json
from typing import Literal
from log.logger import log
from langgraph.graph import END
from langgraph.types import Command
from langgraph.errors import NodeError
from ..models.models import OutputSchema, SelectedProducts
from langgraph.config import get_stream_writer
from langchain_core.prompts import ChatPromptTemplate
from ..tools.tools import SemanticFilterSearch, KeywordFilterSearch, WebSearch
from ..models.models import SearchAgentState, classify_intent_schema
from ..LLMs.llm import extracter_llm, final_extracter_llm, standard_llm
from langchain.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from ..prompts.prompt import CLASSIFICATION_PROMPT, SEARCH_PROMPT, FINAL_RESPONSE_PROMPT


MAX_SEARCH_ITERATIONS = 4

def classify_intent(state: SearchAgentState) -> Command[Literal["search_node", "response_node"]]:
    """Use an llm to classify user's intent from prompt"""

    structured_llm = extracter_llm.with_structured_output(classify_intent_schema, method = 'json_mode')
    messages = [SystemMessage(CLASSIFICATION_PROMPT)] + state["messages"]
    result = structured_llm.invoke(messages)
    goto = "search_node"
    if result.get("classification") == "search":
        goto = "search_node"
    elif result.get("classification") == "direct":
        goto = "response_node"

    return Command(
        goto = goto
    )


# search tools
search_tools = [KeywordFilterSearch, SemanticFilterSearch, WebSearch]
search_tools_by_name = {tool.name: tool for tool in search_tools}

def search_node(state: SearchAgentState) -> dict:
    """
    Searches TypeSense to retrieve relevant halal products
    Two core components:
    1. Keyword + Filter based search
    2. Semantic + Filter based search
    """
    search_iterations = state.get("search_call_iterations", 0)
    # Always bind tools. The loop is capped in should_continue instead of by
    # dropping tools here — gpt-oss on Groq still emits a tool call when no tools
    # are bound, which Groq rejects ("tool choice is none, but model called a tool").
    llm_with_tools = standard_llm.bind_tools(search_tools)
    result = llm_with_tools.invoke([SystemMessage(SEARCH_PROMPT)] + state['messages'])

    return {
        "messages": [result],
        "search_call_iterations": search_iterations + 1
    }


def should_continue(state: SearchAgentState) -> Literal["tool_node", "response_node"]:
    """Route after each LLM call: run pending tool calls, else format the answer.
    WebSearch is one of the tools, so the LLM decides (with full context of the
    DB results it already saw) whether to escalate to the web."""

    last_message = state["messages"][-1]
    has_tool_calls = bool(getattr(last_message, "tool_calls", None))
    iterations = state.get("search_call_iterations", 0)

    # Cap the search loop here. Past the budget we go to response_node even if the
    # model asked for more tools (its last tool calls are simply not executed).
    if has_tool_calls and iterations < MAX_SEARCH_ITERATIONS:
        return "tool_node"
    return "response_node"


def tool_node(state: SearchAgentState) -> dict:
    """Executes the tools invoked."""

    # initialize the stream writer
    writer = get_stream_writer()
    search_results = []
    tool_messages = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = search_tools_by_name.get(tool_call["name"])
        if tool is None:
            log.warning("agent.tool.unknown", tool=tool_call["name"])
            tool_messages.append(ToolMessage(
                content="Unknown tool.", tool_call_id=tool_call["id"]
            ))
            continue
        observation = tool.invoke(tool_call['args'])
        if not observation:
            tool_messages.append(ToolMessage(
            content="No products found.", tool_call_id=tool_call["id"]
            ))
            continue
        writer({"search_results": observation, "tool": tool_call["name"]})
        search_results.extend(observation)
        tool_messages.append(ToolMessage(content=json.dumps(observation), tool_call_id = tool_call["id"]))

    return {"messages": tool_messages, "search_results": search_results}


# Queryable product fields shown to the final LLM (compact). Bulky / internal
# fields (grounding, embedding, source_files, source_ids) are deliberately left
# out — they aren't needed to judge relevance and would inflate the prompt.
_CANDIDATE_FIELDS = [
    "norm_name", "companies", "halal_status", "cert_bodies", "cert_numbers",
    "category_l1", "category_l2", "sold_in", "marketplace", "fda_numbers",
    "barcodes", "typical_uses", "health_info",
]
# Fields allowed out to the client (whitelist applied when returning products).
_ALLOWED_OUT = set(OutputSchema.model_fields)
_FALLBACK_N = 3


def _compact_candidate(p: dict) -> str:
    """One compact, LLM-friendly block per product: an id line + present fields."""
    lines = [f"[id: {p.get('canonical_id')}]"]
    for field in _CANDIDATE_FIELDS:
        value = p.get(field)
        if not value:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{field}: {value}")
    return "\n".join(lines)


def _project(raw: dict) -> dict:
    """Return only client-facing fields; default DB products to verified."""
    proj = {k: v for k, v in raw.items() if k in _ALLOWED_OUT}
    proj.setdefault("verified", True)
    return proj


def response_node(state: SearchAgentState) -> dict:
    """Writes the user-facing message and selects which products to show.

    The LLM only returns the ids of the relevant products; the product objects
    are looked up by canonical_id and returned verbatim. This keeps the data
    deterministic (no field mangling/hallucination) and the output cheap.
    """

    all_results = state.get("search_results", [])
    candidates = "\n\n".join(_compact_candidate(p) for p in all_results) or "No products found."

    structured_llm = final_extracter_llm.with_structured_output(SelectedProducts, method="json_schema")
    prompt = ChatPromptTemplate.from_template(FINAL_RESPONSE_PROMPT)
    chain = prompt | structured_llm
    result = chain.invoke({
        "halal_search_results": candidates,
        "conversation_history": state["messages"],
    })

    # Resolve ids -> products deterministically. Unknown ids (hallucinated) are
    # skipped; duplicates de-duped; order follows the LLM's relevance order.
    by_id = {p.get("canonical_id"): p for p in all_results if p.get("canonical_id")}
    selected, seen = [], set()
    for pid in result.product_ids:
        if pid not in by_id:
            log.warning("response_node.unknown_product_id", product_id=pid)
            continue
        if pid in seen:
            continue
        seen.add(pid)
        selected.append(_project(by_id[pid]))
        if len(selected) >= 10:
            break
    # Fallback: the LLM tried to select (returned ids) but none matched, while we
    # do have results -> show the most recent few (no unified score across DB/web).
    if result.product_ids and not selected and all_results:
        log.warning("response_node.no_ids_matched", note="falling back to recent results")
        selected = [_project(p) for p in reversed(all_results[-_FALLBACK_N:])]
    
    final = {"response": result.response, "products": selected}
    return {
        "messages": [AIMessage(content=json.dumps(final))]
    }



def default_error_handler(state: SearchAgentState, error: NodeError):
    """Recovery node, handles node failures."""

    log.error("agent.node.failed", node=error.node, error=str(error), error_type=type(error.error).__name__)
    response_object = {"response": "Some error occured, please try again.", "products": []}
    
    return Command(
        update = {"messages": [AIMessage(content=json.dumps(response_object))]},
        goto = END
    )