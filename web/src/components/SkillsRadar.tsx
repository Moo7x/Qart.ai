import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SignalLabel, SkillSignal, SkillSignalsSnapshot } from '../types'
import { label as labelCls } from '../ui'
import { CHART, formatChange, Provenance, SignalBadge, Sparkline } from './SignalParts'

// Momentum order: rising first, insufficient data last; within a label, larger 12-month change first.
const LABEL_ORDER: Record<SignalLabel, number> = { rising: 0, stable: 1, cooling: 2, insufficient_data: 3 }
const byMomentum = (a: SkillSignal, b: SkillSignal) =>
  LABEL_ORDER[a.label] - LABEL_ORDER[b.label] || (b.change_12m ?? -Infinity) - (a.change_12m ?? -Infinity)

const SERIES = [
  { key: 'index', name: 'Share of posts (index)', color: CHART.index },
  { key: 'short', name: '3-month average', color: CHART.short },
  { key: 'long', name: '12-month average', color: CHART.long },
] as const

/**
 * All three lines on one axis: the averages are rebased with the same base month as the index
 * (share / base share × 100), so the chart never needs a second y-scale.
 */
function indexedPoints(skill: SkillSignal) {
  const anchor = skill.points.find(p => p.index !== null && p.index > 0)
  const base = anchor ? (anchor.share * 100) / (anchor.index as number) : null
  const rebase = (v: number | null) => (v === null || !base ? null : Math.round((v / base) * 100))
  return skill.points.map(p => ({
    month: p.month,
    index: p.index === null ? null : Math.round(p.index),
    short: rebase(p.ma_short),
    long: rebase(p.ma_long),
    mentions: p.mentions,
    total: p.total_posts,
  }))
}

