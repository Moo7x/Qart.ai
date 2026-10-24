"""Occupation routes: match a job title to standard occupations, and preview one's evidence."""

from dataclasses import asdict
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Engine, func, select

from src.api.evidence import get_engine, get_settings
from src.config import Settings
from src.evidence.signals import occupation_signals
from src.evidence.store import query_observations
from src.occupations.catalogue import catalogue_table, vector_table
from src.occupations.detect import detect
from src.occupations.preview import preview

router = APIRouter(prefix="/api/occupations")
MAX_QUERY_CHARS = 300


class Query(BaseModel):
    text: str = Field(min_length=2, max_length=MAX_QUERY_CHARS)


@router.get("/status")
def occupation_status(
    engine: Engine = Depends(get_engine), settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    """Observed catalogue/index readiness, not a promise that a GPU worker is warm."""
    with engine.connect() as conn:
        count, updated, release = conn.execute(
            select(
                func.count(),
                func.max(catalogue_table.c.updated_at),
                func.max(catalogue_table.c.release),
            )
        ).one()
        indexed = conn.execute(select(func.count()).select_from(vector_table)).scalar_one()
    return {
        "occupations": count,
        "vectors": indexed,
        "updated_at": updated,
        "release": release,
        "runpod_configured": settings.runpod_configured,
        "source": "O*NET occupation catalogue",
        "url": "https://www.onetcenter.org/database.html",
        "examples": ["accounts clerk", "Kerani akaun", "software developer", "registered nurse"],
    }


@router.post("/detect")
def detect_occupation(
    body: Query, engine: Engine = Depends(get_engine), settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    """Suggestions only: the person confirms which occupation is theirs."""
    return asdict(detect(engine, settings, body.text))


@router.get("/{soc}")
def occupation_preview(soc: str, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    rows = query_observations(engine)
    with httpx.Client() as client:
        found = preview(engine, soc, rows, occupation_signals(rows), client)
    if found is None:
        raise HTTPException(status_code=404, detail="unknown occupation")
    return found
