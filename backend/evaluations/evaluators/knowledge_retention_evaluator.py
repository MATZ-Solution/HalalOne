from evaluations.evaluators.task_completion_evaluator import _transcript, llm
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class KnowledgeRetentionGrade(BaseModel):
    """Judge whether the agent correctly retained and applied facts introduced earlier in the conversation."""
    reasoning: str = Field(..., description="Identify each fact, name, or detail the human introduced and say whether the agent retained and applied it correctly in later turns.")
    knowledge_retained: bool = Field(..., description="TRUE if the agent consistently retained and applied factual information. FALSE if it contradicted, forgot, or ignored previously established facts.")


grader_instructions = """You are an expert conversation evaluator. You will be shown a full conversation between a human user and an AI agent.
Your task is to assess whether the agent correctly retained and applied factual information introduced earlier in the conversation.

<Rubric>
Good knowledge retention may include:
- The agent correctly references facts, names, or details provided earlier in the conversation
- The agent's later responses are consistent with information established in prior turns
- The agent does not contradict or forget context that was clearly provided

Poor knowledge retention may include:
- The agent contradicts a fact it was given earlier
- The agent asks for information it has already been given
- The agent ignores or forgets context that is relevant to a later turn
- The agent's responses are inconsistent with previously established facts
</Rubric>

<Instructions>
For each conversation:
1. Identify the key facts, names, or details introduced by the human throughout the conversation
2. For each piece of introduced information, assess whether the agent retained and applied it correctly in later turns
3. Flag any contradictions, omissions, or ignored context
4. Return TRUE if the agent consistently retained and applied factual information, FALSE if it contradicted, forgot, or ignored previously established facts
</Instructions>

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct.
"""

grading_llm = llm.with_structured_output(KnowledgeRetentionGrade, method="json_schema")


async def knowledge_retention_evaluator(outputs: dict) -> dict:
    """Scores whether the agent stayed consistent with facts the human established
    earlier in the conversation, rather than contradicting, forgetting, or ignoring
    them in a later turn."""
    messages = outputs.get("messages", [])
    if not messages:
        return {"key": "knowledgeRetention", "score": False, "comment": "No conversation to grade."}

    transcript = _transcript(messages)
    try:
        grade: KnowledgeRetentionGrade = await grading_llm.ainvoke([
            SystemMessage(grader_instructions),
            HumanMessage(f"<conversation>\n{transcript}\n</conversation>"),
        ])
    except Exception as e:
        return {"key": "knowledgeRetention", "score": None, "comment": f"grading error: {e}"}

    return {"key": "knowledgeRetention", "score": grade.knowledge_retained, "comment": grade.reasoning}
