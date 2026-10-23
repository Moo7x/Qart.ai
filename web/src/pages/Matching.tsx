import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, Check, RotateCcw, TriangleAlert } from 'lucide-react'
import { getHeldSkills, getLearningPlan, getRanking, getSkillSignals } from '../api'
import { useAnswers } from '../onboarding/answers'
import { useUserId } from '../persona'
import { btn } from '../ui'

const MIN_STAGE_MS = 400 // so fast local calls still read as steps; no delay beyond this
type Status = 'waiting' | 'active' | 'done' | 'failed'

const STAGES = [
  { title: 'Reading your answers', detail: 'Turning your three sections into a skills profile' },
  { title: 'Mapping your skills', detail: 'Matching what you do to standard skill IDs' },
  { title: 'Scanning the job market', detail: 'Checking demand trends from public job postings' },
  { title: 'Ranking future roles', detail: 'Scoring each role on skills, demand, direction and time' },
  { title: 'Building your skills gap', detail: 'Listing what you have and what to learn next' },
]

const STATUS_TEXT: Record<Status, string> = { waiting: 'Waiting', active: 'In progress', done: 'Complete', failed: 'Failed' }
const wait = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms))

/**
 * Matching progress (QART_ONBOARDING_FLOW_SPEC §5). Each stage is a real call: save the answers,
 * map them to skill ids, load the market signals, rank the roles, build the top role's gap and
 * plan. A failed stage turns red with one line of explanation and can be retried from there.
 * Test hook: /matching?fail=4 makes stage 4 fail once, to check the error state.
 */
export default function Matching() {
  const navigate = useNavigate()
  const userId = useUserId()
  const a = useAnswers()
  const [params] = useSearchParams()
  const failOnce = useRef(params.get('fail'))
  const [status, setStatus] = useState<Status[]>(STAGES.map(() => 'waiting'))
  const [error, setError] = useState<string | null>(null)
  const topRole = useRef<string | null>(null)
  const started = useRef(false)

  const stage = useCallback(async (i: number): Promise<void> => {
    if (failOnce.current === String(i + 1)) {
      failOnce.current = null
      throw new Error('Simulated failure (test hook).')
    }
    if (i === 0) {
      const missing = [...a.missing(1), ...a.missing(2)]
      if (missing.length) throw new Error(`Some required answers are missing: ${missing.join(', ')}.`)
      await a.save()
    } else if (i === 1) {
      const held = await getHeldSkills(userId)
      if (held.length === 0) throw new Error('No skills found in your answers; add your tools or tasks.')
    } else if (i === 2) {
      await getSkillSignals()
    } else if (i === 3) {
      const ranking = await getRanking(userId, 'moderate')
      if (ranking.empty_profile) throw new Error(ranking.message ?? 'Add a few skills or tasks to get a personalised ranking.')
      topRole.current = ranking.roles[0]?.role_id ?? null
    } else {
      await getLearningPlan(userId, topRole.current)
    }
  }, [a, userId])

  const run = useCallback(async (from: number) => {
    setError(null)
    for (let i = from; i < STAGES.length; i++) {
      setStatus(s => s.map((v, j) => (j === i ? 'active' : j < i ? 'done' : v === 'failed' ? 'waiting' : v)))
      try {
        await Promise.all([stage(i), wait(MIN_STAGE_MS)])
      } catch (e) {
        setStatus(s => s.map((v, j) => (j === i ? 'failed' : v)))
        setError(e instanceof Error && e.message ? e.message : 'Something went wrong. Please try again.')
        return
      }
      setStatus(s => s.map((v, j) => (j === i ? 'done' : v)))
    }
    a.setComplete(true)
  }, [stage, a])

  useEffect(() => {
    if (!a.loaded || started.current) return
    started.current = true
    run(0)
  }, [a.loaded, run])

  const failedAt = status.indexOf('failed')
  const done = status.every(s => s === 'done')

  return (
    <section className="max-w-3xl mx-auto flex flex-col gap-7">
      <div className="text-center flex flex-col items-center gap-3">
        <h1 className="text-[clamp(34px,6vw,52px)] leading-[1.08] tracking-[-0.03em] font-extrabold text-ink">
          {done ? 'Your matches are ready' : 'We are looking for the best match'}
        </h1>
        <p className="max-w-xl font-serif text-xl leading-[1.45] text-graphite">
          {done ? 'Roles ranked from your skills, the market trend for them, your direction and your time.' : 'Five quick steps, each using your answers and real market data.'}
        </p>
      </div>
      <ol aria-live="polite" className="flex flex-col gap-3">
        {STAGES.map((s, i) => {
          const st = status[i]
          return (
            <li key={s.title} className={`flex items-center gap-4 rounded-2xl border px-6 py-[18px] ${st === 'failed' ? 'border-coral/50 bg-coral-tint' : st === 'waiting' ? 'border-hairline bg-canvas' : 'border-hairline bg-surface'}`}>
              {st === 'done' && <span className="w-9 h-9 shrink-0 rounded-full bg-[#E7F4EA] flex items-center justify-center"><Check size={18} strokeWidth={2.5} className="text-[#166534]" aria-hidden="true" /></span>}
              {st === 'active' && (
                <span className="w-9 h-9 shrink-0 rounded-full bg-action-tint flex items-center justify-center">
                  <svg className="animate-spin motion-reduce:animate-none" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9" className="text-action" stroke="currentColor" /></svg>
                </span>
              )}
              {st === 'waiting' && <span className="w-9 h-9 shrink-0 rounded-full border-2 border-dashed border-hairline-strong" aria-hidden="true" />}
              {st === 'failed' && <span className="w-9 h-9 shrink-0 rounded-full bg-surface flex items-center justify-center"><TriangleAlert size={18} className="text-coral-ink" aria-hidden="true" /></span>}
              <div className="flex-1 min-w-0">
                <div className="text-[17px] font-bold text-ink">{s.title}</div>
                <div className="text-sm text-graphite">{st === 'failed' && error ? error : s.detail}</div>
              </div>
              <span className={`shrink-0 text-[15px] font-medium ${st === 'done' ? 'text-[#166534]' : st === 'active' ? 'text-action-ink' : st === 'failed' ? 'text-coral-ink' : 'text-graphite'}`}>{STATUS_TEXT[st]}</span>
            </li>
          )
        })}
      </ol>
      {failedAt >= 0 && (
        <div className="flex flex-wrap justify-center gap-3">
          <button type="button" onClick={() => run(failedAt)} className={`${btn.primary} min-h-12 rounded-full px-6`}><RotateCcw size={16} aria-hidden="true" /> Try again</button>
          <button type="button" onClick={() => navigate('/onboarding/1')} className={`${btn.outline} min-h-12 rounded-full px-6`}>Back to questions</button>
        </div>
      )}
      {done && (
        <div className="flex justify-center">
          <button type="button" onClick={() => navigate('/app/match')} className={`${btn.primary} min-h-14 rounded-full px-9 text-lg font-bold`}>
            See my matches <ArrowRight size={18} aria-hidden="true" />
          </button>
        </div>
      )}
    </section>
  )
}
