"""YouTube catalogue job: more checked videos per skill, found with the YouTube Data API.

    .venv/Scripts/python.exe -m src.collectors.youtube [SKILL ...]   # resources_youtube.yaml

For every skill a destination role needs (and every AI-basics topic) that has fewer than
YOUTUBE_TARGET_PER_SKILL videos:
1. search (YouTube Data API v3 `search.list`, 100 quota units per call) with a declared query;
2. keep only videos from a trusted channel (TRUSTED_CHANNELS: professional bodies, universities,
   the tools' makers and educators already used in resources.yaml), with a length between
   YOUTUBE_MIN_MINUTES and YOUTUBE_MAX_MINUTES (`videos.list`, 1 unit);
3. check the fit like a course (src/collectors/course_check.py): one LLM_MODEL call
   gives a verdict and a quote; the quote must appear word for word in the video's English
   captions (or its description when YouTube refuses captions). Only "fits" with a found quote is
   written; everything else is dropped, so nothing unverified is ever shown.
Only metadata is stored (title, channel, link, length, date, the checked quote): no captions.
"""

import json
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import yaml

from src import http, llm, params
from src.agents.segments import caption_snippets
from src.collectors.course_check import _skill_text, quote_found
from src.config import load_settings
from src.envfile import load_env_file
from src.evidence.field import PACK_DIR
from src.pack import load_pack
from src.resources import load_resources

API = "https://www.googleapis.com/youtube/v3"
OUT_FILE = "resources_youtube.yaml"
# Channels whose videos may be added (declared): every channel already checked by hand in
# resources.yaml, plus professional bodies, universities and the makers of the tools.
TRUSTED_CHANNELS = {
    "Accounting Stuff",
    "Corporate Finance Institute",
    "Edspira",
    "Khan Academy",
    "Microsoft Learn",
    "Microsoft Power BI",
    "Microsoft 365",
    "Google Cloud Tech",
    "Google Cloud",
    "IBM Technology",
    "freeCodeCamp.org",
    "Kevin Stratvert",
    "StatQuest with Josh Starmer",
    "Strategyzer",
    "Coursera",
    "edX",
    "MIT OpenCourseWare",
    "Harvard Business Review",
    "ACCA",
    "ACCA Global",
    "CIMA",
    "ICAEW",
    "IFAC",
    "AICPA & CIMA",
    "The Finance Storyteller",
    "Financial Executives International (FEI)",
    "Ryan O'Connell, CFA, FRM",
    "Leila Gharani",
    "Kenji Explains",
    "SAP",
    "SAP Learning",
    "Oracle",
    "Procurement Academy",
    "Management Courses - Mike Clayton",
    "Business To You",
    "Sustainability Illustrated",
    "Ellen MacArthur Foundation",
    "UN Environment Programme",
    "World Economic Forum",
    "Chartered Institute of Procurement & Supply",
    "CIPS",
    "Excel Campus - Jon",
    "Chandoo",
}
QUERY = "{name} explained"  # declared search phrase; the fit check decides, not the search rank
SYSTEM = (
    "You check whether a YouTube video teaches one finance-related skill. Use only the video text "
    "you are given (its captions or description). Answer 'fits' when the video teaches knowledge "
    "or tasks that belong to the skill; it does not need to cover the whole skill. Copy one "
    "sentence from the text, word for word, that shows it; if you cannot, answer 'unclear'. "
    "Answer 'does_not_fit' when it teaches something else or only advertises a product. Never "
    "use outside knowledge and never invent text."
)
SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "quote", "reason"],
    "properties": {
        "verdict": {"type": "string", "enum": ["fits", "does_not_fit", "unclear"]},
        "quote": {"type": "string"},
        "reason": {"type": "string"},
    },
}
DURATION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def minutes(iso: str) -> int:
    """ISO 8601 duration (PT1H2M3S) to whole minutes, rounded up."""
    match = DURATION.fullmatch(iso)
    if not match:
        return 0
    h, m, s = (int(x or 0) for x in match.groups())
    return h * 60 + m + (1 if s else 0)


def search(client: httpx.Client, key: str, query: str) -> list[str]:
    response = client.get(
        f"{API}/search",
        params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 15,
            "relevanceLanguage": "en",
            "safeSearch": "strict",
            "key": key,
        },
    )
    response.raise_for_status()
    return [item["id"]["videoId"] for item in response.json().get("items", [])]


