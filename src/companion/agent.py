"""Companion agent – manages sessions, runs the help ladder, calls the LLM."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from src.companion.playbook_versions import BASE_VERSION, read_playbook
from src.companion.tools import (
    compare_amounts,
    find_document,
    get_section,
    list_adjustments,
    match_entries,
    recompute_totals,
)

# In-memory session store (fine for hackathon; one process)
_sessions: dict[str, dict[str, Any]] = {}

HELP_LEVEL_NAMES = {
    0: "no help",
    1: "a question",
    2: "a hint",
    3: "an explanation",
    4: "the answer shown",
}
HELP_STEP_NAMES = {1: "question", 2: "hint", 3: "explanation", 4: "answer"}
WALK_BACK_MESSAGE = (
    "That decision does not match what the evidence shows. Have another look: press "
    "'I'm stuck' for a question, then a hint, if you need one."
)

_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "recompute_totals",
            "description": "Recompute ledger and bank totals and their difference.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "match_entries",
            "description": "Match ledger rows to bank rows by amount.",
            "parameters": {
                "type": "object",
                "properties": {"tolerance": {"type": "number"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_adjustments",
            "description": "List all proposed adjustments from the AI output.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_document",
            "description": "Find a document by doc_ref.",
            "parameters": {
                "type": "object",
                "properties": {"doc_ref": {"type": "string"}},
                "required": ["doc_ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_amounts",
            "description": "Compare two monetary amounts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_section",
            "description": "Get a section of the case (ledger, bank, documents, ai_output).",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["ledger", "bank", "documents", "ai_output"],
                    }
                },
                "required": ["section"],
            },
        },
    },
]


def _reset_case_state(session: dict[str, Any], case: dict[str, Any], mode: str) -> None:
    """Reset per-case fields when the user opens a new case in the same session."""
    session.update(
        {
            "current_case_id": case["id"],
            "case": case,
            "mode": mode,
            "help_level": 0,
            "help_steps": [],
            "checks_used": [],
            "messages": [],  # clear chat history so case B doesn't inherit case A's context
            "start_time": datetime.now(UTC),
            "decided": False,
            "flagged_rows": [],
            "missed_decision": False,
        }
    )


def clear_sessions() -> None:
    """Forget every chat session (used by the demo reset)."""
    _sessions.clear()


def get_or_create_session(
    session_id: str,
    case: dict[str, Any],
    mode: str,
    user_id: str = "u_aina",
    scenario: str = "assistive",
) -> dict[str, Any]:
    case_id = case["id"]
    if session_id not in _sessions:
        _sessions[session_id] = {
            "user_id": user_id,
            "scenario": scenario,
            "messages": [],
            "current_case_id": None,
            # per-case fields (populated by _reset_case_state below):
            "case": case,
            "mode": mode,
            "help_level": 0,
            "help_steps": [],
            "checks_used": [],
            "start_time": datetime.now(UTC),
            "decided": False,
            "flagged_rows": [],
            "missed_decision": False,
        }
    session = _sessions[session_id]
    # Reset per-case state whenever the user opens a different case, or starts a new attempt on
    # a case already decided (otherwise the old help level would leak into the new attempt).
    if session["current_case_id"] != case_id or session["decided"]:
        _reset_case_state(session, case, mode)
    # Check-in is always independent — help is never allowed.
    if mode == "checkin":
        session["help_level"] = 0
    return session


def _call_tool(name: str, args: dict[str, Any], case: dict[str, Any]) -> Any:
    if name == "recompute_totals":
        return recompute_totals(case)
    if name == "match_entries":
        return match_entries(case, args.get("tolerance", 0.01))
    if name == "list_adjustments":
        return list_adjustments(case)
    if name == "find_document":
        return find_document(case, args.get("doc_ref", ""))
    if name == "compare_amounts":
        return compare_amounts(args.get("a", 0), args.get("b", 0))
    if name == "get_section":
        return get_section(case, args.get("section", "ledger"))
    return {"error": f"Unknown tool: {name}"}


def _build_system_prompt(session: dict[str, Any], playbook: str) -> str:
    case_no_gt = {k: v for k, v in session["case"].items() if k != "ground_truth"}
    mode = session["mode"]
    hl = session["help_level"]

    reveal_rules = {
        0: (
            "You may ONLY answer clarifying questions about the process. Do NOT reveal any "
            "issues, rows, or amounts that suggest a problem."
        ),
        1: (
            "You may ask ONE leading question (e.g. 'What would make this total change?'). "
            "Do NOT identify the specific issue or rows."
        ),
        2: (
            "You may give a HINT pointing to a specific area (e.g. 'Look closely at the "
            "adjustments'). Do NOT name specific row IDs or the exact error."
        ),
        3: (
            "You may EXPLAIN the concept behind the issue (e.g. 'A transposition error means "
            "digits are swapped'). Do NOT give the specific row ID or exact amount."
        ),
        4: (
            "You may show the SPECIFIC ANSWER including exact row IDs, amounts, and what the "
            "correct value should be."
        ),
    }

    checkin_note = (
        "\n\nCHECK-IN MODE: Independent assessment. NEVER offer hints, questions, or "
        "explanations about the case."
        if mode == "checkin"
        else ""
    )
    missed_note = (
        "\n\nThe employee just submitted an incorrect decision. Walk them back through the "
        "case step by step, starting with the most obvious clue."
        if session.get("missed_decision")
        else ""
    )

    return (
        "You are a finance companion helping an employee review an AI-prepared bank "
        "reconciliation.\n\n"
        f"PLAYBOOK:\n{playbook}\n\n"
        f"CASE:\n{json.dumps(case_no_gt, indent=2)}\n\n"
        f"CURRENT HELP LEVEL: {hl} ({HELP_LEVEL_NAMES[hl]})\n"
        f"REVEAL RULE: {reveal_rules[hl]}{checkin_note}{missed_note}\n\n"
        "RULES:\n"
        "- Only cite row IDs and amounts that actually exist in the case above.\n"
        "- Never claim certainty you don't have.\n"
        "- Keep responses to 1-3 sentences.\n"
        "- Use tools to check facts before stating them.\n"
        "- The employee must make the final decision. Never decide for them.\n"
    )


def _extract_ui_actions(tool_name: str, result: Any, help_level: int) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if tool_name == "recompute_totals":
        summary = (
            f"Ledger {result.get('ledger_total')} vs Bank {result.get('bank_total')}"
            f" → difference {result.get('difference')}"
        )
        actions.append({"type": "show_check", "check": "recompute_totals", "result": summary})
    elif tool_name == "match_entries":
        unmatched = result.get("unmatched_ledger", []) + result.get("unmatched_bank", [])
        summary = (
            f"{len(result.get('matched', []))} matched, "
            f"{len(result.get('unmatched_ledger', []))} unmatched ledger, "
            f"{len(result.get('unmatched_bank', []))} unmatched bank"
        )
        actions.append({"type": "show_check", "check": "match_entries", "result": summary})
        if help_level >= 2 and unmatched:
            actions.append({"type": "highlight_rows", "rows": [r["row_id"] for r in unmatched]})
    elif tool_name == "find_document" and "error" not in result and help_level >= 2:
        actions.append({"type": "open_document", "doc_ref": result.get("doc_ref", "")})
    return actions


def _validate_reply(reply: str, case: dict[str, Any]) -> bool:
    """Return False if the reply mentions a row ID that doesn't exist in the case."""
    all_ids: set[str] = set()
    for row in case.get("ledger", []):
        all_ids.add(row["row_id"])
    for row in case.get("bank", []):
        all_ids.add(row["row_id"])
    for adj in case.get("ai_output", {}).get("proposed_adjustments", []):
        all_ids.add(adj["id"])
    mentioned = re.findall(r"\b[LBADadj]+\d+\b", reply)
    return all(m in all_ids for m in mentioned)


