"""Signal computation and labels (AI_SIGNAL_SPEC §4) on small synthetic series."""

import pytest

from src.signals.compute import build_points, change_12m, label_for, skill_signals
from src.signals.config import default_config

PARAMS = default_config().params
MONTHS = [f"{2024 + i // 12}-{i % 12 + 1:02d}" for i in range(24)]
TOTAL = 400


def ramp(start: int, end: int) -> list[int]:
    """12 flat months at `start`, then 12 months moving linearly to `end`."""
    step = (end - start) / 11
    return [start] * 12 + [round(start + step * i) for i in range(12)]


@pytest.mark.parametrize(
    ("mentions", "expected"),
    [
        (ramp(20, 80), "rising"),
        ([40] * 24, "stable"),
        (ramp(80, 20), "cooling"),
        ([2] * 24, "insufficient_data"),
    ],
)
def test_labels_on_synthetic_series(mentions: list[int], expected: str) -> None:
    points = build_points(MONTHS, mentions, [TOTAL] * 24, PARAMS)
    assert label_for(points, PARAMS) == expected


def test_insufficient_data_overrides_a_rising_shape() -> None:
    # Rising from 0 to 4 a month: the shape rises, but recent mentions average below 5.
    points = build_points(MONTHS, ramp(0, 4), [TOTAL] * 24, PARAMS)
    assert label_for(points, PARAMS) == "insufficient_data"


def test_short_history_is_insufficient_not_stable() -> None:
    points = build_points(MONTHS[:6], [30] * 6, [TOTAL] * 6, PARAMS)
    assert points[-1].ma_long is None
    assert label_for(points, PARAMS) == "insufficient_data"


def test_moving_averages_index_and_change() -> None:
    mentions = [10] * 12 + [20] * 12
    points = build_points(MONTHS, mentions, [100] * 24, PARAMS)
    assert points[1].ma_short is None and points[2].ma_short == pytest.approx(0.10)
    assert points[11].ma_long == pytest.approx(0.10)
    assert points[-1].ma_short == pytest.approx(0.20) and points[-1].ma_long == pytest.approx(0.20)
    assert points[0].index == 100 and points[-1].index == 200
    assert change_12m(points) == pytest.approx(1.0)


def test_skill_signals_count_posts_once_and_keep_the_window() -> None:
    posts = {m: ["Python and SQL", "Python, Python", "Hiring a designer"] for m in MONTHS}
    signals = {s.id: s for s in skill_signals(posts, default_config().skills, PARAMS)}
    python = signals["python"]
    assert python.points[-1].mentions == 2 and python.points[-1].total_posts == 3
    assert python.latest_sample_size == 2 and python.latest_total_posts == 3
    assert len(python.points) == len(MONTHS) <= PARAMS.window_months
    assert signals["pytorch"].latest_sample_size == 0
