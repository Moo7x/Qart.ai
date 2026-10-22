"""Companion tools – deterministic Python functions the LLM calls through function calling.
All functions accept a `case` dict but never read ground_truth.
"""

from __future__ import annotations

from typing import Any


def get_section(case: dict[str, Any], section: str) -> dict[str, Any]:
    """Return one section of the case: ledger, bank, documents, or ai_output."""
    valid = {"ledger", "bank", "documents", "ai_output"}
    if section not in valid:
        return {"error": f"section must be one of {sorted(valid)}"}
    return {section: case.get(section, [])}


def recompute_totals(case: dict[str, Any]) -> dict[str, Any]:
    """Compute ledger total, bank total, their difference, and the adjustments total."""
    ledger_total = sum(r["amount"] for r in case.get("ledger", []))
    bank_total = sum(r["amount"] for r in case.get("bank", []))
    adj_total = sum(a["amount"] for a in case.get("ai_output", {}).get("proposed_adjustments", []))
    difference = round(ledger_total - bank_total, 2)
    return {
        "ledger_total": round(ledger_total, 2),
        "bank_total": round(bank_total, 2),
        "difference": difference,
        "adjustments_total": round(adj_total, 2),
        "adjusted_difference": round(difference + adj_total, 2),
    }


def match_entries(case: dict[str, Any], tolerance: float = 0.01) -> dict[str, Any]:
    """Match ledger rows to bank rows by amount (within tolerance). Return matched/unmatched."""
    ledger = list(case.get("ledger", []))
    bank = list(case.get("bank", []))
    matched = []
    unmatched_ledger = []
    used_bank: set[int] = set()
    for lr in ledger:
        found = None
        for i, br in enumerate(bank):
            if i not in used_bank and abs(lr["amount"] - br["amount"]) <= tolerance:
                found = i
                break
        if found is not None:
            matched.append(
                {
                    "ledger_row": lr["row_id"],
                    "bank_row": bank[found]["row_id"],
                    "amount": lr["amount"],
                }
            )
            used_bank.add(found)
        else:
            unmatched_ledger.append(
                {
                    "row_id": lr["row_id"],
                    "amount": lr["amount"],
                    "description": lr["description"],
                }
            )
    unmatched_bank = [
        {"row_id": br["row_id"], "amount": br["amount"], "description": br["description"]}
        for i, br in enumerate(bank)
        if i not in used_bank
    ]
    return {
        "matched": matched,
        "unmatched_ledger": unmatched_ledger,
        "unmatched_bank": unmatched_bank,
    }


def find_document(case: dict[str, Any], doc_ref: str) -> dict[str, Any]:
    """Find a document by doc_ref. Returns the document or an error."""
    documents: list[dict[str, Any]] = case.get("documents", [])
    for doc in documents:
        if doc["doc_ref"] == doc_ref:
            return doc
    return {"error": f"No document found for ref '{doc_ref}'"}


def compare_amounts(a: float, b: float) -> dict[str, Any]:
    """Compare two amounts and return the difference."""
    diff = round(a - b, 2)
    return {"a": a, "b": b, "difference": diff, "match": abs(diff) < 0.01}


def list_adjustments(case: dict[str, Any]) -> list[dict[str, Any]]:
    """List all proposed adjustments from the AI output."""
    adjustments: list[dict[str, Any]] = case.get("ai_output", {}).get("proposed_adjustments", [])
    return adjustments
