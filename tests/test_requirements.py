"""Requirement card and the scenario shift rule (Task A2b)."""

import pytest

from src.contract import (
    CardWeight,
    CompanyAssumptions,
    OnetBasis,
    Role,
    RoleSkill,
    RoleTask,
    Scenario,
    SkillType,
)
from src.engine import params
from src.engine.catalogue import default_catalogue
from src.engine.requirements import requirement_card, role_outlook, scenario_weights

URL = "https://www.onetonline.org/link/summary/43-3031.00"


def tiny_role() -> Role:
    """Execution skill A (0.6) used by one task; oversight skill B (0.4) used by none."""
    return Role(
        id="tiny",
        title="Tiny",
        internal=True,
        based_on=[OnetBasis(source="O*NET 31.0", code="43-3031.00", title="Clerks", url=URL)],
        skills=[RoleSkill(skill_id="A", base_weight=0.6), RoleSkill(skill_id="B", base_weight=0.4)],
        sdg_targets=["4.4"],
        summary="test role",
        tasks=[
            RoleTask(
                task="t", onet="43-3031.00", workflow_task="match", skills=["A"], source_url=URL
            )
        ],
    )


TINY_TYPES: dict[str, SkillType] = {"A": "execution", "B": "oversight"}


def tiny_assumptions(allocation: str) -> CompanyAssumptions:
    return CompanyAssumptions.model_validate(
        {
            "version": 1,
            "updated_by": "test",
            "scenarios": {
                "assistive": {"tasks": {"match": allocation}},
                "agentic": {"tasks": {"match": allocation}},
            },
            "shift_rule": "test rule",
            "shift_fractions": {"assistive": 0.5, "agentic": 0.8},
        }
    )


def skill_types() -> dict[str, SkillType]:
    return {k: s.type for k, s in default_catalogue().skills.items()}


def test_shift_rule_worked_example_assistive() -> None:
    weights = scenario_weights(tiny_role(), "assistive", tiny_assumptions("ai"), TINY_TYPES)
    # A loses 50% of 0.6 = 0.3, which moves to the only oversight skill B: 0.4 + 0.3.
    assert weights.scenario == pytest.approx({"A": 0.3, "B": 0.7})


def test_shift_rule_worked_example_agentic() -> None:
    weights = scenario_weights(
        tiny_role(), "agentic", tiny_assumptions("ai_drafts_human_reviews"), TINY_TYPES
    )
    assert weights.scenario == pytest.approx({"A": 0.12, "B": 0.88})


def test_human_allocation_keeps_base_weights() -> None:
    weights = scenario_weights(tiny_role(), "agentic", tiny_assumptions("human"), TINY_TYPES)
    assert weights.scenario == pytest.approx(weights.base)


@pytest.mark.parametrize("scenario", ["assistive", "agentic"])
def test_weights_sum_to_one_for_every_role(scenario: Scenario) -> None:
    cat = default_catalogue()
    for role in cat.roles.values():
        weights = scenario_weights(role, scenario, cat.assumptions_v1, skill_types())
        assert sum(weights.scenario.values()) == pytest.approx(1.0)
        assert all(w >= 0 for w in weights.scenario.values())


def test_agentic_moves_weight_from_execution_to_oversight() -> None:
    cat = default_catalogue()
    role = cat.roles["ai_finops_analyst"]
    assistive = scenario_weights(role, "assistive", cat.assumptions_v1, skill_types()).scenario
    agentic = scenario_weights(role, "agentic", cat.assumptions_v1, skill_types()).scenario
    assert agentic["ai_output_review"] > assistive["ai_output_review"]
    assert agentic["recon_to_source"] < assistive["recon_to_source"]


