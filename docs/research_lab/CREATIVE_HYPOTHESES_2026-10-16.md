# Creative hypotheses, round 2: where money could come from on Polymarket (2026-10-16)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass of 2026-10-16 (00:44 UTC+1) at the user's request. One file; no
code, no queue specs, no commits. Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34); this file starts at CH35
and does not repeat round 1. Where an idea builds on a round-1 idea, the parent is named.

## 0. How to read this file

**What changed since round 1 (15-16 Oct results).**
- **J4 (SB2) placebo diagnosis.** The pooled 2h Gamma-mid reversal is almost entirely *between-market*. One identified
  contributor: markets toggle between a tight quote state and a wide one with a different mid. 9.6% of triple rows had a
  wide-state leg, where `|d_bm|` averaged 0.107 against 0.003 in tight legs. In the wide state one side of the book has
  vanished and the Gamma mid is displaced by about 10c. A second between-market channel exists in tight markets and is
  not understood. Consequence for every idea here: a Gamma-mid target is unusable unless tightness is required at `h`
  and `i`, the estimator demeans by each market's *expanding past* mean, and the placebo shuffles increments within
  market (the J4-R declaration). Print-based or sweep-mid targets are preferred.
- **J5.** A sibling's 1h move predicts a market's 2h Gamma-mid *reversal* (event-level, R² +0.014). It survives the
  SB2 rule but its target is the Gamma mid, so it may be correlated quote-state noise across siblings.
- **HB2 (h2 screen, placebo null).** Flow continuation is stronger in volatile (F4) and wide-spread (F5) markets, near
  resolution (F3) and when the flow comes from trades that are large for the market (F7); illiquid markets reverse
  1-day changes more (L1); all three cross-market staleness tests are null. Read as a liquidity provider: adverse
  selection is concentrated in identifiable states, so the places where a maker loses are predictable from public data.
- **Venue mechanics confirmed from the docs (cited in §5).** Makers pay no fee and receive a daily rebate equal to the
  category rebate share (crypto 20%, sports 15%, others 25%) of the fee-equivalent of *their own* fills. Taker fees are
  category-wide since 2026-03-30 (sports since 02-18). A seven-tier **taker rebate** programme started 2026-05-28/29
  (30-day weighted volume; third-party tables say 3% to 50%). Liquidity rewards are sampled once a minute at a random
  offset, scored `S = ((v - s)/v)^2 * b` (quadratic in distance from the adjusted mid, `b` an in-game multiplier), need
  two sides outside [0.10, 0.90], are normalised across makers per minute, paid daily at 00:00 UTC with a $1 floor. In
  April 2026 Polymarket put over $5M into sports rewards split into Pre and Live pools per game. The CLOB has GTC and GTD
  orders only; once an account sends a heartbeat it must send one every 5 s, and **a 10 s lapse cancels every open
  order of that API key across all markets**; the exchange has a cancel-only mode and had a planned upgrade in April
  2026 that cleared every order book, plus a 4h17m halt on 2026-08-31. UMA proposals carry a $750 bond and a 2h
  liveness; disputed markets take 4-6 days; Polymarket publishes on-chain "Additional context" clarifications; a WSJ
  analysis found the ten largest wallets hold over half the voting power in most disputes. CLOB V2 orders carry a
  **builder code** inside the signed order struct, visible in `OrderFilled` events, with builder fees on top of
  platform fees. Polymarket US (QCX LLC, a CFTC DCM) runs in parallel to the global venue with a different fee
  schedule. A Columbia study put wash volume near 25%; airdrop farmers reportedly run 100+ wallets ahead of a token.

**Data labels.** `A` = in AREPO's stores now: complete-universe 2h captures in `research_lab/snapshots` (touch, Gamma
mid, `oneHourPriceChange`, `last_trade_price`, `volume24hr`, `liquidity`, neg-risk ids, `closed`) with the sidecar
`rows_ext.csv.gz` since 11 Oct 12:00Z (`accepting_orders`, `competitive`, `open_interest`, `clob_rewards`,
`rewards_max_spread`, `rewards_min_size`, `fee_schedule`, `uma_resolution_statuses`, `series_slugs`,
`parent_event_ids`, `order_price_min_tick_size`); book sweeps twice per pass (`sweep_books.py`: touch, 1c and 5c
depth); trade samples (`sample_trades.py`: 2,000 active-frame markets per pass, hashed wallets, raw kept 3 days); the CB1
extract tables `negrisk/`, `postend/`, `rungs/`; backfills `h2_main`, `h3_power`, `h5_cb1` (10-minute prices from
listing, hashed trades, outcomes, `created_at`, `end_at`, `closed_time`) and `h6_weather` (being built); pmxt hourly
L2 books 2026-04-13 to 08-10; the IF-H2 ladder universe and panel; the cross-venue 10-minute pair history (958 pairs);
the live trade monitor (prints >= $1k every 5 min, hashed wallets, wallet age); the wallet activity cache (9,621
wallets, REDEEM rows); E011 surprise scores per capture. The E009/E010 live poller (2-min quotes on both venues) is
**sealed until 2026-11-03** and is not used by anything here. `P` = collectable read-only from public keyless sources at
modest cost. `N` = no known free source.

**Hygiene that binds every idea.** Trade before `t` (placeholder rule); scheduled anchors, never `closedTime`;
event x resolution-week clustering for carries; tightness at `h` and `i` for any mid-based target; print-based
targets where possible; the cumulative test count (M3). Category stays a parameter (sports scope is the user's call).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = an afternoon on existing data, 5 = new
collector plus weeks). My judgement, not measurements. Round-1 cost conventions apply (taker fee `rate*p*(1-p)`;
median spreads by band 4.1 / 3.0 / 2.2 / 3.0 / 2.5c; liquid round trip 1.8c).

---

## 1. Map: what the new results say about where money is

| Family | What the 15-16 Oct results suggest | Money route |
|---|---|---|
| A. Quote-state mechanics | Quotes vanish and return; the wide-state mid is displaced ~10c; vanishing is partly mechanical (heartbeat, bot outages) | maker on the vacated side; never take in a wide state |
| B. Selective liquidity provision | Adverse selection sits in known states: large-for-market prints, wide spreads, high volatility, late life; uninformed flow has identifiable sources (farmers, profit-takers, followers) | maker with state-dependent presence; reward and rebate as the fee-free floor |
| C. Resolution and rule mechanics | Close rules, dispute windows, regulation-only wording, scheduled hazards create pricing that the crowd does not read | one-leg carry or riskless pairs |
| D. Natural experiments on venue rules | Fee rollout (03-30), taker tiers (05-28) changed who can harvest gaps and what flow means | tells us which gaps remain and for whom |
| E. Behavioural flow | Series rolls, listing seeds, copy-trading cascades, UI-visible fake moves generate predictable uninformed flow | maker into the flow; small taker fades |
| F. Cross-venue structure | Kalshi has designated makers and a retail distribution channel; Polymarket has reward farmers | Kalshi as a fair-value anchor and as a flow-composition signal, not as a 10-minute lead |

---

## 2. Hypotheses

### A. Quote-state mechanics (from the J4 diagnosis)

**CH35. Quote-vacuum re-quoting: when one side of a tight book vanishes, the fair value stays near the last tight-state
mid, and a maker who re-posts the vacated side a tick inside the old level earns the old half-spread plus the gap with
little adverse selection.**
- Mechanism: the wide state is created by a cancellation, not a trade: reward bots cancel on heartbeat lapses,
  inventory limits, staleness guards and daily restarts; GTD orders expire. Nothing about the world changed in most
  cases. Nobody re-quotes for minutes because the reward bots that would do so are the ones that left, and human makers
  do not watch 120,000 markets. The money persists because the event is scattered across the long tail where no one
  competes for a 2c fill.
