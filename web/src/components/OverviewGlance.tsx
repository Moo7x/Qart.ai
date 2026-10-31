import { Link } from 'react-router-dom'
import { formatWhen, useApi } from '../api'
import type { MatchesResponse, RoleCard, Run, SourceStatus } from '../types'
import type { RaiseOption } from '../typesScoring'
import { levelText } from './journey'
import { KindLabel, WhyButton } from './Why'

// "Where you're heading" on the Overview (docs/PHASE2_PLAN.md A1): the destination's fit as a ring
// with its range, the essentials still short and the one change that would raise it most, each
// with a Why?. The band, range rule and "what would raise it" come from owner B's C2 fields; an
// absent field hides its line, never a placeholder number.
const RAISE_SHOWN = 3
const VIA: Record<RaiseOption['via'], string> = { study: 'study', practice: 'practice at work', check: 'a progress check' }

function raiseText(r: RaiseOption): string {
  const from = r.from_level === null || r.from_level === undefined ? 'not rated' : levelText(r.from_level)
  return `+${r.points.toFixed(1)} points: ${r.skill_name} ${from} → ${levelText(r.to_level)} by ${VIA[r.via]}`
}

const RUNS_POLL_MS = 60_000
const RING = 2 * Math.PI * 70

export const destinationOf = (matches: MatchesResponse): RoleCard | undefined => matches.roles.find((r) => r.role_id === matches.destination) ?? matches.roles[0]

function FitRing({ fit, low, high, band }: { fit: number; low: number; high: number; band: string | null | undefined }) {
  const arc = (from: number, to: number) => ({ strokeDasharray: `${(RING * Math.max(to - from, 0.5)) / 100} ${RING}`, strokeDashoffset: `${(-RING * from) / 100}` })
  return (
    <svg viewBox="0 0 200 200" className="mx-auto h-[180px] w-[180px]" role="img" aria-label={`Fit ${Math.round(fit)} out of 100${band ? `, ${band}` : ''}, range ${Math.round(low)} to ${Math.round(high)}`}>
      <circle cx="100" cy="100" r="88" fill="none" stroke="#d9d0ff" strokeWidth="2" strokeDasharray="2 6" />
      <circle cx="100" cy="100" r="70" fill="#fff" stroke="#eeeef0" strokeWidth="12" />
      <circle cx="100" cy="100" r="70" fill="none" stroke="#d9d0ff" strokeWidth="12" transform="rotate(-90 100 100)" style={arc(low, high)} />
      <circle cx="100" cy="100" r="70" fill="none" stroke="#6c47ff" strokeWidth="12" strokeLinecap="round" transform="rotate(-90 100 100)" style={arc(0, fit)} />
      <text x="100" y="106" textAnchor="middle" className="fill-ink font-mono text-[40px]">{Math.round(fit)}</text>
      <text x="100" y="128" textAnchor="middle" className="fill-muted text-[11px]">fit / 100{band ? ` · ${band}` : ''}</text>
    </svg>
  )
}

/** The destination's fit, with Why? and a way to every ranked role. */
export function FitCard({ matches }: { matches: MatchesResponse }) {
  const role = destinationOf(matches)
  if (!role) return null
  const rows = role.requirements
  // The API sends skill ids; show the names.
  const short = (role.essentials_short ?? role.essential_gaps).map((id) => rows.find((r) => r.skill === id)?.skill_name ?? id)
  return (
    <section aria-label="Your destination" className="flex flex-col gap-2 rounded-[28px] bg-white p-5 sm:p-6">
      <div className="flex items-start justify-between gap-2">
        <h2 className="m-0 text-[18px] font-medium leading-snug">{role.title}</h2>
        <KindLabel kind="estimate" />
      </div>
      <span className="text-[12px] text-muted">{matches.destination ? 'Your destination' : 'Your best-fitting role'} · {matches.scenario_label}</span>
      <FitRing fit={role.fit} low={role.fit_range.low} high={role.fit_range.high} band={role.band} />
      <p className="m-0 text-[13px] leading-relaxed text-[#404040]">
        Range {Math.round(role.fit_range.low)}–{Math.round(role.fit_range.high)}. {short.length > 0 ? <>Essentials still short: <b className="text-ink">{short.join(', ')}</b>.</> : 'Your claims cover every essential skill.'}
      </p>
      <div className="flex flex-wrap items-center gap-2 pt-1">
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
        <Link className="q-btn q-btn-dark ml-auto py-2 pl-5 pr-5" to="/roles">All ranked roles</Link>
      </div>
    </section>
  )
}

