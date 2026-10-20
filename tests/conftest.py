"""API test client backed by a fresh, seeded SQLite store per test."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api_engine import get_store, seed
from src.main import app
from src.store import Store


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    store = Store(tmp_path / "test.sqlite")
    seed(store)
    app.dependency_overrides[get_store] = lambda: store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
