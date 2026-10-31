import type { RadarAxis } from '../types'

// Radar of one role's skills: needed level, your claimed level, and the level after the pathway.
// Levels use the app's 0–5 scale (none · novice · aware · working · proficient · expert).
const SIZE = 320
const CENTRE = SIZE / 2
const RADIUS = 102
const MAX_LEVEL = 5

function point(i: number, n: number, level: number): [number, number] {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  const r = (RADIUS * level) / MAX_LEVEL
  return [CENTRE + r * Math.cos(angle), CENTRE + r * Math.sin(angle)]
}

function polygon(axes: RadarAxis[], level: (a: RadarAxis) => number) {
  return axes.map((a, i) => point(i, axes.length, level(a)).join(',')).join(' ')
}

function labelLines(name: string): string[] {
  const lines: string[] = ['']
  for (const word of name.split(' ')) {
    const last = lines.length - 1
    if (lines[last].length + word.length > 20 && lines[last]) lines.push(word)
    else lines[last] += `${lines[last] ? ' ' : ''}${word}`
  }
  return lines
}

export const RADAR_COLOURS = { you: '#5b5bd6', needed: '#c2508f', after: '#0072B2' }

export function SkillRadar({ axes }: { axes: RadarAxis[] }) {
  const n = axes.length
  if (n < 3) return null
  return (
    <svg viewBox={`-150 -40 ${SIZE + 300} ${SIZE + 80}`} className="w-full max-w-[680px]" role="img" aria-label={`Skills radar: ${axes.map((a) => `${a.name}, you ${a.claimed ?? 'not rated'}, needs ${a.required}, after the plan ${a.after}`).join('; ')}`}>
      <defs>
        <radialGradient id="radar-disc" cx="50%" cy="45%" r="60%">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#efeaff" />
        </radialGradient>
        <filter id="radar-soft" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="10" stdDeviation="12" floodColor="#6c47ff" floodOpacity="0.12" />
        </filter>
      </defs>
      {[5, 4, 3, 2, 1].map((level) => (
        <circle key={level} cx={CENTRE} cy={CENTRE} r={(RADIUS * level) / MAX_LEVEL + (level === 5 ? 14 : 0)} fill="url(#radar-disc)" filter={level === 5 ? 'url(#radar-soft)' : undefined} stroke="#ffffff" strokeWidth="2" />
      ))}
      {axes.map((a, i) => {
        const [x, y] = point(i, n, MAX_LEVEL)
        const [lx, ly] = point(i, n, MAX_LEVEL + 0.75)
        const anchor = Math.abs(lx - CENTRE) < 8 ? 'middle' : lx > CENTRE ? 'start' : 'end'
        const lines = labelLines(a.name)
        return (
          <g key={a.skill}>
            <line x1={CENTRE} y1={CENTRE} x2={x} y2={y} stroke="#e4ddff" strokeWidth="1" />
            <text x={lx} y={ly} textAnchor={anchor} className="fill-muted text-[12px]">
              {lines.map((line, j) => <tspan key={j} x={lx} dy={j === 0 ? -(lines.length - 1) * 7 - 6 : 14}>{line}</tspan>)}
              <tspan x={lx} dy={15} className="fill-ink text-[12px] font-semibold">you {a.claimed ?? '—'} · needs {a.required}</tspan>
            </text>
          </g>
        )
      })}
      <polygon points={polygon(axes, (a) => a.required)} fill="rgba(194,80,143,0.07)" stroke={RADAR_COLOURS.needed} strokeWidth="2" strokeDasharray="5 4" strokeLinejoin="round" />
      <polygon points={polygon(axes, (a) => a.after)} fill="none" stroke={RADAR_COLOURS.after} strokeWidth="1.5" strokeLinejoin="round" />
      <polygon points={polygon(axes, (a) => a.claimed ?? 0)} fill="rgba(91,91,214,0.12)" stroke={RADAR_COLOURS.you} strokeWidth="2.5" strokeLinejoin="round" />
      {axes.map((a, i) => {
        const [x, y] = point(i, n, a.required)
        return <circle key={a.skill} cx={x} cy={y} r="4" fill="#fff" stroke={RADAR_COLOURS.needed} strokeWidth="2" />
      })}
    </svg>
  )
}
