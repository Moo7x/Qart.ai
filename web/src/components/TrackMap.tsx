import { useCallback, useState } from 'react'
import { useJourney } from '../state'
import type { SkillBasis, Track, TrackNode } from '../types'
import type { PracticeStep } from '../typesScoring'
import { AgentRunWindow, BrainButton } from './AgentWindow'
import { levelText } from './journey'
import { Windows, type Pane } from './Windows'

type State = 'done' | 'current' | 'no_course'

function videoId(url: string): string {
  return new URL(url).searchParams.get('v') ?? ''
}

// A node is done when every course planned for it is marked done (the person's own record).
function nodeDone(node: TrackNode, done: string[]): boolean {
  const planned = node.courses.filter((c) => c.planned)
  return planned.length > 0 && planned.every((c) => done.includes(c.id))
}

// Steps are never locked: each is a different skill, so the person can start with any of them.
// A step with no free course still opens (videos and articles); it is marked so.
function states(track: Track, done: string[]): State[] {
  return track.nodes.map((n) => {
    if (nodeDone(n, done)) return 'done'
    if (n.courses.length === 0) return 'no_course'
    return 'current'
  })
}

const STATUS_TAG: Record<PracticeStep['status'], string> = {
  open: 'bg-mist text-graphite',
  done: 'bg-observed-bg text-observed',
  skipped: 'bg-weak-bg text-weak',
}

// Practice at work (B4): levels above what study gives come from a task agreed with a manager.
function practicePane(steps: PracticeStep[], onSkip: (id: string) => void, paused: boolean): Pane {
  return {
    key: 'practice',
    wide: true,
    title: 'Practice at work',
    hint: 'Study reaches level 2 at most; these levels come from work you do. Weeks are estimates.',
    body: (
      <ol className="m-0 flex flex-col gap-3 pl-5">
        {steps.map((p) => (
          <li key={p.id} className="flex flex-col gap-1.5">
            <span className="font-medium">To {levelText(p.target_level)}: {p.text}</span>
            <span className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-graphite">
              <span className="tag bg-estimate-bg text-estimate">Estimate</span>
              {p.time.low}–{p.time.high} weeks · to agree with your manager
            </span>
            <span className="text-[12px] text-graphite">To complete it, describe: {p.show_by} Your own re-rating moves the level.</span>
            <span className="flex flex-wrap items-center gap-2">
              <span className={`tag ${STATUS_TAG[p.status]}`}>{p.status === 'open' ? (p.locked ? 'Locked: finish this skill’s courses first' : 'Open') : `${p.status === 'done' ? 'Done' : 'Skipped'} · ${p.status_label}`}</span>
              {p.status === 'open' && <button type="button" className="btn min-h-[44px] text-[13px]" disabled={paused} onClick={() => onSkip(p.id)}>Continue anyway</button>}
            </span>
          </li>
        ))}
      </ol>
    ),
  }
}

// Owner A's scout agent on a skill stop (docs/PHASE2_PLAN.md §9): it points to the parts of the
// checked resources that teach the skill. It starts only when asked.
type OpenAgent = (resourceId?: string, resourceTitle?: string) => void

const WHY_TAG: Record<SkillBasis['kind'], [string, string]> = {
  talentcorp: ['TalentCorp names it for this role', 'bg-observed-bg text-observed'],
  onet: ['Used in this job\'s tasks', 'bg-observed-bg text-observed'],
  onet_tech: ['Employers ask for it', 'bg-observed-bg text-observed'],
  assumption: ['Our assumption', 'bg-estimate-bg text-estimate'],
  ai_trend: ['Where AI is taking this skill', 'bg-estimate-bg text-estimate'],
}

