"""A CV draft built only from what the person has confirmed, with versions and a visible diff.

Sections and their only sources:
* headline   – current role (pack title) or situation, and the chosen destination or goal role
* skills     – the person's claimed skills with their own rating (never called verified)
* experience – sentences quoted from their CV during intake, word for word
* learning   – courses they marked completed (self-reported), never listed as work experience
Nothing is invented: no employer, date, achievement or credential that the person did not give.
The person accepts a draft to make it a version; each draft is compared with the last accepted.
"""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Engine, Integer, String, Table, Text, insert, select

from src.db import metadata
from src.journey.store import ProfileData
from src.pack import Pack

LEVEL_WORDS = ("none", "aware", "working", "proficient", "expert")
SITUATION_WORDS = {
    "working": "Finance professional",
    "student": "Accounting and finance graduate",
    "switcher": "Professional moving into finance",
}

cv_table = Table(
    "cv_version",
    metadata,
    Column("profile_id", String(64), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("sections", Text, nullable=False),  # JSON {section: [lines]}
    Column("accepted_at", DateTime(timezone=True), nullable=False),
)


def build_draft(
    pack: Pack,
    profile: ProfileData,
    destination: str | None,
    goal_role: str | None,
    done_courses: list[str],
) -> dict[str, list[str]]:
    current = pack.current_roles.get(profile.current_role)
    who = current.title if current else SITUATION_WORDS[profile.situation]
    target = goal_role or (pack.destination_roles[destination].title if destination else None)
    headline = f"{who}, building towards {target}." if target else f"{who}."
    skills = sorted(
        (
            (claim.level, pack.skills[skill].name)
            for skill, claim in profile.skills.items()
            if claim.level and skill in pack.skills
        ),
        key=lambda x: (-x[0], x[1]),
    )
    quotes = sorted(
        {
            c.evidence.strip()
            for c in profile.skills.values()
            if c.source == "cv" and c.evidence.strip()
        }
    )
    finished = [pack.courses[c] for c in done_courses if c in pack.courses]
    learning = [
        f"{c.title} ({c.provider}, {round(c.minutes / 60, 1)} h) — completed, self-reported"
        for c in finished
    ]
    return {
        "headline": [headline],
        "skills": [f"{name} — own rating: {LEVEL_WORDS[level]}" for level, name in skills],
        "experience": quotes,
        "learning": learning,
    }


def versions(engine: Engine, profile_id: str) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(cv_table).where(cv_table.c.profile_id == profile_id).order_by(cv_table.c.version)
        ).mappings()
        return [
            {
                "version": r["version"],
                "accepted_at": r["accepted_at"],
                "sections": json.loads(r["sections"]),
            }
            for r in rows
        ]


def diff(
    old: dict[str, list[str]] | None, new: dict[str, list[str]]
) -> dict[str, dict[str, list[str]]]:
    """Lines added and removed per section, compared with the last accepted version."""
    old = old or {}
    return {
        section: {
            "added": [line for line in lines if line not in old.get(section, [])],
            "removed": [line for line in old.get(section, []) if line not in lines],
        }
        for section, lines in new.items()
    }


def accept(engine: Engine, profile_id: str, sections: dict[str, list[str]]) -> int:
    number = len(versions(engine, profile_id)) + 1
    with engine.begin() as conn:
        conn.execute(
            insert(cv_table).values(
                profile_id=profile_id,
                version=number,
                sections=json.dumps(sections),
                accepted_at=datetime.now(UTC),
            )
        )
    return number
