"""Measures computed from stored observations. Pure functions: rows in, numbers out.

Rows are the dicts returned by store.query_observations (latest version of each fact).
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from src import params

Row = dict[str, Any]
Point = tuple[str, float]  # (period, value)
PUBLISHED_DECIMALS = 2  # the Economic Index rounds every value to 0.01


@dataclass(frozen=True)
class BacktestRow:
    """Mean absolute error (percentage points) of each model on the test years."""

    group: str
    naive: float
    linear: float
    damped: float

    @property
    def best(self) -> str:
        errors = {"naive": self.naive, "linear": self.linear, "damped": self.damped}
        return min(errors, key=lambda name: errors[name])


@dataclass(frozen=True)
class Segment:
    """A run of quarters with comparable platform coverage."""

    points: list[Point]  # (quarter, share in %)
    starts_after_break: bool


def occupation_shares(rows: list[Row]) -> dict[str, list[Point]]:
    """Share of employees (%) per occupation group and year, from the first comparable year.

    share(group, year) = 100 × employees(group, year) ÷ employees(overall, year)
    """
    by_year: dict[str, dict[int, float]] = defaultdict(dict)
    for row in rows:
        if row["source_id"] == "dosm_wages_occupation" and row["value"] is not None:
            by_year[row["entity"]][int(row["period"])] = float(row["value"])
    overall = by_year.pop("overall", {})
    shares: dict[str, list[Point]] = {}
    for group, values in by_year.items():
        years = sorted(y for y in values if y >= params.DOSM_FIRST_COMPARABLE_YEAR and y in overall)
        shares[group] = [(str(y), 100 * values[y] / overall[y]) for y in years]
    return shares


def headcounts(rows: list[Row], group: str) -> list[Point]:
    points = [
        (str(r["period"]), float(r["value"]))
        for r in rows
        if r["source_id"] == "dosm_wages_occupation"
        and r["entity"] == group
        and r["value"] is not None
        and int(r["period"]) >= params.DOSM_FIRST_COMPARABLE_YEAR
    ]
    return sorted(points)


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least-squares line y = a + b·x."""
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / sum(
        (x - mean_x) ** 2 for x in xs
    )
    return mean_y - slope * mean_x, slope


def backtest(
    series: list[Point], group: str, train_end: int = params.BACKTEST_TRAIN_END
) -> BacktestRow:
    """Fit on years ≤ train_end, score each model on the later years.

    naive:  every test year = the last training value (no change)
    linear: straight line fitted on all training years
    damped: last value + recent slope, damped by phi each year ahead
    """
    train = [(int(p), v) for p, v in series if int(p) <= train_end]
    test = [(int(p), v) for p, v in series if int(p) > train_end]
    if len(train) < params.DAMPED_TREND_FIT_YEARS or not test:
        raise ValueError(f"{group}: not enough years for the backtest")
    last = train[-1][1]
    a, b = _ols([float(y) for y, _ in train], [v for _, v in train])
    recent = train[-params.DAMPED_TREND_FIT_YEARS :]
    _, b_recent = _ols([float(y) for y, _ in recent], [v for _, v in recent])

    def damped(steps: int) -> float:
        return last + b_recent * sum(params.DAMPED_TREND_PHI**k for k in range(1, steps + 1))

    return BacktestRow(
        group=group,
        naive=statistics.fmean(abs(last - v) for _, v in test),
        linear=statistics.fmean(abs(a + b * y - v) for y, v in test),
        damped=statistics.fmean(abs(damped(y - train_end) - v) for y, v in test),
    )


