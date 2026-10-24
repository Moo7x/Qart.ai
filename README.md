# Qart.ai

> Qart.ai shows finance workers and graduates in Malaysia which of their skills still count in the AI era, which future roles fit them, and a free learning route to get there, built on dated public evidence.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | Qart.ai                                      |
| **Team Domain**        | Domain 1: Aiversecity Future-Ready Workforce |
| **SDG Track (1–17)**   | SDG 4: Quality Education (targets 4.4, 4.3); SDG 8 (targets 8.2, 8.5) |
| **Team Leader**        | Kydyrgaliyev Meiirman                                |
| **University**         | Xiamen University Malaysia                         |
| **Number of Members**  | 2                                           |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/Moo7x/qart.ai               |
| Live Demo (Replit) | https://qartai.replit.app/start               |
| RunPod Endpoint   | Private serverless endpoint, called only by the server |
| Slide Deck        | https://example.com/slides                     |
| Demo Video        | https://example.com/demo-video                 |

---

## Overview

### Problem

AI is changing which jobs exist faster than training programmes and skills frameworks can be updated. In Malaysia, workers do not know which AI-era skills to learn, employers cannot tell which roles to train people for, and learning pathways are static lists that are out of date when published (Domain 1 brief, Aiversecity).

### Solution

Qart.ai reads a person's synthetic CV or short questionnaire into skill claims, each one quoting the CV. A daily pipeline collects dated public evidence on AI and the Malaysian job market, and code, not the language model, turns it into how much each skill matters under a moderate and a fast AI-adoption scenario. Nine real GBS finance roles are then ranked with an explainable fit score and skills gap, and the person gets a roadmap: AI basics first, then reskilling without AI and with AI, built from checked free courses, videos and articles. When new evidence arrives, Qart shows what would change, and the person accepts or declines.

### Key Features

- **Profile intake** — synthetic CV upload (PDF, DOCX or TXT), form or questionnaire. Personal details are removed first, and every skill quotes the CV.
- **Live evidence layer** — seven registered public sources checked daily; every number shows its source and date.
- **Ranked future roles** — a fit score with every point shown, an essential-skill check and a skills gap.
- **Reskilling roadmap** — three tracks with hours and free resources, plus a with/without-AI comparison.
- **SDG mapping** — every role, skill and step tagged to an SDG target, with how the path contributes.
- **Two scenarios** — moderate and fast AI adoption, always labelled as estimates.
- **The person decides** — new evidence proposes changes in *What changed*; CV updates are suggested and downloadable as PDF.

### Who it is for

Working adults at risk of displacement, fresh graduates and students (also through TVET and university career centres) and career switchers. The field with full coverage is Malaysian Global Business Services (GBS), finance & accounting; an HR / L&D team view is planned for a later phase.

### Status

Built slice by slice to [`docs/PLAN.md`](docs/PLAN.md) and deployed on Replit. Seven collectors
(OpenDOSM, DOSM job ads, Anthropic Economic Index, TalentCorp, O*NET 31.0, ILO exposure index,
MyCOL) feed an immutable evidence store, checked daily by a Replit Scheduled deployment. A person
starts from a synthetic CV, a form or a short questionnaire; nine GBS finance destination roles are
scored under two declared scenarios (moderate and fast AI adoption) with an explainable fit and
skills gap. The plan is a three-track roadmap (AI basics, then reskilling without AI and with AI)
built from 33 verified free courses, 48 videos and 41 articles, with a with/without-AI comparison
and SDG targets on every step. **What changed** shows how new or replayed evidence would change
emphasis, scores and pathway; the person accepts or declines, and their skill claims and destination
never change on their own.

Scope limits: AI-use scenario shifts and course gains are assumptions, not trained adoption or
learning-outcome forecasts. Ten of the 37 skills the destination roles need have no verified free
course yet (videos or articles only). Full pathways cover GBS finance and accounting only; other
occupations show evidence without a plan. Research agent, HR team view, Telegram and what-if
planning are deferred. See [architecture](docs/explain/ARCHITECTURE.md),
[journey](docs/explain/journey.md), [changes](docs/explain/changes.md) and
[baseline validation](docs/BASELINE_CHECK.md).

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | React 19, TypeScript, Vite, Tailwind CSS |
| Backend       | Python 3.12, FastAPI, Pydantic, SQLAlchemy Core |
| Database      | SQLite locally; PostgreSQL on Replit (`DATABASE_URL`) |
| AI / Compute  | OpenAI gpt-4o-mini (CV extraction, plain-language explanations); RunPod Serverless GPU hosting BAAI/bge-m3 and bge-reranker-v2-m3 (skill mapping) |
| Hosting / Dev | Replit (app, database, scheduled pipeline runs) |

All libraries, datasets and models, with licences, are listed in [`docs/DECLARATION_LOG.md`](docs/DECLARATION_LOG.md).

