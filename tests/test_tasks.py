"""Task view shows each evidence kind from its own rows, latest period first, missing as None."""

from typing import Any

from src.match.tasks import task_view
from src.pack import load_pack


def row(
    source: str, series: str, entity: str, geo: str, period: str, value: float, **extra: Any
) -> dict[str, Any]:
    return {
        "source_id": source,
        "series": series,
        "entity": entity,
        "geography": geo,
        "period": period,
        "value": value,
        "url": f"https://{source}.example.test",
        "cited_span": extra.get("cited_span", ""),
        "published": extra.get("published"),
    }


ROWS = [
    row(
        "anthropic_economic_index",
        "aei_task_pct",
        "21515 Prepare adjusting journal entries.",
        "GLOBAL",
        "2026-04",
        0.01,
    ),
    row(
        "anthropic_economic_index",
        "aei_task_pct",
        "21515 Prepare adjusting journal entries.",
        "GLOBAL",
        "2026-05",
        0.02,
    ),
    row(
        "anthropic_economic_index",
        "aei_task_pct",
        "21515 Prepare adjusting journal entries.",
        "MYS",
        "2026-05",
        0.05,
    ),
    row(
        "anthropic_economic_index",
        "aei_task_collaboration_bucket_automation_pct",
        "21515 Prepare adjusting journal entries.",
        "GLOBAL",
        "2026-05",
        61.4,
    ),
    row("onet_database", "onet_task_importance", "21515 13-2011.00", "US", "31.0", 4.29),
    row(
        "ilo_genai_exposure_2025",
        "ilo_occupation_exposure",
        "2411 Accountants",
        "GLOBAL",
        "2025",
        0.51,
        cited_span="ILO · ISCO-08 2411 Accountants · mean 0.51 · gradient: Exposed: Gradient 3",
        published="2025-05-20",
    ),
    row(
        "ilo_genai_exposure_2025",
        "ilo_task_exposure",
        "2411.2 Preparing financial statements;",
        "GLOBAL",
        "2025",
        0.65,
    ),
    row(
        "ilo_genai_exposure_2025",
        "ilo_task_exposure",
        "2411.3 Preparing tax returns;",
        "GLOBAL",
        "2025",
        0.465,
    ),
]


def test_each_evidence_kind_comes_from_its_own_rows() -> None:
    pack = load_pack()
    view = task_view(pack, pack.destination_roles["fixed_assets_accountant"], ROWS, "medium")
    journal = next(t for t in view["tasks"] if t["task"] == "21515")
    assert journal["skills"] == ["General Ledger Accounting"]
    use = journal["observed_use"]
    assert (use["share"], use["share_local"], use["automation"], use["period"]) == (
        0.02,
        0.05,
        61.4,
        "2026-05",
    )
    assert use["augmentation"] is None  # not published for this task: missing, not zero
    assert journal["importance"]["value"] == 4.29 and journal["importance"]["release"] == "31.0"
    exposure = view["exposure"]
    assert (exposure["isco"], exposure["mean"], exposure["gradient"]) == (
        "2411",
        0.51,
        "Exposed: Gradient 3",
    )
    assert [t["score"] for t in exposure["tasks"]] == [0.65, 0.465]  # highest first
    assert view["deployment"] is None
    assert "1 of" in view["summary"] and "estimate of technical potential" in view["summary"]


def test_tasks_without_rows_have_no_observed_use() -> None:
    pack = load_pack()
    view = task_view(pack, pack.destination_roles["fixed_assets_accountant"], ROWS, "medium")
    others = [t for t in view["tasks"] if t["task"] != "21515"]
    assert others and all(t["observed_use"] is None and t["importance"] is None for t in others)
