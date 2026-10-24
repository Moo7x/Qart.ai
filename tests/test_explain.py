"""Explanations only rephrase computed facts: no digits, every sentence cites a known fact."""

import json
from typing import Any

from fastapi.testclient import TestClient

from src.config import Settings
from src.match.engine import Evidence, score_role
from src.match.explain import explain, facts
from src.pack import load_pack
from src.pathway.planner import plan_pathway

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="test")
LEVELS: dict[str, int | None] = {"general_ledger": 3, "accounting_principles": 2, "reporting": 2}


def fact_list() -> list[dict[str, str]]:
    pack = load_pack()
    match = score_role(
        pack, pack.destination_roles["cost_accountant"], LEVELS, "moderate", EVIDENCE
    )
    path = plan_pathway(pack, match, LEVELS, 6, "moderate", EVIDENCE)
    return facts(match, path, "Moderate")


def model(sentences: list[dict[str, Any]]) -> Any:
    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        assert "Never write a number" in messages[0]["content"]
        assert schema["properties"]["sentences"]["items"]["properties"]["facts"]["items"]["enum"]
        return json.dumps({"sentences": sentences})

    return complete


def test_sentences_with_digits_or_without_known_facts_are_dropped(settings: Settings) -> None:
    answer = [
        {"text": "Your fit is held back by standard costing.", "facts": ["fit", "skill1"]},
        {"text": "You score 43 here.", "facts": ["fit"]},  # a number: dropped
        {"text": "This sounds great.", "facts": []},  # no fact: dropped
        {"text": "Something unrelated.", "facts": ["made_up"]},  # unknown fact: dropped
        {"text": "You score forty-three of one hundred.", "facts": ["fit"]},  # number words
    ]
    result = explain(fact_list(), settings, model(answer))
    assert [s["text"] for s in result["sentences"]] == [
        "Your fit is held back by standard costing."
    ]
    assert result["sentences"][0]["facts"][0]["text"].startswith("Fit for Cost Accountant is")
    assert "4 sentence(s) removed" in result["note"] and "gpt-4o-mini" in result["engine"]


def test_nothing_valid_or_no_key_gives_a_labelled_template(settings: Settings) -> None:
    rejected = explain(fact_list(), settings, model([{"text": "Score 10.", "facts": ["fit"]}]))
    assert rejected["engine"] == "template (fallback)" and rejected["sentences"]
    offline = explain(fact_list(), settings)
    assert offline["engine"] == "template (fallback)"
    assert offline["note"] == "no language model configured; computed facts shown instead"


def test_explain_route_uses_the_profile(client: TestClient) -> None:
    from tests.test_api_journey import create

    pid = create(client)
    body = client.get(f"/api/profiles/{pid}/roles/cost_accountant/explain").json()
    assert body["engine"] == "template (fallback)"  # tests never call the paid model
    assert body["sentences"][0]["facts"][0]["id"] == "fit"
    assert client.get(f"/api/profiles/{pid}/roles/nope/explain").status_code == 404


def test_fact_ids_echoed_into_the_text_are_removed(settings: Settings) -> None:
    answer = [{"text": "Essential skills hold this role back (fit, essentials).", "facts": ["fit"]}]
    result = explain(fact_list(), settings, model(answer))
    assert result["sentences"][0]["text"] == "Essential skills hold this role back."


def test_forecast_or_promise_sentences_are_dropped(settings: Settings) -> None:
    answer = [
        {"text": "Demand for this role is expected to rise.", "facts": ["fit"]},
        {"text": "This pathway will secure the job.", "facts": ["pathway"]},
        {"text": "Your general ledger skill helps most.", "facts": ["skill1"]},
    ]
    result = explain(fact_list(), settings, model(answer))
    assert [s["text"] for s in result["sentences"]] == ["Your general ledger skill helps most."]
