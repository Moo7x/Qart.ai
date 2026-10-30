import { Info } from 'lucide-react'
import { useState } from 'react'
import type { MatchesResponse, RoleCard } from '../types'
import type { RolePay } from '../typesScoring'
import { levelText } from './journey'
import { Windows, type Pane } from './Windows'

const VIA_TEXT = { study: 'study', practice: 'practice at work', check: 'a progress check' } as const

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// The "Why?" control (docs/PHASE2_PLAN.md §5): a btn with the Info icon, at least 44 px high.
export function WhyButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button type="button" className="btn inline-flex min-h-[44px] items-center gap-1.5" onClick={onClick} aria-label={label}>
      <Info size={16} aria-hidden="true" />
      Why?
    </button>
  )
}

// "Fair · 41 (32–48)": the band, the fit and its range, large, with its "Why?" beside it.
export function ScoreChip({ role, matches, size = 'large' }: { role: RoleCard; matches: MatchesResponse; size?: 'large' | 'small' }) {
  const [open, setOpen] = useState(false)
  const band = role.band ? capitalise(role.band) : 'Fit'
  const range = `${Math.round(role.fit_range.low)}–${Math.round(role.fit_range.high)}`
  return (
    <span className="flex flex-wrap items-center gap-3">
      <span
        className={`inline-flex items-baseline gap-2 rounded-md border border-violet bg-violet-soft px-3 py-1.5 font-mono ${size === 'large' ? 'text-[28px]' : 'text-[15px]'}`}
        aria-label={`${band}, fit ${Math.round(role.fit)} out of 100, range ${range}`}
      >
        <span className="font-sans font-semibold">{band}</span>
        <span>· {Math.round(role.fit)}</span>
        <span className="text-[0.6em] text-graphite">({range})</span>
      </span>
      <WhyButton onClick={() => setOpen(true)} label={`Why this score for ${role.title}?`} />
      {open && <ScoreWhy role={role} matches={matches} onClose={() => setOpen(false)} />}
    </span>
  )
}

function Formula({ role }: { role: RoleCard }) {
  const rows = role.components ?? []
  return (
    <div className="flex flex-col gap-2">
      <p className="m-0 font-mono text-[12px]">fit = 100 × Σ w·min(c/r, 1) ÷ Σ w = {role.fit.toFixed(1)}</p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] border-collapse text-[12px]">
          <thead>
            <tr className="cap text-left">
              <th className="py-1 pr-2 font-normal">Skill</th>
              <th className="px-1 py-1 text-right font-normal">w</th>
              <th className="px-1 py-1 text-right font-normal">c</th>
              <th className="px-1 py-1 text-right font-normal">r</th>
              <th className="py-1 pl-1 text-right font-normal">Points</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.skill} className="border-t border-line align-top">
                <td className="py-1.5 pr-2">
                  {c.skill_name}
                  <span className="block text-[11px] text-graphite">
                    {c.claimed === null ? 'Not stated (counts as 0)' : c.evidenced ? `${c.source === 'agent_check' ? 'Progress check' : 'CV'}: “${c.evidence}”` : 'Self-rated'}
                  </span>
                </td>
                <td className="px-1 py-1.5 text-right font-mono">{c.weight}</td>
                <td className="px-1 py-1.5 text-right font-mono">{levelText(c.claimed)}</td>
                <td className="px-1 py-1.5 text-right font-mono">{levelText(c.required)}</td>
                <td className="py-1.5 pl-1 text-right font-mono">{c.points.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-[11px] text-graphite">w = weight after the scenario, c = your claimed level, r = the level the role needs (TalentCorp 2024 requirement, level an assumption). Levels are your claims, never verified.</p>
    </div>
  )
}

function Weights({ role, matches }: { role: RoleCard; matches: MatchesResponse }) {
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {role.requirements.map((r) => (
        <li key={r.skill} className="border-t border-line pt-1.5">
          <span className="font-medium">{r.skill_name}</span> <span className="font-mono text-[11px]">{r.base_weight} → {r.weight.toFixed(2)}</span>
          <span className="block text-[12px] text-graphite">{r.shift_reason}</span>
        </li>
      ))}
      <li className="text-[11px] text-graphite">AI-use share: {matches.evidence.source || 'no AI-use data stored'}{matches.evidence.period ? `, ${matches.evidence.period}` : ''} (observed). Scenario intensity {matches.intensity} ({matches.scenario_label}) is an assumption.</li>
    </ul>
  )
}

