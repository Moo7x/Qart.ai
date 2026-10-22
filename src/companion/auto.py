"""auto_diagnose – runs the companion with no user, returning a diagnosis.
Used by Person A's evaluation runner and optimiser. Does NOT read ground_truth.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.companion.tools import (
    find_document,
    list_adjustments,
    match_entries,
    recompute_totals,
)


def auto_diagnose(case: dict, playbook_path: str) -> dict:
    """
    Diagnose the case using the playbook, with no user interaction.

    Returns:
        has_issue: bool
        issue_types: list of skill_id strings
        affected_rows: list of row_id strings
        decision: "sign_off" | "correct" | "escalate"
        explanation: one-sentence summary
        tool_calls: list of {tool, result} for auditing
    """
    playbook = Path(playbook_path).read_text()
    api_key = os.getenv("LLM_API_KEY", "")

    tool_calls_log: list[dict] = []

    totals = recompute_totals(case)
    tool_calls_log.append({"tool": "recompute_totals", "result": totals})

    matches = match_entries(case)
    tool_calls_log.append({"tool": "match_entries", "result": matches})

    adjustments = list_adjustments(case)
    tool_calls_log.append({"tool": "list_adjustments", "result": adjustments})

    if not api_key:
        return _rule_based_diagnose(case, totals, matches, adjustments, tool_calls_log)

    try:
        from openai import OpenAI  # type: ignore[import-not-found]

        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        case_no_gt = {k: v for k, v in case.items() if k != "ground_truth"}

        prompt = (
            f"You are diagnosing a bank reconciliation. Follow this playbook:\n\n{playbook}\n\n"
            f"Case:\n{json.dumps(case_no_gt, indent=2)}\n\n"
            f"Tool results:\n"
            f"- Totals: {json.dumps(totals)}\n"
            f"- Entries: {json.dumps(matches)}\n"
            f"- Adjustments: {json.dumps(adjustments)}\n\n"
            "Respond with JSON only:\n"
            '{"has_issue": bool, "issue_types": [...], "affected_rows": [...], '
            '"decision": "sign_off"|"correct"|"escalate", "explanation": "one sentence"}'
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        result = json.loads(response.choices[0].message.content or "")
        result["tool_calls"] = tool_calls_log
        return result
    except Exception:  # noqa: BLE001
        return _rule_based_diagnose(case, totals, matches, adjustments, tool_calls_log)


def _rule_based_diagnose(
    case: dict,
    totals: dict,
    matches: dict,
    adjustments: list,
    tool_calls_log: list,
) -> dict:
    """Fallback rule-based diagnosis used when no LLM key is available."""
    has_issue = False
    issue_types: list[str] = []
    affected_rows: list[str] = []

    # Unexplained difference after all adjustments
    if abs(totals["adjusted_difference"]) > 0.01:
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
            if lr.get("doc_ref") and abs(lr["amount"] - adj.get("amount", 0)) < 0.01:
                doc_ref = lr["doc_ref"]
                break
        doc_supported = False
        if doc_ref:
            doc = find_document(case, doc_ref)
            doc_supported = "error" not in doc
        if not doc_supported and abs(adj.get("amount", 0)) > 100:
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
