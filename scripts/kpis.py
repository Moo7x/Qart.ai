"""Report figures for Section 4 (docs/PHASE2_PLAN.md §8 B9), computed by code, not written by hand.

Run: python -m scripts.kpis   → writes docs/KPI_RESULTS.md

It builds the app on a temporary SQLite file with no model keys and uses the app's own API, so the
figures are what a person would see. Figures:
1. Verified free-course coverage of the required skills, over the Phase 1 denominator (the 37
   skills pinned below; Phase 1 baseline 27/37, target at least 34/37). Catalogue changes since
   Phase 1 are reported separately and never folded into that comparison.
2. The free share of each persona's plan.
3. The share of numbers in the role score (C2) and plan (C3) that carry a source or a label.
4. The paired-profile fairness check (C10).
"""

import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.api.journey import load_personas
from src.app import create_app
from src.config import REPO_ROOT, Settings, load_settings
from src.db import make_engine
from src.journey.impact import time_to_plan
from src.levels import required_skills
from src.match.engine import Evidence
from src.match.fairness import paired_profile_check
from src.match.labels import C2_LABELS, C3_LABELS, c2_numbers, c3_numbers, unlabelled
from src.pack import load_pack

OUT = REPO_ROOT / "docs" / "KPI_RESULTS.md"
# The required skills at Phase 1 (the denominator of the 27/37 baseline), pinned so roles added
# later (B10) never change the comparison.
PHASE1_REQUIRED = (
    "accounting_principles", "advanced_technology_integration", "big_data_analytics",
    "budget_management", "business_environment_analytics", "compliance_reporting",
    "continuous_improvement", "credit_collections", "dashboards", "data_management",
    "data_migration", "database_querying", "digital_business_model", "ehs", "energy_management",
    "erp", "esg", "financial_reporting", "financial_systems", "fixed_assets", "fpa",
    "general_ledger", "green_asset_management", "green_auditing", "green_procurement",
    "internal_controls", "invoice_processing", "process_automation", "process_optimisation",
    "reporting", "stakeholder_management", "standard_costing", "statistical_analytics",
    "system_performance", "systems_integration", "variance_analytics", "vendor_management",
)  # fmt: skip
PHASE1_COVERED = 27
TARGET_SHARE = 0.9  # Phase 1 commitment: at least 90% (34/37)


def coverage() -> dict[str, Any]:
    pack = load_pack()
    covered = [s for s in PHASE1_REQUIRED if pack.courses_for(s)]
    added = [s for s in required_skills(pack) if s not in PHASE1_REQUIRED]
    return {
        "denominator": len(PHASE1_REQUIRED),
        "covered": len(covered),
        "share": len(covered) / len(PHASE1_REQUIRED),
        "target": TARGET_SHARE,
        "target_count": -(-int(TARGET_SHARE * 100) * len(PHASE1_REQUIRED) // 100),
        "baseline": PHASE1_COVERED,
        "uncovered": [pack.skills[s].name for s in PHASE1_REQUIRED if s not in covered],
        "added_skills": [(pack.skills[s].name, bool(pack.courses_for(s))) for s in added],
        "catalogue_checked": pack.courses_checked,
        "verified_courses": sum(c.verified for c in pack.courses.values()),
        "candidate_courses": sum(not c.verified for c in pack.courses.values()),
    }


def personas(client: TestClient) -> list[dict[str, Any]]:
    """Each persona through the API: top role, plan, and the label check on C2 and C3."""
    out = []
    for name, persona in load_personas().items():
        skills = {
            k: {"level": c["level"], "evidence": c["evidence"], "source": "cv"}
            for k, c in persona["skills"].items()
        }
        body = {"situation": persona["situation"], "skills": skills}
        pid = client.post("/api/profiles", json=body).json()["id"]
        card = client.get(f"/api/profiles/{pid}/matches").json()["roles"][0]
        client.post(f"/api/profiles/{pid}/destination", json={"role_id": card["role_id"]})
        path = client.get(f"/api/profiles/{pid}/pathway").json()
        c2, c3 = c2_numbers(card), c3_numbers(path)
        missing = unlabelled(card, c2, C2_LABELS) + unlabelled(path, c3, C3_LABELS)
        out.append(
            {
                "persona": name,
                "role": card["title"],
                "fit": card["fit"],
                "study_hours": path["study_hours"],
                "free_share": path["free_share"],
                "free_share_basis": path["free_share_basis"],
                "numbers": len(c2) + len(c3),
                "unlabelled": missing,
            }
        )
    return out


def _version() -> str:
    try:
        found = subprocess.run(
            ["git", "describe", "--always", "--dirty=+uncommitted"],
            capture_output=True,
            text=True,
            check=True,
        )
        return found.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def compute() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            database_url=f"sqlite:///{(Path(tmp) / 'kpis.sqlite').as_posix()}",
            llm_api_key=None,
            llm_base_url=None,
            llm_model="gpt-4o-mini",
            runpod_api_key=None,
            runpod_endpoint_id=None,
            admin_token=None,
        )
        app = create_app(settings, first_run=False)
        with TestClient(app) as client:
            people = personas(client)
        app.state.engine.dispose()  # Windows cannot delete the temporary database while it is open
    evidence = Evidence(automation_share={}, automation_period="", automation_source="")
    return {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "version": _version(),
        "coverage": coverage(),
        "personas": people,
        "fairness": paired_profile_check(load_pack(), evidence),
        "time_to_plan": _measured_time_to_plan(),
    }


