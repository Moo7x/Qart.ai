import type { RadarAxis } from '../types'

// Radar of one role's skills: needed level, your claimed level, and the level after the pathway.
// Levels use the app's 0–4 scale (none · aware · working · proficient · expert).
const SIZE = 320
const CENTRE = SIZE / 2
const RADIUS = 102
const MAX_LEVEL = 4

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

export function SkillRadar({ axes }: { axes: RadarAxis[] }) {
  const n = axes.length
  if (n < 3) return null
  return (
    <svg viewBox={`-130 -30 ${SIZE + 260} ${SIZE + 60}`} className="w-full max-w-[580px]" role="img" aria-label="Skills radar: needed, yours and after the pathway">
      {[1, 2, 3, 4].map((level) => (
        <polygon key={level} points={axes.map((_, i) => point(i, n, level).join(',')).join(' ')} fill="none" stroke="#dcdfe7" strokeWidth="1" />
      ))}
      {axes.map((a, i) => {
        const [x, y] = point(i, n, MAX_LEVEL)
        const [lx, ly] = point(i, n, MAX_LEVEL + 0.55)
        const anchor = Math.abs(lx - CENTRE) < 8 ? 'middle' : lx > CENTRE ? 'start' : 'end'
        return (
          <g key={a.skill}>
            <line x1={CENTRE} y1={CENTRE} x2={x} y2={y} stroke="#dcdfe7" strokeWidth="1" />
            <text x={lx} y={ly} textAnchor={anchor} className="fill-graphite text-[12px]">
              {labelLines(a.name).map((line, i, lines) => <tspan key={i} x={lx} dy={i === 0 ? -(lines.length - 1) * 7 : 14}>{line}</tspan>)}
            </text>
          </g>
        )
      })}
      <polygon points={polygon(axes, (a) => a.required)} fill="rgba(154,70,9,0.06)" stroke="#9a4609" strokeWidth="1.5" strokeDasharray="4 3" />
      <polygon points={polygon(axes, (a) => a.after)} fill="rgba(31,95,191,0.08)" stroke="#1f5fbf" strokeWidth="1.5" />
      <polygon points={polygon(axes, (a) => a.claimed ?? 0)} fill="rgba(108,71,255,0.18)" stroke="#6c47ff" strokeWidth="2" />
    </svg>
  )
}
