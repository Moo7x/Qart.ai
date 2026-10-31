import { ChevronDown } from 'lucide-react'
import { useState, type Dispatch } from 'react'
import { Claim, Serif } from '../../components/atoms'
import { LevelPicker } from '../../components/LevelPicker'
import { levelName, useLevels } from '../../components/journey'
import { useT } from '../../i18n'
import type { Extraction, PackInfo } from '../../types'
import type { Draft, DraftAction } from './draft'

const FIRST_SHOWN = 2

/** Step 2: the skills read from the CV, each with its sentence; every level is a claim. */
export function SkillsStep({ draft, dispatch, pack, extraction }: { draft: Draft; dispatch: Dispatch<DraftAction>; pack: PackInfo | null; extraction: Extraction | null }) {
  const { t } = useT()
  const levels = useLevels()
  const [more, setMore] = useState(false)
  const [query, setQuery] = useState('')
  const name = (id: string) => pack?.skills.find((s) => s.id === id)?.name ?? id
  const entries = Object.entries(draft.skills)
  const shown = more ? entries : entries.slice(0, FIRST_SHOWN)
  const hidden = entries.length - FIRST_SHOWN
  const addable = (pack?.skills ?? []).filter((s) => !(s.id in draft.skills) && query.length > 1 && s.name.toLowerCase().includes(query.toLowerCase())).slice(0, 6)
  return (
    <>
      <div className="flex flex-wrap items-center gap-2.5">
        <h2 id="j-title" className="m-0 text-[clamp(26px,4vw,38px)] font-medium leading-[1.08] tracking-[-0.02em]">
          Check your <Serif>skills</Serif>
        </h2>
        <Claim>each level is a claim</Claim>
      </div>
      <p className="m-0 text-[15px] text-[#404040]">
        Read from your CV, each with the sentence it came from. Pick the highest sentence that is true for your work in the last two years. A level is your own claim, not a test.
      </p>
      {extraction && (
        <p className="q-src">
          {extraction.engine} · {Object.entries(extraction.removed).map(([k, v]) => `${v} ${k} removed`).join(', ') || 'no personal details found'}
          {extraction.rejected.length > 0 ? ` · ${extraction.rejected.length} claim(s) dropped: their quote was not in the CV` : ''}
          {extraction.note ? ` · ${extraction.note}` : ''}
        </p>
      )}
      {entries.length === 0 && <p className="m-0 text-sm text-muted">{t('No skills yet. Add the ones you have below.')}</p>}
      <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
        {shown.map(([id, claim]) => (
          <li key={id} className="flex flex-col gap-2 rounded-2xl border border-[#e5e5e5] bg-white px-4 py-3.5">
            <div className="flex flex-wrap justify-between gap-1.5">
              <span className="text-[15px] font-semibold">{name(id)}</span>
              <span className="text-[13px] text-muted">{claim.level === null ? 'not rated' : `${levelName(levels, claim.level)}`} · claim</span>
            </div>
            <span className="text-[13px] leading-relaxed text-muted">
              {claim.source === 'cv' ? `From your CV: “${claim.evidence}”` : claim.source === 'keyword' ? 'Found by keyword · set your level' : 'You added this'}
            </span>
            <LevelPicker skill={id} level={claim.level} label={`Your level in ${name(id)}`} onChange={(level) => dispatch({ type: 'level', skill: id, level })} />
          </li>
        ))}
      </ul>
      {hidden > 0 && (
        <button type="button" aria-expanded={more} onClick={() => setMore((m) => !m)} className="q-btn self-start">
          {more ? 'Show fewer skills' : `Show ${hidden} more skill${hidden === 1 ? '' : 's'}`}
          <ChevronDown size={16} aria-hidden="true" className={more ? 'rotate-180' : ''} />
        </button>
      )}
      {extraction?.unmatched?.length ? (
        <p className="m-0 text-sm text-muted">
          <span className="font-medium">Not in our skill list</span> (found in your CV, not used in any score): {extraction.unmatched.map((p) => `“${p}”`).join(', ')}
        </p>
      ) : null}
      <label className="flex flex-col gap-1.5 text-[13px] font-semibold">
        Add a skill
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. SQL, budget, ESG" className="j-field" />
      </label>
      {addable.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {addable.map((s) => (
            <button key={s.id} type="button" className="q-chip border-dashed" onClick={() => { dispatch({ type: 'add', skills: [s.id], level: 1 }); setQuery('') }}>
              + {s.name}
            </button>
          ))}
        </div>
      )}
    </>
  )
}
