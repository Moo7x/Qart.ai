"""The agents' tool-calling chat goes through the shared LLM call: same budget and usage row."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import openai
import pytest
from sqlalchemy import Engine, select

from src import usage
from src.agents.client import openai_chat
from src.config import Settings
from src.db import init_db, make_engine


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    db = make_engine(settings.database_url)
    init_db(db)
    usage.bind(db)
    yield db
    usage.unbind()


class FakeOpenAI:
    seen: dict[str, Any] = {}

    def __init__(self, **options: Any) -> None:
        FakeOpenAI.seen = {"options": options}
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request: Any) -> Any:
        FakeOpenAI.seen["request"] = request
        call = SimpleNamespace(
            id="c1", function=SimpleNamespace(name="search", arguments='{"q": "sql"}')
        )
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=50, completion_tokens=5),
            choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))],
        )


def test_agent_chat_returns_tool_calls_and_records_one_usage_row(
    engine: Engine, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    reply = openai_chat(settings, "resource_scout", 2.0)([{"role": "user", "content": "x"}], [])
    assert reply["content"] == ""
    assert reply["tool_calls"][0]["function"] == {"name": "search", "arguments": '{"q": "sql"}'}
    assert FakeOpenAI.seen["options"]["max_retries"] == 0
    assert FakeOpenAI.seen["options"]["timeout"] == 2.0
    assert FakeOpenAI.seen["request"]["model"] == settings.agent_model
    with engine.connect() as conn:
        [row] = [dict(r) for r in conn.execute(select(usage.usage_table)).mappings()]
    assert row["purpose"] == "resource_scout" and row["model"] == settings.agent_model
    assert (row["tokens_in"], row["tokens_out"], row["ok"]) == (50, 5, True)
