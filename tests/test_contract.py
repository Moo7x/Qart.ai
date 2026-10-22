"""Every contract example in schemas/examples/ must validate against src/contract.py."""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from src import contract

EXAMPLES = Path(__file__).resolve().parent.parent / "schemas" / "examples"

MODEL_BY_FILE: dict[str, type[BaseModel]] = {
    "profile.json": contract.Profile,
    "case.json": contract.Case,
    "event.json": contract.Event,
    "skill_state.json": contract.SkillState,
    "role.json": contract.Role,
    "snapshot.json": contract.Snapshot,
    "company_assumptions.json": contract.CompanyAssumptions,
    "recommendation.json": contract.Recommendation,
    "path_plan.json": contract.PathPlan,
    "course.json": contract.Course,
    "optimizer_proposal.json": contract.OptimizerProposal,
}


def test_every_example_file_has_a_model() -> None:
    assert {p.name for p in EXAMPLES.glob("*.json")} == set(MODEL_BY_FILE)


@pytest.mark.parametrize("file_name", sorted(MODEL_BY_FILE))
def test_example_validates(file_name: str) -> None:
    data = json.loads((EXAMPLES / file_name).read_text(encoding="utf-8"))
    MODEL_BY_FILE[file_name].model_validate(data)


def test_rank_change_serialises_with_contract_field_names() -> None:
    change = contract.RankChange.model_validate(
        {"role_id": "r", "from": 3, "to": 1, "because": "x"}
    )
    assert change.model_dump() == {"role_id": "r", "from": 3, "to": 1, "because": "x"}
