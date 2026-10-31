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
from src.api.schemas import FutureOut, MatchesOut, RadarOut, ReskillOut, TracksOut
from src.changes.store import baseline_cutoff
from src.collectors.talentcorp import load_extraction
from src.config import REPO_ROOT, Settings
from src.evidence.signals import build_signals, job_ad_signals, occupation_signals
from src.intake.extract import extract
from src.intake.files import UnsupportedFileError, read_cv
from src.intake.skill_search import search, warm
from src.journey.events import record_claim_changes, record_event
from src.journey.person import Person, load_person
from src.journey.progress import get_progress
from src.journey.store import (
    ProfileData,
    SkillClaim,
    choose_destination,
    create_profile,
    get_profile,
    update_profile,
)
from src.levels import load_levels
from src.match import directions
from src.match.basis import requirement_basis
from src.match.decision import (
    band,
    components,
    essentials_short,
    fit_range,
    meters,
    raise_options,
)
from src.match.engine import Evidence, RoleMatch, Scenario, rank_roles
from src.match.explain import explain, facts
from src.match.outlook import in_demand_skills, role_outlook
from src.match.pay import role_pay
from src.match.radar import radar
from src.match.tasks import task_view
from src.occupations.catalogue import catalogue_table
from src.pack import Pack, load_pack
from src.pathway.planner import Pathway, PathwayOut, ai_basics_choice, apply_progress, pathway_out
from src.pathway.reskill import current_job_path, destination_path
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


