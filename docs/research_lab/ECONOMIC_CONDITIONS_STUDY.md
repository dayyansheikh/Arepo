# Economic conditions study (paper only)

`evidence_role: exploratory_dev` | EXPLORATORY, post-hoc, paper-only. AREPO never trades. No edge, profitability or
tradability claim. Written 2026-10-12. Code: `backend/scripts/econ_conditions_taker.py` (live Gamma touches) and
`backend/scripts/econ_conditions_maker.py` (historical pmxt books plus trade prints). Trial lines: kinds
`econ_conditions_taker` and `econ_conditions_maker` in `trials.jsonl` (95 tested cells, BY applied across all).

## Question
E004 (reversal) and E007 (flow continuation) are statistically real but small. Are there conditions where they cover
the cost? (1) top-liquidity markets; (2) large predicted moves; (3) passive entry; (4) E004 and E007 in the same direction.

## Verdict
**No condition has a positive after-cost CI.** Of 95 one-sided tests (H: mean net P&L per share > 0), the smallest raw
p is 0.62 and the smallest BY-adjusted p is 1.0. Zero pass. The one place a CI is positive (below) assumes a free exit
and is not a tradable result.

## Method
- **Taker P&L (part A).** One share, entry at the origin touch, exit at the next-snapshot touch (about 2h), so
  `net = d*(mid_j - mid_i) - half-spread_i - half-spread_j - fee_i - fee_j`. Fee `rate*p*(1-p)` on each leg from the
  per-market sidecar schedule (`economics.fee_spec`, policy `max_if_unknown`, unknown = 0.07). Sidecar rows exist only
  in captures from 2026-10-11 12:00Z onward, so earlier captures use the same market's schedule from a later capture
  (a market attribute); 1% of E004 trades had no schedule and took 0.07.
- **E004 population:** the registered 11-period panel, trades where `|dmid_hat| > spread/2`, direction `sign(dmid_hat)`
  (frozen -0.3316*chg_1h): 9,541 trades, 2,734 event clusters. Reproduces E004's -0.045 touch-to-touch before fees.
- **E007 population:** the 12 confirmation periods, 29,860 pairs (4,982 with flow). Directions: flow = `sign(signed_share)`;
  reversal = `-sign(chg_1h)`; combined = same direction only; "augmented sign" = sign of the frozen dev-fit prediction.
  Weighted by 1/inclusion probability.
- **Inference.** Event-clustered bootstrap of the (weighted) mean, 2,000 resamples, seed 116, 95% two-sided CI and a
  one-sided p for mean > 0. Cells with fewer than 30 clusters are not tested. **Benjamini-Yekutieli** across all 95
  testable cells of parts A and B (conservative: it includes the many clearly negative cells).
- **Maker (part B).** Books: pmxt v2 hourly archive at 6h-grid origins (`history_sources/book_features/rows.jsonl`, two-sided
  books only), 2026-04-13 to 2026-08-10. Prints: `h2_main` Data API trades. Rows with `traded_before_t == 0` are excluded
  (programme placeholder-price rule). 6,632 origin-market rows after filters, 3,737 signalled orders. A passive order is
  posted at the touch at origin (buy at bid for an up signal, sell at ask for a down signal) and lives until the 2h
  target. Prints are converted to outcome-0 terms (a BUY of outcome 1 at q is a sell of outcome 0 at 1-q).
  Fill rules: **touch** (any opposite-aggressor print at or through our price: optimistic, queue-free);
  **through** (strictly through); **queue** (cumulative aggressor volume at or through our price reaches the displayed
  top-of-book size plus our 5 shares). Exit: **mark** at the 2h history mid (free exit: optimistic) or **taker exit**
  (half the entry-time spread plus the exit fee). Unfilled orders earn 0 and are not losses.
- **Rebates.** Source: <https://docs.polymarket.com/trading/fees>, fetched 2026-10-12. It states that "Makers are never
  charged fees" and that taker fees fund a Maker Rebates Program that redistributes fees daily. Listed rebate shares:
  crypto 20%, sports 15%, finance/politics/economics/culture/weather/other/mentions/tech 25%, geopolitics not listed. The
  page does not say how the rebate is allocated, so the model assumes the optimistic case: the share applies pro rata to
  the fee on our own fill. No liquidity-rewards programme is documented on that page, so none is modelled (the sidecar's
  `rewards_min_size` and `rewards_max_spread` fields exist but their payout rules are undocumented here).

## Results: taker (part A)

All figures are cents per share. Gross is the realised mid-to-mid move in the predicted direction; costs are positive numbers.

