# DECISIONS.md — Astrolabe

An append-only log of significant engineering and product decisions, with reasoning.
Newest entries at the top of each section.

---

## D0. Product name and identity

**Decision:** The product is named **Astrolabe**.

**Rationale:**
- An astrolabe is a historical instrument used to *measure the position of celestial
  bodies and to navigate* — a precise, honest metaphor for this project, which fixes a
  prediction market's "position" from its order book and price motion and flags when the
  readings are anomalous. It is an *instrument for reading markets*, not a trading venue.
- Naming due-diligence (web search, 2026-08-02): "Astrolabe" is **not** strongly associated
  with any existing financial, trading or analytics product. Search returns only an
  aerospace company ("Astrolabe Inc", different industry) and unrelated financial-astrology
  apps (which do not use the name). This satisfies the spec requirement to avoid names tied
  to existing financial/trading/analytics products and to avoid confusing similarity.
- Rejected alternatives:
  - **Sextant** — already used by multiple financial firms (Sextant asset-management funds,
    Sextant Capital Solutions). Too close to the finance space.
  - **Plumbline** — muddy; used by consulting / trades-services companies.
  - **Bellwether / Meridian / Vantage / Parallax** — either generic finance terms or tied to
    existing funds/firms (e.g. Parallax Volatility Advisers).
- Identity is intentionally lightweight per the spec ("polished but efficient"): a single
  wordmark, a compact instrument-inspired glyph, one restrained palette, one type pairing.
  See `docs/architecture.md` (design language) and the frontend design tokens.

**Independence:** This is an original codebase built from first principles. It does not
reference, continue, fork or reproduce any prior prediction-market project, and the forbidden
name ("Ripple") appears nowhere in the product, code, docs, branding or wording.

---

## Architecture decisions

### A5. No Docker daemon / no deploy CLI in the build environment
The build machine has **no Docker daemon** and **no `gh`/`vercel` CLI** installed, and no
authenticated hosting account. Consequence: Dockerfiles and `docker-compose.yml` are authored
to spec and validated by inspection, but **`docker compose up` is not executed here**; public
deployment is prepared (configs + docs) but **not performed** — it requires the user's own
hosting authentication, which is an explicit stop-boundary per CLAUDE.md. All status docs state
this truthfully. Local run is verified via the non-Docker path (uvicorn + `next dev`).

### A4. Deterministic replay via a committed dataset + injectable clock
Replay reads a small, version-controlled JSON dataset and drives the *same* analytics code as
live mode through an injectable clock/sequence source. This proves the analytics are pure and
makes backtests reproducible and look-ahead-safe (evaluation data is strictly separated from
signal-generation data by timestamp).

### A3. Three explicit data modes as a first-class enum
`LIVE`, `CACHED`, `REPLAY` are modeled as a domain enum surfaced on every API response envelope
alongside REST state, WebSocket state, last-successful-update and data age. The UI can never
silently present cached/replay data as live because the mode travels with the data.

### A2. Anti-corruption layer: raw third-party JSON never reaches the frontend
Gamma/CLOB responses are normalized into typed Pydantic domain models at the ingestion
boundary (`ingest/normalize.py`). The FastAPI layer serializes only internal domain/API models.
Rationale: Polymarket returns JSON-encoded strings for structured fields (e.g. `outcomes`,
`outcomePrices`, `clobTokenIds` are strings containing JSON arrays; prices/sizes are strings),
schemas drift, and fields are frequently missing — all of which must be absorbed and validated
in one place, not leaked to clients.

### A1. Async Python backend (FastAPI) + Next.js/TS frontend, SQLite→Postgres
Matches the recommended stack. `httpx.AsyncClient` for REST, `websockets` for the CLOB market
channel, SQLAlchemy (async) over SQLite locally with a Postgres-compatible URL for deployment.
Analytics use NumPy/pandas; SciPy only where a specific function justifies it.

_Environment note:_ Python 3.11.2 is used (spec allows "3.12 or another currently supported
version"; 3.11 is current and supported). Node 20 LTS for the frontend.
