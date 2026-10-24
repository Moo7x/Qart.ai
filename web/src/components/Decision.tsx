import { useState } from 'react'
import { sendJSON, useApi } from '../api'
import type { Meters, Question, RoleCard, Scenario, WhatIfResponse } from '../types'
import { Loading, Problem } from './ui'

const LEVELS = ['none', 'aware', 'working', 'proficient', 'expert']

// Coverage, essentials and profile completeness kept apart, so one number never hides them.
export function MeterRow({ meters, range }: { meters: Meters; range: { low: number; high: number } }) {
  const essentials = meters.essentials_ready
    ? 'all essentials met'
    : [
        meters.essentials_below.length ? `${meters.essentials_below.length} below level` : '',
        meters.essentials_unstated.length ? `${meters.essentials_unstated.length} not stated` : '',
      ].filter(Boolean).join(' · ')
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
      {[
        ['COVERAGE', `${Math.round(meters.coverage)} / 100`, 'weighted requirement coverage'],
        ['IF UNSTATED ARE STRONG', range.high > range.low ? `up to ${Math.round(range.high)}` : 'no change', 'assumption-based range'],
        ['ESSENTIALS', essentials, [...meters.essentials_below, ...meters.essentials_unstated.map((n) => `${n} (not stated)`)].join(', ') || 'none missing'],
        ['PROFILE STATED', `${Math.round(meters.completeness)}%`, `${meters.stated} of ${meters.requirements} skills`],
      ].map(([label, value, hint]) => (
        <div key={label} className="rounded-lg bg-surface px-3 py-2">
          <span className="block font-mono text-[10px] tracking-widest text-stone">{label}</span>
          <span className="block text-[15px] font-semibold">{value}</span>
          <span className="block text-[11px] text-slate-mid">{hint}</span>
        </div>
      ))}
    </div>
  )
}

// The unstated skill whose answer changes this person's options most; answering saves a
// self-rated claim (never verified) and the ranking is recomputed.
export function BestQuestion({ profileId, scenario, onAnswered }: { profileId: string; scenario: Scenario; onAnswered: () => void }) {
  const questions = useApi<Question[]>(`/api/profiles/${profileId}/questions?scenario=${scenario}`)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (questions.loading) return <Loading what="the next question" />
  if (questions.error) return <Problem what="the next question" message={questions.error} onRetry={questions.reload} />
  const [first, ...rest] = questions.data ?? []
  if (!first) return null

  async function answer(level: number) {
    setBusy(true)
    setError(null)
    try {
      await sendJSON(`/api/profiles/${profileId}/answer`, { body: { skill: first.skill, level } })
      questions.reload()
      onAnswered()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card-light flex flex-col gap-2.5 border-l-4 border-violet px-6 py-4">
      <span className="cap text-violet">The question that matters most for you now</span>
      <h2 className="h2">How would you rate your {first.skill_name}?</h2>
      <p className="m-0 text-[13px] text-graphite">{first.effect}</p>
      <div className="flex flex-wrap gap-2" role="group" aria-label={`Your level in ${first.skill_name}`}>
        {LEVELS.map((label, level) => (
          <button key={label} type="button" className="btn" disabled={busy} onClick={() => answer(level)}>
            {label}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="m-0 text-xs text-weak">{error}</p>}
      <p className="m-0 text-xs text-graphite">
        Your answer is saved as your own rating, not a verified level.
        {rest.length > 0 && <> Next: {rest.map((q) => q.skill_name).join(', ')}.</>}
      </p>
    </section>
  )
}

// Hypothetical levels → exact rank and fit changes; nothing is saved.
export function WhatIf({ profileId, scenario, role }: { profileId: string; scenario: Scenario; role: RoleCard }) {
  const [skill, setSkill] = useState(role.requirements[0]?.skill ?? '')
  const [level, setLevel] = useState(3)
  const [result, setResult] = useState<WhatIfResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function run() {
    setError(null)
    try {
      setResult(await sendJSON<WhatIfResponse>(`/api/profiles/${profileId}/whatif`, { body: { changes: { [skill]: level }, scenario } }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    }
  }

  const moved = (result?.roles ?? []).filter((r) => r.fit_then !== r.fit_now || r.rank_then !== r.rank_now)
  return (
    <details className="card-light px-6 py-4">
      <summary className="h2 cursor-pointer">What would change this? (what-if)</summary>
      <div className="mt-3 flex flex-wrap items-end gap-2 text-[13px]">
        <label className="flex flex-col gap-1">
          <span className="cap">If my</span>
          <select className="rounded-md border border-hairline px-2 py-1.5" value={skill} onChange={(e) => setSkill(e.target.value)}>
            {role.requirements.map((r) => <option key={r.skill} value={r.skill}>{r.skill_name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="cap">were</span>
          <select className="rounded-md border border-hairline px-2 py-1.5" value={level} onChange={(e) => setLevel(Number(e.target.value))}>
            {LEVELS.map((label, i) => <option key={label} value={i}>{label}</option>)}
          </select>
        </label>
        <button type="button" className="btn btn-v" onClick={run}>Recompute</button>
      </div>
      {error && <p role="alert" className="m-0 mt-2 text-xs text-weak">{error}</p>}
      {result && (
        <ul className="mt-3 flex list-none flex-col gap-1 p-0 text-[13px]">
          {moved.length === 0 && <li className="text-graphite">No role's fit or rank would change.</li>}
          {moved.map((r) => (
            <li key={r.role_id} className="flex flex-wrap justify-between gap-2 border-t border-mist pt-1">
              <span>{r.title}</span>
              <span className="font-mono">
                fit {r.fit_now.toFixed(1)} → {r.fit_then.toFixed(1)} · rank {r.rank_now} → {r.rank_then}
              </span>
            </li>
          ))}
          <li className="text-xs text-graphite">Hypothetical: your saved profile is unchanged.</li>
        </ul>
      )}
    </details>
  )
}
