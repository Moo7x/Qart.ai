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
import { EMPTY_DRAFT, draftReducer, toProfile, type Draft } from './onboarding/draft'
import { Landing } from './onboarding/Landing'

/** /start: the landing page, and the CV popup over it. "Continue" saves the profile, with each
 *  level read from the CV as a claim, and opens the Overview. */
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

  return (
    <>
      <Landing onStart={() => start('cv')} saved={profileId !== null} />
      {open && (
        <CvPopup onClose={() => { setOpen(null); if (editing) navigate(-1) }}>
          <section aria-label="Your CV" className="flex min-w-0 flex-[1.6_1_520px] flex-col gap-5">
            {editing && existing.loading && <p role="status" className="m-0">Loading your saved answers…</p>}
            <div className="flex flex-col gap-4">
              <CvStep draft={draft} dispatch={dispatch} pack={pack.data} formFirst={open === 'form'} busy={busy !== null} onFile={readCv} run={run} />
            </div>
            <ReadSummary draft={draft} extraction={extraction} pack={pack.data} />
            {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}
            <div className="flex flex-wrap items-center gap-2 border-t border-[#e5e5e5] pt-4">
              <span className="text-[13px] text-muted">Every level is your own claim. You can rate more skills later on My options.</span>
              <span className="flex-1" />
              <DarkButton onClick={save} disabled={busy !== null || (editing && !loaded.current)}>Continue</DarkButton>
            </div>
          </section>
          {activity && (busy !== null || activity.stages?.length) ? (
            <aside aria-label="What is happening" className="q-card flex-[1_1_300px] self-start">
              <ProcessLog title={activity.title} running={busy !== null} label={t(busy ?? '')} stages={activity.stages} result={activity.result} />
            </aside>
          ) : (
            <aside aria-label="About this step" className="q-card flex-[1_1_300px] gap-4 self-start">
              <span className="q-kicker">Your journey</span>
              <h3 className="q-h3 text-[22px]">{t('You control what gets used')}</h3>
              <p className="m-0 text-[15px] text-[#404040]">Upload a CV. We read your role and skills from it, each with the sentence it came from, and remove personal details first.</p>
              <ol className="m-0 flex list-none flex-col gap-3 p-0">
                {['Your overview', 'Roles that fit you', 'A plan you can follow'].map((label, i) => (
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

/** What was read from the CV (or added in the form), before saving: every skill with its sentence. */
function ReadSummary({ draft, extraction, pack }: { draft: Draft; extraction: Extraction | null; pack: PackInfo | null }) {
  const skills = Object.entries(draft.skills)
  if (skills.length === 0) return null
  const name = (id: string) => pack?.skills.find((s) => s.id === id)?.name ?? id
  const role = pack?.current_roles.find((r) => r.id === draft.role)?.title
  const removed = extraction ? Object.values(extraction.removed).reduce((a, b) => a + b, 0) : null
  return (
    <section aria-label="What we read" className="flex flex-col gap-2 rounded-2xl border border-[#e5e5e5] bg-white px-4 py-3.5">
      <span className="text-[15px] font-semibold">
        {role ? `${role} · ` : ''}{skills.length} skill{skills.length === 1 ? '' : 's'}{extraction ? ', each quoting your CV' : ''}
        {removed !== null && <span className="font-normal text-muted"> · {removed} personal detail{removed === 1 ? '' : 's'} removed</span>}
      </span>
      <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
        {skills.map(([id, claim]) => (
          <li key={id} className="rounded-full bg-tray px-2.5 py-1 text-xs" title={claim.evidence || undefined}>
            {name(id)} · {claim.level === null ? 'not rated' : `${claim.level}/5`} <span className="text-muted">claim</span>
          </li>
        ))}
      </ul>
      {extraction?.unmatched?.length ? (
        <p className="q-src">Not in our skill list (not used in any score): {extraction.unmatched.map((u) => `“${u}”`).join(', ')}</p>
      ) : null}
    </section>
  )
}
