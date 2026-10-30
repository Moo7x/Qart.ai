"""SDG matrix (C4): hours split over the skills a step serves, totals per target, roles view."""

from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

from src.match.engine import Evidence, score_role
from src.pack import load_pack
from src.pathway.planner import plan_pathway
from src.pathway.sdg import NOTE, sdg_matrix

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")
ROLES = list(load_pack().destination_roles)


def _matrix(role_id: str):  # type: ignore[no-untyped-def]
    pack = load_pack()
    match = score_role(pack, pack.destination_roles[role_id], {}, "moderate", EVIDENCE)
    path = plan_pathway(pack, match, {}, 6, "moderate", EVIDENCE)
    return path, sdg_matrix(pack, path)


@pytest.mark.parametrize("role_id", ROLES)
def test_cell_hours_equal_the_step_split(role_id: str) -> None:
    path, m = _matrix(role_id)
    rows = {r.skill for r in m.rows}
    expected: dict[str, float] = defaultdict(float)
    for step in path.steps:
        served = [s for s in step.course.covers if s in rows]
        for s in served:
            expected[s] += step.hours / len(served)
    for cell in m.cells:
        assert cell.hours == pytest.approx(expected.get(cell.skill, 0.0), abs=0.01)
        assert cell.reasons and all(r.text and r.source for r in cell.reasons)


@pytest.mark.parametrize("role_id", ROLES)
def test_totals_are_the_column_sums_and_not_added_across_targets(role_id: str) -> None:
    _, m = _matrix(role_id)
    for total in m.totals:
        column = sum(c.hours for c in m.cells if c.target == total.target)
        assert total.hours == pytest.approx(column, abs=0.01)
    assert m.note == NOTE
    assert {t.id for t in m.targets} == {t.target for t in m.totals}


def test_practice_is_a_marker_without_hours() -> None:
    path, m = _matrix("cost_accountant")
    practised = {p.skill for p in path.practice_steps}
    assert practised
    for row in m.rows:
        assert row.practice is (row.skill in practised)
    studied = {s for step in path.steps for s in step.course.covers}
    for cell in m.cells:  # a practice-only skill gets no hours from its practice
        if cell.skill in practised and cell.skill not in studied:
            assert cell.hours == 0


def test_api_shape_matches_c4(client: TestClient) -> None:
    pid = client.post("/api/profiles", json={"situation": "working"}).json()["id"]
    assert client.get(f"/api/profiles/{pid}/sdg").status_code == 409  # no destination yet
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": "cost_accountant"})
    body = client.get(f"/api/profiles/{pid}/sdg").json()
    assert set(body) == {
        "targets",
        "rows",
        "cells",
        "path_links",
        "totals",
        "roles",
        "note",
        "source",
    }
    assert set(body["targets"][0]) == {"id", "title", "text"}
    assert set(body["rows"][0]) == {"skill", "skill_name", "steps", "practice"}
    assert set(body["cells"][0]) == {"skill", "target", "hours", "reasons"}
    assert set(body["cells"][0]["reasons"][0]) == {"text", "source"}
    assert {link["target"] for link in body["path_links"]} >= {"4.3", "8.5"}
    assert len(body["roles"]) == len(load_pack().destination_roles)
    assert set(body["roles"][0]["targets"][0]) == {"target", "reason", "source"}
