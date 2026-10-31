import { useState, type ReactNode } from 'react'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useApi } from '../api'
import { OVERVIEW_SCENARIO } from '../components/atoms'
import { JobHub } from '../components/JobHub'
import { destinationOf, FitCard, FreshnessLine, RaiseCard } from '../components/OverviewGlance'
import { OverviewTrends } from '../components/OverviewTrends'
import { SkillRadar } from '../components/SkillRadar'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { MatchesResponse, PackInfo, ProfileData, ProgressResponse, RadarResponse } from '../types'

// Overview: where you are (your job and the evidence about it), your skills against the role you
// are heading for, and that role's fit; then the trends in the field. Always the moderate scenario
// (OVERVIEW_SCENARIO). Matching, the plan and the market data have their own pages; this page only
// summarises them, and its one main action is the next step: My options.

function Step({ n, children }: { n: number; children: ReactNode }) {
  return <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-violet">{n} · {children}</span>
}

function Stat({ value, of, label }: { value: number | string; of?: number; label: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[clamp(26px,3vw,34px)] leading-none tracking-[-0.02em]">{value}{of !== undefined && <span className="text-[0.55em] text-muted">/{of}</span>}</span>
      <span className="text-[12px] text-muted">{label}</span>
    </div>
  )
}

function OverviewBody({ onChanged }: { onChanged: () => void }) {
  const { profileId, setProfileId, setScenario } = useJourney()
  const q = `scenario=${OVERVIEW_SCENARIO}`
  const radar = useApi<RadarResponse>(profileId ? `/api/profiles/${profileId}/radar?${q}` : null)
  const matches = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?${q}` : null)
  const progress = useApi<ProgressResponse>(profileId ? `/api/profiles/${profileId}/progress?${q}` : null)
  const profile = useApi<{ profile: ProfileData }>(profileId ? `/api/profiles/${profileId}` : null)
  const pack = useApi<PackInfo>('/api/pack')
  if (!profileId) return null
  if (radar.loading || matches.loading) return <Loading what="your overview" />
  if (radar.error) return <Problem what="your skills" message={radar.error} onRetry={radar.reload} />
  if (matches.error) return <Problem what="your matches" message={matches.error} onRetry={matches.reload} />
  if (!radar.data || !matches.data) return null
  const axes = radar.data.axes
  const role = destinationOf(matches.data)
  const situation = profile.data?.profile.situation
  const job = situation && situation !== 'student' ? pack.data?.current_roles.find((r) => r.id === profile.data?.profile.current_role) : undefined
  const plan = progress.data?.plan
  return (
    <>
      <section aria-label="Summary" className="flex flex-wrap items-end justify-between gap-x-8 gap-y-5">
        <p className="m-0 flex flex-wrap items-center gap-2 text-[15px] text-muted">
          {job && <><span>{job.title}</span><ArrowRight size={18} className="text-violet" aria-hidden="true" /></>}
          <span className="font-semibold text-ink">{radar.data.title}</span>
          <span className="rounded-full bg-white px-3 py-1 text-[12px]">{radar.data.scenario_label} · estimates labelled</span>
          <Link to="/start" className="text-[13px] text-graphite underline underline-offset-4" onClick={() => { setProfileId(null); setScenario('moderate') }}>Start over</Link>
        </p>
        <div className="flex flex-wrap gap-[clamp(20px,3vw,36px)]">
          {role && <Stat value={Math.round(role.fit)} label="Fit / 100" />}
          <Stat value={axes.filter((a) => a.claimed !== null).length} of={axes.length} label="Skills rated" />
          {plan && <Stat value={plan.steps_done} of={plan.steps} label="Plan steps done" />}
        </div>
      </section>

      <div className={`grid items-stretch gap-4 ${job ? 'lg:grid-cols-[4fr_5fr_3fr]' : 'lg:grid-cols-[5fr_3fr]'}`}>
        {job && (
          <div className="flex min-w-0 flex-col gap-4">
            <Step n={1}>Where you are</Step>
            <JobHub soc={job.soc} title={job.title} impact={job.impact} page={job.page} routes={job.transitions.length} summary={job.summary} />
          </div>
        )}
        <div className="flex min-w-0 flex-col gap-4">
          <Step n={job ? 2 : 1}>Your skills</Step>
          <SkillRadar axes={axes} title={radar.data.title} onChanged={onChanged} />
        </div>
        <div className="flex min-w-0 flex-col gap-4">
          <Step n={job ? 3 : 2}>Where you&rsquo;re heading</Step>
          <FitCard matches={matches.data} />
          <RaiseCard matches={matches.data} />
        </div>
      </div>
    </>
  )
}

export function Overview() {
  // Bumped when a skill is rated, so every section reads the new claims.
  const [refresh, setRefresh] = useState(0)
  return (
    <main className="page max-w-[1400px] gap-6">
      <h1 className="sr-only">Overview</h1>
      <div className="q-tray flex flex-col gap-6 sm:p-6">
        <OverviewBody key={`body-${refresh}`} onChanged={() => setRefresh((r) => r + 1)} />
        <OverviewTrends />
        <FreshnessLine />
      </div>
    </main>
  )
}
