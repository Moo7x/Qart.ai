import { Link } from 'react-router-dom'
import { useApi } from '../api'
import type { OccupationPreview } from '../types'
import { Loading, Problem } from './ui'

const KIND = {
  observed: ['Observed', 'bg-observed-bg text-observed'],
  estimate: ['Estimate', 'bg-estimate-bg text-estimate'],
  expert: ['Expert view', 'bg-mist text-graphite'],
} as const

function Kind({ kind }: { kind: keyof typeof KIND }) {
  return <span className={`tag ${KIND[kind][1]}`}>{KIND[kind][0]}</span>
}

export function OccupationEvidence({ soc, compact = false }: { soc: string; compact?: boolean }) {
  const view = useApi<OccupationPreview>(`/api/occupations/${soc}`)
  if (view.loading) return <Loading what="the evidence for this occupation" />
  if (view.error) return <Problem what="the evidence" message={view.error} onRetry={view.reload} />
  const p = view.data
  if (!p) return null
  return (
    <section className="flex flex-col gap-4">
      <div className={`card-light flex flex-col gap-1.5 border-l-4 px-6 py-4 ${p.in_field ? 'border-mint' : 'border-amber-glow'}`}>
        <span className="cap">{p.soc} · O*NET 31.0</span>
        <h2 className="h2">{p.title}</h2>
        <p className="m-0 text-[13px] text-graphite">{p.description}</p>
        <p className="m-0 text-[13px] font-medium">{p.coverage}</p>
        {p.in_field && !compact && <Link className="btn btn-v self-start" to="/start">Start your full journey</Link>}
      </div>

      <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]">
        <div className="card-light flex flex-col gap-1.5 px-5 py-4 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="observed" /><span className="cap">AI use</span></span>
          {p.ai_use ? (
            <>
              <span><b>{p.ai_use.share}%</b> of sampled Claude conversations worldwide ({p.ai_use.period}){p.ai_use.share_local !== null && <>; <b>{p.ai_use.share_local}%</b> in Malaysia</>}.</span>
              {p.ai_use.automation !== null && <span className="text-graphite">{p.ai_use.automation}% of that use is automation-style; the rest is people working with AI.</span>}
              <span className="text-xs text-graphite">Anthropic Economic Index. Shows use of an AI assistant, not job losses.</span>
            </>
          ) : <span className="text-ash">Not published for this occupation (missing, not zero).</span>}
        </div>
        <div className="card-light flex flex-col gap-1.5 px-5 py-4 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="estimate" /><span className="cap">Potential exposure</span></span>
          {p.exposure ? (
            <>
              <span>ILO rates <b>{p.exposure.title}</b> (ISCO-08 {p.exposure.isco}) <b>{p.exposure.gradient}</b>, mean task score {p.exposure.mean} of 1.</span>
              <span className="text-xs text-graphite">Technical potential, not adoption. Linked through ESCO &ldquo;{p.esco.title}&rdquo; ({p.esco.match}).</span>
            </>
          ) : <span className="text-ash">{p.isco_note || 'No exposure score for this group.'}</span>}
        </div>
        <div className="card-light flex flex-col gap-1.5 px-5 py-4 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="observed" /><span className="cap">Malaysian employment</span></span>
          {p.employment ? (
            <>
              <span><b>{p.employment.title}</b>: {p.employment.headline}.</span>
              <span className="text-xs text-graphite">DOSM, the whole major group, not this occupation alone. {p.employment.note}</span>
            </>
          ) : <span className="text-ash">No Malaysian group series linked yet.</span>}
        </div>
        <div className="card-light flex flex-col gap-1.5 px-5 py-4 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="expert" /><span className="cap">Critical occupation list</span></span>
          {p.mycol ? (
            <span>{p.mycol.listed ? <>MyCOL 2024/2025 lists <b>{p.mycol.name}</b> as critical (hard to fill) in Malaysia.</> : <>Not among the {p.mycol.of} occupations MyCOL 2024/2025 lists as critical.</>}</span>
          ) : <span className="text-ash">Needs the ISCO-08 link to check.</span>}
        </div>
      </div>

      {p.tasks.length > 0 && (
        <div className="card-light flex flex-col gap-2 px-6 py-4 text-[13px]">
          <span className="flex items-center gap-2"><Kind kind="observed" /><span className="cap">Most important tasks (O*NET)</span></span>
          <ol className="m-0 space-y-1 pl-5">
            {p.tasks.map((t) => <li key={t.task}>{t.text} <span className="font-mono text-ash">· importance {t.importance ?? '—'}/5</span></li>)}
          </ol>
        </div>
      )}
    </section>
  )
}

