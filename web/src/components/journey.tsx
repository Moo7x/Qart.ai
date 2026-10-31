import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getJSON, useApi } from '../api'
import type { PackInfo, ProgressResponse } from '../types'
import type { LevelsInfo } from '../typesScoring'
import { useJourney } from '../state'
import { Label, ScenarioSwitch as AtomScenarioSwitch } from './atoms'

// Official UN SDG colours (un.org brand guidelines) for the goals the pack uses.
const SDG_COLOUR: Record<number, string> = { 4: '#C5192D', 8: '#A21942', 12: '#BF8B2E', 13: '#3F7E44' }

export function sdgColour(target: string): string {
  return SDG_COLOUR[Number(target.split('.')[0])] ?? '#5e5f6e'
}

export function SdgTag({ target }: { target: string }) {
  const goal = Number(target.split('.')[0])
  return (
    <span className="tag font-mono text-white" style={{ background: SDG_COLOUR[goal] ?? '#5e5f6e' }}>
      SDG {target}
    </span>
  )
}

// Skill levels run 0–5 (docs/PHASE2_PLAN.md §1 decision 2) and are shown as stored: "3/5". Their
// labels and "I can…" sentences come from GET /api/pack (levels.yaml), never from this file.
export const LEVEL_MAX = 5 // mirrors src/journey/store.py MAX_LEVEL

export function levelText(level: number | null | undefined): string {
  return level === null || level === undefined ? '—' : `${level}/${LEVEL_MAX}`
}

// The pack's level scale, fetched once and shared by every picker and level display.
let levelsRequest: Promise<LevelsInfo | null> | null = null

export function useLevels(): LevelsInfo | null {
  const [levels, setLevels] = useState<LevelsInfo | null>(null)
  useEffect(() => {
    levelsRequest ??= getJSON<PackInfo>('/api/pack').then((p) => p.levels ?? null, () => {
      levelsRequest = null // retry on the next mount instead of caching a failure
      return null
    })
    let live = true
    levelsRequest.then((value) => { if (live) setLevels(value) })
    return () => { live = false }
  }, [])
  return levels
}

// "3 · working" once the scale has loaded, the number alone before.
export function levelName(levels: LevelsInfo | null, level: number): string {
  const label = levels?.scale.find((s) => s.level === level)?.label
  return label ? `${level} · ${label}` : String(level)
}

export function Dots({ level, tone = 'violet' }: { level: number | null; tone?: 'violet' | 'stone' | 'light' }) {
  const levels = useLevels()
  const filled = level ?? 0
  const on = tone === 'violet' ? 'bg-violet' : tone === 'light' ? 'bg-violet-light' : 'bg-stone'
  const off = tone === 'light' ? 'bg-surface' : 'bg-hairline'
  return (
    <span className="inline-flex items-center gap-2" aria-label={level === null ? 'not stated' : `${level} of ${LEVEL_MAX}, ${levelName(levels, level)}`}>
      <span aria-hidden="true" className="inline-flex gap-[3px]">
        {Array.from({ length: LEVEL_MAX }, (_, i) => <span key={i} className={`h-1.5 w-3 ${i < filled ? on : off}`} />)}
      </span>
      <span aria-hidden="true" className="font-mono text-[11px]">{levelText(level)}</span>
    </span>
  )
}

/** The scenario switch with its ESTIMATE label (the redesign's segmented control, atoms.tsx). */
export function ScenarioSwitch() {
  return (
    <div className="flex items-center gap-2.5">
      <AtomScenarioSwitch />
      <Label kind="estimate" />
    </div>
  )
}

// ---- Career route: where the person is in the journey (the app's signature element) ----

type Station = { key: string; label: string; to: string; paths: string[] }

// Sent after plan progress is saved, so the route redraws without a page reload.
export const PROGRESS_EVENT = 'qart:progress'

const STATIONS: Station[] = [
  { key: 'profile', label: 'Your profile', to: '/start?edit=1', paths: ['/start'] },
  { key: 'picture', label: 'Your picture', to: '/overview', paths: ['/overview'] },
  { key: 'options', label: 'Choose a role', to: '/roles', paths: ['/roles', '/goal'] },
  { key: 'plan', label: 'Your plan', to: '/pathway', paths: ['/pathway'] },
  { key: 'future', label: 'Future you', to: '/future', paths: ['/future'] },
]

// Each station's state comes from saved data: a profile exists, a destination is chosen, plan
// steps are marked done. Nothing is marked done for having opened a page.
export function JourneyRoute() {
  const { profileId, scenario } = useJourney()
  const { pathname } = useLocation()
  const saved = useApi<{ destination: string | null }>(profileId ? `/api/profiles/${profileId}` : null)
  const progress = useApi<ProgressResponse>(profileId ? `/api/profiles/${profileId}/progress?scenario=${scenario}` : null)
  const { reload } = progress
  useEffect(() => {
    window.addEventListener(PROGRESS_EVENT, reload)
    return () => window.removeEventListener(PROGRESS_EVENT, reload)
  }, [reload])
  if (!profileId) return null
  const chosen = Boolean(saved.data?.destination)
  const plan = progress.data?.plan
  const note: Record<string, string> = {
    profile: 'saved',
    picture: 'ready',
    options: chosen ? 'role chosen' : 'pick one',
    plan: plan ? `${plan.steps_done}/${plan.steps} steps` : chosen ? 'not started' : 'after a role',
    future: chosen ? 'compare' : 'after a role',
  }
  const done: Record<string, boolean> = {
    profile: true,
    picture: true,
    options: chosen,
    plan: Boolean(plan && plan.steps > 0 && plan.steps_done === plan.steps),
    future: false,
  }
  const current = STATIONS.findIndex((s) => s.paths.includes(pathname))
  return (
    <nav aria-label="Your journey">
      <ol className="q-steps">
        {STATIONS.map((s, i) => {
          const isCurrent = i === current
          return (
            <li key={s.key} className="flex-none">
              <Link to={s.to} aria-current={isCurrent ? 'step' : undefined} className="!pl-3">
                <span aria-hidden="true" className={`h-2.5 w-2.5 flex-none rounded-full ${done[s.key] || isCurrent ? 'bg-violet' : 'border-2 border-[#a3a3a3]'}`} />
                <span className="flex flex-col leading-tight">
                  <span className="text-[13px] font-semibold">{s.label}</span>
                  <span className="text-[11px] font-normal text-muted">{done[s.key] ? '✓ ' : ''}{note[s.key]}</span>
                </span>
                <span className="sr-only">{done[s.key] ? 'done' : isCurrent ? 'you are here' : 'not done yet'}</span>
              </Link>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

// The one action that moves the person on, at the end of a journey page.
export function NextStep({ to, label, hint }: { to: string; label: string; hint?: string }) {
  return (
    <div className="section flex-row flex-wrap items-center justify-between gap-3">
      <span className="text-sm text-graphite">{hint ?? 'Next step'}</span>
      <Link to={to} className="btn btn-v min-h-[44px]">{label} →</Link>
    </div>
  )
}
