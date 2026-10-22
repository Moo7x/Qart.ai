import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Check } from 'lucide-react'
import { getNextCase, getProfile, getRoles, postProfile } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { Preferences, Profile, Role } from '../types'
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
const TOOLS = ['Excel', 'SQL', 'Python', 'Power BI / Tableau', 'ERP (SAP, Oracle)', 'AI assistants', 'None of these']
const DIRECTIONS: { value: NonNullable<Preferences['direction']>; label: string; hint: string }[] = [
  { value: 'grow', label: 'Grow in my current role', hint: 'Add AI and automation skills to the job I do now' },
  { value: 'adjacent', label: 'Move to a nearby role', hint: 'Use what I know in a new role, e.g. finance → data analyst' },
  { value: 'switch', label: 'Switch to a new field', hint: 'Start fresh in a different area' },
]
const TIMEFRAMES: NonNullable<Preferences['timeframe_months']>[] = [3, 6, 12]
const FORMATS = ['Hands-on cases', 'Short videos', 'Reading', 'Mentor sessions']
const NOTES_MAX = 500 // matches the contract limit

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

/** Answers kept in Profile.preferences: saved, but no engine factor reads them yet. */
function NotScored() {
  return <Tag tone="linen" title="Stored in your profile. The ranking does not use it yet.">Saved · not used for ranking yet</Tag>
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
  const [roles, setRoles] = useState<Role[]>([])
  const [error, setError] = useState<string | null>(null)
  const name = profile?.display_name.replace(' (synthetic)', '') ?? ''
  const [roleId, setRoleId] = useState('')
  const [yearsBand, setYearsBand] = useState('')
  const [weeklyHours, setWeeklyHours] = useState(4)
  const [prefs, setPrefs] = useState<Preferences>({ tools: [], formats: [] })
  const [submitting, setSubmitting] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [profile !== null])

  // Pre-fill from the employee's saved profile so the form shows their current values
  useEffect(() => {
    getRoles().then(setRoles).catch(() => setRoles([]))
    getProfile(userId).then(profile => {
      setProfile(profile)
      setRoleId(profile.current_role_id)
      setYearsBand(bandFor(profile.years_experience))
      if (profile.weekly_learning_hours) setWeeklyHours(profile.weekly_learning_hours)
      setPrefs({ tools: [], formats: [], ...profile.preferences })
    }).catch(() => setError('Could not load your profile.'))
  }, [userId])

  const setPref = <K extends keyof Preferences>(key: K, value: Preferences[K]) => setPrefs(p => ({ ...p, [key]: value }))

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
        current_role_id: roleId || profile.current_role_id,
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

  const currentRoles = roles.filter(r => r.internal)
  const roleOptions = currentRoles.length ? currentRoles : roles

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
              <select value={roleId} onChange={e => setRoleId(e.target.value)} className={inputCls}>
                {roleOptions.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
              Industry <span className="sr-only">(saved, not used for ranking yet)</span>
              <select value={prefs.industry ?? ''} onChange={e => setPref('industry', e.target.value || null)} className={inputCls}>
                <option value="">Select…</option>
                {INDUSTRIES.map(o => <option key={o}>{o}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
              Highest education
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
            <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Tools you use today <span className="font-normal text-graphite">pick any</span> <NotScored /></legend>
            <div className="flex flex-wrap gap-2">
              {TOOLS.map(t => <Chip key={t} on={(prefs.tools ?? []).includes(t)} onClick={() => setPref('tools', toggle(prefs.tools ?? [], t))}>{t}</Chip>)}
            </div>
          </fieldset>
          <p className="text-xs text-graphite">Industry and education are saved with your profile; the ranking does not use them yet.</p>
        </Card>

        <Card data-reveal className="p-6 space-y-5">
          <CardTitle aside={<NotScored />}>Where do you want to go next?</CardTitle>
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
              {TIMEFRAMES.map(m => <Chip key={m} on={prefs.timeframe_months === m} onClick={() => setPref('timeframe_months', prefs.timeframe_months === m ? null : m)}>{m} months</Chip>)}
            </div>
          </fieldset>
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
              <span className="inline-flex flex-wrap items-center gap-2">How comfortable are you using AI tools at work? <NotScored /></span>
              <span className="tabular-nums text-action-ink">{prefs.ai_comfort == null ? 'not set' : `${prefs.ai_comfort}/10`}</span>
            </label>
            <input id="ai-comfort" type="range" min={0} max={10} step={1} value={prefs.ai_comfort ?? 5} onChange={e => setPref('ai_comfort', parseInt(e.target.value, 10))} className="mt-3 w-full" />
          </div>
          <fieldset>
            <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Preferred format <NotScored /></legend>
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
