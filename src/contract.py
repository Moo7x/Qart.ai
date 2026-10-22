"""Pydantic models for the shared JSON contract (team/00_SHARED_CONTRACT.md §3–§4, v2).

These models mirror `schemas/examples/*.json`. Fields that are not in the contract examples are
optional (they have defaults), so every contract example still validates unchanged. Each such
addition is listed in docs/CONTRACT_QUESTIONS.md for both teammates to confirm.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- §3 enums -------------------------------------------------------------------------------
HelpLevel = int  # 0 none · 1 question · 2 hint · 3 explanation · 4 answer shown (validated below)
HELP_LEVEL_NAMES: dict[int, str] = {
    0: "no help",
    1: "a question",
    2: "a hint",
    3: "an explanation",
    4: "the answer shown",
}
CaseMode = Literal["practice", "checkin", "real"]
Decision = Literal["sign_off", "correct", "escalate"]
SkillStateName = Literal[
    "self_reported", "observed_with_help", "demonstrated_independently", "insufficient_evidence"
]
Scenario = Literal["assistive", "agentic"]
SCENARIOS: tuple[Scenario, ...] = ("assistive", "agentic")
CauseIfWrong = Literal["worker_gap", "ai_error", "data_issue", "ambiguous"]
# Per-skill outcome inside an event. The contract shows "success" and "missed_then_found";
# "failure" (missed and not found) is our closest compliant addition (CONTRACT_QUESTIONS Q1).
Outcome = Literal["success", "missed_then_found", "failure"]
Allocation = Literal["human", "ai_drafts_human_reviews", "ai"]
SkillType = Literal["execution", "oversight"]
FlagName = Literal["companion_error", "ambiguous_case", "data_issue"]


# --- Profile --------------------------------------------------------------------------------
class SelfReportedSkill(BaseModel):
    skill_id: str
    confidence: float = Field(ge=0.0, le=1.0)


class Profile(BaseModel):
    id: str
    display_name: str
    current_role_id: str
    years_experience: float = Field(ge=0.0)
    skills_self_reported: list[SelfReportedSkill] = []
    interests: list[str] = []
    weekly_learning_hours: float = Field(gt=0.0)
    language: str = "en"
    team: str


# --- Case (owned by Person B; modelled here so both sides validate the same shape) ----------
class LedgerRow(BaseModel):
    row_id: str
    date: str
    description: str
    amount: float
    currency: str
    doc_ref: str | None = None


class BankRow(BaseModel):
    row_id: str
    date: str
    description: str
    amount: float
    currency: str


class CaseDocument(BaseModel):
    doc_ref: str
    type: str
    text: str


class ProposedAdjustment(BaseModel):
    id: str
    amount: float
    reason: str


class AiOutput(BaseModel):
    claim: str
    proposed_adjustments: list[ProposedAdjustment] = []


class GroundTruth(BaseModel):
    has_issue: bool
    issue_types: list[str]
    affected_rows: list[str]
    correct_decision: Decision
    explanation: str
    skills: list[str]


class Case(BaseModel):
    id: str
    title: str
    mode: CaseMode
    difficulty: int
    scenario_variant: Scenario
    ledger: list[LedgerRow]
    bank: list[BankRow]
    documents: list[CaseDocument]
    ai_output: AiOutput
    ground_truth: GroundTruth | None = None


# --- Event ----------------------------------------------------------------------------------
class SkillEvidence(BaseModel):
    skill_id: str
    outcome: Outcome
    help_level: HelpLevel = Field(ge=0, le=4)


class EventFlags(BaseModel):
    companion_error: bool = False
    ambiguous_case: bool = False
    data_issue: bool = False


class Event(BaseModel):
    id: str
    user_id: str
    case_id: str
    mode: CaseMode
    scenario: Scenario
    timestamp: str
    self_confidence_before: float | None = Field(default=None, ge=0.0, le=1.0)
    help_level_max: HelpLevel = Field(ge=0, le=4)
    help_steps: list[str] = []
    checks_used: list[str] = []
    user_decision: Decision
    decision_correct: bool
    issue_found_by: str | None = None
    skills_evidence: list[SkillEvidence]
    cause_if_wrong: CauseIfWrong | None = None
    companion_version: str | None = None
    duration_sec: int | None = None
    difficulty: int | None = None
    session_id: str
    flags: EventFlags = EventFlags()


# --- SkillState -----------------------------------------------------------------------------
class EvidenceTrailItem(BaseModel):
    event_id: str
    case_id: str
    outcome: Outcome
    help_level: HelpLevel
    # Additions (optional): lets the UI explain why a flagged event was ignored.
    counted: bool = True
    note: str | None = None


class SkillState(BaseModel):
    user_id: str
    skill_id: str
    state: SkillStateName
    why: str
    next_to_confirm: str | None = None
    evidence_trail: list[EvidenceTrailItem] = []
    counted_events: int
    independent_successes: int
    self_confidence: float | None = None
    # Internal only: orders practice. Never shown to users as a percentage (AGENTS.md).
    provisional_estimate: float
    estimate_note: str
    last_updated: str | None = None


# --- Role -----------------------------------------------------------------------------------
class OnetBasis(BaseModel):
    source: str
    code: str
    title: str
    url: str


class RoleSkill(BaseModel):
    skill_id: str
    base_weight: float = Field(ge=0.0)


class RoleTask(BaseModel):
    """A role task taken from an O*NET task statement (addition, PERSON_A Task A2)."""

    task: str
    onet: str
    workflow_task: str
    skills: list[str]
    source_url: str


class Role(BaseModel):
    id: str
    title: str
    internal: bool
    based_on: list[OnetBasis]
    skills: list[RoleSkill]
    sdg_targets: list[str]
    summary: str
    # Additions (optional): task statements behind the weights, and interest tags.
    tasks: list[RoleTask] = []
    tags: list[str] = []


# --- Snapshot (layer A: external evidence only) ---------------------------------------------
class Signal(BaseModel):
    entity: str
    metric: str
    geo: str | None = None
    value: float
    period: str | None = None


class AssumptionReview(BaseModel):
    assumption_id: str
    reason: str


class Snapshot(BaseModel):
    id: str
    source: str
    release_date: str
    period: str
    geo: str
    url: str
    retrieved_at: str
    signals: list[Signal]
    suggested_assumption_reviews: list[AssumptionReview] = []
    # Additions (optional): licence/attribution and the honesty label.
    licence: str | None = None
    label: str | None = None


class SignalChange(BaseModel):
    """One signal compared across two snapshots (diff response; shape proposed in Q9)."""

    entity: str
    metric: str
    geo: str | None
    before: float | None
    after: float | None
    change: float | None
    relative_change: float | None
    significant: bool


class SnapshotDiff(BaseModel):
    """`GET /api/snapshots/diff` response; the contract names the endpoint, not its shape (Q9)."""

    from_id: str
    to_id: str
    from_period: str
    to_period: str
    label: str
    changes: list[SignalChange]
    suggested_assumption_reviews: list[AssumptionReview]
    note: str


# --- CompanyAssumptions (layer B: explicit, labelled, editable by HR) -----------------------
class ScenarioAllocation(BaseModel):
    tasks: dict[str, Allocation]


class ReviewTrigger(BaseModel):
    """Maps an external signal to the assumptions HR should review when it moves (addition)."""

    soc_code: str
    metric: str
    geo: str
    assumption_ids: list[str]


class CompanyAssumptions(BaseModel):
    version: int = Field(ge=1)
    updated_by: str
    based_on_snapshot: str | None = None
    scenarios: dict[Scenario, ScenarioAllocation]
    shift_rule: str
    # Additions (optional): the machine-readable form of shift_rule and the review mapping.
    shift_fractions: dict[Scenario, float] = {"assistive": 0.5, "agentic": 0.8}
    task_descriptions: dict[str, str] = {}
    review_triggers: list[ReviewTrigger] = []
    label: str | None = None
    change_note: str | None = None


# --- Recommendation -------------------------------------------------------------------------
class Factors(BaseModel):
    coverage: float
    confidence: float
    interest: float
    effort: float


class GapItem(BaseModel):
    skill_id: str
    state: SkillStateName
    weight: float


class CardTask(BaseModel):
    task: str
    onet: str
    allocation: Allocation
    # Addition (optional): the company workflow task this O*NET task maps to.
    workflow_task: str | None = None


class CardWeight(BaseModel):
    skill_id: str
    base: float
    scenario: float
    because: str


class SourceLink(BaseModel):
    label: str
    url: str
    # Addition (optional): evidence / assumption / synthetic (AGENTS.md labelling rule).
    kind: str | None = None


OutlookLabel = Literal["being transformed", "stable", "AI-era role"]


class RoleOutlook(BaseModel):
    """How the company's AI-adoption assumptions reshape a role (addition, Q12).

    Derived from company assumptions (layer B), not a headcount forecast.
    """

    ai_handled_share: float
    oversight_share: float
    label: OutlookLabel
    because: str
    basis: str


class RequirementCard(BaseModel):
    tasks: list[CardTask]
    weights: list[CardWeight]
    evidence: list[SourceLink]
    # Addition (optional): the assumption text the weights follow from, and the role outlook.
    assumption: str | None = None
    outlook: RoleOutlook | None = None


class TimeToReady(BaseModel):
    """Hours still needed to close the role's gaps, and weeks at the current budget (Q12)."""

    hours: float
    weeks_at_current_budget: int


