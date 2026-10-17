# Creative hypotheses, round 4: where money could come from on Polymarket (2026-10-18)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-17 10:40 UTC+1,
2026-10-17T09:40Z; the file carries the round's planned date). A first attempt at this round was cut off and wrote
nothing; this file is the complete round. Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2
`CREATIVE_HYPOTHESES_2026-10-16.md` (CH35-CH59), round 3 `CREATIVE_HYPOTHESES_2026-10-17.md` (CH60-CH78); this file
starts at **CH79** and repeats none of them. Where an idea builds on an earlier one, the parent is named and the new
mechanism or data source is stated. Every number quoted from an AREPO document is a development or screen result, not
evidence. One file; no code, no queue specs, no other commits.

## 0. How to read this file

**What changed since round 3 (17 Oct results, drafts and venue facts).**
- **CB1-D (CH09) did not advance.** Under-priced neg-risk sets are more common than over-priced ones (+0.78 pp, p 0.016,
  fails the 1 pp floor and the without-top-5 check at +0.15 pp); D2 had 33 triggers in 8 events. Structural gaps exist,
  are small, and sit in a few events. Nothing here re-tests sum-of-asks states.
- **CB6's h8_tail smoke test** failed (4 of 20) and passed on v2 (20 of 20). The diagnosis is a structural fact for every
  sampling frame in this file: **94% of closed markets in the exclusion pool lived under 14 days** (539 of 573) and
  about **23% closed more than 2 days before their scheduled end**. The universe is dominated by short-lived dailies and
  games; any "life >= N days" rule is a large selection, and any window anchored on the scheduled end must check that
  the market existed and was still open.
- **CB7 (CH63, CH61, CH73) and CB8 (CH76, CH69, CH70) are drafted, challenged and in collection.** CB7 dropped CH67;
  CB8 dropped CH62, CH64, CH65, CH68, CH72, CH74, CH75 and CH78 with concrete reasons (CB7 §0.2, CB8 §0.2). None of those
  returns here in its old form; where a dropped idea's *mechanism* survives with a new source, the parent is named.
