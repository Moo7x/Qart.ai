"""The skill-search warm-up starts only when the GPU is configured and the cache is incomplete."""

from fastapi.testclient import TestClient

from src.config import Settings
from src.intake import skill_search
from src.pack import load_pack


def test_warm_up_needs_runpod(settings: Settings) -> None:
    assert skill_search.warm(load_pack(), settings) is False  # tests run without RunPod


def test_warm_route_answers_at_once(client: TestClient) -> None:
    assert client.post("/api/skills/warm").json() == {"started": False}
