# AREPO feature-discovery programme (2026-10-11)

**Status:** programme map and governance proposal. It does not freeze anything, does not change any registered
experiment, and makes no edge claim. Section 3 needs an accepting `science-reviewer` pass before it binds a
registration. Data-driven model weights only: the legacy v1 score (`evaluation/research_predictors.py`) is a baseline.

**Objective (user, 2026-10-11).** Find which observable features, combinations, interactions, thresholds and
regime-dependent relationships predict future Polymarket price movement. Weights are learned from data. Strict
chronological out-of-sample validation, then prospective confirmation, then a separate economic check.

Builds on, and does not replace: `MULTI_SIGNAL_PIPELINE_DESIGN.md` (MC1 design, reviewed), `EXPERIMENT_LEDGER.md`,
`DEPENDENCE_CLUSTERING_ANALYSIS.md`, `../research/2026-09-20/` (F01-F60, H01-H60, model protocol), architecture §6
(`../research/2026-10-10-architecture/AREPO_FUTURE_ARCHITECTURE_2026-10-10.md`) and the historical-data handoff
(`../research/2026-10-11-historical-data/HANDOFF.md`). Parallel work in progress, referenced not duplicated:
**(a)** historical backfill (CLOB prices-history, Data API trades); **(b)** wallet and trade-flow features with
hashed wallet ids; **(c)** interpretability module (family ablations, conditional permutation importance, ALE,
SHAP interactions, regime splits); **(d)** multi-horizon and magnitude targets in `ml_panel`.

## 1. Mapping: objective against existing work

| Objective element | Where | Status |
|---|---|---|
| Baselines B0-B3, frozen E002 reversal | `research_lab/models.py`, `model_specs/e002_reversal_v1.json`, Phase 4 plan | Implemented |
| M0 price+momentum multinomial baseline | `research_lab/ml_models.py` (`fit_m0`) | Implemented |
| Elastic net (M1, splines, declared `chg_1h` interactions) | `ml_models.py` (`fit_m1`), design §3 | Implemented |
| GBM (M2 LightGBM, 20-config search, early stopping) | `ml_models.py` (`fit_m2`) | Implemented |
| Bayesian hierarchical (M3_eb, Laplace-EM; NumPyro M3 later) | `ml_models.py` (`BayesHier`), design §9 amendment A1 | Implemented (A1 pending review); NumPyro planned |
| Ensembles (E50, EW, ES, EG) | design §3 (E50 only), `../research/2026-09-20/MODEL_COMPARISON_AND_VALIDATION.md` §8, Phase 7 | Planned |
| Feature registry with label guard, families, versions | `research_lab/features.py` (`register`, `LABEL_COLUMNS`), `ml_panel.register_ml` | Implemented |
| Point-in-time panel, purge + embargo, hashed fold manifest | `ml_panel.py`, `evaluate.purged_train_mask` | Implemented |
| Dependence clustering (fixture-day + event; season sensitivity) | `ml_panel.dep_group`, `DEPENDENCE_CLUSTERING_ANALYSIS.md` | Implemented |
| Clustered paired bootstrap, MDE | `compare.paired_bootstrap`, `power.py`, `ml_models.score_arms` | Implemented |
| Trial logging (every dev run) | `provenance.append_trial` -> `trials.jsonl` | Implemented |
| Placebos (shuffled labels, leak control, quote-age-only) | `scripts/run_ml_dev.py` | Implemented |
| Development runner, 40-snapshot gate | `scripts/run_ml_dev.py` | Implemented, waiting for data (~14-15 Oct) |
| OOF TreeSHAP and linear SHAP, family sums | `ml_models.tree_shap`, `summarize_shap` | Implemented |
| Family ablations, conditional permutation, ALE, SHAP interactions, regime splits | agent (c) | In progress |
| Direction target T1 (δ = 0.005) | `ml_panel.assign_class` | Implemented |
| Magnitude, multi-horizon targets | agent (d); T2/T1-24 defined in design §1 | In progress |
| Resolution target T5 / MC2 | design §5 (MC2); C1 study in ledger | Planned |
| Executable-opportunity target (net P&L, H2a/H2b) | design §5; `ml_econ.py` (Task 7) | Planned (fee table P1 open) |
| Prospective confirmation, one model, fixed sequence | design §5 (MC1) | Planned (needs dev run) |
| Discovery governance: budget, hierarchy, promotion ladder | this document §3 | Proposed here |
| Historical exploratory data and sealed holdouts | historical handoff §4; agent (a) | Researched; adapter in progress |
| Regime breaks (CLOB V2, fee and tick eras) | `../research/2026-10-11-market-structure/POLYMARKET_REGIME_TIMELINE.md` | Researched |
| Wallet features (as-of) | Phase 5 plan; F03-F06, F33-F35; agent (b) | In progress (hashed ids) |
| External information | `../research/2026-09-20/EXTERNAL_SOURCE_REGISTER.md`; design §2 tier (b) | Researched; not collected |

