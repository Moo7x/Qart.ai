import { createContext, type ReactNode, useCallback, useContext, useState } from 'react'
import type { Scenario } from './types'

// The profile id is the person's key to their profile (the server never lists profiles), so it
// lives only in this browser. Storage can be unavailable (private mode): fall back to memory.
const PROFILE_KEY = 'qart.profile'
const SCENARIO_KEY = 'qart.scenario'

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key)
    else window.localStorage.setItem(key, value)
  } catch {
    // Not stored: the session still works until the page is closed.
  }
}

type JourneyState = {
  profileId: string | null
  setProfileId: (id: string | null) => void
  scenario: Scenario
  setScenario: (s: Scenario) => void
}

const Journey = createContext<JourneyState | null>(null)

export function JourneyProvider({ children }: { children: ReactNode }) {
  const [profileId, setId] = useState<string | null>(() => read(PROFILE_KEY))
  const [scenario, setSc] = useState<Scenario>(() => (read(SCENARIO_KEY) === 'fast' ? 'fast' : 'moderate'))
  const setProfileId = useCallback((id: string | null) => {
    write(PROFILE_KEY, id)
    setId(id)
  }, [])
  const setScenario = useCallback((s: Scenario) => {
    write(SCENARIO_KEY, s)
    setSc(s)
  }, [])
  return <Journey.Provider value={{ profileId, setProfileId, scenario, setScenario }}>{children}</Journey.Provider>
}

export function useJourney(): JourneyState {
  const value = useContext(Journey)
  if (!value) throw new Error('useJourney must be used inside JourneyProvider')
  return value
}
