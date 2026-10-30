# Polymarket market-structure regime timeline (2022-09 to 2026-10)

Independent web research, 2026-10-11 (subagent; main source docs.polymarket.com/changelog). Rows marked UNVERIFIED or Press need confirmation before they bind anything. Research input, not an implemented decision.

**Actionable for AREPO (lead summary):**
- Treat 2026-04-28 ~11:00 UTC (CLOB V2, pUSD, all open orders wiped) as a hard break in any pooled or historical analysis.
- Fees apply by market *creation date*, so the fee regime is a per-market attribute.
- Gamma `feeSchedule` (since 2026-03-31) and `tick_size` are cheap as-of fields worth adding to the research collector, additively, between registered series.
- Phase 8 cost models must use the per-market fee formula. Up to feeRate/4 at p=0.5, e.g. 1.75% for crypto and 1.25% for sports.
- Short-duration crypto up/down markets (from ~2025-10) need a universe-composition indicator.

## Polymarket market-structure timeline, 2022-09 to 2026-10

I checked this on the web only: nothing was downloaded and the repo was not touched. The main source is the official changelog at https://docs.polymarket.com/changelog (cited as **CL** below). An item is marked Y only when an official doc or a primary on-chain source gives the date.

| Date (UTC) | Change | Source | Verified? |
|---|---|---|---|
| ~2022-09-27 | CTF Exchange v1 deployed (0x4bFb…982E), so CLOB-era on-chain trades start here. Collateral is USDC.e. | https://polygonscan.com/address/0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E (page says "4 yrs 14 days ago") | Approximate (date inferred from relative age) |
| ~2023-11-29 | Neg Risk CTF Exchange v1 deployed (0xC5d5…f80a). Multi-outcome markets move to the NegRisk adapter. | https://polygonscan.com/address/0xC5d563A36AE78145C45a50134d48A1215220f80a (page says "2 yrs 316 days ago") | Approximate |
| 2025-05-28 | FAK order type added; market websocket subscription limit removed | CL | Y |
| 2025-07-23 | Book responses gain `tick_size`, `min_order_size` and `neg_risk` fields | CL | Y |
| 2025-08-26 | Data API `/trades` and `/activity` capped at limit 500 and offset 1000 | CL | Y |
| 2025-09-15 23:00 | WSS `price_change` message structure changed | CL | Y |
| ~2025-10-20 | 15-minute crypto up/down markets launch on global Polymarket (Chainlink-resolved) | https://www.cryptopolitan.com/polymarkets-15-minute-up-down/ ; https://www.altcoinbuzz.io/polymarket-launches-15-minute-crypto-markets | Press only. Launch date for hourly markets not found. |
| ~2025-11 | 500ms taker delay on hourly and 15-minute crypto markets | https://dev.to/lkto1m/february-2026-changed-polymarket-forever-heres-what-happened-to-my-bots-numbers-2fi5 | UNVERIFIED |
| 2025-11 / 2025-12-03 | Polymarket US (QCEX, a CFTC DCM) gets its Amended Order of Designation, then a waitlisted iOS sports rollout. Waitlist removed 2026-05-12. It is a separate venue and order book. | https://cointelegraph.com/news/polymarket-us-relaunch-waitlisted-users ; https://covers.com/industry/polymarket-removes-waitlist-launches-for-american-ios-users-may-12-2026 | Press. No evidence that global market listings changed. |
| 2026-01-05 | **First taker fees**, on 15-minute crypto only. Formula C·p·0.25·(p(1−p))², peaking at 1.56% at p=0.5. Daily maker rebates funded from fees. | CL ; https://www.theblock.co/post/384461 | Y |
| 2026-01-06 | Post-only orders and HeartBeats API | CL | Y |
| 2026-02-12 | 5-minute crypto markets launch with fees | CL | Y |
| ~2026-02-16 | 500ms taker delay removed without announcement | https://protos.com/polymarket-ends-trading-loophole-for-bitcoin-quants/ | Press |
| 2026-02-17 | Liquidity-reward sponsorship opened to all users | https://defirate.com/news/polymarket-launches-public-api-unlocks-permissionless-liquidity/ | Press |
| 2026-02-18 | **Sports fees** start on NCAAB and Serie A, newly created events only (rate 0.0175, exponent 1, peak ≈0.44%). Rebates now calculated per market. | CL ; https://igamingbusiness.com/prediction-markets/polymarket-sports-fee-hike-2026/ | Y |
| ~2026-02-25 | 250ms taker delay on 5-minute, 15-minute and hourly crypto | dev.to (above) | UNVERIFIED |
| 2026-03-06 | Fees extended to all crypto markets (1H, 4H, daily, weekly) created after Mar 6 | CL (Mar 1 entry) | Y |
| 2026-03-30 | **Fee Structure V2**: fee = C·feeRate·p(1−p). Applies to crypto, sports, finance, politics, economics, culture, weather, tech, mentions and other. Geopolitics stays free. Markets listed from Mar 30. Fee schedule moves into a per-market `feeSchedule` (Mar 31). | CL ; https://docs.polymarket.com/trading/fees | Y |
| 2026-04-09 / 04-10 | Gamma `/markets` gets `closed=false` as the default. Keyset pagination endpoints added. Keyset limit capped at 100 on 05-14. | CL | Y |
| 2026-04-28 ~11:00 | **CLOB V2 cutover**. New contracts: Exchange 0xE111…996B and NegRisk Exchange 0xe222…0F59. **pUSD replaces USDC.e** as collateral (wrapped via the Collateral Onramp). Order struct drops `nonce`, `feeRateBps` and `taker`, and adds a ms `timestamp`, `metadata` and `builder` (bytes32 builder code). Fees are set at match time and charged to takers only. EIP-712 domain version moves to "2". About 1 hour of downtime, **all open orders wiped**. The docs do not say whether markets and tokens carried over or whether the OrderFilled layout changed. | CL ; https://docs.polymarket.com/v2-migration | Y (carry-over and OrderFilled layout UNVERIFIED) |
| 2026-07-02 | World Cup moneyline, advance, spread and total markets move to a **0.0025 tick** | CL | Y |
| 2026-07-10 00:00 | Sports taker coefficient 0.03 → 0.05; sports rebate 25% → 15% | CL | Y |
| 2026-07-14 / 07-17 | v1 NegRisk adapter (0xd91E…5296) retired; v2 adapter is 0xadA2…eAab | CL | Y |
| 2026-07-24 04:00 | FAK/FOK responses return `tradeIDs` instead of tx hashes | CL | Y |
| 2026-08-07 / 08-14 | Crypto up/down markets resolve on Chainlink TWAPs; 5-minute markets move from a 30s to a 60s TWAP on 08-14 | CL | Y |
| 2026-08-17 11:00 | Crypto taker delay 250ms → 50ms | CL | Y |
| 2026-09-04 14:00 | Data API v2 goes live (cursor pagination, `data` wrapper, v1 frozen). prices-history moves to `data-api/v2/prices-history`. Crypto taker delay 50ms → 150ms. | CL | Y |
| 2026-09-15 | PolyBolt reference-price websocket launches; RTDS becomes legacy | CL | Y |
| Ongoing | Dynamic tick: a `tick_size_change` event fires when price goes above 0.96 or below 0.04 (0.01 → 0.001). Allowed ticks are 0.1, 0.01, 0.001 and 0.0001, plus 0.0025 for the World Cup markets. Minimum order size is per market (5 in the examples). No start date found. | https://docs.polymarket.com/market-data/websocket/market-channel.md | Y for the rule; start date UNVERIFIED |

