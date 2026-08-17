import asyncio
from .dataset import dataset_name
from .evaluator import correct_classification
from config.langsmith_client import get_langsmith_client
from agents.langgraph_agent.main_langgraph_agent import search_agent

# Target function for running the relevant step
async def run_intent_classifier(inputs: dict) -> dict:
    # Note that we can access and run the intent_classifier node of our graph directly.
    command = await search_agent.nodes['classify_intent'].ainvoke(inputs)
    return {"classification": command.goto}

# Run evaluation

async def run_evaluation():
    client = get_langsmith_client()
    experiment_results = await client.aevaluate(
        run_intent_classifier,
        data=dataset_name,
        evaluators=[correct_classification],
        experiment_prefix="experiment-halal-one-node1-intent-classifier",
        max_concurrency=4,
    )

asyncio.run(run_evaluation())