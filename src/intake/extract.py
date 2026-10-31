"""Read a (synthetic) CV into claimed skills, each backed by a sentence copied from the CV.

Primary: OpenAI gpt-4.1-mini with a strict JSON schema whose skill field is limited to the pack's
skill ids, so the model cannot name a skill we do not have. Code then checks every quoted
sentence against the scrubbed CV and rejects any claim whose quote is not really there.
Fallback (no key, timeout, invalid answer): keyword matching, labelled as such; its skills come
without a level for the person to set.
Both paths end with one rule: if the CV names an ERP system (params.ERP_ALIASES) and no `erp`
claim was read, one is added at level 2 with that sentence as evidence, and the note says so.
Levels are always the person's claims as read from their CV, never verified skill.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from src import llm, params
from src.config import Settings
from src.intake.pii import scrub
from src.intake.skill_search import bm25
from src.levels import Levels, load_levels
from src.pack import Pack
from src.stages import Stages

LLM_TIME_BUDGET_SECONDS = 25.0
MAX_CV_CHARS = 12_000  # longer text is cut: a CV, not a book
KEYWORD_MIN_SCORE = 2.0  # BM25 score a sentence must reach to count as mentioning a skill
MIN_QUOTE_CHARS = 8  # a quote shorter than this cannot show anything (e.g. a lone word)
# A phrase outside our skill list is a short name ("Python", "Tableau"), so it may be short.
MIN_UNMATCHED_CHARS = 2
MAX_UNMATCHED_CHARS = 80  # longer than a skill or tool name: a sentence, not a phrase
MAX_UNMATCHED = 20  # a CV, not a list of every word
KEYWORD_UNMATCHED_NOTE = "keywords cannot list CV phrases outside our skill list"
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
ERP_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(a) for a in params.ERP_ALIASES) + r")(?!\w)", re.IGNORECASE
)
ERP_RULE_NOTE = "ERP claim added by rule: the CV names an ERP system"
KINDS = ["finance_core", "data_digital", "green", "business"]

Complete = llm.Complete

LEVELS = (1, 2, 3, 4, 5)  # a claim needs evidence, so "none" (0) is never read from a CV


def level_guide(levels: Levels) -> str:
    """The scale meanings and rules, plus each skill's sentences when they fit the budget."""
    meanings = "; ".join(f"{s.level} = {s.label} ({s.meaning})" for s in levels.scale if s.level)
    guide = f"Levels: {meanings}. Rules: {' '.join(levels.rules)}"
    sentences = "\n".join(
        f"- {skill_id}: " + " | ".join(f"{n}: {text}" for n, text in sorted(s.anchors.items()))
        for skill_id, s in levels.skills.items()
    )
    with_sentences = f"{guide}\nLevel sentences per skill:\n{sentences}"
    return with_sentences if len(with_sentences) <= params.LEVEL_GUIDE_MAX_CHARS else guide


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
    # Skills or tools the CV names that are not in our skill list, word for word from the CV.
    # Listed as "not in our skill list", never dropped silently; they do not change any score.
    unmatched: list[str] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)  # measured, for the activity panel


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def schema(pack: Pack) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["current_role", "years_experience", "skills", "interests", "unmatched"],
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
                        "level": {"type": "integer", "enum": list(LEVELS)},
                        "evidence": {"type": "string"},
                    },
                },
            },
            "interests": {"type": "array", "items": {"type": "string", "enum": KINDS}},
            "unmatched": {"type": "array", "items": {"type": "string"}},
        },
    }


def messages(pack: Pack, cv_text: str) -> list[dict[str, str]]:
    levels = load_levels()

    def meaning(skill_id: str) -> str:
        # The skill's level-1 sentence says what it covers, so "Invoice Processing" (supplier
        # invoices) is not read from customer-invoice work; skills without sentences use the name.
        found = levels.skills.get(skill_id)
        return f" ({found.anchors[1].removeprefix('I can ')})" if found else ""

    skills = "\n".join(f"- {s.id}: {s.name}{meaning(s.id)}" for s in pack.skills.values())
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
                f"{level_guide(levels)} Pick the current role from the list, or "
                "'other'. Interests are the "
                "kinds of work the person says they want more of. Under unmatched, copy word for "
                "word the short name of each skill or tool the CV shows that fits none of the "
                "allowed skills (e.g. a programming language); never a whole sentence."
                "\n\nAllowed skills:\n"
                f"{skills}\n\nCurrent roles:\n{roles}"
            ),
        },
        {"role": "user", "content": cv_text},
    ]


def openai_complete(settings: Settings) -> Complete:
    return llm.openai_complete(
        settings,
        schema_name="cv_extraction",
        purpose="cv_extraction",
        timeout=LLM_TIME_BUDGET_SECONDS,
    )


