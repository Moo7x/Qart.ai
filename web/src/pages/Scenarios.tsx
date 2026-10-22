import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronUp, History } from 'lucide-react'
import { getProfile, getRecommendation, getSnapshots } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import { SCENARIO_LABEL, SCENARIOS } from '../scenarios'
import type { Profile, Recommendation, Scenario, Snapshot } from '../types'
import { btn, Card, EmptyState, Highlight, label, Loading, NextStepCard, PageHeader, ProvenanceTag, SectionTitle, Tag } from '../ui'

const SHARE_PCT = 100 // ai_handled_share is a 0–1 share of the role's task weight
const BAR_TONE: Record<Scenario, string> = { assistive: 'bg-action', agentic: 'bg-coral' }

const share = (v: number | undefined) => (v === undefined ? '–' : `${Math.round(v * SHARE_PCT)}%`)

export default function Scenarios() {
  const userId = useUserId()
  const [recs, setRecs] = useState<Partial<Record<Scenario, Recommendation>>>({})
  const [profile, setProfile] = useState<Profile | null>(null)
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [methodOpen, setMethodOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [loading])

  useEffect(() => {
    Promise.all([
      getRecommendation(userId, 'assistive'),
      getRecommendation(userId, 'agentic'),
      getProfile(userId),
      getSnapshots().catch(() => []),
    ])
      .then(([a, g, p, s]) => { setRecs({ assistive: a, agentic: g }); setProfile(p); setSnapshots(s) })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }, [userId])

  if (loading) return <Loading what="scenarios" />
  if (failed || !recs.assistive || !recs.agentic) {
    return (
      <div className="max-w-4xl mx-auto">
        <EmptyState title="Could not load the scenarios">The server did not respond. Check that the backend is running.</EmptyState>
      </div>
    )
  }

  const both = recs as Record<Scenario, Recommendation>
  const roleIds = both.assistive.roles.map(r => r.role_id)
  const find = (s: Scenario, id: string) => both[s].roles.find(r => r.role_id === id)
  const titleOf = (id: string) => find('assistive', id)?.title ?? id
  const current = profile?.current_role_id ?? ''
  const moved = roleIds.filter(id => find('assistive', id)?.rank !== find('agentic', id)?.rank)
  const latest = snapshots[snapshots.length - 1]
  const changes = SCENARIOS.flatMap(s => {
    const cs = both[s].changed_since
    if (!cs) return []
    const ranks = cs.rank_changes.filter(c => c.from !== c.to).map(c => ({ s, text: `${titleOf(c.role_id)}: rank ${c.from} → ${c.to}`, because: c.because }))
    const outlooks = (cs.outlook_changes ?? []).map(c => ({ s, text: `${titleOf(c.role_id)}: ${c.from_label} → ${c.to_label} (${share(c.from_ai_handled_share)} → ${share(c.to_ai_handled_share)} handled by AI)`, because: c.because }))
    return [...ranks, ...outlooks]
  })

  return (
    <div ref={root} className="max-w-4xl mx-auto space-y-8">
      <div data-reveal>
        <PageHeader
          title={<>Two possible <Highlight>futures</Highlight></>}
          intro="Nobody knows how fast AI will change work. Instead of one prediction, Qart compares the company's two AI scenarios and shows how your plan holds up in both."
          aside={<ProvenanceTag kind="assumption">company assumptions v{both.assistive.assumptions_version}</ProvenanceTag>}
        />
      </div>

      <div data-reveal className="grid gap-4 md:grid-cols-2">
        {SCENARIOS.map(s => {
          const rec = both[s]
          const mine = find(s, current)?.outlook
          const best = rec.roles[0]
          return (
            <Card key={s} className="p-6 space-y-4">
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${BAR_TONE[s]}`} aria-hidden="true" />
                <h2 className="text-[22px] leading-[1.27] font-semibold tracking-[-0.01em] text-ink">{SCENARIO_LABEL[s]}</h2>
              </div>
              <dl className="space-y-3">
                <div>
                  <dt className={label}>Your current role's task weight done or drafted by AI</dt>
                  <dd className="mt-1 flex flex-wrap items-baseline gap-2">
                    <span className="text-[32px] leading-none font-semibold tabular-nums text-ink">{share(mine?.ai_handled_share)}</span>
                    {mine && <Tag tone="linen">{mine.label}</Tag>}
                  </dd>
                  {mine && <p className="mt-1 text-xs text-graphite">{mine.because}</p>}
                </div>
                <div>
                  <dt className={label}>Best-fit role</dt>
                  <dd className="mt-1 font-semibold text-ink">{best?.title ?? best?.role_id ?? '–'}</dd>
                </div>
              </dl>
              <ProvenanceTag kind="assumption">layer B, not a headcount forecast</ProvenanceTag>
            </Card>
          )
        })}
      </div>

      <section data-reveal>
        <SectionTitle>What changes between the two</SectionTitle>
        <Card className="p-6 text-sm">
          {moved.length === 0 ? (
            <p className="text-ink">The role ranking is the same in both scenarios, so your pathway does not need to change if AI spreads faster.</p>
          ) : (
            <ul className="space-y-1.5">
              {moved.map(id => (
                <li key={id} className="text-ink">
                  <strong className="font-medium">{titleOf(id)}</strong>: rank {find('assistive', id)?.rank} → {find('agentic', id)?.rank} when AI does most routine work
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      <section data-reveal>
        <SectionTitle aside={
          <span className="flex flex-wrap gap-3 text-xs text-graphite" aria-hidden="true">
            {SCENARIOS.map(s => <span key={s} className="inline-flex items-center gap-1.5"><span className={`w-2.5 h-2.5 rounded-sm ${BAR_TONE[s]}`} />{SCENARIO_LABEL[s]}</span>)}
          </span>
        }>Outlook by role</SectionTitle>
        <Card className="p-6 space-y-5">
          <p className="text-sm text-graphite">Share of each role's task weight that AI does or drafts, from the company's assumptions. Point values, not ranges: no uncertainty model exists yet.</p>
          {roleIds.map(id => (
            <div key={id}>
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-medium text-ink">{titleOf(id)}{id === current && <span className="text-graphite font-normal"> · your current role</span>}</span>
              </div>
              <div className="mt-2 space-y-1.5">
                {SCENARIOS.map(s => {
                  const o = find(s, id)?.outlook
                  const width = Math.round((o?.ai_handled_share ?? 0) * SHARE_PCT)
                  return (
                    <div key={s} className="grid grid-cols-[1fr_3.5rem] items-center gap-3" aria-label={`${titleOf(id)}, ${SCENARIO_LABEL[s]}: ${share(o?.ai_handled_share)}`}>
                      <div className="h-2.5 bg-linen rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${BAR_TONE[s]}`} style={{ width: `${width}%` }} />
                      </div>
                      <span className="text-sm tabular-nums text-ink text-right">{share(o?.ai_handled_share)}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </Card>
      </section>

      {changes.length > 0 && (
        <section data-reveal>
          <SectionTitle aside={<Tag tone="marigold" icon={History}>since your last change</Tag>}>What moved recently</SectionTitle>
          <Card className="p-6">
            <ul className="space-y-3 text-sm">
              {changes.map((c, i) => (
                <li key={i}>
                  <div className="text-ink"><span className="text-graphite">{SCENARIO_LABEL[c.s]} · </span>{c.text}</div>
                  <div className="text-xs text-graphite mt-0.5">{c.because}</div>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      )}

      <section data-reveal>
        <button
          type="button" onClick={() => setMethodOpen(o => !o)} aria-expanded={methodOpen}
          className="w-full flex items-center justify-between gap-3 rounded-lg bg-surface border border-hairline px-5 py-4 text-left hover:border-hairline-strong transition-colors duration-200"
        >
          <span className="font-semibold text-ink">How we make these estimates</span>
          {methodOpen ? <ChevronUp size={20} className="text-graphite" aria-hidden="true" /> : <ChevronDown size={20} className="text-graphite" aria-hidden="true" />}
        </button>
        {methodOpen && (
          <ul className="mt-3 space-y-2 text-sm text-ink list-disc pl-5">
            <li>Each scenario is a company assumption (layer B, version {both.assistive.assumptions_version}) about who does each task: a person, AI drafting for a person, or AI.</li>
            <li>{find('assistive', current)?.outlook?.basis ?? 'Shares are derived from company assumptions.'}</li>
            <li>External evidence{latest ? ` (${latest.source}, period ${latest.period}, released ${latest.release_date})` : ''} can suggest that HR reviews an assumption; it never changes one by itself.</li>
            <li>Role ranks use the same formula in both scenarios; only the task split, and so the skill weights, differ. These are planning aids, not promises.</li>
          </ul>
        )}
      </section>

      <div data-reveal>
        <NextStepCard
          eyebrow="Ready?"
          title="Start step 1 of your pathway"
          action={<Link to={`/pathway?role=${encodeURIComponent(both.assistive.roles[0]?.role_id ?? '')}`} className={`${btn.primary} whitespace-nowrap`}>Open my pathway <ArrowRight size={16} aria-hidden="true" /></Link>}
        >
          Your pathway is planned to work in both scenarios.
        </NextStepCard>
      </div>
    </div>
  )
}
