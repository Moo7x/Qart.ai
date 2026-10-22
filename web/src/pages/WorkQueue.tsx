import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Star } from 'lucide-react'
import { listCases } from '../api'
import type { Case } from '../types'
import { btn, Card, EmptyState, Loading, PageHeader, Tag, type Tone } from '../ui'

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
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listCases().then(setCases).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading what="cases" />

  return (
    <div className="max-w-3xl mx-auto">
      <PageHeader title="Work queue" intro="AI-prepared work waiting for your review. You decide what happens to each one." />
      {cases.length === 0 ? (
        <EmptyState title="No cases yet">Your first practice case appears here.</EmptyState>
      ) : (
        <ul className="space-y-3">
          {cases.map(c => {
            const mode = MODE_META[c.mode] ?? { label: c.mode, tone: 'linen' as Tone }
            return (
              <li key={c.id}>
                <Card className="p-5 flex flex-col sm:flex-row sm:items-center gap-4 hover:border-hairline-strong transition-colors duration-200">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <Tag tone={mode.tone}>{mode.label}</Tag>
                      <span className="text-xs text-graphite">{c.scenario_variant} scenario</span>
                    </div>
                    <div className="font-semibold text-ink">{c.title}</div>
                    <div className="mt-1"><Difficulty n={c.difficulty} /></div>
                  </div>
                  <Link to={`/workspace/${c.id}`} className={`${btn.primary} whitespace-nowrap`}>
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
