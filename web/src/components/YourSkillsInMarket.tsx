import { Link } from 'react-router-dom'
import type { HiringNow, UserSignals } from '../types'
import { formatChange, SignalBadge } from './SignalParts'

/**
 * The person's own skills against both market sources, side by side: the 3-year trend in tech
 * job posts (Hacker News) and how often this week's open postings in Malaysia + Singapore mention
 * the skill (public job boards). Rising skills they don't have yet follow as chips.
 */
export default function YourSkillsInMarket({ mine, hiring }: { mine: UserSignals; hiring: HiringNow | null }) {
  const now = Object.fromEntries((hiring?.skills ?? []).map(s => [s.skill_id, s.share_pct]))
  return (
    <div className="rounded-lg border border-hairline bg-surface p-5 sm:p-6 space-y-5">
      {mine.user_skills.length === 0 ? (
        <p className="text-sm text-graphite">
          None of your skills is tracked yet. Add your tools and tasks on your <Link to="/start" className="text-action-ink hover:underline">Profile</Link> to see them here.
        </p>
      ) : (
        <div>
          <div className="hidden sm:grid grid-cols-[minmax(0,1fr)_11rem_7rem_9rem] gap-x-4 pb-1.5 text-xs text-graphite">
            <span>Your skill</span><span>3-year trend (tech posts)</span><span className="text-right">12-month change</span>
            <span className="text-right">{hiring ? `${hiring.region_label} now` : 'Postings now'}</span>
          </div>
          <ul aria-label="Your skills in the market">
            {mine.user_skills.map(s => (
              <li key={s.id} className="flex flex-col gap-1 sm:grid sm:grid-cols-[minmax(0,1fr)_11rem_7rem_9rem] sm:items-center sm:gap-x-4 border-t border-hairline py-2.5 text-sm">
                <div className="flex items-center justify-between gap-3 sm:contents">
                  <span className="font-medium text-ink min-w-0">{s.name}</span>
                  <span className="shrink-0"><SignalBadge label={s.label} /></span>
                </div>
                <div className="flex items-center justify-between gap-3 text-xs sm:contents sm:text-sm">
                  <span className="tabular-nums text-ink sm:text-right">
                    <span className="sm:hidden text-graphite">12-month change </span>{s.label === 'insufficient_data' ? '–' : formatChange(s.change_12m)}
                  </span>
                  <span className="tabular-nums text-ink text-right">
                    {now[s.id] == null ? <span className="text-graphite">–</span> : `${now[s.id]!.toFixed(1)}%`}
                    <span className="sm:hidden text-graphite"> of {hiring?.region_label ?? ''} postings now</span>
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {mine.rising_skills_not_held.length > 0 && (
        <div>
          <div className="text-sm font-medium text-ink mb-2">Rising skills you don't have yet</div>
          <ul className="flex flex-wrap gap-2">
            {mine.rising_skills_not_held.map(s => (
              <li key={s.id} className="inline-flex items-center gap-1.5 rounded-md border border-hairline px-2.5 py-1.5 text-sm text-ink">
                {s.name} <SignalBadge label={s.label} />
                {now[s.id] != null && <span className="text-xs tabular-nums text-graphite">{now[s.id]!.toFixed(1)}% now</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-xs text-graphite">
        Trend: {mine.attribution}, data to {mine.data_as_of}.{hiring ? ` Postings now: public job boards of ${hiring.meta.coverage?.companies.length ?? 0} companies, data to ${hiring.meta.data_as_of}.` : ''} Trend signals, not predictions; they shape your matches as market momentum.
        {mine.no_market_data.length > 0 && <> No market data yet for: {mine.no_market_data.join(', ')}.</>}
      </p>
    </div>
  )
}
