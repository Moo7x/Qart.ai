# Evaluation results

Counts on synthetic data, never rounded up. Each section is rewritten by its own script.

<!-- companion-evaluation:start -->
## Companion evaluation (acceptance set)

Criteria: `eval/acceptance_criteria.py` (sha256:c80fce4f321f83d2dc93ca6d71caab4b09a6a32690d51c681cf02f217588fd0f). Cases: 0.

**Not run:** no acceptance cases in `eval/acceptance/` yet (Person B).
<!-- companion-evaluation:end -->

<!-- retrieval:start -->
## Retrieval recall@5 (synthetic labelled set)

Set: `eval/retrieval_set.json` (15 queries, labelled synthetic). Corpus: 227 documents (verified courses + O*NET 31.0 tasks and DWAs for our roles).

| Retriever | Mean recall@5 | Relevant found | Notes |
|---|---|---|---|
| bm25 (CPU baseline) | 0.74 | 20/28 | k1=1.5, b=0.75, not tuned |
| RunPod hybrid (BGE-M3 + RRF + bge-reranker) | not run | not run | set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID (runpod/README.md) |

| Query | Found (BM25) | Top 5 (BM25) |
|---|---|---|
| q01 learn to query ledger tables with SQL | 2/2 | course_04, course_06, onet_task_21517, onet_task_21518, onet_task_2492 |
| q02 explain gaps between budget and actual spending | 2/3 | course_10, course_22, course_11, course_05, course_09 |
| q03 design review controls for an AI-assisted finance process | 2/2 | course_24, course_16, course_17, course_01, course_15 |
| q04 present findings to managers clearly | 2/2 | course_05, course_09, onet_task_21600, course_22, onet_dwa_4.A.4.a.1.a.1 |
| q05 build a sales forecast from history | 0/1 | course_21, course_10, onet_dwa_4.A.4.c.1.c.4, course_24, onet_dwa_4.A.2.a.2.d.1 |
| q06 automate repetitive finance steps with a flow | 2/2 | course_24, course_12, course_01, course_16, course_17 |
| q07 check whether AI output can be trusted | 2/2 | course_15, course_14, course_25, course_26, onet_task_21523 |
| q08 fix messy, incomplete data before analysis | 0/2 | course_10, course_11, onet_task_3406, course_22, onet_task_3398 |
| q09 match bank statement lines to the ledger | 0/3 | course_08, course_18, onet_task_21518, course_04, course_06 |
| q10 spot weak controls or possible fraud | 1/2 | onet_task_21507, course_16, course_17, course_24, onet_task_3394 |
| q11 post correcting entries at month end | 1/1 | onet_task_21518, onet_task_21515, onet_task_21517 |
| q12 find keying mistakes in postings | 1/1 | onet_task_2486, course_18 |
| q13 spreadsheet formulas and schedules | 2/2 | course_13, course_21, course_02 |
| q14 follow up compliance problems | 1/1 | onet_task_21458, onet_task_2505, onet_task_21590, onet_task_21460, onet_dwa_4.A.4.b.6.h.4 |
| q15 bookkeeping basics: double entry and trial balance | 2/2 | onet_task_2504, onet_task_2486, course_04, course_08, course_06 |
<!-- retrieval:end -->

<!-- engine-checks:start -->
## Engine checks

| Check | Result | How |
|---|---|---|
| Fairness twins | 12/12 identical (failed: none) | each synthetic employee vs a twin differing only in id, name, team, gender, age; same evidence; rankings, scores, fit and paths compared in both scenarios |
| Time from profile to path | median 35 ms over 5 runs (max 67 ms) | POST /api/profile → GET /api/recommendations → GET /api/path, in-process, fresh SQLite, this laptop |
<!-- engine-checks:end -->
