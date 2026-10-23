"""Questionnaire pre-fill and held skills (QART_NEXT_STEPS §3): defaults to "use sometimes",
never downgrades, and practice evidence only raises a level."""

from src.contract import Preferences, Profile, SkillState
from src.engine.questionnaire import default_questionnaire, held_skills, prefill_levels

Q = default_questionnaire()


def profile_with(levels: dict[str, str]) -> Profile:
    return Profile(
        id="u_test",
        display_name="Test (synthetic)",
        current_role_id="recon_associate",
        years_experience=3,
        weekly_learning_hours=3,
        team="t",
        preferences=Preferences.model_validate({"skill_levels": levels}),
    )


def state(skill_id: str, name: str) -> SkillState:
    return SkillState.model_validate(
        {
            "user_id": "u_test",
            "skill_id": skill_id,
            "state": name,
            "why": "test",
            "counted_events": 1,
            "independent_successes": 0,
            "provisional_estimate": 0.5,
            "estimate_note": "test",
        }
    )


def test_prefill_combines_role_tasks_and_tools_at_the_default_level() -> None:
    levels = prefill_levels(
        "reconciliation_associate",
        ["record_macros", "query_database"],
        ["Python", "None of these"],
        Q,
    )
    assert {"recon_to_source", "erp", "excel_automation", "sql_basics", "python"} <= set(levels)
    assert set(levels.values()) == {"sometimes"}
    assert prefill_levels(None, [], ["None of these"], Q) == {}
    assert prefill_levels("graduate", [], [], Q) == {}


def test_evidence_raises_but_never_lowers_a_level() -> None:
    held = held_skills(
        profile_with({"recon_to_source": "heard", "spreadsheet_modelling": "confident"}),
        [
            state("recon_to_source", "observed_with_help"),
            state("spreadsheet_modelling", "observed_with_help"),
            state("cutoff_timing", "demonstrated_independently"),
            state("fx_conversion", "self_reported"),
        ],
        Q,
    )
    assert held["recon_to_source"].level == "sometimes"
    assert held["recon_to_source"].source == "questionnaire + practice evidence"
    assert held["spreadsheet_modelling"].level == "confident"
    assert held["spreadsheet_modelling"].source == "questionnaire"
    assert (
        held["cutoff_timing"].value == 1.0 and held["cutoff_timing"].source == "practice evidence"
    )
    assert "fx_conversion" not in held  # a self-reported claim alone adds nothing


def test_funding_options_match_the_contract() -> None:
    """The questionnaire's option ids are exactly the values Preferences accepts."""
    from typing import get_args

    from src.contract import AgeBand, Budget, Citizenship, EmployerHrd, Employment, LearningLanguage

    f = Q.funding
    for options, literal in [
        (f.employment, Employment),
        (f.employer_hrd, EmployerHrd),
        (f.budget, Budget),
        (f.language, LearningLanguage),
        (f.age_band, AgeBand),
        (f.malaysian, Citizenship),
    ]:
        assert [o.id for o in options] == list(get_args(literal))
