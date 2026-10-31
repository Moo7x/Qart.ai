"""SDG contribution of a person's path: skills or steps by SDG target, in planned hours.

docs/PHASE2_PLAN.md B7 and contract C4. Owner: B (p2-scoring-pathway). Registered in src/app.py
in Stage 0; routes are added here only. The response models live with the pure function in
src/pathway/sdg.py, which owner A's status page also calls.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import chosen_role, require_person
from src.match.engine import Scenario
from src.pathway.sdg import SdgMatrix, sdg_matrix

router = APIRouter(prefix="/api/profiles/{profile_id}")


@router.get("/sdg")
def sdg(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> SdgMatrix:
    """The destination plan's skills × SDG targets in planned study hours, with reasons."""
    person = require_person(engine, profile_id)
    match = person.score(chosen_role(person), scenario)
    return sdg_matrix(person.pack, person.plan(match, scenario))
