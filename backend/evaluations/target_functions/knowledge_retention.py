from langchain.messages import HumanMessage, AIMessage
from agents.langgraph_agent.main_langgraph_agent import search_agent, _initial_state


def _to_messages(history: list[dict]) -> list:
    """Dataset-form {role, content} history -> LangChain messages, the same
    mapping backend/main.py's _history_to_messages does for real conversations."""
    messages = []
    for m in history:
        content = m.get("content", "")
        if m.get("role") == "user":
            messages.append(HumanMessage(content))
        else:
            messages.append(AIMessage(content))
    return messages


# Target function: the dataset's `history` is a FIXED, pre-authored conversation
# (both sides — user and assistant — already written out), ending on an
# unanswered user turn (the probe). This makes exactly ONE real call to the
# agent, on that final turn, with everything before it passed in as-is —
# mirroring exactly how production replays history (backend/main.py's
# _history_to_messages -> _initial_state -> a single ainvoke per new user
# message), rather than having the eval itself simulate every prior turn live.
# What's being measured is whether that one real response stays consistent
# with facts planted earlier in the fixed history.
async def run_knowledge_retention(inputs: dict) -> dict:
    history = inputs.get("history", [])
    if not history or history[-1].get("role") != "user":
        return {"messages": []}

    probe = history[-1]["content"]
    conversation_history = _to_messages(history)

    result = await search_agent.ainvoke(_initial_state(probe, conversation_history))
    messages = result.get("messages")
    reply = messages[-1].content if messages else ""

    return {"messages": conversation_history + [AIMessage(content=reply)]}
