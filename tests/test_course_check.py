"""The automatic course check verifies a course only when the model's quote is on its own page."""

import json
from pathlib import Path
from typing import Any

import yaml

from src.collectors import course_check
from src.config import Settings

PAGE = "In this module you will learn how to process vendor invoices and match them to orders."


def candidates(tmp_path: Path, *courses: dict[str, Any]) -> Path:
    path = tmp_path / "courses_open.yaml"
    path.write_text("# header\n" + yaml.safe_dump({"courses": list(courses)}), encoding="utf-8")
    return path


def course(course_id: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": course_id,
        "title": "Processing vendor invoices",
        "provider": "Microsoft Learn",
        "url": f"https://example.org/{course_id}",
        "covers": ["invoice_processing"],
        "verified": False,
        **extra,
    }


def answering(verdict: str, quote: str) -> Any:
    calls: list[int] = []

    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        calls.append(1)
        return json.dumps({"verdict": verdict, "quote": quote, "reason": "test"})

    complete.calls = calls  # type: ignore[attr-defined]
    return complete


def run(tmp_path: Path, settings: Settings, complete: Any, page: str = PAGE, **kw: Any) -> list:
    course_check.run(
        settings,
        reader=lambda url: page,
        complete=complete,
        files=("courses_open.yaml",),
        pack_dir=tmp_path,
        **kw,
    )
    return yaml.safe_load((tmp_path / "courses_open.yaml").read_text(encoding="utf-8"))["courses"]


def test_a_fit_with_a_quote_from_the_page_is_verified(tmp_path: Path, settings: Settings) -> None:
    candidates(tmp_path, course("a"))
    quote = "you will learn how to process vendor invoices"
    [out] = run(tmp_path, settings, answering("fits", quote))
    assert out["verified"] is True
    assert out["fit_check"]["result"] == "fits" and out["fit_check"]["quote"] == quote
    assert out["fit_check"]["by"] == settings.llm_model


def test_a_quote_that_is_not_on_the_page_never_verifies(tmp_path: Path, settings: Settings) -> None:
    candidates(tmp_path, course("a"))
    [out] = run(tmp_path, settings, answering("fits", "covers three-way matching in depth"))
    assert out["verified"] is False and out["fit_check"]["result"] == "unclear"


def test_does_not_fit_stays_a_candidate(tmp_path: Path, settings: Settings) -> None:
    candidates(tmp_path, course("a"))
    [out] = run(tmp_path, settings, answering("does_not_fit", ""))
    assert out["verified"] is False and out["fit_check"]["result"] == "does_not_fit"


def test_an_empty_page_is_unclear_without_asking_the_model(
    tmp_path: Path, settings: Settings
) -> None:
    candidates(tmp_path, course("a"))
    complete = answering("fits", "anything at all here")
    [out] = run(tmp_path, settings, complete, page="")
    assert out["fit_check"]["result"] == "unclear" and complete.calls == []


def test_checked_courses_are_skipped_unless_rechecked(tmp_path: Path, settings: Settings) -> None:
    done = {"result": "does_not_fit", "by": "gpt-4o-mini", "quote": "", "checked": "2026-10-31"}
    candidates(tmp_path, course("a", fit_check=done))
    complete = answering("fits", "you will learn how to process vendor invoices")
    run(tmp_path, settings, complete)
    assert complete.calls == []
    [out] = run(tmp_path, settings, complete, recheck=True)
    assert out["verified"] is True and complete.calls == [1]


def test_a_course_keeps_only_the_skills_its_page_shows(tmp_path: Path, settings: Settings) -> None:
    candidates(tmp_path, course("a", covers=["invoice_processing", "fpa"]))
    quote = "you will learn how to process vendor invoices"

    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        fits = "Invoice Processing" in messages[1]["content"]
        verdict = "fits" if fits else "does_not_fit"
        return json.dumps({"verdict": verdict, "quote": quote if fits else "", "reason": "t"})

    [out] = run(tmp_path, settings, complete)
    assert out["verified"] is True and out["covers"] == ["invoice_processing"]
    assert out["fit_check"]["skills_removed"] == ["fpa"]