- **Cumulative test count** was 1,121 at the CB8 draft (M3). Every test here joins that denominator.
- **Venue facts verified for this round (keyless, 2026-10-17, cited in §5; counts and rule text only, no price read).**
  1. **Pyth-settled daily markets on traditional assets** exist since 2026-04-02: "Up or Down" and "close above $X"
     markets on about a dozen US equities (NVDA, TSLA, AAPL, COIN, PLTR...), equity indices, gold, silver, WTI and
     natural gas. Live rule text: resolution on the **Pyth "Close" value of the 1-minute candle for the final minute of
     regular trading**; "exactly equal" resolves No/Down; no trade in the regular session resolves 50-50; a holiday
     clause names the "most recent prior trading day"; `endDate` is 20:00Z for US equities (16:00 ET) and 21:00Z for
     XAU/USD. A CME-settled twin ("Gold (GC) Up or Down", official settlement) was listed in March. **No CB1-CB8
     population contains these markets** (CB8-B's regex is crypto/Binance only).
  2. **Combos** (parlay-style multi-leg positions) launched 2026-06-10 on sports (moneyline, spread, totals) through a
     request-for-quote gateway: 2-50 legs, BUY or SELL, a five-second acceptance window, maker "last look", signed
     Exchange v3 orders on Polygon, a Combo YES/NO position id and `condition_id` per combo. A **public, keyless
     catalogue** (`GET /v1/rfq/combo-markets`) lists each combo's `position_ids`, `outcome_prices` and `volume`.
  3. **Joint neg-risk events** ("Who wins the Senate ... and oil below $80 before the midterms?": four members, one per
     cell of a 2x2) exist; at least three among the 1,000 most active events on 2026-10-17, with the marginal markets
     listed separately. Round 3 rejected Fréchet pairs as too rare; the product now exists.
  4. **UMA's Managed Optimistic Oracle V2** (August 2025) restricts Polymarket proposals to **37 whitelisted
     addresses**; disputes remain open to anyone. Chainlink resolves the 15-minute and hourly crypto markets; Pyth the
     TradFi dailies; Binance 1-minute candles the daily crypto markets (CB8's probe).
  5. **Two 2026 papers.** Dubach (arXiv 2604.24366): trade direction inferred from Polymarket's public feed agrees with
     the on-chain `OrderFilled` record in only **about 59% of buckets** (panel mean 0.615, CI [0.58, 0.65]); the sign
     of the effective half-spread flips between feed and on-chain directions in 67% and 50% of markets in two 7-day
     windows; depth is "closer to uniform than to top-of-book"; self-counterparty (wash) share has median 1% with an
     upper tail of 22%. Le (arXiv 2602.19520, 353M trades, Kalshi and Polymarket): **persistent underconfidence in
     political markets** (prices pushed toward 50%), replicating on Polymarket. Nechepurenko (arXiv 2605.11640): public
     fills cannot identify market making; 13.4M `OrderFilled` records in 2.3 days.
  6. **External anchors probed keyless.** Deribit history lists 123,886 expired BTC options and serves hourly chart
     data for recently expired ones (85 bars over the last 7 days of a 4 Oct 2026 put); the live option chain (938
     instruments) is one request. Manifold's API is keyless (`probability`, `totalLiquidity`, `closeTime`). Metaculus
     returns 403 without a key.

**The reading that steers this round: the residuals are clues.**
- Every taker effect in AREPO dies at the same wall: about 3.5c of spread plus fee against 0.3-1c of gross (E007,
  HB1 survivors, HB2-R F4/F5). Round 2 answered "be the maker"; the open question is whether the gross itself is
  *measured* right. If the public print's side flag is wrong 40% of the time (fact 5), the flow coefficient is
  attenuated by a factor of about 2q-1 = 0.2, and the true per-unit effect could be several times what AREPO has
  measured. That is the cheapest, highest-value question in this file (CH79).
- Every carry dies on a tail or on the wait. Round 3 attacked the tail (CB6-T); this round attacks the wait (CH85:
  the proposer clock is now a 37-address object) and looks for carries whose outcome is a *public function of a public
  path* (CH83, CH84), where the tail is latency, not information.
- The venue has shipped three products that no round has seen: Pyth dailies, Combos and joint events. New products
  mean new, unsophisticated flow and new makers; the first months of a product are when its crowd is least efficient.
- The Gamma mid is not a price (J4). This round adds the mirror case: a quote that is present but empty (CH80).

**Data labels.** `A` = in AREPO's stores now: complete-universe 2h captures (touch, Gamma mid, `oneHourPriceChange`,
`last_trade_price`, `volume24hr`, `liquidity`, neg-risk ids, `closed`) with the sidecar since 11 Oct 12:00Z
(`accepting_orders`, `competitive`, `open_interest`, `clob_rewards`, `rewards_max_spread`, `rewards_min_size`,
`fee_schedule`, `uma_resolution_statuses`, `series_slugs`, `parent_event_ids`, `order_price_min_tick_size`); book sweeps
twice per pass (touch, 1c and 5c depth); trade samples (2,000 active-frame markets per pass, HMAC-hashed wallets, raw
kept 3 days); the live large-trade monitor (prints >= $1k every 5 min, hashed wallets, wallet age); the CB extract tables
(`quote_state/`, `closewin/`, `listings/`, `cdf/`, `band/`, `printflag/`, `textorig/`, `holders/`); backfills `h1`-`h3`
(worn or retired), `h5`-`h9` (sealed to their batches); pmxt v2 hourly L2 event files 2026-04-13 to 08-10 (range reads
by condition id, both clocks, `tick_size_change` events); the audited cross-venue pair history (316 clean pairs,
10-minute); the IF-H2 ladder metadata; the wallet activity cache (9,621 hashed wallets, REDEEM rows); the Wikipedia
pageviews fetcher (`fetch_pageviews`, built, exploratory, PIT rule D + 36 h); the Binance 1-minute public archive
(CB8-B, q0165). `P` = collectable read-only from public keyless sources within a week (Gamma `description`, Data API
`/trades`, `/holders`, `/activity`, Polygon public JSON-RPC receipts and logs, the Combos catalogue, Pyth Hermes and
Benchmarks, Deribit public and history endpoints, Manifold, Cleveland Fed and Atlanta Fed nowcast files, Wikimedia
pageviews). `N` = no known keyless source. **Sealed and not usable by anything here:** `h4_seal`, `h5_cb1`,
`h5_cb1_ladders`, `h6_weather`, `h7_cb4_*`, `h8_tail`, `h8_text`, `h8_geo`, the `h9_flow` HOLDOUT, CB8-B's HOLDOUT
weeks, CB8-H's windows, CB1-D's replication captures (to 2026-11-09), the E009/E010 poller (to 2026-11-03), E011 labels
(to 2026-11-11), the J4-R window (2026-10-16 to 10-21). `h2_main` is worn and `h3_power` retired. Every historical test
below names a **fresh** fetch (`h10_*`), disjoint by market id *and* event / neg-risk / series key from every prior
sample and seal copy, with rows before a declared `T_hist_end` (CB8's 2026-10-01 convention) or collected
prospectively; none is bound to the 2026-10-22 `T_seal` lane.

**Hygiene that binds every idea.** Trade before `t` (placeholder rule); scheduled anchors, never `closedTime`; event x
resolution-week clustering for carries; tightness at both ends of any mid-based target (J4-R) and print-based targets
where possible; rule text as of first sighting (`textorig`) or the clarification-marker exclusion; hashed wallets only,
never a raw address or a funding counterparty stored; the cumulative test count (M3). Category stays a parameter
(sports scope is the user's call; two ideas here are sports-heavy today and are written category-agnostic).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = an afternoon on existing data, 5 = new
collector plus weeks). My judgement, not measurements. Cost conventions as rounds 1-3: taker fee `rate*p*(1-p)` per leg
(crypto 0.07; sports 0.03-0.05; politics/finance/tech 0.04; economics/culture/weather 0.05; geopolitics 0; makers 0,
rebate 15-25% of the fee-equivalent of own fills); median spreads by price band 4.1 / 3.0 / 2.2 / 3.0 / 2.5c; liquid
(>= $100k) round trip 1.8c; median round trip 4.5c; one-leg hold-to-resolution pays the half-spread and the fee once.

---

## 1. Map: what the residuals and the new products say about where money is

| Family | What the evidence suggests | Money route |
|---|---|---|
| A. Measurement residuals | The side flag in the public record may be wrong 40% of the time; the Gamma mid can be set by an empty quote | re-measure flow with on-chain roles; price off the size-weighted touch |
| B. New products and resolution plumbing | Pyth dailies, Combos and joint events have months-old crowds; proposals come from 37 addresses; tick changes cancel quotes mechanically | model-anchored maker in path-settled dailies; parlay-leg fade; joint-marginal pairs; wait-forecast carries; re-quote after tick changes |
| C. Rule text and category calibration | Resolution standards differ (reports vs official); politics is underconfident in the literature | one-leg carries selected by text class and category x horizon |
| D. External anchors never joined | Deribit's option chain, institutional nowcasts and a play-money crowd price overlapping questions | hold-to-resolution on the side the anchor favours |
| E. Flow identity for makers | Liquidations, stop cascades, theme baskets, funding paths and attention spikes are readable from public prints and public sources before the mark-out window | maker skew, step-aside and presence filters |

---

## 2. Hypotheses

### A. Measurement residuals

**CH79. Trade-direction truth: the flow-continuation effect (E007 +0.36c; HB1 FL family +0.3 to +0.6c per SD) is
attenuated by side misclassification in the public print record; with the taker side taken from on-chain `OrderFilled`
roles the per-unit effect is several times larger, large enough to make a flow-skewed maker material and to put the
liquid-market taker version near its 1.8c round trip.**
- Mechanism: Dubach (2026) finds the public feed's inferred direction agrees with the on-chain record in about 59% of
  buckets, and that the effective half-spread changes sign between the two conventions in half to two-thirds of markets.
  If the Data API's `side` carries similar noise (symmetric with accuracy `q`), a regression of the future move on the
  observed signed flow has slope about `(2q-1)` times the true slope: at `q` = 0.6 that is 0.2, so a measured +0.36c
  per unit would be about +1.8c true. Nobody pays yet; this is a measurement. Why it persists: everyone uses the feed or
  the Data API; the on-chain join is a chore (13.4M `OrderFilled` rows in 2.3 days). The likely sources of error are
  complementary matches (a YES buy matched against a NO buy by minting has no natural "taker side" in token terms),
  match fragmentation and operator-mediated fills.
- Test. **Stage 0 (audit, `A` + `P`, one afternoon):** take 2,000 sampled prints from the trade samples or the live
  monitor (they carry `transactionHash`); fetch each receipt from a keyless Polygon RPC (`eth_getTransactionReceipt`,
  2,000 requests, under 20 MB, decode only `OrderFilled(orderHash, maker, taker, makerAssetId, takerAssetId,
  makerAmountFilled, takerAmountFilled, fee)`); the true taker side is "buy of the maker's asset" when `takerAssetId` is
  the collateral id, else "sell", with a frozen rule for mint/merge-mediated fills; compare with the Data API `side` and
  `outcome`. Primary: agreement rate with a Wilson interval, by liquidity tercile, price band and fill type. **Kill for
  the audit: agreement >= 97%** (then the Data API is near-truth and the attenuation hypothesis is dead; worth knowing
  for 2,000 requests). **Stage 1 (only if agreement < 90%):** fresh print fetch `h10_sign` (about 1,200 markets, one
  windowed Data API request each, 72-h windows before `T_hist_end`, disjoint from `h9_flow`), receipts for about 20,000
  prints (1.5 h at 4 rps), the E007/FL2 specification computed twice on identical windows (feed sides vs on-chain
  sides); target = 2h and 6h print-based move; primary = ratio of the on-chain slope to the feed slope, event-clustered
  bootstrap of the ratio. MDE: with 30,000 pairs the E007 CI width (about 0.0036 on `beta`) resolves a ratio of 2 from 1.
- Data: `A` (prints with hashes) + `P` (receipts, `h10_sign`). Disk under 100 MB.
- Economics: if the true 6h effect is 1.5-2c per unit flow in >= $100k markets, the taker round trip (1.8c) is
  borderline, not a route; the maker version (CH92) is where it pays: no fee, half-spread 0.5-1c, a 1-2c skew.
- Kill: Stage 0 agreement >= 97%; or Stage 1 ratio CI includes 1.5.
- Leakage/confound: receipts are public and permanent, no outcome is used; the E007 registered rows and the HB1 rows
  are worn and never re-read (fresh prints only); the mint/merge rule is frozen before the audit; sampled prints over-
  represent active markets (report by tercile).
- Novelty: no CH questions the sign; the UNUSUAL_FLOW, HB and E007 work all take `side` as given. N 5, EV 4, C 1-2.

**CH80. Dust-anchored midpoint: a large share of two-sided markets have a best bid or ask whose size is below the
venue's minimum order (a residual from a partial fill), so the Gamma mid, `oneHourPriceChange`, the UI movers lists,
reward-bot centring and every mid-based AREPO target are set by an order nobody can trade against; the size-weighted
touch (first level with >= 5 shares) is the real price, the dust-vs-real gap predicts where the next print lands, and
reward quotes centred on the dust mid are executable against the real value.**
- Mechanism: new orders need `orderMinSize` (5 shares) but partial fills leave residuals of any size; the public best
  bid/ask ignores size. J4 found the wide state (a side absent) displaces the mid by about 10c; this is the mirror: a
  side present but empty. Who pays: takers who trade off the displayed mid (a market order sweeps the dust and fills at
  the real level), alert bots keyed on `chg_1h`, and reward bots whose "midpoint" is the dust mid, which places their
  far-side quote inside the real value. Why it persists: nobody cleans residuals; the displayed price is the product.
- Test (`A`): pmxt full-depth books (2026-04-13 to 08-10; level sizes are stored) for about 1,000 markets disjoint from
  every prior pmxt pull (range reads, 2-4 GB ingress); unit = market-hour with a two-sided book; dust state = best level
  size x price < $1 or size < 5 shares; feature = dust mid minus size-weighted mid; target 1 (mechanism) = which mid the
  next print price is closer to (one-sided: the size-weighted mid), target 2 = 2h print-based mark-out of a paper taker
  who trades at the "stale" far-side reward quote when it lies through the size-weighted fair by > 1c; descriptive =
  share of market-hours in the dust state by liquidity and the share of `chg_1h` moves attributable to dust changes.
  Live check: sweeps store touch and 1c/5c depth; add the touch size to the sweep row (one field) for the prospective
  version. Cluster by market x day; J4-R increment-shuffle placebo for any mid-based quantity.
- Economics: route 1 is cost-side (never trade off a dust mid; every mid-based test in AREPO gains a filter); route 2 is
  a taker at a mis-centred quote: gross 1-3c, fee `rate*p*(1-p)`, no spread paid if the quote is through fair; capacity
  is the resting size of the mis-centred order.
- Kill: dust state under 5% of two-sided market-hours; or the size-weighted mid no better than the dust mid at
  predicting the next print; or fewer than 1 executable through-fair quote per 200 market-hours.
- Leakage/confound: none for the mechanism (public books); dust orders may be deliberate probes (informed); the
  reward "midpoint" definition is the docs' and may already exclude dust (check first; if it does, route 2 is dead and
  route 1 stands).
- Novelty: CH35 (vacated side), CH20 (round-number walls), CH36 (footprints). The present-but-empty state is new, and
  the methods payoff applies to J4, J5, E004 and every Gamma-mid target. N 4, EV 2, C 1.

### B. New products and resolution plumbing

**CH81. Joint-event implied correlation: in the new joint neg-risk events (Senate control x oil price, four cells), the
cells are priced by narrative while the two marginals are priced separately by bots, so (a) the row and column sums
violate the standalone marginal prices by more than the fee band, which is a riskless pair, and (b) the implied
correlation between the components is extreme relative to any frozen historical co-movement, so the cells that carry
the narrative resolve below their price.**
- Mechanism: a 2x2 joint event has three free parameters; two are pinned by the marginal markets, leaving only the
  correlation. "Democrats win and oil spikes" is a story; the standalone "oil above $85 on Nov 2" is a hedge for
  commodity people. Who pays: narrative buyers of the story cell. Why it persists: no page shows the joint event next to
  its marginals; a four-leg taker pays about `rate*(1 - sum p^2)` in fees (2-3c), so only makers close small gaps.
- Test (`A` + `P`): census first: a frozen title rule ("and" joining two clauses; outcome names containing ";") over
  every capture for three weeks, plus one Gamma text fetch per candidate (about 50 requests). **Kill at the census:
  fewer than 10 joint events with both marginals listed and rule-identical** (then record and stop). Otherwise unit =
  joint-event capture; features = `sum ask(row) - bid(marginal)` and the reverse for each row and column; implied
  correlation `rho` from the four mids; targets = persistence of executable violations (next capture and sweep pair),
  the realised pair payoff at the later resolution, and (b) the resolution excess of the high-`|rho|` cells; cluster by
  joint event x day (few clusters: declare the MDE honestly, it is descriptive below 10 events).
- Economics: pair legs as maker (fee 0) or taker in zero-fee geopolitics; hold to the later resolution (weeks).
- Kill: census floor; or violations under 1% of event-captures; or an inconsistent-resolution rate (joint vs marginal
  rules diverge) above the mean gap.
- Leakage/confound: marginal and joint rules differ subtly (the probe found "oil below $80 before the midterms" next to
  "oil at least $85 on November 2": not the same event); only rule-identical pairs count; augmented events excluded.
- Novelty: round 3 rejected Fréchet pairs as too rare; CH13/CH59 are date and bucket ladders; the joint product is new.
  N 4, EV 2, C 1.

**CH82. Combos: the public catalogue prices the retail parlay markup, popular parlay legs are overpriced in their own
books, and combo fills create uninformed hedge flow in the legs.**
- Mechanism: parlays are the retail product of sportsbooks and are overpriced on Kalshi (Moshrefi). Polymarket's Combos
  are quoted by RFQ makers who hedge each sold combo by buying the legs in the order books; the combo's own price is
  public (`outcome_prices` on the catalogue) as is its `volume`, so three things are measurable without seeing a single
  RFQ: (i) the premium of the combo YES price over the independence product of the leg mids (or over the Fréchet upper
  bound for same-game legs); (ii) which legs are *popular* in combos (volume-weighted leg appearance); (iii) leg-book
  taker buys that follow combo volume increments within a minute (the hedge). Who pays: parlay buyers (the markup) and,
  through the hedge, the leg-market price. Why it persists: the product is four months old; its makers are few; the leg
  overpricing is small per leg and spread over hundreds of games.
- Test (`P`, cheap): poll the catalogue hourly (cursor pages of 100, about 10-50 requests per hour, a few MB per day);
  map `position_ids` to leg markets via Gamma `clobTokenIds` (a few hundred requests once); leg prints for popular legs
  from the Data API (optional, about 2,000 requests per day). Unit = combo-hour and leg-day. Primary 1 (descriptive):
  premium distribution by number of legs and same-game flag. Primary 2 (route): leg "parlay popularity" (24h combo
  volume increments in which the leg appears, scaled by the leg's own 24h volume) against the leg's resolution excess
  (payout minus ask; one-sided: popular legs resolve below price) and its 24h print-based move; cluster by game day.
  Secondary (hedge flow): same-direction leg prints inside 60 s of a combo volume increment and their 2h mark-out
  (uninformed: reverts).
- Economics: maker ask on popular legs (fee 0, half-spread about 1c in liquid game books) or NO taker (sports fee 0.03-
  0.05 x p(1-p) <= 1.25c); needs leg overpricing >= 2c. Capacity: liquid game markets, so real size.
- Kill: mean premium <= 0 (then makers are not charging a markup and the leg mechanism has no fuel); or popularity slope
  CI includes 0 at an MDE of 1.5c with about 2,000 leg-days; or hedge-flow mark-outs not negative.
- Leakage/confound: catalogue `outcome_prices` may be indicative, not executable (use them only as a markup proxy);
  `volume` is cumulative (use increments); leg prices as of `t`; combos are sports-only today, so **this is
  sports-scoped until the product expands** (written category-agnostic: any combo-enabled category).
- Novelty: Combos post-date rounds 1-3; CH29 (closing line) is the only sports pricing idea so far. N 5, EV 3, C 2.

**CH83. Pyth-settled TradFi dailies: the outcome is a public function of a public, keyless, real-time price path, so
(a) in the first hour after the equity open the "Up or Down" price under-reacts to the opening gap, (b) in the last
minutes before the close the winning side's ask stays below fair when the path has made it near-certain, and (c) on
NYSE early-close days (13:00 ET) the outcome is fixed three hours before the market's 16:00 ET `endDate`, leaving a
live book with a known answer.**
- Mechanism: a daily "Up or Down" on NVDA is a digital option on the close relative to yesterday's close; its fair
  value at any minute is a known function of (price now minus strike, minutes left, intraday volatility), all public via
  Pyth's own feed (Hermes, keyless, sub-second). Retail prices it by feel; many free quote pages are delayed; the crowd
  is six months old. Early-close days are rule-text facts ("final minute of regular trading") that the `endDate` field
  does not reflect. Who pays: retail directional traders in dailies; on half days, anyone quoting after 13:00 ET.
- Test (`A` for history, `P` for the rest): frame = Gamma closed markets with `resolutionSource` containing
  `pythdata.app` since 2026-04-02 (about 200 requests); pmxt range reads for the hours 13:30-14:30Z and 19:30-20:00Z
  of each market-day (about 1,300 market-days to 08-10; 5-8 GB ingress); the Pyth path from Benchmarks (one request
  per timestamp covers all feed ids; about 1,500 requests) with the strike from the previous session's final-minute
  close. Units and primaries, one Holm family of three: (a) at 09:45 ET, fair value from a frozen lognormal digital
  (intraday sigma from the prior 20 sessions) versus the recorded touch, target = settlement minus ask on the model's
  side when |fair - mid| > 5c; (b) at T-5 and T-1 minutes, 1 - ask(winning side by a 3-sigma condition) minus fee,
  with depth; (c) prospective: the 2026-11-27 and 2026-12-24 sessions (about 15 markets each), any ask < 0.97 on the
  certain side between 13:00 and 16:00 ET, recorded from the live book poll (1 request per minute per market).
  Cluster by session day. MDE: (a) about 1c on net with 400 market-days at SD 10c; (b) 0.3c with 300 market-days.
- Economics: taker; finance fee 0.04 x p(1-p) (0.19c at 0.95, 1c at 0.5); tick 0.001 above 0.96; gains of 1-4c in (b)
  and 5-15c in (a) if the under-reaction is real; capacity = displayed depth; latency is minutes, not milliseconds,
  except in the final minute.
- Kill: (a) net <= 0 after fee; (b) mean gap <= 0.5c at T-5; (c) no stale ask on either half day (then recorded as a
  two-day descriptive, not a null).
- Leakage/confound: the sigma condition and the fair value use Pyth prices before `t` only; pmxt venue vs receipt
  clocks; the "final minute of regular trading" must be parsed per market (half-day rule); the Pyth 1-minute "Close"
  can differ from the official auction close by cents (coin-flip strikes excluded by the 3-sigma rule); **do not pool
  with CB8-B** (crypto, Binance; its verdict on terminal minutes is independent, because the retail quote-delay
  argument is specific to equities).
- Novelty: CH30 (15-minute crypto digital, never tested), CH76/CB8-B (Binance terminal minutes). The TradFi family, the
  open-gap clock and the early-close window are new. N 3, EV 2, C 2.

**CH84. Model-anchored maker in path-settled dailies: in every market whose payoff is a public function of a public
price path (Pyth TradFi dailies, Chainlink hourly crypto, Binance daily crypto, the 15-minute crypto markets whose
taker fees fund maker rebates), a two-sided quote centred on a frozen digital-option value with a model-based width,
rather than on the book's mid, earns the spread from directional retail with adverse selection bounded by latency, and
is net-positive after the rebate where the mid-centred maker is not.**
- Mechanism: in ordinary markets the maker's enemy is private information; in path-settled dailies there is none, only
  public information arriving continuously. A maker who centres on the model is adversely selected only by takers who
  are faster than the model's refresh (seconds) and by sigma misestimation; a maker who centres on the mid is adversely
  selected by every retail trader who looked at the chart. The venue pays maker rebates funded by taker fees (crypto
  15-minute markets since January 2026) and the dailies are the highest-turnover product on the venue. Who pays:
  directional retail in dailies; why it persists: bots do this in the busiest crypto windows, but the TradFi dailies
  are six months old and the hourly crypto markets are thinner than the 15-minute ones.
- Test (`A` + `P`): population = pmxt books of Pyth TradFi dailies and Chainlink hourly crypto markets 2026-04-13 to
  08-10 (**disjoint from CB8-B's daily Binance population by regex**), prints from the Data API (about 1,300 + 2,000
  requests); paper maker at 5-minute origins: quote = model value +/- w, w = max(1 tick, k x model sigma over the
  refresh interval) with k frozen; fills by the queue rule against prints; mark-out = settlement value (a public
  function; no outcome field read, the kline/Pyth path gives it) minus fill price, plus the rebate at the documented
  category share; baseline = the same quote centred on the book mid. Primary: net per posted quote, model-centred minus
  mid-centred, clustered by session day; secondary: fill rate and the share of fills within 30 s of a 1-sigma path
  move (the latency tail). MDE: about 0.3c per posted quote with 20,000 quote-origins.
- Economics: maker; fee 0; rebate 20% (crypto) or 25% (finance) of the fee-equivalent of own fills; gross = half-width
  (1-2c) on retail fills minus the latency tail; the 15-minute variant is `N` in AREPO's 2h stores and needs a
  WebSocket poller (`P`, keyless, cheap) and is competed by sub-second bots, so it is the last to test.
- Kill: model-centred minus mid-centred net CI includes 0 at the MDE; or the fill rate under 2% of quote-origins; or
  the latency-tail share of losses above 80% (then it is a speed game, out of scope).
- Leakage/confound: the model uses the path before `t` only; sigma from prior sessions; pmxt hourly files are event
  streams so the book at any minute is reconstructable (HISTORICAL_SOURCES §a); never reuse CB8-B's market-days.
- Novelty: CH30, CH76, CH83 are taker clocks; CH16/CH45 are reward geometry; CH43 a risk filter. A model-centred maker
  in the one market class where fair value is computable is new. N 3, EV 3, C 2.

**CH85. Whitelisted-proposer clocks: since UMA's managed oracle limited Polymarket proposals to 37 addresses, the
time between an outcome becoming public and the on-chain proposal is a function of a few proposer bots' schedules
(hour, category, batch cadence), learnable from on-chain history; the decided carry's annualised return (CB1-A2's
`R_ann` -32.7% killer) is therefore forecastable, and the right carry population is "decided, proposer due within N
hours".**
- Builds on CH01/CH02 (which decide by price or by the proposal itself) and on round 3's rejected "proposer-activity
  clocks" note; what is new is the whitelist fact (a small, fixed, identifiable set of proposers since August 2025),
  which makes the wait a modelled quantity rather than a covariate, and the target is the wait, not the gap.
- Mechanism: the 2h liveness is fixed; the proposal lag is the variable part of the wait, and it is set by when the
  proposers' operators or bots run. A carry entered when the proposer is due is a 3-hour lock; entered at the wrong
  hour it is a 30-hour lock for the same 1-2c. Who pays: nobody directly; the carry pays by not locking capital.
- Test (`P`): keyless Polygon logs of the Managed Optimistic Oracle V2 `ProposePrice` events (topic filter, 2,000-block
  windows, about 3,000 requests for three months, under 100 MB), decoded to proposal time, proposer (hashed in
  storage), ancillary data (question id -> market via Gamma). Unit = market with a proposal; features at `t` (the
  scheduled end, or the first capture with the mid >= 0.97 after it) = hour of day, weekday, category, the proposer
  set's historical median lag for that category (fitted on proposals before `t`); target = proposal time minus `t`;
  primary = out-of-sample MAE of the wait forecast versus a category-median baseline (one-sided: 20% better);
  secondary = the paper carry (CB1-A2 machinery on fresh markets, `h10_wait`, disjoint from h2/h5) restricted to
  predicted wait < 6h: annualised net with the CB1 tail gate.
- Economics: entry at an ask >= 0.97 (half-spread 0.1-0.5c, fee about 0.1c), hold hours; 0.5c net in 6h is about 30%
  annualised on tiny size; depth at the ask bounds it.
- Kill: MAE improvement under 20%; or the short-wait carry net <= 0 after the tail gate.
- Leakage/confound: "decided" must come from the scheduled end or the price, never from the proposal; proposer
  addresses are public but are stored hashed; CB1-A's h2 units are worn and not reused.
- N 3, EV 2, C 2.

**CH86. Tick-change vacuums: when a market's mid crosses 0.96 or 0.04 the tick changes between 0.01 and 0.001
(`tick_size_change` events in pmxt; CB2 verified the regime map), resting orders at now-invalid prices are cancelled
or orphaned, so the book thins mechanically at a known trigger; the vacated side's fair value is unchanged (the trigger
is a price-grid event, not news), and a re-quote at the old touch is filled by the next retail print at the old
half-spread plus the gap.**
- Builds on CH35 (quote vacuums, CB3-A) with a *named mechanical cause* that carries a feed timestamp; CB3-A tests
  vacuums generically on 2h captures.
