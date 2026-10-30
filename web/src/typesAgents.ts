// Types for owner A's Phase 2 endpoints (docs/PHASE2_PLAN.md §4: C6 progress check, C7 change
// test, C8 forecast, C9 status). They mirror the server's Pydantic models exactly; only owner A
// edits this file.

// ---- C7 change test (POST /api/profiles/{id}/evidence-test, src/api/evidence_test.py) ----

export type Override = { kind: 'occupation_share' | 'task_share'; key: string; value: number }
export type RoleRank = { role_id: string; title: string; rank: number; fit: number }
export type EvidenceTestOut = {
  label: string
  scenario: 'moderate' | 'fast'
  overrides: Override[]
  previous: Record<string, number | null>
  before: { roles: RoleRank[] }
  after: { roles: RoleRank[] }
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
  components: Record<string, string | number | null> | null
}
