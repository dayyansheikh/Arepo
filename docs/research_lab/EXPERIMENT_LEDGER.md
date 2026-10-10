# AREPO research-lab experiment ledger

Track A (D115) exploratory experiments. Every registered experiment stays listed whatever its outcome:
positive, negative, inconclusive, invalid or unavailable. Each entry is written and committed **before** its outcomes
are computed. Later edits only add results or record deviations. **Development data only.** No result here is
validated edge or confirmation evidence. A positive result is a hypothesis for later prospective confirmation.

| ID | Status | Question | Result summary |
|---|---|---|---|
| E001 | COMPLETE (exploratory) | Do price/momentum/context fields in Gamma full-universe snapshots predict repricing by the next snapshot, beyond no-change? | 1h-change model *Indicative (exploratory)*: R2_oos +0.037, positive in 4/4 periods; the fitted sign is **reversal** (about -0.3). Others inconclusive. No edge claim. |
| E002 | REGISTERED (pre-outcome) | Does the E001 1h-change reversal hold prospectively on new full-universe snapshots, using a frozen coefficient? | pending |
| E003 | COMPLETE (exploratory) | Does top-of-book imbalance or microprice displacement (H08/H09) predict the next few minutes of midpoint repricing, beyond no-change and the 1h reversal? | H08 and H09 **inconclusive** (R2 about 0). The combined model beats reversal-only (+0.031 [+0.011,+0.049]), but only in wide-spread markets; the gain comes from spread/intercept drift, not imbalance. No edge claim. |

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
