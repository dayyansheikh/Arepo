# Execution cost model v1 (paper; development tool)

AREPO never trades. This model prices *hypothetical* executions so that every cost check in the programme uses
the same fee table, the same book walk and the same documented maker assumptions. Results are paper estimates,
"optimistic, not tradable". Nothing in this document changes a past verdict: past outcomes stand, and a re-check
of a closed candidate needs its own registered design.

- Code: `backend/astrolabe/research_lab/costs.py` (pure functions, typed, units in the docstrings).
- Calibration script: `backend/scripts/cost_model_calibration.py`; output
  `backend/astrolabe/research_lab/model_specs/cost_model_calibration_v1.json`; queue draft
  `docs/research_lab/queue/drafts/qcm1_cost_model_calibration.json`.
- Tests: `backend/tests/test_costs.py`, `backend/tests/test_cost_model_calibration.py`.
- It complements `EXECUTION_COSTS.md` (one-snapshot taker distribution, 2026-10-11) and `economics.py` (H2a/H2b
  paper P&L), and does not replace them. The fee tables are pinned equal to `economics.py` by a test.

Units: prices, spreads and every `*_ps` value are probability units per share (USDC per outcome share;
1c = 0.01). `notional` is USDC. "Gross" is the mean mid-to-mid move per share in the signal's direction.

## 1. How costs are assumed today (inventory, 2026-10-19)

There are at least 15 separate cost implementations. They disagree on the following points.

| Point | Variants in the code |
|---|---|
| Fee for an unknown category | 0.07 (`cb1_history.fee_rate`, `cross_venue_live`, `economics` max-if-unknown); **0** (`battery.fee_rate`, used by `battery2._paper_cost`, which priced F4/F5); 0.05 (`cb11_w`); a 0.04 floor (`cb15_common.taker_rate`) |
| Fee source | per-market `feeSchedule` (`economics`, `econ_conditions_taker`, `cb13_t`) vs the docs category table (`cb1_history`, `cb11_w`, `econ_conditions_maker`) |
| Exit leg | charged (`cb1_history` exits, `battery`, `cb15`, `econ_conditions_taker`); entry only (`cb1_history.cost_model`, `EXECUTION_COSTS.md` break-even); exit only (`cb13_t` T3) |
| Spread | half-spread band table per side (`cb1_history.HALF_SPREAD`: 2.05/1.50/1.10/1.50/1.25c by price band); full-spread band medians (`battery.BAND_SPREAD`); 2c floor (`cb2_weather`); none (`cb15`); recorded touch (`e004`, `cross_venue_live`) |
| Depth / impact | only `economics.sweep_fill` and the CB3 queue rule; everything else fills at the touch with unlimited size |
| Maker | `cb3_maker` (touch / queue rules, rebate halved), `econ_conditions_maker` (rebate not halved); rewards are never in a primary |
| Cost sensitivity | +0.75c binding (`cb1_history.COST_SENS`, `cb5_seed.BIND_COST`, `cb2_weather`); +1c per side (`cb15`) |
| Cost register | `cost_regimes.py` reads `model_specs/cost_regimes_v1.json`, which was never written (CB4 E1/E2 "not testable"), so the CB1 defaults apply |

The "about 3.5c" quoted for F4/F5 (EXPERIMENT_LEDGER SB2-J2) is the favourable-tercile mean spread 2.68c plus a
round-trip fee of 0.84c, touch fills only. Section 5 reassesses it.

## 2. Fees and incentives: official sources (retrieved 2026-10-19)

**Facts** (quoted from official pages):
- **Taker fee**: `fee = C * feeRate * p * (1 - p)` (https://docs.polymarket.com/trading/fees; the page was last
  updated 2026-07-10). Rates: crypto 0.07; sports, economics, culture, weather, other 0.05; finance, politics,
  mentions, tech 0.04; geopolitics 0. "Makers are never charged fees." Fees are rounded to 5 dp (minimum 0.00001).
  The docs example is 100 shares at 0.50: 1.75 at crypto, 1.00 at 0.04 (pinned in a test). At p = 0.5 one taker
  leg therefore costs 1.0c (0.04), 1.25c (0.05) or 1.75c (crypto) per share.
