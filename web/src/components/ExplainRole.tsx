import { useState } from 'react'
import { useT } from '../i18n'
import { getJSON } from '../api'
import type { Explanation, Scenario } from '../types'
import { Activity } from './Activity'

// Plain-language sentences written by the model from computed facts only. The numbers stay in the
// cited facts (written by code), shown under each sentence.
export function ExplainRole({ profileId, roleId, scenario }: { profileId: string; roleId: string; scenario: Scenario }) {
  const { t } = useT()
  const [data, setData] = useState<Explanation | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setBusy(true)
    setError(null)
    try {
      setData(await getJSON<Explanation>(`/api/profiles/${profileId}/roles/${roleId}/explain?scenario=${scenario}`))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  if (!data) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn" onClick={load} disabled={busy}>
          {busy ? 'Writing…' : t('Explain this in plain words')}
        </button>
        <Activity running={busy} label="Writing from the computed facts" />
        {error && <span role="alert" className="text-xs text-weak">{error}</span>}
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-2 border-l-2 border-violet bg-violet-soft px-4 py-3">
      <ul className="m-0 flex list-none flex-col gap-2 p-0 text-[13px]">
        {data.sentences.map((s) => (
          <li key={s.text}>
            {s.text}
            <details className="mt-0.5 text-[11px] text-graphite">
              <summary className="cursor-pointer">Based on {s.facts.length} computed fact{s.facts.length === 1 ? '' : 's'}</summary>
              <ul className="mt-1 space-y-0.5 pl-4">
                {s.facts.map((f) => <li key={f.id}>{f.text}</li>)}
              </ul>
            </details>
          </li>
        ))}
      </ul>
      <span className="font-mono text-[11px] text-graphite">
        <Activity running={false} label="" stages={data.stages} />
        Written by {data.engine}{data.note ? ` · ${data.note}` : ''}. It only rephrases the computed facts and may word them loosely: the facts under each sentence are the record, and every number comes from code.
      </span>
    </div>
  )
}
