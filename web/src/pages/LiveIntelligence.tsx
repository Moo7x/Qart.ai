import { History, Lock } from 'lucide-react'
import { useT } from '../i18n'
import { type FormEvent, useState } from 'react'
import { formatWhen, parseUtc, sendJSON, useApi } from '../api'
import { ChangeTest } from '../components/ChangeTest'
import { EvidenceDrawer } from '../components/EvidenceDrawer'
import { Sparkline } from '../components/LineChart'
import { PipelineDiagram, type StepId } from '../components/PipelineDiagram'
import { KindLabel } from '../components/Why'
import { Windows, type Pane } from '../components/Windows'
import { DIRECTION_LABEL, Empty, Loading, Problem } from '../components/ui'
import type { Direction, Run, Signal, SignalsResponse, SourceStatus } from '../types'
import type { SeriesForecast } from '../typesAgents'

const RUNS_POLL_MS = 5_000
const SECONDS_PER_MINUTE = 60

const STEP_TEXT: Record<StepId, [string, string]> = {
  schedule: ['SCHEDULE', 'A scheduled job runs the whole pipeline every day; an admin can also start it with Run now. A lock stops two runs overlapping, and every run is logged, including runs with no change.'],
  sources: ['REGISTERED SOURCES', 'Seven public sources. Click a source to see what it shows, its terms and its last run. A source that fails keeps its last good data.'],
  fetch: ['FETCH', 'Each source gets two attempts with a time limit. Releases already read are not downloaded again, so a quiet day costs a few requests.'],
  validate: ['VALIDATE', 'Release dates and quarters are checked; a count that is not stated stays missing, never zero; a jump in total job ads is treated as a coverage break.'],
  measure: ['MEASURE', 'Shares and changes between comparable periods, at the precision each source publishes, then the forecast backtest below.'],
  label: ['LABEL', 'Rising or weakening needs two independent sources, or one official series with enough comparable points; otherwise "not enough evidence yet".'],
  forecast: ['SCENARIOS', 'Moderate and fast AI adoption shift the weight of non-essential skills using observed AI use. They are estimates, not predictions. Essentials stay fixed.'],
  match: ['MATCH', 'Every destination role is scored against each person\'s claimed skills. New evidence produces a stored before-and-after comparison.'],
  notify: ['IN THE APP', 'When new evidence changes a person\'s scores or plan, What changed shows the before and after. The person accepts or declines.'],
}

function duration(run: Run): string {
  if (!run.finished_at) return '—'
  const seconds = (parseUtc(run.finished_at) - parseUtc(run.started_at)) / 1000
  return seconds >= SECONDS_PER_MINUTE ? `${Math.round(seconds / SECONDS_PER_MINUTE)} min` : `${Math.round(seconds)} s`
}

const RESULT_STYLE: Record<string, string> = {
  changed: 'bg-observed-bg text-observed',
  'no change': 'bg-mist text-graphite',
  partial: 'bg-weak-bg text-weak',
  failed: 'bg-weak-bg text-weak',
  'failed (interrupted)': 'bg-weak-bg text-weak',
  running: 'bg-[#e6fbff] text-[#0a6b7d]',
}

function RunNow({ onStarted }: { onStarted: () => void }) {
  const [open, setOpen] = useState(false)
  const [token, setToken] = useState('')
  const [message, setMessage] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    try {
      await sendJSON('/api/pipeline/run', { headers: { 'X-Admin-Token': token } })
      setMessage('Run started. Watch the pipeline above.')
      setOpen(false)
      onStarted()
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : String(reason))
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      {!open && (
        <button type="button" className="btn btn-v" onClick={() => setOpen(true)}>
          <Lock size={14} aria-hidden="true" />
          Run now · admin
        </button>
      )}
      {open && (
        <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="admin-token">Admin token</label>
          <input id="admin-token" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Admin token" className="min-h-[38px] rounded-md border border-hairline bg-fog px-3 font-mono text-sm" />
          <button type="submit" className="btn btn-v" disabled={!token}>Start run</button>
          <button type="button" className="btn" onClick={() => setOpen(false)}>Cancel</button>
        </form>
      )}
      {message && <span role="status" className="text-xs text-graphite">{message}</span>}
    </div>
  )
}

