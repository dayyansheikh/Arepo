# Case study: Maduro markets, January 2026 (Part A) and broad frozen-detector backtest (Part B)

**Status (2026-10-12):** `evidence_role: exploratory_historical`. Data were fetched after the fact from
public no-key endpoints. Maduro is the programme's single **tuning** case (`UNUSUAL_FLOW_PROGRAMME.md` §2),
so Part A is descriptive only. Part B is the frozen-rule evaluation on the judgement half of a random broad
sample. AREPO does not label any wallet, trade or market as insider activity. The object of study is
*unusual pre-news flow* in public, taker-side, HMAC-hashed trade prints. Wallets appear only as `W1`,
`W2`, ... (ranked by notional). No hash, address or identity is given here, and none is inferred.

Code: `backend/astrolabe/research_lab/event_study.py`, `backend/scripts/run_event_study.py` (`find`, `probe`,
`pull`, `timeline`, `bsample`, `bpanel`, `evaluate`), and `tests/unit/test_research_lab_event_study.py`. Data:
`data-dumps/research_lab/event_study/` (markets.json, per-market prices/trades/timelines, `first_trade.jsonl`,
broad panel and results, each with a manifest).

## Part A: what the data show

### Markets (Gamma `public-search` "maduro", "venezuela" and others, plus `/events`; 2,316 condition ids found)

| market_id | Question | Created (UTC) | Closed (UTC) | Resolved | Volume |
|---|---|---|---|---|---|
| **916440** | Maduro out by January 31, 2026? (primary) | 2025-12-11 21:44 | 2026-01-03 12:14 | YES | $11.0M |
| 663850 | Maduro out by March 31, 2026? | 2025-11-03 | 2026-01-03 12:24 | YES | $3.8M |
| 516947 | Maduro out in 2025? | 2024-12-31 | 2026-01-01 08:30 | NO | $34.6M |
| 916438 | US x Venezuela military engagement by January 15, 2026? | 2025-12-11 | 2026-01-03 10:30 | YES | $3.3M |
| 956631 | US forces in Venezuela by January 31, 2026? | 2025-12-17 | 2026-01-03 15:51 | YES | $6.4M |
| 956450 | Will the U.S. invade Venezuela by January 31, 2026? | 2025-12-17 | 2026-02-01 | NO | $8.4M |
| 1094682 | Maduro in U.S. custody by January 31? | 2026-01-03 07:47 | 2026-01-07 | YES | $11.0M (created after the move) |

Only 916440 was fully analysed. The secondary pull was stopped part-way through 663850's wallet lookups
(prices and trades are on disk; there is no manifest). It is resumable with
`run_event_study.py pull --markets 663850 916438 956631 956450` (the first-trade cache is reused). The
secondary markets are not used below.

### Data pulled for 916440 (window 2025-12-04 to 2026-01-05; the market traded 2025-12-12 to 2026-01-03 12:13)

- **Prices:** CLOB `prices-history`, 10-minute fidelity (finest available), 3,232 points. Price semantics are
  unverified (mid-like, not the last trade).
- **Trades:** Data API `/trades`. **Probe finding:** `/trades` honours `start`/`end` (unix s). `startTs/endTs`,
  `from/to`, `after/before` and other names are ignored. `fetch_trades_full` therefore splits any window that
  hits the 10,000-offset cap. This market needed one window: 9,367 trades and 3,533 distinct wallets.
  `/trades` returns **taker** fills (`takerOnly` default), so a wallet that only posted resting orders is
  invisible.
- **Wallet age:** one `/activity?type=TRADE&sortDirection=ASC&limit=1&end=<wallet's first trade in this
  market>` request per wallet. This gives the wallet's first Polymarket trade, known at the time of its trade
  here. 3,533 of 3,533 resolved (cache keyed by HMAC hash). Raw addresses were held in memory only.

### Timeline (1h bins, each evaluated at the bin end `t` from trades with `ts < t` and price points usable before `t`)

