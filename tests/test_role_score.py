"""C2 role score: range, band, components, what would raise it, and pay beside the card."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src import params
from src.evidence.field import field_profile
from src.journey.store import SkillClaim
from src.match.decision import band, components, fit_range, raise_options
from src.match.engine import Evidence, score_role
from src.match.outlook import MAJOR_GROUP
from src.match.pay import role_pay
from src.pack import load_pack

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")
ROLE = "o2c_reporting_analyst"


def _claims(source: str) -> dict[str, SkillClaim]:
    evidence = "Built the daily cash position report in Excel." if source == "cv" else ""
    role = load_pack().destination_roles[ROLE]
    return {r.skill: SkillClaim(level=2, evidence=evidence, source=source) for r in role.requires}


def _score(claims: dict[str, SkillClaim]) -> tuple[Any, dict[str, int | None]]:
    pack = load_pack()
    levels = {k: c.level for k, c in claims.items()}
    return score_role(pack, pack.destination_roles[ROLE], levels, "moderate", EVIDENCE), levels


def test_fully_evidenced_profile_has_low_equal_to_the_fit() -> None:
    claims = _claims("cv")
    match, levels = _score(claims)
    r = fit_range(load_pack(), match, levels, "moderate", EVIDENCE, claims)
    assert r["low"] == match.fit and r["basis"]


def test_self_rated_claims_lower_the_low_end() -> None:
    claims = _claims("self")
    match, levels = _score(claims)
    r = fit_range(load_pack(), match, levels, "moderate", EVIDENCE, claims)
    lowered, _ = _score({k: SkillClaim(level=1, source="self") for k in claims})
    assert r["low"] == lowered.fit < match.fit


def test_raise_points_equal_a_re_score_and_follow_the_route_rule() -> None:
    pack = load_pack()
    claims = {
        "reporting": SkillClaim(level=1, evidence="Prepared monthly ageing reports.", source="cv")
    }
    match, levels = _score(claims)
    options = raise_options(pack, match, levels, "moderate", EVIDENCE, claims)
    assert 0 < len(options) <= params.RAISE_SHOWN
    assert [o["points"] for o in options] == sorted((o["points"] for o in options), reverse=True)
    for o in options:
        after, _ = _score(
            {**claims, o["skill"]: SkillClaim(level=o["to_level"], source="cv", evidence="x")}
        )
        assert o["points"] == pytest.approx(after.fit - match.fit, abs=0.05)
        assert o["via"] == ("study" if o["to_level"] <= params.STUDY_MAX_LEVEL else "practice")


def test_a_self_rated_skill_at_its_level_is_raised_by_a_check() -> None:
    pack = load_pack()
    role = pack.destination_roles[ROLE]
    # Every requirement met at level 3 with CV evidence, except one self-rated skill.
    claims = {
        r.skill: SkillClaim(level=3, source="cv", evidence="Did it at work.") for r in role.requires
    }
    first = role.requires[0].skill
    claims[first] = SkillClaim(level=3, source="self")
    match, levels = _score(claims)
    checks = [
        o
        for o in raise_options(pack, match, levels, "moderate", EVIDENCE, claims)
        if o["via"] == "check"
    ]
    assert [c["skill"] for c in checks] == [first]
    evidenced = fit_range(
        pack,
        match,
        levels,
        "moderate",
        EVIDENCE,
        {**claims, first: SkillClaim(level=3, source="cv", evidence="Did it.")},
    )
    now = fit_range(pack, match, levels, "moderate", EVIDENCE, claims)
    assert checks[0]["points"] == pytest.approx(evidenced["low"] - now["low"], abs=0.05)


@pytest.mark.parametrize(
    ("fit", "expected"),
    [
        (100, "strong"),
        (75, "strong"),
        (74.9, "good"),
        (55, "good"),
        (35, "fair"),
        (34.9, "low"),
        (0, "low"),
    ],
)
def test_band_follows_the_thresholds(fit: float, expected: str) -> None:
    assert band(fit) == expected


def test_components_add_up_to_the_fit_and_mark_evidence() -> None:
    claims = {
        "reporting": SkillClaim(level=2, evidence="Prepared monthly ageing reports.", source="cv"),
        "dashboards": SkillClaim(level=1, source="self"),
    }
    match, _ = _score(claims)
    rows = components(match, claims)
    assert sum(r["points"] for r in rows) == pytest.approx(match.fit, abs=0.2)
    by_skill = {r["skill"]: r for r in rows}
    assert by_skill["reporting"]["evidenced"] and not by_skill["dashboards"]["evidenced"]


def _pay_row(series: str, entity: str, period: str, value: float) -> dict[str, Any]:
    return {
        "source_id": "dosm_wages_occupation",
        "series": series,
        "entity": entity,
        "period": period,
        "value": value,
        "unit": "RM per month",
        "fetched_at": datetime(2026, 10, 30, tzinfo=UTC),
        "cited_span": f"{entity} {period}",
    }


def test_pay_uses_the_latest_year_of_the_roles_group_and_never_zero() -> None:
    role = load_pack().destination_roles[ROLE]
    group = MAJOR_GROUP[field_profile().occupation(role.soc).isco[0]]  # type: ignore[union-attr]
    rows = [
        _pay_row("wages_median", group, "2024", 5000),
        _pay_row("wages_median", group, "2025", 5200),
        _pay_row("wages_mean", group, "2025", 6100),
        _pay_row("wages_median", "overall", "2025", 2900),
    ]
    pay = role_pay(role, rows)
    assert pay is not None
    assert (pay["year"], pay["median"], pay["mean"], pay["overall_median"]) == (
        "2025",
        5200,
        6100,
        2900,
    )
    assert pay["kind"] == "observed" and "not an offer" in pay["note"]
    assert role_pay(role, []) is None  # not published, never 0


def test_matches_cards_carry_c2_fields_and_pay_never_moves_fit(client: TestClient) -> None:
    body = {"situation": "working", "skills": {"reporting": {"level": 2, "source": "self"}}}
    pid = client.post("/api/profiles", json=body).json()["id"]
    for card in client.get(f"/api/profiles/{pid}/matches").json()["roles"]:
        assert card["band"] == band(card["fit"]) and card["band_basis"] == "assumption"
        assert {"low", "high", "basis"} <= set(card["fit_range"])
        assert card["fit_range"]["low"] <= card["fit"] <= card["fit_range"]["high"]
        assert card["components"] and isinstance(card["raise"], list)
        assert "essentials_short" in card and card["pay"] is None  # no pay series stored yet
