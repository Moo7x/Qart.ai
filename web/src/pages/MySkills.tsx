import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, CircleCheck, CircleDot, CircleX, Flag, Info, type LucideIcon } from 'lucide-react'
import { getSkills } from '../api'
import type { SkillState } from '../types'
import { skillName } from '../skillNames'
import { btn, Card, EmptyState, label, Loading, PageHeader, StatePill, Tag, type Tone } from '../ui'

const OUTCOMES: Record<string, { icon: LucideIcon; label: string; tone: Tone }> = {
  success: { icon: CircleCheck, label: 'Found it', tone: 'action' },
  missed_then_found: { icon: CircleDot, label: 'Missed, then found', tone: 'marigold' },
  failure: { icon: CircleX, label: 'Missed', tone: 'coral' },
}

// help_level 0..4 from the contract; recorded as evidence, not a penalty, so one neutral tone.
const HELP_LABELS = ['No help', 'Question', 'Hint', 'Explanation', 'Answer shown']

function SkillCard({ skill }: { skill: SkillState }) {
  const [expanded, setExpanded] = useState(false)
  const [flagged, setFlagged] = useState(false)
  const trailId = `trail-${skill.skill_id}`

  return (
    <Card className="p-5">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-ink">{skillName(skill.skill_id)}</span>
            <StatePill state={skill.state} />
          </div>
          <p className="text-sm text-graphite mt-1.5">{skill.why}</p>
          {skill.next_to_confirm && (
            <p className="text-sm text-action-ink mt-1">Next: {skill.next_to_confirm}</p>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {/* Self-rating only, never a mastery percentage */}
          {skill.self_confidence != null && (
            <div className="text-right">
              <div className="text-xs text-stone">Your rating</div>
              <div className="text-sm font-medium text-ink tabular-nums">{Math.round(skill.self_confidence * 10)}/10</div>
            </div>
          )}
          <button onClick={() => setExpanded(e => !e)} aria-expanded={expanded} aria-controls={trailId} className={`${btn.text} px-2 py-1 text-xs`}>
            {expanded ? <>Hide <ChevronUp size={14} aria-hidden="true" /></> : <>Evidence <ChevronDown size={14} aria-hidden="true" /></>}
          </button>
        </div>
      </div>

      {expanded && (
        <div id={trailId} className="mt-4 border-t border-hairline pt-4 space-y-2">
          <div className={label}>Evidence trail</div>
          {skill.evidence_trail.length === 0 ? (
            <p className="text-sm text-stone">No cases yet.</p>
          ) : (
            <ul className="space-y-2">
              {skill.evidence_trail.map((item, i) => {
                const o = OUTCOMES[item.outcome] ?? OUTCOMES.failure
                const counted = item.counted !== false
                return (
                  <li key={i} className={`flex items-center gap-2 text-sm flex-wrap ${!counted ? 'opacity-60' : ''}`}>
                    <span className="text-ink font-medium tabular-nums">{item.case_id}</span>
                    <Tag tone={o.tone} icon={o.icon}>{o.label}</Tag>
                    <Tag tone="linen">{HELP_LABELS[item.help_level] ?? 'Unknown help'}</Tag>
                    {!counted && <span className="text-stone italic text-xs">not counted</span>}
                    {item.note && <span className="text-stone italic text-xs">{item.note}</span>}
                  </li>
                )
              })}
            </ul>
          )}
          <p className="text-xs text-stone pt-1 tabular-nums">
            {skill.counted_events} counted event{skill.counted_events !== 1 ? 's' : ''} ·{' '}
            {skill.independent_successes} success{skill.independent_successes !== 1 ? 'es' : ''} on your own
          </p>

          <div className="pt-3 border-t border-hairline">
            <button
              onClick={() => setFlagged(f => !f)}
              aria-pressed={flagged}
              className={`inline-flex items-center gap-1.5 text-xs rounded-sm px-2.5 py-1 transition-colors duration-200 ${flagged ? 'bg-marigold-tint text-marigold-ink' : 'border border-hairline-strong text-graphite hover:bg-linen'}`}
            >
              <Flag size={12} aria-hidden="true" />
              {flagged ? 'Flagged as unclear' : 'Flag a companion error or unclear case'}
            </button>
            {flagged && (
              <p className="text-xs text-marigold-ink mt-1.5">Flagged events count neither for nor against this skill. A senior will review it.</p>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}

export default function MySkills() {
  const [skills, setSkills] = useState<SkillState[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSkills('u_aina').then(s => { setSkills(s); setLoading(false) })
  }, [])

  if (loading) return <Loading what="your skills" />

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <PageHeader title="My skills" intro="What your work has shown so far, and why each state changed." aside={<Tag tone="linen">Evidence states, not scores</Tag>} />

      <div className="bg-action-tint rounded-lg p-4 text-sm text-action-ink flex gap-3">
        <Info size={20} className="shrink-0" aria-hidden="true" />
        <p>
          States come from what you did in cases, never a percentage. <strong>Shown on your own</strong> needs at least 2 no-help
          successes (one a check-in) on different cases in separate sessions. Help you asked for is recorded as evidence, not a penalty.
        </p>
      </div>

      {skills.length === 0 ? (
        <EmptyState title="No skill evidence yet">Complete a case and your skills appear here.</EmptyState>
      ) : (
        <div className="space-y-3">
          {skills.map(s => <SkillCard key={s.skill_id} skill={s} />)}
        </div>
      )}
    </div>
  )
}
