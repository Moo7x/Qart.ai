// Types matching team/00_SHARED_CONTRACT.md v2

export type HelpLevel = 0 | 1 | 2 | 3 | 4;
export type CaseMode = 'practice' | 'checkin' | 'real';
export type Decision = 'sign_off' | 'correct' | 'escalate';
export type SkillStateName =
  | 'self_reported'
  | 'observed_with_help'
  | 'demonstrated_independently'
  | 'insufficient_evidence';
export type Scenario = 'assistive' | 'agentic';
export type Outcome = 'success' | 'missed_then_found' | 'failure';

export interface LedgerRow {
  row_id: string;
  date: string;
  description: string;
  amount: number;
  currency: string;
  doc_ref?: string;
}

export interface BankRow {
  row_id: string;
  date: string;
  description: string;
  amount: number;
  currency: string;
}

export interface CaseDocument {
  doc_ref: string;
  type: string;
  text: string;
}

export interface ProposedAdjustment {
  id: string;
  amount: number;
  reason: string;
}

export interface AiOutput {
  claim: string;
  proposed_adjustments: ProposedAdjustment[];
}

export interface Case {
  id: string;
  title: string;
  mode: CaseMode;
  difficulty: number;
  scenario_variant: Scenario;
  ledger: LedgerRow[];
  bank: BankRow[];
  documents: CaseDocument[];
  ai_output: AiOutput;
  // ground_truth is never returned by the API
}

export interface SkillEvidence {
  skill_id: string;
  outcome: Outcome;
  help_level: HelpLevel;
}

export interface EventFlags {
  companion_error: boolean;
  ambiguous_case: boolean;
  data_issue: boolean;
}

export interface CompanionEvent {
  id: string;
  user_id: string;
  case_id: string;
  mode: CaseMode;
  scenario: Scenario;
  timestamp: string;
  self_confidence_before: number | null;
  help_level_max: HelpLevel;
  help_steps: string[];
  checks_used: string[];
  user_decision: Decision;
  decision_correct: boolean;
  issue_found_by: string | null;
  skills_evidence: SkillEvidence[];
  cause_if_wrong: string | null;
  companion_version: string | null;
  duration_sec: number | null;
  difficulty: number | null;
  session_id: string;
  flags: EventFlags;
}

export interface EvidenceTrailItem {
  event_id: string;
  case_id: string;
  outcome: Outcome;
  help_level: HelpLevel;
  counted?: boolean;
  note?: string;
}

export interface SkillState {
  user_id: string;
  skill_id: string;
  state: SkillStateName;
  why: string;
  next_to_confirm: string | null;
  evidence_trail: EvidenceTrailItem[];
  counted_events: number;
  independent_successes: number;
  self_confidence: number | null;
  provisional_estimate: number;
  estimate_note: string;
  last_updated: string | null;
}

export interface SelfReportedSkill {
  skill_id: string;
  confidence: number;
}

export interface Profile {
  id: string;
  display_name: string;
  current_role_id: string;
  years_experience: number;
  skills_self_reported: SelfReportedSkill[];
  interests: string[];
  weekly_learning_hours: number;
  language: string;
  team: string;
  preferences?: Preferences; // v2.1: stored only, not used for ranking yet
}

// Optional intake answers (contract v2.1). The engine does not score them yet.
export interface Preferences {
  industry?: string | null;
  education?: string | null;
  tools?: string[];
  direction?: 'grow' | 'adjacent' | 'switch' | null;
  timeframe_months?: 3 | 6 | 12 | null;
  formats?: string[];
  ai_comfort?: number | null;
  notes?: string | null;
  // v2.4: questionnaire answers (ids from GET /api/questionnaire)
  current_job?: string | null;
  tasks?: string[];
  skill_levels?: Record<string, SkillLevel>;
}

// GET /api/questionnaire (v2.4)
export type SkillLevel = 'heard' | 'sometimes' | 'confident';
export interface Questionnaire {
  industries: string[];
  education: { label: string; level: string }[];
  education_order: string[];
  levels: { id: SkillLevel; label: string; value: number }[];
  default_level: SkillLevel;
  tools: { label: string; skills: string[]; exclusive: boolean }[];
  current_roles: { id: string; name: string; family: string | null; catalogue_role_id: string | null; typical_skills: string[] }[];
  tasks: { id: string; label: string; skills: string[]; families: string[] }[];
  skills: { id: string; name: string; category: string }[];
}

// GET /api/roles
export interface Role {
  id: string;
  title: string;
  internal: boolean;
  skills: { skill_id: string; base_weight: number }[];
  sdg_targets: string[];
  summary: string;
  tags?: string[];
}

