"""Every stored text fits its column. Postgres enforces VARCHAR lengths; SQLite does not, so
without this check a value can pass every local test and fail on the deployed database."""

import json
from pathlib import Path

from sqlalchemy import String

from src.collectors import aei, dosm_jmi, dosm_wages, talentcorp
from src.evidence.store import Observation, observation_table

FIXTURES = Path(__file__).parent / "fixtures"


def sample_observations() -> list[Observation]:
    rows = json.loads((FIXTURES / "dosm_wages_occupation.json").read_text(encoding="utf-8"))
    out = dosm_wages.parse(rows)
    for name in ("q1_2026", "q2_2023", "q1_2024"):
        page = (FIXTURES / "dosm_jmi" / f"{name}.html").read_text(encoding="utf-8")
        out += dosm_jmi.release_observations(dosm_jmi.parse_release(name, page))
    with (FIXTURES / "aei_sample.csv").open(encoding="utf-8", newline="") as handle:
        # Use every metric the collector keeps, so the longest unit labels are covered.
        out += aei.parse_rows(handle, "2026-06-26", "https://example.test")
    out += talentcorp.parse(talentcorp.load_extraction())
    return out


def test_every_text_value_fits_its_varchar_column() -> None:
    limits = {
        c.name: c.type.length
        for c in observation_table.columns
        if isinstance(c.type, String) and c.type.length
    }
    too_long = []
    for obs in sample_observations():
        values = {**obs.__dict__, "content_hash": obs.content_hash()}
        for column, limit in limits.items():
            value = values.get(column)
            if isinstance(value, str) and len(value) > limit:
                too_long.append((column, len(value), limit, value[:60]))
    assert too_long == []


def test_longest_declared_units_fit() -> None:
    unit_type = observation_table.c.unit.type
    assert isinstance(unit_type, String) and unit_type.length is not None
    unit_limit = unit_type.length
    units = list(aei.GLOBAL_METRICS.values()) + [talentcorp.IMPACT_UNIT]
    assert max(len(u) for u in units) <= unit_limit
