"""Hacker News "Ask HN: Who is hiring?" threads via the public Algolia HN Search API (no key).

Each top-level comment of a monthly thread is one job post. Raw thread JSON is cached per month
in data/raw/hn/{yyyy-mm}.json (gitignored), so a re-run only fetches months it has not seen.
The current month's thread is still collecting posts, so it is always fetched fresh.
Requests are sequential, with a short pause and retries with backoff (be polite to the API).
"""

import html
import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from src.signals.config import REPO_ROOT

logger = logging.getLogger(__name__)

API = "https://hn.algolia.com/api/v1"
SEARCH_PATH = "/search_by_date"
SEARCH_PARAMS = {
    "tags": "story,author_whoishiring",
    "query": '"who is hiring"',
    "hitsPerPage": 100,
}
TITLE_PREFIX = "Ask HN: Who is hiring?"
CACHE_DIR = REPO_ROOT / "data" / "raw" / "hn"
PAUSE_S = 0.5  # pause between requests
RETRIES = 3
BACKOFF_S = 2.0  # first retry wait; doubles each time
TIMEOUT_S = 30.0
MAX_SEARCH_PAGES = 10  # 100 stories a page; plenty for 36 months of threads

MONTHS = {
    m: i
    for i, m in enumerate(
        [
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
        ],
        start=1,
    )
}
TITLE_MONTH = re.compile(r"\((\w+) (\d{4})\)")
TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class ThreadRef:
    story_id: int
    month: str  # YYYY-MM
    title: str


def month_of(title: str, created_at: str) -> str:
    """Month from the title, e.g. "(October 2026)"; falls back to the post date."""
    m = TITLE_MONTH.search(title)
    if m and m.group(1).lower() in MONTHS:
        return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
    return created_at[:7]


def strip_html(text: str) -> str:
    return html.unescape(TAG.sub(" ", text.replace("<p>", "\n"))).strip()


def _get(
    client: httpx.Client,
    path: str,
    params: dict[str, Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    wait = BACKOFF_S
    for attempt in range(1, RETRIES + 1):
        try:
            response = client.get(f"{API}{path}", params=params, timeout=TIMEOUT_S)
            response.raise_for_status()
            sleep(PAUSE_S)
            return response.json()
        except httpx.HTTPError as exc:
            if attempt == RETRIES:
                raise
            logger.warning("HN API %s failed (%s); retrying in %.0f s", path, exc, wait)
            sleep(wait)
            wait *= 2
    raise RuntimeError("unreachable")


def discover_threads(
    client: httpx.Client, since_month: str, sleep: Callable[[float], None] = time.sleep
) -> list[ThreadRef]:
    """Monthly "Who is hiring?" threads from `since_month` (YYYY-MM) on, oldest first."""
    found: dict[str, ThreadRef] = {}
    for page in range(MAX_SEARCH_PAGES):
        data = _get(client, SEARCH_PATH, {**SEARCH_PARAMS, "page": page}, sleep)
        hits = data.get("hits", [])
        for hit in hits:
            title = hit.get("title") or ""
            if not title.startswith(TITLE_PREFIX):
                continue  # excludes "Who wants to be hired?" and "Freelancer?" threads
            month = month_of(title, hit.get("created_at", ""))
            if month >= since_month and month not in found:
                found[month] = ThreadRef(int(hit["objectID"]), month, title)
        oldest = min((h.get("created_at", "")[:7] for h in hits), default="")
        if not hits or oldest < since_month or page + 1 >= data.get("nbPages", 0):
            break
    return [found[m] for m in sorted(found)]


def posts_of(thread: dict[str, Any]) -> list[str]:
    """Top-level comments only, HTML stripped; deleted or empty comments are skipped."""
    return [strip_html(c["text"]) for c in thread.get("children", []) if c.get("text")]


def load_months(
    client: httpx.Client,
    since_month: str,
    cache_dir: Path = CACHE_DIR,
    now: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[dict[str, list[str]], list[str]]:
    """Posts per month from `since_month` on, using the cache. Returns (posts, fetched months).

    A cached thread is reused only if it was fetched after its month ended; a thread cached while
    its month was still open (it keeps filling up) is fetched once more, then kept for good.
    """
    current = (now or datetime.now(UTC)).strftime("%Y-%m")
    cache_dir.mkdir(parents=True, exist_ok=True)
    posts: dict[str, list[str]] = {}
    fetched: list[str] = []
    for ref in discover_threads(client, since_month, sleep):
        path = cache_dir / f"{ref.month}.json"
        cached = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        if cached is not None and _is_final(cached, ref.month, current):
            thread = cached.get("thread", cached)  # older files hold the bare thread
        else:
            thread = _get(client, f"/items/{ref.story_id}", None, sleep)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps({"fetched_month": current, "thread": thread}), encoding="utf-8"
            )
            tmp.replace(path)
            fetched.append(ref.month)
        posts[ref.month] = posts_of(thread)
    return posts, fetched


def cached_thread(cache_dir: Path, month: str) -> dict[str, Any]:
    """The thread saved for `month` (either cache file format)."""
    data: dict[str, Any] = json.loads((cache_dir / f"{month}.json").read_text(encoding="utf-8"))
    thread: dict[str, Any] = data.get("thread", data)
    return thread


def _is_final(cached: dict[str, Any], month: str, current: str) -> bool:
    """True if the cached thread was fetched in a later month than its own (it was complete).

    Files from before fetched_month was recorded hold the raw thread; they were all written in
    one run, when only the current month was still open, so they count as final.
    """
    if month == current:
        return False
    fetched_month = cached.get("fetched_month")
    return fetched_month is None or fetched_month > month
