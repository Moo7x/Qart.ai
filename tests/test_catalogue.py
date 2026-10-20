"""Integrity rules for catalogue/*.json: no dangling ids, every role cited, every course checked."""

from src.contract import SCENARIOS
from src.engine.catalogue import checkin_cases_by_skill, default_case_index, default_catalogue

CONTRACT_PRACTISED_SKILLS = {
    "recon_to_source",
    "duplicate_detection",
    "cutoff_timing",
    "unsupported_adjustment",
    "fx_conversion",
    "transposition_check",
    "escalation_judgment",
    "ai_output_review",
}
CONTRACT_FUTURE_SKILLS = {
    "variance_analysis",
    "data_quality",
    "controls_design",
    "process_automation",
    "stakeholder_communication",
    "forecasting",
    "spreadsheet_modelling",
    "sql_basics",
}


def test_skills_match_contract_vocabulary() -> None:
    cat = default_catalogue()
    assert set(cat.practised_skill_ids) == CONTRACT_PRACTISED_SKILLS
    assert set(cat.skills) == CONTRACT_PRACTISED_SKILLS | CONTRACT_FUTURE_SKILLS
    assert all(skill.type_reason for skill in cat.skills.values())


def test_core_oversight_skills_are_oversight() -> None:
    cat = default_catalogue()
    assert cat.skill_type("ai_output_review") == "oversight"
    assert cat.skill_type("escalation_judgment") == "oversight"


def test_every_role_is_based_on_onet_with_url() -> None:
    for role in default_catalogue().roles.values():
        assert role.based_on, role.id
        for basis in role.based_on:
            assert basis.source == "O*NET 31.0"
            assert basis.url == f"https://www.onetonline.org/link/summary/{basis.code}"
        assert {task.onet for task in role.tasks} <= {b.code for b in role.based_on}


def test_role_skills_and_tasks_reference_known_ids() -> None:
    cat = default_catalogue()
    workflow_tasks = set(cat.assumptions_v1.task_descriptions)
    for role in cat.roles.values():
        role_skills = {s.skill_id for s in role.skills}
        assert role_skills <= set(cat.skills), role.id
        for task in role.tasks:
            assert set(task.skills) <= role_skills, (role.id, task.task)
            assert task.workflow_task in workflow_tasks, (role.id, task.workflow_task)


def test_assumptions_allocate_every_task_in_both_scenarios() -> None:
    assumptions = default_catalogue().assumptions_v1
    for scenario in SCENARIOS:
        assert set(assumptions.scenarios[scenario].tasks) == set(assumptions.task_descriptions)
    assert set(assumptions.shift_fractions) == set(SCENARIOS)


def test_courses_reference_known_skills_and_prerequisites() -> None:
    cat = default_catalogue()
    for course in cat.courses.values():
        assert set(course.skills) <= set(cat.skills), course.id
        assert set(course.prerequisites) <= set(cat.courses), course.id
        assert course.url.startswith("https://")
        assert course.hours > 0
        assert course.hours_source


def test_unverified_courses_explain_why() -> None:
    for course in default_catalogue().courses.values():
        if not course.verified:
            assert course.verification_note, course.id


def test_sdg_map_covers_all_roles_and_skills() -> None:
    cat = default_catalogue()
    target_ids = {t.id for t in cat.sdg.targets}
    assert {t.id for t in cat.sdg.targets if t.main} == {"4.4"}
    assert set(cat.sdg.roles) == set(cat.roles)
    assert set(cat.sdg.skills) == set(cat.skills)
    for link in [*cat.sdg.roles.values(), *cat.sdg.skills.values()]:
        assert set(link.targets) <= target_ids
    for role in cat.roles.values():
        assert role.sdg_targets == cat.sdg.roles[role.id].targets


def test_case_index_uses_known_skills_and_covers_the_golden_journey() -> None:
    cat = default_catalogue()
    cases = default_case_index()
    ids = {c.id for c in cases}
    assert {"case_001", "case_003", "case_006", "case_007", "checkin_001", "checkin_002"} <= ids
    for case in cases:
        assert set(case.skills) <= set(cat.practised_skill_ids), case.id
    assert checkin_cases_by_skill(cases)["unsupported_adjustment"][:2] == [
        "checkin_001",
        "checkin_002",
    ]
