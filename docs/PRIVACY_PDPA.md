# Personal data under Malaysia's PDPA 2010: how Qart.ai handles it

Built with synthetic profiles only. The mapping below is how a live service would meet the seven
PDPA principles, and where each part is in the code today.

| PDPA principle | What Qart.ai does | Where |
|---|---|---|
| General (purpose) | Processes only what matching needs: situation, current role, skill levels with the CV sentence behind each, hours, budget, interests | Privacy page; `src/journey/store.py` |
| Notice and choice | The CV popup says what is read before upload; every extracted item is reviewed by the person before it is saved | `web/src/pages/onboarding/CvPopup.tsx` |
| Disclosure | No data is shared with third parties; the language model receives scrubbed text only | `src/intake/pii.py` |
| Security | Admin routes need a token; secrets live in environment variables; no raw CV file is stored, only the reviewed claims and quoted sentences | `src/api/evidence.py` `require_admin`; `src/config.py` |
| Retention | Profiles unused for 90 days are deleted by the daily pipeline | `PROFILE_RETENTION_DAYS`, `src/privacy.py` |
| Data integrity | The person can edit every claim; a level is always labelled a claim | Edit my profile; level labels |
| Access | Export everything held about you, or delete it, from the Privacy page | `GET /api/privacy/export`, `DELETE /api/privacy` |

Aggregates across people (platform SDG totals) hide any group smaller than 5
(`PLATFORM_SDG_MIN_PROFILES`). Fairness: `tests/test_fairness.py` checks that profiles differing
only in protected attributes get identical results.
