"""HN "Who is hiring?" client: thread discovery, HTML stripping, cache reuse and retries.

Uses httpx.MockTransport only; tests never touch the network.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from src.signals.hn import discover_threads, load_months, month_of, posts_of, strip_html

STORIES = [
    {
        "objectID": "3",
        "title": "Ask HN: Who is hiring? (October 2026)",
        "created_at": "2026-10-01T15:00:00Z",
    },
    {
        "objectID": "4",
        "title": "Ask HN: Who wants to be hired? (October 2026)",
        "created_at": "2026-10-01T15:00:00Z",
    },
    {
        "objectID": "2",
        "title": "Ask HN: Who is hiring? (September 2026)",
        "created_at": "2026-09-01T15:00:00Z",
    },
    {
        "objectID": "5",
        "title": "Ask HN: Freelancer? Seeking freelancer? (September 2026)",
        "created_at": "2026-09-01T15:00:00Z",
    },
    {
        "objectID": "1",
        "title": "Ask HN: Who is hiring? (August 2026)",
        "created_at": "2026-08-03T15:00:00Z",
    },
]
THREAD = {
    "children": [
        {"text": "<p>Acme | Python &amp; SQL</p>", "children": [{"text": "a reply, not a post"}]},
        {"text": None},
        {"text": "Beta | React"},
    ]
}
NOW = datetime(2026, 10, 15, tzinfo=UTC)


class Api:
    """Fake Algolia API that records which items were fetched."""

    def __init__(self, fail_first: int = 0) -> None:
        self.items: list[str] = []
        self.fail_first = fail_first

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.fail_first:
            self.fail_first -= 1
            return httpx.Response(503)
        if request.url.path.endswith("/search_by_date"):
            return httpx.Response(200, json={"hits": STORIES, "nbPages": 1})
        self.items.append(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(200, json=THREAD)


def client(api: Api) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(api))


def no_sleep(_: float) -> None:
    return None


def test_only_who_is_hiring_threads_are_kept_oldest_first() -> None:
    refs = discover_threads(client(Api()), "2026-08", no_sleep)
    assert [(r.month, r.story_id) for r in refs] == [("2026-08", 1), ("2026-09", 2), ("2026-10", 3)]
    assert [r.month for r in discover_threads(client(Api()), "2026-09", no_sleep)] == [
        "2026-09",
        "2026-10",
    ]


def test_month_comes_from_the_title_and_html_is_stripped() -> None:
    assert month_of("Ask HN: Who is hiring? (March 2025)", "2025-02-28T23:00:00Z") == "2025-03"
    assert month_of("Ask HN: Who is hiring?", "2025-02-28T23:00:00Z") == "2025-02"
    assert strip_html("<p>A &amp; B</p><i>c</i>") == "A & B  c"
    assert posts_of(THREAD) == ["Acme | Python & SQL", "Beta | React"]  # top level, not deleted


def test_rerun_fetches_only_months_not_in_the_cache_plus_the_current_one(tmp_path: Path) -> None:
    first = Api()
    posts, fetched = load_months(client(first), "2026-08", tmp_path, NOW, no_sleep)
    assert fetched == ["2026-08", "2026-09", "2026-10"] and len(posts["2026-09"]) == 2
    second = Api()
    _, fetched_again = load_months(client(second), "2026-08", tmp_path, NOW, no_sleep)
    assert fetched_again == ["2026-10"]  # the current month is still collecting posts
    assert second.items == ["3"]
    cached: Any = json.loads((tmp_path / "2026-08.json").read_text(encoding="utf-8"))
    assert cached == {"fetched_month": "2026-10", "thread": THREAD}


def test_a_month_cached_while_open_is_fetched_once_more_after_it_ends(tmp_path: Path) -> None:
    load_months(client(Api()), "2026-08", tmp_path, NOW, no_sleep)  # October cached mid-month
    november = datetime(2026, 11, 20, tzinfo=UTC)
    later = Api()
    _, fetched = load_months(client(later), "2026-08", tmp_path, november, no_sleep)
    assert fetched == ["2026-10"]  # October is complete now; August and September stay cached
    _, fetched = load_months(client(Api()), "2026-08", tmp_path, november, no_sleep)
    assert fetched == []


def test_old_cache_files_without_a_fetch_month_count_as_complete(tmp_path: Path) -> None:
    (tmp_path / "2026-08.json").write_text(json.dumps(THREAD), encoding="utf-8")
    _, fetched = load_months(client(Api()), "2026-08", tmp_path, NOW, no_sleep)
    assert fetched == ["2026-09", "2026-10"]


def test_server_errors_are_retried_with_backoff() -> None:
    waits: list[float] = []
    refs = discover_threads(client(Api(fail_first=2)), "2026-08", waits.append)
    assert len(refs) == 3
    assert waits[:2] == [2.0, 4.0]
