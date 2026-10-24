import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Cv } from './pages/Cv'
import { Future } from './pages/Future'
import { Goal } from './pages/Goal'
import { Changes } from './pages/Changes'
import { LiveIntelligence } from './pages/LiveIntelligence'
import { Onboarding } from './pages/Onboarding'
import { Pathway } from './pages/Pathway'
import { Occupations } from './pages/Occupations'
import { Roles } from './pages/Roles'
import { LanguageProvider } from './i18n'
import { JourneyProvider, useJourney } from './state'

// The charting library is only needed on Trends, so that page loads on demand.
const Trends = lazy(() => import('./pages/Trends').then((m) => ({ default: m.Trends })))
const Overview = lazy(() => import('./pages/Overview').then((m) => ({ default: m.Overview })))

function Shell() {
  const location = useLocation()
  const { profileId } = useJourney()
  if (location.pathname === '/start') return <Onboarding key={location.search} />
  if (location.pathname === '/') return <Navigate to="/start" replace />
  if (location.pathname === '/overview' && !profileId) return <Navigate to="/start" replace />
  return (
    <div className="app-shell">
      <Sidebar />
      <Routes>
        <Route path="/overview" element={<Suspense fallback={<main className="page"><span role="status" className="cap">Loading your overview…</span></main>}><Overview /></Suspense>} />
        <Route path="/goal" element={<Goal />} />
        <Route path="/roles" element={<Roles />} />
        <Route path="/pathway" element={<Pathway />} />
        <Route path="/future" element={<Future />} />
        <Route path="/changes" element={<Changes />} />
        <Route path="/cv" element={<Cv />} />
        <Route path="/trends" element={<Suspense fallback={<main className="page"><span role="status" className="cap">Loading the trends…</span></main>}><Trends /></Suspense>} />
        <Route path="/occupations" element={<Occupations />} />
        <Route path="/live" element={<LiveIntelligence />} />
        <Route
          path="*"
          element={
            <main className="flex-[999_1_640px] px-10 py-7">
              <h1 className="h1">Page not found</h1>
              <p className="text-graphite">Use the menu to open a page.</p>
            </main>
          }
        />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <LanguageProvider>
    <JourneyProvider>
      <Shell />
    </JourneyProvider>
    </LanguageProvider>
  )
}
