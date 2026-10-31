import { useState } from 'react'
import { formatWhen, useApi } from '../api'
import { useJourney } from '../state'
import type { TrendsResponse } from '../types'
import type { SeriesForecast } from '../typesAgents'
import { type Pane, Windows } from './Windows'
import { KindLabel } from './Why'

// One chart for stage 2 (docs/PHASE2_PLAN.md A2): what is rising and declining, as skills or as
// job groups with the roles in them. One axis per mode, rising to the right, declining to the left.
// Skills: % weight change under the chosen scenario (an assumption applied to observed AI use).
// Roles: percentage-point change in a group's share of employees, observed over the recent window
// (bar) and forecast two years ahead with its backtest interval (dot and whisker, an estimate).

const MODEL_NAMES: Record<string, string> = {
  naive: 'keep the last value',
  drift: 'average change so far',
  linear: 'straight-line trend',
  damped: 'damped trend',
  smoothing: 'exponential smoothing',
  theta: 'Theta method',
  gbr: 'gradient boosting across all groups (machine learning)',
}

type Mode = 'skills' | 'roles'

type Row = {
  id: string
  label: string
  sub?: string
  value: number // the bar
  forecast?: { point: number; low: number | null; high: number | null }
  detail: Pane
}

const RISE = 'var(--color-rising)'
const FALL = 'var(--color-weak)'
const FORECAST = 'var(--color-estimate)'

function signed(v: number, unit: string): string {
  return `${v > 0 ? '+' : ''}${v.toFixed(unit === '%' ? 1 : 2)}${unit === '%' ? '%' : ' pp'}`
}

function Bar({ row, max, unit }: { row: Row; max: number; unit: string }) {
  const pos = (v: number) => `${50 + (50 * v) / max}%`
  const width = `${(50 * Math.abs(row.value)) / max}%`
  const f = row.forecast
  return (
    <span className="relative block h-5" aria-hidden="true">
      <span className="absolute inset-y-0 left-1/2 w-px bg-[#bdbfca]" />
      <span
        className="absolute top-1 h-3 rounded-[3px]"
        style={{ width, background: row.value >= 0 ? RISE : FALL, ...(row.value >= 0 ? { left: '50%' } : { right: '50%' }) }}
      />
      {f && (
        <>
          {f.low !== null && f.high !== null && (
            <span className="absolute top-[9px] h-[2px]" style={{ left: pos(Math.min(f.low, f.high)), width: `${(50 * Math.abs(f.high - f.low)) / max}%`, background: FORECAST }} />
          )}
          <span className="absolute top-[5px] h-[10px] w-[10px] -translate-x-1/2 rounded-full border-2 border-white" style={{ left: pos(f.point), background: FORECAST }} title={`forecast ${signed(f.point, unit)}`} />
        </>
      )}
    </span>
  )
}

function skillRows(data: TrendsResponse, scenario: 'moderate' | 'fast'): Row[] {
  return data.skills_by_scenario[scenario]
    .filter((s) => s.change !== 0)
    .sort((a, b) => b.change - a.change)
    .map((s) => ({
      id: s.skill,
      label: s.name,
      value: s.change,
      detail: {
        key: s.skill,
        title: s.name,
        hint: 'Assumption applied to observed AI use',
        body: (
          <div className="flex flex-col gap-2">
            <p className="m-0">
              Weight change {signed(s.change, '%')} under {scenario} AI adoption, averaged over the {s.roles} destination role(s) that need this skill. It is a {s.ai_role === 'routine' ? 'routine skill, so it loses weight' : 'skill that complements AI, so it gains weight'} as automation-style AI use reaches its tasks.
            </p>
            <p className="m-0 text-graphite">AI use: {data.evidence_source}, {data.evidence_period} ({s.basis.join(' and ')}-level). Essentials and neutral skills never shift. Not a forecast of jobs.</p>
          </div>
        ),
      },
    }))
}

