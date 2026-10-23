import { useEffect, useState } from 'react'
import { ArrowDownRight, ArrowUpRight, CircleCheck, DatabaseZap, Lightbulb } from 'lucide-react'
import { getAssumptions, getSnapshotDiff, getSnapshots, ingestNextSnapshot, putAssumptions } from '../api'
import type { Allocation, CompanyAssumptions, Scenario, Signal, Snapshot, SnapshotDiff } from '../types'
import { btn, Card, Highlight, input as inputCls, label, PageHeader, ProvenanceTag, SectionTitle, Tag } from '../ui'

const ALLOCATIONS: { value: Allocation; label: string }[] = [
  { value: 'human', label: 'Human does it' },
  { value: 'ai_drafts_human_reviews', label: 'AI drafts, human reviews' },
  { value: 'ai', label: 'AI does it' },
]
const SCENARIOS: Scenario[] = ['assistive', 'agentic']

// AEI values are already percentages: usage_pct 0.30 = 0.30 % of the geography's conversations.
const METRICS: Record<string, string> = {
  usage_pct: 'share of AI conversations',
  automation_pct: 'automation share',
  augmentation_pct: 'augmentation share',
}

const METRIC_ORDER = ['usage_pct', 'automation_pct', 'augmentation_pct']

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? '–' : `${value.toFixed(2)}%`
}

/** One row per occupation and geography, with its AEI metrics side by side. */
function byEntity(signals: Signal[]) {
  const rows = new Map<string, { entity: string; geo: string | null; values: Record<string, number> }>()
  for (const s of signals) {
    const key = `${s.entity}|${s.geo ?? ''}`
    const row = rows.get(key) ?? { entity: s.entity, geo: s.geo ?? null, values: {} }
    row.values[s.metric] = s.value
    rows.set(key, row)
  }
  return [...rows.values()]
}

