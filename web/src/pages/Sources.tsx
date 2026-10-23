import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, ExternalLink, TriangleAlert } from 'lucide-react'
import { getHiringNow, getMarketPulse, getSkillSignals, getSnapshots } from '../api'
import { useReveal } from '../motion'
import type { HiringNow, SignalSnapshotMeta, Snapshot } from '../types'
import { Card, Highlight, Loading, PageHeader, ProvenanceTag, Tag } from '../ui'

interface Feed {
  name: string
  what: string
  used_for: string
  url: string
  license: string
  frequency: string
  data_as_of: string
  fetched: string
  caveats: string[]
  stale: boolean
}

function fromSignal(meta: SignalSnapshotMeta, what: string, usedFor: string): Feed {
  return {
    name: meta.source, what, used_for: usedFor, url: meta.source_url, license: meta.license,
    frequency: meta.update_frequency, data_as_of: meta.data_as_of, fetched: meta.fetched_at.slice(0, 10),
    caveats: meta.caveats, stale: meta.stale,
  }
}

function fromJobs(h: HiringNow): Feed {
  const c = h.meta.coverage
  return {
    name: h.meta.source,
    what: `Open postings on the public job boards of ${c?.companies.length ?? 0} companies (Greenhouse, Lever, Ashby), saved every day; first snapshot ${h.meta.first_snapshot}. ${c?.open_jobs_latest_run ?? 0} open postings in the latest run.`,
    used_for: 'Market pulse (AI share by region, once a region has 4 weeks) and Hiring now on the Signals page.',
    url: 'https://docs.greenhouse.io/job-board.html', license: h.meta.license, frequency: h.meta.update_frequency,
    data_as_of: h.meta.data_as_of, fetched: (h.meta.fetched_at ?? '').slice(0, 10), caveats: h.meta.caveats, stale: h.stale,
  }
}

function fromAei(snaps: Snapshot[]): Feed | null {
  const latest = snaps[snaps.length - 1]
  if (!latest) return null
  return {
    name: latest.source,
    what: 'Share of AI conversations, automation and augmentation, per occupation (finance-related SOC codes), for GLOBAL and Malaysia.',
    used_for: 'Signals page (AI use in work like yours); suggests assumption reviews to HR, never changes weights by itself.',
    url: latest.url ?? '', license: latest.licence ?? 'see source', frequency: 'releases a few times a year; replayed here by period',
    data_as_of: latest.period, fetched: (latest.retrieved_at ?? '').slice(0, 10),
    caveats: ['AI usage share is not proof that tasks are replaced.', latest.label ?? ''].filter(Boolean), stale: false,
  }
}

/** Every external feed the app shows, with licence, update frequency, dates and caveats. */
export default function Sources() {
  const [feeds, setFeeds] = useState<Feed[] | null>(null)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [feeds !== null])

  useEffect(() => {
    Promise.all([getSkillSignals().catch(() => null), getMarketPulse().catch(() => null), getSnapshots().catch(() => []), getHiringNow().catch(() => null)])
      .then(([skills, pulse, aei, jobs]) => {
        const list: (Feed | null)[] = [
          skills && fromSignal(skills, 'Monthly “Ask HN: Who is hiring?” threads; each top-level comment is one job post, matched to skills by keyword.', 'Future Skills Radar; the Pathway “market context” card.'),
          pulse && fromSignal(pulse, 'Daily share of Indeed job postings mentioning AI terms (7-day average), per country, shown as a monthly mean.', 'Market Pulse on the Signals page.'),
          jobs && fromJobs(jobs),
          fromAei(aei),
        ]
        setFeeds(list.filter((f): f is Feed => f !== null))
      })
  }, [])

  if (!feeds) return <Loading what="data sources" />

  return (
    <div ref={root} className="max-w-3xl mx-auto space-y-6">
      <div data-reveal>
        <Link to="/app/skills" className="inline-flex items-center gap-1 text-sm text-action-ink hover:underline mb-4"><ArrowLeft size={14} aria-hidden="true" /> Back to Signals</Link>
        <PageHeader
          title={<>Where the numbers come <Highlight>from</Highlight></>}
          intro="Every external feed the app shows. The app reads saved snapshots of these, so it works offline; a scheduled job refreshes them. Profiles and cases are synthetic demo data and are never sent to any of these sources."
        />
      </div>
      {feeds.map(f => (
        <Card key={f.name} data-reveal className="p-6 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <ProvenanceTag kind="evidence">data to {f.data_as_of}</ProvenanceTag>
            {f.stale && <Tag tone="coral" icon={TriangleAlert}>Stale data</Tag>}
          </div>
          <h2 className="text-lg font-semibold text-ink">{f.name}</h2>
          <p className="text-sm text-ink">{f.what}</p>
          <dl className="grid grid-cols-1 sm:grid-cols-[9rem_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-graphite">Used for</dt><dd className="text-ink">{f.used_for}</dd>
            <dt className="text-graphite">Licence</dt><dd className="text-ink">{f.license}</dd>
            <dt className="text-graphite">Updates</dt><dd className="text-ink">{f.frequency}</dd>
            <dt className="text-graphite">Refreshed here</dt><dd className="text-ink tabular-nums">{f.fetched || '–'}</dd>
          </dl>
          {f.caveats.length > 0 && (
            <ul className="list-disc pl-5 text-sm text-graphite space-y-0.5">{f.caveats.map(c => <li key={c}>{c}</li>)}</ul>
          )}
          {f.url && (
            <a href={f.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-action-ink hover:underline">
              Open the source <ExternalLink size={12} aria-hidden="true" />
            </a>
          )}
        </Card>
      ))}
    </div>
  )
}
