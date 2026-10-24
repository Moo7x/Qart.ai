import { useState } from 'react'
import { useT } from '../i18n'
import { getJSON, sendJSON } from '../api'
import { useJourney } from '../state'

export type FeedbackKind =
  | 'not_my_goal'
  | 'impractical_schedule'
  | 'course_unavailable'
  | 'wrong_skill_mapping'
  | 'unsupported_claim'
  | 'wrong_number'
type Target = 'role' | 'course' | 'skill' | 'evidence' | 'explanation' | 'requirement' | 'plan'

const LABELS: Record<FeedbackKind, string> = {
  not_my_goal: 'This is not my goal',
  impractical_schedule: 'This schedule does not work for me',
  course_unavailable: 'This course is unavailable or broken',
  wrong_skill_mapping: 'The skill is wrong',
  unsupported_claim: 'The source does not support this',
  wrong_number: 'A number looks wrong',
}

// A small "report a problem" control. Preferences apply to the person at once; errors go to review.
export function ReportProblem({ kinds, targetType, targetId, page, dark = false }: { kinds: FeedbackKind[]; targetType: Target; targetId: string; page: string; dark?: boolean }) {
  const { t } = useT()
  const { profileId } = useJourney()
  const [kind, setKind] = useState<FeedbackKind>(kinds[0])
  const [message, setMessage] = useState('')
  const [sent, setSent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function send() {
    setError(null)
    try {
      const out = await sendJSON<{ explanation: string }>('/api/feedback', {
        body: { kind, target_type: targetType, target_id: targetId, page, message, profile_id: profileId },
      })
      setSent(out.explanation)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    }
  }

  return (
    <details className={`text-xs ${dark ? 'text-stone' : 'text-graphite'}`}>
      <summary className="cursor-pointer">{t('Report a problem')}</summary>
      {sent ? (
        <p className="m-0 mt-1.5">Thank you. {sent}</p>
      ) : (
        <div className="mt-1.5 flex flex-wrap items-end gap-2">
          <select value={kind} onChange={(e) => setKind(e.target.value as FeedbackKind)} className="rounded-md border border-hairline px-2 py-1 text-xs text-void">
            {kinds.map((k) => <option key={k} value={k}>{LABELS[k]}</option>)}
          </select>
          <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="What is wrong? (optional)" maxLength={1000} className="min-w-0 flex-1 rounded-md border border-hairline px-2 py-1 text-xs text-void" />
          <button type="button" className="btn" onClick={send}>{t('Send')}</button>
          {error && <span role="alert" className="text-weak">{error}</span>}
        </div>
      )}
    </details>
  )
}

type QueueItem = { id: number; kind: string; target_type: string; target_id: string; message: string; status: string; version: string; created_at: string; proposal: null | { action: string; course_id: string } }
type Release = { id: number; feedback_id: number; decision: string; action: string; evaluation: { plans?: number; plans_changed?: number; essentials_left_without_course?: string[] }; decided_at: string }
type Evaluation = { plans: number; plans_changed: number; essentials_left_without_course: string[] }

// Admin: review reports, see the regression check of a proposed correction, release or reject it.
export function FeedbackReview() {
  const [token, setToken] = useState('')
  const [data, setData] = useState<{ queue: QueueItem[]; releases: Release[] } | null>(null)
  const [checks, setChecks] = useState<Record<number, Evaluation | null>>({})
  const [error, setError] = useState<string | null>(null)
  const headers = { 'X-Admin-Token': token }

  async function load() {
    setError(null)
    try {
      setData(await getJSON(`/api/feedback`, { headers }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    }
  }
  async function evaluate(id: number) {
    const out = await getJSON<{ evaluation: Evaluation | null }>(`/api/feedback/${id}/evaluate`, { headers })
    setChecks((c) => ({ ...c, [id]: out.evaluation }))
  }
  async function decide(id: number, decision: 'accept' | 'reject') {
    await sendJSON(`/api/feedback/${id}/decide`, { body: { decision }, headers })
    await load()
  }

  return (
    <section className="card-light flex flex-col gap-3 px-6 py-5">
      <h2 className="h2">Feedback review · admin</h2>
      <p className="m-0 text-xs text-graphite">People&rsquo;s error reports wait here. A proposed correction is first run on fixed synthetic profiles for every destination role; release applies it for everyone and is logged.</p>
      <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); void load() }}>
        <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Admin token" className="rounded-md border border-hairline px-3 py-1.5 text-sm" />
        <button type="submit" className="btn" disabled={!token}>Open the queue</button>
      </form>
      {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}
      {data && (
        <>
          {data.queue.filter((q) => q.status === 'review').length === 0 && <p className="m-0 text-sm text-graphite">No reports waiting.</p>}
          {data.queue.filter((q) => q.status === 'review').map((q) => (
            <div key={q.id} className="rounded-lg border border-mist p-3 text-[13px]">
              <span className="font-semibold">#{q.id} {q.kind.replace(/_/g, ' ')}</span> · {q.target_type} {q.target_id} · seen at {q.version}
              {q.message && <div className="text-graphite">&ldquo;{q.message}&rdquo;</div>}
              <div className="mt-1.5 flex flex-wrap gap-2">
                {q.proposal && <button type="button" className="btn" onClick={() => evaluate(q.id)}>Test the correction</button>}
                <button type="button" className="btn btn-v" onClick={() => decide(q.id, 'accept')}>{q.proposal ? 'Release' : 'Mark reviewed'}</button>
                <button type="button" className="btn" onClick={() => decide(q.id, 'reject')}>Reject</button>
              </div>
              {checks[q.id] && (
                <p className="m-0 mt-1.5 text-xs">
                  Regression check: {checks[q.id]!.plans_changed} of {checks[q.id]!.plans} example plans change.{' '}
                  {checks[q.id]!.essentials_left_without_course.length > 0
                    ? `Left without a verified course: ${checks[q.id]!.essentials_left_without_course.join('; ')}.`
                    : 'No essential skill is left without a course.'}
                </p>
              )}
            </div>
          ))}
          {data.releases.length > 0 && (
            <div className="text-xs text-graphite">
              <span className="cap">Decisions</span>
              <ul className="m-0 mt-1 space-y-0.5 pl-4">
                {data.releases.map((r) => <li key={r.id}>#{r.feedback_id} {r.decision} · {r.action} · {r.decided_at.slice(0, 16)}{r.evaluation.plans ? ` · ${r.evaluation.plans_changed}/${r.evaluation.plans} example plans changed` : ''}</li>)}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  )
}
