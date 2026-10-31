"""The SDGs a person chooses change which near-tie role comes first, never a fit score."""

from src.match.engine import Evidence, rank_roles, sdg_overlap
from src.pack import load_pack

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")


def test_chosen_sdgs_reorder_only_near_ties_and_keep_fit() -> None:
    pack = load_pack()
    levels: dict[str, int | None] = {}  # everyone at zero: every role ties at fit 0
    plain = rank_roles(pack, levels, "moderate", EVIDENCE)
    green = rank_roles(pack, levels, "moderate", EVIDENCE, sdg_goals={"12"})
    assert {m.role_id: m.fit for m in plain} == {m.role_id: m.fit for m in green}
    assert sdg_overlap(pack, green[0].role_id, {"12"}) == 1  # a role serving SDG 12 comes first
    first_without = next(m for m in plain if sdg_overlap(pack, m.role_id, {"12"}) == 0)
    assert [m.role_id for m in green].index(first_without.role_id) > 0
