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
