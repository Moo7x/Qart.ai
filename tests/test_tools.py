"""Unit tests for src/companion/tools.py using case_003 fixture data."""

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.companion.tools import (
    compare_amounts,
    find_document,
    get_section,
    list_adjustments,
    match_entries,
    recompute_totals,
)

CASES_DIR = pathlib.Path(__file__).resolve().parent.parent / "cases"


@pytest.fixture
def case_003():
    return json.loads((CASES_DIR / "case_003.json").read_text())


@pytest.fixture
def case_001():
    return json.loads((CASES_DIR / "case_001.json").read_text())


# ── recompute_totals ──────────────────────────────────────────────────────────


def test_recompute_totals_case003(case_003):
    result = recompute_totals(case_003)
    assert result["ledger_total"] == pytest.approx(39380.0)
    assert result["bank_total"] == pytest.approx(39650.0)
    assert result["difference"] == pytest.approx(-270.0)
    assert result["adjustments_total"] == pytest.approx(270.0)
    assert result["adjusted_difference"] == pytest.approx(0.0)


def test_recompute_totals_clean(case_001):
    result = recompute_totals(case_001)
    assert result["difference"] == pytest.approx(0.0)
    assert result["adjusted_difference"] == pytest.approx(0.0)


# ── match_entries ─────────────────────────────────────────────────────────────


def test_match_entries_unmatched_row(case_003):
    result = match_entries(case_003)
    unmatched_l = [r["row_id"] for r in result["unmatched_ledger"]]
    unmatched_b = [r["row_id"] for r in result["unmatched_bank"]]
    assert "L4" in unmatched_l  # -1520 doesn't match -1250
    assert "B6" in unmatched_b  # -1250 doesn't match -1520


def test_match_entries_all_match(case_001):
    result = match_entries(case_001)
    assert result["unmatched_ledger"] == []
    assert result["unmatched_bank"] == []
    assert len(result["matched"]) == len(case_001["ledger"])


def test_match_entries_matched_rows(case_003):
    result = match_entries(case_003)
    matched_ledger_ids = {m["ledger_row"] for m in result["matched"]}
    # All rows except L4 should be matched
    for row in case_003["ledger"]:
        if row["row_id"] != "L4":
            assert row["row_id"] in matched_ledger_ids


# ── find_document ─────────────────────────────────────────────────────────────


def test_find_document_found(case_003):
    doc = find_document(case_003, "INV-1043")
    assert doc["doc_ref"] == "INV-1043"
    assert "1,250" in doc["text"]


def test_find_document_not_found(case_003):
    result = find_document(case_003, "NONEXISTENT")
    assert "error" in result


# ── compare_amounts ───────────────────────────────────────────────────────────


def test_compare_amounts_mismatch():
    result = compare_amounts(1520.0, 1250.0)
    assert result["difference"] == pytest.approx(270.0)
    assert result["match"] is False


def test_compare_amounts_match():
    result = compare_amounts(3200.0, 3200.0)
    assert result["difference"] == pytest.approx(0.0)
    assert result["match"] is True


# ── list_adjustments ──────────────────────────────────────────────────────────


def test_list_adjustments(case_003):
    adjs = list_adjustments(case_003)
    assert len(adjs) == 1
    assert adjs[0]["id"] == "ADJ-7"
    assert adjs[0]["amount"] == pytest.approx(270.0)


def test_list_adjustments_empty(case_001):
    adjs = list_adjustments(case_001)
    assert adjs == []


# ── get_section ───────────────────────────────────────────────────────────────


def test_get_section_ledger(case_003):
    result = get_section(case_003, "ledger")
    assert "ledger" in result
    assert len(result["ledger"]) == 7


def test_get_section_invalid():
    result = get_section({}, "invalid_section")
    assert "error" in result
