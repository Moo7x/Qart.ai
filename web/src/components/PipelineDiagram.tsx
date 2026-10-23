import { BarChart3, Bell, Clock, Database, Download, FileText, ListChecks, Send, ShieldCheck, Target, TrendingUp } from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'
import type { Run } from '../types'

// One fixed layout (px) inside a horizontally scrollable box: lanes Collect → Understand →
// Decide → Notify, as in the approved mockup. Arrows are drawn in one SVG under the nodes.
const W = 1064
const H = 524
const SOURCE_NODES = [
  { id: 'dosm_wages_occupation', label: 'OpenDOSM API', sub: 'labour statistics', icon: Database },
  { id: 'dosm_job_market_insights', label: 'DOSM job ads', sub: 'quarterly releases', icon: Database },
  { id: 'anthropic_economic_index', label: 'Economic Index', sub: 'AI task use', icon: Database },
  { id: 'talentcorp_gbs_2024', label: 'TalentCorp study', sub: 'GBS roles · 2024', icon: FileText },
  { id: 'onet_database', label: 'O*NET database', sub: 'tasks + importance', icon: Database },
  { id: 'ilo_genai_exposure_2025', label: 'ILO exposure index', sub: 'potential · 2025', icon: FileText },
  { id: 'mycol_2024_2025', label: 'MyCOL list', sub: 'critical jobs · 2024/25', icon: FileText },
]
const SOURCE_TOP = [118, 170, 222, 274, 326, 378, 430]
const SOURCE_H = 44

export type StepId = 'schedule' | 'sources' | 'fetch' | 'validate' | 'measure' | 'label' | 'forecast' | 'match' | 'notify' | 'telegram'

type NodeProps = {
  x: number
  y: number
  w: number
  h: number
  icon: ReactNode
  title: string
  sub: string
  tone: 'cyan' | 'violet' | 'mint' | 'amber' | 'planned'
  selected: boolean
  onClick: () => void
}

const TONE: Record<NodeProps['tone'], string> = {
  cyan: 'bg-[rgba(93,227,255,0.14)] text-cyan',
  violet: 'bg-[rgba(157,134,255,0.16)] text-violet-light',
  mint: 'bg-[rgba(63,209,160,0.14)] text-mint',
  amber: 'bg-[rgba(255,168,107,0.16)] text-amber-glow',
  planned: 'bg-[rgba(255,255,255,0.06)] text-stone',
}

function Node({ x, y, w, h, icon, title, sub, tone, selected, onClick }: NodeProps) {
  const planned = tone === 'planned'
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      style={{ left: x, top: y, width: w, height: h }}
      className={`absolute flex cursor-pointer items-center gap-2.5 rounded-lg border-0 px-3 text-left text-[13px] leading-tight text-white ${
        planned
          ? 'bg-transparent shadow-[inset_0_0_0_1px_rgba(255,255,255,0.16)]'
          : 'bg-surface shadow-[inset_0_1px_0_rgba(255,255,255,0.06),inset_0_0_0_1px_rgba(255,255,255,0.04),0_4px_12px_rgba(0,0,0,0.3)] hover:bg-[#383943]'
      } ${selected ? 'outline outline-2 outline-violet-light' : ''}`}
    >
      <span className={`flex h-7 w-7 flex-none items-center justify-center rounded-md ${TONE[tone]}`}>{icon}</span>
      <span>
        <b className={`font-semibold ${planned ? 'text-[#c4c5cf]' : ''}`}>{title}</b>
        <br />
        <span className="font-mono text-[11px] text-stone">{sub}</span>
      </span>
    </button>
  )
}

function Dot({ x, y, d, axis, delay, running }: { x: number; y: number; d: number; axis: 'x' | 'y'; delay: number; running: boolean }) {
  const style = {
    left: x,
    top: y,
    '--d': `${d}px`,
    animation: `flow-${axis} 1.4s linear ${delay}s infinite`,
    animationPlayState: running ? 'running' : 'paused',
    opacity: running ? undefined : 0,
  } as CSSProperties
  return <span aria-hidden="true" className="flow-dot absolute h-2 w-2 rounded-full bg-cyan shadow-[0_0_8px_#5de3ff]" style={style} />
}

const LINES: [number, number, number, number, boolean][] = [
  // [x1, y1, x2, y2, arrowhead]
  [240, 82, 410, 82, false],
  [410, 82, 410, 170, true],
  ...SOURCE_TOP.map((t): [number, number, number, number, boolean] => [240, t + SOURCE_H / 2, 280, t + SOURCE_H / 2, false]),
  [280, SOURCE_TOP[0] + SOURCE_H / 2, 280, SOURCE_TOP[SOURCE_TOP.length - 1] + SOURCE_H / 2, false],
  [280, 204, 318, 204, true],
  [410, 236, 410, 298, true],
  [410, 364, 410, 426, true],
  [500, 460, 648, 460, true],
  [740, 428, 740, 366, true],
  [740, 300, 740, 238, true],
  [830, 204, 875, 204, false],
  [875, 164, 875, 296, false],
  [875, 164, 912, 164, true],
  [875, 296, 912, 296, true],
]

