"""Runtime settings, read once from environment variables (Replit Secrets or the local .env).

Only names live in the code and in .env.example; values never appear in logs or responses.
"""

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Local default: one SQLite file under data/ (gitignored). Replit sets DATABASE_URL to Postgres.
DEFAULT_SQLITE_PATH = REPO_ROOT / "data" / "qart.sqlite"
DEFAULT_LLM_MODEL = "gpt-4o-mini"  # the named model for extraction, explanation and both agents


@dataclass(frozen=True)
class Settings:
    """What the app needs from its environment; missing keys switch to labelled fallbacks."""

    database_url: str
    llm_api_key: str | None
    llm_base_url: str | None
    llm_model: str
    runpod_api_key: str | None
    runpod_endpoint_id: str | None
    admin_token: str | None

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def runpod_configured(self) -> bool:
        return bool(self.runpod_api_key and self.runpod_endpoint_id)


def _sqlalchemy_url(raw: str) -> str:
    """Replit gives `postgres://...`; SQLAlchemy needs the psycopg 3 driver named."""
    for prefix in ("postgres://", "postgresql://"):
        if raw.startswith(prefix):
            return "postgresql+psycopg://" + raw.removeprefix(prefix)
    return raw


def load_settings() -> Settings:
    raw_db = os.environ.get("DATABASE_URL") or ""
    if raw_db:
        database_url = _sqlalchemy_url(raw_db)
    else:
        sqlite_path = Path(os.environ.get("QART_DB_PATH") or DEFAULT_SQLITE_PATH)
        database_url = f"sqlite:///{sqlite_path.as_posix()}"
    return Settings(
        database_url=database_url,
        llm_api_key=os.environ.get("LLM_API_KEY") or None,
        llm_base_url=os.environ.get("LLM_BASE_URL") or None,
        llm_model=os.environ.get("LLM_MODEL") or DEFAULT_LLM_MODEL,
        runpod_api_key=os.environ.get("RUNPOD_API_KEY") or None,
        runpod_endpoint_id=os.environ.get("RUNPOD_ENDPOINT_ID") or None,
        admin_token=os.environ.get("QART_ADMIN_TOKEN") or None,
    )
