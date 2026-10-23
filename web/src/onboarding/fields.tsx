import type { ReactNode } from 'react'
import { Check } from 'lucide-react'
import type { Preferences, QuestionnaireOption, SkillLevel } from '../types'
import { Tag } from '../ui'

// Years are chosen as a band; the profile stores a number, so each band maps to its midpoint
// (10+ maps to 12). Declared mapping, not data.
export const YEAR_BANDS = [
  { label: 'Under 2 years', value: 1 },
  { label: '2–5 years', value: 3.5 },
  { label: '5–10 years', value: 7.5 },
  { label: '10+ years', value: 12 },
]
export const bandFor = (years: number) =>
  YEAR_BANDS.reduce((best, b) => (Math.abs(b.value - years) < Math.abs(best.value - years) ? b : best)).label

export const DIRECTIONS: { value: NonNullable<Preferences['direction']>; label: string; hint: string }[] = [
  { value: 'grow', label: 'Grow in my current role', hint: 'Add AI and automation skills to the job I do now' },
  { value: 'adjacent', label: 'Move to a nearby role', hint: 'Use what I know in a new role, e.g. finance → data analyst' },
  { value: 'switch', label: 'Switch to a new field', hint: 'Start fresh in a different area' },
]
export const TIMEFRAMES: NonNullable<Preferences['timeframe_months']>[] = [3, 6, 12]
export const FORMATS = ['Hands-on cases', 'Short videos', 'Reading', 'Mentor sessions']
export const NOTES_MAX = 500 // matches the contract limit
export const DEFAULT_TIMEFRAME = 3 // a visible option, pre-selected (QART_NEXT_STEPS §4.2)
export const TASKS_SHOWN = 10 // the rest behind "Show more", so the question stays short
export type Levels = Record<string, SkillLevel>

/** Add skills at `level` without lowering a level the person already set (QART_NEXT_STEPS §3.2). */
export function raise(levels: Levels, skillIds: string[], level: SkillLevel, order: SkillLevel[]): Levels {
  const next = { ...levels }
  for (const id of skillIds) {
    const current = next[id]
    if (current === undefined || order.indexOf(level) > order.indexOf(current)) next[id] = level
  }
  return next
}

export const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter(x => x !== v) : [...list, v])

export function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button" aria-pressed={on} onClick={onClick}
      className={`inline-flex min-h-11 items-center gap-1 rounded-full px-4 py-2 text-sm transition-colors duration-200 ${on ? 'bg-action-tint text-action-ink font-medium' : 'bg-surface border border-hairline-strong text-graphite hover:bg-linen'}`}
    >
      {on && <Check size={14} strokeWidth={2} aria-hidden="true" />}
      {children}
    </button>
  )
}

/** One-choice chip row; tapping the chosen chip again clears it. */
export function ChoiceRow({ legend, aside, options, value, onChange }: {
  legend: ReactNode; aside?: ReactNode; options: QuestionnaireOption[]; value: string | null | undefined; onChange: (v: string | null) => void
}) {
  return (
    <fieldset>
      <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">{legend} {aside}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map(o => <Chip key={o.id} on={value === o.id} onClick={() => onChange(value === o.id ? null : o.id)}>{o.label}</Chip>)}
      </div>
    </fieldset>
  )
}

/** Required-field marker (the hint next to Next names what is missing). */
export const Req = () => <span className="text-coral-ink" aria-hidden="true"> *</span>

/** Truthful badges: each says whether an answer affects the ranking, the plan, or nothing. */
export function ShapesPathway({ what }: { what: string }) {
  return <Tag tone="action" title={what}>Shapes your pathway</Tag>
}
export function ShapesRanking({ what = 'These become your skills, which your role matches are scored on.' }: { what?: string }) {
  return <Tag tone="action" title={what}>Shapes your ranking</Tag>
}
export function ForPlan() {
  return <Tag tone="action" title="Your learning plan uses this to choose courses: budget, funding, format, certificate and language.">Shapes your learning plan</Tag>
}
export function EligibilityOnly() {
  return <Tag tone="linen" title="Only used to check who a course is open to (for example a programme for Malaysians aged 18–30). Never used to rank roles.">Only used to check course eligibility</Tag>
}
export function NoteOnly() {
  return <Tag tone="linen" title="Saved. Shown as a note on roles that often ask for more; it never changes a score.">Saved · shown as a note</Tag>
}
