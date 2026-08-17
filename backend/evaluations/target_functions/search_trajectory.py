from agents.langgraph_agent.main_langgraph_agent import search_agent


# Target function: runs the full agent on a question and returns its message
# trajectory (used to evaluate the search-node tool calls).
async def run_search_node(inputs: dict) -> dict:
    question = inputs.get('question', '')
    if not question or not question.strip():
        return {"messages": []}

    results = await search_agent.ainvoke({"messages": [{"role": "user", "content": inputs['question']}]})

    messages = results.get("messages")
    if not messages:
        # no messages, return empty list
        return {"messages": []}

    return {"messages": messages}
