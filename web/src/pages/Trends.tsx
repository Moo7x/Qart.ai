import { useT } from '../i18n'
import { useApi } from '../api'
import { TimeSeriesChart } from '../components/Charts'
import { ScenarioSwitch } from '../components/journey'
import { TrendsChart } from '../components/TrendsChart'
import { KindLabel } from '../components/Why'
import { Loading, Problem } from '../components/ui'
import type { TrendsResponse } from '../types'

// Groups too small to read on the shared chart, and unrelated to finance work.
const LEFT_OUT = new Set(['agriculture'])

export function Trends() {
  const { t } = useT()
  const view = useApi<TrendsResponse>('/api/trends')
  const data = view.data
  // One chart for every job group: change in its share of employees since the first comparable
  // year, so all lines start at 0 and can be compared on one scale.
  const groups = (data?.employment ?? [])
    .filter((g) => !LEFT_OUT.has(g.group))
    .sort((a, b) => b.change_long - a.change_long)
    .map((g) => {
      const base = g.points[0]?.value ?? 0
      return { label: g.title, points: g.points.map((p) => ({ ...p, value: Math.round(100 * (p.value - base)) / 100 })) }
    })
  const first = data?.employment[0]?.first
  const last = data?.employment[0]?.last
  return (
    <main className="page">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Future skills radar</span>
          <h1 className="h1">{t('What is growing, what is shrinking')}</h1>
        </div>
        <ScenarioSwitch />
      </header>
      <TrendsChart />
      {view.loading && <Loading what="the trends" />}
      {view.error && <Problem what="the trends" message={view.error} onRetry={view.reload} />}
      {data && groups.length > 0 && (
        <section className="section">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="h2">How each job group&rsquo;s share of Malaysian employees changed since {first}</h2>
            <KindLabel kind="observed" />
          </div>
          <TimeSeriesChart series={groups} unit="pts" axis="pts since start" source={`DOSM via OpenDOSM, ${first}–${last}`} height={320} />
          <p className="m-0 text-xs text-graphite">Above 0: a growing part of the workforce. Accountants sit in Professionals, finance clerks in Clerical support. Starts in {first}, when DOSM changed its occupation classification.</p>
        </section>
      )}
    </main>
  )
}