export function PipelineDiagram({ run, running, selected, onSelect }: {
  run: Run | undefined
  running: boolean
  selected: StepId
  onSelect: (step: StepId) => void
}) {
  const bySource = new Map((run?.sources ?? []).map((s) => [s.source_id, s]))
  const ok = (run?.sources ?? []).filter((s) => s.status === 'ok').length
  const total = run?.sources.length ?? 0
  return (
    <div className="overflow-x-auto">
      <div className="relative" style={{ width: W, height: H }}>
        {[
          [16, 254, 'COLLECT'],
          [286, 304, 'UNDERSTAND'],
          [606, 284, 'DECIDE'],
          [906, 150, 'NOTIFY'],
        ].map(([left, width, name]) => (
          <div key={name} className="absolute top-4 rounded-lg bg-[rgba(255,255,255,0.025)] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04)]" style={{ left: Number(left), width: Number(width), height: 492 }}>
            <span className="absolute left-3.5 top-3 font-mono text-[11px] tracking-widest text-slate-mid">{name}</span>
          </div>
        ))}
        <svg className="absolute inset-0" width={W} height={H} aria-hidden="true">
          <defs>
            <marker id="pipe-head" orient="auto" markerWidth="5" markerHeight="5" refX="2" refY="2">
              <path d="M0 0 L4 2 L0 4 Z" fill="#696a78" />
            </marker>
          </defs>
          {LINES.map(([x1, y1, x2, y2, head]) => (
            <line key={`${x1}-${y1}-${x2}-${y2}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#696a78" strokeWidth="2" strokeLinecap="round" markerEnd={head ? 'url(#pipe-head)' : undefined} />
          ))}
        </svg>
        <Dot x={276} y={200} d={40} axis="x" delay={0} running={running} />
        <Dot x={406} y={236} d={60} axis="y" delay={0.3} running={running} />
        <Dot x={406} y={364} d={60} axis="y" delay={0.6} running={running} />
        <Dot x={500} y={456} d={145} axis="x" delay={0.9} running={running} />
        <Dot x={736} y={424} d={-60} axis="y" delay={1.1} running={running} />

        <Node x={40} y={56} w={200} h={52} icon={<Clock size={16} />} title="Schedule" sub={run ? `last: ${run.trigger}` : 'no run yet'} tone="cyan" selected={selected === 'schedule'} onClick={() => onSelect('schedule')} />
        {SOURCE_NODES.map((s, i) => {
          const result = bySource.get(s.id)
          const status = result ? (result.status === 'ok' ? `ok · ${result.new} new` : 'failed · kept last good') : s.sub
          return (
            <Node key={s.id} x={40} y={SOURCE_TOP[i]} w={200} h={SOURCE_H} icon={<s.icon size={16} />} title={s.label} sub={status} tone="cyan" selected={selected === 'sources'} onClick={() => onSelect('sources')} />
          )
        })}
        <Node x={320} y={172} w={180} h={64} icon={<Download size={16} />} title="Fetch" sub={run ? `${ok} of ${total} sources ok` : 'waiting'} tone="violet" selected={selected === 'fetch'} onClick={() => onSelect('fetch')} />
        <Node x={320} y={300} w={180} h={64} icon={<ShieldCheck size={16} />} title="Validate" sub="dates, units, breaks" tone="violet" selected={selected === 'validate'} onClick={() => onSelect('validate')} />
        <Node x={320} y={428} w={180} h={64} icon={<BarChart3 size={16} />} title="Measure" sub="shares, changes, backtest" tone="violet" selected={selected === 'measure'} onClick={() => onSelect('measure')} />
        <Node x={650} y={428} w={180} h={64} icon={<ListChecks size={16} />} title="Label" sub="rules, not opinions" tone="mint" selected={selected === 'label'} onClick={() => onSelect('label')} />
        <Node x={650} y={300} w={180} h={64} icon={<TrendingUp size={16} />} title="Scenarios" sub="declared assumptions" tone="amber" selected={selected === 'forecast'} onClick={() => onSelect('forecast')} />
        <Node x={650} y={172} w={180} h={64} icon={<Target size={16} />} title="Match" sub="scores + explanations" tone="violet" selected={selected === 'match'} onClick={() => onSelect('match')} />
        <Node x={914} y={138} w={142} h={52} icon={<Bell size={16} />} title="In the app" sub="review changes" tone="mint" selected={selected === 'notify'} onClick={() => onSelect('notify')} />
        <Node x={914} y={270} w={142} h={52} icon={<Send size={16} />} title="Telegram" sub="later" tone="planned" selected={selected === 'telegram'} onClick={() => onSelect('telegram')} />
      </div>
    </div>
  )
}
