import { AlertTriangle, Bot, Brain, CheckCircle2, ExternalLink, FileText, PlayCircle, Wrench, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { getJSON, sendJSON } from '../api'
import type { AgentRun, ScoutPick } from '../typesAgents'

// The resource scout's console (docs/PHASE2_PLAN.md A7): each step appears as the agent works,
// then the parts it chose, each with a link that opens the video at that second or the article at
// that passage. It finds and points; the person decides what to watch or read.

const POLL_MS = 800
const STEP_ICON: Record<string, [typeof Brain, string]> = {
  think: [Brain, 'text-violet-light'],
  tool: [Wrench, 'text-cyan'],
  result: [CheckCircle2, 'text-mint'],
  note: [AlertTriangle, 'text-amber-glow'],
  error: [AlertTriangle, 'text-[#ff8a8a]'],
}

function clock(seconds: number | null): string {
  if (seconds === null) return ''
  const s = Math.floor(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

function videoThumb(url: string): string | null {
  const id = url.match(/youtu\.be\/([\w-]{6,})/)?.[1] ?? url.match(/[?&]v=([\w-]{6,})/)?.[1]
  return id ? `https://i.ytimg.com/vi/${id}/mqdefault.jpg` : null
}

function PickCard({ pick }: { pick: ScoutPick }) {
  const thumb = pick.kind === 'video' ? videoThumb(pick.url) : null
  return (
    <a href={pick.url} target="_blank" rel="noopener noreferrer" className="agent-pick group flex gap-3 rounded-xl border border-[rgba(157,134,255,0.35)] bg-[rgba(255,255,255,0.04)] p-3 text-white no-underline hover:border-violet-light hover:bg-[rgba(157,134,255,0.12)]">
      {thumb ? (
        <span className="relative h-[72px] w-[128px] shrink-0 overflow-hidden rounded-lg bg-surface">
          <img src={thumb} alt="" width={128} height={72} className="h-full w-full object-cover" loading="lazy" />
          <span className="absolute bottom-1 left-1 flex items-center gap-1 rounded bg-void/80 px-1.5 py-0.5 font-mono text-[11px]"><PlayCircle size={12} />{clock(pick.start)}–{clock(pick.end)}</span>
        </span>
      ) : (
        <span className="grid h-[72px] w-[56px] shrink-0 place-items-center rounded-lg bg-surface text-cyan"><FileText size={22} /></span>
      )}
      <span className="flex min-w-0 flex-col gap-1">
        <span className="flex items-start justify-between gap-2 text-[14px] font-semibold leading-snug">{pick.title}<ExternalLink size={14} aria-hidden="true" className="mt-0.5 shrink-0 text-violet-light" /></span>
        <span className="font-mono text-[11px] text-stone">{pick.kind === 'video' ? `Opens the video at ${clock(pick.start)}` : `Opens the article at “${pick.anchor}…”`} · {pick.source}</span>
        {pick.reason && <span className="text-[13px] text-[#d9dae3]">{pick.reason}</span>}
      </span>
    </a>
  )
}

function Console({ runId }: { runId: string }) {
  const [run, setRun] = useState<AgentRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const started = useRef(Date.now())
  useEffect(() => {
    let stop = false
    const tick = async () => {
      try {
        const next = await getJSON<AgentRun>(`/api/agents/runs/${runId}`)
        if (stop) return
        setRun(next)
        if (next.status === 'running') window.setTimeout(tick, POLL_MS)
      } catch (reason) {
        if (!stop) setError(reason instanceof Error ? reason.message : String(reason))
      }
    }
    void tick()
    return () => { stop = true }
  }, [runId])
  const running = !run || run.status === 'running'
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => setNow(Date.now()), 200)
    return () => window.clearInterval(timer)
  }, [running])
  const picks = run?.result?.picks ?? []
  const seconds = ((running ? now : started.current + 0) - started.current) / 1000
  return (
    <div className="grid min-h-0 flex-1 gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
      <section aria-label="What the agent is doing" className="flex min-h-0 flex-col gap-3 rounded-xl bg-[rgba(255,255,255,0.03)] p-4">
        <span className="flex items-center justify-between font-mono text-[11px] uppercase tracking-widest text-stone">
          <span>Agent log</span>
          <span>{running ? `${seconds.toFixed(1)} s` : run?.status === 'done' ? 'finished' : run?.status}</span>
        </span>
        {error && <p role="alert" className="m-0 text-[#ff8a8a]">{error}</p>}
        <ol className="m-0 flex min-h-0 list-none flex-col gap-2 overflow-y-auto p-0" aria-live="polite">
          {(run?.steps ?? []).map((s) => {
            const [Icon, tone] = STEP_ICON[s.kind] ?? STEP_ICON.think
            return (
              <li key={s.id} className="agent-step flex items-start gap-2.5 text-[13px] leading-snug text-[#e6e7ee]">
                <Icon size={15} aria-hidden="true" className={`mt-0.5 shrink-0 ${tone}`} />
                <span>{s.text}</span>
              </li>
            )
          })}
          {running && (
            <li className="flex items-center gap-2.5 text-[13px] text-violet-light">
              <span className="agent-dots" aria-hidden="true"><span /><span /><span /></span>
              {run ? 'Thinking…' : 'Starting the agent…'}
            </li>
          )}
        </ol>
      </section>
      <section aria-label="Parts to open" className="flex min-h-0 flex-col gap-3 overflow-y-auto">
        <span className="font-mono text-[11px] uppercase tracking-widest text-stone">{running ? 'Results appear here' : picks.length ? `${picks.length} part${picks.length === 1 ? '' : 's'} chosen for you` : 'Nothing found to point to'}</span>
        {running && [0, 1, 2].map((i) => <span key={i} className="agent-skeleton h-[96px] rounded-xl" />)}
        {picks.map((p) => <PickCard key={`${p.resource_id}-${p.start ?? p.anchor}`} pick={p} />)}
        {!running && <span className="font-mono text-[11px] text-stone">{run?.result?.engine ?? run?.engine}{run?.result?.note ? ` · ${run.result.note}` : ''}. The agent chooses and explains; times, links and ranking come from code.</span>}
      </section>
    </div>
  )
}

