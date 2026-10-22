"""Settings come from the environment; Postgres URLs get the psycopg 3 driver."""

import pytest

from src.config import load_settings


def test_replit_postgres_url_uses_psycopg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:5432/db")
    assert load_settings().database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_sqlite_path_used_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("QART_DB_PATH", "/tmp/x.sqlite")
    assert load_settings().database_url == "sqlite:////tmp/x.sqlite"


def test_missing_llm_key_means_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    settings = load_settings()
    assert not settings.llm_configured
    assert settings.llm_model == "gpt-4o-mini"
