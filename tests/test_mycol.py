"""The MyCOL extraction is complete, linked to field ISCO groups and, with the PDF, on its pages."""

import re

import pytest

from src.collectors import mycol
from src.config import REPO_ROOT
from src.evidence.field import field_profile

PDF = REPO_ROOT / "data" / "raw" / "mycol" / "MyMahir-MyCOL-20242025-Brochure.pdf"


def test_list_has_66_critical_and_9_persistent_occupations() -> None:
    data = mycol.load_extraction()
    names = data["critical_occupations"]["names"]
    assert len(names) == len(set(names)) == 66
    assert len(data["persistent"]["names"]) == 9
    assert set(data["persistent"]["names"]) <= set(names)


def test_field_links_name_listed_occupations_of_field_groups() -> None:
    data = mycol.load_extraction()
    assert set(data["field_links"]) <= field_profile().isco_codes()
    assert set(data["field_links"].values()) <= set(data["critical_occupations"]["names"])


def test_observations_cite_their_page() -> None:
    observations = mycol.parse(mycol.load_extraction())
    assert len(observations) == 75 and all("PDF p." in o.cited_span for o in observations)


def squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


@pytest.mark.skipif(not PDF.exists(), reason="MyCOL brochure is kept only in gitignored data/raw")
def test_every_name_appears_on_its_cited_page() -> None:
    from pypdf import PdfReader

    pages = [squash(p.extract_text() or "") for p in PdfReader(PDF).pages]
    data = mycol.load_extraction()
    for part in ("critical_occupations", "persistent"):
        page = pages[data[part]["pdf_page"] - 1]
        missing = [n for n in data[part]["names"] if squash(n) not in page]
        assert not missing, missing
