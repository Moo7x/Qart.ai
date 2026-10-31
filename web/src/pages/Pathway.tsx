import { useEffect, useState } from 'react'
import { useT } from '../i18n'
import { Link } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { RouteCompare } from '../components/RouteCompare'
import { SdgPlan } from '../components/SdgPlan'
import { Badges } from '../components/Badges'
import { TrackMap } from '../components/TrackMap'
import { ScenarioSwitch, NextStep, PROGRESS_EVENT } from '../components/journey'
import { PageHead, Serif, VividTile } from '../components/atoms'
import { LevelBars } from '../components/MiniCharts'
import type { RadarOut } from '../apiTypes'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { PathwayResponse, ProfileData, ProgressResponse, Scenario, TracksResponse } from '../types'
import type { Badge, SdgMatrix } from '../typesScoring'
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
  const sdg = useApi<SdgMatrix>(`/api/profiles/${profileId}/sdg?scenario=${scenario}`)
  const badges = useApi<Badge[]>(`/api/profiles/${profileId}/badges?scenario=${scenario}`)
  const profile = useApi<{ profile: ProfileData }>(`/api/profiles/${profileId}`)
  const radar = useApi<RadarOut>(`/api/profiles/${profileId}/radar?scenario=${scenario}`)
  // Self-reported completion, saved per profile on the server; it never changes skills or fit.
  const progress = useApi<ProgressResponse>(`/api/profiles/${profileId}/progress?scenario=${scenario}`)
  const [state, setState] = useState<ProgressResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const current = state ?? progress.data
  const done = current?.done ?? []

  async function save(next: { done: string[]; paused: boolean; skipped?: string[] }) {
    setSaving(true)
    setSaveError(null)
    try {
      setState(await sendJSON<ProgressResponse>(`/api/profiles/${profileId}/progress?scenario=${scenario}`, { method: 'PUT', body: next }))
      window.dispatchEvent(new Event(PROGRESS_EVENT))
      // Lock and skip states are computed by the server, so the plan is read again.
      path.reload()
      tracks.reload()
      badges.reload()
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

  function skip(stepId: string) {
    const skipped = current?.skipped ?? []
    void save({ done, paused: current?.paused ?? false, skipped: [...skipped, stepId] })
  }

  function toggle(courseId: string) {
    const next = done.includes(courseId) ? done.filter((d) => d !== courseId) : [...done, courseId]
    void save({ done: next, paused: current?.paused ?? false })
  }

  const noDestination = path.error?.includes('choose a destination')
  const data = path.data
  const finished = data ? data.steps.filter((s) => done.includes(s.course.id)).length : 0

  return (
    <main className="page">
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
          <PageHead
            badge="My plan · destination you chose"
            title={<>Your <Serif>plan</Serif> to {data.role_title}</>}
            sub={`${data.total_hours} h${tracks.data?.comparison.with_ai.ai_basics_hours ? ` + ${tracks.data.comparison.with_ai.ai_basics_hours} h AI basics` : ''} · RM 0 · ${data.weekly_hours} h a week · about ${data.weeks} week${data.weeks === 1 ? '' : 's'} · ${finished} of ${data.steps.length} steps done`}
            right={
              <div className="flex flex-col items-start gap-2 md:items-end">
                <ScenarioSwitch />
                <span className="flex gap-3 text-[13px]"><Link to="/time">Change time and budget</Link><Link to="/roles">Change destination</Link></span>
              </div>
            }
          />

          <div className="q-tray q-g2">
            <article aria-label="Plan totals" className="q-card">
              <span className="q-kicker">Study and practice</span>
              <PlanTotals data={data} />
            </article>
            <VividTile theme="lime" pill="your badges" label="Your badges">
              {badges.error && <Problem what="your badges" message={badges.error} onRetry={badges.reload} />}
              {badges.data && <Badges badges={badges.data} />}
              <p className="m-0 mt-auto text-[13px] leading-normal text-[#33402a]">Badges come only from what you do: courses marked done, levels raised. Never from a model or a guess.</p>
            </VividTile>
            {radar.data && (
              <article aria-label="Your levels against the role" className="q-card q-span2">
                <LevelBars
                  title={`Your levels against what ${data.role_title} needs`}
                  rows={radar.data.axes.map((a) => ({ skill: a.skill, name: a.name, you: a.claimed, needs: a.required, essential: a.essential }))}
                />
              </article>
            )}
          </div>

          <section aria-label="Your roadmap" className="panel min-w-0 gap-5">
            <div className="flex flex-col gap-1">
              <h2 className="h2">Your roadmap</h2>
              <p className="m-0 max-w-[720px] text-[13px] text-graphite">
                Three tracks: AI basics first, then the skills this role needs without AI and with AI. Each step opens its courses, YouTube videos and articles; a step unlocks when the one before it in its track is done.
              </p>
            </div>
            {data.adjustments && data.adjustments.length > 0 && (
              <div className="flex flex-col gap-1 border-l-4 border-observed bg-observed-bg px-4 py-3 text-[13px]">
                <span className="font-semibold text-observed">Adjusted for you</span>
                <ul className="m-0 pl-5">{data.adjustments.map((a) => <li key={`${a.rule}-${a.text}`}>{a.text}</li>)}</ul>
              </div>
            )}
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
            {tracks.data && (current || progress.error) && <TrackMap tracks={tracks.data.tracks} done={done} onToggle={toggle} onSkip={skip} paused={saving || progress.loading || (current?.paused ?? false)} checked={tracks.data.resources_checked} />}
          </section>

          {tracks.data && <RouteCompare data={tracks.data.comparison} scenario={scenario} />}

          {sdg.loading && <Loading what="the SDG contribution" />}
          {sdg.error && <Problem what="the SDG contribution" message={sdg.error} onRetry={sdg.reload} />}
          {sdg.data && <SdgPlan matrix={sdg.data} path={data} goals={profile.data?.profile.sdg_priorities ?? []} />}

          <section aria-label="Employer-funded training" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-paper px-5 py-4">
            <span className="flex max-w-[760px] flex-col gap-1 text-[13px]">
              <span className="text-[15px] font-semibold">Need more than free courses? Ask about HRD Corp</span>
              <span className="text-graphite">If your employer pays the HRD Corp levy, it can claim the cost of approved training. HRD Corp&rsquo;s e-LATiH platform also offers free courses. Qart.ai does not mark any programme as claimable until HRD Corp&rsquo;s own listing confirms it.</span>
            </span>
            <a className="btn min-h-[40px]" href="https://hrdcorp.gov.my" target="_blank" rel="noopener noreferrer">HRD Corp ↗</a>
          </section>

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

        </>
      )}
      <NextStep to="/future" label="See today versus future you" hint="Next: what this plan changes, in both scenarios" />
    </main>
  )
}

