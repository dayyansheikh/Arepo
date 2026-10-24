# Technical review of PLAN.md draft (efb4fa7), 2026-10-11

Independent subagent review. The disposition of each finding is recorded in PLAN.md section 9.

## Technical review of the auto-execution PLAN.md

I didn't edit any files. I read the plan, `forecast.py`, the e002 spec, `panel.py`, `book_sweep.py`, `evaluation/execution.py`, the E002/E004/E006/D1 ledger sections and the regime timeline. I checked the Polymarket docs (fees, create order, orders overview, v2-migration, market channel, changelog) and the NautilusTrader docs.

**Checked and correct:**
- The fee per share is feeRate·p(1−p), in USDC, taker only: 0.04×0.25 = 1.0¢.
- μ_shrunk = 0.315×0.03316 = 1.04¢.
- f* = μa/σ² is the right small-edge Kelly result, and 0.01×0.5/0.0025 = 2.0.
- calib ≈ 0.212/0.3316 = 0.64.
- The 150 ms crypto taker delay is right.
- Batches of 15 orders are right.

### HIGH

**H1. §3.2, §1.4, §5 Stage 0: the edge is never re-anchored to the book you actually trade.**
- μ forecasts the next-capture mid relative to the Gamma origin mid. That mid is 7–12 min old, and per D1 it is mostly quote movement in untraded markets.
- By the time the candidate sweep runs, part or all of the reversal may already have happened. Subtracting costs from κ|mu| then trades on edge that is already gone. This is the main way paper P&L would be optimistic.
- Fix: with s = sign(mu), set `gross = s·(m_origin + κ·mu − m_book)`, and use the same `m_book` in every cost term.
- Add `NO_TRADE: SOURCE_DIVERGENCE` when |m_gamma − m_book| > 1 tick, or more than κ|mu|/2.
- Use the remaining horizon, not the nominal one.

**H2. §1.2, §2.2, §3.3: κ and σ are not defined at the horizon, or on the price, you trade.**
- The plan contradicts itself on cadence: holding "~5h until next capture" in §3.3 against a "2-hourly" collector in §1.4. E004 runs on ~2h periods, and the coefficient was fitted on multi-day spacing (E004 disclosure).
- calib_ratio 0.63 is a mid-change slope at 4.92h. The ledger itself says quote noise alone predicts a negative slope.
- Fix, in three parts:
  1. Add `calib_basis ∈ {mid, touch}` and `horizon_s` (the planned hold) to Insight v1. Treat a mid-basis κ as an upper bound until E004's touch-to-touch execution check is scored at the actual hold horizon.
  2. Make σ conditional on |chg_1h| and the spread bucket. In flow screen S1, 61.8% of pairs have dmid = 0, so unconditional residuals badly understate σ for selected movers. That also makes the 3σ stop too tight.
  3. Estimate κ and σ only from pairs whose target time is ≤ t_decision, and cover this in the §7.5 leakage test.

**H3. §8.1 ordering: the feasibility arithmetic says almost nothing trades.**
- Balanced needs net ≥ 1.5×cost, so g ≥ 2.5×cost. With κ·0.3316 = 0.1045:
  - taker at p = 0.5 in a 0.04-fee market with a 1¢ spread costs 3¢, so it needs |chg_1h| ≥ 0.72;
  - fee-free with a 1¢ spread costs 1¢, so it needs |chg_1h| ≥ 0.24.
- Three hundred trades in 90 days (about 3.3 a day) is probably unreachable.
- Fix: add a one-day step X0′ before X1. Apply the §3.2 rule offline to the already-logged E002 forecasts and existing book sweeps. Report the no-trade reasons and the expected trades per day. This is descriptive and development-only, and must not touch E004 inputs. Size X1 from that result, and consider gating X1 on E004's execution check.

