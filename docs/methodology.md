# Methodology

This document describes every quantitative method Astrolabe computes: its definition, why
that specific formulation was chosen, its inputs, how it handles edge cases, and its
limitations. All formulas below are taken directly from the implementation in
`backend/astrolabe/analytics/`; file references are given so a reviewer can check the code
against this description.

None of the measures below constitute investment advice, a calibrated forecast, or evidence
of wrongdoing. They are transparent, explainable descriptive statistics over public order-book
and price data.

---

## 1. Implied probability

**File:** `analytics/implied.py`

**Definition:** A binary contract that pays 1 unit if "Yes" occurs trades at a price `p`,
which is treated as an approximate market-implied probability of that event. Astrolabe
clamps `p` to `[0, 1]` defensively:

```
implied_probability(price) = clamp(price, 0, 1)
```

The preferred source is the order book **midpoint** (`(best_bid + best_ask) / 2`); if no book
is available, the most recent trade price is used, and the source (`"midpoint"` vs `"last"`)
is recorded on the result.

**Why this choice:** The midpoint is less biased than either the best bid or best ask alone
(each is skewed by which side of the spread a trade cleared on) and does not require
knowledge of trade direction. Clamping guards against any dirty upstream value while
preserving the fact that a probability is bounded.

**Overround normalization** (`normalized_outcome_probabilities`): across all outcomes of one
market, the raw implied probabilities need not sum to exactly 1 – the sum reflects the book's
spread ("overround" if > 1, or an under-round if < 1). Astrolabe also reports a
**normalized** view that divides each outcome's implied probability by the sum of all
(available) outcomes' implied probabilities, removing this artifact so the outcomes sum to 1.
Missing prices are excluded from both the numerator and denominator; if the finite prices sum
to `0`, the function returns the (clamped) inputs unscaled rather than dividing by zero.

**Caveats surfaced in the product:** implied probability is a **risk-neutral, spread/fee
-contaminated estimate**, not a calibrated real-world forecast. It can be biased by
liquidity, limits to arbitrage, and sentiment, and is not adjusted for the time value of
capital or any resolution-timing effects.

---

## 2. Movement

**File:** `analytics/movement.py`

**Definition:** The additive (percentage-point) change between two observations:

```
movement(prices) = p_last - p_first
relative(prices) = (p_last - p_first) / p_first     (undefined if p_first == 0)
```

`window_movement(prices, window)` reports movement over the most recent `window` observations
(or fewer, if fewer exist). Astrolabe's UI shows a "recent movement" figure computed over the
last 4 observations (`MOVEMENT_WINDOW = 4` in `service/enrich.py`).

**Inputs:** a price series (`None`/NaN entries are dropped before differencing).

**Edge cases:** fewer than 2 finite observations yields `absolute=None, relative=None`; a
`relative` move is `None` (not `inf`) when the starting price is exactly 0.

**Limitations:** movement over a fixed observation count, not a fixed wall-clock window –
irregular sampling (e.g. thin markets with sparse updates) changes what "recent" spans in
real time.

---

## 3. Additive vs. relative/log returns – why additive is the default

**File:** `analytics/series.py`

Conventional relative returns `(p_t - p_{t-1}) / p_{t-1}` and log returns
`ln(p_t / p_{t-1})` behave poorly on a probability series bounded in `[0, 1]`: a move from
0.01 to 0.02 is a +100% "return" that says nothing meaningful about the market's actual
behaviour, and moves near the 0/1 boundary are systematically amplified or become undefined
(division by zero, log of zero).

Astrolabe therefore defaults every return-based calculation (volatility, z-score, backtest
signal) to **additive returns** (first differences, in probability points):

```
r_t = p_t - p_{t-1}
```

