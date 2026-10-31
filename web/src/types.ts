// Shapes returned by the FastAPI server (src/api/evidence.py, src/evidence/signals.py).
// Keep these exactly in step with the server models.

import type * as api from './apiTypes'
import type { LevelsInfo } from './typesScoring'

export type Direction = 'rising' | 'weakening' | 'stable' | 'insufficient' | 'expert'

export type Point = { period: string; value: number }

export type Evidence = {
  source_id: string
  period: string
  value: number | null
  cited_span: string
  url: string
  published: string | null
  fetched: string
}

export type SourceCard = {
  id: string
  name: string
  publisher: string
  terms: string
  shows: string
  does_not_show: string
}

export type Signal = {
  id: string
  title: string
  family: string
  kind: 'observed' | 'expert'
  direction: Direction
  early_direction: 'up' | 'down' | 'flat' | null
  headline: string
  unit: string
  points: Point[]
  independent_sources: number
  note: string
  sources: SourceCard[]
  evidence: Evidence[]
}

export type SignalsResponse = {
  generated_at: string
  observations: number
  signals: Signal[]
}

export type SourceStatus = {
  id: string
  name: string
  publisher: string
  family: string
  url: string
  terms: string
  terms_url: string
  terms_checked: string | null
  attribution: string
  tier: string
  cadence: string
  shows: string
  does_not_show: string
  notes: string
  observations: number
  last_fetched: string | null
  last_status: string | null
  last_note: string | null
  last_attempt_at: string | null
  last_success_at: string | null
  serving_snapshot_from: string | null
}

export type RunSource = {
  source_id: string
  status: 'ok' | 'failed'
  fetched: number
  new: number
  note?: string
  error?: string
  attempts?: number
  seconds?: number
}

export type Run = {
  id: number
  trigger: string
  started_at: string
  finished_at: string | null
  status: string
  new_observations: number
  sources: RunSource[]
}

export type BacktestEntry = {
  group: string
  naive: number
  linear: number
  damped: number
  best: string
}

// ---- Journey (src/api/journey.py) ----

export type Scenario = 'moderate' | 'fast'
export type Situation = 'working' | 'student' | 'switcher'
export type SkillKind = 'finance_core' | 'data_digital' | 'green' | 'business'

export type PackSkill = { id: string; name: string; kind: SkillKind; ai_role: string; page: number }
export type CurrentRole = {
  id: string
  title: string
  impact: string
  page: number
  soc: string
  summary: string
  typical_skills: string[]
  transitions: string[]
  other_sectors: string[]
}
export type PackInfo = {
  task_examples: { role_id: string; soc: string; text: string; source: string; url: string }[]
  field: string
  skills: PackSkill[]
  current_roles: CurrentRole[]
  destination_roles: { id: string; title: string }[]
  samples: { id: string; label: string }[]
  proficiency: string[]
  levels?: LevelsInfo
  courses_checked: string
}

export type ClaimedSkill = { skill: string; name: string; level: number | null; evidence: string }
export type Extraction = {
  current_role: string
  years_experience: number | null
  skills: ClaimedSkill[]
  interests: SkillKind[]
  engine: string
  note: string
  removed: Record<string, number>
  rejected: { skill: string; reason: string }[]
  unmatched?: string[]
  stages?: Stage[]
  situation?: Situation
  situation_reason?: string
}

export type SkillClaim = {
  level: number | null
  evidence: string
  source: 'cv' | 'self' | 'keyword' | 'agent_check'
  checked_at?: string
  model?: string
}
export type ProfileData = {
  situation: Situation
  current_role: string
  years_experience: number | null
  weekly_hours: number
  budget: 'free' | 'free_hrd' | 'up_to_500'
  interests: SkillKind[]
  sdg_priorities: string[]
  skills: Record<string, SkillClaim>
  extraction_engine: string
  intake_seconds?: number | null
}

export type GapColumn = 'ready' | 'bridgeable' | 'missing' | 'not_stated'
export type AutomationBasis = 'task' | 'occupation' | 'none'
export type TaskEvidence = api.TaskEvidence
export type RequirementScore = api.RequirementScore
export type SdgRef = { target: string; title: string; how: string }
export type RoleCard = api.RoleCard
export type MatchesResponse = api.MatchesOut

export type Course = {
  id: string
  title: string
  provider: string
  url: string
  minutes: number
  level: string
  covers: string[]
  requires: string[]
}
export type PathwayStep = api.Step
export type PathwayResponse = api.PathwayOut

export type FutureScenario = api.FutureScenario
export type FutureRole = api.FutureRole
export type FutureResponse = api.FutureOut

