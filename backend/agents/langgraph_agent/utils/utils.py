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
        if k not in FILTER_FIELDS:
            continue
        if isinstance(v, list):
            parts.append(f'{k}:=[{",".join(str(i) for i in v)}]')
        else:
            parts.append(f'{k}:="{v}"')
    return " && ".join(parts)
