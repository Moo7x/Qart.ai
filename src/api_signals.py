"""Future Skills Radar routes. They read the saved snapshots only (never the sources), so the
app works offline; refresh with scripts/fetch_signals.py.

GET /api/signals/market-pulse          Indeed AI Tracker, monthly AI share of postings
GET /api/signals/skills                HN "Who is hiring?" skill signals
GET /api/signals/for-user/{user_id}    the person's own skills against those signals
GET /api/signals/ai-trend               the AI trend chart: job boards or Indeed (one loader)
GET /api/signals/hiring-now             latest week on the job boards: skills, families

Every response carries the snapshot's source, licence, attribution, data_as_of, fetched_at,
caveats, plus age_days and stale (data older than stale_after_days). These are trend signals,
not predictions. Matching a person to signals happens here, server-side: no profile data is
sent anywhere.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.api_engine import StoreDep, require_profile, states_for
from src.engine.catalogue import default_catalogue
from src.engine.questionnaire import held_skills
from src.signals.config import default_config
from src.signals.pipeline import MARKET_PULSE, SKILL_SIGNALS, SNAPSHOT_DIR
from src.signals.trends import load_ai_trend, load_hiring_now

router = APIRouter(prefix="/api/signals", tags=["signals"])


def read_snapshot(name: str, directory: Path = SNAPSHOT_DIR) -> dict[str, Any]:
    path = directory / name
    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"{name} not found; run python scripts/fetch_signals.py"
        )
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return {**data, **freshness(data.get("data_as_of") or "")}


def freshness(data_as_of: str, today: date | None = None) -> dict[str, Any]:
    """Age of the data in days and whether it is stale (older than stale_after_days)."""
    try:
        as_of = date.fromisoformat(str(data_as_of)[:10])
    except ValueError:
        return {"age_days": None, "stale": True}
    age = ((today or datetime.now(UTC).date()) - as_of).days
    return {"age_days": age, "stale": age > default_config().params.stale_after_days}


@router.get("/market-pulse")
def market_pulse() -> dict[str, Any]:
    return read_snapshot(MARKET_PULSE)


@router.get("/ai-trend")
def ai_trend(region: str | None = None, granularity: str = "week") -> dict[str, Any]:
    """The AI trend chart's data: job boards for the region once there is enough history,
    otherwise the Indeed tracker plus the latest job-board figure (src/signals/trends.py)."""
    if granularity not in ("week", "month"):
        raise HTTPException(status_code=422, detail="granularity must be week or month")
    trend = load_ai_trend(region, granularity)
    as_of = (trend.get("meta") or {}).get("data_as_of") or ""
    return {**trend, **freshness(as_of)}


@router.get("/hiring-now")
def hiring_now(region: str = "malaysia_singapore") -> dict[str, Any]:
    """Latest-week skill shares and AI share per role family on the job boards, for a region."""
    view = load_hiring_now(region)
    if view is None:
        raise HTTPException(
            status_code=404, detail="no job-board snapshot yet; run scripts/fetch_jobs.py"
        )
    return {**view, **freshness(view["meta"].get("data_as_of") or "")}


@router.get("/skills")
def skills() -> dict[str, Any]:
    return read_snapshot(SKILL_SIGNALS)


def _summary(s: dict[str, Any], why: str) -> dict[str, Any]:
    return {
        "id": s["id"],
        "name": s["name"],
        "label": s["label"],
        "change_12m": s["change_12m"],
        "latest_sample_size": s["latest_sample_size"],
        "why": why,
    }


@router.get("/for-user/{user_id}")
def for_user(user_id: str, store: StoreDep) -> dict[str, Any]:
    """The person's skills as the radar sees them, for the pathway (informational only).

    "Your skills" = the skills from onboarding (questionnaire levels), raised by practice-case
    evidence, that the radar tracks. Same vocabulary ids, so no mapping is needed.
    """
    snapshot = read_snapshot(SKILL_SIGNALS)
    profile = require_profile(store, user_id)
    catalogue = default_catalogue()
    held = held_skills(profile, states_for(profile, store.events_for(user_id), catalogue))
    mine = {
        s["id"]: _summary(s, f"from your {held[s['id']].source}")
        for s in snapshot["series"]
        if s["id"] in held
    }
    tracked = {s["id"] for s in snapshot["series"]}
    return {
        "user_id": user_id,
        "source": snapshot["source"],
        "attribution": snapshot["attribution"],
        "data_as_of": snapshot["data_as_of"],
        "stale": snapshot["stale"],
        "user_skills": sorted(mine.values(), key=lambda s: s["name"]),
        "user_skills_cooling": [s for s in mine.values() if s["label"] == "cooling"],
        "rising_skills_not_held": [
            _summary(s, "rising in the tech hiring signal")
            for s in snapshot["series"]
            if s["label"] == "rising" and s["id"] not in mine
        ],
        "no_market_data": sorted(catalogue.vocabulary[k].name for k in held if k not in tracked),
        "note": "Trend signal from tech hiring posts (Hacker News), not a forecast. It does not "
        "change your matches or your pathway.",
    }
