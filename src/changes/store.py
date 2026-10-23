"""Accepted evidence cutoffs and immutable per-profile change proposals.

New evidence never changes a person's profile or goal. Moving the accepted cutoff is an explicit
user action. Cutoffs refer to immutable observation ids, including revisions of earlier facts.
"""

import hashlib
import json
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
    UniqueConstraint,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from src import params
from src.db import metadata
from src.evidence.store import latest_observation_id, query_observations
from src.journey.store import ProfileData
from src.pack import load_pack

baseline_table = Table(
    "journey_evidence",
    metadata,
    Column("profile_id", String(64), primary_key=True),
    Column("cutoff", Integer, nullable=False),
)
change_table = Table(
    "journey_change",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("profile_id", String(64), nullable=False, index=True),
    Column("scenario", String(16), nullable=False),
    Column("before_cutoff", Integer, nullable=False),
    Column("after_cutoff", Integer, nullable=False),
    Column("context_hash", String(64), nullable=False),
    Column("run_id", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("status", String(16), nullable=False),
    Column("report", JSON, nullable=False),
    UniqueConstraint(
        "profile_id",
        "scenario",
        "before_cutoff",
        "after_cutoff",
        "context_hash",
        name="uq_journey_change",
    ),
)


def context_hash(profile: ProfileData, destination: str | None) -> str:
    policy_names = (
        "CALCULATION_VERSION",
        "ROLE_TIER_LEVEL",
        "ROLE_TIER_WEIGHT",
        "AI_ROLE_DIRECTION",
        "SCENARIO_INTENSITY",
        "SCENARIO_HORIZON_YEARS",
        "NEAR_TIE_POINTS",
        "COURSE_LEVEL_REACH",
        "COURSE_SHORT_MINUTES",
        "COURSE_MAX_GAIN_SHORT",
        "COURSE_MAX_GAIN_LONG",
    )
    policy = {name: getattr(params, name) for name in policy_names}
    raw = json.dumps(
        [profile.model_dump(), destination, load_pack().model_dump(), policy], sort_keys=True
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def baseline_cutoff(engine: Engine, profile_id: str, initial: int | None = None) -> int:
    with engine.begin() as conn:
        cutoff = conn.execute(
            select(baseline_table.c.cutoff).where(baseline_table.c.profile_id == profile_id)
        ).scalar_one_or_none()
        if cutoff is None:
            cutoff = latest_observation_id(engine) if initial is None else initial
            try:
                with conn.begin_nested():
                    conn.execute(
                        insert(baseline_table).values(profile_id=profile_id, cutoff=cutoff)
                    )
            except IntegrityError:
                # Two first page requests may establish the same baseline at once.
                cutoff = conn.execute(
                    select(baseline_table.c.cutoff).where(baseline_table.c.profile_id == profile_id)
                ).scalar_one()
        return int(cutoff)


def accepted_rows(engine: Engine, profile_id: str) -> list[dict[str, Any]]:
    return query_observations(engine, through_id=baseline_cutoff(engine, profile_id))


def list_changes(engine: Engine, profile_id: str, limit: int = 30) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [
            dict(r)
            for r in conn.execute(
                select(change_table)
                .where(change_table.c.profile_id == profile_id)
                .order_by(change_table.c.id.desc())
                .limit(limit)
            ).mappings()
        ]


def save_change(engine: Engine, values: dict[str, Any]) -> None:
    """Deduplicate reruns; a declined proposal is not re-created by polling."""
    identity = ("profile_id", "scenario", "before_cutoff", "after_cutoff", "context_hash")
    with engine.begin() as conn:
        existing = conn.execute(
            select(change_table.c.id).where(*(change_table.c[k] == values[k] for k in identity))
        ).first()
        if existing is None:
            try:
                with conn.begin_nested():
                    conn.execute(
                        insert(change_table).values(
                            **values, created_at=datetime.now(UTC), status="pending"
                        )
                    )
            except IntegrityError:
                # A scheduled publisher and an open Changes page can race on the unique key.
                pass


def resolve_change(
    engine: Engine,
    profile_id: str,
    change_id: int,
    accept: bool,
    expected_context: str,
) -> str:
    """Accept latest evidence for both scenarios or decline this proposal; reject stale input."""
    with engine.begin() as conn:
        row = (
            conn.execute(
                select(change_table).where(
                    change_table.c.id == change_id,
                    change_table.c.profile_id == profile_id,
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise LookupError("proposal not found")
        cutoff = conn.execute(
            select(baseline_table.c.cutoff).where(baseline_table.c.profile_id == profile_id)
        ).scalar_one()
        if (
            row["context_hash"] != expected_context
            or row["before_cutoff"] != cutoff
            or row["after_cutoff"] != latest_observation_id(engine)
        ):
            raise ValueError("profile, goal, evidence or calculation rules changed; refresh first")
        if row["status"] != "pending":
            raise ValueError("this proposal has already been resolved")
        status = "accepted" if accept else "declined"
        conn.execute(
            update(change_table).where(change_table.c.id == change_id).values(status=status)
        )
        if accept:
            conn.execute(
                update(baseline_table)
                .where(baseline_table.c.profile_id == profile_id)
                .values(cutoff=row["after_cutoff"])
            )
            conn.execute(
                update(change_table)
                .where(
                    change_table.c.profile_id == profile_id,
                    change_table.c.status == "pending",
                )
                .values(status="superseded")
            )
        return status
