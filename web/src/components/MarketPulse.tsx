import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { MarketPulseSnapshot } from '../types'
import { CHART, Provenance } from './SignalParts'

/**
 * Monthly share of job postings mentioning AI, one country at a time (a single series, so the
 * title names it and no legend box is needed). Only countries present in the data are offered;
 * the default is labelled as "not Malaysia" because Malaysia is not covered.
 */
export default function MarketPulse({ snapshot }: { snapshot: MarketPulseSnapshot }) {
  const [country, setCountry] = useState(snapshot.default_country)
  const series = snapshot.series.find(s => s.country === country && s.series === 'AI') ?? snapshot.series.find(s => s.country === country)
  const points = series?.points ?? []
  const latest = points[points.length - 1]
  const title = country === snapshot.default_country ? snapshot.default_country_label : `${series?.country_name ?? country} (not Malaysia)`
  const months = new Set(points.map(p => p.month))
  // Numbered markers on the chart, named in a list below it (close events would overprint).
  const events = snapshot.events.filter(e => months.has(e.month))

  return (
    <div className="rounded-lg border border-hairline bg-surface p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="font-semibold text-ink">AI share of job postings · {title}</div>
          {latest && <div className="text-sm text-graphite tabular-nums">{latest.share_pct.toFixed(1)}% of postings mentioned AI in {latest.month}</div>}
        </div>
        <span className="text-xs text-graphite">{snapshot.attribution}</span>
      </div>

      <div role="radiogroup" aria-label="Country" className="mt-4 flex flex-wrap gap-1.5">
        {snapshot.countries.map(c => {
          const name = snapshot.series.find(s => s.country === c)?.country_name ?? c
          return (
            <button
              key={c} role="radio" aria-checked={country === c} onClick={() => setCountry(c)}
              className={`rounded-full px-3 py-1 text-xs transition-colors duration-200 ${country === c ? 'bg-action-tint text-action-ink font-medium' : 'border border-hairline-strong text-graphite hover:bg-linen'}`}
            >
              {name}
            </button>
          )
        })}
      </div>

      <div className="mt-4 h-60 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 16, right: 12, bottom: 0, left: -16 }}>
            <CartesianGrid vertical={false} stroke={CHART.grid} />
            <XAxis dataKey="month" tick={{ fill: CHART.axis, fontSize: 11 }} tickLine={false} axisLine={{ stroke: CHART.grid }} minTickGap={36} />
            <YAxis tick={{ fill: CHART.axis, fontSize: 11 }} tickLine={false} axisLine={false} width={44} unit="%" />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid rgba(0,0,0,0.08)', fontSize: 12 }}
              formatter={value => [`${Number(value).toFixed(2)}% of postings`, 'AI share']}
            />
            {events.map((e, i) => (
              <ReferenceLine
                key={e.month} x={e.month} stroke={CHART.event}
                label={{ value: String(i + 1), position: 'top', fill: CHART.axis, fontSize: 11 }}
              />
            ))}
            <Line type="monotone" dataKey="share_pct" name="AI share" stroke={CHART.index} strokeWidth={2} dot={false} activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
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
      <Provenance meta={snapshot} extra={snapshot.covers_malaysia ? undefined : 'Shown for context; this is not Malaysian data.'} />
    </div>
  )
}
