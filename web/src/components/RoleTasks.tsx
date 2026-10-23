import { useApi } from '../api'
import type { RoleTasksResponse, TaskUse } from '../types'
import { Loading, Problem } from './ui'

const KIND = {
  observed: ['Observed', 'bg-observed-bg text-observed'],
  estimate: ['Estimate', 'bg-estimate-bg text-estimate'],
  expert: ['Expert view', 'bg-mist text-graphite'],
  missing: ['Not collected', 'bg-weak-bg text-weak'],
} as const

function Kind({ kind }: { kind: keyof typeof KIND }) {
  return <span className={`tag ${KIND[kind][1]}`}>{KIND[kind][0]}</span>
}

function pct(value: number | null) {
  return value === null ? 'not published' : `${value}%`
}

function Use({ use }: { use: TaskUse | null }) {
  if (!use) return <span className="text-ash">Not in the sampled conversations (missing, not zero)</span>
  return (
    <span className="flex flex-col gap-0.5">
      <span className="font-mono">
        {use.share === 0 ? 'under 0.01% (published rounded to 0.00)' : pct(use.share)} of conversations · {use.period}
      </span>
      <span className="text-graphite">automation-style {pct(use.automation)} · augmentation {pct(use.augmentation)}</span>
      {use.share_local !== null && <span className="text-graphite">Malaysia: {use.share_local}% of its conversations</span>}
    </span>
  )
}

export function RoleTasks({ profileId, roleId }: { profileId: string; roleId: string }) {
  const view = useApi<RoleTasksResponse>(`/api/profiles/${profileId}/roles/${roleId}/tasks`)
  if (view.loading) return <Loading what="the role's tasks" />
  if (view.error) return <Problem what="the role's tasks" message={view.error} onRetry={view.reload} />
  const data = view.data
  if (!data) return null
  const occ = data.occupation
  return (
    <section className="card-light flex flex-col gap-4 px-6 py-5">
      <div className="flex flex-col gap-1">
        <h2 className="h2">What changes in this role's tasks</h2>
        <p className="m-0 text-[13px] text-graphite">
          Four kinds of evidence, kept apart. None of them alone says a task is being automated. {data.summary}
        </p>
      </div>

      <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(220px,1fr))]">
        <div className="flex flex-col gap-1.5 rounded-lg border border-mist p-3 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="estimate" /><span className="cap">Potential exposure</span></span>
          {data.exposure ? (
            <>
              <span>ILO rates <b>{data.exposure.title}</b> (ISCO-08 {data.exposure.isco}) <b>{data.exposure.gradient}</b>, mean task score {data.exposure.mean} of 1.</span>
              <details className="text-xs">
                <summary className="cursor-pointer text-graphite">Its {data.exposure.tasks.length} ISCO tasks and scores</summary>
                <ul className="mt-1.5 space-y-1 pl-4">
                  {data.exposure.tasks.map((t) => <li key={t.text}><span className="font-mono">{t.score}</span> · {t.text}</li>)}
                </ul>
              </details>
              <span className="text-xs text-graphite">
                Technical potential, not adoption or job loss. Linked through ESCO "{occ?.esco}" ({occ?.esco_match}). <a href={data.exposure.url} target="_blank" rel="noreferrer">{data.sources.exposure} ↗</a>
              </span>
            </>
          ) : (
            <span className="text-ash">No exposure score for this occupation yet (missing, not zero).</span>
          )}
        </div>
        <div className="flex flex-col gap-1.5 rounded-lg border border-mist p-3 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="expert" /><span className="cap">Expert impact</span></span>
          <span>{data.expert.text}</span>
          <span className="text-xs text-graphite">The study combines AI, digital and green drivers. {data.sources.expert}</span>
        </div>
        <div className="flex flex-col gap-1.5 rounded-lg border border-mist p-3 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="missing" /><span className="cap">Reported deployment</span></span>
          <span className="text-ash">No source collected yet reports organisations using AI for these tasks. Usage in chats is not deployment.</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[540px] border-collapse text-[13px]">
          <thead>
            <tr className="text-left font-mono text-[11px] tracking-wider text-ash">
              <th className="py-1.5 pr-2 font-normal">O*NET TASK · {data.soc}</th>
              <th className="px-2 py-1.5 font-normal">SHOWS SKILL</th>
              <th className="px-2 py-1.5 font-normal">IMPORTANCE <Kind kind="observed" /></th>
              <th className="py-1.5 pl-2 font-normal">AI USE <Kind kind="observed" /></th>
            </tr>
          </thead>
          <tbody>
            {data.tasks.map((t) => (
              <tr key={t.task} className="border-t border-mist align-top">
                <td className="py-2 pr-2">{t.text}</td>
                <td className="px-2 py-2 text-graphite">{t.skills.join(', ')}</td>
                <td className="px-2 py-2 font-mono">{t.importance?.value ?? '—'}<span className="text-ash"> / 5</span></td>
                <td className="py-2 pl-2 text-xs"><Use use={t.observed_use} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-xs text-graphite">
        Tasks: {data.sources.tasks}; which task shows which skill is our declared mapping (assumption). AI use: {data.sources.observed_use}.
        {data.unlinked_skills.length > 0 && <> No O*NET task describes {data.unlinked_skills.join(', ')} for this occupation; those skills use the occupation-level figure.</>}
      </p>
    </section>
  )
}
