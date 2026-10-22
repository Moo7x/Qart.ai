import { useEffect, useState } from 'react'
import { getResources } from '../api'
import type { SearchResponse } from '../types'

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
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <span
          title={response.note}
          className={`text-xs px-1.5 py-0.5 rounded border font-medium ${gpu ? 'bg-violet-50 text-violet-700 border-violet-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}
        >
          {gpu ? 'GPU search (RunPod)' : 'keyword search'}
        </span>
        <span className="text-xs text-gray-400 truncate">{response.note}</span>
      </div>
      {response.results.length === 0 && <p className="text-xs text-gray-400">Nothing found.</p>}
      {response.results.map(r => (
        <div key={r.document_id} className="text-xs bg-gray-50 rounded px-3 py-2">
          <a href={r.url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline font-medium">
            {r.title}
          </a>
          <div className="text-gray-400 mt-0.5">
            {KIND_LABELS[r.kind] ?? r.kind} · {r.source} · retrieved {r.date}
          </div>
        </div>
      ))}
    </div>
  )
}

/** Verified courses for one skill, found by searching with the skill's own description. */
export function SkillResources({ skillId, k = 3 }: { skillId: string; k?: number }) {
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    getResources(skillId, k).then(setResponse).catch(() => setFailed(true))
  }, [skillId, k])

  if (failed) return <p className="text-xs text-gray-400">Search is not available right now.</p>
  if (!response) return <p className="text-xs text-gray-400">Searching… (the GPU may take up to 15 s to wake up)</p>
  return <ResourceList response={response} />
}
