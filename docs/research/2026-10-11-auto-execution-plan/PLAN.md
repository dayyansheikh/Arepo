# Arepo automated trading engine: feasibility and design plan

**Date:** 2026-10-11. Revision 2, restructured after user direction and the independent technical review.

**Status:** research and prototyping plan; nothing is implemented. No orders are placed, no credentials are requested and no trading API is connected. Legal, regulatory and terms-of-service questions are out of scope (user decision).

**Focus (user direction).** The *machinery*: a system that can actually trade for a user through venue APIs, under a user-set risk tolerance. What it trades on is a pluggable strategy input. Arepo's research insights are one plug-in, and simple test strategies exercise the engine before any insight is good enough.

**Companion files in this folder:**
- `API_RESEARCH.md`: cited, current facts on Polymarket's trading API, wallets, settlement and SDKs, plus Kalshi.
- `REVIEW.md`: the independent technical review of revision 1.
- `PLAN.md` §9: how each review finding was handled.

**Code grounding** (at commit `efb4fa7`):
- `backend/astrolabe/domain/models.py`, `opportunity/*`;
- `evaluation/execution.py`, `evaluation/portfolio.py`, `evaluation/constants.py`;
- `research_lab/forecast.py`, `research_lab/book_sweep.py`;
- `scheduler/tick.py`, `accounts/*`, `alerts/*`.

## 0. Task and acceptance criteria

**Task.** Design the best version of an automated trading engine for Arepo, then a realistic path to a working prototype. The engine connects to venue APIs, authenticates, turns strategy intents into correctly formed orders, manages their whole lifecycle through on-chain settlement and redemption, keeps an exact ledger, and enforces the user's risk tolerance with hard safety controls.

**Acceptance criteria:**
1. Covers architecture; the risk engine; intent-to-order; execution mechanics; the prototype path (simulator, fill and slippage models); evaluation; engineering; and the roadmap with the user's decisions.
2. Execution mechanics reflect the **current** Polymarket API, which is mid-migration between two exchange generations, with citations in `API_RESEARCH.md`.
3. The engine is strategy-agnostic: one interface, several strategies, identical code in every mode.
4. Safety is designed in: idempotency, a settlement-aware ledger, a dead-man switch, reconciliation, a signing firewall and least-privilege keys.
5. A no-credentials build path reaches "live-capable": everything except funded keys and the switch.
6. The review is folded in (§9), and the plan ends with the exact next action (§10).

---

## 1. Vision and architecture

### 1.1 The best version

Arepo Execution is a **venue-agnostic, strategy-agnostic trading engine**:
- A user chooses a risk profile and a set of strategies, then funds a restricted wallet.
- The engine runs unattended. It turns strategy intents into orders, executes them cost-efficiently (maker-first where sensible), and tracks every order and fill to on-chain confirmation.
- It redeems resolved positions automatically, reconciles continuously against the venue and the chain, and stops itself the moment anything looks wrong.

**Every action is explained:**
- which strategy asked;
- what the risk engine allowed;
- what was sent, what happened, and what it cost.

**Four modes share one code path.** Only the venue adapter and the fill source differ:

| Mode | Market data | Orders | Fills |
|---|---|---|---|
| `replay` | recorded books and deltas | simulated | simulated fill models |
| `paper` | live (REST and websocket) | simulated | simulated fill models |
| `shadow` | live | fully constructed **and signed with a throwaway unfunded key**, never sent | queue-aware inference from the live stream |
| `live` | live | sent to the venue | venue and chain |