Roughly: modelling, validation and attribution machinery are implemented; interpretability depth, extra
targets, wallet and historical features are in progress; ensembles, resolution/economic targets, external
features and the cross-cycle discovery governance were missing or only planned.

## 2. Feature families

PIT = point-in-time feasibility. "Now" = collected by the launchd loop (`com.arepo.collector`, 2-hourly).

| Family | Register IDs | Collected now | Missing | PIT feasibility |
|---|---|---|---|---|
| Market state | F25, F39-F43 (+ a1-a8, a12) | Complete-universe Gamma snapshots; sidecar v3 (fees, tick, min size, createdAt, rewards, OI, comments, parentEventId); own-history Δmid, volatility | Within-period price path; tick-transition events (F43); reward changes over time (F42) | Good on own receipt clock. Gamma `chg_*`/`updatedAt` latency unknown; cumulative fields origin-only (design §2) |
| Order book | F08-F10, F23-F24, F26-F27 | `book_sweep.py`: 2 sweeps per pass, top imbalance, microprice, 1c/5c depth (`ml_panel` `book` family) | WS deltas (F10, F23 OFI, F24 resiliency), sub-hour series | Sweep lands 7-8 min after its snapshot; sweep-gap diagnostic is mandatory. pmxt v2 gives historical L2 (dev only) |
| Trade flow | F01, F02, F07, F11-F13, F28-F32 | `trade_sample.py`: 2,000-market probability sample per pass, taker-only, no wallets; `flow_screen.py` F1-F4; E007 | Census of the active frame; maker side; F13 needs event schedules | Trade timestamps are on-chain-anchored. 51% of eligible markets never trade (ledger D1): flow models need an active-frame population with inclusion probabilities |
| Wallet behaviour | F03-F06, F21, F33-F35, F55 | None (wallet fields deliberately dropped) | New wallets (F03/F04), concentration (F05), coordinated wallets (F35 co-trading graph), as-of history/skill (F06, F34, F55), inventory (F33), exposure / liquidity (F01 with per-wallet net) | Agent (b), hashed ids. First-seen is left-censored at coverage start (record coverage start). Skill uses only labels matured before origin. Graphs past-only. Never labelled insider trading |
| Market relationships | F15, F36-F38, F60 | Neg-risk excess (a9), sibling `chg_1h` (a10), dependence groups; E005, L1 | Nested-threshold map (F38), related-lead residualisation (F15), cross-venue (F36) | Same-scan siblings arrive minutes later but precede target. Group maps must be as-of |
| External information | F14, F16-F20, F44-F54, F56-F59 | None | All of tier (b) and (c) in design §2 | See §6. Only live-received values count prospectively |

New candidates outside F01-F60 get IDs `FX01...` in the ledger methods note that introduces them, with the same
fields as the register (definition, inputs, availability, mechanism, falsification).

## 3. Discovery governance

**Entry.** A candidate enters as a ledger line: register ID, family, definition, PIT note (source clock, receipt
clock, lag), expected coverage and cost. It is implemented only through `features.register` /
`ml_panel.register_ml` with a declared family and version (the label guard and `is_origin_side` apply). New
families are added to `features.FAMILIES` (e.g. `ml_flow`, `ml_wallet`, `ml_external`) before any fit.

**Ranking (before fitting).** Prior plausibility (register priority, mechanism), PIT cleanliness, coverage in the
target population, collection cost. After a dev run: family ablation ΔLL with dependence-group CI, conditional
permutation importance, fold-to-fold rank stability, and agreement across regimes.

