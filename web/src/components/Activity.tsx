import { useEffect, useState } from 'react'

export type Stage = { name: string; engine: string; outcome: string; seconds: number }

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
