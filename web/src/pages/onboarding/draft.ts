import type { Extraction, ProfileData, Situation, SkillClaim, SkillKind } from '../../types'

/** What the person has told us so far in the CV popup; saved as their profile on "Continue". */
export type Draft = {
  situation: Situation | null // read from the CV; null = infer from role and years
  situationNote: string
  role: string
  years: string
  tasks: string
  skills: Record<string, SkillClaim>
  // Kept from a saved profile; set later on Roles (interests, SDGs) and Time and budget.
  hours: number
  budget: ProfileData['budget']
  interests: SkillKind[]
  sdgs: string[]
  engine: string
  intakeSeconds: number | null
}

export const EMPTY_DRAFT: Draft = {
  situation: null,
  situationNote: '',
  role: 'other',
  years: '',
  tasks: '',
  skills: {},
  hours: 6,
  budget: 'free',
  interests: [],
  sdgs: [],
  engine: 'none',
  intakeSeconds: null,
}

export type DraftAction =
  | { type: 'load'; profile: ProfileData }
  | { type: 'extracted'; result: Extraction }
  | { type: 'set'; patch: Partial<Draft> }
  | { type: 'add'; skills: string[]; level: number | null }

export function draftReducer(d: Draft, a: DraftAction): Draft {
  switch (a.type) {
    case 'load': {
      const p = a.profile
      return {
        situation: p.situation,
        situationNote: '',
        role: p.current_role,
        years: p.years_experience === null ? '' : String(p.years_experience),
        tasks: [...new Set(Object.values(p.skills).map((s) => s.evidence).filter(Boolean))].join('\n'),
        skills: p.skills,
        hours: p.weekly_hours,
        budget: p.budget,
        interests: p.interests,
        sdgs: p.sdg_priorities,
        engine: p.extraction_engine,
        intakeSeconds: p.intake_seconds ?? null,
      }
    }
    case 'extracted': {
      const r = a.result
      const skills: Record<string, SkillClaim> = {}
      for (const s of r.skills) skills[s.skill] = { level: s.level, evidence: s.evidence, source: s.level === null ? 'keyword' : 'cv' }
      return {
        ...d,
        situation: r.situation ?? d.situation,
        situationNote: r.situation_reason ?? '',
        role: r.current_role !== 'other' ? r.current_role : d.role,
        years: r.years_experience !== null ? String(r.years_experience) : d.years,
        interests: r.interests.length ? r.interests : d.interests,
        skills,
        tasks: [...new Set(r.skills.map((s) => s.evidence).filter(Boolean))].join('\n'),
        engine: r.engine,
      }
    }
    case 'set':
      return { ...d, ...a.patch }
    case 'add': {
      const skills = { ...d.skills }
      for (const id of a.skills) skills[id] ??= { level: a.level, evidence: '', source: 'self' }
      return { ...d, skills }
    }
  }
}

/** The situation as read from the CV, else inferred from the answers (as before the redesign). */
export function situationOf(d: Draft): Situation {
  if (d.situation) return d.situation
  if (d.role !== 'other') return 'working'
  return d.years === '' || Number(d.years) === 0 ? 'student' : 'switcher'
}

export function toProfile(d: Draft): ProfileData {
  const situation = situationOf(d)
  return {
    situation,
    current_role: situation === 'student' ? 'other' : d.role,
    years_experience: d.years === '' ? null : Number(d.years),
    weekly_hours: d.hours,
    budget: d.budget,
    interests: d.interests,
    sdg_priorities: d.sdgs,
    skills: d.skills,
    extraction_engine: d.engine,
    intake_seconds: d.intakeSeconds,
  }
}
