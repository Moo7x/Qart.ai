"""Shared test fixtures. Tests never call paid or network services."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.config import Settings

PAID_SERVICE_KEYS = ("LLM_API_KEY", "RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID")


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the app loads .env, so drop the paid-service keys for every test."""
    for name in PAID_SERVICE_KEYS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Offline settings on a fresh SQLite file per test."""
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}",
        llm_api_key=None,
        llm_base_url=None,
        llm_model="gpt-4o-mini",
        runpod_api_key=None,
        runpod_endpoint_id=None,
        admin_token="test-admin-token",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