// Adapt steps: resources on doing this skill's work with AI, each with the two checked quotes.
function aiPane(node: TrackNode): Pane[] {
  if (!node.mode || (node.mode !== 'oversee' && node.mode !== 'use_ai')) return []
  const items = node.ai_resources ?? []
  return [{
    key: 'ai',
    title: 'Doing this with AI',
    hint: 'Checked: each one shows this skill’s work and AI used on it (quotes from the page or video).',
    body: items.length === 0 ? (
      <div className="flex flex-col gap-2">
        <p className="m-0 text-graphite">No checked resource on doing this skill with AI yet. {node.basics?.length ? 'Start with these AI basics; the courses beside cover the skill itself.' : 'The courses beside cover the skill itself.'}</p>
        {(node.basics ?? []).length > 0 && (
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {(node.basics ?? []).map((b) => (
              <li key={b.url} className="flex flex-col gap-0.5">
                <a href={b.url} target="_blank" rel="noopener noreferrer" className="font-medium text-void">{b.title} ↗</a>
                <span className="font-mono text-[11px] text-graphite">AI basics · {b.topic} · {b.provider} · {b.kind} · {b.minutes} min</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    ) : (
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {items.map((r) => (
          <li key={r.id} className="flex flex-col gap-1 border-b border-line pb-2.5 last:border-0">
            <a href={r.url} target="_blank" rel="noopener noreferrer" className="font-medium text-void">{r.title} ↗</a>
            <span className="font-mono text-[11px] text-graphite">{r.provider} · {r.kind === 'video' ? 'video' : 'course'} · {r.minutes} min</span>
            <span className="text-[12px] text-[#404040]">AI on this work: &ldquo;{r.ai_quote}&rdquo;</span>
          </li>
        ))}
      </ul>
    ),
  }]
}

// Why this skill is on the plan at all, with its source (src/match/basis.py).
function whyPane(node: TrackNode): Pane[] {
  if (!node.why) return []
  const [tag, tone] = WHY_TAG[node.why.kind]
  return [{
    key: 'why',
    wide: true,
    title: 'Why you need this',
    hint: node.essential ? 'Essential for this role' : 'Counts toward your fit for this role',
    body: (
      <div className="flex flex-col gap-2">
        <span className={`tag self-start ${tone}`}>{tag}</span>
        <p className="m-0">{node.why.text}</p>
        <span className="font-mono text-[11px] text-graphite">{node.why.source}</span>
      </div>
    ),
  }]
}

function panes(node: TrackNode, done: string[], onToggle: (id: string) => void, onSkip: (id: string) => void, paused: boolean, checked: string, onAgent: OpenAgent): Pane[] {
  const practice = node.practice?.length ? [practicePane(node.practice, onSkip, paused)] : []
  return [
    ...whyPane(node),
    ...aiPane(node),
    ...practice,
    {
      key: 'courses',
      title: 'Courses',
      hint: 'Free and checked. Courses marked “In your plan” count towards your hours and fit.',
      body: node.courses.length === 0 ? (
        <p className="m-0 text-graphite">No verified free course for this yet. The videos and articles are a start; ask your L&amp;D team about paid options.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {node.courses.map((c) => {
            const isDone = done.includes(c.id)
            return (
              <li key={c.id} className="flex flex-col gap-1.5 border-b border-line pb-3 last:border-0">
                <a href={c.url} target="_blank" rel="noopener noreferrer" className="font-medium text-void">{c.title} ↗</a>
                <span className="font-mono text-[11px] text-graphite">{c.provider} · {c.minutes < 60 ? `${c.minutes} min` : `${(c.minutes / 60).toFixed(1)} h`} · {c.level}</span>
                {c.fit_check?.result === 'fits' && (
                  <span className="text-[11px] text-graphite">Fit checked automatically ({c.fit_check.by}, {c.fit_check.checked}) from the course page: &ldquo;{c.fit_check.quote}&rdquo;</span>
                )}
                <span className="flex flex-wrap items-center gap-2">
                  <span className={`tag ${c.planned ? 'bg-violet-soft text-violet' : 'bg-mist text-graphite'}`}>{c.planned ? 'In your plan' : 'Alternative'}</span>
                  {c.planned && (
                    <button type="button" className={`btn min-h-[34px] text-[13px] ${isDone ? '' : 'btn-v'}`} aria-pressed={isDone} disabled={paused} onClick={() => onToggle(c.id)}>
                      {isDone ? 'Done ✓ · undo' : 'Mark as done'}
                    </button>
                  )}
                </span>
              </li>
            )
          })}
        </ul>
      ),
    },
    {
      key: 'videos',
      title: 'YouTube',
      hint: `Channel, length and date checked ${checked}. Extra watching, not counted in your hours.`,
      body: node.videos.length === 0 ? (
        <p className="m-0 text-graphite">No checked video for this yet.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {node.videos.map((v) => (
            <li key={v.id} className="flex items-start gap-3">
              <a href={v.url} target="_blank" rel="noopener noreferrer" className="grid min-w-0 flex-auto grid-cols-[112px_minmax(0,1fr)] gap-3 text-void no-underline hover:underline">
                <img src={`https://i.ytimg.com/vi/${videoId(v.url)}/mqdefault.jpg`} alt="" width={112} height={63} loading="lazy" className="h-[63px] w-[112px] bg-mist object-cover" />
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="font-medium leading-snug">{v.title}</span>
                  <span className="font-mono text-[11px] text-graphite">{v.channel} · {v.minutes} min · {v.published}</span>
                </span>
              </a>
              <BrainButton label={`AI agent: open “${v.title}” at the key minute`} onClick={() => onAgent(v.id, v.title)} />
            </li>
          ))}
        </ul>
      ),
    },
    {
      key: 'articles',
      title: 'Articles',
      hint: `Pages from standards bodies, professional bodies and official docs, checked ${checked}.`,
      body: node.articles.length === 0 ? (
        <p className="m-0 text-graphite">No checked article for this yet.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
          {node.articles.map((a) => (
            <li key={a.id} className="flex items-start gap-3 border-b border-line pb-2.5 last:border-0">
              <span className="min-w-0 flex-auto">
                <a href={a.url} target="_blank" rel="noopener noreferrer" className="font-medium text-void">{a.title} ↗</a>
                <span className="block font-mono text-[11px] text-graphite">{a.publisher}{a.is_article === false ? ' · web page' : ''}</span>
              </span>
              {a.is_article !== false && <BrainButton label={`AI agent: show the important passages of “${a.title}”`} onClick={() => onAgent(a.id, a.title)} />}
            </li>
          ))}
        </ul>
      ),
    },
  ]
}

// Each track has its own colour, shared with the with/without-AI comparison below.
const TRACK_TONE: Record<Track['id'], { line: string; soft: string; label: string }> = {
  ai_basics: { line: '#138a72', soft: '#e3f4ef', label: 'Start here' },
  without_ai: { line: '#d9771f', soft: '#fcefe3', label: 'Without AI' },
  with_ai: { line: '#6c47ff', soft: '#f1edff', label: 'With AI' },
  path: { line: '#6c47ff', soft: '#f1edff', label: 'Your path' },
}

const MODE_TAG: Record<string, string> = { oversee: 'adapt: oversee AI', use_ai: 'adapt: use AI', learn: 'new for this role', basics: 'AI basics' }

function Stop({ node, state, index, tone, onOpen, first }: { node: TrackNode; state: State; index: number; tone: { line: string; soft: string }; onOpen: () => void; first: boolean }) {
  const ring = state === 'current' ? { boxShadow: `0 0 0 6px ${tone.soft}` } : undefined
  const fill =
    state === 'done'
      ? { background: tone.line, borderColor: tone.line, color: '#ffffff' }
      : state === 'current'
        ? { background: '#ffffff', borderColor: tone.line, color: tone.line, ...ring }
        : { background: '#ffffff', borderColor: '#9394a1', color: '#747686', borderStyle: 'dashed' as const }
  const status = state === 'done' ? 'done' : state === 'current' ? 'next up' : 'no course yet'
  return (
    <li className="road-stop">
      <span className={`road-pin ${first ? '' : 'invisible'}`} style={{ background: tone.line }} aria-hidden="true">Start here</span>
      <button
        type="button"
        onClick={onOpen}
        title="Open courses, videos and articles"
        aria-label={`${node.title}: ${status}. Open courses, videos and articles`}
        className="road-dot"
        style={fill}
      >
        {state === 'done' ? '✓' : index + 1}
      </button>
      <span className="road-label text-void">
        <span className={`block text-[14px] leading-snug ${state === 'current' ? 'font-semibold' : 'font-medium'}`}>{node.title}</span>
        <span className="mt-1 block font-mono text-[11px] text-graphite">
          {node.mode === 'oversee' || node.mode === 'use_ai'
            ? `you: ${levelText(node.now)}${node.ai_use != null ? ` · ${node.ai_use.toFixed(0)}% AI use on its tasks` : ''}`
            : node.now !== null || node.required !== null ? `${levelText(node.now)} → ${levelText(node.study_after ?? node.after)} by study${node.practice?.length ? ` · practice to ${levelText(node.required)}` : ''}` : `${node.courses.length + node.videos.length + node.articles.length} resources`}
          {node.essential ? ' · essential' : ''}
        </span>
        {node.mode && <span className="mt-1 block text-[11px] text-graphite">{MODE_TAG[node.mode]}</span>}
        {state === 'no_course' && <span className="mt-1 block text-[11px] text-graphite">Videos and articles only</span>}
      </span>
    </li>
  )
}

// My plan as three roads stacked top to bottom. Each road runs from Start to Finish through its
// reskilling stops; the coloured part of the road is what the person has completed.
export function TrackMap({ tracks, done, onToggle, onSkip, paused, checked }: { tracks: Track[]; done: string[]; onToggle: (id: string) => void; onSkip: (id: string) => void; paused: boolean; checked: string }) {
  const { profileId } = useJourney()
  const [open, setOpen] = useState<{ track: number; node: number } | null>(null)
  const [agent, setAgent] = useState<{ skill: string; skillName: string; resourceId?: string; resourceTitle?: string } | null>(null)
  const [showSkipped, setShowSkipped] = useState(false)
  const close = useCallback(() => setOpen(null), [])
  const all = tracks.map((t) => states(t, done))
  const selected = open ? tracks[open.track].nodes[open.node] : null

  return (
    <div className="road-map">
      {tracks.map((track, ti) => {
        const st = all[ti]
        const tone = TRACK_TONE[track.id]
        const finished = st.filter((s) => s === 'done').length
        const countable = st.filter((s) => s !== 'no_course').length
        const n = track.nodes.length
        // How far along the road the colour reaches: up to the current stop, or the end.
        const reached = st.every((s) => s === 'done' || s === 'no_course') ? n - 1 : Math.max(st.indexOf('current'), 0)
        const fraction = n > 1 ? reached / (n - 1) : 1
        return (
          <section key={track.id} aria-label={track.title} className="road-track">
            <header className="road-head">
              <span aria-hidden="true" className="road-marker" style={{ background: tone.line }}>{ti + 1}</span>
              <div className="min-w-0">
                <span className="font-mono text-[11px] uppercase tracking-widest" style={{ color: tone.line }}>{tone.label}</span>
                <h3 className="m-0 text-[19px] font-semibold tracking-tight">{track.title}</h3>
                <p className="m-0 mt-1 max-w-[560px] text-[13px] text-graphite">{track.why}</p>
              </div>
              <div className="road-progress" aria-label={`${finished} of ${countable} steps done`}>
                <span className="font-mono text-[13px] font-semibold">{finished}/{countable}</span>
                <span className="text-[11px] text-graphite"> steps done</span>
                <span className="mt-1.5 block h-1.5 w-28 overflow-hidden rounded-full bg-mist" aria-hidden="true">
                  <span className="block h-full rounded-full" style={{ width: `${countable ? (100 * finished) / countable : 0}%`, background: tone.line }} />
                </span>
              </div>
            </header>
            {track.shown === false && !showSkipped ? (
              <div className="flex flex-wrap items-center gap-3 text-[13px]">
                <span className="tag bg-observed-bg text-observed">Adjusted for you</span>
                <span className="text-graphite">{track.reason}</span>
                <button type="button" className="btn min-h-[44px]" onClick={() => setShowSkipped(true)}>Show AI basics anyway</button>
              </div>
            ) : n === 0 ? (
              <p className="m-0 text-[13px] text-graphite">Nothing to build on this road: you already meet these skills for this role.</p>
            ) : (
              <div className="road-scroll">
                <ol className="road" style={{ gridTemplateColumns: `repeat(${n}, minmax(150px, 1fr))`, ['--road-cols' as string]: n }}>
                  <span aria-hidden="true" className="road-line" />
                  <span aria-hidden="true" className="road-fill" style={{ background: tone.line, width: `calc((100% - 100% / ${n}) * ${fraction})` }} />
                  <span aria-hidden="true" className="road-end road-end-start">Start</span>
                  <span aria-hidden="true" className="road-end road-end-finish">Finish</span>
                  {track.nodes.map((node, ni) => (
                    <Stop key={node.id} node={node} state={st[ni]} index={ni} tone={tone} first={ni === st.findIndex((x) => x !== 'done')} onOpen={() => setOpen({ track: ti, node: ni })} />
                  ))}
                </ol>
              </div>
            )}
          </section>
        )
      })}
      <p className="m-0 text-[12px] text-graphite">Click any stop to see its courses, YouTube videos and articles; start with whichever skill you like. Levels show you now → after the planned courses (projected, an assumption); levels above 2 need practice at work.</p>
      {open && selected && (
        <Windows
          key={`${open.track}-${open.node}`}
          title={`${tracks[open.track].title} · ${selected.title}`}
          panes={panes(selected, done, onToggle, onSkip, paused, checked, (resourceId, resourceTitle) => {
            // A skill stop runs on its skill; an AI-basics stop on its topic.
            const basics = selected.mode === 'basics' || tracks[open.track].id === 'ai_basics'
            setAgent({ skill: basics ? selected.id : selected.skill ?? selected.id, skillName: selected.title, resourceId, resourceTitle })
            setOpen(null)
          })}
          onClose={close}
        />
      )}
      {agent && <AgentRunWindow skill={agent.skill} skillName={agent.skillName} profileId={profileId} resourceId={agent.resourceId} resourceTitle={agent.resourceTitle} onClose={() => setAgent(null)} />}
    </div>
  )
}
