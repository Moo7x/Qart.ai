"""Microsoft Learn catalogue → candidate courses for the pack's skills (docs/PHASE2_PLAN.md A6).

    .venv/Scripts/python.exe -m src.collectors.mslearn

1. Fetch the public Microsoft Learn Catalog API (free, no key): modules, learning paths and their
   units, each with title, summary, levels, duration and URL.
2. Keep the items about finance, data analysis and process work, or about the finance tools the
   pack's roles use (Dynamics 365 Finance and Business Central, Power BI, Power Automate, Excel).
3. Map items to skills on RunPod: BGE-M3 embeds every item and every skill; for each skill the
   CATALOGUE_SHORTLIST most similar items go to the reranker (query: the skill name), and its
   CATALOGUE_TOP_PER_SKILL best above CATALOGUE_MIN_RERANK cover the skill (an item lists at most
   CATALOGUE_MAX_SKILLS_PER_ITEM skills).
4. Write data/packs/gbs_fa/courses_mslearn.yaml. Every entry is a candidate (`verified: false`):
   the planner never uses it until a reviewer opens it and marks it verified
   (scripts/review_catalogue.py). Items already in courses.yaml are left out.

The file is generated and reviewed in the repository rather than by the scheduled pipeline,
because the pack is read from files; a rerun replaces candidates but keeps every verified entry.
Durations are Microsoft's reading estimates (`time_basis: reading_estimate`); `hands_on` is true
only when the item has a unit titled "Exercise …" (for a learning path, in any of its modules).
"""

import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from src import http, params
from src.config import Settings, load_settings
from src.envfile import load_env_file
from src.evidence.field import PACK_DIR
from src.pack import Pack, load_pack
from src.runpod_jobs import BACKGROUND_BUDGET_SECONDS, embed, rerank

API_URL = "https://learn.microsoft.com/api/catalog/"
OUT = PACK_DIR / "courses_mslearn.yaml"
PROVIDER = "Microsoft Learn"
SUBJECTS = {"finance-accounting", "data-analytics", "data-modeling", "process-workflow"}
PRODUCTS = {
    "dynamics-finance",
    "dynamics-business-central",
    "power-bi",
    "power-automate",
    "office-excel",
}
LEVEL_ORDER = ("beginner", "intermediate", "advanced")
TRACKING = re.compile(r"\?WT\.mc_id=[^&#]*")
EXERCISE = re.compile(r"^\s*exercise\b", re.I)
SKILL_CONTEXT = "a skill for finance and accounting roles in a Malaysian shared-services centre"


@dataclass
class Item:
    uid: str
    title: str
    summary: str
    url: str
    minutes: int
    level: str
    hands_on: bool

    def text(self) -> str:
        return f"{self.title}. {self.summary}"


