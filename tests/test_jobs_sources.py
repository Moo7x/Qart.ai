"""ATS fetchers and tagging on recorded sample responses (tests/fixtures/ats/). No network:
every request goes to an httpx.MockTransport."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.jobs.config import default_ats_config, load_companies
from src.jobs.sources import AshbyFetcher, GreenhouseFetcher, LeverFetcher, Posting, strip_html
from src.jobs.tagging import Tagger
from src.signals.config import default_config
from src.signals.http import Politeness

FIXTURES = Path(__file__).parent / "fixtures" / "ats"
POLITE = Politeness(timeout_s=5, retries=3, backoff_s=0.01, pause_s=0)
CFG = default_ats_config()
TAGGER = Tagger(CFG, default_config().skills)


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def no_sleep(_: float) -> None:
    return None


def client_for(handler: Any) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_greenhouse_normalises_to_the_common_schema() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=fixture("greenhouse_thoughtworks.json"))

    raw, postings = GreenhouseFetcher(POLITE, no_sleep).fetch(
        client_for(handler), "thoughtworks", "Thoughtworks"
    )
    assert (
        seen[0].url.params["content"] == "true" and "/boards/thoughtworks/jobs" in seen[0].url.path
    )
    assert raw["jobs"] and len(postings) == 3
    p = postings[0]
    assert p.source == "greenhouse" and p.company == "Thoughtworks" and p.job_id.isdigit()
    assert p.location == "Singapore, Singapore" and p.url.startswith("https://")
    assert p.posted_at and p.posted_at[:4] == "2026" and "<" not in p.description


def test_lever_pages_with_skip_and_limit() -> None:
    jobs = fixture("lever_ninjavan.json")
    pages: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        pages.append(dict(request.url.params))
        skip = int(request.url.params["skip"])
        return httpx.Response(200, json=jobs[skip : skip + 2])

    _, postings = LeverFetcher(POLITE, no_sleep, page_size=2).fetch(
        client_for(handler), "ninjavan", "Ninja Van"
    )
    assert [p["skip"] for p in pages] == ["0", "2"] and all(p["mode"] == "json" for p in pages)
    assert len(postings) == 3
    my = next(p for p in postings if "Malaysia" in p.location)
    assert my.employment_type and my.posted_at and my.posted_at.endswith("+00:00")


def test_ashby_uses_remote_fields_and_skips_unlisted_jobs() -> None:
    data = fixture("ashby_airwallex.json")
    data["jobs"].append({**data["jobs"][0], "id": "hidden", "isListed": False})
    _, postings = AshbyFetcher(POLITE, no_sleep).fetch(
        client_for(lambda r: httpx.Response(200, json=data)), "airwallex", "Airwallex"
    )
    assert "hidden" not in {p.job_id for p in postings} and len(postings) == 3
    remote = [p for p in postings if p.remote]
    assert remote, "the fixture has a remote Ashby job"


def test_an_invalid_board_token_fails_at_once_and_server_errors_are_retried() -> None:
    calls: list[int] = []

    def not_found(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404)

    with pytest.raises(httpx.HTTPStatusError):
        GreenhouseFetcher(POLITE, no_sleep).fetch(client_for(not_found), "nope", "Nope")
    assert len(calls) == 1  # no retry for a wrong token
    attempts: list[int] = []

    def flaky(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(503) if len(attempts) < 3 else httpx.Response(200, json={"jobs": []})

    assert GreenhouseFetcher(POLITE, no_sleep).fetch(client_for(flaky), "x", "X") == (
        {"jobs": []},
        [],
    )
    assert len(attempts) == 3


def posting(**kw: Any) -> Posting:
    base = dict(
        source="lever",
        company="C",
        job_id="1",
        title="Software Engineer",
        department=None,
        location="Berlin, Germany",
        remote=False,
        employment_type=None,
        description="",
        posted_at=None,
        url="https://x",
    )
    return Posting(**{**base, **kw})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("location", "remote", "regions"),
    [
        (
            "Shah Alam, Selangor, Malaysia",
            False,
            {"global", "malaysia", "apac", "malaysia_singapore"},
        ),
        ("SG - Singapore", False, {"global", "singapore", "apac", "malaysia_singapore"}),
        ("Bangkok, Thailand", False, {"global", "apac"}),
        ("London, United Kingdom", True, {"global", "remote"}),
    ],
)
def test_regions_come_from_location_text_and_remote_fields(
    location: str, remote: bool, regions: set[str]
) -> None:
    assert set(TAGGER.regions(posting(location=location, remote=remote))) == regions


@pytest.mark.parametrize(
    ("title", "family"),
    [
        ("Senior Security Engineer", "security"),
        ("Machine Learning Engineer", "ml_ai"),
        ("Data Engineer", "data_engineering"),
        ("Financial Analyst, FP&A", "finance_ops"),
        ("Customer Success Manager", "customer_ops"),
        ("Backend Software Engineer", "software"),
        ("Head of Wine", None),
    ],
)
def test_role_family_from_the_title_first_rule_wins(title: str, family: str | None) -> None:
    assert TAGGER.family(posting(title=title)) == family


def test_ai_flag_and_skills_are_keyword_based() -> None:
    ai = posting(
        title="Analyst",
        description="You will build LLM agents and evaluate generative AI tools in Python and SQL.",
    )
    assert TAGGER.mentions_ai(ai)
    tags = TAGGER.tag(ai)
    assert {"python", "sql_basics"} <= set(tags.skills)
    assert not TAGGER.mentions_ai(
        posting(description="Maintain the airline's main hangar; said rain may delay")
    )
    assert not TAGGER.mentions_ai(
        posting(description="Strong ai attention to detail")
    )  # lower-case 'ai' is not AI


def test_html_is_stripped_including_escaped_html() -> None:
    assert strip_html("&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;") == "Hello & welcome"


def test_company_config_has_three_sources_and_verified_tokens() -> None:
    companies = load_companies()
    assert set(companies) == {"greenhouse", "lever", "ashby"}
    assert all(c.checked for cs in companies.values() for c in cs)
    assert sum(len(c) for c in companies.values()) >= 20


def test_company_boilerplate_is_removed_before_ai_matching() -> None:
    from src.jobs.tagging import strip_boilerplate

    about = "About us: the leading platform for the AI era, trusted by teams worldwide."
    tasks = [
        "reconcile the bank ledger",
        "pay supplier invoices",
        "close the month",
        "audit expense claims",
        "prepare VAT returns",
        "review payroll",
    ]
    jobs = [
        posting(job_id=str(i), description=f"You will {t}. {about}") for i, t in enumerate(tasks)
    ]
    jobs.append(posting(job_id="ai", description=f"Build LLM evaluations in Python. {about}"))
    cleaned = strip_boilerplate(jobs, min_share=0.3, min_postings=5, n=8)
    assert sum(TAGGER.mentions_ai(p) for p in jobs) == 7  # before: all "mention AI"
    assert [p.job_id for p in cleaned if TAGGER.mentions_ai(p)] == ["ai"]  # after: the real one
    assert cleaned[0].description == "You will reconcile the bank ledger."  # role text kept
    assert strip_boilerplate(jobs[:3], 0.3, 5, 8) == jobs[:3]  # too few postings to tell
