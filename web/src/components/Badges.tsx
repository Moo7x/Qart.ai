import { Flag, Footprints, Lock, ShieldCheck, TrendingUp, Trophy } from 'lucide-react'
import type { Badge } from '../typesScoring'

// Badges on the plan page (B8): each comes only from what the person did, never from a model or a
// guess. Earned badges glow with their date; the others are shown locked, with how to earn them.

const KINDS: { prefix: string; title: string; how: string; icon: typeof Trophy; colours: [string, string] }[] = [
  { prefix: 'first_step', title: 'First step', how: 'Mark your first course done', icon: Footprints, colours: ['#6c47ff', '#5de3ff'] },
  { prefix: 'skill_up', title: 'Skill up', how: 'Raise a skill the role needs', icon: TrendingUp, colours: ['#157a4a', '#3fd1a0'] },
  { prefix: 'essentials_ready', title: 'Essentials ready', how: 'Reach every essential level', icon: ShieldCheck, colours: ['#9a4609', '#ffa86b'] },
  { prefix: 'halfway', title: 'Halfway', how: 'Finish half the study hours', icon: Flag, colours: ['#2a78d6', '#9d86ff'] },
  { prefix: 'plan_complete', title: 'Plan complete', how: 'Finish every step', icon: Trophy, colours: ['#b8860b', '#ffd34d'] },
]

// Collecting REWARD_AT kinds of badge unlocks the progress record: a printable page of the
// person's skills, plan and evidence to bring to a manager, HR (an HRD Corp training request) or an
// employer. It records only what they did; nothing is bought or paid.
const REWARD_AT = 3

export function Badges({ badges }: { badges: Badge[] }) {
  const kinds = KINDS.filter((k) => badges.some((b) => b.id.startsWith(k.prefix))).length
  const unlocked = kinds >= REWARD_AT
  return (
    <div className="flex flex-col gap-4">
    <ul className="m-0 grid list-none grid-cols-2 gap-4 p-0 sm:grid-cols-3 lg:grid-cols-5" aria-label="Your badges">
      {KINDS.map((k) => {
        const earned = badges.filter((b) => b.id.startsWith(k.prefix))
        const on = earned.length > 0
        const Icon = on ? k.icon : Lock
        return (
          <li key={k.prefix} className="flex flex-col items-center gap-2 text-center" title={on ? earned[0].rule : k.how}>
            <span
              className={`badge-medal grid h-[76px] w-[76px] place-items-center rounded-full text-white ${on ? 'badge-on' : ''}`}
              style={on ? { background: `conic-gradient(from 210deg, ${k.colours[0]}, ${k.colours[1]}, ${k.colours[0]})` } : undefined}
            >
              <span className={`grid h-[58px] w-[58px] place-items-center rounded-full ${on ? 'bg-[rgba(19,19,22,0.25)]' : 'bg-mist text-ash'}`}>
                <Icon size={26} aria-hidden="true" />
              </span>
            </span>
            <span className={`text-[13px] font-semibold ${on ? '' : 'text-graphite'}`}>{k.title}{earned.length > 1 ? ` ×${earned.length}` : ''}</span>
            <span className="text-[11px] text-graphite">{on ? `Earned ${earned[0].earned_at.slice(0, 10)}` : k.how}</span>
          </li>
        )
      })}
    </ul>
    <div className="flex flex-col gap-2 rounded-2xl bg-white/60 px-4 py-3">
      <span className="flex items-center justify-between gap-2 text-[13px] font-semibold">
        <span>{unlocked ? 'Progress record unlocked' : `${kinds} of ${REWARD_AT} badges to unlock your progress record`}</span>
        <span className="font-mono">{Math.min(kinds, REWARD_AT)}/{REWARD_AT}</span>
      </span>
      <span className="block h-2 overflow-hidden rounded-full bg-white" aria-hidden="true"><span className="block h-full rounded-full bg-[#3f6212] transition-[width] duration-500" style={{ width: `${(100 * Math.min(kinds, REWARD_AT)) / REWARD_AT}%` }} /></span>
      <span className="text-[12px] text-[#33402a]">A one-page record of your skills, plan and the evidence behind them, to bring to your manager, to HR when you ask for HRD Corp-funded training, or to an employer. Badges come only from what you do.</span>
      {unlocked && <button type="button" className="q-btn self-start text-[13px]" onClick={() => window.print()}>Print my progress record</button>}
    </div>
    </div>
  )
}
