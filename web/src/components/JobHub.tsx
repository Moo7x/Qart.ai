import { ArrowRight, ChevronDown } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../api'
import type { OccupationPreview } from '../types'
import { Loading, Problem } from './ui'
import { Windows, type Pane } from './Windows'

// "Where you are" on the Overview: the job on a dark card, then the four kinds of evidence as small
// charts, each opening its source and caveats. The kinds stay separate (observed AI use, potential
// exposure, employment, expert list) and none is turned into a verdict.

type Kind = 'observed' | 'estimate' | 'expert'
const KIND: Record<Kind, [string, string]> = {
  observed: ['Observed', 'bg-observed-bg text-observed'],
  estimate: ['Estimate', 'bg-estimate-bg text-estimate'],
  expert: ['Expert view', 'bg-mist text-graphite'],
}

function ChartCard({ title, kind, source, onOpen, children }: { title: string; kind: Kind; source: string; onOpen: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onOpen} aria-label={`${title}: details and source`} className="flex min-w-0 cursor-pointer flex-col gap-2.5 rounded-[22px] border border-transparent bg-white p-4 text-left font-[inherit] text-ink transition-colors hover:border-[#d9d0ff]">
      <span className="flex items-start justify-between gap-2">
        <span className="text-[13px] font-semibold leading-snug">{title}</span>
        <span className={`tag shrink-0 whitespace-nowrap ${KIND[kind][1]}`}>{KIND[kind][0]}</span>
      </span>
      {children}
      <span className="mt-auto text-[11px] leading-snug text-muted">{source}</span>
    </button>
  )
}

function Donut({ value }: { value: number }) {
  const c = 2 * Math.PI * 26
  return (
    <span className="flex items-center gap-3">
      <svg width="72" height="72" viewBox="0 0 72 72" className="flex-none" aria-hidden="true">
        <circle cx="36" cy="36" r="26" fill="none" stroke="#d9d0ff" strokeWidth="12" />
        <circle cx="36" cy="36" r="26" fill="none" stroke="#6c47ff" strokeWidth="12" strokeDasharray={`${(c * value) / 100} ${c}`} transform="rotate(-90 36 36)" />
        <text x="36" y="40" textAnchor="middle" className="fill-ink font-mono text-[13px]">{Math.round(value)}%</text>
      </svg>
      <span className="flex flex-col gap-1.5 text-[11px] leading-tight text-[#404040]">
        <span className="flex gap-1.5"><i aria-hidden="true" className="mt-0.5 h-2.5 w-2.5 flex-none rounded-[3px] bg-violet" />AI does the task {Math.round(value)}%</span>
        <span className="flex gap-1.5"><i aria-hidden="true" className="mt-0.5 h-2.5 w-2.5 flex-none rounded-[3px] bg-range" />AI helps a person {100 - Math.round(value)}%</span>
      </span>
    </span>
  )
}

const STEP_COLOUR = ['#eeeef0', '#d9d0ff', '#9d86ff', '#6c47ff']

function Gradient({ step }: { step: number }) {
  return (
    <span className="flex flex-col gap-1" aria-hidden="true">
      <span className="grid grid-cols-4 gap-[3px]">{STEP_COLOUR.map((c) => <span key={c} className="h-2.5 rounded" style={{ background: c }} />)}</span>
      <span className="grid grid-cols-4 text-[10px] text-muted">
        {[1, 2, 3, 4].map((s) => <span key={s} className={s === step ? 'font-bold text-violet' : ''}>{s}{s === step ? ' ← yours' : ''}</span>)}
      </span>
    </span>
  )
}