- Other side: retail market orders that arrive during the vacuum (they would otherwise hit the far-away residual quote,
  so the maker's fill is an improvement for them too); and, in the bad case, an informed taker whose news caused the
  bot to pull.
- Capture: maker. Rest a quote on the vacated side at (old touch minus one tick); hold until the book re-tightens
  (minutes to the next pass) and exit at the restored touch, or hold to resolution when the price is extreme. Capacity:
  thousands of vacuum onsets per day across the universe, each with tens to a few hundred shares of natural flow.
- Cheapest decisive test (`A`): population = market-captures that were tight at capture `i` and wide at `i+1` (one
  side's touch moved by >= 5c while the other moved < 1c), trade before `i`; feature = side that vanished and the
  displacement; target (mechanism) = the tight-state mid at the next tight capture minus the mid at `i`, compared with
  the displaced mid at `i+1`: if the ratio (recovery toward the old mid) is near 1 the vacuum carries no information;
  target (economic) = paper P&L of the re-quote filled by the first opposite print in the trade sample at or through
  the price, marked at the next tight mid; baseline = same-size quote posted in tight markets; metric = recovery ratio
  with event-clustered CI, fill rate, mean net per filled share; kill = recovery ratio below 0.5 (the vacuum is
  information) or fills so rare (< 2% of vacuums in sampled markets) that the route is theoretical. Sweeps (twice per
  pass, minutes apart) give a within-pass check that the vacuum persists over minutes, not seconds.
- Main way it is fake: selection on `i` tight and `i+1` wide conditions on the path, so "recovery toward the old mid"
  is partly guaranteed by regression to the mean of quote noise; use the J4-R expanding-past estimator and compare
  with a placebo that shuffles within-market increments. Second: the trade sample covers 2,000 markets per pass, so
  fills are measured on a small, non-random subset.
- Envelope: gross 1-3c per filled share (old half-spread 1-2c plus a tick), no fee, plus rebate; fills perhaps 5-20% of
  vacuums; size tiny per event; the universe-level number depends on how many vacuums a bot can cover, which is a
  rate-limit question, not a research one.
- Scores: N 4, EV 3, C 1.

**CH36. Bot-footprint outages: vacuums are synchronised across the set of markets one API key quotes (a heartbeat lapse
cancels every order of that key within 10 s), so footprints can be mapped from public books, and during a footprint
outage the remaining maker takes the whole per-minute reward share and the whole spread in every market of the set.**
- Mechanism: the docs say a 10 s heartbeat lapse cancels all open orders of the credentials; deploys, crashes and
  rate-limit incidents therefore produce simultaneous cancellations across hundreds of markets with the same quoting
  signature (same size, same distance from the mid, same `rewards_min_size` multiple). Rewards are normalised across
  makers present in each sampled minute, so a competitor absent for an hour hands that hour's share to whoever remains.
  Why it persists: outages are unscheduled; nobody has published footprints; the long tail is served by few bots.
- Other side: the treasury (reward pool) and takers who arrive during the outage.
- Capture: maker. Keep two-sided reward-qualifying quotes in markets that are normally served by one or two footprints;
  the edge is realised passively when a footprint goes dark. Capacity: bounded by the daily pools of the affected
  markets (small individually, many markets).
- Cheapest decisive test (`A`, descriptive first): population = all complete captures since 10 Oct; step 1 = cluster
  wide-state onsets by capture: how many markets go wide in the same 2h period vs the per-market base rate (a
  Poisson-mixture or simple excess count with day clustering); step 2 = within synchronised onsets, cluster markets by
  pre-onset quoting signature (depth at touch, spread, size multiples from sweeps) to estimate the number of distinct
  footprints and their coverage; step 3 = during an outage, what fraction of the affected markets still has a
  reward-qualifying two-sided quote (needs `rewards_max_spread` and `rewards_min_size` from the sidecar and depth from
  sweeps). Kill = synchronised onsets are no more frequent than the independent base rate (then CH35's vacuums are
  idiosyncratic and this idea has no footprint to exploit). A sub-case: the 2026-04 planned upgrade that cleared all
  books, if its date falls inside the pmxt window (starts 04-13), gives one venue-wide rebuild to describe (which
  markets re-acquire quotes first and how long the long tail stays unquoted).
- Fake: a market-wide news shock also produces synchronised cancellations; separate by category spread (a footprint
  spans categories, news does not) and by the absence of prints. Also 2h captures smear onset times; the within-pass
  sweep pair narrows it to minutes but only for sampled markets.
- Envelope: a footprint covering 500 long-tail markets with $5-20 daily pools each is $2.5-10k/day of pool; a one-hour
  outage transfers about 4% of that to the remaining makers: $100-400 per outage-hour, shared. Real but small; the
  larger value is knowing which markets are one-bot markets (an input to CH16 and CH45).
- Scores: N 5, EV 2, C 1 (descriptive) / 3 (live verification).

**CH37. Artefact-induced flow: the displaced wide-state mid shows up as a large `oneHourPriceChange` in the UI's movers
lists and in third-party alert bots, which brings taker flow in the direction of the fake move; a maker posting against
the displacement is filled by that flow at a price on the wrong side of the real value.**
- Mechanism: `chg_1h` tracks the mid more than the last trade (J4 descriptive: coefficient on Δmid 0.49, on Δltp ≈ 0).
  Anything keyed off the Gamma mid (the UI's price change, "top movers", Telegram alert bots, surprise detectors like
  AREPO's own) sees a 10c move that no trade produced. Retail reacts to moves. The flow is uninformed by construction
  because the move was not information.
- Other side: alert-driven takers.
- Capture: maker (post the ask above the old tight mid after a fake up-move; the bid below after a fake down-move);
  exit when the book re-tightens. Short holding (minutes to 2h). Capacity: small per event; many events.
- Cheapest decisive test (`A` with a collector tweak): population = wide-state onsets as in CH35 that were *not*
  preceded by a print in the last hour; feature = displacement sign and size; target = signed taker volume in the trade
  sample over the next hour, in the displacement's direction, and the mark-out of those prints against the next tight
  mid; baseline = tight markets with a genuine print-confirmed 1h move of the same size (the J4 "chg_1h with prints"
  rows); metric = excess directional taker share and mean mark-out with event clustering; kill = no excess directional
  volume, or mark-outs no worse than in the baseline. Collector change: direct `sample_trades.py` to include every market
  that went wide in the current pass (a targeted stratum of a few hundred markets), otherwise the trade sample misses
  most onsets.
- Fake: a vanished quote and a subsequent print are both symptoms of one informed arrival (the bot pulled because it
  saw the taker coming on another venue); the no-prior-print filter and the Kalshi check in CH38 are the controls.
- Envelope: if 10% of vacuums attract a retail print of 20-100 shares at a 3-8c displacement, that is 0.6-8 dollars per
  event; thousands of events per day; a capacity number that only matters if the fill rate is real.
- Scores: N 4, EV 2, C 2.

**CH38. Kalshi as the fair-value anchor during Polymarket vacuums: in matched pairs, when Polymarket's book goes wide the
Kalshi mid (designated market makers, retail distribution through Robinhood) locates the fair value better than
Polymarket's displaced mid or its last tight mid, so the vacated side should be re-quoted at the Kalshi-implied price.**
- Mechanism: the cross-venue study found a 10-20 minute Kalshi lead and gaps that behave like basis and stale quotes.
  The stale-quote part is exactly the wide state. Kalshi's books are kept by designated makers (press reports name
  Susquehanna) who do not vanish on a heartbeat. This is a different use of Kalshi from E009/E010: not predicting
  the next move but pricing a quote when Polymarket's own book is uninformative.
- Other side: as CH35.
- Capture: maker on Polymarket only; Kalshi is read, never traded. Holding minutes to hours. Capacity as CH35 but only
  for the 300-900 matched markets, which are the liquid ones, so size is larger per event.
- Cheapest decisive test (`A`): population = historical matched pairs (CROSS_VENUE_STUDY 10-minute data, 958 pairs)
  at Polymarket wide-state onsets (10-minute price gaps or spread proxies; where pmxt books cover the pair, use the
  book); feature = Kalshi mid at onset; target = the next tight Polymarket mid; metric = mean absolute error of three
  predictors (Kalshi mid, last tight Polymarket mid, displaced mid) with pair clustering; kill = Kalshi not better than
  the last tight mid. Must not touch the sealed E009/E010 live data.
- Fake: matcher errors (56 of 167 live pairs were once mismatched; use the audited set); Kalshi's mid is itself stale
  overnight; timestamp semantics of `prices-history` (the two conventions move the lead by 10 minutes).
- Envelope: the value is the reduction in adverse selection of CH35 in liquid pairs: if the Kalshi anchor cuts the
  re-quote's mark-out error from 2c to 1c, the maker nets about 1c more per filled share on the markets that matter.
- Scores: N 4, EV 2, C 1.

### B. Selective liquidity provision (from HB2)

**CH39. Post-print quote retreat: the adverse selection suffered by passive orders (1-7c per filled share in the economic
study) is concentrated in the minutes after a taker print that is large for the market (HB2 F7); a maker who cancels for
a fixed window after such a print and re-quotes afterwards keeps the spread and sheds most of the loss.**
- Mechanism: F7 says the continuation signal lives in large-for-market trades. A large print is public the second it
  happens (trades API, WebSocket). The maker's resting order is the first thing the informed taker hits; subsequent
  takers in the same direction are the continuation. The money persists because reward bots are paid to stay present
  (the per-minute sampling penalises absence) and most do not condition on prints.
- Other side: the informed taker (avoided) and the uninformed takers who arrive in the quiet periods (kept).
- Capture: maker. The paper rule: two-sided quote at the touch; cancel both sides for `W` minutes after any print whose
  size is above the market's trailing 90th percentile; re-quote. Holding is the spread capture (minutes to hours).
  Capacity: the reward pool plus natural flow of the quoted markets.
- Cheapest decisive test (`A`): pmxt hourly books (2026-04-13 to 08-10) with `h2_main` trades, as in ECONOMIC_CONDITIONS
  part B, but the population is *all* fills of a standing touch quote (not signal-driven ones): classify each paper
  fill by whether a large-for-market print occurred in the prior `W` in {5, 15, 30, 60} minutes (`W` declared, not
  tuned: the test is on the ordering, one Holm family); target = 2h and 6h mark-out against the history mid; metric =
  difference in mean mark-out between post-large-print fills and the rest, event-clustered; the economic line = net
  per filled share with and without the retreat rule including forgone reward minutes (reward share proxied by the
  public formula at the market's `v`, which for history must be a fixed 3c band). Kill = no mark-out difference, or the
  rule's forgone fills carry more spread than the avoided losses.
- Fake: pmxt books are hourly, so "a quote at the touch for the hour" assumes the touch did not move; the queue rule
  (fills only after displayed size) is the honest fill model; a large print and a wide spread are correlated (F5), so
  the moderator must be tested with spread as a control. Survivorship: `h2_main`'s market sample.
- Envelope: in wide long-tail markets the spread is 3-5c; the economic study saw filled passive orders lose 1-7c; if
  60% of that loss sits in the post-large-print window (which covers perhaps 10-20% of time), the retreat rule turns a
  negative maker net into roughly +1c per filled share before rewards. The claim is the concentration, not the level.
- Scores: N 3, EV 4, C 2.

**CH40. Late-life adverse selection schedule: informed flow arrives late (HB2 F3: continuation strongest near
resolution), so a maker's mark-out loss per fill rises with the fraction of the market's life elapsed; the optimal
presence schedule is to quote tight early, widen to the reward band edge late, and leave in the final window.**
- Mechanism: near the end the outcome is being decided; the people who trade then know something (score, count,
  announcement). Early in life most flow is opinion. The reward formula pays for presence within `v` regardless of
  whether the quote is at the touch, so late in life the maker can keep the reward and avoid the touch.
- Other side: late informed takers (avoided), early opinion takers (kept).
- Capture: maker. Time-varying distance from the mid as a function of life fraction and category.
- Cheapest decisive test (`A`): the CH39 machinery with life fraction `(t - created_at) / (end_at - created_at)` as the
  moderator (scheduled `end_at`, never `closed_time`); target = fill mark-out at 2h/6h and at resolution; metric = slope
  of mark-out loss on life fraction, event x resolution-week clustered; plus a per-category table; kill = flat slope.
- Fake: `end_at` is sometimes wrong (IF-H2 found rungs with `endDate` months after the deadline); markets whose outcome
  was effectively decided early have late "life" without information; use the near-extreme price as a control.
- Envelope: a maker who leaves the last 10% of life gives up perhaps 10% of spread income and avoids what HB2 and the
  economic study suggest is the lion's share of adverse selection; the net could be the difference between a losing and
  a break-even maker book. Not a large edge; a necessary component of any maker design.
- Scores: N 3, EV 3, C 1.

**CH41. Farmer-flow share: wallets that trade large volume with near-zero net position across many markets (volume-tier
and airdrop farmers, wash traders) are uninformed by construction; the share of a market's recent taker volume that
comes from such wallets predicts low adverse selection for maker fills there, and the top decile is maker-positive.**
- Mechanism: the Columbia estimate (about 25% of volume wash-like, up to 60% in some weeks), the May 2026 taker tiers
  (30-day weighted volume buys fee rebates) and the expected token airdrop all pay people to trade without a view.
  Farmers prefer liquid, tight markets and round-trip fast. Their flow pays the spread and carries no information. A
  maker who is on the other side of farmer flow earns the spread (plus rebate) at almost no adverse-selection cost. Why
  it persists: the maker must identify farmer wallets, which needs the Data API activity history, and most reward bots
  do not look at counterparties.
- Other side: farmers (knowingly: the spread is their cost of farming).
- Capture: maker. Select markets by farmer share; quote tight. Spread capture, holding minutes. Capacity: proportional
  to farmer volume, which is large in liquid markets.
- Cheapest decisive test (`A` partial, `P` for wallet stats): population = markets in the trade samples with >= 20 prints
  in the pass; wallet features from the Data API `/activity` for the hashed wallets seen (public, keyless; the wallet
  cache already holds 9,621 wallets): 30-day volume, number of markets, |net position| / volume, median round-trip
  time; frozen rule for "farmer" declared before any outcome (e.g. volume > $10k, > 20 markets, |net|/volume < 0.1,
  median round trip < 1h); feature = farmer share of the market's taker volume in the pass; target = paper maker
  fill mark-out at 2h (sweep mid) for a touch quote filled by the sampled prints; metric = slope of mark-out on farmer
  share, event-clustered, and the top-decile net; kill = no slope, or a slope driven by the liquidity correlate (test
  with `liquidity` as a control). Honest label: this is a wallet-family idea; the WA1-WA8 nulls were about direction,
  this is about the *cost* of being filled.
- Fake: farmers choose liquid markets; liquidity alone predicts low adverse selection (ECONOMIC_CONDITIONS: liquid
  round trip 1.8c). The control is essential. Also, farmer wallets may be the *makers* (farming rebates), not the takers.
- Envelope: a liquid market with 50% farmer flow and a 1-2c spread yields the maker 0.5-1c per filled share plus
  0.25-0.35c rebate at p near 0.5, against near-zero adverse selection on the farmer half; the informed half is the
  risk. In dollars this scales with farmer volume, which press and the Columbia study put in the hundreds of millions
  per month across the venue.
- Scores: N 4, EV 4, C 2.

**CH42. Disposition sellers at high prices: sells of YES at 0.85-0.97 from wallets that are in profit on the position are
profit-taking, not information; a maker's bid at those prices filled by such sells has a positive mark-out and a
favourable resolution excess, whereas sells from wallets in loss or new to the market are informed.**
- Mechanism: the disposition effect (realise gains early) is robust in retail trading; here the "gain" is a position
  bought at 0.40 now at 0.90. Nothing in the holder's decision to cash out carries news. The counterparty who buys at
  the bid earns the half-spread and the carry to resolution. Wallet positions and entry prices are public (Data API
  `/positions`, `/activity`), so the classification is causal.
- Other side: profit-taking holders.
- Capture: maker (resting bids 1-2c below the mid on the favourite side) with hold to resolution; also the two-sided
  reward quote at extremes (both sides required above 0.90), where the ask is lifted by "lock-in" buyers and the bid
  is hit by profit-takers, both uninformed if the mid is fair.
- Cheapest decisive test (`A` partial, `P`): population = sampled prints in markets with mid >= 0.85, side = sell of
  the favourite; feature = seller's unrealised P&L on the position before the print (from `/positions` snapshots and
  entry prices in `/activity`), and seller age in the market; target = 6h mark-out and payout minus print price;
  baseline = sells from wallets in loss / new; metric = difference in mean mark-out and resolution excess, event x
  resolution-week clustered; kill = no difference, or an effect confined to a few events.
- Fake: wallets in profit are, by selection, in markets that moved up, which may continue (momentum) or revert; use
  market-level controls (own 1-day change, print-confirmed). Positions API may lag.
- Envelope: half-spread 1c plus a favourite resolution excess that round 1's PX2/PX4 found absent on the mid; so the
  realistic gross is the spread and the avoided adverse selection, perhaps 1-1.5c per filled share held hours to days.
- Scores: N 4, EV 2, C 2.

**CH43. Surprise score as the maker's risk filter: E011's ungated learned surprise score (volatility-driven: low `rv_1d`,
high `rv_7d`) predicts large moves; maker fills in high-score markets have worse mark-outs, and restricting presence to
low-score markets turns the paper maker net from negative to about zero or positive.**
- Mechanism: the detector already exists and is scored on every capture (60 alerts + controls per capture; stage-1
  proxies for the universe). A move predictor is, for a maker, an adverse-selection predictor. No one else has this
  particular score; the general idea (quote wide when vol is coming) is standard, which is why the test is cheap and the
  edge is small.
- Other side: takers who trade in markets about to move.
- Capture: maker; a presence filter. Holding: spread capture.
- Cheapest decisive test (`A`): population = markets in the trade sample with a stage-1 surprise proxy at capture `i`;
  target = paper fill mark-out at the next sweep mid and at 24h for a touch quote; metric = mark-out by score decile,
  event-clustered; kill = flat. Must not read E011's registered outcome labels before 2026-11-11; the maker mark-out is a
  different target on different rows, but the analysis should be logged as development and kept away from the E011
  analysis script.
- Fake: the score correlates with spread and liquidity (volatile markets are wide); control for both. Also the score was
  fitted on `h2_main` price paths and the maker test must not re-tune it.
- Envelope: avoided loss of 1-3c per fill in the top deciles; forgone spread in those markets (which are also the
  widest, so the forgone spread is real). Small, but almost free to test.
- Scores: N 3, EV 2, C 1.

**CH44. Live-pool sports quoting at the band edge: during in-play periods the Live reward pool (with its in-game
multiplier) is split among very few qualifying quoters because score events make touch quoting lethal, so a two-sided
quote parked at the maximum spread earns a large share of the Live pool with a fill probability near zero.**
- Mechanism: the April 2026 programme split each game's pool into Pre and Live; the scoring function pays
  `((v - s)/v)^2` so an order at 80% of `v` scores 4% of a touch order, but 4% of a pool nobody else is in is the whole
  pool. During live play most makers pull or widen beyond `v`. Why it persists: the pool is per game and small; the
  bots that could do it are the ones that are afraid of the live state; the arithmetic is public but the per-minute
  qualifying depth in live states is not published anywhere.
- Other side: the treasury (reward pool); occasionally a taker who sweeps through 80% of `v` after a goal (the fill
  risk).
- Capture: maker, far from the touch, both sides, refreshed after each scoring event. Capacity: the Live pools.
- Cheapest decisive test (`P`): a game-time book poller (CLOB WebSocket or REST every 30 s) on a sample of games with
  reward settings read from Gamma (`clobRewards`, `rewardsMaxSpread`, `rewardsMinSize`), recording qualifying depth per
  side per minute; feature = minute of play; target = qualifying depth and number of distinct price levels; metric =
  live vs pre-game ratio with game clustering; plus the paper reward share of a band-edge quote; kill = qualifying depth
  does not fall in play (ratio > 0.7) or the band-edge quote is filled in more than 5% of game-minutes. Sports scope is
  the user's decision; the design stays category-parametric (any market with a scheduled live period).
- Fake: the in-game multiplier and the Live pool sizes may be lower than the Pre ones (the docs do not publish `b`);
  the qualifying depth may be dominated by one designated partner that never leaves.
- Envelope: a $500 Live pool per game shared by two quoters is $250 per game for a few hundred dollars of capital at
  risk of one adverse fill; dozens of games per day. Real but entirely a subsidy; disappears when the programme ends.
- Scores: N 4, EV 3, C 3.

**CH45. Reward geometry screen: markets whose configured `rewards_max_spread` is several times their natural spread pay
for quotes that essentially never fill, so the pool-to-qualifying-depth ratio at the band edge identifies a near-riskless
subsidy; the screen across 18,800 reward-enabled markets is the product, not any one market.**
- Builds on CH16 (reward per adverse selection); the angle here is the configured geometry (`v` vs observed spread)
  rather than the fill-loss ratio, and it needs only the sidecar and sweeps.
- Mechanism: `v` is set per market by Polymarket and rarely updated; natural spreads tighten as markets mature; where
  `v` = 10c and the spread is 1c, a quote at 8c from the mid is 4% of a touch quote by score but has a fill probability
  near zero. The per-minute normalisation means its share depends on how many others sit in the band.
- Other side: the treasury.
- Capture: maker at the band edge; capital parked; the only risk is a sweep through 8c (a surprise move: CH43 is the
  filter).
- Cheapest decisive test (`A`): population = reward-enabled markets in the sidecar with a two-sided sweep; feature =
  `v / observed spread` and the pool (`clob_rewards`); target (mechanism) = probability that any print in the trade
  sample occurred at >= 0.8 `v` from the mid within the pass (fill proxy), and the 5c-depth as a lower bound on
  competing depth; metric = paper reward of a min-size band-edge quote divided by expected fill loss, by decile of
  `v / spread`; kill = fill proxy above 1% per pass-hour in the top decile, or 5c depth so large that the share is
  below $1/day (the payout floor).
- Fake: sweeps store only 1c and 5c aggregates, so the competing depth at 8c is unknown (a level-by-level book
  collector on the top screen candidates is the fix, `P`, cheap); our own quote dilutes the pool.
- Envelope: $5-20 daily pools on long-tail markets; if a $200 band-edge quote takes 20% of a $10 pool, that is 1% per
  day on parked capital, before the rare sweep. Honest: it is a subsidy harvest, and known to farmers; the research
  content is the systematic screen and the fill-risk measurement.
- Scores: N 2, EV 3, C 1.

### C. Resolution process and rule mechanics

**CH46. Pre-close liquidity dump: in markets that stop accepting orders before the outcome is known, holders who need to
exit sell into a thinning book in the final window; the last prints before `accepting_orders` flips are at a discount to
the eventual payout, and a resting bid in that window is filled at that discount.**
- Mechanism: once a market closes, a position is locked until resolution (hours to weeks); holders who want liquidity
  (or who fear a 50/50 or a long dispute) sell before the door shuts; makers pull before the close because they cannot
  manage inventory afterwards. The flip time is scheduled (Gamma exposes the accepting-orders state and in many markets
  a timestamp) and so are the end dates. Why it persists: it only exists in markets with a close-before-resolution rule,
  and the window is short.
- Other side: liquidity-needing holders; makers who left.
- Capture: maker bids (and asks for the symmetric NO-side dump) in the final hour; hold to resolution. Capacity: the
  dumped size.
- Cheapest decisive test (`A` since 11 Oct): population = markets whose sidecar `accepting_orders` went true -> false
  while `closed` stayed false and no outcome was known (UMA status not proposed), with a trade in the last 6h;
  bracket the flip to the 2h capture (or Gamma's timestamp where present); feature = minutes before the flip;
  target = payout minus print price for sampled prints in the final 2h, and the last tight mid before the flip vs
  the payout; baseline = prints 24h earlier in the same market; metric = mean discount with event x resolution-week
  clustering; kill = no discount, or fewer than 50 such markets per week (then it is a curiosity).
- Fake: outcome-dependent close (a market that closes because the event happened) is not a dump but information; the
  population must be defined by the scheduled close and checked against `closed_time` only afterwards. The trade sample
  may not cover the final hour of most such markets (add a targeted stratum: markets within 6h of a scheduled close).
- Envelope: a 2-5c discount on a position held days to resolution, one leg, no exit cost. If the population is a few
  hundred markets a week, it is a modest, repeatable carry. Unknown until the sidecar window shows how many markets
  close before resolution.
- Scores: N 4, EV 3, C 1.

**CH47. Dispute lottery: during the 2h liveness after a UMA proposal the losing side trades at 0.5-2c; in large,
contested or ambiguously worded markets the dispute rate is high enough that buying the losing side is a positive-EV
lottery (50/50 pays 0.50; a reversal pays 1.00; a "too early" dispute reopens the market).**
- Builds on CH02/CH03 (the proposed side); this is the opposite leg of the same machinery.
- Mechanism: the base rate of disputes is concentrated: by volume, by category (politics, crypto rules), by wording
  ("confirmed", "officially", "announced"); the Strategy-BTC market shows how a clarification can flip an $85M market.
  Buyers of the 1c side are seen as fools, so no one competes to be one; but the EV only needs a dispute rate of about
  2-4% on the right subset.
- Other side: holders dumping the losing side at 1c to free capital; proposers' bond economics.
- Capture: taker at 1-2c during liveness, hold 2h (or 4-6 days if disputed). Capacity: the 1c side's depth, which is
  often large (people dump).
- Cheapest decisive test (`P` then `A`): Polygon log scan of the Optimistic Oracle (`ProposePrice`, `DisputePrice`,
  `Settle`) for 2026-04 to 08 joined to pmxt books at proposal time and to `h2_main` outcomes; population = proposals
  with a two-sided book; feature = volume decile, category, a frozen wording-ambiguity rule, first vs re-proposal;
  target = settlement value of the losing side minus its ask at proposal + 10 min; metric = dispute rate (Wilson) and
  mean net by subset, clustered by week (DVM rounds batch); kill = no subset with dispute rate above the ask.
- Fake: the ask on the losing side during liveness may be empty (nobody sells at 1c) so the "lottery" is not
  purchasable; disputes that re-propose the same outcome pay nothing; the subset selection is multiple testing.
- Envelope: price 1.5c; if 3% of the subset disputes and half of those end 50/50 or flipped, EV is about 0.03 * 0.6 *
  0.5 = 0.9c gross on 1.5c at risk, minus 0.1c fee: positive but tiny per share; heavy-tailed; a few dozen qualifying
  markets a month.
- Scores: N 4, EV 1, C 3.

**CH48. Regulation-only rule misread: Polymarket's "to win" sports markets that resolve on regulation time (with a draw
outcome) coexist with "to advance" or "to qualify" markets for the same tie; retail prices the regulation-only favourite
as if it included extra time and penalties, so its YES is overpriced by roughly the favourite's share of the
extra-time probability, which is a few points in knockout football.**
- Mechanism: the rule text ("first 90 minutes plus stoppage") is read by few; the headline is "who wins". The
  structural relation `P(win in regulation) = P(advance) - P(advance after a draw)` is checkable against the draw
  market in the same event. Why it persists: per-tie it is small and seasonal (cups); bookmakers price it correctly, but
  sportsbook sharps do not trade Polymarket's long tail.
- Other side: casual buyers of the favourite.
- Capture: NO on the regulation favourite (or the pair: NO on "win in regulation", YES on "advance") held to the match.
  Capacity: match liquidity (large for big cups).
- Cheapest decisive test (`P` with `A` outcomes): Gamma descriptions (one fetch per sports market; `description` is not
  stored) for frozen rule-text rules; population = ties with both market types and a draw market; feature = implied
  `P(draw)` and the favourite's regulation price; target = payout minus ask; baseline = the same favourite's "advance"
  market; metric = mean net with tie clustering; kill = under 100 ties per season or no excess. Historical `h2_main`
  sports questions give the text for a first count. Sports scope undecided (parametrised as "rule-scoped outcome
  markets", which also covers "in regulation" rules in hockey and basketball).
- Fake: three-way markets with a draw are usually priced jointly by the same bots; the "misread" may already be
  arbitraged in liquid ties and only appear in illiquid ones where the spread eats it.
- Envelope: knockout draw probability about 25%; favourite's share of extra-time outcomes about 55%; regulation YES
  overpriced by about 3-4 points if the crowd fully misreads, more likely 1-2 points in practice; fee at 0.5 is 1.25c;
  half-spread 1c; marginal, seasonal.
- Scores: N 4, EV 1, C 3.

**CH49. Calendar-gated ladder pairs: when a ladder's event can only occur on scheduled dates (FOMC decisions, earnings,
court dates, launches, votes), two adjacent rungs with no scheduled date between them must have identical value; any
executable gap between them is a riskless pair under the calendar constraint, unlike the statistical hazard residual.**
- Builds on CH06 (hazard residual, statistical) and CH12 (dominance, which needs `ask(far) < bid(near)`); here the
  constraint is an equality, so both directions are tradable: buy YES on the cheaper rung and NO on the dearer one.
- Mechanism: retail pays for "more time" even when the extra time contains no decision date; the rung prices are set by
  different people and bots that do not read calendars. Why it persists: the calendar must be curated per ladder
  family; the gain per pair is a few cents; capital is locked to the later deadline.
- Other side: buyers of time that contains nothing.
- Capture: two taker legs (or two maker legs for the fee-free version), hold to the later deadline. Capacity: rung depth.
- Cheapest decisive test (`A` for the panel, public calendars frozen in advance): population = IF-H2 ladders whose stem
  matches a frozen list of scheduled-event families (Fed rate decisions with the published FOMC calendar; earnings with
  announced dates; court rulings with scheduled hearing dates where published); feature = `|ask_k - bid_{k+1}|` and
  `|ask_{k+1} - bid_k|` for adjacent rungs with no scheduled date between; target = frequency, size after fees and
  realised payoff of the pair held to the later deadline (payoffs must be equal by construction; the test is that they
  are, and what the gap was); metric = pair-hours per week with net > 0.5c, clustered by ladder; kill = under 5 such
  pair-hours per week, or a non-zero rate of unequal payoffs (then the calendar rule was wrong, which is the real risk:
  emergency meetings, surprise announcements).
- Fake: the calendar is not a certainty (emergency FOMC meetings exist; earnings dates move; courts rule off-schedule);
  the "riskless" label holds only up to that probability, which must be priced. Rung `endDate` errors.
- Envelope: gaps of 1-4c on rungs priced 0.1-0.6; fees two legs about 1-2c as taker (zero as maker); hold weeks; a
  handful of pairs at any time. Small and clean.
- Scores: N 4, EV 2, C 1.

**CH50. Series roll flow: when a member of a recurring series resolves (weekly charts, weekly box office, daily weather,
weekly games, monthly data), holders mechanically re-enter the next member within hours; the next member's price rises
on that uninformed buying and reverts over one to two days, so a maker's ask into the roll is filled above fair.**
- Mechanism: redemption releases capital at a known moment; the venue's UI surfaces the next member on the same page;
  habitual traders repeat the same bet. The flow is time-stamped by the predecessor's resolution, which is public and
  scheduled. Why it persists: the effect is per series and per week, small in cents, and spread over hundreds of series.
- Other side: rollers (habitual re-entrants).
- Capture: maker asks on the rolled-into side (whichever side the predecessor's holders won on, since winners roll more
  than losers), posted in the hours after the predecessor resolves; exit over 1-2 days or hold if the series
  base-rate (CH51) agrees. Capacity: roll size, small per market, many series.
- Cheapest decisive test (`A`): sidecar `series_slugs` groups members; `h2_main`/`h3_power`/`h6_weather` give 10-minute
  prices and trades for closed members; population = series with >= 8 resolved members and a successor open at
  resolution; origin = predecessor's resolution time (UMA settle or `closed_time` only as the roll trigger, never as an
  outcome anchor for the successor); feature = which side won the predecessor; target = successor's print-confirmed
  price change over +6h and its reversal over +48h; baseline = the same successor at random non-roll times; metric =
  mean excess move and reversal, clustered by series x week; kill = no excess move or no reversal (then the roll is
  informative, which is itself worth knowing).
- Fake: the predecessor's outcome *is* information for the successor in many series (a hot song stays number one; a
  team's form); separate by series type (independent outcomes such as weather and data releases vs persistent ones) and
  test the reversal, not the move.
- Envelope: a 1-3c transient on the rolled-into side; a maker captures part of it plus the spread; hundreds of series,
  one event per member. Modest and repeatable.
- Scores: N 4, EV 2, C 1.

**CH51. Series base-rate calibration: within a recurring series the leader's price at a fixed point before resolution is
miscalibrated in a stable, series-specific direction that earlier members reveal; a per-series calibration map beats the
price out of sample on later members.**
- Mechanism: T5-DEV found no price-only model beats the recalibrated price *pooled*; a per-series map is a different
  object: the same crowd makes the same mistake every week on the same question type (weather buckets, chart leaders,
  "will X tweet N times"). Why it persists: each series is small; nobody fits 300 maps; the crowd on a series is
  habitual.
- Other side: the habitual crowd.
- Capture: hold-to-resolution on the side the series map favours, taker at the ask or maker inside the spread.
- Cheapest decisive test (`A`): population = series with >= 12 resolved members in `h2_main`/`h3_power`/`h6_weather`
  with a trade before the origin; origin = `end_at` - 24h; feature = leader price and a per-series isotonic or
  two-parameter calibration fitted on members resolved before the origin only; target = payout minus executable ask;
  baseline = pooled recalibration (T5's winner); metric = out-of-sample log loss and net per share per series, clustered
  by series x resolution week, with Holm over series families (not individual series); kill = no family beats the
  pooled map at an MDE declared from the member counts.
- Fake: survivorship of series (discontinued series vanish from Gamma listings); multiple testing across hundreds of
  series (hence families); regime change within a series (weather markets changed bucket widths over 2026).
- Envelope: 2-5c calibration gaps on 0.3-0.7 prices in the best families; fee 1c; one-leg spread 1-2c; holds of a day.
  Capacity is the series' liquidity, small for most.
- Scores: N 3, EV 3, C 1.

### D. Natural experiments on venue rules (where did the money go)

**CH52. Taker-rebate tiers (2026-05-28) narrowed the harvestable band: executable structural deviations (sum of asks below
1 in neg-risk events, ladder dominance) became smaller and shorter-lived after high-tier takers' effective fee halved,
so the residual gaps are exactly those below the Obsidian fee and are harvestable only by makers.**
- Mechanism: the fee band (round 1 CH34) is the gap size below which no taker closes it. The tier programme gives
  $10M/30-day takers a 50% rebate (third-party figure; the docs confirm seven tiers), halving their band. A step change
  on a known date is a natural experiment on who harvests what.
- Other side: none (this is a measurement). It tells CH09/CH12/CH13-type designs how much is left and for whom.
- Capture: none directly; maker-only routes for the residual.
- Cheapest decisive test (`A`): pmxt hourly books (04-13 to 08-10 straddles 05-28); population = non-augmented
  neg-risk events with all members two-sided (CB1-D's extract rules applied to pmxt) and IF-H2 ladders with both rungs
  in pmxt; feature = date relative to 05-28; target = size and half-life of `sum ask - 1 < -0.02` states and of
  `bid(near) > ask(far)` states; metric = before/after difference with event clustering and a placebo date (05-07, three
  weeks earlier); kill = no change (then tiers did not matter, also informative). Note the sports fee start (02-18) and
  the category rollout (03-30) predate the window, so they cannot confound within pmxt.
- Fake: liquidity trends over the summer; the fee step of 07-10 inside the window (declare both dates; test the pair).
- Envelope: no money; a map of residual gap sizes by category after 05-28, which sets the floor for maker-only designs.
- Scores: N 4, EV 2 (as an organising result), C 1.

**CH53. The fee rollout (sports 2026-02-18, most categories 03-30) changed what flow means: taker fees made wash and
farming volume costly, so the informed share of flow rose; flow-continuation coefficients and maker adverse selection per
fill are higher after the rollout, and volume features estimated on pre-fee data are not comparable.**
- Mechanism: the Columbia study's 25% wash estimate is pre-fee; a 1c fee per share at p = 0.5 kills most wash loops.
  Flow signals (E007, HB1/HB2) were estimated on windows spanning the change. If wash volume was uninformed noise, its
  removal raises the per-unit informativeness of what remains.
- Other side: none (measurement), but it changes the maker's cost of a fill and the taker's fee at the same time.
- Capture: none directly; a maker should expect higher adverse selection per fill after 03-30 and price quotes
  accordingly; a flow-signal design should be estimated post-rollout only.
- Cheapest decisive test (`A`): `h2_main` trades and 10-minute prices; HB1's flow-continuation test (F-family) run on
  two frozen windows, 2025-12 to 2026-02 and 2026-04 to 06, same specification; target = continuation coefficient per
  unit signed flow and (for the maker reading) the mark-out of prints; metric = difference with event clustering and a
  placebo split at 2026-01-15; kill = no difference. Also report the share of volume in wallets with near-zero net
  position (the CH41 farmer rule) before and after.
- Fake: the two windows differ in composition (election cycles, sports seasons); the category parameter and a sports
  vs non-sports split with their different fee dates are the control (sports changed on 02-18, others on 03-30: a
  staggered design).
- Envelope: no money directly; it decides whether flow signals and maker cost models need post-fee re-estimation
  before anything else is registered.
- Scores: N 3, EV 2 (methods), C 1.

**CH54. Builder-code flow composition: CLOB V2 orders carry an on-chain builder code (visible in `OrderFilled` events on
the CTF Exchange V2), so taker flow can be classified by originating app; flow from copy-trading and bot apps differs in
informativeness from native-UI flow, and a market's recent builder-attributed share predicts continuation vs reversal and
the maker's adverse selection.**
- Mechanism: builders charge a fee on top of platform fees, so their users are the least price-sensitive takers on the
  venue; copy-trading apps generate correlated, delayed flow; trading bots generate fast, informed or wash flow. The
  code is public per fill and builder profiles are queryable. Nobody in the published research has used it.
- Other side: builder-app users (as the uninformed component) and bot flow (as the informed one, to be avoided).
- Capture: maker presence and skew by builder-share; a taker fade of copy-app cascades (CH55).
- Cheapest decisive test (`P`): Polygon log scan of `OrderFilled` events on the V2 exchange (free public RPC, bounded
  to the markets in the trade sample for one month); join to the Data API trades by transaction hash; feature = share
  of a market's 6h taker volume by builder class (frozen classes: native, copy/social apps, bot/API builders, other,
  from the public builder profiles); target = 6h continuation of signed flow by class and the mark-out of a paper
  touch quote filled by each class; metric = per-class slope and mark-out, event-clustered; kill = classes
  indistinguishable.
- Fake: the native UI may itself be attributed with a builder code (then "native" is not identifiable); builder codes
  can be shared across very different users; the V2 migration date bounds the history (the docs do not give it; the
  scan will).
- Envelope: if copy-app flow is 5-10% of volume in popular markets and has a 2-4c adverse mark-out *for the taker*
  (i.e. favourable for the maker), that is the maker's best counterparty class; a per-class skew could add 0.5-1c per
  filled share in those markets.
- Scores: N 5, EV 3, C 3.

### E. Behavioural flow

**CH55. Leaderboard-follower cascade: public leaderboard wallets are copied by bots and apps; after a leader's print,
follower flow arrives in the same direction within minutes and then reverts, so a maker ask posted immediately after a
leader buy sells to followers above fair, and a leader buy followed by no reversion is the informed case.**
- Mechanism: Polymarket's leaderboard and profile pages are public; copy-trading tools are widely sold; CLOB V2 builder
  codes (CH54) may even name them. Followers pay the spread and move the price; the leader's information, if any, is
  already in the first print. Why it persists: the cascade is short, in liquid markets, and requires watching prints at
  second resolution.
- Other side: followers.
- Capture: maker (asks after a leader buy, bids after a leader sell), exit at the re-tightened mid within an hour;
  capacity: follower size per cascade (hundreds to thousands of dollars in liquid markets).
- Cheapest decisive test (`P`, with existing hashing): a 30-second Data API trades poller on the top-200 leaderboard
  wallets (public addresses, HMAC-hashed with the existing key so the live trade monitor's hashes join); population =
  leader prints >= $500; target = signed follower volume (prints by other wallets, same direction) in the next 2, 10
  and 60 minutes, and the mark-out of those prints at 2h against the sweep mid; baseline = matched prints by non-leader
  wallets of the same size and market; metric = excess follower volume and follower mark-out, event-clustered; kill =
  no excess follower volume, or follower mark-outs not negative (then the "followers" are co-informed, not copying).
  The live trade monitor (5-minute poll, >= $1k) gives a coarse first look now (`A`).
- Fake: the leader's own order splitting looks like followers (same wallet is excluded, but a leader with several
  wallets is not); leaders trade on news that others also see (co-arrival), so a cascade with no reversion is
  information, which is why the reversion is the test, not the volume.
- Envelope: a 1-3c follower push in a liquid market reverting within the hour; the maker captures part of it on
  hundreds of shares; dozens of cascades a day across the leaderboard.
- Scores: N 4, EV 3, C 3.

**CH56. Seed-anchor reversion: a new market's seeded opening quote (the two-sided quote present before any trade) is a
model-based anchor; the first retail trades push the price away from it, and the price reverts toward the seed over the
first days, so fading the deviation from the seed is profitable in the genesis window.**
- Builds on CH22 (genesis overpricing of sensational YES), with a different feature: the seed is the anchor, not the
  text rule.
- Mechanism: the seeded quote is placed by whoever seeds new books (Polymarket's own liquidity or a partner bot) at a
  modelled price (sportsbook-implied for games, a template for recurring series, a prior for others). The first retail
  trades are attention-driven. If the seed is a better forecast than the first trades, the deviation reverts. The T5-DEV
  rule treats untraded prices as placeholders to be excluded as *targets*; here the seed is a *feature*, and the target
  still requires trades.
- Other side: first-hour retail.
- Capture: maker on the seed side after the first trades deviate (asks when the price rose from the seed, bids when it
  fell); hold to day 3 or to resolution. Capacity: early books are thin.
- Cheapest decisive test (`A`): `h2_main`/`h3_power` raw 10-minute prices from listing (the panel excluded day 0 but
  the points exist) with `created_at` and trades; population = markets with >= 3 trades in the first 24h; feature =
  first-trade-day VWAP minus the pre-trade seed price (the first 10-minute points before any trade); target = day-3
  price minus day-1 VWAP and resolution excess; metric = slope of the target on the deviation, clustered by event and
  listing day; placebo = markets whose seed equals 0.50 exactly (an uninformative template seed, expected no
  reversion); kill = slope CI including 0, or the whole effect sitting in the 0.50-seed stratum.
- Fake: the "seed" may be the first trade itself in `prices-history` (the API's first point semantics must be checked
  against the trades); bounce at listing; sports seeds come from books that also inform later prices (not fake, but the
  mechanism differs by category: parametrise).
- Envelope: deviations of 5-15c in the first day on thin books; reversion of half of that over three days; one-leg
  entry as maker; hundreds of listings a day.
- Scores: N 3, EV 3, C 1.

**CH57. Weather model-run lag: weather markets reprice after the 00/06/12/18Z global model runs and the hourly NWS
updates with a lag of tens of minutes to hours, and the first prints after a run move toward the new forecast, so a stale
ask is executable for a while after each run.**
- Builds on CH27 (favourite underpricing) and CH28 (scheduled sources); the specific clock here is the model-run
  schedule, and the data are the `h6_weather` whole-event backfill now being built for CB2.
- Mechanism: forecasts update on a public schedule; weather bots exist but the C1 subgroup result (calibration slope
  1.5) says they have not flattened the market; most weather traders look once a day.
- Other side: stale asks (makers and retail limit orders set before the run).
- Capture: taker at the stale ask within the first hour after a run, hold to resolution (1-3 days). Capacity: weather
  books are thin (favourite spread 3.9c median).
- Cheapest decisive test (`A` when `h6_weather` is sealed, `P` for forecasts): population = temperature-bucket events
  with trades; feature = minutes since the last model run (fixed schedule) and, in phase 2, the change in the
  forecast-implied bucket probability from Open-Meteo's archived runs (free); target = time for the favourite's price to
  cover 80% of its 6h-later value after a run, and payout minus the ask at run + 30 min; metric = lag distribution and
  net per share with city-day clustering; kill = median lag under 10 minutes (bot-dominated) or net below 1c.
- Fake: `h6_weather` is CB2-W's screen and holdout set; CH57 must declare which half it reads and must not touch the
  holdout; the model-run clock is also when NWS text products update, so the "source" is ambiguous (fine for the lag,
  not for attribution).
- Envelope: a forecast shift of one bucket moves the favourite by 10-30c; if 10% of runs produce a shift and the stale
  ask survives 30 minutes with 20-50 shares, the setup is worth a few dollars each, hundreds of city-days per month.
- Scores: N 3, EV 2, C 2.

### F. Cross-venue structure beyond the lead

**CH58. Retail-channel hours moderate the Kalshi lead: Robinhood is reported to route over half of Kalshi's volume, so
Kalshi moves during US retail hours are noisier than overnight ones; the Kalshi lead's predictive value for Polymarket's
next 10-20 minutes is concentrated outside US retail hours, and a follower should condition on the hour.**
- Mechanism: the 10-20 minute lead (CROSS_VENUE_STUDY) averages over very different Kalshi flow compositions; a
  distribution channel with a million casual users injects uninformed flow at predictable hours; Kalshi's designated
  makers absorb it but the mid moves. Why it persists: the lead is already at the edge of what anyone can use; the
  conditional version has not been tested.
- Other side: Kalshi retail (indirectly, through what Polymarket then does).
- Capture: only as a conditioning rule for any Kalshi-anchored Polymarket design (CH38 and the E009/E010 family); not a
  standalone route.
- Cheapest decisive test (`A`): the historical 10-minute pair data (the audited set), not the sealed live poller;
  feature = UTC hour bucket (US retail 13:30-20:00 ET-equivalent vs other) and weekday; target = the lead-lag
  asymmetry and the 10-minute follow-through of a Kalshi move on Polymarket; metric = difference between hour buckets
  with event clustering; kill = no difference. Any live version waits for the E009/E010 single analysis after 11-03.
- Fake: Polymarket's own hour effects (TI1-TI5 null on price, but quote-state toggling may have an hour profile:
  check with the J4 wide-state rate by hour first); timestamp conventions.
- Envelope: no standalone money; a halving of the follower's false-positive rate in the right hours would make the
  cross-venue anchor usable where it is otherwise marginal.
- Scores: N 3, EV 1, C 1.

**CH59. Ladder-versus-bucket CDF consistency: the same timing question is often listed twice, as a cumulative ladder
("by June", "by December") in one event and as an exclusive neg-risk bucket event ("in June", "in July", ...,
"not in 2026"); the identity `P(by D) = sum of buckets up to D` must hold, and the executable violations are riskless
pairs that neither IF-H2's grouper nor CH13's cross-event date ladders cover.**
- Builds on CH12/CH13 (within-ladder and cross-event date dominance); the new structure is cumulative vs exclusive.
- Mechanism: the two listings are quoted by different bots (neg-risk events have conversion-aware makers; ladders do
  not); retail prefers the bucket view ("in which month"); the sum of several thin bucket asks is often far from the
  ladder's single quote. Why it persists: no page shows both; the taker fee on N bucket legs is large (round 1's fee
  arithmetic), so the pair is a maker route except in zero-fee geopolitics.
- Other side: whichever listing is stale.
- Capture: buy the cheaper representation, sell the dearer (maker legs where possible); hold to the common deadline.
  Riskless up to resolution-rule divergence between the two events.
- Cheapest decisive test (`A`): the IF-H2 metadata (303k events) and the snapshot member lists; a frozen text grouper
  matching a ladder stem to a "which month/quarter" neg-risk event on the same subject; feature = `sum ask(buckets <= D)
  - bid(by D)` and the reverse; target = frequency, size after fees, persistence over captures, realised payoff; metric
  = pair-hours per week with net > 0.5c and the inconsistent-resolution rate; kill = fewer than 20 matched
  ladder-bucket families, or an inconsistent-resolution rate above the mean gap.
- Fake: the two listings often have subtly different resolution sources or time zones (the real risk); the bucket
  event's "Other"/"not in 2026" member may be augmented (excluded).
- Envelope: gaps of 2-6c across N legs; maker legs fee-free; weeks of hold; a few dozen families. Small and clean.
- Scores: N 4, EV 2, C 2.

---

## 3. Ranked top 10

Rank = expected value if true x prior plausibility x testability now (existing stores, no new collector, no sealed
data). "Now" means the test can start this week.

| Rank | ID | One line | Runnable now | Family |
|---|---|---|---|---|
| 1 | CH35 | Quote-vacuum re-quoting: does the vacated side's fair stay at the old tight mid? | yes (snapshots, sweeps, trade samples) | A |
| 2 | CH39 | Post-print quote retreat: is maker adverse selection concentrated after large-for-market prints? | yes (pmxt books + `h2_main` trades) | B |
| 3 | CH41 | Farmer-flow share as the maker's adverse-selection predictor | mostly (trade samples + Data API wallet stats) | B |
| 4 | CH46 | Pre-close liquidity dump before `accepting_orders` flips | yes (sidecar since 11 Oct, trade samples, outcomes) | C |
| 5 | CH36 | Bot-footprint outages: synchronised vacuums and the reward share they hand over | yes (snapshots, sweeps; descriptive first) | A |
| 6 | CH52 | Taker-tier launch (05-28) as a natural experiment on harvestable gaps | yes (pmxt straddles the date) | D |
| 7 | CH50 | Series roll flow after a predecessor resolves | yes (`series_slugs`, `h2_main`/`h3`/`h6`) | C |
| 8 | CH40 | Late-life adverse-selection schedule for makers | yes (CH39 machinery, `end_at`) | B |
| 9 | CH54 | Builder-code flow classes from on-chain `OrderFilled` events | no (Polygon log scan, one month) | D |
| 10 | CH49 | Calendar-gated ladder pairs (FOMC and other scheduled-hazard ladders) | yes (IF-H2 panel + frozen calendars) | C |

**How the families would be registered.**
- **A. Quote-state family (CH35, CH36, CH37, CH38).** One machinery: wide-state onset detection from captures and sweep
  pairs, the J4-R estimator and increment-shuffle placebo, a targeted trade-sample stratum for wide-state markets (one
  small change to `sample_trades.py`), and the audited Kalshi pairs as the anchor check. CH35's mechanism test (recovery
  ratio) is the first thing to run; it decides whether any of A has a money route.
