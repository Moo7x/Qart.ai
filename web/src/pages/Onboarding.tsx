import { useEffect, useRef, useState } from 'react'
import { useT } from '../i18n'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { getJSON, sendJSON, uploadFile, useApi } from '../api'
import { Activity, RunLog, type LogLine } from '../components/Activity'
import { LevelPicker } from '../components/journey'
import { useJourney } from '../state'
import type { Extraction, MatchesResponse, PackInfo, PathwayResponse, ProfileData, SignalsResponse, Situation, SkillClaim, SkillKind, Stage } from '../types'

const STEPS = ['', 'Your situation', 'Your CV', 'Your work today', 'Your skills', 'Time and budget', 'What matters to you']
const LAST_QUESTION = 6
const BUILDING = 7
const HOURS = [2, 4, 6, 10]
type SkillSuggestions = { hits: { skill: string; name: string; score: number }[]; engine: string; note: string; stages?: Stage[] }
const SITUATIONS: { id: Situation; title: string; body: string }[] = [
  { id: 'working', title: 'I work in finance now', body: 'See how AI is changing your tasks, and routes to nearby roles.' },
  { id: 'student', title: "I'm studying or just graduated", body: 'Entry roles that fit you and the skills to build first.' },
  { id: 'switcher', title: 'I want to move into finance', body: 'Which of your skills carry over, and a plan to switch.' },
]
const INTERESTS: { id: SkillKind; label: string }[] = [
  { id: 'data_digital', label: 'Working with data and systems' },
  { id: 'finance_core', label: 'Accounting and finance work' },
  { id: 'green', label: 'Sustainability (ESG)' },
  { id: 'business', label: 'Improving processes and working with people' },
]
const SDGS = [
  { id: '4', label: '4 · Quality education', colour: '#C5192D' },
  { id: '8', label: '8 · Decent work', colour: '#A21942' },
  { id: '12', label: '12 · Responsible production', colour: '#BF8B2E' },
]

function chip(on: boolean): string {
  return `min-h-[40px] cursor-pointer rounded-full px-3.5 text-sm ${on ? 'border border-violet bg-violet-soft text-[#3b1fc2]' : 'border border-hairline bg-white text-void'}`
}

