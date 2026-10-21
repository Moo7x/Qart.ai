"""Optimisation-set variants keep the answer while changing order, ids and names."""

import json
from pathlib import Path
from typing import Any

import pytest

from eval.variants import check_variant, make_variant, make_variants, totals

EXAMPLE = Path(__file__).resolve().parent.parent / "schemas" / "examples" / "case.json"


def case() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    return data


def test_variant_keeps_ground_truth_and_totals_but_renames_ids_and_names() -> None:
    original = case()
    variant = make_variant(original, 1)
    assert variant["id"] == "case_003_v1" and variant["variant_of"] == "case_003"
    truth = variant["ground_truth"]
    assert truth["affected_rows"] == ["L104", "ADJ-107"]
    assert truth["correct_decision"] == original["ground_truth"]["correct_decision"]
    assert totals(variant) == totals(original)
    assert variant["ledger"][0]["doc_ref"] == "INV-2043"
    assert variant["documents"][0]["doc_ref"] == "INV-2043"
    assert "BEANS" not in json.dumps(variant) and "KACANG CO" in variant["bank"][0]["description"]


def test_variants_are_reproducible_and_only_for_practice_cases() -> None:
    checkin = {**case(), "id": "checkin_x", "mode": "checkin"}
    variants = make_variants([case(), checkin], per_case=2)
    assert [v["id"] for v in variants] == ["case_003_v1", "case_003_v2"]
    assert make_variant(case(), 2) == variants[1]


def test_check_variant_rejects_a_changed_answer() -> None:
    original = case()
    broken = make_variant(original, 1)
    broken["ground_truth"]["correct_decision"] = "sign_off"
    with pytest.raises(ValueError, match="ground truth changed"):
        check_variant(original, broken)
