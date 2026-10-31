import { Bot, BookOpen } from 'lucide-react'
import type { RouteMetrics, Scenario, TracksResponse } from '../types'

// Reskilling with and without AI, planned by the same rules. Two cards and one sentence on what
// choosing the AI route means: extra study time against the fit it adds in each AI scenario.

function signed(v: number, unit = ''): string {
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}${unit}`
}

function Route({ title, icon, m, fitNow, scenario, tone, note }: { title: string; icon: React.ReactNode; m: RouteMetrics; fitNow: Record<Scenario, number>; scenario: Scenario; tone: string; note: string }) {
  const other: Scenario = scenario === 'fast' ? 'moderate' : 'fast'
  return (
    <div className={`flex flex-col gap-3 rounded-xl border-2 bg-paper p-5 ${tone}`}>
      <span className="flex items-center gap-2 text-[17px] font-semibold">{icon}{title}</span>
      <span className="text-[13px] text-graphite">{note}</span>
      <div className="grid grid-cols-2 gap-3">
        <span className="flex flex-col"><span className="cap">Study time</span><span className="font-mono text-[24px] leading-tight">{m.hours} h</span><span className="text-[12px] text-graphite">{m.courses} courses · {m.weeks} wk</span></span>
        <span className="flex flex-col"><span className="cap">Fit after · {scenario}</span><span className="font-mono text-[24px] leading-tight">{Math.round(fitNow[scenario])} → {Math.round(m.fit_after[scenario])}</span><span className="text-[12px] text-graphite">{other}: {Math.round(m.fit_after[other])}</span></span>
      </div>
      {m.essentials_unmet.length > 0 && <span className="text-[12px] text-weak">Essentials still short: {m.essentials_unmet.join(', ')}</span>}
    </div>
  )
}

export function RouteCompare({ data, scenario }: { data: TracksResponse['comparison']; scenario: Scenario }) {
  const w = data.without_ai
  const a = data.with_ai
  const extraHours = a.hours - w.hours
  const gainFast = a.fit_after.fast - w.fit_after.fast
  const gainModerate = a.fit_after.moderate - w.fit_after.moderate
  const verdict =
    gainFast > 0 || gainModerate > 0
      ? `Choosing AI costs ${signed(extraHours, ' h')} of study and adds ${signed(gainModerate, ' fit points')} if AI adoption is moderate, ${signed(gainFast, '')} if it is fast: the skills that work with AI gain weight as AI takes over routine tasks.`
      : `For this role the AI route adds ${signed(extraHours, ' h')} of study without raising your fit: its skills do not gain weight from AI yet.`
  return (
    <section className="section" aria-label="Reskilling with and without AI">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="h2">With AI or without: what it changes for you</h2>
        <span className="tag bg-estimate-bg text-estimate">Estimate</span>
      </div>
      <p className="m-0 max-w-[820px] rounded-lg border-l-4 border-violet bg-violet-soft px-4 py-3 text-[15px] font-medium">{verdict}</p>
      <div className="grid gap-4 md:grid-cols-2">
        <Route title="Without AI" icon={<BookOpen size={18} className="text-[#e0892f]" />} m={w} fitNow={data.fit_now} scenario={scenario} tone="border-[#f0c79a]" note="The role's skills as they are done today." />
        <Route title="With AI" icon={<Bot size={18} className="text-violet" />} m={a} fitNow={data.fit_now} scenario={scenario} tone="border-violet" note={`Also the AI basics${a.ai_basics_hours ? ` (${a.ai_basics_hours} h)` : ''} and the data and digital skills the role needs.`} />
      </div>
      <p className="m-0 text-[12px] text-graphite">&ldquo;With AI&rdquo; means learning to work with AI tools, not studying with an AI tutor. Both routes use the same verified free courses and rules.</p>
    </section>
  )
}
