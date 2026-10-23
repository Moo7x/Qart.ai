"""Persona learning-plan tests (pathway.md §7.3). They assert structure and properties, never
exact titles, so curation changes don't break them.

They include draft courses (include_drafts=True): the HRD-claimable and AI untuk Rakyat entries
are still waiting for a team review, and these tests check the plan logic, not the review state.
The demo build uses verified courses only (tests/test_resource_catalogue.py, DEMO_BUILD=1).
"""

from typing import Any

from src.engine.catalogue import default_catalogue
from src.engine.learning_plan import LearningPlan, plan_for_profile
from tests.test_personas import PERSONA_DIR, SIGNALS, load, profile_for

COURSES = default_catalogue().courses


def plan_of(name: str, **overrides: Any) -> LearningPlan:
    persona = load(PERSONA_DIR / f"{name}.json")
    persona["answers"] = {**persona["answers"], **overrides}
    plan = plan_for_profile(profile_for(persona), snapshot=SIGNALS, include_drafts=True)
    assert plan is not None
    return plan


def test_p1_hrd_registered_employer_pays_nothing_and_gets_an_hr_action() -> None:
    plan = plan_of("p1_recon_nearby")
    hrd = [s for s in plan.steps if s.kind == "course" and s.hrd_claimable]
    assert hrd and all(s.cost_to_user_myr == 0 for s in hrd)
    assert any("Ask HR to apply for the HRD Corp grant via e-TRiS" in a for a in plan.action_items)
    assert plan.summary.cost_to_user_myr == 0 and plan.summary.hrd_claimable_steps >= 1
    assert plan.summary.cost_possibly_covered_by_employer_myr > 0


def test_p1b_employer_not_sure_shows_the_listed_price_and_a_may_be_claimable_note() -> None:
    plan = plan_of("p1_recon_nearby", employer_hrd="not_sure")
    hrd = [s for s in plan.steps if s.kind == "course" and s.hrd_claimable]
    assert hrd and all(s.cost_to_user_myr is None or s.cost_to_user_myr > 0 for s in hrd)
    assert any("May be claimable" in n for n in plan.notes)
    assert any("whether your company is HRD Corp-registered" in x for x in plan.action_items)


def test_p3_eligible_graduate_starts_with_ai_untuk_rakyat_and_pays_nothing() -> None:
    plan = plan_of("p3_graduate_switch")
    first = COURSES[plan.steps[0].resource_id or ""]
    assert (
        "ai_literacy" in first.tags
        and first.eligibility.max_age == 30
        and first.eligibility.malaysian_only
    )
    assert plan.summary.cost_to_user_myr == 0 and plan.summary.steps_with_unknown_cost == 0


def test_p3b_older_graduate_gets_the_open_ai_literacy_course_instead() -> None:
    plan = plan_of("p3_graduate_switch", age_band="31_45")
    first = COURSES[plan.steps[0].resource_id or ""]
    assert "ai_literacy" in first.tags
    assert first.eligibility.max_age is None and not first.eligibility.malaysian_only


def test_p5_strong_data_profile_fits_the_timeframe_and_counts_certificates() -> None:
    plan = plan_of("p5_strong_data")
    assert plan.summary.fits_timeframe and all(s.in_timeframe for s in plan.steps)
    with_cert = sum(1 for s in plan.steps if s.kind == "course" and s.certificate)
    assert plan.summary.certificates == with_cert


def test_every_persona_plan_shows_hours_weeks_cost_source_and_check_date() -> None:
    for name in (
        "p1_recon_nearby",
        "p2_recon_grow",
        "p3_graduate_switch",
        "p5_strong_data",
        "p6_accountant_switch",
    ):
        for step in plan_of(name).steps:
            assert step.hours > 0 and 1 <= step.start_week <= step.end_week
            if step.kind == "course":
                assert step.url and step.last_verified and step.reasons
                assert step.cost_to_user_myr is not None or step.cost_type in {
                    "unknown",
                    "hrd_claimable",
                }


def test_the_sparse_profile_gets_no_plan() -> None:
    persona = load(PERSONA_DIR / "p4_sparse.json")
    assert plan_for_profile(profile_for(persona), snapshot=SIGNALS) is None
