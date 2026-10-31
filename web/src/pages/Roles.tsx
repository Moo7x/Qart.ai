import { ChevronDown, Info } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { Dots, SdgTag, levelText } from '../components/journey'
import { DarkButton, Label, Legend, PageHead, ScenarioSwitch, Segmented, Serif } from '../components/atoms'
import { FitGauge } from '../components/MiniCharts'
import { CompareRoles, JobPosts, Openings } from '../components/CompareRoles'
import { MeterRow, WhatIf } from '../components/Decision'
import { ExplainRole } from '../components/ExplainRole'
import { ReportProblem } from '../components/Feedback'
import { RoleTasks } from '../components/RoleTasks'
import { PayLine, ScoreWhy } from '../components/ScoreWhy'
import { SdgRolesGrid } from '../components/SdgHeatmap'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { GapColumn, MatchesResponse, PackInfo, ProfileData, RoleCard, Situation } from '../types'

// Roles shown before "Show all": enough to compare, few enough to read.
const ROLES_SHOWN = 5

const GAP_TITLE: Record<GapColumn, [string, string]> = {
  ready: ['Ready now', 'text-rising'],
  bridgeable: ['Partly there', 'text-[#5231e0]'],
  missing: ['Still to build', 'text-weak'],
  not_stated: ['Not stated · tell us', 'text-graphite'],
}
const COLUMNS: GapColumn[] = ['ready', 'bridgeable', 'missing', 'not_stated']

/** The SDG goals that matter to the person: saved at once; roles whose fits are close are then
 *  ordered by the goals they serve (the fit never changes), and the plan shows the goal's links. */
function SdgGoals({ profileId, profile, goals, onSaved }: { profileId: string; profile: ProfileData; goals: { id: string; title: string }[]; onSaved: () => void }) {
  const [busy, setBusy] = useState(false)
  const chosen = profile.sdg_priorities
  async function toggle(id: string) {
    setBusy(true)
    try {
      const next = chosen.includes(id) ? chosen.filter((g) => g !== id) : [...chosen, id]
      await sendJSON(`/api/profiles/${profileId}`, { method: 'PUT', body: { ...profile, sdg_priorities: next } })
      onSaved()
    } finally {
      setBusy(false)
    }
  }
  return (
    <div role="group" aria-label="Sustainable Development Goals that matter to you" className="flex flex-wrap items-center gap-2 text-[13px]">
      <span className="font-semibold">Goals that matter to you:</span>
      {goals.map((g) => <button key={g.id} type="button" aria-pressed={chosen.includes(g.id)} disabled={busy} className="q-chip" onClick={() => toggle(g.id)}>SDG {g.id}{g.title ? ` · ${g.title}` : ''}</button>)}
      <span className="text-muted">Roles with close fits move up when they serve your goals; the fit itself never changes.</span>
    </div>
  )
}

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