class RoleRecommendation(BaseModel):
    role_id: str
    rank: int
    score: float
    factors: Factors
    formula: str
    gap: list[GapItem]
    requirement_card: RequirementCard
    sources: list[SourceLink]
    # Addition (optional): role title, SDG targets and the score label for the UI.
    title: str | None = None
    sdg_targets: list[str] = []
    score_note: str | None = None
    outlook: RoleOutlook | None = None
    # Additions (optional, Q12): readable ranking. `score` is clamped at 0 for display.
    fit: float | None = None
    time_to_ready: TimeToReady | None = None
    close_match: bool = False


class RankChange(BaseModel):
    role_id: str
    # Contract field names are "from" / "to"; "from" is a Python keyword, hence the alias.
    from_rank: int = Field(alias="from")
    to: int
    because: str

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class OutlookChange(BaseModel):
    """A role whose outlook moved between two recommendations (addition, Q12)."""

    role_id: str
    from_label: OutlookLabel
    to_label: OutlookLabel
    from_ai_handled_share: float
    to_ai_handled_share: float
    because: str


class ChangedSince(BaseModel):
    assumptions_version: int | None = None
    rank_changes: list[RankChange] = []
    # Addition (optional): outlook changes, e.g. after HR approves a new assumption version.
    outlook_changes: list[OutlookChange] = []


