import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { flagSession, getNextCase, getSkills } from '../api'
import { useUserId } from '../persona'
import { skillName } from '../skillNames'
import { SkillResources } from '../components/ResourceList'
import type { DecisionResponse, NextCase, SkillState } from '../types'

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

const FLAGS = [
  { value: 'companion_error', label: 'The companion was wrong or misleading' },
  { value: 'ambiguous_case', label: 'The case is ambiguous (more than one answer is defensible)' },
  { value: 'data_issue', label: 'The case data has an error' },
] as const

/** Flags this attempt so it stops counting as evidence (the trail shows it as flagged). */
function ReportProblem({ sessionId, userId, onFlagged }: { sessionId: string; userId: string; onFlagged: () => void }) {
  const [open, setOpen] = useState(false)
  const [done, setDone] = useState<string | null>(null)
  if (done) return <p className="text-xs text-gray-500">Reported ({done}). This attempt no longer counts as evidence.</p>
  return (
    <div className="text-xs">
      <button onClick={() => setOpen(!open)} className="text-gray-500 hover:text-gray-700 underline">
        Report a problem with this case
      </button>
      {open && (
        <div className="mt-2 flex flex-col gap-1">
          {FLAGS.map(f => (
            <button
              key={f.value}
              onClick={async () => {
                await flagSession(sessionId, f.value, userId)
                setDone(f.label.toLowerCase())
                onFlagged()
              }}
              className="text-left px-3 py-1.5 rounded border border-gray-200 hover:bg-gray-50 text-gray-700"
            >
              {f.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Result() {
  useParams<{ caseId: string }>()
  const userId = useUserId()
  const location = useLocation()
  const result: DecisionResponse | null = location.state?.result ?? null
  const [skills, setSkills] = useState<SkillState[]>([])
  const [nextCase, setNextCase] = useState<NextCase | null>(null)

  useEffect(() => {
    getSkills(userId).then(setSkills)
    getNextCase(userId).then(setNextCase).catch(() => setNextCase(null))
  }, [userId])

  const relevantSkillIds = result?.event?.skills_evidence.map(se => se.skill_id) ?? []
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
              Issue in rows: {result.affected_rows.join(', ')}. Correct decision was: <strong>{result.correct_decision?.replace('_', ' ')}</strong>.
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
                  <div className="text-sm font-medium text-gray-800">{skillName(s.skill_id)}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{s.why}</div>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-3">Evidence state, not a score. See My skills for your full trail.</p>
        </div>
      )}

      {result?.event?.session_id && (
        <ReportProblem
          sessionId={result.event.session_id}
          userId={userId}
          onFlagged={() => getSkills(userId).then(setSkills)}
        />
      )}

      {relevantSkills.some(s => s.state !== 'demonstrated_independently') && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Learn more</div>
          {relevantSkills
            .filter(s => s.state !== 'demonstrated_independently')
            .slice(0, 2)
            .map(s => (
              <div key={s.skill_id} className="space-y-1">
                <div className="text-sm font-medium text-gray-800">{skillName(s.skill_id)}</div>
                <SkillResources skillId={s.skill_id} k={2} />
              </div>
            ))}
        </div>
      )}

      {nextCase?.case_id && (
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 text-sm text-indigo-900">
          <div className="text-xs font-medium text-indigo-500 uppercase tracking-wide mb-1">Suggested next</div>
          <strong>{nextCase.case_id}</strong> · {nextCase.because}
        </div>
      )}

      <div className="flex gap-3">
        <Link
          to={nextCase?.case_id ? `/workspace/${nextCase.case_id}` : '/queue'}
          className="flex-1 text-center bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 transition-colors"
        >
          {nextCase?.case_id ? `Next case: ${nextCase.case_id}` : 'Next case'}
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
