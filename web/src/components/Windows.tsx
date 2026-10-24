import { useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

export type Pane = { key: string; title: string; hint?: string; body: ReactNode }

// Temporary windows over the page: each can be closed on its own; closing the last one (or
// "Close all", Esc, or a click on the backdrop) returns to the page. Nothing is saved by closing.
// Rendered into <body> so no page section's own stacking layer can draw over the windows.
export function Windows({ title, panes, onClose }: { title: string; panes: Pane[]; onClose: () => void }) {
  const [closed, setClosed] = useState<string[]>([])
  const first = useRef<HTMLButtonElement>(null)
  const dialog = useRef<HTMLDivElement>(null)
  const open = panes.filter((p) => !closed.includes(p.key))
  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
    first.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); onClose(); return }
      if (e.key !== 'Tab') return
      const stops = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), [tabindex="0"]') ?? []).filter((el) => el.getClientRects().length > 0)
      const edge = e.shiftKey ? stops[0] : stops.at(-1)
      if (document.activeElement === edge) { e.preventDefault(); (e.shiftKey ? stops.at(-1) : stops[0])?.focus() }
    }
    window.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      trigger?.focus()
    }
  }, [onClose])
  useEffect(() => {
    if (open.length === 0) onClose()
  }, [open.length, onClose])
  return createPortal(
    <div ref={dialog} role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-50 flex flex-col bg-void/55 p-3 backdrop-blur-[2px] md:p-8" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-3 pb-3 text-white">
        <h2 className="m-0 min-w-0 text-lg font-semibold leading-snug tracking-tight">{title}</h2>
        <button ref={first} type="button" className="btn min-h-[40px] shrink-0" onClick={onClose}>Close all</button>
      </div>
      <div className={`mx-auto grid min-h-0 w-full max-w-[1200px] flex-1 content-start items-start gap-3 overflow-y-auto ${open.length >= 3 ? 'md:grid-cols-3' : open.length === 2 ? 'md:grid-cols-2' : 'md:max-w-[640px]'}`}>
        {open.map((p) => (
          <section key={p.key} aria-label={p.title} className="flex max-h-[78vh] min-h-0 flex-col border border-line bg-paper motion-safe:animate-[pop_160ms_ease-out]">
            <header className="flex items-start justify-between gap-2 border-b border-line px-4 py-3">
              <div className="min-w-0">
                <h3 className="m-0 text-[15px] font-semibold">{p.title}</h3>
                {p.hint && <span className="block text-[11px] text-graphite">{p.hint}</span>}
              </div>
              <button type="button" aria-label={`Close ${p.title}`} className="grid h-11 w-11 shrink-0 cursor-pointer place-items-center rounded border border-line bg-paper text-graphite hover:bg-fog" onClick={() => { first.current?.focus(); setClosed((c) => [...c, p.key]) }}>
                ×
              </button>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 text-[13px]">{p.body}</div>
          </section>
        ))}
      </div>
    </div>,
    document.body,
  )
}
