# RunPod occupation matching: measured comparison

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
