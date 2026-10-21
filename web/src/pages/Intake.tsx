import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { postProfile } from '../api'

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
  const [name] = useState('Aina')
  const [weeklyHours, setWeeklyHours] = useState(4)
  const [confidences, setConfidences] = useState<Record<string, number>>(
    Object.fromEntries(SKILLS.map(s => [s.id, 0.5]))
  )
  const [interests, setInterests] = useState<string[]>(['analysis', 'automation'])
  const [submitting, setSubmitting] = useState(false)

  const toggleInterest = (i: string) =>
    setInterests(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await postProfile({
        display_name: name,
        current_role_id: 'recon_associate',
        years_experience: 0.5,
        skills_self_reported: SKILLS.map(s => ({ skill_id: s.id, confidence: confidences[s.id] })),
        interests,
        weekly_learning_hours: weeklyHours,
        language: 'en',
        team: 'finops_kl',
      })
      navigate('/workspace/case_003')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Welcome, {name}</h1>
        <p className="text-gray-500 mt-1 text-sm">Tell us where you are today so we can personalise your practice.</p>
        <span className="inline-block mt-2 text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">Synthetic demo data · Aina is a synthetic persona</span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Self-rated confidence</h2>
          <p className="text-xs text-gray-500 mb-4">These are your starting self-reports. They will be updated as you practice and check-in cases provide evidence.</p>
          <div className="space-y-3">
            {SKILLS.map(skill => (
              <div key={skill.id} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-52 shrink-0">{skill.label}</span>
                <input
                  type="range" min={0} max={1} step={0.05}
                  value={confidences[skill.id]}
                  onChange={e => setConfidences(prev => ({ ...prev, [skill.id]: parseFloat(e.target.value) }))}
                  className="flex-1 accent-indigo-600"
                />
                <span className="text-sm text-gray-500 w-10 text-right">{Math.round(confidences[skill.id] * 10)}/10</span>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Interests</h2>
          <div className="flex flex-wrap gap-2">
            {INTEREST_OPTIONS.map(i => (
              <button
                key={i} type="button"
                onClick={() => toggleInterest(i)}
                className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${interests.includes(i) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'}`}
              >
                {i}
              </button>
            ))}
          </div>
        </section>

        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Weekly learning hours</h2>
          <div className="flex items-center gap-3">
            <input
              type="range" min={1} max={10} step={0.5}
              value={weeklyHours}
              onChange={e => setWeeklyHours(parseFloat(e.target.value))}
              className="flex-1 accent-indigo-600"
            />
            <span className="text-sm text-gray-700 w-16">{weeklyHours} h/week</span>
          </div>
        </section>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-60 transition-colors"
        >
          {submitting ? 'Starting…' : 'Start practising →'}
        </button>
      </form>
    </div>
  )
}
