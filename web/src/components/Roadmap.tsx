import { useState } from 'react'
import { useT } from '../i18n'
import type { PathwayStep } from '../types'
import { ReportProblem } from './Feedback'
import { SdgTag, levelText } from './journey'

const MINUTES_PER_HOUR = 60

type State = 'done' | 'current' | 'locked'

// The plan as one route: stations in the planner's order (prerequisites first, essentials
// first). A station is done (the person's own record), current (the first one not done) or
// locked (it waits for the station before it). Opening a station shows its details in place.
// Completion is learning recorded by the person; it never changes a skill level or a fit.
export function Roadmap({ steps, done, onToggle, checked, paused }: { steps: PathwayStep[]; done: string[]; onToggle: (courseId: string) => void; checked: string; paused: boolean }) {
  const { t } = useT()
  const firstOpen = steps.findIndex((s) => !done.includes(s.course.id))
  // Until the person opens a station themselves, the current one is open (progress may load late).
  const [picked, setOpen] = useState<string | null | undefined>(undefined)
  const open = picked === undefined ? (firstOpen >= 0 ? steps[firstOpen].course.id : null) : picked
  if (steps.length === 0) return null
  const state = (i: number): State => (done.includes(steps[i].course.id) ? 'done' : i === firstOpen ? 'current' : 'locked')

  return (
    <ol className="m-0 flex list-none flex-col p-0" aria-label="Your plan, in order">
      {steps.map((step, i) => {
        const s = state(i)
        const isOpen = open === step.course.id
        const last = i === steps.length - 1
        const before = i > 0 ? steps[i - 1] : null
        return (
          <li key={step.course.id} className="grid grid-cols-[64px_28px_minmax(0,1fr)] gap-x-3 md:grid-cols-[84px_28px_minmax(0,1fr)]">
            <span className="pt-3.5 text-right font-mono text-[11px] uppercase tracking-wider text-ash">
              Week {step.week_start}{step.week_end > step.week_start ? `–${step.week_end}` : ''}
            </span>
            <span className="relative flex justify-center" aria-hidden="true">
              {!last && <span className={`absolute bottom-0 top-0 w-[2px] ${s === 'done' ? 'bg-violet' : 'bg-line'}`} />}
              <span
                className={`relative mt-2.5 grid h-7 w-7 place-items-center rounded-full border-2 text-[12px] font-semibold ${
                  s === 'done' ? 'border-violet bg-violet text-white' : s === 'current' ? 'border-violet bg-paper text-violet' : 'border-line bg-fog text-ash'
                }`}
              >
                {s === 'done' ? '✓' : s === 'locked' ? (
                  <svg width="11" height="12" viewBox="0 0 11 12"><rect x="1" y="5" width="9" height="6.5" rx="1" fill="currentColor" /><path d="M3 5V3.5a2.5 2.5 0 0 1 5 0V5" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
                ) : step.order}
              </span>
            </span>
            <div className={`mb-3 min-w-0 border ${isOpen ? 'border-line bg-paper' : 'border-transparent'} ${s === 'current' && !isOpen ? 'bg-violet-soft' : ''}`}>
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : step.course.id)}
                className="flex w-full cursor-pointer flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-0 bg-transparent px-3 py-3 text-left"
              >
                <span className={`min-w-0 text-[15px] leading-snug ${s === 'locked' ? 'text-graphite' : 'font-semibold'}`}>
                  {step.course.title}
                  <span className="sr-only"> · {s === 'done' ? 'done' : s === 'current' ? 'next up' : 'locked'}</span>
                </span>
                <span className="font-mono text-[11px] text-graphite">
                  {step.course.minutes >= MINUTES_PER_HOUR ? `${step.hours} h` : `${step.course.minutes} min`} · free
                  {s === 'current' && <span className="ml-2 text-violet">NEXT UP</span>}
                </span>
              </button>
              {isOpen && (
                <div className="flex flex-col gap-3 border-t border-line px-3 pb-3.5 pt-3 text-[13px]">
                  <span className="text-graphite">{step.course.provider} · {step.course.level}</span>
                  {step.gains.length > 0 ? (
                    <div className="flex flex-col gap-1">
                      <span className="cap">Builds · projected, an assumption</span>
                      {step.gains.map((g) => (
                        <span key={g.skill}>{g.skill_name}: {levelText(g.before)} → {levelText(g.after)}</span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-graphite">Needed first for {step.prerequisite_for.length ? 'the next course' : 'later steps'}.</span>
                  )}
                  {step.sdgs.map((g) => (
                    <div key={g.target} className="flex items-start gap-2.5">
                      <SdgTag target={g.target} />
                      <span>{g.how}</span>
                    </div>
                  ))}
                  <div className="flex flex-wrap items-center gap-2">
                    <a className="btn" href={step.course.url} target="_blank" rel="noopener noreferrer">{t('Open course ↗')}</a>
                    {s === 'locked' ? (
                      <span className="text-[13px] text-graphite">Finish &ldquo;{before?.course.title}&rdquo; first to unlock this step.</span>
                    ) : (
                      <button type="button" className={`btn ${s === 'current' ? 'btn-v' : ''}`} aria-pressed={s === 'done'} disabled={paused} onClick={() => {
                        onToggle(step.course.id)
                        if (s === 'current') setOpen(steps[i + 1]?.course.id ?? null)
                      }}>
                        {s === 'done' ? 'Done ✓ · undo' : t('Mark as done')}
                      </button>
                    )}
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-ash">Link checked {checked} · {step.course.provider}</span>
                  <ReportProblem kinds={['course_unavailable', 'impractical_schedule', 'wrong_skill_mapping']} targetType="course" targetId={step.course.id} page="pathway" />
                </div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
