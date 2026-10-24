import { Route, Routes, useLocation } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Cv } from './pages/Cv'
import { Future } from './pages/Future'
import { Goal } from './pages/Goal'
import { Changes } from './pages/Changes'
import { LiveIntelligence } from './pages/LiveIntelligence'
import { Onboarding } from './pages/Onboarding'
import { Overview } from './pages/Overview'
import { Pathway } from './pages/Pathway'
import { Occupations } from './pages/Occupations'
import { Roles } from './pages/Roles'
import { Trends } from './pages/Trends'
import { JourneyProvider } from './state'

function Shell() {
  const location = useLocation()
  if (location.pathname === '/start') return <Onboarding />
  return (
    <div className="flex min-h-screen flex-wrap items-start bg-fog">
      <Sidebar />
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/goal" element={<Goal />} />
        <Route path="/roles" element={<Roles />} />
        <Route path="/pathway" element={<Pathway />} />
        <Route path="/future" element={<Future />} />
        <Route path="/changes" element={<Changes />} />
        <Route path="/cv" element={<Cv />} />
        <Route path="/trends" element={<Trends />} />
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
    <JourneyProvider>
      <Shell />
    </JourneyProvider>
  )
}
