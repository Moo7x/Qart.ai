# "Find my path" flow (`web/src/onboarding/`, `Landing`, `Onboarding`, `Matching`, `FindMyPath`)

## 1. What it does
New users land on one question, "Where does your career go next?", with a **Find my path** button. Three short steps of questions follow, then a matching screen, then the app's four tabs: Find my path · Future skills · Get matched · Generate pathway.

## 2. Why it exists
The questionnaire used to be one long page. Three steps with clear required fields make the start easier, and the locked tabs make the order obvious: answer first, then see matches and a pathway. Market data (Future skills) is open to everyone.

## 3. How it works
- **One answers object** (`answers.tsx`): the same Profile and Preferences the ranking reads.
  - Every change is kept as a draft in the browser, so a refresh keeps your answers and your step.
  - Leaving a step saves it to the backend.
  - `profileComplete` turns on only when matching finishes.
- **Steps** (`Steps.tsx`): the existing questions, in three groups. Next stays disabled until the required fields are filled (role and years in step 1, direction in step 2), and the hint names what's missing.
- **Matching** (`Matching.tsx`): five stages, each a real request:
  1. save the answers;
  2. map them to skill IDs (`/api/held-skills`);
  3. load the market signals;
  4. rank the roles;
  5. build the top role's gap and plan.

  Each shows for at least 400 ms. If one fails it turns red with the reason, and **Try again** resumes from that stage. `/matching?fail=4` simulates a failure, for testing.
- **Shell** (`AppShell.tsx`): the tab bar and a More menu (SDG impact, Scenarios, Work queue, My skills, Data sources).
  - Get matched and Generate pathway are locked until matching completes.
  - The routes are guarded too: a direct URL shows the same "unlocks after Find my path" panel.

## 4. Where in the code
- `web/src/onboarding/{answers,fields,Steps,AppShell}.tsx`
- `web/src/pages/{Landing,Onboarding,Matching,FindMyPath}.tsx`
- routes in `web/src/App.tsx`
- old URLs (`/start`, `/signals`, `/matches`, `/pathway`) forward to the new ones.

## 5. Questions and answers
- *Where is my name stored?* Only in your browser. The server never receives it, because the app must not hold real personal data.
- *What does Reset demo do?* It also clears the saved answers, so the tabs lock again.
