from src.forecast.roles import check, industry_roles


def test_industry_roles_cover_the_talentcorp_cluster_and_are_consistent() -> None:
    roles = industry_roles().roles
    assert check() == []
    assert len({r.id for r in roles}) == len(roles)
    assert sum(r.talentcorp is not None for r in roles) == 24  # TalentCorp's F&A cluster
