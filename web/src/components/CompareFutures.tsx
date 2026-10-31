import { useApi } from '../api'
import { useJourney } from '../state'
import type { MatchesResponse } from '../types'
import { KindLabel } from './Why'

// Stage 6, compare futures (docs/PHASE2_PLAN.md A10): the same profile under moderate and fast AI
// adoption side by side. Both come from the same engine with one declared parameter changed (the
// share of observed automation-style AI use assumed to reach the tasks), so every difference here
// is that parameter at work. Estimates, not predictions of what will happen.

function shift(before: number, after: number): { text: string; tone: string } {
  if (after < before) return { text: `↑${before - after}`, tone: 'text-rising' }
  if (after > before) return { text: `↓${after - before}`, tone: 'text-weak' }
  return { text: '=', tone: 'text-graphite' }
}

export function CompareFutures() {
  const { profileId } = useJourney()
  const moderate = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=moderate` : null)
  const fast = useApi<MatchesResponse>(profileId ? `/api/profiles/${profileId}/matches?scenario=fast` : null)
  const m = moderate.data
  const f = fast.data
  if (!m || !f) return <span role="status" className="cap">Loading both futures…</span>
  const rankIn = (data: MatchesResponse) => new Map(data.roles.map((r, i) => [r.role_id, i + 1]))
  const mRank = rankIn(m)
  const focusId = m.destination ?? m.roles[0]?.role_id
  const mRole = m.roles.find((r) => r.role_id === focusId)
  const fRole = f.roles.find((r) => r.role_id === focusId)
  const moved = (mRole?.requirements ?? [])
    .map((req) => ({ req, fast: fRole?.requirements.find((x) => x.skill === req.skill) }))
    .filter(({ req, fast: fr }) => fr && Math.abs(fr.weight - req.weight) > 0.005)
  return (
    <section className="section" aria-label="Compare futures">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex flex-col gap-1">
          <span className="eyebrow">Compare futures</span>
          <h2 className="h2">The same you, under moderate and fast AI adoption</h2>
        </div>
        <KindLabel kind="estimate" />
      </div>
      <p className="m-0 max-w-[760px] text-[13px] text-graphite">
        One declared parameter changes: the share of the observed automation-style AI use assumed to reach these tasks within {m.horizon_years} years ({Math.round(100 * m.intensity)}% moderate, {Math.round(100 * f.intensity)}% fast; {m.evidence.source}, {m.evidence.period}). Routine skills lose weight and AI-complementing skills gain it; essential skills never move.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {[m, f].map((data) => (
          <div key={data.scenario} className="min-w-0">
            <span className="cap">{data.scenario_label}</span>
            <ol className="m-0 mt-1 flex list-none flex-col p-0 text-[13px]">
              {data.roles.map((r, i) => {
                const s = data === f ? shift(mRank.get(r.role_id) ?? i + 1, i + 1) : null
                return (
                  <li key={r.role_id} className={`grid grid-cols-[24px_minmax(0,1fr)_56px_32px] items-center gap-2 border-t border-line py-1.5 ${r.role_id === focusId ? 'font-semibold' : ''}`}>
                    <span className="font-mono text-ash">{i + 1}</span>
                    <span className="min-w-0">{r.title}</span>
                    <span className="text-right font-mono">{r.fit.toFixed(1)}</span>
                    <span className={`text-right font-mono text-[12px] ${s?.tone ?? ''}`}>{s?.text ?? ''}</span>
                  </li>
                )
              })}
            </ol>
          </div>
        ))}
      </div>
      {mRole && (
        <div className="flex flex-col gap-1.5 border-t border-line pt-3">
          <span className="cap">What moves for {mRole.title}: skill weights, moderate → fast</span>
          {moved.length === 0 ? (
            <p className="m-0 text-[13px] text-graphite">No weight in this role depends on the adoption speed: its skills are essential or neutral, or have no observed AI use.</p>
          ) : (
            <ul className="m-0 grid list-none gap-x-6 gap-y-1 p-0 text-[13px] md:grid-cols-2">
              {moved.map(({ req, fast: fr }) => (
                <li key={req.skill} className="flex justify-between gap-2">
                  <span>{req.skill_name}</span>
                  <span className={`font-mono ${(fr?.weight ?? 0) > req.weight ? 'text-rising' : 'text-weak'}`}>{req.weight.toFixed(2)} → {fr?.weight.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="m-0 text-[12px] text-graphite">Fit {mRole.fit.toFixed(1)} → {fRole?.fit.toFixed(1)}. Your skills are the same in both; only the weights change.</p>
        </div>
      )}
    </section>
  )
}
