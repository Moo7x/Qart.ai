"""SDG contribution of a person's path: skills or steps by SDG target, in planned hours.

docs/PHASE2_PLAN.md B7 and contract C4. Owner: B (p2-scoring-pathway). Registered in src/app.py
in Stage 0; routes are added here only.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/profiles/{profile_id}")
