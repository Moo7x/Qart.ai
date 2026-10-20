# Decision log (our own reasoning: evidence the idea is ours)

Format: `YYYY-MM-DD HH:MM · who · decision · why · what we do instead`

- 2026-10-21 · team · Product name Qart.ai; problem: help companies retrain employees as AI changes work instead of replacing them; "your mistakes are your future skills" · our own framing after domain research
- 2026-10-21 · team · First setting: finance operations (bank reconciliation review of AI-prepared work) · checkable ground truth, strong 2026 finance evidence, at-risk roles
- 2026-10-21 · team · Build a deployed base first, then shippable increments; voice / RunPod / improvement gate are timeboxed spikes · a working base with features beats nothing
- 2026-10-21 · Person A (with Claude Code) · Four internal roles (recon_associate, ai_finops_analyst, controls_assurance_analyst, fpa_analyst), each built on cited O*NET 31.0 occupations; optional roles (finance data quality, automation specialist) left out · four roles are enough to show ranking and scenario changes, and each one can be explained · add roles only with an O*NET basis
- 2026-10-21 · Person A · Skill types: unsupported_adjustment, escalation_judgment, ai_output_review, data_quality, controls_design, stakeholder_communication are oversight; the rest execution · type drives the scenario shift rule, so it must be explainable per skill (catalogue/skills.json type_reason)
- 2026-10-21 · Person A · 16 verified free courses instead of ~40 · every URL had to be opened by hand; we prefer fewer real items to many unchecked ones · add more later with the same verification
- 2026-10-21 · Person A · Contract gaps written to docs/CONTRACT_QUESTIONS.md (outcome "failure", optional extra fields, case metadata without ground_truth) · the contract is not changed without both teammates · code uses the closest compliant choice meanwhile
