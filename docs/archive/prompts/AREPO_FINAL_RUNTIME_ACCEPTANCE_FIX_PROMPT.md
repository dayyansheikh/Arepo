# Arepo Final Runtime Acceptance Fix

Start from branch `arepo-final-predeployment-launch-readiness` at commit `ccd003c`.

Create:

- safety tag: `arepo-before-final-runtime-acceptance-fix`
- branch: `arepo-final-runtime-acceptance-fix`

Preserve all research, migration, causal-timing and model logic. Do not change signal direction, thresholds, confidence, Research Priority, cohort eligibility, baselines, ablation, walk-forward or edge criteria.

This pass fixes real runtime failures that manual browser testing reproduced despite passing unit tests.

## Reproduced failures

1. Signal Lab popover still renders partly outside the right edge.
2. Signal Lab still has real horizontal overflow:
   - `scrollWidth: 632`
   - `clientWidth: 574`
   - `overflowing: true`
3. The qualification badge and `Why this fired` are still visibly pressed together.
4. Replay does not show the real 6h prospective research cohort.
   - default Replay shows reconstructed analysis
   - `?replay=prospective` shows the old synthetic weekly demonstration
   - real scheduled time, actual freeze time and lateness are absent
5. `/markets/2694364` and `/markets/2822017` fail with:
   `Cannot find module './vendor-chunks/geist.js'`
6. When the API is stopped, repeated `/api/status?mode=live` requests flood the console with `ERR_CONNECTION_REFUSED`.

## 1. Fix popovers using real rendered geometry

The existing pure positioning tests are insufficient.

Requirements:

- portal to document body
- `position: fixed`
- measure actual rendered dimensions with `getBoundingClientRect()` after mount
- perform a second positioning pass after measurement
- use `window.visualViewport` when available
- otherwise use document client width/height
- clamp after real dimensions are known
- keep at least 12 px from every viewport edge
- `max-width: min(22rem, calc(100dvw - 24px))`
- wrap long text
- reposition on open, scroll, resize and visualViewport resize/scroll
- no initial visible off-screen flash
- Escape, outside-click, keyboard and ARIA support
- never increase document width

Do not use brittle fixed offsets.

## 2. Add real browser tests

Add Playwright or the existing E2E framework.

Run the actual Next app and test at:

- 574 × 900, reproducing the failure
- 320 × 800
- 375 × 812
- 768 × 1024
- 1024 × 768
- 1280 × 800
- 1440 × 900

For edge popovers, assert from the real bounding rectangle:

- left >= viewport + 12
- right <= viewport - 12
- top/bottom remain within the viewport where physically possible
- `document.documentElement.scrollWidth <= document.documentElement.clientWidth`

Test after page scroll and resize. Capture screenshots on failure.

## 3. Remove the actual horizontal-overflow source

Do not pass by applying only global `overflow-x: hidden` or `clip`.

Instrument the real page and log every element whose bounding box exceeds the viewport, including selector, classes, width, transform, min-width and white-space.

Audit:

- popovers
- cards
- metric area
- mode switcher
- nav
- filters
- action rows
- long market text
- footer
- `100vw`
- fixed/min widths
- negative margins
- transforms

Test overflow on:

- `/signals`
- `/`
- `/markets`
- both supplied market routes
- `/replay`
- `/replay?replay=prospective`

## 4. Fix action spacing

Create a deliberate action row.

Requirements:

- qualification badge in its own item
- at least 12 px horizontal gap before `Why this fired`
- at least 12 px gap before `Show detail` / `Hide detail`
- 8 px vertical gap when wrapping
- usable padded click targets
- long text wraps without overlap
- controls may move to a second row
- browser tests assert spacing from bounding rectangles

## 5. Integrate real research data into Replay

The local database and `/api/research/status` contain one real 6h cohort:

- 60 frozen markets
- 10 public selections
- 9 shadow directional
- 9 observation
- 32 abstention
- scheduled for 2026-08-06 00:00 UTC
- frozen at 2026-08-06 01:24:13 UTC
- evaluation origin equals frozen time
- about 84 minutes late
- not excessively late

Replay must show this real cohort.

Required structure:

### Real prospective research

Primary when real cohorts exist. Show:

- counts by cadence
- total frozen markets
- role counts
- horizon coverage
- scheduled_for
- frozen_at
- evaluation_origin_at
- lateness
- late/excessively-late status
- degraded status
- collector freshness
- edge verdict
- calibration status
- model limitation note

Show a prominent banner:

`Actually frozen at Y · scheduled for X · N minutes late · outcomes measured from the actual freeze time`

### Reconstructed analysis

Keep separate and clearly secondary.

### Synthetic demonstration

Move to a separate `Demo` or `Synthetic demonstration` control.

Synthetic data must:

- never be default when real prospective data exists
- never be labelled simply prospective
- never mix into real statistics
- never hide the real research status

Add API integration and browser tests using the reproduced real cohort payload.

## 6. Fix market-route runtime stability

Reproduce from a clean state:

```bash
rm -rf .next
npm ci
npm run build
npm run dev
```

Investigate `Cannot find module './vendor-chunks/geist.js'`.

Determine whether the cause is:

- stale/corrupt `.next`
- dev/build concurrency
- dependency packaging
- real route code

Requirements:

- clean install works
- clean build works
- clean dev server works
- direct navigation, refresh and Back/Forward work for both supplied IDs
- no missing generated vendor chunk
- add route smoke tests
- document a safe `dev:clean` command if stale output is the cause
- deployment must build from a clean environment

## 7. Handle API disconnection properly

When the backend is unavailable:

- show one clear API disconnected state
- use bounded retry/backoff
- do not flood the console
- cancel requests on unmount/navigation
- recover automatically when the API returns
- avoid unhandled rejections
- browser-test disconnected → connected recovery

## 8. Real runtime acceptance

Run the actual backend and frontend plus browser tests.

Manually verify:

- popover fully inside viewport
- no horizontal scrollbar
- action spacing fixed
- real 6h cohort visible in Replay
- scheduled and actual freeze times visible
- synthetic separated
- both market routes work
- API disconnect/reconnect is controlled

Create `docs/FINAL_RUNTIME_ACCEPTANCE.md` with screenshots and measured before/after rectangles.

No item may remain Fail.

## 9. Test gate

Run:

```bash
cd backend
pytest
ruff check .
```

Then:

```bash
cd frontend
npx tsc --noEmit
npm run lint
npm test -- --run
npm run build
```

Also run the complete browser suite.

Do not weaken tests.

## 10. Completion

Update `CHECKPOINT.md`, `TASKS.md`, `DECISIONS.md` and `docs/USER_DEPLOYMENT_CHECKLIST.md`.

Do not deploy yet.

Commit and push.

Final report must state:

1. popover root cause
2. horizontal-overflow root cause
3. before/after measurements at 574 px
4. action-spacing fix
5. Replay real-cohort integration
6. synthetic separation
7. route root cause
8. clean route proof
9. API polling fix
10. browser test count
11. backend/frontend results
12. branch
13. final commit
14. push status
15. exact local verification commands
16. whether deployment is safe

Do not claim completion only because unit tests pass.

Start now and continue autonomously.
