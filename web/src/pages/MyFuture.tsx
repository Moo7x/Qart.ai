import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Clock, ExternalLink, Search } from 'lucide-react'
import { getPath, getRecommendation, getSnapshots, searchResources } from '../api'
import { ResourceList, SkillResources } from '../components/ResourceList'
import { useUserId } from '../persona'
import type { PathPlan, Recommendation, RoleRecommendation, Scenario, SearchResponse, Snapshot } from '../types'
import { skillName } from '../skillNames'
import { asProvenance, btn, Card, input as inputCls, label, Loading, PageHeader, ProvenanceTag, SectionTitle, STATE_META, Tag, type Tone } from '../ui'

const SEARCH_RETRIES = 4 // a GPU cold start took ~100 s; 4 × 25 s covers it
const SEARCH_RETRY_MS = 25000

const ALLOC_META: Record<string, { label: string; tone: Tone }> = {
  human: { label: 'Human', tone: 'action' },
  ai_drafts_human_reviews: { label: 'AI drafts → human reviews', tone: 'marigold' },
  ai: { label: 'AI', tone: 'linen' },
}

const STEP_TONE: Record<string, Tone> = { checkin: 'coral', course: 'action' }

function FactorBar({ label: name, value, penalty = false }: { label: string; value: number; penalty?: boolean }) {
  // Role-fit factors (not skill mastery), so a bar is allowed here.
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-graphite">
        <span>{name}{penalty ? ' (counts against)' : ''}</span>
        <span className="tabular-nums text-ink">{pct}%</span>
      </div>
      <div className="h-1.5 bg-linen rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${penalty ? 'bg-coral' : 'bg-action'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function RoleCard({ role, expanded, onToggle, planned, onPlan }: {
  role: RoleRecommendation
  expanded: boolean
  onToggle: () => void
  planned: boolean
  onPlan: () => void
}) {
  const detailsId = `role-${role.role_id}`
  const [openSkill, setOpenSkill] = useState<string | null>(null)
  return (
    <Card className="overflow-hidden">
      <button
        type="button" onClick={onToggle} aria-expanded={expanded} aria-controls={detailsId}
        className="w-full text-left flex items-start justify-between gap-3 p-5 hover:bg-canvas transition-colors duration-200"
      >
        <div className="flex items-start gap-3 min-w-0">
          <span className="w-8 h-8 rounded-full bg-action-tint text-action-ink text-sm font-semibold flex items-center justify-center shrink-0 tabular-nums">
            {role.rank}
          </span>
          <div className="min-w-0">
            <div className="font-semibold text-ink flex items-center gap-2 flex-wrap">
              {role.title ?? role.role_id.replace(/_/g, ' ')}
              {role.close_match && <Tag tone="marigold">Close match</Tag>}
              {role.outlook && (
                <Tag tone={role.outlook.label === 'AI-era role' ? 'action' : role.outlook.label === 'stable' ? 'linen' : 'coral'} title={`${role.outlook.because} · ${role.outlook.basis}`}>
                  {role.outlook.label}
                </Tag>
              )}
            </div>
            <div className="flex items-center gap-x-3 gap-y-1 mt-1 flex-wrap text-sm">
              {role.time_to_ready && (
                <span className="inline-flex items-center gap-1 text-action-ink font-medium tabular-nums">
                  <Clock size={14} aria-hidden="true" />
                  ~{role.time_to_ready.hours} h to ready · {role.time_to_ready.weeks_at_current_budget} wk at your pace
                </span>
              )}
              {role.fit !== undefined && (
                <span className="text-graphite tabular-nums">Fit {role.fit.toFixed(2)} <span className="text-xs">(indicator, not a probability)</span></span>
              )}
            </div>
            {role.score_note && <div className="text-xs text-stone italic mt-1">{role.score_note}</div>}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="hidden sm:flex gap-1">
            {role.sdg_targets?.map(t => <Tag key={t} tone="linen">SDG {t}</Tag>)}
          </span>
          {expanded ? <ChevronUp size={20} className="text-graphite" aria-hidden="true" /> : <ChevronDown size={20} className="text-graphite" aria-hidden="true" />}
        </div>
      </button>

      {expanded && (
        <div id={detailsId} className="border-t border-hairline p-5 space-y-6">
          <button onClick={onPlan} disabled={planned} className={planned ? `${btn.ghost} disabled:opacity-100` : btn.primary}>
            {planned ? 'Your learning path below is for this role' : 'Plan my learning path for this role'}
          </button>
          <div>
            <div className={`${label} mb-3`}>Why this rank</div>
            <div className="space-y-3">
              <FactorBar label="Coverage" value={role.factors.coverage} />
              <FactorBar label="Confidence" value={role.factors.confidence} />
              <FactorBar label="Interest" value={role.factors.interest} />
              <FactorBar label="Effort" value={role.factors.effort} penalty />
            </div>
            <div className="mt-3 text-xs text-graphite font-mono bg-linen rounded-sm px-3 py-2 overflow-x-auto">{role.formula}</div>
          </div>

          {role.gap.length > 0 && (
            <div>
              <div className={`${label} mb-2`}>Skills to build</div>
              <ul className="space-y-2">
                {role.gap.map(g => (
                  <li key={g.skill_id}>
                    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm">
                      <span className="text-ink">{skillName(g.skill_id)}</span>
                      <span className="flex items-center gap-2">
                        <Tag tone={STATE_META[g.state].tone}>{STATE_META[g.state].label}</Tag>
                        <span className="text-xs text-graphite tabular-nums">weight {Math.round(g.weight * 100)}%</span>
                        <button
                          onClick={() => setOpenSkill(openSkill === g.skill_id ? null : g.skill_id)}
                          aria-expanded={openSkill === g.skill_id}
                          className="text-xs text-action-ink hover:underline"
                        >
                          {openSkill === g.skill_id ? 'Hide courses' : 'Find courses'}
                        </button>
                      </span>
                    </div>
                    {openSkill === g.skill_id && <div className="mt-2 mb-1"><SkillResources skillId={g.skill_id} /></div>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <div className={`${label} mb-1`}>Requirement card</div>
            <p className="text-xs text-stone mb-3">How this role's tasks are split under the selected scenario, and why the skill weights changed.</p>
            <ul className="space-y-1.5">
              {role.requirement_card.tasks.map((t, i) => {
                const alloc = ALLOC_META[t.allocation] ?? { label: t.allocation, tone: 'linen' as Tone }
                return (
                  <li key={i} className="flex items-center justify-between gap-3 text-sm bg-canvas rounded-sm px-3 py-2">
                    <span className="text-ink">{t.task}</span>
                    <Tag tone={alloc.tone}>{alloc.label}</Tag>
                  </li>
                )
              })}
            </ul>
            {role.requirement_card.weights.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className={label}>Weight changes</div>
                {role.requirement_card.weights.map((w, i) => (
                  <div key={i} className="text-sm bg-coral-tint/50 rounded-sm px-3 py-2">
                    <div className="text-ink tabular-nums">
                      <span className="font-medium">{skillName(w.skill_id)}</span>: base {Math.round(w.base * 100)}% → scenario {Math.round(w.scenario * 100)}%
                    </div>
                    <div className="mt-1 flex items-start gap-2 text-xs text-graphite">
                      <ProvenanceTag kind="assumption" />
                      <span>{w.because}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <ul className="mt-4 space-y-1.5">
              {role.requirement_card.evidence.map((e, i) => (
                <li key={i} className="flex items-center gap-2 text-sm min-w-0">
                  <ProvenanceTag kind={asProvenance(e.kind)} />
                  <a href={e.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-action-ink hover:underline truncate">
                    {e.label} <ExternalLink size={12} aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </Card>
  )
}

function PathTimeline({ plan }: { plan: PathPlan }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="font-medium text-ink tabular-nums">{plan.total_hours} h total · {plan.weeks} weeks at {plan.weekly_hours} h/week</span>
        <span className="text-xs text-graphite tabular-nums">Gap left after this path (worse scenario): {plan.worst_case_gap.toFixed(2)}</span>
      </div>
      <ol className="relative">
        <div className="absolute left-4 top-4 bottom-4 w-px bg-hairline-strong" aria-hidden="true" />
        {plan.steps.map(step => (
          <li key={step.order} className="relative flex items-start gap-4 pb-3">
            <span className="w-8 h-8 rounded-full bg-surface border border-hairline-strong text-ink text-sm font-semibold flex items-center justify-center shrink-0 relative z-10 tabular-nums">
              {step.order}
            </span>
            <Card className="flex-1 min-w-0 p-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-ink">{step.title}</span>
                <Tag tone={STEP_TONE[step.type] ?? 'linen'}>{step.type.replace('_', ' ')}</Tag>
                {step.cost === 'free' && <Tag tone="mocha">free</Tag>}
                {step.sdg_targets?.map(t => <Tag key={t} tone="linen">SDG {t}</Tag>)}
              </div>
              <div className="flex items-center gap-2 mt-1.5 text-sm text-graphite flex-wrap">
                <span className="inline-flex items-center gap-1 tabular-nums"><Clock size={14} aria-hidden="true" /> {step.hours} h</span>
                {step.url && (
                  <a href={step.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-action-ink hover:underline">
                    Open <ExternalLink size={12} aria-hidden="true" />
                  </a>
                )}
                {step.because && <span className="italic">· {step.because}</span>}
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {step.skills.map(sk => <Tag key={sk} tone="outline">{skillName(sk)}</Tag>)}
              </div>
            </Card>
          </li>
        ))}
      </ol>
    </div>
  )
}

export default function MyFuture() {
  const userId = useUserId()
  const [scenario, setScenario] = useState<Scenario>('assistive')
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [path, setPath] = useState<PathPlan | null>(null)
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [expandedRole, setExpandedRole] = useState<string | null>(null)
  const [pathRole, setPathRole] = useState<string | null>(null) // null: server picks the best role
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [found, setFound] = useState<SearchResponse | null>(null)
  const [searching, setSearching] = useState(false)

  const runSearch = async (text: string) => {
    if (text.trim().length < 2) return
    setSearching(true)
    try {
      const first = await searchResources(text.trim(), undefined, 6)
      setFound(first)
      // While the GPU worker starts, ask again so the keyword results get replaced by GPU results.
      let latest = first
      for (let attempt = 0; attempt < SEARCH_RETRIES && latest.engine === 'keyword' && latest.note.includes('starting up'); attempt++) {
        await new Promise(resolve => window.setTimeout(resolve, SEARCH_RETRY_MS))
        latest = await searchResources(text.trim(), undefined, 6)
        setFound(latest)
      }
    } finally {
      setSearching(false)
    }
  }

  useEffect(() => {
    getSnapshots().then(setSnapshots).catch(() => {})
  }, [])

  useEffect(() => {
    Promise.all([
      getRecommendation(userId, scenario),
      getPath(userId, pathRole),
    ]).then(([rec, p]) => {
      setRecommendation(rec)
      setPath(p)
      setLoading(false)
    })
  }, [scenario, pathRole, userId])

  const pathRoleTitle = path
    ? recommendation?.roles.find(r => r.role_id === path.target_role_id)?.title ?? path.target_role_id
    : ''

  if (loading) return <Loading what="your future roles" />

  return (
    <div className="max-w-3xl mx-auto space-y-10">
      <PageHeader title="My future" intro="Roles your evidence points toward, and a path to get there. The system recommends; you decide." />

      {/* Snapshot card: reads source/release_date/period from GET /api/snapshots */}
      {snapshots.length > 0 && (
        <div className="bg-mocha-tint rounded-lg p-5">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span className="text-sm font-semibold text-mocha-ink">External evidence</span>
            <Tag tone="linen">Historical data replay</Tag>
            {recommendation?.assumptions_version !== undefined && (
              <ProvenanceTag kind="assumption">v{recommendation.assumptions_version}</ProvenanceTag>
            )}
          </div>
          {snapshots.map(snap => (
            <p key={snap.id} className="text-sm text-ink tabular-nums">{snap.source} · {snap.release_date} release · {snap.period}</p>
          ))}
          <p className="text-xs text-mocha-ink mt-2">Usage data informs the skill-weight assumptions. Usage is not replacement; each requirement card shows how.</p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-ink font-medium" id="scenario-label">Company AI scenario</span>
        <div role="radiogroup" aria-labelledby="scenario-label" className="inline-flex bg-linen rounded-md p-1">
          {(['assistive', 'agentic'] as Scenario[]).map(s => (
            <button
              key={s} role="radio" aria-checked={scenario === s}
              onClick={() => { setScenario(s); setLoading(true) }}
              className={`px-4 py-1.5 rounded-sm text-sm transition-colors duration-200 ${scenario === s ? 'bg-surface text-ink font-medium shadow-[0_1px_2px_rgb(0_0_0/0.06)]' : 'text-graphite hover:text-ink'}`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <ProvenanceTag kind="assumption">company adoption scenario</ProvenanceTag>
      </div>

      <section>
        <SectionTitle>Roles that fit your evidence</SectionTitle>
        <p className="text-sm text-graphite mb-4">Suitability indicators from your evidence, not probabilities.</p>
        <div className="space-y-3">
          {recommendation?.roles.map(role => (
            <RoleCard
              key={role.role_id}
              role={role}
              expanded={expandedRole === role.role_id}
              onToggle={() => setExpandedRole(expandedRole === role.role_id ? null : role.role_id)}
              planned={path?.target_role_id === role.role_id}
              onPlan={() => setPathRole(role.role_id)}
            />
          ))}
        </div>
      </section>

      {path && (
        <section>
          <SectionTitle aside={<Tag tone="linen">{pathRole ? 'Role you chose' : 'Best role across both scenarios'} · works in both</Tag>}>
            Your learning path · {pathRoleTitle}
          </SectionTitle>
          <PathTimeline plan={path} />
          <p className="text-xs text-graphite mt-2">Course coverage is an assumption until new evidence arrives. Hours are estimates.</p>
        </section>
      )}

      {/* Resource search (RunPod hybrid search when available) */}
      <section>
        <SectionTitle>Search learning resources and work evidence</SectionTitle>
        <form onSubmit={e => { e.preventDefault(); runSearch(query) }} className="flex gap-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="e.g. challenge adjustments without documents"
            aria-label="Search learning resources"
            className={`${inputCls} flex-1 min-w-0`}
          />
          <button type="submit" disabled={searching} className={btn.outline}>
            <Search size={16} aria-hidden="true" /> {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        <p className="text-xs text-graphite mt-2">Searches verified courses and O*NET task statements. Every result carries its source and date.</p>
        {found && <div className="mt-4"><ResourceList response={found} /></div>}
      </section>
    </div>
  )
}
