"""ATS pipeline over two runs, with recorded responses and no network."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from src.jobs import metrics
from src.jobs.config import Company, default_ats_config
from src.jobs.pipeline import build_snapshot, run
from src.jobs.store import StoredJob, all_jobs, connect

FIXTURES = Path(__file__).parent / "fixtures" / "ats"
CFG = default_ats_config().model_copy(update={"min_sample": 1})
COMPANIES = {
    "greenhouse": [Company(token="thoughtworks", name="Thoughtworks")],
    "lever": [Company(token="ninjavan", name="Ninja Van"), Company(token="gone", name="Gone Ltd")],
    "ashby": [Company(token="airwallex", name="Airwallex")],
}


def api(drop_lever_job: bool = False) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "gone" in path:
            return httpx.Response(404)
        if "greenhouse" in str(request.url):
            return httpx.Response(
                200, json=json.loads((FIXTURES / "greenhouse_thoughtworks.json").read_text())
            )
        if "lever" in str(request.url):
            jobs = json.loads((FIXTURES / "lever_ninjavan.json").read_text())
            return httpx.Response(200, json=jobs[1:] if drop_lever_job else jobs)
        return httpx.Response(200, json=json.loads((FIXTURES / "ashby_airwallex.json").read_text()))

    return lambda: httpx.Client(transport=httpx.MockTransport(handler))


def go(tmp: Path, day: date, **kw: Any) -> dict[str, Any]:
    return run(
        now=datetime(day.year, day.month, day.day, 3, tzinfo=UTC),
        db_path=tmp / "jobs.sqlite",
        raw_dir=tmp / "raw",
        out_dir=tmp / "out",
        companies=COMPANIES,
        cfg=CFG,
        sleep=lambda s: None,
        **kw,
    )


def test_two_runs_track_first_and_last_seen_and_skip_a_bad_board(tmp_path: Path) -> None:
    first = go(tmp_path, date(2026, 10, 23), make_client=api())
    assert first["companies_ok"] == 3 and first["companies_failed"] == 1 and first["jobs"] == 9
    assert any("lever/gone" in e for e in first["errors"]) and first["snapshot"] == "ok"
    assert (tmp_path / "raw" / "2026-10-23" / "lever__ninjavan.json").exists()
    go(tmp_path, date(2026, 10, 30), make_client=api(drop_lever_job=True))
    with connect(tmp_path / "jobs.sqlite") as conn:
        jobs = {(j.source, j.job_id): j for j in all_jobs(conn)}
    assert len(jobs) == 9  # deduplicated by source + job_id
    lever = [j for k, j in jobs.items() if k[0] == "lever"]
    assert sorted(j.last_seen for j in lever) == [
        "2026-10-23",
        "2026-10-30",
        "2026-10-30",
    ]  # one closed
    assert all(j.first_seen == "2026-10-23" for j in jobs.values())


def test_snapshot_has_regions_series_and_no_descriptions(tmp_path: Path) -> None:
    go(tmp_path, date(2026, 10, 23), make_client=api())
    snap = json.loads((tmp_path / "out" / CFG.snapshot_name).read_text())
    assert snap["data_as_of"] == snap["first_snapshot"] == "2026-10-23" and snap["snapshots"] == 1
    assert {r["id"] for r in snap["regions"]} >= {
        "malaysia",
        "singapore",
        "apac",
        "remote",
        "global",
    }
    week_my = next(
        s
        for s in snap["series"]
        if s["region"] == "malaysia_singapore" and s["granularity"] == "week"
    )
    assert week_my["points"][0]["total"] >= 4  # SG + MY postings in the fixtures
    assert snap["coverage"]["companies_failed"] == ["lever/Gone Ltd"]
    text = json.dumps(snap)
    assert "descriptionPlain" not in text and "content" not in snap  # aggregates only


def test_a_run_with_no_successful_board_keeps_the_previous_snapshot(tmp_path: Path) -> None:
    go(tmp_path, date(2026, 10, 23), make_client=api())
    before = (tmp_path / "out" / CFG.snapshot_name).read_text()
    down = lambda: httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))  # noqa: E731
    result = go(tmp_path, date(2026, 10, 24), make_client=down)
    assert result["companies_ok"] == 0 and "kept previous" in result["snapshot"]
    assert (tmp_path / "out" / CFG.snapshot_name).read_text() == before


def job(
    first: str,
    last: str,
    ai: bool,
    regions: tuple[str, ...] = ("global",),
    family: str | None = None,
) -> StoredJob:
    return StoredJob(
        "lever",
        f"{first}{last}{ai}",
        "C",
        "t",
        regions,
        family,
        ai,
        ("python",) if ai else (),
        first,
        last,
    )


def test_weekly_share_counts_jobs_open_during_each_week_and_hides_small_samples() -> None:
    jobs = [
        job("2026-10-05", "2026-10-20", True),
        job("2026-10-05", "2026-10-06", False),
        job("2026-10-19", "2026-10-30", False),
    ]
    series = metrics.ai_series(
        jobs, ["global"], date(2026, 10, 5), date(2026, 10, 30), "week", min_sample=2
    )
    points = {p["period"]: p for p in series[0]["points"]}
    assert points["2026-W41"] == {"period": "2026-W41", "total": 2, "ai": 1, "share_pct": 50.0}
    assert (
        points["2026-W42"]["total"] == 1 and points["2026-W42"]["share_pct"] is None
    )  # under min_sample
    assert points["2026-W43"]["total"] == 2  # the first job closed on the 20th (Tue of W43)
    months = metrics.ai_series(jobs, ["global"], date(2026, 10, 5), date(2026, 10, 30), "month", 1)[
        0
    ]["points"]
    assert months == [{"period": "2026-10", "total": 3, "ai": 1, "share_pct": 33.3}]


def test_latest_week_skill_and_family_breakdowns() -> None:
    jobs = [
        job("2026-10-26", "2026-10-30", True, ("global", "malaysia"), "analytics"),
        job("2026-10-26", "2026-10-30", False, ("global",), "analytics"),
    ]
    skills, families = metrics.latest_breakdowns(
        jobs, ["global", "malaysia"], {"python": "Python"}, date(2026, 10, 30), 1
    )
    assert {
        "region": "global",
        "skill_id": "python",
        "name": "Python",
        "mentions": 1,
        "total": 2,
        "share_pct": 50.0,
    } in skills
    assert {
        "region": "malaysia",
        "family": "analytics",
        "total": 1,
        "ai": 1,
        "share_pct": 100.0,
    } in families


def test_no_successful_run_means_no_snapshot(tmp_path: Path) -> None:
    assert build_snapshot(tmp_path / "empty.sqlite", CFG, "2026-10-23T00:00:00+00:00") is None
