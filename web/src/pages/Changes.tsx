import { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatWhen, getJSON, sendJSON, useApi } from '../api'
import { ScenarioSwitch } from '../components/journey'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { AutomationBasis, ChangeReport, ChangesResponse, PathSummary, Proposal } from '../types'
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

function PathColumn({ title, path }: { title: string; path: PathSummary }) {
  return (
    <div className="min-w-0 flex-1 rounded-lg border border-hairline p-4">
      <h3 className="m-0 text-base">{title}</h3>
      <p className="text-sm text-graphite">{path.hours} h · about {path.weeks} weeks</p>
      <ol className="space-y-2 pl-5 text-sm">
        {path.courses.map((course) => <li key={course.id}><a href={course.url} target="_blank" rel="noreferrer">{course.title}</a></li>)}
      </ol>
      {path.essential_gaps.length > 0 && <p className="text-sm text-weak">Essentials still to build: {path.essential_gaps.join(', ')}.</p>}
    </div>
  )
}

function Report({ report }: { report: ChangeReport }) {
  const pathway = report.pathway
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="h2">{report.before_label} → {report.after_label}</h2>
        <span className="tag bg-estimate-bg text-estimate">{report.mode === 'replay' ? 'Historical source replay' : 'Update proposal'} · {report.scenario}</span>
      </div>
      <p role="status" className="m-0 text-sm text-graphite">
        {report.recommendation_changed ? 'The recomputed ranking, fit or pathway differs.' : 'No change to the computed ranking, fit or pathway. New evidence does not have to change your recommendation.'}
      </p>
      <details className="rounded-lg border border-hairline p-4" open>
        <summary className="cursor-pointer text-sm font-semibold">1 · What the source reports · {report.evidence.length} changed observations</summary>
        <div className="mt-3 max-h-[420px] overflow-auto">
          {report.evidence.length === 0 && <p className="text-sm">No latest observed values changed.</p>}
          {report.evidence.map((e, index) => (
            <article key={`${e.source_id}-${index}`} className="border-t border-mist py-3 text-sm">
              <div className="font-semibold">{e.entity} · {e.geography}</div>
              <div className="font-mono text-xs">{e.before ?? 'not available'} ({e.before_period ?? '—'}) → {e.after ?? 'not available'} ({e.after_period ?? '—'}) · {e.unit}</div>
              <div className="mt-1 text-xs text-graphite">{e.metric} · {e.comparable ? 'Same recorded method and unit' : 'New or non-comparable cell; do not treat as a measured rate of change'}</div>
              <blockquote className="mx-0 my-2 break-words border-l-2 border-hairline pl-3 text-xs text-graphite">{e.cited_span}</blockquote>
              <a href={e.url} target="_blank" rel="noreferrer">Open source ↗</a>
              <span className="ml-2 text-xs text-graphite">Published {e.published ?? 'date not supplied'}</span>
            </article>
          ))}
        </div>
      </details>
      <section className="min-w-0 overflow-x-auto">
        <h3 className="h2 mb-3">2 · Scenario emphasis → your role scores</h3>
        <p className="text-xs text-graphite">Your skills stay fixed. Essential weights stay fixed; their share of a normalised total can change. Expand a role for the exact calculation differences.</p>
        {report.roles.map((role) => {
          const driver = report.evidence.find((e) => e.source_id === 'anthropic_economic_index' && e.metric === 'aei_collaboration_bucket_automation_pct' && e.geography === 'GLOBAL' && e.entity.split(' ')[0] === role.soc)
          return (
          <details key={role.role_id} className="border-t border-hairline py-3">
            <summary className="cursor-pointer text-sm">
              <span className="font-semibold">{role.title}</span>
              <span className="ml-3 font-mono">{role.fit_before.toFixed(1)} → {role.fit_after.toFixed(1)} / 100</span>
              <span className="ml-3 text-graphite">rank {role.rank_before} → {role.rank_after}</span>
            </summary>
            <p className="text-xs text-graphite">Mapped occupation: {role.soc}. {driver && <>Occupation-level automation-style share (used for skills without task-level data): {driver.before ?? 'not available'}% → {driver.after ?? 'not available'}%. <a href={driver.url} target="_blank" rel="noreferrer">Source ↗</a></>}</p>
            {role.weights.length === 0 ? <p className="text-xs text-graphite">No requirement weights or contributions changed.</p> : (
              <ul className="space-y-3 pl-5 text-xs">
                {role.weights.map((w) => (
                  <li key={w.skill}>
                    <span className="font-semibold">{w.name}{w.essential ? ' · essential' : ''}</span>
                    <div className="font-mono">Weight {w.before.toFixed(4)} → {w.after.toFixed(4)} · fit points {w.points_before.toFixed(4)} → {w.points_after.toFixed(4)}</div>
                    <div className="font-mono text-graphite">Observed automation-style share: {shareText(w.share_before, w.basis_before)} → {shareText(w.share_after, w.basis_after)}</div>
                    <div className="text-graphite">{w.reason} Scenario rule, not an observed change in your ability.</div>
                  </li>
                ))}
              </ul>
            )}
          </details>
          )
        })}
      </section>
      {pathway ? (
        <section>
          <h3 className="h2">3 · Your selected pathway · {pathway.title}</h3>
          <p className="text-sm text-graphite">{pathway.added.length} courses added · {pathway.removed.length} removed · {pathway.reordered ? 'order changed' : 'no reordering of the same courses'}. Your destination is unchanged.</p>
          <div className="flex flex-wrap gap-4"><PathColumn title="Before" path={pathway.before} /><PathColumn title="After · proposed" path={pathway.after} /></div>
        </section>
      ) : <p className="text-sm">Choose a destination on the <Link to="/roles">Roles page</Link> to compare its pathway too.</p>}
      <aside className="rounded-lg bg-fog p-4 text-xs leading-relaxed text-graphite">
        {report.notes.map((note) => <p key={note} className="my-1">{note}</p>)}
      </aside>
    </div>
  )
}

