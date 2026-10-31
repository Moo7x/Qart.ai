"""The link check reports links that no longer open and checks YouTube through oEmbed."""

import httpx

from src.pipeline.links import catalogue_urls, check_urls


def test_failing_and_removed_links_are_reported() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "gone" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200)

    items = [
        ("ok", "https://learn.microsoft.com/en-us/training/modules/ok/"),
        ("gone", "https://learn.microsoft.com/en-us/training/modules/gone/"),
        ("video", "https://www.youtube.com/watch?v=gone123"),
    ]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        failed = check_urls(items, client)
    assert {f["id"] for f in failed} == {"gone", "video"}
    assert not any(f["blocked"] for f in failed)  # a 404 is broken, not merely blocked
    assert any(u.startswith("https://www.youtube.com/oembed") for u in seen)  # not the watch page


def test_sites_refusing_bots_are_listed_apart_from_broken_links() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        [failed] = check_urls([("iso", "https://www.iso.org/standard/45001")], client)
    assert failed["blocked"] and failed["status"] == 403


def test_every_catalogue_item_has_a_url_to_check() -> None:
    items = catalogue_urls()
    assert items and all(url.startswith("https://") for _, url in items)
