
import os
import json
import uuid
import asyncio
import chat_store
import session_state
from log.logger import log
from dotenv import load_dotenv
from contextlib import aclosing
from .LLMs.llm import summarizer_llm
from .models.models import SearchAgentState
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy, default_retry_on
from .prompts.prompt import SUMMARIZE_CONVERSATION_PROMPT
from langchain_core.messages.utils import count_tokens_approximately
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from .nodes.node import (
    search_node, tool_node, judge_node, orchestration_node,
    response_node, should_continue, default_error_handler,
)

load_dotenv(override=True)

# Fallback keep budget (tokens) if a caller doesn't pass one. Normally main.py
# passes SUMMARY_KEEP_TOKENS (a % of the compaction threshold).
DEFAULT_KEEP_TOKENS = int(os.getenv("SUMMARY_KEEP_TOKENS", "20000"))


def _msg_tokens(m: dict) -> int:
    """Approx token count of one agent-history message."""
    role = m.get("role")
    lc = AIMessage(content=m.get("content", "")) if role == "assistant" else HumanMessage(content=m.get("content", ""))
    return count_tokens_approximately([lc])


def _split_by_token_budget(history: list[dict], budget: int) -> tuple[list[dict], list[dict]]:
    """Split history into (fold, kept). Keeps the most-recent WHOLE turns whose token
    sum stays within `budget`, folding the rest. A turn starts at a user message and
    includes the assistant reply that follows. Rounds DOWN to a turn boundary; always
    keeps at least the last turn even if it alone exceeds the budget (never truncates a
    message); returns ([], history) when everything already fits (nothing to fold)."""
    if not history:
        return [], []
    turn_starts = [i for i, m in enumerate(history) if m.get("role") == "user"]
    if not turn_starts:
        return [], list(history)  # malformed (no user msg): keep all, fold nothing
    kept_start = turn_starts[-1]                      # last turn is always kept
    running = sum(_msg_tokens(m) for m in history[kept_start:])
    for ts in reversed(turn_starts[:-1]):
        turn_toks = sum(_msg_tokens(m) for m in history[ts:kept_start])
        if running + turn_toks > budget:
            break                                     # round down: stop before it exceeds
        running += turn_toks
        kept_start = ts
    return history[:kept_start], history[kept_start:]

# Hard cap on the summarizer LLM call. A hang (as opposed to an error) would
# otherwise leave the session stuck in the "compacting" state forever, since the
# caller's try/except only catches raised exceptions. On timeout we raise, which
# flows into _run_compaction's fallback (full, un-compacted context).
SUMMARY_TIMEOUT_S = float(os.getenv("SUMMARY_TIMEOUT_S", "45"))


workflow = StateGraph[SearchAgentState, None, SearchAgentState, SearchAgentState](SearchAgentState)
workflow.set_node_defaults(
    retry_policy=RetryPolicy(max_attempts=3, retry_on=default_retry_on), error_handler=default_error_handler
)

workflow.add_node("search_node", search_node)
workflow.add_node("tool_node", tool_node)
workflow.add_node("judge_node", judge_node)
workflow.add_node("orchestration_node", orchestration_node)
workflow.add_node("response_node", response_node)
workflow.add_edge(START, "search_node")
workflow.add_conditional_edges(
    "search_node",
    should_continue,
    ["tool_node", "response_node"]
)

# tool -> judge -> (response on match | orchestration on no match) -> (loop to
# search | response on budget exhausted). judge_node and orchestration_node route
# with Command, so no static edges out of them (same pattern as classify_intent).
workflow.add_edge("tool_node", "judge_node")
workflow.add_edge("response_node", END)


# No checkpointer: the graph is linear with no interrupts, and conversation
# history is persisted in Supabase (chat_messages) rather than in graph state.
search_agent = workflow.compile()

# build the agent's flow chart

# from IPython.display import Image, display
# graph_image = search_agent.get_graph(xray=True).draw_mermaid_png()
# with open("agent_flowchart.png", "wb") as f:
#     f.write(graph_image)
# print("Saved as agent_flowchart.png")


def _initial_state(query: str, messages: list) -> dict:
    """Fresh graph state for one run. Lists/None defaults keep the reducers and the
    node `state.get(...)` calls happy from the very first step."""
    return {
        "user_prompt": query,
        "messages": messages,
        "search_results": [],
        "search_call_iterations": 0,
        "classification": None,
        "tools_called": [],
        "first_tool": None,
        "keyword_params": None,
        "filters": None,
        "current_pool": [],
        "matched": [],
        "relevant": [],
    }


