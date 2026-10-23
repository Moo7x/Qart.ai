"""Intake removes identifiers, keeps only evidenced claims, and labels every fallback."""

import json
from pathlib import Path
from typing import Any

import httpx

from src.config import Settings
from src.intake import extract as extract_mod
from src.intake.pii import scrub
from src.intake.skill_search import bm25, search
from src.pack import load_pack

SAMPLES = Path(__file__).parent.parent / "data" / "samples"


def nur_text() -> str:
    return (SAMPLES / "nur.txt").read_text(encoding="utf-8")


def test_scrub_removes_name_email_phone_and_ic() -> None:
    cleaned = scrub(nur_text())
    for secret in ("Nur Aisyah", "nur.aisyah.sample@example.com", "12-345 6789", "900101-14-5678"):
        assert secret not in cleaned.text
    assert cleaned.removed["name"] == 1
    assert "Cash Application Analyst with 6 years" in cleaned.text  # the work stays


def test_samples_are_marked_synthetic() -> None:
    for path in SAMPLES.glob("*.txt"):
        assert "THIS PERSON DOES NOT EXIST" in path.read_text(encoding="utf-8")


def fake_model(answer: dict[str, Any]) -> extract_mod.Complete:
    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        assert "nur.aisyah.sample@example.com" not in messages[1]["content"]  # scrubbed first
        assert schema["properties"]["skills"]["items"]["properties"]["skill"]["enum"]
        return json.dumps(answer)

    return complete


def test_claims_without_a_real_quote_are_rejected(settings: Settings) -> None:
    answer = {
        "current_role": "cash_application_analyst",
        "years_experience": 6,
        "skills": [
            {
                "skill": "cash_application",
                "level": 3,
                "evidence": "Applied incoming customer receipts to open invoices in SAP",
            },
            {"skill": "sql", "level": 3, "evidence": "Wrote complex SQL queries every day"},
            {"skill": "made_up_skill", "level": 2, "evidence": "anything at all here"},
        ],
        "interests": ["data_digital"],
    }
    result = extract_mod.extract(load_pack(), nur_text(), settings, fake_model(answer))
    assert [s.skill for s in result.skills] == ["cash_application"]
    assert {r["skill"] for r in result.rejected} == {"sql", "made_up_skill"}
    assert result.current_role == "cash_application_analyst"
    assert "schema-constrained" in result.engine


def test_without_a_model_the_keyword_fallback_is_labelled(settings: Settings) -> None:
    result = extract_mod.extract(load_pack(), nur_text(), settings)
    assert result.engine == "BM25 keywords (fallback)"
    assert "fallback" in result.note
    assert result.current_role == "cash_application_analyst"
    assert all(s.level is None for s in result.skills)  # the person sets levels
    assert {"cash_application", "reconciliation"} <= {s.skill for s in result.skills}


def test_a_broken_model_answer_falls_back_without_pretending(settings: Settings) -> None:
    def broken(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        return "not json"

    result = extract_mod.extract(load_pack(), nur_text(), settings, broken)
    assert result.engine == "BM25 keywords (fallback)"
    assert "JSONDecodeError" in result.note


def test_bm25_finds_the_obvious_skill() -> None:
    assert bm25(load_pack(), "bank reconciliation of cash")[0].skill == "reconciliation"


def test_skill_search_falls_back_when_runpod_is_slow(settings: Settings) -> None:
    configured = Settings(**{**settings.__dict__, "runpod_api_key": "k", "runpod_endpoint_id": "e"})

    def cold(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "IN_QUEUE"})

    with httpx.Client(transport=httpx.MockTransport(cold)) as client:
        result = search(load_pack(), "matching receipts to invoices", configured, client)
    assert result.engine == "BM25 keywords (fallback)"
    assert "RunPod unavailable" in result.note


def test_skill_search_uses_runpod_vectors_when_they_arrive(settings: Settings) -> None:
    configured = Settings(**{**settings.__dict__, "runpod_api_key": "k", "runpod_endpoint_id": "e"})
    pack = load_pack()
    target = list(pack.skills).index("sql")

    def warm(request: httpx.Request) -> httpx.Response:
        texts = json.loads(request.content)["input"]["texts"]
        # Query vector [1, 0]; the sql skill gets the same direction, every other skill [0, 1].
        vectors = [[1.0, 0.0]] + [
            [1.0, 0.0] if i == target else [0.0, 1.0] for i in range(len(texts) - 1)
        ]
        return httpx.Response(200, json={"status": "COMPLETED", "output": {"vectors": vectors}})

    from src.intake import skill_search

    skill_search._SKILL_VECTORS.clear()
    with httpx.Client(transport=httpx.MockTransport(warm)) as client:
        result = search(pack, "writing queries", configured, client)
    skill_search._SKILL_VECTORS.clear()
    assert result.engine == "bge-m3 (RunPod)"
    assert result.hits[0].skill == "sql"
