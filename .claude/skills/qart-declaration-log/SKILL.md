---
name: qart-declaration-log
description: Keep docs/DECLARATION_LOG.md and docs/decision_log.md up to date for the SDC Technical & Tools Declaration and originality evidence. Use whenever a library, model, dataset, API, AI tool or sponsor resource is added, and whenever a feature is dropped, a spike fails, or the design changes.
---

# Qart.ai declaration and decision logs

## docs/DECLARATION_LOG.md (feeds the Technical & Tools Declaration PDF)
Append one row per new item, never delete rows (mark "removed" instead):

| Date | Category | Name & version | Purpose in Qart.ai | Licence / terms | Access tier | Added by |
|---|---|---|---|---|---|---|

Categories: `library` · `framework` · `external API` · `cloud/deployment` · `AI model (called)` · `AI model (hosted on RunPod)` · `dataset` · `AI dev tool` (Claude Code, Codex: note extent minor/moderate/major) · `sponsor resource` (Replit, RunPod, Kracked Devs).
- Check licences at the source: Hugging Face card, GitHub LICENSE file, dataset docs. The Anthropic Economic Index **data is CC-BY** (code MIT). O*NET 31.0 is CC BY 4.0.
- Note if a dataset contains personal data (it must not, apart from public aggregate statistics).

## docs/decision_log.md (evidence that the idea and decisions are the team's)
One dated entry per decision, in the team's own words:
`YYYY-MM-DD HH:MM · who · decision · why · what we'll do instead`
Examples: the result of the browser-tab spike; choosing the GBS finance demo field; a parameter value and its reason; a source rejected for its terms.

## Rules
- Write entries at the moment of the change, not at the end.
- Never include API keys, emails or phone numbers.