export function Changes() {
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
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div><span className="eyebrow">What changed · from evidence to your decision</span><h1 className="h1 mt-2">See the difference, then choose</h1></div>
        <ScenarioSwitch />
      </header>
      <p className="m-0 max-w-[760px] text-sm text-graphite">Collected evidence can propose a revision. Your roles and pathway keep their accepted evidence until you choose an update. Historical replay is separate and never changes your profile.</p>
      {changes.loading && !changes.data && <Loading what="evidence changes" />}
      {changes.error && <Problem what="change history" message={changes.error} onRetry={changes.reload} />}
      {message && <p role="status" className="rounded-md bg-fog p-3 text-sm">{message}</p>}
      <section className="card-light p-5">
        <h2 className="h2">Collected updates</h2>
        {proposals.length === 0 && <p className="text-sm text-graphite">No proposals yet. A genuinely new observation can create one; a quiet scheduled check is a valid no-change result.</p>}
        {proposals.map((proposal) => (
          <details key={proposal.id} className="mt-4 border-t border-hairline pt-4" open={proposal.actionable}>
            <summary className="mb-4 cursor-pointer text-sm">{formatWhen(proposal.created_at)} · {proposal.status}{!proposal.actionable && proposal.status === 'pending' ? ' · replaced by newer evidence, profile or calculation rules' : ''}</summary>
            <Report report={proposal.report} />
            {proposal.actionable && <div className="mt-4 flex flex-wrap gap-3">
              <button className="btn btn-v" disabled={busy} onClick={() => decide(proposal, 'accept')}>Use this evidence for both scenarios</button>
              <button className="btn" disabled={busy} onClick={() => decide(proposal, 'decline')}>Decline this proposal</button>
            </div>}
          </details>
        ))}
      </section>
      <section className="card-light flex flex-col gap-4 p-5">
        <div><h2 className="h2">Replay genuine historical observations</h2><p className="mb-0 text-sm text-graphite">Select saved observation periods. These are not necessarily separate publication releases. Other reference data stays fixed.</p></div>
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
