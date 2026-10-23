"""Economic Index collector keeps only the field's occupations and skips releases already read."""

from pathlib import Path

import httpx
import pytest

from src.collectors import aei
from src.collectors.base import MemoryState

SAMPLE = Path(__file__).parent / "fixtures" / "aei_sample.csv"
RELEASE = "release_2026_06_26"
CSV_PATH = f"{RELEASE}/data/aei_claude_ai_2026-06-26.csv"


def test_parse_keeps_field_occupations_and_known_metrics_only() -> None:
    with SAMPLE.open(encoding="utf-8", newline="") as handle:
        observations = aei.parse_rows(handle, "2026-06-26", "https://example.test")
    series = {(o.series, o.entity.split()[0], o.geography, o.period): o.value for o in observations}
    assert series[("aei_pct", "43-3031.00", "MYS", "2026-04")] == 0.28
    assert series[("aei_pct", "43-3031.00", "MYS", "2026-05")] == 0.30
    assert (
        series[("aei_collaboration_bucket_automation_pct", "13-2011.00", "GLOBAL", "2026-05")]
        == 45.02
    )
    assert not any(o.entity.startswith("15-1252") for o in observations)  # not a finance occupation
    assert not any(o.series == "aei_ai_autonomy_mean" for o in observations)  # metric not kept


def fake_hub(downloads: list[str]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/tree/main"):
            return httpx.Response(
                200,
                json=[
                    {"type": "directory", "path": "release_2026_03_24"},
                    {"type": "directory", "path": RELEASE},
                    {"type": "directory", "path": "labor_market_impacts"},
                ],
            )
        if path.endswith(f"/tree/main/{RELEASE}/data"):
            return httpx.Response(200, json=[{"type": "file", "path": CSV_PATH}])
        if path.endswith(CSV_PATH):
            downloads.append(path)
            return httpx.Response(200, text=SAMPLE.read_text(encoding="utf-8"))
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_collect_downloads_a_new_release_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Ignore any developer copy under data/raw so the test always exercises the download path.
    monkeypatch.setattr(aei, "local_copy", lambda release, csv_path: tmp_path / "absent.csv")
    downloads: list[str] = []
    state = MemoryState()
    with httpx.Client(transport=fake_hub(downloads)) as client:
        first = aei.collect(client, state)
        second = aei.collect(client, state)
    assert len(first.observations) > 0
    assert first.observations[0].published == "2026-06-26"
    assert second.observations == []
    assert second.note == "no new release since 2026-06-26"
    assert len(downloads) == 1
