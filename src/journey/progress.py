"""Self-reported learning progress per profile: completed courses and a pause flag.

Completion is the person's own record of finishing a course. It never changes a skill claim or
the fit: the person updates their levels themselves when they feel ready.
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


def get_progress(engine: Engine, profile_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        row = (
            conn.execute(select(progress_table).where(progress_table.c.profile_id == profile_id))
            .mappings()
            .first()
        )
    if row is None:
        return {"done": [], "paused": False, "updated_at": None}
    return {
        "done": json.loads(row["done"]),
        "paused": row["paused"],
        "updated_at": row["updated_at"],
    }


def save_progress(engine: Engine, profile_id: str, done: list[str], paused: bool) -> None:
    with engine.begin() as conn:
        conn.execute(delete(progress_table).where(progress_table.c.profile_id == profile_id))
        conn.execute(
            insert(progress_table).values(
                profile_id=profile_id,
                done=json.dumps(sorted(set(done))),
                paused=paused,
                updated_at=datetime.now(UTC),
            )
        )
