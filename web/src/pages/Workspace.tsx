import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowUpRight, Bot, Check, CircleCheck, FileText, Flag, LifeBuoy, PencilLine, Send, type LucideIcon } from 'lucide-react'
import { getCase, postDecision, postMessage } from '../api'
import { useUserId } from '../persona'
import type { Case, CaseDocument, DecisionResponse, UiAction } from '../types'
import { enter, pop, useReveal } from '../motion'
import { btn, Card, Drawer, input as inputCls, label, Loading, Tag } from '../ui'

// Help ladder from the contract (help_level 1..4); 0 means no help used yet.
const HELP_STEPS = ['Question', 'Hint', 'Explanation', 'Answer']
const MAX_HELP_LEVEL = HELP_STEPS.length

const DECISIONS: { id: 'sign_off' | 'correct' | 'escalate'; label: string; icon: LucideIcon }[] = [
  { id: 'sign_off', label: 'Sign off', icon: Check },
  { id: 'correct', label: 'Correct', icon: PencilLine },
  { id: 'escalate', label: 'Escalate', icon: ArrowUpRight },
]

type TableView = 'both' | 'ledger' | 'bank'
const TABLE_VIEWS: { id: TableView; label: string }[] = [
  { id: 'both', label: 'Side by side' },
  { id: 'ledger', label: 'Ledger' },
  { id: 'bank', label: 'Bank statement' },
]
// Below this width two tables side by side would truncate descriptions again.
const WIDE_SCREEN_PX = 1280

function fmt(n: number) {
  return n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** Rises in once when it first appears (GSAP). */
function Appear({ children, className = '' }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => enter(ref.current), [])
  return <div ref={ref} className={className}>{children}</div>
}

