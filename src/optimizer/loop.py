"""Reflective playbook optimiser (PERSON_A Task A9): the part that writes candidates.

Editable scope: the playbook text only. Everything it learns from comes from the DEVELOPMENT set:
the practice cases in cases/ plus perturbed variants of them (eval/variants.py). It never opens
eval/acceptance/ or eval/holdout/, and it does not change the grading criteria (it only calls
eval.acceptance_criteria.grade, the same fixed function the evaluator uses).

One round:
1. diagnose every development case with the current playbook (the companion's automatic
   diagnosis, LLM path) and grade it;
2. give the model the playbook and the failures (what was decided vs what was right, and why);
3. it returns a revised playbook and a rationale (strict JSON schema);
4. the revision is graded on the same set and kept only if it is better (rule below).
The best text after ROUNDS rounds is the candidate. Scoring on the acceptance set happens after
the candidate is frozen, in eval/gate.py, so acceptance results cannot shape the text.
"""

import json
import os
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eval.acceptance_criteria import CaseResult, grade
from eval.variants import make_variants
from src.companion.auto import DEFAULT_BASE_URL, Diagnosis, diagnose_with_playbook, llm_model

CASES_DIR = Path(__file__).resolve().parent.parent.parent / "cases"
INDEX_FILE = "index.json"
# DECLARED: variants per practice case (5 practice + 2 check-in cases → 7 + 2×5 = 17 cases).
VARIANTS_PER_CASE = 2
# DECLARED: revision rounds per run (each round = 1 proposal call + one pass over the set).
ROUNDS = 3
# DECLARED: parallel diagnosis calls (keeps a pass under a minute without hitting rate limits).
WORKERS = 4
# DECLARED: weights of the improvement rule. Decisions and root causes count once; a false alarm
# on a clean case costs 2 (it wastes reviewer time and erodes trust, the problem v1 showed); an
# invalid citation costs 1. A candidate must beat the current text on this utility AND must not
# add false alarms.
FALSE_ALARM_COST = 2
INVALID_CITATION_COST = 1
MAX_PLAYBOOK_GROWTH = 2.0  # a revision may at most double the text (keeps it a readable procedure)
PROPOSAL_MAX_TOKENS = 2500
PROPOSAL_TEMPERATURE = 0.4  # variety between rounds (first live run: revisions were near copies)

Diagnose = Callable[[dict[str, Any], str], Diagnosis]
Propose = Callable[[str, list[dict[str, Any]]], tuple[str, str]]


@dataclass(frozen=True)
class SetScore:
    cases: int
    clean: int
    decision: int
    root_cause: int
    false_alarms: int
    invalid_citations: int

    @property
    def utility(self) -> int:
        return (
            self.decision
            + self.root_cause
            - FALSE_ALARM_COST * self.false_alarms
            - INVALID_CITATION_COST * self.invalid_citations
        )

    def summary(self) -> str:
        return (
            f"decisions {self.decision}/{self.cases} · root cause {self.root_cause}/{self.cases} · "
            f"false alarms {self.false_alarms}/{self.clean} · invalid citations "
            f"{self.invalid_citations}"
        )


def better(candidate: SetScore, current: SetScore) -> bool:
    return candidate.utility > current.utility and candidate.false_alarms <= current.false_alarms


@dataclass
class LoopResult:
    base_text: str
    base_score: SetScore
    best_text: str
    best_score: SetScore
    rationale: str
    improved: bool
    log: list[str] = field(default_factory=list)
    # The last revision tried, kept or not, so a run without gain can still be shown and rejected.
    tried: tuple[str, SetScore, str] | None = None


def development_set(cases_dir: Path = CASES_DIR) -> list[dict[str, Any]]:
    """Practice and check-in cases plus their variants (built in memory, nothing written)."""
    cases = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(cases_dir.glob("*.json"))
        if path.name != INDEX_FILE
    ]
    cases = [c for c in cases if isinstance(c, dict) and "ground_truth" in c]
    return cases + make_variants(cases, VARIANTS_PER_CASE)


def score_results(results: Sequence[CaseResult]) -> SetScore:
    return SetScore(
        cases=len(results),
        clean=sum(r.clean for r in results),
        decision=sum(r.decision_correct for r in results),
        root_cause=sum(r.root_cause_correct for r in results),
        false_alarms=sum(r.false_alarm for r in results),
        invalid_citations=sum(r.invalid_citations for r in results),
    )


def _failure(case: dict[str, Any], diagnosis: Diagnosis, result: CaseResult) -> dict[str, Any]:
    truth = case["ground_truth"]
    return {
        "case": case.get("title", case["id"]),
        "ai_claim": case.get("ai_output", {}).get("claim", ""),
        "decided": diagnosis.get("decision"),
        "found_issue_types": diagnosis.get("issue_types", []),
        "reasoning": diagnosis.get("explanation", ""),
        "right_decision": truth["correct_decision"],
        "right_issue_types": truth["issue_types"],
        "why": truth.get("explanation", ""),
        "false_alarm": result.false_alarm,
    }