| Condition | n trades (clusters) | gross | spreads | fees | net [95% CI] |
|---|---|---|---|---|---|
| E004 all selected | 9,541 (2,734) | +4.01 | 8.53 | 1.15 | -5.67 [-5.88, -5.44] |
| E004 liquidity >= $10k | 1,466 (785) | +0.63 | 2.14 | 1.41 | -2.92 [-3.37, -2.46] |
| E004 liquidity >= $50k | 208 (115) | +0.92 | 0.77 | 1.30 | -1.15 [-2.58, +0.44] |
| E004 liquidity >= $100k | 91 (50) | -0.24 | 0.62 | 1.06 | -1.92 [-4.10, -0.13] |
| E004 top predicted-move decile | 949 (278) | +11.51 | 17.33 | 0.64 | -6.46 [-6.90, -5.88] |
| E004 top 1% predicted move | 99 (56) | +10.59 | 13.08 | 0.55 | -3.04 [-4.93, -0.35] |
| E004 top decile and liq >= $10k | 4 (3) | not testable | | | |
| E007 flow, all | 4,982 (2,191) | +0.26 | 2.66 | 1.38 | -3.79 [-3.98, -3.59] |
| E007 flow, liq >= $10k | 2,468 (1,173) | +0.24 | 1.80 | 1.33 | -2.89 [-3.09, -2.70] |
| E007 flow, liq >= $100k | 524 (159) | +0.25 | 0.77 | 1.05 | -1.57 [-1.96, -1.10] |
| E007 flow, top magnitude decile | 499 (-) | +0.21 | - | - | -4.18 [-4.58, -3.82] |
| E007 reversal, liq >= $100k | 173 (84) | -0.24 | 0.66 | 0.84 | -1.73 [-3.08, -0.73] |
| **Combined (same direction), all** | 871 (621) | +0.95 | 3.23 | 1.39 | -3.67 [-4.23, -3.08] |
| Combined, liq >= $10k | 317 (253) | +0.86 | 2.37 | 1.37 | -2.88 [-3.57, -2.23] |
| Combined, liq >= $100k | 25 (22) | not testable | | | |
| Combined, top decile of summed magnitude | 88 (81) | +3.40 | 4.60 | 1.54 | -2.74 [-6.60, +1.55] |
| Disagreeing signals, liq >= $100k | 102 (57) | +0.90 | 0.68 | 0.85 | -0.63 [-1.90, +1.39] |
| Augmented-model sign, liq >= $100k | 1,182 (206) | -0.02 | 0.79 | 1.01 | -1.83 [-2.07, -1.61] |

(All cells, including magnitude deciles/quintiles for each signal, are in the trial lines.)

Reading:
1. **Liquidity** cuts the spread cost as the EXECUTION_COSTS table says (about 0.6-0.8c round-trip spread at >= $100k)
   but the fee does not fall (1.0-1.4c at mid prices), and the gross move **also shrinks** in liquid markets: E004's 4c
   gross is largely bid-ask bounce in wide-spread, illiquid quotes (median liquidity $531 among E004 trades). At >= $100k
   the gross is -0.2c (E004) to +0.25c (E007), far below the roughly 1.5-1.9c cost floor. The E007 flow gross of about
   0.25c at $100k matches E007's reported +0.36c per fully one-sided hour.
2. **Large predicted moves.** E004's realised gross rises with predicted size (0 to 11.5c from decile 1 to 10) but the
   spread rises faster (1.2c to 17.3c), because large `chg_1h` appear where quotes are wide and stale. Net is negative in
   every decile (-2.3c to -7.7c). The top decile contains almost no liquid markets (median $65). E007 magnitude buckets
   are net -2.9c to -4.7c.
3. **Combining** the two selects few trades (871 of 29,860 pairs with both signals nonzero and agreeing) and the gross
   (+0.95c) does not add up to anything near cost. The top-decile combined cell has a CI that straddles zero because it
   has 88 trades; its point estimate is still -2.7c.

### The single positive CI (not tradable)
E004's optimistic variant (`exit at mid_j`, entry still crosses the spread and pays the entry fee, exit costs nothing)
is positive for the top three predicted-move deciles: decile 10 +8.3c [+6.2, +10.2], top 5% +9.6c [+6.8, +11.7]
(484 trades, 120 clusters), `|pred| >= 5c` +3.4c [+2.4, +4.3] (4,758 trades). **This is not an after-cost result.** It
needs a free exit at a quote mid that is not executable (those markets have a median $65 to $135 of liquidity and
10c-17c half-spread round trips). It is not in the BY family. It only says that, if an exit at a fair price were
possible, the entry cost alone would not erase E004's bounce. This is part of the reason to examine passive entry.

## Results: passive entry (part B)