def fetch(client: httpx.Client) -> dict[str, Any]:
    response = client.get(
        API_URL, params={"locale": "en-us", "type": "modules,learningPaths,units"}, timeout=120
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def candidates(catalog: dict[str, Any], known_urls: set[str]) -> list[Item]:
    """Finance, data and process items, with their lowest level and the hands-on flag."""
    unit_titles = {u["uid"]: u.get("title", "") for u in catalog.get("units", [])}
    modules = {m["uid"]: m for m in catalog.get("modules", [])}

    def has_exercise(item: dict[str, Any]) -> bool:
        units = list(item.get("units", []))
        for child in item.get("modules", []):  # a learning path lists its modules
            units += modules.get(child, {}).get("units", [])
        return any(EXERCISE.match(unit_titles.get(u, "")) for u in units)

    out = []
    for item in [*catalog.get("modules", []), *catalog.get("learningPaths", [])]:
        if not (
            set(item.get("subjects", [])) & SUBJECTS or set(item.get("products", [])) & PRODUCTS
        ):
            continue
        url = TRACKING.sub("", item.get("url", ""))
        levels = [lvl for lvl in LEVEL_ORDER if lvl in item.get("levels", [])]
        if not url.startswith("https://") or url in known_urls or not levels:
            continue
        out.append(
            Item(
                uid=item["uid"],
                title=item["title"].strip(),
                summary=(item.get("summary") or "").strip(),
                url=url,
                minutes=int(item.get("duration_in_minutes") or 0),
                level=levels[0],
                hands_on=has_exercise(item),
            )
        )
    return [i for i in out if i.minutes > 0]


def _skill_text(pack: Pack, skill_id: str) -> str:
    return f"{pack.skills[skill_id].name}: {SKILL_CONTEXT}"


def map_skills(
    settings: Settings, pack: Pack, items: list[Item], client: httpx.Client
) -> dict[str, dict[str, float]]:
    """item uid → {skill id: reranker relevance} for the skills the item covers."""
    skills = list(pack.skills)
    vectors = embed(
        settings,
        [i.text() for i in items] + [_skill_text(pack, s) for s in skills],
        BACKGROUND_BUDGET_SECONDS,
        client,
    )
    item_vecs, skill_vecs = vectors[: len(items)], vectors[len(items) :]
    found: dict[str, dict[str, float]] = {}
    for skill, sv in zip(skills, skill_vecs, strict=True):
        similar = sorted(
            range(len(items)),
            key=lambda k: -sum(a * b for a, b in zip(sv, item_vecs[k], strict=True)),
        )[: params.CATALOGUE_SHORTLIST]
        scores = rerank(
            settings,
            pack.skills[skill].name,  # the bare name: added context pushed every score near 0
            [items[k].text() for k in similar],
            BACKGROUND_BUDGET_SECONDS,
            client,
        )
        best = sorted(zip(similar, scores, strict=True), key=lambda x: -x[1])
        for k, score in best[: params.CATALOGUE_TOP_PER_SKILL]:
            if score >= params.CATALOGUE_MIN_RERANK:
                found.setdefault(items[k].uid, {})[skill] = round(score, 3)
    return {
        uid: dict(sorted(by.items(), key=lambda kv: -kv[1])[: params.CATALOGUE_MAX_SKILLS_PER_ITEM])
        for uid, by in found.items()
    }


def _course_id(uid: str) -> str:
    return "mslearn_" + re.sub(r"[^a-z0-9]+", "_", uid.lower()).strip("_")


def entries(
    items: list[Item], mapped: dict[str, dict[str, float]], checked: str
) -> list[dict[str, Any]]:
    out = []
    for item in items:
        covers = mapped.get(item.uid)
        if not covers:
            continue
        out.append(
            {
                "id": _course_id(item.uid),
                "title": item.title,
                "provider": PROVIDER,
                "url": item.url,
                "minutes": item.minutes,
                "level": item.level,
                "covers": list(covers),
                "time_basis": "reading_estimate",
                "hands_on": item.hands_on,
                "checked": checked,
                "verified": False,
                "match": covers,  # reranker relevance per skill, for the reviewer
            }
        )
    return sorted(out, key=lambda e: e["id"])


def merge(
    existing: dict[str, Any] | None, fresh: list[dict[str, Any]], checked: str
) -> dict[str, Any]:
    """New candidates replace old ones; every entry a reviewer verified is kept as it is."""
    kept = [c for c in (existing or {}).get("courses", []) if c.get("verified")]
    kept_ids = {c["id"] for c in kept}
    return {
        "checked": checked,
        "source": f"{PROVIDER} Catalog API ({API_URL}), fetched {checked}",
        "courses": kept + [c for c in fresh if c["id"] not in kept_ids],
    }


HEADER = (
    "# Generated by `python -m src.collectors.mslearn` from the Microsoft Learn Catalog API.\n"
    "# Candidates (verified: false) are never planned until a reviewer opens them and runs\n"
    "# `python scripts/review_catalogue.py --verify <id>`. `match` is the reranker's relevance.\n"
)


def write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def main() -> None:
    load_env_file()  # the RunPod keys live in the local .env
    settings = load_settings()
    if not settings.runpod_configured:
        raise SystemExit("RunPod is not configured: the skill mapping needs the GPU endpoint")
    pack = load_pack()
    known = {c.url for c in pack.courses.values() if c.provider != PROVIDER or c.verified}
    checked = f"{datetime.now(UTC):%Y-%m-%d}"
    with http.client("course catalogue", 120, follow_redirects=True) as client:
        items = candidates(fetch(client), known)
        mapped = map_skills(settings, pack, items, client)
    existing = yaml.safe_load(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
    data = merge(existing, entries(items, mapped, checked), checked)
    write(OUT, data)
    fresh = sum(not c["verified"] for c in data["courses"])
    print(f"{len(items)} catalogue items screened; {fresh} candidates written to {OUT.name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
