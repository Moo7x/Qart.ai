"""A person's data: export it, delete it, and delete profiles nobody has used for a while.

Every table holding a person's data keys it by a `profile_id` column (docs/PHASE2_PLAN.md §5), so
export and delete find those tables from the shared metadata instead of a list that could fall
behind. The profile row itself is keyed by `id`. Agent steps belong to an agent run, so they go
with the person's runs. Nothing here touches the evidence, the catalogue or the usage counter,
which hold no personal data.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Engine, Table, delete, select

from src.agents.store import agent_run_table, agent_step_table
from src.db import metadata
from src.intake import cache as cv_cache
from src.journey.store import profile_table


def person_tables() -> list[Table]:
    """Every table with a profile_id column, found from the metadata (new tables included)."""
    return sorted(
        (t for t in metadata.tables.values() if "profile_id" in t.c),
        key=lambda t: t.name,
    )


def _plain(row: dict[str, Any]) -> dict[str, Any]:
    plain: dict[str, Any] = json.loads(json.dumps(row, default=str))  # datetimes as text
    return plain


def export(engine: Engine, profile_id: str) -> dict[str, list[dict[str, Any]]] | None:
    """Every stored row for the profile, by table; None when there is no such profile."""
    with engine.connect() as conn:
        profile = (
            conn.execute(select(profile_table).where(profile_table.c.id == profile_id))
            .mappings()
            .first()
        )
        if profile is None:
            return None
        out = {profile_table.name: [_plain(dict(profile))]}
        for table in person_tables():
            rows = conn.execute(select(table).where(table.c.profile_id == profile_id)).mappings()
            out[table.name] = [_plain(dict(r)) for r in rows]
        runs = [r["id"] for r in out.get(agent_run_table.name, [])]
        if runs:
            steps = conn.execute(
                select(agent_step_table).where(agent_step_table.c.run_id.in_(runs))
            ).mappings()
            out[agent_step_table.name] = [_plain(dict(s)) for s in steps]
    return out


def delete_profile(engine: Engine, profile_id: str) -> dict[str, int]:
    """Delete the profile and every row of it; returns rows deleted per table."""
    counts: dict[str, int] = {}
    with engine.begin() as conn:
        runs = [
            r[0]
            for r in conn.execute(
                select(agent_run_table.c.id).where(agent_run_table.c.profile_id == profile_id)
            )
        ]
        if runs:
            counts[agent_step_table.name] = conn.execute(
                delete(agent_step_table).where(agent_step_table.c.run_id.in_(runs))
            ).rowcount
        for table in person_tables():
            counts[table.name] = conn.execute(
                delete(table).where(table.c.profile_id == profile_id)
            ).rowcount
        counts[profile_table.name] = conn.execute(
            delete(profile_table).where(profile_table.c.id == profile_id)
        ).rowcount
    return {k: v for k, v in counts.items() if v}


def purge_idle(engine: Engine, days: int, now: datetime | None = None) -> int:
    """Delete every profile not updated for `days` days; returns how many."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    if engine.dialect.name == "sqlite":
        cutoff = cutoff.replace(tzinfo=None)  # SQLite stores datetimes without a zone
    with engine.connect() as conn:
        idle = [
            r[0]
            for r in conn.execute(
                select(profile_table.c.id).where(profile_table.c.updated_at < cutoff)
            )
        ]
    for profile_id in idle:
        delete_profile(engine, profile_id)
    # Stored CV readings (src/intake/cache.py) follow the same retention as profiles.
    with engine.begin() as conn:
        conn.execute(delete(cv_cache.cache_table).where(cv_cache.cache_table.c.created_at < cutoff))
    return len(idle)
