import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowRight, CircleCheck, CircleX } from 'lucide-react'
import { getNextCase, getSkills } from '../api'
import { skillName } from '../skillNames'
import type { DecisionResponse, NextCase, SkillState } from '../types'
import { btn, Card, label, SectionTitle, StatePill } from '../ui'

export default function Result() {
  useParams<{ caseId: string }>()
  const location = useLocation()
  const result: DecisionResponse | null = location.state?.result ?? null
  const [skills, setSkills] = useState<SkillState[]>([])
  const [nextCase, setNextCase] = useState<NextCase | null>(null)

  useEffect(() => {
    getSkills('u_aina').then(setSkills)
    getNextCase('u_aina').then(setNextCase).catch(() => setNextCase(null))
  }, [])

  const relevantSkillIds = result?.event?.skills_evidence.map(se => se.skill_id) ?? []
  const relevantSkills = skills.filter(s => relevantSkillIds.includes(s.skill_id))

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {result && (
        <div className={`rounded-lg p-6 ${result.decision_correct ? 'bg-action-tint' : 'bg-coral-tint'}`}>
          <div className={`flex items-center gap-2 text-[28px] leading-[1.2] font-semibold tracking-[-0.02em] ${result.decision_correct ? 'text-action-ink' : 'text-coral-ink'}`}>
            {result.decision_correct ? <CircleCheck size={28} aria-hidden="true" /> : <CircleX size={28} aria-hidden="true" />}
            {result.decision_correct ? 'Correct' : 'Not this time'}
          </div>
          <p className="mt-3 font-serif text-lg leading-[1.56] text-ink">{result.explanation}</p>
          {!result.decision_correct && result.affected_rows.length > 0 && (
            <p className="text-sm text-graphite mt-3">
              Issue in rows: {result.affected_rows.join(', ')}. The right decision was <strong className="text-ink">{result.correct_decision?.replace('_', ' ')}</strong>.
            </p>
          )}
        </div>
      )}

      {relevantSkills.length > 0 && (
        <Card className="p-6">
          <SectionTitle>What this case showed</SectionTitle>
          <ul className="space-y-4">
            {relevantSkills.map(s => (
              <li key={s.skill_id} className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4">
                <div className="sm:w-52 shrink-0"><StatePill state={s.state} /></div>
                <div>
                  <div className="font-medium text-ink">{skillName(s.skill_id)}</div>
                  <div className="text-sm text-graphite mt-0.5">{s.why}</div>
                </div>
              </li>
            ))}
          </ul>
          <p className="text-xs text-stone mt-5">Evidence states, not scores. My skills shows the full trail.</p>
        </Card>
      )}

      {nextCase?.case_id && (
        <div className="bg-marigold-tint rounded-lg p-5">
          <div className={`${label} text-marigold-ink mb-1`}>Suggested next</div>
          <p className="text-ink"><strong>{nextCase.case_id}</strong> · {nextCase.because}</p>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        <Link to={nextCase?.case_id ? `/workspace/${nextCase.case_id}` : '/queue'} className={`${btn.primary} flex-1 py-3`}>
          {nextCase?.case_id ? `Next case: ${nextCase.case_id}` : 'Next case'}
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
        <Link to="/skills" className={`${btn.outline} flex-1 py-3`}>See my skills</Link>
      </div>
    </div>
  )
}
