import { Link, useLocation } from 'react-router-dom'
import { Check } from 'lucide-react'

/** The six-screen reskilling flow (design/qart-flow), in order. */
export const FLOW_STEPS = [
  { to: '/start', label: 'Profile' },
  { to: '/signals', label: 'Signals' },
  { to: '/future', label: 'Matches' },
  { to: '/pathway', label: 'Pathway' },
  { to: '/impact', label: 'SDG impact' },
  { to: '/scenarios', label: 'Scenarios' },
] as const

/** Flow routes after the intake; the "My future" nav item stays highlighted on all of them. */
export const FUTURE_FLOW_PATHS = FLOW_STEPS.slice(1).map(s => s.to)

/** Step bar shown at the top of each flow screen. Earlier steps show a tick (they are behind you). */
export default function FlowSteps() {
  const { pathname } = useLocation()
  const current = FLOW_STEPS.findIndex(s => pathname.startsWith(s.to))
  return (
    <nav aria-label="Reskilling steps" className="mb-8 -mx-4 px-4 overflow-x-auto">
      <ol className="flex gap-1.5 min-w-max">
        {FLOW_STEPS.map((step, i) => {
          const isCurrent = i === current
          const done = current > -1 && i < current
          return (
            <li key={step.to}>
              <Link
                to={step.to}
                aria-current={isCurrent ? 'step' : undefined}
                className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm whitespace-nowrap transition-colors duration-200 ${
                  isCurrent ? 'bg-action text-white font-medium'
                    : done ? 'bg-action-tint text-action-ink hover:bg-[#d6eafd]'
                      : 'bg-linen text-graphite hover:text-ink'
                }`}
              >
                {done ? <Check size={14} strokeWidth={2.5} aria-hidden="true" /> : <span className="tabular-nums">{i + 1}</span>}
                {step.label}
              </Link>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
