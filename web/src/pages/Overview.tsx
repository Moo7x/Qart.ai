import { Link } from 'react-router-dom'
import { useApi } from '../api'
import { ScenarioSwitch, NextStep } from '../components/journey'
import { PageHead, Serif } from '../components/atoms'
import { OverviewTiles } from '../components/OverviewTiles'
import { JobHub } from '../components/JobHub'
import { OverviewGlance } from '../components/OverviewGlance'
import { SkillRadar } from '../components/SkillRadar'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { PackInfo, ProfileData, RadarAxis, RadarResponse } from '../types'

// Overview: where you start, the role you are heading for, this week's step, how your skills are
// moving and what is changing in your job. Matching, the plan and the market data have their own
// pages; this page only summarises them.

const EMPHASIS: Record<RadarAxis['emphasis'], [string, string, string]> = {
  rising: ['↑', 'More weight', 'bg-rising text-white'],
  weakening: ['↓', 'Less weight', 'bg-weak text-white'],
  stable: ['→', 'No shift', 'bg-mist text-graphite'],
  fixed: ['■', 'Essential, fixed', 'bg-void text-white'],
}

function AxisRow({ axis }: { axis: RadarAxis }) {
  const [arrow, label, tone] = EMPHASIS[axis.emphasis]
  const use = axis.ai_use
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-line py-2.5" title={axis.reason}>
      <span className="min-w-0">
        <span className="block font-semibold">{axis.name}</span>
        {use && use.automation_share !== null && (
          <span className="block text-[12px] text-graphite">{use.automation_share.toFixed(0)}% of AI use on its tasks is automation · observed</span>
        )}
      </span>
      <span className={`inline-flex min-w-[150px] items-center justify-center gap-2 rounded-full px-3 py-1.5 text-[14px] font-semibold ${tone}`}>
        <span aria-hidden="true" className="text-[18px] leading-none">{arrow}</span>{label}
      </span>
    </li>
  )
}

function PersonalRadar() {
  const { profileId, scenario } = useJourney()
  const view = useApi<RadarResponse>(profileId ? `/api/profiles/${profileId}/radar?scenario=${scenario}` : null)
  if (!profileId) return null
  if (view.loading) return <Loading what="your radar" />
  if (view.error) return <Problem what="your radar" message={view.error} onRetry={view.reload} />
  const data = view.data
  if (!data) return null
  return (
    <section className="section">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="eyebrow">Your skills as AI moves</span>
          <h2 className="m-0 text-xl font-semibold tracking-tight">{data.title}</h2>
          <span className="text-[13px] text-graphite">Which of this role&rsquo;s skills gain or lose weight under {data.scenario_label.toLowerCase()} · estimate</span>
        </div>
        <ScenarioSwitch />
      </div>
      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[1_1_300px] flex-col items-center gap-2">
          <SkillRadar axes={data.axes} />
          <div className="flex flex-wrap justify-center gap-4 font-mono text-[11px] text-graphite">
            <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-0.5 w-5 bg-violet" />you</span>
            <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-0.5 w-5 border-t border-dashed border-weak" />needed</span>
            <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-0.5 w-5 bg-observed" />after your plan</span>
          </div>
        </div>
        <ul className="m-0 min-w-0 flex-[1.3_1_320px] list-none p-0">
          {data.axes.map((a) => <AxisRow key={a.skill} axis={a} />)}
        </ul>
      </div>
    </section>
  )
}

// Working adults and switchers: what the evidence says about the job they have today.
function CurrentJob() {
  const { profileId } = useJourney()
  const profile = useApi<{ profile: ProfileData }>(profileId ? `/api/profiles/${profileId}` : null)
  const pack = useApi<PackInfo>('/api/pack')
  const data = profile.data?.profile
  if (!data || data.situation === 'student') return null
  const role = pack.data?.current_roles.find((r) => r.id === data.current_role)
  if (!role) return null
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <span className="eyebrow">What is changing in your current job</span>
        <span className="text-[13px] text-graphite">Click any part for its source and details.</span>
      </div>
      <JobHub soc={role.soc} title={role.title} impact={role.impact} page={role.page} routes={role.transitions.length} />
    </section>
  )
}

export function Overview() {
  const { setProfileId, setScenario } = useJourney()
  return (
    <main className="page">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <PageHead badge="Overview · GBS finance & accounting · Malaysia" title={<>Your <Serif>next</Serif> move starts here</>} />
        <Link to="/start" className="text-sm text-graphite underline underline-offset-4" onClick={() => { setProfileId(null); setScenario('moderate') }}>Start over</Link>
      </header>
      <div className="q-tray"><OverviewTiles /></div>
      <OverviewGlance />
      <PersonalRadar />
      <CurrentJob />
      <NextStep to="/roles" label="See the roles that fit you" hint="Next: compare the roles your skills lead to" />
    </main>
  )
}
