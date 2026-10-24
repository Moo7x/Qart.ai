"""Feedback that improves the system: record, triage, evaluate a bounded correction, release it.

1. Record: every report keeps what it is about (target type and id), the page, and the version
   of the result the person saw (calculation version and their accepted evidence cutoff).
2. Triage, by kind (declared in KINDS):
   * preference – "not my goal", "impractical schedule": applies to that person only and at once
     (a role they marked is labelled for them); it is never treated as an error in the data.
   * error      – "course unavailable", "wrong skill mapping", "unsupported claim", "wrong number":
     goes to the review queue. A course report carries a bounded proposed correction (mark that
     course unavailable); other errors carry none and are fixed in the pack by a person.
3. Evaluate: before release, the correction is applied to fixed synthetic regression profiles
   (data/eval/regression_profiles.yaml) for every destination role: how many plans change, and
   which essential skills would be left with no verified course. Shown to the reviewer.
4. Release or reject (admin): a release is logged with its evaluation and takes effect for
   everyone (the planner stops using the course); a rejection is logged too. Nothing is learned
   automatically and no code changes itself.
"""

import json
from datetime import UTC, datetime
from typing import Any, Literal

import yaml
from sqlalchemy import (
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

from src import params
from src.config import REPO_ROOT
from src.db import metadata
from src.match.engine import Evidence, score_role
from src.pack import load_pack, set_unavailable, unavailable
from src.pathway.planner import plan_pathway

Kind = Literal[
    "not_my_goal",
    "impractical_schedule",
    "course_unavailable",
    "wrong_skill_mapping",
    "unsupported_claim",
    "wrong_number",
]
KINDS: dict[str, str] = {
    "not_my_goal": "preference",
    "impractical_schedule": "preference",
    "course_unavailable": "error",
    "wrong_skill_mapping": "error",
    "unsupported_claim": "error",
    "wrong_number": "error",
}
REGRESSION = REPO_ROOT / "data" / "eval" / "regression_profiles.yaml"

feedback_table = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("profile_id", String(64), nullable=True),
    Column("kind", String(32), nullable=False),
    Column("target_type", String(32), nullable=False),
    Column("target_id", String(128), nullable=False),
    Column("page", String(32), nullable=False),
    Column("message", Text, nullable=False),
    Column("version", String(64), nullable=False),
    Column("status", String(16), nullable=False),  # preference | review | released | rejected
    Column("proposal", Text, nullable=True),  # JSON
    Column("created_at", DateTime(timezone=True), nullable=False),
)
release_table = Table(
    "correction_release",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("feedback_id", Integer, nullable=False),
    Column("decision", String(16), nullable=False),  # released | rejected
    Column("action", String(64), nullable=False),
    Column("payload", Text, nullable=False),
    Column("evaluation", Text, nullable=False),
    Column("note", Text, nullable=False),
    Column("decided_at", DateTime(timezone=True), nullable=False),
)


def record(
    engine: Engine,
    profile_id: str | None,
    kind: str,
    target_type: str,
    target_id: str,
    page: str,
    message: str,
    cutoff: int | None,
) -> dict[str, Any]:
    route = KINDS[kind]
    proposal = (
        {"action": "mark_course_unavailable", "course_id": target_id}
        if kind == "course_unavailable" and target_id in load_pack().courses
        else None
    )
    values = {
        "profile_id": profile_id,
        "kind": kind,
        "target_type": target_type,
        "target_id": target_id,
        "page": page,
        "message": message,
        "version": f"{params.CALCULATION_VERSION}|cutoff {cutoff}",
        "status": "preference" if route == "preference" else "review",
        "proposal": json.dumps(proposal) if proposal else None,
        "created_at": datetime.now(UTC),
    }
    with engine.begin() as conn:
        new_id = conn.execute(insert(feedback_table).values(**values)).inserted_primary_key
    return {
        "id": new_id[0] if new_id else None,
        "route": route,
        "status": values["status"],
        "proposal": proposal,
    }


