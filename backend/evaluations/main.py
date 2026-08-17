from config.langsmith_client import get_langsmith_client
import asyncio
# Datasets (LangSmith dataset names). Both files export `dataset_name`, so alias.
from evaluations.datasets.trajectory_dataset import dataset_name as trajectory_dataset_name
from evaluations.datasets.classification_dataset import dataset_name as classification_dataset_name
from evaluations.datasets.retrieval_relevance_dataset import dataset_name as retrieval_relevance_dataset_name
# Evaluators
from evaluations.target_functions.search_trajectory import run_search_node
from evaluations.target_functions.intent_classifier import run_intent_classifier
from evaluations.target_functions.retrieval_relevance import run_retrieval_relevance
from evaluations.evaluators.classification_correctness import correct_classification
from evaluations.evaluators.trajectory_correctness import agent_trajectory_correctness
from evaluations.evaluators.retrieval_relevance import retrieval_relevance


# Evaluates Node 1 — intent classification: does the agent route each prompt to the correct branch (search_node vs response_node)?
async def run_classification_evaluation():
    client = get_langsmith_client()
    return await client.aevaluate(
        run_intent_classifier,
        data=classification_dataset_name,
        evaluators=[correct_classification],
        experiment_prefix="experiment-halal-one-node1-intent-classifier",
        max_concurrency=4,
    )


# Evaluates Node 2 — search trajectory: are the search-node tool calls correct in name, order (fallback ladder + budget), and arguments?
async def run_trajectory_evaluation():
    client = get_langsmith_client()
    return await client.aevaluate(
        run_search_node,
        data=trajectory_dataset_name,
        evaluators=[agent_trajectory_correctness],
        experiment_prefix="experiment-halal-one-agent-trajectory-evaluation 1.0",
    )


# Evaluates retrieval relevance — on conceptual queries (semantic-first search),
# how relevant are the returned products to the user's request? Reports the average
# per-product confidence and the fraction judged relevant; a no-result query passes.
async def run_retrieval_relevance_evaluation():
    client = get_langsmith_client()
    return await client.aevaluate(
        run_retrieval_relevance,
        data=retrieval_relevance_dataset_name,
        evaluators=[retrieval_relevance],
        experiment_prefix="experiment-halal-one-retrieval-relevance 1.0",
    )


# asyncio.run(run_classification_evaluation())
# asyncio.run(run_trajectory_evaluation())
asyncio.run(run_retrieval_relevance_evaluation())
