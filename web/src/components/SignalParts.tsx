/** Shared pieces of the Future Skills Radar: label badge, provenance line, sparkline, colours. */
import { CircleDashed, ExternalLink, Minus, TrendingDown, TrendingUp, TriangleAlert, type LucideIcon } from 'lucide-react'
import type { SignalLabel, SignalSnapshotMeta } from '../types'
import { Tag, type Tone } from '../ui'

/**
 * Chart colours, mirroring the design tokens (SVG presentation attributes cannot read CSS
 * variables reliably). The three-series set action/coral/saffron passed the dataviz validator on
 * white (lightness, chroma, CVD ΔE ≥ 10, normal-vision ΔE 17.8). Saffron is under 3:1 contrast,
 * so every chart that uses it also has a legend and a data table.
 */
export const CHART = {
  index: '#0075de',
  short: '#f64932',
  long: '#e89d01',
  spark: '#615d59',
  grid: 'rgba(0, 0, 0, 0.08)',
  axis: '#615d59',
  event: 'rgba(0, 0, 0, 0.24)',
}

const LABEL_META: Record<SignalLabel, { text: string; tone: Tone; icon: LucideIcon }> = {
  rising: { text: 'Rising', tone: 'action', icon: TrendingUp },
  stable: { text: 'Stable', tone: 'linen', icon: Minus },
  cooling: { text: 'Cooling', tone: 'coral', icon: TrendingDown },
  insufficient_data: { text: 'Insufficient data', tone: 'outline', icon: CircleDashed },
}

/** Label with an icon and a word, so the state never depends on colour alone. */
export function SignalBadge({ label }: { label: SignalLabel }) {
  const m = LABEL_META[label]
  return <Tag tone={m.tone} icon={m.icon}>{m.text}</Tag>
}

export function formatChange(change: number | null): string {
  if (change === null) return '–'
  const pct = Math.round(change * 100)
  return `${pct > 0 ? '+' : pct < 0 ? '−' : ''}${Math.abs(pct)}%`
}

/** "Source: … (licence) · data to … · refreshed … · link", the caveats, and a stale badge. */
export function Provenance({ meta, extra }: { meta: Omit<SignalSnapshotMeta, 'source_url' | 'age_days'> & { source_url?: string | null }; extra?: string }) {
  return (
    <div className="mt-3 space-y-1 text-xs text-graphite">
      <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
        {meta.stale && <Tag tone="coral" icon={TriangleAlert}>Stale data</Tag>}
        <span>
          Source: {meta.source} ({meta.license}) · data to {meta.data_as_of} · refreshed {meta.fetched_at.slice(0, 10)}
          {meta.source_url?.startsWith('http') && (
            <>
              {' · '}
              <a href={meta.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-action-ink hover:underline">
                link <ExternalLink size={10} aria-hidden="true" />
              </a>
            </>
          )}
        </span>
      </p>
      <p>{[...meta.caveats, extra].filter(Boolean).join(' ')}</p>
    </div>
  )
}

const SPARK_W = 96
const SPARK_H = 28
const SPARK_PAD = 3

/** One-series trend line in the de-emphasis colour, latest point in the accent. */
export function Sparkline({ values, label }: { values: (number | null)[]; label: string }) {
  const pts = values.map((v, i) => [i, v] as const).filter((p): p is readonly [number, number] => p[1] !== null)
  if (pts.length < 2) return <span className="text-xs text-stone">–</span>
  const max = Math.max(...pts.map(p => p[1]))
  const min = Math.min(...pts.map(p => p[1]))
  const x = (i: number) => SPARK_PAD + (i / (values.length - 1)) * (SPARK_W - 2 * SPARK_PAD)
  const y = (v: number) => SPARK_H - SPARK_PAD - (max === min ? 0.5 : (v - min) / (max - min)) * (SPARK_H - 2 * SPARK_PAD)
  const d = pts.map(([i, v], k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const [li, lv] = pts[pts.length - 1]
  return (
    <svg width={SPARK_W} height={SPARK_H} viewBox={`0 0 ${SPARK_W} ${SPARK_H}`} role="img" aria-label={label}>
      <path d={d} fill="none" stroke={CHART.spark} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(li)} cy={y(lv)} r={3} fill={CHART.index} stroke="#fff" strokeWidth={1.5} />
    </svg>
  )
}
