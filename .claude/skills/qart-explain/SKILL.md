---
name: qart-explain
description: Write or update plain-language explanation docs (docs/explain/<module>.md) for each Qart.ai module so both teammates can answer judges' questions about any part, at concept level and code level. Use after finishing a module or changing its behaviour, and before checkpoints and the pitch.
---

# Qart.ai module explanations (judge Q&A prep)

Judges may ask **any member about any part**, at concept level ("why help-weighted evidence?") or code level ("show me where the ranking is computed"). Each module gets `docs/explain/<module>.md`:

## Template
1. **What it does:** 2–3 sentences, no jargon.
2. **Why it exists:** the user or brief need it serves (cite the must-have or rule).
3. **How it works:** the steps; formulas written out in plain text; where each number comes from (evidence / assumption / declared parameter / synthetic).
4. **Where in the code:** file paths, key functions and endpoints (`src/engine/skills.py::derive_state`).
5. **Example:** one concrete input → output walk-through (use the golden-journey data: Aina, case_003, case_006, checkin_001).
6. **Limits and honesty:** what it does NOT prove; provisional parameters; what needs validation.
7. **Likely judge questions + short answers:** 4–6 Q&As (e.g. "Isn't this just a chatbot?", "Why not show a mastery %?", "How do trends change roles?", "What if the AI companion is wrong?", "How do you avoid inventing courses?").
8. **Design choices considered:** alternatives and why we didn't pick them (e.g. deep knowledge tracing without learner data; fine-tuning; swarms; OS-level computer use).

## Rules
- Keep each doc under 1 page. Accurate to the current code. Update it when the code changes.
- Write so a teammate who didn't write the code can explain it after a 5-minute read.
- Also maintain `docs/explain/ARCHITECTURE.md`: a one-page overview with the data flow (signals → assumptions → requirements → recommendation → path; case → companion → grader → event → evidence state) and who owns what.
