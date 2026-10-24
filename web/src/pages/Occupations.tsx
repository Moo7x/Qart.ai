import { useState } from 'react'
import { useT } from '../i18n'
import { sendJSON } from '../api'
import { OccupationEvidence } from '../components/OccupationEvidence'
import type { Detection } from '../types'

export function Occupations() {
  const { t } = useT()
  const [text, setText] = useState('')
  const [result, setResult] = useState<Detection | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function search(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setChosen(null)
    try {
      setResult(await sendJSON<Detection>('/api/occupations/detect', { body: { text } }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">Any occupation · evidence preview</span>
        <h1 className="h1">{t('What the evidence says about your job')}</h1>
        <p className="m-0 max-w-[680px] text-graphite">
          Type your job title or what you do, in English or Malay. Qart matches it to a standard occupation and shows what the registered sources say about it. Full journeys (roles, courses, pathways) are verified for GBS finance & accounting so far.
        </p>
      </header>
      <form onSubmit={search} className="card-light flex flex-wrap items-end gap-2 px-6 py-4">
        <label className="flex min-w-0 flex-[1_1_320px] flex-col gap-1 text-[13px]">
          <span className="cap">Job title or what you do</span>
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. Kerani akaun, or: I chase customers for overdue invoices" className="rounded-md border border-hairline px-3 py-2" maxLength={300} />
        </label>
        <button type="submit" className="btn btn-v" disabled={busy || text.trim().length < 2}>{busy ? 'Matching… (the GPU may be waking up)' : t('Find my occupation')}</button>
      </form>
      {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}
      {result && (
        <section className="card-light flex flex-col gap-2 px-6 py-4">
          <span className="cap">Which of these is closest? You choose.</span>
          {result.matches.length === 0 && <p className="m-0 text-sm text-graphite">No match found. Try other words.</p>}
          <div className="flex flex-wrap gap-2">
            {result.matches.map((m) => (
              <button key={m.soc} type="button" onClick={() => setChosen(m.soc)} aria-pressed={chosen === m.soc} className={`btn ${chosen === m.soc ? 'btn-v' : ''}`}>
                {m.title}{m.in_field ? ' · full journey' : ''}
              </button>
            ))}
          </div>
          <span className="font-mono text-[11px] text-ash">Matched by {result.engine}{result.note ? ` · ${result.note}` : ''}. A suggestion, not a classification of you.</span>
        </section>
      )}
      {chosen && <OccupationEvidence key={chosen} soc={chosen} />}
    </main>
  )
}
