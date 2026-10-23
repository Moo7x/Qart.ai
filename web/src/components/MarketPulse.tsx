import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Info } from 'lucide-react'
import { getAiTrend } from '../api'
import type { AiTrend } from '../types'
import { CHART, Provenance } from './SignalParts'

/**
 * Share of job postings mentioning AI, one region at a time (a single series: the title names it,
 * no legend box). Data comes from one loader (GET /api/signals/ai-trend): the public job boards
 * for Malaysia, Singapore, APAC or remote once a region has a few weeks of history, otherwise the
 * Indeed tracker, labelled "not Malaysia", with today's job-board figure shown beside it.
 */
export default function MarketPulse() {
  const [region, setRegion] = useState<string | undefined>(undefined)
  const [trend, setTrend] = useState<AiTrend | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    getAiTrend(region).then(t => { setTrend(t); setFailed(false) }).catch(() => setFailed(true))
  }, [region])

  if (failed) return <p className="text-sm text-graphite">The AI trend could not be loaded.</p>
  if (!trend || !trend.meta) return null

  const points = trend.points
  const latest = [...points].reverse().find(p => p.share_pct !== null)
  const periods = new Set(points.map(p => p.period))
  const events = (trend.meta.events ?? []).filter(e => periods.has(e.month))
  const options = [
    ...trend.options.ats_regions.map(r => ({ id: r.id, label: r.label, group: 'Job boards' })),
    ...trend.options.indeed_countries.map(c => ({ id: c.id, label: c.label, group: 'Indeed' })),
  ]
  const asked = region ?? (trend.ats_latest?.region ?? trend.region)
  const unit = trend.granularity === 'week' ? 'week' : 'month'

  return (
    <div className="rounded-lg border border-hairline bg-surface p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="font-semibold text-ink">AI share of job postings · {trend.region_label}</div>
          {latest && (
            <div className="text-sm text-graphite tabular-nums">
              {latest.share_pct?.toFixed(1)}% of postings mentioned AI in {latest.period}
              {latest.total ? ` (${latest.total} postings)` : ''}
            </div>
          )}
        </div>
        <span className="text-xs text-graphite">{trend.meta.attribution}</span>
      </div>

      <label className="mt-4 flex flex-wrap items-center gap-2 text-sm text-graphite">
        Region
        <select value={asked} onChange={e => setRegion(e.target.value)} className="rounded-sm border border-hairline-strong bg-surface px-2 py-1 text-sm text-ink">
          {['Job boards', 'Indeed'].map(group => (
            <optgroup key={group} label={group === 'Indeed' ? 'Indeed AI Tracker (not Malaysia)' : 'Public job boards'}>
              {options.filter(o => o.group === group).map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
            </optgroup>
          ))}
        </select>
      </label>

      {trend.ats_latest && trend.mode !== 'ats' && (
        <div className="mt-4 rounded-md bg-action-tint px-4 py-3 text-sm text-ink">
          <p className="font-medium">
            Today on the public job boards: {trend.ats_latest.share_pct === null ? 'too few postings to tell' : `${trend.ats_latest.share_pct.toFixed(1)}%`} of{' '}
            {trend.ats_latest.total} open postings in {trend.ats_latest.label} mention AI ({trend.ats_latest.data_as_of}).
          </p>
          {trend.fallback_reason && <p className="mt-1 flex gap-1.5 text-xs text-graphite"><Info size={14} className="mt-px shrink-0" aria-hidden="true" />{trend.fallback_reason}</p>}
        </div>
      )}
      {!trend.ats_latest && trend.fallback_reason && <p className="mt-3 text-xs text-graphite">{trend.fallback_reason}</p>}

      <div className="mt-4 h-60 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 16, right: 12, bottom: 0, left: -16 }}>
            <CartesianGrid vertical={false} stroke={CHART.grid} />
            <XAxis dataKey="period" tick={{ fill: CHART.axis, fontSize: 11 }} tickLine={false} axisLine={{ stroke: CHART.grid }} minTickGap={36} />
            <YAxis tick={{ fill: CHART.axis, fontSize: 11 }} tickLine={false} axisLine={false} width={44} unit="%" />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid rgba(0,0,0,0.08)', fontSize: 12 }}
              formatter={(value, _name, item) => {
                const total = (item?.payload as { total?: number | null } | undefined)?.total
                return [`${Number(value).toFixed(1)}% of postings${total ? ` (${total})` : ''}`, `AI share per ${unit}`]
              }}
            />
            {events.map((e, i) => (
              <ReferenceLine key={e.month} x={e.month} stroke={CHART.event} label={{ value: String(i + 1), position: 'top', fill: CHART.axis, fontSize: 11 }} />
            ))}
            <Line type="monotone" dataKey="share_pct" name="AI share" stroke={CHART.index} strokeWidth={2} dot={trend.mode === 'ats'} connectNulls={false} activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {events.length > 0 && (
        <ol className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-graphite" aria-label="Events on the chart">
          {events.map((e, i) => (
            <li key={e.month}>
              <span className="font-medium text-ink tabular-nums">{i + 1}</span>{' '}
              <a href={e.url} target="_blank" rel="noreferrer" className="hover:underline">{e.label}</a> ({e.month})
              {!e.verified && <span title="Link not checked automatically; a person should confirm it"> · link unverified</span>}
            </li>
          ))}
        </ol>
      )}
      <Provenance
        meta={{ ...trend.meta, stale: trend.stale }}
        extra={trend.mode === 'indeed' ? 'Shown for context; this is not Malaysian data.' : trend.meta.coverage ? `Companies covered: ${trend.meta.coverage.companies.length}.` : undefined}
      />
    </div>
  )
}
