"""Progress events (docs/PHASE2_PLAN.md §4 C5): what a person did, dated; the basis of badges.

Kinds: course_done, course_undone, step_skipped, level_changed (its `after` holds the level and
the claim's source) and destination_chosen. B's routes write them; owner A's progress-check
decide route writes level_changed through `record_event`. Rows are keyed by `profile_id`, so the
privacy delete finds this table. Nothing here judges a person: events only record their actions.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
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


@dataclass
class _Progress:
    """What the person's events say so far, replayed in order."""

    essentials: dict[str, int]  # essential skill -> the level its tier needs
    study_hours: dict[str, float]  # course id -> hours, for the plan's study steps
    practice: list[tuple[str, int]]  # (skill, target level) of the plan's practice steps
    has_plan: bool
    done: set[str] = field(default_factory=set)
    levels: dict[str, int] = field(default_factory=dict)

    def essentials_met(self) -> bool:
        return bool(self.essentials) and all(
            self.levels.get(s, 0) >= need for s, need in self.essentials.items()
        )

    def halfway(self) -> bool:
        total = sum(self.study_hours.values())
        done = sum(h for c, h in self.study_hours.items() if c in self.done)
        return total > 0 and done >= total / 2

    def complete(self) -> bool:
        return (
            self.has_plan
            and bool(self.study_hours or self.practice)
            and all(c in self.done for c in self.study_hours)
            and all(self.levels.get(s, 0) >= t for s, t in self.practice)
        )


@dataclass(frozen=True)
class _StateBadge:
    """A badge that describes the present: shown while `holds` is true, dated by the event that
    last made it true."""

    id: str
    title: str
    rule: str
    holds: Callable[[_Progress], bool]


STATE_BADGES = (
    _StateBadge("essentials_ready", "Essentials ready", ESSENTIALS_RULE, _Progress.essentials_met),
    _StateBadge("halfway", "Halfway", HALFWAY_RULE, _Progress.halfway),
    _StateBadge("plan_complete", "Plan complete", COMPLETE_RULE, _Progress.complete),
)


def badges(
    pack: "Pack", events: list[dict[str, Any]], destination: str | None, plan: "Pathway | None"
) -> list[dict[str, Any]]:
    role = pack.destination_roles.get(destination) if destination else None
    roles = [role] if role else list(pack.destination_roles.values())
    required = {r.skill for d in roles for r in d.requires}
    state = _Progress(
        essentials={
            r.skill: params.ROLE_TIER_LEVEL[r.tier]
            for r in (role.requires if role else [])
            if r.essential
        },
        study_hours={s.course.id: s.hours for s in plan.steps} if plan else {},
        practice=[(p.skill, p.target_level) for p in plan.practice_steps] if plan else [],
        has_plan=plan is not None,
    )
    out: list[dict[str, Any]] = []
    since: dict[str, dict[str, Any] | None] = {b.id: None for b in STATE_BADGES}
    for event in events:
        kind, ref = event["kind"], event["ref"]
        if kind == "course_done":
            if not any(b["id"] == "first_step" for b in out):  # the first ever, kept
                out.append(_badge("first_step", "First step", event, FIRST_STEP_RULE))
            state.done.add(ref)
        elif kind == "course_undone":
            state.done.discard(ref)
        elif kind == "level_changed":
            after, before = (event["after"] or {}).get("level"), event["before"]
            if after is not None:
                state.levels[ref] = after
                if before is not None and after > before and ref in required:
                    name = pack.skills[ref].name if ref in pack.skills else ref
                    out.append(
                        _badge(f"skill_up:{event['id']}", f"Skill up: {name}", event, SKILL_UP_RULE)
                    )
        for b in STATE_BADGES:
            if not b.holds(state):
                since[b.id] = None
            elif since[b.id] is None:
                since[b.id] = event
    for b in STATE_BADGES:
        made_true = since[b.id]
        if made_true is not None:
            out.append(_badge(b.id, b.title, made_true, b.rule))
    return out
