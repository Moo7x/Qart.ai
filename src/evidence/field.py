"""The field profile of the pack in use (which occupations the evidence layer follows)."""

from functools import cache

import yaml
from pydantic import BaseModel

from src.config import REPO_ROOT

PACK_DIR = REPO_ROOT / "data" / "packs" / "gbs_fa"


class Occupation(BaseModel):
    code: str
    name: str


class FieldProfile(BaseModel):
    id: str
    name: str
    country: str
    soc_occupations: list[Occupation]
    dosm_job_ad_occupations: list[str]

    def soc_codes(self) -> set[str]:
        return {o.code for o in self.soc_occupations}


@cache
def field_profile() -> FieldProfile:
    raw = yaml.safe_load((PACK_DIR / "field.yaml").read_text(encoding="utf-8"))
    return FieldProfile.model_validate(raw)
