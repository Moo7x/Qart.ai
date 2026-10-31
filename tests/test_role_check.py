"""Pack check (B10): a destination role needs a study page, an essential, a followed SOC code and
an SDG link, or the pack does not load."""

import pytest

from src.pack import Pack, PackError, _check, load_pack

ROLE = "cost_accountant"


def _broken(change: str) -> Pack:
    pack = load_pack().model_copy(deep=True)
    role = pack.destination_roles[ROLE]
    if change == "page":
        role.pages = []
    elif change == "essential":
        role.requires = [r.model_copy(update={"essential": False}) for r in role.requires]
    elif change == "soc":
        role.soc = "99-9999.00"
    elif change == "sdg":
        pack.sdg.roles.pop(ROLE)
    return pack


def test_every_destination_role_cites_a_page_and_an_essential() -> None:
    for role in load_pack().destination_roles.values():
        assert role.pages and any(r.essential for r in role.requires)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("page", "cites no study page"),
        ("essential", "has no essential requirement"),
        ("soc", "SOC 99-9999.00 is not in field.yaml"),
        ("sdg", "has no SDG link"),
    ],
)
def test_pack_check_rejects_an_unsourced_role(change: str, message: str) -> None:
    with pytest.raises(PackError, match=message):
        _check(_broken(change))
