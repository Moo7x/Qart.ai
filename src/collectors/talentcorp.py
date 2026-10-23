"""TalentCorp GBS study (2024): expert-assessed impact per role, in-demand skills, emerging roles.

A one-off, versioned extraction: facts were read by hand into data/packs/gbs_fa/talentcorp_2024.yaml
with their page numbers (the study is "all rights reserved", so no text is reproduced). This
collector turns that file into observations; it needs no network.
"""

from typing import Any

import httpx
import yaml

from src.collectors.base import CollectorResult, SourceState
from src.evidence.field import PACK_DIR
from src.evidence.registry import registry
from src.evidence.store import Observation

SOURCE_ID = "talentcorp_gbs_2024"
EXTRACTION = PACK_DIR / "talentcorp_2024.yaml"
# Impact is categorical; it is stored as an ordered code so it fits the numeric value column.
IMPACT_CODE = {"low": 1.0, "medium": 2.0, "high": 3.0, "emerging": 0.0}
IMPACT_UNIT = "impact level (0 emerging, 1 low, 2 medium, 3 high)"


def load_extraction() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(EXTRACTION.read_text(encoding="utf-8"))
    return data


def parse(data: dict[str, Any]) -> list[Observation]:
    url = registry()[SOURCE_ID].url
    version = str(data["version"])
    published = str(data["published"])

    def fact(series: str, entity: str, value: float, unit: str, where: str) -> Observation:
        return Observation(
            source_id=SOURCE_ID,
            series=series,
            entity=entity,
            geography="MYS",
            period=published,
            value=value,
            unit=unit,
            url=url,
            cited_span=f"{where} · {data['document']}",
            method_version=version,
            published=published,
        )

    counts = data["study_counts"]
    where = f"PDF p. {counts['pdf_page']} (printed pp. {counts['printed']})"
    observations = [
        fact("talentcorp_roles_by_impact", level, float(counts[f"{level}_impact"]), "roles", where)
        for level in ("high", "medium", "low")
    ]
    observations.append(
        fact(
            "talentcorp_roles_by_impact",
            "emerging",
            float(counts["emerging_roles"]),
            "roles",
            where,
        )
    )
    roles = data["finance_accounting_roles"]
    for level, code in IMPACT_CODE.items():
        for role in roles[level]:
            observations.append(
                fact(
                    "talentcorp_role_impact",
                    role,
                    code,
                    IMPACT_UNIT,
                    f"Finance & Accounting · {level} impact · PDF p. {roles['impact_pdf_page']}",
                )
            )
    skills = data["in_demand_skills"]
    for area in ("ai_digital", "green"):
        for skill in skills[area]:
            observations.append(
                fact(
                    "talentcorp_in_demand_skill",
                    skill,
                    1.0,
                    "listed (1 = yes)",
                    f"In-demand skills · {area} · PDF p. {skills['pdf_page']}",
                )
            )
    emerging = data["emerging_roles"]
    for role in emerging["roles"]:
        observations.append(
            fact(
                "talentcorp_emerging_role",
                role,
                1.0,
                "listed (1 = yes)",
                f"Emerging roles · PDF p. {emerging['pdf_page']}",
            )
        )
    return observations


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    data = load_extraction()
    return CollectorResult(parse(data), note=f"versioned extraction {data['version']}")