- **B. Selective-maker family (CH39, CH40, CH41, CH42, CH43, CH44, CH45).** One machinery: paper touch quotes against
  pmxt books, queue-rule fills from `h2_main` prints, 2h/6h/resolution mark-outs, reward share by the public formula,
  rebate at the category share of the fill's fee-equivalent, and a set of frozen presence filters (post-print window,
  life fraction, farmer share, surprise score, band-edge geometry). The economic study's part B already built most of
  it; what is new is that the fills are *unconditional* and the filters are the hypotheses. One registration could test
  the filters as a Holm family against the unfiltered maker baseline.
- **C. Rule-mechanics family (CH46, CH47, CH48, CH49, CH50, CH51, CH59).** Shared: scheduled anchors, resolution-week
  clustering, rule text fetched once per market (a small `description` collector, cheap), frozen calendars and text
  rules declared before any outcome.
- **D. Natural experiments (CH52, CH53, CH54).** Measurements, not routes; CH52 and CH53 should run early because they
  change the cost assumptions of everything else.
- **E/F (CH55, CH56, CH57, CH58).** CH56 is cheap and uses the untouched day-0 slice; CH55 needs a 30-second trade
  poller on leaderboard wallets (keyless, light); CH57 waits for the `h6_weather` seal and must respect the CB2 holdout;
  CH58 uses only the historical pairs.