Price-defined onset: the first 10-minute point at least 10 points above its trailing-24h median is
**2026-01-03 06:20 UTC** (0.115 to 0.215). Before that, the price had already moved from 0.070 to about 0.10
between 02:50 and 04:10 UTC. It reached 0.665 at 07:10, fell back to about 0.37 by 09:10, then went to 0.99
or more from about 09:30. The widely reported public news times (strikes on Caracas overnight, then the
capture announcement in the morning, UTC) were **not verified here**, so every lead time below is relative
to the data-defined onset.

| Bin end (UTC) | p_yes | Trades | Volume $ | Net YES flow $ | Largest trade $ (wallet age, d) | New<7d share | z(vol) | z(net YES) | z(new<7d) |
|---|---|---|---|---|---|---|---|---|---|
| 01-01 21:00 | 0.055 | 15 | 19,352 | -18,826 | 19,000 (5.8) NO side | 0.98 | 1.9 | -2.4 | 2.6 |
| 01-02 00:00 | 0.055 | 21 | 35,898 | -25,388 | 30,400 (426) | 0.14 | 2.2 | -3.2 | -0.3 |
| 01-02 17:00 | 0.055 | 9 | 6,048 | +6,003 | 6,000 (6.5) **W1** | 1.00 | 1.1 | 1.1 | 2.7 |
| 01-02 22:00 | 0.065 | 16 | 6,199 | +5,532 | 5,783 (0.0) W4, first-ever trade | 0.94 | 1.1 | 1.0 | 2.5 |
| 01-03 02:00 | 0.070 | 11 | 6,528 | +5,842 | 6,000 (6.9) **W1** | 0.94 | 1.1 | 1.0 | 2.5 |
| 01-03 03:00 | 0.070 | 15 | 15,009 | +13,876 | 7,215 (6.9) **W1** | 0.97 | 1.6 | 2.0 | 2.5 |
| 01-03 04:00 | 0.085 | 100 | 37,793 | -14,132 | 10,000 (0.0) W3, first-ever trade | 0.27 | 2.2 | -1.5 | 0.1 |
| 01-03 05:00 | 0.105 | 36 | 22,089 | -13,893 | 14,264 (115) | 0.01 | 1.8 | -1.4 | -0.8 |
| 01-03 07:00 | 0.360 | 598 | 171,871 | +71,238 | 22,985 (37) | 0.01 | 2.97 | 9.0 | -0.7 |
| 01-03 10:00 | 0.992 | 1,248 | 1,191,409 | +651,342 | 148,490 (1,024) | 0.01 | 3.8 | 60.2 | -0.7 |

z = value against the market's own previous 7 days of bins (at least 2 days of history; sd floored at
0.1 × |mean|). In the 72 h before the onset, the largest trade relative to trailing-7-day notional never
exceeded 0.09.
Book depth is unavailable: pmxt covers 2026-04-13 to 08-10 only.

**Pseudonymous wallet W1.** Its first Polymarket trade was 2025-12-27 05:05 UTC. Between 2025-12-31 00:20
and 2026-01-03 02:58 UTC it made 7 taker buys of YES, totalling **$32,538 for about 436,760 shares at an
average of 0.0745**. Its last buy was about 3.4 h before the price onset and about 8 h before the price
passed 0.90. It made no trade in this market after the onset. Two wallets whose first-ever Polymarket trade
was the trade itself added $5,783 (W4, 21:44 on 2 Jan) and $10,000 (W3, 03:42 on 3 Jan) on YES. In the
30 h before the onset, wallets under 7 days old supplied $46k of the $115k YES-side notional. Over the same
72 h, total net flow was **toward NO** (-$205k), and the price did not respond to the YES buying: it held at
0.055-0.075 until about 02:50 on 3 Jan.

### When did activity first become unusual against the market's own baseline?

- **Hourly z ≥ 3 on volume, net YES flow, new-wallet (<7d) share or largest-trade/7d-volume:** no bin in the
  72 h before the onset. The first z ≥ 3 comes **at or after the onset** (net YES flow in the 06:10-06:20
  10-minute bin; hourly z(volume) at 08:00).