Historical, 2026-04 to 2026-08, 6h-grid origins with a two-sided pmxt book. Spreads are wide in this sample (mean 16c
for reversal orders, 3.4c for flow orders), because the history frame has no liquidity filter. Cents per filled share unless stated.

| Signal | Fill rule | Fill rate | Mean move, filled vs unfilled | Mark exit (free) net [95% CI] | Taker exit net [95% CI] |
|---|---|---|---|---|---|
| Reversal (2,532 orders, 273 clusters) | touch | 12% | -2.78 vs +0.19 | -0.96 [-2.03, +0.07] | -3.35 [-4.63, -2.31] |
| Reversal | through | 8% | -4.84 vs +0.22 | -2.58 [-4.53, -0.98] | -5.40 [-7.64, -3.76] |
| Reversal | queue | 6% | -3.69 vs +0.06 | -1.65 [-3.59, +0.06] | -4.26 [-6.27, -2.65] |
| Flow (1,051 orders) | touch | 33% | -0.91 vs +0.73 | -0.21 [-1.33, +0.50] | -1.39 [-2.97, -0.62] |
| Flow | queue | 11% | -2.30 vs +0.51 | -1.18 [-3.61, +0.81] | -2.82 [-5.56, -0.86] |
| Same direction (154 orders) | touch | 33% | -2.09 vs +1.03 | -1.17 [-4.19, +0.71] | -2.71 [-5.66, -0.88] |
| Same direction | queue | 19% | -1.45 vs +0.33 | not testable (29 fills) | not testable |

For comparison, taker entry at the touch on the same orders loses 17.6c (reversal), 4.4c (flow) and 7.9c (same
direction) per share. Rebates add only about +0.1c per filled share (e.g. reversal touch/mark -0.96c to -0.85c).

Reading:
- **Adverse selection is large and consistent.** Orders that fill are the ones where price moved against us: the mean
  mid move in the predicted direction is -0.9c to -7.0c for filled orders but +0.1c to +1.1c for unfilled ones, in every
  signal and every fill rule. Even the most optimistic cell (touch fill, free mark exit, rebate) has a negative mean and no
  positive CI (smallest raw p 0.62). With a real exit, every testable cell has a CI entirely below zero.
- Fill rates under the queue rule are 4-19%, so expected value per attempted order is about -0.1c to -0.9c; passive
  entry does not rescue the signals. The 2h edge (E007 +0.36c) is smaller than the adverse-selection loss.
- Rebate size is immaterial here: the fee on a filled mid-price share is about 1.5-1.7c and the rebate share is 15-25% of
  it, so about 0.1c to 0.4c.

## Optimistic assumptions (all of which favour finding a positive result)
- Touch-to-touch fills with no depth limit, latency or queue (taker part); one-share size; no price impact.
- Fills at the touch print with no queue (`touch` rule); `through` and `queue` are the less optimistic ones.
- Free exit at a history mid (`mark`), which is mid-like but unverified; history-price/pmxt-book source gap averages 0.75c.
- Rebate applied pro rata to our fill although the allocation rule is not documented.
- Fee schedules of later captures applied to earlier ones; the 2h exit is assumed possible at the next-snapshot touch.
- No hold-to-resolution variant (different rule, not modelled); no shorting constraints.

## Limitations
- Live data span about 22h of one day (E004 and E007 share it); 1-2 independent time blocks. Historical part B is 245
  origins over about four months, 6h-grid only, with an unweighted market subsample (971 markets) and wide spreads.
- Part B's signals are the history-panel analogues (`ml_chg_1h` from the price series, signed share from prints), not the
  Gamma `oneHourPriceChange` of E004 or the frozen E007 coefficients. Direction rules use the signs only.
- Liquidity is unavailable in the history panel without end-of-life leakage, so the liquidity-conditional test exists only
  for the live part (where Gamma liquidity at origin is a point-in-time field).
- Thresholds (liquidity $10k/$50k/$100k, deciles, quintiles) were fixed by the question and not tuned. Tie-breaking
  within the discrete E007 magnitude buckets is by row order.
- 95 one-sided tests; clearly negative cells inflate the BY denominator, which only makes passing harder. Even
  unadjusted, no testable cell has p below 0.62.

## Conclusion
Under the conditions asked, the confirmed signals do not cover costs: at >= $100k liquidity the cost is 1.5-1.9c while
the realised gross is 0.0-0.25c; large predicted moves occur where spreads are larger than the moves; combining adds few
trades and no gross; and passive entry pays for itself in adverse selection (filled orders move against us 1-7c). Any
future economic hypothesis would need a different source of gross edge (an informed-flow signal, not bounce) or a
strategy that earns the spread (two-sided quoting), which is a different study with its own registration.
