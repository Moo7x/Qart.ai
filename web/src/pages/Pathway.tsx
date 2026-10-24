import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { ReportProblem } from '../components/Feedback'
import { PlanCompare } from '../components/PlanCompare'
import { Roadmap } from '../components/Roadmap'
import { ScenarioSwitch, SdgTag } from '../components/journey'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { PathwayResponse, ProgressResponse, Scenario } from '../types'
import { NeedProfile } from './Roles'

const MINUTES_PER_HOUR = 60
// Older builds kept completion in this browser; it is moved to the server once.
function readDone(key: string): string[] {
  try {
    const saved: unknown = JSON.parse(window.localStorage.getItem(key) ?? '[]')
    return Array.isArray(saved) ? saved.filter((id): id is string => typeof id === 'string') : []
  } catch {
    return []
  }
}

export function Pathway() {
  const { profileId, scenario } = useJourney()
  if (!profileId) return <NeedProfile />
  return <ProfilePathway key={profileId} profileId={profileId} scenario={scenario} />
}

function ProfilePathway({ profileId, scenario }: { profileId: string; scenario: Scenario }) {
  const path = useApi<PathwayResponse>(`/api/profiles/${profileId}/pathway?scenario=${scenario}`)
  // Self-reported completion, saved per profile on the server; it never changes skills or fit.
  const progress = useApi<ProgressResponse>(`/api/profiles/${profileId}/progress?scenario=${scenario}`)
  const [state, setState] = useState<ProgressResponse | null>(null)
  const current = state ?? progress.data
  const done = current?.done ?? []

  async function save(next: { done: string[]; paused: boolean }) {
    setState(await sendJSON<ProgressResponse>(`/api/profiles/${profileId}/progress?scenario=${scenario}`, { method: 'PUT', body: next }))
  }

  useEffect(() => {
    const legacy = readDone(`qart.done.${profileId}`)
    if (progress.data && progress.data.done.length === 0 && legacy.length > 0) {
      void save({ done: legacy, paused: progress.data.paused }).then(() => window.localStorage.removeItem(`qart.done.${profileId}`))
    }
  }, [progress.data]) // eslint-disable-line react-hooks/exhaustive-deps

  function toggle(courseId: string) {
    const next = done.includes(courseId) ? done.filter((d) => d !== courseId) : [...done, courseId]
    void save({ done: next, paused: current?.paused ?? false })
  }

  const noDestination = path.error?.includes('choose a destination')
  const data = path.data
  const finished = data ? data.steps.filter((s) => done.includes(s.course.id)).length : 0

  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      {noDestination && (
        <div className="flex flex-col gap-3">
          <span className="eyebrow">My plan · pathway</span>
          <h1 className="h1">Choose a destination role first</h1>
          <Link className="btn btn-v self-start" to="/roles">See roles that fit me</Link>
        </div>
      )}
      {path.loading && <Loading what="your pathway" />}
      {path.error && !noDestination && <Problem what="your pathway" message={path.error} onRetry={path.reload} />}

      {data && (
        <>
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="eyebrow">Pathway · destination you chose</span>
              <h1 className="h1">{data.role_title}</h1>
              <p className="m-0 font-mono text-[13px] text-graphite">
                {data.total_hours} h · RM 0 · {data.weekly_hours} h a week · about {data.weeks} week{data.weeks === 1 ? '' : 's'} · {finished} of {data.steps.length} steps done
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <ScenarioSwitch />
              <Link to="/roles" className="text-[13px]">Change destination</Link>
            </div>
          </header>

          {current?.plan && (
            <section className="card-light flex flex-col gap-3 px-6 py-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="h2">{current.paused ? 'Paused: your plan waits for you' : 'Your progress'}</h2>
                <button type="button" className="btn" onClick={() => save({ done, paused: !current.paused })}>{current.paused ? 'Resume' : 'Pause for now'}</button>
              </div>
              <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))]">
                <div className="rounded-lg border border-mist px-3 py-2">
                  <span className="cap">Plan completed</span>
                  <span className="block text-lg font-semibold">{current.plan.steps_done} of {current.plan.steps} steps</span>
                  <span className="text-xs text-graphite">{current.plan.hours_done} of {current.plan.hours} h · your own record</span>
                </div>
                <div className="rounded-lg border border-mist px-3 py-2">
                  <span className="cap">Requirement coverage</span>
                  <span className="block text-lg font-semibold">{Math.round(current.plan.coverage)} / 100</span>
                  <span className="text-xs text-graphite">changes only when you update your skill levels</span>
                </div>
                <div className="rounded-lg border border-mist px-3 py-2">
                  <span className="cap">Still to tell us</span>
                  <span className="block text-lg font-semibold">{current.plan.open_questions} skill{current.plan.open_questions === 1 ? '' : 's'}</span>
                  <Link to="/roles" className="text-xs">answer on My options</Link>
                </div>
              </div>
              {!current.paused && current.plan.this_week.length > 0 && (
                <p className="m-0 text-[13px]">
                  <span className="font-semibold">This week ({current.plan.weekly_hours} h):</span>{' '}
                  {current.plan.this_week.map((w) => `${w.title} (${w.hours} h)`).join(' · ')}
                </p>
              )}
              <p className="m-0 text-xs text-graphite">Finishing a course is recorded as learning, not as a skill level. Pausing loses nothing and never lowers anything.</p>
            </section>
          )}

          <Roadmap steps={data.steps} done={done} />

          <PlanCompare profileId={profileId} scenario={scenario} />

          <div className="flex flex-wrap items-start gap-5">
            <section aria-label="Steps" className="card-light min-w-0 flex-[3_1_520px] overflow-hidden">
              {data.steps.length === 0 && <p className="m-0 px-5 py-5 text-sm">You already meet every requirement this pathway can teach. See the gaps below, if any.</p>}
              {data.steps.map((step) => {
                const isDone = done.includes(step.course.id)
                return (
                  <article key={step.course.id} className="grid grid-cols-[96px_minmax(0,1fr)] border-b border-mist">
                    <div className="flex flex-col items-start gap-2 py-[18px] pl-[18px]">
                      <span className="font-mono text-xs text-ash">
                        WEEK {step.week_start}{step.week_end > step.week_start ? `–${step.week_end}` : ''}
                      </span>
                      <span className={`flex h-[26px] w-[26px] items-center justify-center rounded-full text-xs font-semibold ${isDone ? 'bg-[#12a372] text-white' : 'bg-white text-violet shadow-[inset_0_0_0_1.5px_#6c47ff]'}`}>
                        {isDone ? '✓' : step.order}
                      </span>
                    </div>
                    <div className="flex min-w-0 flex-col gap-2.5 py-[18px] pl-2 pr-5">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h3 className="m-0 text-base font-semibold tracking-tight">{step.course.title}</h3>
                        <span className="font-mono text-xs text-graphite">
                          {step.course.minutes >= MINUTES_PER_HOUR ? `${step.hours} h` : `${step.course.minutes} min`} · free · {step.course.level}
                        </span>
                      </div>
                      <span className="text-[13px] text-graphite">{step.course.provider}</span>
                      {step.gains.length > 0 ? (
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
                          <span className="cap">Projected levels · assumption</span>
                          {step.gains.map((g) => (
                            <span key={g.skill}>{g.skill_name} {g.before} → {g.after}</span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[13px] text-graphite">Needed first for: {step.prerequisite_for.length ? 'the next course' : 'later steps'}</span>
                      )}
                      {step.sdgs.map((s) => (
                        <div key={s.target} className="flex items-start gap-2.5 rounded-md bg-fog px-3 py-2 text-[13px]">
                          <SdgTag target={s.target} />
                          <span>{s.how}</span>
                        </div>
                      ))}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-mono text-[11px] text-ash">CHECKED {data.courses_checked} · {step.course.provider.toUpperCase()}</span>
                        <span className="flex gap-2">
                          <a className="btn" href={step.course.url} target="_blank" rel="noopener noreferrer">Open course ↗</a>
                          <button type="button" className="btn" aria-pressed={isDone} onClick={() => toggle(step.course.id)}>{isDone ? 'Done ✓' : 'Mark as done'}</button>
                        </span>
                      </div>
                      <ReportProblem kinds={['course_unavailable', 'impractical_schedule', 'wrong_skill_mapping']} targetType="course" targetId={step.course.id} page="pathway" />
                    </div>
                  </article>
                )
              })}
              <div className="flex flex-col gap-1.5 px-[18px] py-3.5 text-xs text-graphite">
                <span>Ordered by prerequisites, essentials first. A short course raises a skill by at most one level; covering material is not the same as proven skill.</span>
                {data.uncovered.length > 0 && <span>No verified free course yet for: {data.uncovered.join(', ')}.</span>}
                {data.partly_covered.length > 0 && <span>Only partly covered by free courses: {data.partly_covered.join(', ')}.</span>}
                {data.essentials_unmet.length > 0 && <span className="text-weak">Essential skills still below the level after this path: {data.essentials_unmet.join(', ')}.</span>}
              </div>
            </section>

            <aside aria-label="SDG contribution" className="card-dark flex min-w-0 flex-[2_1_320px] flex-col gap-4 p-[22px]">
              <span className="font-mono text-[11px] tracking-widest text-cyan">HOW THIS PATH CONTRIBUTES</span>
              <h2 className="m-0 text-xl font-semibold tracking-tight">{Object.keys(data.sdg_summary).length} SDG targets, with the reason for each</h2>
              {Object.entries(data.sdg_summary).map(([target, hows]) => (
                <div key={target} className="grid grid-cols-[64px_minmax(0,1fr)] gap-3 border-t border-surface pt-3">
                  <SdgTag target={target} />
                  <div className="text-[13px]">
                    <div className="font-semibold">{data.sdg_targets[target]?.title}</div>
                    {hows.map((h) => (
                      <div key={h} className="text-[#c4c5cf]">{h}</div>
                    ))}
                    <div className="mt-1 text-[11px] text-slate-mid">“{data.sdg_targets[target]?.text}”</div>
                  </div>
                </div>
              ))}
              <span className="font-mono text-[11px] text-slate-mid">{data.sdg_source}</span>
              <div className="flex items-center justify-between border-t border-surface pt-3 font-mono text-xs">
                <span className="text-stone">Fit now → after the path (estimate)</span>
                <span>{Math.round(data.fit_before)} → {Math.round(data.fit_after)}</span>
              </div>
              <Link className="btn btn-v" to="/future">See Today → Future you</Link>
            </aside>
          </div>
        </>
      )}
    </main>
  )
}
