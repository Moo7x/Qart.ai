// Types for owner B's Phase 2 endpoints (docs/PHASE2_PLAN.md §4: C1 levels, C2 role score,
// C3 pathway steps, C4 SDG matrix, C5 badges). They mirror the server's Pydantic models exactly;
// only owner B edits this file. Answers with a server model are aliases of the generated types
// in apiTypes.ts (python -m scripts.api_types), so they cannot drift from the server.

import type * as api from './apiTypes'

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
export type RoleComponent = api.Component
export type RaiseOption = api.RaiseOption
// Band thresholds as the server declares them (params.BAND_THRESHOLDS), labelled an assumption.
export type BandRules = { thresholds: Record<string, number>; below: Band; kind: 'assumption' }

// C11: the role's occupation-group pay (src/match/pay.py); null = not published, never 0.
export type RolePay = api.Pay

// C3: plan steps and totals (GET /api/profiles/{id}/pathway and the nodes of /tracks).
export type StepTime = api.TimeEstimate
export type StepUnlock = 'previous_step' | 'study_done' | 'level_check' | null
export type PracticeStep = api.PracticeStep
export type EstimateRange = api.FitRange

// C4: GET /api/profiles/{id}/sdg (src/pathway/sdg.py SdgMatrix).
export type SdgReason = api.SdgReason
export type SdgMatrix = api.SdgMatrix

// C5: GET /api/profiles/{id}/badges (src/api/badges.py Badge), derived only from events.
export type Badge = api.Badge
