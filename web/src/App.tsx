import { Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { LiveIntelligence } from './pages/LiveIntelligence'
import { Overview } from './pages/Overview'

export default function App() {
  return (
    <div className="flex min-h-screen flex-wrap items-start bg-fog">
      <Sidebar />
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/live" element={<LiveIntelligence />} />
        <Route
          path="*"
          element={
            <main className="flex-[999_1_640px] px-10 py-7">
              <h1 className="h1">Page not found</h1>
              <p className="text-graphite">Use the menu to open the overview or live intelligence.</p>
            </main>
          }
        />
      </Routes>
    </div>
  )
}
