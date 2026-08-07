import os
import warnings
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_cerebras import ChatCerebras
# from langchain_aws import ChatBedrockConverse

load_dotenv()

# Cosmetic-only: with_structured_output(..., method="json_schema") on ChatCerebras
# runs the OpenAI parse path, which model_dumps the SDK's ParsedChatCompletion
# whose `parsed` field is generically typed None but holds our Pydantic object.
# The parse itself succeeds; only silence this exact serializer warning.
warnings.filterwarnings(
    "ignore",
    message=r"Pydantic serializer warnings:[\s\S]*field_name='parsed'",
)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY')
# AWS_BEARER_TOKEN_BEDROCK = os.getenv('AWS_BEARER_TOKEN_BEDROCK')


if not GROQ_API_KEY:
    raise ValueError("Invalid GROQ API KEY")

if not CEREBRAS_API_KEY:
    raise ValueError("Invalid CEREBRAS API KEY")

# if not AWS_BEARER_TOKEN_BEDROCK:
#     raise ValueError("Invalid AWS API KEY")



# extracter_llm = ChatBedrockConverse(
#     api_key=AWS_BEARER_TOKEN_BEDROCK,
#     region_name = "us-east-1",
#     model_id="openai.gpt-oss-120b-1:0",
#     temperature = 0,
#     max_tokens=300
# )

extracter_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "llama-3.1-8b-instant",    
    temperature = 0,
    max_tokens = 300
)

final_extracter_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "openai/gpt-oss-120b",
    temperature = 0,
)


standard_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "openai/gpt-oss-120b",
    temperature = 0,
)

# use a smaller llm for summarizing conversation histories
summarizer_llm = ChatGroq(
    api_key = GROQ_API_KEY,
    model = "llama-3.3-70b-versatile",
    temperature = 0
)

# final_extracter_llm = ChatCerebras(
#     api_key=CEREBRAS_API_KEY,
#     model="zai-glm-4.7",
#     temperature=0,
# )

# standard_llm = ChatCerebras(
#     api_key=CEREBRAS_API_KEY,
#     model="zai-glm-4.7",
#     temperature=0,
# )


# final_extracter_llm = ChatBedrockConverse(
#     api_key=AWS_BEARER_TOKEN_BEDROCK,
#     region_name = "us-east-1",
#     model_id="anthropic.claude-opus-4-1-20250805-v1:0",
#     temperature = 0,
# )

# standard_llm = ChatBedrockConverse(
#     api_key=AWS_BEARER_TOKEN_BEDROCK,
#     region_name = "us-east-1",
#     model_id="anthropic.claude-opus-4-1-20250805-v1:0",
#     temperature = 0,
# )

# import boto3  

# client = boto3.client("bedrock-runtime", region_name="us-east-1")  

# response = client.converse( 
#     modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0", 
#     messages=[ 
#         { 
#             "role": "user", 
#             "content": [{"text": "Write a one-sentence bedtime story about a unicorn."}]
#         } 
#     ] 
# )  

# print(response["output"]["message"]["content"][0]["text"])