"""Learning-plan route (pathway.md §4–5, Domain 1 must-have 4).

GET /api/learning-plan/{user_id}?role_id=&scenario=&swap=skill_id:course_id

The plan for the chosen role (default: the top-ranked one) from the pure build_learning_plan,
plus what the Pathway page needs around it: the role, the other top roles to switch to, details
of the alternative courses for "Swap", SDG targets per step (catalogue/sdg_map.json), the official
funding links, and the state of the course catalogue (verified vs drafts awaiting review).
"""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.api_engine import StoreDep, require_profile, states_for
from src.api_ranking import _read_signals
from src.engine.catalogue import default_catalogue
from src.engine.learning_plan import default_plan_config, plan_answers_for, plan_for_profile
from src.engine.questionnaire import default_questionnaire
from src.engine.ranking import default_scoring, rank_for_profile
from src.engine.resources import show_drafts

router = APIRouter(prefix="/api", tags=["learning plan"])
TOP_ROLES = 5

# Official pages only (checked 2026-10-23); the UI links to them and never hard-codes the rules.
FUNDING_LINKS = [
    {
        "label": "HRD Corp Claimable Courses (HCC)",
        "url": "https://hrdcorp.gov.my/hrdcorp-claimable-courses",
        "note": "Employers apply via e-TRiS before the training starts; "
        "approval is not guaranteed.",
    },
    {
        "label": "SBL-KHAS grant steps (HRD Corp support centre)",
        "url": "https://supportcentre.hrdcorp.gov.my/portal/en/kb/articles/hrd-corp-claimable-courses-sbl-khas-scheme",
        "note": "How an employer applies in e-TRiS (scheme code HRD CC).",
    },
    {
        "label": "e-LATiH FAQ (HRD Corp)",
        "url": "https://elatih.hrdcorp.gov.my/pages/faq",
        "note": "Open to all individuals; free and premium courses; certificate of completion.",
    },
    {
        "label": "Rakyat Digital: Coursera Global Learning Pass",
        "url": "https://rakyatdigital.gov.my/en/skills-hub",
        "note": "Three months of free Coursera access, funded by the Government of Malaysia.",
    },
    {
        "label": "AI untuk Rakyat (Ministry of Digital)",
        "url": "https://www.digital.gov.my/en-GB/siaran/Program-AI-Untuk-Rakyat-Bakal-Perkasa-100,000-Belia-Dengan-Akses-Kepada-Teknologi-AI-Secara-Percuma",
        "note": "Free for Malaysian citizens aged 18 to 30; six modules on Rakyat Digital.",
    },
]


def parse_swaps(swaps: list[str]) -> dict[str, str]:
    pins = {}
    for s in swaps:
        skill, _, course = s.partition(":")
        if not skill or not course:
            raise HTTPException(
                status_code=422, detail=f"swap must be skill_id:course_id, got {s!r}"
            )
        pins[skill] = course
    return pins


@router.get("/learning-plan/{user_id}")
def learning_plan(
    user_id: str,
    store: StoreDep,
    role_id: str | None = None,
    scenario: str | None = None,
    swap: list[str] = Query(default=[]),
) -> dict[str, Any]:
    profile = require_profile(store, user_id)
    catalogue = default_catalogue()
    states = states_for(profile, store.events_for(user_id), catalogue)
    snapshot = _read_signals() or {}
    ranking = rank_for_profile(profile, states, snapshot, scenario)
    courses = catalogue.courses
    drafts = sum(c.status == "draft" for c in courses.values())
    catalogue_state = {
        "verified": sum(c.status == "verified" for c in courses.values()),
        "drafts": drafts,
        "drafts_in_use": show_drafts(),
        "last_full_review": max(
            (c.last_verified or "" for c in courses.values() if c.status == "verified"),
            default=None,
        ),
    }
    if ranking.empty_profile:
        return {
            "user_id": user_id,
            "plan": None,
            "empty_profile": True,
            "message": ranking.message,
            "catalogue": catalogue_state,
            "funding_links": FUNDING_LINKS,
        }
    if role_id is not None and role_id not in {r.role_id for r in ranking.roles}:
        raise HTTPException(status_code=404, detail=f"unknown role {role_id}")
    plan = plan_for_profile(profile, role_id, states, snapshot, scenario, pins=parse_swaps(swap))
    assert plan is not None
    role = next(r for r in ranking.roles if r.role_id == plan.role_id)
    sdg = catalogue.sdg
    titles = {t.id: t.title for t in sdg.targets}
    alt_ids = {a for s in plan.steps for a in s.alternatives}
    steps = []
    for step in plan.steps:
        targets = sorted(
            {t for k in step.skill_ids if k in sdg.skills for t in sdg.skills[k].targets}
        )
        steps.append(
            {
                **asdict(step),
                "sdg_targets": [{"id": t, "title": titles.get(t, "")} for t in targets],
            }
        )
    answers = plan_answers_for(
        profile, default_questionnaire(), default_scoring(), default_plan_config()
    )
    return {
        "user_id": user_id,
        "empty_profile": False,
        "role": {
            "role_id": role.role_id,
            "name": role.name,
            "band": role.band,
            "score": role.score,
            "family_name": role.family,
            "gap_hours": role.gap_hours,
        },
        "other_roles": [
            {"role_id": r.role_id, "name": r.name, "band": r.band, "score": r.score}
            for r in ranking.roles[:TOP_ROLES]
        ],
        "plan": {**asdict(plan), "steps": steps},
        "alternatives": {
            cid: {
                "title": courses[cid].title,
                "provider": courses[cid].provider,
                "hours": courses[cid].hours,
                "cost_type": courses[cid].cost_type,
                "cost_myr": courses[cid].cost_myr,
                "status": courses[cid].status,
            }
            for cid in sorted(alt_ids)
            if cid in courses
        },
        "answers": {
            "weekly_hours": answers.weekly_hours,
            "timeframe_months": answers.timeframe_months,
            "timeframe_weeks": answers.timeframe_weeks,
            "budget": answers.budget,
            "employment": answers.employment,
            "employer_hrd": answers.employer_hrd,
            "ai_comfort": answers.ai_comfort,
        },
        "pins": parse_swaps(swap),
        "catalogue": catalogue_state,
        "funding_links": FUNDING_LINKS,
        "note": "A suggested plan from real, dated courses; you choose what to take. "
        "HRD Corp claims are never guaranteed.",
    }
