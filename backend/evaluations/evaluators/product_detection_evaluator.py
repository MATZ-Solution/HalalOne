import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==============================================================================
# PARENT - CHILD BRAND FAMILIES (From your Excel sheet hierarchy)
# ==============================================================================
BRAND_FAMILIES = {
    "mars": {
        "mars",
        "twix",
        "snickers",
        "skittles",
        "hubba bubba",
        "m&m's",
        "bounty",
        "galaxy",
        "maltesers",
        "milky way",
    },
    "twix": {"mars", "twix"},
    "snickers": {"mars", "snickers"},
    "skittles": {"mars", "skittles"},
    "hubba bubba": {"mars", "hubba bubba"},
    "ferrero": {
        "ferrero",
        "nutella",
        "kinder",
        "tic tac",
        "ferrero rocher",
        "raffaello",
    },
    "nutella": {"ferrero", "nutella"},
    "kinder": {"ferrero", "kinder"},
    "nestle": {
        "nestle",
        "nestlé",
        "aero",
        "kitkat",
        "damak",
        "milkybar",
        "garden gourmet",
        "hot pockets",
        "maggi",
        "smarties",
    },
    "aero": {"nestle", "nestlé", "aero", "milkybar"},
    "kitkat": {"nestle", "nestlé", "kitkat"},
    "damak": {"nestle", "nestlé", "damak"},
    "garden gourmet": {"nestle", "nestlé", "garden gourmet"},
    "unilever": {
        "unilever",
        "knorr",
        "magnum",
        "wall's",
        "walls",
        "cornetto",
        "viennetta",
        "ben & jerry's",
        "ben and jerrys",
        "breyers",
        "hellmann's",
        "lipton",
    },
    "knorr": {"unilever", "knorr"},
    "magnum": {"unilever", "magnum"},
    "cornetto": {"unilever", "wall's", "walls", "cornetto"},
    "wall's": {"unilever", "wall's", "walls", "cornetto"},
    "viennetta": {"unilever", "wall's", "walls", "viennetta"},
    "ben & jerry's": {"unilever", "ben & jerry's", "ben and jerrys"},
    "froneri": {
        "froneri",
        "drumstick",
        "häagen-dazs",
        "haagen dazs",
        "outshine",
        "skinny cow",
    },
    "drumstick": {"froneri", "drumstick"},
    "bahlsen": {
        "bahlsen",
        "leibniz",
        "pickup",
        "pickup!",
        "choco leibniz",
        "ohne gleichen",
        "waffeletten",
        "messino",
    },
    "katjes": {"katjes", "sallos", "vicks", "treets"},
    "almarai": {
        "almarai",
        "7days",
        "alyoum",
        "farm's select",
        "farms select",
        "seama",
        "l'usine",
        "lusine",
        "teama",
    },
    "7days": {"almarai", "7days"},
    "alyoum": {"almarai", "alyoum"},
    "americana": {
        "americana",
        "americana group",
        "americana foods",
        "koki",
        "farm frites",
        "heroz",
        "zingz",
    },
    "heroz": {"americana", "heroz"},
    "zingz": {"americana", "zingz"},
    "farm's select": {"almarai", "farm's select", "farms select"},
    "farms select": {"almarai", "farm's select", "farms select"},
    "americana group": {"americana", "americana group", "americana foods"},
    "americana foods": {"americana", "americana group", "americana foods"},
    "barilla": {"barilla", "mulino bianco", "wasa", "voiello"},
}

STOP_WORDS = {
    "is",
    "the",
    "a",
    "an",
    "and",
    "or",
    "for",
    "by",
    "in",
    "of",
    "with",
    "to",
    "halal",
    "candy",
    "bar",
    "pack",
    "bag",
}


class ProductJudgeVerdict(BaseModel):
    """Structured evaluation verdict from the LLM Judge."""

    reasoning: str = Field(
        ...,
        description="Step-by-step reasoning on whether the retrieved products/response match the user's requested product and company.",
    )
    product_brought_up: bool = Field(
        ...,
        description="True if the agent brought up the requested product (accounting for packaging/weight/alias differences), False otherwise.",
    )


