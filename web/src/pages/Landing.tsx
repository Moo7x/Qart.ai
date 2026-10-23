import { Link } from 'react-router-dom'
import { useAnswers } from '../onboarding/answers'

/** Landing: one clear start (QART_ONBOARDING_FLOW_SPEC §1). */
export default function Landing() {
  const { profileComplete } = useAnswers()
  return (
    <section className="min-h-[70vh] flex flex-col items-center justify-center text-center gap-6 px-2">
      <h1 className="max-w-3xl text-[clamp(40px,7vw,68px)] leading-[1.05] tracking-[-0.035em] font-extrabold text-ink">
        Where does your career go next?
      </h1>
      <p className="max-w-xl font-serif text-[22px] leading-[1.45] text-graphite">
        Answer three short sets of questions. We match you to future-proof roles and build your reskilling pathway.
      </p>
      <Link to="/onboarding/1" className="mt-2 inline-flex min-h-16 items-center rounded-full bg-action px-11 text-xl font-bold text-white hover:bg-action-hover transition-colors duration-200">
        Find my path
      </Link>
      <span className="text-sm text-graphite">About 3 minutes · no CV needed</span>
      {profileComplete
        ? <Link to="/app/match" className="inline-flex min-h-11 items-center px-3 text-[15px] font-semibold text-action-ink hover:underline">Go to my matches →</Link>
        : <Link to="/app/skills" className="inline-flex min-h-11 items-center px-3 text-[15px] font-semibold text-action-ink hover:underline">Look around first →</Link>}
    </section>
  )
}
