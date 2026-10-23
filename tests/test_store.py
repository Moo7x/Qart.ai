"""Observations are immutable and deduplicated; the run lock prevents overlapping runs."""

from datetime import timedelta
from pathlib import Path

from sqlalchemy import Engine

from src.db import init_db, make_engine
from src.evidence.registry import load_registry
from src.evidence.store import (
    Observation,
    acquire_lock,
    insert_observations,
    query_observations,
    release_lock,
)

HOUR = timedelta(hours=1)


def engine_at(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{(tmp_path / 'e.sqlite').as_posix()}")
    init_db(engine)
    return engine


def obs(value: float | None, period: str = "2025") -> Observation:
    return Observation(
        source_id="dosm_wages_occupation",
        series="employees",
        entity="clerical",
        geography="MYS",
        period=period,
        value=value,
        unit="thousand persons",
        url="https://example.test",
        cited_span="row",
        method_version="v1",
    )


def test_same_fact_twice_is_stored_once(tmp_path: Path) -> None:
    engine = engine_at(tmp_path)
    assert insert_observations(engine, [obs(1360.1)], run_id=None) == 1
    assert insert_observations(engine, [obs(1360.1)], run_id=None) == 0


def test_revision_is_a_new_row_and_latest_wins(tmp_path: Path) -> None:
    engine = engine_at(tmp_path)
    insert_observations(engine, [obs(1360.1)], run_id=None)
    assert insert_observations(engine, [obs(1361.0)], run_id=None) == 1
    rows = query_observations(engine, series="employees")
    assert [r["value"] for r in rows] == [1361.0]


def test_missing_value_stays_missing(tmp_path: Path) -> None:
    engine = engine_at(tmp_path)
    insert_observations(engine, [obs(None)], run_id=None)
    assert query_observations(engine)[0]["value"] is None


def test_source_can_revise_back_to_a_previously_seen_value(tmp_path: Path) -> None:
    engine = engine_at(tmp_path)
    insert_observations(engine, [obs(100)], run_id=None)
    insert_observations(engine, [obs(200)], run_id=None)
    assert insert_observations(engine, [obs(100)], run_id=None) == 1
    assert query_observations(engine)[0]["value"] == 100
    assert query_observations(engine, through_id=2)[0]["value"] == 200
    assert insert_observations(engine, [obs(100)], run_id=None) == 0
    assert insert_observations(engine, [obs(200), obs(100)], run_id=None) == 2
    assert query_observations(engine)[0]["value"] == 100


def test_lock_blocks_a_second_holder_until_released(tmp_path: Path) -> None:
    engine = engine_at(tmp_path)
    assert acquire_lock(engine, "pipeline", "run-a", HOUR)
    assert not acquire_lock(engine, "pipeline", "run-b", HOUR)
    release_lock(engine, "pipeline", "run-a")
    assert acquire_lock(engine, "pipeline", "run-b", HOUR)


def test_expired_lock_can_be_taken_over(tmp_path: Path) -> None:
    engine = engine_at(tmp_path)
    assert acquire_lock(engine, "pipeline", "crashed-run", -HOUR)
    assert acquire_lock(engine, "pipeline", "run-b", HOUR)


def test_registry_loads_with_terms_for_every_source() -> None:
    sources = load_registry()
    assert len(sources) >= 4
    assert all(s.terms and s.terms_url and s.attribution for s in sources)
