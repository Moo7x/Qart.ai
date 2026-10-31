"""SDG links (B7): every skill and destination role has its own linked target, reason and source."""

import pytest

from src.pack import PackError, SdgLink, _check, load_pack


def test_every_skill_and_destination_role_is_linked_with_a_reason_and_source() -> None:
    pack = load_pack()
    for skill in pack.skills:
        links = pack.sdg.skills[skill]
        assert any(link.target == "4.4" for link in links)
        assert all(link.how and link.source and link.target in pack.sdg.targets for link in links)
    for role in pack.destination_roles:
        links = pack.sdg.roles[role]
        assert any(link.target == "8.5" for link in links)
        assert all(link.how and link.source for link in links)


def test_green_skills_serve_12_6_and_automation_serves_8_2() -> None:
    pack = load_pack()
    assert "12.6" in {link.target for link in pack.sdg.skills["esg"]}
    assert "8.2" in {link.target for link in pack.sdg.skills["process_automation"]}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda p: p.sdg.skills.pop("erp"), "skill erp has no SDG link"),
        (lambda p: p.sdg.roles.pop("cost_accountant"), "cost_accountant has no SDG link"),
        (
            lambda p: p.sdg.skills.__setitem__("erp", [SdgLink(target="4.4", how="", source="x")]),
            "needs a one-line reason",
        ),
        (
            lambda p: p.sdg.skills.__setitem__("erp", [SdgLink(target="9.9", how="x", source="x")]),
            "unknown target 9.9",
        ),
    ],
)
def test_pack_check_rejects_a_missing_link_reason_or_target(change: object, message: str) -> None:
    pack = load_pack().model_copy(deep=True)
    change(pack)  # type: ignore[operator]
    with pytest.raises(PackError, match=message):
        _check(pack)