- Mechanism: bots quote on the coarse grid; after the change the fine grid lets anyone penny-jump by 0.1c, and the
  bots' own stale coarse orders are removed; recovery waits for the next bot cycle. Who pays: takers who arrive during
  the thin window; why it persists: the event is rare per market (a few times in a life) and nobody watches for it.
- Test (`A`): pmxt `tick_size_change` events (2026-04-13 to 08-10) for all markets in a fresh pmxt pull (range reads by
  condition id; about 2 GB); unit = tick-change event; targets = depth within 1c and 5c of the mid at -1, +1, +5, +30
  minutes (one-sided: a drop at +1 that recovers by +30), the mid displacement at +1 versus the pre-event mid, and the
  paper re-quote (CB3-A's A2 rule) filled by prints in the next 30 minutes, marked at the +30 mid; cluster by market x
  day; placebo = the same statistics at random times in the same markets at the same price level (the level matters:
  0.96 is also the reward-shadow edge, CB6-R, so the placebo must be at-level).
- Economics: maker, fee 0; 0.5-2c per filled share; events are a few hundred per month across the universe.
- Kill: no depth drop at +1 (ratio > 0.8 of pre-event depth) or no recovery by +30; or fills under 2% of events.
- Leakage/confound: CB6-R's 0.90 discontinuity and the extreme-price fee valley (CH72, dropped) are nearby; the
  at-level placebo separates them; venue vs receipt clocks.
- N 3, EV 2, C 1.

### C. Rule text and category calibration

**CH87. Reporting-standard premium: markets whose rules resolve on "consensus of credible reporting" pay on the
*report*, so YES resolves more often than the physical event occurs (false or early reports count; retractions often do
not un-count), while markets with an "official source" standard pay on the event; at the same price and category, the
report class resolves YES more often, and NO buyers who price the event pay for the difference.**
- Builds on CH63 (condition count, CB7-S) and CH64 (twins, dropped); the object here is the *resolution standard*, a
  different text feature with a directional prediction.
- Mechanism: the standard is an asymmetric filter: a report can trigger YES without the event; a missing report only
  delays NO. The crowd prices "will it happen"; the rules pay "will it be reported". Who pays: NO buyers in
  report-standard markets. Why it persists: the standard is boilerplate nobody reads, and the base rate of false or
  premature reports is small but not zero (deaths, resignations, strikes, ceasefires).
- Test (`A` prospective + `P` historical): prospective: the CB7 `textorig` table already stores rule text at first
  sighting; add a frozen regex class (report standard: "consensus of credible reporting", "credible reports"; official
  standard: "official", "as published by", "according to <named source>"); unit = market at 7d and 1d before the
  scheduled end with a trade before `t`; primary = resolved-YES rate minus price, report class minus official class,
  within price band and category; cluster by event x resolution week. Historical: `h10_std`, about 5,000 resolved
  non-sports markets with `description` (about 10,000 requests, 100 MB), disjoint from `h8_text`. MDE about 3c on the
  class difference with 1,500 markets per class.
- Economics: YES taker in report-class markets at 7d: fee 0.04-0.05 x p(1-p) (<= 1.25c), half-spread 1-2c; a 3c gap
  clears, a 1c gap does not; a maker bid is fee-free. One leg, hold to resolution.
- Kill: class difference <= 1c or reversed; or the classes are collinear with category (report standard = geopolitics)
  such that the within-category estimate has fewer than 300 markets per class.
- Leakage/confound: current-text clarifications (use `textorig` or the clarification-marker exclusion); category and
  price-band controls mandatory; the `h8_text` sample is CB7-S's and is never reused.
- N 4, EV 2, C 2.

**CH88. Political underconfidence carry: in political markets the price is compressed toward 0.5 at horizons of weeks
to months (Le 2026, replicating on Polymarket), so the favourite at 0.60-0.85 with 30-120 days to the scheduled end
resolves YES more often than priced, and a one-leg hold on the favourite earns the compression.**
- Mechanism: Page and Clemen's abstention argument plus the retail taste for contrarian political bets; AREPO's own
  PX2/PX4 found no favourite excess *pooled at 24h and at mid >= 0.85*, which does not test the category x long-horizon
  cell where the literature finds the effect. Who pays: contrarian buyers of the political underdog. Why it persists:
  the carry is long (months), the annualised number is modest, and the political crowd is the largest and most
  opinionated on the venue.
- Test (`P`): `h10_pol`, resolved politics-tagged binary markets with scheduled life >= 60 days (about 4,000 markets,
  8,000 requests, 80 MB; disjoint from h2/h3/h8_text/h8_geo by key); origins at 90, 60 and 30 days before the scheduled
  end with a trade before `t`; primary = calibration slope (logit of resolved-YES on logit of price) in politics minus
  the same in a matched non-politics set at the same horizon (one-sided: slope > 1 in politics), and the net of buying
  the favourite at the recorded ask held to resolution; cluster by event x resolution week (elections are one cluster:
  declare the cluster count honestly; one election cycle can dominate). MDE about 4 points on the slope with 1,500
  origins per arm.
- Economics: fee 0.04 x p(1-p) (about 0.9c at 0.7), half-spread 1-1.5c, one leg; a 0.70 favourite that is really 0.78
  pays about 6c net over 2-3 months, roughly 30-40% annualised gross on 0.70 of capital; if the compression is 3
  points it does not clear the hurdle at 30 days and barely at 90.
- Kill: slope not above 1 in politics at 60 and 90 days; or the carry net <= 0 after the tail gate; or the effect
  confined to one election cluster.
- Leakage/confound: survivorship of Gamma listings; placeholder prices (trade before `t`); `endDate` errors in politics
  (set loosely); the published finding is on Kalshi primarily and "replicates" on Polymarket in the author's words,
  which is a prior, not a result here.
- Novelty: low against the literature (N 2), new as a category x horizon carry in AREPO. EV 3, C 2.

### D. External anchors never joined to Polymarket

**CH89. Option-implied anchor for crypto strike ladders (Deribit): the risk-neutral digital probability of BTC or ETH
finishing above a strike, read from Deribit's public option chain and haircut by a frozen variance-risk-premium rule,
predicts the resolution excess of Polymarket "above $K on/by date" markets beyond the Polymarket price; the gap is a
one-leg carry that persists because the two crowds do not overlap and the 7% crypto taker fee stops takers closing
small gaps.**
- Mechanism: Deribit is the deepest crypto option venue; a strike ladder on Polymarket is a retail CDF (CH78's
  round-strike bump, dropped, was a within-ladder symptom). The option chain implies the whole distribution at each
  expiry; the known bias (Q-measure tails too fat) is a frozen, pre-sample adjustment. Who pays: Polymarket buyers of
  far strikes (lottery) and sellers of near ones.
- Test (`P`): prospective: hourly poll of `get_book_summary_by_currency` for BTC and ETH (2 requests per hour, about
  5 MB per day); historical: `history.deribit.com` hourly chart data per expired instrument (probed: 85 hourly bars over
  the last 7 days of a 4 Oct 2026 put; trades are sparse, so use marks), about 10 instruments per expiry, 1,000
  requests for six months; Polymarket side: a fresh crypto strike-ladder walk (Gamma metadata plus prints at origins,
  about 2,000 requests; CB5-L's `cdf/` extract is sealed and not reused). Unit = strike-market origin (daily, >= 2 days
  before resolution, trade before `t`); feature = `P_Q_adj(S_T > K)` interpolated to the market's strike and
  resolution time from the two nearest expiries, with a frozen rule for "by date" (barrier) versus "on date"
  (European) markets (barrier markets excluded in v1); primary = slope of (payout minus price) on (`P_Q_adj` minus
  price), clustered by asset x expiry; economic = one-leg carry at the recorded ask when |gap| > 4c. MDE about 0.3 on
  the gap-to-excess slope with 600 origins.
- Economics: crypto taker fee 0.07 x p(1-p) (<= 1.75c), half-spread 1-2c; needs a gap above about 3.5c as taker and
  1.5c as maker; holds of days to weeks.
- Kill: slope CI includes 0; or carry net <= 0 after the tail gate; or fewer than 200 origins with a Deribit expiry
  within 3 days of the Polymarket resolution.
- Leakage/confound: Deribit marks as of `t` (venue clock); the VRP haircut frozen from pre-sample data; settlement basis
  (Deribit index at 08:00 UTC versus Polymarket's Binance 12:00 ET candle or other source): the time and price basis
  must be modelled or the sample restricted to same-day expiries.
- Novelty: CH30, CH78, CH13 use internal consistency or Black-Scholes on spot; an external options market is new. N 4,
  EV 3, C 3.

**CH90. Institutional nowcast anchor for macro bucket ladders: for CPI, PCE, payrolls and GDP bucket events, the
public nowcast (Cleveland Fed inflation nowcast, daily; Atlanta Fed GDPNow; both keyless files) with the series'
pre-sample nowcast-error distribution gives bucket probabilities sharper than the Polymarket bucket prices at 1-7 days
before release, and the nowcast-favoured bucket resolves more often than priced (the weather-favourite structure of
CH27 in a second domain).**
- Mechanism: bucket events invite spreading; the nowcasts are the professional consensus for the current print;
  buckets are 0.1-point wide and the Cleveland nowcast's monthly CPI error is of that order. Who pays: bucket
  spreaders and "surprise" buyers. Why it persists: economics markets are small and few (about 600 a year in the resdev
  frame); nobody bothers to wire the nowcast.
- Test (`P`): nowcast vintage files (2 downloads; vintages carry their publication dates); `h10_macro`, resolved
  economics bucket events whose rules name a release (frozen regex), about 500 Gamma requests and 1,000 print requests;
  origins at release - 7d and - 1d; feature = normal bucket probability from the nowcast as of `t` and the pre-sample
  error SD; primary = log-loss gain over the market price per bucket event and the net of buying the nowcast-favoured
  bucket at the recorded ask (trade before `t`); cluster by release (one release = one cluster; expect 60-100 releases
  across series in a year, so the MDE is about 4c on net).
- Economics: economics fee 0.05 x p(1-p) (<= 1.25c); half-spread 2-3c (thin); needs a 4c gap; one leg, hold a week.
- Kill: no log-loss gain; or net <= 0; or fewer than 40 resolvable releases.
- Leakage/confound: nowcast vintages as of `t` only (never the final nowcast); releases shared across markets (one
  cluster); CH75 (first-print revisions, dropped by CB8 as implausible and key-needing) is a different object: this is
  the forecast, not the revision, and needs no FRED key.
- Novelty: CH31 (FedWatch), CH28 (release clock), CH75 (revisions). N 3, EV 2, C 2.

**CH91. Play-money crowd anchor (Manifold): on questions listed on both venues, the Manifold probability (keyless API)
carries information about Polymarket's resolution beyond Polymarket's own price, most in long-dated, thin Polymarket
markets where abstention pulls prices toward 0.5; the signed gap predicts Polymarket's resolution excess.**
- Mechanism: a different crowd (forecasters; no capital cost, no fees, no KYC) with different biases; on a thin
  long-dated Polymarket market the price is a few opinions plus a placeholder, while Manifold often has a larger
  forecaster crowd on the identical question (AI, science, politics). Who pays: thin-market quoters on Polymarket.
  Metaculus would be the better anchor but needs a key (403 unauthenticated today); Manifold is keyless.
- Test (`P`): a title matcher (the cross-venue matcher's rules, frozen; hand audit of every pair; expect 100-300
  pairs), a daily Manifold poll (one request per 100 markets), Polymarket mids from captures (`A`). Unit = pair-day at
  origins >= 7 days before resolution; primary = slope of Polymarket's resolution excess (payout minus mid) on (Manifold
  p minus Polymarket mid), event x resolution-week clustered; placebo = sign-shuffled gaps; secondary = Polymarket's 7d
  mid change toward Manifold.
- Economics: one-leg hold at the ask; fee 0.04 x p(1-p); half-spread 2-3c in thin markets; needs a 4c gap; capacity
  tiny (thin markets): this is information more than money, and a cheap check on the "price is a few opinions"
  reading of the long tail.
- Kill: slope CI includes 0 at MDE 0.25; or fewer than 60 resolved pairs in three months.
- Leakage/confound: Manifold markets can be created after news (use prices as of `t` only); creator-resolved
  questions diverge from Polymarket's rules (exclude by text); the matcher is frozen before any price is read.
- Novelty: CH25/CH38/CH73 use Kalshi (money); a non-money crowd is new. N 3, EV 2, C 2.

### E. Flow identity for makers (new signatures from public prints and public chains)

**CH92. Flow-skewed quoting in the F4/F5 cells: the replicated flow moderators (continuation stronger in volatile and
wide-spread markets, HB2-R) are exactly where the maker's half-spread exceeds the signal; a two-sided quote shifted by
a fraction of the frozen flow prediction keeps the spread income and converts the 1c continuation from a taker loss
into a maker gain, so the skewed maker is net-positive in those cells where the unskewed maker is not.**
- The direct maker dual of E007/HB2 (CH39/CH40/CH41 are presence filters; CH73 skews on Kalshi; CH24 on attention
  days); it has not been proposed. Its value doubles if CH79 shows the true flow effect is larger.
- Mechanism: a maker with a signed-flow forecast of +1c moves both quotes up by `k` x 1c (k frozen at 0.5): the bid
  side is now filled by sellers at a price that will drift up (gain), the ask side by buyers at a higher price (less
  adverse selection), and the spread income is unchanged. Who pays: the uninformed half of the flow; why it persists:
  reward bots centre on the mid.
- Test (`A` + `P`): pmxt books for about 800 markets disjoint from every prior pmxt population (CB3-B, CB1-C, CB4-N,
  CB8-B), 6h-grid origins 2026-04-13 to 08-10 (about 5 GB ingress), prints from the Data API (1,600 requests; sides as
  the Data API gives them, with the CH79 caveat); the CB3-B paper-maker machinery (queue-rule fills, 2h mark-out);
  rule = HB2's frozen flow feature at the origin; compare the skewed and unskewed quotes' net per posted quote in the
  F4 (top volatility tercile) and F5 (top spread tercile) cells versus the rest; event x day clustered. MDE about 0.4c
  per posted quote with 15,000 quote-origins.
- Economics: maker; fee 0; rebate; gain = captured continuation (about 1c) on the fills that remain plus avoided
  adverse selection; cost = fewer fills on the skewed-away side.
- Kill: skewed minus unskewed net CI includes 0 at the MDE; or the unskewed maker is already positive in those cells
  (then the skew is unneeded and the result is CB3-B's).
- Leakage/confound: flow computed from prints before the origin; hourly pmxt books limit fill realism (as ECONOMIC
  CONDITIONS part B); the skew must not be re-tuned (k frozen).
- N 2-3, EV 3, C 2.

**CH93. Stop-cascade fades at round-level breaks: when a print crosses 0.25, 0.50, 0.75 (or 0.10/0.90) for the first
time in 24 hours, third-party stop and alert tools fire market orders in the break direction within minutes; those
post-break prints have negative mark-outs, larger than same-size prints elsewhere and larger than at pseudo-levels, and a
maker quote posted one tick beyond the level against the break is net-positive.**
- Builds on CH20 (resting depth at round levels: the maker side of round numbers); this is the taker cascade after a
  break, with a placebo that CH20 lacks.
- Mechanism: Polymarket has no native stop orders; copy and alert tools implement "sell if below X" with round defaults
  and retail anchors at round prices; the cascade is price-triggered, not news-triggered. Who pays: stop users.
- Test (`A` + `h10_sign` prints): unit = break episode (first print-confirmed crossing of a round level in 24h,
  >= 3 prints in the prior 24h); primary = print-based mark-out at +30 min and +2h of prints in the 10 minutes after the
  break, in the break direction, versus matched prints (same market, same size band, no break) and **versus the same
  statistic at pseudo-levels (0.23, 0.48, 0.73)**: the pseudo-level contrast is the test, because a generic post-move
  reversal is E004/J4 bounce. Economic = paper maker one tick beyond the level, filled by the cascade, exit at the 2h
  mid or hold. Cluster by market x day; J4-R increment shuffle for the mid-based secondary.
- Economics: maker; fee 0; 1-3c per filled share; episodes are frequent (hundreds per day across the universe).
- Kill: real-level reversal not larger than pseudo-level reversal (difference CI includes 0 at MDE 0.5c).
- Leakage/confound: the crossing must be print-confirmed, never a Gamma-mid crossing (dust and vacuum artefacts,
  CH80/CH35); level breaks coincide with news in a share of cases (the pseudo-level placebo handles the generic part;
  news-driven breaks make the test conservative).
- N 3, EV 2, C 1.

**CH94. Account-exit sweeps: a wallet that sells every position it holds across three or more unrelated events within
15 minutes is liquidating, not informing; its sells hit thin bids and revert; a maker bid one tick above the first hit,
filled by the sweep's later clips, is net-positive.**
- Builds on CH66 (conversion sells within one event, CB6-N), CH68 (post-redemption redeployment, dropped) and CH69
  (worked orders, CB8-W); the new object is the cross-event liquidation signature.
- Mechanism: exits are driven by cash needs or account closure; the portfolio page makes "sell all" one click; the
  sells are same-wallet, same-direction, across structurally unrelated events (different parent events and categories)
  in minutes. Who pays: the exiting user (spread and impact on thin bids).
- Test (`A` + `P`): the live monitor and trade samples give hashed wallets now; history from `h10_exit` (prints with
  hashed wallets for about 1,500 markets x 72h windows, disjoint from `h9_flow`; 1,500 requests, 150 MB). Unit = sweep
  episode x market; primary = print-based mark-out at +30 min and +2h of the sweep's sells versus size-matched sells by
  other wallets in the same market-hour (reversal, one-sided); economic = paper bid one tick above the first hit, filled
  by the next clip, marked at the 2h mid. Optional confirmation: an outbound USDC transfer from the proxy wallet within
  24h (keyless RPC, one request per episode; the class is stored, never the address). Cluster by wallet x day.
- Economics: maker; fee 0; 1-3c on thin members; capacity small per episode; frequency unknown (census first).
- Kill: fewer than 200 episodes in the sample; or mark-out difference CI includes 0 at MDE 0.5c.
- Leakage/confound: "unrelated events" is structural (parent event, neg-risk id, series, category), never price-based;
  a sweep across *related* markets is a theme trade (CH95), excluded; hashed wallets only.
- N 4, EV 2, C 2.

**CH95. Theme-basket buys as the maker's informed-flow signature: a wallet that buys YES across three or more markets
of one frozen keyword theme (different events) within 10 minutes is acting on a view about a common driver; such basket
buys have positive mark-outs (informed), and a maker who sees the second leg steps aside on the theme's remaining
markets; single-market buys of the same size are not informed.**
- Mechanism: the case catalogue's informed episodes spread across sibling and thematic markets; the basket is a
  signature readable from public prints (hashed wallet plus theme) before the mark-out window. Who pays: the maker who
  does not step aside. Honest label: a wallet-family idea; WA1-WA8 tested wallet *direction*; this is a cost-of-fill
  filter keyed on a cross-event pattern, not on age or records.
- Test (`A` + `h10_exit` prints): theme map frozen from question text (keyword clusters hashed before any mark-out);
  unit = basket episode; primary = 2h and 24h print-based mark-out of basket buys versus size-matched single buys
  (one-sided positive); secondary = the mark-out of *other* theme markets in the next hour (does the basket predict a
  theme-wide move?). Cluster by theme x day. MDE about 1c with 500 episodes.
- Economics: maker step-aside on the theme (avoided loss); a taker follow is excluded by the 3.5c hurdle unless the
  theme-wide move exceeds 5c (reported, not routed).
- Kill: basket mark-out not larger than single-buy mark-out at the MDE.
- Leakage/confound: never run on the case catalogue's events (the detector's held-out set); the live monitor's size
  bias (>= $1k); a basket can also be a farmer's rotation (CH41-narrow's round-trip rule as a control).
