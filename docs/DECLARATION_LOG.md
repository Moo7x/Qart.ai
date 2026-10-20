# Declaration log (feeds the Technical & Tools Declaration)

| Date | Category | Name & version | Purpose in Qart.ai | Licence / terms | Access tier | Added by |
|---|---|---|---|---|---|---|
| 2026-10-21 | template | SDC Hackathon Submission Template (organisers) | Repo starting point | Apache-2.0 (LICENSE) | provided | team |
| 2026-10-21 | AI dev tool | Claude Code | Coding assistance (reviewed by the team) | Anthropic terms | personal subscription | Person A |
| 2026-10-21 | AI dev tool | obra/superpowers skills (TDD, systematic debugging, verification, code review, finishing a branch), installed as personal Claude Code skills, not in the repo | Development workflow guidance for the coding agent | MIT | free | Person A |
| 2026-10-21 | framework | FastAPI 0.155.0 (+ Starlette) | HTTP API for engine and companion routes | MIT (Starlette BSD-3) | free / open source | Person A |
| 2026-10-21 | library | Uvicorn 0.54.0 | ASGI server (Replit run command) | BSD-3-Clause | free / open source | Person A |
| 2026-10-21 | library | Pydantic 2.14.1 | Contract models (src/contract.py), request validation | MIT | free / open source | Person A |
| 2026-10-21 | library | pandas 3.0.6 | Filtering the Anthropic Economic Index CSV into snapshots | BSD-3-Clause | free / open source | Person A |
| 2026-10-21 | library | Google OR-Tools 9.15 | Optional CP-SAT version of the path planner | Apache-2.0 | free / open source | Person A |
| 2026-10-21 | library | runpod 1.12.0 | RunPod serverless handler (template) | MIT | free / open source | Person A |
| 2026-10-21 | library (dev) | pytest 9.1.1, httpx 0.28.1 | Unit and API tests (FastAPI TestClient) | MIT / BSD-3-Clause | free / open source | Person A |
| 2026-10-21 | library (dev) | ruff 0.17.1, mypy 2.4.0, pandas-stubs | Lint, format and type checking | MIT / MIT / BSD-3-Clause | free / open source | Person A |
| 2026-10-21 | dataset | O*NET 31.0 Database / O*NET OnLine (occupations 43-3031.00, 13-2051.00, 13-2011.00, 13-1041.00, 13-2031.00): task statements copied verbatim into catalogue/roles.json | Basis for internal roles and their tasks | CC BY 4.0 (USDOL/ETA); attribution in roles.json | free / public | Person A |
| 2026-10-21 | external resource (links only) | Free learning resources in catalogue/courses.json: Kaggle Learn, SQLBolt, OTexts (FPP3), OpenLearn (The Open University), Alison, Microsoft Learn, Microsoft Support, Anthropic Academy, Elements of AI, Coursera (IIA COSO) | Path planner recommendations; we only link, no content is copied | each provider's terms; URLs opened 2026-10-21 | free (one item: free access unconfirmed, verified=false) | Person A |
| 2026-10-21 | reference | UN SDG goal pages 4 and 8 (sdgs.un.org) | SDG target titles (paraphrased) in catalogue/sdg_map.json | UN terms of use | free / public | Person A |
| 2026-10-21 | dataset | Anthropic Economic Index, release_2026_06_26, file aei_claude_ai_2026-06-26.csv (Hugging Face Anthropic/EconomicIndex) | Layer-A trend snapshots (Apr and May 2026, GLOBAL + MYS, finance SOC occupations); raw file kept in gitignored data/raw/, only derived snapshots committed | Data CC-BY (attribution required; in every snapshot), code MIT. Aggregated usage statistics, no personal data | free / public | Person A |
