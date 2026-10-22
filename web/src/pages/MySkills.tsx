import { useEffect, useState } from 'react'
import { getSkills } from '../api'
import { useUserId } from '../persona'
import type { SkillState } from '../types'
import { SKILL_NAMES } from '../skillNames'

const STATE_COLORS: Record<string, string> = {
  demonstrated_independently: 'bg-green-100 text-green-800 border-green-200',
  observed_with_help: 'bg-blue-100 text-blue-800 border-blue-200',
  self_reported: 'bg-amber-100 text-amber-700 border-amber-200',
  insufficient_evidence: 'bg-gray-100 text-gray-500 border-gray-200',
}

const STATE_LABELS: Record<string, string> = {
  demonstrated_independently: 'Demonstrated independently',
  observed_with_help: 'Observed with help',
  self_reported: 'Self-reported',
  insufficient_evidence: 'Insufficient evidence',
}

const OUTCOME_ICONS: Record<string, { icon: string; label: string; color: string; badge: string }> = {
  success: { icon: '✓', label: 'success', color: 'text-green-600', badge: 'bg-green-100 text-green-700 border-green-200' },
  missed_then_found: { icon: '◑', label: 'missed, then found', color: 'text-purple-600', badge: 'bg-purple-100 text-purple-700 border-purple-200' },
  failure: { icon: '✗', label: 'missed', color: 'text-red-600', badge: 'bg-red-100 text-red-700 border-red-200' },
}


function HelpBadge({ level }: { level: number }) {
  const labels = ['no help', 'question', 'hint', 'explanation', 'answer shown']
  const colors = ['bg-green-100 text-green-700', 'bg-blue-100 text-blue-700', 'bg-amber-100 text-amber-700', 'bg-orange-100 text-orange-700', 'bg-red-100 text-red-700']
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${colors[level] ?? colors[0]}`}>
      {labels[level] ?? 'unknown'}
    </span>
  )
}

function SkillCard({ skill }: { skill: SkillState }) {
  const [expanded, setExpanded] = useState(false)
  const [flagged, setFlagged] = useState(false)

  return (
    <div className={`rounded-xl border p-4 bg-white ${STATE_COLORS[skill.state].split(' ').slice(2).join(' ')}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-900">
              {SKILL_NAMES[skill.skill_id] ?? skill.skill_id.replace(/_/g, ' ')}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${STATE_COLORS[skill.state]}`}>
              {STATE_LABELS[skill.state]}
            </span>
          </div>
          <p className="text-sm text-gray-600 mt-1">{skill.why}</p>
          {skill.next_to_confirm && (
            <p className="text-xs text-indigo-600 mt-1">Next: {skill.next_to_confirm}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {/* Reality gauge: self-rating label only, no percentage */}
          {skill.self_confidence != null && (
            <div className="text-right">
              <div className="text-xs text-gray-400">Self-rating</div>
              <div className="text-sm font-medium text-gray-600">
                {Math.round(skill.self_confidence * 10)}/10
              </div>
            </div>
          )}
          <button
            onClick={() => setExpanded(e => !e)}
            className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
          >
            {expanded ? '▲ hide' : '▼ trail'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-gray-100 pt-3 space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Evidence trail</div>
          {skill.evidence_trail.length === 0 ? (
            <p className="text-xs text-gray-400">No cases yet.</p>
          ) : (
            skill.evidence_trail.map((item, i) => {
              const o = OUTCOME_ICONS[item.outcome] ?? OUTCOME_ICONS.failure
              const counted = item.counted !== false
              return (
                <div key={i} className={`flex items-center gap-2 text-xs flex-wrap ${!counted ? 'opacity-50' : ''}`}>
                  <span className="text-gray-700 font-medium">{item.case_id}</span>
                  <span className={`px-1.5 py-0.5 rounded border font-medium ${o.badge}`}>{o.icon} {o.label}</span>
                  <HelpBadge level={item.help_level} />
                  {!counted && <span className="text-gray-400 italic">(not counted)</span>}
                  {item.note && <span className="text-gray-400 italic">{item.note}</span>}
                </div>
              )
            })
          )}
          <div className="text-xs text-gray-400 pt-1">
            {skill.counted_events} counted event{skill.counted_events !== 1 ? 's' : ''} ·{' '}
            {skill.independent_successes} independent success{skill.independent_successes !== 1 ? 'es' : ''}
          </div>

          {/* Flag button */}
          <div className="pt-2 border-t border-gray-100">
            <button
              onClick={() => setFlagged(f => !f)}
              className={`text-xs px-3 py-1 rounded border transition-colors ${flagged ? 'bg-amber-50 border-amber-300 text-amber-700' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}
            >
              {flagged ? '⚑ Flagged as unclear' : '⚑ Flag as companion error / unclear case'}
            </button>
            {flagged && (
              <p className="text-xs text-amber-600 mt-1">
                Flagged events don't count toward or against this skill. A senior will review.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function MySkills() {
  const userId = useUserId()
  const [skills, setSkills] = useState<SkillState[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSkills(userId).then(s => { setSkills(s); setLoading(false) })
  }, [userId])

  if (loading) return <div className="text-gray-400 text-center py-12">Loading…</div>

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">My skills</h1>
        <span className="text-xs text-gray-400">Evidence states, not scores</span>
      </div>

      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 text-sm text-indigo-800">
        <strong>How this works:</strong> States are based on what you've done in cases, not a percentage.
        "Demonstrated independently" requires ≥2 no-help successes (including a check-in) on different cases in separate sessions.
        Help level is recorded as evidence, not a penalty.
      </div>

      <div className="space-y-3">
        {skills.map(s => <SkillCard key={s.skill_id} skill={s} />)}
      </div>

      {skills.length === 0 && (
        <div className="text-center text-gray-400 py-12">
          Complete a case to see your skill evidence here.
        </div>
      )}
    </div>
  )
}
