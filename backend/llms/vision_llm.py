import asyncio
import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import re

from dotenv import load_dotenv
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.exceptions import OutputParserException
from langchain_fireworks import ChatFireworks
from log.logger import log
from pydantic import BaseModel, ValidationError

load_dotenv()

FIREWORKS_API_KEY = os.getenv("FIREWORKS_AI_API_KEY")

# Fallback VLMs, tried in this order: on an infra failure (or a model that can't
# produce valid output) we move to the next one.
FALLBACK_VLMS = {
    "primary_vlm": "accounts/fireworks/models/glm-5p3-flash",
    "seconday_vlm": "accounts/fireworks/models/muse-glimmer-30b",
    "tertiary_vlm": "accounts/fireworks/models/deepseek-v4-flash-vision-exp",
}
# Alias for typo tolerance
FALLBACK_VLMS["secondary_vlm"] = FALLBACK_VLMS["seconday_vlm"]

_VLM_ORDER = ["primary_vlm", "seconday_vlm", "tertiary_vlm"]

# Each schema-fix retry RE-SENDS the image (image tokens), so keep this low. A model
# that still can't produce valid output after this many tries hands off to the next.
FEEDBACK_RETRIES = 1
# Per-attempt wall-clock cap (seconds), so one hanging provider can't stall a call.
VLM_TIMEOUT = int(os.getenv("VLM_TIMEOUT", "30"))
# Overall deadline (seconds) across ALL models + retries.
EXTRACT_DEADLINE = int(os.getenv("VLM_EXTRACT_DEADLINE", "60"))


class ProductInfo(BaseModel):
    norm_name: str | None = None
    companies: list[str] | None = None
    cert_bodies: list[str] | None = None
    marketplace: list[str] | None = None
    category_l1: str | None = None
    category_l2: str | None = None
    halal_status: str | None = None
    sold_in: list[str] | None = None
    cert_numbers: list[str] | None = None
    fda_numbers: list[str] | None = None
    barcodes: list[str] | None = None


def _parse_product_info(raw_content: Any) -> ProductInfo:
    """Robustly parses VLM response into ProductInfo, safely handling markdown code fences."""
    if isinstance(raw_content, ProductInfo):
        return raw_content
    if isinstance(raw_content, dict):
        return ProductInfo(**raw_content)
    text = str(raw_content).strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        text = text[first_brace : last_brace + 1]
    data = json.loads(text)
    return ProductInfo(**data)


