import os
import re
import json
import base64
import asyncio
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_fireworks import ChatFireworks
from langchain.messages import HumanMessage, SystemMessage
from log.logger import log

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIREWORKS_API_KEY = os.getenv("FIREWORKS_AI_API_KEY")

vision_llm = ChatGroq(
    model = "qwen/qwen3.6-27b",
    api_key = GROQ_API_KEY,
    temperature = 0,               
    max_tokens=4096,               
    reasoning_effort="none",       
    model_kwargs={"response_format": {"type": "json_object"}}
)

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

## INSTRUCTIONS ##
Return only JSON with the following keys:

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

## OUTPUT EXAMPLES ##
{{
"norm_name": "Halal Certified Confectionery Products",
"companies": ["Nestlé", "Mars Wrigley", "Haribo", "Perfetti Van Melle", "Lotte Confectionery"],
"cert_bodies": ["JAKIM (Malaysia)", "MUI (Indonesia)", "HFCE (USA)", "Islamic Food and Nutrition Council of America (IFANCA)", "Halal Monitoring Authority (HMA - Canada)"],
"typical_uses": ["Daily snacks", "Gift boxes", "Party treats", "Religious celebrations (Eid, Ramadan)", "Retail vending"],
"marketplace": ["Amazon", "Walmart", "Carrefour", "eBay", "Local halal grocery stores"],
"category_l1": "Food & Beverage",
"category_l2": "Confectionery & Sweets",
"halal_status": "Halal",
"sold_in": ["Malaysia", "Indonesia", "Saudi Arabia", "United Arab Emirates", "United States", "Canada", "United Kingdom"],
"cert_numbers": ["JAKIM-2025-0789", "MUI-IND-4456", "IFANCA-USA-1234", "HMA-CAN-9876"],
"health_info": ["Gluten-free options available", "No artificial colors in select lines", "Contains sugar and glucose syrup", "May contain traces of nuts", "Gelatin-free (plant-based pectin used)"],
"fda_numbers": ["FDA-2025-3321", "FDA-2025-9987"],
"barcodes": ["8901234567890", "8901234567891", "8901234567892"]
}}

{{
"norm_name": "Halal Certified Poultry Meat",
"companies": ["Tyson Foods", "Cargill", "BRF", "Al-Watania Poultry", "Sadia"],
"cert_bodies": ["Halal Food Authority (HFA - UK)", "Islamic Services of America (ISA)", "JAKIM", "MUI", "European Halal Development Institute (EHDI)"],
"typical_uses": ["Fresh meat retail", "Processed chicken nuggets", "Ready-to-cook marinades", "Food service catering", "School meal programs"],
"marketplace": ["Sysco", "Costco", "Kroger", "Alibaba", "Local butchers"],
"category_l1": "Food & Beverage",
"category_l2": "Meat & Poultry",
"halal_status": "Halal",
"sold_in": ["Saudi Arabia", "UAE", "USA", "UK", "France", "Turkey", "Australia"],
"cert_numbers": ["HFA-UK-4452", "ISA-USA-7721", "JAKIM-P-6543", "MUI-M-3322"],
"health_info": ["High protein", "Low fat (skinless options)", "No added hormones", "Antibiotic-free", "Rich in B vitamins"],
"fda_numbers": ["FDA-P-2025-112", "FDA-P-2025-113"],
"barcodes": ["6921168509256", "6921168509263", "6921168509270"]
}}

"""

# structured_llm = vision_llm.with_structured_output(ProductInfo, method="json_schema")

def _parse_json(text: str) -> Optional[dict]:
    """Direct parse first; fall back to extracting the first {...} block."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


async def invoke_llm_with_image(image_url: str) -> Dict[str, Any]:
    if not image_url:
        return {"error": "No valid image found"}
    messages = [SystemMessage(SYSTEM_INSTRUCTIONS), HumanMessage(content=[{
        'type': 'image_url',
        'image_url': {
            'url': image_url
        }
    }])]
    
    try:
        # Native async — cleaner than asyncio.to_thread(vision_llm.invoke, ...)
        response = await vision_llm.ainvoke(messages)
        print(response)
    except Exception as exc:
        log.exception("vision_llm.invoke.failed", error=str(exc), error_type=type(exc).__name__)
        return {"error": f"LLM request failed: {exc}"}

    content = (response.content or "").strip()
    if not content:
        return {"error": "Empty response from LLM"}

    data = _parse_json(content)
    if data is None:
        log.error("vision_llm.parse.failed", content_preview=content[:500])
        return {"error": "No valid JSON in LLM response"}

    try:
        return ProductInfo(**data).model_dump()
    except ValidationError as exc:
        log.warning("vision_llm.validation.failed", error=str(exc), error_type=type(exc).__name__)
        return data  # JSON was valid, just off-schema — return raw rather than drop it