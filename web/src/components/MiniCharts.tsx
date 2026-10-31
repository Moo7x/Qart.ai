import { useId, useState, type ReactNode } from 'react'
import { Legend, ViewSwitch } from './atoms'

// Small charts in the redesign's dashboard style. Each has one axis, says in words what the
// colours mean, and the larger ones switch to a table (docs/PHASE2_PLAN.md §10 rules).

/** A tiny trend line for an observed series; the value it ends on is always written beside it. */
export function Sparkline({ points, width = 72, height = 24, label }: { points: { period: string; value: number }[]; width?: number; height?: number; label: string }) {
  if (points.length < 2) return null
  const values = points.map((p) => p.value)
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const span = hi - lo || 1
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${((i / (points.length - 1)) * (width - 4) + 2).toFixed(1)} ${(height - 2 - ((p.value - lo) / span) * (height - 4)).toFixed(1)}`)
    .join(' ')
  const up = values[values.length - 1] >= values[0]
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}: ${points[0].period} ${values[0]} to ${points[points.length - 1].period} ${values[values.length - 1]}`} className="flex-none">
      <path d={path} fill="none" stroke={up ? '#157a4a' : '#c2410c'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/** The change between the last two observations, with its sign spelled out. */
export function ChangePill({ points, unit }: { points: { value: number }[]; unit: string }) {
  if (points.length < 2) return null
  const delta = points[points.length - 1].value - points[points.length - 2].value
  const rounded = Math.round(delta * 100) / 100
  const text = `${rounded > 0 ? '+' : rounded < 0 ? '−' : '±'}${Math.abs(rounded)}${unit.startsWith('%') ? ' pt' : ''}`
  const tone = rounded > 0 ? 'bg-rising-bg text-rising' : rounded < 0 ? 'bg-weak-bg text-weak' : 'bg-mist text-muted'
  return <span className={`whitespace-nowrap rounded-md px-1.5 py-0.5 text-xs font-semibold ${tone}`}>{text}</span>
}

const BAND_COLOUR: Record<string, string> = { low: '#d1495b', fair: '#e9a23b', good: '#9bbf3a', strong: '#2e9e5b' }

/** The fit as a half dial split into the four bands (an assumption), with a marker at the fit. */
export function FitGauge({ fit, band, thresholds, caption, children }: { fit: number; band: string; thresholds: Record<string, number>; caption: string; children?: ReactNode }) {
  const cuts = [0, thresholds.fair ?? 35, thresholds.good ?? 55, thresholds.strong ?? 75, 100]
  const names = ['low', 'fair', 'good', 'strong']
  const R = 80
  const at = (v: number, r = R) => {
    const a = Math.PI + (v / 100) * Math.PI
    return [100 + r * Math.cos(a), 100 + r * Math.sin(a)]
  }
  const arc = (from: number, to: number) => {
    const [x1, y1] = at(from + 1)
    const [x2, y2] = at(to - 1)
    return `M${x1.toFixed(1)} ${y1.toFixed(1)} A${R} ${R} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`
  }
  const [mx, my] = at(Math.min(Math.max(fit, 1), 99))
  return (
    <div className="flex flex-col items-center gap-1 text-center">
      <svg viewBox="0 0 200 118" className="w-full max-w-[240px]" role="img" aria-label={`Fit ${Math.round(fit)} out of 100, ${band} band. Bands: low below ${cuts[1]}, fair from ${cuts[1]}, good from ${cuts[2]}, strong from ${cuts[3]}.`}>
        {names.map((n, i) => <path key={n} d={arc(cuts[i], cuts[i + 1])} fill="none" stroke={BAND_COLOUR[n]} strokeWidth="12" strokeLinecap="round" opacity={n === band ? 1 : 0.35} />)}
        <circle cx={mx} cy={my} r="9" fill="#fff" stroke="#0b0f1a" strokeWidth="3" />
        <text x="100" y="98" textAnchor="middle" fontSize="40" fontWeight="600" fill="#0b0f1a">{Math.round(fit)}</text>
      </svg>
      <span className="text-sm font-semibold">Your fit is <span className="capitalize">{band}</span></span>
      <span className="text-xs text-muted">{caption}</span>
      {children}
    </div>
  )
}

export type LevelRow = { skill: string; name: string; you: number | null; needs: number; essential: boolean }

/** Your claimed level against the level the role needs, one pair of bars per skill (0–5). */
export function LevelBars({ rows, title }: { rows: LevelRow[]; title: string }) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  const id = useId()
  const H = 140
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={id} className="q-h3 text-[17px]">{title}</h3>
        <ViewSwitch value={view} onChange={setView} />
      </div>
      {view === 'chart' ? (
        <>
          <div className="flex gap-2">
            <div aria-hidden="true" className="flex flex-col justify-between pb-6 text-right text-[11px] text-muted-2" style={{ height: H + 24 }}>
              {[5, 4, 3, 2, 1, 0].map((l) => <span key={l}>{l}</span>)}
            </div>
            <div role="img" aria-label={`${title}: ${rows.map((r) => `${r.name} you ${r.you ?? 'not rated'}, needs ${r.needs}`).join('; ')}`} className="flex min-w-0 flex-1 items-end gap-2 overflow-x-auto border-b border-[#e5e5e5]">
              {rows.map((r) => (
                <div key={r.skill} className="flex min-w-[44px] flex-1 flex-col items-center gap-1">
                  <div className="relative w-full max-w-[34px]" style={{ height: H }}>
                    <span className="absolute inset-x-0 bottom-0 rounded-t-lg bg-[#e9e4ff]" style={{ height: `${(r.needs / 5) * 100}%` }} />
                    <span className="m-grow absolute inset-x-[5px] bottom-0 rounded-t-md bg-gradient-to-t from-[#4b2bd1] to-[#8f77ff]" style={{ height: `${((r.you ?? 0) / 5) * 100}%`, transformOrigin: '50% 100%' }} />
                  </div>
                  <span className="line-clamp-2 h-6 w-full text-center text-[10px] leading-tight text-muted" title={r.name}>{r.name}</span>
                </div>
              ))}
            </div>
          </div>
          <Legend items={[{ swatch: '#6c47ff', text: 'Your level (claim)' }, { swatch: '#e9e4ff', text: 'Level the role needs' }]} />
        </>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[320px] border-collapse text-[13px]">
            <caption className="pb-1.5 text-left text-xs text-muted">{title}</caption>
            <thead><tr className="text-left text-xs text-muted"><th className="py-1.5 font-semibold">Skill</th><th className="font-semibold">You (claim)</th><th className="font-semibold">Needs</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.skill} className="border-t border-[#eee]"><td className="py-1.5">{r.name}{r.essential ? ' · essential' : ''}</td><td>{r.you ?? 'not rated'}</td><td>{r.needs}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
