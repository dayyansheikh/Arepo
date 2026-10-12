# Live cross-venue lead test (Kalshi -> Polymarket), 2026-10-12

Research only, local, read-only. Never trades, holds no credentials, uses only keyless public GET/POST market-data
endpoints. No edge, calibration or profitability claim. Registered as **E009** in `EXPERIMENT_LEDGER.md`
(E008 is reserved for the IF-H2 deadline ladder).

## Why
The historical study (`CROSS_VENUE_STUDY.md`, `exploratory_historical`, rung L1) found Kalshi's latest 10-minute change
predicting Polymarket's next 10-20 minutes (+5.3% relative MSE gain over M0 at 10 min, BY-passing; Kalshi first in 70% of
large moves; Polymarket does about 86% of the convergence). Its timestamps could not separate a 10- from a 20-minute lead,
Polymarket history points may be stale, and the economics were unresolved. This test uses receipt-timed quotes from both
venues and a model frozen before any live outcome.

## What runs
Module `backend/astrolabe/research_lab/cross_venue_live.py`, runner `backend/scripts/run_cross_venue_live.py`, tests
`backend/tests/test_research_lab_cross_venue_live.py`. Launchd job `com.arepo.cross-venue-live` (template
`backend/scripts/launchd/com.arepo.cross-venue-live.plist.template`; RunAtLoad, KeepAlive on crash). Output under
`data-dumps/research_lab/cross_venue_live/` (git-ignored). Logs `~/Library/Logs/arepo-cross-venue-live.{err,out}`.

1. **Pair list (daily, separate subprocess).** Kalshi `/markets?status=open&mve_filter=exclude` (about 120k markets, 121
   pages) and Polymarket Gamma `/markets/keyset?closed=false` (about 260k markets, 100 per page), both reduced to open,
   currently two-sided (0 < bid < ask < 1, spread <= 10c) Yes/No contracts. `cross_venue.match_markets` runs unchanged.
   A Kalshi market that fails a necessary matcher condition (number set, 3 shared words, end date within 3 days) is
   dropped while streaming (`MatchPrefilter`, output-identical, memory only). Then:
   - hand verdicts (`model_specs/cross_venue_live_verified.json`, title level) are applied: `different` excluded, `same` first;
   - **live-only tightening** for pairs without a verdict: `LIVE_EXTRA_CONFLICT` words (vice, halftime, leading, second,
     runoff, round, group, removed, nominee, nomination, justice, republican, democrat, quarter, half, period, set, map) on
     one side only reject the pair. Added after the first live refresh showed 56 of 167 matcher pairs were different
     contracts (presidential vs vice-presidential nominee 30, match vs halftime 7, next Justice vs next nominee 9, group vs
     tournament 3, election vs second round 2, party vs candidate 2, other 3). `cross_venue.CONFLICT` is unchanged;
   - rank: hand-verified first, then by the smaller 24h volume of the two venues. Cap 200.
   - Refresh traffic yields to the live collector (`live_pass_running_anchored`), 0.5 req/s per venue.
2. **Poll (every 120 s on the UTC grid).** Kalshi `/markets?tickers=` (100 per request: last price, yes bid/ask, sizes) and
   Polymarket CLOB `POST /books` (100 tokens per request: executable best bid/ask and sizes, book timestamp). Each is
   stamped with its receipt time and appended to `quotes/YYYYMMDD.jsonl` (gzipped after 2 days). Pairs dropped by a
   refresh keep being polled 70 min so their pending outcomes complete.
3. **Predictions before outcomes.** For each active pair with complete features, a line is appended (fsync) to
   `predictions.jsonl` in the same cycle, before any later quote exists. Features (`spec.feature_definitions`):
   `r1, r6` Polymarket mid change over 10/60 min, `lvl, lvl2`, `gap = Kalshi mid - Polymarket mid`, `dk1, dk6` Kalshi mid
   change over 10/60 min. A lagged value is the latest poll in `[t-L-240 s, t-L]`; every endpoint must be a valid two-sided
   mid inside [0.03, 0.97]; nothing is interpolated. Each line carries M0 and M1 predictions at 10/20/60 min, the
   direction `side = sign(M1_20)`, the entry round-trip cost `ask - bid + taker fees`, `trade = |M1_20| > cost`, the
   evidence role and the spec hash.
4. **Outcomes (`OutcomeWriter`, reads predictions and quotes only).** For origins on the 10-minute grid (disk budget),
   Polymarket mid and touch at +10/+20/+60 min from the poll at exactly `t+h`, else the nearest within +-120 s; else
   `unavailable` (never filled). Paper taker P&L per share: long = exit bid - entry ask, short = entry bid - exit ask, minus
   `economics.taker_fee` on both legs (rate: `feesEnabled` plus the docs rate of the `feeType` category; unknown -> the
   highest docs rate, 0.07). A restart recovers pending outcomes and the feature history from disk.
5. **Limits.** Poll: 4 requests per 120 s (<= 0.9 req/s pacing per venue, exponential backoff on 429/5xx). Disk cap 2 GB
   total (the poller exits with code 3). Poller RSS about 115 MB; the refresh subprocess is measured separately (below).

