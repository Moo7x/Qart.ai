"""The app starts offline and reports which parts run on fallbacks."""

from fastapi.testclient import TestClient


def test_health_reports_database_and_labelled_fallbacks(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "sqlite",
        "llm": "not configured (fallbacks)",
        "embeddings": "not configured (BM25)",
    }


def test_unknown_api_path_is_404(client: TestClient) -> None:
    assert client.get("/api/does-not-exist").status_code == 404