def _measured_time_to_plan() -> dict[str, Any] | None:
    """From the app's own database (local or the DATABASE_URL set), never from the personas."""
    try:
        engine = make_engine(load_settings().database_url)
        try:
            return time_to_plan(engine)
        finally:
            engine.dispose()
    except Exception:  # noqa: BLE001  no database yet: the section says so
        return None


def _time_line(t: dict[str, Any] | None) -> str:
    if not t or not t["people"]:
        return (
            "- No timed journey in this database yet (the intake records it for each new profile)."
        )
    share = t["under_target"] / t["people"]
    return (
        f"- **{share:.0%}** of {t['people']} timed journeys reached ranked roles and a chosen plan "
        f"within {t['target_seconds'] // 60} minutes (target {t['target_share']:.0%}); median "
        f"{t['median_seconds']} s. Observed from the app's database (src/journey/impact.py)."
    )


def render(k: dict[str, Any]) -> str:
    cov = k["coverage"]
    status = "meets" if cov["share"] >= cov["target"] else "is below"
    total = sum(p["numbers"] for p in k["personas"])
    labelled = total - sum(len(p["unlabelled"]) for p in k["personas"])
    fair = k["fairness"]
    lines = [
        "# KPI results (generated)",
        "",
        f"Generated by `python -m scripts.kpis` on {k['generated']} from commit `{k['version']}`. "
        "Do not edit by hand: re-run the script.",
        "",
        "## 1. Verified free-course coverage of the required skills",
        "",
        f"- **{cov['covered']}/{cov['denominator']} ({cov['share']:.0%})** of the Phase 1 required "
        f"skills have at least one verified free course. Phase 1 baseline: "
        f"{cov['baseline']}/{cov['denominator']}. Target: at least {cov['target_count']}/"
        f"{cov['denominator']} ({cov['target']:.0%}); the figure {status} the target.",
        f"- Still without a verified free course: {'; '.join(cov['uncovered']) or 'none'}.",
        f"- Catalogue: {cov['verified_courses']} verified courses (checked "
        f"{cov['catalogue_checked']}); unverified candidates, never planned and not counted: "
        f"{cov['candidate_courses']}.",
        "- Required skills added since Phase 1 (reported apart, not in the figure above): "
        + (
            "; ".join(
                f"{n} ({'covered' if c else 'no verified course'})" for n, c in cov["added_skills"]
            )
            or "none."
        ),
        "",
        "## 2. Free share of each persona's plan",
        "",
        "| Persona | Top role | Fit | Study hours | Free share |",
        "|---|---|---|---|---|",
        *(
            f"| {p['persona'].title()} | {p['role']} | {p['fit']} | {p['study_hours']} | "
            + (f"{p['free_share']:.0%}" if p["free_share"] is not None else "no study steps")
            + " |"
            for p in k["personas"]
        ),
        "",
        f"Basis: {k['personas'][0]['free_share_basis']} Personas: synthetic, fixed levels from "
        "data/samples/personas.yaml.",
        "",
        "## 3. Numbers shown with a source or a label (C2 role score and C3 plan)",
        "",
        f"- **{labelled}/{total} ({labelled / total:.0%})** of the numbers in the four personas' "
        "top role card and plan carry a source or a label (src/match/labels.py).",
        *(
            f"- Unlabelled for {p['persona'].title()}: {', '.join(p['unlabelled'])}"
            for p in k["personas"]
            if p["unlabelled"]
        ),
        "",
        "## 4. Fairness (paired profiles, C10)",
        "",
        f"- {fair['pairs']} pairs of synthetic CVs that differ only in protected attributes: "
        f"results {'identical' if fair['identical'] else 'NOT identical'}, largest fit difference "
        f"{fair['max_fit_difference']} points (checked {fair['checked_at']}).",
        "",
        "## 5. Time to ranked roles and a plan (Phase 1 target: 80% within 5 minutes)",
        "",
        _time_line(k["time_to_plan"]),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT.write_text(render(compute()), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
