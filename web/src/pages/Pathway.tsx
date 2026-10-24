import { useEffect, useState } from 'react'
import { useT } from '../i18n'
import { Link } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { PlanCompare } from '../components/PlanCompare'
import { RouteCompare } from '../components/RouteCompare'
import { TrackMap } from '../components/TrackMap'
import { ScenarioSwitch, SdgTag, sdgColour, JourneyRoute, NextStep, PROGRESS_EVENT } from '../components/journey'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { PathwayResponse, ProgressResponse, Scenario, TracksResponse } from '../types'
import { NeedProfile } from './Roles'

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
  return <ProfilePathway key={`${profileId}-${scenario}`} profileId={profileId} scenario={scenario} />
}

function ProfilePathway({ profileId, scenario }: { profileId: string; scenario: Scenario }) {
  const { t } = useT()
  const path = useApi<PathwayResponse>(`/api/profiles/${profileId}/pathway?scenario=${scenario}`)
  const tracks = useApi<TracksResponse>(`/api/profiles/${profileId}/tracks?scenario=${scenario}`)
  // Self-reported completion, saved per profile on the server; it never changes skills or fit.
  const progress = useApi<ProgressResponse>(`/api/profiles/${profileId}/progress?scenario=${scenario}`)
  const [state, setState] = useState<ProgressResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const current = state ?? progress.data
  const done = current?.done ?? []

  async function save(next: { done: string[]; paused: boolean }) {
    setSaving(true)
    setSaveError(null)
    try {
      setState(await sendJSON<ProgressResponse>(`/api/profiles/${profileId}/progress?scenario=${scenario}`, { method: 'PUT', body: next }))
      window.dispatchEvent(new Event(PROGRESS_EVENT))
      return true
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : String(reason))
      return false
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    const legacy = readDone(`qart.done.${profileId}`)
    if (progress.data && progress.data.done.length === 0 && legacy.length > 0) {
      void save({ done: legacy, paused: progress.data.paused }).then((saved) => { if (saved) window.localStorage.removeItem(`qart.done.${profileId}`) })
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
    <main className="page">
      <JourneyRoute />
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

          <section aria-label="Your roadmap" className="panel min-w-0 gap-5">
            <div className="flex flex-col gap-1">
              <h2 className="h2">Your roadmap</h2>
              <p className="m-0 max-w-[720px] text-[13px] text-graphite">
                Three tracks: AI basics first, then the skills this role needs without AI and with AI. Each step opens its courses, YouTube videos and articles; a step unlocks when the one before it in its track is done.
              </p>
            </div>
            {(data.essentials_unmet.length > 0 || data.uncovered.length > 0) && (
              <div className="flex flex-col gap-1 border-l-4 border-weak bg-weak-bg px-4 py-3 text-[13px]">
                {data.essentials_unmet.length > 0 && <span className="font-semibold text-weak">Essential skills still below the level after this plan: {data.essentials_unmet.join(', ')}.</span>}
                {data.uncovered.length > 0 && <span className="text-graphite">No verified free course yet for: {data.uncovered.join(', ')} — the stop still offers videos and articles.</span>}
              </div>
            )}
            {(tracks.loading || (progress.loading && !current)) && <Loading what="your roadmap" />}
            {tracks.error && <Problem what="your roadmap" message={tracks.error} onRetry={tracks.reload} />}
            {saveError && <p role="alert" className="m-0 text-weak">Progress was not saved: {saveError}. Try the action again.</p>}
            {/* Drawn only once saved progress is known, so steps never flash the wrong state. */}
            {tracks.data && (current || progress.error) && <TrackMap tracks={tracks.data.tracks} done={done} onToggle={toggle} paused={saving || progress.loading || (current?.paused ?? false)} checked={tracks.data.resources_checked} />}
          </section>

          {tracks.data && <RouteCompare data={tracks.data.comparison} scenario={scenario} />}

          {current?.plan && (
            <section aria-label="Your progress" className="panel gap-4">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-[40px] leading-none tracking-[-0.05em]">{current.plan.steps_done}<span className="text-graphite">/{current.plan.steps}</span></span>
                  <span className="text-[13px] text-graphite">
                    steps done · {current.plan.hours_done} of {current.plan.hours} h
                    {current.paused && <span className="ml-2 font-semibold text-weak">Paused</span>}
                  </span>
                </div>
                <button type="button" className="btn" disabled={saving} onClick={() => save({ done, paused: !current.paused })}>{current.paused ? t('Resume') : t('Pause for now')}</button>
              </div>
              <div
                role="progressbar"
                aria-label="Plan completed"
                aria-valuemin={0}
                aria-valuemax={data.steps.length}
                aria-valuenow={finished}
                className="grid h-3 gap-[3px]"
                style={{ gridTemplateColumns: data.steps.map((s) => `${Math.max(s.hours, 0.5)}fr`).join(' ') }}
              >
                {data.steps.map((s) => (
                  <span key={s.course.id} title={s.course.title} className={`transition-colors duration-500 ${done.includes(s.course.id) ? 'bg-violet' : 'bg-line'}`} />
                ))}
              </div>
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-[12px] text-graphite">
                <span>Segment width = course hours · your own record</span>
                <span>Requirement coverage {Math.round(current.plan.coverage)}/100 (changes only when you update your skill levels)</span>
                {current.plan.open_questions > 0 && <Link to="/roles">{current.plan.open_questions} skill{current.plan.open_questions === 1 ? '' : 's'} still to rate</Link>}
              </div>
              {!current.paused && current.plan.this_week.length > 0 && (
                <p className="m-0 border-l-2 border-violet pl-3 text-[13px]">
                  <span className="font-semibold">This week ({current.plan.weekly_hours} h):</span>{' '}
                  {current.plan.this_week.map((w) => `${w.title} (${w.hours} h)`).join(' · ')}
                </p>
              )}
            </section>
          )}

          <section aria-label="SDG contribution" className="sdg-band">
            <div className="mx-auto flex max-w-[760px] flex-col items-center gap-2 text-center">
              <span className="eyebrow">Sustainable Development Goals</span>
              <h2 className="m-0 text-[26px] font-semibold leading-tight tracking-tight">How this plan contributes to {Object.keys(data.sdg_summary).length} SDG targets</h2>
              <p className="m-0 text-[14px] text-graphite">
                Fit for {data.role_title}: <span className="font-mono font-semibold text-void">{Math.round(data.fit_before)} → {Math.round(data.fit_after)}</span>{' '}
                <span className="text-[12px] text-estimate">estimate after the plan</span>
              </p>
            </div>
            <div className="sdg-grid">
              {Object.entries(data.sdg_summary).map(([target, hows]) => (
                <article key={target} className="sdg-card" style={{ borderLeftColor: sdgColour(target) }}>
                  <span className="flex flex-wrap items-center gap-2"><SdgTag target={target} /><span className="text-[15px] font-semibold">{data.sdg_targets[target]?.title}</span></span>
                  {hows.map((h) => <p key={h} className="m-0 text-[14px] leading-relaxed">{h}</p>)}
                  <p className="m-0 text-[12px] italic text-graphite">&ldquo;{data.sdg_targets[target]?.text}&rdquo;</p>
                </article>
              ))}
            </div>
            <p className="m-0 text-center font-mono text-[11px] text-graphite">{data.sdg_source} · these are the mechanisms by which the plan contributes, not a measured impact</p>
          </section>

          <PlanCompare profileId={profileId} scenario={scenario} />
        </>
      )}
      <NextStep to="/future" label="See today versus future you" hint="Next: what this plan changes, in both scenarios" />
    </main>
  )
}
