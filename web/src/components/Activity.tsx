import { useEffect, useState } from 'react'

export type Stage = { name: string; engine: string; outcome: string; seconds: number }

export type LogLine = { label: string; status: 'running' | 'done' | 'failed'; startedAt: number; detail?: string; seconds?: number }

const SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

// Terminal-style log of real work: a line appears when its request starts and ticks off when it
// returns, with the time it took and what it found. `total` is the number of planned requests, so
// the bar only counts requests that actually finished.
export function RunLog({ lines, total, title }: { lines: LogLine[]; total: number; title: string }) {
  const running = lines.some((l) => l.status === 'running')
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => setNow(Date.now()), 120)
    return () => window.clearInterval(timer)
  }, [running])
  const done = lines.filter((l) => l.status === 'done').length
  const frame = SPINNER[Math.floor(now / 120) % SPINNER.length]
  return (
    <section aria-label={title} className="border border-obsidian bg-void font-mono text-[13px] text-white">
      <div className="flex items-center justify-between gap-3 border-b border-surface px-4 py-2.5 text-[11px] tracking-widest text-stone">
        <span>{title.toUpperCase()}</span>
        <span>{done}/{total} DONE</span>
      </div>
      <div className="h-[3px] bg-surface" aria-hidden="true">
        <div className="h-full bg-cyan transition-[width] duration-300" style={{ width: `${(100 * done) / total}%` }} />
      </div>
      <ol className="m-0 flex list-none flex-col gap-3 px-4 py-4" aria-live="polite">
        {lines.map((line, i) => {
          const seconds = line.seconds ?? (now - line.startedAt) / 1000
          return (
            <li key={`${line.label}-${i}`} className="grid grid-cols-[18px_minmax(0,1fr)_auto] gap-x-2">
              <span aria-hidden="true" className={line.status === 'failed' ? 'text-weak' : 'text-cyan'}>
                {line.status === 'done' ? '✓' : line.status === 'failed' ? '✗' : <><span className="motion-reduce:hidden">{frame}</span><span className="hidden motion-reduce:inline">…</span></>}
              </span>
              <span className={line.status === 'running' ? 'text-white' : 'text-[#e6e6ea]'}>
                {line.label}
                <span className="sr-only"> · {line.status}</span>
              </span>
              <span className="text-right text-stone">{seconds.toFixed(1)} s</span>
              {line.detail && <span className={`col-start-2 col-end-4 text-xs ${line.status === 'failed' ? 'text-weak' : 'text-stone'}`}>{line.detail}</span>}
            </li>
          )
        })}
        {running && <li aria-hidden="true" className="text-stone motion-safe:animate-pulse">▍</li>}
      </ol>
    </section>
  )
}

// A long action (reading a CV, matching tasks) as the same terminal-style log: while it runs,
// one live line with the elapsed time; afterwards, each stage the server measured, plus a result
// line built from what came back. Nothing is shown as done before the server says so.
export function ProcessLog({ title, running, label, stages, result }: { title: string; running: boolean; label: string; stages?: Stage[]; result?: string }) {
  const [startedAt, setStartedAt] = useState(() => Date.now())
  useEffect(() => {
    if (running) setStartedAt(Date.now())
  }, [running])
  if (running) return <RunLog title={title} total={1} lines={[{ label, status: 'running', startedAt }]} />
  if (!stages || stages.length === 0) return null
  const lines: LogLine[] = stages.map((s) => ({
    label: s.name,
    status: 'done',
    startedAt,
    seconds: s.seconds,
    detail: `${s.engine}${s.outcome !== 'ok' ? ` · ${s.outcome}, fallback used` : ''}`,
  }))
  if (result) lines.push({ label: 'Result', status: 'done', startedAt, seconds: 0, detail: result })
  return <RunLog title={title} total={lines.length} lines={lines} />
}

// Status of a long action: while it runs, what it is doing and for how long (no fake progress
// bar, the work has no known length); afterwards, the stages the server measured.
export function Activity({ running, label, stages, dark = false }: { running: boolean; label: string; stages?: Stage[]; dark?: boolean }) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!running) return
    const started = Date.now()
    setElapsed(0)
    const timer = window.setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000)
    return () => window.clearInterval(timer)
  }, [running])
  const tone = dark ? 'text-stone' : 'text-graphite'
  if (running) {
    return (
      <p role="status" className={`m-0 flex items-center gap-2 text-[13px] ${tone}`}>
        <span aria-hidden="true" className="inline-block h-2 w-2 rounded-full bg-violet motion-safe:animate-pulse" />
        {label} · {elapsed} s
      </p>
    )
  }
  if (!stages || stages.length === 0) return null
  const total = stages.reduce((sum, s) => sum + s.seconds, 0)
  return (
    <details className={`text-xs ${tone}`}>
      <summary className="cursor-pointer">What happened · {stages.length} step{stages.length === 1 ? '' : 's'}, {total.toFixed(1)} s</summary>
      <ol className="m-0 mt-1 space-y-0.5 pl-4">
        {stages.map((s, i) => (
          <li key={`${s.name}-${i}`}>
            {s.name}{s.engine ? ` · ${s.engine}` : ''} · {s.seconds.toFixed(1)} s{s.outcome !== 'ok' && <span className="text-weak"> · {s.outcome}, fallback used</span>}
          </li>
        ))}
      </ol>
    </details>
  )
}
