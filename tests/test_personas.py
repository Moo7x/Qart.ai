"""Persona tests for the role ranking (QART_NEXT_STEPS §8), written before the scoring.

Each fixture in tests/personas/ holds a full questionnaire answer set and the team's expected
outcome. Answers are turned into skill chips exactly as the questionnaire does (role pre-fill +
tasks + tools at "use sometimes"), then `skill_edits` apply the person's own level changes.
We assert top-3 membership, families and bands, never exact order or scores.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from src.contract import Preferences, Profile
from src.engine.questionnaire import default_questionnaire, prefill_levels

PERSONA_DIR = Path(__file__).parent / "personas"
PERSONAS = sorted(PERSONA_DIR.glob("*.json"))


def load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def profile_for(persona: dict[str, Any]) -> Profile:
    a = persona["answers"]
    levels = prefill_levels(a["current_job"], a["tasks"], a["tools"], default_questionnaire())
    levels.update(a.get("skill_edits", {}))
    prefs = {
        k: a[k]
        for k in (
            "current_job",
            "industry",
            "education",
            "tools",
            "tasks",
            "direction",
            "timeframe_months",
        )
        if k in a
    }
    return Profile(
        id=persona["id"],
        display_name=f"{persona['label']} (synthetic)",
        current_role_id="recon_associate",  # evidence-engine field; the ranking does not read it
        years_experience=a["years_experience"],
        weekly_learning_hours=a["weekly_learning_hours"],
        team="personas",
        preferences=Preferences.model_validate({**prefs, "skill_levels": levels}),
    )


@pytest.mark.xfail(reason="rank_roles is built in the next step (QART_NEXT_STEPS §5)", strict=True)
@pytest.mark.parametrize("path", PERSONAS, ids=lambda p: p.stem)
def test_persona_expectations(path: Path) -> None:
    from src.engine.ranking import rank_for_profile  # noqa: PLC0415 (not built yet)

    persona = load(path)
    result = rank_for_profile(profile_for(persona))
    expect = persona["expect"]
    if expect.get("empty_profile"):
        assert result.empty_profile and result.starter_roles
        return
    assert not result.empty_profile
    top3 = result.roles[:3]
    ids = [r.role_id for r in top3]
    for role_id in expect.get("top3_includes", []):
        assert role_id in ids, f"{role_id} not in top 3 {ids}"
    if within := expect.get("top3_families_within"):
        assert all(r.family in within for r in top3), [r.family for r in top3]
    if exclude := expect.get("top3_families_exclude"):
        assert all(r.family not in exclude for r in top3), [r.family for r in top3]
    rank = {r.role_id: i for i, r in enumerate(result.roles)}
    if pair := expect.get("best_of_above_best_of"):
        better, worse = pair
        assert min(rank[x] for x in better) < min(rank[x] for x in worse)
    by_id = {r.role_id: r for r in result.roles}
    if strong := expect.get("any_strong"):
        assert any(by_id[x].band == "Strong match" for x in strong), [
            (x, by_id[x].band) for x in strong
        ]
    for role_id, floor in expect.get("feasibility_at_least", {}).items():
        assert by_id[role_id].components.feasibility >= floor


def test_persona_fixtures_are_valid_questionnaire_answers() -> None:
    q = default_questionnaire()
    assert len(PERSONAS) >= 6
    for path in PERSONAS:
        persona = load(path)
        a = persona["answers"]
        assert a["current_job"] in {r.id for r in q.current_roles}
        assert set(a["tasks"]) <= {t.id for t in q.tasks}
        assert set(a["tools"]) <= {t.label for t in q.tools}
        profile_for(persona)  # validates every field against the contract
