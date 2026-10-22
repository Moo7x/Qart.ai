import { useEffect, useState } from 'react'

// Placeholder shell until the UI mockup is approved: it only proves the build, the API
// connection and the spike pages. The real layout (docs/PLAN.md §12) replaces it.

type Health = { status: string; database: string; llm: string; embeddings: string }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error(`API answered ${response.status}`)
        return response.json() as Promise<Health>
      })
      .then(setHealth)
      .catch((reason: unknown) => setError(String(reason)))
  }, [])

  return (
    <main className="mx-auto max-w-xl p-8 font-sans text-slate-900">
      <h1 className="text-2xl font-semibold">Qart.ai</h1>
      <p className="mt-2 text-slate-600">From who you are today to where you can be in the AI era.</p>
      <section className="mt-6 rounded border border-slate-200 p-4 text-sm">
        <h2 className="font-medium">Service status</h2>
        {error && <p className="mt-2 text-red-700">API unavailable: {error}</p>}
        {!error && !health && <p className="mt-2 text-slate-500">Checking…</p>}
        {health && (
          <dl className="mt-2 grid grid-cols-2 gap-1">
            <dt>Database</dt><dd>{health.database}</dd>
            <dt>Language model</dt><dd>{health.llm}</dd>
            <dt>Embeddings</dt><dd>{health.embeddings}</dd>
          </dl>
        )}
      </section>
      <p className="mt-6 text-sm">
        Browser checks: <a className="underline" href="/spikes/tabs.html">tabs</a> ·{' '}
        <a className="underline" href="/spikes/speech.html">speech</a>
      </p>
    </main>
  )
}
