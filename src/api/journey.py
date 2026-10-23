"""Journey routes: intake, profiles, matched roles, destination, pathway, Today → Future you."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src import params
from src.api.evidence import get_engine, get_settings
from src.changes.store import accepted_rows, baseline_cutoff
from src.config import REPO_ROOT, Settings
from src.evidence.signals import build_signals, job_ad_signals, occupation_signals
from src.intake.extract import extract
from src.intake.files import UnsupportedFileError, read_cv
from src.intake.skill_search import search
from src.journey.store import (
    ProfileData,
    choose_destination,
    create_profile,
    get_profile,
    update_profile,
)
from src.match.engine import Evidence, RoleMatch, Scenario, rank_roles, score_role
from src.match.evidence import automation_evidence
from src.match.explain import explain, facts
from src.match.outlook import role_outlook
from src.match.radar import radar
from src.match.tasks import task_view
from src.pack import Pack, load_pack
from src.pathway.planner import Pathway, plan_pathway

router = APIRouter(prefix="/api")

SAMPLES_DIR = REPO_ROOT / "data" / "samples"
SAMPLES = {
    "nur": "Nur · cash application analyst",
    "hafiz": "Hafiz · accounting graduate",
    "mei": "Mei · retail supervisor",
}
MAX_TEXT_CHARS = 20_000
SCENARIO_LABEL = {"moderate": "Moderate AI adoption", "fast": "Fast AI adoption"}
IMPACT_MEANING = {  # TalentCorp (2024) PDF p. 25, "Role and Skills Analysis by Impact Level"
    "high": "highly impacted: need to pivot to an adjacent role and reskill",
    "medium": "medium impact: roles are evolving; upskill to deliver beyond the traditional role",
    "low": "low impact: keep improving to stay relevant",
}


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


class ProfileCreated(BaseModel):
    id: str


def evidence_for(engine: Engine, profile_id: str) -> Evidence:
    return automation_evidence(accepted_rows(engine, profile_id))


def require_profile(engine: Engine, profile_id: str) -> tuple[ProfileData, str | None]:
    found = get_profile(engine, profile_id)
    if found is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return found


@router.get("/pack")
def pack_info() -> dict[str, Any]:
    pack = load_pack()
    return {
        "field": "GBS finance & accounting (Malaysia)",
        "skills": [s.model_dump() for s in pack.skills.values()],
        "current_roles": [r.model_dump() for r in pack.current_roles.values()],
        "destination_roles": [
            {"id": r.id, "title": r.title} for r in pack.destination_roles.values()
        ],
        "samples": [{"id": k, "label": v} for k, v in SAMPLES.items()],
        "proficiency": list(params.PROFICIENCY_LABELS),
        "courses_checked": pack.courses_checked,
    }


@router.get("/samples/{sample_id}")
def sample(sample_id: str) -> dict[str, str]:
    if sample_id not in SAMPLES:
        raise HTTPException(status_code=404, detail="unknown sample")
    return {
        "id": sample_id,
        "label": SAMPLES[sample_id],
        "text": (SAMPLES_DIR / f"{sample_id}.txt").read_text(encoding="utf-8"),
    }


def _extraction_out(text: str, settings: Settings) -> dict[str, Any]:
    result = extract(load_pack(), text, settings)
    return asdict(result)


@router.post("/intake/parse")
def parse_text(body: TextIn, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return _extraction_out(body.text, settings)


@router.post("/intake/upload")
async def parse_upload(
    file: UploadFile = File(...), settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    try:
        text = read_cv(file.filename or "", await file.read())
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    if not text.strip():
        raise HTTPException(status_code=422, detail="no text could be read from this file")
    return _extraction_out(text, settings)


@router.post("/skills/search")
def skill_search(body: TextIn, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return asdict(search(load_pack(), body.text, settings))


@router.post("/profiles", status_code=201)
def new_profile(data: ProfileData, engine: Engine = Depends(get_engine)) -> ProfileCreated:
    _check_profile(load_pack(), data)
    profile_id = create_profile(engine, data)
    baseline_cutoff(engine, profile_id)
    return ProfileCreated(id=profile_id)


@router.get("/profiles/{profile_id}")
def read_profile(profile_id: str, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    data, destination = require_profile(engine, profile_id)
    return {"profile": data.model_dump(), "destination": destination}


@router.put("/profiles/{profile_id}")
def edit_profile(
    profile_id: str, data: ProfileData, engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    require_profile(engine, profile_id)
    _check_profile(load_pack(), data)
    update_profile(engine, profile_id, data)
    return {"profile": data.model_dump()}


def _check_profile(pack: Pack, data: ProfileData) -> None:
    unknown = [s for s in data.skills if s not in pack.skills]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown skills: {', '.join(unknown)}")
    if data.current_role != "other" and data.current_role not in pack.current_roles:
        raise HTTPException(status_code=422, detail="unknown current role")


def _role_sdgs(pack: Pack, match: RoleMatch) -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    links = list(pack.sdg.destination)
    for req in match.requirements:
        if req.tier == "upskill":
            links += pack.sdg.skill_kinds[pack.skills[req.skill].kind]
    for link in links:
        seen.setdefault(
            link.target,
            {"target": link.target, "title": pack.sdg.targets[link.target].title, "how": link.how},
        )
    return list(seen.values())


def _card(
    pack: Pack,
    match: RoleMatch,
    data: ProfileData,
    path: Pathway,
    evidence: Evidence,
    demand: list[dict[str, str]],
) -> dict[str, Any]:
    role = pack.destination_roles[match.role_id]
    current = pack.current_roles.get(data.current_role)
    outlook = [
        {
            "kind": "expert",
            "text": f"TalentCorp rates it {IMPACT_MEANING[role.impact]}.",
            "source": "TalentCorp (2024) GBS study, PDF p. 25–26",
        }
    ]
    if match.automation_share is not None:
        outlook.append(
            {
                "kind": "observed",
                "text": (
                    f"{match.automation_share:.0f}% of AI use for the matching occupation "
                    f"({role.soc}) is automation-style in the sampled Claude conversations."
                ),
                "source": f"{evidence.automation_source}, {evidence.automation_period}",
            }
        )
    return {
        **asdict(match),
        "impact": role.impact,
        "outlook": outlook + demand,
        "listed_transition": bool(current and match.role_id in current.transitions),
        "effort_hours": path.total_hours,
        "effort_weeks": path.weeks,
        "uncovered": path.uncovered,
        "sdgs": _role_sdgs(pack, match),
    }


@router.get("/profiles/{profile_id}/matches")
def matches(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    data, destination = require_profile(engine, profile_id)
    pack = load_pack()
    rows = accepted_rows(engine, profile_id)
    evidence = automation_evidence(rows)
    signals = occupation_signals(rows) + job_ad_signals(rows)
    levels = data.levels()
    ranked = rank_roles(pack, levels, scenario, evidence, set(data.interests) or None)
    cards = [
        _card(
            pack,
            m,
            data,
            plan_pathway(pack, m, levels, data.weekly_hours, scenario, evidence),
            evidence,
            role_outlook(pack, pack.destination_roles[m.role_id], rows, signals),
        )
        for m in ranked
    ]
    current = pack.current_roles.get(data.current_role)
    return {
        "scenario": scenario,
        "scenario_label": SCENARIO_LABEL[scenario],
        "horizon_years": params.SCENARIO_HORIZON_YEARS,
        "intensity": params.SCENARIO_INTENSITY[scenario],
        "evidence": {
            "source": evidence.automation_source,
            "period": evidence.automation_period,
            "occupations": len(evidence.automation_share),
        },
        "current_role": current.model_dump() if current else None,
        "current_impact": IMPACT_MEANING[current.impact] if current else None,
        "destination": destination,
        "roles": cards,
    }


@router.post("/profiles/{profile_id}/destination")
def set_destination(
    profile_id: str, body: dict[str, str], engine: Engine = Depends(get_engine)
) -> dict[str, str]:
    require_profile(engine, profile_id)
    role_id = body.get("role_id", "")
    if role_id not in load_pack().destination_roles:
        raise HTTPException(status_code=422, detail="unknown destination role")
    choose_destination(engine, profile_id, role_id)
    return {"destination": role_id}


def _destination_or_query(destination: str | None, role_id: str | None) -> str:
    chosen = role_id or destination
    if not chosen or chosen not in load_pack().destination_roles:
        raise HTTPException(status_code=409, detail="choose a destination role first")
    return chosen


@router.get("/profiles/{profile_id}/pathway")
def pathway(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    role_id: str | None = Query(default=None, max_length=64),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    data, destination = require_profile(engine, profile_id)
    chosen = _destination_or_query(destination, role_id)
    pack = load_pack()
    evidence = evidence_for(engine, profile_id)
    match = score_role(pack, pack.destination_roles[chosen], data.levels(), scenario, evidence)
    path = plan_pathway(pack, match, data.levels(), data.weekly_hours, scenario, evidence)
    out = asdict(path)
    out["sdg_targets"] = {k: v.model_dump() for k, v in pack.sdg.targets.items()}
    out["sdg_source"] = pack.sdg.source
    out["courses_checked"] = pack.courses_checked
    out["scenario"] = scenario
    return out


@router.get("/profiles/{profile_id}/roles/{role_id}/explain")
def explain_role(
    profile_id: str,
    role_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Plain-language sentences about one computed role result, each tied to the facts it uses."""
    data, _ = require_profile(engine, profile_id)
    pack = load_pack()
    role = pack.destination_roles.get(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="unknown destination role")
    rows = accepted_rows(engine, profile_id)
    evidence = automation_evidence(rows)
    levels = data.levels()
    match = score_role(pack, role, levels, scenario, evidence)
    path = plan_pathway(pack, match, levels, data.weekly_hours, scenario, evidence)
    return explain(facts(match, path, SCENARIO_LABEL[scenario]), settings)


