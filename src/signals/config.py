"""Typed view of catalogue/signal_config.json (skills, labelling parameters, sources, events)."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

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
    profile_tools: list[str] = []  # Profile.preferences.tools values that mean "I use this"
    catalogue_skills: list[str] = []  # catalogue skill ids this market skill relates to


class SignalConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    about: str = Field(default="", validation_alias="_about")
    params: SignalParams
    sources: dict[str, SourceInfo]
    events: list[EventMarker]
    skills: list[SkillSpec]


def load_config(path: Path = CONFIG_PATH) -> SignalConfig:
    return SignalConfig.model_validate_json(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def default_config() -> SignalConfig:
    return load_config()
