# Execution costs (paper-only)

AREPO never trades. `backend/astrolabe/research_lab/economics.py` prices hypothetical fills against
recorded public book sweeps for H2a/H2b and Phase 8. Results are "optimistic, not tradable": no
latency, queue position or depth beyond the recorded bands.

## Formula sources
- **Taker fee:** `fee = C * feeRate * p * (1 - p)`, takers only, USDC, rounded to 5 dp (smallest fee
  0.00001). Source: <https://docs.polymarket.com/trading/fees>, retrieved 2026-10-11. The page lists
  rates by category: crypto 0.07; sports, economics, culture, weather, other 0.05; finance,
  politics, mentions, tech 0.04; geopolitics 0. It does not mention sell-side fees, so the same
  formula is applied to the exit leg (assumption).
- **Per-market rate:** the sidecar `fee_schedule` (`{"exponent":1,"rate":r,"rebateRate":..,
  "takerOnly":true}`) is the primary source, giving `C*rate*(p(1-p))^exponent`. All observed
  schedules have exponent 1, so it equals the documented formula. `takerBaseFee` (always 1000) is not a
  rate for this formula and is ignored.
- **Cross-check against the docs:** sports schedules at 0.03 (`sports_fees_v2`,
  `sports_fees_nfl_cfb_oct26`, 30,503 sidecar rows of 248,235) sit below the docs 0.05; politics
  and finance at 0.04 and crypto at 0.07 match. The code flags `schedule_below_docs` and offers
  `fee_policy="conservative"` (max of schedule and docs). The default is the design's rule.
- **Missing data:** `feesEnabled=0` gives 0. Enabled with no usable schedule gives NaN plus a flag
  (`unknown_schedule`); in P&L the design rule applies (highest table rate, 0.07). Never 0.

## Execution model
- Size `q = max(1, orderMinSize)` (all observed markets: 5). Entry needs top-of-book size >= q.
- The sweep file stores only the touch and cumulative depth within 1c and 5c. The walk prices the
  1c band at best +/- 1c and the 5c band at best +/- 5c, rounded against the taker to the tick, so
  fills are an upper bound on cost. Exact `levels_bids/levels_asks` are used when given.
- Reported per fill: half-spread (touch vs mid), impact (VWAP vs touch), fee, `depth_exhausted`.
- Outcome 1 trades mirror the token-0 book at `1 - price`. An unfilled exit remainder is valued at 0
  and flagged. A missing exit sweep means the origin does not qualify.
- H2a/H2b: one-sided 5th-percentile bootstrap, whole clusters, same draw scheme as
  `compare.paired_bootstrap` (seed 116, 1,000). The two-sided CI comes from that function itself.
  Needs >= 30 trades and >= 10 clusters with a trade (else "not testable"), and must reject under
  every cluster definition.

## Cost distribution (sweep 20261011T184657Z, snapshot 20261011T183104Z)
37,225 eligible tokens, 37,103 fillable for 5 shares round trip (same book, buy then sell). Median
round trip **4.5c per share** (p25 3.2c, p75 6.8c, p90 9.3c). Impact is 0 at median because q=5
sits inside the touch. Share of markets with round trip <= 2c: 10%; <= 3c: 23%; <= 5c: 55%.

| Price band | n | median cost | spread | fee | break-even dLL (nats) |
|---|---|---|---|---|---|
| <0.05 | 8218 | 4.4c | 4.1c | 0.3c | 0.0246 |
| 0.05-0.20 | 10597 | 4.2c | 3.0c | 0.8c | 0.0086 |
| 0.20-0.80 | 16158 | 5.2c | 2.2c | 2.3c | 0.0060 |
| 0.80-0.95 | 1485 | 4.2c | 3.0c | 1.0c | 0.0103 |
| >=0.95 | 645 | 2.8c | 2.5c | 0.3c | 0.0177 |

| Liquidity | n | median cost | spread | break-even dLL |
|---|---|---|---|---|
| <1k | 11194 | 6.2c | 5.1c | 0.0225 |
| 1k-10k | 16938 | 4.7c | 3.0c | 0.0075 |
| 10k-100k | 8747 | 3.1c | 2.0c | 0.0039 |
| >=100k | 346 | 1.8c | 1.0c | 0.0012 |

| Category | n | median cost | fee | break-even dLL |
|---|---|---|---|---|
| sports | 21209 | 5.2c | 1.2c | 0.0112 |
| politics | 6456 | 3.6c | 0.6c | 0.0075 |
| crypto | 4324 | 4.5c | 3.5c | 0.0041 |
| finance | 1091 | 4.7c | 0.7c | 0.0132 |
| tech | 1036 | 4.2c | 0.7c | 0.0110 |
| culture | 986 | 3.6c | 0.7c | 0.0082 |
| weather | 697 | 4.5c | 1.1c | 0.0085 |
| economics | 533 | 3.4c | 0.9c | 0.0060 |
| no fees (unknown category) | 727 | 1.8c | 0 | 0.0015 |

## Break-even
To cover a round trip of `c` per share, the model must be right by about `c` in probability
(expected gross P&L per share = true probability minus mid). The matching log-loss gain over the
market price is `KL(m + c || m)`, about `c^2 / (2 m (1 - m))` nats per observation. It is a
required edge on the traded subset, before selecting on the signal.

**Headline:** a typical market needs a 4.5 point probability edge to break even, about 0.006 to
0.011 nats per observation in the central price band. That is 1 to 2 times a 1% relative
log-loss gain when the market log loss is near 0.6 (about 0.006 nats), so there is no margin. Only
liquid markets (>= 10k) have costs low enough to be worth forecasting: round trip 1.8c at >= 100k
(0.0012 nats) and 3.1c at 10k-100k (0.0039 nats). Markets under 1k liquidity (30% of the sweep) need 6c or
more. The best cells are price <0.05 or >=0.95 with liquidity >= 100k (round trip < 1c), but
they are tiny (n = 80) and carry little outcome variance. Small-edge forecasting should be
restricted to liquid, mid-priced, low-fee markets (politics, economics, culture).

Caveats: one snapshot; costs vary by time of day. A one-sided position held to resolution would
avoid the exit half-spread, which is a different rule and is not modelled. Reproduce with
`python backend/scripts/execution_cost_breakeven.py`.
