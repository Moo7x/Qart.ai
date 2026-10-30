"""Agent runs and their steps, so the agent window can show each step as it happens.

A run is started by a route and executed in a background thread; every step (what the agent is
doing, which tool it called, what came back) is written as it happens and the window polls for
new ones. The final result is stored with the run. No caption or article text is stored, only
what the window shows: titles, times, link anchors and the agent's one-line reasons.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Engine,
    Integer,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)

from src.db import metadata

agent_run_table = Table(
    "agent_run",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("profile_id", String(64), nullable=True),  # deleted with the profile (privacy)
    Column("kind", String(32), nullable=False),  # scout | check
    Column("subject", String(128), nullable=False),  # the skill
    Column("status", String(16), nullable=False),  # running | done | failed
    Column("engine", String(128), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("result", JSON, nullable=True),
)

agent_step_table = Table(
    "agent_step",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String(32), nullable=False, index=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("kind", String(16), nullable=False),  # think | tool | result | note | error
    Column("text", Text, nullable=False),
)


def start(
    engine: Engine, kind: str, subject: str, profile_id: str | None, agent_engine: str
) -> str:
    run_id = uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(
            insert(agent_run_table).values(
                id=run_id,
                profile_id=profile_id,
                kind=kind,
                subject=subject,
                status="running",
                engine=agent_engine,
                started_at=datetime.now(UTC),
            )
        )
    return run_id


def step(engine: Engine, run_id: str, kind: str, text: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            insert(agent_step_table).values(
                run_id=run_id, at=datetime.now(UTC), kind=kind, text=text
            )
        )


def finish(
    engine: Engine, run_id: str, status: str, agent_engine: str, result: dict[str, Any]
) -> None:
    with engine.begin() as conn:
        conn.execute(
            update(agent_run_table)
            .where(agent_run_table.c.id == run_id)
            .values(
                status=status, engine=agent_engine, finished_at=datetime.now(UTC), result=result
            )
        )


def read(engine: Engine, run_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        run = (
            conn.execute(select(agent_run_table).where(agent_run_table.c.id == run_id))
            .mappings()
            .first()
        )
        if run is None:
            return None
        steps = conn.execute(
            select(agent_step_table)
            .where(agent_step_table.c.run_id == run_id)
            .order_by(agent_step_table.c.id)
        ).mappings()
        return {**dict(run), "steps": [dict(s) for s in steps]}
