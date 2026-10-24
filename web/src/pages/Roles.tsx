import { useState } from 'react'
import { useT } from '../i18n'
import { Link, useNavigate } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { Dots, ScenarioSwitch, SdgTag, levelText, JourneyRoute, NextStep } from '../components/journey'
import { CompareRoles, JobPosts, Openings } from '../components/CompareRoles'
import { BestQuestion, MeterRow, WhatIf } from '../components/Decision'
import { ExplainRole } from '../components/ExplainRole'
import { ReportProblem } from '../components/Feedback'
import { RoleTasks } from '../components/RoleTasks'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { GapColumn, MatchesResponse, PackInfo, ProfileData, RoleCard, SensitivityResponse, Situation } from '../types'

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

// Graduates: entry roles TalentCorp lists with a route to this role. Switchers: what carries over.
function ForYou({ role, situation, pack }: { role: RoleCard; situation: Situation; pack: PackInfo | null }) {
  if (situation === 'student') {
    const ways = (pack?.current_roles ?? []).filter((r) => r.transitions.includes(role.role_id))
    if (ways.length === 0) return null
    return (
      <p className="m-0 text-[13px] text-graphite">
        <span className="font-semibold text-void">Ways in:</span> start as {ways.map((w) => w.title).join(', ')}. TalentCorp lists a route from {ways.length === 1 ? 'that role' : 'these roles'} to {role.title} (expert view).
      </p>
    )
  }
  if (situation === 'switcher') {
    const carry = role.requirements.filter((r) => r.column === 'ready').map((r) => r.skill_name)
    return (
      <p className="m-0 text-[13px] text-graphite">
        <span className="font-semibold text-void">What carries over:</span> {carry.length ? `${carry.join(', ')}, at the level this role needs (your own rating).` : 'none of your stated skills yet reach this role’s level; tell us more on the question above.'}
      </p>
    )
  }
  return null
}

type Tab = 'why' | 'gap' | 'tasks' | 'outlook' | 'compare' | 'whatif'
const TABS: [Tab, string][] = [
  ['why', 'Why this score'],
  ['gap', 'Skills gap'],
  ['tasks', 'Tasks and AI'],
  ['outlook', 'Outlook and SDGs'],
  ['compare', 'Compare roles'],
  ['whatif', 'What if'],
]

