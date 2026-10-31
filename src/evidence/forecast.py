"""Forecasts of the trend series, each chosen by a rolling backtest against keeping the last value.

Series: the OpenDOSM share of employees per major occupation group (annual), and the DOSM online
job-ad total and Professionals share (quarterly, only after the last coverage break).

Models, all declared:
* naive, drift, linear, damped, smoothing – the simple methods already in `measures`;
* theta     – simple exponential smoothing plus half the fitted linear trend (the classic Theta
              method's two-line form, Assimakopoulos & Nikolopoulos 2000);
* gbr       – a global gradient-boosting model (scikit-learn): it learns next year's change from
              the last changes and the level, trained across all occupation groups at once.

Choice: at every origin of a rolling backtest each model only sees the past and is scored on the
value h steps later. A model's score is its mean absolute error divided by keeping the last value
(naive) at the same origins, averaged over the horizons. The lowest score wins only if it is below
NAIVE_RATIO_TO_BEAT; otherwise the forecast is the last value and says so. Intervals are the
chosen model's own backtest errors (10th–90th percentile), so they are empirical, not assumed.

Outlooks for the person's screens keep their components apart:
* role_outlook  – the forecast for the role's occupation group (estimate);
* skill_outlook – the average forecast change of the groups of the roles that need the skill
                  (estimate), beside the observed automation-style AI use on its tasks. They are
                  never merged into one "automated" verdict.
Pure: rows and the pack in, plain dicts out. Retrospective backtests use today's published
series, not the values DOSM had published at each origin.
"""

import statistics
from collections.abc import Callable
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor  # type: ignore[import-untyped]

from src import params
from src.evidence import measures
from src.evidence.field import field_profile
from src.match.engine import Evidence, requirement_automation
from src.match.outlook import MAJOR_GROUP
from src.pack import Pack

Row = dict[str, Any]
Point = tuple[str, float]
LOCAL_METHODS = measures.ROLLING_METHODS + ("theta",)
GBR = "gbr"
NAIVE = "naive"
QUARTERS = 4

GROUP_TITLES = {
    "managers": "Managers",
    "professionals": "Professionals",
    "technicians": "Technicians and associate professionals",
    "clerical": "Clerical support workers",
    "service_sales": "Service and sales workers",
    "agriculture": "Skilled agricultural, forestry and fishery workers",
    "craft": "Craft and related trades workers",
    "operators": "Plant and machine operators and assemblers",
    "elementary": "Elementary occupations",
}


def _local(method: str, values: list[float], steps: int) -> float:
    history = list(enumerate(values))
    if method == "theta":
        level = values[0]
        for value in values[1:]:
            level = params.SMOOTHING_ALPHA * value + (1 - params.SMOOTHING_ALPHA) * level
        slope = float(np.polyfit(range(len(values)), values, 1)[0])
        return level + 0.5 * slope * steps
    return measures.forecast_one(method, history, steps)


# ---- the global gradient-boosting model --------------------------------------------------------


def _features(values: list[float], t: int, group: int, groups: int) -> list[float]:
    changes = [values[t - k] - values[t - k - 1] for k in range(params.GBR_LAGS)]
    onehot = [1.0 if g == group else 0.0 for g in range(groups)]
    return [*changes, values[t], *onehot]


def gbr_fit(series: dict[str, list[float]]) -> HistGradientBoostingRegressor | None:
    """Fit next-step change on lagged changes, level and group, across all series."""
    names = sorted(series)
    x_rows, y_rows = [], []
    for g, name in enumerate(names):
        values = series[name]
        for t in range(params.GBR_LAGS, len(values) - 1):
            x_rows.append(_features(values, t, g, len(names)))
            y_rows.append(values[t + 1] - values[t])
    if len(y_rows) < params.GBR_MIN_TRAIN_ROWS:
        return None
    model = HistGradientBoostingRegressor(
        max_depth=params.GBR_MAX_DEPTH,
        max_iter=params.GBR_MAX_ITER,
        random_state=params.GBR_RANDOM_STATE,
    )
    model.fit(np.array(x_rows), np.array(y_rows))
    return model


def gbr_predict(
    model: HistGradientBoostingRegressor, values: list[float], group: int, groups: int, steps: int
) -> float:
    """Recursive forecast: each predicted change is appended before predicting the next."""
    path = list(values)
    for _ in range(steps):
        change = float(model.predict(np.array([_features(path, len(path) - 1, group, groups)]))[0])
        path.append(path[-1] + change)
    return path[-1]


# ---- backtest and choice ----------------------------------------------------------------------

Forecaster = Callable[[str, list[float], int], float]


