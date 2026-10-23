"""Resource catalogue validation (pathway.md §7.1)."""

import os
import warnings
from dataclasses import replace
from datetime import date

import pytest

from src.contract import Course
from src.engine.catalogue import default_case_index, default_catalogue
from src.engine.resources import default_milestones, plan_courses
from src.engine.role_catalogue import default_role_catalogue

CAT = default_catalogue()
COURSES = list(CAT.courses.values())
VOCABULARY = CAT.vocabulary
LEVELS = {0.0, 0.3, 0.7, 1.0}


@pytest.mark.parametrize("course", COURSES, ids=lambda c: c.id)
def test_course_is_complete_and_honest(course: Course) -> None:
    assert course.url.startswith("https://") and course.hours > 0 and course.hours_basis
    assert course.skill_steps, "every course needs skill steps"
    assert [s.id for s in course.skill_steps] == course.skills  # one list for old and new code
    for step in course.skill_steps:
        assert step.id in VOCABULARY
        assert (
            step.from_level in LEVELS
            and step.to_level in LEVELS
            and step.to_level > step.from_level
        )
    if course.hrd_claimable:  # never claimable without a page that says so
        assert course.claim_evidence_url and course.claim_evidence_url.startswith("https://")
        assert course.hrd_scheme
    if course.cost_type == "free":
        assert course.cost_myr == 0 and course.cost_note  # free only where a source says so
    if (
        course.cost_myr is None
    ):  # no listed price: never counted as free for anyone outside a scheme
        assert course.cost_type in {"unknown", "hrd_claimable", "free_if_eligible"}
    if course.cost_type == "free_if_eligible":
        assert course.eligibility.malaysian_only or course.eligibility.max_age is not None
    if course.status == "draft":
        assert course.verified is False  # drafts are never in search or the demo plan
    assert course.format and course.language
    if course.hours_basis == "provider_pace":  # hours = pace x length: keep the stated pace (§3.2)
        assert course.stated_duration
    assert set(course.prerequisites) <= set(CAT.courses)
    if course.status == "verified":
        assert course.last_verified and course.verified_by
        date.fromisoformat(course.last_verified)


def test_ids_are_unique() -> None:
    import json
    from pathlib import Path

    raw = json.loads((Path(__file__).parents[1] / "catalogue" / "courses.json").read_text())
    ids = [c["id"] for c in raw["courses"]]
    assert len(ids) == len(set(ids))


def test_an_open_to_all_ai_literacy_resource_exists() -> None:
    open_ai = [
        c
        for c in COURSES
        if "ai_literacy" in c.tags
        and c.status == "verified"
        and c.eligibility.max_age is None
        and c.eligibility.min_age is None
        and not c.eligibility.malaysian_only
    ]
    assert open_ai, "the AI-literacy-first rule needs a resource open to everyone"


def test_every_core_role_skill_has_a_verified_resource() -> None:
    """Warning while drafting; an error for the demo build (DEMO_BUILD=1)."""
    covered = {s.id for c in plan_courses(CAT, include_drafts=False) for s in c.skill_steps}
    core = {s.id for r in default_role_catalogue().roles for s in r.core_skills}
    missing = sorted(core - covered)
    if missing and os.environ.get("DEMO_BUILD") == "1":
        pytest.fail(f"core skills without a verified resource: {missing}")
    if missing:
        warnings.warn(f"core skills without a verified resource yet: {missing}", stacklevel=1)


def test_drafts_are_hidden_unless_the_flag_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    draft = next(iter(CAT.courses.values())).model_copy(update={"id": "draft_x", "status": "draft"})
    cat = replace(CAT, courses={**CAT.courses, "draft_x": draft})
    monkeypatch.delenv("SHOW_DRAFT_RESOURCES", raising=False)
    assert "draft_x" not in {c.id for c in plan_courses(cat)}
    monkeypatch.setenv("SHOW_DRAFT_RESOURCES", "true")
    assert "draft_x" in {c.id for c in plan_courses(cat)}


def test_milestones_reference_real_skills_and_cases() -> None:
    m = default_milestones()
    cases = {c.id for c in default_case_index()}
    for ms in [*m.milestones, m.default]:
        assert set(ms.skills) <= set(VOCABULARY) and ms.hours > 0
        assert ms.case_id is None or ms.case_id in cases, ms.id
    assert any(ms.case_id for ms in m.milestones)  # practice cases are linked
