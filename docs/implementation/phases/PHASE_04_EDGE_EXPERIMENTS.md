# Phase 04 — Baselines and edge experiments

Status: **IN PROGRESS — Phase 3 closed with limitation (D117, 2026-10-11).** Track A (D115) research-lab
infrastructure already exists and has produced E001-E003 and E002 results. Every finding is exploratory and
non-validated until Phase 3 closure is confirmed; no edge, calibration or profitability claim exists.
Refreshed 2026-10-11 against actual code and ledger. Supersedes the earlier provisional template.

## Objective

Run a small number of pre-registered, event-clustered, prospectively confirmed experiments that test whether
information beyond price and momentum predicts repricing, always against locked simple baselines, and produce
honest positive, negative and inconclusive verdicts. Output is knowledge and a trustworthy experiment ledger,
not a product signal.

## What Phase 3 hands over

- D116 outcome `PASS_WITH_LIMITATION:no_eligible_untriggered` (`../PHASE_03_D116_EVIDENCE.json`): E0-E9 passed,
  4 complete chains, 0 engineering findings. Per D115 item 5 (`../AREPO_V2_DECISIONS.md`) this permits closure.
  D089-era availability gates are reclassified as diagnostics for D116 onward only; D089/D094/D097/D114 keep
  their failed outcomes.
- **Known limitation: control pairing never formed live (D097 and D116).** The panel's matched trigger/control
  design is therefore machinery-validated only (causal clocks, freezing, sampling, target plumbing). It has never
  produced a matched pair, so Phase 4 must NOT rely on the panel's matched-control comparison for any effect
  estimate. Phase 4 experiments use the research-lab design instead: complete-universe snapshots, all
  E001-eligible markets, no-change and simple-model comparators, event-clustered inference. Panel machinery is
  reused only for provenance, clocks and freezing rules. Revisit matched controls only if a registered design
  first shows that eligible untriggered members exist in sufficient number.
- Contracts: `../PHASE_03_DATA_BOUNDARY.md`, `../../AREPO_V2_PHASE_3_HANDOVER.md`, `../../architecture/`.

## Data actually available (limits stated)

All under `data-dumps/research_lab/` (read-only for experiments; never edit canonical runs).

| Source | Code | Limits |
|---|---|---|
| Complete-universe Gamma snapshots, ~2-hourly loop (Parquet+zstd via `columnar.py`, immutable ID map) | `collector.py`, `columnar.py`, `panel.py` | Binary markets only; Gamma-computed change fields have unknown latency; 68% of tokens lack `chg_1h`; capture spans of minutes, not simultaneous; the E004 loop covers about 1 calendar day, i.e. 1-2 independent time blocks; laptop collector can have gaps (flag gaps over 3h, never backfill). |
| Dev snapshots (`dev_snapshots_v2`, E001 CSV captures) | `extract.py`, `features_dev.py` | Development only; not collected under a frozen design; CSVs are lossy-parsed; unlimited use but every run logged. |
| CLOB book sweeps (outcome-0 token, `POST /books`) | `book_sweep.py` | Top-of-book and depth snapshots of eligible markets only; sequential batches so book time differs by market; minutes-scale targets only (E003). |
| Forecast log (append-only) | `forecast.py` | Frozen-model forecasts logged before outcomes; only E002's reversal spec exists (`model_specs/e002_reversal_v1.json`). |
| Trade sampler (stratified probability sample, Data API `/trades`) | `trade_sample.py` | Code exists with sealed seed and inclusion probabilities; no collected trade panel is recorded in the ledger yet; taker-only pages; wallets never stored; recent trades only (backfill depth unknown, to be probed). |

Not available: L2 depth history beyond sweeps, news/social/external-venue feeds, wallet history, resolution
labels at scale from the lab pipeline. Anything needing these is blocked until a bounded registered collection
exists (architecture doc §9.2).

**Third-party historical data (development only; not integrated).**
- `../../research/2026-10-11-historical-data/HANDOFF.md` assesses free historical sources that partly fill the gaps above. Read it before building depth, trade-flow or wallet features:
  - pmxt v2 provides L2 books and trade prints for 2026-04-13 to 08-10;
  - an on-chain trades and wallets dataset covers 2022-11 to 2026-03.
- The handoff gives sealed holdout windows (embargoes, read budget), a working demo template and a minimal adapter plan.
- Historical results are development evidence only, never prospective confirmation.
- **Regime breaks.** Before pooling across dates or interpreting fees and ticks, see `../../research/2026-10-11-market-structure/POLYMARKET_REGIME_TIMELINE.md`. It covers CLOB V2 on 2026-04-28, fee regimes by market creation date, tick-size regimes, and short-duration crypto markets from ~2025-10.

## Baselines (locked; every experiment names its version)

