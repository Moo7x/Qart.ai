import { useState } from 'react'
import { useApi } from '../api'
import { CvPopup } from '../pages/onboarding/CvPopup'
import type { Point, Scenario, TrendSkill, TrendsResponse } from '../types'
import { Label, Legend, OVERVIEW_SCENARIO, SCENARIO_TEXT, Serif } from './atoms'
import { LineChart } from './LineChart'
import { Loading, Problem } from './ui'

// Trends on the Overview (GET /api/trends, unchanged): skills rising or declining under the chosen
// AI scenario, and job groups rising or declining in DOSM's published shares. "More" opens the
// numbers behind each row as a chart built from those same values, never a drawn line.

const SHOWN = 5
type Direction = 'rising' | 'declining' | 'steady'
type GroupRow = { id: string; title: string; sub: string; points: Point[]; change: number; unit: string; source: string }
type Detail = { kind: 'skill'; skill: TrendSkill } | { kind: 'group'; row: GroupRow }

const direction = (change: number): Direction => (Math.abs(change) < 0.005 ? 'steady' : change > 0 ? 'rising' : 'declining')

function Trend({ change }: { change: number }) {
  const d = direction(change)
  const [arrow, tone] = d === 'rising' ? ['↗', 'bg-rising-bg text-rising'] : d === 'declining' ? ['↘', 'bg-weak-bg text-weak'] : ['→', 'bg-mist text-graphite']
  return <span className={`whitespace-nowrap rounded-full px-3 py-1.5 text-[13px] font-semibold ${tone}`}>{d} <span aria-hidden="true">{arrow}</span></span>
}

function Row({ title, sub, change, onMore }: { title: string; sub: string; change: number; onMore: () => void }) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-t border-[#eeeef0] py-3">
      <span className="min-w-0">
        <span className="block text-[15px] font-medium leading-snug">{title}</span>
        <span className="block text-xs text-muted">{sub}</span>
      </span>
      <Trend change={change} />
      <button type="button" className="q-btn min-h-[40px] border-[#d9d9de] px-4 text-[13px]" onClick={onMore} aria-label={`More about ${title}`}>More</button>
    </li>
  )
}

export function OverviewTrends() {
  const scenario = OVERVIEW_SCENARIO
  const view = useApi<TrendsResponse>('/api/trends')
  const [allSkills, setAllSkills] = useState(false)
  const [allGroups, setAllGroups] = useState(false)
  const [detail, setDetail] = useState<Detail | null>(null)
  if (view.loading) return <Loading what="the trends" />
  if (view.error) return <Problem what="the trends" message={view.error} onRetry={view.reload} />
  const data = view.data
  if (!data) return null
  const skills = [...data.skills_by_scenario[scenario]].sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
  const groups: GroupRow[] = [
    ...data.employment.map((e) => ({
      id: `emp-${e.group}`,
      title: e.title,
      sub: `share of employees · ${e.first}–${e.last}`,
      points: e.points,
      change: e.change_recent ?? e.change_long,
      unit: '% of employees',
      source: 'DOSM, wages by occupation (OpenDOSM API)',
    })),
    ...data.job_ads.named.map((n) => ({
      id: `ads-${n.entity}`,
      title: n.entity,
      sub: `share of online job ads · ${n.points[0]?.period}–${n.points.at(-1)?.period}`,
      points: n.points,
      change: (n.points.at(-1)?.value ?? 0) - (n.points[0]?.value ?? 0),
      unit: '% of online job offerings',
      source: 'DOSM Job Market Insights',
    })),
  ].sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
  return (
    <section aria-label="Trends" className="flex flex-col gap-5 rounded-[28px] bg-white p-5 sm:p-7">
      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-violet">4 · Trends</span>
        <h2 className="m-0 text-[clamp(24px,3vw,32px)] font-medium tracking-[-0.02em]"><Serif>Trends</Serif> in GBS finance</h2>
        <p className="m-0 text-sm text-[#404040]">What is rising and declining. Tap “More” for the numbers behind each row.</p>
      </div>
      <div className="grid gap-x-10 gap-y-6 lg:grid-cols-2">
        <div className="flex min-w-0 flex-col">
          <span className="flex flex-wrap items-center gap-2 pb-2.5 text-[15px] font-semibold">Skills · {SCENARIO_TEXT[scenario]} <Label kind="assumption" /></span>
          <ul className="m-0 list-none p-0">
            {(allSkills ? skills : skills.slice(0, SHOWN)).map((s) => (
              <Row key={s.skill} title={s.name} sub={`weight ${s.change > 0 ? '+' : ''}${s.change}% · in ${s.roles} role${s.roles === 1 ? '' : 's'}`} change={s.change} onMore={() => setDetail({ kind: 'skill', skill: s })} />
            ))}
          </ul>
          {skills.length > SHOWN && <button type="button" className="q-btn mt-3 self-start border-[#d9d9de]" aria-expanded={allSkills} onClick={() => setAllSkills((v) => !v)}>{allSkills ? 'Show fewer' : `Show all ${skills.length} skills`}</button>}
          <p className="q-src mt-2">Weight change of each skill under the scenario, from observed AI use ({data.evidence_source}, {data.evidence_period}). Essentials never move.</p>
        </div>
        <div className="flex min-w-0 flex-col">
          <span className="flex flex-wrap items-center gap-2 pb-2.5 text-[15px] font-semibold">Job groups in Malaysia <Label kind="observed" /></span>
          <ul className="m-0 list-none p-0">
            {(allGroups ? groups : groups.slice(0, SHOWN)).map((g) => (
              <Row key={g.id} title={g.title} sub={g.sub} change={g.change} onMore={() => setDetail({ kind: 'group', row: g })} />
            ))}
          </ul>
          {groups.length > SHOWN && <button type="button" className="q-btn mt-3 self-start border-[#d9d9de]" aria-expanded={allGroups} onClick={() => setAllGroups((v) => !v)}>{allGroups ? 'Show fewer' : `Show all ${groups.length} groups`}</button>}
          <p className="q-src mt-2">DOSM share of employees by occupation group (recent change since {data.recent_from}) and DOSM share of online job ads by occupation.</p>
        </div>
      </div>
      {detail && <TrendPopup detail={detail} data={data} onClose={() => setDetail(null)} />}
    </section>
  )
}

