import { Lock } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { formatWhen, parseUtc, sendJSON, useApi } from '../api'
import { PipelineDiagram, type StepId } from '../components/PipelineDiagram'
import { Empty, Loading, Problem } from '../components/ui'
import type { BacktestEntry, Run, SourceStatus } from '../types'

const RUNS_POLL_MS = 5_000
const SECONDS_PER_MINUTE = 60

const STEP_TEXT: Record<StepId, [string, string]> = {
  schedule: ['SCHEDULE', 'A scheduled job runs the whole pipeline; an admin can also start it with Run now. A lock stops two runs overlapping, and every run is logged, including runs with no change.'],
  sources: ['REGISTERED SOURCES', 'Four public sources, each with its terms and what it can and cannot show. A source that fails keeps its last good data and is marked in the run log.'],
  fetch: ['FETCH', 'Each source gets two attempts with a time limit. Releases already read are not downloaded again, so a quiet day costs a few requests.'],
  validate: ['VALIDATE', 'Release dates and quarters are checked; pages announced before their release day are skipped; a count that is not stated stays missing, never zero; a jump in total job ads is treated as a coverage break.'],
  measure: ['MEASURE', 'Shares and changes between comparable periods, at the precision each source publishes. The DOSM trend backtest below decides whether a trend may be projected.'],
  label: ['LABEL', 'Rising or weakening needs two independent sources, or one official series with at least eight comparable points; otherwise the signal is "not enough evidence yet".'],
  forecast: ['SCENARIOS · DECLARED ASSUMPTIONS', 'Moderate and fast AI-adoption scenarios shift nonessential emphasis using observed occupation-level AI use. They are conditional estimates, not measured Malaysian adoption forecasts. Essentials stay fixed.'],
  match: ['MATCH', 'The engine scores every destination against the person’s claimed skills. New evidence produces a stored comparison; the accepted journey stays fixed until the person chooses an update.'],
  notify: ['IN-APP PROPOSALS', 'The scheduled pipeline publishes profile-specific evidence, score and pathway comparisons. What changed shows those proposals and a separate read-only historical replay. Telegram is deferred.'],
  telegram: ['TELEGRAM · LATER', 'Planned for the improvement phase: change notifications, then answers drawn only from the app, with sources.'],
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
      setMessage('Run started. Progress appears below.')
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
          <input
            id="admin-token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Admin token"
            className="min-h-[38px] rounded-md border border-hairline bg-fog px-3 font-mono text-sm"
          />
          <button type="submit" className="btn btn-v" disabled={!token}>Start run</button>
          <button type="button" className="btn" onClick={() => setOpen(false)}>Cancel</button>
        </form>
      )}
      {message && <span role="status" className="text-xs text-graphite">{message}</span>}
    </div>
  )
}

