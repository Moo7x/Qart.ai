# Qart.ai

> A practice companion a company deploys so finance employees learn to review AI-prepared work. Their mistakes and successes become evidence of skill, which drives explainable future-role matching and a time-budgeted learning path: training people as AI changes the work, rather than replacing them.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | Your Team Name                              |
| **Team Domain**        | Domain 1: Aiversecity Future-Ready Workforce |
| **SDG Track (1–17)**   | SDG 4: Quality Education (target 4.4); related SDG 8 targets 8.2 and 8.5 |
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

AI now prepares routine finance work such as bank reconciliations, so the job of the people who did it shifts from doing the work to checking it. Companies need to know who can already review AI output safely and how to retrain the rest. Today that is judged by self-assessment or job titles, and staff in at-risk roles are often let go instead of retrained.

### Solution

Employees review realistic, AI-prepared reconciliations that contain planted errors (or none). A companion helps in steps (a question, a hint, an explanation, the answer), and how much help was needed is recorded as evidence. The engine turns that evidence into skill states with reasons, matches people to future internal roles using dated public data on how AI is used at work plus the company's own adoption assumptions, and plans a learning path that fits their weekly hours. The system recommends; people decide.

### Key Features

- **Practice with stepped help:** a companion (LLM with deterministic checking tools) asks a question first, then hints, and only shows the answer last. A wrong decision is held back while the employee keeps looking, without revealing the answer.
- **Evidence, not scores:** skills move from self-reported to insufficient evidence, observed with help, and demonstrated independently (two no-help successes on different cases in separate sessions). Each state shows why and the cases behind it. No mastery percentages.
- **Mistakes drive the next case:** the next case targets the employee's latest mistake, then a no-help check-in confirms it.
- **Explainable future roles:** each role is built on cited O*NET tasks. Each task is allocated to AI or the human under two company scenarios (assistive, agentic), and a shift rule moves weight from execution to oversight skills. Every number is labelled as evidence (dated source), assumption (company layer) or synthetic.
- **Updated external evidence:** a newer Anthropic Economic Index snapshot produces a diff and suggested assumption reviews. HR approves a new assumption version, and rankings and role outlooks update with "changed since" reasons. Data alone never changes weights.
- **Learning path:** verified courses and practice within the weekly time budget, robust across both scenarios, preferring free resources (greedy planner; OR-Tools CP-SAT version for comparison).
- **HR view with privacy:** aggregates only; groups and cells under 5 people are suppressed.
- **Honest evaluation:** fixed, hashed acceptance criteria; the companion is compared with a text-only LLM baseline; counts are reported as measured (`eval/RESULTS.md`).

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | React 19, TypeScript, Vite, Tailwind CSS |
| Backend       | Python 3.12, FastAPI, Pydantic |
| Database      | SQLite locally; PostgreSQL on Replit (`DATABASE_URL`) |
| AI / Compute  | OpenAI-compatible LLM (gpt-4o-mini) for the companion; RunPod Serverless GPU hosting BAAI/bge-m3 and bge-reranker-v2-m3 for search; OR-Tools for path planning |
| Data          | O*NET 31.0 (CC BY 4.0), Anthropic Economic Index (CC-BY), synthetic cases and team |
| Hosting / Dev | Replit                       |

All libraries, datasets and models, with licences, are listed in [`docs/DECLARATION_LOG.md`](docs/DECLARATION_LOG.md).

---

## Project Structure

```
.
├── catalogue/               # Skills, roles (O*NET-based), courses, company assumptions, SDG map
├── cases/                   # Synthetic practice and check-in cases (with ground truth)
├── data/                    # Snapshots, synthetic team, processed O*NET tasks (data/raw not committed)
├── docs/
│   ├── explain/             # One plain-language explanation per module
│   ├── DECLARATION_LOG.md   # Tools, data, models and licences
│   └── decision_log.md      # Decisions and scope changes
├── eval/                    # Acceptance criteria, runner, baseline, retrieval and engine checks
├── runpod/                  # RunPod serverless worker (handler.py, Dockerfile)
├── schemas/                 # JSON contract examples
├── src/
│   ├── main.py              # FastAPI app: API routes + built web app
│   ├── api_engine.py        # Engine routes (profile, skills, events, recommendations, path, HR, ...)
│   ├── api_companion.py     # Case and companion routes
│   ├── contract.py          # Pydantic contract models
│   ├── store.py             # SQLite / PostgreSQL store
│   ├── companion/           # Companion agent, checking tools, grader, automatic diagnosis, playbooks
│   ├── engine/              # Evidence rules, requirement cards, recommender, planners, snapshots, HR
│   └── retrieval/           # BM25, hybrid fusion, RunPod embedding and reranking clients
├── submission/              # Required submission documents
├── tests/                   # pytest suite
├── web/                     # React frontend
├── .env.example             # Environment variable names (no values)
├── .replit                  # Replit run configuration
├── replit_start.sh          # Install, build the web app, start the server
├── requirements.txt         # Python dependencies (Python 3.12)
└── README.md
```