// The full-screen agent console. It starts a run when it opens: for one video or article when
// `resourceId` is given, otherwise across every checked resource for the skill.
export function AgentRunWindow({ skill, skillName, profileId, resourceId, resourceTitle, onClose }: {
  skill: string
  skillName: string
  profileId: string | null
  resourceId?: string
  resourceTitle?: string
  onClose: () => void
}) {
  const [runId, setRunId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const startedFor = useRef<string | null>(null)
  useEffect(() => {
    const key = `${skill}|${resourceId ?? ''}`
    if (startedFor.current === key) return
    startedFor.current = key
    sendJSON<{ run_id: string }>('/api/agents/scout', { body: { skill, profile_id: profileId, resource_id: resourceId ?? null } })
      .then((out) => setRunId(out.run_id))
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)))
  }, [skill, resourceId, profileId])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
  return createPortal(
    <div role="dialog" aria-modal="true" aria-label={`Scout agent · ${skillName}`} className="fixed inset-0 z-[60] flex items-center justify-center bg-void/70 p-3 backdrop-blur-sm md:p-8" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="agent-console flex max-h-[90vh] w-full max-w-[1100px] flex-col gap-5 rounded-2xl p-5 text-white md:p-7">
        <header className="flex items-start justify-between gap-4">
          <span className="flex items-center gap-3">
            <span className="agent-avatar grid h-12 w-12 place-items-center rounded-2xl"><Bot size={24} aria-hidden="true" /></span>
            <span className="flex flex-col">
              <span className="font-mono text-[11px] uppercase tracking-widest text-violet-light">Scout agent · {skillName}</span>
              <span className="text-[20px] font-semibold leading-tight">{resourceTitle ? `Finding the parts of “${resourceTitle}” that teach it` : 'Finding the best parts of the checked videos and articles'}</span>
            </span>
          </span>
          <button type="button" onClick={onClose} aria-label="Close the agent" className="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-lg border-0 bg-surface text-white hover:bg-[#383943]"><X size={18} /></button>
        </header>
        {error && <p role="alert" className="m-0 text-[#ff8a8a]">{error}</p>}
        {runId ? <Console runId={runId} /> : !error && <span className="flex items-center gap-2.5 text-violet-light"><span className="agent-dots" aria-hidden="true"><span /><span /><span /></span>Starting the agent…</span>}
      </div>
    </div>,
    document.body,
  )
}

// A clear, always-visible way to start the agent for one resource or a whole skill.
export function AgentButton({ label, onClick, compact = false }: { label: string; onClick: () => void; compact?: boolean }) {
  return (
    <button type="button" onClick={onClick} className={`agent-button inline-flex cursor-pointer items-center gap-2 rounded-full border-0 font-semibold text-white ${compact ? 'min-h-[34px] px-3 text-[12px]' : 'min-h-[44px] px-4 text-[14px]'}`}>
      <Bot size={compact ? 14 : 16} aria-hidden="true" />
      {label}
    </button>
  )
}

export function ScoutButton({ skill, skillName, profileId }: { skill: string; skillName: string; profileId: string | null }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <AgentButton label={`Find the best parts for ${skillName}`} onClick={() => setOpen(true)} />
      {open && <AgentRunWindow skill={skill} skillName={skillName} profileId={profileId} onClose={() => setOpen(false)} />}
    </>
  )
}
