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

type SendOptions = { body?: unknown; headers?: Record<string, string>; method?: 'POST' | 'PUT' }

export async function sendJSON<T>(path: string, { body, headers = {}, method = 'POST' }: SendOptions = {}): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) throw new ApiError(response.status, await readError(response))
  return (await response.json()) as T
}

export async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(path, { method: 'POST', body: form })
  if (!response.ok) throw new ApiError(response.status, await readError(response))
  return (await response.json()) as T
}

export type Loadable<T> = {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/** Fetch `path` on mount (and every `pollMs` if given). A null path fetches nothing. */
export function useApi<T>(path: string | null, pollMs?: number): Loadable<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    if (path === null) return
    let cancelled = false
    setLoading(true)
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
    if (!pollMs || path === null) return
    const id = window.setInterval(reload, pollMs)
    return () => window.clearInterval(id)
  }, [pollMs, path, reload])

  return { data, error, loading, reload }
}

/** Server timestamps are UTC: Postgres sends a zone, SQLite does not. */
export function parseUtc(iso: string): number {
  return Date.parse(/[zZ]$|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`)
}

/** Show a server timestamp in Malaysia time. */
export function formatWhen(iso: string | null): string {
  if (!iso) return '—'
  return new Date(parseUtc(iso)).toLocaleString('en-MY', {
    timeZone: 'Asia/Kuala_Lumpur',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