**The moat** is not order routing. It is the combination of three things:
- strict *evidence gates* deciding which strategies may trade (Arepo's research discipline);
- a *settlement-exact ledger*;
- *measured* paper → shadow → live gaps.

### 1.2 Components and boundaries

The new package is `backend/astrolabe/execution/`. It runs as its own worker process with its own lease and deadline, separate from the scan and collect workflows. It is never triggered by browser requests.

```
                ┌──────────────── Strategy plug-ins ────────────────┐
                │ ManualIntent │ RuleBased(test) │ ArepoInsight(E00x)│
                └───────────────┬───────────────────────────────────┘
                                │ TradeIntent (target exposure, urgency, limit price band, horizon, rationale)
 Market data ──► MarketState ───┤
 (REST /book, WS market,        ▼
  Gamma meta, fee schedule) ┌────────┐   ┌──────────┐   ┌──────────────┐   ┌───────────────┐
                            │ Risk   │──►│ Order    │──►│ OMS (state   │──►│ VenueAdapter  │──► Sim | Shadow | Polymarket | Kalshi
                            │ engine │   │ builder  │   │ machine,     │   │ (+ Signer via │
                            └────────┘   └──────────┘   │ idempotency) │   │  firewall)    │
                                ▲                       └──────┬───────┘   └──────┬────────┘
                                │                              │ acks/fills        │ user WS, REST, chain
                         ┌──────┴──────┐   ┌───────────────┐   ▼                   ▼
                         │ Halt / kill │◄──│ Reconciler    │◄──┴─ Settlement-aware Ledger ◄─┘
                         └─────────────┘   └───────────────┘        │ positions, cash, P&L, fees
                                                                    ▼
                                         Redemption & conversion ── Ops: alerts, metrics, UI, API
```

| Submodule | Responsibility |
|---|---|
| `strategies/` | `Strategy` protocol: `on_market_state(state) -> list[TradeIntent]`. Built-ins: `ManualIntent` (UI- or API-entered intents, for testing the machinery), `RuleBased` (deterministic test rules, e.g. "post-only bid one tick behind touch on market X, size 5"), `ArepoInsight` (adapter over frozen research-lab model specs; §3.4). |
| `market_state.py` | Per-token book, tick, min size, `neg_risk`, market `version`, fee rate, data age (receipt clock), market status (open, paused, closed, resolved, disputed). |
| `risk.py` | Profiles, pre-trade checks, exposure headroom (counting resting orders), halts. |
| `order_builder.py` | Intent → concrete order(s): token choice, price rounded to tick, size rounding, order type and TIF, version-specific fields. |
| `oms.py` | Order and trade state machines, sign-once idempotency, cancel/replace, batching, retry policy. |
| `venues/` | `VenueAdapter` interface. `SimVenue`, `ShadowVenue`, `PolymarketVenue` (via the official unified SDK), `KalshiVenue` (later). |
| `signer/` | A separate process holding key material, which enforces the firewall caps (§7.6). |
| `ledger.py` | Provisional and final fills, positions, cash, fees, rebates, marks, P&L. |
| `recon.py` | Ledger ↔ venue ↔ chain reconciliation. |
| `redeem.py` | Detect resolution; redeem, merge or convert per position system. |
| `fillmodel.py`, `sim.py` | Simulator and fill models (§5). |
| `api.py`, `ops.py` | `/exec/*` routes, metrics, alerts (reuses `alerts/`), heartbeat. |

### 1.3 Build vs buy

| Layer | Decision | Why |
|---|---|---|
| Signing, order structs, auth headers | **Buy**: official unified Python SDK `polymarket-client` (≥0.12.0, Python ≥3.11, matching the backend), wrapped by `PolymarketVenue`. *Not* `py-clob-client`, which is V1-only and no longer works. | The order structs and EIP-712 domains changed twice in 2026 (CLOB V2 on 04-28; Protocol V2 / ExchangeV3 canary from 10-05). Tracking that ourselves is high-risk, low-value work. |
| OMS, risk, ledger, recon, redemption, strategies, simulator | **Build** | This is the product. Each part is small, and each must encode Arepo's safety and evidence rules exactly. |
| Full framework (NautilusTrader Polymarket adapter, V2; documented in nightly builds) | **Spike, don't adopt yet** | It would give backtest/live parity and a mature OMS, but its stable V2 status is unconfirmed, it is heavy for an 8 GB host, and it duplicates our ledger and evidence model. Revisit if Stage 2 needs sub-second strategies. |
| Unified multi-venue SDKs (pmxt, ccxt prediction) | **No** (for now) | Their V2/pUSD support is unverified, and they add an abstraction layer over the critical signing path. |

### 1.4 Prototype that proves the loop end to end

1. `RuleBased` and `ManualIntent` strategies generate intents on a small allow-list of liquid markets.
2. The full engine runs in **paper** and **shadow** simultaneously:
   - risk → builder → OMS → `SimVenue` (paper fills);
   - and `ShadowVenue`: the same orders are fully built and **signed** with a throwaway unfunded local key, persisted, never sent, and their fills inferred from the live stream.
3. The ledger, recon (self-consistency), redemption simulation, halts, API and a minimal monitor UI all operate.
4. `PolymarketVenue` is complete behind a **mock venue** that implements the documented endpoint, websocket and error behaviours, and passes contract tests. Going live is then "fund wallet + approvals + session key + flip mode", gated by §6 and the user (§8).

---

## 2. Risk tolerance engine

### 2.1 Profiles → concrete limits

Limits are fractions of account equity E, marked at **liquidation value**: bid minus the taker fee for longs (review M7). Mid-marks are shown as secondary.

- **Event cluster:** all markets with the same `event_id`. A neg-risk group is one cluster.
- **Theme cluster:** a user-visible category.
- **Depth unit:** shares within **1¢ of touch** (review L3).

| Limit | Conservative | Balanced | Aggressive | Custom (hard ceiling in code) |
|---|---|---|---|---|
| Max position per market (cost basis) | 1% E | 2% E | 5% E | ≤ 5% |
| Max per event cluster | 2% | 5% | 10% | ≤ 10% |
| Max per theme | 5% | 12% | 25% | ≤ 25% |
| Max gross exposure (positions + resting orders) | 10% | 25% | 50% | ≤ 60% |
| Max open positions / resting orders | 10 / 20 | 25 / 50 | 50 / 100 | ≤ 100 / 200 |
| Daily loss: soft halt / hard halt | 1% / 1.5% | 2% / 3% | 4% / 6% | ≤ 5% / 7.5% |
| Drawdown from high-water (hard halt, manual reset) | 5% | 10% | 20% | ≤ 25% |
| Max order size as share of depth within 1¢ | 5% | 10% | 20% | ≤ 25% |
| Max quoted spread to enter | 2¢ | 4¢ | 6¢ | ≤ 10¢ |
| Min depth within 1¢, each side (shares) | 2,000 | 500 | 200 | ≥ 100 |
| Execution styles | post-only maker | maker-first, taker fallback | maker or taker | any |
| Price band | 0.10–0.90 | 0.05–0.95 | 0.03–0.97 | within 0.02–0.98 |
| Min time to market end at entry | 24h | 6h | 3h | ≥ 3h |
| Max data age at decision | 2 min | 5 min | 10 min | ≤ 10 min |
| Max notional per order / per day | 1% / 10% E | 2% / 25% E | 5% / 50% E | ≤ 5% / 60% |
| Strategy evidence status allowed (live) | NET_EDGE_SHADOW | NET_EDGE_SHADOW | NET_EDGE_PAPER | ≥ NET_EDGE_PAPER |
| Short-duration crypto markets | excluded | excluded | allowed | opt-in |

**Rules:**
- Profiles are versioned records. Every decision stores the version it used.
- Custom values are clamped to code ceilings, and the signer firewall enforces its own, independent ceilings (§7.6).
- After all caps, an order below the market's `min_order_size` is dropped and recorded as a no-trade reason, never rounded up.

### 2.2 Sizing

**Default (prototype): caps-first.** `size = min(per-market headroom, cluster headroom, gross headroom, depth cap, per-order notional cap)`, scaled by the strategy's requested fraction in [0, 1]. The review (L4) showed that for short-horizon strategies, Kelly with realistic σ always exceeds the caps, so Kelly is logged as a diagnostic and not used to size.

**Optional (strategies that supply calibrated μ and σ).** Shrunk fractional Kelly. All prices are anchored on the book mid at decision time, m_book (review H1).
- **Mid-move trades:** f* = μ_net · a / σ², with λ ∈ {0.10, 0.25, 0.50} by profile.
- **Hold-to-resolution trades:** with cost per share c = a + fee(a), f* = (q_used − c)/(1 − c), where q_used = m_book + κ·(q − m_book). Shrinkage is towards the mid, not the ask (review M3).

Then the caps apply. κ comes from the strategy's evidence record (e.g. a prospective calibration ratio with a CI-bound alternative). It is never hand-tuned.

### 2.3 Kill switch, halts and restricted venue modes

**States:**

    RUNNING → SOFT_HALT (no new entries; exits allowed) → HARD_HALT (cancel-all, then optional flatten per profile) → manual RESUME with reason

| Trigger | Action |
|---|---|
| Manual kill (UI, API or CLI) | HARD |
| Daily loss soft or hard threshold; drawdown limit | SOFT / HARD / HARD + manual reset |
| Reconciliation mismatch beyond 1 share or 0.1% notional | HARD |
| Heartbeat to venue lost, or signer unreachable | HARD (the venue auto-cancels resting orders within ~10–15 s anyway) |
| Data age above the limit for 2 cycles; no fresh market state | SOFT |
| Clock offset > 1 s (NTP) | SOFT |
| Rejects > 20% of the last 20 orders, or ≥ 3 consecutive | SOFT |
| Realised slippage > 3× model over 10 fills | SOFT |
| Trade settlement FAILED | SOFT, plus recon |
| Venue 503 "trading disabled" or cancel-only | SOFT (pause new orders) |
| HTTP 425 (engine restart) | back off per `Retry-After`; treat the next 2 min as post-only |
| Account closed-only status (`/auth/ban-status/closed-only`) | SOFT (reduce-only) |
| Held market paused, closed, disputed, or fee or tick schedule changed | SOFT for that market |
| Strategy drift monitor (strategy-specific) fires | Disable that strategy |

Every halt writes `exec_risk_events`, sends an alert, and is shown in the UI.

---

## 3. Intent → order

### 3.1 The strategy contract

```
TradeIntent
  intent_id, strategy_id, strategy_version, evidence_status
  market (condition_id / position system), outcome, direction (increase|decrease exposure)
  target_fraction (0..1 of allowed headroom) | target_shares
  urgency: PASSIVE (maker only) | NORMAL (maker-first, taker fallback) | URGENT (taker)
  limit_band: worst acceptable price (absolute)
  horizon_s (for TIF and exit timing), optional mu/sigma/q (+ basis: mid|touch)
  rationale (text + feature digest), t_basis (receipt time of the data used)
```

Strategies only express intent. **They never see keys, never call the venue, and cannot bypass risk.**

### 3.2 Order construction (builder)

1. **Refresh market metadata** from `GET /book` immediately before building: `tick_size`, `min_order_size`, `neg_risk`, `version`, plus the market fee rate. Version branching:
   - **CTF (v1 market):** `clobTokenIds`, EIP-712 domain "2", exchange `0xE111…` (or `0xe222…` if `neg_risk`).
   - **Protocol V2 market:** `positionIds`, domain "3", ExchangeV3.
2. **Choose the token.** Exposure *against* an outcome means buying the complementary token, since positions are long-only. Decreasing exposure sells held shares; never sell what isn't held.
3. **Set the price.**
   - PASSIVE: best bid (or best ask for a sell), or one tick inside if the spread is ≥ 3 ticks.
   - URGENT: the marketable price capped at `limit_band`.
   - Round to the tick, respecting the dynamic tick (0.01 normally, 0.001 near the extremes; listed ticks run from 0.1 to 0.0001; 0.0025 is World Cup only).
4. **Set the size.** GTC/GTD BUY is in **shares**; FOK/FAK BUY is in **collateral, pre-fee**, so the cash check adds the fee (review L1). Size has 2 decimals, and amounts are 6-decimal integers.
5. **Set type and TIF:**
   - PASSIVE: post-only GTD, expiration = now + 60 s + max(180 s, horizon-derived life). GTD expires 60 s early and needs ≥ 3 min.
   - NORMAL: post-only GTD, then on expiry re-evaluate and use FAK at `limit_band`.
   - URGENT: FAK, or FOK if all-or-nothing.
6. **Cost check (generic).** For any intent that carries μ or q, net = gross(anchored on m_book) − half-spread × (taker legs) − fee × (taker legs) − slippage − latency − adverse selection (maker). If net is below the profile's threshold: no trade, with the reason recorded. Fees use `fee = C·feeRate·p(1−p)` (taker only; builder fee if any). Intents without μ (manual, test) skip the edge check but never the risk checks.

### 3.3 Lifecycle rules

- **Exits** come from the strategy (horizon end, reversal, stop) or from risk (halts). The default exit is PASSIVE for up to 30 min, then NORMAL.
- **Closing and resolved markets:**
  - No entries inside the profile's minimum time to end.
  - At close, positions are held to resolution.
  - After resolution, `redeem.py` redeems: via the Router for Protocol V2, via the collateral adapters for CTF.
  - Disputed or paused markets are frozen with no new orders.
- **Neg-risk:**
  - Exposure is netted per group.
  - Placeholder or "Other" outcomes are never traded.
  - Conversion (NO → YES-of-others) is a deliberate operation that needs a strategy request and the user's profile permission.
- **Stale data:** every decision checks the per-token data age against the profile, using the receipt clock and never the venue timestamp.

### 3.4 `ArepoInsight` strategy (one plug-in; details deferred)

This adapter wraps frozen research-lab specs: today E002's reversal (`research_lab/forecast.py`, `model_specs/e002_reversal_v1.json`). It emits intents with μ, σ and `basis="mid"`. The v1 product `Signal` (`domain/models.py:231`) is a ranking score, not an expected return, so it cannot be a sizing input without a registered mapping model.

The review's strategy-level findings (H1 re-anchoring, H2 horizon and σ consistency, H3 expected trade counts) are requirements for this adapter, recorded in §9. They do not block the engine.

---

## 4. Execution mechanics (Polymarket; facts and citations in `API_RESEARCH.md`)

### 4.1 Accounts, wallets, keys

**Recommended custody model: Deposit Wallet (signature type 3) plus a CLOB-scoped session key.**
- The session key **cannot withdraw**, expires in at most 180 days, is revocable (revoking cancels its open orders), and can be scoped to `CLOB`.
- The owner key stays offline.
- Setting up session keys needs a builder API key enabled for session-key management.

**Alternatives:**
- An EOA (type 0) needs allowlisting plus POL for gas. Not recommended.
- Proxy and Safe (types 1 and 2) are legacy.

**Auth layers:**
- **L1:** EIP-712 `ClobAuth`, to create or derive API credentials.
- **L2:** HMAC headers on every trading call, signature over `ts + method + path + body`.
- **One credential set per executor instance.** The heartbeat cancels *all* orders on that credential set (review L2).

**Gas:** Deposit, Safe and Proxy wallets are gasless via the Relayer. Relayer transactions are tracked to `STATE_CONFIRMED` or `STATE_FAILED`.

### 4.2 Preflight (fail closed)

At startup and every N minutes, the engine checks the following and refuses to trade if any is missing:
1. pUSD balance.
2. pUSD allowances to the Standard Exchange, the NegRisk Exchange and ExchangeV3.
3. CTF `setApprovalForAll` to both CTF exchanges; PositionManager approval to ExchangeV3.
4. Allowance cache sync (`/balance-allowance/update` per asset type).
5. Session key validity and remaining lifetime (warn at < 14 days).
6. Closed-only status.
7. Clock sync.

USDC.e → pUSD wrapping uses the Collateral Onramp. It is a manual, user-initiated funding step, never automated by the engine.

### 4.3 Order submission and idempotency (review M6)

- **No client order id exists, and uniqueness comes from salt + ms timestamp.** So the engine **signs once** and persists the full signed payload, its hash, salt and timestamp *before* POST.
- **On timeout or unknown outcome:**
  1. Query `/data/orders` and `/data/trades` for the token, matching on (side, price, size, timestamp/salt).
  2. If not found after the reconciliation window, resubmit the **identical signed bytes**.
  3. **Never re-sign a retry.**
- **Batches:** `POST /orders` takes up to 15 orders. Responses may carry per-order errors inside a 200, so each element is parsed individually.
- **`metadata` (bytes32):** carries an attribution hash for our own audit. It is not used for lookup, because open orders don't expose it.

### 4.4 Order and trade state machines

**Order states:**

    NEW → SIGNED → SUBMITTING → {LIVE | DELAYED | MATCHED | UNMATCHED | REJECTED}
    LIVE → PARTIAL → FILLED;  LIVE/PARTIAL → CANCELING → CANCELED;  GTD → EXPIRED

- `DELAYED` (crypto taker delay, currently 150 ms) **cannot be cancelled**. Risk counts it as filled-in-full until resolved.
- **Cancel/replace:** there is no amend. Cancel, wait for the ack, then place the new order. The new size = target − (filled + still-resting); this handles fills during the gap.

**Trade (fill) states,** keyed by `tradeID`:

    MATCHED_NOT_BROADCASTED → MATCHED → MINED → CONFIRMED (final)
                                   ↘ RETRYING ↺          ↘ FAILED (final: never happened)

**The ledger books provisionally at MATCHED and finally at CONFIRMED.** FAILED reverses the provisional entry and triggers recon plus a SOFT halt. Exposure and risk use provisional fills; P&L reports split provisional and final.

### 4.5 Real-time and reconciliation

**User websocket** (orders and trades): auth with L2 credentials, PING every 10 s.
- It has **no sequence numbers and no replay**. On every (re)connect, rebuild state from REST (`/data/orders`, `/data/trades`, positions) and only then apply stream events.
- The stream is advisory; REST plus chain is authoritative.

**Market websocket:** `book`, `price_change`, `last_trade_price`, `tick_size_change`, plus `best_bid_ask`, `market_resolved` and `new_market` with custom features. Resync from REST `/book` on gaps or hash divergence.

**Heartbeat dead-man switch:** `POST /v1/heartbeats` every 5 s, from a **separate lightweight process**. A missed beat leads to venue-side cancel-all within about 10–15 s. On shutdown the engine also sends an explicit `cancel-all`.

**Reconcile** (every cycle and on reconnect): open orders, trades by status, Data API v2 positions, and on-chain balances (pUSD, CTF/PositionManager) against the ledger.
- Redemptions remove balances without a trade, so they are booked from `redeem.py` events before reconciling.
- A mismatch → HARD halt.

### 4.6 Rate limits, restarts, delays

**Rate limits** are per-IP (Cloudflare) and **throttle by queueing** rather than rejecting. So the engine measures request latency and treats rising latency as back-pressure. Client token buckets are set at ≤ 25% of documented limits:
- `POST /order` 5,000 per 10 s;
- `POST /orders` 2,000 per 10 s;
- `/data/orders` 500 per 10 s;
- `/book` 1,500 per 10 s.

**Batch caps:** 15 orders per POST; cancel batches up to 1,000 ids (the docs conflict; assume 1,000).

**Engine restarts:**
- HTTP 425 with `Retry-After`, followed by a 2-minute post-only window (503 `post_only_mode`).
- Announced about 2 days ahead on Polymarket channels; the ops calendar can pre-pause.

**Crypto taker delay:** 150 ms. It is part of the latency cost and of the DELAYED state.

### 4.7 Post-trade

- **Fees:** charged at match, taker only. BUY fees are added to spend; SELL fees are deducted from proceeds. Rounded to 5 dp. Recorded per fill.
- **Maker rebates:** paid daily in pUSD, pro rata, $1 minimum. There is no query API, so they are booked from wallet inflows tagged by recon.
- **Redemption:**
  - Router `redeem(cid, outcomeIndex, amt)` for Protocol V2;
  - adapter `redeemPositions` for CTF (the v1 neg-risk adapter is deprecated);
  - no deadline, batched daily.
  - An optional AutoRedeemer operator approval is a user decision.
- **Merge** of complete sets frees collateral. It is an opportunistic, risk-reducing action, available in all profiles.

### 4.8 Second venue: Kalshi (later)

`KalshiVenue` behind the same interface:
- **Auth:** API key ID plus RSA-PSS or Ed25519 request signing.
- **Demo environment:** `external-api.demo.kalshi.co`.
- **Orders:** native `client_order_id` (simplifies idempotency), `post_only`, `reduce_only`, self-trade prevention, `cancel_order_on_pause`.

Kalshi's demo is the only **real sandbox** found, which makes it the cheapest place to prove the live adapter path end to end without funds at risk. That is useful even before any Kalshi strategy exists.

---

## 5. Prototype path

### Stage 0: paper (live data, simulated venue)

**Data:**
- A candidate-only **book poller**: raw levels to 5¢, every 1–2 min for allow-listed and active tokens (review M4). Existing `book_sweep` keeps only summaries, so it cannot support depth walks.
- Plus the market websocket for the same bounded set (≤ 200 tokens, RSS-capped process).
- Output root `data-dumps/exec/`, never under `research_lab/snapshots/` (review M8). Network jobs run only between research snapshots.

**`SimVenue` fill models:**
- `TakerDepthWalk(latency_ms)`: VWAP across levels at decision time + latency, plus the fee. The latency penalty is the measured mid change over the latency window from the stream.
- `MakerTradeThrough`: fills only when a later print or book state crosses our price.

**Exit criteria (engineering):**
- 14 consecutive days with zero ledger invariant violations;
- every order reaches a terminal state;
- halts fire correctly in injected-fault drills.

### Stage 1: shadow (real books, signed-but-unsent orders)

- `ShadowVenue` builds and **signs** every order with a throwaway unfunded local key (it proves signing, domain and version branching) and persists the bytes. Nothing is sent.
- **`MakerQueue` model (review M1):**
  - Our order joins the back of the queue; queue_ahead = displayed size at P.
  - Per update at P: `cancels = max(0, −Δsize − traded_at_P)` within a matched timestamp window. Only cancels are apportioned ahead or behind (sensitivity 0 / 50 / 100%). Increases go behind us.
  - Prints at or through P reduce queue_ahead. Fill when queue_ahead < 0.
  - If `last_trade_price.size` is missing, the fill is **unavailable**, never assumed.
  - Resync on hash divergence.
- **Adverse selection** is measured at +1, +5 and +30 min after inferred fills.
- **Slippage calibration:** predicted VWAP vs book state at +150 ms, 1 s and 5 s. A power-law fallback `slip = k·(size/depth_1¢)^β` is used only where levels are missing.

### Stage 1b: live-capable without credentials

`PolymarketVenue` is complete against a **mock venue server** that implements the documented behaviour:
- auth header validation shape;
- `/order` and `/orders` with per-element errors;
- cancel variants;
- order and trade status progressions including RETRYING and FAILED;
- 425 and 503 modes;
- heartbeat semantics;
- user and market websockets without replay;
- throttling latency.

Contract tests are written from `API_RESEARCH.md`. Optionally, `KalshiVenue` is proven against Kalshi's real demo environment.

**Exit:** the full chaos suite (§7.5) is green, and every preflight check is implemented.

### Stage 2: live pilot (only by user decision; §8)

- Deposit Wallet plus a CLOB-scoped session key, a tiny funded balance, Conservative profile, post-only only, allow-listed markets, signer firewall caps.
- Same decision code and logs. The live-vs-shadow cost gap per fill is the main metric.

### Simulator specification

- **Event-driven and deterministic** (seeded); the clock comes from recorded events in replay.
- **Inputs:** books, deltas and prints (own captures; pmxt history for replay tests), fee schedules, ticks, min sizes, market status events.
- **Outputs:** order and trade events in the *same* format as the live adapter, so the OMS and ledger cannot tell sim from live.
- **Missing depth means the fill is unavailable**, never free (principle from `evaluation/execution.py`). `evaluation/constants.py:DEFAULT_FEE_RATE = 0.0` is superseded by per-market fees in the new module; the old module is left unchanged.

---

## 6. Evaluation (frozen before the first paper decision)

### 6.1 Engine quality (the primary goal now)

| Metric | Target to pass Stage 0/1 |
|---|---|
| Ledger invariants (cash + liquidation-marked positions = equity; no negative positions; fills ⊆ orders) | 0 violations |
| Orders reaching a terminal state; stuck orders > TTL + 5 min | 100%; 0 |
| Reconciliation mismatches (sim self-check; mock venue) | 0 unexplained |
| Halt drills (each trigger in §2.3 injected) | 100% correct action within 1 cycle |
| Decision-to-signed-order latency p99 | < 500 ms |
| Paper-vs-shadow fill agreement (same orders) | Reported; no target until shadow calibrates |
| Shadow slippage model error (predicted vs inferred) | Mean absolute error reported by spread bucket |

### 6.2 Strategy performance (for any strategy claiming edge)

**Separation:** `exec_*` tables live in a separate `exec.db` (Postgres schema `exec` later). They never write to `research_*` cohorts or canonical `data-dumps` runs. Execution results never change experiment verdicts. Parameter changes are logged as trials.

**Metrics:**
- net P&L per share and per capital-day at liquidation marks;
- **Σrealised / Σpredicted net edge** (ratio of sums, clustered CI; review H4);
- cost decomposition;
- drawdown;
- fill rate, time-to-fill, implementation shortfall;
- the no-trade reason distribution.

**Benchmarks:**
- no-trade;
- a **deterministic mirrored trade** (paired difference = 2 × signed gross move);
- a **random-entry-time placebo** in the same markets (review L5);
- the strategy's own predicted P&L.

**Inference:**
- day blocks are the primary cluster;
- with about 20 blocks, use t with K−1 degrees of freedom or a wild-cluster bootstrap;
- MDE declared from a dry-run σ_trade using `research_lab/power.py`.

**Analysis times are fixed:** at the minimum sample (≥ 300 trades, ≥ 20 days, ≥ 100 events) and at day 90. α is split with O'Brien–Fleming. There is no continuous peeking.

**Gates:**
- **Stop:** upper CI of net per share < 0, or ratio upper CI < 0.3.
- **Paper → shadow:** lower CI > 0 and beats both placebos.
- **Shadow → live:** lower CI > 0 under queue split 0% (worst case), ratio lower CI > 0.5, and the user's decision.
- Fewer than 300 trades in 90 days returns the verdict "insufficient opportunity".

---

## 7. Engineering

### 7.1 Data model (`exec.db`)

| Table | Purpose and key columns |
|---|---|
| `exec_accounts` | id, user_id, mode, venue, wallet_address (public), signature_type, created_at |
| `exec_risk_profiles` | id, user_id, version, preset, limits_json, supersedes_id |
| `exec_strategies` | strategy_id, version, kind, evidence_status, spec_sha256?, enabled |
| `exec_intents` | intent_id, strategy_id/version, market, outcome, direction, target, urgency, limit_band, horizon_s, mu/sigma/q, basis, t_basis |
| `exec_decisions` | decision_id, intent_id, profile_version, market_meta_json (tick, min size, version, neg_risk, fee rate), costs_json, binding_constraint, outcome, reason_code |
| `exec_orders` | order_uid, decision_id, venue_order_id?, side, token/position_id, price, size, type, tif, expiration, version, domain, salt, ts_ms, signed_payload_sha256, metadata_hash, state |
| `exec_signed_payloads` | sha256, payload (blob, never contains keys), created_at |
| `exec_order_events` | order_uid, seq, from, to, t_local, venue_ts, raw_hash |
| `exec_trades` | trade_id (venue), order_uid, qty, price, fee, liquidity (maker/taker), status (MATCHED…CONFIRMED/FAILED), tx_hash?, t_status |
| `exec_positions` | account, position key, qty_provisional, qty_final, avg_cost, realised_pnl (derived; rebuildable) |
| `exec_cash_events` | deposits, rebates, redemptions, merges, fees, with source tx |
| `exec_marks` | account, token, t, bid, ask, mid, liquidation_value |
| `exec_risk_events`, `exec_recon_runs`, `exec_preflight_runs`, `exec_heartbeats` | Safety and audit |

Everything is append-only, except the derived position cache.

### 7.2 APIs (authenticated; per-user isolation via existing fastapi-users)

- `GET/PUT /exec/profile` (versioned, with a preview of money at risk);
- `GET /exec/state` (mode, halt state, preflight status, equity, exposures by cluster);
- `GET /exec/orders`, `/exec/trades`, `/exec/positions`, `/exec/decisions?outcome=NO_TRADE`;
- `GET /exec/pnl?compare=paper,shadow,predicted`;
- `POST /exec/intents` (ManualIntent; risk-checked like any strategy);
- `POST /exec/halt`, `POST /exec/resume` (reason required);
- `POST /exec/strategies/{id}/enable|disable`.

### 7.3 UI

- **Risk page:** preset cards plus custom sliders clamped to ceilings; a live preview of worst-case daily loss in currency, max positions, binding caps, and a worked example order with every cost line.
- **Monitor:**
  - mode and halt banner with kill button;
  - preflight checklist (balances, approvals, session-key expiry);
  - open orders with state;
  - trades by settlement state (provisional vs final);
  - positions with liquidation and mid marks;
  - equity curves for paper, shadow and live;
  - cost waterfall;
  - no-trade reasons;
  - recon status.
- **Strategy page:** each strategy's evidence status, enabled state and performance against benchmarks.
- **Copy rules:** "paper" and "shadow" are always labelled; strength ≠ probability; predicted ≠ realised.

### 7.4 Observability

- **Logs:** structured, one JSON line per state transition.
- **Metrics:** decision latency, data age, request latency per endpoint (the throttle signal), reject rate, fill rate, settlement times, recon diffs, heartbeat health.
- **Alerts** through `alerts/`.
- **Dead-man:** an external check that the engine heartbeat row is fresh.

### 7.5 Testing

- **Unit:** tick rounding, size and precision, fees, builder version branching, cost decomposition, sizing caps.
- **Property-based:**
  - no intent sequence breaches any cap, counting resting and DELAYED orders;
  - ledger invariants hold;
  - retries never create duplicates (sign-once).
- **Mock venue contract tests** for every documented behaviour (§5 Stage 1b).
- **Chaos tests:**
  - timeout after POST (order accepted / not accepted);
  - duplicate websocket events;
  - websocket drop without replay;
  - RETRYING → FAILED reversal;
  - 425 and post-only window;
  - 503 cancel-only;
  - tick change with resting orders;
  - heartbeat loss;
  - signer down;
  - clock jump;
  - stale book;
  - market resolves while orders rest.
- **Replay golden tests** on recorded books.
- **Leakage test:** strategies receive only data with receipt time ≤ decision time.
- **Signing tests:** EIP-712 domain "2" and "3" vectors against the SDK, using a throwaway key.

### 7.6 Secrets and the signing firewall (design only; nothing created now)

- **No keys anywhere near this repo or the web API.** The repo is public, so live executor configuration can live in a private repo (operational security).
- **Process split:**
  - **Engine:** no keys; sends unsigned order requests to the signer over a local socket.
  - **Signer:** holds the session key, loaded from the OS keychain or a secret manager. It enforces **independent hard caps** from a user-signed, read-only config:
    - max notional per order and per day;
    - market allow-list;
    - max open orders;
    - allowed order types;
    - mode = live only if the config says so.
  - The signer logs every request (hash plus parameters).
- **Least privilege:**
  - the session key has CLOB scope only and cannot withdraw;
  - the owner key is offline;
  - API credentials are per executor, with planned rotation before the 180-day key expiry;
  - funds are topped up manually.

---

## 8. Roadmap

### 8.1 Phases

Effort is in focused engineering days for one developer with agent assistance.

| Phase | Content | Effort | Depends on |
|---|---|---|---|
| X0. Contracts | `TradeIntent`, `Strategy` protocol, `VenueAdapter`, order and trade state machines, `exec.db` schema, risk profiles, frozen §6 | 3–4 d | — |
| X1. Paper engine | MarketState (book poller plus market websocket, bounded), risk engine and halts, builder, OMS with sign-once, `SimVenue` fill models, settlement-aware ledger, `ManualIntent` and `RuleBased` strategies, daily report | 8–11 d | X0 |
| X2. Mock venue and `PolymarketVenue` | Mock server (REST, websockets, error modes), adapter via `polymarket-client` ≥0.12, preflight, heartbeat process, recon, redemption simulation, contract and chaos tests | 8–12 d | X1 |
| X3. Shadow | Signing with a throwaway key, `MakerQueue`, adverse-selection and slippage calibration, paper/shadow comparison | 6–9 d | X1, X2 |
| X4. API and UI | `/exec/*`, risk page, monitor | 5–7 d | X1 |
| X5. Signer firewall | Separate process, independent caps, keychain integration (no real key), audit | 3–5 d | X2 |
| X6. `ArepoInsight` strategy | E002 adapter with review H1–H3 requirements; offline trade-count dry run first | 3–5 d | X1 (any time) |
| X7. (Optional) `KalshiVenue` on Kalshi demo | Proves a real sandboxed live path end to end | 4–6 d | X2 |
| X8. Live pilot | User decision only | — | X2–X5, §6 gates |

**Totals:** engine to live-capable (X0–X5) is about 33–48 days; the first end-to-end paper loop (X0–X1) is about 11–15 days.

**Deferred until a strategy shows non-trivial trade counts** (review L8): neg-risk conversion automation, multi-account support, and a framework migration.

### 8.2 Risks and open technical questions

| Item | Impact | Mitigation or resolution |
|---|---|---|
| Polymarket mid-migration: Protocol V2 (ExchangeV3, domain "3", PositionManager) for new markets from ~2026-11-02 (date UNVERIFIED) | Signing and approvals break if the engine is v1-only | Version branching per market from day one; SDK ≥0.12; contract tests for both domains |
| No official sandbox; Amoy support UNVERIFIED | Can't test live paths for free on Polymarket | Mock venue plus shadow signing; optional Kalshi demo; a first live step of tiny post-only orders (user decision) |
| No client order id | Duplicate orders on retry | Sign-once plus persisted payload plus REST matching before any resubmit |
| Websockets without sequence or replay | Missed fills or cancels | REST rebuild on every reconnect; REST and chain authoritative |
| Settlement can FAIL after MATCHED | Phantom positions | Provisional vs final ledger; reversal path tested |
| DELAYED orders can't be cancelled | Exposure larger than intended | Risk counts them in full until resolved |
| Silent throttling | Latency spikes and stale decisions | Latency-based back-pressure; budgets ≤ 25% of limits |
| 8 GB host shared with research collection | Crash risk (2026-10-10 incident) | Bounded token set, RSS caps, never alongside multi-GB jobs; a small VM later (architecture study) |
| Session-key setup needs builder-key enablement via Polymarket | Blocks the recommended custody model | Decide early (user); EOA allowlisting is the fallback |
| Rebates have no query API | Cash recon noise | Book from wallet inflows; daily recon tolerance |
| No strategy yet clears costs (E002: 2% of forecasts > half-spread) | Live pilot may never be justified | The engine is valuable regardless; strategies plug in as research matures |

### 8.3 Decisions only the user can make

| # | Decision | Recommendation |
|---|---|---|
| 1 | Start building X0–X1 (paper engine) now, alongside Phase 4 research? | **Yes.** It is self-contained and reuses existing data plumbing. |
| 2 | Scope of "live-capable" before any funding: stop at X5 (mock plus shadow signing), or also X7 (Kalshi demo)? | **Through X5; add X7 if you want a real-API end-to-end proof without funds.** |
| 3 | Custody model for any future live use | **Deposit Wallet + CLOB-scoped session key** (no withdrawal, revocable). It needs a builder key with session-key enablement; request it only when live is approved. |
| 4 | Default profile for paper and shadow; profile for any pilot | **Balanced** for paper and shadow; **Conservative, post-only** for a pilot. |
| 5 | Freeze §6 gates now | **Yes, before the first paper decision.** |
| 6 | AGENTS.md product definition ("never places trades or holds exchange credentials") | X0–X5 and X7 comply (no real orders or credentials). Revise the wording only when approving X8. |
| 7 | Where live executor code and config live | **A private repo** for the signer config and live executor deployment; the engine and paper/shadow code can stay here. |
| 8 | Live pilot and capital cap | Decide only after the shadow → live gate; a fixed small cap. |
| 9 | Host for an always-on engine | Laptop for paper and shadow; a small VM before any live pilot (the heartbeat and recon need uptime). |

---

## 9. Independent review: disposition (`REVIEW.md`)

| Finding | Disposition |
|---|---|
| **H1** edge not re-anchored to the traded book | **Adopted** (§2.2, §3.2): gross anchored on m_book, plus a `SOURCE_DIVERGENCE` no-trade reason in the `ArepoInsight` adapter (X6). |
| **H2** κ/σ horizon and basis inconsistencies | **Adopted as X6 requirements:** `basis` and `horizon_s` on intents; σ conditional on move size and spread bucket; κ/σ from pairs with target time ≤ decision; mid-basis κ is an upper bound until E004's touch-to-touch check. |
| **H3** almost nothing trades | **Adopted:** X6 starts with an offline trade-count dry run on logged E002 forecasts (development only, never touching E004 inputs). Per user direction, the engine no longer waits on any strategy. |
| **H4** gates have repeated looks and no power plan | **Adopted** (§6.2): fixed analysis times, O'Brien–Fleming, day blocks with t(K−1) or wild bootstrap, MDE from dry-run σ, ratio of sums. |
| **M1** queue double counting | **Adopted** (§5 Stage 1). |
| **M2** maker cost inconsistency | **Adopted** (§3.2): maker entry signed relative to m_book, + adverse selection − rebate. |
| **M3** resolution Kelly denominator; shrink towards mid | **Adopted** (§2.2). |
| **M4** data cannot support fill models | **Adopted** (§5 Stage 0): candidate-only level poller plus market websocket. |
| **M5** wrong SDK | **Adopted and extended:** the unified `polymarket-client` ≥0.12 (supersedes `py-clob-client-v2` per the API research). |
| **M6** idempotency | **Adopted** (§4.3): sign once, persist bytes, REST match, identical resubmit. |
| **M7** mid marks | **Adopted** (§2.1): liquidation-value marks. |
| **M8** shared host and rate budget | **Adopted** (§5 Stage 0, §8.2): own output root; run between snapshots; no collector changes during registered series. |
| **L1–L3** GTD, FAK, heartbeat, tick and depth units | **Adopted** (§3.2, §4.1, §2.1). |
| **L4** Kelly inert | **Adopted:** caps-first sizing default; Kelly is a diagnostic. |
| **L5** placebo | **Adopted:** mirrored-trade plus random-entry-time placebos. |
| **L6** token mapping (snapshots carry only token 0) | **Adopted:** the builder fetches `clobTokenIds` / `positionIds` per candidate. |
| **L7** missing triggers | **Adopted** (§2.3). |
| **L8** over-engineering | **Partly adopted.** Per user direction the engine machinery (recon, chaos tests, mock venue) is now the core deliverable rather than deferred. Neg-risk conversion automation and framework migration are deferred. |

---

## 10. Exact next action

**If the user approves decision 1:** implement **X0**. Create `backend/astrolabe/execution/` with:
- the `TradeIntent`, `Strategy`, `VenueAdapter` and state-machine definitions;
- the `exec.db` schema;
- versioned risk profiles with the §2.1 numbers and code ceilings;
- the §6 evaluation declaration committed as `docs/research/2026-10-11-auto-execution-plan/EVALUATION_FREEZE.md`;
- unit and property tests for the caps and state machines.

No network, no keys. Then **X1** (paper engine with `ManualIntent` and `RuleBased` strategies).