def _mock_reply(session: dict[str, Any]) -> dict[str, Any]:
    """Deterministic reply used when no LLM key is configured."""
    hl = session["help_level"]
    case = session["case"]
    mode = session["mode"]

    if mode == "checkin":
        return {
            "reply": "This is a check-in case. Review the reconciliation and submit your decision.",
            "help_level": 0,
            "ui_actions": [],
            "trace": ["check-in mode – no hints available"],
        }

    totals = recompute_totals(case)
    ui_actions: list[dict[str, Any]] = [
        {
            "type": "show_check",
            "check": "recompute_totals",
            "result": (
                f"Ledger {totals['ledger_total']} vs Bank {totals['bank_total']}"
                f" → difference {totals['difference']}"
            ),
        }
    ]
    trace = ["checking totals"]

    # Built only from tool results on this case (never ground_truth), so it fits every case.
    matches = match_entries(case)
    unmatched = [str(r["row_id"]) for r in matches["unmatched_ledger"] + matches["unmatched_bank"]]
    adjustments = [str(a["id"]) for a in list_adjustments(case)]
    replies = {
        0: "I'm here if you need help. Take your time reviewing the reconciliation.",
        1: (
            "What would make the totals differ? Does every row have a partner on the other side, "
            "and does every adjustment have a supporting document?"
        ),
        2: "Look closely at the rows that do not match and at the proposed adjustments.",
        3: (
            "Unmatched rows can mean a typo (e.g. digits swapped), a timing difference or a "
            "duplicate; an adjustment without a document should be challenged, not accepted."
        ),
        4: (
            f"The checks show unmatched rows: {', '.join(unmatched) or 'none'}; proposed "
            f"adjustments: {', '.join(adjustments) or 'none'}. Compare each one with its "
            "document before you decide."
        ),
    }

    if hl >= 2:
        trace.append("matching entries")
        if unmatched:
            ui_actions.append({"type": "highlight_rows", "rows": unmatched})
        doc_refs = [str(r["doc_ref"]) for r in case.get("ledger", []) if r.get("doc_ref")]
        unmatched_docs = [
            str(r["doc_ref"])
            for r in case.get("ledger", [])
            if r.get("doc_ref") and str(r["row_id"]) in unmatched
        ]
        doc = next(iter(unmatched_docs or doc_refs), None)
        if doc:
            ui_actions.append({"type": "open_document", "doc_ref": doc})
            trace.append(f"checking document {doc}")

    return {
        "reply": replies.get(hl, replies[0]),
        "help_level": hl,
        "ui_actions": ui_actions,
        "trace": trace,
    }


