import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowUpRight, Bot, Check, FileText, LifeBuoy, Paperclip, PencilLine, Send, X, type LucideIcon } from 'lucide-react'
import { getCase, postDecision, postMessage } from '../api'
import type { Case, CaseDocument, DecisionResponse, UiAction } from '../types'
import { btn, Card, input as inputCls, label, Loading, Tag } from '../ui'

// Help ladder from the contract (help_level 1..4); 0 means no help used yet.
const HELP_STEPS = ['Question', 'Hint', 'Explanation', 'Answer']
const MAX_HELP_LEVEL = HELP_STEPS.length

const DECISIONS: { id: 'sign_off' | 'correct' | 'escalate'; label: string; icon: LucideIcon }[] = [
  { id: 'sign_off', label: 'Sign off', icon: Check },
  { id: 'correct', label: 'Correct', icon: PencilLine },
  { id: 'escalate', label: 'Escalate', icon: ArrowUpRight },
]

function fmt(n: number) {
  return n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function Workspace() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const sessionId = useRef(`s_${Date.now()}`)

  const [caseData, setCaseData] = useState<Case | null>(null)
  const [loading, setLoading] = useState(true)

  // Companion state
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([])
  const [trace, setTrace] = useState<string[]>([])
  const [checkResults, setCheckResults] = useState<{ check: string; result: string }[]>([])
  const [helpLevel, setHelpLevel] = useState(0)
  const [highlightedRows, setHighlightedRows] = useState<Set<string>>(new Set())
  const [openDoc, setOpenDoc] = useState<string | null>(null)
  const [popIn, setPopIn] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  // Decision state
  const [flaggedRows, setFlaggedRows] = useState<Set<string>>(new Set())
  const [decisionResult, setDecisionResult] = useState<DecisionResponse | null>(null)
  const [deciding, setDeciding] = useState(false)

  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!caseId) return
    getCase(caseId).then(c => { setCaseData(c); setLoading(false) })
  }, [caseId])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const applyActions = (actions: UiAction[]) => {
    for (const a of actions) {
      if (a.type === 'highlight_rows' && a.rows) setHighlightedRows(new Set(a.rows))
      if (a.type === 'open_document' && a.doc_ref) setOpenDoc(a.doc_ref)
      if (a.type === 'show_check' && a.check && a.result)
        setCheckResults(prev => [...prev.filter(c => c.check !== a.check!), { check: a.check!, result: a.result! }])
      if (a.type === 'pop_in' && a.message) setPopIn(a.message)
    }
  }

  const sendMessage = async (text: string) => {
    if (!caseId || !text.trim()) return
    setSending(true)
    setMessages(prev => [...prev, { role: 'user', text }])
    setInput('')
    try {
      const res = await postMessage(sessionId.current, caseId, text)
      setMessages(prev => [...prev, { role: 'assistant', text: res.reply }])
      setHelpLevel(res.help_level)
      setTrace(res.trace)
      applyActions(res.ui_actions)
    } finally {
      setSending(false)
    }
  }

  const handleDecision = async (decision: 'sign_off' | 'correct' | 'escalate') => {
    if (!caseId) return
    setDeciding(true)
    setPopIn(null)
    try {
      const res = await postDecision(sessionId.current, caseId, decision, [...flaggedRows])
      setDecisionResult(res)
      if (!res.missed_and_walking_back) {
        // Navigate to result page after a brief moment
        setTimeout(() => navigate(`/result/${caseId}`, { state: { result: res } }), 1200)
      } else {
        // Walk back: keep workspace open, companion guides
        // The server reveals nothing from the answer here; help comes through the ladder.
        setDecisionResult(null)
        setMessages(prev => [...prev, { role: 'assistant', text: `Not quite. ${res.explanation}` }])
      }
    } finally {
      setDeciding(false)
    }
  }

  const toggleFlag = (rowId: string) =>
    setFlaggedRows(prev => {
      const next = new Set(prev)
      next.has(rowId) ? next.delete(rowId) : next.add(rowId)
      return next
    })

  const openDocData = openDoc && caseData
    ? caseData.documents.find((d: CaseDocument) => d.doc_ref === openDoc) ?? null
    : null

  if (loading || !caseData) {
    return <Loading what="case" />
  }

  const isCheckin = caseData.mode === 'checkin'

  const rowTone = (id: string) => highlightedRows.has(id) ? 'bg-marigold-tint shadow-[inset_3px_0_0_var(--color-marigold)]' : flaggedRows.has(id) ? 'bg-coral-tint' : ''

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[28px] leading-[1.2] font-semibold tracking-[-0.02em] text-ink">{caseData.title}</h1>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <Tag tone={isCheckin ? 'coral' : 'action'}>{isCheckin ? 'Check-in · no help' : caseData.mode}</Tag>
            <span className="text-xs text-graphite">{caseData.scenario_variant} scenario</span>
          </div>
        </div>
        {!isCheckin && (
          <ol className="flex items-center gap-1 text-xs" aria-label={`Help used: ${helpLevel} of ${MAX_HELP_LEVEL}`}>
            {HELP_STEPS.map((step, i) => (
              <li key={step} className="flex items-center gap-1">
                {i > 0 && <span className="text-hairline-strong" aria-hidden="true">→</span>}
                <span className={i < helpLevel ? 'font-medium text-action-ink' : 'text-graphite'}>{step}</span>
              </li>
            ))}
          </ol>
        )}
      </div>

      {/* Pop-in from the companion */}
      {popIn && (
        <div className="bg-action-tint rounded-lg px-4 py-3 flex items-center justify-between gap-3" role="status">
          <span className="flex items-center gap-2 text-sm text-action-ink font-medium"><Bot size={16} aria-hidden="true" /> {popIn}</span>
          <button onClick={() => setPopIn(null)} aria-label="Dismiss" className="text-action-ink/70 hover:text-action-ink rounded-sm p-1"><X size={16} /></button>
        </div>
      )}

      {/* Trace strip */}
      {trace.length > 0 && (
        <div className="bg-linen rounded-md px-4 py-2 text-xs text-graphite">
          <span className="font-medium text-ink mr-2">Companion steps:</span>
          {trace.join(' → ')}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px] items-start">
        {/* Work area */}
        <div className="flex flex-col gap-4 min-w-0">
          {/* AI draft: kept visually separate from the person's decision */}
          <div className="bg-linen rounded-lg p-4">
            <div className="flex items-center gap-1.5 text-xs font-medium text-graphite mb-1.5"><Bot size={14} aria-hidden="true" /> AI draft</div>
            <p className="text-ink">{caseData.ai_output.claim}</p>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            {/* Ledger */}
            <Card className="overflow-hidden">
              <div className={`${label} px-4 py-3 border-b border-hairline`}>Ledger</div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-graphite">
                    <th className="px-3 py-2 text-left font-medium">Date</th>
                    <th className="px-3 py-2 text-left font-medium">Description</th>
                    <th className="px-3 py-2 text-right font-medium">Amount</th>
                    <th className="px-2 py-2"><span className="sr-only">Flag</span></th>
                  </tr>
                </thead>
                <tbody>
                  {caseData.ledger.map(row => (
                    <tr key={row.row_id} className={`border-t border-hairline transition-colors duration-200 ${rowTone(row.row_id)}`}>
                      <td className="px-3 py-2 text-graphite tabular-nums whitespace-nowrap">{row.date.slice(5)}</td>
                      <td className="px-3 py-2 text-ink max-w-0 truncate">
                        {row.description}
                        {row.doc_ref && (
                          <button
                            onClick={() => setOpenDoc(row.doc_ref!)}
                            className="ml-1 align-middle text-action-ink hover:text-action rounded-sm"
                            title={`Open ${row.doc_ref}`} aria-label={`Open ${row.doc_ref}`}
                          ><Paperclip size={14} /></button>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink whitespace-nowrap">{fmt(row.amount)}</td>
                      <td className="px-2 py-2">
                        <input type="checkbox" aria-label={`Flag row ${row.row_id}`} checked={flaggedRows.has(row.row_id)} onChange={() => toggleFlag(row.row_id)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {/* Adjustments */}
              {caseData.ai_output.proposed_adjustments.length > 0 && (
                <div className="border-t border-dashed border-hairline-strong px-3 py-3">
                  <div className={`${label} mb-1 flex items-center gap-1`}><Bot size={12} aria-hidden="true" /> AI adjustments</div>
                  {caseData.ai_output.proposed_adjustments.map(adj => (
                    <div key={adj.id} className={`flex items-center justify-between gap-2 text-sm py-1 px-1 rounded-sm ${rowTone(adj.id)}`}>
                      <div className="min-w-0">
                        <span className="font-medium text-ink">{adj.id}</span>
                        <span className="text-graphite ml-1">· {adj.reason}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="tabular-nums text-ink whitespace-nowrap">{fmt(adj.amount)}</span>
                        <input type="checkbox" aria-label={`Flag adjustment ${adj.id}`} checked={flaggedRows.has(adj.id)} onChange={() => toggleFlag(adj.id)} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Bank statement */}
            <Card className="overflow-hidden">
              <div className={`${label} px-4 py-3 border-b border-hairline`}>Bank statement</div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-graphite">
                    <th className="px-3 py-2 text-left font-medium">Date</th>
                    <th className="px-3 py-2 text-left font-medium">Description</th>
                    <th className="px-3 py-2 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {caseData.bank.map(row => (
                    <tr key={row.row_id} className={`border-t border-hairline transition-colors duration-200 ${rowTone(row.row_id)}`}>
                      <td className="px-3 py-2 text-graphite tabular-nums whitespace-nowrap">{row.date.slice(5)}</td>
                      <td className="px-3 py-2 text-ink max-w-0 truncate">{row.description}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink whitespace-nowrap">{fmt(row.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>

          {/* Check results */}
          {checkResults.map(cr => (
            <Card key={cr.check} className="p-4">
              <div className={`${label} mb-1 flex items-center gap-1`}><Check size={12} aria-hidden="true" /> {cr.check.replace(/_/g, ' ')}</div>
              <p className="text-sm text-ink font-mono">{cr.result}</p>
            </Card>
          ))}

          {/* Documents */}
          <Card className="p-4">
            <div className={`${label} mb-2`}>Documents</div>
            <div className="flex flex-wrap gap-2">
              {caseData.documents.map(doc => (
                <button
                  key={doc.doc_ref}
                  onClick={() => setOpenDoc(openDoc === doc.doc_ref ? null : doc.doc_ref)}
                  aria-pressed={openDoc === doc.doc_ref}
                  className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors duration-200 ${openDoc === doc.doc_ref ? 'bg-action-tint text-action-ink font-medium' : 'border border-hairline-strong text-ink hover:bg-linen'}`}
                >
                  <FileText size={14} aria-hidden="true" /> {doc.doc_ref} <span className="text-graphite font-normal">· {doc.type}</span>
                </button>
              ))}
            </div>
            {openDocData && (
              <div className="mt-3 bg-linen rounded-md p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5 text-sm font-medium text-ink"><FileText size={14} aria-hidden="true" /> {openDocData.doc_ref}</div>
                  <button onClick={() => setOpenDoc(null)} aria-label="Close document" className="text-graphite hover:text-ink rounded-sm p-1"><X size={16} /></button>
                </div>
                <pre className="text-sm text-ink whitespace-pre-wrap font-mono leading-relaxed">{openDocData.text}</pre>
              </div>
            )}
          </Card>
        </div>

        {/* Companion panel */}
        <Card className="flex flex-col lg:sticky lg:top-20 lg:h-[calc(100svh-6rem)] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-hairline">
            <Bot size={20} strokeWidth={1.75} className="text-action" aria-hidden="true" />
            <span className="font-semibold text-ink">Companion</span>
          </div>

          <div className="flex-1 min-h-48 overflow-y-auto p-4 space-y-3" aria-live="polite">
            {messages.length === 0 && (
              <p className="text-sm text-graphite text-center py-6">
                {isCheckin
                  ? 'Check-in: no hints this time. Review the work and make your decision.'
                  : 'Review the AI draft. Ask a question, or say you are stuck to get the next step of help.'}
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${m.role === 'user' ? 'bg-action text-white' : 'bg-linen text-ink'}`}>
                  {m.text}
                </div>
              </div>
            ))}
            {decisionResult && (
              <div className={`rounded-lg p-3 text-sm ${decisionResult.decision_correct ? 'bg-action-tint text-action-ink' : 'bg-coral-tint text-coral-ink'}`}>
                <span className="font-medium">{decisionResult.decision_correct ? 'Correct. ' : 'Not quite. '}</span>
                {decisionResult.explanation}
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="border-t border-hairline p-4 space-y-3">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
                placeholder="Ask the companion…"
                aria-label="Message the companion"
                className={`${inputCls} flex-1 min-w-0`}
                disabled={sending}
              />
              <button onClick={() => sendMessage(input)} disabled={sending || !input.trim()} className={btn.ghost} aria-label="Send">
                <Send size={16} aria-hidden="true" />
              </button>
            </div>
            {!isCheckin && (
              <button onClick={() => sendMessage("I'm stuck")} disabled={sending || helpLevel >= MAX_HELP_LEVEL} className={`${btn.text} w-full border border-dashed border-hairline-strong`}>
                <LifeBuoy size={16} aria-hidden="true" /> I'm stuck
              </button>
            )}

            {flaggedRows.size > 0 && (
              <div className="text-xs text-graphite">Flagged: {[...flaggedRows].join(', ')}</div>
            )}

            <div>
              <div className={`${label} mb-2`}>Your decision</div>
              {/* Equal weight on purpose: the UI must not nudge the person toward one decision. */}
              <div className="grid grid-cols-3 gap-2">
                {DECISIONS.map(d => (
                  <button key={d.id} onClick={() => handleDecision(d.id)} disabled={deciding} className={`${btn.outline} flex-col gap-1 py-3 px-2`}>
                    <d.icon size={20} strokeWidth={1.75} aria-hidden="true" />
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
