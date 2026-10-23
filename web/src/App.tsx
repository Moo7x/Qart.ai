import type { ReactNode } from 'react'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { RotateCcw } from 'lucide-react'
import { resetDemo } from './api'
import { PERSONAS, PersonaProvider, usePersona } from './persona'
import type { PersonaRole } from './persona'
import { AnswersProvider, clearSavedAnswers } from './onboarding/answers'
import { AppPage, Gated } from './onboarding/AppShell'
import { EmptyState, Loading, ProvenanceTag } from './ui'

// Pages load on first visit, so the first screen does not download all of them.
const CompanionUpdates = lazy(() => import('./pages/CompanionUpdates'))
const Evidence = lazy(() => import('./pages/Evidence'))
const HRSummary = lazy(() => import('./pages/HRSummary'))
const Impact = lazy(() => import('./pages/Impact'))
const FindMyPath = lazy(() => import('./pages/FindMyPath'))
const Landing = lazy(() => import('./pages/Landing'))
const Matching = lazy(() => import('./pages/Matching'))
const Onboarding = lazy(() => import('./pages/Onboarding'))
const Matches = lazy(() => import('./pages/Matches'))
const MySkills = lazy(() => import('./pages/MySkills'))
const Pathway = lazy(() => import('./pages/Pathway'))
const Result = lazy(() => import('./pages/Result'))
const Scenarios = lazy(() => import('./pages/Scenarios'))
const Signals = lazy(() => import('./pages/Signals'))
const Sources = lazy(() => import('./pages/Sources'))
const WorkQueue = lazy(() => import('./pages/WorkQueue'))
const Workspace = lazy(() => import('./pages/Workspace'))

const LINKS: Record<PersonaRole, { to: string; label: string }[]> = {
  // Employees navigate with the app's tab bar (Find my path · Future skills · Get matched ·
  // Generate pathway · More), so the header has no link row for them.
  employee: [],
  senior: [{ to: '/improve', label: 'Companion updates' }],
  hr: [
    { to: '/hr', label: 'HR summary' },
    { to: '/evidence', label: 'Evidence & assumptions' },
  ],
}

// Employees land on the "Find my path" landing page.
const HOME: Record<PersonaRole, string> = { employee: '/', senior: '/improve', hr: '/hr' }

