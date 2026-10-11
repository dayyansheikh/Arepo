# Arepo automated execution module: feasibility and design plan

**Date:** 2026-10-11.

**Status:** research and prototyping plan. Nothing here is implemented. No orders, no credentials, no trading-API connection. Legal, regulatory and terms-of-service questions are out of scope for this document (user decision).

**Grounding:** this plan reads the existing code and evidence as of commit `2f2c451`:
- `backend/astrolabe/domain/models.py`
- `opportunity/`
- `evaluation/execution.py`
- `evaluation/portfolio.py`
- `research_lab/forecast.py`
- `research_lab/e004.py`
- `docs/research_lab/EXPERIMENT_LEDGER.md`
- `docs/research/2026-10-11-market-structure/POLYMARKET_REGIME_TIMELINE.md`

## 0. Task and acceptance criteria

**Task.** Design the best version of an automated execution module that takes Arepo's validated insights and trades on them according to a user-set risk tolerance. Then lay out a realistic path to a working prototype that proves the loop end to end: insight → order intent → (simulated) order → fill → position → P&L.

**Acceptance criteria:**
1. Grounded in what an "insight" is in today's code, with file references.
2. Covers vision and architecture, the risk engine, signal-to-order logic, execution mechanics, the prototype path (simulator, fill and slippage models), evaluation, engineering, and the roadmap.
3. Every risk profile maps to concrete numeric limits, and the sizing method is specified with formulas.
4. Edge is always computed net of fees, spread and slippage, using the current fee regimes.
5. Evaluation metrics, benchmarks and stop criteria are declared before any paper trade.
6. Trade logs are kept physically and logically separate from frozen research cohorts.
7. It is honest about evidence: today no insight has a demonstrated edge net of costs. The design must make "do not trade" the default outcome, not a failure.
8. An independent technical review is done and folded in (§9).
9. It ends with the exact next action.

---

## 1. Vision and architecture

### 1.1 The best version

The best version is a **disciplined capital allocator for research findings**. It does not chase signals. It trades only insights that have passed Arepo's own prospective evidence gates. It sizes them by evidence quality and by the user's risk tolerance. It executes them at the lowest achievable cost, preferring resting maker orders, since spread and fees are the dominant cost. Every decision is attributed: which model, which spec hash, which risk profile, why traded, or why not.

The same engine runs in four modes with identical decision code:
- **replay:** historical books;
- **paper:** live prices, simulated fills;
- **shadow:** live books, recorded hypothetical orders, queue-aware fill inference;
- **live:** a later stage, behind gates.

The only things that differ between modes are the venue adapter and the fill source. So paper, shadow and live results are directly comparable, and the gap between *predicted*, *simulated* and *realised* edge becomes a measured quantity, not an assumption.

**What success looks like:**
- the module answers "is any Arepo insight worth trading, at what size, in which markets, for which risk tolerance?" with numbers;
- the answer is usually "not yet" or "only in narrow slices";
- when it says "yes", the claim comes with a pre-declared evaluation that a sceptic can check.

### 1.2 What an "insight" is today, and what the module needs

There are two insight types in the codebase:

| Source | Object | What it carries | Usable for sizing? |
|---|---|---|---|
| v1 product | `domain.models.Signal` (`domain/models.py:231`), scored by `opportunity/scoring.py`, phrased by `opportunity/hypothesis.py` | `direction` up/down, `strength` in [0, 1], `reliability_confidence`, `n_families`, components | **No.** Strength is a ranking score. `confidence` is explicitly a data-quality term, and the hypothesis copy says "we never claim a probability of profit or expected return". There is no expected price change, no horizon and no calibration. |
| Research lab | frozen model spec (`research_lab/model_specs/e002_reversal_v1.json`) applied by `research_lab/forecast.py::predict_frame` to a complete snapshot; logged append-only before outcomes | `dmid_hat` (expected mid change) per token, origin receipt time, an implied horizon (next capture, ~4.9h median in E002), spec hash and registration commit | **Yes**, once a predictive uncertainty and a calibration factor are attached. |

**Current evidence for the research-lab insight** (EXPERIMENT_LEDGER):
- **E002** is *Confirmed (exploratory, prospective)*:
  - R²_oos +0.026 [+0.005, +0.046];
  - realised slope −0.21 [−0.25, −0.17] against the frozen −0.33;
  - 40,436 markets, 9,967 events.
  - Only **2.0%** of forecasts exceed half the spread.
- **E004** (multi-period, with a spread-crossing check), **E005** (neg-risk arbitrage band) and **E006** (moderation by liquidity and time-to-end) are pending.

**Design consequence.** The module consumes a new, explicit contract, `Insight v1`, produced by an adapter from frozen research-lab models. The v1 `Signal` can feed the module only after a registered model maps it to an expected price change, and that model must itself pass the same gates.

