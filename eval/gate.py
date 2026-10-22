"""Acceptance gate for a frozen playbook candidate (evaluator side of PERSON_A Task A9).

The optimiser (src/optimizer/loop.py) never reads the acceptance set. Once its candidate text is
fixed, this gate scores the current playbook and the candidate on eval/acceptance/ with the same
fixed criteria (eval/acceptance_criteria.py, hash reported), once each, and lists regressions:
acceptance cases the current playbook decided correctly and the candidate gets wrong. Only counts
and case ids leave this module; nothing from it is fed back into the optimiser.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from eval.acceptance_criteria import CaseResult, criteria_hash, grade
from eval.runner import ACCEPTANCE_DIR, load_cases
from src.companion.auto import diagnose_with_playbook
from src.contract import AcceptanceResult, SetResult
from src.optimizer.loop import Diagnose, SetScore, score_results


@dataclass(frozen=True)
class GateResult:
    acceptance: AcceptanceResult
    regressions: list[str]
    base: SetScore
    candidate: SetScore


def _results(
    playbook: str, cases: Sequence[dict[str, Any]], diagnose: Diagnose
) -> list[CaseResult]:
    return [grade(case, diagnose(case, playbook)) for case in cases]


def run_gate(
    base_text: str,
    candidate_text: str,
    diagnose: Diagnose = diagnose_with_playbook,
    cases: Sequence[dict[str, Any]] | None = None,
) -> GateResult:
    acceptance = list(cases) if cases is not None else load_cases(ACCEPTANCE_DIR)
    before = _results(base_text, acceptance, diagnose)
    after = _results(candidate_text, acceptance, diagnose)
    base, candidate = score_results(before), score_results(after)
    regressions = [
        b.case_id
        for b, a in zip(before, after, strict=True)
        if b.decision_correct and not a.decision_correct
    ]
    result = AcceptanceResult(
        before=base.summary(),
        after=candidate.summary(),
        criteria_hash=criteria_hash(),
        false_alarms_clean=SetResult(
            before=f"{base.false_alarms}/{base.clean}",
            after=f"{candidate.false_alarms}/{candidate.clean}",
        ),
        invalid_citations=candidate.invalid_citations,
    )
    return GateResult(result, regressions, base, candidate)
