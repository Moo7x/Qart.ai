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

// Skill levels are stored 0–4 (none … expert) and always shown on a 1–5 scale, so people read
// "3 of 5". Only the display changes: the engine, API and stored claims keep 0–4.
export const LEVEL_NAMES = ['None', 'Aware', 'Working', 'Proficient', 'Expert']
export const LEVEL_STEPS = LEVEL_NAMES.length

export function levelText(level: number | null | undefined): string {
  return level === null || level === undefined ? '—' : `${level + 1}/${LEVEL_STEPS}`
}

export function Dots({ level, tone = 'violet' }: { level: number | null; tone?: 'violet' | 'stone' | 'light' }) {
  const filled = level === null ? 0 : level + 1
  const on = tone === 'violet' ? 'bg-violet' : tone === 'light' ? 'bg-violet-light' : 'bg-stone'
  const off = tone === 'light' ? 'bg-surface' : 'bg-hairline'
  return (
    <span className="inline-flex items-center gap-2" aria-label={level === null ? 'not stated' : `${filled} of ${LEVEL_STEPS}, ${LEVEL_NAMES[level]}`}>
      <span aria-hidden="true" className="inline-flex gap-[3px]">
        {LEVEL_NAMES.map((name, i) => <span key={name} className={`h-1.5 w-3 ${i < filled ? on : off}`} />)}
      </span>
      <span aria-hidden="true" className="font-mono text-[11px]">{levelText(level)}</span>
    </span>
  )
}

// Five-step rating control: each step is a radio, filled up to the chosen level.
export function LevelPicker({ level, onChange, label, disabled = false }: { level: number | null; onChange: (level: number) => void; label: string; disabled?: boolean }) {
  return (
    <div role="radiogroup" aria-label={label} className="grid grid-cols-5 gap-px border border-hairline bg-hairline">
      {LEVEL_NAMES.map((name, i) => {
        const on = level !== null && i <= level
        return (
          <button
            key={name}
            type="button"
            role="radio"
            aria-checked={level === i}
            disabled={disabled}
            onClick={() => onChange(i)}
            className={`flex min-h-[44px] min-w-[54px] cursor-pointer flex-col items-center justify-center border-0 px-1 text-[11px] leading-tight transition-colors disabled:cursor-default ${on ? 'bg-violet text-white' : 'bg-white text-graphite hover:bg-fog'} ${level === i ? 'font-semibold' : ''}`}
          >
            <span className="font-mono text-[13px]">{i + 1}</span>
            {name}
          </button>
        )
      })}
    </div>
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
