"""Learning resources for the plan (pathway.md §3): which courses the plan may use, and the
hands-on milestones it places between them.

By default the plan uses verified courses only (a team member checked the page). Setting the
environment variable SHOW_DRAFT_RESOURCES=true also offers drafts, which the UI badges "Draft";
it is a development flag and must stay off in the demo build.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from src.contract import Course
from src.engine.catalogue import CATALOGUE_DIR, Catalogue

MILESTONES_PATH = CATALOGUE_DIR / "milestones.json"
DRAFT_FLAG = "SHOW_DRAFT_RESOURCES"


class Milestone(BaseModel):
    id: str
    title: str
    skills: list[str]
    hours: float
    case_id: str | None = None  # a Qart practice case, where one exists


class MilestoneCatalogue(BaseModel):
    milestones: list[Milestone]
    default: Milestone  # used when no milestone matches the skill just learned


@lru_cache(maxsize=1)
def default_milestones(path: Path = MILESTONES_PATH) -> MilestoneCatalogue:
    return MilestoneCatalogue.model_validate_json(path.read_text(encoding="utf-8"))


def show_drafts() -> bool:
    return os.environ.get(DRAFT_FLAG, "").lower() in {"1", "true", "yes"}


def plan_courses(catalogue: Catalogue, include_drafts: bool | None = None) -> list[Course]:
    """Courses the plan may choose from: verified ones, plus drafts when the dev flag is on."""
    drafts = show_drafts() if include_drafts is None else include_drafts
    return [c for c in catalogue.courses.values() if c.status == "verified" or drafts]
