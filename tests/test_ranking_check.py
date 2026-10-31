from src.match.validation import check
from src.pack import load_pack

# Floor measured on 2026-11-01 (offline, fit only): 8 of 11 current roles have a career move
# TalentCorp lists for them among their top 3. A change that drops below it must say why.
HIT_RATE_FLOOR = 0.7


def test_the_ranking_reproduces_most_talentcorp_career_moves() -> None:
    result = check(load_pack())
    assert result["roles"] == 11
    assert result["hit_rate"] >= HIT_RATE_FLOOR