// GET /api/sdg (v2.1): the catalogue's SDG map; `about` says it is declared judgment.
export interface SdgTarget {
  id: string;
  main: boolean;
  goal: number;
  title: string;
  url: string;
  rationale: string;
}

export interface SdgMap {
  about: string;
  retrieved: string;
  targets: SdgTarget[];
  roles: Record<string, { targets: string[]; rationale: string }>;
  skills: Record<string, { targets: string[]; rationale: string }>;
}

// Companion message response
export interface UiAction {
  type: 'highlight_rows' | 'open_document' | 'show_check' | 'pop_in';
  rows?: string[];
  doc_ref?: string;
  check?: string;
  result?: string;
  message?: string;
}

export interface CompanionMessageResponse {
  reply: string;
  help_level: HelpLevel;
  ui_actions: UiAction[];
  trace: string[];
}

// Decision response — event is null when a wrong practice decision is held back
export interface DecisionResponse {
  event: CompanionEvent | null;
  decision_correct: boolean;
  explanation: string;
  affected_rows: string[];
  correct_decision: Decision | null; // null while a wrong practice decision is held back
  missed_and_walking_back: boolean;
}

// Recommendation types (simplified for mock)
export interface FactorBreakdown {
  coverage: number;
  confidence: number;
  interest: number;
  effort: number;
}

export interface GapItem {
  skill_id: string;
  state: SkillStateName;
  weight: number;
}

export interface RequirementCard {
  tasks: { task: string; onet: string; allocation: string }[];
  weights: { skill_id: string; base: number; scenario: number; because: string }[];
  evidence: { label: string; url: string; kind?: string }[];
}

export interface RoleRecommendation {
  role_id: string;
  rank: number;
  score: number;
  title?: string;
  factors: FactorBreakdown;
  formula: string;
  gap: GapItem[];
  requirement_card: RequirementCard;
  sources: { label: string; url: string }[];
  sdg_targets?: string[];
  score_note?: string;
  // readable ranking and role outlook (engine additions)
  fit?: number;
  time_to_ready?: TimeToReady;
  close_match?: boolean;
  matches_direction?: boolean | null; // v2.2: fits Profile.preferences.direction
  outlook?: RoleOutlook | null;
}

export interface TimeToReady {
  hours: number;
  weeks_at_current_budget: number;
}

export interface RoleOutlook {
  ai_handled_share: number;
  oversight_share: number;
  label: 'being transformed' | 'AI-era role' | 'stable';
  because: string;
  basis: string;
}

export interface Recommendation {
  user_id: string;
  scenario: Scenario;
  snapshot_id: string | null;
  assumptions_version: number;
  roles: RoleRecommendation[];
  changed_since?: ChangedSince | null;
  profile_inputs?: string[]; // v2.2: which profile answers shaped the ranking
}

export interface ChangedSince {
  assumptions_version: number | null;
  rank_changes: { role_id: string; from: number; to: number; because: string }[];
  outlook_changes?: {
    role_id: string;
    from_label: string;
    to_label: string;
    from_ai_handled_share: number;
    to_ai_handled_share: number;
    because: string;
  }[];
}

export interface PathStep {
  order: number;
  type: 'practice_case' | 'course' | 'checkin';
  ref: string;
  title: string;
  hours: number;
  skills: string[];
  cost: string;
  url?: string;
  retrieved?: string | null;
  sdg_targets?: string[];
  because?: string;
}

export interface Signal {
  entity: string;
  metric: string;
  geo: string | null;
  value: number;
  period: string | null;
}

export interface Snapshot {
  id: string;
  source: string;
  release_date: string;
  period: string;
  url?: string;
  geo?: string;
  retrieved_at?: string;
  signals?: Signal[];
  licence?: string | null;
  label?: string | null;
}

// HR summary (GET /api/hr/summary): null means suppressed (fewer than min_group_size people).
export interface HRSkillCount {
  skill_id: string;
  counts: Record<SkillStateName, number | null>;
}

export interface HRDemandItem {
  skill_id: string;
  people_without_demonstration: number | null;
  max_role_weight: number;
}

export interface HRSummaryData {
  team: string;
  group_size: number | null;
  min_group_size: number;
  suppressed: boolean;
  skills: HRSkillCount[];
  training_demand: { scenario: Scenario; skills: HRDemandItem[] }[];
  note: string;
}

export interface PathPlan {
  user_id: string;
  target_role_id: string;
  weekly_hours: number;
  robust_across: Scenario[];
  steps: PathStep[];
  total_hours: number;
  weeks: number;
  worst_case_gap: number;
  horizon_weeks?: number | null; // v2.2: 6 by default, or the person's timeframe
  profile_inputs?: string[]; // v2.2: which profile answers shaped the path
}

