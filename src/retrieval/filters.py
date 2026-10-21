"""Metadata filtering shared by all retrievers (see SearchFilters for the semantics)."""

from src.engine import params
from src.engine.planner import cost_tier
from src.retrieval.models import Document, MetadataValue, SearchFilters


def _number(value: MetadataValue | None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, float | int):
        return None
    return float(value)


def passes(document: Document, filters: SearchFilters | None) -> bool:
    """True when the document meets every filter that applies to it."""
    if filters is None:
        return True
    meta = document.metadata
    cost, hours = meta.get("cost"), _number(meta.get("hours"))
    language, skills = meta.get("language"), meta.get("skills")
    checks = [
        filters.kinds is None or document.kind in filters.kinds,
        not (
            filters.free_only and isinstance(cost, str) and cost_tier(cost) != params.COST_TIER_FREE
        ),
        filters.max_hours is None or hours is None or hours <= filters.max_hours,
        filters.language is None
        or not isinstance(language, str)
        or language.lower().startswith(filters.language.lower()),
        filters.skills is None
        or not isinstance(skills, list)
        or bool(set(skills) & set(filters.skills)),
    ]
    return all(checks)
