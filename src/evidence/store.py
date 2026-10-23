"""Evidence store: immutable observations, pipeline runs and the run lock.

Observations are never updated in place. A re-fetch that returns the same value is skipped (same
content hash); a revised value is stored as a new row, so earlier results stay reproducible.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Engine,
    Float,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from src.db import metadata

observation_table = Table(
    "observation",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_id", String(64), nullable=False, index=True),
    Column("series", String(128), nullable=False, index=True),
    Column("entity", String(512), nullable=False),
    Column("geography", String(32), nullable=False),
    Column("period", String(16), nullable=False),
    Column("value", Float, nullable=True),  # None = missing, never zero
    Column("unit", String(128), nullable=False),
    Column("denominator", Float, nullable=True),
    Column("published", String(32), nullable=True),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("url", Text, nullable=False),
    Column("cited_span", Text, nullable=False),
    Column("method_version", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("run_id", Integer, nullable=True),
    UniqueConstraint("content_hash", name="uq_observation_content"),
)

run_table = Table(
    "ingestion_run",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("trigger", String(32), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", String(32), nullable=False),
    Column("new_observations", Integer, nullable=False, default=0),
    Column("sources", JSON, nullable=False, default=list),
)

lock_table = Table(
    "run_lock",
    metadata,
    Column("name", String(64), primary_key=True),
    Column("holder", String(64), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)


source_state_table = Table(
    "source_state",
    metadata,
    Column("source_id", String(64), primary_key=True),
    Column("key", String(64), primary_key=True),
    Column("value", Text, nullable=False),
)


class DbSourceState:
    """A collector's remembered values, written only when that source's run succeeds."""

    def __init__(self, engine: Engine, source_id: str) -> None:
        self.engine = engine
        self.source_id = source_id
        self.pending: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        if key in self.pending:
            return self.pending[key]
        stmt = select(source_state_table.c.value).where(
            source_state_table.c.source_id == self.source_id, source_state_table.c.key == key
        )
        with self.engine.connect() as conn:
            value = conn.execute(stmt).scalar_one_or_none()
        return None if value is None else str(value)

    def set(self, key: str, value: str) -> None:
        self.pending[key] = value

    def commit(self) -> None:
        with self.engine.begin() as conn:
            for key, value in self.pending.items():
                where = (
                    source_state_table.c.source_id == self.source_id,
                    source_state_table.c.key == key,
                )
                changed = conn.execute(update(source_state_table).where(*where).values(value=value))
                if changed.rowcount == 0:
                    conn.execute(
                        insert(source_state_table).values(
                            source_id=self.source_id, key=key, value=value
                        )
                    )
        self.pending.clear()


@dataclass(frozen=True)
class Observation:
    """One dated fact from one source, with the passage it came from."""

    source_id: str
    series: str
    entity: str
    geography: str
    period: str
    value: float | None
    unit: str
    url: str
    cited_span: str
    method_version: str
    denominator: float | None = None
    published: str | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def content_hash(self) -> str:
        """Identity of the fact itself (not when it was fetched): same fact → same hash."""
        key = [
            self.source_id,
            self.series,
            self.entity,
            self.geography,
            self.period,
            self.value,
            self.denominator,
            self.unit,
            self.method_version,
        ]
        return hashlib.sha256(json.dumps(key).encode()).hexdigest()


def insert_observations(engine: Engine, observations: list[Observation], run_id: int | None) -> int:
    """Store facts not seen before; return how many were new."""
    new = 0
    with engine.begin() as conn:
        known = set(conn.execute(select(observation_table.c.content_hash)).scalars())
        for obs in observations:
            digest = obs.content_hash()
            if digest in known:
                continue
            conn.execute(
                insert(observation_table).values(
                    source_id=obs.source_id,
                    series=obs.series,
                    entity=obs.entity,
                    geography=obs.geography,
                    period=obs.period,
                    value=obs.value,
                    unit=obs.unit,
                    denominator=obs.denominator,
                    published=obs.published,
                    fetched_at=obs.fetched_at,
                    url=obs.url,
                    cited_span=obs.cited_span,
                    method_version=obs.method_version,
                    content_hash=digest,
                    run_id=run_id,
                )
            )
            known.add(digest)
            new += 1
    return new


def query_observations(
    engine: Engine, source_id: str | None = None, series: str | None = None
) -> list[dict[str, Any]]:
    """Latest version of each fact (by source, series, entity, geography, period)."""
    stmt = select(observation_table).order_by(observation_table.c.id)
    if source_id:
        stmt = stmt.where(observation_table.c.source_id == source_id)
    if series:
        stmt = stmt.where(observation_table.c.series == series)
    latest: dict[tuple[str, ...], dict[str, Any]] = {}
    with engine.connect() as conn:
        for row in conn.execute(stmt).mappings():
            key = (row["source_id"], row["series"], row["entity"], row["geography"], row["period"])
            latest[key] = dict(row)  # later ids are revisions and win
    return list(latest.values())


def start_run(engine: Engine, trigger: str) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            insert(run_table).values(
                trigger=trigger,
                started_at=datetime.now(UTC),
                status="running",
                new_observations=0,
                sources=[],
            )
        )
        key = result.inserted_primary_key
        if key is None:
            raise RuntimeError("database returned no id for the new run")
        return int(key[0])


def finish_run(
    engine: Engine, run_id: int, status: str, new_observations: int, sources: list[dict[str, Any]]
) -> None:
    with engine.begin() as conn:
        conn.execute(
            update(run_table)
            .where(run_table.c.id == run_id)
            .values(
                finished_at=datetime.now(UTC),
                status=status,
                new_observations=new_observations,
                sources=sources,
            )
        )


def list_runs(engine: Engine, limit: int) -> list[dict[str, Any]]:
    stmt = select(run_table).order_by(run_table.c.id.desc()).limit(limit)
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings()]


def acquire_lock(engine: Engine, name: str, holder: str, ttl: timedelta) -> bool:
    """Take the named lock unless someone else holds an unexpired one.

    The expiry means a crashed run cannot block the pipeline forever.
    """
    now = datetime.now(UTC)
    with engine.begin() as conn:
        try:
            conn.execute(insert(lock_table).values(name=name, holder=holder, expires_at=now + ttl))
            return True
        except IntegrityError:
            pass
    with engine.begin() as conn:
        taken = conn.execute(
            update(lock_table)
            .where(
                lock_table.c.name == name, lock_table.c.expires_at < _naive_or_aware(engine, now)
            )
            .values(holder=holder, expires_at=now + ttl)
        )
        return taken.rowcount == 1


def release_lock(engine: Engine, name: str, holder: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            lock_table.delete().where(lock_table.c.name == name, lock_table.c.holder == holder)
        )


def _naive_or_aware(engine: Engine, moment: datetime) -> datetime:
    """SQLite stores datetimes without a zone, so compare with a naive UTC value there."""
    return moment.replace(tzinfo=None) if engine.dialect.name == "sqlite" else moment
