import type { ReactNode } from 'react'
import type { Direction } from '../types'

export const DIRECTION_LABEL: Record<Direction, string> = {
  rising: 'Rising',
  weakening: 'Weakening',
  stable: 'Stable',
  insufficient: 'Not enough evidence yet',
  expert: 'Expert view',
}

const DIRECTION_STYLE: Record<Direction, string> = {
  rising: 'bg-rising-bg text-rising',
  weakening: 'bg-weak-bg text-weak',
  stable: 'bg-mist text-graphite',
  insufficient: 'bg-mist text-graphite border border-dashed border-stone',
  expert: 'bg-observed-bg text-observed',
}

export function DirectionTag({ direction }: { direction: Direction }) {
  return <span className={`tag ${DIRECTION_STYLE[direction]}`}>{DIRECTION_LABEL[direction]}</span>
}

export function KindTag({ kind }: { kind: 'observed' | 'expert' }) {
  return (
    <span className="tag bg-observed-bg text-observed">
      {kind === 'observed' ? 'Observed · source + date' : 'Expert assessment'}
    </span>
  )
}

export function Loading({ what }: { what: string }) {
  return (
    <div role="status" className="cap px-4 py-6">
      Loading {what}…
    </div>
  )
}

export function Problem({ what, message, onRetry }: { what: string; message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 px-4 py-4 text-sm">
      <span>
        Could not load {what}: {message}
      </span>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="px-4 py-6 text-sm text-graphite">{children}</div>
}
