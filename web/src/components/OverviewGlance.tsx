import { Link } from 'react-router-dom'
import { formatWhen, useApi } from '../api'
import { useJourney } from '../state'
import type { ChangesResponse, MatchesResponse, PathwayResponse, ProgressResponse, RoleCard, Run, SourceStatus, TrendsResponse } from '../types'
import type { SeriesForecast } from '../typesAgents'
import { levelText, ScenarioSwitch, SdgTag } from './journey'
import { KindLabel, WhyButton } from './Why'

// Overview "at a glance" (docs/PHASE2_PLAN.md A1): seven short cards, each number with a Why?.
// Fields owner B adds to the role score (C2) are read when present; until then the card shows
// what the API already returns and hides the rest, never a placeholder number.
type ScoredRole = RoleCard & { band?: string; essentials_short?: string[] }

const SNAPSHOT_ITEMS = 3
const RUNS_POLL_MS = 60_000

function TopRoleCard({ matches }: { matches: MatchesResponse }) {
  const role = (matches.roles.find((r) => r.role_id === matches.destination) ?? matches.roles[0]) as ScoredRole | undefined
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
                  {Math.round(role.fit_range.low)} counts the skills you have not stated as none; {Math.round(role.fit_range.high)} counts them at the highest level any requirement needs. Stating more skills narrows the range.
                </p>
              ),
            },
          ]}
        />
        <Link className="text-[13px]" to="/roles">All ranked roles →</Link>
      </div>
    </section>
  )
}