- N 3, EV 2, C 2.

**CH96. Funding-path class for maker protection: fresh wallets whose first USDC inflow came through a bridge or an
unlabelled route have far worse maker mark-outs on their first buys than fresh wallets funded from a labelled exchange
hot wallet; the class is readable on chain before the first trade settles and gives the maker a step-aside rule that
wallet age alone (null three times) does not.**
- Mechanism: ordinary onboarding is an exchange withdrawal; the catalogue's informed fresh wallets were "funded within
  24h", often by bridges. Age is identical; the path differs. Who pays: informed takers avoided; ordinary fresh retail
  kept.
- Test (`P`): for hashed fresh wallets (age < 7d) seen in the monitor or samples, read the proxy wallet's first inbound
  USDC `Transfer` log (keyless RPC, 1-3 requests per wallet, about 2,000 wallets) and classify the sender against a
  frozen public label list (exchange hot wallets, bridge contracts, "other"); **only the class is stored, in memory the
  address is discarded** (the HMAC rule). Unit = fresh-wallet first-24h buy; primary = paper maker mark-out at 2h/24h
  by class, event-clustered; secondary = resolution excess of those buys. MDE about 1c with 1,500 prints.
- Economics: maker step-aside; avoided loss on a small share of volume; forgone spread small.
- Kill: class difference CI includes 0 at the MDE; or label coverage under 50% of fresh wallets ("unclassifiable",
  recorded).