function TrendPopup({ detail, data, onClose }: { detail: Detail; data: TrendsResponse; onClose: () => void }) {
  const title = detail.kind === 'skill' ? detail.skill.name : detail.row.title
  return (
    <CvPopup onClose={onClose}>
      <section aria-label={title} className="flex min-w-0 flex-[1_1_100%] flex-col gap-4">
        <div className="pr-12">
          <h2 id="j-title" className="m-0 text-[clamp(24px,3.4vw,34px)] font-medium leading-[1.1] tracking-[-0.02em]">{title}</h2>
        </div>
        {detail.kind === 'skill' ? <SkillDetail skill={detail.skill} data={data} /> : <GroupDetail row={detail.row} />}
      </section>
    </CvPopup>
  )
}

const SCENARIO_COLOUR: Record<Scenario, string> = { moderate: '#0072B2', fast: '#D55E00' }

function SkillDetail({ skill, data }: { skill: TrendSkill; data: TrendsResponse }) {
  const values = (['moderate', 'fast'] as Scenario[]).map((s) => ({ s, change: data.skills_by_scenario[s].find((x) => x.skill === skill.skill)?.change ?? 0 }))
  const max = Math.max(10, ...values.map((v) => Math.abs(v.change)))
  return (
    <div className="q-card gap-3">
      <span className="flex flex-wrap items-center gap-2 text-[13px]">Weight change under each AI scenario <Label kind="assumption" /></span>
      <div role="img" aria-label={values.map((v) => `${SCENARIO_TEXT[v.s]}: ${v.change}%`).join('; ')} className="flex flex-col gap-3">
        {values.map((v) => (
          <div key={v.s} className="grid grid-cols-[150px_minmax(0,1fr)_64px] items-center gap-3 text-[13px]">
            <span>{SCENARIO_TEXT[v.s]}</span>
            <span className="relative h-6 rounded-md bg-[#f5f5f5]">
              <span className="absolute inset-y-0 left-1/2 w-px bg-[#d4d4d4]" />
              <span className="m-grow absolute inset-y-1 rounded" style={{ background: SCENARIO_COLOUR[v.s], width: `${(50 * Math.abs(v.change)) / max}%`, ...(v.change >= 0 ? { left: '50%' } : { right: '50%' }) }} />
            </span>
            <span className="text-right font-semibold">{v.change > 0 ? '+' : ''}{v.change}%</span>
          </div>
        ))}
        <div className="grid grid-cols-[150px_minmax(0,1fr)_64px] gap-3 text-[11px] text-muted-2" aria-hidden="true">
          <span />
          <span className="flex justify-between"><span>−{max}%</span><span>0</span><span>+{max}%</span></span>
          <span />
        </div>
      </div>
      <Legend items={values.map((v) => ({ swatch: SCENARIO_COLOUR[v.s], text: SCENARIO_TEXT[v.s] }))} />
      <p className="q-src">
        How much more (or less) the {skill.roles} destination role{skill.roles === 1 ? '' : 's'} that need {skill.name} weigh it under each scenario, averaged. Based on observed AI use of its {skill.basis.join(' and ')}-level evidence: {data.evidence_source}, {data.evidence_period}. A scenario estimate from one release, not a series over time; essentials never move.
      </p>
    </div>
  )
}

function GroupDetail({ row }: { row: GroupRow }) {
  const first = row.points[0]
  const last = row.points.at(-1)
  return (
    <div className="q-card gap-3">
      <span className="flex flex-wrap items-center gap-2 text-[13px]">{row.unit} <Label kind="observed" /> {first && last && <span className="text-muted">{first.period}: {first.value} → {last.period}: {last.value}</span>}</span>
      <LineChart series={[{ label: row.title, color: '#6c47ff', points: row.points }]} unit={row.unit} dark={false} />
      <Legend items={[{ swatch: '#6c47ff', text: `${row.title} (${row.unit})` }]} />
      <p className="q-src">Source: {row.source}. Observed values as published; each point is one release.</p>
    </div>
  )
}
