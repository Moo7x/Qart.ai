import { Link } from 'react-router-dom'
import { useApi } from '../api'
import { CompareFutures } from '../components/CompareFutures'
import { JobPosts } from '../components/CompareRoles'
import { Dots, ScenarioSwitch, SdgTag, JourneyRoute, NextStep, levelText } from '../components/journey'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { FutureResponse, FutureRole } from '../types'
import { NeedProfile } from './Roles'

function RoleList({ roles, destination, estimate }: { roles: FutureRole[]; destination: string; estimate?: boolean }) {
  return (
    <ol className="m-0 flex list-none flex-col p-0">
      {roles.map((r) => {
        return (
          <li key={r.role_id} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 border-t border-line py-2.5 text-[14px]">
            <span className="min-w-0">
              <span className="font-medium">{r.title}</span>
              {r.role_id === destination && <span className="tag ml-2 bg-violet text-white">Your destination</span>}
              <JobPosts title={r.title} label="See job posts →" className="block cursor-pointer border-0 bg-transparent p-0 text-left text-[12px] font-medium text-violet hover:underline" />
            </span>
            <span className="font-mono text-lg tracking-tight">
              {Math.round(r.fit)}<span className="text-[11px] text-graphite"> fit{estimate ? ' · est.' : ''}</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export function Future() {
  const { profileId, scenario } = useJourney()
  const future = useApi<FutureResponse>(profileId ? `/api/profiles/${profileId}/future` : null)
  if (!profileId) return <NeedProfile />
  const noDestination = future.error?.includes('choose a destination')
  const data = future.data
  const view = data?.scenarios[scenario]
  const today = data?.current_role ?? (data?.situation === 'student' ? 'Student or recent graduate' : 'Moving into finance')
  const gained = view?.skills.filter((s) => s.after > (s.now ?? 0)) ?? []

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

      {data && view && (
        <>
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="eyebrow">Today → Future you</span>
              <h1 className="h1">From {today.toLowerCase()} to {data.destination.title}</h1>
              <p className="m-0 max-w-[660px] text-graphite">
                Left: what you have now and the roles it fits. Right: what finishing your {view.hours} h plan would add, and the roles it opens. The right side is an estimate, not a promise about hiring.
              </p>
            </div>
            <ScenarioSwitch />
          </header>

          <div className="grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:gap-0">
            <section aria-label="Today" className="flex min-w-0 flex-col gap-6 md:pr-8">
              <div className="flex items-baseline justify-between gap-3 border-b-2 border-void pb-2">
                <h2 className="m-0 text-[22px] font-semibold tracking-tight">Now</h2>
                <span className="cap">Your claims · today</span>
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="cap m-0">Your skills</h3>
                {data.skills_now.length === 0 && <p className="m-0 text-[13px] text-graphite">No rated skills yet. <Link to="/start?edit=1">Rate your skills</Link></p>}
                {data.skills_now.map((s) => (
                  <div key={s.skill} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-line py-2 text-[13px]">
                    <span>{s.name}</span>
                    <Dots level={s.level} tone="stone" />
                  </div>
                ))}
              </div>
              <div className="flex flex-col gap-1">
                <h3 className="cap m-0">Roles you fit best today</h3>
                <RoleList roles={view.roles_now} destination={data.destination.id} />
              </div>
            </section>

            <section aria-label="After your plan" className="flex min-w-0 flex-col gap-6 md:border-l md:border-line md:pl-8">
              <div className="flex items-baseline justify-between gap-3 border-b-2 border-violet pb-2">
                <h2 className="m-0 text-[22px] font-semibold tracking-tight text-violet">Future you</h2>
                <span className="cap text-estimate">Estimate · {scenario === 'fast' ? 'fast' : 'moderate'} AI adoption</span>
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="cap m-0">Skills your plan adds or strengthens</h3>
                {gained.length === 0 && <p className="m-0 text-[13px] text-graphite">Your plan adds no new levels for this role.</p>}
                {gained.map((s) => (
                  <div key={s.skill} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-line py-2 text-[13px]">
                    <span className="font-medium">
                      {s.name}
                      {s.now === null && <span className="tag ml-2 bg-violet-soft text-violet">New</span>}
                      {s.essential && <span className="tag ml-2 bg-weak-bg text-weak">Essential</span>}
                    </span>
                    <span className="font-mono text-[12px]">{levelText(s.now)} → <span className="font-semibold text-violet">{levelText(s.after)}</span></span>
                  </div>
                ))}
              </div>
              <div className="flex flex-col gap-1">
                <h3 className="cap m-0">Roles you could reach after the plan</h3>
                <RoleList roles={view.roles_after} destination={data.destination.id} estimate />
              </div>
            </section>
          </div>


          <CompareFutures />

          <section className="section" aria-label="SDG contribution">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[13px] font-semibold">Your path serves</span>
              {view.sdg_targets.map((t) => <SdgTag key={t} target={t} />)}
            </div>
            {view.uncovered.length > 0 && <p className="m-0 text-[13px] text-graphite">Still without a verified free course: {view.uncovered.join(', ')}.</p>}
            <p className="m-0 max-w-[720px] text-[13px] text-graphite">Qart.ai supports your decision and never makes hiring decisions. Essential skills keep their required level in every scenario.</p>
          </section>
        </>
      )}
      <NextStep to="/cv" label="Update your CV" hint="Next: add what you have done to your CV" />
    </main>
  )
}
