import { useCallback, useState } from 'react'
import type { RoleCard } from '../types'
import { levelText } from './journey'
import { Windows } from './Windows'

// Live job-post searches for a role title on portals whose search URL was checked in a browser on
// 2026-10-24 (each opened real postings for the title). LinkedIn needs sign-in and Hiredly ignored
// the search term, so they are left out. Qart does not read, rank, store or apply to postings.
export function jobSearches(title: string) {
  const plain = title.replace(/\s*\([^)]*\)/g, '').trim()
  const slug = encodeURIComponent(plain.toLowerCase().replace(/\s+/g, '-'))
  const words = encodeURIComponent(plain).replace(/%20/g, '+')
  return [
    { label: 'JobStreet · all Malaysia', url: `https://my.jobstreet.com/${slug}-jobs`, hint: `Search Malaysia for “${plain}”` },
    { label: 'JobStreet · Kuala Lumpur', url: `https://my.jobstreet.com/${slug}-jobs/in-Kuala-Lumpur`, hint: `Search Kuala Lumpur for “${plain}”` },
    { label: 'Indeed Malaysia', url: `https://malaysia.indeed.com/jobs?q=${words}&l=Malaysia`, hint: `Search Malaysia for “${plain}”` },
    { label: 'MYFutureJobs (government portal)', url: 'https://candidates.myfuturejobs.gov.my/search-jobs', hint: `type “${plain}” there` },
  ]
}

export function Openings({ title }: { title: string }) {
  return (
    <p className="m-0 text-[13px] text-graphite">
      See openings:{' '}
      {jobSearches(title).map((s, i) => (
        <span key={s.label}>
          {i > 0 && ' · '}
          <a href={s.url} target="_blank" rel="noreferrer" className="font-medium text-violet">{s.label} ↗</a>
        </span>
      ))}
      . External sites; Qart does not check these openings or apply for you.
    </p>
  )
}

// A button that opens a temporary window with live job-post searches for one role.
export function JobPosts({ title, label = 'See job posts', className = 'btn' }: { title: string; label?: string; className?: string }) {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  return (
    <>
      <button type="button" className={className} onClick={() => setOpen(true)}>{label}</button>
      {open && (
        <Windows
          title={`Job posts · ${title}`}
          onClose={close}
          panes={[
            {
              key: 'posts',
              title: 'Live job posts for this role',
              hint: 'External searches, checked 24 Oct 2026. Results may vary or be empty; no vacancy is guaranteed.',
              body: (
                <div className="flex flex-col gap-3">
                  <ul className="m-0 flex list-none flex-col p-0">
                    {jobSearches(title).map((s) => (
                      <li key={s.label} className="border-b border-line py-2.5 last:border-0">
                        <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-[14px] font-medium text-void">{s.label} ↗</a>
                        <span className="block text-[12px] text-graphite">{s.hint}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="m-0 text-[11px] text-graphite">
                    Qart links to the job boards and does not copy, rank or check individual postings (recruitment integrations are outside this project). Check each employer&rsquo;s own page before you apply.
                  </p>
                </div>
              ),
            },
          ]}
        />
      )}
    </>
  )
}

// Two roles side by side on the same measures; the person picks which two.
export function CompareRoles({ roles }: { roles: RoleCard[] }) {
  const [a, setA] = useState(roles[0]?.role_id ?? '')
  const [b, setB] = useState(roles[1]?.role_id ?? '')
  const left = roles.find((r) => r.role_id === a)
  const right = roles.find((r) => r.role_id === b)
  if (!left || !right) return null
  const skills = [...new Map([...left.requirements, ...right.requirements].map((r) => [r.skill, r.skill_name])).entries()]
  const need = (role: RoleCard, skill: string) => role.requirements.find((r) => r.skill === skill)
  const rows: [string, (r: RoleCard) => string][] = [
    ['Fit now', (r) => `${Math.round(r.fit)} / 100`],
    ['If unstated skills are strong', (r) => `up to ${Math.round(r.fit_range.high)}`],
    ['Essentials', (r) => (r.meters.essentials_ready ? 'all met' : `${r.meters.essentials_below.length} below · ${r.meters.essentials_unstated.length} not stated`)],
    ['Learning to close the gap', (r) => `${r.effort_hours} h · about ${r.effort_weeks} weeks`],
    ['TalentCorp impact', (r) => r.impact],
    ['Route from your role', (r) => (r.listed_transition ? 'listed by TalentCorp' : '—')],
  ]
  const select = (value: string, onChange: (v: string) => void) => (
    <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full rounded-md border border-hairline px-2 py-1.5 text-[13px]">
      {roles.map((r) => <option key={r.role_id} value={r.role_id}>{r.title}</option>)}
    </select>
  )
  return (
    <details className="card-light px-6 py-4">
      <summary className="h2 cursor-pointer">Compare two roles side by side</summary>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[520px] border-collapse text-[13px]">
          <thead>
            <tr>
              <th className="w-[34%] py-1.5 pr-2 text-left font-normal" />
              <th className="px-2 py-1.5 text-left font-normal">{select(a, setA)}</th>
              <th className="py-1.5 pl-2 text-left font-normal">{select(b, setB)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label} className="border-t border-mist">
                <td className="py-1.5 pr-2 text-graphite">{label}</td>
                <td className="px-2 py-1.5 font-mono">{value(left)}</td>
                <td className="py-1.5 pl-2 font-mono">{value(right)}</td>
              </tr>
            ))}
            {skills.map(([skill, name]) => {
              const [l, r] = [need(left, skill), need(right, skill)]
              const cell = (x: typeof l) => (x ? `you ${levelText(x.claimed)} / needs ${levelText(x.required)}${x.essential ? ' · essential' : ''}` : 'not needed')
              return (
                <tr key={skill} className="border-t border-mist text-xs">
                  <td className="py-1 pr-2">{name}</td>
                  <td className={`px-2 py-1 font-mono ${l ? '' : 'text-ash'}`}>{cell(l)}</td>
                  <td className={`py-1 pl-2 font-mono ${r ? '' : 'text-ash'}`}>{cell(r)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="m-0 mt-2 text-xs text-graphite">Same calculation as each role&rsquo;s card. Skills only one role needs are marked &ldquo;not needed&rdquo; for the other.</p>
    </details>
  )
}
