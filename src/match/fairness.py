"""Paired-profile fairness check (docs/PHASE2_PLAN.md §4 C10): protected attributes never change a
result.

The same synthetic CV (data/samples/nur.txt) is given three different identities (name, gender,
religion, race, age, marital status, contact details). Each is scrubbed, read with the keyword
reader (no model), given the same fixed level per claim, ranked and planned in both scenarios.
Every result must be identical. Pure: tests/test_fairness.py uses the same VARIANTS, and owner A's
status page shows this result with its date.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import REPO_ROOT
from src.intake.extract import keyword_extract
from src.intake.pii import scrub
from src.journey.store import claims_from_levels
from src.match.engine import Evidence, Scenario, rank_roles
from src.pack import Pack
from src.pathway.planner import plan_pathway

SAMPLE = REPO_ROOT / "data" / "samples" / "nur.txt"
SCENARIOS: tuple[Scenario, ...] = ("moderate", "fast")
FIXED_LEVEL = 2  # every keyword claim at the same level, so only the identity differs
WEEKLY_HOURS = 6

# Synthetic identities only. Each replaces the four contact lines at the top of the sample CV.
VARIANTS = [
    [
        "Nur Aisyah Binti Kamal",
        "Gender: Female",
        "Religion: Islam",
        "Race: Malay",
        "Date of birth: 01/01/1990",
        "Marital status: Married",
        "Email: nur.aisyah.sample@example.com",
        "Phone: +60 12-345 6789",
        "IC No: 900101-14-5678",
    ],
    [
        "Tan Wei Ming",
        "Gender: Male",
        "Religion: Buddhism",
        "Race: Chinese",
        "Date of birth: 15/06/1975",
        "Marital status: Single",
        "Email: tan.weiming.sample@example.com",
        "Phone: 019-876 5432",
        "IC No: 750615-10-1234",
    ],
    [
        "Rajesh A/L Kumar",
        "Gender: Male",
        "Religion: Hinduism",
        "Race: Indian",
        "Date of birth: 20/03/2001",
        "Marital status: Divorced",
        "Email: rajesh.kumar.sample@example.com",
        "Phone: +6011 2233 4455",
        "IC No: 010320-08-4321",
    ],
]


def variant_cv(header: list[str], sample: Path = SAMPLE) -> str:
    body = sample.read_text(encoding="utf-8").split("\n")[4:]  # drop the original identity lines
    return "\n".join([*header, *body])


def _results(pack: Pack, evidence: Evidence, cv: str) -> dict[str, Any]:
    """Everything a person would see from this CV: roles, fits, gaps and the top role's plan."""
    role, claims = keyword_extract(pack, scrub(cv).text)
    levels: dict[str, int | None] = {c.skill: c.level or FIXED_LEVEL for c in claims}
    out: dict[str, Any] = {"current_role": role}
    for scenario in SCENARIOS:
        ranked = rank_roles(pack, levels, scenario, evidence)
        plan = plan_pathway(
            pack, ranked[0], claims_from_levels(levels), WEEKLY_HOURS, scenario, evidence
        )
        out[scenario] = {
            "fits": {m.role_id: m.fit for m in ranked},
            "order": [m.role_id for m in ranked],
            "gaps": {m.role_id: m.gap for m in ranked},
            "plan": ([s.course.id for s in plan.steps], plan.total_hours, plan.fit_after),
        }
    return out


def paired_profile_check(
    pack: Pack, evidence: Evidence, variants: list[list[str]] | None = None
) -> dict[str, Any]:
    """Compare every variant with the first: identical results, and the largest fit difference."""
    results = [_results(pack, evidence, variant_cv(v)) for v in (variants or VARIANTS)]
    first = results[0]
    max_diff = 0.0
    for other in results[1:]:
        for scenario in SCENARIOS:
            fits_a, fits_b = first[scenario]["fits"], other[scenario]["fits"]
            for role_id in fits_a.keys() | fits_b.keys():
                diff = abs(fits_a.get(role_id, 0.0) - fits_b.get(role_id, 0.0))
                max_diff = max(max_diff, diff)
    return {
        "pairs": len(results) - 1,
        "identical": all(r == first for r in results[1:]),
        "max_fit_difference": round(max_diff, 1),
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
