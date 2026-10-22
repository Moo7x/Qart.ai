import { useCallback, useEffect, useState } from 'react'
import {
  decideProposal,
  getOptimizerStatus,
  getPlaybook,
  getProposals,
  rollbackProposal,
  startOptimizer,
} from '../api'
import { ArrowRight, Check, ChevronDown, ChevronUp, RotateCcw, Sparkles, X } from 'lucide-react'
import type { OptimizerProposal, OptimizerStatus, PlaybookInfo } from '../types'
import { btn, Card, EmptyState, Highlight, label, PageHeader, SectionTitle, Tag, type Tone } from '../ui'

const STATUS_TONE: Record<string, Tone> = { pending: 'marigold', approved: 'action', rejected: 'linen' }
const POLL_MS = 3000
const SENIOR = 'Mr Lim (senior, synthetic)'

function versionNumber(v: string): number {
  return Number(v.replace('playbook_v', '')) || 0
}

function Diff({ text }: { text: string }) {
  return (
    <pre className="text-xs font-mono bg-linen rounded-md p-3 overflow-x-auto max-h-80 whitespace-pre-wrap">
      {text.split('\n').map((line, i) => {
        const added = line.startsWith('+') && !line.startsWith('+++')
        const removed = line.startsWith('-') && !line.startsWith('---')
        return (
          <div key={i} className={added ? 'bg-action-tint text-action-ink' : removed ? 'bg-coral-tint text-coral-ink line-through decoration-coral-ink/40' : 'text-graphite'}>
            {line || ' '}
          </div>
        )
      })}
    </pre>
  )
}

