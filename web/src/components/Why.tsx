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
      <button type="button" className="q-btn q-why" onClick={() => setOpen(true)} aria-label={`${label} ${title}`}>
        <Info size={15} aria-hidden="true" />
        {label}
      </button>
      {open && <Windows title={title} panes={panes} onClose={() => setOpen(false)} />}
    </>
  )
}

export type Kind = 'observed' | 'assumption' | 'estimate'

// The same pill as atoms.tsx Label, so every page labels numbers alike.
export function KindLabel({ kind }: { kind: Kind }) {
  return <span className={`q-label q-label-${kind}`}>{kind}</span>
}
