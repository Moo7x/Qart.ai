"""Scenario floor: no weight vanishes or turns negative at any sensitivity intensity."""

import pytest

from src import params
from src.match.engine import Evidence, scenario_weight, score_role
from src.pack import Requirement, load_pack

# Every occupation at 100% automation-style use: the strongest shift the evidence could give.
ALL_AUTOMATED = Evidence(
    automation_share={r.soc: 100.0 for r in load_pack().destination_roles.values()},
    automation_period="test",
    automation_source="test",
)


@pytest.mark.parametrize("intensity", params.SENSITIVITY_INTENSITIES)
def test_routine_weight_stays_positive_at_every_intensity(intensity: float) -> None:
    req = Requirement(skill="credit_collections", tier="core")
    weight, _ = scenario_weight(req, "routine", "fast", 100.0, intensity=intensity)
    assert weight >= params.ROLE_TIER_WEIGHT["core"] * params.SCENARIO_FACTOR_FLOOR
    assert weight > 0


def test_floor_applies_only_below_it() -> None:
    req = Requirement(skill="credit_collections", tier="core")
    weight, reason = scenario_weight(req, "routine", "fast", 50.0)
    assert weight == pytest.approx(params.ROLE_TIER_WEIGHT["core"] * 0.5)
    floored, floored_reason = scenario_weight(req, "routine", "fast", 100.0, intensity=1.5)
    assert floored == pytest.approx(params.ROLE_TIER_WEIGHT["core"] * params.SCENARIO_FACTOR_FLOOR)
    assert "×0.10" in floored_reason


@pytest.mark.parametrize("intensity", params.SENSITIVITY_INTENSITIES)
def test_every_role_weight_is_positive_and_essentials_unchanged(intensity: float) -> None:
    pack = load_pack()
    for role in pack.destination_roles.values():
        match = score_role(pack, role, {}, "fast", ALL_AUTOMATED, intensity)
        for req in match.requirements:
            assert req.weight > 0
            if req.essential:
                assert req.weight == req.base_weight