- Leakage/ethics: maker protection only, never identification; the UNUSUAL_FLOW programme owns the insider question;
  a wallet-family idea that must be justified against the Q1 nulls (it is a cost filter, not a direction signal).
- Novelty: CH41 (farmer share), CH60 (young-wallet large buy, CB6-T); the funding path is new. N 4, EV 2, C 3.

**CH97. Attention without news (Wikipedia pageviews): a market whose named entity's pageviews jumped on the last fully
published day with no print-confirmed price move receives attention-driven, uninformed flow the next day, so maker
fills there have better mark-outs; a print-confirmed move with no pageview jump is more likely private information, so
the maker steps aside. The 2x2 of (attention, move) separates crowd attention from private news.**
- Mechanism: public attention and public information are correlated but distinct; AREPO already has the fetcher
  (`fetch_pageviews`, PIT rule D + 36h). Who pays: attention-driven takers (kept) and private-information takers
  (avoided).
- Test (`A` + `P`): entity extraction by a frozen rule (the question's proper noun to an article title; expect about
  30% coverage of non-sports markets); pageviews for about 500 entities x 60 days (30,000 requests, Wikimedia allows
  it with a user agent; 50 MB); unit = market-day; feature = pageview ratio (1d/7d) tercile x print-confirmed |move|
  tercile on day D-1; target = paper touch-maker mark-out at 2h/24h from trade-sample fills on day D and the realised
  |move| on day D; cluster by event x day. MDE about 0.5c per cell with 500 market-days per cell.
