import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, Award, BookOpen, Check, ClipboardList, Clock, ExternalLink, Hammer, Info, Repeat, Search, TriangleAlert, Video, Wallet } from 'lucide-react'
import { ResourceList } from '../components/ResourceList'
import { getLearningPlan, getUserSignals, searchResources } from '../api'
import { SignalBadge } from '../components/SignalParts'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { LearningPlanResponse, LearningPlanStep, SearchResponse, UserSignals } from '../types'
import { btn, Card, EmptyState, Highlight, input as inputCls, Loading, NextStepCard, PageHeader, SectionTitle, StatTile, Tag, type Tone } from '../ui'

const SEARCH_RETRIES = 4 // a GPU cold start took ~100 s; 4 × 25 s covers it
const SEARCH_RETRY_MS = 25000
const BAND_TONE: Record<string, Tone> = { 'Strong match': 'action', 'Good match': 'marigold', Stretch: 'linen' }
const FORMAT_ICON = { hands_on: Hammer, videos: Video, reading: BookOpen, mentor: ClipboardList } as const
const FORMAT_LABEL: Record<string, string> = { hands_on: 'Hands-on', videos: 'Videos', reading: 'Reading', mentor: 'Mentor-led' }
const LEVEL: Record<string, string> = { '0': 'none', '0.3': 'heard of it', '0.7': 'use sometimes', '1': 'confident' }

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

function CostBadge({ step }: { step: LearningPlanStep }) {
  if (step.kind === 'milestone') return <Tag tone="mocha">Free practice</Tag>
  if (step.kind === 'no_resource') return <Tag tone="linen">No course yet</Tag>
  if (step.hrd_claimable && step.cost_to_user_myr === 0) return <Tag tone="action" icon={Wallet}>HRD-claimable · RM0 to you if approved</Tag>
  if (step.hrd_claimable) return <Tag tone="marigold" icon={Wallet}>HRD-claimable{step.cost_to_user_myr ? ` · RM${step.cost_to_user_myr}` : ''}</Tag>
  if (step.cost_type === 'free_if_eligible') return <Tag tone="mocha">Free if eligible</Tag>
  if (step.cost_to_user_myr === 0) return <Tag tone="mocha">Free</Tag>
  if (step.cost_to_user_myr === null) return <Tag tone="linen">Price not stated</Tag>
  return <Tag tone="linen">RM{step.cost_to_user_myr}</Tag>
}

const weeks = (s: LearningPlanStep) => (s.start_week === s.end_week ? `Week ${s.start_week}` : `Weeks ${s.start_week}–${s.end_week}`)

