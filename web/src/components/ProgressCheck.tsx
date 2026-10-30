import { MessageSquareText } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { sendJSON } from '../api'
import type { CheckState } from '../typesAgents'
import { levelText } from './journey'
import { Windows } from './Windows'

// Progress check (docs/PHASE2_PLAN.md A8, contract C6): a finance reviewer asks about work the
// person did, then proposes a level from the person's own words. The person accepts or declines;
// an accepted level is still a claim ("checked by the agent"), never "verified".

type Turn = { q: string; a: string }

function Chat({ profileId, skill }: { profileId: string; skill: string }) {
  const [state, setState] = useState<CheckState | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState<string | null>(null)

  async function call(path: string, body: unknown): Promise<CheckState | null> {
    setBusy(true)
    setError(null)
    try {
      return await sendJSON<CheckState>(path, { body })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
      return null
    } finally {
      setBusy(false)
    }
  }

  async function begin() {
    const out = await call(`/api/profiles/${profileId}/checks`, { skill })
    if (out) {
      setState(out)
      setSession(out.session_id ?? null)
    }
  }

  async function reply(event: FormEvent) {
    event.preventDefault()
    if (!state?.question || !session || !text.trim()) return
    const asked = state.question
    const out = await call(`/api/profiles/${profileId}/checks/${session}/answer`, { text })
    if (out) {
      setTurns((t) => [...t, { q: asked, a: text }])
      setText('')
      setState(out)
    }
  }

  async function decide(accept: boolean) {
    if (!session) return
    const out = await call(`/api/profiles/${profileId}/checks/${session}/decide`, { accept })
    if (out) setState(out)
  }

  if (!state) {
    return (
      <div className="flex flex-col gap-3">
        <p className="m-0">A senior finance reviewer will ask two to four questions about work you have done. It does not teach or test knowledge; it reads your answers against the level descriptions and proposes a level. You decide whether to keep it.</p>
        <button type="button" className="btn btn-v self-start" disabled={busy} onClick={begin}>{busy ? 'Starting…' : 'Start the check'}</button>
        {error && <p role="alert" className="m-0 text-weak">{error}</p>}
      </div>
    )
  }
  const result = state.result
  return (
    <div className="flex flex-col gap-3">
      <span className="font-mono text-[11px] text-graphite">Now: {levelText(state.current_level)} · the role needs {levelText(state.target_level)}</span>
      <ol className="m-0 flex list-none flex-col gap-2 p-0" aria-live="polite">
        {turns.map((t, i) => (
          <li key={i} className="flex flex-col gap-1">
            <span className="rounded-md bg-mist px-3 py-2">{t.q}</span>
            <span className="self-end rounded-md bg-violet-soft px-3 py-2">{t.a}</span>
          </li>
        ))}
        {state.question && !result && <li className="rounded-md bg-mist px-3 py-2">{state.question}</li>}
      </ol>
      {state.question && !result && (
        <form onSubmit={reply} className="flex flex-col gap-2">
          <label className="sr-only" htmlFor="check-answer">Your answer</label>
          <textarea id="check-answer" rows={3} value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} className="rounded-md border border-hairline bg-paper p-2" placeholder="What you did, with which tool, how often, and what happened" />
          <button type="submit" className="btn btn-v self-start" disabled={busy || !text.trim()}>{busy ? 'Reading your answer…' : 'Send'}</button>
        </form>
      )}
      {result && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <span className="cap">Proposed level</span>
          <p className="m-0 text-[15px] font-semibold">
            {result.proposed_level > state.current_level
              ? `${levelText(state.current_level)} → ${levelText(result.proposed_level)}`
              : `Stays at ${levelText(state.current_level)}: the answers did not clearly show the next level`}
          </p>
          {result.met.length > 0 && (
            <ul className="m-0 flex flex-col gap-1 pl-4 text-[13px]">
              {result.met.map((m) => <li key={m.level}>Level {m.level}: {m.verdict}, from your words “{m.quote}”</li>)}
            </ul>
          )}
          <span className="font-mono text-[11px] text-ash">{result.engine}. {result.note} A level you accept is your claim, checked by the agent, not verified.</span>
          {state.decided ? (
            <p className="m-0 text-[13px]">{state.decided === 'accepted' ? 'Saved to your profile. Your plan and scores use it from now on.' : 'Nothing changed.'}</p>
          ) : result.proposed_level > state.current_level ? (
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn btn-v" disabled={busy} onClick={() => decide(true)}>Keep this level</button>
              <button type="button" className="btn" disabled={busy} onClick={() => decide(false)}>Keep my current level</button>
            </div>
          ) : null}
        </div>
      )}
      {error && <p role="alert" className="m-0 text-weak">{error}</p>}
    </div>
  )
}

export function ProgressCheckButton({ profileId, skill, skillName }: { profileId: string | null; skill: string; skillName: string }) {
  const [open, setOpen] = useState(false)
  if (!profileId) return null
  return (
    <>
      <button type="button" className="btn min-h-[44px] gap-1.5" onClick={() => setOpen(true)}>
        <MessageSquareText size={15} aria-hidden="true" />
        Check my progress in {skillName}
      </button>
      {open && (
        <Windows
          title={`Progress check · ${skillName}`}
          panes={[{ key: 'chat', title: 'Senior finance reviewer', hint: 'Asks about work you did; you decide', body: <Chat profileId={profileId} skill={skill} /> }]}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  )
}
