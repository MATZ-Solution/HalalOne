import os
from dotenv import load_dotenv

# Point this process at the evaluation LangSmith account when one is configured.
# Both the client AND the background tracer read LANGSMITH_API_KEY from the
# environment, so it is promoted here before any other import creates them.
# The .env file is never modified; the running app keeps its own key.
load_dotenv(override=True)

if os.getenv("LANGSMITH_EVAL_API_KEY"):
    os.environ["LANGSMITH_API_KEY"] = os.environ["LANGSMITH_EVAL_API_KEY"]
    os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_EVAL_PROJECT", "halal-one-evals")

from config.langsmith_client import get_langsmith_client
import asyncio
# Datasets (LangSmith dataset names). Both files export `dataset_name`, so alias.
from evaluations.datasets.trajectory_dataset import dataset_name as trajectory_dataset_name
from evaluations.datasets.classification_dataset import dataset_name as classification_dataset_name
from evaluations.datasets.retrieval_relevance_dataset import dataset_name as retrieval_relevance_dataset_name
from evaluations.datasets.judge_node_dataset import dataset_name as judge_node_dataset_name, variant_dataset_name
from evaluations.datasets.task_completion_dataset import dataset_name as task_completion_dataset_name
from evaluations.datasets.knowledge_retention_dataset import dataset_name as knowledge_retention_dataset_name
# Evaluators
from evaluations.target_functions.search_trajectory import run_search_node
from evaluations.target_functions.intent_classifier import run_intent_classifier
from evaluations.target_functions.retrieval_relevance import run_retrieval_relevance
from evaluations.target_functions.judge_node import run_judge_node
from evaluations.target_functions.task_completion import run_task_completion
from evaluations.target_functions.knowledge_retention import run_knowledge_retention
from evaluations.evaluators.classification_correctness import correct_classification
from evaluations.evaluators.trajectory_correctness import agent_trajectory_correctness
from evaluations.evaluators.retrieval_relevance import retrieval_relevance
from evaluations.evaluators.judge_node_evaluator import judge_node_evaluator
from evaluations.evaluators.task_completion_evaluator import task_completion_evaluator
from evaluations.evaluators.knowledge_retention_evaluator import knowledge_retention_evaluator


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


# Evaluates judge_node in isolation — given the user's keyword criteria and a
# candidate blob, does the LLM field-match judge return EXACTLY the expected set of
# matching canonical_ids? Exact set match scores 1; any missed/extra id scores 0.
async def run_judge_node_evaluation():
    client = get_langsmith_client()
    return await client.aevaluate(
        run_judge_node,
        data=variant_dataset_name,
        evaluators=[judge_node_evaluator],
        experiment_prefix="experiment-halal-one-judge-node 1.0",
    )


# Evaluates task completion — replays each multi-turn conversation through the real
# agent and grades the resulting transcript as a whole: did the agent fully resolve
# every request the human made, or did any request get missed, half-answered, or
# require the human to re-ask/correct/follow up?
async def run_task_completion_evaluation():
    client = get_langsmith_client()
    return await client.aevaluate(
        run_task_completion,
        data=task_completion_dataset_name,
        evaluators=[task_completion_evaluator],
        experiment_prefix="experiment-halal-one-task-completion 1.0",
    )


# Evaluates knowledge retention — replays each multi-turn conversation through the
# real agent and grades the resulting transcript: did the agent stay consistent
# with facts, names, or details the human established earlier, or did it
# contradict, forget, or ignore them in a later turn?
async def run_knowledge_retention_evaluation():
    client = get_langsmith_client()
    return await client.aevaluate(
        run_knowledge_retention,
        data=knowledge_retention_dataset_name,
        evaluators=[knowledge_retention_evaluator],
        experiment_prefix="experiment-halal-one-knowledge-retention 1.0",
    )


# asyncio.run(run_classification_evaluation())
# asyncio.run(run_trajectory_evaluation())
# asyncio.run(run_retrieval_relevance_evaluation())
# asyncio.run(run_judge_node_evaluation())
# asyncio.run(run_task_completion_evaluation())
asyncio.run(run_knowledge_retention_evaluation())