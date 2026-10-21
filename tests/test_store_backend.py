"""Store backend selection (item 7): Postgres when DATABASE_URL is set, else SQLite.

No Postgres server is needed: selection is a pure function, and the Postgres adapter is checked
with a fake connection.
"""

from pathlib import Path
from typing import Any

from src.store import (
    DEFAULT_DB_PATH,
    BackendChoice,
    _PostgresConnection,
    make_store,
    select_backend,
)

URL = "postgresql://user:secret@db.example.test:5432/qart?sslmode=require"


def test_database_url_selects_postgres_and_wins_over_sqlite_path() -> None:
    env = {"DATABASE_URL": URL, "QART_DB_PATH": "x.sqlite"}
    assert select_backend(env) == BackendChoice("postgres", URL)


def test_without_database_url_sqlite_is_used() -> None:
    assert select_backend({}) == BackendChoice("sqlite", str(DEFAULT_DB_PATH))
    assert select_backend({"QART_DB_PATH": "a.sqlite"}) == BackendChoice("sqlite", "a.sqlite")
    assert select_backend({"DATABASE_URL": "  "}).kind == "sqlite"


def test_make_store_builds_a_working_sqlite_store(tmp_path: Path) -> None:
    store = make_store({"QART_DB_PATH": str(tmp_path / "s.sqlite")})
    assert store.backend == "sqlite" and store.is_empty()
    with store.seed_lock():
        assert store.is_empty()


class FakePgConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, sql: str, params: tuple[Any, ...]) -> str:
        self.calls.append((sql, params))
        return "cursor"


def test_postgres_adapter_converts_placeholders() -> None:
    fake = FakePgConnection()
    _PostgresConnection(fake).execute(
        "SELECT body FROM events WHERE id = ? AND user_id = ?", ["a", "b"]
    )
    assert fake.calls == [("SELECT body FROM events WHERE id = %s AND user_id = %s", ("a", "b"))]
