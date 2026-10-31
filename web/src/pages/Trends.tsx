import { useT } from '../i18n'
import { useApi } from '../api'
import { ScenarioSwitch } from '../components/journey'
import { TrendsChart } from '../components/TrendsChart'
import { IndustryForecast } from '../components/IndustryForecast'
import { Loading, Problem } from '../components/ui'
import type { TrendsResponse } from '../types'

export function Trends() {
  const { t } = useT()
  const view = useApi<TrendsResponse>('/api/trends')
  return (
    <main className="page">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Future skills radar</span>
          <h1 className="h1">{t('What is growing, what is shrinking')}</h1>
        </div>
        <ScenarioSwitch />
      </header>
      <IndustryForecast />
      <TrendsChart />
      {view.loading && <Loading what="the trends" />}
      {view.error && <Problem what="the trends" message={view.error} onRetry={view.reload} />}
    </main>
  )
}
