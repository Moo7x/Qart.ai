"""The pipeline logs every run, says "no change" honestly, and survives a failing source."""

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine

from src import params
from src.collectors.base import Collect, CollectorResult, SourceState
from src.db import init_db, make_engine
from src.evidence.store import Observation, acquire_lock, list_runs, query_observations
from src.pipeline import run as pipeline

ClientFactory = Callable[[], httpx.Client]


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{(tmp_path / 'p.sqlite').as_posix()}")
    init_db(engine)
    return engine


@pytest.fixture
def offline() -> ClientFactory:
    """Collectors are faked, so the client must never be used for a real request."""
    return lambda: httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))


def fake(source_id: str, value: float) -> Collect:
    def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
        observation = Observation(
            source_id=source_id,
            series="s",
            entity="e",
            geography="MYS",
            period="2025",
            value=value,
            unit="u",
            url="https://example.test",
            cited_span="row",
            method_version="v1",
        )
        return CollectorResult([observation], note="fake")

    return collect


def broken(client: httpx.Client, state: SourceState) -> CollectorResult:
    raise httpx.ConnectError("source is down")


def all_fakes() -> dict[str, Collect]:
    return {
        "dosm_wages": fake("dosm_wages_occupation", 1.0),
        "dosm_jmi": fake("dosm_job_market_insights", 2.0),
        "aei": fake("anthropic_economic_index", 3.0),
        "talentcorp": fake("talentcorp_gbs_2024", 4.0),
        "onet": fake("onet_database", 5.0),
        "ilo": fake("ilo_genai_exposure_2025", 6.0),
    }


def test_second_identical_run_is_no_change(
    engine: Engine, offline: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline, "COLLECTORS", all_fakes())
    first = pipeline.run_pipeline(engine, "manual", offline, retry_pause=0)
    second = pipeline.run_pipeline(engine, "schedule", offline, retry_pause=0)
    assert (first.status, first.new_observations) == ("changed", 6)
    assert (second.status, second.new_observations) == ("no change", 0)
    assert [r["status"] for r in list_runs(engine, 5)] == ["no change", "changed"]


def test_failing_source_is_retried_logged_and_others_still_stored(
    engine: Engine, offline: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    collectors = all_fakes()
    collectors["aei"] = broken
    monkeypatch.setattr(pipeline, "COLLECTORS", collectors)
    summary = pipeline.run_pipeline(engine, "manual", offline, retry_pause=0)
    assert summary.status == "partial"
    failed = next(r for r in summary.sources if r["source_id"] == "anthropic_economic_index")
    assert failed["status"] == "failed"
    assert failed["attempts"] == pipeline.MAX_ATTEMPTS
    assert "ConnectError" in failed["error"]
    assert len(query_observations(engine)) == 5  # the other five sources


def test_run_is_skipped_while_another_holds_the_lock(
    engine: Engine, offline: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline, "COLLECTORS", all_fakes())
    assert acquire_lock(engine, pipeline.LOCK_NAME, "other-run", timedelta(minutes=5))
    summary = pipeline.run_pipeline(engine, "manual", offline, retry_pause=0)
    assert summary.status == "skipped: locked"
    assert list_runs(engine, 5) == []


def test_an_unexpected_error_in_one_source_does_not_stop_the_others(
    engine: Engine, offline: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explodes(client: httpx.Client, state: SourceState) -> CollectorResult:
        raise RuntimeError("database constraint")

    collectors = all_fakes()
    collectors["dosm_jmi"] = explodes
    monkeypatch.setattr(pipeline, "COLLECTORS", collectors)
    summary = pipeline.run_pipeline(engine, "manual", offline, retry_pause=0)
    assert summary.status == "partial"
    assert list_runs(engine, 1)[0]["status"] == "partial"  # the run record is closed


def test_evidence_is_stale_without_runs_and_after_a_day(
    engine: Engine, offline: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import UTC, datetime

    assert pipeline.is_stale(engine)
    monkeypatch.setattr(pipeline, "COLLECTORS", all_fakes())
    pipeline.run_pipeline(engine, "manual", offline, retry_pause=0)
    assert not pipeline.is_stale(engine)
    later = datetime.now(UTC) + timedelta(hours=params.RUN_STALE_AFTER_HOURS + 1)
    assert pipeline.is_stale(engine, now=later)