**H4. §6: the gates have repeated looks and no power plan.**
- "Stop (any stage)" can be checked continuously, which inflates false stops and false promotions.
- Fix: fix the analysis times (at the minimum sample and at day 90), with α split by Bonferroni or O'Brien–Fleming.
- Use day blocks as the primary cluster (the ledger notes period-wide shocks). With about 20 blocks, use t with K−1 degrees of freedom or a wild-cluster bootstrap, not a percentile bootstrap.
- Declare the MDE with the M2 tools, using σ_trade from an X0′/Stage-0 dry run. At σ ≈ 5¢ and n = 300 iid, the MDE is already about 0.8¢, and it is larger once clustered.
- Replace the "realised/predicted slope" with a ratio of sums, Σrealised/Σpredicted, with a clustered CI. Every trade sits just above the threshold, so the slope has almost no leverage and its CI will be uninformative.

### MED

**M1. §5 Stage 1: the queue model double-counts trades.**
- Executions against resting size also reduce the level's aggregate `size` in `price_change`.
- The docs don't confirm whether `size` is the aggregate or a delta. The example matches the aggregate. Verify this empirically.
- Fix: per level, `cancels = max(0, −Δsize − traded_at_P)`, matching prints to the same timestamp window, and apportion only `cancels`. Size increases go behind you.
- `last_trade_price.size` is optional: when it is missing, the fill is unavailable.
- Resync from REST `/book` when the book `hash` diverges.

**M2. §3.2 and the §2.2 example: the maker cost is internally inconsistent.**
- Maker entry ignores the spread you capture but adds c_adverse = half-spread. The worked example also leaves c_adverse out.
- Fix: `c_in(maker) = (P_limit − m_book)` signed for side, `+ c_adverse − rebate`.
- With the example's 2¢ spread:
  - maker entry with taker exit = −1 + 1 + 1 + 1 = 2¢. The plan's own definitions would give 3¢.
  - maker both ways ≈ 0 plus non-fill risk.

**M3. §2.2: the resolution Kelly formula has the wrong denominator.**
- With c = a + φ(a), f* = (q − c)/(1 − c), not (q − a − φ)/(1 − a).
- Shrink towards the mid, not the ask: q_used = m + κ(q − m). Shrinking towards the ask hides the spread.

**M4. §5 Stage 0: the data does not support the fill models.**
- `book_sweep` stores only the top of book plus `depth_*_1c/5c`, not the levels, so a VWAP depth walk is impossible.
- There is no book between the post-insight sweep and the next snapshot about 2h later. A 30-minute maker order therefore can never show a trade-through, and the maker fill rate is 0 by construction.
- Fix: add a candidate-only capture of raw levels (to 5¢), and poll each candidate every 1–2 minutes over the order life and the hold. Keep it bounded and RSS-capped, with its own output root.

**M5. §1.5: wrong client library.**
- Polymarket's v2-migration guide says `py-clob-client` is V1-only and no longer works against production. Use `py-clob-client-v2`.
- NautilusTrader does have a Polymarket adapter. Its nightly docs target V2/pUSD, but its "latest" docs are stale, so stable-release V2 support is unconfirmed.

**M6. §4: the idempotency design relies on lookups that don't exist.**
- `OpenOrder` does not expose `metadata`, and no client-id lookup is documented.
- Uniqueness comes from the signed ms `timestamp`, so re-signing a retry creates a new order.
- Fix: sign once, then persist the signed payload and its hash before the POST. On a timeout, query open orders and trades for the token and match on (side, price, size, timestamp). Resubmit only the identical signed bytes. Use `metadata` for attribution only.

**M7. §2.1, §6: marking at mid.**
- Marking at mid overstates P&L by about the half-spread plus the exit fee, and makes the daily-loss and drawdown halts noisy in thin books.
- Fix: mark at liquidation value (the bid for longs, minus the taker fee), and report mid as secondary.

