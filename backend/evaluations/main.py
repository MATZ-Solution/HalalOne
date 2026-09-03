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
from evaluations.datasets.search_node_args_dataset import dataset_name as search_node_args_dataset_name
from evaluations.datasets.keyword_search_dataset import dataset_name as keyword_search_dataset_name
from evaluations.datasets.semantic_search_dataset import dataset_name as semantic_search_dataset_name
# Evaluators
from evaluations.target_functions.search_trajectory import run_search_node
from evaluations.target_functions.intent_classifier import run_intent_classifier
from evaluations.target_functions.retrieval_relevance import run_retrieval_relevance
from evaluations.target_functions.judge_node import run_judge_node
from evaluations.target_functions.search_node_args import run_search_node_args
from evaluations.evaluators.search_node_args_evaluator import search_node_args_correctness
from evaluations.evaluators.classification_correctness import correct_classification
from evaluations.evaluators.trajectory_correctness import agent_trajectory_correctness
from evaluations.evaluators.retrieval_relevance import retrieval_relevance
from evaluations.evaluators.judge_node_evaluator import judge_node_evaluator


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


# Evaluates the search node's tool ARGUMENTS — for one user query, does the node pick the
# right tool and fill KeywordFilterSearch / SemanticFilterSearch correctly? Runs the node in
# isolation (no Typesense, no embeddings, no loop), so a failure can only be an argument fault.
async def run_search_node_args_evaluation():
    client = get_langsmith_client()
    return await client.aevaluate(
        run_search_node_args,
        data=search_node_args_dataset_name,
        evaluators=[search_node_args_correctness],
        experiment_prefix="experiment-halal-one-search-node-args 2.0",
        max_concurrency=4,
    )


# Evaluates KeywordFilterSearch argument extraction in depth — name/brand splitting, filter
# normalization, verbatim identifiers, over- and under-extraction. Includes negative-routing rows
# (queries that must NOT go to keyword) so the score can't be gamed by always picking one tool.
# async def run_keyword_search_evaluation():
#     client = get_langsmith_client()
#     return await client.aevaluate(
#         run_search_node_args,
#         data=keyword_search_dataset_name,
#         evaluators=[search_node_args_correctness],
#         experiment_prefix="experiment-halal-one-keyword-search 1.0",
#         max_concurrency=4,
#     )


# # Evaluates SemanticFilterSearch argument extraction — intent capture, lifting stated filters out
# # of the vector text, stripping conversational noise, and not inventing constraints. Also carries
# # negative-routing rows (named product/brand/identifier) that must go to keyword instead.
# async def run_semantic_search_evaluation():
#     client = get_langsmith_client()
#     return await client.aevaluate(
#         run_search_node_args,
#         data=semantic_search_dataset_name,
#         evaluators=[search_node_args_correctness],
#         experiment_prefix="experiment-halal-one-semantic-search 1.0",
#         max_concurrency=4,
#     )


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


# Uncomment exactly one.
# asyncio.run(run_classification_evaluation())
# asyncio.run(run_trajectory_evaluation())
# asyncio.run(run_retrieval_relevance_evaluation())
# asyncio.run(run_judge_node_evaluation())
asyncio.run(run_search_node_args_evaluation())
# asyncio.run(run_semantic_search_evaluation())
# asyncio.run(run_keyword_search_evaluation())