export type EvidenceDelta = {
  source_id: string; entity: string; metric: string; geography: string
  before_period: string | null; after_period: string | null
  before: number | null; after: number | null; unit: string; url: string
  published: string | null; cited_span: string; comparable: boolean
}
export type WeightDelta = {
  skill: string; name: string; before: number; after: number
  points_before: number; points_after: number; essential: boolean; reason: string
  share_before: number | null; share_after: number | null
  basis_before: AutomationBasis; basis_after: AutomationBasis
}
export type RoleDelta = {
  role_id: string; title: string; soc: string; rank_before: number; rank_after: number
  fit_before: number; fit_after: number; weights: WeightDelta[]
}
export type PathSummary = {
  course_ids: string[]; courses: { id: string; title: string; url: string }[]
  hours: number; weeks: number; essential_gaps: string[]
}
export type ChangeReport = {
  mode: 'live' | 'replay'; scenario: Scenario; before_label: string; after_label: string
  evidence: EvidenceDelta[]; roles: RoleDelta[]; recommendation_changed: boolean; notes: string[]
  pathway: null | {
    role_id: string; title: string; before: PathSummary; after: PathSummary
    added: string[]; removed: string[]; reordered: boolean
  }
}
export type Proposal = {
  id: number; scenario: Scenario; status: string; actionable: boolean
  created_at: string; run_id: number | null; report: ChangeReport
}
export type ChangesResponse = {
  accepted_cutoff: number; latest_cutoff: number; proposals: Proposal[]
  replay_sources: { source_id: string; periods: string[] }[]
}

// ---- Role tasks (src/match/tasks.py) ----

export type TaskUse = {
  share: number | null
  automation: number | null
  augmentation: number | null
  share_local: number | null
  period: string
  url: string
}
export type RoleTask = {
  task: string
  text: string
  skills: string[]
  observed_use: TaskUse | null
  importance: { value: number | null; release: string; url: string } | null
}
export type RoleTasksResponse = {
  role_id: string
  soc: string
  occupation: { code: string; name: string; isco: string | null; esco: string | null; esco_match: string | null; esco_uri: string | null } | null
  tasks: RoleTask[]
  exposure: null | {
    isco: string
    title: string
    mean: number | null
    gradient: string | null
    url: string
    published: string | null
    tasks: { text: string; score: number | null }[]
  }
  expert: { impact: string; text: string }
  deployment: null
  summary: string
  unlinked_skills: string[]
  sources: { tasks: string; observed_use: string; exposure: string; expert: string }
}

// ---- Personal radar (src/match/radar.py) ----

export type RadarAxis = api.RadarAxis
export type RadarResponse = api.RadarOut

// ---- Role explanation (src/match/explain.py) ----

export type Explanation = {
  sentences: { text: string; facts: { id: string; text: string }[] }[]
  engine: string
  note: string
  stages?: Stage[]
}

// ---- Trend model versions (src/evidence/models.py) ----

export type ModelVersion = {
  id: number
  group_id: string
  created_at: string
  run_id: number | null
  first_year: string
  last_year: string
  points: number
  train_end: number
  test_years: string
  naive: number
  linear: number
  damped: number
  best: 'naive' | 'linear' | 'damped'
}

// ---- Decision support (src/match/decision.py, src/pathway/optimise.py) ----

export type Meters = {
  coverage: number
  essentials_ready: boolean
  essentials_below: string[]
  essentials_unstated: string[]
  completeness: number
  stated: number
  requirements: number
}
export type Question = {
  skill: string
  skill_name: string
  value: number
  top_role_changes: boolean
  essential_for: string[]
  swing: number
  effect: string
}
export type SensitivityResponse = {
  intensities: number[]
  roles: { role_id: string; title: string; ranks: number[]; stable: boolean }[]
}
export type WhatIfResponse = {
  roles: { role_id: string; title: string; rank_now: number; rank_then: number; fit_now: number; fit_then: number }[]
  pathway: null | { role_id: string; now: { hours: number; weeks: number }; then: { hours: number; weeks: number } }
}
export type PlanOption = {
  course_ids: string[]
  courses: { id: string; title: string; url: string; hours: number }[]
  hours: number
  fit_after: Record<Scenario, number>
  essentials_reached: number
  essentials_total: number
}
export type PlansResponse = {
  role_id: string
  scenario: Scenario
  budget_hours: number
  budget_weeks: number
  fit_now: number
  relevant_courses: number
  exact: boolean
  plans: { greedy: PlanOption; best?: PlanOption; robust?: PlanOption }
  note: string
}
export type ForecastCheck = {
  group: string
  horizon: number
  origins: number[]
  mae: Record<string, number>
  best: string | null
}

// ---- Trends (src/evidence/trends.py) ----

