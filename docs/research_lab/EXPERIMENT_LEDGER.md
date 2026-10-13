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
