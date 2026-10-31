import { useState } from 'react'
import { useApi } from '../api'
import { useJourney } from '../state'
import type { IndustryCategory, IndustryForecastResponse, IndustryRoleForecast } from '../types'
import { KindLabel } from './Why'
import { Loading, Problem } from './ui'

// Display order and colour of the five categories (src/forecast/industry.py decides them).
const ORDER: IndustryCategory[] = ['growing', 'emerging', 'transforming', 'stable', 'shrinking']
const TONE: Record<IndustryCategory, string> = {
  growing: 'bg-observed-bg text-observed',
  emerging: 'bg-assumption-bg text-violet',
  transforming: 'bg-estimate-bg text-estimate',
  stable: 'bg-mist text-graphite',
  shrinking: 'bg-[#fde8e8] text-[#9b1c1c]',
}
const MODEL_NAME: Record<string, string> = {
  ridge: 'ridge regression',
  random_forest: 'random forest',
  hist_gradient_boosting: 'gradient boosting',
  lightgbm: 'LightGBM',
  xgboost: 'XGBoost',
}

function RoleRow({ role }: { role: IndustryRoleForecast }) {
  const [open, setOpen] = useState(false)
  const change = role.demand.change_pp
  return (
    <li className="border-t border-line py-2.5">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full cursor-pointer items-center justify-between gap-3 border-0 bg-transparent p-0 text-left text-[14px] text-ink">
        <span className="font-medium">{role.title}</span>
        <span className="text-[12px] text-graphite">
          {role.demand.critical && 'hard to fill (MyCOL) · '}
          {change != null && `job group ${change > 0 ? '+' : ''}${change.toFixed(2)} pts`}
          {role.ai.use != null && ` · AI ${role.ai.use.toFixed(0)}%`}
        </span>
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-1 text-[13px] text-[#404040]">
          <p className="m-0">{role.meaning}</p>
          <ul className="m-0 pl-4">{role.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          <p className="m-0 text-[12px] text-graphite">
            Measured through O*NET {role.occupation ?? 'no occupation'}{role.soc ? ` (${role.soc})` : ''}{role.soc_reason ? `: ${role.soc_reason}` : ''}.
            {' '}AI use over {role.ai.tasks_observed} observed and {role.ai.tasks_predicted} predicted tasks.
            {role.demand.source ? ` Demand: ${role.demand.source}${role.demand.fetched ? `, fetched ${role.demand.fetched.slice(0, 10)}` : ''}.` : ''}
          </p>
        </div>
      )}
    </li>
  )
}

/** Qart's own forecast for GBS finance roles and skills (GET /api/forecast/industry). */
export function IndustryForecast() {
  const { scenario } = useJourney()
  const view = useApi<IndustryForecastResponse>(`/api/forecast/industry?scenario=${scenario}`)
  if (view.loading) return <Loading what="the Qart forecast" />
  if (view.error) return <Problem what="the Qart forecast" message={view.error} onRetry={view.reload} />
  const data = view.data
  if (!data) return null
  const model = data.task_model
  const rising = data.skills.filter((s) => s.trend === 'rising')
  const declining = data.skills.filter((s) => s.trend === 'declining')
  return (
    <section className="section" aria-label="Qart forecast">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="h2">Qart forecast: where GBS finance jobs are heading ({data.scenario} AI)</h2>
        <KindLabel kind="estimate" />
      </div>
      <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]">
        {ORDER.map((category) => {
          const roles = data.roles.filter((r) => r.category === category)
          if (!roles.length) return null
          return (
            <div key={category} className="q-card gap-1 px-5 py-4">
              <span className={`self-start rounded-full px-3 py-1 text-[12px] font-semibold ${TONE[category]}`}>{roles[0].label} · {roles.length}</span>
              <p className="m-0 text-[12px] text-graphite">{roles[0].meaning}</p>
              <ul className="m-0 list-none p-0">{roles.map((r) => <RoleRow key={r.id} role={r} />)}</ul>
            </div>
          )
        })}
      </div>
      <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]">
        <div className="q-card gap-1 px-5 py-4">
          <h3 className="q-h3">Skills rising</h3>
          <p className="m-0 text-[13px] text-[#404040]">{rising.map((s) => s.name).join(', ') || 'None yet.'}</p>
        </div>
        <div className="q-card gap-1 px-5 py-4">
          <h3 className="q-h3">Skills declining</h3>
          <p className="m-0 text-[13px] text-[#404040]">{declining.map((s) => s.name).join(', ') || 'None yet.'}</p>
        </div>
      </div>
      <p className="m-0 text-xs text-graphite">
        How: each role&rsquo;s job group is forecast from DOSM employment shares (model chosen by backtest against keeping the last value). AI pressure needs two of three kinds of evidence to agree: AI use on the role&rsquo;s tasks, the ILO&rsquo;s exposure score and TalentCorp&rsquo;s impact level.
        {model && model.best !== 'none' && ` AI use on tasks without an observation is predicted by a ${MODEL_NAME[model.best] ?? model.best} model trained on ${model.training_tasks.toLocaleString()} observed tasks (${model.features === 'bge-m3' ? 'BGE-M3 text embeddings' : 'word features'}; average error ${model.mae} points against ${model.baseline_mae} for guessing the average; Economic Index ${model.period}).`}
        {' '}Switch the AI speed to see roles move between categories.
      </p>
    </section>
  )
}
