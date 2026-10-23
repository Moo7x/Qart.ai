"""Matching rules: fit formula, essentials, scenario shifts and near-ties behave as declared."""

import pytest

from src import params
from src.match.engine import Evidence, rank_roles, scenario_weight, score_role
from src.pack import Requirement, load_pack

# Automation-style shares per SOC as the Economic Index reported them for May 2026 (global).
EVIDENCE = Evidence(
    automation_share={
        "15-2051.01": 66.0,
        "13-2011.00": 45.0,
        "15-1211.00": 84.0,
        "13-2031.00": 34.0,
        "13-1111.00": 45.0,
        "13-1023.00": 66.0,
    },
    automation_period="2026-05",
    automation_source="test",
)
# A synthetic cash application analyst (the "Nur" sample persona).
NUR = {
    "cash_application": 3,
    "reconciliation": 3,
    "credit_collections": 3,
    "erp": 2,
    "reporting": 2,
    "data_validation": 1,
    "accounting_principles": 2,
}


def test_every_destination_role_is_scored_and_none_hidden() -> None:
    ranked = rank_roles(load_pack(), NUR, "moderate", EVIDENCE)
    assert len(ranked) == len(load_pack().destination_roles)
    assert [m.fit for m in ranked] == sorted((m.fit for m in ranked), reverse=True)


def test_fit_is_100_when_every_level_is_met_and_0_when_none_is() -> None:
    pack = load_pack()
    role = pack.destination_roles["cost_accountant"]
    full = {r.skill: 4 for r in role.requires}
    assert score_role(pack, role, full, "fast", EVIDENCE).fit == 100.0
    assert score_role(pack, role, {}, "fast", EVIDENCE).fit == 0.0


def test_essential_weights_are_the_same_in_every_scenario() -> None:
    pack = load_pack()
    for role in pack.destination_roles.values():
        moderate = score_role(pack, role, NUR, "moderate", EVIDENCE)
        fast = score_role(pack, role, NUR, "fast", EVIDENCE)
        for a, b in zip(moderate.requirements, fast.requirements, strict=True):
            if a.essential:
                assert (a.weight, a.required) == (b.weight, b.required)


def test_fast_adoption_moves_weight_from_routine_to_complementing_skills() -> None:
    routine = Requirement(skill="credit_collections", tier="core")
    complement = Requirement(skill="big_data_analytics", tier="upskill", pages=[46])
    share = 66.0
    w_mod, _ = scenario_weight(routine, "routine", "moderate", share)
    w_fast, reason = scenario_weight(routine, "routine", "fast", share)
    assert w_fast < w_mod < params.ROLE_TIER_WEIGHT["core"]
    assert "66% of AI use" in reason
    c_mod, _ = scenario_weight(complement, "complement", "moderate", share)
    c_fast, _ = scenario_weight(complement, "complement", "fast", share)
    assert params.ROLE_TIER_WEIGHT["upskill"] < c_mod < c_fast


def test_scenario_never_changes_the_persons_levels() -> None:
    levels = dict(NUR)
    rank_roles(load_pack(), levels, "fast", EVIDENCE)
    assert levels == NUR


def test_unstated_skills_count_as_zero_and_are_shown_apart() -> None:
    pack = load_pack()
    match = score_role(
        pack, pack.destination_roles["o2c_reporting_analyst"], NUR, "moderate", EVIDENCE
    )
    assert "big_data_analytics" in match.gap["not_stated"]
    assert "credit_collections" in match.gap["ready"]
    assert "reporting" in match.gap["bridgeable"]  # claimed 2, needs 3


def test_essential_gap_marks_a_longer_route_but_keeps_the_role_ranked() -> None:
    pack = load_pack()
    match = score_role(pack, pack.destination_roles["cost_accountant"], NUR, "moderate", EVIDENCE)
    assert match.longer_route
    assert "Standard Costing" in match.essential_gaps
    assert match.fit > 0


def test_interests_reorder_only_near_ties_and_never_change_fit() -> None:
    pack = load_pack()
    plain = rank_roles(pack, NUR, "moderate", EVIDENCE)
    green = rank_roles(pack, NUR, "moderate", EVIDENCE, interests={"green"})
    assert sorted(m.fit for m in plain) == sorted(m.fit for m in green)
    for earlier, later in zip(green, green[1:], strict=False):
        assert later.fit <= earlier.fit + params.NEAR_TIE_POINTS


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
def test_contributions_add_up_to_the_fit(scenario: str) -> None:
    pack = load_pack()
    for role in pack.destination_roles.values():
        match = score_role(pack, role, NUR, scenario, EVIDENCE)  # type: ignore[arg-type]
        assert abs(sum(r.contribution for r in match.requirements) - match.fit) < 0.1
