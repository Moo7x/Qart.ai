import { useApi } from '../api'
import type { PlanOption, PlansResponse, Scenario } from '../types'
import { Loading, Problem } from './ui'

const PLAN_TEXT: Record<string, [string, string]> = {
  greedy: ['Simple plan', 'Shortest course for each gap, essentials first, cut at your time budget (baseline).'],
  best: ['Best within your time', 'Every combination of the relevant courses checked; most essentials, then highest projected fit.'],
  robust: ['Safe first steps', 'The combination whose projected fit holds up best under both adoption scenarios.'],
}

function Column({ name, plan, scenario }: { name: string; plan: PlanOption; scenario: Scenario }) {
  const [title, how] = PLAN_TEXT[name]
  return (
    <div className="flex min-w-0 flex-[1_1_220px] flex-col gap-1.5 rounded-lg border border-mist p-3 text-[13px]">
      <span className="font-semibold">{title}</span>
      <span className="text-xs text-graphite">{how}</span>
      <span className="font-mono">{plan.hours} h · {plan.courses.length} course{plan.courses.length === 1 ? '' : 's'}</span>
      <span className="font-mono">
        projected fit {plan.fit_after[scenario].toFixed(1)}
        <span className="text-graphite"> (moderate {plan.fit_after.moderate.toFixed(1)} · fast {plan.fit_after.fast.toFixed(1)})</span>
      </span>
      <span className="text-xs">essentials reached {plan.essentials_reached} of {plan.essentials_total}</span>
      <ol className="m-0 space-y-0.5 pl-4 text-xs">
        {plan.courses.map((c) => <li key={c.id}><a href={c.url} target="_blank" rel="noreferrer">{c.title}</a> · {c.hours} h</li>)}
      </ol>
    </div>
  )
}

// Three plans for the same role and the same time budget, scored by the same declared rules.
export function PlanCompare({ profileId, scenario }: { profileId: string; scenario: Scenario }) {
  const view = useApi<PlansResponse>(`/api/profiles/${profileId}/plans?scenario=${scenario}`)
  if (view.loading) return <Loading what="the plan comparison" />
  if (view.error) return <Problem what="the plan comparison" message={view.error} onRetry={view.reload} />
  const data = view.data
  if (!data) return null
  const entries = (['greedy', 'best', 'robust'] as const).flatMap((k) => (data.plans[k] ? [[k, data.plans[k]] as const] : []))
  const same = entries.every(([, p]) => p.course_ids.join() === entries[0][1].course_ids.join())
  return (
    <details className="card-light px-6 py-4" open={!same}>
      <summary className="h2 cursor-pointer">Compare plans within {data.budget_hours} h ({data.budget_weeks} weeks at your pace)</summary>
      <p className="m-0 mt-2 text-xs text-graphite">
        {same
          ? 'All three plans are the same here: your time budget fits the whole route.'
          : 'The plans differ because your time budget cannot fit every course.'}{' '}
        {data.note} Projected fit is an estimate from declared course rules, not a measured learning result.
      </p>
      <div className="mt-3 flex flex-wrap gap-3">
        {entries.map(([name, plan]) => <Column key={name} name={name} plan={plan} scenario={scenario} />)}
      </div>
    </details>
  )
}
