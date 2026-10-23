"""Per-skill monthly signal and its label (AI_SIGNAL_SPEC §4). Pure functions, no I/O.

For each skill and month: mentions (posts matching it), total_posts, share = mentions/total.
  index      = share rebased so the first month with enough mentions = index_base (100)
  ma_short   = trailing mean of share over ma_short_months (3); None until that many months
  ma_long    = trailing mean of share over ma_long_months (12)
  change_12m = ma_short now / ma_short 12 months earlier − 1
Label, checked in this order:
  insufficient_data  mean mentions over the last 6 months < 5, or no 12-month history yet
  rising             ma_short > ma_long × 1.10 and change_12m > +15 %
  cooling            ma_short < ma_long × 0.90 and change_12m < −15 %
  stable             anything else
Months are calendar months: a month with no thread is kept as a gap (total_posts 0, share
None), so lags and averages never slide onto the wrong months; any average or change whose window
touches a gap is None, which makes the label insufficient_data.
These are trend signals from one tech-hiring source, never predictions.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from src.signals.config import SignalParams, SkillSpec
from src.signals.matcher import compile_skills, skills_in_post

Label = Literal["rising", "stable", "cooling", "insufficient_data"]
CHANGE_LAG_MONTHS = 12  # change_12m compares with the same moving average a year earlier
DECIMALS = 4


@dataclass(frozen=True)
class MonthPoint:
    month: str
    mentions: int
    total_posts: int
    share: float | None  # None for a month with no thread
    index: float | None
    ma_short: float | None
    ma_long: float | None


@dataclass(frozen=True)
class SkillSignal:
    id: str
    name: str
    category: str
    label: Label
    change_12m: float | None
    latest_sample_size: int  # posts mentioning the skill in the latest month
    latest_total_posts: int
    points: list[MonthPoint]


def _trailing_mean(values: Sequence[float | None], end: int, k: int) -> float | None:
    if end + 1 < k:
        return None
    window = values[end + 1 - k : end + 1]
    if any(v is None for v in window):
        return None  # the window touches a month with no data
    return sum(v for v in window if v is not None) / k


def calendar_months(first: str, last: str) -> list[str]:
    """Every YYYY-MM from `first` to `last` inclusive."""
    start = int(first[:4]) * 12 + int(first[5:7]) - 1
    end = int(last[:4]) * 12 + int(last[5:7]) - 1
    return [f"{i // 12}-{i % 12 + 1:02d}" for i in range(start, end + 1)]


def build_points(
    months: Sequence[str], mentions: Sequence[int], totals: Sequence[int], params: SignalParams
) -> list[MonthPoint]:
    shares: list[float | None] = [
        m / t if t else None for m, t in zip(mentions, totals, strict=True)
    ]
    base = next(
        (
            s
            for m, s in zip(mentions, shares, strict=True)
            if m >= params.min_mentions_per_month and s
        ),
        None,
    )
    points = []
    for i, month in enumerate(months):
        ma_s = _trailing_mean(shares, i, params.ma_short_months)
        ma_l = _trailing_mean(shares, i, params.ma_long_months)
        points.append(
            MonthPoint(
                month=month,
                mentions=mentions[i],
                total_posts=totals[i],
                share=round(share, DECIMALS) if (share := shares[i]) is not None else None,
                index=round(share / base * params.index_base, 2)
                if base and share is not None
                else None,
                ma_short=round(ma_s, DECIMALS) if ma_s is not None else None,
                ma_long=round(ma_l, DECIMALS) if ma_l is not None else None,
            )
        )
    return points


def change_12m(points: Sequence[MonthPoint]) -> float | None:
    if len(points) <= CHANGE_LAG_MONTHS:
        return None
    now, then = points[-1].ma_short, points[-1 - CHANGE_LAG_MONTHS].ma_short
    if now is None or not then:
        return None
    return round(now / then - 1, DECIMALS)


def label_for(points: Sequence[MonthPoint], params: SignalParams) -> Label:
    recent = points[-params.min_mentions_window_months :]
    if not recent or sum(p.mentions for p in recent) / len(recent) < params.min_mentions_per_month:
        return "insufficient_data"
    last, change = points[-1], change_12m(points)
    if last.ma_short is None or last.ma_long is None or change is None:
        return "insufficient_data"
    if last.ma_short > last.ma_long * params.rising_ma_ratio and change > params.rising_change_12m:
        return "rising"
    if (
        last.ma_short < last.ma_long * params.cooling_ma_ratio
        and change < params.cooling_change_12m
    ):
        return "cooling"
    return "stable"


def skill_signals(
    posts_by_month: Mapping[str, Sequence[str]], skills: Sequence[SkillSpec], params: SignalParams
) -> list[SkillSignal]:
    """Signals for every configured skill over the months given (oldest first after sorting)."""
    available = sorted(posts_by_month)
    months = (
        calendar_months(available[0], available[-1])[-params.window_months :] if available else []
    )
    compiled = compile_skills(skills)
    hits = {m: [skills_in_post(p, compiled) for p in posts_by_month.get(m, [])] for m in months}
    totals = [len(posts_by_month.get(m, [])) for m in months]
    out = []
    for spec in skills:
        mentions = [sum(spec.id in h for h in hits[m]) for m in months]
        points = build_points(months, mentions, totals, params)
        out.append(
            SkillSignal(
                id=spec.id,
                name=spec.name,
                category=spec.category,
                label=label_for(points, params),
                change_12m=change_12m(points),
                latest_sample_size=mentions[-1] if mentions else 0,
                latest_total_posts=totals[-1] if totals else 0,
                points=points,
            )
        )
    return out
