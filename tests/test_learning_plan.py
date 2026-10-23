"""Unit tests for the learning plan (pathway.md §7.2), on small synthetic courses."""

from dataclasses import replace
from typing import Any

import pytest

from src.contract import Course, Eligibility, SkillStep
from src.engine.catalogue import LearnHours, SkillInfo
from src.engine.learning_plan import (
    PlanAnswers,
    build_learning_plan,
    choose_for_skill,
    cost_to_user,
    default_plan_config,
    eligibility_check,
    prerequisite_order,
    within_budget,
)
from src.engine.ranking import GapItem
from src.engine.resources import Milestone, MilestoneCatalogue

CFG = default_plan_config()
A = PlanAnswers(weekly_hours=4, timeframe_weeks=13, timeframe_months=3)


def skill(sid: str, prereqs: tuple[str, ...] = ()) -> SkillInfo:
    return SkillInfo(
        id=sid,
        name=sid.upper(),
        practised=False,
        learn_hours=LearnHours(to_basic=10, to_confident=20),
        prerequisites=list(prereqs),
    )


VOCAB = {k: skill(k) for k in ("sql", "viz", "ai")} | {
    "py": skill("py"),
    "torch": skill("torch", ("py",)),
}


def course(cid: str, steps: dict[str, tuple[float, float]], hours: float = 4, **kw: Any) -> Course:
    base: dict[str, Any] = {
        "id": cid,
        "title": cid,
        "provider": "p",
        "url": f"https://x/{cid}",
        "hours": hours,
        "cost": "free",
        "skills": list(steps),
        "retrieved": "2026-10-23",
        "status": "verified",
        "cost_type": "free",
        "cost_myr": 0,
        "skill_steps": [SkillStep(id=k, from_level=f, to_level=t) for k, (f, t) in steps.items()],
        "format": ["reading"],
        "language": ["en"],
    }
    return Course(**{**base, **kw})


def gap(
    sid: str, current: float = 0.0, required: float = 0.7, hours: float = 10, core: bool = True
) -> GapItem:
    return GapItem(
        skill_id=sid,
        name=sid.upper(),
        current_level=current,
        required_level=required,
        type="learn" if current == 0 else "improve",
        hours=hours,
        momentum_label="stable",
        is_core=core,
        score_gain_per_hour=1.0,
        fits_timeframe=True,
        label=f"Learn {sid.upper()}",
    )


MILESTONES = MilestoneCatalogue(
    milestones=[Milestone(id="m_sql", title="Use SQL on real data", skills=["sql"], hours=2)],
    default=Milestone(id="m_any", title="Apply it", skills=[], hours=1),
)


def plan(gaps: list[GapItem], courses: list[Course], answers: PlanAnswers = A):  # type: ignore[no-untyped-def]
    return build_learning_plan("role", gaps, answers, courses, VOCAB, MILESTONES, CFG)


# --- §4.1 cost to the person, every row --------------------------------------------------------

HRD = course(
    "hrd",
    {"sql": (0, 0.7)},
    cost_type="hrd_claimable",
    cost_myr=900,
    hrd_claimable=True,
    claim_evidence_url="https://x/hrd",
    hrd_scheme="HCC (SBL-KHAS)",
)


@pytest.mark.parametrize(
    ("c", "answers", "to_user", "covered", "note"),
    [
        (course("f", {"sql": (0, 0.7)}), A, 0, 0, None),
        (
            course(
                "e",
                {"sql": (0, 0.7)},
                cost_type="free_if_eligible",
                cost_myr=None,
                eligibility=Eligibility(malaysian_only=True),
            ),
            A,
            0,
            0,
            "Free if you are eligible",
        ),
        (
            HRD,
            replace(A, employment="employed", employer_hrd="yes"),
            0,
            900,
            "HR applies via e-TRiS",
        ),
        (
            HRD,
            replace(A, employment="employed", employer_hrd="not_sure"),
            900,
            900,
            "May be claimable",
        ),
        (HRD, replace(A, employment="employed", employer_hrd="no"), 900, 0, None),
        (HRD, replace(A, employment="job_seeking", employer_hrd=None), 900, 0, None),
        (course("l", {"sql": (0, 0.7)}, cost_type="low_cost", cost_myr=70), A, 70, 0, None),
        (
            course("u", {"sql": (0, 0.7)}, cost_type="unknown", cost_myr=None),
            A,
            None,
            0,
            "no price stated",
        ),
    ],
)
def test_cost_to_user_follows_the_table(
    c: Course, answers: PlanAnswers, to_user: float | None, covered: float, note: str | None
) -> None:
    cost = cost_to_user(c, answers)
    assert cost.to_user == to_user and cost.possibly_covered == covered
    assert (note is None and not cost.notes) or (note and any(note in n for n in cost.notes))