@router.get("/profiles/{profile_id}/radar")
def personal_radar(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """The chosen (or best-fitting) role's skills for this person, and their field's signals."""
    data, destination = require_profile(engine, profile_id)
    pack = load_pack()
    rows = accepted_rows(engine, profile_id)
    evidence = automation_evidence(rows)
    levels = data.levels()
    if destination:
        match = score_role(pack, pack.destination_roles[destination], levels, scenario, evidence)
    else:
        match = rank_roles(pack, levels, scenario, evidence, set(data.interests) or None)[0]
    path = plan_pathway(pack, match, levels, data.weekly_hours, scenario, evidence)
    out = radar(pack, match, path, bool(destination), rows, build_signals(rows), data.current_role)
    return {**out, "scenario": scenario, "scenario_label": SCENARIO_LABEL[scenario]}


@router.get("/profiles/{profile_id}/roles/{role_id}/tasks")
def role_tasks(
    profile_id: str, role_id: str, engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    """The role's linked O*NET tasks with the four kinds of evidence, at the accepted cutoff."""
    require_profile(engine, profile_id)
    pack = load_pack()
    role = pack.destination_roles.get(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="unknown destination role")
    impact = f"TalentCorp rates it {IMPACT_MEANING[role.impact]}."
    return task_view(pack, role, accepted_rows(engine, profile_id), impact)


@router.get("/profiles/{profile_id}/future")
def future(
    profile_id: str,
    role_id: str | None = Query(default=None, max_length=64),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    data, destination = require_profile(engine, profile_id)
    chosen = _destination_or_query(destination, role_id)
    pack = load_pack()
    evidence = evidence_for(engine, profile_id)
    role = pack.destination_roles[chosen]
    levels = data.levels()
    by_scenario: dict[str, Any] = {}
    scenarios: tuple[Scenario, ...] = ("moderate", "fast")
    for scenario in scenarios:
        match = score_role(pack, role, levels, scenario, evidence)
        path = plan_pathway(pack, match, levels, data.weekly_hours, scenario, evidence)
        after = {g.skill: g.after for step in path.steps for g in step.gains}
        by_scenario[scenario] = {
            "fit_now": path.fit_before,
            "fit_after": path.fit_after,
            "hours": path.total_hours,
            "weeks": path.weeks,
            "skills": [
                {
                    "skill": r.skill,
                    "name": r.skill_name,
                    "required": r.required,
                    "now": r.claimed,
                    "after": max(after.get(r.skill, 0), r.claimed or 0),
                    "essential": r.essential,
                }
                for r in match.requirements
            ],
            "sdg_targets": sorted(path.sdg_summary),
            "uncovered": path.uncovered,
        }
    current = pack.current_roles.get(data.current_role)
    return {
        "destination": {"id": role.id, "title": role.title},
        "current_role": current.title if current else None,
        "situation": data.situation,
        "years_experience": data.years_experience,
        "scenarios": by_scenario,
    }
