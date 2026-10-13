# AREPO v2 live checkpoint

**PHASE 3 CLOSED.**
- D116 was PASS_WITH_LIMITATION, giving D117.
- D118 then PASSED live on 2026-10-11, validating the control-pairing *mechanism* on liquid markets (D119).
  - Scope and disclosures: `implementation/d118/D118_ADDENDUM.md`. Pair 1 was very probably sibling markets; 5 of 7 triggers had no control.

**PHASE 4 IN PROGRESS.** See `implementation/phases/PHASE_04_EDGE_EXPERIMENTS.md` and the ledger `research_lab/EXPERIMENT_LEDGER.md`.
User dashboard: `AREPO_PROGRESS_PLAIN_ENGLISH.md`; its `Last updated` uses `TZ=Etc/GMT-1 date`.

## Standing user decisions
- Work autonomously. Use parallel agents where there is real cause.
- Specialists: Opus max, or Fable 5.1 used sparingly. Extra credits are off.
- Never hold two multi-GB jobs at once.
- Data rights are out of scope (private phase).
- **Category scope is undecided**: sports inclusion is the user's later call, so designs stay category-agnostic with category as a parameter.
- **Trading engine:** a possible far-future feature only. Do not touch the trading or execution plans committed by another session.
- Website wording, physical backup and compression are parked.
- Bypass permissions mode is persisted in `.claude/settings.local.json`. The `git push` ask rule has been removed. Branch-delete and worktree-remove asks remain; do not use them.

## State (2026-10-11 ~13:45Z)
- **Branch:** `chore/arepo-claude-setup`, pushed. Production is untouched. Another session also commits here, so commit only your own files.
- **Backup:** private repo `dayyansheikh/arepo-data`, release `data-20261011`, verified. The local archive parts were deleted 13:4xZ with user approval after a hash re-check; the local manifest and index files remain.
- **Disk:** about 16.3 GB free. D120 launch needs 15,382,085,632 B.

## Multi-signal ML pipeline (user direction, 2026-10-11)
Edge search now goes through combined models plus SHAP, not a chain of single E-tests (memory `multi-signal-ml-direction`).
- **Design:** `research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md`. Reviewed twice and accepted; amendment A1 (M3 Laplace-EM, fixed-effect categories) has been re-simulated.
- **Target:** 3-class Gamma-mid move over the next snapshot, δ = 0.005.
- **Confirmation:** one model, fixed-sequence H1 (log loss vs M0), then H2a/H2b (economic). Needs ≥40 development snapshots plus 24 test periods.
- **Code:**
  - `ml_panel.py` (latest 6c5a074): pairs, features, sweep A features, siblings, dependence groups, fold plan, sweep-gap diagnostic.
  - `ml_models.py` (a1de02e): M0, elastic net, LightGBM (20-config search), M3_eb, clustered bootstrap, OOF SHAP, trials logging.
  - `requirements-research.txt` and `scripts/research_ml_setup.sh` (libomp workaround).
- **Sidecar:** `ext_sidecar.py` writes `rows_ext.csv.gz` per snapshot (v2, from pass 7 on). Main files are byte-identical.
- **Clustering:** `research_lab/DEPENDENCE_CLUSTERING_ANALYSIS.md` (393249a) concludes ML co-primary = fixture-day groups (event ∪ parentEventId ∪ negRisk ∪ series×UTC day ∪ underlying), with season-level as a sensitivity.
  - Done: ml_panel uses fixture-day `dep_group` plus `dep_group_season`; sidecar v3 adds parentEventId (pass 9 onwards).
- **Runner:** `scripts/run_ml_dev.py` (87fb74c). Gate: 40 consecutive complete snapshots with sidecar, which means about 14–15 Oct. `--dry-run` is available. Placebos are being added.

