"""The field profile of the pack in use (which occupations the evidence layer follows)."""

from functools import cache

import yaml
from pydantic import BaseModel

from src.config import REPO_ROOT

PACK_DIR = REPO_ROOT / "data" / "packs" / "gbs_fa"


class Occupation(BaseModel):
    code: str
    name: str
    isco: str | None = None  # ISCO-08 unit group via the ESCO–O*NET crosswalk (None = no match)
    esco: str | None = None  # the ESCO occupation that links them
    esco_match: str | None = None  # exactMatch | closeMatch | broadMatch (ESCO crosswalk type)
    esco_uri: str | None = None


class FieldProfile(BaseModel):
    id: str
    name: str
    country: str
    soc_occupations: list[Occupation]
    dosm_job_ad_occupations: list[str]

    def soc_codes(self) -> set[str]:
        return {o.code for o in self.soc_occupations}

    def occupation(self, soc: str) -> Occupation | None:
        return next((o for o in self.soc_occupations if o.code == soc), None)

    def isco_codes(self) -> set[str]:
        return {o.isco for o in self.soc_occupations if o.isco}


@cache
def field_profile() -> FieldProfile:
    raw = yaml.safe_load((PACK_DIR / "field.yaml").read_text(encoding="utf-8"))
    return FieldProfile.model_validate(raw)
