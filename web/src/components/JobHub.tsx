import { Bot, Building2, Cpu, ShieldAlert } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../api'
import type { OccupationPreview } from '../types'
import { Loading, Problem } from './ui'
import { Windows, type Pane } from './Windows'

// "What is changing in your current job" as one picture: the job in the centre and the four
// kinds of evidence around it, each with one number and one line. Every detail, source and caveat
// is one click away, so the page shows what matters without a wall of text.

type Kind = 'observed' | 'estimate' | 'expert'
const KIND: Record<Kind, [string, string]> = {
  observed: ['Observed', 'bg-observed-bg text-observed'],
  estimate: ['Estimate', 'bg-estimate-bg text-estimate'],
  expert: ['Expert view', 'bg-mist text-graphite'],
}

type Spoke = { key: string; icon: ReactNode; kind: Kind; title: string; big: string; line: string; detail: Pane }

function SpokeCard({ spoke, onOpen, corner }: { spoke: Spoke; onOpen: () => void; corner: string }) {
  return (
    <button type="button" onClick={onOpen} className={`job-spoke ${corner} group flex cursor-pointer flex-col gap-1.5 rounded-xl border border-line bg-paper p-4 text-left shadow-[0_6px_20px_rgba(19,19,22,0.06)] transition-transform hover:-translate-y-0.5 hover:border-violet`}>
      <span className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-[13px] font-semibold"><span className="grid h-7 w-7 place-items-center rounded-lg bg-violet-soft text-violet">{spoke.icon}</span>{spoke.title}</span>
        <span className={`tag ${KIND[spoke.kind][1]}`}>{KIND[spoke.kind][0]}</span>
      </span>
      <span className="font-mono text-[28px] leading-none tracking-tight">{spoke.big}</span>
      <span className="text-[13px] text-graphite">{spoke.line}</span>
      <span className="text-[12px] font-medium text-violet opacity-0 transition-opacity group-hover:opacity-100">Details and source →</span>
    </button>
  )
}

