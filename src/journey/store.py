"""Profiles and destination choices.

A profile holds only what matching needs: situation, current role, claimed skill levels with the
CV sentence behind each, hours, budget and interests. No name, contact details or CV text is
stored. The profile id is a random 128-bit token kept by the person's browser; there is no way to
list profiles, so a profile can only be read by whoever holds its id.
"""

import secrets
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Engine, String, Table, insert, select, update

from src.db import metadata

PROFILE_ID_BYTES = 16  # 128-bit random id: unguessable, so it can act as the access key
MIN_WEEKLY_HOURS = 1
MAX_WEEKLY_HOURS = 40
MAX_LEVEL = 4

profile_table = Table(
    "profile",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("data", JSON, nullable=False),
    Column("destination", String(64), nullable=True),
    Column("destination_chosen_at", DateTime(timezone=True), nullable=True),
)

Situation = Literal["working", "student", "switcher"]


class SkillClaim(BaseModel):
    level: int | None = Field(default=None, ge=0, le=MAX_LEVEL)  # None = not stated
    evidence: str = ""  # the CV sentence, or "" when the person set it themselves
    source: Literal["cv", "self", "keyword"] = "self"


class ProfileData(BaseModel):
    situation: Situation
    current_role: str = "other"
    years_experience: float | None = Field(default=None, ge=0, le=60)
    weekly_hours: float = Field(default=6, ge=MIN_WEEKLY_HOURS, le=MAX_WEEKLY_HOURS)
    budget: Literal["free", "free_hrd", "up_to_500"] = "free"
    interests: list[Literal["finance_core", "data_digital", "green", "business"]] = []
    sdg_priorities: list[str] = []
    skills: dict[str, SkillClaim] = {}
    extraction_engine: str = ""

    def levels(self) -> dict[str, int | None]:
        return {skill: claim.level for skill, claim in self.skills.items()}


def new_profile_id() -> str:
    return secrets.token_hex(PROFILE_ID_BYTES)


def create_profile(engine: Engine, data: ProfileData) -> str:
    profile_id = new_profile_id()
    now = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(
            insert(profile_table).values(
                id=profile_id, created_at=now, updated_at=now, data=data.model_dump()
            )
        )
    return profile_id


def get_profile(engine: Engine, profile_id: str) -> tuple[ProfileData, str | None] | None:
    with engine.connect() as conn:
        row = conn.execute(select(profile_table).where(profile_table.c.id == profile_id)).first()
    if row is None:
        return None
    return ProfileData.model_validate(row.data), row.destination


def update_profile(engine: Engine, profile_id: str, data: ProfileData) -> bool:
    with engine.begin() as conn:
        result = conn.execute(
            update(profile_table)
            .where(profile_table.c.id == profile_id)
            .values(data=data.model_dump(), updated_at=datetime.now(UTC))
        )
    return result.rowcount == 1


def choose_destination(engine: Engine, profile_id: str, role_id: str) -> bool:
    with engine.begin() as conn:
        result = conn.execute(
            update(profile_table)
            .where(profile_table.c.id == profile_id)
            .values(destination=role_id, destination_chosen_at=datetime.now(UTC))
        )
    return result.rowcount == 1
