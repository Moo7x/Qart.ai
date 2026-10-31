# Language-model policy and guardrails

Qart.ai uses language models for reading and wording, never for deciding or for numbers. This page
lists every use and the guardrail that applies, so each can be checked in the code.

## Models

| Use | Model | Where |
|---|---|---|
| Read a CV into role, situation and skill claims | OpenAI `LLM_MODEL` (gpt-4.1-mini) | `src/intake/extract.py` |
| Course and video fit checks (catalogue jobs) | `LLM_MODEL` | `src/collectors/course_check.py`, `src/collectors/youtube.py` |
| Resource scout agent (which part of a video or article to open) | `AGENT_MODEL` (gpt-4.1-mini) | `src/agents/scout.py` |
| Explanations of a computed result | `LLM_MODEL` | `src/match/explain.py` |
| Text embeddings and reranking (not generative) | BAAI/bge-m3, bge-reranker-v2-m3 on RunPod | `runpod/handler.py`, `src/runpod_jobs.py` |

## Rules, each enforced in code

1. **Personal data is removed first.** CV text is scrubbed of names, contacts, IC numbers, links
   and protected attributes before any model sees it (`src/intake/pii.py`). The paired-profile
   test (`tests/test_fairness.py`) shows protected attributes change nothing.
2. **Schema-constrained answers.** Every call asks for a JSON schema and the answer is validated
   in code; an invalid answer is rejected, not repaired by guesswork.
3. **Quotes must exist.** A CV skill claim must quote the CV; a course or video "fits" only when
   its quote is found word for word on the page or in the captions (`quote_found`). Otherwise
   the item stays unverified and is never recommended.
4. **No numbers from a model.** Scores, levels, hours, forecasts and AI-use shares are computed
   in code from stored observations. The scout drops any reason that contains a digit.
5. **Time budgets and visible fallbacks.** Each call has a time limit (`src/params.py`). On a
   timeout, a missing key or an invalid answer, the app falls back (keyword matching, ranking
   only) and says so in `engine` / `note`; a fallback is never shown as a model result.
6. **People decide.** A model never chooses a role, changes a level or accepts evidence. New
   evidence becomes a proposal with a before/after the person accepts or declines.
7. **Usage is logged.** Every call records purpose, model, tokens and seconds
   (`src/usage.py`); `scripts/cost.py` turns that into docs/COST.md.

## When a person should talk to a person

The plan screen points people to human help for decisions a tool should not make alone:
career services (MYFutureJobs by PERKESO, a university or TVET career centre), and their
employer's HR or L&D team for HRD Corp-claimable training. "Report a problem" on any screen
sends the item to a review queue that a person on the team decides (`/api/feedback`).
