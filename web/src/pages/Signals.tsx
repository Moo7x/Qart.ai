import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowDownRight, ArrowRight, ArrowUpRight, DatabaseZap, ExternalLink, Lightbulb } from 'lucide-react'
import FlowSteps from '../components/FlowSteps'
import { getSnapshotDiff, getSnapshots, ingestNextSnapshot } from '../api'
import { useReveal } from '../motion'
import type { Signal, Snapshot, SnapshotDiff } from '../types'
import { btn, Card, EmptyState, Highlight, label, Loading, NextStepCard, PageHeader, ProvenanceTag, SectionTitle, StatTile, Tag } from '../ui'

// AEI values are already percentages: usage_pct 0.30 = 0.30 % of the geography's conversations.
const METRICS: Record<string, string> = {
  usage_pct: 'Share of AI conversations',
  automation_pct: 'Automation share',
  augmentation_pct: 'Augmentation share',
}
const METRIC_ORDER = ['usage_pct', 'automation_pct', 'augmentation_pct']

const pct = (v: number | null | undefined) => (v === null || v === undefined ? '–' : `${v.toFixed(2)}%`)

/** One row per occupation and geography, with its metrics side by side. */
function byEntity(signals: Signal[]) {
  const rows = new Map<string, { entity: string; geo: string | null; values: Record<string, number> }>()
  for (const s of signals) {
    const key = `${s.entity}|${s.geo ?? ''}`
    const row = rows.get(key) ?? { entity: s.entity, geo: s.geo, values: {} }
    row.values[s.metric] = s.value
    rows.set(key, row)
  }
  return [...rows.values()]
}

