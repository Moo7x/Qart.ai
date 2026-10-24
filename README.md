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
| Live Demo (Replit) | https://qartai.replit.app/start                        |
| RunPod Endpoint    | Private serverless endpoint, called only by the server |
| Slide Deck         | [`submission/SDC2026_Qart.ai_PitchDeck.pdf`](submission/SDC2026_Qart.ai_PitchDeck.pdf) |
| Demo Video         | https://youtu.be/vUb9ipMBztw                           |

---

## Overview

### Problem

Malaysia's Global Business Services (GBS) sector employs about 250,000 people, and TalentCorp rates 32% of them, about 89,000, as working in roles highly impacted by AI. The evidence of change exists, from DOSM labour statistics to the Anthropic Economic Index, but it is scattered across reports and datasets that no worker reads. A cash application analyst or a final-year accounting student has no single place to ask: which of my skills still count, which roles can I reach, and what should I learn first? Career sites list jobs, and chatbots can invent jobs, courses and statistics.

### Solution

Qart.ai turns that public evidence into a personal plan that can be checked. A person uploads a synthetic CV or answers a few questions; personal details are removed, and OpenAI gpt-4o-mini reads the CV into skill claims, each quoting the CV. A daily pipeline collects seven public sources, and code then works out how much each skill matters under a moderate and a fast AI-adoption scenario, ranks nine real GBS finance roles with an explainable fit score and skills gap, and builds a roadmap: AI basics first, because nobody can adapt their work to AI without them, then reskilling without AI and with AI, from checked free courses, videos and articles.

What makes it different:

- **Numbers come from code, not the model.** The language model only reads CVs and explains results in plain words; every score is computed from stored, dated observations and shows its source.
- **The answer can change, in the open.** When new evidence arrives, Qart shows what would change in skill emphasis, scores and plan, and the person accepts or declines.
- **Honest about uncertainty.** Two scenarios, every number labelled observed, assumption or estimate, and a trend is projected only if it beats simple baselines in a backtest.
- **English and Malay.** Open models on a RunPod GPU match job titles in either language; Malay titles go from 0% to 75% top-1 accuracy compared with keyword search.

### Key Features

- **Profile intake** — synthetic CV upload (PDF, DOCX or TXT), form or questionnaire. Personal details are removed first, and every skill quotes the CV. Levels stay the person's own claims.
- **Live evidence layer** — seven registered public sources, collected daily by a Replit Scheduled deployment, each number with its source and date.
- **Ranked future roles** — nine GBS finance roles with a fit score that shows every point, an essential-skill check and a skills gap.
- **Reskilling roadmap** — three tracks with study hours and 33 courses, 48 videos and 41 articles, each checked by hand, plus a with/without-AI comparison.
- **SDG mapping** — every role, skill and step tagged to an SDG target, with how the chosen path contributes.
- **Two scenarios** — moderate and fast AI adoption, always labelled as estimates.
- **The person decides** — *What changed* proposes evidence updates to accept or decline; the CV updates as steps are done and downloads as PDF.

### Who it is for

Working adults in GBS finance and accounting roles at risk of displacement, fresh graduates and students (also through TVET and university career centres), and career switchers into GBS. An HR / L&D team view is planned for a later phase.

### Tech Stack

| Layer         | Technology |
| ------------- | ---------- |
| Frontend      | React 19, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend       | Python 3.12, FastAPI, Pydantic, SQLAlchemy Core |
| Database      | PostgreSQL on Replit; SQLite for local runs |
| AI / Compute  | OpenAI gpt-4o-mini (CV reading, plain-words explanations); RunPod Serverless GPU with BAAI/bge-m3 and bge-reranker-v2-m3 (job-title and skill matching) |
| Hosting / Dev | Replit Autoscale (web app and API) and Replit Scheduled (daily evidence pipeline) |

Every library, dataset and model, with its licence, is listed in [`docs/DECLARATION_LOG.md`](docs/DECLARATION_LOG.md).

---

## Project Structure

