import { useCallback, useEffect, useState } from 'react'
import {
  decideProposal,
  getOptimizerStatus,
  getPlaybook,
  getProposals,
  rollbackProposal,
  startOptimizer,
} from '../api'
import type { OptimizerProposal, OptimizerStatus, PlaybookInfo } from '../types'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-gray-100 text-gray-600',
}
const POLL_MS = 3000
const SENIOR = 'Mr Lim (senior, synthetic)'

function versionNumber(v: string): number {
  return Number(v.replace('playbook_v', '')) || 0
}

function Diff({ text }: { text: string }) {
  return (
    <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-3 overflow-x-auto max-h-80 whitespace-pre-wrap">
      {text.split('\n').map((line, i) => (
        <div
          key={i}
          className={line.startsWith('+') && !line.startsWith('+++') ? 'text-green-700 bg-green-50' : line.startsWith('-') && !line.startsWith('---') ? 'text-red-700 bg-red-50' : 'text-gray-600'}
        >
          {line || ' '}
        </div>
      ))}
    </pre>
  )
}

function Row({ label, before, after }: { label: string; before: string; after: string }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-2 text-xs">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-700">
        <span className="text-gray-400">before</span> {before}
        <br />
        <span className="text-gray-400">after</span> {after}
      </span>
    </div>
  )
}

function ProposalCard({ proposal, activeVersion, onChange }: {
  proposal: OptimizerProposal
  activeVersion: string
  onChange: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [showDiff, setShowDiff] = useState(proposal.status === 'pending')
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await fn()
      onChange()
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_STYLES[proposal.status]}`}>{proposal.status}</span>
        <span className="text-sm font-medium text-gray-800">{proposal.base_version} → {proposal.candidate_version}</span>
        {activeVersion === proposal.candidate_version && (
          <span className="text-xs px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 font-medium">active</span>
        )}
        {proposal.decided_by && (
          <span className="text-xs text-gray-400 ml-auto">{proposal.decided_by} · {proposal.decided_at}</span>
        )}
      </div>

      {proposal.rationale && <p className="text-sm text-gray-700">{proposal.rationale}</p>}

      <div className="space-y-2">
        <Row label="Development set" before={proposal.optimisation_set.before} after={proposal.optimisation_set.after} />
        <Row label="Acceptance set" before={proposal.acceptance_set.before} after={proposal.acceptance_set.after} />
        <div className="grid grid-cols-[9rem_1fr] gap-2 text-xs">
          <span className="text-gray-500">Regressions</span>
          <span className="text-gray-700">
            {proposal.regressions.length ? proposal.regressions.join(', ') : 'none'}
            <span className="text-gray-400"> (acceptance cases the current version decided correctly and this one does not)</span>
          </span>
        </div>
        <div className="text-xs text-gray-400">
          Criteria {proposal.acceptance_set.criteria_hash.slice(0, 19)}… (fixed; the optimiser cannot read or change them)
        </div>
      </div>

      {proposal.development_log && proposal.development_log.length > 0 && (
        <ul className="text-xs text-gray-500 list-disc pl-5">
          {proposal.development_log.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      )}

      <button onClick={() => setShowDiff(!showDiff)} className="text-xs text-indigo-600 hover:underline">
        {showDiff ? 'Hide changes' : 'Show changes to the playbook'}
      </button>
      {showDiff && <Diff text={proposal.diff} />}

      <div className="flex gap-2">
        {proposal.status === 'pending' && (
          <>
            <button
              disabled={busy}
              onClick={() => act(() => decideProposal(proposal.id, 'approve', SENIOR))}
              className="px-3 py-1.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700"
            >
              Approve and activate
            </button>
            <button
              disabled={busy}
              onClick={() => act(() => decideProposal(proposal.id, 'reject', SENIOR))}
              className="px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200"
            >
              Reject
            </button>
          </>
        )}
        {proposal.status === 'approved' && activeVersion === proposal.candidate_version && (
          <button
            disabled={busy}
            onClick={() => act(() => rollbackProposal(proposal.id))}
            className="px-3 py-1.5 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200"
          >
            Roll back to {proposal.rollback_to}
          </button>
        )}
      </div>
    </div>
  )
}

export default function CompanionUpdates() {
  const [playbook, setPlaybook] = useState<PlaybookInfo | null>(null)
  const [proposals, setProposals] = useState<OptimizerProposal[]>([])
  const [status, setStatus] = useState<OptimizerStatus | null>(null)
  const [showText, setShowText] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    getPlaybook().then(setPlaybook).catch(() => {})
    getProposals()
      .then(list => setProposals([...list].sort((a, b) => versionNumber(b.candidate_version) - versionNumber(a.candidate_version))))
      .catch(() => {})
    getOptimizerStatus().then(setStatus).catch(() => {})
  }, [])

  useEffect(load, [load])

  useEffect(() => {
    if (status?.state !== 'running') return
    const timer = window.setInterval(() => {
      getOptimizerStatus().then(s => {
        setStatus(s)
        if (s.state !== 'running') load()
      })
    }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [status?.state, load])

  const run = async () => {
    setError(null)
    try {
      setStatus(await startOptimizer())
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(detail ?? 'Could not start the optimiser.')
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Companion updates</h1>
        <span className="text-xs text-gray-400">A senior decides; the optimiser only proposes</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-600">Active checking procedure:</span>
          <span className="font-semibold text-indigo-700">{playbook?.active_version ?? '…'}</span>
          <button onClick={() => setShowText(!showText)} className="text-xs text-indigo-600 hover:underline ml-auto">
            {showText ? 'Hide text' : 'Show text'}
          </button>
        </div>
        {showText && playbook && (
          <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-3 whitespace-pre-wrap max-h-80 overflow-y-auto">{playbook.text}</pre>
        )}
        <p className="text-xs text-gray-500">
          The optimiser may only edit this procedure. It learns from the practice cases and their variants, never
          from the acceptance cases; a candidate is scored on the acceptance set once, after it is fixed.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-2">
        <div className="flex items-center gap-3">
          <button
            onClick={run}
            disabled={status?.state === 'running'}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
          >
            {status?.state === 'running' ? 'Optimiser running…' : 'Run the optimiser'}
          </button>
          <span className="text-xs text-gray-500">
            {status?.state === 'running' && `${status.step} (a run takes a few minutes)`}
            {status?.state === 'failed' && `Failed: ${status.error}`}
            {status?.state === 'done' && `Finished ${status.finished_at}`}
          </span>
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>

      {proposals.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-6">No proposals yet. Run the optimiser to get one.</p>
      )}
      {proposals.map(p => (
        <ProposalCard key={p.id} proposal={p} activeVersion={playbook?.active_version ?? ''} onChange={load} />
      ))}
    </div>
  )
}
