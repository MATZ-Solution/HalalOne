import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from langchain.messages import HumanMessage, SystemMessage
from agents.langgraph_agent.utils.utils import KEYWORD, SEMANTIC, FILTER_FIELDS

load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ API Key is missing!")


class Grade(BaseModel):
    reasoning: str = Field(..., description="Step by step reasoning for the decision.")
    is_correct: bool = Field(..., description="True if the produced value is acceptable, otherwise False.")


evaluator_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="openai/gpt-oss-20b",
    temperature=0,
).with_structured_output(Grade, method="json_schema")


KEYWORD_GRADER_PROMPT = """You are grading how a model filled the keyword arguments of a product search tool.

You are given the user's question, the reference (expected) keyword arguments, and the arguments the model actually produced.

Fields:
- norm_name: the product or ingredient name, lowercase, with the brand removed
- companies: brand or manufacturer names, one per list item

Mark is_correct = true when ALL of the following hold:
1. Every value the model produced is grounded in the user's question. Casing, punctuation, word order and minor typo corrections are acceptable.
2. The model did not add information that is absent from the question. Expanding a code into its chemical name, adding a manufacturer the user never named, or translating a product name into a different language are all failures.
3. Values are in the right field. A brand belongs in companies, a product name belongs in norm_name. A brand additionally left inside norm_name is acceptable; a product name placed in companies is not.
4. Nothing the user stated as a product or brand was silently dropped.

Mark is_correct = false otherwise. The reference is a guide, not a string to match character by character.

Explain your reasoning step by step, then give the verdict."""


SEMANTIC_GRADER_PROMPT = """You are grading the semantic_query a model produced for a vector product search.

You are given the user's question, a reference phrasing, and the query the model actually produced.

The reference is one acceptable phrasing, not a target to match. Be lenient about wording and strict about meaning.

Mark is_correct = true when ALL of the following hold:
1. The produced query captures the user's actual need. Paraphrase, synonyms, dropped filler words, different word order, singular vs plural and a shorter or longer phrasing are all fine as long as a person searching with it would look for the same thing.
2. It contains no constraint the user did not express.
3. It is a usable search phrase, not an empty string, a single stop word, or a restatement of the whole conversation.

Mark is_correct = false only when the meaning genuinely differs from what the user asked for, a constraint the user stated has been lost, or a constraint they never stated has been added.

Explain your reasoning step by step, then give the verdict."""


def _clean(d):
    """Drop keys whose value is null or empty. A null filter never reaches the database."""
    if not d:
        return {}
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


def _exact(actual, expected):
    to_list = lambda x: [str(i) for i in x] if isinstance(x, list) else ([] if x is None else [str(x)])
    if isinstance(actual, list) or isinstance(expected, list):
        return sorted(to_list(actual)) == sorted(to_list(expected))
    return str(actual) == str(expected)


def _allowed_tools(reference):
    expected = reference.get("expected_tool")
    return expected if isinstance(expected, list) else [expected]


def _searchable_text(outputs):
    return json.dumps(outputs.get("args") or {}, ensure_ascii=False) + "\n" + (outputs.get("response") or "")


def _score(key, ok, comment=""):
    return {"key": key, "score": int(bool(ok)), "comment": comment}


def _grade_tool_selection(outputs, reference):
    allowed = _allowed_tools(reference)
    actual = outputs.get("tool_name")
    if actual not in allowed:
        names = ", ".join(t or "DIRECT" for t in allowed)
        return _score("tool_selection", False, f"expected one of [{names}], got {actual or 'DIRECT'}")

    limit = reference.get("max_tool_calls")
    made = len(outputs.get("tool_calls") or [])
    if limit is not None and made > limit:
        return _score("tool_selection", False, f"made {made} tool calls, at most {limit} allowed")

    return _score("tool_selection", True, f"chose {actual or 'DIRECT'}")


def _grade_filter_exactness(outputs, reference):
    expected = _clean(reference.get("filter_args"))
    actual = _clean((outputs.get("args") or {}).get("filter_args"))

    if not expected:
        if not actual:
            return _score("filter_exactness", True, "no filters expected, none set")
        return _score("filter_exactness", True, f"no filters expected; set {sorted(actual)} (see no_over_extraction)")

    missing = [k for k in expected if k not in actual]
    wrong = [k for k in expected if k in actual and not _exact(actual[k], expected[k])]

    if not missing and not wrong:
        return _score("filter_exactness", True, f"all {len(expected)} expected filter(s) matched exactly")

    problems = [f"{k}: missing (expected {expected[k]!r})" for k in missing]
    problems += [f"{k}: got {actual[k]!r}, expected {expected[k]!r}" for k in wrong]
    return _score("filter_exactness", False, "; ".join(problems))


