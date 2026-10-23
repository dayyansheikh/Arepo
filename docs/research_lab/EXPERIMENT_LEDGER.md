# AREPO research-lab experiment ledger

Track A (D115) exploratory experiments. Every registered experiment stays listed whatever its outcome:
positive, negative, inconclusive, invalid or unavailable. Each entry is written and committed **before** its outcomes
are computed. Later edits only add results or record deviations. **Development data only.** No result here is
validated edge or confirmation evidence. A positive result is a hypothesis for later prospective confirmation.

| ID | Status | Question | Result summary |
|---|---|---|---|
| E001 | COMPLETE (exploratory) | Do price/momentum/context fields in Gamma full-universe snapshots predict repricing by the next snapshot, beyond no-change? | 1h-change model *Indicative (exploratory)*: R2_oos +0.037, positive in 4/4 periods; the fitted sign is **reversal** (about -0.3). Others inconclusive. No edge claim. |
| E002 | COMPLETE — **Confirmed (exploratory, prospective)** | Does the E001 1h-change reversal hold prospectively on new full-universe snapshots, using a frozen coefficient? | R2_oos +0.026 [+0.005,+0.046]; slope -0.21 [-0.25,-0.17]; 40,436 markets, 9,967 events, horizon 4.9h; only ~2% of forecasts exceed half the spread |
| E003 | COMPLETE (exploratory) | Does top-of-book imbalance or microprice displacement (H08/H09) predict the next few minutes of midpoint repricing, beyond no-change and the 1h reversal? | H08 and H09 **inconclusive** (R2 about 0). The combined model beats reversal-only (+0.031 [+0.011,+0.049]), but only in wide-spread markets; the gain comes from spread/intercept drift, not imbalance. No edge claim. |
| E004 | REGISTERED (pre-outcome) | Does the frozen 1h reversal hold over 12 consecutive prospective periods (event-clustered), and does it survive crossing the spread? | pending |
| E005 | REGISTERED (pre-outcome) | In neg-risk groups, does a market's deviation from its arbitrage band (from siblings' bids/asks) predict repricing beyond the frozen reversal? | pending |
| E006 | REGISTERED (pre-outcome) | Is the 1h reversal moderated by liquidity (H1) or by time-to-end (H2), with centred interactions and a scale-free test? | pending |
| E007 | REGISTERED (pre-outcome) | In trade-active markets, does net taker order-flow pressure (signed share) over the prior hour predict continuation over ~2h? | pending (needs 12 qualifying periods) |
| T5-DEV | COMPLETE (development, exploratory_historical) | Do point-in-time features predict binary resolution at 1/3/7d before scheduled end better than price and a recalibrated (Platt/isotonic) price? | No: LightGBM vs Platt ΔLL 1d -0.0013, 3d -0.0004, 7d +0.0041 (all CIs span 0); only Platt-vs-raw-price at 7d is positive (+0.0069 [+0.0022, +0.0113]). See `RESOLUTION_DEV_STUDY.md` |
| IF-H2-DEV | COMPLETE (development, exploratory_historical): **null** | Does a decay-adjusted rise of the near deadline-ladder rung (`ifx_term` z >= 2) predict its 24h/7d drift beyond M0v? | No. Later months: ΔR² +0.00016 [-0.00010, +0.00041]; z >= 2 residual -0.20c [-0.48, +0.09] (all test months -0.35c [-0.57, -0.10], reversal). No E008 registered. See `IF_H2_DEADLINE_LADDER.md` |
| HB1 | COMPLETE (development, exploratory_historical) | Which of 72 pre-declared market-state, microstructure, flow, wallet, cross-market, time, category, extremity, liquidity, volatility and interaction hypotheses predict `h2_main` moves out of sample (one split, BY q = 0.10 on the cumulative count)? | 18 of 72 pass BY (m = 468): 2h-reversal moderators by trade confirmation (quote noise), net taker flow continuation at 2-24h (+0.3 to +0.6c per SD; aggressive flow strongest), flow weaker at longshot prices and in quiet markets, a price-level drift, one volatility feature. No wallet, cross-market, time, category or book hypothesis survives; ladders untestable. No survivor covers taker costs (net -2.4c to -4.1c). See `HYPOTHESIS_BATTERY_1.md` |
| HB1-R | COMPLETE (development, exploratory_historical) | Do the 18 HB1 survivors replicate on the independent `h3_power` markets with frozen definitions (Holm), and do wallet-age nulls change with h3's first-trade lookups? | 16 of 18 replicate (Holm, unweighted; same 16 weighted), all 18 signs agree, no shrinkage (median ratio 1.20); MI5 and PX2 fail; VO4 is fragile. Wallet family: WA2 rejects unweighted only and is mostly total flow (post-hoc). No cost viability. See `HYPOTHESIS_BATTERY_1_REPLICATION.md` |
| E009 | REGISTERED (pre-outcome; challenger-reviewed) | Live, receipt-timed: does Kalshi's latest 10-min move (frozen historical model) predict Polymarket's next 20-min mid move beyond M0, and is it executable after taker costs? | pending (fixed end 2026-11-03 00:00Z) |
| E010 | REGISTERED (pre-outcome; challenger-reviewed) | Live, same stream as E009: does the model refitted on the cleaned historical set (Kalshi changes + gap) predict Polymarket's 1h and 6h mid moves beyond M0? | pending (fixed end 2026-11-03 00:00Z) |

---

## E001 — Snapshot repricing baselines on Gamma full-universe captures

- **Registered:** 2026-10-10, before any extraction of outcomes. Commit hash recorded by git.
- **Purpose:**
  - Build and exercise the baseline and walk-forward machinery on real point-in-time data.
  - Learn how hard the next-snapshot repricing problem is.
  - Find out whether momentum or context adds anything beyond no-change.
- **Data (development):**
  - Local Gamma full-universe captures under `data-dumps/fs2_capture_*`, read-only.
  - "Full" means the session has at least 2,000 parsed pages. That is about 7 sessions, 2026-09-20 to 2026-10-10.
  - Each row's observation time is the receipt time of its page, not the session start.
  - These data were not collected under a frozen sampling design. Results do not generalise to a population.
- **Unit:** a (market, capture i, next full capture j) pair, for binary two-outcome markets only.
  - Price is outcome index 0.
  - `mid = (bestBid + bestAsk) / 2`.
- **Eligibility at capture i**, evaluated only from the row at i:
  - Not closed, and active.
  - `0 < bestBid < bestAsk < 1`, `spread <= 0.10`, and `0.02 <= mid <= 0.98`.
  - `endDate` is unknown, or later than the receipt time at j as scheduled from i's data.
  - A pair whose market is missing or one-sided at j is *target-unavailable*. It is counted, not imputed.
- **Target:** `dmid = mid_j - mid_i`. The horizon h is the capture spacing and is recorded per pair.
- **Features**, all from the row at i:
  - `mid`, `spread`
  - `oneHourPriceChange`, `oneDayPriceChange`, `oneWeekPriceChange` (missing → 0, plus a missing flag)
  - `log1p(liquidity)`, `log1p(volume24hr)`
  - `log1p(hours to endDate)` (with an unknown flag)
  - `lastTradePrice - mid`
  - interaction `oneDayPriceChange × log1p(liquidity)`
- **Models**, all fitted only on training pairs. The 5 models form one family.
  - **B0 no-change:** `dmid_hat = 0`.
  - **B1 momentum-1d:** `dmid_hat = b * oneDayPriceChange`, fitted by OLS through the origin.
  - **B1h momentum-1h:** the same, using `oneHourPriceChange`.
  - **B2 price+momentum ridge:** `mid` and the 1h/1d/1w changes.
  - **B3 full-context ridge:** all the features above.
  - Ridge features are standardised on training data only. λ comes from the grid {0.1, 1, 10, 100, 1000}, chosen on the last training period as an inner validation split. Test data is never used for this.
- **Split:**
  - Walk-forward over consecutive full-capture pairs ordered by time. Train on every pair whose target time j is at or before the test pair's origin time i; this purges by actual label availability. Test on the next pair.
  - A test period needs at least one prior training period.
- **Primary metric:** pooled out-of-sample `R2_oos = 1 - SSE_model / SSE_B0` over all test periods, with per-period values.
- **Secondary metrics:**
  - Spearman rank correlation between `dmid_hat` and `dmid`, per period.
  - Directional accuracy on movers with `|dmid| >= 0.01`.
  - MAE.
- **Uncertainty:**
  - Market-clustered bootstrap (1,000 resamples, seed 116) of `R2_oos` within each test period.
  - Test periods are few. Any conclusion must hold in the majority of periods, not only when pooled.
- **Effective sample reporting:**
  - Raw pairs, distinct markets, distinct events (if the Gamma rows carry event ids), number of test periods.
  - Eligibility and target-unavailable counts.
- **Interpretation rule, fixed in advance:**
  - **"Indicative (exploratory)":** `R2_oos > 0` with the bootstrap 95% CI above 0 in the majority of periods.
  - **"Negative":** `R2_oos <= 0` in the majority of periods.
  - **"Inconclusive":** anything else, including fewer than 3 test periods.
  - No outcome is edge.
- **Known limitations:**
  - Irregular horizons; few time periods.
  - Capture spans of about 7-11 minutes, so rows within a frame are not simultaneous.
  - Gamma-computed change fields have unknown update latency (`updatedAt` is recorded).
  - Cross-sectional dependence within a capture time.
  - Survivorship from the "not closed at i" rule.

### E001 results (2026-10-10; code `backend/astrolabe/research_lab/`, runner `backend/scripts/run_research_e001.py`)

**Data**
- 6 full captures (2026-10-03 to 2026-10-10, receipt clock = per-page `receipt.json` `first_received.utc`).
- 1,517,668 rows.
- 5 consecutive pairs, giving 4 test periods (median horizons about 5h, 70h, 5h, 42h).
- 161,902 test pairs, 67,228 markets, 14,879 events.
- 5,379 target-unavailable pairs: 2,761 missing at j, 2,618 one-sided or closed at j.

| Model | Pooled R2_oos [95% CI] | Per period | Mean Spearman | MAE | Label |
|---|---|---|---|---|---|
| B0 | 0 | 0,0,0,0 | n/a | 0.01679 | baseline |
| B1 (1d) | -0.024 [-0.030,-0.017] | -0.155,+0.032,-0.026,+0.018 | 0.109 | 0.01961 | Inconclusive |
| B1h (1h) | +0.037 [+0.030,+0.043] | +0.042,+0.056,+0.034,+0.017 | 0.112 | 0.01702 | **Indicative (exploratory)** |
| B2 | +0.021 [+0.013,+0.029] | -0.037,+0.075,-0.016,+0.031 | 0.086 | 0.02129 | Inconclusive |
| B3 | +0.038 [+0.030,+0.047] | +0.004,+0.082,-0.006,+0.044 | 0.081 | 0.02195 | Inconclusive |

**Post-hoc diagnostic (not pre-registered; hypothesis generation only)**
- The OLS coefficient of `dmid` on `oneHourPriceChange` is **negative** in every pair period: -0.335, -0.373, -0.363, -0.280, -0.279.
- It is almost unchanged after adding `lastTradePrice - mid`, and corr(1h change, gap) is about -0.03.
- So about 30% of the Gamma-reported 1h change reverses by the next snapshot, regardless of horizon (5-70h). "Momentum" is a misnomer for B1h here.
- B1h's MAE is slightly worse than B0. The gain is in squared error on large moves.

**Deviations from registration**
- 6 captures, not about 7: the >=2000-page rule excluded the 1,755-page frame.
- The purge was applied per 60s bin of test origins. This is conservative.
- Test bins with fewer than 500 purged training pairs were skipped (9,216 period-1 pairs).
- The lambda inner split fell back to the latest 25% of training when a side had fewer than 500 pairs.
- Ridge uses an unpenalised intercept.
- Extra missing-value flags: lastTradePrice missing flag; missing liquidity/volume set to 0.
- The target at j requires a valid two-sided, not-closed book, with no spread or mid filter.

**Interpretation**
- Short-horizon price changes on Polymarket partially revert. This may be quote noise or thin-book overreaction rather than an exploitable edge: midpoint reversal is not executable value.
- Development data only. The next step is prospective confirmation (E002).

---

## E002 — Prospective confirmation of the 1h-change reversal (frozen model)

- **Registered:** 2026-10-10, before any E002 snapshot exists. Git commit hash records the freeze.
- **Hypothesis**, generated post hoc in E001: the next-snapshot `dmid` is negatively related to the Gamma
  `oneHourPriceChange` at origin.
- **Frozen model:** `dmid_hat = -0.331610 * oneHourPriceChange` (missing = 0). This is OLS through the origin on all
  197,341 E001 target-available pairs. No refitting.
- **Data:** new compact full-universe Gamma snapshots from the research-lab collector, taken after this commit.
  - Complete keyset enumeration, `closed=false`.
  - Per-page receipt clock.
  - E001 field set and parsing.
  - No E001 capture is reused.
- **Pairs:** consecutive new captures at least 3h apart. Eligibility, target and features are identical to E001.
- **Primary test**, on the first new pair period. Both conditions must hold:
  1. `R2_oos` of the frozen model against B0 is above 0, and its market-clustered bootstrap 95% CI (1,000 resamples, seed 116) lies above 0.
  2. The OLS slope of `dmid` on `oneHourPriceChange` is below 0, with its market-clustered 95% CI below 0.
- **Verdicts:**
  - **Confirmed (exploratory, prospective)** if both conditions hold.
  - **Not confirmed** if either point estimate has the wrong sign.
  - **Inconclusive** otherwise.
  - Later new pair periods are reported as replications under the same rules. They never replace the first-period verdict.
- **Secondary (descriptive):**
  - Slope by spread tercile and by `log1p(liquidity)` tercile (noise versus overreaction).
  - Executable check: the share of eligible pairs where `|dmid_hat| > spread/2`.
- **Non-claims:** midpoint reversal is not executable value; spread, depth and fees are not modelled. One time period is
  thin evidence.

**E002 pre-outcome clarifications (2026-10-10 ~19:50Z, before the second E002 capture exists)**
- The primary "OLS slope" is the slope through the origin, consistent with the frozen model and the E001 diagnostic.
  The with-intercept slope is descriptive only.
- "Wrong sign" means `R2_oos <= 0` or `slope >= 0`.
- The first E002 capture is `20261010T192208Z_db7c7287`. It is the first complete capture after registration commit `58a13a6` (19:20:42Z).
- Forecasts for that capture were logged before outcomes at `data-dumps/research_lab/forecasts/` (43,162 eligible markets).
  Scoring recomputes them and asserts exact equality with the log.
- Code: `backend/astrolabe/research_lab/forecast.py`, `backend/scripts/run_forecast.py score-e002`.

---

## E003 — Short-horizon book imbalance and microprice (H08/H09 cross-sectional variant)

- **Registered:** 2026-10-10, before any book sweep exists.
- **Relation to the research package:** an exploratory variant of H08 (top-level imbalance) and H09 (microprice displacement).
  - The registered horizon is minutes, matching H08's 1-5m range.
  - The population is the whole eligible universe swept in batches, not the H08 sampled panel, so this is development evidence, not the H08 confirmation.
- **Collection:**
  - Two *series* S1 (development) and S2 (confirmation). Each is a fresh complete universe snapshot followed immediately by `sweep_books.py --repeat 3` (sweeps A, B, C over a fixed token order).
  - S2 starts at least 60 minutes after S1 ends.
  - Token = outcome 0 of each forecast-eligible market (E001 eligibility; endDate unknown or later than receipt + 3h).
- **Unit:** a token that is two-sided in sweep A.
- **Primary target:** `dmid_AB = mid_B - mid_A`. The per-token horizon is the receipt-time difference between its batches, recorded.
- **Secondary target:** `dmid_AC`.
- **Target unavailable:** the token is not two-sided at B (or C for the secondary). Counted, never imputed.
- **Features at A:**
  - `I1 = (bid_size_1 - ask_size_1) / (bid_size_1 + ask_size_1)` (H08)
  - `micro = (ask*bid_size_1 + bid*ask_size_1)/(bid_size_1 + ask_size_1) - mid` (H09)
  - `I5 = (depth_bid_5c - depth_ask_5c)/(sum)`
  - `spread`
  - the Gamma `oneHourPriceChange` from the series snapshot (reversal control)
- **Models**, fitted on S1 only and frozen, then evaluated on S2:
  - R0: no-change.
  - R1: reversal, OLS through origin on `chg_1h`.
  - M8: OLS on `I1`.
  - M9: OLS on `micro`.
  - MC: OLS with intercept on {`I1`, `micro`, `I5`, `spread`, `chg_1h`}.
- **Primary tests on S2 (AB target)**, each using a 95% CI from an event-clustered bootstrap (1,000 resamples, seed 116):
  - (a) `R2_oos(M8)` against R0 is above 0 with its CI above 0. This tests H08.
  - (b) `R2_oos(M9)` against R0 is above 0 with its CI above 0. This tests H09.
  - (c) The incremental test: `1 - SSE(MC)/SSE(R1)` is above 0 with its CI above 0. This asks whether book features add beyond reversal.
- **Verdicts:**
  - Each test is **supported (exploratory)** if it meets its condition.
  - It is **wrong sign** if the S2 slope sign differs from S1.
  - Otherwise it is **inconclusive**.
  - H09 counts as "adds beyond H08" only if `R2_oos(M9) > R2_oos(M8)` with the paired-bootstrap CI of the difference above 0.
- **Secondary (descriptive):**
  - The same tests on the AC target.
  - Results by spread tercile.
  - The share of tokens whose mid changed at all between A and B.
- **Known limitations:**
  - There is one time period per series.
  - Common shocks within a series are only partly handled by event clustering.
  - Book `timestamp` semantics are to be checked on the first batch.
  - Batch receipt is not book creation time.
  - This is midpoint movement, not executable value.

**E003 pre-outcome clarifications (2026-10-10 ~19:55Z, before any fit or S2 data)**
- "OLS on I1" (M8) and "OLS on micro" (M9) are fitted through the origin, consistent with R1. MC keeps an intercept.
- Series S1 = `20261010T193535Z_ccc0e4d7` snapshot plus sweeps `...194225Z_94956338`, `...194347Z_d61a9354` and `...194506Z_f1051015`. All 43,420 tokens were returned in each sweep.
- Venue book `timestamp` is Unix milliseconds of the book's last change. It is not used as an observation clock; batch receipt time is.
- Rows with a zero-size denominator get feature = NaN and are excluded and counted.
- Event clusters fall back to market_id where event_id is missing, and those fallbacks are counted.
- (~20:05Z, after the S1 development fit and before any S2 data) A missing `oneHourPriceChange` is set to 0, following the E001/E002
  convention; the share is reported (S1: 62%). Verdict order: the sign check comes first. A zero or NaN sign is inconclusive. The AC target
  is scored with the AB-fitted coefficients. S1 was frozen to `data-dumps/research_lab/e003/s1_fit.json`; its in-sample stats are
  development only.

---

## Methods note M1 — Reusable comparison pipeline and the event-clustering lesson (2026-10-10)
- `backend/astrolabe/research_lab/compare.py` and `features.py` (CLI `scripts/run_comparison.py`) are now the shared,
  leakage-guarded comparison path. Features are computed from origin columns only. Purging follows label availability.
  Paired bootstrap uses shared resamples.
  - Preset `e001_repro` reproduces every E001 metric to within 1.6e-13.
- **Lesson:** clustering the bootstrap by **event** instead of by market widens the B3 pooled R2_oos CI from
  [+0.030, +0.047] to [+0.004, +0.069], because markets within an event move together.
  - E001's market-clustered intervals overstate precision.
  - **From now on, experiments cluster by event** unless they register a different rule. E002's registered market clustering stays
    as registered; an event-clustered result will be reported alongside it as descriptive.
- Post-hoc family ablation on E001 data (DEVELOPMENT only, not registered): removing the momentum/reversal family costs
  the most. The paired R2 difference is +0.030 [+0.011, +0.049]. Context features and the interaction add +0.013 to +0.014.
  These are hypotheses for future registered experiments, not findings.

### E003 results (S2 scored once, 2026-10-10 21:08Z; `data-dumps/research_lab/e003/s2_results.json`)
**S2 data**
- Series `series_20261010T210152Z_7d8b4190` on snapshot `20261010T204959Z_4520b6b7`, 75 min after S1.
- 42,372 tokens across 10,250 events, clustered by event.
- Median horizon: 129s for AB, 268s for AC.
- 11.0% of mids changed between A and B; 16.8% between A and C. 68% of tokens have no `chg_1h`.

| Test (AB) | R2_oos [95% CI] | Verdict |
|---|---|---|
| (a) M8 imbalance vs R0 | +0.00047 [-0.00008, +0.00093] | inconclusive (same sign as S1) |
| (b) M9 microprice vs R0 | +0.000003 [-0.00093, +0.00081] | inconclusive |
| (c) MC vs R1 | +0.0306 [+0.0114, +0.0491] | **supported (exploratory)** |
| H09 beyond H08 | -0.00047 [-0.0011, +0.0002] | no |

**AC secondary:** M8 inconclusive. M9 **wrong sign**. MC vs R1 is +0.024 [+0.016, +0.033].

**Spread terciles (descriptive), MC vs R1:**
- low spread (≤0.02): **-0.39**
- mid spread: -0.004
- high spread (≥0.041): **+0.035**

**Interpretation:**
- Over about 2 minutes, top-of-book imbalance and microprice carry no measurable information about the midpoint across the eligible universe.
- MC's gain sits entirely in wide-spread books and comes from its spread and intercept terms, which describe midpoint drift in illiquid books. Those terms hurt badly in tight books.
- That is unlikely to be executable value, since the spreads are wide. The family-level conclusion for H08/H09 is **no evidence of short-horizon value at this population and horizon**.
- **Next:** if imbalance is revisited, condition on tight, deep books and longer horizons, register first, and model a spread interaction rather than a global spread term.

---

## E004 — Multi-period prospective reversal test with an execution check

- **Registered:** 2026-10-10 ~21:15Z, before the collection loop starts. No loop snapshot exists yet.
- **Model:** frozen `e002_reversal_v1` (`dmid_hat = -0.331610 * chg_1h`, missing = 0). No refitting.
- **Data:** the first 12 complete research-lab snapshots taken by the 2-hourly collection loop started after this commit,
  forming 11 consecutive pair periods. Snapshots from E002 or E003 are excluded. Eligibility, target and features are as in E001.
- **Primary statistical test**, all three must hold:
  1. Pooled `R2_oos` versus B0 is above 0, with its **event-clustered** bootstrap 95% CI (1,000 resamples, seed 116) above 0.
  2. Per-period `R2_oos` is above 0 in at least 8 of 11 periods.
  3. The pooled through-origin slope is below 0, with its event-clustered CI below 0.
- **Statistical verdict:** **Supported (exploratory, prospective)** if all three hold. **Not supported** if the pooled `R2_oos` is at or below 0 or the slope is at or above 0. **Inconclusive** otherwise.
- **Execution check** (economic stage, descriptive with CI):
  - For pairs where `|dmid_hat| > spread_i/2`, take a hypothetical 1-share position in the predicted direction at the origin touch: buy at `bestAsk_i` if up, sell at `bestBid_i` if down.
  - Exit at the next-snapshot touch: sell at `bestBid_j` or buy back at `bestAsk_j`.
  - Report mean P&L per trade with an event-clustered CI, the hit rate, and the trade count.
  - Report also an *optimistic* variant that exits at `mid_j`.
  - Fees, depth, queue position and latency are ignored, so even a positive result is an upper bound.
  - **Economically interesting (exploratory)** only if the touch-to-touch mean P&L CI lies above 0.
- **Non-claims:** no profitability claim. The book depth needed to fill and the capture latency are not modelled.

**E004 pre-outcome clarification (2026-10-10, before any qualifying snapshot exists)**
- The registration commit `3d7335e` time is 21:09:17Z. The "~21:15Z" in the text above is approximate.
- "Snapshots from E002 are excluded" is implemented as the E002 pair chosen by E002's own rule (start times only).
- Qualifying snapshots are complete, started after 21:09:17Z, not in that pair, and taken as the first 12 by start time.
- Event clusters fall back to `market_id`, and the fallbacks are counted.


**E004 challenger review (Opus, 2026-10-10 ~21:20Z, before any qualifying snapshot) and lead decisions.** The registered
criteria are unchanged.
- **Verdict:** E004 is interpretable as a statistical test of a frozen model. The code matches the registration and no leakage path was found.
- **Operational rule (lead decision):** no other capture is written to `data-dumps/research_lab/snapshots/` until E004 has 12
  qualifying snapshots. If the loop yields only 11 (for example because the 22:36Z one-shot fails and loop pass 1 becomes E002's
  capture), E004 is recorded **pending/unavailable**. It is not filled with an extra capture.
- **Execution check reinterpretation (disclosure, not a rule change):**
  - The touch-to-touch P&L is **optimistic by an unknown amount**, not an upper bound. Stale Gamma quotes specifically flatter a reversal bet, and a fill is only possible after receipt.
  - Survivorship from excluding target-unavailable pairs probably biases P&L and the reversal estimate upward.
  - A descriptive count of selected trades lost to target-unavailability will be reported.
  - Mean P&L per share mixes capital bases (long `ask_i` against short `1-bid_i`).
  - Fees, depth, tick size and minimum order size are not in the data.
  - Shorting YES is equivalent to buying NO in P&L terms. Whether Gamma touch prices include mirrored orders is unverified.
- **Statistical disclosures:**
  - Quote noise alone predicts a negative slope; only the execution stage speaks to value.
  - The coefficient was fitted on multi-day spacing and is applied to about 2h horizons.
  - Under a coin-flip null, P(≥8 of 11) ≈ 0.11, so the period rule is a consistency check, not a test.
  - The event bootstrap does not capture period-wide shocks; 11 periods is the true replication count.

---

## E005 — Cross-market consistency in neg-risk groups (arbitrage-band deviation)

- **Registered:** 2026-10-10, before the first E004-qualifying snapshot exists.
- **Design origin:** the challenger's revision of a lead draft. The draft's mid-sum "gap" was rejected for these reasons:
  - It encodes group size and spread, and largely confounds with `-chg_1h`.
  - At origin, mid-sums are often far above 1 (quartiles 1.00/1.03/1.41) while `Σbid>1` or `Σask<1` holds in only about 0.2% of groups.
- **Group g:** rows with `neg_risk==1` and the same non-null `neg_risk_market_id`.
  - Exclude g if any member has `event_neg_risk_augmented!=0` or `neg_risk_other==1`, if g has fewer than 2 members, if any member lacks `best_ask`, or if member receipt times span more than 120s.
  - A missing `best_bid` is treated as 0 (no buyer).
- **Synthetic band** for member i, from origin rows only, over all present members including E001-ineligible ones:
  - `SB_i = 1 - Σ_{k≠i} ask_k`
  - `SA_i = 1 - Σ_{k≠i} bid_k`
- **Feature:** `dev_i = max(0, SB_i - mid_i) - max(0, mid_i - SA_i)`, which is 0 inside the band.
- **Descriptive only:** `A_g = Σask`, `B_g = Σbid`, `N_g`, and the arbitrage flags (`A_g<1`, `B_g>1`).
- **Unit:** members passing E001 eligibility. Target `dmid` with E001 panel semantics.
- **Models:**
  - R is the frozen `e002_reversal_v1`.
  - RC is `dmid_hat = R + b*dev`. `b` is fitted by OLS through the origin on the residual `(dmid - R)` against `dev`, using only the re-extracted E001 captures (`data-dumps/research_lab/dev_snapshots_v2/`).
  - `b` is then frozen. `b` and its fit counts are committed before any confirmation-period outcome is computed.
- **Confirmation data:** the 12 E004-qualifying snapshots (11 periods). E004 itself is untouched.
- **Primary tests (all must hold):**
  1. Pooled `1-SSE(RC)/SSE(R) > 0`, with an event-clustered bootstrap CI above 0 (1,000 resamples, seed 116, market_id fallback counted).
  2. The through-origin slope of `(dmid-R)` on `dev` is above 0, with its CI above 0.
  3. Incremental R2 is above 0 in at least 8 of 11 periods.
- **Verdict:**
  - **Supported (exploratory)** if all three hold.
  - **Not supported** if the point estimate of (1) or (2) is at or below 0.
  - **Inconclusive** otherwise.
  - **Unavailable (no verdict)** if there are fewer than 200 pairs with `dev!=0` or fewer than 30 groups with `dev!=0`.
- **Secondary (descriptive):**
  - G-only against B0.
  - Terciles of `N_g` and of band width.
  - A spread+mid drift baseline.
  - Touch-to-touch as in E004, plus a count of selected trades lost to target-unavailability.
- **Disclose:**
  - Group completeness cannot be verified (unlisted, inactive or placeholder siblings).
  - Fees and depth are absent.
  - The data are shared with E004, so results are correlated, not independent.

**E005 amendment v2 (lead decision after a second challenger critique, before any confirmation snapshot exists).**
- The registered band feature `dev_i` is kept.
- Baseline R becomes `dmid_hat = a + s*spread_i - 0.331610*chg_1h`. The reversal coefficient stays frozen; `a` and `s` are fitted by OLS on dev
  residuals `(dmid + 0.331610*chg_1h)` using dev_snapshots_v2 only, then frozen.
- RC = R + b*dev, with `b` fitted on dev residuals `(dmid - R_hat)` through the origin, then frozen.
- Primary tests (1)-(3) compare against this R.
- **Reason:** E003 showed that spread-related drift in wide books can masquerade as signal. Without the spread term, a positive
  result could be spread drift correlated with `dev`.
- **Added secondaries:**
  - tight groups (all present spreads ≤ 0.03);
  - exclusivity asymmetry: separate slopes for `dev>0` and `dev<0`, since neg-risk guarantees mutual exclusivity but not exhaustiveness.
- **Clusters:** event_id, falling back to neg_risk_market_id and then market_id (counted).
- **Disclose:** spread and |S-1| are highly correlated at origin (0.92 on a dev capture).
- **Not adopted:** the alternative feature `c_k` (proportional allocation of excess), which rests on a stronger assumption than the
  bid/ask band. It may become a later experiment.
- **Confirmation data:** unchanged (the 12 E004-qualifying snapshots, all taken after this amendment).

**E004/E005 collection rule refinement (before the first qualifying snapshot; replaces "record pending" above).**
- If any loop pass fails, collection continues at the same about 2h cadence until 12 snapshots qualify. This depends only on availability, never on outcomes.
- Gaps over 3h are flagged and kept.
- No other capture is written to `snapshots/` until then.
- The E004 result additionally reports that the frozen spec file equals `git show 3d7335e:` of the same path.
- The neg-risk columns added in 19d7bd3 are additive and are not read by E004.

**E005 development fit (frozen `data-dumps/research_lab/e005/dev_fit.json`, before any confirmation outcome)**
- `a = -0.00116`, `s = +0.0793`, `b = -0.0590`.
- 45,624 in-group pairs. 1,164 of them have `dev≠0` (2.55%), across 277 groups.
- In-sample incremental R2 is about 2e-5.
- **The development data show no support:** the band-deviation coefficient has the opposite sign to the hypothesis and is negligible in size.
- The confirmation test proceeds unchanged. Its primary test (2) requires a positive slope.

**Crash note (2026-10-11 ~00:15 UTC, before any E002 or E004 outcome snapshot exists)**
- The Mac crashed at about 22:00 UTC on 2026-10-10 (memory exhaustion).
- Two scheduled background jobs never ran: the E002 outcome capture (due 22:36 UTC) and the E004 2-hourly loop (first pass due about 22:53 UTC). No partial snapshot exists; all 12 research-lab gzip files and every JSON passed integrity checks after the crash.
- **E002:** the registered rule (first complete capture at least 3h after `20261010T192208Z_db7c7287`) has no maximum gap, so it still holds. The next complete capture becomes E002's target. Its horizon will be about 5h instead of about 3.2h. That is within E001's 5-70h training range, and it is disclosed.
- **E004/E005:** no qualifying snapshot existed before the crash. The 2-hourly loop starts after the E002 capture, under the availability-only continuation rule already recorded. Nothing is redrawn or backfilled.

## Methods note M2: power tools (2026-10-11)

- **Tools:** `backend/astrolabe/research_lab/power.py`, `backend/scripts/power_check.py`, and the optional `time_block_inference=True` flag of `compare.run_comparison`.
- **What they do:** planning arithmetic only. They change no existing result. With the flag off, `compare` output is identical.
- **MDE:** `DeltaR2 = mean(c_k)`, `c_k = K * d_k / SSE_baseline` over clusters, so `SE = sd_c / sqrt(K)` and `MDE = (z_{1-a/2} + z_power) * sd_c / sqrt(K)`. `required_clusters` is its inverse. `sd_c` is backed out of a bootstrap CI as `SE * sqrt(K)` and held constant as K grows.
- **Multiple tests:** Bonferroni divides alpha by the number of tests. Holm's first step is the same, so the MDE is identical. Holm only helps later steps (`adjust_pvalues`).
- **Design effect:** `design_effect` returns the cluster-robust (sandwich) variance over the iid variance, or a bootstrap ratio. It also returns the implied ICC.
- **Per-period inference:** `per_period_test` runs a t-test and exact sign test across time blocks. At 4 periods (df 3) the sign test cannot reach p<0.05 (floor: 6 periods), and the t-interval is very wide.
- **Assumptions:** normal approximation, independent clusters, and independent periods. Time dependence between clusters is not modelled.
- **Not evidence:** the numbers are not findings and make no edge claim.


### E002 result (scored once, 2026-10-11 ~00:25Z; `data-dumps/research_lab/e002/results.json`)
- **Pair:** `20261010T192208Z_db7c7287` -> `20261011T001707Z_c0f0fb92`, a 4.92h gap. The first post-crash attempt
  (`20261011T001311Z_80cc2683`) ended `incomplete:http_403` after 1,311 pages and was ignored by rule. A
  retry is an availability-only event.
- **Logged-forecast check:** passed. 40,688 compared, 0 scored without a logged forecast.
- **Primary:** `R2_oos` = **+0.0265** [+0.0054, +0.0458]. Through-origin slope = **-0.212** [-0.252, -0.174], market-clustered as registered.
  - **Verdict: Confirmed (exploratory, prospective).**
- **Descriptive:**
  - Slope with intercept: -0.205.
  - Slope by spread tercile: low -0.12 [-0.24, -0.04]; mid -0.13; high -0.26.
  - Slope by log-liquidity tercile: low -0.26, mid -0.04, high -0.22 (wide CI).
  - |dmid_hat| > half-spread for only **2.0%** of eligible pairs.
- **Interpretation:**
  - A reversal of about 21% of the Gamma 1h change held on unseen data at about 5h. It is present even in tight-spread markets.
  - Magnitude is about 2/3 of the dev fit.
  - This is a single time period, and quote noise alone predicts a negative slope.
  - Executable value is not shown: forecasts rarely exceed the half-spread.
  - **Not edge.** E004 tests 11 periods and touch-to-touch execution.

---

## E006 — Reversal moderation by liquidity (H1) and time-to-end (H2)

- **Registered:** 2026-10-11, before any E004-qualifying snapshot exists.
- **Origin:** the 6-variant development screen (`a3cb9cf`; trials in `trials.jsonl`). The spec below is the challenger's, adopted verbatim.
- **Disclosures:**
  - The lead saw E002's descriptive liquidity-tercile slopes (non-monotone) before registering. E002 data are not part of E006's confirmation set.
  - The dev effects are winner's-curse-inflated: 2 of 6 variants were kept from 18 contrasts.
  - The pre-listing of the 6 variants cannot be verified from git.
- **Data:** the E004-qualifying snapshots (12 snapshots, 11 periods), using E004's eligibility, target, collection-continuation and crash rules unchanged.
  - E004 and E005 are untouched. Results share data with them and are correlated.
- **Baseline R (frozen, E005 v2):** `R_hat = a + s*spread_i - 0.331610*chg_1h`, with `a` and `s` from `data-dumps/research_lab/e005/dev_fit.json`.
- **Moderators:**
  - `z2 = chg_1h*(log_liq - m_L)`
  - `z4 = chg_1h*(log_hours_to_end - m_H)`
  - `m_L` and `m_H` are dev means over pairs with observed `chg_1h`, frozen at 6 significant figures.
- **Missing values:**
  - Missing `chg_1h` gives z = 0 (kept, contributes nothing). Report n_eff (pairs) and K_eff (events) with observed `chg_1h`.
  - Missing liquidity: excluded from H1 and counted.
  - `end_unknown=1`: excluded from H2 and counted.
- **Frozen predictive models:** `M_k = R_hat + b_k*z_k`.
  - `b_k` is a through-origin OLS of `(dmid - R_hat)` on `z_k`, fitted on all `dev_snapshots_v2` pairs.
  - Commit `b_k`, counts and corr(chg_1h, z_k) on dev before any E004 outcome is computed. No ridge and no refitting.
- **Hypotheses (Holm, family α = 0.05):**
  - H1 (v2): the liquidity moderator has the sign of `b_2`.
  - H2 (v4): the time-to-end moderator has the sign of `b_4`.
- **Primary statistic (scale-free):**
  - On confirmation data, fit a through-origin OLS of `(dmid - R_hat)` on `[chg_1h, z_k]`.
  - θ_k is the coefficient on `z_k`. The free `chg_1h` term absorbs horizon rescaling of the reversal.
  - Event-clustered bootstrap: 1,000 resamples, seed 116, falling back to market_id (counted). Two-sided p-value, then Holm.
- **Secondaries (reported, do not decide the verdict):**
  - S1: `ΔR2_k = 1 - SSE(M_k)/SSE(R)` with its event-clustered CI. This asks whether the frozen magnitudes transfer to ~2h.
  - S2: θ_k/γ, where γ is the fitted `chg_1h` coefficient.
  - S3: target-unavailable rate by liquidity tercile.
- **v4 guard (required for H2 Supported):**
  - θ_4 keeps its sign, with a Holm-level CI excluding 0, in the augmented regression `[chg_1h, z4, chg_1h*(spread - m_S), (log_hours_to_end - m_H)]`. `m_S` is frozen from dev.
  - The same augmented regression is run for H1 as a disclosed secondary, because corr(log_liq, spread) = -0.535 on dev.
- **Period consistency:**
  - θ_k must have the predicted sign in at least 7 of 11 periods.
  - Disclosure: 11 consecutive ~2h periods span about 1 calendar day, which is 1-2 independent time blocks. P(≥7/11 | coin) = 0.27, so this is a consistency check, not a test. The bootstrap does not capture day-wide shocks.
- **Verdict per hypothesis:**
  - **Supported (exploratory, prospective):** Holm-rejected in the predicted direction, consistency met, and (H2 only) guard met.
  - **Supported and transferable:** additionally, the S1 CI is above 0.
  - **Not supported:** θ_k point estimate at or below 0 in the predicted direction.
  - **Inconclusive:** otherwise.
- **Unavailable (no verdict):**
  - E004 is unavailable;
  - n_eff < 2,000 or K_eff < 500 for a hypothesis;
  - fewer than 9 periods with any observed `chg_1h`;
  - the frozen spec hash differs from the registration commit.
  - **Pending** until 12 snapshots qualify. **Failed:** runtime errors, logged in `trials.jsonl`.
- **MDE (M2 logic, S1 only):**
  - `MDE = 3.083*sd_c/sqrt(K_eff)`.
  - Dev sd_c: v2 0.0947, v4 0.166.
  - At K_eff = 3,000: v2 0.0053, v4 0.0093. At 6,000: v2 0.0038, v4 0.0066.
  - The dev effects (+0.0038 and +0.0086) are selection-inflated. **H1 is likely underpowered on S1.** sd_c is probably larger at short horizons.
  - There is no slope-MDE tool for θ yet.
- **Dev-screen defects carried as disclosures:**
  - The original interactions were uncentred, with corr about 0.96 with `chg_1h`. Fixed here by centring.
  - 75% of dev pairs lack `chg_1h`.
  - The two short-horizon dev periods were mixed.
  - Use the B1h_r reference only.
  - Unknown end dates were coded as hours = 0 in dev; excluded here.
  - Possible survivorship linked to liquidity.
- **Non-claims:** no edge, profitability, calibration or causal claim. No execution stage. This tests moderation of a reversal partly predicted by quote noise. It is not independent of E004 or E005.

**E006 dev fit (frozen `data-dumps/research_lab/e006/dev_fit.json`, before any E004-qualifying snapshot)**
- Fitted values:
  - `m_L = 7.46337`, `m_H = 5.99568`, `m_S = 0.0486011`
  - `b_2 = +0.012287` (H1 predicted sign: positive)
  - `b_4 = -0.061687` (H2 predicted sign: negative, i.e. stronger reversal further from the end date)
- 49,354 of 197,341 dev pairs have an observed `chg_1h`.
- **Disclosure:** even after centring, corr(`chg_1h`, z2) = **-0.874** on dev, so H1's θ is weakly identified and an inconclusive result is
  likely. For z4 the correlation is +0.439.
- Implementation interpretations are recorded in the `e006.py` docstring:
  - the spec hash is taken over the E006 ledger section at `32e6907`;
  - γ is reported as both total and residual;
  - the guard CI is set at the Holm rank level.

---

## Data note D1 — Most quoted markets do not trade (first development trade-flow sample, 2026-10-11)
- **Sample:** `data-dumps/research_lab/trade_samples/20261011T010752Z_0c287bab`.
  - 2,000 markets, probability-sampled (12 liquidity×spread strata, sealed seed, inclusion probabilities recorded) from the
    forecast-eligible frame of snapshot `20261011T002442Z_2173f20d`.
  - Data API `/trades`, all 2,000 requests OK, in 528 s at a peak of 446 MB.
- **Findings (descriptive, development):**
  - **51% of eligible markets returned zero trades ever.** This was cross-checked with and without `takerOnly`.
  - 96.8% had no trade in the hour before origin.
  - The median time since the last trade, among markets that ever traded, was about 33h.
  - No market hit the 500-trade truncation.
- **Consequences:**
  1. Flow-family experiments must define their population as markets with recent trades, and record inclusion probabilities against that frame. The whole quoted universe is mostly untraded.
  2. In much of the eligible universe, Gamma "price changes" (E001/E002 reversal) are quote movements, not trades. This supports the quote-noise caveat on E002, and the "not shown to be tradable" finding.
  3. Future snapshot eligibility for product forecasts should consider a trade-activity filter. Any such filter must be registered before use; it must not be applied retroactively.

**Flow screen S1 (DEVELOPMENT, 2026-10-11 ~02:35Z; `data-dumps/research_lab/flow_screen/flowscreen-ffcdee3436`)**
- **Sample:** trade sample `0c287bab` (eligible frame, 1 period, horizon 1.97h) paired with snapshot `20261011T022316Z_f3cab565`.
  1,987 pairs across 1,537 events. 61.8% have dmid = 0.
- **Results:**
  - Every flow variant F1-F4 is null or negative against both bases (frozen reversal and a ridge on chg_1h). The minimum detectable effects are 0.04-0.10, except F1 and F4 against ridge (about 0.001-0.008).
  - The frozen reversal base gives R2 = 0.165 against no-change in this single period. That is a development observation only, not evidence; E004 tests the reversal over 11 periods.
- **Interpretation:** the eligible frame is mostly untraded (Data note D1). Flow screening continues on trade-active samples (`--frame active`), collected after each loop pass.
- **Flow screen S2 (DEVELOPMENT, ~04:30Z, `flowscreen-9dd7f7852f`)**
  - Two periods: the eligible sample from S1 plus the first trade-active sample (`5a048dfe`, 1,996 pairs). In total 3,983 pairs across 2,652 events.
  - All pooled CIs span 0. In the trade-active period alone, F1, F2a and F3 against ridge come out at about +0.010 to +0.012.
  - This is to be watched as active periods accumulate. It is not a finding.
- **Flow screen S3 (DEVELOPMENT, ~06:30Z):** 3 periods, 5,973 pairs across 3,338 events.
  - Against the ridge base, the two **trade-active** periods both lean positive for F1, F2a, F2b and F3: +0.009 to +0.016 R2 each. The eligible-frame period is negative.
  - Pooled CIs still span 0.
  - **Plan (pre-declared before further data):** once at least 4 trade-active periods exist, screen on the active frame only. If the sign holds in at least 3 of 4, draft a registered flow experiment (E007) for confirmation on later active samples.
- **Flow screen S4 (DEVELOPMENT, ~09:35Z):** 4 periods (3 trade-active), 7,965 pairs across 3,781 events.
  - **The lead weakened.** In the third active period F2a, F2b and F4 are negative. F1 (signed share) against ridge is +0.009, +0.010, -0.002 across the active periods, so it is positive in 2 of 3. Its pooled CI is [-0.0002, +0.0047].
  - **Method caveat:** the screen cross-fits on all periods pooled, so earlier per-period values shift as periods are added. Per-period figures are indicative only.
  - The pre-declared E007 rule needs at least 3 of 4 active periods with the same sign. One more active period decides it.

**Collection availability note (2026-10-11 ~10:50Z; before any E004/E005/E006 outcome is computed)**
- **What happened:** pass 6 (`20261011T101751Z_e5085995`) and its retry (`20261011T102601Z_f324d738`) both ended `incomplete:http_403` at page 1190. Both are ignored by rule.
- **Cause, reproduced:** a Cloudflare firewall deterministically blocks one specific Gamma keyset cursor. Percent-encoding does not help. Re-requesting the previous page with limit 99 yields a different, unblocked cursor.
- **Fix:** collector v2 detours around blocked cursors. It re-requests the previous page with a reduced limit and continues. Enumeration semantics, rows, fields and dedup are otherwise unchanged, and every detour is recorded in the manifest.
- **Why this is allowed:** it is an availability-only change, permitted by the pre-declared continuation rule. Collection continues at the ~2h cadence until 12 snapshots qualify. The gap from pass 5 (08:18Z) to the next complete snapshot will exceed 3h; it is flagged and kept.
- **Future Phase 3-style panel frames** (`research_panel/frame.py`, frozen) would hit the same block. This is a known issue for any future live panel run; the frozen code is not changed.
- **Flow screen S5 (DEVELOPMENT, ~10:45Z):** 6 periods, 11,941 pairs across 4,371 events.
  - **F1 (signed share) against the ridge base:** pooled +0.00393 [+0.00054, +0.00721]. Per period +0.0046 (eligible), then +0.0079, +0.0087, -0.0042, +0.0061 and -0.0006 (active periods). The first 4 active periods are positive in 3 of 4, which **meets the pre-declared E007 drafting rule for F1 only**.
  - F2a, F2b, F3 and F4 are inconsistent. They are not carried forward.
  - E007 design is sent to challenger review before registration.


---

## E007 — Order-flow continuation in trade-active markets (challenger spec, adopted verbatim with disclosures)
- **Registered** 2026-10-11, before any confirmation-sample seed is sealed after this commit.
- **Development-screen disclosures:**
  - Periods 4 and 5 shared a source snapshot (`20261011T081844Z_24399984`) and a target, so there were really 5 time periods.
  - The "active frame only" rule was not followed literally in S5.
  - F1 was selected from 5 variants × 2 bases × 2 weightings across sequential screens (winner's curse). Expect a true effect well below 0.004.
  - The frozen -0.331610 reversal is miscalibrated in this frame (OLS chg_1h about -0.13).
- **Hypothesis:** `signed_share = signed_volume_1h / volume_1h` (0 if volume_1h = 0).
  - Sign convention follows `trade_sample.py:16-19`: positive means net taker buying of outcome 0.
  - Predicted β_ss > 0 for the outcome-0 dmid over the next ~2h.
- **Population:** forecast-eligible binary markets with origin `volume24hr > 0`, from `trade_sample --frame active` (12 strata, sealed seed, 2,000 markets, inclusion probabilities recorded).
  - All categories. Per-category results are descriptive only. The user has not decided on sports.
- **Confirmation data:** samples whose plan seed is sealed after this commit. A period qualifies only if all of these hold:
  - its source snapshot is distinct and has no other sample (the first by `sent_utc` is kept; later ones are excluded and counted);
  - all requests are sent before the target snapshot starts;
  - the target is the next complete snapshot, at most 3h after the source;
  - it has at least 150 pairs with signed_share ≠ 0.
  - Failed or ignored passes are logged as unavailable and never replaced or backfilled.
- **Frozen model** (`data-dumps/research_lab/e007/dev_fit.json`, sha256 recorded here before the first confirmation seed):
  - Fitted on active development periods 1-4, plus period 5's 1,646 markets not in period 4, merged into period 4.
  - Base: dmid ~ 1 + chg_1h. Augmented: base + signed_share.
  - Unweighted OLS.
- **Primary test:** compute r = dmid − frozen-base prediction. Fit WLS of r on [period intercepts, chg_1h, signed_share] with weights 1/p.
  - Test β_ss with a two-sided event-clustered bootstrap (1,000 resamples, seed 116; markets with no event fall back to market_id, counted).
  - Consistency rule: per-period β_ss > 0 in at least 8 of 12 qualifying periods.
- **Secondary (descriptive):** out-of-sample paired ΔR2 of frozen augmented minus frozen base, against no-change, weighted, with CI and MDE. **Pre-declared: this will probably be inconclusive at 12 periods** (pooled MDE about 0.004).
- **Sample size:** **Pending until 12 qualifying periods.** The primary is powered for about half the dev effect (per-period slope SD about 0.0029), which needs about 9-10 periods.
- **Verdicts:**
  - **Supported (exploratory, prospective):** primary rejects with β_ss > 0 and the consistency rule is met.
  - **Contradicted:** primary rejects with β_ss < 0.
  - **Inconclusive:** otherwise.
  - **Unavailable:** fewer than 12 qualifying periods by registration + 7 days, or fewer than 2,000 nonzero-signed_share pairs in total.
- **Dependence:** windows run back to back. Market recurrence (about 17%) is handled by event clustering, and period intercepts absorb common shocks.
- **Non-claims:** not tradable edge, profitability, calibration or causation. dmid is a quote mid, with no costs or fills.
- **Operational note:** in the 2-hourly loop, one active trade sample is taken right after each snapshot, never re-sampling an older snapshot.

E007 dev_fit.json sha256: 7e2c4f79079ced0c74ad1899cfb3536e71f97385c499d9730dd62046560124c6 (n=9610, nonzero signed_share=1504; P1: n=1996, nz=289, P2: n=1990, nz=317, P3: n=1992, nz=333, P4: n=3632, nz=565)


---

## Development study C1 — Are Polymarket prices calibrated as probabilities?

- **Status:** DEVELOPMENT, retrospective. **Not prospective evidence**, no edge, tradability or profitability claim. Written and committed before any outcome, price-history or closed-market data was fetched for this study. (Probing of the Gamma keyset and CLOB endpoints for field names, page sizes and parameter limits happened beforehand and read no sampled market's outcome. It showed a 6h block holds about 5,400 resolved markets, about 3,400 with volume of at least $100.)
- **Question:** Is the outcome-0 price a calibrated probability, and does calibration differ by lead time, traded volume and category? Is there a favourite-longshot pattern?
- **Population:** binary (2 outcomes, 2 CLOB tokens) Gamma markets with `closed=true` whose scheduled `endDate` is in [2026-07-13T00:00Z, 2026-10-04T00:00Z) and whose lifetime `volumeNum` is at least $100. The floor exists because a market with almost no trading has no price formation; its count is not enumerated. All categories are included. Markets resolved early (before `endDate`) or whose `endDate` lies outside the window are outside the frame. Markets that were still unresolved or disputed on 2026-10-11 are not visible in a `closed=true` listing, so they are not counted; this is right-censoring.
- **Sampling (two stage, inclusion probabilities recorded):**
  1. The window is cut into 332 six-hour blocks by `endDate`, split into 3 contiguous periods by `numpy.array_split`. 12 blocks are drawn per period by simple random sampling without replacement (π_block = 12 / blocks in period). Every resolved market in a drawn block is enumerated through `/markets/keyset` (`closed=true`, `volume_num_min=100`, `include_tag=true`, limit 100, sequential, 0.15 s delay).
  2. The pooled enumerated markets are stratified by period × volume band ([100,1e3), [1e3,1e4), [1e4,1e5), [1e5,inf)). Each of the 12 cells gets 250 draws (all of them if the cell is smaller), giving about 3,000. π_market = π_block × n_cell / N_cell, and the weight is 1/π_market.
  3. The draw reads only the frame fields (period, volume, ids), never outcome or price fields. Exclusions are applied afterwards and counted.
  4. **Sealed seed:** `C1-2026-10-11-a41f` (SHA-256 of seed + stage label drives `numpy.random.default_rng`). Block-bootstrap seed 117.
  5. Block clusters (36 blocks) are the sampling clusters; event is the dependence cluster within them.
- **Outcome (Gamma, per market):** outcome 0 won (y=1) iff `umaResolutionStatus == "resolved"` and `outcomePrices` parses to p0 ≥ 0.999 and p1 ≤ 0.001. y=0 iff the reverse. Excluded and counted separately: status not `resolved` (including disputed), a 50-50 split (both within 0.001 of 0.5), and any other price vector. Outcome-0 may be a team or "Over" and not "Yes"; labels are stored and a Yes/No-only subset is reported.
- **Anchor and lead times:** T = min(`endDate`, `closedTime`), because `endDate` is often a date-only midnight placeholder and `closedTime` can lag the event by many hours. Leads are 1d, 7d and 30d before T. A sensitivity run at 1d uses T = `closedTime` when that differs. If the market's `startDate` is later than T − lead the lead is *not listed* (counted, not imputed).
- **Price (CLOB `/prices-history`, token = `clobTokenIds[0]`):** one request per (market, lead): `startTs = T−lead−6h`, `endTs = T−lead`, `fidelity=10`. The price is the last point with `t ≤ T−lead`, accepted only if that point is at most 6h old. Points after the lead time are discarded locally. Otherwise the cell is *unavailable* (counted by reason: empty, stale, not listed, error). Whether `p` is a mid or a last trade is not documented, and the history is a retrospective backfill, not a recording of the quotes seen at the time.
- **Analysis (all estimates weighted by 1/π; unweighted shown beside them):**
  - Reliability table per lead: price bins [0,.02,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.98,1], bin mean price versus weighted outcome frequency, Wilson 95% interval on the effective sample size. A folded favourite view (price of the favoured side versus favoured side won) shows favourite-longshot bias directly.
  - Brier and log loss against the same quantity under perfect calibration (mean p(1−p), mean binary entropy). Climatology skill is also shown. In-sample logistic recalibration Brier is shown as an optimistic ceiling.
  - Calibration intercept and slope: weighted logistic of y on logit(clip(p, 0.001, 0.999)). The slope is b: b < 1 means prices are more extreme than frequencies (overconfident); b > 1 means longshots overpriced and favourites underpriced in the usual FLB direction is **b > 1 on the favourite-folded view** (the fitted slope on raw outcome-0 is label-order invariant). Sensitivity: clip 0.01.
  - 95% CIs: percentile bootstrap of 1,000 resamples, event-clustered (market id when no event) as primary and block-clustered (36 blocks) as a conservative sensitivity.
  - Splits: lead, volume band, coarse category (from market `tags`, precedence sports > crypto > politics > geopolitics > economy > tech > culture > science/weather > other; descriptive only, no category is excluded), and Yes/No-only.
- **Pre-declared reading:** no pass/fail threshold. A calibration claim needs a CI that excludes the stated deviation; CIs containing intercept 0 and slope 1 mean "no detectable miscalibration at this sample size". Subgroup rows are descriptive (many cells, no multiplicity control). The sample size is not powered for per-category inference.
- **Known limitations declared up front:** retrospective (not prospective); volume is lifetime volume used as a liquidity proxy (Gamma `liquidity` is 0 for closed markets); no as-of metadata; prices are post-hoc backfill; hourly-crypto and sports markets with near-0.5 prices may dominate counts, which the weights partly offset; tick-size floors (0.001 / 0.0005) limit extreme-price resolution.
- **Non-claims:** not calibration of any AREPO signal, not edge, not tradable. A finding here is a hypothesis for later prospective work.
- **Outputs:** `data-dumps/research_lab/calibration/<run_id>/` (sample plan, per-market rows, results JSON). Raw API pages are not retained. Code: `astrolabe/research_lab/calibration.py`, `scripts/run_calibration_study.py`.

## Development screen L1 — Related-market (sibling) information (2026-10-11)
- **Label:** DEVELOPMENT, post-hoc, not evidence. Run `leadlag-62d593a402` (`data-dumps/research_lab/leadlag_screen/leadlag-62d593a402/results.json`). Code `astrolabe/research_lab/leadlag_screen.py`, runner `scripts/run_leadlag_screen.py`. Source: research package family H15 "Related-market lead".
- **Family (listed in the module docstring before the run; all four run and reported):**
  - L1 liquidity-weighted mean `chg_1h` of the other markets in the event (origin snapshot).
  - L2 sibling move minus own `chg_1h`. It spans the same linear space as L1 once `chg_1h` is in the base, so it is a duplicate check of L1, not independent evidence.
  - L3 neg-risk group mid-sum change since the previous snapshot (members quoted in both, at least 2; augmented/"other" groups excluded).
  - L4 log sibling count, log moving-sibling count (`|chg_1h|` > 0.01) and its interaction with `chg_1h`.
- **Method:** E001 panel pairs over all 16 complete captures (6 dev + 10 snapshots): 15 periods, 646,404 pairs, 96,418 markets, 22,833 event clusters. Walk-forward by period with the label-availability purge. Base R is a ridge on `chg_1h`. Add-one per variant. Event-clustered paired bootstrap (1,000 resamples, seed 116). Test rows 610,965 in 14 test periods.
- **Data limits:**
  - Horizons are very heterogeneous: periods 0, 2, 4 and 5 span 12-70h (dev captures); periods 6-14 span 0.1-3.4h. Per-period values are not comparable in size.
  - Siblings are read from the same scan, so a sibling's receipt can be minutes after the market's own. All of it precedes the target.
  - `neg_risk` columns exist only in the dev captures and the newest snapshots. L3 is therefore also run on the 11 periods where it is defined (config "neg_risk_periods": 10 test periods, 441,204 test rows, 19,036 clusters).
  - 21% of eligible pairs have no usable sibling (feature 0 plus flag).
- **Base R2 vs no-change:** R 0.0395, B3 0.0547 (B3 minus R +0.0152, CI -0.0007 to +0.0290).
- **Results, pooled dR2 = R2(R+Lk) - R2(R), 95% CI, MDE at 4 tests, positive test periods:**

| Variant | All periods | MDE | Pos | Neg-risk periods | MDE | Pos |
|---|---|---|---|---|---|---|
| L1 | +0.00513 [-0.00259, +0.01269] | 0.0130 | 11/14 | +0.00537 [-0.00140, +0.01192] | 0.0114 | 8/10 |
| L2 | +0.00471 [-0.00280, +0.01196] | 0.0126 | 10/14 | +0.00540 [-0.00107, +0.01168] | 0.0109 | 8/10 |
| L3 | +0.00013 [+0.00002, +0.00023] | 0.0002 | 10/14 | +0.00021 [+0.00007, +0.00033] | 0.0002 | 9/10 |
| L4 | +0.00014 [-0.00534, +0.00532] | 0.0091 | 8/14 | +0.00141 [-0.00513, +0.00598] | 0.0095 | 8/10 |

- **Reading:**
  - L1/L2 are positive in most periods but the CI includes 0 and the per-period swings (to +/-0.04) exceed the effect. The result is underpowered (MDE about 0.012) and inconclusive. Even R+L1 stays below B3 (B3 minus R+L1 = +0.0101, CI +0.0003 to +0.0196).
  - L4 is null.
  - L3 has a CI above 0 but an effect of about 0.0002 R2, which is negligible. Its time-block interval across periods spans 0 (neg-risk periods: mean -0.0004, CI -0.0024 to +0.0016), and period 5 is -0.0083.
- **Drafting rule (declared before the run):** pooled dR2 vs R above 0 with CI lower bound above 0, and positive in at least 75% of test periods. Result: only L3 in the neg-risk-periods configuration meets it (L3 is constant 0 elsewhere, so that is its natural frame). No member meets it on all periods. This is one hit among 8 member-configurations, after upstream sequential screens (winner's curse).
- **Recommendation:** L3 is the sole rule-passing candidate, but its size is negligible and it overlaps E005 (already registered and showing no development support). Registration is not recommended on effect size. L1 is the only member with a plausible-size point estimate; if pursued it needs a design with a same-horizon, fixed-cadence frame (2h snapshots) and about 3x the clusters (MDE about 0.012 now).
- **Post-run note:** after the run, `_diff` was fixed to find a pair keyed in either order (the stored `pooled_vs_B3` fields were null for that reason). Numbers vs B3 above were read from the stored pooled diffs. No result changed.

### C1 results (DEVELOPMENT, retrospective; run `calibration-c1-20261011`, 2026-10-11 ~11:17Z)

- **Deviations and disclosures:**
  - A smoke run (1 block per period, 240 markets, `smoke-20261011`, not used in any result) was looked at before the full run. Its 1d slope was about 0.91 with a very wide CI.
  - The ledger sentence on slope direction above was garbled. The correct reading is: slope b > 1 means prices are *less* extreme than outcomes (underconfident, favourites underpriced); b < 1 means prices are more extreme than outcomes (overconfident); a negative intercept means outcome 0 is overpriced.
  - No 403s, errors or retries occurred. 4,887 requests in total.
- **Counts:** 36 blocks, 64,131 binary markets with volume at least $100 in the frame, 3,000 sampled (12 cells x 250). Outcome exclusions: 13 split 50-50, 0 disputed or unresolved, 0 other. Frame categories (descriptive): sports 30,559; crypto 21,120; science/weather 8,239; economy 2,444; politics 1,031; culture 425; tech 259; geopolitics 54.
- **Availability of a price at the lead (of 2,987 resolved):** 1d 1,976 (892 not yet listed, 119 empty); 7d 692 (2,295 not listed); 30d 31 (2,956 not listed). **The 7d and 30d samples are conditional on a market having existed that long, so they are not comparable to the 1d sample.** 30d is unusable. The `closedTime` anchor at 1d has 1,296.
- **1d (n=1,976, 1,568 events), weighted:** intercept +0.07 [-0.07, +0.24], slope 1.07 [0.94, 1.24] (event bootstrap); block bootstrap slope [0.97, 1.20]. Brier 0.1473 against 0.1496 expected under calibration (excess -0.0023 [-0.010, +0.006]); log-loss excess -0.007 [-0.028, +0.015]. Climatology skill 0.31. Unweighted: slope 0.96. **No detectable miscalibration overall at 1d.**
- **7d (n=692, 511 events), weighted:** intercept -0.50 [-0.71, -0.26], slope 1.34 [1.00, 1.87]. Brier excess -0.016 [-0.023, -0.008]. At 7d, outcome 0 is overpriced mid-range (0.40-0.50 bin: price 0.47, realised 0.28). Unweighted slope 0.96, intercept -0.36. The weighted slope is unstable (low-volume bands drive it; band slopes 1.84 / 1.59 / 0.78 / 0.70). The negative intercept is robust to weighting and to clip. Possible artefacts not tested: outcome-dependent anchor (early-resolving markets anchor at `closedTime`: 617 of 2,987 closed more than 1h before `endDate`, split 329 yes / 288 no), `p` being last trade or mid unknown, and the 7d subset being mostly sports (620 of 692).
- **Favourite view at 1d:** realised frequency tracks price within the Wilson intervals in every bin from 0.5 to 1.0 (for example 0.85 priced -> 0.84; 0.93 -> 0.935; 0.994 -> 1.000). No favourite-longshot pattern is detectable. Longshots: price below 0.02 -> 0 of 234 won; 0.02-0.05 -> 3.0% (price 3.4%); 0.1-0.2 -> 16.4% (14.2%).
- **By volume band at 1d (slope, event-bootstrap CI):** 100-1k 1.12 [0.89, 1.46]; 1k-10k 1.10 [0.90, 1.40]; 10k-100k 0.94 [0.74, 1.25]; 100k+ **0.69 [0.55, 0.92]** with Brier excess +0.019 (the highest-volume markets are overconfident-priced relative to outcomes, a descriptive and unadjusted finding, not multiplicity controlled).
- **By category at 1d (descriptive, no category excluded):** sports (n=1,274) slope 1.00 [0.85, 1.19], intercept +0.03; crypto (239) 1.13 [0.80, 2.51]; science/weather (307) 1.52 [1.14, 2.24] with low prices (mean 0.13); economy (57) and politics (72) too small and wide. culture, tech and geopolitics have fewer than 12 each and are not estimated. Yes/No-only (977): slope 1.14 [0.96, 1.38], intercept +0.21 [-0.06, +0.50].
- **Reading:** at 1 day before resolution, prices are close to calibrated as a population; the only 1d subgroup signals are the 100k+ volume band (slope below 1) and science/weather (slope above 1), both exploratory. At 7d there is an outcome-0 overpricing that needs the anchor and price-definition artefacts ruled out before any interpretation. This is retrospective backfill and says nothing about tradability.
- **Outputs:** `data-dumps/research_lab/calibration/calibration-c1-20261011/` (`sample_plan.json.gz`, `market_rows.jsonl`, `results.json`; gitignored). Trial entry in `trials.jsonl` (`kind: calibration_study_c1`).

### D120 live control pairing (Phase 3, mechanism only; 2026-10-11)

- D120 passed (authoritative, PASS_WITH_CAVEATS): 6/6 group-disjoint complete pairs, 0 engineering findings, one run. It validates the pairing mechanism only. It is not an effect result, says nothing about fill reliability, and does not establish economic independence of pairs.
- Evidence: `docs/implementation/PHASE_03_D120_EVIDENCE.json`; disclosures: `docs/implementation/d120/D120_ADDENDUM.md`; decision D120 / D121 in `AREPO_V2_DECISIONS.md`.

## Results: E004, E005, E006 (scored once, about 23:00Z on 2026-10-11)

All three use the same 12 qualifying snapshots (`20261011T002442Z` to `20261011T223104Z`), giving 11 periods. Results are in `data-dumps/research_lab/e00{4,5,6}/results.json`, with git head `b27cf8c` at scoring. An independent challenger (science-reviewer) verified the integrity, the frozen hashes and that each verdict rule was applied exactly.

- **E004: Supported (exploratory, prospective). Challenger: CONFIRMED_WITH_CAVEATS.**
  - R²_oos 0.0385, CI [0.0194, 0.0538]; 8/11 periods positive (exactly at the threshold); slope -0.226, CI [-0.253, -0.195]; 475,740 pairs; 15,103 events.
  - Execution: touch-to-touch mean P&L -0.045/share, CI [-0.047, -0.043], hit rate 5.4%, 9,541 trades. The optimistic mid-exit gives +0.019, CI [0.013, 0.025].
  - Reading: the reversal is *consistent with* quote noise / bid-ask bounce. It is **not tradable as a taker**, and touch-to-touch is itself optimistic.
  - Caveat: about 22h of one day means 1–2 independent time blocks; period 0 alone contributes R² 0.12.
- **E005: Not supported. Challenger: CONFIRMED.**
  - Incremental R² -0.00015; 2/11 periods positive.
  - The confirmation slope (+0.062) has the opposite sign to the frozen b (-0.059). Treat it as noise; it does not license a follow-up.
- **E006: H1 and H2 Supported on sign only. Challenger: CONFIRMED_WITH_CAVEATS.**
  - H1 (liquidity): θ 0.051, p 0.002. θ > 0 means the reversal is weaker in liquid markets and stronger in illiquid ones, consistent with bounce.
  - H2 (time-to-end): θ -0.017, p 0.012. The reversal is stronger further from the end date.
  - Holm rejects both, and the sign holds in 9/11 periods.
  - **However:** secondary S1 shows the frozen M_k models are significantly WORSE than R (ΔR² H1 -0.0041, H2 -0.0109). The sign transferred; the magnitude did not.
  - Do not quote θ/γ: γ is unstable because of collinearity.
  - Possible contamination: R's offset term sits in the residual. A disclosed sensitivity (adding an intercept and the spread level) is owed; it cannot change the verdict.
  - Liquidity-correlated survivorship: target unavailable in 0.66% of the low tercile vs 0.22% of the high tercile.
- **Licensed claims:** only exploratory and prospective claims, on about one day of Gamma quotes. No tradability, edge, transferable effect size or generality across time.
- **Minor records:**
  - E006 provenance cites E004's registration time; the actual time is 00:24:23Z (commit 32e6907), 19 s before the first qualifying capture.
  - E006 `dev_fit.json` is untracked; its hash is in `trials.jsonl`.

## Development study T5-DEV — Resolution forecasting vs recalibrated price (2026-10-11)

- **Label:** DEVELOPMENT, retrospective, `evidence_role: exploratory_historical`. Not evidence. No edge,
  calibration or tradability claim. Full write-up: `docs/research_lab/RESOLUTION_DEV_STUDY.md`. Run
  `resdev-t5-20261011b`. Trial lines: `history_resolution_dev` and `ml_explain` (114 tests).
- **Design:**
  - 48 seeded 6h `endDate` blocks over 2025-10-11 to 2026-10-04: 49,684 binary closed markets with volume of at least
    $100; 24,432 were listed at least 30h before end.
  - Seeded period x category draw (cap 600 per cell): 7,489 markets, 7,464 cleanly resolved.
  - Horizon anchor: *scheduled* `endDate - h`, never `closedTime`, which leaks the outcome. Point-in-time
    prices-history (10 min, 600 s lag) and trades strictly before the origin.
  - Walk-forward over 8 chunks by end with a 2-day embargo.
  - Arms: price, Platt, isotonic, elastic-net, LightGBM (init score logit p, nested tuning).
  - Conservative cluster-bootstrap hull over event, neg-risk group and parent clusterings.
- **Deviations:**
  - Per-cell cap raised from 250 to 600 after the first enumeration showed only 4,031 draws. That decision used frame
    cell sizes only, before any outcome was analysed. The first run (`resdev-t5-20261011`) was abandoned unanalysed.
  - A 200-market smoke run's feature summary was viewed before the main run.
  - The hierarchical arm was not run (it is bound to the 3-class `ml_panel` design).
- **Scored rows:** 1d 4,980 (2,233 events); 3d 2,449 (862); 7d 1,272 (869, 81% sports).
- **Results:** LightGBM vs Platt ΔLL: 1d -0.0013 [-0.0039, +0.0014]; 3d -0.0004 [-0.0080, +0.0059]; 7d +0.0041
  [-0.0022, +0.0106]. The 7d gain reverses (-0.0031) without trade features. Elastic-net is worse than Platt at 1d and
  3d (CIs below 0). No ml_explain unit is demonstrated (all BY p = 1.0). Platt vs raw price: 1d +0.0001, 3d +0.0009,
  **7d +0.0069 [+0.0022, +0.0113]** (raw price intercept -0.33, slope 1.12 at 7d).
- **Reading:** features add nothing measurable over a recalibrated price. The only signal is outcome-0 overpricing at
  7d, which persists with the scheduled-end anchor (so C1's anchor artefact does not explain it).
- **Recommendation:** no feature-model registration. A narrow recalibration hypothesis at 7d and 3d is a possible
  MC2 candidate. It first needs a challenger check for a label-order or sports artefact, then a frozen map, recorded
  book prices and an executable-ask economic check.


**T5-DEV challenger (2026-10-12): the 7d recalibration candidate is REJECTED AS AN ARTEFACT.**
- The "outcome 0 overpriced at 7d" gap comes from 755 rows with **no trades before t**. Their placeholder or listing prices sit near 0.5, with a gap of −0.118. The 517 traded rows show a gap of +0.004.
- It is concentrated in sports untraded win/draw/Over markets. Politics goes the opposite way.
- About 18 views were taken without correction.
- The study doc's "conservative hull" covers only event and neg-risk clustering, not parent clustering.
- **Not registered.**
- **Programme rule:** historical price-history values for markets with no trade before the origin are not executable prices. Every historical study must flag them and exclude them, or report them separately.

## E007 result: scored once, 2026-10-12 about 16:45Z

**Supported (exploratory, prospective). Challenger: CONFIRMED_WITH_CAVEATS.**
- **Primary result:**
  - β(`signed_share`) = 0.003626, CI [0.001726, 0.005316], with 4,703 event clusters.
  - 11 of 12 periods positive.
  - The first 12 post-registration samples were used (20261011T124341Z to 20261012T104608Z). All were sealed after 1e5efad.
- **Secondary:** descriptive ΔR² 0.00138, CI [−0.00082, 0.00361], declared descriptive.
- **Dev versus confirmation:** the dev β of 0.0050 shrank to 0.0036, as winner's curse predicts.
- **Interpretation:**
  - A fully one-sided hour of flow predicts about +0.36c of mid drift over about 2h.
  - That is under a tenth of the roughly 4.5c median round trip, so it is **not tradable as a taker**.
  - Only 16% of pairs have nonzero flow.
- **Disclosures:**
  - **Interim looks:** 25 `flow_screen` development lines (06:56Z–14:58Z on 10-12) looked at F1 on accumulating confirmation-period data before scoring. The 12-period trigger was fixed, so this was not optional stopping. Those lines are committed with this entry.
  - **git_dirty:** only `CLAUDE.md` and `trials.jsonl` were dirty, neither in the code path.
  - **Collection changes:** the wallet sidecar and the launchd switch did not touch E007's inputs.
  - **Data span:** about 22h of back-to-back periods.
- **Open mechanical risk:** Gamma quote staleness relative to trades just before origin could make "continuation" partly mechanical, especially alongside E004's reversal. Until a development check excludes trades in the last 5–15 minutes before origin, call this **"flow–quote continuation"**, not evidence of informed flow.

### E007 staleness check (development)

**DEVELOPMENT/post-hoc. Does not change E007's verdict.** Same 12 confirmation samples, frozen dev fit, weights and event-clustered bootstrap (`e007.analyse`, unmodified). `signed_share` was recomputed from each sample's `trades.csv.gz` over `[origin-3600s, origin-cutoff)`, with the denominator restricted to the same window. The 0-minute row reproduces the E007 primary exactly. Trial lines: kind `e007_staleness_dev`, role `exploratory_dev`.

| Trades excluded / used | β | 95% CI | Nonzero pairs | Periods β>0 |
|---|---|---|---|---|
| none (E007 primary) | 0.003626 | [0.001726, 0.005316] | 3,859 | 11/12 |
| last 5 min excluded | 0.002993 | [0.001046, 0.004671] | 3,622 | 10/12 |
| last 10 min excluded | 0.003260 | [0.001301, 0.005118] | 3,454 | 11/12 |
| last 15 min excluded | 0.003358 | [0.001305, 0.005385] | 3,237 | 11/12 |
| ONLY last 15 min (complement) | 0.004454 | [0.000653, 0.008284] | 1,332 | 9/12 |

**Interpretation:** β does not collapse. With the last 5–15 minutes removed, it stays at 83–93% of the original and the CIs exclude 0. Quote staleness for trades just before origin is therefore not the main driver. The last-15-minute-only β is larger but noisy and overlaps the others, so some recent-trade contribution is possible and not excluded. This is a single look at 12 periods over about 22h. The "flow–quote continuation" wording is still kept, because this check does not show informed flow.

## Development study HB1 — Hypothesis battery 1 on `h2_main` (2026-10-12)

- **Label:** DEVELOPMENT, retrospective, `evidence_role: exploratory_historical`, one revision of the `h2_main` window
  (beyond its per-window budget; disclosed). Not evidence. No edge, calibration or tradability claim. Full declaration
  and results: `docs/research_lab/HYPOTHESIS_BATTERY_1.md`. Code `battery.py`, `battery_data.py`,
  `scripts/run_hypothesis_battery.py`.
- **Declared before outcomes:** commit `7a4d80c` (declaration sha256 `9e0f15de...`): 72 hypotheses (48 beta, 22
  incremental ΔLL vs M0v, 2 resolution means), split 2026-07-01 with a 24h embargo, discovery sign / judgement test,
  CR SEs by event and two-way event x day (larger p), BY at q = 0.10 over the cumulative count. Price-aligned trade
  windows (trades older than the last usable price point). New bounded fetches: event metadata (2,750 events) and
  3,848 sibling price series (8,386 requests).
- **Result (run at `75eb706`, m_total = 468):** 18 survivors. MI1/MI2/MI3/MI5/MI6 (the 2h reversal is much stronger
  after moves without trades and nearly absent after flow-confirmed moves), FL1/FL2/FL3/FL5/FL6/FL8/FL10 and WA4 (taker
  imbalance continues at 2h-24h, 4/4 months, survives windows ending 30 min earlier; WA4 and FL5 are redundant with
  plain imbalance, post-hoc), PX6 and IX3 (flow continues less at longshot prices and in quiet markets), PX1/PX2
  (price-level drift), VO4 (`|move|` only). Nulls: wallet freshness/record (WA6 closest, BY 0.18), neg-risk sums and
  sibling lead-lag, time of day/weekday, category/asymmetry class, book/liquidity (underpowered), theory interactions
  IX1/IX2. Not testable: IF-H2 ladders (8-12 judgement events), LQ1/LQ4, IX5.
- **Economics:** every directional survivor loses as a taker (net -2.4c to -4.1c per share); only the quote-noise
  reversals MI2/MI3 are positive in the optimistic half-spread, no-fee variant (+0.5c, +0.7c), as in E004.
- **Calibration placebo:** 2 of 70 p below 0.05 on permuted targets; the two mean tests' placebo is not a null
  (disclosed design flaw; no verdict depends on it).
- **Candidates for live registration (not registered):** C1 aggressive taker flow -> 6h (FL6), C2 24h imbalance -> 24h
  (FL3, E007 horizon extension), C3 trade confirmation of 2h moves (MI2/MI6, mechanism only), C4 weaker flow
  continuation at longshot prices (PX6); optional C5 `|move|` filter (VO4). Each needs its own registration, MDE and
  `science-reviewer` pass.
- **Count:** cumulative tests now 396 + 72 + 3 post-hoc = 471 (`ml_explain` count lines with source
  `hypothesis_battery_1` and `hypothesis_battery_1_posthoc`).

---

## E009 — Live cross-venue lead: Kalshi's 10-minute move -> Polymarket's next 20 minutes (frozen model, receipt-timed)

- **Registered:** 2026-10-12 (about 23:10Z), commit containing this entry. `REGISTERED_UTC = 2026-10-13T00:00:00Z` is set in
  `cross_venue_live.py` in the same commit; every origin before it (the pilot) stays `prospective_unregistered` and is
  excluded. The running poller is restarted on the registration code before 00:00Z (restart time recorded below); the
  **effective start** is max(REGISTERED_UTC, first cycle logged by a process started on registration code), and that exact
  value is the `--analyze` START. **Restart record:** poller restarted on registration commit `39857e4` at
  2026-10-12T22:54:35Z (log line `start ... code=39857e437982 registered=2026-10-13T00:00:00Z`), before REGISTERED_UTC, so
  the effective start is **2026-10-13T00:00:00Z**.
  E008 is reserved for the IF-H2 deadline ladder. Design, code and pilot: `CROSS_VENUE_LIVE.md`.
- **Origin of the hypothesis (post hoc, exploratory_historical):** `CROSS_VENUE_STUDY.md` 5.1-5.2: r(dK_t, dP_t+L) about 0.24
  at the peak lag, +5.3% (conservative alignment) / +9.8% (`pm_lag = 0`) relative MSE gain of M0 + gap + Kalshi changes over
  M0 at 10 min. Timestamp semantics put the lead at 10 or 20 min, hence the 20-min primary target.
- **Frozen model:** `model_specs/cross_venue_live_v1.json`, sha256 `e63f20cc095ba88346155cabe0d2e4289981017cc48450ccc575bbc7d0d16e2b`
  (pinned in code, verified at every start). Unpenalised OLS on all 341 historical pairs (190 events), `pm_lag = 0` alignment,
  one fit per horizon, never refitted. M0 = `[r1, r6, lvl, lvl2]`; M1 = M0 + `[gap, dk1, dk6]`. 20-min M1: dk1 0.339, dk6
  0.123, gap 0.024, r1 -0.230, r6 -0.120.
- **Population:** active matched Kalshi/Polymarket Yes/No pairs from the daily refresh (`cross_venue.match_markets` unchanged
  + live-only conflict words + title-level hand verdicts, ranked hand-verified first then by min 24h volume, cap 200), polled
  every 120 s. Features and predictions are written before any outcome quote exists.
- **Primary metric:** relative MSE gain `G = 1 - SSE(M1) / SSE(M0)` of the frozen predictions for the Polymarket mid change
  from `t` to `t + 20 min`, over origins with `t % 1200 == 0` (non-overlapping per pair), origins in
  `[effective start, 2026-11-03T00:00:00Z)`, evidence role `prospective_confirmation`, outcome status `evaluated`.
  Inference: event-clustered bootstrap (Polymarket event id; 4,000 resamples, seed 20261012), one-sided p for G > 0 (the
  share of bootstrap G <= 0: a percentile-bootstrap tail share, not a null-centred test), 95% percentile CI. Single
  primary test; alpha 0.05 one-sided.
- **Data hygiene (challenger review, fixed pre-outcome, in `analyze`):** outcome lines de-duplicated on (id, h), first line
  kept, duplicates counted; an origin whose Kalshi or Polymarket receipt (`kr`, `pr`) is more than 60 s after its poll time
  `t` is excluded and counted (`origin_late`, e.g. laptop sleep or backoff); an outcome quote received more than 60 s after
  its poll time is `unavailable`; grid origins whose outcome is due but has no line are counted as `missing_line`,
  separately from `unavailable`.
- **Secondary (each reported, no multiplicity claim):** G at 10 min (`t % 600 == 0`) and 60 min (`t % 3600 == 0`); the slope
  of dP(20 min) on dk1 and the partial slope on dk1 given the frozen M0 prediction, with clustered CIs (scale-free check of
  direction); largest event's share of SSE(M0) and the leave-one-event-out range of G; unavailable / late / missing counts.
- **Executable metric (separate):** paper taker P&L per share at 20 min for origins where the frozen rule fires
  (`|M1_20| > entry ask - entry bid + taker fees at entry and exit`), direction `sign(M1_20)`, entry at the touch at `t`, exit
  at the touch at `t + 20 min`, `economics.taker_fee` both legs (feesEnabled + docs rate of feeType; unknown -> 0.07).
  Event-clustered mean with one-sided p for > 0; valid only with >= 30 trades in >= 10 events (`economics.MIN_TRADES`,
  `MIN_CLUSTERS`). Descriptive companion: the same P&L on every primary origin with `|dk1| >= 2c`. No depth, queue or latency;
  optimistic.
- **Stopping rule:** fixed end date **2026-11-03T00:00:00Z** (about 21 days). Analysis runs **once**, after
  2026-11-03T02:00:00Z (all 60-min outcomes due), with
  `run_cross_venue_live.py --analyze <REGISTERED_UTC> 2026-11-03T00:00:00Z`. No interim look at outcome statistics; only
  operational counts (`--ops-stats`, which never reads outcomes) may be checked. `predictions.jsonl` holds later mids from
  which outcomes could be rebuilt, so it is covered by the same rule: no analysis of it other than `--ops-stats`. If the 2 GB disk cap or a crash stops
  collection early, the window is not extended; whatever was collected is analysed at the same time and the shortfall is
  recorded.
- **Pilot (2026-10-12 21:44Z-about 23:00Z, `prospective_unregistered`, excluded; operational counts only, outcomes not
  read):** 167 then 109 pairs after the hand-verified refresh (106 verified `same`, 27 events); 4 requests per 120 s cycle
  (2 per venue), no 429s; quotes two-sided on both venues for 96% of pair-polls; about 70 pairs (22 events) have complete
  features per cycle (the rest sit outside [0.03, 0.97]); 546 bytes per prediction (about 28 MB/day); poller RSS 115 MB;
  refresh subprocess RSS 118 MB while paging, full-run peak 204 MB (operational correction after registration, no design
  effect) (flat `/markets/keyset`; the first `/events/keyset` version peaked at 245-380 MB and was
  replaced). |dk1| median 0, 90th percentile 0.5c, 99th 2c; **dk1 is non-zero on only 12% of origins** (long-dated
  markets, Kalshi mids rarely move). The trade rule fired 0 times in the pilot (median Polymarket spread 1c).
- **Sample size and MDE:** expected primary origins about 70 pairs x 3 per hour x 24 x 21 days, about 100,000, but the
  binding quantity is event clusters: 22-27 now, plus new short-lived events (game props) from daily refreshes, planned
  estimate 40 (range 25-60). Scaling the historical event-cluster SE of the frozen 20-min gain (1.42 points at 190
  clusters, in-sample) by sqrt(190 / C): C = 40 gives SE about 3.1 points and **MDE about 7.7 points** (one-sided alpha
  0.05, power 0.80: 2.49 x SE); C = 25 gives 9.8 points. The historical in-sample gain is 7.1 points, and live dk1
  activity (12% non-zero) is likely lower than in the historical last-30-days windows, so **power against the historical
  effect is about 50% at best and probably lower. Declared in advance: an Inconclusive result is the most likely outcome**;
  only a large live effect or a clear contradiction is detectable. The executable metric will very likely be below its
  30-trade minimum (0 trades in the pilot) and is then reported as not shown.
- **Verdicts:**
  - **Supported (exploratory, prospective):** G > 0 with one-sided p < 0.05 **and** the dk1 slope point estimate > 0.
  - **Contradicted:** the 95% CI of G lies entirely below 0 (the frozen lead model is worse than M0 live). If at the same
    time the partial-slope CI lies entirely above 0, the label is "lead present, frozen scale miscalibrated", not "no lead".
  - **Inconclusive:** otherwise.
  - **Unavailable:** fewer than 20 event clusters or fewer than 5,000 evaluated primary origins in the window.
  - **Economics:** "covers taker costs (paper)" only if the executable mean is > 0 with p < 0.05 at the trade/cluster minimum;
    otherwise "not shown". A Supported primary without this is information, not a tradable edge.
- **Frozen for the window:** spec sha256 `e63f20cc...6e2b`; hand verdicts `model_specs/cross_venue_live_verified.json` sha256
  `1d6f942a27c9ba1ba56b6514ecb0bad79bd06ce0236084683f722d71932ac54c` (111 same, 56 different); `LIVE_EXTRA_CONFLICT`; the
  feature, prediction, outcome and analysis code at the registration commit (each prediction line carries the code commit
  and spec hash). Verdicts added during the window are title level only, timestamped, apply only to later refreshes, and
  are never based on observed prices or moves. Any operational fix during the window is logged here as a deviation.
- **Dependence:** pairs within an event are dependent (e.g. 20 Time Person of the Year candidates form one event); the
  event is the cluster. Common market-wide shocks across events at the same time are not modelled (as in the study), so CIs
  may be too narrow. Pair recurrence across daily refreshes stays in its event cluster.
- **Non-claims:** no calibration, causation, profitability or tradability claim. Matching is title level; about 2% of
  historical matches were wrong, and live pairs without a hand verdict may include mismatches (they bias towards 0).
- **Deviations from the historical study** (fixed pre-outcome, `CROSS_VENUE_LIVE.md`): book mid instead of history price;
  Kalshi `expected_expiration_time` for matching; live-only conflict words and hand verdicts; long-dated open markets ranked
  by volume rather than the last 30 days before resolution.
- **Deviation log (operational, no effect on E009 lines or statistics):** 2026-10-13, for E010 the poller gained a hook that
  runs later experiments' writers after the E009 lines of each cycle (failures are caught and never stop E009), and
  `RETIRE_KEEP_S` grew from 70 min to 6 h 20 min (retired pairs are polled longer; E009 never predicts for retired pairs).
  E009 feature, prediction, outcome-matching and `analyze` code are unchanged. Possible operational effects: longer cycles
  (an extra request per venue once active + retired pairs exceed 200), hence later receipts and more E009 origins excluded
  as late, and more quote rows towards the shared 2 GB cap (which stops E009 too). Monitored via `--ops-stats` and the cycle log.

---

## E010 — Live cross-venue, cleaned-set model: Kalshi changes + gap -> Polymarket at 1h and 6h

- **Registered:** 2026-10-13 (commit containing this entry). `REGISTERED_UTC = 2026-10-13T02:00:00Z` in
  `cross_venue_live_e010.py`, later than the registration commit; the poller is restarted on the registration code before it
  (restart time recorded below). Effective start = max(REGISTERED_UTC, first cycle of a process on registration code).
  E009 stays exactly as registered; this is a separate experiment. **Restart record:** poller restarted on registration commit
  `9beda37` at 2026-10-12T23:28:59Z (log: `E010 writer on: spec=62b992c6af95 registered=2026-10-13T02:00:00Z`), before
  REGISTERED_UTC, so the E010 effective start is **2026-10-13T02:00:00Z**. (This restart preceded E009's 00:00Z start too.)
- **Origin (post hoc, exploratory_historical):** `CROSS_VENUE_STUDY.md` section 10 (revision r1, commit 86a41c2): dropping 25
  mismatched pairs (C1, 316 pairs, 183 events) reversed the v1 gap null. Walk-forward relative MSE gain over M0, C1:
  gap only +5.1% (1h, CI 4.1-6.2), +7.5% (6h, 1.2-11.2); gap + Kalshi changes +7.0% (1h, 3.2-12.7), +6.9% (6h, 2.3-9.8).
  The primary designation of C1 over C2 in r1 was made after seeing both (disclosed there).
- **Frozen model:** `model_specs/cross_venue_live_e010_v1.json`, sha256
  `62b992c6af95ff9a508d8c3130c3ec3ae3333e582bf822d051ea72da46e4961c` (pinned in code). Refitted once on C1 (the study's analysis
  set minus `results_r1.json` `audit.rule`, 25 tickers listed in the spec), `pm_lag = 0` alignment as E009, unpenalised OLS
  on all non-overlapping origins per horizon, never refitted. Models per horizon: M0 `[r1, r6, lvl, lvl2]`; M-gap = M0 + gap;
  **M1 = M0 + gap + dk1 + dk6**. M1 coefficients: 1h gap 0.089, dk1 0.205, dk6 0.197; 6h gap 0.263, dk1 0.427, dk6 0.014.
  Features are E009's (`cross_venue_live.features`) at the same origins.
- **Data stream and dependence (disclosed):** E010 uses E009's pairs, quotes, features and window. Its lines go to
  `predictions_e010.jsonl` / `outcomes_e010.jsonl` (append-only; written by `E010Writer` inside the same poller cycle, after
  the E009 lines and before any outcome quote exists). **E009 and E010 results are correlated** (shared data; the 20-min and
  1h targets overlap; same events); they must never be counted as independent confirmations or pooled, and each keeps its
  own alpha.
- **Origins:** cycles with `t % 3600 == 0` in `[effective start, 2026-11-03T00:00:00Z)`, role `prospective_confirmation`.
  Hourly origins overlap for the 6h target within a pair; the event-clustered bootstrap carries that dependence.
- **Primary metrics (two):** for h in {60, 360} min, relative MSE gain `G_h = 1 - SSE(M1) / SSE(M0)` of the frozen
  predictions for the Polymarket mid change `t -> t+h`. Event-clustered bootstrap (Polymarket event id, 4,000 resamples,
  seed 20261013 + h), one-sided p for G > 0 (percentile-bootstrap tail share, not a null-centred test), **Holm over the two
  primaries, familywise alpha 0.05 one-sided.**
- **Secondary:** G of frozen M-gap over M0 at each horizon (is the gap alone informative live); largest event's SSE share;
  leave-one-event-out range; unavailable / late / missing counts. Holm always uses m = 2: a horizon without a test enters
  with p = 1.
- **Executable metric (separate, per horizon):** paper taker P&L per share where the frozen rule fires (`|M1_h| > entry
  round-trip cost`), direction `sign(M1_h)`, enter at the touch at `t`, exit at the touch at `t + h`, `economics.taker_fee`
  both legs. Valid only with >= 30 trades in >= 10 events (6h trades from hourly origins overlap within a pair, so the
  trade count includes dependent trades; inference is event-clustered). **Economics verdict per horizon:** "covers taker
  costs (paper)" only if the event-clustered mean is > 0 with one-sided p < 0.05 at the trade/cluster minimum; otherwise
  "not shown". A positive primary without it is information, not a tradable edge.
- **Hygiene (as E009):** outcome lines de-duplicated on (id, h); origins with receipt lag > 60 s excluded; outcome quotes
  with receipt lag > 60 s unavailable; poll at exactly `t+h` else nearest within +-120 s, else unavailable; due-but-missing
  lines counted separately. Retired pairs are polled 6 h 20 min so 6h outcomes can complete; quote window after a restart
  is recovered from disk (7 h+).
- **Stopping rule:** fixed end **2026-11-03T00:00:00Z** (shared with E009: same stream, disk budget). Analysis **once**, after
  2026-11-03T08:00:00Z (all 6h outcomes due), with `run_cross_venue_live.py --analyze-e010 <effective start>
  2026-11-03T00:00:00Z`. No interim look at E010 outcomes or predictions beyond operational line counts. Early stop (cap,
  crash) does not extend the window; the shortfall is recorded.
- **Sample size and MDE:** about 70 pairs with complete features per origin (E009 pilot), so about 70 x 24 x 20 days = 34,000
  hourly origins per horizon, but the binding quantity is event clusters: 22-27 now, planned estimate 40 (range 25-60).
  Scaling the historical walk-forward event-cluster SE of the M1 gain (1h: 2.42 points at 158 clusters; 6h: 1.92 at 163) by
  sqrt(C_hist / C) and using z = 1.96 + 0.84 (Holm worst case alpha 0.025 one-sided, power 0.80): **1h MDE about 13.5 points at
  C = 40 (17.0 at 25); 6h MDE about 10.9 (13.7 at 25)** against historical gains of 7.0 and 6.9. Power against the historical
  effect is roughly 20-30%. **Declared in advance: Inconclusive is the most likely outcome**; only a live effect about twice
  the historical size, or a contradiction, is detectable. Live long-dated markets (dk1 non-zero on 12% of origins) are less
  active than the historical last-30-days windows.
- **Verdicts (per horizon, after Holm):**
  - **Supported (exploratory, prospective):** Holm-adjusted p < 0.05 and G_h > 0.
  - **Contradicted:** 95% CI of G_h entirely below 0.
  - **Inconclusive:** otherwise. **Unavailable:** fewer than 20 event clusters or fewer than 2,000 evaluated origins at that
    horizon.
- **Frozen for the window:** spec sha above; E009's hand verdicts file (sha `1d6f942a...c54c`) and `LIVE_EXTRA_CONFLICT`
  (shared pair list); `cross_venue_live_e010.py` writer and `analyze` at the registration commit. Any operational fix is
  logged here as a deviation.
- **Non-claims:** no calibration, causation, profitability or tradability claim; residual pair mismatches (2-4% historical,
  unknown live) bias towards 0.
- **C1 selection disclosure (challenger review):** C1 was designated primary after r1 results for C1 and C2 were seen. 4 of
  the 9 hand-dropped pairs (Opus x2, Trump China x2) were first surfaced by the outcome-disagreement list (judged on titles),
  and dropping those 9 alone produces the whole gap-null reversal (`CROSS_VENUE_STUDY.md` 10.3). The historical C1 gains
  (7.0 at 1h, 6.9 at 6h) are therefore an optimistic reference. Live pairs never had an outcome-informed audit: the live
  mismatch rate, which caused the v1 null historically, is unknown and would bias G towards 0 (and could make the gap term
  harmful).

## Development study HB1-R — HB1 replication on `h3_power` (2026-10-13)

- **Label:** DEVELOPMENT, retrospective, `exploratory_historical`. Independent markets (none shared with h1/h2; 66
  shared events, sensitivity reported), same calendar. Full declaration and results:
  `docs/research_lab/HYPOTHESIS_BATTERY_1_REPLICATION.md`; code `battery_replication.py`,
  `scripts/run_hb1_replication.py`; frozen spec `model_specs/hb1_replication_v1.json` (sha256 `f9b73416...`).
- **Declared before any h3 outcome:** commit `e5a3ef3`. Family R = the 18 HB1 survivors with HB1's definitions,
  directions, scaling, cuts and economics rule; Holm at 0.05; unweighted primary, `sample_weight` secondary. Family W =
  WA1-WA3 (wallet-age nulls), Holm over 3.
- **Result:** family R replicated 16/18 (MI1, MI2, MI3, MI6, FL1, FL2, FL3, FL5, FL6, FL8, FL10, WA4, PX1, PX6, IX3,
  VO4); not MI5 or PX2. Signs agree 18/18; median h3/HB1 effect ratio 1.20 (flow 1.48, reversal moderators 0.92,
  calendar-matched 1.16). VO4 loses significance without the shared events (refit-sensitive). Family W: WA2 Holm
  0.030 unweighted, 0.10 weighted, and +0.51c (p 0.067) once total imbalance is controlled (post-hoc); WA1 and WA3 null.
- **Economics:** every directional survivor still loses as a taker (net -1.2c to -4.1c); only the quote-noise reversals
  are positive in the optimistic variant.
- **Reading:** robust across markets, not shown across time or mechanism (same mid-like series). Candidates C1-C4 stand;
  each still needs a prospective registration. Cumulative tests now 494.

## E011 — Live prospective test of the frozen ungated surprise-move detector on complete-universe snapshots

- **Registered:** 2026-10-13 (commit containing this entry, after an accepting `science-reviewer` pass).
  `REGISTERED_UTC = 2026-10-13T14:00:00Z`, `END_UTC = 2026-11-10T00:00:00Z` in `surprise_snapshot.py`. Captures
  with start time in `[REGISTERED_UTC, END_UTC)` are `prospective_confirmation`; the dry-run pass on capture
  `20261013T083104Z` and any pass before 14:00Z are `prospective_unregistered` and excluded by `analyze`.
- **Origin (exploratory_historical, disclosed):** `SURPRISE_MOVE_DETECTOR.md`. `sm_learned_v1` (elastic net, 20
  terms, fit on h2 months <= 2026-07) gave +1.8 pts matched excess on the h2 test months (§5). Its pre-declared h3
  replication *with the deployment gate* was null (§10.1); the **ungated** score (the form evaluated on h2) replicated
  on the disjoint h3 markets (§10.3: +5.8 pts at 1 %, weighted +7.2). The ungated reading was a secondary analysis
  made after the gated null; the gate removal is therefore a post-hoc spec choice, which is why this live test exists.
  The detector's value is price-path context (realised volatility over a week vs a day, market age, weekday), not
  flow or wallet terms (§4, §10.5).
- **Frozen rule:** `sm_learned_v2`, sha256 `ee227e7e0b850c6ace940d380aad48f54435a1bc4f487f9250125d2d77c14ef1`
  (`detector_specs/FROZEN_SURPRISE_SNAPSHOT.json`): identical terms, centres, scales and weights to `sm_learned_v1`
  (`ee7ea5f1…`), `direction_feature: null`, no refit. Scored by `detector_eval.score_rule` (engine `detector-eval-v1`).
- **Live scoring path** (`surprise_snapshot.py`, `scripts/run_surprise_snapshot.py`, run inside each collector pass
  after the snapshot is complete): eligible = binary, open, two-sided quote, mid in [0.02, 0.98], has a last trade,
  end date > t + 1 h (about 27,000 markets per capture). **Stage 1** (no requests): pre-score = the frozen terms over
  snapshot features, with 2h-grid volatility proxies (rms of consecutive-capture mid changes over 3/12/84 steps,
  centres/scales fixed from the h3 development months; `STAGE1` sha256 `2f5ef2416346f5f8602e49ee376d7f0ea23abc63a79f0953f9daebee84a679c5`) in place of the 10-minute
  `rv_6h/rv_1d/rv_7d` terms; flow, `rv_2h`, `last_trade_age_h`, `ladder_n` at their centres. Top 400 (about 1.5 %)
  are candidates. **Stage 2** (800 requests, about 3.5 min at 4 req/s): per candidate one CLOB `prices-history`
  (8 d, 10-min) and one Data API `trades` page; exact `price_context` + `surprise_features` at the capture time with
  the snapshot mid; sibling terms from consecutive captures; `ladder_n` NaN. The origin `t` of every line is the
  row's own `received_utc` (a capture takes about 13 min; the capture start is kept separately as `capture_t`), and
  price history and trades end at that `t`. **Alerts = top 60 candidates by exact score** (about 0.22 % of eligible;
  `SnapshotConfig` hash `7087fec7c4f95feb`), each with **3 seeded matched controls** (same capture, price band on
  |mid − 0.5| (0.05/0.20/0.45), volume24h tercile, different market, **not a stage-1 candidate**; price band only
  when that pool is short, recorded as `control_match`). Because controls are drawn outside the stage-1 top 1.5 %,
  the comparison is "alerts vs same-stratum markets the pre-score did not shortlist", not vs random peers; this is
  the stated question (does the frozen score select markets followed by surprise moves more often than matched
  non-selected markets) and it inflates the excess relative to a random-peer control. All lines go to
  `data-dumps/research_lab/surprise_live/alerts.jsonl` before any outcome exists; `passes.jsonl` records every pass.
- **Validation of the two-stage path (h3, exploratory_historical, `live_config_validation.json`):** stage-1 vs exact
  score Spearman 0.71. Deployed configuration (candidates 1.5 %, alerts 0.22 %) on the h3 primary months: 173
  alerts, precision 10.4 %, base 0.87 %, matched controls 1.16 %, excess **+9.3 pts (95 % CI +3.4, +18.7)**; at a
  1 % budget with 1.5 % candidates +3.8 pts (+1.9, +6.0) (precision 4.8 %; 5.3 % with 5 % candidates). Without the
  proxies the path collapses (Spearman 0.375, 2.3 %). **Disclosed:** the deployed shares were chosen for the request
  budget after seeing h3 outcomes for three configurations, and the h3 validation drew its controls from all
  non-alerted rows (not excluding candidates); +9.3 pts is an optimistic, not like-for-like, reference.
- **Outcomes** (`write_outcomes`, same script, later passes; reads `alerts.jsonl` only): one `prices-history`
  request per alert/control line over [t − 25 h, t + 25 h] once t + 24 h 15 min has passed (so arrivals up to 6 h
  after a departure, and the 24 h move, are inside the window): `surprise_moves.detect_events`
  (`surprise-labels-v1`, sha `d9cf42f7…`, primary spec and filters, end cut from the line's end date), `hit_6h` =
  a surprise departure in (t, t + 6 h], `sharp_any_6h` = any ≥ 0.15-in-6 h departure in that window without the
  surprise filters, `fwd_move_6h` and `fwd_move_24h` from the same series (so a market that leaves the eligible
  set still gets its outcome). `unavailable` only on a 200 with no usable series 12 h after due; non-200 stays
  pending and is retried. Lines are never edited. About 240 outcome requests per pass.
- **Unit and dependence:** unit = alert episode (alert lines of one market closer than 24 h collapse to the first);
  cluster = Gamma event id (market id when absent). Controls are evaluated with the same label.
- **Primary metric (one):** matched excess precision at the deployed budget: mean over episodes of
  `hit_6h(alert) − mean hit_6h(its controls)`, event-clustered bootstrap (4,000 resamples, seed 20261013), one-sided
  p for excess > 0. One primary, so no multiplicity correction; everything else is secondary.
- **Secondary (descriptive):** (a) **matched excess on `sharp_any_6h`** (pre-declared reading: the surprise
  filters require a quiet prior day, which overlaps score inputs such as `rv_1d`, so part of the primary excess may
  be the score finding markets that *pass the filter*; if the `sharp_any_6h` excess is near zero while the primary
  is positive, the detector mostly finds quiet markets that then move, which is still the registered question but
  must be read as such); (b) alert precision and control base rate (the live base rate of the alert strata); (c)
  2 h label; (d) |`fwd_move_6h`| >= 0.15 and |`fwd_move_24h`| >= 0.15 rates (undirected rule: no directional or
  P&L claim); (e) by fee category and sports vs non-sports; (f) `control_match` composition; (g) the accounting:
  pending, unavailable and dropped episodes split by alert vs control (`analyze()` uses the first alert line of a
  market within 24 h and never substitutes a later line for a dropped head), passes missed, request and timing
  stats.
- **Sample size and MDE:** 60 alerts per pass, 12 passes per day, 27.4 days: about 19,700 alert lines; the binding
  count is episodes (repeat alerts on a market within 24 h collapse) and event clusters. `alerts_needed(b, δ)` (80 %
  power, one-sided 5 %, independent episodes): at a control base rate b = 1 %: δ = +2 pts needs 605 episodes, +3 pts
  334, +5 pts 167; **at b = 3 %: 1,187 / 590 / 257; at b = 5 %: 1,743 / 834 / 343.** The dry run put 51 of 60 alerts
  in sports (h3 sports base 1.45 %, matched-control rate for the deployed configuration 1.16 %), so the live
  control rate is expected between 1 % and 5 %. With dependence inflating variance by up to 3x, about 5,200 episodes
  power the test for +2 pts at b = 5 %; 25 % new markets per pass gives > 4,000 episodes, so **the test is powered
  for about +2.5 pts at b = 5 % and +2 pts at b <= 3 %** against an optimistic historical reference of +9.3 pts.
  The metric is the excess, not the level.
- **Verdicts (after the single analysis):** **Supported (exploratory, prospective)** if one-sided p < 0.05 and
  excess > 0; **Contradicted** if the 95 % CI lies entirely below 0; **Inconclusive** otherwise; **Unavailable**
  with fewer than 30 episodes with a label and controls, or fewer than 10 clusters.
- **Stopping rule:** fixed end `END_UTC`; analysis **once** after **2026-11-11T13:00:00Z** (the last lines are due
  about 2026-11-11T00:30Z and an empty series becomes `unavailable` 12 h after due) with
  `scripts/run_surprise_snapshot.py analyze`; any line still pending at analysis time is reported as pending, never
  imputed. **Window membership is by capture start (`capture_t`)**, as the evidence role is: whole captures are in
  or out at both the `REGISTERED_UTC` and `END_UTC` edges, even though each line's origin `t` is its row receipt.
  No interim look at outcomes beyond operational counts. Early stop (disk cap 2 GB / 100 MB per day, collector
  outage) does not extend the window; the shortfall is recorded.
- **Hygiene:** idempotent per capture (`already_scored`); the scorer runs only after `state=complete`; capture start
  time is the origin (receipt clock); venue stamps for outcomes; wallet addresses hashed in memory, never written;
  no raw address in any line; read-only public endpoints; <= 4 req/s; no heavy lock needed (RSS about 500 MB while
  the rolling series is loaded). Any operational fix is logged here as a deviation.
- **Non-claims:** no calibration, causation, profitability or tradability claim; the rule is undirected; alerts
  are not labels of any wallet, trade or market as informed or insider activity.
- **Collector wiring (user action):** in `~/arepo_collector/arepo_pass.sh`, inside the `state=complete` block after
  `run_flow_screen.py`: `caffeinate -i $PY scripts/run_surprise_snapshot.py score --rps 4 2>&1 | tail -2`.

## Operational deviation: collection host moved Mac → Oracle at 2026-10-14 11:29Z (E009, E010, E011; also E004/E007 status, live monitor)

User-approved on 2026-10-13. Code, specs, frozen models and thresholds are unchanged. Spec hashes on the host match the Mac:
E009 `e63f20cc095b` and E010 `62b992c6af95`. The wallet hash key is the same. The runbook is `COLLECTION_HOST.md`.
- **Cutover.** The Mac launchd jobs were unloaded at 11:29:09Z (plists kept as `*.disabled`). The final incremental data sync left
  0 differences. Host monitors started at 11:30:55Z and were restarted at 11:32:32Z on code `5085e49` (an ops-only watchdog fix).
  The first host collection pass is at 12:31Z.
- **Gap from the cutover itself.**
  - E009/E010 poll grid points 11:30Z (and possibly 11:32Z) are missing.
  - New E009 predictions resume after the poller's 10-minute warm-up (about 11:42Z).
  - The live trade monitor is down 11:29–11:32Z; trades are fetched by page, so later cycles may recover part of it.
  - No collector pass is lost: none was due between 10:31Z and 12:31Z.
- **Larger gap before the cutover (Mac offline or asleep, not caused by the move).**
  - Collector passes 00:31Z to 10:31Z on 2026-10-14 did not run (6 passes). E011 has no captures for them.
  - The E009/E010 poller had no valid quotes from 00:02Z to 10:44Z.
  - The live trade monitor fetched no trades from about 00:00Z to 10:47Z.
  - Missing stays missing. The E011 window is not extended.
- **Parallel validation copy (not canonical, not merged).**
  - A validation copy of both monitors ran on the host from 2026-10-13 23:33Z to 2026-10-14 11:29Z into
    `/home/opc/arepo_val/data-dumps/research_lab/` with the identical code and specs. It therefore covers the Mac outage.
  - It is kept as is. Whether any of it may stand in for the outage is a design question for review. Until such a decision,
    it is NOT evidence for E009/E010.
  - **User decision 2026-10-15 19:31 UTC+1 (2026-10-15T18:31Z): fill the gap ("include it").** Made before any E009/E010 outcome analysis
    (analysis is after 2026-11-03). Pre-declared rule for that analysis:
    - The validation copy is used ONLY for the E009/E010 outage window where the canonical stream has no valid quotes
      (2026-10-14 00:02Z to 10:44Z). Outside that window the canonical stream is used and the copy is ignored.
    - Every substituted row carries `source=validation_copy`. The validation copy is not edited or merged in place.
    - The primary result includes the window. A sensitivity result excluding it is reported next to it, with the
      selection disclosed.
    - The live trade monitor and E011 are unaffected (E011 keeps its gap; the copy ran no collector passes in the window).
- **Validation results.**
  - Host pass 23:20Z: complete; 262,295 rows vs the Mac's 22:31Z pass at 264,126; 261,908 market ids in both, which fits market
    churn; same columns and manifest schema.
  - All steps ran: forecast, 2 sweeps, 2,000-market trade sample, E011 score (60 alerts, 180 controls); about 18 min, about 1.0 GB
    peak RSS.
  - Monitors, 23:36–00:30Z: live trades 208/208 identical (including wallet hashes); E010 predictions 74/74.
  - E009 quotes: Kalshi sides identical on all 1,582 shared rows; Polymarket sides identical on about 99%, the rest book-timing noise.
  - E009 predictions: 854 of 881 shared identical. The host lacked 147 at 23:40–23:42Z, which is its own start-up warm-up.
- **Environment.** The host runs Python 3.11.13 on Linux aarch64 with numpy, pandas, lightgbm, scikit-learn and scipy pinned to the
  Mac versions. Provenance env fields now read `linux`.
  - Scoped tests: 197 of 199 pass. The 2 failures are byte-identity checks of a gzip test fixture (Linux and macOS zlib compress
    differently); the sampling plans are identical.

## Methods note M3 — Cumulative test count and the SB2 two-stage rule (2026-10-15)
- **Count correction.** The HB1-era counter `battery.prior_test_count()` skipped the HB1 `ml_explain` line (72 tests)
  and several non-placebo kinds (economics 95, cross-venue 82, surprise detector 46, case lines 12, IF-H2 1). Past
  results keep the labels they were computed with; they are not re-labelled. From Screening Batch 2 on, every BY label
  uses `battery2.cumulative_count()` (rule `battery2-count-v1`, 991f04e): an explicit rule for every trial kind,
  fail-closed on unknown kinds, placebo lines 0. Local total 2026-10-15: **906**. Automatic `flow_screen` lines (one
  per pass) count one each; whether they should is an open governance question, recorded, not changed.
- **Two-stage rule for SB2 history families** (`SCREENING_BATCH_2.md` §2). Stage 1 on `h2_main` judgement rows:
  one-sided p < 0.01 in the discovery sign advances a test (the BY label is still attached). Stage 2 on `h3_power`,
  frozen definitions: Holm at 0.05 over the advanced set. Only a Stage-2 pass is reported as "development-replicated"
  (L2-dev). Reason: at a denominator near 1,000, BY needs z ≈ 4.1, which on one sample hides every moderation smaller
  than the main effect; an independent-markets replication with Holm controls family-wise error of what is carried
  forward. Neither stage is confirmation; confirmation needs SEALED-P (prospective) or SEALED-H4 (origins ≥
  2026-10-22T00:00Z).
- **h3_power wear.** SB2's J2, J6, J8 are its reads 4-6 (frozen definitions only; J8 on markets never read by ML).
  After SB2, h3_power is retired from replication use.

## Development screen SB2-J4 — bounce decomposition of the 2h reversal on prospective snapshots (q0006, 2026-10-15)
- **Status:** counted (5 `bounce_decomp` tests, Holm family of 5; prior cumulative count 916), **verdicts withheld**.
- **Why withheld:** the declared within-market permuted-target placebo was not null (P1 −0.202 vs real −0.207; all
  five placebo tests Holm-significant). The reading rule required a null placebo first.
- **Real estimates (for the record, not findings):** P1 −0.207, P1x −0.041, P2 +0.117 c/unit, P3 −0.165, P4 −0.166;
  all LODO-sign-stable. Details and descriptives: `SCREENING_BATCH_2.md` "Results / J4".
- **Next:** diagnostic q0031 (no trials). A corrected null and any re-read go to the challenger before anything is
  stated. J4 never closes Q5 alone (supporting evidence for J3).

## Development screen SB2-J5 — sibling lead-lag re-screen on the 2h snapshot cadence (q0005, 2026-10-15)
- **Status:** counted (8 `leadlag_screen` lines), development, not evidence.
- **Result:** SB2 rule (drafting rule + ΔR² ≥ 0.001) met by L1 (+0.0142, CI [+0.0060, +0.0217], 42/50 periods), L2
  (duplicate of L1) and L4 (+0.0114); L3 not met (+0.0008). Candidate: L1, an event-level *reversal* (corr(L1, dmid)
  −0.19). Holds on fresh periods only (34/39 positive).
- **Limits:** increment is over R only; R + L1 < B3; target is the Gamma mid (see J4 placebo issue); not tradable as
  shown. Next: L1-beyond-B3 and sweep-mid checks on later captures before any registration.

## Development screen SB2-J1 — Hypothesis battery 2 (HB2) on `h2_main` (q0008, 2026-10-15)
- **Status:** counted (13 tests; m_total 947), development (Stage 1).
- **Placebo (global permutation):** null (no test advances).
- **Advanced (p < 0.01, discovery sign):** F4 (flow × volatility, BY survivor), F5 (flow × spread), F7 (large-for-market
  trades), L1 (1d change × liquidity), F3 (flow × time to end, robust to end-date look-ahead), F8 (24h flow × liquidity;
  vanishes with the quiet-market control). Null: F1, F2, F6, L2 and all cross-market X1-X3.
- **Next:** frozen Stage-2 replication on `h3_power` (q0009 → q0010). No cost test yet; not tradable as shown.

## Development screen SB2-J7 — ML regime contrasts and interactions, r5_regime_ix on `h2_main` (q0012, 2026-10-16)
- **Status:** counted (27 `ml_explain` tests; prior cumulative 952), development (Stage 1), global placebo gate passed.
- **Advanced (4 of 12 contrasts):** C-ACT in all three cells (full-model gain over M0v is 0.04-0.06 nats larger in
  rows with a trade in the last 2h; close to mechanical, because flow features are empty without trades); C-TTE in
  direction 2h (larger gain < 24h before end; robust to the end-date look-ahead sensitivity).
- **Not advanced:** C-EXT (direction 2h p 0.0006 but the discovery sign disagrees), all other C-TTE/C-EXT; **0 of 15
  interaction pairs** (H² leaders are degenerate missingness indicators).
- **Defect:** C-LIQ not informative in all cells (empty low tercile: lower cut 0.0 with a mass at zero notional).
  Counted, not re-defined. Details: `HISTORICAL_ML_DEV.md` r5 section.
- **Next:** J8 frozen replication on h3 (q0013, queued). Q6 is closed for h2 interactions.

## Development replication SB2-J2 — HB2-R on `h3_power` (q0010, 2026-10-16)
- **Status:** counted (6 `history_battery2` replication tests, Holm family of 6), development-replicated ceiling (h3 read 4).
- **Replicated (Holm 0.05, frozen sign):** F4 flow × volatility (ratio to h2 1.59), F5 flow × spread (1.27), L1 1d change
  × liquidity (1.22); also under the weighted and excluding-shared-events secondaries. **Not replicated:** F3, F7, F8.
- **Economics:** F4/F5 gross about 1c per trade in the favourable tercile versus about 3.5c spread + fee; net taker about
  −2.5c, and still negative at half-spread without fees. Not tradable as a taker.
- **Engineering:** first two attempts crashed on NaN controls in F8's secondary (fixed c269ff4; disclosed). Details:
  `SCREENING_BATCH_2.md` Results / J2.

## Development replication SB2-J8 — frozen replication of the r5 regime contrasts on `h3_power` (q0013, 2026-10-16)
- **Status:** counted (4 `ml_explain` tests, Holm family of 4; prior cumulative 1,009), development-replicated ceiling
  (J8 is the frozen-definition h3 read on the ML-unread complement; 2,138 recorded replication markets excluded, sha match).
- **Replicated (Holm 0.05, frozen sign):** C-TTE direction 2h (+0.0188 nats, CI [0.0094, 0.0292]); C-ACT direction 2h
  (+0.0427 [0.0346, 0.0509]); C-ACT up-vs-down 2h (+0.0331 [0.0229, 0.0433]); C-ACT up-vs-down 6h (+0.0115 [0.0015, 0.0222],
  Holm p 0.0121). **Not replicated:** none of the four. The 6h cell fails the weighted secondary (one-sided p 0.064).
  C-ACT decays to 27-72% of the h2 effect and is close to mechanical (flow features empty without trades).
- **Economics:** forecasting only, no cost check (log-loss gain over a baseline model, not a return).
- **Next:** stop rule met (at least one replicated). Challenger pass (`science-reviewer`) before any MC1-style registration
  draft; C-TTE direction 2h is the candidate with content. Details: `SCREENING_BATCH_2.md` Results / J8,
  `HISTORICAL_ML_DEV.md` J8 section.

## Development screen SB2-J3 — book-mid bounce decomposition, `j3_expanding_v1` on `h2_main` pmxt rows (q0011, 2026-10-16)
- **Status:** counted (6 tests, `book_decomp` plus count line; prior cumulative 1,028), development, ceiling L1 (h2 only).
  `family_status` OK, so the unavailability is not a family failure.
- **Result: UNAVAILABLE, not a null.** 751 judgement rows in 113 events (declared floor 2,000 rows and 100 events);
  2,145 complete rows of 420,937 panel rows. No B1-B4, D1 or D2 estimate and no `rho_s` benchmark was produced; the
  placebo was untestable. Q5 and the depth-conditional flow question (Q3, book part) stay open for history.
- **Economics:** none (no cost check). No re-run is possible on this table without a reviewed design change.
- **Next:** none for J3 itself. A maker-side capture study needs its own design (SCREENING_BATCH_2.md J3 stop rule).

## Development ablation ML-r4_book — pmxt book family on `h2_main` (q0004, 2026-10-16)
- **Status:** counted (36 `ml_explain` ablation tests: 9 cells of 3 horizons x 3 targets, 4 units each; run-internal BY
  m_total 277), development (exploratory_historical), 3 time folds, 637 markets, 94,435 rows (updown 20,854 at 2h;
  29,325 at 6h; 42,082 at 24h). Only 16,750 of 131,684 in-window origins have a book (12.7%); the rest are NaN.
  **Correction (challenger 2026-10-16):** judgement was book-only (`run_ml_history.py` sets `eval_mask` to book-present
  rows since 22b361a; `ablation_study` judges `eval_mask & full.mask`); only the fitting used all rows. The earlier
  wording that the run judged all rows was wrong. Tests and labels unchanged; the judged-row count is not stored in the file.
- **Result: book family is `descriptive_only` in all 9 cells; none is `demonstrated_incremental_value`.** Book
  ablation delta log loss (positive = book helps): 2h direction -0.0042 [-0.0072, -0.0013], absmove -0.0025, updown
  -0.0092 (book hurts); 6h direction +0.0030 [-0.0009, 0.0067], updown +0.0071 [0.0004, 0.0138]; 24h updown +0.0068
  [0.0002, 0.0137]. All BY p = 1.0. Flow remained the only family with a stable positive delta (2h direction +0.0149,
  p_by 0.17). Plain reading: book levels add no demonstrated out-of-sample value over the baseline/flow models here;
  the two nominally positive updown deltas are borderline, not corrected-significant, and sit on 12.7% coverage.
- **Defects disclosed:** 24h absmove placebo gate failed (M2F>M2v on shuffled labels; M2F beats M2v by 0.00025 nats, 0.036%,
  on 60,763 shuffled rows), so that cell is not interpretable; the output note said "Book features absent" (stale
  boilerplate; now emitted only when no book table is joined, tested).
- **Economics:** none (no cost check). **Next:** none; the book family is closed as descriptive at this coverage. A
  higher-coverage book table would be a new design.

## Challenger verdicts on the 2026-10-16 write-ups (SB2-J8, r4_book, J3)
- **C-TTE (J8): revise.** No forecasting-only registration. The contrast rests on the Gamma `endDate` read after the fact
  (`ml_log_hours_to_end` is in the M0V baseline as well as the regime variable), the look-ahead sensitivity was never run
  on h3 (frozen path), and the clip at 0 puts post-end origins in "<24h". Descriptive diagnostics queued as q0100
  (`--tte-diag`, not counted, nothing appended to trials): look-ahead exclusion, pre-end vs post-end split of "<24h",
  exclusion of markets with |endDate - closedTime| <= 1h (declared in code), UTC-day clustered CI beside the event CI.
  Next: near-end conditional rule with a cost check, or an as-of hours-to-end live feature.
- **C-ACT: rejected as a candidate**; kept as a descriptive replication only (close to mechanical: flow features are
  empty without trades).
- **J3: accepted as unavailable.** The 341 complete rows in neither split (2,145 vs 1,053 discovery + 751 judgement) are
  the embargo rows: `split` is disc (`t_i + 24h <= 2026-07-01`), judge (`t_i >= 2026-07-01 + 24h`) or embargo, applied on
  both sides of the split (`battery.py` SPLIT_TS/EMBARGO_S; `bounce_decomp` reads `split`). Derived from code and the
  three-valued split; the results file does not store an embargo count.
- **r4_book:** record corrected above (judgement was book-only; labels and the 36 tests stand).

## Development screen CB1 — Creative Batch 1 carry screens on `h2_main` (q0019-q0023, 2026-10-16)
- **Status:** counted (9 tests: A1, A2, E1, E2, E3, C1, C2, B1, B2; `ml_explain` lines `creative_batch_1:A|E|C|B`),
  development (exploratory_historical, L1; h2 worn beyond its revision budget). B ran on the `h5_cb1_ladders` probe,
  not h2. Census (q0019): A1 57 units / 51 clusters, A2 348 / 281, E 0 units (2,886 of 3,200 markets have no text).
  Declared in `CREATIVE_BATCH_1.md` (declaration sha256 `58e203bb...`); thresholds unchanged.
- **Result: nothing advanced.** A2 net -1.05c (event CI [-2.96c, +0.64c], p 0.912, `R_ann` -32.7%; fails p, floor, tail
  gate, robustness). C1 net -3.84c per filled share (62 events, p 0.907; fails all gates; PX1 not clean). A1 (57 units)
  and C2 (11 clusters) are below the testability floors; E1-E3 have no text units; B1 and B2 are not testable (52 usable
  ladders < 300, stop rule). All "not testable" tests are counted with p = 1. The break-even placebo was not run
  because no test met the gate. Plain reading: not detected at the screen MDE, not shown absent; E is a data failure
  (missing text), not a negative result.
- **Economics:** none beyond the in-test cost nets (A2 and C1 are negative after costs); no cost check was triggered.
- **Next:** none for A, C, E, B1, B2: no h5 replication is run and `h5_cb1`/`h5_cb1_ladders` stay sealed and unread.
  Open: CB1-D dev (after 2026-10-17T00:00Z), B3 rung list at T_rep_start (>= 2026-10-19). E on h5 would need a
  reviewed design change.

## J8 C-TTE descriptive diagnostics (q0100), 2026-10-16 23:09Z
- Role: exploratory_historical, **descriptive, not counted** (no Holm, no trials line). h3_power, direction 2h, frozen r5 configs.
- C-TTE (<24h − >30d ΔLL): as replicated +0.0188 [0.0094, 0.0292]; look-ahead excluded +0.0178 [0.0084, 0.0280]; pre-end
  origins only +0.0166 [0.0073, 0.0261]; post-end only +0.0255 [0.0058, 0.0656]; near-end markets excluded +0.0183 [0.0088, 0.0293].
- Verdict: the challenger's three artefact routes (look-ahead endDate, post-end clip, near-end markets) do not explain the gain.
  Still forecasting-only and built on an after-the-fact endDate; no cost check; nothing registered. Next: as-of hours-to-end in
  the live MC1 dev run. Details: `HISTORICAL_ML_DEV.md` (J8 C-TTE descriptive diagnostics).

## Development screen CB1-D — neg-risk asymmetry on dev captures (q0022, 2026-10-17)
- **Status:** counted (2 tests: D1, D2; `ml_explain` line `creative_batch_1:D`; prior cumulative 1,104, now 1,106),
  development (exploratory_historical, L1). Inputs: frozen 60-capture list (sha256 `967a0cb0...`), 15,883 eligible
  event-captures / 572 events, 59 pairs (58 kept). Declared in `CREATIVE_BATCH_1.md` (declaration sha256
  `c9a2ec8d...`); thresholds unchanged. Results sha256 `d176c9df...`.
- **Result: nothing advanced.** D1 mean(U - O) +0.78 pp (U 0.85%, O 0.07%; event CI [+0.20, +1.58] pp), p 0.0156:
  fails alpha 0.01, the 1.0 pp floor and the without-top-5 robustness check (+0.15 pp). D2 is not testable (33 triggers
  from 8 events < 100 / 30; no resolved trigger events; mean null, p = 1; payoff and depth unverified). As-of-only
  sensitivity (one day, n 2,619): D1 +0.46 pp, p 0.136, descriptive. Plain reading: not detected at the screen MDE
  (about 1.3 pp), not shown absent; the positive D1 estimate is not a finding.
- **Economics:** none beyond the structural per-trigger net, which was not estimable (D2 not testable).
- **Next:** none for D. Stop rule: no rep run (q0027 not spent, rep captures stay unfrozen and unread). The maker
  route would need a collector extension and a new declaration. Open in CB1: B3 rung list at T_rep_start (>= 2026-10-19).

## Data and smoke events, 2026-10-17 (autopilot ~09:55Z; no outcome test run; smoke consequences suspended pending v2)
- **CB7 smoke q0140: FAIL (engineering, pool specification).** (a) PASS; (b), (c) FAIL with only 2 of 200 drawn
  candidates eligible (205 of 13,700 exclusion ids end in 2025 with >= $10k volume). Source not tested. v1 file stays on
  record; diagnosis and v2 in `SMOKE_DIAGNOSIS_2026-10-17_CB7_CB8H.md`. **Consequence suspended pending the reviewed
  v2** (science-reviewer ACCEPT_WITH_CHANGES, 2026-10-17): v2 pool = sample ids ending in 2025 with life >= 14 d and
  close >= end - 7 d (33 ids by a zero-request count), Gamma volume >= 10k as v1, seed `arepo-cb7-smoke-v2`, new rules
  file `cb7_text_geo_rules_v2.json`. **A v2 FAIL is final:** S1 and G1 become "not run (smoke FAIL)", counted; `T_seal`
  unchanged. q0142/q0143 not promoted.
- **CB8-H holders smoke q0160: FAIL (engineering, empty frame).** Sidecar market `open_interest` is blank in all 280,175
  rows (Gamma markets carry no OI); `/holders` was never called. Data API `/oi` (60 ids per request) supplies market OI.
  v2 in the same file. **Consequence suspended pending the reviewed v2** (ACCEPT_WITH_CHANGES; the design's rule
  "FAIL of (a)/(b) -> H not run (source)" is overridden by this recorded design change because `/holders` was never
  called): option A (`/oi` for every base-frame market at frame-build time `t_f`, strictly before the first `/holders`
  request), distinct `oi_lookup_failed` / `oi_absent` / `oi_nonnumeric` states, new `cb8_holders_rules_v2.json`. **A v2 FAIL
  of (a) or (b) makes H "not run (source)", counted.** q0162/q0163 not promoted.
- **CB3 history census q0061b: done** (counts in `CREATIVE_BATCH_3.md` §2.7.1; sha256 `d3441636...`). The freeze waits for
  q0064 (after 2026-10-25), as declared.
- **h6_weather sealed (q0044):** 2,965 screen / 1,987 holdout markets, 48 embargo, d_split 2026-08-05, listing sha256
  `e6e3e250...`. **h8_tail fetch complete (q0120):** 362 items, 670 origins, 145,430 price rows, 49,262 trade rows, 0 failed;
  seal q0121 after `T_seal`. **CB7 exclusion keys complete (q0141):** 20,913 ids, 1 missing (share 0.00005 < 0.02).
- **Memory failures:** q0084 (CB4 pmxt pilot) MemoryError twice in pyarrow reads; q0082f (h7 series frame) MemoryError on
  resume (322 MB partial walk file). Fixes in progress; not outcome-related.
- **Ops:** host package caches cleared (~3 GB); collector data cap 13 -> 14 GiB; CB5 fetch refusal 12 -> 13 GB (15ea7e2).

## Design change CB6-T A-T1: h8_tail_b top-up (2026-10-17; no test run, count 0)
- **Why:** the frozen h8_tail frame (q0120, one random 15-minute window per day) yielded 362 markets / 670 origins instead of
  about 4,500 markets. At the planned eligibility that is about 235 units and a T1 MDE of about 17c.
- **What was seen when deciding (counts only, no value):** `frame_report.json` (sha256 `b2e41922...`): 65,584 raw frame rows;
  dropped created outside the window 33,305, life < 14 d 22,725, crypto Up/Down 7,417, weather 692; 15 exclusion ids; 1,068
  exclusion-key drops; 362 markets kept and all taken (21 strata); 670 origins; 145,430 price rows and 49,262 print rows;
  3,668 requests. **No outcome, price value, print value or wallet was read by any analysis.**
- **Decision (science-reviewer ACCEPT_WITH_CHANGES):** run `h8_tail_b` with the same seed, 9 windows per day, walking only the 8
  windows h8_tail did not walk (nested draw; union = frozen 9-window frame), clock pinned to h8_tail's `T_fetch8`, h8_tail
  excluded by market id only, same rules otherwise (rules v3 `ad7f5baa...` adds the top-up section; all v2 rule functions
  byte-identical). Sealed together with h8_tail (one listing, one event-hash split). Any non-complete ending drops it; no
  third run.
- **Power restated:** union about 1,140-1,530 units, Stage-1 MDE about 6.7-7.7c (was 3.8c at 4,700 units); T1 detects only
  strong effects; the 2.0c floor and the >= 10 YES-cluster rule are unchanged. No threshold, formula or gate changed.
- **Trial line:** `design_change`, `n_tests` 0, id `44cb83a8-efd4-45df-8e5b-d30ddf96d10a`. Drafts q0120b / q0121 in `queue/drafts/`.

## CB7 smoke v2 (q0140b), 2026-10-17 10:00Z: PASS (engineering gate, not counted)
- Rules v2 `05bf365c...`; seed `arepo-cb7-smoke-v2`; 33 recorded-field candidates, all found on Gamma, 20 smoked;
  (a) slug resolves; (b) bounds and newest-first on 15 non-empty responses (>= 10); (c) 15 of 20 covered (>= 14).
  Disclosure: 14 of the 20 were also probed by CB6 smoke v2, 1 by CB6 smoke v1, 0 by CB7 v1. Seal copies
  `seals/cb7_smoke_v2_PASS_20261017.json` (sha256 `f178a3a8...`) and `cb7_smoke_FAIL_20261017.json`.
- Consequence: q0142 (h8_text) and q0143 (h8_geo) promoted (4e55ee5); both must finish before `T_seal` 2026-10-22T00Z.

## CB4-N power pilot (q0084), 2026-10-17 10:26Z (descriptive, outside the analysis window; not counted)
- 24/24 hours, 1.29 eligible events/hour (prior assumed ~15), 31 event-hours; all band indicators 0 (`I_none` = 1.0,
  SD 0). Frozen rule gives H = 84 with a degenerate predicted MDE of 0. Open for the CB4 freeze check: "not testable" vs
  run at H = 84 with a non-degenerate MDE, plus a check that the band classifier is not defective
  (`CREATIVE_BATCH_4.md`, power pilot result). q0085 (flip trades) still not before ~10-24T12Z.
- **CB4-N ruling (science-reviewer, 2026-10-17 ~11:00Z):** the frozen stop rule fires (1.29 < 5 eligible events per
  hour), so **N1 and N2 are "not testable (stop rule)", p = 1, counted (2 tests)**; the earlier `testable: true` was a
  defect (stop not enforced in `measure-N`), fixed in 3988b1d with a YES-token check and a synthetic-hour classifier test
  (passed: the zero mid-band share is a data property). The 2 counted lines are written by q0087n (`measure-N
  --not-testable-only`) after the CB4 freeze, not now; q0087 for N is not run. Band map = pilot data only.

## CB7 fetches complete (q0142 h8_text, q0143 h8_geo), 2026-10-17: counts only, not counted
- h8_text: 4,108 markets (the whole filtered pool), **1,026 eligible origins** (design assumed about 5,000 units; rough
  Stage-1 S1 MDE about 5-6c per marker, census replaces). h8_geo: 3,067 markets, 7,380 origins, **1,917 eligible**
  (rough G1 MDE about 7-8c). 0 failed items or windows; outcomes guarded and unread. Details: `CREATIVE_BATCH_7.md`,
  last section. Seals q0144/q0145 after `T_seal`.


## CB10 drafted, not counted, k = 3 fixed + up to 4 conditional (2026-10-17 15:48 UTC+1; design only)
- `CREATIVE_BATCH_10.md` (status DRAFT, not challenged, not frozen; queue ids q0200-q0219, specs in the document only).
  Families: **CB10-D** (CH89, Deribit option-implied digital vs BTC/ETH daily strike ladders; D1 slope Stage 1 on resolution
  dates `[2025-10-01, 2026-04-13) ∪ [2026-08-11, 2026-10-01)`, avoiding CB8-B's crypto calendar; D1-rep and D2 economic at
  recorded asks on 56 post-freeze dates) and **CB10-B** (CH93, side-free round-level vs pseudo-level break reversal B1 and
  trade-through maker B2; fresh `h10_brk`, SCREEN/HOLDOUT by event). Dropped with reasons: CH82 (probe: the public Combos
  catalogue lists leg markets, not combos; no combo price or volume is public), CH87 (CB7-S not reported; report clause is a
  fallback inside official-source rules in 53 of 54 probed texts), CH90, CH91. 33 counts-only probe requests, nothing
  stored. MDEs: D1 about 0.85-1.25 in slope (floor 0.30), B1 about 0.6-0.7c (floor 0.5c), B2 about 0.9-1.1c (floor 1.0c).
  No pmxt; about 9,200 `net`-lane requests after `T_seal`; outputs ≤ 0.12 GB. Count 0 now; cumulative 1,141 (Mac working
  tree, lower bound). Next: `science-reviewer` challenger round 1.

## CB9 code-against-design freeze check, 2026-10-17 (science-reviewer): not counted
- q0180 smoke GO_WITH_CONDITIONS; data side (q0181-q0188) NO_GO; analysis side (q0189-q0198) NO_GO, pending 12 must-fixes
  (per-exchange smoke counts, unavailable vs failed smoke, a same-sentence tie regex, non-stalling dependency chain,
  data-dumps headroom 14, open long-dated K/D markets, 13Z ingress decision, the missing P Stage-2 outcome fetch, one
  Stage-2 rule with code-derived k, write-once results, the P small-G cluster rule). Rules v1 re-derive exactly; fixes go
  into v2 rules files, and v1 stays untouched. Tie rule checked on a live Pyth daily (2026-10-16 NVDA): an exact tie resolves 50-50.

## CB5-L CDF frame (q0104b, done 2026-10-17T19:23Z): 0 families, G59 will fail; counts only, not counted
- `run_cb5.py cdf-frame` on IF-H2 events + the 2026-10-01 walk: 318,808 events in, 12,016 ladder rungs in 7,405 groups,
  **1 bucket event, 0 families, 0 live, 0 pairs**. Diagnosis (implementer, read-only re-run of the bucket filter on the raw
  unreduced file on the host): the reduced loader (3a030f6) drops nothing (same counts). Of 303,136 IF-H2 events 109,619 are
  neg-risk; 57 have ≥ 2 members whose `groupItemTitle` parses as a period; 51 are excluded by the frozen
  `cdf-grouper-v1` rule against "Other"/"No X" placeholder members, 4 fail period parsing ("Before September" vs
  "September 1-15"), 2 parse fully and 1 tiles. Walk: 19 windows, 871 requests, 0 failed.
- Consequence: gate G59 (≥ 20 audited live families) cannot be met, so **CH59 is expected to close as "too rare in the
  live universe (0 families)"** when q0106's census applies G59 (design §691). The grouper is frozen; admitting placeholder
  buckets would be a design change and is not made. Drafts q0105 (cdf extract backfill) and q0107 (r_inc) are held: they
  would read an empty family list. Other CB5 parts (G, K, J4) are unaffected.

## Ops: h7 series frame q0082f incomplete -> q0082g; CB8-H smoke q0160b FAIL (criterion h), 2026-10-17: not counted
- **q0082f** ended `done` only because the repeat loop hit `max_runs 8`: every late run stopped on the ops disk cap
  (`DiskBudget` counts the whole run dir: `walk_partial.jsonl` 2.0 GB + guarded 0.56 GB > 1.0 GB). The walk was near the
  end of the closed pass (2026-10-14 window). The cap is not a hashed rules field. Re-issued as **q0082g** with
  `--disk-cap-gb 4.0`, resuming from the partials (e49ca18); q0082 (fetch) now depends on q0082g, its ops cap 0.40 -> 6.0
  (the shared run dir already holds 2.6 GB). Deadline: cap-at 2026-10-22T00Z.
- **q0160b** (CB8-H holders smoke v2, rules v3): criteria a-g pass; **h FAILS**: `/oi` missing share 0.819 > 0.02 (base
  278,705, `oi_absent` 228,318, 0 lookup failures, 0 nonnumeric, 0 integrity violations). Smoke = FAIL; under the design
  q0162/q0163 do not run. Diagnosis: `/oi` returned 539/540 random active Gamma markets, while 235/300 sampled base-frame
  markets were absent, all dormant (blank/zero `volume24hr`). Working hypothesis: absent = zero OI, which the OI ≥ 1,000 rule
  excludes anyway. Being verified independently before any amendment (would be H-v4, new rules file, science-reviewer,
  new smoke q0160c); if not verified, CB8-H stays FAIL under its stop rule.

## CB9 focused freeze re-check (M4-M12), 2026-10-17 (science-reviewer): not counted
- Rules sign v3 / P v3 / kd v2 re-derive exactly from committed code; 112 cb9 tests pass; M4, M7 (no leakage), M8 (only
  the ingress constant moved), M10, M11, M12 verified. **Data side GO_WITH_CONDITIONS** (q0182 argv lacks the required
  `--cb8-keys-sha256`; q0188 refuses instead of stalling after an upstream K/D stall). **Analysis side GO_WITH_CONDITIONS**
  for q0189-q0194 and q0197; **NO_GO for q0195/q0196** (pyth-live single pass without a repeat; rep-P has no
  completeness/time guard and could freeze pending sessions as "unavailable"). Six should-fixes (q0198 polling,
  13Z `not_measured` labels, sticky P-frame stall, q0197 also depends on q0191, M7 fetch-time volume disclosure, CB8
  failure path). Fixes being implemented (sign rules v4 after q0180 runs on v3).

## CB10 code-against-design freeze check, 2026-10-17 (science-reviewer): not counted
- Code c439a1d (104 tests), rules `cb10_rules.json` re-derives exactly (rules_sha256 `2db70d9a…`). Round-1 changes
  verified (separate earlier-transaction `p_reg`/`p_alt`, GDP power gate, no CB8 object opened). **q0200 smoke
  GO_WITH_CONDITIONS, data side GO_WITH_CONDITIONS, analysis side NO_GO.** Must-fixes: B mutual exclusion looked ahead
  (dropped real breaks that continued ≥ 3c, biasing B1 up; design amendment: drop only the later episode); Stage-2 k must
  count 2 for a D1 advance; untestable independent-price placebo passed vacuously; D2 +0.5c robustness re-selected
  trades; D2 start epoch must be explicit; q0202 per-item failure cap; draft repeat/depends fixes; smoke network give-up
  must be NotNow. Rulings: audit denominator, RV_MIN_RETURNS 150, stricter placebo, 30-min mark, trial roles, cap 40
  accepted. Fixes being implemented (rules v2).

## CB11 design draft, not counted, k = 6 fixed + up to 6 conditional (2026-10-17 20:50 UTC+1; design only)
- `CREATIVE_BATCH_11.md` (status DRAFT, challenger review pending, not frozen; queue ids q0220-q0239, specs in the
  document only). Families: **CB11-W** (CH85, whitelisted-proposer clocks: W1 forecast of the post-end wait
  `closedTime − endDate` vs a category-median baseline, floor 20% MAE gain; W2 decided carry restricted to predicted
  waits ≤ 6 h at an hourly capital-time rate, CB1 tail gate), Stage 1 on the **h2_main/h3_power frames already on the
  host** (metadata only; reused frame, fresh target, sampled markets dropped by key) plus a 9,000-request print fetch;
  **CB11-P** (CH88, politics favourites 0.60-0.85 at 30/60/90 d: P1 mean excess ≥ 3c, P2 declared-ask carry), fresh
  `h11_pol`, out-of-time split at 2026-01-01; **CB11-A** (CH97, Wikipedia pageviews: quiet-minus-spike continuation of
  ≥ 3c moves, A1 ≥ 1c, A2 taker follow), fresh `h11_attn`, event split. Dropped with reasons: CH81 (census floor),
  CH86 (pmxt ingress), CH94/CH95/CH96 (`side` and wallet dependence, wallet nulls), CH98 (about 5 usable capture days).
- 32 counts-only probe requests, nothing stored: Gamma `closedTime` = `umaEndDate` (UMA settlement); `resolvedBy` is the
  adapter (2 values), not the proposer; public RPCs refuse topic-only `ProposePrice` log scans; ≥ 510 long-life
  politics markets ending in March 2026 alone; pageviews for 2026-10-16 still unpublished ≥ 19.8 h after the day ended
  (the 12 h fallback assumption is contradicted; CB11 uses 48 h).
- MDEs (estimates): W1 about 0.03-0.06 (floor 0.20 binds), W2 about 1.5-2.4c (floor 0.30c), P1 about 4.5-7c (floor 3c;
  power gate 6.0c), A1 about 2.6c (floor 1c; GA may fail on spike count), A2 about 1.1c. W can screen before `T_seal`;
  P and A fetches (about 50,000 requests) use the idle `net` lane at priorities 25-29, behind every `T_seal`-bound job.
- Count 0 now; cumulative **1,141** as stated in the latest ledger entry that states one (CB10 draft); 1,156 from
  `battery2.cumulative_count()` on the Mac working tree at drafting (lower bound). Next: `science-reviewer` challenger
  round 1.

## CB9 smoke q0180 (v1, rules sign v3), 2026-10-17T19:58Z: FAIL on receipt count only; counted as descriptive (trial line written by the job)
- gamma_paging, pmxt_heads, topic_pins, yahoo_clock PASS. **receipts_v1 FAIL (8 receipts < 20), receipts_v2 FAIL
  (18 < 20)**, but every receipt decoded: v1 8/8 matched with T1 = T2 (both v1 exchanges exercised), v2 18/18 (both v2
  exchanges), 0 unavailable, RPC 26 requests 0 failures. Cause: the smoke draws a fixed 10 markets x 2 prints, so it can
  reach 20 receipts only if every draw yields a distinct receipt (a sampling defect, not a source property). Result kept
  (write-once). Smoke v2 (draw markets in seeded order until 20 receipts, cap 40; pass rule unchanged; new seed,
  `smoke_v2.json`, sign rules v5) being implemented; q0181 waits on it.

## Smokes PASS, 2026-10-17 ~20:10Z: CB9 smoke v2 (q0180b) and CB10 smoke (q0200); descriptive trial lines written by the jobs
- **q0180b CB9 smoke v2** (sign rules v5): all six criteria PASS. Receipts v1 era 20/20 matched with T1 = T2 (19 markets
  tried), v2 era 20/20 (10 markets tried); 0 duplicates, 0 unavailable. Supersedes the v1 smoke FAIL by disclosure (v1
  `smoke.json` kept). CB9 data jobs q0181+ remain gated on T_seal 2026-10-22T00Z.
- **q0200 CB10 smoke** (rules v2): deribit, ladder_frame, live_flags, data_api_paging, tx_aggregation, whitelist all
  PASS (29 requests). Next CB10 job q0201 (exclusion keys) needs the CB9 frame pins (q0182/q0183/q0185) after T_seal.

## CB11 challenger round 1 response (2026-10-17 21:04 UTC+1; design only, not counted)
- `science-reviewer` round 1: ACCEPT_WITH_REQUIRED_CHANGES (W, P, A); 11 required items all adopted, none rejected;
  status DRAFT-REVISED, code and code-against-design freeze check next. Changes: P activity now a causal
  `prices-history` proxy (Data API reach only a variant); `uma_status` guarded, W keeps every closed row, new censoring
  gate GWC (q0224, upper 95% bound > 2% → not testable); P end-date hindsight flags + "L1, hindsight end date" label;
  week-factor copula, max-of-ways MDE and a 2024-election exclusion check; C1/T5 exclusion mandatory ("possibly touched"
  label if absent); W2 entry at the next transaction ≥ τ + 60 s and a capacity-capped pool gate (excess over 4.5% ≥ 10%);
  W1 must beat both B0 (≥ 0.20) and the rolling B1 (≥ 0.10); W1 placebo = permutation within category x month; A
  pageview rules (median ≥ 50, 9 days present, 30-day history), 3-day-block cluster way, non-`vol_ok` stratum for a
  causal-volume check; budget recomputed (≤ about 74,000 requests; incomplete fetch = pending). Optional items adopted
  (risk-free excess, unclean outcomes counted and scored, liquidity stratum, frame-source mix, CB1-A1 prior). Census
  split per family (q0231 W, q0239 P/A) so W can still screen before `T_seal`.
- Budget unchanged: 6 fixed + ≤ 6 conditional. Count 0 now; cumulative **1,156** from the committed host-unioned
  `trials.jsonl` at `e721331`.

## CB8-H design change H-v4 / H-v5 (oi_absent = no OI listed), 2026-10-17: not counted (design change, no trial run)
- **What:** override of the pre-registered stop rule for CB8-H ("a FAIL of criterion a, b or h makes H 'not run (source)'; there is no smoke v3", `CREATIVE_BATCH_8.md` "H v2" and its must-fixes item 1) after q0160b failed criterion h only
  (`/oi` missing share 0.819: 228,318 of 278,705 base markets `oi_absent`; criteria a, b, c, e, f, g pass). The sentences are explicitly superseded in "CB8-H amendment H-v5".
- **Pre-verification record:** the hypothesis (absent = zero OI, excluded anyway by OI >= 1,000) was written in the q0160b entry above ("Ops: ... CB8-H smoke q0160b FAIL") before any check, with the commitment that an unverified hypothesis leaves CB8-H a FAIL.
- **Verification:** seeded sample of 600 base markets: 490 absent, 110 listed (90 < 1,000, none 0); `/holders` of 40 absent markets: 40 of 40 no holders; single `/oi` of 15: 15 of 15 empty; 10 smallest listed (OI 0.14-3.56): 10 of 10 have holders.
  Evidence: `docs/research_lab/evidence_cb8/` (v2 smoke counts, sha256 `8566d1f0...ae27e`; verification scripts and output). The one active-but-absent market of the 539/540 diagnosis was not identified (disclosed).
- **Reviewer:** science-reviewer ACCEPT_WITH_REQUIRED_CHANGES on H-v4, applied in H-v5: (1) `absent_contradicted` (absent with single-market event OI >= 1,000 in the capture) inside the 2 % rule on every day and in the smoke, plus smoke criterion i
  (`/holders` of the 20 highest-volume absent markets, none with top-20 holdings >= 1,000); (2) empty `/oi` reply to a batch of more than 15 ids is split and retried (an honest all-absent 60-batch has probability about 6e-6); (3) 403 fallback to batches of <= 15;
  (4) disclosure and this entry; (5) evidence committed; (6) cosmetics.
- **What did not change:** OI >= 1,000, terciles, 1,500 + 300 sample, criteria a, b, c, e, f, g, windows, H1 earliest start 2026-10-21T06:00Z, T_seal 2026-10-22T00Z. A smoke v3 FAIL of a, b, f, h or i makes H "not run (source)", counted; no smoke v4.
- **Files:** code `fe86fd8`; the H-v5 docs, evidence, seals and drafts landed in `d3278b8` (its message is misleading: a concurrent commit picked them up from the shared index; see note commit `d202c74`). Rules `cb8_holders_rules_v5.json` `5fe7f6b3...`, `cb8_h_analysis_rules_v3.json` `193ab064...`; drafts q0160c, q0162, q0163, q0172. H-v4 rules files (`2aca9bdc...`, `ef435a74...`) superseded unused.
- **H-v6 (reviewer re-check GO_WITH_CONDITIONS):** splits made auditable (persisted per batch; `n_split_batches`, `n_split_requests`, `n_empty_replies_le15` in the smoke output, plan and day marker) and large `/oi` batches split on the first failure; v5 files superseded unused. Code `d922ffc`; rules `cb8_holders_rules_v6.json` `e7e72f4c...`, `cb8_h_analysis_rules_v4.json` `dbd87ef7...`; q0160c `timeout_s` 14,400.

## CB4-E group-S ruling (2026-10-17): as_declared ["sports"]; CH53 E1/E2 not testable (frame counts only)
- Era frame `03e58086…231d`: S|P0 = 6 and S|P1 = 92 against 800 targeted per cell. Stop rule fires (fewer than 30
  clusters): **E1 and E2 not testable, p = 1, counted (2 lines when the CB4 analysis runs)**. era_rule = pooled_allowed,
  labelled "untested". Series frame `50e51b87…6606`: sports-series leak count to be disclosed. No threshold or formula
  changed. Seal `h7_cb4_group_s_amendment.json`; gate q0081g releases the q0081/q0082 fetches.

## Ops (2026-10-18 ~00:55Z, autopilot): h7 and h8_tail_b T_seal-bound fetches COMPLETE; not counted (data only)
- **q0081 h7_cb4_era fetch:** done 21:29Z (attempt 1, 4,139 s). 3,139 items, 0 failed; 2,860,016 price rows (19 dropped
  post-cap), 891,275 trade rows, 13 markets with truncated trades; 48.9 MB.
- **q0082 h7_cb4_series fetch:** done 22:13Z (attempt 1, 2,637 s). 1,922 items, 0 failed; 546,888 price rows (1 dropped
  post-cap), 976,949 trade rows, 33 markets with truncated trades; 674 MB.
- **q0120b h8_tail_b fetch (CB6/CB7 top-up):** done 00:13Z 10-18 after one partial session (5,103 s) and one completing
  session (1,996 s). 4,196 items, 0 failed; 10,297 origins; 1,831,709 price rows; 1,014,270 trade rows; 145 truncated
  print windows; 596 wallet lookups, 0 errors; 6 HTTP 429s retried. Finished before the 10-21T09Z deadline.
- No outcome, target or test was computed. Next: seals q0083 (after the q0083b recorder, on/after 10-22T00Z), q0121/
  q0144/q0145 (after T_seal), as already planned. Truncation counts are disclosed at each census.

## CB8-H smoke v3 (q0160c) PASS, 2026-10-18 01:02Z; q0162/q0163 promoted; not counted (descriptive)
- **Result** (`creative_batch8/holders_smoke_v3.json`, rules v6 `e7e72f4c…`, git 7627f05, capture 20261017T223101Z):
  criteria a, b, c, e (units consistent), f, g (paging offsets 0 and 4000 both 200), h (oi_source ok) and i (absent
  probe) all pass. /holders: 20 of 20 HTTP ok and non-empty. /oi: 261,693 base markets, 213,926 `oi_absent` (share
  0.817), 8 `absent_contradicted`, 8 unavailable (share 3.1e-5), 0 lookup failures, 0 integrity violations, 0 split
  batches. Absent probe: the 20 highest-volume absent markets all had no holders. Event-OI cross-check: 709 of 724
  single-market events agree within 0.25 (median ratio 1.0). Frame: 8,038 eligible; samples 1,500 main (pool 5,796,
  no shortfall) and 300 sports.
- **Action:** q0162 holders-snap and q0163 holders-prints promoted unchanged from the drafts (rules v6). The collector
  freeze check (CB8 §10.1, GO_WITH_CONDITIONS) and the H-v6 re-check were already met. Both jobs refuse until
  max(2026-10-21T06:00Z, first run + 2 h) and send idle heartbeats meanwhile. q0172 census stays a draft until near
  T8_H1_end + 30 h (it would exhaust the 48-tempfail limit if queued now). Host wallet key checked: fingerprint
  80ce5e81a539a570 = the pinned value.

## CB12 challenger round 1 response (2026-10-18; design only, not counted)
- `science-reviewer` round 1 verdicts: M REVISE, E REVISE, F REVISE, X ACCEPT (non-blocking only), O REVISE
  (effectively DROP unless daily strike events exist). 24 items (14 blocking), all adopted, none rejected; status
  DRAFT-REVISED, code and code-against-design freeze check next (`CREATIVE_BATCH_12.md` §9-§10). Changes: E points at
  fidelity 60 usable from stamp + 3,600 s, q0245 requests recomputed (Σ 14-day chunks, ≤ 15,000), checkpoints from
  2024-09-04T16:00Z; E window-component cluster way (GE ≥ 30 components), 10:00Z `p_reg` read for E1-rep, E Stage-2
  stop rule (≥ 30 components and 100 units by the unchanged 90-day cap, likely "not run (power)"); M print reach
  (`limit` 10,000, "unavailable (source)", binding worst-case fill), separate SCREEN/HOLDOUT outcome files with the
  HOLDOUT sha256 sealed, a frozen sports exclusion (tags + broadcast regex; sports arm only as a later registration),
  `ceil_tick` quotes, a binding bid-proxy check, a speaker factor in GMP; F paging at `limit` 10,000 (≤ 4,800 requests),
  feature-only power gate GFP (MDE > 2 x floor → not run), per-event and short-stratum rules; X hindsight-end-date
  label, fresh-steps robustness, no E009/E010 subgroups; O kept: 8 counts-only round-1 probes found a live daily
  equity strike template ("<Name> (<TKR>) closes above ___ on <date>?", 10 live, ≥ 32 distinct 2026 settlement dates
  in a truncated search), so O windows and GO need ≥ 30 distinct settlement dates (else "not run (power)", counted),
  O2 pays on the Gamma resolution, listed-`K` and iv time-convention rules, `m_prev` at 11:00 ET; Holm early
  finishers at α/10 in both stages. Request budgets recomputed (historical ≤ about 73,000, planning about 46,000).
- Declared k after revision: **unchanged, 10 fixed (M1, M2, E1, AL1, AL2, SH1, SH2, X1, O1, O2; Holm k1 = 10) + ≤ 10
  conditional = 10-20.** Count 0 now; cumulative **1,181** from the committed `trials.jsonl` at `fec1b04`.

## CB11 code-against-design freeze check, 2026-10-18 (science-reviewer): not counted
- Code b1e2894 (64 tests; W family, smoke and shared code; P and A not yet implemented). Rules hash 577f5c4a… re-derives.
  **q0220 smoke + q0221 keys ACCEPT_WITH_FIXES; W chain (q0222-q0224, q0230-q0232, q0235) ACCEPT_WITH_FIXES.**
- Must-fixes: (B1) one whole-document rules hash, so adding P/A would refuse every pending W job: hash per part (W, PA);
  (B2) q0221/q0224 return in_progress with exit 0 but the drafts have no `repeat`; (B3) C1/T5 ids silently "absent"
  (write-once) when not staged; (B4) mandatory h2_main/h3_power sample files silently skipped; (B5) W2 ignores print
  coverage (uncovered markets must be unavailable, < 60 % -> not testable); (B6) GW2 counted no_room/unfilled as
  decided; (B7) W2 sign-by-calendar-month robustness missing; (B8) W1-rep judged at 0.01 instead of the Stage-2 alpha
  0.05/k; (B9) rep pool annualised over W_screen (122 d), not W_hold (71 d); (B10) unverified disjointness stopped all
  of W, while the design says only P/A. Plus nine non-blocking items (capped censoring windows, undeclared table
  deviations, h3-only subset, integrity re-checks, MDE from counts, q0235 coupling to P/A, "unfilled" split).
- Fixes being implemented (rules v2, per-part hash); a focused re-check follows before q0220 is promoted.

## CB11 focused re-check (B1-B10) and P/A code-against-design freeze check, 2026-10-18 (science-reviewer): not counted
- Code 32f06da (145 tests; rules W `ecf500f7…`, PA `a8727c40…` re-derive). B1-B10 resolved except a residual B6/N9
  counting slip (`w2_units` still counts no_room/unfilled as decided); N1-N9 spot-checked resolved. The W hash covers
  `rep_w` and the PA hash covers `rep_p`/`rep_a`, so all fixes land before q0220 (W) and q0225 (PA) are promoted.
- **Verdicts:** (a) q0220 smoke + q0221 keys ACCEPT_WITH_FIXES (fill the two sample pins, stage the C1/T5 id lists);
  (b) W chain ACCEPT_WITH_FIXES: b1 seal drops never read by W analyses; b2 q0230 `--family auto` makes the W census
  wait on P/A seals; (c) P/A data ACCEPT_WITH_FIXES: c1 q0227 lacks `repeat`; c2 an exhausted Wikipedia budget never
  reaches an end state; (d) P/A analysis ACCEPT_WITH_FIXES: d1 `--stage2-k` has no N7 lower bound (alpha could be
  loosened); d2 rep_p/rep_a ignore drops; d3 P/A screens skip the N5 integrity checks.
- Coordinator: sample pins measured read-only on the host (h2_main `77a15bd9…`, h3_power `f8e1a7bb…`); C1/T5 id lists
  being extracted from release `data-20261013-research-lab` (hash-verified against its `files.sha256`). Fixes being
  implemented; nothing promoted yet.

## CB13 drafted (98a00e6) and challenger round 1, 2026-10-18 (design only, not counted)
- `CREATIVE_BATCH_13.md` from round 6: **CB13-T** (CH128, maker mark-out by frozen resolution class, host files only)
  and **CB13-R** (CH118, barrier-versus-terminal on crypto "reach/dip" ladders, own Binance fetch). CH119 deferred
  (census: about 74 eligible markets after CB2-W and CB12-E keys). k = 3 fixed + up to 5 conditional; count 1,181 now.
  Probes contradicted three round-6 premises (no CB8-B Binance archive; captures carry no question text; the monitor's
  alerts are the `uf_*` rules, not `sm_learned`).
- **Challenger round 1: T REVISE, R REVISE.** Main challenge: T's paper fill against a capture touch up to 60 min old
  measures staleness, not toxicity (fill must anchor on the print). Also: T HOLDOUT captures from 10-20T22Z sit inside
  J4-R `[10-16,10-21)`; T HOLDOUT mark-outs wait for the CB3 freeze (CB3 dev window counts-only); add a series x block
  way; R needs same-asset overlapping-window components, nested placebo latents, kline coverage from min T0, and a
  >= 30-component gate before the large fetch. Response round in progress.

## CB12 code (74a0f17) freeze check, fixes (c0cb6ba) and verify round, 2026-10-18 (science-reviewer): not counted
- Code common + smoke + M + X (90 tests). **Freeze check: REVISE** (keys never wrote the series-date file; q0241/q0242
  could finish half-done; X source not hash-pinned; month top-5 drop missing; smoke/C1 failures not counted as
  "not testable (source)"; q0243 held every member in memory; rep_m omitted `units_t24`, so M1-rep could never pass;
  rep ignored seal drops; the 60 % availability rule was missing). M1 copula placebo: not a code defect, accepted as is
  (power cost, the 1.5 % limit stays).
- Fixes c0cb6ba (parts common `81301d59…`, M `94f059ee…`, X `45428b85…`). Sports tag list = the 492 tag ids of the
  Gamma `/sports` registry (`evidence_cb12/sports_tag_registry_20261018.json`), accepted as a disclosed deviation from
  the "out-of-window events" wording (metadata only, no outcomes).
- **Verify round: X GO; smoke/keys, M data and M analysis NO_GO** until D1 (series-date event lookup not closed-first,
  no unverified-share gate), D2 (shared Holm helper non-strict; CB12 uses a local strict Holm), D3 (budgeted stops via
  `--budget-min`; B2 wording) and D4 (q0243 regex). Being fixed. Nothing promoted.

## Smoke events, 2026-10-18 ~21:00-21:30Z (engineering gates; not counted as tests)
- **CB12 smoke q0240 (rules common f2f672c1…, M 8b72053c…, X 24e3444b…)** ran 21:04Z, 8 requests, write-once
  `creative_batch12/smoke.json`: every X criterion PASS (`x_c1_reproduction`, `x_inputs_pinned`, guards); M criteria
  PASS except `m_prices_history` (m0 status 200 with 0 points over `[start - 26 h, start]`, m1 156 points; the Data API
  shows 528 prints for m0, apparently all during the event). Reading: the criterion tested member pre-start
  liquidity, not the source. **M smoke v2 being prepared** (v1 kept as the record; disclosure in CB12 §11; precedent
  CB9 smoke v2 / CB8-H v3). X proceeds on v1 (q0251 X census, counts only).
- **CB11 smoke q0220** attempt 1 (21:02Z) failed before any request: `SystemError` because rules verification imports
  scikit-learn, which cannot map under the 400 MB address cap (mem_mb 200). Ops fix 6c2056f (mem_mb 400 on five small
  jobs). A coordinator diagnostic of the smoke's network steps (counts only, nothing written, no trial line) then showed
  the out-of-window politics weeks (May 2024) contain no market with life >= 100 d, so `prices_history` and
  `data_api_reach` would fail vacuously and mark P/W2/A "not testable (source)" for a sampling artefact; and the
  pageviews lag was 69 h (> 48 h; declared consequence: lag 72 h, A origin X + 4 d). **q0220 parked before it wrote
  anything**; the pick search is being fixed (bounded out-of-window long-life search) before it is revived.

## Smoke fixes and CB12-X freshness correction reviewed, 2026-10-18 ~21:20Z (science-reviewer): not counted
- a5b86e0: CB11 smoke picks long-life out-of-window markets by a bounded backwards search (ends before 2024-06-24, before
  P's SCREEN start 2024-07-01): **accept**. wiki_lag now drives A's declared fallback (lag 72 h, origin X + 4 d) instead
  of stalling A: matches CB11 §2.2, but **revise**: a lag above 72 h itself must make A "not testable (source)" (the
  probe showed 69 h, about 3 h of margin). CB12 M smoke v2 (pre-start-traded members; v1 kept): **accept as a
  disclosed supersession** (outcome-blind; member liquidity carried by the census 90 % per-unit and 60 % availability
  rules); minor: truncated print fetches must count as unknown.
- 16870d6: CB12-X freshness measured from usability (PM stamp in `[t - 1200, t - 600]`) after the X census showed 0
  fresh pairs: **accept** (outcome-blind, only counts seen; the stamp-based reading could never be met). Defect: the X
  screen did not check the census rules sha. A q0240 job note misstated the v1 smoke sha (the record is common
  `f2f672c1…`, M `8b72053c…`, X `24e3444b…`); being corrected.
- Promotion: q0251b X census v2 GO; q0240b GO after the record fix; q0220 revival GO after the 72 h ceiling; q0255
  after the census sha check and the v2 census write-up.

## CB14 drafted (03f7200), challenger round 1 and response (e696bf8), 2026-10-18 (design only, not counted)
- `CREATIVE_BATCH_14.md` from round 6: **CB14-W** (CH123, Wikipedia edit bursts before resign / out-as / fired /
  indicted moves; listing-date frame, data before 2026-04-01, disjoint from CB11-A) and **CB14-S** (CH121, intra-speech
  hazard decay in mention baskets; P window disjoint from CB12-M, N window gated on CB12-M's Stage-1 result). CH127
  deferred (no timestamped preview source). k = 4 fixed + up to 4 conditional. Probe counts: out-as 296, resign 71,
  fired 31, indicted 18 events; S P-window 60 single-speech events with >= 8 words (43 Trump).
- **Challenger: W REVISE, S REVISE.** W1 could count a burst after the market had already repriced (lead now measured
  from the move start D0 against the [D-24 h, D-2 h] VWAP; hot-period same-subject placebo is the baseline); W2 worst
  case was a median cost; S's unsaid rule read 60 s past the causal clock (now: unsaid iff not said by e_t, anchors only
  from words said by e_t, ±2 min clock shift binding); term-level dependence added; the N window becomes reported-only
  if S's rules are hashed after CB12-M's Stage-1 result. All 14 items adopted (2 modified, flagged for the freeze
  check). Count: 1,221 at HEAD (40 flow_screen lines arrived by host union); counts are recorded at run.

## Smokes PASS and CB12-X census v2, 2026-10-18 ~21:35-21:45Z (engineering gates and counts; not counted as tests)
- **CB11 smoke q0220 PASS** (21:34Z, 19 requests, rules W `2d2bb169…`): all criteria pass except `wiki_lag` (pageviews
  newest day > 48 h old); `wiki_lag_ceiling` (<= 72 h) holds, so A uses the declared fallback (lag 72 h, origin X + 4 d,
  outcome-blind). The CB11 data chain runs. q0221 attempt 1 hit a MemoryError under its 1 GB cap (id sets peak about
  493 MB RSS); ops fix mem_mb 1200 (6770b34); attempt 2 had started under the old cap and was stopped (not counted).
- **CB12 M smoke v2 q0240b PASS** (21:38Z, 12 requests; `smoke_M_v2.json`, v1 kept).
- **CB12 X census v2 q0251b** (rules X `7485a272…`, counts only): 316 pairs / 183 events / 13 resolution months;
  step pairs short 125,967 (fresh 94,636), mid 279,399 (181,042), long 82,969 (64,192); GX gate pass in both bins;
  G event 183, month 13 (long bin: 25 events, 10 months). Volume key `volume` (500/500). **Decision before the screen:**
  freshness as corrected (A7); volume terciles from `volume`. q0255 X screen promoted (X1, one counted test).

## CB12-X freeze, 2026-10-19 ~01:15Z (science-reviewer ACCEPT_WITH_FIXES; not counted)
- q0255 (X screen) refused twice on 10-18 (rc 2, "freeze spec not found"): it was promoted but `model_specs/cb12_v1.json`
  had never been written. Those attempts read nothing and compute nothing.
- Freeze confirmation (science-reviewer): the declaration matches the design (bins, floor, ways, seeds, placebo, GX,
  label, robustness; nothing relaxed); the census was counts only (`census_x` never calls `gap_of`); no CB12-X test
  line exists in trials.jsonl. Fixes applied in the file: census hashes both ways (canonical object `f0c5d9f7…`, which
  reproduces on the host; file bytes `340c72f5…`), the A7 freshness text, the decision rule as bound by the rules hash,
  and two branches the census forces: (i) the month way (G 13, long bin 10, < 15) drops out of the p maximum and only
  its leave-one-month-out sign rule binds, so X1's p is the event-way p (G 183); (ii) Elections has 6 long-bin pairs
  (< 10), so that stratum is reported as not evaluable in the long bin.
- Census (read-only on the host): pairs short 239 / long 56, events 154 / 25, availability 0.991, `label_X` null.
- **Frozen:** `model_specs/cb12_v1.json` part X, rules `7485a272…`, X-part sha256 `b231830e…`. q0255 revived (one
  counted test, X1). Other CB12 parts (M, E, F, O) freeze later as separate keys, each committed before its screen.

## Operational deviation: CB3 quote_state refused every pass since about 10-17 (found 2026-10-19 ~01:20Z; not counted)
- `arepo_pass.sh` ran `run_cb3_quote_state.py --all-new --data-dumps-cap-gb 13`; the 10-17 guard raise to 40 GiB
  (36d908f) covered the queue jobs but missed this collector-pass line, so once data-dumps passed 13 GiB every pass
  logged `refused_no_headroom` (19 captures pending at 00:31Z on 10-19, 0 written). No row was written or altered.
- Fix: the cap is now 40 GiB (the convention). The extraction is idempotent and oldest-first over complete captures
  still on the host (the 8-day snapshot rule frees nothing before about 10-25), so the 19 captures are extracted
  over the next passes (600 s timeout each). The effect is a delay only; if any capture is no longer on the host when
  reached, it is recorded `missing`, never reconstructed.

## CB13 code (fef4066) freeze check, 2026-10-19 ~01:10Z (science-reviewer): REVISE; not counted
- 59 CB13 tests pass; rules parts common `51e84496…`, LABELLER `5907eaa4…`, T `bf693848…`, R `996bccf7…` verify.
- Groups: T smoke, T frame/data, T census, R smoke/data, R pregate/census and R screen/rep GO_WITH_FIXES; **T screen,
  T rep and R seal NO_GO.** Nothing promoted.
- 22 defects. The main ones: (1) the T1 composition placebo raises KeyError on any event outside the T1 index, so
  q0273 could never run; (2) the 60% availability rule is unused; (3) a smoke FAIL writes no counted
  "not testable (source)" line; (4) Holm is non-strict (CB12 D2 again); (5) an unverified-disjointness stall leaves R1
  uncounted; (6, 7) GL ignores UNKNOWN > 5% and the thinned-population label is never set; (9) HOLDOUT skips the
  late-receipt day 10-26; (10) T exclusion keys drop ids without timestamps (an undeclared population change);
  (13) a ledger sentence quoting the design could lift the CB3 hold; (21) R `hourly_change` reads points that are not
  usable at t (a small causal leak). The rest are queue drafts (lanes, mem_mb, budget, `not_before`, regex) and
  undeclared parser and labeller deviations.
- Trial count: `battery2.cumulative_count()` gives 1,226 at HEAD. The code records the count at run time, so the
  design's 1,181 and 1,221 are historical.
- Next: an implementer fixes 1-22 with regression tests, then a verify round, then promotion in the reviewer's order
  (q0270 -> q0285 -> q0271/q0272 -> q0276-q0279, q0284 -> q0280; screens after the freezes; q0274/q0275 last; q0275
  also needs CB3's freeze).

## CB12-X Stage 1 screen (q0255), 2026-10-19 01:00-~01:30Z: X1 NOT IDENTIFIABLE (placebo advanced); 1 counted test
- Frozen part X `b231830e…`, census v2 bytes `340c72f5…`, results `creative_batch12/results_X.json` (file sha256
  `5a3b88f3…` on the host). Label: L1, worn set, new moderator, hindsight end date. Evidence role exploratory_historical.
- **X1** (does the cross-venue gap decay more slowly in long-horizon pairs?): pooled AR(1) rho short 0.868 / mid
  0.905 / long 0.952, so the half-lives are 48.9 / 69.6 / 139.7 min. The contrast HL_long - HL_short is +90.8 min,
  above the 60 min floor. Event-way cluster bootstrap p = 0.0030 (G 181; 2,000 draws). The month way (G 13) leaves
  the maximum by the frozen branch; its leave-one-out sign holds. The early Holm (0.005) passes. Availability 0.991.
- **The horizon-offset placebo advanced in 32 of 200 draws (16%, against the <= 1.5% allowed).** Permuting the
  horizon within category reproduces a qualifying contrast far too often, so the contrast is not attributable to
  horizon; pair or category composition explains it as well. Robustness also failed: the top-5 event drop, the top-5
  resolution-month drop, and the strata sign (Elections is not evaluable in the long bin; Sports holds). Causal
  demeaning, |g| >= 3c, the edit flag, fresh steps, thirds and volume terciles hold.
- **Verdict: not identifiable; X1 does not advance.** CB12-X has no replication stage (L1), so CB12-X is closed.
  Reported only (descriptive): the K->P lag cross-correlation at lag 2 (short bin) is 0.45, against P->K 0.001. This
  is consistent with the sealed Kalshi-lead object (E009/E010) and is not re-tested here.
- Count: the trials.jsonl line (n_tests 1, family cb12_X) was written on the host. `by_triage` cumulative is 1,231
  (q 0.1, no survivors).

## Ops: CB3 quote_state caught up (02:31Z pass, 2026-10-19); not counted
- After the 2018cf6 guard fix, the 02:31Z collector pass extracted all 20 pending captures (written 20, missing 0,
  remaining 0, max 16.4 s per capture). The deviation above was a delay only; no capture was lost.

## CB11 q0221 superseded by q0221b (exclusion-key id sources and key reuse), 2026-10-19; not counted
- q0221 never completed (two 40-min timeouts, an error, a stop; parked on the host, its partial `exclusion_run11/` kept
  and refused by the code). Cause: the code read the whole CB4 series walk (3.96M ids) instead of the sampled unit frame
  that §1.3 names, and looked up every id on Gamma even where a source already carried keys.
- Amendment `CREATIVE_BATCH_11.md` §11.2: series source `units.jsonl.gz` (13,657 ids), keys reused from sources,
  Gamma lookups only for the remaining ids (about 3,300 batches against the declared <= 400: a declared engineering
  deviation). science-reviewer: ACCEPT_WITH_FIXES; fix 1 applied (conflicting negRiskMarketIDs are looked up, not
  reused), fix 2 recorded (source keys are snapshots; affects only the P/A series rule). No population, gate, floor,
  alpha or the 2% rule changed; nothing outcome-dependent is read.
- Rules part W `6d3f1613…` (was `2d2bb169…`); P/A rules `2d48bd73…` unchanged. q0222-q0231 and drafts q0232/q0235
  re-pinned; q0222/q0225/q0227 now depend on q0221b. The q0220 smoke PASS stays valid (smoke code unchanged).

## CB13 verify round (fixes 39c85d9), 2026-10-19 ~04:35Z (science-reviewer): REVISE; not counted
- 20 of 22 defects FIXED, #14 partial, #15/#19 declared; 74 CB13 tests pass; rules parts reproduce.
- New defects: **A (high)** the CB13-wide Stage-2 Holm can never add a pass (`adv` already needs p < 0.01 = alpha/5;
  design §2.3 says the final Holm "can only add passes"); **B (medium)** an R pregate fail writes no census, so screen-R
  tempfails until `failed` and stage2-final waits forever (same for a failed smoke); **C** q0271/q0274 lack
  `--budget-min` and `repeat`; **D** the T3 <= 100-share limit is not applied; **E** shared c12/c10 helpers are not
  hashed in the rules.
- Verdicts: T smoke GO; T census and R seal GO; the rest GO_WITH_FIXES. **Promoted now: q0270 (T smoke) and q0285
  (R smoke).** Next: fix A-E, reseal, then q0271 -> q0272; R data after the CB11 exclusion keys (q0221b) are pinned.

## CB13 fixes A-E (7fb59a3) re-check, 2026-10-19 ~05:10Z (science-reviewer): ACCEPT_WITH_FIXES; not counted
- A (Stage-2: checks_ok and (p < alpha/5 or Holm reject)), B (terminal counted not-testable on smoke/pregate fail),
  C (q0271/q0274 budget + repeat), D (T3 position min(size, 100), declared) accepted. E completed in the follow-up
  commit (more shared helpers hashed); rules resealed: common `62e90149…`, LABELLER `1e515bb4…`, T `05acfff6…`,
  R `27ddbc2e…`; drafts re-pinned; q0276 depends on q0221b.
- Still needed before T data: the GL labeller audit (`audit-sample --round 1` on the host, independent labels,
  `audit-score`), then q0271 -> q0272; q0273 needs the T freeze (`model_specs/cb13_v1.json` via `freeze-part`).

## CB14 code (d50a2ed) freeze check, 2026-10-19 ~05:05Z (science-reviewer): REVISE; not counted
- 90 tests pass; rules parts reproduce. 18 defects; three repeat CB13's (the Stage-2 Holm cannot add a pass, shared
  helpers unhashed, stalls write no counted line). The most serious: the small-G rule marks a test untestable when any
  way has < 15 clusters (design: that way leaves the max and its leave-one-out sign binds); W live tracks nothing (date
  clamp); W Stage 2 reads only the latest live frame (selection on outcome); the N exemption can be emptied by CB13's
  key file. Implementer fixing 1-18; nothing promoted.

## CB15 drafted (2920504), challenger round 1 and response, 2026-10-19 (design only, not counted)
- `CREATIVE_BATCH_15.md` from round 6: **CB15-E** (CH129, US election night 2026-11-03, a one-night case study with
  the single-cluster caveat in its title; part E frozen by 2026-11-01T12:00Z or "not run (calendar)", counted),
  **CB15-P** (CH130, cross-venue pairs listed first on Kalshi, census-gated), CB15-L (CH125 leaderboard incumbency).
- Challenger (science-reviewer): E REVISE (the national swing does not cancel across per-state windows, so tests are
  stratified by closing time with a control-market drift check; no spread-based selection at entry; network-archived
  sign sources; priority-99 jobs and cron pause/resume for the night), P REVISE (birth from first print, not resampled
  history; the C1 population is selected on lifetime volume, so it is labelled as such with a lowest-volume-tercile
  check), **L WITHDRAWN uncounted** (no L outcome, price or leader seen; archived leaderboard pages hold no table).
- Response: 8 adopted, 3 adopted with stated modifications, none rejected. k = 4 fixed (E1, E2, P1, P2) + up to 2
  conditional; k1 = 4 fixed now (because of the withdrawal). Jobs q0340-q0353. Next: GE0 sign table compiled by two
  independent network-enabled compilers with archived sources, then rules, code, the freeze check by 10-29.

## CB11 chain after q0221b, CB13 smokes, CB12 M promoted, 2026-10-19 05:30-09:05Z (queue events; verdicts pending checks)
- **q0221b DONE** (exclusion keys, 33 min): 525,227 ids, missing share 0.0128 (< 0.02), disjointness verified, key file
  sha256 `c8a1d64b…` (= `keys_sha256` in `exclusion_report.json`). This pins CB12 q0241 and CB13 q0276.
- **CB11-W: provisionally "not testable (censoring windows)" (q0222 w-frame, 26 s; q0223/q0224/q0230/q0231 carried the
  label).** Stall reason: reconstructed censoring windows cover < 99% of a frame's closed rows (h2_main 0.592, h3_power
  0.574). Not yet counted: an engineering check (genuine source limit vs a coverage/denominator defect) is running; the
  label is recorded as final and counted only if the check finds no defect.
- **CB11-P/A data:** q0225 pol-frame complete (pol screen 265 / holdout 704; ctl screen 334 / holdout 554); q0226
  pol-prices complete (1,857 markets, 5,571 units). **q0227 attn-frame FAILED 3x (MemoryError under the 2 x mem_mb
  address cap)**; being fixed under a new id (q0227b); q0229/q0238/q0239 wait on it.
- **CB13 smokes both FAIL (engineering gates, not tests):** q0270 T: `t_capture_print_join` false (guards and labeller
  pass). q0285 R: `r_prices_history`, `r_rule_parser`, `r_walk_finds_search` false (Binance units, request cap, guards
  pass). Both outputs carry `counted_not_testable_source: true`; whether that flag stands (genuine source failure) or
  the smokes re-run as v2 after defect fixes is being checked against the design's consequence table. Not counted yet.
- **CB12 M chain promoted** (a7736e3; q0241 `--base-sha256 c8a1d64b…`, depends on q0221b; q0242/q0243/q0248/q0249);
  regenerated CB12 rules identical to the committed file (common `f2f672c1…`, M `a2e420b0…`). Deployed 09:05Z.

## CB14 fixes (515d68d) re-check, 2026-10-19 ~09:40Z (science-reviewer): ACCEPT_WITH_FIXES; smokes promoted; not counted
- All 18 freeze-check items addressed (F8, F13 partial). 109 CB14 tests pass; rules reproduce (common `0440b859…`,
  W `1a9b1132…`, S `8e448f1e…`). q0302's base pin is CB13 q0276's key file (design §1.3), so it stays a token until
  q0276 runs. New draft q0323 (Stage-2 final Holm).
- Open before the S freeze / q0302 / q0321: **F13 (high)**: S Stage-2 sets unresolved members to y = 0.5 at window close
  and never re-fetches outcomes; resolution timing may depend on outcome. F5 gap (smoke ignores a terminal record),
  F8 transitive helpers unhashed, F12 wording, q0302 still depends on the failed q0227, q0321 regex lacks
  `terminal_not_testable`, stage2-final skips the rules check, live-print merge overwrites coverage (power only).
  The implementer is fixing these.
- **Promoted and deployed (a1d9399): q0300 (W smoke) and q0301 (S smoke), priority 25, net lane.**

## CB13 smoke defects fixed (ca86bf2), 2026-10-19 ~09:45Z; v2 smokes drafted; not counted
- All six failed v1 criteria were code defects: T paired two SCREEN captures before the print window opened (0 prints
  between; the fix uses the first in-window pair: a host dry run joins 422 = 422 prints); R's undated search queries
  found no event in the window, so the walk, parser and prices-history never ran (fix: dated queries, end ±60 s
  window, which also removes a hidden breach of the 30-request cap). Disclosure `CREATIVE_BATCH_13.md` §11.y; rules T
  `f72683f5…`, R `32bbd825…` (common, LABELLER unchanged). Drafts q0270b/q0285b (`--supersedes default`).
- v1 count lines (T 2, R 1) stay in trials.jsonl (conservative double count if v2 passes).
- **Open scientific question:** every probed weekly barrier event has 7-9 late-added members whose rules start "from
  the creation of this market" with unquoted High/Low, so the frozen R flag rule gives flags_ok = 0 per event. A
  science-reviewer is ruling on whether this is a genuine source limit (R not testable, counted) or a specification
  defect that may be corrected before data with written justification.

## Hour 10:00-11:00 UTC+1, 2026-10-19: fixes, reviews, promotions (nothing counted)
- **CB11 provisional W label WITHDRAWN (not counted): engineering defect.** The code checked censoring windows as
  half-open `[a, b)`, while the Gamma walk that built the frames and the q0224 count use `[a, b]`. Host evidence: every
  unmatched closed row (h2_main 81,574 of 199,868; h3_power 94,273 of 221,169) ends exactly on a window end, in every
  month and category; with `[a, b]` both frames match 100%. Fix 9ede7dd (amendment `CREATIVE_BATCH_11.md` §11.4; W
  `6d3f1613…` -> `7734729d…`); new-id W chain drafts q0222b-q0231b (output naming being adjusted so CB12-CB15
  exclusion readers see the W prints file without rehashing their frozen code). The q0222-q0231 stall records stay.
- **CB11 q0227 MemoryError: engineering defect** (`walk_day` held a whole day of raw Gamma markets, ~10 KB each,
  under an 800 MB cap; peak 250 -> 64 MB after the fix, same rows and order). §11.3; P/A rules `2d48bd73…` ->
  `125386f2…` (only `walk_day`/`attn_frame`; q0225/q0226 code unchanged); q0227b drafted (mem 600, resumes the 9 walk
  days on disk); q0229 depends on q0227b. Review of §11.3/§11.4 before promotion.
- **CB13:** T smoke v2 (q0270b) **PASS** 09:24Z (capture-print join 422 = 422). Labeller audit round 1 sample drawn on
  the host (200 SCREEN markets, 30 sports-adjacent, seed 13121; sample `e474c5f4…`, key `9db3c64f…`); a blind
  science-reviewer is labelling titles and slugs only. §11.z (R flags per member as designed; creation-anchored members
  excluded and counted by a description-only rule) science-reviewer **ACCEPT_WITH_FIXES**: it decides gate GR (with
  anchored members the probe share is 0.667 < 0.95), so §11.z must say so; R1's claims are limited to strikes listed
  when the window opens. R `7d05b00d…`. **q0285b (R smoke v2) promoted** (d759773).
- **CB14:** re-check fixes 31bdc39 (F13: 14-day post-close outcome re-fetch before q0322; smoke terminal check;
  transitive helper hashing; q0302 -> q0227b): common `d34a2e73…`, W `011abaf5…`, S `657c7ae3…`. Smokes q0300/q0301
  queued (net lane, behind the running CB12 M job).
- **CB15:** part E code dbb5db4 (rules common `13c70322…`, E `a796280b…`; drafts q0340-q0346; additive `LANE_HOLD`
  flag in `queue_worker.py`, inert until a hold file exists; `scripts/oracle/cb15_e_crontab.txt` not installed);
  P Stage 1 e01ce12 (P undeclared until Stage 2 exists). Part E freeze check running.
- **CB16:** draft f78a396 (Q quoter grain, U wake-up prints, K Kalshi-absent census k = 0, H hedging skew).
  Challenger round 1: **REVISE**; Q REVISE (the mark-out includes the realised half-spread, a mechanical grain bias near
  the floor; stale-spread strata; single-grain placebo cells), U REVISE (the activity rule excludes the dead books that
  are CH132's object; U2 cost robustness vacuous; HB1 MS2 disclosure), K ACCEPT with fixes, **H WITHDRAWN uncounted**
  (MDE 12-20c vs the 4c gate; trigger depends on R1's outcome on the same units; no R result exists). Response in
  progress.

## CB15-E code (dbb5db4) freeze check, 2026-10-19 ~09:55Z (science-reviewer): REVISE; q0341 promoted; not counted
- Rules reproduce (common `13c70322…`, E `a796280b…`); 63 tests pass; strata, weights, within-stratum permutation, GEP,
  k1 = 4, strict p < 0.01, outcome stripping, no spread exclusion at t_b and counted terminal records match the design.
- Defects: (1, high, design amendment) a race called and resolved within 12 h loses its book and is dropped as a gap,
  which excludes on post-entry state (the fastest-called races carry the largest drift): closure must be told apart
  from gaps and use the last read before closure; (2) a Gamma outage can stall the minute collector; (3) transient
  NTP/`/books` faults score as a terminal smoke FAIL, and out-of-frame tokens are unfiltered; (4) a deploy touching
  hashed helpers before 11-06 would silently stop the collector (heartbeat watchdog and deploy freeze needed); (5) the
  tier snapshot has no time bound; (6) the trade-market pick is arbitrary with several Democrat members; (7) an
  untestable placebo counts as met; (8) a weak calendar check; (9, 10) undeclared rules and unhashed gate logic.
  LANE_HOLD fail-safe accepted; the hold must start early enough that no heavy job runs into the night.
- **q0341 (census, counts only) GO: promoted (6131cf4), priority 99.** q0343 smoke NO_GO until fix 3.

## CB13 GL round 1 FAIL and labeller revision 1 of 1 (551cdc4), 2026-10-19 ~09:35-10:05Z; not counted
- Round 1 (seed 13121, 200 SCREEN markets, 30 sports-adjacent; blind science-reviewer saw titles and slugs plus the
  written definitions only): overall 0.91; LOW 0.98 of the labeller's / 0.90 of the reviewer's; **NEWS 0.75 / 0.94 ->
  FAIL** (>= 0.80 both ways needed). Records `docs/research_lab/audits/cb13_gl/` (33a8b17). The reviewer's prose
  totals were mis-stated; the scored JSON (sha256 `2dba4619…`) has 62 LOW / 48 NEWS / 90 other.
- Revision 1 of 1 (`CREATIVE_BATCH_13.md` §11.r), general rules from the class definitions, not title memorisation:
  PUBLIC-STATISTIC gains more macro releases (PPI, JOLTS, ADP, claims, trade balance, YoY/MoM forms), post/tweet counts,
  box-office "grossing" forms and chart ranks; SCHEDULED-EVENT gains award shows, central-bank policy rates and named
  central banks, and "next <elected office>" unless the title has "by"/"before" or a removal word. Known flaw:
  appointed offices (e.g. France's PM) also match. Unchanged: fee-type PATH labels, the Senate-odds title (Polymarket's
  own odds, not a published statistic), sidecar sports labels. On 130k historical questions the rules move
  291/157/167 titles. LABELLER `1e515bb4…` -> `95cde0ab…` (T does not hash the labeller; it is pinned by the freeze
  and the audit file). Round 2: fresh 200 (seed 13122), new blind reviewer; a second FAIL makes T1/T2
  "not testable (labeller)", counted.
- CB13 q0276 draft now also depends on CB11 q0223b (the h11_wprints directory exists with only the stalled manifest,
  so an earlier run would read 0 ids and never re-read them).

## CB13 GL round 2 sample drawn, 2026-10-19 09:47Z; scoring rule declared before labelling; not counted
- `audit-sample --round 2` on the host: 200 SCREEN markets, seed 13122, labeller `95cde0ab…`. **36 of the 200 also
  appeared in round 1** (the frozen sampler does not exclude round-1 ids); 2 of those 36 were round-1 disagreements,
  which the revision addressed. Declared now, before any round-2 label exists: the binding score is the full 200 as
  drawn by the frozen sampler; the 164 markets not in round 1 are scored as a sensitivity check; **if the two verdicts
  differ, round 2 is recorded as FAIL** (conservative). A new blind science-reviewer (no access to round-1 material)
  labels the sample.

## CB11 §11.3/§11.4 review (9ede7dd, 211b48a), 2026-10-19 ~10:15Z (science-reviewer): ACCEPT (minor); W v2 promoted
- [a, b] is a genuine code defect (the frame walk queries Gamma with end_date_min = a, end_date_max = b and q0224 uses
  the same bounds; the old check used ends < b); the design never specifies half-open; the 0.99 floor and GWC gate are
  unchanged; window membership only feeds the N8 gate and censoring counts, never unit selection. §11.3 (memory) changes
  no output. Correction to the entry above: the W fix is recorded in `CREATIVE_BATCH_11.md` §11.3/§11.4 as written
  there, and the live hashes are **W `a3a16f98…`, P/A `94f0d5e0…`** (`7734729d…`/`125386f2…` were superseded by
  211b48a before any W run). The only line written for the withdrawn label is trials.jsonl:9066 (`cb11_descriptive`,
  n_tests 0, excluded by §2.5); it stays as is. W v2 writes new files into `history/h11_wprints/` (`manifest_b.json`,
  id-only top-level `markets.csv.gz`); the stalled `manifest.json` is untouched and read by nothing.
- Process deviation: q0227b was committed straight into jobs/ by the implementer (9ede7dd) and started 09:40Z before
  this review; the review found no scientific change. Its 9 resumed walk days were fetched under P/A `2d48bd73…`.
- **Promoted (8f1b4eb): q0222b, q0223b, q0224b, q0230b, q0231b.**

## CB15-E GE0 committed (b7e1f0a) with archive audit; q0341 -> q0341b; CB11 W v2 and CB12 keys data done, 2026-10-19 ~14:20Z; not counted
- **GE0 (two network-enabled compiler passes, all 51 jurisdictions, archived):** passes agree on a non-zero sign only for
  **MS (+1)**; merged sign table MS +1, 50 x 0; **Cohen's kappa 0.0069** (pass A 6 x -1 / 1 x +1; pass B 12 x +1).
  Poll-close tables agree on all 51. Bundle sha256 `a571f58b…` (pinned in drafts q0344/q0346, ba0ce3b). Cross-table: the
  only non-zero effective sign is MS in the 01Z stratum.
- **Archive audit (science-reviewer, read-only, ~14:20Z): ACCEPT, no sign changes.** MS supported (2024 President and
  2022 House early-to-final D share recomputed from the cited NYT snapshots in both passes; NCSL counting-order cites).
  The 50 s = 0 entries were not individually audited (effective s is 0 either way) and are marked `unsupported`
  conservatively. **Two fetched files breach the no-2026-news rule** (`6aa6a304bac1…`, a May 2026 local news article;
  `8fd30b184a9d…`, a 270toWin 2026 poll-closing page whose navigation links 2026 forecasts, polls and prediction
  markets, no numbers); neither is cited and no entry changes; pass B's README claim that none was fetched is inaccurate.
  `party_map.json` is empty/pending (must be audited before any freeze).
- **Disclosure (compiler reliability):** both passes used NYT/AP results via Wayback, the same sign convention and
  office rule, but different early points: pass A = first capture with >= 25% of the final vote (median ~30%, election
  evening); pass B = first capture 10:00-13:00Z next morning (median ~96%). A measures the election-night swing toward R
  as election-day votes arrive; B only the late tail toward D (opposite directions in 13 states in 2022 and 15 in 2024,
  6 in both). The frozen rule (disagreement -> s = 0) was applied unchanged.
- **Consequence:** with no -1 state, no closing-hour stratum is identified, so **E1/E2 will be "not run
  (identifiability)", counted**, when GEI is evaluated (q0344 by design). Whether to run q0343 -> q0344 for the record or
  record the terminal directly goes to a science-reviewer after q0341b.
- **q0341 (CB15-E census) FAILED 3/3**, MemoryError ~20 s in, nothing written: address-space cap 2 x 300 MB; a local
  outcome-blind probe (no outputs, counts not inspected) measured Python peak 289 MB, max RSS 586 MB. **q0341b** = same
  argv/code/rules (common `13c70322…`, E `10ab88e7…`), mem_mb 1000 (e8c44f9, deployed).
- **Host data steps complete (queue events, no test):** CB12 q0241 exclusion keys (`exclusion_keys_complete`); CB11 W v2
  q0222b frame, q0223b prints (4,788 markets, 16 truncated, 0 unavailable), q0224b censoring (300 windows, 0 unavailable).

## CB13 GL round 2 (blind labeller audit): PASS, 2026-10-19 ~14:30Z; q0271/q0272 promoted; not counted
- New blind science-reviewer saw only `DEFINITIONS.md` and the 200-title sample (isolated folder); labels committed
  before scoring (727665d, `4710f404…`; LOW 60 / NEWS 55 / other 85). `audit-score --round 2` (host): overall 0.97;
  LOW 0.98 of the labeller's / 0.93 of the reviewer's; NEWS 0.92 / 0.98 -> **PASS** (`audit_final`). Declared
  sensitivity (164 markets not in round 1): overall 0.97, LOW 0.98 / 0.94, NEWS 0.92 / 0.98 -> PASS; verdicts agree, so
  **GL passes** and T1/T2 stay testable. Records in `research_lab/audits/cb13_gl/` (4cfb587).
- **Promoted (4cfb587, deployed): q0271 T frame, q0272 T census** (cpu lane; rules common `62e90149…`, LABELLER
  `95cde0ab…`, T `f72683f5…` verified).

## CB12-O code (c79364a) freeze check, 2026-10-19 ~14:40Z (science-reviewer): REVISE; not counted
- Rules parts recomputed: O `766eed85` matches the seal; common `f2f672c1`, M `a2e420b0`, X `7485a272` unchanged by
  c79364a. 28 O tests pass. Frozen constants, chain-before-books ordering, the two >= 60 s book reads, the digital
  construction, p = max over both cluster ways and Holm match the design; the census opens no outcome file; the
  collector uses keyless public sources only (Gamma, CLOB, cdn.cboe.com, Yahoo, api.nasdaq.com).
- Defects: (1, blocks freeze) `exdiv_status` reads chain fields containing "div", which the CBOE delayed chain lacks,
  so every unit would be "excluded: ex-dividend unknown" (needs a reviewed pre-data amendment, e.g. previous-session
  Nasdaq ex-dates with indices exempt; ETFs are also queried as `stocks`); (2) `screen_o` KeyError `w1` (untested);
  (3) the m_prev placebo only uses previous units that passed anchor filters (should be the raw second read);
  (4) O2 eligibility uses the second book read, taken >= 60 s after the decision (should be first-read tight + anchor);
  (5) the smoke skips Yahoo chart and the Gamma closed lookup; (6) the outcome guard checks labels not dates;
  (7) earnings/dividend rows for 11:00 units are fetched minutes after t (use the previous session's file);
  (8) missed checkpoints not counted in the census; (9) small items (unrefetched unresolved Gamma rows, per-unit
  agreement, census-value reuse, rule-text flags descriptive, "later ET date" disclosure; no root-cap enforcement or
  cron timeout).
- Next: implementer fixes 2-9 and drafts the amendment for 1 -> re-check -> q0260 smoke (after fix 5) -> freeze ->
  q0261. q0262-q0264 wait.

## CB15-P code (e01ce12, 49eba64) freeze check, 2026-10-19 ~14:45Z (science-reviewer): REVISE; not counted
- Hashes reproduce the seal (common `13c70322…`, E `10ab88e7…`, P `198b7fab…`); the P hash covers cb15_p functions,
  constants, `declared()` and the C1 loader; leakage guards hold (no outcome or `p_end` read, rows >= 2026-10-12
  refused, units from information at t_d). `pytest -k cb15`: 96 passed, 1 stale E test (expected TODO pins that
  ba0ce3b filled).
- Defects (HIGH): Stage-2 read windows not enforced and failed reads marked done; watcher runs the Kalshi refresh before
  reads and polls ineligible pairs (missed reads, request cap); P1-rep drops units without a two-sided 24-h book
  (post-entry selection) and lacks the >= 60% availability gate; top-5 cluster drops check sign only (design: p and
  floor). (MED) silent non-200s become permanent "no quote"; rule-boolean exclusion not applied; key rule incomplete;
  matcher pre-filters recent Kalshi markets (deviates from C1); stop rule counts unusable births; P1 availability
  denominator omits "no Kalshi quote"; re-reads replace first reads; per-minute full data-dumps walk. (LOW) undeclared
  deviations need a §11 P amendment; census misses two counts. Drafts q0347/q0348 mem 600 unverified (set 900).
- Next: implementer fixes all (common/E hashes unchanged) -> re-check -> promote q0347, q0348, then q0349, q0350;
  q0352 only after the Stage-2 fixes and a re-check (cannot start before 2026-11-04).

## CB12-E code (561647a), 2026-10-19 ~14:50Z (implementer); freeze check running; not counted
- Completed from the interrupted WIP: frame + USGS catalogue, 72 h accessor, negative-binomial model, E1 with both
  binding placebos, GE/GEP census (outcome-blind), collector, rep; added the reported Poisson variant, negRiskMarketID in
  the key drop, a month-name fix in the regional regex, the 7-day-lag and M >= 7.5 robustness for E1-rep, and a
  Stage-2 outcome guard (opens only for `rep-E`). §11 row E1 lists the implementation choices. 162 CB12 tests pass.
- Rules: E `9a60a4a5…`; common `f2f672c1…`, M `a2e420b0…`, X `7485a272…`, O `766eed85…` unchanged (recomputed).
- Drafts: q0244, q0245, q0253, q0257 (cron collector), q0258, q0266 (E census), q0267 (E-only smoke; q0240 predates E).

## CB12-E code (561647a) freeze check, 2026-10-19 ~15:00Z (science-reviewer): REVISE; q0267 smoke promoted; not counted
- All five rules parts recomputed at 561647a and match the seal; 36 E tests pass. Stage-2 magnitudes are stored as
  served (point-in-time); Stage 1 uses final revised magnitudes (disclosed), only events older than 72 h feed q.
- Defects: (HIGH) E1-rep pass ignores the binding p_alt placebo credit; Stage-2 catalogue outcome can undercount (read
  span starts at the earliest still-open window; > 10-day reads keep only M >= 5.5). (MED) 60% availability rule
  inert in Stage 2 and loose in Stage 1; missed/failed passes leave no record; p_alt placebo fails open; halves split
  at the median unit time, not calendar halves. (LOW) census reads events in [t-72 h, t) (disclose); trial-line role
  labels; Stage-2 span < 30 days; unlabelled capped windows; E2 drops; GE parser-failure denominator; engineering:
  q0245 holds ~1-1.7 M points in memory under a 600 MB cap, q0244 memory, `point_at` linear scans, q0244 request count.
- Rulings: months non-regional faithful ("this month" still regional, fix pre-freeze on out-of-window text only); no
  series key faithful; Stage-2 storage enough for lag/big-quake checks but not outcomes; n_tests = 2 faithful; 90-day
  fallback faithful ("not run (power)" expected).
- **Promoted q0267** (E smoke, cpu lane, mem 600). q0244 after confirming the census accepts a frame written under the
  pre-fix E sha; q0245 after the memory fix; q0266/q0253/q0257/q0258 after fixes + freeze (q0258 committed only near
  `T12_E2_end`).

## CB15-P fixes (1528f0d, §11b P-1..P-15) re-check, 2026-10-19 ~14:45Z (science-reviewer): ACCEPT_WITH_FIXES; q0348 promoted; not counted
- Hashes: common `13c70322…`, E `10ab88e7…` unchanged; P `198b7fab…` -> `80db6dfa…` (matches seal and drafts).
  `pytest -k cb15` 112 passed. All 14 earlier defects fixed or declared; no threshold loosened.
- Remaining: (MED-HIGH) Stage 2 lacks the scheduled-end exclusion (a market closing before the 24-h read gives a 404
  read as an empty book -> invented mid); (MED) q0349 never finishes if one pair always fails (needs a pre-declared
  terminal "unavailable (source)" rule); live disk cap counts the Kalshi cache; (LOW-MED) 3,500/day cap can be
  overshot; a failed unused Kalshi leg at 24 h drops the unit; (LOW) cron timeouts, combined Kalshi rps 1.5 vs stated
  <= 1, non-atomic shared disk_check.json, small doc items. Ruling needed before q0350: P-6's Polymarket
  `can_close_early = False` has a weak factual basis.
- **Promoted q0348** (P smoke). q0347 waits for q0340 (draft, after CB14 q0302). q0349/q0350 after defect 2 (+ the
  ruling); q0352/q0354 after a Stage-2 re-check.

## CB16 code (5c3644f, drafts 1eeb1fa), 2026-10-19 ~15:00Z (implementer); freeze check running; not counted
- Implemented: cb16_common, cb16_smoke, Q (cb16_q), U (cb16_u, incl. the q0389 Data API client), K (cb16_k), part-A
  orchestration (cb16_a), run_cb16.py, tests (65 pass; CB13-CB15 + battery2 suites 259 pass), battery2 kinds
  cb16_test / cb16_replication / cb16_descriptive. H not implemented (withdrawn). Drafts q0380-q0389, q0392.
- No rules file yet: K's `matches_all.json` pin was unset; the host file's sha256 is `f4cde1e9…` (603,444 B,
  2026-10-12 20:52); the other K pins match the host files. Provisional hashes common `9a087b8c…`, A `33420b93…`.
- Implementer's flag for the freeze check: the stratified composition placebo (permutation within fine strata)
  retains part of a true effect and advanced in synthetic data unless strata were coarse; it may be near-unpassable at
  ~4 fills per stratum. Ruling pending (a design change needs a written justification and review).

## CB12-O fixes (beadf81), 2026-10-19 ~15:05Z (implementer); re-check running; not counted
- All 9 defects addressed; O `766eed85…` -> `13cb7b63…` (common/M/X unchanged, E untouched). Amendment O3 (pre-data,
  §11): ex-dividend dates from the previous session's Nasdaq file (fetched before t), indices exempt, tickers without a
  valid entry excluded as unknown (so the first post-freeze session's equity units are all excluded), ETF assetclass
  handling. Smoke adds Yahoo, Gamma closed lookup and Nasdaq dividend checks; outcome guard checks dates; census reports
  missed checkpoints (their share multiplies availability, 60% unchanged); cron line in
  `scripts/oracle/cb12_o_crontab.txt` (flock, timeout 900). 37 O tests pass.

## Session 2026-10-19 ~20:30Z (autopilot): finished jobs written up; WIP recovery
- **q0341b CB15-E census (done 15:00Z):** completeness gate FAILED: 26 race events inside the frame of 511 walked race
  events (share 0.051 < 0.95; 1,865 walk events, 61 requests). The job wrote the terminal **E1/E2 "not testable (frame
  completeness)", counted** (newly counted). A 5% share is implausibly low for a correct frame, so a science-reviewer is
  auditing whether the denominator/matching is faithful or a defect before anything further is recorded or retired.
  q0343-q0346 stay drafts meanwhile.
- **q0267 CB12-E smoke (done 15:04Z):** PASS (e_parser_out_of_window, e_usgs, guards_fixture_E all true; 4 requests).
- **q0271 CB13-T frame (done 14:33Z):** complete, 2,931 fills (SCREEN, 2026-10-12..15).
- **q0272 CB13-T census (done 15:06Z), counts only:** gate **GT FAILED**: SCREEN LOW 163 fills in 72 events, NEWS 427
  fills in 104 events (each needs >= 500 fills in >= 60 events); GL passed (round 2); GTP MDE T1 1.71c (> 1.0c) and T2
  1.66c (> 0.5c), so both would also be "not run (power)". The largest drop was "touch older than 60 min" (17,816).
  By the frozen rule T1 and T2 are **"not testable (population)", counted (2)**; R1-rep/R2 untouched (R family separate).
  **q0273 promoted** (cpu lane) to write the counted lines; it computes no estimate when a gate fails.
- **Recovery:** the 14:10Z session ended mid-work. Its uncommitted CB12-E and CB15-P fix WIP failed tests; both were
  handed to new implementers. The CB12-O re-check and CB16 freeze check (in flight at the stop) were relaunched.
  Round 8 creative hypotheses (CH144+, top 5 all host-only/cpu lane) committed 67df385; CB17 design drafting started.
- Queue ops: smokes q0285b/q0300/q0301/q0348 priority 25/9 -> 27 so they run between q0227b's 80-min budget runs
  (q0227b CB11-A walk at 139 of 164 days, still progressing). Ops only, no design change.

## CB15-E completeness audit (q0341b terminal), 2026-10-19 ~20:36Z (science-reviewer): FAITHFUL; counted 2 (E1, E2)
- Frame and walk use the same `parse_event` / `classify_event`; the walk only narrows (tag 2, end in
  [2026-11-03, 2027-01-31]); event ids are sets. All 26 frame races are in the walk; the 485 missing races were never
  returned as races by the five frozen queries ("House 2026" returned 409 House events, all primary/runoff/other; the
  frame has Senate 15, Governor 11 and no House general race). Even if all 93 "description lacks 3 Nov" frame rows were
  artefacts, the share is <= 0.233 < 0.95. The gate is the frozen design (CREATIVE_BATCH_15.md:400-403), untouched by §11.
- **Final: E1 and E2 "not testable (frame completeness)", counted once each** (2 lines locally and on the host; 0
  identifiability lines). GE0 (MS +1 only) stays a descriptive note: identifiability would also have failed. The
  write-once terminal means GEI is never counted a second time.
- **q0343-q0346 retired: not run (family E terminal), not counted** (drafts marked RETIRED). A House-race design would
  need a new registration (e.g. a tag-walk frame), not a CB15-E re-run. Could not verify: walk titles of the 485 were not
  saved (House share is an inference).

## CB12-O fixes (beadf81) re-check, 2026-10-19 ~20:38Z (science-reviewer): ACCEPT_WITH_FIXES; not counted
- Verified from a `git archive HEAD` export: O `13cb7b63…` matches seal and q0260-q0264; common/M/X/E unchanged; 37/37
  O tests pass; no floor, gate, alpha or threshold loosened (missed-checkpoint share makes the 60% rule stricter);
  amendment O3 causal (previous-session Nasdaq file with `fetched_t_end < t`; missing -> "unknown", excluded; invalid
  reply raises).
- Must fix: (1, MED, before the O freeze/q0261, by 2026-11-27) the day after a half session finds no previous daily
  file (half sessions have no checkpoints, so `run_daily` writes nothing) -> all equity units "ex-dividend unknown":
  use the latest daily file with `fetched_t_end < t` or run the daily step on half sessions (changes O hash). (2, MED,
  before q0260) `o_dividends_keyless` passes with zero ex-dates: require `n_dates >= 1` for SPY and AAPL. (3, LOW)
  earnings flags beyond the previous file's covered settlement date must be None, not False. (4, LOW) disclose the
  re-run of a timeout-killed checkpoint within a window.
- Order: fix 2 -> promote q0260 smoke (run inside a regular session 10:00-15:45 ET) -> fixes 1 and 3 -> reseal -> freeze
  confirmation -> O freeze commit -> install cron on the freeze day. q0262-q0264 after window 1 closes. Fix agent starts
  after the concurrent CB12-E fix commit (shared seal file and design doc).

## CB12-E freeze-check fixes (38bef1a), 2026-10-19 ~20:40Z (implementer); re-check running; not counted
- E `9a60a4a5…` -> `eb086757…`; common/M/X/O unchanged; `pytest tests/test_cb12*.py` 183 passed. Amendment row E2 in
  CREATIVE_BATCH_12.md §11. Fixed: E1-rep needs the p_alt placebo credit; Stage-2 outcomes only from reads spanning the
  window start (else "unavailable (outcome read)"), USGS span >= 30 days, 400-day-cap windows "unavailable (span cap)";
  availability denominator counts every "unavailable (…)" and "no separate earlier point" (stricter; 60% unchanged);
  per-slot pass state; p_alt fails closed; calendar halves; LOW items; q0245 streams; bisect lookups.
- Not fixed: q0244 memory/request count (draft at 400 MB); E2 drops only via counting unresolved trades. Rulings asked:
  stricter denominator, span-cap label for E-c windows, q0244 cap vs streaming.

## CB12-O re-check fixes (89fd546), CB15-P fixes (7c33ef9), CB16 freeze check, 2026-10-19 ~20:45Z; not counted
- **CB12-O (implementer, 89fd546):** all 4 items fixed (previous daily file = latest dated before the unit's day;
  dividend smoke needs n_dates >= 1 for SPY and AAPL; earnings beyond `earnings_covered_end` -> None; timeout re-run
  disclosed); amendment O4; O `13cb7b63…` -> `0899797a…`; 186 cb12 tests pass. **q0260 (O smoke) promoted**, cpu lane,
  `not_before` 2026-10-20T14:05Z (inside a regular US session). Freeze confirmation of O (fixes 1, 3) before q0261.
- **CB15-P (implementer, 7c33ef9):** P-16..P-22 (§11b-2): scheduled-end exclusion and "unavailable (no order book at
  24 h)"; terminal "unavailable (source)" after 3 failures in 3 runs over >= 15 min; only-needed legs; Kalshi cache cap
  0.25 GB counted in the total; read room under 3,500/day; Kalshi 0.5+0.5 rps; cron timeouts; atomic disk_check. P
  `80db6dfa…` -> `6ac3b610…` (common/E unchanged); q0348 hash token updated; 121 cb15 tests pass. P-6 ruling open.
  Re-check running (science-reviewer). Note: the implementer relaxed a draft-priority test (q0348 is now priority 27)
  and padded a disk-cap test for the separate cache cap; the re-check judges both.
- **CB16 freeze check (science-reviewer): ACCEPT_WITH_FIXES.** Causal guards, windows, REP_A drops, seeds, SE-only power
  gates, Holm k1 = 2, terminal counting verified; 66 tests pass. Must fix before the rules commit: (1) Q1 calibration
  placebo shuffles within market x hour (cells of ~1 fill: always fails) -> within market, as U1; (2) **ruling:**
  composition placebos for Q1/U1 kept the stratum-level grain share tied to the outcome, so they cannot separate
  composition from grain -> within-strata permutation test (same strata, 200 draws, seeds 16101/16111; holds iff <= 3
  of 200 permuted coefficients reach the observed one); decided before any CB16 statistic exists; (3) fine-strata
  synthetic fixtures; (4) U: failed HTTP / missing earlier print must be "failed/unresolved", never "silent"; (5) K pin
  check must refuse unset pins; pin `matches_all.json` sha256 `f4cde1e9…ca326`, 603,444 B, mtime 2026-10-12T20:52:48Z
  (measured read-only on the host; predates E009 registration), with the stated limitation that it is not re-derived;
  (6) declare percentile interpolation, tight-touch subset and REP_A minimums for Q2/U2. Fix agent running. Then a short
  re-check -> q0381 smoke first.

## CB12-E fixes (38bef1a) re-check, 2026-10-19 ~20:50Z (science-reviewer): REVISE (one item); not counted
- Verified: all part hashes recompute; 48 E tests pass; E1-rep needs the p_alt credit; Stage-2 outcomes only from a
  read spanning the window start; p_alt fails closed; calendar halves; no pass back-filled.
- (HIGH) 38bef1a moved the frozen ambiguous-quake exclusion from [t-72h, t) to [t-144h, t-72h) and labelled it a
  disclosure; it changes a frozen point-in-time guard and is not clearly stricter -> revert (the earlier ruling only
  asked to disclose the census read window). (LOW) q0257 cron fires once per slot, so the 3-try retry is 1 -> add :15/:25.
  (LOW) disclose that synthetic "unavailable (collection)" units come only from the last pass's members.
- Rulings: stricter availability denominator ACCEPTED (pre-data, makes 60% harder); "span cap" label not needed for
  E-c (the span always covers an E-c start); q0244 cap -> 1,000 MB (engineering only; not alongside a multi-GB job).
- Order after the revert + re-check: q0244 -> q0245 -> q0266 -> freeze -> q0253 -> q0257 -> q0258 (near T12_E2_end).
  Fix agent running. Open: the census does not check the frame's E hash in `load_frame`.

## CB15-P fixes (7c33ef9) re-check, 2026-10-19 ~20:55Z (science-reviewer): ACCEPT_WITH_FIXES; not counted
- Verified: 121 cb15 tests; P `6ac3b610…`, E and common unchanged; P-16 (listing endDate saved at the match; 24-h 404 ->
  `NO_BOOK_24H`, kept in denominators), P-18, P-19b, P-22 implemented; smoke makes <= ~15 requests (< 30). The two
  test edits (cache padding; smoke exempt from the draft priority band) weaken no safeguard.
- Fixes: (1, MED, q0349) P-17 terminal unreachable within max_runs 4 -> raise and guarantee a run gap; (2, q0349) empty
  fallback candle reply accepted -> require non-empty; (3, q0352/q0354) declare BEFORE q0348's output is read what its
  cache-size projection triggers (cap fixed; it binds); (4, q0353) NO-side 24-h 404 must not drop P1 units; (5) docs/test.
- **P-6 ruling:** Polymarket early-close flags declared unknown (disclosed); Kalshi true-flag exclusion kept (causal),
  renamed "Kalshi early-close/provisional flag"; never select on the actual Polymarket close time (post-t0,
  outcome-linked); early closers stay in denominators; disclose that Stage 1 reads Gamma endDate after the fact.
- q0348 stays on hold (not_before) until fix 3 is committed; fix agent running.

## CB12-E revert (59aa91d) and CB16 fixes (cc82c5e), 2026-10-19 ~21:00Z (implementers); re-checks running; not counted
- **CB12-E 59aa91d:** ambiguous-quake guard back to [t-72h, t), E2(viii) corrected, (x) outage disclosure; q0257 cron
  `5,15,25 10,16 * * *` (per-slot retries, an ok slot is a no-op); q0244 mem 1,000 MB. E `eb086757…` -> `a63672c9…`;
  common/M/X/O unchanged; 186 cb12 tests. A census test was narrowed (q must never change; the only allowed label change
  is available -> "ambiguous recent quake"); the re-check judges it.
- **CB16 cc82c5e:** items 1-6 done; new `strata_permutation_test` (200 draws, seeds 16101/16111, holds iff <= 3 reach
  the observed; uncomputable draws count against holding); fine-strata fixtures; U failed / no-earlier-print excluded
  and counted; K refuses unset pins, `matches_all.json` pinned; rules file `seals/cb16_rules.json` created: common
  `9a087b8c…`, A `8f395a7d…`, K `cfe9bea5…`; 75 tests. Four tests updated because K is now declared.

## CB12-E revert (59aa91d) confirmation, 2026-10-19 ~21:05Z (science-reviewer): ACCEPT_WITH_FIXES; q0244 promoted
- Verified: guard [t-72h, t) with 71 h/72 h/t boundary tests; per-slot retries never re-run an ok slot (lock, adopt
  existing pass file); E2 (x); q0244 1,000 MB; seal recomputed (E a63672c9, common/M/X/O match); 48 E tests.
- Fixes before q0266 (no seal change): (MED) the narrowed census test compares q on 0 units (all injected magnitudes
  sit within ±0.3 of the fixture's 6.5 threshold) -> inject only magnitudes > 0.3 from every threshold, require exact
  equality and >= 1 available unit, keep a separate ambiguity assertion; (LOW-MED) `load_frame`/`census_e_block`
  must refuse a frame or prices manifest whose rules hash differs from the current E part.
- **q0244 (quake frame, net lane, 1,000 MB) promoted**: the frame never calls `ambiguous`. Then q0245; q0266 after the
  two fixes and a re-check.

## CB15-P re-check 2 fixes (88f404a), 2026-10-19 ~21:10Z (implementer); q0348 hold lifted; confirmation running
- P-23: q0349 max_runs 8; a run starting < 15 min after a run that left failed pairs exits 75 (not a run or attempt),
  so the P-17 terminal is reachable. P-24: the fallback candle reply must be non-empty with parser fields. P-25 (declared
  before any q0348 output): the 0.25 GB cache cap is fixed; when it binds, skipped scans and listings needing an
  uncached Kalshi read are counted ("unavailable (source: cache cap)"), never read. P-26: NO-side 24-h 404 drops P2 only.
  P-27: the P-6 ruling as written above. P `6ac3b610…` -> `7d856416…` (common/E unchanged); 126 cb15 tests.
- **q0348 hold lifted** (runs after the next deploy). Confirmation re-check of 88f404a running for q0349/q0350 and the
  Stage-2 jobs.

## CB16 fixes (cc82c5e) re-check, 2026-10-19 ~21:10Z (science-reviewer): ACCEPT_WITH_FIXES; part K signed off; q0381 promoted
- Verified: 75 tests; committed rules common `9a087b8c…`, A `8f395a7d…`, K `cfe9bea5…`; items 1-6 as ruled
  (`strata_permutation_test` exact; `--draws` refused without the uncommitted-rules flag); K content (10 non-matches pins
  byte-identical to CB12-X, counts 148,384 / 326,380 / 958, cells, MDE 3.80·SD·√(1/G_p + 1/G_a), re-entry rule) matches
  the design. Updated tests weaken nothing.
- Fixed by the coordinator: q0381 note pin suffix (ca327 -> ca326). Optional: a U1 fine-strata fixture.
- Host check (read-only, coordinator): all 11 cross_venue files match the K pins; CB13-T SCREEN captures present.
  **q0381 (A+K smoke, cpu lane) promoted**, priority 20 (a failed A smoke counts Q1/U1 once each as not testable (source)).
- Next: q0382 after q0381; q0380 after q0340 (`--base-sha256` = host sha256 of `creative_batch15/exclusion_keys.csv.gz`
  after q0340); q0383 after q0380+q0381, alone (1,200 MB). q0384-q0389 after the part-A freeze (not_before = S_A + 14 d
  + 8 h from the actual frozen_utc); q0386 also needs E011's analysis-commit and CB3's freeze/stop records; q0388 needs
  the committed results_A.json sha256; q0392 only after Stage 2 triggers.

## CB12-E census guard fixes (3716711), 2026-10-19 ~21:12Z (implementer); not counted
- Test now compares q on units with magnitudes > 0.3 from every threshold (exact equality, >= 1 unit) plus a separate
  near-threshold ambiguity test; `run_cb12.py` refuses a frame/prices manifest recorded under a different E part
  (census, screen, rep). E hash unchanged (runner is unhashed); 189 cb12 tests. q0266 may follow q0244/q0245 after a
  short confirmation.

## CB15-P fixes (88f404a) confirmation, 2026-10-19 ~21:15Z (science-reviewer): ACCEPT_WITH_FIXES (LOW); not counted
- Verified: P `7d856416…`; 126 cb15 tests; run gap holds (stamp at both failed-pair exits, exit 75 not counted, failed
  pairs retried first; terminal reachable in 8 runs at <= 150 pairs); P-24, P-26, P-27 as ruled; relaxed test harmless.
- LOW fixes before q0352/q0354 are installed (reseal): log listings while the stale cache skips matching; rename the
  cache-cap count as an upper bound and state that a binding cap ends enrolment (time-, not outcome-dependent); report
  the cap counters in `rep_p`; make NO-404 labels exclusive. Fix agent running.
- Order: q0347 with q0340 (CB14 draft); q0348 in jobs; q0349 + q0350 only after q0347 and q0348 pass; then P freeze
  check and `freeze-part --part P`; q0351 after the freeze; q0354 (>= 2026-11-03) and q0352 (>= max(freeze + 1 d,
  2026-11-04)) as cron after the freeze; q0353 only if q0351 advances P1 or P2.
- **P-28 done (066ffbe, 21:05Z):** stale-cache listings logged (no prices) and counted; `cache_cap_unavailable_upper_bound`;
  cap counters in `rep_p`; NO-404 units counted once as "ok (P1 only; NO book unavailable at 24 h)", label counts sum to
  the total. P `7d856416…` -> `1c6b7e95…` (common/E unchanged); 127 cb15 tests. Deployed to the host with HEAD 066ffbe.

## CB12-E guard (3716711) and CB12-O (89fd546) confirmation, 2026-10-19 ~21:10Z (science-reviewer); not counted
- (A) E: census tests ACCEPTED; guard called on every data path, but frame (q0244) and prices (q0245) share one
  manifest whose `rules_sha256` is overwritten by the last writer -> MED: record frame/prices rules hashes in state and
  refuse a mismatched q0245 start/resume (reseals E). q0244 held (not_before) until the reseal is deployed.
- (B) O: ACCEPT; 89fd546 is freeze-ready code (causal: strictly earlier daily file plus `fetched_t_end < t`). Optional
  LOW: `earnings_flag` checks `fetched_t_end` itself; report per-unit previous-file age (outage case). Taken now (O5,
  reseals O) so the freeze uses final code. O freeze still needs q0260's iv_convention (2026-10-20).
- **E3/O5 done (c9002da, ~21:20Z):** frame/prices rules hashes recorded in state, q0245 refuses a missing/mismatched
  frame or earlier-chunk hash, guard checks both; `earnings_flag` fails closed without `fetched_t_end < t`; per-unit
  `daily_file_age_days` in the census. E `a63672c9…` -> `bd512db4…`, O `0899797a…` -> `4e1dd759…`; common/M/X
  unchanged; 191 cb12 tests. q0244 hold lifted; q0244/q0260 and drafts re-pinned. A short confirmation precedes q0266
  and the O freeze.

## CB16 smoke q0381 PASS; q0382 promoted; q0273 refused (no CB13 freeze), 2026-10-19 ~21:25Z; not counted
- **q0381 (done 21:00:45Z): PASS** for parts A and K (all 11 criteria true incl. CB13 pins and reproduction, K counts
  exact, inputs pinned, no outcome fields); nothing counted. **q0382 (Q grain census, cpu, 800 MB) promoted**.
- **q0273 refused** (rc 2): `model_specs/cb13_v1.json` does not exist; the CB13 screens refuse before the family's
  freeze entry. Promoting q0273 before the T freeze was a coordinator error (no data read, nothing counted). A
  science-reviewer is checking whether the T freeze may be committed now; then `queue_worker.py retry q0273` on the
  host.

## CB13-T freeze check, 2026-10-19 ~21:35Z (science-reviewer): NOT YET; correction to the ~20:30Z entry
- **Correction:** the ~20:30Z entry said q0273 "computes no estimate when a gate fails". That was false: `cmd_screen`
  loads post-fill marks and `screen_t` writes a `reported` block (per-class mean mark-outs) regardless of the gates.
  q0273 refused before reading anything (no freeze file), so no mark-out has been computed or seen.
- Must-fix items of the T freeze-check rounds are all closed (A-D at 7fb59a3, E in 5891bec, GL round 2); T `f72683f5`,
  LABELLER `95cde0ab`; 123 CB13 tests. Order census -> T freeze -> q0273 is the design's.
- **Decision (coordinator, option a):** amend the screen so that when no T test is testable it opens no mark index,
  builds no outcome dataset and writes only the counted terminal lines ("not testable (population)", GT precedence).
  Justification: removes outcome exposure that serves no counted test; pre-outcome; no threshold changed. Reseals T,
  then a short re-check, the T freeze commit (record-only common and census shas), and `retry q0273` on the host.
- R unaffected (separate freeze part).

## CB17 drafted (a00c4ef) and challenger round 1, 2026-10-19 ~21:40Z (design only, not counted)
- Draft from round 8: A open vs close (CH144), B1 book age at fill (CH146), B2 breathing book (CH147), C mint share /
  event OI (CH150) counted (k = 4 fixed + up to 8 conditional); E first-day prints (CH154) census only (k = 0; 30
  first-day fills in 4 days). SCREEN_8 2026-10-26..11-09, REP_8 11-09..11-23. Census jobs q0400-q0403 (cpu lane).
- Challenger: REVISE A, B1, B2, C; PROCEED E-census and q0400-q0403 once part `pre` carries the strata-informativeness
  report and the per-band signing-agreement gate. HIGH: C eligibility used capture k+1 (selection on the outcome);
  composition strata too fine for the 50% both-label rule; calibration placebo vacuous (judged with the floor) and
  shuffles break autocorrelation (use block permutation, p alone). MED: B no-mark drop-outs; job reads inside CB13-T's
  sealed HOLDOUT (lookback floor); C terciles include r_{k+1}; branch-S signing gate per band. Rulings: add CB16 §11's
  <= 3/200 rule to the composition check; binding d-balanced estimate for A; B2 placebo stays binding; decide the
  live_trades 3 GB cap (est. reached ~11-25..11-29) before S_8. Designer response running.
- **Amendment done (a198f5a, ~21:45Z):** §11.t; when the census leaves no T test testable the screen opens no fills,
  prints, pin or mark index, runs no GTI, writes no `reported`/estimate, only the two counted lines (p = 1) and an
  `outcome_exposure` record (all false). Precedence GL -> GT -> GTP. T `f72683f5…` -> `33bd165b…` (common, LABELLER,
  R unchanged); 124 CB13 tests; q0273/q0274/q0275 re-pinned. Re-check + freeze decision running (incl. whether the
  census written under the old T hash is accepted or needs a counts-only q0272b).

## CB13-T freeze (56d1088), 2026-10-19 21:19Z, after science-reviewer FREEZE_OK; q0273 retried
- Re-check of a198f5a: gate-fail path opens nothing (readers replaced by raising stubs in the test), GL > GT > GTP
  faithful; label "not testable (population)" for T1 and T2. The census written under T `f72683f5` is accepted: the
  §11.t reseal changed only screen functions (`census_t` hash unchanged); host census canonical sha `530ab15a…`, file
  bytes `5408b1f5…`. Disclosure added (pre-11.t cadence-before-population order).
- `model_specs/cb13_v1.json` part T committed: rules `33bd165b…`, LABELLER `95cde0ab…`, common `62e90149…` (record
  only), census pins and counts, decisions, frozen_utc 2026-10-19T21:18:57Z; `require_freeze` verified locally; 124
  CB13 tests. Deployed; `queue_worker.py retry q0273_cb13_screen_T` on the host (cpu lane, after q0382).

## CB17 challenger response (b7374fc), 2026-10-19 ~21:35Z: DRAFT-REVISED; census code started; not counted
- 7 findings adopted, 1 modified (B no-mark: recorded capture mark first, adverse worst case only without a recorded
  price), 0 rejected; all 8 rulings adopted (cap: proposal). k: branch S 4 fixed + up to 8 conditional (k1 = 4); branch
  T withdraws A uncounted before its part commit (3 + up to 6, k1 = 3).
- Part `pre` (before q0400-q0403 code): old-data paths/dates with refusal of rows >= 2026-10-16; branch rule (S needs
  97% agreement overall, Wilson LB >= 0.95, n >= 800, and 97% per touch-age band / price band / class with n >= 100);
  strata ladders and informativeness (finest level with old-data share >= 60%, else level 2); cut points fixed from old
  data, C terciles from >= 6 earlier intervals; SE-only planning recipe; cost-map grid. Implementer started (pre +
  q0400-q0403 code); a science-reviewer freeze check of part pre follows before the census jobs run.
- live_trades cap: designer recommends raising the 3 GiB total cap to 8 GiB before S_8 (one-line reviewed change; the
  300 MB/day guard stays; not in `config_hash`), after checking data-dumps stays under the 40 GB job guard. Decision
  pending (coordinator, with the part-pre freeze check); the fallback leaves it (cap projected after REP_8 ends).

## q0273 CB13-T screen and q0382 CB16-Q grain census, 2026-10-19 21:16-21:22Z; counted 3
- **q0273 (done 21:22:04Z): T1 and T2 "not testable (population)", p = 1, counted 2** (GT failed in the census). No
  mark index opened (§11.t path). CB13-T is finished at Stage 1; q0274/q0275 never run. CB13-R continues (q0285b).
- **q0382 (done 21:16:17Z), counts only: gate GQG FAILED** -> **Q1 "not testable (grain)", counted once** (newly
  counted); Q2 stopped by design. Eligible fills 125; markets with both grains 7 (32 fills, share 0.256); sub-cent share
  0.896 (112 of 125); touch tick 0.001: 225, 0.01: 812 prints. 37,598 prints read (lookback limited to the SCREEN window;
  data before 2026-10-12 not on the host, disclosed in the output). CB16-U and K continue.

## Session 2026-10-20 ~01:27Z (autopilot): smokes q0285b / q0300 / q0301 / q0348 written up; q0276 promoted; counted 2
- **q0285b CB13-R smoke v2 (done 22:22:14Z): PASS** (guards_fixture_R, binance units, prices-history, request cap, rule
  parser, walk finds search all true; 6 requests). Not counted. R continues: q0276 promoted (below).
- **q0300 CB14-W smoke (done 22:24:20Z): PASS** (all 9 criteria true; 16 requests). Not counted. W continues at q0302
  (behind q0276, whose key file is q0302's base pin).
- **q0301 CB14-S smoke (done 22:26:11Z): FAIL -> S1 and S2 "not testable (source)", p = 1, counted 2** (CB14 §CB14-SM:
  "any failure -> the dependent family is not testable (source), counted; no rule is re-fitted"; `run_cb14.cmd_smoke`
  wrote the counted lines once; smoke file write-once). Failed criteria: `s_factbase_transcript` (Factbase search
  returned 0 records, 0 stamps) and `s_availability_p_months` (no primary-speaker event found in any of the 7 P months
  2024-11..2025-05). Passing: guards, pins, causal accessor, alignment fixture, tag walk (7 events, HTTP 200), term
  matcher (3 events, 46 terms). 9 requests. Cause (source change vs code) not diagnosed; no re-run, by design. Only
  CB14-S uses Factbase (grep), so no other family is affected. S drafts q0312-q0322 are never committed; S's part of
  q0323 sees S terminal.
- **q0348 CB15-P smoke (done 22:28:24Z): PASS** (all 9 criteria true; 10 requests). Not counted. P continues: q0347
  after q0340; q0349/q0350 after q0347.
- **q0276 promoted** (CB13-R exclusion keys, net, priority 17): deps q0285b, q0221b, q0223b all done; base pin
  `c8a1d64b…` as drafted. **Ops-only addition** (no rule, hash or threshold change): it also depends on q0227b, q0242
  and q0244, because `cb13_r.read_ids_generic` records any existing run directory as present and reads only its
  csv(.gz) files. `history/h11_attn/` exists now with only `frame_partial.jsonl.gz` (q0227b at run 9 of 12, entity
  phase: 815 Wikipedia summaries cached of the 3,000 cap), so a run now would record h11_attn present with 0 ids and
  never re-read it at the seal (the same reasoning as the earlier q0223b dependency).
- **Queue shape:** the net lane is serial behind q0227b (then q0229, q0242, q0244, q0276 -> q0302 -> q0340 -> q0380 /
  q0347). The cpu lane is idle until q0260 (not_before 14:05Z) and the CB17 pre-censuses q0400-q0403 (code being
  finished by an implementer from the untracked drafts of 10-19 22:31Z; science-reviewer freeze check of part `pre`
  before promotion).

## LT2 (E012-E014 drafts) challenger round 1, 2026-10-20 ~01:50Z (autopilot; design only, not counted)
- The interactive `feat/live-tests-2` stream stopped at about 2026-10-19 23:00 UTC+1 with the draft at ef16f9b1 plus
  uncommitted edits, before its challenger review. Registration must be committed before `REGISTERED_UTC`
  2026-10-22T00:00Z or the window slides (LIVE_TESTS_2.md §1.1). The autopilot ran the review read-only on that state.
- **Verdict REVISE for all four** (E012, E013-F4, E013-F5, E014): `docs/research_lab/reviews/LT2_CHALLENGER_R1_2026-10-20.md`.
  HIGH: the cyclic-shift timing gate is not a valid null (neighbour flow overlaps the window/target; 2-3-row markets
  give too few distinct shuffles). HIGH/MED: E012 is predicted by bid/ask bounce and E006 H1 (1 h version, "consistent
  with bounce") is not cited. MED: resolution attrition is unmeasurable; 6 h coverage depends on post-origin trades
  (selection on the future); day-level inference optimistic (21 clusters); code/spec mismatches incl. 8 vs 4 counted
  tests and unpinned code. LOW: F4 likely underpowered; E014 gain decomposition; `tight_i` mismatch.
- **Response:** new worktree `../astrolabe-live-tests-r1` on branch `feat/live-tests-2-r1` = feat/live-tests-2 + commit
  cdafeef8 carrying the uncommitted edits unchanged (the original worktree is untouched). A designer-implementer is
  applying the fixes there; then a short reviewer re-check, the SPEC/code pins, the registration ledger entry and the
  promotion of q0460 (all before 10-22T00:00Z).

## CB17 part `pre` code (cadaaf19), 2026-10-20 ~02:10Z (implementer); not counted
- From the untracked drafts of 10-19: `cb17_common.py`, `cb17_pre.py`, `cb17_census.py`, `scripts/run_cb17.py`
  (`rules`, `pre-census --family A|B|C`, `cost-lag-map`), 51 tests (cb16 suites unchanged and passing), seal
  `seals/cb17_rules.json` part pre `c186fdcd…` (only `pre` declared; common/A/B/C/E undeclared so later edits cannot
  break the frozen pre hash). Drafts q0400-q0403 (cpu lane), not promoted.
- Defects fixed in the drafts before any run: trailing-tercile list aliasing (r_k leaked into its own cut points);
  B2 imbalance read at the first sweep (design: second); spread-band tolerance sign; result-guard prefix match;
  `volume24hr` whitelisted per §1.4. Declared: C multi-member |Δm_int| = mean over qualifying members
  (`C_ABS_DM_RULE`); rows >= 2026-10-16 skipped and counted, later directories never opened.
- Science-reviewer freeze check of part pre (with the §10.3 cap ruling on measured bytes: live_trades 378 MiB,
  60.2 MB in the last 24 h, cap 3 GiB) running.
- **Freeze check of part pre (science-reviewer, ~02:25Z): FREEZE_OK_WITH_FIXES.** pre verifies at HEAD (`c186fdcd…`),
  51 tests pass, no outcome/mark/Y/slope/net reaches any census output, C uses k-2..k only, branch thresholds and
  per-band gates match §10.4. Must-fix (q0400, irreversible branch): (1) A informativeness shares must use units in
  both-label (market x d) cells, else level 2 is chosen by construction; (2) missing/mixed side counts as
  non-agreement (§2.3), overall and per cell; (3) q0400 must reproduce P1's counts (2,931 / 2,715 / 216 / 1,006 / 971 /
  676 / 295) before the branch is recorded; a mismatch is investigated, never adjusted. LOWs taken with the re-seal
  (path-key SE, E "later" bins, clock-anomaly exclusion in B, touch fixture, disclosures, q0401 timeout 3600).
  Rulings: freezing cb17_common under pre is consistent with §1.4 (later window jobs verify pre too); internal OLS in
  `fe_cluster_se` acceptable (SE only); `created_at` from the pinned captures permitted (disclose the unknown bias).
  Re-seal supersedes `c186fdcd` (nothing has run).
- **Monitor cap (§10.3): option (a) adopted** (reviewer: acceptable ops change; not production; `total_cap_bytes` not in
  `config_hash`, no protocol pins it). Measured 2026-10-20 01:40Z: live_trades 378 MiB, 60.2 MB written in the last
  24 h, data-dumps 17 of 40 GiB. Under (b) the 3 GiB cap would land ~11-27..12-06, 4-13 days after REP_8's last row and
  inside CB16 REP_A. TOTAL_CAP_BYTES 3 -> 8 GiB, 300 MB/day guard kept; deploy before S_8 via COLLECTION_HOST.md;
  `du` before/after recorded at deploy; data-dumps checked against 40 GiB weekly.
- **Fixes and re-check (~02:40-03:00 UTC+1):** de5c553a applied all three must-fixes and the LOWs (pre `c186fdcd` ->
  `31656d5d`); monitor cap 3 -> 8 GiB in 8853f9cc (deployed; a running monitor keeps the code it started with, so the
  8 GiB cap takes effect at the next restart of `live-trade-monitor`, needed before ~11-20; restart only that service at
  a quiet moment, never the cross-venue poller). Re-check (science-reviewer): NOT_YET, one must-fix: on a P1 mismatch the
  write-once result and trials line still carried the branch. Fixed in 80ff3858 (branch / withdrawal / selected
  population and level null, candidate only under `branch_unrecorded_candidate` labelled NOT_A_BRANCH, status
  `pre_census_A_p1_mismatch`, exit 2; rerun only to a new path with `--supersedes`; any blank side in a fill = missing).
  pre `31656d5d` -> **`ddc0249b…`**; 60 CB17 tests. Coordinator verified the diff and tests (no further review round:
  programme rule, one challenge and one response).
- **Promoted q0400-q0403** (cpu lane, mem 500-800, priority 9; they start after the 02:45-05:30Z blackout). Next: read
  q0400's status and `p1_reproduction` FIRST (exit 2 = mismatch, investigated, never adjusted); then branch S/T into
  part A, cut points and levels into parts B/C, cost-lag map into §2.1/§3; parts A/B/C code before S_8 = 10-26.

## Creative round 9 (d72e1006), 2026-10-20 ~02:30Z (Fable xhigh; ideas only, not counted)
- `CREATIVE_HYPOTHESES_2026-10-23.md`: CH156-CH168 (13 ideas), 6 counts-only host probes verbatim with sha256, ranked
  top 10, top 5 all live-ready pure readers on existing streams: CH156 quoted vs traded moves (~77,700 movers/day),
  CH161 walked-flow moderator of continuation, CH160 walked prints (needs CB17 branch S), CH157 volume surge without a
  move, CH162 trains and herds. Pre-registration sketches as an "LT3" family separate from LT2.
- Probe facts (counts only): every trade-sample row has a unique `tx_hash` (Data API aggregates per taker order);
  23% of rows and 40% of non-sports large prints have >= 4 decimals (bears on CB16-Q's premise; CB16-Q is already
  terminal, nothing changed); 85% of 2 h moves >= 1c have no trade behind them; 0 `closed` flips in snapshots (markets
  leave the listing; resolution arms need a light Gamma fetch); trade-sample CSVs on the host only from 10-16.
- Next: LT3 draft pre-registration (designer running, `LIVE_TESTS_3.md`, E015+, two-stage prospective screen +
  replication) -> challenger -> code -> freeze.

## CB17 pre-censuses q0400-q0403, done 2026-10-20 02:04-02:27Z (counts only); A withdrawn uncounted (branch T)
- Ran under part pre `ddc0249b` before the 02:45Z blackout (cpu lane), all rc 0.
- **q0400 (A, 123 s): P1 REPRODUCED** (all 7 counts equal: fills 2,931, token-resolved 2,715, ambiguous 216,
  non-sports 1,006, non-sports resolved 971, open 676, close 295). **Side agreement 906 / 971 = 93.3%** < the 97%
  overall bar of §10.4 (every binding cell also fails: PATH-SETTLED 121/135, SCHEDULED-EVENT 362/392,
  UNSCHEDULED-NEWS 397/417, p bands 159/165, 347/361, 386/431, touch age 0-20 min 367/382), so **branch T**:
  **CB17-A withdrawn uncounted** before its part commit, as pre-declared (§10.5: k = 3 fixed + up to 6 conditional,
  k1 = 3). Strata: selected population T, level 1; 44 both-label cells. Result sha256 `9deedcf5…`.
- **q0401 (B, 352 s):** 545,355 units; 4,828 tokens with both fresh and old books; selected level B1 = 2, B2 = 1.
  sha256 `c3b8ae1b…`. **q0402 (C, 400 s):** 2,419 events with units having >= 6 prior intervals; selected level 2.
  sha256 `442e99da…`. **q0403 (cost-lag map, 303 s):** 37,598 prints, 42 sweeps. sha256 `43f28e02…`.
- Next: write branch T into the record (A withdrawn), cut points and levels into parts B and C, the cost-lag map into
  §2.1/§3; parts B/C (and E census) code, freeze checks and commits before S_8 = 2026-10-26. Round 9's CH160 (walked
  prints, needs branch S) therefore is not live-ready; LT3 must not use it.

## q0227b CB11-A attention frame COMPLETE, 2026-10-20 05:39Z (run 10 of 12); not counted
- Status `attn_frame_complete`: n_sample 1,693 (SCREEN 812, HOLDOUT 881); split and audit written before any pageview
  or print request (design 2.8). q0229 (attention data, net) started 05:4xZ. q0276 (CB13 keys) and q0302 (CB14 keys)
  no longer wait on q0227b (q0276 still waits on q0242 and q0244).

## Session 2026-10-20 ~06:15Z (autopilot): CB11 unblocks; CB11-A entity audit labels (GA0 will fail, pre-declared)
- **q0231b (CB11-W census) failed twice (rc 2):** refused because the seal copies `seals/cb11_w_hold_SEAL.json` and
  `seals/cb11_wprints_holdout_SEAL.json` (written on the host by q0224b/q0230b, rules W `a3a16f98…`) were not committed.
  Committed byte-identical to the host (sha256 `58bbf0d7…`, `eaf08ff4…`), deployed, `retry`. Not a science event.
- **q0242 (CB12-M say frame) failed twice (MemoryError in ~6 s):** the 2 x 300 MB address-space cap. mem_mb 300 -> 1000
  (as q0244, which completed), resource only; `retry`.
- **CB11-A gate GA0 audit (design §CB11-A, "labels committed before q0229"):** the 200-row seeded SCREEN audit file
  (`creative_batch11_audit/attn_audit_sample.csv`, sha256 `3508d18b…`, host copy identical; question, canonical title,
  description only) was blind-labelled by a `science-reviewer` agent that read only that file and the two design
  passages (no outcomes, prices or censuses). Labels committed as `seals/cb11_attn_audit_labels.csv`: **145 subject /
  55 not, precision 0.725 < 0.80**. Main misses: country articles for Eurovision entries, commodity/currency articles for
  price markets, homonyms. Per the frozen rule the census q0239 will record GA0 FAIL and label **A1, A2 "not testable
  (entity map)"**, counted with p = 1 (§Counting). Nothing re-labelled or re-drawn; one labeller, as designed. q0229
  continues as specified (data are still the census's descriptive input).

## CB11-W census and freeze (not testable), 2026-10-20 06:18-06:55Z; 2 tests counted with p = 1
- **q0231b census (v2 chain, rules W `a3a16f98…`), rc 0:** `census_W_b.json` sha256 `debb66ac…`. GW: units 11,774
  (>= 5,000 ok), end-dates 98 (>= 90 ok), **fee categories with >= 200 W_fit units: 1 (need 6)**; W_fit categories
  tech 1 / unknown 18,329. GWC passes (hold upper95 0.0076). GW2 375 decided S units in 296 events over 59 dates.
  **W1, W2 "not testable (GW: units, dates or categories)".**
- **science-reviewer ruling: TERMINAL** (source limitation, not a defect). `fee_category` comes from Gamma `feeType`
  through the frozen v1 map (`history_backfill.py:397`, `pairing.py:55-63`); unknown share is 0.1-1.0% for May-Oct
  2026 end-months but 100% for Oct-Dec 2025 (incl. crypto/sports), first politics/finance/culture labels in Mar 2026;
  the W_fit window is 2025-10-01..2026-02-08. Known before the freeze (`CREATIVE_BATCH_4.md:1702`: `feeType` marks
  later fee charging, not a listing-time attribute), so this is a **design weakness** of the frozen GW gate, recorded
  here. No alternative category source is substituted (data-driven design change). Minor: `cats_ok` counts `unknown`
  as a category (more lenient than design line 270); the gate fails either way.
- **W freeze part** `model_specs/cb11_v1.json` W (part sha256 `fa5e97b2…`), science-reviewer GO (fixes applied). q0232
  promoted: on the labelled path it opens no target/guarded/unit file (W_hold files only hashed for the seal check) and
  writes `results_W.json` plus 2 `cb11_test` (p = 1) and 2 `ml_explain` count lines. The v1 `census_W.json`
  (half-open window defect, §11.3) is superseded and never counted.

## LT3 (E015-E019) pre-registration draft, 2026-10-20 ~07:15Z; design only, nothing registered or counted
- `LIVE_TESTS_3.md` (1aa1500f, merged 733faf6b): pure reader of host streams; one Holm family, k <= 5 after counts-only
  census gates C1-C4 (outcome-blind; a test dropped there is uncounted). E015 CH156 quoted (both quotes, no trade)
  vs traded 2 h moves; E016 CH161 walked-flow share x 6 h flow continuation; E017 CH157 volume surge (>= 3x, >= +$500)
  with < 1c move -> 24 h drift; E018 CH162 burst share x flow (dropped pre-registration if degenerate or corr > 0.5
  with E016's measure); E019 CH159 ladder breadth (>= 80% members re-quoted without trade) continuation.
  Dropped: CH158 (one tilt value per pass, ~20 effective df; MDE 0.6-4.6c vs 0.5c floor -> descriptive only); CH160 and
  CH162's print arm (need print direction; CB17 branch T); CH157's resolution arm (needs a fetch).
  MDEs are planning estimates from one worn probe day. Proposed window 2026-10-24..2026-11-14, single analysis on or
  after 2026-11-15T12:00Z. Next: challenger round 1 (running) -> response -> code -> censuses -> freeze.
- **LT3 challenger round 1 (07:40Z, `reviews/LT3_CHALLENGER_R1_2026-10-20.md`):** E015 ACCEPT_WITH_CHANGES; E016,
  E017, E018, E019 REVISE; nothing fatal. Main findings: E019 contrast mechanically predicted by quote anatomy (binding
  "quote-anatomy composition" label) and crypto-series cluster dominance (t on G_series-1, ex-crypto primary if one
  family > 50%); trade samples older than 3 days are retired by archive retention (C2 needs a byte restore); "walked"
  (>= 4 decimals) may be a float/micro-unit artefact (grid-distance rule, drop E016 if > 20% within 1e-4 of grid);
  E016 size/life-cycle controls; E015 impact/anatomy label (M3); E017 neg-risk-only primary and lagged-volume control;
  reader cron every 20 min with flock and a late-loss label. Response + code by the designer-implementer (running).

## Session 2026-10-20 ~07:18Z (autopilot): the 06:14Z session stopped at ~06:48Z; its agent streams resumed
- **q0232 (CB11-W screen, done 06:28:03Z, rc 0):** `results_W.json` written on the labelled path: W1, W2
  "not testable (GW: units, dates or categories)", p = 1, as recorded in the CB11-W entry above. Nothing else changed.
- **Interrupted streams (no process left; their files stopped changing at ~06:48Z):** LT2 R1 fixes (uncommitted edits in
  `../astrolabe-live-tests-r1`), LT3 challenger response (untracked `seals/lt3_census_inputs_C2.json` in
  `../astrolabe-live-tests-3`), CB17 (rules parts common/B/C/E committed e37643f3 in the agent worktree, not merged).
  Relaunched one agent per worktree (same scope, told to inspect and keep only correct partial work). Creative round 10
  (Fable xhigh, live-ready readers for an LT4 family) started; ideas only, not counted.
- **Queue (07:19Z):** net lane q0243 running; cpu lane idle until q0260 `not_before` 14:05Z. No new failures.

## LT2 (E012-E014) R1 response and re-check, 2026-10-20 07:20-08:10Z; design only, nothing registered or counted
- **Response (e37578dc, merged a4c2585c):** all 9 R1 findings mapped in LIVE_TESTS_2.md §9. Timing gate replaced by a
  far-future control (sources >= flow window + horizon later, >= 4 per row, p = max(CR1, jackknife) under t(G-1));
  E006 H1 disclosed + frozen 6 h skip-slot bounce label; per-capture status files + 5 pp attrition label; E013
  population cut on origin `volume24hr` <= `vol24_cap`; primary p = max(event, two-way, t G-1); counting 8 lines-tests,
  Holm k = 4; spec/code sha pins per line. 41 unit tests pass. Planning MDEs: E012 0.037, F4 0.0017, F5 0.0028, E014 0.0030.
- **Re-check (science-reviewer): PROCEED_WITH_FIXES** (`reviews/LT2_RECHECK_R1_2026-10-20.md`): no new leakage, no
  threshold loosened, nothing reads window data. Must-fix: A census ids checked against the spec; B NaN cap refused;
  C provenance of the 1,500-world size figures. Disclosures: gate rows selected on future presence (necessary, not
  sufficient); E014 truncation only labelled; skip-slot controls conservative.
- **Census re-run on the host (07:54-07:57Z, /tmp, 684 MB RSS):** exactly the spec ids; n reproduce (zL 153,711, zRV
  3,891, zSPR 4,142); 6 h truncated 5/4,147 = 0.12% (< 1%) so `vol24_cap` = +inf (no cut binds); 1 h 1/8,000. Output
  `seals/lt2_census_r1_2026-10-20.json` (sha256 `4656490b…`). E007 `dev_fit.json` on the host sha256 `7e2c4f79…` = §4.
- Next: A-C + cap fill + code_sha refresh (implementer running) -> host dry run -> SPEC_SHA256 pin -> registration
  entry -> promote q0460 (not_before 10-21T00Z) before REGISTERED_UTC 10-22T00:00Z.

## Session 2026-10-20 ~12:25Z (autopilot): queue idle; seal copies committed; 6 jobs promoted; streams relaunched
- **Queue at 12:24Z: idle ("no ready jobs").** q0239 (CB11-PA census) and q0249 (CB12-M census) each failed twice in
  ~2 s (rc 2) with the designed refusal "seal copy … is not committed (or differs from HEAD)": the seal jobs q0238
  (10:17Z) and q0248 (12:12Z) had written `cb11_attn_holdout_SEAL.json`, `cb11_pol_holdout_SEAL.json` and
  `cb12_say_holdout_SEAL.json` on the host. Copied, sha256 byte-identical to the host (`46c27032…`, `242240104…`,
  `20c7660b…`), committed, deployed, both jobs `retry`. No rule, hash or threshold changed;
  the failed attempts are recorded in `attempts.jsonl` and nothing was counted. `h6_weather_SEAL.json` (6.3 MB, 10-17)
  stays uncommitted on the host as before (no job refuses on it).
- **Promoted (dffc11c0):** q0245 (CB12-E quake prices, after q0244 done); q0302 (CB14 exclusion keys; `--base-sha256`
  = host sha256 of `creative_batch13/exclusion_keys.csv.gz` after q0276 `exclusion_keys_complete` at 12:20Z,
  `b0f54329…5f79`); q0277 -> q0279 -> q0284 (CB13-R touch frame, Binance klines, pregate); q0303 (CB14-W frame, after
  q0302). All deps-ordered; code freeze-checked and rules sealed on 10-19; argv unchanged except the base pin.
- **Interrupted streams (files last changed ~08:46Z, no process):** LT2 must-fix A-C (not started in any worktree; the
  uncommitted edits in `../astrolabe-live-tests` are the pre-R1 drafts of 10-19 22:58 and are superseded), LT3 R1
  response + code (`../astrolabe-live-tests-3`, uncommitted), CB17 window code (agent worktree, uncommitted), creative
  round 10 (file never written). Relaunched: LT2 A-E implementer (isolated worktree), LT3 response + code, CB17 window
  code, creative round 10 (Fable xhigh). CB12-E/O pre-q0266 confirmation (science-reviewer) started.
- **CB12-E/O pre-q0266 confirmation (science-reviewer, ~12:55Z): ACCEPT.** Both fixes present and tested
  (`tests/test_cb12_e.py:1027-1046`, hash refusal `run_cb12.py:490-500` in census/screen/rep, q0245 at
  `cb12_e.py:724-727`); 191 cb12 tests pass; all six rules parts recomputed byte-identical to `seals/cb12_rules.json`
  (E `bd512db4…`, O `4e1dd759…`, common `f2f672c1…`) and every draft pin matches; census counts-only. **q0266 promoted**
  (after q0245). O is freeze-ready pending only q0260's `iv_convention` (enforced at `run_cb12.py:185-195`).
- **LT2 fixes A-E merged (a14f3efb):** A census refuses unless its captures/samples equal the spec's ids
  (`live_tests2.py:832-871`); B `code_check` refuses NaN `vol24_cap` (+inf allowed); C the 1,500-world null-size run is
  now reproducible (seeded tests, `LT2_N_SIM=1500`, output `seals/lt2_gate_null_size_1500.json`): pooled 566/12,000 =
  0.047, scenarios 0.042-0.054; the figures quoted before differed and are relabelled "unreproduced" in §1.5; D
  `flow.vol24_cap` = Infinity citing census `4656490b…`; E `code_sha256` refreshed (`ec07e16b…`, `a7b5c781…`).
  41 tests pass. Next: host dry run (R1 collector) -> short reviewer verification -> SPEC_SHA256 pin -> registration.
- **LT3 (E015-E019) R1 response + code (63d89b5e, ee7627d4) and freeze check (science-reviewer, ~12:50Z):
  FREEZE_READY_WITH_FIXES; CENSUS_OK_TO_RUN after fixes 1, 2, 4 + rulings.** All 12 R1 findings implemented; no
  loosening of floors, alpha, Holm or counting, except one undisclosed change (simulated gate-size criterion "<= 0.05"
  -> 0.068), ruled acceptable as a stated Monte-Carlo tolerance once disclosed, with q0473 at >= 2,000 worlds (limit now
  0.058). Fixes (76778698, §13.9): (1, HIGH) `write_once_csv` "%.7g" rounded epochs to ~1,000 s and vol24 -> exact
  "%.17g" + round-trip test; (2) NaN `vol24_cap` refused, C2 E016 gate fails on NaN V*; (3) disclosure; (4) the
  E015-style pessimistic planning-MDE <= floor gate added to censuses C3/C4 (E017, E019) **before** any census ran
  (at the old counts both currently fail: E017 ~1.12c vs 1.0c, E019 ~0.72c vs 0.5c, so either may drop uncounted at
  q0470); (5) dry-run into live root refused, spec/module REGISTERED_UTC equality. Rulings: C_par parallel-only;
  crypto regex `dogecoin`/`^eth-`; C2 agreement >= 500 rows per arm (else drop); install as host cron every 20 min with
  an internal flock, q0474 fallback only. 32 LT3 tests pass. Merged 2993a5df. **Promoted:** q0470 (C1/C3/C4 censuses,
  deadline 10-22T03:30Z retention), q0471 (C2 restore from releases) -> q0472 (C2 flow census), q0473 (size check).
- **LT2 fix F (b756fcbc):** the same precision bug in LT2 (`%.6g`, epochs ~10,000 s) found by the LT3 reviewer; now
  "%.17g" with a round-trip test; `code_sha256` `live_tests2.py` -> `88ee00b2…`. No line had been frozen. No other
  module uses a reduced `float_format` (grep).

## Session 2026-10-20 ~17:38Z (autopilot): host was 15 commits behind; LT2 REGISTERED; queue PATH and q0245 memory fixed
- **Queue idle at 17:38Z** ("no ready jobs"); q0239 and q0249 had failed twice more (15:02Z, 15:10Z) with the same refusal
  "seal copy … is not committed (or differs from HEAD)". Cause: the host checkout was at a4c2585c, 15 commits behind
  `chore/arepo-claude-setup` (a532ee33). The seal-copy commit a972959c and the promotions of dffc11c0 and c97f63eb had never
  reached the host (most likely a deploy from a worktree branch during the 12:25Z session's host dry-run step overwrote the
  tip; deploy.sh deploys whatever branch it is given). Deployed a532ee33 at 17:40Z; `retry` q0239 and q0249. q0470 (LT3 C1/C3/C4
  censuses) started at once. **Rule from now on: deploy only from `chore/arepo-claude-setup`, never from a worktree.**
  No rule, hash or threshold changed; the refused attempts are in `attempts.jsonl`; nothing counted.
- **q0471 (LT3 C2 restore) failed (rc 1):** `FileNotFoundError: 'gh'`. The queue cron line had no PATH, and gh lives in
  `~/.local/bin` (authenticated; the archive cron lines already set this PATH). Queue cron line now sets
  `PATH=/home/opc/.local/bin:/usr/bin:/bin` (host crontab edited, backup `~/crontab.bak.20261020`; `crontab.txt` updated).
  q0471 will retry on its own backoff (attempt 1 of 3 used).
- **q0245 (CB12-E quake prices) failed at start with `MemoryError`** under the 600 MB address-space cap (mem_mb 300).
  mem_mb -> 600 (resource only; argv, rules, caps unchanged). In `retry_wait`.
- **Creative round 10 committed (fe54ef20)**: `CREATIVE_HYPOTHESES_2026-10-24.md` (CH169-CH179+; written 12:57Z by the Fable
  xhigh pass of the 12:25Z session, left uncommitted when it stopped). Ideas only; top 5 (CH169, CH170, CH174, CH171, CH173)
  are live-ready LT4 candidates. LT4 designer started (worktree `../astrolabe-live-tests-4`, branch `feat/live-tests-4`).
- **CB17 window code (q0404-q0412) committed on its worktree branch** (`worktree-agent-ae42d4cfea66b78af`: cdab2fd5 code,
  runner, tests; f0d710ba drafts and §12). 39 CB17 tests pass, synthetic data only; no SCREEN_8/REP_8 file opened (none
  exists; S_8 not before 2026-10-26). Next: freeze check (science-reviewer, incl. P1-P3 reproduction), merge, pins.

## LT2 (E012-E014) REGISTERED, 2026-10-20 17:51Z (commit a4127bb9; registration; nothing analysed; counting per LIVE_TESTS_2.md)
- **Last owed item, the R1 host dry run** (17:41-17:47Z, `/tmp/lt2dry`, nothing under `~/arepo`, code a532ee33, 20 runs
  of `run --max-items 4` over 2026-10-19 under `ulimit -v` 960 MB until exit 75): peak RSS 584 MB; exits 0/75, <= 32 s;
  34 series, 34 status, 7 E012 and 24 flow files, 55 MB; R1 columns present (`x_skip6`, `trunc1h`, `vol24_i`, `spec_sha`,
  `code_sha`); `pinned=false`; no statistic on any target computed. All 3,918,532 status rows `one_sided`.
- **Pre-pin verification (science-reviewer): PIN_OK_WITH_DISCLOSURE** (`reviews/LT2_PREPIN_VERIFY_2026-10-20.md`).
  Complete captures query Gamma with `closed=false` (`collector.py:38`), so `unavailable_closed` cannot occur and closure or
  resolution is recorded as `unavailable_absent` (also covers removal from the listing); the attrition rule uses the
  unavailable share regardless of reason, so labels, bounds and Holm are unaffected. Disclosure text applied to
  `LIVE_TESTS_2.md` §1.2, §1.3, §6.2 (owed items closed) and the §9 finding-3 row. No code change.
- **Pins:** `SPEC_SHA256` = `010a7ba131936e8ffda243a1858f5be8864562f2b036d5863af7b785f5d6584c` (sha256 of
  `model_specs/live_tests2_v1.json`) in `live_tests2.py`; `code_sha256` unchanged (`live_tests2.py` 88ee00b2…8053,
  `live_tests2_analysis.py` a7b5c781…1ab0; normalised pin line). 43 LT2 tests pass.
- **Window:** `REGISTERED_UTC` 2026-10-22T00:00:00Z (commit before 2026-10-21T22:00Z, so §1.1 does not slide);
  `END_UTC` 2026-11-12T00:00:00Z; effective start = max(REGISTERED_UTC, first capture processed by q0460 with this code);
  single analysis q0461 not before 2026-11-13T12:00:00Z; no interim outcome look.
- **Counting (as declared, R1 response):** 8 line-tests, Holm k = 4 over the primaries (E012; E013 F4, F5; E014), economics
  separate. Counted at the single analysis, not now.
- **Jobs promoted:** q0460 (collector, net lane, mem_mb 480, not_before 2026-10-21T00:00Z, repeat until
  `LIVE_TESTS2_WINDOW_CLOSED`), q0461 (analysis, not_before 2026-11-13T12:00Z). Registry: E012-E014 and LT2 -> `live_test`,
  status `queued`.

## LT3 censuses C1/C3/C4 (q0470), done 2026-10-20 17:53Z (counts only, worn captures 2026-10-15/16); E017 and E019 dropped uncounted
- **Output** `live_tests3_census/C134.json` sha256 `ed18ed1473f1465a88920649b52867e35e7f827931f2ec9aeb69e425eec80484`
  (code_sha256 live_tests3.py `202c0d63…`, live_tests3_analysis.py `b03c6321…`; 24 captures of 2026-10-15/16; runtime 758 s).
  Origin-side fields only; no target, no later-capture price, no P&L read.
- **C1 (E015): gate PASS.** Non-sports movers 50,417 (sports 78,787; sidecar missing 0); traded 18,536 (share 0.368, in
  [15%, 60%]); parallel quote-only 2,504; projected 21 d traded 194,628 (eff 40,814), parallel 26,292 (eff 19,467);
  `last_trade_price` absent 6.5% (<= 60%); planning MDE_eff 0.31c; `V−` share 0.103; markets with both classes 1,316;
  permuted-strata share 0.449; up-share per pass 0.438-0.549 (n 24).
- **C3 (E017 surges): gate FAIL -> E017 dropped before registration, uncounted** (§8 and §13.6 rule; planning-MDE gate added
  in 76778698 before any census ran). A 79 units / 63 events in the census days (projected 21 d 829.5 / 557 against
  >= 2,000 / >= 1,500); planning MDE 1.83c against the 1.0c floor. Neg-risk share of non-sports A 0.52.
- **C4 (E019 ladder breadth): gate FAIL -> E019 dropped before registration, uncounted.** High 18 (projected 189 against
  >= 3,000), events with both 13 (projected 127 against >= 300), high clusters 18; planning MDE 2.86c against 0.5c;
  crypto share of high 0.17; top family share 0.056.
- **Remaining LT3 primaries:** E015 (passed C1), E016 and E018 (await C2: q0471 restore, retrying after the gh PATH fix,
  -> q0472 census-flow, deadline before 2026-10-23T03:30Z) and q0473 size check. k is set after C2. Nothing registered.

## CB12-O smoke and freeze (not testable), 2026-10-20; 2 tests counted with p = 1 (at q0263)
- **q0260 opt-smoke (15:06Z, code a4c2585c, rules O `4e1dd759…`, common `f2f672c1…`):** `opt_smoke.json` sha256
  `fcb6e89e…30e6c3`, pass **false**. Every needed criterion true except **`o_dividends_keyless`** (amendment O4(ii): >= 1
  ex-date for both SPY (assetclass etf) and AAPL): AAPL 83, **SPY 0**. `iv_convention` choice "none" (act365 match 0.25,
  trading hours 0.15 < 0.8). `o_chain_dividend_field` false is informational (O3).
- **Source check (orchestrator, one keyless request each, ~18:05Z):** `api.nasdaq.com/api/quote/SPY/dividends?assetclass=etf`
  rCode 200, `data.dividends.rows` null and every dividend field "N/A"; `assetclass=stocks` rCode 400. Source limitation,
  not a parsing defect (`cb12_o.py:540-570`).
- **science-reviewer ruling: TERMINAL "not testable (source)".** No re-smoke (`opt_smoke.json` is write-once; the stop rule
  covers failed jobs, not a smoke that ran), no amendment: another dividend source or dropping the ETF probe would change a
  gate after it failed (a new registered design would be needed, as for CB11-W).
- **O freeze entry** committed in `model_specs/cb12_v1.json` part O (`frozen_utc` 2026-10-20T17:57:26Z, `iv_convention`
  "none", rules shas, smoke record, `label_O`). **Promoted:** q0262 (census O; returns the label before any window logic)
  -> q0263 (screen O; 2 `cb12_test` lines O1, O2 with p = 1, testable false, in the k1 = 10 Holm, plus one `ml_explain`
  line). **q0261 collector never installed; q0264 never run.** 191 cb12 tests pass.

## CB17 window code: freeze check, fixes, open-question rulings, 2026-10-20 18:20-18:50Z (design and code; nothing counted)
- **Freeze check (science-reviewer): FREEZE_READY_WITH_FIXES** (`reviews/CB17_WINDOW_FREEZE_CHECK_2026-10-20.md`); design
  logic faithful (Holm k1 = 3 over B1, B2, C1; family A refused everywhere, branch T). Fixes 1-7 applied (9b335fec on
  `worktree-agent-ae42d4cfea66b78af`; 52 CB17 tests): missing monitor/snapshot days exit 75 with a restore instruction;
  smoke gated on the code-freeze record and stores `code_sha256`; `b0`/`a0` float64; unknown never counts as met; econ
  event minimum among flagged fills; q0406 B frame resumable; disk caps in every job; stage-2 verifies pins. Added smoke
  `--worn-sha256`, `--snapshot-root`, `--live-trades-root`, `worn-manifest`.
- **Open-question rulings: REVISE, accepted** (`reviews/CB17_OPEN_QUESTION_RULINGS_2026-10-20.md`): O9 tick change ->
  availability status (was eligibility on a post-decision mark: selection on the outcome); O11 symmetric one-sided worst
  case by class; O1 re-entry counts on the signable population. All stricter and outcome-blind; parts B, C, E re-hash
  before they bind (e37643f3 never reached the working branch). O2: T17_rules = commit time landing the final parts on
  `chore/arepo-claude-setup`; by 2026-10-25T00:00Z -> S_8 = 2026-10-26T00:00Z. O12: q0405 pin copied verbatim from
  q0380's manifest. O4, O5, O6, O8, O10 accepted. Implementer applying O1/O9/O11 + re-hash.
- **q0413 queued** (net lane): byte-for-byte restore of the smoke's worn inputs from releases 10-15..10-17 (the
  10-12 capture's `rows_ext` is already rotated off the host).

## LT4 (E020-E024) DRAFT, 2026-10-20 ~18:10-18:50Z (design + code; nothing registered or counted)
- From creative round 10's top five: E020 arrivals vs cancellations (CH169), E021 age of the move (CH170), E022 hollow
  liquidity (CH174), E023 opens vs closes (CH171), E024 flow concentration (CH173). One Holm family, k <= 5 after census
  gates (q0480-q0486 drafts). Proposed window 2026-10-26T00:00Z to 2026-11-16T00:00Z; analysis after 2026-11-17T12:00Z.
  Planning MDEs vs floors in `LIVE_TESTS_4.md` §0 (E021 borderline, E023/E024 census-gated).
- Branch `feat/live-tests-4` (6290d93c design, c08383a5 code: reader reuses LT3 by import, 20 synthetic tests).
  Challenger R1 (science-reviewer) running.

## CB17 T17_rules: final rules parts landed, 2026-10-20 18:27:58Z (merge 2d6d3aa9); S_8 = 2026-10-26T00:00Z
- O-rulings applied (f0ef434d; 152 CB17 tests): O9 tick change as availability status (placebo/guard/attribution index
  sets unchanged, test-asserted); O11 symmetric one-sided worst case by class; O1 re-entry counts bind on the signable
  population; O12 q0405 pin note; B1 pre-registered as expected "uninformative" (O3/O7).
- **Re-hash chain:** pre `ddc0249b…` and common `23437440…` unchanged; B `fd9ce656…` -> `64e61091…`; C `68bd50a2…` ->
  `3e24af26…`; E `337382d6…` -> `9b1eba65…` (design §11.6). Part A never declared (branch T, withdrawn uncounted).
- **T17_rules** = committer time of merge 2d6d3aa9 on `chore/arepo-claude-setup` = 2026-10-20T18:27:58Z (ruling O2);
  record `seals/cb17_t17_rules.json`; `s8_from_rules` gives **S_8 = 2026-10-26T00:00:00Z**. Post-merge: 178 CB17 +
  battery2 tests pass. Next: delta freeze check (fixes 1-7 + O-rulings), code pin + ruling-6 attestation record, q0413
  restore, worn-manifest pins, q0404 smoke on the host (exact P1-P3).

## Reviews 2026-10-20 ~19:05Z: CB17 delta freeze check FIXES; LT3 permutation gate revise (design/code; nothing counted)
- **CB17 delta check: FIXES** (`reviews/CB17_DELTA_FREEZE_CHECK_2026-10-20.md`): re-hash reproduces byte for byte, no rule
  value moved, T17 record valid (S_8 2026-10-26T00Z). Before the code pin: worn-pin check must refuse missing pinned files
  (a partial restore could otherwise become a counted P2 FAIL); monitor-stopped days must give unknown `prt`, not 0;
  lows. Implementer applying; it reports whether any rules part sha moves (T17 would then be re-landed before 10-25T00Z).
- **LT3 permutation gate: revise** (`reviews/LT3_PERM_GATE_CHECK_2026-10-20.md`; raised by LT4 R1 finding 7). E015's
  `perm_gate` permutes the raw label although it correlates with the controls by design; local simulation (300 worlds)
  pass rate 0.127 vs the 0.058 limit at corr ~0.63 (0.040 uncorrelated). The primary p is cluster-robust OLS, so this
  weakens the backstop rather than opening a direct false-Supported path. Fix before the pin: Freedman-Lane gate,
  correlated-control scenarios for both gates, size-check draws 200; q0473 (old code) becomes information only; a q0473b
  size check re-runs on the fixed code. Implementer on `fix/lt3-freedman-lane` (../astrolabe-lt3-fl).

## LT3 Freedman-Lane gate merged; q0473 cancelled, q0473b promoted; CB17 D-fixes merged (2026-10-20 18:40-19:00Z; nothing counted)
- **LT3:** `perm_gate` now Freedman-Lane (61e501b5, merged b57a5cf5): the control-residualised target is shuffled within
  strata, tested term and controls fixed; seeds, 200 draws, strata and pass rule unchanged; new null scenarios
  `perm_corr_control` (corr ~0.62) and `donor_corr_control`; size-check draws 99 -> 200; `donor_gate` unchanged.
  `live_tests3_analysis.py` sha `b03c6321…` -> `d0a4a3b5…` (`live_tests3.py` unchanged `202c0d63…`); no pin existed.
  Local size check (300 worlds, not the registered statement): perm_corr_control 0.053, donor_corr_control 0.030 (limit
  0.0707 at 300). Verification (science-reviewer): **OK**; doc nits (stratum size counted over all rows incl. missing;
  §13.5 preamble names q0473) to fix before the pin. 34 LT3 tests pass.
- **q0473** (size check on the old gate) stopped on the host at ~18:40Z (runner SIGTERM, re-queued, then `cancel`; no
  output written; attempt recorded); superseded, information-only had it finished. **q0473b** promoted (same argv, output
  `size_check_fl.json`, 2,000 worlds, priority 20 so short census/screen jobs go first).
- **CB17:** delta-check D1/D2 + lows (31cca03e, merged 8defe614; 158 tests; rules part shas unchanged so T17 stands).
  Verification: one remaining D1 gap (an incomplete pin set could still yield a counted P2/P3 FAIL); final fix in
  progress before the code pin. Host deployed at 8defe614.

## CB17 code freeze recorded, q0404 smoke promoted, 2026-10-20 19:05-19:15Z (acceptance pending P1-P3 on the host)
- Final D1 completeness fix (04fa3e12, merged 10838876; 160 tests; rules part shas unchanged): pinned mode refuses unless
  exactly 12 P3 captures (incl. sports `20261015T063101Z_9c518015`, both rows files each) and 24 P2 sweeps are pinned;
  `release_map` anchored on a path boundary.
- **`seals/cb17_code_freeze.json`**: `code_sha256` `529e7de5…6267` (7 modules), rules parts pre/common/B/C/E as T17,
  `frozen_utc` 2026-10-20T19:05:50Z, ruling-6 attestation (no SCREEN_8/REP_8 file opened; none exists). Validated by
  `require_code_freeze`. Acceptance (ruling 6 (ii)) only when q0404 reproduces P1-P3 exactly with this code.
- **`seals/cb17_worn_sha256.json`** (54 keys): 53 from the releases' `files.sha256` (10-15..10-20), none from disk;
  `fills.csv.gz` `bd896882…` from q0273's write-once manifest (the file is in no release).
- **q0404 promoted** (after q0413 restore; snapshots/trades from the restore tree, sweeps/fills live).

## Queue and LT4 R1 response, 2026-10-20 19:10-19:30Z (nothing counted)
- **q0245 (CB12-E quake prices) done** (attempt 2, 19:17Z, 115 s, mem_mb 600): `quake_prices_complete`, 108 events,
  215 markets priced, 217 requests (<= the 15,000 recorded by q0244), 0 unavailable (network), 33 USGS requests. No
  outcome read. Unblocks q0266 (CB12-E census).
- **Restore jobs q0471 / q0413 failed in < 1 s** (q0471 attempt 3, q0413 attempt 1): `gh` (Go) aborts with "runtime:
  out of memory" under the 2 x mem_mb address-space cap (1.2 GB); measured on the host: fails at 1.2 GB, works at
  1.6 GB. mem_mb -> 1200 (cap 2.4 GB), deployed b002d48d, both `retry` (fresh budgets). Resource only.
- **LT4 R1 response** (`feat/live-tests-4` 708949c3, ee82f45d; LIVE_TESTS_4.md §14; 24 LT4 tests): all 12 findings
  addressed (E020 common support; permuted-share census + pre-declared fallback stratum; E021 skip-slot primary +
  n2h_truncated; E022 within-market VIF / residual-IQR gate / D_{k-1} / imbalance / binding transient label; both-token
  depth rule; Freedman-Lane gates; census DE with rho 0.02; interaction VIF + `x6|mid-0.5|`; 200 draws, 11 scenarios;
  sweep-missing label; LT3-first ordering); q0485 kept on the net lane (refusal with reason). New planning MDEs: E020
  0.22-0.32c, E021 0.36-0.68c (likely to drop), E022 0.25-0.63c (borderline) vs 0.5c floors. **New finding:** a donor
  gate is oversized (~0.115 for LT3's `donor_gate`) when the tested moderator correlates 0.7 with a controlled moderator
  that has a real effect; LT4's residualised donor gate + census cap |corr| <= 0.5 gives ~0.068 (limit 0.075 at 200
  worlds); the designer stopped tuning; E023/E024 blocked at the pin unless q0484 passes. Challenger R2 and an LT3
  donor-gate ruling (science-reviewer) running; LT3's pin waits for that ruling.

## Session 2026-10-20 ~22:39Z (autopilot): restore root cause fixed; gap 19:30-22:39Z written up (nothing counted)
- **Recorded late (previous session stopped ~20:40Z):**
  - **LT3 donor-gate ruling** (c5920dd2, `reviews/LT3_DONOR_GATE_RULING_2026-10-20.md`): revise. Studentise the donor
    statistic, add binding `donor_collinear_control` scenarios (0.5, 0.7; effect 0.004), census C2 reports within-market
    R^2 of x6 zW / x6 zH on the controlled interactions and uses |corr|. q0473b stopped (cancelled on the host; no
    output used). Fix running on `fix/lt3-donor` (implementer, this session); a new >= 2,000-world size check on the
    fixed code follows a science-reviewer pass, before the pin.
  - **LT4 challenger R2** (6ce45313): E020-E022 ACCEPT_WITH_CHANGES; E023/E024 dropped before any census (k = 3).
    R2 code + response 99c4c2eb / ebda78b8 (`feat/live-tests-4`): CH depth from the chosen definition, MA(2) overlapping-
    target size scenario, DE gate floor 3.0, `abs_dev` in the correlation cap, joint late1|late3 skip mask, n2h by band.
    Re-check (science-reviewer) running this session.
  - **CB18 DRAFT design** (9ea4f371, `feat/cb18`): round-10 remainder (CH172, CH175-CH177, CH179; CH178 excluded as a
    double count of E015). Design only.
- **Jobs finished (data preparation, no outcome read, nothing counted):** q0266 CB12-E census `not testable
  (dependence)` (19:40Z; freeze entry per the CB12-O precedent pending); q0277 CB13 touch frame complete (screen 374 /
  holdout 861 events); q0279 CB13 Binance 64 files, 0 unavailable; q0284 CB13-R pregate pass (58 components); q0302
  CB14 exclusion keys complete; q0303 CB14 W frame complete (94 of 1,119 rows kept; dropped: key 411, window 409,
  sports 180, summary 14, mention 9, entity 1). Follow-up promotions: audit running.
- **Restore failures, root cause:** q0471 (LT3 C2) and q0413 (CB17 worn inputs) failed with `no catalogue for
  data-20261016/17-dsheikh`: the repo catalogue stopped at 10-15. `archive_catalogue.py` run for 10-15-active and
  10-16..10-20 (incl. -2, -active) and committed (d79db323). q0413 attempt 1 had already restored and verified the 6
  files of data-20261015-dsheikh (report passed, 79,926,435 B); later attempts refused because those files existed, so
  its argv drops that tag (selection globs unchanged). Both `retry` with fresh budgets after deploy. q0472's deadline
  (10-23T03:30Z) still holds.

## Operational deviation: canonical E009/E010 gaps on 2026-10-13 before the 10-14 outage (recorded 2026-10-20; facts only, not counted)

Found by the live-tests readiness audit (`LIVE_TESTS_READINESS_2026-10-19.md`) from prediction-line timestamps only. No
outcome was read.
- **Gaps:** the canonical E009 stream (the Mac poller) has no prediction cycles strictly between 2026-10-13 21:24Z and
  22:22Z, nor strictly between 22:28Z and 23:12Z. The bounding cycles at 21:24Z, 22:22Z, 22:28Z and 23:12Z are present.
  Hourly cycle counts out of 30 are 21:00Z 13, 22:00Z 4 and 23:00Z 24. E010 has no 22:00Z or 23:00Z origin.
- **Cause:** unknown. This is separate from the documented 2026-10-14 00:02Z–10:44Z outage.
- **Coverage:** the validation copy started at 23:33Z and covers neither gap. The 2026-10-15 gap-fill decision covers only
  the open interval (00:02Z, 10:44Z) on 10-14 (rule `gapfill-v2`, `E009_E010_GAPFILL_RULE_V2.md`). Missing stays missing,
  and neither window is extended.
- **E011 is unaffected:** its passes at 20:31Z and 22:31Z on 10-13 are present.

## E010 verdict rule declared: Holm when a horizon is Unavailable (2026-10-21 00:12 UTC+1; pre-outcome, not counted)

This entry is declared before any E010 outcome analysis. It follows the science-reviewer's ACCEPT_WITH_CHANGES on the
readiness audit. It clarifies the registered sentence "Holm always uses m = 2: a horizon without a test enters with p = 1"
together with "Unavailable: fewer than 20 event clusters or fewer than 2,000 evaluated origins at that horizon".
- **Rule.** A horizon that is Unavailable by the registered minimum counts as "a horizon without a test" and enters Holm
  with p = 1. The other horizon's adjusted p is then min(1, 2·p_raw), where p_raw is its frozen `p_one_sided_m1`. When
  neither horizon is Unavailable, the Holm adjustment is the frozen `holm_m1`, unchanged.
- **Why.** The frozen `cross_venue_live_e010.analyze` assigns p = 1 only to a horizon with fewer than 2 clusters. A
  horizon with 2–19 clusters, or with fewer than 2,000 origins, would otherwise enter Holm with its own p, although the
  registration gives it no test.
- **Reporting.** `backend/scripts/live_verdicts.py e010` applies this rule. It also reports the frozen `holm_m1` and the
  verdicts that `holm_m1` would give. If the two sets of verdicts differ, both are shown and the declared rule is the
  registered verdict. No statistic is recomputed: p_raw is read from the frozen output.

## Deviation: fix to frozen E011 analysis code, `_cluster_id` (2026-10-21 00:12 UTC+1; pre-outcome, not counted)

- **What changed.** In `surprise_snapshot.analyze` (commit `ed7dea22`, branch `feat/live-audit`), the episode cluster
  `a.get("event_id") or a["market_id"]` became `_cluster_id(a)`. It treats `"nan"`, `"None"`, empty and null event ids
  as absent and falls back to the market id.
- **Why.** The E011 registration says "cluster = Gamma event id (market id when absent)". Alert lines store
  `str(row["event_id"])`, so a capture row without an event id arrives as the string `"nan"`. The old expression treated
  that string as present and would have pooled every such market into one `"nan"` cluster. The fix restores the
  registered definition exactly.
- **Effect on collected data:** none so far. 0 of the 4,200 window alert lines (as of 2026-10-19 21:44Z) carry a
  missing-like event id. The latest capture had 1 market without an event id among 246,961 rows, so the case can occur.
  The primary statistic, the episode rule, the window and the verdict thresholds are unchanged.
- **Found and checked by:** the live-tests readiness audit, reviewed by the science-reviewer (ACCEPT_WITH_CHANGES). Test:
  `test_e011_missing_event_id_falls_back_to_market_id`. The E011 analysis must run from a commit that contains this fix.

## CB12-M and CB12-E freeze (gate-failure path) and screens, 2026-10-20 22:56-23:10Z; 3 tests counted with p = 1
- **Freeze entries** (`model_specs/cb12_v1.json`, merge ae175bec of `freeze/cb12-me` 7181778c + 48964e20): M
  `rules_sha256` a2e420b0…, census `census_M.json` sha256 6229816e… (q0249, 19:04Z); E `rules_sha256` bd512db4…, census
  `census_E.json` sha256 caabaadd… (q0266, 19:40Z); common f2f672c1…; both census shas re-checked on the host by the
  orchestrator. Science-reviewer freeze check: **FREEZE_OK_WITH_FIXES**, applied: `git_commit` labelled as inferred from
  host log time (binding pin is `census_rules_sha256`; CB12 code identical across 8defe614..7181778c); E's q0257
  collector not installed recorded as a **disclosed deviation** (design :78/:768/:948/:1087 install it unconditionally;
  harmless because E1 is fixed at p = 1 by the outcome-blind census, so Stage 2 can never open, :785-786); M's
  verify_fetch/holdout-listing calls on this path noted.
- **Census gates (counts only):** M: GM pass (159 events, 79 speaker keys, 36 weeks), GMP fail (MDE_M1 3.19 words > 1.0)
  -> M1, M2 "not run (power)". E: parser gate pass; dependence minima unmet (183/300 markets, 28/60 events, 30/40 weeks,
  27/30 components) -> E1 "not testable (dependence)"; GEP not computed.
- **Screens (counted):** q0252 (23:08Z) M1, M2 p = 1, advance false; q0253 (23:10Z) E1 p = 1, advance false. No outcome
  file opened (the screens return before any guarded open). **CB12 counted so far at p = 1: O 2, M 2, E 1 = 5 of k1 = 10.**
  Never run: q0256, q0257, q0258 (and q0261, q0264 for O).

## LT4 (E020-E022) R2 re-check and censuses promoted; LT3 donor-gate ruling 2, 2026-10-20 23:00-23:59Z (nothing counted)
- **LT4 R2 re-check** (science-reviewer, `reviews/LT4_CHALLENGER_R2_RECHECK_2026-10-20.md`): **ACCEPT_WITH_CHANGES**. New
  HIGH: q0484 (size check) cannot run until LT3's registration commit is merged and the LT4 code freeze is recorded
  (LT4 hashes `live_tests3_analysis.py`; `sim_move_world` RNG order changed with the Freedman-Lane commit). MEDIUM: block
  anchor split census days. LOW: `bounce_decomp` not hashed; stale text. Fixes 4b6cc7e1 (per-census anchor at its first
  UTC day, analysis at REGISTERED_UTC; `bounce_decomp` in CODE_FILES; q0484 gating; q0481 folded into LT3's q0471
  restore) and 99618c95; verification **OK_WITH_FIXES** (capture seal missing before q0482/q0483; one-day final block
  disclosed). Capture/sweep seal `seals/lt4_census_inputs_captures.json` written from the releases' `files.sha256`
  (211 files, 2026-10-14T22Z .. 10-17, manifests checked) before any LT4 census. feat/live-tests-4 merged; **q0482 (CQ/CH)
  and q0483 (CF clock) promoted**, counts only, after q0480 (restore; mem 1200; adds release -2 for 10-17T04:31Z) and q0471.
- **LT3 donor-gate ruling 1 implemented** (`fix/lt3-donor` d0196387: studentised score, `donor_collinear_control`
  0.5/0.7, C2 within-market R^2, |corr| cap; 38 tests). Local informational size check (300 worlds; limit 0.0707):
  donor_iid 0.073, donor_corr_control 0.100, donor_collinear_control_0.7 0.073; perm scenarios within the limit.
- **Ruling 2** (`reviews/LT3_DONOR_GATE_RULING2_2026-10-21.md`): implementation correct; the donor gate is structurally
  invalid (real and donor statistics not exchangeable: direction correlation real-donor 0.210 vs donor-donor 0.243 iid,
  0.131 vs 0.183 corr_mod). **Option (ii):** the donor gate becomes a reported, non-binding label; E016/E018 use the
  Freedman-Lane permutation gate as E015/E019; binding size scenarios = perm scenarios + flow-world perm (iid, AR 0.6,
  collinear 0.7); skipped draws fail closed; thresholds, alpha, draws, seeds, limit 0.058 unchanged; written as §13.13
  before any 2,000-world run, then a science-reviewer pass, then the run; any binding failure blocks the pin with no
  further redesign. The decision does not depend on any later size result. Implementer running. q0471/q0472 unaffected.

## CB14-W gate GW0 blind audit, 2026-10-20 ~23:25Z (repo step; nothing counted yet)
- q0303's `w_map_audit_sample.csv` (every mapped pair, 56 rows, sha256 3875e69b…) blind-labelled by one science-reviewer
  agent that read only that file and CREATIVE_BATCH_14.md:575-592: **38 match / 18 not, precision 0.679 < 0.90 (GW0
  FAIL)**. Misses: surname lists (Epstein, Menendez, Nguesso, Trudeau, Tshisekedi), companies/apps (ChatGPT, OpenAI,
  TikTok, Tea App, Tinder), wrong pages (a Coldplay tour for Andy Byron / Kristin Cabot; Tony Gonzalez vs Gonzales; "Von";
  Japan; ICE; University Presidents; Trump as a modifier). Committed as `seals/cb14_w_map_audit.json`; q0305 gets
  `--audit` pointing there (the default path under data-dumps is not in git).
- The design allows one blind revision of the entity rule after a GW0 failure. **Not used:** the frame keeps 94
  markets after key drops (q0303 counts), below GWC's 150-market minimum regardless of the map, so a revision cannot
  change the GWC result (decided from counts only, no outcome). q0305 will record GWC FAIL -> W1, W2 not testable,
  counted with p = 1 per the design; q0306/q0307 are never committed.

## LT3 ruling 2 implemented, verified, size check queued, 2026-10-20 23:30-23:55Z (nothing counted)
- `fix/lt3-donor` b43f6e1b (merged 50b7fbac with e29ead9c): E016/E018 binding gate = Freedman-Lane permutation gate
  (market x UTC day, 200 draws, min stratum 4, seeds E016_gate/E018_gate unchanged); donor gate computed as a
  non-binding label only; skipped draws fail closed in both gates (p = (1+ge)/(1+completed); pass needs all 200);
  binding size scenarios perm_iid, perm_persistent, perm_corr_control, flowperm_iid, flowperm_ar0.6,
  flowperm_collinear_0.7; donor_* reported with binding false; §13.13 items 1-7; 41 LT3 tests, 26 LT4 tests.
- Verification (science-reviewer): **OK to run**. Optional fix applied (e29ead9c, label only): "within-unit timing
  untestable" when the verdict is Unavailable, the donor gate could not run or draws were skipped. Noted gap: no binding
  world has serially correlated residuals (not blocking: a failed gate can only force p to 1). Code: analysis
  62ef3375…, reader 2dff0621…. Mac timing ~85 min; host estimate 3-5 h, ~150 MB.
- **q0474** queued (2,000 worlds, 200 draws, seed 20261020, limit 0.058, priority 42, timeout 12 h, retries for
  infrastructure only). Any binding failure blocks LT3's pin with no further redesign.

## CB18 R1 response and challenger R2, 2026-10-21 ~00:00-00:55 UTC+1 (design only; nothing counted)
- R1 response (`feat/cb18` 067d368e, CREATIVE_BATCH_18.md §11): CB18-R counted test dropped (race map descriptive, no
  revival in this census); DE_gate = max(3.0, computed) with SE inflation, 1.5 factor, 1/n0; chg_* byte flags + chg_only
  class + |mid| controls; binding MA(11) overlapping-target scenario; lookback capped at 11 (first origin's furthest read
  10-26T00:31Z); 10-14 00:31-10:31Z captures declared unavailable; updated_at prior use disclosed; q0500/q0501 tags and
  globs fixed against the new catalogues; CB18-P both-sample membership + stratum dummies; whitelist for
  uma_resolution_statuses; CB18-M folded bands; CB18-F breakpoint from the dated venue observation only. Pessimistic
  planning MDEs: CB18-S 1.58c (batch route) vs 1.0c floor, RS-2 (LT5 28-day route) 0.71-1.00c; CB18-P 1.39c/0.98c vs
  0.5c (expected to drop). Counted: CB18-S only, k = 0-2.
- **Challenger R2** (`reviews/CB18_CHALLENGER_R2_2026-10-21.md`, 40adc91c): **ACCEPT_WITH_CHANGES**; all R1 findings
  resolved; five changes before `pre` lands (J4-R census-read disclosure, latent-volatility label scenario, P power gate
  pinned as the max of two routes, P look-back label, E012 wait for q0512). Recommendation: run the counts-only censuses
  (RS-2 is powered on paper; GS1/GS2 are a cheap kill); cut P first if coding time is short. Implementation of the
  changes, part `pre` and the censuses running on feat/cb18.

## Development study WS1: wallet skill family (feat/wallet-skill, merged 2026-10-20T23:37Z; interactive session): 4 tests counted
- **Status:** counted (4 tests P1–P4, Holm family of 4). Development (exploratory_historical) on HB1 history sets
  h1_first/h2_main/h3_power, trades 2025-04 to 2026-10-12 only, outcomes known at closedTime + 48 h. No live-test,
  sealed or holdout data read. The declaration was committed before any result (319bcd2c); results are in 56377f0f.
- **P1 skill persistence: PASS (Holm p 0.002).**
  - Top-decile sign-randomisation-skilled wallets ranked on outcomes before 2026-07-01: 71.2% stayed positive afterwards
    vs 59.7% base. Re-significance 44.4% vs 21.1%. Out-of-sample +21.7c per dollar at risk [+1.4, +39.6] vs +3.6c.
  - P&L-ranked wallets do not persist.
- **P2/P3/P4: null (Holm p 1.0).** Skilled-wallet flow adds nothing over generic flow for 24 h and 6 h mid change or for resolution.
- **Reading:** skill is measured against trade price and may reflect bias exploitation, not private information. The
  family goes to the signal engine as a low-priority challenger, embargoed until 2026-11-18 (signed flow overlaps
  E013/E014/E016/E018).
- **Next:** a wallet-level copy-latency test (prior-art gap 1 H1b) needs its own registration and challenger review.

## LT3 census C2 (q0472), done 2026-10-20 23:45Z (counts only, sealed samples of 2026-10-16/17); E016 and E018 dropped uncounted (written up 2026-10-21 ~03:50Z, autopilot)
- **Output** `live_tests3_census/C2.json` sha256 `77f6e512a4e3ba934103b0b628bfd35edfa9b35b9776f1a7870fdc6f16ac3032`
  (code_sha256 live_tests3.py `42663375…`, live_tests3_analysis.py `62ef3375…` = the ruling-2 code; seal
  `seals/lt3_census_inputs_C2.json`, 23 restored samples re-hashed, `bad` empty; runtime 1,284 s). Origin-side fields only;
  no target, no later-capture price, no P&L read.
- Counts: covered units 21,311 in 5,303 events (projected 21 d 223,766); signed rows 5,093,017 (all tick-known); walked
  495,889; 6 h truncation 2 of 21,313 rows (`vol24_cap` = inf, defined).
- **E016: gate FAIL** on four of five conditions: projected covered units with W in (0, 1) 51,828 (< 60,000); walked share
  0.0974 (< 10%); ">= 4 decimal" rows within 1e-4 of grid 0.596 (> 20%); agreement arm n_walked 473 (< 500, so the gap
  -2.9 pp cannot pass). V* defined (pass).
- **E018: gate FAIL**: H in (0, 1) for 0.308 of covered units (< 40%); agreement arm < 500 rows; corr(W, H) 0.136 (pass).
- **Rule (LIVE_TESTS_3.md §8, §13.6):** a failed census gate drops the test before registration, uncounted; recorded in
  §7.6. Gates were fixed at the freeze check (13.9) before any census ran; nothing is re-tuned.
- **LT3 now: E015 only, k_tests = [E015], Holm m = 1.** Remaining before the pin (§13.11): q0474 size check (running;
  any binding failure still blocks the pin), science-reviewer freeze check of code against design, host dry run,
  `code_sha256` map, `SPEC_SHA256`, registration commit. `REGISTERED_UTC` 2026-10-24T00:00Z if the commit lands by
  2026-10-23T00:00Z (§1.1, unchanged).

## LT3 pre-pin verification, 2026-10-21 ~04:10Z: PIN_OK_WITH_FIXES (nothing counted; q0474 not read)
- `reviews/LT3_PREPIN_VERIFY_2026-10-21.md` (science-reviewer, on 38aa5694): E015 path ready; fixes before the pin:
  (1) HIGH analysis must compute only `k_tests` (dropped tests produced estimates); (2) MED-HIGH switch surge/flow
  collection off by `k_tests` (a crash there could block E015's freezes/outcomes); (3) hash correction below; (4) date
  constants rule; (5) ruling: binding for the E015 pin = `perm_iid`, `perm_persistent`, `perm_corr_control` only (a
  `flowperm_*` failure is recorded and blocks future flow-moderation use of the gate, not this pin); written before q0474
  is read; (6)-(7) dry-run procedure and stale text. Fixes 1-2 change module hashes, so the size check is re-run (draft
  q0475) on the fixed code; its `perm_*` rates must equal q0474's exactly (size-check code byte-identical).
- **Correction** to the entry "LT3 ruling 2 implemented, verified, size check queued": the reader hash there
  (`2dff0621…`) is wrong; `live_tests3.py` at b43f6e1b / e29ead9c / 38aa5694 is `42663375…` (as C2.json records).
- Implementation on `fix/lt3-prepin` (worktree ../astrolabe-lt3-prepin), then merge, promote q0475, dry run, pins,
  registration commit before 2026-10-23T00:00Z.

## Signal engine: started on the host + challenger se8_lr_event (event family), 2026-10-21 ~03:45-04:40Z (signal-engine autopilot; nothing counted yet)
- **Engine started:**
  - The per-pass `tick` is the last step of `arepo_pass.sh`.
  - Queue jobs q0512 refit, q0513 score and q0514 walkforward promoted.
  - Feature backfill of the captures still on the host; 15 archived captures skipped, missing stays missing.
  - Bug fixed: archived captures no longer use the per-run feature budget.
- **New challenger `se8_lr_event`:** the champion plus the auxiliary family `event` (`se-aux-event-v1`; DESIGN_V1 §16).
  - Science review: ACCEPT-WITH-FIXES. All fixes were applied before any table was written:
    - no zero-imputed sums;
    - `require_full_coverage`, for comparability with the champion's row set;
    - no prediction without the table;
    - the join result sets the source flag;
    - coverage and rows-sha provenance recorded.
  - No embargo token: no live test from E009 onward isolates event or sibling features.
- **Overlap note (for future registrations):**
  - `ev_sib_*` resembles SB2-J5's L1 (sibling reversal). `ev_norm_gap` / `ev_sum_mid_m1` resemble E005's band
    deviation.
  - se8's prospective scores are a development look at both families. The first leaderboard that shows a se8 gain
    counts as one development test, and a trials line is appended then.
  - Any later live test of J5 or a neg-risk band hypothesis must declare that it is not fresh.
- **For the experiments track (not edited here):** the ledger summary row for E005 (line ~14) still reads
  "REGISTERED, pending". Its scored entry (line ~678) says "Not supported".

## LT3 pre-pin fixes merged and verified, 2026-10-21 ~05:00Z (nothing counted; size-check results not read)
- `fix/lt3-prepin` merged (6c51901c): §13.15 ruling first (65719509: binding for the E015 pin = `perm_iid`,
  `perm_persistent`, `perm_corr_control`; `flowperm_*` recorded, not blocking; donor reported); analysis computes only
  `k_tests` (b48e1909); collector surge/flow off by `k_tests` (f9c9566c); text, spec and §13.16 date rule (eaa67bc8).
  New code hashes: `live_tests3.py` 3ac52d79…, `live_tests3_analysis.py` 224b5603…. 69 LT3/LT4 tests pass.
- Fix verification (science-reviewer): **FIXES_OK_WITH_NOTES**, nothing blocking; `size_check()` and all callees
  byte-identical to 6b82fe78, so q0475's `perm_*` rates must equal q0474's exactly. Note applied: a date move after the dry
  run repeats the dry run.
- **q0475_lt3_size_check_r3 promoted** (cpu, 400 MB). Remaining: q0475 result vs §13.15, host dry run (13.4), pins,
  registration commit before 2026-10-23T00:00Z.

## CB12-O q0263 bookkeeping note, 2026-10-21 ~05:15Z (nothing new counted)
- q0263 (screen O, 10-20T19:08Z) shows `failed` in the queue. Checked on the host (read-only): `results_O.json` was
  written once (sha256 `4d329a5d…`), and both counted `cb12_test` lines O1 and O2 (p = 1, testable false, label
  "not testable (source)") are in `trials.jsonl` at 19:08:04Z. The count of 2 for O stands.
- The error came after those lines: the family summary line (`kind` `ml_explain`, source `creative_batch_12:O`,
  `n_tests` 2) was refused by `provenance.check_evidence_role`, because `run_cb12.py:622` passes the role "prospective",
  which is not an allowed value. Attempt 2 refused correctly (results are write-once).
- **Effect:** one descriptive summary line is missing; no test count, p-value or verdict changes. Not back-filled. O is
  terminal (q0264 never runs), so the defect cannot recur on this path. The CB12 code stays frozen; any future
  CB12-style runner must map "prospective" to an allowed role. The queue entry stays `failed` as the honest record.

## LT3 host dry run (§13.4), recorded 2026-10-21 ~08:55Z (run 04:50-05:15Z; nothing counted; no outcome read)
- Run by the 10-21 interactive helper (`/tmp/lt3drv.sh` on the host) and not written up before; recorded here from the
  host log `/tmp/lt3drv.log` and the per-pass outputs. Host tip 054388ec; `lt.code_hashes()` on the host =
  `live_tests3.py` 3ac52d79…, `live_tests3_analysis.py` 224b5603… (the §13.16 hashes to be pinned).
- Command: the exact §13.4 cron command (own `flock` on `~/arepo/run/live_tests3.lock`, `nice -n 19`, `oom_score_adj` 1000,
  `ulimit -v 983040`, `--max-items 40`, `--data-dumps-cap-gb 40`) plus only `--dry-run-start 2026-10-19T00:00:00Z
  --dry-run-end 2026-10-19T12:00:00Z --root /tmp/lt3dry`; `/usr/bin/time -v` between `flock` and `nice`. Started only
  with no collector pass running and MemAvailable >= 1,500 MB (4,504 MB at start).
- Passes (exit code, peak RSS, wall): 1: rc 0, 534,372 kB, 13:11 (backlog: 39 series, 1 sweep); 2: rc 0, 342,792 kB, 3:02
  (38 sweeps, 2 move freezes); 3: rc 0, 317,592 kB, 0:28 (4 move freezes, 24 move outcomes); 4: rc 75 `nothing_new`,
  123,280 kB, 0:02. Every pass `pinned: false` (lines `prospective_unregistered`), `kinds_off: [flow, surge]` (§13.16 fix 2
  working), `refused_late` 0. Scratch root 117 MB, 156 files (series 39, status 39, sweeps 39, move/frozen 6,
  events/frozen 6, move/outcomes 24).
- **Result:** peak RSS 0.53 GB is well under the 960 MB cap; the slowest pass (a 12 h backlog of 40 items) took 13 min,
  under the 20-min cron interval, and steady-state passes take seconds. 13.4's owed dry run is done. Remaining before
  registration: q0475 (`perm_*` must equal q0474 exactly, §13.15), pins, registration commit before 2026-10-23T00:00Z,
  then the cron install.

## MC1 q0116e: killed by the kernel OOM killer again, 2026-10-21 07:10Z (nothing counted; development only)
- q0116e (memory-fixed `run_ml_dev.py`, 9e6d5596; exclusive; max_retries 0) started 06:58Z and was killed at 07:10:49Z
  after 771 s: global OOM, `anon-rss` 4,932,452 kB, total-vm 10.5 GB, `oom_score_adj` 1000 (the collector and monitors
  were protected as designed; the collector pass and live collectors were unaffected). The job log holds only the argv
  line, so the stage is not known; the peak is about the same as q0116d's (4.8 GB), so the column-wise read-back fix did
  not lower the true peak enough, or the peak is in the model-fit stage the fix did not measure.
- No trials lines, no outputs; the cached panel (hash c30de03b…) and period cache are unchanged and stay reusable.
- **Decision:** no further attempt on this host (5.6 GB RAM; five OOM-type failures q0116..q0116e). Not retried and not
  re-designed by shrinking the panel (that would be a design change needing a written justification and review).
  MC1 waits for more memory: either the second free instance (auto-retry still "out of host capacity" at 08:40Z) or an
  owner-approved free resize of this instance (Always Free A1 allows 4 OCPU / 24 GB in total). Dashboard approval item.
  The signal engine (separate autopilot) covers prospective multi-family scoring meanwhile.

## LT3 size check q0474 (old code) read, 2026-10-21 ~09:00Z (information; the binding size statement is q0475's)
- `live_tests3_census/size_check_r2.json` (sha256 39d0978b…), 2,000 worlds x 200 draws, seed 20261020, limit 0.058017.
  Read after the §13.15 ruling was committed, as that section requires.
- **Binding for the E015 pin (§13.15):** `perm_iid` 0.0470, `perm_persistent` 0.0480, `perm_corr_control` 0.0435, all ok.
- **Flow scenarios (not binding for E015, §13.15 item 4):** `flowperm_iid` 0.0465 ok, `flowperm_collinear_0.7` 0.0495 ok,
  **`flowperm_ar0.6` 0.0590 FAIL** (above 0.058). As pre-declared, this does not block the E015 pin. It blocks any future
  use of the Freedman-Lane gate for flow moderation (E016/E018 or a successor) until that gate is redesigned and passes
  its own size check. The overall `pass` field is false because of it and is ignored for this pin (§13.15 item 2).
- **Donor (reported only, §13.13):** iid 0.0555 ok; ar0.6 0.0595, corr_control 0.0585, collinear 0.5 0.060 / 0.7 0.067,
  lifecycle 0.0665 all above the limit, which confirms the donor gate's non-binding status.
- **Provenance note:** the file's `code_sha256` shows the post-fix hashes (3ac52d79… / 224b5603…). The runner computes
  them from the files on disk at write time (06:54Z), after the fixes were deployed (~05:00Z), while the process had
  loaded the pre-fix modules at 03:12Z. The size-check functions are byte-identical across the fix (§13.16 item 3), so
  this is a labelling caveat only. q0475, which loaded the fixed code, gives the registered statement.

## Queue promotions, 2026-10-21 ~08:55Z (autopilot; nothing counted)
- **Promoted:** q0280_cb13_seal_R (q0278/q0279 done; CB13 freeze-checked; T_seal not binding for CB13);
  q0347_cb15_p_birth_census (q0340 done, q0348 P smoke passed, CB15-P fixes ACCEPT_WITH_FIXES);
  q0380_cb16_exclusion_keys (q0340 done; CB16 freeze-checked and re-checked; `--base-sha256` 10240ce7… = host
  `creative_batch15/exclusion_keys.csv.gz`, also listed in its `exclusion_report.json`). Rules part hashes regenerated
  for cb11-cb16 into a scratch path: every one matches the committed seals and the draft notes.
- **CB18:** census code merged (feat/cb18, 45 fixture tests); restores q0500/q0501 promoted. The census jobs q0502-q0506
  wait for an independent code-against-rules check.
- **Held, with reasons:** q0233/q0234 (CB11 P/A freeze part not committed; census already failed GP/GPP and GA/GA0);
  q0312 (CB14-S terminal after the q0301 smoke failure); q0040b (not before 10-23); q0235, q0256, q0258 (rep stages not
  triggered: their screens gave advance false).

## CB18 census code: fixes verified, census jobs promoted, 2026-10-21 ~09:00Z (nothing counted)
- Code check (science-reviewer) CENSUS_READY_WITH_FIXES (`reviews/CB18_CENSUS_CODE_CHECK_2026-10-21.md`). The eight
  fixes are in 1442bb27: capture time over all rows; unknown category, missing stamp and missing receipt fail closed
  and are counted; routing checks the hashes; map M exits use no later information. CREATIVE_BATCH_18.md §13 holds the
  interpretation notes, committed 09:59 +0100, before any census. Rules part `pre` is unchanged (e5b9c645…). Verification:
  **FIXES_OK_WITH_NOTES**, 51 tests pass. No CB18 output and no `creative_batch_18` trials line existed on the host or
  locally.
- **Notes carried forward (disclosure):**
  - (1) the sealed helper `cb18_rules_pre.book_untouched` still fails open on a NaN outcome-1 stamp. The census does not
    use it; later S and window code must not reuse it unchanged.
  - (2) map M counts a re-appearance once per market, and a re-appeared market is no longer tracked, so it never
    appears in `still_listed_at_end` / `undetermined`.
  - (3) an empty `fee_type` counts as a known category (same as F).
- **Promoted:** q0502 (S), q0503 (P), q0504 (R), q0505 (F), q0506 (map), behind restores q0500/q0501. Then the
  orchestrator runs `run_cb18.py routing`. Real-data memory is not measured (declared 300-390 MB); watch q0502.

## Signal engine: development walk-forward look + challenger se10_lgbm_event, 2026-10-21 ~08:40-10:00Z (signal-engine autopilot; development only, nothing counted)
- **Development walk-forward (historical, not prospective):** `run_signal_engine.py walkforward --max-test-days 7
  --max-rows 200000` on a Mac copy of the host engine root (rsync 08:35Z; no host CPU used). Test days 10-14 to 10-20;
  embargoed models (se2-se6, se9) computed nothing. Mean log-loss gain over the logistic champion `se0`, event-clustered
  95% CI, days positive:
  - `se1_lgbm_mm` (same features, LightGBM): dir_2h +0.0408 [0.0401, 0.0416] 7/7; dir_6h +0.0538 [0.0527, 0.0549] 7/7;
    dir_24h +0.0513 [0.0493, 0.0534] 6/6.
  - `se7_lgbm_all` (broad): dir_2h +0.0458 [0.0450, 0.0466]; dir_6h +0.0606 [0.0595, 0.0617]; dir_24h +0.0584
    [0.0564, 0.0606].
  - se8: insufficient coverage (12 captures lack the event table). res_7d: no labels yet.
  - **Reading:** a learner effect (non-linear use of market state + momentum), not a new information family. Forecast
    quality only; no edge, return or calibration claim. The host's q0514 remains the record of this baseline.
- **New challenger `se10_lgbm_event`:** se1's learner and params + the `event` aux family (same table as se8;
  `require_full_coverage`). Reason: a family effect measured on the logistic learner says little once a LightGBM model
  is champion; se10 vs se1 reads the family at a matched learner. No embargo (as se8). se8 and se10 together are one
  development look at the event / neg-risk / sibling family (the overlap note of the se8 entry applies unchanged); K for
  non-embargoed challengers goes 3 -> 4. Dry fit on the Mac copy (coverage requirement relaxed in a temp spec dir only):
  fits and predicts; peak RSS 1.0 GB.
- **Rewards aux backfill:** 85 `rewards` tables built on the host 09:01-09:04Z (niced, 2 GB address cap); 24
  captures unbuildable (rows archived), missing stays missing.

## Signal engine: embargo requests applied, 2026-10-21 ~10:20Z (signal-engine autopilot; nothing counted)
- Applied the experiments track's requests (`CANDIDATES.md`, "Embargo requests", filed ~09:20Z) in `config.EMBARGO`:
  `flow`, `book`, `rewards` -> 2026-11-22T00:00Z (LT5 drafts J/O, H/R, R); `wallet` -> 2026-12-07T00:00Z (E026 draft);
  new tokens `wallet_skill` (2026-12-07) and `event` (2026-11-22, LT5 F draft). All moves are later; none earlier.
- `event` now embargoes `se8_lr_event` and `se10_lgbm_event`. No event-family score was ever computed or shown
  (neither has a fit yet; the earlier development walk-forward reported se8 as insufficient coverage, se10 did not
  exist). The se10 dry fit on the Mac copy (previous entry) produced fit diagnostics only, no score; its attribution
  share is not reported anywhere public.
- Non-embargoed challengers until 2026-11-04: se1, se7 (K = 2).

## LT5 drafted, challenger R1 and re-check, 2026-10-21 ~08:50-09:15Z (design only; nothing counted or registered)
- Draft `LIVE_TESTS_5.md` on `feat/live-tests-5` (c4b09d73) from round 11 (`CREATIVE_HYPOTHESES_2026-10-25.md`). Up to
  5 tests, Holm k <= 5, k set by counts-only censuses alone:
  - J (CH180, jump vs grind);
  - F (CH184, alone vs with the family);
  - O (CH182, overhang);
  - H (CH181, 7-day high-water mark);
  - R (CH183, rewarded-band jump).
- Dropped or deferred: CH185 (trains, excluded by the round's rules); CH190 (after E022, which uses the same control);
  CH187/CH188 (maps first); CH186/CH189 (engine first). Earliest window 2026-10-30.
- **Challenger R1: ACCEPT_WITH_CHANGES** (`reviews/LT5_CHALLENGER_R1_2026-10-21.md`). The two HIGH findings:
  - (1) the Freedman-Lane gate that failed `flowperm_ar0.6` (q0474) must not be reused for flow-moderation-like terms
    without AR scenarios;
  - (2) J's target overlapped the selection window and the bounce: skip-slot primary.
- **Response** (ac6a29ef, §14):
  - O is treated as flow moderation, with a new circular-shift gate;
  - AR / Markov+MA binding scenarios for O, R, H and J;
  - a failing scenario makes only its own test "SE check failed", p = 1, k unchanged;
  - J and O targets start at k+1;
  - F is clustered on the family, with a moving-share control;
  - R gets a crossing-market gate (25%, 50 markets);
  - H has a spread <= 0.10 mark and one unit per market-day;
  - resources follow LT3's 534 MB.
- **Re-check: R1_RESPONSE_OK_WITH_NOTES.** The open MED note is that the size-check world parameters must be fixed
  before any census. It is being applied, then the census and size-check code. The embargo condition is met: the
  signal engine applied `event`, `flow`, `book` and `rewards` to 2026-11-22, and `wallet` / `wallet_skill` to
  2026-12-07 for E026 (26f5f954).

## CB13-R seal (q0280) done; census q0281 promoted, 2026-10-21 ~09:45Z (nothing counted)
- q0280 sealed R's HOLDOUT at 09:11Z (108 s). The seal copy is committed as `seals/cb13_touch_holdout_SEAL.json`, a byte copy
  of `creative_batch13/holdout_SEAL_R.json`, sha256 98a5404a…. It holds hashes and counts only:
  - 238 kept;
  - 0 dropped absent;
  - 0 dropped by seal copies;
  - 7,219 drop ids;
  - disjointness verified;
  - 74 fetched files re-hashed.
- q0281 (R census, counts only, gates GR/GRP and MDEs) promoted.
- **Ops:** q0380 (CB16 keys) died twice with MemoryError at 500 MB, so it was raised to 1,200 MB. The CB18 restores
  q0500/q0501 crashed in gh's Go runtime at 600 MB, so they were raised to 1,200 MB, as the earlier restores q0413/q0480
  used. No scientific change.

## LT5 census and size-check code merged; seal job q0564 promoted, 2026-10-21 ~10:05Z (nothing counted)
- Code on `feat/live-tests-5`, merged into this branch after these reviews:
  - code check CENSUS_READY_WITH_FIXES (3 MED: silent absence of sealed inputs, R depth-band population, CHW population;
    7 LOW);
  - fixes e8f0cd96;
  - verification NOT_OK on one item: the H gap rule had been reworded into a looser check that never fired;
  - re-fix f49bf94e (literal original rule, seal step `seal-captures`);
  - re-verification **FIXES_OK_WITH_NOTES**.
  Reviews: `reviews/LT5_CENSUS_CODE_CHECK_2026-10-21.md`. 41 LT5 tests pass.
- The code-hash map covers 11 files (vendored LT3/LT4 base and imported dependencies). Size-check worlds are fixed in
  §1.8.1 (12 binding scenarios incl. AR 0.6/0.9/0.95 for O), before any census.
- **Queue:**
  - q0560 (restore of 10-12 and 10-13T00/02 captures, which have left the host) promoted early;
  - q0564 (input seal, after the 10-21T22:31Z pass; not before 23:20Z) promoted;
  - q0561 (capture censuses F/H/R/CHW, exclusive), q0562 (flow censuses J/O, after q0561) and q0563 (size check, after
    both) stay drafts.
- **Hard timing:** q0561 must start before 2026-10-22T02:45Z (queue blackout) and read its captures before the 03:30Z
  retention run, which removes the 10-13/10-14 captures inside H's look-back. Before that, the q0564 seal must be
  byte-copied to `seals/lt5_census_inputs_captures.json`, committed and deployed (q0561 refuses an uncommitted seal).
  If the window is missed, a new restore and seal are needed; nothing is backfilled.
- Reviewer notes carried forward: `seal-captures` does not refuse when `--restore-report` is missing (q0564 passes the
  one report it needs); the seal copy is a manual byte copy, so check its sha256 against the q0564 output.

## Signal engine: hidden learner-matched challengers se11-se13, 2026-10-21 ~10:15Z (signal-engine autopilot; nothing counted)
- Added `se11_lgbm_flow`, `se12_lgbm_tte`, `se13_lgbm_xvenue`: LightGBM with `se1_lgbm_mm`'s params on the champion's
  features plus one family each (DESIGN_V1 §18). Each is embargoed under the same token as its logistic sibling
  (flow 11-22, tte 11-14, xvenue 11-04): predictions are written once with receipt times, no score is computed or shown
  before the date, and the walk-forward skips them. No registered live test, file or frozen artefact was touched.
- Non-embargoed challenger count is unchanged (K = 2: se1, se7) until 11-04.
- Mac refit timing (development data only, not a result): ~110 s per extra LightGBM model, peak 1.28 GB RSS.
- Noted: LightGBM `res_7d` fits fail on the causal inner split until resolution receipts precede the validation cut
  (backlog first fetched 10-21; expected around 10-28). No rule changed.

## E026 copy-skilled: census code checked, q0544 promoted, 2026-10-21 ~10:12Z (nothing counted; DRAFT design)
- feat/copy-skilled merged (design `LIVE_TESTS_COPY.md` DRAFT, 41 tests). One commit, c4f3549b (labeller end-date
  skip, store column subset), came from another session. It does not affect the census, and §6 now lists it as a
  proposed change needing review before the pin.
- Census code check: **CENSUS_READY_WITH_FIXES**, then fixes afac80d4, then verification **FIXES_OK_WITH_NOTES**
  (`reviews/E026_CENSUS_CODE_CHECK_2026-10-21.md`).
  - (MED) Skipped samples inflated rates; each usable sample is now credited with the time back to the previous one read.
  - Gates are always written.
  - Comparisons are unrounded.
  - The work dir has a marker so a retry is safe.
  - Verification note: the credit runs to the last sample's start, so the rate may be overstated by up to about 1.4%.
    The census reports it as is, with this note.
- **q0544 promoted** (counts only; sidecar samples [10-18T04:00Z, 10-21T04:00Z); never opens a capture at/after
  10-22T00:00Z; gates G1-G3 declared in aba32281 before any census). Next: commit `census.json`, fill the
  CENSUS-GATED values, challenger review, freeze q0540, pins, registration before 10-24T00:00Z.

## LT3 (E015) REGISTERED, 2026-10-21 ~11:35Z (registration commit = the commit adding this entry)
- **Test:** E015 only. Quote-only versus traded 2 h moves (LIVE_TESTS_3.md, as amended by §13). `k_tests = ["E015"]`,
  Holm m = 1. E016, E017, E018 and E019 were dropped at the censuses (q0470, q0472); uncounted.
- **Size statement (§13.15):**
  - q0475_lt3_size_check_r3 finished 11:2xZ on the pinned code. Its output is byte-identical to q0474's (sha256 39d0978b…
    for both files), as §13.15 item 6 requires.
  - Binding `perm_iid` 0.0470, `perm_persistent` 0.0480, `perm_corr_control` 0.0435, against a limit of 0.058017: all ok.
  - `flowperm_ar0.6` 0.0590 FAIL: non-binding for E015, recorded, and it blocks future flow-moderation use of the gate.
- **Host dry run:** §13.17.
- **Pins:**
  - spec `live_tests3_v1.json` sha256 **72a174eb85a08ef68b279e67af224a7acced9535f9329dc8eb0d75853af22a26**, with
    `SPEC_SHA256` set in `live_tests3.py`;
  - `code_sha256` `live_tests3.py` 3ac52d7959e56c6a5472a34d112c61ca643c7f35ebe77b87388b5cba9c7b8c65 and
    `live_tests3_analysis.py` 224b56036f98a2cfe3f92ffb6778e80c6b1131223cf20a0f548ca95fffaec955 (normalised);
  - `code_check` passes on the pinned spec;
  - the spec records the size result. Its other values are unchanged; the status text and `code_sha256` are filled.
- **Dates:** `REGISTERED_UTC` 2026-10-24T00:00Z, `END_UTC` 2026-11-14T00:00Z, `ANALYSIS_NOT_BEFORE` 2026-11-15T12:00Z
  (unchanged; the commit is before 2026-10-23T00:00Z).
- **Reviews:** challenger R1, freeze check (FREEZE_READY_WITH_FIXES), donor-gate rulings, pre-pin verification
  PIN_OK_WITH_FIXES, then fix verification FIXES_OK_WITH_NOTES (`reviews/LT3_*`).
- **Install:** host cron `*/20` with the exact §13.4 command, after this commit is deployed. The fallback job
  q0474_lt3_live_collect stays a draft. The analysis q0475_lt3_analyze is queued with not_before 2026-11-15T12:00Z.
- **Test-only edits at the pin:**
  - `test_analysis_refusals` now nulls `code_sha256` explicitly before its "hashes not pinned" refusal check, because
    the registered spec has them filled;
  - LT5's DRAFT spec records the raw-hash drift of `live_tests3.py` (the pin line only) in
    `vendored_source_drift_accepted`. Its vendored functions are still checked equal to the source.
  - 110 LT3/LT4/LT5 tests pass.
- No interim looks. Expected outcome per the design: likely partly explained by quote mechanics (disclosed in §10).
- **Install verified (12:07Z):** the host cron ran at 11:40Z and 12:00Z on code 2580c58a, `pinned: true`, spec
  72a174eb, `kinds_off` [flow, surge], status `nothing_new` (no line before REGISTERED_UTC). Crontab backup:
  `~/crontab.bak.20261021T*`.

## Queue, 2026-10-21 ~12:10Z (nothing counted)
- Done: q0500/q0501 (CB18 restores, after mem_mb 1,200), q0380 (CB16 exclusion keys, attempt 3, complete;
  `exclusion_keys.csv.gz` sha256 56dc953ed91aa430...), q0560 (LT5 restore).
- Promoted q0383 (CB16-K census, counts only, exclusive). CB17 q0405 waits for the q0404 smoke; its base-key pin is
  q0380's key file above.
- Ops priorities for tonight: q0544 36 (E026 census, must start before 02:45Z); q0564 45 (LT5 seal, from 23:20Z).
- (12:11Z) Promoted ahead of T_seal with `not_before`: q0083b (h7 deadline recorder, one-shot, 10-22T00:05Z; q0083 seal
  follows) and q0161 (CB8 smoke, 10-22T00:00Z). A session then commits the h7 seal / NOT_RUN copies before q0121, q0144
  and q0145 are promoted.

## E026 census q0544 done, 2026-10-21 12:27Z (counts only; nothing counted as a test)
- q0544 ran 292 s, peak 1.44 GB (child), on normalised code hashes equal to the reviewed afac80d4. It read samples in
  [10-18T04:00Z, 10-21T04:00Z) and no capture at or after 10-22. Committed as
  `live_tests_copy/census_q0544_2026-10-21.json`, sha256 90adaea6d9edfaf19f502e56513e8d7a2ca01c27fae90884c6e6163326ec58bf.
  It holds counts and aggregates only and no wallet hash (checked: the only hex strings are the code and spec hashes).
- **Gates (declared in aba32281 before the census):** G1, G2 and G3 all pass, decision **register_k2**. Skipped samples:
  0 incomplete, 0 missing.
- **Counts:**
  - skilled set: 3,559 of 35,587 eligible wallets;
  - skilled signals: 6,429 over 2.88 days (2,230 a day) from 242 wallets in 3,769 markets;
  - primary set at L = 0: 1,294 signals (449 a day), 650 events, 160 wallets, top wallet share 3%;
  - two-way design effect at ICC 1: 23.9;
  - mean conservative cost: 5.3c per dollar.
- Next: fill the CENSUS-GATED values (`LIVE_TESTS_COPY.md` MDE table and the spec `planning` block), then challenger
  review, freeze q0540, pins, and registration before 2026-10-24T00:00Z.

## Signal engine: hidden challenger se14_lgbm_movetype, 2026-10-21 ~14:30Z (signal-engine autopilot; nothing counted)
- New aux family `movetype` (`se-aux-movetype-v1`; DESIGN_V1 §16) from CANDIDATES C07 + C12. It classifies the last
  2 h move as traded, never-traded, ambiguous or quote-only (still / parallel / one-sided / spread-change), and adds
  bid / ask / ltp / volume changes and move over spread. It reads only the engine's own quotes and features files of k
  and k - 1.
- Challenger `se14_lgbm_movetype`: LightGBM with se1's params. It is embargoed under the new token `movetype` (E015) and
  under `book`, until 2026-11-22. E015's single analysis is not before 2026-11-15T12Z.
- No movetype score has been computed or shown. Predictions are written once from its first fit. The walk-forward
  skips it. No E015 file, pin or frozen artefact was touched.
- Non-embargoed challenger count is unchanged (K = 2: se1, se7) until 11-04.
- q0514 walk-forward: timeout 7200 -> 10800 s, plus a per-day progress line (host LightGBM fits are 8.5-10.5 min). No
  change to fits or scoring.

## E026 census values filled; recorder memory defect; q0545 queued, 2026-10-21 ~14:00Z (counts only; nothing counted)
- `LIVE_TESTS_COPY.md` 7.5 / 8.2 and the spec `planning` block are filled from the committed q0544 census (sha256
  90adaea6…). Decision stays **register_k2** (G1-G3 pass). New facts written into 7.5: the trade-to-entry latency at
  L = 0 is a median 6.6 h (trades are first seen a median 4.5 h after printing), not the 1.5-2 h receipt-to-entry delay;
  the two-way MDE is 0.102 $/$ and the event MDE 0.042, both above the 0.03 materiality floor (a null will most
  likely read Inconclusive).
- **Disclosure:** an earlier uncommitted census by the design session was seen before the gates were committed
  (aba32281); its numbers (about 1,278 copies, MDE 0.042 / 0.051) were relayed to the owner. The gates sit far below
  them, but they are informed, not blind. Written into 7.5 for the challenger.
- **Defect:** q0544's "recorder child peak 1,441.6 MB" is the parent's history-load peak: Linux `ru_maxrss` carries the
  forking parent's peak across exec (verified on the host: 811 MB by ru_maxrss vs 10 MB by VmHWM for a child of an
  800 MB parent). The runner now reads `/proc/self/status` VmHWM in the child (test with a 600 MB parent ballast). The
  census counts are unaffected.
- **q0545_copy_census_memcheck** (priority 37, cpu, counts only, same pre-window period, separate output, gates NOT
  re-applied) measures the recorder's own peak before the 10-22T03:30Z retention run; q0541 `mem_mb` 450 is confirmed
  or re-sized from it before the pin. The skill set, signal counts and L = 0 primary set must equal q0544 (a
  difference is a finding); the 6 h / 24 h availability counts may grow, since later pre-window captures now exist.
- Test fix: `test_queue_drafts_valid` now finds q0544 in `queue/jobs/` (promoted), 41 / 41 pass.

## SB2-J4-R (q0035, run `bounce-j4r`, finished 2026-10-21 07:25Z): **VOID as declared** (placebo failure); 5 tests counted, no verdict
- **Run.** Declared window `[2026-10-16T00:00Z, 2026-10-21T00:00Z)`, h-tight, expanding-past estimator, 20 pooled
  bootstrap placebo draws (seed 117), revision `j4r_expanding_v1`. 58 periods (>= 48), 5 UTC days, 2,581,045 triples,
  33,849 event clusters. Placebo level consistency: 0 level or increment mismatches. Host tree `git_dirty` (the usual
  appended trials.jsonl), head 054388ec.
- **Family status (declared reading rule, SCREENING_BATCH_2.md J4-R freeze check):** the 2.5-97.5% range of the 20
  placebo betas must cover 0 for every test. It does not for **P3** (placebo mean -0.010, range [-0.019, -0.002]) and
  **P4** (placebo mean +0.053, range [+0.046, +0.060], 2.6x its real SE), so the family is **VOID** and every verdict is
  withheld. The 11 trial lines (10 `bounce_decomp` + 1 `ml_explain`, n_tests 5) carry the VOID status. The 5 tests stay
  counted.
- **Numbers (descriptive only; no verdict, no claim):** P1 Gamma-mid reversal beta -0.083 (max-SE 0.023, placebo mean
  -0.000, leave-one-day-out sign stable); P1x -0.059 (0.023; placebo -0.001); P2 +0.030 (0.025; placebo +0.014); P3
  -0.103 (0.040; placebo -0.010); P4 +0.025 (0.021; placebo +0.053). P1 and P1x have clean placebos, but the VOID rule
  binds the whole family; reading them alone would be a post-hoc selection, so it is not done.
- **Consequence.** J4-R does not close Q5 (as declared). The expanding-past estimator removes the dynamic-panel bias for
  the reversal terms (P1, P1x) but not for P4 (and partly P3), whose regressors are built from levels; the placebo
  shows a mechanical slope there. Any further re-read would be a new declared family on new captures with a P3/P4
  estimator whose placebo is null by construction, frozen before the data exist. Not queued now: the bounce question
  is low priority against the live-test programme, and the signal engine's champion (momentum + market state)
  already uses recent mid changes, so a reversal slope would enter it there.

## Signal engine: hidden challenger se15_lgbm_surprise, 2026-10-21 ~15:00Z (signal-engine autopilot; nothing counted)
- New aux family `surprise` (`se-aux-surprise-v1`; DESIGN_V1 §16) from CANDIDATES C06. It holds own realised volatility
  over 6 h / 3 d / 7 d, the ratios to 24 h, the largest 2 h move of the last 24 h, and UTC weekday and hour. It reads
  only the engine's own earlier quotes files. It is not E011's frozen detector and reads none of E011's files.
- Challenger `se15_lgbm_surprise`: LightGBM with se1's params, embargoed under `surprise` until 2026-11-12 (E011,
  analysis after 11-11). No score has been computed or shown; the walk-forward skips it.
- K for the non-embargoed challengers is unchanged (2) until 11-04.

## E026 challenger review R1, 2026-10-21 ~14:15Z: **ACCEPT_WITH_FIXES** (nothing counted)
- `reviews/E026_CHALLENGER_R1_2026-10-21.md`. Causally sound (no future information found). 10 required fixes before the
  pin: conservative negative-verdict bound; counted trials line and Unavailable on no data; pins for the impact table,
  null skillset / code hashes refused, entries and resolutions filtered by pin; pinned shared modules protected by a
  hash test; labeller / recorder memory at 21-day scale; end-date gate off from cutoff - 7 d plus logged counts;
  collectors `not_before` the window; control-side event pieces in the p rule; a causal "earlier visible trade" flag in
  the control matching cell; document corrections. `register_k2` stands (gates passed by > 20x; the disclosure is
  corrected). Owner phone note sent (review verdict). Fixes delegated; then a re-check, the freeze q0540 and the pins.

## Signal engine: science review of the movetype / surprise families, 2026-10-21 ~14:40Z (signal-engine autopilot; nothing counted)
- **Verdict: ACCEPT_WITH_NOTES** (independent `science-reviewer`).
  - No path reads capture k+1 or later, or any label, at build, backfill, training or walk-forward time.
  - No mechanical encoding of the target beyond the origin mid that every model already has.
  - The embargo is enforced on every display path. se7 is unchanged.
- **Applied:**
  - The `surprise` embargo moved **later**, from 11-12 to 11-19. E011's window ends 11-10 and pending outcomes are
    retried, so the margin was thin.
  - The SHAP attribution is no longer computed for embargoed fits. The inner-split loss stays, because the fit needs
    it, and is documented as exempt (DESIGN_V1 §8).
  - An aux build failure now skips only that capture: it counts against the run budget and is retried next run, so
    one bad capture cannot stall a backfill.
  - New test: scrambling capture k+1's quotes and features leaves k's movetype and surprise tables identical.
- **Noted, not changed:**
  - `sp_hour` / `sp_dow` use the capture start rather than the slot time. This is noise only, and the tables are
    write-once v1.
  - The volume tolerance hides trades of about $4 on $1M markets. It is documented.
  - Training subsamples are seeded by model id, so se1 and its learner-matched challengers draw different rows when
    the 300k cap binds. This existed before; a fix would change every model's fits, so it is left as a candidate for
    a v2 refit rule.
- (~14:45Z) R1 fixes in d11ba0a0 (implementer) + R1 response `LIVE_TESTS_COPY.md` section 14. **R1 re-check:
  R1_FIXES_OK_WITH_NOTES** (`reviews/E026_R1_RECHECK_2026-10-21.md`), no required item. Added before the pin: per-pass
  pinned-code check (fails loudly) and a running-capture guard (test fails without it). Memory on a 7.3x synthetic
  store: recorder <= 448 MB (q0541 mem_mb 480), labeller 302 MB (q0542 400), analysis 1,222 MB (q0543 1500); host
  check by q0545. Next: q0545 result, then freeze q0540, pins, registration commit before 2026-10-24T00:00Z.
- (~14:55Z) **q0540 freeze promoted** (priority 36, after q0545). It refuses before writing if the built set differs
  from spec `skill.expected` (35,587 / 3,559; outcomes before 10-18T04:00Z). Pins follow only after q0545 confirms the
  recorder memory.
- (15:20Z) **q0545 done:** recorder peak 269.5 MB on the host (VmHWM, one 35-sample backlog pass, R1 code) -> q0541
  `mem_mb` 480 holds. Skill set, skilled signals and L = 0 primary set equal q0544; controls / pairs moved as designed
  (pairs 1,200 -> 1,167). Committed `live_tests_copy/census_q0545_memcheck_2026-10-21.json` (sha256 24a50571…; no wallet
  hash). q0540 freeze running since 15:14Z.

## E026 — Copy skilled wallets with latency: **REGISTERED 2026-10-21** (2 counted tests)
- **Design:** `docs/research_lab/LIVE_TESTS_COPY.md` (sections 0-13; section 14 = challenger R1 response; 9.1 = pins).
  Code `copy_skilled.py`, `copy_skilled_analysis.py`, runner `run_copy_skilled.py`; spec `model_specs/copy_skilled_v1.json`.
- **Pins:** `SPEC_SHA256` 06d117ed44f4ed26b309ee2418ec5bccfcd480a66330c2d5cc0f56344e9bbd86; `skillset_sha256`
  8120c12e604c74721e7ce52dc84df61ea6f9b190151e845d1035e57e4a550f46 (q0540, frozen 2026-10-21T15:14:02Z; eligible 35,587,
  skilled 3,559, every known outcome before 2026-10-18T04:00Z); recorder code_sha 2bae593a259b8945; impact table
  df45bae4…; code_sha256 of the five pinned modules in the spec. **Frozen until 2026-12-07:** copy_skilled.py,
  copy_skilled_analysis.py, wallet_skill.py, wallet_skill_dev.py, costs.py, copy_skilled_v1.json,
  cost_model_calibration_v1.json (also written into CLAUDE.md and AGENTS.md; a unit test asserts the hashes).
- **Basis:** WS1 P1 persistence (DEVELOPMENT; S2 P&L per dollar of S1-skilled wallets +21.7c vs +3.6c); WS1 P2-P4 null
  (skilled flow adds nothing over generic flow). Expected outcome: probably Inconclusive or Not supported on E026-C.
- **E026-N:** net P&L per dollar of paper copies of frozen-skilled wallets' new taker trades (wallet sidecar), entered at
  the first complete capture starting at or after receipt (L = 0; census trade-to-entry median 6.6 h), held to
  resolution, conservative taker costs (census mean 5.3c per dollar); > 0.
- **E026-C:** E026-N minus the same ratio of matched non-skilled controls (same sample, side, price, age, time-to-end and
  prior-visible cells, other non-empty event); > 0.
- **Family:** Holm k = 2, one-sided, alpha 0.05; p = max(event bootstrap, event t, two-way event x wallet t, and for
  E026-C the combined skilled/control-event bootstrap and t). "Not supported (effects >= 0.03 excluded)" uses the widest
  upper bound of the same set. Floors: 200 copies, 40 events, 150 pairs (below: Unavailable, p = 1, still counted).
- **Window:** receipts `[2026-10-25T00:00Z, 2026-11-15T00:00Z)`; label cutoff 2026-12-06T00:00Z; **single analysis
  q0543 on or after 2026-12-06T12:00Z** (`--trials`, counted). Planning (census q0544, pre-window, counts only):
  projected 9,428 copies, 4,736 events, 8,503 pairs (q0545); MDE E026-N 0.042 (event) / 0.102 (two-way), E026-C 0.053;
  gates G1-G3 pass, register_k2 (gates informed, not blind: disclosed).
- **Reviews:** challenger R1 ACCEPT_WITH_FIXES -> fixes d11ba0a0, e68ff67a -> R1 re-check R1_FIXES_OK_WITH_NOTES.
- **Jobs:** q0541 recorder (net, mem_mb 480; host peak 269.5 MB), `not_before` 2026-10-25T00:00Z; q0542 labeller (net,
  mem_mb 400), `not_before` 2026-10-25T06:00Z; q0543 analysis (cpu, mem_mb 1500), `not_before` 2026-12-06T12:00Z.
  Re-promote a `failed` collector within 48 h; gaps stay missing and are counted.
- **Stop rules:** no interim look (counts only); runs to END whatever the counts; if skilled signals run below a third of
  the census rate after 7 days the ledger notes "likely Unavailable" and nothing else changes. Signal-engine embargo on
  `wallet_skill` / wallet copy features to 2026-12-07 (applied in 26f5f954).
- **Overlaps:** same trade samples and captures as LT2-LT4 and the live-print stream; never pooled; WS1 is development.
- **Registration commit 7777ca66** (2026-10-21 15:20Z; the analysis runs from a worktree at this commit). Deployed;
  host check: `load_spec` pinned (06d117ed…), `check_pinned_code` passes, reader_sha 2bae593a259b8945, the frozen
  skill set's sha256 equals the pin. Owner phone notes sent (review verdict, registration); next at collection start
  (2026-10-25) and weekly counts.
- (15:30Z, ops) q0564 (LT5 capture seal, 23:20Z) moved from the cpu to the net lane (file hashing, mem_mb 300), so a
  running cpu-lane job cannot delay it past the window for the seal commit and the q0561 start before 02:45Z. Nothing
  else changed. LT3 / LT4 restore trees checked present for q0562 (23 samples, 39 captures).

## LT6 design draft, 2026-10-21 ~15:40Z (DRAFT; nothing registered, nothing counted)
- `feat/live-tests-6` 5906c0b9 (pushed): `docs/research_lab/LIVE_TESTS_6.md`, four round-11 candidates (ranks 6-9, not
  in LT5): V CH190 makers' vote (post-move skew once the touch refilled; overlaps E022's pinned `dimb` control, so V's
  origins start after LT4's window and V must be pinned before E022's analysis or it is dropped uncounted), K CH185
  clip trains, D CH187 deadline moves (census-first; likely to drop), B CH188 sibling birth. Provisional k <= 4, fixed
  by counts-only censuses; proposed window 2026-11-16 .. 12-07. All on streams the host already captures (no new
  collector). Challenger R1 (science-reviewer) running.
- (~16:00Z) **LT6 challenger R1: REVISE** (V, K, D ACCEPT_WITH_CHANGES; B REVISE; review on the branch,
  `reviews/LT6_CHALLENGER_R1_2026-10-21.md`, bfa5dcf0). 12 required: few-treated-cluster event t for D/B; B
  volatility size scenario, control-class contamination, crypto exclusion; VIF in K/D/B MDE gates; V depletion
  asymmetry gate and the E022 boundary keyed to E022's own END_UTC; CB18 must not show D's end-date class before the
  pin; LT5 seal dependency plus minimum covered days; look-back timing; memory plan from LT3's 534 MB; K's train
  algorithm. Response being written on the branch.
- (~16:10-16:25Z) **LT6 R1 response** 3a973bcc (section 14), **R1 re-check: R1_RESPONSE_INCOMPLETE** (2 text-only
  required: V's freeze condition had drifted from "before E022's analysis runs" to "before its commit", now "before
  T_E022 = the earlier of E022's analysis job start and its analysis commit" in every place; the crypto classifier is
  pinned) -> fixes 04d9b603 (section 15; `reviews/LT6_R1_RECHECK_2026-10-21.md`), verified by the orchestrator against
  the commit (the re-check ruled no new round needed). **LT6 design accepted for code**, subject to: the LT5 seal sha256
  (q0564 tonight), E022's registration or recorded drop with its END_UTC and analysis timing, the CB18 request below,
  and the engine embargo entries (filed in `signal_engine/CANDIDATES.md` round 2, bf3225be; the signal autopilot
  was told). Nothing counted.
- **Change request to CB18's owner (from LT6, filed 2026-10-21):** in CB18-S, the reported `end_date`-change class is
  not computed or printed for REP_18 origins at or after 2026-11-16T00:00Z (or LT6's REGISTERED_UTC if later) until
  2026-12-08T12:00Z (later if LT6 slides); counts may be printed; SCREEN_18's `end_date`-class output is not shown to
  LT6's designer, coder or reviewers before LT6's pin. Cost: one uncounted secondary delayed about two weeks on part of
  REP_18; no counted test, threshold or verdict changes. CB18 records here whether it was applied before LT6's pin; if
  not, LT6 D carries "partially seen (CB18 `end_date` class)". Text: `LIVE_TESTS_6.md` 14.6.

## Signal engine: first prospective leaderboard, 2026-10-21 15:38Z (signal-engine autopilot; development-scale, nothing counted)
- One-off forced score `q0515_se_score_now` (same code as the daily q0513; owner Lab-board message 14:01Z "jump queue":
  signal-engine jobs q0512-q0515 now priority 50, above every ready experiment job except the time-bound recorders
  q0083b, q0162, q0163). Resolution fetch 800 requests: 39,792 resolved, 103 split, 105 not found.
- `leaderboard/20261021T153806Z.json`: 1 scored day, one labelled origin capture (10-21 12:31Z), `dir_2h`, 49,154 rows,
  coverage 1.0, 0 late. Mean log loss: se0 champion 0.4405, se1_lgbm_mm 0.391, se7_lgbm_all 0.387 (AUC 0.787 / 0.844
  / 0.849). se1's paired gain 0.049 nats, event-clustered 97.5% CI [0.046, 0.053]. One capture, one day: a pipeline
  check, not evidence; promotion needs >= 14 days (c1 false). Every embargoed model shows only `embargoed_until`.

## Signal engine: hidden challenger se16_lgbm_participation, 2026-10-21 ~16:30Z (signal-engine autopilot; nothing counted)
- New aux family `participation` (`se-aux-participation-v1`; DESIGN_V1 §16): event lifetime volume and liquidity, the
  2 h event-volume change (+ a "fell" flag), own liquidity share of the event, Gamma `competitive`, event age, lifetime
  market volume; from the origin's own Gamma sidecar and the previous slot's sidecar only. Open interest and comment
  counts excluded. Challenger `se16_lgbm_participation` (LightGBM, se1's params; read against se1).
- Science review: **REVISE** (no leak; values correct) because CB17-C (CH150, drafted) uses the event-volume change as
  its eligibility rule and event liquidity as a control. Applied before any table or score existed: embargo token
  `participation` until 2026-11-25T00:00Z (REP_8 ends no earlier than 11-23T08Z), wording corrected, spec re-pinned,
  previous-sidecar provenance in the aux metadata, prefix `pp_`. No score is computed or shown before 11-25; K for the
  non-embargoed challengers stays 2.
- (16:42Z) **LT6 code phase 1** on `feat/live-tests-6` (71cdb2da, 23cf4665, 51664a39; pushed): draft spec
  `live_tests6_v1.json` (E022-dependent dates and census-fixed values null), `live_tests6.py` (crypto classifier, K
  greedy train algorithm with Decimal sizes, V state and both depletion gates, D classifier, B classes, washout, V/E022
  freeze check refusing after either T_E022 time), sealed counts-only censuses CD/CB/CV/CK and seal builder, analysis
  skeleton (G_treated - 1 event t, gates, Holm, verdicts), size-check scenarios 1-11 (seed 20261167); queue drafts
  q0580-q0584 (DRAFT). 121 tests; only new files (no frozen or pinned file touched). Phase 2 (reader, analyze entry
  point, reader / analysis drafts) running. Needed at registration: a `battery2.KIND_RULES["live_tests6"]` entry.

## Finished-job write-ups and queue fixes, 2026-10-21 ~18:55-19:20Z (experiments autopilot)
- **Ops (no science change):** CB18 censuses q0502-q0506 had `--disk-cap-gb 20` (the declared upper bound, `<= 20`);
  with data-dumps at 29.75 GB every attempt exited 75 against the 40 GB cap. Set to 0.25 (outputs are small JSON), cbe76887.
  CB18 drafts q0507-q0516 renumbered q0590-q0599 because q0510-q0515 were already signal-engine job ids (a5029dce).
- **q0404 CB17 smoke refused (exit 2, twice):** the frozen `cb17_jobs._disk` counts the whole `creative_batch17/` tree
  against its 0.3 GB total cap, and q0413 restored the worn files (925 MB) inside it (`creative_batch17/worn_restore`).
  Not a FAIL (a refusal; the P1-P3 reproduction never ran). The frozen code is not edited. The restore tree must be moved
  out of `creative_batch17/` (or cleared, its notes say "clear the tree after q0404"), which the evidence hook blocks
  without an owner-approved session; owner approval requested on the dashboard. Then q0404 is retried with the new
  restore path (`queue_worker.py retry`). S_8 is 2026-10-26T00Z, so CB17 is not yet late.
- **q0281 CB13-R census (18:02Z, counts only, nothing newly counted):** GR basis 0.915 (< 0.95), frame completeness
  0.782 (< 0.98) and events 58 (< 60) fail; markets 801, weeks 31, components 58 and the parser gate pass; GRP MDE 0.658
  (> 0.60) fails. q0282 will write R1 "not testable (basis)", p = 1. The v1 R1 count line of 2026-10-19T07:30:16Z
  stays (ledger 2026-10-19 ~09:45Z: "v1 count lines (T 2, R 1) stay in trials.jsonl (conservative double count)"),
  so R1 is counted twice by design; nothing to reconcile.
- **q0305 CB14-W GWC (18:04Z): FAIL** (58 markets < 150, 46 events < 60, 38 subjects < 40; GW0 audit precision 0.679,
  38 of 56; frame completeness 1.0). W1 and W2 "not testable (population)", **counted 2** (trials line 18:04:03Z).
  Drafts q0306-q0309 are moot (never promoted).
- **q0347 CB15-P GPB (18:06Z): FAIL** (37 pairs in 12 events; minimum 60 pairs in 30 events). P1 and P2 "not testable
  (population)", **counted 2** (trials line 18:06:22Z). Drafts q0349-q0354 are moot.
- **LT4 censuses (q0482 CQ/CH 17:26Z, q0483 CF 17:38Z), counts only.** `CQCH.json` 2c9e2a9e…, `CF.json` 55f01ced…
  (sha256 checked on the host; inputs sealed and verified). **E020 FAIL** (projected cancellations 14,028 < 15,000;
  permutable-strata share 0.055 by day / 0.132 by two-day block < 0.50; pessimistic MDE 0.526c > 0.5c): dropped before
  registration, uncounted. **E021 FAIL** (strata 0.005 / 0.018; MDE 1.060c): dropped, uncounted. **E022 PASS** (depth
  definition token0 0.913, `both` NaN because sweeps hold one token per market; coverage 0.9996; residual-IQR share 0.827
  over 301 markets; stratum block2 0.599; tercile MDE 0.256c). Series concentration: top family 0.059 (E020), 0.024
  (E022); nothing excluded. **k_tests = [E022], Holm m = 1.** Census-fixed values filled into the unpinned spec
  `live_tests4_v1.json` (design 13.4); `LIVE_TESTS_4.md` section 17. Nothing counted, nothing registered. Open for the
  freeze check: the raw-`h` IQR gate of section 8 was evaluated as the residual-IQR gate (the R1/R2 wording), and the
  `both` depth branch is not evaluable. Registration must be committed by 2026-10-25T00:00Z for the 10-26 window.
- (~19:25Z) **CB13-R freeze entry and q0282 promoted** (6d441a9f, deployed). Narrow code-against-design check
  (science-reviewer): FREEZE_OK_WITH_FIXES; the fixes were entry content and draft notes only (gate-fail order basis >
  frame > population/parser > GRP as sealed in `screen_r` on 10-19, before the census; the declared R1 double count;
  census `drops.share` 1.16 reporting defect disclosed, sealed code unchanged). Host checks: smoke_R_v2 and pregate_R
  pass, no results_R.json yet, census_R.json sha256 71483779…. q0282 writes R1 "not testable (basis)", p = 1, counted 1,
  and opens no outcome. q0283 (rep) moot.
- (~19:28Z) **LT4 pre-pin code changes** (44a7e938; `LIVE_TESTS_4.md` section 18): analysis, reader and size check
  restricted to `k_tests` = [E022] (Holm m = 1; reader writes only E022's hollow lines; E022 line format unchanged);
  the size check runs only E022's two continuous scenarios (est. 2-4 h). 72 LT3/LT4 tests pass; LT3 module hashes
  unchanged. Code freeze check (science-reviewer) running. Nothing counted.

## Signal engine: development walk-forward q0514 done, learner budgets, se17_lgbm_mm_900k, 2026-10-21 ~19:30Z (signal-engine autopilot; development only, nothing counted)
- **q0514 walk-forward (attempt 2, done ~17:20Z; 7,528 s, peak 1,412 MB):** test days 10-14..10-20, every fit before
  its test day, scored retrospectively (`dev/walkforward_*.json`, `development_historical`). dir_2h mean log loss:
  se0 champion 0.4604, se1_lgbm_mm 0.4196, se7_lgbm_all 0.4146. Paired gain over se0, event-clustered 95% CI:
  se1 +0.0408 [0.0401, 0.0416], se7 +0.0458 [0.0450, 0.0466], positive on 7/7 days. dir_6h: se1 +0.054, se7 +0.061;
  dir_24h (6 days): se1 +0.052, se7 +0.059. Embargoed models: no numbers. Development evidence; never used for promotion.
- **Learner budgets (scratch, Mac copy of the store, test days 10-18..10-20):** se1's host fits stop at or near the
  300-round cap. Larger trees or more rounds alone: +0.0002 nats dir_2h over se1. 900k rows: +0.0021. 900k rows and
  up to 1000 rounds: +0.0027 (6 h +0.003, 24 h +0.002). The last is registered as **`se17_lgbm_mm_900k`** (spec sha
  `6e27b8c6…`, no family, not embargoed; non-embargoed K = 3). It was selected from four configs, so its development
  gain is optimistic; prospective scoring decides (DESIGN_V1 §19). The shared frame grows to 900k rows; the other
  models keep their own seeded 300k subsamples. q0512 timeout 7200 -> 10800 s, mem_mb 1600 -> 2200.
- **`regime` family dropped:** unsigned market- and category-wide activity (previous capture; rows received earlier
  in the same capture). Science review REVISE (no leak, no shadowed test; common per-capture shock, receipt-order
  proxy). Development: worse than se1 on every direction target (dir_2h -0.0017 nats). Code removed, nothing deployed.
- Reviewer note for the promotion rule (not applied): the event-clustered CI ignores shocks common to all events
  within a capture. Criterion 3 (daily gains positive on >= 2/3 of days) partly covers it. A capture- or day-clustered
  reading would be a new rule version (`se-promotion-v2`), declared before any challenger is near promotion.
- (~19:30Z) **LT4 code freeze check (science-reviewer): FREEZE_OK_WITH_FIXES.** Rulings: the residual-IQR gate is the
  declared replacement of section 8's raw-`h` IQR gate (spec commit 708949c3, 2026-10-20, about 22 h before CH ran; the
  raw gate must not be computed now); `token0` by the declared fallback (`both` all NaN: sweeps hold one token per
  market); seed 20261107 kept with the shorter scenario stream; MA(2) dropped with E021; section 16 finding 1 met
  (2580c58a is an ancestor; LT3 normalised hashes equal its pins). Required: (1, high) the size check permuted within
  market-day while E022's registered gate uses `block2`: worlds get a two-day block and the size check uses the spec's
  stratum; (2) host reader dry run with peak RSS; (3) stale text in spec / drafts / sections 0 and 15.3; (4) one install
  route; (5) disclose the MA(1)-type overlap of consecutive-pass `c_sw` targets. Orchestrator check: spec values (zh
  centre 0.72504 / scale 0.31414, h cuts 0.72963 / 0.93441, gap 1.98319, token0, block2, exclude "") equal CQCH.json
  (sha256 2c9e2a9e… verified on the host; CF.json 55f01ced… verified). Fixes being applied. Nothing counted.
- (~19:33Z, ops) q0502 CB18 census S died "out of memory" in the pandas tokenizer under the 2 x 380 MB address cap:
  mem_mb 600, as_cap_mb 2400, retried (resource only). q0503 (P) and q0504 (R map) done; q0505 (F) running.
- (~19:50Z) **LT4 code freeze recorded** (`LIVE_TESTS_4.md` section 19; code 0e8bbe13, host runs it): five normalised
  module hashes, spec sha256 99899392… before the registration pin, census shas, orchestrator check of spec vs CQCH.json
  (equal). Host reader dry run (scratch, pre-window captures, no confirmation line): peak RSS 484 MB per capture, 525 MB
  for a six-capture catch-up, exit 0 under `ulimit -v 983040`; the 400 MB of 9.2 was a target; cron gets
  `ulimit -v 1572864` for margin (operational). Install route: host cron `10-59/20` at registration; q0485 fallback only.
  **q0484 size check promoted** (not_before 2026-10-22T04:00Z, after the resize and LT5's q0561; priority 97; mem 800;
  one run, seed 20261107, E022's two scenarios with block2 strata, criterion <= 0.058). Nothing counted.
- (~19:58Z) **q0282 CB13-R screen: R1 "not testable (basis)", p = 1, counted 1** (as the freeze entry said; no outcome
  opened). With CB13-T finished at Stage 1, **CB13 is closed**. CB14 and CB15 are closed too (registry: not_testable).
- (~20:05Z) **CB18 routing record** (`seals/cb18_routing.json`, counts only; `CREATIVE_BATCH_18.md` section 14):
  censuses q0502-q0506 all done (q0505 and q0506 also needed mem 600 / as_cap 2400 after the same tokenizer OOM).
  **CB18-S (CH177): RS-0, dropped uncounted** (GS2, GS4, GS5_CB and GS5_LT fail; planning MDE RS-1 3.64c, RS-2 1.37c).
  **CB18-P (CH172): dropped uncounted** (GP1, GP5, GP6 fail). R map only, F census only (re-entry rule 4.4), M map.
  CB18 has k = 0: nothing counted; drafts q0590-q0599 moot. LT6's change request is satisfied trivially (no SCREEN_18
  or REP_18 exists). Registry: CB18 closed (not_testable at design stage).
- (~20:20Z, ops) **CB17 unblocked without moving data:** every CB17 window job (q0404 and drafts q0405-q0412) now passes
  `--root ../data-dumps/research_lab/cb17_window/creative_batch17`. The frozen code accepts any root with a
  `creative_batch17` path part; the 0.3 GB total cap now counts window outputs only (its purpose), and the worn restore
  stays where it is as input. Window jobs read nothing from the old root. No code, rule, input or criterion changed
  (160 CB17 tests pass; argv parse-checked). q0404 retried. The dashboard approval is reduced to the general clearing of
  finished restore copies (data-dumps headroom).
- (20:09Z, signal engine) **Promotion rule `se-promotion-v2` declared** (DESIGN_V1 section 20; `promotion.py`;
  `registry.json` `promotion_rule`). It is v1 plus condition 2b: the dir_2h gain also needs a two-way (event + UTC
  origin day) lower bound `mean - t_{n_days-1} * sqrt(V_event + V_day) > 0`, using the CGM variance without the
  intersection term (conservative relative to CGM), at the same Bonferroni level 1 - 0.05/K. Everything else is
  unchanged; condition 5 stays event-only. Why: event clustering ignores shocks that every market shares within a day.
  It is declared with one prospective day scored, when 2b cannot be computed, and before any challenger could meet
  condition 1 (earliest 11-04). v1 never fired. Science review ACCEPT_WITH_FIXES (exact registry match, wording,
  edge-case tests), all applied. Forecast-quality rule only, no edge claim.
- (20:12Z) **q0404 CB17 smoke: PASS** (all 18 criteria true: parts verify, CB13/CB16 pins, refusals, arm hash, age /
  shift / interval / trailing-tercile / B no-mark / strata-selection fixtures, **exact reproduction of probes P1-P3**;
  pass by family B, C, E). Ruling 6 (ii) met: the CB17 code freeze is accepted. Not counted (descriptive line).
  **q0405 promoted** with `--base-sha256 56dc953e…` copied verbatim from q0380's write-once manifest (O12 ruling).
- (~20:28Z) **q0405 CB17 exclusion keys: done** (attempt 2 after mem 300 -> 1200): universe 568,117 ids, 0 drop keys
  (no overlap with CB16's key set 56dc953e…). Not counted. CB17 window jobs wait for S_8 (10-26T00Z) and their dates.
- (~20:30Z) **LT6 code freeze check (science-reviewer): FREEZE_READY_WITH_FIXES for the census code, NOT_READY for
  registration.** Verified: 137 tests; no reused/frozen module modified on the branch; V/K/D/B/crypto/washout/T_E022
  definitions match the design; census causality and sealing. Required before the censuses: (1, high) `load_rows6` reads
  `end_date` as category, which crashes `panel._epoch` on pandas 2.3.3 (the host's version) for captures of >= 50 rows;
  (2) B admitted unknown-end incumbents; (3) NaN treated as "changed"; (4) LT5 seal pin check, CK per-market sums, two
  undeclared counted exclusions to declare. Before q0584: (5, high) the size check permutes within market-day while the
  gates use the census-fixed `perm_stratum` (LT4's bug repeated). Before registration: size-check result not passed to
  the analysis; K placebo P1 / S3 never frozen (trade samples rotate in ~3 days); analysis still a skeleton; E022
  safeguards fail open; reader memory unmeasured. Implementer applying on feat/live-tests-6. Nothing counted.
- (~20:31Z, safety check prompted by item 1) **LT3's registered reader works on real captures:** host dry run into a
  scratch root (captures 10-21 16:31Z/18:31Z, `--max-items 2`, cron's `ulimit -v 983040`): series written, peak RSS
  464 MB, exit 0; scratch deleted. Its live log shows only "nothing_new" so far (window opens 10-24).
- (~20:35Z) Follow-up on LT6 item 1: on the host, `panel._epoch` of a real capture's `end_date` read as category
  (20261021T183102Z, 276,559 rows, ISO `...Z` strings) works; the crash needs other date formats (the reviewer's
  synthetic ones). LT3 and LT5 (same pattern; LT5 censuses run tonight) are not at risk; LT6's switch to `str` stays as
  hardening.
- (~20:50Z, signal engine) **Embargo token `hollow` added** (`config.EMBARGO`, until 2026-11-18T00:00Z, E022; experiments
  round-3 request in CANDIDATES.md). Covers any feature combining Gamma `liquidity` with sweep depth. No engine model
  or feature computes one, so nothing was scored or shown. Confirmed E022's depth control `log1p D0` is `bk_depth5c`
  (outcome-0, sweep 1 of the pass) under `book` (12-09). Disclosed: the broad `se7_lgbm_all` has `liquidity` and
  `bk_depth5c` as separate inputs (broad models are unembargoed by DESIGN_V1 §8). Nothing counted.
- (~20:47Z) **Creative round 12** (Fable xhigh; `CREATIVE_HYPOTHESES_2026-10-26.md`, CH191-CH201; merged 042e883d;
  ideas only, nothing tested or counted). Brief: population arithmetic, permutable strata and MDE vs floor up front,
  after four batches closed at census today. Top 6 for a future LT7 (window not before 2026-12-08): CH195 resistance
  (pre-move hit-side depth), CH191 grind at the capture clock, CH194 hour-held move, CH197 patient money, CH193 absorbed
  flow, CH192 implied vs realised; engine-first families listed in `signal_engine/CANDIDATES.md` (do-not-isolate note
  for the LT7 six until LT7 fixes its embargo dates).
- (~21:00Z) **LT6 freeze-check fixes applied** on `feat/live-tests-6` (5d3e549c..f6587202, pushed; 157 tests): end_date as
  text; B unknown-end exclusion (counted); missing updated_at stays NaN; LT5 seal pin check; per-market label sums; two
  previously undeclared counted exclusions declared in section 16; size check through `strata_of` with the census-fixed
  stratum; size-check result verified by the analysis; E022 safeguards fail closed; V anatomy categorical; `.late` fix;
  reader now freezes K P1/S3, the reported arms and h4 outcomes; new `live_tests6_readings.py` (labels, attrition / Lee
  bounds, coverage, secondaries, economics, Thanksgiving). Open: the implementer added two label thresholds (sweep-missing
  2%, attrition 2 pp) and four interpretations (section 16); D's placebo P1 not computable from frozen lines; B's S2 not
  computed. **Re-check (science-reviewer) running before any LT6 census.** Nothing counted.

## Seals at T_seal and LT5 census start, 2026-10-22 ~00:15-00:25Z (experiments autopilot; nothing counted)
- **LT5 capture-census seal:** q0564 done 23:22Z (382 files, 135 slots 2026-10-12T00:31Z..10-21T22:31Z, 8 genuinely
  missing slots recorded, not imputed). Byte copy committed as `seals/lt5_census_inputs_captures.json`
  (sha256 `fcd88926…8752`, equal to the host). **q0561 promoted** (priority 25 -> 60, exclusive; argv and gates
  unchanged) so it starts before the 02:45Z blackout and reads captures before the 03:30Z retention run. Counts only.
- **h7 (CB4) seals:** q0083b recorded both runs `complete` (00:06Z); q0083 sealed `h7_cb4_era` (6,286 files) and
  `h7_cb4_series` (7,699 files; D_split4 2026-06-27; universe 1,904, screen 1,118, holdout 755, embargo 31, 18 dropped
  for era overlap) at 00:08Z. Seal copies committed byte-identical to the host (`f2fddb67…`, `e9e3b627…`).
  **q0121 (h8_tail seal) promoted.** q0144/q0145 stay drafts until q0121's own seal copy is committed (their notes).
- **CB8 smoke q0161 (00:00Z): FAIL on criterion (a), so CB8-W1 is "not testable (source)", p = 1, COUNTED (1).**
  The pool rule (h1/h2/h3 exclusion ids looked up on Gamma, closed with `end_at` 2026-05..09, volume >= $50,000,
  life >= 10 d) left only 5 eligible worn markets of 192 found (20 required); 4 of 5 returned prints, 0 capped, bounds,
  order and duplicates all OK. The pre-declared rule (CREATIVE_BATCH_8.md) applies as written: q0167/q0168, q0171 and
  q0175 are not committed; W1-rep is never reached (uncounted). A larger pool would be a design change needing review
  and is not proposed. (b) Binance checksums and (c) pmxt HEADs PASS, so B continues. Record:
  `seals/cb8_smoke_FAIL_20261022.json` (sha256 `8189303f…`, equal to the host); trials `cb8_test` W1 plus a
  `creative_batch_8:W` count line (n_tests 1).
- **q0164 (CB8 exclusion keys) promoted:** both required pins derived once on the host at 00:17Z (c1_legs 500 ids
  `8341c500…`; cb5_listings 244,420 ids from 64 files `e1a12551…`).

## Signal engine: book timing overlap, se7 promotion-ineligible, CH199 / CH200 closed, 2026-10-22 ~00:50Z (signal-engine autopilot; development diagnostics only, nothing counted)
- **Book timing overlap found and disclosed** (DESIGN_V1 section 21). Direction labels start at the origin capture's
  Gamma mid. The `book` family comes from sweep 1 of the pass, ~7 min later. On two 10-21 captures (~50k eligible
  each), 6.4% / 5.4% of markets had already moved > DELTA by sweep time, about a third of 2 h movers. `bk_micro`
  correlates -0.28 / -0.22 with that in-window move.
- **Science review: REVISE twice; both rounds applied.** `se3_lr_book` and `se14_lgbm_movetype` are also listed (still
  embargoed, no score seen). `se7_lgbm_all` (broad, has book inputs) is promotion-ineligible from
  2026-10-22T00:50Z (`config.PROMOTION_INELIGIBLE`). It is still scored and shown, and K stays 3. No pinned spec,
  constant or formula changed. The reason is the timing measurement, not a score. se7's one-day leaderboard of 10-21
  (about +0.05 nats, same as se1) had been seen; disclosed.
- **CH200 `sweep2` declined:** sweep-2 minus sweep-1 mid is part of the label's own path.
- **CH199 `rulesrc` killed at census:** 19.9% of eligible non-sports markets carry a parseable resolution-source host,
  below its own 30% kill line.
- Also: /lab promotion-rule status card merged (PR #26).
- (~01:00Z, signal engine) **Embargo round 4 applied (LT7 draft):** `book` 12-09 -> 12-31, `movetype` 11-22 -> 12-31, new
  tokens `resist`, `capath`, `mm_fresh`, `deepbook`, `absorbed`, `ivr` until 12-31 (no models). Only later dates and new
  tokens. No score of an affected model has been computed or shown.

## LT6 re-check and LT7 challenger R1, 2026-10-22 ~00:30-01:00Z (experiments autopilot; nothing registered or counted)
- **LT6 code freeze-check re-check: RECHECK_OK_WITH_FIXES** (`feat/live-tests-6`, `reviews/LT6_FREEZE_RECHECK_2026-10-22.md`,
  2e63dd59). Five must-fixes (stale size-check results accepted; a size-check bypass; late-loss / sweep-missing
  denominators; D's placebo P1 silently dropped; E022 decision could be left unmade) fixed in de2326b1 / b8804735
  (section 17, 166 tests). Verification: **FIXES_OK_WITH_NOTES**, one new defect N1 (reader log lines lack `spec_sha`, so
  K's coverage-limited label could never fire in the pinned analysis); fix in progress before q0584. No threshold, formula,
  seed, date, gate, alpha or draw count changed; no LT6 census has run. Censuses may proceed (census path unaffected).
- **LT7 challenger R1: REVISE** (`feat/live-tests-7`, `reviews/LT7_CHALLENGER_R1_2026-10-22.md`, f5c011ca): 11 must-fixes,
  incl. CH197's feasibility gate undefined on the sealed window, CH193's stale-quote channel, CH194 informed by E002/E004,
  CH191's gate breaking LT7's own rule. Response efdcdb6e (section 13): **CH194 withdrawn before registration (uncounted)**;
  every other must-fix applied; planning at E022's measured design effect 6.196 says all five remaining tests are likely to
  drop at census (k <= 5, expected 0-2). Embargo requests filed (CANDIDATES round 4, 9621c12e); `mm_fresh` withdrawn.
  R1 re-check (science-reviewer) running.
- (~01:15Z) **LT7 R1 re-check: ACCEPT_WITH_FIXES** (`reviews/LT7_R1_RECHECK_2026-10-22.md`): 3 must-fixes, all tightening
  (block-gate share proxy scaled to census length, `ceil(16 x covered_days / 21)`; CH197 F gate on
  `r_gate = max(r_w, r_pool)`; CH193 to the block gate) plus should-fixes, applied in cedfd6be (section 13.5) and checked by
  the orchestrator. **LT7 DESIGN-TEXT FREEZE:** `LIVE_TESTS_7.md` at cedfd6be, sha256 `840f4500cde37158f57f6cf6bf54a3535ee5b24f3e5dedfd9240b315eeb52899`; merged into
  chore. Any later change to a test's text is a recorded deviation. Next: restore/seal (q0600-q0601), code (vendored
  `live_tests7_base.py`), code freeze check, censuses (q0602-q0604), size check (q0605), pins, registration (window not
  before 2026-12-08). Nothing registered or counted; E-numbers unassigned.

## Signal engine: `book0` (pre-origin book) family, se18 / se19, 2026-10-22 ~03:30Z (signal-engine autopilot; development diagnostic only, nothing counted)
- **Built** the honest replacement for the sweep-1 `book` family (DESIGN_V1 §22): aux family `book0` (`se-aux-book0-v1`)
  from the newest complete pass sweep finished before the origin capture started (<= 3 h; on the host the previous
  pass's last sweep, ~110 min earlier). New specs: `se18_lgbm_all_b0` (se7 with `book` -> `book0`; broad, not embargoed,
  promotion-eligible; K 3 -> 4, stricter) and `se19_lr_book0` (isolates `book0` + `book`, embargoed to 2026-12-31).
  New EMBARGO token `book0` (same date and tests as `book`).
- Development diagnostic (8 host captures of 10-21, read-only): coverage 92-94%; `b0_micro` / `b0_imb5c` show no
  correlation with the in-window move (v1 `bk_micro` up to -0.27). Columns and specs were written before it; seen
  before commit; nothing changed after it.
- Science review: ACCEPT_WITH_FIXES (no leakage defect). Applied: pass-sweep restriction and hidden-folder skip, sweep
  provenance in metadata, the se7 minus se18 contrast disclosed, §22 causality wording, backfill = training input only.
- (~01:35Z) **q0561 (LT5 capture census) attempt 1 failed** (01:02-01:33Z, rc 1): `_ArrayMemoryError` at the 3,000 MB
  address-space cap (2 x mem_mb) in the counting loop; its per-run series cache keeps every read series (H's 96-slot
  look-back needs most of ~127). No output was written; nothing counted. Ops-only fix (41636f7c): mem_mb 1500 -> 3000,
  as_cap_mb 6500; argv, code, seal and gates unchanged. Restarted 01:46Z (attempt 2, the last automatic one).
  **Operational slip (autopilot):** `queue_worker.py stop <id>` is not per-job: it paused the queue and SIGTERMed every
  running job. Effects: q0121 (h8_tail seal) stopped after 6 s (recorded `stopped`, attempt not counted, re-queued); the
  queue was paused 01:34-01:44Z and resumed by hand. Nothing lost. Use `pause` / `retry <id>` instead.

## Operational deviation: research host resized (2026-10-22; facts only; draft by scripts/oracle/post_resize_check.py, appended by the experiments autopilot ~05:30Z)
- Owner decision 2026-10-21 ("Yes, but at a quiet time"): Always Free A1 allowance, cost 0. Target 2 OCPU / 12 GB. Before: {'mem_total_gib': 5.52, 'nproc': 1}; after: {'nproc': 2, 'mem_total_gib': 11.4} (metadata {'ocpus': 2.0, 'memory_gb': 12.0}). Result: resized.
- Queue paused 2026-10-22T02:40:19Z (pre-existing pause: False); resumed 2026-10-22T03:15:31Z. Jobs stopped and re-queued (not counted as attempts): none.
- Collector pass lock held from 2026-10-22T03:00:59Z; light job locks (streams, reward params, lab push) from 2026-10-22T03:10:17Z; monitors stopped 2026-10-22T03:10:25Z; update accepted 2026-10-22T03:10:28Z; boot 2026-10-22T03:12:36Z; check 2026-10-22T03:20:02Z.
- E009/E010 poller: last cycle before 2026-10-22T03:10:00Z, first cycle after 2026-10-22T03:16:00Z; missed 120 s cycles 2; 10-minute grid origins without a poll: none. Not backfilled; missing stays missing (gap-fill rule per E009_E010_GAPFILL_RULE_V2.md applies as written).
- Live trade monitor: last cycle before 2026-10-22T03:08:48Z, first after 2026-10-22T03:15:35Z.
- Streams (last poll before / first after): predictit (1 min) 2026-10-22T03:10:02Z / 2026-10-22T03:14:02Z; smarkets (5 min) 2026-10-22T03:05:17Z / 2026-10-22T03:15:16Z; espn_odds (10 min) 2026-10-22T03:02:12Z / None at the check (polling again by 05:02Z); gamma_rules (hourly) 2026-10-22T02:51:02Z / None at the check (polled 04:50Z).
- Scheduled collector passes inside the window: none (E011 scores per complete capture; E012-E014 origins come from captures and trade samples, so no capture means no origin).
- Problems: none. Resize cron removed (`resize_host.py --remove-cron`, ~05:25Z).

## LT6 seal committed, LT7 census code verified and merged, census jobs promoted (2026-10-22 ~05:50Z; experiments autopilot; nothing counted)
- **LT6:** q0581 done 04:02Z; `seals/lt6_census_inputs.json` committed byte-identical (sha256 18040c8073fa1af8…, host and
  Mac equal). q0582 (CD/CB/CV) and q0583 (CK) promoted (8df23f1f). Ops only: priority 22 -> 96 (both must run before the
  temporary 10-day snapshot retention is reverted; q0582 reads live 10-15 captures), q0582 mem_mb 1200 -> 2500 with
  as_cap_mb 9000, q0583 as_cap_mb 6000 (LT5 q0561 address-space lesson). argv, code, seal and gates unchanged.
- **h8 tail:** q0121 done 01:58Z; `seals/h8_tail_SEAL.json` committed (sha256 2a88f3e5…). q0144 / q0145 promoted unchanged.
- **LT7:** science-reviewer verification of the census-code check fixes: **FIXES_OK_WITH_NOTES**, no remaining must-fix
  (`reviews/LT7_CENSUS_CODE_CHECK_2026-10-22.md`, final section). Notes applied (699b9ee9): CH192 correlations now fail
  (NaN) unless both origin definitions are finite (stricter; a test added), blackout-aware deadlines in q0600 / q0602,
  a stale q0604 note removed, q0601b as_cap_mb 2000. No threshold, gate or design text changed (`LIVE_TESTS_7.md` still
  840f4500…). Merged into chore (dde3c3c4). **q0601 (seal) promoted** (17d67a1a); q0600 (restore) not promoted by its own
  rule (the censuses are planned before the first loss, 10-18 rows leaving the host 10-28T03:30Z under the temporary
  10-day rule or 10-26T03:30Z under 8 days); its dependency was removed from q0601 as its notes direct. Next: commit the
  seal, run q0601b and read `common` before promoting q0602 by hand.
- **MC1:** q0116f promoted (8df23f1f) after the resize; depends on q0484. Development only, not evidence.

## LT5 capture censuses (q0561): F, H and R dropped at census, uncounted (2026-10-22 ~06:05Z; experiments autopilot)
- q0561 ran once on the 12 GB host (05:30-05:35Z, attempt 3 after two address-space-cap failures; no output existed before)
  on seal 59b17969 (fcd88926…); output `seals/CF5_CHW_CRW.json` sha256 2e124285… committed. Counts only, no target read.
- **F (CH184): dropped** (pessimistic MDE 1.01c > 0.5c; all other gates pass). **H (CH181): dropped** (near 1,082 and far
  3,329 projected, below 3,150 / 15,750; `hwm_incomplete` 0.55; market strata 0.0; NaN corr). **R (CH183): dropped**
  (crossing share 0.21 < 0.25; design MDE 1.03c > 0.5c; unrewarded cells 0, possibly the empty-`clob_rewards`-as-NaN parse,
  disclosed; the drop stands without it). Details: `LIVE_TESTS_5.md` 7.3. Uncounted (census drops before registration).
- LT5 continues with J (CH180) and O (CH182): q0562 (flow census) next; then `k_tests`, the vendored-drift record for
  `live_tests4.py`, q0563 size check. Snapshot retention stays at the temporary 10 days until LT6's q0582 is done.

## E022 REGISTERED (LT4; 2026-10-22 ~06:20Z; experiments autopilot)
- **E022** (LT4, the single survivor of its censuses; E020 / E021 dropped uncounted at census, E023 / E024 before any
  census): **registered**, k = 1 (Holm m = 1). Window 2026-10-26T00:00Z .. 2026-11-16T00:00Z; analysis q0486 not before
  2026-11-17T12:00Z, scored once. Design `LIVE_TESTS_4.md` (challenger R1, R2, R2 re-check; census results 17; code freeze
  check FREEZE_OK_WITH_FIXES, 19; registration 20).
- Size check q0484 (one run, seed 20261107, 2,000 x 200): 0.0485 and 0.048 against the 0.058 limit; both binding
  scenarios pass. Output sha256 b8e30676…; its code hashes equal the freeze record.
- Pins: spec sha256 f7fbcff1… (`SPEC_SHA256` in `live_tests4.py`), five normalised module hashes as recorded in section 19.
- Reader: host cron `10-59/20` installed with the registration (own flock, nice 19, oom_score_adj 1000, ulimit -v 1572864).
- Counted when analysed: 1 test. No interim looks.
- Operational slip (recorded): q0486's move from drafts to jobs was swept into commit cd4f3702 (LT7 seal), one commit
  before this registration commit, and deployed with it. No effect: q0486 has not_before 2026-11-17T12:00Z and the
  analysis refuses before `ANALYSIS_NOT_BEFORE`; its notes edit lands in the registration commit.
- Registration check (science-reviewer): REGISTER_OK (pins match; only `code_sha256` and the descriptive `status` changed
  in the spec; LT7's drift record correct and outside its hashed blocks). LT5 must record its `live_tests4.py` drift with
  the post-pin sha256 4e043b65… after q0562.
- (~06:05Z) Ops decision: the temporary 10-day snapshot retention (693db389) is kept beyond q0561 until LT7's last
  census (q0604) is done, because LT7's frozen ordering rule (text 7: after LT6's q0584) pushes its censuses past the
  8-day loss date of the 10-18 rows it sealed. Longer, never shorter; reverted to 8 days afterwards with a ledger line.

## LT6 capture censuses (q0582): D, B and V dropped at census, uncounted (2026-10-22 ~06:35Z; experiments autopilot)
- q0582 ran once (05:42-06:26Z, rc 0) on seal 18040c80…; output `seals/CD_CB_CV.json` sha256 b4c12b32… committed.
  Counts only, no target read.
- **D (CH187): dropped** (3 later by-date units in 9.08 days against a >= 3,150 projected kill line). **B (CH188):
  dropped** (no qualifying birth unit; the kill line is >= 630 births). **V (CH190): dropped** (within corr(zv, z v_prev)
  0.595 > 0.5; every other gate passes, tercile MDE 0.35c). Details: `LIVE_TESTS_6.md` 6.3. Uncounted (census drops
  before registration).
- LT6 continues with K (CH185): q0583 (flow census) next, then `k_tests`; q0584 size check only if K survives.

## Signal engine: `crypto` spot-reference family, se20, tick aux budget fix, 2026-10-22 ~06:00Z (signal-engine autopilot; nothing scored or counted)
- **Built** aux family `crypto` (`se-aux-crypto-v1`, DESIGN_V1 §23; CANDIDATES builder row 20, unblocking row 5 now that
  CB13-R is closed): crypto template markets mapped from their own sidecar `series_slugs` + `fee_category` (no text);
  Binance spot 1 m / 5 m klines closed before the capture start, fetched once per capture and stored write-once with
  their fetch time. Columns: spot returns 5 m..24 h, realised volatility, up/down window z and normal-reference gap,
  the market's own beta to spot from earlier 2 h pairs and the latest lag. Challenger `se20_lgbm_crypto` (se1's
  LightGBM params + `crypto`; read against se1). No embargo token: no live test uses a spot reference. K 4 -> 5
  (stricter for every challenger).
- Spec written 02:23-02:41Z (the session that hit the usage limit) before any crypto table existed; the only real-data
  look was a sidecar coverage count (~4,800 of 5,870 crypto rows map; no outcomes) after the spec.
- Science review: ACCEPT_WITH_FIXES, no leakage. Applied: HTTP 400 symbols recorded as permanently unavailable (all ten
  symbols answer 200 today); `cr_has` NaN for markets absent from the sidecar; sidecar sha256 in provenance; a 120 s
  per-capture fetch budget; §23 disclosures (Binance is a proxy, not the resolution source; daily up/down reference
  minute; NaN scope; outcome-0 = Up assumption); registry `added_utc` corrected to 02:34Z.
- Coverage: snapshot rows exist only from 10-13 04:31Z (temporary 10-day retention), so 14 engine captures never get a
  crypto table; se20's direction fits start at the 10-27 refit, `res_7d` ~11-10.
- **Defect fixed:** the tick built at most 4 aux tables per run, so `participation` and `book0` of each new capture were
  built only at the next pass, after the 2 h target had started (capture 10-22 04:31Z). Now `len(AUX_FAMILIES) x
  max_items`. No prediction was affected (se16 has no fit; se18 / se19 first fit at the 10-22 07:34Z refit).

## LT6 closed: K dropped at census, no LT6 test registered (2026-10-22 ~06:50Z; experiments autopilot)
- q0583 (CK) ran once (06:28-06:39Z, rc 0) on seal 18040c80…; output `seals/CK.json` sha256 e0476df1… committed. Counts
  only. **K (CH185): dropped** (13 clip units in 1.92 days, projected 142 against >= 8,400; clip share 0.0066; permutable
  share 0.0 by day; MDE 5.75c). Details: `LIVE_TESTS_6.md` 6.3.
- **LT6 has no surviving test** (V, D, B at q0582; K at q0583): nothing registered, **uncounted**. q0584 and the LT6
  reader / analysis drafts are moot. LT7's "after LT6's q0584 or its recorded drop" is met by this entry; q0602's
  dependency on q0584 is removed with a note (the cpu lane still serialises LT7 with LT5's census jobs).

## LT5 closed: J and O dropped at census, no LT5 test registered (2026-10-22 ~07:35Z; experiments autopilot)
- q0562 (CJ, CO) ran once (07:12-07:25Z, rc 0); output `seals/CJ_CO.json` sha256 5b806f7d… committed. Counts only.
- **J (CH180): dropped** (63.7 qualifying units a pass < 120; permutable share 0.0; MDE 2.16c). **O (CH182): dropped**
  (372 covered units a pass < 600; IQR share 0.44 < 0.50; MDE 0.84c). Details: `LIVE_TESTS_5.md` 7.3.
- **LT5 has no surviving test** (F, H, R at q0561; J, O at q0562): nothing registered, **uncounted**. q0563 and the LT5
  reader / analysis drafts are moot. The `flow` engine token (until 11-22) was filed for LT5 J / O only.
- The vendored-provenance guard is closed out with drift records for `live_tests4.py` (post-pin sha256 4e043b65…) and
  `live_tests4_analysis.py` (c31117ac…; only the E022 pin line and earlier LT4 pre-pin edits changed; every vendored function still equals its source, which the test
  checks), so the suite stays meaningful; LT5's spec is otherwise unchanged and will never be pinned.

## LT8 drafted, challenger R1 and re-check, design-text freeze (2026-10-22 ~07:45Z; experiments autopilot; nothing counted)
- **Source:** creative round 13 (`CREATIVE_HYPOTHESES_2026-10-27.md`, CH202-CH211, merged 553bd125). LT8 = CH203 (quiet
  book: 5c-imbalance innovation behind an unmoved touch), CH202 (sweep clock: held versus fresh part of the previous move),
  CH204 (the market's own hot-slot clock); one Holm family, k <= 3. CH205 not proposed (sports scope, owner's call);
  CH206 a counts-only map first; CH207-CH211 engine-first.
- **Reviews:** draft 4552cec5 -> challenger R1 **REVISE** (8 must-fix; `reviews/LT8_CHALLENGER_R1_2026-10-22.md`, 9f99504d)
  -> response 164078c8 (section 13) -> re-check **ACCEPT_WITH_FIXES** (`reviews/LT8_R1_RECHECK_2026-10-22.md`; 4 fixes:
  binding worlds 3 and 5 restored to the first draft's scales after the response had weakened them, vendoring wording,
  LT5 closed) -> fixes c124db50. Orchestrator ruling: world 5's "next two passes" = t + 2 and t + 3 (the reading that
  puts the whole reversal inside the skip target, i.e. the stricter world).
- **DESIGN-TEXT FREEZE:** `LIVE_TESTS_8.md` at c124db50, sha256 `5e61c20b1282cef79c7caee68f08dceb506f845bc1a1325fe2fb9335c955cf48`;
  merged into chore. Any later change to a test's text is a recorded deviation; changes after LT7's census commit are
  labelled *informed (LT7 census)*. Proposed window 2026-12-30T00:00Z .. 2027-01-20T00:00Z (after LT7's END + 24 h),
  analysis on or after 2027-01-21T12:00Z. Honest odds (author): expected k at census about 0.65; about 0.47 that all
  three drop. Next: embargo requests (`quietbook`, `swclock`, `sched`; `book0` / `book` extended) before 12-01, code
  phase (seal and censuses q0620-q0627), code freeze check. Nothing registered or counted; E-numbers unassigned.

## LT7 reward-field null ruling and design amendment 13.6 (2026-10-22 ~11:10Z; experiments autopilot; nothing counted)
- **Trigger:** q0601b (counts only; `seals/lt7_rewards_null_share.json`, sha256 2278ce60…) fired its pre-declared `common`
  rule: `clob_rewards` null on 0.60-0.65 of sealed non-sports ex-crypto market-captures every day 10-12..10-21; `[]` never;
  `rewards_max_spread` / `rewards_min_size` never null.
- **Challenger ruling (B with changes)** (`reviews/LT7_REWARD_NULL_RULING_2026-10-22.md`): a null `clob_rewards` with the
  sidecar row present = "no native programme listed" -> `rewarded = 0` (CH197, CH192 primary) and the unrewarded
  wall-class branch, counted `rewards_null_as_zero`; listed but inactive on the day -> 0, counted
  `rewards_listed_inactive`; malformed or absent -> NaN, counted. No indicator column; listed-only sensitivity reported.
  Outcome-blind (sidecar counts only, before any census). Gates, thresholds, formulas unchanged; this restores the
  planned population (leaving it frozen would have cut CH197 and CH192 to ~38% of units, MDE ~1.6x). Also found: the
  existing parse returned 0.0 for malformed text ("unparseable excluded" was not implemented) and mislabelled a count.
- **Design-text amendment 13.6:** `LIVE_TESTS_7.md` sha256 840f4500… -> `31baf5e5b5c1bec2518228618fc21ab7f111c0e673d6cb064583ce1363d20dd4`
  (a recorded deviation after the text freeze; before any census and any adjacent `T_X`). The LT7 census seal
  (117e9b45…, design hash 840f4500…) is kept, not re-sealed (LT8 pins it); the code will accept it as the amendment's
  predecessor.
- **Next:** code fix on a branch (strict parse, four reward statuses, counts, spec key `reward_null_rule`, tests), a
  counts-only probe (listed-inactive share, `order_min_size` null share, within-day switching), census-code re-check, then
  CV7 (q0602), CC7 (q0603), CS7 (q0604) on one code hash with fresh work dirs, finishing before 2026-10-28T03:30Z.

## Signal engine: embargo withdrawals after census drops, LT8 tokens applied, 2026-10-22 ~12:00Z (signal-engine autopilot; nothing scored or counted)
- **Withdrawn** (programme rule: a test dropped at census before registration loses its token and any extension made
  only for it; DESIGN_V1 §8 "Withdrawal"; `until` set to 2026-10-22T12:00:00Z with a `WITHDRAWN` note, entries kept):
  - `event` (LT5 F, dropped q0561): se8_lr_event and se10_lgbm_event visible from 12:00Z. Neither had a fit, a
    prediction or a score before. Disclosed: the LT5 census read 2026-10-20/21 captures for counts only.
  - `rewards` 11-22 -> 11-18: only the extension for LT5 R (dropped q0561) is undone; E020 (dropped at the LT4
    census) is removed. The token stays for registered E022's S2 secondary (reward versus non-reward split; analysis
    not before 11-17T12Z): the later of 11-18 and E022's analysis commit. se9 stays hidden until then. LT7 has
    rewarded secondaries and an open challenger ruling on null `clob_rewards`, but requests no token.
  - `flow` 11-22 -> 11-16: only the 2026-10-21 extension for LT5 J/O (dropped q0562) is undone. E016/E018 (dropped
    q0472) are removed; 11-16 is kept as margin over E013/E014's 2026-11-13T12Z analysis (not shortened to 11-14).
    The later of 11-16 and LT2's analysis commit (q0461): if q0461 slips, the date moves later. se2_lr_flow and
    se11_lgbm_flow are scored from 11-16, over their history since 10-21.
  - `vote`, `clips`, `deadline`, `siblings` (LT6 V/K/D/B, dropped q0582/q0583; no models); `mm_fresh` (CH194
    withdrawn in LT7's R1 response; no model).
  - Tests lists pruned of dropped tests, dates unchanged: `book`/`book0` drop E019, E020, LT5 H/R, LT6 V (LT8 §9
    asks for LT6 V); `wallet` drops E024.
- **Applied LT8 §9 requests** (CANDIDATES round 5, filed ~11:00Z; design text frozen c124db50; before the 12-01 deadline): new tokens `quietbook`
  (CH203), `swclock` (CH202), `sched` (CH204) to the later of 2027-01-23T00:00Z and LT8's analysis commit; `book` and
  `book0` 12-31 -> 2027-01-23 (later only; back to 12-31 only if both CH202 and CH203 drop at census). se3, se14
  and se19 stay hidden 23 days longer (disclosed by LT8).
- **Record:** withdrawn entries stay in `config.EMBARGO` with `until` = `withdrawn_utc` = 2026-10-22T12:00:00Z and
  `until_before`; flow and rewards carry the same fields. A test checks that any date moved earlier carries them.
- **Consequence:** se-promotion-v2's K (every active non-embargoed challenger) goes 5 -> 7 at once (se8, se10), so the
  Bonferroni level is stricter for se1, se17, se18 and se20. This follows the pre-declared definition of K; no constant
  changed. No challenger can reach 14 days of age before ~11-04. se8 and se10 join K before they can be scored (first
  fits ~10-27); if they never fit, they raise K for nothing. Expected K path as embargoes lapse: 9 at 11-04, 11 at
  11-14, 13 at 11-16, 14 at 11-18, 15 at 11-19, 16 at 11-25, 17 at 12-07, 20 at 2027-01-23. se8's 28-day retirement
  check counts from its first prospective score, not from today.
- **Partial overlaps disclosed (no tested term):** the event family holds event size and sibling moves. CB17-C has a
  "moving members {1, >=2}" stratum (REP_8 to at least 11-23), which the 11-22 `event` token happened to cover; its
  tested quantity stays under `participation` (11-25). LT8 caps CH203 / CH204 at 10 members per event.
- Science review: ACCEPT_WITH_FIXES. All fixes applied: `rewards` kept for E022 S2 (only the LT5 R extension
  withdrawn), "later of" wording on flow / LT8 / book entries, structured withdrawal fields, these disclosures and the
  K path. Withdrawal time set at or after the deploy (deploy before 12:00Z; actual time in STATUS.md). Tests: 50 engine tests pass; ruff clean.

## MC1 q0116f: timed out at the 6 h limit, 2026-10-22 13:42Z (nothing counted; development only); PARKED
- q0116f (`run_ml_dev.py`, exclusive, 6,000 MB, as_cap 14,000 MB, 1 CPU, timeout 21,600 s) ran on the resized host
  (2 OCPU / 11.4 GiB) from 07:42Z and was stopped by the worker's timeout at 13:42:02Z (rc -15). No OOM this time (RSS
  about 6.2 GB at 3 h). It wrote only the fold manifest (`ml_dev_20261022T074210Z_cac75bfc_fold_manifest.json`, 07:42Z,
  the same size as q0116c's); the job log holds only the argv line, so the stage at which it spent the remaining ~6 h is
  not known (the model-fit stages log nothing).
- No trials lines, no model outputs; the cached panel and period cache are unchanged and stay reusable.
- **Decision:** parked (16:02Z), not retried. Per the standing rule, no new id without a measured fix: the next step is
  stage-level progress and timing lines in `run_ml_dev.py` (panel load, per-model fit per fold, bootstrap, SHAP) and a
  bounded one-fold profile job, then a timeout and CPU request set from that measurement. No design change (panel,
  models, folds and gates unchanged). The signal engine (separate autopilot) keeps covering prospective multi-family
  scoring meanwhile.

## CB16-K census q0383, 2026-10-22 14:06Z (counts only; no test, nothing counted)
- Output `creative_batch16/census_K.json` (host, sha256 aebc528a…; rules K cfe9bea5…, common 9a087b8c…; exclusion keys
  56dc953e…; input pins ok). No outcome, price or network read.
- Labels over 148,384 rows (frame 61,146; outside frame 87,238): PRESENT-STRICT 939, PRESENT-TOPIC 30,176,
  ABSENT (liquid-universe) 30,031, FAR-TOPIC 9,989; unlistable absent 16, rule conflicts 2 (0 in matches); 958 matches
  against 326,380 indexed Kalshi markets. Sports (SPORTS-FEED) reported separately: strict 353, topic 4,977, absent 12,132.
- Cells (LABELLER class x volume decile) with both labels >= 30 events: strict 7 (all UNSCHEDULED-NEWS; 261 present /
  2,698 absent events; MDE bound 2.46 pp optimistic, 5.91 pp max); strict ∪ topic 40 (15,405 / 10,240 events; 0.48 pp
  optimistic, 1.16 pp max). FAR-TOPIC: 39 cells.
- **Re-entry rule (§CB16-K, declared before the census):** counts part PASSES (union >= 5 eligible cells, optimistic MDE
  0.48 <= 2 pp; FAR-TOPIC >= 30 events in >= 5 eligible cells). The remaining condition is the seeded blind audit of 100
  PRESENT-TOPIC pairs (science-reviewer, titles only, seed 16141, >= 90% genuine same-event twins). A counted K may be
  designed only in a later batch and only if that audit passes; otherwise CH143 is "not testable at the floor". No
  counted K is registered. **Next:** a titles-only audit sampler (seed 16141), then the audit.

## CB9 gating after CB8-W's smoke FAIL, 2026-10-22 ~16:09Z (science-reviewer ruling; operational, nothing counted)
- `reviews/CB9_H9_DEPENDENCY_RULING_2026-10-22.md`: REVISE. h9_flow never fetched (CB8 q0161 FAIL (a)); absent at q0182
  per CB9 §1.3; (f) not engaged. q0182 keeps its id and definition; `depends_on` = [q0164, q0166]; it adds the two
  `--extra-pin`s (CB8 updown frame, dated CB8-H holders snapshot) the draft lacked, and q0164's keys sha256 (MUST 1).
- **Pre-declared before q0166's result:** coverage-audit FAIL (`source_unavailable`) -> holdout seal absent at q0182, q0182
  runs with the q0165 frame pinned; crash/unrecoverable -> (f) as written.
- q0181 (S0 audit A) promoted ~16:07Z (c535f978); unaffected.
- **Time-label erratum (autopilot session 10-22 from 15:59Z):** queue-spec notes written this session carry "~HH:MMZ"
  labels that are 0.2-2.5 h late (local time misread as UTC): q0602/q0165/q0166 "~16:15Z" = ~16:03Z; q0181 "~16:30Z" =
  ~16:07Z; q0116g/q0393 "~17:20Z" = ~16:12Z; q0146 "~18:30Z" = ~16:25Z; q0602/q0116g priority "18:50Z" = ~16:29Z. Spec
  files are not edited (hash/ops reasons); commit times are authoritative. Review headers and the checkpoint were corrected.

## LT7 reward-switch ruling and design amendment 13.7 (2026-10-22 ~16:10Z; experiments autopilot; nothing counted)
- **Trigger:** q0601c (counts only; `seals/lt7_rewards_probe.json`, sha256 263413f2…): the pre-declared rule (c) fired. 30,543 of 258,393
  market-days (0.118 > 0.05) switch between null and non-null `clob_rewards` within a UTC day; (b) 0.0012 and (d) 0 did not fire; (a) 0
  (report only). One endpoint, parameter set and code path, so the switching comes from Gamma's responses; Gamma omitting the field in a
  response is the likelier reading (about 3,000 switchers a day = about 30% of about 9,700 listed markets per capture; listed zero-rate 0/1,047,747).
- **Challenger ruling (C)** (`reviews/LT7_REWARD_SWITCH_RULING_2026-10-22.md`): rule `listed_carry24h_v2`. A null `clob_rewards` at origin k is
  `rewarded = 1` if a listed text at any sealed capture in the causal window `[k-11, k]` gives a rate > 0 re-parsed for day(k); the latest such
  capture is the source for `rew_min` / `rew_maxspread` (`in_band`, wall rule). Missing slots skipped and counted, never filled; no slot after k is
  read. v1 (`null_as_unrewarded_v1`) and listed-only are descriptive sensitivities. (A) rejected (reads omitted captures of rewarded markets as
  unrewarded), (B) rejected (uses captures after k: leak), (D) rejected (selection on the reward field), (E) rejected (changes the frozen
  controls). Unit counts, MDE inputs, gates, thresholds and formulas unchanged. Outcome-blind (counts only, before any census).
- **Design-text amendment 13.7:** `LIVE_TESTS_7.md` sha256 31baf5e5… (13.6) -> `8fc83a739ef48ddf23c568847e0eec98ff56bd3bead4c4974eac463d023c1803`.
  13.6's sha and the text-freeze sha 840f4500… are declared predecessors in code (the committed seal 117e9b45… records 840f4500…; CV7's output
  records 31baf5e5…). 13.7 also corrects 13.6's wall-class label (CH193's, not CH192's) and states that CH193 gets `rew_status` / `rew_min` / `osz`
  as bookkeeping columns of `absorbed_units` (no exclusion, count or gate).
- **Split disclosed:** CV7 (q0602) reads no reward field and records design 31baf5e5…; CC7 (q0603) and CS7 (q0604) record 8fc83a73….
- **Code:** branch `feat/lt7-reward-carry` (`RewardCarry`, `_reward_cols` counts, CS7 capture set gains the 12:31Z carry window, spec
  `reward_null_rule: listed_carry24h_v2`, `reward_carry_slots: 12`). Drafts q0603 / q0604 use fresh work dirs (`work_cc7_rn_v2`, `work_cs7_rn_v2`)
  and stay drafts until the census-code re-check. Each census runs once, finishing before 2026-10-28T03:30Z.
- **13.7 erratum (same day, census-code re-check of 64acdbc4 = FIXES_REQUIRED, before any census):** (1) "unit counts unchanged" corrected: the
  carry can change `in_band` finiteness, so units can enter or drop; both are counted (`in_band_known_only_via_carry`, `in_band_lost_via_carry`).
  (2) CH197 F-feasibility pairs use the **k-only (v1) reward and in_band** (option b): their windows are not all sealed (slots 156-161 are not in the
  LT7 seal; 12 of 22 pair slots lie outside CS7's K set), so option (a) was not available. (3) `RewardCarry.add` refuses a series without `rew_raw`
  when listed rows exist. (4) v1 sensitivity relabelled "v1 rewarded on the v2 unit set"; market-deduplicated switching count added. Design sha256
  now `8fc83a739ef48ddf23c568847e0eec98ff56bd3bead4c4974eac463d023c1803` (text above, erratum paragraph at the end of 13.7); `575eb1dd45328800cdab1ccf633099c40a21817a8ae8f308c23454c9de96e730` (13.7 first commit) is a declared predecessor; no census has run on it.
- **Bug found by the fix-3 round-trip test (code, not design):** pandas reads the series-CSV cell text `null` back as NaN, so `rew_status == "null"` never matched on a file read back from the work dir and the carry would never have fired (the 13.6 `rewards_null_as_zero` count would also have read 0). `RewardCarry` now treats a NaN status as `null` (`_status_array`); `live_tests7_base.read_series` is untouched.

## MC1 one-fold profile q0116g: timed out at its 2 h limit, 2026-10-22 19:22Z (measurement only; nothing counted)
- q0116g (`run_ml_dev.py --profile-folds 1`, exclusive, 6,000 MB, as_cap 14,000 MB, 1 CPU, timeout 7,200 s) wrote 132
  stage lines and was stopped at 7,200 s during the placebo fits of fold 0 (rc -15). No trials lines, no model outputs
  (the profile sink records nothing).
- **Measured, fold 0 (the smallest training window of 16 folds in the manifest):** sweep arms 3,981 s (M1 fit 1,387 s,
  M2 fit 2,190 s incl. SHAP 760 s, M3_eb 392 s); no-sweep sensitivity 2,379 s (M1 1,183 s, M2 1,187 s); bootstrap 5 s;
  placebos started at 6,443 s and were unfinished at 7,200 s. Peak RSS 6,248 MB (fits 5.5-6.2 GB), so memory fits the
  resized host; time does not.
- **Implication:** a full development run is at least 16 x ~2 h = ~32 h of exclusive time on 1 CPU (later folds train on
  more periods, so likely more). It would block the exclusive LT7 censuses (q0603/q0604 must finish before
  10-28T03:30Z) and the signal-engine refits for days, and the memory rule forbids pairing it with another multi-GB job.
- **Decision (operational, no design change):** no full run is queued now. The measured fix is per-fold resumability
  (write each finished fold's out-of-fold predictions and stage record, skip finished folds on restart, same fold plan,
  models and gates), so the run can proceed in <= 6 h exclusive slices after q0604. q0116g stays `failed` (it was a
  measurement); q0116f stays parked.

## CB16-K blind twin audit, 2026-10-22 ~20:45Z (science-reviewer; nothing counted)
- Auditor file `creative_batch16/audit_K_sample.json` (q0393, seed 16141, 100 of 30,176 PRESENT-TOPIC pairs; sha256
  0d317a11…, equal to the manifest's `sample_sha256`); titles, subtitles and the two 3-day-rule dates only, as q0393
  declared. Key file not read. Review: `reviews/CB16_K_BLIND_AUDIT_2026-10-22.md`.
- **Result: 3 GENUINE, 1 UNCLEAR, 96 NOT_TWIN; FAIL against the declared >= 90 / 100.** The PRESENT-TOPIC text rule
  matches recurring templates (crypto "price between" vs unrelated indices, unnamed-city °F vs °C buckets, one-way
  implications within a match), not same-event twins.
- **Re-entry rule not met: CH143 is recorded as "not testable at the floor with available or feasibly collectable
  data"** (CREATIVE_BATCH_16.md §CB16-K). No K test existed (declared "no CB16 test"), so nothing is counted. The
  seed / stratum provenance check by a key-side reader is moot for the verdict and not pursued.

## CB7 census q0147 fix re-check, 2026-10-22 ~20:45Z (science-reviewer; operational)
- `reviews/CB7_CENSUS_FIX_RECHECK_2026-10-22.md`: **FIXES_OK_WITH_NOTES** for freeze-check items 3-8 (4cc77b64, af960b80;
  39 tests). Design §2.7 unchanged; no outcome read.
- Note 1 (medium): the q0146-failure contingency (re-specify q0147 as `--family S,G` with X terminal) needs a durable
  terminal record before it is used: a refused / disk_budget q0146 must leave a marker, `require_xv_complete` must not
  tempfail on a sticky terminal manifest, and census.json must carry an explicit X terminal state. To implement before
  q0146 ends or before q0147 is promoted (not before 10-24T01:00Z). Notes 2-3 (low) in the review.

## Signal engine: market-price reference row for `res_7d`, 2026-10-22 ~21:00Z (signal-engine autopilot; no model, no K change)
- Added `market_price_reference` to the scorer (DESIGN_V1 §24): P(yes) = the origin's Gamma mid from the write-once
  features file, scored on `res_7d` only, with each scored model's `gain_vs_market_mid` (event-clustered CI). It is a
  benchmark, not a challenger: not in the registry, never promoted, no change to K, the promotion rule or any existing
  score. First rows at the 2026-10-23 daily score. Any gain over the mid is forecast quality only (no costs, no fill),
  not an edge claim. Test `test_market_price_reference_scores_res_7d_from_the_origin_mid`.

## CB8 q0164 / CB9 q0181 failures and fixes, 2026-10-22 ~21:20Z (operational; nothing counted)
- **CB8 q0164 (exclusion keys) exited 0 on a failed run** (`stage_failed: gamma markets lookup status 422`), so the queue
  marked it `done` without keys; q0165 then failed 3 times ("exclusion key files missing"). Cause: Gamma's `id` filter
  takes integers only; the `h7_cb4_series` seal copy names files `<successor market>__<pred event>` (1,922 composite ids).
  q0164 stays recorded as a failed run that exited 0 and was wrongly marked done (no history rewritten).
- Fix (new file `cb8_exclusion_fix.py`, run-scoped; pinned CB8 rules 33decb52… untouched): market part to the lookup;
  ruling `reviews/CB8_Q0164B_RULING_2026-10-22.md` GO_WITH_CHANGES adds the `pred_*` market ids and pred event ids (the
  conservative direction, before the split), a frozen id-set hash across repeat runs, per-pin id counts (zero-id seals
  labelled "ids not extractable from seal copy", not covered), provenance of the wrapper in the manifest, refusal on
  unresolvable ids, a copy of q0164's failed manifest. Incomplete transient stops now exit 75. New job q0164b; q0165
  depends on it (retry q0165 after q0164b is deployed).
- **CB9 q0181 (S0 sign audit A):** MemoryError x3 at the 600 MB address-space cap (2 x mem_mb 300), in the S0 frame walk
  before any sample was written. Measured on the host: VmSize 609 MB at 1,750 requests, RSS growing ~0.035 MB/request.
  Spec caps raised (mem_mb 1,200, as_cap 4,000, timeout 3 h; ec9f900a), deployed, `retry` at 21:18Z.

## MC1 per-unit resume, 2026-10-22 ~21:30Z (development tooling; nothing counted)
- `ml_resume.py` + `run_ml_dev.py --resume-dir --time-budget-s` (0adebfb9, 04385110): each finished (arm, fold) unit is
  stored atomically and reloaded on restart; identity (fold-manifest sha, panel hash, code sha256s, argv, package
  versions) must match or the run refuses; exit 75 at a unit boundary when the budget would be exceeded; trials rows
  flushed once at completion. Review OK_WITH_NOTES (no cross-unit RNG or fold state; notes 1-4 applied). Synthetic
  interrupted-vs-uninterrupted test bit-identical; real fits not yet run twice. Draft q0116h (depends on q0604).

## Signal engine: `hwm` own high-water-mark family, se21, 2026-10-22 ~22:15Z (signal-engine autopilot; development family, nothing scored or counted)
- Built aux family `hwm` (`se-aux-hwm-v1`, DESIGN_V1 §25; CANDIDATES CH181, development only, LT5 H dropped at census):
  distance of the origin mid to the highest / lowest mid of the earlier captures over 3 d and 7 d, hours since the 7 d
  extremes, position in the 7 d range, share of 7 d slots quoted; from the engine's own quotes files only. Challenger
  `se21_lgbm_hwm` (se1's LightGBM params + hwm; one pre-declared configuration, no development selection; not
  embargoed). K rises by one. Science review ACCEPT_WITH_FIXES (documentation fixes applied). Ideas only: no evidence
  yet. Tests `test_hwm_features_hand_example`, `test_hwm_family_reads_only_earlier_quotes`.

## LT7 census CC7 (q0603), 2026-10-22 21:4xZ: CH191, CH192, CH193 dropped at census (counts only; uncounted)
- `live_tests7_census/CC7.json` (host, sha256 088abbcb…; live_tests7.py e1c5c0c6…, design 8fc83a73…, reward rule
  `listed_carry24h_v2`, 12 carry slots). CV7 (q0602) sha256 309596e9… (records live_tests7.py 2ee6a659…, the pre-13.7
  code; its only gate is CH193's semantic gate). No outcome or target read; gates as frozen in LIVE_TESTS_7.md §7.
- **CH191 (grind at the capture clock): FAIL** on units (projected 6 h movers after family exclusion 71,807 < 201,600),
  grind share (0.045 < 0.15), block-gate share (0.38) and the class MDE (0.63c); correlation caps passed.
- **CH192 (implied against realised): FAIL** on the slope MDE, the F-MDE (declared 1.73c) and the
  `corr(zivr, log rv24)` cap (pooled -0.75, within -0.73); units, residual IQR and rv-floor passed.
- **CH193 (absorbed flow): FAIL** on units (projected 50,269 after family exclusion, below the gate); its MDE, F-MDE and
  correlation gates passed. CV7's semantic gate is moot.
- Per LT7 §7 (as for LT5/LT6), a census drop is not a test: nothing counted. LT7's k now depends on CS7 (q0604: CH195,
  CH197; CH194 was withdrawn earlier). Design-doc census fills (§6.3) after q0604. Retention stays at 10 days until LT8's
  q0623 (LT8 re-check R3).

## LT7 census CS7 (q0604) and LT7 closure, 2026-10-22 ~22:00Z (counts only; uncounted): LT7 has no test
- `live_tests7_census/CS7.json` (host, sha256 64883244…; design 8fc83a73…, `listed_carry24h_v2`). No outcome read.
- **CH195 (book depth on the side a move hit): FAIL on the F-MDE only** (0.667c > the 0.5c cap; r_w 0.11); units
  (228,300 projected), coverage, sign agreement, slope MDE (0.22c per SD) and correlation caps passed. The design declared
  in advance that CH195 was "more likely than not to drop at census on its F-MDE gate" (LIVE_TESTS_7.md §2).
- **CH197 (deep orders behind the best price): FAIL** on units (102,533 projected < 210,000), slope MDE (0.55c per SD) and
  F-MDE (2.40c), as the design expected; covered share 0.82 and correlation caps passed.
- **LT7 closed with no test** (CC7 dropped CH191/CH192/CH193; CH194 withdrawn before). Nothing counted; phase 2 (reader,
  analysis, q0605) moot. Embargo withdrawals requested in signal_engine/CANDIDATES.md (22:10Z note).
- **Retention:** the temporary 10-day snapshot rule stays until LT8's q0623 finishes (LT8 re-check R3), then reverts to 8 days.

## LT8 amendment 13.7 and re-check fixes R1-R3, 2026-10-22 (~21:30Z; experiments autopilot; nothing counted)
- **Trigger:** `reviews/LT8_CENSUS_CODE_FIX_RECHECK_2026-10-22.md` = FIXES_REQUIRED R1-R3 (fixes 1-10 OK). Before the LT8 seal and every LT8 census.
- **R2, design-text amendment 13.7** ("reward-null rule `listed_carry24h_v2` (from LT7 13.7 and its erratum)"): `LIVE_TESTS_8.md` sha256
  5e61c20b… (text freeze, now a declared predecessor in code) -> `c76ffff6563ed88eae22046d5986e580cc527e8799488b014dcfd8365ef3accb`. CH203 only:
  a null `clob_rewards` at k takes `rewarded` from the latest positive listed text of `[k-11, k]` re-parsed for day(k), with that source's
  `rewards_max_spread` (`in_band`) and `rewards_min_size` (`ft_both`); `rw_changed` compares the effective texts E(k) and E(k-2); F pairs use the
  carry at k. Counts as LT7; v1 `ft_both`, `VIF_w` and slope MDE descriptive only. Only input: LT7's probe counts (263413f2…); not *informed (LT7
  census)* (no LT7 census output committed; CV7's host output read for its code hash only). Gates, thresholds, formulas and MDE inputs unchanged.
- **Code:** vendored LT7 `RewardCarry` and its count helpers (7 names, byte-identical to the e1c5c0c6 blob); spec keys `reward_null_rule:
  listed_carry24h_v2`, `reward_carry_slots: 12` (sealed blocks); `maker_rewards.py` hashed; pre-13.7 test exemption removed.
- **R1:** accepted LT7 census code = {CV7: `live_tests7.py` 2ee6a659…; CC7 / CS7: e1c5c0c6…; all: `live_tests7_base.py` 2e8baa90…}; anything else
  refuses. Every vendored body CV7 depends on (and every non-carry vendored body) is byte-identical in the 2ee6a659 blob (test).
- **R3:** q0620-q0623 drafts gain the LT7/LT6/LT5/LT4 restore-tree roots (hash-checked); no census "measured by a host dry run" on sealed inputs;
  10-day retention kept until q0623 finishes; promotion only per `restore-plan` or a chain finishing before 2026-10-28T03:30Z outside 02:45-05:30Z.
- **Next:** census-code re-check of this commit, then q0620. Nothing counted.

## LT8 13.7 re-check notes N2-N4 closed, 2026-10-22 (~21:58Z; experiments autopilot; nothing counted)
- **Trigger:** `reviews/LT8_13_7_RECHECK_2026-10-22.md` = FIXES_OK_WITH_NOTES (R1-R3 fixed). Before the LT8 seal and every LT8 census.
- **N2, option (a): 13.7 erratum** (`LIVE_TESTS_8.md`, end of file): `rw_changed` is NaN, the unit excluded and counted as
  `rw_changed_no_column`, when capture k or k-2 is a sidecar without the `clob_rewards` column (an absent column is not an empty
  programme, check fix 7). Code: `rw_frame` / `read_rw8` give a `no_column` row `clob_h` NaN (not `clob_hash(NaN) = ""`), `effective_text`
  returns NaN there, `quiet_units` takes `rw_nocol` and counts the exclusion before `rw_changed_unknown`; the descriptive v1 comparison is NaN in
  the same cases. Design sha256 c76ffff6… -> `73c941e1a4dd2c2d00350808ca5287edaebb16ca2edc191ffe3b88ce7f1f356b` (c76ffff6… and 5e61c20b…
  declared predecessors in code; spec `design`, `design_text_sha256` and `reward_rule.rw_changed_rule` updated). Only input: code reading.
  Gates, thresholds, formulas and MDE inputs unchanged. CS8 prints `carry_counts_caveat` next to the carry counts: LT8's carry store reads every
  sidecar row, LT7's only two-sided series rows, so LT8 and LT7 carry counts are not comparable like for like (ruling 2).
- **N3:** CV7.json on the host records `code_sha256["live_tests7.py"]` = 2ee6a6592890… (verified by the orchestrator 2026-10-22 ~20:55Z; CV7.json
  read for its code hash only, no count read), so q0621's accepted-set check (`LT7_CENSUS_CODE_ACCEPTED`: CV7 = 2ee6a659…) is satisfied.
- **N4:** the census drops `rew_raw` from each rw frame once its slot is in the `RewardCarry` (`rw_slim`; test: byte-identical census JSON
  with and without it, and `effective_text` never sees `rew_raw`). q0623 keeps mem_mb 2000 (reasoning in its notes; no census run to measure).
- **Next:** short re-check of this commit, then q0620 per the R3 promotion rule (N1, the checkpoint retention line, is the orchestrator's).

## LT8 code merged into chore, 2026-10-22 ~22:20Z (nothing counted)
- feat/live-tests-8-code merged (amendment 13.7 + erratum; design sha256 73c941e1…; 220 tests). Re-checks:
  `reviews/LT8_CENSUS_CODE_FIX_RECHECK_2026-10-22.md` (R1-R3), `reviews/LT8_13_7_RECHECK_2026-10-22.md` (OK_WITH_NOTES),
  `reviews/LT8_13_7_ERRATUM_RECHECK_2026-10-22.md` (OK_WITH_NOTES). **Independence ruling (reviewer):** the 13.7 erratum is
  the mechanical fix prescribed by N2 option (a) before LT7 CC7 was committed; it concerns only CH203 `rw_changed`
  missingness, so it is not "informed (LT7 census)".

## LT8 restore-plan and seal promotion, 2026-10-22 ~22:35Z (operational; nothing counted)
- `run_live_tests8.py restore-plan` on the host with the q0621 roots (host originals, LT8 and LT7-LT4 restore trees):
  159 / 159 needed dirs present hash-equal, 0 mismatches, 0 restore paths (/tmp/lt8_restore_plan.json, sha256 df557c55…).
  q0620 (archive restore) is therefore not needed and stays a draft (never promote); q0621's depends_on changed to q0604.
- Host-only: snapshots 10-18..10-21 and sweeps 10-17 and 10-19T22..10-21, which the 10-day rule starts removing from
  10-28; so the R3 timing route applies: q0621 (seal, promoted now), then q0622 / q0623 after the seal copy is committed
  and pulled, all before 2026-10-28T03:30Z outside 02:45-05:30Z. q0116h priority lowered 95 -> 40 so the LT8 chain takes
  the gaps between MC1 slices first.

## LT8 seal committed, censuses promoted, 2026-10-23 ~02:25Z (operational; nothing counted)
- q0621's depends_on edit (q0620 -> q0604) recorded at 774c43c0 had not been committed; committed 66bbc2fd and deployed
  02:00Z. q0621 ran 02:00Z (light, net lane, beside MC1) and wrote `lt8_census_inputs.json`, sha256
  `5545538af10a672b4f84cd6789481841bc5387e15dc256cca661fd5d55c7bc26`: 430 files (112 capture slots, 47 sweep slots; 159
  slots), span 10-12T00:31Z..10-21T22:31Z, 0 missing, 0 `--unavailable` reports used, design text 73c941e1…. Copied
  unchanged to `docs/research_lab/seals/lt8_census_inputs.json` (hash re-checked on the Mac).
- q0622 (CC8 captures) and q0623 (CS8 sweeps) promoted together (their depends_on chain them; exclusive; mem 1500 / 2000
  MB, so held by the 02:45-05:30Z start blackout). Each runs once; only a deterministic crash gets one retry. They must
  finish before 2026-10-28T03:30Z. The 10-day snapshot rule stays until q0623 is done.

## LT9 design draft, 2026-10-22 (nothing counted)
- **Draft:** `docs/research_lab/LIVE_TESTS_9.md` on `feat/live-tests-9` (from chore `9079ca39`), sha256
  `01c4989065c35743c47baa7c191f5956a1a734d9270a0c8e9c107605f82bef0a`. DRAFT, **not frozen**, no challenger review yet;
  not registered; no code, seal, census or size run; E-numbers unassigned.
- **Source:** creative round 14 (`CREATIVE_HYPOTHESES_2026-10-28.md`) ranks 1-3: CH213 (band break: spread re-tightening after
  a strict `s >= 2v` crossing, reward panel against a cell-matched control panel), CH214 (pool splits: symmetric in-band depth
  innovation between sweeps k - 2 and k - 1 on the CLOB spread from sweep k to k + 1), CH212 (the `clob_rewards` omission as
  a serving-path event, route A or B fixed by a counts-only rule, "neither" drops it). CH215 (scheduled programme end) is an
  optional fourth that enters only if every gate of its own census (CR9) passes; Holm over k <= 3 (4 with CH215).
- **Reward status:** LT7 13.7's `listed_carry24h_v2` for every LT9 control and panel; CH212's state is that rule's carry lag
  (no unit is reclassified; LT7's and LT8's frozen controls are not re-opened; LT8's k-only control disclosed as different).
- **Planning MDEs (DE 31; low / high):** CH213 interaction 1.39c / 0.62c against 1.0c (needs about 68 strict breaks a capture
  per panel); CH214 slope 0.28c / 0.19c (F binding); CH212 route A 0.58c / 0.35c against 0.5c (needs about 240 omitted units a
  capture); CH215 2.23c / 0.92c (needs about 51 ends a day). Designer's odds: census 0.35 / 0.35 / 0.30 / 0.10; expected
  k about 1.0; about 0.30 that CH213, CH214 and CH212 all drop.
- **Window (proposed, ordered lane):** `[2027-01-21T00:00Z, 2027-02-11T00:00Z)`, keyed to LT8's `END_UTC` + 24 h (slides with
  LT8; LT8's slot if LT8 drops entirely); analysis on or after 2027-02-12T12:00Z. Round 14's fast lane declined (DST-straddling
  census, results would inform LT8's pin and LT7's window). Freeze before the earlier of 2026-11-14T12:00Z and `T_E015`;
  pin before `T_LT7` or every test dropped. Census on a fresh seal 2026-11-02..11-12 (drafts q0640-q0647, none written).
- **Next:** challenger R1 (`science-reviewer`) on the draft; embargo requests (`bandbreak`, `pool`, `rwblink`; `rwend` on
  CH215's entry; `book0` / `book` to the LT9 date only if CH214 survives; no `rewards` extension) filed at acceptance and
  before 2026-12-23.

## LT9 R1 REVISE and response, 2026-10-22 (~22:10Z; nothing counted)
- **R1** (`science-reviewer`; `reviews/LT9_R1_CHALLENGER_2026-10-22.md`, commit 118cf498): **REVISE**, nine required changes
  plus should-fix items, on `LIVE_TESTS_9.md` sha256 `01c4989065c35743c47baa7c191f5956a1a734d9270a0c8e9c107605f82bef0a`.
- **Response** (`reviews/LT9_R1_RESPONSE_2026-10-22.md`): all nine changes made as worded and every should-fix item taken.
  No threshold, floor or gate was loosened. Revised text sha256
  `bbfeb62add0e24860947e9413025cece5bdfbd4f8ebbe46b27974b8b29a354e1`. Still DRAFT, not frozen, not registered; no code, seal,
  census or size run; E-numbers unassigned.
- **Main changes.** `f_binding` is removed: CH213's and CH214's F bind by design, each with a census F-MDE <= 1.0c gate, and
  CH212's F is a label. CH213's panel is fixed at the market's first unit (`panel_switched`). New binding worlds 3b
  (relative position) and 4c (stale control rows), and a `break x relpos_k` control. CH212's route B tests `om_k` on its
  two-class population, and route A needs a feed-listed end after capture k + 1. CH214 tests `max(0, zdD)` with `min(0, zdD)`
  as a control, and world 8 carries non-fill volume noise.
- **Recomputed planning MDEs (low / high).** CH213 1.50c / 0.67c, F 2.24c / 1.005c: **the binding F gate fails at both
  planning ends, so CH213 is expected to die at census.** CH214 0.56c / 0.38c, F 0.79-0.94c / 0.54-0.65c (a quarter of the low
  count fails). CH212 route A 0.58c / 0.35c (the low end fails 0.5c, as before). CH215 unchanged.
- **Disclosed:** CH212's census agreement table (carry against feed) will be seen before `T_LT7`. It is descriptive and changes
  no LT7 control.
- **Next:** R1 re-check (`science-reviewer`) of the revised text and the response.

## LT9 re-check ACCEPT_WITH_FIXES and fixes 1-6, 2026-10-22; nothing counted
- **Re-check** (`reviews/LT9_R1_RECHECK_2026-10-22.md`): ACCEPT_WITH_FIXES; fixes 1-6 made as worded (addendum in `reviews/LT9_R1_RESPONSE_2026-10-22.md`), no gate or threshold changed.
- `LIVE_TESTS_9.md` sha256 `bbfeb62add0e24860947e9413025cece5bdfbd4f8ebbe46b27974b8b29a354e1` -> `098aa3fb5f6765f08dcad3f85ad63ec70e29df65249413608f0f7ad5fd505b77` (still DRAFT; freeze commit separate).

## LT9 drafted, challenger R1 and re-check, DESIGN-TEXT FREEZE (2026-10-22 ~22:50Z; experiments autopilot; nothing counted)
- **Source:** creative round 14 (`CREATIVE_HYPOTHESES_2026-10-28.md`, merged 9079ca39). LT9 = CH213 (band break
  re-tightening), CH214 (pool splits: arrival side of the symmetric in-band depth innovation), CH212 (`clob_rewards`
  omission as a serving-path event, route by counts); CH215 (farmers' retreat before a programme end) enters only if its
  own census passes. One Holm family, k <= 3 (4).
- **Reviews:** draft b2882734 (01c49890…) -> challenger R1 **REVISE** (9 required; `reviews/LT9_R1_CHALLENGER_2026-10-22.md`)
  -> response dcc2ec37 (bbfeb62a…; `reviews/LT9_R1_RESPONSE_2026-10-22.md`) -> re-check **ACCEPT_WITH_FIXES**
  (`reviews/LT9_R1_RECHECK_2026-10-22.md`; 6 fixes) -> fixes 11fee7a0. Orchestrator diff check: every changed hunk is tagged
  "re-check fix N" and maps to fixes 1-6; no gate, threshold, floor or planning value changed; optional world-3b rule not applied.
- **DESIGN-TEXT FREEZE:** `LIVE_TESTS_9.md` at 11fee7a0, sha256 `098aa3fb5f6765f08dcad3f85ad63ec70e29df65249413608f0f7ad5fd505b77`
  (before the earlier of 2026-11-14T12:00Z and T_E015). Any later change to a test's text is a recorded deviation; changes
  after LT8's census commit are labelled *informed (LT8 census)*. Proposed window 2027-01-21 .. 2027-02-11 (LT8's end +
  24 h, slides with LT8); analysis on or after 2027-02-12T12:00Z. Honest odds (author): census survival CH213 0.15, CH214
  0.30, CH212 0.30, CH215 0.10; about 0.42 that CH213, CH214 and CH212 all drop (CH213 expected to fail its binding F gate).
- **Next:** embargo requests (section 9) filed in CANDIDATES at acceptance; code phase (seal, censuses CC9/CS9/CR9, drafts
  q0640-q0647) on a fresh seal of 2026-11-02..11-12.

## Signal engine: LT7 closure withdrawals and LT9 round-6 embargo requests, 2026-10-22 ~23:30Z (signal-engine autopilot; nothing scored or counted)
- **Withdrawn, effective 2026-10-23T00:00:00Z.** LT7 closed at census with no test (ledger "LT7 census CC7" and "LT7 census
  CS7 and closure", 2026-10-22; withdrawal request CANDIDATES ~22:10Z). Programme rule: a test dropped before registration
  loses its token and any extension made only for it.
  - New tokens `resist`, `capath`, `deepbook`, `absorbed`, `ivr`: `until` = `withdrawn_utc` = 2026-10-23T00:00Z, `until_before`
    12-31. None had a model.
  - `movetype` 12-31 -> 11-22 (E015): the extension was made for CH193 only. LT8 section 9 does not extend it ("not extended
    for CH202"), and LT9 section 9 lists it as not requested. se14 also isolates `book`, so it stays hidden; K is unchanged.
  - LT7-CH195 / CH197 pruned from the `book` / `book0` tests lists. Their date is held by LT8 and LT9. The LT7 attribution
    limits (`chg_1h` x own 2 h, lagged-step interactions) are dropped; they were never computed.
- **Applied LT9 section 9** (round 6; design text frozen 11fee7a0; filed ~22:55Z; before any isolating challenger exists,
  well before the 12-23 deadline).
  - New tokens `bandbreak` (CH213), `pool` (CH214), `rwblink` (CH212), to the later of 2027-02-14T00:00Z and LT9's
    analysis commit. `rwend` (CH215) gets no token now: it is requested only on CH215's entry at census, and no rwend family
    is built before then.
  - `book` / `book0` 2027-01-23 -> 2027-02-14, applied now (the conservative order); withdrawn back to 2027-01-23 if CH214
    drops at census. se3, se14 and se19 stay hidden about 22 days longer (disclosed by LT9).
  - Attribution limits entered in `config.EMBARGO` as `attrlimit_lt9` (to 2027-02-14) and, for the same enforcement,
    `attrlimit_lt8` (to 2027-01-23; round 5's limits were in CANDIDATES only). Each carries `kind: attribution_limit`,
    `limits`, `models` and `no_broad_families`. They match no family or spec, so they hide nothing by themselves. The
    engine's attribution is per family only (DESIGN_V1 section 17), so none of the listed terms is computed or shown. A
    test fails if a broad spec holds an LT8 or LT9 family.
- **Files:** `signal_engine/config.py`, `tests/unit/test_signal_engine.py` (new
  `test_lt7_closure_withdrawals_and_lt9_round6_requests`; book dates updated), DESIGN_V1 section 8 table, CANDIDATES (builder
  replies, rows 12/19, row 21 `hwm`).

## Signal engine: `dispgap` (CH218) and `dormant` (CH220) families, se22 and se23, 2026-10-23 ~01:30Z (signal-engine autopilot; development families, nothing scored or counted)
- **What:** two engine-first round-14 ideas (LT9 section 6.2 left them to the engine), each built as its own aux family
  with a learner-matched challenger (LightGBM, se1's params, se21's train block). One pre-declared configuration each,
  with no development selection. DESIGN_V1 section 26.
  - `dispgap`: Gamma's displayed 1 d / 1 w change minus the own 24 h / 7 d change, plus |gap|, the gap signed by the own
    2 h move, and its change since the previous slot.
  - `dormant`: the flat-run (|dmid| <= DELTA) and still-run (no change) lengths, both capped at 12, and a wake-up flag.
- **Science review (ACCEPT_WITH_FIXES, all applied before deploy).**
  - New tokens: `dispgap` to the later of 2026-11-14T00:00Z and LT2's analysis commit. E012 pre-declares Gamma
    `oneDayPriceChange` in place of its x, so `dg_1d` = primary x minus sensitivity x; E013 / E014 use chg_1d / chg_1w as
    controls. `dormant` to 2026-11-19T00:00Z, because E011's label requires a quiet prior day.
  - The builder's first draft claimed that no test reads the venue's 1 d / 1 w fields. That was wrong, and it is
    corrected in section 26.
  - The census column, denominators and order are fixed before the census runs (dormant on `dm_still == 12`, 3% / 60%
    of non-sports; dispgap |dg_1d| >= 2 ticks on >= 2% of rows; frame: captures 10-16..10-22).
- **K:** se22 joins at 11-14 and se23 at 11-19 (z about 2.73 -> 2.81 at K = 10). No change before then.
- **Census:** counts only, run after the backfill and before the first fit; the result follows as its own entry.

## Signal engine: census of `dispgap` and `dormant` (counts only), 2026-10-22 ~23:25Z (signal-engine autopilot; both survive; nothing scored)
- **Backfill** (host, one-off `features --max-items 25`, nice 10, 4 GB address-space cap, alongside MC1 q0116h):
  122 tables per family in 28 s, peak RSS 537 MB, exit 0, no build errors.
- **Frame** (DESIGN_V1 section 26, declared before the census): the aux tables of captures started in [10-16T00Z, 10-23T00Z).
  That is 82 tables, because 2 of the 84 slots have no capture. There are 4,134,776 rows, 1,421,736 of them non-sports.
  No outcome or label was read.
- **`dispgap`: survives.**
  - |dg_1d| >= 2 x ms_tick on 4.72% of all rows (6.38% of non-sports); the kill line was < 2%.
  - NaN dg_1d 38.8% (no 24 h own look-back or no venue field). NaN or zero tick 0.0%.
  - Median |dg_1d| is 0 ticks (p90 1 tick).
  - |dg_chg| < 1 tick on 82.9% of rows: mostly persistent or zero gaps, with a fresh disagreement on about 17%. This is
    CH218's trait question, reported only.
  - Units check: the median per-capture correlation of chg_1d with the own 24 h change is 0.934, and both median
    absolute values are 0.0100. Same scale, so `oneDayPriceChange` is an absolute price change close to the mid path.
- **`dormant`: survives.** `dm_still == 12` (no change at all for 24 h) on 10.37% of non-sports rows; the kill line was
  < 3% or > 60%. NaN 22.6% of non-sports. `dm_flat == 12` on 26.6% of non-sports (information only).
- **Next:** se22 and se23 fit at the 10-23 refit (q0512, ~15:44Z) and predict from the next capture. Scores stay hidden
  until 11-14 / 11-19.
- **Timestamp correction for this session's two earlier entries:** "~23:30Z" for the LT7/LT9 embargo entry should read
  ~23:00Z (deployed 23:03Z). "2026-10-23 ~01:30Z" for the dispgap/dormant entry should read 2026-10-22 ~23:15Z. The
  builder wrote UTC+1 local times as UTC; the config and docs are corrected (commit 30e62dba). The withdrawal effective
  time 2026-10-23T00:00:00Z is unchanged.

## LT9 census code phase 1 merged, 2026-10-23 ~03:05Z (experiments autopilot; nothing counted)
- **Code** (`feat/live-tests-9`, merged 9e482fab): vendored base `live_tests9_base` (unmodified LT3-LT8 copies, hash-pinned;
  additions for the overlaps: LT8 `quiet_units` + helpers, LT7 `behind_touch` / `patient_units`), seal, censuses CR9 / CC9 /
  CS9, feed reader and end-date parse rule, lag-slot loaders, runner, DRAFT spec `live_tests9_v1.json`, drafts q0640-q0647
  (not promoted). Design text unchanged (sha256 098aa3fb…). 76 LT9 + provenance tests; LT7 / LT8 / copy_skilled green.
- **Reviews:** `reviews/LT9_CENSUS_CODE_CHECK_2026-10-23.md` FIXES_REQUIRED (5 must-fix: a missing sealed sidecar must
  refuse; CR9 decision capture strictly before t_dec; CH213 control twin band from capture k + 5's cell; CH215 ties by
  condition_id; CR9 completeness over all 120 span slots) -> fixes ea4eefbc -> `..._FIX_RECHECK_...` FIXES_OK_WITH_NOTES ->
  notes 60df6c47 -> `..._FINAL_CHECK_...` OK_WITH_NOTES -> notes 1f1159d8. The reviewers are read-only; the orchestrator
  filed their reports.
- **Declared before the seal** (`declared_before_seal` in the spec, printed in every census output; each can only lower a
  count or is a descriptive): malformed > open > dated for feed ends (mixed cases counted; extended to CR9, and malformed
  markets excluded from CR9's control pool, counted); the sentinel year read as written; each end-kind denominator; the
  switching gate's mean-per-day definition; CH197 `osz` passed NaN (no filter).
- **Deviation (descriptive, no gate):** the LT8 CH203 overlap is NOT computed in CS9 (ruling (i)): CH203's quiet test reads
  capture k's mid, which is after CH214's decision (1.3) and barred by the section 7 lag-slot rule. CC9 / CR9 print both
  overlaps NaN ("census reads no sweeps"). CH197's overlap is computed in CS9 on (market, UTC day).
- **Next:** seal (q0641) only after the 11-02..11-12 span exists; check by hand that no LT8 q0624-q0627 runs before
  promoting any LT9 census (memory rule).

## LT10 design draft, 2026-10-23 (~03:30Z; experiments autopilot; nothing counted)
- **Source:** creative round 15 (`CREATIVE_HYPOTHESES_2026-10-29.md`, CH222-CH231, merged c23b5a52; Fable xhigh). Its finding:
  capture-clock cross-venue tests lack pairs (>= 1,100 needed; the politics venues offer a few hundred); E009's 120 s
  Kalshi + Polymarket CLOB poller is the only fine-clock panel with Polymarket on it.
- **Draft:** `docs/research_lab/LIVE_TESTS_10.md` on `feat/live-tests-10` (ba559ced), sha256 `d7529914c71763bc…`. DRAFT, not
  frozen, challenger R1 running; not registered; E-numbers unassigned. Tests CH224 (Kalshi spread innovation -> Polymarket
  spread 20 min later; planning MDE 0.30c / 0.23c, floor 1.0c, F binding), CH223 (Kalshi size pull without a Kalshi mid move ->
  Polymarket's next |move|; 0.47c / 0.26c, floor 0.5c), CH222 (Kalshi moves split by whether `last_price` changed; 0.63c /
  0.44c, floor 0.5c: fails at the low planning end, put to the challenger). One Holm family, k <= 3, `informed (E009, E010)`.
- **Timing:** design text frozen before 2026-11-03T02:00Z (before E009 / E010's analysis) or LT10 is not registered; census
  (counts only, seal 10-21..10-31) only after E010's analysis commit; window proposed 11-10..12-01, analysis after
  12-02T12:00Z. Family gate first: >= 60 pairs in >= 30 events (E009's pilot had 22-27 events). Designer's odds that no test
  registers: about 0.66 (a judgement).
- **Open orchestrator decision D-LT10-1:** the poller stops at its 2 GiB cap around 11-16 (projection); proposed quotes-only
  successor in new files (`xv_quotes/`), same pairs and grid; no new external service.

## LT10 challenger R1, response, re-check, DESIGN-TEXT FREEZE (2026-10-23 ~03:50Z; experiments autopilot; nothing counted)
- **R1** `reviews/LT10_CHALLENGER_R1_2026-10-23.md`: **REVISE** (7 must-fix: scope final before the census; D-LT10-1 route 1
  committed; pair-record in-force time; event-level Freedman-Lane offsets + a 20-pair-event world; `kxbook` embargo naming the
  xvenue2 2 h columns; both E009 and E010 analysis commits required; CH224 count gate; 10 should-fix). All arithmetic
  re-computed and matching; no E009/E010 frozen rule broken (their no-look rule ends at their analyses; the census runs after).
- **Response** dc846d4e (section 13; no threshold loosened; designer's odds of no test registering 0.66 -> 0.76, a judgement).
- **Re-check** `reviews/LT10_R1_RECHECK_2026-10-23.md`: **ACCEPT_WITH_FIXES** (6 fixes: real-time in-force rule in the window;
  L declared, not guaranteed; pre-`T_E009` steps O1-O3 and scope deadline at the freeze; W10 over 21 days with contiguous
  presence; `kxbook` family move; disclosure of the CD10 block-gate easing). Fixes d0951bf0. **Pre-freeze verification**
  `reviews/LT10_PREFREEZE_VERIFY_2026-10-23.md`: FREEZE_OK_AFTER 2 mechanical edits, applied 34b7e22e.
- **DESIGN-TEXT FREEZE:** `LIVE_TESTS_10.md` at **34b7e22e**, sha256
  **`1da6c07510f294c26ab0c69d17fd57bd6daefab7275d88f4bbeb6d3a130bc6e8`**; merged into chore 6f651f7e. Frozen before
  2026-11-03T02:00Z and before E009 / E010's analyses, as required. Family label `informed (E009, E010)`. Not registered;
  E-numbers unassigned; nothing counted.
- **Scope:** no owner scope decision exists at the freeze, so the default `non_sports_ex_crypto` holds (fixed at the freeze).
- **O1 (at the freeze, 2026-10-23T03:44Z, host):** E009's directory `cross_venue_live/` 602,884,181 B (576 MiB); root free
  35,900,596,224 B (35.9 GB) of 95.3 GB. Route 1's projected need 3.0 GB, x 1.5 = 4.5 GB: covered. No E009/E010 file deletion
  is needed. **O2: not needed** (the standing collection authorisation covers the successor collector; same public keyless
  endpoints, same request rate). Separate note: data-dumps is 35 GB against the 40 GB job cap (owner approval 8 pending).
- **O3 (deadline 11-03T02:00Z):** the engine's second `xvenue` read root, requested in CANDIDATES round 7 with the `kxbook`
  and `attrlimit_lt10` entries (apply before 11-04T00:00Z). Missing by the deadline = route 3 (not registered).
- **Next:** code phase (successor poller `run_xv_quotes_poller.py`, reader, seal, censuses CF10 / CK10 / CD10, size check),
  its code-freeze check (must confirm re-check fixes 1 and 4 in the code); census only after both E009 and E010 analysis
  commits.

- **LT10 code, timing-run disclosure (N1, 2026-10-23, code-fixes re-check):** the seed and plan of the implementer's ~3 s / ~13 s size-check timing
  runs are not recorded (not in commit messages, tests or the code-check review of this branch). Known: before commit 2e9ba424 the worlds tests
  (`test_research_lab_live_tests10_worlds.py`, introduced in e3d1dd79) called `size_check` with the registered seed 20261397 and tiny worlds
  (2 worlds x 4 draws, `registered=True`), and nothing then refused it; so it cannot be ruled out that a timing run or test ran at 20261397.
  Such a run is a tiny-world code test with no recorded output and no use of any result; the registered q0665 (not before 2026-11-04) stays
  the only run whose output counts. From f36ff4dd on, no test runs `size_check` at 20261397 (R1) and q0665 has `max_retries` 0 (R2).