- Economics: maker presence filter; avoided loss 1-3c per fill in the "move without attention" cell; forgone spread
  elsewhere.
- Kill: no cell difference at the MDE; or coverage under 500 market-days.
- Leakage/confound: the PIT rule (only fully published days); the entity map frozen; reverse causality (a Polymarket
  move causing a pageview spike) is harmless for the filter reading but must be stated.
- Novelty: pageviews appear in no CH; CH24 is on-venue category volume. N 3, EV 2, C 1-2.

**CH98. Redemption-cash days: resolutions cluster on scheduled dates (month-ends, game days, release days), so the
aggregate cash returned to wallets per category per day is forecastable from the captures (`open_interest` of markets
with a scheduled end that day); on high-redemption days the next day's category volume and longshot prices rise
(house money at the aggregate level) and longshot YES bought on those days resolves below its price.**
- Builds on CH68 (per-wallet redeployment, dropped because hashed wallets cannot be re-queried); this is the
  market-level version with no wallet data, and on CH24 (category attention days) with a *scheduled* driver.
- Test (`A`): captures only; unit = category-day; feature = predicted redemption cash (sum of `open_interest` of
  markets with scheduled end on D, computed at D-1); targets = D+1 category volume (vs its 28-day median), D+1 mean
  longshot (mid <= 0.15) print-based change, and the resolution excess of longshot YES prints on D+1; cluster by day
  (few clusters: declare the MDE; three weeks of captures give about 20 days per category).
