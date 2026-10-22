"""One optimiser run, from the active playbook to a stored OptimizerProposal.

Order (PERSON_A Task A9): optimise on the development set (src/optimizer/loop.py) → freeze the
candidate and save it as the next playbook version (not active) → if it improved on the
development set, score current and candidate on the acceptance set once (eval/gate.py) →
proposal with status "pending" for a senior to approve or reject. Without a gain the proposal is
stored as "rejected" by the optimiser itself and the acceptance set is not touched: a rejection is
a valid result and is shown, not hidden. Approving activates the candidate; rollback_to names the
version to return to.
"""

import difflib
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from eval.acceptance_criteria import criteria_hash
from eval.gate import GateResult, run_gate
from src.companion.playbook_versions import active_playbook, next_version, save_version
from src.contract import AcceptanceResult, OptimizerProposal, SetResult
from src.optimizer.loop import ROUNDS, LoopResult, development_set, optimise
from src.store import Store

NOT_RUN = "not run (no gain on the development set)"
AUTO_REJECTED_BY = "optimiser (automatic: no gain on the development set)"

Gate = Callable[[str, str], GateResult]


class NothingToProposeError(RuntimeError):
    """The loop produced no revision (no failures, or every revision was unusable)."""


def unified_diff(before: str, after: str, from_name: str, to_name: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=from_name,
        tofile=to_name,
    )
    return "".join(lines)


def build_proposal(
    base_version: str,
    candidate_version: str,
    loop: LoopResult,
    gate: GateResult | None,
) -> tuple[OptimizerProposal, str]:
    """The proposal and the candidate text it refers to."""
    if loop.improved:
        text, score, rationale = loop.best_text, loop.best_score, loop.rationale
    elif loop.tried is not None:
        text, score, rationale = loop.tried
    else:
        raise NothingToProposeError("; ".join(loop.log))
    if gate is not None:
        acceptance, regressions = gate.acceptance, gate.regressions
        status, decided_by, decided_at = "pending", None, None
    else:
        acceptance = AcceptanceResult(
            before=NOT_RUN,
            after=NOT_RUN,
            criteria_hash=criteria_hash(),
            false_alarms_clean=SetResult(before=NOT_RUN, after=NOT_RUN),
            invalid_citations=0,
        )
        regressions = []
        status, decided_by = "rejected", AUTO_REJECTED_BY
        decided_at = datetime.now(UTC).isoformat(timespec="seconds")
    proposal = OptimizerProposal(
        id=f"prop_{uuid.uuid4().hex[:8]}",
        editable_scope="playbook",
        base_version=base_version,
        candidate_version=candidate_version,
        diff=unified_diff(loop.base_text, text, base_version, candidate_version),
        optimisation_set=SetResult(before=loop.base_score.summary(), after=score.summary()),
        acceptance_set=acceptance,
        regressions=regressions,
        status=status,
        decided_by=decided_by,
        decided_at=decided_at,
        rollback_to=base_version,
        rationale=rationale,
        development_log=loop.log,
    )
    return proposal, text


def run_optimizer(
    store: Store,
    rounds: int = ROUNDS,
    loop_fn: Callable[..., LoopResult] = optimise,
    gate_fn: Gate = run_gate,
    progress: Callable[[str], None] = lambda _: None,
) -> OptimizerProposal:
    base_version, base_text = active_playbook(store)
    loop = loop_fn(base_text, development_set(), rounds=rounds, progress=progress)
    gate = None
    if loop.improved:
        progress("candidate frozen; scoring current and candidate on the acceptance set (once)")
        gate = gate_fn(base_text, loop.best_text)
    candidate_version = next_version(store)
    proposal, text = build_proposal(base_version, candidate_version, loop, gate)
    save_version(store, candidate_version, text)
    store.put_proposal(proposal)
    progress(f"proposal {proposal.id} stored ({proposal.status})")
    return proposal
