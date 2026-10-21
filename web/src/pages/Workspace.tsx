import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getCase, postDecision, postMessage } from '../api'
import type { Case, CaseDocument, DecisionResponse, UiAction } from '../types'

const HELP_DOTS = ['●', '●', '●', '●', '●']
const DECISION_LABELS: Record<string, string> = {
  sign_off: 'Sign off',
  correct: 'Correct',
  escalate: 'Escalate',
}

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
        setMessages(prev => [...prev, {
          role: 'assistant',
          text: `Not quite. ${res.explanation} Let me walk you through it.`
        }])
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
    return <div className="text-center py-16 text-gray-400">Loading case…</div>
  }

  const isCheckin = caseData.mode === 'checkin'

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-gray-900">{caseData.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{caseData.mode}</span>
            <span className="text-xs text-gray-400">{caseData.scenario_variant} scenario</span>
            {isCheckin && <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">No hints available</span>}
          </div>
        </div>
        <div className="flex items-center gap-1" title={`Help level: ${helpLevel}/4`}>
          {HELP_DOTS.map((d, i) => (
            <span key={i} className={`text-lg ${i < helpLevel ? 'text-indigo-500' : 'text-gray-200'}`}>{d}</span>
          ))}
        </div>
      </div>

      {/* Pop-in toast */}
      {popIn && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3 flex items-center justify-between">
          <span className="text-sm text-indigo-800 font-medium">🤖 {popIn}</span>
          <button onClick={() => setPopIn(null)} className="text-indigo-400 hover:text-indigo-600 text-lg leading-none">×</button>
        </div>
      )}

      {/* Trace strip */}
      {trace.length > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-xs text-gray-500">
          <span className="font-medium text-gray-600 mr-2">Agent:</span>
          {trace.join(' → ')}
        </div>
      )}

      {/* Main 3-column layout */}
      <div className="grid grid-cols-3 gap-4">
        {/* Ledger */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
            Ledger
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-3 py-2 text-left text-gray-500">Date</th>
                <th className="px-3 py-2 text-left text-gray-500">Description</th>
                <th className="px-3 py-2 text-right text-gray-500">Amount</th>
                <th className="px-2 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {caseData.ledger.map(row => (
                <tr
                  key={row.row_id}
                  className={`border-b border-gray-50 transition-colors ${highlightedRows.has(row.row_id) ? 'bg-amber-50 border-l-4 border-l-amber-400' : ''} ${flaggedRows.has(row.row_id) ? 'bg-red-50' : ''}`}
                >
                  <td className="px-3 py-2 text-gray-500">{row.date.slice(5)}</td>
                  <td className="px-3 py-2 text-gray-800 max-w-0 truncate">
                    {row.description}
                    {row.doc_ref && (
                      <button
                        onClick={() => setOpenDoc(row.doc_ref!)}
                        className="ml-1 text-indigo-400 hover:text-indigo-600 text-xs"
                        title={`Open ${row.doc_ref}`}
                      >📎</button>
                    )}
                  </td>
                  <td className={`px-3 py-2 text-right font-mono ${row.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {fmt(row.amount)}
                  </td>
                  <td className="px-2 py-2">
                    <input type="checkbox" checked={flaggedRows.has(row.row_id)} onChange={() => toggleFlag(row.row_id)} className="accent-red-400" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* Adjustments */}
          {caseData.ai_output.proposed_adjustments.length > 0 && (
            <div className="border-t border-dashed border-gray-200 px-3 py-2">
              <div className="text-xs text-gray-400 mb-1 font-medium">AI adjustments</div>
              {caseData.ai_output.proposed_adjustments.map(adj => (
                <div key={adj.id} className={`flex items-center justify-between text-xs py-1 ${flaggedRows.has(adj.id) ? 'bg-red-50 rounded px-1' : ''} ${highlightedRows.has(adj.id) ? 'bg-amber-50 rounded px-1' : ''}`}>
                  <div>
                    <span className="font-medium text-gray-700">{adj.id}</span>
                    <span className="text-gray-400 ml-1">— {adj.reason}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`font-mono ${adj.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>{fmt(adj.amount)}</span>
                    <input type="checkbox" checked={flaggedRows.has(adj.id)} onChange={() => toggleFlag(adj.id)} className="accent-red-400" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bank statement */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase tracking-wide">
            Bank statement
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-3 py-2 text-left text-gray-500">Date</th>
                <th className="px-3 py-2 text-left text-gray-500">Description</th>
                <th className="px-3 py-2 text-right text-gray-500">Amount</th>
              </tr>
            </thead>
            <tbody>
              {caseData.bank.map(row => (
                <tr
                  key={row.row_id}
                  className={`border-b border-gray-50 transition-colors ${highlightedRows.has(row.row_id) ? 'bg-amber-50 border-l-4 border-l-amber-400' : ''}`}
                >
                  <td className="px-3 py-2 text-gray-500">{row.date.slice(5)}</td>
                  <td className="px-3 py-2 text-gray-800 max-w-0 truncate">{row.description}</td>
                  <td className={`px-3 py-2 text-right font-mono ${row.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {fmt(row.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Right panel: AI claim + documents */}
        <div className="flex flex-col gap-3">
          {/* AI claim */}
          <div className="bg-white rounded-xl border border-indigo-100 p-4">
            <div className="text-xs font-semibold text-indigo-600 uppercase tracking-wide mb-2">AI claim</div>
            <p className="text-sm text-gray-800">{caseData.ai_output.claim}</p>
          </div>

          {/* Check results */}
          {checkResults.map(cr => (
            <div key={cr.check} className="bg-white rounded-xl border border-gray-200 p-3">
              <div className="text-xs font-medium text-gray-500 mb-1">✓ {cr.check.replace(/_/g, ' ')}</div>
              <p className="text-xs text-gray-700 font-mono">{cr.result}</p>
            </div>
          ))}

          {/* Document panel */}
          {openDocData && (
            <div className="bg-white rounded-xl border border-green-200 p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-semibold text-green-700 uppercase tracking-wide">📄 {openDocData.doc_ref}</div>
                <button onClick={() => setOpenDoc(null)} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
              </div>
              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">{openDocData.text}</pre>
            </div>
          )}

          {/* Documents list */}
          <div className="bg-white rounded-xl border border-gray-200 p-3">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Documents</div>
            <div className="space-y-1">
              {caseData.documents.map(doc => (
                <button
                  key={doc.doc_ref}
                  onClick={() => setOpenDoc(openDoc === doc.doc_ref ? null : doc.doc_ref)}
                  className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${openDoc === doc.doc_ref ? 'bg-green-50 text-green-700' : 'hover:bg-gray-50 text-gray-600'}`}
                >
                  📄 {doc.doc_ref} <span className="text-gray-400">— {doc.type}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Companion panel */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Chat messages */}
        <div className="h-48 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-6">
              {isCheckin
                ? 'Check-in mode — no hints available. Review and submit your decision.'
                : "Review the reconciliation above. Use 'I'm stuck' if you need a nudge."}
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-sm px-3 py-2 rounded-xl text-sm ${m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                {m.text}
              </div>
            </div>
          ))}
          {decisionResult && (
            <div className={`rounded-xl p-3 text-sm ${decisionResult.decision_correct ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
              {decisionResult.decision_correct ? '✓ Correct! ' : '✗ Not quite. '}
              {decisionResult.explanation}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input and controls */}
        <div className="border-t border-gray-200 p-3 bg-gray-50">
          <div className="flex gap-2 mb-3">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
              placeholder="Ask the companion…"
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 bg-white"
              disabled={sending}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={sending || !input.trim()}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              Send
            </button>
            {!isCheckin && (
              <button
                onClick={() => sendMessage("I'm stuck")}
                disabled={sending || helpLevel >= 4}
                className="bg-amber-100 text-amber-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-amber-200 disabled:opacity-50 transition-colors"
              >
                I'm stuck
              </button>
            )}
          </div>

          {flaggedRows.size > 0 && (
            <div className="text-xs text-gray-500 mb-2">
              Flagged rows: {[...flaggedRows].join(', ')}
            </div>
          )}

          <div className="flex gap-2">
            {(['sign_off', 'correct', 'escalate'] as const).map(d => (
              <button
                key={d}
                onClick={() => handleDecision(d)}
                disabled={deciding}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                  d === 'sign_off' ? 'bg-green-100 text-green-700 hover:bg-green-200' :
                  d === 'correct' ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' :
                  'bg-red-100 text-red-700 hover:bg-red-200'
                }`}
              >
                {DECISION_LABELS[d]}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