function DetailChart({ skill }: { skill: SkillSignal }) {
  const data = indexedPoints(skill)
  const [showTable, setShowTable] = useState(false)
  if (!data.some(d => d.index !== null)) {
    return <p className="text-sm text-graphite">Too few mentions to draw a trend yet.</p>
  }
  return (
    <div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-graphite mb-2" aria-label="Legend">
        {SERIES.map(s => (
          <li key={s.key} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 h-0.5 rounded" style={{ background: s.color }} aria-hidden="true" />
            {s.name}
          </li>
        ))}
      </ul>
      <div className="h-56 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid vertical={false} stroke={CHART.grid} />
            <XAxis dataKey="month" tick={{ fill: CHART.axis, fontSize: 11 }} tickLine={false} axisLine={{ stroke: CHART.grid }} minTickGap={28} />
            <YAxis tick={{ fill: CHART.axis, fontSize: 11 }} tickLine={false} axisLine={false} width={44} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid rgba(0,0,0,0.08)', fontSize: 12 }}
              formatter={(value, name) => [value ?? '–', name]}
              labelFormatter={(m, payload) => {
                const row = payload?.[0]?.payload as { mentions: number; total: number } | undefined
                return row ? `${m} · ${row.mentions} of ${row.total} posts` : String(m)
              }}
            />
            {SERIES.map(s => (
              <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={2} dot={false} activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }} connectNulls={false} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-xs text-graphite">Index: share of job posts mentioning {skill.name}, first month with enough mentions = 100.</p>
      <button type="button" onClick={() => setShowTable(t => !t)} aria-expanded={showTable} className="mt-2 text-xs text-action-ink hover:underline">
        {showTable ? 'Hide the numbers' : 'Show the numbers'}
      </button>
      {showTable && (
        <div className="mt-2 max-h-64 overflow-auto rounded-md border border-hairline">
          <table className="w-full text-xs tabular-nums">
            <thead className="sticky top-0 bg-surface">
              <tr className="text-left text-graphite">
                <th scope="col" className="px-3 py-1.5 font-medium">Month</th>
                <th scope="col" className="px-3 py-1.5 font-medium text-right">Mentions</th>
                <th scope="col" className="px-3 py-1.5 font-medium text-right">Posts</th>
                {SERIES.map(s => <th key={s.key} scope="col" className="px-3 py-1.5 font-medium text-right">{s.name}</th>)}
              </tr>
            </thead>
            <tbody>
              {[...data].reverse().map(d => (
                <tr key={d.month} className="border-t border-hairline">
                  <td className="px-3 py-1 text-ink">{d.month}</td>
                  <td className="px-3 py-1 text-right">{d.mentions}</td>
                  <td className="px-3 py-1 text-right">{d.total}</td>
                  {SERIES.map(s => <td key={s.key} className="px-3 py-1 text-right">{d[s.key] ?? '–'}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function SkillRow({ skill, why }: { skill: SkillSignal; why?: string }) {
  const [open, setOpen] = useState(false)
  const id = `signal-${skill.id}`
  return (
    <li className="border-t border-hairline first:border-t-0">
      <button
        type="button" onClick={() => setOpen(o => !o)} aria-expanded={open} aria-controls={id}
        className="w-full text-left grid grid-cols-[1fr_auto] md:grid-cols-[minmax(0,1.6fr)_9rem_5rem_6.5rem_5.5rem_1.5rem] items-center gap-x-4 gap-y-2 px-4 py-3 hover:bg-canvas transition-colors duration-200"
      >
        <span className="min-w-0">
          <span className="font-medium text-ink">{skill.name}</span>
          {why && <span className="block text-xs text-graphite">{why}</span>}
        </span>
        <span className="md:order-none justify-self-end md:justify-self-start"><SignalBadge label={skill.label} /></span>
        <span className="text-sm tabular-nums text-ink md:text-right"><span className="md:hidden text-xs text-graphite">12-month change </span>{skill.label === 'insufficient_data' ? <span title="Too few mentions for a reliable change">–</span> : formatChange(skill.change_12m)}</span>
        <span className="justify-self-end md:justify-self-start"><Sparkline values={skill.points.map(p => p.ma_short ?? p.share)} label={`${skill.name} trend over ${skill.points.length} months`} /></span>
        <span className="text-xs tabular-nums text-graphite md:text-right">{skill.latest_sample_size} of {skill.latest_total_posts}<span className="md:hidden"> posts last month</span></span>
        <span className="hidden md:block text-graphite" aria-hidden="true">{open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</span>
      </button>
      {open && <div id={id} className="px-4 pb-4"><DetailChart skill={skill} /></div>}
    </li>
  )
}

function Group({ title, skills, why }: { title: string; skills: SkillSignal[]; why: Record<string, string> }) {
  if (skills.length === 0) return null
  return (
    <div>
      <div className={`${labelCls} px-4 pt-4 pb-2`}>{title}</div>
      <div className="hidden md:grid grid-cols-[minmax(0,1.6fr)_9rem_5rem_6.5rem_5.5rem_1.5rem] gap-x-4 px-4 pb-1 text-xs text-graphite">
        <span>Skill</span><span>Signal</span><span className="text-right">12-month change</span><span>Trend</span><span className="text-right">Last month</span><span />
      </div>
      <ul>{skills.map(s => <SkillRow key={s.id} skill={s} why={why[s.id]} />)}</ul>
    </div>
  )
}

/** Skills ranked by momentum; the person's own skills first, then "Skills to watch". */
export default function SkillsRadar({ snapshot, mine }: { snapshot: SkillSignalsSnapshot; mine: Record<string, string> }) {
  const ranked = [...snapshot.series].sort(byMomentum)
  return (
    <div>
      <div className="rounded-lg border border-hairline bg-surface overflow-hidden">
        <Group title="Your skills" skills={ranked.filter(s => mine[s.id])} why={mine} />
        <Group title="Skills to watch" skills={ranked.filter(s => !mine[s.id])} why={{}} />
      </div>
      <Provenance meta={snapshot} extra={`Labels compare the ${snapshot.params.ma_short_months}-month and ${snapshot.params.ma_long_months}-month averages and the 12-month change. Trend signals, not predictions.`} />
    </div>
  )
}
