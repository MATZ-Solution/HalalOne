from langchain.messages import HumanMessage, AIMessage
from agents.langgraph_agent.main_langgraph_agent import search_agent, _initial_state


# Target function: replays a full multi-turn conversation through the real agent,
# one turn at a time, accumulating history exactly the way production does
# (backend/main.py's _history_to_messages -> stream_agent -> _initial_state): each
# turn's HumanMessage is appended, the graph is run on the history so far, and the
# agent's final message is appended back as an AIMessage before the next turn.
# Returns the full trajectory for the knowledge-retention judge to grade.
async def run_knowledge_retention(inputs: dict) -> dict:
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
