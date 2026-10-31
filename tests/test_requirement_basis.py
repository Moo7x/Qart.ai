"""Every plan skill says why it is there: a TalentCorp page, an O*NET task, or our assumption."""

from src.match.basis import requirement_basis
from src.pack import load_pack


def test_every_requirement_has_a_basis_with_a_source() -> None:
    pack = load_pack()
    kinds = set()
    for role in pack.destination_roles.values():
        for req in role.requires:
            basis = requirement_basis(pack, role.id, req.skill)
            assert basis["text"] and basis["source"]
            kinds.add(basis["kind"])
            if req.pages:
                assert basis["kind"] == "talentcorp"
    assert kinds == {"talentcorp", "onet", "assumption"}


def test_erp_for_p2p_is_labelled_our_assumption() -> None:
    basis = requirement_basis(load_pack(), "p2p_reporting_analyst", "erp")
    assert basis["kind"] == "assumption" and "not for" in basis["text"]
