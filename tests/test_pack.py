"""The field pack is consistent and every name is on the TalentCorp page it cites."""

import re
from functools import cache

import pytest

from src.evidence.field import field_profile
from src.pack import load_pack
from tests.test_talentcorp import PDF


def test_pack_loads_and_every_reference_resolves() -> None:
    pack = load_pack()
    assert len(pack.current_roles) == 11  # the 11 highly impacted finance roles (PDF p. 26)
    assert len(pack.destination_roles) == 9
    assert "cash_application_analyst" in pack.current_roles


def test_every_role_crosswalk_is_followed_by_the_evidence_layer() -> None:
    pack = load_pack()
    codes = field_profile().soc_codes()
    socs = {r.soc for r in pack.current_roles.values()} | {
        r.soc for r in pack.destination_roles.values()
    }
    assert socs <= codes


def test_every_destination_is_reachable_from_some_current_role() -> None:
    pack = load_pack()
    reachable = {d for r in pack.current_roles.values() for d in r.transitions}
    assert reachable == set(pack.destination_roles)


def squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


@cache
def pdf_pages() -> list[str]:
    from pypdf import PdfReader  # dev-only; the test is skipped without the PDF

    return [squash(p.extract_text() or "") for p in PdfReader(PDF).pages]


# TalentCorp sometimes words a skill slightly differently on a pathway page than in its taxonomy.
PATHWAY_WORDING = {
    "systems_integration": "Systems Integration",
    "system_performance": "Systems Performance Management",
    "energy_management": "Energy Management",
}


@pytest.mark.skipif(not PDF.exists(), reason="TalentCorp PDF is kept only in gitignored data/raw")
def test_names_and_links_appear_on_their_cited_pages() -> None:
    pages = pdf_pages()
    pack = load_pack()
    missing = []
    for skill in pack.skills.values():
        if squash(skill.name) not in pages[skill.page - 1]:
            missing.append(("skill", skill.id, skill.page))
    for role in pack.current_roles.values():
        page = pages[role.page - 1]
        if squash(role.title.split(" (")[0]) not in page:
            missing.append(("role", role.id, role.page))
    for dest in pack.destination_roles.values():
        for req in dest.requires:
            name = PATHWAY_WORDING.get(req.skill, pack.skills[req.skill].name)
            missing += [
                ("link", f"{dest.id}<-{req.skill}", p)
                for p in req.pages
                if squash(name) not in pages[p - 1]
            ]
    assert missing == []