export function JobHub({ soc, title, impact, page, routes }: { soc: string; title: string; impact: string; page: number; routes: number }) {
  const view = useApi<OccupationPreview>(`/api/occupations/${soc}`)
  const [open, setOpen] = useState<Pane | null>(null)
  if (view.loading) return <Loading what="the evidence for your job" />
  if (view.error) return <Problem what="the evidence for your job" message={view.error} onRetry={view.reload} />
  const p = view.data
  if (!p) return null
  const spokes: Spoke[] = [
    {
      key: 'use',
      icon: <Bot size={15} />,
      kind: 'observed',
      title: 'AI use today',
      big: p.ai_use?.automation !== null && p.ai_use?.automation !== undefined ? `${Math.round(p.ai_use.automation)}%` : '—',
      line: p.ai_use ? 'of AI use on this job is AI doing the task, not helping a person' : 'Not published for this occupation',
      detail: {
        key: 'use', title: 'AI use today', hint: `Anthropic Economic Index · ${p.ai_use?.period ?? ''}`,
        body: p.ai_use ? <p className="m-0">{p.ai_use.share}% of sampled Claude conversations worldwide{p.ai_use.share_local !== null ? ` and ${p.ai_use.share_local}% in Malaysia` : ''} are about this occupation ({p.ai_use.period}). {p.ai_use.automation}% of that use is automation-style; the rest is people working with AI. It shows use of an AI assistant, not job losses.</p> : <p className="m-0">Not published for this occupation (missing, not zero).</p>,
      },
    },
    {
      key: 'exposure',
      icon: <Cpu size={15} />,
      kind: 'estimate',
      title: 'Could AI do these tasks?',
      big: p.exposure?.mean !== null && p.exposure?.mean !== undefined ? `${Math.round(100 * p.exposure.mean)} / 100` : '—',
      line: p.exposure ? `ILO task score · ${p.exposure.gradient ?? 'no gradient'}` : 'No exposure score for this group',
      detail: {
        key: 'exposure', title: 'Could AI do these tasks?', hint: 'ILO Working Paper 140 (2025)',
        body: p.exposure ? <p className="m-0">The ILO rates {p.exposure.title} (ISCO-08 {p.exposure.isco}) {p.exposure.gradient}, mean task score {p.exposure.mean} of 1. This is technical potential, not adoption. Linked through ESCO &ldquo;{p.esco.title}&rdquo; ({p.esco.match}).</p> : <p className="m-0">{p.isco_note || 'No exposure score for this group.'}</p>,
      },
    },
    {
      key: 'jobs',
      icon: <Building2 size={15} />,
      kind: 'observed',
      title: 'Jobs like it in Malaysia',
      big: p.employment?.points.at(-1) ? `${p.employment.points.at(-1)?.value.toFixed(1)}%` : '—',
      line: p.employment ? `of employees work in its group (${p.employment.points.at(-1)?.period}); ${p.employment.direction === 'stable' ? 'stable since 2016' : p.employment.direction}` : 'No Malaysian series linked',
      detail: {
        key: 'jobs', title: 'Jobs like it in Malaysia', hint: 'DOSM via OpenDOSM',
        body: p.employment ? <p className="m-0">{p.employment.title}: {p.employment.headline}. This is the whole major group, not this occupation alone. {p.employment.note}</p> : <p className="m-0">No Malaysian group series linked yet.</p>,
      },
    },
    {
      key: 'critical',
      icon: <ShieldAlert size={15} />,
      kind: 'expert',
      title: 'Hard-to-fill list',
      big: p.mycol ? (p.mycol.listed ? 'Listed' : 'Not listed') : '—',
      line: 'MyCOL 2024/2025 critical occupations',
      detail: {
        key: 'critical', title: 'Hard-to-fill list', hint: 'MyCOL 2024/2025 (TalentCorp, Ministry of Human Resources)',
        body: <p className="m-0">{p.mycol ? (p.mycol.listed ? `MyCOL lists ${p.mycol.name} as critical (hard to fill) in Malaysia.` : `Not among the ${p.mycol.of} occupations MyCOL lists as critical.`) : 'Needs the ISCO-08 link to check.'}</p>,
      },
    },
  ]
  const centre: Pane = {
    key: 'job', title: p.title, hint: `${p.soc} · O*NET 31.0`,
    body: (
      <div className="flex flex-col gap-2">
        <p className="m-0">{p.description}</p>
        {p.tasks.length > 0 && <><span className="cap">Most important tasks (O*NET)</span><ol className="m-0 flex flex-col gap-1 pl-5">{p.tasks.map((t) => <li key={t.task}>{t.text}</li>)}</ol></>}
      </div>
    ),
  }
  const corners = ['job-tl', 'job-tr', 'job-bl', 'job-br']
  return (
    <div className="job-hub">
      <svg className="job-hub-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {[[20, 22], [80, 22], [20, 78], [80, 78]].map(([x, y]) => <line key={`${x}-${y}`} x1="50" y1="50" x2={x} y2={y} className="job-hub-line" />)}
      </svg>
      {spokes.map((s, i) => <SpokeCard key={s.key} spoke={s} corner={corners[i]} onOpen={() => setOpen(s.detail)} />)}
      <button type="button" onClick={() => setOpen(centre)} className="job-centre flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-violet bg-void p-5 text-center text-white shadow-[0_12px_40px_rgba(108,71,255,0.35)]">
        <span className="font-mono text-[11px] uppercase tracking-widest text-violet-light">Your job today</span>
        <span className="text-[20px] font-semibold leading-tight">{title}</span>
        <span className={`tag ${impact === 'high' ? 'bg-weak text-white' : 'bg-surface text-white'}`}>TalentCorp: {impact} impact · p. {page}</span>
        <Link to="/roles" onClick={(e) => e.stopPropagation()} className="text-[13px] font-medium text-violet-light">{routes} routes out in GBS →</Link>
      </button>
      {open && <Windows title={open.title} panes={[open]} onClose={() => setOpen(null)} />}
    </div>
  )
}
