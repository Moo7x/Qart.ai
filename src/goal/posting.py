"""A person's goal role, checked against a public job posting they paste (PLAN: dream role).

1. Requirements are read from the posting. Primary: gpt-4o-mini with a strict JSON schema; each
   requirement must quote the posting word for word (checked in code) and maps to a pack skill
   or "other". Fallback (no key, error, nothing valid): the posting's lines matched to skills by
   keyword search, labelled. Requirements marked "required/must/minimum" are essential.
2. Coverage of THIS posting: for each mapped requirement, the person's claimed level against the
   level the posting implies (POSTING_DEFAULT_LEVEL unless the model read a clear level).
   Reported as counts ("covers 4 of 9"), with unstated and unmapped requirements kept apart.
   It is not hiring readiness and says nothing about other employers.
3. Stepping stones: destination roles whose verified requirements share the posting's skills,
   with the person's fit for them and the courses that serve both.
No scraping, no application, no contact with the employer.
"""

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from src.config import Settings
from src.intake.extract import KEYWORD_MIN_SCORE, MIN_QUOTE_CHARS, _normalise
from src.intake.pii import scrub
from src.intake.skill_search import bm25
from src.match.engine import Evidence, Scenario, score_role
from src.pack import Pack

LLM_TIME_BUDGET_SECONDS = 25.0
MAX_POSTING_CHARS = 8000
# Level a posting requirement is taken to need when it states none: "working" (2), the level the
# pack uses for non-core requirements. Declared, because postings rarely state levels.
POSTING_DEFAULT_LEVEL = 2
ESSENTIAL_WORDS = re.compile(r"\b(must|required|requirement|minimum|mandatory|essential)\b", re.I)
LINE = re.compile(r"\n+|(?<=[.;])\s+")
MAX_STEPPING_STONES = 3

Complete = Callable[[list[dict[str, str]], dict[str, Any]], str]


@dataclass
class PostingRequirement:
    quote: str
    skill: str | None  # pack skill id, or None when the posting asks for something outside it
    skill_name: str | None
    essential: bool
    required_level: int | None
    claimed: int | None = None
    status: str = ""  # met | below | not_stated | outside_catalogue


@dataclass
class PostingCheck:
    engine: str
    note: str
    requirements: list[PostingRequirement] = field(default_factory=list)
    rejected: int = 0


def _schema(pack: Pack) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["requirements"],
        "properties": {
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["quote", "skill", "essential", "level"],
                    "properties": {
                        "quote": {"type": "string"},
                        "skill": {"type": "string", "enum": [*pack.skills, "other"]},
                        "essential": {"type": "boolean"},
                        "level": {"type": ["integer", "null"], "enum": [1, 2, 3, 4, None]},
                    },
                },
            }
        },
    }


def _messages(pack: Pack, posting: str) -> list[dict[str, str]]:
    skills = "\n".join(f"- {s.id}: {s.name}" for s in pack.skills.values())
    return [
        {
            "role": "system",
            "content": (
                "You read one job posting and list its requirements. For each, copy the phrase "
                "from the posting word for word as 'quote', pick the closest skill from the list "
                "or 'other' if none fits, mark essential=true only if the posting says it is "
                "required, a must or a minimum, and give a level only if the posting clearly "
                "states one (1 aware, 2 working, 3 proficient/several years, 4 expert/lead), "
                "otherwise null. Do not add anything the posting does not ask for.\n\n"
                f"Skills:\n{skills}"
            ),
        },
        {"role": "user", "content": posting},
    ]


def _openai(settings: Settings) -> Complete:
    def complete(msgs: list[dict[str, str]], json_schema: dict[str, Any]) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=LLM_TIME_BUDGET_SECONDS,
            max_retries=0,
        )
        request: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": msgs,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "posting_requirements",
                    "strict": True,
                    "schema": json_schema,
                },
            },
            "temperature": 0,
        }
        return client.chat.completions.create(**request).choices[0].message.content or ""

    return complete


def _keyword(pack: Pack, posting: str) -> list[PostingRequirement]:
    out = []
    for line in (part.strip(" -•*\t") for part in LINE.split(posting)):
        if len(line) < MIN_QUOTE_CHARS:
            continue
        hits = [h for h in bm25(pack, line, top_k=1) if h.score >= KEYWORD_MIN_SCORE]
        out.append(
            PostingRequirement(
                quote=line,
                skill=hits[0].skill if hits else None,
                skill_name=hits[0].name if hits else None,
                essential=bool(ESSENTIAL_WORDS.search(line)),
                required_level=None,
            )
        )
    return [r for r in out if r.skill]  # unmatched lines are often not requirements at all


