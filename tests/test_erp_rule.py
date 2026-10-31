"""ERP rule: a CV that names an ERP system gets an `erp` claim with that sentence, once."""

import json
from pathlib import Path
from typing import Any

import pytest

from src import params
from src.config import Settings
from src.intake import extract as extract_mod
from src.pack import load_pack

NUR = (Path(__file__).parent.parent / "data" / "samples" / "nur.txt").read_text(encoding="utf-8")
SAP_SENTENCE = (
    "Applied incoming customer receipts to open invoices in SAP for four entities, about 1,200 "
    "lines a month."
)


def model(skills: list[dict[str, Any]]) -> extract_mod.Complete:
    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        return json.dumps(
            {"current_role": "other", "years_experience": 6, "skills": skills, "interests": []}
        )

    return complete


def test_rule_adds_erp_after_the_model_with_its_sentence(settings: Settings) -> None:
    result = extract_mod.extract(load_pack(), NUR, settings, model([]))
    erp = [s for s in result.skills if s.skill == "erp"]
    assert len(erp) == 1
    assert erp[0].level == params.ERP_RULE_LEVEL
    assert erp[0].evidence == SAP_SENTENCE
    assert "added by rule" in result.note


def test_rule_adds_erp_in_the_keyword_fallback(settings: Settings) -> None:
    result = extract_mod.extract(load_pack(), NUR, settings)
    erp = [s for s in result.skills if s.skill == "erp"]
    assert [(s.level, s.evidence) for s in erp] == [(params.ERP_RULE_LEVEL, SAP_SENTENCE)]
    assert "fallback" in result.note and "added by rule" in result.note


def test_rule_never_duplicates_or_overrides_an_erp_claim(settings: Settings) -> None:
    claim = {"skill": "erp", "level": 3, "evidence": "SAP FI-AR, Microsoft Excel"}
    result = extract_mod.extract(load_pack(), NUR, settings, model([claim]))
    erp = [s for s in result.skills if s.skill == "erp"]
    assert [(s.level, s.evidence) for s in erp] == [(3, "SAP FI-AR, Microsoft Excel")]
    assert "added by rule" not in result.note


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("Posted journals in S/4HANA every month.", True),
        ("Closed the books in AutoCount for three clients.", True),
        ("Raised purchase orders in Dynamics 365 Finance.", True),
        ("Collected information for the sapling project.", False),  # no whole-word alias
        ("Prepared the month-end pack in Excel.", False),
    ],
)
def test_aliases_match_whole_words_only(text: str, found: bool) -> None:
    assert (extract_mod.erp_rule(load_pack(), text, []) is not None) is found
