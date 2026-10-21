import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getSkills } from '../api'
import type { DecisionResponse, SkillState } from '../types'

const STATE_COLORS: Record<string, string> = {
  demonstrated_independently: 'bg-green-100 text-green-700',
  observed_with_help: 'bg-blue-100 text-blue-700',
  self_reported: 'bg-gray-100 text-gray-600',
  insufficient_evidence: 'bg-yellow-100 text-yellow-700',
}

const STATE_LABELS: Record<string, string> = {
  demonstrated_independently: 'Demonstrated independently',
  observed_with_help: 'Observed with help',
  self_reported: 'Self-reported',
  insufficient_evidence: 'Insufficient evidence',
}

export default function Result() {
  useParams<{ caseId: string }>()
  const location = useLocation()
  const result: DecisionResponse | null = location.state?.result ?? null
  const [skills, setSkills] = useState<SkillState[]>([])

  useEffect(() => {
    getSkills('u_aina').then(setSkills)
  }, [])

  const relevantSkillIds = result?.event.skills_evidence.map(se => se.skill_id) ?? []
  const relevantSkills = skills.filter(s => relevantSkillIds.includes(s.skill_id))

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {result && (
        <div className={`rounded-xl p-6 border ${result.decision_correct ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className={`text-2xl font-bold mb-2 ${result.decision_correct ? 'text-green-800' : 'text-red-800'}`}>
            {result.decision_correct ? '✓ Correct!' : '✗ Incorrect'}
          </div>
          <p className="text-gray-700">{result.explanation}</p>
          {!result.decision_correct && result.affected_rows.length > 0 && (
            <p className="text-sm text-gray-500 mt-2">
              Issue in rows: {result.affected_rows.join(', ')}. Correct decision was: <strong>{result.correct_decision.replace('_', ' ')}</strong>.
            </p>
          )}
        </div>
      )}

      {relevantSkills.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Skills updated</h2>
          <div className="space-y-3">
            {relevantSkills.map(s => (
              <div key={s.skill_id} className="flex items-start gap-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium mt-0.5 ${STATE_COLORS[s.state]}`}>
                  {STATE_LABELS[s.state]}
                </span>
                <div>
                  <div className="text-sm font-medium text-gray-800">{s.skill_id.replace(/_/g, ' ')}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{s.why}</div>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-3">Evidence state, not a score. See My skills for your full trail.</p>
        </div>
      )}

      <div className="flex gap-3">
        <Link
          to="/queue"
          className="flex-1 text-center bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 transition-colors"
        >
          Next case
        </Link>
        <Link
          to="/skills"
          className="flex-1 text-center bg-gray-100 text-gray-700 py-3 rounded-xl font-medium hover:bg-gray-200 transition-colors"
        >
          My skills
        </Link>
      </div>
    </div>
  )
}