## Frozen spec (hash-pinned)
`backend/astrolabe/research_lab/model_specs/cross_venue_live_v1.json`, sha256
`e63f20cc095ba88346155cabe0d2e4289981017cc48450ccc575bbc7d0d16e2b` (pinned in `SPEC_SHA256`; `load_spec` refuses any
other bytes). Built once by `run_cross_venue_live.py --freeze` on 2026-10-12 before any live quote was collected.

- **Data:** the historical study's analysis set (341 pairs, 190 Polymarket events; `matches.json` and `results.json`
  sha256 recorded in the spec), code commit `70da1ee`.
- **Alignment:** `cross_venue.align_pair(pm_lag_s=0)` (a Polymarket history point usable at its own stamp), the closest
  analogue of a receipt-timed live quote. The study's primary (conservative) alignment puts the lead at 20 min and this
  one at 10 min; the 20-min target covers both.
- **Fit:** unpenalised OLS with intercept in raw units, all usable origins (non-overlapping per horizon via
  `cross_venue._design`), one fit per horizon, never refitted. M0 = `[r1, r6, lvl, lvl2]`, M1 = M0 + `[gap, dk1, dk6]`.
- **Key coefficients (20 min):** dk1 0.339, dk6 0.123, gap 0.024, r1 -0.230, r6 -0.120. dk1 alone: 0.429. In-sample
  relative MSE gain of M1 over M0: 9.6% (10 min), 7.1% (20 min), 4.1% (60 min). Event-cluster bootstrap SE of the 20-min
  gain: 1.4 points (190 clusters, 220,358 origins). In-sample, so optimistic.

## Deviations from the historical study (all fixed before any live outcome)
- Polymarket price: executable book mid with the same two-sided validity rule as Kalshi (history used `prices-history`).
- Kalshi close time for matching: `expected_expiration_time` (else `close_time`); history used settled close times.
- Live-only conflict words and hand verdicts (above). Pairs are long-dated open markets ranked by volume, not the last
  30 days before resolution.
- 2-minute polling; features are still 10/60-minute changes.

## Pilot (2026-10-12 21:44Z to 2026-10-13 00:00Z, `prospective_unregistered`, excluded from E009)
Operational numbers (no outcome read) are in the E009 ledger entry: about 70 pairs / 22 events with complete features per
cycle, dk1 non-zero on 12% of origins, 0 trade-rule firings, no 429s, poller RSS 115 MB, refresh RSS 118 MB while paging, peak 194-204 MB at the end (matching); see Resource notes. Pilot outcome
lines exist on disk but were not analysed. Registration: `REGISTERED_UTC = 2026-10-13T00:00:00Z`; challenger review
(science-reviewer) accepted with required fixes, all applied before the registration commit (ledger E009).

## Resource notes
- Refresh memory: the first version paged Gamma `/events/keyset` (pages can hold events with thousands of markets) and peaked at
  245-380 MB; it now pages the flat `/markets/keyset` (100 markets per page, about 2,600 pages, about 50 min at 0.9 req/s)
  with compact candidate records and a matcher-equivalent Kalshi prefilter: 118 MB while paging, but the full run peaked at
  204 MB (`/usr/bin/time` max RSS; 194 MB self-reported), so the refresh subprocess sits at the 200 MB budget. The long-running
  poller is 115-132 MB. Open item: lower the refresh peak (e.g. tokenise Polymarket candidates once, drop texts after matching).
- Disk: about 28 MB/day predictions, about 10 MB/day outcomes, about 30 MB/day raw quotes (gzipped after 2 days): well
  under the 2 GB cap by the end date.

## Commands
```
cd backend && source .venv/bin/activate
python scripts/run_cross_venue_live.py --ops-stats          # operational stats, never reads outcomes
python scripts/run_cross_venue_live.py --refresh            # refresh pairs now
python scripts/run_cross_venue_live.py --outcomes           # recover/write due outcomes (offline)
python scripts/run_cross_venue_live.py --analyze <effective start, >= 2026-10-13T00:00:00Z> 2026-11-03T00:00:00Z   # once, after 2026-11-03T02:00Z
launchctl kickstart -k gui/$(id -u)/com.arepo.cross-venue-live   # restart
launchctl bootout gui/$(id -u)/com.arepo.cross-venue-live        # stop
pytest tests/test_research_lab_cross_venue_live.py && ruff check astrolabe/research_lab/cross_venue_live.py scripts/run_cross_venue_live.py
```

## E010 on the same stream (2026-10-13)
`backend/astrolabe/research_lab/cross_venue_live_e010.py` (`E010Writer`, hooked into `Poller.extras`) writes hourly-origin
predictions of a model refitted once on the cleaned historical set C1 (316 pairs; spec `model_specs/cross_venue_live_e010_v1.json`,
sha256 `62b992c6...961c`) to `predictions_e010.jsonl`, and +60/+360 min outcomes with paper taker P&L to `outcomes_e010.jsonl`.
Retired pairs are now polled 6 h 20 min. E009 is unchanged. Registration, dependence on E009 and MDE: ledger E010.
`python scripts/run_cross_venue_live.py --analyze-e010 <effective start> 2026-11-03T00:00:00Z` once, after 2026-11-03T08:00Z.
Tests: `backend/tests/test_research_lab_cross_venue_live_e010.py`.
