"""Trend models are re-scored only when their data changes, and every version keeps its error."""

from pathlib import Path

import pytest
from sqlalchemy import Engine

import src.evidence.models  # noqa: F401  (registers the table before init_db)
from src.db import init_db, make_engine
from src.evidence.models import history, record_versions
from src.evidence.store import Observation, insert_observations


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{(tmp_path / 'm.sqlite').as_posix()}")
    init_db(engine)
    return engine


def wages(years: range, clerical: float = 14.0) -> list[Observation]:
    out = []
    for year in years:
        for entity, value in (("overall", 100.0), ("clerical", clerical + 0.1 * (year - 2011))):
            out.append(
                Observation(
                    source_id="dosm_wages_occupation",
                    series="employees",
                    entity=entity,
                    geography="MYS",
                    period=str(year),
                    value=value,
                    unit="thousand",
                    url="https://example.test",
                    cited_span="test",
                    method_version="test",
                )
            )
    return out


def test_new_year_adds_a_version_and_a_quiet_run_adds_none(engine: Engine) -> None:
    insert_observations(engine, wages(range(2011, 2025)), None)
    first = record_versions(engine, 1)
    quiet = record_versions(engine, 2)
    insert_observations(engine, wages(range(2025, 2026)), None)
    later = record_versions(engine, 3)
    versions = [v for v in history(engine) if v["group_id"] == "clerical"]
    assert [v["last_year"] for v in versions] == ["2024", "2025"]
    assert versions[0]["test_years"] == "2022–2024" and versions[1]["test_years"] == "2022–2025"
    assert all(v["naive"] >= 0 and v["best"] in {"naive", "linear", "damped"} for v in versions)
    assert (
        "first backtest version" in first["note"]
        and "re-scored" in later["note"]
        and "unchanged" in quiet["note"]
        and "2025" in later["note"]
    )
