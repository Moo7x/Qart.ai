"""Privacy: export and delete a profile, the resume code, retention.

docs/PHASE2_PLAN.md A9. Owner: A (p2-ai-experience). Registered in src/app.py in Stage 0; routes
are added here only.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/profiles/{profile_id}")