This keeps returns on the same natural scale as the underlying probability and keeps the
downstream z-score directly interpretable ("this move is *k* standard deviations relative to
this market's own recent moves"). Relative (`method="simple"`) and log (`method="log"`)
returns are still implemented in `series.returns()` for reference, but callers must opt in
explicitly; nothing in the product defaults to them.

**Missing-data handling:** `returns()` drops `None`/NaN prices *before* differencing
(`clean()`), so a single gap in the series does not fabricate a spurious jump across it –
the return is computed between the nearest two finite observations, not across the gap at
its original time spacing.

---

## 4. Rolling volatility

**File:** `analytics/volatility.py`

**Definition:** the sample standard deviation (`ddof=1`) of the most recent `window` return
observations:

```
volatility = std(returns[-window:], ddof=1)
```

Default `window=20`, `min_periods=5`. Optional winsorization (`winsor_limit`, symmetric
per-tail quantile clipping) can be applied to the return window before computing the
standard deviation, to reduce the influence of a single extreme prior move.

**Inputs:** a price series; internally converted to additive returns by default.

**Edge cases:** fewer than `min_periods` return observations → `value=None`,
`sufficient=False`, with `n` reporting how many were actually available. `volatility_series()`
computes this at every step (for charting) using the same window/min-periods logic, `None`
wherever insufficient history exists at that point.

**Limitations:** expressed in probability points per observation-step, not per unit time –
comparing volatility across markets with different update cadences is not directly
apples-to-apples. `ddof=1` (sample, not population) std is used throughout for consistency.

---

## 5. Rolling z-score (standardized movement)

**File:** `analytics/zscore.py`

**Definition:** answers "how unusual is the most recent move relative to this market's own
recent behaviour?"

```
z = (r_last - mean(returns[-window:])) / std(returns[-window:], ddof=1)
```

Default `window=20`, `min_periods=8`. The reference distribution (mean and std) is computed
over the trailing window **including** the most recent return, which is the standard rolling
z-score definition used here.

**Edge-case handling (explicit, by design):**

| Case | Behaviour |
|---|---|
| Fewer than `min_periods` returns | `value=None`, `reason="insufficient_history"` |
| Zero variance (flat window, `std == 0`) | `value=None`, `reason="zero_variance"` – a market that has not moved has no meaningful standardized move; Astrolabe does not emit `±inf` |
| Missing prices | Dropped pairwise before differencing (see §3) |
| Extreme prior outlier | Optional `winsor_limit` winsorizes the *reference* window so a single earlier spike does not inflate `std` and mask a genuine new move |
| Absurd magnitude from near-zero std | `clip` (default `10.0`) bounds the reported `z` to `±clip`; set `clip=None` to disable |

**Limitations:** a rolling window mixes regimes if the market's volatility genuinely shifted
partway through the window; the z-score says nothing about *why* a move occurred.

---

## 6. Midpoint, spread, relative spread, ticks

**File:** `analytics/microstructure.py` (`spread_info`)

**Definitions:**

```
midpoint          = (best_bid + best_ask) / 2                (OrderBook.midpoint property)
spread            = best_ask - best_bid
relative_spread   = spread / midpoint                         (guarded: midpoint not None/0)
spread_ticks      = spread / tick_size                        (guarded: tick_size known and > 0)
```

**Inputs:** a normalized `OrderBook` (bids sorted descending, asks ascending, best-first –
enforced at the ingestion/normalization boundary since upstream ordering is not guaranteed).

**Edge cases:** any quantity requiring `best_bid`/`best_ask` is `None` if either side of the
book is empty (a one-sided or empty book has no defined midpoint/spread).

**Limitations:** the touch (best bid/ask) can be thin – a market can show a tight spread with
almost no size actually resting there, which is why near-mid depth (§8) is reported
separately rather than relying on spread alone.

---

## 7. Order-book imbalance

**File:** `analytics/microstructure.py` (`order_book_imbalance`)

**Definition:** over the first `levels` price levels on each side of the book (default
`levels=5`):

```
imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)     range: [-1, 1]
```

`depth` is the summed contract size per side by default, or summed notional
(`price × size`) when `use_notional=True`. Positive values indicate bid-heavy (buying
pressure); negative indicate ask-heavy.

**Edge cases:** `value=None` when both sides are empty (zero denominator) rather than
dividing by zero.

**Limitations:** a snapshot measure – it says nothing about *resting time* or whether the
displayed size is likely to be pulled before it can be executed against (no information here
about order cancellation behaviour).

---

## 8. Near-mid executable depth

**File:** `analytics/microstructure.py` (`near_mid_depth`)

**Definition:** total resting size within `±band` probability points of the midpoint
(default `band=0.02`, i.e. ±2 points):

```
near_mid_depth = sum(size for levels within [mid - band, mid + band])
```

reported separately for bids and asks, plus a `total_depth`.

**Edge cases:** if the midpoint is undefined (one-sided/empty book), returns
`defined=False` with zero depths rather than guessing a band around an undefined center.

**Limitations:** explicitly a **band-limited, snapshot** measure of near-touch liquidity –
Astrolabe deliberately does not claim this represents "the market's liquidity" in any general
sense; it is only ever presented as "near-mid depth within ±X points."

---

## 9. Composite anomaly score

**File:** `analytics/anomaly.py`, `analytics/abnormality.py`

**Definition:** a `[0, 1]` screening score blending up to seven normalized, individually
visible components. As of the Signal & Historical Refinement pass the composite is
rebalanced so it is **led by price behaviour**, not by the order book:

| Component | Raw input | Saturation cap | Default weight |
|---|---|---|---|
| `unusual_return` | \|rolling z-score of the latest additive return\| | 4.0 (\|z\|=4 → fully saturated) | 0.24 |
| `movement_abnormality` | standardised magnitude of the recent multi-step move (`return_burst_score`) | 4.0 (a 4-sigma cumulative move → saturated) | 0.20 |
| `volatility_regime` | short-window return volatility vs. a longer baseline, elevated side only | 2.0 (recent volatility 3x baseline → saturated) | 0.16 |
| `volume_acceleration` | (recent incremental volume − baseline) / baseline | 3.0 (300% acceleration → saturated) | 0.12 |
| `book_imbalance` | signed order-book imbalance, first 5 levels | 1.0 (already in [-1,1]) | 0.12 |
| `spread_change` | relative spread change vs. a trailing baseline | 1.0 | 0.08 |
| `depth_change` | relative near-mid depth change vs. a trailing baseline | 1.0 | 0.08 |

The first three rows (`unusual_return`, `movement_abnormality`, `volatility_regime`) are the
**price-behaviour features** (`PRICE_FEATURES` in `analytics/anomaly.py`) and together carry
0.60 of the weight, more than double order-book imbalance's 0.12. `movement_abnormality` and
`volatility_regime` are computed in `analytics/abnormality.py`:

- `return_burst_score` (movement_abnormality) is a sustained-move detector: it takes the net
  move over the most recent `k` returns and divides by `sigma * sqrt(k)`, where `sigma` is the
  per-step return standard deviation over a trailing baseline window. This fires on a run of
  moves in one direction, not just a single jump, complementing the single-step z-score.
- `volatility_regime` is `short_vol / long_vol - 1`: recent short-window return volatility
  relative to a longer baseline. Only the elevated side counts (a calmer-than-usual market is
  clamped to 0 before weighting), since a volatility drop is not itself anomalous in the same
  sense.

Each raw value is mapped to a `[0, 1]` magnitude via `squash(x, cap) = min(1, |x| / cap)` – a
simple linear map that saturates at the documented cap, keeping outliers from dominating
the score without an unbounded input ever producing an unbounded contribution.

```
score = Σ (weight_i × normalized_i) / Σ weight_i     over components that are available
```

**Why led by price behaviour:** order-book imbalance and spread/depth change are snapshot or
short-baseline measures that can look large on very little genuine information, and on the
read-only live path spread/depth change usually have no historical series to compare against
(see below). Weighting the composite towards return-based features keeps a strong score tied
to something that actually happened to the price, not to a transient quirk of the book.

**Safeguards against the composite being dominated by the order book:**

1. **Book-only ceiling.** If no price-behaviour feature is *materially* present for a reading,
   the score is capped at `BOOK_ONLY_CEILING = 0.5`, regardless of how large `book_imbalance`
   (or spread/depth change) is. "Materially present" means a price feature whose normalized
   value clears a small floor (`PRICE_CONTEXT_FLOOR = 0.05`); a present-but-near-zero feature
   (which a calm market produces on every tick, e.g. a zero volatility regime) does not count,
   so it cannot be used to lift the ceiling. A reading built on order-book features alone, or
   on price features that are all essentially zero, can therefore never reach a "strong" score
   by itself; a genuinely strong composite requires real, measured price movement.
2. **Weight renormalization.** If a component is unavailable (e.g. no volume history, or no
   order-book time series to compute spread/depth change against), it is excluded from both
   the numerator and the weight sum – a missing input neither inflates nor deflates the score,
   it is simply absent from the average.
3. **Graceful degradation, never fabrication.** Every feature function (`return_burst_score`,
   `volatility_regime`, the z-score, imbalance, etc.) returns `None` on insufficient or
   degenerate data (too little history, a flat baseline, an empty book) rather than inventing
   a value. A component that is absent is absent; it is never estimated or defaulted to zero.
4. **Fixed, documented weights, not fitted to outcomes.** The weights and caps above are
   assumptions, coded exactly as `DEFAULT_WEIGHTS` / `DEFAULT_CAPS` in `analytics/anomaly.py`,
   chosen and documented up front rather than fit or tuned against which markets later moved.
   This avoids overfitting the composite to a small, retrospectively-known sample. A production
   deployment intending to act on this score would still need to validate them against labelled
   outcome data. Astrolabe does not claim they are optimal.

**Honest limitation: calm markets get a capped, book-only reading.** Most prediction markets
sit still for most of their life. When a market's price has not genuinely moved recently, all
three price-behaviour features are absent (there is nothing unusual to standardise), so the
composite falls back to whatever order-book features are available and is capped at 0.5 by the
book-only ceiling above. A **strong** composite score, by construction, requires genuine recent
price movement: a real return z-score, a real sustained move, or a real volatility spike. This
is intentional, not a bug: it is what stops a lopsided-but-quiet book from ever reading as a
top anomaly.

**Why spread/depth change are usually absent on the live path:** `spread_change` and
`depth_change` need a *time series* of order-book snapshots to compare "now" against a
baseline. The read-only live data path (`service/sources.py`) fetches the current book once per
request; it does not maintain a rolling order-book history, so these two components are
typically `None` in live mode and drop out of the weighted mean via renormalization. They are
retained in the model (and populated where a caller does supply a book time series) because
they are a real informative feature, not because they are expected to fire in this deployment.

**Confidence:** the `Signal.confidence` attached to a composite-anomaly signal is
`strength × quality.confidence` (§10) – i.e. a strong-looking reading with poor data quality
ranks below a strong-and-trustworthy one. `Signal.direction` is derived from the sign of the
z-score component when available (`"up"` / `"down"` / `None`).

**Limitations (stated verbatim in the product):** "Screening heuristic only. Not evidence of
insider activity; not a profit signal. Sensitive to the chosen weights, caps and windows, which
are assumptions. Spread and depth change need an order-book time series that the read-only
live path does not capture, so they are usually absent and the score leans on price and
imbalance."

---

## 9a. Historical reconstructed retrospective

**Files:** `evaluation/historical.py`, `api/routes/historical.py`
(`GET /api/historical/screen`, see `docs/API.md`).

**Purpose:** a research screen that asks "if Arepo's composite anomaly signal had been
computed at a past moment, using only what was knowable then, which markets would it have
flagged, and what actually happened to their prices afterwards?" It exists alongside, and is
kept strictly separate from, the prospective weekly cohort system in §12.

**No look-ahead:** for a chosen cut-off `as_of`, each candidate market's signal is reconstructed
using **only** the real price history up to and including that cut-off (`prefix` in
`run_historical_screen`); the later history (`suffix`) is used exclusively to measure what
happened afterwards, never to compute the signal itself. Both the pre-cutoff and post-cutoff
history are genuine recorded CLOB price history, not synthetic or invented data.

**Universe (causal selection):** the scan set is chosen by recent trading activity (24-hour
volume), a market-activity property, **never by price**. A candidate is then screened only if
its price **at the cut-off** (the last pre-cutoff point, `entry`) sat away from the extremes,
roughly between 0.1 and 0.9 (`NEAR_MID` in `historical.py`). This is deliberately judged at the
cut-off, not on today's price: a market pinned near 0 or 1 at the cut-off has no room to move
and no price-behaviour signal to reconstruct, whereas whether it later drifted to an extreme
(or is near-mid now) must not affect whether it was ever a candidate. Selection therefore uses
no post-cut-off information about the outcome, which is proven by regression tests
(`test_current_price_does_not_change_historical_selection`,
`test_pinned_at_cutoff_excluded_even_if_near_mid_or_moving_later`). Activity ordering is used
because the long-shots that top total volume and liquidity are pinned near 0/1 with no history
to reconstruct, whereas actively traded markets include the genuinely uncertain ones; its one
caveat is the mild survivorship effect noted below.

**Ranking:** signals are reconstructed for every candidate token, filtered to those meeting a
minimum strength and minimum lookback length, then ranked by strength. The result keeps the
**top 15 distinct markets** (one entry per market, its strongest outcome), not 15 outcome rows
that could double up on the same Yes/No pair.

**Scoring against real later history:** each selected entry is scored at three forward
horizons, **1 hour, 24 hours and 7 days**, using the real price at or after that point in the
recorded history (falling back to the last known price if the series ends first, never an
invented value). Direction correctness is judged at the 24-hour horizon: a signal's direction
(`"up"`/`"down"`) is compared against the real 24-hour movement.

**Provenance:** every result carries `provenance_class = "reconstructed"`
(`PROVENANCE_RECONSTRUCTED`). It is never mixed with `prospective` cohorts (§12) or the
`synthetic` demonstration; the API response and UI surface the provenance explicitly.

**Stated assumptions** (from `HistoricalScreen.assumptions`):
- The signal at the cut-off is reconstructed from only the real price history up to that
  moment, so there is no look-ahead.
- Candidates are chosen by recent trading activity, not by price, and a market is screened only
  if its price at the cut-off was away from the extremes. Selection never uses today's price or
  what happened later.
- Entry is the real price at the cut-off; forward prices are the real later history.
- Historical order books are not available, so the reconstructed signal uses price-behaviour
  features only (no order-book imbalance, spread or depth).

**Stated limitations** (from `HistoricalScreen.limitations`, and worth restating honestly
here):
- **Survivorship bias.** The universe is markets that are *still discoverable now* and that
  happen to have enough real history reaching back before the chosen cut-off. Markets that
  closed, were removed, or never accumulated that much history are structurally excluded. This
  makes the screen an illustrative research tool, not a representative sample of "every market
  that existed" at the cut-off, and not a tradable track record.
- **Price-only reconstruction.** Because historical order-book snapshots are not available,
  every reconstructed signal is necessarily a price-behaviour-only composite (no imbalance,
  spread or depth component can be computed for the past), unlike a live composite which may
  also see order-book features.
- A move in the signalled direction is not a claim of profitability; no costs, fees or slippage
  are modelled.

---

## 10. Confidence / data-quality penalty model

**File:** `analytics/quality.py`

**Definition:** confidence starts at `1.0` and is reduced by a sequence of independent,
multiplicative penalties, each recorded as a human-readable reason (`QualityAssessment.
reasons`) so a low confidence is always explainable – never a black box.

| Penalty | Trigger | Penalty factor |
|---|---|---|
| Short history | `n_history < ideal_history` (default ideal = 20 obs) | `max(0.2, n_history / ideal_history)` |
| Wide spread | `relative_spread > wide_spread_threshold` (default 0.10) | `max(0.4, 1 / (relative_spread / threshold))` |
| Thin near-mid depth | `near_mid_depth < thin_depth_floor` (default 100) | `max(0.3, near_mid_depth / thin_depth_floor)` |
| Stale data | `data_age_seconds > stale_after_seconds` (default 60s) | linear decay from `1.0` at the threshold to `0.1` at 5× the threshold |
| Incomplete (one-sided) book | book is not two-sided | flat `0.3` |
| Partial API coverage | e.g. WS down, fields missing | flat `0.7` |

Each factor is applied via `QualityAssessment.penalise(factor, reason)`, which multiplies
`confidence` by `factor` (only if `factor < 1.0`) and appends the reason string. An unknown
input (e.g. `relative_spread=None`) applies **no** penalty rather than guessing.

**Coarse band mapping**, from the final confidence:

```
confidence >= 0.75  -> GOOD
confidence >= 0.45  -> LIMITED
otherwise           -> POOR
```

(`UNAVAILABLE` is used elsewhere for genuinely absent data, not produced by this function.)

**Why multiplicative, independent penalties:** each weakness (short history, wide spread,
thin book, staleness, one-sidedness, partial coverage) is a *distinct* reason to trust a
reading less, and they can co-occur; multiplying keeps the model simple, monotonic (more
problems never increases confidence), and each factor's contribution auditable in isolation
via the recorded `reasons` list.

**Limitations:** the specific thresholds (20 obs, 10% spread, 100 units depth, 60s stale) are
assumptions calibrated by inspection, not fit to labelled data; a different market's typical
liquidity profile might warrant different floors.

---

## 11. Backtest (look-ahead-safe)

**File:** `analytics/backtest.py`, driven by `replay/player.py`

**Purpose:** measures, on the committed **synthetic** replay dataset, whether a fired
composite-anomaly signal tends to be followed by further movement in the signalled direction.
This is a **directional follow-through test, not a profitability or alpha claim** – no
transaction costs, slippage, or fees are modelled, and it is not a P&L simulation.

**Look-ahead safety (the single most important property):** for a candidate signal at frame
`i`, every component is computed using **only** frames `0..i` (see `_components_at`, which
calls `player.prices(..., upto_index=i)` etc.); the outcome is evaluated using **only**
frames `i+1..i+horizon`. Signal-generation data and evaluation data never overlap – asserted
explicitly in the loop (`assert fwd_idx > i`).

**Default parameters** (all configurable, and reported back in the result for transparency):

| Parameter | Default | Meaning |
|---|---|---|
| `strength_threshold` | 0.30 | Minimum composite anomaly strength to count as a "signal" |
| `move_threshold` | 0.02 | Minimum absolute probability-point move in the signalled direction to count as a "hit" |
| `horizon` | 5 | Frames ahead the forward price is evaluated |
| `zscore_window` | 20 | Window for the z-score component |
| `min_history` | 8 | Minimum observations before a signal can fire |

**Definitions:**

```
direction   = "up" if z > 0 else "down" if z < 0 else None
forward_move = price[i + horizon] - price[i]
followed_through = (direction_sign × forward_move) >= move_threshold
hit_rate = hits / evaluated                      (evaluated = signals with enough forward data)
false_positive_rate = (evaluated signals whose |forward_move| < move_threshold) / evaluated
```

Signals whose forward index runs past the end of the dataset are counted in
`missing_observations` and excluded from `hit_rate`/`false_positive_rate` (there is no
forward data to score them against).

**On the committed synthetic dataset**, a run with the defaults above produced
`sample_size=16`, `hit_rate=0.625`, `false_positive_rate=0.125`. This dataset (3 fictional
markets, 48 frames each, seeded/deterministic – see `replay/dataset/scenario.json`) was
constructed with planted momentum-continuation and spike-and-revert episodes specifically to
exercise the signal and backtest logic; **it is not real Polymarket data and these numbers
say nothing about live performance.**

**Stated assumptions** (from `BacktestResult.assumptions`):
- Signal fires when composite anomaly strength ≥ `strength_threshold`.
- A "hit" means price moved ≥ `move_threshold` probability points in the signalled direction
  within `horizon` frames.
- Signal generation uses frames `0..i`; evaluation uses frames `i+1..i+horizon` only.
- No transaction costs, slippage or fees are modelled; this is not a P&L simulation.

**Stated limitations** (from `BacktestResult.limitations`):
- Deterministic synthetic demo dataset – results do not generalise to live markets.
- Small sample; no survivorship correction (markets that closed are not repopulated).
- Directional "hit rate" measures follow-through only, **not** profitability or alpha.

---

## 12. Prospective evaluation

**Files:** `backend/astrolabe/evaluation/` (`constants.py`, `models.py`, `ranking.py`,
`engine.py`, `tracking.py`, `portfolio.py`, `service.py`, `cli.py`).

This is a separate system from the backtest in §11. Where §11 tests the signal against a
fixed synthetic dataset, this system records what Arepo would genuinely have selected each
week, freezes that selection, and tracks it forward against real subsequent prices and
resolutions. It exists to satisfy one rule: **Arepo must never retrospectively pick only the
signals that later performed well.**

### When prospective tracking begins

Real prospective cohorts begin at the first genuine `python -m astrolabe.evaluation.cli rank
--mode live` run on a given deployment. There is no reconstructed historical snapshot store
on this machine, so no cohort exists before that first run, and none is invented. Every
cohort row carries a `provenance_class` of `prospective`, `reconstructed` or `synthetic`
(`constants.PROVENANCE_CLASSES`); only `prospective` (and, if explicitly requested,
`reconstructed`) cohorts are aggregated into real performance statistics. `synthetic` cohorts
are never mixed into those statistics under any circumstance.

### Weekly selection and eligibility

During the current, unfrozen calendar week, Arepo keeps a provisional list of up to ten
signals (`COHORT_TARGET_SIZE = 10`). A signal is eligible for a slot only if, at the moment it
is considered (`ranking.is_eligible`):

- it has a valid entry price (see below): a signal with no usable price never qualifies,
- its data-quality band is at least `limited` (`MIN_DATA_QUALITY_RANK`, poor < limited <
  good), and
- its strength is at least `0.30` (`MIN_STRENGTH`).

Eligible signals are ranked strongest-first. If the provisional list has a free slot, an
eligible signal takes it. Once the list is full, a new eligible signal only replaces the
current *weakest* entry, and only if it is strictly stronger by the tie-break ordering below.
One market can never hold two slots in the same cohort: if a market already has an entry, a
new signal for that market only *upgrades* the existing entry in place (never adds a second
slot), which is the anti-concentration rule. Every provisional enter, replace or skip is
written to an append-only audit row (`ranking_audit`) with a reason.

### Weekly freeze

Each cohort's cut-off is **Sunday 23:59:59 UTC** (`ranking.week_bounds`; the week itself runs
Monday 00:00:00 UTC to that cut-off). Freezing a cohort:

- assigns permanent ranks to the entries as they stand at that instant,
- marks the cohort `frozen` with a `frozen_at` timestamp, and
- makes every entry immutable from that point on: the repository layer refuses any further
  replace, remove or rescore against a frozen cohort's entries, regardless of what later
  signals or prices become available.

If fewer than ten signals qualified in a week, the cohort freezes at the actual qualifying
number, and a note records why (`"Only N signals qualified this week..."`) rather than padding
the cohort to ten. Losing and unresolved entries are never deleted; they remain visible,
including as pending, indefinitely.

### Tie-breaking

Two signals never order ambiguously. `ranking.selection_key` breaks ties, in order, by:

1. strength (higher first),
2. confidence (higher first),
3. data-quality band (higher first),
4. the earlier signal-capture timestamp, then
5. a stable identifier (the snapshot reference hash, or the row id) as a final deterministic
   tie-break.

### Entry price

The entry price recorded for a selected signal is the **order-book midpoint at the signal
timestamp** when a two-sided book exists at that moment, or the last traded/implied price
otherwise. It is captured once, at selection time, alongside the best bid, best ask and
spread that were quoted then. An entry price is **never** taken from a later moment: a signal
with no usable price at the time it was considered simply cannot qualify (see eligibility,
above).

### Forward horizons

