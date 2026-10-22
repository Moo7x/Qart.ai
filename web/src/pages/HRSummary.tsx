import { useEffect, useRef, useState } from 'react'
import { EyeOff, Grid3x3, ShieldCheck, Users } from 'lucide-react'
import { useReveal } from '../motion'
import { getHRSummary } from '../api'
import { skillName } from '../skillNames'
import type { HRSummaryData, SkillStateName } from '../types'
import { Card, EmptyState, Highlight, label, Loading, PageHeader, ProvenanceTag, StatePill, StatTile, Tag } from '../ui'

const COLUMNS: SkillStateName[] = ['demonstrated_independently', 'observed_with_help', 'self_reported', 'insufficient_evidence']

function CountCell({ value }: { value: number | null | undefined }) {
  // Suppressed (group under the minimum size) is a dash, never a zero, so it cannot be misread.
  if (value === null || value === undefined)
    return <span className="text-stone cursor-help" title="Hidden: group too small to show">—<span className="sr-only">hidden, group too small</span></span>
  return <span className="font-medium text-ink tabular-nums">{value}</span>
}

export default function HRSummary() {
  const [summary, setSummary] = useState<HRSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [loading])

  useEffect(() => {
    getHRSummary('finops_kl')
      .then(data => { setSummary(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  // Cells hidden because the group is too small (counted, never revealed).
  const hiddenCells = summary?.skills.reduce((n, row) => n + COLUMNS.filter(c => row.counts[c] === null || row.counts[c] === undefined).length, 0) ?? 0

  return (
    <div ref={root} className="max-w-4xl mx-auto space-y-6">
      <div data-reveal>
        <PageHeader
          title={<>Your team, in <Highlight>aggregate</Highlight></>}
          intro="How skill evidence looks across the team. Aggregates only, never individuals."
          aside={<Tag tone="mocha" icon={ShieldCheck}>Aggregates only</Tag>}
        />
      </div>

      <div data-reveal className="bg-marigold-tint rounded-lg p-4 text-sm text-marigold-ink flex gap-3">
        <ShieldCheck size={20} className="shrink-0" aria-hidden="true" />
        <p>
          <strong>Privacy:</strong> individual recommendations are visible only to each employee.
          The system recommends; it never makes hiring, promotion or dismissal decisions.
          {summary && <> {summary.note}</>}
        </p>
      </div>

      {loading && <Loading what="team summary" />}

      {!loading && summary && summary.suppressed && (
        <EmptyState title="Nothing to show for this team">This team has fewer than {summary.min_group_size} people, so all counts are hidden.</EmptyState>
      )}

      {!loading && summary && !summary.suppressed && (
        <>
          <div data-reveal className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-graphite">
            <span>Team <strong className="text-ink">{summary.team}</strong></span>
            <span className="ml-auto"><ProvenanceTag kind="synthetic" /></span>
          </div>
          <div data-reveal className="grid grid-cols-3 gap-3">
            <StatTile tone="action" icon={Users} label="People" value={summary.group_size ?? '—'} />
            <StatTile tone="linen" icon={Grid3x3} label="Skills tracked" value={summary.skills.length} />
            <StatTile tone="marigold" icon={EyeOff} label={`Hidden cells (group < ${summary.min_group_size})`} value={hiddenCells} />
          </div>

          <Card data-reveal className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th scope="col" className={`${label} text-left px-4 py-3`}>Skill</th>
                  {COLUMNS.map(state => (
                    <th key={state} scope="col" className="px-4 py-3 text-center font-normal"><StatePill state={state} /></th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {summary.skills.map(row => (
                  <tr key={row.skill_id} className="border-t border-hairline">
                    <th scope="row" className="px-4 py-3 text-left text-ink font-medium">{skillName(row.skill_id)}</th>
                    {COLUMNS.map(state => (
                      <td key={state} className="px-4 py-3 text-center"><CountCell value={row.counts[state]} /></td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            {summary.training_demand.map(d => (
              <Card key={d.scenario} className="p-5">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="font-semibold text-ink">Training demand</span>
                  <ProvenanceTag kind="assumption">{d.scenario} scenario</ProvenanceTag>
                </div>
                <ul className="space-y-2 text-sm">
                  {d.skills.slice(0, 5).map(s => (
                    <li key={s.skill_id} className="flex justify-between gap-3 border-t border-hairline pt-2 first:border-0 first:pt-0">
                      <span className="text-ink">{skillName(s.skill_id)}</span>
                      <span className="text-graphite text-xs text-right tabular-nums">
                        not yet shown: <CountCell value={s.people_without_demonstration} /> · max role weight {s.max_role_weight.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>

          <p className="text-xs text-graphite">
            Counts are evidence-state totals across the team. A dash means fewer than {summary.min_group_size} people,
            which reduces but does not eliminate re-identification risk.
          </p>
        </>
      )}

      {!loading && !summary && (
        <EmptyState title="Could not load the HR summary">The server did not respond. Check that the backend is running.</EmptyState>
      )}
    </div>
  )
}
