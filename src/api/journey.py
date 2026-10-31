"""Journey routes: intake, profiles, matched roles, destination, pathway, Today → Future you."""

import json
from dataclasses import asdict
from typing import Any

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import Engine, select

from src import params
from src.api.evidence import get_engine, get_settings
from src.changes.store import accepted_rows, baseline_cutoff
from src.collectors.talentcorp import load_extraction
from src.config import REPO_ROOT, Settings
from src.evidence.signals import build_signals, job_ad_signals, occupation_signals
from src.intake.extract import extract
from src.intake.files import UnsupportedFileError, read_cv
from src.intake.skill_search import search, warm
from src.journey.events import record_claim_changes, record_event
from src.journey.progress import get_progress
from src.journey.store import (
    ProfileData,
    choose_destination,
    create_profile,
    get_profile,
    update_profile,
)
from src.levels import load_levels
from src.match.decision import (
    band,
    components,
    essentials_short,
    fit_range,
    meters,
    raise_options,
)
from src.match.engine import Evidence, RoleMatch, Scenario, rank_roles, score_role
from src.match.evidence import automation_evidence
from src.match.explain import explain, facts
from src.match.outlook import role_outlook
from src.match.pay import role_pay
from src.match.radar import radar
from src.match.tasks import task_view
from src.occupations.catalogue import catalogue_table
from src.pack import Pack, load_pack
from src.pathway.planner import Pathway, apply_progress, plan_pathway
from src.pathway.sdg import role_targets
from src.pathway.tracks import build_tracks, comparison
from src.resources import load_resources

router = APIRouter(prefix="/api")

SAMPLES_DIR = REPO_ROOT / "data" / "samples"
SAMPLES = {
    "nur": "Nur · cash application analyst",
    "hafiz": "Hafiz · accounting graduate",
    "mei": "Mei · retail supervisor",
    "kavitha": "Kavitha · senior reporting analyst",
}
PERSONAS_FILE = SAMPLES_DIR / "personas.yaml"  # fixed levels for the persona test and KPIs
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


def load_personas() -> dict[str, dict[str, Any]]:
    """The four personas' situation and fixed levels, each quoting their synthetic CV."""
    personas: dict[str, dict[str, Any]] = yaml.safe_load(PERSONAS_FILE.read_text(encoding="utf-8"))[
        "personas"
    ]
    return personas


def evidence_for(engine: Engine, profile_id: str) -> Evidence:
    return automation_evidence(accepted_rows(engine, profile_id))


def require_profile(engine: Engine, profile_id: str) -> tuple[ProfileData, str | None]:
    found = get_profile(engine, profile_id)
    if found is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return found


def _task_examples(pack: Pack, engine: Engine) -> list[dict[str, str]]:
    """Use a role's own crosswalk; otherwise its stored O*NET core tasks, never another role."""
    socs = {r.soc for r in pack.current_roles.values()}
    with engine.connect() as conn:
        rows = conn.execute(select(catalogue_table).where(catalogue_table.c.soc.in_(socs)))
        catalogue = {r["soc"]: dict(r) for r in rows.mappings()}
    examples: list[dict[str, str]] = []
    for role in pack.current_roles.values():
        occupation = pack.tasks.occupations.get(role.soc)
        stored = catalogue.get(role.soc)
        if occupation:
            texts = [t.text for ts in occupation.skills.values() for t in ts]
            source = pack.tasks.source
        elif stored:
            texts = [t["text"] for t in json.loads(stored["tasks"])]
            source = f"O*NET {stored['release']} core tasks · fetched {stored['updated_at'].date()}"
        else:
            continue
        examples.extend(
            {
                "role_id": role.id,
                "soc": role.soc,
                "text": text,
                "source": source,
                "url": pack.tasks.source_url,
            }
            for text in list(dict.fromkeys(texts))[:3]
        )
    return examples


def _levels_out() -> dict[str, Any]:
    """C1: the 0–5 scale, its rules, and each skill's "I can…" sentences with their basis."""
    levels = load_levels()
    return {
        "checked": levels.checked,
        "scale": [s.model_dump() for s in levels.scale],
        "rules": levels.rules,
        "skills": {
            skill_id: {
                "anchors": {str(n): text for n, text in s.anchors.items()},
                "basis": [b.model_dump() for b in s.basis],
                "status": s.status,
            }
            for skill_id, s in levels.skills.items()
        },
    }


@router.get("/pack")
def pack_info(engine: Engine = Depends(get_engine)) -> dict[str, Any]:
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
        "levels": _levels_out(),
        "courses_checked": pack.courses_checked,
        "task_examples": _task_examples(pack, engine),
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


