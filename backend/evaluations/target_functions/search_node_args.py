import asyncio
from langchain.messages import HumanMessage
from agents.langgraph_agent.nodes.node import search_node


async def run_search_node_args(inputs: dict) -> dict:
    question = (inputs.get("question") or "").strip()
    if not question:
        return {"tool_name": None, "args": {}, "tool_calls": [], "classification": None, "response": ""}

    state = {
        "messages": [HumanMessage(question)],
        "tools_called": [],
        "first_tool": None,
    }

    update = await asyncio.to_thread(search_node, state)

    message = update["messages"][-1]
    tool_calls = [
        {"name": tc["name"], "args": tc["args"]}
        for tc in (getattr(message, "tool_calls", None) or [])
    ]

    return {
        "tool_name": tool_calls[0]["name"] if tool_calls else None,
        "args": tool_calls[0]["args"] if tool_calls else {},
        "tool_calls": tool_calls,
        "classification": update.get("classification"),
        "response": message.content or "",
    }
