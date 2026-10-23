"""Signals: labelled, sourced statements built from measures (the Future Skills Radar's list).

Labels follow the declared gates in src/params.py. A direction (rising / weakening) needs two
independent sources agreeing, or one official series with enough comparable points; otherwise the
signal is "not enough evidence yet" and its direction is shown only as an early signal. Expert
assessments (TalentCorp) are shown as expert views, never as measured trends.
"""

from typing import Any, Literal

from pydantic import BaseModel

from src import params
from src.collectors.talentcorp import IMPACT_CODE
from src.evidence import measures
from src.evidence.field import field_profile
from src.evidence.registry import registry

Direction = Literal["rising", "weakening", "stable", "insufficient", "expert"]
# Occupation groups (MASCO major groups) that contain the field's roles: finance clerks are
# clerical support workers; accountants are professionals; accounting associates are technicians
# and associate professionals.
FIELD_GROUPS = {
    "clerical": "Clerical support workers",
    "professionals": "Professionals",
    "technicians": "Technicians and associate professionals",
}


class Point(BaseModel):
    period: str
    value: float


class Evidence(BaseModel):
    source_id: str
    period: str
    value: float | None
    cited_span: str
    url: str
    published: str | None
    fetched: str


class Signal(BaseModel):
    id: str
    title: str
    family: str
    kind: Literal["observed", "expert"]
    direction: Direction
    early_direction: Literal["up", "down", "flat"] | None
    headline: str
    unit: str
    points: list[Point]
    independent_sources: int
    note: str
    sources: list[dict[str, str]]
    evidence: list[Evidence]


def _source_card(source_id: str) -> dict[str, str]:
    s = registry()[source_id]
    return {
        "id": s.id,
        "name": s.name,
        "publisher": s.publisher,
        "terms": s.terms,
        "shows": s.shows,
        "does_not_show": s.does_not_show,
    }


def _evidence(rows: list[dict[str, Any]]) -> list[Evidence]:
    return [
        Evidence(
            source_id=r["source_id"],
            period=r["period"],
            value=r["value"],
            cited_span=r["cited_span"],
            url=r["url"],
            published=r["published"],
            fetched=r["fetched_at"].date().isoformat()
            if hasattr(r["fetched_at"], "date")
            else str(r["fetched_at"])[:10],
        )
        for r in rows
    ]


def _direction_from_change(change: float, threshold: float) -> Literal["up", "down", "flat"]:
    if change >= threshold:
        return "up"
    if change <= -threshold:
        return "down"
    return "flat"


def _label(
    early: Literal["up", "down", "flat"], sources: int, points: int, official: bool
) -> Direction:
    enough = sources >= params.MIN_INDEPENDENT_SOURCES or (
        official and points >= params.MIN_POINTS_SINGLE_OFFICIAL_SERIES
    )
    if not enough:
        return "insufficient"
    labels: dict[str, Direction] = {"up": "rising", "down": "weakening", "flat": "stable"}
    return labels[early]


def occupation_signals(rows: list[dict[str, Any]]) -> list[Signal]:
    shares = measures.occupation_shares(rows)
    out = []
    for group, title in FIELD_GROUPS.items():
        series = shares.get(group, [])
        if len(series) < 2:
            continue
        (first_p, first), (last_p, last) = series[0], series[-1]
        early = _direction_from_change(last - first, params.DOSM_MIN_SHARE_CHANGE_PP)
        heads = measures.headcounts(rows, group)
        check = measures.backtest(series, group)
        cited = [
            r
            for r in rows
            if r["source_id"] == "dosm_wages_occupation"
            and r["entity"] in (group, "overall")
            and r["period"] in (first_p, last_p)
        ]
        out.append(
            Signal(
                id=f"dosm_share_{group}",
                title=f"{title}: share of employees",
                family="malaysian_labour",
                kind="observed",
                direction=_label(early, 1, len(series), official=True),
                early_direction=early,
                headline=(
                    f"{first:.2f}% ({first_p}) → {last:.2f}% ({last_p}); headcount "
                    f"{heads[0][1]:,.0f}k → {heads[-1][1]:,.0f}k"
                ),
                unit="% of employees",
                points=[measures_point(p) for p in series],
                independent_sources=1,
                note=(
                    f"Observed history, not a forecast. Backtest 2022–2025: no-change error "
                    f"{check.naive:.2f} pts vs straight-line {check.linear:.2f} pts, "
                    f"so the trend is not extrapolated."
                ),
                sources=[_source_card("dosm_wages_occupation")],
                evidence=_evidence(cited),
            )
        )
    return out


def measures_point(point: measures.Point) -> Point:
    return Point(period=point[0], value=round(point[1], 4))


