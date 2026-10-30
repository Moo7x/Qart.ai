import { Bot, ExternalLink } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getJSON, sendJSON } from '../api'
import type { AgentRun } from '../typesAgents'
import { Windows } from './Windows'

// The resource scout's window (docs/PHASE2_PLAN.md A7): each step appears as the agent works,
// then the parts it chose, each with a link that opens the video at that second or the article at
// that passage. It finds and points; the person decides what to watch or read.

const POLL_MS = 800
const STEP_MARK: Record<string, string> = { think: '…', tool: '→', result: '✓', note: '!', error: '✕' }

function clock(seconds: number | null): string {
  if (seconds === null) return ''
  const s = Math.floor(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

function RunView({ runId }: { runId: string }) {
  const [run, setRun] = useState<AgentRun | null>(null)
  const [error, setError] = useState<string | null>(null)
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
  if (error) return <p role="alert" className="m-0 text-weak">{error}</p>
  if (!run) return <span role="status" className="cap">Starting the scout…</span>
  const picks = run.result?.picks ?? []
  return (
    <div className="flex flex-col gap-3">
      <ol className="m-0 flex list-none flex-col gap-1.5 p-0 font-mono text-[12px]" aria-live="polite">
        {run.steps.map((s) => (
          <li key={s.id} className={`flex gap-2 ${s.kind === 'error' || s.kind === 'note' ? 'text-weak' : 'text-graphite'}`}>
            <span aria-hidden="true" className="w-3 shrink-0">{STEP_MARK[s.kind] ?? '·'}</span>
            <span>{s.text}</span>
          </li>
        ))}
        {run.status === 'running' && <li className="flex gap-2 text-violet"><span className="w-3 motion-safe:animate-pulse">●</span><span>Working…</span></li>}
      </ol>
      {run.status !== 'running' && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <span className="cap">{picks.length > 0 ? `${picks.length} part${picks.length === 1 ? '' : 's'} to open` : 'Nothing found to point to'}</span>
          {picks.map((p) => (
            <a key={`${p.resource_id}-${p.start ?? p.anchor}`} href={p.url} target="_blank" rel="noopener noreferrer" className="card-light flex flex-col gap-1 p-3 text-void no-underline hover:bg-fog">
              <span className="flex items-center justify-between gap-2 text-[13px] font-semibold">
                {p.title}
                <ExternalLink size={14} aria-hidden="true" className="shrink-0 text-violet" />
              </span>
              <span className="font-mono text-[11px] text-graphite">
                {p.kind === 'video' ? `Video · ${clock(p.start)}–${clock(p.end)}` : `Article · opens at “${p.anchor}…”`} · {p.source}
              </span>
              {p.reason && <span className="text-[13px]">{p.reason}</span>}
            </a>
          ))}
          <span className="font-mono text-[11px] text-ash">{run.result?.engine ?? run.engine}{run.result?.note ? ` · ${run.result.note}` : ''}. The agent chooses and describes; times, links and ranking come from code.</span>
        </div>
      )}
    </div>
  )
}

export function ScoutButton({ skill, skillName, profileId }: { skill: string; skillName: string; profileId: string | null }) {
  const [runId, setRunId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  async function start() {
    setError(null)
    try {
      const out = await sendJSON<{ run_id: string }>('/api/agents/scout', { body: { skill, profile_id: profileId } })
      setRunId(out.run_id)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    }
  }
  return (
    <>
      <button type="button" className="btn min-h-[44px] gap-1.5" onClick={start}>
        <Bot size={15} aria-hidden="true" />
        Find the best parts for {skillName}
      </button>
      {error && <span role="alert" className="text-[12px] text-weak">{error}</span>}
      {runId && (
        <Windows
          title={`Scout · ${skillName}`}
          panes={[{ key: 'run', title: 'What the agent is doing', hint: 'Checked videos and articles only', body: <RunView runId={runId} /> }]}
          onClose={() => setRunId(null)}
        />
      )}
    </>
  )
}
