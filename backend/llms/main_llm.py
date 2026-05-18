import os
from dotenv import load_dotenv
from prompts.central_prompt import SYSTEM_INSTRUCTIONS
from langchain_groq import ChatGroq
from langchain.messages import SystemMessage, HumanMessage
from models.agent_output import OutputSchema
load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
llm = ChatGroq(
    name = "Halalify_llm",
    model="llama-3.1-8b-instant",
    api_key = GROQ_API_KEY,
    temperature=0
)


def invoke_llm(query: str):
    if not query:
        raise ValueError("No query provided")
    
    messages = [
        SystemMessage(SYSTEM_INSTRUCTIONS),
        HumanMessage(query)
    ]
    halalify_llm = llm.with_structured_output(OutputSchema, method="json_mode")
    response = halalify_llm.invoke(messages)
    
    return response


# exhaustive testing
# while True:
#     query = input("Enter your query here: ")
#     if query == 'exit':
#         break
#     response = invoke_llm(query)
#     print(response)