import json

from src.collectors import ai_resources as ar

TEXT = (
    "Invoice processing means matching each supplier invoice to its purchase order. "
    "With Copilot in Dynamics 365 Finance, AI matches the invoice lines and flags exceptions."
)
TARGET = {"name": "Invoice processing", "tasks": ["Match invoices to purchase orders."]}
COURSE = {"kind": "course", "url": "https://example.org", "title": "T", "provider": "P"}


def _answer(skill: str, ai: str):
    return lambda messages, schema: json.dumps(
        {"teaches_skill": "yes", "skill_quote": skill, "applies_ai": "yes", "ai_quote": ai}
    )


def test_a_resource_is_kept_only_when_both_quotes_are_found() -> None:
    both = ar.judge(
        COURSE,
        TARGET,
        _answer(
            "matching each supplier invoice to its purchase order",
            "AI matches the invoice lines and flags exceptions",
        ),
        lambda url: TEXT,
        lambda v: [],
    )
    assert both["label"] == 1
    no_ai = ar.judge(
        COURSE,
        TARGET,
        _answer(
            "matching each supplier invoice to its purchase order",
            "an AI sentence that is not on the page at all",
        ),
        lambda url: TEXT,
        lambda v: [],
    )
    assert no_ai["label"] == 0 and no_ai["ai_quote"] == ""
    assert ar.judge(COURSE, TARGET, _answer("x", "y"), lambda url: "", lambda v: [])["label"] == 0


def test_precision_at_k_counts_labelled_items_in_each_top_k() -> None:
    group = [{"label": 1, "s": 3}, {"label": 0, "s": 2}, {"label": 1, "s": 1}, {"label": 0, "s": 0}]
    assert ar.precision_at([group], lambda c: c["s"]) == round(2 / 3, 3)
    assert ar.precision_at([group], lambda c: -c["s"]) == round(1 / 3, 3)


def test_the_ranker_is_fitted_only_with_enough_labels_of_both_kinds() -> None:
    few = [{"features": [0.1, 0.1, 1, 1, 2], "label": 1}] * 5
    assert ar.fit_ranker(few)[0] is None
    many = [
        {"features": [s, a, 1.0, 1.0, 2.0], "label": int(a > 0.5)}
        for s in (0.2, 0.4, 0.6, 0.8)
        for a in (0.1, 0.3, 0.6, 0.7, 0.8, 0.9, 0.2, 0.95)
    ]
    model, report = ar.fit_ranker(many)
    assert model is not None and report["coefficients"]["ai_score"] > 0


def test_an_ai_quote_that_does_not_name_ai_is_not_enough() -> None:
    text = TEXT + " In this module, you'll use real-time input variables instead of fixed values."
    result = ar.judge(
        COURSE,
        TARGET,
        _answer(
            "matching each supplier invoice to its purchase order",
            "you'll use real-time input variables instead of fixed values",
        ),
        lambda url: text,
        lambda v: [],
    )
    assert result["label"] == 0


def test_a_general_ai_course_that_never_names_the_skill_is_not_kept() -> None:
    text = "Explore how finance teams use AI-powered agents to work faster across operations today."
    result = ar.judge(
        COURSE,
        TARGET,
        _answer(
            "finance teams use AI-powered agents to work faster",
            "finance teams use AI-powered agents to work faster",
        ),
        lambda url: text,
        lambda v: [],
    )
    assert result["label"] == 0
    assert ar.skill_stems("Reconciliation Processes") == ["recon", "proce"]
