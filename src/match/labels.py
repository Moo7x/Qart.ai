"""Every number shown in the role score (C2) and the plan (C3) carries a source or a label.

AGENTS.md: label every number as observed (source and date), assumption or estimate. Each
numeric field is listed with the check that its label is present; a number with no entry counts
as unlabelled, so a field added later without a label is caught. Used by tests/test_personas.py
and scripts/kpis.py (the report's share of labelled numbers).
"""

import re
from collections.abc import Callable
from typing import Any

Check = Callable[[dict[str, Any], re.Match[str]], Any]


def _requirement(card: dict[str, Any], skill: str) -> dict[str, Any]:
    return next(r for r in card["requirements"] if r["skill"] == skill)


# Role card (GET /matches): numeric path → its label.
C2_LABELS: list[tuple[str, Check]] = [
    (r"fit", lambda card, _: card["band_basis"] == "assumption" and card["components"]),
    (r"fit_range\.(low|high)", lambda card, _: card["fit_range"]["basis"]),
    (
        r"components\[(\d+)\]\.weight",
        lambda card, m: _requirement(card, card["components"][int(m[1])]["skill"])["shift_reason"],
    ),
    (r"components\[(\d+)\]\.points", lambda card, _: card["band_basis"]),
    (r"components\[(\d+)\]\.claimed", lambda card, m: card["components"][int(m[1])]["source"]),
    (r"components\[(\d+)\]\.required", lambda card, _: True),  # TalentCorp tier level, cited pages
    (r"raise\[(\d+)\]\.points", lambda card, m: card["raise"][int(m[1])]["via"]),
    (r"raise\[(\d+)\]\.(from_level|to_level)", lambda card, m: card["raise"][int(m[1])]["via"]),
    (r"pay\.\w+", lambda card, _: card["pay"]["kind"] == "observed" and card["pay"]["source"]),
]
# Plan (GET /pathway).
C3_LABELS: list[tuple[str, Check]] = [
    (
        r"steps\[(\d+)\]\.time\.(value|low|high)",
        lambda p, m: p["steps"][int(m[1])]["time"]["basis"],
    ),
    (r"steps\[(\d+)\]\.(order|target_level)", lambda p, _: True),  # positions and levels
    (
        r"practice_steps\[(\d+)\]\.time\.(value|low|high)",
        lambda p, m: p["practice_steps"][int(m[1])]["time"]["basis"] == "practice_estimate",
    ),
    (
        r"practice_steps\[(\d+)\]\.week_start\.(low|high)",
        lambda p, m: p["practice_steps"][int(m[1])]["time"]["basis"] == "practice_estimate",
    ),
    (r"practice_steps\[(\d+)\]\.(order|target_level)", lambda p, _: True),
    (r"study_hours", lambda p, _: all(s["time"]["basis"] for s in p["steps"])),
    (r"practice_weeks\.(low|high)", lambda p, _: p["practice_weeks"]["kind"] == "estimate"),
    (
        r"fit_after_(study|practice)\.(low|high)",
        lambda p, m: p[f"fit_after_{m[1]}"]["kind"] == "estimate",
    ),
    (r"free_share", lambda p, _: p["free_share_basis"]),
]
C2_FIELDS = ("fit", "fit_range", "band", "components", "raise", "essentials_short", "pay")
C3_STEP_FIELDS = ("order", "target_level", "time")
C3_TOTALS = (
    "practice_steps",
    "study_hours",
    "practice_weeks",
    "fit_after_study",
    "fit_after_practice",
    "free_share",
)


def numbers(value: Any, path: str = "") -> list[str]:
    """Paths of every number in a JSON-like value (booleans and nulls are not numbers)."""
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, int | float):
        return [path]
    if isinstance(value, dict):
        return [n for k, v in value.items() for n in numbers(v, f"{path}.{k}" if path else k)]
    if isinstance(value, list):
        return [n for i, v in enumerate(value) for n in numbers(v, f"{path}[{i}]")]
    return []


def unlabelled(doc: dict[str, Any], paths: list[str], table: list[tuple[str, Check]]) -> list[str]:
    """The paths whose label is missing, or that have no declared label at all."""
    missing = []
    for path in paths:
        for pattern, label in table:
            match = re.fullmatch(pattern, path)
            if match:
                if not label(doc, match):
                    missing.append(path)
                break
        else:
            missing.append(path)
    return missing


def c2_numbers(card: dict[str, Any]) -> list[str]:
    return numbers({k: card[k] for k in C2_FIELDS})


def c3_numbers(path: dict[str, Any]) -> list[str]:
    totals = numbers({k: path[k] for k in C3_TOTALS})
    steps = numbers({"steps": [{k: s[k] for k in C3_STEP_FIELDS} for s in path["steps"]]})
    return totals + steps
