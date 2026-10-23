import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Check, Plus, X } from 'lucide-react'
import { getNextCase, getProfile, getQuestionnaire, postProfile } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { Preferences, Profile, Questionnaire, SkillLevel } from '../types'
import { btn, Card, Highlight, input as inputCls, PageHeader, ProvenanceTag, Tag } from '../ui'

// Years are chosen as a band; the profile stores a number, so each band maps to its midpoint
// (10+ maps to 12). Declared mapping, not data.
const YEAR_BANDS = [
  { label: 'Under 2 years', value: 1 },
  { label: '2–5 years', value: 3.5 },
  { label: '5–10 years', value: 7.5 },
  { label: '10+ years', value: 12 },
]
const bandFor = (years: number) => YEAR_BANDS.reduce((best, b) => (Math.abs(b.value - years) < Math.abs(best.value - years) ? b : best)).label

const INDUSTRIES = ['Finance & accounting', 'Banking & insurance', 'Retail & e-commerce', 'Manufacturing & logistics', 'Healthcare', 'Public sector', 'Technology', 'Other']
const EDUCATION = ['SPM / secondary school', 'Diploma', "Bachelor's degree", "Master's or higher", 'Professional certification']
const DIRECTIONS: { value: NonNullable<Preferences['direction']>; label: string; hint: string }[] = [
  { value: 'grow', label: 'Grow in my current role', hint: 'Add AI and automation skills to the job I do now' },
  { value: 'adjacent', label: 'Move to a nearby role', hint: 'Use what I know in a new role, e.g. finance → data analyst' },
  { value: 'switch', label: 'Switch to a new field', hint: 'Start fresh in a different area' },
]
const TIMEFRAMES: NonNullable<Preferences['timeframe_months']>[] = [3, 6, 12]
const FORMATS = ['Hands-on cases', 'Short videos', 'Reading', 'Mentor sessions']
const NOTES_MAX = 500 // matches the contract limit
const DEFAULT_TIMEFRAME = 3 // a visible option, pre-selected (QART_NEXT_STEPS §4.2)
const TASKS_SHOWN = 10 // the rest behind "Show more", so the question stays short
type Levels = Record<string, SkillLevel>

/** Add skills at `level` without lowering a level the person already set (QART_NEXT_STEPS §3.2). */
function raise(levels: Levels, skillIds: string[], level: SkillLevel, order: SkillLevel[]): Levels {
  const next = { ...levels }
  for (const id of skillIds) {
    const current = next[id]
    if (current === undefined || order.indexOf(level) > order.indexOf(current)) next[id] = level
  }
  return next
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button" aria-pressed={on} onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-full px-3.5 py-2 text-sm transition-colors duration-200 ${on ? 'bg-action-tint text-action-ink font-medium' : 'bg-surface border border-hairline-strong text-graphite hover:bg-linen'}`}
    >
      {on && <Check size={14} strokeWidth={2} aria-hidden="true" />}
      {children}
    </button>
  )
}

/** Answers the engine uses for the pathway (contract v2.2). */
function Shapes({ what }: { what: string }) {
  return <Tag tone="action" title={what}>Shapes your pathway</Tag>
}

/** Answers that become the person's skills (held skills; contract v2.4). */
function BuildsSkills() {
  return <Tag tone="action" title="These become your skills, shown on the Signals page.">Builds your skills</Tag>
}

/** Answers kept in Profile.preferences that nothing reads yet. */
function SavedOnly() {
  return <Tag tone="linen" title="Stored in your profile. Nothing uses it yet.">Saved · not used yet</Tag>
}

function CardTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-base font-semibold text-ink">{children}</h2>
      {aside}
    </div>
  )
}

const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter(x => x !== v) : [...list, v])

