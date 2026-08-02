# FINAL_STATUS — Astrolabe

_Truthful final status of the project. Every claim below was verified by running the code._

## Project summary

**Astrolabe** is a read-only prediction-market intelligence platform over public Polymarket
data. It ingests market discovery + order-book data (Gamma API, CLOB REST, CLOB market
WebSocket), normalises it through a strict typed boundary, computes transparent microstructure
and time-series analytics (implied probability, movement, rolling volatility, standardised
z-score, spread/midpoint, order-book imbalance, near-mid depth, a composite anomaly score with
confidence/data-quality), and serves them via a FastAPI backend to a Next.js/TypeScript
frontend. It has three explicit data modes — **live**, **cached**, **replay** — and a
deterministic, look-ahead-safe backtest over a committed synthetic dataset. It never places
trades and makes no profitability claim.

## Verified implemented features

- **Live discovery + order-book analytics against real Polymarket** — verified in the browser:
  real current markets (e.g. 2028-election markets, $40M+ volumes), real books, spreads,
  order-book imbalance, z-scores over ~145 real price-history points, composite anomaly signals.
- **Cached mode** — a real ingestion cycle (`scripts/ingest.py`) discovered 7 markets and
  stored 14 order-book snapshots; the API served them labelled `CACHED` with correct
  midpoint/spread. Verified.
- **Deterministic replay mode** — committed dataset (3 markets, 144 frames); the app runs fully
  offline in replay.
- **Look-ahead-safe backtest** — signal on frames 0..i, evaluation on i+1..i+H; on the default
  dataset: sample 16, hit-rate 0.625, false-positive-rate 0.125 (synthetic data — illustrative,
  not a profitability claim).
- **Frontend** — 6 surfaces (Overview, Markets, Market detail, Signal Lab, Replay/Backtest,
  Methodology), always-visible data-mode + health chip, degradation banner, price-history chart,
  explainable signals with component breakdowns. All verified rendering against the live backend.
- **Resilience** — typed upstream error hierarchy (no raw httpx/JSON errors escape), bounded
  retry/backoff, 404→benign NotFound, WebSocket reconnect/dedup/heartbeat/DEGRADED signalling,
  live→cached→replay fallback with a truthful `DataStatus` envelope.

## Exact local start command

**One command (Docker — authored, not executed here, no daemon in build env):**
```bash
docker compose up --build
```

**Non-Docker (verified path):**
```bash
# Backend  (terminal 1)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn astrolabe.api.app:app --reload            # -> http://localhost:8000

# Frontend (terminal 2)
cd frontend && npm install && npm run dev          # -> http://localhost:3000
```

## Localhost addresses
- Frontend: `http://localhost:3000`  (defaults to **replay** mode; switch to Live/Cached in the top bar)
- Backend API: `http://localhost:8000`  · OpenAPI docs: `http://localhost:8000/docs` · health: `/health`

## Public URLs
- **None — not deployed.** Public deployment requires the operator's hosting account
  authentication (an external step this build environment could not perform). Deployment
  configuration and instructions are in `docs/deployment.md`.

## Test commands and ACTUAL results

```bash
cd backend && source .venv/bin/activate
python -m pytest -q            # -> 128 passed
ruff check astrolabe tests scripts   # -> All checks passed!
```
```bash
cd frontend
npm run lint                   # -> No ESLint warnings or errors
npx tsc --noEmit               # -> clean (no type errors)
npm run build                  # -> Compiled successfully (7 routes)
```
Backend: **128 tests pass**, ruff clean. Frontend: **lint + typecheck + production build pass.**

## Build results
- Backend imports and boots (`uvicorn`); `/health` and all `/api/*` endpoints return 200
  (verified against a running server).
- Frontend `next build` succeeds: routes `/`, `/markets`, `/markets/[id]`, `/signals`,
  `/replay`, `/methodology`.

## Live-data status
- **Working.** Gamma discovery + CLOB REST order-book/price-history verified against the live
  public APIs (no credentials). The CLOB market WebSocket client is implemented and unit-tested
  (reconnect/dedup/heartbeat/DEGRADED); it is used for the live-update path and the ingestion
  pipeline. WebSocket behaviour is covered by tests rather than a long-lived live capture.

## Known limitations (see `docs/limitations.md`)
- Implied probabilities are spread/fee-contaminated risk-neutral estimates, not forecasts.
- Signals are screening heuristics — not insider-trading evidence, not profitability, not alpha.
- Backtest uses a synthetic deterministic dataset; results are illustrative only (no survivorship
  correction, no transaction costs).
- Per-token historical volume is not available from the public CLOB, so the volume-acceleration
  component uses limited inputs in live mode; spread-change/depth-change components require a
  trailing book history only available in the backtest path.
- Docker startup and public deployment were **not executed** in the build environment.

## Report
- Markdown: `docs/portfolio-report.md`  ·  PDF: `docs/portfolio-report.pdf`
  (regenerate with `python scripts/build_report_pdf.py`; needs `pip install markdown xhtml2pdf`).

## Submission ZIP
- Path: `Dayyan-Sheikh-Prediction-Market-Project.zip`  ·  Size: **~0.75 MB** (well under 20 MB).
- Regenerate with `bash scripts/package_submission.sh` (stages a clean copy, validates
  exclusions, scans for secrets, enforces the 20 MB cap).

## Truthful application wording
> An independently developed, read-only prediction-market intelligence platform using live
> Polymarket public data, event-driven ingestion, order-book microstructure analysis,
> transparent anomaly detection with confidence scoring, and deterministic look-ahead-safe
> historical replay. It does not place trades and makes no profitability claim.

---

## Three-minute demonstration script

**(0:00–0:20) Framing.** "Astrolabe is a read-only instrument for reading prediction markets.
It doesn't place trades — it measures a market's implied probability and order-book behaviour
and flags when the readings are statistically unusual, with an honest confidence score."

**(0:20–0:50) Overview (replay mode).** Open `http://localhost:3000`. Point out the mode chip
(top-right) showing REPLAY, and the top-movers / most-active / highest-volume / widest-spread
cards with signal-strength meters. "Every response carries its data mode, so cached or replay
data is never shown as live."

**(0:50–1:30) Market detail.** Click a market. Show the price-history chart (both outcomes),
then the per-outcome panel: implied probability and its normalised value, best bid/ask, midpoint,
spread, order-book imbalance, near-mid depth, rolling volatility, movement, z-score, a
data-quality badge and a confidence figure. "Implied probability is a spread-contaminated
risk-neutral estimate — we surface that, not hide it."

**(1:30–2:05) Signal Lab.** Open Signal Lab. Expand a signal's "why": the composite anomaly's
visible components (return z-score, volume acceleration, book imbalance), weights, and the
plain-language explanation and limitations. "These are screening heuristics, not proof of
anything."

**(2:05–2:40) Replay & Backtest.** Open Replay. Adjust the strength/move thresholds and horizon;
show the sample size, hit rate, false-positive rate and the events table (momentum signals
follow through; spike-and-revert signals don't). Read the Assumptions/Limitations. "The signal
at frame i is evaluated only on later frames — no look-ahead — and this is synthetic data, so
it's a demonstration of the machinery, not a profit claim."

**(2:40–3:00) Live mode + close.** Switch the mode chip to **Live**. The overview repopulates
with real, current Polymarket markets and the chip turns green. "Same analytics, real public
data, clearly labelled live. That's Astrolabe — correct, transparent, and honest about what it
does and doesn't know." Optionally open `http://localhost:8000/docs` to show the typed API.