- Economics: maker ask on longshots on D+1 (fee 0; the CB1-C tail is the risk, CB6-T's class filter applies).
- Kill: no volume response (ratio CI includes 1) or no longshot excess at MDE 1c.
- Leakage/confound: scheduled end, never `closedTime`; sports game days are the dominant cluster (parametrised).
- N 3, EV 1-2, C 1.

---

## 3. Ranked top 8

Rank = value of information x feasibility now x originality. "Runnable now" means the test can start this week on
existing stores or on keyless fetches that are not bound to the `T_seal` lane.

| Rank | ID | One line | Runnable now | Family |
|---|---|---|---|---|
| 1 | CH79 | Trade-direction truth: audit the Data API side flag against on-chain `OrderFilled`; if it is noisy, every flow effect is attenuated by about 5x | yes (2,000 receipts for the audit) | A |
| 2 | CH84 | Model-anchored maker in path-settled dailies (Pyth TradFi, Chainlink hourly), where fair value is a public function and adverse selection is only latency | yes (pmxt + prints; disjoint from CB8-B) | B |
| 3 | CH82 | Combos: public catalogue prices the parlay markup; popular parlay legs overpriced; hedge flow in legs | yes (hourly catalogue poll; sports-scoped today) | B |
| 4 | CH89 | Deribit option-implied anchor for crypto strike ladders | yes (keyless live and history endpoints probed) | D |
| 5 | CH83 | Pyth dailies: open-gap under-reaction, terminal minutes with a free real-time source, early-close stale window | yes (pmxt history since April; prospective half days) | B |
| 6 | CH92 | Flow-skewed maker in the F4/F5 cells (the maker dual of E007/HB2; doubles in value if CH79 is right) | yes (fresh pmxt pull + prints) | E |
| 7 | CH87 | Reporting-standard premium (report-resolved vs official-resolved markets at the same price) | yes (the `textorig` table is live; fresh `h10_std`) | C |
| 8 | CH80 | Dust-anchored midpoint: present-but-empty quotes set the Gamma mid; methods payoff for every mid-based test | yes (pmxt level sizes) | A |

Next in line: CH93 (stop cascades with the pseudo-level placebo; cheapest print-based test), CH94 (exit sweeps), CH85
(proposer clocks), CH88 (political underconfidence carry; literature prior, long holds).

**How the families would be registered.**
- **A. Measurement (CH79, CH80).** CH79 is an audit before it is a hypothesis: 2,000 receipts decide whether a
  measurement correction exists. If it does, the correction is a methods note (M4) that re-states every flow result's
  ceiling and feeds CH92; the Stage-1 re-estimate is one counted test on `h10_sign`. CH80 is a pmxt descriptive with
  one counted route test, and a one-field sweep addition for the prospective version.
- **B. New products (CH81-CH86).** One fresh Gamma frame of Pyth dailies (CH83, CH84) with pmxt range reads disjoint
  from CB8-B; the Combos catalogue poller (CH82) is a tiny collector; CH81 is a census with a floor; CH85 is a Polygon
  log scan; CH86 reuses the pmxt pull. Shared machinery: public-function outcomes (no outcome field read), session-day
  clustering, the CB3 paper maker.
- **C. Text and calibration (CH87, CH88).** `textorig` (live) plus two fresh fetches (`h10_std`, `h10_pol`); frozen
  regex classes hashed before the census; event x resolution-week clustering; the CB1 tail gate on any carry.
- **D. Anchors (CH89, CH90, CH91).** Each is one small keyless poller plus a frozen matcher or interpolation rule;
  the slope-on-gap test with a sign-shuffle placebo is common to all three.
- **E. Flow identity (CH92-CH98).** One fresh print fetch (`h10_exit`/`h10_sign`, the same rows can serve CH79, CH93,
  CH94, CH95 if declared together, each with its own frozen detector), the pmxt maker machinery (CH92), the
  pageviews fetcher (CH97), captures only (CH98). Episode detectors and theme maps hashed before any mark-out;
  print-based targets; J4-R placebos for anything mid-based; hashed wallets only.

**What is honest to say about all of them.** Round 1 was carries, round 2 the maker in the right state, round 3 tails
and flow identity. This round's bet is different: that part of what looks like "small effects" is *measurement*
(CH79, CH80), and that the venue's newest products (Pyth dailies, Combos, joint events) and plumbing (37 proposers,
tick changes) are where a six-month-old crowd leaves the most. The published sign-accuracy figure is one paper's
abstract on the feed, not on the Data API, which is why CH79 starts with an audit that can kill it for 2,000 requests.
The external anchors (Deribit, nowcasts, Manifold) are the only ideas here with a professional counterparty, and their
risk is basis, not information. Fill rates bound every maker envelope (CB6-C). Nothing here is edge until it has gone
through screen, frozen replication, prospective registration and an economic check at recorded prices.

---

## 4. Ideas considered and rejected, and why

- **Chainlink-versus-Binance basis in the last seconds of 15-minute markets.** The settlement price (Chainlink's
  on-chain aggregate) lags spot by seconds and updates on deviation thresholds; the edge lives in a sub-minute window
  that AREPO cannot observe or collect; round 3 rejected the terminal-second family for the same reason. CH84's
  15-minute variant is kept only as the last test and only as a maker.
