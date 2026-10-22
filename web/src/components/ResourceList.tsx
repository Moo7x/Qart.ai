import { useEffect, useState } from 'react'
import { Cpu, ExternalLink, TextSearch } from 'lucide-react'
import { getResources } from '../api'
import type { SearchResponse } from '../types'
import { ProvenanceTag, Tag } from '../ui'

const GPU_RETRIES = 4 // a cold start took ~100 s; 4 × 25 s covers it
const GPU_RETRY_MS = 25000

const KIND_LABELS: Record<string, string> = {
  course: 'course',
  course_candidate: 'course (unreviewed)',
  onet_task: 'O*NET task',
  onet_dwa: 'O*NET work activity',
}

/** Results of one search, with the engine that produced them (GPU or keyword) and their sources. */
export function ResourceList({ response }: { response: SearchResponse }) {
  const gpu = response.engine === 'hybrid'
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 min-w-0">
        <Tag tone={gpu ? 'action' : 'linen'} icon={gpu ? Cpu : TextSearch} title={response.note}>
          {gpu ? 'GPU search (RunPod)' : 'Keyword search'}
        </Tag>
        <span className="text-xs text-graphite truncate">{response.note}</span>
      </div>
      {response.results.length === 0 && <p className="text-sm text-graphite">Nothing found.</p>}
      <ul className="space-y-1.5">
        {response.results.map(r => (
          <li key={r.document_id} className="bg-surface border border-hairline rounded-md px-3 py-2.5 hover:border-hairline-strong transition-colors duration-200">
            <a href={r.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-medium text-action-ink hover:underline">
              {r.title} <ExternalLink size={12} aria-hidden="true" />
            </a>
            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-graphite">
              <Tag tone={r.kind === 'course_candidate' ? 'marigold' : 'linen'}>{KIND_LABELS[r.kind] ?? r.kind}</Tag>
              <ProvenanceTag kind="evidence">{r.source} · retrieved {r.date}</ProvenanceTag>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Verified courses for one skill, found by searching with the skill's own description. */
export function SkillResources({ skillId, k = 3 }: { skillId: string; k?: number }) {
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined
    // While the GPU worker starts, the server answers with keyword results; ask again a few
    // times so the list switches to GPU results without a reload.
    const load = (attempt: number) => {
      getResources(skillId, k)
        .then(r => {
          if (cancelled) return
          setResponse(r)
          if (r.engine === 'keyword' && r.note.includes('starting up') && attempt < GPU_RETRIES) {
            timer = window.setTimeout(() => load(attempt + 1), GPU_RETRY_MS)
          }
        })
        .catch(() => !cancelled && setFailed(true))
    }
    load(0)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [skillId, k])

  if (failed) return <p className="text-sm text-graphite">Search is not available right now.</p>
  if (!response) return <p className="text-sm text-graphite" role="status">Searching… (the GPU may take up to 15 s to wake up)</p>
  return <ResourceList response={response} />
}
