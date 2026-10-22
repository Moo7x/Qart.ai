"""Evaluation runner for companion diagnoses (Increment 3 scaffold, PERSON_A Task A8).

Usage:  python -m eval.runner [--cases eval/acceptance] [--playbook <path>]

For every case in the acceptance folder it calls Person B's
`src/companion/auto.py::auto_diagnose(case, playbook_path)` and, for comparison, a text-only
baseline (the same LLM given the raw tables without tools), then grades both with the fixed
criteria in eval/acceptance_criteria.py and writes counts to eval/RESULTS.md.

Neither diagnoser exists yet: both are clearly named stubs that raise NotImplementedError, and the
runner reports "not run" instead of inventing numbers. No LLM is called here; when the baseline is
built it must go through a provider-agnostic interface (the provider will be configured through
LLM_API_KEY).
"""

import argparse
import importlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.acceptance_criteria import CaseResult, criteria_hash, grade
from eval.results_md import RESULTS_PATH, write_section

ACCEPTANCE_DIR = Path(__file__).resolve().parent / "acceptance"
DEFAULT_PLAYBOOK = "src/companion/playbooks/playbook_v1.md"
SECTION = "companion-evaluation"

Diagnosis = dict[str, Any]
Diagnoser = Callable[[dict[str, Any], str], Diagnosis]


def auto_diagnose_not_available(case: dict[str, Any], playbook_path: str) -> Diagnosis:
    """Stub used until Person B ships src/companion/auto.py::auto_diagnose."""
    raise NotImplementedError(
        "auto_diagnose is not available yet: Person B's src/companion/auto.py is missing"
    )


def text_only_baseline_not_built(case: dict[str, Any], playbook_path: str) -> Diagnosis:
    """Stub for the text-only LLM baseline (raw tables, no tools). No LLM is called in this run."""
    raise NotImplementedError(
        "text-only baseline not built yet: it needs the provider-agnostic LLM client (LLM_API_KEY)"
    )


def load_auto_diagnose() -> Diagnoser:
    """B's auto_diagnose if importable, else the stub."""
    try:
        module = importlib.import_module("src.companion.auto")
    except ModuleNotFoundError:
        return auto_diagnose_not_available
    diagnoser: Diagnoser = module.auto_diagnose
    return diagnoser


def load_cases(directory: Path = ACCEPTANCE_DIR) -> list[dict[str, Any]]:
    """Acceptance cases (contract Case JSON with ground_truth), sorted by file name.

    Index files (index.json) and anything without a ground_truth are skipped.
    """
    cases = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
        if path.name != "index.json"
    ]
    return [c for c in cases if isinstance(c, dict) and "ground_truth" in c]


@dataclass(frozen=True)
class Summary:
    name: str
    cases: int
    clean_cases: int
    root_cause_correct: int
    decision_correct: int
    false_alarms: int
    invalid_citations: int
    error: str | None = None


def evaluate(
    name: str, cases: Sequence[dict[str, Any]], diagnose: Diagnoser, playbook_path: str
) -> Summary:
    """Grade one diagnoser on all cases; a missing diagnoser yields a summary with `error`."""
    results: list[CaseResult] = []
    for case in cases:
        try:
            diagnosis = diagnose(case, playbook_path)
        except NotImplementedError as missing:
            return Summary(name, len(cases), 0, 0, 0, 0, 0, error=str(missing))
        results.append(grade(case, diagnosis))
    return Summary(
        name=name,
        cases=len(results),
        clean_cases=sum(r.clean for r in results),
        root_cause_correct=sum(r.root_cause_correct for r in results),
        decision_correct=sum(r.decision_correct for r in results),
        false_alarms=sum(r.false_alarm for r in results),
        invalid_citations=sum(r.invalid_citations for r in results),
    )


def render(summaries: Sequence[Summary], case_count: int) -> str:
    lines = [
        "## Companion evaluation (acceptance set)",
        "",
        f"Criteria: `eval/acceptance_criteria.py` ({criteria_hash()}). Cases: {case_count}.",
        "",
    ]
    if case_count == 0:
        lines.append("**Not run:** no acceptance cases in `eval/acceptance/` yet (Person B).")
        return "\n".join(lines)
    lines += [
        "| Diagnoser | Root cause | Decision | False alarms (clean) | Invalid citations | Note |",
        "|---|---|---|---|---|---|",
    ]
    for s in summaries:
        if s.error:
            lines.append(f"| {s.name} | not run | not run | not run | not run | {s.error} |")
            continue
        lines.append(
            f"| {s.name} | {s.root_cause_correct}/{s.cases} | {s.decision_correct}/{s.cases} | "
            f"{s.false_alarms}/{s.clean_cases} | {s.invalid_citations} | |"
        )
    return "\n".join(lines)


def run(
    cases_dir: Path = ACCEPTANCE_DIR,
    playbook_path: str = DEFAULT_PLAYBOOK,
    results_path: Path = RESULTS_PATH,
    companion: Diagnoser | None = None,
    baseline: Diagnoser = text_only_baseline_not_built,
) -> list[Summary]:
    cases = load_cases(cases_dir)
    summaries = [
        evaluate(
            "companion (auto_diagnose)", cases, companion or load_auto_diagnose(), playbook_path
        ),
        evaluate("text-only baseline", cases, baseline, playbook_path),
    ]
    write_section(SECTION, render(summaries, len(cases)), results_path)
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ACCEPTANCE_DIR)
    parser.add_argument("--playbook", default=DEFAULT_PLAYBOOK)
    args = parser.parse_args()
    for summary in run(args.cases, args.playbook):
        print(summary)


if __name__ == "__main__":
    main()
