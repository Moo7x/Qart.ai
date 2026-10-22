# Qart.ai

> From "who I am today" to "where I can be in the AI era", for people in Malaysia. Qart.ai keeps collecting dated public evidence on AI and the job market, turns it into task-level change and skill forecasts under more than one scenario, ranks real future roles with an explainable fit score and skills gap, and builds a reskilling pathway where every role, skill and step is tied to an SDG target. A visible on-screen agent opens the evidence, courses and job openings for you; you make the decisions.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | Your Team Name                              |
| **Team Domain**        | Domain 1: Aiversecity Future-Ready Workforce |
| **SDG Track (1–17)**   | SDG 4: Quality Education (targets 4.4, 4.3); SDG 8 (targets 8.2, 8.5) |
| **Team Leader**        | Leader Name                                 |
| **University**         | University Name(s)                          |
| **Number of Members**  | 2                                           |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/Moo7x/qart.ai               |
| Replit Project    | https://replit.com/@your-username/your-project |
| Live Demo         | https://your-project.replit.app                |
| RunPod Endpoint   | https://api.runpod.ai/v2/your-endpoint-id      |
| Slide Deck        | https://example.com/slides                     |
| Demo Video        | https://example.com/demo-video                 |

---

## Overview

### Problem

AI is changing which jobs exist faster than training programmes and skills frameworks can be updated. In Malaysia, workers do not know which AI-era skills to learn, employers cannot tell which roles to train people for, and learning pathways are static lists that are out of date when published (Domain 1 brief, Aiversecity).

### Solution

A continuous intelligence loop and a field-aware research agent collect dated evidence from public sources (DOSM labour statistics and job-ad insights, TalentCorp's GBS role study, the Anthropic Economic Index, taxonomies such as O*NET and ESCO). Code, not the language model, turns that evidence into:

1. task-level change for each role, keeping observed AI use, reported deployment, potential exposure and expert impact separate;
2. skill emphasis under two scenarios (moderate and fast AI adoption), labelled as estimates, with essential skills never lowered;
3. a ranked list of real future roles with an explainable fit score, an essential-skill gate and a three-column skills gap;
4. an ordered, week-by-week pathway of verified free or low-cost courses, each step tagged to the SDG target it contributes to.

When new evidence arrives, the system recomputes and proposes a revision with the full chain (evidence → task change → skill weight → score → step). The person decides.

### Who it is for

Working adults at risk of displacement, fresh graduates and students (also through TVET and university career centres), career switchers, and HR / L&D managers (aggregate team view only). The demo field with deep coverage is Malaysian Global Business Services (GBS), finance & accounting.

### Status

This branch is being rebuilt slice by slice to the design in [`docs/PLAN.md`](docs/PLAN.md). What works today: the app skeleton (`/api/health`) and the browser spikes for the on-screen agent (`/spikes/tabs.html`, `/spikes/speech.html`). Each slice adds a working, tested part of the journey.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | React 19, TypeScript, Vite, Tailwind CSS |
| Backend       | Python 3.12, FastAPI, Pydantic, SQLAlchemy Core |
| Database      | SQLite locally; PostgreSQL on Replit (`DATABASE_URL`) |
| AI / Compute  | OpenAI gpt-4o-mini (extraction, explanations, research agent, on-screen agent); RunPod Serverless GPU hosting BAAI/bge-m3 and bge-reranker-v2-m3 (skill mapping) |
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
├── src/
│   ├── app.py               # FastAPI app: API routes + built web app
│   ├── config.py            # Settings from environment variables
│   └── db.py                # One database layer for SQLite and PostgreSQL
├── submission/              # Required submission documents
├── tests/                   # pytest suite
├── web/                     # React frontend (web/public/spikes: browser checks)
├── .env.example             # Environment variable names (no values)
├── .replit                  # Replit run configuration
├── replit_start.sh          # Install, build the web app, start the server
├── requirements.txt         # Python dependencies (Python 3.12)
└── README.md
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [Replit Project](https://replit.com/@your-username/your-project), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab and add the variables listed in `.env.example` (`LLM_API_KEY`, `DATABASE_URL`, `QART_ADMIN_TOKEN`, optionally `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`).
3. Click **Run**. Replit runs `replit_start.sh`: it installs the Python packages, builds the web app and starts `uvicorn src.app:app` on port 8000.

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
- **Scheduled pipeline:** a Replit Scheduled Deployment runs the evidence pipeline so run history accumulates (from slice 1).
- **Secrets:** keys are stored in Replit Secrets, never in the code.

📄 Proof of use: [`submission/REPLIT PROOF OF USE.pdf`](submission/REPLIT%20PROOF%20OF%20USE.pdf)

## How We Use RunPod *(Required)*

- **Workload:** GPU inference. A serverless worker serves two open models: `BAAI/bge-m3` (embeddings, MIT) and `BAAI/bge-reranker-v2-m3` (reranker, Apache-2.0). Inference only; nothing is trained.
- **Setup:** `runpod/handler.py` is deployed as a **RunPod Serverless Endpoint**, built from `runpod/Dockerfile` (min workers 0, max 1).
- **Use in Qart.ai:** mapping a person's free-text experience to canonical skills before matching, with a time budget and a labelled BM25 fallback (slice 2).

📄 Proof of use: [`submission/RUNPOD PROOF OF USE.pdf`](submission/RUNPOD%20PROOF%20OF%20USE.pdf)

---

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Member Name | Role | [@username](https://github.com/username) |

---

## Submission Checklist

- [ ] Team name, domain and SDG track filled in
- [ ] Slide deck link added
- [ ] Demo video link added
- [ ] Replit used, with proof of use in `submission/`
- [ ] RunPod used, with proof of use in `submission/`
- [ ] Submission template completed in `submission/`
- [ ] "How to Run" steps verified
- [ ] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
