"""My plan's three tracks and the with/without-AI comparison use checked data and the planner."""

from fastapi.testclient import TestClient

from src.pack import load_pack
from src.pathway.tracks import is_ai_skill
from src.resources import load_resources
from tests.test_api_journey import create


def test_resources_point_at_real_skills_courses_and_checked_links() -> None:
    res = load_resources()  # raises on unknown skill, topic or course
    assert res.checked and res.videos and res.articles
    assert all(v.url.startswith("https://www.youtube.com/watch?v=") for v in res.videos)
    assert all(a.url.startswith("https://") for a in res.articles)
    assert [t.id for t in res.ai_basics][0] == "genai_basics"


def test_tracks_split_gaps_by_skill_kind_and_list_resources(client: TestClient) -> None:
    pid = create(client)
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": "finance_systems_analyst"})
    body = client.get(f"/api/profiles/{pid}/tracks").json()
    pack = load_pack()
    ids = [t["id"] for t in body["tracks"]]
    assert ids == ["ai_basics", "without_ai", "with_ai"]
    basics, without, with_ai = body["tracks"]
    assert basics["nodes"] and all(n["courses"] for n in basics["nodes"])
    assert all(not is_ai_skill(pack, n["skill"]) for n in without["nodes"])
    assert all(is_ai_skill(pack, n["skill"]) for n in with_ai["nodes"])
    planned = [
        c for t in body["tracks"][1:] for n in t["nodes"] for c in n["courses"] if c["planned"]
    ]
    path = client.get(f"/api/profiles/{pid}/pathway").json()
    assert {c["id"] for c in planned} <= {s["course"]["id"] for s in path["steps"]}


def test_comparison_uses_the_same_rules_for_both_routes(client: TestClient) -> None:
    pid = create(client)
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": "finance_systems_analyst"})
    comp = client.get(f"/api/profiles/{pid}/tracks").json()["comparison"]
    without, with_ai = comp["without_ai"], comp["with_ai"]
    # The with-AI route is the full plan plus AI basics, so it takes at least as long and, as
    # levels only rise, reaches at least the same fit in both scenarios.
    assert with_ai["hours"] >= without["hours"]
    for s in ("moderate", "fast"):
        assert with_ai["fit_after"][s] >= without["fit_after"][s] >= comp["fit_now"][s]


def test_progress_marks_a_node_done(client: TestClient) -> None:
    pid = create(client)
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": "finance_systems_analyst"})
    basics = client.get(f"/api/profiles/{pid}/tracks").json()["tracks"][0]
    first = basics["nodes"][0]
    client.put(
        f"/api/profiles/{pid}/progress",
        json={"done": [c["id"] for c in first["courses"]], "paused": False},
    )
    again = client.get(f"/api/profiles/{pid}/tracks").json()["tracks"][0]["nodes"][0]
    assert again["status"] == "done"
