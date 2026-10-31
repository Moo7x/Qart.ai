"""A skill already at what study gives goes straight to practice and is never "uncovered"."""

import pytest

from src import params
from src.journey.store import claims_from_levels
from src.match.engine import Evidence, score_role
from src.pack import load_pack
from src.pathway.planner import plan_pathway

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")
ROLE = "continuous_improvement_specialist"


@pytest.mark.parametrize("skill", ["continuous_improvement", "process_optimisation"])
def test_skill_at_study_maximum_is_practice_not_uncovered(skill: str) -> None:
    pack = load_pack()
    assert pack.courses_for(skill)  # the skill has verified courses: "uncovered" would be false
    levels: dict[str, int | None] = {skill: params.STUDY_MAX_LEVEL}
    match = score_role(pack, pack.destination_roles[ROLE], levels, "moderate", EVIDENCE)
    path = plan_pathway(pack, match, claims_from_levels(levels), 6, "moderate", EVIDENCE)
    name = pack.skills[skill].name
    assert name not in path.uncovered and name not in path.partly_covered
    assert any(a["rule"] == "straight_to_practice" and name in a["text"] for a in path.adjustments)
    assert any(p.skill == skill for p in path.practice_steps)
    assert all(s.skill != skill for s in path.steps)
