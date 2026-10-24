import { useState } from 'react'
import { useT } from '../i18n'
import { Link } from 'react-router-dom'
import { formatWhen, useApi } from '../api'
import { EvidenceDrawer } from '../components/EvidenceDrawer'
import { ScenarioSwitch, levelText, JourneyRoute, NextStep } from '../components/journey'
import { Sparkline } from '../components/LineChart'
import { TimeSeriesChart, type ChartSeries } from '../components/Charts'
import { JobPosts } from '../components/CompareRoles'
import { OccupationEvidence } from '../components/OccupationEvidence'
import { SkillRadar } from '../components/SkillRadar'
import { DIRECTION_LABEL, Empty, Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { Direction, MatchesResponse, PackInfo, PathwayResponse, ProfileData, ProgressResponse, RadarAxis, RadarResponse, Signal, SignalsResponse, SourceStatus } from '../types'

// Occupation groups drawn in the chart, with one colour each (dark-panel palette).
const GROUP_COLOURS: Record<string, { label: string; color: string }> = {
  dosm_share_clerical: { label: 'Clerical support workers', color: '#ffa86b' },
  dosm_share_professionals: { label: 'Professionals', color: '#9d86ff' },
  dosm_share_technicians: { label: 'Technicians & associate professionals', color: '#5de3ff' },
}
const LIST_ORDER: Direction[] = ['rising', 'weakening', 'stable', 'insufficient', 'expert']
const GROUP_STYLE: Record<Direction, { arrow: string; color: string }> = {
  rising: { arrow: '↑', color: 'text-rising' },
  weakening: { arrow: '↓', color: 'text-weak' },
  stable: { arrow: '→', color: 'text-graphite' },
  insufficient: { arrow: '?', color: 'text-graphite' },
  expert: { arrow: '◆', color: 'text-observed' },
}
const SPARK_COLOUR: Record<string, string> = { up: '#157a4a', down: '#9a4609', flat: '#747686' }

function SignalRow({ signal, selected, onPick }: { signal: Signal; selected: boolean; onPick: () => void }) {
  const style = GROUP_STYLE[signal.direction]
  return (
    <button
      type="button"
      onClick={onPick}
      aria-pressed={selected}
      className={`grid w-full cursor-pointer grid-cols-[20px_minmax(0,1fr)_auto] items-start gap-x-3 border-0 border-b border-mist px-4 py-3 text-left hover:bg-fog ${selected ? 'bg-violet-soft' : 'bg-white'}`}
    >
      <span aria-hidden="true" className={`font-mono font-semibold ${style.color}`}>
        {style.arrow}
      </span>
      <span className="min-w-0">
        <span className="block font-medium">{signal.title}</span>
        <span className="block text-xs text-graphite">{signal.headline}</span>
      </span>
      <span className="flex flex-col items-end gap-1">
        <Sparkline points={signal.points} color={SPARK_COLOUR[signal.early_direction ?? 'flat']} />
        <span className="whitespace-nowrap font-mono text-[11px] text-ash">
          {signal.independent_sources} source{signal.independent_sources === 1 ? '' : 's'}
        </span>
      </span>
    </button>
  )
}

function AiUseTable({ rows, onPick }: { rows: Signal[]; onPick: (s: Signal) => void }) {
  if (rows.length === 0) return <Empty>No Economic Index release has been collected yet.</Empty>
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-[13px]">
        <thead>
          <tr className="cap text-left">
            <th className="py-2 pr-2 font-medium">Occupation</th>
            <th className="px-2 py-2 font-medium">Where</th>
            <th className="px-2 py-2 text-right font-medium">First month</th>
            <th className="px-2 py-2 text-right font-medium">Second month</th>
            <th className="py-2 pl-2 font-medium">Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => {
            const [first, last] = [s.points[0], s.points.at(-1)!]
            const where = s.title.endsWith('(Malaysia)') ? 'Malaysia' : 'Global'
            const name = s.title.replace(/^AI use · /, '').replace(/ \((Malaysia|global)\)$/, '')
            return (
              <tr key={s.id} className="cursor-pointer border-t border-mist hover:bg-fog" onClick={() => onPick(s)}>
                <td className="py-2.5 pr-2">
                  <button type="button" className="cursor-pointer border-0 bg-transparent p-0 text-left font-medium" onClick={() => onPick(s)}>
                    {name}
                  </button>
                </td>
                <td className="px-2 py-2.5 text-graphite">{where}</td>
                <td className="px-2 py-2.5 text-right font-mono">{first.value.toFixed(2)}%</td>
                <td className="px-2 py-2.5 text-right font-mono">{last.value.toFixed(2)}%</td>
                <td className="py-2.5 pl-2 font-mono text-xs text-graphite">
                  {s.early_direction === 'flat' ? 'within rounding' : s.early_direction === 'up' ? '↑ real change' : '↓ real change'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

const EMPHASIS: Record<RadarAxis['emphasis'], [string, string]> = {
  rising: ['↑ more emphasis', 'text-rising'],
  weakening: ['↓ less emphasis', 'text-weak'],
  stable: ['→ no shift', 'text-graphite'],
  fixed: ['■ essential, fixed', 'text-weak'],
}

function AxisRow({ axis }: { axis: RadarAxis }) {
  const [label, tone] = EMPHASIS[axis.emphasis]
  const use = axis.ai_use
  return (
    <li className="flex flex-col gap-1 border-t border-line py-2.5 text-[13px]" title={axis.reason}>
      <span className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-semibold">{axis.name}</span>
        <span className="font-mono text-[11px] text-graphite">you {levelText(axis.claimed)} · needs {levelText(axis.required)} · after {levelText(axis.after)}</span>
      </span>
      <span className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
        <span className={tone}>{label} <span className="text-graphite">(assumption)</span></span>
        {use && use.automation_share !== null && (
          <span className="text-graphite">
            {use.automation_share.toFixed(0)}% automation-style AI use{' '}
            {use.basis === 'task' ? `on ${use.tasks_observed} of ${use.tasks_linked} tasks` : 'for the occupation'}{' '}
            <span className="text-slate-mid">(observed)</span>
          </span>
        )}
        {axis.in_demand && <span className="text-observed">in demand, TalentCorp <span className="text-graphite">(expert)</span></span>}
      </span>
    </li>
  )
}

function PersonalRadar({ onPick }: { onPick: (s: Signal) => void }) {
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
          <span className="eyebrow">Your future skills radar</span>
          <h2 className="m-0 text-xl font-semibold tracking-tight">{data.title}</h2>
          <span className="text-[13px] text-graphite">
            {data.chosen ? 'Your chosen destination' : 'Your best-fitting role so far'} · fit {Math.round(data.fit)} now,{' '}
            {Math.round(data.fit_after)} after the pathway (estimate) · {data.scenario_label}
          </span>
        </div>
        <ScenarioSwitch />
      </div>
      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[1_1_300px] flex-col items-center gap-2">
          <SkillRadar axes={data.axes} />
          <div className="flex flex-wrap justify-center gap-4 font-mono text-[11px] text-graphite">
            <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-0.5 w-5 bg-violet" />you (claim)</span>
            <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-0.5 w-5 border-t border-dashed border-weak" />needed</span>
            <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-0.5 w-5 bg-observed" />after pathway (estimate)</span>
          </div>
        </div>
        <ul className="m-0 min-w-0 flex-[1.3_1_320px] list-none p-0">
          {data.axes.map((a) => <AxisRow key={a.skill} axis={a} />)}
        </ul>
      </div>
      {data.field_signals.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <span className="cap">Signals for your current job</span>
          <div className="flex flex-wrap gap-2">
            {data.field_signals.map((s) => (
              <button key={s.id} type="button" onClick={() => onPick(s)} className="cursor-pointer rounded border border-line bg-paper px-3 py-2 text-left text-[12px] text-void hover:bg-violet-soft">
                <span className="block font-semibold">{s.title}</span>
                <span className="block text-graphite">{s.headline} · {DIRECTION_LABEL[s.direction]}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <p className="m-0 text-xs text-graphite">
        Levels are your claims, never verified. Emphasis is the scenario rule applied to observed AI use; it is not a forecast of jobs.
      </p>
    </section>
  )
}

function PersonalSummary() {
  const { profileId, scenario } = useJourney()
  const view = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=${scenario}` : null)
  const progress = useApi<ProgressResponse>(profileId ? `/api/profiles/${profileId}/progress?scenario=${scenario}` : null)
  const path = useApi<PathwayResponse>(profileId && view.data?.destination ? `/api/profiles/${profileId}/pathway?scenario=${scenario}` : null)
  if (view.loading) return <Loading what="your career picture" />
  if (view.error) return <Problem what="your career picture" message={view.error} onRetry={view.reload} />
  if (!view.data) return null
  const data = view.data
  const target = data.roles.find((r) => r.role_id === data.destination) ?? data.roles[0]
  const gap = target?.requirements.filter((r) => r.column !== 'ready').sort((a, b) => Number(b.essential) - Number(a.essential) || b.weight - a.weight)[0]
  const next = path.data?.steps.find((s) => !progress.data?.done.includes(s.course.id))
  return <section className="personal-summary" aria-label="Your career picture">
    <div className="flex min-w-0 flex-col gap-5">
      <div><span className="cap">Your starting point</span><h2 className="mt-2 text-[26px] font-semibold leading-tight tracking-tight">{data.current_role?.title ?? 'Your stated skills and experience'}</h2><span className="text-xs text-graphite">Your profile · editable, self-reported skills</span></div>
      <div className="border-l-2 border-violet pl-4"><span className="cap">A gap to focus on</span><p className="my-1 font-semibold">{gap?.skill_name ?? 'No gap in your stated skills for this role'}</p>{gap && <p className="m-0 text-xs text-graphite">For {target.title}: you {levelText(gap.claimed)} → needs {levelText(gap.required)}{gap.essential ? ' · essential' : ''}. Requirement: TalentCorp GBS study (2024){gap.evidence_pages.length > 0 ? `, PDF p. ${gap.evidence_pages.join(', ')}` : ''}; levels and weights are assumptions.</p>}</div>
      <div className="border-t border-line pt-4"><span className="cap">Your next step</span><p role={path.loading || progress.loading ? 'status' : undefined} className="my-2 text-sm">{path.loading || progress.loading ? 'Loading your next step…' : next ? `${next.course.title} · ${next.hours} h (estimate)` : data.destination ? 'Review your plan and record the courses you complete.' : 'Compare the roles and choose the destination you want.'}</p><Link className="btn btn-v" to={data.destination ? '/pathway' : '/roles'}>{data.destination ? 'Continue my plan →' : 'Explore my options →'}</Link></div>
    </div>
    <div className="flex min-w-0 flex-col gap-3"><div className="flex flex-wrap items-baseline justify-between gap-2"><h2 className="h2">Your best-fitting roles</h2><span className="tag bg-estimate-bg text-estimate">Estimate · {scenario} adoption</span></div>
      {data.roles.slice(0,3).map((r, i) => <div key={r.role_id} className="grid grid-cols-[24px_minmax(0,1fr)_auto] items-start gap-3 border-t border-line py-4"><span className="font-mono text-ash">0{i+1}</span><div><Link to="/roles" className="text-[16px] font-semibold text-void no-underline hover:underline">{r.title}</Link><p className="my-1 text-xs text-graphite">{r.longer_route ? 'Essential skills still to build' : 'Essential requirements covered by your claims'} · TalentCorp</p><JobPosts title={r.title} className="job-link" /></div><span className="text-right font-mono text-[28px] leading-none">{Math.round(r.fit)}<span className="block pt-2 text-[11px] text-graphite">/ 100 fit</span></span></div>)}
      <p className="m-0 text-xs text-graphite">Fit measures weighted skill-requirement coverage, not your chance of getting hired. <Link to="/roles">See each calculation →</Link></p>
    </div>
  </section>
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
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <span className="eyebrow">What is changing in your current job</span>
        <h2 className="h2">{role.title}</h2>
        <p className="m-0 text-[13px] text-graphite">
          TalentCorp rates it {role.impact} impact (PDF p. {role.page}) and lists {role.transitions.length} routes from it in GBS. Below is the evidence for its standard occupation.
        </p>
      </div>
      <OccupationEvidence soc={role.soc} compact />
    </section>
  )
}

export function Overview() {
  const { t } = useT()
  const { setProfileId, setScenario } = useJourney()
  const signals = useApi<SignalsResponse>('/api/signals')
  const sources = useApi<SourceStatus[]>('/api/sources')
  const [selected, setSelected] = useState<Signal | null>(null)

  const all = signals.data?.signals ?? []
  const chartSeries: ChartSeries[] = all
    .filter((s) => s.id in GROUP_COLOURS)
    .map((s) => ({ ...GROUP_COLOURS[s.id], points: s.points }))
  const listed = all.filter((s) => s.family !== 'ai_task_use')
  const aiUse = all.filter((s) => s.family === 'ai_task_use')

  return (
    <main className="page">
      <JourneyRoute />
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">Overview · GBS finance &amp; accounting · Malaysia</span>
        <h1 className="h1">{t('Your next move starts here')}</h1>
        <p className="m-0 max-w-[660px] text-graphite">
          Your skills today, the roles they lead to, and what to build next. Market evidence explains the context; you choose the direction.
        </p>
      </header>
      <div className="flex flex-wrap items-center gap-3">
        <Link className="btn" to="/start?edit=1">Edit my profile</Link>
        <Link to="/start" className="text-sm text-graphite underline underline-offset-4" onClick={() => { setProfileId(null); setScenario('moderate') }}>Start over</Link>
      </div>

      <PersonalSummary />
      <PersonalRadar onPick={setSelected} />
      <CurrentJob />

      {signals.loading && <Loading what="the evidence" />}
      {signals.error && <Problem what="the evidence" message={signals.error} onRetry={signals.reload} />}
      {signals.data && all.length === 0 && (
        <div className="card-light">
          <Empty>
            No evidence collected yet. The first pipeline run starts automatically on a new deployment; see{' '}
            <Link to="/live">{t('Live intelligence')}</Link> for its progress.
          </Empty>
        </div>
      )}

      {all.length > 0 && (
        <div className="flex flex-wrap items-stretch gap-5">
          <section className="card-light flex min-w-0 flex-[3_1_480px] flex-col gap-3.5 p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="h2">How Malaysia’s workforce has shifted since 2011</h2>
              <span className="font-mono text-xs text-graphite">Observed · % of employees · 2011–2025</span>
            </div>
            <p className="m-0 max-w-[760px] text-[14px] leading-relaxed"><span className="font-semibold">What this shows:</span> out of every 100 employees in Malaysia, how many work in each type of job, year by year since 2011 (official DOSM figures). A rising line means that type of work is a growing part of the workforce; a falling line, a shrinking part. Finance clerks are counted under clerical support, accountants under professionals.</p>
            <TimeSeriesChart series={chartSeries} unit="% of employees" axis="%" source="OpenDOSM · employees by occupation, 2011–2025" />
            <p className="m-0 text-xs text-graphite">
              Observed history from OpenDOSM; 2010 is left out because the occupation classification changed in 2011.
              Finance clerks sit in clerical support, accountants in professionals.
            </p>
            <div className="flex flex-col gap-1.5 border-t border-line pt-3">
              <span className="cap">Feeding this page</span>
              <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 font-mono text-xs">
                {(sources.data ?? []).map((s) => (
                  <span key={s.id} className="contents">
                    <span className="text-graphite">{s.name}</span>
                    <span className="text-slate-mid">{s.last_fetched ? `fetched ${formatWhen(s.last_fetched)}` : 'not fetched yet'}</span>
                  </span>
                ))}
              </div>
            </div>
          </section>

          <section className="card-light flex min-w-0 flex-[2_1_340px] flex-col overflow-hidden">
            <div className="flex items-baseline justify-between px-4 pb-2.5 pt-4">
              <h2 className="h2">Signals</h2>
              <span className="cap">select one for its evidence</span>
            </div>
            {LIST_ORDER.map((direction) => {
              const items = listed.filter((s) => s.direction === direction)
              if (items.length === 0) return null
              return (
                <div key={direction} className="flex flex-col">
                  <span className={`cap px-4 pb-1 pt-2.5 ${GROUP_STYLE[direction].color}`}>{DIRECTION_LABEL[direction]}</span>
                  {items.map((s) => (
                    <SignalRow key={s.id} signal={s} selected={selected?.id === s.id} onPick={() => setSelected(s)} />
                  ))}
                </div>
              )
            })}
          </section>
        </div>
      )}

      {all.length > 0 && (
        <section className="card-light flex flex-col gap-3 px-6 py-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="h2">AI use by finance occupation</h2>
            <span className="text-[13px] text-graphite">
              Share of sampled Claude conversations, Anthropic Economic Index. Shows use of AI, not hiring or job losses.
            </span>
          </div>
          <AiUseTable rows={aiUse} onPick={setSelected} />
        </section>
      )}

      {selected && <EvidenceDrawer signal={selected} onClose={() => setSelected(null)} />}
      <NextStep to="/roles" label="See the roles that fit you" hint="Next: compare the roles your skills lead to" />
    </main>
  )
}
