import { formatWhen, useApi } from '../api'
import { KindLabel } from '../components/Why'
import { Loading, Problem } from '../components/ui'
import type { StatusResponse } from '../typesAgents'

// Status (docs/PHASE2_PLAN.md A9, contract C9): how fresh the data is, what ran, which engines
// answered and what they cost. Measured from the app's own tables; cost is an estimate.

const POLL_MS = 30_000

function TimeToPlan({ t }: { t: NonNullable<StatusResponse['time_to_plan']> }) {
  const share = t.people ? t.under_target / t.people : null
  return (
    <section className="section">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="h2">Time to ranked roles and a plan</h2>
        <KindLabel kind="observed" />
      </div>
      {t.people === 0 ? (
        <p className="m-0 text-[14px] text-graphite">No timed journey yet. Each new profile records the minutes from Start to choosing a role.</p>
      ) : (
        <p className="m-0 text-[15px]">
          <b className="font-mono text-[28px]">{share === null ? '—' : `${Math.round(100 * share)}%`}</b> of {t.people} {t.people === 1 ? 'person' : 'people'} got there within {t.target_seconds / 60} minutes (target {Math.round(100 * t.target_share)}%) · median {t.median_seconds === null ? '—' : `${Math.floor(t.median_seconds / 60)} min ${t.median_seconds % 60} s`}
        </p>
      )}
      <p className="m-0 text-[12px] text-graphite">Measured from use: the intake timer plus the time until a destination was chosen. Our Phase 1 target.</p>
    </section>
  )
}

export function Status() {
  const view = useApi<StatusResponse>('/api/status', POLL_MS)
  const data = view.data
  return (
    <main className="page">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">Status · data, engines, cost</span>
        <h1 className="h1">Is the evidence fresh, and what does it cost?</h1>
        <p className="m-0 max-w-[700px] text-graphite">Measured from the app&rsquo;s own run log and usage counter. Cost multiplies the measured calls by declared list prices, so it is an estimate.</p>
      </header>
      {data?.time_to_plan && <TimeToPlan t={data.time_to_plan} />}
      {view.loading && !data && <Loading what="the status" />}
      {view.error && <Problem what="the status" message={view.error} onRetry={view.reload} />}
      {data && (
        <>
          <section className="section">
            <div className="flex flex-wrap items-baseline justify-between gap-2"><h2 className="h2">Sources</h2><KindLabel kind="observed" /></div>
            <p className="m-0 text-[13px] text-graphite">{data.schedule}</p>
            <table className="w-full border-collapse text-[13px]">
              <thead><tr className="text-left text-graphite"><th className="py-1 pr-3 font-normal">Source</th><th className="py-1 pr-3 font-normal">Data fetched</th><th className="py-1 pr-3 font-normal">Last attempt</th><th className="py-1 font-normal">Last success</th></tr></thead>
              <tbody>
                {data.sources.map((s) => (
                  <tr key={s.id} className="border-t border-line">
                    <td className="py-1.5 pr-3">{s.name}</td>
                    <td className="py-1.5 pr-3 font-mono">{formatWhen(s.serving_snapshot_from)}</td>
                    <td className={`py-1.5 pr-3 ${s.last_status === 'failed' ? 'text-weak' : ''}`}>{s.last_status ?? '—'} · {formatWhen(s.last_attempt_at)}</td>
                    <td className="py-1.5 font-mono">{formatWhen(s.last_success_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="section">
            <h2 className="h2">Recent runs</h2>
            <ul className="m-0 flex list-none flex-col gap-1 p-0 font-mono text-[12px]">
              {data.runs.map((r) => <li key={r.id}>{formatWhen(r.started_at)} · {r.trigger} · {r.status} · {r.new_observations} new</li>)}
            </ul>
          </section>
          <section className="section">
            <div className="flex flex-wrap items-baseline justify-between gap-2"><h2 className="h2">Engines and cost</h2><KindLabel kind="estimate" /></div>
            <div className="grid gap-3 md:grid-cols-2">
              {([['Language model', data.engines.language_model], ['GPU (RunPod)', data.engines.gpu]] as const).map(([name, e]) => (
                <div key={name} className="card-light flex flex-col gap-1 p-3 text-[13px]">
                  <span className="font-semibold">{name}: {e.configured ? 'connected' : 'not configured, labelled fallbacks in use'}</span>
                  <span className="font-mono text-[12px] text-graphite">{e.models.join(' · ')}</span>
                  <span>{e.calls} calls, {e.failed} failed (fallback shown)</span>
                </div>
              ))}
            </div>
            <table className="w-full border-collapse text-[13px]">
              <thead><tr className="text-left text-graphite"><th className="py-1 pr-3 font-normal">Purpose</th><th className="py-1 pr-3 font-normal">Model</th><th className="py-1 pr-3 font-normal">Calls</th><th className="py-1 pr-3 font-normal">Tokens in / out</th><th className="py-1 pr-3 font-normal">Seconds</th><th className="py-1 font-normal">Cost (USD)</th></tr></thead>
              <tbody>
                {data.usage.map((u) => (
                  <tr key={`${u.purpose}-${u.model}`} className="border-t border-line font-mono text-[12px]">
                    <td className="py-1.5 pr-3 font-sans">{u.purpose}</td>
                    <td className="py-1.5 pr-3">{u.model}</td>
                    <td className="py-1.5 pr-3">{u.calls}{u.failed ? ` (${u.failed} failed)` : ''}</td>
                    <td className="py-1.5 pr-3">{u.tokens_in.toLocaleString()} / {u.tokens_out.toLocaleString()}</td>
                    <td className="py-1.5 pr-3">{u.seconds.toFixed(1)}</td>
                    <td className="py-1.5">{u.cost_usd === null ? 'price not set' : u.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="m-0 text-[12px] text-graphite">Total so far: about USD {data.cost.total_usd.toFixed(4)} for the language model{data.cost.gpu_price_set ? ' and GPU' : ' (GPU seconds above; set its price to include it)'}. {data.cost.note} Prices checked {data.cost.prices_checked}.</p>
          </section>
        </>
      )}
    </main>
  )
}
