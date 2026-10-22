import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, ExternalLink } from 'lucide-react'
import FlowSteps from '../components/FlowSteps'
import { getPath, getRecommendation, getSdg } from '../api'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import { skillName } from '../skillNames'
import type { PathPlan, RoleRecommendation, SdgMap, SdgTarget } from '../types'
import { btn, Card, EmptyState, Highlight, label, Loading, NextStepCard, PageHeader, ProvenanceTag, SectionTitle, StatTile, Tag } from '../ui'

function TargetCard({ target }: { target: SdgTarget }) {
  return (
    <Card className="p-5 flex gap-4">
      <span className="w-12 h-12 rounded-lg bg-action-tint text-action-ink flex flex-col items-center justify-center shrink-0" aria-hidden="true">
        <span className="text-[10px] font-medium leading-none">SDG</span>
        <span className="text-lg font-semibold leading-tight tabular-nums">{target.goal}</span>
      </span>
      <div className="min-w-0 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-ink">Target {target.id}</span>
          {target.main && <Tag tone="marigold">Main target</Tag>}
        </div>
        <p className="text-sm text-ink">{target.title}</p>
        <p className="text-sm text-graphite"><strong className="font-medium text-ink">Why Qart tags it: </strong>{target.rationale}</p>
        <a href={target.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-action-ink hover:underline">
          UN Goal {target.goal} page <ExternalLink size={12} aria-hidden="true" />
        </a>
      </div>
    </Card>
  )
}

export default function Impact() {
  const userId = useUserId()
  const [params, setParams] = useSearchParams()
  const [sdg, setSdg] = useState<SdgMap | null>(null)
  const [roles, setRoles] = useState<RoleRecommendation[]>([])
  const [path, setPath] = useState<PathPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [loading])

  const roleId = params.get('role') ?? roles[0]?.role_id ?? null

  useEffect(() => {
    Promise.all([getSdg(), getRecommendation(userId, 'assistive')])
      .then(([map, rec]) => { setSdg(map); setRoles(rec.roles) })
      .catch(() => setSdg(null))
      .finally(() => setLoading(false))
  }, [userId])

  useEffect(() => {
    if (roleId) getPath(userId, roleId).then(setPath).catch(() => setPath(null))
  }, [userId, roleId])

  if (loading) return <Loading what="SDG impact" />
  if (!sdg) {
    return (
      <div className="max-w-3xl mx-auto">
        <FlowSteps />
        <EmptyState title="Could not load the SDG map">The server did not respond. Check that the backend is running.</EmptyState>
      </div>
    )
  }

  const targetsById = Object.fromEntries(sdg.targets.map(t => [t.id, t]))
  const roleLink = roleId ? sdg.roles[roleId] : undefined
  const roleTargets = (roleLink?.targets ?? []).map(id => targetsById[id]).filter(Boolean)
  const pathSkills = [...new Set(path?.steps.flatMap(s => s.skills) ?? [])]
  const taggedSkills = pathSkills.filter(id => sdg.skills[id])
  const goals = new Set(roleTargets.map(t => t.goal))

  return (
    <div ref={root} className="max-w-3xl mx-auto space-y-8">
      <FlowSteps />
      <div data-reveal>
        <PageHeader
          title={<>How your path helps the Global <Highlight>Goals</Highlight></>}
          intro="Each role and skill in Qart is tagged to UN Sustainable Development Goal targets. Here is what your chosen path contributes to."
          aside={<ProvenanceTag kind="assumption">team's declared mapping · {sdg.retrieved}</ProvenanceTag>}
        />
      </div>

      <div data-reveal className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-ink" id="role-label">Showing goals for</span>
        <div role="radiogroup" aria-labelledby="role-label" className="inline-flex flex-wrap bg-linen rounded-md p-1">
          {roles.map(r => (
            <button
              key={r.role_id} role="radio" aria-checked={roleId === r.role_id}
              onClick={() => setParams({ role: r.role_id })}
              className={`px-3 py-1.5 rounded-sm text-sm transition-colors duration-200 ${roleId === r.role_id ? 'bg-surface text-ink font-medium shadow-[0_1px_2px_rgb(0_0_0/0.06)]' : 'text-graphite hover:text-ink'}`}
            >
              {r.title ?? r.role_id}
            </button>
          ))}
        </div>
      </div>

      <div data-reveal className="grid grid-cols-3 gap-3">
        <StatTile tone="action" label="Goals" value={goals.size} />
        <StatTile tone="marigold" label="Targets for this role" value={roleTargets.length} />
        <StatTile tone="linen" label="Path skills tagged" value={`${taggedSkills.length} of ${pathSkills.length}`} />
      </div>

      <section data-reveal className="space-y-3">
        <SectionTitle>Targets this role contributes to</SectionTitle>
        {roleLink?.rationale && <p className="font-serif text-lg leading-[1.56] text-ink">{roleLink.rationale}</p>}
        {roleTargets.length === 0
          ? <EmptyState title="No targets tagged for this role">The catalogue declares no SDG target for it.</EmptyState>
          : roleTargets.map(t => <TargetCard key={t.id} target={t} />)}
      </section>

      {taggedSkills.length > 0 && (
        <section data-reveal>
          <SectionTitle>Skills on your pathway, mapped to targets</SectionTitle>
          <Card className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th scope="col" className={`${label} py-3 px-4`}>Skill</th>
                  <th scope="col" className={`${label} py-3 px-4`}>Targets</th>
                  <th scope="col" className={`${label} py-3 px-4`}>Why</th>
                </tr>
              </thead>
              <tbody>
                {taggedSkills.map(id => (
                  <tr key={id} className="border-t border-hairline align-top">
                    <th scope="row" className="py-2.5 px-4 text-left font-normal text-ink whitespace-nowrap">{skillName(id)}</th>
                    <td className="py-2.5 px-4"><span className="flex flex-wrap gap-1">{sdg.skills[id].targets.map(t => <Tag key={t} tone="linen">SDG {t}</Tag>)}</span></td>
                    <td className="py-2.5 px-4 text-graphite">{sdg.skills[id].rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </section>
      )}

      <p data-reveal className="text-xs text-graphite">{sdg.about}</p>

      <div data-reveal>
        <NextStepCard
          eyebrow="Step 6"
          title="How your plan holds up in two possible futures"
          action={<Link to="/scenarios" className={`${btn.primary} whitespace-nowrap`}>Explore scenarios <ArrowRight size={16} aria-hidden="true" /></Link>}
        >
          Nobody knows how fast AI will change work, so we compare both company scenarios.
        </NextStepCard>
      </div>
    </div>
  )
}
