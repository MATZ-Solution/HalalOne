import asyncio
from .dataset import dataset_name
from .evaluator import agent_trajectory_correctness
from config.langsmith_client import get_langsmith_client
from agents.langgraph_agent.main_langgraph_agent import search_agent



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

async def run_evaluation():
    client = get_langsmith_client()
    experiment_results = await client.aevaluate(
        run_search_node,
        data=dataset_name,
        evaluators=[agent_trajectory_correctness],
        experiment_prefix="experiment-halal-one-agent-trajectory-evaluation 1.0"
    )


results = asyncio.run(run_evaluation())