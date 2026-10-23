"""Measures and labels reproduce the published numbers; gates stop thin evidence becoming a trend.

The numbers pinned here come from the real OpenDOSM and DOSM releases fetched on 2026-10-23.
"""

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from src.collectors import dosm_jmi, dosm_wages, talentcorp
from src.evidence import measures, signals
from src.evidence.store import Observation

FIXTURES = Path(__file__).parent / "fixtures"
FETCHED = datetime(2026, 10, 23, tzinfo=UTC)


def as_rows(observations: list[Observation]) -> list[dict[str, Any]]:
    return [{**o.__dict__, "fetched_at": FETCHED} for o in observations]


@pytest.fixture(scope="module")
def wage_rows() -> list[dict[str, Any]]:
    raw = json.loads((FIXTURES / "dosm_wages_occupation_full.json").read_text(encoding="utf-8"))
    return as_rows(dosm_wages.parse(raw))


def test_clerical_share_and_headcount_match_dosm(wage_rows: list[dict[str, Any]]) -> None:
    shares = dict(measures.occupation_shares(wage_rows)["clerical"])
    assert round(shares["2011"], 2) == 14.52
    assert round(shares["2025"], 2) == 13.10
    heads = dict(measures.headcounts(wage_rows, "clerical"))
    assert (heads["2011"], heads["2025"]) == (1108.6, 1360.1)


def test_2010_is_left_out_because_of_the_classification_break(
    wage_rows: list[dict[str, Any]],
) -> None:
    years = [p for p, _ in measures.occupation_shares(wage_rows)["professionals"]]
    assert years[0] == "2011"
    assert round(dict(measures.occupation_shares(wage_rows)["professionals"])["2025"], 2) == 18.74


def test_backtest_is_reproducible_and_no_change_wins_for_clerical(
    wage_rows: list[dict[str, Any]],
) -> None:
    row = measures.backtest(measures.occupation_shares(wage_rows)["clerical"], "clerical")
    assert (round(row.naive, 2), round(row.linear, 2), round(row.damped, 2)) == (0.48, 0.95, 0.88)
    assert row.best == "naive"


def test_occupation_labels_follow_the_declared_threshold(wage_rows: list[dict[str, Any]]) -> None:
    by_id = {s.id: s for s in signals.occupation_signals(wage_rows)}
    assert by_id["dosm_share_clerical"].direction == "weakening"
    assert by_id["dosm_share_professionals"].direction == "rising"
    assert by_id["dosm_share_technicians"].direction == "stable"  # -0.20 pts < 0.5
    assert "not extrapolated" in by_id["dosm_share_clerical"].note


def jmi_rows(quarters: Mapping[str, tuple[int, int | None]]) -> list[dict[str, Any]]:
    out = []
    for quarter, (total, accountants) in quarters.items():
        release = dosm_jmi.Release(
            slug=quarter,
            quarter=quarter,
            published="2026-08-18",
            next_release=None,
            total=total,
            total_span="total",
            accountants=accountants,
            accountants_span="acc",
        )
        out.extend(dosm_jmi.release_observations(release))
    return as_rows(out)


REAL_JMI = {  # (total, accountants) as published by DOSM
    "2025-Q1": (263_083, 9_462),
    "2025-Q2": (281_736, 9_990),
    "2025-Q3": (588_148, 17_587),
    "2025-Q4": (587_801, 20_111),
    "2026-Q1": (626_861, 24_784),
    "2026-Q2": (555_509, 22_067),
}


def test_coverage_break_splits_the_job_ad_series() -> None:
    segments = measures.job_ad_segments(jmi_rows(REAL_JMI), "Accountants and Auditors")
    assert [len(s.points) for s in segments] == [2, 4]
    assert segments[1].starts_after_break
    latest = dict(segments[1].points)
    assert round(latest["2025-Q4"], 2) == 3.42
    assert round(latest["2026-Q2"], 2) == 3.97


def test_one_short_job_ad_series_is_not_enough_for_a_label() -> None:
    (signal,) = signals.job_ad_signals(jmi_rows(REAL_JMI))
    assert signal.direction == "insufficient"
    assert signal.early_direction == "up"


def test_unstated_count_stays_missing() -> None:
    rows = jmi_rows(
        {
            "2024-Q1": (392_054, None),
            "2024-Q2": (335_205, None),
            "2024-Q4": (276_624, 9_422),
            "2025-Q1": (263_083, 9_462),
        }
    )
    segments = measures.job_ad_segments(rows, "Accountants and Auditors")
    assert [p for p, _ in segments[0].points] == ["2024-Q4", "2025-Q1"]


def test_economic_index_rounding_is_not_a_change() -> None:
    assert not measures.is_real_change(0.11, 0.12)  # 0.01 points: within rounding
    assert measures.is_real_change(0.28, 0.30)  # 0.02 points and 7%: counts (float-safe)
    assert measures.is_real_change(0.59, 0.56)


def test_expert_view_is_never_labelled_as_a_trend() -> None:
    rows = as_rows(talentcorp.parse(talentcorp.load_extraction()))
    expert = signals.expert_signals(rows)
    assert {s.direction for s in expert} == {"expert"}
    assert expert[0].headline.startswith("11 of 24")


def test_rolling_backtest_scores_every_origin_without_looking_ahead() -> None:
    from src.evidence.measures import rolling_backtest

    series = [(str(y), 10.0 + 0.5 * (y - 2011)) for y in range(2011, 2026)]  # a straight line
    one = rolling_backtest(series, 1)
    assert one["origins"] == list(range(2015, 2025))
    assert one["mae"]["linear"] < 1e-9 and one["mae"]["drift"] < 1e-9
    assert one["mae"]["naive"] == 0.5 and one["best"] in {"linear", "drift"}
    assert rolling_backtest(series, 2)["origins"][-1] == 2023
