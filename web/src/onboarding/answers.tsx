import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getProfile, getQuestionnaire, postProfile } from '../api'
import { useUserId } from '../persona'
import type { Preferences, Profile, Questionnaire, SkillLevel } from '../types'
import { bandFor, DEFAULT_TIMEFRAME, raise, toggle, YEAR_BANDS, type Levels } from './fields'

/**
 * The one onboarding answers object (QART_ONBOARDING_FLOW_SPEC §3): the same Profile and
 * Preferences the ranking reads, only split across three steps. Every change is kept as a draft
 * in this browser, so leaving mid-way and coming back restores the answers; completing a step
 * also saves it to the backend profile. `profileComplete` is set only when matching finishes.
 * The optional name stays in the browser and is never sent (no real personal data in the app).
 */

interface Draft {
  prefs: Preferences
  yearsBand: string
  weeklyHours: number
  name: string
}

export interface Answers extends Draft {
  loaded: boolean
  error: string | null
  q: Questionnaire | null
  profile: Profile | null
  profileComplete: boolean
  setComplete: (done: boolean) => void
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void
  setPrefs: (update: (p: Preferences) => Preferences) => void
  setYearsBand: (band: string) => void
  setWeeklyHours: (hours: number) => void
  setName: (name: string) => void
  chooseJob: (id: string) => void
  toggleTask: (id: string) => void
  toggleTool: (label: string) => void
  addSkills: (ids: string[]) => void
  cycleLevel: (id: string) => void
  removeSkill: (id: string) => void
  /** What is still missing before a step can be left (labels for the hint next to Next). */
  missing: (step: 1 | 2 | 3) => string[]
  save: () => Promise<void>
}

const AnswersContext = createContext<Answers | null>(null)
const draftKey = (userId: string) => `qart.answers.${userId}`
const completeKey = (userId: string) => `qart.profileComplete.${userId}`

/** Clears every saved draft and completion flag (used by Reset demo). */
export function clearSavedAnswers() {
  try {
    Object.keys(localStorage).filter(k => k.startsWith('qart.answers.') || k.startsWith('qart.profileComplete.')).forEach(k => localStorage.removeItem(k))
  } catch { /* storage blocked: nothing to clear */ }
}

function readDraft(userId: string): Draft | null {
  try {
    const raw = localStorage.getItem(draftKey(userId))
    return raw ? (JSON.parse(raw) as Draft) : null
  } catch {
    return null
  }
}

function fromProfile(profile: Profile, q: Questionnaire): Draft {
  const saved: Preferences = profile.preferences ?? {}
  const job = saved.current_job ?? q.current_roles.find(r => r.catalogue_role_id === profile.current_role_id)?.id ?? null
  const order = q.levels.map(l => l.id)
  let levels: Levels = saved.skill_levels ?? {}
  if (Object.keys(levels).length === 0) {
    const fromJob = q.current_roles.find(r => r.id === job)?.typical_skills ?? []
    const fromTasks = q.tasks.filter(t => saved.tasks?.includes(t.id)).flatMap(t => t.skills)
    const fromTools = q.tools.filter(t => saved.tools?.includes(t.label)).flatMap(t => t.skills)
    levels = raise({}, [...fromJob, ...fromTasks, ...fromTools], q.default_level, order)
  }
  return {
    prefs: { tools: [], formats: [], tasks: [], ...saved, current_job: job, skill_levels: levels, timeframe_months: saved.timeframe_months ?? DEFAULT_TIMEFRAME },
    yearsBand: bandFor(profile.years_experience),
    weeklyHours: profile.weekly_learning_hours || 4,
    name: '',
  }
}

