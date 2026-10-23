import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { getHiringNow, getSkillSignals, getUserSignals } from '../api'
import AiByWorkType from '../components/AiByWorkType'
import MarketPulse from '../components/MarketPulse'
import SkillsRadar from '../components/SkillsRadar'
import YourSkillsInMarket from '../components/YourSkillsInMarket'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { HiringNow, SkillSignalsSnapshot, UserSignals } from '../types'
import { btn, EmptyState, Highlight, NextStepCard, PageHeader, SectionTitle, Tag } from '../ui'

/**
 * Is the market moving toward your skills? Three sections, each with its source and dates:
 *   1. your skills: 3-year trend in tech posts (Hacker News) and how often this week's
 *      Malaysia + Singapore postings mention them (public job boards)
 *   2. AI in job postings: the AI-share chart (one loader) and AI by type of work
 *   3. skills employers mention: the full radar with a "MY+SG now" column
 * Anthropic Economic Index occupation data lives on the HR Evidence page.
 */
export default function Signals() {
  const userId = useUserId()
  const [skills, setSkills] = useState<SkillSignalsSnapshot | null>(null)
  const [mine, setMine] = useState<UserSignals | null>(null)
  const [hiring, setHiring] = useState<HiringNow | null>(null)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [skills !== null, mine !== null])

  // Each section reads a saved snapshot; a missing one just hides that section.
  useEffect(() => {
    getSkillSignals().then(setSkills).catch(() => setSkills(null))
    getUserSignals(userId).then(setMine).catch(() => setMine(null))
    getHiringNow().then(setHiring).catch(() => setHiring(null))
  }, [userId])

  const nowShare = Object.fromEntries((hiring?.skills ?? []).map(s => [s.skill_id, s.share_pct]))

  return (
    <div ref={root} className="max-w-4xl mx-auto space-y-10">
      <div data-reveal>
        <PageHeader
          title={<>Is the market moving toward your <Highlight>skills</Highlight>?</>}
          intro="Real, dated public data: how often job posts mention your skills and AI, over three years and this week. Trend signals, never predictions; every section shows its source and dates."
          aside={<Link to="/sources" className="text-sm text-action-ink hover:underline">All data sources</Link>}
        />
      </div>

      {mine && (
        <section data-reveal>
          <SectionTitle>Your skills in the market</SectionTitle>
          <YourSkillsInMarket mine={mine} hiring={hiring} />
        </section>
      )}

      <section data-reveal className="space-y-4">
        <SectionTitle>AI in job postings</SectionTitle>
        <MarketPulse />
        {hiring && <AiByWorkType data={hiring} />}
      </section>

      <section data-reveal>
        <SectionTitle aside={<Tag tone="linen">Tech posts (Hacker News) · MY+SG job boards</Tag>}>Skills employers mention</SectionTitle>
        <p className="-mt-1 mb-3 text-sm text-graphite">
          The trend comes from three years of "Who is hiring?" posts; "MY+SG now" is this week's share of open postings in Malaysia and Singapore. Open a skill to see its trend.
        </p>
        {skills
          ? <SkillsRadar snapshot={skills} mine={Object.fromEntries((mine?.user_skills ?? []).map(s => [s.id, s.why]))} nowShare={nowShare} />
          : <EmptyState title="No skill signals yet">Run python scripts/fetch_signals.py to build the snapshot.</EmptyState>}
      </section>

      <div data-reveal>
        <NextStepCard
          eyebrow="Next"
          title="See which roles fit you"
          action={<Link to="/app/match" className={`${btn.primary} whitespace-nowrap`}>See my role matches <ArrowRight size={16} aria-hidden="true" /></Link>}
        >
          Your matches use these trends as market momentum, next to your skills, your direction and your time.
        </NextStepCard>
      </div>
    </div>
  )
}