/** The one change that would raise the fit most, drawn on the 0–100 fit line. */
export function RaiseCard({ matches }: { matches: MatchesResponse }) {
  const role = destinationOf(matches)
  const best = role?.raise?.[0]
  if (!role || !best) return null
  const fit = role.fit
  const gain = Math.min(best.points, 100 - fit)
  const high = Math.max(role.fit_range.high, fit + gain)
  return (
    <section aria-label="Biggest raise" className="flex flex-1 flex-col gap-3 rounded-[28px] bg-white p-5 sm:p-6">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="m-0 text-[16px] font-medium">Biggest raise</h2>
        <span className="text-[28px] tracking-tight">+{best.points.toFixed(1)}</span>
      </div>
      <div role="img" aria-label={`Fit ${Math.round(fit)} now, about ${Math.round(fit + gain)} with this change, range up to ${Math.round(high)}`} className="flex h-9 gap-1">
        <span className="rounded-l-[14px] rounded-r bg-violet" style={{ flex: Math.max(fit, 2) }} />
        <span className="rounded bg-ink" style={{ flex: Math.max(gain, 2) }} />
        <span className="rounded-l rounded-r-[14px] bg-range" style={{ flex: Math.max(high - fit - gain, 2) }} />
      </div>
      <div className="flex justify-between text-[11px] text-muted"><span>now {Math.round(fit)}</span><span>→ about {Math.round(fit + gain)}</span><span>range to {Math.round(high)}</span></div>
      <p className="m-0 text-[13px] leading-relaxed text-[#404040]">{raiseText(best).replace(/^\+[\d.]+ points: /, '')}. Points are an estimate.</p>
      {role.raise && role.raise.length > 1 && (
        <div className="flex flex-col gap-2.5 border-t border-[#eeeef0] pt-3">
          <span className="text-[12px] font-semibold">Other ways to raise it</span>
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {role.raise.slice(1, RAISE_SHOWN + 1).map((r) => (
              <li key={`${r.skill}-${r.via}`} className="flex flex-col gap-1 text-[12px] leading-snug">
                <span className="flex items-baseline justify-between gap-2"><span className="min-w-0">{r.skill_name}</span><span className="font-mono font-semibold">+{r.points.toFixed(1)}</span></span>
                <span aria-hidden="true" className="block h-1.5 overflow-hidden rounded-full bg-[#eeeef0]"><span className="block h-full rounded-full bg-[#9d86ff]" style={{ width: `${Math.min(100, (100 * r.points) / best.points)}%` }} /></span>
                <span className="text-muted">{r.from_level === null || r.from_level === undefined ? 'not rated' : levelText(r.from_level)} → {levelText(r.to_level)} by {VIA[r.via]}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

export function FreshnessLine() {
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=1', RUNS_POLL_MS)
  const sources = useApi<SourceStatus[]>('/api/sources')
  const latest = runs.data?.[0]
  const fetched = (sources.data ?? []).filter((s) => s.last_fetched).sort((a, b) => (b.last_fetched ?? '').localeCompare(a.last_fetched ?? ''))
  const failing = (sources.data ?? []).filter((s) => s.last_status === 'failed')
  return (
    <div className="flex flex-wrap items-center gap-2 font-mono text-[12px] text-graphite">
      <span className="rounded-full bg-white px-3.5 py-2">Last pipeline run: {runs.loading && !latest ? '…' : latest ? `${formatWhen(latest.finished_at ?? latest.started_at)} · ${latest.status}` : 'none yet'}</span>
      <span className="rounded-full bg-white px-3.5 py-2">Newest data fetched: {sources.loading ? '…' : fetched[0] ? formatWhen(fetched[0].last_fetched) : 'not yet'}</span>
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
