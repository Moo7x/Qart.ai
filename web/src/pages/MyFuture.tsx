import { useEffect, useState } from 'react'
import { getPath, getRecommendation, getSnapshots, searchResources } from '../api'
import { ResourceList, SkillResources } from '../components/ResourceList'
import type { PathPlan, Recommendation, RoleRecommendation, Scenario, SearchResponse, Snapshot } from '../types'
import { SKILL_NAMES } from '../skillNames'

const SDG_COLORS: Record<string, string> = {
  '4.4': 'bg-red-100 text-red-700',
  '8.2': 'bg-orange-100 text-orange-700',
  '8.5': 'bg-yellow-100 text-yellow-700',
  '5.5': 'bg-pink-100 text-pink-700',
}


const STATE_LABELS: Record<string, string> = {
  demonstrated_independently: 'Demonstrated',
  observed_with_help: 'Observed',
  self_reported: 'Self-reported',
  insufficient_evidence: 'Not yet evidenced',
}

const ALLOC_LABELS: Record<string, { label: string; color: string }> = {
  human: { label: 'Human', color: 'bg-green-100 text-green-700' },
  ai_drafts_human_reviews: { label: 'AI drafts → Human reviews', color: 'bg-blue-100 text-blue-700' },
  ai: { label: 'AI', color: 'bg-purple-100 text-purple-700' },
}

const KIND_BADGES: Record<string, string> = {
  evidence: 'bg-blue-50 text-blue-700 border-blue-200',
  assumption: 'bg-amber-50 text-amber-700 border-amber-200',
  synthetic: 'bg-gray-50 text-gray-600 border-gray-200',
}

