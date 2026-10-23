import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { Signal } from '../types'
import { DirectionTag, KindTag } from './ui'

const MAX_ROWS = 8

export function EvidenceDrawer({ signal, onClose }: { signal: Signal; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <aside
      aria-label="Evidence"
      className="fixed inset-y-0 right-0 z-10 flex w-full max-w-[420px] flex-col gap-4 overflow-y-auto bg-white p-6 shadow-[rgba(0,0,0,0.06)_0_0_0_1px,rgba(47,48,55,0.2)_-15px_0_35px_-5px]"
    >
      <div className="flex items-center justify-between">
        <span className="eyebrow text-observed">Evidence</span>
        <button ref={closeRef} type="button" onClick={onClose} aria-label="Close evidence" className="rounded-md p-2 hover:bg-mist">
          <X size={16} aria-hidden="true" />
        </button>
      </div>
      <h3 className="m-0 text-xl font-semibold leading-tight tracking-tight">{signal.title}</h3>
      <div className="flex flex-wrap gap-1.5">
        <KindTag kind={signal.kind} />
        <DirectionTag direction={signal.direction} />
      </div>
      <p className="m-0 font-mono text-[13px]">{signal.headline}</p>
      <p className="m-0 text-[13px] text-graphite">{signal.note}</p>

      <div className="card-dark flex flex-col gap-2 rounded-lg p-4">
        <span className="font-mono text-[11px] tracking-widest text-cyan">CITED ROWS</span>
        {signal.evidence.slice(0, MAX_ROWS).map((row) => (
          <p key={`${row.period}-${row.cited_span}`} className="m-0 font-mono text-xs leading-relaxed text-white">
            {row.cited_span}
            <span className="block text-slate-mid">
              {row.published ? `published ${row.published} · ` : ''}fetched {row.fetched}
            </span>
          </p>
        ))}
        {signal.evidence.length > MAX_ROWS && (
          <span className="font-mono text-[11px] text-stone">+{signal.evidence.length - MAX_ROWS} more rows</span>
        )}
      </div>

      {signal.sources.map((source) => (
        <dl key={source.id} className="m-0 grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-2 text-[13px]">
          <dt className="cap pt-px">Source</dt>
          <dd className="m-0">{source.name}</dd>
          <dt className="cap pt-px">Publisher</dt>
          <dd className="m-0">{source.publisher}</dd>
          <dt className="cap pt-px">Shows</dt>
          <dd className="m-0">{source.shows}</dd>
          <dt className="cap pt-px">Doesn't show</dt>
          <dd className="m-0">{source.does_not_show}</dd>
          <dt className="cap pt-px">Terms</dt>
          <dd className="m-0">{source.terms}</dd>
        </dl>
      ))}
      {signal.evidence[0] && (
        <a className="btn mt-auto self-start" href={signal.evidence[0].url} target="_blank" rel="noopener noreferrer">
          Open the source ↗
        </a>
      )}
    </aside>
  )
}
