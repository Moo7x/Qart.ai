import { useCallback, useEffect, useState } from 'react'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    return body.detail ?? `The server answered ${response.status}`
  } catch {
    return `The server answered ${response.status}`
  }
}

export async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw new ApiError(response.status, await readError(response))
  return (await response.json()) as T
}

export async function postJSON<T>(path: string, headers: Record<string, string> = {}): Promise<T> {
  const response = await fetch(path, { method: 'POST', headers })
  if (!response.ok) throw new ApiError(response.status, await readError(response))
  return (await response.json()) as T
}

export type Loadable<T> = {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/** Fetch `path` on mount (and every `pollMs` if given). */
export function useApi<T>(path: string, pollMs?: number): Loadable<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let cancelled = false
    getJSON<T>(path)
      .then((value) => {
        if (!cancelled) {
          setData(value)
          setError(null)
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : String(reason))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [path, tick])

  useEffect(() => {
    if (!pollMs) return
    const id = window.setInterval(reload, pollMs)
    return () => window.clearInterval(id)
  }, [pollMs, reload])

  return { data, error, loading, reload }
}

/** Server timestamps from SQLite have no zone; they are UTC. Show them in Malaysia time. */
export function formatWhen(iso: string | null): string {
  if (!iso) return '—'
  const withZone = /[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`
  return new Date(withZone).toLocaleString('en-MY', {
    timeZone: 'Asia/Kuala_Lumpur',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
