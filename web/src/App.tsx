import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import HRSummary from './pages/HRSummary'
import Intake from './pages/Intake'
import MyFuture from './pages/MyFuture'
import MySkills from './pages/MySkills'
import Result from './pages/Result'
import WorkQueue from './pages/WorkQueue'
import Workspace from './pages/Workspace'
import { ProvenanceTag } from './ui'

const PERSONAS = ['Aina (Employee)', 'Siti (Employee)', 'Mr Lim (Senior)', 'Nadia (HR)']

const LINKS = [
  { to: '/queue', label: 'Work queue' },
  { to: '/skills', label: 'My skills' },
  { to: '/future', label: 'My future' },
  { to: '/hr', label: 'HR summary' },
]

function Nav() {
  return (
    <header className="sticky top-0 z-40 bg-surface/90 backdrop-blur border-b border-hairline shadow-nav">
      <div className="max-w-6xl mx-auto h-16 px-4 flex items-center gap-3 sm:gap-6">
        <Link to="/" className="shrink-0 flex items-center gap-2 text-base font-semibold tracking-[-0.01em] text-ink">
          <img src="/favicon.svg" alt="" width={24} height={24} />
          Qart.ai
        </Link>
        <nav aria-label="Main" className="min-w-0 flex gap-1 overflow-x-auto">
          {LINKS.map(l => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors duration-200 ${isActive ? 'bg-action-tint text-action-ink font-medium' : 'text-ink/60 hover:text-ink'}`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto hidden md:flex items-center gap-3">
          <ProvenanceTag kind="synthetic">demo data</ProvenanceTag>
          <label className="flex items-center gap-2 text-xs text-graphite">
            Viewing as
            <select className="bg-surface border border-hairline-strong rounded-sm px-2 py-1 text-xs text-ink focus:outline-none">
              {PERSONAS.map(p => <option key={p}>{p}</option>)}
            </select>
          </label>
        </div>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <main className="max-w-6xl mx-auto px-4 py-10">
        <Routes>
          <Route path="/" element={<Intake />} />
          <Route path="/queue" element={<WorkQueue />} />
          <Route path="/workspace/:caseId" element={<Workspace />} />
          <Route path="/result/:caseId" element={<Result />} />
          <Route path="/skills" element={<MySkills />} />
          <Route path="/future" element={<MyFuture />} />
          <Route path="/hr" element={<HRSummary />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
