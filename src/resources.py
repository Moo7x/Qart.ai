"""Checked supplementary resources (YouTube videos, articles) and the AI-basics topics.

Loaded from data/packs/gbs_fa/resources.yaml and any resources_*.yaml beside it (videos and
articles only). Videos and articles are links only: they are shown
next to the courses on My plan and are never counted in planned hours or projected fit.
"""

from functools import cache

import yaml
from pydantic import BaseModel

from src.pack import PackError, load_pack, pack_files


class Video(BaseModel):
    id: str
    title: str
    channel: str
    url: str
    minutes: int
    published: str
    skills: list[str] = []
    topics: list[str] = []


class Article(BaseModel):
    id: str
    title: str
    publisher: str
    url: str
    skills: list[str] = []
    topics: list[str] = []


class AiTopic(BaseModel):
    id: str
    title: str
    skill: str | None = None  # the pack skill this topic builds, when there is one
    courses: list[str]


class Resources(BaseModel):
    checked: str
    videos: list[Video]
    articles: list[Article]
    ai_basics: list[AiTopic]

    def videos_for(self, skill: str | None = None, topic: str | None = None) -> list[Video]:
        return [
            v for v in self.videos if (skill and skill in v.skills) or (topic and topic in v.topics)
        ]

    def articles_for(self, skill: str | None = None, topic: str | None = None) -> list[Article]:
        return [
            a
            for a in self.articles
            if (skill and skill in a.skills) or (topic and topic in a.topics)
        ]


def _read() -> Resources:
    """resources.yaml, plus the videos and articles of any resources_*.yaml (pipeline-built)."""
    first, *extra = pack_files("resources")
    res = Resources.model_validate(yaml.safe_load(first.read_text(encoding="utf-8")))
    for path in extra:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        res.videos += [Video.model_validate(v) for v in raw.get("videos", [])]
        res.articles += [Article.model_validate(a) for a in raw.get("articles", [])]
    return res


@cache
def load_resources() -> Resources:
    res = _read()
    pack = load_pack()
    topics = {t.id for t in res.ai_basics}
    items: list[Video | Article] = [*res.videos, *res.articles]
    problems = [
        f"{item.id}: unknown skill {s}"
        for item in items
        for s in item.skills
        if s not in pack.skills
    ]
    problems += [
        f"{item.id}: unknown topic {t}" for item in items for t in item.topics if t not in topics
    ]
    problems += [
        f"{t.id}: unknown course {c}"
        for t in res.ai_basics
        for c in t.courses
        if c not in pack.courses
    ]
    problems += [
        f"{t.id}: unknown skill {t.skill}"
        for t in res.ai_basics
        if t.skill and t.skill not in pack.skills
    ]
    if problems:
        raise PackError("; ".join(problems))
    return res