**What is honest to say about all of them.** The round-1 ideas were mostly carries; the round-2 ideas are mostly about
*being the maker in the right state*. That is where the 15-16 Oct results point: the taker routes keep failing cost
checks, the quote-state artefact says the mid is not a price, and HB2 says the maker's losses have an address. But
maker economics on this venue are a subsidy plus a spread, and the subsidy can be withdrawn (the crypto TWAP pools
ended; the sports pools are monthly). Every envelope above is a few cents per filled share on small size; the total
depends on coverage and rate limits, not on the hypothesis. Nothing here is edge until it has gone through screen,
frozen replication, prospective registration and an economic check at recorded prices.

---

## 4. Ideas considered and rejected, and why

- **Polymarket US vs Polymarket global as a cross-venue pair.** Same brand, segmented capital, different fees, reportedly
  an order book plus an AMM; a real structure, but no public market-data API is confirmed, and the route would need
  capital on a KYC venue. Parked until a read-only feed is found; then it is CH38's anchor with a second source.
- **Inducing heartbeat outages, spoofing, quote-stuffing or any way of *causing* a vacuum.** Manipulation; not
  public-data research; excluded without analysis.
- **Proposer-reward farming (be the UMA proposer, collect the reward).** Not a market inefficiency; bond risk; a few
  dollars a proposal. Only the dispute statistics (CH47) are kept.