export default function Intake() {
  const navigate = useNavigate()
  const userId = useUserId()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [q, setQ] = useState<Questionnaire | null>(null)
  const [allTasks, setAllTasks] = useState(false)
  const [adding, setAdding] = useState('')
  const [error, setError] = useState<string | null>(null)
  const name = profile?.display_name.replace(' (synthetic)', '') ?? ''
  const [yearsBand, setYearsBand] = useState('')
  const [weeklyHours, setWeeklyHours] = useState(4)
  const [prefs, setPrefs] = useState<Preferences>({ tools: [], formats: [] })
  const [submitting, setSubmitting] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [profile !== null && q !== null])

  // Pre-fill from the employee's saved profile so the form shows their current values. A profile
  // without a questionnaire job takes the job matching its catalogue role; one without skill
  // chips gets that job's typical skills (plus any saved tasks and tools) to edit.
  useEffect(() => {
    Promise.all([getProfile(userId), getQuestionnaire()]).then(([profile, q]) => {
      setProfile(profile)
      setQ(q)
      setYearsBand(bandFor(profile.years_experience))
      if (profile.weekly_learning_hours) setWeeklyHours(profile.weekly_learning_hours)
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
      setPrefs({
        tools: [], formats: [], tasks: [], ...saved,
        current_job: job, skill_levels: levels, timeframe_months: saved.timeframe_months ?? DEFAULT_TIMEFRAME,
      })
    }).catch(() => setError('Could not load your profile.'))
  }, [userId])

  const setPref = <K extends keyof Preferences>(key: K, value: Preferences[K]) => setPrefs(p => ({ ...p, [key]: value }))
  const order = q?.levels.map(l => l.id) ?? []
  const levels = prefs.skill_levels ?? {}
  const addSkills = (ids: string[]) => q && setPrefs(p => ({ ...p, skill_levels: raise(p.skill_levels ?? {}, ids, q.default_level, order) }))
  const skillName = (id: string) => q?.skills.find(s => s.id === id)?.name ?? id
  const levelLabel = (l: SkillLevel) => q?.levels.find(x => x.id === l)?.label ?? l
  const cycleLevel = (id: string) => setPrefs(p => {
    const now = (p.skill_levels ?? {})[id]
    return { ...p, skill_levels: { ...p.skill_levels, [id]: order[(order.indexOf(now) + 1) % order.length] } }
  })
  const removeSkill = (id: string) => setPrefs(p => {
    const rest = { ...p.skill_levels }
    delete rest[id]
    return { ...p, skill_levels: rest }
  })

  const job = q?.current_roles.find(r => r.id === prefs.current_job)
  const chooseJob = (id: string) => {
    setPref('current_job', id || null)
    addSkills(q?.current_roles.find(r => r.id === id)?.typical_skills ?? [])
  }
  const toggleTask = (id: string) => {
    const on = (prefs.tasks ?? []).includes(id)
    setPref('tasks', toggle(prefs.tasks ?? [], id))
    if (!on) addSkills(q?.tasks.find(t => t.id === id)?.skills ?? [])
  }
  // "None of these" clears the other tool chips, and any other chip clears it (§4.5).
  const toggleTool = (label: string) => {
    const chip = q?.tools.find(t => t.label === label)
    const exclusive = new Set(q?.tools.filter(t => t.exclusive).map(t => t.label))
    const current = prefs.tools ?? []
    const on = current.includes(label)
    const next = on ? current.filter(t => t !== label) : chip?.exclusive ? [label] : [...current.filter(t => !exclusive.has(t)), label]
    setPref('tools', next)
    if (!on && chip) addSkills(chip.skills)
  }
  // Tasks for the person's role family first, then the rest (stable order within each group).
  const tasks = q ? [...q.tasks].sort((a, b) => Number(!a.families.includes(job?.family ?? '')) - Number(!b.families.includes(job?.family ?? ''))) : []
  const shownTasks = allTasks ? tasks : tasks.slice(0, TASKS_SHOWN).concat(tasks.slice(TASKS_SHOWN).filter(t => prefs.tasks?.includes(t.id)))
  const heldIds = Object.keys(levels).sort((a, b) => skillName(a).localeCompare(skillName(b)))
  const addable = (q?.skills ?? []).filter(s => !(s.id in levels)).sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name))

  // Both buttons save first; they differ only in where they go next.
  const save = async (then: 'pathway' | 'practice') => {
    if (!profile) return
    setSubmitting(true)
    setError(null)
    try {
      // Keep everything else in the profile, including the stored self-ratings and interests
      // (no longer asked here); only the answers on this page change.
      await postProfile({
        ...profile,
        // A job that matches a catalogue role also updates the evidence engine's current role.
        current_role_id: job?.catalogue_role_id ?? profile.current_role_id,
        years_experience: YEAR_BANDS.find(b => b.label === yearsBand)?.value ?? profile.years_experience,
        weekly_learning_hours: weeklyHours,
        preferences: { ...prefs, notes: prefs.notes?.trim() || null },
      })
      if (then === 'pathway') {
        navigate('/signals')
      } else {
        const next = await getNextCase(userId).catch(() => null)
        navigate(next?.case_id ? `/workspace/${next.case_id}` : '/queue')
      }
    } catch {
      setError('Saving your answers failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div ref={root} className="max-w-3xl mx-auto">
      <PageHeader
        title={name ? <>Welcome, <Highlight>{name}</Highlight></> : 'Welcome'}
        intro="Tell us about your work and where you want to go. We'll turn it into your reskilling pathway."
        aside={name ? <ProvenanceTag kind="synthetic">{name} is a demo persona</ProvenanceTag> : undefined}
      />
      {error && <p role="alert" className="-mt-4 mb-6 rounded-md bg-coral-tint px-4 py-3 text-sm text-coral-ink">{error}</p>}

      <form onSubmit={e => { e.preventDefault(); save('pathway') }} className="space-y-4">
        <Card data-reveal className="p-6 space-y-5">
          <CardTitle>Where you are now</CardTitle>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
              Current role
              <select value={prefs.current_job ?? ''} onChange={e => chooseJob(e.target.value)} className={inputCls}>
                <option value="">Select…</option>
                {q?.current_roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
              <span className="inline-flex flex-wrap items-center gap-2">Industry <SavedOnly /></span>
              <select value={prefs.industry ?? ''} onChange={e => setPref('industry', e.target.value || null)} className={inputCls}>
                <option value="">Select…</option>
                {INDUSTRIES.map(o => <option key={o}>{o}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
              <span className="inline-flex flex-wrap items-center gap-2">Highest education <SavedOnly /></span>
              <select value={prefs.education ?? ''} onChange={e => setPref('education', e.target.value || null)} className={inputCls}>
                <option value="">Select…</option>
                {EDUCATION.map(o => <option key={o}>{o}</option>)}
              </select>
            </label>
          </div>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-ink mb-2">Years of experience</legend>
            <div className="flex flex-wrap gap-2">
              {YEAR_BANDS.map(b => <Chip key={b.label} on={yearsBand === b.label} onClick={() => setYearsBand(b.label)}>{b.label}</Chip>)}
            </div>
          </fieldset>
          <fieldset className="space-y-2">
            <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Which of these do you do most weeks? <span className="font-normal text-graphite">pick any</span> <BuildsSkills /></legend>
            <div className="flex flex-wrap gap-2">
              {shownTasks.map(t => <Chip key={t.id} on={(prefs.tasks ?? []).includes(t.id)} onClick={() => toggleTask(t.id)}>{t.label}</Chip>)}
              {tasks.length > TASKS_SHOWN && (
                <button type="button" onClick={() => setAllTasks(v => !v)} className="px-2 py-2 text-sm text-action-ink hover:underline">
                  {allTasks ? 'Show fewer' : `Show ${tasks.length - TASKS_SHOWN} more`}
                </button>
              )}
            </div>
          </fieldset>
          <fieldset className="space-y-2">
            <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Tools you use today <span className="font-normal text-graphite">pick any</span> <BuildsSkills /></legend>
            <div className="flex flex-wrap gap-2">
              {q?.tools.map(t => <Chip key={t.label} on={(prefs.tools ?? []).includes(t.label)} onClick={() => toggleTool(t.label)}>{t.label}</Chip>)}
            </div>
          </fieldset>
          <fieldset className="space-y-2 min-w-0">
            <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-1">Your skills <BuildsSkills /></legend>
            <p className="text-sm text-graphite">
              {heldIds.length > 0
                ? "We've added skills typical for your role and the tasks and tools you picked. Remove any you don't use, add any we missed, and tap a skill to change its level."
                : 'Pick your role, tasks or tools above, or add skills here.'}
            </p>
            <ul className="flex flex-wrap gap-2" aria-label="Your skills">
              {heldIds.map(id => (
                <li key={id} className="inline-flex items-stretch rounded-full bg-action-tint text-action-ink text-sm">
                  <button
                    type="button" onClick={() => cycleLevel(id)}
                    aria-label={`${skillName(id)}: ${levelLabel(levels[id])}. Change level`}
                    className="rounded-l-full pl-3.5 pr-2 py-2 text-left hover:bg-action/10 transition-colors duration-200"
                  >
                    <span className="font-medium">{skillName(id)}</span> <span className="text-xs">· {levelLabel(levels[id])}</span>
                  </button>
                  <button type="button" onClick={() => removeSkill(id)} aria-label={`Remove ${skillName(id)}`} className="rounded-r-full pl-1 pr-3 hover:bg-action/10 transition-colors duration-200">
                    <X size={14} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <label htmlFor="add-skill" className="sr-only">Add a skill</label>
              <select id="add-skill" value={adding} onChange={e => setAdding(e.target.value)} className={`${inputCls} w-full sm:w-auto sm:max-w-md min-w-0`}>
                <option value="">Add a skill…</option>
                {addable.map(s => <option key={s.id} value={s.id}>{s.name} ({s.category})</option>)}
              </select>
              <button type="button" disabled={!adding} onClick={() => { addSkills([adding]); setAdding('') }} className={btn.outline}>
                <Plus size={14} aria-hidden="true" /> Add
              </button>
            </div>
            <p className="text-xs text-graphite">Levels: {q?.levels.map(l => l.label).join(' · ')}. Skills you show in practice cases move up on their own.</p>
          </fieldset>
          <p className="text-xs text-graphite">Industry and education are saved with your profile; nothing uses them yet.</p>
        </Card>

        <Card data-reveal className="p-6 space-y-5">
          <CardTitle aside={<Shapes what="Direction picks which role your pathway is built for; timeframe sets how much it can hold." />}>Where do you want to go next?</CardTitle>
          <div className="grid gap-3 sm:grid-cols-3">
            {DIRECTIONS.map(d => {
              const on = prefs.direction === d.value
              return (
                <button
                  key={d.value} type="button" aria-pressed={on}
                  onClick={() => setPref('direction', on ? null : d.value)}
                  className={`text-left rounded-lg p-4 transition-colors duration-200 ${on ? 'bg-action-tint ring-2 ring-action' : 'bg-surface border border-hairline-strong hover:bg-linen'}`}
                >
                  <span className={`block font-semibold ${on ? 'text-action-ink' : 'text-ink'}`}>{d.label}</span>
                  <span className="block mt-1 text-sm text-graphite">{d.hint}</span>
                </button>
              )
            })}
          </div>
          <fieldset>
            <legend className="text-sm font-medium text-ink mb-2">Timeframe</legend>
            <div className="flex flex-wrap gap-2">
              {TIMEFRAMES.map(m => <Chip key={m} on={prefs.timeframe_months === m} onClick={() => setPref('timeframe_months', m)}>{m} months</Chip>)}
            </div>
          </fieldset>
          <p className="text-xs text-graphite">Your direction picks the role your pathway is built for. Your timeframe sets how much the pathway can hold; it starts at {DEFAULT_TIMEFRAME} months.</p>
        </Card>

        <Card data-reveal className="p-6 space-y-5">
          <CardTitle>How you learn</CardTitle>
          <div>
            <label htmlFor="weekly-hours" className="flex justify-between gap-3 text-sm font-medium text-ink">
              Time for learning each week <span className="tabular-nums text-action-ink">{weeklyHours} h</span>
            </label>
            <input id="weekly-hours" type="range" min={1} max={20} step={0.5} value={weeklyHours} onChange={e => setWeeklyHours(parseFloat(e.target.value))} className="mt-3 w-full" />
          </div>
          <div>
            <label htmlFor="ai-comfort" className="flex flex-wrap justify-between gap-2 text-sm font-medium text-ink">
              <span className="inline-flex flex-wrap items-center gap-2">How comfortable are you using AI tools at work? <Shapes what="At 3/10 or below, an intro-to-AI course goes first in your pathway." /></span>
              <span className="tabular-nums text-action-ink">{prefs.ai_comfort == null ? 'not set' : `${prefs.ai_comfort}/10`}</span>
            </label>
            {/* Until it is set the handle is hidden, so the label and the handle never disagree (§4.1). */}
            <input
              id="ai-comfort" type="range" min={0} max={10} step={1} value={prefs.ai_comfort ?? 5}
              onChange={e => setPref('ai_comfort', parseInt(e.target.value, 10))}
              onPointerUp={e => setPref('ai_comfort', parseInt(e.currentTarget.value, 10))}
              aria-valuetext={prefs.ai_comfort == null ? 'not set' : `${prefs.ai_comfort} out of 10`}
              className={`mt-3 w-full ${prefs.ai_comfort == null ? '[&::-webkit-slider-thumb]:opacity-0 [&::-moz-range-thumb]:opacity-0' : ''}`}
            />
            <p className="mt-1 text-xs text-graphite">
              {prefs.ai_comfort == null ? 'Tap the line to set it. ' : <button type="button" onClick={() => setPref('ai_comfort', null)} className="text-action-ink hover:underline mr-1">Clear</button>}
              At 3/10 or below, an intro-to-AI course goes first in your pathway.
            </p>
          </div>
          <fieldset>
            <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Preferred format <SavedOnly /></legend>
            <div className="flex flex-wrap gap-2">
              {FORMATS.map(f => <Chip key={f} on={(prefs.formats ?? []).includes(f)} onClick={() => setPref('formats', toggle(prefs.formats ?? [], f))}>{f}</Chip>)}
            </div>
          </fieldset>
          <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
            <span>Anything else we should know? <span className="font-normal text-graphite">(optional)</span></span>
            <textarea
              rows={3} maxLength={NOTES_MAX} value={prefs.notes ?? ''}
              onChange={e => setPref('notes', e.target.value)}
              placeholder="e.g. I can only study on weekends, I'd like a certificate at the end"
              className={`${inputCls} resize-y`}
            />
            <span className="text-xs font-normal text-graphite">Demo data only. Saved with your profile; never sent to the AI companion.</span>
          </label>
        </Card>

        <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3 pt-2">
          <button type="button" onClick={() => save('practice')} disabled={submitting || !profile} className={btn.text}>
            Or start practising now <ArrowRight size={16} aria-hidden="true" />
          </button>
          <button type="submit" disabled={submitting || !profile} className={`${btn.primary} py-3 px-6`}>
            {submitting ? 'Saving…' : <>Build my reskilling pathway <ArrowRight size={16} aria-hidden="true" /></>}
          </button>
        </div>
      </form>
    </div>
  )
}
