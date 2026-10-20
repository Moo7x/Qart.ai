"""Snapshot build, ingest filtering and diff → suggested assumption reviews (Task A1).

tests/fixtures/aei_sample.csv copies a few real AEI release_2026_06_26 rows (CC-BY) plus rows that
the filter must drop (sub-occupation, major group, other occupation, subregion, other metric).
"""

from pathlib import Path

from src.contract import ReviewTrigger
from src.engine.catalogue import default_catalogue
from src.engine.ingest import build_all, read_finance_rows, run_ingest
from src.engine.snapshots import compare_signals, diff, diff_report, load_snapshots

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_SNAPSHOTS = Path(__file__).resolve().parent.parent / "data" / "snapshots"


def triggers() -> list[ReviewTrigger]:
    return default_catalogue().assumptions_v1.review_triggers


def test_filter_keeps_only_finance_detailed_occupations_and_overall_shares() -> None:
    rows = read_finance_rows(FIXTURES / "aei_sample.csv")
    assert {r.soc_code for r in rows} == {"43-3031", "13-2011", None}
    assert {r.geo for r in rows} == {"GLOBAL", "MYS"}
    assert all(r.metric != "usage_pct" for r in rows)
    assert len(rows) == 10


def test_one_dated_snapshot_per_period_with_source_and_licence() -> None:
    snaps = build_all(read_finance_rows(FIXTURES / "aei_sample.csv"), triggers(), "2026-10-21")
    assert [s.id for s in snaps] == ["snap_aei_2026_04", "snap_aei_2026_05"]
    for snap in snaps:
        assert snap.release_date == "2026-06-26"
        assert snap.retrieved_at == "2026-10-21"
        assert snap.url.startswith("https://huggingface.co/datasets/Anthropic/EconomicIndex")
        assert snap.licence and "CC-BY" in snap.licence
        assert snap.label and "historical data replay" in snap.label
    assert snaps[0].suggested_assumption_reviews == []


def test_bookkeeping_usage_rise_suggests_reviews_but_rounding_noise_does_not() -> None:
    april, may = build_all(read_finance_rows(FIXTURES / "aei_sample.csv"), triggers(), "x")
    reviews = {r.assumption_id: r.reason for r in diff(april, may, triggers())}
    assert set(reviews) == {
        "assistive.check_entries",
        "assistive.match_transactions",
        "agentic.prepare_adjustments",
    }
    assert "0.30→0.32" in reviews["assistive.check_entries"]
    assert "Apr 2026→May 2026" in reviews["assistive.check_entries"]
    # 13-2011 moved 0.11 → 0.12: below the 0.02 minimum, treated as rounding noise.
    assert "assistive.prepare_adjustments" not in reviews


def test_diff_never_touches_weights_and_reports_every_change() -> None:
    april, may = build_all(read_finance_rows(FIXTURES / "aei_sample.csv"), triggers(), "x")
    before = default_catalogue().assumptions_v1.model_copy(deep=True)
    report = diff_report(april, may, triggers())
    assert default_catalogue().assumptions_v1 == before
    assert report.label == "historical data replay: Apr 2026 → May 2026"
    assert "not proof of task replacement" in report.note
    assert report.changes[0].significant
    changes = {(c.entity, c.geo): c for c in compare_signals(april, may) if c.metric == "usage_pct"}
    bookkeeping = changes[("SOC 43-3031 Bookkeeping, Accounting, and Auditing Clerks", "GLOBAL")]
    assert bookkeeping.change == 0.02 and bookkeeping.relative_change is not None


def test_run_ingest_offline_writes_snapshot_files(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "aei_claude_ai_2026-06-26.csv").write_text(
        (FIXTURES / "aei_sample.csv").read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = run_ingest(raw, tmp_path / "snaps", allow_download=False, retrieved_at="2026-10-21")
    assert result.snapshot_ids == ["snap_aei_2026_04", "snap_aei_2026_05"]
    assert [s.id for s in load_snapshots(tmp_path / "snaps")] == result.snapshot_ids


def test_committed_snapshots_are_the_april_and_may_2026_periods() -> None:
    april, may = load_snapshots(REPO_SNAPSHOTS)
    assert (april.period, may.period) == ("2026-04", "2026-05")
    assert any(
        r.assumption_id == "assistive.check_entries" for r in may.suggested_assumption_reviews
    )
