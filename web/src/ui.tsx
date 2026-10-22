/** Shared building blocks for the qart-design-system skill, so every screen uses one look. */
import type { ReactNode } from 'react'
import { BadgeCheck, CircleDashed, LifeBuoy, MessageSquareQuote, type LucideIcon } from 'lucide-react'
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

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`bg-surface border border-hairline rounded-lg ${className}`}>{children}</div>
}

export function PageHeader({ title, intro, aside }: { title: string; intro?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[32px] leading-[1.15] font-semibold tracking-[-0.02em] text-ink">{title}</h1>
        {intro && <p className="mt-2 font-serif text-lg leading-[1.56] text-graphite max-w-2xl">{intro}</p>}
      </div>
      {aside && <div className="flex items-center gap-2">{aside}</div>}
    </header>
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
