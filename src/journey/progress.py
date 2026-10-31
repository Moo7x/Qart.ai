"""Self-reported learning progress per profile: completed courses and a pause flag.

Completion is the person's own record of finishing a course. It never changes a skill claim or
the fit: the person updates their levels themselves when they feel ready. A step passed with
"continue anyway" is stored as skipped (C5) and always shown as such, never as done.
"""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
)

from src.db import metadata

progress_table = Table(
    "journey_progress",
    metadata,
    Column("profile_id", String(64), primary_key=True),
    Column("done", Text, nullable=False),  # JSON list of course ids
    Column("paused", Boolean, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# Steps passed with "continue anyway". A separate table, so the existing one keeps its columns.
skipped_table = Table(
    "journey_skipped",
    metadata,
    Column("profile_id", String(64), primary_key=True),
    Column("skipped", Text, nullable=False),  # JSON list of step ids
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def get_progress(engine: Engine, profile_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        row = (
            conn.execute(select(progress_table).where(progress_table.c.profile_id == profile_id))
            .mappings()
            .first()
        )
        skipped = conn.execute(
            select(skipped_table.c.skipped).where(skipped_table.c.profile_id == profile_id)
        ).scalar_one_or_none()
    passed = json.loads(skipped) if skipped else []
    if row is None:
        return {"done": [], "paused": False, "updated_at": None, "skipped": passed}
    return {
        "done": json.loads(row["done"]),
        "paused": row["paused"],
        "updated_at": row["updated_at"],
        "skipped": passed,
    }


def save_progress(
    engine: Engine,
    profile_id: str,
    done: list[str],
    paused: bool,
    skipped: list[str] | None = None,
) -> None:
    """Replace the saved progress; `skipped=None` keeps the steps already passed."""
    with engine.begin() as conn:
        if skipped is not None:
            conn.execute(delete(skipped_table).where(skipped_table.c.profile_id == profile_id))
            conn.execute(
                insert(skipped_table).values(
                    profile_id=profile_id,
                    skipped=json.dumps(sorted(set(skipped))),
                    updated_at=datetime.now(UTC),
                )
            )
        conn.execute(delete(progress_table).where(progress_table.c.profile_id == profile_id))
        conn.execute(
            insert(progress_table).values(
                profile_id=profile_id,
                done=json.dumps(sorted(set(done))),
                paused=paused,
                updated_at=datetime.now(UTC),
            )
        )
