# Role catalogue for the ranking (`catalogue/target_roles.json`, `src/engine/role_catalogue.py`)

## 1. What it does
It lists the 15 future roles the ranking can suggest. For each role it records:
- the skills it needs: **3 = core**, **1 = nice to have**;
- the level that counts as "has it" (0.7, "use sometimes");
- its family, typical industries and usual education (a note only);
- the public O\*NET occupation it is based on.

## 2. Why it exists
The spec (§0) says the catalogue's quality matters more than the algorithm. Every role is curated by the team and tied to a public occupation, so nothing is invented.

## 3. How it works
- **Families** (`catalogue/families.json`): 14 families with symmetric adjacency, for example finance operations ↔ analytics and analytics ↔ data engineering. Direction fit uses them: same family, adjacent, or far.
- **Sources:** every code was checked on O\*NET OnLine on 2026-10-23.
  - Three roles have **no fitting O\*NET occupation**: Finance Automation (RPA), AI Operations / Prompt and AI Product. They are marked `code: TODO` with candidates for the team to choose.
  - Data Analyst and ML Engineer share 15-2051.00 (Data Scientists), which O\*NET's search returns first for both titles.

## 4. Where in the code
- `catalogue/target_roles.json`
- `catalogue/families.json`
- `src/engine/role_catalogue.py`
- `tests/test_role_catalogue.py`, which checks:
  - each role has 5–8 skills, all in the vocabulary;
  - each role has at least 3 core skills, and the core totals are similar across roles;
  - families exist and adjacency is symmetric;
  - industries and education come from the questionnaire lists;
  - each code is real and checked, or TODO.

## 5. Questions and answers
- *Why not use roles.json?* The practice-evidence engine and HR views use it, and it holds only the 16 practice skills.
- *Why these weights?* They are team judgement, declared, and still to be tuned against the persona tests in step 7.
