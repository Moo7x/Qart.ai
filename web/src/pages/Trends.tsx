import { useT } from '../i18n'
import { useApi } from '../api'
import { SmallMultiples } from '../components/Charts'
import { Loading, Problem } from '../components/ui'
import type { TrendsResponse } from '../types'

const KIND = {
  observed: ['Observed', 'bg-observed-bg text-observed'],
  assumption: ['Assumption', 'bg-mist text-graphite'],
  estimate: ['Estimate', 'bg-estimate-bg text-estimate'],
} as const

function Kind({ kind }: { kind: keyof typeof KIND }) {
  return <span className={`tag ${KIND[kind][1]}`}>{KIND[kind][0]}</span>
}

// Horizontal bars around zero: rising to the right in green, declining to the left in amber.
function Diverging({ rows, unit }: { rows: { label: string; value: number | null; hint?: string }[]; unit: string }) {
  const max = Math.max(...rows.map((r) => Math.abs(r.value ?? 0)), 0.01)
  return (
    <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-[12px]">
      {rows.map((r) => {
        const v = r.value ?? 0
        const width = `${(50 * Math.abs(v)) / max}%`
        return (
          <li key={r.label} className="grid grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)_64px] items-center gap-2" title={r.hint}>
            <span className="truncate">{r.label}</span>
            <span className="relative h-3 rounded bg-mist">
              <span className="absolute inset-y-0 left-1/2 w-px bg-hairline" />
              {r.value !== null && (
                <span className={`absolute inset-y-0 rounded ${v >= 0 ? 'left-1/2 bg-[#12a372]' : 'right-1/2 bg-[#e0892f]'}`} style={{ width }} />
              )}
            </span>
            <span className="text-right font-mono">{r.value === null ? '—' : `${v > 0 ? '+' : ''}${v}${unit}`}</span>
          </li>
        )
      })}
    </ul>
  )
}

export function Trends() {
  const { t } = useT()
  const view = useApi<TrendsResponse>('/api/trends')
  const data = view.data
  // Biggest groups first; each panel states its own change so differing y-axes never mislead.
  const groups = [...(data?.employment ?? [])]
    .sort((a, b) => (b.points.at(-1)?.value ?? 0) - (a.points.at(-1)?.value ?? 0))
    .map((g) => ({ label: g.title, points: g.points, note: `${g.change_long > 0 ? '+' : ''}${g.change_long} pts since ${g.first}` }))
  const first = data?.employment[0]?.first
  const last = data?.employment[0]?.last
  return (
    <main className="page">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">Trends · rising and declining</span>
        <h1 className="h1">{t('What is growing, what is shrinking')}</h1>
        <p className="m-0 max-w-[680px] text-graphite">
          Every chart says what kind of number it shows: observed (measured by the source), assumption (our declared scenario rule) or estimate (a model of potential). History is not a forecast.
        </p>
      </header>
      {view.loading && <Loading what="the trends" />}
      {view.error && <Problem what="the trends" message={view.error} onRetry={view.reload} />}
      {data && (
        <>
          <section className="section">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="h2">Share of Malaysian employees by occupation group, {first}–{last}</h2>
              <Kind kind="observed" />
            </div>
            <p className="m-0 max-w-[760px] text-[14px] leading-relaxed"><span className="font-semibold">What this shows:</span> out of every 100 employees in Malaysia, how many work in each type of job, year by year since 2011 (official DOSM figures). A rising line means that type of work is a growing part of the workforce; a falling line, a shrinking part. Finance clerks are counted under clerical support, accountants under professionals.</p>
            <SmallMultiples series={groups} unit="% of employees" source={`DOSM via OpenDOSM, ${first}–${last}`} />
            <p className="m-0 text-xs text-graphite">
              % of all employees, yearly. Each panel has its own vertical scale so small groups stay readable; compare groups by the change under each title. Hover a line for exact values. DOSM, wages by occupation (OpenDOSM); 2010 is left out because the classification changed in 2011.
            </p>
          </section>

            <section className="section">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="h2">Skills gaining or losing emphasis</h2>
                <Kind kind="assumption" />
              </div>
              <Diverging
                unit="%"
                rows={data.skills.filter((s) => s.change !== 0).map((s) => ({ label: s.name, value: s.change, hint: `${s.ai_role} skill · ${s.basis.join(', ')}-level AI use · in ${s.roles} role(s)` }))}
              />
              <p className="m-0 text-xs text-graphite">
                Weight change under fast adoption, averaged over the destination roles that need the skill: the declared scenario rule applied to observed AI use (task-level where published). Essentials and neutral skills do not shift. Not a forecast.
              </p>
            </section>

          <section className="section">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="h2">How much of each occupation&rsquo;s tasks GenAI could do</h2>
              <Kind kind="estimate" />
            </div>
            <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-[12px]">
              {data.exposure.map((e) => (
                <li key={e.isco} className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,1.5fr)_auto] items-center gap-2">
                  <span className="truncate">{e.title} <span className="text-ash">· {e.isco}</span></span>
                  <span className="h-3 rounded bg-mist"><span className="block h-3 rounded bg-[#8a2a77]" style={{ width: `${100 * (e.mean ?? 0)}%` }} /></span>
                  <span className="font-mono">{e.mean?.toFixed(2)} · {e.gradient}</span>
                </li>
              ))}
            </ul>
            <p className="m-0 text-xs text-graphite">ILO Working Paper 140 (2025), mean task score 0–1. Technical potential, not job loss or adoption in Malaysia.</p>
          </section>
        </>
      )}
    </main>
  )
}