def job_ad_segments(rows: list[Row], occupation: str) -> list[Segment]:
    """The occupation's share of online job offerings per quarter, split at coverage breaks.

    A break is a quarter whose *total* changed by more than JOB_AD_BREAK_RATIO; shares on either
    side are not compared. Quarters where DOSM did not state the count are left out (missing).
    """
    totals: dict[str, float] = {}
    counts: dict[str, float] = {}
    for row in rows:
        if row["source_id"] != "dosm_job_market_insights" or row["value"] is None:
            continue
        target = totals if row["entity"] == "all occupations" else counts
        if row["entity"] in ("all occupations", occupation):
            target[row["period"]] = float(row["value"])
    segments: list[Segment] = []
    current: list[Point] = []
    after_break = False
    previous_total: float | None = None
    for quarter in sorted(totals):
        total = totals[quarter]
        if previous_total and abs(total / previous_total - 1) > params.JOB_AD_BREAK_RATIO:
            if current:
                segments.append(Segment(current, after_break))
            current, after_break = [], True
        if quarter in counts:
            current.append((quarter, 100 * counts[quarter] / total))
        previous_total = total
    if current:
        segments.append(Segment(current, after_break))
    return segments


def is_real_change(before: float, after: float) -> bool:
    """True when an Economic Index change is larger than rounding could explain."""
    # Values are published to two decimals, so compare at that precision: in floating point
    # 0.30 - 0.28 is 0.0199..., which would otherwise miss the 0.02 threshold.
    absolute = round(abs(after - before), PUBLISHED_DECIMALS)
    relative = absolute / before if before else float("inf")
    return absolute >= params.AEI_MIN_ABSOLUTE_CHANGE and relative >= params.AEI_MIN_RELATIVE_CHANGE


def aei_series(rows: list[Row], metric: str, geography: str) -> dict[str, list[Point]]:
    """Monthly values per occupation for one metric and geography."""
    out: dict[str, list[Point]] = defaultdict(list)
    for row in rows:
        if (
            row["source_id"] == "anthropic_economic_index"
            and row["series"] == f"aei_{metric}"
            and row["geography"] == geography
            and row["value"] is not None
        ):
            out[row["entity"]].append((row["period"], float(row["value"])))
    return {entity: sorted(points) for entity, points in out.items()}


ROLLING_METHODS = ("naive", "drift", "linear", "damped", "smoothing")


def _forecast(method: str, history: list[tuple[int, float]], steps: int) -> float:
    """One forecast `steps` years after the last history point, by a named simple method."""
    years = [float(y) for y, _ in history]
    values = [v for _, v in history]
    last = values[-1]
    if method == "naive":
        return last
    if method == "drift":  # last value plus the average yearly change so far
        return last + steps * (values[-1] - values[0]) / (len(values) - 1)
    if method == "linear":
        a, b = _ols(years, values)
        return a + b * (years[-1] + steps)
    if method == "damped":
        recent = history[-params.DAMPED_TREND_FIT_YEARS :]
        _, slope = _ols([float(y) for y, _ in recent], [v for _, v in recent])
        return last + slope * sum(params.DAMPED_TREND_PHI**k for k in range(1, steps + 1))
    level = values[0]  # simple exponential smoothing: a flat forecast at the smoothed level
    for value in values[1:]:
        level = params.SMOOTHING_ALPHA * value + (1 - params.SMOOTHING_ALPHA) * level
    return level


def rolling_backtest(series: list[Point], horizon: int) -> dict[str, Any]:
    """Mean absolute error of each method over every forecast origin (time-series cross-validation).

    Origins run from ROLLING_FIRST_ORIGIN; each method only sees years up to its origin and is
    scored on the year `horizon` later. Retrospective on today's published series, not on the
    values DOSM had published at each origin.
    """
    points = [(int(p), v) for p, v in series]
    errors: dict[str, list[float]] = {m: [] for m in ROLLING_METHODS}
    origins = []
    for i, (year, _) in enumerate(points):
        if year < params.ROLLING_FIRST_ORIGIN or i + horizon >= len(points):
            continue
        history, actual = points[: i + 1], points[i + horizon][1]
        origins.append(year)
        for method in ROLLING_METHODS:
            errors[method].append(abs(_forecast(method, history, horizon) - actual))
    mae = {m: round(statistics.fmean(e), 4) for m, e in errors.items() if e}
    best = min(mae, key=lambda m: mae[m]) if mae else None
    return {"horizon": horizon, "origins": origins, "mae": mae, "best": best}
