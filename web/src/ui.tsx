/** Shared building blocks for the qart-design-system skill, so every screen uses one look. */
import { useEffect, useLayoutEffect, useRef, type HTMLAttributes, type ReactNode } from 'react'
import { BadgeCheck, CircleDashed, LifeBuoy, MessageSquareQuote, X, type LucideIcon } from 'lucide-react'
import { DURATION, EASE, gsap, reducedMotion } from './motion'
import type { SkillStateName } from './types'

/** Class recipes from the skill's component table. */
export const btn = {
  primary: 'inline-flex items-center justify-center gap-2 bg-action hover:bg-action-hover text-white text-sm font-medium rounded-md px-4 py-2 transition-colors duration-200 disabled:opacity-50',
  ghost: 'inline-flex items-center justify-center gap-2 bg-action-tint text-action-ink text-sm font-medium rounded-md px-4 py-2 hover:bg-[#d6eafd] transition-colors duration-200 disabled:opacity-50',
  text: 'inline-flex items-center justify-center gap-2 text-ink/90 text-sm font-medium rounded-md px-4 py-2 hover:bg-linen transition-colors duration-200 disabled:opacity-50',
  outline: 'inline-flex items-center justify-center gap-2 bg-surface border border-hairline-strong text-ink text-sm font-medium rounded-md px-4 py-2 hover:bg-linen transition-colors duration-200 disabled:opacity-50',
}

export const input =
  'bg-surface border border-hairline-strong rounded-sm px-3 py-2 text-sm text-ink placeholder:text-stone focus:outline-none focus:ring-2 focus:ring-action/40'

/** Section label inside a card (small, quiet). */
export const label = 'text-xs font-medium text-graphite'

export type Tone = 'action' | 'marigold' | 'coral' | 'mocha' | 'linen' | 'outline'

const TONE_CLASSES: Record<Tone, string> = {
  action: 'bg-action-tint text-action-ink',
  marigold: 'bg-marigold-tint text-marigold-ink',
  coral: 'bg-coral-tint text-coral-ink',
  mocha: 'bg-mocha-tint text-mocha-ink',
  linen: 'bg-linen text-graphite',
  outline: 'border border-dashed border-hairline-strong text-graphite',
}