function TaskStep({ n, done, children }: { n: number; done: boolean; children: ReactNode }) {
  const circle = useRef<HTMLSpanElement>(null)
  const wasDone = useRef(done)
  // Pop only on the change to done, not on first render.
  useEffect(() => {
    if (done && !wasDone.current) pop(circle.current)
    wasDone.current = done
  }, [done])
  return (
    <li className={`flex items-center gap-2 text-sm ${done ? 'text-ink' : 'text-marigold-ink'}`}>
      <span ref={circle} className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 ${done ? 'bg-action text-white' : 'bg-surface text-marigold-ink border border-marigold/60'}`}>
        {done ? <Check size={14} strokeWidth={2.5} aria-hidden="true" /> : n}
      </span>
      <span>{children}</span>
      <span className="sr-only">{done ? '(done)' : '(to do)'}</span>
    </li>
  )
}

export default function Workspace() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const sessionId = useRef(`s_${Date.now()}`)
  const userId = useUserId()

  const [caseData, setCaseData] = useState<Case | null>(null)
  const [loading, setLoading] = useState(true)

  // Companion state
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([])
  const [trace, setTrace] = useState<string[]>([])
  const [checkResults, setCheckResults] = useState<{ check: string; result: string }[]>([])
  const [helpLevel, setHelpLevel] = useState(0)
  const [highlightedRows, setHighlightedRows] = useState<Set<string>>(new Set())
  const [openDoc, setOpenDoc] = useState<string | null>(null)
  const [docsViewed, setDocsViewed] = useState(false)
  const [popIn, setPopIn] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  // Decision state
  const [flaggedRows, setFlaggedRows] = useState<Set<string>>(new Set())
  const [decisionResult, setDecisionResult] = useState<DecisionResponse | null>(null)
  const [deciding, setDeciding] = useState(false)

  const chatEndRef = useRef<HTMLDivElement>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  useReveal(rootRef, [loading])

  useEffect(() => {
    if (!caseId) return
    getCase(caseId).then(c => { setCaseData(c); setLoading(false) })
  }, [caseId])

  useEffect(() => {
    // 'nearest' scrolls only the chat panel, not the whole page
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages])

  const showDoc = (ref: string) => { setOpenDoc(ref); setDocsViewed(true) }
  const closeDoc = useCallback(() => setOpenDoc(null), [])

  // Pick the table layout once from the screen width; the person can switch it.
  const [tableView, setTableView] = useState<TableView>(() => (window.innerWidth >= WIDE_SCREEN_PX ? 'both' : 'ledger'))

  const applyActions = (actions: UiAction[]) => {
    for (const a of actions) {
      if (a.type === 'highlight_rows' && a.rows) setHighlightedRows(new Set(a.rows))
      if (a.type === 'open_document' && a.doc_ref) showDoc(a.doc_ref)
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
      const res = await postMessage(sessionId.current, caseId, text, userId, caseData?.scenario_variant ?? 'assistive')
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
      const res = await postDecision(sessionId.current, caseId, decision, [...flaggedRows], userId, caseData?.scenario_variant ?? 'assistive')
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
  const adjustments = caseData.ai_output.proposed_adjustments
  const starters = [
    'Where should I start?',
    adjustments[0] ? `What is ${adjustments[0].id} based on?` : 'What does the AI claim rest on?',
    'Do the totals match?',
  ]

  // Task strip ticks itself from what the person has already done; nothing new is stored.
  const compared = docsViewed || checkResults.length > 0 || messages.length > 0
  const steps = [
    { done: true, text: 'Read the AI draft' },
    { done: compared, text: 'Compare rows and documents' },
    { done: flaggedRows.size > 0, text: flaggedRows.size > 0 ? `Flag anything wrong (${flaggedRows.size} flagged)` : 'Flag anything wrong' },
    { done: deciding || decisionResult !== null, text: 'Decide' },
  ]

  const rowTone = (id: string) =>
    highlightedRows.has(id) ? 'bg-marigold-tint shadow-[inset_3px_0_0_var(--color-marigold)]'
      : flaggedRows.has(id) ? 'bg-coral-tint shadow-[inset_3px_0_0_var(--color-coral)]' : ''

  const flagCell = (id: string) => (
    <label className="inline-flex items-center gap-1.5 cursor-pointer text-xs text-graphite">
      <input type="checkbox" checked={flaggedRows.has(id)} onChange={() => toggleFlag(id)} aria-label={`Flag ${id}`} />
      {flaggedRows.has(id) && <span className="text-coral-ink font-medium">Flagged</span>}
    </label>
  )

  const ledgerTable = (
    <Card className="overflow-hidden">
      <div className={`${label} px-4 py-3 border-b border-hairline`}>Ledger</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-graphite">
            <th className="px-3 py-2 text-left font-medium w-14">Date</th>
            <th className="px-3 py-2 text-left font-medium">Description</th>
            <th className="px-3 py-2 text-right font-medium">Amount</th>
            <th className="px-3 py-2 text-left font-medium w-24">Flag</th>
          </tr>
        </thead>
        <tbody>
          {caseData.ledger.map(row => (
            <tr key={row.row_id} className={`border-t border-hairline align-top transition-colors duration-200 ${rowTone(row.row_id)}`}>
              <td className="px-3 py-2.5 text-graphite tabular-nums whitespace-nowrap">{row.date.slice(5)}</td>
              <td className="px-3 py-2.5 text-ink">
                {row.description}
                {row.doc_ref && (
                  <button
                    onClick={() => showDoc(row.doc_ref!)}
                    className="ml-2 inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-action-tint text-action-ink px-2 py-0.5 text-xs font-medium hover:bg-[#d6eafd] align-middle"
                  >
                    <FileText size={12} aria-hidden="true" /> {row.doc_ref}
                  </button>
                )}
              </td>
              <td className="px-3 py-2.5 text-right tabular-nums text-ink whitespace-nowrap">{fmt(row.amount)}</td>
              <td className="px-3 py-2.5">{flagCell(row.row_id)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )

  const bankTable = (
    <Card className="overflow-hidden">
      <div className={`${label} px-4 py-3 border-b border-hairline`}>Bank statement</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-graphite">
            <th className="px-3 py-2 text-left font-medium w-14">Date</th>
            <th className="px-3 py-2 text-left font-medium">Description</th>
            <th className="px-3 py-2 text-right font-medium">Amount</th>
          </tr>
        </thead>
        <tbody>
          {caseData.bank.map(row => (
            <tr key={row.row_id} className={`border-t border-hairline align-top transition-colors duration-200 ${rowTone(row.row_id)}`}>
              <td className="px-3 py-2.5 text-graphite tabular-nums whitespace-nowrap">{row.date.slice(5)}</td>
              <td className="px-3 py-2.5 text-ink">{row.description}</td>
              <td className="px-3 py-2.5 text-right tabular-nums text-ink whitespace-nowrap">{fmt(row.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )

  return (
    <div ref={rootRef} className="flex flex-col gap-5">
      {/* Case header */}
      <div data-reveal>
        <h1 className="text-[28px] sm:text-[32px] leading-[1.15] font-semibold tracking-[-0.025em] text-ink">{caseData.title}</h1>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <Tag tone={isCheckin ? 'coral' : 'action'}>{isCheckin ? 'Check-in · no help' : caseData.mode}</Tag>
          <span className="text-xs text-graphite">{caseData.scenario_variant} scenario</span>
        </div>
      </div>

      {/* Task strip: what to do on this screen */}
      <div data-reveal className="bg-marigold-tint rounded-lg px-5 py-4 flex flex-col xl:flex-row xl:items-center gap-3 xl:gap-8">
        <p className="text-ink font-medium shrink-0">Your job: check the AI's draft, then decide.</p>
        <ol className="flex flex-wrap gap-x-6 gap-y-2">
          {steps.map((st, i) => <TaskStep key={st.text} n={i + 1} done={st.done}>{st.text}</TaskStep>)}
        </ol>
      </div>

      {popIn && (
        <div className="bg-action-tint rounded-lg px-4 py-3 flex items-center gap-2 text-sm text-action-ink font-medium" role="status">
          <Bot size={16} aria-hidden="true" /> {popIn}
          <button onClick={() => setPopIn(null)} className="ml-auto text-xs underline underline-offset-2">Dismiss</button>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] items-start">
        {/* Work area */}
        <div data-reveal className="flex flex-col gap-4 min-w-0">
          {/* AI draft: kept visually apart from the person's decision */}
          <div className="bg-linen rounded-lg p-5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-graphite"><Bot size={14} aria-hidden="true" /> AI draft</div>
            <p className="mt-2 font-serif text-xl leading-[1.45] text-ink">{caseData.ai_output.claim}</p>
            {adjustments.length > 0 && (
              <div className="mt-4 border-t border-hairline-strong/60 pt-3">
                <div className={`${label} mb-1.5`}>Adjustments the AI proposes</div>
                <ul className="space-y-1">
                  {adjustments.map(adj => (
                    <li key={adj.id} className={`flex flex-wrap items-center justify-between gap-2 text-sm rounded-sm px-2 py-1.5 -mx-2 ${rowTone(adj.id)}`}>
                      <span><span className="font-medium text-ink">{adj.id}</span> <span className="text-graphite">· {adj.reason}</span></span>
                      <span className="flex items-center gap-4">
                        <span className="tabular-nums text-ink">{fmt(adj.amount)}</span>
                        {flagCell(adj.id)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Table view switch */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div role="tablist" aria-label="Table view" className="inline-flex bg-linen rounded-md p-1">
              {TABLE_VIEWS.map(v => (
                <button
                  key={v.id} role="tab" aria-selected={tableView === v.id}
                  onClick={() => setTableView(v.id)}
                  className={`px-3 py-1.5 rounded-sm text-sm transition-colors duration-200 ${v.id === 'both' ? 'hidden xl:inline-block' : ''} ${tableView === v.id ? 'bg-surface text-ink font-medium shadow-[0_1px_2px_rgb(0_0_0/0.06)]' : 'text-graphite hover:text-ink'}`}
                >
                  {v.label}
                </button>
              ))}
            </div>
            <span className="text-xs text-graphite">Tick a row to flag it. Document chips open the source.</span>
          </div>

          {tableView === 'both' ? (
            <div className="grid gap-4 xl:grid-cols-2">{ledgerTable}{bankTable}</div>
          ) : tableView === 'ledger' ? ledgerTable : bankTable}

          {/* Check results from the companion */}
          {checkResults.map(cr => (
            <Appear key={cr.check}>
              <Card className="p-4">
                <div className={`${label} mb-1 flex items-center gap-1`}><CircleCheck size={12} aria-hidden="true" /> {cr.check.replace(/_/g, ' ')}</div>
                <p className="text-sm text-ink font-mono">{cr.result}</p>
              </Card>
            </Appear>
          ))}

          {/* Documents */}
          <div>
            <div className={`${label} mb-2`}>Documents</div>
            <div className="flex flex-wrap gap-2">
              {caseData.documents.map(doc => (
                <button
                  key={doc.doc_ref}
                  onClick={() => showDoc(doc.doc_ref)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-surface border border-hairline px-3 py-2 text-sm text-ink hover:border-hairline-strong transition-colors duration-200"
                >
                  <FileText size={14} className="text-action" aria-hidden="true" /> {doc.doc_ref}
                  <span className="text-graphite">· {doc.type}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Companion */}
        <Card data-reveal className="flex flex-col lg:sticky lg:top-28 lg:h-[calc(100svh-8rem)] overflow-hidden">
          <div className="px-4 py-3 border-b border-hairline">
            <div className="flex items-center gap-2.5">
              <span className="w-9 h-9 rounded-full bg-action-tint text-action flex items-center justify-center"><Bot size={20} strokeWidth={1.75} aria-hidden="true" /></span>
              <div>
                <div className="font-semibold text-ink leading-tight">Companion</div>
                <div className="text-xs text-graphite">{isCheckin ? 'Watching only during check-ins' : 'Asks before it tells'}</div>
              </div>
            </div>
            {!isCheckin && (
              <ol className="mt-3 flex flex-wrap items-center gap-1 text-xs" aria-label={`Help used: ${helpLevel} of ${MAX_HELP_LEVEL}`}>
                {HELP_STEPS.map((step, i) => (
                  <li key={step} className="flex items-center gap-1">
                    {i > 0 && <span className="text-hairline-strong" aria-hidden="true">→</span>}
                    <span className={`rounded-full px-2 py-0.5 ${i < helpLevel ? 'bg-action-tint text-action-ink font-medium' : 'text-graphite'}`}>{step}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <div className="flex-1 min-h-56 overflow-y-auto p-4 space-y-3" aria-live="polite">
            {messages.length === 0 && (isCheckin ? (
              <div className="bg-coral-tint text-coral-ink rounded-lg p-4 text-sm">
                <div className="font-semibold">No help in check-ins</div>
                <p className="mt-1">This one shows what you can do on your own. Review the work and make your decision.</p>
              </div>
            ) : (
              <div className="text-sm text-graphite">
                <p>Stuck or unsure? Ask anything. I'll start with a question, not the answer.</p>
                <div className="mt-3 flex flex-col items-start gap-2">
                  {starters.map(q => (
                    <button key={q} onClick={() => sendMessage(q)} disabled={sending} className="rounded-full border border-hairline-strong px-3 py-1.5 text-sm text-ink hover:bg-linen transition-colors duration-200 text-left disabled:opacity-50">
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {messages.map((m, i) => (
              <Appear key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${m.role === 'user' ? 'bg-action text-white' : 'bg-linen text-ink'}`}>
                  {m.text}
                </div>
              </Appear>
            ))}
            {sending && <div className="text-xs text-graphite" role="status">Companion is thinking…</div>}
            {decisionResult && (
              <div className={`rounded-lg p-3 text-sm ${decisionResult.decision_correct ? 'bg-action-tint text-action-ink' : 'bg-coral-tint text-coral-ink'}`}>
                <span className="font-medium">{decisionResult.decision_correct ? 'Correct. ' : 'Not quite. '}</span>
                {decisionResult.explanation}
              </div>
            )}
            {trace.length > 0 && (
              <details className="text-xs text-graphite">
                <summary className="cursor-pointer select-none">How the companion decided</summary>
                <p className="mt-1">{trace.join(' → ')}</p>
              </details>
            )}
            <div ref={chatEndRef} />
          </div>

          {!isCheckin && (
            <div className="border-t border-hairline p-3 space-y-2">
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
                <button onClick={() => sendMessage(input)} disabled={sending || !input.trim()} className={`${btn.ghost} px-3`} aria-label="Send">
                  <Send size={16} aria-hidden="true" />
                </button>
              </div>
              <button onClick={() => sendMessage("I'm stuck")} disabled={sending || helpLevel >= MAX_HELP_LEVEL} className={`${btn.text} w-full border border-dashed border-hairline-strong`}>
                <LifeBuoy size={16} aria-hidden="true" /> I'm stuck
              </button>
            </div>
          )}

          {/* Decision footer, always in view */}
          <div className="border-t border-hairline bg-canvas p-4">
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-sm font-semibold text-ink">Your decision</span>
              {flaggedRows.size > 0
                ? <span className="inline-flex items-center gap-1 text-xs text-coral-ink"><Flag size={12} aria-hidden="true" /> {[...flaggedRows].join(', ')}</span>
                : <span className="text-xs text-graphite">Nothing flagged</span>}
            </div>
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
        </Card>
      </div>

      <Drawer open={openDocData !== null} onClose={closeDoc} title={openDocData ? `${openDocData.doc_ref} · ${openDocData.type}` : ''}>
        {openDocData && <pre className="text-sm text-ink whitespace-pre-wrap font-mono leading-relaxed bg-linen rounded-md p-4">{openDocData.text}</pre>}
      </Drawer>
    </div>
  )
}
