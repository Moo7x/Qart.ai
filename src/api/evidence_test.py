"""Change test: recompute roles, weights and pathway with test evidence values; nothing is saved.

docs/PHASE2_PLAN.md A3 and contract C7. Owner: A (p2-ai-experience). Registered in src/app.py
in Stage 0; routes are added here only.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/profiles/{profile_id}")
