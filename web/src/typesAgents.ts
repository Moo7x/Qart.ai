// Types for owner A's Phase 2 endpoints (docs/PHASE2_PLAN.md §4: C6 progress check, C7 change
// test, C8 forecast, C9 status). They mirror the server's Pydantic models exactly; only owner A
// edits this file.

// ---- C7 change test (POST /api/profiles/{id}/evidence-test, src/api/evidence_test.py) ----

export type Override = { kind: 'occupation_share' | 'task_share' | 'group_change'; key: string; value: number }
export type CategoryChange = { role_id: string; title: string; before: string; after: string; current_job: boolean }
export type RoleRank = { role_id: string; title: string; rank: number; fit: number }
export type EvidenceTestOut = {
  label: string
  scenario: 'moderate' | 'fast'
  overrides: Override[]
  previous: Record<string, number | null>
  before: { roles: RoleRank[] }
  after: { roles: RoleRank[] }
  forecast?: CategoryChange[]
  weights: { role_id: string; skill: string; skill_name: string; before: number; after: number }[]
  pathway: null | {
    role_id: string
    title: string
    before: string[]
    after: string[]
    titles: Record<string, string>
    fit_after_before: number
    fit_after_after: number
  }
}

// ---- A7 resource scout (POST /api/agents/scout, GET /api/agents/runs/{id}, src/api/agents.py) ----

export type ScoutPick = {
  resource_id: string
  kind: 'video' | 'article'
  title: string
  url: string
  start: number | null
  end: number | null
  anchor: string
  score: number
  reason: string
  source: string
  // Articles: one link that highlights every chosen passage of the page at once.
  page_url?: string
  // Articles: the chosen passage, shortened, shown in the agent window.
  excerpt?: string
}
export type AgentRun = {
  id: string
  kind: string
  subject: string
  status: 'running' | 'done' | 'failed'
  engine: string
  started_at: string
  finished_at: string | null
  result: null | { skill: string; skill_name?: string; picks: ScoutPick[]; engine?: string; note: string }
  steps: { id: number; at: string; kind: 'think' | 'tool' | 'result' | 'note' | 'error'; text: string }[]
}

// ---- C9 status (GET /api/status, src/api/status.py) ----

export type UsageRow = {
  purpose: string
  engine: string
  model: string
  calls: number
  failed: number
  tokens_in: number
  tokens_out: number
  seconds: number
  cost_usd: number | null
}
export type EngineState = { configured: boolean; models: string[]; calls: number; failed: number }
export type StatusResponse = {
  sources: import('./types').SourceStatus[]
  runs: import('./types').Run[]
  schedule: string
  engines: { language_model: EngineState; gpu: EngineState }
  usage: UsageRow[]
  cost: { label: 'estimate'; total_usd: number; prices_checked: string; gpu_price_set: boolean; note: string; profiles?: number; per_person_usd?: number | null; per_month_usd?: Record<string, number> }
  fairness: { available: boolean; pairs?: number; identical?: boolean; max_fit_difference?: number; checked_at?: string }
  platform_sdg: { available: boolean; profiles?: number; min_profiles?: number; suppressed?: boolean; totals?: { target: string; hours: number }[] }
  time_to_plan?: { people: number; median_seconds: number | null; under_target: number; target_seconds: number; target_share: number; kind: 'observed' }
}

// ---- C8 forecast (GET /api/forecast, src/api/evidence.py SeriesForecast) ----

export type ForecastPoint = { period: string; point: number; low: number | null; high: number | null }

export type SeriesForecast = {
  series_id: string
  kind: 'employment_share' | 'job_ads' | 'role_outlook' | 'skill_outlook'
  title: string
  history: { period: string; value: number }[]
  forecast: ForecastPoint[]
  model: string | null
  baseline: string
  backtest: null | { ratio: number; baseline_ratio: number; ratios: Record<string, number>; origins: number; scale: string }
  label: 'estimate'
  source: string
  fetched_at: string | null
  note: string
  // Role outlooks add `evidence`: the role's own observed and expert facts (src/match/outlook.py).
  components: Record<string, string | number | null | OutlookEvidence[]> | null
}
export type OutlookEvidence = { kind: 'observed' | 'expert'; text: string; source: string }
