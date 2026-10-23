"""Qart.ai FastAPI application.

Run locally or on Replit:  uvicorn src.app:app --host 0.0.0.0 --port 8000

Order matters: API routes first, the built web app (web/dist) last, so "/api/..." is never
shadowed by the static files.
"""

import logging
import threading
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import Engine
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from src.envfile import load_env_file

load_env_file()  # local .env (gitignored); must run before settings are read

import src.evidence.store  # noqa: E402, F401  (registers the evidence tables before init_db)
from src.api.evidence import router as evidence_router  # noqa: E402
from src.config import Settings, load_settings  # noqa: E402
from src.db import init_db, make_engine, ping  # noqa: E402
from src.evidence.store import list_runs  # noqa: E402
from src.pipeline.run import run_pipeline  # noqa: E402

logger = logging.getLogger(__name__)

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
NOT_FOUND = 404
API_PREFIX = "api/"


class SinglePageApp(StaticFiles):
    """Serves web/dist. An unknown non-API path (a refresh on /radar) gets index.html so the
    React router can show that page; unknown /api paths stay 404."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            # Starlette passes an OS path ("api\\x" on Windows), so compare with "/" separators.
            if error.status_code != NOT_FOUND or path.replace("\\", "/").startswith(API_PREFIX):
                raise
            return await super().get_response("index.html", scope)


class Health(BaseModel):
    """Which parts are live and which run on a labelled fallback (no secret values)."""

    status: str
    database: str
    llm: str
    embeddings: str


def start_first_run_if_empty(engine: Engine) -> None:
    """A fresh deployment has no evidence yet: start one run in the background so pages fill in
    without anyone waiting on it. Later runs come from the schedule or Run now."""
    if list_runs(engine, 1):
        return
    threading.Thread(target=run_pipeline, args=(engine, "first start"), daemon=True).start()


def create_app(settings: Settings | None = None, first_run: bool = True) -> FastAPI:
    settings = settings or load_settings()
    engine = make_engine(settings.database_url)
    init_db(engine)
    if first_run:
        start_first_run_if_empty(engine)

    application = FastAPI(
        title="Qart.ai",
        description="Evidence-based future-role matching and reskilling pathways for Malaysia.",
        version="0.3.0",
    )
    application.state.engine = engine
    application.state.settings = settings
    api = APIRouter(prefix="/api")

    @api.get("/health")
    def health() -> Health:
        return Health(
            status="ok",
            database=engine.dialect.name if ping(engine) else "unavailable",
            llm=settings.llm_model if settings.llm_configured else "not configured (fallbacks)",
            embeddings="runpod" if settings.runpod_configured else "not configured (BM25)",
        )

    application.include_router(api)
    application.include_router(evidence_router)
    if WEB_DIST.is_dir():
        application.mount("/", SinglePageApp(directory=WEB_DIST, html=True), name="web")
    else:
        logger.info("web/dist not built yet; only the API is served")
    return application


app = create_app()
