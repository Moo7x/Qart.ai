"""One reskilling path, built from the skills the person already has and where AI is taking them.

Only one path is shown at a time:
* no destination chosen: **your job's AI-era path**. Each skill the person holds is measured on
  the O*NET tasks linked to it in their current occupation (automation-style AI use: observed in
  the Economic Index, else predicted by the task model, else the occupation's average), scaled by
  the scenario intensity, and gets one of three modes:
    oversee  routine work that AI already does in practice: the work that stays is checking AI
             output, handling exceptions and keeping controls;
    use_ai   work AI helps people do: learning to use AI on it is the step;
    keep     little AI use on these tasks: a human strength, shown but not a step.
  Steps are ordered by that AI pressure, highest first, after the AI basics.
* a destination chosen: **the path to that role**, which replaces the first one. Its steps are
  AI basics, the role's skills the person already meets but that AI is reshaping (adapt), and the
  role's gap skills (learn) in plan order. A skill can appear in both paths: finance roles are
  close.

Steps are never locked: each is a different skill, so the person can start anywhere. The mode
rules (thresholds and wording) are declared assumptions in src/params.py; the AI-use numbers are
observed or estimated and say which. Pure: the pack, resources, rows and claims in; dicts out.
"""

from collections.abc import Mapping
from typing import Any

from src import params
from src.journey.store import SkillClaim
from src.match.engine import RoleMatch
from src.pack import Pack
from src.pathway.planner import AiBasics, Pathway
from src.pathway.tracks import _article, _basics_nodes, _course, _skill_nodes, _status, _video
from src.resources import Resources, load_ai_resources

Row = dict[str, Any]
NO_AI_TITLE = "AI is changing this work"  # no checked AI resource for the skill yet
MODE_TITLE = {
    "oversee": "check and steer AI-run work",
    "use_ai": "do it faster with AI",
    "keep": "a human strength to keep",
}
MODE_TEXT = {
    "oversee": (
        "AI already does much of this work in practice. The part that stays with people is "
        "checking AI output, handling exceptions and keeping the controls."
    ),
    "use_ai": "AI helps people do this work. Learning to use it here keeps you ahead.",
    "keep": "Little AI use on these tasks so far: a human strength. Keep it visible on your CV.",
}
FRAMEWORK = (
    "Singapore Jobs Transformation Map, Generative AI in Financial Services "
    "(MAS, IBF, SWDA, 2025): "
    "roles with high automation potential are redesigned and their staff reskilled; for the "
    "others, proficiency in GenAI tools is essential"
)


def skill_pressure(
    pack: Pack, soc: str | None, skill: str, task_rows: list[Row], intensity: float
) -> tuple[float | None, str]:
    """Effective automation-style AI use on the skill's tasks (0-100) and what it rests on."""
    if soc is None:
        return None, "none"
    by_task = {(r["soc"], r["task"]): r for r in task_rows}

    def measured(socs: list[str]) -> tuple[list[float], list[float]]:
        observed, predicted = [], []
        for code in socs:
            for link in pack.tasks_for(code, skill):
                row = by_task.get((code, str(link.task)))
                if row is not None and row["observed"] is not None:
                    observed.append(row["observed"])
                elif row is not None and row["predicted"] is not None:
                    predicted.append(row["predicted"])
        return observed, predicted

    # The skill's own tasks in this occupation first; else the same skill's linked tasks in the
    # other followed finance occupations (the skill is the same work wherever it is done).
    for socs, where in (([soc], ""), (sorted(pack.tasks.occupations), "_field")):
        observed, predicted = measured(socs)
        values = observed + predicted
        if values:
            basis = "observed" if not predicted else "predicted" if not observed else "mixed"
            return round(intensity * sum(values) / len(values), 1), basis + where
    occupation = [
        r["observed"] if r["observed"] is not None else r["predicted"]
        for r in task_rows
        if r["soc"] == soc and (r["observed"] is not None or r["predicted"] is not None)
    ]
    if occupation:
        return round(intensity * sum(occupation) / len(occupation), 1), "occupation"
    return None, "none"


def mode_for(ai_role: str, effective: float | None) -> str:
    high = effective is not None and effective >= params.INDUSTRY_USE_HIGH
    if high and ai_role == "routine":
        return "oversee"
    if high or ai_role == "complement":
        return "use_ai"
    return "keep"


def _why(mode: str, effective: float | None, basis: str, model_version: int | None) -> Row:
    source = {
        "observed": "Anthropic Economic Index, automation-style share of task conversations",
        "predicted": f"Qart task model v{model_version} (estimate from the task's wording)",
        "mixed": f"Anthropic Economic Index and Qart task model v{model_version}",
        "observed_field": (
            "Anthropic Economic Index, the skill's tasks in other finance occupations"
        ),
        "predicted_field": f"Qart task model v{model_version}, the skill's tasks in other finance "
        "occupations (estimate)",
        "mixed_field": f"Economic Index and Qart task model v{model_version}, the skill's tasks in "
        "other finance occupations",
        "occupation": "average over the occupation's O*NET tasks (Economic Index and task model)",
        "none": "no AI-use data for these tasks",
    }[basis]
    measured = (
        f" {effective:.0f}% automation-style AI use on its tasks." if effective is not None else ""
    )
    return {
        "kind": "ai_trend",
        "text": f"{MODE_TEXT[mode]}{measured}",
        "source": f"{source}; modes after the {FRAMEWORK}",
    }


