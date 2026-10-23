"""Rising and declining: the series behind the Trends page, each with what kind of number it is.

* employment – DOSM share of employees per MASCO major group (observed), with the change over the
               whole comparable period and over the recent window, which can point different ways
* job_ads    – DOSM online job ads: the Professionals share each quarter and the named occupations'
               share of all ads (observed), with quarters where the total jumped (possible coverage
               change, not demand)
* skills     – how the fast-adoption scenario shifts each skill's weight in the destination roles
               (an assumption applied to observed AI use)
* exposure   – ILO GenAI exposure of the field's ISCO-08 occupations (an estimate of potential)
Pure: rows and the pack in, a dict out.
"""

import statistics
from typing import Any

from src import params
from src.collectors.ilo import OCCUPATION_SERIES, gradient_of
from src.evidence import measures
from src.evidence.field import field_profile
from src.match.engine import Evidence, requirement_automation, scenario_weight
from src.pack import Pack

Row = dict[str, Any]
# MASCO 2020 major groups (ISCO-08 based) as OpenDOSM names them in wages_occupation.
MAJOR_GROUPS = {
    "managers": ("1", "Managers"),
    "professionals": ("2", "Professionals"),
    "technicians": ("3", "Technicians and associate professionals"),
    "clerical": ("4", "Clerical support workers"),
    "service_sales": ("5", "Service and sales workers"),
    "agriculture": ("6", "Skilled agricultural, forestry and fishery workers"),
    "craft": ("7", "Craft and related trades workers"),
    "operators": ("8", "Plant and machine operators and assemblers"),
    "elementary": ("9", "Elementary occupations"),
}
# The recent window starts after the backtest's training years, so it matches the test years.
RECENT_FROM = str(params.BACKTEST_TRAIN_END)


def _employment(rows: list[Row]) -> list[dict[str, Any]]:
    out = []
    for group, points in measures.occupation_shares(rows).items():
        if len(points) < 2:
            continue
        values = dict(points)
        recent = values.get(RECENT_FROM)
        code, title = MAJOR_GROUPS.get(group, ("", group))
        out.append(
            {
                "group": group,
                "major_group": code,
                "title": title,
                "points": [{"period": p, "value": round(v, 3)} for p, v in points],
                "first": points[0][0],
                "last": points[-1][0],
                "change_long": round(points[-1][1] - points[0][1], 2),
                "change_recent": round(points[-1][1] - recent, 2) if recent is not None else None,
            }
        )
    return sorted(out, key=lambda g: g["major_group"])


def _job_ads(rows: list[Row]) -> dict[str, Any]:
    ads = [
        r for r in rows if r["source_id"] == "dosm_job_market_insights" and r["value"] is not None
    ]
    totals = {r["period"]: r["value"] for r in ads if r["entity"] == "all occupations"}
    quarters = sorted(totals)
    breaks = [
        q
        for prev, q in zip(quarters, quarters[1:], strict=False)
        if totals[prev] and abs(totals[q] / totals[prev] - 1) > params.JOB_AD_BREAK_RATIO
    ]
    professionals = sorted(
        (r["period"], r["value"]) for r in ads if r["series"] == "online_job_offerings_share"
    )
    named: dict[str, list[dict[str, Any]]] = {}
    for r in ads:
        named_ad = r["series"] == "online_job_offerings" and r["entity"] != "all occupations"
        if named_ad and totals.get(r["period"]):
            share = round(100 * r["value"] / totals[r["period"]], 2)
            named.setdefault(r["entity"], []).append({"period": r["period"], "value": share})
    return {
        "quarters": quarters,
        "breaks": breaks,
        "professionals": [{"period": p, "value": v} for p, v in professionals],
        "named": [
            {"entity": name, "points": sorted(points, key=lambda p: p["period"])}
            for name, points in sorted(named.items(), key=lambda kv: -len(kv[1]))
        ],
    }


def _skills(pack: Pack, evidence: Evidence) -> list[dict[str, Any]]:
    """Fast-scenario weight factor per skill, averaged over the destination roles that need it."""
    factors: dict[str, list[float]] = {}
    bases: dict[str, set[str]] = {}
    for role in pack.destination_roles.values():
        for req in role.requires:
            if req.essential:
                continue  # essentials never shift
            skill = pack.skills[req.skill]
            share, basis, _ = requirement_automation(pack, role, req.skill, evidence)
            weight, _ = scenario_weight(req, skill.ai_role, "fast", share)
            factors.setdefault(req.skill, []).append(weight / params.ROLE_TIER_WEIGHT[req.tier])
            bases.setdefault(req.skill, set()).add(basis)
    return sorted(
        (
            {
                "skill": skill,
                "name": pack.skills[skill].name,
                "ai_role": pack.skills[skill].ai_role,
                "change": round(100 * (statistics.fmean(f) - 1), 1),  # % weight change
                "roles": len(f),
                "basis": sorted(bases[skill]),
            }
            for skill, f in factors.items()
        ),
        key=lambda s: -s["change"],
    )


def _exposure(rows: list[Row]) -> list[dict[str, Any]]:
    groups = field_profile().isco_codes()
    out = [
        {
            "isco": r["entity"].split(" ", 1)[0],
            "title": r["entity"].split(" ", 1)[1],
            "mean": r["value"],
            "gradient": gradient_of(r["cited_span"]),
        }
        for r in rows
        if r["series"] == OCCUPATION_SERIES
        and r["value"] is not None
        and r["entity"].split(" ", 1)[0] in groups
    ]
    return sorted(out, key=lambda e: -(e["mean"] or 0.0))


def trends(pack: Pack, rows: list[Row], evidence: Evidence) -> dict[str, Any]:
    return {
        "employment": _employment(rows),
        "recent_from": RECENT_FROM,
        "job_ads": _job_ads(rows),
        "skills": _skills(pack, evidence),
        "exposure": _exposure(rows),
    }
