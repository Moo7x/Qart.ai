"""DOSM collectors read the published numbers exactly and keep the passage they came from."""

import json
from datetime import date
from pathlib import Path

import httpx

from src.collectors import dosm_jmi, dosm_wages
from src.collectors.base import MemoryState

FIXTURES = Path(__file__).parent / "fixtures"


def jmi_page(name: str) -> str:
    return (FIXTURES / "dosm_jmi" / f"{name}.html").read_text(encoding="utf-8")


def test_wages_keeps_both_sexes_rows_with_exact_headcounts() -> None:
    rows = json.loads((FIXTURES / "dosm_wages_occupation.json").read_text(encoding="utf-8"))
    observations = {(o.entity, o.period): o for o in dosm_wages.parse(rows)}
    assert observations[("clerical", "2011")].value == 1108.6
    assert observations[("clerical", "2025")].value == 1360.1
    assert observations[("overall", "2025")].value == 10381.6
    assert all("sex=both" in o.cited_span for o in observations.values())


def test_wages_collect_calls_the_open_api() -> None:
    rows = json.loads((FIXTURES / "dosm_wages_occupation.json").read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["id"] == "wages_occupation"
        return httpx.Response(200, json=rows)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert len(dosm_wages.collect(client, MemoryState()).observations) == 15


def test_jmi_reads_quarter_dates_total_and_accountants() -> None:
    release = dosm_jmi.parse_release("q1-2026", jmi_page("q1_2026"))
    assert release.quarter == "2026-Q1"
    assert release.published == "2026-06-25"
    assert release.next_release == "2026-11-17"
    assert release.total == 626_861
    assert release.accountants == 24_784
    assert "Accountants and Auditors (24,784 job offerings)" in release.accountants_span


def test_jmi_reads_the_older_wording_without_job_offerings() -> None:
    release = dosm_jmi.parse_release("q2-2023", jmi_page("q2_2023"))
    assert (release.quarter, release.total, release.accountants) == ("2023-Q2", 261_231, 10_781)


def test_jmi_count_not_stated_is_missing_not_zero() -> None:
    release = dosm_jmi.parse_release("q1-2024", jmi_page("q1_2024"))
    assert release.total == 392_054
    assert release.accountants is None
    accountants = dosm_jmi.release_observations(release)[1]
    assert accountants.value is None
    assert accountants.cited_span == "count not stated on the release page"


def test_jmi_collect_discovers_linked_releases() -> None:
    pages = {
        dosm_jmi.SEED_SLUG: jmi_page("q1_2026"),
        "big-data-analytics-job-market-insights-q12026": jmi_page("q1_2026"),
        "big-data-analytics-job-market-insights-and-my-job-profile-first-q12025": jmi_page(
            "q1_2024"
        ),
        "big-data-analytics-job-market-insights-and-my-job-profile-fourth-q42024": jmi_page(
            "q2_2023"
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        slug = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, text=pages[slug]) if slug in pages else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = dosm_jmi.collect(client, MemoryState())
    assert {o.period for o in result.observations} == {"2026-Q1", "2024-Q1", "2023-Q2"}
    assert "archive link(s) unreachable" in result.note  # fixture links lead nowhere


def test_jmi_announced_placeholder_is_not_published_before_its_day() -> None:
    placeholder = dosm_jmi.parse_release("q3-2026", jmi_page("q3_2026_placeholder"))
    assert placeholder.quarter == "2026-Q3"
    assert not dosm_jmi.is_published(placeholder, date(2026, 10, 23))
    real = dosm_jmi.parse_release("q1-2026", jmi_page("q1_2026"))
    assert dosm_jmi.is_published(real, date(2026, 10, 23))


def test_next_quarter_slug_rolls_over_the_year() -> None:
    assert dosm_jmi.next_quarter_slug("2026-Q4") == "big-data-analytics-job-market-insights-q12027"
