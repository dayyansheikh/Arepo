# TASKS.md — Astrolabe / Arepo

Legend: `[x]` done · `[ ]` todo · `[~]` in progress · `[!]` blocked (external).
See `FINAL_STATUS.md` for the authoritative state.

## Arepo redesign (branch `arepo-redesign`)

### Phase 1 — foundation & audit
- [x] Confirm clean tree; branch `arepo-redesign`; tag `astrolabe-baseline` (pre-existing)
- [x] Record baseline: frontend tsc/lint/build clean; backend 128 tests pass, ruff clean
- [x] Inspect every `design-references/` file (7 HTML + 3 `_ds` bundles + 4 PNGs)
- [x] `docs/design-reference-audit.md` (adopt / adapt / reject)
- [x] `docs/brand-system.md` (name, logo decision, type, palette, tokens, a11y)
- [x] Redesign decisions logged in `DECISIONS.md` (R1–R7)

### Phase 2 — design system & shell
- [x] Design tokens (globals.css vars + tailwind), Geist font, metadata rename
- [x] Arepo logo + favicon; TopBar/nav; ModeSelector; Footer; DisclaimerBanner
- [x] Shared primitives: Card, Button, Badge, MetricHelp, StatTile, StrengthMeter,
      Select, Slider, Disclose, Equation (KaTeX)

### Phase 3 — education & maths
- [x] `How Arepo Works` page; rebuild `Methodology` with KaTeX + full anchors
- [x] Wire MetricHelp across all metrics to Methodology anchors

### Phase 4 — Overview & Markets redesign
### Phase 5 — Market detail & Signal Lab redesign
### Phase 6 — Replay & data-mode controls
### Phase 7 — QA gauntlet
- [x] Responsive + a11y review; visual review vs references; cross-browser smoke
- [x] lint / typecheck / build / backend tests; independent review; repairs
- [x] Deliverables: screenshots, README, portfolio report, ZIP, FINAL_STATUS, changelog

---

## Baseline (original Astrolabe build) — Completed
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
