from agents.langgraph_agent.main_langgraph_agent import search_agent


# Target function: runs the agent's intent-classifier node directly and returns
# the route it chose (search_node / response_node).
async def run_intent_classifier(inputs: dict) -> dict:
    command = await search_agent.nodes['classify_intent'].ainvoke(inputs)
    return {"classification": command.goto}
