"""Compare the same profile and scenario against two supplied evidence snapshots.

No fetching, database access, LLM calls or changes to a person's skills. A replay changes only
one source's observation-period cutoff; all other reference data stays fixed and is labelled so.
"""

from typing import Any, Literal

from pydantic import BaseModel

from src import params
from src.journey.store import ProfileData
from src.match.engine import Scenario, rank_roles
from src.match.evidence import automation_evidence
from src.pack import Pack
from src.pathway.planner import plan_pathway

Row = dict[str, Any]
# Numerical comparison tolerance, not a threshold for career significance.
EPSILON = 1e-9
REPLAY_SOURCES = {"anthropic_economic_index", "dosm_job_market_insights"}


class EvidenceDelta(BaseModel):
    source_id: str
    entity: str
    metric: str
    geography: str
    before_period: str | None
    after_period: str | None
    before: float | None
    after: float | None
    unit: str
    url: str
    published: str | None
    cited_span: str
    comparable: bool


class WeightDelta(BaseModel):
    skill: str
    name: str
    before: float
    after: float
    points_before: float
    points_after: float
    essential: bool
    reason: str


class RoleDelta(BaseModel):
    role_id: str
    title: str
    soc: str
    rank_before: int
    rank_after: int
    fit_before: float
    fit_after: float
    weights: list[WeightDelta]


class CourseRef(BaseModel):
    id: str
    title: str
    url: str


class PathSummary(BaseModel):
    course_ids: list[str]
    courses: list[CourseRef]
    hours: float
    weeks: int
    essential_gaps: list[str]


class PathDelta(BaseModel):
    role_id: str
    title: str
    before: PathSummary
    after: PathSummary
    added: list[str]
    removed: list[str]
    reordered: bool


class ChangeReport(BaseModel):
    mode: Literal["live", "replay"]
    scenario: Scenario
    before_label: str
    after_label: str
    evidence: list[EvidenceDelta]
    roles: list[RoleDelta]
    pathway: PathDelta | None
    recommendation_changed: bool
    notes: list[str]


def _latest(rows: list[Row]) -> dict[tuple[str, ...], Row]:
    latest: dict[tuple[str, ...], Row] = {}
    for row in rows:
        key = (row["source_id"], row["series"], row["entity"], row["geography"])
        previous = latest.get(key)
        if previous is None or row["period"] >= previous["period"]:
            latest[key] = row
    return latest


def evidence_deltas(before: list[Row], after: list[Row]) -> list[EvidenceDelta]:
    """Latest observed cells, never a synthetic adoption percentage or causal attribution."""
    old, new = _latest(before), _latest(after)
    out = []
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        if (
            a
            and b
            and all(
                a.get(field) == b.get(field)
                for field in ("value", "period", "method_version", "unit")
            )
        ):
            continue
        row = b or a
        assert row is not None
        out.append(
            EvidenceDelta(
                source_id=row["source_id"],
                entity=row["entity"],
                metric=row["series"],
                geography=row["geography"],
                before_period=a["period"] if a else None,
                after_period=b["period"] if b else None,
                before=a["value"] if a else None,
                after=b["value"] if b else None,
                unit=row["unit"],
                url=row["url"],
                published=row.get("published"),
                cited_span=row["cited_span"],
                comparable=bool(
                    a
                    and b
                    and a["method_version"] == b["method_version"]
                    and a["unit"] == b["unit"]
                ),
            )
        )
    # A correction to an older observation matters even if the latest month's value stayed the
    # same. It belongs in the audit trail without pretending it changed today's recommendation.
    older = {
        (r["source_id"], r["series"], r["entity"], r["geography"], r["period"]): r for r in before
    }
    for row in after:
        key = (row["source_id"], row["series"], row["entity"], row["geography"], row["period"])
        previous = older.get(key)
        is_latest = new[key[:-1]]["period"] == row["period"]
        if not is_latest and (
            previous is None
            or any(previous.get(k) != row.get(k) for k in ("value", "unit", "method_version"))
        ):
            out.extend(evidence_deltas([previous] if previous else [], [row]))
    return out


