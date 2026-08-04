# Diagnosis: why directional views are rare, confidence saturates, and components are empty

Written diagnosis required by spec §3, §6, §7, produced before changing thresholds. Grounded in
the code and corroborated by an independent Sonnet diagnostic reviewer. **No thresholds were
lowered arbitrarily**; the fixes target the real causes below.

## A. Why directional views are almost always absent (§3)

The gate is `has_directional_view(direction, n_families, signal_strength)`
(`opportunity/hypothesis.py`): a view needs a resolved `direction` AND (`n_families >= 1` OR
`signal_strength >= 0.40`). Every route bottlenecks on the **same input — real, non-trivial price
movement in the trailing window**:

1. **`direction` is `None` on flat markets.** Direction comes only from the price z-score sign
   (`anomaly.py`: `direction = up/down/None from sign(zscore)`). `rolling_zscore` returns `None`
   when the window has **zero variance** (a flat price) or too little history. Polymarket outcomes
   sit unchanged at a consensus probability for long stretches, and the live path fetches price
   history at **30-minute fidelity** (`sources.py`, `interval="max", fidelity=30`), so flat
   windows — hence `direction=None` — are routine, not an edge case.
2. **The price family needs movement too.** `_price_family` fires only if a price feature
   (`unusual_return`/`movement_abnormality`/`volatility_regime`) exceeds `PRICE_CONTEXT_FLOOR=0.05`.
   A flat window clears none of these.
3. **Composite strength is capped without price context.** `composite_anomaly_score` is capped at
   `BOOK_ONLY_CEILING=0.5` unless a price feature clears the same 0.05 floor, so strength rarely
   reaches the 0.40 fallback on a calm market.
4. **The other families are live-only and trade-gated.** `trade_flow`, `wallet_concentration` and
   `timing` need ≥15-20 recent public trades AND live mode; in cached/replay board building they
   never fire, leaving `price` and `order_book` as the only possible families (and `book` needs an
   extreme imbalance ≥ 0.5).
5. **The market-detail ModelView was stricter still.** The frontend `ModelView` required
   `strength >= 0.40` with **no family credit**, so it abstained even when the backend board would
   have shown a view. This mismatch is the direct cause of "the current model view usually says
   Arepo lacks enough evidence".

**Root cause:** a data-availability bottleneck (coarse price fidelity + zero-variance flat
windows), compounded by a frontend gate that ignored evidence families.

**Fixes applied (report-consistent, not threshold-lowering):**
- **Direction net-move fallback:** when the single-step z-score is undefined (flat/zero-variance)
  but there is a genuine net price change across the window, derive `direction` from the sign of
  that net move. This uses real movement, not noise, and never fabricates a direction on a truly
  unchanged market.
- **Unify the ModelView gate** with the backend evidence rule (families OR moderate strength), so
  the market page and board agree.
- **Selective board** (§4): the Opportunity Board defaults to directional views only and states
  how selective it is ("screened N, M qualify"), so abstention is preserved for weak markets while
  the default surface shows usable views. Explore keeps all markets, including neutral ones.
- Finer price fidelity for actively-surfaced markets is recorded as a follow-up data change
  (rate-limit sensitive) in `docs/limitations.md`.

## B. Why confidence frequently displays 100% (§6)

`assess_quality` (`analytics/quality.py`) initialises `confidence = 1.0` and only ever multiplies
**down** via six data-completeness penalties (short history, wide spread, thin depth, staleness,
one-sided book, partial coverage). Any market with ≥20 observations, spread ≤ 10%, depth ≥ 100,
data ≤ 60s old and a two-sided book trips none of them and stays at **exactly 1.0 = 100%**.
Confidence therefore measured **data completeness, not model reliability**: it had no term for
evidence-family agreement, sample adequacy beyond the history floor, or historical calibration.

**Fix applied:** confidence is redesigned as a **reliability estimate** = data-quality ×
reliability factor, where the reliability factor rewards corroboration across *distinct* evidence
families and adequate sample size and is **capped below 1.0 for single-family, uncorroborated
readings**. A lone composite-anomaly reading can no longer display 100%. Confidence is still
computed only from information available at the signal timestamp (no future outcomes), now
produces meaningful variation, and is documented as a reliability estimate (not a relative quality
score) with a variation/monotonicity table in `docs/methodology.md`. Tests cover saturation,
missing data and monotonicity.

## C. Why 'Faster trading activity', 'Spread change', 'Available depth change' are empty (§7)

- **Faster trading activity (volume acceleration):** `LiveSource` and `CachedSource` hardcode
  `volumes=[]` (`sources.py`), because CLOB `/prices-history` returns only `{t, p}` points and
  Gamma exposes only cumulative `volume`/`volume24hr` scalars. `_volume_acceleration` needs a
  ≥6-point series it never receives. **Classification: not fetched / not stored.**
- **Spread change and Available depth change:** the maths exists (`analytics/backtest.py` diffs a
  trailing series of book snapshots), but `compute_token_analytics` (`enrich.py`) — the sole live
  analytics entry point — **never constructs `spread_change`/`depth_change`**, and the live path
  keeps no series of prior book snapshots to diff against. **Classification: not wired + no live
  time series.**

**Fix applied (§7 policy):** these are not reconstructable from a single live snapshot and must
never be back-filled from current books. This pass adds a **microstructure snapshot store** and an
idempotent collection function that persists timestamped `(spread, near_mid_depth,
cumulative_volume)` per token; `compute_token_analytics` computes the three change-features from
the stored series **when enough snapshots exist**, and otherwise labels them **missing** (never
silently zero) and lowers confidence via the missing-feature policy. Until the production
scheduler (§19) has accumulated snapshots, the surface rows show an explicit "collecting" state
rather than a permanently empty value, and a test proves each retained component can contribute
once a series exists. Historical reconstruction remains **price-only** and never displays these
features (labelled accordingly).
