"""Level descriptions: a 0–5 scale and five sentences for every skill a destination role needs."""

import copy
from typing import Any

import pytest
import yaml

from src.levels import LEVELS_FILE, load_levels, main, missing, parse_levels, required_skills
from src.pack import PackError, load_pack


def raw() -> dict[str, Any]:
    return copy.deepcopy(yaml.safe_load(LEVELS_FILE.read_text(encoding="utf-8")))


def test_every_required_skill_has_sentences_for_levels_1_to_5() -> None:
    levels = load_levels()
    assert missing(load_pack(), levels) == []
    for skill_id in required_skills(load_pack()):
        assert all(levels.anchor(skill_id, level).startswith("I ") for level in range(1, 6))


def test_scale_has_six_labels_from_none_to_expert() -> None:
    assert load_levels().labels() == ["none", "novice", "aware", "working", "proficient", "expert"]


def test_every_skill_cites_a_basis_with_a_read_date() -> None:
    for skill in load_levels().skills.values():
        assert skill.basis and all(b.url.startswith("https://") and b.read for b in skill.basis)


def test_unknown_skill_or_a_gap_in_the_sentences_is_rejected() -> None:
    unknown = raw()
    unknown["skills"]["quantum_ledger"] = unknown["skills"]["erp"]
    with pytest.raises(PackError, match="quantum_ledger"):
        parse_levels(load_pack(), unknown)
    gap = raw()
    del gap["skills"]["erp"]["anchors"][3]
    with pytest.raises(PackError, match="erp"):
        parse_levels(load_pack(), gap)


def test_missing_lists_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--missing"]) == 0
    assert capsys.readouterr().out == ""