```
Insight v1 (immutable record)
  insight_id          uuid
  model_id, spec_sha256, registration_commit
  validation_status   DEV | EXPLORATORY_CONFIRMED | NET_EDGE_PAPER | NET_EDGE_SHADOW | LIVE_APPROVED
  token_id, condition_id, event_id, neg_risk_group_id?
  t_origin_receipt    receipt clock of the data the forecast used
  data_age_s          now - t_origin_receipt, at decision time
  horizon_s           forecast horizon (e.g. E002: time to next capture)
  mu                  expected mid change over horizon (probability points)
  sigma               predictive s.d. of the mid change (from model residuals, by stratum)
  calib_ratio         realised/predicted slope from prospective scoring (E002: 0.21/0.33 = 0.63)
  mid_at_origin, spread_at_origin, fee_rate_bps (if known), tick_size
  features_digest     hash of the input features (audit)
```

### 1.3 Module boundaries in the existing backend

The new package `backend/astrolabe/execution/` is a sibling of `research_lab/` and `evaluation/`:

| Submodule | Responsibility | Reuses |
|---|---|---|
| `insights.py` | Adapters: frozen research-lab model on a snapshot → `Insight v1`; later, the v1 Signal adapter | `research_lab.forecast.predict_frame`, `load_spec`, `sha256_file` |
| `costs.py` | Fee (per market regime), spread, depth-walk slippage, latency penalty | Generalises `evaluation/execution.py` (replaces `DEFAULT_FEE_RATE = 0.0` with per-market fee schedules) |
| `risk.py` | Risk profiles, limit checks, kill switch, auto-halt state machine | — |
| `sizing.py` | Fractional Kelly with shrinkage, then caps | — |
| `policy.py` | Insight + costs + risk → `OrderIntent` (or a recorded no-trade reason) | — |
| `oms.py` | Order state machine, idempotent client ids, cancel/replace, timeouts | — |
| `venues/` | `VenueAdapter` interface: `SimVenue` (replay/paper), `ShadowVenue` (live book, no orders), `LiveVenue` (later stage only; not built in prototype) | `research_lab.book_sweep` for books |
| `fillmodel.py` | Taker depth-walk, maker queue model, adverse-selection bookkeeping | — |
| `ledger.py` | Positions, cash, marks, realised and unrealised P&L, attribution | Ideas from `evaluation/portfolio.py` |
| `recon.py` | Venue ↔ ledger reconciliation (live); sim self-consistency checks (paper) | — |
| `runner.py` | Scheduled loop with its own lease and deadline, separate from scan and collect | Pattern from `scheduler/tick.py` |
| `api.py` | FastAPI routes under `/exec/*` | `api/deps.py`, `accounts` (fastapi-users) |

### 1.4 Data flow

```
complete snapshot (collector, 2-hourly) ──► insights.py ──► Insight v1 (immutable, hashed)
                                                    │
live/recorded order books (CLOB /book, WS) ─────────┤
fee schedule, tick, min size (Gamma/CLOB) ──────────┤
                                                    ▼
                              policy.py: net edge = |mu·calib| − costs(order style, size)
                                                    │  (no-trade reasons recorded)
                              sizing.py ──► risk.py (pre-trade checks; may shrink or veto)
                                                    ▼
                                             OrderIntent ──► oms.py ──► VenueAdapter
                                                    ▲                        │
                                     cancel/replace │                        ▼
                                                 fills/acks ◄── SimVenue | ShadowVenue | (LiveVenue)
                                                    ▼
                                        ledger.py (positions, P&L, attribution)
                                                    ▼
                         marks from later snapshots/books ──► evaluation + monitoring + halts
```

### 1.5 Build vs buy

| Layer | Recommendation | Reason |
|---|---|---|
| Insight, risk, sizing, policy, ledger, evaluation | **Build** | These are Arepo's core value and tightly coupled to its evidence model; they are small (a few thousand lines). |
| Simulator and fill models | **Build**, with an optional spike on an existing event-driven framework (NautilusTrader reportedly has a Polymarket adapter — **verify in the spike**) | A small, deterministic, auditable simulator matched to Arepo's snapshot cadence is cheaper than adapting a general framework. A framework becomes attractive only if Stage 2 needs high-frequency live/backtest parity. |
| Order signing and submission (live stage only) | **Use the official open-source Polymarket CLOB client** (py-clob-client) behind `LiveVenue`, pinned and reviewed | Signing and order struct details changed at the CLOB V2 cutover (2026-04-28: new contracts, pUSD collateral, order struct with millisecond `timestamp`, `metadata`, `builder`). An official client tracks this. |
| Market data | **Reuse Arepo's collector and book sweep**. Add a websocket market-channel recorder in Stage 1 | Already built and tested; the recorder is needed for queue-aware shadow fills. |

### 1.6 Prototype scope (proves the loop end to end)

1. The E002 frozen reversal model (the only prospectively confirmed insight) produces `Insight v1` records on each new complete snapshot.
2. The policy computes net edge for two execution styles, taker and maker-first, under the **Balanced** profile, against the book captured at decision time.
3. `SimVenue` fills against recorded books. The ledger marks positions at the next snapshots and at resolution.
4. A daily report compares predicted edge, simulated net P&L and (Stage 1) shadow-inferred P&L, against the pre-declared metrics in §6.