function groupRows(data: TrendsResponse, forecasts: SeriesForecast[]): Row[] {
  const roles = forecasts.filter((f) => f.kind === 'role_outlook')
  const byGroup = new Map(forecasts.filter((f) => f.kind === 'employment_share').map((f) => [f.series_id.split(':')[1], f]))
  return data.employment
    .filter((g) => g.change_recent !== null)
    .map((g) => {
      const f = byGroup.get(g.group)
      const last = f?.history.at(-1)?.value
      const horizon = f?.forecast.at(-1)
      const forecast = horizon && last !== undefined
        ? { point: horizon.point - last, low: horizon.low === null ? null : horizon.low - last, high: horizon.high === null ? null : horizon.high - last }
        : undefined
      const inGroup = roles.filter((r) => r.components?.group === g.group)
      const here = inGroup.map((r) => r.title)
      return {
        id: g.group,
        label: g.title,
        sub: here.length > 0 ? `Your roles here: ${here.join(', ')}` : undefined,
        value: g.change_recent ?? 0,
        forecast,
        detail: {
          key: g.group,
          title: g.title,
          hint: 'Observed history, estimated forecast',
          body: (
            <div className="flex flex-col gap-2">
              <p className="m-0"><KindLabel kind="observed" /> Share of all employees in Malaysia moved {signed(g.change_recent ?? 0, 'pp')} from {data.recent_from} to {g.last} (OpenDOSM, wages by occupation).</p>
              {f && horizon && forecast ? (
                <>
                  <p className="m-0"><KindLabel kind="estimate" /> Forecast for {horizon.period}: {horizon.point.toFixed(2)}% ({signed(forecast.point, 'pp')}){horizon.low !== null && horizon.high !== null ? `, likely between ${horizon.low.toFixed(2)}% and ${horizon.high.toFixed(2)}%` : ''}.</p>
                  <p className="m-0 text-graphite">
                    Model: {MODEL_NAMES[f.model ?? 'naive'] ?? f.model}. {f.backtest ? `In a backtest over ${f.backtest.origins} past years its error was ${Math.round(100 * f.backtest.ratio)}% of keeping the last value.` : ''} {f.note}
                  </p>
                  <p className="m-0 text-graphite">Source: {f.source}{f.fetched_at ? `, fetched ${formatWhen(f.fetched_at)}` : ''}. The interval comes from this model's own past errors.</p>
                </>
              ) : (
                <p className="m-0 text-graphite">{f?.note || 'No forecast for this group.'}</p>
              )}
              {here.length > 0 && <p className="m-0">Your destination roles in this group: {here.join(', ')}. The forecast is for the whole group, not for these roles.</p>}
              {inGroup.map((r) => {
                const items = Array.isArray(r.components?.evidence) ? r.components.evidence : []
                if (items.length === 0) return null
                return (
                  <div key={r.series_id} className="flex flex-col gap-1 border-t border-line pt-2">
                    <span className="text-[13px] font-semibold">{r.title}: evidence about this occupation</span>
                    <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-[12px]">
                      {items.map((e) => (
                        <li key={e.text}>{e.kind === 'observed' ? <KindLabel kind="observed" /> : <span className="tag bg-mist text-graphite">Expert view</span>} {e.text} <span className="text-graphite">({e.source})</span></li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </div>
          ),
        },
      }
    })
    .sort((a, b) => b.value - a.value)
}

export function TrendsChart() {
  const { scenario } = useJourney()
  const [mode, setMode] = useState<Mode>('skills')
  const [open, setOpen] = useState<Pane | null>(null)
  const trends = useApi<TrendsResponse>('/api/trends')
  const forecasts = useApi<SeriesForecast[]>('/api/forecast')
  const data = trends.data
  if (!data) return <span role="status" className="cap">Loading the trends…</span>
  const rows = mode === 'skills' ? skillRows(data, scenario) : groupRows(data, forecasts.data ?? [])
  const unit = mode === 'skills' ? '%' : 'pp'
  const max = Math.max(0.01, ...rows.flatMap((r) => [Math.abs(r.value), Math.abs(r.forecast?.low ?? 0), Math.abs(r.forecast?.high ?? 0), Math.abs(r.forecast?.point ?? 0)]))
  const seg = (active: boolean) => `min-h-[36px] cursor-pointer rounded border-0 px-3 text-[13px] ${active ? 'bg-void font-medium text-white' : 'bg-transparent text-graphite'}`
  return (
    <section className="section" aria-label="What is rising and declining">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="group" aria-label="Show" className="card-light flex rounded-md p-[3px]">
          <button type="button" aria-pressed={mode === 'skills'} className={seg(mode === 'skills')} onClick={() => setMode('skills')}>Skills</button>
          <button type="button" aria-pressed={mode === 'roles'} className={seg(mode === 'roles')} onClick={() => setMode('roles')}>Roles and job groups</button>
        </div>
        <div className="flex items-center gap-2">
          {mode === 'skills' ? <KindLabel kind="assumption" /> : <><KindLabel kind="observed" /><KindLabel kind="estimate" /></>}
        </div>
      </div>
      <p className="m-0 text-[13px] text-graphite">
        {mode === 'skills'
          ? `How much each skill's weight in the destination roles moves under ${scenario} AI adoption. Select a skill for why.`
          : `Bars: observed change in each group's share of employees, ${data.recent_from}–${data.employment[0]?.last ?? ''}. Dots: forecast change over the next two years, with the likely range. Select a group for the model and its test.`}
      </p>
      {mode === 'roles' && (
        <div className="flex flex-wrap gap-4 font-mono text-[11px] text-graphite">
          <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-2.5 w-4 rounded-[2px]" style={{ background: RISE }} />rising (observed)</span>
          <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-2.5 w-4 rounded-[2px]" style={{ background: FALL }} />declining (observed)</span>
          <span className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: FORECAST }} />forecast and range (estimate)</span>
        </div>
      )}
      <ul className="m-0 flex list-none flex-col p-0">
        {rows.map((r) => (
          <li key={r.id} className="border-t border-line first:border-t-0">
            <button
              type="button"
              onClick={() => setOpen(r.detail)}
              className="grid min-h-[44px] w-full cursor-pointer grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_72px] items-center gap-3 border-0 bg-transparent px-1 py-1.5 text-left text-[13px] hover:bg-fog focus-visible:bg-fog"
              aria-label={`${r.label}: ${signed(r.value, unit)}${r.forecast ? `, forecast ${signed(r.forecast.point, unit)}` : ''}. Open details`}
            >
              <span className="min-w-0">{r.label}{r.sub && <span className="block text-[11px] text-graphite">{r.sub}</span>}</span>
              <Bar row={r} max={max} unit={unit} />
              <span className={`text-right font-mono ${r.value >= 0 ? 'text-rising' : 'text-weak'}`}>{signed(r.value, unit)}</span>
            </button>
          </li>
        ))}
      </ul>
      {mode === 'roles' && forecasts.loading && <span role="status" className="cap">Loading the forecasts…</span>}
      {open && <Windows title={open.title} panes={[open]} onClose={() => setOpen(null)} />}
    </section>
  )
}
