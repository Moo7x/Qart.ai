import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { Dots, ScenarioSwitch, SdgTag } from '../components/journey'
import { ExplainRole } from '../components/ExplainRole'
import { RoleTasks } from '../components/RoleTasks'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { GapColumn, MatchesResponse, RoleCard } from '../types'

const GAP_TITLE: Record<GapColumn, [string, string]> = {
  ready: ['Ready now', 'text-rising'],
  bridgeable: ['Partly there', 'text-[#5231e0]'],
  missing: ['Still to build', 'text-weak'],
  not_stated: ['Not stated · tell us', 'text-graphite'],
}
const COLUMNS: GapColumn[] = ['ready', 'bridgeable', 'missing', 'not_stated']

export function NeedProfile() {
  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-4 px-5 py-7 md:px-10">
      <span className="eyebrow">Your journey</span>
      <h1 className="h1">Tell us about yourself first</h1>
      <p className="m-0 max-w-[560px] text-graphite">
        Roles, pathways and the future view are built from your profile. It takes about three minutes and you can skip any question.
      </p>
      <Link className="btn btn-v self-start" to="/start">Start</Link>
    </main>
  )
}

function bars(role: RoleCard) {
  const total = role.requirements.reduce((sum, r) => sum + r.weight, 0)
  const share = (cols: GapColumn[]) =>
    (100 * role.requirements.filter((r) => cols.includes(r.column)).reduce((s, r) => s + r.weight, 0)) / total
  return { ready: share(['ready']), partly: share(['bridgeable']) }
}