export type TrendsResponse = {
  employment: {
    group: string
    major_group: string
    title: string
    points: Point[]
    first: string
    last: string
    change_long: number
    change_recent: number | null
  }[]
  recent_from: string
  job_ads: { quarters: string[]; breaks: string[]; professionals: Point[]; named: { entity: string; points: Point[] }[] }
  skills: TrendSkill[]
  skills_by_scenario: Record<Scenario, TrendSkill[]>
  evidence_period: string
  evidence_source: string
  exposure: { isco: string; title: string; mean: number | null; gradient: string | null }[]
}
export type TrendSkill = { skill: string; name: string; ai_role: string; change: number; roles: number; basis: string[] }

// ---- Occupations (src/occupations/) ----

export type Detection = {
  query: string
  engine: string
  note: string
  stages?: Stage[]
  matches: { soc: string; title: string; score: number; in_field: boolean }[]
}
export type OccupationPreview = {
  soc: string
  title: string
  description: string
  in_field: boolean
  coverage: string
  esco: { title: string | null; match: string | null; uri: string | null }
  isco: string | null
  isco_note: string
  tasks: { task: string; text: string; importance: number | null }[]
  ai_use: null | { share: number; share_local: number | null; automation: number | null; period: string; url: string }
  exposure: null | { isco: string; title: string; mean: number | null; gradient: string | null; tasks: { text: string; score: number | null }[]; url: string }
  employment: Signal | null
  mycol: null | { listed: boolean; name: string | null; of: number }
}

// ---- Goal (src/goal/, src/api/goal.py) ----

export type GoalInput = {
  role_title: string
  company: string
  location: string
  why: string
  posting_text: string
  posting_url: string
  posting_date: string
}
export type PostingRequirement = {
  quote: string
  skill: string | null
  skill_name: string | null
  essential: boolean
  required_level: number | null
  claimed: number | null
  status: 'met' | 'below' | 'not_stated' | 'outside_catalogue'
}
export type GoalResponse = {
  goal: GoalInput | null
  coverage?: null | {
    engine: string
    note: string
    requirements: PostingRequirement[]
    covered: number
    mapped: number
    not_stated: number
    outside_catalogue: number
    essentials_met: number
    essentials: number
    default_level: number
  }
  stages?: Stage[]
  stepping_stones?: { role_id: string; title: string; shared: string[]; overlap: number; fit: number; longer_route: boolean; shared_courses: { id: string; title: string; url: string }[] }[]
}

// ---- Progress (src/journey/progress.py, src/api/decision.py) ----

export type ProgressResponse = {
  done: string[]
  paused: boolean
  skipped?: string[]
  updated_at: string | null
  plan: null | {
    role_id: string
    steps: number
    steps_done: number
    hours: number
    hours_done: number
    coverage: number
    open_questions: number
    this_week: { id: string; title: string; hours: number }[]
    weekly_hours: number
  }
}

export type Stage = { name: string; engine: string; outcome: string; seconds: number }

// ---- My plan tracks (src/pathway/tracks.py, GET /api/profiles/{id}/tracks) ----

export type CourseFitCheck = { result: 'fits' | 'does_not_fit' | 'unclear'; by: string; quote: string; checked: string }
export type TrackCourse = api.TrackCourse
export type TrackVideo = api.TrackVideo
export type TrackArticle = api.TrackArticle
export type SkillBasis = { kind: 'talentcorp' | 'onet' | 'onet_tech' | 'assumption' | 'ai_trend'; text: string; source: string }
export type TrackNode = api.TrackNode
export type Track = api.Track
export type RouteMetrics = api.RouteMetrics
export type TracksResponse = api.TracksOut

// GET /api/forecast/industry (src/api/forecast.py, src/forecast/industry.py)
export type IndustryCategory = 'growing' | 'transforming' | 'shrinking' | 'emerging' | 'stable'
export interface IndustryRoleForecast {
  id: string
  title: string
  soc: string | null
  occupation: string | null
  soc_reason: string | null
  destination: boolean
  pack_role: string | null
  category: IndustryCategory
  label: string
  meaning: string
  reasons: string[]
  demand: { group: string | null; critical: boolean | null; change_pp?: number | null; model?: string | null; note?: string; source?: string | null; fetched?: string | null }
  ai: { use: number | null; use_observed_share: number | null; tasks_observed: number; tasks_predicted: number; exposure: number | null; talentcorp_impact: number | null }
}
export interface SkillForecast {
  skill: string
  name: string
  trend: 'rising' | 'steady' | 'declining'
  ai_role: string
  demand_change_pp: number | null
  ai_use: number | null
  needed_by: string[]
}
export interface TaskModelSummary {
  version: number
  trained: string | null
  period: string
  features: string
  training_tasks: number
  predicted_tasks: number
  best: string
  mae: number | null
  baseline_mae: number | null
  scores: Record<string, number>
  source: string
}
export interface IndustryForecastResponse {
  scenario: 'moderate' | 'fast'
  intensity: number
  roles: IndustryRoleForecast[]
  skills: SkillForecast[]
  task_model: TaskModelSummary | null
  kind: 'estimate'
}
export type ReskillResponse = api.ReskillOut
