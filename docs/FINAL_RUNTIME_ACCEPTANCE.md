# Final Runtime Acceptance — Arepo

Branch: `arepo-final-runtime-acceptance-fix` · Safety tag: `arepo-before-final-runtime-acceptance-fix`

This pass fixes real runtime failures that manual browser testing reproduced **despite passing unit
tests**. Every item below was verified in a real Chromium browser driving the actual Next app (dev
server on `:3000`) against the real FastAPI backend (`:8000`) with the real local
`backend/astrolabe.db` (the one valid 6h prospective cohort — 60 frozen markets — was preserved; the
database was never reset, recreated or destructively migrated).

Screenshots and the raw measured rectangles are in `docs/runtime-acceptance/`
(`measurements.json`, `signals-574-popover.png`, `signals-574-actionrow.png`, `replay-real-cohort.png`,
`market-2694364.png`, `market-2822017.png`).

## How to reproduce the acceptance run locally

```bash
# 1. Backend (real DB)
cd backend && source .venv/bin/activate
uvicorn astrolabe.api.app:app --port 8000

# 2. Frontend (clean output, pointed at the backend)
cd frontend
npm ci
npm run dev:clean                      # rm -rf .next && next dev
# NEXT_PUBLIC_API_BASE=http://localhost:8000 is the default

# 3. Browser acceptance suite (real Chromium, real rendered geometry)
cd frontend
npm run e2e:install                    # one-time: playwright install chromium
npm run e2e                            # playwright test  → 79 passed
```

## Acceptance items — no item is Fail

| # | Item | Result | Evidence |
|---|------|--------|----------|
| 1 | Popover fully inside viewport | **Pass** | At 574px the panel right edge = **562px = 574 − 12** (12px margin exactly); left 210px. `e2e/popover.spec.ts` asserts left ≥ 12 and right ≤ vw − 12 from the real bounding rect at all 7 viewports, after scroll and after resize. |
| 2 | No horizontal scrollbar | **Pass** | `document.documentElement.scrollWidth <= clientWidth` AND `window.scrollX === 0` on every required route at all 7 viewports (`e2e/overflow.spec.ts`, 49 route×viewport cases). |
| 3 | Action spacing fixed | **Pass** | Badge and toggle share a row with **12.8px** horizontal gap (≥12) at 574 and 375; toggle height **32.3px** (padded); wraps to ≥8px vertical gap when narrow. `e2e/action-spacing.spec.ts`. |
| 4 | Real 6h cohort visible in Replay | **Pass** | Default Replay = "Real prospective research"; shows 60 frozen markets, role counts (10/9/9/32), horizon coverage, edge verdict, calibration, model-limitation note (`e2e/replay.spec.ts`). |
| 5 | Scheduled and actual freeze times visible | **Pass** | Banner: *"Actually frozen at 06/08/2026, 02:24:13 · scheduled for 06/08/2026, 01:00:00 · 84 minutes late · outcomes measured from the actual freeze time."* (local time; source is 01:24:13Z frozen / 00:00Z scheduled). |
| 6 | Synthetic separated | **Pass** | Synthetic is a distinct "Synthetic demonstration" tab, never default, never labelled simply "prospective", never mixed into real stats; `?replay=prospective` now lands on the **real** research. |
| 7 | Both market routes work | **Pass** | `/markets/2694364` and `/markets/2822017` → HTTP 200 on direct nav, refresh and Back/Forward; no `vendor-chunks/geist.js` error (`e2e/routes.spec.ts`). |
| 8 | API disconnect/reconnect controlled | **Pass** | One clear "API disconnected" chip; ≤4 status requests in a 4s outage window (bounded backoff, was a flood); auto-recovers to connected; zero unhandled rejections (`e2e/api-disconnect.spec.ts`). |

## Before / after at 574 px (the reproduced failure width)