class Recommendation(BaseModel):
    user_id: str
    scenario: Scenario
    snapshot_id: str | None
    assumptions_version: int
    roles: list[RoleRecommendation]
    changed_since: ChangedSince | None = None


# --- PathPlan -------------------------------------------------------------------------------
PathStepType = Literal["practice_case", "course", "checkin"]


class PathStep(BaseModel):
    order: int
    type: PathStepType
    ref: str
    title: str
    hours: float
    skills: list[str]
    cost: str
    url: str | None = None
    retrieved: str | None = None
    sdg_targets: list[str] = []
    # Addition (optional): why the planner picked or revised this step.
    because: str | None = None


class PathPlan(BaseModel):
    user_id: str
    target_role_id: str
    weekly_hours: float
    robust_across: list[Scenario]
    steps: list[PathStep]
    total_hours: float
    weeks: int
    worst_case_gap: float


# --- Course ---------------------------------------------------------------------------------
class Course(BaseModel):
    id: str
    title: str
    provider: str
    url: str
    hours: float
    cost: str
    skills: list[str]
    prerequisites: list[str] = []
    retrieved: str
    # Additions (optional, PERSON_A Task A2): URL verification status and HRD Corp flag.
    verified: bool = False
    hrd_claimable: bool = False
    hours_source: str | None = None
    verification_note: str | None = None
    # Addition (optional): where the cost label was confirmed (never "free" without a source).
    cost_source: str | None = None


# --- OptimizerProposal ----------------------------------------------------------------------
class SetResult(BaseModel):
    before: str
    after: str


class AcceptanceResult(BaseModel):
    before: str
    after: str
    criteria_hash: str
    false_alarms_clean: SetResult
    invalid_citations: int


class OptimizerProposal(BaseModel):
    id: str
    editable_scope: Literal["playbook"]
    base_version: str
    candidate_version: str
    diff: str
    optimisation_set: SetResult
    acceptance_set: AcceptanceResult
    regressions: list[str]
    status: Literal["pending", "approved", "rejected"]
    decided_by: str | None
    decided_at: str | None
    rollback_to: str
    # Additions (optional): why the optimiser changed the text, and its development-set log.
    rationale: str | None = None
    development_log: list[str] = []


# --- Small response objects (§5) ------------------------------------------------------------
class NextCase(BaseModel):
    case_id: str | None
    because: str
    # Addition (optional): the skill the case targets.
    skill_id: str | None = None
