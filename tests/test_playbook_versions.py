"""Playbook versions: v1 by default, a saved version can be activated, events record the version."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api_engine import get_store
from src.companion import playbook_versions as pv
from src.store import Store


@pytest.fixture
def playbook_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A copy of the committed playbooks so tests never write into the repository."""
    directory = tmp_path / "playbooks"
    directory.mkdir()
    (directory / "playbook_v1.md").write_text(
        (pv.PLAYBOOK_DIR / "playbook_v1.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(pv, "PLAYBOOK_DIR", directory)
    return directory


def test_v1_is_active_until_another_version_is_activated(
    tmp_path: Path, playbook_dir: Path
) -> None:
    store = Store(tmp_path / "s.sqlite")
    version, text = pv.active_playbook(store)
    assert version == pv.BASE_VERSION and "Step 6" in text
    assert pv.next_version(store) == "playbook_v2"
    path = pv.save_version(store, "playbook_v2", "# Procedure v2")
    assert path.read_text(encoding="utf-8") == "# Procedure v2"
    pv.set_active(store, "playbook_v2")
    assert pv.active_playbook(store) == ("playbook_v2", "# Procedure v2")
    assert pv.next_version(store) == "playbook_v3"


def test_unknown_or_malformed_versions_are_refused(tmp_path: Path, playbook_dir: Path) -> None:
    store = Store(tmp_path / "s.sqlite")
    with pytest.raises(KeyError):
        pv.set_active(store, "playbook_v9")
    with pytest.raises(ValueError):
        pv.playbook_file("../../secrets")


def test_events_record_the_active_version_and_reset_returns_to_v1(
    client: TestClient, playbook_dir: Path
) -> None:
    store = client.app.dependency_overrides[get_store]()  # type: ignore[attr-defined]
    pv.save_version(store, "playbook_v2", "# Procedure v2")
    pv.set_active(store, "playbook_v2")
    body = {"decision": "sign_off", "case_id": "case_001"}
    event = client.post("/api/companion/s_v2/decision", json=body).json()["event"]
    assert event["companion_version"] == "playbook_v2"
    client.post("/api/demo/reset").raise_for_status()
    assert pv.active_playbook(store)[0] == pv.BASE_VERSION
