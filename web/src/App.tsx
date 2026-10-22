import type { ReactNode } from 'react'
import { useState } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { resetDemo } from './api'
import CompanionUpdates from './pages/CompanionUpdates'
import Evidence from './pages/Evidence'
import HRSummary from './pages/HRSummary'
import Intake from './pages/Intake'
import MyFuture from './pages/MyFuture'
import MySkills from './pages/MySkills'
import Result from './pages/Result'
import WorkQueue from './pages/WorkQueue'
import Workspace from './pages/Workspace'
import { PERSONAS, PersonaProvider, usePersona } from './persona'
import type { PersonaRole } from './persona'

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
  const loc = useLocation()
  const navigate = useNavigate()
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
    <header className="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-4 text-sm sticky top-0 z-40 shadow-sm flex-wrap">
      <Link to={HOME[persona.role]} className="font-bold text-indigo-700 text-base mr-2">Qart.ai</Link>
      <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded text-xs font-medium">Synthetic demo data</span>
      <nav className="flex gap-1 ml-2 flex-wrap">
        {LINKS[persona.role].map(l => (
          <Link
            key={l.to}
            to={l.to}
            className={`px-3 py-1.5 rounded text-sm transition-colors ${loc.pathname.startsWith(l.to) ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            {l.label}
          </Link>
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs text-gray-500">Persona:</span>
        <select
          aria-label="Persona"
          value={persona.key}
          onChange={e => {
            const next = PERSONAS.find(p => p.key === e.target.value) ?? PERSONAS[0]
            setPersona(next)
            navigate(HOME[next.role])
          }}
          className="text-xs border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none"
        >
          {PERSONAS.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
        </select>
        <button
          onClick={reset}
          disabled={resetting}
          className="text-xs text-gray-500 border border-gray-200 rounded px-2 py-1 hover:bg-gray-50"
          title="Back to the synthetic starting state"
        >
          {resetting ? 'Resetting…' : 'Reset demo'}
        </button>
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
    <div className="max-w-xl mx-auto bg-white border border-gray-200 rounded-xl p-6 text-center text-sm text-gray-600">
      {message}
    </div>
  )
}

function Home() {
  const { persona } = usePersona()
  return <Navigate to={persona.role === 'employee' ? '/start' : HOME[persona.role]} replace />
}

export default function App() {
  return (
    <PersonaProvider>
      <BrowserRouter>
        <Nav />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/start" element={<Only role="employee"><Intake /></Only>} />
            <Route path="/queue" element={<Only role="employee"><WorkQueue /></Only>} />
            <Route path="/workspace/:caseId" element={<Only role="employee"><Workspace /></Only>} />
            <Route path="/result/:caseId" element={<Only role="employee"><Result /></Only>} />
            <Route path="/skills" element={<Only role="employee"><MySkills /></Only>} />
            <Route path="/future" element={<Only role="employee"><MyFuture /></Only>} />
            <Route path="/hr" element={<Only role="hr"><HRSummary /></Only>} />
            <Route path="/evidence" element={<Only role="hr"><Evidence /></Only>} />
            <Route path="/improve" element={<Only role="senior"><CompanionUpdates /></Only>} />
          </Routes>
        </main>
      </BrowserRouter>
    </PersonaProvider>
  )
}
