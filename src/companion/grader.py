"""Grader – the ONLY module that reads ground_truth.

grade() is called after the user submits a decision. Only this function may access
case["ground_truth"]. All other modules must treat ground_truth as absent.
"""

from __future__ import annotations

from typing import Any


def grade(case: dict[str, Any], decision: str, flagged_rows: list[str]) -> dict[str, Any]:
    """
    Grade a user decision against the case ground truth.

    Returns:
        decision_correct: whether the decision matches the correct answer
        skills_evidence: list of {skill_id, outcome, help_level} — help_level is 0 here;
                         agent.py enriches it from session state after calling grade()
        explanation: the ground truth explanation
        issue_found_by: "user" | "companion" | "none"
        affected_rows: the rows that contained issues
        correct_decision: the ground truth correct decision
    """
    gt = case.get("ground_truth", {})
    correct_decision = gt.get("correct_decision", "sign_off")
    affected_rows = gt.get("affected_rows", [])
    skills = gt.get("skills", [])
    explanation = gt.get("explanation", "")
    has_issue = gt.get("has_issue", False)

    decision_correct = decision == correct_decision

    user_found = any(row in affected_rows for row in (flagged_rows or []))
    if not has_issue:
        issue_found_by = "none"
    elif user_found:
        issue_found_by = "user"
    else:
        issue_found_by = "companion"

    # outcome is "success" or "failure" only; agent.py upgrades to "missed_then_found"
    # when the user eventually finds the issue after a prior wrong decision.
    skills_evidence = []
    for skill_id in skills:
        outcome = "success" if decision_correct else "failure"
        skills_evidence.append({"skill_id": skill_id, "outcome": outcome, "help_level": 0})

    return {
        "decision_correct": decision_correct,
        "skills_evidence": skills_evidence,
        "explanation": explanation,
        "issue_found_by": issue_found_by,
        "affected_rows": affected_rows,
        "correct_decision": correct_decision,
    }
