import { Info } from 'lucide-react'
import { useState } from 'react'
import { Windows, type Pane } from './Windows'

// The one "Why?" control (docs/PHASE2_PLAN.md §5): a large button next to the number it explains,
// opening the shared Windows panel with what the number is, its kind, how it is computed and its
// source and date.
export function WhyButton({ title, panes, label = 'Why?' }: { title: string; panes: Pane[]; label?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" className="btn min-h-[44px] gap-1.5" onClick={() => setOpen(true)} aria-label={`${label} ${title}`}>
        <Info size={15} aria-hidden="true" />
        {label}
      </button>
      {open && <Windows title={title} panes={panes} onClose={() => setOpen(false)} />}
    </>
  )
}

export type Kind = 'observed' | 'assumption' | 'estimate'

const KIND_STYLE: Record<Kind, string> = {
  observed: 'bg-observed-bg text-observed',
  assumption: 'bg-mist text-graphite',
  estimate: 'bg-estimate-bg text-estimate',
}

export function KindLabel({ kind }: { kind: Kind }) {
  return <span className={`tag ${KIND_STYLE[kind]}`}>{kind[0].toUpperCase() + kind.slice(1)}</span>
}
