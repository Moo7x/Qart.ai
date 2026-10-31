import { useState } from 'react'
import type { SdgMatrix, SdgReason } from '../typesScoring'
import { SdgTag } from './journey'
import { Windows } from './Windows'

// One sequential hue (violet), light → dark for more planned hours. Text contrast was computed
// (WCAG): dark ink on the first four steps (≥ 5.3:1), white on the darkest (6.75:1).
const RAMP = ['#f1edff', '#d9d0ff', '#b9a6ff', '#8f72ff', '#5a35e8']
const INK_ON_DARK = 4 // index from which the cell text turns white

function step(hours: number, max: number): number {
  if (max <= 0 || hours <= 0) return -1
  return Math.min(RAMP.length - 1, Math.floor((hours / max) * RAMP.length))
}

type Open = { title: string; hint: string; reasons: SdgReason[] }

function ReasonList({ reasons }: { reasons: SdgReason[] }) {
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {reasons.map((r) => (
        <li key={r.text} className="border-b border-line pb-2 last:border-0">
          {r.text}
          <span className="block font-mono text-[11px] text-graphite">{r.source}</span>
        </li>
      ))}
    </ul>
  )
}

// Skills of the plan × SDG targets; a cell is the study hours that skill takes in the plan
// (C4). A click opens the one-line reasons and their sources. A real table, so it reads without
// colour: the hours are printed in every cell.
export function SdgHeatmap({ data }: { data: SdgMatrix }) {
  const [open, setOpen] = useState<Open | null>(null)
  const max = Math.max(0, ...data.cells.map((c) => c.hours))
  const cell = (skill: string, target: string) => data.cells.find((c) => c.skill === skill && c.target === target)
  const title = (id: string) => data.targets.find((t) => t.id === id)?.title ?? id
  // Columns: the targets the plan's skills serve (the ones with totals); path links sit below.
  const columns = data.targets.filter((t) => data.totals.some((x) => x.target === t.id))
  if (!data.rows.length) return <p className="m-0 text-[13px] text-graphite">No skill gaps in this plan, so no study hours to map.</p>
  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse text-[13px]">
          <caption className="sr-only">Planned study hours per skill and SDG target</caption>
          <thead>
            <tr className="text-left">
              <th scope="col" className="cap py-2 pr-2 font-normal">Skill in your plan</th>
              {columns.map((t) => (
                <th key={t.id} scope="col" className="px-1 py-2 text-center font-normal">
                  <SdgTag target={t.id} />
                  <span className="mt-1 block text-[11px] leading-tight text-graphite">{t.title}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.skill} className="border-t border-line">
                <th scope="row" className="py-1.5 pr-2 text-left font-normal">
                  {row.skill_name}
                  {row.practice && <span className="ml-1.5 text-[11px] text-graphite">+ practice at work</span>}
                </th>
                {columns.map((t) => {
                  const c = cell(row.skill, t.id)
                  if (!c) return <td key={t.id} className="px-1 py-1.5 text-center text-ash" aria-label="not linked">·</td>
                  const s = step(c.hours, max)
                  const label = `${row.skill_name} → SDG ${t.id}: ${c.hours.toFixed(1)} h planned. Open the reason.`
                  return (
                    <td key={t.id} className="p-0.5">
                      <button
                        type="button"
                        title={label}
                        aria-label={label}
                        onClick={() => setOpen({ title: `${row.skill_name} → SDG ${t.id} ${title(t.id)}`, hint: `${c.hours.toFixed(1)} h of planned study`, reasons: c.reasons })}
                        className="min-h-[44px] w-full cursor-pointer rounded border border-line font-mono text-[12px] hover:outline hover:outline-2 hover:outline-violet"
                        style={{ background: s < 0 ? '#ffffff' : RAMP[s], color: s >= INK_ON_DARK ? '#ffffff' : '#131316' }}
                      >
                        {c.hours > 0 ? `${c.hours.toFixed(1)} h` : row.practice ? 'practice' : '0 h'}
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
            <tr className="border-t-2 border-void">
              <th scope="row" className="py-2 pr-2 text-left font-semibold">Total per target <span className="block text-[11px] font-normal text-graphite">not additive across targets</span></th>
              {columns.map((t) => (
                <td key={t.id} className="px-1 py-2 text-center font-mono text-[12px] font-semibold">{(data.totals.find((x) => x.target === t.id)?.hours ?? 0).toFixed(1)} h</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-graphite" aria-hidden="true">
        <span>fewer hours</span>
        {RAMP.map((c) => <span key={c} className="inline-block h-3 w-6 rounded-sm border border-line" style={{ background: c }} />)}
        <span>more hours</span>
        <span className="ml-2">· not linked</span>
      </div>
      <p className="m-0 text-[12px] text-graphite">{data.note} Hours are planned study (estimates); practice at work is marked, not counted.</p>
      <div className="flex flex-col gap-1.5 text-[13px]">
        <span className="font-medium">Your path as a whole</span>
        {data.path_links.map((l) => (
          <span key={`${l.target}-${l.text}`} className="flex flex-wrap items-start gap-2">
            <SdgTag target={l.target} />
            <span>{l.text} <span className="font-mono text-[11px] text-graphite">{l.source}</span></span>
          </span>
        ))}
      </div>
      <p className="m-0 font-mono text-[11px] text-graphite">Target wording: {data.source}</p>
      {open && <Windows title={open.title} onClose={() => setOpen(null)} panes={[{ key: 'why', title: 'Why this link', hint: open.hint, body: <ReasonList reasons={open.reasons} /> }]} />}
    </div>
  )
}

// Roles × SDG targets (on /roles): which targets each role serves, with the reason on click.
export function SdgRolesGrid({ roles }: { roles: SdgMatrix['roles'] }) {
  const [open, setOpen] = useState<Open | null>(null)
  const targets = [...new Set(roles.flatMap((r) => r.targets.map((t) => t.target)))].sort((a, b) => Number(a) - Number(b))
  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] border-collapse text-[13px]">
          <caption className="sr-only">Which SDG targets each destination role serves</caption>
          <thead>
            <tr className="text-left">
              <th scope="col" className="cap py-2 pr-2 font-normal">Role</th>
              {targets.map((t) => <th key={t} scope="col" className="px-1 py-2 text-center font-normal"><SdgTag target={t} /></th>)}
            </tr>
          </thead>
          <tbody>
            {roles.map((role) => (
              <tr key={role.role_id} className="border-t border-line">
                <th scope="row" className="py-1.5 pr-2 text-left font-normal">{role.title}</th>
                {targets.map((t) => {
                  const link = role.targets.find((x) => x.target === t)
                  if (!link) return <td key={t} className="px-1 py-1.5 text-center text-ash" aria-label="not linked">·</td>
                  return (
                    <td key={t} className="p-0.5 text-center">
                      <button type="button" className="min-h-[44px] w-full cursor-pointer rounded border border-line bg-violet-soft text-[12px] hover:outline hover:outline-2 hover:outline-violet" aria-label={`${role.title} serves SDG ${t}. Open the reason.`} title={link.reason} onClick={() => setOpen({ title: `${role.title} → SDG ${t}`, hint: 'Why this role serves this target', reasons: [{ text: link.reason, source: link.source }] })}>
                        ✓ linked
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-[11px] text-graphite">A tick means the role serves the target; click it for the reason and source. Linked or not, never a score.</p>
      {open && <Windows title={open.title} onClose={() => setOpen(null)} panes={[{ key: 'why', title: 'Why this link', hint: open.hint, body: <ReasonList reasons={open.reasons} /> }]} />}
    </div>
  )
}
