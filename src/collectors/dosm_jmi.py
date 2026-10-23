"""DOSM "Big Data Analytics: Job Market Insights": online job offerings per quarter.

Each quarterly release page states the total number of online job offerings and, when it is among
the top occupations, the count for Accountants and Auditors. We read those numbers from the page
text and keep the sentence they came from. A release that does not state the count stores it as
missing, never zero.

Release pages link to the earlier releases, so the collector discovers the archive from the latest
known page and fetches each release once.
"""

import html
import re
from dataclasses import dataclass

import httpx

from src.collectors.base import CollectorResult, SourceState
from src.evidence.store import Observation

SOURCE_ID = "dosm_job_market_insights"
BASE = "https://www.dosm.gov.my/portal-main/release-content/"
SEED_SLUG = "big-data-analytics-job-market-insights-q22026"
METHOD_VERSION = "dosm_jmi/1"
USER_AGENT = "Qart.ai evidence pipeline (SDC Hackathon 2026; public data)"
SLUG_PATTERN = re.compile(
    r"/portal-main/release-content/(big-data-analytics-job-market-insights[\w-]*)"
)
QUARTER_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4}
QUARTERS_PER_YEAR = 4
HTTP_OK = 200
MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
# The accountant count appears as "Accountants and Auditors (24,784 job offerings)",
# "Accountants & Auditors (9,462 job offerings)" or "Accountants and Auditors (10,781)".
ACCOUNTANTS = re.compile(r"Accountants (?:and|&) Auditors \(([\d,]+)(?: job offerings)?\)")
# The total is the first large number after the quarter is named, e.g. "... increased by 6.6 per
# cent to 626,861", "... was 587,801", "... with 392,054 vacancies", "... to record 338,305".
TOTAL = re.compile(r"(?:to record|to|was|with|amounting to)\s+([\d]{1,3}(?:,\d{3})+)")


@dataclass(frozen=True)
class Release:
    slug: str
    quarter: str  # e.g. "2026-Q1"
    published: str | None  # ISO date of the release
    next_release: str | None
    total: int | None
    total_span: str
    accountants: int | None
    accountants_span: str


def page_text(page_html: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page_html, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def _iso(day_month_year: str | None) -> str | None:
    if not day_month_year:
        return None
    day, month, year = day_month_year.split()
    return f"{year}-{MONTHS.index(month.lower()) + 1:02d}-{int(day):02d}"


def _sentence(text: str, start: int) -> str:
    """The sentence around position `start`, used as the cited span."""
    begin = text.rfind(". ", 0, start) + 2 if text.rfind(". ", 0, start) >= 0 else 0
    end = text.find(". ", start)
    return text[begin : end + 1 if end >= 0 else len(text)].strip()


def parse_release(slug: str, page_html: str) -> Release:
    # The heading may continue with a badge (<span>), so read only its text up to the next tag.
    title = re.search(r"<h3>([^<]*Quarter[^<]*)<", page_html)
    if not title:
        raise ValueError(f"{slug}: no release title found")
    q = re.search(r"(First|Second|Third|Fourth) Quarter (?:of )?(\d{4})", title.group(1), re.I)
    if not q:
        raise ValueError(f"{slug}: cannot read the quarter from {title.group(1)!r}")
    quarter = f"{q.group(2)}-Q{QUARTER_WORDS[q.group(1).lower()]}"
    date = r"(\d{1,2} [A-Za-z]+ \d{4})"
    published = re.search(r"Latest Release\s*:\s*" + date, page_html)
    upcoming = re.search(r"Upcoming release\s*:\s*" + date, page_html, re.I)

    text = page_text(page_html)
    overview = text[text.find("Overview") :] if "Overview" in text else text
    named = re.search(r"in the (first|second|third|fourth) quarter of \d{4}", overview, re.I)
    total_match = TOTAL.search(overview, named.end()) if named else None
    accountants = ACCOUNTANTS.search(overview)
    return Release(
        slug=slug,
        quarter=quarter,
        published=_iso(published.group(1) if published else None),
        next_release=_iso(upcoming.group(1) if upcoming else None),
        total=int(total_match.group(1).replace(",", "")) if total_match else None,
        total_span=_sentence(overview, total_match.start()) if total_match else "",
        accountants=int(accountants.group(1).replace(",", "")) if accountants else None,
        accountants_span=_sentence(overview, accountants.start()) if accountants else "",
    )


def release_observations(release: Release) -> list[Observation]:
    url = BASE + release.slug
    total = Observation(
        source_id=SOURCE_ID,
        series="online_job_offerings",
        entity="all occupations",
        geography="MYS",
        period=release.quarter,
        value=float(release.total) if release.total is not None else None,
        unit="job offerings",
        url=url,
        cited_span=release.total_span or "total not stated on the release page",
        method_version=METHOD_VERSION,
        published=release.published,
    )
    accountants = Observation(
        source_id=SOURCE_ID,
        series="online_job_offerings",
        entity="Accountants and Auditors",
        geography="MYS",
        period=release.quarter,
        value=float(release.accountants) if release.accountants is not None else None,
        unit="job offerings",
        denominator=float(release.total) if release.total else None,
        url=url,
        cited_span=release.accountants_span or "count not stated on the release page",
        method_version=METHOD_VERSION,
        published=release.published,
    )
    return [total, accountants]


def discover_slugs(page_html: str) -> set[str]:
    return set(SLUG_PATTERN.findall(page_html))


def fetch_page(client: httpx.Client, slug: str) -> str:
    response = client.get(BASE + slug, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def next_quarter_slug(quarter: str) -> str:
    """Recent releases follow one URL pattern, so the next one can be tried before it is linked."""
    year, q = int(quarter[:4]), int(quarter[-1])
    year, q = (year + 1, 1) if q == QUARTERS_PER_YEAR else (year, q + 1)
    return f"big-data-analytics-job-market-insights-q{q}{year}"


def probe_next_release(client: httpx.Client, latest_quarter: str) -> Release | None:
    slug = next_quarter_slug(latest_quarter)
    response = client.get(BASE + slug, headers={"User-Agent": USER_AGENT})
    if response.status_code != HTTP_OK or "Quarter" not in response.text:
        return None  # not published yet
    return parse_release(slug, response.text)


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    seed_html = fetch_page(client, SEED_SLUG)
    pages = {SEED_SLUG: seed_html}
    for slug in sorted(discover_slugs(seed_html) - {SEED_SLUG}):
        pages[slug] = fetch_page(client, slug)
    releases = [parse_release(slug, page_html) for slug, page_html in pages.items()]
    newer = probe_next_release(client, max(r.quarter for r in releases))
    if newer is not None:
        releases.append(newer)
    observations = [obs for release in releases for obs in release_observations(release)]
    quarters = sorted({r.quarter for r in releases})
    upcoming = max((r.next_release for r in releases if r.next_release), default=None)
    note = f"{len(quarters)} releases {quarters[0]}–{quarters[-1]}" if quarters else "no releases"
    return CollectorResult(
        observations, note=note + (f" · next release {upcoming}" if upcoming else "")
    )
