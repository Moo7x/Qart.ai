import { useApi } from '../api'
import type { PlanOption, PlansResponse, Scenario } from '../types'
import { Loading, Problem } from './ui'

const PLAN_TEXT: Record<string, [string, string, string]> = {
  greedy: ['Simple plan', 'Shortest course for each gap, essentials first.', 'Shortest course for each gap, essentials first, cut at your time budget. This is the baseline the other two are compared with.'],
  best: ['Best within your time', 'The strongest set of courses that fits your hours.', 'Every combination of the relevant courses was checked; the plan reaches the most essential skills, then the highest projected fit.'],
  robust: ['Safe first steps', 'Holds up whether AI adoption is moderate or fast.', 'The combination whose projected fit stays best across both adoption scenarios.'],
}

function Column({ name, plan, scenario }: { name: string; plan: PlanOption; scenario: Scenario }) {
  const [title, short, how] = PLAN_TEXT[name]
  return (
    <section aria-label={title} className="flex min-w-0 flex-col gap-3 border-t-2 border-void pt-3">
      <div className="flex flex-col gap-0.5">
        <h3 className="m-0 text-base font-semibold tracking-tight">{title}</h3>
        <span className="text-[13px] text-graphite">{short}</span>
      </div>
      <span className="font-mono text-[12px]">
        {plan.courses.length} course{plan.courses.length === 1 ? '' : 's'} · {plan.hours} h · essentials {plan.essentials_reached}/{plan.essentials_total}
      </span>
      <ol className="m-0 flex list-none flex-col p-0 text-[13px]">
        {plan.courses.map((c, i) => (
          <li key={c.id} className="grid grid-cols-[20px_minmax(0,1fr)_auto] gap-2 border-t border-line py-2">
            <span className="font-mono text-ash">{i + 1}</span>
            <a href={c.url} target="_blank" rel="noreferrer" className="text-void underline-offset-2 hover:underline">{c.title}</a>
            <span className="font-mono text-[11px] text-graphite">{c.hours} h</span>
          </li>
        ))}
      </ol>
      <details className="text-[12px] text-graphite">
        <summary className="cursor-pointer text-[13px] text-void">Why this plan</summary>
        <p className="m-0 mt-1.5">{how}</p>
        <p className="m-0 mt-1.5 font-mono">
          Projected fit after it: {plan.fit_after[scenario].toFixed(1)} under this scenario (moderate {plan.fit_after.moderate.toFixed(1)} · fast {plan.fit_after.fast.toFixed(1)}). Estimate.
        </p>
      </details>
    </section>
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
    <section className="section" aria-label="Compare plans">
      <div className="flex flex-col gap-1">
        <h2 className="h2">Compare plans within {data.budget_hours} h</h2>
        <p className="m-0 text-[13px] text-graphite">
          {same
            ? 'All three ways of planning give the same courses here, because your time budget fits the whole route.'
            : `Your ${data.budget_weeks}-week budget cannot fit every course, so the three ways of planning pick differently.`}
        </p>
      </div>
      {same ? (
        <Column name="greedy" plan={entries[0][1]} scenario={scenario} />
      ) : (
        <div className="grid gap-6 md:grid-cols-3">
          {entries.map(([name, plan]) => <Column key={name} name={name} plan={plan} scenario={scenario} />)}
        </div>
      )}
      <p className="m-0 text-[11px] text-graphite">{data.note} Projected fit is an estimate from declared course rules, not a measured learning result.</p>
    </section>
  )
}
