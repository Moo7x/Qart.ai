"""Engine HTTP routes (Person A): validate input, call the engine, return contract models.

All A-owned endpoints of contract §5, plus `POST /api/ingest/run`, `POST /api/demo/reset` and
`GET /api/profile/{user_id}` (CONTRACT_QUESTIONS Q8). HR routes return aggregates only.
"""

import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.contract import (
    ChangedSince,
    CompanyAssumptions,
    Event,
    FlagName,
    NextCase,
    OptimizerProposal,
    PathPlan,
    Profile,
    Recommendation,
    Role,
    Scenario,
    SkillState,
    Snapshot,
    SnapshotDiff,
)
from src.engine.catalogue import (
    Catalogue,
    checkin_cases_by_skill,
    default_case_index,
    default_catalogue,
)
from src.engine.hr import HrSummary, hr_summary
from src.engine.ingest import CSV_NAME, RAW_DIR, SNAPSHOT_DIR, run_ingest
from src.engine.next_case import next_case
from src.engine.planner import plan_path
from src.engine.recommend import changed_since, recommend
from src.engine.skills import derive_states
from src.engine.snapshots import REPLAY_LABEL, diff_report, load_snapshots
from src.store import Store, make_store, seed_demo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["engine"])

DEFAULT_RECOMMENDATION_SCENARIO: Scenario = "agentic"  # contract §5 example
DEFAULT_PRACTICE_SCENARIO: Scenario = "assistive"  # the golden-journey cases are assistive


# --- dependencies ---------------------------------------------------------------------------
def snapshots_by_id() -> dict[str, Snapshot]:
    return {s.id: s for s in load_snapshots(SNAPSHOT_DIR)}


def seed(store: Store) -> int:
    ordered = sorted(snapshots_by_id().values(), key=lambda s: s.period)
    first = ordered[0].id if ordered else None
    return seed_demo(store, default_catalogue().assumptions_v1, first)


@lru_cache(maxsize=1)
def get_store() -> Store:
    """The process-wide store (Postgres if DATABASE_URL is set, else SQLite), seeded with
    synthetic data if empty (Replit may wipe files)."""
    store = make_store()
    with store.seed_lock():  # several instances may start at once on Replit
        if store.is_empty():
            logger.info("empty %s store: seeding synthetic demo data", store.backend)
            seed(store)
    return store


StoreDep = Annotated[Store, Depends(get_store)]


# --- helpers --------------------------------------------------------------------------------
def require_profile(store: Store, user_id: str) -> Profile:
    profile = store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"unknown user {user_id}")
    return profile


def current_assumptions(store: Store) -> CompanyAssumptions:
    return store.assumptions() or default_catalogue().assumptions_v1


def states_for(profile: Profile, events: list[Event], catalogue: Catalogue) -> list[SkillState]:
    confidence = {s.skill_id: s.confidence for s in profile.skills_self_reported}
    checkins = checkin_cases_by_skill(default_case_index())
    return derive_states(profile.id, list(catalogue.skills), events, confidence, checkins)


def active_snapshot(store: Store, snapshot_id: str | None) -> Snapshot | None:
    ids = store.ingested_snapshot_ids()
    if snapshot_id is not None and snapshot_id not in ids:
        raise HTTPException(status_code=404, detail=f"snapshot {snapshot_id} not ingested")
    chosen = snapshot_id or (ids[-1] if ids else None)
    return snapshots_by_id().get(chosen) if chosen else None


def _evidence_text(event: Event) -> str:
    parts = [f"{e.skill_id} {e.outcome} (help {e.help_level})" for e in event.skills_evidence]
    return f"{event.id} on {event.case_id}: {', '.join(parts)}"


