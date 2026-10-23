import { useJourney } from '../state'

// Official UN SDG colours (un.org brand guidelines) for the goals the pack uses.
const SDG_COLOUR: Record<number, string> = { 4: '#C5192D', 8: '#A21942', 12: '#BF8B2E', 13: '#3F7E44' }

export function SdgTag({ target }: { target: string }) {
  const goal = Number(target.split('.')[0])
  return (
    <span className="tag font-mono text-white" style={{ background: SDG_COLOUR[goal] ?? '#5e5f6e' }}>
      SDG {target}
    </span>
  )
}

export function Dots({ level, of = 4, tone = 'violet' }: { level: number | null; of?: number; tone?: 'violet' | 'stone' | 'light' }) {
  const n = level ?? 0
  const colour = tone === 'violet' ? 'text-violet' : tone === 'light' ? 'text-violet-light' : 'text-stone'
  return (
    <span className={`font-mono tracking-[3px] ${colour}`} aria-label={level === null ? 'not stated' : `level ${n} of ${of}`}>
      {'●'.repeat(n)}
      {'○'.repeat(of - n)}
    </span>
  )
}

function segClass(active: boolean): string {
  return `min-h-[32px] cursor-pointer rounded px-3 text-[13px] border-0 ${active ? 'bg-void font-medium text-white' : 'bg-transparent text-graphite'}`
}

export function ScenarioSwitch() {
  const { scenario, setScenario } = useJourney()
  return (
    <div className="flex items-center gap-2.5">
      <div role="group" aria-label="Scenario" className="card-light flex rounded-md p-[3px]">
        <button type="button" aria-pressed={scenario === 'moderate'} className={segClass(scenario === 'moderate')} onClick={() => setScenario('moderate')}>
          Moderate AI adoption
        </button>
        <button type="button" aria-pressed={scenario === 'fast'} className={segClass(scenario === 'fast')} onClick={() => setScenario('fast')}>
          Fast AI adoption
        </button>
      </div>
      <span className="tag bg-estimate-bg text-estimate">Estimate</span>
    </div>
  )
}