def read_requirements(
    pack: Pack, raw: str, settings: Settings, complete: Complete | None = None
) -> PostingCheck:
    posting = scrub(raw[:MAX_POSTING_CHARS]).text  # a posting may carry a recruiter's contact
    if settings.llm_configured or complete is not None:
        try:
            answer = json.loads(
                (complete or _openai(settings))(_messages(pack, posting), _schema(pack))
            )
            haystack = _normalise(posting)
            kept, rejected = [], 0
            for item in answer.get("requirements", []):
                quote = str(item.get("quote", "")).strip()
                skill = item.get("skill")
                if len(quote) < MIN_QUOTE_CHARS or _normalise(quote) not in haystack:
                    rejected += 1
                    continue
                known = skill in pack.skills
                kept.append(
                    PostingRequirement(
                        quote=quote,
                        skill=skill if known else None,
                        skill_name=pack.skills[skill].name if known else None,
                        essential=bool(item.get("essential")),
                        required_level=item.get("level"),
                    )
                )
            if kept:
                note = (
                    f"{rejected} requirement(s) rejected: quote not in the posting"
                    if rejected
                    else ""
                )
                return PostingCheck(
                    f"{settings.llm_model} (schema-constrained)", note, kept, rejected
                )
            note = "no requirement passed the quote check; keyword fallback used"
        except Exception as exc:  # noqa: BLE001  any model or parsing failure → labelled fallback
            note = f"model unavailable ({type(exc).__name__}); keyword fallback used"
    else:
        note = "no language model configured; keyword fallback used"
    return PostingCheck("BM25 keywords (fallback)", note, _keyword(pack, posting))


def coverage(check: PostingCheck, levels: Mapping[str, int | None]) -> dict[str, Any]:
    for req in check.requirements:
        if req.skill is None:
            req.status = "outside_catalogue"
            continue
        needed = req.required_level or POSTING_DEFAULT_LEVEL
        req.claimed = levels.get(req.skill)
        if req.claimed is None:
            req.status = "not_stated"
        else:
            req.status = "met" if req.claimed >= needed else "below"
    mapped = [r for r in check.requirements if r.skill]
    essentials = [r for r in mapped if r.essential]
    return {
        "engine": check.engine,
        "note": check.note,
        "requirements": [asdict(r) for r in check.requirements],
        "covered": sum(r.status == "met" for r in mapped),
        "mapped": len(mapped),
        "not_stated": sum(r.status == "not_stated" for r in mapped),
        "outside_catalogue": sum(r.status == "outside_catalogue" for r in check.requirements),
        "essentials_met": sum(r.status == "met" for r in essentials),
        "essentials": len(essentials),
        "default_level": POSTING_DEFAULT_LEVEL,
    }


def stepping_stones(
    pack: Pack,
    check: PostingCheck,
    levels: Mapping[str, int | None],
    scenario: Scenario,
    evidence: Evidence,
) -> list[dict[str, Any]]:
    """Destination roles sharing the posting's skills, by overlap, with shared learning steps."""
    wanted = {r.skill for r in check.requirements if r.skill}
    gaps = {r.skill for r in check.requirements if r.skill and r.status in ("below", "not_stated")}
    out: list[dict[str, Any]] = []
    for role in pack.destination_roles.values():
        shared = sorted(wanted & {r.skill for r in role.requires})
        if not shared:
            continue
        match = score_role(pack, role, levels, scenario, evidence)
        courses = sorted(
            {c.id: c for s in shared if s in gaps for c in pack.courses_for(s)}.values(),
            key=lambda c: c.minutes,
        )
        out.append(
            {
                "role_id": role.id,
                "title": role.title,
                "shared": [pack.skills[s].name for s in shared],
                "overlap": len(shared),
                "fit": match.fit,
                "longer_route": match.longer_route,
                "shared_courses": [
                    {"id": c.id, "title": c.title, "url": c.url} for c in courses[:3]
                ],
            }
        )
    out.sort(key=lambda r: (-len(r["shared"]), -float(r["fit"])))
    return out[:MAX_STEPPING_STONES]
