import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCases } from '../api'
import type { Case } from '../types'

const MODE_COLORS: Record<string, string> = {
  practice: 'bg-blue-100 text-blue-700',
  checkin: 'bg-purple-100 text-purple-700',
  real: 'bg-green-100 text-green-700',
}

function Stars({ n }: { n: number }) {
  return (
    <span className="text-yellow-400 text-sm">
      {'★'.repeat(n)}{'☆'.repeat(3 - n)}
    </span>
  )
}

export default function WorkQueue() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listCases().then(setCases).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-gray-400">Loading cases…</div>

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Work queue</h1>
        <p className="text-gray-500 text-sm mt-1">AI-prepared reconciliations waiting for your review.</p>
      </div>
      <div className="space-y-3">
        {cases.map(c => (
          <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4 hover:border-indigo-300 transition-colors">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${MODE_COLORS[c.mode] ?? 'bg-gray-100 text-gray-600'}`}>
                  {c.mode}
                </span>
                <span className="text-xs text-gray-400">{c.scenario_variant}</span>
              </div>
              <div className="font-medium text-gray-900 text-sm">{c.title}</div>
              <div className="flex items-center gap-2 mt-1">
                <Stars n={c.difficulty} />
                <span className="text-xs text-gray-400">difficulty {c.difficulty}/3</span>
              </div>
            </div>
            <Link
              to={`/workspace/${c.id}`}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors whitespace-nowrap"
            >
              {c.mode === 'checkin' ? 'Take check-in' : 'Start review'}
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