def _backtest(
    values: list[float], forecaster: Forecaster, methods: tuple[str, ...]
) -> tuple[dict[str, dict[int, list[float]]], int]:
    """Signed errors (actual − forecast) per method and horizon over every rolling origin."""
    errors: dict[str, dict[int, list[float]]] = {
        m: {h: [] for h in params.FORECAST_HORIZONS} for m in methods
    }
    origins = 0
    for i in range(params.FORECAST_MIN_HISTORY - 1, len(values) - 1):
        origins += 1
        for h in params.FORECAST_HORIZONS:
            if i + h >= len(values):
                continue
            for m in methods:
                errors[m][h].append(values[i + h] - forecaster(m, values[: i + 1], h))
    return errors, origins


def _ratios(errors: dict[str, dict[int, list[float]]]) -> dict[str, float]:
    """Each method's mean absolute error ÷ naive's, averaged over horizons with errors."""
    out = {}
    for method, by_h in errors.items():
        parts = []
        for h, errs in by_h.items():
            naive = errors[NAIVE][h]
            if errs and naive and statistics.fmean(abs(e) for e in naive) > 0:
                parts.append(
                    statistics.fmean(abs(e) for e in errs) / statistics.fmean(abs(e) for e in naive)
                )
        if parts:
            out[method] = round(statistics.fmean(parts), 3)
    return out


def _next_period(period: str, steps: int) -> str:
    if "-Q" in period:
        year, quarter = period.split("-Q")
        index = int(year) * QUARTERS + int(quarter) - 1 + steps
        return f"{index // QUARTERS}-Q{index % QUARTERS + 1}"
    return str(int(period) + steps)


def forecast_series(
    series_id: str,
    kind: str,
    title: str,
    points: list[Point],
    source: str,
    fetched_at: str | None,
    forecaster: Forecaster,
    methods: tuple[str, ...],
) -> dict[str, Any]:
    """One series: its history, the chosen model, its backtest and the forecast with interval."""
    values = [v for _, v in points]
    base: dict[str, Any] = {
        "series_id": series_id,
        "kind": kind,
        "title": title,
        "history": [{"period": p, "value": round(v, 3)} for p, v in points],
        "forecast": [],
        "model": None,
        "baseline": NAIVE,
        "backtest": None,
        "label": "estimate",
        "source": source,
        "fetched_at": fetched_at,
        "note": "",
    }
    if len(values) < params.FORECAST_MIN_HISTORY + 1:
        base["note"] = (
            f"Only {len(values)} comparable points: too few to test a forecast, so none is shown."
        )
        return base
    errors, origins = _backtest(values, forecaster, methods)
    ratios = _ratios(errors)
    best = min(ratios, key=lambda m: ratios[m]) if ratios else NAIVE
    chosen = best if ratios.get(best, 1.0) < params.NAIVE_RATIO_TO_BEAT else NAIVE
    out = []
    for h in params.FORECAST_HORIZONS:
        point = forecaster(chosen, values, h)
        errs = errors[chosen][h]
        low = high = None
        if len(errs) >= params.MIN_INTERVAL_ERRORS:
            q_low, q_high = np.quantile(errs, params.INTERVAL_QUANTILES)
            low, high = round(point + float(q_low), 3), round(point + float(q_high), 3)
        out.append(
            {
                "period": _next_period(points[-1][0], h),
                "point": round(point, 3),
                "low": low,
                "high": high,
            }
        )
    base.update(
        forecast=out,
        model=chosen,
        backtest={
            "ratio": ratios.get(chosen, 1.0),
            "baseline_ratio": 1.0,
            "ratios": ratios,
            "origins": origins,
            "scale": "mean absolute error ÷ keeping the last value, at the same origins",
        },
        note=(
            "No model beat keeping the last value in the backtest, so the forecast is the "
            "last value."
            if chosen == NAIVE
            else ""
        ),
    )
    return base


# ---- the series ---------------------------------------------------------------------------------


def _fetched(rows: list[Row], source_id: str) -> str | None:
    dates = [r["fetched_at"] for r in rows if r["source_id"] == source_id and r.get("fetched_at")]
    return str(max(dates)) if dates else None


def employment_forecasts(rows: list[Row]) -> list[dict[str, Any]]:
    shares = measures.occupation_shares(rows)
    names = sorted(shares)
    values = {name: [v for _, v in shares[name]] for name in names}
    # One global model per cut-off year, shared by every group's backtest.
    cache: dict[int, HistGradientBoostingRegressor | None] = {}

    def forecaster_for(name: str) -> Forecaster:
        def forecast(method: str, history: list[float], steps: int) -> float:
            if method != GBR:
                return _local(method, history, steps)
            cut = len(history)  # the global model only sees the same years from every group
            if cut not in cache:
                cache[cut] = gbr_fit({n: v[:cut] for n, v in values.items()})
            model = cache[cut]
            if model is None:
                return _local(NAIVE, history, steps)
            return gbr_predict(model, history, names.index(name), len(names), steps)

        return forecast

    fetched = _fetched(rows, "dosm_wages_occupation")
    return [
        forecast_series(
            f"employment_share:{name}",
            "employment_share",
            f"{GROUP_TITLES.get(name, name)}: share of employees (%)",
            shares[name],
            "OpenDOSM wages_occupation, employees by occupation group",
            fetched,
            forecaster_for(name),
            (*LOCAL_METHODS, GBR),
        )
        for name in names
    ]


