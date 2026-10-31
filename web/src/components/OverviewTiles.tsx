import { Info } from 'lucide-react'
import { useState } from 'react'
import { formatWhen, useApi } from '../api'
import type { RadarOut } from '../apiTypes'
import { useJourney } from '../state'
import type { ChangesResponse, MatchesResponse, ProgressResponse, Run } from '../types'
import { Label, ScenarioSwitch, SCENARIO_TEXT, VividNumber, VividTile } from './atoms'
import { ScoreWhy } from './ScoreWhy'
import { Loading, Problem } from './ui'

const VIA: Record<string, string> = { study: 'study', practice: 'practice at work', check: 'a progress check' }
const level = (v: number | null) => (v === null ? '—' : `${v}/5`)

/** The three vivid tiles at the top of the Overview (design-prototype/ pages.py overview): the
 *  destination, this week's study and what changed. Every number comes from the API. */
export function OverviewTiles() {
  const { profileId, scenario } = useJourney()
  const matches = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=${scenario}` : null)
  const progress = useApi<ProgressResponse>(profileId ? `/api/profiles/${profileId}/progress?scenario=${scenario}` : null)
  const radar = useApi<RadarOut>(profileId ? `/api/profiles/${profileId}/radar?scenario=${scenario}` : null)
  const changes = useApi<ChangesResponse>(profileId ? `/api/profiles/${profileId}/changes` : null)
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=1')
  const [why, setWhy] = useState(false)
  if (matches.loading) return <Loading what="your overview" />
  if (matches.error) return <Problem what="your overview" message={matches.error} onRetry={matches.reload} />
  const data = matches.data
  if (!data) return null
  const role = data.roles.find((r) => r.role_id === data.destination) ?? data.roles[0]
  const raise = role?.raise[0]
  const plan = progress.data?.plan
  const week = plan?.this_week ?? []
  const weekHours = Math.round(week.reduce((s, w) => s + w.hours, 0) * 10) / 10
  const signals = (radar.data?.field_signals ?? []).filter((s) => s.points.length > 0).slice(0, 2)
  const fresh = changes.data?.proposals.filter((p) => p.actionable) ?? []
  const run = runs.data?.[0]
  return (
    <div className="q-g3">
      {role && (
        <VividTile theme="lavender" pill={data.destination ? 'your destination' : 'your best fit today'} to="/roles" toLabel="All ranked roles" label="Your destination" className="q-span2 min-h-[380px]">
          <h2 className="m-0 max-w-[520px] text-[clamp(24px,3vw,34px)] font-normal leading-[1.15] tracking-[-0.02em]">{role.title}</h2>
          <div className="flex flex-wrap items-end gap-x-4 gap-y-2.5">
            <VividNumber value={Math.round(role.fit)} size={92} />
            <span className="flex flex-col gap-2 pb-1.5">
              <span className="text-[15px] text-white/80">/ 100 fit · {SCENARIO_TEXT[scenario]}</span>
              <span className="flex flex-wrap items-center gap-1.5">
                <Label kind="estimate" />
                {role.band && <span className="rounded-full bg-[#fef3c7] px-2 py-0.5 text-xs font-semibold capitalize text-[#92400e]">{role.band} band</span>}
                <span className="text-[13px] text-white/80">range {Math.round(role.fit_range.low)}–{Math.round(role.fit_range.high)}</span>
                <Label kind="assumption" />
              </span>
            </span>
          </div>
          <p className="m-0 max-w-[560px] text-[15px] leading-normal text-white/80">
            Essentials still short: <b className="font-semibold text-white">{role.essentials_short.length ? role.requirements.filter((r) => role.essentials_short.includes(r.skill)).map((r) => r.skill_name).join(', ') : 'none'}</b>.
            {raise && <> Biggest raise: <b className="font-semibold text-white">+{raise.points.toFixed(1)} points: {raise.skill_name} {level(raise.from_level)} → {level(raise.to_level)} by {VIA[raise.via]}</b>.</>}
          </p>
          <div className="mt-auto flex flex-wrap items-center gap-2.5">
            <button type="button" className="q-btn q-why" onClick={() => setWhy(true)} aria-label={`Why? How the ${role.title} fit of ${Math.round(role.fit)} is calculated`}><Info size={16} aria-hidden="true" />Why?</button>
            <ScenarioSwitch />
          </div>
          <p className="m-0 text-xs text-white/80">Requirements: {role.outlook.find((o) => o.kind === 'expert')?.source ?? 'TalentCorp (2024) GBS study'}. Fit measures weighted skill-requirement coverage, not your chance of getting hired.</p>
          {why && <ScoreWhy role={role} matches={data} onClose={() => setWhy(false)} />}
        </VividTile>
      )}
      <VividTile theme="sky" pill="this week" to="/pathway" toLabel="Open my plan" label="This week" className="min-h-[380px]">
        {!data.destination && <p className="m-0 text-[15px] text-white/85">Choose a role to get a weekly study plan.</p>}
        {data.destination && plan && (
          <>
            <div className="flex flex-wrap items-end gap-2.5">
              <VividNumber value={`${weekHours} h`} size={68} />
              <span className="pb-1.5"><Label kind="estimate" /></span>
            </div>
            <span className="text-[15px] text-white/85">study plan, within your {plan.weekly_hours} h a week</span>
            <ul className="m-0 flex list-none flex-col p-0">
              {week.map((w) => (
                <li key={w.id} className="flex justify-between gap-3 border-t border-white/20 py-2 text-sm">
                  <span>{w.title}</span><span className="whitespace-nowrap text-white/85">{w.hours} h</span>
                </li>
              ))}
              {week.length === 0 && <li className="border-t border-white/20 py-2 text-sm">{progress.data?.paused ? 'Your plan is paused.' : 'No study step left: record your practice on the plan.'}</li>}
            </ul>
            <span className="mt-auto text-[13px] text-white/85">{plan.steps_done} of {plan.steps} steps done · your own record</span>
          </>
        )}
      </VividTile>
      <VividTile theme="lime" pill="what changed" to="/changes" toLabel="See what changed" label="What changed for you" className="min-h-[340px]">
        {signals.map((s, i) => {
          const last = s.points[s.points.length - 1]
          const source = s.sources[0] as { name?: string } | undefined
          return (
            <div key={s.id} className="flex flex-col gap-1">
              <span className="flex flex-wrap items-end gap-2.5">
                <VividNumber value={`${Math.round(last.value * 100) / 100}${s.unit.startsWith('%') ? '%' : ` ${s.unit}`}`} size={i === 0 ? 64 : 28} />
                <span className="pb-1"><Label kind={s.kind === 'observed' ? 'observed' : 'assumption'} /></span>
              </span>
              <span className="text-sm leading-snug text-[#33402a]">{s.title} · {source?.name ?? s.evidence[0]?.source_id ?? ''} · {last.period}</span>
            </div>
          )
        })}
        {radar.data && signals.length === 0 && <p className="m-0 text-sm text-[#33402a]">No signal for your field is stored yet (missing, not zero).</p>}
        <p className="m-0 mt-auto text-sm leading-normal">
          {fresh.length ? <><b className="font-semibold">{fresh.length} update{fresh.length === 1 ? '' : 's'} to review.</b> New evidence would change your results; you decide whether to accept.</> : <><b className="font-semibold">Your top result stays.</b> No new evidence has changed your results since you started.</>}
        </p>
        <span className="text-[13px] text-[#33402a]">Last pipeline run: {run ? `${formatWhen(run.finished_at ?? run.started_at)} · ${run.status}` : 'no run yet'}</span>
      </VividTile>
    </div>
  )
}
