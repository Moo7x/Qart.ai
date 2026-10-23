"""Typed view of catalogue/ats_companies.json and catalogue/ats_config.json."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from src.engine.catalogue import CATALOGUE_DIR
from src.signals.http import Politeness

COMPANIES_PATH = CATALOGUE_DIR / "ats_companies.json"
CONFIG_PATH = CATALOGUE_DIR / "ats_config.json"
SOURCES = ("greenhouse", "lever", "ashby")


class Company(BaseModel):
    token: str
    name: str
    checked: str | None = None


class HttpSettings(BaseModel):
    user_agent: str
    timeout_s: float
    retries: int
    backoff_s: float
    pause_s: float
    lever_page_size: int

    @property
    def politeness(self) -> Politeness:
        return Politeness(self.timeout_s, self.retries, self.backoff_s, self.pause_s)


class Boilerplate(BaseModel):
    min_share: float  # a sentence in at least this share of a company's postings is boilerplate
    min_postings: int  # only for companies with at least this many postings in the run
    shingle_words: int  # a run of this many consecutive words is the unit of repetition


class AtsConfig(BaseModel):
    http: HttpSettings
    regions: dict[str, str]  # region id -> case-insensitive pattern on the location text
    region_labels: dict[str, str]
    ai_terms: list[str]
    ai_terms_case_sensitive: list[str]
    boilerplate: Boilerplate
    role_families: list[tuple[str, str]]  # (family id, title pattern), first match wins
    min_sample: int
    min_periods_for_chart: int
    snapshot_name: str


def load_companies(path: Path = COMPANIES_PATH) -> dict[str, list[Company]]:
    """Companies per source: the verified list plus anything added under ADD_YOUR_OWN."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    extra = raw.get("ADD_YOUR_OWN", {})
    return {
        s: [Company.model_validate(c) for c in raw["sources"].get(s, []) + extra.get(s, [])]
        for s in SOURCES
    }


@lru_cache(maxsize=1)
def default_ats_config(path: Path = CONFIG_PATH) -> AtsConfig:
    return AtsConfig.model_validate_json(path.read_text(encoding="utf-8"))