- **Per-market schedule**: Gamma `feesEnabled` and `feeSchedule{rate, exponent, takerOnly, rebateRate}`
  (https://docs.polymarket.com/market-data/market-details). The changelog of 2026-03-31 says fees "should now be
  calculated using the `feeSchedule` object". Some sports markets still carry a 0.03 rate.
- **Maker rebates** (https://docs.polymarket.com/programs/maker-rebates): funded by taker fees in the market.
  The share is crypto 20%, sports 15% and other fee-enabled categories 25%. The rebate is
  `(own fee-equivalent / total fee-equivalent) * pool`, paid daily (minimum $1). The rate is at Polymarket's discretion.
- **Taker rebates** (https://docs.polymarket.com/programs/taker-rebates): volume tiers from 3% to 50% since
  2026-05-28. Not modelled; a research account would sit in no tier.
- **Liquidity rewards** (https://docs.polymarket.com/programs/liquidity-rewards): quadratic score
  `((v - s) / v)^2` of resting size within `rewardsMaxSpread` of the adjusted mid, sampled each minute. Two-sided
  quoting is required outside [0.10, 0.90]. Rewards are paid for quoting, not for fills.
- **Holding rewards**: 4% annualised on eligible markets (`holdingRewardsEnabled`). Not modelled.
- **Mechanics**: order types GTC/GTD/FOK/FAK plus post-only; gasless relayer; no Polymarket deposit or
  withdrawal fee; tick sizes from 0.1 down to 0.0001 (0.01 and 0.001 seen); `orderMinSize` 5.
- **History** (https://docs.polymarket.com/changelog plus Wayback captures):
  - no taker fees before 2026-01-05;
  - crypto from 2026-01 to 2026-03-06;
  - all categories except geopolitics for markets deployed on or after 2026-03-30;
  - CLOB V2 and pUSD collateral on 2026-04-28;
  - crypto rate 0.072 changed to 0.07 between 2026-04-22 and 2026-05-15;
  - sports rate 0.03 changed to 0.05, and the sports rebate 25% to 15%, on 2026-07-10.

  Historical studies must use the fee era of the data (`cost_regimes.FEE_ERAS`).

**Assumptions / uncertain:**
- The same formula applies to sells. Captures before 2026-04-22 said fees were taken in shares on buys and USDC
  on sells; current docs say only "takers".
- The rebate pool haircut of 0.5 per filled share (`REBATE_POOL_HAIRCUT`; the CB3 convention).
- Whether `orderMinSize` is in shares or USDC (the docs say USDC, the examples use shares). Here it is taken as shares.
- Polymarket US (QCX, CFTC filing) has its own schedule (taker Θ 0.0695 since 2026-09-17, maker rebate Θ -0.0125).
  It is not the venue of AREPO data and is not modelled.

## 3. The model (`costs.py`)

| Function | What it does |
|---|---|
| `taker_rate(category, schedule_rate, fees_enabled, policy)` | One rule for every check. `conservative` (default) = max(schedule, docs); fees disabled gives 0; unknown gives 0.07, never 0 |
| `taker_fee_ps`, `maker_rebate_ps` | Fee per share (formula above); expected rebate per filled share = share x fee x pool haircut |
| `levels_from_summary`, `walk`, `depth_notional_within` | Conservative levels from a sweep row, with each band priced at its outer edge, so the cost is an upper bound. The walk takes shares or USDC notional |
| `taker_leg`, `round_trip_from_quote` | Half-spread, impact, fee and staleness per leg; exit by crossing, or hold to resolution (no exit cost) |
| `staleness_haircut_ps(latency_s, sigma_1h, kappa=0.4)` | ASSUMPTION: an expected loss of 0.4 x the mid SD over the latency. For a 60 s delay and a 1-1.3c hourly SD this is about 0.05c. It matters only for stale-quote signals |
| `fill_probability(Q, q, p_active, scale, alpha)` | Back-of-queue touch order fills fully with `P = p_active * (1 + (Q+q)/scale)^-alpha` (Lomax hitting volume); calibrated per tier |
| `fill_conditioning(AS, scenario)` | Shortfall of the move on filled orders. `independent` (optimistic): the tier's adverse selection. `conservative` (default): max(tier AS, 2.81c, the only signal-conditional estimate, from flow signals in ECONOMIC_CONDITIONS_STUDY part B) |
| `maker_entry` / `MakerLeg` | Per fill: `gross + h - fill_conditioning + rebate - exit_cost`; per attempt = `p_fill` x per fill; break-even gross |
| `cost_check(gross_ps, mid=, spread=, category=, liquidity=, impact_ps=, ...)` | The standard check: taker round trip and net, the taker hold-to-resolution cost, maker net per fill and per attempt, break-evens, an assumptions dict and a "development cost check" label |

## 4. Calibration (development data; descriptive, not a test)

**Data and window.**
- Read-only run on the collection host in `/tmp/costmodel`, deleted afterwards.
- Window: the first sweep of each 2-hourly pair over 2026-10-16T04Z to 2026-10-19T00Z (34 origins).
- Inputs: their snapshots (liquidity, event, fee fields); for maker fills, the first trade sample starting at
  least 1 h + 60 s after each origin.
- Trade files only remain on the host from 2026-10-16T04:40Z, so the maker part could not use an earlier window.
  A books-only check on 2026-10-12 to 2026-10-14 (24 origins) gave the same tier picture.
- No registered test's outcome variable is read. Book sweeps feed CB16 only as a reported depth descriptor, and
  trade samples are refused by CB13 to CB16. The quantities are unconditional (no signal, no outcome).
- Runtime: 305 s, peak RSS 1.46 GB.

**Quotes and taker depth.** Outcome-0 two-sided books; 842,979 token-origins.
- Medians, except the p90 spread column.
- "Fillable within 5c" means the recorded depth within 5c of the touch covers the order.
- The $100 round trip is a conservative walk: buy for $100, then sell the shares back on the same book, both fees
  included. It covers only the books where both legs fill.

| Liquidity tier | n | Spread (p50 / p90) | Touch ask $ | Ask depth within 1c / 5c $ | Fillable within 5c: $10 / $100 / $1000 | Impact $100 (p50 / p90) | $100 round trip (p25 / p50 / p75) | 2h mid SD |
|---|---|---|---|---|---|---|---|---|
| <1k | 226,658 | 4.9 / 8.9c | 6.5 | 14 / 27 | 68% / 25% / 2% | 1.0 / 3.7c | 6.3 / 9.9 / 12.2c | 4.4c |
| 1k-10k | 411,016 | 3.0 / 7.0c | 12.9 | 77 / 254 | 96% / 73% / 17% | 0.9 / 3.9c | 5.2 / 7.2 / 10.4c | 1.4c |
| 10k-100k | 195,718 | 2.0 / 4.3c | 33.9 | 166 / 658 | 93% / 74% / 43% | 0.3 / 2.4c | 2.9 / 3.9 / 5.3c | 1.3c |
| >=100k | 9,587 | 1.0 / 1.0c | 1,646 | 11,086 / 41,696 | 100% / 100% / 99% | 0 / 0.7c | 1.9 / 2.9 / 3.5c | 1.9c |
| all | 842,979 | 3.0 / 7.0c | | | | | 4.0 / 6.0 / 9.5c | |

- By category, the median $100 round trip is:
  - crypto 9.7c, of which fees 3.5c;
  - sports 6.2c (fees 2.1c);
  - finance 6.3c;
  - weather 6.9c;
  - culture 4.5c;
  - economics 4.2c;
  - politics 3.8c (fees 1.0c);
  - tech 3.9c.
- In liquid markets the fee, not the spread, is the binding cost: at p ≈ 0.5 a politics round trip carries 2c of
  fees against a 1c spread.
- Liquidity-reward programmes cover 10% (1k-10k) to 52% (>=100k) of the books.
- `book_age_s` (median 82 s) is the time since the book last changed, not a latency.

**Maker fills.** Hypothetical 5-share orders join the back of the queue at both touches at the sweep receipt time
(128,742 orders, 22,293 markets).
- The `queue` rule fills when a trade goes through the price, or when the hitting taker volume at the price
  reaches the queue ahead plus 5 shares. Cancellations ahead of the order are ignored, which is conservative.
- The `touch` rule fills on any hitting trade.
- Mark: the mid of the next sweep, about 2 h after the origin.
- Adverse selection (AS) = placement half-spread minus realised spread on filled orders.
- 95% CIs come from an event-cluster bootstrap.
- 9 of 64,380 sample markets were excluded because their 500-trade page did not reach back to the origin. This
  slightly under-represents the busiest markets.

| Tier | Fill within 1 h: touch | Fill within 1 h: queue [95% CI] | Fill within 15 min: queue | Half-spread p50 | AS filled, 1 h [95% CI] | Realised spread: filled / unfilled |
|---|---|---|---|---|---|---|
| <1k | 4.1% | 1.9% [1.7, 2.0] | 0.5% | 2.0c | 3.87c [3.20, 4.66] | -1.92 / +2.48c |
| 1k-10k | 9.0% | 4.3% [3.9, 4.7] | 1.0% | 1.0c | 2.45c [2.19, 2.70] | -1.17 / +1.60c |
| 10k-100k | 8.0% | 2.9% [2.6, 3.1] | 0.8% | 0.75c | 2.04c [1.76, 2.31] | -1.23 / +1.08c |
| >=100k | 26.3% | 3.4% [2.7, 4.2] | 0.9% | 0.5c | 0.39c [-0.01, 0.65] | -0.05 / +0.45c |
| all | 8.3% | 3.1% [2.9, 3.3] | 0.8% | 1.0c | 2.38c [2.19, 2.61] | -1.23 / +1.53c |

- **Adverse selection exceeds the half-spread in every tier except >=100k.** A filled touch order loses about
  1.2c to 1.9c against a 2 h mark before any exit cost. Orders that did not fill would have earned (+0.5 to
  +2.5c) because the price moved away. This is the same pattern ECONOMIC_CONDITIONS_STUDY part B found on
  2026-04 to 2026-08 history (pmxt books).
- By category, the queue fill rate within 1 h is about 1.7% for politics, 2.3% for sports and 4.7% for crypto,
  and 15.7% for weather (AS 2.8c).
- **Fill-probability model.** An exponential hitting-volume model was rejected: it over-predicted fills for short
  queues (by up to 2x) and under-predicted them for long ones. The Lomax fit is within about 1 to 1.5 points of
  the observed rate in every queue-size quintile, for example 10k-100k observed 3.3/3.2/3.0/2.9/2.0% versus
  predicted 4.7/3.7/3.0/2.4/1.6%. Tier parameters are in `MAKER_DEFAULTS`.
- Fill probability depends mostly on whether anyone trades (`p_active`) and only weakly on queue length
  (alpha 0.20 to 0.34).

## 5. Development reassessment of F4 and F5 (taker vs maker)

F4 (flow x volatility) and F5 (flow x spread) replicated as forecasting facts (SB2-J2; development-replicated
ceiling). Their verdict, not tradable as a taker, stands and is not re-labelled. This section only shows what the
unified model says about execution alternatives, using the reported inputs:
- favourable h2 tercile, 6 h horizon;
- gross F4 +0.94c [0.65, 1.24], F5 +1.03c [0.77, 1.31];
- mean spread 2.68c (h = 1.34c), round-trip fee 0.84c (0.42c per leg);
- rebate 25% x 0.42 x 0.5 ≈ 0.05c.

| Execution | Cost / break-even gross | F4 net per fill | F5 net per fill |
|---|---|---|---|
| Taker both legs at the touch (as reported) | 3.52c | -2.58c | -2.49c |
| Taker, $100 per leg (median walk impact 10k-100k / 1k-10k) | 4.07c / 5.36c | -3.13 / -4.42c | -3.04 / -4.33c |
| Maker entry, taker exit, fill independent of signal (AS 10k-100k 2.04c) | 2.41c | -1.47c | -1.38c |
| Same with AS 1k-10k 2.45c | 2.82c | -1.88c | -1.79c |
| Maker entry, taker exit, conservative (2.81c fill conditioning) | 3.18c | -2.24c | -2.15c |
| Maker both legs, independent, both legs fill (ignores non-fill and inventory risk) | 1.30c | -0.36c | -0.27c |
| Maker both legs, conservative | 2.84c | -1.90c | -1.81c |

- **Per attempted signal**, a maker version fills only about 3 to 4% of the time within an hour, so the expected
  value per signal is about -0.04 to -0.10c. That is close to zero only because the strategy almost never trades.
- **The most optimistic maker case** (both legs passive, fills independent of the signal, no non-fill risk) needs
  1.30c. That is at the upper edge of F5's gross CI (1.31c) and above F4's (1.24c). Every realistic element makes
  it worse: signal-conditional fills, longer resting, the exit not filling, and fees on any forced exit.
- **Hold to resolution** removes the exit cost. Maker entry followed by holding costs about AS - h - rebate ≈ 0.65c
  (10k-100k), or about 0 at >=100k (AS 0.39c vs h 0.43c). However, a 6 h gross is not a hold-to-resolution gross,
  so this cannot be assessed without its own design.

**Reading.** The maker alternative lowers the break-even from about 3.5c to about 2.4-3.2c. F4/F5's roughly 1c
gross remains 1.4-2.2c short. The conclusion "forecasting facts, not routes" is unchanged.

## 6. How future cost checks should call it

```python
from astrolabe.research_lab import costs

# quote-level check (gross = mean mid-to-mid move per share in the signal direction, probability units)
chk = costs.cost_check(gross_ps, mid=mid, spread=ask - bid, category=fee_category,
                       schedule_rate=fee_schedule_rate, fees_enabled=fees_enabled,
                       liquidity=gamma_liquidity, impact_ps=impact_per_leg)
chk.cents()        # gross, taker round trip / net, resolution cost, maker per fill / per attempt, maker break-even
chk.assumptions    # rate, fee policy, fill-conditioning scenario, tier, version: report it verbatim

# book-level impact for an intended size
asks = costs.levels_from_summary(best_ask, ask_size_1, depth_ask_1c, depth_ask_5c, lift_asks=True, tick=tick)
impact_per_leg = costs.walk(asks, notional=100.0).impact_ps
```

Rules for a registered design's economic stage:
1. Use `cost_check` (or its components) with `fee policy = conservative`. Report taker net and maker net per fill
   and per attempt, with the version string `cost-model-v1`.
2. Report the maker under `conservative` as primary. The `independent` scenario is an optimistic secondary and
   must be labelled as such.
3. Price the intended size with `walk`; touch-only results must say "touch, size-unlimited".
4. Use the fee era of the data for historical windows (`cost_regimes.FEE_ERAS`); this model encodes the current
   table.
5. Liquidity rewards, taker rebates and holding rewards stay out of primaries. A maker claim needs its own
   signal-conditional fill and mark-out measurement in the registered window; `MAKER_DEFAULTS` are development priors.

## 7. Limitations

- **Depth.** Sweeps keep only the touch and depth within 1c/5c. Bands are priced at their outer edge, so walk
  costs are upper bounds for large sizes, and depth beyond 5c is unknown.
- **Fills.**
  - The fill horizon is 1 h (the next trade sample is about 2 h after the origin), so longer resting is
    extrapolation.
  - Trade samples are a stratified probability sample (liquidity x spread); tier results are unweighted
    within tier.
  - Taker trades come from the Data API (taker-only, one row per taker trade). Complementary-token matching is
    mapped to outcome 0 (a buy of outcome 1 at x is a sell of outcome 0 at 1 - x).
- **Marks.** The mark is the next 2-hourly sweep mid, so adverse selection is a 1-2 h mark-out.
- **Fill conditioning.** The 2.81c conservative value comes from one historical flow-signal study and
  transfers to other signals only as a prior.
- **Staleness.** `kappa` is an assumption.
- **Rebates.** The rebate pool haircut is an assumption, and rebate magnitudes are small (about 0.05-0.1c per fill).
- **Data window.** The calibration covers 3 days of one season (October 2026); refresh it via the qcm1 draft.

## 8. Recommendations

1. Route new economic stages through `costs.cost_check`, so that the scattered implementations in section 1 stop
   diverging. Correct `battery.fee_rate`'s unknown-category value of 0 in any future consumer (it is not
   re-run for past results).
2. Stop screening small-edge directional ideas on the full universe. A taker needs about 2.9c (>=100k) to 7c
   (1k-10k) for a $100 round trip, and a maker 2.4c or more. A candidate under about 2c gross is not worth a
   registered economic test in any tier below 100k.
3. The only cost regime below 1c is passive entry in >=100k markets held to resolution or long horizons (AS ≈
   half-spread), plus fee-free categories (geopolitics, fee-disabled markets). Ideas aimed there need fills
   measured with their own signal, inside a registered design.
4. Refresh the calibration (qcm1) when the fee table or the tick regime changes, and version the model.
