# Creative hypotheses: where money could come from on Polymarket (2026-10-15)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass of 2026-10-15 at the user's request. One file; no code, no queue
specs, no commits.

## 0. How to read this file

**What is deliberately excluded.** The textbook families AREPO has already run and mostly killed: own-price momentum and
reversal (E002, E004, E006, MI1-MI6), taker order-flow continuation (E007, FL1-FL10), wallet freshness and records
(WA1-WA8, HB1-R), sibling lead-lag and neg-risk *drift* (E005, L1-L4, XM1-XM6, SB2 J5), Kalshi lead-lag (E009/E010),
time-of-day and weekday (TI1-TI5), category labels (CA1-CA5), volatility features (VO1-VO5), the IF-H2 timing signal, the
7d recalibration (T5-DEV, rejected as a placeholder-price artefact), and the 95-cell cost study. A family is revisited only
with an angle that none of those designs tested.

**The one regime none of that work priced.** Every economic check so far models a *round trip*: enter at the touch, exit at
the touch about 2h to 24h later (median 4.5c per share, EXECUTION_COSTS.md). `ECONOMIC_CONDITIONS_STUDY.md` says in
its caveats: "A one-sided position held to resolution would avoid the exit half-spread, which is a different rule and is
not modelled." Most of the hypotheses below live in that unmodelled rule: one leg, fee `rate*p*(1-p)` paid once, no exit,
and the cost of capital over the wait replaces the exit spread. At p = 0.97 the one-leg cost is about 1.25c half-spread +
0.12c fee; at p = 0.03 selling YES passively costs nothing but the risk. That is a different arithmetic from the 4.5c
round trip, and it is why several "known" effects that are not tradable as round trips might be tradable as carries.

**Cost conventions used in the envelopes.** Taker fee = `rate*p*(1-p)` per leg (crypto 0.07; sports 0.03-0.05;
politics/finance/tech 0.04; geopolitics 0; makers 0). Median quoted spread by band: <0.05 4.1c, 0.05-0.20 3.0c,
0.20-0.80 2.2c, 0.80-0.95 3.0c, >=0.95 2.5c (one sweep, 2026-10-11). Liquid (>= $100k) round trip 1.8c. "Annualised" means
net gain / capital at risk * 365 / days held. Nothing is risk-adjusted.

**Data labels.** `A` = available now in AREPO's own stores (complete-universe 2h snapshots since 10 Oct with touch and
neg-risk ids; the metadata sidecar since 11 Oct 12:00Z with reward settings, `accepting_orders`, `competitive`,
`open_interest`, UMA statuses; book sweeps twice per pass; 2,000-market trade samples per pass; `h2_main`/`h3_power`
backfills with 10-minute prices-history from listing, hashed trades, `created_at`, `end_at`, `closed_time`, `uma_status`,
`outcome_prices`, question text; pmxt hourly L2 books 2026-04-13 to 08-10; the IF-H2 ladder universe and panel; the
Kalshi pair history; wallet first-trade cache). `P` = collectable prospectively with public, keyless sources at modest cost.
`N` = not available and no known free source.

**Data hygiene that applies to every hypothesis.** Historical prices for markets with no trade before the origin are
placeholders, not executable prices (T5-DEV challenger rule); every test must require a trade before `t` or read a real
book. Anchors must be scheduled times, never `closedTime`, whenever the anchor could be outcome-dependent. Dependence: cluster
by event (and parent event / neg-risk group), and for hold-to-resolution designs also by resolution week, because
positions overlap in calendar time. Multiple testing: every test here would join the cumulative count (M3 rule).

**Scores.** Novelty N (1 = known, 5 = not in the literature or AREPO), expected value if true EV (1 = pennies, 5 = large
and scalable), cost C (1 = an afternoon on existing data, 5 = new collector plus weeks of data). All three are my
judgement, not measurements.

---

## 1. Map: where could money come from?

| Family | Why the price can be wrong | Who fails to correct it | Money route |
|---|---|---|---|
| Resolution mechanics and carry | Resolution lags the decision by hours to days; oracle risk is priced crudely; capital is locked | Nobody wants to tie up capital for 3c; bots have better things to do | hold-to-resolution (one leg) |
| Structural consistency | Markets in one event, across events, or across strikes/dates must obey inequalities; fees and conversion asymmetry create bands inside which nobody arbitrages | Taker fees up to 7% define a no-arbitrage band; conversion is one-directional; UI shows one market at a time | maker inside the band; full-set carry |
| Liquidity provision | The venue pays makers (rewards, rebates); adverse selection varies by market by an order of magnitude | Reward farmers quote everywhere; few select by adverse selection | maker (reward + half-spread) |
| Behavioural / attention | New markets, sensational questions, end-of-game hope, category-wide attention days | Retail pays the ask; liquidity is thin exactly when attention spikes | sell the ask; fade as maker |
| Information timing | Public sources (weather, charts, schedules, feeds) update on a known clock before the market reprices | 51% of quoted markets never trade; repricing in thin markets takes an hour | taker at the stale ask, hold to resolution |
| Cost-side | Spreads cycle predictably around scheduled events; fee bands differ by category | n/a | makes the other routes cheaper |

---

## 2. Hypotheses

### A. Resolution mechanics and time-to-resolution carry

