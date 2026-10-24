"""DOSM "Big Data Analytics: Job Market Insights": online job offerings per quarter.

Each quarterly release page states the total number of online job offerings and, when it is among
the top occupations, the count for Accountants and Auditors. We read those numbers from the page
text and keep the sentence they came from. A release that does not state the count stores it as
missing, never zero.

Release pages link to the earlier releases, so the collector discovers the archive from the latest
known page and fetches each release once.
"""

import html
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

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
# v2: releases are re-read once so the named occupations and the Professionals share are added.
STATE_KEY = "read_releases_v2"
MAX_RELEASE_PAGES = 60  # about 15 years of quarters; stops a runaway crawl if links loop
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
# The Professionals major group's share, stated in every release though worded differently:
# "Professional category, accounting for 50.4 per cent", "Professional category with 47.6 per
# cent", "Professionals accounted the largest share during the quarter with 48.1 per cent".
PROFESSIONALS = re.compile(r"Professionals?\b(?: category)?[^.%]{0,70}?(\d{1,2}\.\d) per cent")
# Named occupations with a count: "Accountants and Auditors (24,784 job offerings)" or "(20,846)".
NAMED = re.compile(
    r"([A-Z][A-Za-z,&/'\- ]+?)\s*\(([\d]{1,3}(?:,\d{3})*)(?: job offerings| vacancies)?\)"
)
LEAD_IN = re.compile(r"\b(?:for|by|were|was|as well as|and also|such as)\s+|,\s*")


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
    professional_share: float | None = None
    professional_span: str = ""
    named: tuple[tuple[str, int, str], ...] = ()  # (occupation, count, sentence)


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
    # Occupation paragraph only: from the occupation heading to the economic-activity heading.
    start = re.search(
        r"(?:Advertised Online|Online) (?:for|by) (?:Major Group )?Occupation", overview
    )
    end = re.search(r"(?:Advertised Online|Online) (?:for|by) Economic Activit", overview)
    occupation = overview[start.start() : end.start() if end else None] if start else ""
    share = PROFESSIONALS.search(occupation)
    listed: list[tuple[str, int, str]] = []
    for m in NAMED.finditer(occupation):
        name = LEAD_IN.split(m.group(1))[-1].strip().replace(" & ", " and ")
        if name and name[0].isupper() and len(name.split()) <= 8:
            listed.append(
                (name, int(m.group(2).replace(",", "")), _sentence(occupation, m.start()))
            )
    return Release(
        slug=slug,
        quarter=quarter,
        published=_iso(published.group(1) if published else None),
        next_release=_iso(upcoming.group(1) if upcoming else None),
        total=int(total_match.group(1).replace(",", "")) if total_match else None,
        total_span=_sentence(overview, total_match.start()) if total_match else "",
        accountants=int(accountants.group(1).replace(",", "")) if accountants else None,
        accountants_span=_sentence(overview, accountants.start()) if accountants else "",
        professional_share=float(share.group(1)) if share else None,
        professional_span=_sentence(occupation, share.start()) if share else "",
        named=tuple(listed),
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
    out = [total, accountants]
    if release.professional_share is not None:
        out.append(
            Observation(
                source_id=SOURCE_ID,
                series="online_job_offerings_share",
                entity="Professionals",
                geography="MYS",
                period=release.quarter,
                value=release.professional_share,
                unit="% of online job offerings",
                url=url,
                cited_span=release.professional_span,
                method_version=METHOD_VERSION,
                published=release.published,
            )
        )
    for name, count, span in release.named:
        if name == "Accountants and Auditors":
            continue  # already stored above under the same entity
        out.append(
            Observation(
                source_id=SOURCE_ID,
                series="online_job_offerings",
                entity=name,
                geography="MYS",
                period=release.quarter,
                value=float(count),
                unit="job offerings",
                denominator=float(release.total) if release.total else None,
                url=url,
                cited_span=span,
                method_version=METHOD_VERSION,
                published=release.published,
            )
        )
    return out


def discover_slugs(page_html: str) -> set[str]:
    return set(SLUG_PATTERN.findall(page_html))


def fetch_page(client: httpx.Client, slug: str) -> str:
    response = client.get(BASE + slug, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def next_quarter(quarter: str) -> str:
    year, q = int(quarter[:4]), int(quarter[-1])
    return f"{year + 1}-Q1" if q == QUARTERS_PER_YEAR else f"{year}-Q{q + 1}"


def next_quarter_slug(quarter: str) -> str:
    """Recent releases follow one URL pattern, so the next one can be tried before it is linked."""
    nxt = next_quarter(quarter)
    return f"big-data-analytics-job-market-insights-q{nxt[-1]}{nxt[:4]}"


def probe_next_release(client: httpx.Client, latest_quarter: str) -> Release | None:
    """The next quarter's release if its page exists (it may still be an announced placeholder)."""
    response = client.get(
        BASE + next_quarter_slug(latest_quarter), headers={"User-Agent": USER_AGENT}
    )
    if response.status_code != HTTP_OK:
        return None
    try:
        release = parse_release(next_quarter_slug(latest_quarter), response.text)
    except ValueError:
        return None  # a generic page, not a release
    # Accept the page only if it really is the quarter after the latest one we have.
    return release if release.quarter == next_quarter(latest_quarter) else None


def is_published(release: Release, today: date) -> bool:
    """DOSM creates a page before the release day; it counts only once dated and filled in."""
    return (
        release.published is not None
        and release.published <= today.isoformat()
        and (release.total is not None)
    )


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    # A published release never changes, so pages read in earlier runs are not fetched again
    # (DOSM's site is slow: re-reading all 13 pages took about 90 s). The latest page is always
    # read, because it carries the links to anything new.
    already: dict[str, str] = json.loads(state.get(STATE_KEY) or "{}")  # slug -> quarter
    pages: dict[str, str] = {}
    unreachable: set[str] = set()
    to_visit = [SEED_SLUG]
    while to_visit and len(pages) < MAX_RELEASE_PAGES:
        slug = to_visit.pop()
        if slug in pages or slug in unreachable or (slug in already and slug != SEED_SLUG):
            continue
        try:
            pages[slug] = fetch_page(client, slug)
        except httpx.HTTPStatusError:
            if slug == SEED_SLUG:
                raise  # without the latest release there is nothing to anchor on
            unreachable.add(slug)  # one broken archive link must not stop the others
            continue
        to_visit.extend(sorted(discover_slugs(pages[slug]) - pages.keys() - unreachable))
    releases = [parse_release(slug, page_html) for slug, page_html in pages.items()]
    known_quarters = [r.quarter for r in releases] + list(already.values())
    newer = probe_next_release(client, max(known_quarters))
    if newer is not None:
        releases.append(newer)
    today = datetime.now(UTC).date()
    published = {r.quarter: r for r in releases if is_published(r, today)}
    announced = sorted(r.quarter for r in releases if not is_published(r, today))
    observations = [obs for r in published.values() for obs in release_observations(r)]
    state.set(STATE_KEY, json.dumps({**already, **{r.slug: r.quarter for r in published.values()}}))
    quarters = sorted(set(already.values()) | set(published))
    upcoming = max((r.next_release for r in releases if r.next_release), default=None)
    note = f"{len(quarters)} releases {quarters[0]}–{quarters[-1]}" if quarters else "no releases"
    note += f" · {len(pages)} page(s) read"
    if announced:
        note += f" · announced, not yet published: {', '.join(announced)}"
    if unreachable:
        note += f" · {len(unreachable)} archive link(s) unreachable"
    if upcoming:
        note += f" · next release {upcoming}"
    return CollectorResult(observations, note=note)
