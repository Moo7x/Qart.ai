// Types for owner B's Phase 2 endpoints (docs/PHASE2_PLAN.md §4: C1 levels, C2 role score,
// C3 pathway steps, C4 SDG matrix, C5 badges). They mirror the server's Pydantic models exactly;
// only owner B edits this file.

// C1: GET /api/pack → levels (src/api/journey.py _levels_out, src/levels.py).
export type LevelScaleEntry = { level: number; label: string; meaning: string }
export type LevelBasis = { title: string; url: string; read: string }
export type SkillLevels = {
  anchors: Record<string, string> // "1"–"5" → "I can…" sentence
  basis: LevelBasis[]
  status: 'draft' | 'reviewed'
}
export type LevelsInfo = {
  checked: string
  scale: LevelScaleEntry[]
  rules: string[]
  skills: Record<string, SkillLevels>
}

// C2: added to every role in GET /api/profiles/{id}/matches (src/match/decision.py).
export type Band = 'strong' | 'good' | 'fair' | 'low'
export type FitRange = { low: number; high: number; basis?: string }
export type RoleComponent = {
  skill: string
  skill_name: string
  weight: number
  claimed: number | null
  required: number
  points: number
  evidenced: boolean
  evidence: string
  source: '' | 'cv' | 'self' | 'keyword' | 'agent_check'
}
export type RaiseOption = {
  skill: string
  skill_name: string
  from_level: number | null
  to_level: number
  points: number
  via: 'study' | 'practice' | 'check'
}
// Band thresholds as the server declares them (params.BAND_THRESHOLDS), labelled an assumption.
export type BandRules = { thresholds: Record<string, number>; below: Band; kind: 'assumption' }

// C11: the role's occupation-group pay (src/match/pay.py); null = not published, never 0.
export type RolePay = {
  group: string
  group_title: string
  year: string
  median: number
  mean: number | null
  overall_median: number | null
  unit: string
  kind: 'observed'
  source: string
  fetched_at: string
  cited_span: string
  note: string
}

// C3: plan steps and totals (GET /api/profiles/{id}/pathway and the nodes of /tracks).
export type StepTime = {
  value: number
  unit: 'hours' | 'weeks'
  basis: 'reading_estimate' | 'guided_hours' | 'stated' | 'practice_estimate'
  low: number | null
  high: number | null
}
export type StepUnlock = 'previous_step' | 'study_done' | 'level_check' | null
export type PracticeStep = {
  order: number
  kind: 'practice'
  id: string
  skill: string
  skill_name: string
  target_level: number
  text: string
  show_by: string
  time: StepTime
  week_start: { low: number; high: number }
  basis: { title: string; url: string; read: string }[]
  locked: boolean
  unlock: StepUnlock
  status: 'open' | 'done' | 'skipped'
  status_label: string
}
export type EstimateRange = { low: number; high: number; kind: 'estimate' }