- **CME-settlement versus Pyth-spot gold twins ("Gold (GC) Up or Down" vs "Gold (XAUUSD) Up or Down").** A real
  rule-divergence pair (CH64's mechanism) whose basis is computable from public prices; but the GC listing was seen only
  in March and CB8 parked CH64 pending a `textorig` census. Re-entry: when the census shows both listings live on the
  same days for >= 20 days.
- **Overround in mutually exclusive sets that are not neg-risk (no conversion, so `sum bids > 1` cannot be arbitraged
  by conversion).** CB2 found the exclusive bucket events it looked at (weather) are neg-risk; a census of non-neg-risk
  exclusive sets would be needed first and the expected count is small. One census line, not a hypothesis.
- **Resolution-holiday and no-trade 50-50 clauses in price markets.** Real (the Pyth rule text has them) but fires on
  halts and listing errors only; no base rate to price.
- **Tick-constrained queues (spread = 1 tick in the 1c mid band) as a maker measurement.** True and probably important
  for fill rates, but it is a moderator of CB6-R and CB6-C rather than a route; folded into the band family's
  descriptives.
- **Listing bursts (hundreds of dailies listed at one minute) as a capacity shock.** Subsumed by CH22/CH56 (CB5-G) and
  CB6-C's fill model.
- **Combo RFQ quote-level data, last-look behaviour, maker identities.** Not public (the quote endpoints need L2
  auth); only the catalogue is public, which is why CH82 is written on the catalogue alone.
- **Polymarket US as a second venue for the Pyth dailies.** No documented public feed (round 2's reason stands).
- **Metaculus as the anchor crowd.** The better anchor, but 403 without a key; Manifold (keyless) is used instead and
  Metaculus is noted as an upgrade if a free key is acceptable to the user (not assumed).
- **Open-interest and funding-flow macro indicators (venue-level USDC inflows as a risk-appetite gauge).** Observable
  on chain, but the money route is a weak moderator of longshot pricing with few independent days; parked.
- **Position-split and merge events on the CTF as "short-seller" signatures.** Splits are mostly operator-mediated
  matching, not trader intent; no clean signal.
- **Re-running momentum, reversal, wallet freshness or Kalshi lead-lag with new data.** Excluded by the brief; CH79 is
  the one legitimate re-measurement because it questions the measurement, not the effect.
- **Order anticipation, spoofing, inducing cancellations, manipulation of any kind, insider identification as a route,
  holding rewards, maker-rebate loops, taker full-set arbitrage, comment sentiment, wash detection as alpha, API
  quirks.** Rejected in rounds 1-3 for reasons that still hold.

---

## 5. Sources consulted (external; AREPO documents are cited inline by name)

**Keyless probes run for this round (2026-10-17, 09:00-09:40Z; counts, field names and rule text only; no price,
volume or outcome of any market was printed or stored).**
- Gamma `GET /markets?closed=false&limit=200&order=volume24hr` and `GET /events?closed=false&order=volume24hr`
  (1,000 events): joint-event titles (three events of the "Senate ... and oil ..." form, four members each, neg-risk);
  Gamma `public-search` for "Nvidia up or down", "Gold up or down", "Tesla close above": rule text and
  `resolutionSource` (`pythdata.app/explore/Equity.US.NVDA/USD`, `Metal.XAU/USD`; a March "Gold (GC)" market with
  CME settlement), `endDate` 20:00Z and 21:00Z.
- Deribit `history.deribit.com/api/v2/public/get_instruments` (123,886 expired BTC options, expiries 2016-07 to
  2026-10-21), `get_tradingview_chart_data` (85 hourly bars for `BTC-4OCT26-77000-P` over its last 7 days; `no_data`
  for a 2023 instrument), `get_last_trades_by_instrument_and_time` (1 trade in 30 days for that put: use marks, not
  trades), `www.deribit.com/.../get_book_summary_by_currency` (938 live BTC option instruments).
- Manifold `api.manifold.markets/v0/search-markets` (keyless; fields `probability`, `totalLiquidity`, `closeTime`,
  `pool`). Metaculus `/api/posts/` and `/api2/questions/`: HTTP 403 without a key.
- Pyth Hermes and Benchmarks, the Cleveland Fed and Atlanta Fed nowcast files, Wikimedia pageviews at scale and the
  Polygon RPC log scans were **not probed today** (the pageviews fetcher exists in AREPO).

**External documents.**
- Polymarket docs, Combos for requesters (RFQ, 2-50 legs, five-second acceptance, last look, Exchange v3, combo
  position ids): https://docs.polymarket.com/trading/combos/requesters; public combo catalogue
  (`GET https://combos-rfq-api.polymarket.com/v1/rfq/combo-markets`, fields `id`, `condition_id`, `position_ids`,
  `outcomes`, `outcome_prices`, `volume`, cursor, no auth): https://docs.polymarket.com/api-reference/combo-markets/get-combo-markets.md;
  OpenAPI: https://docs.polymarket.com/api-spec/combos-rfq-openapi.yaml (CH82).
- Combos launch coverage (global launch 2026-06-10 on sports; US rollout August; Kalshi parlay maker fees):
  https://cryptobriefing.com/polymarket-combo-trading-feature/,
  https://www.legalsportsreport.com/264161/polymarket-adds-multi-leg-contracts-as-it-chases-kalshi-sportsbooks/,
  https://cdcgaming.com/brief/polymarket-u-s-fully-launches-parlays-as-kalshi-adds-parlay-maker-fees/ (CH82).
- Pyth integration for daily equity, index and commodity markets (April 2026):
  https://www.theblock.co/post/396200/polymarket-taps-pyth-network-to-resolve-new-us-equity-and-commodity-markets,
  https://cryptobriefing.com/polymarket-pyth-integration/ (CH83, CH84).
- UMA Managed Optimistic Oracle V2 for Polymarket (37 whitelisted proposers; disputes open to anyone), August 2025:
  https://www.theblock.co/post/366507/polymarket-uma-oracle-update; Chainlink for price-focused markets:
  https://www.theblock.co/post/370444/polymarket-turns-to-chainlink-oracles-for-resolution-of-price-focused-bets
  (CH84, CH85).
- Taker fees on 15-minute crypto markets funding maker rebates (January 2026):
  https://www.theblock.co/post/384461/polymarket-adds-taker-fees-to-15-minute-crypto-markets-to-fund-liquidity-rebates
  (CH84).
- Dubach, "The Anatomy of a Decentralized Prediction Market: Microstructure Evidence from the Polymarket Order Book",
  arXiv:2604.24366 (feed-vs-on-chain trade direction about 59%; effective half-spread sign flips in 67% and 50% of
  markets; depth closer to uniform; self-counterparty share median 1%, upper tail 22%): https://arxiv.org/abs/2604.24366
  (CH79, CH80).
- Nechepurenko, "Fill-Side Behavioral Concentration on Polymarket: Identification Limits under Record-Level
  Attribution", arXiv:2605.11640 (public fills do not identify market making; attribution conventions; 13.4M
  `OrderFilled` in 2.3 days): https://arxiv.org/abs/2605.11640 (CH79's mint/merge rule).
- Le, "Decomposing Crowd Wisdom", arXiv:2602.19520 (353M trades, Kalshi and Polymarket; persistent political
  underconfidence toward 50%, replicating on Polymarket): https://arxiv.org/abs/2602.19520 (CH88).
- Cheng, Yang, Zou, "Arbitrage Analysis in Polymarket NBA Markets", arXiv:2605.00864 (single-market anomalies rare,
  median 3.6 s): https://econpapers.repec.org/paper/arxpapers/2605.00864.htm (context for CH82's sports legs).
- Deribit API documentation (public endpoints; historical access): https://docs.deribit.com/ and
  https://support.deribit.com/hc/en-us/articles/25973087226909-Accessing-historical-trades-and-orders-using-API (CH89).
- Manifold API: https://api.manifold.markets/v0 (probed; CH91). Metaculus API (key required):
  https://www.metaculus.com/news/2023/02/15/metaculus-officially-launches-api/ (CH91 note).
- Polymarket docs cited in rounds 1-3 and still used here: fees (`rate*p*(1-p)`, maker 0, rebates), liquidity rewards
  (midpoint, `v`, two-sided rule), CLOB orders (`orderMinSize`, tick sizes), negative risk, UMA resolution:
  https://docs.polymarket.com/trading/fees, https://docs.polymarket.com/developers/market-makers/liquidity-rewards,
  https://docs.polymarket.com/developers/CLOB/orders/orders, https://docs.polymarket.com/developers/neg-risk/overview,
  https://docs.polymarket.com/developers/resolution/UMA.
- Moshrefi (Kalshi parlays overpriced), Page and Clemen (abstention and time-to-expiry bias), Cardozo and
  Rivero-Wildemauwe (favourite-longshot on Polymarket): as cited in round 1.
