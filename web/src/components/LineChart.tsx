import type { Point } from '../types'

export type Series = { label: string; color: string; points: Point[] }

const WIDTH = 640
const HEIGHT = 260
const PAD = { left: 44, right: 16, top: 16, bottom: 28 }
const Y_TICKS = 4

/** A small multi-series line chart for yearly or quarterly values (no library needed). */
export function LineChart({ series, unit, dark = true }: { series: Series[]; unit: string; dark?: boolean }) {
  const periods = [...new Set(series.flatMap((s) => s.points.map((p) => p.period)))].sort()
  const values = series.flatMap((s) => s.points.map((p) => p.value))
  if (periods.length < 2 || values.length === 0) return null
  const lo = Math.floor(Math.min(...values))
  const hi = Math.ceil(Math.max(...values))
  const x = (period: string) =>
    PAD.left + ((WIDTH - PAD.left - PAD.right) * periods.indexOf(period)) / (periods.length - 1)
  const y = (value: number) => PAD.top + ((HEIGHT - PAD.top - PAD.bottom) * (hi - value)) / (hi - lo || 1)
  const grid = dark ? '#2f3037' : '#eeeef0'
  const label = dark ? '#9394a1' : '#747686'
  const ticks = Array.from({ length: Y_TICKS + 1 }, (_, i) => lo + ((hi - lo) * i) / Y_TICKS)
  const everyNth = Math.ceil(periods.length / 8)
  const summary = series
    .map((s) => `${s.label}: ${s.points[0]?.value.toFixed(2)} to ${s.points.at(-1)?.value.toFixed(2)} ${unit}`)
    .join('; ')

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={summary} className="h-auto w-full">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(t)} y2={y(t)} stroke={grid} />
          <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill={label} fontFamily="Geist Mono, monospace">
            {t.toFixed(0)}
          </text>
        </g>
      ))}
      {periods.map((p, i) =>
        i % everyNth === 0 || i === periods.length - 1 ? (
          <text key={p} x={x(p)} y={HEIGHT - 8} textAnchor="middle" fontSize="11" fill={label} fontFamily="Geist Mono, monospace">
            {p}
          </text>
        ) : null,
      )}
      {series.map((s) => (
        <g key={s.label}>
          <polyline
            points={s.points.map((p) => `${x(p.period)},${y(p.value)}`).join(' ')}
            fill="none"
            stroke={s.color}
            strokeWidth="2.25"
            strokeLinejoin="round"
          />
          {s.points.length > 0 && (
            <circle cx={x(s.points.at(-1)!.period)} cy={y(s.points.at(-1)!.value)} r="3.5" fill={s.color} />
          )}
        </g>
      ))}
    </svg>
  )
}

export function Sparkline({ points, color }: { points: Point[]; color: string }) {
  if (points.length < 2) return null
  const vals = points.map((p) => p.value)
  const lo = Math.min(...vals)
  const hi = Math.max(...vals)
  const path = points
    .map((p, i) => `${3 + (58 * i) / (points.length - 1)},${17 - (14 * (p.value - lo)) / (hi - lo || 1)}`)
    .join(' ')
  return (
    <svg width="64" height="20" viewBox="0 0 64 20" aria-hidden="true">
      <polyline points={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