function Sparkline({ points }: { points: { period: string; value: number }[] }) {
  const values = points.map((p) => p.value)
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const span = hi - lo || 1
  const xy = values.map((v, i) => [(200 * i) / Math.max(values.length - 1, 1), 54 - ((v - lo) / span) * 46])
  const line = xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const [lx, ly] = xy[xy.length - 1]
  return (
    <span className="flex flex-col gap-1" aria-hidden="true">
      <svg viewBox="0 0 200 60" preserveAspectRatio="none" className="h-[56px] w-full">
        <polygon points={`0,60 ${line} 200,60`} fill="#f1edff" />
        <polyline points={line} fill="none" stroke="#6c47ff" strokeWidth="2" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <circle cx={lx} cy={ly} r="3.5" fill="#5d38f5" />
      </svg>
      <span className="flex justify-between text-[10px] text-muted"><span>{points[0]?.period}</span><span>{points.at(-1)?.period}</span></span>
    </span>
  )
}

export function JobHub({ soc, title, impact, page, routes, summary }: { soc: string; title: string; impact: string; page: number | string; routes: number; summary: string }) {
  const view = useApi<OccupationPreview>(`/api/occupations/${soc}`)
  const [open, setOpen] = useState<Pane | null>(null)
  const [tasksOpen, setTasksOpen] = useState(false)
  if (view.loading) return <Loading what="the evidence for your job" />
  if (view.error) return <Problem what="the evidence for your job" message={view.error} onRetry={view.reload} />
  const p = view.data
  if (!p) return null
  const automation = p.ai_use?.automation ?? null
  const step = Number(p.exposure?.gradient?.match(/Gradient (\d)/)?.[1] ?? 0)
  const series = p.employment?.points ?? []
  const last = series.at(-1)
  const detail: Record<string, Pane> = {
    use: {
      key: 'use', title: 'AI use today', hint: `Anthropic Economic Index · ${p.ai_use?.period ?? ''}`,
      body: p.ai_use ? <p className="m-0">{p.ai_use.share}% of sampled Claude conversations worldwide{p.ai_use.share_local !== null ? ` and ${p.ai_use.share_local}% in Malaysia` : ''} are about this occupation ({p.ai_use.period}). {p.ai_use.automation}% of that use is automation-style; the rest is people working with AI. It shows use of an AI assistant, not job losses.</p> : <p className="m-0">Not published for this occupation (missing, not zero).</p>,
    },
    exposure: {
      key: 'exposure', title: 'Could AI do these tasks?', hint: 'ILO Working Paper 140 (2025)',
      body: p.exposure ? <p className="m-0">The ILO rates {p.exposure.title} (ISCO-08 {p.exposure.isco}) {p.exposure.gradient}, mean task score {p.exposure.mean} of 1. This is technical potential, not adoption. Linked through ESCO &ldquo;{p.esco.title}&rdquo; ({p.esco.match}).</p> : <p className="m-0">{p.isco_note || 'No exposure score for this group.'}</p>,
    },
    jobs: {
      key: 'jobs', title: 'Jobs like it in Malaysia', hint: 'DOSM via OpenDOSM',
      body: p.employment ? <p className="m-0">{p.employment.title}: {p.employment.headline}. This is the whole major group, not this occupation alone. {p.employment.note}</p> : <p className="m-0">No Malaysian group series linked yet.</p>,
    },
    critical: {
      key: 'critical', title: 'Hard-to-fill list', hint: 'MyCOL 2024/2025 (TalentCorp, Ministry of Human Resources)',
      body: <p className="m-0">{p.mycol ? (p.mycol.listed ? `MyCOL lists ${p.mycol.name} as critical (hard to fill) in Malaysia.` : `Not among the ${p.mycol.of} occupations MyCOL lists as critical.`) : 'Needs the ISCO-08 link to check.'}</p>,
    },
  }
  return (
    <div className="flex flex-1 flex-col gap-4">
      <section aria-label="Your job today" className="relative flex flex-col gap-4 overflow-hidden rounded-[28px] bg-void p-6 text-white">
        <span aria-hidden="true" className="absolute -right-16 -top-16 h-56 w-56 rounded-full border-[28px] border-white/[0.06]" />
        <span className="relative font-mono text-[11px] uppercase tracking-[0.16em] text-violet-light">Your job today</span>
        <h2 className="relative m-0 text-[26px] font-semibold leading-tight tracking-tight">{title}</h2>
        <p className="relative m-0 text-[14px] leading-relaxed text-[#d4d4dc]">{summary}</p>
        <button type="button" aria-expanded={tasksOpen} onClick={() => setTasksOpen((o) => !o)} className="relative inline-flex min-h-[36px] cursor-pointer items-center gap-2 self-start rounded-full border-0 bg-white/[0.14] px-3.5 font-[inherit] text-[12px] text-white">
          TalentCorp: {impact} impact · p. {page}
          <ChevronDown size={14} aria-hidden="true" className={`transition-transform ${tasksOpen ? 'rotate-180' : ''}`} />
        </button>
        {tasksOpen && p.tasks.length > 0 && (
          <div className="relative flex flex-col gap-1.5 text-[13px] text-white/80">
            <span className="font-mono text-[11px] uppercase tracking-widest text-violet-light">Most important tasks (O*NET {p.soc})</span>
            <ol className="m-0 flex flex-col gap-1 pl-5">{p.tasks.map((t) => <li key={t.task}>{t.text}</li>)}</ol>
          </div>
        )}
        <Link to="/roles" className="relative flex items-center justify-between gap-3 rounded-2xl bg-white px-5 py-3 text-ink no-underline hover:bg-[#f5f2ee]">
          <span className="flex flex-col">
            <span className="text-[15px] font-semibold">Explore {routes} route{routes === 1 ? '' : 's'} out</span>
            <span className="text-[12px] text-muted">Roles TalentCorp lists from this job in GBS</span>
          </span>
          <ArrowRight size={18} aria-hidden="true" />
        </Link>
      </section>

      <section aria-label="The signals behind this" className="flex flex-1 flex-col gap-3">
        <h3 className="m-0 text-[15px] font-semibold">The signals behind this</h3>
        <div className="grid flex-1 grid-cols-1 gap-3 min-[420px]:grid-cols-2">
          <ChartCard title="AI use today" kind="observed" source={`Anthropic Economic Index · ${p.ai_use?.period ?? '—'}`} onOpen={() => setOpen(detail.use)}>
            {automation !== null ? <Donut value={automation} /> : <span className="text-[13px] text-muted">Not published for this occupation.</span>}
          </ChartCard>
          <ChartCard title="Could AI do the tasks?" kind="estimate" source="ILO exposure gradient · potential, not adoption" onOpen={() => setOpen(detail.exposure)}>
            <span className="font-mono text-[26px] leading-none">{p.exposure?.mean != null ? <>{Math.round(100 * p.exposure.mean)}<span className="text-[13px] text-muted">/100</span></> : '—'}</span>
            {step > 0 && <Gradient step={step} />}
          </ChartCard>
          <ChartCard title="Jobs like it in Malaysia" kind="observed" source={p.employment ? `DOSM · ${p.employment.title.split(':')[0]}` : 'DOSM'} onOpen={() => setOpen(detail.jobs)}>
            <span className="flex items-baseline gap-2">
              <span className="font-mono text-[26px] leading-none">{last ? `${last.value.toFixed(1)}%` : '—'}</span>
              {p.employment && <span className="text-[11px] text-muted">of employees · {p.employment.direction}</span>}
            </span>
            {series.length > 1 && <Sparkline points={series} />}
          </ChartCard>
          <ChartCard title="Hard-to-fill list" kind="expert" source="MyCOL 2024/2025 critical occupations" onOpen={() => setOpen(detail.critical)}>
            <span className="text-[20px] font-semibold leading-tight">{p.mycol ? (p.mycol.listed ? 'Listed' : 'Not listed') : '—'}</span>
            {p.mycol && (
              <span aria-hidden="true" className="grid grid-cols-[repeat(11,8px)] gap-1">
                {Array.from({ length: p.mycol.of }, (_, i) => <span key={i} className={`h-2 w-2 rounded-full ${p.mycol?.listed && i === 0 ? 'bg-violet' : 'bg-range'}`} />)}
              </span>
            )}
          </ChartCard>
        </div>
      </section>
      {open && <Windows title={open.title} panes={[open]} onClose={() => setOpen(null)} />}
    </div>
  )
}
