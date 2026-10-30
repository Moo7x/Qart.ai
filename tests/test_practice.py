"""Practice tasks: levels 3 and 4 of every required skill, with estimated weeks and a basis."""

import copy
from typing import Any

import pytest
import yaml

from src.levels import required_skills
from src.pack import PackError, load_pack
from src.pathway.practice import PRACTICE_FILE, load_practice, parse_practice


def raw() -> dict[str, Any]:
    return copy.deepcopy(yaml.safe_load(PRACTICE_FILE.read_text(encoding="utf-8")))


def test_every_required_skill_has_tasks_for_levels_3_and_4() -> None:
    practice = load_practice()
    for skill_id in required_skills(load_pack()):
        for level in (3, 4):
            task = practice.task(skill_id, level)
            assert task is not None and task.text and task.show_by and task.basis
            assert 0 < task.weeks_low <= task.weeks_high


def test_no_task_for_level_2_or_5() -> None:
    assert load_practice().task("erp", 2) is None
    assert load_practice().task("erp", 5) is None


def test_reversed_weeks_a_missing_level_or_an_unknown_skill_is_rejected() -> None:
    reversed_weeks = raw()
    reversed_weeks["skills"]["erp"][3]["weeks_low"] = 40
    with pytest.raises(PackError, match="erp 3"):
        parse_practice(load_pack(), reversed_weeks)
    missing = raw()
    del missing["skills"]["erp"][4]
    with pytest.raises(PackError, match="erp"):
        parse_practice(load_pack(), missing)
    unknown = raw()
    unknown["skills"]["quantum_ledger"] = unknown["skills"]["erp"]
    with pytest.raises(PackError, match="quantum_ledger"):
        parse_practice(load_pack(), unknown)
