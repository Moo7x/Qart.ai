"""Fairness twins and time-to-path checks (eval/engine_checks.py)."""

from pathlib import Path

from eval.engine_checks import TIMING_DB, fairness_twins, render, time_to_path


def test_every_synthetic_twin_gets_identical_rankings_and_paths() -> None:
    results = fairness_twins()
    assert len(results) == 12
    assert all(r.identical for r in results)


def test_time_to_path_runs_and_cleans_up(tmp_path: Path) -> None:
    timings = time_to_path(runs=2)
    assert len(timings) == 2 and all(t > 0 for t in timings)
    assert not TIMING_DB.exists()
    assert "12/12 identical" in render(fairness_twins(), timings)