- **Trading on "Additional context" clarifications.** The on-chain clarification is a clean trigger (cleaner than CH08's
  `updated_at`, which CB2 found changes in bulk), but clarifications are rare (tens per year) and the direction is a
  reading-comprehension problem with no base rate; recorded for the case catalogue, not as a hypothesis.
- **Goal-overreaction fades in live football.** The literature (Croxson and Reade 2014 on Betfair) finds live prices
  efficient after goals; nothing in AREPO's data is at the right resolution to disagree.
- **The "equal or greater resolves Up" tie rule in TWAP markets.** A continuous TWAP makes exact equality essentially
  impossible; no money.
- **GTD expiry clustering at round hours as a liquidity signal.** Probably real and probably tiny; needs minute-level
  books across many markets; subsumed by CH36's outage analysis if it shows up there.
- **Cross-venue median (Kalshi, Robinhood/Rothera, ForecastEx, Crypto.com) as a fair-value estimate.** A better CH25,
  but it multiplies the matcher problem by four venues and three of them have no documented public feed.
- **Robinhood or Kalshi order-flow composition data.** Not public; CH58 uses hour-of-day as the only observable proxy.
- **Re-running momentum, reversal, flow or wallet-direction tests with the J4-R estimator.** That is J4-R's and HB2-R's
  job; this file adds only the maker-cost readings of those effects.