function StepCard({ step, data, done, onToggle, onSwap }: {
  step: LearningPlanStep; data: LearningPlanResponse; done: boolean; onToggle: () => void; onSwap: (course: string) => void
}) {
  const marker = step.kind === 'milestone' ? 'bg-marigold-tint text-marigold-ink' : step.kind === 'no_resource' ? 'bg-linen text-graphite' : 'bg-action-tint text-action-ink'
  const alternatives = step.alternatives.filter(a => data.alternatives?.[a])
  return (
    <li className="relative flex items-start gap-4 pb-3">
      <button
        type="button" onClick={onToggle} aria-pressed={done} aria-label={done ? `Untick step ${step.order}` : `Tick step ${step.order} as done`}
        className={`w-8 h-8 rounded-full text-sm font-semibold flex items-center justify-center shrink-0 relative z-10 tabular-nums ring-4 ring-canvas transition-colors duration-200 ${done ? 'bg-action text-white' : marker}`}
      >
        {done ? <Check size={16} strokeWidth={2.5} aria-hidden="true" /> : step.order}
      </button>
      <Card className={`flex-1 min-w-0 p-4 space-y-2 ${done ? 'opacity-70' : ''}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-semibold text-ink">{step.title}</span>
              {step.status === 'draft' && <Tag tone="outline">Draft</Tag>}
            </div>
            {step.provider && <p className="text-sm text-graphite">{step.provider}</p>}
          </div>
          <div className="text-right shrink-0">
            <div className="text-sm font-semibold text-ink tabular-nums">{step.hours} h</div>
            <div className="text-xs text-graphite">{weeks(step)}</div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <CostBadge step={step} />
          {step.formats.map(f => {
            const Icon = FORMAT_ICON[f as keyof typeof FORMAT_ICON]
            return <Tag key={f} tone="linen" icon={Icon}>{FORMAT_LABEL[f] ?? f}</Tag>
          })}
          {step.certificate && <Tag tone="linen" icon={Award}>Certificate</Tag>}
          {step.date_to_confirm && <Tag tone="marigold" icon={Clock}>Date to confirm</Tag>}
          {step.from_level !== null && step.to_level !== null && step.kind === 'course' && (
            <span className="text-xs text-graphite">{LEVEL[String(step.from_level)] ?? step.from_level} → {LEVEL[String(step.to_level)] ?? step.to_level}</span>
          )}
        </div>
        <ul className="space-y-0.5 text-sm text-graphite">{step.reasons.map(r => <li key={r}>{r}</li>)}</ul>
        {step.sdg_targets.length > 0 && (
          <div className="flex flex-wrap gap-1.5">{step.sdg_targets.map(t => <Tag key={t.id} tone="outline" title={t.title}>SDG {t.id}</Tag>)}</div>
        )}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1">
          {step.url && (
            <a href={step.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-action-ink hover:underline">
              Open course <ExternalLink size={12} aria-hidden="true" />
            </a>
          )}
          {step.case_id && (
            <Link to={`/workspace/${step.case_id}`} className="inline-flex items-center gap-1 text-sm text-action-ink hover:underline">
              Practise in Qart <ArrowRight size={12} aria-hidden="true" />
            </Link>
          )}
          {step.last_verified && <span className="text-xs text-graphite">Last checked {step.last_verified}</span>}
          {alternatives.length > 0 && (
            <label className="flex w-full sm:w-auto min-w-0 items-center gap-1.5 text-sm text-graphite">
              <Repeat size={14} className="shrink-0" aria-hidden="true" /> Swap
              <select
                value="" onChange={e => e.target.value && onSwap(e.target.value)}
                className="min-w-0 flex-1 sm:flex-none sm:max-w-[14rem] rounded-sm border border-hairline-strong bg-surface px-2 py-1 text-sm text-ink"
              >
                <option value="">for…</option>
                {alternatives.map(a => {
                  const alt = data.alternatives![a]
                  const cost = alt.cost_type === 'free' ? 'free' : alt.cost_myr ? `RM${alt.cost_myr}` : alt.cost_type?.replace(/_/g, ' ')
                  return <option key={a} value={a}>{alt.title} ({alt.hours} h, {cost})</option>
                })}
              </select>
            </label>
          )}
        </div>
      </Card>
    </li>
  )
}

/** The learning plan for the chosen role (pathway.md §5; Domain 1 must-have 4). */
export default function Pathway() {
  const userId = useUserId()
  const [params, setParams] = useSearchParams()
  const roleId = params.get('role') // null: the top-ranked role
  const [swaps, setSwaps] = useState<Record<string, string>>({})
  const [data, setData] = useState<LearningPlanResponse | null>(null)
  const [failed, setFailed] = useState(false)
  const [market, setMarket] = useState<UserSignals | null>(null)
  const [query, setQuery] = useState('')
  const [found, setFound] = useState<SearchResponse | null>(null)
  const [searching, setSearching] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [data !== null])
  const checklist = useChecklist(`qart.plan.done.${userId}.${data?.role?.role_id ?? roleId ?? 'top'}`)

  useEffect(() => { setSwaps({}) }, [roleId, userId])
  useEffect(() => {
    getLearningPlan(userId, roleId, swaps).then(d => { setData(d); setFailed(false) }).catch(() => setFailed(true))
  }, [userId, roleId, swaps])
  // Market context is informational only: it never changes a step, an hour or a score.
  useEffect(() => { getUserSignals(userId).then(setMarket).catch(() => setMarket(null)) }, [userId])

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

  if (failed) return <div className="max-w-3xl mx-auto"><EmptyState title="Could not build a learning plan">The server did not return a plan. Check that the backend is running.</EmptyState></div>
  if (!data) return <Loading what="your learning plan" />
  if (data.empty_profile || !data.plan || !data.role) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <EmptyState title="Not enough to plan yet">{data.message}</EmptyState>
        <Link to="/start" className={btn.primary}>Add skills on your profile <ArrowRight size={16} aria-hidden="true" /></Link>
      </div>
    )
  }

  const { plan, role, answers } = data
  const s = plan.summary
  const inPlan = plan.steps.filter(x => x.in_timeframe)
  const nextPhase = plan.steps.filter(x => !x.in_timeframe)
  const months = answers?.timeframe_months ?? 3
  const moreWeeks = Math.max(0, s.weeks_needed - s.timeframe_weeks)
  const swap = (step: LearningPlanStep, course: string) => setSwaps(prev => ({ ...prev, [step.skill_ids[0]]: course }))
  const list = (steps: LearningPlanStep[]) => (
    <ol className="relative">
      <div className="absolute left-4 top-4 bottom-4 w-px bg-hairline-strong" aria-hidden="true" />
      {steps.map(step => (
        <StepCard
          key={`${step.order}-${step.resource_id}`} step={step} data={data}
          done={checklist.done.includes(`${step.kind}:${step.resource_id ?? step.order}`)}
          onToggle={() => checklist.toggle(`${step.kind}:${step.resource_id ?? step.order}`)}
          onSwap={course => swap(step, course)}
        />
      ))}
    </ol>
  )

  return (
    <div ref={root} className="max-w-3xl mx-auto space-y-8">
      <div data-reveal>
        <PageHeader
          title={<>Your learning <Highlight>plan</Highlight></>}
          intro={<>To <strong className="font-medium text-ink">{role.name}</strong>: real courses in order, week by week, at {answers?.weekly_hours} h a week. You choose what to take.</>}
          aside={<Tag tone={BAND_TONE[role.band]}>{role.band} · {role.score}</Tag>}
        />
        {data.other_roles && data.other_roles.length > 1 && (
          <div className="mt-2 flex flex-wrap items-center gap-1.5" role="radiogroup" aria-label="Plan for another role">
            <span className="text-sm text-graphite mr-1">Plan for:</span>
            {data.other_roles.map(r => (
              <button
                key={r.role_id} type="button" role="radio" aria-checked={r.role_id === role.role_id}
                onClick={() => setParams(r.role_id === data.other_roles![0].role_id ? {} : { role: r.role_id })}
                className={`rounded-full px-3 py-1 text-sm transition-colors duration-200 ${r.role_id === role.role_id ? 'bg-action-tint text-action-ink font-medium' : 'border border-hairline-strong text-graphite hover:bg-linen'}`}
              >
                {r.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {plan.action_items.length > 0 && (
        <Card data-reveal className="p-5 border-marigold/40 bg-marigold-tint">
          <div className="flex items-center gap-2 font-semibold text-marigold-ink"><TriangleAlert size={16} aria-hidden="true" /> To do before you start</div>
          <ul className="mt-2 space-y-1 text-sm text-ink list-disc pl-5">{plan.action_items.map(a => <li key={a}>{a}</li>)}</ul>
        </Card>
      )}

      <div data-reveal className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatTile tone="action" icon={Clock} label="Total learning" value={`${s.total_hours} h`} />
        <StatTile tone="marigold" label={s.fits_timeframe ? `Fits your ${months}-month plan` : `Needs ~${moreWeeks} more weeks than your ${months} months`} value={`${s.weeks_needed} wk`} />
        <StatTile tone="mocha" icon={Wallet} label={`Cost to you${s.steps_with_unknown_cost ? ` (+${s.steps_with_unknown_cost} with no price stated)` : ''}`} value={`RM${s.cost_to_user_myr}`} />
        <StatTile tone="linen" icon={Award} label={s.cost_possibly_covered_by_employer_myr > 0 ? `Certificates · employer may cover RM${s.cost_possibly_covered_by_employer_myr}` : 'Certificates'} value={s.certificates} />
      </div>

      <section data-reveal>
        <SectionTitle aside={<Link to="/start" className="text-sm text-action-ink hover:underline">Change my answers</Link>}>Week by week</SectionTitle>
        {list(inPlan)}
        {nextPhase.length > 0 && (
          <>
            <div className="my-4 flex items-center gap-2 text-xs font-medium text-coral-ink" role="separator">
              <span className="h-px flex-1 bg-coral/40" /> End of your {months}-month plan · Next phase <span className="h-px flex-1 bg-coral/40" />
            </div>
            {list(nextPhase)}
          </>
        )}
        <p className="text-xs text-graphite mt-1">
          Hours include a 20% practice buffer. Ticks are your own checklist, kept in this browser; evidence comes from practice cases.
        </p>
      </section>

      {plan.notes.length > 0 && (
        <section data-reveal>
          <SectionTitle>Notes</SectionTitle>
          <ul className="space-y-1.5 text-sm text-graphite list-disc pl-5">{plan.notes.map(n => <li key={n}>{n}</li>)}</ul>
        </section>
      )}

      <details data-reveal className="rounded-lg border border-hairline bg-surface p-5">
        <summary className="cursor-pointer font-semibold text-ink inline-flex items-center gap-2"><Info size={16} aria-hidden="true" /> How course funding works (HRD Corp, e-LATiH, Rakyat Digital)</summary>
        <div className="mt-3 space-y-3 text-sm text-graphite">
          <p>
            HRD Corp-claimable courses are paid from your employer's HRD Corp levy. Your employer, not you, applies through e-TRiS before the training starts, and approval is not guaranteed.
            e-LATiH has free and paid courses. Rakyat Digital offers free Coursera access and AI untuk Rakyat for eligible Malaysians. Rules change, so check the official pages:
          </p>
          <ul className="space-y-1.5">
            {data.funding_links.map(l => (
              <li key={l.url}>
                <a href={l.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-action-ink hover:underline">{l.label} <ExternalLink size={12} aria-hidden="true" /></a>
                <span className="block text-xs">{l.note}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs">
            Course catalogue: {data.catalogue.verified} verified courses{data.catalogue.drafts ? `, ${data.catalogue.drafts} drafts ${data.catalogue.drafts_in_use ? 'shown for development' : 'not used yet'}` : ''}, curated by the team, last checked {data.catalogue.last_full_review}.{' '}
            <Link to="/sources" className="text-action-ink hover:underline">All data sources</Link>
          </p>
        </div>
      </details>

      {market && (market.user_skills.length > 0 || market.rising_skills_not_held.length > 0) && (
        <section data-reveal>
          <SectionTitle aside={<Tag tone="linen">Signal, not a forecast</Tag>}>Market context</SectionTitle>
          <Card className="p-5 space-y-4">
            {market.rising_skills_not_held.length > 0 && (
              <div>
                <div className="text-sm font-medium text-ink mb-2">Rising skills you don't have yet</div>
                <ul className="flex flex-wrap gap-2">
                  {market.rising_skills_not_held.map(x => (
                    <li key={x.id} className="inline-flex items-center gap-1.5 rounded-md border border-hairline px-2.5 py-1.5 text-sm text-ink">{x.name} <SignalBadge label={x.label} /></li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-graphite">
              {market.note} {market.attribution} · data to {market.data_as_of}. <Link to="/signals" className="text-action-ink hover:underline">See the radar</Link>
            </p>
          </Card>
        </section>
      )}

      <section data-reveal>
        <SectionTitle>Search more courses and work tasks</SectionTitle>
        <form onSubmit={e => { e.preventDefault(); runSearch(query) }} className="flex gap-2">
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="e.g. Power BI dashboards for finance" aria-label="Search learning resources" className={`${inputCls} flex-1 min-w-0`} />
          <button type="submit" disabled={searching} className={btn.outline}><Search size={16} aria-hidden="true" /> {searching ? 'Searching…' : 'Search'}</button>
        </form>
        <p className="text-xs text-graphite mt-2">Searches verified courses and O*NET task statements. Every result carries its source and date.</p>
        {found && <div className="mt-4"><ResourceList response={found} /></div>}
      </section>

      <div data-reveal>
        <NextStepCard
          eyebrow="Next"
          title="How this plan helps the Global Goals"
          action={<Link to={`/impact?role=${encodeURIComponent(role.role_id)}`} className={`${btn.primary} whitespace-nowrap`}>See my SDG impact <ArrowRight size={16} aria-hidden="true" /></Link>}
        >
          Each role and skill is tagged to UN Sustainable Development Goal targets.
        </NextStepCard>
      </div>
    </div>
  )
}