## Experiments
- E002: Confirmed (exploratory). E003: inconclusive.
- E004/E005/E006: 9 of 12 qualifying. Passes run at 18:31Z, 20:31Z and 22:31Z. Score at 12.
- E007: 2 of 12. Deadline 2026-10-18.
- **Collection is now a user-approved launchd job, `com.arepo.collector`** (installed 2026-10-11). It runs every even UTC hour at :31, doing snapshot, forecast, sweeps, trades, flow screen and E004/E007 status.
  - Script: `~/arepo_collector/arepo_pass.sh`. Logs: `~/arepo_collector/logs/`.
  - Do NOT chain session passes while it is loaded. Commit trials.jsonl lines periodically.
  - Avoid heavy jobs and live launches at :25–:50 after even UTC hours.
  - Remove it when collection ends (about 15 Oct) with `launchctl unload` plus deleting the plist.

## D120 (pairing redesign): PASS
- Frozen at 04e71ea (record ea29ae6). Launched once at 14:47Z (HEAD 47375bc).
- Evaluator: PASS, 6/6 group-disjoint complete pairs, 0 engineering findings.
- Challenger: PASS_WITH_CAVEATS. Economics pair shares a driver; reliability is untested.
- Evidence `PHASE_03_D120_EVIDENCE.json`, addendum `d120/D120_ADDENDUM.md`, decision D120/D121 (86004ed).

## Hourly update job
Cancelled by the user at about 18:30 UTC+1 on 2026-10-11 (cron `dbea28e0` deleted).

## Feature-discovery programme (user objective, 2026-10-11 evening)
- **Mapping and governance:** `research_lab/FEATURE_DISCOVERY_PROGRAMME.md` (09afff6), plus Phase 4 amendment A-ML1. M1 is the default F*. Complex arms must beat M1 (CI under both clusterings, ≥2/3 blocks stable, ≥16 dev days). Budgets are cumulative.
- **Done:**
  - `flow_features.py` and `wallet_sidecar.py` (b3923b5): HMAC wallet hashes; E007 files unchanged.
  - `ml_explain.py`: ranks by incremental out-of-sample ΔLL; `demonstrated_incremental_value` vs `descriptive_only`.
  - Horizons h1/h3/h12 plus magnitude and binary targets (389a677).
- **Running agents (usage budget high until Wed 14 Oct; user asked for max progress):**
  - `history_backfill` (CLOB prices-history plus Data API trades; exploratory_historical);
  - non-sports dependence analysis (Opus max);
  - integration (flow/wallet into the panel, evidence_role enforcement, cumulative counter);
  - `history_sources` (historical books, on-chain wallet history);
  - `resolution_dev` (T5 resolution forecasting, Opus);
  - `external_news` (GDELT);
  - `economics` (fees, slippage, paper P&L, break-even).
- **Disk caps:** history 1.5 GB, sources 1 GB, resolution 2 GB, news 0.5 GB.

## Unusual pre-news flow programme (the user's founding goal: Maduro-style signals)
**Design and tooling**
- Programme (Fable): `research_lab/UNUSUAL_FLOW_PROGRAMME.md` and `detector_eval.py`.
- 5 variants FINAL FREEZE at 692ab61 (`UNUSUAL_FLOW_DETECTOR.md`). IF-H1 frozen as f92952cb.
- Theory (Opus max): `INFORMED_FLOW_SIGNAL_THEORY.md`.

**Results**
- Maduro (`CASE_STUDY_MADURO.md`): striking but not unusual against the market's own history.
- Broad backtest and census revision (7dbc7bf): nothing significant; underpowered (26–80 alert episodes against 200–800 needed). Lead only: `uf_new_wallet_concentration` lift 6.9, nominal p 0.045.
- Held-out cases (`CASE_CATALOGUE.md`, 11 cases): alerts before 4/10, but always 36–52h early. The reported flows came in the final hours.
- Cumulative detector trials: 18.

**Conclusion:** rare events can only be tested prospectively, at fine time resolution.

**Live large-trade monitor**
- `live_trade_monitor.py` (c8a291c and later): 5-minute poll of trades ≥ $1k, hashed wallets, wallet age, frozen-rule scores, matched controls, and a separate outcome writer.
- Being fixed: a causal trailing-99th-percentile alert budget with a 7-day warm-up, and a wider control pool.
- NOT installed as launchd: **this needs the user's approval.**

