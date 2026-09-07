from agents.langgraph_agent.main_langgraph_agent import _initial_state, search_agent
from langchain.messages import AIMessage, HumanMessage


async def run_task_completion(inputs: dict) -> dict:
    turns = [t for t in inputs.get("turns", []) if t and t.strip()]
    if not turns:
        return {"messages": []}

    conversation_history = []
    for turn in turns:
        conversation_history.append(HumanMessage(turn))
        result = await search_agent.ainvoke(_initial_state(turn, conversation_history))
        messages = result.get("messages")
        reply = messages[-1].content if messages else ""
        conversation_history.append(AIMessage(content=reply))

    return {"messages": conversation_history}