JUDGE_SYSTEM_PROMPT = """You are an expert evaluation judge for the HalalOne product verification system.

Your job is to determine whether the AI agent successfully identified, fetched, and addressed the user's requested product.

CRITERIA:
1. Product Match: The retrieved items or the response must refer to the same specific product the user asked for. Minor variations (such as pack sizes, grams/ounces, brand prefixes, slight spelling differences like 'Al Paka' vs 'Alpaka', or slight naming simplifications) count as a PASS.
2. Company/Brand Match: If the user specified a company or brand, the product must be from that brand/company or its recognized parent/subsidiary (e.g., Mars owns Twix/Snickers/Skittles; Ferrero owns Nutella/Kinder; Nestle owns KitKat/Aero; Unilever owns Knorr/Magnum/Cornetto/Viennetta; Almarai owns 7DAYS/Alyoum). If no company was specified, evaluate only the product.
3. Pass Condition: If the agent successfully retrieved and answered about the requested product, set `product_brought_up` to True.
4. Fail Condition: If the agent fetched an entirely unrelated product, hallucinated, or gave a generic 'not found' / 'I wasn't able to find' without bringing up the product, set `product_brought_up` to False.

Explain your reasoning clearly, then return your verdict.
"""


def _normalize(text: str) -> str:
    """Helper to clean strings by removing punctuation, weights, and extra whitespace."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r"\b\d+(\.\d+)?\s*(g|oz|ounce|pack|ct|ml|kg)\b", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _compact(text: str) -> str:
    """Remove all spaces and punctuation for compressed matching (e.g. 'al paka' -> 'alpaka')."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _extract_keywords(text: str) -> set[str]:
    """Extract significant keywords from a text string."""
    norm = _normalize(text)
    return {w for w in norm.split() if len(w) > 2 and w not in STOP_WORDS}


def _is_company_match(
    expected_company: str, doc_company: str, doc_name: str, response_text: str
) -> bool:
    """
    Checks if expected company matches directly, through parent-child family,
    or appears in the product name itself.
    """
    if not expected_company:
        return True

    norm_expected = _normalize(expected_company)
    norm_doc_company = _normalize(doc_company)
    norm_doc_name = _normalize(doc_name)
    norm_response = _normalize(response_text)

    # 1. Direct substring in company or doc name or response
    if (
        norm_expected in norm_doc_company
        or norm_expected in norm_doc_name
        or norm_expected in norm_response
    ):
        return True

    # 2. Check Parent-Child Brand Family Map
    for brand_key, family in BRAND_FAMILIES.items():
        if norm_expected in brand_key or brand_key in norm_expected:
            for member in family:
                norm_member = _normalize(member)
                if (
                    norm_member in norm_doc_company
                    or norm_member in norm_doc_name
                    or norm_member in norm_response
                ):
                    return True

    return False


def _extract_from_outputs(outputs: dict) -> tuple[list, str]:
    """Safely extracts retrieved products and response text from diverse outputs shapes."""
    if not isinstance(outputs, dict):
        return [], str(outputs or "")

    retrieved = outputs.get("retrieved_products") or []
    response = outputs.get("response_text") or outputs.get("response") or ""

    messages = outputs.get("messages") or []
    if messages and not response:
        last_msg = messages[-1]
        content = getattr(last_msg, "content", "")
        if isinstance(content, str):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    response = data.get("response", "")
                    if not retrieved:
                        matched = data.get("matched") or []
                        relevant = data.get("relevant") or []
                        retrieved = matched + relevant
            except Exception:
                response = content
        elif isinstance(content, dict):
            response = content.get("response", "")
            if not retrieved:
                retrieved = (content.get("matched") or []) + (
                    content.get("relevant") or []
                )

    # Also check outputs['matched'] and outputs['relevant'] directly
    if not retrieved:
        retrieved = (outputs.get("matched") or []) + (outputs.get("relevant") or [])

    return retrieved, response


