# DECISIONS.md — Astrolabe / Arepo

An append-only log of significant engineering and product decisions, with reasoning.
Newest entries at the top of each section.

---

## Arepo redesign (branch `arepo-redesign`, from tag `astrolabe-baseline`)

### R7. Light-only identity; inherited auto dark-mode dropped
Every design reference and the brand brief are light-first (red on a warm-white
ground). To keep the identity calm, consistent and credible, Arepo commits to a
single light theme and removes the baseline's `prefers-color-scheme: dark`
overrides. Dark mode was a cosmetic feature, not core functionality or a data
mode, so this preserves the "all functionality and data modes" requirement while
matching every reference exactly.

### R6. Richer Markets filters are client-side over existing fields
The backend `/api/markets` supports `search`, `category`, `status`, `sort` only.
The brief's additional guided filters (signal-strength range, probability range,
time-to-close, sport/competition where present) are implemented **client-side**
over fields already on `MarketCard`, with honest empty states — no backend change,
per "do not alter backend behaviour". Sport/competition are shown only when the
data carries them; the UI never implies all markets have sports metadata.

### R5. Maths via KaTeX
Equations render with KaTeX (added as a frontend dep), not hand-rolled fraction
markup. Guarantees correct fractions, superscripts/subscripts, Greek and aligned
equations, per the brief's "never display equations as programming text".

### R4. Typography — Geist Sans via next/font, Inter fallback
Per brief preference order. Geist Mono for raw identifiers only. Tabular numerals
on all data.

### R3. Brand direction — modernist restraint, softened
Of the three `_ds` bundles, **modernist** (red-on-white, flat, disciplined) is the
closest to the brief and the primary influence; **industry** and **broadsheet**
are rejected. Modernist's zero-radius / heavy-2px-rule aesthetic is softened to the
brief's restrained radius, subtler borders and calmer spacing. See
`docs/design-reference-audit.md`.

### R2. Accent red `#E50C0E`, used sparingly
Single accent for active nav, primary actions, selected controls and key signals
only. Never carries meaning alone (up/down/good/bad always pair colour with a
sign, arrow or word). Chart primary series = Arepo red; comparison series = neutral
slate. See `docs/brand-system.md`.

### R1. Product rename Astrolabe → Arepo (user-facing only)
User-facing surfaces (nav, titles, metadata, README, report, logo, favicon,
copy) become **Arepo**. Internal Python packages, DB identifiers and API paths keep
`astrolabe` — renaming coupled internals is cosmetic risk with no user benefit, per
the brief. Brand meaning is the Sator-Square connective word; full paragraph in
`docs/brand-system.md`.

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