def details(client: httpx.Client, key: str, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    response = client.get(
        f"{API}/videos",
        params={"part": "snippet,contentDetails", "id": ",".join(ids), "key": key},
    )
    response.raise_for_status()
    out = []
    for item in response.json().get("items", []):
        snippet = item["snippet"]
        out.append(
            {
                "video": item["id"],
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "description": snippet.get("description", ""),
                "published": snippet["publishedAt"][:10],
                "minutes": minutes(item["contentDetails"]["duration"]),
            }
        )
    return out


def eligible(video: dict[str, Any]) -> bool:
    return (
        video["channel"] in TRUSTED_CHANNELS
        and params.YOUTUBE_MIN_MINUTES <= video["minutes"] <= params.YOUTUBE_MAX_MINUTES
    )


def video_text(video: str, captions: Callable[[str], list[tuple[float, float, str]]]) -> str:
    try:
        return " ".join(text for _, _, text in captions(video))
    except Exception:  # noqa: BLE001  YouTube refuses captions sometimes: use the description
        return ""


def check(video: dict[str, Any], skill_text: str, text: str, complete: llm.Complete) -> str:
    """The checked quote when the video fits the skill, else ""."""
    if not text.strip():
        return ""
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Skill: {skill_text}\n\nVideo: {video['title']} ({video['channel']})\n\n"
                f"Video text:\n{text[: params.COURSE_CHECK_PAGE_CHARS]}"
            ),
        },
    ]
    answer = json.loads(complete(messages, SCHEMA))
    if answer["verdict"] == "fits" and quote_found(answer["quote"], text):
        return str(answer["quote"])
    return ""


def targets() -> list[tuple[str, str, str]]:
    """(kind, id, description) for every needed skill and AI-basics topic."""
    pack, res = load_pack(), load_resources()
    needed = sorted({r.skill for role in pack.destination_roles.values() for r in role.requires})
    out = [("skill", s, _skill_text(s)) for s in needed]
    out += [("topic", t.id, t.title) for t in res.ai_basics]
    return out


def run(
    key: str,
    complete: llm.Complete,
    model: str,
    client: httpx.Client,
    only: set[str] | None = None,
    captions: Callable[[str], list[tuple[float, float, str]]] = caption_snippets,
) -> dict[str, Any]:
    res = load_resources()
    path = PACK_DIR / OUT_FILE
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    videos: list[dict[str, Any]] = list((data or {}).get("videos", []))
    known = {v.url for v in res.videos} | {v["url"] for v in videos}
    today = f"{datetime.now(UTC):%Y-%m-%d}"
    added = 0
    for kind, ident, text in targets():
        if only and ident not in only:
            continue
        have = len(res.videos_for(**{kind: ident})) + sum(
            ident in v.get("skills" if kind == "skill" else "topics", []) for v in videos
        )
        if have >= params.YOUTUBE_TARGET_PER_SKILL:
            continue
        name = text.split(". Level 1")[0]
        found = [
            v
            for v in details(client, key, search(client, key, QUERY.format(name=name)))
            if eligible(v)
        ]
        for video in found:
            url = f"https://www.youtube.com/watch?v={video['video']}"
            if url in known or have >= params.YOUTUBE_TARGET_PER_SKILL:
                continue
            body = video_text(video["video"], captions)
            source = "captions" if body else "description"
            quote = check(video, text, body or video["description"], complete)
            if not quote:
                continue
            videos.append(
                {
                    "id": f"yt_api_{video['video']}",
                    "title": video["title"],
                    "channel": video["channel"],
                    "url": url,
                    "minutes": video["minutes"],
                    "published": video["published"],
                    "skills" if kind == "skill" else "topics": [ident],
                    "fit_check": {
                        "result": "fits",
                        "by": model,
                        "quote": quote,
                        "checked": today,
                        "from": source,
                    },
                }
            )
            known.add(url)
            have += 1
            added += 1
    header = {
        "checked": today,
        "source": "YouTube Data API v3 search; fit checked against captions or description",
    }
    path.write_text(
        yaml.safe_dump({**header, "videos": videos}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return {"added": added, "total": len(videos)}


def main() -> None:
    load_env_file()
    settings = load_settings()
    import os

    key = os.environ.get("YOUTUBE_API_KEY")
    if not key or not settings.llm_configured:
        raise SystemExit("needs YOUTUBE_API_KEY and LLM_API_KEY")
    complete = llm.openai_complete(
        settings,
        schema_name="video_fit",
        purpose="video_fit_check",
        timeout=params.COURSE_CHECK_LLM_SECONDS,
    )
    with http.client("youtube catalogue", 30) as client:
        print(run(key, complete, settings.llm_model, client, set(sys.argv[1:]) or None))


if __name__ == "__main__":
    main()