### Architecture

```
Browser (React) ──► FastAPI on Replit ──┬──► Engine: evidence rules → recommender → path planner
                                        ├──► Companion ──► LLM API (stepped help, diagnosis)
                                        ├──► Store: SQLite / PostgreSQL
                                        └──► RunPod Serverless (BGE-M3 embeddings + reranker)
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [Replit Project](https://replit.com/@your-username/your-project), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab (🔒) and add the variables listed in `.env.example`:
   - `LLM_API_KEY` (and optionally `LLM_MODEL`, default `gpt-4o-mini`; `LLM_BASE_URL` for another OpenAI-compatible provider)
   - `DATABASE_URL` for the deployed app (Replit PostgreSQL); without it the app uses SQLite
   - `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` for GPU search
3. Click **Run**. Replit runs `replit_start.sh`: it installs the Python packages, builds the web app and starts `uvicorn src.main:app` on port 8000.

Without `LLM_API_KEY` the app still runs: the companion falls back to deterministic replies built from the checking tools.

### Option 2 — Run Locally

Requires Python 3.12 and Node.js 20.

```bash
# 1. Clone the repository
git clone https://github.com/Moo7x/qart.ai.git
cd qart.ai

# 2. Create and activate a virtual environment with Python 3.12
python3.12 -m venv .venv        # Windows: py -3.12 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env            # then fill in your values

# 5. Build the web app
cd web && npm ci && npm run build && cd ..

# 6. Run the app, then open http://localhost:8000
uvicorn src.main:app --port 8000
```

`POST /api/demo/reset` restores the synthetic demo state (persona Aina, first snapshot, assumptions v1).

### Run Tests

```bash
python -m pytest
```

The tests never call paid services. Code checks: `ruff check .` and `mypy src eval`. Evaluation: `python -m eval.runner` (writes `eval/RESULTS.md`; LLM rows need `LLM_API_KEY`).

---

## How We Use Replit *(Required)*

- **Hosting:** the FastAPI app and the built React frontend run as one Replit app, deployed with Replit Deployments at the Live Demo link above.
- **Database:** the deployed app stores profiles, events and assumption versions in Replit PostgreSQL (`DATABASE_URL`); local runs use SQLite.
- **Secrets:** the LLM and RunPod keys are stored in Replit Secrets, never in the code.

📄 Proof of use: [`submission/REPLIT PROOF OF USE.pdf`](submission/REPLIT%20PROOF%20OF%20USE.pdf)

## How We Use RunPod *(Required)*

- **Workload:** GPU inference for search. A serverless worker serves two open models: `BAAI/bge-m3` (embeddings, MIT) and `BAAI/bge-reranker-v2-m3` (reranker, Apache-2.0). Inference only; nothing is trained.
- **Setup:** `runpod/handler.py` is deployed as a **RunPod Serverless Endpoint**, built from `runpod/Dockerfile` (min workers 0, max 1, so it costs nothing while idle).
- **Integration:** `src/retrieval/runpod_backends.py` calls the endpoint with `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`. Hybrid search (BM25 + embeddings with reciprocal-rank fusion, then reranking) runs over the course catalogue and O*NET tasks. `python -m eval.retrieval_eval` measures recall@5 against the BM25 baseline. Using hybrid search inside the app's path planner and companion is in progress.

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

- **Keeping evidence honest.** An early version showed the full answer right after a wrong decision, while still recording that the employee found it "after a hint". Help shown and help recorded now always match, and tests check it.
- **Measuring instead of claiming.** On our fixed acceptance set, a text-only LLM baseline currently makes more correct decisions than our companion (14/17 vs 6/17). The cause is the companion's checking procedure, which escalates errors it could correct. We report this as measured and improve the procedure on separate development cases.
- **Separating evidence from assumptions.** Public data on AI use describes usage, not job loss. We keep dated external data, company assumptions and synthetic data apart and label every number.
- **Integrating two people's work** through a shared JSON contract, with an end-to-end test of the main user journey after every merge.

## Future Improvements

- [ ] Playbook optimiser: propose improvements to the companion's checking procedure, measured on development cases and activated only after a senior approves, with rollback
- [ ] Use hybrid search inside the learning path and the companion, with cited passages
- [ ] More dated trend data (all Anthropic Economic Index releases, Indeed Hiring Lab AI tracker) for trends over time
- [ ] More case types and roles beyond bank reconciliation

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Member Name | Engine, data, evaluation, RunPod | [@username](https://github.com/username) |
| Member Name | Companion, cases, web app | [@username](https://github.com/username) |

---

## Submission Checklist

- [ ] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [ ] Slide deck link added
- [ ] Demo video link added
- [ ] Replit used, with proof of use in `submission/`
- [ ] RunPod used, with proof of use in `submission/`
- [ ] Submission template completed in `submission/`
- [ ] "How to Run" steps verified
- [ ] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
