import type { ReactNode } from 'react'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { RotateCcw } from 'lucide-react'
import { resetDemo } from './api'
import { PERSONAS, PersonaProvider, usePersona } from './persona'
import type { PersonaRole } from './persona'
import { EmptyState, Loading, ProvenanceTag } from './ui'

// Pages load on first visit, so the first screen does not download all of them.
const CompanionUpdates = lazy(() => import('./pages/CompanionUpdates'))
const Evidence = lazy(() => import('./pages/Evidence'))
const HRSummary = lazy(() => import('./pages/HRSummary'))
const Impact = lazy(() => import('./pages/Impact'))
const Intake = lazy(() => import('./pages/Intake'))
const MyFuture = lazy(() => import('./pages/MyFuture'))
const MySkills = lazy(() => import('./pages/MySkills'))
const Pathway = lazy(() => import('./pages/Pathway'))
const Result = lazy(() => import('./pages/Result'))
const Scenarios = lazy(() => import('./pages/Scenarios'))
const Signals = lazy(() => import('./pages/Signals'))
const WorkQueue = lazy(() => import('./pages/WorkQueue'))
const Workspace = lazy(() => import('./pages/Workspace'))

const LINKS: Record<PersonaRole, { to: string; label: string }[]> = {
  // The reskilling flow in order, then the practice loop.
  employee: [
    { to: '/start', label: 'Profile' },
    { to: '/signals', label: 'Signals' },
    { to: '/matches', label: 'Matches' },
    { to: '/pathway', label: 'Pathway' },
    { to: '/impact', label: 'SDG impact' },
    { to: '/scenarios', label: 'Scenarios' },
    { to: '/queue', label: 'Work queue' },
    { to: '/skills', label: 'My skills' },
  ],
  senior: [{ to: '/improve', label: 'Companion updates' }],
  hr: [
    { to: '/hr', label: 'HR summary' },
    { to: '/evidence', label: 'Evidence & assumptions' },
  ],
}

// Employees land on their Profile, the first step of the reskilling flow.
const HOME: Record<PersonaRole, string> = { employee: '/start', senior: '/improve', hr: '/hr' }

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
      {/* Links get their own row: eight employee screens do not fit beside the controls. */}
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
  return <Navigate to={HOME[persona.role]} replace />
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
        <Nav />
        <Main>
          <Suspense fallback={<Loading what="page" />}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/start" element={<Only role="employee"><Intake /></Only>} />
              <Route path="/queue" element={<Only role="employee"><WorkQueue /></Only>} />
              <Route path="/workspace/:caseId" element={<Only role="employee"><Workspace /></Only>} />
              <Route path="/result/:caseId" element={<Only role="employee"><Result /></Only>} />
              <Route path="/skills" element={<Only role="employee"><MySkills /></Only>} />
              <Route path="/signals" element={<Only role="employee"><Signals /></Only>} />
              <Route path="/matches" element={<Only role="employee"><MyFuture /></Only>} />
              <Route path="/future" element={<Navigate to="/matches" replace />} />
              <Route path="/pathway" element={<Only role="employee"><Pathway /></Only>} />
              <Route path="/impact" element={<Only role="employee"><Impact /></Only>} />
              <Route path="/scenarios" element={<Only role="employee"><Scenarios /></Only>} />
              <Route path="/hr" element={<Only role="hr"><HRSummary /></Only>} />
              <Route path="/evidence" element={<Only role="hr"><Evidence /></Only>} />
              <Route path="/improve" element={<Only role="senior"><CompanionUpdates /></Only>} />
            </Routes>
          </Suspense>
        </Main>
      </BrowserRouter>
    </PersonaProvider>
  )
}
