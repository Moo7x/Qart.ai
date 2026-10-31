import { useState } from 'react'
import { useT } from '../i18n'
import { sendJSON } from '../api'
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