const BASIS_TEXT: Record<string, string> = {
  reading_estimate: 'reading estimates',
  guided_hours: 'guided hours',
  stated: 'stated lengths',
}

// Study and practice kept apart (B4): hours of study, weeks of practice as a range, and the fit
// after each, every one an estimate. Study reaches level 2 at most.
function PlanTotals({ data }: { data: PathwayResponse }) {
  if (data.study_hours === undefined || !data.fit_after_study || !data.fit_after_practice) return null
  const bases = [...new Set(data.steps.map((s) => s.time?.basis).filter((b): b is NonNullable<typeof b> => !!b && b in BASIS_TEXT))]
  const range = (r: { low: number; high: number }) => `${Math.round(r.low)}–${Math.round(r.high)}`
  const weeks = data.practice_weeks
  return (
    <div className="flex w-full flex-col gap-1.5 text-[13px]">
      <span className="flex flex-wrap items-center gap-2">
        <span className="tag bg-estimate-bg text-estimate">Estimate</span>
        Study {data.study_hours} h{bases.length ? ` (${bases.map((b) => BASIS_TEXT[b]).join(', ')})` : ''}
        {weeks && weeks.high > 0 ? ` · practice at work ${weeks.low}–${weeks.high} weeks` : ''}
      </span>
      <span>
        Fit after study <b>{range(data.fit_after_study)}</b>
        {weeks && weeks.high > 0 ? <> · after study and practice <b>{range(data.fit_after_practice)}</b></> : null}
        <span className="text-graphite"> (now {Math.round(data.fit_before)}; planned levels count as self-rated)</span>
      </span>
      {data.partly_covered.length > 0 && (
        <span className="text-graphite">Study stops below level 2 for {data.partly_covered.join(', ')}: not enough verified hands-on material yet. Level 2 needs 20 h including hands-on work.</span>
      )}
    </div>
  )
}