def preferences(engine: Engine, profile_id: str) -> dict[str, list[str]]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(feedback_table.c.kind, feedback_table.c.target_id).where(
                feedback_table.c.profile_id == profile_id, feedback_table.c.status == "preference"
            )
        ).all()
    return {
        "not_my_goal": sorted({t for k, t in rows if k == "not_my_goal"}),
        "impractical_schedule": sorted({t for k, t in rows if k == "impractical_schedule"}),
    }


def queue(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(select(feedback_table).order_by(feedback_table.c.id.desc())).mappings()
        out = []
        for r in rows:
            if r["status"] == "preference":
                continue
            item = dict(r)
            item["proposal"] = json.loads(r["proposal"]) if r["proposal"] else None
            out.append(item)
        return out


def evaluate_course_removal(course_id: str) -> dict[str, Any]:
    """Plans for the regression profiles with and without the course, for every destination."""
    pack = load_pack()
    cases = yaml.safe_load(REGRESSION.read_text(encoding="utf-8"))["profiles"]
    evidence = Evidence(automation_share={}, automation_period="", automation_source="regression")
    before_set = unavailable()
    changed, lost, total = 0, [], 0

    def plans() -> dict[tuple[str, str], tuple[list[str], list[str]]]:
        out = {}
        for case in cases:
            for role in pack.destination_roles.values():
                match = score_role(pack, role, case["levels"], "moderate", evidence)
                path = plan_pathway(
                    pack, match, case["levels"], case["weekly_hours"], "moderate", evidence
                )
                out[(case["id"], role.id)] = ([s.course.id for s in path.steps], path.uncovered)
        return out

    try:
        old = plans()
        set_unavailable(set(before_set) | {course_id})
        new = plans()
    finally:
        set_unavailable(set(before_set))
    essentials = {
        (role.id, pack.skills[r.skill].name)
        for role in pack.destination_roles.values()
        for r in role.requires
        if r.essential
    }
    for key, (courses, uncovered) in old.items():
        total += 1
        if courses != new[key][0]:
            changed += 1
        for skill in set(new[key][1]) - set(uncovered):
            if (key[1], skill) in essentials:
                lost.append(f"{key[0]} → {pack.destination_roles[key[1]].title}: {skill}")
    return {
        "plans": total,
        "plans_changed": changed,
        "essentials_left_without_course": sorted(set(lost)),
    }


def decide(engine: Engine, feedback_id: int, accept: bool, note: str) -> dict[str, Any]:
    with engine.connect() as conn:
        row = (
            conn.execute(select(feedback_table).where(feedback_table.c.id == feedback_id))
            .mappings()
            .first()
        )
    if row is None:
        raise LookupError("unknown feedback")
    if row["status"] != "review":
        raise ValueError(f"feedback is {row['status']}, not waiting for review")
    proposal = json.loads(row["proposal"]) if row["proposal"] else None
    evaluation: dict[str, Any] = {}
    action = "none"
    if proposal and proposal["action"] == "mark_course_unavailable":
        evaluation = evaluate_course_removal(proposal["course_id"])
        action = proposal["action"]
    decision = "released" if accept and proposal else "rejected" if not accept else "reviewed"
    with engine.begin() as conn:
        conn.execute(
            update(feedback_table).where(feedback_table.c.id == feedback_id).values(status=decision)
        )
        conn.execute(
            insert(release_table).values(
                feedback_id=feedback_id,
                decision=decision,
                action=action,
                payload=json.dumps(proposal or {}),
                evaluation=json.dumps(evaluation),
                note=note,
                decided_at=datetime.now(UTC),
            )
        )
    load_released(engine)
    return {"decision": decision, "evaluation": evaluation}


def releases(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(select(release_table).order_by(release_table.c.id.desc())).mappings()
        return [
            {
                **dict(r),
                "payload": json.loads(r["payload"]),
                "evaluation": json.loads(r["evaluation"]),
            }
            for r in rows
        ]


def load_released(engine: Engine) -> None:
    """Apply every released course correction (at start-up and after each decision)."""
    gone = {
        r["payload"]["course_id"]
        for r in releases(engine)
        if r["decision"] == "released" and r["action"] == "mark_course_unavailable"
    }
    set_unavailable(gone)