Definitions follow `../../research/2026-09-20/MODEL_COMPARISON_AND_VALIDATION.md` §4 and E001 in
`../../research_lab/EXPERIMENT_LEDGER.md`.

| ID | Definition | Status / code |
|---|---|---|
| B0 | No-change (`dmid_hat = 0`) | Exists: `models.py`. |
| B1 | Momentum/reversal on trailing change. E001's 1d and 1h variants; the frozen reversal spec `dmid_hat = -0.331610 * chg_1h` | Exists: `models.py`, frozen at `model_specs/e002_reversal_v1.json`. E001/E002 show the sign is reversal, not momentum. |
| B2 | Price/context ridge (mid + 1h/1d/1w changes) | Exists: `models.py`, `features.py`. |
| B3 | Full E001 context ridge (adds spread, liquidity, volume, time-to-end, last-trade gap, interaction) | Exists: `models.py`, `features.py`; reproduced to 1.6e-13 by `compare.py` preset `e001_repro`. |
| B4 | Domain baseline (rule-aware asset threshold, official forecast, cross-venue probability) | **Not implemented; no data source ingested.** Only relevant to resolution-target and external-lead experiments (H14, H36, H44, H47). Any such experiment must first define B4 in its registration. |
| v1 | Legacy AREPO score replay (`evaluation/research_predictors.py`) | Pinned reference only; reproduce where a registration needs it. |

**Rule:** every experiment reports its model vs B0 AND vs the strongest simple baseline available at registration
(currently the frozen B1 reversal; for book-timescale targets, B1 plus spread/intercept terms, per the E003
lesson). A gain over B0 alone is not a finding. Fit baseline transforms in development only.

## Governance (binding on every registration)

Sources: architecture doc §6 and §9.1 (`../../research/2026-10-10-architecture/AREPO_FUTURE_ARCHITECTURE_2026-10-10.md`),
ledger Methods notes M1/M2.

1. **Pre-register before any outcome**: question, data, unit, features, models, split, metric, interpretation
   rule, non-claims, committed to `EXPERIMENT_LEDGER.md` before outcomes exist. Later edits only add results or
   disclosed deviations. Never change a threshold or formula to obtain a pass.
2. **Dev vs confirmation windows**: development data are unlimited but every run is appended to
   `docs/research_lab/trials.jsonl` (`provenance.append_trial`; code hash, dirty flag, environment). Confirmation
   uses only origins strictly after the registration commit, in a window declared at registration; drop origins
   whose label window crosses the window edge. Frozen coefficients are never refit.
3. **MDE per registration** via `power.py` (M2): state the minimum detectable effect, required clusters and the
   design effect; treat DeltaR2 < 0.02 as out of reach until months of independent days exist.
4. **Clustering**: event-clustered bootstrap by default (1,000 resamples, seed 116, `market_id` fallback counted).
   Market clustering overstates precision (M1: CI widens roughly 4x).
5. **Time**: report per-period and per-day results; time-block inference; consecutive ~2h periods are not
   independent. Two-way clustering is unreliable below about 20 time clusters.
6. **Multiplicity**: pre-declared alpha, Holm within a declared family, tracked in the ledger. 2-4 concurrent
   confirmatory slots; 60 candidate experiments do not run at once.
7. **Challenger review**: a `science-reviewer` pass on each registration before the collection that confirms it
   starts, and on each verdict before it is relied upon.
8. **Unit/leakage tests**: features from origin columns only (`features.py` refuses label-side columns), purge by
   actual label availability, future-shift placebo, equal-origin parity across models.
9. All verdicts are preserved: positive, negative, inconclusive, invalid, unavailable.

## Experiment queue (prioritised)

Priorities from `../../research/2026-09-20/EDGE_EXPERIMENTS.csv` (P1 = highest) combined with measured results.
Current confirmatory slots: E004, E005, E006 (three of four).

