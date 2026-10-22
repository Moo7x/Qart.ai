import { useEffect, useState } from 'react'
import { getAssumptions, getSnapshotDiff, getSnapshots, ingestNextSnapshot, putAssumptions } from '../api'
import type { Allocation, CompanyAssumptions, Scenario, Snapshot, SnapshotDiff } from '../types'

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

function pct(value: number | null): string {
  return value === null ? '–' : `${value.toFixed(2)}%`
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

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Evidence & assumptions</h1>
        <span className="text-xs text-gray-400">Data informs; HR decides</span>
      </div>

      <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-700">External evidence (layer A)</h2>
          <span className="text-xs bg-blue-100 text-blue-700 border border-blue-200 px-1.5 py-0.5 rounded">evidence</span>
        </div>
        {snapshots.map(s => (
          <p key={s.id} className="text-sm text-gray-700">{s.source} · {s.release_date} release · period {s.period}</p>
        ))}
        <button
          onClick={ingest}
          disabled={busy}
          className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
        >
          Load the newer snapshot (historical data replay)
        </button>
        {message && <p className="text-xs text-gray-500">{message}</p>}

        {diff && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500">
              {diff.from_period} → {diff.to_period} · {diff.label}
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 text-left">
                  <th className="py-1">Signal</th><th>Before</th><th>After</th><th>Change</th>
                </tr>
              </thead>
              <tbody>
                {diff.changes.filter(c => c.significant).map((c, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    <td className="py-1 text-gray-700">{c.entity} · {METRICS[c.metric] ?? c.metric}{c.geo ? ` · ${c.geo}` : ''}</td>
                    <td>{pct(c.before)}</td>
                    <td>{pct(c.after)}</td>
                    <td className="font-medium">{c.relative_change === null ? '–' : `${(c.relative_change * 100).toFixed(0)}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {diff.suggested_assumption_reviews.length > 0 && (
              <div className="bg-amber-50 border border-amber-100 rounded p-3 text-xs text-amber-900 space-y-1">
                <div className="font-medium">Suggested assumption reviews</div>
                {diff.suggested_assumption_reviews.map((r, i) => (
                  <div key={i}><span className="font-mono">{r.assumption_id}</span>: {r.reason}</div>
                ))}
              </div>
            )}
            <p className="text-xs text-gray-400">{diff.note}</p>
          </div>
        )}
      </section>

      {draft && current && (
        <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-gray-700">Company AI-adoption assumptions (layer B)</h2>
            <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded">assumption</span>
            <span className="text-xs text-gray-400 ml-auto">version {current.version} · {current.updated_by}</span>
          </div>
          <p className="text-xs text-gray-500">
            Who does each task under each scenario. New data never changes these by itself: HR reviews and approves a new version.
          </p>
          {SCENARIOS.map(s => (
            <div key={s} className="space-y-1">
              <div className="text-xs font-medium text-gray-600 capitalize">{s}</div>
              {Object.keys(draft.scenarios[s].tasks).map(task => (
                <div key={task} className="flex items-center justify-between gap-3 text-xs bg-gray-50 rounded px-3 py-1.5">
                  <span className="text-gray-700">{draft.task_descriptions[task] ?? task}</span>
                  <select
                    aria-label={`${s} ${task}`}
                    value={draft.scenarios[s].tasks[task]}
                    onChange={e => setAllocation(s, task, e.target.value as Allocation)}
                    className={`border rounded px-2 py-1 bg-white ${draft.scenarios[s].tasks[task] !== current.scenarios[s].tasks[task] ? 'border-amber-400' : 'border-gray-200'}`}
                  >
                    {ALLOCATIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                  </select>
                </div>
              ))}
            </div>
          ))}
          <input
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="Why (e.g. AI now drafts entry checks, per the May 2026 snapshot)"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <button
            onClick={approve}
            disabled={busy || changed.length === 0}
            className="px-3 py-1.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          >
            Approve as version {current.version + 1}
          </button>
          {changed.length === 0 && <span className="text-xs text-gray-400 ml-2">Change an allocation to approve a new version.</span>}
          {saved && <p className="text-xs text-green-700">{saved}</p>}
        </section>
      )}
    </div>
  )
}
