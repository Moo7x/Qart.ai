"""SDG contribution of a person's path: skills or steps by SDG target, in planned hours.

docs/PHASE2_PLAN.md B7 and contract C4. Owner: B (p2-scoring-pathway). Registered in src/app.py
in Stage 0; routes are added here only. The response models live with the pure function in
src/pathway/sdg.py, which owner A's status page also calls.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import _destination_or_query, evidence_for, require_profile
from src.match.engine import Scenario, score_role
from src.pack import load_pack
from src.pathway.planner import plan_pathway
from src.pathway.sdg import SdgMatrix, sdg_matrix

router = APIRouter(prefix="/api/profiles/{profile_id}")


@router.get("/sdg")
def sdg(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> SdgMatrix:
    """The destination plan's skills × SDG targets in planned study hours, with reasons."""
    data, destination = require_profile(engine, profile_id)
    chosen = _destination_or_query(destination, None)
    pack = load_pack()
    evidence = evidence_for(engine, profile_id)
    levels = data.levels()
    match = score_role(pack, pack.destination_roles[chosen], levels, scenario, evidence)
    path = plan_pathway(
        pack, match, levels, data.weekly_hours, scenario, evidence, data.skills, data.situation
    )
    return sdg_matrix(pack, path)
