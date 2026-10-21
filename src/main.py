"""Qart.ai FastAPI application (shared file: change only after messaging the other teammate).

Run locally or on Replit:  uvicorn src.main:app --host 0.0.0.0 --port 8000

Order matters: API routers first, the built web app (web/dist) last, so "/api/..." is never
shadowed by the static files.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api_engine import router as engine_router

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = REPO_ROOT / "web" / "dist"

app = FastAPI(
    title="Qart.ai",
    description="Practise reviewing AI-prepared finance work; evidence-based future-role matching.",
    version="0.1.0",
)

# --- Person A: engine routes (src/api_engine.py) -----------------------------------------------
app.include_router(engine_router)


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
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
else:
    logger.info("web/dist not built yet; only the API is served")
