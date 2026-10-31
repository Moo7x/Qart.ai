import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { sendJSON } from '../api'
import { CvPopup } from '../pages/onboarding/CvPopup'
import { useJourney } from '../state'
import type { RadarAxis } from '../types'
import { Claim, OVERVIEW_SCENARIO } from './atoms'
import { LEVEL_MAX } from './journey'
import { LevelPicker } from './LevelPicker'
import { SurveyPopup } from './SkillSurvey'

// "Your skills" on the Overview: a radar of the role's skills on the 0–5 scale, your claimed level
// against the level TalentCorp sets for the role. An unrated skill's label rates it in place (its
// own claim, POST /answer); "Rate next skill" asks the skills that would change your options most.

const COLOUR = { you: '#6c47ff', needed: '#b4457f' }
// The drawing box: centre and the radius of level LEVEL_MAX; labels sit just outside it.
const W = 600
const H = 500
const CX = W / 2
const CY = H / 2
const R = 160
const LABEL_LEVEL = LEVEL_MAX * 1.16

function point(i: number, n: number, level: number): [number, number] {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  const r = (R * level) / LEVEL_MAX
  return [CX + r * Math.cos(angle), CY + r * Math.sin(angle)]
}

const polygon = (axes: RadarAxis[], level: (a: RadarAxis) => number) => axes.map((a, i) => point(i, axes.length, level(a)).join(',')).join(' ')
const at = (x: number, y: number) => ({ left: `${(100 * x) / W}%`, top: `${(100 * y) / H}%` })

function RatePopup({ axis, onClose, onSaved }: { axis: RadarAxis; onClose: () => void; onSaved: () => void }) {
  const { profileId } = useJourney()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  async function save(level: number | null) {
    if (level === null || !profileId) return
    setBusy(true)
    setError(null)
    try {
      await sendJSON(`/api/profiles/${profileId}/answer`, { body: { skill: axis.skill, level } })
      onSaved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
      setBusy(false)
    }
  }
  return (
    <CvPopup onClose={onClose}>
      <section aria-label={`Rate ${axis.name}`} className="flex min-w-0 flex-[1_1_100%] flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2.5 pr-12">
          <h2 id="j-title" className="m-0 text-[clamp(24px,3.4vw,34px)] font-medium leading-[1.1] tracking-[-0.02em]">How would you rate your {axis.name}?</h2>
          <Claim>your own rating</Claim>
        </div>
        <p className="m-0 text-sm text-[#404040]">This role needs level {axis.required}. Pick the highest sentence that is true for your work in the last two years.</p>
        <div className="max-w-[460px]">
          <LevelPicker skill={axis.skill} level={null} label={`Your level in ${axis.name}`} disabled={busy} allowUnsure={false} onChange={(level) => void save(level)} />
        </div>
        {error && <p role="alert" className="m-0 text-xs text-weak">{error}</p>}
      </section>
    </CvPopup>
  )
}

function Label({ axis, i, n, onRate }: { axis: RadarAxis; i: number; n: number; onRate: () => void }) {
  const [x, y] = point(i, n, LABEL_LEVEL)
  const side = Math.abs(x - CX) < 12 ? 'middle' : x > CX ? 'start' : 'end'
  const shift = side === 'middle' ? (y < CY ? 'translate(-50%,-100%)' : 'translate(-50%,0)') : side === 'start' ? 'translate(0,-50%)' : 'translate(-100%,-50%)'
  const align = side === 'middle' ? 'text-center' : side === 'start' ? 'text-left' : 'text-right'
  const value = `you ${axis.claimed ?? '—'} · needs ${axis.required}`
  const style = { ...at(x, y), transform: shift }
  const body = (
    <>
      <span className="block text-muted">{axis.name}</span>
      <span className="block font-semibold text-ink">{value}{axis.claimed === null && <span className="text-violet"> · Rate →</span>}</span>
    </>
  )
  // On a phone the labels around the radar are too small; the list under it takes their place.
  const cls = `absolute hidden w-max max-w-[23%] text-[12px] leading-tight sm:block ${align}`
  return axis.claimed === null ? (
    <button type="button" onClick={onRate} style={style} aria-label={`Rate ${axis.name}: not rated, needs ${axis.required}`} className={`${cls} cursor-pointer rounded-lg border-0 bg-transparent px-1 py-0.5 font-[inherit] hover:bg-violet-soft focus-visible:bg-violet-soft`}>
      {body}
    </button>
  ) : (
    <span style={style} className={cls}>{body}</span>
  )
}