export function LiveIntelligence() {
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=12', RUNS_POLL_MS)
  const sources = useApi<SourceStatus[]>('/api/sources')
  const backtest = useApi<BacktestEntry[]>('/api/pipeline/backtest')
  const [step, setStep] = useState<StepId>('validate')
  const [open, setOpen] = useState<number | null>(null)

  const latest = runs.data?.[0]
  const running = latest?.status === 'running'
  const finished = runs.data?.find((r) => r.status !== 'running')
  const [stepTitle, stepText] = STEP_TEXT[step]

  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Live intelligence · open to everyone</span>
          <h1 className="h1">Where every number comes from</h1>
          <p className="m-0 max-w-[640px] text-graphite">
            The pipeline runs on a schedule even when nobody is using the app. Every run is logged, including runs where
            nothing changed.
          </p>
        </div>
        <div className="flex items-start gap-3">
          <span className={`tag mt-2 ${RESULT_STYLE[running ? 'running' : 'no change']}`}>
            {running ? 'Running now' : latest ? `Idle · last run ${formatWhen(latest.finished_at)}` : 'No run yet'}
          </span>
          <RunNow onStarted={runs.reload} />
        </div>
      </header>

      <section className="card-dark flex flex-col gap-3.5 bg-[radial-gradient(60%_60%_at_50%_0%,rgba(93,227,255,0.08),rgba(33,33,38,0)_70%)] p-5">
        <PipelineDiagram run={running ? latest : finished} running={running} selected={step} onSelect={setStep} />
        <div className="flex flex-col gap-1 rounded-lg bg-surface px-3.5 py-3" aria-live="polite">
          <span className="font-mono text-[11px] tracking-widest text-cyan">{stepTitle}</span>
          <span className="text-[13px]">{stepText}</span>
        </div>
      </section>

      <div className="flex flex-wrap items-start gap-5">
        <section className="card-light flex min-w-0 flex-[1_1_440px] flex-col gap-2.5 px-6 py-5">
          <h2 className="h2">Run history</h2>
          {runs.loading && <Loading what="runs" />}
          {runs.error && <Problem what="runs" message={runs.error} onRetry={runs.reload} />}
          {runs.data && runs.data.length === 0 && <Empty>No run yet. A new deployment starts its first run on its own.</Empty>}
          {runs.data && runs.data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] border-collapse text-[13px]">
                <thead>
                  <tr className="cap text-left">
                    <th className="py-2 pr-2 font-medium">When</th>
                    <th className="px-2 py-2 font-medium">Trigger</th>
                    <th className="px-2 py-2 font-medium">Sources</th>
                    <th className="px-2 py-2 font-medium">New rows</th>
                    <th className="px-2 py-2 font-medium">Took</th>
                    <th className="py-2 pl-2 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.map((run) => (
                    <FragmentRow key={run.id} run={run} open={open === run.id} onToggle={() => setOpen(open === run.id ? null : run.id)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card-light flex min-w-0 flex-[1_1_360px] flex-col gap-2.5 px-6 py-5">
          <h2 className="h2">Model check</h2>
          <p className="m-0 text-[13px] text-graphite">
            Share of employees per occupation group, fitted to 2021 and scored on 2022–2025 (mean error in percentage
            points). Where &ldquo;no change&rdquo; wins, the app shows history and does not project a trend.
          </p>
          {backtest.error && <Problem what="the backtest" message={backtest.error} onRetry={backtest.reload} />}
          {backtest.data && (
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="cap text-left">
                  <th className="py-2 pr-2 font-medium">Group</th>
                  <th className="px-2 py-2 text-right font-medium">No change</th>
                  <th className="px-2 py-2 text-right font-medium">Straight line</th>
                  <th className="px-2 py-2 text-right font-medium">Damped</th>
                </tr>
              </thead>
              <tbody>
                {backtest.data.map((row) => (
                  <tr key={row.group} className="border-t border-mist">
                    <td className="py-2 pr-2">{row.group.replace('_', ' & ')}</td>
                    {(['naive', 'linear', 'damped'] as const).map((model) => (
                      <td key={model} className={`px-2 py-2 text-right font-mono ${row.best === model ? 'font-semibold text-rising' : ''}`}>
                        {row[model].toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <section className="card-light flex flex-col gap-2.5 px-6 py-5">
        <h2 className="h2">Registered sources</h2>
        {sources.error && <Problem what="sources" message={sources.error} onRetry={sources.reload} />}
        {sources.data && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-[13px]">
              <thead>
                <tr className="cap text-left">
                  <th className="py-2 pr-2 font-medium">Source</th>
                  <th className="px-2 py-2 font-medium">Shows · does not show</th>
                  <th className="px-2 py-2 font-medium">Terms</th>
                  <th className="px-2 py-2 font-medium">Rows</th>
                  <th className="py-2 pl-2 font-medium">Last run</th>
                </tr>
              </thead>
              <tbody>
                {sources.data.map((s) => (
                  <tr key={s.id} className="border-t border-mist align-top">
                    <td className="py-2.5 pr-2">
                      <a href={s.url} target="_blank" rel="noopener noreferrer" className="font-medium text-void">{s.name}</a>
                      <span className="block text-xs text-graphite">{s.publisher} · {s.cadence}</span>
                    </td>
                    <td className="px-2 py-2.5 text-graphite">{s.shows}<span className="block text-xs">Not: {s.does_not_show}</span></td>
                    <td className="px-2 py-2.5">
                      <a href={s.terms_url} target="_blank" rel="noopener noreferrer">{s.terms}</a>
                      <span className="block font-mono text-[11px] text-ash">checked {s.terms_checked ?? 'not yet'}</span>
                    </td>
                    <td className="px-2 py-2.5 font-mono">{s.observations}</td>
                    <td className="py-2.5 pl-2">
                      <span className={`tag ${s.last_status === 'ok' ? 'bg-rising-bg text-rising' : s.last_status ? 'bg-weak-bg text-weak' : 'bg-mist text-graphite'}`}>
                        {s.last_status ?? 'not run'}
                      </span>
                      {s.last_note && <span className="mt-1 block max-w-[260px] font-mono text-[11px] text-ash">{s.last_note}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}

function FragmentRow({ run, open, onToggle }: { run: Run; open: boolean; onToggle: () => void }) {
  const ok = run.sources.filter((s) => s.status === 'ok').length
  return (
    <>
      <tr className="border-t border-mist">
        <td className="py-2.5 pr-2 font-mono text-xs">
          <button type="button" onClick={onToggle} aria-expanded={open} className="cursor-pointer border-0 bg-transparent p-0 text-left font-mono text-xs">
            {open ? '▾' : '▸'} {formatWhen(run.started_at)}
          </button>
        </td>
        <td className="px-2 py-2.5">{run.trigger}</td>
        <td className="px-2 py-2.5 font-mono">{run.status === 'running' ? '…' : `${ok}/${run.sources.length}`}</td>
        <td className="px-2 py-2.5 font-mono">{run.new_observations}</td>
        <td className="px-2 py-2.5 font-mono">{duration(run)}</td>
        <td className="py-2.5 pl-2"><span className={`tag ${RESULT_STYLE[run.status] ?? 'bg-mist text-graphite'}`}>{run.status}</span></td>
      </tr>
      {open && (
        <tr>
          <td colSpan={6} className="pb-3">
            <ul className="m-0 flex list-none flex-col gap-1 rounded-md bg-fog p-3 font-mono text-[11px] text-graphite">
              {run.sources.map((s) => (
                <li key={s.source_id}>
                  <span className={s.status === 'ok' ? 'text-rising' : 'text-weak'}>{s.status}</span> · {s.source_id} · {s.new} new
                  {s.note ? ` · ${s.note}` : ''}
                  {s.error ? ` · ${s.error}` : ''}
                </li>
              ))}
            </ul>
          </td>
        </tr>
      )}
    </>
  )
}
