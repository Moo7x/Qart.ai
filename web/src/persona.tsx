import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

export type PersonaRole = 'employee' | 'senior' | 'hr'

export interface Persona {
  key: string
  label: string
  role: PersonaRole
  userId: string | null // only employees have individual data
}

// Synthetic demo personas (data/synthetic_team.json). HR sees aggregates only; the senior reviews
// companion updates. No individual page is shown to HR or the senior.
export const PERSONAS: Persona[] = [
  { key: 'aina', label: 'Aina (Employee)', role: 'employee', userId: 'u_aina' },
  { key: 'siti', label: 'Siti (Employee)', role: 'employee', userId: 'u_siti' },
  { key: 'lim', label: 'Mr Lim (Senior)', role: 'senior', userId: null },
  { key: 'nadia', label: 'Nadia (HR)', role: 'hr', userId: null },
]

const STORAGE_KEY = 'qart.persona'

function initialPersona(): Persona {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return PERSONAS.find(p => p.key === saved) ?? PERSONAS[0]
  } catch {
    return PERSONAS[0]
  }
}

interface PersonaState {
  persona: Persona
  setPersona: (p: Persona) => void
}

const PersonaContext = createContext<PersonaState>({ persona: PERSONAS[0], setPersona: () => {} })

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [persona, setState] = useState<Persona>(initialPersona)
  const setPersona = (p: Persona) => {
    setState(p)
    try {
      localStorage.setItem(STORAGE_KEY, p.key)
    } catch {
      /* private window: keep it for this page only */
    }
  }
  return <PersonaContext.Provider value={{ persona, setPersona }}>{children}</PersonaContext.Provider>
}

export function usePersona(): PersonaState {
  return useContext(PersonaContext)
}

/** The employee id for individual pages (falls back to Aina so a page never crashes). */
export function useUserId(): string {
  return usePersona().persona.userId ?? 'u_aina'
}
