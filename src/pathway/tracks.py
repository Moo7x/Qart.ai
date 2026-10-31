"""My plan as three tracks, and the comparison of reskilling with and without AI.

1. AI basics: a declared foundation shown first (src/resources.py topics), because adapting to
   AI starts with knowing how to use it safely; skipped, with the reason, when the person shows
   AI or automation work with evidence (B5, planner.ai_basics_choice), and shown on request.
2. Reskilling without AI: the role's gaps in finance, business and green skills.
3. Reskilling with AI: the role's gaps in data and digital skills (params.AI_TRACK_KINDS).

Each skill is a node with its planned courses (from the pathway planner, unchanged), other free
courses, and the checked videos and articles. The comparison plans the role twice with the same
planner and the same course rules: once over the non-AI skills only, once over every skill plus
the AI-basics courses. Plan hours are only the planned study steps; the AI-basics hours are
reported apart (`plan_hours` + `ai_basics_hours` = the with-AI `hours`), never added silently.
Fit is scored by the same engine; every number here is an estimate from
declared rules, not a measured learning result. "With AI" means learning the AI-related skills,
not studying with an AI tutor.
"""

import math
from dataclasses import asdict, replace
from typing import Any

from src import params
from src.match.engine import Evidence, RoleMatch, Scenario, score_role
from src.pack import Course, Pack
from src.pathway.planner import Pathway, plan_pathway
from src.resources import Article, Resources, Video

MINUTES_PER_HOUR = 60
SCENARIOS: tuple[Scenario, ...] = ("moderate", "fast")


def is_ai_skill(pack: Pack, skill: str) -> bool:
    return pack.skills[skill].kind in params.AI_TRACK_KINDS


def _course(c: Course, planned: set[str], done: list[str]) -> dict[str, Any]:
    return {
        "id": c.id,
        "title": c.title,
        "provider": c.provider,
        "url": c.url,
        "minutes": c.minutes,
        "level": c.level,
        "planned": c.id in planned,
        "done": c.id in done,
        # How a catalogue candidate's fit was checked (None: checked by hand when it was added).
        "fit_check": c.fit_check.model_dump() if c.fit_check else None,
    }


def _video(v: Video) -> dict[str, Any]:
    return {
        "id": v.id,
        "title": v.title,
        "channel": v.channel,
        "url": v.url,
        "minutes": v.minutes,
        "published": v.published,
    }


def _article(a: Article) -> dict[str, Any]:
    return {"id": a.id, "title": a.title, "publisher": a.publisher, "url": a.url}


def _status(courses: list[dict[str, Any]]) -> str:
    planned = [c for c in courses if c["planned"]]
    if not courses:
        return "no_course"
    if planned and all(c["done"] for c in planned):
        return "done"
    return "open"


def _skill_nodes(
    pack: Pack, res: Resources, match: RoleMatch, path: Pathway, done: list[str], ai: bool
) -> list[dict[str, Any]]:
    planned = {s.course.id for s in path.steps}
    order = {s.course.id: s.order for s in path.steps}
    after = {g.skill: g.after for s in path.steps for g in s.gains}
    gaps = [r for r in match.requirements if (r.claimed or 0) < r.required]
    nodes = []
    for r in gaps:
        if is_ai_skill(pack, r.skill) != ai:
            continue
        courses = sorted(
            (_course(c, planned, done) for c in pack.courses_for(r.skill)),
            key=lambda c: (not c["planned"], order.get(c["id"], 999), c["minutes"]),
        )
        first = min((order[c["id"]] for c in courses if c["planned"]), default=999)
        nodes.append(
            {
                "id": r.skill,
                "title": r.skill_name,
                "skill": r.skill,
                "essential": r.essential,
                "now": r.claimed,
                "required": r.required,
                "after": after.get(r.skill, r.claimed),
                # B4: the level study can give here, and the practice steps above it (C3).
                "study_after": path.study_levels.get(r.skill, r.claimed),
                "practice": [asdict(p) for p in path.practice_steps if p.skill == r.skill],
                "courses": courses,
                "videos": [_video(v) for v in res.videos_for(skill=r.skill)],
                "articles": [_article(a) for a in res.articles_for(skill=r.skill)],
                "status": _status(courses),
                "_order": first,
            }
        )
    nodes.sort(key=lambda n: (n["_order"], not n["essential"]))
    for n in nodes:
        del n["_order"]
    return nodes


