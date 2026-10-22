import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import HRSummary from './pages/HRSummary'
import Intake from './pages/Intake'
import MyFuture from './pages/MyFuture'
import MySkills from './pages/MySkills'
import Result from './pages/Result'
import WorkQueue from './pages/WorkQueue'
import Workspace from './pages/Workspace'

const PERSONAS = ['Aina (Employee)', 'Siti (Employee)', 'Mr Lim (Senior)', 'Nadia (HR)']

function Nav() {
  const loc = useLocation()
  const links = [
    { to: '/queue', label: 'Work queue' },
    { to: '/skills', label: 'My skills' },
    { to: '/future', label: 'My future' },
    { to: '/hr', label: 'HR summary' },
  ]
  return (
    <header className="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-4 text-sm sticky top-0 z-40 shadow-sm">
      <Link to="/" className="font-bold text-indigo-700 text-base mr-2">Qart.ai</Link>
      <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded text-xs font-medium">Synthetic demo data</span>
      <nav className="flex gap-1 ml-2">
        {links.map(l => (
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
        <select className="text-xs border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none">
          {PERSONAS.map(p => <option key={p}>{p}</option>)}
        </select>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <main className="max-w-7xl mx-auto px-4 py-6">
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
