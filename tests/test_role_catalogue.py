"""Role catalogue guards (QART_NEXT_STEPS §5.1): real O*NET codes or TODO, known skills,
families and industries, honest sizes, and symmetric family adjacency."""

import re

import pytest

from src.engine.catalogue import default_catalogue
from src.engine.questionnaire import load_questionnaire
from src.engine.role_catalogue import CORE_WEIGHT, TargetRole, load_role_catalogue

CAT = load_role_catalogue()
Q = load_questionnaire()
VOCABULARY = default_catalogue().vocabulary
ONET_CODE = re.compile(r"^\d{2}-\d{4}\.\d{2}$")


@pytest.mark.parametrize("role", CAT.roles, ids=lambda r: r.id)
def test_role_is_well_formed(role: TargetRole) -> None:
    ids = [s.id for s in role.skills]
    assert len(ids) == len(set(ids)) and 5 <= len(ids) <= 8
    assert not set(ids) - set(VOCABULARY), "unknown skill id"
    assert len(role.core_skills) >= 3
    assert role.family in CAT.family_ids
    assert set(role.typical_industries) <= set(Q.industries)
    assert role.min_education in Q.education_order


@pytest.mark.parametrize("role", CAT.roles, ids=lambda r: r.id)
def test_source_is_a_checked_onet_code_or_todo(role: TargetRole) -> None:
    source = role.source
    if source.code == "TODO":
        assert source.verified is False and source.note and source.candidates
    else:
        assert ONET_CODE.match(source.code) and source.verified and source.retrieved
        assert source.url == f"https://www.onetonline.org/link/summary/{source.code}"


def test_catalogue_size_and_balance() -> None:
    assert len(CAT.roles) >= 12 and len({r.id for r in CAT.roles}) == len(CAT.roles)
    core_totals = [sum(s.weight for s in r.core_skills) for r in CAT.roles]
    assert max(core_totals) <= 4 * CORE_WEIGHT and min(core_totals) >= 3 * CORE_WEIGHT


def test_family_adjacency_is_symmetric_and_known() -> None:
    for family in CAT.families:
        assert family.id not in family.adjacent
        for other in family.adjacent:
            assert other in CAT.family_ids and CAT.adjacent(other, family.id)


def test_questionnaire_families_exist() -> None:
    used = {r.family for r in Q.current_roles if r.family} | {
        f for t in Q.tasks for f in t.families
    }
    assert used <= CAT.family_ids
    assert {e.level for e in Q.education} <= set(Q.education_order)
