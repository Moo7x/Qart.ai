import { formatWhen, useApi } from '../api'
import { KindLabel } from '../components/Why'
import { Loading, Problem } from '../components/ui'
import type { StatusResponse } from '../typesAgents'

// Status (docs/PHASE2_PLAN.md A9, contract C9): how fresh the data is, what ran, which engines
// answered and what they cost. Measured from the app's own tables; cost is an estimate.

const POLL_MS = 30_000

function FairnessLine({ f }: { f: StatusResponse['fairness'] }) {
  if (!f.available || f.identical === undefined) return <p className="m-0 text-[13px]">Paired-profile fairness check: not available.</p>
  return (
    <div className="flex flex-col gap-1">
      <p className="m-0 text-[13px]">
        <span className={`font-semibold ${f.identical ? 'text-rising' : 'text-weak'}`}>{f.identical ? 'Identical results' : 'Results differ'}</span>
        {' '}for {f.pairs} pairs of the same synthetic CV that differ only in name, gender, religion, race, age, marital status and contact details. Largest fit difference: {f.max_fit_difference}. Run {formatWhen(f.checked_at ?? null)} on the current evidence.
      </p>
      <p className="m-0 text-[12px] text-graphite">Personal details are removed before matching, and the same check runs in the test suite on every change.</p>
    </div>
  )
}

function PlatformSdg({ p }: { p: StatusResponse['platform_sdg'] }) {
  if (!p.available) return <p className="m-0 text-[13px]">SDG hours planned across all people: not available.</p>
  if (p.suppressed) {
    return <p className="m-0 text-[13px]">SDG hours planned across all people: withheld, because {p.profiles} {p.profiles === 1 ? 'person has' : 'people have'} chosen a destination and groups under {p.min_profiles} are never shown.</p>
  }
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[13px]">Study hours planned across the {p.profiles} people with a destination, per SDG target</span>
      <ul className="m-0 flex list-none flex-wrap gap-x-6 gap-y-1 p-0 text-[13px]">
        {(p.totals ?? []).map((t) => <li key={t.target}><span className="font-mono">{t.target}</span> · {t.hours} h</li>)}
      </ul>
      <p className="m-0 text-[12px] text-graphite">An hour of a skill counts toward every target that skill serves, so these do not add up across targets. Planned hours, not completed hours.</p>
    </div>
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
          <section className="section">
            <h2 className="h2">Fairness and SDG totals</h2>
            <FairnessLine f={data.fairness} />
            <PlatformSdg p={data.platform_sdg} />
          </section>
        </>
      )}
    </main>
  )
}
