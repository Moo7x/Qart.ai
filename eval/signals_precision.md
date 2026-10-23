# Skills Radar matcher: hand-checked precision

*23 Oct 2026 · HN "Who is hiring?" cache, Nov 2023 → Oct 2026 (36 threads) · matcher in `src/signals/matcher.py`, patterns in `catalogue/signal_config.json`.*

## Random sample (30 matches, seed 20261023)
Each match was read with about 60 characters of context on each side.

- **28 / 30 clear true positives**: the skill named as part of the stack or the requirements.
- **2 borderline**, counted as false positives:
  - SQL mentioned to say users *don't* need it ("without experience or expertise in SQL");
  - AWS listed while the post says it mainly wants Azure/GCP.
- **Precision ≈ 93 %** (28/30). The sample is dominated by common skills (Python, TypeScript, React, SQL, AWS), as in the data.

## Spot checks of ambiguous skills (5 random matches each)

| Skill | Matching posts (36 months) | Finding |
|---|---|---|
| RAG | 183 | All 5 real mentions; one is a product question ("Is RAG the killer use case?") |
| ERP (SAP / Oracle / NetSuite) | 67 | All 5 about ERP products or integrations |
| Excel | 114 | Mostly finance or spreadsheet products ("AI-native spreadsheet", "Excel Copilot"); `spreadsheets?` also matches companies building spreadsheets |
| AI agents | 814 | Real, but often what the company *builds* ("builds AI agents") rather than a skill requirement |
| RPA / process automation | 57 | `workflow automation` mostly describes products; only some posts ask for RPA tools |

## What this means for the UI
- The radar measures **how often job posts mention a topic**, not a verified skill requirement. The HN caveat says matches are keyword-based, and the source is tech start-ups, mostly US or remote.
- Low-volume skills (fewer than 5 mentions a month over the last 6 months) show as **Insufficient data**. Today that's Excel, ERP, RPA, Power BI / Tableau, data quality, LangChain, MLOps, TensorFlow and NLP, so the finance tools mostly sit there. That's expected on a tech board; don't read it as a sign that the skill is declining.
- Bare `R`, `Go` and `C` are not tracked (too noisy); `Excel at` and `React Native` are excluded.

## Re-check
Re-run the sampling script in this note's commit message after changing any pattern, and update the counts here.
