# Evidence layer and pipeline

## What it does
A scheduled pipeline collects dated facts from six registered public sources, stores each fact
with the passage it came from, and turns them into labelled signals ("rising", "weakening", "not
enough evidence yet", "expert view") that the Overview and Live intelligence pages show.

## Why it exists
Brief must-have 2: an updatable AI and job-market signal layer that shows its source and date
(hard-coded lists do not count). Success test: the output changes when the trend data changes.
Rule: never invent statistics; every number cites a source.

## How it works
1. **Registry** (`data/sources.yaml`): what each source shows and does not show, its terms and
   cadence. Only registered sources are collected.
2. **Collectors** (`src/collectors/`): OpenDOSM wages by occupation (API), DOSM Job Market
   Insights (quarterly release pages), Anthropic Economic Index (Hugging Face release, streamed and
   filtered: occupation rows and the rows of each linked O*NET task), TalentCorp GBS study (hand
   extraction with page numbers), O*NET database (task wording and importance for the linked
   tasks, newest release found on the download page) and the ILO GenAI exposure index (score
   file for the field's ISCO-08 groups). Each returns observations and a note for the run log;
   O*NET also names linked tasks that a new release dropped or reworded.
3. **Store** (`src/evidence/store.py`): observations are immutable. Re-fetching the current value
   is skipped; a revision becomes a new row, including A→B→A reversals. A repeated historical
   value gets a hash linked to its predecessor, retaining the unique-hash constraint. A cutoff id
   reconstructs the latest revision available then. Missing stays missing, never zero.
4. **Pipeline** (`src/pipeline/run.py`): a lock stops overlapping runs; each source gets two
   attempts; a failing source keeps its last good data; a run with nothing new is "no change".
5. **Measures** (`src/evidence/measures.py`):
   - share(group, year) = 100 × employees(group) ÷ employees(all), from 2011 (2010 is a
     classification break);
   - job-ad share = 100 × count ÷ total per quarter, split where the total jumps by more than 60%
     (treated as a possible platform-coverage break);
   - Economic Index change counts only if ≥ 0.02 points and ≥ 5%, compared at two decimals;
   - backtest: fit to 2021, score 2022–2025 for no-change, straight line and damped trend.
   After every run the backtest is recomputed on all comparable years so far
   (`src/evidence/models.py`); a new model version with its errors is stored only when a group's
   data changed, and the run log says "trend models unchanged" otherwise. Live intelligence lists
   the versions, so forecast error over time is visible.
   A rolling-origin check (`measures.rolling_backtest`) scores no change, drift, straight line,
   damped trend and simple smoothing at every origin from 2015, one and two years ahead. No
   trend method beats no change in any followed group, so no trend is projected. It uses today's
   published series, not the values available at each origin.
6. **Labels** (`src/evidence/signals.py`): rising/weakening needs two independent sources or one
   official series with ≥ 8 comparable points; otherwise "not enough evidence yet" with an early
   direction. TalentCorp is always an "expert view". All thresholds are in `src/params.py`.

## Any occupation and the Trends page
- `src/occupations/catalogue.py` keeps every O*NET 31.0 occupation (title, reported titles, the
  pack's Malaysian GBS role titles, description, top core tasks) and its closest ESCO occupation.
  After each run the pipeline step `occupation_index` embeds new or changed texts with BGE-M3 on
  RunPod (queued jobs, `src/runpod_jobs.py`) and back-fills ISCO-08 links from the ESCO API.
- `src/occupations/detect.py` matches a job title: BGE-M3 similarity, then the BGE reranker on the
  top 10, both on RunPod; BM25 when RunPod or the index is unavailable, labelled. The person picks.
  `python -m src.occupations.evaluate` writes the measured comparison to `docs/RUNPOD_EVAL.md`.
- `src/occupations/preview.py` shows one occupation's evidence: O*NET tasks, Economic Index use,
  ILO exposure of its ISCO-08 group, the DOSM major-group trend and the MyCOL listing. Roles,
  courses and pathways appear only for the verified GBS finance occupations.
- `src/evidence/trends.py` feeds the Trends page: employment shares by major group with long and
  recent change, the Professionals job-ad share and named occupations (DOSM releases), skill
  emphasis under fast adoption (assumption) and ILO exposure (estimate).

## Where in the code
`src/collectors/*.py::collect` (`onet.py`, `ilo.py` for tasks and exposure) ·
`src/pipeline/run.py::run_pipeline` ·
`src/evidence/measures.py::backtest` · `src/evidence/signals.py::build_signals` ·
routes in `src/api/evidence.py` (`/api/signals`, `/api/sources`, `/api/pipeline/runs`,
`/api/pipeline/backtest`, `POST /api/pipeline/run` with the admin token).

## Example
OpenDOSM: clerical support workers 1,108.6k of 7,634.0k employees in 2011 (14.52%) and 1,360.1k of
10,381.6k in 2025 (13.10%): a fall of 1.42 points ≥ 0.5 over 15 comparable years → "weakening",
noted as history. Backtest for clerical: no-change error 0.48 points, straight line 0.95 → the
trend is not projected.

## Limits and honesty
- Occupation groups are broad (MASCO major groups); they do not show demand for one job title.
- The job-ad series is short and jumped in Q3 2025 (a possible coverage change); DOSM says it does
  not represent all job offerings.
- The Economic Index shows AI use in sampled conversations, not hiring or job losses; only two
  compatible months exist so far.
- TalentCorp combines AI, digital and green drivers; it is one expert source from 2024.
- O*NET describes US occupations; its tasks stand in for GBS work through a declared crosswalk.
- ILO exposure is a model-assisted estimate of technical potential for ISCO-08 occupations (linked
  through the ESCO–O*NET crosswalk), not adoption or job loss, and it scores ISCO tasks, not
  O*NET tasks.
- Thresholds are declared choices, not estimated from data.

## Likely judge questions
- *Is this just a static list?* No: six collectors run on a schedule; the run log shows every run,
  including "no change", and a new DOSM quarter is detected by probing the next release URL.
- *Why not predict the trend?* We tested it: on 2022–2025, no-change beats a straight line for 7 of
  9 groups, so projecting would add error. We show the backtest instead.
- *How do you avoid invented numbers?* The language model is not used here at all; every value is
  a stored row with its cited sentence or row and dates.
- *What if a source is down?* Two attempts, then it is logged as failed and its last good data is
  kept and marked.

## Design choices considered
- Scraping job boards (rejected: their terms forbid it; DOSM publishes aggregated job-ad data).
- An LLM reading the sources (rejected for numbers: values are parsed by code and pinned in tests).
- Merging all sources into one score (rejected: the four kinds of evidence stay separate).