// Steps logged with a run that are not sources.
export const STEPS = ['trend_models', 'occupation_index', 'link_check', 'retention']
const TRIGGER: Record<string, string> = { schedule: 'Scheduled', manual: 'Run by admin', 'catch-up': 'Catch-up on start', admin: 'Run by admin' }

function RunCard({ run, names }: { run: Run; names: Record<string, string> }) {
  const collected = run.sources.filter((s) => !STEPS.includes(s.source_id))
  const ok = collected.filter((s) => s.status === 'ok').length
  const grew = collected.filter((s) => s.new > 0).sort((a, b) => b.new - a.new)
  const headline =
    run.status === 'running'
      ? 'Collecting now…'
      : run.new_observations > 0
        ? `${run.new_observations.toLocaleString()} new data points: ${grew.slice(0, 3).map((s) => `${names[s.source_id] ?? s.source_id} +${s.new.toLocaleString()}`).join(', ')}${grew.length > 3 ? '…' : ''}`
        : `${ok} of ${collected.length} sources checked: nothing new published since the last run`
  return (
    <li className="flex flex-col gap-2 border-t border-line py-3 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-semibold">{formatWhen(run.started_at)}</span>
        <span className="flex items-center gap-2 text-[12px] text-graphite">
          <span className="tag bg-mist text-graphite">{TRIGGER[run.trigger] ?? run.trigger}</span>
          {duration(run)}
          <span className={`tag ${RESULT_STYLE[run.status] ?? 'bg-mist text-graphite'}`}>{run.status}</span>
        </span>
      </div>
      <p className="m-0 text-[13px]">{headline}</p>
    </li>
  )
}

function sourcePane(s: SourceStatus): Pane {
  return {
    key: s.id,
    title: s.name,
    hint: `${s.publisher} · ${s.cadence}`,
    body: (
      <dl className="m-0 grid grid-cols-[110px_minmax(0,1fr)] gap-x-3 gap-y-2 text-[13px]">
        <dt className="cap">Shows</dt><dd className="m-0">{s.shows}</dd>
        <dt className="cap">Does not show</dt><dd className="m-0">{s.does_not_show}</dd>
        <dt className="cap">Stored rows</dt><dd className="m-0 font-mono">{s.observations.toLocaleString()}</dd>
        <dt className="cap">Last run</dt><dd className="m-0">{s.last_status ?? 'not run'}{s.last_fetched ? ` · fetched ${formatWhen(s.last_fetched)}` : ''}{s.last_status === 'failed' && s.serving_snapshot_from ? ` · showing the last good data, fetched ${formatWhen(s.serving_snapshot_from)}` : ''}</dd>
        {s.last_note && <><dt className="cap">Note</dt><dd className="m-0 text-graphite">{s.last_note}</dd></>}
        <dt className="cap">Terms</dt><dd className="m-0"><a href={s.terms_url} target="_blank" rel="noopener noreferrer">{s.terms}</a></dd>
        <dt className="cap">Open</dt><dd className="m-0 break-all"><a href={s.url} target="_blank" rel="noopener noreferrer">{s.url}</a></dd>
      </dl>
    ),
  }
}

