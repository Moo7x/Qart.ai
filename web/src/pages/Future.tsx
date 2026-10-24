import { Link } from 'react-router-dom'
import { useApi } from '../api'
import { Dots, ScenarioSwitch, SdgTag, JourneyRoute, NextStep } from '../components/journey'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { FutureResponse } from '../types'
import { NeedProfile } from './Roles'

export function Future() {
  const { profileId, scenario } = useJourney()
  const future = useApi<FutureResponse>(profileId ? `/api/profiles/${profileId}/future` : null)
  if (!profileId) return <NeedProfile />
  const noDestination = future.error?.includes('choose a destination')
  const data = future.data
  const view = data?.scenarios[scenario]
  const other = data?.scenarios[scenario === 'moderate' ? 'fast' : 'moderate']
  const today = data?.current_role ?? (data?.situation === 'student' ? 'Student or recent graduate' : 'Moving into finance')

  return (
    <main className="page">
      <JourneyRoute />
      {noDestination && (
        <div className="flex flex-col gap-3">
          <span className="eyebrow">Today → Future you</span>
          <h1 className="h1">Choose a destination role first</h1>
          <Link className="btn btn-v self-start" to="/roles">See roles that fit me</Link>
        </div>
      )}
      {future.loading && <Loading what="your comparison" />}
      {future.error && !noDestination && <Problem what="your comparison" message={future.error} onRetry={future.reload} />}

      {data && view && other && (
        <>
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="eyebrow">Today → Future you</span>
              <h1 className="h1">From {today.toLowerCase()} to {data.destination.title}</h1>
              <p className="m-0 max-w-[640px] text-graphite">Fit after the path assumes you finish it and reach the level the courses cover. It is an estimate, not a promise about hiring.</p>
            </div>
            <ScenarioSwitch />
          </header>

          <div className="flex flex-wrap items-stretch gap-5">
            <section className="card-light flex min-w-0 flex-[1_1_360px] flex-col gap-5 p-6">
              <div>
                <span className="cap">Today</span>
                <h2 className="m-0 mt-1.5 text-2xl font-semibold tracking-tight">{today}</h2>
                <span className="text-[13px] text-graphite">
                  {data.years_experience !== null ? `${data.years_experience} years · ` : ''}levels are your claims
                </span>
              </div>
              <div>
                <span className="cap">Fit for the destination</span>
                <div className="font-mono text-[44px] leading-tight tracking-[-0.04em]">{Math.round(view.fit_now)}</div>
              </div>
              <div className="flex flex-col">
                {view.skills.map((s) => (
                  <div key={s.skill} className="grid grid-cols-[minmax(0,1fr)_88px] items-center gap-3 border-t border-mist py-2 text-[13px]">
                    <span>{s.name}{s.essential ? ' ★' : ''}</span>
                    <Dots level={s.now} tone="stone" />
                  </div>
                ))}
              </div>
            </section>

            <section className="card-dark flex min-w-0 flex-[1_1_360px] flex-col gap-5 bg-[radial-gradient(80%_70%_at_100%_0%,rgba(108,71,255,0.26),rgba(33,33,38,0)_70%)] p-6">
              <div>
                <span className="font-mono text-[11px] tracking-widest text-cyan">AFTER YOUR PATHWAY</span>
                <h2 className="m-0 mt-1.5 text-2xl font-semibold tracking-tight">{data.destination.title}</h2>
                <span className="text-[13px] text-stone">{view.hours} h · RM 0 · about {view.weeks} weeks</span>
              </div>
              <div className="flex flex-wrap gap-8">
                <div>
                  <span className="font-mono text-[11px] tracking-wider text-stone">FIT AFTER THE PATH · ESTIMATE</span>
                  <div className="font-mono text-[44px] leading-tight tracking-[-0.04em]">{Math.round(view.fit_after)}</div>
                </div>
                <div>
                  <span className="font-mono text-[11px] tracking-wider text-stone">UNDER {scenario === 'moderate' ? 'FAST' : 'MODERATE'} ADOPTION</span>
                  <div className="font-mono text-[44px] leading-tight tracking-[-0.04em] text-slate-mid">{Math.round(other.fit_after)}</div>
                </div>
              </div>
              <div className="flex flex-col">
                {view.skills.map((s) => (
                  <div key={s.skill} className="grid grid-cols-[minmax(0,1fr)_88px] items-center gap-3 border-t border-surface py-2 text-[13px]">
                    <span className={s.after > (s.now ?? 0) ? 'font-medium text-white' : 'text-stone'}>{s.name}{s.essential ? ' ★' : ''}</span>
                    <Dots level={s.after} tone="light" />
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="card-light flex flex-wrap items-center justify-between gap-4 px-[22px] py-[18px]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[13px] font-semibold">Your path serves</span>
              {view.sdg_targets.map((t) => <SdgTag key={t} target={t} />)}
            </div>
            <Link className="btn btn-v" to="/pathway">Back to my pathway</Link>
          </section>
          {view.uncovered.length > 0 && (
            <p className="m-0 text-[13px] text-graphite">Still without a verified free course: {view.uncovered.join(', ')}.</p>
          )}
          <p className="m-0 max-w-[720px] text-[13px] text-graphite">
            Qart.ai supports your decision and never makes hiring decisions. ★ marks essential skills: their level never drops in any scenario.
          </p>
        </>
      )}
      <NextStep to="/cv" label="Update your CV" hint="Next: add what you have done to your CV" />
    </main>
  )
}