function RoleDetail({ role, roles, onChoose, chosen, busy, situation, pack }: { role: RoleCard; roles: RoleCard[]; onChoose: () => void; chosen: boolean; busy: boolean; situation: Situation; pack: PackInfo | null }) {
  const { t } = useT()
  const { ready, partly } = bars(role)
  const { profileId, scenario } = useJourney()
  const [tab, setTab] = useState<Tab>('why')
  return (
    <section aria-label={`${role.title}: details`} className="flex min-w-0 flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="eyebrow">Selected role</span>
          <h2 className="m-0 text-[28px] font-semibold leading-tight tracking-[-0.03em]">{role.title}</h2>
          <span className="text-[13px] text-graphite">
            {role.effort_hours} h of verified free courses · about {role.effort_weeks} week{role.effort_weeks === 1 ? '' : 's'} at your pace
          </span>
        </div>
        <span className="flex items-baseline gap-1.5" aria-label={`Fit ${Math.round(role.fit)} out of 100`}>
          <span className="font-mono text-[56px] leading-none tracking-[-0.05em]">{Math.round(role.fit)}</span>
          <span className="font-mono text-[13px] text-graphite">/ 100 fit</span>
        </span>
      </div>
      <div className="flex flex-col gap-1.5">
        <div className="flex h-2 overflow-hidden bg-mist" aria-hidden="true">
          <span style={{ width: `${ready}%` }} className="bg-rising" />
          <span style={{ width: `${partly}%` }} className="bg-violet-light" />
        </div>
        <span className="flex flex-wrap gap-x-4 text-[11px] text-graphite">
          <span><span className="mr-1 inline-block h-2 w-2 bg-rising" />ready now {Math.round(ready)}%</span>
          <span><span className="mr-1 inline-block h-2 w-2 bg-violet-light" />partly there {Math.round(partly)}%</span>
          <span>share of what the role leans on</span>
        </span>
      </div>
      <MeterRow meters={role.meters} range={role.fit_range} />
      <ForYou role={role} situation={situation} pack={pack} />
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn btn-v min-h-[44px]" onClick={onChoose} disabled={busy}>
          {chosen ? 'Your destination ✓ · open the plan' : t('Choose as my destination')}
        </button>
        <JobPosts title={role.title} className="btn min-h-[44px]" />
        <span className="text-[13px] text-graphite">You can change your destination any time.</span>
      </div>

      <div role="tablist" aria-label="About this role" className="flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`panel-${id}`}
            onClick={() => setTab(id)}
            className={`-mb-px shrink-0 cursor-pointer border-0 border-b-2 bg-transparent px-3 py-2.5 text-[13px] ${tab === id ? 'border-violet font-semibold text-void' : 'border-transparent text-graphite hover:text-void'}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="flex min-w-0 flex-col gap-4">
        {tab === 'why' && (
          <>
            {profileId && <ExplainRole key={`${role.role_id}-${scenario}`} profileId={profileId} roleId={role.role_id} scenario={scenario} />}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] border-collapse text-[13px]">
                <thead>
                  <tr className="cap text-left">
                    <th className="py-2 pr-2 font-normal">Skill</th>
                    <th className="px-2 py-2 font-normal">You</th>
                    <th className="px-2 py-2 font-normal">Needs</th>
                    <th className="px-2 py-2 text-right font-normal">Weight</th>
                    <th className="py-2 pl-2 text-right font-normal">Fit points</th>
                  </tr>
                </thead>
                <tbody>
                  {role.requirements.map((r) => (
                    <tr key={r.skill} className="border-t border-line align-top">
                      <td className="py-2.5 pr-2">
                        <span className="font-medium">{r.skill_name}</span>
                        {r.essential && <span className="tag ml-1.5 bg-weak-bg text-weak">Essential</span>}
                        <span className="block text-[11px] text-graphite">{r.shift_reason}</span>
                      </td>
                      <td className="px-2 py-2.5"><Dots level={r.claimed} /></td>
                      <td className="px-2 py-2.5 font-mono">{levelText(r.required)}</td>
                      <td className="px-2 py-2.5 text-right font-mono">{r.weight.toFixed(2)}</td>
                      <td className="py-2.5 pl-2 text-right font-mono font-semibold">{r.contribution.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details className="text-[13px] text-graphite">
              <summary className="cursor-pointer">How the fit is calculated</summary>
              <p className="m-0 mt-2 font-mono text-xs text-void">fit = 100 × Σ w · min(your level ÷ needed level, 1) ÷ Σ w</p>
              <p className="m-0 mt-1.5 text-xs">
                w = how much the role leans on each skill under this scenario (assumption, shown per skill above). Essential skills keep their level and weight in every scenario.
              </p>
            </details>
          </>
        )}
        {tab === 'gap' && (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {COLUMNS.map((col) => (
                <div key={col} className="flex flex-col gap-2">
                  <span className={`cap ${GAP_TITLE[col][1]}`}>{GAP_TITLE[col][0]} · {role.requirements.filter((r) => r.column === col).length}</span>
                  {role.requirements.filter((r) => r.column === col).map((r) => (
                    <div key={r.skill} className="border-t border-line pt-2 text-[13px]">
                      <div className="font-medium">{r.skill_name}</div>
                      <div className="font-mono text-[11px] text-ash">you {levelText(r.claimed)} · needs {levelText(r.required)}</div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            {role.uncovered.length > 0 && (
              <p className="m-0 text-xs text-graphite">No verified free course yet for: {role.uncovered.join(', ')}. Ask your employer&rsquo;s L&amp;D team or check HRD Corp programmes.</p>
            )}
          </>
        )}
        {tab === 'tasks' && profileId && <RoleTasks key={role.role_id} profileId={profileId} roleId={role.role_id} />}
        {tab === 'outlook' && (
          <>
            {role.outlook.map((o) => (
              <p key={o.text} className="m-0 text-[13px]">
                <span className={`tag mr-2 ${o.kind === 'observed' ? 'bg-observed-bg text-observed' : 'bg-mist text-graphite'}`}>{o.kind === 'observed' ? 'Observed' : 'Expert view'}</span>
                {o.text} <span className="text-graphite">({o.source})</span>
              </p>
            ))}
            <div className="flex flex-wrap items-center gap-1.5 border-t border-line pt-3">
              <span className="text-[13px] text-graphite">Contributes to</span>
              {role.sdgs.map((g) => (
                <span key={g.target} title={g.how}><SdgTag target={g.target} /></span>
              ))}
            </div>
            <Openings title={role.title} />
          </>
        )}
        {tab === 'compare' && <CompareRoles roles={roles} />}
        {tab === 'whatif' && profileId && <WhatIf key={`whatif-${role.role_id}`} profileId={profileId} scenario={scenario} role={role} />}
      </div>
      <ReportProblem kinds={['not_my_goal', 'wrong_number', 'unsupported_claim']} targetType="role" targetId={role.role_id} page="roles" />
    </section>
  )
}

export function Roles() {
  const { t } = useT()
  const { profileId, scenario } = useJourney()
  const navigate = useNavigate()
  const current = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=${scenario}` : null)
  const baseline = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=moderate` : null)
  const profile = useApi<{ profile: ProfileData }>(profileId ? `/api/profiles/${profileId}` : null)
  const pack = useApi<PackInfo>('/api/pack')
  const prefs = useApi<{ not_my_goal: string[] }>(profileId ? `/api/profiles/${profileId}/preferences` : null)
  const stability = useApi<SensitivityResponse>(profileId ? `/api/profiles/${profileId}/sensitivity?scenario=${scenario}` : null)
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
    <main className="page">
      <JourneyRoute />
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">My options · every destination role is scored</span>
          <h1 className="h1">{t('Where your skills can take you')}</h1>
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
        <div className="grid items-start gap-8 lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]">
          <section aria-label="Ranked roles" className="flex min-w-0 flex-col lg:sticky lg:top-6">
            <div className="cap grid grid-cols-[24px_minmax(0,1fr)_44px] gap-3 border-b border-line pb-2">
              <span>#</span>
              <span>Role</span>
              <span className="text-right">Fit</span>
            </div>
            {data.roles.map((r, i) => {
              const was = moderateRank.indexOf(r.role_id)
              const moved = scenario === 'fast' && was >= 0 ? was - i : 0
              const b = bars(r)
              const ranks = stability.data?.roles.find((x) => x.role_id === r.role_id)?.ranks
              const on = r.role_id === role.role_id
              return (
                <div key={r.role_id}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => setSelected(r.role_id)}
                  className={`grid w-full cursor-pointer grid-cols-[24px_minmax(0,1fr)_44px] items-start gap-x-3 border-0 border-b border-l-2 border-b-line py-3 pl-2 pr-0 text-left ${on ? 'border-l-violet bg-paper' : 'border-l-transparent bg-transparent hover:bg-paper'}`}
                >
                  <span className="pt-0.5 font-mono text-ash">{i + 1}</span>
                  <span className="flex min-w-0 flex-col gap-1.5">
                    <span className={`text-[14px] leading-snug ${on ? 'font-semibold' : 'font-medium'}`}>{r.title}</span>
                    <span aria-hidden="true" className="flex h-1 max-w-[200px] overflow-hidden bg-mist">
                      <span style={{ width: `${b.ready}%` }} className="bg-rising" />
                      <span style={{ width: `${b.partly}%` }} className="bg-violet-light" />
                    </span>
                    <span className="flex flex-wrap gap-1">
                      {data.destination === r.role_id && <span className="tag bg-violet text-white">Your destination</span>}
                      {r.listed_transition && <span className="tag bg-observed-bg text-observed">Route from your role</span>}
                      {prefs.data?.not_my_goal.includes(r.role_id) && <span className="tag bg-mist text-ash">You said: not your goal</span>}
                      {r.longer_route && <span className="tag bg-weak-bg text-weak">Longer route</span>}
                      {moved !== 0 && <span className="tag bg-estimate-bg text-estimate">{moved > 0 ? `▲ ${moved}` : `▼ ${-moved}`} under Fast</span>}
                      {ranks && Math.min(...ranks) !== Math.max(...ranks) && (
                        <span className="tag bg-estimate-bg text-estimate" title="Rank across AI-adoption intensities from none to stronger than fast">rank {Math.min(...ranks)}–{Math.max(...ranks)} by adoption</span>
                      )}
                    </span>
                  </span>
                  <span className="text-right font-mono text-xl tracking-tight">{Math.round(r.fit)}</span>
                </button>
                <JobPosts title={r.title} className="job-link mb-3 ml-11" />
                </div>
              )
            })}
            <p className="m-0 pt-3 text-[11px] text-graphite">
              {data.scenario_label}: {Math.round(data.intensity * 100)}% of the observed automation-style AI use is assumed to reach these tasks within {data.horizon_years} years. Evidence: {data.evidence.source}, {data.evidence.period}.
            </p>
          </section>

          <div className="flex min-w-0 flex-col gap-6">
            <BestQuestion profileId={profileId} scenario={scenario} onAnswered={() => { current.reload(); baseline.reload(); stability.reload() }} />
            <RoleDetail role={role} roles={data.roles} chosen={data.destination === role.role_id} busy={busy} onChoose={() => choose(role.role_id)} situation={profile.data?.profile.situation ?? 'working'} pack={pack.data} />
          </div>
        </div>
      )}
      <NextStep to="/pathway" label="Open the plan for your role" hint="Next: a free learning plan for the role you chose" />
    </main>
  )
}