function ChangedCard() {
  const { profileId } = useJourney()
  const changes = useApi<ChangesResponse>(profileId ? `/api/profiles/${profileId}/changes` : null)
  const proposals = changes.data?.proposals ?? []
  const latest = proposals.find((p) => p.actionable) ?? proposals[0]
  return (
    <section className="card-light flex min-w-0 flex-col gap-2.5 p-4" aria-label="What changed for you">
      <span className="cap">What changed for you</span>
      {latest ? (
        <>
          <p className="m-0 text-[14px] font-semibold">
            {latest.report.recommendation_changed ? 'New evidence changes your results' : 'New evidence arrived; your top result stays'}
          </p>
          <p className="m-0 text-[13px] text-graphite">
            {latest.report.before_label} → {latest.report.after_label} · {formatWhen(latest.created_at)}
          </p>
          <Link className="btn mt-auto self-start" to="/changes">{latest.actionable ? 'Review the proposed change' : 'See what changed'}</Link>
        </>
      ) : (
        <p className="m-0 text-[13px] text-graphite">
          {changes.loading ? 'Checking for new evidence…' : 'No new evidence has changed your results since you started. You will see a proposal here when it does.'}
        </p>
      )}
    </section>
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

function TrendsCard({ period }: { period: string }) {
  const { scenario } = useJourney()
  const trends = useApi<TrendsResponse>('/api/trends')
  const forecasts = useApi<SeriesForecast[]>('/api/forecast')
  const data = trends.data
  if (!data) return null
  // Two-year forecast change per group (A2), shown beside the observed change when available.
  const ahead = new Map(
    (forecasts.data ?? [])
      .filter((f) => f.kind === 'employment_share' && f.forecast.length > 0)
      .map((f) => [f.series_id.split(':')[1], (f.forecast.at(-1)?.point ?? 0) - (f.history.at(-1)?.value ?? 0)]),
  )
  const next = (group: string) => {
    const v = ahead.get(group)
    return v === undefined ? '' : ` → ${v > 0 ? '+' : ''}${v.toFixed(2)}`
  }
  const skills = [...data.skills_by_scenario[scenario]].sort((a, b) => b.change - a.change)
  const rising = skills.filter((s) => s.change > 0).slice(0, SNAPSHOT_ITEMS)
  const falling = skills.filter((s) => s.change < 0).slice(-SNAPSHOT_ITEMS).reverse()
  const groups = data.employment.filter((g) => g.change_recent !== null).sort((a, b) => (b.change_recent ?? 0) - (a.change_recent ?? 0))
  const years = groups[0] ? `${data.recent_from}–${groups[0].last}` : ''
  const line = (name: string, value: string, up: boolean) => (
    <li key={name} className="flex justify-between gap-3"><span className="min-w-0">{up ? '↑' : '↓'} {name}</span><span className={`shrink-0 font-mono ${up ? 'text-rising' : 'text-weak'}`}>{value}</span></li>
  )
  return (
    <section className="card-light flex min-w-0 flex-col gap-2.5 p-4 md:col-span-2" aria-label="Trends snapshot">
      <span className="cap">Skills and jobs on the move</span>
      <div className="grid gap-3 text-[13px] sm:grid-cols-2">
        <div className="min-w-0">
          <span className="mb-1 flex flex-wrap items-center gap-1.5 text-[12px] text-graphite">Skills · weight change, {scenario} adoption <KindLabel kind="assumption" /></span>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {rising.map((s) => line(s.name, `+${s.change}%`, true))}
            {falling.map((s) => line(s.name, `${s.change}%`, false))}
          </ul>
        </div>
        <div className="min-w-0">
          <span className="mb-1 flex flex-wrap items-center gap-1.5 text-[12px] text-graphite">Job groups · share of employees {years} <KindLabel kind="observed" /></span>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {groups.slice(0, SNAPSHOT_ITEMS).filter((g) => (g.change_recent ?? 0) > 0).map((g) => line(g.title, `+${g.change_recent}${next(g.group)} pp`, true))}
            {groups.slice(-SNAPSHOT_ITEMS).filter((g) => (g.change_recent ?? 0) < 0).reverse().map((g) => line(g.title, `${g.change_recent}${next(g.group)} pp`, false))}
          </ul>
          {ahead.size > 0 && <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-graphite">past change → forecast next two years <KindLabel kind="estimate" /></span>}
        </div>
      </div>
      <div className="mt-auto flex flex-wrap items-center gap-2">
        <WhyButton
          title="Where these trends come from"
          panes={[
            { key: 'skills', title: 'Skills', hint: 'Assumption applied to observed AI use', body: <p className="m-0">How much each skill's weight in the destination roles moves under {scenario} AI adoption: routine work loses weight and AI-complementing work gains it, in proportion to the automation-style share of AI use on its tasks (Anthropic Economic Index, {period}). It is a scenario rule, not a forecast of jobs.</p> },
            { key: 'groups', title: 'Job groups', hint: 'Observed, then estimated', body: <p className="m-0">Change in each occupation group's share of all employees in Malaysia, in percentage points, {years} (OpenDOSM, wages by occupation). After the arrow: the forecast change over the next two years, from the model that beat keeping the last value in a backtest (or the last value itself when none did). Finance clerks sit in clerical support, accountants in professionals. The Future skills radar shows each model and its range.</p> },
          ]}
        />
        <Link className="text-[13px]" to="/trends">Future skills radar →</Link>
      </div>
    </section>
  )
}

function SdgCard({ destination }: { destination: string | null }) {
  const { profileId, scenario } = useJourney()
  const path = useApi<PathwayResponse>(profileId && destination ? `/api/profiles/${profileId}/pathway?scenario=${scenario}` : null)
  const data = path.data
  const targets = data ? Object.keys(data.sdg_summary).sort() : []
  return (
    <section className="card-light flex min-w-0 flex-col gap-2.5 p-4" aria-label="SDG contribution">
      <span className="cap">Your plan and the SDGs</span>
      {data ? (
        <>
          <p className="m-0 text-[13px]">Your plan contributes to {targets.length} SDG targets:</p>
          <div className="flex flex-wrap gap-1.5">{targets.map((t) => <SdgTag key={t} target={t} />)}</div>
          <div className="mt-auto flex flex-wrap items-center gap-2">
            <WhyButton
              title="How your plan contributes to the SDGs"
              panes={targets.map((t) => ({
                key: t,
                title: `SDG ${t} · ${data.sdg_targets[t]?.title ?? ''}`,
                hint: data.sdg_source,
                body: <ul className="m-0 flex flex-col gap-1.5 pl-4">{data.sdg_summary[t].map((how) => <li key={how}>{how}</li>)}</ul>,
              }))}
            />
            <Link className="text-[13px]" to="/pathway#sdg">SDG contribution →</Link>
          </div>
        </>
      ) : (
        <p className="m-0 text-[13px] text-graphite">{path.loading ? 'Loading your plan…' : 'Choose a destination role to see how your plan contributes to the SDGs.'}</p>
      )}
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
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <TopRoleCard matches={matches.data} />
        <ChangedCard />
        <WeekCard />
        <TrendsCard period={matches.data.evidence.period} />
        <SdgCard destination={matches.data.destination} />
      </div>
      <FreshnessLine />
    </section>
  )
}
