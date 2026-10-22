import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Check } from 'lucide-react'
import { getNextCase, getProfile, postProfile } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { Profile } from '../types'
import { btn, Card, Highlight, PageHeader, ProvenanceTag } from '../ui'

const SKILLS = [
  { id: 'recon_to_source', label: 'Reconcile to source' },
  { id: 'duplicate_detection', label: 'Duplicate detection' },
  { id: 'cutoff_timing', label: 'Cutoff / timing items' },
  { id: 'unsupported_adjustment', label: 'Unsupported adjustments' },
  { id: 'fx_conversion', label: 'FX conversion' },
  { id: 'transposition_check', label: 'Transposition errors' },
  { id: 'escalation_judgment', label: 'Escalation judgment' },
  { id: 'ai_output_review', label: 'AI output review' },
]

const INTEREST_OPTIONS = ['analysis', 'automation', 'reporting', 'controls', 'data quality', 'forecasting']

export default function Intake() {
  const navigate = useNavigate()
  const userId = useUserId()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const name = profile?.display_name.replace(' (synthetic)', '') ?? ''
  const [weeklyHours, setWeeklyHours] = useState(4)
  const [confidences, setConfidences] = useState<Record<string, number>>(
    Object.fromEntries(SKILLS.map(s => [s.id, 0.5]))
  )
  const [interests, setInterests] = useState<string[]>(['analysis', 'automation'])
  const [submitting, setSubmitting] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [profile !== null])

  // Pre-fill from the employee's saved profile so the form shows their current values
  useEffect(() => {
    getProfile(userId).then(profile => {
      setProfile(profile)
      if (profile.skills_self_reported?.length) {
        const map: Record<string, number> = {}
        for (const s of profile.skills_self_reported) map[s.skill_id] = s.confidence
        setConfidences(prev => ({ ...prev, ...map }))
      }
      if (profile.interests?.length) setInterests(profile.interests)
      if (profile.weekly_learning_hours) setWeeklyHours(profile.weekly_learning_hours)
    }).catch(() => setError('Could not load your profile.'))
  }, [userId])

  const toggleInterest = (i: string) =>
    setInterests(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!profile) return
    setSubmitting(true)
    setError(null)
    try {
      // Keep everything else in the profile; only the answers on this page change.
      await postProfile({
        ...profile,
        skills_self_reported: SKILLS.map(s => ({ skill_id: s.id, confidence: confidences[s.id] })),
        interests,
        weekly_learning_hours: weeklyHours,
      })
      const next = await getNextCase(userId).catch(() => null)
      navigate(next?.case_id ? `/workspace/${next.case_id}` : '/queue')
    } catch {
      setError('Saving your answers failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div ref={root} className="max-w-2xl mx-auto">
      <PageHeader
        title={name ? <>Welcome, <Highlight>{name}</Highlight></> : 'Welcome'}
        intro="Tell us where you are today. Your practice starts from here and changes as you work."
        aside={name ? <ProvenanceTag kind="synthetic">{name} is a demo persona</ProvenanceTag> : undefined}
      />
      {error && <p role="alert" className="-mt-4 mb-6 rounded-md bg-coral-tint px-4 py-3 text-sm text-coral-ink">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Card data-reveal className="p-6">
          <h2 className="text-base font-semibold text-ink">How confident are you today?</h2>
          <p className="mt-1 mb-5 text-sm text-graphite">This is your own starting view. Practice and check-in cases add real evidence next to it.</p>
          <div className="space-y-4">
            {SKILLS.map(skill => (
              <div key={skill.id} className="grid grid-cols-[1fr_auto] sm:grid-cols-[13rem_1fr_3rem] items-center gap-x-4 gap-y-1">
                <label htmlFor={`conf-${skill.id}`} className="col-start-1 row-start-1 text-sm text-ink">{skill.label}</label>
                <input
                  id={`conf-${skill.id}`}
                  type="range" min={0} max={1} step={0.05}
                  value={confidences[skill.id]}
                  onChange={e => setConfidences(prev => ({ ...prev, [skill.id]: parseFloat(e.target.value) }))}
                  className="col-span-2 row-start-2 sm:col-span-1 sm:col-start-2 sm:row-start-1 w-full"
                />
                <span className="col-start-2 row-start-1 sm:col-start-3 text-sm text-graphite tabular-nums text-right">{Math.round(confidences[skill.id] * 10)}/10</span>
              </div>
            ))}
          </div>
        </Card>

        <Card data-reveal className="p-6">
          <h2 className="text-base font-semibold text-ink">What do you enjoy?</h2>
          <p className="mt-1 mb-4 text-sm text-graphite">Pick any. They help rank future roles for you.</p>
          <div className="flex flex-wrap gap-2">
            {INTEREST_OPTIONS.map(i => {
              const on = interests.includes(i)
              return (
                <button
                  key={i} type="button" aria-pressed={on}
                  onClick={() => toggleInterest(i)}
                  className={`inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm transition-colors duration-200 ${on ? 'bg-action-tint text-action-ink font-medium' : 'bg-surface border border-hairline-strong text-graphite hover:bg-linen'}`}
                >
                  {on && <Check size={14} strokeWidth={2} aria-hidden="true" />}
                  {i}
                </button>
              )
            })}
          </div>
        </Card>

        <Card data-reveal className="p-6">
          <label htmlFor="weekly-hours" className="text-base font-semibold text-ink">Time for learning each week</label>
          <div className="mt-4 flex items-center gap-4">
            <input
              id="weekly-hours"
              type="range" min={1} max={10} step={0.5}
              value={weeklyHours}
              onChange={e => setWeeklyHours(parseFloat(e.target.value))}
              className="flex-1"
            />
            <span className="text-sm text-ink tabular-nums w-20 text-right">{weeklyHours} h/week</span>
          </div>
        </Card>

        <button type="submit" disabled={submitting || !profile} className={`${btn.primary} w-full py-3`}>
          {submitting ? 'Starting…' : <>Start practising <ArrowRight size={16} aria-hidden="true" /></>}
        </button>
      </form>
    </div>
  )
}