def compute_changed_since(
    store: Store,
    profile: Profile,
    scenario: Scenario,
    snapshot: Snapshot | None,
    current: Recommendation,
) -> ChangedSince | None:
    """Compare with the state just before the latest change that affects this user."""
    change = store.last_change(profile.id)
    if change is None:
        return None
    catalogue = default_catalogue()
    assumptions = current_assumptions(store)
    events = store.events_for(profile.id)
    if change.kind == "assumptions" and assumptions.version > 1:
        previous = store.assumptions(assumptions.version - 1)
        if previous is None:
            return None
        baseline = recommend(
            profile, states_for(profile, events, catalogue), catalogue, previous, scenario, snapshot
        )
        note = f": {assumptions.change_note}" if assumptions.change_note else ""
        because = (
            f"company assumptions v{previous.version} → v{assumptions.version} approved by "
            f"{assumptions.updated_by}{note}"
        )
        return changed_since(baseline, current, because, previous.version)
    if change.kind in ("event", "flag"):
        changed = store.get_event(change.ref)
        if changed is None:
            return None
        if change.kind == "event":
            # Compare with the start of the latest session: one event may not move any factor
            # (e.g. "1 of 2" keeps the same state), but the session's events together do.
            session = changed.session_id
            before_events = [e for e in events if e.session_id != session]
            listed = "; ".join(_evidence_text(e) for e in events if e.session_id == session)
            because = f"new evidence in session {session}: {listed}"
        else:
            unflagged = changed.model_copy(update={"flags": type(changed.flags)()})
            before_events = [unflagged if e.id == changed.id else e for e in events]
            because = f"{changed.id} ({changed.case_id}) was flagged and no longer counts"
        baseline = recommend(
            profile,
            states_for(profile, before_events, catalogue),
            catalogue,
            assumptions,
            scenario,
            snapshot,
        )
        return changed_since(baseline, current, because, assumptions.version)
    return ChangedSince(assumptions_version=assumptions.version, rank_changes=[])


