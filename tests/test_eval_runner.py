"""Evaluation scaffold (item 5): fixed criteria, stubs, and RESULTS.md sections."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from eval.acceptance_criteria import criteria_hash, grade
from eval.baseline import text_only_baseline
from eval.results_md import write_section
from eval.runner import (
    auto_diagnose_not_available,
    default_diagnosers,
    evaluate,
    run,
)

EXAMPLE_CASE = Path(__file__).resolve().parent.parent / "schemas" / "examples" / "case.json"


def issue_case() -> dict[str, Any]:
    case: dict[str, Any] = json.loads(EXAMPLE_CASE.read_text(encoding="utf-8"))
    return case


def clean_case() -> dict[str, Any]:
    case = copy.deepcopy(issue_case())
    case["id"] = "case_clean"
    case["ground_truth"].update(
        {"has_issue": False, "issue_types": [], "affected_rows": [], "correct_decision": "sign_off"}
    )
    return case


def perfect(case: dict[str, Any], playbook: str) -> dict[str, Any]:
    truth = case["ground_truth"]
    return {
        "has_issue": truth["has_issue"],
        "issue_types": truth["issue_types"],
        "affected_rows": truth["affected_rows"],
        "decision": truth["correct_decision"],
    }


def flag_everything(case: dict[str, Any], playbook: str) -> dict[str, Any]:
    return {
        "has_issue": True,
        "issue_types": ["unsupported_adjustment"],
        "affected_rows": ["L4", "X99"],
        "decision": "escalate",
    }


def test_perfect_diagnosis_scores_full_marks() -> None:
    summary = evaluate("perfect", [issue_case(), clean_case()], perfect, "pb")
    assert (summary.root_cause_correct, summary.decision_correct) == (2, 2)
    assert (summary.false_alarms, summary.invalid_citations, summary.clean_cases) == (0, 0, 1)


def test_flag_everything_is_caught_as_false_alarm_with_invalid_citation() -> None:
    result = grade(clean_case(), flag_everything(clean_case(), "pb"))
    assert result.false_alarm and not result.root_cause_correct
    assert result.invalid_citations == 1  # X99 does not exist in the case


def test_stubs_raise_and_runner_reports_not_run(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError):
        auto_diagnose_not_available(issue_case(), "pb")
    with pytest.raises(NotImplementedError):
        text_only_baseline(issue_case(), "pb")  # no LLM_API_KEY in tests
    cases = tmp_path / "cases"
    cases.mkdir()
    (cases / "case_003.json").write_text(json.dumps(issue_case()), encoding="utf-8")
    results = tmp_path / "RESULTS.md"
    summaries = run(cases, "pb", results, {"companion": auto_diagnose_not_available})
    assert all(s.error for s in summaries)
    assert "not run" in results.read_text(encoding="utf-8")


def test_runner_with_a_diagnoser_writes_counts(tmp_path: Path) -> None:
    cases = tmp_path / "cases"
    cases.mkdir()
    for case in (issue_case(), clean_case()):
        (cases / f"{case['id']}.json").write_text(json.dumps(case), encoding="utf-8")
    results = tmp_path / "RESULTS.md"
    run(cases, "pb", results, {"companion (auto_diagnose)": perfect})
    text = results.read_text(encoding="utf-8")
    assert "| companion (auto_diagnose) | 2/2 | 2/2 | 0/1 | 0 |" in text


def test_empty_acceptance_folder_is_reported_honestly(tmp_path: Path) -> None:
    results = tmp_path / "RESULTS.md"
    run(tmp_path, "pb", results)
    assert "Not run:** no acceptance cases" in results.read_text(encoding="utf-8")


def test_criteria_hash_is_a_sha256() -> None:
    value = criteria_hash()
    assert value.startswith("sha256:") and len(value) == len("sha256:") + 64


def test_write_section_replaces_only_its_own_block(tmp_path: Path) -> None:
    path = tmp_path / "RESULTS.md"
    write_section("a", "first", path)
    write_section("b", "other", path)
    write_section("a", "second", path)
    text = path.read_text(encoding="utf-8")
    assert "second" in text and "first" not in text and "other" in text


def test_criteria_hash_ignores_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import eval.acceptance_criteria as criteria

    source = Path(criteria.__file__).read_bytes().replace(b"\r\n", b"\n")
    crlf = tmp_path / "crlf.py"
    crlf.write_bytes(source.replace(b"\n", b"\r\n"))
    lf_hash = criteria.criteria_hash()
    monkeypatch.setattr(criteria, "__file__", str(crlf))
    assert criteria.criteria_hash() == lf_hash


def test_index_files_are_not_treated_as_cases(tmp_path: Path) -> None:
    from eval.runner import load_cases

    (tmp_path / "index.json").write_text('{"cases": []}', encoding="utf-8")
    (tmp_path / "a001.json").write_text(json.dumps(issue_case()), encoding="utf-8")
    assert [c["id"] for c in load_cases(tmp_path)] == ["case_003"]


def test_llm_answers_are_counted_and_fallbacks_are_not(tmp_path: Path) -> None:
    def half_llm(case: dict[str, Any], playbook: str) -> dict[str, Any]:
        source = "llm" if case["id"] == "case_clean" else "rule_based_fallback"
        return {**perfect(case, playbook), "source": source}

    cases = tmp_path / "cases"
    cases.mkdir()
    for case in (issue_case(), clean_case()):
        (cases / f"{case['id']}.json").write_text(json.dumps(case), encoding="utf-8")
    results = tmp_path / "RESULTS.md"
    [summary] = run(cases, "pb", results, {"companion, LLM": half_llm})
    assert summary.llm_answers == 1
    assert "1/2 answered by the LLM" in results.read_text(encoding="utf-8")


def test_without_a_key_only_the_rules_companion_runs(tmp_path: Path) -> None:
    (tmp_path / "case_003.json").write_text(json.dumps(issue_case()), encoding="utf-8")
    results = tmp_path / "RESULTS.md"
    summaries = run(tmp_path, "src/companion/playbooks/playbook_v1.md", results)
    assert [s.error is None for s in summaries] == [True, False, False]
    assert len(default_diagnosers()) == 3
