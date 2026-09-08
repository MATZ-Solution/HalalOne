import os
import asyncio
from log.logger import log
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ValidationError
from langchain_core.exceptions import OutputParserException
from langchain.messages import HumanMessage, SystemMessage
from langchain_fireworks import ChatFireworks

load_dotenv()

FIREWORKS_API_KEY = os.getenv("FIREWORKS_AI_API_KEY")

# Fallback VLMs, tried in this order: on an infra failure (or a model that can't
# produce valid output) we move to the next one.
FALLBACK_VLMS = {
    "primary_vlm": "accounts/fireworks/models/deepseek-v4-flash-vision-exp",
    "seconday_vlm": "accounts/fireworks/models/muse-glimmer-30b",
    "tertiary_vlm": "accounts/fireworks/models/glm-5p3-flash",
}
_VLM_ORDER = ["primary_vlm", "seconday_vlm", "tertiary_vlm"]

# Each schema-fix retry RE-SENDS the image (image tokens), so keep this low. A model
# that still can't produce valid output after this many tries hands off to the next.
FEEDBACK_RETRIES = 1
# Per-attempt wall-clock cap (seconds), so one hanging provider can't stall a call.
VLM_TIMEOUT = int(os.getenv("VLM_TIMEOUT", "15"))
# Overall deadline (seconds) across ALL models + retries. Keep it <= the frontend's
# request timeout so the user gets a result or a clean error within budget — never a
# false "timed out" while the server keeps working on (and then discards) a late 200.
EXTRACT_DEADLINE = int(os.getenv("VLM_EXTRACT_DEADLINE", "25"))


class ProductInfo(BaseModel):
    norm_name: Optional[str] = None
    companies: Optional[List[str]] = None
    cert_bodies: Optional[List[str]] = None
    marketplace: Optional[List[str]] = None
    category_l1: Optional[str] = None
    category_l2: Optional[str] = None
    halal_status: Optional[str] = None
    sold_in: Optional[List[str]] = None
    cert_numbers: Optional[List[str]] = None
    fda_numbers: Optional[List[str]] = None
    barcodes: Optional[List[str]] = None


def _build_vlm(model_id: str):
    return ChatFireworks(
        model=model_id,
        api_key=FIREWORKS_API_KEY,
        temperature=0,
        max_tokens=4096,
    ).with_structured_output(schema=ProductInfo, method="json_schema")


# Built once and reused. Building a fresh ChatFireworks per call opened a new aiohttp
# session each time and leaked it ("Unclosed client session"); caching keeps one
# session per model for the process lifetime and skips rebuild overhead.
_VLMS = {pref: _build_vlm(model_id) for pref, model_id in FALLBACK_VLMS.items()}


def select_vlm(model_preference: str):
    """Return the cached structured VLM for a preference key
    ("primary_vlm" | "seconday_vlm" | "tertiary_vlm")."""
    if not isinstance(model_preference, str):
        raise TypeError("Model preference must be a string")
    return _VLMS[model_preference]


SYSTEM_INSTRUCTIONS = """
You are a specialist assistant for extracting key information from a product image.
**NEVER** assume any field's value if it is not present in the image.

For example, if the image shows product name "Shan Biryani" by "National Foods Limited":
{
    "norm_name": "Shan Biryani",
    "companies": ["National Foods Limited"]
}
Don't assume category_l1, cert_bodies, or any other field. STRICTLY leave every field
that is absent or unreadable as null.

## FIELDS ##
norm_name (string), companies (string[]), cert_bodies (string[]), marketplace (string[]),
category_l1 (string), category_l2 (string), halal_status (string), sold_in (string[]),
cert_numbers (string[]), fda_numbers (string[]), barcodes (string[]).

## OUTPUT EXAMPLES ##
{
"norm_name": "KitKat Wafer",
"companies": ["Nestlé"],
"cert_bodies": ["JAKIM"],
"marketplace": ["Amazon"],
"category_l1": "Food",
"category_l2": "Snacks & Confectionery",
"halal_status": "Halal",
"sold_in": ["Malaysia", "UAE"],
"cert_numbers": ["JAKIM-2025-0789"],
"fda_numbers": null,
"barcodes": ["8901234567890"]
}

{
"norm_name": "Chicken Nuggets",
"companies": ["Al-Watania Poultry"],
"cert_bodies": ["JAKIM"],
"marketplace": null,
"category_l1": "Food",
"category_l2": "Meat & Poultry",
"halal_status": "Halal",
"sold_in": ["Saudi Arabia", "UAE"],
"cert_numbers": null,
"fda_numbers": null,
"barcodes": ["6921168509256"]
}
""".strip()