def score_playbook(
    playbook: str, cases: Sequence[dict[str, Any]], diagnose: Diagnose = diagnose_with_playbook
) -> tuple[SetScore, list[dict[str, Any]]]:
    """Grade the playbook on the cases; return the score and the failure traces."""
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        diagnoses = list(pool.map(lambda c: diagnose(c, playbook), cases))
    results = [grade(c, d) for c, d in zip(cases, diagnoses, strict=True)]
    failures = [
        _failure(c, d, r)
        for c, d, r in zip(cases, diagnoses, results, strict=True)
        if not (r.decision_correct and r.root_cause_correct) or r.false_alarm
    ]
    return score_results(results), failures


PROPOSER_SYSTEM = (
    "You improve a checking procedure that an AI companion follows when it reviews AI-prepared "
    "bank reconciliations with a finance employee. You get the current procedure and the cases "
    "where following it led to a wrong decision or wrong issue types. Rewrite the procedure so "
    "those mistakes are less likely, while keeping what works. Rules: keep it a general "
    "procedure for any reconciliation (never mention specific case names, row ids, amounts or "
    "documents); keep the step structure and the decision step; be precise about when to sign "
    "off, correct or escalate; keep the existing rules section; plain Markdown."
)


def _proposal_schema() -> dict[str, Any]:
    properties = {"playbook": {"type": "string"}, "rationale": {"type": "string"}}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "playbook_revision",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


def _counts(counter: Counter[str]) -> str:
    return ", ".join(f"{key} ({n})" for key, n in counter.most_common()) or "none"


def failure_pattern(failures: Sequence[dict[str, Any]]) -> str:
    """Counts of the mistakes, so the proposer sees the pattern and not only single cases."""
    decisions = Counter(f"{f['decided']} instead of {f['right_decision']}" for f in failures)
    extra: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    for f in failures:
        extra.update(set(f["found_issue_types"]) - set(f["right_issue_types"]))
        missing.update(set(f["right_issue_types"]) - set(f["found_issue_types"]))
    return (
        f"Decision mistakes: {_counts(decisions)}.\n"
        f"Issue types reported but not present: {_counts(extra)}.\n"
        f"Issue types present but missed: {_counts(missing)}."
    )


def llm_propose(playbook: str, failures: list[dict[str, Any]]) -> tuple[str, str]:
    """One revision from the LLM: (new playbook text, rationale)."""
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"], base_url=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
    )
    user = (
        f"Current procedure:\n\n{playbook}\n\n"
        f"Pattern of the mistakes:\n{failure_pattern(failures)}\n\n"
        "Fix the pattern first: make the decision criteria in the procedure precise enough that "
        "these mistakes stop, without causing the opposite mistake.\n\n"
        f"The cases ({len(failures)}):\n"
        f"{json.dumps(failures, ensure_ascii=False, indent=1)}\n\n"
        "Return the full revised procedure and a short rationale (what you changed and why)."
    )
    response = client.chat.completions.create(  # type: ignore[call-overload]
        model=llm_model(),
        messages=[
            {"role": "system", "content": PROPOSER_SYSTEM},
            {"role": "user", "content": user},
        ],
        response_format=_proposal_schema(),
        temperature=PROPOSAL_TEMPERATURE,
        max_tokens=PROPOSAL_MAX_TOKENS,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return str(data.get("playbook", "")), str(data.get("rationale", ""))


def optimise(
    base_text: str,
    cases: Sequence[dict[str, Any]],
    rounds: int = ROUNDS,
    diagnose: Diagnose = diagnose_with_playbook,
    propose: Propose = llm_propose,
    progress: Callable[[str], None] = lambda _: None,
) -> LoopResult:
    progress(f"scoring the current playbook on {len(cases)} development cases")
    base_score, failures = score_playbook(base_text, cases, diagnose)
    result = LoopResult(base_text, base_score, base_text, base_score, "", False)
    result.log.append(f"current: {base_score.summary()}")
    for round_number in range(1, rounds + 1):
        if not failures:
            result.log.append("no failures left on the development set")
            break
        progress(f"round {round_number}: proposing a revision from {len(failures)} failures")
        text, rationale = propose(result.best_text, failures)
        if not text.strip() or len(text) > MAX_PLAYBOOK_GROWTH * len(base_text):
            result.log.append(f"round {round_number}: revision rejected (empty or too long)")
            continue
        progress(f"round {round_number}: scoring the revision")
        score, new_failures = score_playbook(text, cases, diagnose)
        result.tried = (text, score, rationale)
        verdict = "kept" if better(score, result.best_score) else "not better, discarded"
        result.log.append(f"round {round_number}: {score.summary()} ({verdict})")
        if verdict == "kept":
            result.best_text, result.best_score, result.rationale = text, score, rationale
            result.improved = True
            failures = new_failures
    return result
