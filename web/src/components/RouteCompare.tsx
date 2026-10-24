import type { RouteMetrics, Scenario, TracksResponse } from '../types'

function FitBar({ now, after, tone }: { now: number; after: number; tone: string }) {
  return (
    <span className="relative block h-2.5 w-full bg-mist" aria-hidden="true">
      <span className="absolute inset-y-0 left-0 bg-stone" style={{ width: `${now}%` }} />
      <span className={`absolute inset-y-0 ${tone}`} style={{ left: `${now}%`, width: `${Math.max(after - now, 0)}%` }} />
    </span>
  )
}

function signed(v: number, unit = ''): string {
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}${unit}`
}

// Reskilling with and without AI, planned by the same rules: time, effort, fit and efficiency.
export function RouteCompare({ data, scenario }: { data: TracksResponse['comparison']; scenario: Scenario }) {
  const other: Scenario = scenario === 'fast' ? 'moderate' : 'fast'
  const routes: [string, string, RouteMetrics, string][] = [
    ['without', 'Without AI', data.without_ai, 'bg-[#e0892f]'],
    ['with', 'With AI', data.with_ai, 'bg-violet'],
  ]
  const w = data.without_ai
  const a = data.with_ai
  const rows: [string, (m: RouteMetrics) => string, string][] = [
    ['Study time', (m) => `${m.hours} h · ${m.weeks} wk`, signed(a.hours - w.hours, ' h')],
    ['Courses', (m) => String(m.courses), signed(a.courses - w.courses)],
    [`Fit after · ${scenario}`, (m) => `${Math.round(m.fit_after[scenario])}/100`, signed(a.fit_after[scenario] - w.fit_after[scenario], ' pts')],
    [`Fit after · ${other}`, (m) => `${Math.round(m.fit_after[other])}/100`, signed(a.fit_after[other] - w.fit_after[other], ' pts')],
    ['Fit gained per 10 h', (m) => `${m.points_per_10h[scenario]} pts`, signed(a.points_per_10h[scenario] - w.points_per_10h[scenario], ' pts')],
    ['Essentials still short', (m) => (m.essentials_unmet.length ? m.essentials_unmet.join(', ') : 'none'), ''],
  ]
  return (
    <section className="section" aria-label="Reskilling with and without AI">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h2">Reskilling with AI or without: what it changes</h2>
        <span className="tag bg-estimate-bg text-estimate">Estimate · same planner and course rules</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {routes.map(([key, title, m, tone]) => (
          <div key={key} className={`flex flex-col gap-2 border-t-2 pt-3 ${key === 'with' ? 'border-violet' : 'border-[#e0892f]'}`}>
            <div className="flex items-baseline justify-between gap-2">
              <h3 className="m-0 text-base font-semibold">{title}</h3>
              <span className="font-mono text-[12px] text-graphite">{m.hours} h · {m.courses} courses</span>
            </div>
            {([scenario, other] as Scenario[]).map((s) => (
              <div key={s} className="flex flex-col gap-1">
                <span className="flex justify-between text-[12px]"><span className="text-graphite">Fit {Math.round(data.fit_now[s])} → <b className="text-void">{Math.round(m.fit_after[s])}</b></span><span className="cap">{s} adoption</span></span>
                <FitBar now={data.fit_now[s]} after={m.fit_after[s]} tone={tone} />
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] border-collapse text-[13px]">
          <thead>
            <tr className="cap text-left">
              <th className="py-2 pr-2 font-normal">Measure</th>
              <th className="px-2 py-2 font-normal">Without AI</th>
              <th className="px-2 py-2 font-normal">With AI</th>
              <th className="py-2 pl-2 text-right font-normal">Difference</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, value, diff]) => (
              <tr key={label} className="border-t border-line">
                <td className="py-2 pr-2">{label}</td>
                <td className="px-2 py-2 font-mono">{value(w)}</td>
                <td className="px-2 py-2 font-mono">{value(a)}</td>
                <td className="py-2 pl-2 text-right font-mono font-semibold">{diff}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-[12px] text-graphite">
        &ldquo;With AI&rdquo; means also learning the AI basics and the data and digital skills the role needs, not studying with an AI tutor. {a.ai_basics_hours ? `It includes ${a.ai_basics_hours} h of AI basics. ` : ''}{data.note}
      </p>
    </section>
  )
}
