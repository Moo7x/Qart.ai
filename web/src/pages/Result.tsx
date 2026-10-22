import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowRight, CircleCheck, CircleX, Flag } from 'lucide-react'
import { flagSession, getNextCase, getSkills } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import { skillName } from '../skillNames'
import { SkillResources } from '../components/ResourceList'
import type { DecisionResponse, NextCase, SkillState } from '../types'
import { btn, Card, NextStepCard, SectionTitle, StatePill } from '../ui'

const FLAGS = [
  { value: 'companion_error', label: 'The companion was wrong or misleading' },
  { value: 'ambiguous_case', label: 'The case is ambiguous (more than one answer is defensible)' },
  { value: 'data_issue', label: 'The case data has an error' },
] as const

/** Flags this attempt so it stops counting as evidence (the trail shows it as flagged). */
function ReportProblem({ sessionId, userId, onFlagged }: { sessionId: string; userId: string; onFlagged: () => void }) {
  const [open, setOpen] = useState(false)
  const [done, setDone] = useState<string | null>(null)
  if (done) {
    return <p className="text-sm text-marigold-ink bg-marigold-tint rounded-md px-4 py-3">Reported ({done}). This attempt no longer counts as evidence.</p>
  }
  return (
    <div className="text-sm">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="inline-flex items-center gap-1.5 text-graphite hover:text-ink underline underline-offset-2">
        <Flag size={14} aria-hidden="true" /> Report a problem with this case
      </button>
      {open && (
        <div className="mt-3 flex flex-col gap-2">
          {FLAGS.map(f => (
            <button
              key={f.value}
              onClick={async () => {
                await flagSession(sessionId, f.value, userId)
                setDone(f.label.toLowerCase())
                onFlagged()
              }}
              className="text-left rounded-md border border-hairline-strong bg-surface px-3 py-2 text-ink hover:bg-linen transition-colors duration-200"
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
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [])

  useEffect(() => {
    getSkills(userId).then(setSkills)
    getNextCase(userId).then(setNextCase).catch(() => setNextCase(null))
  }, [userId])

  const relevantSkillIds = result?.event?.skills_evidence.map(se => se.skill_id) ?? []
  const relevantSkills = skills.filter(s => relevantSkillIds.includes(s.skill_id))
  const toLearn = relevantSkills.filter(s => s.state !== 'demonstrated_independently').slice(0, 2)

  return (
    <div ref={root} className="max-w-2xl mx-auto space-y-6">
      {result && (
        <div data-reveal className={`rounded-lg p-6 ${result.decision_correct ? 'bg-action-tint' : 'bg-coral-tint'}`}>
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
        <Card data-reveal className="p-6">
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

      {toLearn.length > 0 && (
        <Card className="p-6 space-y-4">
          <SectionTitle>Learn more</SectionTitle>
          {toLearn.map(s => (
            <div key={s.skill_id} className="space-y-2">
              <div className="font-medium text-ink">{skillName(s.skill_id)}</div>
              <SkillResources skillId={s.skill_id} k={2} />
            </div>
          ))}
        </Card>
      )}

      <div data-reveal>
        <NextStepCard
          eyebrow="Suggested next"
          title={nextCase?.case_id ?? 'Pick your next case'}
          action={
            <Link to={nextCase?.case_id ? `/workspace/${nextCase.case_id}` : '/queue'} className={`${btn.primary} whitespace-nowrap`}>
              {nextCase?.case_id ? 'Start it' : 'Work queue'} <ArrowRight size={16} aria-hidden="true" />
            </Link>
          }
        >
          {nextCase?.because ?? 'Choose any case from your work queue.'}
        </NextStepCard>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/skills" className={btn.outline}>See my skills</Link>
        {result?.event?.session_id && (
          <ReportProblem
            sessionId={result.event.session_id}
            userId={userId}
            onFlagged={() => getSkills(userId).then(setSkills)}
          />
        )}
      </div>

    </div>
  )
}
