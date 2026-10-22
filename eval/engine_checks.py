"""Engine checks for the PRD (PERSON_A Task A8): fairness twins and time from profile to path.

Run:  python -m eval.engine_checks   → rewrites the "engine-checks" section of eval/RESULTS.md

1. Fairness twin test: every synthetic employee gets a "twin" that differs only in identity and
   demographic-style fields (id, name, team, plus gender and age passed in the request body, which
   the contract Profile does not even store). Same evidence. Rankings, scores and learning paths
   must be identical in both scenarios.
2. Time to path: wall-clock time for POST /api/profile → GET /api/recommendations → GET /api/path
   through the real FastAPI app on a fresh SQLite file (the brief's "profile → ranked roles + path
   in minutes" success test). Reported as the median of several runs.
"""

import json
import statistics
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from eval.results_md import RESULTS_PATH, write_section
from src.api_engine import get_store, seed
from src.contract import SCENARIOS, Event, Profile
from src.engine.catalogue import default_case_index, default_catalogue
from src.engine.planner import plan_path
from src.engine.recommend import recommend
from src.engine.skills import derive_states
from src.main import app
from src.store import SYNTHETIC_TEAM_PATH, Store, expand_history

SECTION = "engine-checks"
REPO_ROOT = Path(__file__).resolve().parent.parent
TIMING_DB = REPO_ROOT / "data" / "eval_timing.sqlite"  # gitignored (*.sqlite), removed after use
TIMING_RUNS = 5
MILLISECONDS = 1000
TWIN_EXTRA_FIELDS = {"gender": "other", "age": 52}  # ignored by the engine by design


@dataclass(frozen=True)
class TwinResult:
    person: str
    identical: bool


def _ranking_and_path(profile: Profile, events: Sequence[Event]) -> list[Any]:
    cat = default_catalogue()
    confidence = {s.skill_id: s.confidence for s in profile.skills_self_reported}
    states = derive_states(profile.id, list(cat.skills), list(events), confidence)
    output: list[Any] = []
    for scenario in SCENARIOS:
        rec = recommend(profile, states, cat, cat.assumptions_v1, scenario)
        output.append([(r.role_id, r.score, r.fit) for r in rec.roles])
        top = rec.roles[0].role_id
        plan = plan_path(
            profile.id,
            top,
            profile.weekly_learning_hours,
            states,
            cat,
            cat.assumptions_v1,
            default_case_index(),
            {e.case_id for e in events},
        )
        output.append([(s.ref, s.hours) for s in plan.steps])
    return output


def fairness_twins(team_path: Path = SYNTHETIC_TEAM_PATH) -> list[TwinResult]:
    people = json.loads(team_path.read_text(encoding="utf-8"))["people"]
    results = []
    for person in people:
        profile = Profile.model_validate(person["profile"])
        events = expand_history(profile.id, person["history"])
        twin_raw = {
            **person["profile"],
            "id": f"{profile.id}_twin",
            "display_name": "Twin (synthetic)",
            "team": "twin_team",
            **TWIN_EXTRA_FIELDS,
        }
        twin = Profile.model_validate(twin_raw)
        twin_events = [e.model_copy(update={"user_id": twin.id}) for e in events]
        same = _ranking_and_path(profile, events) == _ranking_and_path(twin, twin_events)
        results.append(TwinResult(profile.id, same))
    return results


def time_to_path(runs: int = TIMING_RUNS) -> list[float]:
    """Milliseconds per run for profile → recommendations → path on a fresh database."""
    TIMING_DB.unlink(missing_ok=True)
    store = Store(TIMING_DB)
    seed(store)
    app.dependency_overrides[get_store] = lambda: store
    client = TestClient(app)
    base = json.loads((REPO_ROOT / "schemas" / "examples" / "profile.json").read_text("utf-8"))
    timings = []
    try:
        for run in range(runs):
            profile = {**base, "id": f"u_timing_{run}"}
            start = time.perf_counter()
            client.post("/api/profile", json=profile).raise_for_status()
            client.get(f"/api/recommendations/{profile['id']}").raise_for_status()
            client.get(f"/api/path/{profile['id']}").raise_for_status()
            timings.append((time.perf_counter() - start) * MILLISECONDS)
    finally:
        app.dependency_overrides.clear()
        TIMING_DB.unlink(missing_ok=True)
    return timings


def render(twins: Sequence[TwinResult], timings: Sequence[float]) -> str:
    identical = sum(t.identical for t in twins)
    failed = ", ".join(t.person for t in twins if not t.identical) or "none"
    return "\n".join(
        [
            "## Engine checks",
            "",
            "| Check | Result | How |",
            "|---|---|---|",
            f"| Fairness twins | {identical}/{len(twins)} identical (failed: {failed}) | each "
            "synthetic employee vs a twin differing only in id, name, team, gender, age; same "
            "evidence; rankings, scores, fit and paths compared in both scenarios |",
            f"| Time from profile to path | median {statistics.median(timings):.0f} ms over "
            f"{len(timings)} runs (max {max(timings):.0f} ms) | POST /api/profile → GET "
            "/api/recommendations → GET /api/path, in-process, fresh SQLite, this laptop |",
        ]
    )


def run(results_path: Path = RESULTS_PATH) -> tuple[list[TwinResult], list[float]]:
    twins, timings = fairness_twins(), time_to_path()
    write_section(SECTION, render(twins, timings), results_path)
    return twins, timings


if __name__ == "__main__":
    twin_results, run_timings = run()
    print(f"twins identical: {sum(t.identical for t in twin_results)}/{len(twin_results)}")
    print(f"median ms: {statistics.median(run_timings):.0f}")
