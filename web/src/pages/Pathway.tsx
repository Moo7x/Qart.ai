import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, Check, Clock, ExternalLink, Search, UserRound } from 'lucide-react'
import { ResourceList } from '../components/ResourceList'
import { getPath, getRoles, searchResources } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import { SCENARIO_LABEL } from '../scenarios'
import { skillName } from '../skillNames'
import type { PathPlan, PathStep, SearchResponse } from '../types'
import { btn, Card, EmptyState, Highlight, input as inputCls, Loading, NextStepCard, PageHeader, SectionTitle, StatTile, Tag, type Tone } from '../ui'

const PACES = [3, 5, 8, 10] // hours per week offered as chips; the planner re-plans for each
const SEARCH_RETRIES = 4 // a GPU cold start took ~100 s; 4 × 25 s covers it
const SEARCH_RETRY_MS = 25000

const STEP_META: Record<PathStep['type'], { label: string; tone: Tone; marker: string }> = {
  course: { label: 'course', tone: 'action', marker: 'bg-action-tint text-action-ink' },
  checkin: { label: 'check-in', tone: 'coral', marker: 'bg-coral-tint text-coral-ink' },
  practice_case: { label: 'practice case', tone: 'marigold', marker: 'bg-marigold-tint text-marigold-ink' },
}

/** Week range for each step when hours are done in order at `pace` hours a week (an estimate). */
function weekRanges(steps: PathStep[], pace: number): string[] {
  let done = 0
  return steps.map(s => {
    const start = Math.floor(done / pace) + 1
    done += s.hours
    const end = Math.max(start, Math.ceil(done / pace))
    return start === end ? `Week ${start}` : `Weeks ${start}–${end}`
  })
}

/** Ticks are a personal checklist kept in this browser only; they are never evidence. */
function useChecklist(key: string) {
  const read = (): string[] => {
    try { return JSON.parse(localStorage.getItem(key) ?? '[]') as string[] } catch { return [] }
  }
  const [done, setDone] = useState<string[]>(read)
  useEffect(() => { setDone(read()) }, [key]) // eslint-disable-line react-hooks/exhaustive-deps
  const toggle = (id: string) => setDone(prev => {
    const next = prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    try { localStorage.setItem(key, JSON.stringify(next)) } catch { /* private window: keep in memory */ }
    return next
  })
  return { done, toggle }
}

