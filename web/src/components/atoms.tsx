import { ArrowUpRight, ChevronRight } from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useJourney } from '../state'
import type { Scenario } from '../types'

// Shared pieces of the redesign (design-prototype/ app.py atoms). Styles live in index.css
// (.q-*, .v-*); the "Why?" control and its panel stay in Why.tsx and Windows.tsx.

/** The italic accent word of a heading. */
export function Serif({ children }: { children: ReactNode }) {
  return <span className="serif">{children}</span>
}

export type Kind = 'observed' | 'assumption' | 'estimate'

/** The label every number carries: OBSERVED (source + date), ASSUMPTION or ESTIMATE. */
export function Label({ kind }: { kind: Kind }) {
  return <span className={`q-label q-label-${kind}`}>{kind}</span>
}

/** A person's level is always a claim, never verified. */
export function Claim({ children = 'claim' }: { children?: ReactNode }) {
  return <span className="q-claim">{children}</span>
}

export function Card({ label, className = '', children }: { label: string; className?: string; children: ReactNode }) {
  return (
    <article aria-label={label} className={`q-card ${className}`}>
      {children}
    </article>
  )
}

export function PageHead({ badge, title, sub, right }: { badge: string; title: ReactNode; sub?: ReactNode; right?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex min-w-0 max-w-[760px] flex-col gap-3.5">
        <span className="q-head-badge">{badge}</span>
        <h1 className="q-h1">{title}</h1>
        {sub && <p className="m-0 text-[15px] leading-relaxed text-[#404040]">{sub}</p>}
      </div>
      {right}
    </header>
  )
}

/** The main step forward: an ink pill with a round arrow. */
export function DarkLink({ to, children, onClick }: { to: string; children: ReactNode; onClick?: () => void }) {
  return (
    <Link to={to} onClick={onClick} className="q-btn q-btn-dark self-start">
      {children}
      <span className="q-btn-arrow" aria-hidden="true"><ChevronRight size={16} /></span>
    </Link>
  )
}

export function DarkButton({ children, onClick, disabled }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} className="q-btn q-btn-dark self-start">
      {children}
      <span className="q-btn-arrow" aria-hidden="true"><ChevronRight size={16} /></span>
    </button>
  )
}

/** Two-option switch; each option is a toggle button (aria-pressed). */
export function Segmented<T extends string>({ label, value, options, onChange, white }: { label: string; value: T; options: { id: T; text: string }[]; onChange: (v: T) => void; white?: boolean }) {
  return (
    <div role="group" aria-label={label} className={`q-seg ${white ? 'q-seg-white' : ''}`}>
      {options.map((o) => (
        <button key={o.id} type="button" aria-pressed={value === o.id} onClick={() => onChange(o.id)}>{o.text}</button>
      ))}
    </div>
  )
}

export const SCENARIO_TEXT: Record<Scenario, string> = { moderate: 'Moderate AI adoption', fast: 'Fast AI adoption' }

/** The scenario switch, shared by every page through the journey state. */
export function ScenarioSwitch({ white = true }: { white?: boolean }) {
  const { scenario, setScenario } = useJourney()
  return (
    <Segmented
      label="Scenario"
      value={scenario}
      white={white}
      onChange={setScenario}
      options={[{ id: 'moderate', text: SCENARIO_TEXT.moderate }, { id: 'fast', text: SCENARIO_TEXT.fast }]}
    />
  )
}

export function Legend({ items }: { items: { swatch: string; text: string }[] }) {
  return (
    <ul aria-label="Legend" className="q-legend">
      {items.map((i) => (
        <li key={i.text}><i aria-hidden="true" style={{ background: i.swatch }} />{i.text}</li>
      ))}
    </ul>
  )
}

/** Chart | Table switch for every chart. */
export function ViewSwitch({ value, onChange }: { value: 'chart' | 'table'; onChange: (v: 'chart' | 'table') => void }) {
  return <Segmented label="Show as" value={value} onChange={onChange} options={[{ id: 'chart', text: 'Chart' }, { id: 'table', text: 'Table' }]} />
}

type Vivid = 'lime' // the plan's badges tile; the other themes went with the Overview tiles
const BLOB: Record<Vivid, [string, string, string]> = {
  lime: ['rgba(250,255,215,.85)', 'rgba(170,205,60,.6)', 'rgba(90,130,20,.45)'],
}

function Blob({ theme, size, style, delay = 0 }: { theme: Vivid; size: number; style: CSSProperties; delay?: number }) {
  const [c1, c2, shade] = BLOB[theme]
  return (
    <div
      aria-hidden="true"
      className="v-blob"
      style={{
        ...style,
        width: size,
        height: size,
        animationDelay: `-${delay}s`,
        background: `radial-gradient(circle at 32% 28%, rgba(255,255,255,.95) 0%, rgba(255,255,255,.5) 14%, ${c1} 40%, ${c2} 76%)`,
        boxShadow: `inset -18px -26px 50px ${shade}, inset 14px 18px 30px rgba(255,255,255,.55), 0 30px 60px rgba(0,0,0,.16)`,
      }}
    />
  )
}

/** A vivid tile: deep gradient, glossy blob, white pill label, round arrow link. White text only
 *  on the darker gradients; lime carries ink. */
export function VividTile({ theme, pill, to, toLabel, label, className = '', children }: { theme: Vivid; pill: string; to?: string; toLabel?: string; label: string; className?: string; children: ReactNode }) {
  return (
    <article aria-label={label} className={`v-tile v-${theme} ${className}`}>
      <Blob theme={theme} size={220} style={{ right: -60, bottom: -70 }} />
      <Blob theme={theme} size={90} style={{ right: 120, top: -30 }} delay={6} />
      <div className="v-body">
        <div className="flex items-center justify-between gap-2.5">
          <span className="v-pill">{pill}</span>
          {to && (
            <Link to={to} aria-label={toLabel ?? pill} className="v-arrow">
              <ArrowUpRight size={18} aria-hidden="true" />
            </Link>
          )}
        </div>
        {children}
      </div>
    </article>
  )
}
