import { useState } from 'react'
import type { PathwayStep } from '../types'

// The pathway as a prerequisite map: one column per prerequisite depth, arrows from a course to
// the ones that need it. A node is done (your record), ready (its prerequisites are done) or
// waiting for a prerequisite. Click a node for its details; the list below stays the full view.
const NODE_W = 190
const NODE_H = 58
const GAP_X = 56
const GAP_Y = 16

type State = 'done' | 'ready' | 'waiting'
const STYLE: Record<State, [string, string]> = {
  done: ['#e6f4ec', '#157a4a'],
  ready: ['#f1edff', '#6c47ff'],
  waiting: ['#f7f7f8', '#9394a1'],
}

export function Roadmap({ steps, done }: { steps: PathwayStep[]; done: string[] }) {
  const [open, setOpen] = useState<string | null>(null)
  const byId = new Map(steps.map((s) => [s.course.id, s]))
  const depth = new Map<string, number>()
  const level = (id: string): number => {
    if (depth.has(id)) return depth.get(id)!
    const reqs = (byId.get(id)?.course.requires ?? []).filter((r) => byId.has(r))
    const d = reqs.length ? 1 + Math.max(...reqs.map(level)) : 0
    depth.set(id, d)
    return d
  }
  steps.forEach((s) => level(s.course.id))
  const columns: PathwayStep[][] = []
  steps.forEach((s) => (columns[depth.get(s.course.id)!] ??= []).push(s))
  const pos = new Map<string, { x: number; y: number }>()
  columns.forEach((col, c) => col.forEach((s, r) => pos.set(s.course.id, { x: c * (NODE_W + GAP_X), y: r * (NODE_H + GAP_Y) })))
  const width = columns.length * (NODE_W + GAP_X) - GAP_X
  const height = Math.max(...columns.map((c) => c.length)) * (NODE_H + GAP_Y) - GAP_Y
  const state = (s: PathwayStep): State =>
    done.includes(s.course.id) ? 'done' : s.course.requires.every((r) => !byId.has(r) || done.includes(r)) ? 'ready' : 'waiting'
  const selected = open ? byId.get(open) : undefined
  if (steps.length === 0) return null
  return (
    <section className="card-light flex flex-col gap-3 px-6 py-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h2">Roadmap</h2>
        <span className="flex gap-3 text-[11px]">
          {(['done', 'ready', 'waiting'] as State[]).map((k) => (
            <span key={k} className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: STYLE[k][0], border: `1px solid ${STYLE[k][1]}` }} />{k === 'waiting' ? 'needs a prerequisite' : k}</span>
          ))}
        </span>
      </div>
      <div className="overflow-x-auto">
        <div className="relative" style={{ width, height }}>
          <svg className="absolute inset-0" width={width} height={height} aria-hidden="true">
            {steps.flatMap((s) =>
              s.course.requires.filter((r) => pos.has(r)).map((r) => {
                const a = pos.get(r)!
                const b = pos.get(s.course.id)!
                return <line key={`${r}-${s.course.id}`} x1={a.x + NODE_W} y1={a.y + NODE_H / 2} x2={b.x} y2={b.y + NODE_H / 2} stroke="#b9b9c3" strokeWidth="1.5" />
              }),
            )}
          </svg>
          {steps.map((s) => {
            const p = pos.get(s.course.id)!
            const [bg, border] = STYLE[state(s)]
            return (
              <button
                key={s.course.id}
                type="button"
                onClick={() => setOpen(open === s.course.id ? null : s.course.id)}
                aria-pressed={open === s.course.id}
                className="absolute flex cursor-pointer flex-col justify-center rounded-lg px-2.5 text-left text-[12px] leading-tight"
                style={{ left: p.x, top: p.y, width: NODE_W, height: NODE_H, background: bg, border: `1.5px solid ${border}` }}
              >
                <span className="line-clamp-2 font-medium">{s.order}. {s.course.title}</span>
                <span className="font-mono text-[10px] text-graphite">{s.hours} h · week {s.week_start}</span>
              </button>
            )
          })}
        </div>
      </div>
      {selected && (
        <div className="rounded-lg border border-mist p-3 text-[13px]">
          <span className="font-semibold">{selected.course.title}</span> · {selected.course.provider} · {selected.hours} h · {selected.course.level}
          <div className="text-xs text-graphite">
            Builds: {selected.gains.map((g) => `${g.skill_name} ${g.before}→${g.after}`).join(', ') || 'a prerequisite for later steps'} (projected, an assumption).
            {selected.course.requires.length > 0 && <> Needs first: {selected.course.requires.map((r) => byId.get(r)?.course.title ?? r).join(', ')}.</>}
            {selected.sdgs.length > 0 && <> SDG {selected.sdgs.map((g) => g.target).join(', ')}.</>}
          </div>
          <a href={selected.course.url} target="_blank" rel="noreferrer" className="text-xs">Open course ↗</a>
        </div>
      )}
    </section>
  )
}
