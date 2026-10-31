# Qart.ai

> Qart.ai shows finance workers and graduates in Malaysia which of their skills still count in the AI era, which future roles fit them, and a free learning route to get there, built on dated public evidence.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | Qart.ai                                     |
| **Team Domain**        | Domain 1: Aiversecity — Future-Ready Workforce |
| **SDG Track (1–17)**   | SDG 4 — Quality Education (targets 4.4, 4.3); SDG 8 — Decent Work and Economic Growth (targets 8.2, 8.5) |
| **Team Leader**        | Kydyrgaliyev Meiirman                       |
| **University**         | Xiamen University Malaysia                  |
| **Number of Members**  | 2                                           |

## Links

| Resource           | Link                                                   |
| ------------------ | ------------------------------------------------------ |
| GitHub Repository  | https://github.com/Moo7x/qart.ai                       |
| Live Demo (Replit) | https://qartai.replit.app                              |
| Demo guide (two synthetic CVs) | [`submission/phase2/DEMO.md`](submission/phase2/DEMO.md) |
| Demo Video (final) | https://youtu.be/_TpEkTakf44                           |
| Slide Deck (final) | [`submission/phase2/SDC2026_Qart.ai_PitchDeck.pdf`](submission/phase2/SDC2026_Qart.ai_PitchDeck.pdf) |
| Final Project & Prototype Report | [`submission/phase2/SDC2026_Qart.ai_Final.pdf`](submission/phase2/SDC2026_Qart.ai_Final.pdf) |
| Technical & Tools Declaration (final) | [`submission/phase2/SDC2026_Qart.ai_TechDeclaration.pdf`](submission/phase2/SDC2026_Qart.ai_TechDeclaration.pdf) |
| RunPod Endpoint    | Private serverless endpoint, called only by the server |
| Preliminary round  | [`submission/`](submission/): proposal, declaration, deck, proof of use; video https://youtu.be/vUb9ipMBztw |

---

## Overview

### Problem

Malaysia's Global Business Services (GBS) sector employs about 250,000 people, and TalentCorp rates 32% of them, about 89,000, as working in roles highly impacted by AI. The evidence of change exists, from DOSM labour statistics to the Anthropic Economic Index, but it is scattered across reports and datasets that no worker reads. A cash application analyst or a final-year accounting student has no single place to ask: which of my skills still count, which roles can I reach, and what should I learn first? Career sites list jobs, and chatbots can invent jobs, courses and statistics.

### Solution

Qart.ai turns that public evidence into a personal plan that can be checked. A person uploads a synthetic CV or answers a few questions; personal details are removed, and OpenAI gpt-4.1-mini reads the CV into skill claims, each quoting the CV (the same CV always gets the same reading). A daily pipeline collects seven public sources, and from them Qart makes its own forecast: a trained model predicts how much AI already does on each task, backtested models forecast demand per job group, and 27 GBS finance roles are labelled Growing, Transforming, Shrinking, Emerging or Stable. Roles are ranked by an explainable fit score and that forecast. The reskilling path starts from the skills the person already has: each becomes "check and steer AI-run work" or "do it faster with AI", with checked courses and YouTube videos on doing that work with AI. Choosing a role turns it into the path to that role.

What makes it different:

- **Numbers come from code, not the model.** The language model reads CVs, checks resources and explains results in plain words; every score is computed from stored, dated observations and shows its source.
- **Its own forecast, with measured error.** The task-level AI-use model (gradient boosting on BGE-M3 features) is chosen by 5-fold cross-validation: mean error 11.2 points against 16.2 for the average. A role is called Transforming only when two of three kinds of AI evidence agree.
- **Reskilling for AI adoption.** Every step is about doing the work with AI; each course or video keeps the quote, from its page or captions, that shows AI used on that work.
- **The answer can change, in the open.** When new evidence arrives, Qart shows what would change and the person accepts or declines; the change test lets anyone edit AI-use or job-market figures and see which roles move.
- **Honest about uncertainty.** Two scenarios, every number labelled observed, assumption or estimate, and a demand trend is projected only if it beats "no change" in a backtest.

### Key Features

