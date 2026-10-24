"""Task view of one destination role: four kinds of task-change evidence, kept separate (PLAN §4.3).

1. observed AI use   – Anthropic Economic Index rows for each linked O*NET task (observed)
2. reported deployment – organisations saying they use AI for the task: not collected in the MVP
                         (the research agent is improvement-phase work), so shown as missing
3. potential exposure – ILO GenAI exposure of the role's ISCO-08 occupation (an estimate of
                         technical potential, model-assisted, occupation level)
4. expert impact     – TalentCorp impact level of the role (expert view; AI, digital and green
                         drivers combined, as the study does not separate them)

Pure: rows from the evidence store and the pack go in, a dict for the API comes out. No verdict
such as "being automated" is produced; the summary only restates what each source shows.
"""

from typing import Any

from src.collectors.ilo import OCCUPATION_SERIES, TASK_SERIES, gradient_of
from src.evidence.field import field_profile
from src.match.evidence import IMPORTANCE_SERIES
from src.pack import DestinationRole, Pack

Row = dict[str, Any]
AEI = "anthropic_economic_index"
TASK_METRICS = {
    "aei_task_pct": "share",
    "aei_task_collaboration_bucket_automation_pct": "automation",
    "aei_task_collaboration_bucket_augmentation_pct": "augmentation",
}


def _latest(rows: list[Row]) -> dict[tuple[str, str, str], Row]:
    """Latest row per (series, entity id, geography)."""
    out: dict[tuple[str, str, str], Row] = {}
    for row in rows:
        key = (row["series"], row["entity"].split(" ", 1)[0], row["geography"])
        if key not in out or row["period"] >= out[key]["period"]:
            out[key] = row
    return out


def _value(latest: dict[tuple[str, str, str], Row], series: str, entity: str, geo: str) -> Any:
    row = latest.get((series, entity, geo))
    return None if row is None else row["value"]


def task_view(
    pack: Pack, role: DestinationRole, rows: list[Row], impact_text: str
) -> dict[str, Any]:
    latest = _latest(rows)
    country = field_profile().country
    tasks: dict[str, dict[str, Any]] = {}
    for req in role.requires:
        for link in pack.tasks_for(role.soc, req.skill):
            task = str(link.task)
            entry = tasks.setdefault(task, {"task": task, "text": link.text, "skills": []})
            entry["skills"].append(pack.skills[req.skill].name)
    for task, entry in tasks.items():
        observed = {
            name: _value(latest, series, task, "GLOBAL") for series, name in TASK_METRICS.items()
        }
        observed["share_local"] = _value(latest, "aei_task_pct", task, country)
        aei_row = latest.get(("aei_task_pct", task, "GLOBAL"))
        entry["observed_use"] = (
            {**observed, "period": aei_row["period"], "url": aei_row["url"]} if aei_row else None
        )
        onet_row = latest.get((IMPORTANCE_SERIES, task, "US"))
        entry["importance"] = (
            {"value": onet_row["value"], "release": onet_row["period"], "url": onet_row["url"]}
            if onet_row
            else None
        )
    occupation = field_profile().occupation(role.soc)
    exposure = None
    if occupation and occupation.isco:
        ilo = latest.get((OCCUPATION_SERIES, occupation.isco, "GLOBAL"))
        if ilo:
            exposure = {
                "isco": occupation.isco,
                "title": ilo["entity"].split(" ", 1)[1],
                "mean": ilo["value"],
                "gradient": gradient_of(ilo["cited_span"]),
                "url": ilo["url"],
                "published": ilo.get("published"),
                "tasks": sorted(
                    (
                        {"text": r["entity"].split(" ", 1)[1], "score": r["value"]}
                        for (series, entity, _), r in latest.items()
                        if series == TASK_SERIES and entity.split(".")[0] == occupation.isco
                    ),
                    key=lambda t: -(t["score"] or 0.0),
                ),
            }
    listed = list(tasks.values())
    with_use = [t for t in listed if t["observed_use"]]
    return {
        "role_id": role.id,
        "soc": role.soc,
        "occupation": occupation.model_dump() if occupation else None,
        "tasks": listed,
        "exposure": exposure,
        "expert": {"impact": role.impact, "text": impact_text},
        "deployment": None,
        "summary": _summary(len(listed), len(with_use), exposure, role.impact),
        "unlinked_skills": [
            pack.skills[r.skill].name
            for r in role.requires
            if not pack.tasks_for(role.soc, r.skill)
        ],
        "sources": {
            "tasks": pack.tasks.source + " · " + pack.tasks.licence,
            "observed_use": "Anthropic Economic Index, sampled Claude conversations (CC-BY)",
            "exposure": "ILO Working Paper 140 (2025), CC BY 4.0, via the ESCO–O*NET crosswalk",
            "expert": "TalentCorp (2024) GBS study, PDF p. 25–26",
        },
    }


def _summary(n: int, observed: int, exposure: dict[str, Any] | None, impact: str) -> str:
    parts = [
        f"{observed} of {n} linked tasks appear in sampled Claude conversations (observed use)."
        if n
        else "No O*NET task is linked to this role's skills yet."
    ]
    if exposure:
        parts.append(
            f"The ILO rates its occupation ({exposure['title']}) '{exposure['gradient']}': "
            "an estimate of technical potential, not of adoption."
        )
    parts.append(f"TalentCorp rates the role {impact} impact (expert view).")
    parts.append("No source here reports organisations deploying AI for these tasks yet.")
    return " ".join(parts)
