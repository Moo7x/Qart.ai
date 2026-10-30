// Types for owner A's Phase 2 endpoints (docs/PHASE2_PLAN.md §4: C6 progress check, C7 change
// test, C8 forecast, C9 status). They mirror the server's Pydantic models exactly; only owner A
// edits this file.

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