def adapt_nodes(
    pack: Pack,
    res: Resources,
    soc: str | None,
    claims: Mapping[str, SkillClaim],
    task_rows: list[Row],
    intensity: float,
    model_version: int | None,
    only: set[str] | None = None,
    done: list[str] | None = None,
) -> tuple[list[Row], list[Row]]:
    """Steps that adapt the skills the person holds to AI, and the skills kept as strengths."""
    steps: list[Row] = []
    strengths: list[Row] = []
    for skill_id, claim in claims.items():
        if (claim.level or 0) < 1 or skill_id not in pack.skills:
            continue
        if only is not None and skill_id not in only:
            continue
        skill = pack.skills[skill_id]
        effective, basis = skill_pressure(pack, soc, skill_id, task_rows, intensity)
        mode = mode_for(skill.ai_role, effective)
        if mode == "keep":
            strengths.append(
                {
                    "skill": skill_id,
                    "name": skill.name,
                    "level": claim.level,
                    "ai_use": effective,
                    "ai_basis": basis,
                    "text": MODE_TEXT["keep"],
                }
            )
            continue
        courses = [_course(c, set(), done or []) for c in pack.courses_for(skill_id)]
        # Resources about doing this skill's work with AI (checked; src/collectors/ai_resources.py).
        # Without one the step says so instead of promising an AI version it cannot show.
        ai_items = load_ai_resources().get(skill_id, [])
        why = _why(mode, effective, basis, model_version)
        if not ai_items:
            why["text"] += (
                " No checked resource on doing this with AI yet: start with the AI basics."
            )
        steps.append(
            {
                "id": f"adapt:{skill_id}",
                "title": f"{skill.name}: {MODE_TITLE[mode] if ai_items else NO_AI_TITLE}",
                "ai_resources": ai_items,
                "skill": skill_id,
                "essential": False,
                "now": claim.level,
                "required": None,
                "after": None,
                "courses": courses,
                "videos": [_video(v) for v in res.videos_for(skill=skill_id)],
                "articles": [_article(a) for a in res.articles_for(skill=skill_id)],
                "status": _status(courses),
                "why": why,
                "mode": mode,
                "ai_use": effective,
                "ai_basis": basis,
            }
        )
    steps.sort(key=lambda n: -(n["ai_use"] or 0))
    return steps, strengths


def _basics(pack: Pack, res: Resources, done: list[str], choice: AiBasics) -> list[Row]:
    if not choice.shown:
        return []
    return [{**n, "mode": "basics"} for n in _basics_nodes(pack, res, done)]


def current_job_path(
    pack: Pack,
    res: Resources,
    soc: str | None,
    claims: Mapping[str, SkillClaim],
    task_rows: list[Row],
    intensity: float,
    model_version: int | None,
    choice: AiBasics,
    done: list[str],
) -> tuple[Row, list[Row]]:
    """The no-destination path: AI basics, then the held skills AI is reshaping."""
    steps, strengths = adapt_nodes(
        pack, res, soc, claims, task_rows, intensity, model_version, done=done
    )
    track = {
        "id": "path",
        "title": "Your job's AI-era path",
        "why": (
            "Reskill the skills you already have for where your job is heading. Choose a role on "
            "My options to switch to that role's path."
        ),
        "nodes": _basics(pack, res, done, choice) + steps,
    }
    return track, strengths


def destination_path(
    pack: Pack,
    res: Resources,
    match: RoleMatch,
    path: Pathway,
    done: list[str],
    rows: list[Row],
    soc: str | None,
    claims: Mapping[str, SkillClaim],
    task_rows: list[Row],
    intensity: float,
    model_version: int | None,
) -> Row:
    """The path to a chosen role: basics, adapt the role's skills you meet, learn its gaps."""
    met = {r.skill for r in match.requirements if (r.claimed or 0) >= r.required}
    adapt, _ = adapt_nodes(pack, res, soc, claims, task_rows, intensity, model_version, met, done)
    learn = [
        {**n, "mode": "learn"}
        for n in _skill_nodes(pack, res, match, path, done, False, rows)
        + _skill_nodes(pack, res, match, path, done, True, rows)
    ]
    return {
        "id": "path",
        "title": f"Your path to {match.title}",
        "why": (
            "One path: AI basics, the skills you already have that AI is reshaping, then the "
            "skills this role needs. Start any step; each is a different skill."
        ),
        "nodes": _basics(pack, res, done, path.ai_basics) + adapt + learn,
    }
