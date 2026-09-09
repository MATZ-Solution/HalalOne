"""Web search provider for the fallback path (Exa, streaming /search).

Hits Exa's /search endpoint with stream=true and a structured output schema, so
Exa returns a synthesized product object plus per-field grounding citations.
Isolated here (sync, behind one generator) so the provider can be swapped and so
it drops straight into the synchronous tool/graph context.
"""

import os
import json
import time
import random
import httpx
from dotenv import load_dotenv
from log.logger import log
from ..utils.utils import CANONICAL_LISTS

load_dotenv()

_NUM_RESULTS = 4
_EXA_SEARCH_URL = "https://api.exa.ai/search"
_STREAM_TIMEOUT = 60

# Retry policy for transient failures (network blips, timeouts, Exa 429/5xx).
_MAX_ATTEMPTS = 3  # 1 initial try + 2 retries
_BASE_BACKOFF = 0.5  # seconds; grows 0.5 -> 1.0 -> 2.0 ...
_MAX_BACKOFF = 8.0
# Status codes worth retrying: throttling and server-side/gateway errors. 4xx like
# 400/401/403/404 are the caller's fault and won't change on a retry.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
VALID_FIELD_ITEMS = ["sold_in", "marketplace", "cert_bodies", "halal_status"]


def _is_retryable(exc: httpx.HTTPError) -> bool:
    """True only for errors a retry might fix: transport-level (timeout, connection
    reset, remote hangup) or a retryable HTTP status. Client 4xx and everything else
    are terminal."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return isinstance(
        exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)
    )


def _backoff_delay(exc: httpx.HTTPError, attempt: int) -> float:
    """Seconds to wait before the next attempt. Honors a numeric Retry-After header
    on throttle/unavailable responses; otherwise exponential backoff with jitter."""
    if isinstance(exc, httpx.HTTPStatusError):
        retry_after = exc.response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), _MAX_BACKOFF)
            except ValueError:
                pass  # HTTP-date form — fall through to computed backoff
    base = min(_BASE_BACKOFF * (2**attempt), _MAX_BACKOFF)
    return base + random.uniform(0, base * 0.25)  # jitter to avoid thundering herd


def _str_list(description: str, field: str | None = None) -> dict:
    """A JSON-schema array-of-strings field with its own description."""
    if field is not None and field not in VALID_FIELD_ITEMS:
        raise ValueError(
            f"Invalid field name {field}. Must be one of: sold_in, marketplace, cert_bodies, halal_status"
        )
    return {
        "type": "array",
        "items": {"anyOf": [{"enum": CANONICAL_LISTS[field]}, {"type": "string"}]}
        if field
        else {"type": "string"},
        "description": description,
    }


# Per-product object. Exa caps outputSchema at 10 TOTAL properties across all
# levels; the products-array wrapper below spends one, so this holds 9 fields.
_WEB_PRODUCT_SCHEMA = {
    "type": "object",
    "properties": {
        "norm_name": {
            "type": "string",
            "description": "Normalised product name, e.g. 'Nestle KitKat Wafer'",
        },
        "companies": _str_list(
            "Brand or manufacturer names that make or sell the product"
        ),
        "halal_status": {
            "type": "string",
            "description": "Halal status exactly as stated in the source",
            "enum": ["Halal", "Haram", "Mushbooh", "Unknown"],
        },
        "cert_bodies": _str_list(
            "Names of the organisations that certified the product as halal",
            "cert_bodies",
        ),
        "cert_numbers": _str_list("Official halal certificates or reference numbers"),
        "category_l1": {
            "type": "string",
            "description": "Top-level product category, e.g. 'Food', 'Non-food', 'Beverage'",
            "anyOf": [{"enum": CANONICAL_LISTS["category_l1"]}, {"type": "string"}],
        },
        "category_l2": {
            "type": "string",
            "description": "Sub-category, e.g. 'Snacks & Confectionery','Hospitality', 'Antioxidant'",
            "anyOf": [{"enum": CANONICAL_LISTS["category_l2"]}, {"type": "string"}],
        },
        "sold_in": _str_list(
            "Countries or regions where the product is sold", "sold_in"
        ),
        "marketplace": _str_list(
            "Retail channels or marketplaces where it is available, e.g. 'Amazon', 'Walmart'",
            "marketplace",
        ),
        # typical_uses dropped to free a property slot: Exa caps the schema at 10
        # TOTAL properties, and wrapping products in a list spends one on the array.
        # "typical_uses": _str_list("Common usage contexts, e.g. 'snacking', 'baking'"),
        # "fda_numbers": _str_list("FDA registration numbers listed for the product"),
        # "barcodes": _str_list("Product barcodes (UPC/EAN)"),
        # "health_info": _str_list("Health effects, dietary notes, allergens or warnings stated for the product"),
    },
    "required": ["norm_name"],
}

# Exa requires the root schema to be an object (arrays can't be top-level), so the
# synthesised products are returned as a list under a single "products" property.
WEB_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "items": _WEB_PRODUCT_SCHEMA,
            "description": "All matching halal products found across the web sources.",
        }
    },
    "required": ["products"],
}


def stream_web_search(
    query: str, num_results: int = _NUM_RESULTS, search_type: str = "auto"
):
    """Yield decoded Exa /search streaming event dicts as they arrive.

    Frame types this function yields:
      - {"type": "results", "results": [{"url", "title", "favicon", "highlights"}, ...]}
      - {"type": "done", "output": {"content": {"products": [<product>, ...]}, "grounding": [...]}}

    This is a generator. It yields nothing on any failure (missing key, network
    or HTTP error), so the caller can treat "no events" as "no web results".

    Transient failures (connection blips, timeouts, Exa 429/5xx) are retried with
    exponential backoff — but ONLY before the first frame is yielded. Once we've
    streamed anything to the caller, a retry would re-emit duplicate frames, so a
    mid-stream break is logged and ends the stream with whatever arrived.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        log.error("web_search.exa_api_key.missing")
        return

    payload = {
        "query": query,
        "numResults": num_results,
        "type": search_type,
        "stream": True,
        "outputSchema": WEB_OUTPUT_SCHEMA,
        "contents": {"highlights": True},
    }
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    for attempt in range(_MAX_ATTEMPTS):
        yielded_any = False
        try:
            with httpx.Client(timeout=_STREAM_TIMEOUT) as client:
                with client.stream(
                    "POST", _EXA_SEARCH_URL, headers=headers, json=payload
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[len("data:") :].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            frame = json.loads(raw)
                        except json.JSONDecodeError:
                            log.warning(
                                "web_search.sse_frame.skipped", note="non-JSON frame"
                            )
                            continue
                        yielded_any = True
                        yield frame
            return  # stream finished cleanly
        except httpx.HTTPError as e:
            # Retry only when it's transient AND we haven't yet emitted anything —
            # retrying after a partial stream would double-send frames to the caller.
            can_retry = (
                _is_retryable(e) and not yielded_any and attempt < _MAX_ATTEMPTS - 1
            )
            if can_retry:
                delay = _backoff_delay(e, attempt)
                log.warning(
                    "web_search.exa_stream.retrying",
                    attempt=attempt + 1,
                    delay=round(delay, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                time.sleep(delay)
                continue
            log.error(
                "web_search.exa_stream.failed",
                attempt=attempt + 1,
                yielded=yielded_any,
                error=str(e),
                error_type=type(e).__name__,
            )
            return