def _grade_no_over_extraction(outputs, reference):
    actual = _clean((outputs.get("args") or {}).get("filter_args"))
    forbidden_keys = reference.get("forbidden_filter_keys") or []
    forbidden_terms = reference.get("forbidden_terms") or []

    problems = [f"{k} must not be set, got {actual[k]!r}" for k in forbidden_keys if k in actual]

    text = _searchable_text(outputs)
    problems += [f"forbidden term {t!r} appeared in the output" for t in forbidden_terms if t in text]

    expected_keyword = reference.get("keyword_args")
    produced_keyword = _clean((outputs.get("args") or {}).get("keyword_args"))
    if expected_keyword is None and "keyword_args" in reference and produced_keyword:
        problems.append(f"keyword_args should be null, got {produced_keyword!r}")

    unknown = [k for k in actual if k not in FILTER_FIELDS]
    problems += [f"{k} is not a valid filter field" for k in unknown]

    if problems:
        return _score("no_over_extraction", False, "; ".join(problems))
    return _score("no_over_extraction", True, "no forbidden fields or terms present")


async def _grade_keyword_args(inputs, outputs, reference, errors):
    expected = reference.get("keyword_args")
    actual = (outputs.get("args") or {}).get("keyword_args")

    if outputs.get("tool_name") != KEYWORD or not expected:
        return None
    if not _clean(actual):
        return _score("keyword_args_correctness", False, f"expected {expected!r}, got nothing")

    message = (
        f"USER QUESTION: {inputs.get('question', '')}\n"
        f"REFERENCE keyword_args: {json.dumps(_clean(expected), ensure_ascii=False)}\n"
        f"PRODUCED keyword_args: {json.dumps(_clean(actual), ensure_ascii=False)}"
    )
    try:
        grade: Grade = await evaluator_llm.ainvoke(
            [SystemMessage(KEYWORD_GRADER_PROMPT), HumanMessage(message)]
        )
    except Exception as e:
        errors.append(f"keyword_args_correctness: {type(e).__name__}: {e}")
        return None
    return _score("keyword_args_correctness", grade.is_correct, grade.reasoning)


async def _grade_semantic_query(inputs, outputs, reference, errors):
    if outputs.get("tool_name") != SEMANTIC:
        return None

    actual = ((outputs.get("args") or {}).get("semantic_query") or "").strip()
    if not actual:
        return _score("semantic_query_quality", False, "semantic_query is empty")

    reference_query = reference.get("semantic_query")
    if not reference_query:
        return _score("semantic_query_quality", True, f"no reference phrasing; produced {actual!r}")

    message = (
        f"USER QUESTION: {inputs.get('question', '')}\n"
        f"REFERENCE semantic_query: {reference_query}\n"
        f"PRODUCED semantic_query: {actual}"
    )
    try:
        grade: Grade = await evaluator_llm.ainvoke(
            [SystemMessage(SEMANTIC_GRADER_PROMPT), HumanMessage(message)]
        )
    except Exception as e:
        errors.append(f"semantic_query_quality: {type(e).__name__}: {e}")
        return None
    return _score("semantic_query_quality", grade.is_correct, grade.reasoning)


async def search_node_args_correctness(inputs: dict, outputs: dict, reference_outputs: dict = None) -> list[dict]:
    """Grades what the search node passed into KeywordFilterSearch / SemanticFilterSearch."""
    reference = reference_outputs or {}
    errors: list[str] = []

    scores = [
        _grade_tool_selection(outputs, reference),
        _grade_filter_exactness(outputs, reference),
        _grade_no_over_extraction(outputs, reference),
    ]

    for grade in (
        await _grade_keyword_args(inputs, outputs, reference, errors),
        await _grade_semantic_query(inputs, outputs, reference, errors),
    ):
        if grade is not None:
            scores.append(grade)

    failed = [s["key"] for s in scores if not s["score"]]
    scores.append(_score("all_checks_passed", not failed, "failed: " + ", ".join(failed) if failed else "all checks passed"))
    scores.append({"key": "grading_errors", "score": len(errors), "comment": "\n".join(errors)})

    return scores