- **Profile intake** — synthetic CV upload (PDF, DOCX or TXT), form or questionnaire. Personal details are removed first, and every skill quotes the CV. Levels stay the person's own claims.
- **Live evidence layer** — seven registered public sources, collected daily by a Replit Scheduled deployment, each number with its source and date.
- **Industry forecast** — 27 GBS finance roles in five categories, with the evidence and its strength; skills marked rising or declining.
- **Ranked future roles** — 21 GBS finance roles with full skill requirements, ordered by fit × outlook, with a fit score that shows every point, an essential-skill check, a skills gap and "what would raise it".
- **Reskilling path** — one path built from the person's own skills and how much AI does on their tasks, or to a chosen role; each step has courses, YouTube videos and articles on doing the work with AI, with study hours.
- **SDG mapping** — every role, skill and step tagged to SDG 4.4, 4.3, 8.2 or 8.5 (12.6 for green skills), with how the chosen path contributes.
- **Two scenarios** — moderate and fast AI adoption change weights, forecast and ranking, always labelled as estimates.
- **The person decides** — *What changed* proposes evidence updates to accept or decline; the CV updates as steps are done and downloads as PDF.

### Who it is for

Working adults in GBS finance and accounting roles at risk of displacement, fresh graduates and students (also through TVET and university career centres), and career switchers into GBS. An HR / L&D team view is planned for a later phase.

### Tech Stack

| Layer         | Technology |
| ------------- | ---------- |
| Frontend      | React 19, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend       | Python 3.12, FastAPI, Pydantic, SQLAlchemy Core |
| Database      | PostgreSQL on Replit; SQLite for local runs |
| AI / Compute  | OpenAI gpt-4.1-mini (CV reading, resource checks, plain-words explanations, agents); RunPod Serverless GPU with BAAI/bge-m3 and bge-reranker-v2-m3 (matching, task-model features, resource ranking); scikit-learn models trained in the pipeline |
| Hosting / Dev | Replit Autoscale (web app and API) and Replit Scheduled (daily evidence pipeline) |

Every library, dataset and model, with its licence, is listed in [`docs/DECLARATION_LOG.md`](docs/DECLARATION_LOG.md).

---

## Project Structure

```
.
├── data/
│   ├── sources.yaml         # Registered evidence sources: terms, limits, cadence
│   ├── packs/gbs_fa/        # GBS finance field: roles, skills, tasks, resources, SDG targets
│   ├── samples/             # Synthetic sample CVs (Daniel, Aina, Nur, Hafiz, Mei, Kavitha)
│   └── eval/                # Labelled job titles for the RunPod evaluation
├── docs/
│   ├── PLAN.md              # Product and system design
│   ├── DECLARATION_LOG.md   # Tools, data, models and licences
│   ├── decision_log.md      # Decisions and scope changes
│   ├── RUNPOD_EVAL.md       # Matching accuracy with and without the GPU models
│   └── explain/             # Plain-language explanation of each module
├── runpod/                  # RunPod serverless worker (handler.py, Dockerfile)
├── src/
│   ├── app.py               # FastAPI app: API routes + built web app
│   ├── api/                 # HTTP routes
│   ├── intake/              # CV files, personal-detail removal, skill extraction, skill search
│   ├── collectors/          # One collector per registered source
│   ├── evidence/            # Evidence store, measures, trends and labelled signals
│   ├── forecast/            # Task-level AI-use model and the industry forecast
│   ├── match/               # Fit score, skills gap, scenarios, ranking check, explanations
│   ├── pathway/             # Reskilling path and planner
│   ├── agents/              # Resource scout and progress check (gpt-4.1-mini)
│   ├── changes/             # Update proposals from new evidence
│   ├── cv/, goal/, journey/ # CV versions, a user's goal role, progress
│   ├── occupations/         # Any-occupation search across 1,016 occupations
│   ├── pipeline/run.py      # The scheduled run: python -m src.pipeline.run
│   ├── params.py            # Every threshold and weight, with its reason
│   └── db.py                # One database layer for SQLite and PostgreSQL
├── submission/              # Preliminary round: proposal, declaration, proof of use, deck
│   └── phase2/              # Final round: report, declaration, deck, demo guide
├── tests/                   # pytest suite
├── web/                     # React frontend
├── .env.example             # Environment variable names (no values)
├── .replit                  # Replit run and deployment configuration
├── replit_build.sh          # Install Python packages and build the web app
├── replit_serve.sh          # Start the server, or run the pipeline (QART_DEPLOY_ROLE=pipeline)
├── replit_start.sh          # Run button: build, then serve
└── requirements.txt         # Python dependencies (Python 3.12)
```