def _tier1_code_check(
    expected_product: str,
    expected_company: str,
    retrieved_products: list,
    response_text: str,
) -> tuple[bool, str]:
    """
    Tier 1 Deterministic Code Evaluator:
    Checks if normalized expected_product and expected_company exist in retrieved docs or response
    via exact substring, compressed matching, or keyword overlap.
    """
    norm_expected_product = _normalize(expected_product)
    compact_expected = _compact(expected_product)
    expected_keywords = _extract_keywords(expected_product)

    product_matched = False
    company_matched = False if expected_company else True

    # Check inside structured product documents
    for doc in retrieved_products:
        if isinstance(doc, dict):
            doc_name = (
                doc.get("norm_name") or doc.get("name") or doc.get("product_name") or ""
            )
            doc_company = str(
                doc.get("companies") or doc.get("brand") or doc.get("company") or ""
            )
            norm_doc_name = _normalize(doc_name)
            compact_doc = _compact(doc_name)
            doc_keywords = _extract_keywords(doc_name)

            # 1. Substring match
            if norm_expected_product and (
                norm_expected_product in norm_doc_name
                or norm_doc_name in norm_expected_product
            ):
                product_matched = True

            # 2. Compact match (ignores spaces like 'al paka' vs 'alpaka')
            if compact_expected and (
                compact_expected in compact_doc or compact_doc in compact_expected
            ):
                product_matched = True

            # 3. Keyword overlap match
            overlap = expected_keywords.intersection(doc_keywords)
            if len(expected_keywords) > 0 and (
                len(overlap) >= 2 or len(overlap) / len(expected_keywords) >= 0.5
            ):
                product_matched = True

            if expected_company and _is_company_match(
                expected_company, doc_company, doc_name, response_text
            ):
                company_matched = True

    # Check inside text response
    if not product_matched and expected_keywords:
        response_keywords = _extract_keywords(response_text)
        overlap = expected_keywords.intersection(response_keywords)
        if len(expected_keywords) > 0 and (
            len(overlap) >= 2 or len(overlap) / len(expected_keywords) >= 0.5
        ):
            product_matched = True

    if expected_company and not company_matched:
        if _is_company_match(expected_company, "", "", response_text):
            company_matched = True

    if product_matched and company_matched:
        return (
            True,
            "Tier 1 Code Match Passed (Exact/Compressed/Keyword-overlap/Brand-family match found).",
        )

    return (
        False,
        f"Tier 1 Code Mismatch (Product matched: {product_matched}, Company matched: {company_matched}).",
    )


async def product_detection_evaluator(
    inputs: dict = None, outputs: dict = None, reference_outputs: dict = None
) -> list[dict]:
    """
    Two-Tier Hybrid Evaluator:
    1. Tier 1 (Code): Fast deterministic string, compressed & keyword-overlap matching.
    2. Tier 2 (LLM Judge Fallback): Invoked ONLY if Tier 1 fails to resolve subtle naming/packaging differences.
    """
    inputs = inputs or {}
    outputs = outputs or {}
    reference = reference_outputs or {}

    expected_product = (
        reference.get("expected_product") or inputs.get("product_name") or ""
    )
    expected_company = (
        reference.get("expected_company") or inputs.get("company_name") or ""
    )

    retrieved_products, response_text = _extract_from_outputs(outputs)

    # ==========================================
    # TIER 1: CODE EVALUATOR
    # ==========================================
    code_passed, code_comment = _tier1_code_check(
        expected_product, expected_company, retrieved_products, response_text
    )

    if code_passed:
        return [
            {
                "key": "product_detection_correctness",
                "score": 1,
                "comment": code_comment,
            }
        ]

    # ==========================================
    # TIER 2: LLM-AS-A-JUDGE FALLBACK
    # (Runs only because Tier 1 code failed)
    # ==========================================
    retrieved_summary = []
    for p in retrieved_products[:5]:
        if isinstance(p, dict):
            p_name = p.get("norm_name") or p.get("name") or p.get("product_name") or ""
            p_comp = p.get("companies") or p.get("brand") or p.get("company") or ""
            retrieved_summary.append(f"- Product: {p_name} | Company: {p_comp}")

    retrieved_text = "\n".join(retrieved_summary) if retrieved_summary else "None"

    judge_prompt = f"""USER TARGET:
- Expected Product: {expected_product}
- Expected Company/Brand: {expected_company if expected_company else "N/A (Product Only Query)"}

AGENT EXECUTION OUTPUT:
- Retrieved Products:
{retrieved_text}

- Agent Final Response:
{response_text}
"""

    try:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set.")

        judge_llm = ChatGroq(
            api_key=GROQ_API_KEY, model="openai/gpt-oss-20b", temperature=0
        )
        judge_llm_structured = judge_llm.with_structured_output(
            ProductJudgeVerdict, method="json_mode"
        )
        verdict: ProductJudgeVerdict = await judge_llm_structured.ainvoke(
            [
                SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                HumanMessage(content=judge_prompt),
            ]
        )

        score = 1 if verdict.product_brought_up else 0
        return [
            {
                "key": "product_detection_correctness",
                "score": score,
                "comment": f"Tier 2 LLM Judge ({'PASS' if score == 1 else 'FAIL'}): {verdict.reasoning}",
            }
        ]
    except Exception as e:
        return [
            {
                "key": "product_detection_correctness",
                "score": 0,
                "comment": f"Tier 1 Code Mismatch. (LLM Judge note: {e!s})",
            }
        ]
