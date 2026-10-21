"""Course candidates from the public Microsoft Learn Catalog API (RAG preparation).

Source: https://learn.microsoft.com/api/catalog/?type=modules,learningPaths&locale=en-us
(no authentication; offered under the Microsoft APIs Terms of Use, no charge; the documented use
case is to "pull a list ... in order to link to them"). Microsoft Learn training is free (Microsoft
Learn FAQ). We store metadata and links only.

The candidates are written to catalogue/course_candidates_mslearn.json with status "candidate".
**The path planner must not use them until a human approves them** (they are not in courses.json).

Selection rule (declared): level "beginner", at least one business-facing role, and either a
finance/office product (Excel, Power BI, Power Automate, Dynamics 365 Finance), a finance keyword
in the title, or an AI-fundamentals / responsible-AI title.

Run:  python -m src.retrieval.mslearn [--offline]
"""

import argparse
import json
import re
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from src.engine.catalogue import REPO_ROOT

CATALOG_URL = "https://learn.microsoft.com/api/catalog/?type=modules,learningPaths&locale=en-us"
TERMS_URL = "https://learn.microsoft.com/en-us/legal/microsoft-apis/terms-of-use"
RAW_PATH = REPO_ROOT / "data" / "raw" / "mslearn_catalog" / "catalog_modules_paths_en-us.json"
CANDIDATES_PATH = REPO_ROOT / "catalogue" / "course_candidates_mslearn.json"
MINUTES_PER_HOUR = 60
HOURS_DECIMALS = 1

BEGINNER = "beginner"
BUSINESS_ROLES = frozenset(
    {"business-user", "business-analyst", "data-analyst", "business-owner", "business-leader"}
    | {"auditor"}
)
# Product → skills it most plausibly supports (hints for a human reviewer, not evidence).
PRODUCT_SKILLS: dict[str, list[str]] = {
    "office-excel": ["spreadsheet_modelling"],
    "power-bi": ["variance_analysis", "data_quality"],
    "power-automate": ["process_automation"],
    "dynamics-finance": ["variance_analysis"],
}
FINANCE_TITLE = re.compile(r"\b(financ\w*|accounting|reconcil\w*)\b", re.IGNORECASE)
AI_TITLE = re.compile(
    r"(introduction to (generative )?ai|ai concepts|responsible (generative )?ai|"
    r"fundamentals of (generative )?ai|ai fundamentals)",
    re.IGNORECASE,
)


def fetch_catalog(dest: Path = RAW_PATH, url: str = CATALOG_URL) -> Path:
    """Download the catalog JSON into gitignored data/raw/ (about 7 MB)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)  # noqa: S310 (fixed https URL)
    return dest


def skill_hints(item: dict[str, Any]) -> list[str]:
    hints = [s for p in item.get("products", []) for s in PRODUCT_SKILLS.get(p, [])]
    if FINANCE_TITLE.search(item["title"]):
        hints.append("variance_analysis")
    if AI_TITLE.search(item["title"]):
        hints.append("ai_output_review")
    return sorted(set(hints))


def is_candidate(item: dict[str, Any]) -> bool:
    if BEGINNER not in item.get("levels", []):
        return False
    if not BUSINESS_ROLES & set(item.get("roles", [])):
        return False
    return bool(set(item.get("products", [])) & PRODUCT_SKILLS.keys()) or bool(
        FINANCE_TITLE.search(item["title"]) or AI_TITLE.search(item["title"])
    )


def to_candidate(item: dict[str, Any], retrieved: str) -> dict[str, Any]:
    minutes = item.get("duration_in_minutes") or 0
    return {
        "id": f"mslearn:{item['uid']}",
        "title": item["title"],
        "type": item["type"],
        "provider": "Microsoft Learn",
        "url": item["url"],
        "duration_in_minutes": minutes,
        "hours": round(minutes / MINUTES_PER_HOUR, HOURS_DECIMALS),
        "levels": item.get("levels", []),
        "roles": item.get("roles", []),
        "products": item.get("products", []),
        "last_modified": item.get("last_modified"),
        "skill_hints": skill_hints(item),
        "cost": "free",
        "cost_source": "Microsoft Learn FAQ: 'Microsoft Learn training is free'",
        "language": "en",
        "retrieved": retrieved,
        "status": "candidate",
    }


def select_candidates(catalog: dict[str, Any], retrieved: str) -> list[dict[str, Any]]:
    items = catalog.get("modules", []) + catalog.get("learningPaths", [])
    chosen = [to_candidate(i, retrieved) for i in items if is_candidate(i)]
    return sorted(chosen, key=lambda c: (c["type"], c["title"]))


def write_candidates(
    candidates: list[dict[str, Any]], retrieved: str, path: Path = CANDIDATES_PATH
) -> None:
    doc = {
        "_about": (
            "CANDIDATES ONLY, not approved: the path planner must not use these until Person A's "
            "teammate/human reviewer approves them and moves chosen items into courses.json with "
            "a verification. Metadata from the Microsoft Learn Catalog API (free, no key, "
            "Microsoft APIs Terms of Use); we only link to the training."
        ),
        "source": CATALOG_URL,
        "terms": TERMS_URL,
        "retrieved": retrieved,
        "selection_rule": (
            "level beginner; a business-facing role; and a finance/office product (Excel, Power "
            "BI, Power Automate, Dynamics 365 Finance), a finance keyword in the title, or an "
            "AI-fundamentals / responsible-AI title"
        ),
        "candidates": candidates,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="use the raw file in data/raw")
    args = parser.parse_args()
    if not args.offline or not RAW_PATH.exists():
        fetch_catalog()
    retrieved = date.today().isoformat()
    catalog = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    candidates = select_candidates(catalog, retrieved)
    write_candidates(candidates, retrieved)
    print(f"wrote {len(candidates)} candidates to {CANDIDATES_PATH}")


if __name__ == "__main__":
    main()
