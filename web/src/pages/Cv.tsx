import { useState } from 'react'
import { useT } from '../i18n'
import { sendJSON, useApi } from '../api'
import { JourneyRoute, NextStep } from '../components/journey'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import { NeedProfile } from './Roles'

type Sections = Record<string, string[]>
type CvResponse = {
  draft: Sections
  diff: Record<string, { added: string[]; removed: string[] }>
  unchanged: boolean
  current: Sections | null
  versions: { version: number; accepted_at: string }[]
}
const TITLES: Record<string, string> = {
  headline: 'Headline',
  skills: 'Skills (your own ratings)',
  experience: 'Experience, in your words from your CV',
  learning: 'Learning',
}
const PRINT_TITLES: Record<string, string> = { headline: 'Profile', skills: 'Skills', experience: 'Experience', learning: 'Learning' }

function asText(sections: Sections): string {
  return Object.entries(sections)
    .filter(([, lines]) => lines.length)
    .map(([key, lines]) => `${TITLES[key] ?? key}\n${lines.map((l) => (key === 'headline' ? l : `- ${l}`)).join('\n')}`)
    .join('\n\n')
}

// One-page layout used only when printing (Download PDF uses the browser's "Save as PDF").
function PrintCv({ sections, name }: { sections: Sections; name: string }) {
  return (
    <article id="cv-print" aria-hidden="true">
      <h1>{name.trim() || 'Your name'}</h1>
      {Object.entries(sections).filter(([, lines]) => lines.length).map(([key, lines]) => (
        <section key={key}>
          <h2>{PRINT_TITLES[key] ?? key}</h2>
          {key === 'headline' ? <p>{lines[0]}</p> : <ul>{lines.map((l) => <li key={l}>{l}</li>)}</ul>}
        </section>
      ))}
      <footer>Skill ratings are self-assessed. Learning entries are self-reported course completions.</footer>
    </article>
  )
}

