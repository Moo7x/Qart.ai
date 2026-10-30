"""Privacy: export and delete a profile.

docs/PHASE2_PLAN.md A9. Owner: A (p2-ai-experience). Registered in src/app.py in Stage 0; routes
are added here only. The profile id is the private code kept in the person's browser: whoever
holds it can read, export or delete the profile, and nobody can list profiles.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine

from src import privacy
from src.api.evidence import get_engine

router = APIRouter(prefix="/api/profiles/{profile_id}")


@router.get("/export")
def export_profile(profile_id: str, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    """Everything stored for this profile, table by table."""
    data = privacy.export(engine, profile_id)
    if data is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"profile_id": profile_id, "tables": data}


@router.delete("")
def delete_profile(profile_id: str, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    """Delete the profile and every row of it. Cannot be undone."""
    deleted = privacy.delete_profile(engine, profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"deleted": deleted}
