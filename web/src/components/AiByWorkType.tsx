import type { HiringNow } from '../types'
import { Provenance } from './SignalParts'

const FAMILY_NAMES: Record<string, string> = {
  finance_ops: 'Finance operations', analytics: 'Analytics', automation: 'Automation', data_engineering: 'Data engineering',
  ml_ai: 'Machine learning and AI', risk_compliance: 'Risk and compliance', business: 'Business and product',
  marketing: 'Marketing', security: 'Security', project_management: 'Project management', customer_ops: 'Customer operations',
  admin: 'Administration', it_support: 'IT support', software: 'Software',
}

/** How often this week's open postings mention AI, by type of work (public job boards). Groups
 * under the minimum sample are hidden; counts are shown next to every share. */
export default function AiByWorkType({ data }: { data: HiringNow }) {
  const families = data.families.filter(f => f.share_pct !== null).sort((a, b) => (b.share_pct ?? 0) - (a.share_pct ?? 0))
  if (families.length === 0) return null
  return (
    <div className="rounded-lg border border-hairline bg-surface p-5 sm:p-6">
      <div className="font-semibold text-ink">Postings that mention AI, by type of work · {data.region_label}</div>
      <p className="text-sm text-graphite">This week's open postings on {data.meta.coverage?.companies.length ?? 0} companies' public job boards.</p>
      <ul className="mt-4 grid gap-x-8 gap-y-2 sm:grid-cols-2 text-sm">
        {families.map(f => (
          <li key={f.family} className="flex items-center justify-between gap-3">
            <span className="text-ink">{FAMILY_NAMES[f.family] ?? f.family}</span>
            <span className="tabular-nums text-graphite">{f.share_pct?.toFixed(0)}% <span className="text-xs">of {f.total}</span></span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-graphite">Groups with fewer than {data.meta.min_sample} postings are not shown.</p>
      <Provenance meta={{ ...data.meta, stale: data.stale }} />
    </div>
  )
}
