# Retrieval preparation (`src/retrieval/`, `eval/retrieval_eval.py`)

## 1. What it does
One search interface (`index(documents)`, `search(query, filters)` → ranked results with source and
date) that the path planner and the companion can use later. Today it runs a CPU **BM25** keyword
baseline with metadata filters; the **RunPod** dense-embedding (BGE-M3) and reranker
(bge-reranker) backends exist as interfaces only. Nothing in the planner or the API uses it yet.

## 2. Why it exists
PERSON_A Task A7 (RunPod retrieval) and the rule "no source → no claim": every result carries its
source, URL and date. Recall@5 is measured now so the later GPU gain can be shown honestly.

## 3. How it works
- **Corpus** (227 docs): the 26 verified courses (text = provider + the names and descriptions of the
  skills they cover, our own catalogue metadata) + O\*NET 31.0 task statements (113) and detailed
  work activities (88) for the five occupations our roles are based on. Raw O\*NET CSVs stay in
  gitignored `data/raw/onet_31_0/`; `data/processed/onet_tasks_dwas.json` (40 KB) is committed with
  source, URL and retrieval date.
- **BM25** (`bm25.py`): score = Σ IDF(t)·f(t,d)(k1+1)/(f(t,d)+k1(1−b+b|d|/avgdl)), k1 = 1.5,
  b = 0.75 (standard defaults, *sourced*, not tuned).
- **Filters** (`filters.py`): free only (cost tier from the label, never assumed free), max hours,
  language, document kinds, skills. A filter only applies to documents carrying that field.
- **Hybrid** (`hybrid.py`): BM25 + dense rankings fused by reciprocal-rank fusion,
  RRF(d) = Σ 1/(60 + rank), then an optional cross-encoder rerank of the fused pool.
- **RunPod backends** (`runpod_backends.py`): `RunPodBGEM3Embedder`, `RunPodBGEReranker` raise
  NotImplementedError until the endpoint exists (no silent fallback).
- **Microsoft Learn candidates** (`mslearn.py`): the public Catalog API (no key, Microsoft APIs Terms
  of Use, free) filtered to beginner, business-facing items on Excel / Power BI / Power Automate /
  Dynamics Finance, finance titles or AI fundamentals → 129 items in
  `catalogue/course_candidates_mslearn.json` with status "candidate". **The planner must not use
  them until a human approves them.**

## 4. Where in the code
`src/retrieval/{models,base,filters,bm25,hybrid,runpod_backends,corpus,mslearn}.py`;
`eval/retrieval_eval.py` + `eval/retrieval_set.json`; tests `tests/test_retrieval.py`.

## 5. Example
"spot weak controls or possible fraud" → top 5 includes O\*NET 13-2011 tasks 21507 ("Collect and
analyze data to detect deficient controls…") and 21511, plus both COSO resources. Overall BM25 mean
recall@5 = **0.74 (20/28 relevant found, 15 synthetic queries)**, down from 0.78 when the corpus
grew from 17 to 26 courses (more look-alike documents compete); misses are vocabulary mismatches
("build a sales forecast from history" does not share words with "Forecasting: Principles and
Practice"), which is what dense embeddings are expected to fix.

## 6. Limits and honesty
The labelled set is small, synthetic and written by us; course texts include our skill
descriptions, which helps BM25. Microsoft Learn skill hints are keyword guesses for a reviewer. The
Catalog API endpoint is marked for deprecation in favour of the Learn Platform API.

## 7. Questions and answers
- *Why BM25 first?* It runs on CPU, is explainable, and gives the baseline the GPU version must beat.
- *Where is RunPod?* The interfaces are ready; the endpoint is the next spike (A7).
- *Can retrieval invent a course?* No: it only returns indexed documents, each with source and date.

## 8. Design choices considered
A vector database (overkill for ~200 documents); `rank_bm25` library (a 40-line implementation is
easier to explain and test); LLM query rewriting (no LLM in this run).
