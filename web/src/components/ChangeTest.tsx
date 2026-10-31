import { useState } from 'react'
import { sendJSON, useApi } from '../api'
import { useJourney } from '../state'
import type { MatchesResponse, RequirementScore } from '../types'
import type { EvidenceTestOut, Override } from '../typesAgents'

// "Change the trend data now: what should change?" (docs/PHASE2_PLAN.md A3). The person picks one
// observed AI-use share behind a skill of their top role, sets a test value, and sees what the
// real engine does with it. Nothing is saved; the stored evidence never changes.

type Target = { kind: Override['kind']; key: string; label: string; current: number | null }
// DOSM job groups a finance role can belong to (src/match/outlook.py MAJOR_GROUP).
const GROUPS = [
  { key: 'professionals', label: 'Professionals (accountants, analysts)' },
  { key: 'technicians', label: 'Technicians and associate professionals' },
  { key: 'clerical', label: 'Clerical support (finance clerks, AP and AR)' },
]

function targets(soc: string, req: RequirementScore, occupationShare: number | null): Target[] {
  const tasks: Target[] = req.tasks.map((t) => ({ kind: 'task_share', key: t.task, label: `Task: ${t.text}`, current: t.automation_share }))
  return [...tasks, { kind: 'occupation_share', key: soc, label: `The whole occupation (${soc})`, current: occupationShare }]
}

function arrow(before: number, after: number): string {
  if (after < before) return `↑ ${before - after}`
  if (after > before) return `↓ ${after - before}`
  return '='
}

/** One sentence on what the test value changed, so the effect is seen at once. */
function Summary({ result }: { result: EvidenceTestOut }) {
  const before = new Map(result.before.roles.map((r) => [r.role_id, r]))
  const moved = result.after.roles.filter((r) => before.get(r.role_id)?.fit !== r.fit)
  const reordered = result.after.roles.some((r) => before.get(r.role_id)?.rank !== r.rank)
  const parts: string[] = []
  for (const r of moved.slice(0, 3)) {
    const b = before.get(r.role_id)
    if (b) parts.push(`${r.title} fit ${b.fit.toFixed(1)} → ${r.fit.toFixed(1)}`)
  }
  if (result.weights.length) parts.push(`${result.weights.length} skill weight${result.weights.length === 1 ? '' : 's'} moved`)
  if (result.pathway && result.pathway.fit_after_before !== result.pathway.fit_after_after) parts.push(`plan fit ${result.pathway.fit_after_before.toFixed(1)} → ${result.pathway.fit_after_after.toFixed(1)}`)
  if ((result.forecast ?? []).length) parts.push(`${result.forecast?.length} forecast categor${result.forecast?.length === 1 ? 'y' : 'ies'} changed`)
  parts.push(reordered ? 'the role order changed' : 'the role order stayed the same')
  return (
    <p className="m-0 rounded-xl bg-[#f1edff] px-4 py-3 text-[14px] font-medium text-ink">
      {moved.length || result.weights.length || (result.forecast ?? []).length ? 'What changed: ' : 'Nothing moved: this figure is not used by your roles. Try the whole occupation or a job-market trend. '}
      {parts.join(' · ')}.
    </p>
  )
}

