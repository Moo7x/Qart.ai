import { useState } from 'react'
import { sendJSON, useApi } from '../api'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import { NeedProfile } from './Roles'

type Sections = Record<string, string[]>
type CvResponse = {
  draft: Sections
  diff: Record<string, { added: string[]; removed: string[] }>
  unchanged: boolean
  versions: { version: number; accepted_at: string }[]
}
const TITLES: Record<string, string> = {
  headline: 'Headline',
  skills: 'Skills (your own ratings)',
  experience: 'Experience, in your words from your CV',
  learning: 'Learning',
}

function asText(sections: Sections): string {
  return Object.entries(sections)
    .filter(([, lines]) => lines.length)
    .map(([key, lines]) => `${TITLES[key] ?? key}\n${lines.map((l) => (key === 'headline' ? l : `- ${l}`)).join('\n')}`)
    .join('\n\n')
}

export function Cv() {
  const { profileId } = useJourney()
  const view = useApi<CvResponse>(profileId ? `/api/profiles/${profileId}/cv` : null)
  const [busy, setBusy] = useState(false)
  if (!profileId) return <NeedProfile />
  const data = view.data

  async function acceptDraft() {
    setBusy(true)
    try {
      await sendJSON(`/api/profiles/${profileId}/cv/accept`)
      view.reload()
    } finally {
      setBusy(false)
    }
  }

  function download() {
    if (!data) return
    const blob = new Blob([asText(data.draft)], { type: 'text/plain;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'qart-cv-draft.txt'
    link.click()
    URL.revokeObjectURL(link.href)
  }

  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">My CV · draft update</span>
        <h1 className="h1">Your CV, updated from what you confirmed</h1>
        <p className="m-0 max-w-[680px] text-graphite">
          Built only from your profile, the sentences in your CV and the courses you marked done. Courses go under learning, never under experience, and ratings are your own. Nothing here is invented; check it before you use it.
        </p>
      </header>
      {view.loading && <Loading what="your CV draft" />}
      {view.error && <Problem what="your CV draft" message={view.error} onRetry={view.reload} />}
      {data && (
        <>
          <section className="card-light flex flex-col gap-4 px-6 py-5">
            {Object.entries(data.draft).map(([key, lines]) => (
              <div key={key} className="flex flex-col gap-1">
                <span className="cap">{TITLES[key] ?? key}</span>
                {lines.length === 0 && <span className="text-[13px] text-ash">Nothing confirmed yet.</span>}
                <ul className="m-0 list-none space-y-0.5 p-0 text-[13px]">
                  {lines.map((line) => {
                    const added = data.versions.length > 0 && data.diff[key]?.added.includes(line)
                    return <li key={line} className={added ? 'rounded bg-rising-bg px-1' : ''}>{line}{added && <span className="ml-1.5 font-mono text-[10px] text-rising">NEW</span>}</li>
                  })}
                  {data.diff[key]?.removed.map((line) => <li key={`-${line}`} className="text-ash line-through">{line}</li>)}
                </ul>
              </div>
            ))}
            <div className="flex flex-wrap items-center gap-2 border-t border-mist pt-3">
              <button type="button" className="btn btn-v" onClick={acceptDraft} disabled={busy || data.unchanged}>
                {data.unchanged ? 'No changes since your last version' : data.versions.length ? 'Accept these changes' : 'Accept as version 1'}
              </button>
              <button type="button" className="btn" onClick={download}>Download as text</button>
              <span className="text-xs text-graphite">
                {data.versions.length ? `Version ${data.versions.at(-1)!.version} accepted ${data.versions.at(-1)!.accepted_at.slice(0, 10)}. New lines are marked; removed lines are struck through.` : 'No version accepted yet.'}
              </span>
            </div>
          </section>
          <p className="m-0 text-xs text-graphite">Synthetic demo data only. A CV wording is not a hiring guarantee and is not checked against any applicant system.</p>
        </>
      )}
    </main>
  )
}
