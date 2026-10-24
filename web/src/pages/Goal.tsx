import { useEffect, useState } from 'react'
import { useT } from '../i18n'
import { Link } from 'react-router-dom'
import { sendJSON, useApi } from '../api'
import { ReportProblem } from '../components/Feedback'
import { Loading, Problem } from '../components/ui'
import { useJourney } from '../state'
import type { GoalInput, GoalResponse, PostingRequirement } from '../types'
import { NeedProfile } from './Roles'

const EMPTY: GoalInput = { role_title: '', company: '', location: '', why: '', posting_text: '', posting_url: '', posting_date: '' }
const STATUS: Record<PostingRequirement['status'], [string, string]> = {
  met: ['You meet it', 'text-rising'],
  below: ['Below the level', 'text-weak'],
  not_stated: ['Not stated · tell us', 'text-graphite'],
  outside_catalogue: ['Outside our skill catalogue', 'text-ash'],
}
const LEVELS = ['none', 'aware', 'working', 'proficient', 'expert']

function Field({ label, value, onChange, placeholder, area }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; area?: boolean }) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-[13px]">
      <span className="cap">{label}</span>
      {area ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={8} maxLength={8000} className="rounded-md border border-hairline px-3 py-2 font-[inherit]" />
      ) : (
        <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} maxLength={120} className="rounded-md border border-hairline px-3 py-2" />
      )}
    </label>
  )
}

export function Goal() {
  const { t } = useT()
  const { profileId, scenario } = useJourney()
  const view = useApi<GoalResponse>(profileId ? `/api/profiles/${profileId}/goal?scenario=${scenario}` : null)
  const [form, setForm] = useState<GoalInput>(EMPTY)
  const [result, setResult] = useState<GoalResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (view.data?.goal) {
      setForm(view.data.goal)
      setResult(view.data)
    }
  }, [view.data])

  if (!profileId) return <NeedProfile />
  const set = (key: keyof GoalInput) => (value: string) => setForm((f) => ({ ...f, [key]: value }))

  async function save(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setResult(await sendJSON<GoalResponse>(`/api/profiles/${profileId}/goal?scenario=${scenario}`, { method: 'PUT', body: form }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  const cov = result?.coverage
  return (
    <main className="flex min-w-0 flex-[999_1_640px] flex-col gap-6 px-5 py-7 md:px-10">
      <header className="flex flex-col gap-1.5">
        <span className="eyebrow">My goal · the role you are aiming for</span>
        <h1 className="h1">{t('Where do you want to be?')}</h1>
        <p className="m-0 max-w-[680px] text-graphite">
          Name the role, and if you have found a real public job posting for it, paste its text. Qart reads that posting&rsquo;s requirements and shows which you already meet, and which roles get you there step by step. This checks one posting; it is not a hiring prediction.
        </p>
      </header>
      {view.loading && <Loading what="your goal" />}
      {view.error && <Problem what="your goal" message={view.error} onRetry={view.reload} />}

      <form onSubmit={save} className="card-light flex flex-col gap-3 px-6 py-5">
        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
          <Field label="Role you want" value={form.role_title} onChange={set('role_title')} placeholder="e.g. FP&A Analyst" />
          <Field label="Company (optional)" value={form.company} onChange={set('company')} placeholder="e.g. a GBS centre in KL" />
          <Field label="Location (optional)" value={form.location} onChange={set('location')} placeholder="e.g. Kuala Lumpur" />
        </div>
        <Field label="Why this goal matters to you (optional)" value={form.why} onChange={set('why')} />
        <Field label="Paste a public job posting (optional)" value={form.posting_text} onChange={set('posting_text')} placeholder="Paste the requirements section of a posting you found" area />
        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
          <Field label="Posting link (optional)" value={form.posting_url} onChange={set('posting_url')} />
          <Field label="Date on the posting (optional)" value={form.posting_date} onChange={set('posting_date')} placeholder="e.g. 2026-10-20" />
        </div>
        <button type="submit" className="btn btn-v self-start" disabled={busy || form.role_title.trim().length < 2}>{busy ? 'Reading the posting…' : t('Save my goal')}</button>
        {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}
      </form>

      {cov && (
        <section className="card-light flex flex-col gap-3 px-6 py-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="h2">This posting&rsquo;s requirements and you</h2>
            <span className="font-mono text-[13px]">covers {cov.covered} of {cov.mapped} · essentials {cov.essentials_met} of {cov.essentials}</span>
          </div>
          <p className="m-0 text-xs text-graphite">
            {result?.goal?.company ? `${result.goal.company} · ` : ''}{result?.goal?.posting_date ? `posting dated ${result.goal.posting_date} · ` : ''}
            Read by {cov.engine}{cov.note ? ` (${cov.note})` : ''}. Each line quotes the posting. Where it states no level, &ldquo;{LEVELS[cov.default_level]}&rdquo; is assumed.{' '}
            {[cov.not_stated > 0 ? `${cov.not_stated} not stated in your profile yet` : '', cov.outside_catalogue > 0 ? `${cov.outside_catalogue} outside our skill catalogue` : ''].filter(Boolean).join('; ')}
            {cov.not_stated + cov.outside_catalogue > 0 ? '.' : ''}
          </p>
          <ul className="m-0 flex list-none flex-col p-0">
            {cov.requirements.map((r) => (
              <li key={r.quote} className="grid gap-1 border-t border-mist py-2 text-[13px] md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_auto]">
                <span>&ldquo;{r.quote}&rdquo;{r.essential && <span className="ml-1.5 font-mono text-[10px] text-amber-glow">REQUIRED</span>}</span>
                <span className="text-graphite">{r.skill_name ?? '—'}{r.skill && <span className="font-mono"> · you {r.claimed ?? '—'} / needs {r.required_level ?? cov.default_level}</span>}</span>
                <span className={STATUS[r.status][1]}>{STATUS[r.status][0]}</span>
                <span className="md:col-span-3"><ReportProblem kinds={['wrong_skill_mapping', 'unsupported_claim']} targetType="requirement" targetId={r.quote.slice(0, 120)} page="goal" /></span>
              </li>
            ))}
          </ul>
          {cov.not_stated > 0 && <Link to="/roles" className="text-[13px]">Answer the open skill questions on Roles →</Link>}
        </section>
      )}

      {result?.stepping_stones && result.stepping_stones.length > 0 && (
        <section className="card-light flex flex-col gap-3 px-6 py-5">
          <h2 className="h2">Roles that share this goal&rsquo;s skills</h2>
          <p className="m-0 text-xs text-graphite">Verified GBS finance roles whose requirements overlap the posting: a possible step on the way, or an alternative. Your fit is the same calculation as on Roles. You keep your goal; this is a comparison, not a replacement.</p>
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(240px,1fr))]">
            {result.stepping_stones.map((s) => (
              <div key={s.role_id} className="flex flex-col gap-1 rounded-lg border border-mist p-3 text-[13px]">
                <span className="font-semibold">{s.title}</span>
                <span className="font-mono text-xs">fit {Math.round(s.fit)} / 100{s.longer_route ? ' · longer route' : ''}</span>
                <span className="text-xs text-graphite">Shares {s.overlap}: {s.shared.join(', ')}</span>
                {s.shared_courses.length > 0 && (
                  <span className="text-xs">Learning that serves both: {s.shared_courses.map((c, i) => <span key={c.id}>{i > 0 && ', '}<a href={c.url} target="_blank" rel="noreferrer">{c.title}</a></span>)}</span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
