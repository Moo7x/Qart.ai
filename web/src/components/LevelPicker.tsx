import { useState } from 'react'
import { levelName, useLevels } from './journey'

// Pick a level by its "I can…" sentence (docs/PHASE2_PLAN.md §8 B2): the skill's sentences 1–5
// from GET /api/pack, the highest true one wins. "None of these" is 0; "Not sure" leaves the level
// unstated (null), which is different from 0. A skill without sentences shows the scale meanings.
export function LevelPicker({
  skill,
  level,
  onChange,
  label,
  disabled = false,
  allowUnsure = true,
}: {
  skill: string
  level: number | null
  onChange: (level: number | null) => void
  label: string
  disabled?: boolean
  allowUnsure?: boolean
}) {
  const levels = useLevels()
  const [open, setOpen] = useState(level === null)
  if (!levels) return <span className="text-[12px] text-graphite">Loading the level descriptions…</span>
  const anchors = levels.skills[skill]?.anchors
  const sentence = (n: number) => anchors?.[String(n)] ?? levels.scale.find((s) => s.level === n)?.meaning ?? ''
  const options: [number | null, string, string][] = [
    ...[1, 2, 3, 4, 5].map((n): [number, string, string] => [n, levelName(levels, n), sentence(n)]),
    [0, levelName(levels, 0), 'None of these'],
    ...(allowUnsure ? [[null, 'Not sure', 'Leave it unstated for now'] as [null, string, string]] : []),
  ]
  const pick = (value: number | null) => {
    onChange(value)
    setOpen(false)
  }

  if (!open) {
    return (
      <span className="flex flex-wrap items-center justify-end gap-2 text-[12px]">
        <span className="text-graphite">{level === null ? 'Not stated' : levelName(levels, level)}</span>
        <button type="button" className="btn min-h-[44px]" disabled={disabled} onClick={() => setOpen(true)} aria-label={`Change ${label}`}>Change</button>
      </span>
    )
  }
  return (
    <div className="flex w-full flex-col gap-1">
      <span className="text-[12px] text-graphite">{levels.rules[1] ?? 'Pick the highest sentence that is true for your work.'}</span>
      <div role="radiogroup" aria-label={label} className="flex flex-col gap-px border border-hairline bg-hairline">
        {options.map(([value, name, text]) => (
          <button
            key={name}
            type="button"
            role="radio"
            aria-checked={level === value}
            disabled={disabled}
            onClick={() => pick(value)}
            className={`flex min-h-[44px] cursor-pointer items-start gap-3 border-0 px-3 py-2 text-left text-[13px] leading-snug transition-colors disabled:cursor-default ${level === value ? 'bg-violet text-white' : 'bg-white hover:bg-fog'}`}
          >
            <span className="w-[92px] shrink-0 font-mono text-[11px]">{name}</span>
            <span>{text}</span>
          </button>
        ))}
      </div>
      {anchors === undefined && <span className="text-[11px] text-graphite">No sentences for this skill yet; showing what each level means.</span>}
    </div>
  )
}
