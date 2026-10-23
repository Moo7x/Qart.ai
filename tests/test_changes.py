"""Change explanations use actual engine deltas; unknowns and no-change remain honest."""

from copy import deepcopy
from typing import Any

import pytest

from src.changes.engine import compare, replay_rows
from src.journey.store import ProfileData
from src.pack import load_pack
from tests.test_api_journey import NUR


def rows(value: float, period: str = "2026-04") -> list[dict[str, Any]]:
    """Synthetic controlled inputs, not claimed historical observations."""
    return [
        {
            "source_id": "anthropic_economic_index",
            "series": "aei_collaboration_bucket_automation_pct",
            "entity": "15-2051.01 Business Intelligence Analysts",
            "geography": "GLOBAL",
            "period": period,
            "value": value,
            "unit": "% of occupation conversations",
            "url": "https://example.test/controlled-fixture",
            "published": "2026-06-26",
            "cited_span": f"synthetic test fixture: {value}",
            "method_version": "test/1",
        }
    ]


def test_comparison_recomputes_weights_and_preserves_claims_and_essentials() -> None:
    profile = ProfileData.model_validate(NUR)
    saved = deepcopy(profile)
    report = compare(
        load_pack(),
        profile,
        "o2c_reporting_analyst",
        rows(20),
        rows(80, "2026-05"),
        "fast",
        "replay",
        "April",
        "May",
    )
    assert profile == saved
    assert report.recommendation_changed
    changed = next(r for r in report.roles if r.role_id == "o2c_reporting_analyst")
    assert changed.fit_before != changed.fit_after
    assert changed.weights
    assert all(w.before == w.after for w in changed.weights if w.essential)
    assert report.pathway and report.pathway.role_id == "o2c_reporting_analyst"
    assert report.evidence[0].after == 80
    assert "not an as-of" in report.notes[-1]


def test_identical_evidence_has_no_fabricated_effect() -> None:
    report = compare(
        load_pack(),
        ProfileData.model_validate(NUR),
        None,
        rows(20),
        rows(20),
        "moderate",
        "live",
        "old",
        "new",
    )
    assert not report.recommendation_changed
    assert not report.evidence
    assert not any(r.weights for r in report.roles)
    assert report.pathway is None


def test_new_observation_period_can_have_no_recommendation_change() -> None:
    report = compare(
        load_pack(),
        ProfileData.model_validate(NUR),
        None,
        rows(20),
        rows(20, "2026-05"),
        "fast",
        "live",
        "old",
        "new",
    )
    assert report.evidence
    assert not report.recommendation_changed


def test_replay_uses_real_available_periods_and_holds_other_sources_fixed() -> None:
    other = {**rows(8)[0], "source_id": "dosm_job_market_insights", "period": "2026-Q2"}
    old, new = replay_rows(
        [*rows(20), *rows(80, "2026-05"), other], "anthropic_economic_index", "2026-04", "2026-05"
    )
    assert len(old) == 2 and len(new) == 3
    assert other in old and other in new
    with pytest.raises(ValueError, match="available periods"):
        replay_rows(old, "anthropic_economic_index", "2025-01", "2026-04")
    with pytest.raises(ValueError, match="methods differ"):
        replay_rows(
            [*rows(20), {**rows(80, "2026-05")[0], "method_version": "new/2"}],
            "anthropic_economic_index",
            "2026-04",
            "2026-05",
        )


def test_job_ad_replay_does_not_cross_the_declared_coverage_break() -> None:
    totals = [
        {
            **rows(value)[0],
            "source_id": "dosm_job_market_insights",
            "entity": "all occupations",
            "period": quarter,
        }
        for quarter, value in (("2025-Q2", 100), ("2025-Q3", 210))
    ]
    with pytest.raises(ValueError, match="coverage break"):
        replay_rows(totals, "dosm_job_market_insights", "2025-Q2", "2025-Q3")


def test_revision_of_an_older_cell_is_shown_without_inventing_a_current_fit_change() -> None:
    before = [*rows(20), *rows(60, "2026-05")]
    after = [*rows(30), *rows(60, "2026-05")]
    report = compare(
        load_pack(),
        ProfileData.model_validate(NUR),
        None,
        before,
        after,
        "fast",
        "live",
        "old",
        "new",
    )
    assert not report.recommendation_changed
    assert len(report.evidence) == 1
    assert report.evidence[0].before_period == "2026-04"
    assert (report.evidence[0].before, report.evidence[0].after) == (20, 30)