function Raise({ role }: { role: RoleCard }) {
  const options = role.raise ?? []
  if (!options.length) return <p className="m-0 text-graphite">No single skill change would raise this score: every requirement is met and evidenced.</p>
  return (
    <ol className="m-0 flex flex-col gap-2 pl-5">
      {options.map((o) => (
        <li key={o.skill}>
          <span className="font-medium">{o.skill_name}</span>: {o.via === 'check' ? `confirm your ${levelText(o.to_level)}` : `${levelText(o.from_level)} → ${levelText(o.to_level)}`} by {VIA_TEXT[o.via]}
          <span className="block font-mono text-[12px] text-violet">+{o.points.toFixed(1)} {o.via === 'check' ? 'on the low end of your range' : 'fit points'} (estimate, re-scored)</span>
        </li>
      ))}
    </ol>
  )
}

function Essentials({ role }: { role: RoleCard }) {
  const short = role.essentials_short ?? []
  const names = role.requirements.filter((r) => short.includes(r.skill)).map((r) => `${r.skill_name} (you ${levelText(r.claimed)}, needs ${levelText(r.required)})`)
  return names.length ? <ul className="m-0 pl-5">{names.map((n) => <li key={n}>{n}</li>)}</ul> : <p className="m-0">All essentials are at their level.</p>
}

function Labels({ role, matches }: { role: RoleCard; matches: MatchesResponse }) {
  const rules = matches.bands
  return (
    <div className="flex flex-col gap-2">
      <p className="m-0"><span className="tag bg-estimate-bg text-estimate">Assumption</span> Bands: {rules ? `${Object.entries(rules.thresholds).map(([b, t]) => `${b} ≥ ${t}`).join(' · ')} · ${rules.below} below` : 'not loaded'}. Declared thresholds, not a hiring standard.</p>
      <p className="m-0"><span className="tag bg-estimate-bg text-estimate">Assumption</span> Range {Math.round(role.fit_range.low)}–{Math.round(role.fit_range.high)}: {role.fit_range.basis ?? 'unstated skills from none to working'}.</p>
    </div>
  )
}

export function ScoreWhy({ role, matches, onClose }: { role: RoleCard; matches: MatchesResponse; onClose: () => void }) {
  const panes: Pane[] = [
    { key: 'formula', title: `Fit ${role.fit.toFixed(1)}: the formula with your numbers`, hint: 'Computed by code from your claims', body: <Formula role={role} /> },
    { key: 'weights', title: 'Why each weight is what it is', hint: 'Observed AI use × declared scenario', body: <Weights role={role} matches={matches} /> },
    { key: 'raise', title: 'What would raise it', hint: 'Each change re-scored exactly', body: <Raise role={role} /> },
    { key: 'essentials', title: 'Essentials still short', body: <Essentials role={role} /> },
    { key: 'labels', title: 'Band and range', hint: 'What is an assumption', body: <Labels role={role} matches={matches} /> },
  ]
  return <Windows title={`Why this score: ${role.title}`} panes={panes} onClose={onClose} />
}

// Group pay beside the card (C11): observed, with year and source; never part of fit or rank.
export function PayLine({ pay }: { pay: RolePay | null | undefined }) {
  const [open, setOpen] = useState(false)
  if (!pay) return <span className="text-[13px] text-graphite">Pay for this occupation group: not published.</span>
  const rm = (v: number) => `RM ${v.toLocaleString('en-MY')}`
  return (
    <span className="flex flex-wrap items-center gap-2 text-[13px]">
      <span className="tag bg-observed-bg text-observed">Observed</span>
      <span>
        Median pay {rm(pay.median)} a month · {pay.group_title}, {pay.year}
        {pay.overall_median !== null ? ` · all employees ${rm(pay.overall_median)}` : ''}
      </span>
      <WhyButton onClick={() => setOpen(true)} label="Why this pay figure?" />
      {open && (
        <Windows
          title="Pay of this occupation group"
          onClose={() => setOpen(false)}
          panes={[{
            key: 'pay',
            title: `${rm(pay.median)} a month (median, ${pay.year})`,
            hint: `${pay.source} · fetched ${pay.fetched_at.slice(0, 10)}`,
            body: (
              <div className="flex flex-col gap-2">
                <p className="m-0">{pay.note}</p>
                <p className="m-0">Median {rm(pay.median)}{pay.mean !== null ? ` · mean ${rm(pay.mean)}` : ''}{pay.overall_median !== null ? ` · national median ${rm(pay.overall_median)}` : ''} ({pay.unit}).</p>
                <p className="m-0 font-mono text-[11px] text-graphite">Published row: {pay.cited_span}</p>
                <p className="m-0 text-[11px] text-graphite">Pay is never used in fit, band or rank.</p>
              </div>
            ),
          }]}
        />
      )}
    </span>
  )
}