| Order | Experiment | Status | Data needed | Data exists? |
|---|---|---|---|---|
| 1 | **E004** multi-period reversal, 12 qualifying snapshots, with spread-crossing execution check | Registered, running (collection loop) | 2-hourly snapshots | Yes, accruing. Covers ~1 day; verdict is a consistency check, not independent days. |
| 2 | **E005** neg-risk arbitrage-band deviation (H37-type coherence) beyond reversal | Registered, running; dev fit frozen (in-sample incremental R2 ~2e-5, expect inconclusive) | Same snapshots plus neg-risk columns | Yes |
| 3 | **E006** reversal moderation by liquidity (H1) and time-to-end (H2) | Registered, running; dev fit frozen, H1 weakly identified (disclosed) | Same snapshots | Yes |
| 4 | **Trade-flow family** (H01/H02 size vs liquidity/depth, H05/H11/H12/H29 flow shape; wallet fields excluded) via `trade_sample.py` | Next candidate; needs registration, a bounded backfill-availability probe and a collected sample | Stratified trade sample with inclusion probabilities, plus snapshots for targets | Code yes; collected data no |
| 5 | **Book signals conditional on tight books** (H08/H09, H23-H25, H27) | Candidate. E003 found imbalance/microprice inconclusive and the model gain driven by spread/intercept drift in wide-spread markets; re-test only in tight-spread strata with a spread-aware baseline | Book sweeps, ideally a one-day hourly series | Sweeps yes; hourly series no |
| 6 | **Related-market families** (H15 related lead, H37/H38 coherence beyond neg-risk) | Candidate after E005 verdict | Event/group structure from snapshots | Partly (event ids present; nested-threshold mapping not built) |
| 7 | **Reversal tradability** (H27/H28 persistence and impact reversal after spread, depth and fees) | Candidate after E004 execution check | Book sweeps at origin and later quotes | Partial |
| Later | External/news/wallet/social (H14, H16-H22, H36, H44-H50) | Blocked | External feeds, B4 baselines | No |

Rules for adding to the queue: one registration per question; no new experiment fills a slot until a current
one has a scored verdict; post hoc dev screens (`features_dev.py` style) generate hypotheses, never evidence.

## Multi-signal and feature-discovery track (user direction, 2026-10-11)

- Edge search now runs mainly through combined models with attribution, not single E-tests:
  `../../research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md` (MC1, reviewed and accepted).
- Cross-cycle feature, interaction and regime discovery, the promotion ladder (exploratory, dev-validated,
  registered, prospectively confirmed, economically checked) and the search budget are in
  `../../research_lab/FEATURE_DISCOVERY_PROGRAMME.md` (science-reviewer: ACCEPT_WITH_CHANGES, applied).
- **Amendment A-ML1 (2026-10-11; resolves the conflict with the Stage-2 non-goal).**
  1. In the multi-signal track, M2 (LightGBM), M3 (hierarchical) and E50 are **development challengers only**.
  2. F\* defaults to M1 (elastic net). A complex arm replaces M1 only if all hold: its paired ΔLL vs M1 has a CI
     excluding 0 under both cluster definitions; its sign is stable in ≥ 2/3 of test blocks; and the development
     span covers ≥ 16 independent days (the Stage-2 day count).
  3. The Stage-2 non-goal below otherwise stands, and still governs every other registration.

## Data-readiness criteria

- **Registering a confirmatory test**: data exist or a registered collection is running, power statement shows the
  target effect is detectable at the expected cluster count, and the dev/confirmation split is declared.
- **Stage-2 models (LightGBM, hierarchical Bayesian)**: an effect that survived development AND confirmation,
  with at least 16 independent days and at least 50k event clusters (architecture doc §6). Until then ridge/OLS only.
- **Stage 1 storage triggers** (Parquet ID map in place; generic scoring): more than 30 snapshots, 3 GB of frames
  or 10 experiments. Archive backup (§9.1) precedes any space recovery; no retirement without explicit approval.
- Independent time blocks, not period counts, decide whether a result may be called confirmed.

## Exit criteria

- [ ] Phase 3 closure confirmed (D116 review) and recorded in the checkpoint.
- [ ] B0-B3 frozen with exact versions and reproducible (met in code); B4 status stated per experiment.
- [ ] E004, E005, E006 scored once each under their registered rules, with MDE, per-day and event-clustered
      results, and execution check; verdicts recorded whatever their sign.
- [ ] At least one further registered experiment from the queue (item 4 or 5) scored or blocked on documented data.
- [ ] `trials.jsonl` complete; ledger, decisions log and checkpoint current; data-readiness report written
      stating how many independent days exist and what Stage 2 would still need.
- [ ] Tests: `cd backend && source .venv/bin/activate && pytest tests -k research_lab && ruff check astrolabe/research_lab`.
- [ ] Diff reviewed for leakage, repeated-row inflation and protected boundaries.

## Non-goals

- No nonlinear, boosted or Bayesian models before the Stage-2 trigger; no ensembles before Stage 3.
- No product promotion of any signal (forecast cards, alerts, rankings) before prospective confirmation plus an
  economic check (spread, depth, fees). Midpoint reversal is not executable value.
- No matched-control claims from the Phase 3 panel; no pooling, redrawing, relabelling or backfilling of old pilots.
- No retention changes, deletion, production migration, deploy, trades or paid purchases; no wallet identifiers stored.
- No synthetic data as scientific evidence; synthetic effects test machinery only.

## Protected boundaries

Never fabricate prospective observations, tune on confirmation data, or treat repeated rows as independent events.
Missing data stays missing. A protected action needs the user's explicit decision; record
BLOCKED - USER DECISION REQUIRED with the concrete action.
