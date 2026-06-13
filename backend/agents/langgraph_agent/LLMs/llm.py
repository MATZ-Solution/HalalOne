import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')


if not GROQ_API_KEY:
    raise ValueError("Invalid GROQ API KEY")


extracter_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "llama-3.1-8b-instant",    
    temperature = 0,
    max_tokens = 500
)

final_extracter_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "openai/gpt-oss-20b",
    reasoning_effort = "medium",
    temperature = 0,
)

standard_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "openai/gpt-oss-120b",
    reasoning_effort = "medium",
    temperature = 0,
)



# def stream_reasoning_and_response(prompt: str):
#     # Stream the response from the LLM
#     for chunk in final_extracter_llm.stream(prompt):
#         # Iterate over content_blocks for normalized access
#         for block in chunk.content_blocks:
#             # Print reasoning content
#             if block.get("type") == "reasoning":
#                 print(f"\n[Thinking]: {block.get('reasoning')}", end="", flush=True)
            
#             # Print standard text content
#             if block.get("type") == "text":
#                 print(f"\n [RESPONSE]: {block.get('text')}", end="", flush=True)

# # Run the streamer
# stream_reasoning_and_response("Hello dear")