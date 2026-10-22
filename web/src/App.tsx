import type { ReactNode } from 'react'
import { useState } from 'react'
import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { RotateCcw } from 'lucide-react'
import { resetDemo } from './api'
import CompanionUpdates from './pages/CompanionUpdates'
import Evidence from './pages/Evidence'
import HRSummary from './pages/HRSummary'
import Impact from './pages/Impact'
import Intake from './pages/Intake'
import MyFuture from './pages/MyFuture'
import MySkills from './pages/MySkills'
import Pathway from './pages/Pathway'
import Result from './pages/Result'
import Scenarios from './pages/Scenarios'
import Signals from './pages/Signals'
import WorkQueue from './pages/WorkQueue'
import Workspace from './pages/Workspace'
import { FUTURE_FLOW_PATHS } from './components/FlowSteps'
import { PERSONAS, PersonaProvider, usePersona } from './persona'
import type { PersonaRole } from './persona'
import { EmptyState, ProvenanceTag } from './ui'

const LINKS: Record<PersonaRole, { to: string; label: string }[]> = {
  employee: [
    { to: '/start', label: 'Start' },
    { to: '/queue', label: 'Work queue' },
    { to: '/skills', label: 'My skills' },
    { to: '/future', label: 'My future' },
  ],
  senior: [{ to: '/improve', label: 'Companion updates' }],
  hr: [
    { to: '/hr', label: 'HR summary' },
    { to: '/evidence', label: 'Evidence & assumptions' },
  ],
}

const HOME: Record<PersonaRole, string> = { employee: '/queue', senior: '/improve', hr: '/hr' }

function Nav() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  // "My future" covers every flow screen after the intake (Signals … Scenarios).
  const inFutureFlow = FUTURE_FLOW_PATHS.some(p => pathname.startsWith(p))
  const { persona, setPersona } = usePersona()
  const [resetting, setResetting] = useState(false)

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
      <div className="max-w-6xl mx-auto h-16 px-4 flex items-center gap-3 sm:gap-6">
        <Link to={HOME[persona.role]} className="shrink-0 flex items-center gap-2 text-base font-semibold tracking-[-0.01em] text-ink">
          <img src="/favicon.svg" alt="" width={24} height={24} />
          <span className="hidden sm:inline">Qart.ai</span>
        </Link>
        <nav aria-label="Main" className="min-w-0 flex gap-1 overflow-x-auto">
          {LINKS[persona.role].map(l => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors duration-200 ${isActive || (l.to === '/future' && inFutureFlow) ? 'bg-action-tint text-action-ink font-medium' : 'text-ink/60 hover:text-ink'}`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
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
  return <Navigate to={persona.role === 'employee' ? '/start' : HOME[persona.role]} replace />
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
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/start" element={<Only role="employee"><Intake /></Only>} />
            <Route path="/queue" element={<Only role="employee"><WorkQueue /></Only>} />
            <Route path="/workspace/:caseId" element={<Only role="employee"><Workspace /></Only>} />
            <Route path="/result/:caseId" element={<Only role="employee"><Result /></Only>} />
            <Route path="/skills" element={<Only role="employee"><MySkills /></Only>} />
            <Route path="/signals" element={<Only role="employee"><Signals /></Only>} />
            <Route path="/future" element={<Only role="employee"><MyFuture /></Only>} />
            <Route path="/pathway" element={<Only role="employee"><Pathway /></Only>} />
            <Route path="/impact" element={<Only role="employee"><Impact /></Only>} />
            <Route path="/scenarios" element={<Only role="employee"><Scenarios /></Only>} />
            <Route path="/hr" element={<Only role="hr"><HRSummary /></Only>} />
            <Route path="/evidence" element={<Only role="hr"><Evidence /></Only>} />
            <Route path="/improve" element={<Only role="senior"><CompanionUpdates /></Only>} />
          </Routes>
        </Main>
      </BrowserRouter>
    </PersonaProvider>
  )
}