## Other results (overnight 11–12 Oct)
- E004 Supported but not tradable; E005 Not supported; E006 sign-only (ad55b0f).
- T5 resolution: no model beats recalibrated price. The 7d candidate was an artefact (untraded placeholder prices).
- Historical ML (`HISTORICAL_ML_DEV.md`, revisions r1–r3): against M0v, flow adds about 2% direction skill at 2h and 1% at 6h (demonstrated; possibly a series-lag artefact); wallet age shows nothing. r4_book is pending the h2 book table (background job, about 15h).
- GDELT is unusable; the Wikipedia pageviews fallback is built (574b703).
- **E007: Supported** (β 0.0036, CI [0.0017, 0.0053], 11/12 periods). The challenger confirmed it with caveats. The staleness check (dev, 7cffda0) survives excluding the last 5–15 min. Not tradable as a taker.

## Wave 3 workstreams (launched 2026-10-12 ~17:30 UTC+1; heavy-lock convention in `~/arepo_collector/heavy_lock.md`)
1. **Learned surprise-move detector** (Fable): `SURPRISE_MOVE_DETECTOR.md`. If it beats the hand rules on the test months, freeze it and add it to the live monitor.
2. **Hypothesis battery 1: DONE (development).** 72 declared (7a4d80c), one run: 18 pass cumulative BY (m=468). Survivors are flow continuation (aggressive flow strongest), reversal moderators by trade confirmation (quote noise), flow weaker at longshots/quiet markets, price-level drift and one |move| feature. Wallet, cross-market, time, category and book hypotheses are null; ladders untestable. No survivor covers taker costs. Candidates C1-C4 (not registered) are in `HYPOTHESIS_BATTERY_1.md` section 11.6. **Replication on h3_power (HB1-R, e5a3ef3): 16 of 18 replicate under Holm, no shrinkage (median ratio 1.20); still no cost viability; wallet-age nulls stay null except a weak WA2 lead** (`HYPOTHESIS_BATTERY_1_REPLICATION.md`). Cumulative tests now 494.
3. **`h3_power` backfill:** about 10k more markets, oversampling decision-asymmetric categories.
4. **Cross-venue Kalshi lead-lag:** `CROSS_VENUE_STUDY.md` (historical, L1). **Live test E009 registered** (`CROSS_VENUE_LIVE.md`, `cross_venue_live.py`): `REGISTERED_UTC` 2026-10-13T00:00Z, fixed end 2026-11-03T00:00Z, analyse once after 02:00Z that day; no interim outcome looks.
5. **Economic conditions** (liquid markets, large signals, maker-style paper analysis): `ECONOMIC_CONDITIONS_STUDY.md`.
6. **IF-H2 deadline ladder:** development, then possible E008 registration (`IF_H2_DEADLINE_LADDER.md`).

**Live jobs:** `com.arepo.cross-venue-live` (E009 poller + daily pair refresh), `com.arepo.collector`, `com.arepo.live-trade-monitor`, `com.arepo.live-trade-outcomes` and `com.arepo.notify` (ntfy topic in `~/.arepo/ntfy_topic`; the user still has to subscribe).

## Latest results (12–13 Oct)
- **Economics:** 95 conditions, none after-cost positive (`ECONOMIC_CONDITIONS_STUDY.md`).
- **Battery 1:** 72 hypotheses, 18 survive BY, none cost-viable. Flow continuation is the main real effect; wallet effects are null (`HYPOTHESIS_BATTERY_1.md`).
- **Learned surprise detector** `sm_learned_v1`: test-month lift about 4x, excess +1.8 pts, Holm p 0.008, placebo rank 1/100. It is volatility-driven. Deployed live in the monitor (`SURPRISE_MOVE_DETECTOR.md`).
- **Cross-venue:** Kalshi leads Polymarket by 10–20 min (`CROSS_VENUE_STUDY.md`).
  - **E009 registered:** live test, runs 2026-10-13 to 2026-11-03, analysed once (`CROSS_VENUE_LIVE.md`). launchd job `com.arepo.cross-venue-live`.
  - The historical pairs are being re-audited for matcher errors: 56 of 167 live pairs were wrongly matched.
