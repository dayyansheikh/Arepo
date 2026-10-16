# Creative hypotheses, round 3: where money could come from on Polymarket (2026-10-17)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass of 2026-10-17 (00:16 UTC+1, 2026-10-16T23:16Z) at the user's
request. One file; no code, no queue specs, no other commits. Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md`
(CH01-CH34), round 2 is `CREATIVE_HYPOTHESES_2026-10-16.md` (CH35-CH59); this file starts at CH60 and repeats neither.
Where an idea builds on an earlier one, the parent is named. Every number quoted from AREPO documents is a development
or screen result, not evidence.

## 0. How to read this file

**What changed since round 2 (16 Oct results and drafts).**
- **CB1 (q0019-q0023) advanced nothing.** A1 (decided carry, post-end) 57 units: below floor. A2 (decided carry,
  pre-end) 348 units / 281 clusters: net -1.05c, 11 losing clusters; without its 5 worst events +0.35c (p 0.31, a
  robustness check, not a result). C1 (longshot ask-selling held to resolution) 224 filled orders / 62 events: net
  -3.84c per filled share, decomposed as captured half-spread +0.91c and resolution excess -4.75c, fill rate 6.8%;
  without its 5 worst events +4.6c, with the declared tail and p conditions still failing. E (genesis window) was
  untestable: 2,886 of 3,200 `h2_main` markets have no question text in the store (a storage choice, not a venue
  fact: Gamma returns `description` for closed markets). B (near-rung NO) was untestable: 52 usable ladders of the
  300 needed. **Reading that steers this round:** both carries that ran show a *tail-loss* structure (a small mean
  loss made of many small wins and a few catastrophic events). The question is not "is the mean positive" but "are
  the catastrophic events identifiable before they happen". Any such test must use fresh data; CB1's h2 rows are
  worn and are never re-screened.
- **HB2-R (J2):** F4 (flow x volatility), F5 (flow x spread) and L1 (1d change x liquidity) replicate on h3; F3 (late
  life), F7 (large-for-market prints) and F8 do not. J8: C-ACT is near-mechanical; C-TTE needs an as-of time-to-end.
  J3 (book bounce) was UNAVAILABLE (12.7% book coverage). r4_book: book levels are descriptive only. Nothing from the
  taker side is cost-viable: F4/F5 gross about 1c against about 3.5c spread + fee.
- **CB3, CB4, CB5 are drafted** (quote vacuums CH35, selective maker CH39/40/41, pre-close dump CH46, series roll CH50,
  natural experiments CH52/53, seed anchor CH56, hour moderation CH58, ladder-vs-bucket CH59). CB2 covers weather
  favourites (CH27), ladder dominance (CH12/13) and placeholders (CH10). None of those is repeated here.
- **Venue mechanics verified for this round (keyless, 2026-10-16, cited in §5).** (1) Daily crypto "Up or Down"
  markets resolve on the **Binance 1-minute candle "Close"** at 12:00 ET, comparing the previous day's noon candle
  with today's; an exactly equal close resolves 50-50 (read from live Gamma rule text, not from a docs page). (2)
  The Data API **`/holders?market=<conditionId>`** returns the top holders of each token with amounts and proxy
  wallets, without a key. (3) Neg-risk conversion is atomic: one NO share of a member becomes one YES share of
  *every other* member of the event; augmented events add placeholders and an explicit "Other".

**Data labels.** `A` = in AREPO's stores now: complete-universe 2h captures with touch, Gamma mid, `oneHourPriceChange`,
`last_trade_price`, `volume24hr`, `liquidity`, neg-risk ids, `closed`, and the sidecar since 11 Oct 12:00Z
(`accepting_orders`, `competitive`, `open_interest`, `clob_rewards`, `rewards_max_spread`, `rewards_min_size`,
`fee_schedule`, `uma_resolution_statuses`, `series_slugs`, `parent_event_ids`, `order_price_min_tick_size`); book
sweeps twice per pass (touch, 1c and 5c depth); trade samples (2,000 active-frame markets per pass, hashed wallets,
raw kept 3 days); the live large-trade monitor (prints >= $1k every 5 min, hashed wallets, wallet age); the wallet
activity cache (9,621 wallets, including REDEEM rows); the audited cross-venue pair history (316 clean pairs in the
C1 set; 958 in the full history; 10-minute); pmxt hourly L2 books 2026-04-13 to 08-10 (range reads by condition id);
the IF-H2 ladder metadata (events walked, deadlines parsed). `P` = collectable read-only from public keyless sources
at modest cost within a week (Gamma `description` for any market, Data API `/holders`, `/activity`, `/trades`,
Binance public klines, Polygon public RPC logs, CourtListener/RECAP, FRED/ALFRED vintages). `N` = no known free
source. **Sealed and not usable by anything here:** `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`,
`h7_cb4_*`, the E009/E010 live poller (until 2026-11-03), E011 labels (until 2026-11-11). `h2_main` is worn beyond its
budget and `h3_power` is retired from replication; every historical test below names a **fresh** fetch (`h8_*`)
disjoint by market id from h1/h2/h3/h5/h6/h7, capped at `min(T_fetch, T_seal = 2026-10-22T00:00Z)`, with the
trade-before-`t` placeholder rule and scheduled anchors.

**Hygiene that binds every idea.** Trade before `t`; scheduled anchors, never `closedTime`; event x resolution-week
clustering for carries; tightness at both ends of any mid-based target (J4-R) and print-based targets where possible;
Gamma `description` is the *current* text, so any text feature must exclude markets with a post-listing clarification
or use text stored at first sighting; the cumulative test count (M3). Category stays a parameter (sports scope is the
user's call).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = an afternoon on existing data, 5 = new
collector plus weeks). My judgement, not measurements. Cost conventions as rounds 1-2: taker fee `rate*p*(1-p)` per
leg (crypto 0.07; sports 0.03-0.05; politics/finance/tech 0.04; geopolitics 0; makers 0, rebate 15-25% of the
fee-equivalent of own fills); median spreads by band 4.1 / 3.0 / 2.2 / 3.0 / 2.5c; liquid round trip 1.8c; median
round trip 4.5c. One-leg hold-to-resolution pays the half-spread and the fee once.

---

## 1. Map: what the 16 Oct results say about where money is

| Family | What the results suggest | Money route |
|---|---|---|
| A. Tail structure | Both CB1 carries lost on a handful of events and would have been positive without them; the catastrophic events are the object, not the mean | carry only where the tail is identifiable and excluded ex ante; buy the tail where the crowd prices it away |
| B. Rule text | Text was missing in the store, not at the venue; rules carry condition counts, deadline hours, source names and wording twins that the headline-trading crowd does not read | hold-to-resolution NO on over-specified questions; dominance pairs from wording; dispute avoidance |
| C. Forced and mechanical flow | Conversions, sibling resolutions, redemptions, execution algorithms and concentrated holders create flow whose timing and direction are predictable and whose information content is nil | maker into the flow; small fade after it |
| D. Price-band geometry | Rewards stop at 0.90; fees vanish at the extremes; both create bands with different competition and different flow composition | maker in the reward shadow; maker at the extremes where farmers trade |
| E. Cross-venue for makers | The Kalshi lead is real and not takeable; a maker does not need to take it, only to step aside | adverse-selection shield |
| F. Information timing, new sources | Dockets, statistical first prints and the Binance settlement candle are public clocks nobody has joined to Polymarket | taker in the minutes after the source updates; carry at the bucket boundary |
| G. Capacity and structure | 51% of quoted markets never trade; maker fill rates of 7% bind every maker route | fill-probability model; round-strike bumps |

---

## 2. Hypotheses

### A. Tail structure (the CB1 residuals, on fresh data)

**CH60. Ex-ante tail classifier for longshot sellers: the catastrophic longshot wins that sink a longshot-selling carry
(C1's five worst events) are concentrated in markets whose resolution is a discrete private decision, whose longshot
drifted up over the prior week, and which received large-for-market buys from young wallets in the prior 24h; selling
asks only outside that class turns the carry's mean positive.**
- Mechanism: a longshot at 0.03-0.10 pays off in two ways. In *continuous-process* markets (crypto strikes, weather
  buckets, pre-game sports, polls) the tail arrives through a public path the seller can watch and exit ahead of. In
  *discrete-decision* markets (awards, courts, executive orders, strikes, nominations) the tail is a jump that is
  unhedgeable and, per the case catalogue, sometimes preceded by informed buying. C1's resolution excess (-4.75c)
  is the price of the jumps; its half-spread (+0.91c) is the income. If the jump class is predictable from public
  data at order time, the seller avoids it and keeps the income.
- Why here: Polymarket lists both classes side by side with the same fee and the same reward rules, so a reward bot
  that sells both sides everywhere is the natural counterparty on both; the discrete class is where the documented
  informed episodes live (`CASE_CATALOGUE.md`: 11 cases, mostly geopolitics, awards and corporate decisions).
- Test (fresh, `P`): fetch `h8_tail`, a seeded sample of resolved binary markets with a leg priced in [0.02, 0.10] at
  some 6h origin in its last 60 days, disjoint from every prior run, with `description`, 10-min prices and trades
  (capped at `T_seal`). **Declare before any outcome read** four ex-ante features at each origin: (i) resolution
  class from the rule text (regex over "announce", "court", "order", "award", "nominate", "strike" vs "price",
  "temperature", "score", "poll"; frozen before the census); (ii) 7-day drift of the longshot mid; (iii) presence
  of a buy print >= 5x the market's median print in the prior 24h; (iv) that buyer's wallet age < 30d (hashed
  first-trade lookup, as the live monitor does). Unit: origin-market; primary: logistic odds ratio of "longshot
  resolves YES" on the four features, controlling for price; economic secondary: paper C1 rule restricted to the
  "no flag" stratum, net per filled share with the CB1 tail gate. Cluster by event x resolution week. MDE: with about
  3,000 origin-markets and a 5% base rate (about 150 YES events, deff 2), a binary feature with 30% prevalence is
  detectable at an odds ratio of about 1.7; the economic stratum needs about 1,000 fills for a 1.5c net at SD 22c.
- Route and hurdle: maker, no fee, one leg, hold to resolution; the hurdle is the wrong-side tail only. Capacity is
  bounded by fills (C1: 6.8% of attempted orders), so the route is an income floor, not scale.
- Leakage: the rule text is current text (clarifications after a surprise could encode the outcome): use only
  markets without a clarification marker, and store text at first sighting prospectively. Feature (iii)/(iv) must be
  computed from trades strictly before the origin with the truncation rule (unavailable, never 0). Do not look at
  C1's five events to choose the features; the list above is fixed now.
- Scores: N 4, EV 3, C 3.

**CH61. Geopolitics discrete tails are underpriced: in the zero-fee geopolitics category, discrete-decision outcomes
priced 0.02-0.10 at 7-30 days before the scheduled end resolve YES more often than priced, because the crowd prices
"nothing happens" and the realised base rate of surprises (strikes, ceasefires, leadership changes) is higher.**
- Mechanism: the mirror of CH60. The favourite-longshot bias says longshots are *over*priced in aggregate (PX3/PX4
  null at mid-levels, C1 near calibration at 1d), but the aggregate is dominated by sports and crypto where the
  tail is continuous. In a category where tails are jumps and informed trading has been documented, the public
  price before the jump is a lower bound on the probability, not an estimate of it.
- Why here: geopolitics is the one fee-free category, so a taker's one-leg cost is the half-spread alone (about 2c
  at these prices); nowhere else is a tail buy this cheap.
- Test (fresh, `P`): `h8_geo`, every resolved geopolitics market (Gamma category or fee schedule) with volume >= $100
  since 2025-06, disjoint from prior runs; the resdev frame suggests roughly 600-900 such markets in a year, many in
  ladders. Unit: market at origins 30d, 14d, 7d before the scheduled end, trade before `t`; primary: resolved-YES
  rate minus mean price in the [0.02, 0.10] band (one-sided > 0); cluster by event x resolution week (ladders are
  one cluster). MDE: with about 600 markets and 150 clusters, about 3-4c on the gap, which is also the size that
  matters (a 5c price needs a 10% true rate to be worth the capital).
- Route and hurdle: taker buys the ask once (fee 0, half-spread about 2c), holds to resolution; capital locked for
  weeks; most positions expire worthless, so the P&L is lumpy and the tail gate must be inverted (a minimum number of
  winning clusters).
- Leakage: survivorship of Gamma's listing; the case catalogue must not be used to pick the sample; "discrete" is
  defined by the frozen regex, not by hindsight; cluster by theme as a sensitivity (one war is one bet).
- Scores: N 3, EV 3, C 2.

**CH62. Calendar-decided NO carry: in single "by <date>" markets (not ladders) whose parsed deadline has passed by more
than 24h, whose YES never traded above 0.50, and whose NO ask is still below 0.99, the residual is pure oracle wait
with a wrong-side tail set only by rule ambiguity, and the carry is positive where A2's price-decided carry was not.**
- Mechanism: A2 (pre-end, "decided" by price >= threshold) lost on 11 clusters: outcomes that were priced as decided
  and were not. Deciding by the calendar instead of the price removes the forecast tail: once the deadline has passed
  without the event, only resolution mechanics remain (a late UMA proposal, a clarification, a timezone or
  "announced-vs-occurred" reading). CH01 and CH02 decide by price or by on-chain proposal; CH05 is the ladder case,
  which CB1-B could not test. This is the single-market, calendar case.
- Why here: Polymarket sets `endDate` loosely (IF-H2 found "by March 31" rungs with a June `endDate`), so markets
  stay open and quoted for days after their own deadline, and the reward bots keep two-sided quotes inside them.
- Test (`A` + `P`): the IF-H2 deadline parser applied to the live captures (metadata only) gives single-market
  deadlines; population = captures where `now > deadline + 24h`, `closed = false`, max historical YES trade price
  < 0.50 (trades fetched post hoc), NO ask < 0.99. Unit: market; primary: net per share of buying NO at the
  recorded ask, held to resolution, after the event x resolution-week clustering and the CB1 tail gate; secondary:
  wait distribution (days to `closed`) and annualised net. Historical version on `h8_bydate` (resolved single "by
  date" markets, deadlines parsed, prices from listing). MDE: with about 400 units and 300 clusters at SD 10c (most
  units win 1-3c, a few lose 97c), about 1.5c on the mean; the exact event-level bound decides below 10 losing
  clusters.
- Route and hurdle: taker buys NO at 0.97-0.99 once; fee about 0.1-0.2c at these prices; capital locked days to
  weeks; the annualised number is the test, with a declared floor.
- Leakage: the deadline must be parsed from the question at listing (IF-H2 rule), never from `endDate` or
  `closedTime`; "never traded above 0.50" is computed from trades before the origin only; a market can be clarified
  to extend its deadline (store the text at first sighting; count extensions as losses in a worst-case bound).
- Scores: N 3, EV 2, C 2.

### B. Rule text (collectable now; the h2 absence was a storage choice)

**CH63. Specificity discount: the more binding conditions a market's rules carry (named source, exact wording,
"officially", a time of day, a conjunction), the more the headline-trading crowd overprices YES, so NO resolves more
often than priced in the top condition-count tercile.**
- Mechanism: the title is the product; the rules are the contract. A rule with four conditions describes a narrower
  event than its headline (the conjunction effect), and Polymarket resolves on the rules. Buyers of YES price the
  headline; the discount for specificity is left to whoever reads the text.
- Why here: Polymarket's markets are user-facing headlines with long rule text under the order book; the venue
  itself warns that resolution follows the "pre-defined rules" (help centre, cited in §5). CH48 is the sports
  "regulation-only" special case; CH32 the mentions case. This is the general version.
- Test (fresh, `P`): `h8_text`, a seeded sample of about 6,000 resolved binary markets across categories with
  `description`, prices and trades; frozen regex counts of condition markers ("must", "official", "according to",
  "and", "before <time>", "ET", named URL) hashed before the census. Unit: market at origins 7d and 1d before the
  scheduled end (trade before `t`); primary: calibration gap (price minus resolved-YES rate) in the top tercile of
  condition count minus the bottom tercile, within price band and category (one-sided > 0); cluster by event x
  resolution week. MDE: about 3c on the tercile difference at 2,000 markets per tercile and deff 2.
- Route and hurdle: taker buys NO once at 7d (fee 0.04-0.05 x p(1-p), about 0.5-1c mid-range; half-spread 1-2c) and
  holds; a maker version rests NO bids in high-count markets. A 3c calibration gap clears the one-leg hurdle; a 1c gap
  does not.
- Leakage: current text may include clarifications added after events; exclude markets with "clarif", "update",
  "additional context" markers and report the share excluded; count markers only in the text as of listing where the
  prospective extractor stores it. Category and price-band controls are mandatory (sports rules are long for other
  reasons).
- Scores: N 4, EV 3, C 2.

**CH64. Rule-divergence twins: two Polymarket markets on the same headline with different rules (by vs on; announced vs
in effect; Binance vs Coinbase close; with vs without overtime) trade as if identical, so one of each pair is a
dominance leg (the broader event cannot be less likely) that can be held riskless when the ordering is inverted and
is a probability spread otherwise.**
- Mechanism: the venue lists near-duplicates (series re-lists, sponsor-created variants, the cross-venue audit found
  9 inverted or before-vs-on mismatches among 341 "same" pairs across venues; the same wording drift exists within
  Polymarket). Crowds and bots match on titles. CH12/CH13 use dates and strikes; CH59 ladders vs buckets; this uses
  the *rule text* to establish the ordering.
- Why here: no listing review enforces consistency between events; makers quote per market from one fair value.
- Test (`A` + `P`): census first. Stem-match questions across events in the live captures (the IF-H2 stem rule),
  fetch both descriptions, classify the ordering by a frozen rule set (broader vs narrower deadline, broader vs
  narrower trigger, same). Unit: twin pair-capture; primary: share of captures where `ask(broader) < bid(narrower)`
  by more than the fee band (riskless), and the mean signed gap otherwise; realised-payoff check at resolution
  (the broader leg must resolve YES whenever the narrower does; count violations, which are the rule-reading
  errors). Cluster by pair x day. MDE: descriptive until the census shows >= 100 pairs; the realised-payoff
  consistency rate needs about 60 resolved pairs for a 10-point gap.
- Route and hurdle: maker inside the band or taker on the inverted pairs; fee on two legs (about 1-2c at
  mid-prices) against a gap that must exceed it; capital locked to the later resolution.
- Leakage: rule classification must be frozen before any price is read; current text risk as CH63; a pair that
  resolves inconsistently (both YES and NO) is a dispute, not a profit.
- Scores: N 3, EV 2, C 2.

**CH65. Ex-ante dispute predictor: the probability that a market is disputed (4-6 days of extra lock and a 50-50 tail)
is predictable from rule ambiguity, open interest, a mid-range price at end and the proposer's wallet, and the cost
of every carry in rounds 1-3 is concentrated in that predictable set.**
- Mechanism: disputes are rare and their cost is a tail; CH03 measures the base rate and CH47 the post-proposal
  lottery, but nothing predicts *which* markets will be disputed before the proposal. If the predictors are public
  and ex ante, every carry (CH01, CH02, CH05, CH62) can exclude the high-risk set and its tail gate changes.
- Why here: UMA disputes need a $750 bond and are worth it only when the stake is large (open interest) and the
  rule admits two readings (text); both are public before the proposal.
- Test (`A` since 11 Oct + `P`): prospective: the sidecar's `uma_resolution_statuses` gives proposals and disputes
  per capture; features at the last capture before the proposal: condition count (CH63), `open_interest`, |mid -
  0.5|, time between scheduled end and proposal, prior clarifications. Unit: market with a proposal; primary:
  out-of-sample AUC and the dispute rate in the top-decile score vs the rest; cluster by event. Historical:
  Polygon logs of the OptimisticOracle (CH03's scanner, keyless RPC) joined to Gamma text. MDE: at the documented
  dispute rate (a few percent), about 2,000 proposals give a 2x risk ratio in the top decile.
- Route and hurdle: not a route; a cost filter that changes the carry arithmetic (the 4-6 day lock on 1-3c carries
  is the annualised killer).
- Leakage: features at the last capture *before* the proposal only; the dispute itself may trigger clarification
  text (exclude post-proposal text); the proposer wallet is public on-chain but must be hashed.
- Scores: N 3, EV 2, C 2.

### C. Forced and mechanical flow (new sources of uninformed prints)

**CH66. Neg-risk conversion dumps: a holder who converts NO on one member receives YES on every other member and sells
the unwanted low-probability ones at their bids within minutes, a synchronised multi-member sell by one wallet with no
information; the hit members' quotes revert, and part of J5's sibling-move reversal is this.**
- Mechanism: conversion is atomic and one-directional (verified: 1 NO of a member becomes 1 YES of each other
  member). A trader who wanted "not X" now holds a basket of YES tokens they did not choose; the natural action is
  to sell the ones priced at 1-5c at the bid. That is a burst of same-wallet sells across siblings at the same
  minute, hitting thin bids. Nothing about the world changed.
- Why here: only Polymarket has the neg-risk adapter; Kalshi has no conversion. Reward bots on each member re-centre
  on their own market's mid, so the displaced bids stay displaced until the next re-quote.
- Test (`A`): in the trade samples, detect clusters of >= 3 sells by one hashed wallet across >= 3 members of one
  event within 120 s (the signature); fresh-data version (`P`): Polygon logs of the neg-risk contracts' conversion
  events (keyless RPC) give exact conversion times. Unit: conversion episode x member; primary: print-based mark-out
  of the hit members' bid at +30 min and +2h relative to the pre-episode tight mid (reversal > 0, one-sided), with the
  within-market increment-shuffle placebo (J4-R); economic secondary: paper bid posted one tick above the hit bid
  after the first sell, filled by the next sell in the episode, marked at the next tight mid. Cluster by event x
  day. MDE: with about 500 episodes (deff 2) at a 3c mark-out SD, about 0.4c.
- Route and hurdle: maker (no fee, rebate); gross 1-3c per filled share on thin members; capacity small per episode
  but episodes are frequent in large political and sports events.
- Leakage: the signature must be detectable from public prints before the mark-out window (same-second multi-market
  sells are visible in `/trades` within the monitor's 5-minute cycle); the hashed wallet is never identified; the
  episode detector is frozen before any mark-out is read.
- Scores: N 5, EV 3, C 2.

**CH67. Sibling-resolution unwind: in the hours after one member of a multi-market event flips `closed` (resolves),
the remaining members' asks are stale relative to the sum-to-one constraint and to makers' hedge unwinds, so the
sum of sibling asks deviates from 1 by more than the fee band for minutes to hours and the first-hour sibling move
partly reverts.**
- Mechanism: when a member resolves YES, every other member is worth 0 (a sibling of a YES-resolved member is dead
  but may still show a bid); when it resolves NO, the other members' fair values rise by a known factor. Makers who
  hedged across members unwind the legs; reward bots re-centre per market with their own lag. CH09 measures the
  standing deviation; CH50 the series roll into a *successor* market; this is the trigger inside one event.
- Why here: Polymarket resolves members of an event one at a time (eliminations, early calls), and nobody owns the
  cross-member book.
- Test (`A`): population = captures `i` where a member's `closed` flipped between `i-1` and `i` (sidecar since 11
  Oct); unit: event-episode; primary: sum of YES asks across open members at `i` and at the sweeps of pass `i`
  (minutes apart) minus 1, against the same event's pre-flip deviation (CH09 band), and the share of episodes
  where a passive full set could be assembled inside the fee band; secondary: reversal of each open member's
  first-hour move by the next tight capture (J4-R estimator, print-based where prints exist). Cluster by event x
  day. MDE: with about 300 episodes in two weeks of captures, about 0.5c on the deviation; the full-set share is
  descriptive.
- Route and hurdle: maker (passive accumulation of the full set at the moment of the flip) or taker on dead members
  with a residual bid (sell YES of a sibling of a YES-resolved member at any bid > fee: riskless, tiny). The hurdle
  is the fee band on N legs for the taker and the two-hour re-quote window for the maker.
- Leakage: `closed` flips are observed with up to 2h lag at the capture cadence; use the sweep pair inside the pass
  for the minute scale; never use the resolved outcome of *other* members as a feature.
- Scores: N 3, EV 2, C 1.

**CH68. Post-redemption redeployment: wallets re-deploy redeemed cash within 24h into markets of the same event family
or category, those trades are uninformed (mark-out at or below 0), and their timing is predictable from public
resolutions, so a maker who is present in the destination markets after large resolutions earns the spread without
adverse selection.**
- Mechanism: a redemption is a cash event; the behavioural literature on house-money and the Polymarket pattern of
  "rolling" winnings into the next market of the same series suggest the next buy is attention-driven, not
  information-driven. The flow is dated by the resolution and located by the wallet's history.
- Why here: redemptions are on-chain and visible per wallet in the public activity feed (the wallet cache already
  holds REDEEM rows); the series and event structure tells the maker where the money goes.
- Test (`A` + `P`): from the wallet activity cache (9,621 wallets) and new `/activity` reads for wallets seen in the
  live monitor, build (REDEEM, next trades within 24h) pairs. Unit: wallet-redemption episode; primary: print-based
  mark-out (2h, 24h) of the post-redemption buys vs the same wallet's other buys and vs matched buys by other wallets
  in the same market-hour (one-sided <= 0 for "uninformed"); secondary: the share of redeployed notional that lands in
  the same series or category (destination predictability) and its arrival-time distribution. Cluster by wallet and
  by market-day (two-way). MDE: with about 3,000 episodes at a 3c mark-out SD and deff 2, about 0.2c.
- Route and hurdle: maker in the destination markets in the 24h after large resolutions; no fee, rebate; the hurdle
  is that uninformed flow is only worth the spread if it arrives where the maker is (fill rate).
- Leakage: wallet selection by the live monitor is size-biased (>= $1k prints); hashed wallets only; the "next
  trade" must be strictly after the REDEEM timestamp with the Data API's own clock; survivorship of wallets that
  stop trading.
- Scores: N 4, EV 2, C 2.

**CH69. Execution-algorithm footprints: regular-interval, same-wallet, same-direction clips of similar size (a TWAP
signature) predict further same-direction prints for the next 10-30 minutes, the sequence's mark-out *after it ends*
reverts, and a maker who steps aside during the sequence and re-posts after it avoids the loss and captures the fade.**
- Mechanism: a large order worked in clips is flow, not value; HB2 F7 (large-for-market prints) replicated poorly on
  h3, consistent with "large prints" mixing informed jumps with worked orders. The sequence is public in the prints
  (wallet hash, timestamps, sizes). Its information content is in *future flow* (the rest of the order), not in the
  outcome.
- Why here: Polymarket has no hidden orders or icebergs at the venue level, so working an order leaves a visible
  trail in `/trades`; reward bots do not read it.
- Test (`A`): in trade samples and the live monitor, detect sequences: >= 4 prints by one hashed wallet, same side,
  inter-arrival CV < 0.5, size CV < 0.5, within 30 minutes. Unit: sequence; primary (flow): probability of a further
  same-side print by the same wallet in the next 10 minutes vs a matched non-sequence print (one-sided > 0);
  primary (value): print-based mark-out at 2h after the *last* print of the sequence (reversal, one-sided < 0 in the
  sequence's direction); economic: paper maker who cancels the hit side at the second clip and re-posts at the touch
  10 minutes after the last clip, vs the always-present maker. Cluster by market x day. MDE: with about 800
  sequences, 10 points on the continuation probability; 0.4c on the 2h mark-out.
- Route and hurdle: maker protection plus a small fade; no fee; the hurdle is latency (a 5-minute monitor sees the
  sequence after two or three clips, which is enough for 30-minute sequences).
- Leakage: the sequence detector sees only taker prints in the sample's 2,000 markets; sequences cut by the sample
  window are "unavailable"; the hashed wallet is never identified; this is a maker-side use of public prints, not
  order anticipation for a taker (not proposed).
- Scores: N 3, EV 2, C 1.

**CH70. Holder concentration as a forced-flow predictor: markets where one wallet holds more than half of a side's
open interest (Data API `/holders`, keyless) have larger pre-close dumps, more quote vacuums and uninformed exit
prints, so the concentration ratio is a presence filter for makers and a moderator for CH46.**
- Mechanism: a concentrated holder must exit through a thin book or hold to resolution; either way their prints are
  size-driven, not information-driven, and their presence deters other makers (a single large resting order is the
  book). The ratio is public per market at any time.
- Why here: Polymarket shows top holders in the UI and serves them keyless; the long tail has hundreds of markets
  where the top holder is most of the market.
- Test (`P`, cheap: one `/holders` call per market per day for the 2,000 sampled markets): unit: market-day;
  features: top-1 and top-3 holder share of each side; targets: (i) wide-state frequency in the next day's captures
  (CB3's `quote_state/` definitions), (ii) print-based mark-out of prints by the top holder's hashed wallet vs
  others (one-sided <= 0), (iii) CH46's pre-close dump size by concentration tercile. Cluster by event x day. MDE:
  with about 10,000 market-days, 2 points on the wide-state rate per tercile; about 0.3c on the mark-out with 2,000
  top-holder prints.
- Route and hurdle: maker presence filter (no fee); taker fade of the top holder's exit (3.5c hurdle, probably not
  met); the value is in (i) and (iii), which feed CB3 and CB4 designs.
- Leakage: holders are current snapshots; the top holder's identity is never stored, only the hashed proxy wallet;
  the share must be computed before the day's prints; the `/holders` endpoint's limit and refresh cadence must be
  measured (undocumented).
- Scores: N 3, EV 2, C 1.

### D. Price-band and reward geometry

**CH71. Reward-shadow band: liquidity rewards require two-sided quotes inside [0.10, 0.90], so at the 0.90 boundary
reward quoters disappear, spreads and vacuum rates jump discontinuously, taker fees are still small
(0.05 x 0.9 x 0.1 = 0.45c), and a maker in 0.90-0.96 faces less competition and a flow of disposition sellers and
hope buyers (CH42, CH23) that is uninformed.**
- Mechanism: the reward formula pays nothing outside the band, so the marginal quoter above 0.90 is a human or an
  inventory hedger, not a bot. Fine ticks (0.001) still apply until 0.96 (CH15), so price improvement is possible.
  The flow in this band is the exit of winners and the entry of late hope; HB2 F4/F5 say adverse selection is
  concentrated in volatile and wide markets, which the band is not once the outcome is near-decided.
- Why here: the band edges are venue constants (docs cited in round 2); no other venue has the same geometry.
- Test (`A`): regression discontinuity at 0.90 (and its mirror 0.10) on the captures and sweeps: unit:
  market-capture; primary: quoted spread and 1c depth just above vs just below 0.90 (local linear, bandwidth 3c;
  one-sided wider above); second primary: paper maker at the touch in [0.90, 0.96] vs [0.84, 0.90], queue-rule
  fills from trade samples, print-based 2h mark-out and hold-to-resolution net; cluster by market and capture day.
  MDE: with about 20,000 market-captures in the window, 0.3c on the spread discontinuity; about 1,000 fills for a
  0.5c mark-out difference.
- Route and hurdle: maker, no fee, no reward either (that is the point); gross is the half-spread (1-1.5c in the
  band); the hurdle is the wrong-side tail (a 0.92 market that loses costs 92c), which CH60's class filter and the
  tail gate must bound.
- Leakage: tightness at both capture ends for the spread target; the maker's hold-to-resolution P&L needs the CB1
  truncation rule; a market can cross 0.90 because of news (condition on the prior capture's state, not the current
  one, for the maker test).
- Scores: N 4, EV 3, C 1.

**CH72. Fee-valley farming flow: because the taker fee is `rate*p*(1-p)`, the cheapest place to generate volume for
taker-rebate tiers or airdrop points is at extreme prices, so farmer flow (round-trip wallets) concentrates at p > 0.95
and p < 0.05, is two-sided and uninformed, and extreme-price makers in high-turnover markets get the best fills on the
venue.**
- Mechanism: a farmer who needs $100k of volume pays 0.07 x 0.25 = 1.75c per share at 0.50 in crypto and 0.07 x
  0.0475 = 0.33c at 0.95; the choice is forced by the fee shape. CH41 asks whether farmer share predicts maker losses;
  this asks *where on the price axis* farmers trade and whether the extremes are therefore the maker's best band.
- Why here: the fee formula and the tier programme (05-28) are specific to Polymarket; the rebate is a share of the
  fee-equivalent of fills, which is also smallest at the extremes, so reward bots have less reason to be there.
- Test (`A`): from trade samples, classify wallets by within-market round-trip share (CH41-narrow's definition);
  unit: price-band x market-day; primary: share of farmer notional by price band vs non-farmer share (one-sided:
  more extreme); second: paper maker mark-out at the touch in p > 0.95 markets with `volume24hr / open_interest` in
  the top tercile vs bottom tercile. Cluster by market-day. MDE: band shares are precise with about 50,000 prints;
  the mark-out needs about 1,000 fills for 0.4c.
- Route and hurdle: maker at 0.95-0.99 in high-turnover markets; gross is the tick (1c above 0.96) and the half-
  spread; the tail is the 97c loss on a wrong-side resolution, so this is CH01's carry with a flow justification and
  needs CH60's class filter.
- Leakage: the farmer label uses the wallet's *prior* prints only; the 500-print visibility cap truncates the
  heaviest farmers (count as unavailable); the natural-experiment date (05-28) must be respected if pmxt history is
  used.
- Scores: N 3, EV 2, C 1.

### E. Cross-venue for makers

**CH73. Kalshi-skewed maker: the 10-20 minute Kalshi lead is not takeable after costs, but a Polymarket maker who pulls
or skews the quote on the side Kalshi just moved against, for 20 minutes, avoids exactly the fills that are informed;
the filtered maker's mark-out improves by more than the fills forgone cost.**
- Mechanism: the cross-venue study found Kalshi's 10-minute change predicts Polymarket's next 10-20 minutes (r
  about 0.24) and Polymarket does 86% of the closing. For a taker that is 1-2c against a 3.5c hurdle; for a maker it
  is a signal that the *next prints* on one side are informed. Stepping aside costs the spread on those prints and
  saves the adverse selection. CH38 uses Kalshi only during vacuums; this is unconditional.
- Why here: Polymarket has reward bots that quote both sides regardless of the other venue; Kalshi has designated
  makers and a retail channel; the lead is documented and the live stream is already collected (sealed until
  2026-11-03, not used here).
- Test (`A` + `P`): the audited historical pair set (316 clean pairs, 10-minute) joined to Data API prints for the
  Polymarket legs (fetchable, capped at the pair history's end). Unit: pair x 10-minute step; primary: print-based
  mark-out (20 min, 1h) of Polymarket prints that hit the touch in the 20 minutes after a Kalshi move >= 1c, on the
  side Kalshi moved toward, vs prints at other times (one-sided: worse for the maker after a Kalshi move); economic:
  paper touch maker with the skew rule vs always-present, fills by the touch rule, net per posted quote. Cluster by
  pair x day. MDE: with about 20,000 post-move prints, 0.3c on the mark-out difference.
- Route and hurdle: maker, no fee; the gain is avoided loss (1-2c on perhaps 10-20% of fills); the hurdle is the
  forgone spread on the fills skipped and the matcher's error rate (the audit found 9 mismatches in 341).
- Leakage: Kalshi candles are venue-timed; use receipt-equivalent lags (the E009 design's 2-minute rule); never use
  the E009/E010 live stream before its unseal; the pair set is worn by the lead finding itself (label the measurement
  "unreplicated"; the prospective check is E009's stream after 11-03 with owner sign-off, as CB5-K).
- Scores: N 3, EV 3, C 2.

### F. Information timing from public sources not yet joined to Polymarket

**CH74. Docket-first: court rulings appear on public dockets (CourtListener/RECAP, court websites) minutes before
news outlets report them, legal-outcome markets reprice with a lag of tens of minutes, and the move is large
(20-90c) relative to the 3.5c taker hurdle.**
- Mechanism: the information is public at the docket timestamp; the market's repricing waits for a human to read
  it. CH28 (scheduled statistics) and CH49 (scheduled hazards) cover *when*; this covers a source with a *precise
  public timestamp* and a large payoff per event.
- Why here: Polymarket lists many "Will the court rule / block / uphold X by date" markets (politics, 4% fee);
  the thin long tail of these reprices slowly (51% of quoted markets never trade).
- Test (`P`): historical: for resolved court-outcome markets (frozen regex on the question), find the docket entry
  time of the resolving order (CourtListener's free API; registration needed for some endpoints) and the 10-minute
  Polymarket price path; unit: market-event; primary: time from docket entry to the first 10-minute step that moves
  >= half the final move, and the executable gain of buying the correct side at the ask 10 and 30 minutes after the
  docket time, after fee and half-spread (one-sided > 0); cluster by case x day. MDE: descriptive at n < 50; about
  40 events give a 10c mean gain at SD 20c. Prospective: a docket poller is cheap, the market match is the work.
- Route and hurdle: taker within 30 minutes of the docket entry; fee 0.04 x p(1-p) and spread; the gain per event
  is tens of cents, so the hurdle is easily cleared if the lag exists; capacity is the book depth of thin markets
  (sweeps show 1c and 5c depth).
- Leakage: the docket time must be the entry time, not the document date; matching docket to market by hand before
  reading prices; survivorship (markets that never resolved on a ruling).
- Scores: N 4, EV 3, C 3.

**CH75. First-print bias in statistic-resolved markets: markets that resolve on the *first reported* value of a
revisable statistic (jobless claims, GDP advance, payrolls, box office weekend estimates) are priced to the consensus
of the *final* number; the direction of first-print-vs-final revisions is public and persistent, so the bucket at the
boundary is mispriced by the typical revision.**
- Mechanism: rules name a specific release ("as first reported by the BLS on <date>"); forecasters and the crowd
  discuss the underlying quantity; the revision history (ALFRED vintages, free) gives the sign and size of the
  first-print bias per series. CH28 is about the clock of the release; this is about *which number* the rule binds.
- Why here: economics markets are listed as bucket ladders where a 0.1-point revision moves the boundary bucket
  from YES to NO; 604 economy markets in the resdev frame year.
- Test (`P`): `h8_stats`, resolved economics and culture markets whose rules name a first-print source (frozen
  regex); unit: market; features: the series' historical mean first-print-minus-final (ALFRED, computed with
  vintages before the market's origin only); primary: resolved-YES rate minus price at 1d before the release for
  boundary buckets, split by the sign of the series' first-print bias (one-sided: the bucket favoured by the bias
  resolves more often than priced); cluster by release x series. MDE: with about 300 boundary buckets, about 5c on
  the gap, which is the size a boundary effect would have.
- Route and hurdle: taker at 1d before the release, one leg, fee 0.05 x p(1-p) and half-spread (2-3c on these
  buckets); the gain is a 5-15c mispricing at the boundary if the hypothesis holds.
- Leakage: vintages must be as of the origin; the first-print bias must be estimated on releases before the market's
  listing; releases are shared across markets (one release is one cluster).
- Scores: N 4, EV 2, C 3.

**CH76. Terminal-minute certainty in Binance-settled daily Up/Down markets: the outcome is a public function of the
Binance 1-minute candle close at 12:00 ET (verified rule text), so in the last minutes before settlement the winning
side's fair value is near 1 whenever |spot - strike| exceeds a few 1-minute sigmas, and the Polymarket ask on that
side stays measurably below 0.97 while the taker fee at 0.95 is 0.33c and the tick is 1c.**
- Mechanism: a digital option seconds from expiry with the spot far from the strike is worth 1; the book lags because
  the reward bots quote around the last mid. CH30 is the Black-Scholes value over the life; this is the last 5
  minutes with a public certainty condition and the specific settlement convention (the 12:00 candle's close is
  known only at 12:01:00 ET, which some participants may misread).
- Why here: the daily markets state the Binance source and the 50-50 tie rule in the rule text; both the strike
  (yesterday's noon close) and the spot are public to the second.
- Test (`A` + `P`): pmxt books for the daily Up/Down markets (2026-04-13 to 08-10) joined to Binance public
  1-minute klines (keyless); unit: market x minute in the last 10 minutes; condition: |spot - strike| >= 3 x the
  trailing 30-minute 1-minute sigma (no outcome used); primary: 1 - ask(winning-side-by-condition) minus fee at
  T-5, T-2, T-1 minutes, with depth at that ask (one-sided > 0.5c); cluster by day. MDE: about 100 market-days
  give 0.3c on the mean gap.
- Route and hurdle: taker in the last minutes; fee 0.33c at 0.95 and a 1c tick; the gain is 1-4c per share if the
  ask is stale; competed by bots, so the test is of what remains, not of the mechanism. Capacity is the displayed
  depth.
- Leakage: the certainty condition uses spot before `t` only; venue vs receipt clocks on pmxt (both stored); the
  settlement candle convention must be read from each market's text (hourly and 15-minute variants may differ:
  check before pooling).
- Scores: N 2, EV 2, C 2.

### G. Capacity and structure

**CH77. Where the fills are: the probability that a quoted market prints in the next 2h is predictable from the
public fields that drive the UI's lists (`volume24hr` rank, days since listing, hours to end, `oneHourPriceChange`,
event size, series membership), so a maker's capacity (fills, not edge) can be targeted and every maker route in
rounds 1-3 gains a fill model.**
- Mechanism: D1 found 51% of eligible markets never trade and 96.8% had no print in the prior hour; C1's binding
  constraint was a 6.8% fill rate. Retail flow goes where the UI shows markets: volume-sorted lists, "new",
  "ending soon", movers. All of those are functions of public Gamma fields.
- Why here: Polymarket's UI sort keys are the same fields the captures store, and the long tail is invisible to it.
- Test (`A`): unit: market-capture; target: >= 1 print in the trade sample's next window; features as above at the
  capture; walk-forward by capture day; primary: out-of-sample log-loss gain over the base rate and the print
  probability in the top decile vs the rest; cluster by event x day. Not a trading hypothesis: a measurement
  (counted as `ml_explain`). MDE: with about 20,000 sampled market-captures, a 5-point difference in print
  probability per decile is precise.
- Route and hurdle: none directly; it turns "maker route with 7% fills" into "maker route with 30% fills" if the
  model works, which changes every envelope in this file and in rounds 1-2.
- Leakage: the trade sample is a probability sample of the active frame (inclusion probabilities recorded); the
  features must be as of the capture; `oneHourPriceChange` is partly quote noise (J4), which is fine for a flow
  target.
- Scores: N 2, EV 3, C 1.

**CH78. Round-strike bump: in crypto "above $X by date" ladders the crowd overprices round-number strikes being hit
(a pinning-style bias), so the implied CDF has a bump at 50k/100k-type strikes relative to a smooth lognormal fitted
through the neighbours, and selling the round strike's YES against buying the neighbours is a hedged carry.**
- Mechanism: round strikes attract attention and lottery demand (option-market literature on strike clustering);
  the neighbours do not. CH13 tests CDF *consistency*; this tests a *signed, located* inconsistency.
- Why here: Polymarket lists dense crypto strike ladders with round and non-round strikes side by side.
- Test (`P`, fresh walk; CB5-L's `cdf/` extract is sealed for CB5): resolved crypto strike ladders since 2025-06 via
  a fresh Gamma walk (metadata, then prices at 7d and 30d before end, trade before `t`); unit: ladder-origin;
  primary: the round strike's price minus the lognormal interpolation through its two neighbours (one-sided > 0) and
  the realised-payoff version (round strikes resolve YES less often than priced relative to neighbours); cluster by
  asset x expiry. MDE: with about 200 ladder-origins, about 1.5c on the bump.
- Route and hurdle: maker on the round strike's ask with neighbour hedges; fee 0.07 x p(1-p) on taker legs (up to
  1.75c), so the bump must exceed about 3c for a taker and about 1c for a maker.
- Leakage: strike parsing from text at listing; survivorship of Gamma's listing; the interpolation model is frozen
  (lognormal with the two neighbours only; no fitting across the ladder).
- Scores: N 3, EV 2, C 2.

---

## 3. Ranked top 8

Rank = expected value if true x prior plausibility x testability now (existing stores or a fetch that completes
before `T_seal` 2026-10-22, no sealed data). "Runnable now" means the test can start this week.

| Rank | ID | One line | Runnable now | Family |
|---|---|---|---|---|
| 1 | CH66 | Neg-risk conversion dumps: same-wallet multi-member sells are mechanical; the hit bids revert | yes (trade samples, captures; Polygon logs optional) | C |
| 2 | CH71 | Reward-shadow band: discontinuity at 0.90 in spread, depth and maker mark-out | yes (captures, sweeps, trade samples) | D |
| 3 | CH60 | Ex-ante tail classifier for longshot sellers (C1's residual, declared features, fresh `h8_tail`) | yes if the fetch completes before 10-22 | A |
| 4 | CH73 | Kalshi-skewed maker: step aside for 20 min after a Kalshi move; mark-out of avoided fills | yes (historical pairs + Data API prints) | E |
| 5 | CH63 | Specificity discount: condition count in the rules predicts NO beyond price (fresh `h8_text`) | yes if the fetch completes before 10-22 | B |
| 6 | CH77 | Where the fills are: print-probability model from UI-visible fields (capacity for every maker route) | yes (trade samples, captures) | G |
| 7 | CH67 | Sibling-resolution unwind: sum-of-asks deviation and first-hour reversal after a member closes | yes (sidecar `closed` flips, sweeps) | C |
| 8 | CH61 | Geopolitics discrete tails underpriced at 7-30d in the zero-fee category (fresh `h8_geo`) | yes if the fetch completes before 10-22; n is the risk | A |

**How the families would be registered.**
- **A. Tail family (CH60, CH61, CH62).** One fresh fetch programme (`h8_tail`, `h8_geo`, `h8_bydate`) with frozen
  regexes and features hashed before the census, capped at `T_seal`, disjoint by market id from every prior run.
  One shared machinery: hold-to-resolution net, event x resolution-week clustering, the CB1 tail gate (one-sided,
  cluster-aware, bound-based) and its inverse for the tail buy. CH60's classifier is the first thing to run; CH61 and
  CH62 are its two applications (buy the class; carry outside it).
- **B. Text family (CH63, CH64, CH65).** Shared: a `description` fetch at first sighting added to the live extractor
  (cheap; it also fixes CB1-E's data failure for future cohorts), a clarification-marker exclusion, frozen regexes.
  CH63 is the primary; CH64 needs a census first; CH65 is a cost filter for the carries.
- **C. Mechanical-flow family (CH66, CH67, CH68, CH69, CH70).** Shared: episode detectors frozen before any
  mark-out, print-based targets, the J4-R increment-shuffle placebo, two-way clustering. CH66 and CH67 run on the
  captures and samples now; CH68 and CH70 add one keyless endpoint each; CH69 reuses the live monitor.
- **D. Band family (CH71, CH72).** A regression discontinuity at 0.90/0.10 and a band-by-turnover maker table; both
  on existing data; both need CH60's class filter before any hold-to-resolution number is read as a route.
- **E/F/G (CH73-CH78).** CH73 reuses the audited pairs; CH74-CH76 each need one small public-source join (dockets,
  ALFRED vintages, Binance klines); CH77 is a measurement that should run early because it reprices every maker
  envelope; CH78 needs a fresh ladder walk.

**What is honest to say about all of them.** Round 1 was carries, round 2 was being the maker in the right state,
and this round is mostly about *tails and flow identity*: who is on the other side, and whether the few events that
kill a carry can be named before they happen. The CB1 numbers that motivate family A are robustness checks on a
negative screen, not findings; a classifier that is declared after seeing which five events lost would be
hindsight, which is why every feature above is fixed now and tested on data that CB1 never touched. Fill rates,
not hypotheses, bound every maker envelope (CH77). Nothing here is edge until it has gone through screen, frozen
replication, prospective registration and an economic check at recorded prices.

---

## 4. Ideas considered and rejected, and why

- **Terminal-second latency on the 15-minute crypto markets.** The settlement source for the 15-minute variant was
  not verified today (the daily variant states Binance candles); even if stale asks exist in the last seconds they
  are competed by bots at sub-second latency that AREPO cannot measure or collect. Only the daily, minute-scale
  version (CH76) is kept, with low novelty.
- **Impossible-bucket residual value (eliminated teams, exceeded counts).** Real and riskless, but the payoff is the
  residual bid of 0.1-0.5c on a position locked for months; capital cost exceeds it. Recorded as a CH01 footnote.
- **Fee-tag twins (the same headline in a zero-fee geopolitics market and a 4% politics market).** The leading market
  would be the fee-free one and the lagging one has fees, so the taker route fails by construction; the maker version
  is CH73's logic with a worse anchor. Parked.
- **Zero-fee islands (`feesEnabled = false` markets) as the place where the small taker effects become viable.** The
  spread (2-4c) still exceeds the 0.36-1c effects; and the share of such markets outside geopolitics is unmeasured.
  Worth one census line inside the cost model, not a hypothesis.
- **Running-count "dead buckets" (tweet counts, mention counts, named storms).** The count sources are either paid
  (X), already covered (CH32 mentions) or rare (storms); the dead-bucket residual has the capital problem above.
- **Reward-parameter change events (`rewards_max_spread` or `rewards_min_size` edits) as depth shocks.** Probably real,
  a measurement, subsumed by CH19 (reward cliff) and CB3's `quote_state/` descriptives.
- **Round-number UI flows, movers-list flows, leaderboard copying.** CH20, CH37 and CH55 already hold them.
- **Weather station bias (resolution on a named station vs the city forecast).** A good CH27 moderator, but
  `h6_weather` is reserved by CB2-W with a sealed holdout; adding a feature there is a design change for CB2, not a
  new hypothesis.
- **Pre-game injury and line-up timing in sports.** CH29 (closing-line value) covers the mechanism; sports scope is
  the user's open decision; kept as a note for when the category is settled.
- **Re-testing ladders (near-rung NO, hazard residual) on the IF-H2 data.** CB1-B was untestable at 52 ladders and
  B3 is already declared for a fresh rung list at `T_rep_start`; nothing new until then.
- **Order anticipation as a taker (front-running worked orders).** CH69 is deliberately a maker-protection and
  post-sequence fade; using the sequence to trade ahead of it is excluded.
- **Proposer-activity clocks (carry when the known UMA proposer bots are awake).** A wait-distribution covariate for
  CH01, not a hypothesis; folded into CH65's features.
- **Cross-venue resolution-speed arbitrage (Kalshi settles faster for sports than UMA).** Needs capital on both
  venues; not public-data research; same reason as round 1's cross-venue arbitrage rejection.
- **Mempool reads of pending UMA proposals.** Seconds of lead at best; nothing to test at AREPO's cadence.
- **Fréchet-bound pairs (joint-event markets vs their marginals).** Too few joint-event markets exist to count.
- **Re-screening the C1 or A2 units with the new features.** Excluded by the brief and by M3: those rows are worn and
  the five events are known; every family-A test is on `h8_*` data only.
- **Holding rewards, maker-rebate loops, taker full-set arbitrage, insider detection as a route, comment sentiment,
  wash detection as alpha, parlays, API quirks, manipulation of any kind.** Rejected in rounds 1-2 for reasons that
  still hold.

---

## 5. Sources consulted (external; AREPO documents are cited inline by name)

- Polymarket Gamma API, live market rule text for "Bitcoin Up or Down on October 17?" and the ETH twin, read
  2026-10-16T23:10Z via `GET https://gamma-api.polymarket.com/markets?tag_id=102127&closed=false`: resolution on the
  Binance 1-minute candle "Close" at 12:00 ET, previous noon vs today's noon, exactly equal closes resolve 50-50,
  `resolutionSource` = Binance BTC/USDT (CH76).
