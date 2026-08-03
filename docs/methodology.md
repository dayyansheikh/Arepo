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

**File:** `analytics/anomaly.py`

**Definition:** a `[0, 1]` screening score blending up to five normalized, individually
visible components:

| Component | Raw input | Saturation cap | Default weight |
|---|---|---|---|
| `unusual_return` | \|rolling z-score of additive returns\| | 4.0 (\|z\|=4 → fully saturated) | 0.35 |
| `volume_acceleration` | (recent incremental volume − baseline) / baseline | 3.0 (300% acceleration → saturated) | 0.20 |
| `book_imbalance` | signed order-book imbalance, first 5 levels | 1.0 (already in [-1,1]) | 0.15 |
| `spread_change` | relative spread change vs. a trailing baseline | 1.0 | 0.15 |
| `depth_change` | relative near-mid depth change vs. a trailing baseline | 1.0 | 0.15 |

Each raw value is mapped to a `[0, 1]` magnitude via `squash(x, cap) = min(1, |x| / cap)` – a
simple linear map that saturates at the documented cap, keeping outliers from dominating
the score without an unbounded input ever producing an unbounded contribution.

```
score = Σ (weight_i × normalized_i) / Σ weight_i     over components that are available
```

**Weight renormalization:** if a component is unavailable (e.g. no volume history in live
mode), it is simply excluded from both the numerator and the weight sum – a missing input
neither inflates nor deflates the score, it is absent from the average.

**These weights and caps are assumptions, not empirically fit values.** They are documented
here exactly as coded in `DEFAULT_WEIGHTS` / `DEFAULT_CAPS` in `analytics/anomaly.py`, and a
production deployment intending to act on this score would need to re-derive them from
labelled outcome data. Astrolabe does not claim they are optimal.

**Confidence:** the `Signal.confidence` attached to a composite-anomaly signal is
`strength × quality.confidence` (§10) – i.e. a strong-looking reading with poor data quality
ranks below a strong-and-trustworthy one. `Signal.direction` is derived from the sign of the
z-score component when available (`"up"` / `"down"` / `None`).

**Limitations (stated verbatim in the product):** "Screening heuristic only. Not evidence of
insider activity; not a profit signal. Sensitive to the chosen weights, caps and windows,
which are assumptions."

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