/** `onChanged` runs after any rating is saved, so the whole Overview reads the new claims. */
export function SkillRadar({ axes, title, onChanged }: { axes: RadarAxis[]; title: string; onChanged: () => void }) {
  const { profileId } = useJourney()
  const [rating, setRating] = useState<RadarAxis | null>(null)
  const [survey, setSurvey] = useState(false)
  const n = axes.length
  const unrated = axes.filter((a) => a.claimed === null).length
  const spokes = axes.map((_, i) => { const [x, y] = point(i, n, LEVEL_MAX); return `M${CX} ${CY}L${x.toFixed(1)} ${y.toFixed(1)}` }).join(' ')
  return (
    <section aria-label="Your skills" className="flex flex-1 flex-col gap-4 rounded-[28px] bg-white p-5 sm:p-6">
      <div className="flex flex-col gap-1">
        <h2 className="m-0 text-[18px] font-medium">Your level vs. what the role needs</h2>
        <span className="text-[12px] text-muted">{title} · {n} skills · levels 0–{LEVEL_MAX}</span>
      </div>

      {n >= 3 && (
        // Takes the column's spare height, so the three columns end level with no empty band.
        <div className="flex flex-1 items-center">
        <div
          role="img"
          aria-label={`Skills radar for ${title}, levels 0 to ${LEVEL_MAX}: ${axes.map((a) => `${a.name} you ${a.claimed ?? 'not rated'}, needs ${a.required}`).join('; ')}`}
          className="relative w-full"
          style={{ aspectRatio: `${W} / ${H}` }}
        >
          <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 h-full w-full" aria-hidden="true">
            <circle cx={CX} cy={CY} r={R + 14} fill="#f1edff" />
            <circle cx={CX} cy={CY} r={R} fill="#f8f6ff" stroke="#fff" strokeWidth="2" />
            {Array.from({ length: LEVEL_MAX - 1 }, (_, k) => <circle key={k} cx={CX} cy={CY} r={(R * (k + 1)) / LEVEL_MAX} fill="none" stroke="#fff" strokeWidth="2" />)}
            <path d={spokes} stroke="#e4ddff" strokeWidth="1" />
            <polygon points={polygon(axes, (a) => a.required)} fill="rgba(180,69,127,0.07)" stroke={COLOUR.needed} strokeWidth="2" strokeDasharray="6 5" strokeLinejoin="round" />
            <polygon points={polygon(axes, (a) => a.claimed ?? 0)} fill="rgba(108,71,255,0.18)" stroke={COLOUR.you} strokeWidth="2.5" strokeLinejoin="round" />
            {axes.map((a, i) => { const [x, y] = point(i, n, a.required); return <circle key={`n-${a.skill}`} cx={x} cy={y} r="4.5" fill="#fff" stroke={COLOUR.needed} strokeWidth="2" /> })}
            {axes.map((a, i) => { if (a.claimed === null) return null; const [x, y] = point(i, n, a.claimed); return <circle key={`y-${a.skill}`} cx={x} cy={y} r="4.5" fill={COLOUR.you} /> })}
          </svg>
          {axes.map((a, i) => <Label key={a.skill} axis={a} i={i} n={n} onRate={() => setRating(a)} />)}
        </div>
        </div>
      )}

      <ul className="m-0 flex list-none flex-col p-0 sm:hidden">
        {axes.map((a) => (
          <li key={a.skill} className="flex items-center justify-between gap-3 border-t border-[#eeeef0] py-2 text-[13px]">
            <span className="min-w-0"><span className="block leading-snug">{a.name}</span><span className="block text-[12px] text-muted">you {a.claimed ?? '—'} · needs {a.required}</span></span>
            {a.claimed === null && <button type="button" className="q-btn min-h-[36px] flex-none border-[#d9d9de] px-3.5 text-[13px]" onClick={() => setRating(a)} aria-label={`Rate ${a.name}`}>Rate</button>}
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap justify-center gap-4 text-[12px] text-[#404040]">
        <span className="flex items-center gap-2"><i aria-hidden="true" className="h-3.5 w-3.5 rounded" style={{ background: COLOUR.you }} />You (your claims)</span>
        <span className="flex items-center gap-2"><i aria-hidden="true" className="w-5 border-t-2 border-dashed" style={{ borderColor: COLOUR.needed }} />Needed (TalentCorp)</span>
      </div>
      <p className="m-0 text-center text-[11px] text-muted">&ldquo;You&rdquo; is your claim (CV or your own rating), never verified. Needed levels never change with the scenario.</p>

      {unrated > 0 && profileId && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-violet-soft px-4 py-3">
          <span className="text-[13px] text-[#2b1f7a]"><b>{unrated} skill{unrated === 1 ? '' : 's'} {unrated === 1 ? "isn't" : "aren't"} rated yet.</b> Rate them to see your full gap.</span>
          <button type="button" className="q-btn min-h-[40px] border-[#d9d9de] px-4 text-[13px] font-semibold" onClick={() => setSurvey(true)}>Rate next skill</button>
        </div>
      )}

      <Link to="/roles" className="flex items-center justify-between gap-4 rounded-2xl bg-ink px-5 py-4 text-white no-underline transition-colors hover:bg-[#1f2330]">
        <span className="flex min-w-0 flex-col">
          <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-white/60">Next step</span>
          <span className="text-[16px] font-semibold">Compare the roles that fit you</span>
        </span>
        <span className="flex flex-none items-center gap-2 text-[14px] font-medium"><span className="hidden sm:inline">See your options</span> <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/15"><ArrowRight size={18} aria-hidden="true" /></span></span>
      </Link>

      {rating && <RatePopup axis={rating} onClose={() => setRating(null)} onSaved={() => { setRating(null); onChanged() }} />}
      {survey && profileId && <SurveyPopup profileId={profileId} scenario={OVERVIEW_SCENARIO} onClose={() => { setSurvey(false); onChanged() }} />}
    </section>
  )
}