**CH01. Decided-but-unresolved carry: the discount on outcomes that are already known is larger than the oracle risk plus a
reasonable cost of capital, and it is predictable from the expected wait.**
- Mechanism: once the real-world event has happened, the market keeps trading until a UMA proposal passes (2h liveness
  after proposal; proposals are often made hours or days after the event; `closedTime` lags `endDate` by hours to days in
  C1's frame). The residual discount (1 - ask) compensates for (a) locked capital over an uncertain wait, (b) the small
  probability of a wrong or 50-50 resolution, (c) attention: nobody bothers for 2c. Bots arbitrage spreads, not calendar
  risk. Persistence: the capital-cost component cannot be competed away below the market's own cost of capital.
- Money route: buy the >= 0.97 side at the ask, hold to redemption. Envelope: 3c gross on 0.97; entry cost about 1.4c
  (half-spread 1.25c + fee 0.12c); if 1% of such markets resolve the other way the tail costs about 1c; net about 0.6c per
  share. Over a 3-day wait that is roughly 70% annualised; over 30 days, 7%. The whole question is the wait distribution
  and the tail rate, both measurable.
- Data: `A` (`h2_main`/`h3_power`: 10-minute prices, `end_at`, `closed_time`, `uma_status`, `outcome_prices`, fee category;
  snapshots and sidecar for live asks and `accepting_orders`).
- Minimal test: population = closed binary markets with >= 1 trade before `t`, first time the token-0 price reaches >= 0.97
  or <= 0.03 at least 2h before `closed_time`; feature = expected wait from a frozen per-category model of
  (`closed_time` - first-extreme time) fitted on earlier markets only, plus the discount at `t`; target = payout minus the
  executable ask (book sweep where available, else price + half the band spread) and the realised wait; baseline = 0 net
  after fee; metric = mean net per share and annualised return with an event x resolution-week clustered bootstrap, and
  the tail rate (wrong-side resolutions) with a Wilson interval; kill = annualised net below 10% or a wrong-side rate above
  the discount in any category with >= 100 markets.
- Overlap: PX2/PX4 (favourite drift and resolution excess at mid >= 0.85, not survivors), C1 (0.994 priced -> 1.000 realised
  at 1d, descriptive). Neither modelled the wait or the executable ask.
- Scores: N 3, EV 3, C 1.

**CH02. Proposal-window carry: after an on-chain UMA proposal, the proposed side's ask below 0.99 is a 2-hour carry whose only
risk is the dispute rate, which is tiny outside large contested markets.**
- Mechanism: a `ProposePrice` event on the optimistic oracle (Polygon) is public the second it is mined; the market keeps
  trading for the 2h liveness; the price on the proposed side should go to 0.99+. Lag between the on-chain proposal and the
  book reflects attention and the fact that most traders do not watch the chain. Dispute probability is a function of
  volume and wording (a $750 bond is only worth posting on big markets).
- Money route: taker at the ask on the proposed side within minutes of the proposal, hold 2h. Envelope: 1-2c gross at
  p = 0.98; fee 0.08c; half-spread about 1.25c; net about 0.5c in 2h, annualised in the thousands of percent on tiny size;
  bounded by depth at the ask (median top-of-book depth is small). Loss case: a successful dispute (first dispute only
  re-proposes; a reversal needs a second round) at a rate `d` costs about 0.98*d.
- Data: `P` for live (Polygon logs via a public RPC, free; CLOB books polled at proposal time). Historical: the same log
  scan over 2026-04 to 08 joined to pmxt books gives an `A`-grade development test once the scan is written.
- Minimal test: population = proposals on markets with a two-sided book at proposal time; feature = ask on the proposed
  side at proposal + 1 min and + 10 min; target = settlement value (1 or 0 or 0.5) minus ask, with the dispute flag;
  baseline = 0; metric = mean net with market-level clustering (one proposal per market, but cluster by day because
  proposals batch); dispute rate by volume decile; kill = net below 0.3c or dispute rate above the mean discount in any
  decile.
- Overlap: none in AREPO (no on-chain oracle data has been read). Literature: dispute mechanics only.
- Scores: N 4, EV 2 (size-limited), C 3.

**CH03. Dispute-state trade: when a market is disputed, the first proposal is upheld far more often than the disputed-state
price implies.**
- Mechanism: the DVM path takes 4-6 days; during it the price sits well inside (0, 1); voting is dominated by a few large
  UMA holders who overwhelmingly side with the outcome that ends up winning (press reports: nine addresses, about half the
  voting power). Whether that is "they predict well" or "they decide" does not matter for the base rate. The crowd prices
  disputes as uncertain; the base rate may be 85-95% for the first proposal.
- Money route: taker on the first-proposed side at the disputed-state ask; hold 4-6 days. Envelope: if the disputed price
  is 0.75 and the base rate 0.90, gross 15c on 0.75; fee 0.75c; half-spread 1-2c (disputed markets are liquid); huge per
  trade, but disputes are rare (tens per month) and clustered in politics, so the sample is small and heavy-tailed.
- Data: `P` live (sidecar `uma_resolution_statuses` already records "disputed" every 2h; the book sweep gives the ask);
  historical: Polygon `DisputePrice`/`Settle` logs plus pmxt books (`A` after the scan). `h2_main` only holds the final
  status.
- Minimal test: population = every dispute with a two-sided book 1h after the dispute; feature = side of the first
  proposal and the ask on it; target = final settlement minus ask; baseline = 0; metric = base rate (Wilson) and mean net,
  clustered by event and by vote week (several disputes resolve in one DVM round); kill = base rate below 0.80 or net
  below 2c, or fewer than 30 disputes in a year of logs (then "not testable", recorded).
- Overlap: none. Honest label: the mechanism is partly a governance pathology; it could change if UMA/Polymarket
  reform resolution (the holding-rewards page says a new oracle system is planned).
- Scores: N 5, EV 3, C 3.

**CH04. Decision-to-close lag and zombie quotes: after a decisive public event, automated makers keep quoting near the
pre-event mid for minutes, and the stale side is executable.**
- Mechanism: the venue has no designated market maker; reward farmers run quote bots keyed off the market's own
  mid, not off the world. When the decisive event occurs (final whistle, official result), the bot's quotes are wrong until
  a taker hits them or the bot's own staleness guard trips. The lag is the money. Press estimates of about 80 minutes for
  full repricing after major news (not peer reviewed) suggest it is not trivial in thin markets.
- Money route: taker at the stale ask immediately after the event, hold to resolution (hours). Envelope: sports
  favourite at 0.90 before the final whistle, 1.00 after: 10c gross; fee 0.27c; half-spread 1c; net about 8c if the ask is
  still there; the catch is that it rarely is, and depth is 5-50 shares.
- Data: `A` for the lag measurement (`h2_main` 10-minute paths: time from first reaching 0.95 to reaching 0.99; snapshots:
  `closed`/`accepting_orders` vs price); `P` for the trigger (sports scores from a free API such as ESPN's public
  scoreboard, or launch/announcement feeds) and for the book at event time (CLOB WebSocket, keyless).
- Minimal test (phase 1, existing data): population = sports and scheduled-event markets with trades; feature = time to
  cross 0.95; target = minutes to reach 0.99 and the number of 10-minute points with a price below 0.97 after the cross;
  metric = the lag distribution by category and liquidity; kill = median lag under 10 minutes in liquid markets (then the
  edge is bot-only). Phase 2 (prospective): the executable ask at event time + 60 s against resolution.
- Overlap: CH01 (carry after the decision) is the slow cousin; this is the fast one. E011 (surprise detector) is about
  *unexplained* moves, not explained ones.
- Scores: N 2, EV 3, C 2 (phase 1) / 4 (phase 2).

**CH05. Near-rung NO carry: the earliest-dated rung of a "by date" ladder resolves YES less often than priced; buying its NO
and holding to the deadline earns the gap.**
- Mechanism: IF-H2's descriptive result: payout minus `v1` for closed near rungs is -5.2c [-6.3, -4.1] overall and -7.1c
  after a near/far rise. Candidate causes that would persist: lottery demand for the cheap imminent rung; the near rung
  is the one the headline mentions; makers hedge across rungs and shade the near one up. Caveat the IF-H2 study itself
  gives: Gamma listing survivorship and dependence; it was never designed as a strategy test.
- Money route: buy NO on the near rung (price 1 - v1, typically 0.85-0.95) at the ask, hold to the deadline. Envelope:
  5c gross on 0.90 capital; fee 0.04*0.9*0.1 = 0.36c; half-spread 1c (median rung spread 2c); net about 3.5c over the
  rung's remaining life (days to weeks): roughly 30-100% annualised if the gap is real.
- Data: `A` (IF-H2 ladder universe and panel, 1,249 ladders, with deadlines parsed from text and payouts for closed
  rungs; live rungs in snapshots: 1,338 open rungs in 622 events on 2026-10-12).
- Minimal test: population = near rungs with >= 2 days to deadline, a trade before `t`, `0.05 <= v1 <= 0.60`, one origin
  per rung per week to limit overlap; feature = none (an unconditional carry) plus `v1` band and days-to-deadline;
  target = payout minus executable NO ask (1 - bid, from pmxt where covered else `v1` + 1c); baseline = 0; metric = mean
  net by band, clustered by ladder and by deadline week; a placebo on the *far* rung (which should not show the gap if
  the mechanism is "imminence"); kill = net below 1c after the Gamma-listing survivorship check (re-run on rungs that
  were listed in a snapshot while open).
- Overlap: IF-H2 (timing signal, null; the resolution-excess line is the seed of this), TI4 (longshot decay near scheduled
  end, null on `h2_main` where ladders were untestable), PX3 (longshots, null).
- Scores: N 3, EV 4, C 1.

**CH06. Hazard-inconsistency residual across rungs: the price of rung k, relative to the hazard implied by rungs 1..k-1,
predicts rung k's resolution excess (static mispricing, not timing information).**
- Mechanism: ladders are priced rung by rung by different people; the implied conditional hazard between adjacent
  deadlines is often absurd (for example P(by June) = 0.04, P(by December) = 0.05 implies almost no hazard in the second
  half). The far rung in such a ladder is underpriced relative to a constant-hazard fit (or the near rung overpriced).
  Page and Clemen's abstention argument (long-dated prices pulled toward 0.5) says the far rung should be too close to
  0.5. The residual persists because no instrument lets you trade "the hazard between June and December" directly.
- Money route: hold-to-resolution on the mispriced rung (buy YES on the far rung when its residual is negative, NO when
  positive). Envelope: residuals of 3-8c on 0.3-0.7 prices; fee about 1c; half-spread 1c; the hold is long (months), so
  the annualised number is low unless the residual is large; the realistic value is as a filter inside CH05.
- Data: `A` (IF-H2 panel: all rungs, hourly prices, payouts for closed rungs).
- Minimal test: population = ladders with >= 3 rungs and trades on every rung; feature = residual of rung k's price vs
  the constant-hazard fit to rungs 1..k-1 (and the reverse); target = payout minus price for rung k; baseline = own
  price (M0v) as IF-H2 used; metric = slope of the excess on the residual, clustered by ladder; placebo = the residual of a
  randomly relabelled rung order; kill = slope CI including 0 at 24h *and* at resolution.
- Overlap: IF-H2 (`ifx_term` is a *change* in the near/far ratio; this is the *level* residual across all rungs; the
  study itself said "if revisited, it needs a new hypothesis").
- Scores: N 3, EV 2, C 1.

**CH07. Postponement optionality: in weather-exposed sports markets whose rules resolve 50-50 or "No" if the game is not
played by a date, the underdog carries an unpriced option on the postponement.**
- Mechanism: the crowd prices the game, not the rule. If the rule says "resolves 50-50 if postponed beyond D", the
  underdog at 0.25 is worth `0.25*(1-q) + 0.5*q` where `q` is the postponement probability, which public forecasts
  (NWS precipitation) make observable. Persistence: the rule text is read by few; postponements are rare enough that
  nobody builds the model.
- Money route: buy the underdog at the ask when `q` is high; hold to resolution. Envelope: `q` = 0.20 gives +5c on 0.25
  (fair 0.30); fee 0.56c; half-spread 1.5c; net about 3c, over days. Rare setups (rain-outs, outdoor tennis, cricket).
- Data: `P` (market `description` holds the rule text; not stored in snapshots; one Gamma fetch per sports market;
  NWS/Open-Meteo hourly precipitation probability, free, with archived forecasts). Historical: partially `A` if
  descriptions are fetched for closed `h2_main` sports markets (Gamma keeps them) and matched to archived forecasts.
- Minimal test: population = outdoor-sport markets with a parsable postponement rule; feature = archived precipitation
  probability at the venue at game time, read 12h before; target = resolution value minus ask on the underdog; baseline =
  the same for games with `q` < 0.05; metric = difference in mean net, clustered by game day; kill = fewer than 50
  postponements in the sample (not testable) or no difference.
- Overlap: none (rule-text features have never been used).
- Scores: N 5, EV 2, C 3. Speculative.

**CH08. Rule-edit events: a change of a market's `updated_at` without a price event marks a rule clarification; the
clarified side moves within hours, and the direction is readable from the text diff.**
- Mechanism: Polymarket edits descriptions to resolve ambiguity (the Zelenskyy-suit and Strategy-sale controversies show
  how much turns on wording). The edit is public metadata; most traders learn it from the price. The direction of the
  clarification is in the diff.
- Money route: taker on the favoured side within minutes of the edit, hold hours to resolution. Envelope: unknown; the
  phase-1 test is whether `updated_at` jumps predict `|move|` at all.
- Data: `A` for phase 1 (snapshot `updated_at` every 2h since 10 Oct; `h2_main` has only the fetch-time value). `P` for the
  diff (fetch the description when `updated_at` changes; cheap).
- Minimal test: phase 1: population = markets with a trade in the prior 24h; feature = `updated_at` changed since the
  previous snapshot with |chg_1h| < 0.005 at that snapshot; target = |2h move| next period; baseline = M0v-style
  volatility controls; metric = ΔLL as in HB1 dll tests, clustered by event; kill = no ΔLL. Phase 2 adds the signed text
  diff (keyword rules frozen before any outcome).
- Overlap: none. Note `updated_at` also changes on routine metadata refreshes, so phase 1 may be dominated by noise.
- Scores: N 4, EV 2, C 1 (phase 1).

### B. Structural consistency across markets

**CH09. Asymmetric neg-risk deviations: because conversion only runs NO -> YES-of-all-others, "sum of YES bids > 1" is
arbitraged instantly while "sum of YES asks < 1" persists; the under-priced state is a full-set carry for makers.**
- Mechanism: buying NO_i, converting, and selling every YES_j is an instant arbitrage when `sum_j bid_j > 1`. The
  reverse (buy all YES_j for `sum_j ask_j < 1`) pays only at resolution: capital is locked, and taker fees on N legs sum
  to about `rate * (1 - sum p_j^2)`, up to 4-7c on a spread-out event, which exceeds most gaps. So the negative side of
  the deviation should be fatter-tailed and longer-lived, especially in high-fee categories, and makers (zero fee) can
  accumulate the set passively. Saguillo et al. found about $40M of realised rebalancing/combinatorial profits in
  2024-25, which says the instant side is harvested; this hypothesis is about the side they cannot harvest.
- Money route: (a) maker: rest bids on every YES_j at prices summing to `1 - carry - buffer`; a complete fill is a
  risk-free $1 at resolution; partial fills are directional risk; (b) taker in zero-fee geopolitics only. Envelope: gap
  3c, no fee as maker, hold weeks: 3% over the event life; for sports series (days) it is tens of percent annualised; for
  elections it is nothing. Fill completion rate is the unknown.
- Data: `A` (complete-universe snapshots carry every member's touch and `neg_risk_market_id`; exclude
  `event_neg_risk_augmented`; sidecar fee schedule per market since 11 Oct).
- Minimal test: population = non-augmented neg-risk events with 2-25 members, all members two-sided and >= 1 traded;
  feature = `S_ask = sum ask_j - 1` and `S_bid = sum bid_j - 1` per snapshot; target = persistence (half-life of
  `S_ask < -0.02` vs `S_bid > +0.02`), the distribution skew, and the paper P&L of a maker rule (bids at 0.5c inside each
  touch; fills counted when the next trade sample shows a print at or through the price); baseline = symmetric
  persistence; metric = half-life ratio with a bootstrap over events, by fee category (prediction: ordering crypto >
  sports > politics > geopolitics in persistence); kill = no asymmetry, or `S_ask < -0.02` in under 1% of event-snapshots.
- Overlap: E005/XM1/XM2 (mid-sum deviation as a drift predictor: not supported), L3 (negligible R2). None looked at
  executable asks vs bids, asymmetry, or fee bands.
- Scores: N 4, EV 3, C 1.

**CH10. Placeholder members: in events where some members have never traded, the untraded member's quote is a placeholder,
and its sibling-implied fair value is executable against the resting quote.**
- Mechanism: 51% of quoted markets never trade (D1). In a bucket event ("How many X in October: 0-2, 3-5, 6-8, 9+") the
  traded buckets pin the distribution; an untraded bucket still shows a seeded two-sided quote near its listing price.
  When exactly one member is untraded, its fair YES value is `1 - sum of traded mids` (neg-risk) and its NO is worth the
  complement; the resting NO ask on it can be far below that. Persistence: the quotes are seeded by scripts and only
  cancelled when someone trades; the T5-DEV artefact (untraded prices near 0.5) is exactly this.
- Money route: taker on the resting quote of the untraded member, hold to resolution (buckets resolve together). Envelope:
  untraded NO ask 0.60 vs implied 0.90: 30c gross; fee 1c; this is the kind of gap that exists only because nobody
  looks; size is the resting order (often 5-100 shares).
- Data: `A` (snapshots: `last_trade_price`, `volume24hr`, `volume_num` in the sidecar, touch of every member).
- Minimal test: population = neg-risk or bucket events with exactly one never-traded member (`volume_num` = 0) and all
  other members traded; feature = implied fair minus the resting ask on the untraded member (both sides); target = payout
  minus ask at resolution (closed events) and the 24h change in the ask (does it get corrected?); baseline = 0;
  metric = mean net clustered by event; the count of such setups per day; kill = fewer than 2 setups per day with
  |gap| > 5c, or gaps that vanish (quote cancelled) before the next snapshot in > 90% of cases.
- Overlap: XM1 (sum deviation over *traded* members, null), T5-DEV (placeholder prices as an artefact to exclude; here
  they are the target).
- Scores: N 4, EV 3, C 1.

**CH11. Augmented "Other" decay: in augmented neg-risk events the "Other" outcome's YES loses value mechanically every time a
placeholder is named, so it drifts down and resolves below its price.**
- Mechanism: the docs advise against trading "Other" because its definition shrinks as outcomes are named; retail buys it
  as a cheap "chaos" ticket. The value transfer to newly named outcomes is deterministic and public.
- Money route: buy NO on "Other" (price 0.90-0.97), hold to resolution or to the next naming. Envelope: 3-8c on 0.93;
  fee 0.26c; half-spread 1.5c; months-long holds for elections but weeks for awards and sports fields.
- Data: `A` (`event_neg_risk_augmented`, `neg_risk_other` flags in every snapshot; outcomes from Gamma when closed).
- Minimal test: population = "Other" markets in augmented events with a trade; feature = number of placeholders still
  unnamed (from the event's member list) and days to the event; target = 7d and 30d mid change and resolution excess;
  baseline = named members of the same event; metric = mean excess clustered by event; kill = no negative drift, or a
  positive resolution excess (chaos actually happens).
- Overlap: none (augmented events were excluded from every sibling test).
- Scores: N 4, EV 2, C 1.

**CH12. Within-ladder dominance arbitrage: `ask(YES by D2) < bid(YES by D1)` is a riskless pair (buy the far YES, buy the
near NO) that pays >= 1 at the later resolution; it occurs because the two rungs have different quote bots.**
- Mechanism: cumulative ladders must satisfy `v1 <= v2`. XM8 (violation -> drift) was untestable on `h2_main`; IF-H2
  found inconsistent ladders common enough to need an exclusion rule. The executable version has a guaranteed payoff of 1
  (if not by D1) or 2 (if between) against a cost of `ask_2 + 1 - bid_1`.
- Money route: two taker legs, hold to D2. Envelope: cost 0.97 for a payoff >= 1 with an option on 2; fees two legs about
  1-2c; the "between" state is a free lottery ticket.
- Data: `A` (IF-H2 universe plus snapshots for the touch).
- Minimal test: population = ladders with both rungs two-sided; feature = `bid_1 - ask_2`; target = frequency,
  size after fees, persistence, and realised payoff of the pair held to D2; metric = count of executable pair-hours per
  week and mean net; kill = under 5 pair-hours per week with net > 0.5c after fees.
- Overlap: XM8 (drift, untestable), IF-H2 exclusion rule (noted the inconsistency, never traded it).
- Scores: N 2, EV 2, C 1.

**CH13. Cross-event implied-CDF consistency: strikes and dates spread across *separate* events (BTC above $X by date; CPI
above Y%; "wins nomination" vs "wins presidency"; "makes playoffs" vs "wins title") violate monotonicity more often and
for longer than within-event ladders, because no page shows them together.**
- Mechanism: IF-H2's grouper excluded cross-event series ladders by design, so this universe is unexamined. The
  inequalities are logical (A implies B gives P(A) <= P(B)); violations are executable pairs with a guaranteed floor, like
  CH12, but with different resolution dates and oracles (a residual risk: inconsistent resolution across events).
- Money route: pair trade held to the later resolution. Envelope: as CH12; more setups expected.
- Data: `A` (IF-H2 metadata for 303k events; snapshots for touches); needs a grouper extension with frozen text rules.
- Minimal test: population = implication pairs found by frozen rules (same stem, different date; same asset, ordered
  strikes, same date; nomination/presidency templates); feature = `ask(dominant) - bid(dominated)`; target = violation
  frequency, size, persistence, realised pair payoff; metric = as CH12 plus the share of pairs whose resolutions were
  inconsistent (the real risk); kill = violation rate under 1% of pair-hours or an inconsistent-resolution rate above the
  mean gap.
- Overlap: none; it is the explicit gap in IF-H2 v1.
- Scores: N 4, EV 3, C 2.

**CH14. Moneyline versus spread/total consistency in the same game: the moneyline implied from the spread market (a fixed
margin distribution per sport) predicts which of the two markets moves, and the spread market is the slower one.**
- Mechanism: sportsbooks price moneyline, spread and total from one model; Polymarket lists them as separate markets with
  separate quote bots and separate retail. A simple margin model (normal with a per-sport sigma, Stern 1991) converts a
  spread price to a moneyline probability; disagreements are model-dependent, not arbitrage, but the slower market should
  converge to the faster one.
- Money route: taker on the lagging market, hold to game end. Envelope: typical disagreements of 2-4 points; sports
  fee at 0.5 is 0.75-1.25c; half-spread 1c; marginal unless disagreements are larger in live play.
- Data: `P` (Gamma `sportsMarketType` and `line` fields are not stored; one sidecar field each; historical questions in
  `h2_main` can be parsed for "spread"/"O/U" text but the line is in the title only).
- Minimal test: population = games with moneyline and spread markets both traded; feature = implied-moneyline minus
  moneyline mid; target = next-2h move of each market and the resolution; baseline = own price; metric = slope on each
  market, clustered by game; kill = neither market responds, or the sigma fit is unstable across seasons.
- Overlap: XM4/XM6 (mean sibling change, null) tested co-movement, not model-implied consistency.
- Scores: N 3, EV 2, C 3. Category scope (sports) is an open user decision.

**CH15. Tick-regime discount: at the 0.96/0.04 boundary where the tick coarsens from 0.001 to 0.01, near-certain outcomes
quoted in the coarse regime carry a mechanical discount that disappears after the tick change.**
- Mechanism: the CLOB switches tick size near the extremes (pmxt records `tick_size_change`). In the coarse regime makers
  cannot quote 0.975; they quote 0.97 or 0.98, and queue priority at 0.97 keeps the ask there. A 0.97 ask on a 0.985 fair
  value is 1.5c of pure granularity.
- Money route: buy at the coarse ask, hold to resolution (combines with CH01). Envelope: 1-2c per share; fee 0.1c.
- Data: `A` (pmxt books and tick events, 2026-04 to 08; sidecar `order_price_min_tick_size` since 11 Oct).
- Minimal test: population = tokens with mid in [0.94, 0.975] with a trade in the prior day; feature = tick regime at `t`;
  target = resolution excess over the ask and the 24h mid change; baseline = the fine-tick regime at the same mid;
  metric = difference in mean net, clustered by event; kill = no difference or the coarse regime having wider asks that
  cancel the gap.
- Overlap: none. Speculative; the regime may be rare in the pmxt window.
- Scores: N 4, EV 1, C 2.

### C. Liquidity-provision economics

**CH16. Reward-per-adverse-selection selection: the daily liquidity reward divided by the expected adverse-selection loss of
a reward-qualifying two-sided quote is predictable from public market settings, and its top decile is positive out of
sample.**
- Mechanism: rewards pay a per-minute share `Q_min / sum Q_min` of a per-market daily pool, scored by
  `((v - s)/v)^2 * size`, with two-sided quotes required outside [0.10, 0.90] and a 3x penalty on one-sided quotes inside
  it. The pool, max spread `v` and min size are public per market (sidecar `clob_rewards`, `rewards_max_spread`,
  `rewards_min_size`). Adverse selection is the loss on fills (ECONOMIC_CONDITIONS_STUDY measured 1-7c per filled share
  for *signal-driven* orders in wide markets); for a quote at the max spread in a market with few trades and low
  volatility, fills are rare and the reward accrues anyway. Reward farmers crowd the big markets, so the ratio should be
  best in the long tail. Persistence: the ratio is a public-data computation, but it requires watching thousands of
  markets, which is exactly what AREPO does.
- Money route: maker. Envelope: pool $20/day on a market with $2k of qualifying depth: a $500 two-sided quote at the max
  spread earns on the order of $2-5/day (0.5-1% per day on capital) if the quadratic score favours it; fills at a 5c
  spread lose 1-3c per filled share on perhaps 50 shares a day: $1. The sign of the net is the hypothesis.
- Data: `A` since 11 Oct (sidecar reward fields; book sweeps for competing depth; trade samples for fill proxies;
  snapshots for volatility); about two weeks of data by the end of October. Only the paper reward share is computable
  (actual maker identities are not public), and our own quote would dilute the pool.
- Minimal test: population = reward-enabled markets in the eligible frame; feature = frozen score = paper reward of a
  standard quote (min size x 2, at 80% of max spread) / (expected fills x expected loss), computed from the previous 7
  days; target = the same quantity realised over the next 7 days with fills counted from trade-sample prints at or
  through the quote and loss as the 2h mid move after each fill; baseline = a volume-ranked selection (what farmers do);
  metric = mean realised net in the top decile, clustered by event and day; kill = top-decile net <= 0 after including
  our own quote in the pool denominator.
- Overlap: ECONOMIC_CONDITIONS_STUDY part B (passive entry *driven by a directional signal*, which lost to adverse
  selection; rewards were called immaterial for *that* design because the fill was the point). Here fills are the cost
  and rewards are the point.
- Scores: N 3, EV 4, C 2.

**CH17. Longshot ask-selling with hold-to-resolution: resting asks at the touch on tokens priced <= 0.10 are filled by
lottery buyers, and the filled position (short YES) earns the half-spread plus any favourite-longshot premium with
little adverse selection, because informed longshot buying is rare.**
- Mechanism: Cardozo and Rivero-Wildemauwe report that purchases below 10c lose 19.3c per dollar (crypto and politics,
  not sports). AREPO's own tests say the *mid* is roughly fair (PX3 null; C1 longshot bins track price) and that convex
  longshot pressure carries no information (IX1, IX5, PX6). If both are right, the loss of longshot buyers is mostly
  spread and fee, and the maker who sells them the ask keeps it. The key cost saving is that a short-YES position held
  to resolution never pays an exit: it simply expires.
- Money route: maker (resting asks), hold to resolution. Envelope: ask 0.05 on a 0.03 mid; if the mid is fair, EV per
  filled share = 0.05 - 0.03 = +2c on 0.95 of capital at risk, plus the liquidity reward; 2% per fill, 10-150%
  annualised depending on the market's life. Adverse selection is the whole risk: one informed fill at 0.05 that pays 1
  costs 47 fair fills.
- Data: `A` (pmxt books for the touch and queue, `h2_main` trades for fills and `outcome_prices` for payouts,
  2026-04 to 08; sports vs non-sports split from fee category).
- Minimal test: population = tokens with mid <= 0.10, two-sided pmxt book, a trade in the prior 7 days, at 6h-grid
  origins; rule = rest an ask at the touch for 6h; fill when a taker BUY print at >= our price appears (queue rule: after
  displayed size at that level); target = ask minus payout per filled share, plus the paper reward; baseline = 0; metric =
  mean net per filled share and per attempted order, with an event x resolution-week bootstrap, separately for sports and
  non-sports; kill = negative net in non-sports, or net driven by fewer than 10 events.
- Overlap: PX1/PX3/PX6 (mid-based; PX1's +0.48c upward drift of longshots over 24h is the main threat: if it is real
  information rather than bounce, the maker is adversely selected), ECONOMIC_CONDITIONS part B (signal-driven passive
  orders; different population and no hold-to-resolution).
- Scores: N 3, EV 4, C 2.

**CH18. Off-hours maker share: the number of distinct qualifying quoters falls at specific UTC hours while the reward is
paid per minute, so a quote that stays up overnight earns a disproportionate share.**
- Mechanism: rewards are sampled every minute and normalised across makers present in that minute; a maker present when
  others are not takes the whole minute. Human-run and some bot quoters pause overnight or at weekends; the pool does not.
- Money route: maker. Envelope: if the qualifying depth halves between 02:00 and 08:00 UTC, the per-minute share
  doubles for a quarter of the day: about +25% on the daily reward for the same capital.
- Data: `A` (pmxt `book` events give full depth at any minute, 2026-04 to 08; the qualifying band needs `v`, which is
  only in the sidecar now, so use a fixed 3c band for history); `P` for live verification with the real `v`.
- Minimal test: population = reward-eligible markets (now) or markets with `competitive` depth (history); feature = UTC
  hour; target = qualifying depth and number of distinct price levels per side at each hour; metric = ratio of overnight
  to daytime qualifying depth with a day-clustered CI; kill = ratio above 0.8 (no thinning).
- Overlap: TI1/TI5 (hour and weekend effects on *price*, not on maker competition).
- Scores: N 3, EV 2, C 1.

**CH19. Reward cliff: when a market's reward programme ends (public end date in `clobRewards`), quoting depth collapses
within a day, spreads widen, and the last quoter earns a wider spread with less competition; takers who must trade should do
so before the cliff.**
- Mechanism: rewards are the reason most long-tail depth exists; its scheduled end is public metadata that nobody prices
  into their execution timing.
- Money route: cost-side for takers; maker spread capture after the cliff. Envelope: spread widening from 2c to 5c is
  worth 1.5c per share to a taker who trades a day early.
- Data: `A` since 11 Oct (sidecar `clob_rewards` JSON with start/end dates; snapshots for spread and depth).
- Minimal test: population = markets whose reward end date falls inside the snapshot window; feature = days to the
  cliff; target = spread and 5c depth before vs after; baseline = matched markets without a cliff; metric =
  difference-in-differences with event clustering; kill = no widening.
- Overlap: none.
- Scores: N 3, EV 1, C 1.

**CH20. Round-number walls: resting depth concentrates at 0.05/0.10/0.25/0.50/0.75 and ticks just inside the wall have better
fill-to-adverse-selection ratios; mid drift away from a wall is predictable from which side the wall is on.**
- Mechanism: anchoring in limit-order placement is documented in equities; a wall at 0.50 means a quote at 0.49/0.51 has
  queue priority over a large book and is protected by the wall on one side.
- Money route: maker (penny-jump the wall). Envelope: unknown; the first test is descriptive.
- Data: `A` (pmxt full-depth books).
- Minimal test: population = two-sided pmxt books; feature = depth at round levels vs neighbours (ratio) and wall side;
  target = depth ratio, and the 1h mid drift conditional on the mid being one tick from a wall; metric = depth ratio
  with a market-clustered CI; drift slope clustered by event; kill = ratio under 1.5 or no drift asymmetry.
- Overlap: MI9/MI10 (depth imbalance and microprice, null) looked at imbalance, not level clustering.
- Scores: N 3, EV 1, C 1.

**CH21. Holding-rewards mark spikes (speculative): in the 18 holding-rewards events, positions are valued at the hourly
sampled mid, which gives holders an incentive to lift the mid at the sample time; the hourly grid shows mid spikes that
revert.**
- Mechanism: 3.25% a year on mid value is small, but the sampling is hourly and the markets are thin at the edges; a
  cheap spoof of the mid at :00 raises the mark. If anyone does it, the pattern is a mid rise in the last minute of the
  hour that reverts within minutes.
- Money route: taker fade (tiny) or, more usefully, a warning that mids in those events are unreliable at :00.
- Data: `P` (poll CLOB books every 30 s around the hour for the 18 events for two weeks; keyless, trivial load).
- Minimal test: feature = minute of hour; target = |mid change| and sign of the subsequent 5-minute reversal; baseline =
  non-eligible markets of similar liquidity; metric = excess spike rate at :59-:00 with a day-clustered CI; kill = no
  excess.
- Overlap: none.
- Scores: N 4, EV 1, C 2.

### D. Behavioural and attention

**CH22. Genesis window: in the first 24 hours after listing, which no AREPO panel has examined (origins start one day after
the first price), the affirmative side of sensational non-sports questions is overpriced relative to day 7 and to
resolution.**
- Mechanism: new markets open with an empty book (no auction, no designated maker); the first traders are the ones the
  headline attracted; sports books fill fast and balanced, other categories open wide and settle over an hour or more
  (IMDEA working paper on initial liquidity). The lottery buyer arrives before the sceptic. Persistence: the window is
  short, thin and recurs with every listing (hundreds per day).
- Money route: sell the affirmative side (rest an ask, or take the NO) between hour 6 and hour 24 in markets that have
  traded; hold to day 7 or to resolution. Envelope: a 3-5c overpricing on a 0.20 YES is 15-25% of capital on the NO side
  at 0.80 over a week; fee 0.64c; half-spread 1.5c in the wide early book (a maker avoids it).
- Data: `A` (`h2_main`/`h3_power` raw 10-minute prices-history from listing and trades, with `created_at`; the panel
  rule excluded these origins but the points were fetched). Must require a trade before `t` (placeholder rule).
- Minimal test: population = non-sports binary markets with >= 3 trades in the first 24h; origin = hour 6, 12 and 24
  after `created_at`; feature = YES price and a frozen "sensational" text rule (question contains a named person and
  a dramatic verb list, frozen before any outcome); target = price at day 7 minus price at origin, and resolution excess;
  baseline = PX1/PX2 price-level drift on mature markets; metric = mean drift and excess, clustered by event and listing
  day; placebo = sports markets (expected null); kill = no negative drift for the affirmative side, or a drift that
  vanishes when the first-trade price is replaced by the first two-sided book.
- Overlap: MS1 (market age -> |move|, which *hurt* out of sample; it was a volatility feature on mature origins), PX1
  (longshots drift up over 24h on mature markets; this is a different population).
- Scores: N 3, EV 3, C 1.

**CH23. End-of-game hope premium: in the final minutes of a live sports market the trailing side's YES is overpriced by
insurance-style buying from holders of losing positions, so the leading side at 0.90-0.97 resolves more often than priced.**
- Mechanism: Moshrefi (Kalshi, 23M moneyline trades) reports step-like calibration in the final ten minutes with a
  Prelec curvature well above 1, attributed to insurance buying. On Polymarket the same crowd exists; makers pricing
  the final minutes face the same information as everyone (the score), so the premium is paid to whoever sells hope.
- Money route: taker at the ask on the leader, hold to the final whistle (minutes). Envelope: 0.92 -> 1.00 realised at
  0.96: 4c gross; fee 0.22c; half-spread 1c; net about 2.5c in 15 minutes. Hundreds of games per week.
- Data: `P` (requires a game clock: Gamma `gameStartTime` plus sport durations, or a free score feed; CLOB book polls
  every 30 s in the last 20 minutes). Historical: `h2_main` 10-minute prices can give a coarse version using the
  scheduled start plus a per-sport duration (never `closed_time`).
- Minimal test: population = sports game markets with trades in the prior hour at origin = estimated end - 15 min;
  feature = leader price in [0.85, 0.97]; target = payout minus ask; baseline = the same at estimated end - 2h; metric =
  mean net by price band, clustered by game and by game day; kill = net below 1c or the premium concentrated in one
  league.
- Overlap: PX2/PX4 (favourites over 24h / at resolution, mature markets; not survivors), C1 at the 1-day lead (no
  favourite-longshot pattern detectable). Those horizons are hours to days; this is minutes, where the literature finds
  the effect.
- Scores: N 2, EV 3, C 3. Sports scope undecided by the user.

**CH24. Category attention shocks: on days when a category's aggregate volume is in its top decile, 2h moves in markets of
that category whose own volume is *not* elevated are noise and reverse more; the money is a maker skew, not a taker fade.**
- Mechanism: a big news day brings retail into every politics market, not only the one in the news; flow without
  information moves thin quotes and reverts. The taker version is dead (E004 touch-to-touch -4.5c); the maker version
  earns the bounce as spread: during a category attention day, post quotes skewed against the recent move.
- Money route: maker. Envelope: the E004 reversal is about 4c mid-to-mid in illiquid quotes; a maker who is filled on
  the overshoot side captures part of it; adverse selection is lower when the flow is attention-driven rather than
  informed, which is the testable claim.
- Data: `A` (snapshots: `volume24hr` and fee category for every market; trade samples for prints).
- Minimal test: population = markets with a trade in the prior 6h; feature = category-volume decile of the day x own
  volume not elevated; target = next-2h reversal of the last 2h move, and in part B the fill-conditional move for a
  paper quote skewed against the move; baseline = the same on category-quiet days; metric = difference in reversal
  slope and in fill-conditional P&L, clustered by day (the shock is a day-level variable: few clusters, declare the MDE);
  kill = no difference in the fill-conditional P&L.
- Overlap: E004/E006/MI1-MI6 (own-market reversal and its moderators), XM4/XM6 (sibling moves). The category-level
  attention variable and the maker route are new; the family is otherwise saturated.
- Scores: N 2, EV 2, C 1.

**CH25. Partisan level gap: the persistent sign of (Polymarket - Kalshi) on the same political question predicts the
resolution excess on Polymarket (a crowd-composition bias), even though it does not predict the next hour.**
- Mechanism: the cross-venue study found the gap has no value for Polymarket's next 1h/6h move and that gaps persist for
  hours, "more likely basis/stale-price artefacts". A crowd-composition bias would look exactly like that at short
  horizons and only show up at resolution. Persistence: cross-venue capital is segmented (KYC, jurisdictions).
- Money route: hold-to-resolution on Polymarket on the side Kalshi says is cheap. Envelope: a 3-point level gap is 3c
  gross; fee 1c; half-spread 1c; one-leg; long holds for elections, short for scheduled votes and data releases.
- Data: `A` (cross-venue pair history with 500 matched pairs and daily prices; resolutions via Gamma and Kalshi
  settlement); power is the issue: a few hundred resolved pairs at most.
- Minimal test: population = resolved matched pairs; feature = mean signed gap over the last 7 days of the pair's life
  (Polymarket minus Kalshi, in Polymarket's YES terms); target = Polymarket payout minus Polymarket price at the same
  time; baseline = 0; metric = slope of excess on gap, clustered by event and resolution week; kill = CI including 0 with
  an MDE below 2c, or a sign that flips between the two halves of the sample.
- Overlap: CROSS_VENUE_STUDY and E009/E010 (lead-lag and next-move prediction; this is level -> resolution, which they
  did not test).
- Scores: N 3, EV 2, C 1.

**CH26. Inattentive-holder share: markets whose recent volume comes from wallets with long historical redemption lags
(they leave winnings unredeemed for days) reprice more slowly after news, so continuation is stronger there.**
- Mechanism: redemption lag is a causal, public measure of attention per wallet (REDEEM events in `/activity` vs the
  market's resolution time, using only markets resolved before `t`). Inattentive holders do not update, so their markets
  have less competition for the first reprice.
- Money route: taker continuation in slow markets (a moderator for the E007-type signal), or maker avoidance of fast
  markets. Envelope: E007 continuation is +0.36c per hour of one-sided flow; the claim is that it is several times that in
  inattentive markets; the round-trip cost of 1.8c (liquid) must still be cleared, which is doubtful.
- Data: `A` partially (wallet activity cache for 9,621 wallets includes REDEEM rows; the moderator needs the
  per-market wallet mix from trade samples with hashed wallets).
- Minimal test: population = markets with trades in the prior 24h and >= 50% of notional from wallets with a known
  redemption history; feature = volume-weighted median redemption lag; target = 6h continuation of the 2h flow sign;
  baseline = E007/FL2 without the moderator; metric = interaction slope, clustered by event; kill = no interaction. This
  is a wallet-family idea and must be justified against the Q1 nulls: it is attention, not freshness or skill.
- Overlap: WA1-WA8 (freshness, concentration, records: null), E007.
- Scores: N 3, EV 1, C 2.

### E. Information timing from public sources

**CH27. Weather favourites: in multi-bucket weather events the top-priced bucket resolves more often than priced one day
out, because retail spreads bets across buckets as lottery tickets while the public forecast (NWS/ECMWF) is sharper than
the crowd.**
- Mechanism: C1's descriptive subgroup result: science/weather calibration slope 1.52 [1.14, 2.24] at 1d (prices less
  extreme than outcomes), mean price 0.13, n = 307, unadjusted. The structural reason is bucket events: a temperature
  question with 6-8 buckets invites spreading; the favourite bucket is underbought. The forecast is public and better
  than the crowd's implied distribution. Persistence: weather markets are small and numerous; bots that read NWS
  forecasts exist but the C1 number says they have not flattened it.
- Money route: buy the favourite bucket at the ask 12-24h before resolution, hold. Envelope: 0.85 priced, 0.92 realised:
  7c gross; fee 0.05*0.85*0.15 = 0.64c; half-spread 2.2c (weather median 4.5c); net about 4c in a day. Hundreds of
  city-days per month. Capital is small per market.
- Data: `A` (`h2_main`/`h3_power` weather markets with outcomes and 10-minute prices; the C1 rows); `P` for the
  forecast-model version (NWS API and the Iowa State archived-forecast mirror, free).
- Minimal test: population = weather bucket events with a trade in the prior 24h at origin = `end_at` - 24h and - 6h;
  feature = favourite price (and later the forecast-implied probability); target = payout minus ask; baseline = 0 and
  the same rule in non-weather bucket events (crypto price buckets); metric = mean net by price band, clustered by
  city-day; kill = net below 1c at -6h, or an effect confined to one city.
- Overlap: C1 (descriptive), T5-DEV (resolution forecasting with price-only features, no category model).
- Scores: N 3, EV 3, C 1.

**CH28. Scheduled-source markets: for markets that resolve on a public statistic published on a fixed clock (box office,
Spotify/Billboard charts, app-store ranks, official weather observations, game stats), the market reprices with a lag after
the source updates, and the stale ask is executable.**
- Mechanism: the update time is known (charts at a fixed hour, box office each morning); the number is public the second
  it posts; the market is thin and nobody is watching at that minute. Latency arbitrage against inattention rather than
  against a faster feed.
- Money route: taker at the stale ask within minutes of the post, hold to resolution (often the same day). Envelope: 10-40c
  moves on a known number; fee 1c; half-spread 2c; the question is whether any size is left at the stale ask, and how
  often the market's own price already reflects a leak (chart previews).
- Data: `A` for the lag measurement (`h2_main` 10-minute prices around known posting times for chart/stat markets
  identified by frozen text rules); `P` for the trigger (the source's public page or API, polled at the posting time)
  and the book (CLOB poll).
- Minimal test (phase 1): population = chart/statistic markets with trades; feature = minutes since the scheduled post;
  target = time for the price to move 80% of the way to its 6h-later value; metric = lag distribution by source and
  liquidity; kill = median lag under 10 minutes. Phase 2: executable ask at post + 2 min against resolution.
- Overlap: none (EXTERNAL_NEWS.md used GDELT as a gate, never as a source of resolution facts).
- Scores: N 3, EV 3, C 2 (phase 1) / 4 (phase 2).

**CH29. Closing-line value: Polymarket's pre-game price lags the sportsbook closing line (de-vigged), and the side the
closing line favours wins more often than Polymarket's price implies.**
- Mechanism: the closing line is the most efficient public forecast in sports; it incorporates sharp money that may not
  trade on Polymarket (jurisdiction, size). If Polymarket's crowd lags it, the gap is a one-leg carry of hours.
- Money route: taker at game start on the closing-line side, hold to the end. Envelope: 2-3 point gaps; fee 1c;
  half-spread 1c; net about 1c per share over hours: thin, but the sample is thousands of games.
- Data: `N` historically (Pinnacle's API is closed; free odds archives are partial); `P` prospectively (free odds API
  tiers give a few hundred requests a month: enough for one league's closing lines).
- Minimal test: population = games with both a Polymarket price and a de-vigged closing line 5 minutes before start;
  feature = line minus price; target = payout minus ask; baseline = 0; metric = slope and mean net, clustered by game
  day; kill = net below 0.5c or a gap that is itself unstable across books.
- Overlap: cross-venue family (Kalshi only). Known to practitioners; low novelty, decent prior.
- Scores: N 1, EV 2, C 3. Sports scope undecided.

**CH30. Digital-option fair value in the 15-minute crypto markets: the Up/Down price lags the Black-Scholes digital value
computed from the public spot path and realised volatility, especially in the last 5 minutes.**
- Mechanism: the contract is a cash-or-nothing digital on the Chainlink TWAP vs the price-to-beat set at window open;
  its fair value is a known function of spot minus strike, time left and short-horizon vol, all public. Retail prices it by
  feel. Bots exist (press on "top 15m traders") and about 25% of Polymarket volume is wash-like, heaviest in crypto, so
  the printed volume overstates the real depth.
- Money route: taker at the ask on the side the digital value favours, hold to settlement (minutes). Envelope: the fee is
  the killer: crypto 0.07 at p = 0.5 is 1.75c per leg; half-spread 0.5c; the model edge must exceed 2.3c, which it does
  only when spot has moved well past the strike late in the window (p_fair 0.75 vs market 0.65), i.e. when the market
  is slow.
- Data: `N` in AREPO (2h snapshots cannot see 15-minute markets; the panel's one-day lag excludes them); `P` (CLOB
  WebSocket for the Up/Down tokens and Binance 1-minute klines, both keyless).
- Minimal test: population = every window for BTC/ETH over two weeks; feature = digital fair value minus mid at
  minute 10 and 13; target = settlement minus ask; baseline = 0; metric = net per share by |edge| bucket, clustered by
  hour (windows overlap in information); kill = net below 0 at any |edge| after the 0.07 fee.
- Overlap: none in AREPO; well known in spirit.
- Scores: N 1, EV 2, C 3.

**CH31. FOMC bias: Polymarket's Fed-decision prices differ from the CME FedWatch probabilities by a sign predictable from
the futures term premium, and FedWatch is the better predictor of the decision.**
- Mechanism: FedWatch is derived from hedging instruments with a term premium; Polymarket is an opinion market. The two
  should disagree in a systematic direction. Eight decisions a year: this is a prior, not a test with power.
- Money route: hold to the FOMC date. Data: `P` (FedWatch daily values are public but their history is not freely
  archived; start collecting). Kill = fewer than 16 decisions (two years) before any test; recorded as a long-horizon
  collection item only.
- Scores: N 2, EV 1, C 2. Not testable soon.

**CH32. "Mentions" markets: the speaker's historical word-frequency base rate (public transcripts) beats the price for
longshot words, which are bought as lottery tickets.**
- Mechanism: "Will X say Y during Z" markets are frequent and resolve on a transcript; past transcripts are public and
  give a base rate per word; retail buys the funny word at 0.10 when the base rate is 0.02.
- Money route: sell YES (NO at 0.90) and hold through the event (hours). Envelope: 8c gross on 0.90; fee 0.36c;
  half-spread 1.5c; net about 6c per event-word, dozens of words per event.
- Data: `A` partially (`h2_main` has a `mentions` fee category with outcomes: the unconditional test); `P` for the
  transcript model (whitehouse.gov, C-SPAN and rev.com transcripts; a frozen tokeniser).
- Minimal test: population = mentions markets with trades at origin = `end_at` - 6h; feature = price band (phase 1) and
  base-rate minus price (phase 2); target = payout minus NO ask; baseline = PX3-style longshot excess in other categories;
  metric = mean net by band, clustered by event (all words in one speech resolve together: one cluster); kill = net
  below 1c, or fewer than 30 events.
- Overlap: PX3 (longshot resolution excess pooled across categories, null). The category and the base-rate model are new.
- Scores: N 3, EV 2, C 1 (phase 1).

### F. Cost-side (makes the other routes cheaper)

**CH33. Pre-event spread cycle: spreads and depth follow a predictable cycle around scheduled resolution events (game start,
data release, deadline), so the same taker order costs 1-2c less when timed 30-90 minutes before the widening.**
- Mechanism: makers widen before known information events and after; the cycle is visible in every scheduled market and
  is cheap to exploit for any strategy that has discretion on timing.
- Money route: cost reduction for CH23, CH27, CH28, CH29. Envelope: 1-2c per share on 4.5c median: a quarter to a half
  of the round-trip cost.
- Data: `A` (book sweeps every 2h and pmxt hourly books; `end_at` and sports start times for the anchor).
- Minimal test: population = scheduled-event markets; feature = hours to the event; target = spread and 5c depth;
  metric = cycle shape with event-clustered CIs; kill = no cycle (a flat spread profile within 1c).
- Overlap: LQ1-LQ4 (book changes as volatility features, not as a cost model).
- Scores: N 2, EV 2, C 1.

**CH34. Fee-band persistence: mispricings between linked markets persist inside a band whose width is the category taker
fee, so the structural opportunities of CH09-CH13 are largest and longest-lived in crypto (7%) and smallest in
geopolitics (0%); inside the band only makers can act.**
- Mechanism: takers cannot close a gap smaller than the fees on the legs; makers pay no fee. Fees changed by category
  in 2026 (fee step 07-10; sports schedules at 0.03): a natural experiment on the band width.
- Money route: none directly; it tells the structural hypotheses where to look and that the route is maker.
- Data: `A` (snapshots with the sidecar fee schedule; pmxt around the 2026-07-10 fee step).
- Minimal test: population = neg-risk events and ladders; feature = category fee rate and the fee step date; target =
  persistence (half-life) and size of executable deviations; metric = half-life by fee rate, before vs after the step,
  clustered by event; kill = no monotone relation between fee rate and deviation persistence.
- Overlap: E005/XM1 (mids only, no fees).
- Scores: N 3, EV 2 (as an organising result), C 1.

---

## 3. Ranked top 10 and the families to test first

Ranking weighs expected value if true, prior plausibility, independence from the saturated families, and whether the
test can run on data AREPO already holds. "Runnable now" means existing stores, no new collector.

| Rank | ID | One line | Runnable now | Family |
|---|---|---|---|---|
| 1 | CH01 | Decided-but-unresolved carry vs expected wait and oracle tail | yes (`h2_main`/`h3_power`, snapshots) | R |
| 2 | CH09 | Asymmetric neg-risk deviations; passive full-set accumulation inside the fee band | yes (snapshots, sidecar) | S |
| 3 | CH17 | Longshot ask-selling held to resolution (harvest the ask, not the mid) | yes (pmxt + `h2_main` trades/outcomes) | M |
| 4 | CH05 | Near-rung NO carry on deadline ladders (IF-H2's -5c follow-up) | yes (IF-H2 panel) | R |
| 5 | CH10 | Placeholder members: sibling-implied fair vs resting quotes | yes (snapshots) | S |
| 6 | CH16 | Reward-per-adverse-selection market selection for makers | partly (sidecar since 11 Oct; 2 weeks needed) | M |
| 7 | CH22 | Genesis window: first-24h overpricing of sensational YES | yes (raw backfill prices from listing) | B |
| 8 | CH27 | Weather favourites underpriced at 1d (C1 subgroup follow-up) | yes (`h2_main` weather) | I |
| 9 | CH03 + CH02 | UMA dispute base rate; proposal-window carry | no (Polygon log scan, then pmxt join) | R |
| 10 | CH13 | Cross-event implied-CDF consistency (strikes, dates, nested outcomes) | yes after a grouper extension (IF-H2 metadata) | S |

**Families, as they would be registered.**
- **R. Resolution-carry family (CH01, CH05, CH02, CH03, CH04).** One shared machinery: executable ask, wait distribution,
  wrong-side tail, annualised net, event x resolution-week clustering. One shared risk: oracle behaviour can change.
  Start with CH01 and CH05 on existing data; build the Polygon log scanner once for CH02/CH03/CH04.
- **S. Structural-consistency family (CH09, CH10, CH12, CH13, CH11, CH34).** One shared machinery: event membership from
  snapshots, touch-level inequalities, fee bands, persistence half-lives, paper maker fills from trade samples. Start with
  CH09 and CH10 (no new code beyond the snapshot join); CH13 needs the grouper.
- **M. Passive-side economics family (CH16, CH17, CH18, CH19, CH20).** One shared machinery: paper quotes against pmxt
  or sweep books, queue-rule fills from prints, reward share from the public formula, hold-to-resolution P&L. CH17 is
  the sharpest single test; CH16 needs the sidecar window to grow.
- **B. Listing and attention family (CH22, CH23, CH24).** CH22 is cheap and uses an untouched slice of existing data.
- **I. Public-source family (CH27, CH28, CH32, CH29, CH30).** CH27 is runnable now; the others need small collectors.

**What is honest to say about all ten.** Every envelope above depends on numbers nobody has measured on this venue
(waits, tail rates, fill completion, persistence). The point of the first tests is to measure those, not to find edge.
A result that "looks profitable" on `h2_main` is a screen on worn data and goes through the same ladder as everything
else: placebo, replication on `h3_power` with frozen definitions, then prospective registration on sealed data, then an
economic check at recorded asks. Several ideas (CH02, CH03, CH04, CH28) are latency plays against inattention; they can
be true and still be capacity-limited to a few hundred dollars per setup, which is worth knowing before anyone calls it
an edge.

---

## 4. Ideas I considered and rejected, and why

- **Maker-rebate loops (trade against yourself to collect the rebate share).** Negative by construction: the rebate is a
  fraction (15-25%) of the taker fee you paid; it is also wash trading.
- **Holding-rewards full-set yield (split $1 into YES+NO on the 18 eligible events, earn 3.25% on the mid value of both).**
  Real but not research: a published, treasury-funded, capped rate with no mispricing to find. Noted in CH21 only for
  the mark-spike side effect.
- **Taker arbitrage of "sum of asks < 1".** Killed by arithmetic: fees on N legs sum to about `rate * (1 - sum p^2)`,
  up to 4-7c, larger than almost every gap; survives only in zero-fee geopolitics and as a maker route (CH09).
- **Re-running momentum, reversal, flow, wallet freshness and Kalshi lead-lag with more data or new models.** The brief
  excludes them, SB2 J1-J8 already covers the conditional versions, and the cost study showed the gross is an order of
  magnitude below round-trip costs. Only the maker and hold-to-resolution angles above touch them.
- **Cross-venue arbitrage with capital on both venues.** Not a public-data edge: the study found gaps that look like
  basis and stale prices; it needs KYC'd capital on Kalshi and simultaneous execution; the gap adds nothing to the
  next move.
- **Insider or informed-flow detection as a money route.** It is the UNUSUAL_FLOW programme's question; episodes are rare,
  unlabelled and legally delicate; the battery found no market-level trace (IX1, IX2, IX5, WA2, WA3). Nothing new to add.
- **Predicting UMA whale votes.** Unobservable before the vote; the base-rate version is CH03.
- **Comment-feed sentiment and social-media attention.** Overlaps CH24 with worse data; comment counts are a gate in
  `ifx_quiet`, not a signal.
- **Wash-trade detection as alpha.** The Columbia estimate (about 25% of volume artificial, 45% in sports) is a reason
  to distrust volume features, not a trading signal; worth a methods note for the flow family, not a hypothesis here.
- **Exploiting the mid-marking of holding rewards, spoofing before a proposal, or any manipulation-based idea.** Not
  public-data research, and not legitimate.
- **Market-creation games (seeding, creator liquidity).** Polymarket creates every market; there is no user listing
  mechanism to exploit.
- **Parlay mispricing.** Documented on Kalshi (Moshrefi) but Polymarket has no parlay product.
- **API quirk exploitation (cursor blocks, pagination caps).** Operational facts, not economics.
- **Time-of-day and weekend price effects.** TI1/TI2/TI5 null; only the maker-competition version (CH18) is kept.
- **Favourite-longshot bias as a mid-level carry.** PX3/PX4 null and C1 shows prices near calibration at 1d; the surviving
  angle is the ask side (CH17) and the specific populations where the literature finds it (CH22, CH23, CH27, CH32).

---

## 5. Sources consulted (external; AREPO documents are cited inline by name)

- Polymarket docs: liquidity rewards formula and sampling
  (https://docs.polymarket.com/developers/market-makers/liquidity-rewards); UMA resolution, 2h challenge period, bonds,
  dispute path (https://docs.polymarket.com/developers/resolution/UMA); negative risk and augmented events
  (https://docs.polymarket.com/developers/neg-risk/overview); holding rewards, 3.25%, hourly sampling, 18 events
  (https://help.polymarket.com/en/articles/13364459-holding-rewards); fees (https://docs.polymarket.com/trading/fees,
  as read in EXECUTION_COSTS.md).
- Saguillo, Ghafouri, Kiffer, Suarez-Tangil, "Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets",
  arXiv:2508.03474 (about $40M realised rebalancing and combinatorial arbitrage, Apr 2024 to Apr 2025).
- Cardozo and Rivero-Wildemauwe, "The Favorite-Longshot Bias in Prediction Markets: Evidence from Polymarket",
  arXiv:2609.12878 (purchases below 10c lose 19.3c per dollar; crypto and politics, not sports).
- Moshrefi, "Prices, Probabilities, and Parlays: Systematic Bias in Sports Prediction Markets", arXiv:2607.14430
  (Kalshi; step-like calibration in the final ten minutes; parlays overpriced).
- Page and Clemen (2013), Economic Journal, time-to-expiry bias from discounting and abstention.
- IMDEA working paper on Polymarket initial liquidity (empty books at listing; sports narrow fastest).
- Sirolly, Ma, Kanoria, Sethi (Columbia, SSRN 2025), network-based wash-trade detection (about 25% of volume).
- Press on UMA disputes (The Block, The Defiant, Cointelegraph via TradingView, KuCoin news) and on bot profitability
  (Bloomberg analysis as syndicated); treated as background, not evidence.
