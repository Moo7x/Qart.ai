"""Qart's industry forecast: which GBS finance roles and skills grow, transform, shrink or emerge.

Each role (data/packs/gbs_fa/industry_roles.yaml) is measured through its O*NET occupation and
gets two kinds of estimate, kept apart and both shown:

* demand – the forecast change of the share of employees in the role's DOSM occupation group over
  the forecast horizon (src/evidence/forecast.py: models chosen by a rolling backtest against
  keeping the last value), plus whether MyCOL lists the occupation as critical (hard to fill);
* AI pressure – three kinds of evidence that are never merged into one number:
    use       the importance-weighted mean automation-style share of AI use over the occupation's
              O*NET tasks: observed (Economic Index) where it exists, otherwise predicted by the
              task model (src/forecast/task_model.py), scaled by the scenario intensity;
    exposure  the ILO's mean GenAI exposure of the occupation's tasks (technical potential);
    expert    TalentCorp's impact level for the role.

Category rules (declared, INDUSTRY_* in src/params.py); "no verdict from usage alone" holds because
AI pressure needs at least two of the three kinds to agree:
    emerging      TalentCorp lists the role as emerging;
    transforming  AI pressure: >= INDUSTRY_AI_AGREE of {use, exposure, expert} are high;
    shrinking     transforming and the demand forecast falls by more than INDUSTRY_DEMAND_EPS_PP;
    growing       not transforming, and demand rises by more than INDUSTRY_DEMAND_EPS_PP or MyCOL
                  lists the occupation as critical;
    stable        otherwise.
The scenario changes `use` only (the declared share of observed AI use assumed to reach the tasks),
so switching to the fast scenario can move a role into transforming or shrinking.

Skills join through the roles that need them (roles.yaml requirements, tier weights): a skill's
demand is the weighted mean demand change of those roles, and its AI use the mean over the tasks
linked to it in those roles' occupations. Pure: rows, task rows and the pack in; dicts out.
"""

from dataclasses import dataclass, field
from typing import Any

from src import params
from src.collectors.mycol import CRITICAL_SERIES
from src.collectors.mycol import load_extraction as load_mycol
from src.evidence import forecast
from src.evidence.field import field_profile
from src.forecast.roles import industry_roles
from src.pack import Pack

Row = dict[str, Any]
LABELS = {
    "growing": "Growing",
    "transforming": "Transforming",
    "shrinking": "Shrinking",
    "emerging": "Emerging",
    "stable": "Stable",
}
MEANING = {
    "growing": "More jobs expected and AI is not reshaping most of the work.",
    "transforming": "The role stays, but AI is reshaping much of its daily work.",
    "shrinking": "AI is reshaping the work and the job group is expected to shrink.",
    "emerging": "A new role that TalentCorp expects to appear in GBS.",
    "stable": "No strong signal either way yet.",
}


def task_pressure(task_rows: list[Row]) -> dict[str, dict[str, Any]]:
    """Per occupation: importance-weighted automation-style share, and how much is observed."""
    out: dict[str, dict[str, Any]] = {}
    for soc in {r["soc"] for r in task_rows}:
        weighted = total = 0.0
        observed = predicted = 0
        for r in task_rows:
            if r["soc"] != soc:
                continue
            value = r["observed"] if r["observed"] is not None else r["predicted"]
            if value is None:
                continue
            weight = r["importance"] or params.INDUSTRY_DEFAULT_IMPORTANCE
            weighted += weight * value
            total += weight
            observed += r["observed"] is not None
            predicted += r["observed"] is None
        if total:
            out[soc] = {
                "share": round(weighted / total, 1),
                "tasks_observed": observed,
                "tasks_predicted": predicted,
            }
    return out


def _talentcorp(rows: list[Row]) -> dict[str, float]:
    return {
        r["entity"]: float(r["value"])
        for r in rows
        if r["series"] == "talentcorp_role_impact" and r["value"] is not None
    }


def _ilo(rows: list[Row]) -> dict[str, float]:
    return {
        str(r["entity"]).split()[0]: float(r["value"])
        for r in rows
        if r["series"] == "ilo_occupation_exposure" and r["value"] is not None
    }


def _critical(rows: list[Row], isco: str | None) -> bool | None:
    listed = {r["entity"] for r in rows if r["series"] == CRITICAL_SERIES}
    if not listed:
        return None  # MyCOL not collected: unknown, not "not critical"
    name = load_mycol()["field_links"].get(isco or "")
    return bool(name and name in listed)