def job_ad_signals(rows: list[dict[str, Any]]) -> list[Signal]:
    out = []
    for occupation in field_profile().dosm_job_ad_occupations:
        segments = measures.job_ad_segments(rows, occupation)
        if not segments or len(segments[-1].points) < 2:
            continue
        latest = segments[-1]
        (first_p, first), (last_p, last) = latest.points[0], latest.points[-1]
        early = _direction_from_change(last - first, params.DOSM_MIN_SHARE_CHANGE_PP)
        cited = [
            r
            for r in rows
            if r["source_id"] == "dosm_job_market_insights"
            and r["entity"] == occupation
            and r["value"] is not None
            and first_p <= r["period"] <= last_p
        ]
        missing = sorted(
            r["period"]
            for r in rows
            if r["source_id"] == "dosm_job_market_insights"
            and r["entity"] == occupation
            and r["value"] is None
        )
        note = "One source over a short comparable period."
        if latest.starts_after_break:
            note += (
                f" Comparable only from {first_p}: total online job offerings roughly "
                f"doubled the quarter before, a change in platform coverage."
            )
        if missing:
            note += f" Count not stated for {', '.join(missing)} (missing, not zero)."
        out.append(
            Signal(
                id=f"dosm_jmi_{occupation.lower().replace(' ', '_')}",
                title=f"{occupation}: share of online job ads",
                family="malaysian_job_ads",
                kind="observed",
                direction=_label(early, 1, len(latest.points), official=True),
                early_direction=early,
                headline=f"{first:.2f}% ({first_p}) → {last:.2f}% ({last_p})",
                unit="% of online job offerings",
                points=[measures_point(p) for p in latest.points],
                independent_sources=1,
                note=note,
                sources=[_source_card("dosm_job_market_insights")],
                evidence=_evidence(cited),
            )
        )
    return out


def ai_use_signals(rows: list[dict[str, Any]]) -> list[Signal]:
    country = field_profile().country
    local = measures.aei_series(rows, "pct", country)
    world = measures.aei_series(rows, "pct", "GLOBAL")
    automation = measures.aei_series(rows, "collaboration_bucket_automation_pct", "GLOBAL")
    out = []
    for entity, global_points in sorted(world.items()):
        points, geo = (
            (local[entity], country)
            if len(local.get(entity, [])) >= 2
            else (global_points, "GLOBAL")
        )
        if len(points) < 2:
            continue
        (first_p, first), (last_p, last) = points[0], points[-1]
        real = measures.is_real_change(first, last)
        early: Literal["up", "down", "flat"] = (
            "flat" if not real else ("up" if last > first else "down")
        )
        style = automation.get(entity, [])
        style_note = (
            (
                f" Globally, {style[-1][1]:.0f}% of this occupation's conversations were "
                f"automation-style ({style[-1][0]})."
            )
            if style
            else ""
        )
        cited = [
            r
            for r in rows
            if r["source_id"] == "anthropic_economic_index"
            and r["entity"] == entity
            and r["geography"] == geo
            and r["series"] == "aei_pct"
        ]
        code, name = entity.split(" ", 1)
        where = "Malaysia" if geo == country else "global"
        out.append(
            Signal(
                id=f"aei_{code}_{geo}",
                title=f"AI use · {name} ({where})",
                family="ai_task_use",
                kind="observed",
                direction="insufficient",
                early_direction=early,
                headline=(
                    f"{first:.2f}% → {last:.2f}% of sampled conversations ({first_p} → {last_p})"
                ),
                unit="% of sampled Claude conversations",
                points=[measures_point(p) for p in points],
                independent_sources=1,
                note=(
                    "Two months of one release; shows AI use, not hiring or job losses."
                    + ("" if real else " The change is within rounding.")
                    + style_note
                ),
                sources=[_source_card("anthropic_economic_index")],
                evidence=_evidence(cited),
            )
        )
    return out


def expert_signals(rows: list[dict[str, Any]]) -> list[Signal]:
    impact = [r for r in rows if r["series"] == "talentcorp_role_impact"]
    if not impact:
        return []
    high = [r for r in impact if r["value"] == IMPACT_CODE["high"]]
    skills = [r for r in rows if r["series"] == "talentcorp_in_demand_skill"]
    out = [
        Signal(
            id="talentcorp_fa_high_impact",
            title="Finance & accounting roles rated highly impacted",
            family="malaysian_role_impact",
            kind="expert",
            direction="expert",
            early_direction=None,
            headline=(
                f"{len(high)} of {len(impact)} finance & accounting roles: "
                + ", ".join(r["entity"] for r in high[:4])
                + ", …"
            ),
            unit="roles",
            points=[],
            independent_sources=1,
            note=(
                "Expert assessment of AI, digital and green-economy impact combined. Highly "
                "impacted roles need to pivot to an adjacent role and reskill (TalentCorp 2024)."
            ),
            sources=[_source_card("talentcorp_gbs_2024")],
            evidence=_evidence(high),
        )
    ]
    if skills:
        out.append(
            Signal(
                id="talentcorp_in_demand_skills",
                title="In-demand skills named for GBS",
                family="malaysian_role_impact",
                kind="expert",
                direction="expert",
                early_direction=None,
                headline=", ".join(r["entity"] for r in skills[:5]) + f", … ({len(skills)} in all)",
                unit="skills",
                points=[],
                independent_sources=1,
                note="Half are AI and digital skills, half green skills (TalentCorp 2024).",
                sources=[_source_card("talentcorp_gbs_2024")],
                evidence=_evidence(skills),
            )
        )
    return out


def build_signals(rows: list[dict[str, Any]]) -> list[Signal]:
    return (
        occupation_signals(rows)
        + job_ad_signals(rows)
        + ai_use_signals(rows)
        + expert_signals(rows)
    )
