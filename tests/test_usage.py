"""Usage counter and the shared LLM client: each model or GPU call leaves one row, no content."""

from collections.abc import Iterator
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest
from sqlalchemy import Engine, select

from src import llm, usage
from src.config import Settings
from src.db import init_db, make_engine
from src.runpod_jobs import RunPodError, run_job


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    db = make_engine(settings.database_url)
    init_db(db)
    usage.bind(db)
    yield db
    usage.unbind()


def rows(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(select(usage.usage_table)).mappings()]


def test_record_does_nothing_when_unbound(engine: Engine) -> None:
    usage.unbind()
    usage.record("cv_extraction", "openai", "gpt-4o-mini", 1.0, True)
    assert rows(engine) == []


class FakeOpenAI:
    """Stands in for openai.OpenAI; answers with fixed text and token counts."""

    fail = False

    def __init__(self, **_: Any) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request: Any) -> Any:
        if FakeOpenAI.fail:
            raise TimeoutError("budget")
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=120, completion_tokens=30),
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        )


def test_llm_call_records_tokens_and_model(
    engine: Engine, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    complete = llm.openai_complete(
        settings, schema_name="x", purpose="cv_extraction", timeout=1.0, model="gpt-4.1-mini"
    )
    assert complete([{"role": "user", "content": "cv"}], {"type": "object"}) == '{"ok": true}'
    [row] = rows(engine)
    assert row["purpose"] == "cv_extraction" and row["engine"] == "openai"
    assert row["model"] == "gpt-4.1-mini" and row["ok"]
    assert (row["tokens_in"], row["tokens_out"]) == (120, 30)


def test_failed_llm_call_is_recorded_as_failed(
    engine: Engine, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(FakeOpenAI, "fail", True)
    complete = llm.openai_complete(settings, schema_name="x", purpose="role_explanation", timeout=1)
    with pytest.raises(TimeoutError):
        complete([], {})
    [row] = rows(engine)
    assert not row["ok"] and row["model"] == settings.llm_model and row["tokens_in"] is None
    assert usage.totals(engine)[0]["failed"] == 1


def test_runpod_job_is_recorded(engine: Engine, settings: Settings) -> None:
    configured = replace(settings, runpod_api_key="k", runpod_endpoint_id="e")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"id": "j", "status": "COMPLETED", "output": {"scores": []}}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        run_job(configured, {"task": "rerank"}, 5.0, client)

    def stuck(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "j", "status": "IN_QUEUE"})

    with httpx.Client(transport=httpx.MockTransport(stuck)) as client, pytest.raises(RunPodError):
        run_job(configured, {"task": "embed"}, -1.0, client, sleep=lambda s: None)
    found = {(r["purpose"], r["model"], r["ok"]) for r in rows(engine)}
    assert found == {
        ("runpod_rerank", "BAAI/bge-reranker-v2-m3", True),
        ("runpod_embed", "BAAI/bge-m3", False),
    }
