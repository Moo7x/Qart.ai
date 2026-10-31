"""Link check: every course, video and article the app can show still opens.

A URL passes when it answers 2xx after redirects. A YouTube video is checked through YouTube's
public oEmbed endpoint, because a removed video's watch page still answers 200. The check never
changes the catalogue: it reports failures (in the pipeline run log and in
scripts/check_links.py) for a person to fix or retire.
"""

from collections.abc import Iterable
from typing import Any

import httpx

from src import http
from src.pack import load_pack
from src.resources import load_resources

TIMEOUT_SECONDS = 15.0
OK_LOW, OK_HIGH = 200, 300
# Some publishers refuse automated requests (403 from open.edu, iso.org, asq.org and pmi.org on
# 2026-10-30, while the pages open in a browser). Those are "not checkable automatically", listed
# for a person to open by hand, not reported as broken.
BLOCKED = {401, 403, 429}
OEMBED = "https://www.youtube.com/oembed"
YOUTUBE_HOSTS = ("youtube.com/watch", "youtu.be/")


def catalogue_urls() -> list[tuple[str, str]]:
    """(id, url) of every course, video and article in the pack, verified or not."""
    pack, res = load_pack(), load_resources()
    return (
        [(c.id, c.url) for c in pack.courses.values()]
        + [(v.id, v.url) for v in res.videos]
        + [(a.id, a.url) for a in res.articles]
    )


def _probe(client: httpx.Client, url: str) -> httpx.Response:
    if any(h in url for h in YOUTUBE_HOSTS):
        return client.get(OEMBED, params={"url": url, "format": "json"})
    return client.get(url)


def check_urls(items: Iterable[tuple[str, str]], client: httpx.Client) -> list[dict[str, Any]]:
    """The items whose URL did not open, with the status code or error."""
    failed = []
    for item_id, url in items:
        try:
            status = _probe(client, url).status_code
            if not OK_LOW <= status < OK_HIGH:
                failed.append(
                    {"id": item_id, "url": url, "status": status, "blocked": status in BLOCKED}
                )
        except httpx.HTTPError as exc:
            failed.append(
                {"id": item_id, "url": url, "status": type(exc).__name__, "blocked": False}
            )
    return failed


def link_step(client: httpx.Client) -> dict[str, Any]:
    """Pipeline run-log entry; a failed link never changes the run's status."""
    items = catalogue_urls()
    problems = check_urls(items, client)
    broken = [f["id"] for f in problems if not f["blocked"]]
    blocked = [f["id"] for f in problems if f["blocked"]]
    note = f"{len(items) - len(problems)} of {len(items)} links open"
    if broken:
        note += f"; broken: {', '.join(broken[:10])}"
    if blocked:
        note += f"; {len(blocked)} refuse automated checks (open by hand)"
    return {
        "source_id": "link_check",
        "status": "ok",
        "fetched": len(items),
        "new": 0,
        "note": note,
    }


def client() -> httpx.Client:
    return http.client("link check", TIMEOUT_SECONDS, follow_redirects=True)
