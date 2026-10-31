"""Which linked "articles" really are articles the scout can read and point into.

    .venv/Scripts/python.exe -m src.collectors.article_check     # writes article_checks.yaml

Each article link is opened and its main text extracted (trafilatura, as the scout does). It is
an article when the response is an HTML page and the extracted body has at least
ARTICLE_MIN_WORDS words; a PDF, a landing or login page, a tool or a page that will not load is
"web page" or "unreachable". Only articles get the agent button; the others stay listed as plain
links. Stored: the verdict, the word count and the date (no page text).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import yaml

from src import http, params
from src.evidence.field import PACK_DIR
from src.resources import load_resources

OUT = PACK_DIR / "article_checks.yaml"


def classify(content_type: str, text: str) -> tuple[str, int]:
    words = len(text.split())
    if "html" not in content_type.lower():
        return "web page", words  # a PDF or a file: linked, but not something to point into
    return ("article" if words >= params.ARTICLE_MIN_WORDS else "web page"), words


def check(url: str, client: httpx.Client, extract: Callable[[str], str]) -> dict[str, Any]:
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError:
        return {"kind": "unreachable", "words": 0}
    kind, words = classify(response.headers.get("content-type", ""), extract(response.text))
    return {"kind": kind, "words": words}


def _extract(html: str) -> str:
    import trafilatura

    return trafilatura.extract(html, include_comments=False, include_tables=False) or ""


def main() -> None:
    today = f"{datetime.now(UTC):%Y-%m-%d}"
    out: dict[str, Any] = {}
    with http.client(
        "article check", params.COURSE_CHECK_FETCH_SECONDS, follow_redirects=True
    ) as client:
        for article in load_resources().articles:
            out[article.id] = {**check(article.url, client, _extract), "checked": today}
            print(article.id, out[article.id]["kind"], out[article.id]["words"])
    OUT.write_text(
        yaml.safe_dump({"checked": today, "articles": out}, sort_keys=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