def job_ad_forecasts(rows: list[Row]) -> list[dict[str, Any]]:
    ads = [
        r for r in rows if r["source_id"] == "dosm_job_market_insights" and r["value"] is not None
    ]
    totals = sorted(
        (r["period"], float(r["value"])) for r in ads if r["entity"] == "all occupations"
    )
    shares = sorted(
        (r["period"], float(r["value"])) for r in ads if r["series"] == "online_job_offerings_share"
    )
    breaks = [
        q
        for (_, prev), (q, total) in zip(totals, totals[1:], strict=False)
        if prev and abs(total / prev - 1) > params.JOB_AD_BREAK_RATIO
    ]
    start = breaks[-1] if breaks else ""
    fetched = _fetched(rows, "dosm_job_market_insights")
    out = []
    for series_id, title, points in (
        ("job_ads:total", "Online job ads in Malaysia (count)", totals),
        ("job_ads:professionals_share", "Professionals' share of online job ads (%)", shares),
    ):
        since = [(p, v) for p, v in points if p >= start]
        entry = forecast_series(
            series_id,
            "job_ads",
            title,
            since,
            "DOSM Big Data Analytics: Job Market Insights",
            fetched,
            _local,
            LOCAL_METHODS,
        )
        if start:
            entry["note"] = (
                f"Counted from {start}, after a jump in the total that DOSM does not explain "
                f"(a possible change in platform coverage). {entry['note']}".strip()
            )
        out.append(entry)
    return out


def _group_of(soc: str) -> str | None:
    occupation = field_profile().occupation(soc)
    return MAJOR_GROUP.get(occupation.isco[0]) if occupation and occupation.isco else None


def _change(entry: dict[str, Any]) -> float | None:
    if not entry["forecast"]:
        return None
    return round(float(entry["forecast"][-1]["point"]) - float(entry["history"][-1]["value"]), 3)


def outlooks(
    pack: Pack, employment: list[dict[str, Any]], evidence: Evidence
) -> list[dict[str, Any]]:
    """Role outlooks from their group's forecast; skill outlooks with their components apart."""
    by_group = {e["series_id"].split(":", 1)[1]: e for e in employment}
    out: list[dict[str, Any]] = []
    role_change: dict[str, float] = {}
    for role in pack.destination_roles.values():
        group = _group_of(role.soc)
        entry = by_group.get(group) if group else None
        if entry is None:
            continue
        change = _change(entry)
        if change is not None:
            role_change[role.id] = change
        out.append(
            {
                **entry,
                "series_id": f"role_outlook:{role.id}",
                "kind": "role_outlook",
                "title": role.title,
                "components": {
                    "group": group,
                    "group_title": GROUP_TITLES.get(group or "", group),
                    "change_pp": change,
                    "talentcorp_impact": role.impact,
                },
                "note": (
                    f"Forecast for {GROUP_TITLES.get(group or '', group)}, the occupation group of "
                    f"this role, not for the role itself. {entry['note']}"
                ).strip(),
            }
        )
    skills: dict[str, list[str]] = {}
    for role in pack.destination_roles.values():
        for req in role.requires:
            skills.setdefault(req.skill, []).append(role.id)
    for skill_id, role_ids in sorted(skills.items()):
        changes = [role_change[r] for r in role_ids if r in role_change]
        shares = [
            share
            for r in role_ids
            if (
                share := requirement_automation(
                    pack, pack.destination_roles[r], skill_id, evidence
                )[0]
            )
            is not None
        ]
        skill = pack.skills[skill_id]
        out.append(
            {
                "series_id": f"skill_outlook:{skill_id}",
                "kind": "skill_outlook",
                "title": skill.name,
                "history": [],
                "forecast": [],
                "model": None,
                "baseline": NAIVE,
                "backtest": None,
                "label": "estimate",
                "source": (
                    "OpenDOSM forecast of the roles' occupation groups; Anthropic Economic Index"
                ),
                "fetched_at": None,
                "components": {
                    "demand_change_pp": round(statistics.fmean(changes), 3) if changes else None,
                    "roles": len(role_ids),
                    "ai_use_share": round(statistics.fmean(shares), 1) if shares else None,
                    "ai_use_period": evidence.automation_period,
                    "ai_role": skill.ai_role,
                },
                "note": (
                    "Two separate parts: the forecast change in the share of employees in the "
                    "occupation groups of the roles that need this skill (estimate), and the "
                    "observed share of automation-style AI use on its tasks. Neither says the "
                    "skill is being automated."
                ),
            }
        )
    return out


def forecasts(pack: Pack, rows: list[Row], evidence: Evidence) -> list[dict[str, Any]]:
    employment = employment_forecasts(rows)
    return [*employment, *job_ad_forecasts(rows), *outlooks(pack, employment, evidence)]
