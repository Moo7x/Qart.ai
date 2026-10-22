"""Evaluation runner for companion diagnoses (PERSON_A Task A8).

Usage:  python -m eval.runner [--cases eval/acceptance] [--playbook <path>]

For every case in the acceptance folder it runs three diagnosers and grades each with the fixed
criteria in eval/acceptance_criteria.py, then writes counts to eval/RESULTS.md:

- companion, rules only: `src/companion/auto.py::auto_diagnose(..., use_llm=False)`;
- companion, LLM: the same function with the playbook and tool results given to the model;
- text-only baseline (eval/baseline.py): the same model given the raw case, no tools or playbook.

LLM rows run only when LLM_API_KEY is set (read from the environment or .env); otherwise they are
reported as "not run". The Note column says how many answers really came from the model, so a
silent fallback to rules can never pass as an LLM result. Run it once per playbook version: the
acceptance set is for scoring, never for tuning.
"""

import argparse
import importlib
import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.acceptance_criteria import CaseResult, criteria_hash, grade
from eval.results_md import RESULTS_PATH, write_section
from src.envfile import load_env_file

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
    llm_answers: int = 0  # diagnoses whose source is "llm" (not a rule-based fallback)


def evaluate(
    name: str, cases: Sequence[dict[str, Any]], diagnose: Diagnoser, playbook_path: str
) -> Summary:
    """Grade one diagnoser on all cases; a missing diagnoser yields a summary with `error`."""
    results: list[CaseResult] = []
    llm_answers = 0
    for case in cases:
        try:
            diagnosis = diagnose(case, playbook_path)
        except NotImplementedError as missing:
            return Summary(name, len(cases), 0, 0, 0, 0, 0, error=str(missing))
        results.append(grade(case, diagnosis))
        llm_answers += diagnosis.get("source") == "llm"
    return Summary(
        name=name,
        cases=len(results),
        clean_cases=sum(r.clean for r in results),
        root_cause_correct=sum(r.root_cause_correct for r in results),
        decision_correct=sum(r.decision_correct for r in results),
        false_alarms=sum(r.false_alarm for r in results),
        invalid_citations=sum(r.invalid_citations for r in results),
        llm_answers=llm_answers,
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
            f"{s.false_alarms}/{s.clean_cases} | {s.invalid_citations} | {note(s)} |"
        )
    return "\n".join(lines)


def note(summary: Summary) -> str:
    if summary.llm_answers == 0:
        return ""
    return f"{summary.llm_answers}/{summary.cases} answered by the LLM"


def llm_not_configured(case: dict[str, Any], playbook_path: str) -> Diagnosis:
    raise NotImplementedError("needs LLM_API_KEY")


def companion_rules_only(case: dict[str, Any], playbook_path: str) -> Diagnosis:
    from src.companion.auto import auto_diagnose

    return auto_diagnose(case, playbook_path, use_llm=False)


def default_diagnosers() -> dict[str, Diagnoser]:
    """Rules-only companion always; LLM companion and text-only baseline when a key is set."""
    from eval.baseline import text_only_baseline

    companion = load_auto_diagnose()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    has_key = bool(os.getenv("LLM_API_KEY"))
    rules = companion if companion is auto_diagnose_not_available else companion_rules_only
    return {
        "companion, rules only": rules,
        f"companion, LLM ({model})": companion if has_key else llm_not_configured,
        f"text-only baseline ({model})": text_only_baseline,
    }


def run(
    cases_dir: Path = ACCEPTANCE_DIR,
    playbook_path: str = DEFAULT_PLAYBOOK,
    results_path: Path = RESULTS_PATH,
    diagnosers: dict[str, Diagnoser] | None = None,
) -> list[Summary]:
    cases = load_cases(cases_dir)
    chosen = diagnosers if diagnosers is not None else default_diagnosers()
    summaries = [
        evaluate(name, cases, diagnose, playbook_path) for name, diagnose in chosen.items()
    ]
    write_section(SECTION, render(summaries, len(cases)), results_path)
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ACCEPTANCE_DIR)
    parser.add_argument("--playbook", default=DEFAULT_PLAYBOOK)
    args = parser.parse_args()
    load_env_file()
    for summary in run(args.cases, args.playbook):
        print(summary)


if __name__ == "__main__":
    main()
