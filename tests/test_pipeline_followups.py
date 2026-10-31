"""Steps after collection run on their own: one failing never skips another or the run status."""

from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine

from src.db import init_db, make_engine
from src.pipeline import run as pipeline
from tests.test_pipeline import all_fakes


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{(tmp_path / 'p.sqlite').as_posix()}")
    init_db(engine)
    return engine


def offline() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))


def _down(*_: object) -> str:
    raise httpx.ConnectError("O*NET is down")


def test_a_failing_catalogue_refresh_still_builds_the_index(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    built: list[bool] = []
    monkeypatch.setattr(pipeline, "COLLECTORS", all_fakes())
    monkeypatch.setattr(pipeline, "refresh_catalogue", _down)
    monkeypatch.setattr(pipeline, "build_index", lambda *a: built.append(True) or "index built")
    monkeypatch.setattr(pipeline, "fill_isco", lambda *a: "isco filled")
    summary = pipeline.run_pipeline(engine, "manual", offline, retry_pause=0)
    row = next(r for r in summary.sources if r["source_id"] == "occupation_index")
    assert built and row["status"] == "failed"
    assert row["error"].startswith("catalogue: ConnectError")
    assert row["note"] == "index built; isco filled"
    assert summary.status == "changed"  # follow-up steps never change the run's status


def test_a_failing_proposal_refresh_is_logged_without_failing_the_run(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline, "COLLECTORS", all_fakes())
    monkeypatch.setattr(pipeline, "refresh_proposals", _down)
    summary = pipeline.run_pipeline(engine, "manual", offline, retry_pause=0)
    assert summary.status == "changed"
    assert any(r["source_id"] == "proposals" and r["status"] == "failed" for r in summary.sources)
    assert {"trend_models", "occupation_index", "link_check", "retention"} <= {
        r["source_id"] for r in summary.sources
    }