def require_person(engine: Engine, profile_id: str) -> Person:
    person = load_person(engine, profile_id)
    if person is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return person


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
    person: Person,
    match: RoleMatch,
    path: Pathway,
    demand: list[dict[str, str]],
    scenario: Scenario,
    forecasts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pack, data, evidence, rows = person.pack, person.data, person.evidence, person.card_rows
    role = pack.destination_roles[match.role_id]
    current = pack.current_roles.get(data.current_role)
    forecast = (forecasts or {}).get(match.role_id)
    tier = directions.related_tier(rows, current.soc if current else None, role.soc)
    outlook = [
        {
            "kind": "expert",
            "text": f"TalentCorp rates it {IMPACT_MEANING[role.impact]}.",
            "source": role.study_source,
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
        "fit_range": fit_range(pack, match, data.skills, scenario, evidence),
        "band": band(match.fit),
        "band_basis": "assumption",
        "components": components(match, data.skills),
        "raise": raise_options(pack, match, data.skills, scenario, evidence),
        "essentials_short": essentials_short(match),
        "pay": role_pay(role, rows),
        "listed_transition": bool(current and match.role_id in current.transitions),
        "effort_hours": path.total_hours,
        "effort_weeks": path.weeks,
        "uncovered": path.uncovered,
        "sdgs": _role_sdgs(pack, match),
        # Why each skill is counted for this role (src/match/basis.py), keyed by skill id.
        "requirement_basis": {
            r.skill: requirement_basis(pack, match.role_id, r.skill, rows)
            for r in match.requirements
        },
        # Skills TalentCorp names as in demand (expert view, PDF p. 25): the row's trend line.
        "in_demand": in_demand_skills(pack, role, rows),
        # The person's chosen goals this role serves (they order near-ties; fit is unchanged).
        # Where the role is heading (industry forecast, estimate), how close the move is, and the
        # score the roles are ordered by (fit x outlook factor; the fit itself is unchanged).
        "forecast": directions.summary(forecast),
        "direction": directions.direction(match.fit, tier),
        "related_tier": tier,
        "direction_score": round(match.fit * directions.factor(forecast), 1),
        "serves_goals": sorted(
            {link.target.split(".")[0] for link in pack.sdg.for_role(match.role_id)}
            & set(data.sdg_priorities)
        ),
    }


@router.get("/profiles/{profile_id}/matches", response_model=MatchesOut)
def matches(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    person = require_person(engine, profile_id)
    pack, evidence, rows = person.pack, person.evidence, person.rows
    signals = occupation_signals(rows) + job_ad_signals(rows)
    forecasts = person.forecasts(scenario)
    cards = [
        _card(
            person,
            m,
            person.plan(m, scenario),
            role_outlook(pack, pack.destination_roles[m.role_id], person.card_rows, signals),
            scenario,
            forecasts,
        )
        for m in person.rank(scenario)
    ]
    current = pack.current_roles.get(person.data.current_role)
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
        # Where the person's own job is heading: the basis of the no-destination reskilling path.
        "current_forecast": directions.summary(forecasts.get(current.id)) if current else None,
        "destination": person.destination,
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


def chosen_role(person: Person, role_id: str | None = None) -> str:
    """The role asked for, else the person's destination; 409 when there is neither."""
    chosen = role_id or person.destination
    if not chosen or chosen not in person.pack.destination_roles:
        raise HTTPException(status_code=409, detail="choose a destination role first")
    return chosen


def _progressed_plan(
    engine: Engine, person: Person, role_id: str, scenario: Scenario
) -> tuple[RoleMatch, Pathway, list[str]]:
    """The person's plan with their saved progress applied, and every course they marked done
    (AI-basics courses too, which are not plan steps)."""
    match = person.score(role_id, scenario)
    saved = get_progress(engine, person.id)
    path = apply_progress(
        person.plan(match, scenario), saved["done"], saved["skipped"], person.data.skills
    )
    return match, path, saved["done"]


@router.get("/profiles/{profile_id}/pathway")
def pathway(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    role_id: str | None = Query(default=None, max_length=64),
    engine: Engine = Depends(get_engine),
) -> PathwayOut:
    person = require_person(engine, profile_id)
    _, path, _ = _progressed_plan(engine, person, chosen_role(person, role_id), scenario)
    return pathway_out(path, person.pack, scenario)


@router.get(
    "/profiles/{profile_id}/tracks", response_model=TracksOut, response_model_exclude_unset=True
)
def tracks(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """My plan as AI basics, reskilling without AI and with AI, plus the route comparison."""
    person = require_person(engine, profile_id)
    pack, data = person.pack, person.data
    chosen = chosen_role(person)
    res = load_resources()
    match, path, done = _progressed_plan(engine, person, chosen, scenario)
    return {
        "role_id": chosen,
        "role_title": match.title,
        "scenario": scenario,
        "weekly_hours": data.weekly_hours,
        "tracks": build_tracks(pack, res, match, path, done, person.rows),
        # The one path shown (src/pathway/reskill.py): basics, adapt held skills, learn the gaps.
        "path": destination_path(
            pack, res, match, path, done, person.rows, *_reskill_inputs(person, scenario)
        ),
        "comparison": comparison(
            pack, res, data.skills, chosen, data.weekly_hours, person.evidence, data.situation
        ),
        "resources_checked": res.checked,
        "courses_checked": pack.courses_checked,
    }


def _reskill_inputs(
    person: Person, scenario: Scenario
) -> tuple[str | None, dict[str, SkillClaim], list[dict[str, Any]], float, int | None]:
    """The current occupation, claims, task rows, scenario intensity and task-model version."""
    current = person.pack.current_roles.get(person.data.current_role)
    version = person.task_rows[0]["version_id"] if person.task_rows else None
    return (
        current.soc if current else None,
        dict(person.data.skills),
        person.task_rows,
        params.SCENARIO_INTENSITY[scenario],
        version,
    )


@router.get("/profiles/{profile_id}/reskill", response_model=ReskillOut)
def reskill(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """The path shown before a destination is chosen: the person's job's AI-era path."""
    person = require_person(engine, profile_id)
    pack, data = person.pack, person.data
    current = pack.current_roles.get(data.current_role)
    soc, claims, task_rows, intensity, version = _reskill_inputs(person, scenario)
    done: list[str] = []  # progress is recorded against a destination's plan, not this path
    track, strengths = current_job_path(
        pack,
        load_resources(),
        soc,
        claims,
        task_rows,
        intensity,
        version,
        ai_basics_choice(pack, data.skills, data.situation),
        done,
    )
    forecast = person.forecasts(scenario).get(current.id) if current else None
    return {
        "scenario": scenario,
        "current_role": current.title if current else None,
        "current_forecast": directions.summary(forecast),
        "track": track,
        "strengths": strengths,
        "destination": person.destination,
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
    person = require_person(engine, profile_id)
    if role_id not in person.pack.destination_roles:
        raise HTTPException(status_code=404, detail="unknown destination role")
    match = person.score(role_id, scenario)
    return explain(facts(match, person.plan(match, scenario), SCENARIO_LABEL[scenario]), settings)


@router.get("/profiles/{profile_id}/radar", response_model=RadarOut)
def personal_radar(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """The chosen (or best-fitting) role's skills for this person, and their field's signals."""
    person = require_person(engine, profile_id)
    destination, rows = person.destination, person.rows
    match = person.score(destination, scenario) if destination else person.rank(scenario)[0]
    path = person.plan(match, scenario)
    out = radar(
        person.pack,
        match,
        path,
        bool(destination),
        rows,
        build_signals(rows),
        person.data.current_role,
    )
    return {**out, "scenario": scenario, "scenario_label": SCENARIO_LABEL[scenario]}


@router.get("/profiles/{profile_id}/roles/{role_id}/tasks")
def role_tasks(
    profile_id: str, role_id: str, engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    """The role's linked O*NET tasks with the four kinds of evidence, at the accepted cutoff."""
    person = require_person(engine, profile_id)
    role = person.pack.destination_roles.get(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="unknown destination role")
    impact = f"TalentCorp rates it {IMPACT_MEANING[role.impact]}."
    return task_view(person.pack, role, person.rows, impact)


def _top_roles(
    pack: Pack, levels: dict[str, int | None], scenario: Scenario, evidence: Evidence
) -> list[dict[str, Any]]:
    """The best fits by fit alone (no ordering preferences): today against after the plan."""
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


@router.get("/profiles/{profile_id}/future", response_model=FutureOut)
def future(
    profile_id: str,
    role_id: str | None = Query(default=None, max_length=64),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    person = require_person(engine, profile_id)
    pack, data, evidence = person.pack, person.data, person.evidence
    role = pack.destination_roles[chosen_role(person, role_id)]
    levels = person.levels()
    by_scenario: dict[str, Any] = {}
    scenarios: tuple[Scenario, ...] = ("moderate", "fast")
    for scenario in scenarios:
        match = person.score(role.id, scenario)
        path = person.plan(match, scenario)
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
