"""The source registry (data/sources.yaml): what each source shows, its terms and cadence."""

from functools import cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from src.config import REPO_ROOT

REGISTRY_PATH = REPO_ROOT / "data" / "sources.yaml"


class Source(BaseModel):
    """One registered source. Only registered sources feed observations."""

    id: str
    name: str
    publisher: str
    family: str
    url: str
    docs_url: str
    terms: str
    terms_url: str
    terms_checked: str | None
    attribution: str
    tier: Literal["A", "B", "C"]
    cadence: str
    collector: str
    shows: str
    does_not_show: str
    notes: str = ""


def load_registry(path: Path = REGISTRY_PATH) -> list[Source]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = [Source.model_validate(item) for item in raw]
    ids = [s.id for s in sources]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate source ids in {path}")
    return sources


@cache
def registry() -> dict[str, Source]:
    """Registry keyed by id, read once per process."""
    return {s.id: s for s in load_registry()}
