"""Load test: many people walking the Qart.ai journey at the same time (docs/PHASE2_PLAN.md A9).

    locust -f scripts/load/locustfile.py --host https://qartai.replit.app \
        --users 50 --spawn-rate 5 --run-time 5m --headless --csv docs/load/run50

Each virtual person creates a synthetic profile from fixed levels (no CV, so no language-model
cost), then opens what a person opens: matches, the plan, the tracks, the trends, the forecast
and the status. A small share also reads a sample CV with the language model, capped at
LOAD_MAX_LLM_CALLS per run so a test never runs up a bill. Results (p50 / p95 per endpoint,
errors, requests per second) go in docs/LOAD_TEST.md with the date and commit. Run it from a
laptop against the deployed app; never against a judge's live session.
"""

import random
import threading

from locust import HttpUser, between, task

LOAD_MAX_LLM_CALLS = 50  # language-model calls allowed in one run (cost cap)
LLM_SHARE = 0.05  # share of virtual people who also read a sample CV
SCENARIOS = ("moderate", "fast")
PERSONAS = [
    {
        "situation": "working",
        "current_role": "cash_application_analyst",
        "weekly_hours": 6,
        "skills": {"reconciliation": 3, "cash_application": 3, "erp": 2, "reporting": 2},
    },
    {
        "situation": "student",
        "current_role": "other",
        "weekly_hours": 8,
        "skills": {"accounting_principles": 1, "reporting": 1},
    },
    {
        "situation": "switcher",
        "current_role": "other",
        "weekly_hours": 5,
        "skills": {"stakeholder_management": 2, "reporting": 1},
    },
]

_llm_calls = 0
_lock = threading.Lock()


def _take_llm_call() -> bool:
    global _llm_calls
    with _lock:
        if _llm_calls >= LOAD_MAX_LLM_CALLS:
            return False
        _llm_calls += 1
        return True


class Person(HttpUser):
    wait_time = between(1, 4)  # seconds a person spends reading between clicks

    def on_start(self) -> None:
        persona = random.choice(PERSONAS)
        body = {
            **{k: v for k, v in persona.items() if k != "skills"},
            "skills": {
                s: {"level": lvl, "evidence": "", "source": "self"}
                for s, lvl in persona["skills"].items()
            },
        }
        self.profile = self.client.post("/api/profiles", json=body, name="/api/profiles").json()[
            "id"
        ]
        roles = self.client.get(f"/api/profiles/{self.profile}/matches", name="/matches").json()[
            "roles"
        ]
        self.client.post(
            f"/api/profiles/{self.profile}/destination",
            json={"role_id": roles[0]["role_id"]},
            name="/destination",
        )
        if random.random() < LLM_SHARE and _take_llm_call():
            sample = self.client.get("/api/samples/nur", name="/samples").json()["text"]
            self.client.post("/api/intake/parse", json={"text": sample}, name="/intake/parse (LLM)")

    @task(4)
    def matches(self) -> None:
        scenario = random.choice(SCENARIOS)
        self.client.get(
            f"/api/profiles/{self.profile}/matches?scenario={scenario}", name="/matches"
        )

    @task(3)
    def plan(self) -> None:
        self.client.get(f"/api/profiles/{self.profile}/pathway", name="/pathway")
        self.client.get(f"/api/profiles/{self.profile}/tracks", name="/tracks")

    @task(2)
    def trends(self) -> None:
        self.client.get("/api/trends", name="/trends")
        self.client.get("/api/forecast", name="/forecast")

    @task(1)
    def status(self) -> None:
        self.client.get("/api/status", name="/status")
        self.client.get("/api/sources", name="/sources")

    def on_stop(self) -> None:
        self.client.delete(
            f"/api/profiles/{self.profile}", name="/profiles (delete)"
        )  # leave no test data
