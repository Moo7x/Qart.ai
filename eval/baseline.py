"""Text-only LLM baseline (PERSON_A Task A8): the same model as the companion, given the raw case.

It answers in the companion's format (same labels, same row ids, same strict schema) but gets no
playbook and no tool results (no recomputed totals, no matching). The evaluation compares it with
the companion so we can say whether the playbook and the deterministic tools add anything over
"just ask the model". Never reads ground_truth. Without LLM_API_KEY it raises NotImplementedError,
which the runner reports as "not run".
"""

import os
from typing import Any

from src.companion.auto import Diagnosis, diagnosis_request, llm_diagnosis

SYSTEM = "You review AI-prepared bank reconciliations for a finance team."
DECISION_RULE = "sign_off if the reconciliation is right, correct if you can fix it, else escalate."


def text_only_baseline(case: dict[str, Any], playbook_path: str) -> Diagnosis:
    """Diagnose from the raw case only (playbook_path is ignored by design)."""
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        raise NotImplementedError("text-only baseline needs LLM_API_KEY")
    diagnosis = llm_diagnosis(case, SYSTEM, diagnosis_request(case, DECISION_RULE), api_key)
    return {**diagnosis, "source": "llm"}