The expected honest outcome is very few trades. That is the point: the prototype must show that the loop works *and* that it correctly declines to trade when costs exceed edge.

---

## 2. Risk tolerance engine

### 2.1 Profiles → concrete limits

All limits are fractions of the **account equity E**, the paper or shadow bankroll, unless stated. **Event cluster** = all markets sharing a Gamma `event_id`, and every neg-risk group counts as one cluster. **Theme cluster** = a user-visible category (e.g. "US politics", "BTC short-duration").

| Limit | Conservative | Balanced (prototype default) | Aggressive | Custom (allowed range; hard system ceiling) |
|---|---|---|---|---|
| Kelly fraction λ | 0.10 | 0.25 | 0.50 | 0.05–0.50 (ceiling 0.50) |
| Max position per market (cost basis) | 1% E | 2% E | 5% E | 0.25–5% (ceiling 5%) |
| Max per event cluster | 2% E | 5% E | 10% E | ≤ 10% |
| Max per theme cluster | 5% E | 12% E | 25% E | ≤ 25% |
| Max gross exposure | 10% E | 25% E | 50% E | ≤ 60% |
| Max open positions | 10 | 25 | 50 | ≤ 100 |
| Daily loss halt (realised + marked) | 1% E | 2% E | 4% E | 0.5–5% |
| Drawdown halt from equity high-water | 5% | 10% | 20% | ≤ 25% (then manual reset only) |
| Max order size as share of displayed depth within 2 ticks of touch | 5% | 10% | 20% | ≤ 25% |
| Max quoted spread to enter | 2¢ | 4¢ | 6¢ | ≤ 10¢ |
| Min book depth within 5¢ (each side, in USDC) | 2,000 | 500 | 200 | ≥ 100 |
| Min net edge per share (after all modelled costs) | 1.0¢ **and** ≥ 2.0 × total cost | 0.5¢ and ≥ 1.5 × cost | 0.3¢ and ≥ 1.2 × cost | ≥ 0.2¢ and ≥ 1.1 × cost |
| Allowed execution styles | maker only | maker-first, taker fallback if edge holds | maker or taker | any |
| Price band | 0.10–0.90 | 0.05–0.95 | 0.03–0.97 | within 0.02–0.98 |
| Min time to market end at entry | 24h | 6h | 3h | ≥ 3h |
| Max data age at decision | 10 min | 20 min | 30 min | ≤ 30 min |
| Minimum validation status to trade (paper/shadow) | NET_EDGE_SHADOW | EXPLORATORY_CONFIRMED | EXPLORATORY_CONFIRMED | ≥ EXPLORATORY_CONFIRMED |
| Short-duration crypto (5m/15m/1h up/down) | excluded | excluded | allowed if the model was validated on them | opt-in |

Profiles are **versioned records**: each change creates a new version, and every decision stores the profile version it used. Custom values are clamped to the system ceilings, which are code constants. Changing those constants requires a reviewed commit.

### 2.2 Position sizing: shrunk fractional Kelly, then caps

**Short-horizon mid-move trades** (the E002 type). One share bought at price a, exited around the horizon, earns ΔP per share with mean μ_net and s.d. σ. If a fraction f of equity is invested, the return per unit invested is ΔP/a. The small-edge Kelly optimum is

    f* = E[r] / Var[r] = (μ_net / a) / (σ² / a²) = μ_net · a / σ²

**Uncertainty in μ.** Kelly is extremely sensitive to errors in μ, so μ is shrunk before use:

    μ_used = κ · |mu| − cost_total(style, size)
    κ = calib_ratio × status_multiplier

- `calib_ratio` = prospective realised/predicted slope. For E002 this is 0.63.
- `status_multiplier`: EXPLORATORY_CONFIRMED 0.5, NET_EDGE_PAPER 0.6, NET_EDGE_SHADOW 0.8, LIVE_APPROVED 1.0. DEV is always 0, so it never trades.
- As an alternative, the lower confidence bound can be used. The prototype implements both and reports both, with the shrinkage form as primary.

**Final size:**

    f = clamp( λ · μ_used · a / σ²,  0,  min(per-market cap, event headroom, theme headroom, gross headroom, depth cap) )

**Worked example (Balanced).**
- **Market:** mid a = 0.50, spread 2¢, politics fee rate 0.04, so the taker fee per share at p = 0.5 is 0.04 × 0.25 = **1.0¢**.
- **Forecast:** chg_1h = +0.10, so the frozen forecast is mu = −0.033. With κ = 0.63 × 0.5 = 0.315, μ_shrunk = 1.04¢.
- **Taker round trip:** cost = 1¢ (half-spread in) + 1¢ (half-spread out) + 1¢ + 1¢ fees = 4¢. μ_used < 0, so **no trade**.
- **Maker entry, taker exit:** cost = 0 + 1¢ + 0 + 1¢ = 2¢. Still no trade.
- **Maker both ways:** cost ≈ 0 in fees and spread, but fill probability and adverse selection apply (§4).