def test_changing_one_allocation_changes_weights_and_card_explains_it() -> None:
    cat = default_catalogue()
    role = cat.roles["recon_associate"]
    v1 = cat.assumptions_v1
    v2 = v1.model_copy(deep=True)
    v2.version = 2
    v2.scenarios["assistive"].tasks["check_entries"] = "ai_drafts_human_reviews"

    before = requirement_card(role, "assistive", v1, skill_types())
    after = requirement_card(role, "assistive", v2, skill_types())
    again = requirement_card(role, "assistive", v2, skill_types())

    def weight(card_weights: list[CardWeight], skill_id: str) -> float:
        return next(w.scenario for w in card_weights if w.skill_id == skill_id)

    assert weight(after.weights, "transposition_check") < weight(
        before.weights, "transposition_check"
    )
    assert weight(after.weights, "escalation_judgment") > weight(
        before.weights, "escalation_judgment"
    )
    assert after == again  # deterministic
    because = next(w.because for w in after.weights if w.skill_id == "transposition_check")
    assert "Check postings for keying and arithmetic errors" in because
    assert "assumption v2" in because
    task = next(t for t in after.tasks if t.workflow_task == "check_entries")
    assert task.allocation == "ai_drafts_human_reviews"


def test_card_lists_onet_tasks_and_assumption_text() -> None:
    cat = default_catalogue()
    role = cat.roles["ai_finops_analyst"]
    card = requirement_card(role, "agentic", cat.assumptions_v1, skill_types())
    assert [t.task for t in card.tasks] == [t.task for t in role.tasks]
    assert {t.onet for t in card.tasks} <= {b.code for b in role.based_on}
    assert card.assumption is not None and "v1" in card.assumption
    assert card.evidence == []  # no snapshot given: no external evidence claimed
    assert all(w.because for w in card.weights)


# --- role outlook (item: "predict which jobs emerge or decline") ----------------------------
def test_agentic_recon_associate_has_higher_ai_handled_share_than_assistive() -> None:
    cat = default_catalogue()
    role = cat.roles["recon_associate"]
    assistive = role_outlook(role, "assistive", cat.assumptions_v1, skill_types())
    agentic = role_outlook(role, "agentic", cat.assumptions_v1, skill_types())
    assert agentic.ai_handled_share > assistive.ai_handled_share
    assert agentic.label == "being transformed"
    assert "not a headcount forecast" in agentic.basis


def test_outlook_labels_follow_documented_thresholds() -> None:
    cat = default_catalogue()
    for role in cat.roles.values():
        for scenario in ("assistive", "agentic"):
            outlook = role_outlook(role, scenario, cat.assumptions_v1, skill_types())
            assert 0.0 <= outlook.ai_handled_share <= 1.0
            assert 0.0 <= outlook.oversight_share <= 1.0
            if outlook.ai_handled_share >= params.OUTLOOK_TRANSFORMED_AI_SHARE:
                assert outlook.label == "being transformed"
            elif outlook.oversight_share >= params.OUTLOOK_AI_ERA_OVERSIGHT_SHARE:
                assert outlook.label == "AI-era role"
            else:
                assert outlook.label == "stable"


def test_all_human_allocation_gives_zero_ai_share() -> None:
    outlook = role_outlook(tiny_role(), "agentic", tiny_assumptions("human"), TINY_TYPES)
    assert outlook.ai_handled_share == 0.0


def test_v2_approval_changes_recon_associate_assistive_outlook() -> None:
    cat = default_catalogue()
    role = cat.roles["recon_associate"]
    v2 = cat.assumptions_v1.model_copy(deep=True)
    v2.version = 2
    v2.scenarios["assistive"].tasks["check_entries"] = "ai_drafts_human_reviews"
    before = role_outlook(role, "assistive", cat.assumptions_v1, skill_types())
    after = role_outlook(role, "assistive", v2, skill_types())
    assert after.ai_handled_share > before.ai_handled_share
    assert (before.label, after.label) == ("stable", "being transformed")
    assert "check_entries" in after.because and "assumption v2" in after.because
    card = requirement_card(role, "assistive", v2, skill_types())
    assert card.outlook == after