export function AnswersProvider({ children }: { children: ReactNode }) {
  const userId = useUserId()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [q, setQ] = useState<Questionnaire | null>(null)
  const [draft, setDraft] = useState<Draft>({ prefs: { tools: [], formats: [] }, yearsBand: '', weeklyHours: 4, name: '' })
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [profileComplete, setProfileComplete] = useState(false)

  useEffect(() => {
    setLoaded(false)
    try { setProfileComplete(localStorage.getItem(completeKey(userId)) === 'true') } catch { setProfileComplete(false) }
    Promise.all([getProfile(userId), getQuestionnaire()]).then(([p, questionnaire]) => {
      setProfile(p)
      setQ(questionnaire)
      setDraft(readDraft(userId) ?? fromProfile(p, questionnaire))
      setLoaded(true)
    }).catch(() => setError('Could not load your answers.'))
  }, [userId])

  // Keep the draft in this browser on every change.
  useEffect(() => {
    if (!loaded) return
    try { localStorage.setItem(draftKey(userId), JSON.stringify(draft)) } catch { /* private window */ }
  }, [draft, loaded, userId])

  const setComplete = useCallback((done: boolean) => {
    setProfileComplete(done)
    try { localStorage.setItem(completeKey(userId), String(done)) } catch { /* private window */ }
  }, [userId])

  const setPrefs = useCallback((update: (p: Preferences) => Preferences) => setDraft(d => ({ ...d, prefs: update(d.prefs) })), [])
  const order: SkillLevel[] = useMemo(() => q?.levels.map(l => l.id) ?? [], [q])

  const value = useMemo<Answers>(() => {
    const prefs = draft.prefs
    const setPref = <K extends keyof Preferences>(key: K, v: Preferences[K]) => setPrefs(p => ({ ...p, [key]: v }))
    const addSkills = (ids: string[]) => q && setPrefs(p => ({ ...p, skill_levels: raise(p.skill_levels ?? {}, ids, q.default_level, order) }))
    const job = q?.current_roles.find(r => r.id === prefs.current_job)
    return {
      ...draft, loaded, error, q, profile, profileComplete, setComplete, setPref, setPrefs,
      setYearsBand: band => setDraft(d => ({ ...d, yearsBand: band })),
      setWeeklyHours: hours => setDraft(d => ({ ...d, weeklyHours: hours })),
      setName: name => setDraft(d => ({ ...d, name })),
      chooseJob: id => {
        setPref('current_job', id || null)
        addSkills(q?.current_roles.find(r => r.id === id)?.typical_skills ?? [])
      },
      toggleTask: id => {
        const on = (prefs.tasks ?? []).includes(id)
        setPref('tasks', toggle(prefs.tasks ?? [], id))
        if (!on) addSkills(q?.tasks.find(t => t.id === id)?.skills ?? [])
      },
      // "None of these" clears the other tool chips, and any other chip clears it (§4.5).
      toggleTool: label => {
        const chip = q?.tools.find(t => t.label === label)
        const exclusive = new Set(q?.tools.filter(t => t.exclusive).map(t => t.label))
        const current = prefs.tools ?? []
        const on = current.includes(label)
        setPref('tools', on ? current.filter(t => t !== label) : chip?.exclusive ? [label] : [...current.filter(t => !exclusive.has(t)), label])
        if (!on && chip) addSkills(chip.skills)
      },
      addSkills,
      cycleLevel: id => setPrefs(p => {
        const now = (p.skill_levels ?? {})[id]
        return { ...p, skill_levels: { ...p.skill_levels, [id]: order[(order.indexOf(now) + 1) % order.length] } }
      }),
      removeSkill: id => setPrefs(p => {
        const rest = { ...p.skill_levels }
        delete rest[id]
        return { ...p, skill_levels: rest }
      }),
      missing: step => {
        if (step === 1) return [!prefs.current_job && 'your current role', !draft.yearsBand && 'years of experience'].filter((x): x is string => Boolean(x))
        if (step === 2) return prefs.direction ? [] : ['where you want to go next']
        return []
      },
      save: async () => {
        if (!profile) throw new Error('profile not loaded')
        // Keep everything else in the profile (self-ratings, interests); only these answers change.
        const saved = await postProfile({
          ...profile,
          // A job that matches a catalogue role also updates the evidence engine's current role.
          current_role_id: job?.catalogue_role_id ?? profile.current_role_id,
          years_experience: YEAR_BANDS.find(b => b.label === draft.yearsBand)?.value ?? profile.years_experience,
          weekly_learning_hours: draft.weeklyHours,
          preferences: { ...prefs, notes: prefs.notes?.trim() || null },
        })
        setProfile(saved.profile)
      },
    }
  }, [draft, loaded, error, q, profile, profileComplete, setComplete, setPrefs, order])

  return <AnswersContext.Provider value={value}>{children}</AnswersContext.Provider>
}

export function useAnswers(): Answers {
  const ctx = useContext(AnswersContext)
  if (!ctx) throw new Error('useAnswers outside AnswersProvider')
  return ctx
}