**Hierarchical testing order (per development cycle).**
1. **Family level** (≤ 8 families): drop-one-family ablations against the full candidate model, and add-one-family
   against M0. Only families whose ablation ΔLL interval excludes 0 under both cluster definitions advance.
2. **Feature level**, inside surviving families only: grouped/conditional permutation (permute within strata of
   correlated partners), never raw marginal importance alone.
3. **Interactions and thresholds**, among features from surviving families only: rank candidates by mean |SHAP
   interaction| and Friedman H on OOF rows, confirm the shape with 2-D ALE. Cap: ≤ 10 interaction pairs carried
   forward per cycle.
4. **Regimes**, from a pre-declared list only: probability level (`|mid-0.5|`), liquidity tercile, time to end,
   `fee_category`, trade-active flag, fee/tick era, short-duration crypto. ≤ 5 regime variables per cycle.
   A regime effect is a stable sign/size difference across folds, not a single split that looks good.

**Search budget and multiple testing.**
- Keep the design §3 caps: ≤ 3 feature-set revisions after the first dev run, one arm selection, one τ selection.
- Development screens produce rankings and descriptive intervals, never p-value claims. Every attempt (feature,
  interaction, threshold, regime, horizon) is a `trials.jsonl` line; the trial count is reported in every
  registration.
- Triage label: Benjamini-Yekutieli FDR at q = 0.10 across the family screen (valid under dependence), then within
  surviving families. Labels are "screen-positive", nothing more.
- Confirmation spends α once per registration: one confirmatory model per cycle (the MC1 pattern), fixed-sequence
  gatekeeping or Holm within a declared family, 2-4 concurrent confirmatory slots (Phase 4 governance item 6).
- **Dev vs confirmation split:** development = everything before the registration commit (plus sealed historical
  holdouts, ≤ 3 reads per source, handoff §4); confirmation = origins strictly after the commit. Confirmation data
  are never used to rank, select or tune. A finding found on a dataset cannot be confirmed on the same dataset.
- **Selection bias:** expect shrinkage (E002 kept ~2/3 of its dev effect). The registered MDE uses the dev `sd_c`;
  report the dev estimate next to the confirmation estimate.

**Promotion ladder** (each rung recorded in the ledger; no rung skipped).

| Rung | Label | Requirement |
|---|---|---|
| L0 | Candidate | Ledger line, PIT note, registered feature spec |
| L1 | Exploratory | Appears in a logged dev run (ablation, SHAP, screen). Hypothesis-generating only |
| L2 | Dev-validated | Purged walk-forward OOF gain with both cluster CIs excluding 0; passes placebos (shuffled labels, future shift, quote-age-only, sweep-gap); stable sign across ≥ 2/3 of test blocks; where available, survives one sealed historical holdout read |
| L3 | Registered | Ledger registration, MDE, frozen artifacts (sha256), accepting `science-reviewer` pass |
| L4 | Prospectively confirmed | Scored once under the registration; verdict recorded whatever its sign |
| L5 | Economically checked | Separate H2a/H2b-style test at stated size, spread, fees; still "optimistic, not tradable" |

Promotion beyond L5 goes to Phase 8/10 review. Negative and inconclusive results stay in the ledger at their rung.

## 4. Targets

Each target is scored separately; one model never stands for another target.

| Target | Definition | Loss / metric | Evidence standard |
|---|---|---|---|
| Direction (T1) | 3-class Gamma-mid move, δ = 0.005 (0.01 sensitivity), next snapshot | Multiclass log loss (primary), Brier, calibration slope | MC1 H1: relative ΔLL > 0, CI excludes 0 under both clusters, ≥ 17/24 periods positive |
| Magnitude (T2, \|T2\|) | `dmid`, logit change, absolute change; 2h and 24h (agent d) | MAE, R²_oos vs no-change and frozen E002; CRPS/pinball if quantiles | Secondary in MC1; own registration to be primary |
| Future probability | Distribution of `mid` at t+h | CRPS or quantile (pinball) loss; PIT-histogram calibration | Development until a registration; never presented as event probability |
| Resolution (T5) | Payout of outcome 0, markets closing in 1-7 days, proposal-state excluded at origin | Log loss / Brier vs recalibrated market price | MC2, separate registration; needs a resolution-label collector |
| Executable opportunity | Net P&L at q shares: entry at ask, exit at next sweep bid, both taker fees | Mean net P&L per trade; paired F*-vs-M0 P&L | H2a/H2b one-sided bootstrap lower bound > 0 under both clusters; ≥ 30 trades, ≥ 10 clusters |

