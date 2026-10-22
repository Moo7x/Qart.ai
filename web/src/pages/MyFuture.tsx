import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BadgeCheck, ChevronDown, ChevronUp, Clock, ExternalLink } from 'lucide-react'
import FlowSteps from '../components/FlowSteps'
import { useReveal } from '../motion'
import { getRecommendation, getRoles, getSnapshots } from '../api'
import { SkillResources } from '../components/ResourceList'
import { useUserId } from '../persona'
import { SCENARIO_LABEL, SCENARIOS } from '../scenarios'
import type { Recommendation, Role, RoleRecommendation, Scenario, Snapshot } from '../types'
import { skillName } from '../skillNames'
import { asProvenance, btn, Card, Highlight, label, Loading, NextStepCard, PageHeader, ProvenanceTag, SectionTitle, STATE_META, Tag, type Tone } from '../ui'

const ALLOC_META: Record<string, { label: string; tone: Tone }> = {
  human: { label: 'Human', tone: 'action' },
  ai_drafts_human_reviews: { label: 'AI drafts → human reviews', tone: 'marigold' },
  ai: { label: 'AI', tone: 'linen' },
}


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

function RoleCard({ role, info, expanded, onToggle }: {
  role: RoleRecommendation
  info?: Role
  expanded: boolean
  onToggle: () => void
}) {
  // Skills outside gap[] have full credit, i.e. were shown on the person's own (engine: gap_list).
  const gapIds = new Set(role.gap.map(g => g.skill_id))
  const shown = (info?.skills ?? []).map(s => s.skill_id).filter(id => !gapIds.has(id))
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
            {info?.summary && <p className="mt-1.5 text-sm text-graphite">{info.summary}</p>}
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
          <Link to={`/pathway?role=${encodeURIComponent(role.role_id)}`} className={btn.outline}>
            Build this pathway <ArrowRight size={16} aria-hidden="true" />
          </Link>
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

          {shown.length > 0 && (
            <div>
              <div className={`${label} mb-2`}>Already shown on your own</div>
              <div className="flex flex-wrap gap-1.5">
                {shown.map(id => <Tag key={id} tone="action" icon={BadgeCheck}>{skillName(id)}</Tag>)}
              </div>
            </div>
          )}

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

export default function MyFuture() {
  const userId = useUserId()
  const [scenario, setScenario] = useState<Scenario>('assistive')
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [roles, setRoles] = useState<Record<string, Role>>({})
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [expandedRole, setExpandedRole] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [loading])

  useEffect(() => {
    getSnapshots().then(setSnapshots).catch(() => {})
    getRoles().then(list => setRoles(Object.fromEntries(list.map(r => [r.id, r])))).catch(() => {})
  }, [])

  useEffect(() => {
    getRecommendation(userId, scenario).then(rec => {
      setRecommendation(rec)
      setLoading(false)
    })
  }, [scenario, userId])

  if (loading) return <Loading what="your role matches" />

  const top = recommendation?.roles[0]
  const latest = snapshots[snapshots.length - 1]

  return (
    <div ref={root} className="max-w-3xl mx-auto space-y-8">
      <FlowSteps />
      <div data-reveal>
        <PageHeader
          title={<>Roles that fit your <Highlight>evidence</Highlight></>}
          intro="Ranked from your evidence, your interests and the company's AI assumptions. Open a role to see exactly how its rank was built. The system recommends; you decide."
        />
      </div>

      <div data-reveal className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-ink font-medium" id="scenario-label">Company AI scenario</span>
        <div role="radiogroup" aria-labelledby="scenario-label" className="inline-flex flex-wrap bg-linen rounded-md p-1">
          {SCENARIOS.map(s => (
            <button
              key={s} role="radio" aria-checked={scenario === s}
              onClick={() => { setScenario(s); setLoading(true) }}
              className={`px-4 py-1.5 rounded-sm text-sm transition-colors duration-200 ${scenario === s ? 'bg-surface text-ink font-medium shadow-[0_1px_2px_rgb(0_0_0/0.06)]' : 'text-graphite hover:text-ink'}`}
            >
              {SCENARIO_LABEL[s]}
            </button>
          ))}
        </div>
        {recommendation && <ProvenanceTag kind="assumption">company assumptions v{recommendation.assumptions_version}</ProvenanceTag>}
      </div>

      {top && (
        <div data-reveal>
          <NextStepCard
            eyebrow="Your closest role right now"
            title={top.title ?? top.role_id}
            action={<Link to={`/pathway?role=${encodeURIComponent(top.role_id)}`} className={`${btn.primary} whitespace-nowrap`}>Build this pathway <ArrowRight size={16} aria-hidden="true" /></Link>}
          >
            {top.time_to_ready
              ? `About ${top.time_to_ready.hours} hours of learning, or ${top.time_to_ready.weeks_at_current_budget} weeks at your weekly pace. Estimates, not a promise.`
              : 'Open the role below to see why it ranks first.'}
          </NextStepCard>
        </div>
      )}

      <section data-reveal>
        <SectionTitle>Ranked roles</SectionTitle>
        <p className="text-sm text-graphite mb-4">Fit is a suitability indicator from your evidence, not a probability.</p>
        <div className="space-y-3">
          {recommendation?.roles.map(role => (
            <RoleCard
              key={role.role_id}
              role={role}
              info={roles[role.role_id]}
              expanded={expandedRole === role.role_id}
              onToggle={() => setExpandedRole(expandedRole === role.role_id ? null : role.role_id)}
            />
          ))}
        </div>
      </section>

      {latest && (
        <p data-reveal className="text-xs text-graphite">
          External evidence behind the assumptions: {latest.source} · {latest.release_date} release · period {latest.period}.{' '}
          <Link to="/signals" className="text-action-ink hover:underline">See the signals</Link>
        </p>
      )}
    </div>
  )
}