export default function Signals() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [diff, setDiff] = useState<SnapshotDiff | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [loading])

  const load = () =>
    Promise.all([getSnapshots().catch(() => []), getSnapshotDiff()]).then(([s, d]) => {
      setSnapshots(s)
      setDiff(d)
      setLoading(false)
    })
  useEffect(() => { load() }, [])

  const ingest = async () => {
    setBusy(true)
    try {
      const result = await ingestNextSnapshot()
      setMessage(result.message)
      await load()
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Loading what="signals" />

  const latest = snapshots[snapshots.length - 1]
  const rows = latest?.signals ? byEntity(latest.signals) : []
  const significant = diff?.changes.filter(c => c.significant) ?? []

  return (
    <div ref={root} className="max-w-4xl mx-auto space-y-8">
      <FlowSteps />
      <div data-reveal>
        <PageHeader
          title={<>What the AI-use data is <Highlight>saying</Highlight></>}
          intro="Dated public evidence on how people use AI in work like yours. It informs the assumptions behind your role matches; it never changes them by itself."
          aside={latest?.label ? <Tag tone="linen">{latest.label}</Tag> : undefined}
        />
      </div>

      {snapshots.length === 0 ? (
        <EmptyState title="No evidence loaded yet">Load the first snapshot to see signals.</EmptyState>
      ) : (
        <>
          <div data-reveal className="grid grid-cols-3 gap-3">
            <StatTile tone="mocha" label="Snapshots loaded" value={snapshots.length} />
            <StatTile tone="linen" label="Signals in latest" value={latest?.signals?.length ?? 0} />
            <StatTile tone="action" label="Notable changes" value={significant.length} />
          </div>

          <section data-reveal>
            <SectionTitle aside={
              <button onClick={ingest} disabled={busy} className={btn.outline}>
                <DatabaseZap size={16} aria-hidden="true" /> {busy ? 'Loading…' : 'Load newer snapshot'}
              </button>
            }>Data sources</SectionTitle>
            <p className="-mt-1 mb-3 text-xs text-graphite">Historical data replay: the newer snapshot already exists and is loaded as if it had just been released.</p>
            {message && <p role="status" className="mb-3 text-sm text-action-ink bg-action-tint rounded-md px-3 py-2">{message}</p>}
            <div className="grid gap-3 sm:grid-cols-2">
              {snapshots.map(s => (
                <Card key={s.id} className="p-5 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <ProvenanceTag kind="evidence">period {s.period}</ProvenanceTag>
                    {s.geo && <Tag tone="linen">{s.geo}</Tag>}
                  </div>
                  <div className="font-semibold text-ink">{s.source}</div>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
                    <dt className="text-graphite">Released</dt><dd className="text-ink tabular-nums">{s.release_date}</dd>
                    {s.retrieved_at && <><dt className="text-graphite">Retrieved</dt><dd className="text-ink tabular-nums">{s.retrieved_at.slice(0, 10)}</dd></>}
                    {s.licence && <><dt className="text-graphite">Licence</dt><dd className="text-ink">{s.licence}</dd></>}
                  </dl>
                  {s.url && (
                    <a href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-action-ink hover:underline">
                      Open source <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  )}
                </Card>
              ))}
            </div>
          </section>

          {diff && (
            <section data-reveal>
              <SectionTitle>What changed</SectionTitle>
              <Card className="p-6 space-y-3">
                <div className={label}>{diff.from_period} → {diff.to_period} · {diff.label}</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-graphite">
                        <th scope="col" className="py-2 pr-3 font-medium">Signal</th>
                        <th scope="col" className="py-2 px-3 font-medium text-right">Before</th>
                        <th scope="col" className="py-2 px-3 font-medium text-right">After</th>
                        <th scope="col" className="py-2 pl-3 font-medium text-right">Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {significant.map((c, i) => (
                        <tr key={i} className="border-t border-hairline">
                          <td className="py-2 pr-3 text-ink">{c.entity} · {METRICS[c.metric] ?? c.metric}{c.geo ? ` · ${c.geo}` : ''}</td>
                          <td className="py-2 px-3 text-right tabular-nums text-graphite">{pct(c.before)}</td>
                          <td className="py-2 px-3 text-right tabular-nums text-ink">{pct(c.after)}</td>
                          <td className="py-2 pl-3 text-right tabular-nums font-medium text-ink">
                            {c.relative_change === null ? '–' : (
                              <span className="inline-flex items-center gap-0.5">
                                {c.relative_change >= 0 ? <ArrowUpRight size={14} aria-hidden="true" /> : <ArrowDownRight size={14} aria-hidden="true" />}
                                {`${(c.relative_change * 100).toFixed(0)}%`}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {diff.suggested_assumption_reviews.length > 0 && (
                  <div className="bg-marigold-tint rounded-md p-4 text-sm text-marigold-ink">
                    <div className="flex items-center gap-1.5 font-semibold"><Lightbulb size={16} aria-hidden="true" /> {diff.suggested_assumption_reviews.length} assumption review{diff.suggested_assumption_reviews.length > 1 ? 's' : ''} suggested to HR</div>
                    <p className="mt-1">HR decides whether to change who does which task. Your matches update only after HR approves.</p>
                  </div>
                )}
                <p className="text-xs text-graphite">{diff.note}</p>
              </Card>
            </section>
          )}

          {latest && rows.length > 0 && (
            <section data-reveal>
              <SectionTitle aside={<ProvenanceTag kind="evidence">{latest.source} · {latest.period}</ProvenanceTag>}>Signals by occupation</SectionTitle>
              <Card className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-graphite">
                      <th scope="col" className="py-3 px-4 font-medium">Occupation</th>
                      {METRIC_ORDER.map(m => <th key={m} scope="col" className="py-3 px-4 font-medium text-right">{METRICS[m]}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(r => (
                      <tr key={`${r.entity}|${r.geo}`} className="border-t border-hairline">
                        <th scope="row" className="py-2.5 px-4 text-left font-normal text-ink">
                          {r.entity}{r.geo ? <span className="text-graphite"> · {r.geo}</span> : null}
                        </th>
                        {METRIC_ORDER.map(m => <td key={m} className="py-2.5 px-4 text-right tabular-nums text-ink">{pct(r.values[m])}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
              <p className="mt-2 text-xs text-graphite">AI usage share is not proof that tasks are replaced. Automation = AI does the task; augmentation = AI helps a person do it.</p>
            </section>
          )}
        </>
      )}

      <div data-reveal>
        <NextStepCard
          eyebrow="Step 3"
          title="See which roles fit you"
          action={<Link to="/future" className={`${btn.primary} whitespace-nowrap`}>See my role matches <ArrowRight size={16} aria-hidden="true" /></Link>}
        >
          Your matches combine your evidence with these signals, through the company's assumptions.
        </NextStepCard>
      </div>
    </div>
  )
}