Current fee rates (fees page): crypto 0.07 with 20% rebate; sports 0.05 with 15%; finance, politics and tech 0.04; economics, culture, weather and other 0.05; mentions 0.04; geopolitics 0. Peak at p=0.5 is feeRate/4, so 1.75% for crypto and 1.25% for sports. Before 2026, v1 orders carried a signed `feeRateBps`, but no taker fees are documented before 2026-01-05, which suggests it was effectively 0. I have not checked that on-chain.

## Implications for AREPO

**Regime boundaries to encode**, in order of importance:
- **R0, until 2026-01-04: fee-free.** Short-duration crypto markets appear from about 2025-10-20, which shifts the population mix.
- **2026-01-05**: fees start on 15-minute crypto.
- **2026-02-12 to 02-25**: 5-minute markets launch, sports fees start, and the crypto taker-delay regime changes.
- **2026-03-06**: fees on all new crypto markets.
- **2026-03-30**: Fee Structure V2 for newly listed markets in most categories.
- **2026-04-28 ~11:00**: CLOB V2, pUSD collateral, new contracts, order wipe. This is a hard microstructure and data-format break.
- **2026-07-10**: sports fee hike.
- **2026-09-04**: Data API v2 and 150ms taker delay. This is a data-access break, not a price-dynamics break.

