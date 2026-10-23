import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Briefcase, CircleCheck, Clock, ExternalLink, Info, Search, Star, TrendingUp, TriangleAlert } from 'lucide-react'
import { getHiringNow, getRanking } from '../api'
import { SignalBadge } from '../components/SignalParts'
import { useReveal } from '../motion'
import { useUserId } from '../persona'
import type { HiringNow, RankedRoleView, RankingGapItem, RankingResponse, RankingWeights, ScenarioName } from '../types'
import { btn, Card, Drawer, EmptyState, Highlight, input as inputCls, Loading, PageHeader, ProvenanceTag, SectionTitle, Tag, type Tone } from '../ui'

const BAND_TONE: Record<string, Tone> = { 'Strong match': 'action', 'Good match': 'marigold', Stretch: 'linen' }
const BANDS = ['All', 'Strong match', 'Good match', 'Stretch'] as const
const BAND_FILTER: Record<(typeof BANDS)[number], string> = { All: 'All', 'Strong match': 'Strong matches', 'Good match': 'Good matches', Stretch: 'Stretch' }
const RELATION: Record<string, string> = { same: 'Same field', adjacent: 'Nearby move', far: 'New field' }
// Ring stroke per band: the band word sits next to the ring, so colour never carries meaning alone.
const RING: Record<string, string> = { 'Strong match': '#0075de', 'Good match': '#e89d01', Stretch: '#a39e98' }

// Breakdown colours, validated with the dataviz palette script (all checks pass; saffron is
// under 3:1 on white, so every segment's points are also written as text in the legend).
const PARTS: { key: keyof RankingWeights; name: string; color: string }[] = [
  { key: 'skill', name: 'Skills', color: '#0075de' },
  { key: 'momentum', name: 'Market momentum', color: '#e89d01' },
  { key: 'direction', name: 'Direction fit', color: '#0f9d8a' },
  { key: 'feasibility', name: 'Time to get there', color: '#f64932' },
]

const points = (role: RankedRoleView, key: keyof RankingWeights, scenario: ScenarioName) =>
  role.scenarios[scenario].weights[key] * role.components[key] * 100

function levelWord(value: number, levels: RankingResponse['levels']): string {
  if (value <= 0) return 'Not yet'
  return [...levels].reverse().find(l => value >= l.value)?.label ?? levels[0].label
}

const initials = (name: string) => name.split(/[\s/&()-]+/).filter(w => /^[A-Z]/.test(w)).slice(0, 2).map(w => w[0]).join('')

/** Match score as a ring (role fit, not skill mastery: no percent sign). */
function ScoreRing({ score, band, size = 52 }: { score: number; band: string; size?: number }) {
  const r = size / 2 - 4
  const c = 2 * Math.PI * r
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`Match score ${score} of 100, ${band}`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-linen)" strokeWidth={4} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={RING[band]} strokeWidth={4} strokeLinecap="round" strokeDasharray={`${(score / 100) * c} ${c}`} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold text-ink tabular-nums">{score}</span>
    </div>
  )
}

function Avatar({ name, large = false }: { name: string; large?: boolean }) {
  return (
    <span aria-hidden="true" className={`${large ? 'w-14 h-14 text-lg rounded-xl' : 'w-11 h-11 text-sm rounded-full'} shrink-0 bg-midnight text-white font-semibold flex items-center justify-center`}>
      {initials(name)}
    </span>
  )
}