def test_hrd_wording_never_promises_approval() -> None:
    cost = cost_to_user(HRD, replace(A, employment="employed", employer_hrd="yes"))
    assert "if approved" in cost.notes[0]


# --- §4.2 filters ----------------------------------------------------------------------------

YOUTH = course(
    "y",
    {"ai": (0, 0.3)},
    cost_type="free_if_eligible",
    eligibility=Eligibility(min_age=18, max_age=30, malaysian_only=True),
    tags=["ai_literacy"],
)


def test_a_known_answer_excludes_and_an_unknown_one_keeps_with_a_note() -> None:
    assert eligibility_check(YOUTH, replace(A, age_band="31_45", malaysian="yes"), CFG) == (
        False,
        [],
    )
    assert eligibility_check(YOUTH, replace(A, age_band="18_30", malaysian="no"), CFG) == (
        False,
        [],
    )
    allowed, notes = eligibility_check(
        YOUTH, replace(A, age_band="prefer_not", malaysian="prefer_not"), CFG
    )
    assert allowed and any("Malaysian" in n for n in notes) and any("18–30" in n for n in notes)
    assert eligibility_check(YOUTH, replace(A, age_band="18_30", malaysian="yes"), CFG) == (
        True,
        [],
    )


@pytest.mark.parametrize(
    ("budget", "free", "cheap", "dear", "unknown", "hrd"),
    [
        ("free_only", True, False, False, False, False),
        ("up_to_200", True, True, False, False, False),
        ("employer_pays", True, False, False, False, True),
        (None, True, True, True, True, True),
    ],
)
def test_budget_options(
    budget: str | None, free: bool, cheap: bool, dear: bool, unknown: bool, hrd: bool
) -> None:
    a = replace(A, budget=budget)
    options = {
        "free": course("f", {"sql": (0, 0.7)}),
        "cheap": course("c", {"sql": (0, 0.7)}, cost_type="low_cost", cost_myr=70),
        "dear": course("d", {"sql": (0, 0.7)}, cost_type="low_cost", cost_myr=230),
        "unknown": course("u", {"sql": (0, 0.7)}, cost_type="unknown", cost_myr=None),
        "hrd": HRD,
    }
    got = {k: within_budget(c, cost_to_user(c, a), a) for k, c in options.items()}
    assert got == {"free": free, "cheap": cheap, "dear": dear, "unknown": unknown, "hrd": hrd}


def test_a_course_must_start_near_the_person_level() -> None:
    advanced = course("adv", {"sql": (0.7, 1.0)})
    assert choose_for_skill(gap("sql", current=0.0, required=1.0), [advanced], A, CFG, set()) == []
    assert choose_for_skill(gap("sql", current=0.7, required=1.0), [advanced], A, CFG, set())


# --- §4.3 choosing ---------------------------------------------------------------------------


def test_one_course_covering_the_step_beats_a_chain_and_a_chain_has_at_most_two() -> None:
    basic, more, full = (
        course("b", {"sql": (0, 0.3)}, hours=2),
        course("m", {"sql": (0.4, 0.7)}, hours=3),
        course("full", {"sql": (0, 0.7)}, hours=6),
    )
    assert [
        p.course.id for p in choose_for_skill(gap("sql"), [basic, more, full], A, CFG, set())
    ] == ["full"]
    assert [p.course.id for p in choose_for_skill(gap("sql"), [basic, more], A, CFG, set())] == [
        "b",
        "m",
    ]
    third = course("t", {"sql": (0.3, 0.5)}, hours=1)
    chain = choose_for_skill(gap("sql", required=1.0), [basic, third, more], A, CFG, set())
    assert len(chain) <= CFG.max_courses_per_skill


def test_a_course_far_bigger_than_the_need_is_only_a_last_resort() -> None:
    huge = course("huge", {"sql": (0, 1.0)}, hours=200)
    small = course("small", {"sql": (0, 0.3)}, hours=3)
    picked = choose_for_skill(gap("sql", hours=10), [huge, small], A, CFG, set())
    assert [p.course.id for p in picked] == ["small"] and "huge" in picked[0].alternatives
    assert [p.course.id for p in choose_for_skill(gap("sql", hours=10), [huge], A, CFG, set())] == [
        "huge"
    ]


def test_scoring_prefers_free_format_certificate_language_and_ties_break_on_cost_hours_id() -> None:
    a = replace(A, formats=("hands_on",), wants_certificate=True, language="ms")
    plain = course("a_plain", {"sql": (0, 0.7)})
    liked = course(
        "z_liked", {"sql": (0, 0.7)}, format=["hands_on"], certificate=True, language=["ms"]
    )
    assert choose_for_skill(gap("sql"), [plain, liked], a, CFG, set())[0].course.id == "z_liked"
    twin_a, twin_b = course("twin_a", {"sql": (0, 0.7)}), course("twin_b", {"sql": (0, 0.7)})
    assert choose_for_skill(gap("sql"), [twin_b, twin_a], A, CFG, set())[0].course.id == "twin_a"
    again = [
        choose_for_skill(gap("sql"), [twin_b, twin_a, plain], A, CFG, set())[0].course.id
        for _ in range(5)
    ]
    assert len(set(again)) == 1


