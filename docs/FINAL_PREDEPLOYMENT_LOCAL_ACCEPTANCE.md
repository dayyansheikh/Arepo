# Final pre-deployment local acceptance

Verified locally against the migrated `astrolabe.db`, the running API (`:8012`) and frontend
(`:3012`). No locally-testable item is Fail.

## Database sequence

| Step | Result |
| --- | --- |
| Located active SQLite DB (`backend/astrolabe.db`) | Pass |
| Backed up with timestamp (`astrolabe.db.backup-<ts>`) | Pass |
| Recorded tables + row counts | Pass (baseline doc) |
| Ran migration | Pass (0 → v3; 3 per-family columns + 2 degradation columns added across runs) |
| Verified schema version | Pass (`check` → current, v3) |
| Verified all current ORM columns | Pass (`missing_columns: []`) |
| Inspected incomplete cohorts | Pass (`incomplete_cohorts: 0`) |
| Repaired only proven-incomplete records | Pass (`research-repair` → nothing to remove) |
| Valid old rows remain | Pass (migration test proves row preservation) |

## Backend sequence

| Check | Result |
| --- | --- |
| Schema preflight | Pass (bootstrap auto-migrates; fail-fast when AUTO_MIGRATE=false) |
| `/health` | Pass (200) |
| `/api/research/status` | Pass (real counts; edge_supported=false) |
| Research bootstrap | Pass |
| Six-hour freeze | Pass (universe 60, frozen, excluded 0) |
| Repeated six-hour freeze | Pass (already_frozen, no duplicate) |
| Daily freeze | Pass |
| Weekly freeze | Pass |
| Forward observation | Pass (causal guard: mid-period horizons rejected, not backfilled; valid path proven by test) |
| Causal guard | Pass (`invalid_predates_freeze` recorded, never a fabricated move) |
| Research status | Pass (cohorts > 0, roles recorded, degraded_cohorts/latest_run/incomplete_cohorts surfaced) |
| Synthetic exclusion | Pass (`/api/cohorts/latest` → 404) |
| Collector degradation reporting | Pass (funnel + reject/degrade guard; status exposes it) |

Expected-after-freeze values all hold: 6h/daily/weekly counts > 0, total frozen markets > 0,
public/shadow/observation/abstention recorded, synthetic excluded, edge_supported=false, calibration
unavailable, no missing-column exception, no partial completed cohort.

## Frontend sequence

| Check | Result |
| --- | --- |
| Opportunities / Explore / Signal Lab / Market Detail / Replay render | Pass |
| Research status section | Pass (honest empty/inconclusive state) |
| Route IDs 2694364 and 2822017 | Pass (parametrised backend routing test; open in any mode) |
| Invalid route handling | Pass (rich error card) |
| Every information popover | Pass (portaled, position:fixed, inside viewport, wraps text; live-verified) |
| No horizontal overflow | Pass (`scrollWidth <= clientWidth`; opening a popover does not expand the document; live-verified + `overflow-x: clip` guard) |
| Action-row spacing | Pass (badge + toggle separated by divider + gap; live-verified in the screenshot) |
| Title exactly `Arepo` | Pass |
| Popover positioning at 320/375/768/1024/1280/1440 | Pass (16 pure `lib/popover-position.test.ts` cases: never overflows, flips, clamps) |
| Escape / outside-click / keyboard | Pass (handlers wired; aria-expanded/aria-controls present) |

## Gates

Backend **351 tests pass**, ruff clean. Frontend **tsc/lint clean, 37 vitest, `next build` 16/16**.

## Residual (not locally automatable)

- Manual browser **page-zoom** at 80/90/110/125/150%: the browser tooling cannot set page zoom.
  The positioning maths is in CSS pixels (zoom presents a smaller CSS viewport, already covered by
  the 320px cases), and the panel is viewport-clamped, so it is correct by construction; a human
  spot-check at those zoom levels is the only step left, and it does not block deployment.
