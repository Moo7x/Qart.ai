"""Paired-profile test: CVs that differ only in protected attributes get identical results.

Each variant is the same synthetic CV with a different name, gender, religion, race, age, marital
status and contact details. Rule (AGENTS.md): protected attributes never change a result. The
check runs at every stage that could leak them: the scrubbed text, the exact messages the language
model would receive, the keyword fallback, and the ranked roles, gaps and pathways in both
scenarios. Covers labelled lines and the name line; a protected fact written into a free-text
sentence is not removed (documented in docs/explain/journey.md).
"""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.config import Settings
from src.intake import extract as extract_mod
from src.intake.pii import scrub
from src.pack import load_pack

SAMPLE = Path(__file__).parent.parent / "data" / "samples" / "nur.txt"

# Synthetic identities only. Each replaces the four contact lines at the top of the sample CV.
VARIANTS = [
    [
        "Nur Aisyah Binti Kamal",
        "Gender: Female",
        "Religion: Islam",
        "Race: Malay",
        "Date of birth: 01/01/1990",
        "Marital status: Married",
        "Email: nur.aisyah.sample@example.com",
        "Phone: +60 12-345 6789",
        "IC No: 900101-14-5678",
    ],
    [
        "Tan Wei Ming",
        "Gender: Male",
        "Religion: Buddhism",
        "Race: Chinese",
        "Date of birth: 15/06/1975",
        "Marital status: Single",
        "Email: tan.weiming.sample@example.com",
        "Phone: 019-876 5432",
        "IC No: 750615-10-1234",
    ],
    [
        "Rajesh A/L Kumar",
        "Gender: Male",
        "Religion: Hinduism",
        "Race: Indian",
        "Date of birth: 20/03/2001",
        "Marital status: Divorced",
        "Email: rajesh.kumar.sample@example.com",
        "Phone: +6011 2233 4455",
        "IC No: 010320-08-4321",
    ],
]


def variant(header: list[str]) -> str:
    body = SAMPLE.read_text(encoding="utf-8").split("\n")[4:]  # drop the original identity lines
    return "\n".join([*header, *body])


def cvs() -> list[str]:
    return [variant(h) for h in VARIANTS]


def test_variants_really_differ_before_scrubbing() -> None:
    assert len(set(cvs())) == len(VARIANTS)


def test_scrubbed_text_is_identical() -> None:
    scrubbed = [scrub(cv).text for cv in cvs()]
    assert len(set(scrubbed)) == 1
    for word in ("Female", "Islam", "Chinese", "Hinduism", "1975", "Married", "Rajesh"):
        assert word not in scrubbed[0]


def test_model_receives_identical_messages(settings: Settings) -> None:
    pack = load_pack()
    seen: list[str] = []
    answer = {
        "current_role": "cash_application_analyst",
        "years_experience": 6,
        "skills": [
            {
                "skill": "cash_application",
                "level": 3,
                "evidence": "Applied incoming customer receipts to open invoices in SAP",
            }
        ],
        "interests": ["data_digital"],
    }

    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        seen.append(json.dumps(messages))
        return json.dumps(answer)

    results = [extract_mod.extract(pack, cv, settings, complete) for cv in cvs()]
    assert len(set(seen)) == 1
    assert all(r.skills == results[0].skills for r in results)


def test_keyword_fallback_is_identical(settings: Settings) -> None:
    pack = load_pack()
    results = [extract_mod.extract(pack, cv, settings) for cv in cvs()]
    assert "fallback" in results[0].engine
    first = (results[0].current_role, results[0].years_experience, results[0].skills)
    assert all((r.current_role, r.years_experience, r.skills) == first for r in results)


def _journey(client: TestClient, cv: str) -> dict[str, Any]:
    parsed = client.post("/api/intake/parse", json={"text": cv}).json()
    profile = {
        "situation": "working",
        "current_role": parsed["current_role"],
        "years_experience": parsed["years_experience"],
        "weekly_hours": 6,
        "interests": parsed["interests"],
        # Keyword claims come without a level; a fixed self-rating keeps the pair comparable.
        "skills": {
            s["skill"]: {"level": s["level"] or 2, "evidence": s["evidence"], "source": "cv"}
            for s in parsed["skills"]
        },
    }
    created = client.post("/api/profiles", json=profile)
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    out: dict[str, Any] = {"parsed": {k: v for k, v in parsed.items() if k != "removed"}}
    for scenario in ("moderate", "fast"):
        roles = client.get(f"/api/profiles/{pid}/matches", params={"scenario": scenario}).json()
        out[f"roles_{scenario}"] = [
            (r["role_id"], r["fit"], r["gap"], r["essential_gaps"]) for r in roles["roles"]
        ]
        top = roles["roles"][0]["role_id"]
        path = client.get(
            f"/api/profiles/{pid}/pathway", params={"scenario": scenario, "role_id": top}
        ).json()
        out[f"path_{scenario}"] = (
            [s["course"]["id"] for s in path["steps"]],
            path["total_hours"],
            path["fit_after"],
        )
    return out


def test_ranked_roles_gaps_and_pathways_are_identical(client: TestClient) -> None:
    journeys = [_journey(client, cv) for cv in cvs()]
    assert journeys[0]["roles_moderate"]  # the comparison is not vacuous
    assert all(j == journeys[0] for j in journeys)
