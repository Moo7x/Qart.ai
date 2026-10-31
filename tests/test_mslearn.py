"""Microsoft Learn candidates: filtered, mapped on (fake) RunPod, never planned until verified."""

from typing import Any

import pytest

from src import params
from src.collectors import mslearn
from src.config import Settings
from src.pack import load_pack

CATALOG: dict[str, Any] = {
    "modules": [
        {
            "uid": "learn.invoice",
            "type": "module",
            "title": "Process vendor invoices",
            "summary": "Post and match vendor invoices.",
            "levels": ["intermediate", "beginner"],
            "subjects": ["finance-accounting"],
            "products": [],
            "duration_in_minutes": 40,
            "url": "https://learn.microsoft.com/en-us/training/modules/invoices/?WT.mc_id=api_CatalogApi",
            "units": ["learn.invoice.intro", "learn.invoice.ex"],
        },
        {
            "uid": "learn.security",
            "type": "module",
            "title": "Secure a firewall",
            "summary": "Network rules.",
            "levels": ["beginner"],
            "subjects": ["security"],
            "products": ["azure-firewall"],
            "duration_in_minutes": 30,
            "url": "https://learn.microsoft.com/en-us/training/modules/firewall/",
            "units": [],
        },
    ],
    "learningPaths": [
        {
            "uid": "learn.path.pbi",
            "type": "learningPath",
            "title": "Build Power BI reports",
            "summary": "Dashboards for finance.",
            "levels": ["advanced"],
            "subjects": [],
            "products": ["power-bi"],
            "duration_in_minutes": 300,
            "url": "https://learn.microsoft.com/en-us/training/paths/pbi/?WT.mc_id=api_CatalogApi",
            "modules": ["learn.invoice"],
        }
    ],
    "units": [
        {"uid": "learn.invoice.intro", "title": "Introduction"},
        {"uid": "learn.invoice.ex", "title": "Exercise - Match an invoice"},
    ],
}


def test_candidates_keep_finance_items_with_clean_urls_and_lowest_level() -> None:
    items = {i.uid: i for i in mslearn.candidates(CATALOG, set())}
    assert set(items) == {"learn.invoice", "learn.path.pbi"}  # the firewall module is filtered out
    invoice = items["learn.invoice"]
    assert invoice.url == "https://learn.microsoft.com/en-us/training/modules/invoices/"
    assert invoice.level == "beginner" and invoice.hands_on
    assert items["learn.path.pbi"].hands_on  # through the exercise in its module


def test_known_urls_are_left_out() -> None:
    known = {"https://learn.microsoft.com/en-us/training/modules/invoices/"}
    assert [i.uid for i in mslearn.candidates(CATALOG, known)] == ["learn.path.pbi"]


def test_mapping_keeps_the_best_above_the_floor(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = load_pack()
    items = mslearn.candidates(CATALOG, set())
    monkeypatch.setattr(mslearn, "embed", lambda s, texts, b, c: [[1.0, 0.0] for _ in texts])

    def fake_rerank(s: Any, query: str, passages: list[str], b: float, c: Any) -> list[float]:
        wanted = query == pack.skills["invoice_processing"].name
        return [0.9 if wanted and "invoice" in p.lower() else 0.001 for p in passages]

    monkeypatch.setattr(mslearn, "rerank", fake_rerank)
    mapped = mslearn.map_skills(settings, pack, items, client=None)  # type: ignore[arg-type]
    assert mapped == {"learn.invoice": {"invoice_processing": 0.9}}
    assert params.CATALOGUE_MIN_RERANK > 0.001  # clear mismatches never become candidates


def test_entries_are_unverified_reading_estimates_and_merge_keeps_verified() -> None:
    items = mslearn.candidates(CATALOG, set())
    fresh = mslearn.entries(items, {"learn.invoice": {"invoice_processing": 0.9}}, "2026-10-30")
    [entry] = fresh
    assert entry["verified"] is False and entry["time_basis"] == "reading_estimate"
    assert entry["covers"] == ["invoice_processing"] and entry["level"] == "beginner"
    verified = {**entry, "id": "mslearn_old", "verified": True}
    merged = mslearn.merge({"courses": [verified, {**entry, "id": "stale"}]}, fresh, "2026-10-31")
    ids = [c["id"] for c in merged["courses"]]
    assert ids == ["mslearn_old", entry["id"]]  # verified kept, stale candidate replaced
    assert merged["checked"] == "2026-10-31"


def test_generated_candidates_are_never_planned() -> None:
    pack = load_pack()
    unverified = {c.id for c in pack.courses.values() if not c.verified}
    planned = {c.id for skill in pack.skills for c in pack.courses_for(skill)}
    assert not unverified & planned