After a cohort freezes, Arepo collects forward prices at three fixed horizons measured from
the freeze timestamp: **1 hour, 24 hours and 7 days** (`FORWARD_HORIZONS`). Each
(entry, horizon) pair is recorded at most once (`forward_price_observations` is unique on
that pair), so repeated scheduler runs never duplicate an observation; a horizon is only
collected once its window has actually elapsed (`tracking.due_horizons`).

### Resolution logic

Resolution is checked against the market's own metadata: a market counts as resolved only
once it is closed (or resolved) *and* exactly one outcome sits at an extreme price (≥ 0.99).
This is a best-effort, metadata-based check, not a canonical settlement feed: see
`docs/limitations.md`. A market's resolution is recorded once per `market_id` and is never
overwritten once it has settled (`tracking.record_resolutions` skips any market whose stored
resolution is already `resolved`).

### Two evaluation views

Fixed-horizon price movement and final resolution are kept as two distinct, separately
reported verdicts, never conflated:

- **Price movement.** Evaluated at the 24-hour horizon where available (falling back to
  whichever of 7d/24h/1h is available if not). A signal counts as having "moved as expected"
  if the raw probability-point movement from the entry price is in the signalled direction; a
  move against that direction, or no forward price yet, is reported honestly as against or
  pending, never silently folded into a hit rate.
