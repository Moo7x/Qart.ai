"""One canonical skill vocabulary (QART_NEXT_STEPS §2): every skill id used anywhere must exist
in catalogue/skills.json. Fails on any unknown id. Questionnaire files (current roles, tasks,
tool chips) are checked too."""

import json
from pathlib import Path
from typing import Any

import pytest

from src.engine.catalogue import default_catalogue
from src.engine.questionnaire import load_questionnaire
from src.signals.config import default_config

ROOT = Path(__file__).resolve().parent.parent
VOCABULARY = default_catalogue().vocabulary


def skill_ids_in(obj: Any) -> set[str]:
    """Skill ids under any `skill_id`, `skills` or `*_skills` key, at any depth."""
    found: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "skill_id" and isinstance(value, str):
                found.add(value)
            elif key == "skills" or key.endswith("_skills"):
                if isinstance(value, dict):
                    found |= set(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            found.add(item)
                        elif isinstance(item, dict) and isinstance(item.get("skill_id"), str):
                            found.add(item["skill_id"])
            found |= skill_ids_in(value)
    elif isinstance(obj, list):
        for item in obj:
            found |= skill_ids_in(item)
    return found


FILES = sorted(
    [
        ROOT / "catalogue" / "roles.json",
        ROOT / "catalogue" / "courses.json",
        ROOT / "catalogue" / "sdg_map.json",
        ROOT / "data" / "case_index.json",
        *(ROOT / "cases").glob("*.json"),
    ]
)


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_referenced_skill_id_exists(path: Path) -> None:
    referenced = skill_ids_in(json.loads(path.read_text(encoding="utf-8")))
    unknown = sorted(referenced - set(VOCABULARY))
    assert not unknown, f"{path.name} uses unknown skill ids: {unknown}"


def test_vocabulary_ids_are_unique_and_complete() -> None:
    raw = json.loads((ROOT / "catalogue" / "skills.json").read_text(encoding="utf-8"))["skills"]
    ids = [s["id"] for s in raw]
    assert len(ids) == len(set(ids))
    for skill in VOCABULARY.values():
        assert skill.learn_hours is not None, f"{skill.id} has no learn_hours"
        assert skill.learn_hours.to_basic > 0 and skill.learn_hours.to_confident > 0
        if skill.evidence_tracked:
            assert skill.type is not None, f"evidence skill {skill.id} needs execution/oversight"
        if skill.trend_tracked:
            assert skill.patterns, f"tracked skill {skill.id} needs Hacker News patterns"
        assert skill.ai_exposure is not None, f"{skill.id} needs ai_exposure (fast scenario)"


def test_radar_tracks_exactly_the_trend_tracked_vocabulary_skills() -> None:
    tracked = {s.id for s in VOCABULARY.values() if s.trend_tracked}
    assert {s.id for s in default_config().skills} == tracked


def test_questionnaire_skill_ids_exist() -> None:
    q = load_questionnaire()
    unknown = sorted(q.referenced_skill_ids() - set(VOCABULARY))
    assert not unknown, f"questionnaire.json uses unknown skill ids: {unknown}"
    roles = default_catalogue().roles
    assert all(r.catalogue_role_id in roles for r in q.current_roles if r.catalogue_role_id)


def test_skill_prerequisites_are_known_and_acyclic() -> None:
    """A cycle would make a learning plan impossible to order (pathway.md §7.1)."""
    graph = {k: s.prerequisites for k, s in VOCABULARY.items()}
    for skill_id, prereqs in graph.items():
        assert set(prereqs) <= set(graph), f"{skill_id} has unknown prerequisites"
        assert skill_id not in prereqs
    state: dict[str, str] = {}

    def visit(node: str, path: tuple[str, ...]) -> None:
        if state.get(node) == "done":
            return
        assert state.get(node) != "open", f"prerequisite cycle: {' -> '.join((*path, node))}"
        state[node] = "open"
        for nxt in graph[node]:
            visit(nxt, (*path, node))
        state[node] = "done"

    for node in graph:
        visit(node, ())
