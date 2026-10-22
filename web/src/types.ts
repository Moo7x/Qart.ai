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
  sdg_targets?: string[];
  because?: string;
}

export interface Snapshot {
  id: string;
  source: string;
  release_date: string;
  period: string;
  url?: string;
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