// "Do our forecasts beat a simple guess?": for each job group, how much smaller the chosen model's
// past error was than just repeating last year's value. No bar: nothing beat it, so the forecast
// is last year's value.
function ForecastScore({ entries }: { entries: SeriesForecast[] }) {
  const rows = entries
    .filter((e) => e.kind === 'employment_share' && e.backtest)
    .sort((a, b) => (a.backtest?.ratio ?? 1) - (b.backtest?.ratio ?? 1))
  const beat = rows.filter((r) => (r.backtest?.ratio ?? 1) < 1).length
  return (
    <div className="flex flex-col gap-3">
      <p className="m-0 max-w-[760px] text-[14px]">
        For each job group we hid past years, let each model predict them, and compared with what really happened. A model is used only if it beat simply repeating last year: <b>{beat} of {rows.length} groups</b>.
      </p>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {rows.map((r) => {
          const gain = Math.max(0, Math.round(100 * (1 - (r.backtest?.ratio ?? 1))))
          return (
            <li key={r.series_id} className="grid grid-cols-[minmax(0,220px)_minmax(0,1fr)_minmax(0,190px)] items-center gap-3 text-[13px]">
              <span className="truncate font-medium">{r.title.replace(': share of employees (%)', '')}</span>
              <span className="h-4 rounded-full bg-mist">
                {gain > 0 && <span className="block h-4 rounded-full bg-rising transition-[width] duration-700" style={{ width: `${Math.min(100, gain * 2)}%` }} />}
              </span>
              <span className={gain > 0 ? 'font-semibold text-rising' : 'text-graphite'}>{gain > 0 ? `${gain}% more accurate than "no change": forecast used` : '"no change" was as good: shown as no change'}</span>
            </li>
          )
        })}
      </ul>
      <p className="m-0 text-[12px] text-graphite">Models tried: repeat last year, drift, straight line, slowing trend, smoothing, Theta and gradient boosting. Re-run on every new DOSM release.</p>
    </div>
  )
}

const LIST_ORDER: Direction[] = ['rising', 'weakening', 'stable', 'insufficient', 'expert']
const ARROW: Record<Direction, [string, string]> = {
  rising: ['↑', 'text-rising'],
  weakening: ['↓', 'text-weak'],
  stable: ['→', 'text-graphite'],
  insufficient: ['?', 'text-graphite'],
  expert: ['◆', 'text-observed'],
}

function Signals({ signals, onPick }: { signals: Signal[]; onPick: (s: Signal) => void }) {
  const listed = signals.filter((s) => s.family !== 'ai_task_use')
  return (
    <div className="grid gap-x-8 md:grid-cols-2">
      {LIST_ORDER.map((d) => {
        const items = listed.filter((s) => s.direction === d)
        if (!items.length) return null
        return (
          <div key={d} className="flex flex-col">
            <span className={`cap pb-1 pt-3 ${ARROW[d][1]}`}>{DIRECTION_LABEL[d]}</span>
            {items.map((s) => (
              <button key={s.id} type="button" onClick={() => onPick(s)} className="grid cursor-pointer grid-cols-[22px_minmax(0,1fr)_auto] items-center gap-3 border-0 border-t border-line bg-transparent py-2.5 text-left hover:bg-fog">
                <span aria-hidden="true" className={`text-[18px] font-semibold ${ARROW[d][1]}`}>{ARROW[d][0]}</span>
                <span className="min-w-0"><span className="block truncate font-medium">{s.title}</span><span className="block truncate text-[12px] text-graphite">{s.headline}</span></span>
                <Sparkline points={s.points} color="#6c47ff" />
              </button>
            ))}
          </div>
        )
      })}
    </div>
  )
}

