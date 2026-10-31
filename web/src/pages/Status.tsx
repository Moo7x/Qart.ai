import { useApi } from '../api'
import { KindLabel } from '../components/Why'
import { Loading, Problem } from '../components/ui'
import type { StatusResponse } from '../typesAgents'

// Status (docs/PHASE2_PLAN.md A9, contract C9): how fresh the data is, what ran, which engines
// answered and what they cost. Measured from the app's own tables; cost is an estimate.

const POLL_MS = 30_000

export function Status() {
  const view = useApi<StatusResponse>('/api/status', POLL_MS)
  const data = view.data
  return (
    <main className="page">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">Status · engines and cost</span>
        <h1 className="h1">Which engines answer, and what does it cost?</h1>
        <p className="m-0 max-w-[700px] text-[13px] text-graphite">Measured from the app&rsquo;s usage counter; cost multiplies the measured calls by declared list prices, so it is an estimate. Data freshness and runs are on Live intelligence.</p>
      </header>
      {view.loading && !data && <Loading what="the status" />}
      {view.error && <Problem what="the status" message={view.error} onRetry={view.reload} />}
      {data && (
        <>
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
            {data.cost.per_person_usd != null && (
              <div className="grid gap-3 sm:grid-cols-4">
                <div className="card-light flex flex-col gap-0.5 p-3"><span className="cap">Per person</span><span className="font-mono text-[22px]">USD {data.cost.per_person_usd.toFixed(4)}</span><span className="text-[11px] text-graphite">measured over {data.cost.profiles} profiles</span></div>
                {Object.entries(data.cost.per_month_usd ?? {}).map(([n, usd]) => (
                  <div key={n} className="card-light flex flex-col gap-0.5 p-3"><span className="cap">{Number(n).toLocaleString()} people a month</span><span className="font-mono text-[22px]">USD {usd.toFixed(2)}</span><span className="text-[11px] text-graphite">language model and GPU, estimate</span></div>
                ))}
              </div>
            )}
            <p className="m-0 text-[12px] text-graphite">Hosting (Replit) is a fixed monthly cost, not per person. Total so far: about USD {data.cost.total_usd.toFixed(4)} for the language model{data.cost.gpu_price_set ? ' and GPU' : ' (GPU seconds above; set its price to include it)'}. {data.cost.note} Prices checked {data.cost.prices_checked}.</p>
          </section>
        </>
      )}
    </main>
  )
}
