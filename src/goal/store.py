"""One saved goal per profile: what the person aims for and the requirements read from a posting."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Engine, String, Table, Text, delete, insert, select

from src.db import metadata

goal_table = Table(
    "journey_goal",
    metadata,
    Column("profile_id", String(64), primary_key=True),
    Column("data", Text, nullable=False),  # JSON: inputs + extracted requirements
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def save_goal(engine: Engine, profile_id: str, data: dict[str, Any]) -> None:
    with engine.begin() as conn:
        conn.execute(delete(goal_table).where(goal_table.c.profile_id == profile_id))
        conn.execute(
            insert(goal_table).values(
                profile_id=profile_id, data=json.dumps(data), updated_at=datetime.now(UTC)
            )
        )


def get_goal(engine: Engine, profile_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        raw = conn.execute(
            select(goal_table.c.data).where(goal_table.c.profile_id == profile_id)
        ).scalar_one_or_none()
    return json.loads(raw) if raw else None