/** Before → after for one evaluation set: counts on synthetic variants, never a score. */
function Row({ label: name, before, after }: { label: string; before: string; after: string }) {
  return (
    <div className="rounded-md bg-canvas px-4 py-3">
      <div className={label}>{name}</div>
      <div className="mt-1 flex items-center gap-2 text-ink tabular-nums">
        <span className="text-graphite">{before}</span>
        <ArrowRight size={14} className="text-graphite" aria-hidden="true" />
        <span className="font-semibold">{after}</span>
      </div>
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
    <Card className="p-6 space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Tag tone={STATUS_TONE[proposal.status] ?? 'linen'}>{proposal.status}</Tag>
        <span className="font-semibold text-ink">{proposal.base_version} → {proposal.candidate_version}</span>
        {activeVersion === proposal.candidate_version && <Tag tone="action" icon={Check}>active</Tag>}
        {proposal.decided_by && <span className="text-xs text-graphite ml-auto">{proposal.decided_by} · {proposal.decided_at}</span>}
      </div>

      {proposal.rationale && <p className="font-serif text-lg leading-[1.5] text-ink">{proposal.rationale}</p>}

      <div className="grid gap-3 sm:grid-cols-2">
        <Row label="Development set" before={proposal.optimisation_set.before} after={proposal.optimisation_set.after} />
        <Row label="Acceptance set" before={proposal.acceptance_set.before} after={proposal.acceptance_set.after} />
      </div>
      <div className="text-sm">
        <span className="text-graphite">Regressions: </span>
        <span className={proposal.regressions.length ? 'text-coral-ink font-medium' : 'text-ink'}>{proposal.regressions.length ? proposal.regressions.join(', ') : 'none'}</span>
        <span className="block text-xs text-graphite mt-0.5">Acceptance cases the current version decided correctly and this one does not.</span>
      </div>
      <p className="text-xs text-graphite">
        Criteria <span className="font-mono">{proposal.acceptance_set.criteria_hash.slice(0, 19)}…</span> (fixed; the optimiser cannot read or change them)
      </p>

      {proposal.development_log && proposal.development_log.length > 0 && (
        <ul className="text-sm text-graphite list-disc pl-5 space-y-0.5">
          {proposal.development_log.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      )}

      <div>
        <button onClick={() => setShowDiff(!showDiff)} aria-expanded={showDiff} className="inline-flex items-center gap-1 text-sm text-action-ink hover:underline">
          {showDiff ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
          {showDiff ? 'Hide changes' : 'Show changes to the playbook'}
        </button>
        {showDiff && <div className="mt-2"><Diff text={proposal.diff} /></div>}
      </div>

      {proposal.status === 'pending' && (
        <div className="border-t border-hairline pt-4">
          <div className={`${label} mb-2`}>Your decision</div>
          {/* Equal weight on purpose: the senior decides; the UI must not push toward approving. */}
          <div className="grid grid-cols-2 gap-2 max-w-md">
            <button disabled={busy} onClick={() => act(() => decideProposal(proposal.id, 'approve', SENIOR))} className={btn.outline}>
              <Check size={16} aria-hidden="true" /> Approve and activate
            </button>
            <button disabled={busy} onClick={() => act(() => decideProposal(proposal.id, 'reject', SENIOR))} className={btn.outline}>
              <X size={16} aria-hidden="true" /> Reject
            </button>
          </div>
        </div>
      )}
      {proposal.status === 'approved' && activeVersion === proposal.candidate_version && (
        <button disabled={busy} onClick={() => act(() => rollbackProposal(proposal.id))} className={btn.outline}>
          <RotateCcw size={16} aria-hidden="true" /> Roll back to {proposal.rollback_to}
        </button>
      )}
    </Card>
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
    <div className="max-w-3xl mx-auto space-y-8">
      <PageHeader
        title={<>The optimiser proposes, you <Highlight tone="action">decide</Highlight></>}
        intro="Each proposal changes only the companion's checking procedure, with the evidence for and against it."
      />

      <section>
        <SectionTitle aside={
          <button onClick={() => setShowText(!showText)} aria-expanded={showText} className="text-sm text-action-ink hover:underline">
            {showText ? 'Hide text' : 'Show text'}
          </button>
        }>Active checking procedure</SectionTitle>
        <Card className="p-6 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-[22px] font-semibold tracking-[-0.01em] text-ink font-mono">{playbook?.active_version ?? '…'}</span>
            <button onClick={run} disabled={status?.state === 'running'} className={`${btn.primary} ml-auto`}>
              <Sparkles size={16} aria-hidden="true" /> {status?.state === 'running' ? 'Optimiser running…' : 'Run the optimiser'}
            </button>
          </div>
          {status && status.state !== 'idle' && (
            <p role="status" className={`text-sm rounded-md px-3 py-2 ${status.state === 'failed' ? 'bg-coral-tint text-coral-ink' : 'bg-linen text-graphite'}`}>
              {status.state === 'running' && `${status.step} (a run takes a few minutes)`}
              {status.state === 'failed' && `Failed: ${status.error}`}
              {status.state === 'done' && `Finished ${status.finished_at}`}
            </p>
          )}
          {error && <p role="alert" className="text-sm bg-coral-tint text-coral-ink rounded-md px-3 py-2">{error}</p>}
          {showText && playbook && (
            <pre className="text-xs font-mono bg-linen rounded-md p-3 whitespace-pre-wrap max-h-80 overflow-y-auto text-ink">{playbook.text}</pre>
          )}
          <p className="text-xs text-graphite">
            The optimiser may only edit this procedure. It learns from the practice cases and their variants, never
            from the acceptance cases; a candidate is scored on the acceptance set once, after it is fixed.
          </p>
        </Card>
      </section>

      <section>
        <SectionTitle>Proposals</SectionTitle>
        {proposals.length === 0 ? (
          <EmptyState title="No proposals yet">Run the optimiser to get one.</EmptyState>
        ) : (
          <div className="space-y-4">
            {proposals.map(p => (
              <ProposalCard key={p.id} proposal={p} activeVersion={playbook?.active_version ?? ''} onChange={load} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