---

## Project Structure

```
.
├── docs/
│   ├── PLAN.md              # Product and system design
│   ├── DECLARATION_LOG.md   # Tools, data, models and licences
│   └── decision_log.md      # Decisions and scope changes
├── runpod/                  # RunPod serverless worker (handler.py, Dockerfile)
├── data/
│   ├── sources.yaml         # Registered evidence sources: terms, limits, cadence
│   └── packs/gbs_fa/        # GBS finance field profile and the TalentCorp extraction
├── src/
│   ├── app.py               # FastAPI app: API routes + built web app
│   ├── api/                 # HTTP routes (evidence, pipeline)
│   ├── collectors/          # One collector per registered source
│   ├── evidence/            # Store, measures, labelled signals, registry
│   ├── pipeline/run.py      # The scheduled run: python -m src.pipeline.run
│   ├── params.py            # Declared thresholds, each with its reason
│   ├── config.py            # Settings from environment variables
│   └── db.py                # One database layer for SQLite and PostgreSQL
├── submission/              # Required submission documents
├── tests/                   # pytest suite
├── web/                     # React frontend (web/public/spikes: browser checks)
├── .env.example             # Environment variable names (no values)
├── .replit                  # Replit run configuration
├── replit_build.sh          # Install Python packages and build the web app
├── replit_serve.sh          # Start the server (a deployment's run step)
├── replit_start.sh          # Run button: build, then serve
├── requirements.txt         # Python dependencies (Python 3.12)
└── README.md
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [Replit Project](https://replit.com/@your-username/your-project), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab and add the variables listed in `.env.example` (`LLM_API_KEY`, `DATABASE_URL`, `QART_ADMIN_TOKEN`, optionally `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`).
3. Click **Run**. Replit runs `replit_start.sh`: it installs the Python packages, builds the web app and starts `uvicorn src.app:app` on port 8000.
4. To publish, choose an **Autoscale** deployment. `.replit` builds once (`replit_build.sh`) and then only starts the server (`replit_serve.sh`), so it answers Replit's health check on `/` within seconds.
5. For the daily evidence run, import the same repository into a second Repl, add the production database's `DATABASE_URL` and the API keys to its Secrets plus `QART_DEPLOY_ROLE=pipeline`, and publish it as a **Scheduled** deployment. The same `replit_serve.sh` then runs the pipeline once per schedule instead of starting the server.

Without the LLM or RunPod keys the app still runs; `/api/health` shows which parts use a labelled fallback.

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

- **Hosting:** the FastAPI app and the built React frontend run as one Replit app.
- **Database:** Replit PostgreSQL (`DATABASE_URL`); local runs use SQLite.
- **Scheduled pipeline:** a Replit Scheduled Deployment runs `python -m src.pipeline.run --trigger schedule` daily against the same database, so run history accumulates even when nobody uses the app.
- **Secrets:** keys are stored in Replit Secrets, never in the code.

📄 Proof of use: [`submission/REPLIT PROOF OF USE.pdf`](submission/REPLIT%20PROOF%20OF%20USE.pdf)

## How We Use RunPod *(Required)*

- **Workload:** GPU inference. A serverless worker serves two open models: `BAAI/bge-m3` (embeddings, MIT) and `BAAI/bge-reranker-v2-m3` (reranker, Apache-2.0). Inference only; nothing is trained.
- **Setup:** `runpod/handler.py` is deployed as a **RunPod Serverless Endpoint**, built from `runpod/Dockerfile` (min workers 0, max 1).
- **Use in Qart.ai:** matching any job title, in English or Malay, to 1,016 occupations, and mapping a person's free-text tasks to canonical skills before matching. Every call has a time budget and a labelled BM25 fallback. On 40 labelled titles, top-1 accuracy is 72% with the models and 58% with BM25 alone (Malay titles: 75% and 0%).

📄 Proof of use: [`submission/RUNPOD PROOF OF USE.pdf`](submission/RUNPOD%20PROOF%20OF%20USE.pdf)

---

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Kydyrgaliyev Meiirman | Team leader · planning and idea · frontend and UI | [@kydyrgaliyevm](https://github.com/kydyrgaliyevm) |
| Mounir Ben Hassine | Planning and idea · backend, data pipeline and deployment | [@Moo7x](https://github.com/Moo7x) |

Both members iterated on the frontend and backend together once the first working version was in place.

---

## Submission Checklist

- [x] Team name, domain and SDG track filled in
- [ ] Slide deck link added
- [ ] Demo video link added
- [x] Replit used, with proof of use in `submission/`
- [x] RunPod used, with proof of use in `submission/`
- [x] Submission template and Technical & Tools Declaration completed in `submission/`
- [ ] "How to Run" steps verified
- [x] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
