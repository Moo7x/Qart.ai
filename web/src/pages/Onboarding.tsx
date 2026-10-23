import { useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight } from 'lucide-react'
import { useAnswers } from '../onboarding/answers'
import { StepHeading, StepHowYouLearn, StepWhereNow } from '../onboarding/Steps'
import { btn, Loading } from '../ui'

const STEPS = {
  1: { title: 'Where you are now', sub: 'Your current work tells us which skills you already have.', Body: StepWhereNow },
  2: { title: "Where you're heading", sub: 'Your direction decides which roles count as a good fit.', Body: StepHeading },
  3: { title: 'How you learn', sub: 'Your time and preferences shape the learning plan.', Body: StepHowYouLearn },
} as const

/** The existing questionnaire, one step per screen; steps are URLs so Back and refresh work. */
export default function Onboarding() {
  const { step: raw } = useParams()
  const step = Number(raw) as 1 | 2 | 3
  const navigate = useNavigate()
  const a = useAnswers()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (![1, 2, 3].includes(step)) return <Navigate to="/onboarding/1" replace />
  if (a.error) return <p role="alert" className="rounded-md bg-coral-tint px-4 py-3 text-sm text-coral-ink">{a.error}</p>
  if (!a.loaded) return <Loading what="your answers" />

  const { title, sub, Body } = STEPS[step]
  const missing = a.missing(step)
  const hint = missing.length ? `${step === 2 ? 'Choose' : 'Add'} ${missing.join(' and ')} to continue.` : ''

  const next = async () => {
    if (step === 3) { navigate('/matching'); return } // matching saves the answers as its first stage
    setSaving(true)
    setError(null)
    try {
      await a.save()
      navigate(`/onboarding/${step + 1}`)
    } catch {
      setError('Saving your answers failed. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <div className="text-sm font-semibold text-graphite">Step {step} of 3</div>
        <div className="mt-2 grid grid-cols-3 gap-2" role="progressbar" aria-valuemin={1} aria-valuemax={3} aria-valuenow={step} aria-label={`Step ${step} of 3`}>
          {[1, 2, 3].map(n => <span key={n} className={`h-1.5 rounded-full ${n <= step ? 'bg-action' : 'bg-hairline-strong'}`} />)}
        </div>
      </div>
      <form onSubmit={e => { e.preventDefault(); if (!missing.length) next() }} className="space-y-6">
        <section className="rounded-[20px] border border-hairline bg-surface p-6 sm:p-10">
          <h1 className="text-[30px] font-extrabold tracking-[-0.02em] text-ink">{title}</h1>
          <p className="mt-1 mb-6 text-graphite">{sub}</p>
          <Body />
        </section>
        {error && <p role="alert" className="rounded-md bg-coral-tint px-4 py-3 text-sm text-coral-ink">{error}</p>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button type="button" onClick={() => navigate(step === 1 ? '/' : `/onboarding/${step - 1}`)} className={`${btn.text} min-h-11`}>
            <ArrowLeft size={16} aria-hidden="true" /> Back
          </button>
          <div className="flex flex-wrap items-center justify-end gap-3">
            {hint && <span className="text-sm text-graphite" id="next-hint">{hint}</span>}
            <button type="submit" disabled={missing.length > 0 || saving} aria-describedby={hint ? 'next-hint' : undefined}
              className={`${btn.primary} min-h-12 rounded-full px-7 text-base`}>
              {saving ? 'Saving…' : step === 3 ? <>Find pathway <ArrowRight size={16} aria-hidden="true" /></> : <>Next <ArrowRight size={16} aria-hidden="true" /></>}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