function RoleDetail({ role, roles, matches, situation, pack }: { role: RoleCard; roles: RoleCard[]; matches: MatchesResponse; situation: Situation; pack: PackInfo | null }) {
  const { ready, partly } = bars(role)
  const { profileId, scenario } = useJourney()
  const [tab, setTab] = useState<Tab>('why')
  return (
    <section aria-label={`${role.title}: details`} className="flex min-w-0 flex-col gap-4">
      <PayLine pay={role.pay} />
      <div className="flex flex-col gap-1.5">
        <div className="flex h-2 overflow-hidden rounded-full bg-mist" aria-hidden="true">
          <span style={{ width: `${ready}%` }} className="bg-rising" />
          <span style={{ width: `${partly}%` }} className="bg-violet-light" />
        </div>
        <span className="flex flex-wrap gap-x-4 text-[11px] text-muted">
          <span><span className="mr-1 inline-block h-2 w-2 bg-rising" />ready now {Math.round(ready)}%</span>
          <span><span className="mr-1 inline-block h-2 w-2 bg-violet-light" />partly there {Math.round(partly)}%</span>
          <span>share of what the role leans on</span>
        </span>
      </div>
      <MeterRow meters={role.meters} range={role.fit_range} />
      <ForYou role={role} situation={situation} pack={pack} />
      <JobPosts title={role.title} className="q-btn self-start" />

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
                      {role.requirement_basis?.[r.skill] && (
                        <div className={`mt-1 text-[11px] ${role.requirement_basis[r.skill].kind === 'assumption' ? 'text-estimate' : 'text-graphite'}`} title={role.requirement_basis[r.skill].source}>
                          {role.requirement_basis[r.skill].kind === 'assumption' ? 'Our assumption' : role.requirement_basis[r.skill].kind === 'talentcorp' ? 'Named by TalentCorp' : 'In this job\'s tasks'}
                        </div>
                      )}
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
            {matches.sdg_roles && (
              <div className="flex flex-col gap-2 border-t border-line pt-3">
                <h3 className="m-0 text-[15px] font-semibold">Compare roles by SDG contribution</h3>
                <SdgRolesGrid roles={matches.sdg_roles} />
              </div>
            )}
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

function RangeBar({ role, i }: { role: RoleCard; i: number }) {
  const fit = Math.round(role.fit)
  const lo = Math.round(role.fit_range.low)
  const hi = Math.round(role.fit_range.high)
  return (
    <span className="r-bar flex min-w-0 items-center gap-2.5">
      <span className="w-[30px] flex-none text-right text-[22px] font-semibold tracking-[-0.02em]">{fit}</span>
      <span role="img" aria-label={`Fit ${fit} out of 100, range ${lo} to ${hi}`} className="relative h-3 flex-auto rounded-full bg-[#f0f0f0]">
        <span className="m-grow absolute inset-y-0 rounded-full bg-range" style={{ left: `${lo}%`, width: `${Math.max(hi - lo, 1)}%`, animationDelay: `${0.25 + i * 0.04}s` }} />
        <span className="m-fade absolute top-1/2 -ml-[7px] -mt-[7px] h-3.5 w-3.5 rounded-full bg-violet shadow-[0_0_0_2px_#fff]" style={{ left: `${fit}%`, animationDelay: `${0.6 + i * 0.04}s` }} />
      </span>
      <span className="flex-none whitespace-nowrap text-xs text-muted">{lo}–{hi}</span>
    </span>
  )
}

export function Roles() {
  const { profileId, scenario } = useJourney()
  const navigate = useNavigate()
  const current = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=${scenario}` : null)
  const baseline = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=moderate` : null)
  const fastView = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=fast` : null)
  const profile = useApi<{ profile: ProfileData }>(profileId ? `/api/profiles/${profileId}` : null)
  const pack = useApi<PackInfo>('/api/pack')
  const prefs = useApi<{ not_my_goal: string[] }>(profileId ? `/api/profiles/${profileId}/preferences` : null)
  const [openId, setOpenId] = useState<string | null | undefined>(undefined) // undefined: the first row
  const [whyFor, setWhyFor] = useState<RoleCard | null>(null)
  const [showAll, setShowAll] = useState(false)
  const [bySdg, setBySdg] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!profileId) return <NeedProfile />

  const data = current.data
  const moderateRank = baseline.data?.roles.map((r) => r.role_id) ?? []
  const fastRank = fastView.data?.roles.map((r) => r.role_id) ?? []
  const goals = profile.data?.profile.sdg_priorities ?? []
  // The goals the destination roles are tagged with (from the API): only these can change an order.
  const roleGoals = (data?.sdg_goals ?? []).map((id) => ({ id, title: '' }))
  const ordered = data ? (bySdg ? [...data.roles].sort((a, b) => (b.serves_goals?.length ?? 0) - (a.serves_goals?.length ?? 0) || b.fit - a.fit) : data.roles) : []
  const listed = showAll ? ordered : ordered.slice(0, ROLES_SHOWN)
  const openRole = openId === undefined ? listed[0]?.role_id : openId
  const skillName = (id: string) => pack.data?.skills.find((s) => s.id === id)?.name ?? id

  async function choose(roleId: string) {
    setBusy(true)
    setError(null)
    try {
      await sendJSON(`/api/profiles/${profileId}/destination`, { body: { role_id: roleId } })
      navigate('/time')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="page gap-6">
      <PageHead
        badge="My options · every destination role is scored"
        title={<>Roles that fit you <Serif>next</Serif></>}
        sub="Destination roles TalentCorp lists for highly impacted GBS finance roles. Fit compares your levels with what each role needs under the selected scenario; outlook is shown separately with its sources."
        right={
          <div className="flex flex-col items-start gap-2 md:items-end">
            <span className="flex items-center gap-2"><ScenarioSwitch /><Label kind="estimate" /></span>
            <Link to="/goal" className="text-[13px]">Have a job posting? Check it against your skills →</Link>
          </div>
        }
      />

      {current.loading && <Loading what="your matches" />}
      {current.error && <Problem what="your matches" message={current.error} onRetry={current.reload} />}
      {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}

      {data && (
        <div className="q-tray flex flex-col gap-4">
          {data.current_role && (
            <div className="q-card flex-row flex-wrap items-center justify-between gap-3 px-5 py-3.5 text-[13px]">
              <span><span className="font-semibold">Today: {data.current_role.title}</span> · TalentCorp rates it {data.current_impact} (PDF p. {data.current_role.page}).{data.current_forecast && <> Qart forecast: <span className="font-semibold">{data.current_forecast.label}</span> ({data.current_forecast.meaning.toLowerCase()})</>}</span>
              <span className="text-muted">Routes it lists: {data.current_role.transitions.length} in GBS{data.current_role.other_sectors.length ? `, ${data.current_role.other_sectors.length} in other sectors` : ''}</span>
            </div>
          )}
          {profile.data && <SdgGoals profileId={profileId} profile={profile.data.profile} goals={roleGoals} onSaved={() => { current.reload(); baseline.reload(); fastView.reload(); profile.reload() }} />}
          <section aria-label="Ranked roles" className="q-card gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[13px]"><span className="font-semibold text-violet">All {data.roles.length} destination roles</span> <span className="text-muted">· {data.scenario_label} · ordered by fit and the Qart forecast (a growing role moves up, a shrinking one down; the fit shown is unchanged)</span></span>
              <Legend items={[{ swatch: '#6c47ff', text: 'Fit today (estimate)' }, { swatch: '#d9d0ff', text: 'Range if unrated skills are low or working (assumption)' }]} />
            </div>
            {goals.length > 0 && (
              <Segmented label="Order roles by" value={bySdg ? 'sdg' : 'fit'} onChange={(v) => setBySdg(v === 'sdg')} options={[{ id: 'fit', text: 'Best fit' }, { id: 'sdg', text: 'My SDG goals first' }]} />
            )}
            <div className="r-axis" aria-hidden="true">
              <span />
              <span className="text-xs text-muted">Role</span>
              <span className="flex items-center gap-2.5">
                <span className="w-[30px] flex-none text-right text-xs text-muted">fit</span>
                <span className="relative h-4 flex-auto">
                  {[0, 25, 50, 75, 100].map((v) => <span key={v} className="absolute text-[11px] text-muted-2" style={{ left: `${v}%`, transform: `translateX(${v === 0 ? 0 : v === 100 ? -100 : -50}%)` }}>{v}</span>)}
                </span>
                <span className="flex-none text-xs text-muted">range</span>
              </span>
              <span className="text-xs text-muted">What stands between</span>
              <span />
            </div>
            <ol className="m-0 list-none p-0">
              {listed.map((r, i) => {
                const open = r.role_id === openRole
                const rankMove = moderateRank.indexOf(r.role_id) - fastRank.indexOf(r.role_id)
                const short = r.essentials_short.length
                const trend = r.in_demand.find((s) => (r.requirements.find((q) => q.skill === s)?.claimed ?? 0) < (r.requirements.find((q) => q.skill === s)?.required ?? 0))
                return (
                  <li key={r.role_id} className="border-t border-[#f0f0f0]">
                    <button type="button" className="r-row" aria-expanded={open} aria-controls={`r-detail-${r.role_id}`} onClick={() => setOpenId(open ? null : r.role_id)}>
                      <span className="text-[13px] font-semibold text-muted">{String(i + 1).padStart(2, '0')}</span>
                      <span className="flex min-w-0 flex-col gap-1 text-left">
                        <span className="text-[15px] font-semibold leading-snug">{r.title}</span>
                        <span className="flex flex-wrap gap-1">
                          {data.destination === r.role_id && <span className="whitespace-nowrap rounded-full bg-violet px-2 py-0.5 text-[11px] font-semibold text-white">your destination</span>}
                          {r.forecast && <span title={`${r.forecast.meaning} ${r.forecast.reasons.join('; ')}`} className="whitespace-nowrap rounded-full bg-estimate-bg px-2 py-0.5 text-[11px] font-semibold text-estimate">{r.forecast.label} · Qart forecast</span>}
                          <span className="whitespace-nowrap rounded-full bg-mist px-2 py-0.5 text-[11px] text-graphite">{r.direction === 'adjacent' ? 'adjacent move' : 'stretch move'}</span>
                          {r.listed_transition && <span className="whitespace-nowrap rounded-full bg-tray px-2 py-0.5 text-[11px] font-medium">listed route from your role</span>}
                          {prefs.data?.not_my_goal.includes(r.role_id) && <span className="whitespace-nowrap rounded-full bg-mist px-2 py-0.5 text-[11px] text-muted">you said: not your goal</span>}
                          {rankMove !== 0 && moderateRank.length > 0 && fastRank.length > 0 && <span className="q-label q-label-estimate">{rankMove > 0 ? `▲ ${rankMove}` : `▼ ${-rankMove}`} if AI moves fast</span>}
                          {(r.serves_goals ?? []).map((g) => <span key={g} className="whitespace-nowrap rounded-full bg-rising-bg px-2 py-0.5 text-[11px] text-rising">serves SDG {g} · your goal</span>)}
                        </span>
                      </span>
                      <RangeBar role={r} i={i} />
                      <span className="r-meta flex min-w-0 flex-col gap-0.5 text-xs text-[#404040]">
                        <span>{short ? `${short} essential${short === 1 ? '' : 's'} short` : 'no essential short'} · {r.effort_hours ? `${r.effort_hours} h study` : 'no verified course yet'}</span>
                        {trend ? <span className="font-semibold text-rising">↑ {skillName(trend)} in demand</span> : <span className="text-muted">no in-demand skill listed</span>}
                      </span>
                      <ChevronDown size={16} aria-hidden="true" className={open ? 'rotate-180' : ''} />
                    </button>
                    {open && (
                      <div id={`r-detail-${r.role_id}`} className="j-step j-fwd r-detail flex flex-col gap-4">
                        <div className="flex flex-wrap items-start gap-x-6 gap-y-3">
                          {r.band && (
                            <div className="q-card w-[220px] flex-none items-center gap-1 border border-[#f0f0f0] p-3">
                              <span className="self-start text-[13px] font-semibold">Your fit</span>
                              <FitGauge fit={r.fit} band={r.band} thresholds={data.bands.thresholds} caption={`${data.scenario_label} · estimate`}>
                                <button type="button" className="q-btn mt-1 min-h-[36px] bg-mist px-3 text-xs" onClick={() => setWhyFor(r)}>What these numbers mean</button>
                              </FitGauge>
                            </div>
                          )}
                          <div className="flex min-w-0 flex-[1_1_300px] flex-col gap-2">
                            <span className="flex flex-wrap items-center gap-1.5 text-[13px]">Fit {Math.round(r.fit)} <Label kind="estimate" /> {r.band && <span className="rounded-full bg-[#fef3c7] px-2 py-0.5 text-xs font-semibold capitalize text-[#92400e]">{r.band} band</span>} range {Math.round(r.fit_range.low)}–{Math.round(r.fit_range.high)} <Label kind="assumption" /></span>
                            <p className="m-0 text-[13px]">Essentials still short: <b className="font-semibold">{r.essentials_short.map(skillName).join(', ') || 'none'}</b></p>
                            {trend && <p className="q-src">{skillName(trend)}: in demand · TalentCorp (2024), PDF p. 25</p>}
                            <p className="q-src">Study: {r.effort_hours ? `${r.effort_hours} h of free courses, about ${r.effort_weeks} week${r.effort_weeks === 1 ? '' : 's'} at your pace (estimate)` : 'no verified free course covers its gaps yet'}</p>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 self-end">
                            <button type="button" className="q-btn q-why" onClick={() => setWhyFor(r)} aria-label={`Why? How ${r.title} scores ${Math.round(r.fit)}`}><Info size={16} aria-hidden="true" />Why?</button>
                            <Link to="/trends" className="inline-flex min-h-[44px] items-center px-1 text-[13px] font-medium">See the evidence</Link>
                            <Link to="/future" className="inline-flex min-h-[44px] items-center px-1 text-[13px] font-medium">Compare futures</Link>
                            {data.destination === r.role_id ? (
                              <DarkButton onClick={() => choose(r.role_id)} disabled={busy}>Continue with this role</DarkButton>
                            ) : (
                              <button type="button" className="q-btn" disabled={busy} onClick={() => choose(r.role_id)}>Choose and continue</button>
                            )}
                          </div>
                        </div>
                        <RoleDetail role={r} roles={data.roles} matches={data} situation={profile.data?.profile.situation ?? 'working'} pack={pack.data} />
                      </div>
                    )}
                  </li>
                )
              })}
            </ol>
            {ordered.length > ROLES_SHOWN && (
              <button type="button" className="q-btn self-start" aria-expanded={showAll} onClick={() => setShowAll((v) => !v)}>{showAll ? `Show the top ${ROLES_SHOWN}` : `Show all ${ordered.length} roles`}</button>
            )}
            <p className="q-src">
              {data.scenario_label}: {Math.round(data.intensity * 100)}% of the observed automation-style AI use is assumed to reach these tasks within {data.horizon_years} years. Evidence: {data.evidence.source}, {data.evidence.period}. Fit measures skill coverage, not your chance of getting hired.
            </p>
          </section>
        </div>
      )}
      {whyFor && data && <ScoreWhy role={whyFor} matches={data} onClose={() => setWhyFor(null)} />}
    </main>
  )
}
