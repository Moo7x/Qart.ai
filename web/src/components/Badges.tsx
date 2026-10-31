import type { Badge } from '../typesScoring'

const EVENT_TEXT: Record<string, string> = {
  course_done: 'course marked done',
  course_undone: 'course undone',
  step_skipped: 'step skipped',
  level_changed: 'level changed',
  destination_chosen: 'destination chosen',
}

// Badges on the plan page (B8): each names the event that earned it and its date. They come only
// from what the person did, never from a model or a guess.
export function Badges({ badges }: { badges: Badge[] }) {
  if (!badges.length) {
    return <p className="m-0 text-[13px] text-graphite">No badges yet: they come from what you do, such as marking a course done or raising a level.</p>
  }
  return (
    <ul className="m-0 flex list-none flex-wrap gap-2 p-0" aria-label="Your badges">
      {badges.map((b) => (
        <li key={b.id} className="flex min-w-[180px] flex-col gap-0.5 rounded-md border border-violet bg-violet-soft px-3 py-2" title={b.rule}>
          <span className="text-[13px] font-semibold">{b.title}</span>
          <span className="text-[11px] text-graphite">{b.rule}</span>
          <span className="font-mono text-[11px] text-graphite">{EVENT_TEXT[b.evidence.kind] ?? b.evidence.kind} · {b.evidence.ref} · {b.earned_at.slice(0, 10)}</span>
        </li>
      ))}
    </ul>
  )
}