export function Cv() {
  const { t } = useT()
  const { profileId } = useJourney()
  const view = useApi<CvResponse>(profileId ? `/api/profiles/${profileId}/cv` : null)
  const [busy, setBusy] = useState(false)
  const [skipped, setSkipped] = useState<string[]>([])
  const [kept, setKept] = useState<string[]>([])
  const [name, setName] = useState('')
  if (!profileId) return <NeedProfile />
  const data = view.data
  const added = data ? Object.entries(data.diff).flatMap(([key, d]) => d.added.map((line) => ({ key, line }))) : []
  const removed = data && data.versions.length ? Object.entries(data.diff).flatMap(([key, d]) => d.removed.map((line) => ({ key, line }))) : []
  const shown = data?.current ?? data?.draft

  async function acceptChosen() {
    setBusy(true)
    try {
      await sendJSON(`/api/profiles/${profileId}/cv/accept`, { body: { skip_added: skipped, keep_removed: kept } })
      setSkipped([])
      setKept([])
      view.reload()
    } finally {
      setBusy(false)
    }
  }

  function download() {
    if (!shown) return
    const blob = new Blob([asText(shown)], { type: 'text/plain;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'qart-cv.txt'
    link.click()
    URL.revokeObjectURL(link.href)
  }

  const toggle = (list: string[], set: (v: string[]) => void, line: string) => set(list.includes(line) ? list.filter((l) => l !== line) : [...list, line])
  const taken = added.length - added.filter((a) => skipped.includes(a.line)).length

  return (
    <main className="page">
      <JourneyRoute />
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">My CV</span>
        <h1 className="h1">{t('Your CV, updated from what you confirmed')}</h1>
        <p className="m-0 max-w-[680px] text-graphite">
          Built only from your profile, the sentences in your CV and the courses you marked done. Courses go under learning, never under experience, and ratings are your own. Nothing is added until you tick and accept it.
        </p>
      </header>
      {view.loading && <Loading what="your CV" />}
      {view.error && <Problem what="your CV" message={view.error} onRetry={view.reload} />}
      {data && shown && (
        <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <section aria-label="Suggested changes" className="flex min-w-0 flex-col gap-4">
            <div className="flex items-baseline justify-between gap-2 border-b-2 border-void pb-2">
              <h2 className="h2">Suggested changes</h2>
              <span className="cap">{added.length + removed.length} to review</span>
            </div>
            {data.unchanged && <p className="m-0 text-[13px] text-graphite">Nothing new since your last version. Mark plan steps done or rate more skills and new lines will appear here.</p>}
            {added.length > 0 && (
              <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
                <legend className="cap pb-1">Add to your CV</legend>
                {added.map(({ key, line }) => (
                  <label key={`${key}-${line}`} className="flex min-h-11 cursor-pointer items-start gap-3 border-t border-line py-2.5 text-[13px]">
                    <input type="checkbox" className="mt-0.5 h-4 w-4 accent-violet" checked={!skipped.includes(line)} onChange={() => toggle(skipped, setSkipped, line)} />
                    <span className="min-w-0">
                      <span className="block">{line}</span>
                      <span className="font-mono text-[10px] uppercase tracking-wider text-ash">{TITLES[key] ?? key}</span>
                    </span>
                  </label>
                ))}
              </fieldset>
            )}
            {removed.length > 0 && (
              <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
                <legend className="cap pb-1">No longer in your data · tick to keep</legend>
                {removed.map(({ key, line }) => (
                  <label key={`-${key}-${line}`} className="flex min-h-11 cursor-pointer items-start gap-3 border-t border-line py-2.5 text-[13px]">
                    <input type="checkbox" className="mt-0.5 h-4 w-4 accent-violet" checked={kept.includes(line)} onChange={() => toggle(kept, setKept, line)} />
                    <span className={kept.includes(line) ? '' : 'text-ash line-through'}>{line}</span>
                  </label>
                ))}
              </fieldset>
            )}
            {!data.unchanged && (
              <div className="flex flex-wrap items-center gap-3">
                <button type="button" className="btn btn-v min-h-[44px]" onClick={acceptChosen} disabled={busy}>
                  {data.versions.length ? `Accept ${taken} change${taken === 1 ? '' : 's'}` : `Save as version 1 (${taken} line${taken === 1 ? '' : 's'})`}
                </button>
                <span className="text-xs text-graphite">Unticked lines stay suggestions; they are not deleted.</span>
              </div>
            )}
          </section>

          <section aria-label="Your CV" className="flex min-w-0 flex-col gap-4">
            <div className="flex items-baseline justify-between gap-2 border-b-2 border-violet pb-2">
              <h2 className="h2">{data.current ? `Your CV · version ${data.versions.at(-1)!.version}` : 'Preview · not saved yet'}</h2>
              {data.versions.length > 0 && <span className="cap">accepted {data.versions.at(-1)!.accepted_at.slice(0, 10)}</span>}
            </div>
            <div className="flex flex-col gap-4 border border-line bg-paper px-6 py-5">
              {Object.entries(shown).map(([key, lines]) => (
                <div key={key} className="flex flex-col gap-1">
                  <span className="cap">{TITLES[key] ?? key}</span>
                  {lines.length === 0 && <span className="text-[13px] text-ash">Nothing confirmed yet.</span>}
                  <ul className="m-0 list-none space-y-0.5 p-0 text-[13px]">
                    {lines.map((line) => <li key={line}>{line}</li>)}
                  </ul>
                </div>
              ))}
            </div>
            <label className="flex flex-col gap-1.5 text-[13px] font-medium">
              Name to print on the PDF (stays in this browser, never saved)
              <input value={name} onChange={(e) => setName(e.target.value)} className="min-h-[44px] rounded border border-line bg-paper px-3 text-[15px]" />
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" className="btn btn-v min-h-[44px]" disabled={!data.current} onClick={() => window.print()}>Download PDF</button>
              <button type="button" className="btn min-h-[44px]" onClick={download}>{t('Download as text')}</button>
              {!data.current && <span className="text-xs text-graphite">Save a version first; the PDF prints your accepted CV.</span>}
              {data.current && <span className="text-xs text-graphite">Choose &ldquo;Save as PDF&rdquo; in the print window.</span>}
            </div>
          </section>
          {data.current && <PrintCv sections={data.current} name={name} />}
        </div>
      )}
      <p className="m-0 text-xs text-graphite">Synthetic demo data only. A CV wording is not a hiring guarantee and is not checked against any applicant system.</p>
      <NextStep to="/pathway" label="Back to your plan" hint="Keep going: mark plan steps done as you finish them" />
    </main>
  )
}