- Polymarket Data API `GET https://data-api.polymarket.com/holders?market=<conditionId>&limit=3`, probed
  2026-10-16T23:10Z without a key: returns per-token top holders with `proxyWallet`, `amount`, `outcomeIndex` (CH70).
- Polymarket docs, negative risk overview (conversion gives 1 YES of every other member for 1 NO; atomic; augmented
  events with placeholders and "Other"): https://docs.polymarket.com/developers/neg-risk/overview (CH66, CH67).
- Polymarket docs, Gamma get-markets (field names; no rule fields documented there):
  https://docs.polymarket.com/developers/gamma-markets-api/get-markets
- Polymarket help centre, "How are prediction markets resolved" (markets resolve per the rules under the order book;
  UMA proposal, bond, 2-hour challenge period): https://help.polymarket.com/en/articles/13364518-how-are-prediction-markets-resolved
  (CH63, CH65).
- Polymarket docs, fees and liquidity rewards (cited in rounds 1-2; the [0.10, 0.90] two-sided rule and the
  `rate*p*(1-p)` fee shape used in CH71 and CH72): https://docs.polymarket.com/trading/fees,
  https://docs.polymarket.com/developers/market-makers/liquidity-rewards
- CourtListener / RECAP API (free, registration for some endpoints; docket entry timestamps): https://www.courtlistener.com/help/api/
  (CH74; not probed today).
- FRED / ALFRED vintage data (first-print vs revised values by vintage date): https://alfred.stlouisfed.org/ (CH75;
  not probed today).
- Binance public market data, klines endpoint (keyless 1-minute candles): https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
  (CH76; not probed today).
- Polygon public JSON-RPC (keyless log reads of the neg-risk and OptimisticOracle contracts; addresses on the
  Polymarket contracts page): https://docs.polymarket.com/developers/resolution/UMA and the contracts page linked
  from the neg-risk overview (CH65, CH66; not probed today).
