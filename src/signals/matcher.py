"""Keyword matching of job posts to skills (word-boundary regexes, one count per post per skill).

Patterns listed in `case_sensitive_patterns` match case-sensitively (e.g. "RAG", "SAP", "Excel"),
every other pattern ignores case. Ambiguous short words (R, Go, C, "agent") are never matched on
their own: noisy counts are worse than a missing skill.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from src.signals.config import SkillSpec


@dataclass(frozen=True)
class CompiledSkill:
    id: str
    regexes: tuple[re.Pattern[str], ...]

    def matches(self, text: str) -> bool:
        return any(rx.search(text) for rx in self.regexes)


def compile_skill(skill: SkillSpec) -> CompiledSkill:
    sensitive = set(skill.case_sensitive_patterns)
    regexes = tuple(
        re.compile(p) if p in sensitive else re.compile(p, re.IGNORECASE) for p in skill.patterns
    )
    # A case-sensitive pattern may be listed only in case_sensitive_patterns; include it too.
    extra = tuple(re.compile(p) for p in skill.case_sensitive_patterns if p not in skill.patterns)
    return CompiledSkill(id=skill.id, regexes=regexes + extra)


def compile_skills(skills: Iterable[SkillSpec]) -> list[CompiledSkill]:
    return [compile_skill(s) for s in skills]


def skills_in_post(text: str, skills: Sequence[CompiledSkill]) -> set[str]:
    """Skill ids mentioned in one post; each skill counts at most once."""
    return {s.id for s in skills if s.matches(text)}
