import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Track, TrackNode } from '../types'
import { levelText } from './journey'
import { Windows, type Pane } from './Windows'

type State = 'done' | 'current' | 'locked' | 'no_course'

function videoId(url: string): string {
  return new URL(url).searchParams.get('v') ?? ''
}

// A node is done when every course planned for it is marked done (the person's own record).
function nodeDone(node: TrackNode, done: string[]): boolean {
  const planned = node.courses.filter((c) => c.planned)
  return planned.length > 0 && planned.every((c) => done.includes(c.id))
}

// Within a track, a node unlocks when the nodes before it that have courses are done.
function states(track: Track, done: string[]): State[] {
  let blocked = false
  return track.nodes.map((n) => {
    if (n.courses.every((c) => !c.planned)) return 'no_course'
    if (nodeDone(n, done)) return 'done'
    if (blocked) return 'locked'
    blocked = true
    return 'current'
  })
}

function panes(node: TrackNode, state: State, blocker: string | null, done: string[], onToggle: (id: string) => void, paused: boolean, checked: string): Pane[] {
  return [
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
                <span className="flex flex-wrap items-center gap-2">
                  <span className={`tag ${c.planned ? 'bg-violet-soft text-violet' : 'bg-mist text-graphite'}`}>{c.planned ? 'In your plan' : 'Alternative'}</span>
                  {c.planned && (state === 'locked' ? (
                    <span className="text-[12px] text-graphite">Finish &ldquo;{blocker}&rdquo; first.</span>
                  ) : (
                    <button type="button" className={`btn min-h-[34px] text-[13px] ${isDone ? '' : 'btn-v'}`} aria-pressed={isDone} disabled={paused} onClick={() => onToggle(c.id)}>
                      {isDone ? 'Done ✓ · undo' : 'Mark as done'}
                    </button>
                  ))}
                  {isDone && <Link to="/cv" className="text-[12px] font-medium text-violet">Add it to your CV →</Link>}
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
            <li key={v.id}>
              <a href={v.url} target="_blank" rel="noopener noreferrer" className="grid grid-cols-[112px_minmax(0,1fr)] gap-3 text-void no-underline hover:underline">
                <img src={`https://i.ytimg.com/vi/${videoId(v.url)}/mqdefault.jpg`} alt="" width={112} height={63} loading="lazy" className="h-[63px] w-[112px] bg-mist object-cover" />
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="font-medium leading-snug">{v.title}</span>
                  <span className="font-mono text-[11px] text-graphite">{v.channel} · {v.minutes} min · {v.published}</span>
                </span>
              </a>
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
            <li key={a.id} className="border-b border-line pb-2.5 last:border-0">
              <a href={a.url} target="_blank" rel="noopener noreferrer" className="font-medium text-void">{a.title} ↗</a>
              <span className="block font-mono text-[11px] text-graphite">{a.publisher}</span>
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
}

const LOCK_ICON = (
  <svg width="13" height="14" viewBox="0 0 11 12" aria-hidden="true"><rect x="1" y="5" width="9" height="6.5" rx="1" fill="currentColor" /><path d="M3 5V3.5a2.5 2.5 0 0 1 5 0V5" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
)

function Stop({ node, state, index, tone, blocker, onOpen }: { node: TrackNode; state: State; index: number; tone: { line: string; soft: string }; blocker: string | null; onOpen: () => void }) {
  const locked = state === 'locked'
  const ring = state === 'current' ? { boxShadow: `0 0 0 6px ${tone.soft}` } : undefined
  const fill =
    state === 'done'
      ? { background: tone.line, borderColor: tone.line, color: '#ffffff' }
      : state === 'current'
        ? { background: '#ffffff', borderColor: tone.line, color: tone.line, ...ring }
        : state === 'no_course'
          ? { background: '#ffffff', borderColor: '#9394a1', color: '#747686', borderStyle: 'dashed' as const }
          : { background: '#eceef3', borderColor: '#dcdfe7', color: '#9394a1' }
  const status = state === 'done' ? 'done' : state === 'current' ? 'next up' : state === 'locked' ? 'locked' : 'no course yet'
  return (
    <li className="road-stop">
      <span className={`road-pin ${state === 'current' ? '' : 'invisible'}`} style={{ background: tone.line }} aria-hidden="true">You are here</span>
      <button
        type="button"
        disabled={locked}
        onClick={onOpen}
        title={locked ? `Locked: finish “${blocker ?? 'the step before'}” first` : 'Open courses, videos and articles'}
        aria-label={`${node.title}: ${status}${locked ? `. Finish ${blocker ?? 'the step before'} first` : '. Open courses, videos and articles'}`}
        className="road-dot"
        style={fill}
      >
        {state === 'done' ? '✓' : locked ? LOCK_ICON : index + 1}
      </button>
      <span className={`road-label ${locked ? 'text-ash' : 'text-void'}`}>
        <span className={`block text-[14px] leading-snug ${state === 'current' ? 'font-semibold' : 'font-medium'}`}>{node.title}</span>
        <span className="mt-1 block font-mono text-[11px] text-graphite">
          {node.now !== null || node.required !== null ? `${levelText(node.now)} → ${levelText(node.after)}` : `${node.courses.length + node.videos.length + node.articles.length} resources`}
          {node.essential ? ' · essential' : ''}
        </span>
        {locked && <span className="mt-1 block text-[11px] text-ash">Unlocks after the step before</span>}
        {state === 'no_course' && <span className="mt-1 block text-[11px] text-graphite">Videos and articles only</span>}
      </span>
    </li>
  )
}

// My plan as three roads stacked top to bottom. Each road runs from Start to Finish through its
// reskilling stops; the coloured part of the road is what the person has completed.
export function TrackMap({ tracks, done, onToggle, paused, checked }: { tracks: Track[]; done: string[]; onToggle: (id: string) => void; paused: boolean; checked: string }) {
  const [open, setOpen] = useState<{ track: number; node: number } | null>(null)
  const close = useCallback(() => setOpen(null), [])
  const all = tracks.map((t) => states(t, done))
  const selected = open ? tracks[open.track].nodes[open.node] : null
  const selectedState = open ? all[open.track][open.node] : 'locked'
  // The step that keeps a stop locked: the current (next-up) stop of its track.
  const blockerOf = (ti: number) => tracks[ti].nodes.find((_, i) => all[ti][i] === 'current')?.title ?? null

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
            {n === 0 ? (
              <p className="m-0 text-[13px] text-graphite">Nothing to build on this road: you already meet these skills for this role.</p>
            ) : (
              <div className="road-scroll">
                <ol className="road" style={{ gridTemplateColumns: `repeat(${n}, minmax(150px, 1fr))`, ['--road-cols' as string]: n }}>
                  <span aria-hidden="true" className="road-line" />
                  <span aria-hidden="true" className="road-fill" style={{ background: tone.line, width: `calc((100% - 100% / ${n}) * ${fraction})` }} />
                  <span aria-hidden="true" className="road-end road-end-start">Start</span>
                  <span aria-hidden="true" className="road-end road-end-finish">Finish</span>
                  {track.nodes.map((node, ni) => (
                    <Stop key={node.id} node={node} state={st[ni]} index={ni} tone={tone} blocker={blockerOf(ti)} onOpen={() => setOpen({ track: ti, node: ni })} />
                  ))}
                </ol>
              </div>
            )}
          </section>
        )
      })}
      <p className="m-0 text-[12px] text-graphite">Click an open stop to see its courses, YouTube videos and articles. Locked stops open once the stop before them is done. Levels show you now → after the planned courses (projected, an assumption).</p>
      {open && selected && (
        <Windows
          key={`${open.track}-${open.node}`}
          title={`${tracks[open.track].title} · ${selected.title}`}
          panes={panes(selected, selectedState, blockerOf(open.track), done, onToggle, paused, checked)}
          onClose={close}
        />
      )}
    </div>
  )
}
