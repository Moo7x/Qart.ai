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

function NodeMark({ state, index }: { state: State; index: number }) {
  const base = 'relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded border text-[12px] font-semibold'
  if (state === 'done') return <span className={`${base} border-violet bg-violet text-white`}>✓</span>
  if (state === 'current') return <span className={`${base} border-violet bg-paper text-violet ring-4 ring-violet-soft`}>{index + 1}</span>
  if (state === 'no_course') return <span className={`${base} border-dashed border-stone bg-fog text-ash`}>–</span>
  return (
    <span className={`${base} border-line bg-fog text-ash`}>
      <svg width="11" height="12" viewBox="0 0 11 12" aria-hidden="true"><rect x="1" y="5" width="9" height="6.5" rx="1" fill="currentColor" /><path d="M3 5V3.5a2.5 2.5 0 0 1 5 0V5" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
    </span>
  )
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

// My plan as three tracks stacked top to bottom; each track's reskilling steps run to its right.
export function TrackMap({ tracks, done, onToggle, paused, checked }: { tracks: Track[]; done: string[]; onToggle: (id: string) => void; paused: boolean; checked: string }) {
  const [open, setOpen] = useState<{ track: number; node: number } | null>(null)
  const close = useCallback(() => setOpen(null), [])
  const all = tracks.map((t) => states(t, done))
  const selected = open ? tracks[open.track].nodes[open.node] : null
  const selectedState = open ? all[open.track][open.node] : 'locked'
  // The step that keeps the opened one locked: the nearest earlier step in its track not done.
  const blocker = open
    ? tracks[open.track].nodes.filter((_, i) => i < open.node && all[open.track][i] === 'current').at(0)?.title ?? null
    : null

  return (
    <div className="relative flex flex-col gap-0">
      {tracks.map((track, ti) => {
        const st = all[ti]
        const finished = st.filter((s) => s === 'done').length
        const countable = st.filter((s) => s !== 'no_course').length
        const last = ti === tracks.length - 1
        return (
          <section key={track.id} aria-label={track.title} className="track-row">
            <div className="relative flex gap-3">
              {!last && <span aria-hidden="true" className="track-spine" />}
              <span aria-hidden="true" className={`relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded font-mono text-[14px] font-semibold ${countable > 0 && finished === countable ? 'bg-violet text-white' : 'bg-void text-white'}`}>{ti + 1}</span>
              <div className="flex min-w-0 flex-col gap-1 pt-1">
                <h3 className="m-0 text-[17px] font-semibold tracking-tight">{track.title}</h3>
                <span className="text-[12px] text-graphite">{track.why}</span>
                <span className="font-mono text-[11px] uppercase tracking-wider text-ash">{finished}/{countable} done{track.nodes.length > countable ? ` · ${track.nodes.length - countable} without a course` : ''}</span>
              </div>
            </div>
            {track.nodes.length === 0 ? (
              <p className="m-0 self-center text-[13px] text-graphite">Nothing to build here: you already meet these skills for this role.</p>
            ) : (
              <ol className="track-skills">
                {track.nodes.map((node, ni) => (
                  <li key={node.id} className="min-w-0">
                    <button
                      type="button"
                      onClick={() => setOpen({ track: ti, node: ni })}
                      className={`skill-node skill-node-${st[ni]} group`}
                      aria-label={`${node.title}: ${st[ni] === 'done' ? 'done' : st[ni] === 'current' ? 'next up' : st[ni] === 'locked' ? 'locked' : 'no course yet'}. Open courses, videos and articles`}
                    >
                      <span className="flex w-full items-center justify-between gap-3"><NodeMark state={st[ni]} index={ni} /><span className="text-xs font-medium">{st[ni] === 'current' ? 'Next up ↗' : st[ni] === 'done' ? 'Done' : st[ni] === 'locked' ? 'Locked' : 'No planned course'}</span></span>
                      <span className="text-[15px] font-semibold leading-snug text-void group-hover:underline">{node.title}</span>
                      <span className="font-mono text-[11px] text-graphite">
                        {node.now !== null || node.required !== null ? `${levelText(node.now)} → ${levelText(node.after)}` : `${node.courses.length + node.videos.length + node.articles.length} resources`}
                        {node.essential ? ' · ★' : ''}
                      </span>
                      <span className="mt-auto pt-1 text-xs text-graphite">Courses · videos · articles →</span>
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </section>
        )
      })}
      <p className="m-0 text-[11px] text-graphite">Click a step to open its courses, YouTube videos and articles. ★ marks an essential skill. Levels show you now → after the planned courses (projected, an assumption).</p>
      {open && selected && (
        <Windows
          key={`${open.track}-${open.node}`}
          title={`${tracks[open.track].title} · ${selected.title}`}
          panes={panes(selected, selectedState, blocker, done, onToggle, paused, checked)}
          onClose={close}
        />
      )}
    </div>
  )
}
