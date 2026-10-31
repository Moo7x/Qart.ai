import { ChevronRight, FileUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Serif } from '../../components/atoms'
import { HeroScene } from '../../components/HeroScene'
import { TopNav } from '../../components/TopNav'
import { useT } from '../../i18n'

/** The landing page (design-prototype/ hero.py): the landscape, the headline and the start card. */
export function Landing({ onStart, onForm, saved }: { onStart: () => void; onForm: () => void; saved: boolean }) {
  const { t } = useT()
  const step = (n: number, when: string, what: string) => (
    <div className="h-tile flex-1">
      <span className="h-num" aria-hidden="true">{n}</span>
      <span className="flex min-w-0 flex-col">
        <span className="text-xs text-muted-2">{when}</span>
        <span className="text-sm font-semibold">{t(what)}</span>
      </span>
    </div>
  )
  return (
    <div className="h-wrap">
      <div className="h-hero">
        <HeroScene />
        <div className="h-top"><TopNav onStart={onStart} /></div>
        <main className="h-split">
          <div className="h-left">
            <span className="h-pill">{t('GBS finance & accounting · Malaysia')}</span>
            <h1 className="h-h1">
              Your finance <Serif>career</Serif>
              <br />
              in the AI era
            </h1>
            <p className="h-sub">See which roles fit you as AI changes the work, why, and the free steps to get there.</p>
            <div className="flex flex-wrap gap-3">
              <Link to="/trends" className="h-ghost">Explore the trends</Link>
              {saved && <Link to="/overview" className="h-ghost">Continue with my saved profile</Link>}
            </div>
          </div>
          <article className="h-card" aria-labelledby="h-card-title">
            <h2 id="h-card-title" className="m-0 text-[26px] font-semibold leading-[1.15] tracking-[-0.02em]">
              <Serif><span className="text-[28px]">Where is your career</span></Serif> headed?
            </h2>
            <p className="m-0 mb-1 text-sm leading-normal text-muted">Start from what you do today. We read your tasks and skills, then show the roles that fit you next.</p>
            <button type="button" className="h-tile" onClick={onStart}>
              <FileUp size={24} aria-hidden="true" className="flex-none text-violet" />
              <span className="flex min-w-0 flex-col">
                <span className="text-sm font-semibold">{t('Your CV')}</span>
                <span className="text-[13px] text-muted-2">{t('Drop a PDF, DOCX or text file')}</span>
              </span>
            </button>
            <div className="flex flex-wrap gap-2.5">
              {step(2, 'Then', 'Your overview')}
              {step(3, 'Next', 'Roles that fit you')}
            </div>
            <button type="button" className="h-primary" onClick={onStart}>
              Start with my CV
              <span className="q-btn-arrow" aria-hidden="true"><ChevronRight size={16} /></span>
            </button>
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
              <button type="button" onClick={onForm} className="min-h-[44px] cursor-pointer border-0 bg-transparent px-0.5 text-sm font-medium text-ink underline underline-offset-[3px]">
                Use a form instead
              </button>
              <span className="text-xs text-muted">No account needed</span>
            </div>
            <p className="m-0 text-xs text-muted">Your CV is cleaned of personal details before matching.</p>
          </article>
        </main>
      </div>
    </div>
  )
}
