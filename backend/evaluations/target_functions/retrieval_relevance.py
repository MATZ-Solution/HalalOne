from agents.langgraph_agent.main_langgraph_agent import search_agent


# Target function: runs the full agent on a conceptual query and returns its
# message trajectory. The final message holds the products shown to the user,
# which is what the retrieval_relevance evaluator judges.
async def run_retrieval_relevance(inputs: dict) -> dict:
    question = inputs.get('question', '')
    if not question or not question.strip():
        return {"messages": []}

    results = await search_agent.ainvoke({"messages": [{"role": "user", "content": question}]})

    messages = results.get("messages")
    if not messages:
        # no messages, return empty list
        return {"messages": []}

    return {"messages": messages}
