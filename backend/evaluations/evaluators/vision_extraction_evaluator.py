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


def _is_substr_match(s1: str, s2: str) -> bool:
    if not s1 or not s2:
        return False
    if s1 in s2 or s2 in s1:
        return True
    # Check space-stripped version (e.g. '7 days' vs '7days')
    s1_compact = s1.replace(" ", "")
    s2_compact = s2.replace(" ", "")
    return s1_compact in s2_compact or s2_compact in s1_compact


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
        if any(_is_substr_match(e, a) for a in act_set):
            matched += 1
    return matched / max(len(exp_set), 1)


async def vision_extraction_evaluator(
    inputs: dict = None, outputs: dict = None, reference_outputs: dict = None
) -> list[dict]:
    """Evaluates the vision LLM extraction output across all 11 schema fields (Max score = 11)."""
    outputs = outputs or {}
    reference = reference_outputs or {}

    # Extract all 11 fields from prediction and reference
    exp_name = _clean_str(reference.get("norm_name"))
    act_name = _clean_str(outputs.get("norm_name") or outputs.get("product_name"))

    exp_companies = reference.get("companies") or []
    act_companies = outputs.get("companies") or []

    exp_certs = reference.get("cert_bodies") or []
    act_certs = outputs.get("cert_bodies") or []

    exp_marketplaces = reference.get("marketplace") or []
    act_marketplaces = outputs.get("marketplace") or []

    exp_cat1 = _clean_str(reference.get("category_l1"))
    act_cat1 = _clean_str(outputs.get("category_l1"))

    exp_cat2 = _clean_str(reference.get("category_l2"))
    act_cat2 = _clean_str(outputs.get("category_l2"))

    exp_halal = _clean_str(reference.get("halal_status"))
    act_halal = _clean_str(outputs.get("halal_status"))

    exp_sold_in = reference.get("sold_in") or []
    act_sold_in = outputs.get("sold_in") or []

    exp_cert_nums = reference.get("cert_numbers") or []
    act_cert_nums = outputs.get("cert_numbers") or []

    exp_fda_nums = reference.get("fda_numbers") or []
    act_fda_nums = outputs.get("fda_numbers") or []

    exp_barcodes = reference.get("barcodes") or []
    act_barcodes = outputs.get("barcodes") or []

    # Scoring each of the 11 fields (1 pt each if correct, 0 if incorrect)
    # 1. Product Name (norm_name)
    name_score = 0
    if not exp_name and not act_name:
        name_score = 1
    elif exp_name and act_name:
        exp_words = set(exp_name.split())
        act_words = set(act_name.split())
        overlap = exp_words.intersection(act_words)
        if exp_name in act_name or act_name in exp_name or len(overlap) >= 2 or (exp_words and len(overlap) / len(exp_words) >= 0.5):
            name_score = 1

    # 2. Companies / Brand (companies) - proportional partial credit
    company_score = round(_calculate_field_overlap(exp_companies, act_companies), 2)

    # 3. Certification Bodies (cert_bodies) - proportional partial credit
    cert_score = round(_calculate_field_overlap(exp_certs, act_certs), 2)

    # 4. Marketplaces (marketplace) - proportional partial credit
    market_score = round(_calculate_field_overlap(exp_marketplaces, act_marketplaces), 2)

    # 5. Category L1 (category_l1)
    cat1_score = 0
    if not exp_cat1 and not act_cat1:
        cat1_score = 1
    elif exp_cat1 and act_cat1 and (exp_cat1 in act_cat1 or act_cat1 in exp_cat1):
        cat1_score = 1

    # 6. Category L2 (category_l2)
    cat2_score = 0
    if not exp_cat2 and not act_cat2:
        cat2_score = 1
    elif exp_cat2 and act_cat2 and (exp_cat2 in act_cat2 or act_cat2 in exp_cat2):
        cat2_score = 1

    # 7. Halal Status (halal_status)
    halal_score = 0
    if not exp_halal and not act_halal:
        halal_score = 1
    elif exp_halal and act_halal:
        if exp_halal in act_halal or act_halal in exp_halal:
            halal_score = 1
        elif ("halal" in exp_halal and "halal" in act_halal) or ("mushbooh" in exp_halal and "mushbooh" in act_halal):
            halal_score = 1

    # 8. Sold In Countries (sold_in) - proportional partial credit
    sold_score = round(_calculate_field_overlap(exp_sold_in, act_sold_in), 2)

    # 9. Certification Numbers (cert_numbers) - proportional partial credit
    cert_num_score = round(_calculate_field_overlap(exp_cert_nums, act_cert_nums), 2)

    # 10. FDA Numbers (fda_numbers) - proportional partial credit
    fda_num_score = round(_calculate_field_overlap(exp_fda_nums, act_fda_nums), 2)

    # 11. Barcodes (barcodes) - proportional partial credit
    barcode_score = round(_calculate_field_overlap(exp_barcodes, act_barcodes), 2)

    raw_total = (
        name_score
        + company_score
        + cert_score
        + market_score
        + cat1_score
        + cat2_score
        + halal_score
        + sold_score
        + cert_num_score
        + fda_num_score
        + barcode_score
    )
    raw_total = round(raw_total, 2)
    max_score = 11

    # Gate: If norm_name is incorrect, fail the entire test because the product itself was not correctly identified
    if name_score == 0:
        total_correct = 0.0
        accuracy = 0.0
        status_prefix = "[FAILED - norm_name mismatch] "
    else:
        total_correct = raw_total
        accuracy = round(total_correct / max_score, 2)
        status_prefix = ""

    feedback = (
        f"{status_prefix}Score: {total_correct}/{max_score} fields | "
        f"Name: {name_score}/1, "
        f"Company: {company_score}/1, "
        f"Certs: {cert_score}/1, "
        f"Marketplace: {market_score}/1, "
        f"CatL1: {cat1_score}/1, "
        f"CatL2: {cat2_score}/1, "
        f"Halal: {halal_score}/1, "
        f"SoldIn: {sold_score}/1, "
        f"CertNums: {cert_num_score}/1, "
        f"FDANums: {fda_num_score}/1, "
        f"Barcode: {barcode_score}/1"
    )

    return [
        {
            "key": "correct_fields_count",
            "score": total_correct,
            "comment": feedback,
        },
        {
            "key": "vision_extraction_accuracy",
            "score": accuracy,
            "comment": feedback,
        }
    ]
