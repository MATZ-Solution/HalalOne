"""Web search provider for the fallback path (Exa, streaming /search).

Hits Exa's /search endpoint with stream=true and a structured output schema, so
Exa returns a synthesized product object plus per-field grounding citations.
Isolated here (sync, behind one generator) so the provider can be swapped and so
it drops straight into the synchronous tool/graph context.
"""
import os
import json
import httpx
from dotenv import load_dotenv
from log.logger import log

load_dotenv()

_NUM_RESULTS = 4
_EXA_SEARCH_URL = "https://api.exa.ai/search"
_STREAM_TIMEOUT = 60


def _str_list(description: str) -> dict:
    """A JSON-schema array-of-strings field with its own description."""
    return {"type": "array", "items": {"type": "string"}, "description": description}


# Flat, per-product schema (a single product object, not a list).
# NOTE: Exa caps object schemas at 10 properties (nesting depth 2), so a few
# lower-value fields are commented out to stay within the limit.
WEB_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "norm_name": {"type": "string", "description": "Normalised product name, e.g. 'Nestle KitKat Wafer'"},
        "companies": _str_list("Brand or manufacturer names that make or sell the product"),
        "halal_status": {"type": "string", "description": "Halal status exactly as stated in the source", "enum": ["Halal", "Haram", "Mushbooh", "Unknown"]},
        "cert_bodies": _str_list("Names of the organisations that certified the product as halal"),
        "cert_numbers": _str_list("Official halal certificates or reference numbers"),
        "category_l1": {"type": "string", "description": "Top-level product category, e.g. 'Food', 'Cosmetics'"},
        "category_l2": {"type": "string", "description": "Sub-category, e.g. 'Confectionery', 'Beverage'"},
        "sold_in": _str_list("Countries or regions where the product is sold"),
        "marketplace": _str_list("Retail channels or marketplaces where it is available, e.g. 'Amazon', 'Walmart'"),
        "fda_numbers": _str_list("FDA registration numbers listed for the product"),
        # "barcodes": _str_list("Product barcodes (UPC/EAN)"),
        # "typical_uses": _str_list("Common usage contexts of the product, e.g. 'snacking', 'baking'"),
        # "health_info": _str_list("Health effects, dietary notes, allergens or warnings stated for the product"),
    },
    "required": ["norm_name"],
}


def stream_web_search(query: str, num_results: int = _NUM_RESULTS, search_type: str = "auto"):
    """Yield decoded Exa /search streaming event dicts as they arrive.

    Frame types this function yields:
      - {"type": "results", "results": [{"url", "title", "favicon", "highlights"}, ...]}
      - {"type": "done", "output": {"content": {<product>}, "grounding": [...]}}

    This is a generator. It yields nothing on any failure (missing key, network
    or HTTP error), so the caller can treat "no events" as "no web results".
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

    try:
        with httpx.Client(timeout=_STREAM_TIMEOUT) as client:
            with client.stream("POST", _EXA_SEARCH_URL, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    if not raw or raw == "[DONE]":
                        continue
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError:
                        log.warning("web_search.sse_frame.skipped", note="non-JSON frame")
                        continue
    except httpx.HTTPError as e:
        log.error("web_search.exa_stream.failed", error=str(e), error_type=type(e).__name__)
        return


# if __name__ == "__main__":
#     for evt in stream_web_search("Is Kitkat halal?"):
#         etype = evt.get("type")
#         if etype == "results":
#             for r in evt.get("results", []):
#                 print("SOURCE:", r.get("title"), "::", r.get("url"))
#         elif etype == "done":
#             output = evt.get("output") or {}
#             print("\nPRODUCT:", json.dumps(output.get("content"), indent=2, ensure_ascii=False))
#             print("\nGROUNDING:", json.dumps(output.get("grounding"), indent=2, ensure_ascii=False))
