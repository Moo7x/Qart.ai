"""Optimiser routes (src/api_optimizer.py): run, proposals, senior decision, rollback.

A senior (synthetic role in the demo) starts a run, reads the proposal (diff, development-set and
acceptance counts, regressions, rationale) and approves or rejects it. Approving activates the
candidate playbook for the companion; rollback returns to the version the proposal was based on.
The optimiser never activates anything by itself.
"""

import os
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api_engine import StoreDep
from src.companion.playbook_versions import active_playbook, known_versions, set_active
from src.contract import OptimizerProposal
from src.optimizer.jobs import JOB, OptimizerStatus
from src.optimizer.pipeline import run_optimizer

router = APIRouter(prefix="/api/optimizer", tags=["optimizer"])


class ProposalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    decided_by: str


class PlaybookInfo(BaseModel):
    active_version: str
    text: str
    versions: list[str]


def _playbook_info(store: StoreDep) -> PlaybookInfo:
    version, text = active_playbook(store)
    return PlaybookInfo(active_version=version, text=text, versions=known_versions(store))


def _proposal(store: StoreDep, proposal_id: str) -> OptimizerProposal:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"unknown proposal {proposal_id}")
    return proposal


@router.get("/proposals")
def get_proposals(store: StoreDep) -> list[OptimizerProposal]:
    """Every proposal, pending or decided; empty until the optimiser has run."""
    return store.list_proposals()


@router.post("/proposals/{proposal_id}/decision")
def decide_proposal(
    proposal_id: str, decision: ProposalDecision, store: StoreDep
) -> OptimizerProposal:
    proposal = _proposal(store, proposal_id)
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail=f"proposal already {proposal.status}")
    approved = decision.decision == "approve"
    if approved:
        set_active(store, proposal.candidate_version)
    decided = proposal.model_copy(
        update={
            "status": "approved" if approved else "rejected",
            "decided_by": decision.decided_by,
            "decided_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    )
    store.put_proposal(decided)
    return decided


@router.post("/proposals/{proposal_id}/rollback")
def rollback(proposal_id: str, store: StoreDep) -> PlaybookInfo:
    """Return to the version this approved proposal replaced."""
    proposal = _proposal(store, proposal_id)
    if proposal.status != "approved" or active_playbook(store)[0] != proposal.candidate_version:
        raise HTTPException(status_code=409, detail="only the active, approved version rolls back")
    set_active(store, proposal.rollback_to)
    return _playbook_info(store)


@router.get("/playbook")
def get_playbook(store: StoreDep) -> PlaybookInfo:
    return _playbook_info(store)


@router.post("/run")
def start_run(store: StoreDep) -> OptimizerStatus:
    if not os.getenv("LLM_API_KEY"):
        raise HTTPException(status_code=409, detail="the optimiser needs LLM_API_KEY")
    if not JOB.start(store, run_optimizer):
        raise HTTPException(status_code=409, detail="an optimiser run is already in progress")
    return JOB.status


@router.get("/status")
def run_status() -> OptimizerStatus:
    return JOB.status