def _build_vlm(model_id: str):
    return ChatFireworks(
        model=model_id,
        api_key=FIREWORKS_API_KEY,
        temperature=0,
        max_tokens=4096,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


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
You are an expert specialist for extracting key product information strictly from packaging images.

## CRITICAL RULES ##
1. **VISUAL GROUNDING ONLY:** Extract ONLY text and markings that are physically printed and visible in the image.
2. **NEVER ASSUME OR GUESS:** If a field is not visibly stamped or printed on the package, you MUST set it to null.
3. **DO NOT INVENT CATEGORIES:** Do NOT set category_l1 or category_l2 to "Food", "Snacks", etc. unless that exact word is printed on the package. If absent, set to null.
4. **BARCODES:** Extract numerical barcode digits ONLY if the barcode is clearly visible. Otherwise set to null.
5. **HALAL / CERTIFICATION:** Extract halal status or certification bodies only if an official logo, seal, or text is visible. Otherwise set to null.

## FIELDS ##
norm_name (string), companies (string[]), cert_bodies (string[]), marketplace (string[]),
category_l1 (string), category_l2 (string), halal_status (string), sold_in (string[]),
cert_numbers (string[]), fda_numbers (string[]), barcodes (string[]).
""".strip()


def _load_image_data_url(rel_path: str) -> str | None:
    """Loads a local image file as a Base64 data URL."""
    backend_root = Path(__file__).resolve().parent.parent
    full_path = backend_root / rel_path
    if not full_path.exists():
        return None
    try:
        mime_type, _ = mimetypes.guess_type(str(full_path))
        mime_type = mime_type or "image/jpeg"
        with open(full_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime_type};base64,{b64}"
    except Exception:
        return None


# Curated reference examples to visually demonstrate strict extraction
_FEW_SHOT_CONFIG = [
    {
        "rel_path": "evaluations/data/images/7days_strawberry_cake_bar.jpg",
        "output": {
            "norm_name": "cake bar with strawberry filling",
            "companies": ["7DAYS"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        "rel_path": "evaluations/data/images/alyoum_chicken_drumsticks.jpg",
        "output": {
            "norm_name": "alyoum premium fresh chicken drumsticks",
            "companies": ["Alyoum", "Almarai"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": "Halal",
            "sold_in": ["Saudi Arabia"],
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": ["6281007057899"],
        },
    },
    {
        "rel_path": "evaluations/data/images/twix_salted_caramel.jpg",
        "output": {
            "norm_name": "twix salted caramel",
            "companies": ["Twix", "Mars", "Mars Egypt for Manufacturing L.L.C."],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": ["Egypt", "Morocco", "Syria", "Palestine", "Tunisia"],
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": ["6221134010312"],
        },
    },
]

# Cache few-shot image data URLs once
_CACHED_FEW_SHOTS = []
for item in _FEW_SHOT_CONFIG:
    data_url = _load_image_data_url(item["rel_path"])
    out = item.get("output") or item.get("outputs")
    if data_url and out:
        _CACHED_FEW_SHOTS.append({"image_url": data_url, "output": out})


def _build_messages(target_image_url: str) -> list[Any]:
    """Constructs prompt messages with system instructions, visual few-shot turns, and target image."""
    messages = [SystemMessage(SYSTEM_INSTRUCTIONS)]

    # Add few-shot visual turns (excluding the exact query image if evaluating on the same image)
    for fs in _CACHED_FEW_SHOTS:
        if fs["image_url"] != target_image_url:
            messages.append(
                HumanMessage(
                    content=[
                        {"type": "image_url", "image_url": {"url": fs["image_url"]}}
                    ]
                )
            )
            messages.append(AIMessage(content=json.dumps(fs["output"])))

    # Append the target image query
    messages.append(
        HumanMessage(
            content=[{"type": "image_url", "image_url": {"url": target_image_url}}]
        )
    )
    return messages


def _is_schema_error(e: Exception) -> bool:
    """The model produced output that doesn't match ProductInfo — its own fault, and
    fixable by feeding the error back and asking it to try again."""
    return isinstance(e, (OutputParserException, ValidationError, json.JSONDecodeError))


def _is_fatal_input(e: Exception) -> bool:
    """The image itself is unusable (too large / unreadable format). Every model would
    fail the same way, so don't waste the fallback chain — bail out."""
    m = str(e).lower()
    return any(
        s in m
        for s in (
            "too large",
            "payload too large",
            "invalid image",
            "unsupported image",
        )
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


async def invoke_llm_with_image(
    image_url: str,
    model_preference: str | None = None,
) -> dict[str, Any]:
    """Extract product fields from an image, trying the fallback VLMs in order (or a specific model if requested).

    If model_preference is specified ('primary_vlm', 'seconday_vlm' / 'secondary_vlm', 'tertiary_vlm'),
    only that model is evaluated with its feedback retry.
    Otherwise, iterates over the fallback order (_VLM_ORDER).

    Returns the extracted fields dict, or {"error": ...} once every model is exhausted.
    """
    if not image_url:
        return {"error": "No valid image found"}

    base = _build_messages(image_url)

    # Overall budget across every model + retry; each attempt is capped at the smaller
    # of VLM_TIMEOUT and the time left, so the whole call always finishes within it.
    deadline = asyncio.get_running_loop().time() + EXTRACT_DEADLINE

    models_to_try = [model_preference] if model_preference else _VLM_ORDER

    for pref in models_to_try:
        llm = select_vlm(pref)
        messages = list(base)
        for attempt in range(FEEDBACK_RETRIES + 1):
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                log.warning("vision_llm.deadline_exceeded", model=pref)
                return {"error": "Image analysis took too long. Please try again."}
            try:
                response = await asyncio.wait_for(
                    llm.ainvoke(messages), timeout=min(VLM_TIMEOUT, remaining)
                )
                raw_text = response.content if hasattr(response, "content") else str(response)
                result: ProductInfo = _parse_product_info(raw_text)
                return result.model_dump()
            except Exception as exc:
                if _is_schema_error(exc):
                    # Model's fault and fixable → feed the error back, retry same model.
                    log.warning(
                        "vision_llm.schema_failed",
                        model=pref,
                        attempt=attempt + 1,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                    messages.append(_schema_feedback(exc))
                    continue
                if _is_fatal_input(exc):
                    log.error("vision_llm.fatal_input", model=pref, error=str(exc))
                    return {
                        "error": "The image could not be processed. Please try a clearer or smaller image."
                    }
                # Transient / infra / unknown → stop retrying this model, try the next.
                log.warning(
                    "vision_llm.model_failed",
                    model=pref,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                break
        # Schema retries exhausted on this model → fall through to the next model.

    log.error("vision_llm.all_models_exhausted")
    return {"error": "Failed to extract image information"}
