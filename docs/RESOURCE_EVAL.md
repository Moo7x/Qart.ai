# "Doing this with AI" resources: method and measured result

Job: `python -m src.collectors.ai_resources` (writes `data/packs/gbs_fa/ai_resources.yaml`).
Run 2026-11-01 over all 51 pack skills, task model v2.

## Method

1. **Target from evidence.** Each skill's O*NET tasks in the finance and clerical occupations,
   ordered by automation-style AI use (Economic Index, else the task model), plus the skill's level
   description. Two queries: the skill's work, and "how finance staff use AI, Copilot or automation
   for" that work.
2. **Candidates.** All Microsoft Learn modules and paths about AI, Copilot or automation (Catalog
   API), and YouTube videos found with "<skill> with AI" (trusted channels, or channels with at
   least 20,000 subscribers and videos with 5,000 views; 3-60 minutes).
3. **Ranking.** BGE-M3 shortlists 20 per skill; bge-reranker-v2-m3 scores each against both
   queries; the 6 with the highest lower score are judged.
4. **Judgement (labels).** gpt-4.1-mini reads the page or the captions and must quote one sentence
   on the skill's work and one on AI used for it. Kept only if both quotes are found word for word,
   the AI quote names AI or automation, and one quote names the skill. These are model labels.
5. **Learned ranker.** Logistic regression on both scores, provider trust, recency and length.
6. **Specificity.** A resource counts for at most 2 skills (its best-scoring ones).

## Result

| Ordering of the judged candidates | Precision at 3 |
|---|---|
| The source's own order | 0.21 |
| Dense similarity only | 0.28 |
| Lower of the two reranker scores | 0.31 |
| Learned ranker (fitted on the same labels, so optimistic) | 0.34 |

Learned ranker, 5-fold cross-validated AUC: 0.73. Its weights: AI-query score +2.44, recent +0.66,
provider on the trusted list −1.85 (general Microsoft Learn modules failed the check more often
than specific videos), skill score −0.11, length −0.11.

306 candidates judged, 78 kept; after the specificity rule 41 resources cover 28 of 51 skills. The
other skills show "No checked resource on doing this with AI yet" instead of an AI promise.

**Check of the kept resources.** All 41 were reviewed by an AI coding assistant (Claude Code)
against their skill: 32 clearly teach the skill's work with AI; 9 are weak or general (for
example a customer-data platform for data management). A human review of the labels is still to
be done and would replace these model labels as the training and test set.