- **Final resolution.** For a resolved market, the entry is correct only if the market
  resolved to the outcome the signal selected (`resolved_token_id == entry.token_id`). Markets
  that have not resolved stay visibly pending; they are never dropped from the denominator or
  treated as either correct or incorrect.

### Portfolio assumptions

The Replay page's "Hypothetical portfolio" is a pure simulation, not a trading record, using
only information available at the signal timestamp to enter a position:

- **Fixed stake:** 100 (notional) per signal (`DEFAULT_STAKE`).
- **Fill price:** the entry crosses half the quoted spread: `fill = clamp(entry_price +
  spread/2, 0.01, 0.99)` (`SPREAD_CROSS_FRACTION = 0.5`), so the simulation never assumes a
  better fill than what was actually quoted at signal time.
- **Fees:** a configurable round-trip fee rate, default `0` (`DEFAULT_FEE_RATE`).
- **Valuation:** a resolved position pays its stake-scaled contract count if the selected
  outcome won, else zero; an unresolved position with a forward price is marked to that price;
  an unresolved position with no forward price yet is held at cost and counted as pending.

### Immutability and provenance, restated

Once a cohort is frozen, nothing about its entries (scores, prices, ranks) can change,
regardless of what happens afterwards; only *derived* rows (forward observations, resolutions,
evaluation results) are added or updated, and each of those is itself idempotent (unique per
entry/horizon or per market). Prospective, reconstructed and synthetic cohorts are always
kept in visibly distinct classes; synthetic data is illustrative only and is never mixed into
real prospective statistics. The committed synthetic demonstration cohort described in
`docs/portfolio-report.md` and shown in Replay exists purely to demonstrate that the machinery
works end-to-end (selection, freeze, forward tracking, resolution, portfolio valuation) before
any real cohort has had time to accumulate a week of history.

