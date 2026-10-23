import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronUp, Clock, ExternalLink, Info, Star, TriangleAlert } from 'lucide-react'
import { getRanking } from '../api'
import { SignalBadge } from '../components/SignalParts'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { RankedRoleView, RankingGapItem, RankingResponse, RankingWeights, ScenarioName } from '../types'
import { btn, Card, EmptyState, Highlight, Loading, PageHeader, ProvenanceTag, SectionTitle, Tag, type Tone } from '../ui'

const SHOWN = 5 // roles shown before "Show all"
const BAND_TONE: Record<string, Tone> = { 'Strong match': 'action', 'Good match': 'marigold', Stretch: 'linen' }
const RELATION: Record<string, string> = { same: 'Same field', adjacent: 'Nearby move', far: 'New field' }

// Breakdown colours, validated with the dataviz palette script (all checks pass; saffron is
// under 3:1 on white, so every segment's points are also written as text in the legend).
const PARTS: { key: keyof RankingWeights; name: string; color: string }[] = [
  { key: 'skill', name: 'Skills', color: '#0075de' },
  { key: 'momentum', name: 'Market momentum', color: '#e89d01' },
  { key: 'direction', name: 'Direction fit', color: '#0f9d8a' },
  { key: 'feasibility', name: 'Time to get there', color: '#f64932' },
]

const points = (role: RankedRoleView, key: keyof RankingWeights, scenario: ScenarioName) =>
  role.scenarios[scenario].weights[key] * role.components[key] * 100

function levelWord(value: number, levels: RankingResponse['levels']): string {
  if (value <= 0) return 'Not yet'
  return [...levels].reverse().find(l => value >= l.value)?.label ?? levels[0].label
}

