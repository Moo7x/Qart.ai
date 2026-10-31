import { ClipboardList } from 'lucide-react'
import { useState } from 'react'
import { sendJSON, useApi } from '../api'
import { CvPopup } from '../pages/onboarding/CvPopup'
import { useJourney } from '../state'
import type { Question } from '../types'
import { Claim, DarkButton, Serif } from './atoms'
import { LevelPicker } from './LevelPicker'
import { Loading, Problem } from './ui'

const MAX_ANSWERS = 3 // the server returns the 3 questions that would change the person's options most

/** "Increase the accuracy of your results": the unrated skills whose answer would change the
 *  person's options most (GET /questions), answered in a popup. Each answer is saved as the
 *  person's own rating (POST /answer), never a verified level; `onDone` lets the page refresh. */
export function SkillSurvey({ onDone }: { onDone: () => void }) {
  const { profileId, scenario } = useJourney()
  const questions = useApi<Question[]>(profileId ? `/api/profiles/${profileId}/questions?scenario=${scenario}` : null)
  const [open, setOpen] = useState(false)
  if (!profileId || questions.loading || questions.error || !questions.data?.length) return null
  const n = questions.data.length
  return (
    <section aria-label="Increase the accuracy of your results" className="q-card flex-row flex-wrap items-center gap-4 px-6 py-5">
      <span aria-hidden="true" className="inline-flex h-12 w-12 flex-none items-center justify-center rounded-2xl bg-assumption-bg text-violet"><ClipboardList size={22} /></span>
      <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-1">
        <h2 className="q-h3">Increase the accuracy of your results</h2>
        <p className="m-0 text-sm text-[#404040]">
          {n === 1 ? 'One skill' : `${n} skills`} your roles depend on {n === 1 ? 'is' : 'are'} not rated yet: {questions.data.map((q) => q.skill_name).join(', ')}. Answer a few questions; each answer is your own rating and updates your radar and your options.
        </p>
      </div>
      <DarkButton onClick={() => setOpen(true)}>Answer the questions</DarkButton>
      {open && profileId && (
        <SurveyPopup profileId={profileId} scenario={scenario} onClose={() => { setOpen(false); questions.reload(); onDone() }} />
      )}
    </section>
  )
}

function SurveyPopup({ profileId, scenario, onClose }: { profileId: string; scenario: string; onClose: () => void }) {
  const questions = useApi<Question[]>(`/api/profiles/${profileId}/questions?scenario=${scenario}`)
  const [answered, setAnswered] = useState(0)
  const [skipped, setSkipped] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const left = (questions.data ?? []).filter((q) => !skipped.includes(q.skill))
  const current = answered < MAX_ANSWERS ? left[0] : undefined

  async function answer(level: number) {
    if (!current) return
    setBusy(true)
    setError(null)
    try {
      await sendJSON(`/api/profiles/${profileId}/answer`, { body: { skill: current.skill, level } })
      setAnswered((a) => a + 1)
      questions.reload() // the next best question is re-ranked with this answer
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <CvPopup onClose={onClose}>
      <section aria-label="Skills questions" className="flex min-w-0 flex-[1.6_1_520px] flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2.5">
          <h2 id="j-title" className="m-0 text-[clamp(26px,4vw,38px)] font-medium leading-[1.08] tracking-[-0.02em]">
            Fill in for more <Serif>accuracy</Serif>
          </h2>
          <Claim>each answer is your own rating</Claim>
        </div>
        {questions.loading && <Loading what="the next question" />}
        {questions.error && <Problem what="the next question" message={questions.error} onRetry={questions.reload} />}
        {current ? (
          <div key={current.skill} className="j-step j-fwd flex flex-col gap-3">
            <span className="q-kicker">Question {answered + skipped.length + 1} · up to {MAX_ANSWERS}</span>
            <h3 className="q-h3">How would you rate your {current.skill_name}?</h3>
            <p className="m-0 text-sm text-[#404040]">{current.effect}</p>
            <div className="max-w-[420px]">
              <LevelPicker skill={current.skill} level={null} label={`Your level in ${current.skill_name}`} disabled={busy} allowUnsure={false} onChange={(level) => { if (level !== null) void answer(level) }} />
            </div>
            {error && <p role="alert" className="m-0 text-xs text-weak">{error}</p>}
          </div>
        ) : (
          !questions.loading && (
            <p className="m-0 text-[15px]">
              {answered ? `Thank you: ${answered} answer${answered === 1 ? '' : 's'} saved. Your radar and your options now use ${answered === 1 ? 'it' : 'them'}.` : 'No question is left to ask right now.'}
            </p>
          )
        )}
        <div className="flex flex-wrap items-center gap-2 border-t border-[#e5e5e5] pt-4">
          {current && <button type="button" className="q-btn q-btn-text" disabled={busy} onClick={() => setSkipped((s) => [...s, current.skill])}>Skip this one</button>}
          <span className="flex-1" />
          <DarkButton onClick={onClose} disabled={busy}>Done</DarkButton>
        </div>
      </section>
      <aside aria-label="About these questions" className="q-card flex-[1_1_300px] gap-3 self-start">
        <span className="q-kicker">Why we ask</span>
        <h3 className="q-h3 text-[22px]">Unknown is different from missing</h3>
        <p className="m-0 text-[15px] text-[#404040]">
          These are the skills whose answer would change your options most. Pick the highest sentence that is true for your work in the last two years. Your answer updates “Your skills as AI moves” and My options; it is your own rating, not a test.
        </p>
      </aside>
    </CvPopup>
  )
}
