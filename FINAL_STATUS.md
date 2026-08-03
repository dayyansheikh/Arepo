# FINAL_STATUS: Arepo Master Final Refinement

_Truthful final status of the Master Final Refinement (branch `arepo-master-final`, from
safety tag `arepo-ui-v1`). Every claim below was verified by running the code in this
environment; commands and their actual output are given so a reader can reproduce them._

## Project summary

**Arepo** is a read-only prediction-market intelligence platform over public Polymarket data.
It ingests market discovery and order-book data (Gamma API, CLOB REST, CLOB market WebSocket),
normalises it through a strict typed boundary, computes transparent microstructure and
time-series analytics (implied probability, movement, rolling volatility, standardised
z-score, spread/midpoint, order-book imbalance, near-mid depth, a composite anomaly score with
confidence/data-quality), and serves them via a FastAPI backend to a Next.js/TypeScript
frontend. It has three explicit data modes, live, cached, replay, a deterministic
look-ahead-safe backtest over a committed synthetic dataset, and, added in this refinement, a
separate prospective weekly cohort evaluation engine. It never places trades and makes no
profitability claim.

## What this refinement changed

Grouped as requested, with the primary files for each area.

### Brand
- Faithful SVG reconstruction of the supplied 5x5 grid logo (`design-assets/brand/AREPO logo
  (no word).png`): second column and second row red, remaining cells outlined, adapted for the
  light-only identity (`frontend/components/Logo.tsx`).
- Documented that the earlier Phase 1 "convergence mark" concept, recorded in
  `docs/brand-system.md`, was superseded by the grid-mark reconstruction once the supplied
  asset was integrated directly.

### Typography
- Display heading font decision: **Jost** (SIL OFL, a Futura revival), vendored locally as
  static `.woff2` files (`frontend/app/fonts/`) and loaded via `next/font/local`
  (`frontend/app/fonts.ts`), used only for major titles, hero and section-intro headings, in
  uppercase with wide tracking. Documented explicitly as an approximation of the supplied
  wordmark, not an exact match, in `docs/brand-system.md`.
- Interface text and data values stay Geist Sans with tabular numerals throughout.

### Interface
- Navigation presence, active/hover states and logo/wordmark readability improved.
- The pale-red information panel (read as an error) replaced with a neutral information panel;
  Arepo red reserved for active nav, selected controls and genuine signal emphasis.
- Technical status labels (`REST`, `WS`, `age`) replaced with `API`, `Live feed`, `Updated`,
  each with an accessible tooltip and clear states (Connected, Updating, Delayed, Offline, Not
  available in this mode).
- Market detail readability: larger body text, clearer headings, progressive disclosure
  (`Show advanced market data`) for specialist metrics.
- Signal Lab terminology simplified: `Unusual market activity` as the surface label for the
  composite anomaly score, `Data coverage` and `Lookback` in place of raw identifiers,
  friendly component names, technical detail behind a disclosure.
- Methodology and How Arepo Works readability pass: larger text, KaTeX-rendered equations,
  plain-English summary before each formula, worked examples, anchored links from product
  pages.

### Data quality
- Chart repair: fixed timestamp handling so price-history points carry their real timestamps
  (or a synthesised, distinct axis when timestamps are genuinely absent) instead of collapsing
  to one point; visible line strokes and points for sparse data; a stated note when only
  limited history exists.
- Category, sport and competition filters (`GET /api/markets/facets`) built dynamically from
  the normalised market set, with no invented values and no `Unknown` placeholder; empty states
  where no markets match.

### Signals
- Composite anomaly score terminology, hierarchy and disclosures reworked per the brief
  (surface label, plain-English explanation first, technical detail and equations behind
  disclosure).

### Replay
- A new prospective weekly cohort evaluation engine (`backend/astrolabe/evaluation/`, 8 new
  tables, ranking/freeze/forward/resolution/portfolio logic, an idempotent CLI, and 4 new
  read-only API endpoints under `/api/cohorts/*`).
- The Replay page (`frontend/app/replay/page.tsx`) rebuilt to consume the cohort API: week
  picker, price-movement vs final-resolution views, entry-level "why this qualified"
  disclosures, a labelled hypothetical portfolio, and provenance notices distinguishing
  prospective, reconstructed and synthetic cohorts. The prior deterministic signal backtest is
  preserved underneath as a clearly labelled, separate demonstration.

### Accessibility
- Keyboard/touch-operable metric tooltips, a single themed focus ring, non-colour cues paired
  with colour throughout (verdicts, status), chart data alternatives, semantic headings,
  reduced-motion support carried through the refinement.

### Technical quality
- Backend test count grew from the 128-test baseline to **174 tests** (24 category/facet tests,
  3 chart-timestamp regression tests, 19 evaluation-engine tests, plus the pre-existing suite),
  all passing, `ruff` clean.
- Frontend gained a `vitest` unit-test runner (none existed at baseline) with **8 tests**
  covering chart row-building, all passing; `tsc --noEmit`, `next lint` and `next build` all
  clean.

## Migrations added

Eight new SQLAlchemy ORM tables, added to the shared `Base.metadata` (the project uses
`create_all`, not Alembic) and created idempotently by
`backend/astrolabe/evaluation/migrations.py::bootstrap`:

`calculation_versions`, `signal_snapshots`, `weekly_cohorts`, `cohort_entries`,
`ranking_audit`, `forward_price_observations`, `market_resolutions`, `evaluation_results`.

Defined in `backend/astrolabe/evaluation/models.py`. `bootstrap()` is safe to run repeatedly:
`create_all` skips existing tables, and the calculation-version row is upserted, not
duplicated.

## Commands added

`python -m astrolabe.evaluation.cli <command>` (`backend/astrolabe/evaluation/cli.py`), every
command idempotent and safe to run on a schedule:

