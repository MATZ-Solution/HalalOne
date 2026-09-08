import re
from typing import Any


def _clean_str(text: Any) -> str:
    if text is None:
        return ""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _list_to_clean_set(items: Any) -> set[str]:
    if not items:
        return set()
    if isinstance(items, str):
        items = [items]
    return {_clean_str(x) for x in items if x}


def _calculate_field_overlap(expected_list: list[str], actual_list: list[str]) -> float:
    exp_set = _list_to_clean_set(expected_list)
    act_set = _list_to_clean_set(actual_list)
    if not exp_set and not act_set:
        return 1.0
    if not exp_set or not act_set:
        return 0.0
    # Check partial / substring containment
    matched = 0
    for e in exp_set:
        if any(e in a or a in e for a in act_set):
            matched += 1
    return matched / max(len(exp_set), 1)


async def vision_extraction_evaluator(
    inputs: dict = None, outputs: dict = None, reference_outputs: dict = None
) -> list[dict]:
    """Evaluates the vision LLM extraction output against ground-truth reference schema."""
    outputs = outputs or {}
    reference = reference_outputs or {}

    # Extract fields from prediction and reference
    exp_name = _clean_str(reference.get("norm_name"))
    act_name = _clean_str(outputs.get("norm_name") or outputs.get("product_name"))

    exp_companies = reference.get("companies") or []
    act_companies = outputs.get("companies") or []

    exp_barcodes = reference.get("barcodes") or []
    act_barcodes = outputs.get("barcodes") or []

    exp_halal = _clean_str(reference.get("halal_status"))
    act_halal = _clean_str(outputs.get("halal_status"))

    exp_cat1 = _clean_str(reference.get("category_l1"))
    act_cat1 = _clean_str(outputs.get("category_l1"))

    # Scoring breakdown:
    # 1. Product Name Match (Weight: 30%)
    name_score = 0.0
    if exp_name and act_name:
        exp_words = set(exp_name.split())
        act_words = set(act_name.split())
        overlap = exp_words.intersection(act_words)
        if exp_name in act_name or act_name in exp_name:
            name_score = 1.0
        elif len(overlap) >= 2 or (exp_words and len(overlap) / len(exp_words) >= 0.5):
            name_score = 0.8
        elif len(overlap) >= 1:
            name_score = 0.5

    # 2. Company / Brand Match (Weight: 25%)
    company_score = _calculate_field_overlap(exp_companies, act_companies)

    # 3. Halal Status Match (Weight: 20%)
    halal_score = 0.0
    if exp_halal and act_halal:
        if exp_halal in act_halal or act_halal in exp_halal:
            halal_score = 1.0
        elif ("halal" in exp_halal and "halal" in act_halal) or (
            "mushbooh" in exp_halal and "mushbooh" in act_halal
        ):
            halal_score = 0.8

    # 4. Barcode Match (Weight: 15% if expected, otherwise rolled into others)
    barcode_score = 1.0
    if exp_barcodes:
        barcode_score = _calculate_field_overlap(exp_barcodes, act_barcodes)

    # 5. Category Match (Weight: 10%)
    cat_score = (
        1.0
        if (exp_cat1 and exp_cat1 in act_cat1) or (not exp_cat1 and not act_cat1)
        else 0.5
    )

    total_score = (
        (name_score * 0.30)
        + (company_score * 0.25)
        + (halal_score * 0.20)
        + (barcode_score * 0.15)
        + (cat_score * 0.10)
    )

    feedback = (
        f"Name: {name_score:.2f} (Exp: '{exp_name}' | Act: '{act_name}'), "
        f"Company: {company_score:.2f}, Halal: {halal_score:.2f}, "
        f"Barcode: {barcode_score:.2f}, Category: {cat_score:.2f}"
    )

    return [
        {
            "key": "vision_extraction_accuracy",
            "score": round(total_score, 2),
            "comment": feedback,
        }
    ]
