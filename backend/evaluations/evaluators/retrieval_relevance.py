import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from agents.langgraph_agent.utils.utils import SEMANTIC


load_dotenv(override=True)


class ProductScore(BaseModel):
    """A single product's relevance to the user's request."""
    canonical_id: str = Field(..., description="The product's canonical_id, copied verbatim from its `id:` line.")
    confidence: float = Field(..., description="Relevance confidence from 0.0 (unrelated) to 1.0 (fully matches the request).")

class RelevanceGrade(BaseModel):
    """Judge how relevant each semantically-retrieved product is to the user's request."""
    reasoning: str = Field(..., description="Step-by-step reasoning for each product's relevance confidence.")
    scores: list[ProductScore] = Field(default_factory=list, description="A relevance confidence for EVERY returned product.")

grader_instructions = """You are a retrieval-relevance judge for a halal-product semantic search.

You are given the user's request and the products a semantic (vector) search returned. The search matches on the concatenation of each product's norm_name, companies, typical_uses and health_info, so those are the fields you see. For EVERY returned product, give a relevance confidence from 0.0 to 1.0 for how well it matches what the user asked for.

Here is the scoring criteria to follow:
1) 1.0 means the product fully satisfies the user's need or intent. Because this is semantic (not exact) search, a product may include extra attributes, brands, or details the user did not ask for — that is fine and does not lower the score, as long as it genuinely fits the request.
2) Lower the confidence for a PARTIAL match — the product covers the main need but misses a qualifier the user asked for.
   For Example. User asks: "vitamin-rich products for children" → a vitamin-rich product that does not mention children still covers the main need, so score it high but not perfect (e.g. 0.8). A vitamin product clearly meant for children scores ~1.0.
3) 0.0 means off-topic or unrelated to the user's intent (e.g. an unrelated spice or a cleaning product for a "calcium-rich snack" request).
4) Judge each product against the USER'S ORIGINAL request, not any reformulated query. Do not require exact wording; meaning is what matters.

Score EVERY product. Copy each `canonical_id` verbatim from its `id:` line — never invent, guess, or modify an id.

Explain your reasoning in a step-by-step manner, then give the scores.
"""

GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not GROQ_API_KEY:
    raise ValueError("GROQ API Key is missing!")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model='openai/gpt-oss-20b',
    temperature=0
)

relevance_llm = llm.with_structured_output(RelevanceGrade, method="json_schema")

# Semantic search embeds these fields, so the judge sees exactly what was matched on.
RELEVANCE_FIELDS = ("norm_name", "companies", "health_info", "typical_uses")


def _called_tool_names(messages: list) -> list:
    """Tool names the agent called, in order."""
    names = []
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls:
                names.append(tc["name"])
    return names


def _final_products(messages: list) -> list:
    """The products shown to the user, read from the final response JSON. That is
    always the last message (response_node / error handler both emit it and go to
    END). For a semantic-first query matched is empty, so `relevant` is the
    semantic result set. A missing / non-JSON tail means the run failed — return []."""
    if not messages:
        return []
    try:
        data = json.loads(messages[-1].content)
    except (AttributeError, TypeError, json.JSONDecodeError):
        return []
    return data.get("relevant") or []


def _block(product: dict) -> str:
    """id + the embedded fields for one candidate."""
    lines = [f"id: {product.get('canonical_id')}"]
    for field in RELEVANCE_FIELDS:
        value = product.get(field)
        if not value:
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{field}: {value}")
    return "\n".join(lines)


def _result(confidence, ratio, comment: str) -> list:
    """The two metrics this evaluator reports, so every path returns the same shape.
    relevanceConfidence = average per-product confidence; retrievalRelevance =
    fraction judged relevant (confidence >= 0.5), derived from the same scores."""
    return [
        {"key": "relevanceConfidence", "score": confidence, "comment": comment},
        {"key": "retrievalRelevance", "score": ratio, "comment": comment},
    ]


async def retrieval_relevance(inputs: dict, outputs: dict) -> list:
    """Score how relevant the semantically-retrieved products are to the user's
    query. Only fires when the FIRST tool call was a semantic search; an empty
    result set counts as a pass."""

    messages = outputs.get("messages", [])
    names = _called_tool_names(messages)

    # Gate: only judge semantic-first trajectories (relevant == semantic results).
    if not names or names[0] != SEMANTIC:
        return _result(None, None, "Not a semantic-first trajectory — retrieval relevance not applicable.")

    products = _final_products(messages)
    # No products returned is a pass (semantic search can legitimately find nothing).
    if not products:
        return _result(1.0, 1.0, "No products returned by the semantic search — pass.")

    candidate_ids = {p.get("canonical_id") for p in products if p.get("canonical_id")}
    blob = "\n\n".join(_block(p) for p in products)
    user_message = f"""USER REQUEST: {inputs.get('question', '')}
    
    SEMANTIC SEARCH RESULTS:
    {blob}
    """
    try:
        grade: RelevanceGrade = await relevance_llm.ainvoke([SystemMessage(grader_instructions), HumanMessage(user_message)])
    except Exception as e:
        return _result(None, None, f"grading error: {e}")

    # Map each judged (valid) id to a clamped confidence. A product the judge
    # omitted counts as 0.0, so leaving hard ones out can't inflate the average.
    by_id = {s.canonical_id: max(0.0, min(1.0, s.confidence)) for s in grade.scores if s.canonical_id in candidate_ids}
    confidences = [by_id.get(p.get("canonical_id"), 0.0) for p in products]

    avg_confidence = round(sum(confidences) / len(products), 2)
    ratio = round(sum(1 for c in confidences if c >= 0.5) / len(products), 2)
    return _result(avg_confidence, ratio, grade.reasoning)
