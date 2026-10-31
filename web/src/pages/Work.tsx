import type { ReactNode } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useApi } from '../api'
import type { RadarOut, WorkTask, WorkTodayOut } from '../apiTypes'
import { Card, DarkLink, Label, ScenarioSwitch, SCENARIO_TEXT, Serif } from '../components/atoms'
import { FlowSteps } from '../components/FlowSteps'
import { ChangePill, Sparkline } from '../components/MiniCharts'
import { Loading, Problem } from '../components/ui'
import { WhyButton } from '../components/Why'
import { useJourney } from '../state'

const pct = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${v}%`)

function Chip({ title, quiet, grow, children }: { title: string; quiet?: boolean; grow: string; children: ReactNode }) {
  return (
    <div className={`flex min-w-0 flex-col gap-0.5 rounded-[14px] px-3.5 py-2 ${quiet ? 'border border-dashed border-[#d4d4d8] bg-[#f4f4f5] text-[#71717a]' : 'border border-[#e5e5e5] bg-white'}`} style={{ flex: grow }}>
      <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-muted">{title}</span>
      <span className="flex flex-wrap items-center gap-1.5 text-[13px]">{children}</span>
    </div>
  )
}

function AiUse({ task }: { task: WorkTask }) {
  const use = task.observed_use
  if (!use || use.share === null) {
    return (
      <span className="flex min-w-0 items-center gap-2">
        <span aria-hidden="true" className="w-bar h-2 max-w-[120px] flex-auto rounded-full border border-dashed border-[#d4d4d8]" />
        <span className="whitespace-nowrap text-[13px] text-[#71717a]"><span className="w-mob">AI use: </span>no data <span className="text-xs">(not zero)</span></span>
      </span>
    )
  }
  const assist = use.augmentation ?? 0
  return (
    <span className="flex min-w-0 flex-col gap-1">
      <span className="flex items-center gap-2">
        <span aria-hidden="true" className="w-bar flex h-2 max-w-[120px] flex-auto overflow-hidden rounded-full bg-[#f0f0f0]">
          <span style={{ width: `${assist}%`, background: '#0072B2' }} />
          <span style={{ width: `${use.automation ?? 0}%`, background: '#D55E00' }} />
        </span>
        <span className="whitespace-nowrap text-[13px]"><span className="w-mob">AI use: </span>{pct(use.share)} of conversations</span>
      </span>
      <span className="text-xs text-muted">assist {pct(use.augmentation)} · automation-style {pct(use.automation)} · {use.period}</span>
    </span>
  )
}

/** "How AI is changing your work today": the current job, before the roles (design-prototype/
 *  pages.py work). Four kinds of evidence kept apart; missing evidence reads "no data". */
export function Work() {
  const { profileId, scenario } = useJourney()
  const work = useApi<WorkTodayOut>(profileId ? `/api/profiles/${profileId}/work-today` : null)
  const radar = useApi<RadarOut>(profileId ? `/api/profiles/${profileId}/radar?scenario=${scenario}` : null)
  if (!profileId) return <Navigate to="/start" replace />
  if (work.error?.includes('no current job')) return <Navigate to="/roles" replace />
  const data = work.data
  const axes = (radar.data?.axes ?? []).filter((a) => a.claimed !== null)
  const moved = axes.some((a) => a.emphasis === 'rising' || a.emphasis === 'weakening')
  const noUse = axes.every((a) => a.ai_use === null)
  const why = data && [
    { key: 'use', title: 'AI use in conversations', hint: 'observed', body: <p className="m-0">The Anthropic Economic Index reports, per O*NET task, the share of sampled Claude conversations, split into assist (augmentation) and automation-style use, with its release period. {data.tasks.some((t) => t.observed_use) ? '' : 'None is stored for these tasks, so each reads “no data”: missing is not zero.'} <span className="q-src">{data.sources.observed_use}</span></p> },
    { key: 'tasks', title: 'Your tasks', hint: data.task_source === 'onet' ? 'O*NET' : 'ILO', body: <p className="m-0">{data.task_source === 'onet' ? 'The O*NET tasks the pack links to a skill for your occupation. Which task shows which skill is our declared mapping (an assumption). “You do this” means you claim that skill with a sentence from your CV.' : 'No O*NET task is linked to a skill for your occupation yet, so this is the ILO’s task list for it, each with its exposure score (an estimate of technical potential). These tasks carry no observed AI use and no skill link.'} <span className="q-src">{data.sources.tasks}</span></p> },
    { key: 'exposure', title: 'Potential exposure', hint: 'estimate', body: <p className="m-0">{data.exposure ? `The ILO rates ${data.exposure.title} (ISCO-08 ${data.exposure.isco}) “${data.exposure.gradient}”, mean task score ${data.exposure.mean} of 1: how much of the work current generative AI could technically perform. It is not adoption and not job loss.` : 'No exposure score for this occupation yet (missing, not zero).'} <span className="q-src">{data.sources.exposure}</span></p> },
    { key: 'expert', title: 'Expert view', hint: 'TalentCorp', body: <p className="m-0">{data.role.impact_text} <span className="q-src">{data.sources.expert}</span></p> },
    { key: 'deployment', title: 'Reported deployment', hint: 'not collected', body: <p className="m-0">No source of organisations reporting AI deployment for these tasks is collected yet.</p> },
  ]
  return (
    <main className="page gap-5">
      <FlowSteps current="work" />
      <div className="q-tray">
        <Card label="How AI is changing your work today" className="gap-3.5 px-6 py-5">
          {work.loading && <Loading what="your work today" />}
          {work.error && !work.error.includes('no current job') && <Problem what="your work today" message={work.error} onRetry={work.reload} />}
          {data && why && (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 flex-col gap-1.5">
                  <h1 className="m-0 text-[clamp(26px,3.4vw,36px)] font-medium leading-[1.08] tracking-[-0.02em]">How AI is changing your work <Serif>today</Serif></h1>
                  <span className="text-[15px] text-[#404040]">{data.role.title} · your role at a glance</span>
                </div>
                <div className="w-scen flex items-center gap-2"><ScenarioSwitch /></div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Chip title="Expert view" grow="1 1 250px">
                  <b className="font-semibold">{data.role.impact[0].toUpperCase() + data.role.impact.slice(1)} impact</b>
                  <span className="text-[#404040]">· {data.role.source.replace('TalentCorp (2024) GBS study, PDF', 'TalentCorp 2024,')}</span>
                </Chip>
                <Chip title="Potential exposure" grow="2.4 1 420px">
                  {data.exposure ? <b className="font-semibold">{data.exposure.gradient}</b> : <span className="text-[#71717a]">no data</span>}
                  <Label kind="estimate" />
                  <span className="text-[#404040]">ILO 2025 · technical potential, not adoption or job loss</span>
                </Chip>
                <Chip title="Reported deployment" quiet grow="0.6 1 200px">not collected yet</Chip>
              </div>
              <section aria-label="Job market for your occupation" className="flex flex-col gap-1.5">
                <span className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-muted">Job market for your occupation <Label kind="observed" /></span>
                {data.market.length === 0 && <p className="m-0 text-[13px] text-[#71717a]">Not in this snapshot of the evidence (missing, not zero).</p>}
                <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
                  {data.market.map((m) => {
                    const last = m.points[m.points.length - 1]
                    return (
                      <li key={m.text} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-[#f0f0f0] bg-white px-3 py-2 text-[13px] shadow-[0_1px_2px_rgba(0,0,0,.03)]">
                        <span className="min-w-[200px] flex-[1_1_260px] leading-snug" title={m.text}>{m.text.split(':')[0]} <span className="text-muted">· {m.source}, {m.period}</span></span>
                        <Sparkline points={m.points} label={m.text.split(':')[0]} />
                        {last && <span className="whitespace-nowrap font-semibold">{Math.round(last.value * 100) / 100}{m.unit.startsWith('%') ? '%' : ` ${m.unit}`}</span>}
                        <ChangePill points={m.points} unit={m.unit} />
                      </li>
                    )
                  })}
                </ul>
              </section>
              <section aria-label="Your tasks and AI" className="flex flex-col gap-1.5">
                <div className="w-row w-head">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-muted">Your tasks</span>
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-muted">AI use in conversations <Label kind="observed" /></span>
                  <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-muted">Skill it shows</span>
                </div>
                <ul className="m-0 list-none p-0">
                  {data.tasks.map((task) => (
                    <li key={task.task ?? task.text} className="w-row">
                      <span className="flex min-w-0 items-start gap-2.5">
                        <span aria-hidden="true" className={`mt-1.5 h-2 w-2 flex-none rounded-full ${task.you_do_this ? 'bg-violet' : 'bg-[#a3a3a3]'}`} />
                        <span className="min-w-0 text-[13px] leading-snug">
                          {task.text}
                          {task.you_do_this && <span className="ml-1 inline-block whitespace-nowrap rounded-full bg-assumption-bg px-2 py-px align-[1px] text-[11px] font-semibold text-[#3b1fc2]">you do this</span>}
                          {task.exposure_score !== null && <span className="ml-1 whitespace-nowrap text-xs text-muted">exposure {task.exposure_score} of 1 <Label kind="estimate" /></span>}
                        </span>
                      </span>
                      <AiUse task={task} />
                      <span className="inline-flex min-w-0 items-center gap-1.5">
                        {task.skill_name ? <span className="rounded-full bg-tray px-2.5 py-0.5 text-xs font-medium">{task.skill_name}</span> : <span className="text-xs text-[#71717a]">not linked yet</span>}
                      </span>
                    </li>
                  ))}
                </ul>
                {data.tasks.length === 0 && <p className="m-0 text-sm text-muted">No task list for this occupation is stored yet.</p>}
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
                  <p className="q-src min-w-[240px] flex-1">
                    AI use: Anthropic Economic Index (assist vs automation-style share of conversations){data.tasks.some((t) => t.observed_use) ? '' : ' · none stored for these tasks'} · Tasks: {data.sources.tasks} · Skill match from your CV (assumption)
                  </p>
                  <WhyButton title="Where this screen’s evidence comes from" panes={why} />
                </div>
              </section>
              <section aria-label="What it means for your skills" className="flex flex-col gap-2 border-t border-[#f0f0f0] pt-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.06em] text-muted">What it means for your skills · {SCENARIO_TEXT[scenario]}</span>
                    <Label kind="assumption" />
                  </span>
                  <span className="text-xs text-muted">
                    {radar.data && `For ${radar.data.title}${radar.data.chosen ? '' : ', your best fit today'}`}
                    {radar.data && !moved && ` · No weight moved: ${noUse ? 'no observed AI use is stored' : 'the observed use does not shift these skills'} · essentials never move`}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {axes.map((a) => {
                    const [mark, text, colour] = a.emphasis === 'fixed' ? ['■', 'essential, fixed', '#92400e'] : a.emphasis === 'rising' ? ['↑', 'more important', '#157a4a'] : a.emphasis === 'weakening' ? ['↓', 'less weight', '#9a4609'] : ['→', 'steady', '#525252']
                    return (
                      <span key={a.skill} className="inline-flex min-h-[36px] items-center gap-2 rounded-full border border-[#e5e5e5] bg-white px-3.5 text-[13px]">
                        <span aria-hidden="true" className="font-bold" style={{ color: colour }}>{mark}</span>
                        <b className="font-semibold">{a.name}</b>
                        <span style={{ color: colour }}>{text}</span>
                      </span>
                    )
                  })}
                  {radar.data && axes.length === 0 && <span className="text-sm text-muted">None of the skills you claimed is weighed by this role.</span>}
                </div>
              </section>
              <div className="flex flex-wrap items-center gap-2.5 border-t border-[#e5e5e5] pt-3.5">
                <Link to="/start?edit=1" className="q-btn q-btn-text">← Your CV</Link>
                <span className="flex-auto text-right text-sm font-semibold">These signals shape which roles fit you next.</span>
                <DarkLink to="/roles">See my future roles</DarkLink>
              </div>
            </>
          )}
        </Card>
      </div>
    </main>
  )
}