**M8. §6 separation: shared host and rate budget.**
- Candidate sweeps and pollers share Polymarket rate limits and the 8 GB host with the registered E004/E006 collection. E002 already lost a capture to `http_403`.
- Fix: run exec network jobs only after a snapshot is complete. Never write under `data-dumps/research_lab/snapshots/`.
- Fetch `feeSchedule` and tick from the exec module for candidates only. Do not add fields to the collector during a registered series.

### LOW

**L1. GTD and FAK details.**
- GTD expires 60 s early, so set expiration = now + 60 + N, and it must be at least 3 minutes ahead (an effective minimum of about 2 minutes).
- Post-only works only with GTC or GTD.
- A FAK BUY `amount` is pre-fee notional, so the cash check must add the fee.

**L2. Heartbeat details.**
- Send every 5 s. The timeout is 10 s, and the cancel can land up to 5 s later.
- It cancels all orders for those API credentials, so each executor needs its own credential set.

**L3. Tick and depth units.**
- The 0.0025 tick applies to World Cup markets only, not "some sports".
- "2 ticks of touch" is only 0.2¢ at a 0.001 tick, and it mixes units with "5¢ depth in USDC". Use a fixed 1¢ band in shares for both, and check min_order_size after the depth cap.

**L4. Kelly is not doing anything (§2.2).**
- The caps always bind: even at σ = 10¢, λf* = 12.5%, above the 5% ceiling. Kelly is effectively a sign gate.
- For the prototype, size = min(caps) and log Kelly as a diagnostic.
- The 0.5 status multiplier is ad hoc. A principled alternative is the CI-bound ratio 0.174/0.332 = 0.52.

**L5. The placebo (§6) is nearly redundant.**
- With symmetric costs, a random-sign placebo has expectation ≈ −cost, so it mostly repeats the net > 0 test with added noise.
- Replace it with a deterministic mirrored trade (the paired difference is 2× the signed gross move), plus a random-entry-time placebo in the same markets to capture drift.

**L6. Insight mapping (§1.2).**
- `predict_frame` is keyed by `market_id`, the mid comes from the outcome-0 Gamma quote, and snapshots carry only `clob_token_id_0`.
- Down trades need `clobTokenIds[1]`, fetched for candidates.

**L7. Missing triggers (§2.3).**
- No new complete snapshot for 2 cycles: block new entries.
- A held market that is paused, closed or under dispute.

**L8. Effort and over-engineering (§8.1).**
- X1 at 6–8 d is optimistic once M4, L6 and the fee lookup are added.
- Defer the OMS cancel/replace races, chaos tests, recon and the X3 UI until H3 shows a non-trivial trade count.

### What is solid

- The plan characterises "insight" correctly: v1 `Signal` is a ranking and data-quality score, and it is rightly not sizeable.
- Using frozen research-lab specs with hashes as the only source of sizeable insight is sound.
- The same decision code runs in every mode, with predicted, simulated and realised P&L as measured gaps.
- Every no-trade reason is logged as an output.
- Resting orders count against limit headroom.
- Profile limits are coherent: gross exposure binds before per-market caps × max positions. Profiles are versioned and clamped to ceilings held in code.
- Missing depth gives "unavailable, never zero".
- Decisions use receipt clocks, not venue timestamps.
- Execution is physically separated in `exec.db`, has no verdict authority, and logs trials.
- The signing firewall is a separate process with independent caps. Venue heartbeat and reconcile-first restarts are right.
- Gates are frozen before data, and the worst-case queue sensitivity (cancel_split = 0%) is used for promotion.
- "Do not trade" is the default outcome.

Sources:
- https://docs.polymarket.com/trading/fees
- https://docs.polymarket.com/trading/orders/create
- https://docs.polymarket.com/trading/orders/overview
- https://docs.polymarket.com/v2-migration
- https://docs.polymarket.com/market-data/websocket/market-channel.md
- https://docs.polymarket.com/changelog
- https://nautilustrader.io/docs/nightly/integrations/polymarket/
