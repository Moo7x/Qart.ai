from types import SimpleNamespace

from src import params
from src.collectors.onet import RELATED_SERIES
from src.match import directions


def test_related_tier_reads_onet_links_and_same_occupation() -> None:
    rows = [{"series": RELATED_SERIES, "entity": "43-3031.00 13-2011.00", "value": 2.0}]
    assert directions.related_tier(rows, "43-3031.00", "13-2011.00") == 2
    assert directions.related_tier(rows, "13-2011.00", "13-2011.00") == 0
    assert directions.related_tier(rows, "43-3031.00", "15-1211.00") is None
    assert directions.related_tier(rows, None, "15-1211.00") is None


def test_direction_is_adjacent_for_close_occupations_or_high_fit() -> None:
    assert directions.direction(10.0, 1) == "adjacent"
    assert directions.direction(params.DIRECTION_ADJACENT_FIT, None) == "adjacent"
    assert directions.direction(10.0, 3) == "stretch"


def test_outlook_reorders_close_fits_but_not_distant_ones() -> None:
    a, b, c = (
        SimpleNamespace(role_id=i, fit=f) for i, f in (("a", 50.0), ("b", 48.0), ("c", 20.0))
    )
    forecasts = {
        "b": {"category": "growing"},
        "a": {"category": "shrinking"},
        "c": {"category": "growing"},
    }
    ordered = [m.role_id for m in directions.order([a, b, c], forecasts)]  # type: ignore[list-item]
    assert ordered == ["b", "a", "c"]  # a growing role passes a close shrinking one, not a far one
