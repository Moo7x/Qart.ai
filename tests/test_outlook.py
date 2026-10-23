"""Role outlook restates demand evidence from its sources and never touches the fit."""

from src.collectors import mycol, talentcorp
from src.evidence.signals import Signal
from src.match.outlook import role_outlook
from src.pack import load_pack


def rows() -> list[dict[str, object]]:
    observations = mycol.parse(mycol.load_extraction())
    observations += talentcorp.parse(talentcorp.load_extraction())
    return [o.__dict__ for o in observations]


def share_signal(group: str) -> Signal:
    return Signal(
        id=f"dosm_share_{group}",
        title="Professionals: share of employees",
        family="malaysian_labour",
        kind="observed",
        direction="rising",
        early_direction="up",
        headline="13.85% (2011) → 18.74% (2025)",
        unit="% of employees",
        points=[],
        independent_sources=1,
        note="Observed history, not a forecast.",
        sources=[],
        evidence=[],
    )


def test_listed_occupation_and_in_demand_skills_are_named_with_sources() -> None:
    pack = load_pack()
    items = role_outlook(
        pack, pack.destination_roles["cost_accountant"], rows(), [share_signal("professionals")]
    )
    texts = " ".join(i["text"] for i in items)
    assert "MyCOL lists Accountants and Auditors as a critical" in texts
    assert "Big Data Analytics" in texts and "ISCO-08 2411" in texts
    assert all(i["source"] for i in items)


def test_unlisted_occupation_says_not_listed_and_missing_sources_say_nothing() -> None:
    pack = load_pack()
    procurement = pack.destination_roles["procurement_analyst"]  # ISCO-08 3323 Buyers
    items = role_outlook(pack, procurement, rows(), [])
    assert any("not among the 66 critical occupations" in i["text"] for i in items)
    assert role_outlook(pack, procurement, [], []) == []  # nothing collected: no claims at all