def _build_results(response: str, result: dict) -> dict:
    """Assemble the final "results" chunk. Carries the new matched/relevant split
    AND a combined `documents` (matched first, then relevant) so the existing
    persistence/frontend keep working until the UI consumes the split."""
    matched = result.get("matched", [])
    relevant = result.get("relevant", [])
    return {
        "type": "results",
        "response": response,
        "matched": matched,
        "relevant": relevant,
        "documents": matched + relevant,
        # Section tag for the matched bucket: "Matches" (semantic) or "Exact Matches"
        # (keyword). Defaults for the error path, which has no label.
        "match_label": result.get("match_label", "Exact Matches"),
    }


async def run_agent(query:str, config: dict = None)-> dict:
    if not query:
        return {"response": "Please enter a valid query", "matched": [], "relevant": []}
    result = await asyncio.to_thread(
        search_agent.invoke,
        _initial_state(query, [HumanMessage(query)]),
        config=config or {"configurable": {"thread_id": str(uuid.uuid4())}}
    )
    final = json.loads(result["messages"][-1].content)
    return {
        "response": final.get("response", ""),
        "matched": final.get("matched", []),
        "relevant": final.get("relevant", []),
    }

# ---------------------------------------------------------------------------
# Conversation summarization / compaction
# ---------------------------------------------------------------------------

def summarize_conversation(conversation_history: list, old_summary: str = "") -> list:
    """Fold a run of turns (and any prior summary) into a single paragraph.

    Lifted from tests/agent_tests/test_summarizer.py. Sync (blocking LLM call) —
    callers on the event loop must run it via asyncio.to_thread. Returns
    [summary] on success or [] if the model returned nothing.
    """
    tokens_before = count_tokens_approximately(conversation_history)
    if old_summary:
        tokens_before += count_tokens_approximately([AIMessage(content=old_summary)])

    turns = "\n".join(
        f"{'User' if m.type == 'human' else 'Halalify'}: {m.content}"
        for m in conversation_history
    )

    if old_summary:
        history_text = f"PREVIOUS SUMMARY:\n{old_summary}\n\nNEW TURNS:\n{turns}"
    else:
        history_text = f"NEW TURNS:\n{turns}"

    response = summarizer_llm.invoke([
        SystemMessage(content=SUMMARIZE_CONVERSATION_PROMPT),
        HumanMessage(content=history_text),
    ])

    tokens_after = count_tokens_approximately([response])
    log.info(
        "summary.tokens",
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        saved_pct=round((1 - tokens_after / tokens_before) * 100, 1) if tokens_before else None,
    )

    return [response.content] if response.content else []


def _history_dicts_to_lc(history: list[dict]) -> list:
    """Agent-form history entries -> LangChain messages for the summarizer.
    Assistant content is a json.dumps({response, documents}) blob; summarize the
    response text only (the product payload is noise for a summary)."""
    messages = []
    for m in history:
        content = m.get("content", "")
        if m.get("role") == "assistant":
            try:
                content = json.loads(content).get("response", content)
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def context_token_count(summary: str, lc_messages: list) -> int:
    """Approximate token count of the context the agent would receive: the
    summary (if any) prepended to the verbatim messages."""
    msgs = [AIMessage(content=summary)] + list(lc_messages) if summary else list(lc_messages)
    return count_tokens_approximately(msgs)


