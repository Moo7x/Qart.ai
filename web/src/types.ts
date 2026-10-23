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