First passage (T3) and path extrema (T4) stay out of scope until dense quote paths exist.

## 5. Historical data

- **Sufficient to start development:** about 30+ independent days with ≥ several thousand dependence groups
  per family screen. Available: pmxt v2 post-V2 window (2026-04-29 to 06-04, ~36 days of L2 and prints); on-chain
  fills with wallets 2022-11 to 2025-12 (dev window, regime-stratified by fee era); AREPO's own snapshots (~40 for
  the MC1 dev run). Agent (a) adds CLOB prices-history (server-resampled, so usable for labels and coarse
  momentum, not as point-in-time features) and Data API trades.
- **First use:** estimate per-day variance of ΔLL to set MDEs, and run the family-level screen on flow and wallet
  families, which our own collection cannot yet supply at depth.
- **Labelling** (`evidence_role` in every manifest and trial): `development` (own pre-registration data or
  historical dev windows); `historical_holdout` ("historical out-of-sample, third-party, post-hoc-selected
  source, possibly different regime"); `prospective_confirmation` (own data after a registration commit only).
  Historical results can reach L2, never L4. Transport to AREPO's full universe is never assumed.
- Regime stratification and short-duration crypto separation follow the handoff §4. Gaps stay missing.

## 6. External information (later)

Admission rule (design §2 tier b): free, no key, live-collected, value used only if received before `t0`;
backfill is development-only.

| Source | Feature | Clock | Main leakage risk |
|---|---|---|---|
| Coinbase public / Polymarket RTDS | F14/F44 spot vs strike, spot returns | Exchange tick timestamps | Low live; strike/expiry matching errors |
| Deribit public | Implied vol -> digital probability | Live only | Historical IV snapshots not PIT |
| GDELT 2.0 15-min files | F16 news acceleration, F20 corroboration | File publish time | Re-processed/late GKG records; entity map built with hindsight; use publish time, freeze map |
| Kalshi public market data | F36 cross-venue gap | Request time | Rule matching informed by resolved outcomes |
| NWS api.weather.gov | F47 forecast innovation | Issue time in payload | No archive (prospective only); observation lag |
| Wikimedia pageviews | F50 attention | Daily, published with lag | Use only fully published days; 24h/T5 only |
| SEC EDGAR, BLS | F45/F48 surprise | Acceptance / release time | Revised vintages; few markets, low power |

Text and LLM features (F17, F51, F54) carry historical-knowledge leakage and stay in tier (c). Order: crypto
spot/IV, then GDELT, then Kalshi.

## 7. Next steps (ordered)

1. Land agents (a)-(d) with tests; register their features under declared families (`ml_flow`, `ml_wallet`)
   and their targets under versioned names; nothing enters the MC1 feature set retroactively.
2. `science-reviewer` pass on §3 of this document; on acceptance add a ledger methods note (M3) adopting the
   ladder, budget and BY triage.
3. MC1 development run (`scripts/run_ml_dev.py`, gate ~14-15 Oct): all arms, family ablations, SHAP, placebos;
   ranks tier-(a) families (L1/L2).
4. Historical family screen for trade-flow and wallet families on the dev windows (agent a/b data), regime
   stratified; one holdout read only for families that reach L2 on dev data.
5. Interaction and regime screen (step 3 of §3) on surviving families, using agent (c) tools.
6. Register MC1 (and, if justified, a separate active-frame flow/wallet model) for prospective confirmation.
7. Economic check (H2a/H2b) only after predictive support; fee table P1 first.
8. Tier-(b) adapters one at a time (crypto spot/IV first), each with its own admission note and fresh dev data.
9. Resolution-label collector, then MC2 (T5).
10. Ensembles (Phase 7) only once ≥ 2 locked constituents exist.