The example shows that, with today's evidence, **execution style decides feasibility**, and Kelly mainly proportions among the rare trades that clear costs. Raw Kelly is huge for short horizons (f* = 0.01 × 0.5 / 0.05² = 2.0 for μ = 1¢, σ = 5¢), so **the caps, not Kelly, bind**. This is intended and must be shown in the UI.

**Hold-to-resolution trades** (future models that output a resolution probability q). For a YES share at ask a with fee φ(a):

    f* = (q − a − φ(a)) / (1 − a)

The same shrinkage applies, with q shrunk towards the market price: q_used = a + κ · (q − a).

**Alternatives considered:**
- *Fixed fractional* (simplest; used as a placebo benchmark).
- *Volatility targeting* (f ∝ 1/σ; ignores edge size).
- *Risk-parity across clusters* (only useful with many concurrent positions).

Fractional Kelly with shrinkage is recommended because it ties size to *both* edge and uncertainty, and reduces gracefully to "no trade".

### 2.3 Kill switch and auto-halt

**States:**

    RUNNING → HALTED_SOFT (no new entries; manage exits) → HALTED_HARD (cancel all; optional flatten per profile) → RUNNING only via manual resume with a reason

| Trigger | Level |
|---|---|
| Manual kill (UI or API) | HARD |
| Daily loss limit hit | SOFT; HARD at 1.5× the limit |
| Drawdown limit hit | HARD, plus manual reset |
| Data age > profile max for > 2 consecutive decision cycles | SOFT |
| Reconciliation mismatch (position or cash) above tolerance | HARD |
| Clock offset > 1 s (NTP check) | SOFT |
| Order reject rate > 20% over 20 orders, or ≥ 3 consecutive rejects | SOFT |
| Fill-rate or slippage anomaly: realised slippage > 3× model for 10 fills | SOFT |
| Model drift: rolling realised/predicted slope (≥ 500 forecasts) has a CI excluding the registered sign, or calib_ratio < 0.3 | SOFT, plus demotion of the insight's validation status |
| Venue status degraded or websocket heartbeat lost > 30 s (live) | HARD (rely on venue-side heartbeat auto-cancel too) |
| Fee or tick schedule changed for a held market | SOFT for that market |

Every halt writes a `risk_events` row and sends an alert through the existing `alerts/` provider.

---

## 3. Signal-to-order logic

### 3.1 Direction to instrument

- **Negative mu on token T** (expected YES price fall). Prefer buying the complementary outcome token T′ (NO) rather than "selling" T, unless the account already holds T. Polymarket positions are long-only per outcome token: short exposure is a long position in the complement.
- **Neg-risk groups.** Exposure is measured per group. A long NO on one member is economically related to longs on siblings, so the event-cluster cap applies to the group's **net** payoff vector, not the sum of notionals.

### 3.2 Expected edge net of costs (per share, probability points)

    gross   = κ · |mu|                                    (shrunk, §2.2)
    c_in    = style_in  == taker ? (ask − mid) + slip_in(size) + fee(p_in)  : −rebate_est (0 in base case)
    c_out   = style_out == taker ? (mid − bid) + slip_out(size) + fee(p_out) : 0
    c_lat   = latency penalty = E[|Δmid| over decision-to-fill delay] (estimated from the data age and taker delay)
    net     = gross − c_in − c_out − c_lat − c_adverse(style)

- **Fee.** fee(p) = feeRate · p · (1 − p) per share, using the market's own `feeSchedule`. The fee regime is per market, by creation date (regime timeline). Markets created before the fee eras have rate 0. Geopolitics has rate 0.
- **Adverse selection.** `c_adverse` for maker fills is the mean mid move against the position in the N minutes after a fill. It is estimated in Stage 1 from shadow fills. The prototype starts with a conservative prior equal to the half-spread.

**Entry rule:**
- net ≥ the profile's minimum net edge and multiple-of-cost thresholds;
- every filter passes (spread, depth, price band, time to end, data age, validation status);
- size > the market's minimum order size after caps.

### 3.3 Entry, hold and exit rules

- **Entry.**
  - Maker-first: post-only at the best price on our side, or one tick inside if the spread is ≥ 3 ticks. Time-in-force is min(horizon/3, 30 min), via GTD where available.
  - If unfilled at expiry and the profile allows taker fallback: recompute net edge at taker cost and cross only if it still clears the threshold.
- **Hold.** The target holding time is the model horizon (E002: until the next complete capture, ~5h).
  - Re-evaluate at each new snapshot. A fresh forecast in the same direction may extend the hold, but never adds beyond the caps.
  - An opposite-sign forecast that clears thresholds triggers an exit.
