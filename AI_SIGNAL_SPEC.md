# AI Skills Signal — Build Spec for Qart.ai

> Feature spec for Claude Code. Read the whole file before writing code.
> **First step:** inspect the existing repo (stack, folder layout, how the CV upload and skill extraction work) and adapt the paths and libraries below to fit it. Don't introduce a new framework if one already exists. If something here conflicts with the repo, follow the repo and note the deviation in the PR/summary.

---

## 1. Goal

Add a **Future Skills Radar** to Qart.ai that answers one question for the user:

> "Is the market moving toward or away from my skills?"

It uses **real, public, dated data** for the AI and skills trend signal. Every chart shows its source, the latest date in the data, and when it was fetched.

**Hackathon data rule:** CVs and user data in the app are synthetic. The market/AI signal must come from the real public sources below. Don't mix the two, and never send CV content to any external API.

---

## 2. Data sources

### 2.1 Market pulse — Indeed Hiring Lab AI Tracker
- Repo: https://github.com/hiring-lab/ai-tracker
- What it is: share (%) of job postings mentioning AI / GenAI terms, by country, as a 7-day trailing average. The values are daily and the repo is refreshed monthly.
- Licence: CC BY 4.0. **Attribution is required:** "Source: Indeed Hiring Lab".
- Access: CSV files in the repo, fetched via raw.githubusercontent.com. No key needed.
- **TODO for Claude Code:** open the repo, find the actual CSV filename(s) and column names (expect `jobcountry` as an ISO-2 code plus `*_share` columns), and don't hardcode a guessed path.
- Processing: aggregate daily values to a **monthly mean** per country. Keep both the AI and GenAI series if both exist.
- Country handling: check whether `MY` is present. If not, default to `SG` and label the chart clearly (e.g. "Singapore (closest covered market)"). Never label non-Malaysian data as Malaysia.

### 2.2 Skill-level signal — Hacker News "Ask HN: Who is hiring?"
- Monthly threads posted by HN user `whoishiring`. Each **top-level comment** is one job post.
- API (free, no key): Algolia HN Search API
  - Find threads: `GET https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&query=%22who%20is%20hiring%22&hitsPerPage=100` (paginate; keep only titles starting with "Ask HN: Who is hiring?" — exclude "Who wants to be hired?" and "Freelancer?" threads).
  - Fetch a thread with all comments: `GET https://hn.algolia.com/api/v1/items/{story_id}` → use `children` (top level only) as job posts. Strip HTML from `text`.
- Window: last **36 months**.
- Cache raw thread JSON to disk (`data/raw/hn/{yyyy-mm}.json`) so re-runs only fetch new months. Be polite: sequential requests, short sleep, retry with backoff.
- Known bias (must appear in the UI caveat): skewed toward tech startups, mostly US and remote roles. Label it "Tech hiring signal (Hacker News)", not "Malaysian job market".

### 2.3 Optional later: arXiv (research momentum)
- Monthly paper counts per topic via the arXiv API, plotted against hiring mentions. **Out of scope for v1.** Leave a clean extension point only.

---

## 3. Skill matching

- Config file: `config/skills.yaml` (or JSON, whichever the repo prefers).
- Each skill has an id, a display name, a category, and match patterns (aliases):

```yaml
- id: rag
  name: RAG
  category: AI/ML
  patterns: ['\bRAG\b', 'retrieval[- ]augmented']
  case_sensitive_patterns: ['\bRAG\b']
```

- Rules:
  - Use word-boundary regex. Count a post **once per skill** however many times the term appears.
  - Short or ambiguous terms (`R`, `Go`, `C`, `Rust`, `agent`) need specific patterns (`\bGolang\b|\bGo\b(?= developer| engineer|,)`, `AI agents?|agentic`) or must be excluded. Prefer leaving a skill out over producing noisy counts.
  - Write unit tests for the matcher with true positive and false positive examples for every ambiguous skill.
- **Default skill set (~15)**, used when no CV is uploaded and as the comparison baseline: Python, SQL, PyTorch, TensorFlow, LLMs, RAG, LangChain, AI agents, MLOps, Computer vision, NLP, Kubernetes, AWS, TypeScript, React.
- **User skills:** reuse the app's existing CV skill extraction. Map each extracted skill to a config entry. Skills with no config entry are shown as "No market data yet" rather than silently dropped.

---

## 4. Signal computation

All parameters live in config, not in code.

For each skill, per month:
- `mentions` = number of job posts matching the skill
- `total_posts` = number of top-level posts in that month's thread
- `share` = mentions / total_posts

Derived values:
- `index` = share rebased so the first month with enough data = 100
- `ma_short` = 3-month moving average of share
- `ma_long` = 12-month moving average of share
- `change_12m` = % change of `ma_short` versus its value 12 months earlier

