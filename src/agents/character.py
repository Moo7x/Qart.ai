"""Agent character files (data/agents/*.character.yaml), in the spirit of ElizaOS characters.

A character file says who an agent is, how it speaks and what it must and must never do. Code
loads and checks it (a file without `must` or `never` rules is refused) and builds the system
prompt from it, so the agent's behaviour is reviewable data, not text hidden in code. The model
is not fine-tuned.
"""

from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.config import REPO_ROOT

AGENTS_DIR = REPO_ROOT / "data" / "agents"


class Style(BaseModel):
    all: list[str] = []
    chat: list[str] = []


class Rules(BaseModel):
    must: list[str] = Field(min_length=1)
    never: list[str] = Field(min_length=1)


class Example(BaseModel):
    user: str
    agent: str


class Character(BaseModel):
    name: str
    role: str
    bio: list[str] = Field(min_length=1)
    style: Style = Style()
    adjectives: list[str] = []
    topics: list[str] = []
    rules: Rules
    message_examples: list[Example] = []

    def system_prompt(self) -> str:
        lines = [f"You are {self.name}, {self.role}."]
        lines += self.bio
        if self.adjectives:
            lines.append("You are " + ", ".join(self.adjectives) + ".")
        if self.topics:
            lines.append("You know about: " + ", ".join(self.topics) + ".")
        lines += ["Style:", *(f"- {s}" for s in [*self.style.all, *self.style.chat])]
        lines += ["You must:", *(f"- {r}" for r in self.rules.must)]
        lines += ["You must never:", *(f"- {r}" for r in self.rules.never)]
        for ex in self.message_examples:
            lines += ["Example.", f"Input: {ex.user}", f"You: {ex.agent}"]
        return "\n".join(lines)


def load_character_file(path: Path) -> Character:
    return Character.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@cache
def load_character(name: str) -> Character:
    """data/agents/<name>.character.yaml, checked."""
    return load_character_file(AGENTS_DIR / f"{name}.character.yaml")
