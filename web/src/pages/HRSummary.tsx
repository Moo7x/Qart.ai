import { useEffect, useState } from 'react'
import { getHRSummary } from '../api'
import { skillName } from '../skillNames'
import type { HRSummaryData, SkillStateName } from '../types'

const COLUMNS: { state: SkillStateName; label: string; color: string }[] = [
  { state: 'demonstrated_independently', label: 'Demonstrated', color: 'bg-green-100 text-green-700' },
  { state: 'observed_with_help', label: 'Observed with help', color: 'bg-blue-100 text-blue-700' },
  { state: 'self_reported', label: 'Self-reported', color: 'bg-amber-100 text-amber-700' },
  { state: 'insufficient_evidence', label: 'Not evidenced', color: 'bg-gray-100 text-gray-500' },
]

function CountCell({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined)
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
        The system recommends; it never makes hiring, promotion or dismissal decisions.
        {summary && <> {summary.note}</>}
      </div>

      {loading && (
        <div className="text-gray-400 text-center py-10">Loading…</div>
      )}

      {!loading && summary && summary.suppressed && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-500">
          This team has fewer than {summary.min_group_size} people, so nothing is shown.
        </div>
      )}

      {!loading && summary && !summary.suppressed && (
        <>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>Team: <strong className="text-gray-800">{summary.team}</strong></span>
            <span>People: <strong className="text-gray-800">{summary.group_size ?? 'suppressed'}</strong></span>
            <span className="text-xs text-gray-400 ml-auto">Synthetic data</span>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Skill</th>
                  {COLUMNS.map(c => (
                    <th key={c.state} className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${c.color}`}>{c.label}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {summary.skills.map((row, i) => (
                  <tr key={row.skill_id} className={`border-b border-gray-50 ${i % 2 === 0 ? '' : 'bg-gray-50/40'}`}>
                    <td className="px-4 py-3 text-gray-700 font-medium">{skillName(row.skill_id)}</td>
                    {COLUMNS.map(c => (
                      <td key={c.state} className="px-4 py-3 text-center"><CountCell value={row.counts[c.state]} /></td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {summary.training_demand.map(d => (
            <div key={d.scenario} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Training demand · {d.scenario} scenario
              </div>
              <ul className="space-y-1 text-sm">
                {d.skills.slice(0, 5).map(s => (
                  <li key={s.skill_id} className="flex justify-between gap-3">
                    <span className="text-gray-700">{skillName(s.skill_id)}</span>
                    <span className="text-gray-500 text-xs">
                      not yet demonstrated: <CountCell value={s.people_without_demonstration} /> · max role weight {s.max_role_weight.toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <p className="text-xs text-gray-400">
            Counts are evidence-state totals across the team. "Suppressed" means fewer than {summary.min_group_size} people,
            which reduces but does not eliminate re-identification risk.
          </p>
        </>
      )}

      {!loading && !summary && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-400">
          <p className="font-medium text-gray-600">Could not load HR summary</p>
          <p className="text-sm mt-1">The server did not respond. Check that the backend is running.</p>
        </div>
      )}
    </div>
  )
}
