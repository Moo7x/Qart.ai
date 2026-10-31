"""Progress events (docs/PHASE2_PLAN.md §4 C5): what a person did, dated; the basis of badges.

Kinds: course_done, course_undone, step_skipped, level_changed (its `after` holds the level and
the claim's source) and destination_chosen. B's routes write them; owner A's progress-check
decide route writes level_changed through `record_event`. Rows are keyed by `profile_id`, so the
privacy delete finds this table. Nothing here judges a person: events only record their actions.
"""

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, get_args

from sqlalchemy import Column, DateTime, Engine, Integer, String, Table, Text, insert, select

from src import params
from src.db import metadata

if TYPE_CHECKING:
    from src.pack import Pack
    from src.pathway.planner import Pathway

EventKind = Literal[
    "course_done", "course_undone", "step_skipped", "level_changed", "destination_chosen"
]
KINDS: tuple[str, ...] = get_args(EventKind)

event_table = Table(
    "journey_event",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("profile_id", String(64), nullable=False, index=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("kind", String(32), nullable=False),
    Column("ref", String(128), nullable=False),  # course, step, skill or role id
    Column("before", Text, nullable=True),  # JSON
    Column("after", Text, nullable=True),  # JSON
)


def record_event(
    engine: Engine,
    profile_id: str,
    kind: str,
    ref: str,
    before: Any = None,
    after: Any = None,
) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown event kind: {kind}")
    with engine.begin() as conn:
        conn.execute(
            insert(event_table).values(
                profile_id=profile_id,
                at=datetime.now(UTC),
                kind=kind,
                ref=ref,
                before=json.dumps(before),
                after=json.dumps(after),
            )
        )


def list_events(engine: Engine, profile_id: str) -> list[dict[str, Any]]:
    """The person's events, oldest first, with before/after decoded."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(event_table)
            .where(event_table.c.profile_id == profile_id)
            .order_by(event_table.c.id)
        ).mappings()
        return [
            {
                **dict(r),
                "before": json.loads(r["before"]) if r["before"] else None,
                "after": json.loads(r["after"]) if r["after"] else None,
            }
            for r in rows
        ]


def record_claim_changes(
    engine: Engine,
    profile_id: str,
    old: dict[str, tuple[int | None, str]],
    new: dict[str, tuple[int | None, str]],
) -> None:
    """A level_changed event per skill whose stated level or source changed (level, source)."""
    for skill, (level, source) in new.items():
        before = old.get(skill, (None, ""))
        if level is not None and (level, source) != before:
            record_event(
                engine,
                profile_id,
                "level_changed",
                skill,
                before[0],
                {"level": level, "source": source},
            )


# --- Badges: derived only from events (C5) ----------------------------------------------------
# "First step" and "Skill up" record something that happened, so they stay. "Essentials
# ready", "Halfway" and "Plan complete" describe the present, so they show only while still true;
# their date is the event that last made them true.

FIRST_STEP_RULE = "Your first course marked done."
SKILL_UP_RULE = "A level you raised on a skill your destination requires."
ESSENTIALS_RULE = "Every essential skill of your destination at its required level."
HALFWAY_RULE = "Courses marked done cover half of your plan's study hours."
COMPLETE_RULE = "Every study step done and every practice step complete (a skip is not done)."


def _badge(badge_id: str, title: str, event: dict[str, Any], rule: str) -> dict[str, Any]:
    return {
        "id": badge_id,
        "title": title,
        "earned_at": event["at"],
        "rule": rule,
        "evidence": {"kind": event["kind"], "ref": event["ref"]},
    }


def badges(
    pack: "Pack", events: list[dict[str, Any]], destination: str | None, plan: "Pathway | None"
) -> list[dict[str, Any]]:
    role = pack.destination_roles.get(destination) if destination else None
    required = (
        {r.skill for r in role.requires}
        if role
        else {r.skill for d in pack.destination_roles.values() for r in d.requires}
    )
    essentials = {r.skill: r for r in role.requires if r.essential} if role else {}
    needed = {r.skill: r for r in role.requires} if role else {}
    study_hours = {s.course.id: s.hours for s in plan.steps} if plan else {}
    total_hours = sum(study_hours.values())
    practice = [(p.skill, p.target_level) for p in plan.practice_steps] if plan else []

    done: set[str] = set()
    levels: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    first_step = False
    since: dict[str, dict[str, Any] | None] = {
        "essentials": None,
        "halfway": None,
        "complete": None,
    }

    def state() -> dict[str, bool]:
        essentials_met = bool(essentials) and all(
            levels.get(s, 0) >= params.ROLE_TIER_LEVEL[needed[s].tier] for s in essentials
        )
        hours_done = sum(h for c, h in study_hours.items() if c in done)
        return {
            "essentials": essentials_met,
            "halfway": total_hours > 0 and hours_done >= total_hours / 2,
            "complete": bool(plan)
            and (bool(study_hours) or bool(practice))
            and all(c in done for c in study_hours)
            and all(levels.get(s, 0) >= t for s, t in practice),
        }

    for event in events:
        kind, ref = event["kind"], event["ref"]
        if kind == "course_done":
            done.add(ref)
            if not first_step:
                first_step = True
                out.append(_badge("first_step", "First step", event, FIRST_STEP_RULE))
        elif kind == "course_undone":
            done.discard(ref)
        elif kind == "level_changed":
            after = (event["after"] or {}).get("level")
            before = event["before"]
            if after is not None:
                levels[ref] = after
                if before is not None and after > before and ref in required:
                    name = pack.skills[ref].name if ref in pack.skills else ref
                    out.append(
                        _badge(f"skill_up:{event['id']}", f"Skill up: {name}", event, SKILL_UP_RULE)
                    )
        now = state()
        for key in since:
            if not now[key]:
                since[key] = None
            elif since[key] is None:
                since[key] = event
    titles = {
        "essentials": ("essentials_ready", "Essentials ready", ESSENTIALS_RULE),
        "halfway": ("halfway", "Halfway", HALFWAY_RULE),
        "complete": ("plan_complete", "Plan complete", COMPLETE_RULE),
    }
    for key, made_true in since.items():
        if made_true is not None:
            badge_id, title, rule = titles[key]
            out.append(_badge(badge_id, title, made_true, rule))
    return out
