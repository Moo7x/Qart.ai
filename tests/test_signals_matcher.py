"""Skill matcher (AI_SIGNAL_SPEC §3): true and false positives for every ambiguous skill."""

import pytest

from src.signals.config import default_config
from src.signals.matcher import compile_skills, skills_in_post

SKILLS = compile_skills(default_config().skills)


def found(text: str) -> set[str]:
    return skills_in_post(text, SKILLS)


@pytest.mark.parametrize(
    ("skill", "positive", "negative"),
    [
        ("sql_basics", "Strong SQL and dbt", "We use NoSQL stores only"),
        ("rag", "Build RAG pipelines", "Drag-and-drop editor; a rag-tag team"),
        ("react", "React and TypeScript front end", "React Native mobile app; react to incidents"),
        (
            "spreadsheet_modelling",
            "Advanced Excel modelling",
            "You excel at ownership; Excel at scale; excellent pay",
        ),
        ("aws", "Deploy on AWS Lambda", "Comply with employment laws"),
        ("nlp", "NLP for search ranking", "nlp-style shorthand in lowercase"),
        ("llms", "Fine-tune LLMs for support", "llms written in lowercase"),
        ("ai_agents", "Ship AI agents for finance ops", "Real estate agent; user agent strings"),
        ("erp", "SAP S/4 and ERP migration", "Reply ASAP; sap and syrup"),
        ("process_automation", "UiPath RPA developer", "rpa lowercase acronym only"),
        ("python", "Python, Django", "Pythonic is not a skill mention"),
        (
            "data_visualisation",
            "Dashboards in Power BI or Tableau",
            "Business intelligence in general",
        ),
        ("mlops", "MLOps on Kubeflow", "Ops team for ML research"),
    ],
)
def test_ambiguous_skill_matches_and_rejects(skill: str, positive: str, negative: str) -> None:
    assert skill in found(positive)
    assert skill not in found(negative)


def test_a_post_counts_once_per_skill_however_often_it_appears() -> None:
    hits = found("Python Python python! SQL, SQL and more SQL. Python again.")
    assert hits >= {"python", "sql_basics"}
    assert len([h for h in hits if h == "python"]) == 1


def test_bare_short_words_are_never_matched() -> None:
    # Go, R and C are not configured skills: noisy counts are worse than a missing skill.
    assert not found("Go to the office. R is fine. C++ maybe. Pick a lane.") & {"go", "r", "c"}
    assert found("Go to the office, R and C") == set()


def test_every_configured_pattern_compiles_and_ids_are_unique() -> None:
    ids = [s.id for s in default_config().skills]
    assert len(ids) == len(set(ids)) == len(SKILLS)