- **Exit.**
  - **Normal:** at horizon end, a resting maker exit at the touch for up to 30 min, then taker if the remaining position is above the min size.
  - **Take-profit:** realised move ≥ 1.5 × gross predicted move.
  - **Stop:** adverse move ≥ 3σ_horizon.
  - **Halts:** HARD halts follow the profile's flatten policy.
- **Closing and resolved markets.** No entries within the profile's minimum time to end. Positions still open at market close are held to resolution and valued at payout. A market that is closed but not yet resolved is marked at last mid with a "pending resolution" flag. **Never** trade during the resolution or dispute window.
- **Neg-risk markets.** Enter only if the group's book data is complete for all members at the decision time (E005 machinery). Group-level net exposure is capped.
- **Stale data.** Data age is measured from the receipt clock of the book used, not from the snapshot start. Snapshots span 7–12 minutes, so per-market data age is computed per row. Too stale means no decision; it is recorded as a no-trade reason.
- **Tick and dynamic tick.** Prices are rounded to the market's current tick: 0.01 normally, 0.001 above 0.96 or below 0.04, 0.0025 for some sports. A `tick_size_change` event cancels and re-prices resting orders.

### 3.4 Every decision is recorded

The module writes a `decisions` row for **every** insight considered, including the computed costs, net edge, the binding constraint, and the outcome: TRADE, or NO_TRADE with a reason code. The no-trade distribution is itself a key research output: "what fraction of forecasts were killed by fees, spread, depth or staleness?"

---

## 4. Execution mechanics

| Topic | Design |
|---|---|
| **Order types** | GTC and GTD limit (resting), FOK and FAK (immediate), post-only (guarantees maker) — all available on the CLOB per the official changelog. Prototype: post-only GTD for maker entries; FAK for taker fallback (partial fill allowed, no resting remainder). |
| **Maker vs taker** | Fees are taker-only; makers may receive rebates. Maker execution avoids spread and fees but risks non-fill and adverse selection. Default maker-first; taker only where net edge clears thresholds at taker cost. Crypto markets have a venue taker delay (currently 150 ms) that adds to latency cost. |
| **Partial fills** | Track `filled_qty`. A remainder below the min order size is cancelled. Position and exposure checks run on **open + resting** quantity, so resting orders consume limit headroom. |
| **Cancel/replace** | There is no amend: cancel, then on acknowledgement place a new order. During the gap the old order may fill, so the new order's size = target − (filled + still-resting). Replace triggers: a tick change, our price no longer at the touch for > 2 min, or the edge recomputed below threshold. |
| **Idempotency** | `client_order_id = H(decision_id, leg, attempt)` is stored *before* submission. Retries after a timeout first query by that id (live: through the order `metadata` field or venue order lookup) and never resubmit blindly. The OMS state machine is NEW → SUBMITTING → OPEN → PARTIAL → FILLED, plus CANCELING → CANCELED, REJECTED and EXPIRED. Every transition is an append-only `order_events` row. |
| **Reconciliation** | Every cycle (live) or daily (paper/shadow self-check): venue open orders, trades and positions vs ledger, plus on-chain token balances (live) vs ledger. Any mismatch beyond tolerance (1 share or 0.1% notional) is a HARD halt. Sim mode checks invariants: cash + marked positions = equity, and no negative positions. |
| **Rate limits** | A client-side token bucket per endpoint family, set to 50% of documented venue limits. Back off on 429 with jitter. Book refreshes are batched (`POST /books` as in `book_sweep.py`). |
| **Clock handling** | NTP-disciplined host. Every record carries `t_decision` (local, UTC), `t_book_receipt`, venue `timestamp` (where available) and `t_ack`/`t_fill`. Decisions use receipt clocks only. Venue timestamps are recorded for audit but never trusted for freshness: trentmkelly data showed stale exchange timestamps with p99 739 s. |
| **Disconnect safety (live stage)** | Use the venue heartbeat mechanism (HeartBeats API, 2026-01-06) so resting orders auto-cancel if the executor dies. Executor restarts are reconciliation-first. |

---

## 5. Prototype path

### Stage 0: paper trading on live prices

**Inputs:**
- each new complete snapshot from the existing collector;
- a book sweep of **candidate tokens only** (those whose insight clears a pre-filter of gross edge > 0.5¢), taken immediately after insight generation.

**Fills (SimVenue):**
- **Taker:** walk the recorded book levels for the order size (VWAP), add the fee, then apply a latency penalty. The penalty is the mid change between that sweep and the next available book for the token if within 5 min; otherwise a conservative 0.5 × spread.
- **Maker (conservative, no queue data):** a resting buy at price P fills only if a *later* recorded book shows the best ask ≤ P − 1 tick (trade-through), within the order's lifetime.

Marks come from subsequent snapshots, then resolution. **Deliverable:** a daily paper P&L and a decision log.

### Stage 1: shadow orders against the real order book

