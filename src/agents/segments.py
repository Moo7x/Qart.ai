"""Cut a video's captions or an article's text into short parts, and rank them for one skill.

Pure functions plus two fetchers. Captions come from YouTube's public caption tracks
(youtube-transcript-api, MIT); article text from the page itself (trafilatura, Apache-2.0). The
ranking is the BGE reranker on RunPod with the skill name as the query (the bare name ranked
best in the catalogue check, docs/decision_log.md); without RunPod, a word-overlap score is used
and labelled. Nothing fetched here is stored: only timestamps, link anchors and the agent's own
one-line reasons are cached (data/agents/scout_cache.yaml).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from src import params
from src.config import Settings
from src.runpod_jobs import INTERACTIVE_BUDGET_SECONDS, RunPodError, rerank

SENTENCE_END = re.compile(r"[.!?][\"')\]]*$")
VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|/embed/)([\w-]{11})")
WORD = re.compile(r"[a-z0-9]+")
BOILERPLATE = re.compile(
    r"\b(subscribe|newsletter|sign up|cookie|privacy statement|stay up to date)\b", re.I
)
USER_AGENT = "Qart.ai resource scout (SDC Hackathon 2026; public pages)"


@dataclass
class Part:
    """One segment of a video (with times) or passage of an article (with a link anchor)."""

    part_id: str
    resource_id: str
    kind: str  # video | article
    text: str
    start: float | None = None
    end: float | None = None
    score: float = 0.0

    def link(self, url: str) -> str:
        if self.kind == "video" and self.start is not None:
            match = VIDEO_ID.search(url)
            return f"https://youtu.be/{match.group(1)}?t={int(self.start)}" if match else url
        words = anchor_words(self.text)
        # "-" and "," have a meaning inside a text fragment, so they are always encoded.
        encoded = quote(" ".join(words), safe="").replace("-", "%2D")
        return f"{url.split('#')[0]}#:~:text={encoded}" if words else url


def anchor_words(text: str) -> list[str]:
    """The passage's first words, starting at a letter or digit (a bullet would break the link)."""
    return re.sub(r"^\W+", "", text).split()[: params.FRAGMENT_WORDS]


def video_id(url: str) -> str | None:
    match = VIDEO_ID.search(url)
    return match.group(1) if match else None


def caption_snippets(video: str) -> list[tuple[float, float, str]]:
    """(start, duration, text) of the English captions; raises when YouTube refuses."""
    from youtube_transcript_api import YouTubeTranscriptApi

    fetched = YouTubeTranscriptApi().fetch(video, languages=["en", "en-US", "en-GB"])
    return [(s.start, s.duration, s.text.replace("\n", " ")) for s in fetched]


def video_parts(resource_id: str, snippets: list[tuple[float, float, str]]) -> list[Part]:
    """30–90 s segments, cut where a sentence ends once the minimum length is reached."""
    parts: list[Part] = []
    start, texts, end = None, [], 0.0
    for t0, dur, text in snippets:
        if start is None:
            start = t0
        texts.append(text)
        end = t0 + dur
        long_enough = end - start >= params.SEGMENT_MIN_SECONDS
        if (
            long_enough and SENTENCE_END.search(text.strip())
        ) or end - start >= params.SEGMENT_MAX_SECONDS:
            parts.append(
                Part(
                    f"{resource_id}#{len(parts)}", resource_id, "video", " ".join(texts), start, end
                )
            )
            start, texts = None, []
    if texts and start is not None:
        parts.append(
            Part(f"{resource_id}#{len(parts)}", resource_id, "video", " ".join(texts), start, end)
        )
    return parts


def article_text(url: str, client: httpx.Client) -> str:
    import trafilatura

    response = client.get(url, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return trafilatura.extract(response.text, include_comments=False, include_tables=False) or ""


def article_parts(resource_id: str, text: str) -> list[Part]:
    """Passages of 300–900 characters built from whole paragraphs."""
    parts: list[Part] = []
    buffer = ""
    for paragraph in (p.strip() for p in text.split("\n") if p.strip()):
        if BOILERPLATE.search(paragraph):
            continue  # sign-up and cookie banners that page extraction sometimes keeps
        buffer = f"{buffer} {paragraph}".strip()
        if len(buffer) >= params.PASSAGE_MIN_CHARS:
            parts.append(
                Part(
                    f"{resource_id}#{len(parts)}",
                    resource_id,
                    "article",
                    buffer[: params.PASSAGE_MAX_CHARS],
                )
            )
            buffer = ""
    if len(buffer) >= params.PASSAGE_MIN_CHARS // 2:
        parts.append(Part(f"{resource_id}#{len(parts)}", resource_id, "article", buffer))
    return parts


Ranker = Callable[[str, list[str]], list[float]]


def overlap_scores(query: str, texts: list[str]) -> list[float]:
    """Fallback ranking: the share of the skill name's words that appear in the text."""
    words = set(WORD.findall(query.lower()))
    return [len(words & set(WORD.findall(t.lower()))) / max(len(words), 1) for t in texts]


def rank(
    settings: Settings, skill_name: str, parts: list[Part], client: httpx.Client
) -> tuple[list[Part], str]:
    """The SCOUT_TOP_SEGMENTS best parts for the skill, and the engine that ranked them."""
    if not parts:
        return [], "none"
    texts = [p.text for p in parts]
    engine = "bge-reranker-v2-m3 (RunPod)"
    try:
        if not settings.runpod_configured:
            raise RunPodError("RunPod is not configured")
        scores = rerank(settings, skill_name, texts, INTERACTIVE_BUDGET_SECONDS, client)
    except (RunPodError, httpx.HTTPError, KeyError, ValueError):
        scores, engine = overlap_scores(skill_name, texts), "word overlap (fallback)"
    for part, score in zip(parts, scores, strict=True):
        part.score = round(score, 3)
    return sorted(parts, key=lambda p: -p.score)[: params.SCOUT_TOP_SEGMENTS], engine
