# TASKS.md — Astrolabe

Legend: `[x]` done · `[!]` blocked (external). See `FINAL_STATUS.md` for the authoritative state.

## Completed
- [x] Research (Gamma/CLOB/WS confirmed from primary sources) + naming (Astrolabe) + tracking docs
- [x] Repo scaffold, typed domain contract, config, structured logging, FastAPI spine + /health
- [x] Gamma + CLOB REST clients + anti-corruption normalization (verified on live data)
- [x] CLOB WebSocket client (reconnect/dedup/heartbeat/DEGRADED) + tests
- [x] Storage (async SQLAlchemy, SQLite/Postgres) + repository + cache + tests
- [x] Analytics core (implied, movement, volatility, z-score, microstructure, quality, anomaly)
      — Opus-owned, hand-derived test values
- [x] Deterministic replay dataset + player + look-ahead-safe backtest
- [x] Service brain (live/cached/replay + fallback, DataStatus never mislabels mode)
- [x] Ingestion pipeline (Gamma→CLOB→storage) — real ingest verified
- [x] FastAPI routes (overview/markets/detail/signals/status/meta/replay) + real uvicorn boot
- [x] Next.js/TS/Tailwind frontend (6 surfaces, mode chip, charts) — built + browser-verified
- [x] Independent adversarial review → 4 real defects fixed + regression-tested
- [x] 3 frontend integration bugs found via browser smoke test + fixed
- [x] Docker + compose + deployment configs (authored; compose YAML validated)
- [x] Docs set (README, architecture, methodology, API, deployment, limitations) + Mermaid
- [x] Portfolio report (md) + PDF (5 pages) + build_report_pdf.py
- [x] Packaging script → clean 0.75 MB ZIP (<20 MB; exclusions + secret scan enforced)
- [x] FINAL_STATUS.md + 3-minute demo script + screenshots

## Blocked (external authorization only — per stop-boundary)
- [!] `docker compose up` — no Docker daemon in build environment
- [!] Public deployment + production smoke test — requires the user's hosting account auth
