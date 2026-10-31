import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { Card, DarkButton, Serif } from '../components/atoms'
import { FlowSteps } from '../components/FlowSteps'
import { Loading, Problem } from '../components/ui'
import { useT } from '../i18n'
import { useJourney } from '../state'
import type { PackInfo, ProfileData } from '../types'

// The options the profile already defines (ProfileData.weekly_hours, ProfileData.budget).
const HOURS = [2, 4, 6, 10]
const BUDGETS: { id: ProfileData['budget']; text: string }[] = [
  { id: 'free', text: 'Free only' },
  { id: 'free_hrd', text: 'Free + HRD Corp-claimable' },
  { id: 'up_to_500', text: 'Up to RM 500' },
]

/** Time and budget, asked once a role is chosen and just before the plan is built. */
export function Time() {
  const { t } = useT()
  const navigate = useNavigate()
  const { profileId } = useJourney()
  const saved = useApi<{ profile: ProfileData; destination: string | null }>(profileId ? `/api/profiles/${profileId}` : null)
  const pack = useApi<PackInfo>('/api/pack')
  const [hours, setHours] = useState(6)
  const [budget, setBudget] = useState<ProfileData['budget']>('free')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!saved.data) return
    setHours(saved.data.profile.weekly_hours)
    setBudget(saved.data.profile.budget)
  }, [saved.data])
  if (!profileId) return <Navigate to="/start" replace />
  const destination = saved.data?.destination
  const title = pack.data?.destination_roles.find((r) => r.id === destination)?.title

  async function build() {
    if (!saved.data) return
    setBusy(true)
    setError(null)
    try {
      await sendJSON(`/api/profiles/${profileId}`, { method: 'PUT', body: { ...saved.data.profile, weekly_hours: hours, budget } })
      navigate('/pathway')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="page gap-5">
      <FlowSteps current="time" skip={saved.data?.profile.current_role === 'other' ? ['work'] : []} />
      <div className="q-tray flex flex-wrap items-start gap-4 p-5">
        <Card label="Time and budget" className="flex-[1.6_1_560px] gap-4">
          {saved.loading && <Loading what="your profile" />}
          {saved.error && <Problem what="your profile" message={saved.error} onRetry={saved.reload} />}
          {saved.data && !destination && <Navigate to="/roles" replace />}
          <span className="text-[13px] text-muted">For {title ?? 'your chosen role'} · <Link to="/roles">change role</Link></span>
          <h1 className="m-0 text-[clamp(30px,5vw,44px)] font-medium leading-[1.08] tracking-[-0.02em]">How much time and money can you put into <Serif>learning</Serif>?</h1>
          <span className="text-[13px] font-semibold">{t('Hours per week')}</span>
          <div role="radiogroup" aria-label="Hours per week" className="flex flex-wrap gap-2">
            {HOURS.map((h) => <button key={h} type="button" role="radio" aria-checked={hours === h} className="q-chip" onClick={() => setHours(h)}>{h} h</button>)}
          </div>
          <span className="text-[13px] font-semibold">{t('Budget')}</span>
          <div role="radiogroup" aria-label="Budget" className="flex flex-wrap gap-2">
            {BUDGETS.map((b) => <button key={b.id} type="button" role="radio" aria-checked={budget === b.id} className="q-chip" onClick={() => setBudget(b.id)}>{t(b.text)}</button>)}
          </div>
          <p className="m-0 text-[13px] text-muted">{t('Every course listed today is free. HRD Corp-claimable programmes are shown only once the official listing confirms them.')}</p>
          {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}
          <div className="flex flex-wrap items-center gap-2.5 border-t border-[#e5e5e5] pt-4">
            <Link to="/roles" className="q-btn q-btn-text">← Roles</Link>
            <span className="flex-1" />
            <DarkButton onClick={build} disabled={busy || !saved.data}>Build my plan</DarkButton>
          </div>
        </Card>
        <Card label="About this screen" className="flex-[1_1_280px] gap-3.5 self-start">
          <span className="q-kicker">Why this matters</span>
          <h3 className="q-h3 text-[22px]">{t('Make the plan fit your week')}</h3>
          <p className="m-0 text-[15px] text-[#404040]">Course hours are estimates from the checked catalogue. More weekly time changes the schedule, not your current ability.</p>
        </Card>
      </div>
    </main>
  )
}
