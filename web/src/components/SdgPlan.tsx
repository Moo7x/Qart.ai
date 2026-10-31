import { useState } from 'react'
import type { PathwayResponse } from '../types'
import type { SdgMatrix } from '../typesScoring'
import { sdgColour } from './journey'
import { SdgHeatmap } from './SdgHeatmap'

// One place for the plan's SDG contribution (docs/PHASE2_PLAN.md B7): a tile per target with the
// study hours that serve it, the skills behind those hours and the reason; whole-plan links (free
// learning, the role move) as their own tiles. A tile opens its reasons, sources and UN wording.
// The person's chosen goals are marked, because they also order close role matches.

type Tile = { target: string; hours: number | null; skills: { name: string; hours: number }[]; reasons: { text: string; source: string }[] }

export function SdgPlan({ matrix, path, goals }: { matrix: SdgMatrix; path: PathwayResponse; goals: string[] }) {
  const [open, setOpen] = useState<string | null>(null)
  const [table, setTable] = useState(false)
  const name = (skill: string) => matrix.rows.find((r) => r.skill === skill)?.skill_name ?? skill
  const tiles: Tile[] = matrix.totals.map((t) => {
      const cells = matrix.cells.filter((c) => c.target === t.target)
      return {
        target: t.target,
        hours: t.hours,
        skills: cells.filter((c) => c.hours > 0).map((c) => ({ name: name(c.skill), hours: c.hours })).sort((a, b) => b.hours - a.hours),
        reasons: cells.flatMap((c) => c.reasons).filter((r, i, all) => all.findIndex((x) => x.text === r.text) === i),
      }
    })
  // A whole-plan link (free learning, the role move) joins the tile of the same target if the
  // plan's skills already serve it; otherwise it gets its own tile.
  for (const l of matrix.path_links) {
    const same = tiles.find((t) => t.target === l.target)
    if (same) same.reasons.push({ text: l.text, source: l.source })
    else tiles.push({ target: l.target, hours: null, skills: [], reasons: [{ text: l.text, source: l.source }] })
  }
  const title = (target: string) => matrix.targets.find((t) => t.id === target)?.title ?? path.sdg_targets[target]?.title ?? ''
  const text = (target: string) => matrix.targets.find((t) => t.id === target)?.text ?? path.sdg_targets[target]?.text ?? ''
  return (
    <section id="sdg" aria-label="SDG contribution" className="sdg-plan flex flex-col gap-5 rounded-2xl p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="eyebrow">Sustainable Development Goals</span>
          <h2 className="m-0 text-[26px] font-semibold leading-tight tracking-tight">What your plan does for {tiles.length} SDG targets</h2>
          <span className="text-[14px] text-graphite">Fit for {path.role_title}: <b className="font-mono text-void">{Math.round(path.fit_before)} → {Math.round(path.fit_after)}</b> after the plan · estimate</span>
        </div>
        <button type="button" className="btn min-h-[38px] text-[13px]" onClick={() => setTable((v) => !v)}>{table ? 'Show the target tiles' : 'See it skill by skill'}</button>
      </div>
      {table ? (
        <SdgHeatmap data={matrix} />
      ) : (
        // The tiles move slowly left to right in a loop (a second, hidden copy closes the loop);
        // hover, focus or an open tile pauses it, and reduced-motion users see it still.
        <div className={`sdg-marquee ${open ? 'sdg-paused' : ''}`}>
          <div className="sdg-track">
          {[0, 1].flatMap((copy) => tiles.map((t) => {
            const colour = sdgColour(t.target)
            const mine = goals.includes(t.target.split('.')[0])
            const isOpen = open === t.target
            return (
              <button key={`${copy}-${t.target}`} type="button" aria-hidden={copy === 1} tabIndex={copy === 1 ? -1 : undefined} aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : t.target)} className="sdg-tile flex w-[270px] flex-none cursor-pointer flex-col gap-2 self-start rounded-2xl border-0 bg-paper p-0 text-left shadow-[0_6px_20px_rgba(19,19,22,0.07)]">
                <span className="flex items-center justify-between gap-2 rounded-t-xl px-4 py-3 text-white" style={{ background: colour }}>
                  <span className="font-mono text-[20px] font-semibold">SDG {t.target}</span>
                  {mine && <span className="rounded-full bg-white/90 px-2 py-0.5 text-[11px] font-semibold" style={{ color: colour }}>Your goal</span>}
                </span>
                <span className="flex flex-col gap-1.5 px-4 pb-4">
                  <span className="text-[14px] font-semibold leading-snug">{title(t.target)}</span>
                  <span className="font-mono text-[26px] leading-none" style={{ color: colour }}>{t.hours === null ? 'Whole plan' : `${t.hours.toFixed(1)} h`}</span>
                  <span className="text-[13px] text-graphite">{t.reasons[0]?.text}</span>
                  {t.skills.length > 0 && (
                    <span className="flex flex-wrap gap-1 pt-1">
                      {t.skills.slice(0, 4).map((s) => <span key={s.name} className="rounded-full bg-mist px-2 py-0.5 text-[11px]">{s.name} · {s.hours.toFixed(1)} h</span>)}
                    </span>
                  )}
                  {isOpen && (
                    <span className="flex flex-col gap-1.5 border-t border-line pt-2 text-[12px]">
                      {t.reasons.slice(1).map((r) => <span key={r.text}>{r.text} <span className="text-graphite">({r.source})</span></span>)}
                      <span className="text-graphite">Source: {t.reasons[0]?.source}</span>
                      <span className="italic text-graphite">UN target {t.target}: &ldquo;{text(t.target)}&rdquo;</span>
                    </span>
                  )}
                </span>
              </button>
            )
          }))}
          </div>
        </div>
      )}
      <p className="m-0 text-[12px] text-graphite">Hours are planned study hours; an hour counts toward every target its skill serves. These are the ways the plan contributes, not a measured impact. {matrix.source}</p>
    </section>
  )
}
