import { useEffect, useReducer, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { sendJSON, uploadFile, useApi } from '../api'
import { ProcessLog } from '../components/Activity'
import { DarkButton } from '../components/atoms'
import { useT } from '../i18n'
import { useJourney } from '../state'
import type { Extraction, PackInfo, ProfileData, Stage } from '../types'
import { CvPopup } from './onboarding/CvPopup'
import { CvStep } from './onboarding/CvStep'
import { EMPTY_DRAFT, draftReducer, toProfile } from './onboarding/draft'
import { Landing } from './onboarding/Landing'
import { SkillsStep } from './onboarding/SkillsStep'

const STEP_NAMES = ['Your CV', 'Your skills'] as const
const HELP = [
  ['You control what gets used', 'Upload a CV. We read your role and skills from it; you review every one before continuing.'],
  ['Unknown is different from missing', 'Leave a level unrated when unsure. Your matches show that uncertainty instead of treating the skill as verified.'],
] as const

/** /start: the landing page, and the two-step CV popup over it (Your CV → Your skills). "Continue"
 *  saves the profile and opens "Your work today" (or the roles, when there is no current job). */
export function Onboarding() {
  const { t } = useT()
  const navigate = useNavigate()
  const { profileId, setProfileId } = useJourney()
  const [params] = useSearchParams()
  const editing = params.get('edit') === '1' && profileId !== null
  const pack = useApi<PackInfo>('/api/pack')
  const existing = useApi<{ profile: ProfileData }>(editing ? `/api/profiles/${profileId}` : null)
  const [draft, dispatch] = useReducer(draftReducer, EMPTY_DRAFT)
  const [open, setOpen] = useState<null | 'cv' | 'form'>(editing ? 'cv' : null)
  const [step, setStep] = useState<0 | 1>(editing ? 1 : 0)
  const [dir, setDir] = useState<'fwd' | 'back'>('fwd')
  const [extraction, setExtraction] = useState<Extraction | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activity, setActivity] = useState<{ title: string; stages?: Stage[]; result?: string } | null>(null)
  const startedAt = useRef<number | null>(null) // the time-to-plan measure (src/journey/impact.py)
  const loaded = useRef(false)

  useEffect(() => {
    if (!editing || !existing.data || loaded.current) return
    dispatch({ type: 'load', profile: existing.data.profile })
    loaded.current = true
  }, [editing, existing.data])

  // Wake the GPU and embed the skill list while the person reads the CV step.
  const warmed = useRef(false)
  useEffect(() => {
    if (!open || warmed.current) return
    warmed.current = true
    sendJSON('/api/skills/warm', { body: {} }).catch(() => undefined)
  }, [open])

  const start = (how: 'cv' | 'form') => {
    startedAt.current ??= Date.now()
    setOpen(how)
  }
  const go = (to: 0 | 1) => { setDir(to > step ? 'fwd' : 'back'); setStep(to) }

  async function run(title: string, work: () => Promise<string | void>) {
    setActivity({ title: title.replace(/…$/, '') })
    setBusy(title)
    setError(null)
    try {
      const result = await work()
      setActivity((a) => (a ? { ...a, result: result ?? undefined } : a))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(null)
    }
  }

  const readCv = (file: File) =>
    run('Reading your CV…', async () => {
      const result = await uploadFile<Extraction>('/api/intake/upload', file)
      setExtraction(result)
      dispatch({ type: 'extracted', result })
      setActivity({ title: 'Reading your CV', stages: result.stages })
      go(1)
      const removed = Object.values(result.removed).reduce((a, b) => a + b, 0)
      return `${result.skills.length} skill${result.skills.length === 1 ? '' : 's'} found, each quoting your CV · ${removed} personal detail${removed === 1 ? '' : 's'} removed` +
        (result.rejected.length ? ` · ${result.rejected.length} claim${result.rejected.length === 1 ? '' : 's'} dropped: quote not in the CV` : '')
    })

  const save = () =>
    run(editing ? 'Updating your profile…' : 'Saving your profile…', async () => {
      const profile: ProfileData = {
        ...toProfile(draft),
        intake_seconds: editing ? draft.intakeSeconds : startedAt.current === null ? null : Math.round((Date.now() - startedAt.current) / 1000),
      }
      if (editing && profileId) await sendJSON(`/api/profiles/${profileId}`, { method: 'PUT', body: profile })
      else setProfileId((await sendJSON<{ id: string }>('/api/profiles', { body: profile })).id)
      navigate('/overview')
    })

  const help = HELP[step]
  return (
    <>
      <Landing onStart={() => start('cv')} onForm={() => start('form')} saved={profileId !== null} />
      {open && (
        <CvPopup onClose={() => { setOpen(null); if (editing) navigate(-1) }}>
          <section aria-label="Question" className="flex min-w-0 flex-[1.6_1_520px] flex-col gap-5">
            <div className="flex flex-col gap-2.5">
              <div role="progressbar" aria-label="Onboarding progress" aria-valuemin={1} aria-valuemax={2} aria-valuenow={step + 1} className="flex gap-1.5">
                {STEP_NAMES.map((n, i) => <span key={n} className={`h-1 flex-1 rounded-full ${i <= step ? 'bg-violet' : 'bg-[#d4d4d4]'}`} />)}
              </div>
              <span className="text-[13px] text-muted">Step {step + 1} of 2 · {t(STEP_NAMES[step])}</span>
            </div>
            {editing && existing.loading && <p role="status" className="m-0">Loading your saved answers…</p>}
            <div key={step} className={`j-step j-${dir} flex flex-col gap-4`}>
              {step === 0 ? (
                <CvStep draft={draft} dispatch={dispatch} pack={pack.data} formFirst={open === 'form'} busy={busy !== null} onFile={readCv} run={run} />
              ) : (
                <SkillsStep draft={draft} dispatch={dispatch} pack={pack.data} extraction={extraction} />
              )}
            </div>
            {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}
            <div className="flex flex-wrap items-center gap-2 border-t border-[#e5e5e5] pt-4">
              {step === 1 && <button type="button" className="q-btn q-btn-text" onClick={() => go(0)}>← Back</button>}
              <span className="flex-1" />
              {step === 0 ? (
                <>
                  <button type="button" className="q-btn q-btn-text" onClick={() => go(1)}>{t('Skip')}</button>
                  <button type="button" className="q-btn q-btn-violet" disabled={busy !== null} onClick={() => go(1)}>Continue</button>
                </>
              ) : (
                <DarkButton onClick={save} disabled={busy !== null || (editing && !loaded.current)}>Continue</DarkButton>
              )}
            </div>
          </section>
          {activity && (busy !== null || activity.stages?.length) ? (
            <aside aria-label="What is happening" className="q-card flex-[1_1_300px] self-start">
              <ProcessLog title={activity.title} running={busy !== null} label={t(busy ?? '')} stages={activity.stages} result={activity.result} />
            </aside>
          ) : (
            <aside aria-label="About this step" className="q-card flex-[1_1_300px] gap-4 self-start">
              <span className="q-kicker">Your journey · {step + 1} / 2</span>
              <h3 className="q-h3 text-[22px]">{t(help[0])}</h3>
              <p className="m-0 text-[15px] text-[#404040]">{t(help[1])}</p>
              <ol className="m-0 flex list-none flex-col gap-3 p-0">
                {['Your skills today', 'Future roles that fit', 'A plan you can follow'].map((label, i) => (
                  <li key={label} className="flex items-center gap-3">
                    <span aria-hidden="true" className="inline-flex h-9 w-9 flex-none items-center justify-center rounded-[10px] bg-assumption-bg text-sm font-semibold text-violet">{i + 1}</span>
                    <span className="text-[15px] font-medium">{t(label)}</span>
                  </li>
                ))}
              </ol>
              <p className="q-src">Public evidence. Explainable calculations. You choose the destination.</p>
            </aside>
          )}
        </CvPopup>
      )}
    </>
  )
}