export function ChangeTest() {
  const { profileId, scenario } = useJourney()
  const matches = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=${scenario}` : null)
  const [skill, setSkill] = useState<string | null>(null)
  const [targetKey, setTargetKey] = useState<string | null>(null)
  const [value, setValue] = useState(50)
  const [mode, setMode] = useState<'ai' | 'market'>('ai')
  const [group, setGroup] = useState(GROUPS[2].key)
  const [change, setChange] = useState(-1)
  const [result, setResult] = useState<EvidenceTestOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (!profileId || !matches.data) return null
  const data = matches.data
  const role = data.roles.find((r) => r.role_id === data.destination) ?? data.roles[0]
  if (!role) return null
  const shiftable = role.requirements.filter((r) => !r.essential)
  const req = shiftable.find((r) => r.skill === skill) ?? shiftable[0]
  if (!req) return null
  const options = targets(role.soc, req, role.automation_share)
  const target = options.find((o) => o.key === targetKey) ?? options[0]

  function pick(next: string) {
    const r = shiftable.find((x) => x.skill === next)
    const first = r ? targets(role.soc, r, role.automation_share)[0] : null
    setSkill(next)
    setTargetKey(first?.key ?? null)
    setValue(Math.round(first?.current ?? 50))
    setResult(null)
  }

  async function apply() {
    setBusy(true)
    setError(null)
    try {
      const out = await sendJSON<EvidenceTestOut>(`/api/profiles/${profileId}/evidence-test`, {
        body: { scenario, overrides: [mode === 'ai' ? { kind: target.kind, key: target.key, value } : { kind: 'group_change', key: group, value: change }] },
      })
      setResult(out)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  const ranksBefore = new Map(result?.before.roles.map((r) => [r.role_id, r]) ?? [])
  return (
    <section className="section" aria-label="Change the trend data">
      <div className="flex flex-col gap-1">
        <span className="eyebrow">Test it yourself</span>
        <h2 className="h2">Change the trend data: what should change?</h2>
        <p className="m-0 max-w-[720px] text-[13px] text-graphite">
          Pick a skill of {role.title}, choose the observed AI-use figure behind it, and set a test value. The real scoring and planning rules run on it; your saved data and the stored evidence stay as they are.
        </p>
      </div>
      <div role="radiogroup" aria-label="What to change" className="flex flex-wrap gap-2">
        {([['ai', 'AI use on a task'], ['market', 'Job-market trend']] as const).map(([id, text]) => (
          <button key={id} type="button" role="radio" aria-checked={mode === id} onClick={() => { setMode(id); setResult(null) }} className={`btn min-h-[40px] ${mode === id ? 'btn-v' : ''}`}>{text}</button>
        ))}
      </div>
      {mode === 'market' && (
        <div className="flex flex-col gap-2 text-[13px]">
          <label className="flex flex-col gap-1">
            <span className="cap">Job group (DOSM)</span>
            <select className="min-h-[40px] rounded-md border border-hairline bg-paper px-2" value={group} onChange={(e) => { setGroup(e.target.value); setResult(null) }}>
              {GROUPS.map((g) => <option key={g.key} value={g.key}>{g.label}</option>)}
            </select>
          </label>
          <label className="flex flex-wrap items-center gap-3">
            <span className="cap shrink-0">Test trend</span>
            <input type="range" min={-3} max={3} step={0.1} value={change} onChange={(e) => { setChange(Number(e.target.value)); setResult(null) }} className="min-w-[160px] flex-1 accent-[var(--color-violet)]" aria-label="Forecast change of the group's share of employees, test value" />
            <span className="w-[200px] font-mono">{change > 0 ? '+' : ''}{change.toFixed(1)} points in 2 years</span>
          </label>
          <p className="m-0 text-[12px] text-graphite">The forecast change of this group&rsquo;s share of Malaysian employees (DOSM, model chosen by backtest) is replaced by the test value. Roles in the group can move between Growing, Stable, Transforming and Shrinking.</p>
          <button type="button" className="btn btn-v min-h-[44px] self-start" disabled={busy} onClick={apply}>{busy ? 'Recomputing…' : 'Apply test value'}</button>
        </div>
      )}
      {mode === 'ai' && <>
      <div className="grid gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-[13px]">
          <span className="cap">Skill</span>
          <select className="min-h-[40px] rounded-md border border-hairline bg-paper px-2" value={req.skill} onChange={(e) => pick(e.target.value)}>
            {shiftable.map((r) => <option key={r.skill} value={r.skill}>{r.skill_name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[13px] md:col-span-2">
          <span className="cap">Observed figure to change</span>
          <select
            className="min-h-[40px] rounded-md border border-hairline bg-paper px-2"
            value={target.key}
            onChange={(e) => {
              const t = options.find((o) => o.key === e.target.value)
              setTargetKey(e.target.value)
              setValue(Math.round(t?.current ?? 50))
              setResult(null)
            }}
          >
            {options.map((o) => <option key={o.key} value={o.key}>{o.label} · {o.current === null ? 'no published value' : `${o.current.toFixed(0)}% now`}</option>)}
          </select>
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-[13px]">
        <label className="flex flex-1 items-center gap-3">
          <span className="cap shrink-0">Test value</span>
          <input type="range" min={0} max={100} step={1} value={value} onChange={(e) => { setValue(Number(e.target.value)); setResult(null) }} className="min-w-[160px] flex-1 accent-[var(--color-violet)]" aria-label="Automation-style share of AI use, test value" />
          <span className="w-[120px] font-mono">{value}% automation-style</span>
        </label>
        <button type="button" className="btn btn-v min-h-[44px]" disabled={busy} onClick={apply}>{busy ? 'Recomputing…' : 'Apply test value'}</button>
        {result && <button type="button" className="btn min-h-[44px]" onClick={() => setResult(null)}>Reset</button>}
      </div>
      <p className="m-0 text-[12px] text-graphite">
        Now: {target.current === null ? 'no published value' : `${target.current.toFixed(1)}%`} ({data.evidence.source}, {data.evidence.period}). Routine skills lose weight as this share rises; skills that complement AI gain weight. Essentials never move.
      </p>
      </>}
      {error && <p role="alert" className="m-0 text-[13px] text-weak">{error}</p>}
      {result && (
        <div className="flex flex-col gap-3 rounded-md border-2 border-dashed border-estimate p-3">
          <span className="tag self-start bg-estimate-bg text-estimate">{result.label}</span>
          <Summary result={result} />
          <div>
            <span className="cap">Qart forecast categories that changed</span>
            {(result.forecast ?? []).length === 0 ? (
              <p className="m-0 mt-1 text-[13px] text-graphite">None: no role crosses a category line with this value. A role is Transforming only when two of three kinds of AI evidence agree, and Shrinking only when its job group also falls.</p>
            ) : (
              <ul className="m-0 mt-1 flex list-none flex-col gap-1 p-0 text-[13px]">
                {(result.forecast ?? []).map((c) => <li key={c.role_id} className="flex justify-between gap-2"><span>{c.title}{c.current_job ? ' · your job' : ''}</span><span className="font-mono">{c.before} → {c.after}</span></li>)}
              </ul>
            )}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="min-w-0">
              <span className="cap">Role ranking, before → after</span>
              <table className="mt-1 w-full border-collapse text-[13px]">
                <tbody>
                  {result.after.roles.map((r) => {
                    const b = ranksBefore.get(r.role_id)
                    return (
                      <tr key={r.role_id} className={`border-t border-line ${b && (b.fit !== r.fit || b.rank !== r.rank) ? 'bg-[#f1edff] font-semibold text-violet' : ''}`}>
                        <td className="py-1 pr-2 font-mono">{r.rank}</td>
                        <td className="py-1 pr-2">{r.title}</td>
                        <td className="py-1 pr-2 font-mono text-graphite">{b ? `${b.fit.toFixed(1)} → ${r.fit.toFixed(1)}` : r.fit.toFixed(1)}</td>
                        <td className="py-1 font-mono">{b ? arrow(b.rank, r.rank) : ''}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex min-w-0 flex-col gap-3">
              <div>
                <span className="cap">Weights that moved</span>
                {result.weights.filter((w) => w.role_id === role.role_id).length === 0 ? (
                  <p className="m-0 mt-1 text-[13px] text-graphite">No weight in {role.title} uses this figure.</p>
                ) : (
                  <ul className="m-0 mt-1 flex list-none flex-col gap-1 p-0 text-[13px]">
                    {result.weights.filter((w) => w.role_id === role.role_id).map((w) => (
                      <li key={w.skill} className="flex justify-between gap-2"><span>{w.skill_name}</span><span className="font-mono">{w.before.toFixed(2)} → {w.after.toFixed(2)}</span></li>
                    ))}
                  </ul>
                )}
              </div>
              {result.pathway && (
                <div>
                  <span className="cap">Your plan for {result.pathway.title}</span>
                  <p className="m-0 mt-1 text-[13px]">
                    {result.pathway.before.join() === result.pathway.after.join() ? 'Same steps in the same order.' : 'The steps change:'} Fit after the plan {result.pathway.fit_after_before.toFixed(1)} → {result.pathway.fit_after_after.toFixed(1)} (estimate).
                  </p>
                  {result.pathway.before.join() !== result.pathway.after.join() && (
                    <ol className="m-0 mt-1 pl-5 text-[12px]">
                      {result.pathway.after.map((id) => <li key={id} className={result.pathway?.before.includes(id) ? '' : 'font-semibold'}>{result.pathway?.titles[id] ?? id}</li>)}
                    </ol>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
