import { useEffect, useState } from 'react'
import { getHiringNow } from '../api'
import type { HiringNow as HiringNowData } from '../types'
import { Provenance } from './SignalParts'

const SHOWN = 8
const FAMILY_NAMES: Record<string, string> = {
  finance_ops: 'Finance operations', analytics: 'Analytics', automation: 'Automation', data_engineering: 'Data engineering',
  ml_ai: 'Machine learning and AI', risk_compliance: 'Risk and compliance', business: 'Business and product',
  marketing: 'Marketing', security: 'Security', project_management: 'Project management', customer_ops: 'Customer operations',
  admin: 'Administration', it_support: 'IT support', software: 'Software',
}

/** This week on the public job boards for a region: the skills open postings mention most, and
 * how often postings in each type of work mention AI. Counts are shown; small groups are hidden. */
export default function HiringNow() {
  const [data, setData] = useState<HiringNowData | null>(null)
  useEffect(() => { getHiringNow().then(setData).catch(() => setData(null)) }, [])
  if (!data) return null
  const skills = data.skills.filter(s => s.share_pct !== null).slice(0, SHOWN)
  const families = data.families.filter(f => f.share_pct !== null).sort((a, b) => (b.share_pct ?? 0) - (a.share_pct ?? 0))
  const total = data.skills[0]?.total ?? 0
  return (
    <div className="rounded-lg border border-hairline bg-surface p-5 sm:p-6">
      <div className="font-semibold text-ink">Hiring now · {data.region_label}</div>
      <p className="text-sm text-graphite tabular-nums">{total} open postings this week from {data.meta.coverage?.companies.length ?? 0} companies' public job boards</p>
      <div className="mt-4 grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="text-xs font-medium text-graphite mb-2">Skills postings mention most</h3>
          <ul className="space-y-1.5 text-sm">
            {skills.map(s => (
              <li key={s.skill_id} className="flex items-center justify-between gap-3">
                <span className="text-ink">{s.name}</span>
                <span className="tabular-nums text-graphite">{s.share_pct?.toFixed(1)}% <span className="text-xs">({s.mentions})</span></span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-medium text-graphite mb-2">Postings that mention AI, by type of work</h3>
          <ul className="space-y-1.5 text-sm">
            {families.map(f => (
              <li key={f.family} className="flex items-center justify-between gap-3">
                <span className="text-ink">{FAMILY_NAMES[f.family] ?? f.family}</span>
                <span className="tabular-nums text-graphite">{f.share_pct?.toFixed(0)}% <span className="text-xs">of {f.total}</span></span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-graphite">Groups with fewer than {data.meta.min_sample} postings are not shown.</p>
        </div>
      </div>
      <Provenance meta={{ ...data.meta, stale: data.stale }} />
    </div>
  )
}
