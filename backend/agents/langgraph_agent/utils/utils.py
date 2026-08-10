from typing import Optional
from ..models.models import FilterArgs

COLLECTION = "halal_products"

KEYWORD_FIELDS = {"norm_name", "companies", "health_info", "typical_uses"}
FILTER_FIELDS = {
    "category_l1", "category_l2", "halal_status", "sold_in",
    "cert_bodies", "cert_numbers", "fda_numbers", "barcodes", "marketplace",
}

# Tool-call budgets: keyword-first can climb the full ladder
# (keyword -> web -> semantic x2); a semantic-first query only runs semantic.
MAX_KEYWORD_CALLS = 5
MAX_SEMANTIC_CALLS = 2

KEYWORD = "KeywordFilterSearch"
SEMANTIC = "SemanticFilterSearch"
WEB = "WebSearch"


def select_tools(first_tool: Optional[str], tools_called: list[str]) -> list[str]:
    """The tools to bind for the next search call, enforcing the fallback ladder.

    First call: {keyword, semantic} — the LLM's only free choice (sets first_tool).
    Keyword-first ladder: keyword -> {keyword|web} -> web -> semantic -> semantic.
    Semantic-first: always semantic.
    Pure function so the ladder can be unit-tested without an LLM.
    """
    n = len(tools_called)
    if n == 0:
        return [KEYWORD, SEMANTIC]
    if first_tool == SEMANTIC:
        return [SEMANTIC]
    # Keyword-first ladder. Web may run at most once — once it has, only semantic
    # is left; until then keyword can be refined once (2nd call) before web.
    if WEB not in tools_called:
        return [KEYWORD, WEB] if n == 1 else [WEB]
    return [SEMANTIC]


def should_loop(first_tool: Optional[str], tools_called_count: int) -> bool:
    """Whether the search loop may run another tool call, given the budget."""
    limit = MAX_SEMANTIC_CALLS if first_tool == SEMANTIC else MAX_KEYWORD_CALLS
    return tools_called_count < limit


def validate_ids(returned_ids: list[str], candidate_ids: list[str]) -> tuple[list[str], list[str]]:
    """Split the judge's ids into (valid, hallucinated). Valid ids exist in the
    candidate pool and are de-duplicated; hallucinated ids don't exist. Pure."""
    candidates = set(candidate_ids)
    seen: set[str] = set()
    valid: list[str] = []
    hallucinated: list[str] = []
    for i in returned_ids:
        if i in candidates:
            if i not in seen:
                seen.add(i)
                valid.append(i)
        else:
            hallucinated.append(i)
    return valid, hallucinated


def _matches_filters(product: dict, active: dict) -> bool:
    """True if the product satisfies every active filter (case-insensitive)."""
    for key, want in active.items():
        have = product.get(key)
        if have is None:
            return False
        if isinstance(want, list):
            have_set = {str(x).lower() for x in (have if isinstance(have, list) else [have])}
            if not all(str(w).lower() in have_set for w in want):
                return False
        elif isinstance(have, list):
            if str(want).lower() not in {str(x).lower() for x in have}:
                return False
        elif str(have).lower() != str(want).lower():
            return False
    return True


def apply_filter_check(products: list[dict], filters: Optional[dict]) -> tuple[list[dict], list[dict]]:
    """Split products into (passers, rejected) by the exact filters the user gave.
    Mostly a safety net for web results (DB results are already filtered). Pure."""
    active = {k: v for k, v in (filters or {}).items() if v}
    if not active:
        return list(products), []
    passers, rejected = [], []
    for p in products:
        (passers if _matches_filters(p, active) else rejected).append(p)
    return passers, rejected


def dedup_by_id(products: list[dict]) -> list[dict]:
    """Drop products whose canonical_id was already seen, preserving order. Pure."""
    seen: set[str] = set()
    out: list[dict] = []
    for p in products:
        pid = p.get("canonical_id")
        if pid and pid in seen:
            continue
        if pid:
            seen.add(pid)
        out.append(p)
    return out


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
