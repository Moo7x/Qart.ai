"""Weekly and monthly trend metrics from the job store (pure functions).

A posting counts as open in a period when it was seen during it: first_seen <= period end and
last_seen >= period start. Per period and region: open postings, how many mention AI, and the
share. Shares from fewer than `min_sample` postings are reported as None ("insufficient"), never
as a number. For the latest week: the share of postings mentioning each tracked skill, and the
AI share per role family, by region. These describe the companies covered, not the whole market.
"""

from collections.abc import Sequence
from datetime import date, timedelta

from src.jobs.store import StoredJob

DECIMALS = 1


def week_bounds(day: date) -> tuple[str, date, date]:
    year, week, _ = day.isocalendar()
    start = day - timedelta(days=day.weekday())
    return f"{year}-W{week:02d}", start, start + timedelta(days=6)


def month_bounds(day: date) -> tuple[str, date, date]:
    start = day.replace(day=1)
    nxt = (start + timedelta(days=32)).replace(day=1)
    return f"{start:%Y-%m}", start, nxt - timedelta(days=1)


def periods(first: date, last: date, granularity: str) -> list[tuple[str, date, date]]:
    bounds = week_bounds if granularity == "week" else month_bounds
    out, day = [], first
    while day <= last:
        label, start, end = bounds(day)
        out.append((label, start, end))
        day = end + timedelta(days=1)
    return out


def open_in(jobs: Sequence[StoredJob], start: date, end: date) -> list[StoredJob]:
    s, e = start.isoformat(), end.isoformat()
    return [j for j in jobs if j.first_seen <= e and j.last_seen >= s]


def share(part: int, total: int, min_sample: int) -> float | None:
    return round(100 * part / total, DECIMALS) if total >= min_sample else None


def ai_series(
    jobs: Sequence[StoredJob],
    regions: Sequence[str],
    first: date,
    last: date,
    granularity: str,
    min_sample: int,
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for region in regions:
        points: list[dict[str, object]] = []
        for label, start, end in periods(first, last, granularity):
            open_jobs = [j for j in open_in(jobs, start, end) if region in j.regions]
            ai = sum(j.mentions_ai for j in open_jobs)
            points.append(
                {
                    "period": label,
                    "total": len(open_jobs),
                    "ai": ai,
                    "share_pct": share(ai, len(open_jobs), min_sample),
                }
            )
        out.append({"region": region, "granularity": granularity, "points": points})
    return out


def latest_breakdowns(
    jobs: Sequence[StoredJob],
    regions: Sequence[str],
    skill_names: dict[str, str],
    last: date,
    min_sample: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """(skill shares, AI share per role family) for the week of `last`, by region."""
    _, start, end = week_bounds(last)
    current = open_in(jobs, start, end)
    skills, families = [], []
    for region in regions:
        here = [j for j in current if region in j.regions]
        for skill_id, name in skill_names.items():
            n = sum(skill_id in j.skills for j in here)
            skills.append(
                {
                    "region": region,
                    "skill_id": skill_id,
                    "name": name,
                    "mentions": n,
                    "total": len(here),
                    "share_pct": share(n, len(here), min_sample),
                }
            )
        for family in sorted({j.family for j in here if j.family}):
            fam = [j for j in here if j.family == family]
            ai = sum(j.mentions_ai for j in fam)
            families.append(
                {
                    "region": region,
                    "family": family,
                    "total": len(fam),
                    "ai": ai,
                    "share_pct": share(ai, len(fam), min_sample),
                }
            )
    return skills, families
