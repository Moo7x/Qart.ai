import { useState } from 'react'
import { useT } from '../i18n'
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
      <p role="status" className="m-0 text-[14px] text-graphite">
        {report.recommendation_changed ? 'The recomputed ranking, fit or pathway differs.' : 'No change to the computed ranking, fit or pathway. New evidence does not have to change your recommendation.'}
      </p>
      <details className="rounded-lg border border-hairline p-4" open>
        <summary className="cursor-pointer text-[14px] font-semibold">1 · What the source reports · {report.evidence.length} changed observations</summary>
        <div className="mt-3 max-h-[420px] overflow-auto">
          {report.evidence.length === 0 && <p className="text-[14px]">No latest observed values changed.</p>}
          {report.evidence.map((e, index) => (
            <article key={`${e.source_id}-${index}`} className="border-t border-mist py-3 text-[14px]">
              <div className="font-semibold">{e.entity} · {e.geography}</div>
              <div className="font-mono text-[13px]">{e.before ?? 'not available'} ({e.before_period ?? '—'}) → {e.after ?? 'not available'} ({e.after_period ?? '—'}) · {e.unit}</div>
              <div className="mt-1 text-[13px] text-graphite">{e.metric} · {e.comparable ? 'Same recorded method and unit' : 'New or non-comparable cell; do not treat as a measured rate of change'}</div>
              <blockquote className="mx-0 my-2 break-words border-l-2 border-hairline pl-3 text-[13px] text-graphite">{e.cited_span}</blockquote>
              <a href={e.url} target="_blank" rel="noreferrer">Open source ↗</a>
              <span className="ml-2 text-[13px] text-graphite">Published {e.published ?? 'date not supplied'}</span>
            </article>
          ))}
        </div>
      </details>
      <section className="min-w-0 overflow-x-auto">
        <h3 className="h2 mb-3">2 · Scenario emphasis → your role scores</h3>
        <p className="text-[13px] text-graphite">Your skills stay fixed. Essential weights stay fixed; their share of a normalised total can change. Expand a role for the exact calculation differences.</p>
        {report.roles.map((role) => {
          const driver = report.evidence.find((e) => e.source_id === 'anthropic_economic_index' && e.metric === 'aei_collaboration_bucket_automation_pct' && e.geography === 'GLOBAL' && e.entity.split(' ')[0] === role.soc)
          return (
          <details key={role.role_id} className="border-t border-hairline py-3">
            <summary className="cursor-pointer text-[14px]">
              <span className="font-semibold">{role.title}</span>
              <span className="ml-3 font-mono">{role.fit_before.toFixed(1)} → {role.fit_after.toFixed(1)} / 100</span>
              <span className="ml-3 text-graphite">rank {role.rank_before} → {role.rank_after}</span>
            </summary>
            <p className="text-[13px] text-graphite">Mapped occupation: {role.soc}. {driver && <>Occupation-level automation-style share (used for skills without task-level data): {driver.before ?? 'not available'}% → {driver.after ?? 'not available'}%. <a href={driver.url} target="_blank" rel="noreferrer">Source ↗</a></>}</p>
            {role.weights.length === 0 ? <p className="text-[13px] text-graphite">No requirement weights or contributions changed.</p> : (
              <ul className="space-y-3 pl-5 text-[13px]">
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
          <p className="text-[14px] text-graphite">{pathway.added.length} courses added · {pathway.removed.length} removed · {pathway.reordered ? 'order changed' : 'no reordering of the same courses'}. Your destination is unchanged.</p>
          <div className="flex flex-wrap gap-4"><PathColumn title="Before" path={pathway.before} /><PathColumn title="After · proposed" path={pathway.after} /></div>
        </section>
      ) : <p className="text-[14px]">Choose a destination on the <Link to="/roles">Roles page</Link> to compare its pathway too.</p>}
      <aside className="rounded-lg bg-fog p-4 text-[13px] leading-relaxed text-graphite">
        {report.notes.map((note) => <p key={note} className="my-1">{note}</p>)}
      </aside>
    </div>
  )
}

// One collected update: the gist and the decision first, the full comparison on request.
function ProposalCard({ proposal, busy, onDecide }: { proposal: Proposal; busy: boolean; onDecide: (d: 'accept' | 'decline') => void }) {
  const r = proposal.report
  const moved = [...r.roles].sort((x, y) => Math.abs(y.fit_after - y.fit_before) - Math.abs(x.fit_after - x.fit_before))[0]
  const changedRoles = r.roles.filter((x) => x.fit_after !== x.fit_before || x.rank_after !== x.rank_before).length
  const stats: [string, string][] = [
    ['Observations changed', String(r.evidence.length)],
    ['Your roles affected', `${changedRoles} of ${r.roles.length}`],
    ['Biggest fit change', moved ? `${moved.title}: ${moved.fit_before.toFixed(1)} → ${moved.fit_after.toFixed(1)}` : 'none'],
    ['Your plan', r.pathway ? `${r.pathway.added.length} added · ${r.pathway.removed.length} removed` : 'no destination chosen'],
  ]
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
      <dl className="m-0 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(([label, value]) => (
          <div key={label} className="border-l-2 border-violet pl-3">
            <dt className="cap">{label}</dt>
            <dd className="m-0 mt-1 text-[15px] font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
      <details>
        <summary className="cursor-pointer text-[14px] font-medium text-violet">See the full comparison</summary>
        <div className="mt-4"><Report report={r} /></div>
      </details>
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
      <p className="m-0 max-w-[760px] text-sm text-graphite">Collected evidence can propose a revision. Your roles and pathway keep their accepted evidence until you choose an update. Historical replay is separate and never changes your profile.</p>
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
