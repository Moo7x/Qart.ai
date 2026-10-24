import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Point } from '../types'

// Chart palette: the dataviz reference categorical order (validated for colour-vision
// deficiency on light surfaces). A series keeps its slot for as long as it is shown; more than
// eight series are never coloured, they become small multiples instead.
export const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
const INK = '#131316'
const MUTED = '#5e5f6e'
const GRID = '#e4e6ec'
const AXIS_FONT = { fontSize: 11, fill: MUTED, fontFamily: 'Geist Mono, ui-monospace, monospace' }

export type ChartSeries = { label: string; points: Point[] }

function fmt(value: number, unit: string): string {
  return `${value.toFixed(value >= 10 ? 1 : 2)}${unit.startsWith('%') ? '%' : ` ${unit}`}`
}

type TipProps = { active?: boolean; label?: string | number; payload?: { name?: string; value?: number | string; color?: string }[] }

function Tip({ active, label, payload, unit, source }: TipProps & { unit: string; source: string }) {
  if (!active || !payload?.length) return null
  const rows = payload.filter((p) => typeof p.value === 'number')
  return (
    <div className="border border-line bg-paper px-3 py-2 text-[12px] shadow-sm" style={{ color: INK }}>
      <div className="font-mono text-[11px] text-graphite">{label}</div>
      {rows.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span aria-hidden="true" className="inline-block h-0.5 w-3" style={{ background: p.color }} />
          <span className="min-w-0 flex-1">{p.name}</span>
          <span className="font-mono font-semibold">{fmt(p.value as number, unit)}</span>
        </div>
      ))}
      <div className="mt-1 text-[10px] text-graphite">Observed · {source}</div>
    </div>
  )
}

// Rows keyed by period; a missing value stays missing (the line breaks), it is never zero.
function rows(series: ChartSeries[]): Record<string, string | number | null>[] {
  const periods = [...new Set(series.flatMap((s) => s.points.map((p) => p.period)))].sort()
  return periods.map((period) => {
    const row: Record<string, string | number | null> = { period }
    for (const s of series) row[s.label] = s.points.find((p) => p.period === period)?.value ?? null
    return row
  })
}

/** Several series on one y-axis, with a crosshair tooltip, legend and axis units (≤ 8 series). */
export function TimeSeriesChart({ series, unit, axis, source, height = 260 }: { series: ChartSeries[]; unit: string; axis: string; source: string; height?: number }) {
  const shown = series.slice(0, SERIES.length)
  const data = rows(shown)
  if (data.length < 2) return null
  const summary = shown.map((s) => `${s.label}: ${s.points[0]?.value.toFixed(2)} to ${s.points.at(-1)?.value.toFixed(2)} ${unit}`).join('; ')
  return (
    <figure className="m-0" aria-label={summary}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="period" tick={AXIS_FONT} tickLine={false} axisLine={{ stroke: GRID }} minTickGap={24} />
          <YAxis
            tick={AXIS_FONT}
            tickLine={false}
            axisLine={false}
            width={48}
            domain={['auto', 'auto']}
            label={{ value: axis, angle: -90, position: 'insideLeft', offset: 10, style: { ...AXIS_FONT, textAnchor: 'middle' } }}
          />
          <Tooltip content={<Tip unit={unit} source={source} />} cursor={{ stroke: MUTED, strokeDasharray: '3 3' }} />
          {shown.length > 1 && <Legend verticalAlign="bottom" align="left" iconType="plainline" wrapperStyle={{ fontSize: 12, color: INK, paddingTop: 6 }} />}
          {shown.map((s, i) => (
            <Line key={s.label} type="linear" dataKey={s.label} name={s.label} stroke={SERIES[i]} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: '#ffffff' }} connectNulls={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </figure>
  )
}

/** One small chart per series, each with its own y-axis (stated), for more series than colours. */
export function SmallMultiples({ series, unit, source }: { series: (ChartSeries & { note?: string })[]; unit: string; source: string }) {
  return (
    <div className="grid gap-x-6 gap-y-5 sm:grid-cols-2 xl:grid-cols-3">
      {series.map((s) => {
        const last = s.points.at(-1)
        return (
          <figure key={s.label} className="m-0 flex min-w-0 flex-col gap-1 border-t border-line pt-2">
            <figcaption className="flex items-baseline justify-between gap-2">
              <span className="min-w-0 truncate text-[13px] font-medium" title={s.label}>{s.label}</span>
              {last && <span className="font-mono text-[13px]">{fmt(last.value, unit)}<span className="text-[10px] text-graphite"> · {last.period}</span></span>}
            </figcaption>
            {s.note && <span className="font-mono text-[11px] text-graphite">{s.note}</span>}
            <ResponsiveContainer width="100%" height={110}>
              <LineChart data={s.points} margin={{ top: 6, right: 6, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="period" tick={AXIS_FONT} tickLine={false} axisLine={{ stroke: GRID }} interval="preserveStartEnd" minTickGap={40} />
                <YAxis tick={AXIS_FONT} tickLine={false} axisLine={false} width={36} domain={['auto', 'auto']} tickCount={3} />
                <Tooltip content={<Tip unit={unit} source={source} />} cursor={{ stroke: MUTED, strokeDasharray: '3 3' }} />
                <Line type="linear" dataKey="value" name={s.label} stroke={SERIES[0]} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: '#ffffff' }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </figure>
        )
      })}
    </div>
  )
}
