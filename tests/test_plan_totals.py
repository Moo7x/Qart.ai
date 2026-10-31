"""One definition of plan hours: the planned study steps; AI basics are named apart."""

import pytest

from src.journey.store import claims_from_levels
from src.match.engine import Evidence, score_role
from src.pack import load_pack
from src.pathway.planner import plan_pathway
from src.pathway.tracks import comparison
from src.resources import load_resources

EVIDENCE = Evidence(automation_share={}, automation_period="test", automation_source="test")
# A synthetic cash application analyst (the "Nur" sample persona), as in tests/test_match.py.
NUR = {
    "cash_application": 3,
    "reconciliation": 3,
    "credit_collections": 3,
    "erp": 2,
    "reporting": 2,
    "data_validation": 1,
    "accounting_principles": 2,
}
ROLES = list(load_pack().destination_roles)


@pytest.mark.parametrize("role_id", ROLES)
def test_plan_total_is_the_sum_of_its_steps(role_id: str) -> None:
    pack = load_pack()
    match = score_role(pack, pack.destination_roles[role_id], NUR, "moderate", EVIDENCE)
    path = plan_pathway(pack, match, claims_from_levels(NUR), 6, "moderate", EVIDENCE)
    assert path.total_hours == pytest.approx(sum(s.hours for s in path.steps))


@pytest.mark.parametrize("role_id", ROLES)
def test_with_ai_hours_name_both_parts(role_id: str) -> None:
    pack = load_pack()
    match = score_role(pack, pack.destination_roles[role_id], NUR, "moderate", EVIDENCE)
    claims = claims_from_levels(NUR)
    path = plan_pathway(pack, match, claims, 6, "moderate", EVIDENCE)
    with_ai = comparison(pack, load_resources(), claims, role_id, 6, EVIDENCE)["with_ai"]
    assert with_ai["plan_hours"] == path.total_hours
    # Exact to the shown decimal: the screen prints "X h plan + Y h AI basics" beside the total.
    assert with_ai["hours"] == round(with_ai["plan_hours"] + with_ai["ai_basics_hours"], 1)