- **10-minute bins:** largest-trade/7d-volume z ≥ 5 first at 2026-01-01 09:10 (45 h before onset). But that
  bin's flow was on the **NO** side (-$30k), and the same metric reached z ≥ 5 in 5 earlier bins of this
  market's own history (bins ending more than 72 h before the onset).
- **Own-history check of the W1-style pattern:** prints of ≥ $5k from wallets under 7 days old occurred on
  12-22 (YES), 12-23 (NO), 12-24 (YES, $9,975), 01-01 (NO $19,000 and YES $5,000), 01-02 (YES ×2) and 01-03
  (YES ×4). Seven of the 11 prints were before the final 30 h, and none of the earlier ones was followed by a
  move. The final 30 h holds the densest YES-side cluster, which is only visible as distinct in hindsight.

**Honest reading.** The data do contain the reported shape: a days-old wallet repeatedly buying the 6-7%
outcome in size, hours before the move, while total flow ran the other way. W1's last buy came about 3.4 h
before the data-defined onset. But measured against this market's own trailing baseline, nothing crossed a
conventional z ≥ 3 alarm before the onset. Similar new-wallet longshot prints of $5-20k, on both sides,
recurred throughout the market's 3-week life with no move after them. With one case and no false-alarm
denominator, the W1 cluster is an anecdote, not a demonstrated signal.

### Did the frozen variants fire before the onset on Maduro? (descriptive: Maduro is a tuning case)

