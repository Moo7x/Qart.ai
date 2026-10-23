// Shapes returned by the FastAPI server (src/api/evidence.py, src/evidence/signals.py).
// Keep these exactly in step with the server models.

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
  field: string
  skills: PackSkill[]
  current_roles: CurrentRole[]
  destination_roles: { id: string; title: string }[]
  samples: { id: string; label: string }[]
  proficiency: string[]
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
}

export type SkillClaim = { level: number | null; evidence: string; source: 'cv' | 'self' | 'keyword' }
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
}

export type GapColumn = 'ready' | 'bridgeable' | 'missing' | 'not_stated'
export type AutomationBasis = 'task' | 'occupation' | 'none'
export type TaskEvidence = {
  task: string
  text: string
  automation_share: number | null
  importance: number | null
}
export type RequirementScore = {
  skill: string
  skill_name: string
  tier: 'core' | 'upskill' | 'support'
  essential: boolean
  required: number
  claimed: number | null
  base_weight: number
  weight: number
  shift_reason: string
  contribution: number
  column: GapColumn
  evidence_pages: number[]
  automation_share: number | null
  automation_basis: AutomationBasis
  tasks: TaskEvidence[]
}
export type SdgRef = { target: string; title: string; how: string }
export type RoleCard = {
  role_id: string
  title: string
  fit: number
  longer_route: boolean
  essential_gaps: string[]
  requirements: RequirementScore[]
  automation_share: number | null
  soc: string
  gap: Record<GapColumn, string[]>
  impact: string
  outlook: { kind: 'observed' | 'expert'; text: string; source: string }[]
  listed_transition: boolean
  effort_hours: number
  effort_weeks: number
  uncovered: string[]
  sdgs: SdgRef[]
  meters: Meters
  fit_range: { low: number; high: number }
}
export type MatchesResponse = {
  scenario: Scenario
  scenario_label: string
  horizon_years: number
  intensity: number
  evidence: { source: string; period: string; occupations: number }
  current_role: CurrentRole | null
  current_impact: string | null
  destination: string | null
  roles: RoleCard[]
}

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
export type PathwayStep = {
  order: number
  course: Course
  hours: number
  week_start: number
  week_end: number
  gains: { skill: string; skill_name: string; before: number; after: number }[]
  sdgs: SdgRef[]
  prerequisite_for: string[]
}
export type PathwayResponse = {
  role_id: string
  role_title: string
  weekly_hours: number
  steps: PathwayStep[]
  total_hours: number
  weeks: number
  uncovered: string[]
  partly_covered: string[]
  essentials_unmet: string[]
  fit_before: number
  fit_after: number
  sdg_summary: Record<string, string[]>
  pathway_sdgs: { target: string; how: string }[]
  sdg_targets: Record<string, { goal: number; title: string; text: string }>
  sdg_source: string
  courses_checked: string
  scenario: Scenario
}

export type FutureScenario = {
  fit_now: number
  fit_after: number
  hours: number
  weeks: number
  skills: { skill: string; name: string; required: number; now: number | null; after: number; essential: boolean }[]
  sdg_targets: string[]
  uncovered: string[]
}
export type FutureResponse = {
  destination: { id: string; title: string }
  current_role: string | null
  situation: Situation
  years_experience: number | null
  scenarios: Record<Scenario, FutureScenario>
}

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

export type RadarAxis = {
  skill: string
  name: string
  kind: SkillKind
  essential: boolean
  claimed: number | null
  required: number
  after: number
  emphasis: 'rising' | 'weakening' | 'stable' | 'fixed'
  weight_factor: number
  reason: string
  ai_use: { automation_share: number | null; basis: AutomationBasis; tasks_observed: number; tasks_linked: number } | null
  in_demand: boolean | null
}
export type RadarResponse = {
  role_id: string
  title: string
  chosen: boolean
  fit: number
  fit_after: number
  axes: RadarAxis[]
  field_signals: Signal[]
  scenario: Scenario
  scenario_label: string
}

// ---- Role explanation (src/match/explain.py) ----

export type Explanation = {
  sentences: { text: string; facts: { id: string; text: string }[] }[]
  engine: string
  note: string
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
  skills: { skill: string; name: string; ai_role: string; change: number; roles: number; basis: string[] }[]
  exposure: { isco: string; title: string; mean: number | null; gradient: string | null }[]
}