export function Onboarding() {
  const { t } = useT()
  const navigate = useNavigate()
  const { profileId, setProfileId } = useJourney()
  const [searchParams] = useSearchParams()
  const editing = searchParams.get('edit') === '1' && profileId !== null
  const existing = useApi<{ profile: ProfileData }>(editing ? `/api/profiles/${profileId}` : null)
  const hydrated = useRef(false)
  const pack = useApi<PackInfo>('/api/pack')
  const signals = useApi<SignalsResponse>('/api/signals')
  const [step, setStep] = useState(editing ? 1 : 0)
  const [situation, setSituation] = useState<Situation>('working')
  const [stages, setStages] = useState<Stage[] | undefined>(undefined)
  const [extraction, setExtraction] = useState<Extraction | null>(null)
  const [role, setRole] = useState('other')
  const [years, setYears] = useState('')
  const [tasks, setTasks] = useState('')
  const [skills, setSkills] = useState<Record<string, SkillClaim>>({})
  const [addQuery, setAddQuery] = useState('')
  const [hours, setHours] = useState(6)
  const [budget, setBudget] = useState<ProfileData['budget']>('free')
  const [interests, setInterests] = useState<SkillKind[]>([])
  const [sdgs, setSdgs] = useState<string[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [built, setBuilt] = useState<MatchesResponse | null>(null)
  const [log, setLog] = useState<LogLine[]>([])
  const [suggestions, setSuggestions] = useState<SkillSuggestions | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  useEffect(() => {
    if (!editing || !existing.data || hydrated.current) return
    const p = existing.data.profile
    setSituation(p.situation); setRole(p.current_role); setYears(p.years_experience === null ? '' : String(p.years_experience))
    setSkills(p.skills); setHours(p.weekly_hours); setBudget(p.budget); setInterests(p.interests); setSdgs(p.sdg_priorities)
    hydrated.current = true
  }, [editing, existing.data])

  const skillName = (id: string) => pack.data?.skills.find((s) => s.id === id)?.name ?? id
  const go = (n: number) => setStep(Math.max(0, Math.min(BUILDING, n)))

  function applyExtraction(result: Extraction) {
    setExtraction(result)
    setStages(result.stages)
    if (result.current_role !== 'other') setRole(result.current_role)
    if (result.years_experience !== null) setYears(String(result.years_experience))
    if (result.interests.length) setInterests(result.interests)
    const found: Record<string, SkillClaim> = {}
    for (const s of result.skills) {
      found[s.skill] = { level: s.level, evidence: s.evidence, source: s.level === null ? 'keyword' : 'cv' }
    }
    setSkills(found)
    go(3)
  }

  async function run(label: string, action: () => Promise<void>) {
    setStages(undefined)
    setBusy(label)
    setError(null)
    try {
      await action()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(null)
    }
  }

  const pickSample = (id: string) =>
    run('Reading the sample CV…', async () => {
      const sample = await getJSON<{ text: string }>(`/api/samples/${id}`)
      applyExtraction(await sendJSON<Extraction>('/api/intake/parse', { body: { text: sample.text } }))
    })

  const pickFile = (file: File) =>
    run('Reading your CV…', async () => applyExtraction(await uploadFile<Extraction>('/api/intake/upload', file)))

  const findFromTasks = () =>
    run('Matching your tasks to skills…', async () => {
      setSuggestions(null)
      setSelected([])
      const result = await sendJSON<SkillSuggestions>('/api/skills/search', { body: { text: tasks } })
      setSuggestions(result)
      setStages(result.stages)
    })

  function setLevel(id: string, level: number) {
    setSkills((prev) => {
      return { ...prev, [id]: { ...(prev[id] ?? { evidence: '', source: 'self' }), level, source: prev[id]?.source === 'cv' ? 'cv' : 'self' } }
    })
  }

  const finish = () =>
    run('Building your picture…', async () => {
      go(BUILDING)
      const profile: ProfileData = {
        situation,
        current_role: situation === 'student' ? 'other' : role,
        years_experience: years === '' ? null : Number(years),
        weekly_hours: hours,
        budget,
        interests,
        sdg_priorities: sdgs,
        skills,
        extraction_engine: extraction?.engine ?? existing.data?.profile.extraction_engine ?? 'none',
      }
      setBuilt(null)
      setLog([])
      // Each line is one real request, shown when it starts and ticked off when it returns.
      async function logged<T>(label: string, work: () => Promise<T>, found: (result: T) => string): Promise<T> {
        const startedAt = Date.now()
        setLog((lines) => [...lines, { label, status: 'running', startedAt }])
        const finishLine = (patch: Partial<LogLine>) =>
          setLog((lines) => lines.map((line, i) => (i === lines.length - 1 ? { ...line, ...patch, seconds: (Date.now() - startedAt) / 1000 } : line)))
        try {
          const result = await work()
          finishLine({ status: 'done', detail: found(result) })
          return result
        } catch (reason) {
          finishLine({ status: 'failed', detail: reason instanceof Error ? reason.message : String(reason) })
          throw reason
        }
      }
      let id = profileId
      await logged(
        editing ? 'Update your saved profile' : 'Save your profile',
        async () => {
          if (editing && id) await sendJSON(`/api/profiles/${id}`, { method: 'PUT', body: profile })
          else {
            id = (await sendJSON<{ id: string }>('/api/profiles', { body: profile })).id
            setProfileId(id)
          }
        },
        () => { const n = Object.keys(skills).length; return `${n} skill claim${n === 1 ? "" : "s"} saved; names and contact details are never stored` },
      )
      const moderate = await logged(
        'Score the destination roles · moderate AI adoption',
        () => getJSON<MatchesResponse>(`/api/profiles/${id}/matches?scenario=moderate`),
        (m) => `${m.roles.length} roles scored · best fit: ${m.roles[0]?.title ?? 'none'} · AI-use evidence for ${m.evidence.occupations} occupations, ${m.evidence.period}`,
      )
      await logged(
        'Re-score them · fast AI adoption',
        () => getJSON<MatchesResponse>(`/api/profiles/${id}/matches?scenario=fast`),
        (m) => `best fit under fast adoption: ${m.roles[0]?.title ?? 'none'}`,
      )
      const top = moderate.roles[0]
      if (top) {
        await logged(
          `Plan free courses towards ${top.title}`,
          () => getJSON<PathwayResponse>(`/api/profiles/${id}/pathway?scenario=moderate&role_id=${top.role_id}`),
          (p) => `${p.steps.length} verified courses · ${p.total_hours} h · about ${p.weeks} weeks at ${hours} h a week`,
        )
      }
      await logged(
        "Load today's market evidence",
        () => getJSON<SignalsResponse>('/api/signals'),
        (r) => `${r.signals.length} signals from ${r.observations} stored observations, each with its source and date`,
      )
      setBuilt(moderate)
    })

  const addable = (pack.data?.skills ?? []).filter((s) => !(s.id in skills) && addQuery.length > 1 && s.name.toLowerCase().includes(addQuery.toLowerCase())).slice(0, 6)
  const evidence = signals.data?.signals.filter((s) => s.id === 'dosm_jmi_accountants_and_auditors' || s.id === 'dosm_share_clerical') ?? []

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-fog">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(120%_100%_at_50%_0%,rgba(108,71,255,0)_10%,rgba(255,249,99,0.12)_34%,rgba(98,72,246,0.18)_67%,rgba(98,72,246,0)_95%)]" />
      <header className="relative flex items-center justify-between px-8 py-5">
        <Link to="/" className="flex items-center gap-2.5 text-void no-underline">
          <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
            <rect width="26" height="26" rx="6" fill="#131316" />
            <circle cx="12" cy="12" r="6" fill="none" stroke="#ffffff" strokeWidth="2.2" />
            <path d="M16 16l4.5 4.5" stroke="#6c47ff" strokeWidth="2.4" strokeLinecap="round" />
          </svg>
          <span className="text-[17px] font-semibold tracking-tight">Qart.ai</span>
        </Link>
        <Link to="/live" className="text-sm text-graphite">{t('Browse public evidence')}</Link>
      </header>

      <main className="relative mx-auto flex max-w-[640px] flex-col gap-7 px-6 pb-16 pt-8">
        {editing && existing.loading && <p role="status">Loading your saved answers…</p>}
        {editing && existing.error && <p role="alert">Could not load your saved answers. <button type="button" className="btn" onClick={existing.reload}>Retry</button></p>}
        {step >= 1 && step <= LAST_QUESTION && (
          <div className="flex flex-col gap-2.5">
            <div role="progressbar" aria-valuemin={1} aria-valuemax={LAST_QUESTION} aria-valuenow={step} aria-label="Onboarding progress" className="grid grid-cols-6 gap-1.5">
              {STEPS.slice(1).map((name, i) => (
                <span key={name} className={`h-1 rounded-full ${i + 1 <= step ? 'bg-violet' : 'bg-hairline'}`} />
              ))}
            </div>
            <span className="font-mono text-xs text-graphite">
              Step {step} of {LAST_QUESTION} · {t(STEPS[step])}
            </span>
          </div>
        )}

        {step === 0 && (
          <section className="flex flex-col gap-6 pt-6">
            <span className="eyebrow">{t('GBS finance & accounting · Malaysia')}</span>
            <h1 className="m-0 text-[56px] font-semibold leading-[1.02] tracking-[-0.035em]">{t('Where is your finance career going as AI changes the work?')}</h1>
            <p className="m-0 max-w-[560px] text-lg text-graphite">
              Qart.ai reads Malaysia's public labour and job-ad data, shows which of your skills are gaining weight, which roles fit you, and a free learning plan. Every number links to its source.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" className="btn btn-v min-h-[44px] text-[15px]" onClick={() => go(1)}>{t('Start · about 3 minutes')}</button>
              {profileId && <Link to="/overview" className="btn">Continue with my saved profile</Link>}
              <span className="text-[13px] text-graphite">{t('Skip any question. The demo uses synthetic CVs only.')}</span>
            </div>
            {evidence.length > 0 && (
              <div className="card-dark flex flex-col gap-2.5 px-5 py-4">
                <span className="font-mono text-[11px] tracking-widest text-cyan">LATEST EVIDENCE IN THE PIPELINE</span>
                {evidence.map((s) => (
                  <div key={s.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 font-mono text-[13px]">
                    <span>{s.title}</span>
                    <span className="text-cyan">{s.points.at(-1)?.value.toFixed(2)}%</span>
                    <span className="text-stone">{s.sources[0]?.name} · {s.points.at(-1)?.period}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {step === 1 && (
          <section className="flex flex-col gap-4">
            <h1 className="h1">{t('Which describes you?')}</h1>
            <p className="m-0 text-graphite">{t('This changes what you see first.')}</p>
            <div role="radiogroup" aria-label="Your situation" className="flex flex-col gap-2.5">
              {SITUATIONS.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  role="radio"
                  aria-checked={situation === s.id}
                  onClick={() => setSituation(s.id)}
                  className={`flex w-full cursor-pointer items-center justify-between gap-4 rounded-lg bg-white px-[18px] py-4 text-left ${situation === s.id ? 'border-[1.5px] border-violet shadow-[0_0_0_3px_rgba(108,71,255,0.12)]' : 'border border-hairline'}`}
                >
                  <span>
                    <span className="block font-semibold">{t(s.title)}</span>
                    <span className="block text-sm text-graphite">{t(s.body)}</span>
                  </span>
                  <span aria-hidden="true" className={`h-[18px] w-[18px] flex-none rounded-full ${situation === s.id ? 'border-[5px] border-violet' : 'border-[1.5px] border-stone'}`} />
                </button>
              ))}
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="flex flex-col gap-4">
            <h1 className="h1">{t('Add your CV')}</h1>
            <p className="m-0 text-graphite">{t('We pre-fill the next questions from it. Prefer not to? Skip and answer them yourself.')}</p>
            <label className="relative flex min-h-[160px] cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border-[1.5px] border-dashed border-stone bg-white p-4 text-center">
              <span className="font-semibold">{t('Drop a PDF, DOCX or text file')}</span>
              <span className="text-[13px] text-graphite">or click to browse</span>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                aria-label="Upload CV"
                className="absolute inset-0 cursor-pointer opacity-0"
                onChange={(e) => e.target.files?.[0] && pickFile(e.target.files[0])}
              />
            </label>
            <div className="flex flex-col gap-2">
              <span className="cap">{t('Or try a synthetic sample')}</span>
              <div className="flex flex-wrap gap-2">
                {(pack.data?.samples ?? []).map((s) => (
                  <button key={s.id} type="button" className={chip(false)} onClick={() => pickSample(s.id)}>
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
            <p className="m-0 text-[13px] text-graphite">{t('Names, IC numbers, phone numbers and emails are removed before anything reads the CV. The CV text itself is not stored.')}</p>
          </section>
        )}

        {step === 3 && (
          <section className="flex flex-col gap-4">
            <h1 className="h1">{situation === 'student' ? 'What have you studied and done?' : 'What do you do today?'}</h1>
            {extraction && <span className="font-mono text-[11px] text-violet">READ FROM YOUR CV BY {extraction.engine.toUpperCase()} · EDIT IF WRONG</span>}
            {situation !== 'student' && (
              <label className="flex flex-col gap-1.5 text-[13px] font-medium">
                Current or last role
                <select value={role} onChange={(e) => setRole(e.target.value)} className="min-h-[44px] rounded-md border border-hairline bg-fog px-3 text-[15px]">
                  <option value="other">{t('None of these')}</option>
                  {(pack.data?.current_roles ?? []).map((r) => (
                    <option key={r.id} value={r.id}>{r.title}</option>
                  ))}
                </select>
              </label>
            )}
            {situation !== 'student' && <div className="flex flex-wrap gap-2" aria-label="Role examples">
              {pack.data?.current_roles.slice(0,4).map((r) => <button key={r.id} type="button" className={chip(role === r.id)} onClick={() => setRole(r.id)}>{r.title}</button>)}
            </div>}
            <label className="flex flex-col gap-1.5 text-[13px] font-medium">
              Years of work experience
              <input type="number" min={0} max={60} value={years} onChange={(e) => setYears(e.target.value)} className="min-h-[44px] rounded-md border border-hairline bg-fog px-3 text-[15px]" />
            </label>
            <label className="flex flex-col gap-1.5 text-[13px] font-medium">
              Main tasks, in your own words
              <textarea value={tasks} onChange={(e) => { setTasks(e.target.value); setSuggestions(null); setSelected([]) }} rows={3} placeholder="e.g. applying customer receipts, month-end reports" className="rounded-md border border-hairline bg-fog px-3 py-2 text-[15px]" />
            </label>
            <button type="button" className="btn self-start" disabled={busy !== null || tasks.trim().length < 3} onClick={findFromTasks}>
              Find the matching skills
            </button>
            <div className="flex flex-col gap-2" aria-label="Task examples">
              <span className="cap">Or start from an O*NET task and edit it</span>
              {pack.data?.task_examples.map((example) => <button key={example.text} type="button" className="btn justify-start py-2 text-left text-xs" onClick={() => { setTasks(example.text); setSuggestions(null) }}>{example.text}</button>)}
              {pack.data?.task_examples[0] && <a className="text-xs text-graphite" href={pack.data.task_examples[0].url} target="_blank" rel="noreferrer">Task examples: {pack.data.task_examples[0].source}</a>}
            </div>
            {suggestions && <section aria-label="Suggested skills" className="border-y border-hairline py-4">
              <p className="m-0 text-sm font-medium">{suggestions.hits.length ? 'Choose the skills that describe your work' : 'No matching skills found. Try a specific task, or add skills on the next step.'}</p>
              <p className="text-xs text-graphite">Matched by {suggestions.engine}. {suggestions.note}</p>
              {suggestions.hits.map((hit) => <label key={hit.skill} className="flex min-h-11 items-center gap-3 text-sm">
                <input type="checkbox" checked={selected.includes(hit.skill)} onChange={(e) => setSelected((prev) => e.target.checked ? [...prev, hit.skill] : prev.filter((id) => id !== hit.skill))} />
                {hit.name}{hit.skill in skills && ' · already in your profile'}
              </label>)}
              {suggestions.hits.length > 0 && <button type="button" className="btn" disabled={!selected.length} onClick={() => {
                setSkills((prev) => {
                  const next = { ...prev }
                  for (const id of selected) next[id] ??= { level: null, evidence: '', source: 'self' }
                  return next
                })
                setSuggestions(null)
                setSelected([])
              }}>Add selected skills</button>}
            </section>}
          </section>
        )}

        {step === 4 && (
          <section className="flex flex-col gap-4">
            <h1 className="h1">{t('Check your skills')}</h1>
            <p className="m-0 text-graphite">
              Rate each skill from 1 (none) to 5 (expert). A level is your own claim, not a test.
            </p>
            {extraction && (
              <p className="m-0 font-mono text-[11px] text-graphite">
                {extraction.engine} · {Object.entries(extraction.removed).map(([k, v]) => `${v} ${k} removed`).join(', ') || 'no personal details found'}
                {extraction.rejected.length > 0 ? ` · ${extraction.rejected.length} claim(s) dropped: their quote was not in the CV` : ''}
                {extraction.note ? ` · ${extraction.note}` : ''}
              </p>
            )}
            <div className="card-light">
              {Object.keys(skills).length === 0 && <p className="m-0 px-4 py-4 text-sm text-graphite">{t('No skills yet. Add the ones you have below.')}</p>}
              {Object.entries(skills).map(([id, claim]) => (
                <div key={id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-mist px-4 py-3">
                  <span className="min-w-0 flex-[1_1_260px]">
                    <span className="block font-medium">{skillName(id)}</span>
                    <span className="block text-xs text-graphite">
                      {claim.source === 'cv' ? `CV: “${claim.evidence}”` : claim.source === 'keyword' ? 'Found by keyword · set your level' : 'You set this'}
                    </span>
                  </span>
                  <span className="flex flex-col items-end gap-1">
                    <LevelPicker level={claim.level} label={`Your level in ${skillName(id)}`} onChange={(level) => setLevel(id, level)} />
                    {claim.level === null && <span className="text-[11px] text-graphite">Not rated yet</span>}
                  </span>
                </div>
              ))}
            </div>
            <label className="flex flex-col gap-1.5 text-[13px] font-medium">
              Add a skill
              <input value={addQuery} onChange={(e) => setAddQuery(e.target.value)} placeholder="e.g. SQL, budget, ESG" className="min-h-[44px] rounded-md border border-hairline bg-fog px-3 text-[15px]" />
            </label>
            <div className="flex flex-wrap gap-2">
              {addable.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className="min-h-[36px] cursor-pointer rounded-full border border-dashed border-stone bg-transparent px-3 text-sm"
                  onClick={() => {
                    setSkills((prev) => ({ ...prev, [s.id]: { level: 1, evidence: '', source: 'self' } }))
                    setAddQuery('')
                  }}
                >
                  + {s.name}
                </button>
              ))}
            </div>
          </section>
        )}

        {step === 5 && (
          <section className="flex flex-col gap-5">
            <h1 className="h1">{t('How much time and money can you put into learning?')}</h1>
            <div role="radiogroup" aria-label="Hours per week" className="flex flex-col gap-2.5">
              <span className="text-[13px] font-medium">{t('Hours per week')}</span>
              <div className="flex flex-wrap gap-2">
                {HOURS.map((h) => (
                  <button key={h} type="button" role="radio" aria-checked={hours === h} className={chip(hours === h)} onClick={() => setHours(h)}>{h} h</button>
                ))}
              </div>
            </div>
            <div role="radiogroup" aria-label="Budget" className="flex flex-col gap-2.5">
              <span className="text-[13px] font-medium">{t('Budget')}</span>
              <div className="flex flex-wrap gap-2">
                <button type="button" role="radio" aria-checked={budget === 'free'} className={chip(budget === 'free')} onClick={() => setBudget('free')}>{t('Free only')}</button>
                <button type="button" role="radio" aria-checked={budget === 'free_hrd'} className={chip(budget === 'free_hrd')} onClick={() => setBudget('free_hrd')}>{t('Free + HRD Corp-claimable')}</button>
                <button type="button" role="radio" aria-checked={budget === 'up_to_500'} className={chip(budget === 'up_to_500')} onClick={() => setBudget('up_to_500')}>{t('Up to RM 500')}</button>
              </div>
              <span className="text-xs text-graphite">{t('Every course listed today is free. HRD Corp-claimable programmes are shown only once the official listing confirms them.')}</span>
            </div>
          </section>
        )}

        {step === 6 && (
          <section className="flex flex-col gap-5">
            <h1 className="h1">{t('What matters to you in your next role?')}</h1>
            <p className="m-0 text-graphite">{t('Used only to order roles that fit you almost equally well. It never changes a fit score.')}</p>
            <div className="flex flex-wrap gap-2">
              {INTERESTS.map((i) => {
                const on = interests.includes(i.id)
                return (
                  <button key={i.id} type="button" aria-pressed={on} className={chip(on)} onClick={() => setInterests(on ? interests.filter((x) => x !== i.id) : [...interests, i.id])}>
                    {t(i.label)}<span className="ml-1 text-xs">({pack.data?.skills.filter((s) => s.kind === i.id).slice(0,2).map((s) => s.name).join(', ')})</span>
                  </button>
                )
              })}
            </div>
            <div className="flex flex-col gap-2.5">
              <span className="text-[13px] font-medium">{t('Sustainable Development Goals you care about (optional)')}</span>
              <div className="flex flex-wrap gap-2">
                {SDGS.map((g) => {
                  const on = sdgs.includes(g.id)
                  return (
                    <button key={g.id} type="button" aria-pressed={on} onClick={() => setSdgs(on ? sdgs.filter((x) => x !== g.id) : [...sdgs, g.id])}
                      className="min-h-[40px] cursor-pointer rounded-full px-3.5 text-sm"
                      style={on ? { background: g.colour, color: '#fff', border: 0 } : { background: '#fff', color: g.colour, border: `1px solid ${g.colour}` }}>
                      {g.label}
                    </button>
                  )
                })}
              </div>
            </div>
          </section>
        )}

        {step === BUILDING && (
          <section className="flex flex-col gap-5 pt-3">
            <span className="eyebrow">{built ? 'Ready' : 'Almost there'}</span>
            <h1 className="m-0 text-[40px] font-semibold leading-[1.1] tracking-[-0.035em]">{t("Building your picture from today's evidence")}</h1>
            <RunLog title="Build log" lines={log} total={5} />
            {log.some((line) => line.status === 'failed') && (
              <div className="flex flex-wrap items-center gap-3">
                <button type="button" className="btn" disabled={busy !== null} onClick={finish}>Try again</button>
                <span className="text-[13px] text-graphite">Your answers are kept.</span>
              </div>
            )}
            {built && (
              <div className="flex flex-wrap items-center gap-3">
                <button type="button" className="btn btn-v min-h-[44px]" onClick={() => navigate('/overview')}>{t('Open my overview →')}</button>
              </div>
            )}
          </section>
        )}

        <Activity running={busy !== null} label={t(busy ?? '')} stages={stages} />
        {error && <p role="alert" className="m-0 text-sm text-weak">{error}</p>}

        {step >= 1 && step <= LAST_QUESTION && (
          <div className="flex items-center justify-between gap-3 border-t border-hairline pt-5">
            <button type="button" className="min-h-[44px] cursor-pointer border-0 bg-transparent px-3 text-[15px] text-graphite" onClick={() => go(step - 1)}>← Back</button>
            <span className="flex gap-2">
              {step < LAST_QUESTION && (
                <button type="button" className="min-h-[44px] cursor-pointer border-0 bg-transparent px-3 text-[15px] text-graphite" onClick={() => go(step + 1)}>{t('Skip')}</button>
              )}
              <button type="button" className="btn btn-v min-h-[44px]" disabled={busy !== null || (editing && !hydrated.current)} onClick={() => (step === LAST_QUESTION ? finish() : go(step + 1))}>
                {step === LAST_QUESTION ? 'Build my picture' : 'Continue'}
              </button>
            </span>
          </div>
        )}
      </main>
    </div>
  )
}
