import os
import base64
import asyncio
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_fireworks import ChatFireworks
from langchain.messages import HumanMessage, SystemMessage

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIREWORKS_API_KEY = os.getenv("FIREWORKS_AI_API_KEY")



vision_llm = ChatGroq(
    model = "meta-llama/llama-4-scout-17b-16e-instruct",
    api_key = GROQ_API_KEY,
    temperature = 0,
    # stop_sequences=["}"],
    max_tokens=600
)

# vision_llm = ChatFireworks(
#     model = "accounts/fireworks/models/kimi-k2p5",
#     api_key = FIREWORKS_API_KEY,
#     temperature = 0,
#     stop_sequences=["}"],
#     max_tokens=600
# )

class ProductInfo(BaseModel):
    norm_name: str
    companies: List[str]
    cert_bodies: List[str]
    typical_uses: List[str]
    marketplace: List[str]
    category_l1: str
    category_l2: str
    halal_status: str
    sold_in: List[str]
    cert_numbers: List[str]
    health_info: List[str]
    fda_numbers: List[str]
    barcodes: List[str]

SYSTEM_INSTRUCTIONS = """
You are a specialist assistant for extracting key information from a product image.
Output **ONLY VALID** json. **NOTHING ELSE**
**NEVER** assume any field's value if the field is not present in the image. 

For Example: 
Image Data contains: product name: "Shan Biryani", companies: "National Foods Limited".

Output:
{{
    product_name: "Shan Biryani",
    companies: ["National Foods Limited"]
}}
Don't assume category_l1: Food or cert_bodies: ["HFCA"]. Leave all other unextracted fields as None.

##INSTRUCTIONS##
Return only JSON with keys:

1. norm_name (string)
2. companies (string[])
3. cert_bodies (string[])
4. typical_uses (string[])
5. marketplace (string[])
6. category_l1 (string)
7. category_l2 (string)
8. halal_status (string)
9. sold_in (string[])
10. cert_numbers (string[])
11. health_info (string[])
12. fda_numbers (string[])
13. barcodes (string[])
"""
messages = [SystemMessage(SYSTEM_INSTRUCTIONS)]


# structured_llm = vision_llm.with_structured_output(ProductInfo, method="json_schema")

async def invoke_llm_with_image(image_path:str) -> str:
    if not image_path:
        return "Please provide a valid image path"
    image_url = None
    with open(image_path, "rb") as image_file:
        base_64_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    if base_64_string:
        image_url = f"data:image/jpeg;base64,{base_64_string}"
    else:
        return "No image found"
    if not image_url:
        return "No image found"
    
    messages.append(HumanMessage(content=[{
        'type': 'image_url',
        'image_url': {
            'url': image_url
        }
    }]))
    
    response = await asyncio.to_thread(
        vision_llm.invoke, messages
    )
    
    response_content = response.content
    if response_content:
        return response_content
    else:
        return "No response, try again"

response = invoke_llm_with_image(r"C:\Users\anas_\Downloads\WhatsApp Image 2025-12-22 at 3.34.56 PM.jpeg")

print(f"Pre-mature repsonse: {response} \n")
# print(f"Mature response: {response.replace('```json','')}")
