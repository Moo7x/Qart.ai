import { useState } from 'react'
import { sendJSON } from '../api'
import type { Meters, RoleCard, Scenario, WhatIfResponse } from '../types'
import { LEVEL_MAX, levelName, useLevels } from './journey'

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
        <div key={label} className="border-l-2 border-line py-0.5 pl-3">
          <span className="block font-mono text-[10px] tracking-widest text-ash">{label}</span>
          <span className="block text-[15px] font-semibold">{value}</span>
          <span className="block text-[11px] text-graphite">{hint}</span>
        </div>
      ))}
    </div>
  )
}

// The unstated skill whose answer changes this person's options most; answering saves a
// self-rated claim (never verified) and the ranking is recomputed.
// Hypothetical levels → exact rank and fit changes; nothing is saved.
export function WhatIf({ profileId, scenario, role }: { profileId: string; scenario: Scenario; role: RoleCard }) {
  const levels = useLevels()
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
            {Array.from({ length: LEVEL_MAX + 1 }, (_, i) => <option key={i} value={i}>{levelName(levels, i)}</option>)}
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