/** How the score is made up: one segment per component (weight × value), points as text. */
function Breakdown({ role, scenario }: { role: RankedRoleView; scenario: ScenarioName }) {
  const s = role.scenarios[scenario]
  return (
    <div className="space-y-2">
      <div className="flex h-2.5 w-full gap-[2px] rounded-full bg-linen overflow-hidden" role="img"
        aria-label={`Score ${s.score}: ${PARTS.map(p => `${p.name} ${Math.round(points(role, p.key, scenario))}`).join(', ')}`}>
        {PARTS.map(p => (
          <div key={p.key} style={{ width: `${points(role, p.key, scenario)}%`, background: p.color }} className="h-full first:rounded-l-full" />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-graphite">
        {PARTS.map(p => (
          <li key={p.key} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden="true" />
            {p.name} <span className="tabular-nums text-ink">{Math.round(points(role, p.key, scenario))}</span>
          </li>
        ))}
        {s.exposure_points > 0 && <li className="text-ink tabular-nums">− {s.exposure_points} AI exposure</li>}
        {s.capped && <li className="text-ink">capped at {s.score}</li>}
      </ul>
    </div>
  )
}

function GapList({ role }: { role: RankedRoleView }) {
  if (role.gap.length === 0) return <p className="text-sm text-graphite">You already meet the level this role asks for in every skill.</p>
  const firstBeyond = role.gap.findIndex(g => !g.fits_timeframe)
  const total = role.gap.reduce((h, g) => h + g.hours, 0)
  return (
    <div className="space-y-3">
      <p className="text-sm text-graphite">
        In learning order: core skills first, then what lifts your match most per hour. About <span className="tabular-nums text-ink">{Math.round(total)} h</span> in total; your plan has <span className="tabular-nums text-ink">{Math.round(role.available_hours)} h</span>.
      </p>
      <ol className="space-y-2">
        {role.gap.map((g, i) => (
          <li key={g.skill_id}>
            {i === firstBeyond && (
              <div className="my-3 flex items-center gap-2 text-xs font-medium text-coral-ink" role="separator">
                <span className="h-px flex-1 bg-coral/40" /> Beyond your current plan <span className="h-px flex-1 bg-coral/40" />
              </div>
            )}
            <GapRow item={g} order={i + 1} />
          </li>
        ))}
      </ol>
      {firstBeyond === -1 && <p className="text-xs font-medium text-action-ink">All of it fits your plan.</p>}
    </div>
  )
}

function GapRow({ item, order }: { item: RankingGapItem; order: number }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-md border border-hairline px-3 py-2.5">
      <span className="w-6 text-sm text-graphite tabular-nums">{order}</span>
      <span className="font-medium text-ink">{item.label}</span>
      {item.is_core && <Tag tone="action" icon={Star}>Core</Tag>}
      <span className="inline-flex items-center gap-1 text-xs text-graphite tabular-nums"><Clock size={12} aria-hidden="true" /> ~{Math.round(item.hours)} h</span>
      {item.momentum_label === 'no_data'
        ? <Tag tone="linen">No market data</Tag>
        : <SignalBadge label={item.momentum_label} />}
    </div>
  )
}

function Calculation({ role, data }: { role: RankedRoleView; data: RankingResponse }) {
  const s = role.scenarios[data.scenario]
  const other: ScenarioName = data.scenario === 'moderate' ? 'fast' : 'moderate'
  return (
    <div className="space-y-5 text-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <caption className="sr-only">Components of the score</caption>
          <thead className="text-xs text-graphite"><tr><th className="py-1 font-medium">Component</th><th className="py-1 font-medium text-right">Value (0–1)</th><th className="py-1 font-medium text-right">Weight</th><th className="py-1 font-medium text-right">Points</th></tr></thead>
          <tbody className="tabular-nums">
            {PARTS.map(p => (
              <tr key={p.key} className="border-t border-hairline">
                <td className="py-1.5 text-ink">{p.name}</td>
                <td className="py-1.5 text-right">{role.components[p.key].toFixed(2)}</td>
                <td className="py-1.5 text-right">{s.weights[p.key]}</td>
                <td className="py-1.5 text-right">{points(role, p.key, data.scenario).toFixed(1)}</td>
              </tr>
            ))}
            {s.exposure_points > 0 && <tr className="border-t border-hairline"><td className="py-1.5 text-ink" colSpan={3}>AI exposure ({s.label})</td><td className="py-1.5 text-right">−{s.exposure_points}</td></tr>}
            <tr className="border-t border-hairline-strong font-semibold text-ink"><td className="py-1.5" colSpan={3}>Score{s.capped ? ' (capped: under half the core skills)' : ''}</td><td className="py-1.5 text-right">{s.score}</td></tr>
          </tbody>
        </table>
      </div>
      <p className="text-graphite">{s.note} In the other scenario ({role.scenarios[other].label.toLowerCase()}) it is a <span className="text-ink">{role.scenarios[other].band.toLowerCase()}</span> at <span className="tabular-nums text-ink">{role.scenarios[other].score}</span>.</p>

      <div>
        <h4 className="text-xs font-medium text-graphite mb-1.5">Skills: your level vs what the role asks for</h4>
        <ul className="divide-y divide-hairline">
          {role.matched_skills.map(m => (
            <li key={m.skill_id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
              <span className="text-ink">{m.name} {m.is_core && <span className="text-xs text-graphite">(core)</span>}</span>
              <span className={`text-xs ${m.has_it ? 'text-action-ink font-medium' : 'text-graphite'}`}>
                {levelWord(m.user_level, data.levels)} · needs {levelWord(m.required_level, data.levels)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-1.5 text-xs text-graphite">
        <p>
          Market momentum: {Object.keys(role.momentum_skills).length > 0
            ? Object.entries(role.momentum_skills).map(([k, v]) => `${role.matched_skills.find(m => m.skill_id === k)?.name ?? k} ${v}`).join(', ')
            : 'no tracked core skill, so neutral'}. Source: {data.trend.source} · data to {data.trend.data_as_of}{data.trend.stale ? ' (stale)' : ''}.
        </p>
        <p>
          Based on O*NET occupation{' '}
          {role.source_url
            ? <a href={role.source_url} target="_blank" rel="noreferrer" className="text-action-ink hover:underline">{role.source_code} {role.source_title} <ExternalLink size={11} className="inline" aria-hidden="true" /></a>
            : <span className="text-ink">not confirmed yet (team to choose)</span>}.
        </p>
        {role.ai_use_evidence && (
          <p>
            AI use in this occupation: {role.ai_use_evidence.automation_pct.toFixed(0)}% of AI conversations about it were automation rather than help ({role.ai_use_evidence.source}, {role.ai_use_evidence.period}). Shown as evidence; it does not change the score.
          </p>
        )}
      </div>
    </div>
  )
}

function RoleCard({ role, rank, data }: { role: RankedRoleView; rank: number; data: RankingResponse }) {
  const [open, setOpen] = useState<'gap' | 'calc' | null>(rank === 1 ? 'gap' : null)
  const other: ScenarioName = data.scenario === 'moderate' ? 'fast' : 'moderate'
  const toggle = (what: 'gap' | 'calc') => setOpen(o => (o === what ? null : what))
  return (
    <Card data-reveal className="p-5 sm:p-6 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <span className="w-8 h-8 rounded-full bg-action-tint text-action-ink text-sm font-semibold flex items-center justify-center shrink-0 tabular-nums">{rank}</span>
          <div className="min-w-0">
            <h3 className="font-semibold text-ink text-lg leading-snug">{role.name}</h3>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <Tag tone={BAND_TONE[role.band]}>{role.band}</Tag>
              <Tag tone="linen">{RELATION[role.relation]} · {role.family_name}</Tag>
            </div>
          </div>
        </div>
        <div className="w-full sm:w-auto pl-11 sm:pl-0 sm:text-right">
          <div className="text-2xl font-semibold text-ink tabular-nums leading-none">{role.score}</div>
          <div className="text-xs text-graphite">match score</div>
          <div className="mt-1 text-xs text-graphite">{data.scenarios[other].label}: <span className="text-ink">{role.scenarios[other].band}</span> ({role.scenarios[other].score})</div>
        </div>
      </div>

      <Breakdown role={role} scenario={data.scenario} />

      <ul className="space-y-1 text-sm text-ink list-disc pl-5">{role.reasons.map(r => <li key={r}>{r}</li>)}</ul>
      {role.flags.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">{role.flags.map(f => <li key={f}><Tag tone="marigold" icon={TriangleAlert}>{f}</Tag></li>)}</ul>
      )}

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => toggle('gap')} aria-expanded={open === 'gap'} className={btn.ghost}>
          See my skills gap {open === 'gap' ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
        </button>
        <button type="button" onClick={() => toggle('calc')} aria-expanded={open === 'calc'} className={btn.text}>
          <Info size={14} aria-hidden="true" /> How this score was calculated
        </button>
      </div>
      {open === 'gap' && <div className="border-t border-hairline pt-4"><GapList role={role} /></div>}
      {open === 'calc' && <div className="border-t border-hairline pt-4"><Calculation role={role} data={data} /></div>}
    </Card>
  )
}

/** Ranked future roles with match score, gap and two scenarios (Domain 1 must-haves 3 and 6). */
export default function Matches() {
  const userId = useUserId()
  const [scenario, setScenario] = useState<ScenarioName>('moderate')
  const [data, setData] = useState<RankingResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [data?.scenario, data?.roles.length])

  useEffect(() => {
    getRanking(userId, scenario).then(d => { setData(d); setError(null) }).catch(() => setError('Could not load your matches.'))
  }, [userId, scenario])

  if (error) return <EmptyState title="Matches unavailable">{error}</EmptyState>
  if (!data) return <Loading what="your matches" />

  const roles = showAll ? data.roles : data.roles.slice(0, SHOWN)
  return (
    <div ref={root} className="max-w-3xl mx-auto space-y-6">
      <div data-reveal>
        <PageHeader
          title={<>Roles you could <Highlight>move into</Highlight></>}
          intro="Ranked from your skills, the market trend for those skills, the direction you chose and the time you have. You decide; this only suggests."
          aside={<ProvenanceTag kind="assumption">Estimates, not predictions</ProvenanceTag>}
        />
      </div>

      <Card data-reveal className="p-4 sm:p-5 space-y-3">
        <div role="radiogroup" aria-label="Future scenario" className="flex flex-wrap gap-2">
          {(Object.keys(data.scenarios) as ScenarioName[]).map(s => (
            <button
              key={s} type="button" role="radio" aria-checked={scenario === s} onClick={() => setScenario(s)}
              className={`rounded-full px-3.5 py-2 text-sm transition-colors duration-200 ${scenario === s ? 'bg-action-tint text-action-ink font-medium' : 'bg-surface border border-hairline-strong text-graphite hover:bg-linen'}`}
            >
              {data.scenarios[s].label}
            </button>
          ))}
        </div>
        <p className="text-sm text-graphite">{data.scenarios[scenario].description} Both scenarios are declared assumptions, so compare them rather than trusting one.</p>
      </Card>

      {data.empty_profile ? (
        <Card data-reveal className="p-6 space-y-3">
          <SectionTitle>Not enough to rank yet</SectionTitle>
          <p className="text-sm text-graphite">{data.message} Meanwhile, these roles are common first steps:</p>
          <ul className="flex flex-wrap gap-2">{data.starter_roles.map(r => <li key={r.role_id}><Tag tone="linen">{r.name}</Tag></li>)}</ul>
          <Link to="/start" className={btn.primary}>Add skills on your profile <ArrowRight size={16} aria-hidden="true" /></Link>
        </Card>
      ) : (
        <>
          <ol className="space-y-4">
            {roles.map((r, i) => <li key={r.role_id}><RoleCard role={r} rank={i + 1} data={data} /></li>)}
          </ol>
          {data.roles.length > SHOWN && (
            <button type="button" onClick={() => setShowAll(v => !v)} className={btn.outline}>
              {showAll ? `Show the top ${SHOWN}` : `Show all ${data.roles.length} roles`}
            </button>
          )}
        </>
      )}

      <p data-reveal className="text-xs text-graphite">
        Market trend: {data.trend.source} · data to {data.trend.data_as_of}{data.trend.stale ? ' (stale)' : ''} ·{' '}
        <Link to="/sources" className="text-action-ink hover:underline">all data sources</Link>. Bands come first: a score of 73 is not meaningfully better than 71.
      </p>
    </div>
  )
}
