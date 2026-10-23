"""The TalentCorp extraction is internally consistent and, when the PDF is present, matches it."""

import re
from functools import cache
from typing import Any

import pytest

from src.collectors import talentcorp
from src.config import REPO_ROOT

PDF = REPO_ROOT / "data" / "raw" / "talentcorp" / "gbs_impact_study_vol2.pdf"
FINANCE_ROLES = 24  # the study's Finance & Accounting cluster, PDF p. 22


@cache
def extraction() -> dict[str, Any]:
    return talentcorp.load_extraction()


def test_finance_cluster_has_24_roles_without_duplicates() -> None:
    roles = extraction()["finance_accounting_roles"]
    names = [r for level in ("high", "medium", "low", "emerging") for r in roles[level]]
    assert len(names) == FINANCE_ROLES
    assert len(set(names)) == len(names)


def test_sixteen_in_demand_skills_eight_per_area() -> None:
    skills = extraction()["in_demand_skills"]
    assert len(skills["ai_digital"]) == len(skills["green"]) == 8


def test_observations_carry_page_references() -> None:
    observations = talentcorp.parse(extraction())
    cash = [o for o in observations if o.entity == "Cash Application Analyst"]
    assert cash[0].value == talentcorp.IMPACT_CODE["high"]
    assert all("PDF p." in o.cited_span for o in observations)


def squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


@pytest.mark.skipif(not PDF.exists(), reason="TalentCorp PDF is kept only in gitignored data/raw")
def test_every_name_appears_on_its_cited_page() -> None:
    from pypdf import PdfReader  # dev-only dependency, used just for this check

    pages = [squash(p.extract_text() or "") for p in PdfReader(PDF).pages]
    data = extraction()
    roles = data["finance_accounting_roles"]
    checks = [
        (r, roles["impact_pdf_page"]) for lvl in ("high", "medium", "low") for r in roles[lvl]
    ]
    checks += [
        (s, data["in_demand_skills"]["pdf_page"])
        for area in ("ai_digital", "green")
        for s in data["in_demand_skills"][area]
    ]
    checks += [(r, data["emerging_roles"]["pdf_page"]) for r in data["emerging_roles"]["roles"]]
    missing = [(name, page) for name, page in checks if squash(name) not in pages[page - 1]]
    assert missing == []
