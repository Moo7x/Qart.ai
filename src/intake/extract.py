"""Read a (synthetic) CV into claimed skills, each backed by a sentence copied from the CV.

Primary: OpenAI gpt-4o-mini with a strict JSON schema whose skill field is limited to the pack's
skill ids, so the model cannot name a skill we do not have. Code then checks every quoted
sentence against the scrubbed CV and rejects any claim whose quote is not really there.
Fallback (no key, timeout, invalid answer): keyword matching, labelled as such; its skills come
without a level for the person to set.
Levels are always the person's claims as read from their CV, never verified skill.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.config import Settings
from src.intake.pii import scrub
from src.intake.skill_search import bm25
from src.pack import Pack

LLM_TIME_BUDGET_SECONDS = 25.0
MAX_CV_CHARS = 12_000  # longer text is cut: a CV, not a book
KEYWORD_MIN_SCORE = 2.0  # BM25 score a sentence must reach to count as mentioning a skill
MIN_QUOTE_CHARS = 8  # a quote shorter than this cannot show anything (e.g. a lone word)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
KINDS = ["finance_core", "data_digital", "green", "business"]

Complete = Callable[[list[dict[str, str]], dict[str, Any]], str]

LEVEL_GUIDE = (
    "Levels: 1 = aware (mentioned, studied or trained), 2 = working (did it in a job), "
    "3 = proficient (did it routinely or was responsible for it, usually 2+ years), "
    "4 = expert (led it, taught it or improved it for others)."
)


@dataclass(frozen=True)
class ClaimedSkill:
    skill: str
    name: str
    level: int | None  # None = found by keyword; the person sets the level
    evidence: str


@dataclass
class Extraction:
    current_role: str  # a pack current-role id or "other"
    years_experience: float | None
    skills: list[ClaimedSkill]
    interests: list[str]
    engine: str
    note: str
    removed: dict[str, int]
    rejected: list[dict[str, str]] = field(default_factory=list)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def schema(pack: Pack) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["current_role", "years_experience", "skills", "interests"],
        "properties": {
            "current_role": {"type": "string", "enum": [*pack.current_roles, "other"]},
            "years_experience": {"type": ["number", "null"]},
            "skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["skill", "level", "evidence"],
                    "properties": {
                        "skill": {"type": "string", "enum": list(pack.skills)},
                        "level": {"type": "integer", "enum": [1, 2, 3, 4]},
                        "evidence": {"type": "string"},
                    },
                },
            },
            "interests": {"type": "array", "items": {"type": "string", "enum": KINDS}},
        },
    }


def messages(pack: Pack, cv_text: str) -> list[dict[str, str]]:
    skills = "\n".join(f"- {s.id}: {s.name}" for s in pack.skills.values())
    roles = "\n".join(f"- {r.id}: {r.title}" for r in pack.current_roles.values())
    return [
        {
            "role": "system",
            "content": (
                "You read a CV and report only what it shows. List skills from the allowed list "
                "that the CV gives evidence for. For each, copy one sentence or phrase from the CV "
                "word for word as evidence. Never add a skill without such a sentence. "
                "Tools named in the CV count as evidence for the matching skill (e.g. an ERP "
                "system such as SAP for Enterprise Resource Planning). "
                f"{LEVEL_GUIDE} Pick the current role from the list, or 'other'. Interests are the "
                "kinds of work the person says they want more of.\n\nAllowed skills:\n"
                f"{skills}\n\nCurrent roles:\n{roles}"
            ),
        },
        {"role": "user", "content": cv_text},
    ]


def openai_complete(settings: Settings) -> Complete:
    def complete(msgs: list[dict[str, str]], json_schema: dict[str, Any]) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=LLM_TIME_BUDGET_SECONDS,
            max_retries=0,
        )
        # Plain dicts are what the API takes; the SDK's TypedDicts add nothing checkable here.
        request: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": msgs,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "cv_extraction", "strict": True, "schema": json_schema},
            },
            "temperature": 0,
        }
        response = client.chat.completions.create(**request)
        return response.choices[0].message.content or ""

    return complete


def _validate(
    pack: Pack, answer: dict[str, Any], cv_text: str
) -> tuple[list[ClaimedSkill], list[dict[str, str]]]:
    """Keep a claim only if its skill exists and its quote is really in the CV."""
    haystack = _normalise(cv_text)
    kept: dict[str, ClaimedSkill] = {}
    rejected = []
    for item in answer.get("skills", []):
        skill, level, quote = item.get("skill"), item.get("level"), str(item.get("evidence", ""))
        if skill not in pack.skills or level not in (1, 2, 3, 4):
            rejected.append({"skill": str(skill), "reason": "not an allowed skill or level"})
            continue
        if len(quote) < MIN_QUOTE_CHARS or _normalise(quote) not in haystack:
            rejected.append({"skill": skill, "reason": "quoted evidence is not in the CV"})
            continue
        if skill not in kept or level > (kept[skill].level or 0):
            kept[skill] = ClaimedSkill(skill, pack.skills[skill].name, level, quote.strip())
    return list(kept.values()), rejected


def keyword_extract(pack: Pack, cv_text: str) -> tuple[str, list[ClaimedSkill]]:
    lowered = cv_text.lower()
    # Match full role titles without their abbreviations ("Accounts Receivable Analyst"), and
    # take the one mentioned first: CVs list the current role before earlier ones.
    positions = {
        r.id: lowered.find(re.sub(r"\s*\([^)]*\)", "", r.title).lower())
        for r in pack.current_roles.values()
    }
    found_roles = sorted((pos, rid) for rid, pos in positions.items() if pos >= 0)
    role = found_roles[0][1] if found_roles else "other"
    found: dict[str, ClaimedSkill] = {}
    for sentence in (s.strip() for s in SENTENCE.split(cv_text)):
        if len(sentence) < MIN_QUOTE_CHARS:
            continue
        for hit in bm25(pack, sentence, top_k=2):
            if hit.score >= KEYWORD_MIN_SCORE and hit.skill not in found:
                found[hit.skill] = ClaimedSkill(hit.skill, hit.name, None, sentence)
    return role, list(found.values())


def extract(
    pack: Pack, raw_text: str, settings: Settings, complete: Complete | None = None
) -> Extraction:
    cleaned = scrub(raw_text[:MAX_CV_CHARS])
    text = cleaned.text
    if settings.llm_configured or complete is not None:
        try:
            raw = (complete or openai_complete(settings))(messages(pack, text), schema(pack))
            answer = json.loads(raw)
            skills, rejected = _validate(pack, answer, text)
            role = answer.get("current_role")
            return Extraction(
                current_role=role if role in pack.current_roles else "other",
                years_experience=answer.get("years_experience"),
                skills=skills,
                interests=[k for k in answer.get("interests", []) if k in KINDS],
                engine=f"{settings.llm_model} (schema-constrained)",
                note=f"{len(rejected)} claim(s) rejected by the evidence check" if rejected else "",
                removed=cleaned.removed,
                rejected=rejected,
            )
        except Exception as exc:  # noqa: BLE001  any model or parsing failure → labelled fallback
            note = f"model unavailable ({type(exc).__name__}); keyword fallback used"
    else:
        note = "no language model configured; keyword fallback used"
    role, skills = keyword_extract(pack, text)
    return Extraction(
        current_role=role,
        years_experience=None,
        skills=skills,
        interests=[],
        engine="BM25 keywords (fallback)",
        note=note,
        removed=cleaned.removed,
    )
