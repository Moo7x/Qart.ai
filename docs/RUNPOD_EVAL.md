# RunPod occupation matching: measured comparison

Five methods match a job title to O*NET occupations: keyword (BM25), dense (BGE-M3 on RunPod),
dense+rerank, hybrid (keyword and dense merged by reciprocal rank fusion) and hybrid+rerank (the
app's method). Two query sets: the development set, used while the search was built, and a
hold-out set written and frozen before the hybrid search existed. **Quote the hold-out numbers;**
the development numbers are optimistic because changes followed a look at its misses.

**What we concluded (2026-10-30).** The GPU models clearly beat keyword search on both sets
(hold-out top-1: 46% keyword, 70% dense+rerank; top-3: 56% keyword, up to 90% dense). Merging the
keyword results in (hybrid) did not help: hybrid+rerank scored 68% top-1 on the hold-out set and
68% on the development set, against 70% and 72% for dense+rerank. The app therefore keeps
dense+rerank; the hybrid search stays in the evaluation as a measured alternative. One finding to
follow up, not tuned on: on the hold-out Malay queries the reranker lowered top-1 (dense 9/15,
dense+rerank 5/15), while dense alone kept the right occupation in its top 3 for 45 of 50 queries.
Differences of one or two queries out of 50 are within noise.

## Hold-out set (frozen before the hybrid search)

<!-- results:holdout -->
Run 2026-10-30 06:04 UTC with `python -m src.occupations.evaluate holdout` on 1016 O*NET 31.0 occupations and 50 queries (`data/eval/occupation_titles_holdout.yaml`). Models on RunPod: BAAI/bge-m3 (dense) and BAAI/bge-reranker-v2-m3. Hybrid = BM25 and dense top 50 each, merged by reciprocal rank fusion, reranked top 10; dense+rerank reranks the dense top 10. MRR counts the top 3. A small diagnostic set, not a statistical guarantee.

| Method | Top-1 | Top-3 | MRR |
|---|---|---|---|
| bm25 | 23/50 (46%) | 28/50 (56%) | 0.50 |
| dense | 31/50 (62%) | 45/50 (90%) | 0.74 |
| dense+rerank | 35/50 (70%) | 41/50 (82%) | 0.76 |
| hybrid | 33/50 (66%) | 43/50 (86%) | 0.75 |
| hybrid+rerank | 34/50 (68%) | 40/50 (80%) | 0.73 |

Top-1 by query kind (en = English, ms = Malay, mixed, typo):

| Method | en | mixed | ms | typo |
|---|---|---|---|---|
| bm25 | 18/25 (72%) | 3/5 (60%) | 1/15 (7%) | 1/5 (20%) |
| dense | 19/25 (76%) | 1/5 (20%) | 9/15 (60%) | 2/5 (40%) |
| dense+rerank | 22/25 (88%) | 4/5 (80%) | 5/15 (33%) | 4/5 (80%) |
| hybrid | 20/25 (80%) | 3/5 (60%) | 9/15 (60%) | 1/5 (20%) |
| hybrid+rerank | 22/25 (88%) | 5/5 (100%) | 4/15 (27%) | 3/5 (60%) |

Latency: one batch job embedding all 50 queries took 24.9 s (including any cold start); one rerank job took median 2.6 s (max 2.8 s).

Misses (top-1 wrong for hybrid+rerank):

| Query | Expected | bm25 | dense | hybrid | hybrid+rerank |
|---|---|---|---|---|---|
| Collections officer | 43-3011.00 | **13-2081.00** | 43-3011.00 | **25-4012.00** | **13-2081.00** |
| Internal auditor | 13-2011.00 | 13-2011.00 | **51-9061.00** | 13-2011.00 | **13-2061.00** |
| Call centre agent handling billing queries | 43-4051.00 | **43-3021.00** | **43-3011.00** | **43-3021.00** | **43-2021.00** |
| payrol clerk | 43-3051.00 | **23-1012.00** | 43-3051.00 | **43-4071.00** | **43-5051.00** |
| bookeeper | 43-3031.00 | **—** | **47-2011.00** | **47-2011.00** | **37-3011.00** |
| Eksekutif akaun | 13-2011.00, 43-3031.00 | **—** | **43-6011.00** | **43-6011.00** | **11-2011.00** |
| Kerani gaji | 43-3051.00 | **—** | **41-2021.00** | **41-2021.00** | **43-3031.00** |
| Juruwang bank | 43-3071.00 | **13-2061.00** | **43-4141.00** | 43-3071.00 | **43-3011.00** |
| Pegawai pinjaman | 13-2072.00 | **—** | 13-2072.00 | 13-2072.00 | **43-4131.00** |
| Pengurus kewangan | 11-3031.00, 11-3031.01 | **—** | 11-3031.00 | 11-3031.00 | **43-3099.00** |
| Pegawai pematuhan | 13-1041.00 | **—** | 13-1041.00 | 13-1041.00 | **33-3041.00** |
| Juruaudit | 13-2011.00 | **—** | **47-4011.01** | **47-4011.01** | **47-4011.01** |
| Kerani am pejabat | 43-9061.00 | **—** | **43-6014.00** | **43-6014.00** | **43-6011.00** |
| Pegawai perolehan | 13-1023.00, 43-3061.00 | **—** | **43-5071.00** | **43-5071.00** | **31-9095.00** |
| Ahli statistik | 15-2041.00 | **—** | 15-2041.00 | 15-2041.00 | **15-2041.01** |
| Pentadbir pangkalan data | 15-1242.00 | **43-9021.00** | 15-1242.00 | **15-2051.02** | **43-9021.00** |
<!-- end results:holdout -->

## Development set

<!-- results:dev -->
Run 2026-10-30 06:08 UTC with `python -m src.occupations.evaluate dev` on 1016 O*NET 31.0 occupations and 40 queries (`data/eval/occupation_titles.yaml`). Models on RunPod: BAAI/bge-m3 (dense) and BAAI/bge-reranker-v2-m3. Hybrid = BM25 and dense top 50 each, merged by reciprocal rank fusion, reranked top 10; dense+rerank reranks the dense top 10. MRR counts the top 3. A small diagnostic set, not a statistical guarantee.

| Method | Top-1 | Top-3 | MRR |
|---|---|---|---|
| bm25 | 24/40 (60%) | 26/40 (65%) | 0.62 |
| dense | 22/40 (55%) | 31/40 (78%) | 0.65 |
| dense+rerank | 29/40 (72%) | 35/40 (88%) | 0.80 |
| hybrid | 27/40 (68%) | 33/40 (82%) | 0.74 |
| hybrid+rerank | 27/40 (68%) | 35/40 (88%) | 0.76 |

Top-1 by query kind (en = English, ms = Malay, mixed, typo):

| Method | en | ms |
|---|---|---|
| bm25 | 23/32 (72%) | 1/8 (12%) |
| dense | 19/32 (59%) | 3/8 (38%) |
| dense+rerank | 23/32 (72%) | 6/8 (75%) |
| hybrid | 23/32 (72%) | 4/8 (50%) |
| hybrid+rerank | 21/32 (66%) | 6/8 (75%) |

Latency: one batch job embedding all 40 queries took 28.9 s (including any cold start); one rerank job took median 2.6 s (max 2.8 s).

Misses (top-1 wrong for hybrid+rerank):

| Query | Expected | bm25 | dense | hybrid | hybrid+rerank |
|---|---|---|---|---|---|
| Accounts receivable executive | 43-3031.00, 43-3011.00 | 43-3031.00 | 43-3011.00 | **11-2011.00** | **43-1011.00** |
| Payroll executive | 43-3051.00 | 43-3051.00 | 43-3051.00 | 43-3051.00 | **11-3111.00** |
| Credit controller | 13-2041.00, 43-3011.00 | 13-2041.00 | **43-4041.00** | **43-4041.00** | **53-2021.00** |
| FP&A analyst | 13-2051.00, 13-2031.00 | **29-1215.00** | **13-2099.01** | 13-2051.00 | **13-1141.00** |
| Treasury manager | 11-3031.01 | **11-9071.00** | **11-9199.00** | **11-3031.00** | **11-3031.00** |
| Procurement executive | 13-1023.00, 43-3061.00 | 43-3061.00 | 43-3061.00 | 43-3061.00 | **11-3061.00** |
| Power BI developer building finance dashboards | 15-2051.01 | 15-2051.01 | **15-1243.00** | 15-2051.01 | **15-1243.00** |
| SAP FI functional consultant | 15-1211.00 | **27-1021.00** | **13-1082.00** | **15-1299.03** | **15-1299.03** |
| Process improvement lead | 13-1111.00 | **17-2112.03** | **17-2112.00** | **17-2112.00** | **11-3051.01** |
| I reconcile bank statements and post journal entries | 43-3031.00, 13-2011.00 | **49-2094.00** | **13-1031.00** | **13-2061.00** | **43-3041.00** |
| Jururawat | 29-1141.00 | **—** | **29-1171.00** | **29-1171.00** | **29-2061.00** |
| Pemandu lori | 53-3032.00 | **—** | **53-4031.00** | **53-4031.00** | **53-3054.00** |
| HR executive | 13-1071.00 | **11-3121.00** | 13-1071.00 | **11-3121.00** | **11-3121.00** |
<!-- end results:dev -->

## Earlier runs on the development set (before hybrid search)

Run 2026-10-23 18:32 UTC with `python -m src.occupations.evaluate` on 1016 O*NET 31.0 occupations and 40 team-labelled synthetic queries (`data/eval/occupation_titles.yaml`; a query counts as right when a listed code is returned). Models on RunPod: BAAI/bge-m3 (dense) and BAAI/bge-reranker-v2-m3 (reranking the top 10 dense candidates). Small diagnostic set, not a statistical guarantee; the labels were written before the run.

| Method | Top-1 | Top-3 | Top-1, Malay queries | Top-3, Malay queries |
|---|---|---|---|---|
| bm25 | 23/40 (58%) | 25/40 (62%) | 0/8 (0%) | 0/8 (0%) |
| dense | 22/40 (55%) | 31/40 (78%) | 3/8 (38%) | 6/8 (75%) |
| dense+rerank | 29/40 (72%) | 35/40 (88%) | 6/8 (75%) | 6/8 (75%) |

Latency: one batch job embedding all 40 queries took 37.1 s (including any cold start); reranking one query took median 2.5 s (max 2.8 s).

## Earlier run, before adding Malaysian GBS role titles

Run 1 indexed the O*NET text only (title, reported titles, description). After it, and after
seeing that every method missed "Cash application analyst", each finance occupation's text gained
the TalentCorp GBS role titles the pack already links to it. Because that change followed a look
at these misses, the gain on this set is optimistic: treat it as a diagnostic, not a held-out
result. Dense-only top-1 fell (65% to 55%) while dense+rerank rose; the reranker is kept.

| Method | Top-1 | Top-3 | Top-1, Malay queries | Top-3, Malay queries |
|---|---|---|---|---|
| bm25 | 21/40 (52%) | 24/40 (60%) | 0/8 (0%) | 0/8 (0%) |
| dense | 26/40 (65%) | 32/40 (80%) | 3/8 (38%) | 6/8 (75%) |
| dense+rerank | 27/40 (68%) | 34/40 (85%) | 3/8 (38%) | 5/8 (62%) |

## Misses (top-1 wrong)

| Query | Expected | bm25 | dense | dense+rerank |
|---|---|---|---|---|
| Cash application analyst | 43-3031.00 | 43-3031.00 | **41-2011.00** | 43-3031.00 |
| Accounts payable assistant | 43-3031.00 | 43-3031.00 | **43-9111.00** | 43-3031.00 |
| Akauntan | 13-2011.00 | **—** | **43-3011.00** | 13-2011.00 |
| Juruaudit dalaman | 13-2011.00 | **—** | **15-1299.04** | 13-2011.00 |
| Kerani akaun | 43-3031.00 | **—** | **43-4141.00** | 43-3031.00 |
| Payroll executive | 43-3051.00 | 43-3051.00 | 43-3051.00 | **11-3111.00** |
| Credit controller | 13-2041.00, 43-3011.00 | 13-2041.00 | **43-4041.00** | **43-4041.00** |
| Billing specialist | 43-3021.00 | 43-3021.00 | **43-3011.00** | 43-3021.00 |
| FP&A analyst | 13-2051.00, 13-2031.00 | **29-1215.00** | **13-2099.01** | **13-1141.00** |
| Financial controller | 11-3031.01 | 11-3031.01 | **43-3099.00** | 11-3031.01 |
| Treasury manager | 11-3031.01 | **11-9071.00** | **11-9199.00** | 11-3031.01 |
| Procurement executive | 13-1023.00, 43-3061.00 | 43-3061.00 | 43-3061.00 | **11-3061.00** |
| Power BI developer building finance dashboards | 15-2051.01 | 15-2051.01 | **15-1243.00** | **15-1243.00** |
| SAP FI functional consultant | 15-1211.00 | **27-1021.00** | **13-1082.00** | **13-1082.00** |
| Process improvement lead | 13-1111.00 | **17-2112.03** | **17-2112.00** | **11-3051.01** |
| Cost accountant | 13-2011.00 | 13-2011.00 | **13-1051.00** | 13-2011.00 |
| Penganalisis kewangan | 13-2051.00 | **—** | 13-2051.00 | 13-2051.00 |
| Pegawai pembelian | 13-1023.00, 43-3061.00 | **—** | 43-3061.00 | 43-3061.00 |
| I follow up customers about overdue invoices | 43-3011.00 | **41-3031.00** | 43-3011.00 | 43-3011.00 |
| I reconcile bank statements and post journal entries | 43-3031.00, 13-2011.00 | **49-2094.00** | **13-1031.00** | **13-2061.00** |
| Jururawat | 29-1141.00 | **—** | **29-1171.00** | **29-2061.00** |
| Guru sekolah rendah | 25-2021.00 | **—** | 25-2021.00 | 25-2021.00 |
| Pemandu lori | 53-3032.00 | **—** | **53-4031.00** | **53-3054.00** |
| Chef | 35-1011.00 | **35-2013.00** | 35-1011.00 | 35-1011.00 |
| Data scientist | 15-2051.00 | **19-2099.01** | 15-2051.00 | 15-2051.00 |
| HR executive | 13-1071.00 | **11-3121.00** | 13-1071.00 | **11-3121.00** |
| Marketing executive | 13-1161.00, 11-2021.00, 13-1161.01 | 11-2021.00 | **11-2011.00** | 11-2021.00 |