1. Add a **websocket market-channel recorder** for the shadow candidate set: `book`, `price_change`, `last_trade_price` and `tick_size_change` events, with receipt clocks. It writes into the research columnar store, with a separate prefix.
2. For every decision, record the **exact order** that would have been sent (price, size, type, TIF) at the moment of decision. Nothing is sent.
3. **Queue-aware maker fill inference:**
   - On placement, our order joins the back of the queue at price P, with queue_ahead = displayed size at P.
   - Each later `last_trade_price` print at P (or through P) reduces queue_ahead by the traded size.
   - Each `price_change` that reduces size at P is apportioned 50/50 between cancellations ahead of and behind us (a sensitivity parameter, reported at 0/50/100).
   - The order fills when queue_ahead < 0. A partial fill equals the overshoot.
4. **Adverse selection** is measured as the mid move against us at +1, +5 and +30 min after each inferred fill. It feeds `c_adverse`.
5. **Slippage calibration:** predicted taker VWAP cost vs book state at decision + 150 ms, 1 s and 5 s.

**Deliverable:** paper, shadow and predicted P&L per decision, plus calibrated cost models.

### Stage 2: live-capable (design only now; not built until gates in §6 pass and the user decides)

- **`LiveVenue`** wrapping the official CLOB client, behind a **signing firewall**: a separate process holding keys that independently enforces hard caps (max order notional, max open orders, allowed markets, daily notional) regardless of strategy code.
- **Tiny-capital pilot.** Hard equity cap set by the user, Conservative profile only, maker-only.
- **Reconciliation against venue and chain**, plus venue heartbeat, before any order.
- **Same decision code and logs as Stages 0–1.** The live-vs-shadow gap per fill is the main pilot metric.

### Simulator specification (shared by replay, paper and shadow)

- **Event-driven and deterministic** (seeded). The clock is driven by recorded events, never wall time in replay.
- **Inputs:** recorded books, deltas and prints (own captures; pmxt history for replay tests, development only), fee schedules, ticks and min sizes.
- **Pluggable fill models:**
  - `TakerDepthWalk(latency_ms)`;
  - `MakerTradeThrough` (Stage 0);
  - `MakerQueue(cancel_split)` (Stage 1).
- **Slippage model:** `slip(size) = VWAP(size) − touch` from actual levels. When only summary depth exists, a fitted power law `slip = k · (size/depth_5c)^β` per spread bucket, calibrated in Stage 1. If depth is missing, the result is **unavailable**, never zero (the existing `evaluation/execution.py` principle).
- **Outputs:** fills, fees, cost breakdown, and the per-decision ledger.

---

## 6. Evaluation (pre-declared; frozen before the first paper decision)

**Separation from research evidence:**
- Execution trade logs live in `exec_*` tables, in a **separate database file and schema** for the prototype.
- They never write to `research_*` cohort tables or `data-dumps` canonical runs, and only read them by id.
- Execution results are not research evidence and never change an experiment verdict.
- Tuning execution parameters on paper results is itself logged as trials (`trials.jsonl` pattern).

**Primary metrics** (per stage, per profile, per insight):
1. Net P&L per share (¢) and per unit of capital-days, with **event-clustered, day-blocked** confidence intervals (reusing `research_lab.power` / time-block inference).
2. **Realised/predicted edge ratio**: the slope of realised net edge on predicted net edge across trades. 1.0 = calibrated.
3. Cost decomposition: spread, fees, slippage, latency and adverse selection, as shares of gross edge.
4. Max drawdown and daily-loss breaches.
5. Fill rate and time-to-fill (maker). Implementation shortfall vs decision mid.
6. The no-trade reason distribution.

**Benchmarks:**
- **B0:** no trading (P&L 0).
- **Placebo:** same filters, sizes and holding times, with direction randomised (seeded). This separates insight value from selection and market drift.
- **Taker-only:** the same insight executed always by crossing. Isolates the execution-style contribution.
- **Predicted:** the model's own predicted net P&L.

**Stop and promotion criteria** (declared now):

| Gate | Requirement |
|---|---|
| Minimum sample before any verdict | ≥ 300 trades over ≥ 20 trading days and ≥ 100 distinct events, or 90 calendar days, whichever comes first. If fewer than 300 trades occur in 90 days, the verdict is "insufficient opportunity", which is itself a result. |
| **Stop (any stage)** | Upper 95% CI of net P&L per share < 0, **or** realised/predicted ratio upper CI < 0.3. |
| Paper → shadow | Paper net P&L CI lower bound > 0 **and** beats placebo (paired, event-clustered). Shadow runs in parallel with paper from the start because it costs nothing extra, but its verdict gates promotion. |
| Shadow → live pilot | Shadow net P&L CI lower bound > 0 with **queue-model sensitivity at cancel_split = 0%** (worst case) still > 0, **and** realised/predicted ratio CI lower bound > 0.5, **and** the user's decision (§8). |
| Live pilot continuation | Live-vs-shadow cost gap per fill within 1.5× of shadow's model. Otherwise halt and recalibrate. |

