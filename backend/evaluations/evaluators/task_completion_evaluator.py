import json
import os

from dotenv import load_dotenv
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

load_dotenv(override=True)


class TaskCompletionGrade(BaseModel):
    """Judge whether every user request in the conversation was fully completed."""
    reasoning: str = Field(..., description="List each human request in order and say whether it was fully completed.")
    task_completed: bool = Field(..., description="TRUE if every request was fully completed. FALSE if any request was missed, incomplete, or required a follow-up.")


grader_instructions = """You are an expert conversation evaluator. You will be shown a full conversation between a human user and an AI agent.
Your task is to track every request made by the human and determine whether each one was fully completed by the agent.

<Rubric>
Fully completed requests may include:
- The agent addressed all parts of the request in its response
- The human did not re-ask, restate, or follow up on the same request
- The human explicitly confirms the response was sufficient

Incomplete or failed requests may include:
- The agent partially addressed or missed part of the request
- The human had to re-ask or restate the same request
- The human had to correct or clarify because the AI misunderstood
- The human asked the AI to redo, fix, or finish something from a prior response
</Rubric>

<Instructions>
For each conversation:
1. List every request made by the human throughout the conversation
2. For each request, determine whether the AI fully completed it
3. Check whether the human re-asked or followed up on any prior request
4. Return TRUE if all requests were fully completed, FALSE if any request was missed, incomplete, or required a follow-up
</Instructions>

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct.
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
    """Scores whether the agent fully completed every request across the whole
    conversation, grading the transcript holistically rather than turn-by-turn."""
    messages = outputs.get("messages", [])
    if not messages:
        return {"key": "taskCompletion", "score": False, "comment": "No conversation to grade."}

    transcript = _transcript(messages)
    try:
        grade: TaskCompletionGrade = await grading_llm.ainvoke([
            SystemMessage(grader_instructions),
            HumanMessage(f"<conversation>\n{transcript}\n</conversation>"),
        ])
    except Exception as e:  
        return {"key": "taskCompletion", "score": None, "comment": f"grading error: {e}"}

    return {"key": "taskCompletion", "score": grade.task_completed, "comment": grade.reasoning}