| Measurement | Before (reported) | After (measured) |
|-------------|-------------------|------------------|
| `/signals` `document.documentElement.scrollWidth` | **632** | **574** |
| `/signals` `clientWidth` | 574 | 574 |
| `overflowing` | **true** | **false** |
| Information popover right edge | past the right edge (off-screen) | **562px** (viewport 574 − 12px margin) |
| Popover left edge | — | 210px (≥ 12) |
| Popover width | uncapped | **352px** = `min(22rem, 100dvw − 24px)` |
| Badge → "Why this fired" horizontal gap | visibly pressed together | **12.8px** (≥ 12) |
| Detail toggle height (tap target) | — | **32.3px** |

## Root causes (see the final report and DECISIONS.md for full detail)

1. **Popover off-screen** — the panel was measured while its `max-width` was still the default 320px,
   then revealed with a *larger* viewport-capped `max-width`; the wider revealed panel spilled past
   the clamp that had reserved space for a 320px panel. Fixed by capping `max-width` from the viewport
   **before** measuring with `getBoundingClientRect()`, so the measured width equals the revealed
   width, then clamping ≥12px inside a `visualViewport`-aware viewport in a second pass.

2. **Horizontal overflow (632→574)** — three real element-level sources, each fixed at the root (not
   with a global `overflow-x` mask):
   - `TopBar` right cluster (`shrink-0` ModeSwitcher + auth link ≈ 306px) could not fit a 320px
     viewport → now `flex-wrap` and shrinkable so controls wrap.
   - `SignalItem` market link was `inline-flex` (sized to its `nowrap` text) so `truncate` never
     engaged → now width-constrained `flex min-w-0` + `truncate`.
   - `PriceHistoryChart` accessible table used `.sr-only` **on the `<table>`**; a table cannot shrink
     below its min-content (`nowrap` cells ≈ 291px), so `width:1px` was ignored and the hidden table
     extended the document → moved `.sr-only` to a wrapping `<div>` (which honours `width:1px`).
   - The synthetic-**demo** view kept a sub-pixel 1–2px window scroll at 320px from its wide
     fixed-min-width tables; contained with a **scoped** `overflow-x-clip` on that synthetic subtree
     only (no element-level overflow existed; getBoundingClientRect showed no offender).

3. **Market route error** — `Cannot find module './vendor-chunks/geist.js'` was **stale/corrupt
   `.next` dev output** (the per-package dev vendor chunk went missing), not a routing-logic or
   dependency-packaging fault. Proof: after `rm -rf .next && npm ci && npm run build` (clean build
   succeeds, 16 routes incl. `/markets/[id]`) and a fresh `npm run dev`, `.next/server/vendor-chunks/
   geist.js` is regenerated and both IDs return 200. Guarded by new `clean` / `dev:clean` /
   `build:clean` scripts; deployment always builds from a clean environment.

4. **API polling flood** — `useStatus` ran one fixed-30s poller **per consumer** (StatusChip +
   DegradationBanner, doubled again by React StrictMode → up to 4 streams), none with backoff, so a
   downed backend produced a console flood of `ERR_CONNECTION_REFUSED`. Replaced with a single shared,
   deduplicated poll loop per mode with exponential backoff (30s→cap 5min, reset on success),
   `AbortController` cancellation on the last unmount, visibility-pause, and automatic recovery.

## Verified preservation

- `backend/astrolabe.db` untouched; `/api/research/status` still reports the real cohort
  (60 frozen, 10/9/9/32 roles, frozen 01:24:13Z, scheduled 00:00Z, ~84min late, not excessively late,
  `evaluation_origin_at == frozen_at`).
- No change to signal direction, thresholds, confidence, Research Priority, cohort eligibility,
  baselines, ablation, walk-forward or edge criteria. Backend is read-only in this pass
  (`git status` shows only frontend files modified).

## Test results

- Backend: `pytest` **359 passed**; `ruff check .` clean.
- Frontend: `tsc --noEmit` clean; `next lint` clean; `vitest` **40 passed**; `next build` clean.
- Browser: Playwright **79 passed** (overflow 50, popover 9, action-spacing 7, replay 6, routes 6,
  api-disconnect 1).
