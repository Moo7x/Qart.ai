"""Badges earned from stored progress events only.

docs/PHASE2_PLAN.md B8 and contract C5. Owner: B (p2-scoring-pathway). Registered in src/app.py
in Stage 0; routes are added here only.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/profiles/{profile_id}")
