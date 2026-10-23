"""Transparent tags for a posting: regions, role family, mentions AI, skills.

All rules are keyword patterns from catalogue/ats_config.json (regions, AI terms, title ->
family) and the canonical skill patterns in catalogue/skills.json (the same matcher the Skills
Radar uses), so every tag can be traced to the words that produced it.
"""

import re
from dataclasses import dataclass
from functools import cached_property

from src.jobs.config import AtsConfig
from src.jobs.sources import Posting
from src.signals.config import SkillSpec
from src.signals.matcher import compile_skills, skills_in_post


@dataclass(frozen=True)
class Tags:
    regions: tuple[str, ...]  # always includes "global"
    family: str | None
    mentions_ai: bool
    skills: tuple[str, ...]


class Tagger:
    def __init__(self, cfg: AtsConfig, skills: list[SkillSpec]) -> None:
        self.cfg = cfg
        self.skills = compile_skills(skills)

    @cached_property
    def _regions(self) -> dict[str, re.Pattern[str]]:
        return {k: re.compile(v, re.I) for k, v in self.cfg.regions.items()}

    @cached_property
    def _ai(self) -> list[re.Pattern[str]]:
        exact = set(self.cfg.ai_terms_case_sensitive)
        return [re.compile(t) if t in exact else re.compile(t, re.I) for t in self.cfg.ai_terms]

    @cached_property
    def _families(self) -> list[tuple[str, re.Pattern[str]]]:
        return [(fid, re.compile(p, re.I)) for fid, p in self.cfg.role_families]

    def regions(self, p: Posting) -> tuple[str, ...]:
        found = ["global"] + [k for k, rx in self._regions.items() if rx.search(p.location)]
        if "malaysia" in found or "singapore" in found:
            found.append("malaysia_singapore")
        if p.remote:
            found.append("remote")
        return tuple(dict.fromkeys(found))

    def family(self, p: Posting) -> str | None:
        return next((fid for fid, rx in self._families if rx.search(p.title)), None)

    def mentions_ai(self, p: Posting) -> bool:
        text = f"{p.title}\n{p.description}"
        return any(rx.search(text) for rx in self._ai)

    def tag(self, p: Posting) -> Tags:
        text = f"{p.title}\n{p.description}"
        return Tags(
            regions=self.regions(p),
            family=self.family(p),
            mentions_ai=self.mentions_ai(p),
            skills=tuple(sorted(skills_in_post(text, self.skills))),
        )
