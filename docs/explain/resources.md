# Learning resources (`catalogue/courses.json`, `catalogue/milestones.json`, `src/engine/resources.py`)

## 1. What it does
It holds the real courses the learning plan can use, and the hands-on milestones placed between them.

## 2. Why it exists
Domain 1 must-have 4 asks for an ordered plan with time, using free or low-cost courses (including HRD Corp-claimable ones). The brief forbids invented courses, so every entry is a real public page with its source and check date.

## 3. How it works
- **Each course records:**
  - which skills it takes from which level to which (`skill_steps`, on the 0 / 0.3 / 0.7 / 1.0 scale);
  - its hours and where they come from;
  - cost to the person (`cost_myr`, `cost_type`);
  - whether it is HRD Corp-claimable, only with an evidence page;
  - who it is open to, its format, language and certificate;
  - `status`: draft or verified.
- **"Free" only where the provider says so.** No stated price means `unknown`, never free. An unchecked certificate is `null`, never assumed.
- **The plan uses verified courses only.** `SHOW_DRAFT_RESOURCES=true` also offers drafts, for development.
- **The 26 courses checked on 2026-10-21 are verified.** New research is added as drafts for a team member to review.
- **Milestones** are short practice tasks, linked to a Qart practice case where one exists.

## 4. Where in the code
- `catalogue/courses.json` and `catalogue/milestones.json`
- `src/engine/resources.py` (`plan_courses`, `default_milestones`)
- `tests/test_resource_catalogue.py`, which checks:
  - fields, levels and ids;
  - that no course is claimable without evidence, and none is free without a source;
  - that an open-to-all AI-literacy course exists;
  - that every core role skill has a verified course (a warning for now, an error with `DEMO_BUILD=1`);
  - the draft flag and the milestone links.

## 5. Limits
- Most checked courses are short modules, so they only reach "heard of it".
- 10 core skills have no verified course yet (the test warning lists them); B3 drafts them.
