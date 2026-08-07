from typing import Optional
from ..models.models import FilterArgs



COLLECTION = "halal_products"

KEYWORD_FIELDS = {"norm_name", "companies", "health_info", "typical_uses"}
FILTER_FIELDS = {
    "category_l1", "category_l2", "halal_status", "sold_in",
    "cert_bodies", "cert_numbers", "fda_numbers", "barcodes", "marketplace",
}


def build_filter_string(filter_args: Optional[FilterArgs]) -> str:
    if not filter_args:
        return ""
    parts = []
    for k, v in filter_args.model_dump().items():
        # model_dump() returns every field, including the ones the LLM left unset
        # (None) — those must be skipped, not filtered on. Same falsy guard
        # KeywordFilterSearch applies when it builds its own filters.
        if k not in FILTER_FIELDS or not v:
            continue
        if isinstance(v, list):
            # Quote each item so multi-word values ("United Kingdom") survive;
            # matches how search_collection builds the same expression.
            quoted = ",".join(f'"{i}"' for i in v)
            parts.append(f"{k}:=[{quoted}]")
        else:
            parts.append(f'{k}:="{v}"')
    return " && ".join(parts)
