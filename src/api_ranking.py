"""Role ranking route (QART_NEXT_STEPS §5–6, Domain 1 must-haves 3 and 6).

GET /api/ranking/{user_id}?scenario=moderate|fast

The person's skills (questionnaire levels raised by practice evidence) ranked against the role
catalogue by the pure `rank_roles`, scored under both scenarios and ordered by the chosen one,
each role with its gap. Adds the provenance a role card needs: the radar snapshot's source and
date, the scenario descriptions, family names, and, where the role's O*NET occupation is in the
Anthropic Economic Index, its automation share as evidence (shown, never a score input).
"""

import json
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.api_engine import StoreDep, require_profile, snapshots_by_id, states_for
from src.api_signals import freshness
from src.engine.catalogue import default_catalogue
from src.engine.questionnaire import default_questionnaire
from src.engine.ranking import default_scoring, rank_for_profile, signals_from_snapshot
from src.engine.role_catalogue import default_role_catalogue
from src.signals.pipeline import SKILL_SIGNALS, SNAPSHOT_DIR

router = APIRouter(prefix="/api", tags=["ranking"])
AEI_METRIC = "automation_pct"


def _read_signals() -> dict[str, Any] | None:
    """The radar snapshot, or None before the first fetch (momentum is then neutral)."""
    path = SNAPSHOT_DIR / SKILL_SIGNALS
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def aei_evidence() -> dict[str, dict[str, Any]]:
    """O*NET-SOC prefix (e.g. "13-2051") -> automation share from the latest AEI snapshot."""
    snapshots = sorted(snapshots_by_id().values(), key=lambda s: s.period)
    if not snapshots:
        return {}
    latest = snapshots[-1]
    out = {}
    for s in latest.signals:
        if s.metric == AEI_METRIC and s.geo == "GLOBAL" and s.entity.startswith("SOC "):
            out[s.entity[4:11]] = {
                "occupation": s.entity[12:],
                "automation_pct": s.value,
                "period": latest.period,
                "source": latest.source,
                "url": latest.url,
            }
    return out


@router.get("/ranking/{user_id}")
def ranking(
    user_id: str,
    store: StoreDep,
    scenario: str | None = Query(default=None, description="moderate or fast"),
) -> dict[str, Any]:
    cfg = default_scoring()
    if scenario is not None and scenario not in cfg.scenarios:
        raise HTTPException(status_code=422, detail=f"unknown scenario {scenario}")
    profile = require_profile(store, user_id)
    states = states_for(profile, store.events_for(user_id), default_catalogue())
    snapshot = _read_signals()
    result = rank_for_profile(profile, states, snapshot or {}, scenario)
    catalogue = default_role_catalogue()
    roles_by_id = {r.id: r for r in catalogue.roles}
    aei = aei_evidence()
    roles = []
    for ranked in result.roles:
        role = roles_by_id[ranked.role_id]
        roles.append(
            {
                **asdict(ranked),
                "source_title": role.source.title,
                "source_verified": role.source.verified,
                "family_name": next(f.name for f in catalogue.families if f.id == role.family),
                "ai_use_evidence": aei.get(role.source.code[:7]),
            }
        )
    signals = signals_from_snapshot(snapshot)
    return {
        "user_id": user_id,
        "scenario": result.scenario,
        "scenarios": {
            k: {"label": v.label, "description": v.description} for k, v in cfg.scenarios.items()
        },
        "empty_profile": result.empty_profile,
        "message": result.message,
        "starter_roles": [
            {"role_id": r, "name": roles_by_id[r].name}
            for r in result.starter_roles
            if r in roles_by_id
        ],
        "roles": roles,
        "levels": [lv.model_dump() for lv in default_questionnaire().levels],
        "bands": cfg.bands.model_dump(),
        "trend": {
            "source": signals.source,
            "data_as_of": signals.data_as_of,
            "source_url": (snapshot or {}).get("source_url"),
            **freshness(signals.data_as_of),
        },
        "note": "Estimates from declared assumptions and dated public data, not predictions. "
        "You decide; the ranking only suggests.",
    }
