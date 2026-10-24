import { Activity, ArrowRight, ChartLine, FileText, Flag, ListOrdered, Radar, Route as RouteIcon, Search, UserRound } from 'lucide-react'
import { LanguageSwitch, useT } from '../i18n'
import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { formatWhen, useApi } from '../api'
import { useJourney } from '../state'
import type { ChangesResponse, Run } from '../types'

const RUNS_POLL_MS = 60_000

function navClass({ isActive }: { isActive: boolean }): string {
  const base = 'flex min-h-[38px] items-center gap-2.5 rounded-md px-2.5 text-sm no-underline'
  return isActive
    ? `${base} bg-surface text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.05)]`
    : `${base} text-[#c4c5cf] hover:bg-obsidian hover:text-white`
}

export function Sidebar() {
  const { t } = useT()
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=1', RUNS_POLL_MS)
  const latest = runs.data?.[0]
  const { profileId, setProfileId } = useJourney()
  const changes = useApi<ChangesResponse>(profileId ? `/api/profiles/${profileId}/changes` : null, RUNS_POLL_MS)
  // On phones the menu folds into a button so the page content comes first.
  const [open, setOpen] = useState(false)
  const location = useLocation()
  useEffect(() => setOpen(false), [location.pathname])
  return (
    <nav
      aria-label="Main"
      className="flex flex-[1_1_232px] flex-col gap-1 bg-void px-3.5 py-3 md:sticky md:top-0 md:h-screen md:max-w-[260px] md:py-5"
    >
      <span className="flex items-center gap-2.5 px-2 md:pb-5">
        <svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true">
          <rect width="26" height="26" rx="6" fill="#2f3037" />
          <circle cx="12" cy="12" r="6" fill="none" stroke="#ffffff" strokeWidth="2.2" />
          <path d="M16 16l4.5 4.5" stroke="#6c47ff" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <span className="text-base font-semibold tracking-tight text-white">Qart.ai</span>
        <button
          type="button"
          className="ml-auto cursor-pointer rounded-md border-0 bg-surface px-3 py-1.5 text-sm text-white md:hidden"
          aria-expanded={open}
          aria-controls="main-menu"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Close' : 'Menu'}
        </button>
      </span>
      <div id="main-menu" className={`${open ? 'flex' : 'hidden'} flex-1 flex-col gap-1 md:flex`}>
      <span className="cap px-2.5 pb-1.5 text-slate-mid">{t('Your journey · GBS finance')}</span>
      <NavLink to="/" end className={navClass}>
        <Radar size={16} aria-hidden="true" />
        {t('Overview')}
      </NavLink>
      <NavLink to="/goal" className={navClass}>
        <Flag size={16} aria-hidden="true" />
        {t('My goal')}
      </NavLink>
      <NavLink to="/roles" className={navClass}>
        <ListOrdered size={16} aria-hidden="true" />
        {t('My options')}
      </NavLink>
      <NavLink to="/pathway" className={navClass}>
        <RouteIcon size={16} aria-hidden="true" />
        {t('My plan')}
      </NavLink>
      <NavLink to="/future" className={navClass}>
        <ArrowRight size={16} aria-hidden="true" />
        {t('Today → Future you')}
      </NavLink>
      <NavLink to="/changes" className={navClass}>
        <Activity size={16} aria-hidden="true" />
        {t('What changed')}
        {changes.data?.proposals.some((p) => p.actionable) && <span className="tag bg-violet text-white">New</span>}
      </NavLink>
      <NavLink to="/cv" className={navClass}>
        <FileText size={16} aria-hidden="true" />
        {t('My CV')}
      </NavLink>
      {profileId ? (
        <button
          type="button"
          onClick={() => setProfileId(null)}
          className="flex min-h-[38px] cursor-pointer items-center gap-2.5 rounded-md border-0 bg-transparent px-2.5 text-left text-sm text-stone hover:bg-obsidian hover:text-white"
        >
          <UserRound size={16} aria-hidden="true" />
          {t('Start again with a new profile')}
        </button>
      ) : (
        <Link to="/start" className="mt-1 flex min-h-[38px] items-center justify-center rounded-md bg-violet text-sm font-medium text-white no-underline hover:bg-violet-hover">
          {t('Start · tell us about yourself')}
        </Link>
      )}
      <div className="mx-1.5 my-3 h-px bg-surface" />
      <span className="cap px-2.5 pb-1.5 text-slate-mid">{t('Evidence')}</span>
      <NavLink to="/trends" className={navClass}>
        <ChartLine size={16} aria-hidden="true" className="text-cyan" />
        {t('Trends')}
      </NavLink>
      <NavLink to="/occupations" className={navClass}>
        <Search size={16} aria-hidden="true" className="text-cyan" />
        {t('Any occupation')}
      </NavLink>
      <NavLink to="/live" className={navClass}>
        <Activity size={16} aria-hidden="true" className="text-cyan" />
        {t('Live intelligence')}
      </NavLink>
      <div className="flex-1" />
      <LanguageSwitch />
      <div className="border-t border-surface p-2.5 font-mono text-[11px] leading-relaxed text-stone">
        LAST PIPELINE RUN
        <br />
        <span className="text-white">{latest ? formatWhen(latest.finished_at ?? latest.started_at) : '—'}</span>
        <br />
        <span className="text-slate-mid">{latest ? latest.status.toUpperCase() : 'NO RUN YET'}</span>
      </div>
      </div>
    </nav>
  )
}
