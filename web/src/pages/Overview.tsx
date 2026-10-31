import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../api'
import { ScenarioSwitch, NextStep } from '../components/journey'
import { Legend, PageHead, Serif } from '../components/atoms'
import { OverviewTiles } from '../components/OverviewTiles'
import { SkillSurvey } from '../components/SkillSurvey'
import { JobHub } from '../components/JobHub'
import { OverviewGlance } from '../components/OverviewGlance'
import { RADAR_COLOURS, SkillRadar } from '../components/SkillRadar'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { PackInfo, ProfileData, RadarAxis, RadarResponse } from '../types'

// Overview: where you start, the role you are heading for, this week's step, how your skills are
// moving and what is changing in your job. Matching, the plan and the market data have their own
// pages; this page only summarises them.

const EMPHASIS: Record<RadarAxis['emphasis'], [string, string, string]> = {
  rising: ['▲', 'More weight', 'text-rising'],
  weakening: ['▼', 'Less weight', 'text-weak'],
  stable: ['→', 'No shift', 'text-muted'],
  fixed: ['■', 'Essential, fixed', 'text-ink'],
}

function AxisRow({ axis }: { axis: RadarAxis }) {
  const [arrow, label, tone] = EMPHASIS[axis.emphasis]
  return (
    <tr className="border-t border-[#f0f0f0]" title={axis.reason}>
      <td className="py-1.5 pr-2">{axis.name}</td>
      <td className="text-muted">{axis.claimed ?? '—'}</td>
      <td className="font-semibold">{axis.required}</td>
      <td className={`whitespace-nowrap text-right font-bold ${tone}`}><span aria-hidden="true">{arrow}</span><span className="sr-only">{label}</span></td>
    </tr>
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
          <Legend items={[{ swatch: RADAR_COLOURS.you, text: 'You (your claims)' }, { swatch: RADAR_COLOURS.needed, text: 'Needed (dashed)' }, { swatch: RADAR_COLOURS.after, text: 'After your plan (estimate)' }]} />
        </div>
        <div className="q-card min-w-0 flex-[1_1_300px] gap-2 shadow-[0_10px_30px_rgba(108,71,255,.08)]">
          <span className="text-[13px] font-semibold">How each skill moves · {data.scenario_label}</span>
          <table className="w-full border-collapse text-[13px]">
            <caption className="sr-only">Each skill: your level, the level needed and how its weight moves under this scenario</caption>
            <thead><tr className="text-left text-[11px] text-muted"><th className="py-1 font-medium">Skill</th><th className="font-medium">You</th><th className="font-medium">Needs</th><th className="font-medium"><span className="sr-only">Weight</span></th></tr></thead>
            <tbody>{data.axes.map((a) => <AxisRow key={a.skill} axis={a} />)}</tbody>
          </table>
          <p className="q-src">Levels are your claims. Arrows: weight under this scenario (assumption); essentials never move.</p>
        </div>
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
  // Bumped when the skills survey closes, so every section reads the new answers.
  const [refresh, setRefresh] = useState(0)
  return (
    <main className="page">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <PageHead badge="Overview · GBS finance & accounting · Malaysia" title={<>Your <Serif>next</Serif> move starts here</>} />
        <Link to="/start" className="text-sm text-graphite underline underline-offset-4" onClick={() => { setProfileId(null); setScenario('moderate') }}>Start over</Link>
      </header>
      <PersonalRadar key={`radar-${refresh}`} />
      <SkillSurvey onDone={() => setRefresh((r) => r + 1)} />
      <div className="q-tray"><OverviewTiles key={`tiles-${refresh}`} /></div>
      <OverviewGlance key={`glance-${refresh}`} />
      <CurrentJob />
      <NextStep to="/roles" label="See the roles that fit you" hint="Next: compare the roles your skills lead to" />
    </main>
  )
}