// GET /api/next-case/{user_id}: the case the engine picks next, and why.
export interface NextCase {
  case_id: string | null;
  because: string;
  skill_id?: string | null;
}

// GET /api/search and /api/resources/{skill_id}: engine says which search produced the results.
export interface SearchResult {
  document_id: string;
  kind: 'course' | 'course_candidate' | 'onet_task' | 'onet_dwa';
  title: string;
  score: number;
  rank: number;
  source: string;
  url: string;
  date: string;
  retriever: string;
}

export interface SearchResponse {
  query: string;
  engine: 'hybrid' | 'keyword';
  note: string;
  results: SearchResult[];
}

// HR: external evidence and company assumptions (layer A diff, layer B versions).
export type Allocation = 'human' | 'ai_drafts_human_reviews' | 'ai';

export interface CompanyAssumptions {
  version: number;
  updated_by: string;
  based_on_snapshot: string | null;
  scenarios: Record<Scenario, { tasks: Record<string, Allocation> }>;
  shift_rule: string;
  shift_fractions: Record<string, number>;
  task_descriptions: Record<string, string>;
  label?: string | null;
  change_note?: string | null;
  [extra: string]: unknown;
}

export interface SignalChange {
  entity: string;
  metric: string;
  geo: string | null;
  before: number | null;
  after: number | null;
  change: number | null;
  relative_change: number | null;
  significant: boolean;
}

export interface SnapshotDiff {
  from_id: string;
  to_id: string;
  from_period: string;
  to_period: string;
  label: string;
  changes: SignalChange[];
  suggested_assumption_reviews: { assumption_id: string; reason: string }[];
  note: string;
}

export interface IngestResult {
  ingested: string | null;
  active_snapshots: string[];
  diff: SnapshotDiff | null;
  label: string;
  message: string;
}

// Senior: companion playbook optimiser.
export interface OptimizerProposal {
  id: string;
  editable_scope: 'playbook';
  base_version: string;
  candidate_version: string;
  diff: string;
  optimisation_set: { before: string; after: string };
  acceptance_set: {
    before: string;
    after: string;
    criteria_hash: string;
    false_alarms_clean: { before: string; after: string };
    invalid_citations: number;
  };
  regressions: string[];
  status: 'pending' | 'approved' | 'rejected';
  decided_by: string | null;
  decided_at: string | null;
  rollback_to: string;
  rationale?: string | null;
  development_log?: string[];
}

export interface OptimizerStatus {
  state: 'idle' | 'running' | 'done' | 'failed';
  step: string;
  started_at: string | null;
  finished_at: string | null;
  proposal_id: string | null;
  error: string | null;
}

export interface PlaybookInfo {
  active_version: string;
  text: string;
  versions: string[];
}

// --- Future Skills Radar (GET /api/signals/*; snapshots only, trend signals, not forecasts) ---
export interface SignalSnapshotMeta {
  source: string;
  source_url: string;
  license: string;
  attribution: string;
  update_frequency: string;
  data_as_of: string; // latest date in the data, never the fetch date
  fetched_at: string;
  caveats: string[];
  age_days: number | null;
  stale: boolean;
}

export type SignalLabel = 'rising' | 'stable' | 'cooling' | 'insufficient_data';

export interface SignalPoint {
  month: string;
  mentions: number;
  total_posts: number;
  share: number | null; // null for a month with no thread
  index: number | null;
  ma_short: number | null;
  ma_long: number | null;
}

export interface SkillSignal {
  id: string;
  name: string;
  category: string;
  label: SignalLabel;
  change_12m: number | null;
  latest_sample_size: number;
  latest_total_posts: number;
  points: SignalPoint[];
}

export interface SkillSignalsSnapshot extends SignalSnapshotMeta {
  months: string[];
  params: { ma_short_months: number; ma_long_months: number; stale_after_days: number };
  series: SkillSignal[];
}

export interface MarketPulseSnapshot extends SignalSnapshotMeta {
  countries: string[];
  default_country: string;
  default_country_label: string;
  covers_malaysia: boolean;
  events: { month: string; label: string; url: string; verified: boolean }[];
  series: { series: string; country: string; country_name: string; points: { month: string; share_pct: number }[] }[];
}

export interface UserSignalSkill {
  id: string;
  name: string;
  label: SignalLabel;
  change_12m: number | null;
  latest_sample_size: number;
  why: string;
}

export interface UserSignals {
  user_id: string;
  source: string;
  attribution: string;
  data_as_of: string;
  stale: boolean;
  user_skills: UserSignalSkill[];
  user_skills_cooling: UserSignalSkill[];
  rising_skills_not_held: UserSignalSkill[];
  no_market_data: string[];
  note: string;
}