---

## 9b. Market-surveillance indicators and the Research Priority score

**Files:** `analytics/flow.py`, `opportunity/scoring.py`, `opportunity/service.py`.

Beyond the composite anomaly score (price and order book), Arepo computes trade-flow, wallet
and timing indicators from public read-only trades (`data-api.polymarket.com/trades`). Every
indicator is **market-relative** (judged against the market's own recent trade history),
**robust** (median / MAD / percentile, so one outlier does not define its own baseline) and
**sample-gated** (below a minimum number of trades it does not fire and its family is marked
low quality). Wallet measures are neutral aggregates only; a wallet is never labelled insider,
suspicious or manipulated.

Indicators and their evidence family:

| Indicator | Family | What it measures |
|---|---|---|
| Large relative trade | trade flow | Largest recent trade vs the market's own size distribution (robust z / percentile). |
| Contrarian (consensus-opposing) flow | trade flow | Share of aggressive notional buying a low-probability outcome or pushing against the recent move. |
| Clustered trades | trade flow | Several large same-direction trades within a short window. |
| Concentrated flow | wallet concentration | Top-1 / top-5 wallet share and HHI of recent notional. |
| Limited activity history | wallet concentration | Share of large flow from wallets active in few other markets (neutral label). |
| Late large trade | timing | A materially large trade close to the market's close. |
| Rapid repricing | price | A materially present price-behaviour feature (from the composite). |
| One-sided book | order book | Lopsided bid/ask depth (never a strong signal on its own; the book-only ceiling still applies). |

**Independent evidence families** are: price, trade flow, order book, wallet concentration,
timing and cross-market. The score and alert eligibility count *distinct families*, so several
correlated trade-flow indicators cannot masquerade as independent confirmation.

**Research Priority score** (0-100, deliberately not called expected profit): a weighted
combination of the families that fired (fixed, documented weights, never fitted to outcomes)
plus a bonus for the *number* of independent families, then shaped down for poor data quality,
thin liquidity, wide spread and stale data. A high-priority market normally requires at least
two independent families. This preserves the prior causal-selection and book-only safeguards.
No look-ahead: all indicators use only information available at the calculation time.

**Data limits (stated honestly):** most prediction markets are calm most of the time, so on a
typical day most cards score modestly and are driven by the order book and a few flow signals;
strong multi-family opportunities are genuinely rare. Historical order-book snapshots are not
retained, so spread/depth-change components are usually absent. Wallet-history coverage is
partial. See `docs/limitations.md`.

## 9c. Directional hypothesis and the strength / confidence distinction

**Confidence is a pure data-quality measure, independent of strength.** Signal *strength* is how
large and multi-faceted the anomaly is; *confidence* is how much clean evidence went into the
reading (history length, spread, order-book depth). These are deliberately separate numbers:
`confidence = quality.confidence`, and it is **not** multiplied by strength. A large anomaly on
thin data is strong-but-low-confidence; a small one on rich data is weak-but-high-confidence.
(An earlier version folded strength into confidence, which both contradicted this description and
made Research Priority quadratic in strength for single-family cards. That coupling has been
removed; `test_confidence_is_data_quality_not_strength` guards it.)

**Directional hypothesis (`opportunity/hypothesis.py`).** Each surface leads with one cautious
sentence generated only from computed evidence. A directional view is asserted only when a
direction is resolved AND either at least one independent evidence family fired or the signal is
at least moderately strong (>= 0.40). Otherwise Arepo states plainly that there is not enough
independent evidence to favour a direction. The sentence is phrased in terms of upward or
downward *repricing pressure* on the named outcome; it never claims a probability of profit or
certainty. `test_hypothesis.py` covers the sufficient/insufficient cases and the no-profit copy.

**Evidence families.** Five independent families are produced: price, trade flow, order book,
wallet concentration and trade timing. A previously declared sixth "cross-market" family was
never implemented and has been removed so the family count matches what the code computes. High
priority requires at least two distinct families, so correlated indicators within one family
cannot masquerade as independent confirmation.

## 9d. Alert eligibility (per user)

An alert is only ever sent when a user-independent quality floor holds (enough families,
adequate strength, acceptable data quality and liquidity) AND the individual user's opted-in
preferences match (minimum Research Priority, minimum confidence, preferred categories, and any
short-term-only / maximum-time-to-close preference), the user's email is verified, and alerts
are neither paused nor unsubscribed. A user's preferences can tighten but never lower the quality
floor. Per-user, per-market deduplication and a cooldown prevent repeat alerts. See
`docs/alert-configuration.md` and `test_user_alerts.py`.
