import { useState, type Dispatch } from 'react'
import { sendJSON } from '../../api'
import { Serif } from '../../components/atoms'
import { useT } from '../../i18n'
import type { PackInfo, Stage } from '../../types'
import type { Draft, DraftAction } from './draft'

export type SkillSuggestions = { hits: { skill: string; name: string; score: number }[]; engine: string; note: string; stages?: Stage[] }

/** Step 1: upload a CV (read by the existing extraction), or describe the work in a form. */
export function CvStep({
  draft,
  dispatch,
  pack,
  formFirst,
  busy,
  onFile,
  run,
}: {
  draft: Draft
  dispatch: Dispatch<DraftAction>
  pack: PackInfo | null
  formFirst: boolean
  busy: boolean
  onFile: (file: File) => void
  run: (label: string, work: () => Promise<string>) => void
}) {
  const { t } = useT()
  const [form, setForm] = useState(formFirst)
  const [suggestions, setSuggestions] = useState<SkillSuggestions | null>(null)
  const [picked, setPicked] = useState<string[]>([])
  const find = () =>
    run('Matching your tasks to skills…', async () => {
      setSuggestions(null)
      setPicked([])
      const found = await sendJSON<SkillSuggestions>('/api/skills/search', { body: { text: draft.tasks } })
      setSuggestions(found)
      return found.hits.length ? `${found.hits.length} matching skill${found.hits.length === 1 ? '' : 's'} to choose from below` : 'No matching skill found; try a more specific task'
    })
  return (
    <>
      <h2 id="j-title" className="m-0 text-[clamp(26px,4vw,38px)] font-medium leading-[1.08] tracking-[-0.02em]">
        Add your <Serif>CV</Serif>
      </h2>
      <p className="m-0 text-[15px] text-[#404040]">{t('We pre-fill the next questions from it. Prefer not to? Skip and answer them yourself.')}</p>
      <label className="j-drop">
        <span className="text-[15px] font-semibold">{t('Drop a PDF, DOCX or text file')}</span>
        <span className="text-sm text-muted">or click to browse</span>
        <input type="file" accept=".pdf,.docx,.txt" aria-label="Upload CV" disabled={busy} className="absolute inset-0 cursor-pointer opacity-0" onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
      </label>
      <p className="m-0 text-[13px] text-muted">{t('Names, IC numbers, phone numbers and emails are removed before anything reads the CV. The CV text itself is not stored.')}</p>
      <button type="button" aria-expanded={form} aria-controls="j-form" onClick={() => setForm((f) => !f)} className="q-btn self-start">
        {form ? 'Hide the form' : 'Use a form instead'}
      </button>
      {form && (
        <div id="j-form" className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold">
            Current or last role
            <select value={draft.role} onChange={(e) => dispatch({ type: 'set', patch: { role: e.target.value } })} className="j-field">
              <option value="other">{t('None of these')}</option>
              {(pack?.current_roles ?? []).map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold">
            Years of work experience
            <input type="number" min={0} max={60} value={draft.years} onChange={(e) => dispatch({ type: 'set', patch: { years: e.target.value } })} className="j-field" />
          </label>
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold">
            Main tasks, in your own words
            <textarea rows={4} value={draft.tasks} placeholder="e.g. applying customer receipts, month-end reports" onChange={(e) => { dispatch({ type: 'set', patch: { tasks: e.target.value } }); setSuggestions(null) }} className="j-field resize-y leading-relaxed" />
          </label>
          <button type="button" className="q-btn self-start" disabled={busy || draft.tasks.trim().length < 3} onClick={find}>Find the matching skills</button>
          {suggestions && (
            <section aria-label="Suggested skills" className="flex flex-col gap-1 border-y border-[#e5e5e5] py-3">
              <p className="m-0 text-sm font-medium">{suggestions.hits.length ? 'Choose the skills that describe your work' : 'No matching skills found. Try a specific task, or add skills on the next step.'}</p>
              <p className="q-src">Matched by {suggestions.engine}. {suggestions.note}</p>
              {suggestions.hits.map((hit) => (
                <label key={hit.skill} className="flex min-h-11 items-center gap-3 text-sm">
                  <input type="checkbox" className="h-[18px] w-[18px] accent-violet" checked={picked.includes(hit.skill)} onChange={(e) => setPicked((p) => (e.target.checked ? [...p, hit.skill] : p.filter((x) => x !== hit.skill)))} />
                  {hit.name}{hit.skill in draft.skills && ' · already in your profile'}
                </label>
              ))}
              {suggestions.hits.length > 0 && (
                <button type="button" className="q-btn self-start" disabled={!picked.length} onClick={() => { dispatch({ type: 'add', skills: picked, level: null }); setSuggestions(null); setPicked([]) }}>
                  Add selected skills
                </button>
              )}
            </section>
          )}
        </div>
      )}
    </>
  )
}