function Chip({ children, tone = 'plain', icon: Icon }: { children: ReactNode; tone?: 'plain' | 'action' | 'marigold'; icon?: typeof Clock }) {
  const cls = { plain: 'bg-linen text-graphite', action: 'bg-action-tint text-action-ink', marigold: 'bg-marigold-tint text-marigold-ink' }[tone]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs ${cls}`}>
      {Icon && <Icon size={12} aria-hidden="true" />}
      {children}
    </span>
  )
}

const coreHave = (role: RankedRoleView) => {
  const core = role.matched_skills.filter(m => m.is_core)
  return `${core.filter(m => m.has_it).length} of ${core.length} core skills`
}
const fits = (role: RankedRoleView) => role.gap_hours === 0 || role.available_hours >= role.gap_hours
const rising = (role: RankedRoleView) => Object.values(role.momentum_skills).filter(l => l === 'rising').length

function RoleCard({ role, selected, onSelect }: { role: RankedRoleView; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button" onClick={onSelect} aria-pressed={selected}
      className={`w-full text-left rounded-xl border bg-surface p-5 transition-colors duration-200 ${selected ? 'border-action ring-2 ring-action/30' : 'border-hairline hover:border-hairline-strong'}`}
    >
      <div className="flex items-start justify-between gap-3">
        <Avatar name={role.name} />
        <ScoreRing score={role.score} band={role.band} />
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <Tag tone={BAND_TONE[role.band]}>{role.band}</Tag>
        <Tag tone="linen">{RELATION[role.relation]}</Tag>
        {rising(role) > 0 && <Tag tone="action" icon={TrendingUp}>Rising skills</Tag>}
      </div>
      <h3 className="mt-2 text-lg font-semibold text-ink leading-snug">{role.name}</h3>
      <p className="text-sm text-graphite"><span className="text-ink font-medium">{role.family_name}</span>{role.source_title ? ` / ${role.source_title}` : ''}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <Chip icon={Star}>{coreHave(role)}</Chip>
        <Chip icon={Clock}>~{Math.round(role.gap_hours)} h to close the gap</Chip>
        <Chip tone={fits(role) ? 'action' : 'marigold'}>{fits(role) ? 'Fits your plan' : 'Beyond your plan'}</Chip>
      </div>
    </button>
  )
}

function Breakdown({ role, scenario }: { role: RankedRoleView; scenario: ScenarioName }) {
  const s = role.scenarios[scenario]
  return (
    <div className="space-y-2">
      <div className="flex h-2.5 w-full gap-[2px] rounded-full bg-linen overflow-hidden" role="img"
        aria-label={`Score ${s.score}: ${PARTS.map(p => `${p.name} ${Math.round(points(role, p.key, scenario))}`).join(', ')}`}>
        {PARTS.map(p => <div key={p.key} style={{ width: `${points(role, p.key, scenario)}%`, background: p.color }} className="h-full first:rounded-l-full" />)}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-graphite">
        {PARTS.map(p => (
          <li key={p.key} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden="true" />
            {p.name} <span className="tabular-nums text-ink">{Math.round(points(role, p.key, scenario))}</span>
          </li>
        ))}
        {s.exposure_points > 0 && <li className="text-ink tabular-nums">− {s.exposure_points} AI exposure</li>}
        {s.capped && <li className="text-ink">capped at {s.score}</li>}
      </ul>
    </div>
  )
}

function GapRow({ item, order }: { item: RankingGapItem; order: number }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-md border border-hairline px-3 py-2.5">
      <span className="w-6 text-sm text-graphite tabular-nums">{order}</span>
      <span className="font-medium text-ink">{item.label}</span>
      {item.is_core && <Tag tone="action" icon={Star}>Core</Tag>}
      <span className="inline-flex items-center gap-1 text-xs text-graphite tabular-nums"><Clock size={12} aria-hidden="true" /> ~{Math.round(item.hours)} h</span>
      {item.momentum_label === 'no_data' ? <Tag tone="linen">No market data</Tag> : <SignalBadge label={item.momentum_label} />}
    </div>
  )
}

function GapList({ role }: { role: RankedRoleView }) {
  if (role.gap.length === 0) return <p className="text-sm text-graphite">You already meet the level this role asks for in every skill.</p>
  const firstBeyond = role.gap.findIndex(g => !g.fits_timeframe)
  return (
    <div className="space-y-2">
      <p className="text-sm text-graphite">Core skills first, then what lifts your match most per hour. Your plan has <span className="tabular-nums text-ink">{Math.round(role.available_hours)} h</span>.</p>
      <ol className="space-y-2">
        {role.gap.map((g, i) => (
          <li key={g.skill_id}>
            {i === firstBeyond && (
              <div className="my-3 flex items-center gap-2 text-xs font-medium text-coral-ink" role="separator">
                <span className="h-px flex-1 bg-coral/40" /> Beyond your current plan <span className="h-px flex-1 bg-coral/40" />
              </div>
            )}
            <GapRow item={g} order={i + 1} />
          </li>
        ))}
      </ol>
    </div>
  )
}

function Calculation({ role, data }: { role: RankedRoleView; data: RankingResponse }) {
  const s = role.scenarios[data.scenario]
  const other: ScenarioName = data.scenario === 'moderate' ? 'fast' : 'moderate'
  return (
    <div className="space-y-5 text-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <caption className="sr-only">Components of the score</caption>
          <thead className="text-xs text-graphite"><tr><th className="py-1 font-medium">Component</th><th className="py-1 font-medium text-right">Value (0–1)</th><th className="py-1 font-medium text-right">Weight</th><th className="py-1 font-medium text-right">Points</th></tr></thead>
          <tbody className="tabular-nums">
            {PARTS.map(p => (
              <tr key={p.key} className="border-t border-hairline">
                <td className="py-1.5 text-ink">{p.name}</td>
                <td className="py-1.5 text-right">{role.components[p.key].toFixed(2)}</td>
                <td className="py-1.5 text-right">{s.weights[p.key]}</td>
                <td className="py-1.5 text-right">{points(role, p.key, data.scenario).toFixed(1)}</td>
              </tr>
            ))}
            {s.exposure_points > 0 && <tr className="border-t border-hairline"><td className="py-1.5 text-ink" colSpan={3}>AI exposure ({s.label})</td><td className="py-1.5 text-right">−{s.exposure_points}</td></tr>}
            <tr className="border-t border-hairline-strong font-semibold text-ink"><td className="py-1.5" colSpan={3}>Score{s.capped ? ' (capped: under half the core skills)' : ''}</td><td className="py-1.5 text-right">{s.score}</td></tr>
          </tbody>
        </table>
      </div>
      <p className="text-graphite">{s.note} In the other scenario ({role.scenarios[other].label.toLowerCase()}) it is a <span className="text-ink">{role.scenarios[other].band.toLowerCase()}</span> at <span className="tabular-nums text-ink">{role.scenarios[other].score}</span>.</p>
      <div>
        <h4 className="text-xs font-medium text-graphite mb-1.5">Skills: your level vs what the role asks for</h4>
        <ul className="divide-y divide-hairline">
          {role.matched_skills.map(m => (
            <li key={m.skill_id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
              <span className="text-ink">{m.name} {m.is_core && <span className="text-xs text-graphite">(core)</span>}</span>
              <span className={`text-xs ${m.has_it ? 'text-action-ink font-medium' : 'text-graphite'}`}>{levelWord(m.user_level, data.levels)} · needs {levelWord(m.required_level, data.levels)}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="space-y-1.5 text-xs text-graphite">
        <p>
          Market momentum: {Object.keys(role.momentum_skills).length > 0
            ? Object.entries(role.momentum_skills).map(([k, v]) => `${role.matched_skills.find(m => m.skill_id === k)?.name ?? k} ${v}`).join(', ')
            : 'no tracked core skill, so neutral'}. Source: {data.trend.source} · data to {data.trend.data_as_of}{data.trend.stale ? ' (stale)' : ''}.
        </p>
        {role.ai_use_evidence && (
          <p>AI use in this occupation: {role.ai_use_evidence.automation_pct.toFixed(0)}% of AI conversations about it were automation rather than help ({role.ai_use_evidence.source}, {role.ai_use_evidence.period}). Shown as evidence; it does not change the score.</p>
        )}
      </div>
    </div>
  )
}

/** Open job-board postings this week in the same type of work (real data, never a score input). */
function HiringLine({ role, hiring }: { role: RankedRoleView; hiring: HiringNow | null }) {
  const fam = hiring?.families.find(f => f.family === role.family)
  if (!hiring || !fam) return null
  return (
    <p className="flex gap-2 text-sm text-ink">
      <Briefcase size={16} className="mt-0.5 shrink-0 text-graphite" aria-hidden="true" />
      <span>
        <span className="tabular-nums font-medium">{fam.total}</span> open {role.family_name.toLowerCase()} postings in {hiring.region_label} on public job boards this week
        {fam.share_pct !== null && <>; <span className="tabular-nums">{fam.share_pct.toFixed(0)}%</span> mention AI</>}.
        <span className="block text-xs text-graphite">{hiring.meta.coverage?.companies.length ?? 0} companies' Greenhouse, Lever and Ashby boards · data to {hiring.meta.data_as_of}</span>
      </span>
    </p>
  )
}

function RoleDetail({ role, data, hiring }: { role: RankedRoleView; data: RankingResponse; hiring: HiringNow | null }) {
  const [calc, setCalc] = useState(false)
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <Avatar name={role.name} large />
        <div className="flex items-center gap-2">
          <ScoreRing score={role.score} band={role.band} size={60} />
          {role.source_url && (
            <a href={role.source_url} target="_blank" rel="noreferrer" title={`O*NET ${role.source_code}`} aria-label={`Open the O*NET occupation ${role.source_code}`} className="rounded-md p-2 text-graphite hover:bg-linen hover:text-ink">
              <ExternalLink size={18} aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
      <div className="space-y-2">
        <div className="flex flex-wrap gap-1.5">
          <Tag tone={BAND_TONE[role.band]}>{role.band}</Tag>
          <Tag tone="linen">{RELATION[role.relation]}</Tag>
          <Tag tone="linen">{data.scenarios[data.scenario].label}</Tag>
        </div>
        <h2 className="text-2xl font-semibold text-ink leading-tight">{role.name}</h2>
        <p className="text-sm text-graphite">
          <span className="text-ink font-medium">{role.family_name}</span>
          {role.source_title ? ` / O*NET ${role.source_code} ${role.source_title}` : ' / O*NET occupation not confirmed yet'}
        </p>
        <div className="flex flex-wrap gap-1.5">
          <Chip icon={Star}>{coreHave(role)}</Chip>
          <Chip icon={Clock}>~{Math.round(role.gap_hours)} h gap · {Math.round(role.available_hours)} h in your plan</Chip>
          <Chip>{data.scenarios[data.scenario === 'moderate' ? 'fast' : 'moderate'].label}: {role.scenarios[data.scenario === 'moderate' ? 'fast' : 'moderate'].band} ({role.scenarios[data.scenario === 'moderate' ? 'fast' : 'moderate'].score})</Chip>
        </div>
      </div>

      <div className={`flex items-center gap-3 rounded-xl border p-4 ${fits(role) ? 'border-action/30 bg-action-tint' : 'border-marigold/40 bg-marigold-tint'}`}>
        {fits(role) ? <CircleCheck size={20} className="shrink-0 text-action-ink" aria-hidden="true" /> : <TriangleAlert size={20} className="shrink-0 text-marigold-ink" aria-hidden="true" />}
        <p className="text-sm font-medium text-ink">{fits(role) ? 'The skills gap fits the time in your plan.' : 'The skills gap needs more time than your plan has; a longer timeframe would fit it.'}</p>
      </div>
      <Link to={`/app/pathway?role=${role.role_id}`} className={`${btn.primary} w-full sm:w-auto`}>Build my learning plan for this role <ArrowRight size={16} aria-hidden="true" /></Link>

      <section className="rounded-xl border border-hairline p-5 space-y-3">
        <h3 className="text-lg font-semibold text-ink">Why this role</h3>
        <ul className="space-y-1.5 text-sm text-ink list-disc pl-5">{role.reasons.map(r => <li key={r}>{r}</li>)}</ul>
        {role.flags.length > 0 && <ul className="flex flex-wrap gap-1.5">{role.flags.map(f => <li key={f}><Tag tone="marigold" icon={TriangleAlert}>{f}</Tag></li>)}</ul>}
        <Breakdown role={role} scenario={data.scenario} />
        <HiringLine role={role} hiring={hiring} />
      </section>

      <section className="space-y-3">
        <h3 className="text-lg font-semibold text-ink">Your skills gap</h3>
        <GapList role={role} />
      </section>

      <section className="border-t border-hairline pt-4">
        <button type="button" onClick={() => setCalc(v => !v)} aria-expanded={calc} className={btn.text}>
          <Info size={14} aria-hidden="true" /> How this score was calculated
        </button>
        {calc && <div className="mt-3"><Calculation role={role} data={data} /></div>}
      </section>
    </div>
  )
}

/** Ranked future roles: a list of compact cards and the selected role's detail (Domain 1 must-haves 3 and 6). */
export default function Matches() {
  const userId = useUserId()
  const [scenario, setScenario] = useState<ScenarioName>('moderate')
  const [data, setData] = useState<RankingResponse | null>(null)
  const [hiring, setHiring] = useState<HiringNow | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [band, setBand] = useState<(typeof BANDS)[number]>('All')
  const [selected, setSelected] = useState<string | null>(null)
  const [drawer, setDrawer] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  useReveal(root, [data !== null])

  useEffect(() => {
    getRanking(userId, scenario).then(d => { setData(d); setError(null) }).catch(() => setError('Could not load your matches.'))
  }, [userId, scenario])
  useEffect(() => { getHiringNow().then(setHiring).catch(() => setHiring(null)) }, [])

  const roles = useMemo(() => (data?.roles ?? []).filter(r =>
    (band === 'All' || r.band === band) &&
    (query.trim() === '' || `${r.name} ${r.family_name} ${r.source_title ?? ''}`.toLowerCase().includes(query.trim().toLowerCase())),
  ), [data, band, query])

  if (error) return <EmptyState title="Matches unavailable">{error}</EmptyState>
  if (!data) return <Loading what="your matches" />

  const current = roles.find(r => r.role_id === selected) ?? roles[0]
  const choose = (id: string) => {
    setSelected(id)
    if (window.matchMedia('(max-width: 1023px)').matches) setDrawer(true)
  }

  return (
    <div ref={root} className="max-w-6xl mx-auto space-y-5">
      <div data-reveal>
        <PageHeader
          title={<>Your <Highlight>matches</Highlight> <span className="text-lg font-normal text-graphite tabular-nums">{data.roles.length} roles</span></>}
          intro="Ranked from your skills, the market trend for those skills, the direction you chose and the time you have. You decide; this only suggests."
          aside={<ProvenanceTag kind="assumption">Estimates, not predictions</ProvenanceTag>}
        />
      </div>

      <Card data-reveal className="p-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div role="radiogroup" aria-label="Future scenario" className="flex flex-wrap gap-2">
          {(Object.keys(data.scenarios) as ScenarioName[]).map(s => (
            <button
              key={s} type="button" role="radio" aria-checked={scenario === s} onClick={() => setScenario(s)}
              className={`rounded-full px-3.5 py-2 text-sm transition-colors duration-200 ${scenario === s ? 'bg-action-tint text-action-ink font-medium' : 'bg-surface border border-hairline-strong text-graphite hover:bg-linen'}`}
            >
              {data.scenarios[s].label}
            </button>
          ))}
        </div>
        <p className="text-sm text-graphite lg:max-w-md">{data.scenarios[scenario].description}</p>
      </Card>

      {data.empty_profile ? (
        <Card data-reveal className="p-6 space-y-3">
          <SectionTitle>Not enough to rank yet</SectionTitle>
          <p className="text-sm text-graphite">{data.message} Meanwhile, these roles are common first steps:</p>
          <ul className="flex flex-wrap gap-2">{data.starter_roles.map(r => <li key={r.role_id}><Tag tone="linen">{r.name}</Tag></li>)}</ul>
          <Link to="/onboarding/1" className={btn.primary}>Add skills in Find my path <ArrowRight size={16} aria-hidden="true" /></Link>
        </Card>
      ) : (
        <>
          <div data-reveal className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Filter by band">
              {BANDS.map(b => (
                <button key={b} type="button" role="radio" aria-checked={band === b} onClick={() => setBand(b)}
                  className={`rounded-full px-3 py-1.5 text-sm transition-colors duration-200 ${band === b ? 'bg-ink text-white' : 'bg-surface border border-hairline-strong text-graphite hover:bg-linen'}`}>
                  {BAND_FILTER[b]} <span className="tabular-nums opacity-70">{b === 'All' ? data.roles.length : data.roles.filter(r => r.band === b).length}</span>
                </button>
              ))}
            </div>
            <label className="relative block sm:w-72">
              <span className="sr-only">Search roles</span>
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-graphite" aria-hidden="true" />
              <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search roles…" className={`${inputCls} w-full pl-9 rounded-full`} />
            </label>
          </div>

          {roles.length === 0 ? (
            <EmptyState title="No roles match">Try another band or search term.</EmptyState>
          ) : (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start">
              <ol className="space-y-3" aria-label="Ranked roles">
                {roles.map(r => <li key={r.role_id}><RoleCard role={r} selected={current?.role_id === r.role_id} onSelect={() => choose(r.role_id)} /></li>)}
              </ol>
              {current && (
                <Card className="hidden lg:block p-6 sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto">
                  <RoleDetail role={current} data={data} hiring={hiring} />
                </Card>
              )}
            </div>
          )}
          {current && (
            <Drawer open={drawer} onClose={() => setDrawer(false)} title={current.name}>
              <RoleDetail role={current} data={data} hiring={hiring} />
            </Drawer>
          )}
        </>
      )}

      <p data-reveal className="text-xs text-graphite">
        Market trend: {data.trend.source} · data to {data.trend.data_as_of}{data.trend.stale ? ' (stale)' : ''} ·{' '}
        <Link to="/sources" className="text-action-ink hover:underline">all data sources</Link>. Bands come first: a score of 73 is not meaningfully better than 71.
      </p>
    </div>
  )
}