**Multiplicity.** Each (insight × profile × style) combination is a separate hypothesis. Holm correction is applied within the declared family, and the family is fixed before data.

---

## 7. Engineering

### 7.1 Data model (prototype: separate SQLite file `exec.db`; later Postgres schema `exec`)

| Table | Key columns |
|---|---|
| `exec_accounts` | id, user_id, mode (`replay`, `paper`, `shadow`, `live`), base_ccy, equity_start, created_at |
| `exec_risk_profiles` | id, user_id, version, preset, limits_json, created_at, supersedes_id |
| `exec_insights` | insight_id, model_id, spec_sha256, validation_status, token_id, condition_id, event_id, t_origin_receipt, horizon_s, mu, sigma, calib_ratio, features_digest |
| `exec_decisions` | decision_id, account_id, insight_id, profile_version, t_decision, book_ref, costs_json, net_edge, size, binding_constraint, outcome, reason_code |
| `exec_orders` | client_order_id, decision_id, venue_order_id?, side, token_id, price, qty, type, tif, state, created_at |
| `exec_order_events` | order_id, seq, state_from, state_to, t, payload_hash |
| `exec_fills` | fill_id, order_id, qty, price, fee, liquidity_flag (maker/taker), fill_model, t_fill |
| `exec_positions` | account_id, token_id, qty, avg_cost, realised_pnl, updated_at |
| `exec_marks` | account_id, token_id, t, mid, bid, ask, source |
| `exec_risk_events` | id, account_id, trigger, level, t, details_json, resolved_by |
| `exec_recon_runs` | id, account_id, t, status, diffs_json |

Everything is append-only, except `exec_positions`, which is a derived cache rebuildable from fills. Each recorded book has a content hash referenced by `book_ref`.

### 7.2 APIs (FastAPI, authenticated, per-user isolation through existing `accounts`)

- `GET/PUT /exec/profile`: read, or create a new version. Responses include a "what this means" preview: worst-case daily loss in currency, max positions, example sizing.
- `GET /exec/state`: mode, halt state, equity, exposure by cluster.
- `GET /exec/positions`, `/exec/orders`, `/exec/decisions?outcome=NO_TRADE`, `/exec/pnl?compare=paper,shadow,predicted`.
- `POST /exec/halt` with a level and reason; `POST /exec/resume` with a mandatory reason, which also writes a risk event.
- No endpoint triggers scans or heavy work. The runner is a separate scheduled worker.

### 7.3 UI

**Risk tolerance page:**
- the four preset cards, plus custom sliders clamped to ceilings;
- live preview of money at risk, the binding caps, and an example trade worked through with costs (the §2.2 example, with real numbers).

**Monitor page:**
- equity curve per mode (paper, shadow, predicted on one chart);
- exposure by event and theme cluster;
- open orders and positions;
- cost waterfall (gross edge → spread → fees → slippage → adverse selection → net);
- no-trade reasons;
- halt banner with kill button.

**Copy.** Keep Arepo's vocabulary rules: signal strength ≠ probability, and predicted edge ≠ expected profit. Paper and shadow figures are always labelled as such.

### 7.4 Observability

- **Logs:** structured, one JSON log per decision and order event.
- **Metrics:** decision latency, data age at decision, candidate count, trade count, fill rate, reject rate, slippage vs model, halt state.
- **Alerts:** through the existing `alerts/` provider on any halt or reconciliation mismatch.
- **Dead-man:** the runner writes a heartbeat; a missing heartbeat for 2 cycles raises an alert.

### 7.5 Testing strategy

- **Unit:**
  - sizing formulas;
  - fee function against the regime timeline examples;
  - tick rounding;
  - cost decomposition.
- **Property tests** (hypothesis):
  - no sequence of decisions ever breaches any cap, including headroom consumed by resting orders;
  - the ledger invariants hold;
  - idempotent resubmission never duplicates an order.
- **Simulated venue:** a fake CLOB with deterministic matching, partial fills, rejects, latency and disconnects, used to test OMS state transitions and cancel/replace races.
- **Replay tests:** recorded books from Arepo's own sweeps, plus pmxt development days. Golden-output tests pin the P&L of a fixed replay.
- **Chaos tests:** a dropped ack, a duplicate fill message, clock jump, stale book, tick change mid-order.
- **Leakage test:** the decision function receives only data with receipt time ≤ t_decision. A test feeds future-dated rows and asserts refusal, mirroring the `features.register` label guard.

### 7.6 Secrets handling design (live stage only; nothing is created now)

- Keys never enter the repo, the web API process, the frontend or CI. The repo is public.
- A dedicated **executor process** on a separate host or user account loads keys from the OS keychain or a cloud secret manager at start. The key material has no withdrawal capability where the venue model allows, with funds topped up manually.
- A **signing firewall** inside the executor validates every order against hard caps from a read-only config signed by the user. Strategy code cannot raise them.
- Credentials are rotated, and every signing request is logged as a hash and parameters, never the key.
- The live strategy configuration and executor code stay in a private location if the user prefers not to publish them (operational security).

