"""Engine HTTP routes (Person A): validate input, call the engine, return contract models."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["engine"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check used by Replit and the golden-journey test."""
    return {"status": "ok"}
