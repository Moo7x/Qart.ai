"""One person's context for every route: profile, destination, accepted evidence, and the plan.

Every route that scores roles or plans for a person goes through `Person`, so all of them use
the same claims, situation, evidence and ordering. Before this, each route rebuilt the context
by hand and several planned without the person's claims (docs/decision_log.md, 2026-10-31).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from sqlalchemy import Engine

from src.changes.store import accepted_rows
from src.forecast import task_model
from src.journey.store import ProfileData, SkillClaim, get_profile
from src.match import directions
from src.match.engine import Evidence, RoleMatch, Scenario, rank_roles, score_role
from src.match.evidence import automation_evidence
from src.pack import Pack, load_pack
from src.pathway.planner import Pathway, plan_pathway


@dataclass
class Person:
    id: str
    data: ProfileData
    destination: str | None
    pack: Pack
    rows: list[dict[str, Any]]  # the accepted evidence observations at the person's cutoff
    # The task model's newest per-task rows (observed and predicted AI use), for the forecast.
    task_rows: list[dict[str, Any]] = field(default_factory=list)
    evidence: Evidence = field(init=False)

    def __post_init__(self) -> None:
        self.evidence = automation_evidence(self.rows)

    def with_claims(self, changes: Mapping[str, SkillClaim]) -> "Person":
        """The same person with some claims replaced (a what-if); nothing is saved."""
        data = self.data.model_copy(update={"skills": {**self.data.skills, **changes}})
        return replace(self, data=data)

    def levels(self) -> dict[str, int | None]:
        return self.data.levels()

    def score(
        self, role_id: str, scenario: Scenario, evidence: Evidence | None = None
    ) -> RoleMatch:
        role = self.pack.destination_roles[role_id]
        return score_role(
            self.pack,
            role,
            self.levels(),
            scenario,
            self.evidence if evidence is None else evidence,
        )

    def forecasts(self, scenario: Scenario) -> dict[str, dict[str, Any]]:
        """The industry forecast for every pack role (src/match/directions.py)."""
        return directions.forecasts(self.pack, self.rows, self.task_rows, scenario)

    def rank(self, scenario: Scenario, evidence: Evidence | None = None) -> list[RoleMatch]:
        """Every destination role by direction score (fit x outlook factor); interests and chosen
        SDGs order near-ties of fit first, and equal direction scores keep that order."""
        by_fit = rank_roles(
            self.pack,
            self.levels(),
            scenario,
            self.evidence if evidence is None else evidence,
            set(self.data.interests) or None,
            sdg_goals=set(self.data.sdg_priorities) or None,
        )
        return directions.order(by_fit, self.forecasts(scenario))

    def plan(
        self,
        match: RoleMatch,
        scenario: Scenario,
        evidence: Evidence | None = None,
        weekly_hours: float | None = None,
    ) -> Pathway:
        """The person's plan to `match`'s role: always their claims and situation."""
        return plan_pathway(
            self.pack,
            match,
            self.data.skills,
            weekly_hours or self.data.weekly_hours,
            scenario,
            self.evidence if evidence is None else evidence,
            self.data.situation,
        )


def load_person(engine: Engine, profile_id: str) -> Person | None:
    found = get_profile(engine, profile_id)
    if found is None:
        return None
    data, destination = found
    _, task_rows = task_model.latest(engine)
    rows = accepted_rows(engine, profile_id)
    return Person(profile_id, data, destination, load_pack(), rows, task_rows)
