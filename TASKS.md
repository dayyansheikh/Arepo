# TASKS.md — Astrolabe

Legend: `[ ]` pending · `[~]` active · `[x]` done · `[!]` blocked
Owner: **O** = Opus lead (me) · **S#** = a Sonnet subagent · **RV** = independent Sonnet reviewer

## Active
- [~] O — Scaffold repo, domain contract, config, tracking files (this wave)
- [~] S-research — Confirm CLOB WebSocket protocol from primary docs (running)

## Pending — Phase 2–3 (spine + ingestion)
- [ ] O   — Typed domain models (`domain/models.py`, `enums.py`) — the shared contract
- [ ] O   — Config + structured logging + app skeleton + `/health`
- [ ] S1  — Gamma API async client + normalization (`clients/gamma.py`, `ingest/normalize.py`)
- [ ] S2  — CLOB REST async client (`clients/clob_rest.py`)
- [ ] S3  — CLOB WebSocket client: reconnect/resub/dedup/heartbeat/fallback (`clients/clob_ws.py`)
- [ ] RV  — Review S1/S2/S3 clients (independent Sonnet)

## Pending — Phase 4 (storage, cache, replay)
- [ ] S4  — Storage layer: SQLAlchemy async models + repository + cache (`storage/*`)
- [ ] O   — Deterministic replay dataset + player (`replay/*`) + seed script
- [ ] RV  — Review storage + replay

## Pending — Phase 5 (analytics — the quant core, Opus-owned)
- [ ] O   — implied probability, movement, rolling volatility, z-score
- [ ] O   — microstructure: midpoint, spread, imbalance, near-mid depth
- [ ] O   — composite anomaly score + confidence/data-quality
- [ ] O   — backtest (look-ahead-safe) over replay dataset
- [ ] S5  — Comprehensive analytics unit tests (fixtures) — reviewed by O
- [ ] RV  — Independent review of analytics correctness

## Pending — Phase 6 (API + frontend)
- [ ] S6  — FastAPI routes: overview, markets, market detail, signals, replay, meta/health
- [ ] S7  — Frontend design system + shell (Next.js/TS/Tailwind, tokens, layout, mode banner)
- [ ] S8  — Overview + Market explorer pages
- [ ] S9  — Market detail + Signal lab pages (charts)
- [ ] S10 — Replay/backtest page + Methodology page
- [ ] RV  — Review API + each frontend surface

## Pending — Phase 7–8 (resilience, integration, review)
- [ ] O   — End-to-end integration wiring (pipeline → storage → API → UI)
- [ ] S11 — Integration + e2e smoke test (one full user flow)
- [ ] O   — Personal verification pass: run all tests, lint, typecheck, boot app
- [ ] RV  — Full independent review sweep

## Pending — Phase 9 (deploy) — user-auth gated
- [ ] O   — Dockerfiles + docker-compose + Vercel/host configs (authored, inspect-validated)
- [!] O   — Execute `docker compose up` — BLOCKED: no Docker daemon in build env
- [!] O   — Public deployment + prod smoke test — BLOCKED: needs user hosting auth

## Pending — Phase 10 (docs, report, package)
- [ ] S12 — README + docs/{architecture,methodology,API,deployment,limitations}.md + Mermaid
- [ ] O   — docs/portfolio-report.md (5–7pp) → PDF
- [ ] O   — scripts/package_submission.sh (staging, exclusions, size gate <20MB)
- [ ] O   — FINAL_STATUS.md + 3-minute demo script + final ZIP

## Completed
- [x] O — Read CLAUDE.md + PROJECT_SPEC.md fully
- [x] O — Environment audit (Py3.11, Node20; no Docker/gh/vercel)
- [x] O — Verify Gamma + CLOB REST live schemas by direct request
- [x] O — Product naming + due-diligence → "Astrolabe"; DECISIONS.md, research-notes.md
- [x] O — Repo scaffold + directory tree
