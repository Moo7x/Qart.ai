"""Progress check: a finance reviewer asks about work the person did and proposes a level.

docs/PHASE2_PLAN.md A8 and contract C6. One agent on AGENT_MODEL whose character is
data/agents/progress_check.character.yaml (not fine-tuned). Context given to it: the skill's level
descriptions, the O*NET tasks the pack links to the skill in the person's role, and the levels.

1. It asks CHECK_MIN_QUESTIONS to CHECK_MAX_QUESTIONS questions, one at a time, about real work.
2. It then judges each level above the person's current one: yes / partly / no, quoting the
   person's own words. The model never writes the level itself.
3. Code keeps a judgement only if its quote is really in the answers, and proposes the highest
   level L such that every level from current + 1 to L is "yes" ("partly" does not count),
   at most CHECK_MAX_RAISE above the current level.
4. The person accepts or declines. Accepting stores the level as a claim with source
   "agent_check", the quotes as its evidence, the time and the model: still a claim, never
   "verified". Declining changes nothing.

Level descriptions come from data/packs/gbs_fa/levels.yaml when owner B has published them
(contract C1); until then the general level meanings of C1 are used, and the result says so.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import yaml
from sqlalchemy import Engine

from src import llm, params
from src.agents import store
from src.agents.character import load_character
from src.config import Settings
from src.evidence.field import PACK_DIR
from src.journey.store import MAX_LEVEL, ProfileData, SkillClaim, get_profile, update_profile
from src.match.engine import required_level
from src.pack import Pack, load_pack

TIME_BUDGET_SECONDS = 20.0
LEVELS_FILE = PACK_DIR / "levels.yaml"
# The general level meanings of docs/PHASE2_PLAN.md C1, used until per-skill sentences exist.
GENERAL = {
    1: "Understands the basics and can follow along.",
    2: "Does routine tasks with guidance or a template.",
    3: "Handles the full task alone, including common problems.",
    4: "Handles complex cases, improves the process, guides others.",
    5: "Sets standards or direction for a team, function or region.",
}
SPACES = re.compile(r"\s+")


class CheckError(ValueError):
    """The check cannot start or continue (unknown skill, limit reached, no model)."""


def descriptions(skill: str) -> tuple[dict[int, str], str]:
    """Level → description for the skill, and where the descriptions come from."""
    if LEVELS_FILE.exists():
        data = yaml.safe_load(LEVELS_FILE.read_text(encoding="utf-8")) or {}
        anchors = (data.get("skills") or {}).get(skill, {}).get("anchors")
        if anchors:
            return {int(k): str(v) for k, v in anchors.items()}, "the skill's level descriptions"
    return (
        GENERAL,
        "the general level meanings (the skill's own descriptions are not published yet)",
    )


def _context(pack: Pack, data: ProfileData, destination: str | None, skill: str) -> dict[str, Any]:
    roles = [pack.destination_roles[destination]] if destination else []
    roles += [r for r in pack.destination_roles.values() if r not in roles]
    role = next((r for r in roles if any(q.skill == skill for q in r.requires)), None)
    claim = data.skills.get(skill)
    current = claim.level if claim and claim.level is not None else 0
    needed = (
        next((required_level(q) for q in role.requires if q.skill == skill), current)
        if role
        else current
    )
    tasks = [t.text for t in pack.tasks_for(role.soc, skill)] if role else []
    return {
        "current": current,
        "target": max(needed, min(current + 1, MAX_LEVEL)),
        "tasks": tasks[:5],
    }


def _messages(state: dict[str, Any], instruction: str) -> list[dict[str, str]]:
    character = load_character("progress_check")
    levels = "\n".join(f"Level {k}: {v}" for k, v in sorted(state["levels"].items()))
    talk = "\n".join(f"Q: {t['q']}\nA: {t['a']}" for t in state["qa"] if t.get("a"))
    tasks = "\n".join(f"- {t}" for t in state["tasks"]) or "- (no linked tasks)"
    return [
        {"role": "system", "content": character.system_prompt()},
        {
            "role": "user",
            "content": (
                f"Skill: {state['skill_name']}. The person now claims level {state['current']}.\n"
                f"Level descriptions:\n{levels}\nTasks in their field:\n{tasks}\n"
                f"Conversation so far:\n{talk or '(none)'}\n\n{instruction}"
            ),
        },
    ]


QUESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["question", "enough"],
    "properties": {"question": {"type": "string"}, "enough": {"type": "boolean"}},
}
JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["judgements"],
    "properties": {
        "judgements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["level", "verdict", "quote"],
                "properties": {
                    "level": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["yes", "partly", "no"]},
                    "quote": {"type": "string"},
                },
            },
        }
    },
}


def _complete(settings: Settings, purpose: str) -> llm.Complete:
    return llm.openai_complete(
        settings,
        schema_name=purpose,
        purpose=purpose,
        timeout=TIME_BUDGET_SECONDS,
        model=settings.agent_model,
    )


def _ask(state: dict[str, Any], complete: llm.Complete) -> tuple[str, bool]:
    raw = complete(
        _messages(state, "Ask the next single question about work they did, or say it is enough."),
        QUESTION_SCHEMA,
    )
    answer = json.loads(raw)
    return str(answer.get("question", "")).strip(), bool(answer.get("enough"))


def _norm(text: str) -> str:
    return SPACES.sub(" ", text).strip().lower()


def proposed_level(
    state: dict[str, Any], judgements: list[dict[str, Any]]
) -> tuple[int, list[dict[str, Any]]]:
    """Highest consecutive level judged "yes" with a real quote, capped; and the kept judgements."""
    said = _norm(" ".join(t["a"] for t in state["qa"] if t.get("a")))
    kept = [
        {"level": int(j["level"]), "verdict": j["verdict"], "quote": str(j["quote"]).strip()}
        for j in judgements
        if len(str(j.get("quote", "")).strip()) >= params.CHECK_MIN_QUOTE_CHARS
        and _norm(str(j["quote"])) in said
    ]
    yes = {j["level"] for j in kept if j["verdict"] == "yes"}
    cap = min(state["current"] + params.CHECK_MAX_RAISE, MAX_LEVEL)
    level = state["current"]
    while level + 1 <= cap and level + 1 in yes:
        level += 1
    return level, sorted(kept, key=lambda j: j["level"])


def start(
    engine: Engine,
    settings: Settings,
    profile_id: str,
    skill: str,
    complete: llm.Complete | None = None,
) -> dict[str, Any]:
    found = get_profile(engine, profile_id)
    pack = load_pack()
    if found is None:
        raise CheckError("profile not found")
    if skill not in pack.skills:
        raise CheckError("unknown skill")
    if complete is None and not settings.llm_configured:
        raise CheckError(
            "the progress check needs the language model; you can still set your level yourself"
        )
    since = datetime.now(UTC) - timedelta(days=1)
    if (
        store.count_since(engine, "check", skill, profile_id, since)
        >= params.CHECKS_PER_SKILL_PER_DAY
    ):
        raise CheckError(f"at most {params.CHECKS_PER_SKILL_PER_DAY} checks per skill per day")
    data, destination = found
    levels, levels_source = descriptions(skill)
    state = {
        "skill": skill,
        "skill_name": pack.skills[skill].name,
        **_context(pack, data, destination, skill),
        "levels": {k: v for k, v in levels.items() if k <= MAX_LEVEL},
        "levels_source": levels_source,
        "qa": [],
        "result": None,
        "decided": None,
    }
    run_id = store.start(engine, "check", skill, profile_id, f"{settings.agent_model} reviewer")
    question, _ = _ask(state, complete or _complete(settings, "progress_check"))
    state["qa"].append({"q": question, "a": ""})
    store.save(engine, run_id, "running", state)
    return {"session_id": run_id, **_public(state, settings)}


def _public(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    pending = state["qa"][-1]["q"] if state["qa"] and not state["qa"][-1]["a"] else None
    return {
        "skill": state["skill"],
        "skill_name": state["skill_name"],
        "current_level": state["current"],
        "target_level": state["target"],
        "question": pending,
        "asked": len(state["qa"]),
        "result": state["result"],
        "decided": state["decided"],
        "levels_source": state["levels_source"],
        "model": settings.agent_model,
    }


def _session(engine: Engine, profile_id: str, session_id: str) -> dict[str, Any]:
    run = store.read(engine, session_id)
    if run is None or run["kind"] != "check" or run["profile_id"] != profile_id:
        raise CheckError("unknown check")
    state: dict[str, Any] = run["result"]
    state["levels"] = {int(k): v for k, v in state["levels"].items()}
    return state


def answer(
    engine: Engine,
    settings: Settings,
    profile_id: str,
    session_id: str,
    text: str,
    complete: llm.Complete | None = None,
) -> dict[str, Any]:
    state = _session(engine, profile_id, session_id)
    if state["result"] is not None or not state["qa"] or state["qa"][-1]["a"]:
        raise CheckError("this check is not waiting for an answer")
    state["qa"][-1]["a"] = text.strip()
    model = complete or _complete(settings, "progress_check")
    asked = len(state["qa"])
    enough = False
    if asked < params.CHECK_MAX_QUESTIONS:
        question, enough = _ask(state, model)
        if asked < params.CHECK_MIN_QUESTIONS or (not enough and question):
            state["qa"].append({"q": question, "a": ""})
            store.save(engine, session_id, "running", state)
            return _public(state, settings)
    raw = model(
        _messages(
            state,
            "Judge each level above the current one: yes, partly or no, quoting the person's "
            "exact words.",
        ),
        JUDGE_SCHEMA,
    )
    level, kept = proposed_level(state, json.loads(raw).get("judgements", []))
    state["result"] = {
        "skill": state["skill"],
        "proposed_level": level,
        "met": kept,
        "model": settings.agent_model,
        "engine": f"{settings.agent_model} (schema-constrained), quotes checked in code",
        "note": f"Judged against {state['levels_source']}.",
    }
    store.save(engine, session_id, "done", state)
    return _public(state, settings)


def decide(
    engine: Engine, settings: Settings, profile_id: str, session_id: str, accept: bool
) -> dict[str, Any]:
    state = _session(engine, profile_id, session_id)
    if state["result"] is None or state["decided"] is not None:
        raise CheckError("nothing to decide for this check")
    level = state["result"]["proposed_level"]
    if accept and level > state["current"]:
        found = get_profile(engine, profile_id)
        if found is None:
            raise CheckError("profile not found")
        data, _ = found
        quotes = "; ".join(j["quote"] for j in state["result"]["met"] if j["verdict"] == "yes")
        data.skills[state["skill"]] = SkillClaim(
            level=level,
            evidence=quotes,
            source="agent_check",
            checked_at=datetime.now(UTC).isoformat(),
            model=settings.agent_model,
        )
        update_profile(engine, profile_id, data)
    state["decided"] = "accepted" if accept else "declined"
    store.save(engine, session_id, "done", state)
    return _public(state, settings)
