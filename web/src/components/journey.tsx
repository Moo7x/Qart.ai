import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getJSON, useApi } from '../api'
import type { PackInfo, ProgressResponse } from '../types'
import type { LevelsInfo } from '../typesScoring'
import { useJourney } from '../state'

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

function segClass(active: boolean): string {
  return `min-h-[32px] cursor-pointer rounded px-3 text-[13px] border-0 ${active ? 'bg-void font-medium text-white' : 'bg-transparent text-graphite'}`
}

export function ScenarioSwitch() {
  const { scenario, setScenario } = useJourney()
  return (
    <div className="flex items-center gap-2.5">
      <div role="group" aria-label="Scenario" className="card-light flex rounded-md p-[3px]">
        <button type="button" aria-pressed={scenario === 'moderate'} className={segClass(scenario === 'moderate')} onClick={() => setScenario('moderate')}>
          Moderate AI adoption
        </button>
        <button type="button" aria-pressed={scenario === 'fast'} className={segClass(scenario === 'fast')} onClick={() => setScenario('fast')}>
          Fast AI adoption
        </button>
      </div>
      <span className="tag bg-estimate-bg text-estimate">Estimate</span>
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
    <nav aria-label="Your journey" className="-mb-2">
      <ol className="m-0 grid list-none grid-cols-5 p-0">
        {STATIONS.map((s, i) => {
          const isCurrent = i === current
          const reached = done[s.key] || isCurrent
          const lineDone = i < STATIONS.length - 1 && done[s.key]
          return (
            <li key={s.key} className="relative flex min-w-0 flex-col items-start">
              {i < STATIONS.length - 1 && (
                <span aria-hidden="true" className={`absolute left-[7px] right-0 top-[7px] h-[2px] ${lineDone ? 'bg-violet' : 'bg-line'}`} />
              )}
              <Link to={s.to} aria-current={isCurrent ? 'step' : undefined} className="group relative flex min-w-0 flex-col items-start gap-1.5 pr-2 text-void no-underline">
                <span
                  aria-hidden="true"
                  className={`grid h-4 w-4 place-items-center rounded-full border-2 ${done[s.key] ? 'border-violet bg-violet' : isCurrent ? 'border-violet bg-paper' : 'border-line bg-paper'}`}
                >
                  {isCurrent && !done[s.key] && <span className="h-1.5 w-1.5 rounded-full bg-violet" />}
                </span>
                <span className={`truncate text-[12px] leading-tight group-hover:underline ${isCurrent ? 'font-semibold' : reached ? '' : 'text-graphite'} ${isCurrent ? '' : 'max-sm:hidden'}`}>{s.label}</span>
                <span className="hidden truncate font-mono text-[10px] uppercase tracking-wider text-ash sm:block">
                  {done[s.key] ? '✓ ' : ''}{note[s.key]}
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
