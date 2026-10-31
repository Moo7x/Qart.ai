import { ChevronDown, ChevronRight, Menu, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { formatWhen, useApi } from '../api'
import { LanguageSwitch, useT } from '../i18n'
import { useJourney } from '../state'
import type { ChangesResponse, Run } from '../types'

const RUNS_POLL_MS = 60_000

export function Logo({ className }: { className?: string }) {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true" className={className}>
      <polyline points="6,24 16,14 26,6" fill="none" stroke="#6c47ff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="6" cy="24" r="3.5" fill="#6c47ff" />
      <circle cx="16" cy="14" r="3.5" fill="#6c47ff" />
      <circle cx="26" cy="6" r="3.5" fill="#6c47ff" />
    </svg>
  )
}

const MAIN = [
  { to: '/overview', text: 'Overview' },
  { to: '/roles', text: 'My options' },
  { to: '/pathway', text: 'My plan' },
  { to: '/future', text: 'Compare futures' },
  { to: '/trends', text: 'Trends' },
]
// The evidence pages stay one click away: the signal layer with its sources and dates is a
// must-have (docs/PHASE2_PLAN.md §0).
const EVIDENCE = [
  { to: '/changes', text: 'What changed' },
  { to: '/live', text: 'Live intelligence' },
  { to: '/occupations', text: 'Any occupation' },
  { to: '/status', text: 'Status' },
  { to: '/privacy', text: 'Privacy' },
]

function linkClass({ isActive }: { isActive: boolean }) {
  return `inline-flex min-h-[44px] items-center text-sm font-medium no-underline hover:text-violet ${isActive ? 'text-violet' : 'text-ink'}`
}

/** The floating pill navbar (design-prototype/ app.py navbar); replaces the side menu. On the
 *  landing page `onStart` turns the profile button into "Start my profile", which opens the CV popup. */
export function TopNav({ onStart }: { onStart?: () => void } = {}) {
  const { t } = useT()
  const { profileId } = useJourney()
  const location = useLocation()
  const runs = useApi<Run[]>('/api/pipeline/runs?limit=1', RUNS_POLL_MS)
  const changes = useApi<ChangesResponse>(profileId ? `/api/profiles/${profileId}/changes` : null, RUNS_POLL_MS)
  const fresh = changes.data?.proposals.some((p) => p.actionable)
  const latest = runs.data?.[0]
  const [menu, setMenu] = useState(false)
  const [more, setMore] = useState(false)
  const nav = useRef<HTMLElement>(null)
  useEffect(() => { setMenu(false); setMore(false) }, [location.pathname])
  useEffect(() => {
    if (!menu && !more) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setMenu(false)
      setMore(false)
      nav.current?.querySelector<HTMLElement>('[aria-expanded="true"]')?.focus()
    }
    const onClick = (e: MouseEvent) => { if (!nav.current?.contains(e.target as Node)) { setMenu(false); setMore(false) } }
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onClick)
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('mousedown', onClick) }
  }, [menu, more])

  const pipeline = (
    <span className="px-3 py-2 font-mono text-[11px] leading-relaxed text-muted-2">
      Last pipeline run: {latest ? `${formatWhen(latest.finished_at ?? latest.started_at)} · ${latest.status}` : 'no run yet'}
    </span>
  )
  const evidenceLinks = (cls: string) =>
    EVIDENCE.map((l) => (
      <NavLink key={l.to} to={l.to} className={({ isActive }) => `${cls} ${isActive ? 'bg-assumption-bg text-violet' : 'text-ink'}`}>
        {t(l.text)}
        {l.to === '/changes' && fresh && <span className="q-label q-label-assumption ml-2">new</span>}
      </NavLink>
    ))
  const item = 'flex min-h-[44px] items-center rounded-xl px-3 text-[15px] font-medium no-underline'

  return (
    <div className="flex justify-center px-3 pt-3 md:px-4 md:pt-4 m-drop">
      <nav ref={nav} aria-label="Main" className="relative flex w-full max-w-[1120px] items-center gap-4 rounded-full border border-[#e5e5e5] bg-white p-2 shadow-[0_1px_2px_rgba(0,0,0,.05)]">
        <Link to={profileId ? '/overview' : '/start'} className="inline-flex min-h-[44px] flex-none items-center gap-2 pl-1 text-ink no-underline">
          <Logo className={onStart ? 'h-logo' : undefined} />
          <span className="text-[15px] font-semibold">Qart.ai</span>
        </Link>
        <div className="ml-2 hidden flex-wrap items-center gap-5 md:flex">
          {MAIN.map((l) => <NavLink key={l.to} to={l.to} className={linkClass}>{t(l.text)}</NavLink>)}
          <div className="relative">
            <button type="button" aria-expanded={more} aria-controls="nav-more" onClick={() => setMore((o) => !o)} className="inline-flex min-h-[44px] cursor-pointer items-center gap-1 border-0 bg-transparent p-0 text-sm font-medium text-ink hover:text-violet">
              {t('Evidence')}
              {fresh && <span aria-hidden="true" className="h-2 w-2 rounded-full bg-violet" />}
              <ChevronDown size={14} aria-hidden="true" />
            </button>
            {more && (
              <div id="nav-more" className="absolute left-0 top-full z-30 mt-2 flex w-60 flex-col gap-0.5 rounded-2xl border border-[#e5e5e5] bg-white p-2 shadow-[0_10px_30px_rgba(11,15,26,.12)]">
                {evidenceLinks(item)}
                {pipeline}
              </div>
            )}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="hidden lg:block"><LanguageSwitch /></span>
          {onStart ? (
            <button type="button" onClick={onStart} className="q-btn q-btn-violet gap-2 py-1 pl-4 pr-1">
              <span className="hidden md:inline">{t(profileId ? 'Edit my profile' : 'Start my profile')}</span>
              <span className="md:hidden">{t(profileId ? 'Profile' : 'Start')}</span>
              <span aria-hidden="true" className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/20"><ChevronRight size={16} /></span>
            </button>
          ) : (
            <Link to="/start?edit=1" className="q-btn q-btn-violet gap-2 py-1 pl-4 pr-1">
              <span className="hidden md:inline">{t('Edit my profile')}</span>
              <span className="md:hidden">{t('Profile')}</span>
              <span aria-hidden="true" className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/20"><ChevronRight size={16} /></span>
            </Link>
          )}
          <button type="button" aria-label="Menu" aria-expanded={menu} aria-controls="nav-menu" onClick={() => setMenu((o) => !o)} className="inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-full border-0 bg-[#f5f5f5] text-ink md:hidden">
            {menu ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
          </button>
        </div>
        {menu && (
          <div id="nav-menu" className="absolute inset-x-2 top-full z-30 mt-2 flex flex-col gap-0.5 rounded-2xl border border-[#e5e5e5] bg-white p-3 shadow-[0_10px_30px_rgba(11,15,26,.12)] md:hidden">
            {MAIN.map((l) => (
              <NavLink key={l.to} to={l.to} className={({ isActive }) => `${item} ${isActive ? 'bg-assumption-bg text-violet' : 'text-ink'}`}>{t(l.text)}</NavLink>
            ))}
            <span className="cap px-3 pt-3">{t('Evidence')}</span>
            {evidenceLinks(item)}
            {pipeline}
            <span className="px-3"><LanguageSwitch /></span>
          </div>
        )}
      </nav>
    </div>
  )
}
