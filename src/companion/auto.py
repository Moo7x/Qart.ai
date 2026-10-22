"""auto_diagnose: runs the companion with no user and returns a diagnosis.

Used by the evaluation runner and the optimiser. Never reads ground_truth.

LLM path (when LLM_API_KEY is set): the playbook is the instruction; the model must answer with a
strict JSON schema whose `issue_types` can only be the practised skill ids, `decision` only
sign_off / correct / escalate, and `affected_rows` only row or adjustment ids that exist in this
case. The answer is validated again in code and made consistent (sign_off ⇔ no issue). Temperature
is 0 so the same case gives the same answer. If the provider fails, the rule-based diagnosis is
used and the result says so (`source`, `fallback_reason`): fallbacks are never silent.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from src.companion.tools import (
    find_document,
    list_adjustments,
    match_entries,
    recompute_totals,
)
from src.engine.catalogue import default_catalogue

_log = logging.getLogger(__name__)

Diagnosis = dict[str, Any]
DECISIONS = ("sign_off", "correct", "escalate")
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
TEMPERATURE = 0.0  # reproducible evaluation runs
MAX_TOKENS = 600
CENT = 0.01  # amounts are in MYR with two decimals
# Practised skills that describe how the reviewer acts, not a kind of error in the reconciliation;
# case design (qart-case-author) never lists them as issue types, so they are not diagnosis labels.
BEHAVIOUR_SKILLS = frozenset({"escalation_judgment", "ai_output_review"})
# Rule-based fallback: adjustments above RM100 without a document are challenged (case design).
UNSUPPORTED_ADJUSTMENT_MIN = 100.0


def _issue_labels() -> dict[str, str]:
    """Allowed issue_types: error-type skill ids (practised, not behaviour) and their meaning."""
    catalogue = default_catalogue()
    return {
        k: catalogue.skills[k].description
        for k in catalogue.practised_skill_ids
        if k not in BEHAVIOUR_SKILLS
    }


def _row_ids(case: dict[str, Any]) -> list[str]:
    rows = [r["row_id"] for r in case.get("ledger", [])] + [
        r["row_id"] for r in case.get("bank", [])
    ]
    adjustments = case.get("ai_output", {}).get("proposed_adjustments", [])
    return rows + [a["id"] for a in adjustments]


def _schema(labels: list[str], row_ids: list[str]) -> dict[str, Any]:
    properties = {
        "has_issue": {"type": "boolean"},
        "issue_types": {"type": "array", "items": {"type": "string", "enum": labels}},
        "affected_rows": {"type": "array", "items": {"type": "string", "enum": row_ids}},
        "decision": {"type": "string", "enum": list(DECISIONS)},
        "explanation": {"type": "string"},
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "diagnosis",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


def _tool_results(
    case: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[Any], list[Any]]:
    totals = recompute_totals(case)
    matches = match_entries(case)
    adjustments = list_adjustments(case)
    log: list[Any] = [
        {"tool": "recompute_totals", "result": totals},
        {"tool": "match_entries", "result": matches},
        {"tool": "list_adjustments", "result": adjustments},
    ]
    return totals, matches, adjustments, log


def clean_diagnosis(raw: dict[str, Any], labels: list[str], row_ids: list[str]) -> Diagnosis:
    """Keep only allowed labels and existing rows; make has_issue agree with the decision."""
    decision = raw.get("decision") if raw.get("decision") in DECISIONS else "escalate"
    issue_types = [str(t) for t in raw.get("issue_types", []) if str(t) in labels]
    rows = [r for r in raw.get("affected_rows", []) if isinstance(r, str) and r in row_ids]
    has_issue = decision != "sign_off"
    return {
        "has_issue": has_issue,
        "issue_types": list(dict.fromkeys(issue_types)) if has_issue else [],
        "affected_rows": list(dict.fromkeys(rows)) if has_issue else [],
        "decision": decision,
        "explanation": str(raw.get("explanation", "")),
    }


def _llm_diagnose(
    case: dict[str, Any], playbook: str, tool_log: list[Any], api_key: str
) -> Diagnosis:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL))
    labels = _issue_labels()
    row_ids = _row_ids(case)
    case_no_gt = {k: v for k, v in case.items() if k != "ground_truth"}
    label_text = "\n".join(f"- {k}: {v}" for k, v in labels.items())
    user = (
        "Diagnose this AI-prepared bank reconciliation.\n\n"
        "issue_types: the kinds of error present, only from these ids (empty list if the "
        "reconciliation is clean):\n"
        f"{label_text}\n\n"
        "affected_rows: only the row or adjustment ids that are actually wrong (empty if clean).\n"
        "decision: follow Step 6 of the procedure.\n\n"
        f"Case:\n{json.dumps(case_no_gt, ensure_ascii=False)}\n\n"
        f"Tool results:\n{json.dumps(tool_log, ensure_ascii=False)}"
    )
    response = client.chat.completions.create(  # type: ignore[call-overload]
        model=os.getenv("LLM_MODEL", DEFAULT_MODEL),
        messages=[
            {"role": "system", "content": f"Follow this checking procedure exactly:\n\n{playbook}"},
            {"role": "user", "content": user},
        ],
        response_format=_schema(list(labels), row_ids),
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    raw = json.loads(response.choices[0].message.content or "{}")
    return clean_diagnosis(raw, list(labels), row_ids)


def auto_diagnose(case: dict[str, Any], playbook_path: str) -> Diagnosis:
    """Diagnose the case using the playbook, with no user interaction.

    Returns has_issue, issue_types (practised skill ids), affected_rows (row ids), decision
    (sign_off | correct | escalate), explanation, tool_calls, and source (llm | rule_based |
    rule_based_fallback, with fallback_reason when the LLM call failed).
    """
    playbook = Path(playbook_path).read_text(encoding="utf-8")
    api_key = os.getenv("LLM_API_KEY", "")
    totals, matches, adjustments, tool_log = _tool_results(case)
    if not api_key:
        result = _rule_based_diagnose(case, totals, matches, adjustments, tool_log)
        return {**result, "source": "rule_based"}
    try:
        diagnosis = _llm_diagnose(case, playbook, tool_log, api_key)
    except Exception as error:  # noqa: BLE001 (any provider/parse error → visible fallback)
        _log.warning("LLM diagnosis failed for %s, using rules: %s", case.get("id"), error)
        result = _rule_based_diagnose(case, totals, matches, adjustments, tool_log)
        return {**result, "source": "rule_based_fallback", "fallback_reason": str(error)[:200]}
    return {**diagnosis, "tool_calls": tool_log, "source": "llm"}


def _rule_based_diagnose(
    case: dict[str, Any],
    totals: dict[str, Any],
    matches: dict[str, Any],
    adjustments: list[Any],
    tool_calls_log: list[Any],
) -> Diagnosis:
    """Rule-based diagnosis used when no LLM key is available or the LLM call fails."""
    has_issue = False
    issue_types: list[str] = []
    affected_rows: list[str] = []

    # Unexplained difference after all adjustments
    if abs(totals["adjusted_difference"]) > CENT:
        has_issue = True
        issue_types.append("recon_to_source")

    # Unmatched ledger entries
    for row in matches.get("unmatched_ledger", []):
        has_issue = True
        affected_rows.append(row["row_id"])

    # Adjustments without supporting documents
    for adj in adjustments:
        doc_ref = None
        # Look for a ledger row that references a doc matching this adjustment's amount
        for lr in case.get("ledger", []):
            if lr.get("doc_ref") and abs(lr["amount"] - adj.get("amount", 0)) < CENT:
                doc_ref = lr["doc_ref"]
                break
        doc_supported = False
        if doc_ref:
            doc = find_document(case, doc_ref)
            doc_supported = "error" not in doc
        if not doc_supported and abs(adj.get("amount", 0)) > UNSUPPORTED_ADJUSTMENT_MIN:
            has_issue = True
            issue_types.append("unsupported_adjustment")
            affected_rows.append(adj["id"])

    # Transposition check: unmatched pairs whose digits are anagrams
    for ul in matches.get("unmatched_ledger", []):
        for ub in matches.get("unmatched_bank", []):
            a, b = abs(ul["amount"]), abs(ub["amount"])
            if sorted(str(int(a))) == sorted(str(int(b))) and a != b:
                issue_types.append("transposition_check")
                if ul["row_id"] not in affected_rows:
                    affected_rows.append(ul["row_id"])

    issue_types = list(dict.fromkeys(issue_types))  # deduplicate, preserve order
    affected_rows = list(dict.fromkeys(affected_rows))

    if not has_issue:
        decision = "sign_off"
        explanation = "All entries match and adjustments are supported."
    elif set(issue_types) == {"unsupported_adjustment"}:
        decision = "escalate"
        explanation = "Manual adjustment found without a supporting document."
    else:
        decision = "correct"
        explanation = f"Issues found: {', '.join(issue_types)}."

    return {
        "has_issue": has_issue,
        "issue_types": issue_types,
        "affected_rows": affected_rows,
        "decision": decision,
        "explanation": explanation,
        "tool_calls": tool_calls_log,
    }