- **Running:** IF-H2 (E008 is reserved for it) and `h3_power`.

## Pending user decisions (dashboard section 6)
1. Infra deploy (branch `fix/infra-2026-10-11`, bed00bb, reviewed SAFE).
2. Supabase lockdown SQL.
3. DB size: archive or Pro.
4. Resend access.
5. Optional on-chain API key.
6. Installing the live monitor permanently.

## Exact next actions
1. When pass 8 completes: run the loop steps above.
2. Placebos in run_ml_dev, then a science review of the runner, fixture-day grouping and placebos.
3. A future trigger-vs-control effect study needs repeated D120-style runs (D121).
4. At 12 qualifying snapshots, score E004/E005/E006 (tonight).

## Learned surprise-move detector (2026-10-12 evening)
`docs/research_lab/SURPRISE_MOVE_DETECTOR.md`. Labels fixed and logged before features (`surprise-labels-v1`,
sha `d9cf42f7…`), 1,186 surprise moves in `history/h2_main`, matched negatives, 83 pre-event features, three
learned arms + 5 frozen hand rules, time split train ≤ 2026-05 / valid Jun-Jul / test Aug-Oct. Test months at
the 1 % budget: `en_logit_full` precision 2.25 % vs 0.56 % base and 0.43 % matched controls (excess +1.8 pts,
Holm p 0.008, first of 100 shuffled-label placebos); hand rules 0 %. Value sits in price-path context
(`rv_1d` −, `rv_7d` +), flow/wallet families carry no demonstrated incremental value; paper P&L ≤ 0; no case
clears the budget under the frozen arm. Frozen `sm_learned_v1` (sha `ee7ea5f1…`, `FROZEN_SURPRISE.json`) and
deployed in `live_trade_monitor` v2 (prospective, unregistered). Next: let the live alert stream accumulate;
register (programme §7) only if ≥ 30 episodes with controls; do not revise features on this data window.
- **h3 replication (2026-10-13):** frozen `sm_learned_v1` as specified (direction gate on) is **null** on the
  disjoint h3 primary months (0/63 alerts, placebo rank 0.78); the gate admits only rows with 1 h flow (8 %), where
  the signal is absent. The validated ungated score replicates strongly (1 %: precision 6.5 % vs 0.87 % base,
  matched excess +5.8 pts, CI +2.6/+9.6, weighted +7.2), concentrated in sports/crypto/politics; asymmetric topics
  weak or absent. Combined h2+h3 refit: price path only; flow/wallet families still ≈ 0. Decision for the
  coordinator: freeze an ungated v2 and test it on the complete-universe passes, not the print monitor.
- **E011 registered (2026-10-13):** frozen ungated `sm_learned_v2` (sha `ee227e7e…`, identical terms to v1,
  `FROZEN_SURPRISE_SNAPSHOT.json`) scored on every complete-universe capture by
  `scripts/run_surprise_snapshot.py score` (stage-1 proxies from the rolling capture series, Spearman 0.71 on h3;
  stage-2 exact features for 400 candidates; top 60 alerts + 3 matched controls per capture written before
  outcomes; one price-history fetch per line at t + 24 h 15 min for the surprise label and moves). Window
  2026-10-13T14:00Z to 2026-11-10T00:00Z, single analysis after 2026-11-11T13:00Z (`analyze`). Primary: matched
  excess of the 6 h surprise label, event-clustered, one-sided. Reviewer ACCEPT_WITH_CHANGES applied. **User action:**
  add `caffeinate -i $PY scripts/run_surprise_snapshot.py score --rps 4 2>&1 | tail -2` after `run_flow_screen.py`
  in `~/arepo_collector/arepo_pass.sh`.
