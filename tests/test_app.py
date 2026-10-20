"""The FastAPI app starts and mounts the engine router."""

from fastapi.testclient import TestClient

from src.main import app


def test_health() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
