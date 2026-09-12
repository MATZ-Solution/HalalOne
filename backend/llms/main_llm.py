import os

from config.timeouts import LLM_TIMEOUT_S
from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from log.logger import log
from models.agent_output import OutputSchema
from prompts.central_prompt import SYSTEM_INSTRUCTIONS

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
llm = ChatGroq(
    name = "Halalify_llm",
    model="llama-3.1-8b-instant",
    api_key = GROQ_API_KEY,
    temperature=0,
    timeout=LLM_TIMEOUT_S,
)


def invoke_llm(query: str):
    if not query:
        raise ValueError("No query provided")

    messages = [
        SystemMessage(SYSTEM_INSTRUCTIONS),
        HumanMessage(query)
    ]
    halalify_llm = llm.with_structured_output(OutputSchema, method="json_mode")
    try:
        return halalify_llm.invoke(messages)
    except Exception as e:
        # search_products.search_products() already treats a falsy return as
        # "no results" (if not response: return []), so returning None here
        # degrades gracefully rather than crashing the caller.
        log.error("invoke_llm.failed", error=str(e), error_type=type(e).__name__)
        return None


# exhaustive testing
# while True:
#     query = input("Enter your query here: ")
#     if query == 'exit':
#         break
#     response = invoke_llm(query)
#     print(response)