Labels (defaults):
| Label | Rule |
|---|---|
| **Rising** | `ma_short > ma_long × 1.10` AND `change_12m > +15%` |
| **Cooling** | `ma_short < ma_long × 0.90` AND `change_12m < −15%` |
| **Stable** | anything else |
| **Insufficient data** | average `mentions` < 5 per month over the last 6 months |

- The insufficient-data check runs first and overrides the other labels.
- Use the words "trend" and "signal" only. Never "prediction" or "forecast".
- Unit test the labelling with small synthetic series (rising, flat, falling, sparse).

---

## 5. Pipeline and snapshots

```
scripts/fetch_signals.py        # or the repo's equivalent language/location
  ├─ fetch_indeed_ai_tracker()  -> data/snapshots/market_pulse.json
  ├─ fetch_hn_threads()         -> data/raw/hn/*.json (cached)
  └─ compute_skill_signals()    -> data/snapshots/skill_signals.json
```

The app **reads snapshots only** and never calls the sources at request time. That keeps the demo working offline.

### Snapshot schema (every snapshot file)

```json
{
  "source": "Indeed Hiring Lab – AI Tracker",
  "source_url": "https://github.com/hiring-lab/ai-tracker",
  "license": "CC BY 4.0",
  "attribution": "Source: Indeed Hiring Lab",
  "data_as_of": "YYYY-MM-DD",
  "fetched_at": "ISO-8601 with timezone",
  "caveats": ["..."],
  "series": [ ... ]
}
```

- `data_as_of` = the **latest date that actually appears in the data**, never the fetch date.
- `skill_signals.json` also holds, per skill: monthly points (`month`, `mentions`, `total_posts`, `share`, `index`, `ma_short`, `ma_long`), plus `label`, `change_12m`, and `latest_sample_size`.
- If a fetch fails, keep the previous snapshot unchanged and log the error. Partial writes are not allowed (write to a temp file, then rename).

### Refresh
- Add a scheduled job: a GitHub Actions workflow running weekly (cron) that runs the script and commits updated snapshots. Or use the repo's existing scheduler if there is one.
- Add a manual run command to the README.

---

## 6. UI

### 6.1 Market Pulse card
- Line chart: monthly AI share of postings, with a country toggle that shows only countries present in the data.
- 2–3 event markers, e.g. "ChatGPT launch, Nov 2022". Keep the list in config.

### 6.2 Skills Radar (main view)
- A table ranking skills by momentum. Columns: skill, label badge (Rising / Stable / Cooling / Insufficient data), 12-month change, a small inline trend line, and the latest month's sample size.
- Highlight the user's CV skills. Show the default set underneath as "Skills to watch".
- Clicking a row opens a **detail chart**: indexed share over time with the 3- and 12-month moving averages.

### 6.3 Link to the reskilling pathway
- Expose a function or endpoint returning `{ user_skills_cooling: [...], rising_skills_not_in_cv: [...] }` so the pathway generator can use it.
- Wire it in only if the pathway module exists and the integration is simple. Otherwise leave a TODO and say so in the summary.

### 6.4 Provenance (required on every chart)
Below each chart, one line in this format:

`Source: <source> (<license>) · data to <data_as_of> · refreshed <fetched_at date> · <link>`

Plus a short caveat line. For the HN chart, mention the US/startup/remote skew and the sample size.

If a snapshot is more than 45 days old, show a visible "Stale data" badge.

Also add a **"Data sources"** page or modal listing every feed, its update frequency, licence and caveats.

### 6.5 Charts
- Use whatever chart library the repo already uses. If there is none and the frontend is React, use Recharts.
- The view must be readable on a phone (~380px wide): the table collapses to cards and the detail chart stays legible.

---

## 7. Build order

1. Inspect the repo and summarise the stack and relevant modules in 5–10 lines.
2. Skill config, matcher, and matcher tests.
3. HN fetch with caching, plus signal computation and tests → `skill_signals.json`.
4. Indeed tracker fetch → `market_pulse.json`.
5. UI: Skills Radar table and detail chart, then the Market Pulse card, then provenance lines and the Data sources page.
6. CV skills hookup and the pathway link (6.3).
7. Scheduled refresh workflow and README section.

After each step, run the tests and confirm before moving on.

---

## 8. Acceptance criteria

- [ ] Running the fetch script from a clean state produces both snapshots with real data and a correct `data_as_of`.
- [ ] Re-running only fetches new HN months (cache works).
- [ ] Every chart shows source, licence, data date, fetch date and link.
- [ ] Indeed attribution is visible wherever that data is shown.
- [ ] The app works with network access disabled, using the snapshots.
- [ ] Matcher and signal-label tests pass.
- [ ] No CV or user data leaves the app.
- [ ] Non-Malaysian data is never labelled as Malaysia.

---

## 9. Out of scope (v1)

- arXiv research layer.
- Paid APIs (Lightcast, Adzuna).
- Google Trends (no official API).
- Any scraping of sites without a public API.
