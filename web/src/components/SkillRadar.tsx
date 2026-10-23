import type { RadarAxis } from '../types'

// Radar of one role's skills: needed level, your claimed level, and the level after the pathway.
// Levels use the app's 0–4 scale (none · aware · working · proficient · expert).
const SIZE = 320
const CENTRE = SIZE / 2
const RADIUS = 118
const MAX_LEVEL = 4

function point(i: number, n: number, level: number): [number, number] {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  const r = (RADIUS * level) / MAX_LEVEL
  return [CENTRE + r * Math.cos(angle), CENTRE + r * Math.sin(angle)]
}

function polygon(axes: RadarAxis[], level: (a: RadarAxis) => number) {
  return axes.map((a, i) => point(i, axes.length, level(a)).join(',')).join(' ')
}

function shortName(name: string) {
  return name.length > 22 ? `${name.slice(0, 20)}…` : name
}

export function SkillRadar({ axes }: { axes: RadarAxis[] }) {
  const n = axes.length
  if (n < 3) return null
  return (
    <svg viewBox={`-100 -10 ${SIZE + 200} ${SIZE + 20}`} className="w-full max-w-[500px]" role="img" aria-label="Skills radar: needed, yours and after the pathway">
      {[1, 2, 3, 4].map((level) => (
        <polygon key={level} points={axes.map((_, i) => point(i, n, level).join(',')).join(' ')} fill="none" stroke="#3a3b44" strokeWidth="1" />
      ))}
      {axes.map((a, i) => {
        const [x, y] = point(i, n, MAX_LEVEL)
        const [lx, ly] = point(i, n, MAX_LEVEL + 0.55)
        const anchor = Math.abs(lx - CENTRE) < 8 ? 'middle' : lx > CENTRE ? 'start' : 'end'
        return (
          <g key={a.skill}>
            <line x1={CENTRE} y1={CENTRE} x2={x} y2={y} stroke="#3a3b44" strokeWidth="1" />
            <text x={lx} y={ly} textAnchor={anchor} dominantBaseline="middle" className="fill-[#c4c5cf] text-[10px]">
              {shortName(a.name)}
            </text>
          </g>
        )
      })}
      <polygon points={polygon(axes, (a) => a.required)} fill="rgba(255,168,107,0.10)" stroke="#ffa86b" strokeWidth="1.5" strokeDasharray="4 3" />
      <polygon points={polygon(axes, (a) => a.after)} fill="rgba(93,227,255,0.10)" stroke="#5de3ff" strokeWidth="1.5" />
      <polygon points={polygon(axes, (a) => a.claimed ?? 0)} fill="rgba(157,134,255,0.28)" stroke="#9d86ff" strokeWidth="2" />
    </svg>
  )
}