async def compact_session(session_id: str, keep_token_budget: int = DEFAULT_KEEP_TOKENS) -> tuple[str, list[dict], bool]:
    """Fold everything older than the recent verbatim tail into the rolling summary.

    The tail is the most-recent WHOLE turns fitting within `keep_token_budget` tokens
    (a % of the compaction threshold, passed by the caller) — so the kept size scales
    with token weight, not a fixed message count, keeping a stable margin below the
    trigger. Reads the Valkey history (entries carry their DB message id) and the
    current summary, summarizes the older slice, accumulates the covered message ids,
    persists a new chat_summaries row, and updates the Valkey summary + trimmed
    history. Returns (summary, kept_messages, did_compact). did_compact is False when
    everything already fits in the budget (nothing to fold) — a benign no-op. Raises
    if the model returned an empty summary so the caller can surface a failure.
    """
    history = await session_state.load_history(session_id) or []
    summary_state = await session_state.load_summary(session_id) or {}
    old_summary = summary_state.get("summary", "")
    old_ids = summary_state.get("message_ids", [])

    fold, kept = _split_by_token_budget(history, keep_token_budget)
    if not fold:
        # Everything fits in the keep budget — can't reduce further.
        return old_summary, history, False

    # Bound the blocking LLM call: a hung summarizer would otherwise strand the
    # session in "compacting" indefinitely. On timeout, wait_for raises
    # TimeoutError, handled like any other failure by _run_compaction's fallback.
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(summarize_conversation, _history_dicts_to_lc(fold), old_summary),
            timeout=SUMMARY_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        log.warning("compaction.summarize_timeout", session_id=session_id, timeout_s=SUMMARY_TIMEOUT_S)
        raise
    if not result:
        raise RuntimeError("summarizer returned no content")
    new_summary = result[0]

    # Accumulate: previous summary's ids + the ids we just folded in.
    folded_ids = [m["id"] for m in fold if m.get("id")]
    new_ids = list(old_ids) + folded_ids

    # DB is the source of truth and is written first: if this raises (retries
    # exhausted), the caller falls back to full context with the cache untouched.
    await chat_store.insert_summary(session_id, new_summary, new_ids)

    # Warm the cache for the NEXT turn. This turn is unaffected either way — it
    # uses the in-memory (new_summary, kept) returned below. If either write
    # fails the cache would be inconsistent with the DB, so invalidate both keys
    # (best-effort) and let the next turn's _load_context rebuild from the DB.
    ok_summary = await session_state.save_summary(session_id, new_summary, new_ids)
    ok_history = await session_state.seed_history(session_id, kept)  # trim to the verbatim tail
    if not (ok_summary and ok_history):
        log.warning("compaction.cache_reconcile", session_id=session_id, ok_summary=ok_summary, ok_history=ok_history)
        await session_state.clear_summary(session_id)
        await session_state.clear_history(session_id)

    kept_turns = sum(1 for m in kept if m.get("role") == "user")
    folded_turns = sum(1 for m in fold if m.get("role") == "user")
    kept_tokens = sum(_msg_tokens(m) for m in kept)
    log.info(
        "compaction.folded", session_id=session_id,
        kept_turns=kept_turns, folded_turns=folded_turns,
        kept_msgs=len(kept), folded_msgs=len(fold),
        kept_tokens=kept_tokens, keep_budget=keep_token_budget,
        covered_ids=len(new_ids),
    )
    return new_summary, kept, True

async def stream_agent(query: str, conversation_history: list):
    if not query:
        # Carries "type" like every other event this generator yields, so a client
        # routing on event["type"] handles the validation case with the same branch it
        # already uses for the final result.
        yield {"type": "results", "response": "Please enter a valid query", "documents": []}
        return
    
    final_result = None
    
    async with aclosing(
        search_agent.astream(
            _initial_state(query, conversation_history),
            stream_mode=["messages", "custom", "updates"],
            version="v2",
        )
    ) as stream:
        async for chunk in stream:
            if chunk["type"] == "updates":
                for node_name, state in chunk["data"].items():
                    if node_name == "__default_error_handler__" and state:
                        messages = state.get("messages", [])
                        if messages:
                            result = json.loads(messages[-1].content)
                            final_result = _build_results(result.get("response", "Some error occured, please try again."), result)
                            break
                    elif node_name == "response_node" and state:
                        messages = state.get("messages", [])
                        if messages:
                            result = json.loads(messages[-1].content)
                            final_result = _build_results(result.get("response", ""), result)
                            break
                if final_result:
                    break

            elif chunk["type"] == "messages":
                message, metadata = chunk["data"]
                node_name = metadata.get("langgraph_node", "")
                content_blocks = getattr(message, 'content_blocks', [])
                for block in content_blocks:
                    if block.get("type") == "reasoning":
                        reasoning = block.get("reasoning")
                        if reasoning:
                            yield {"type": "reasoning", "node": node_name, "reasoning": reasoning}

                tool_calls = getattr(message, 'tool_calls', [])
                for tool_call in tool_calls:
                    name = tool_call.get("name")
                    args = tool_call.get("args")
                    if name == "KeywordFilterSearch":
                        has_keywords = bool(args.get("keyword_args"))
                        has_filters = bool(args.get("filter_args"))
                        msg = None
                        if has_keywords and has_filters:
                            msg = "Searching keywords"
                        elif not has_keywords and has_filters:
                            msg = "Applying filters"
                        else:
                            msg = "Searching relevant products"
                        yield {"type": "tool_status", "node": node_name, "message": msg, "tool": name, "args": args}
                    elif name == "SemanticFilterSearch":
                        yield {"type": "tool_status", "node": node_name, "message": "Performing Semantic Search", "tool": name, "args": args}
                    elif name == "WebSearch":
                        yield {"type": "tool_status", "node": node_name, "message": "Searching the web", "tool": name, "args": args}

            elif chunk["type"] == "custom":
                data = chunk['data']
                if data.get("type") == "web_source":
                    yield {
                        "type": "web_source",
                        "url": data.get("url"),
                        "title": data.get("title"),
                        "favicon": data.get("favicon"),
                        "highlights": data.get("highlights", []),
                    }
                else:
                    search_results = data.get("search_results", [])
                    tool = data.get('tool', "Tool Result")
                    if search_results:
                        yield {"type": "search_results", "search_results": search_results, "tool": tool}

    if final_result:
        yield final_result