"""Signal snapshots: Indeed monthly means, data_as_of, labelling, atomic writes and failures.

Fake transports only; tests never touch the network.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.signals import indeed
from src.signals.config import default_config
from src.signals.pipeline import (
    MARKET_PULSE,
    SKILL_SIGNALS,
    build_market_pulse,
    run,
    window_start,
    write_atomic,
)

CSV = (
    "date,jobcountry,AI_share_postings\n"
    "2026-08-30,AU,2.0\n2026-08-31,AU,4.0\n2026-09-01,AU,5.0\n2026-09-30,AU,7.0\n"
    "2026-09-15,US,3.0\n"
)
CFG = default_config()
NOW = datetime(2026, 10, 15, tzinfo=UTC)
THREAD = {
    "children": [
        {"text": "Python and SQL", "created_at": "2026-10-03T10:00:00Z"},
        {"text": "React", "created_at": "2026-10-07T12:00:00Z"},
    ]
}


def test_indeed_daily_values_become_monthly_means_and_data_as_of_is_the_latest_date() -> None:
    means, latest = indeed.monthly_means(CSV)
    assert means["AI"]["AU"] == {"2026-08": 3.0, "2026-09": 6.0}
    assert latest == "2026-09-30"


def test_market_pulse_never_claims_malaysia_and_carries_attribution() -> None:
    pulse = build_market_pulse(CSV, CFG, "2026-10-15T00:00:00+00:00")
    assert pulse["covers_malaysia"] is False
    assert pulse["default_country"] == "AU"
    assert "not Malaysia" in pulse["default_country_label"]
    assert pulse["attribution"] == "Source: Indeed Hiring Lab" and pulse["license"] == "CC BY 4.0"
    assert pulse["data_as_of"] == "2026-09-30" and pulse["fetched_at"].startswith("2026-10-15")
    assert {s["country"] for s in pulse["series"]} == {"AU", "US"}


def test_atomic_write_leaves_no_partial_file(tmp_path: Path) -> None:
    target = tmp_path / "snap.json"
    write_atomic(target, {"a": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    assert not list(tmp_path.glob("*.tmp"))


def test_window_start_counts_back_inclusive() -> None:
    assert window_start(NOW, 36) == "2023-11"
    assert window_start(NOW, 1) == "2026-10"


class Sources:
    def __init__(self, indeed_ok: bool = True) -> None:
        self.indeed_ok = indeed_ok

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "raw.githubusercontent.com":
            return httpx.Response(200, text=CSV) if self.indeed_ok else httpx.Response(500)
        if request.url.path.endswith("/search_by_date"):
            hits = [
                {
                    "objectID": "9",
                    "title": "Ask HN: Who is hiring? (October 2026)",
                    "created_at": "2026-10-01T15:00:00Z",
                }
            ]
            return httpx.Response(200, json={"hits": hits, "nbPages": 1})
        return httpx.Response(200, json=THREAD)


def fake(sources: Sources) -> Any:
    return lambda: httpx.Client(transport=httpx.MockTransport(sources))


@pytest.fixture(autouse=True)
def no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.signals.hn.time.sleep", lambda _s: None)


def test_run_writes_both_snapshots_with_their_own_data_dates(tmp_path: Path) -> None:
    status = run(tmp_path / "out", tmp_path / "cache", CFG, NOW, fake(Sources()))
    assert all(v.startswith("ok") for v in status.values())
    signals = json.loads((tmp_path / "out" / SKILL_SIGNALS).read_text(encoding="utf-8"))
    assert signals["data_as_of"] == "2026-10-07"  # newest post, not the fetch date
    python = next(s for s in signals["series"] if s["id"] == "python")
    assert python["points"][-1]["mentions"] == 1 and python["name"] == "Python"
    pulse = json.loads((tmp_path / "out" / MARKET_PULSE).read_text(encoding="utf-8"))
    assert pulse["data_as_of"] == "2026-09-30"


def test_a_failed_source_keeps_its_previous_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "out"
    write_atomic(out / MARKET_PULSE, {"previous": True})
    status = run(out, tmp_path / "cache", CFG, NOW, fake(Sources(indeed_ok=False)))
    assert status[MARKET_PULSE].startswith("kept previous")
    assert json.loads((out / MARKET_PULSE).read_text(encoding="utf-8")) == {"previous": True}
    assert status[SKILL_SIGNALS].startswith("ok")