export function Tag({ tone = 'linen', icon: Icon, children, title }: { tone?: Tone; icon?: LucideIcon; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${TONE_CLASSES[tone]}`}>
      {Icon && <Icon size={12} strokeWidth={2} aria-hidden="true" />}
      {children}
    </span>
  )
}

/** Evidence states: the only way skill progress is shown (never a percentage). */
export const STATE_META: Record<SkillStateName, { label: string; tone: Tone; icon: LucideIcon }> = {
  demonstrated_independently: { label: 'Shown on your own', tone: 'action', icon: BadgeCheck },
  observed_with_help: { label: 'Shown with help', tone: 'marigold', icon: LifeBuoy },
  self_reported: { label: 'You said so', tone: 'linen', icon: MessageSquareQuote },
  insufficient_evidence: { label: 'Not enough evidence yet', tone: 'outline', icon: CircleDashed },
}

export function StatePill({ state }: { state: SkillStateName }) {
  const m = STATE_META[state]
  return <Tag tone={m.tone} icon={m.icon}>{m.label}</Tag>
}

/** Every number shown carries where it comes from (AGENTS.md labelling rule). */
export type Provenance = 'evidence' | 'assumption' | 'synthetic'

const PROVENANCE_TONE: Record<Provenance, Tone> = { evidence: 'mocha', assumption: 'coral', synthetic: 'linen' }
const PROVENANCE_LABEL: Record<Provenance, string> = { evidence: 'Source', assumption: 'Assumption', synthetic: 'Synthetic' }

export function ProvenanceTag({ kind, children }: { kind: Provenance; children?: ReactNode }) {
  return (
    <Tag tone={PROVENANCE_TONE[kind]}>
      {PROVENANCE_LABEL[kind]}{children ? <> · {children}</> : null}
    </Tag>
  )
}

export function asProvenance(kind: string | undefined): Provenance {
  return kind === 'assumption' || kind === 'synthetic' ? kind : 'evidence'
}

export function Card({ children, className = '', ...rest }: { children: ReactNode; className?: string } & HTMLAttributes<HTMLDivElement> & { 'data-reveal'?: boolean }) {
  return <div {...rest} className={`bg-surface border border-hairline rounded-lg ${className}`}>{children}</div>
}

/** Notion's hero highlight pill: an accent fill behind one key word of a headline. */
export function Highlight({ children, tone = 'marigold' }: { children: ReactNode; tone?: 'marigold' | 'action' | 'coral' }) {
  const fill = { marigold: 'bg-marigold-tint', action: 'bg-action-tint', coral: 'bg-coral-tint' }[tone]
  return <span className={`${fill} rounded-full px-3 -mx-0.5 box-decoration-clone`}>{children}</span>
}

export function PageHeader({ title, intro, aside }: { title: ReactNode; intro?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[32px] sm:text-[40px] leading-[1.15] font-semibold tracking-[-0.025em] text-ink">{title}</h1>
        {intro && <p className="mt-3 font-serif text-lg leading-[1.56] text-graphite max-w-2xl">{intro}</p>}
      </div>
      {aside && <div className="flex items-center gap-2">{aside}</div>}
    </header>
  )
}

const TILE_CLASSES: Record<Tone, string> = {
  action: 'bg-action-tint text-action-ink',
  marigold: 'bg-marigold-tint text-marigold-ink',
  coral: 'bg-coral-tint text-coral-ink',
  mocha: 'bg-mocha-tint text-mocha-ink',
  linen: 'bg-linen text-graphite',
  outline: 'bg-surface border border-dashed border-hairline-strong text-graphite',
}

/** Colour-filled count tile. Counts only: never a percentage or a score. */
export function StatTile({ value, label: text, tone, icon: Icon }: { value: ReactNode; label: string; tone: Tone; icon?: LucideIcon }) {
  return (
    <div className={`rounded-lg p-4 sm:p-5 ${TILE_CLASSES[tone]}`}>
      <div className="flex items-center gap-1.5 text-xs font-medium">
        {Icon && <Icon size={14} strokeWidth={2} aria-hidden="true" />}
        {text}
      </div>
      <div className="mt-2 text-[32px] leading-none font-semibold tracking-[-0.02em] tabular-nums text-ink">{value}</div>
    </div>
  )
}

/** The one dark card per screen: the single most useful next step. */
export function NextStepCard({ eyebrow, title, children, action }: { eyebrow: string; title: ReactNode; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="bg-midnight text-white rounded-lg p-6 flex flex-col sm:flex-row sm:items-center gap-4">
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-white/70">{eyebrow}</div>
        <div className="mt-1 text-[22px] leading-[1.27] font-semibold tracking-[-0.01em]">{title}</div>
        {children && <div className="mt-1 text-sm text-white/80">{children}</div>}
      </div>
      {action}
    </div>
  )
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'

/** Right-side slide-over. Esc closes it, focus stays inside, and returns to the opener on close. */
export function Drawer({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode }) {
  const panelRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  // Slide in with GSAP; closing is instant so focus returns to the opener without waiting.
  useLayoutEffect(() => {
    if (!open || reducedMotion()) return
    const tl = gsap.timeline()
    tl.from(overlayRef.current, { opacity: 0, duration: DURATION, ease: EASE })
      .from(panelRef.current, { x: 24, opacity: 0, duration: DURATION, ease: EASE, clearProps: 'transform,opacity' }, 0)
    return () => { tl.kill() }
  }, [open])

  useEffect(() => {
    if (!open) return
    const opener = document.activeElement as HTMLElement | null
    panelRef.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key !== 'Tab' || !panelRef.current) return
      const items = [...panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)]
      if (items.length === 0) return
      const first = items[0], last = items[items.length - 1]
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); opener?.focus() }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50">
      <div ref={overlayRef} className="absolute inset-0 bg-ink/20" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef} role="dialog" aria-modal="true" aria-label={typeof title === 'string' ? title : 'Details'}
        className="absolute right-0 top-0 h-full w-full max-w-md bg-surface shadow-pop flex flex-col"
      >
        <div className="flex items-center justify-between gap-3 px-5 h-16 border-b border-hairline">
          <div className="font-semibold text-ink min-w-0 truncate">{title}</div>
          <button onClick={onClose} aria-label="Close" className="text-graphite hover:text-ink rounded-sm p-1"><X size={20} /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  )
}

export function SectionTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
      <h2 className="text-[22px] leading-[1.27] font-semibold tracking-[-0.01em] text-ink">{children}</h2>
      {aside}
    </div>
  )
}

export function Loading({ what }: { what: string }) {
  return <p className="py-16 text-center text-sm text-graphite" role="status">Loading {what}…</p>
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card className="p-8 text-center">
      <p className="font-medium text-ink">{title}</p>
      {children && <p className="mt-1 text-sm text-graphite">{children}</p>}
    </Card>
  )
}
