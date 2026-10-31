import { Link } from 'react-router-dom'
import { useT } from '../i18n'

export type FlowStep = 'cv' | 'work' | 'roles' | 'time' | 'plan'

const STEPS: { id: FlowStep; text: string; to: string }[] = [
  { id: 'cv', text: 'Your CV', to: '/start?edit=1' },
  { id: 'work', text: 'Your work today', to: '/work' },
  { id: 'roles', text: 'Roles that fit you next', to: '/roles' },
  { id: 'time', text: 'Time and budget', to: '/time' },
  { id: 'plan', text: 'Your plan', to: '/pathway' },
]

/** The five steps from a CV to a plan (design-prototype/ pages.py flow_steps). */
export function FlowSteps({ current, skip = [] }: { current: FlowStep; skip?: FlowStep[] }) {
  const { t } = useT()
  const steps = STEPS.filter((s) => !skip.includes(s.id))
  const at = steps.findIndex((s) => s.id === current)
  return (
    <nav aria-label="Steps to your plan">
      <ol className="q-steps">
        {steps.map((s, i) => (
          <li key={s.id} className="flex-none">
            <Link to={s.to} aria-current={i === at ? 'step' : undefined}>
              <span className="q-step-dot" data-on={i <= at} aria-hidden="true">{i < at ? '✓' : i + 1}</span>
              {t(s.text)}
              {i < at && <span className="sr-only"> (done)</span>}
            </Link>
          </li>
        ))}
      </ol>
    </nav>
  )
}
