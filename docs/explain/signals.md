# Future Skills Radar (`src/signals/`)

## 1. What it does
It answers "is the market moving toward or away from my skills?" with real, dated public data:
- how often tech job posts mention each of 20 skills (Hacker News "Who is hiring?", 36 months);
- how often job postings mention AI in 9 countries (Indeed Hiring Lab AI Tracker).

## 2. Why it exists
The brief asks for trend signals, not guesses. The data is real and every chart is dated and sourced. Profiles stay synthetic and never leave the app.

## 3. How it works
- **Fetch** (`scripts/fetch_signals.py` → `pipeline.run`). The script downloads the Indeed CSV, then the HN threads through the Algolia API. HN threads are cached per month in `data/raw/hn/`, and only new months plus the current one are fetched.
- **Write.** It writes two snapshots in the spec schema, atomically. If a source fails, its old snapshot is kept.
- **Match** (`matcher.py`). Word-boundary regexes from `catalogue/signal_config.json`, case-sensitive where needed. A post counts once per skill. Bare R, Go and C are not tracked.
- **Signal** (`compute.py`), per month:
  - share = mentions / posts;
  - index = share rebased to 100 at the first month with enough mentions;
  - 3- and 12-month moving averages, and the 12-month change of the 3-month average.
- **Label:**
  - *insufficient data* if fewer than 5 mentions a month over the last 6 months (checked first);
  - *rising* if the 3-month average is above 1.10 × the 12-month one and the change is above +15 %;
  - *cooling* for the mirror case (below 0.90 × and below −15 %);
  - otherwise *stable*.

  All thresholds are declared in the config, not fitted to data.
- **Serve** (`src/api_signals.py`). The endpoints read the snapshots only, so the app works offline. They add `age_days` and `stale` (data older than 45 days).
- **"Your skills".** Radar skills matching your Profile tools, plus radar skills linked to catalogue skills you have case evidence for.

## 4. Where in the code
- `src/signals/{config,matcher,hn,indeed,compute,pipeline}.py` and `src/api_signals.py`
- `web/src/components/{SkillsRadar,MarketPulse,SignalParts}.tsx`
- `web/src/pages/{Signals,Sources}.tsx`
- the Pathway "Market context" card
- tests: `tests/test_signals_*.py` and `tests/test_api_signals.py`

## 5. Example (data to 2026-10-15)
- **AI agents** is in 44 of 266 posts this month. Its 3-month average is far above its 12-month one, and its 12-month change is +54 %, so it's **rising**.
- **Excel** is in 2 of 266, so it's **insufficient data**: this is a tech board, so that's no sign the skill is declining.

## 6. Limits and honesty
- HN is US, start-up and remote heavy, with a few hundred posts a month. It's labelled "Tech hiring signal (Hacker News)", never "Malaysian market".
- Keyword matching measures topics mentioned, not verified requirements. Precision is about 93 % on 30 hand-checked matches (`eval/signals_precision.md`).
- Indeed covers no Malaysia or Singapore. The default is Australia, labelled "not Malaysia".
- Two event-marker links (OpenAI) couldn't be checked automatically and are marked unverified.
- Nothing here changes matches or paths.

## 7. Questions and answers
- *Is this a forecast?* No. These are trend signals from public posts, and the UI never says "prediction".
- *Why not Malaysian data?* No free, dated, licensed Malaysian source exists in these feeds. We show the closest covered market and say so.
- *Does my data go to HN or Indeed?* No. The fetch only downloads public data, and matching to your profile happens on our server.
- *Why doesn't a rising skill change my pathway?* External evidence informs, and people and HR decide. Changing weights goes through the company assumptions (layer B).

## 8. Design choices considered
- Google Trends was rejected: it has no official API.
- Paid feeds (Lightcast, Adzuna) are out of scope.
- arXiv research momentum has an extension point in `pipeline.py` but isn't built.
- A committing cron job was rejected for a PR-opening one, so a person reviews each refresh.