def process_message(
    session_id: str,
    user_message: str,
    case: dict[str, Any],
    mode: str,
    user_id: str = "u_aina",
    scenario: str = "assistive",
    playbook: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Process a user message and return a companion response."""
    session = get_or_create_session(session_id, case, mode, user_id, scenario)

    # Advance help level when user says they're stuck (not in checkin mode)
    if "stuck" in user_message.lower() and mode != "checkin":
        new_level = min(session["help_level"] + 1, 4)
        if new_level != session["help_level"]:
            session["help_level"] = new_level
            step_name = HELP_STEP_NAMES.get(new_level, "")
            if step_name and step_name not in session["help_steps"]:
                session["help_steps"].append(step_name)

    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        result = _mock_reply(session)
        session["messages"].append({"role": "user", "content": user_message})
        session["messages"].append({"role": "assistant", "content": result["reply"]})
        for action in result.get("ui_actions", []):
            check = action.get("check")
            if check and check not in session["checks_used"]:
                session["checks_used"].append(check)
        return result

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        playbook_text = playbook[1] if playbook else read_playbook(BASE_VERSION)
        system_prompt = _build_system_prompt(session, playbook_text)

        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(session["messages"])
        messages.append({"role": "user", "content": user_message})

        ui_actions: list[dict[str, Any]] = []
        trace: list[str] = []

        for _ in range(6):
            response = client.chat.completions.create(  # type: ignore[call-overload]
                model=model,
                messages=messages,
                tools=_TOOLS,
                tool_choice="auto",
                max_tokens=600,
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg.model_dump(exclude_none=True))
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments or "{}")
                    tool_result = _call_tool(name, args, session["case"])
                    trace.append(name)
                    if name not in session["checks_used"]:
                        session["checks_used"].append(name)
                    ui_actions.extend(_extract_ui_actions(name, tool_result, session["help_level"]))
                    messages.append(
                        {"role": "tool", "tool_call_id": tc.id, "content": json.dumps(tool_result)}
                    )
            else:
                reply = msg.content or ""
                if not _validate_reply(reply, session["case"]):
                    messages.append(
                        {
                            "role": "user",
                            "content": "Only reference row IDs that exist in the case.",
                        }
                    )
                    continue

                session["messages"].append({"role": "user", "content": user_message})
                session["messages"].append({"role": "assistant", "content": reply})

                # Pop-in if the AI claim says "reconciles" and user hasn't decided yet
                ai_claim = session["case"].get("ai_output", {}).get("claim", "")
                if "reconciles" in ai_claim.lower() and not session["decided"]:
                    pop_in = {
                        "type": "pop_in",
                        "message": "Want a second look before you sign off?",
                    }
                    ui_actions.insert(0, pop_in)

                return {
                    "reply": reply,
                    "help_level": session["help_level"],
                    "ui_actions": ui_actions,
                    "trace": trace,
                }

        return {
            "reply": "I had trouble processing that. Please try again.",
            "help_level": session["help_level"],
            "ui_actions": [],
            "trace": [],
        }
    except Exception:  # noqa: BLE001
        return _mock_reply(session)


def process_decision(
    session_id: str,
    decision: str,
    flagged_rows: list[str],
    case: dict[str, Any],
    mode: str,
    user_id: str = "u_aina",
    scenario: str = "assistive",
    self_confidence_before: float | None = None,
    playbook_version: str = BASE_VERSION,
) -> dict[str, Any]:
    """Grade a decision and return an Event plus grader metadata.

    Practice mode wrong decision: event is None — don't post yet; session stays open.
    Practice mode correct after a prior miss: ONE event with outcome='missed_then_found'.
    All other decisions: event is built immediately.
    """
    from src.companion.grader import grade  # local import to avoid circular

    session = get_or_create_session(session_id, case, mode, user_id, scenario)
    session["flagged_rows"] = flagged_rows or []

    grader_result = grade(case, decision, flagged_rows)

    # Enrich help_level on skills_evidence from actual session state
    for se in grader_result["skills_evidence"]:
        se["help_level"] = session["help_level"]

    duration_sec = int((datetime.now(UTC) - session["start_time"]).total_seconds())

    # Practice wrong decision: hold the event, keep session open for remediation.
    # event=None signals the API layer to skip posting.
    # Nothing from ground_truth is returned here: the user keeps working through the help ladder,
    # and the help level recorded when they find it must be the real amount of help they had.
    if not grader_result["decision_correct"] and mode == "practice":
        session["missed_decision"] = True
        return {
            "event": None,
            "decision_correct": False,
            "explanation": WALK_BACK_MESSAGE,
            "affected_rows": [],
            "correct_decision": None,
            "missed_and_walking_back": True,
        }

    # If the user previously missed and now found it, upgrade the outcome for all skills.
    if grader_result["decision_correct"] and session.get("missed_decision"):
        for se in grader_result["skills_evidence"]:
            se["outcome"] = "missed_then_found"
        session["missed_decision"] = False

    session["decided"] = True

    event: dict[str, Any] = {
        "id": f"ev_{uuid.uuid4().hex[:8]}",
        "user_id": user_id,
        "case_id": case["id"],
        "mode": mode,
        "scenario": scenario,
        "timestamp": datetime.now(UTC).isoformat(),
        "self_confidence_before": self_confidence_before,
        "help_level_max": session["help_level"],
        "help_steps": session["help_steps"],
        "checks_used": session["checks_used"],
        "user_decision": decision,
        "decision_correct": grader_result["decision_correct"],
        "issue_found_by": grader_result["issue_found_by"],
        "skills_evidence": grader_result["skills_evidence"],
        "cause_if_wrong": None,
        "companion_version": playbook_version,
        "duration_sec": duration_sec,
        "difficulty": case.get("difficulty", 1),
        "session_id": session_id,
        "flags": {"companion_error": False, "ambiguous_case": False, "data_issue": False},
    }

    return {
        "event": event,
        "decision_correct": grader_result["decision_correct"],
        "explanation": grader_result["explanation"],
        "affected_rows": grader_result["affected_rows"],
        "correct_decision": grader_result["correct_decision"],
        "missed_and_walking_back": False,
    }
