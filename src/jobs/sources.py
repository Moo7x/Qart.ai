"""One fetcher per ATS behind a common interface, each normalising postings to `Posting`.

Endpoints (public, documented, unauthenticated GET; checked 2026-10-23):
  Greenhouse  boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
  Lever       api.lever.co/v0/postings/{site}?mode=json  (paged with skip / limit)
  Ashby       api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true
Dates come from the source's own fields where they exist (Greenhouse first_published or
updated_at, Lever createdAt, Ashby publishedAt). Only job postings are stored, no personal data.
"""

import html
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

from src.signals.http import Politeness, get_json

GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
LEVER = "https://api.lever.co/v0/postings/{token}"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{token}"


@dataclass(frozen=True)
class Posting:
    """One job posting in the common schema (first_seen / last_seen are added by the store)."""

    source: str
    company: str
    job_id: str
    title: str
    department: str | None
    location: str
    remote: bool
    employment_type: str | None
    description: str
    posted_at: str | None  # the source's own date (ISO 8601), where it gives one
    url: str


class Fetcher(Protocol):
    source: str

    def fetch(self, client: httpx.Client, token: str, company: str) -> tuple[Any, list[Posting]]:
        """(raw response for the snapshot, normalised postings)."""
        ...

    def normalise(self, job: dict[str, Any], company: str) -> Posting:
        """One raw job from this source in the common schema."""
        ...


def strip_html(text: str | None) -> str:
    """Plain text from HTML or entity-escaped HTML (Greenhouse escapes its content)."""
    text = html.unescape(html.unescape(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):  # Lever: epoch milliseconds
        return datetime.fromtimestamp(value / 1000, UTC).isoformat(timespec="seconds")
    return str(value)


@dataclass
class GreenhouseFetcher:
    polite: Politeness
    sleep: Callable[[float], None]
    source: str = "greenhouse"

    def fetch(self, client: httpx.Client, token: str, company: str) -> tuple[Any, list[Posting]]:
        raw = get_json(
            client, GREENHOUSE.format(token=token), {"content": "true"}, self.polite, self.sleep
        )
        return raw, [self.normalise(j, company) for j in raw.get("jobs", [])]

    def normalise(self, job: dict[str, Any], company: str) -> Posting:
        j = job
        location = (j.get("location") or {}).get("name") or ""
        employment = next(
            (
                m.get("value")
                for m in j.get("metadata") or []
                if "employment" in str(m.get("name", "")).lower()
            ),
            None,
        )
        departments = [d.get("name") for d in j.get("departments") or [] if d.get("name")]
        return Posting(
            source=self.source,
            company=company,
            job_id=str(j["id"]),
            title=j.get("title", "").strip(),
            department=departments[0] if departments else None,
            location=location,
            remote="remote" in location.lower(),
            employment_type=str(employment) if employment else None,
            description=strip_html(j.get("content")),
            posted_at=_iso(j.get("first_published") or j.get("updated_at")),
            url=j.get("absolute_url", ""),
        )


@dataclass
class LeverFetcher:
    polite: Politeness
    sleep: Callable[[float], None]
    page_size: int = 100
    source: str = "lever"

    def fetch(self, client: httpx.Client, token: str, company: str) -> tuple[Any, list[Posting]]:
        raw: list[Any] = []
        skip = 0
        while True:
            params = {"mode": "json", "skip": skip, "limit": self.page_size}
            page = get_json(client, LEVER.format(token=token), params, self.polite, self.sleep)
            raw.extend(page)
            if len(page) < self.page_size:
                break
            skip += self.page_size
        return raw, [self.normalise(j, company) for j in raw]

    def normalise(self, job: dict[str, Any], company: str) -> Posting:
        j = job
        cat = j.get("categories") or {}
        locations = [cat.get("location") or "", *(cat.get("allLocations") or [])]
        location = " / ".join(dict.fromkeys(x for x in locations if x))
        workplace = str(j.get("workplaceType") or "").lower()
        return Posting(
            source=self.source,
            company=company,
            job_id=str(j["id"]),
            title=(j.get("text") or "").strip(),
            department=cat.get("department") or cat.get("team"),
            location=location,
            remote=workplace == "remote" or "remote" in location.lower(),
            employment_type=cat.get("commitment"),
            description=j.get("descriptionPlain") or strip_html(j.get("description")),
            posted_at=_iso(j.get("createdAt")),
            url=j.get("hostedUrl", ""),
        )


@dataclass
class AshbyFetcher:
    polite: Politeness
    sleep: Callable[[float], None]
    source: str = "ashby"

    def fetch(self, client: httpx.Client, token: str, company: str) -> tuple[Any, list[Posting]]:
        params = {"includeCompensation": "true"}
        raw = get_json(client, ASHBY.format(token=token), params, self.polite, self.sleep)
        jobs = [j for j in raw.get("jobs", []) if j.get("isListed", True)]
        return raw, [self.normalise(j, company) for j in jobs]

    def normalise(self, job: dict[str, Any], company: str) -> Posting:
        j = job
        secondary = [s.get("location", "") for s in j.get("secondaryLocations") or []]
        location = " / ".join(x for x in [j.get("location") or "", *secondary] if x)
        workplace = str(j.get("workplaceType") or "").lower()
        return Posting(
            source=self.source,
            company=company,
            job_id=str(j["id"]),
            title=(j.get("title") or "").strip(),
            department=j.get("department") or j.get("team"),
            location=location,
            remote=bool(j.get("isRemote")) or workplace == "remote",
            employment_type=j.get("employmentType"),
            description=j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")),
            posted_at=_iso(j.get("publishedAt")),
            url=j.get("jobUrl", ""),
        )


def fetchers(
    polite: Politeness, sleep: Callable[[float], None], lever_page_size: int = 100
) -> dict[str, Fetcher]:
    return {
        "greenhouse": GreenhouseFetcher(polite, sleep),
        "lever": LeverFetcher(polite, sleep, lever_page_size),
        "ashby": AshbyFetcher(polite, sleep),
    }