def compare(
    pack: Pack,
    profile: ProfileData,
    destination: str | None,
    before: list[Row],
    after: list[Row],
    scenario: Scenario,
    mode: Literal["live", "replay"],
    before_label: str,
    after_label: str,
) -> ChangeReport:
    """Recompute rankings, exact weight/contribution differences and the chosen path."""
    levels = profile.levels()
    old_evidence, new_evidence = automation_evidence(before), automation_evidence(after)
    old = rank_roles(pack, levels, scenario, old_evidence, set(profile.interests))
    new = rank_roles(pack, levels, scenario, new_evidence, set(profile.interests))
    old_by_id = {role.role_id: (i, role) for i, role in enumerate(old, 1)}
    roles = []
    for i, role in enumerate(new, 1):
        old_rank, previous = old_by_id[role.role_id]
        old_weights = {r.skill: r for r in previous.requirements}
        weights = [
            WeightDelta(
                skill=r.skill,
                name=r.skill_name,
                before=old_weights[r.skill].weight,
                after=r.weight,
                points_before=old_weights[r.skill].contribution,
                points_after=r.contribution,
                essential=r.essential,
                reason=r.shift_reason,
            )
            for r in role.requirements
            if abs(r.weight - old_weights[r.skill].weight) > EPSILON
            or abs(r.contribution - old_weights[r.skill].contribution) > EPSILON
        ]
        roles.append(
            RoleDelta(
                role_id=role.role_id,
                title=role.title,
                soc=role.soc,
                rank_before=old_rank,
                rank_after=i,
                fit_before=previous.fit,
                fit_after=role.fit,
                weights=weights,
            )
        )
    path_delta = None
    if destination:
        previous = old_by_id[destination][1]
        current = next(r for r in new if r.role_id == destination)
        paths = [
            plan_pathway(pack, match, levels, profile.weekly_hours, scenario, evidence)
            for match, evidence in ((previous, old_evidence), (current, new_evidence))
        ]
        summaries = [
            PathSummary(
                course_ids=[s.course.id for s in path.steps],
                courses=[
                    CourseRef(id=s.course.id, title=s.course.title, url=s.course.url)
                    for s in path.steps
                ],
                hours=path.total_hours,
                weeks=path.weeks,
                essential_gaps=path.essentials_unmet,
            )
            for path in paths
        ]
        a, b = summaries
        path_delta = PathDelta(
            role_id=destination,
            title=pack.destination_roles[destination].title,
            before=a,
            after=b,
            added=[c for c in b.course_ids if c not in a.course_ids],
            removed=[c for c in a.course_ids if c not in b.course_ids],
            reordered=a.course_ids != b.course_ids and set(a.course_ids) == set(b.course_ids),
        )
    changed = any(r.fit_before != r.fit_after or r.rank_before != r.rank_after for r in roles)
    changed = changed or bool(path_delta and path_delta.before != path_delta.after)
    return ChangeReport(
        mode=mode,
        scenario=scenario,
        before_label=before_label,
        after_label=after_label,
        evidence=evidence_deltas(before, after),
        roles=roles,
        pathway=path_delta,
        recommendation_changed=changed,
        notes=[
            "The profile, essential requirements and selected destination are held fixed.",
            "Global occupation-level AI usage informs declared scenario weights, not a "
            "measured Malaysian adoption rate. Fit is not a hiring probability.",
            "Job-ad observations provide demand context; the current fit formula uses skills "
            "and AI-use emphasis, so a job-ad update alone does not alter fit.",
            *(
                [
                    "Historical source replay: only the selected source's observation-period "
                    "cutoff changes. Other reference data is held fixed; this is not an as-of "
                    "historical hiring forecast. Replaying never changes your saved journey."
                ]
                if mode == "replay"
                else []
            ),
        ],
    )


def replay_periods(rows: list[Row], source_id: str) -> list[str]:
    if source_id not in REPLAY_SOURCES:
        raise ValueError("this source does not support replay")
    return sorted({r["period"] for r in rows if r["source_id"] == source_id})


def replay_rows(
    rows: list[Row], source_id: str, before: str, after: str
) -> tuple[list[Row], list[Row]]:
    """Cut only the selected source at two real observation periods; reject method breaks."""
    periods = replay_periods(rows, source_id)
    if before not in periods or after not in periods or before >= after:
        raise ValueError("choose two available periods, with before earlier than after")
    methods = [
        {r["method_version"] for r in rows if r["source_id"] == source_id and r["period"] == period}
        for period in (before, after)
    ]
    if methods[0] != methods[1] or len(methods[0]) != 1:
        raise ValueError("source methods differ; these periods cannot be compared")
    if source_id == "dosm_job_market_insights":
        totals = sorted(
            (r["period"], r["value"])
            for r in rows
            if r["source_id"] == source_id
            and r["entity"] == "all occupations"
            and r["value"] is not None
        )
        for (previous_period, previous), (period, total) in zip(totals, totals[1:], strict=False):
            if (
                before < period <= after
                and previous_period >= before
                and previous > 0
                and abs(total / previous - 1) > params.JOB_AD_BREAK_RATIO
            ):
                raise ValueError("possible job-ad coverage break; choose periods on the same side")
    snapshots = [
        [r for r in rows if r["source_id"] != source_id or r["period"] <= period]
        for period in (before, after)
    ]
    return snapshots[0], snapshots[1]
