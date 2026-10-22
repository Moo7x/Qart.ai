"""Playbook optimiser: improvement rule, loop, pipeline and approval routes (no LLM calls)."""

import ast
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eval.gate import GateResult
from src.api_engine import get_store
from src.companion import playbook_versions as pv
from src.contract import AcceptanceResult, SetResult
from src.optimizer import loop as loop_module
from src.optimizer.loop import LoopResult, SetScore, better, development_set, optimise
from src.optimizer.pipeline import AUTO_REJECTED_BY, run_optimizer
from src.store import Store

FIX = "Decide by what the evidence shows; escalate only what you cannot resolve."
V1 = (pv.PLAYBOOK_DIR / "playbook_v1.md").read_text(encoding="utf-8")


def fake_diagnose(case: dict[str, Any], playbook: str) -> dict[str, Any]:
    """Escalates everything under the old text; follows the truth once FIX is in the playbook."""
    truth = case["ground_truth"]
    if FIX in playbook:
        return {
            "has_issue": truth["has_issue"],
            "issue_types": truth["issue_types"],
            "affected_rows": truth["affected_rows"],
            "decision": truth["correct_decision"],
        }
    return {"has_issue": True, "issue_types": [], "affected_rows": [], "decision": "escalate"}


def fixing_proposer(playbook: str, failures: list[dict[str, Any]]) -> tuple[str, str]:
    return playbook + "\n" + FIX, f"fixed {len(failures)} failures"


def useless_proposer(playbook: str, failures: list[dict[str, Any]]) -> tuple[str, str]:
    return playbook + "\nBe careful.", "added a reminder"


@pytest.fixture
def playbook_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "playbooks"
    directory.mkdir()
    (directory / "playbook_v1.md").write_text(
        (pv.PLAYBOOK_DIR / "playbook_v1.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(pv, "PLAYBOOK_DIR", directory)
    return directory


def test_better_needs_higher_utility_and_no_new_false_alarms() -> None:
    base = SetScore(10, 2, 4, 4, 1, 0)
    assert better(SetScore(10, 2, 6, 5, 1, 0), base)
    assert not better(SetScore(10, 2, 9, 9, 2, 0), base)  # more false alarms is never better
    assert not better(base, base)


def test_development_set_is_practice_cases_and_their_variants_only() -> None:
    cases = development_set()
    ids = [c["id"] for c in cases]
    assert len(cases) == 17 and len(set(ids)) == 17
    assert not any(i.startswith(("a0", "a1", "c0", "h0")) for i in ids)  # acceptance / holdout ids


def test_the_loop_cannot_reach_the_acceptance_or_holdout_sets() -> None:
    source = Path(loop_module.__file__).read_text(encoding="utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported & {"eval.gate", "eval.runner"}
    assert '"acceptance"' not in source and "holdout" not in source.replace("holdout/", "")


def test_optimise_keeps_a_better_revision_and_reports_it() -> None:
    cases = development_set()
    result = optimise(V1, cases, rounds=2, diagnose=fake_diagnose, propose=fixing_proposer)
    assert result.improved and FIX in result.best_text
    assert result.best_score.decision == len(cases) > result.base_score.decision
    assert "kept" in result.log[1]


def test_optimise_discards_a_revision_that_is_not_better() -> None:
    cases = development_set()
    result = optimise(V1, cases, rounds=1, diagnose=fake_diagnose, propose=useless_proposer)
    assert not result.improved and result.best_text == V1
    assert result.tried is not None and "Be careful." in result.tried[0]


def fake_gate(base: str, candidate: str) -> GateResult:
    score = SetScore(17, 5, 10, 9, 1, 0)
    acceptance = AcceptanceResult(
        before="b",
        after="a",
        criteria_hash="sha256:x",
        false_alarms_clean=SetResult(before="2/5", after="1/5"),
        invalid_citations=0,
    )
    return GateResult(acceptance, ["a003"], score, score)


def run_with(store: Store, propose: Any, gate_calls: list[str]) -> Any:
    def loop_fn(base_text: str, cases: Any, rounds: int, progress: Any) -> LoopResult:
        return optimise(base_text, cases, rounds, fake_diagnose, propose, progress)

    def gate(base: str, candidate: str) -> GateResult:
        gate_calls.append(candidate)
        return fake_gate(base, candidate)

    return run_optimizer(store, rounds=1, loop_fn=loop_fn, gate_fn=gate)


def test_an_improvement_becomes_a_pending_proposal_and_is_not_active(
    tmp_path: Path, playbook_dir: Path
) -> None:
    store = Store(tmp_path / "s.sqlite")
    gate_calls: list[str] = []
    proposal = run_with(store, fixing_proposer, gate_calls)
    assert proposal.status == "pending" and proposal.candidate_version == "playbook_v2"
    assert proposal.regressions == ["a003"] and len(gate_calls) == 1
    assert FIX in proposal.diff and proposal.rollback_to == "playbook_v1"
    assert pv.active_playbook(store)[0] == "playbook_v1"  # nothing activates without a senior
    assert FIX in pv.read_playbook("playbook_v2", store)


def test_no_gain_is_rejected_automatically_without_touching_acceptance(
    tmp_path: Path, playbook_dir: Path
) -> None:
    store = Store(tmp_path / "s.sqlite")
    gate_calls: list[str] = []
    proposal = run_with(store, useless_proposer, gate_calls)
    assert proposal.status == "rejected" and proposal.decided_by == AUTO_REJECTED_BY
    assert gate_calls == [] and "not run" in proposal.acceptance_set.after


def test_senior_approval_activates_and_rollback_restores(
    client: TestClient, playbook_dir: Path
) -> None:
    store = client.app.dependency_overrides[get_store]()  # type: ignore[attr-defined]
    proposal = run_with(store, fixing_proposer, [])
    decide = f"/api/optimizer/proposals/{proposal.id}/decision"
    approved = client.post(decide, json={"decision": "approve", "decided_by": "senior (synthetic)"})
    assert approved.json()["status"] == "approved"
    assert client.get("/api/optimizer/playbook").json()["active_version"] == "playbook_v2"
    assert client.post(decide, json={"decision": "reject", "decided_by": "x"}).status_code == 409
    rolled = client.post(f"/api/optimizer/proposals/{proposal.id}/rollback").json()
    assert rolled["active_version"] == "playbook_v1"


def test_a_run_needs_an_llm_key(client: TestClient) -> None:
    assert client.post("/api/optimizer/run").status_code == 409
    assert client.get("/api/optimizer/status").json()["state"] == "idle"