export function LiveIntelligence() {
  const { t } = useT()
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=12', RUNS_POLL_MS)
  const sources = useApi<SourceStatus[]>('/api/sources')
  const signals = useApi<SignalsResponse>('/api/signals')
  const forecast = useApi<SeriesForecast[]>('/api/forecast')
  const [step, setStep] = useState<StepId>('schedule')
  const [win, setWin] = useState<{ title: string; panes: Pane[] } | null>(null)
  const [picked, setPicked] = useState<Signal | null>(null)

  const latest = runs.data?.[0]
  const running = latest?.status === 'running'
  const finished = runs.data?.find((r) => r.status !== 'running')
  const [stepTitle, stepText] = STEP_TEXT[step]
  const names = Object.fromEntries((sources.data ?? []).map((src) => [src.id, src.name.split(' · ')[0].split(' (')[0]]))
  const openSource = (id: string) => {
    const s = sources.data?.find((x) => x.id === id)
    if (s) setWin({ title: 'Registered source', panes: [sourcePane(s)] })
  }
  const openHistory = () =>
    setWin({
      title: 'Run history',
      panes: [
        {
          key: 'runs',
          title: 'Every run, newest first',
          hint: 'Sources publish quarterly or yearly, so most runs rightly find nothing new.',
          body:
            runs.data && runs.data.length > 0 ? (
              <ol className="m-0 flex list-none flex-col p-0">{runs.data.map((run) => <RunCard key={run.id} run={run} names={names} />)}</ol>
            ) : (
              <Empty>No run yet. A new deployment starts its first run on its own.</Empty>
            ),
        },
      ],
    })

  return (
    <main className="page">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Live intelligence · open to everyone</span>
          <h1 className="h1">{t('Where every number comes from')}</h1>
          <p className="m-0 max-w-[640px] text-graphite">A scheduled pipeline collects seven public sources every day, even when nobody uses the app. Click any part to see what it does.</p>
        </div>
        <div className="flex items-start gap-3">
          <span className={`tag mt-2 ${RESULT_STYLE[running ? 'running' : 'no change']}`}>
            {running ? 'Running now' : latest ? `Idle · last run ${formatWhen(latest.finished_at)}` : 'No run yet'}
          </span>
          <RunNow onStarted={runs.reload} />
        </div>
      </header>

      <section className="card-dark flex flex-col gap-3.5 bg-[radial-gradient(60%_60%_at_50%_0%,rgba(93,227,255,0.08),rgba(33,33,38,0)_70%)] p-5">
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={openHistory} className="inline-flex min-h-[40px] cursor-pointer items-center gap-2 rounded-lg border-0 bg-[#ffa86b] px-4 font-semibold text-void shadow-[0_4px_16px_rgba(255,168,107,0.35)] hover:brightness-105">
            <History size={16} aria-hidden="true" />
            Run history{runs.data ? ` · ${runs.data.length}` : ''}
          </button>
          <span className="text-[12px] text-stone">Last run: {finished ? `${formatWhen(finished.started_at)} · ${finished.status}` : '—'}</span>
        </div>
        {runs.error && <Problem what="runs" message={runs.error} onRetry={runs.reload} />}
        <PipelineDiagram run={running ? latest : finished} running={running} selected={step} onSelect={setStep} onSource={openSource} />
        <div className="flex flex-col gap-1 rounded-lg bg-surface px-3.5 py-3" aria-live="polite">
          <span className="font-mono text-[11px] tracking-widest text-cyan">{stepTitle}</span>
          <span className="text-[13px]">{stepText}</span>
        </div>
      </section>

      <section className="section">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="h2">Signals from the market</h2>
          <span className="text-[12px] text-graphite">Click one for its evidence</span>
        </div>
        {signals.loading && <Loading what="the signals" />}
        {signals.error && <Problem what="the signals" message={signals.error} onRetry={signals.reload} />}
        {signals.data && <Signals signals={signals.data.signals} onPick={setPicked} />}
      </section>

      <section className="section">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="h2">Do our forecasts beat a simple guess?</h2>
          <KindLabel kind="estimate" />
        </div>
        {forecast.loading && <Loading what="the forecast check" />}
        {forecast.error && <Problem what="the forecast check" message={forecast.error} onRetry={forecast.reload} />}
        {forecast.data && <ForecastScore entries={forecast.data} />}
      </section>

      <ChangeTest />

      {picked && <EvidenceDrawer signal={picked} onClose={() => setPicked(null)} />}
      {win && <Windows title={win.title} panes={win.panes} onClose={() => setWin(null)} />}
    </main>
  )
}
