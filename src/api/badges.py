"""Badges earned from stored progress events only.

docs/PHASE2_PLAN.md B8 and contract C5. Owner: B (p2-scoring-pathway). Registered in src/app.py
in Stage 0; routes are added here only.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import evidence_for, require_profile
from src.journey.events import badges, list_events  # also registers the journey_event table
from src.match.engine import Scenario, score_role
from src.pack import load_pack
from src.pathway.planner import plan_pathway

router = APIRouter(prefix="/api/profiles/{profile_id}")


class BadgeEvidence(BaseModel):
    kind: str
    ref: str


class Badge(BaseModel):
    id: str
    title: str
    earned_at: datetime
    rule: str
    evidence: BadgeEvidence


@router.get("/badges")
def list_badges(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> list[Badge]:
    """Badges derived only from the person's events, each with the event that earned it."""
    data, destination = require_profile(engine, profile_id)
    pack = load_pack()
    plan = None
    if destination in pack.destination_roles:
        levels = data.levels()
        evidence = evidence_for(engine, profile_id)
        match = score_role(pack, pack.destination_roles[destination], levels, scenario, evidence)
        plan = plan_pathway(
            pack, match, levels, data.weekly_hours, scenario, evidence, data.skills, data.situation
        )
    found = badges(pack, list_events(engine, profile_id), destination, plan)
    return [Badge.model_validate(b) for b in found]