```
bootstrap            create/verify the evaluation tables and calculation version
rank    [--mode]     update this week's provisional top ten from current signals
freeze  [--at]       freeze the cohort for a week at the cut-off
forward [--mode]     collect any due forward prices for frozen cohorts
resolve [--mode]     record newly-available market resolutions
evaluate             (re)compute the two evaluation views and portfolio values
seed-synthetic       build the labelled synthetic demonstration cohort
status               print the recorded cohort weeks
```

## Tests added

- **24 category/sport/competition facet tests** (`backend/tests/unit/test_categories.py`).
- **3 chart-timestamp regression tests** (`backend/tests/unit/test_service.py`:
  `test_history_points_preserve_real_timestamps`,
  `test_history_points_synthesise_distinct_axis_when_timestamps_absent`,
  `test_history_points_empty_when_no_data`).
- **8 frontend chart `vitest` tests** (`frontend/lib/chart-data.test.ts`).
- **19 evaluation-engine tests** (`backend/tests/unit/test_evaluation.py`), covering the 13
  guarantees required by the brief: provisional rankings keep only the strongest qualifying
  entries; a stronger signal replaces only the current lowest entry; ties are deterministic;
  frozen cohorts cannot be modified; later data cannot change an original ranking; losing
  entries remain stored; unresolved entries remain pending; repeated scheduler runs are
  idempotent; forward observations are not duplicated; resolution updates do not overwrite
  entry data; weekly summaries use correct denominators; simulated returns use only available
  entry information; and prospective, reconstructed and synthetic datasets cannot be mixed
  silently.

## Actual test results (verified in this environment)

```
cd backend && source .venv/bin/activate
python -m pytest -q
# -> 174 passed, 1 warning in 3.46s

ruff check astrolabe tests scripts
# -> All checks passed!
```

```
cd frontend
npx vitest run
# -> Test Files  1 passed (1)
#    Tests  8 passed (8)

npx tsc --noEmit
# -> clean (no output, no type errors)

npm run lint
# -> No ESLint warnings or errors

npm run build
# -> Compiled successfully; 9 routes generated
#    (/, /_not-found, /how-it-works, /icon.svg, /markets, /markets/[id],
#     /methodology, /replay, /signals)
```

Backend: **174 tests pass, ruff clean.** Frontend: **8 vitest tests pass; tsc, lint and
production build all clean.**

## Historical-data limitations

There is no reconstructed historical snapshot store on this machine. No earlier prospective
cohort has been invented or backfilled. The prospective evaluation engine correctly reports an
empty cohort history (`GET /api/cohorts/weeks` returns `[]`, `GET /api/cohorts/provenance`
reports `first_prospective_week: null`) until the first genuine `rank --mode live` run is
performed. A synthetic demonstration cohort can be seeded
(`python -m astrolabe.evaluation.cli seed-synthetic`) purely to prove the machinery works end
to end; it is visibly badged as synthetic wherever it appears and is never counted in real
prospective statistics. See `docs/limitations.md` and `docs/methodology.md` §12.

## First prospective cohort date

**None yet.** Real prospective tracking begins at the first `python -m astrolabe.evaluation.cli
rank --mode live` run on a given deployment; that command has not been run against a live
schedule as part of this refinement, so no real cohort week exists to date. This is stated
plainly rather than estimated or assumed.

## Scheduler status

Idempotent CLI commands for the full workflow (rank, freeze, forward, resolve, evaluate) are
implemented and documented in `docs/deployment.md`, including a worked GitHub Actions cron
example. **No paid or public external scheduler has been activated.** Activating GitHub
Actions, a hosting-provider scheduler, or cron against a real deployment requires the user's
own repository or hosting account and explicit approval; none of that has been done here.

## Manual browser checks still recommended

The following were not re-verified with a live browser session as part of writing this
documentation and should be checked manually before relying on them:

- Visual inspection of the Jost display font rendering against the supplied wordmark at
  various sizes (title, hero, report cover).
- Visual inspection of the reconstructed grid logo at favicon size (16px) and in the nav.
- The Replay page's empty state (no cohorts recorded) versus its populated state once
  `seed-synthetic` has been run, in an actual browser.
- Keyboard-only navigation through the Signal Lab and Replay disclosures, and screen-reader
  labelling of the verdict icons (good/bad/pending) on cohort entries.
- Mobile/narrow-viewport behaviour of the Replay portfolio table and week picker.
- Live-mode end-to-end exercise of the `rank` -> `freeze` -> `forward` -> `resolve` ->
  `evaluate` command sequence against real Polymarket data over an actual elapsed week (this
  cannot be verified faster than real time, by the design of the system itself).

## Deployment status

**Not claimed as deployed.** `docker compose up` and any public hosting push were not executed
in this environment (no Docker daemon, no `gh`/`vercel` CLI, no authenticated hosting account).
See `docs/deployment.md` for the exact commands an operator should run and verify
independently, and the new Scheduler section for how the weekly cohort workflow should be
wired up once a deployment exists.

## Localhost addresses

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000` (interactive docs at `/docs`, health at `/health`)

## Exact local start command

**Non-Docker (verified path):**
```bash
# Backend  (terminal 1)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn astrolabe.api.app:app --reload            # -> http://localhost:8000

# Frontend (terminal 2)
cd frontend && npm install && npm run dev          # -> http://localhost:3000
```

**One command (Docker, authored, not executed here, no daemon in this environment):**
```bash
docker compose up --build
```

## Documentation updated

`README.md`, `docs/architecture.md`, `docs/methodology.md`, `docs/API.md`,
`docs/deployment.md`, `docs/limitations.md`, `docs/brand-system.md`,
`docs/portfolio-report.md`, this file.
