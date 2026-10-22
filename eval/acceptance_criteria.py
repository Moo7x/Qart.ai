"""Fixed acceptance criteria for companion diagnoses (PROJECT_PLAN §7). Hashed; never tuned.

The optimiser must not read or change this file. Its SHA-256 (`criteria_hash()`) is written into
every OptimizerProposal (`acceptance_set.criteria_hash`) so any change is visible.

Per case, comparing the companion's diagnosis with the case's ground truth:
- root_cause_correct: has_issue matches and, for cases with an issue, the issue_types sets match.
- decision_correct: the decision (sign_off / correct / escalate) equals correct_decision.
- false_alarm: a clean case (has_issue false) diagnosed as having an issue.
- invalid_citations: cited affected_rows that do not exist in the case (ledger, bank or proposed
  adjustment ids). Every row the companion cites must exist.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HASH_PREFIX = "sha256:"


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    clean: bool
    root_cause_correct: bool
    decision_correct: bool
    false_alarm: bool
    invalid_citations: int


def case_row_ids(case: dict[str, Any]) -> set[str]:
    """Every id a diagnosis may cite: ledger rows, bank rows and proposed adjustments."""
    rows = {r["row_id"] for r in case.get("ledger", [])} | {
        r["row_id"] for r in case.get("bank", [])
    }
    adjustments = case.get("ai_output", {}).get("proposed_adjustments", [])
    return rows | {a["id"] for a in adjustments}


def grade(case: dict[str, Any], diagnosis: dict[str, Any]) -> CaseResult:
    truth = case["ground_truth"]
    clean = not truth["has_issue"]
    same_flag = bool(diagnosis.get("has_issue")) == truth["has_issue"]
    same_types = set(diagnosis.get("issue_types", [])) == set(truth["issue_types"])
    cited = diagnosis.get("affected_rows", [])
    known = case_row_ids(case)
    return CaseResult(
        case_id=case["id"],
        clean=clean,
        root_cause_correct=same_flag and (clean or same_types),
        decision_correct=diagnosis.get("decision") == truth["correct_decision"],
        false_alarm=clean and bool(diagnosis.get("has_issue")),
        invalid_citations=sum(1 for row in cited if row not in known),
    )


def criteria_hash() -> str:
    """SHA-256 of this file, so a changed criterion is detectable in every report.

    Line endings are normalised first, so Windows (CRLF) and Linux/Replit (LF) checkouts agree.
    """
    text = Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256(text).hexdigest()
    return f"{HASH_PREFIX}{digest}"
