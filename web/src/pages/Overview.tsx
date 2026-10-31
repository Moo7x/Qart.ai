import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../api'
import { ScenarioSwitch, NextStep } from '../components/journey'
import { Legend, PageHead, Serif } from '../components/atoms'
import { OverviewTrends } from '../components/OverviewTrends'
import { SkillSurvey } from '../components/SkillSurvey'
import { JobHub } from '../components/JobHub'
import { OverviewGlance } from '../components/OverviewGlance'
import { RADAR_COLOURS, SkillRadar } from '../components/SkillRadar'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { PackInfo, ProfileData, RadarResponse } from '../types'

// Overview: where you start, the role you are heading for, this week's step, how your skills are
// moving and what is changing in your job. Matching, the plan and the market data have their own
// pages; this page only summarises them.

function PersonalRadar() {
  const { profileId, scenario } = useJourney()
  const view = useApi<RadarResponse>(profileId ? `/api/profiles/${profileId}/radar?scenario=${scenario}` : null)
  const profile = useApi<{ profile: ProfileData }>(profileId ? `/api/profiles/${profileId}` : null)
  const pack = useApi<PackInfo>('/api/pack')
  if (!profileId) return null
  if (view.loading) return <Loading what="your radar" />
  if (view.error) return <Problem what="your radar" message={view.error} onRetry={view.reload} />
  const data = view.data
  if (!data) return null
  const situation = profile.data?.profile.situation
  const job = situation && situation !== 'student' ? pack.data?.current_roles.find((r) => r.id === profile.data?.profile.current_role) : undefined
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
        <div className="flex min-w-0 flex-[1.2_1_380px] flex-col items-center gap-2">
          <SkillRadar axes={data.axes} />
          <Legend items={[{ swatch: RADAR_COLOURS.you, text: 'You (your claims)' }, { swatch: RADAR_COLOURS.needed, text: 'Needed (dashed)' }, { swatch: RADAR_COLOURS.after, text: 'After your plan (estimate)' }]} />
        </div>
        {job && (
          <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-3">
            <div className="flex flex-col gap-0.5">
              <span className="eyebrow">What is changing in your current job</span>
              <span className="text-[13px] text-graphite">Click any part for its source and details.</span>
            </div>
            <JobHub compact soc={job.soc} title={job.title} impact={job.impact} page={job.page} routes={job.transitions.length} />
          </div>
        )}
      </div>
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
      <OverviewTrends />
      <OverviewGlance key={`glance-${refresh}`} />
      <NextStep to="/roles" label="See the roles that fit you" hint="Next: compare the roles your skills lead to" />
    </main>
  )
}
