import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BriefcaseBusiness, GraduationCap, ShieldCheck, Star } from 'lucide-react'
import { getNextCase, listCases } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { Case, NextCase } from '../types'
import { btn, Card, EmptyState, Highlight, Loading, NextStepCard, PageHeader, StatTile, Tag, type Tone } from '../ui'

const MODE_META: Record<string, { label: string; tone: Tone }> = {
  practice: { label: 'Practice', tone: 'action' },
  checkin: { label: 'Check-in · no help', tone: 'coral' },
  real: { label: 'Real work', tone: 'mocha' },
}

const MAX_DIFFICULTY = 3

function Difficulty({ n }: { n: number }) {
  return (
    <span className="inline-flex items-center gap-0.5 text-marigold" aria-label={`Difficulty ${n} of ${MAX_DIFFICULTY}`}>
      {Array.from({ length: MAX_DIFFICULTY }, (_, i) => (
        <Star key={i} size={14} strokeWidth={1.75} fill={i < n ? 'currentColor' : 'none'} className={i < n ? '' : 'text-hairline-strong'} aria-hidden="true" />
      ))}
    </span>
  )
}

export default function WorkQueue() {
  const userId = useUserId()
  const [cases, setCases] = useState<Case[]>([])
  const [next, setNext] = useState<NextCase | null>(null)
  const [loading, setLoading] = useState(true)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [loading])

  useEffect(() => {
    listCases().then(setCases).finally(() => setLoading(false))
    getNextCase(userId).then(setNext).catch(() => setNext(null))
  }, [userId])

  if (loading) return <Loading what="cases" />

  const count = (mode: string) => cases.filter(c => c.mode === mode).length
  const nextCase = next?.case_id ? cases.find(c => c.id === next.case_id) : undefined

  return (
    <div ref={root} className="max-w-3xl mx-auto">
      <div data-reveal>
        <PageHeader
          title={<>Review what the AI <Highlight>prepared</Highlight></>}
          intro="AI-prepared work waiting for your review. You decide what happens to each one."
        />
      </div>

      <div data-reveal className="grid grid-cols-3 gap-3 mb-6">
        <StatTile tone="action" icon={GraduationCap} label="Practice" value={count('practice')} />
        <StatTile tone="coral" icon={ShieldCheck} label="Check-ins" value={count('checkin')} />
        <StatTile tone="mocha" icon={BriefcaseBusiness} label="Real work" value={count('real')} />
      </div>

      {next?.case_id && (
        <div data-reveal className="mb-8">
          <NextStepCard
            eyebrow="Suggested next"
            title={nextCase?.title ?? next.case_id}
            action={
              <Link to={`/workspace/${next.case_id}`} className={`${btn.primary} whitespace-nowrap`}>
                Start <ArrowRight size={16} aria-hidden="true" />
              </Link>
            }
          >
            {next.because}
          </NextStepCard>
        </div>
      )}

      {cases.length === 0 ? (
        <EmptyState title="No cases yet">Your first practice case appears here.</EmptyState>
      ) : (
        <ul className="space-y-3">
          {cases.map(c => {
            const mode = MODE_META[c.mode] ?? { label: c.mode, tone: 'linen' as Tone }
            return (
              <li key={c.id} data-reveal>
                <Card className="p-5 flex flex-col sm:flex-row sm:items-center gap-4 hover:border-hairline-strong transition-colors duration-200">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <Tag tone={mode.tone}>{mode.label}</Tag>
                      <span className="text-xs text-graphite">{c.scenario_variant} scenario</span>
                    </div>
                    <div className="font-semibold text-ink">{c.title}</div>
                    <div className="mt-1"><Difficulty n={c.difficulty} /></div>
                  </div>
                  <Link to={`/workspace/${c.id}`} className={`${btn.outline} whitespace-nowrap`}>
                    {c.mode === 'checkin' ? 'Take check-in' : 'Start review'}
                    <ArrowRight size={16} aria-hidden="true" />
                  </Link>
                </Card>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
