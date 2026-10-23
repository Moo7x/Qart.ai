"""Profile-scoped proposals and read-only replay of real, saved observation periods."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import require_profile
from src.changes.engine import REPLAY_SOURCES, ChangeReport, compare, replay_periods, replay_rows
from src.changes.service import refresh_proposals
from src.changes.store import baseline_cutoff, context_hash, list_changes, resolve_change
from src.evidence.store import latest_observation_id, query_observations
from src.match.engine import Scenario
from src.pack import load_pack

router = APIRouter(prefix="/api/profiles/{profile_id}/changes")


class ReplaySource(BaseModel):
    source_id: str
    periods: list[str]


class Proposal(BaseModel):
    id: int
    scenario: Scenario
    status: str
    actionable: bool
    created_at: datetime
    run_id: int | None
    report: ChangeReport


class ChangesResponse(BaseModel):
    accepted_cutoff: int
    latest_cutoff: int
    proposals: list[Proposal]
    replay_sources: list[ReplaySource]


class Decision(BaseModel):
    decision: Literal["accept", "decline"]


@router.get("", response_model=ChangesResponse)
def changes(profile_id: str, engine: Engine = Depends(get_engine)) -> ChangesResponse:
    profile, destination = require_profile(engine, profile_id)
    cutoff = baseline_cutoff(engine, profile_id)
    refresh_proposals(engine, cutoff, profile_id=profile_id)
    latest = latest_observation_id(engine)
    digest = context_hash(profile, destination)
    proposals = [
        Proposal(
            id=r["id"],
            scenario=r["scenario"],
            status=r["status"],
            created_at=r["created_at"],
            run_id=r["run_id"],
            report=ChangeReport.model_validate(r["report"]),
            actionable=(
                r["status"] == "pending"
                and r["before_cutoff"] == cutoff
                and r["after_cutoff"] == latest
                and r["context_hash"] == digest
            ),
        )
        for r in list_changes(engine, profile_id)
    ]
    rows = query_observations(engine)
    return ChangesResponse(
        accepted_cutoff=cutoff,
        latest_cutoff=latest,
        proposals=proposals,
        replay_sources=[
            ReplaySource(source_id=s, periods=replay_periods(rows, s))
            for s in sorted(REPLAY_SOURCES)
        ],
    )


@router.get("/replay", response_model=ChangeReport)
def replay(
    profile_id: str,
    source_id: str,
    before: str,
    after: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> ChangeReport:
    profile, destination = require_profile(engine, profile_id)
    try:
        old, new = replay_rows(query_observations(engine), source_id, before, after)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return compare(load_pack(), profile, destination, old, new, scenario, "replay", before, after)


@router.post("/{change_id}")
def decide(
    profile_id: str,
    change_id: int,
    body: Decision,
    engine: Engine = Depends(get_engine),
) -> dict[str, str]:
    profile, destination = require_profile(engine, profile_id)
    try:
        status = resolve_change(
            engine,
            profile_id,
            change_id,
            body.decision == "accept",
            context_hash(profile, destination),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": status}