# --- §4.4 order ------------------------------------------------------------------------------


def test_a_skill_never_comes_before_its_prerequisite_in_the_gap() -> None:
    ordered = prerequisite_order([gap("torch"), gap("sql"), gap("py")], VOCAB)
    ids = [g.skill_id for g in ordered]
    assert ids.index("py") < ids.index("torch")
    assert [g.skill_id for g in prerequisite_order([gap("torch")], VOCAB)] == [
        "torch"
    ]  # py already held


OPEN_AI = course("open_ai", {"ai": (0, 0.3)}, hours=1, tags=["ai_literacy"])


@pytest.mark.parametrize(("comfort", "first"), [(3, True), (4, False), (None, False)])
def test_ai_literacy_goes_first_only_at_low_comfort(comfort: int | None, first: bool) -> None:
    p = plan(
        [gap("sql")], [course("s", {"sql": (0, 0.7)}), OPEN_AI], replace(A, ai_comfort=comfort)
    )
    assert (p.steps[0].resource_id == "open_ai") is first
    if first:
        assert "comfort with AI tools 3/10" in p.steps[0].reasons[-1]


def test_ai_untuk_rakyat_style_programme_only_for_people_known_to_be_eligible() -> None:
    courses = [course("s", {"sql": (0, 0.7)}), OPEN_AI, YOUTH]
    eligible = replace(A, ai_comfort=2, age_band="18_30", malaysian="yes")
    assert plan([gap("sql")], courses, eligible).steps[0].resource_id == "y"
    for other in (replace(eligible, age_band="31_45"), replace(eligible, malaysian="prefer_not")):
        assert plan([gap("sql")], courses, other).steps[0].resource_id == "open_ai"


# --- §4.5 schedule ---------------------------------------------------------------------------


def test_weeks_are_packed_with_the_practice_buffer_and_a_milestone_after_core_skills() -> None:
    p = plan(
        [gap("sql"), gap("viz", core=False)],
        [course("s", {"sql": (0, 0.7)}, hours=5), course("v", {"viz": (0, 0.7)}, hours=5)],
    )
    kinds = [s.kind for s in p.steps]
    assert kinds == ["course", "milestone", "course"]
    first = p.steps[0]
    assert first.hours == pytest.approx(5 * (1 + CFG.practice_buffer))  # 6 h at 4 h/week
    assert (first.start_week, first.end_week) == (1, 2)
    assert p.steps[1].resource_id == "m_sql" and p.steps[1].start_week == 2
    assert p.summary.total_hours == pytest.approx(6 + 2 + 6)


def test_steps_past_the_timeframe_stay_in_a_next_phase() -> None:
    p = plan(
        [gap("sql"), gap("viz", core=False)],
        [course("s", {"sql": (0, 0.7)}, hours=30), course("v", {"viz": (0, 0.7)}, hours=30)],
        replace(A, weekly_hours=2, timeframe_weeks=13),
    )
    assert p.steps[0].in_timeframe is False or p.steps[-1].in_timeframe is False
    assert not p.summary.fits_timeframe and all(s.kind for s in p.steps)
    assert len([s for s in p.steps if s.kind == "course"]) == 2  # nothing cut


def test_a_gap_with_no_course_still_appears_with_its_estimated_hours() -> None:
    p = plan([gap("sql", hours=10)], [])
    step = p.steps[0]
    assert step.kind == "no_resource" and "no matching course" in step.title
    assert step.hours == pytest.approx(10 * (1 + CFG.practice_buffer))
    assert p.gaps_without_resources == ["Learn SQL"]


def test_scheduled_hrd_course_gives_an_action_item_and_counts_what_the_employer_may_cover() -> None:
    hrd = HRD.model_copy(update={"delivery": "scheduled"})
    p = plan(
        [gap("sql")],
        [hrd],
        replace(A, employment="employed", employer_hrd="yes", budget="employer_pays"),
    )
    assert p.steps[0].date_to_confirm and p.steps[0].cost_to_user_myr == 0
    assert p.action_items == [
        "Ask HR to apply for the HRD Corp grant via e-TRiS before hrd starts."
    ]
    assert (
        p.summary.cost_possibly_covered_by_employer_myr == 900
        and p.summary.hrd_claimable_steps == 1
    )


def test_the_plan_is_deterministic() -> None:
    courses = [course("s", {"sql": (0, 0.7)}), course("v", {"viz": (0, 0.7)}), OPEN_AI]
    gaps = [gap("sql"), gap("viz", core=False)]
    answers = replace(A, ai_comfort=1)
    assert all(plan(gaps, courses, answers) == plan(gaps, courses, answers) for _ in range(3))