# --- profile and skills ---------------------------------------------------------------------
class ProfileResponse(BaseModel):
    profile: Profile
    skills: list[SkillState]


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check used by Replit and the golden-journey test."""
    return {"status": "ok"}


@router.post("/profile")
def create_profile(profile: Profile, store: StoreDep) -> ProfileResponse:
    catalogue = default_catalogue()
    unknown = {s.skill_id for s in profile.skills_self_reported} - set(catalogue.skills)
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown skill ids: {sorted(unknown)}")
    if profile.current_role_id not in catalogue.roles:
        raise HTTPException(status_code=422, detail=f"unknown role {profile.current_role_id}")
    store.upsert_profile(profile)
    events = store.events_for(profile.id)
    return ProfileResponse(profile=profile, skills=states_for(profile, events, catalogue))


@router.get("/profile/{user_id}")
def get_profile(user_id: str, store: StoreDep) -> Profile:
    return require_profile(store, user_id)


@router.get("/skills/{user_id}")
def get_skills(user_id: str, store: StoreDep) -> list[SkillState]:
    profile = require_profile(store, user_id)
    return states_for(profile, store.events_for(user_id), default_catalogue())


# --- events ---------------------------------------------------------------------------------
@router.post("/events")
def post_event(event: Event, store: StoreDep) -> list[SkillState]:
    catalogue = default_catalogue()
    profile = require_profile(store, event.user_id)
    unknown = {e.skill_id for e in event.skills_evidence} - set(catalogue.skills)
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown skill ids: {sorted(unknown)}")
    helped = event.help_level_max > 0 or any(e.help_level > 0 for e in event.skills_evidence)
    if event.mode == "checkin" and helped:
        raise HTTPException(status_code=422, detail="check-in events must have help level 0")
    if store.get_event(event.id) is not None:
        raise HTTPException(status_code=409, detail=f"event {event.id} already recorded")
    store.add_event(event)
    return states_for(profile, store.events_for(event.user_id), catalogue)


class FlagRequest(BaseModel):
    flag: FlagName
    value: bool = True
    set_by: Literal["employee", "senior", "grader"]


class FlagResponse(BaseModel):
    event: Event
    skills: list[SkillState]


@router.post("/events/{event_id}/flag")
def flag_event(event_id: str, request: FlagRequest, store: StoreDep) -> FlagResponse:
    event = store.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"unknown event {event_id}")
    flags = event.flags.model_copy(update={request.flag: request.value})
    updated = event.model_copy(update={"flags": flags})
    store.replace_event(updated)
    profile = require_profile(store, event.user_id)
    skills = states_for(profile, store.events_for(event.user_id), default_catalogue())
    return FlagResponse(event=updated, skills=skills)


# --- snapshots (layer A) --------------------------------------------------------------------
@router.get("/snapshots")
def get_snapshots(store: StoreDep) -> list[Snapshot]:
    available = snapshots_by_id()
    return [available[i] for i in store.ingested_snapshot_ids() if i in available]


@router.get("/snapshots/diff")
def get_snapshot_diff(
    store: StoreDep,
    from_id: Annotated[str | None, Query(alias="from")] = None,
    to_id: Annotated[str | None, Query(alias="to")] = None,
) -> SnapshotDiff:
    ids = store.ingested_snapshot_ids()
    available = snapshots_by_id()
    if from_id is None and to_id is None:
        if len(ids) < 2:
            raise HTTPException(status_code=404, detail="fewer than two snapshots ingested")
        from_id, to_id = ids[-2], ids[-1]
    if from_id not in available or to_id not in available:
        raise HTTPException(status_code=404, detail="unknown snapshot id")
    triggers = current_assumptions(store).review_triggers
    return diff_report(available[from_id], available[to_id], triggers)


class IngestRequest(BaseModel):
    rebuild_from_raw: bool = False


class IngestResult(BaseModel):
    ingested: str | None
    active_snapshots: list[str]
    diff: SnapshotDiff | None
    label: str
    message: str


@router.post("/ingest/run")
def ingest_run(store: StoreDep, request: IngestRequest | None = None) -> IngestResult:
    """Ingest the next dated snapshot (historical data replay); optionally rebuild from raw."""
    if request and request.rebuild_from_raw:
        if not (RAW_DIR / CSV_NAME).exists():
            raise HTTPException(status_code=409, detail="raw AEI CSV not present in data/raw")
        run_ingest(allow_download=False)
    ordered = sorted(snapshots_by_id().values(), key=lambda s: s.period)
    done = store.ingested_snapshot_ids()
    pending = [s for s in ordered if s.id not in done]
    if not pending:
        return IngestResult(
            ingested=None,
            active_snapshots=done,
            diff=None,
            label=REPLAY_LABEL,
            message="no newer snapshot to ingest",
        )
    new = pending[0]
    store.mark_snapshot_ingested(new.id)
    previous = next((s for s in reversed(ordered) if s.id in done), None)
    diff = None
    if previous is not None:
        diff = diff_report(previous, new, current_assumptions(store).review_triggers)
    return IngestResult(
        ingested=new.id,
        active_snapshots=store.ingested_snapshot_ids(),
        diff=diff,
        label=REPLAY_LABEL,
        message=f"ingested {new.id} (period {new.period}); review suggestions need HR approval",
    )


# --- roles, recommendations, path, next case ------------------------------------------------
@router.get("/roles")
def get_roles() -> list[Role]:
    return list(default_catalogue().roles.values())


@router.get("/recommendations/{user_id}")
def get_recommendations(
    user_id: str,
    store: StoreDep,
    scenario: Scenario = DEFAULT_RECOMMENDATION_SCENARIO,
    snapshot: str | None = None,
) -> Recommendation:
    catalogue = default_catalogue()
    profile = require_profile(store, user_id)
    states = states_for(profile, store.events_for(user_id), catalogue)
    snap = active_snapshot(store, snapshot)
    result = recommend(profile, states, catalogue, current_assumptions(store), scenario, snap)
    result.changed_since = compute_changed_since(store, profile, scenario, snap, result)
    return result


def robust_top_role(profile: Profile, states: list[SkillState], store: Store) -> str:
    """The role with the best worst-case score across both scenarios."""
    catalogue = default_catalogue()
    assumptions = current_assumptions(store)
    worst: dict[str, float] = {}
    for scenario in ("assistive", "agentic"):
        for role in recommend(profile, states, catalogue, assumptions, scenario).roles:
            worst[role.role_id] = min(worst.get(role.role_id, role.score), role.score)
    return max(sorted(worst), key=lambda r: worst[r])


@router.get("/path/{user_id}")
def get_path(
    user_id: str,
    store: StoreDep,
    role_id: str | None = None,
    weekly_hours: Annotated[float | None, Query(gt=0)] = None,
) -> PathPlan:
    catalogue = default_catalogue()
    profile = require_profile(store, user_id)
    events = store.events_for(user_id)
    states = states_for(profile, events, catalogue)
    if role_id is not None and role_id not in catalogue.roles:
        raise HTTPException(status_code=404, detail=f"unknown role {role_id}")
    return plan_path(
        user_id,
        role_id or robust_top_role(profile, states, store),
        weekly_hours or profile.weekly_learning_hours,
        states,
        catalogue,
        current_assumptions(store),
        default_case_index(),
        {e.case_id for e in events},
    )


@router.get("/next-case/{user_id}")
def get_next_case(
    user_id: str, store: StoreDep, scenario: Scenario = DEFAULT_PRACTICE_SCENARIO
) -> NextCase:
    catalogue = default_catalogue()
    profile = require_profile(store, user_id)
    events = store.events_for(user_id)
    states = states_for(profile, events, catalogue)
    return next_case(
        profile,
        states,
        events,
        catalogue,
        current_assumptions(store),
        scenario,
        default_case_index(),
    )


# --- HR (aggregates only) and assumptions (layer B) -----------------------------------------
@router.get("/hr/summary")
def get_hr_summary(
    store: StoreDep, team: str | None = None, scenario: Scenario | None = None
) -> HrSummary:
    catalogue = default_catalogue()
    profiles = store.list_profiles()
    states = {p.id: states_for(p, store.events_for(p.id), catalogue) for p in profiles}
    return hr_summary(team, profiles, states, catalogue, current_assumptions(store), scenario)


@router.get("/assumptions")
def get_assumptions(store: StoreDep) -> CompanyAssumptions:
    return current_assumptions(store)


@router.put("/assumptions")
def put_assumptions(update: CompanyAssumptions, store: StoreDep) -> CompanyAssumptions:
    """HR (synthetic) approves a new assumption version; the server bumps the version."""
    current = current_assumptions(store)
    for scenario in ("assistive", "agentic"):
        if set(update.scenarios[scenario].tasks) != set(current.scenarios[scenario].tasks):
            raise HTTPException(status_code=422, detail=f"{scenario}: task list must not change")
    if any(not 0.0 <= f <= 1.0 for f in update.shift_fractions.values()):
        raise HTTPException(status_code=422, detail="shift fractions must be between 0 and 1")
    new = update.model_copy(update={"version": current.version + 1})
    store.put_assumptions(new)
    return new


# --- optimiser proposals (stub: no optimiser run yet) ---------------------------------------
class ProposalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    decided_by: str


@router.get("/optimizer/proposals")
def get_proposals(store: StoreDep) -> list[OptimizerProposal]:
    """Empty until the optimiser (Task A9) writes a proposal; no results are invented."""
    return store.list_proposals()


@router.post("/optimizer/proposals/{proposal_id}/decision")
def decide_proposal(
    proposal_id: str, decision: ProposalDecision, store: StoreDep
) -> OptimizerProposal:
    proposal = store.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"unknown proposal {proposal_id}")
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail=f"proposal already {proposal.status}")
    decided = proposal.model_copy(
        update={
            "status": "approved" if decision.decision == "approve" else "rejected",
            "decided_by": decision.decided_by,
            "decided_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    )
    store.put_proposal(decided)
    return decided


# --- demo -----------------------------------------------------------------------------------
class ResetResult(BaseModel):
    status: str
    people: int
    active_snapshots: list[str]
    assumptions_version: int


@router.post("/demo/reset")
def demo_reset(store: StoreDep) -> ResetResult:
    """Back to the synthetic seed: v1 assumptions, oldest snapshot only, Aina with no events."""
    people = seed(store)
    return ResetResult(
        status="reset",
        people=people,
        active_snapshots=store.ingested_snapshot_ids(),
        assumptions_version=current_assumptions(store).version,
    )
