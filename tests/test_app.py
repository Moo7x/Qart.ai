"""The FastAPI app starts, mounts the engine router, and serves the web app's pages."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.main import SinglePageApp, app


def test_health() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_refreshing_a_web_page_serves_the_app_but_unknown_api_paths_stay_404(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text("<html>qart</html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log(1)", encoding="utf-8")
    web = FastAPI()
    web.mount("/", SinglePageApp(directory=tmp_path, html=True), name="web")
    client = TestClient(web)
    assert client.get("/skills").text == "<html>qart</html>"
    assert client.get("/app.js").text == "console.log(1)"
    assert client.get("/api/not-a-route").status_code == 404
