import { useState } from 'react'
import { useT } from '../i18n'
import { Link } from 'react-router-dom'
import { formatWhen, getJSON, sendJSON, useApi } from '../api'
import { ScenarioSwitch } from '../components/journey'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { AutomationBasis, ChangeReport, ChangesResponse, Proposal } from '../types'
import { NeedProfile } from './Roles'

const CHANGE_POLL_MS = 60_000
const SOURCE_NAMES: Record<string, string> = {
  anthropic_economic_index: 'Anthropic Economic Index · AI use',
  dosm_job_market_insights: 'DOSM Job Market Insights · advertised demand',
}

const BASIS_LABEL: Record<AutomationBasis, string> = {
  task: 'linked O*NET tasks',
  occupation: 'occupation level',
  none: 'no observation',
}

function shareText(share: number | null, basis: AutomationBasis) {
  return share === null ? BASIS_LABEL.none : `${share.toFixed(1)}% (${BASIS_LABEL[basis]})`
}

const EVIDENCE_SHOWN = 3

// A change in plain words: what the source reported, what it does to your roles, what it means
// for your plan. The exact weights stay one click away.
function Report({ report }: { report: ChangeReport }) {
  const pathway = report.pathway
  const moved = report.roles.filter((r) => r.rank_after !== r.rank_before || Math.abs(r.fit_after - r.fit_before) >= 0.05)
  const still = report.roles.length - moved.length
  return (
    <div className="flex flex-col gap-5">
      <ol className="m-0 grid list-none gap-4 p-0 lg:grid-cols-3">
        <li className="flex flex-col gap-2 rounded-xl border border-line bg-paper p-4">
          <span className="cap">1 · What the source reported</span>
          {report.evidence.length === 0 && <span className="text-[14px]">No value changed.</span>}
          {report.evidence.slice(0, EVIDENCE_SHOWN).map((e, i) => (
            <span key={`${e.source_id}-${i}`} className="text-[14px]">
              <b>{e.entity}</b>: {e.before ?? 'none'} → <b>{e.after ?? 'none'}</b> {e.unit}
              <a className="ml-1 text-[12px]" href={e.url} target="_blank" rel="noreferrer">source ↗</a>
            </span>
          ))}
          {report.evidence.length > EVIDENCE_SHOWN && <span className="text-[12px] text-graphite">and {report.evidence.length - EVIDENCE_SHOWN} more values</span>}
        </li>
        <li className="flex flex-col gap-2 rounded-xl border border-line bg-paper p-4">
          <span className="cap">2 · What it does to your roles</span>
          {moved.length === 0 && <span className="text-[14px]">No role moved: same fit, same order.</span>}
          {moved.map((r) => (
            <span key={r.role_id} className="flex flex-wrap items-baseline justify-between gap-2 text-[14px]">
              <span className="font-medium">{r.title}</span>
              <span className="font-mono text-[13px]">
                fit {r.fit_before.toFixed(0)} → <b className={r.fit_after > r.fit_before ? 'text-rising' : r.fit_after < r.fit_before ? 'text-weak' : ''}>{r.fit_after.toFixed(0)}</b>
                {r.rank_after !== r.rank_before && <span className={`ml-2 tag ${r.rank_after < r.rank_before ? 'bg-[#e8f6ee] text-rising' : 'bg-weak-bg text-weak'}`}>#{r.rank_before} → #{r.rank_after}</span>}
              </span>
            </span>
          ))}
          {still > 0 && moved.length > 0 && <span className="text-[12px] text-graphite">{still} other role{still === 1 ? '' : 's'} unchanged</span>}
        </li>
        <li className="flex flex-col gap-2 rounded-xl border border-line bg-paper p-4">
          <span className="cap">3 · What it means for your plan</span>
          {!pathway && <span className="text-[14px]">Choose a destination on the <Link to="/roles">Roles page</Link> to see this.</span>}
          {pathway && pathway.added.length === 0 && pathway.removed.length === 0 && !pathway.reordered && (
            <span className="text-[14px]">Your plan for {pathway.title} stays the same: {pathway.after.courses.length} courses, {pathway.after.hours} h.</span>
          )}
          {pathway && (pathway.added.length > 0 || pathway.removed.length > 0 || pathway.reordered) && (
            <>
              <span className="text-[14px]">For {pathway.title}: {pathway.before.hours} h → <b>{pathway.after.hours} h</b></span>
              {pathway.added.length > 0 && <span className="text-[13px] text-rising">Added: {pathway.after.courses.filter((c) => pathway.added.includes(c.id)).map((c) => c.title).join(', ')}</span>}
              {pathway.removed.length > 0 && <span className="text-[13px] text-weak">Removed: {pathway.before.courses.filter((c) => pathway.removed.includes(c.id)).map((c) => c.title).join(', ')}</span>}
              {pathway.reordered && <span className="text-[13px] text-graphite">Same courses in a new order.</span>}
            </>
          )}
        </li>
      </ol>
      <details className="text-[13px]">
        <summary className="cursor-pointer text-graphite">Exact calculation: every weight that moved</summary>
        <div className="mt-3 flex flex-col gap-3">
          {report.roles.filter((r) => r.weights.length > 0).map((role) => (
            <div key={role.role_id} className="border-t border-line pt-2">
              <span className="font-semibold">{role.title}</span>
              <ul className="m-0 mt-1 flex flex-col gap-1 pl-5">
                {role.weights.map((w) => (
                  <li key={w.skill}>{w.name}{w.essential ? ' · essential' : ''}: weight {w.before.toFixed(2)} → {w.after.toFixed(2)}, AI share {shareText(w.share_before, w.basis_before)} → {shareText(w.share_after, w.basis_after)}</li>
                ))}
              </ul>
            </div>
          ))}
          {report.notes.map((note) => <p key={note} className="m-0 text-graphite">{note}</p>)}
        </div>
      </details>
    </div>
  )
}

// One collected update: the gist and the decision first, the full comparison on request.
function ProposalCard({ proposal, busy, onDecide }: { proposal: Proposal; busy: boolean; onDecide: (d: 'accept' | 'decline') => void }) {
  const r = proposal.report
  return (
    <article className="flex flex-col gap-5 rounded-md border border-line bg-paper p-5 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="font-mono text-[12px] text-graphite">{formatWhen(proposal.created_at)} · {r.before_label} → {r.after_label}</span>
          <h3 className="m-0 text-[20px] font-semibold leading-snug tracking-tight">
            {r.recommendation_changed ? 'New evidence changes your results' : 'New evidence, your results stay the same'}
          </h3>
          {!proposal.actionable && proposal.status === 'pending' && <span className="text-[13px] text-graphite">Replaced by newer evidence, profile or calculation rules.</span>}
        </div>
        {proposal.actionable ? (
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-v min-h-[44px]" disabled={busy} onClick={() => onDecide('accept')}>Use this evidence</button>
            <button className="btn min-h-[44px]" disabled={busy} onClick={() => onDecide('decline')}>Decline</button>
          </div>
        ) : <span className="tag bg-mist text-graphite">{proposal.status}</span>}
      </header>
      <Report report={r} />
    </article>
  )
}

export function Changes() {
  const { t } = useT()
  const { profileId, scenario } = useJourney()
  const changes = useApi<ChangesResponse>(profileId ? `/api/profiles/${profileId}/changes` : null, CHANGE_POLL_MS)
  const [source, setSource] = useState('')
  const [before, setBefore] = useState('')
  const [after, setAfter] = useState('')
  const [preview, setPreview] = useState<ChangeReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  if (!profileId) return <NeedProfile />
  const available = changes.data?.replay_sources.filter((s) => s.periods.length >= 2) ?? []
  const sourceId = source || available[0]?.source_id || ''
  const periods = available.find((s) => s.source_id === sourceId)?.periods ?? []
  const beforePeriod = before || periods[periods.length - 2] || ''
  const afterPeriod = after || periods[periods.length - 1] || ''
  const proposals = changes.data?.proposals.filter((p) => p.scenario === scenario) ?? []

  async function replay() {
    setBusy(true); setMessage(null)
    try {
      const query = new URLSearchParams({ source_id: sourceId, before: beforePeriod, after: afterPeriod, scenario })
      setPreview(await getJSON<ChangeReport>(`/api/profiles/${profileId}/changes/replay?${query}`))
    } catch (error) { setMessage(error instanceof Error ? error.message : String(error)) }
    finally { setBusy(false) }
  }

  async function decide(proposal: Proposal, decision: 'accept' | 'decline') {
    setBusy(true); setMessage(null)
    try {
      await sendJSON(`/api/profiles/${profileId}/changes/${proposal.id}`, { body: { decision } })
      setMessage(decision === 'accept' ? 'Evidence accepted for both scenarios. Your goal and skill claims are unchanged.' : 'Proposal declined. Your accepted journey is unchanged.')
      changes.reload()
    } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); changes.reload() }
    finally { setBusy(false) }
  }

  return (
    <main className="page">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div><span className="eyebrow">What changed · from evidence to your decision</span><h1 className="h1 mt-2">{t('See the difference, then choose')}</h1></div>
        <ScenarioSwitch />
      </header>
      <p className="m-0 max-w-[760px] text-sm text-graphite">When a source publishes new data, we recompute your roles and plan and show you the difference here. Nothing changes until you accept.</p>
      {changes.loading && !changes.data && <Loading what="evidence changes" />}
      {changes.error && <Problem what="change history" message={changes.error} onRetry={changes.reload} />}
      {message && <p role="status" className="rounded-md bg-fog p-3 text-sm">{message}</p>}
      <section className="panel">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="h2">Updates for you</h2>
          <span className="text-[13px] text-graphite">{proposals.filter((x) => x.actionable).length} waiting for your decision · {proposals.length} in total</span>
        </div>
        {proposals.length === 0 && (
          <p className="m-0 max-w-[760px] text-[14px] text-graphite">
            Nothing to decide right now. When a source publishes new data that changes your results, it appears here as a card you can accept or decline. A scheduled check that finds nothing new is a normal result.
          </p>
        )}
        <div className="flex flex-col gap-4">
          {proposals.map((proposal) => <ProposalCard key={proposal.id} proposal={proposal} busy={busy} onDecide={(d) => decide(proposal, d)} />)}
        </div>
      </section>
      <section className="panel min-w-0">
        <div><h2 className="h2">Replay past data: what would have changed?</h2><p className="mb-0 mt-1 text-[14px] text-graphite">Select saved observation periods. These are not necessarily separate publication releases. Other reference data stays fixed.</p></div>
        {available.length === 0 ? <p className="text-sm">At least two saved periods from a supported source are needed. Collect evidence on the Live intelligence page first.</p> : <>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-0 flex-col gap-1 text-xs">Source<select className="min-h-[40px] max-w-full rounded-md border border-hairline bg-white p-2 text-sm" value={sourceId} onChange={(e) => { setSource(e.target.value); setBefore(''); setAfter(''); setPreview(null) }}>{available.map((s) => <option key={s.source_id} value={s.source_id}>{SOURCE_NAMES[s.source_id] ?? s.source_id}</option>)}</select></label>
            <label className="flex flex-col gap-1 text-xs">Before<select className="min-h-[40px] rounded-md border border-hairline p-2 text-sm" value={beforePeriod} onChange={(e) => { setBefore(e.target.value); setPreview(null) }}>{periods.map((p) => <option key={p}>{p}</option>)}</select></label>
            <label className="flex flex-col gap-1 text-xs">After<select className="min-h-[40px] rounded-md border border-hairline p-2 text-sm" value={afterPeriod} onChange={(e) => { setAfter(e.target.value); setPreview(null) }}>{periods.map((p) => <option key={p}>{p}</option>)}</select></label>
            <button className="btn btn-v" disabled={busy || beforePeriod >= afterPeriod} onClick={replay}>{busy ? 'Computing…' : 'Compare saved evidence'}</button>
          </div>
          {preview && preview.scenario === scenario && <Report report={preview} />}
        </>}
      </section>
    </main>
  )
}