function Why({ role, onChoose, chosen, busy }: { role: RoleCard; onChoose: () => void; chosen: boolean; busy: boolean }) {
  const { ready, partly } = bars(role)
  const { profileId, scenario } = useJourney()
  return (
    <section className="card-dark flex flex-col gap-4 bg-[radial-gradient(70%_80%_at_90%_0%,rgba(108,71,255,0.2),rgba(33,33,38,0)_70%)] p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[11px] tracking-widest text-cyan">WHY THIS SCORE</span>
          <h2 className="m-0 text-2xl font-semibold tracking-tight">{role.title}</h2>
          <span className="text-[13px] text-stone">
            {role.effort_hours} h of verified free courses · about {role.effort_weeks} week{role.effort_weeks === 1 ? '' : 's'} at your pace
          </span>
        </div>
        <span className="flex items-baseline gap-1.5">
          <span className="font-mono text-[64px] leading-none tracking-[-0.04em]">{Math.round(role.fit)}</span>
          <span className="font-mono text-[13px] text-stone">/ 100</span>
        </span>
      </div>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-surface" aria-hidden="true">
        <span style={{ width: `${ready}%` }} className="bg-mint" />
        <span style={{ width: `${partly}%` }} className="bg-violet-light" />
      </div>
      <div className="rounded-lg bg-surface px-3.5 py-3">
        <p className="m-0 font-mono text-xs">fit = 100 × Σ w · min(your level ÷ needed level, 1) ÷ Σ w</p>
        <p className="m-0 mt-1.5 text-xs text-stone">
          w = how much the role leans on each skill under this scenario (assumption, shown per skill below). Essential skills keep their level and weight in every scenario.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] border-collapse text-[13px]">
          <thead>
            <tr className="text-left font-mono text-[11px] tracking-wider text-stone">
              <th className="py-1.5 pr-2 font-normal">SKILL</th>
              <th className="px-2 py-1.5 font-normal">YOU</th>
              <th className="px-2 py-1.5 font-normal">NEEDS</th>
              <th className="px-2 py-1.5 text-right font-normal">WEIGHT</th>
              <th className="py-1.5 pl-2 text-right font-normal">POINTS</th>
            </tr>
          </thead>
          <tbody>
            {role.requirements.map((r) => (
              <tr key={r.skill} className="border-t border-surface align-top" title={r.shift_reason}>
                <td className="py-2 pr-2">
                  {r.skill_name}
                  {r.essential && <span className="ml-1.5 font-mono text-[10px] text-amber-glow">ESSENTIAL</span>}
                  <span className="block text-[11px] text-slate-mid">{r.shift_reason}</span>
                </td>
                <td className="px-2 py-2"><Dots level={r.claimed} tone="light" /></td>
                <td className="px-2 py-2 font-mono">{r.required}</td>
                <td className="px-2 py-2 text-right font-mono">{r.weight.toFixed(2)}</td>
                <td className="py-2 pl-2 text-right font-mono">{r.contribution.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {profileId && <ExplainRole key={`${role.role_id}-${scenario}`} profileId={profileId} roleId={role.role_id} scenario={scenario} />}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn btn-v" onClick={onChoose} disabled={busy}>
          {chosen ? 'Your destination ✓ · open the pathway' : 'Choose as my destination'}
        </button>
      </div>
    </section>
  )
}

export function Roles() {
  const { profileId, scenario } = useJourney()
  const navigate = useNavigate()
  const current = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=${scenario}` : null)
  const baseline = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=moderate` : null)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!profileId) return <NeedProfile />

  const data = current.data
  const role = data?.roles.find((r) => r.role_id === selected) ?? data?.roles[0]
  const moderateRank = baseline.data?.roles.map((r) => r.role_id) ?? []

  async function choose(roleId: string) {
    setBusy(true)
    setError(null)
    try {
      await sendJSON(`/api/profiles/${profileId}/destination`, { body: { role_id: roleId } })
      navigate('/pathway')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Roles that fit · every destination role is scored</span>
          <h1 className="h1">Where your skills can take you</h1>
          <p className="m-0 max-w-[640px] text-graphite">
            Destination roles TalentCorp lists for highly impacted GBS finance roles. Fit compares your levels with what each role needs under the selected scenario; outlook is shown separately with its sources.
          </p>
        </div>
        <ScenarioSwitch />
      </header>

      {current.loading && <Loading what="your matches" />}
      {current.error && <Problem what="your matches" message={current.error} onRetry={current.reload} />}
      {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}

      {data && data.current_role && (
        <div className="card-light flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 text-[13px]">
          <span>
            <span className="font-semibold">Today: {data.current_role.title}</span> · TalentCorp rates it {data.current_impact} (PDF p. {data.current_role.page}).
          </span>
          <span className="text-graphite">Routes it lists: {data.current_role.transitions.length} in GBS{data.current_role.other_sectors.length ? `, ${data.current_role.other_sectors.length} in other sectors` : ''}</span>
        </div>
      )}

      {data && role && (
        <div className="flex flex-wrap items-start gap-5">
          <section aria-label="Ranked roles" className="card-light min-w-0 flex-[1_1_360px] overflow-hidden">
            <div className="cap grid grid-cols-[28px_minmax(0,1fr)_56px] gap-3.5 border-b border-mist px-4 py-3">
              <span>#</span>
              <span>Role</span>
              <span className="text-right">Fit</span>
            </div>
            {data.roles.map((r, i) => {
              const was = moderateRank.indexOf(r.role_id)
              const moved = scenario === 'fast' && was >= 0 ? was - i : 0
              const b = bars(r)
              return (
                <button
                  key={r.role_id}
                  type="button"
                  aria-pressed={r.role_id === role.role_id}
                  onClick={() => setSelected(r.role_id)}
                  className={`grid w-full cursor-pointer grid-cols-[28px_minmax(0,1fr)_56px] items-center gap-x-3.5 border-0 border-b border-mist px-4 py-3.5 text-left hover:bg-fog ${r.role_id === role.role_id ? 'bg-violet-soft' : 'bg-white'}`}
                >
                  <span className="font-mono text-ash">{i + 1}</span>
                  <span className="flex min-w-0 flex-col gap-1.5">
                    <span className="text-[15px] font-semibold">{r.title}</span>
                    <span aria-hidden="true" className="flex h-1 max-w-[240px] overflow-hidden rounded-full bg-mist">
                      <span style={{ width: `${b.ready}%` }} className="bg-[#12a372]" />
                      <span style={{ width: `${b.partly}%` }} className="bg-violet-light" />
                    </span>
                    <span className="flex flex-wrap gap-1.5">
                      {r.listed_transition && <span className="tag bg-observed-bg text-observed">Route from your role</span>}
                      {r.longer_route && <span className="tag bg-weak-bg text-weak">Longer route</span>}
                      {moved !== 0 && <span className="tag bg-estimate-bg text-estimate">{moved > 0 ? `▲ ${moved}` : `▼ ${-moved}`} under Fast</span>}
                    </span>
                  </span>
                  <span className="text-right font-mono text-2xl tracking-tight">{Math.round(r.fit)}</span>
                </button>
              )
            })}
            <p className="m-0 px-4 py-3 text-xs text-graphite">
              {data.scenario_label}: {Math.round(data.intensity * 100)}% of the observed automation-style AI use is assumed to reach these tasks within {data.horizon_years} years. Evidence: {data.evidence.source}, {data.evidence.period}.
            </p>
          </section>

          <div className="flex min-w-0 flex-[1.4_1_480px] flex-col gap-5">
            <Why role={role} chosen={data.destination === role.role_id} busy={busy} onChoose={() => choose(role.role_id)} />
            <section className="card-light flex flex-col gap-3.5 px-6 py-5">
              <h2 className="h2">Your skills gap for this role</h2>
              <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
                {COLUMNS.map((col) => (
                  <div key={col} className="flex flex-col gap-2">
                    <span className={`cap ${GAP_TITLE[col][1]}`}>{GAP_TITLE[col][0]}</span>
                    {role.requirements.filter((r) => r.column === col).map((r) => (
                      <div key={r.skill} className="border-t border-mist pt-2 text-[13px]">
                        <div className="font-medium">{r.skill_name}</div>
                        <div className="font-mono text-[11px] text-ash">you {r.claimed ?? '—'} · needs {r.required}</div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
              {role.uncovered.length > 0 && (
                <p className="m-0 text-xs text-graphite">No verified free course yet for: {role.uncovered.join(', ')}. Ask your employer's L&amp;D team or check HRD Corp programmes.</p>
              )}
            </section>
            <section className="card-light flex flex-col gap-2.5 px-6 py-5">
              <h2 className="h2">Outlook, with its sources</h2>
              {role.outlook.map((o) => (
                <p key={o.text} className="m-0 text-[13px]">
                  <span className={`tag mr-2 ${o.kind === 'observed' ? 'bg-observed-bg text-observed' : 'bg-mist text-graphite'}`}>{o.kind === 'observed' ? 'Observed' : 'Expert view'}</span>
                  {o.text} <span className="text-graphite">({o.source})</span>
                </p>
              ))}
              <div className="flex flex-wrap items-center gap-1.5 border-t border-mist pt-3">
                <span className="text-[13px] text-graphite">Contributes to</span>
                {role.sdgs.map((g) => (
                  <span key={g.target} title={g.how}><SdgTag target={g.target} /></span>
                ))}
              </div>
            </section>
            <RoleTasks key={role.role_id} profileId={profileId} roleId={role.role_id} />
          </div>
        </div>
      )}
    </main>
  )
}