@router.post("/skills/warm")
def skill_search_warm(settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    """Start embedding the skills (and waking the GPU) before the person searches."""
    return {"started": warm(load_pack(), settings)}


@router.post("/profiles", status_code=201)
def new_profile(data: ProfileData, engine: Engine = Depends(get_engine)) -> ProfileCreated:
    _check_profile(load_pack(), data)
    profile_id = create_profile(engine, data)
    baseline_cutoff(engine, profile_id)
    record_claim_changes(engine, profile_id, {}, _claim_states(data))
    return ProfileCreated(id=profile_id)


@router.get("/profiles/{profile_id}")
def read_profile(profile_id: str, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    data, destination = require_profile(engine, profile_id)
    return {"profile": data.model_dump(), "destination": destination}


@router.put("/profiles/{profile_id}")
def edit_profile(
    profile_id: str, data: ProfileData, engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    old, _ = require_profile(engine, profile_id)
    _check_profile(load_pack(), data)
    update_profile(engine, profile_id, data)
    record_claim_changes(engine, profile_id, _claim_states(old), _claim_states(data))
    return {"profile": data.model_dump()}


def _claim_states(data: ProfileData) -> dict[str, tuple[int | None, str]]:
    return {skill: (claim.level, claim.source) for skill, claim in data.skills.items()}


def _check_profile(pack: Pack, data: ProfileData) -> None:
    unknown = [s for s in data.skills if s not in pack.skills]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown skills: {', '.join(unknown)}")
    if data.current_role != "other" and data.current_role not in pack.current_roles:
        raise HTTPException(status_code=422, detail="unknown current role")


def _role_sdgs(pack: Pack, match: RoleMatch) -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    links = list(pack.sdg.for_role(match.role_id))
    for req in match.requirements:
        if req.tier == "upskill":
            links += pack.sdg.for_skill(req.skill, pack.skills[req.skill].kind)
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
    scenario: Scenario,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    role = pack.destination_roles[match.role_id]
    levels = data.levels()
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
        "meters": meters(match),
        "fit_range": fit_range(pack, match, levels, scenario, evidence, data.skills),
        "band": band(match.fit),
        "band_basis": "assumption",
        "components": components(match, data.skills),
        "raise": raise_options(pack, match, levels, scenario, evidence, data.skills),
        "essentials_short": essentials_short(match),
        "pay": role_pay(role, rows),
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
            scenario,
            rows,
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
        # B7: roles × SDG targets with reasons, so roles can be compared by contribution.
        "sdg_roles": [r.model_dump() for r in role_targets(pack)],
        "bands": {
            "thresholds": params.BAND_THRESHOLDS,
            "below": params.BAND_BELOW,
            "kind": "assumption",
        },
    }


@router.post("/profiles/{profile_id}/destination")
def set_destination(
    profile_id: str, body: dict[str, str], engine: Engine = Depends(get_engine)
) -> dict[str, str]:
    _, before = require_profile(engine, profile_id)
    role_id = body.get("role_id", "")
    if role_id not in load_pack().destination_roles:
        raise HTTPException(status_code=422, detail="unknown destination role")
    choose_destination(engine, profile_id, role_id)
    if role_id != before:
        record_event(engine, profile_id, "destination_chosen", role_id, before, role_id)
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
    path = plan_pathway(
        pack,
        match,
        data.levels(),
        data.weekly_hours,
        scenario,
        evidence,
        data.skills,
        data.situation,
    )
    saved = get_progress(engine, profile_id)
    apply_progress(path, saved["done"], saved["skipped"], data.skills)
    out = asdict(path)
    out["sdg_targets"] = {k: v.model_dump() for k, v in pack.sdg.targets.items()}
    out["sdg_source"] = pack.sdg.source
    out["courses_checked"] = pack.courses_checked
    out["scenario"] = scenario
    return out


@router.get("/profiles/{profile_id}/tracks")
def tracks(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """My plan as AI basics, reskilling without AI and with AI, plus the route comparison."""
    data, destination = require_profile(engine, profile_id)
    chosen = _destination_or_query(destination, None)
    pack = load_pack()
    res = load_resources()
    evidence = evidence_for(engine, profile_id)
    match = score_role(pack, pack.destination_roles[chosen], data.levels(), scenario, evidence)
    path = plan_pathway(
        pack,
        match,
        data.levels(),
        data.weekly_hours,
        scenario,
        evidence,
        data.skills,
        data.situation,
    )
    saved = get_progress(engine, profile_id)
    done = saved["done"]
    apply_progress(path, done, saved["skipped"], data.skills)
    return {
        "role_id": chosen,
        "role_title": match.title,
        "scenario": scenario,
        "weekly_hours": data.weekly_hours,
        "tracks": build_tracks(pack, res, match, path, done),
        "comparison": comparison(
            pack,
            res,
            data.levels(),
            chosen,
            data.weekly_hours,
            evidence,
            path.ai_basics["shown"],
        ),
        "resources_checked": res.checked,
        "courses_checked": pack.courses_checked,
    }


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


def _top_roles(
    pack: Pack, levels: dict[str, int | None], scenario: Scenario, evidence: Evidence
) -> list[dict[str, Any]]:
    ranked = rank_roles(pack, levels, scenario, evidence)[: params.FUTURE_ROLES_SHOWN]
    return [{"role_id": m.role_id, "title": m.title, "fit": m.fit} for m in ranked]


def _talentcorp_market() -> dict[str, Any]:
    """In-demand skills and emerging roles as TalentCorp names them (expert view, with pages)."""
    data = load_extraction()
    skills = data["in_demand_skills"]
    return {
        "source": "TalentCorp (2024), Impact Study of AI, Digital and Green Economy: GBS",
        "published": str(data["published"]),
        "in_demand": {"ai_digital": skills["ai_digital"], "green": skills["green"]},
        "in_demand_page": skills["pdf_page"],
        "emerging_roles": data["emerging_roles"]["roles"],
        "emerging_page": data["emerging_roles"]["pdf_page"],
    }


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
        # Projected levels if the plan is finished (estimate): the higher of claim and plan.
        levels_after = {**levels, **{k: max(v, levels.get(k) or 0) for k, v in after.items()}}
        by_scenario[scenario] = {
            "roles_now": _top_roles(pack, levels, scenario, evidence),
            "roles_after": _top_roles(pack, levels_after, scenario, evidence),
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
        "skills_now": [
            {"skill": sid, "name": pack.skills[sid].name, "level": level}
            for sid, level in sorted(levels.items(), key=lambda kv: -(kv[1] or 0))
            if level is not None and sid in pack.skills
        ],
        "market": _talentcorp_market(),
        "destination": {"id": role.id, "title": role.title},
        "current_role": current.title if current else None,
        "situation": data.situation,
        "years_experience": data.years_experience,
        "scenarios": by_scenario,
    }