Method: `history_backfill.origin_frame` (2h grid) on 916440, with labels for 2/6/24h,
`detector_eval.normalise_panel(..., "history")`, rows with `traded_before_t == 1`, and `score_rule` for each
frozen spec. An "alert" is a score at or above that rule's 99th-percentile score on the broad discovery half
(the harness's 1% budget, approximated outside the harness). New-wallet first-seen was computed two ways:
the in-sample index, and `/activity` first-trade times. Both gave the same alerts.

| rule_id | Fired in the 72h before the onset (06:20 UTC 3 Jan)? | When (UTC, direction, hours before onset) | Alerts earlier in the market's own history |
|---|---|---|---|
| `uf_large_trade_v1` | **Yes, 8 times** | 12-31 08:00 YES (70.3h); 01-01 10:00 NO (44.3h); 01-02 00:00 YES (30.3h); 01-02 16:00 NO (14.3h); 01-02 18:00 YES (12.3h); 01-02 22:00 YES (8.3h); 01-03 02:00 YES (4.3h); 01-03 04:00 YES (2.3h) | 19 of 219 earlier scored rows (about 9%) |
| `uf_new_wallet_concentration_v1` | No (max 5.07 in-sample / 1.34 activity vs threshold 7.41) | | 0 |
| `uf_imbalance_burst_v1` | No (max 2.75 vs 5.74) | | 0 |
| `uf_convex_longshot_v1` | No (max 5.94 vs 6.26) | | 0 |
| `uf_pressure_no_response_v1` | No (max 1.86 vs 5.25) | | 0 |

Only the large-trade variant fired before the move, and it fired in both directions throughout the market's
life (about 1 row in 11). Firing before this move is therefore not distinguishable from its background rate
in this market.

## Part B: frozen variants on the broad sample (judgement half)

**Sample.** The `history/h2_main` run (3,200 markets, seeded `draw_sample` by status × fee_category × created
month, a 270-day lookback, CLOB prices at 10-minute fidelity, the newest ≤ 5,000 trades per market,
hashed wallets) was sub-sampled again: 1,500 markets, seed `arepo-unusual-flow-b1`, the same stratifier.
Panel: the `build_panel` outputs (2h grid, horizons 2/6/24h), Maduro/Venezuela and catalogue condition
ids removed (0 overlapped), and `normalise_panel(..., "history")`. 1,005 markets with rows, 327,766 rows.
**Discovery cut** 2026-07-30T06:00Z (`1785391200`), the row-time median, written into
`UNUSUAL_FLOW_DETECTOR.md` before any judgement metric. Judgement half: 163,921 rows, of which 44,575 were
untraded and excluded (programme rule). That leaves 119,346 traded rows: 357 markets, 269 clusters, about
332 market-months.

**Run.** `HeldOutHarness().evaluate(rule_id, panel[t >= cut], evidence_role="exploratory_historical",
dataset="h2_main_bsample_b1:judgement", cfg=EvalConfig())` for all 5 frozen variants, then
`holm_across_rules`. Primary statistic: h = 24h, δ = 0.10, 1% budget, ≤ 5 matched controls (same UTC day,
same |mid-0.5| band, different market), event-clustered bootstrap. Liquidity is NaN in history panels, so the
liquidity tercile is not part of the matching. Discovery-half harness runs (3 batch-1 rules) were plumbing
checks only. Cumulative `detector_eval` trials: **8** (3 discovery plumbing plus 5 judgement).

| rule_id | Episodes (clusters) | Firing rate / market-month | Precision | Control base rate | Lift | Excess (95% CI) | p one-sided | **Holm p** | Testable | Recall, large moves (CI) | Lead time, median (n) | Paper P&L $/alert, 5 sh (95% CI) | `alerts_needed(b, 0.05)` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `uf_large_trade_v1` | 80 (16) | 0.25 | 0.038 | 0.036 | 1.05 | +0.002 (-0.037, +0.161) | 0.47 | **1.0** | yes | 0.020 (0.006, 0.039), 6/294 | 4h (15) | -0.13 (-0.33, +0.22) | 281 |
| `uf_imbalance_burst_v1` | 34 (18) | 0.10 | 0.029 | 0.063 | 0.47 | -0.033 (-0.074, +0.031) | 0.87 | **1.0** | yes | 0.007 (0, 0.023), 1/141 | 14h (2) | -0.11 (-0.21, +0.02) | 395 |
| `uf_new_wallet_concentration_v1` | 25 (11) | 0.08 | 0.080 | 0.048 | 1.67 | +0.039 (-0.067, +0.172) | 0.27 | **1.0** | no (< 30 episodes) | 0.021 (0, 0.048), 3/140 | 0h (5) | -0.12 (-0.27, +0.01) | 333 |
| `uf_pressure_no_response_v1` | 20 (18) | 0.10 | 0.100 | 0.090 | 1.11 | +0.010 (-0.086, +0.140) | 0.48 | **1.0** | no | 0.007 (0, 0.025), 1/141 | 0h (4) | -0.06 (-0.30, +0.26) | 503 |
| `uf_convex_longshot_v1` | 6 (2) | 0.02 | 0.000 | 0.133 | 0.00 | -0.133 (-0.16, 0.00) | 1.0 | **1.0** | no | 0.000, 0/26 | none | -0.19 (-0.22, -0.18) | 659 |

Random-budget placebo rank of observed row precision (higher = worse than random): 0.13, 0.96, 0.18, 0.24, 1.0
(same order). Paper P&L is "optimistic, not tradable": mid ± an assumed 0.02 spread, maximum fee when the fee
is unknown, no depth walk.

**Reading.** No variant shows excess directional precision over matched controls. All Holm p = 1.0, and
every CI includes 0. Three of the five are not testable at the declared minimum (30 episodes, 10 clusters).
Recall on large moves is about 0-2%. Every mean paper P&L is negative. At the observed control base rates
(4-13%), detecting a +5-point precision excess at 80% power would need about 280-660 alert episodes, against
6-80 here. Even a real effect of that size could not have been seen in this sample, so the result is
**null and underpowered**, not evidence of absence.

## Does this justify a pre-registered live test?

Not as a confirmatory test of these five rules in their current form. None shows even a directional hint on
the judgement half, and a 5-point excess needs about 300-650 alert episodes. At 0.1-0.25 episodes per
market-month, that is thousands of market-months: years at AREPO's 2,000-market, 2-hourly sampled frame unless
the alert budget rises. A live **descriptive** pre-registration is cheap and worthwhile: write `alerts.jsonl`
at alert time with matched controls before outcomes exist, and true Polymarket wallet age via `/activity`
rather than new-to-sample. It would accumulate the denominator that the Maduro anecdote lacks.
`uf_large_trade_v1` additionally needs the collector feature noted in `UNUSUAL_FLOW_DETECTOR.md`.
