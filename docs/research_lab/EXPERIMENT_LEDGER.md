# AREPO research-lab experiment ledger

Track A (D115) exploratory experiments. Every registered experiment stays listed whatever its outcome:
positive, negative, inconclusive, invalid or unavailable. Each entry is written and committed **before** its outcomes
are computed. Later edits only add results or record deviations. **Development data only.** No result here is
validated edge or confirmation evidence. A positive result is a hypothesis for later prospective confirmation.

| ID | Status | Question | Result summary |
|---|---|---|---|
| E001 | COMPLETE (exploratory) | Do price/momentum/context fields in Gamma full-universe snapshots predict repricing by the next snapshot, beyond no-change? | 1h-change model *Indicative (exploratory)*: R2_oos +0.037, positive in 4/4 periods; the fitted sign is **reversal** (about -0.3). Others inconclusive. No edge claim. |

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
