import { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatWhen, useApi } from '../api'
import { EvidenceDrawer } from '../components/EvidenceDrawer'
import { LineChart, Sparkline, type Series } from '../components/LineChart'
import { DIRECTION_LABEL, Empty, Loading, Problem } from '../components/ui'
import type { Direction, Signal, SignalsResponse, SourceStatus } from '../types'

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

export function Overview() {
  const signals = useApi<SignalsResponse>('/api/signals')
  const sources = useApi<SourceStatus[]>('/api/sources')
  const [selected, setSelected] = useState<Signal | null>(null)

  const all = signals.data?.signals ?? []
  const chartSeries: Series[] = all
    .filter((s) => s.id in GROUP_COLOURS)
    .map((s) => ({ ...GROUP_COLOURS[s.id], points: s.points }))
  const listed = all.filter((s) => s.family !== 'ai_task_use')
  const aiUse = all.filter((s) => s.family === 'ai_task_use')

  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">Overview · GBS finance &amp; accounting · Malaysia</span>
        <h1 className="h1">What the evidence shows for your field</h1>
        <p className="m-0 max-w-[660px] text-graphite">
          Every line comes from a registered public source and shows its date. Labels follow declared rules: a trend
          needs enough comparable data, and expert views are kept apart from measured data.
        </p>
      </header>

      {signals.loading && <Loading what="the evidence" />}
      {signals.error && <Problem what="the evidence" message={signals.error} onRetry={signals.reload} />}
      {signals.data && all.length === 0 && (
        <div className="card-light">
          <Empty>
            No evidence collected yet. The first pipeline run starts automatically on a new deployment; see{' '}
            <Link to="/live">Live intelligence</Link> for its progress.
          </Empty>
        </div>
      )}

      {all.length > 0 && (
        <div className="flex flex-wrap items-stretch gap-5">
          <section className="card-dark flex min-w-0 flex-[3_1_520px] flex-col gap-3.5 bg-[radial-gradient(70%_80%_at_85%_0%,rgba(108,71,255,0.18),rgba(33,33,38,0)_70%)] p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="h2">Share of Malaysian employees by occupation group</h2>
              <span className="font-mono text-xs text-stone">% of employees · 2011–2025</span>
            </div>
            <LineChart series={chartSeries} unit="% of employees" />
            <div className="flex flex-wrap gap-4 font-mono text-xs text-stone">
              {chartSeries.map((s) => (
                <span key={s.label} className="flex items-center gap-1.5">
                  <span aria-hidden="true" className="inline-block h-0.5 w-5" style={{ background: s.color }} />
                  {s.label}
                </span>
              ))}
            </div>
            <p className="m-0 text-xs text-stone">
              Observed history from OpenDOSM; 2010 is left out because the occupation classification changed in 2011.
              Finance clerks sit in clerical support, accountants in professionals.
            </p>
            <div className="flex flex-col gap-1.5 border-t border-surface pt-3">
              <span className="font-mono text-[11px] tracking-widest text-cyan">FEEDING THIS PAGE</span>
              <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 font-mono text-xs">
                {(sources.data ?? []).map((s) => (
                  <span key={s.id} className="contents">
                    <span className="text-[#c4c5cf]">{s.name}</span>
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
    </main>
  )
}