def _is_schema_error(e: Exception) -> bool:
    """The model produced output that doesn't match ProductInfo — its own fault, and
    fixable by feeding the error back and asking it to try again."""
    return isinstance(e, (OutputParserException, ValidationError))


def _is_fatal_input(e: Exception) -> bool:
    """The image itself is unusable (too large / unreadable format). Every model would
    fail the same way, so don't waste the fallback chain — bail out."""
    m = str(e).lower()
    return any(
        s in m for s in ("too large", "payload too large", "invalid image", "unsupported image")
    )


def _schema_feedback(e: Exception) -> HumanMessage:
    """Correction message fed back to the SAME model after a schema failure. The image
    is still in the prior turns, so the model can re-read it."""
    return HumanMessage(
        "Your previous reply did not match the required schema "
        f"(error: {str(e)[:300]}). Reply again with ONLY valid JSON matching the schema: "
        "fill only the fields you can actually read from the image, and leave every "
        "field that is absent or unreadable as null."
    )


async def invoke_llm_with_image(image_url: str) -> Dict[str, Any]:
    """Extract product fields from an image, trying the fallback VLMs in order.

    Per model: on a schema failure, retry the SAME model with human-message feedback
    (bounded by FEEDBACK_RETRIES); on an infra/transient error, fall back to the NEXT
    model; on a fatal image error, bail (all models would fail alike). Returns the
    extracted fields dict, or {"error": ...} once every model is exhausted.
    """
    if not image_url:
        return {"error": "No valid image found"}

    base = [
        SystemMessage(SYSTEM_INSTRUCTIONS),
        HumanMessage(content=[{"type": "image_url", "image_url": {"url": image_url}}]),
    ]

    # Overall budget across every model + retry; each attempt is capped at the smaller
    # of VLM_TIMEOUT and the time left, so the whole call always finishes within it.
    deadline = asyncio.get_running_loop().time() + EXTRACT_DEADLINE

    for pref in _VLM_ORDER:
        llm = select_vlm(pref)
        messages = list(base)
        for attempt in range(FEEDBACK_RETRIES + 1):
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                log.warning("vision_llm.deadline_exceeded", model=pref)
                return {"error": "Image analysis took too long. Please try again."}
            try:
                result: ProductInfo = await asyncio.wait_for(
                    llm.ainvoke(messages), timeout=min(VLM_TIMEOUT, remaining)
                )
                return result.model_dump()
            except Exception as exc:
                if _is_schema_error(exc):
                    # Model's fault and fixable → feed the error back, retry same model.
                    log.warning(
                        "vision_llm.schema_failed",
                        model=pref, attempt=attempt + 1,
                        error=str(exc), error_type=type(exc).__name__,
                    )
                    messages.append(_schema_feedback(exc))
                    continue
                if _is_fatal_input(exc):
                    log.error("vision_llm.fatal_input", model=pref, error=str(exc))
                    return {"error": "The image could not be processed. Please try a clearer or smaller image."}
                # Transient / infra / unknown → stop retrying this model, try the next.
                log.warning(
                    "vision_llm.model_failed",
                    model=pref, error=str(exc), error_type=type(exc).__name__,
                )
                break
        # Schema retries exhausted on this model → fall through to the next model.

    log.error("vision_llm.all_models_exhausted")
    return {"error": "Failed to extract image information"}
