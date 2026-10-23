"""Evidence preview for any O*NET occupation, from the general sources only.

Shows what the registered sources say about one occupation: its most important tasks (O*NET,
observed), AI use in sampled conversations (Economic Index, observed, global and Malaysia), GenAI
exposure of its ISCO-08 group (ILO, estimate), the Malaysian employment trend of its major group
(DOSM, observed) and whether MyCOL lists it as critical (expert). Roles, courses and pathways are
verified only for the GBS finance pack, so outside it the preview says so instead of inventing them.
The ISCO-08 group comes from the ESCO occupation the official crosswalk links (ESCO API, cached).
"""

import json
import re
from typing import Any

import httpx
from sqlalchemy import Engine, select, update

from src.collectors.ilo import OCCUPATION_SERIES, TASK_SERIES, gradient_of
from src.collectors.mycol import CRITICAL_SERIES, load_extraction
from src.evidence.field import field_profile
from src.evidence.signals import Signal
from src.match.outlook import MAJOR_GROUP
from src.occupations.catalogue import catalogue_table

ESCO_API = "https://ec.europa.eu/esco/api/resource/occupation"
ESCO_TIMEOUT_SECONDS = 10.0
Row = dict[str, Any]


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def isco_for(engine: Engine, row: Row, client: httpx.Client) -> tuple[str | None, str]:
    """The ISCO-08 group: the field's verified link, else the linked ESCO occupation's (cached)."""
    field = field_profile().occupation(row["soc"])
    if field and field.isco:
        return field.isco, ""
    if row["isco"]:
        return row["isco"], ""
    if not row["esco_uri"]:
        return None, "no ESCO match in the crosswalk"
    try:
        response = client.get(
            ESCO_API,
            params={"uri": row["esco_uri"], "language": "en"},
            timeout=ESCO_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        response.raise_for_status()
        code = str(response.json().get("code") or "")[:4]
    except (httpx.HTTPError, ValueError) as exc:
        # The ESCO service can be down (it redirects to a maintenance page); the pipeline fills
        # the link later, see fill_isco.
        return None, f"ISCO-08 link pending: the ESCO service did not answer ({type(exc).__name__})"
    if not code.isdigit():
        return None, "the ESCO occupation has no ISCO-08 code"
    with engine.begin() as conn:
        conn.execute(
            update(catalogue_table).where(catalogue_table.c.soc == row["soc"]).values(isco=code)
        )
    return code, ""


def fill_isco(engine: Engine, client: httpx.Client, limit: int = 200) -> str:
    """Background back-fill of ISCO-08 links; stops at the first ESCO failure."""
    with engine.connect() as conn:
        todo = [
            dict(r)
            for r in conn.execute(
                select(catalogue_table).where(
                    catalogue_table.c.isco.is_(None), catalogue_table.c.esco_uri.is_not(None)
                )
            ).mappings()
        ]
    filled = 0
    for row in todo[:limit]:
        code, note = isco_for(engine, row, client)
        if code is None and "pending" in note:
            return (
                f"ISCO-08 links: {filled} filled, {len(todo) - filled} pending (ESCO unavailable)"
            )
        filled += code is not None
    left = len(todo) - filled
    return f"ISCO-08 links: {filled} filled, {left} left" if todo else "ISCO-08 links complete"


def preview(
    engine: Engine, soc: str, rows: list[Row], signals: list[Signal], client: httpx.Client
) -> dict[str, Any] | None:
    with engine.connect() as conn:
        found = (
            conn.execute(select(catalogue_table).where(catalogue_table.c.soc == soc))
            .mappings()
            .first()
        )
    if found is None:
        return None
    occ = dict(found)
    field = field_profile()
    in_field = soc in field.soc_codes()
    isco, isco_note = isco_for(engine, occ, client)

    def latest(series: str, entity_id: str, geo: str) -> Row | None:
        hits = [
            r
            for r in rows
            if r["series"] == series
            and str(r["entity"]).split(" ", 1)[0] == entity_id
            and r["geography"] == geo
            and r["value"] is not None
        ]
        return max(hits, key=lambda r: r["period"]) if hits else None

    use = latest("aei_pct", soc, "GLOBAL")
    ai_use = None
    if use:
        auto = latest("aei_collaboration_bucket_automation_pct", soc, "GLOBAL")
        local = latest("aei_pct", soc, field.country)
        ai_use = {
            "share": use["value"],
            "share_local": local["value"] if local else None,
            "automation": auto["value"] if auto else None,
            "period": use["period"],
            "url": use["url"],
        }
    exposure = None
    if isco:
        ilo = latest(OCCUPATION_SERIES, isco, "GLOBAL")
        if ilo:
            tasks = sorted(
                (
                    {"text": str(r["entity"]).split(" ", 1)[1], "score": r["value"]}
                    for r in rows
                    if r["series"] == TASK_SERIES and str(r["entity"]).split(".")[0] == isco
                ),
                key=lambda t: -(t["score"] or 0.0),
            )
            exposure = {
                "isco": isco,
                "title": str(ilo["entity"]).split(" ", 1)[1],
                "mean": ilo["value"],
                "gradient": gradient_of(ilo["cited_span"]),
                "tasks": tasks,
                "url": ilo["url"],
            }
    by_id = {s.id: s for s in signals}
    group = MAJOR_GROUP.get(isco[0]) if isco else None
    employment = by_id.get(f"dosm_share_{group}") if group else None
    listed = {str(r["entity"]) for r in rows if r["series"] == CRITICAL_SERIES}
    mycol = None
    if listed and isco:
        # MyCOL names follow MASCO/ISCO unit-group titles: the declared field link if there is
        # one, otherwise the same title as the ISCO-08 group (a name match, labelled as such).
        linked = load_extraction()["field_links"].get(isco)
        title = exposure["title"] if exposure else ""
        match = (
            linked
            if linked in listed
            else next((n for n in listed if title and _squash(n) == _squash(title)), None)
        )
        mycol = {"listed": match is not None, "name": match, "of": len(listed)}
    return {
        "soc": soc,
        "title": occ["title"],
        "description": occ["description"],
        "in_field": in_field,
        "coverage": (
            "Full journey: verified roles, courses and pathways exist for this occupation."
            if in_field
            else "Evidence preview only: Qart has verified roles, courses and pathways for GBS "
            "finance & accounting so far, so none are suggested here."
        ),
        "esco": {"title": occ["esco_title"], "match": occ["esco_match"], "uri": occ["esco_uri"]},
        "isco": isco,
        "isco_note": isco_note,
        "tasks": json.loads(occ["tasks"]),
        "ai_use": ai_use,
        "exposure": exposure,
        "employment": employment.model_dump() if employment else None,
        "mycol": mycol,
    }
