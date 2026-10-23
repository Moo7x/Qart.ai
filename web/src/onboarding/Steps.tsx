import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import type { Preferences } from '../types'
import { btn, input as inputCls } from '../ui'
import { useAnswers } from './answers'
import {
  Chip, ChoiceRow, DEFAULT_TIMEFRAME, DIRECTIONS, EligibilityOnly, ForPlan, FORMATS, NOTES_MAX, NoteOnly, Req,
  ShapesPathway, ShapesRanking, TASKS_SHOWN, TIMEFRAMES, toggle, YEAR_BANDS,
} from './fields'

/** Step 1 — Where you are now: role (with skill pre-fill), background, tasks, tools, skill chips. */
export function StepWhereNow() {
  const a = useAnswers()
  const { q, prefs } = a
  const [allTasks, setAllTasks] = useState(false)
  const [adding, setAdding] = useState('')
  const levels = prefs.skill_levels ?? {}
  const skillName = (id: string) => q?.skills.find(s => s.id === id)?.name ?? id
  const levelLabel = (l: string) => q?.levels.find(x => x.id === l)?.label ?? l
  const job = q?.current_roles.find(r => r.id === prefs.current_job)
  // Tasks for the person's role family first, then the rest (stable order within each group).
  const tasks = q ? [...q.tasks].sort((x, y) => Number(!x.families.includes(job?.family ?? '')) - Number(!y.families.includes(job?.family ?? ''))) : []
  const shownTasks = allTasks ? tasks : tasks.slice(0, TASKS_SHOWN).concat(tasks.slice(TASKS_SHOWN).filter(t => prefs.tasks?.includes(t.id)))
  const heldIds = Object.keys(levels).sort((x, y) => skillName(x).localeCompare(skillName(y)))
  const addable = (q?.skills ?? []).filter(s => !(s.id in levels)).sort((x, y) => x.category.localeCompare(y.category) || x.name.localeCompare(y.name))

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
          <span>Your name <span className="font-normal text-graphite">(optional, stays in this browser)</span></span>
          <input value={a.name} onChange={e => a.setName(e.target.value)} placeholder="e.g. Siti" autoComplete="off" className={`${inputCls} min-h-11`} />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
          <span>Current role<Req /></span>
          <select value={prefs.current_job ?? ''} onChange={e => a.chooseJob(e.target.value)} required aria-required="true" className={`${inputCls} min-h-11`}>
            <option value="">Select…</option>
            {q?.current_roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
          <span className="inline-flex flex-wrap items-center gap-2">Industry <ShapesRanking what="Roles common in your industry get a small bonus for direction fit." /></span>
          <select value={prefs.industry ?? ''} onChange={e => a.setPref('industry', e.target.value || null)} className={`${inputCls} min-h-11`}>
            <option value="">Select…</option>
            {q?.industries.map(o => <option key={o}>{o}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
          <span className="inline-flex flex-wrap items-center gap-2">Highest education <NoteOnly /></span>
          <select value={prefs.education ?? ''} onChange={e => a.setPref('education', e.target.value || null)} className={`${inputCls} min-h-11`}>
            <option value="">Select…</option>
            {q?.education.map(o => <option key={o.label}>{o.label}</option>)}
          </select>
        </label>
      </div>
      <fieldset>
        <legend className="text-sm font-medium text-ink mb-2">Years of experience<Req /></legend>
        <div className="flex flex-wrap gap-2">
          {YEAR_BANDS.map(b => <Chip key={b.label} on={a.yearsBand === b.label} onClick={() => a.setYearsBand(b.label)}>{b.label}</Chip>)}
        </div>
      </fieldset>
      <fieldset>
        <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Tools you use today <span className="font-normal text-graphite">— pick any</span> <ShapesRanking /></legend>
        <div className="flex flex-wrap gap-2">
          {q?.tools.map(t => <Chip key={t.label} on={(prefs.tools ?? []).includes(t.label)} onClick={() => a.toggleTool(t.label)}>{t.label}</Chip>)}
        </div>
      </fieldset>
      <fieldset>
        <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Which of these do you do most weeks? <span className="font-normal text-graphite">— pick any</span> <ShapesRanking /></legend>
        <div className="flex flex-wrap gap-2">
          {shownTasks.map(t => <Chip key={t.id} on={(prefs.tasks ?? []).includes(t.id)} onClick={() => a.toggleTask(t.id)}>{t.label}</Chip>)}
          {tasks.length > TASKS_SHOWN && (
            <button type="button" onClick={() => setAllTasks(v => !v)} className="min-h-11 px-2 text-sm text-action-ink hover:underline">
              {allTasks ? 'Show fewer' : `Show ${tasks.length - TASKS_SHOWN} more`}
            </button>
          )}
        </div>
      </fieldset>
      <fieldset className="space-y-2 min-w-0">
        <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-1">Your skills <ShapesRanking /></legend>
        <p className="text-sm text-graphite">
          {heldIds.length > 0
            ? "We've added skills typical for your role and the tasks and tools you picked. Remove any you don't use, add any we missed, and tap a skill to change its level."
            : 'Pick your role, tasks or tools above, or add skills here.'}
        </p>
        <ul className="flex flex-wrap gap-2" aria-label="Your skills">
          {heldIds.map(id => (
            <li key={id} className="inline-flex items-stretch rounded-full bg-action-tint text-action-ink text-sm">
              <button type="button" onClick={() => a.cycleLevel(id)} aria-label={`${skillName(id)}: ${levelLabel(levels[id])}. Change level`}
                className="min-h-11 rounded-l-full pl-4 pr-2 text-left hover:bg-action/10 transition-colors duration-200">
                <span className="font-medium">{skillName(id)}</span> <span className="text-xs">· {levelLabel(levels[id])}</span>
              </button>
              <button type="button" onClick={() => a.removeSkill(id)} aria-label={`Remove ${skillName(id)}`} className="min-h-11 rounded-r-full pl-1 pr-3 hover:bg-action/10 transition-colors duration-200">
                <X size={14} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <label htmlFor="add-skill" className="sr-only">Add a skill</label>
          <select id="add-skill" value={adding} onChange={e => setAdding(e.target.value)} className={`${inputCls} min-h-11 w-full sm:w-auto sm:max-w-md min-w-0`}>
            <option value="">Add a skill…</option>
            {addable.map(s => <option key={s.id} value={s.id}>{s.name} ({s.category})</option>)}
          </select>
          <button type="button" disabled={!adding} onClick={() => { a.addSkills([adding]); setAdding('') }} className={`${btn.outline} min-h-11`}>
            <Plus size={14} aria-hidden="true" /> Add
          </button>
        </div>
        <p className="text-xs text-graphite">Levels: {q?.levels.map(l => l.label).join(' · ')}. Skills you show in practice cases move up on their own.</p>
      </fieldset>
    </div>
  )
}

/** Step 2 — Where you're heading: direction (required) and timeframe. */
export function StepHeading() {
  const a = useAnswers()
  const { prefs } = a
  return (
    <div className="space-y-6">
      <fieldset>
        <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">
          Where do you want to go next?<Req />
          <ShapesRanking what="Direction decides which roles count as a good fit." />
        </legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {DIRECTIONS.map(d => {
            const on = prefs.direction === d.value
            return (
              <button key={d.value} type="button" aria-pressed={on} onClick={() => a.setPref('direction', d.value)}
                className={`text-left rounded-xl p-4 min-h-11 transition-colors duration-200 ${on ? 'bg-action-tint ring-2 ring-action' : 'bg-surface border border-hairline-strong hover:bg-linen'}`}>
                <span className={`block font-semibold ${on ? 'text-action-ink' : 'text-ink'}`}>{d.label}</span>
                <span className="block mt-1 text-sm text-graphite">{d.hint}</span>
              </button>
            )
          })}
        </div>
      </fieldset>
      <fieldset>
        <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">
          Timeframe <ShapesPathway what="Your timeframe sets how many hours you have to close a gap and how much the pathway can hold." />
        </legend>
        <div className="flex flex-wrap gap-2">
          {TIMEFRAMES.map(m => <Chip key={m} on={prefs.timeframe_months === m} onClick={() => a.setPref('timeframe_months', m)}>{m} months</Chip>)}
        </div>
        <p className="mt-2 text-xs text-graphite">It starts at {DEFAULT_TIMEFRAME} months; your matches and your plan both use it.</p>
      </fieldset>
    </div>
  )
}

/** Step 3 — How you learn: hours, AI comfort, format, language, funding, eligibility, notes. */
export function StepHowYouLearn() {
  const a = useAnswers()
  const { q, prefs } = a
  return (
    <div className="space-y-6">
      <div>
        <label htmlFor="weekly-hours" className="flex justify-between gap-3 text-sm font-medium text-ink">
          Time for learning each week <span className="tabular-nums text-action-ink">{a.weeklyHours} h</span>
        </label>
        <input id="weekly-hours" type="range" min={1} max={20} step={0.5} value={a.weeklyHours} onChange={e => a.setWeeklyHours(parseFloat(e.target.value))} className="mt-3 w-full min-h-11" />
      </div>
      <div>
        <label htmlFor="ai-comfort" className="flex flex-wrap justify-between gap-2 text-sm font-medium text-ink">
          <span className="inline-flex flex-wrap items-center gap-2">How comfortable are you using AI tools at work? <ShapesPathway what="At 3/10 or below, an intro-to-AI course goes first in your pathway." /></span>
          <span className="tabular-nums text-action-ink">{prefs.ai_comfort == null ? 'not set' : `${prefs.ai_comfort}/10`}</span>
        </label>
        {/* Until it is set the handle is hidden, so the label and the handle never disagree (§4.1). */}
        <input
          id="ai-comfort" type="range" min={0} max={10} step={1} value={prefs.ai_comfort ?? 0}
          onChange={e => a.setPref('ai_comfort', parseInt(e.target.value, 10))}
          onPointerUp={e => a.setPref('ai_comfort', parseInt(e.currentTarget.value, 10))}
          aria-valuetext={prefs.ai_comfort == null ? 'not set' : `${prefs.ai_comfort} out of 10`}
          className={`mt-3 w-full min-h-11 ${prefs.ai_comfort == null ? '[&::-webkit-slider-thumb]:opacity-0 [&::-moz-range-thumb]:opacity-0' : ''}`}
        />
        <p className="mt-1 text-xs text-graphite">
          {prefs.ai_comfort == null ? 'Tap the line to set it. ' : <button type="button" onClick={() => a.setPref('ai_comfort', null)} className="text-action-ink hover:underline mr-1">Clear</button>}
          At 3/10 or below, an intro-to-AI course goes first in your pathway.
        </p>
      </div>
      <fieldset>
        <legend className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink mb-2">Preferred format <ForPlan /></legend>
        <div className="flex flex-wrap gap-2">
          {FORMATS.map(f => <Chip key={f} on={(prefs.formats ?? []).includes(f)} onClick={() => a.setPref('formats', toggle(prefs.formats ?? [], f))}>{f}</Chip>)}
          <Chip on={prefs.wants_certificate === true} onClick={() => a.setPref('wants_certificate', prefs.wants_certificate ? null : true)}>Certificates where possible</Chip>
        </div>
      </fieldset>
      {q && (
        <>
          <ChoiceRow legend="Course language" aside={<ForPlan />} options={q.funding.language} value={prefs.language} onChange={v => a.setPref('language', v as Preferences['language'])} />
          <ChoiceRow
            legend="Right now I am…" aside={<ForPlan />} options={q.funding.employment} value={prefs.employment}
            // The HRD Corp question only applies to employees, so it is cleared otherwise.
            onChange={v => a.setPrefs(p => ({ ...p, employment: v as Preferences['employment'], employer_hrd: v === 'employed' ? p.employer_hrd : null }))}
          />
          {prefs.employment === 'employed' && (
            <ChoiceRow legend="Is your employer registered with HRD Corp?" aside={<ForPlan />} options={q.funding.employer_hrd} value={prefs.employer_hrd} onChange={v => a.setPref('employer_hrd', v as Preferences['employer_hrd'])} />
          )}
          <ChoiceRow legend="Budget for courses" aside={<ForPlan />} options={q.funding.budget} value={prefs.budget} onChange={v => a.setPref('budget', v as Preferences['budget'])} />
          <details className="rounded-md border border-hairline px-4 py-3">
            <summary className="cursor-pointer min-h-11 flex items-center text-sm font-medium text-ink">Eligibility <span className="ml-1 font-normal text-graphite">(optional)</span></summary>
            <div className="mt-3 space-y-4">
              <p className="text-xs text-graphite">Some free programmes are only for certain ages or for Malaysians. These answers are only used to check that; "Prefer not to say" never hides a course, it adds a note.</p>
              <ChoiceRow legend="Age" aside={<EligibilityOnly />} options={q.funding.age_band} value={prefs.age_band} onChange={v => a.setPref('age_band', v as Preferences['age_band'])} />
              <ChoiceRow legend="Malaysian citizen?" aside={<EligibilityOnly />} options={q.funding.malaysian} value={prefs.malaysian} onChange={v => a.setPref('malaysian', v as Preferences['malaysian'])} />
            </div>
          </details>
        </>
      )}
      <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
        <span>Anything else we should know? <span className="font-normal text-graphite">(optional)</span></span>
        <textarea rows={3} maxLength={NOTES_MAX} value={prefs.notes ?? ''} onChange={e => a.setPref('notes', e.target.value)}
          placeholder="e.g. I can only study on weekends, I'd like a certificate at the end" className={`${inputCls} resize-y`} />
        <span className="text-xs font-normal text-graphite">Demo data only. Saved with your profile; never sent to the AI companion.</span>
      </label>
    </div>
  )
}