def _basics_nodes(pack: Pack, res: Resources, done: list[str]) -> list[dict[str, Any]]:
    nodes = []
    for t in res.ai_basics:
        ids = set(t.courses)
        courses = [_course(pack.courses[c], ids, done) for c in t.courses]
        nodes.append(
            {
                "id": t.id,
                "title": t.title,
                "skill": t.skill,
                "essential": False,
                "now": None,
                "required": None,
                "after": None,
                "courses": courses,
                "videos": [_video(v) for v in res.videos_for(skill=t.skill, topic=t.id)],
                "articles": [_article(a) for a in res.articles_for(skill=t.skill, topic=t.id)],
                "status": _status(courses),
            }
        )
    return nodes


def _metrics(
    hours: float,
    weekly_hours: float,
    fit_now: dict[str, float],
    fit_after: dict[str, float],
    courses: int,
    essentials: list[str],
) -> dict[str, Any]:
    return {
        "hours": round(hours, 1),
        "weeks": math.ceil(hours / weekly_hours) if hours else 0,
        "courses": courses,
        "fit_after": {s: round(fit_after[s], 1) for s in SCENARIOS},
        # Fit points gained per 10 hours of study: the efficiency of the time spent (estimate).
        "points_per_10h": {
            s: round(10 * (fit_after[s] - fit_now[s]) / hours, 1) if hours else 0.0
            for s in SCENARIOS
        },
        "essentials_unmet": essentials,
    }


def comparison(
    pack: Pack,
    res: Resources,
    levels: dict[str, int | None],
    role_id: str,
    weekly_hours: float,
    evidence: Evidence,
    ai_basics_shown: bool = True,
) -> dict[str, Any]:
    role = pack.destination_roles[role_id]
    fit_now: dict[str, float] = {}
    without: dict[Scenario, Pathway] = {}
    full: dict[Scenario, Pathway] = {}
    for s in SCENARIOS:
        match = score_role(pack, role, levels, s, evidence)
        fit_now[s] = match.fit
        domain = replace(
            match, requirements=[r for r in match.requirements if not is_ai_skill(pack, r.skill)]
        )
        without[s] = plan_pathway(pack, domain, levels, weekly_hours, s, evidence)
        full[s] = plan_pathway(pack, match, levels, weekly_hours, s, evidence)
    # AI-basics courses not already in the full plan add their hours to the "with AI" route.
    in_plan = {st.course.id for st in full["moderate"].steps}
    # Skipped AI basics (B5) add nothing to the with-AI route.
    basics = {c for t in res.ai_basics for c in t.courses} - in_plan if ai_basics_shown else set()
    # Rounded before adding, so the two parts shown always add up to the with-AI total.
    basics_hours = round(sum(pack.courses[c].minutes for c in basics) / MINUTES_PER_HOUR, 1)
    w = without["moderate"]
    f = full["moderate"]
    return {
        "fit_now": {s: round(fit_now[s], 1) for s in SCENARIOS},
        "without_ai": _metrics(
            w.total_hours,
            weekly_hours,
            fit_now,
            {s: without[s].fit_after for s in SCENARIOS},
            len(w.steps),
            w.essentials_unmet,
        ),
        "with_ai": {
            **_metrics(
                f.total_hours + basics_hours,
                weekly_hours,
                fit_now,
                {s: full[s].fit_after for s in SCENARIOS},
                len(f.steps) + len(basics),
                f.essentials_unmet,
            ),
            # The two parts of the with-AI hours, named so no screen adds them silently.
            "plan_hours": f.total_hours,
            "ai_basics_hours": basics_hours,
        },
        "note": (
            "Both routes use the same free courses, planner and course rules; fit is scored by "
            "the same engine. The with-AI time is the plan's study steps plus the AI-basics "
            "courses, named separately; AI basics change fit only where the role lists those "
            "skills. Estimates, not measured learning results."
        ),
    }


def build_tracks(
    pack: Pack,
    res: Resources,
    match: RoleMatch,
    path: Pathway,
    done: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "ai_basics",
            "title": "AI basics",
            "why": "Start here: adapting to AI begins with knowing what it is and how to use it "
            "safely.",
            "nodes": _basics_nodes(pack, res, done),
            # B5: false when skipped for this person; the nodes stay for "Show AI basics anyway".
            "shown": path.ai_basics.get("shown", True),
            "reason": path.ai_basics.get("reason", ""),
        },
        {
            "id": "without_ai",
            "title": "Reskilling without AI",
            "why": "Finance, business and green skills the role needs that you have not reached "
            "yet.",
            "nodes": _skill_nodes(pack, res, match, path, done, ai=False),
        },
        {
            "id": "with_ai",
            "title": "Reskilling with AI",
            "why": "Data and digital skills the role needs: the work that grows as routine steps "
            "are automated.",
            "nodes": _skill_nodes(pack, res, match, path, done, ai=True),
        },
    ]
