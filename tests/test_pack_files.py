"""Extra course and resource files (pipeline-built catalogues) load beside the hand-checked ones."""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

import src.pack as pack_module
from src.evidence.field import PACK_DIR
from src.pack import PackError, load_pack
from src.resources import load_resources

CANDIDATE = {
    "id": "ms_candidate_dashboards",
    "title": "Candidate module",
    "provider": "Microsoft Learn",
    "url": "https://learn.microsoft.com/en-us/training/modules/x/",
    "minutes": 30,
    "level": "intermediate",
    "covers": ["dashboards"],
    "verified": False,
}


@pytest.fixture
def pack_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    copy = tmp_path / "pack"
    shutil.copytree(PACK_DIR, copy)
    monkeypatch.setattr(pack_module, "PACK_DIR", copy)
    load_pack.cache_clear()
    load_resources.cache_clear()
    yield copy
    load_pack.cache_clear()
    load_resources.cache_clear()


def write(path: Path, data: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_unverified_candidates_load_but_are_never_planned(pack_dir: Path) -> None:
    write(pack_dir / "courses_mslearn.yaml", {"checked": "2026-10-30", "courses": [CANDIDATE]})
    pack = load_pack()
    assert pack.courses["ms_candidate_dashboards"].verified is False
    hand_checked = yaml.safe_load((pack_dir / "courses.yaml").read_text(encoding="utf-8"))
    assert pack.courses_checked == str(hand_checked["checked"])  # the catalogue date stays
    assert all(c.id != "ms_candidate_dashboards" for c in pack.courses_for("dashboards"))


def test_a_course_defined_twice_is_refused(pack_dir: Path) -> None:
    first = yaml.safe_load((pack_dir / "courses.yaml").read_text(encoding="utf-8"))["courses"][0]
    write(pack_dir / "courses_dup.yaml", {"checked": "2026-10-30", "courses": [first]})
    with pytest.raises(PackError, match="already defined"):
        load_pack()


def test_extra_resource_files_add_videos(pack_dir: Path) -> None:
    before = len(load_resources().videos)
    video = {
        "id": "yt_extra",
        "title": "Extra",
        "channel": "Channel",
        "url": "https://www.youtube.com/watch?v=x",
        "minutes": 10,
        "published": "2026-01-01",
        "skills": ["dashboards"],
    }
    write(pack_dir / "resources_scout.yaml", {"videos": [video]})
    load_resources.cache_clear()
    assert len(load_resources().videos) == before + 1