def _validate(
    pack: Pack, answer: dict[str, Any], cv_text: str
) -> tuple[list[ClaimedSkill], list[dict[str, str]]]:
    """Keep a claim only if its skill exists and its quote is really in the CV."""
    haystack = _normalise(cv_text)
    kept: dict[str, ClaimedSkill] = {}
    rejected = []
    for item in answer.get("skills", []):
        skill, level, quote = item.get("skill"), item.get("level"), str(item.get("evidence", ""))
        if skill not in pack.skills or level not in LEVELS:
            rejected.append({"skill": str(skill), "reason": "not an allowed skill or level"})
            continue
        if len(quote) < MIN_QUOTE_CHARS or _normalise(quote) not in haystack:
            rejected.append({"skill": skill, "reason": "quoted evidence is not in the CV"})
            continue
        if skill not in kept or level > (kept[skill].level or 0):
            kept[skill] = ClaimedSkill(skill, pack.skills[skill].name, level, quote.strip())
    return list(kept.values()), rejected


def _unmatched(answer: dict[str, Any], cv_text: str) -> list[str]:
    """Keep only short phrases that are really in the CV, each once."""
    haystack = _normalise(cv_text)
    kept: dict[str, str] = {}
    for item in answer.get("unmatched", []):
        phrase = str(item).strip()
        if not MIN_UNMATCHED_CHARS <= len(phrase) <= MAX_UNMATCHED_CHARS:
            continue
        key = _normalise(phrase)
        # Whole words only, so "SQ" never counts as found inside "SQL".
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", haystack):
            kept.setdefault(key, phrase)
    return list(kept.values())[:MAX_UNMATCHED]


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


def erp_rule(pack: Pack, cv_text: str, skills: list[ClaimedSkill]) -> ClaimedSkill | None:
    """An `erp` claim from the first CV sentence naming an ERP system, if none was read."""
    if any(s.skill == "erp" for s in skills):
        return None
    for sentence in (s.strip().lstrip("-•* ") for s in SENTENCE.split(cv_text)):
        if len(sentence) >= MIN_QUOTE_CHARS and ERP_PATTERN.search(sentence):
            return ClaimedSkill("erp", pack.skills["erp"].name, params.ERP_RULE_LEVEL, sentence)
    return None


def _with_erp_rule(
    pack: Pack, cv_text: str, skills: list[ClaimedSkill], note: str
) -> tuple[list[ClaimedSkill], str]:
    added = erp_rule(pack, cv_text, skills)
    if added is None:
        return skills, note
    return [*skills, added], "; ".join(n for n in (note, ERP_RULE_NOTE) if n)


def extract(
    pack: Pack, raw_text: str, settings: Settings, complete: Complete | None = None
) -> Extraction:
    stages = Stages()
    with stages.step("Remove names, IC, phone and email", "rules"):
        cleaned = scrub(raw_text[:MAX_CV_CHARS])
    text = cleaned.text
    if settings.llm_configured or complete is not None:
        try:
            with stages.step("Read skills with quoted evidence", settings.llm_model):
                raw = (complete or openai_complete(settings))(messages(pack, text), schema(pack))
            with stages.step("Check every quote is in your CV", "code"):
                answer = json.loads(raw)
                skills, rejected = _validate(pack, answer, text)
                checked = (
                    f"{len(rejected)} claim(s) rejected by the evidence check" if rejected else ""
                )
                skills, checked = _with_erp_rule(pack, text, skills, checked)
                unmatched = _unmatched(answer, text)
            role = answer.get("current_role")
            return Extraction(
                current_role=role if role in pack.current_roles else "other",
                years_experience=answer.get("years_experience"),
                skills=skills,
                interests=[k for k in answer.get("interests", []) if k in KINDS],
                engine=f"{settings.llm_model} (schema-constrained)",
                note=checked,
                removed=cleaned.removed,
                rejected=rejected,
                unmatched=unmatched,
                stages=stages.items,
            )
        except Exception as exc:  # noqa: BLE001  any model or parsing failure → labelled fallback
            note = f"model unavailable ({type(exc).__name__}); keyword fallback used"
    else:
        note = "no language model configured; keyword fallback used"
    with stages.step("Match CV sentences to skills", "BM25 keywords"):
        role, skills = keyword_extract(pack, text)
        skills, note = _with_erp_rule(pack, text, skills, note)
    note = f"{note}; {KEYWORD_UNMATCHED_NOTE}"
    return Extraction(
        current_role=role,
        years_experience=None,
        skills=skills,
        interests=[],
        engine="BM25 keywords (fallback)",
        note=note,
        removed=cleaned.removed,
        stages=stages.items,
    )
