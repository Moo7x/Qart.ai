# Job-board signal (`src/jobs/`, `src/signals/trends.py`)

## 1. What it does
Every day it reads the open jobs on the public job boards of 28 companies, which use Greenhouse, Lever or Ashby. It turns them into dated trends: the share of open postings that mention AI, by region (Malaysia, Singapore, Malaysia + Singapore, APAC, remote, all), the skills postings mention most, and the AI share by type of work.

## 2. Why it exists
The Indeed AI Tracker has no Malaysia or Singapore data. The job boards give real, dated postings in Malaysia and Singapore. The brief requires an updatable, dated, real trend source.

## 3. How it works
- **Fetch** (`sources.py`): one fetcher per system, with a shared, polite HTTP helper (`src/signals/http.py`: timeout, 1 s pause, retries only for timeouts, 429 and 5xx). Everything is normalised to one `Posting` schema.
- **Store** (`store.py`): raw responses are saved per day, and postings go into SQLite, deduplicated by source + job ID. `first_seen` is kept and `last_seen` moves each run. The boards list only what's open today, so this is how history is built.
- **Tag** (`tagging.py`), only after removing each company's boilerplate (any 8-word run in 30% or more of its postings):
  - region from the location text and the boards' remote fields;
  - role family from the job title, using declared keyword rules;
  - "mentions AI" from declared terms, with AI, ML and LLM matched in capitals only;
  - skills from the same patterns the Skills Radar uses.
- **Measure** (`metrics.py`): a posting counts in a week or month when it was seen then. Shares from fewer than 20 postings are reported as insufficient.
- **Serve** (`trends.py`): `load_ai_trend` is the one function behind the AI trend chart. It uses job-board data for a region once there are 4 such weeks. Until then it shows the Indeed tracker, plus today's job-board figure and when it will switch.

## 4. Where in the code
- `catalogue/ats_companies.json` and `catalogue/ats_config.json`
- `src/jobs/{config,sources,tagging,store,metrics,pipeline}.py`
- `src/signals/trends.py` and `src/api_signals.py` (`/ai-trend`, `/hiring-now`)
- `web/src/components/{MarketPulse,HiringNow}.tsx`
- `scripts/fetch_jobs.py`
- `.github/workflows/refresh-jobs.yml`
- tests: `tests/test_jobs_*.py` and `tests/test_signals_trends.py`, all on recorded responses with no network.

## 5. Example: first run, 2026-10-23
- 28 boards, 7,797 open jobs.
- Malaysia + Singapore: 520 postings, 39.6% mention AI.
- APAC: 1,889 postings, 43.6%.
- Python is mentioned in 16.7% of Malaysia + Singapore postings, SQL 15.2%, AI agents 8.5%.
- Within Malaysia + Singapore, 93% of ML/AI roles mention AI, versus 39% of finance roles and 0% of admin roles.

## 6. Limits
- Only companies that use these three systems, biased toward tech.
- No history before the first snapshot.
- A failing board makes its jobs look closed for that day.
- Keyword matching, not human reading.
- Not used for the ranking's momentum until there's about 12 months of history.

## 7. Questions and answers
- *Why not LinkedIn or JobStreet?* Their terms forbid automated access. These three are public, documented APIs that need no key.
- *Why remove boilerplate?* On the first run, company "About us" text mentioning AI made 19 of 28 companies show 100% AI. Removing repeated text measures the jobs, not the branding.
- *Is this the Malaysian job market?* No. It's a sample of companies hiring in Malaysia and Singapore, and every view says so.
