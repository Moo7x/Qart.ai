import { Activity, Radar } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { formatWhen, useApi } from '../api'
import type { Run } from '../types'

const RUNS_POLL_MS = 60_000

function navClass({ isActive }: { isActive: boolean }): string {
  const base = 'flex min-h-[38px] items-center gap-2.5 rounded-md px-2.5 text-sm no-underline'
  return isActive
    ? `${base} bg-surface text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.05)]`
    : `${base} text-[#c4c5cf] hover:bg-obsidian hover:text-white`
}

export function Sidebar() {
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=1', RUNS_POLL_MS)
  const latest = runs.data?.[0]
  return (
    <nav
      aria-label="Main"
      className="flex flex-[1_1_232px] flex-col gap-1 bg-void px-3.5 py-5 md:sticky md:top-0 md:h-screen md:max-w-[260px]"
    >
      <span className="flex items-center gap-2.5 px-2 pb-5">
        <svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true">
          <rect width="26" height="26" rx="6" fill="#2f3037" />
          <circle cx="12" cy="12" r="6" fill="none" stroke="#ffffff" strokeWidth="2.2" />
          <path d="M16 16l4.5 4.5" stroke="#6c47ff" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <span className="text-base font-semibold tracking-tight text-white">Qart.ai</span>
      </span>
      <span className="cap px-2.5 pb-1.5 text-slate-mid">GBS finance &amp; accounting</span>
      <NavLink to="/" end className={navClass}>
        <Radar size={16} aria-hidden="true" />
        Overview
      </NavLink>
      <div className="mx-1.5 my-3 h-px bg-surface" />
      <NavLink to="/live" className={navClass}>
        <Activity size={16} aria-hidden="true" className="text-cyan" />
        Live intelligence
      </NavLink>
      <div className="flex-1" />
      <div className="border-t border-surface p-2.5 font-mono text-[11px] leading-relaxed text-stone">
        LAST PIPELINE RUN
        <br />
        <span className="text-white">{latest ? formatWhen(latest.finished_at ?? latest.started_at) : '—'}</span>
        <br />
        <span className="text-slate-mid">{latest ? latest.status.toUpperCase() : 'NO RUN YET'}</span>
      </div>
    </nav>
  )
}