- **Taker-tier volume flywheel (generate volume to cut one's own fees).** A business decision, not a hypothesis; and it
  is what farmers already do (CH41 is about being on the other side of them).
- **Holding rewards, maker-rebate loops, taker arbitrage of sum-of-asks, insider detection, comment sentiment, wash
  detection as alpha, parlays, API quirks.** Rejected in round 1 for reasons that still hold.

---

## 5. Sources consulted (external; AREPO documents are cited inline by name)

- Polymarket docs, liquidity rewards (formula, minute sampling, two-sided rule, `c` = 3.0, daily payout, $1 floor,
  ended crypto TWAP pools): https://docs.polymarket.com/developers/market-makers/liquidity-rewards and
  https://docs.polymarket.com/market-makers/liquidity-rewards.md
- Polymarket docs, fees (category rates, maker fee 0, rebate shares, taker rebate programme reference):
  https://docs.polymarket.com/trading/fees
- Polymarket docs, maker rebates (rebate = own fee-equivalent share of the market's pool, daily, $1 floor):
  https://docs.polymarket.com/polymarket-learn/trading/maker-rebates-program
- Polymarket docs, taker rebates (seven tiers on 30-day weighted volume, launch 2026-05-28/29):
  https://docs.polymarket.com/trading/taker-rebates (tier percentages quoted from a third-party table at
  https://startpolymarket.com/learn/polymarket-taker-tiers/, unverified)
- Polymarket docs, CLOB orders (GTC/GTD, 5 s heartbeat, 10 s lapse cancels all orders of the credentials, cancel-only
  mode, closed-only accounts): https://docs.polymarket.com/developers/CLOB/orders/orders
- Polymarket docs, UMA resolution ($750 bond, 2h liveness, dispute path, 4-6 days, 50/50, "Additional context"):
  https://docs.polymarket.com/developers/resolution/UMA
- Polymarket docs, builders (builder code in the V2 order struct, `OrderFilled` attribution, builder fees on top of
  platform fees, public profiles): https://docs.polymarket.com/builders/fees and
  https://docs.polymarket.com/programs/builders/overview
- Polymarket docs, negative risk (conversion, augmented events, placeholders):
  https://docs.polymarket.com/developers/neg-risk/overview
- Polymarket sports liquidity incentives, April 2026 (> $5M, Pre and Live pools per game) and the fee rollout dates
  (sports 2026-02-18; most categories 2026-03-30): https://docs.polymarket.com/programs/liquidity-rewards and
  https://pineanalytics.substack.com/p/polymarket-fee-rollout
- Trading halts: 2026-08-31 CLOB failure and 4h17m halt
  (https://www.cryptotimes.io/2026/08/31/polymarket-halts-trading-for-four-hours-after-same-failure-recurs-twice-in-a-day/);
  April 2026 planned upgrade that cleared all order books (same reporting thread; date not pinned).
- Polymarket US (QCX LLC as a CFTC DCM; fee schedules differ by source): https://www.rivermarkets.com/insights/polymarket-us-fees.html,
  https://www.ingame.com/polymarket-review/, https://www.yogonet.com/international/news/2026/05/14/120500-polymarket-moves-forward-with-us-comeback-as-ios-rollout-begins
- UMA dispute concentration (WSJ analysis via Finance Magnates: top-10 wallets > 50% of voting power; one in five
  disputes with a conflicted voter) and the Strategy-BTC case:
  https://www.financemagnates.com/fintech/polymarkets-arbitration-model-faces-conflict-of-interest-questions/,
  https://thedefiant.io/news/markets/usd85m-polymarket-dispute-over-strategy-s-may-bitcoin-sale-puts-uma-s-token-voting-oracle-on
- Kalshi distribution (Robinhood reported to drive over half of Kalshi volume; Rothera, ForecastEx, Crypto.com OG):
  https://sacra.com/chat/h/3c4dec11-6c3d-496d-bb53-23cd38b63168/, https://www.theblock.co/post/409665
- Airdrop farming and wash volume: https://decrypt.co/344895/polymarket-airdrop-farmers-become-more-sophisticated-token-looms;
  Sirolly, Ma, Kanoria, Sethi (Columbia, SSRN 2025) as cited in round 1.
- Croxson and Reade (2014), "Information and Efficiency: Goal Arrival in Soccer Betting", Economic Journal (cited for
  the rejection of goal-overreaction fades).