function FactorBar({ label, value, penalty = false }: { label: string; value: number; penalty?: boolean }) {
  const pct = Math.round(value * 100)
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs text-gray-500">
        <span>{label}{penalty ? ' (penalty)' : ''}</span>
        <span className={penalty ? 'text-red-600' : 'text-gray-700'}>{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${penalty ? 'bg-red-400' : 'bg-indigo-500'}`}
          style={{ width: `${pct}%` }}
        />
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
  const [openSkill, setOpenSkill] = useState<string | null>(null)
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 text-sm font-bold flex items-center justify-center">
            {role.rank}
          </span>
          <div>
            <div className="font-semibold text-gray-900 flex items-center gap-2">
              {role.title ?? role.role_id.replace(/_/g, ' ')}
              {role.close_match && (
                <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium">Close match</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5 flex-wrap">
              {role.time_to_ready && (
                <span className="text-xs text-indigo-600 font-medium">
                  ~{role.time_to_ready.hours} h to ready · {role.time_to_ready.weeks_at_current_budget} wk at your weekly hours
                </span>
              )}
              {role.fit !== undefined && (
                <span className="text-xs text-gray-500">Fit {role.fit.toFixed(2)} (indicator, not a probability)</span>
              )}
              {role.outlook && (
                <span
                  title={`${role.outlook.because} · ${role.outlook.basis}`}
                  className={`text-xs px-1.5 py-0.5 rounded font-medium ${role.outlook.label === 'AI-era role' ? 'bg-emerald-100 text-emerald-700' : role.outlook.label === 'stable' ? 'bg-gray-100 text-gray-600' : 'bg-orange-100 text-orange-700'}`}
                >
                  {role.outlook.label}
                </span>
              )}
            </div>
            {role.score_note && (
              <div className="text-xs text-gray-400 italic mt-0.5">{role.score_note}</div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {role.sdg_targets?.map(t => (
            <span key={t} className={`text-xs px-1.5 py-0.5 rounded font-medium ${SDG_COLORS[t] ?? 'bg-gray-100 text-gray-600'}`}>
              SDG {t}
            </span>
          ))}
          <span className="text-indigo-400 text-sm font-medium">{expanded ? '▲' : '→'}</span>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-5">
          <button
            onClick={onPlan}
            disabled={planned}
            className={`text-sm px-3 py-1.5 rounded-lg font-medium ${planned ? 'bg-gray-100 text-gray-500' : 'bg-indigo-600 text-white hover:bg-indigo-700'}`}
          >
            {planned ? 'Your learning path below is for this role' : 'Plan my learning path for this role'}
          </button>

          {/* Score breakdown */}
          <div>
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Score breakdown</div>
            <div className="space-y-2">
              <FactorBar label="Coverage" value={role.factors.coverage} />
              <FactorBar label="Confidence" value={role.factors.confidence} />
              <FactorBar label="Interest" value={role.factors.interest} />
              <FactorBar label="Effort" value={role.factors.effort} penalty />
            </div>
            <div className="mt-2 text-xs text-gray-400 font-mono bg-gray-50 rounded px-2 py-1">
              {role.formula}
            </div>
          </div>

          {/* Gap */}
          {role.gap.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Skill gaps</div>
              <div className="space-y-1.5">
                {role.gap.map(g => (
                  <div key={g.skill_id}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-700">{SKILL_NAMES[g.skill_id] ?? g.skill_id.replace(/_/g, ' ')}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">{STATE_LABELS[g.state]}</span>
                        <span className="text-xs text-gray-400">weight {Math.round(g.weight * 100)}%</span>
                        <button
                          onClick={() => setOpenSkill(openSkill === g.skill_id ? null : g.skill_id)}
                          className="text-xs text-indigo-600 hover:underline"
                        >
                          {openSkill === g.skill_id ? 'hide courses' : 'find courses'}
                        </button>
                      </div>
                    </div>
                    {openSkill === g.skill_id && (
                      <div className="mt-1.5 mb-2"><SkillResources skillId={g.skill_id} /></div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Requirement card */}
          <div>
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Requirement card</div>
            <div className="text-xs text-gray-400 mb-2 italic">
              How this role's tasks are allocated under the selected scenario, and why the skill weights changed.
            </div>
            <div className="space-y-2">
              {role.requirement_card.tasks.map((t, i) => {
                const alloc = ALLOC_LABELS[t.allocation] ?? { label: t.allocation, color: 'bg-gray-100 text-gray-600' }
                return (
                  <div key={i} className="flex items-center justify-between text-xs bg-gray-50 rounded px-3 py-2">
                    <span className="text-gray-700">{t.task}</span>
                    <span className={`px-2 py-0.5 rounded font-medium ${alloc.color}`}>{alloc.label}</span>
                  </div>
                )
              })}
            </div>
            {role.requirement_card.weights.length > 0 && (
              <div className="mt-3 space-y-1">
                <div className="text-xs text-gray-500 font-medium">Weight changes</div>
                {role.requirement_card.weights.map((w, i) => (
                  <div key={i} className="text-xs text-gray-600 bg-amber-50 border border-amber-100 rounded px-3 py-2">
                    <span className="font-medium">{SKILL_NAMES[w.skill_id] ?? w.skill_id}</span>
                    : base {Math.round(w.base * 100)}% → scenario {Math.round(w.scenario * 100)}%
                    <div className="text-gray-400 mt-0.5">
                      <span className="bg-amber-100 text-amber-700 border border-amber-200 px-1 py-0.5 rounded text-xs mr-1">assumption</span>
                      {w.because}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {/* Evidence sources */}
            <div className="mt-3 space-y-1">
              {role.requirement_card.evidence.map((e, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className={`px-1.5 py-0.5 rounded border font-medium ${KIND_BADGES[e.kind ?? 'evidence']}`}>
                    {e.kind ?? 'evidence'}
                  </span>
                  <a href={e.url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline truncate">
                    {e.label}
                  </a>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function PathTimeline({ plan }: { plan: PathPlan }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm text-gray-600">
        <span className="font-medium">{plan.total_hours}h total · {plan.weeks} weeks at {plan.weekly_hours}h/week</span>
        <span className="text-xs text-gray-400">Weighted gap left after this path (worse scenario): {plan.worst_case_gap.toFixed(2)}</span>
      </div>
      <div className="relative space-y-0">
        <div className="absolute left-3 top-3 bottom-3 w-px bg-indigo-100" aria-hidden="true" />
        {plan.steps.map(step => (
          <div key={step.order} className="relative flex items-start gap-3 bg-white border border-gray-200 rounded-xl p-3 mb-2">
            <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 relative z-10">
              {step.order}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-gray-900 text-sm">{step.title}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${step.type === 'checkin' ? 'bg-purple-100 text-purple-700' : step.type === 'course' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                  {step.type.replace('_', ' ')}
                </span>
                {step.cost === 'free' && <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">free</span>}
                {step.sdg_targets?.map(t => (
                  <span key={t} className={`text-xs px-1 py-0.5 rounded font-medium ${SDG_COLORS[t] ?? 'bg-gray-100 text-gray-600'}`}>SDG {t}</span>
                ))}
              </div>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                <span>{step.hours}h</span>
                {step.url && <a href={step.url} target="_blank" rel="noreferrer" className="text-indigo-500 hover:underline">Open →</a>}
                {step.because && <span className="text-gray-400 italic">· {step.because}</span>}
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {step.skills.map(sk => (
                  <span key={sk} className="text-xs bg-gray-50 text-gray-500 border border-gray-200 px-1.5 py-0.5 rounded">
                    {SKILL_NAMES[sk] ?? sk.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

}

export default function MyFuture() {
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
      setFound(await searchResources(text.trim(), undefined, 6))
    } finally {
      setSearching(false)
    }
  }

  useEffect(() => {
    getSnapshots().then(setSnapshots).catch(() => {})
  }, [])

  useEffect(() => {
    Promise.all([
      getRecommendation('u_aina', scenario),
      getPath('u_aina', pathRole),
    ]).then(([rec, p]) => {
      setRecommendation(rec)
      setPath(p)
      setLoading(false)
    })
  }, [scenario, pathRole])

  const pathRoleTitle = path
    ? recommendation?.roles.find(r => r.role_id === path.target_role_id)?.title ?? path.target_role_id
    : ''

  if (loading) return <div className="text-gray-400 text-center py-12">Loading…</div>

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">My future</h1>
        <span className="text-xs text-gray-400">Recommendations, not decisions</span>
      </div>

      {/* Snapshot card — reads source/release_date/period from GET /api/snapshots */}
      {snapshots.length > 0 && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-xs font-medium text-blue-800">External evidence</span>
            <span className="bg-blue-100 text-blue-700 border border-blue-200 text-xs px-1.5 py-0.5 rounded font-medium">Historical data replay</span>
            {recommendation?.assumptions_version !== undefined && (
              <span className="text-xs text-gray-500">Assumptions version {recommendation.assumptions_version}</span>
            )}
          </div>
          {snapshots.map(snap => (
            <p key={snap.id} className="text-sm text-blue-700">
              {snap.source} · {snap.release_date} release · {snap.period}
            </p>
          ))}
          <p className="text-xs text-blue-500 mt-0.5">
            Signal data informs skill weight assumptions. Usage ≠ replacement — see requirement card for how.
          </p>
        </div>
      )}

      {/* Scenario toggle */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600 font-medium">Scenario:</span>
        {(['assistive', 'agentic'] as Scenario[]).map(s => (
          <button
            key={s}
            onClick={() => { setScenario(s); setLoading(true) }}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${scenario === s ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1">
          <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded font-medium">assumption</span>
          <span className="text-xs text-gray-400">company adoption scenario</span>
        </div>
      </div>

      {/* Role recommendations */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Suggested future roles</h2>
        <p className="text-xs text-gray-400">
          These are suitability indicators based on your evidence, not probabilities. The system recommends; you decide.
        </p>
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

      {/* Learning path */}
      {path && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">Your learning path · {pathRoleTitle}</h2>
            <span className="text-xs text-gray-400">
              {pathRole ? 'Role you chose' : 'Best role across both scenarios'} · robust across both scenarios
            </span>
          </div>
          <PathTimeline plan={path} />
          <p className="text-xs text-gray-400">
            Course coverage is an assumption until new evidence arrives. Hours are estimates.
          </p>
        </div>
      )}

      {/* Resource search (RunPod hybrid search when available) */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Search learning resources and work evidence</h2>
        <form
          onSubmit={e => { e.preventDefault(); runSearch(query) }}
          className="flex gap-2"
        >
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="e.g. challenge adjustments without documents"
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <button type="submit" disabled={searching} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium">
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        <p className="text-xs text-gray-400">
          Searches verified courses and O*NET task statements. Every result carries its source and date.
        </p>
        {found && <ResourceList response={found} />}
      </div>
    </div>
  )
}
