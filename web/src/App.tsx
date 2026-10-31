import { Component, type ComponentType, lazy, type ReactNode, Suspense, useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { TopNav } from './components/TopNav'
import { Future } from './pages/Future'
import { Goal } from './pages/Goal'
import { Changes } from './pages/Changes'
import { LiveIntelligence } from './pages/LiveIntelligence'
import { Onboarding } from './pages/Onboarding'
import { Pathway } from './pages/Pathway'
import { Privacy } from './pages/Privacy'
import { Status } from './pages/Status'
import { Occupations } from './pages/Occupations'
import { Roles } from './pages/Roles'
import { Time } from './pages/Time'
import { Work } from './pages/Work'
import { LanguageProvider } from './i18n'
import { JourneyProvider, useJourney } from './state'

// After a redeploy the browser may still ask for the old build's page files, which no longer
// exist. The first failure reloads the page once to fetch the new build; a second failure shows
// a clear error instead of a blank page (docs/PHASE2_PLAN.md A4).
const RELOADED_KEY = 'qart.reloaded-after-deploy'

function remember(value: string | null): string | null {
  try {
    if (value === null) window.sessionStorage.removeItem(RELOADED_KEY)
    else window.sessionStorage.setItem(RELOADED_KEY, value)
    return value
  } catch {
    return null
  }
}

function alreadyReloaded(): boolean {
  try {
    return window.sessionStorage.getItem(RELOADED_KEY) !== null
  } catch {
    return true // no storage: never risk a reload loop
  }
}

function lazyPage<T extends ComponentType>(load: () => Promise<T>) {
  return lazy(() =>
    load()
      .then((page) => {
        remember(null)
        return { default: page }
      })
      .catch((error: unknown) => {
        if (alreadyReloaded()) throw error
        remember('1')
        window.location.reload()
        return new Promise<never>(() => {}) // the reload replaces the page
      }),
  )
}

class PageError extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="page" role="alert">
        <h1 className="h1">This page could not load</h1>
        <p className="text-graphite">The app may have just been updated. Reload to get the latest version.</p>
        <button type="button" className="btn btn-v self-start" onClick={() => { remember(null); window.location.reload() }}>Reload</button>
      </main>
    )
  }
}

// The charting library is only needed on Trends, so that page loads on demand.
const Trends = lazyPage(() => import('./pages/Trends').then((m) => m.Trends))
const Overview = lazyPage(() => import('./pages/Overview').then((m) => m.Overview))

// Pages load their sections from the API, so a "#section" link waits for the section to appear.
const HASH_WAIT_MS = 3000
const HASH_POLL_MS = 150

function useScrollToHash(pathname: string, hash: string) {
  useEffect(() => {
    if (!hash) return
    const started = Date.now()
    const id = window.setInterval(() => {
      const target = document.getElementById(hash.slice(1))
      if (target || Date.now() - started > HASH_WAIT_MS) {
        window.clearInterval(id)
        target?.scrollIntoView({ block: 'start' })
      }
    }, HASH_POLL_MS)
    return () => window.clearInterval(id)
  }, [pathname, hash])
}

function Shell() {
  const location = useLocation()
  const { profileId } = useJourney()
  useScrollToHash(location.pathname, location.hash)
  if (location.pathname === '/start') return <Onboarding key={location.search} />
  if (location.pathname === '/') return <Navigate to="/start" replace />
  if (location.pathname === '/overview' && !profileId) return <Navigate to="/start" replace />
  return (
    <div className="app-shell">
      <TopNav />
      <Routes>
        <Route path="/overview" element={<PageError><Suspense fallback={<main className="page"><span role="status" className="cap">Loading your overview…</span></main>}><Overview /></Suspense></PageError>} />
        <Route path="/goal" element={<Goal />} />
        <Route path="/work" element={<Work />} />
        <Route path="/time" element={<Time />} />
        <Route path="/roles" element={<Roles />} />
        <Route path="/pathway" element={<Pathway />} />
        <Route path="/future" element={<Future />} />
        <Route path="/changes" element={<Changes />} />
        <Route path="/trends" element={<PageError><Suspense fallback={<main className="page"><span role="status" className="cap">Loading the trends…</span></main>}><Trends /></Suspense></PageError>} />
        <Route path="/occupations" element={<Occupations />} />
        <Route path="/live" element={<LiveIntelligence />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/status" element={<Status />} />
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