---

## 8. Roadmap

### 8.1 Phases and effort

Effort is in focused engineering days for one developer with agent assistance.

| Phase | Content | Effort | Depends on |
|---|---|---|---|
| X0. Contracts | `Insight v1`, cost model with per-market fees (reads Gamma `feeSchedule` and tick), risk profile schema, `exec.db` schema, frozen evaluation declaration (§6) committed | 3–4 d | `research_lab.forecast`, regime timeline |
| X1. Paper loop | insights adapter (E002), policy, sizing, risk engine with halts, SimVenue (taker depth-walk plus maker trade-through), ledger, daily report, runner | 6–8 d | collector, `book_sweep` |
| X2. Shadow | WS market-channel recorder (bounded candidate set), shadow order recording, queue model, adverse-selection and slippage calibration, paper/shadow/predicted comparison | 8–12 d | X1; columnar store |
| X3. API and UI | `/exec/*` routes, risk tolerance page, monitor page | 5–7 d | X1 |
| X4. Replay harness | pmxt and own-book replay, golden tests, chaos tests | 4–6 d | X1 (parallel to X2) |
| X5. Live-capable design hardening | `LiveVenue` against the client library in a mock mode, signing firewall, reconciliation, heartbeat; **no credentials** | 8–10 d | X2 gates passed and user decision |
| X6. Live pilot | Only by user decision, with hard caps | — | X5 |

Stages X0–X4 take about 26–37 days. The first end-to-end paper P&L arrives after X0 and X1, in about 10–12 days.

### 8.2 Risks and open technical questions

| Risk or question | Likelihood and impact | Mitigation or how to resolve |
|---|---|---|
| **No insight clears costs.** E002: 2% of forecasts > half-spread; fees now apply in most categories | **High** / decisive | This is the expected outcome; the module reports it precisely (no-trade reasons). Next insights: E004 (spread crossing), E005, E006 moderators, and flow features. Maker execution is the main lever. |
| Maker adverse selection eats the spread saving | High / high | Measured in Stage 1. Abandon maker-first if `c_adverse` ≥ half-spread. |
| Snapshot latency (7–12 min scans, 2-hourly cadence) makes insights stale by execution time | Medium / high | Per-row data age. Candidate re-check against a fresh book before acting. A future targeted fast panel for candidates only. |
| Capacity is tiny (thin books) | High / medium | The depth-share cap reports capacity per insight. Capacity is an explicit output metric. |
| Fee or tick regime changes | Medium / medium | Per-market schedule read at decision time. Halt on change. |
| Overfitting execution parameters to paper results | Medium / high | §6 thresholds frozen before data. Parameter changes logged as trials. Holm within family. |
| Queue-model error in shadow | Medium / medium | Sensitivity at cancel_split 0/50/100. Promotion uses the worst case. |
| Does a framework (e.g. NautilusTrader) save effort? | Unknown | A 1-day spike in X1: check the Polymarket adapter state, V2 support and replay of Arepo books. |
| WS recorder load on the 8 GB laptop | Medium / medium | Bounded candidate set (≤ 200 tokens), RSS-capped process, columnar batching. Never run alongside multi-GB jobs (checkpoint memory rule). |
| Neg-risk group exposure netting is complex | Medium / low | The prototype excludes neg-risk markets until E005 is scored. |

### 8.3 Decisions only the user can make (with recommendations)

| # | Decision | Recommendation |
|---|---|---|
| 1 | Build X0–X1 (paper loop) now, in parallel with Phase 4 research? | **Yes**: small, reusable, and it turns "is this tradeable?" into a measured question. Keep it off the critical path of E004–E006. |
| 2 | Which insight drives the prototype | **E002 frozen reversal** (the only prospectively confirmed insight). Add E006's moderated variant and E004's result once scored. |
| 3 | Default risk profile | **Balanced** for paper and shadow (more trades, so faster learning). **Conservative** is the only profile allowed for any live pilot. |
| 4 | Paper bankroll | **1,000 USDC-equivalent** notional, a realistic capacity scale for thin books. Sizes scale linearly in reports. |
| 5 | Approve the §6 gates as frozen promotion rules | **Yes, before the first paper decision.** |
| 6 | Product boundary: AGENTS.md says Arepo "never places trades or holds exchange credentials" | Stages X0–X4 are consistent with it (no orders, no credentials). Revisit the wording only if and when you approve X5/X6. |
| 7 | Where live execution code and config live | **A separate private repository or service** for the live executor and signing firewall; the paper/shadow engine can stay in this repo. |
| 8 | Whether a live pilot ever happens, and its hard capital cap | Decide only after the shadow → live gate passes. Recommend a fixed small cap and the Conservative, maker-only profile. |

---

## 9. Independent technical review

*Section completed after review; see `REVIEW.md` in this folder.*

---

## 10. Exact next action

*Set after the review.*