Fee changes apply **by market creation date**, not calendar date. The fee regime is therefore a per-market attribute, read from `feeSchedule` or from the listing date. Trades on the same day can sit under different fee regimes.

**Sealed holdouts:**
- **On-chain trades (dev 2022-11 to 2025-12-24; holdout 2026-01-08 to 03-29): does not straddle a break, but dev and holdout are in different regimes.** Almost all of dev is fee-free. The holdout runs entirely in the new fee era and spans several sub-breaks: Feb 12 (5-minute markets), Feb 18 (sports fees), Feb ~16-25 (taker delay), Mar 6 (all-crypto fees). Fee Structure V2 on 03-30 falls just after it ends. The holdout's market mix is also much heavier in short-duration crypto. Without regime covariates or a stratified evaluation, a dev-vs-holdout gap cannot be separated from a structural change. Cleanest fix: exclude or stratify crypto up/down markets and fee-enabled markets. At minimum, report holdout results split into fee-free and fee-enabled categories. The holdout itself should not be changed; post-hoc stratification needs a written justification.
- **pmxt (dev 04-13 to 06-04; holdout 06-18 to 07-31): dev straddles the hardest break.** CLOB V2 on 2026-04-28 wiped every resting order, which empties the book and then rebuilds it. It also changed collateral and contracts. Dev should be split into pre-V2 (04-13 to 04-28) and post-V2 (04-28 to 06-04), or the pre-V2 slice and the cutover day (with a buffer of at least 24h) should be excluded, before any comparison with the all-V2 holdout. The holdout itself straddles 07-02 (0.0025 World Cup tick), 07-10 (sports fee hike) and 07-14/17 (NegRisk adapter retirement). Sports and World Cup markets in the holdout therefore differ in cost and tick from dev. Flag them, or analyse non-sports separately.
- **trentmkelly holdout (from 2026-10-12): no known break inside or immediately before it.** It does follow the 09-04 Data API v2 move and the taker-delay change. Any dev data from before 2026-09-04 that used v1 prices-history or Gamma offset pagination differs from v2-sourced holdout data in how it was collected, so collection provenance should be recorded. AREPO's own captures from 2026-09-20 onward are all in one regime.

**Features and costs that need regime indicators:**
- **Cost models:** use the per-market fee formula and coefficient by regime: 0 before 2026; the (p(1−p))² curve for early crypto; 0.0175 for early sports; feeRate·p(1−p) after 03-30; the sports step on 07-10. Fees are taker-only, and rebates go to makers. A zero-cost assumption is valid only for fee-free markets.
- **Spread, imbalance and depth features:** the tick regime varies per token over time (0.01 vs 0.001 at extreme prices; 0.0025 for the World Cup). Normalise spreads by tick, and log `tick_size_change` events. Price-level features near 0.04 and 0.96 are mechanically affected.
- **Universe composition:** add an indicator for short-duration crypto markets (5-minute, 15-minute, hourly, 4-hour), which run from about 2025-10 onward. They inflate counts and trade activity, and they resolve on Chainlink TWAPs (from 08-07). They should be stratified or excluded so they do not dominate pooled samples. Repeated crypto series need market-deduplicated, dependence-aware inference.
- **On-chain parsing:** after 2026-04-28, decode trades from the V2 exchange addresses with pUSD collateral. I could not confirm the OrderFilled layout or whether tokens carried over, so check this on a small sample before pooling across the cutover. Treat NegRisk v1 and v2 adapters as separate.
- **Taker-delay regimes (crypto only):** none known before about 2025-11; then 500ms; then 250ms from about 02-25; 50ms from 08-17; 150ms from 09-04. These matter for any flow or latency feature on crypto markets.

**Still unverified:** the exact contract deployment dates (only Polygonscan's relative ages); the launch of hourly and 4-hour crypto markets; the start of the 500ms delay; the V2 OrderFilled layout and token carry-over; the start date of the dynamic-tick rule; and any liquidity-reward changes before 2026, for which nothing was found.
