# What changed

**What and why.** This slice connects new evidence to personal recommendations and makes revisions
inspectable (brief success test and must-haves 2, 3, 4, 6). It compares the same claimed skills,
chosen goal and scenario against two evidence snapshots. It never edits proficiency or changes
the person's destination.

**Flow.** `src/evidence/store.py` keeps immutable observation revisions. Its high-water id selects
the latest version of every fact available at a cutoff, including corrections to past periods.
Re-fetching the current value is a no-op; A→B→A is a new revision. `src/changes/store.py` stores
each profile's accepted cutoff and proposals with their profile/goal hash, scenario and run id.
The scheduled pipeline calls `src/changes/service.py::refresh_proposals` after collection, so
proposals do not depend on visiting a page. A page can recover publication after an interrupted run.

`src/changes/engine.py::compare` calls the existing matching and pathway engines twice. It returns
cited observed differences, exact skill-weight and score-contribution differences, rankings and
the selected pathway's course order/hours. Essential weights and required levels stay fixed.
An essential skill's normalised contribution can change when other weights change.

**Human control.** `/api/profiles/{id}/changes` returns profile-scoped proposals. POST to
`/changes/{change_id}` accepts evidence for both scenarios or declines that proposal. A stale
profile, goal, cutoff, calculation policy/catalogue or already resolved proposal is rejected. Accepted evidence drives the
existing matches/pathway/future routes; source ingestion itself never replaces the chosen journey.
The browser's profile-scoped completion keys are independent of evidence versions.

**Replay.** GET `/changes/replay` chooses two real stored observation periods from AEI or DOSM
JMI. Only that source's cutoff changes; other reference data stays fixed. Method breaks and the
declared possible job-ad coverage break are rejected. Apr/May may be months in the same release,
so the UI calls this observation replay, not two historical publication vintages. Replay does not
write a baseline or proposal. The page is `web/src/pages/Changes.tsx`; the sidebar flags proposals.

**Example.** In the live stored AEI Apr→May data, a synthetic reporting-level-2 graduate's
Procurement Analyst fit under the fast scenario moved 8.4→8.3. The page shows the source passage
and changed contributions. The Finance Systems pathway stayed the same; it is not forced to change.

**Limits / judge questions.** Is this causal labour forecasting? No: AEI usage motivates declared
scenario emphasis; it is not measured Malaysian workplace adoption. Why might DOSM ads change but
fit not change? They provide demand context; the existing fit formula does not use vacancy counts.
Why no change? Duplicate or irrelevant evidence need not alter recommendations. Does replay show
what the app predicted at that historical date? No, other reference data is held fixed. Is the
cloud schedule proven by this code? No, deployment logs must independently establish that.

**Alternatives.** On-demand LLM explanations could drift from the score; these explanations use
the actual computed deltas. A timer in a browser stops when it closes; an independent scheduled
deployment runs the same pipeline command against shared Postgres. Extra research agents,
learned ranking and robust optimisation remain deferred proposals.