_DEMAND_CACHE: dict[tuple[int, int], dict[str, dict[str, Any]]] = {}
DEMAND_CACHE_SIZE = 8  # snapshots kept; each backtest takes seconds, and ranking asks often


def _demand(rows: list[Row]) -> dict[str, dict[str, Any]]:
    """Forecast per DOSM occupation group: change over the horizon, model and fetch date.
    Cached per evidence snapshot (row count and newest row id): the same rows give the same
    forecast, and a new snapshot (or a person's own cutoff) gets its own entry."""
    key = _snapshot(rows)
    if key in _DEMAND_CACHE:
        return _DEMAND_CACHE[key]
    out = {}
    for entry in forecast.employment_forecasts(rows):
        group = entry["series_id"].split(":", 1)[1]
        out[group] = {
            "change_pp": forecast._change(entry),
            "model": entry.get("model"),
            "note": entry.get("note", ""),
            "source": entry.get("source"),
            "fetched": entry.get("fetched"),
        }
    if len(_DEMAND_CACHE) >= DEMAND_CACHE_SIZE:
        _DEMAND_CACHE.pop(next(iter(_DEMAND_CACHE)))
    _DEMAND_CACHE[key] = out
    return out


def categorise(
    use: float | None,
    exposure: float | None,
    impact: float | None,
    change: float | None,
    critical: bool | None,
) -> tuple[str, list[str]]:
    """The category and the reasons that decided it (see the module docstring)."""
    if impact == 0:
        return "emerging", ["TalentCorp lists it as an emerging role"]
    signals = []
    if use is not None and use >= params.INDUSTRY_USE_HIGH:
        signals.append(
            f"AI already does much of this work in practice ({use:.0f}% automation-style)"
        )
    if exposure is not None and exposure >= params.INDUSTRY_EXPOSURE_HIGH:
        signals.append(f"the ILO rates its tasks as highly exposed ({exposure:.2f} of 1)")
    if impact is not None and impact >= params.INDUSTRY_EXPERT_HIGH:
        signals.append("TalentCorp rates the AI impact on it as high")
    eps = params.INDUSTRY_DEMAND_EPS_PP
    falling = change is not None and change < -eps
    rising = change is not None and change > eps
    if len(signals) >= params.INDUSTRY_AI_AGREE:
        if falling:
            return "shrinking", [*signals, f"its job group is forecast to fall ({change:+.2f} pp)"]
        return "transforming", signals
    if rising or critical:
        why = [f"its job group is forecast to grow ({change:+.2f} pp)"] if rising else []
        return "growing", why + (["MyCOL lists it as hard to fill"] if critical else [])
    return "stable", signals or [
        "no forecast change beyond the noise and fewer than two AI signals"
    ]


@dataclass(frozen=True)
class Overrides:
    """Test values for the change test: nothing stored changes (src/api/evidence_test.py).
    occupation_use / task_use replace the automation-style AI-use share (0-100) of every task of an
    occupation or of one task; group_change replaces a DOSM job group's forecast change (points)."""

    occupation_use: dict[str, float] = field(default_factory=dict)
    task_use: dict[str, float] = field(default_factory=dict)
    group_change: dict[str, float] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.occupation_use or self.task_use or self.group_change)

    def tasks(self, task_rows: list[Row]) -> list[Row]:
        out = []
        for r in task_rows:
            value = self.task_use.get(r["task"], self.occupation_use.get(r["soc"]))
            out.append({**r, "observed": value} if value is not None else r)
        return out


_INDUSTRY_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def _snapshot(rows: list[Row]) -> tuple[int, int]:
    return len(rows), max((int(r.get("id") or 0) for r in rows), default=0)


def industry(
    pack: Pack,
    rows: list[Row],
    task_rows: list[Row],
    scenario: str,
    overrides: Overrides | None = None,
) -> dict[str, Any]:
    """Every industry role with its category, demand and AI evidence, and the skills' direction.
    Cached per evidence snapshot, task-model version and scenario: ranking asks for it often.
    Test overrides are never cached."""
    if overrides:
        return _industry(pack, rows, overrides.tasks(task_rows), scenario, overrides.group_change)
    version = task_rows[0].get("version_id") if task_rows else None
    key = (*_snapshot(rows), version, len(task_rows), scenario)
    if key not in _INDUSTRY_CACHE:
        if len(_INDUSTRY_CACHE) >= DEMAND_CACHE_SIZE * 2:
            _INDUSTRY_CACHE.pop(next(iter(_INDUSTRY_CACHE)))
        _INDUSTRY_CACHE[key] = _industry(pack, rows, task_rows, scenario)
    return _INDUSTRY_CACHE[key]


