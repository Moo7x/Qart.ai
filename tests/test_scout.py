"""The scout keeps only parts its tools returned, builds the links itself and always ends."""

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine

from src.agents import store
from src.agents.character import Character, load_character
from src.agents.scout import run_scout
from src.agents.segments import Part, article_parts, video_parts
from src.config import Settings
from src.db import init_db, make_engine
from src.resources import load_resources

SKILL = "dashboards"
SNIPPETS = [
    (float(t), 10.0, "We build a dashboard in Power BI." if t % 40 == 0 else "More detail.")
    for t in range(0, 200, 10)
]


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    db = make_engine(f"sqlite:///{(tmp_path / 'a.sqlite').as_posix()}")
    init_db(db)
    return db


def test_character_file_loads_and_its_rules_reach_the_prompt() -> None:
    character = load_character("scout")
    prompt = character.system_prompt()
    assert all(rule in prompt for rule in [*character.rules.must, *character.rules.never])


def test_a_character_without_never_rules_is_refused() -> None:
    with pytest.raises(ValueError):
        Character.model_validate(
            {"name": "x", "role": "y", "bio": ["z"], "rules": {"must": ["a"], "never": []}}
        )


def test_video_segments_are_30_to_90_seconds_and_links_start_there() -> None:
    parts = video_parts("v1", SNIPPETS)
    assert all(30 <= (p.end or 0) - (p.start or 0) <= 90 for p in parts[:-1])
    assert (
        parts[1]
        .link("https://www.youtube.com/watch?v=VaOhNqNtGGE")
        .endswith(f"?t={int(parts[1].start or 0)}")
    )


def test_article_links_open_at_the_passage_and_skip_banners() -> None:
    text = (
        "Subscribe to our newsletter for updates every week.\n"
        + "A dashboard shows key figures. " * 20
    )
    [part] = article_parts("a1", text)
    assert not part.text.startswith("Subscribe")
    link = Part("p", "a1", "article", "- Build reports and dashboards").link("https://x.test/page")
    assert link == "https://x.test/page#:~:text=Build%20reports%20and%20dashboards"


def fake_chat(script: list[dict[str, Any]]) -> Any:
    replies = iter(script)

    def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        return next(replies)

    return chat


def call(name: str, **args: Any) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": name,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ],
    }


def test_agent_picks_are_checked_and_numbers_dropped(engine: Engine, settings: Settings) -> None:
    video = load_resources().videos_for(skill=SKILL)[0]
    chat = fake_chat(
        [
            call("read_video", resource_id=video.id),
            call(
                "finish",
                picks=[
                    {"part_id": f"{video.id}#0", "reason": "Builds a dashboard step by step."},
                    {
                        "part_id": f"{video.id}#1",
                        "reason": "Takes 3 minutes.",
                    },  # a number: reason dropped
                    {"part_id": "invented#9", "reason": "Not returned by any tool."},
                ],
            ),
        ]
    )
    run_id = store.start(engine, "scout", SKILL, None, "test")
    result = run_scout(engine, settings, run_id, SKILL, chat=chat, captions=lambda vid: SNIPPETS)
    reasons = [p["reason"] for p in result["picks"]]
    assert len(result["picks"]) == 2 and reasons[0] and reasons[1] == ""
    assert all(p["url"].startswith("https://youtu.be/") for p in result["picks"])
    assert store.read(engine, run_id)["status"] == "done"


def test_without_a_model_the_ranking_alone_answers_and_says_so(
    engine: Engine, settings: Settings
) -> None:
    run_id = store.start(engine, "scout", SKILL, None, "test")
    result = run_scout(engine, settings, run_id, SKILL, captions=lambda vid: SNIPPETS)
    assert "ranking only" in result["engine"] and "word overlap" in result["engine"]
    steps = [s["text"] for s in store.read(engine, run_id)["steps"]]
    assert steps[0].startswith("Looking for") and steps[-1].startswith("Done")


def test_refused_captions_fall_back_to_the_earlier_check(
    engine: Engine, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.agents import scout as scout_module

    video = load_resources().videos_for(skill=SKILL)[0]
    cache = {
        "checked": "2026-10-30",
        "skills": {
            SKILL: [
                {
                    "resource_id": video.id,
                    "kind": "video",
                    "start": 120.0,
                    "end": 180.0,
                    "anchor": "",
                    "reason": "Builds a chart.",
                }
            ]
        },
    }
    monkeypatch.setattr(scout_module, "load_cache", lambda: cache)

    def refused(vid: str) -> list[tuple[float, float, str]]:
        raise RuntimeError("YouTube refused")

    run_id = store.start(engine, "scout", SKILL, None, "test")
    result = run_scout(engine, settings, run_id, SKILL, captions=refused)
    cached = [p for p in result["picks"] if p["source"].startswith("checked on")]
    assert (
        cached and cached[0]["url"].endswith("?t=120") and cached[0]["reason"] == "Builds a chart."
    )


def test_a_run_for_one_resource_reads_only_that_resource(
    engine: Engine, settings: Settings
) -> None:
    video = load_resources().videos_for(skill=SKILL)[0]
    run_id = store.start(engine, "scout", SKILL, None, "test")
    result = run_scout(
        engine, settings, run_id, SKILL, captions=lambda vid: SNIPPETS, resource_id=video.id
    )
    assert result["picks"] and {p["resource_id"] for p in result["picks"]} == {video.id}
