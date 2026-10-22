"""Qart.ai FastAPI application (shared file: change only after messaging the other teammate).

Run locally or on Replit:  uvicorn src.main:app --host 0.0.0.0 --port 8000

Order matters: API routers first, the built web app (web/dist) last, so "/api/..." is never
shadowed by the static files.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from src.envfile import load_env_file

load_env_file()  # local .env (gitignored); must run before the routers read any settings

from src.api_engine import router as engine_router  # noqa: E402
from src.api_search import router as search_router  # noqa: E402

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = REPO_ROOT / "web" / "dist"
NOT_FOUND = 404
API_PREFIX = "api/"


class SinglePageApp(StaticFiles):
    """Serves web/dist. An unknown non-API path (e.g. a refresh on /skills) gets index.html, so
    the React router can show that page instead of a 404; unknown /api paths stay 404."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            # Starlette passes an OS path ("api\\x" on Windows), so compare with "/" separators.
            if error.status_code != NOT_FOUND or path.replace("\\", "/").startswith(API_PREFIX):
                raise
            return await super().get_response("index.html", scope)


app = FastAPI(
    title="Qart.ai",
    description="Practise reviewing AI-prepared finance work; evidence-based future-role matching.",
    version="0.1.0",
)

# --- Person A: engine routes (src/api_engine.py) and search (src/api_search.py) -----------------
app.include_router(engine_router)
app.include_router(search_router)


# --- Person B: companion + cases routes (src/api_companion.py) ---------------------------------
# PLACEHOLDER for Person B. Mounted automatically once src/api_companion.py exposes `router`.
def _include_companion_router(application: FastAPI) -> None:
    try:
        from src.api_companion import router as companion_router  # type: ignore[import-not-found,unused-ignore]
    except ModuleNotFoundError:
        logger.info("src/api_companion.py not present yet; companion routes not mounted")
        return
    application.include_router(companion_router)


_include_companion_router(app)


# --- Person B: built web app (web/dist) --------------------------------------------------------
# PLACEHOLDER for Person B. Served at "/" once `npm run build` has produced web/dist.
if WEB_DIST.is_dir():
    app.mount("/", SinglePageApp(directory=WEB_DIST, html=True), name="web")
else:
    logger.info("web/dist not built yet; only the API is served")