def _industry(
    pack: Pack,
    rows: list[Row],
    task_rows: list[Row],
    scenario: str,
    group_change: dict[str, float] | None = None,
) -> dict[str, Any]:
    intensity = params.SCENARIO_INTENSITY[scenario]
    pressure = task_pressure(task_rows)
    impacts, ilo, demand = _talentcorp(rows), _ilo(rows), _demand(rows)
    if group_change:
        demand = {
            g: {**d, "change_pp": group_change.get(g, d["change_pp"])} for g, d in demand.items()
        }
    roles: list[dict[str, Any]] = []
    role_change: dict[str, float] = {}
    for role in industry_roles().roles:
        occupation = field_profile().occupation(role.soc) if role.soc else None
        isco = occupation.isco if occupation else None
        group = forecast._group_of(role.soc) if role.soc else None
        dem = demand.get(group or "", {})
        change = dem.get("change_pp")
        press = pressure.get(role.soc or "")
        use = round(press["share"] * intensity, 1) if press else None
        exposure = ilo.get(isco or "")
        impact = impacts.get(role.talentcorp or "")
        critical = _critical(rows, isco)
        category, reasons = categorise(use, exposure, impact, change, critical)
        if role.pack_role and change is not None:
            role_change[role.pack_role] = change
        roles.append(
            {
                "id": role.id,
                "title": role.title,
                "soc": role.soc,
                "occupation": occupation.name if occupation else None,
                "soc_reason": role.soc_reason,
                "destination": role.pack_role in pack.destination_roles,
                "pack_role": role.pack_role,
                "category": category,
                "label": LABELS[category],
                "meaning": MEANING[category],
                "reasons": reasons,
                "demand": {"group": group, "critical": critical, **dem},
                "ai": {
                    "use": use,
                    "use_observed_share": press["share"] if press else None,
                    "tasks_observed": press["tasks_observed"] if press else 0,
                    "tasks_predicted": press["tasks_predicted"] if press else 0,
                    "exposure": exposure,
                    "talentcorp_impact": impact,
                },
            }
        )
    return {
        "scenario": scenario,
        "intensity": intensity,
        "roles": roles,
        "skills": skill_directions(pack, task_rows, role_change, intensity),
    }


def skill_directions(
    pack: Pack, task_rows: list[Row], role_change: dict[str, float], intensity: float
) -> list[dict[str, Any]]:
    """Each required skill: demand through its roles, AI use on its linked tasks, direction."""
    by_task = {
        (r["soc"], r["task"]): (r["observed"] if r["observed"] is not None else r["predicted"])
        for r in task_rows
    }
    out = []
    for skill in pack.skills.values():
        weights = demand = 0.0
        uses: list[float] = []
        needed_by = []
        for role in pack.destination_roles.values():
            req = next((q for q in role.requires if q.skill == skill.id), None)
            if req is None:
                continue
            needed_by.append(role.title)
            weight = params.ROLE_TIER_WEIGHT[req.tier]
            if role.id in role_change:
                demand += weight * role_change[role.id]
                weights += weight
            for link in pack.tasks_for(role.soc, skill.id):
                value = by_task.get((role.soc, str(link.task)))
                if value is not None:
                    uses.append(value * intensity)
        if not needed_by:
            continue
        change = round(demand / weights, 3) if weights else None
        use = round(sum(uses) / len(uses), 1) if uses else None
        direction = params.AI_ROLE_DIRECTION[skill.ai_role]
        if direction < 0 and use is not None and use >= params.INDUSTRY_USE_HIGH:
            trend = "declining"  # routine work that AI already does in practice
        elif direction > 0 or (change is not None and change > params.INDUSTRY_DEMAND_EPS_PP):
            trend = "rising"
        else:
            trend = "steady"
        out.append(
            {
                "skill": skill.id,
                "name": skill.name,
                "trend": trend,
                "ai_role": skill.ai_role,
                "demand_change_pp": change,
                "ai_use": use,
                "needed_by": needed_by,
            }
        )
    return sorted(
        out, key=lambda s: ({"rising": 0, "steady": 1, "declining": 2}[s["trend"]], s["name"])
    )
