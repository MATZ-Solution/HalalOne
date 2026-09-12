import json
import os

from dotenv import load_dotenv
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

load_dotenv(override=True)


class TaskCompletionGrade(BaseModel):
    """Judge whether the AI's response to the FINAL human request was fully completed."""
    reasoning: str = Field(..., description="State what the final human request asked for (note every part, if multi-part), whether the AI's response addressed each part, and why.")
    task_completed: bool = Field(..., description="TRUE if the AI's response to the final request was fully completed. FALSE if it was missed, incomplete, fabricated a detail, or would require a follow-up.")


grader_instructions = """You are an expert conversation evaluator. You will be shown the PRIOR CONTEXT of a conversation between a human user and an AI agent — already resolved, not to be graded — followed by the FINAL EXCHANGE: the human's last request and the AI's response to it.

Your task is to judge ONLY the final exchange: did the AI's response fully complete the human's final request?

<Rubric>
A fully completed final request:
- The AI's response addresses every part of the final request (a multi-part question needs every part answered)
- The response correctly uses the prior context where the request depends on it (e.g. recalling a product, name, certifier, or detail established earlier)
- Nothing in the response would require the human to re-ask, restate, or correct it

An incomplete or failed final request:
- The response misses part of the request, or answers a different question than what was asked
- The response fabricates a detail (e.g. a name, certifier, or fact) instead of correctly recalling it from the prior context or honestly saying it isn't known
- The response is empty or a generic non-answer
</Rubric>

<Instructions>
1. Identify exactly what the final human request is asking for, noting every part if it has more than one
2. Check the AI's response against the prior context to see whether it needed to recall or use anything established earlier, and whether it did so correctly
3. Determine whether the response fully, correctly, and honestly addresses the final request
4. Return TRUE only if the final request was fully completed; FALSE otherwise
</Instructions>

Explain your reasoning in a step-by-step manner, focused entirely on the final exchange — do not grade or comment on earlier turns in the prior context.
"""

GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not GROQ_API_KEY:
    raise ValueError("GROQ API Key is missing!")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model='openai/gpt-oss-20b',
    temperature=0
)

grading_llm = llm.with_structured_output(TaskCompletionGrade, method="json_schema")


def _reply_text(content: str) -> str:
    """An AI turn's content is the agent's raw response JSON
    ({"response": ..., "matched": [...], "relevant": [...]}); the judge only needs
    the natural-language reply, not the raw product payload."""
    try:
        return json.loads(content).get("response", content)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return content


def _transcript(messages: list) -> str:
    lines = []
    for m in messages:
        if isinstance(m, HumanMessage):
            lines.append(f"Human: {m.content}")
        elif isinstance(m, AIMessage):
            lines.append(f"AI: {_reply_text(m.content)}")
    return "\n".join(lines)


async def task_completion_evaluator(outputs: dict) -> dict:
    """Scores whether the agent's response to the FINAL user turn (the probe)
    fully completed that request. The dataset's pre-authored history (everything
    before the probe) is passed to the agent as-is for context, per
    target_functions/task_completion.py, and target_functions/task_completion.py
    always appends exactly one new HumanMessage(probe) + AIMessage(real reply) at
    the end of `messages` — so those last two messages are the exchange being
    measured; everything earlier is resolved background context, not something to
    re-grade."""
    messages = outputs.get("messages", [])
    if len(messages) < 2:
        return {"key": "taskCompletion", "score": False, "comment": "No conversation to grade."}

    *context_messages, final_human, final_ai = messages
    if not isinstance(final_human, HumanMessage) or not isinstance(final_ai, AIMessage):
        return {
            "key": "taskCompletion",
            "score": None,
            "comment": "Malformed transcript: expected the final two messages to be the probe and its reply.",
        }

    context_transcript = _transcript(context_messages) if context_messages else "(no prior context)"
    final_exchange = f"Human: {final_human.content}\nAI: {_reply_text(final_ai.content)}"

    try:
        grade: TaskCompletionGrade = await grading_llm.ainvoke([
            SystemMessage(grader_instructions),
            HumanMessage(
                f"<prior_context>\n{context_transcript}\n</prior_context>\n\n"
                f"<final_exchange_to_grade>\n{final_exchange}\n</final_exchange_to_grade>"
            ),
        ])
    except Exception as e:
        return {"key": "taskCompletion", "score": None, "comment": f"grading error: {e}"}

    return {"key": "taskCompletion", "score": grade.task_completed, "comment": grade.reasoning}