### Architecture

```
 Synthetic CV / questions
          │
          ▼
 React web app ──► FastAPI backend (Replit Autoscale) ◄──► PostgreSQL (Replit)
                     │                     │                       ▲
                     ▼                     ▼                       │ writes daily
          OpenAI gpt-4.1-mini      RunPod Serverless GPU    Evidence pipeline
          CV → quoted claims;      BGE-M3 + reranker:       (Replit Scheduled)
          plain-words text         titles and tasks → skills       ▲
                                                              7 public sources
```

After each collection the pipeline re-fits the task-level AI-use model and the demand forecasts, and the industry forecast is recomputed from them. Every remote call has a time budget and a labelled fallback. The final architecture is section 3.1 of [`submission/phase2/SDC2026_Qart.ai_Final.pdf`](submission/phase2/SDC2026_Qart.ai_Final.pdf); the modules are explained in [`docs/explain/`](docs/explain/ARCHITECTURE.md).

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. In Replit, choose **Create Repl → Import from GitHub** and pick this repository.
2. Open **Secrets** and add the variables named in `.env.example`: `LLM_API_KEY`, `DATABASE_URL`, `QART_ADMIN_TOKEN`, and optionally `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`.
3. Click **Run**. `replit_start.sh` installs the Python packages, builds the web app and starts the server on port 8000.
4. To publish, choose an **Autoscale** deployment. `.replit` builds once (`replit_build.sh`) and then only starts the server (`replit_serve.sh`).
5. For the daily evidence run, import the same repository into a second Repl, add the production `DATABASE_URL`, the API keys and `QART_DEPLOY_ROLE=pipeline` to its Secrets, and publish it as a **Scheduled** deployment. `replit_serve.sh` then runs the pipeline once per schedule instead of starting the server.

Without the OpenAI or RunPod keys the app still runs; `/api/health` shows which parts use a labelled fallback.

### Option 2 — Run Locally

Requires Python 3.12 and Node.js 22.

```bash
git clone https://github.com/Moo7x/qart.ai.git
cd qart.ai
python3.12 -m venv .venv        # Windows: py -3.12 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your values
cd web && npm ci && npm run build && cd ..
uvicorn src.app:app --port 8000 # then open http://localhost:8000
```

### Run Tests

```bash
python -m pytest
```

The tests never call paid services. Code checks: `ruff check .` and `mypy src tests`.

---

## How We Use Replit *(Required)*

- **Hosting:** the FastAPI backend and the built React frontend run as one Replit Autoscale deployment, the live demo above.
- **Database:** Replit PostgreSQL holds profiles, plans, CV versions, dated evidence and update proposals.
- **Scheduled pipeline:** a second Repl runs `python -m src.pipeline.run --trigger schedule` every day as a Replit Scheduled deployment against the same database (`replit_serve.sh` with `QART_DEPLOY_ROLE=pipeline`), so evidence and run history keep updating even when nobody uses the app. The schedule is also in the repository: `.github/workflows/daily-pipeline.yml` asks the deployed app to start a run every day at 09:15 Malaysia time (`POST /api/pipeline/run?trigger=schedule` with the admin token). The run lock stops the two triggers overlapping, and every run, including "no change", is listed on Live intelligence → Run history.
- **Secrets:** all keys live in Replit Secrets, never in the code.

📄 Proof of use: [`submission/REPLIT PROOF OF USE.pdf`](submission/REPLIT%20PROOF%20OF%20USE.pdf)

## How We Use RunPod *(Required)*

