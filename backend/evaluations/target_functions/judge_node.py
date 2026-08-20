from langchain.messages import AIMessage
from agents.langgraph_agent.utils.utils import KEYWORD
from agents.langgraph_agent.nodes.node import judge_node

async def run_judge_node(inputs: dict) -> dict:
    keyword_args = inputs.get("keyword_args") or {}
    candidates = inputs.get("candidates") or []
    state = {
        "current_pool": candidates,
        "keyword_params": keyword_args,
        "first_tool": KEYWORD,
        "filters": None,
        "relevant": [],
        "tools_called": [KEYWORD],
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": KEYWORD, "args": {"keyword_args": keyword_args}, "id": "judge_eval_call"}],
            )
        ],
    }

    command = judge_node(state)
    matched = command.update.get("matched", [])
    return {"canonical_ids": [p.get("canonical_id") for p in matched if p.get("canonical_id")]}