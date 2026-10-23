"""Derived learn_hours (pathway.md §3.4): medians of verified courses per level step."""

from src.contract import Course, SkillStep
from src.engine.catalogue import LearnHours, SkillInfo
from src.engine.learn_hours import derived_hours

SKILL = SkillInfo(
    id="sql", name="SQL", practised=False, learn_hours=LearnHours(to_basic=10, to_confident=30)
)


def course(
    cid: str, hours: float, frm: float, to: float, status: str = "verified", extra: int = 0
) -> Course:
    steps = [SkillStep(id="sql", from_level=frm, to_level=to)] + [
        SkillStep(id=f"x{i}", from_level=0, to_level=0.3) for i in range(extra)
    ]
    return Course(
        id=cid,
        title=cid,
        provider="p",
        url="https://x",
        hours=hours,
        cost="free",
        skills=[s.id for s in steps],
        retrieved="2026-10-23",
        skill_steps=steps,
        status=status,
    )  # type: ignore[arg-type]


def test_median_per_step_uses_the_skill_share_and_verified_courses_only() -> None:
    courses = [
        course("a", 8, 0, 0.7),
        course("b", 12, 0, 0.7),
        course("c", 40, 0, 0.7, extra=1),  # 20 h for sql
        course("d", 99, 0, 0.7, status="draft"),  # ignored
        course("e", 24, 0.7, 1.0),
        course("f", 3, 0, 0.3),  # does not reach "use sometimes": no sample
    ]
    assert derived_hours({"sql": SKILL}, courses)["sql"] == {"to_basic": 12, "to_confident": 24}


def test_a_full_course_is_split_between_both_steps() -> None:
    got = derived_hours({"sql": SKILL}, [course("g", 40, 0, 1.0)])["sql"]
    assert got == {"to_basic": 10, "to_confident": 30}  # 40 h split 10 : 30 like the estimate


def test_no_course_means_no_derived_value() -> None:
    assert derived_hours({"sql": SKILL}, [])["sql"] == {"to_basic": None, "to_confident": None}
