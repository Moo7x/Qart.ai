"""Qart.ai FastAPI application.

Run locally or on Replit:  uvicorn src.app:app --host 0.0.0.0 --port 8000

Order matters: API routes first, the built web app (web/dist) last, so "/api/..." is never
shadowed by the static files.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from src.envfile import load_env_file

load_env_file()  # local .env (gitignored); must run before settings are read

import src.evidence.models  # noqa: E402, F401  (registers the model-version table)
import src.evidence.store  # noqa: E402, F401  (registers the evidence tables before init_db)
import src.journey.store  # noqa: E402, F401  (registers the profile table)
import src.occupations.catalogue  # noqa: E402, F401  (registers the occupation tables)
from src.api.changes import router as changes_router  # noqa: E402
from src.api.decision import router as decision_router  # noqa: E402
from src.api.evidence import router as evidence_router  # noqa: E402
from src.api.journey import router as journey_router  # noqa: E402
from src.api.occupations import router as occupations_router  # noqa: E402
from src.config import Settings, load_settings  # noqa: E402
from src.db import init_db, make_engine, ping  # noqa: E402
from src.pipeline.run import start_catch_up_if_stale  # noqa: E402

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


def create_app(settings: Settings | None = None, first_run: bool = True) -> FastAPI:
    settings = settings or load_settings()
    engine = make_engine(settings.database_url)
    init_db(engine)
    if first_run:
        start_catch_up_if_stale(engine)  # a fresh deployment fills itself in the background

    application = FastAPI(
        title="Qart.ai",
        description="Evidence-based future-role matching and reskilling pathways for Malaysia.",
        version="0.3.0",
    )
    application.state.engine = engine
    application.state.settings = settings
    application.state.catch_up = first_run  # tests switch background runs off
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
    application.include_router(journey_router)
    application.include_router(changes_router)
    application.include_router(decision_router)
    application.include_router(occupations_router)
    if WEB_DIST.is_dir():
        application.mount("/", SinglePageApp(directory=WEB_DIST, html=True), name="web")
    else:
        logger.info("web/dist not built yet; only the API is served")
    return application


app = create_app()
