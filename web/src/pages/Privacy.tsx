import QRCode from 'qrcode'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getJSON } from '../api'
import { useJourney } from '../state'

// Privacy (docs/PHASE2_PLAN.md A9): what the app keeps, the PDPA's seven principles mapped to
// what it does, the resume code, and export / delete. A prototype, not a compliance certificate.

const PRINCIPLES: [string, string][] = [
  ['General', 'Only what matching needs is processed: situation, current role, skill levels with the CV sentence behind each, hours, budget and interests.'],
  ['Notice and Choice', 'Onboarding says what is kept before anything is stored, and every question can be skipped.'],
  ['Disclosure', 'Names, IC numbers, phone numbers and emails are removed before any model reads a CV. The cleaned text goes to OpenAI for reading skills; job titles and skill names go to RunPod for search. Nothing is shared with employers.'],
  ['Security', 'The profile opens only with its private code; profiles cannot be listed. Keys stay on the server.'],
  ['Retention', 'The CV text itself is not stored. A profile not used for 90 days is deleted automatically.'],
  ['Data Integrity', 'You can change every level and answer at any time; a level is always shown as your claim.'],
  ['Access', 'Download everything stored about you, or delete it, below.'],
]

const RESUME_PATH = '/overview'

export function Privacy() {
  const { profileId, setProfileId } = useJourney()
  const navigate = useNavigate()
  const [qr, setQr] = useState<string | null>(null)
  const [paste, setPaste] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [confirm, setConfirm] = useState(false)

  useEffect(() => {
    if (!profileId) return
    QRCode.toDataURL(profileId, { margin: 1, width: 180 }).then(setQr).catch(() => setQr(null))
  }, [profileId])

  async function download() {
    if (!profileId) return
    const data = await getJSON<unknown>(`/api/profiles/${profileId}/export`)
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'qart-my-data.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function erase() {
    if (!profileId) return
    const response = await fetch(`/api/profiles/${profileId}`, { method: 'DELETE' })
    if (!response.ok) {
      setMessage(`Could not delete: the server answered ${response.status}`)
      return
    }
    setProfileId(null)
    navigate('/start')
  }

  async function resume() {
    const code = paste.trim()
    try {
      await getJSON(`/api/profiles/${code}`)
      setProfileId(code)
      navigate(RESUME_PATH)
    } catch {
      setMessage('No profile has that code.')
    }
  }

  return (
    <main className="page">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">Privacy · your data</span>
        <h1 className="h1">What Qart.ai keeps, and your control over it</h1>
        <p className="m-0 max-w-[700px] text-graphite">
          How the app follows the seven principles of Malaysia&rsquo;s Personal Data Protection Act. This is a prototype for the SDC Hackathon; it describes what the app does, not a legal compliance certificate. The demo uses synthetic CVs only.
        </p>
      </header>
      <section className="section">
        <dl className="m-0 grid gap-x-6 gap-y-3 text-[14px] md:grid-cols-[180px_minmax(0,1fr)]">
          {PRINCIPLES.map(([name, text]) => (
            <div key={name} className="contents">
              <dt className="cap pt-0.5">{name}</dt>
              <dd className="m-0">{text}</dd>
            </div>
          ))}
        </dl>
      </section>
      {profileId ? (
        <section className="section">
          <h2 className="h2">Your resume code</h2>
          <p className="m-0 max-w-[640px] text-[14px] text-graphite">This code opens your profile. Keep it private: anyone with it can see your plan. Scan or paste it to continue on another device.</p>
          <div className="flex flex-wrap items-center gap-4">
            {qr && <img src={qr} alt="QR code of your resume code" width={180} height={180} className="rounded border border-line" />}
            <div className="flex flex-col gap-2">
              <code className="rounded bg-mist px-3 py-2 font-mono text-[13px]">{profileId}</code>
              <button type="button" className="btn self-start" onClick={() => navigator.clipboard?.writeText(profileId).then(() => setMessage('Code copied.'))}>Copy the code</button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 border-t border-line pt-3">
            <button type="button" className="btn" onClick={download}>Download my data</button>
            {!confirm ? (
              <button type="button" className="btn" onClick={() => setConfirm(true)}>Delete my profile</button>
            ) : (
              <>
                <button type="button" className="btn bg-weak text-white" onClick={erase}>Yes, delete everything</button>
                <button type="button" className="btn" onClick={() => setConfirm(false)}>Keep it</button>
              </>
            )}
          </div>
        </section>
      ) : null}
      <section className="section">
        <h2 className="h2">Continue with a resume code</h2>
        <div className="flex flex-wrap gap-2">
          <label className="sr-only" htmlFor="resume-code">Resume code</label>
          <input id="resume-code" value={paste} onChange={(e) => setPaste(e.target.value)} placeholder="Paste your code" className="min-h-[40px] min-w-[280px] rounded-md border border-hairline bg-paper px-3 font-mono text-[13px]" />
          <button type="button" className="btn btn-v" disabled={!paste.trim()} onClick={resume}>Open my profile</button>
        </div>
      </section>
      {message && <p role="status" className="m-0 text-[13px]">{message}</p>}
    </main>
  )
}
