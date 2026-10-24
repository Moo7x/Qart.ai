import { useState } from 'react'
import { useT } from '../i18n'
import { useApi } from '../api'
import { LineChart, type Series } from '../components/LineChart'
import { Loading, Problem } from '../components/ui'
import type { TrendsResponse } from '../types'

const COLOURS = ['#9d86ff', '#5de3ff', '#ffa86b', '#3fd1a0', '#ff7aa8', '#c4c5cf', '#ffd166', '#7aa2ff', '#a0e57a']
const KIND = {
  observed: ['Observed', 'bg-observed-bg text-observed'],
  assumption: ['Assumption', 'bg-mist text-graphite'],
  estimate: ['Estimate', 'bg-estimate-bg text-estimate'],
} as const

function Kind({ kind }: { kind: keyof typeof KIND }) {
  return <span className={`tag ${KIND[kind][1]}`}>{KIND[kind][0]}</span>
}

function Legend({ series, dark }: { series: Series[]; dark: boolean }) {
  return (
    <div className={`flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] ${dark ? 'text-stone' : 'text-graphite'}`}>
      {series.map((s) => (
        <span key={s.label} className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-0.5 w-4" style={{ background: s.color }} />
          {s.label}
        </span>
      ))}
    </div>
  )
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
  const [span, setSpan] = useState<'long' | 'recent'>('long')
  const data = view.data
  const lines: Series[] = (data?.employment ?? []).map((g, i) => ({ label: g.title, color: COLOURS[i % COLOURS.length], points: g.points }))
  const adLines: Series[] = data
    ? [
        { label: 'Professionals (share of all ads)', color: '#6c47ff', points: data.job_ads.professionals },
        ...data.job_ads.named.slice(0, 4).map((n, i) => ({ label: n.entity, color: COLOURS[(i + 1) % COLOURS.length], points: n.points })),
      ]
    : []
  const first = data?.employment[0]?.first
  const last = data?.employment[0]?.last
  const change = (g: TrendsResponse['employment'][number]) => (span === 'long' ? g.change_long : g.change_recent)
  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
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
          <section className="card-dark flex flex-col gap-3 p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="h2">Share of Malaysian employees by occupation group</h2>
              <Kind kind="observed" />
            </div>
            <LineChart series={lines} unit="% of employees" />
            <Legend series={lines} dark />
            <p className="m-0 text-xs text-stone">DOSM, wages by occupation (OpenDOSM), {first}–{last}. 2010 is left out: the classification changed in 2011.</p>
          </section>

          <div className="flex flex-wrap items-start gap-5">
            <section className="card-light flex min-w-0 flex-[1_1_380px] flex-col gap-3 px-6 py-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="h2">Which groups rose or fell</h2>
                <Kind kind="observed" />
              </div>
              <div className="flex gap-2" role="group" aria-label="Time window">
                <button type="button" className={`btn ${span === 'long' ? 'btn-v' : ''}`} onClick={() => setSpan('long')}>{first}–{last}</button>
                <button type="button" className={`btn ${span === 'recent' ? 'btn-v' : ''}`} onClick={() => setSpan('recent')}>{data.recent_from}–{last}</button>
              </div>
              <Diverging
                unit=" pts"
                rows={[...data.employment].sort((a, b) => (change(b) ?? 0) - (change(a) ?? 0)).map((g) => ({ label: g.title, value: change(g) }))}
              />
              <p className="m-0 text-xs text-graphite">
                Change in share of employees, percentage points. The two windows can disagree (clerical work fell over the long run but rose recently), so both are shown; the rolling backtest on Live intelligence says no trend can be projected yet.
              </p>
            </section>

            <section className="card-light flex min-w-0 flex-[1_1_380px] flex-col gap-3 px-6 py-5">
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
          </div>

          <section className="card-light flex flex-col gap-3 px-6 py-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="h2">Online job ads by quarter</h2>
              <Kind kind="observed" />
            </div>
            <LineChart series={adLines} unit="% of online job offerings" dark={false} />
            <Legend series={adLines} dark={false} />
            <p className="m-0 text-xs text-graphite">
              DOSM Job Market Insights, from major private platforms (not all vacancies). Named occupations appear only in quarters where DOSM lists them among the top ones, so gaps are not zero.
              {data.job_ads.breaks.length > 0 && <> Total ads jumped in {data.job_ads.breaks.join(', ')}: a possible change in platform coverage, so compare within each side of it.</>}
            </p>
          </section>

          <section className="card-light flex flex-col gap-3 px-6 py-5">
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
