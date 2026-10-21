# Evaluation results

Counts on synthetic data, never rounded up. Each section is rewritten by its own script.

<!-- companion-evaluation:start -->
## Companion evaluation (acceptance set)

Criteria: `eval/acceptance_criteria.py` (sha256:c80fce4f321f83d2dc93ca6d71caab4b09a6a32690d51c681cf02f217588fd0f). Cases: 0.

**Not run:** no acceptance cases in `eval/acceptance/` yet (Person B).
<!-- companion-evaluation:end -->

<!-- retrieval:start -->
## Retrieval recall@5 (synthetic labelled set)

Set: `eval/retrieval_set.json` (15 queries, labelled synthetic). Corpus: 218 documents (verified courses + O*NET 31.0 tasks and DWAs for our roles).

| Retriever | Mean recall@5 | Relevant found | Notes |
|---|---|---|---|
| bm25 (CPU baseline) | 0.78 | 21/28 | k1=1.5, b=0.75, not tuned |
| RunPod hybrid (BGE-M3 + RRF + bge-reranker) | not run | not run | backend not connected yet |

| Query | Found | Top 5 |
|---|---|---|
| q01 learn to query ledger tables with SQL | 2/2 | course_04, course_06, onet_task_21517, onet_task_21518, course_01 |
| q02 explain gaps between budget and actual spending | 2/3 | course_10, course_11, course_05, course_09, onet_task_21531 |
| q03 design review controls for an AI-assisted finance process | 2/2 | course_16, course_17, course_15, course_01, course_14 |
| q04 present findings to managers clearly | 2/2 | course_05, course_09, onet_task_21600, onet_dwa_4.A.4.a.1.a.1, onet_task_3396 |
| q05 build a sales forecast from history | 0/1 | course_10, course_01, onet_dwa_4.A.4.c.1.c.4, course_13, onet_dwa_4.A.2.a.2.d.1 |
| q06 automate repetitive finance steps with a flow | 2/2 | course_12, course_01, course_16, course_17, onet_task_21595 |
| q07 check whether AI output can be trusted | 2/2 | course_15, course_14, course_03, onet_task_21523, course_02 |
| q08 fix messy, incomplete data before analysis | 0/2 | course_10, course_11, onet_task_3406, onet_task_3398, onet_task_21528 |
| q09 match bank statement lines to the ledger | 0/3 | course_08, onet_task_21518, course_04, course_06, onet_task_2509 |
| q10 spot weak controls or possible fraud | 2/2 | onet_task_21507, course_16, course_17, onet_task_3394, onet_task_21511 |
| q11 post correcting entries at month end | 1/1 | onet_task_21518, onet_task_21515, onet_task_21517 |
| q12 find keying mistakes in postings | 1/1 | onet_task_2486 |
| q13 spreadsheet formulas and schedules | 2/2 | course_13, course_02 |
| q14 follow up compliance problems | 1/1 | onet_task_21458, onet_task_2505, onet_task_21590, onet_task_21460, onet_dwa_4.A.4.b.6.h.4 |
| q15 bookkeeping basics: double entry and trial balance | 2/2 | onet_task_2504, onet_task_2486, course_04, course_08, course_06 |
<!-- retrieval:end -->
