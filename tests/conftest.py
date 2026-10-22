"""API test client backed by a fresh, seeded SQLite store per test."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api_engine import get_store, seed
from src.main import app
from src.store import Store


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never call paid services: importing the app loads .env, so drop its keys here."""
    for name in ("LLM_API_KEY", "RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    store = Store(tmp_path / "test.sqlite")
    seed(store)
    app.dependency_overrides[get_store] = lambda: store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
