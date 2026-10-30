"""Progress check: quotes must be the person's words, "partly" never counts, the person decides."""

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine

from src.agents import check
from src.agents.character import load_character
from src.config import Settings
from src.db import init_db, make_engine
from src.journey.store import ProfileData, SkillClaim, create_profile, get_profile

SKILL = "reconciliation"


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    db = make_engine(f"sqlite:///{(tmp_path / 'c.sqlite').as_posix()}")
    init_db(db)
    return db


@pytest.fixture
def profile(engine: Engine) -> str:
    data = ProfileData(situation="working", skills={SKILL: SkillClaim(level=1, source="self")})
    return create_profile(engine, data)


def fake(judgements: list[dict[str, Any]], enough_after: int = 2) -> Any:
    calls = {"n": 0}

    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        if "judgements" in schema["properties"]:
            return json.dumps({"judgements": judgements})
        calls["n"] += 1
        return json.dumps(
            {"question": f"Question {calls['n']}?", "enough": calls["n"] > enough_after}
        )

    return complete


ANSWERS = [
    "I reconcile the bank accounts of six entities every month in SAP.",
    "When balances differ I trace the open items and post the corrections myself.",
]


def run(
    engine: Engine, settings: Settings, profile: str, judgements: list[dict[str, Any]]
) -> dict[str, Any]:
    complete = fake(judgements)
    started = check.start(engine, settings, profile, SKILL, complete)
    out = started
    for text in ANSWERS:
        out = check.answer(engine, settings, profile, started["session_id"], text, complete)
    return {"session_id": started["session_id"], **out}


def test_the_character_forbids_teaching_and_scores() -> None:
    prompt = load_character("progress_check").system_prompt()
    assert "Teach the skill" in prompt and "Write a score" in prompt


def test_level_rises_only_through_consecutive_yes_with_real_quotes(
    engine: Engine, settings: Settings, profile: str
) -> None:
    out = run(
        engine,
        settings,
        profile,
        [
            {
                "level": 2,
                "verdict": "yes",
                "quote": "reconcile the bank accounts of six entities every month",
            },
            {
                "level": 3,
                "verdict": "yes",
                "quote": "trace the open items and post the corrections myself",
            },
        ],
    )
    assert out["result"]["proposed_level"] == 3  # 1 → 3: the cap of two levels
    assert out["asked"] == 2 and out["question"] is None


def test_a_quote_not_in_the_answers_is_rejected(
    engine: Engine, settings: Settings, profile: str
) -> None:
    out = run(
        engine,
        settings,
        profile,
        [
            {"level": 2, "verdict": "yes", "quote": "I lead the whole finance team"},  # never said
        ],
    )
    assert out["result"]["proposed_level"] == 1 and out["result"]["met"] == []


def test_partly_does_not_raise_and_stops_the_climb(
    engine: Engine, settings: Settings, profile: str
) -> None:
    out = run(
        engine,
        settings,
        profile,
        [
            {
                "level": 2,
                "verdict": "partly",
                "quote": "reconcile the bank accounts of six entities",
            },
            {"level": 3, "verdict": "yes", "quote": "post the corrections myself"},
        ],
    )
    assert out["result"]["proposed_level"] == 1


def test_accept_writes_an_agent_check_claim_and_decline_changes_nothing(
    engine: Engine, settings: Settings, profile: str
) -> None:
    yes = [
        {
            "level": 2,
            "verdict": "yes",
            "quote": "reconcile the bank accounts of six entities every month",
        }
    ]
    declined = run(engine, settings, profile, yes)
    check.decide(engine, settings, profile, declined["session_id"], accept=False)
    assert get_profile(engine, profile)[0].skills[SKILL].level == 1  # type: ignore[index]
    accepted = run(engine, settings, profile, yes)
    check.decide(engine, settings, profile, accepted["session_id"], accept=True)
    claim = get_profile(engine, profile)[0].skills[SKILL]  # type: ignore[index]
    assert (claim.level, claim.source, claim.model) == (2, "agent_check", settings.agent_model)
    assert "six entities" in claim.evidence and claim.checked_at
    with pytest.raises(check.CheckError):
        check.decide(engine, settings, profile, accepted["session_id"], accept=True)  # once only


def test_checks_are_limited_per_skill_per_day(
    engine: Engine, settings: Settings, profile: str
) -> None:
    for _ in range(3):
        check.start(engine, settings, profile, SKILL, fake([]))
    with pytest.raises(check.CheckError, match="per day"):
        check.start(engine, settings, profile, SKILL, fake([]))


def test_without_a_model_the_check_says_so(
    engine: Engine, settings: Settings, profile: str
) -> None:
    with pytest.raises(check.CheckError, match="language model"):
        check.start(engine, settings, profile, SKILL)