```
.
├── data/
│   ├── sources.yaml         # Registered evidence sources: terms, limits, cadence
│   ├── packs/gbs_fa/        # GBS finance field: roles, skills, tasks, resources, SDG targets
│   ├── samples/             # Synthetic sample CVs (Nur, Hafiz, Mei)
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
│   ├── match/               # Fit score, skills gap, scenarios, explanations
│   ├── pathway/             # Roadmap tracks and planner
│   ├── changes/             # Update proposals from new evidence
│   ├── cv/, goal/, journey/ # CV versions, a user's goal role, progress
│   ├── occupations/         # Any-occupation search across 1,016 occupations
│   ├── pipeline/run.py      # The scheduled run: python -m src.pipeline.run
│   ├── params.py            # Every threshold and weight, with its reason
│   └── db.py                # One database layer for SQLite and PostgreSQL
├── submission/              # Proposal, tools declaration, proof of use, pitch deck
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
          OpenAI gpt-4o-mini       RunPod Serverless GPU    Evidence pipeline
          CV → quoted claims;      BGE-M3 + reranker:       (Replit Scheduled)
          plain-words text         titles and tasks → skills       ▲
                                                              7 public sources
```

Every remote call has a time budget and a labelled fallback. The full diagram is Appendix A of [`submission/SDC2026_Qart.ai_TechDeclaration.pdf`](submission/SDC2026_Qart.ai_TechDeclaration.pdf); the modules are explained in [`docs/explain/`](docs/explain/ARCHITECTURE.md).

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
- **Scheduled pipeline:** a second Repl runs `python -m src.pipeline.run --trigger schedule` every day as a Replit Scheduled deployment against the same database, so evidence and run history keep updating even when nobody uses the app.
- **Secrets:** all keys live in Replit Secrets, never in the code.

📄 Proof of use: [`submission/REPLIT PROOF OF USE.pdf`](submission/REPLIT%20PROOF%20OF%20USE.pdf)

## How We Use RunPod *(Required)*

- **Workload:** GPU inference. A serverless worker serves two open models: `BAAI/bge-m3` (embeddings, MIT) and `BAAI/bge-reranker-v2-m3` (reranker, Apache-2.0). Nothing is trained.
- **Setup:** `runpod/handler.py` runs as a **RunPod Serverless Endpoint**, built from `runpod/Dockerfile` in this repository (queue-based, min workers 0, max 1).
- **Use in Qart.ai:** matching any job title, in English or Malay, to 1,016 occupations, and mapping a person's own words about their tasks to skills. Every call has a time budget and a labelled BM25 keyword fallback.
- **Result:** on 40 labelled job titles, top-1 accuracy is 72% with the models and 58% with keyword search alone; for Malay titles, 75% and 0% ([`docs/RUNPOD_EVAL.md`](docs/RUNPOD_EVAL.md)).

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
- **Matching in Malay.** Keyword search found 0% of Malay job titles. Moving matching to open multilingual models on a RunPod GPU raised it to 75%, and we measured it rather than assumed it.
- **Cold GPUs.** A serverless GPU can take about 20 seconds to start, so every call got a time budget and a visible keyword fallback; no page waits for it.
- **Trends that do not predict.** Our backtest found that no trend method beat a simple "no change" forecast for the occupation groups we follow, so Qart shows the observed history and does not project a trend, and says why.
- **Design for the user.** Walking through the app as users showed crowded pages and a plan that was hard to follow. We rebuilt the plan as a route with clear stops, made every question skippable, and kept the journey to about three minutes.

## Future Improvements

- [ ] Test with at least 10 real users: time to a plan and whether they can explain their top role
- [ ] Raise verified free-course coverage from 73% to 90% of required skills
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
- [x] Slide deck added in `submission/`
- [x] Demo video link added
- [x] Replit used, with proof of use in `submission/`
- [x] RunPod used, with proof of use in `submission/`
- [x] Preliminary proposal and Technical & Tools Declaration completed in `submission/`
- [x] "How to Run" steps verified
- [x] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
