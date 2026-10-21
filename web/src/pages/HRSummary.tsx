import { useEffect, useState } from 'react'
import { getHRSummary } from '../api'
import type { HRSummaryData } from '../types'

const STATE_COLORS = {
  demonstrated: 'bg-green-100 text-green-700',
  observed: 'bg-blue-100 text-blue-700',
  self_reported: 'bg-amber-100 text-amber-700',
  insufficient: 'bg-gray-100 text-gray-500',
}

function CountCell({ value }: { value: number | null }) {
  if (value === null)
    return <span className="text-xs text-gray-400 italic">suppressed</span>
  return <span className="text-sm font-semibold text-gray-800">{value}</span>
}

export default function HRSummary() {
  const [summary, setSummary] = useState<HRSummaryData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getHRSummary('finops_kl')
      .then(data => { setSummary(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">HR summary</h1>
        <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-medium">Aggregates only</span>
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 text-sm text-amber-800">
        <strong>Privacy note:</strong> Individual recommendations are visible only to each employee.
        Groups smaller than 5 are suppressed. The system never makes promotion or dismissal decisions.
      </div>

      {loading && (
        <div className="text-gray-400 text-center py-10">Loading…</div>
      )}

      {!loading && summary && (
        <>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>Team: <strong className="text-gray-800">{summary.team}</strong></span>
            <span>Employees: <strong className="text-gray-800">{summary.total_employees}</strong></span>
            <span className="text-xs text-gray-400 ml-auto">
              Generated {new Date(summary.generated_at).toLocaleDateString()}
            </span>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Skill</th>
                  <th className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATE_COLORS.demonstrated}`}>Demonstrated</span>
                  </th>
                  <th className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATE_COLORS.observed}`}>Observed</span>
                  </th>
                  <th className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATE_COLORS.self_reported}`}>Self-reported</span>
                  </th>
                  <th className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATE_COLORS.insufficient}`}>Not evidenced</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {summary.skill_counts.map((row, i) => (
                  <tr key={row.skill_id} className={`border-b border-gray-50 ${i % 2 === 0 ? '' : 'bg-gray-50/40'}`}>
                    <td className="px-4 py-3 text-gray-700 font-medium">{row.skill_label}</td>
                    <td className="px-4 py-3 text-center"><CountCell value={row.demonstrated} /></td>
                    <td className="px-4 py-3 text-center"><CountCell value={row.observed} /></td>
                    <td className="px-4 py-3 text-center"><CountCell value={row.self_reported} /></td>
                    <td className="px-4 py-3 text-center"><CountCell value={row.insufficient} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-gray-400">
            Counts are evidence-state totals across the team. "Suppressed" means the group is smaller than 5 to protect re-identification.
          </p>
        </>
      )}

      {!loading && !summary && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-400">
          <p className="font-medium text-gray-600">Could not load HR summary</p>
          <p className="text-sm mt-1">The engine may not be connected yet. Try again after M1 merge.</p>
        </div>
      )}
    </div>
  )
}
