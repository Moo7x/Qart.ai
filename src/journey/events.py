"""Progress events (docs/PHASE2_PLAN.md §4 C5): what a person did, dated; the basis of badges.

Kinds: course_done, course_undone, step_skipped, level_changed (its `after` holds the level and
the claim's source) and destination_chosen. B's routes write them; owner A's progress-check
decide route writes level_changed through `record_event`. Rows are keyed by `profile_id`, so the
privacy delete finds this table. Nothing here judges a person: events only record their actions.
"""

import json
from datetime import UTC, datetime
from typing import Any, Literal, get_args

from sqlalchemy import Column, DateTime, Engine, Integer, String, Table, Text, insert, select

from src.db import metadata

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
