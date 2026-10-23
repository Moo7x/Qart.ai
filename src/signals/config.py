"""Typed view of catalogue/signal_config.json (labelling parameters, sources, events) plus the
tracked skills, which come from the canonical vocabulary in catalogue/skills.json
(entries with trend_tracked: true)."""

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.engine.catalogue import SkillInfo, default_catalogue

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "catalogue" / "signal_config.json"


class SignalParams(BaseModel):
    window_months: int = Field(gt=0)
    ma_short_months: int = Field(gt=0)
    ma_long_months: int = Field(gt=0)
    rising_ma_ratio: float
    rising_change_12m: float
    cooling_ma_ratio: float
    cooling_change_12m: float
    min_mentions_per_month: float = Field(ge=0)
    min_mentions_window_months: int = Field(gt=0)
    index_base: float = Field(gt=0)
    stale_after_days: int = Field(gt=0)
    default_country: str
    default_country_label: str


class SourceInfo(BaseModel):
    source: str
    source_url: str
    license: str
    attribution: str
    update_frequency: str
    caveats: list[str]
    csv_url: str | None = None


class EventMarker(BaseModel):
    month: str  # YYYY-MM
    label: str
    url: str
    verified: bool


class SkillSpec(BaseModel):
    id: str
    name: str
    category: str
    patterns: list[str]
    case_sensitive_patterns: list[str] = []


class SignalConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    about: str = Field(default="", validation_alias="_about")
    params: SignalParams
    sources: dict[str, SourceInfo]
    events: list[EventMarker]
    skills: list[SkillSpec] = []


def tracked_skills(vocabulary: Iterable[SkillInfo] | None = None) -> list[SkillSpec]:
    """Skills with trend_tracked: true from the validated canonical vocabulary."""
    skills = vocabulary if vocabulary is not None else default_catalogue().vocabulary.values()
    return [
        SkillSpec(
            id=s.id,
            name=s.market_name or s.name,
            category=s.category,
            patterns=s.patterns,
            case_sensitive_patterns=s.case_sensitive_patterns,
        )
        for s in skills
        if s.trend_tracked
    ]


def load_config(path: Path = CONFIG_PATH) -> SignalConfig:
    config = SignalConfig.model_validate_json(path.read_text(encoding="utf-8"))
    return config.model_copy(update={"skills": tracked_skills()})


@lru_cache(maxsize=1)
def default_config() -> SignalConfig:
    return load_config()