export default function Pathway() {
  const userId = useUserId()
  const [params] = useSearchParams()
  const roleId = params.get('role') // null: the planner picks the best role across both scenarios
  const [pace, setPace] = useState<number | null>(null) // null: the profile's weekly hours
  const [path, setPath] = useState<PathPlan | null>(null)
  const [roleTitle, setRoleTitle] = useState('')
  const [failed, setFailed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [found, setFound] = useState<SearchResponse | null>(null)
  const [searching, setSearching] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [loading])
  const checklist = useChecklist(`qart.pathway.done.${userId}.${path?.target_role_id ?? roleId ?? 'best'}`)

  useEffect(() => {
    setFailed(false)
    getPath(userId, roleId, pace ?? undefined)
      .then(p => {
        setPath(p)
        getRoles().then(rs => setRoleTitle(rs.find(r => r.id === p.target_role_id)?.title ?? p.target_role_id)).catch(() => setRoleTitle(p.target_role_id))
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }, [userId, roleId, pace])

  const runSearch = async (text: string) => {
    if (text.trim().length < 2) return
    setSearching(true)
    try {
      const first = await searchResources(text.trim(), undefined, 6)
      setFound(first)
      // While the GPU worker starts, ask again so the keyword results get replaced by GPU results.
      let latest = first
      for (let attempt = 0; attempt < SEARCH_RETRIES && latest.engine === 'keyword' && latest.note.includes('starting up'); attempt++) {
        await new Promise(resolve => window.setTimeout(resolve, SEARCH_RETRY_MS))
        latest = await searchResources(text.trim(), undefined, 6)
        setFound(latest)
      }
    } finally {
      setSearching(false)
    }
  }

  if (loading) return <Loading what="your pathway" />

  if (failed || !path) {
    return (
      <div className="max-w-3xl mx-auto">
        <EmptyState title="Could not plan a pathway">The server did not return a plan. Check that the backend is running.</EmptyState>
      </div>
    )
  }

  const inputs = path.profile_inputs ?? []
  const fromDirection = !roleId && inputs.some(line => line.startsWith('Direction'))
  const paces = [...new Set([...PACES, path.weekly_hours])].sort((a, b) => a - b)
  const ranges = weekRanges(path.steps, path.weekly_hours)
  const free = path.steps.filter(s => s.cost === 'free').length
  const doneCount = path.steps.filter(s => checklist.done.includes(s.ref)).length

  return (
    <div ref={root} className="max-w-3xl mx-auto space-y-8">
      <div data-reveal>
        <PageHeader
          title={<>Your <Highlight>pathway</Highlight></>}
          intro={<>To <strong className="font-medium text-ink">{roleTitle || 'your next role'}</strong>. Steps in order, each closing a gap from your match. Free resources come first; every course links to its source.</>}
          aside={<Tag tone="linen">{roleId ? 'Role you chose' : fromDirection ? 'Role from your direction' : 'Best role across both scenarios'}</Tag>}
        />
      </div>

      {inputs.length > 0 && (
        <div data-reveal className="bg-action-tint rounded-lg p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 font-semibold text-action-ink"><UserRound size={16} aria-hidden="true" /> Planned from your profile</span>
            <Link to="/start" className="text-sm text-action-ink hover:underline">Change my answers</Link>
          </div>
          <ul className="mt-2 space-y-1 text-sm text-ink list-disc pl-5">
            {inputs.map(line => <li key={line}>{line}</li>)}
          </ul>
        </div>
      )}

      <div data-reveal className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatTile tone="action" icon={Clock} label="Total learning" value={`${path.total_hours} h`} />
        <StatTile tone="marigold" label={`Weeks at ${path.weekly_hours} h/week (plan fits ${path.horizon_weeks ?? 6})`} value={path.weeks} />
        <StatTile tone="mocha" label="Free steps" value={`${free} of ${path.steps.length}`} />
        <StatTile tone="linen" icon={Check} label="Ticked (your checklist)" value={`${doneCount} of ${path.steps.length}`} />
      </div>

      <div data-reveal className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-ink" id="pace-label">Hours per week</span>
        <div role="radiogroup" aria-labelledby="pace-label" className="inline-flex flex-wrap bg-linen rounded-md p-1">
          {paces.map(h => (
            <button
              key={h} role="radio" aria-checked={path.weekly_hours === h}
              onClick={() => setPace(h)}
              className={`px-4 py-1.5 rounded-sm text-sm tabular-nums transition-colors duration-200 ${path.weekly_hours === h ? 'bg-surface text-ink font-medium shadow-[0_1px_2px_rgb(0_0_0/0.06)]' : 'text-graphite hover:text-ink'}`}
            >
              {h} h
            </button>
          ))}
        </div>
        <span className="text-xs text-graphite">The planner re-plans for each pace. Hours and weeks are estimates.</span>
      </div>

      <section data-reveal>
        <SectionTitle aside={<span className="text-xs text-graphite">Works in: {path.robust_across.map(s => SCENARIO_LABEL[s]).join(' · ')}</span>}>Steps</SectionTitle>
        <ol className="relative">
          <div className="absolute left-4 top-4 bottom-4 w-px bg-hairline-strong" aria-hidden="true" />
          {path.steps.map((step, i) => {
            const meta = STEP_META[step.type]
            const isDone = checklist.done.includes(step.ref)
            return (
              <li key={step.order} className="relative flex items-start gap-4 pb-3">
                <button
                  type="button" onClick={() => checklist.toggle(step.ref)} aria-pressed={isDone}
                  aria-label={isDone ? `Untick step ${step.order}` : `Tick step ${step.order} as done`}
                  className={`w-8 h-8 rounded-full text-sm font-semibold flex items-center justify-center shrink-0 relative z-10 tabular-nums ring-4 ring-canvas transition-colors duration-200 ${isDone ? 'bg-action text-white' : meta.marker}`}
                >
                  {isDone ? <Check size={16} strokeWidth={2.5} aria-hidden="true" /> : step.order}
                </button>
                <Card className={`flex-1 min-w-0 p-4 ${isDone ? 'opacity-70' : ''}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-ink">{step.title}</span>
                        <Tag tone={meta.tone}>{meta.label}</Tag>
                        <Tag tone={step.cost === 'free' ? 'mocha' : 'linen'}>{step.cost}</Tag>
                      </div>
                      {step.because && <p className="mt-1.5 text-sm text-graphite">{step.because}</p>}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-semibold text-ink tabular-nums">{step.hours} h</div>
                      <div className="text-xs text-graphite">{ranges[i]}</div>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    {step.skills.map(sk => <Tag key={sk} tone="outline">{skillName(sk)}</Tag>)}
                    {step.sdg_targets?.map(t => <Tag key={t} tone="linen">SDG {t}</Tag>)}
                  </div>
                  {step.url && (
                    <a href={step.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm text-action-ink hover:underline">
                      Open{step.retrieved ? ` · checked ${step.retrieved}` : ''} <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  )}
                </Card>
              </li>
            )
          })}
        </ol>
        <p className="text-xs text-graphite mt-1">
          Ticks are your own checklist, kept in this browser; they are not evidence. Evidence comes from practice cases and check-ins.
          Gap left after this path in the harder scenario: {path.worst_case_gap.toFixed(2)} (weighted, 0 = none).
        </p>
      </section>

      <section data-reveal>
        <SectionTitle>Search learning resources and work evidence</SectionTitle>
        <form onSubmit={e => { e.preventDefault(); runSearch(query) }} className="flex gap-2">
          <input
            value={query} onChange={e => setQuery(e.target.value)}
            placeholder="e.g. challenge adjustments without documents" aria-label="Search learning resources"
            className={`${inputCls} flex-1 min-w-0`}
          />
          <button type="submit" disabled={searching} className={btn.outline}>
            <Search size={16} aria-hidden="true" /> {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        <p className="text-xs text-graphite mt-2">Searches verified courses and O*NET task statements. Every result carries its source and date.</p>
        {found && <div className="mt-4"><ResourceList response={found} /></div>}
      </section>

      <div data-reveal>
        <NextStepCard
          eyebrow="Next"
          title="How this path helps the Global Goals"
          action={<Link to={`/impact?role=${encodeURIComponent(path.target_role_id)}`} className={`${btn.primary} whitespace-nowrap`}>See my SDG impact <ArrowRight size={16} aria-hidden="true" /></Link>}
        >
          Each role and skill is tagged to UN Sustainable Development Goal targets.
        </NextStepCard>
      </div>
    </div>
  )
}
