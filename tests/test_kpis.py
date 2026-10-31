"""Report figures (B9) compute offline from the app's own API, over the pinned Phase 1 skills."""

from scripts import kpis
from src.levels import required_skills
from src.pack import load_pack


def test_figures_compute_offline_over_the_pinned_phase1_denominator() -> None:
    k = kpis.compute()
    cov = k["coverage"]
    assert cov["denominator"] == len(kpis.PHASE1_REQUIRED) == 37
    assert set(kpis.PHASE1_REQUIRED) <= set(required_skills(load_pack()))
    assert cov["covered"] + len(cov["uncovered"]) == 37
    assert cov["target_count"] == 34


def test_every_persona_number_is_labelled_and_fairness_holds() -> None:
    k = kpis.compute()
    assert {p["persona"] for p in k["personas"]} == {"hafiz", "mei", "nur", "kavitha"}
    assert all(p["numbers"] > 0 and p["unlabelled"] == [] for p in k["personas"])
    assert k["fairness"]["identical"] is True


def test_the_report_states_whether_the_target_is_met() -> None:
    text = kpis.render(kpis.compute())
    assert "Phase 1 baseline: 27/37" in text
    assert ("meets the target" in text) or ("is below the target" in text)
    assert "Do not edit by hand" in text