- **Workload:** GPU inference. A serverless worker serves two open models: `BAAI/bge-m3` (embeddings, MIT) and `BAAI/bge-reranker-v2-m3` (reranker, Apache-2.0). Nothing is trained on the GPU; its BGE-M3 vectors are the features of Qart's task-level AI-use model, trained in the pipeline.
- **Setup:** `runpod/handler.py` runs as a **RunPod Serverless Endpoint**, built from `runpod/Dockerfile` in this repository (queue-based, min workers 0, max 1).
- **Use in Qart.ai:** matching any job title, in English or Malay, to 1,016 occupations; mapping a person's own words about their tasks to skills; features for the task-level AI-use model; ranking courses and videos on doing each skill with AI. Every call has a time budget and a labelled fallback.
- **Result:** on 40 labelled job titles, top-1 accuracy is 72% with the models and 60% with keyword search alone; for Malay titles, 75% and 12% ([`docs/RUNPOD_EVAL.md`](docs/RUNPOD_EVAL.md)). For AI resources, precision at 3 rises from 0.21 (source order) to 0.31 with the reranker and 0.34 with the learned ranker ([`docs/RESOURCE_EVAL.md`](docs/RESOURCE_EVAL.md)).

Example request:

```bash
curl -X POST https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"task": "embed", "texts": ["bank reconciliation"]}}'
```

📄 Proof of use: [`submission/RUNPOD PROOF OF USE.pdf`](submission/RUNPOD%20PROOF%20OF%20USE.pdf)

---

## Challenges & Learnings

- **Keeping the language model honest.** A model reading a CV can claim skills that are not there. Each claim has to quote the CV, code rejects quotes that are not in it, and the model is never allowed to produce a number.
- **Matching in Malay.** Keyword search found 12% of Malay job titles. Moving matching to open multilingual models on a RunPod GPU raised it to 75%, and we measured it rather than assumed it.
- **Cold GPUs.** A serverless GPU can take about 20 seconds to start, so every call got a time budget and a visible keyword fallback; no page waits for it.
- **Forecasts that must earn their place.** Each demand series is projected only by a method that beats "no change" in a rolling backtest; otherwise Qart shows no change and says why. The task model is used only if it beats the average by 5% in cross-validation.
- **Reskilling must be about AI.** Our first plan had a track "without AI"; feedback showed it missed the point. Every step now teaches doing the work with AI, and a resource is kept only when a quote on its page or in its captions shows AI used on that work.
- **The same CV, two readings.** The model could link one CV sentence to different skills on different runs, giving two fits. The first reading of a CV is now stored and reused.
- **Design for the user.** Walking through the app as users showed crowded pages and a plan that was hard to follow. We rebuilt the plan as a route with clear stops, made every question skippable, and kept the journey to about three minutes.

## Future Improvements

- [ ] Test with at least 10 real users: time to a plan and whether they can explain their top role
- [ ] Raise verified free-course coverage from 83% to 90% of required skills, and AI-adopted material beyond 23 of the 42
- [ ] Human review of the resource labels, then retrain the rankers on a larger set
- [ ] HR / L&D team view with aggregate skill gaps (groups under 5 hidden)
- [ ] More fields beyond GBS finance and accounting
- [ ] Native-speaker review of the Bahasa Malaysia interface

---

## Team

| Name                  | Role                                              | GitHub |
| --------------------- | ------------------------------------------------- | ------ |
| Kydyrgaliyev Meiirman | Team leader · planning and idea · frontend and UI | [@kydyrgaliyevm](https://github.com/kydyrgaliyevm) |
| Mounir Ben Hassine    | Planning and idea · backend, data pipeline and deployment | [@Moo7x](https://github.com/Moo7x) |

Both members iterated on the frontend and backend together once the first working version was in place.

---

## Submission Checklist

- [x] Team name, domain and SDG track filled in
- [x] Final Project & Prototype Report and final Technical & Tools Declaration in `submission/phase2/`
- [ ] Final slide deck in `submission/phase2/`
- [x] Final demo video link and demo guide added
- [x] Preliminary slide deck and video in `submission/`
- [x] Replit used, with proof of use in `submission/`
- [x] RunPod used, with proof of use in `submission/`
- [x] Preliminary proposal and Technical & Tools Declaration completed in `submission/`
- [x] "How to Run" steps verified
- [x] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
