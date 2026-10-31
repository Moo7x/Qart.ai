import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ScoutButton } from './AgentWindow'
import { ProgressCheckButton } from './ProgressCheck'
import { formatWhen, useApi } from '../api'
import { useJourney } from '../state'
import type { MatchesResponse, ProgressResponse, RoleCard, Run, SourceStatus } from '../types'
import type { RaiseOption } from '../typesScoring'
import { levelText, ScenarioSwitch } from './journey'
import { KindLabel, WhyButton } from './Why'

// Overview "at a glance" (docs/PHASE2_PLAN.md A1): the role you are heading for and this week's
// steps, each number with a Why?.
// The role score's band, range rule and "what would raise it" come from owner B's C2 fields;
// an absent field hides its line, never a placeholder number.
const RAISE_SHOWN = 3
const VIA: Record<RaiseOption['via'], string> = { study: 'study', practice: 'practice at work', check: 'a progress check' }

function raiseText(r: RaiseOption): string {
  return `+${r.points.toFixed(1)} points: ${r.skill_name} ${levelText(r.from_level)} → ${levelText(r.to_level)} by ${VIA[r.via]}`
}

const RUNS_POLL_MS = 60_000

function TopRoleCard({ matches }: { matches: MatchesResponse }) {
  const role: RoleCard | undefined = matches.roles.find((r) => r.role_id === matches.destination) ?? matches.roles[0]
  if (!role) return null
  const short = role.essentials_short ?? role.essential_gaps
  const rows = role.requirements
  return (
    <section className="card-light flex min-w-0 flex-col gap-2.5 p-4" aria-label="Your top role">
      <div className="flex items-baseline justify-between gap-2">
        <span className="cap">{matches.destination ? 'Your destination' : 'Your best-fitting role'}</span>
        <KindLabel kind="estimate" />
      </div>
      <h3 className="m-0 text-lg font-semibold leading-snug">{role.title}</h3>
      <div className="flex flex-wrap items-end gap-3">
        <span className="font-mono text-[34px] leading-none">{Math.round(role.fit)}</span>
        <span className="pb-1 text-[13px] text-graphite">
          / 100 fit{role.band ? ` · ${role.band}` : ''} · range {Math.round(role.fit_range.low)}–{Math.round(role.fit_range.high)}
        </span>
      </div>
      <p className="m-0 text-[13px]">
        {short.length > 0 ? <>Essentials still short: <span className="font-semibold">{short.join(', ')}</span></> : 'Your claims cover every essential skill.'}
      </p>
      {role.raise && role.raise.length > 0 && <p className="m-0 text-[13px]">Biggest raise: <span className="font-semibold">{raiseText(role.raise[0])}</span></p>}
      <div className="mt-auto flex flex-wrap items-center gap-2">
        <WhyButton
          title={`Why ${role.title} scores ${Math.round(role.fit)}`}
          panes={[
            {
              key: 'formula',
              title: 'How the fit is calculated',
              hint: `${matches.scenario_label} · weights are an assumption, levels are your claims`,
              body: (
                <div className="flex flex-col gap-2">
                  <p className="m-0 font-mono text-[12px]">fit = 100 × Σ weight × min(you ÷ needed, 1) ÷ Σ weight</p>
                  <table className="w-full border-collapse text-[12px]">
                    <thead>
                      <tr className="text-left text-graphite">
                        <th className="py-1 pr-2 font-normal">Skill</th><th className="py-1 pr-2 font-normal">Weight</th><th className="py-1 pr-2 font-normal">You</th><th className="py-1 pr-2 font-normal">Needs</th><th className="py-1 font-normal">Points</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr key={r.skill} className="border-t border-line">
                          <td className="py-1 pr-2">{r.skill_name}{r.essential ? ' · essential' : ''}</td>
                          <td className="py-1 pr-2 font-mono">{r.weight.toFixed(2)}</td>
                          <td className="py-1 pr-2 font-mono">{levelText(r.claimed)}</td>
                          <td className="py-1 pr-2 font-mono">{levelText(r.required)}</td>
                          <td className="py-1 font-mono">{r.contribution.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="m-0 text-[12px] text-graphite">
                    Requirements: TalentCorp (2024) GBS study. Weights shift with the scenario using observed AI use ({matches.evidence.source}, {matches.evidence.period}); essentials never shift.
                  </p>
                </div>
              ),
            },
            {
              key: 'range',
              title: 'The range',
              hint: 'Assumption',
              body: (
                <p className="m-0">
                  {role.fit_range.basis ?? `${Math.round(role.fit_range.low)} counts the skills you have not stated as none; ${Math.round(role.fit_range.high)} counts them at the highest level any requirement needs.`} Stating more skills narrows the range.
                </p>
              ),
            },
            ...(role.raise && role.raise.length > 0 ? [{
              key: 'raise',
              title: 'What would raise it',
              hint: 'Each option re-scored with only that one change',
              body: (
                <ul className="m-0 flex flex-col gap-1.5 pl-4">
                  {role.raise.slice(0, RAISE_SHOWN).map((r) => <li key={`${r.skill}-${r.via}`}>{raiseText(r)}</li>)}
                </ul>
              ),
            }] : []),
          ]}
        />
        <Link className="text-[13px]" to="/roles">All ranked roles →</Link>
      </div>
      <GapScout role={role} />
    </section>
  )
}

// The resource scout for one of the role's gaps, chosen by the person (essentials first).
function GapScout({ role }: { role: RoleCard }) {
  const { profileId } = useJourney()
  const gaps = role.requirements
    .filter((r) => r.column !== 'ready')
    .sort((a, b) => Number(b.essential) - Number(a.essential) || b.weight - a.weight)
  const [pick, setPick] = useState(gaps[0]?.skill ?? '')
  const chosen = gaps.find((g) => g.skill === pick) ?? gaps[0]
  if (!chosen) return null
  return (
    <div className="flex flex-col gap-2 border-t border-line pt-3">
      <label className="flex flex-col gap-1 text-[12px]">
        <span className="cap">Find learning material for a gap</span>
        <select className="min-h-[40px] rounded-md border border-hairline bg-paper px-2 text-[13px]" value={chosen.skill} onChange={(e) => setPick(e.target.value)}>
          {gaps.map((g) => <option key={g.skill} value={g.skill}>{g.skill_name}{g.essential ? ' · essential' : ''}</option>)}
        </select>
      </label>
      <ScoutButton key={chosen.skill} skill={chosen.skill} skillName={chosen.skill_name} profileId={profileId} />
      <ProgressCheckButton key={`check-${chosen.skill}`} skill={chosen.skill} skillName={chosen.skill_name} profileId={profileId} />
    </div>
  )
}

function WeekCard() {
  const { profileId, scenario } = useJourney()
  const progress = useApi<ProgressResponse>(profileId ? `/api/profiles/${profileId}/progress?scenario=${scenario}` : null)
  const plan = progress.data?.plan
  return (
    <section className="card-light flex min-w-0 flex-col gap-2.5 p-4" aria-label="Your next step this week">
      <div className="flex items-baseline justify-between gap-2">
        <span className="cap">This week</span>
        {plan && <KindLabel kind="estimate" />}
      </div>
      {plan ? (
        plan.this_week.length > 0 ? (
          <>
            <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-[13px]">
              {plan.this_week.map((s) => <li key={s.id}><span className="font-semibold">{s.title}</span> <span className="font-mono text-graphite">· {s.hours} h</span></li>)}
            </ul>
            <p className="m-0 text-[12px] text-graphite">Within your {plan.weekly_hours} h a week · {plan.steps_done} of {plan.steps} steps done</p>
          </>
        ) : (
          <p className="m-0 text-[13px]">Every planned step is done. Review your levels on your plan.</p>
        )
      ) : (
        <p className="m-0 text-[13px] text-graphite">{progress.loading ? 'Loading your plan…' : 'Choose a destination role to get a week-by-week plan.'}</p>
      )}
      {!progress.loading && <Link className="btn btn-v mt-auto self-start" to={plan ? '/pathway' : '/roles'}>{plan ? 'Open my plan →' : 'Choose a role →'}</Link>}
    </section>
  )
}

function FreshnessLine() {
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=1', RUNS_POLL_MS)
  const sources = useApi<SourceStatus[]>('/api/sources')
  const latest = runs.data?.[0]
  const fetched = (sources.data ?? []).filter((s) => s.last_fetched).sort((a, b) => (b.last_fetched ?? '').localeCompare(a.last_fetched ?? ''))
  const failing = (sources.data ?? []).filter((s) => s.last_status === 'failed')
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 font-mono text-[12px] text-graphite">
      <span>Last pipeline run: {runs.loading && !latest ? '…' : latest ? `${formatWhen(latest.finished_at ?? latest.started_at)} · ${latest.status}` : 'none yet'}</span>
      <span>Newest data fetched: {sources.loading ? '…' : fetched[0] ? formatWhen(fetched[0].last_fetched) : 'not yet'}</span>
      {failing.length > 0 && <span className="text-weak">{failing.length} source(s) failed last time; showing their last good data</span>}
      <WhyButton
        label="Sources"
        title="Where the evidence comes from"
        panes={(sources.data ?? []).map((s) => ({
          key: s.id,
          title: s.name,
          hint: s.publisher,
          body: (
            <dl className="m-0 grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-1">
              <dt className="cap">Fetched</dt><dd className="m-0">{s.last_fetched ? formatWhen(s.last_fetched) : 'not yet'}</dd>
              <dt className="cap">Last run</dt><dd className="m-0">{s.last_status ?? '—'}{s.last_status === 'failed' && s.serving_snapshot_from ? ` · showing the last good data, fetched ${formatWhen(s.serving_snapshot_from)}` : ''}</dd>
              <dt className="cap">Shows</dt><dd className="m-0">{s.shows}</dd>
              <dt className="cap">Cadence</dt><dd className="m-0">{s.cadence}</dd>
            </dl>
          ),
        }))}
      />
    </div>
  )
}

export function OverviewGlance() {
  const { profileId, scenario } = useJourney()
  const matches = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=${scenario}` : null)
  if (!profileId || !matches.data) return null
  return (
    <section className="flex flex-col gap-3" aria-label="Your picture at a glance">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="h2">Your picture at a glance</h2>
        <ScenarioSwitch />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <TopRoleCard matches={matches.data} />
        <WeekCard />
      </div>
      <FreshnessLine />
    </section>
  )
}