function Nav() {
  const navigate = useNavigate()
  const { persona, setPersona } = usePersona()
  const [resetting, setResetting] = useState(false)
  const navRef = useRef<HTMLElement>(null)
  const { pathname } = useLocation()
  // A case and its result belong to the work queue.
  const inCase = pathname.startsWith('/workspace') || pathname.startsWith('/result')
  // On narrow screens the link row scrolls; keep the current screen's link visible.
  useEffect(() => {
    navRef.current?.querySelector('[aria-current="page"]')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [pathname])

  const reset = async () => {
    if (!window.confirm('Reset the demo to its synthetic starting state? Practice results, the newer snapshot and assumption approvals are cleared; companion updates are kept.')) return
    setResetting(true)
    try {
      await resetDemo()
      clearSavedAnswers() // answers drafts and "profile complete" live in this browser
      navigate(HOME[persona.role])
      window.location.reload()
    } finally {
      setResetting(false)
    }
  }

  return (
    <header className="sticky top-0 z-40 bg-surface/90 backdrop-blur border-b border-hairline shadow-nav">
      <div className="max-w-6xl mx-auto h-14 px-4 flex items-center gap-3 sm:gap-6">
        <Link to={HOME[persona.role]} className="shrink-0 flex items-center gap-2 text-base font-semibold tracking-[-0.01em] text-ink">
          <img src="/favicon.svg" alt="" width={24} height={24} />
          <span>Qart.ai</span>
        </Link>
        <div className="ml-auto flex items-center gap-2 sm:gap-3 shrink-0">
          <span className="hidden lg:inline-flex"><ProvenanceTag kind="synthetic">demo data</ProvenanceTag></span>
          <label className="flex items-center gap-2 text-xs text-graphite">
            <span className="hidden md:inline">Viewing as</span>
            <select
              aria-label="Persona"
              value={persona.key}
              onChange={e => {
                const next = PERSONAS.find(p => p.key === e.target.value) ?? PERSONAS[0]
                setPersona(next)
                navigate(HOME[next.role])
              }}
              className="bg-surface border border-hairline-strong rounded-sm px-2 py-1 text-xs text-ink focus:outline-none"
            >
              {PERSONAS.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
            </select>
          </label>
          <button
            onClick={reset}
            disabled={resetting}
            title="Back to the synthetic starting state"
            aria-label="Reset demo"
            className="inline-flex items-center gap-1.5 rounded-sm border border-hairline-strong px-2 py-1 text-xs text-graphite hover:bg-linen transition-colors duration-200 disabled:opacity-50"
          >
            <RotateCcw size={12} aria-hidden="true" />
            <span className="hidden md:inline">{resetting ? 'Resetting…' : 'Reset demo'}</span>
          </button>
        </div>
      </div>
      {/* HR and senior links get their own row; employees use the tab bar on each page. */}
      {LINKS[persona.role].length > 0 && (
        <nav ref={navRef} aria-label="Main" className="max-w-6xl mx-auto px-4 flex gap-1 overflow-x-auto pb-2 -mt-1">
          {LINKS[persona.role].map(l => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors duration-200 ${isActive || (l.to === '/queue' && inCase) ? 'bg-action-tint text-action-ink font-medium' : 'text-ink/60 hover:text-ink'}`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}

/** Individual pages are for employees only: HR sees aggregates, the senior reviews the companion. */
function Only({ role, children }: { role: PersonaRole; children: ReactNode }) {
  const { persona } = usePersona()
  if (persona.role === role) return <>{children}</>
  const message = role === 'employee'
    ? 'This page shows one employee’s own results. HR and seniors do not see individual results.'
    : 'This page is not available for the selected persona.'
  return (
    <div className="max-w-xl mx-auto">
      <EmptyState title="Not available for this persona">{message}</EmptyState>
    </div>
  )
}

function Home() {
  const { persona } = usePersona()
  return persona.role === 'employee' ? <Landing /> : <Navigate to={HOME[persona.role]} replace />
}

/** Old URLs keep working: they forward to the new route with their query (e.g. ?role=). */
function Forward({ to }: { to: string }) {
  const { search } = useLocation()
  return <Navigate to={`${to}${search}`} replace />
}

/** An employee page inside the app shell (tab bar on top). */
function Employee({ children }: { children: ReactNode }) {
  return <Only role="employee"><AppPage>{children}</AppPage></Only>
}

/** Data sources are open to every persona; employees see it inside their app shell. */
function SourcesPage() {
  const { persona } = usePersona()
  return persona.role === 'employee' ? <AppPage><Sources /></AppPage> : <Sources />
}

// The workspace needs the full width so two tables fit without truncating descriptions.
function Main({ children }: { children: ReactNode }) {
  const wide = useLocation().pathname.startsWith('/workspace')
  return <main className={`${wide ? 'max-w-[1440px]' : 'max-w-6xl'} mx-auto px-4 py-8 sm:py-10`}>{children}</main>
}

export default function App() {
  return (
    <PersonaProvider>
      <BrowserRouter>
        <AnswersProvider>
        <Nav />
        <Main>
          <Suspense fallback={<Loading what="page" />}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/onboarding/:step" element={<Only role="employee"><Onboarding /></Only>} />
              <Route path="/matching" element={<Only role="employee"><Matching /></Only>} />
              <Route path="/app" element={<Navigate to="/app/path" replace />} />
              <Route path="/app/path" element={<Employee><FindMyPath /></Employee>} />
              <Route path="/app/skills" element={<Employee><Signals /></Employee>} />
              <Route path="/app/match" element={<Employee><Gated tab="Get matched"><Matches /></Gated></Employee>} />
              <Route path="/app/pathway" element={<Employee><Gated tab="Generate pathway"><Pathway /></Gated></Employee>} />
              <Route path="/impact" element={<Employee><Impact /></Employee>} />
              <Route path="/scenarios" element={<Employee><Scenarios /></Employee>} />
              <Route path="/queue" element={<Employee><WorkQueue /></Employee>} />
              <Route path="/workspace/:caseId" element={<Employee><Workspace /></Employee>} />
              <Route path="/result/:caseId" element={<Employee><Result /></Employee>} />
              <Route path="/skills" element={<Employee><MySkills /></Employee>} />
              <Route path="/sources" element={<SourcesPage />} />
              <Route path="/start" element={<Forward to="/onboarding/1" />} />
              <Route path="/signals" element={<Forward to="/app/skills" />} />
              <Route path="/matches" element={<Forward to="/app/match" />} />
              <Route path="/future" element={<Forward to="/app/match" />} />
              <Route path="/pathway" element={<Forward to="/app/pathway" />} />
              <Route path="/hr" element={<Only role="hr"><HRSummary /></Only>} />
              <Route path="/evidence" element={<Only role="hr"><Evidence /></Only>} />
              <Route path="/improve" element={<Only role="senior"><CompanionUpdates /></Only>} />
            </Routes>
          </Suspense>
        </Main>
        </AnswersProvider>
      </BrowserRouter>
    </PersonaProvider>
  )
}