export default function Evidence() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [diff, setDiff] = useState<SnapshotDiff | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [current, setCurrent] = useState<CompanyAssumptions | null>(null)
  const [draft, setDraft] = useState<CompanyAssumptions | null>(null)
  const [note, setNote] = useState('')
  const [saved, setSaved] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = () => {
    getSnapshots().then(setSnapshots).catch(() => {})
    getSnapshotDiff().then(setDiff)
    getAssumptions().then(a => { setCurrent(a); setDraft(structuredClone(a)) }).catch(() => {})
  }
  useEffect(load, [])

  const ingest = async () => {
    setBusy(true)
    try {
      const result = await ingestNextSnapshot()
      setMessage(result.message)
      load()
    } finally {
      setBusy(false)
    }
  }

  const changed = current && draft
    ? SCENARIOS.flatMap(s => Object.keys(draft.scenarios[s].tasks)
        .filter(t => draft.scenarios[s].tasks[t] !== current.scenarios[s].tasks[t])
        .map(t => `${s}: ${t}`))
    : []

  const approve = async () => {
    if (!draft || changed.length === 0) return
    setBusy(true)
    try {
      const latest = snapshots[snapshots.length - 1]?.id ?? draft.based_on_snapshot
      const saved = await putAssumptions({
        ...draft,
        updated_by: 'Nadia (HR, synthetic)',
        based_on_snapshot: latest,
        change_note: note || `Changed ${changed.join(', ')}`,
      })
      setSaved(`Version ${saved.version} approved. Employees' role cards and paths now use it.`)
      setNote('')
      load()
    } finally {
      setBusy(false)
    }
  }

  const setAllocation = (scenario: Scenario, task: string, value: Allocation) => {
    if (!draft) return
    const next = structuredClone(draft)
    next.scenarios[scenario].tasks[task] = value
    setDraft(next)
  }

  // Union of both scenarios' tasks, in first-seen order, so no task can be hidden.
  const tasks = draft ? [...new Set(SCENARIOS.flatMap(sc => Object.keys(draft.scenarios[sc].tasks)))] : []

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <PageHeader
        title={<>Evidence informs, HR <Highlight>decides</Highlight></>}
        intro="New public data can suggest a review. Who does each task only changes when HR approves a new version."
        aside={<Tag tone="linen">Aggregates only</Tag>}
      />

      <section>
        <SectionTitle aside={<ProvenanceTag kind="evidence">layer A</ProvenanceTag>}>External evidence</SectionTitle>
        <Card className="p-6 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <ul className="space-y-1">
              {snapshots.map(s => (
                <li key={s.id} className="text-ink tabular-nums">{s.source} · {s.release_date} release · period {s.period}</li>
              ))}
            </ul>
            <button onClick={ingest} disabled={busy} className={btn.outline}>
              <DatabaseZap size={16} aria-hidden="true" /> Load the newer snapshot
            </button>
          </div>
          <p className="text-xs text-graphite">Historical data replay: the newer snapshot already exists and is loaded as if it had just been released.</p>
          {message && <p role="status" className="text-sm text-action-ink bg-action-tint rounded-md px-3 py-2">{message}</p>}

          {diff && (
            <div className="space-y-3 border-t border-hairline pt-4">
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
                    {diff.changes.filter(c => c.significant).map((c, i) => {
                      const up = (c.relative_change ?? 0) >= 0
                      return (
                        <tr key={i} className="border-t border-hairline">
                          <td className="py-2 pr-3 text-ink">{c.entity} · {METRICS[c.metric] ?? c.metric}{c.geo ? ` · ${c.geo}` : ''}</td>
                          <td className="py-2 px-3 text-right tabular-nums text-graphite">{pct(c.before)}</td>
                          <td className="py-2 px-3 text-right tabular-nums text-ink">{pct(c.after)}</td>
                          <td className="py-2 pl-3 text-right tabular-nums font-medium text-ink">
                            {c.relative_change === null ? '–' : (
                              <span className="inline-flex items-center gap-0.5">
                                {up ? <ArrowUpRight size={14} aria-hidden="true" /> : <ArrowDownRight size={14} aria-hidden="true" />}
                                {`${(c.relative_change * 100).toFixed(0)}%`}
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {diff.suggested_assumption_reviews.length > 0 && (
                <div className="bg-marigold-tint rounded-md p-4 text-sm text-marigold-ink space-y-1.5">
                  <div className="flex items-center gap-1.5 font-semibold"><Lightbulb size={16} aria-hidden="true" /> Suggested assumption reviews</div>
                  {diff.suggested_assumption_reviews.map((r, i) => (
                    <div key={i}><span className="font-mono text-xs">{r.assumption_id}</span>: {r.reason}</div>
                  ))}
                </div>
              )}
              <p className="text-xs text-graphite">{diff.note}</p>
            </div>
          )}

          {snapshots.length > 0 && byEntity(snapshots[snapshots.length - 1].signals ?? []).length > 0 && (
            <div className="space-y-2 border-t border-hairline pt-4">
              <div className={label}>AI use by occupation · {snapshots[snapshots.length - 1].source} · period {snapshots[snapshots.length - 1].period}</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-graphite">
                      <th scope="col" className="py-2 pr-3 font-medium">Occupation</th>
                      {METRIC_ORDER.map(m => <th key={m} scope="col" className="py-2 px-3 font-medium text-right first-letter:uppercase">{METRICS[m]}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {byEntity(snapshots[snapshots.length - 1].signals ?? []).map(r => (
                      <tr key={`${r.entity}|${r.geo}`} className="border-t border-hairline">
                        <th scope="row" className="py-2 pr-3 text-left font-normal text-ink">{r.entity}{r.geo ? <span className="text-graphite"> · {r.geo}</span> : null}</th>
                        {METRIC_ORDER.map(m => <td key={m} className="py-2 px-3 text-right tabular-nums text-ink">{pct(r.values[m])}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-graphite">AI usage share is not proof that tasks are replaced. Automation = AI does the task; augmentation = AI helps a person do it.</p>
            </div>
          )}
        </Card>
      </section>

      {draft && current && (
        <section>
          <SectionTitle aside={<ProvenanceTag kind="assumption">layer B · v{current.version}</ProvenanceTag>}>Company AI-adoption assumptions</SectionTitle>
          <Card className="p-6 space-y-4">
            <p className="text-sm text-graphite">
              Who does each task under each scenario. New data never changes these by itself: HR reviews and approves a new version.
              <span className="block text-xs mt-1">Current: version {current.version} · {current.updated_by}</span>
            </p>
            <div className="overflow-x-auto -mx-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-graphite">
                    <th scope="col" className="py-2 px-2 font-medium">Task</th>
                    {SCENARIOS.map(sc => <th key={sc} scope="col" className="py-2 px-2 font-medium capitalize">{sc}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {tasks.map(task => (
                    <tr key={task} className="border-t border-hairline">
                      <th scope="row" className="py-2 px-2 text-left font-normal text-ink">{draft.task_descriptions[task] ?? task}</th>
                      {SCENARIOS.map(sc => {
                        const edited = draft.scenarios[sc].tasks[task] !== current.scenarios[sc].tasks[task]
                        return (
                          <td key={sc} className="py-2 px-2">
                            <select
                              aria-label={`${sc} ${task}`}
                              value={draft.scenarios[sc].tasks[task]}
                              onChange={e => setAllocation(sc, task, e.target.value as Allocation)}
                              className={`w-full min-w-40 rounded-sm px-2 py-1.5 text-sm text-ink transition-colors duration-200 ${edited ? 'bg-marigold-tint border-2 border-marigold' : 'bg-surface border border-hairline-strong'}`}
                            >
                              {ALLOCATIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                            </select>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border-t border-hairline pt-4 space-y-3">
              <label className="block">
                <span className={label}>Why this change</span>
                <input
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  placeholder="e.g. AI now drafts entry checks, per the May 2026 snapshot"
                  className={`${inputCls} mt-1 w-full`}
                />
              </label>
              <div className="flex flex-wrap items-center gap-3">
                <button onClick={approve} disabled={busy || changed.length === 0} className={btn.primary}>
                  <CircleCheck size={16} aria-hidden="true" /> Approve as version {current.version + 1}
                </button>
                <span className="text-sm text-graphite">
                  {changed.length === 0 ? 'Change an allocation to approve a new version.' : `${changed.length} change${changed.length > 1 ? 's' : ''} waiting for approval`}
                </span>
              </div>
              {saved && <p role="status" className="text-sm text-action-ink bg-action-tint rounded-md px-3 py-2">{saved}</p>}
            </div>
          </Card>
        </section>
      )}
    </div>
  )
}
