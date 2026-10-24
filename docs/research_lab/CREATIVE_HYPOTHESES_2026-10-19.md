# Creative hypotheses, round 5: where money could come from on Polymarket (2026-10-19)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-17 21:05 UTC+1,
2026-10-17T20:05Z; the file carries the round's planned date). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md`
(CH01-CH34), round 2 `CREATIVE_HYPOTHESES_2026-10-16.md` (CH35-CH59), round 3 `CREATIVE_HYPOTHESES_2026-10-17.md`
(CH60-CH78), round 4 `CREATIVE_HYPOTHESES_2026-10-18.md` (CH79-CH98); this file starts at **CH99** and repeats none of
them. Where an idea builds on an earlier one, the parent is named and the new mechanism or data source is stated. Every
number quoted from an AREPO document is a development or screen result, not evidence. One file; no code, no queue specs,
no other commits.

## 0. How to read this file

**What changed since round 4 (17 Oct results, drafts and drops).**
- **CB9 (CH79, CH84+CH83a, CH92, CH80 route 1) and CB10 (CH89, CH93) are drafted and challenged.** CB9 §0.4 and CB10
  §0.4 dropped, with concrete reasons, CH82 (the public Combos catalogue lists *leg markets*, not combos: no combo
  price or volume is public), CH87 (the "credible reporting" clause is a fallback inside official-source rules in 53 of
  54 probed texts, so the two classes are not separable), CH90 (about 30 releases, one cluster each), CH91 (100-300
  pairs, slope MDE useless), CH81 (3 joint events seen), CH85, CH86, CH88, CH94-CH98 (need the audited `side` field or
  weeks of resolutions). None of them returns here in its old form.
- **Three more structural facts from the batch probes bind every idea here.** (i) Pyth price paths are *not* keyless
  (CB9 probe 6); public hourly bars are, minute bars only live or 30 days back. (ii) The Data API `/trades` is not
  windowed by time and reaches at most the newest 20,000 prints per market (CB10 probe 10). (iii) The on-chain CLOB V2
  `OrderFilled` carries an explicit `side` (CB9 probe 2), which CB9-S audits; every flow idea here is written
  **side-free** (price-impact sign or print-based moves only) so it does not wait on S0.
- **Nulls and stop rules since round 4.** CB1-D: under-priced neg-risk sets +0.78 pp, p 0.016, fails the 1 pp floor
  (nothing advanced). CB5-L: **0 CDF families** (51 of 57 candidate bucket events hold an "Other"/"No X" placeholder
  member; CH59 expected to close as too rare). CB4-N: 1.29 eligible events per hour against an assumed 15, stop rule
  fired, N1/N2 not testable. CB6-T's h8_tail frame came in at 362 markets, topped up to about 1,140-1,530 units.
  CB7 smoke v2 passed; h8_text has 1,026 eligible origins (design assumed about 5,000), h8_geo 1,917. The lesson is
  the same each time: **count the population before the hypothesis** (every idea below carries a probe count).
- **Cumulative test count** was 1,146 at the CB10 round-1 review (2026-10-17T15:01Z). Every test here joins that
  denominator.
- **Venue and source facts verified for this round (keyless, 2026-10-17 19:55-20:05Z, 30 requests, counts and field
  names only; no price, outcome, volume or wallet of any market was printed or stored; the requests are listed in §5).**
  1. **A hidden pool of open markets.** Gamma returns at least **2,100 markets with `active=false` and `closed=false`**
     (pages at offset 500 and 2,000 are full), **all `acceptingOrders`**, all attached to events. Among those with
     volume >= $1,000 the first page's end dates are **98 in 2028 and 2 in 2027**: long-dated markets that are open on
     the CLOB but not surfaced. No AREPO panel has looked at this population (the capture query takes `closed=false`;
     whether it also takes `active=false` is a census question, §CH103).
  2. **UMA statuses on Gamma show no disputes.** In 300 closed markets across three 3-day windows (September, June,
     March 2026) the `umaResolutionStatuses` field holds only `proposed` and `resolved`; no market has more than two
     entries. Either disputes are under 1% or the field does not record them; the on-chain `DisputePrice` log is the
     only ground truth (§CH104).
  3. **A keyless US equity option chain exists.** CBOE's delayed-quotes JSON returned **4,302 NVDA options across 25
     expiries** with `bid`, `ask`, `bid_size`, `ask_size`, `iv`, `delta`, `gamma`, `last_trade_price` (15-minute delay,
     no key). This is the equity analogue of the Deribit history CB10-D uses, and it is live-only (§CH99).
  4. **Extended-hours equity bars are keyless.** Yahoo's chart endpoint returned 360 hourly bars for one month with
     `pre`/`regular`/`post` trading periods, and 917 one-minute bars for the current day including pre- and
     after-hours (§CH100).
  5. **Non-equity Pyth dailies have their own session.** The closed "Gold up or down" rule text names Pyth, COMEX and
     a 1-minute candle, states a 5:00 PM ET close and ends at 21:00Z; it does not say "regular trading" or "settlement"
     (§CH101).
  6. **15-minute crypto markets are created inside their own window.** A closed `btc-updown-15m-<ts>` market whose
     question names a 15-minute ET window has `createdAt` 09:36Z, `startDate` 09:38Z and `endDate` 09:45Z: trading
     runs for about seven minutes, after the reference time, and the CLOB `prices-history` serves its minute series
     only with explicit `startTs`/`endTs` (the `interval=max` form returned 0 rows; a bounded request on another
     market returned 1,438 rows) (§CH102).
  7. **Statistic-resolved classes are plentiful.** Closed events on Gamma's public search (capped at 50 events per
     query): "Rotten Tomatoes" 50+ events / 358 markets (up to 15 per event), "App Store" 50+ / 881 (up to 26),
     "measles" 35 / 160, "earthquake" 50+ / 198, "Supreme Court" 50+ / 132, "say during" (mention baskets) 50+ / 970
     with up to **44 members per event**, "bankruptcy" 29 / 62, "acquisition announced" 4 / 4 (§CH106-CH108, CH112).
  8. **Keyless external feeds confirmed:** EDGAR full-text search (44 "chapter 11" 8-Ks in September 2026); PredictIt's
     market-data feed (207 markets, 635 contracts, `timeStamp`); Kalshi's nested events (on one page of 200 open
     events, **55 Economics events with >= 5 markets**, 13 Science/Technology, 11 Entertainment, 11 Elections). ESPN's
     scoreboard JSON returned **403** to the probe user agent (not verified keyless).
  9. **Logical connectives are thin:** of 100 closed questions with volume >= $5k (20-23 Sep), 6 contain "or/either/any
     of" and 10 "and/both/all of", many spurious (§CH117).

**The reading that steers this round: what survived and what died.**
- What survived every screen: **cross-venue information** (Kalshi's 10-20 minute lead, r about 0.24-0.26, the one
  replicated predictor), **structural and mechanical rules** (neg-risk gaps exist, even if small; the tail and
  deadline structure of ladders), and **volatility context** (the learned surprise score is "volatile week, quiet day,
  young market"). What died: **wallet identity** (freshness null in three analyses; the flow, wallet and size
  families add nothing to the surprise detector) and **small flow effects** (E007 +0.36c, HB1 +0.3 to +0.6c per SD,
  real and replicated, eaten by 1.5-1.9c of cost even at >= $100k liquidity; 95 economic setups, none positive;
  passive entry pays 1-7c of adverse selection).
- So this round hunts in three places. **(a) Public anchors with a professional counterparty** where fair value is a
  public function of a public path or a public option chain, and the risk is basis or latency, not information
  (family A, CH108-CH109). **(b) Footprints that are not wallets**: the numeric shape of a print, a broadcast
  threshold, a basket's count distribution (family F). **(c) Populations no panel has seen**: hidden long-dated books,
  markets created inside their own window, statistic-resolved series with keyless counts (families B, E).
- Round 4's measurement theme continues in two places only: stripping the reward subsidy from book imbalance (CH116)
  and the capital-lock explanation of *where* public information is slow (CH115), which is a hunting rule for every
  anchor route rather than a route itself.

**Data labels.** `A` = in AREPO's stores now: complete-universe 2h captures (touch, Gamma mid, `oneHourPriceChange`,
`last_trade_price`, `volume24hr`, `liquidity`, neg-risk ids, `closed`, `endDate`) with the sidecar since 11 Oct 12:00Z
(`accepting_orders`, `competitive`, `clob_rewards`, `rewards_max_spread`, `rewards_min_size`, `fee_schedule`,
`uma_resolution_statuses`, `series_slugs`, `parent_event_ids`, `order_price_min_tick_size`); book sweeps twice per pass
(touch, 1c and 5c depth); trade samples (hashed wallets, raw 3 days); the live large-trade monitor (prints >= $1k every
5 min, hashed wallets, `tx16`); the CB extract tables; the audited cross-venue pair history (316 clean pairs, 10-minute);
the IF-H2 ladder metadata; pmxt v2 hourly L2 event files 2026-04-13 to 08-10 (range reads by condition id); the Binance
1-minute public archive (CB8-B). `P` = collectable read-only from public keyless sources within a week (Gamma
`description`, Data API `/trades` and `/oi`, CLOB `prices-history` with explicit bounds and `/book`, Polygon and
Ethereum public JSON-RPC logs, CBOE delayed option chains, Yahoo chart bars, USGS FDSN event catalogue, CDC weekly
tables, EDGAR full-text search, Federal Register public-inspection API, PredictIt and Kalshi market feeds). `N` = no
known keyless source. **Sealed and not usable by anything here:** everything round 4 lists (`h4_seal`, `h5_*`, `h6_weather`,
`h7_cb4_*`, `h8_*`, the `h9_flow` HOLDOUT, CB8-B's HOLDOUT weeks, CB8-H's windows, CB1-D's replication captures, the
E009/E010 poller to 2026-11-03, E011 labels to 2026-11-11, the J4-R window) plus CB9's K/D HOLDOUT events, CB9-P's Pyth
equity Up/Down frame (pmxt sessions 2026-04-13 to 08-10) and its Stage-2 sessions, CB9-S's receipt strata, CB10-B's
`h10_brk` HOLDOUT, CB10-D's ladder frame and Deribit windows. `h2_main` is worn and `h3_power` retired. Every historical
test below names a **fresh** fetch (`h10_*`), disjoint by market id *and* event / neg-risk / series key from every prior
sample and seal copy, with rows before `T_hist_end` 2026-10-01 (CB8's convention) or collected prospectively; none is
bound to the 2026-10-22 `T_seal` lane.

**Hygiene that binds every idea.** Trade before `t`; scheduled anchors, never `closedTime`; outcomes that are public
functions of public paths are computed from the public path, never read from Gamma's outcome fields (CB9-P's guard);
event x resolution-week clustering for carries, session-day clustering for dailies; tightness at both ends of any
mid-based target (J4-R) and print-based targets where possible; rule text as of first sighting (`textorig`) or the
clarification-marker exclusion; hashed wallets only, and no idea here needs a wallet at all; the cumulative test count
(M3). Category stays a parameter (sports scope is the user's call; nothing here is sports-only, and the one sports-only
idea is in §4).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = an afternoon on existing data or a small keyless
fetch, 5 = new collector plus weeks). My judgement, not measurements. Cost conventions as rounds 1-4: taker fee
`rate*p*(1-p)` per leg (crypto 0.07; sports 0.03-0.05; politics/finance/tech 0.04; economics/culture/weather 0.05;
geopolitics 0; makers 0, rebate 15-25% of the fee-equivalent of own fills); median spreads by price band
4.1 / 3.0 / 2.2 / 3.0 / 2.5c; liquid (>= $100k) round trip 1.8c; median round trip 4.5c; one-leg hold-to-resolution pays
the half-spread and the fee once; Pyth dailies have `rewardsMaxSpread` 4.5c and fee 0.04.

---

## 1. Map: what the survivors say about where money is

| Family | What the evidence suggests | Money route |
|---|---|---|
| A. TradFi dailies with public anchors | Pyth dailies (equities, metals, energy, indices) are public functions of public paths; option chains and extended-hours bars are keyless and nobody in the crowd prices them | hold-to-settlement taker when the anchor disagrees by more than fee plus spread; model-anchored maker |
| B. Populations no panel has seen | 2,100+ hidden long-dated books; 15-minute markets created inside their window | riskless ladder pairs on hidden rungs; first-minute fade of behavioural tilts |
| C. Resolution plumbing and deadlines | disputes are rare but their votes are public on another chain; "by date" deadlines are ET | hold-to-resolution on the visible tally; cheap deadline-hour descriptive |
| D. Public calendars and filings | hazard is concentrated on scheduled days; filings precede coverage | buy before scheduled days; taker at stale asks after a filing |
| E. Statistic-resolved markets | final values are known functions of public running counts or public aggregator inputs | hold-to-resolution on the model side |
| F. Footprints that are not wallets | numeric shape, broadcast thresholds and basket counts classify flow without identity | maker filters; basket selling; fade copy flow |
| G. Cross-venue beyond identical pairs | Kalshi ladders imply CDFs; PredictIt is a third crowd with a known fee bias; capital lock-up slows long-dated markets | maker skew toward the implied price; where to hunt |
| H. Measurement and text | reward bots mask imbalance; logical form has a sign prediction | methods filters; text-class carries |

---

## 2. Hypotheses

### A. TradFi dailies with public anchors (parents CH83, CH84, CH89; CB9-P and CB10-D are the sealed neighbours)

**CH99. Option-chain digital anchor for Pyth equity "close above $X" markets: the risk-neutral probability read from a
keyless delayed option chain (direct call-spread digitals for same-day expiries on SPY, QQQ and the indices; the
strike-specific implied vol for single stocks) predicts the resolution of the daily strike markets beyond their
Polymarket price, and buying the anchor's side when it disagrees by more than fee plus spread pays when held to the
20:00Z settlement.**
- Mechanism: the strike markets (11 in one event on 2026-06-22, 46 on 08-03; CB9 probe 4) are listed the previous day
  at 12:00Z and settle on the Pyth close of the final regular-session minute. Their fair value at any intraday time is
  a digital option with hours to expiry. The listed option market prices exactly that digital, with professional
  makers and tight quotes; the Polymarket crowd prices it with a lognormal in their heads or not at all. The chain is
  keyless (fact 3) but 15 minutes delayed, which only makes the anchor conservative. Who pays: retail buyers of "close
  above" lottery tickets after a morning move and reward bots centred on the book mid. Why it persists: the join is a
  chore and the markets are six months old.
- Test (`P`, prospective; the chain has no keyless history). Per session, at 15:00Z, 17:00Z and 19:00Z: (a) the Gamma
  frame of open Pyth strike markets (text flags as CB9: Pyth, final minute, exactly-equal clause); (b) the CBOE chain
  for each underlying (one request per name; fields `bid`, `ask`, `iv`, `delta`) and the delayed spot it carries; (c)
  the CLOB book of each strike market. Anchor rule frozen before the first session: for names with an expiry on the
  session date, `q = (C(K-h) - C(K+h)) / 2h` from mid quotes with `h` = one listed strike step, clipped to [0, 1]; for
  others, `q = Phi(d2)` with the iv interpolated at `K` from the nearest expiry and scaled to the remaining
  regular-session hours; dividends by the ex-date calendar; the equal-close rule as a 50-50 cell. Unit = market x
  checkpoint; outcome = sign of the Pyth-equivalent close vs `K` from the public daily bar (fallback audit against the
  Gamma field under guard, as CB9-P). Primary: slope of `(Y - p_pm)` on `(q - p_pm)` with `p_pm` the book mid at the
  checkpoint and the J4-R tightness check (both touches present, spread <= 4.5c); clusters = session day (also by
  underlying). Economic: buy the anchor side at the recorded ask when `|q - ask| >= 4c` after the fee, hold to
  settlement; net per share, session-clustered. 30 sessions x about 20-50 markets x 3 checkpoints = 1,800-4,500 units,
  30 clusters; with SD(Y - p) about 0.45 and SD(q - p) about 0.10 the slope MDE is about 0.25 (CB10-D's floor 0.30).
- Data: `P` (CBOE delayed chain, Yahoo daily bars, Gamma frame, CLOB books). Disk under 200 MB for 60 sessions.
- Economics: fee `0.04*p*(1-p)` <= 1c; half-spread 1-2c inside the 4.5c reward band; break-even gap about 3c; the
  anchor's own error (delay, option bid-ask) is 1-3 pp for liquid names, 5+ pp for far strikes (exclude `q` < 0.05 or
  > 0.95 and option spreads wider than 10% of the mid).
- Kill: slope CI includes 0 or point < 0.30 after 30 sessions; or the economic net <= 0 at the 4c filter; or fewer than
  10 units per session on average.
- Leakage/confound: the anchor is always computed from a chain timestamped before the book read; Pyth-vs-exchange close
  basis (CB9 probe 5's fallbacks) and the exactly-equal clause; earnings sessions (the chain's iv jumps; report with and
  without); the delayed chain can lag a sharp move by 15 minutes (this biases *against* the anchor).
- Novelty: CH89 (Deribit for crypto ladders, CB10-D) and CB9-P (lognormal from hourly bars on Up/Down dailies) are the
  parents; new: the strike markets themselves (in no batch), a verified keyless equity chain, and direct same-day
  digitals for the ETF and index names. N 4, EV 4, C 2-3.

**CH100. Extended-hours anchor for next-day Up/Down dailies: between the 20:00Z close and the 13:30Z open the Pyth
Up/Down market for the next session trades on Polymarket while the stock's after-hours and pre-market prints (keyless,
minute-level live, hourly in history) already carry most of the overnight information; the Polymarket overnight price
sits nearer 0.5 than the extended-hours-implied probability, and buying the implied side pays when held to
settlement.**
- Mechanism: the Up/Down market for day D (close_D vs close_D-1) is listed on D-1 at 12:00Z (CB9 probe 5); after
  20:00Z the reference is fixed and the only new information until the open is the extended-hours path (earnings,
  guidance, macro prints, index futures). The crowd that trades Polymarket at 02:00Z is thin and the reward bots
  centre on the mid; the public after-hours print is not something a reward bot reads. Fair value at an overnight time
  is `Phi(ln(S_ext / close_D-1) / (sigma * sqrt(tau)))` with `sigma` the trailing 20-day realised vol and `tau` the
  remaining session fraction plus an overnight weight (frozen at 0.25 of a day; sensitivity 0.15-0.35). On an earnings
  night with a 5% after-hours move the fair is 0.85-0.95 while the market may show 0.6.
- Test. **Stage 1 (`P`, historical):** fresh frame `h10_ext` = Pyth equity Up/Down markets with sessions in
  [2026-08-11, 2026-10-01) (after pmxt ends, so outside CB9-P's frame; verified against CB9's exclusion keys at census),
  about 35 sessions x 17-20 names = 600-700 markets; CLOB `prices-history` with explicit bounds at 1-minute fidelity
  (fact 6) read at 00:00Z, 08:00Z and 13:00Z; Yahoo hourly bars with `includePrePost` (two years keyless) for `S_ext`;
  outcome from the public daily bars. Primary: slope of `(Y - p)` on `(q_ext - p)` with the J4-R increment-shuffle
  placebo (the overnight series is mid-like and may be a stale quote: tightness unknown historically, so Stage 1 is
  labelled optimistic); clusters = session day. **Stage 2 (prospective):** the same three checkpoints with CLOB books
  and prints; the economic rule buys the implied side at the recorded ask when `|q_ext - ask| >= 5c` after fee, holds
  to 20:00Z. MDE at 650 units, 35 clusters: slope about 0.3.
- Data: `P` (CLOB history and books, Yahoo bars, Gamma frame). Under 100 MB.
- Economics: fee <= 1c, overnight half-spread 1-2c (wider than the day; the sweep will say), break-even gap 3-4c; the
  opportunity is concentrated on earnings and macro nights (about 10-20% of market-nights), which is where the
  anchor's own error is also largest (the after-hours move can reverse by the open).
- Kill: Stage-1 slope CI includes 0; or `|q_ext - p| >= 5c` in fewer than 10% of unit-checkpoints; or Stage-2 net <= 0.
- Leakage/confound: `S_ext` must be the last extended-hours bar strictly before the checkpoint; the overnight Polymarket
  series may be an untradeable mid (the Stage-2 book settles it); the 50-50 tie clause; halted names.
- Novelty: CH83a (open-gap under-reaction, folded into CB9-P's 10:32 ET checkpoint) and CH84 are the parents; new: the
  overnight window, the extended-hours source and a historical window CB9-P does not cover. N 3, EV 3, C 2.

**CH101. Non-equity Pyth dailies (gold, silver, WTI, natural gas, indices) with continuous futures anchors: these
markets settle on a 5:00 PM ET Pyth close (fact 5) but their underlyings trade nearly 23 hours a day on public futures
(keyless minute bars live, hourly in history), so the Asian- and European-session path sets the fair value while the
Polymarket crowd is asleep; the same slope and hold-to-settlement tests as CH100, on a population no batch holds.**
- Mechanism: a gold Up/Down for day D compares the Pyth XAU/USD close at 21:00Z with the prior day's; by 08:00Z the
  futures (`GC=F`) have moved on the Asian session and the market, listed at 12:00Z the day before, shows a price set
  by a few bots. The futures-spot basis (carry) is slowly varying and cancels in an Up/Down comparison made
  consistently on futures; for the strike variants it does not, and the prior-day basis is used. CB9 probe 4 saw
  >= 26 Pyth markets at 21:00Z on one July day, so the daily population is about 5-10 markets across metals, energy
  and indices.
- Test (`P`): as CH100 with `h10_cmdty` (sessions 2026-04-02 launch to 10-01; pmxt range reads are possible for
  04-13 to 08-10 because CB9-P pulled equity books only; ingress about 0.5 GB) and Yahoo hourly futures bars; the
  rule-text gate first: the session definition must parse to a public timestamp for >= 80% of markets (fact 5 shows
  "5:00 pm" and COMEX in the gold text; silver, WTI and gas may differ), else not testable. Checkpoints 00:00Z, 08:00Z,
  13:00Z; clusters = session day; about 150 sessions x 5-10 markets = 750-1,500 units.
- Data: `P`. Under 1 GB with pmxt.
- Economics: as CH100; futures-spot basis error about 0.1-0.3% of price, which matters only for strikes within 0.5% of
  the spot.
- Kill: rule-text gate fails; or slope CI includes 0 with >= 600 units; or the CME-settled twin ("Gold (GC) Up or Down",
  round 4 §4) and the Pyth version disagree on more than 5% of days (then the session definition is wrong and the test
  is void).
- Leakage/confound: holiday clauses and the 50-50 no-trade rule (round 4 §4); the COMEX mention may define the session
  differently from the 5:00 PM text; index markets may settle on the cash index rather than the futures.
- Novelty: round 4 rejected the CME-vs-Pyth gold *twin pair*; CB9-P is equities only; new: the non-equity population
  and the 23-hour public anchor. N 3, EV 3, C 2-3.

### B. Populations no panel has seen

**CH102. Late-created 15-minute windows and streak tilts: the 15-minute crypto Up/Down markets are created about six
minutes into their own window (fact 6), so the first quotes face a reference price that is already minutes old and a
public path; conditional on the path-implied fair value, the first-minute price tilts toward the side that won the
previous two or three windows (hot-hand), and a maker who fades the tilt at the first minute earns the tilt plus the
rebate with no information on the other side.**
- Mechanism: 96 windows a day per asset (BTC, ETH, SOL, XRP) with the same retail crowd rolling from window to window
  (CH50's roll flow at a 15-minute cadence). The outcome is a public function of the Chainlink path, whose fair after
  six minutes of a fifteen-minute window is `Phi(ln(S_t / S_ref) / (sigma * sqrt(9 min)))`; the behavioural claim is
  that after three "Up" resolutions the first price sits above that fair by a few cents. The fee (0.07 x 0.25 = 1.75c
  at 0.5) and rebate (20% of fees) mean the maker, not the taker, is the route: quote the fair side one tick inside the
  tilted touch.
- Test (`P` + `A`): fresh frame `h10_q15` = closed 15-minute markets for the four assets on dates in [2026-04-01,
  2026-10-01) excluding CB8-B's sealed HOLDOUT weeks (the daily markets share the asset-weeks); the minute series by
  explicit-bounds `prices-history` (fact 6; one request per market, about 20,000 markets for 50 days, so a 5,000-market
  random sample, 1 request each) and the Data API prints (few per market); the path from the Binance 1-minute archive
  (CB8-B's source, an acceptable proxy for Chainlink at minute scale); prior outcomes from Gamma (resolved before `t`,
  PIT-legal as a *conditioning* variable); the market's own outcome from the public path (equal-close clause as 50-50).
  Unit = market; feature = streak length and sign of the previous k windows (k = 1-4); control = the path-implied fair
  at the first print; primary = mean of (first price - fair), sign-aligned to the streak, by k, clustered by asset-day;
  a second line: calibration of the first price against the outcome by k. Rule-text gate: the reference time ("begin"
  appears in the text) must be parsed and checked against `createdAt` on 50 markets.
- Data: `P` (Gamma, CLOB history, prints) + `A` (Binance archive). Under 300 MB.
- Economics: maker at one tick inside the tilted touch: rebate 0.35c + half-spread 0.5c per filled share against a
  tilt of 1-3c if real; taker only when the tilt exceeds about 3c (fee plus spread).
- Kill: aligned tilt < 1c at k >= 3 with CI excluding 2c; or the tilt is matched by the realised outcome rate (a true
  hot hand in 15-minute BTC returns, which the literature puts near zero); or fewer than 400 markets per k-cell.
- Leakage/confound: the first "price" is a mid-like series point (tightness: 15-minute markets carry the maker rebate
  programme, so books are usually 1c wide, but check); the Binance-vs-Chainlink path difference at minute scale; the
  creation lag varies (use the first price after `startDate`, never before).
- Novelty: CH51 (series calibration), CH76/CB8-B (daily terminal minutes), CH84's 15-minute maker (dropped for the
  CB8-B calendar; here the path is a control, not the route); new: the late-creation fact and the streak conditioning.
  N 3, EV 2, C 2.

**CH103. Hidden long-dated books: at least 2,100 markets are flagged inactive yet open and accepting orders, the traded
ones ending in 2027-2028 (fact 1); they are not surfaced to retail, so their quotes are set by a few bots and holders
and go stale for weeks; where a hidden rung has a visible sibling in the same deadline ladder, the within-ladder
dominance pair (CH12's riskless construction) is violated more often and for longer than in visible ladders, and the
hidden rung's price lags public information by days.**
- Mechanism: a market with `active=false` is absent from lists and search in the UI but the CLOB accepts orders and UMA
  resolves it under its rules; nobody is paid to look at it; capital is locked to 2028 at zero interest (CH115), so no
  arbitrageur corrects a 3c gap. Route (a): `ask(YES by 2028) < bid(YES by 2027)` or, for a non-holder, buy YES-2028 at
  its ask and NO-2027 at its ask for less than $1 total: payoff >= 1 in every state (CH12's pair). Route (b): the
  hidden market's price against a visible twin or an external anchor (CH106-CH109) when the hidden quote is stale.
  Methods consequence regardless of money: if the complete-universe capture takes `active=true` only, AREPO's universe
  is incomplete by at least 2,100 open markets, which AGENTS.md says must never be reduced for convenience.
- Test. **Census (`P`, one afternoon, about 40 Gamma pages):** every `active=false, closed=false` market with end year,
  volume, event, neg-risk flag, sibling presence (same event or same question stem with another date), `description`
  hash; compare ids against the latest capture (the `A` check). **Pairs (`P`, three weeks):** for hidden rungs with a
  visible sibling rung (expected 100-300 pairs), read both CLOB books daily; count dominance violations net of fees
  (`rate*p*(1-p)` per leg; politics 0.04) and their persistence in days; clusters = event. **Staleness (`P`):** for
  hidden markets with a visible twin on the same question, the twin's 7-day move vs the hidden market's; the
  hidden-minus-twin lag in days. Economic (route a): both legs at recorded asks, hold to the near date; the net gain
  per $1 locked and its annualised value (a 3c gain on a 12-month lock is 3%; the floor is 5c net).
- Data: `P` (Gamma, CLOB books), `A` (captures for the universe check). Under 50 MB.
- Economics: route (a) is riskless but capital-locked (the floor above); route (b) is a hold-to-resolution carry with
  CB1's tail gate; capacity = the resting size on the hidden book (expect small: tens to hundreds of dollars).
- Kill: fewer than 20 traded hidden markets with a visible sibling; or violations < 1 per 50 pair-days; or net gaps
  < 3c; or the hidden markets' rules differ from their siblings' in more than 20% of pairs (then it is CH64, not this).
- Leakage/confound: hidden markets may be hidden because they were superseded or mis-worded (rule divergence; a
  `description` diff against the sibling is part of the census); stale quotes may be dust (CH80's size check: ignore
  levels under 5 shares); the 2028 end dates may be placeholders that Polymarket will re-list.
- Novelty: CH04 (zombie quotes after a decisive event), CH10 (placeholder members), CH12 (dominance pairs in visible
  ladders) are the parents; new: a population of open markets that no panel, batch or capture has examined. N 4,
  EV 2-3, C 1-2.

### C. Resolution plumbing and deadlines

**CH104. DVM reveal-tally lead: when a Polymarket resolution is disputed, UMA token holders vote on Ethereum mainnet in
a commit phase followed by a reveal phase; revealed votes are public events, so the running tally is visible hours
before the price is settled and before Polymarket's market resolves, while the Polymarket price during the dispute
sits between the two readings; buying the leading side once the revealed tally passes 80% pays when held to
resolution.**
- Mechanism: disputes lock a market for 4-6 days with a 50-50 tail (round 1 CH03, CH47); voting power is concentrated
  (top-10 wallets over half, round 2 sources), so the tally is decisive early in the 24-hour reveal window. The signal
  is on a different chain from the market and in a contract most traders never read. Who pays: holders who sold into the
  dispute's uncertainty and buyers of the losing side's lottery. It is cross-venue information of the kind that
  survived (a public source leading the price), with the latency measured in hours, not minutes.
- Test (`P`, historical first). The population comes from Polygon `DisputePrice` logs on the OptimisticOracle used by
  Polymarket's adapters (keyless RPC `eth_getLogs` over 12 months, about 8,000 bounded requests in the `net` lane after
  `T_seal`; the Gamma status field does not record disputes, fact 2); for each dispute, the mainnet `VoteRevealed`
  events (`eth_getLogs`, a few requests per dispute) give the tally path; the Polymarket minute series by explicit-bounds
  `prices-history` over the reveal window. Unit = disputed market; feature = tally share at hours 2, 6, 12 of reveal;
  target = the settled price (YES, NO or 50-50) and the P&L of buying the tally side at the recorded mid plus half the
  median dispute-window spread (optimistic, labelled) when tally >= 80% and the market is >= 10c from that side.
  Clusters = dispute week. Census gate: >= 60 disputed markets whose price at reveal start is more than 5c from the
  final settlement; otherwise not testable, counted.
- Data: `P` (Polygon and Ethereum public RPC, CLOB history). Under 100 MB.
- Economics: fee <= 1c, dispute-window spreads 5-10c, so the gap must exceed about 10c; holds <= 2 days; capacity is
  the resting depth of a disputed book (small).
- Kill: census gate fails; or the price already sits within 5c of the tally side at reveal start in > 80% of cases
  (the rules, not the tally, were the information); or net <= 0.
- Leakage/confound: the vote often follows the rules text, which the crowd can read too; 50-50 "unknowable" results
  make the payoff 0.5; voter identities and conflicts are not used (no wallet work); the reveal window's timing must
  come from the contract's round schedule, not from Polymarket.
- Novelty: CH03, CH47, CH65 (dropped), CH85 are the parents; new: the reveal-phase tally as a cross-chain leading
  indicator. N 4, EV 2, C 3-4.

**CH105. Deadline-hour descriptive: "by <date>" rules run to 11:59 PM ET, so the last four to five hours of a deadline
day fall after 00:00Z; if traders and bots key on the UTC date (or on a Gamma `endDate` stored at 00:00Z), the YES
price collapses at 00:00Z while the event can still happen, and YES bought just after 00:00Z on deadline days resolves
YES more often than its price.**
- Mechanism: US evening news (8 PM to midnight ET) is a dense window for announcements, signings and game results; a
  market whose deadline is "October 31" is open for them; a crowd that reads the date in UTC is not. The measurable
  comes first: the distribution of `endDate` clock hours for "by <date>" markets (`A`: captures hold `endDate`) tells
  whether the venue itself encodes ET deadlines as UTC midnight.
- Test (`A` + `P`): (1) census of `endDate` hours for markets whose question matches "by <month> <day>"; (2) fresh
  `h10_tz` minute series (explicit bounds) for 1,000 such markets on their deadline date, 22:00Z to 05:00Z: the mid
  change across 00:00Z vs the changes across 23:00Z and 01:00Z (a discontinuity test with the J4-R placebo); (3)
  hold-to-resolution: YES at the 00:05Z ask (prints, where present) vs resolution, clusters = deadline date.
- Data: `A` + `P`. Under 50 MB.
- Economics: one-leg carry, fee <= 1c, half-spread 1-2c at low prices; the event must occur in the window at a rate
  above the price by 3c+; capacity tiny.
- Kill: no 00:00Z discontinuity (CI within +/- 1c of the neighbouring hours); or fewer than 30 markets whose YES event
  fell inside the window.
- Leakage/confound: Polymarket may close markets early on the UTC boundary (then the window does not exist: the census
  shows it); selection on resolved-YES is avoided by the discontinuity design.
- Novelty: CH62 (calendar-decided NO carry), CH49; new: the clock-boundary mechanism. N 3, EV 1, C 1.

### D. Public calendars and filings (parents CH28, CH49, CH74)

**CH106. Public hazard calendars for single "by date" markets: the day-by-day hazard of court rulings, confirmations,
bill actions and rule publications is concentrated on scheduled days that public calendars announce in advance
(Supreme Court opinion days, Senate cloture clocks and the executive calendar, the House floor schedule, Federal Register
public inspection, FDA action dates); the crowd prices a flat hazard, so YES is cheap the evening before a scheduled day
and dear the evening after an empty one.**
- Mechanism: "Will the Court rule on X by June 30" has a hazard of zero on non-opinion days and large on announced
  opinion days; a confirmation follows a cloture filing by a near-fixed clock; a rule appears on public inspection the
  day before publication. Prices move when the event happens, not when the calendar says it may; the gap is the
  calendar-implied hazard on the next scheduled day minus the flat hazard the price implies. Fact 7: 50+ closed
  "Supreme Court" events (132 markets); confirmation and bill markets add dozens a year.
- Test (`P`, historical): fresh `h10_cal` = closed timing markets ("by <date>") in the court, confirmation, bill and
  rule classes (frozen regex, hashed before the census) with resolutions in [2025-06-01, 2026-10-01); calendars from
  archived public sources with publication dates (the Court's calendars and opinion lists, the Senate executive
  calendar, the Federal Register public-inspection API's `filed_at`), stored with their fetch and publication times;
  unit = market x calendar day; features = scheduled-day indicator (published >= 1 day before), days remaining;
  target = print-based price change over the day and the YES resolution; primary = scheduled-day mean move (sign YES)
  minus pseudo-scheduled-day mean move (same weekday, not scheduled), clusters = calendar day; secondary = hazard ratio
  of resolution on scheduled vs non-scheduled days. About 100-150 markets x 5-20 days = 500-2,000 unit-days, about 150
  clusters; MDE about 1.5c on the daily move.
- Data: `P`. Under 50 MB.
- Economics: buy YES at the prior day's close ask, hold to resolution if the event occurs, else sell at the scheduled
  day's close bid: round trip about 4c (spread plus two fees) against an expected move of `p_cal - p_flat` times the
  payoff; the hold-to-resolution variant pays one half-spread and one fee and avoids the exit.
- Kill: scheduled-minus-pseudo move < 1c; or hazard ratio < 3; or fewer than 60 markets with >= 3 scheduled days.
- Leakage/confound: calendars are public and the crowd may step up the evening before (measure the pre-step; the
  hypothesis survives only if the step is incomplete); direction markets ("rule for X") are excluded (timing only);
  opinion days can be announced a day ahead, so the publication time must be stored.
- Novelty: CH49 (fixed-cadence calendars for *ladders*), CH74 (dockets, dropped: keyless unverified; the sources here
  are verified public pages and one API), CH28 (scheduled statistics); new: dynamic schedules for single timing markets.
  N 3, EV 3, C 2.

**CH107. EDGAR-first for filing-resolvable markets: bankruptcy (8-K Item 1.03), merger agreements (1.01) and officer
departures (5.02) hit EDGAR's keyless full-text search with an acceptance time minutes before coverage, and the Polymarket
markets that resolve on them (29 closed bankruptcy events, 62 markets; a few acquisition markets) reprice minutes to
hours later; the lag is the money, as a taker at the stale ask.**
- Mechanism: these markets are small and few, so no bot watches EDGAR for them; the filing *is* the resolution event (a
  public function of a public record). Fact 8: 44 "chapter 11" 8-Ks in one month on the FTS endpoint.
- Test (`P`): historical lag study: for every resolved bankruptcy / acquisition / departure market since 2025-01-01
  (fresh `h10_edgar`), the matched filing's acceptance time from the EDGAR index and the Polymarket minute series
  (explicit bounds) around it; the lag to the first print and to a price within 5c of the outcome; the ask at +1, +5,
  +15 minutes (prints) vs the outcome; clusters = filing. Prospective: a one-minute FTS poller on the entities of open
  markets, the book at the first hit. Expected count 30-60 filings in the window: a descriptive lag distribution plus
  one counted test (net of buying at the +5-minute ask) if >= 25 cases.
- Data: `P`. Under 20 MB.
- Economics: fee <= 1c, spread 3-5c in thin markets; the gap at +5 minutes must exceed about 6c; capacity small.
- Kill: median lag < 2 minutes (bots are there); or fewer than 25 cases; or net <= 0.
- Leakage/confound: filings often follow a press release by minutes (the release is the real first source; store the
  wire time where public); entity matching errors; the market may require a *court* docket rather than the 8-K.
- Novelty: CH74 (dockets), CH28; new: EDGAR as a verified keyless, machine-readable first source. N 3, EV 2, C 2.

### E. Statistic-resolved markets (parents CH28, CH32, CH75)

**CH108. Running-count convergence (extrapolation neglect): for markets that resolve on a public running statistic with
a keyless feed (USGS earthquake catalogue, CDC weekly measles counts, Rotten Tomatoes scores, App Store ranks,
Polymarket's own volume) the final value is a known statistical function of the current count and the time remaining
(a Poisson tail with the long-run rate; a cumulative count with the recent weekly increment; a Beta-binomial posterior
of the fresh share), and the crowd prices the current state instead; buying the model side when the two differ by more
than 8c pays when held to resolution.**
- Mechanism: "Will a magnitude 6.5+ earthquake strike <region> by <date>" has an exact public prior: the declustered
  Gutenberg-Richter rate from a 50-year catalogue gives `1 - exp(-lambda * tau)`; the crowd either forgets the base rate
  (underpricing YES for thresholds where the Poisson probability exceeds 0.5) or overreacts after a salient quake. CDC
  counts ("measles cases exceed X by <date>") converge at a trend visible in the prior weeks; a Rotten Tomatoes score
  with 40 reviews has a known posterior width; an App Store rank persists with a known half-life. Fact 7 gives the
  populations: earthquake 50+ events / 198 markets (and more by a date walk), measles 35 / 160, RT 50+ / 358, App Store
  50+ / 881.
- Test (`P`). Each class has its own frozen model, declared before the census, and a pre-declared sign where the
  mechanism predicts one (earthquakes: YES underpriced when the Poisson probability >= 0.5). **Historical arm (fully
  keyless):** earthquakes (USGS FDSN event API, complete history; markets' minute series by explicit bounds; outcome =
  the catalogue, never the Gamma field) and measles (archived CDC weekly tables, PIT by publication date); unit =
  market x weekly checkpoint; primary = pooled slope of `(Y - p)` on `(q_model - p)` with class fixed effects,
  clusters = event; secondary per class. **Prospective arm:** RT and App Store (live feeds polled daily; the iTunes
  top-chart RSS is keyless) over 8 weeks. About 200 earthquake + 160 measles markets x 4-8 checkpoints = 1,500-3,000
  units, 80+ clusters; slope MDE about 0.25.
- Data: `P`. Under 100 MB.
- Economics: fee `0.05*p*(1-p)` <= 1.25c (economics/culture), spreads 3-4c in these thin markets; break-even gap
  about 5c; the 8c filter; holds of days to weeks (CB1's tail gate and resolution-week clustering apply).
- Kill: pooled slope CI includes 0; or fewer than 30 markets in a class; or net <= 0 at the 8c filter in the historical
  arm.
- Leakage/confound: Polymarket sets thresholds near the crowd's median (creator selection); aftershock clustering (use
  declustered rates and exclude 30 days after an M7+); CDC reporting lags and revisions (CH75's first-print issue:
  resolve on the first published value as the rules do); RT "certified fresh" rounding; App Store ranks move with
  launch calendars (a covariate).
- Novelty: CH28 (timing of scheduled sources), CH75 (first print), CH32 (mention base rates), round 3's rejected
  running-count buckets (paid X counts, rare storms); new: classes with keyless public counts and an exact statistical
  prior, one of them (earthquakes) fully historical. N 3, EV 3, C 2.

**CH109. Known-formula aggregator lag: some markets resolve on an aggregator whose inputs are public before the
aggregator updates (poll averages from individual poll releases; Billboard's Hot 100 from public daily streaming and
sales charts; a model leaderboard from public votes; Monday box-office actuals from Sunday studio estimates), so the
aggregator's next value is computable hours to days ahead; Polymarket's threshold markets move on the aggregator's
update, not on the inputs, and buying the computed side before the update pays.**
- Mechanism: an approval-rating market resolves on a named average on a date; the average is a documented function of
  listed polls; each poll is public at release, hours before the average refreshes. The crowd watches the average. The
  Wikipedia poll tables' revision history gives a keyless point-in-time record of when each poll became public, and the
  Wayback Machine's CDX index gives the aggregator's own update times.
- Test (`P`, historical for polls and box office; prospective for charts): unit = aggregator update; feature =
  computed next value minus current value, relative to the market's threshold; target = the Polymarket price change
  between the last input release and the aggregator's update (print-based) and the resolution; economic = buy the
  computed side at the ask when the computed value crosses the threshold and the price is below 0.80 (or above 0.20),
  hold to the update or resolution. Count: approval and poll-average markets (dozens, monthly series), Billboard
  (weekly, about 50 a year with several markets each), box office (CH28's parent class); about 100-200 crossing events,
  clusters = aggregator x update.
- Data: `P`. Under 50 MB.
- Economics: fee <= 1c, spread 2-4c; the computed value must cross the threshold by more than the aggregator's
  inclusion noise; holds of hours to days.
- Kill: the price moves toward the computed value before the update in more than 70% of crossings (the crowd computes
  it too); or fewer than 25 crossing events; or net <= 0.
- Leakage/confound: the aggregator's inclusion rules are partly discretionary (RealClearPolitics), so the formula is
  approximate; poll release timing is itself news; chart formulas have unpublished weights (treat Billboard as
  approximate and report separately).
- Novelty: CH28, CH31 (FedWatch), CH90 (nowcasts, dropped: no formula and too few releases); CH108 is statistical
  extrapolation, this is a deterministic formula with a publication lag. N 3, EV 2-3, C 2-3.

### F. Footprints that are not wallets (parents CH41, CH55, CH69, CH93)

**CH110. Alert-threshold discontinuity: prints whose notional just exceeds the thresholds used by public whale-alert
feeds and the venue's own large-trade displays (expected $10,000 and $25,000; the exact values are a census item) are
followed within 15 minutes by more same-direction flow and a larger same-direction price move than prints just below the
threshold, with no information difference between the two; a maker who quotes one tick behind the move for 15 minutes
after a broadcast print is filled by copiers whose mark-out is at or below zero.**
- Mechanism: a $10,200 print is pushed to thousands of phones and copy-trading apps; a $9,800 print is not. The
  regression discontinuity in notional identifies the broadcast effect separately from the information in size (which is
  continuous across the threshold). It is CH55's copying without the leaderboard wallet: the trigger is public and
  wallet-free. Informed traders who split orders below thresholds would produce the opposite jump, which is also
  informative (then CH69's footprint rule applies).
- Test (`P` + `A`, side-free). Fresh `h10_alert`: Data API prints for about 2,000 markets with >= 20 prints of
  >= $5,000 in [2026-04-01, 2026-10-01), newest-first pages, aggregated to transactions (CB10-B's convention; notional =
  sum of size x price), disjoint by event key from `h9_flow`, `h10_brk` and CB9's K/D frames. Unit = transaction with
  notional in [$5k, $20k] or [$15k, $40k]; running variable = notional; outcomes: (i) the signed 15-minute and 2-hour
  print-based move in the direction of the transaction's own impact (its price vs the previous transaction's price),
  (ii) the count and notional of same-impact-sign transactions in the next 15 minutes. Local-linear RD at $10k and $25k
  with a $2k bandwidth, a donut of +/- $50 (exactly-round notionals are CH111's retail mass, not whales), placebo
  thresholds at $8k, $12k, $20k, $30k; clusters = event. About 20,000 transactions in the $10k band; with a 15-minute
  move SD of about 2.5c the jump MDE is about 0.5c. Prospective: the live monitor's >= $1k prints (5-minute cadence,
  `A`, since October) give the same RD on the 2-hour outcome once a few weeks accumulate.
- Data: `P` + `A`. Under 200 MB.
- Economics: the maker's gain is the copiers' mark-out (expected 0 to -1c per filled share for them) plus the
  half-spread; the taker route (ride the wave for 5 minutes) needs a wave > 4c, which only thin markets could show.
- Kill: no jump at either threshold (CI within +/- 0.3c) and no jump in follow-on counts; or the thresholds cannot be
  identified (the census of feeds finds no common values).
- Leakage/confound: round-notional mass at exactly $10,000 (the donut); fragmentation across makers (aggregated by
  transaction hash); the fee changes the received-shares arithmetic but not the notional; a print's impact sign is
  a side-free proxy and is wrong for prints inside the spread (exclude prints that did not move the price).
- Novelty: CH55 (leaderboard copying by wallet), CH37 (movers-list artefact flow), CH93 (round *price* levels); new:
  the notional threshold as a wallet-free broadcast trigger. N 4, EV 2-3, C 1-2.

**CH111. Round-dollar footprint: the venue's interface takes a dollar amount, so retail transactions have round-dollar
notionals ($5, $10, $20, $25, $50, $100 and multiples) and fractional share counts, while programmatic orders have
round share counts and fractional notionals; the numeric shape of a transaction classifies its origin without any
wallet, the flow-continuation effect (E007 +0.36c; HB1 FL +0.3 to +0.6c per SD) is carried by non-round-dollar flow,
round-dollar flow has a mark-out near zero, and a maker who declines to quote when the trailing hour's non-round share
is high avoids most of the 1-7c adverse selection the economic study measured.**
- Mechanism: a $20 buy at 0.37 is 54.05 shares; an API order is 100 shares for $37. After the taker fee the *received*
  shares shrink, so the classifier uses the paid notional (size x price at the fill), reconstructed per transaction. The
  numeric shape is public in every print and costs nothing. Who pays: nobody yet; it is a composition measurement with
  two uses: a maker presence filter and a re-weighting of signed flow that, if the effect is concentrated in a third of
  the volume, triples the per-unit coefficient (orthogonal to CH79's sign-error story; CB9-S measures the sign, this
  measures the mix).
- Test (`P`, screenable this week). Fresh `h10_shape`: prints for about 1,500 markets (stratified by liquidity and
  category) in [2026-04-01, 2026-10-01), aggregated to transactions; disjoint by event key from every prior print
  sample. Shape classes, frozen: round-dollar (notional within $0.01 of the grid {1, 2, 5, 10, 20, 25, 50, 100, 250, 500,
  1,000} and multiples of $100 above), round-share (size within 0.01 of multiples of 10 up to 100 and of 50 above),
  both, neither; ambiguous cells (prices at which both are round, e.g. 0.50) excluded. Unit = market-hour. Line 1
  (side-free): the 2h and 6h print-based move regressed on impact-signed flow split by shape; primary = the difference
  of per-SD slopes (non-round minus round), event-clustered. Line 2 (maker): a paper touch maker (CB3's machinery on
  prints alone: fills at the touch when a print crosses it) with the mark-out of each fill by the shape of the filling
  transaction; primary = mark-out(non-round) minus mark-out(round). Descriptives: shape shares by category, price band,
  hour and fee era (the shape arithmetic changed with the fee rollout: report eras separately). About 150,000
  transactions; slope-difference MDE about 0.15c per SD.
- Data: `P`. Under 300 MB. (The live monitor and trade samples already hold size and price, so the shape shares can be
  tabulated on `A` today as a descriptive; the counted test uses the fresh fetch.)
- Economics: the maker's value is the avoided adverse selection times the share of fills avoided (if non-round flow
  is 40% of fills and carries all of the 1-7c, the filter saves 0.4-2.8c per quoted fill); the taker route still faces
  the 1.8c round trip unless concentration lifts the effect past it, which the slope ratio will say.
- Kill: slope difference CI includes 0; or round-dollar transactions under 15% of transactions (nothing to filter); or
  the shape shares are unstable across fee eras in a way that breaks the classifier (then a per-era rule is a design
  change, not a rescue).
- Leakage/confound: bots can send round-dollar orders (then the classifier is diluted, not biased); sweeps that cross
  levels produce odd notionals for retail too (aggregate by transaction and classify the total); markets priced at
  exact round fractions; the Data API's `size` may be post-fee for buys (a decoding check on 50 receipts in the smoke).
- Novelty: CH41 (farmer share by wallet volume tier), FL5 (small trades), CH69 (TWAP clips), CH96 (funding class); new:
  the numeric shape of a print as a wallet-free origin classifier. N 4, EV 3, C 1.

**CH112. Mention-basket overpricing: in "Will X say Y during Z" events (50+ closed events, up to 44 word markets each)
the sum of the members' YES prices two hours before the speech exceeds the number of words actually said, by a margin
that a maker selling YES across the basket at the touch and holding to resolution captures with no transcript, no
external data and a few hours of exposure.**
- Mechanism: each word is a lottery ticket for retail (prices 0.1-0.6), and the basket's expected count is never traded
  as such; longshot bias and salience push each ticket up, and the sum reveals it. The venue chooses words it thinks
  plausible (which raises the count and works *against* the hypothesis, so the test is conservative). CH32 priced each
  word from transcripts; this needs only Polymarket's own resolved counts.
- Test (`P`, screenable this week, fully keyless). Fresh `h10_say`: closed events whose title matches the frozen
  mention regex, walked by end date over [2025-06-01, 2026-10-01) (public search caps at 50 events; the `/events` walk
  does not); for each member, the minute series (explicit bounds) at `t` = scheduled start - 2h and - 24h and the last
  print before `t`; outcomes from Gamma under the standard guard. Unit = event; primary = mean over events of
  `S_t - N` (sum of YES prices minus the number of YES resolutions), event-clustered (events are the clusters;
  expected 60-150); secondary = per-word calibration slope of `(Y - p)` on `p`, event-clustered; splits by series age
  (CH51's learning), speaker and basket size. Economic: paper maker asks at the touch on every member at `t - 2h`,
  filled by prints at or above the ask (CB6-C's fill envelope), net per filled share = `p_ask - Y`, maker fee 0;
  tail = events with large `N`. MDE at 80 events with SD(S - N) about 2 words: about 0.6 words (12% of a 5-word mean).
- Data: `P`. Under 30 MB.
- Economics: zero fee as maker, no spread paid; the risk is a long, on-message speech; the taker version (buy NO on
  each member) pays 0.04 x p(1-p) per leg and a half-spread each, about 2c per word, which eats a 12% overpricing on a
  0.3 average price (3.6c) only partly.
- Kill: mean `S_t - N` <= 0.3 words or <= 5% of `S_t`; or the per-word calibration slope >= 0.9; or fewer than 40 events
  with >= 8 members.
- Leakage/confound: the venue's word selection; later series may be calibrated (split); partial-word adjudication
  disputes; prices at `t - 2h` are mid-like (tightness: use the last print as the second anchor).
- Novelty: CH32 (per-word base rates from transcripts); new: basket-level count calibration on Polymarket's own data.
  N 3, EV 3, C 1.

### G. Cross-venue beyond identical pairs (parents CH25, CH38, CH58, CH73)

**CH113. Kalshi-ladder implied CDF as the anchor for Polymarket bucket events: Kalshi lists dense strike ladders on
economic releases and other statistics (55 Economics events with >= 5 markets on one page, fact 8) while Polymarket lists
coarse buckets; the probability of a Polymarket bucket implied by Kalshi's ladder (frozen interpolation between adjacent
strikes) leads the bucket's own price by the same 10-20 minutes the identical-pair study found, on pairs the one-to-one
matcher excluded by construction; the route is CH73's maker skew toward the implied price.**
- Mechanism: the professional makers who move Kalshi first (the replicated lead) express their distribution across
  the whole ladder; the Polymarket bucket is one slice of it. The audited pair history (316 pairs) only holds identical
  questions, so the structural population is untested.
- Test (`P`, prospective; historical if Kalshi's candlestick history is keyless as used in CROSS_VENUE_STUDY §2). A
  frozen matcher (same release, same statistic, Polymarket bucket edges contained within Kalshi's strike range, hand
  audit of every pair as CB5-K's precedent) over the open ladders; a 10-minute poller on both sides; lead-lag of
  10-minute changes (the study's estimator) and the gap's out-of-sample prediction of the Polymarket bucket's next
  move; the maker contrast (skewed vs unskewed, mark-out at 1h) on the sweep books. Clusters = release event
  (CPI, jobs, Fed, GDP, gas, plus technology and entertainment ladders): 40-80 clusters a quarter.
- Data: `P` (+ `A` sweeps). Under 100 MB a quarter.
- Economics: maker route (no fee, half-spread 1-2c); a taker route pays the 4.5c median round trip against a 10-minute
  lead, as before.
- Kill: lag-1 cross-correlation < 0.10 (identical pairs: 0.24-0.26); or fewer than 30 matched bucket pairs; or the
  maker contrast <= 0.
- Leakage/confound: differing rounding and resolution conventions ("above 3.1%" vs "3.1-3.3%"); interpolation error
  at the edges; the identical-pair study's timestamp caveats (its §6).
- Novelty: CH25, CH38, CH58, CH73 (identical pairs); new: structural pairs through the implied CDF. N 3, EV 2-3, C 3.

**CH114. Fee-adjusted PredictIt anchor: PredictIt's keyless feed (207 markets, 635 contracts, fact 8) prices a third
crowd (US retail, $850 position cap, 10% fee on profit and 5% on withdrawal) whose fee creates a known, computable price
bias; the PredictIt price net of that bias, compared with Polymarket's on the same political question, predicts the
resolution beyond Polymarket's price, in the direction PredictIt favours.**
- Mechanism: with a 10% fee on profit, a YES bought at `p` pays `(1 - p) * 0.9` if right, so PredictIt's no-arbitrage
  band is wider and longshots sit high; the adjustment is a formula, frozen from the published fee schedule. The crowd
  is capped and small, which removes whales and bots: a different information set from Kalshi's (Robinhood plus makers)
  and Polymarket's (crypto whales plus bots). The programme's core question is information beyond price; a third crowd
  is a candidate source.
- Test (`P`, prospective): a one-minute feed poll (1,440 light requests a day); a frozen title matcher with a hand audit
  of every pair; Polymarket from the 2h captures and sweeps; unit = pair-day; primary = slope of `(Y - p_pm)` on
  `(p_pi_adj - p_pm)`, clusters = election or event (about 40); secondary = the 10-minute lead of PredictIt's changes
  where its volume concentrates (congressional races, primaries, approval). 8 weeks; 100-200 matched contracts.
- Data: `P`. Under 50 MB.
- Economics: hold-to-resolution carry on the PredictIt side; fee <= 1c, half-spread 1-2c; the level gap must exceed
  about 4c after the fee adjustment.
- Kill: fewer than 60 matched contracts; or slope CI includes 0 after 8 weeks.
- Leakage/confound: the cap and fee produce mechanical gaps that are not information (the adjustment handles the fee,
  not the cap; report by PredictIt volume); matcher errors (CB5-K's four hand-dropped pairs); politics only (the
  category confound is the population).
- Novelty: CH25 (Polymarket-Kalshi partisan level gap), round 2's rejected cross-venue median (three venues without
  feeds); new: a verified keyless third venue and the fee-adjusted level. N 2-3, EV 2, C 2.

**CH115. Horizon-dependent staleness (capital lock-up at zero interest): correcting a 3c mispricing in a market that
resolves in twelve months yields under 3% annualised, below any arbitrageur's hurdle, while the same 3c in a two-day
market is hundreds of percent; so the speed at which public information is impounded falls steeply with time to
resolution, the cross-venue gap half-life (80 minutes pooled) is hours to days in long-dated pairs, and anchor-based
routes pay at AREPO's 2-hourly cadence only in the long-dated tail, where the route must be a maker (no lock) rather
than a taker (who inherits the lock).**
- Mechanism: a hunting rule rather than a route. The hidden 2028 books (CH103) are its extreme; CH106-CH109's carries
  live in weeks-long markets for the same reason; the identical-pair study's 86% Polymarket closing share and 80-minute
  half-life are pooled across horizons.
- Test (`A`, screenable now, one afternoon): the audited cleaned pair set (C1, 316 pairs, 10-minute) with each pair's
  time to resolution at observation (Gamma `endDate`, fixed at listing; checked for edits); the gap half-life and the
  lag-1 to lag-12 cross-correlations by horizon tercile; one counted contrast: half-life(long tercile) -
  half-life(short tercile) > 60 minutes, clusters = pair, placebo = horizons shuffled across pairs; descriptives:
  gap size by horizon, stratified by category and by Polymarket volume (the two confounds). A second `A` line: the 2h
  captures' `oneHourPriceChange` autocorrelation by horizon (a cheap staleness proxy, J4 caveats).
- Data: `A`. No fetch.
- Economics: none directly; it re-scopes CH73, CH113 and every anchor carry to the horizons where the lead is long
  enough to act on, and tells the maker where fills are least adverse.
- Kill: the half-life does not rise with horizon (contrast CI includes 0 after stratification), in which case capital
  lock-up is not binding and the hunting rule is dropped.
- Leakage/confound: long-dated pairs are mostly political (stratify); thinner (control by volume); CH25's persistent
  level gap is a level, not a half-life (use demeaned gaps per pair); E009/E010's registered rows are not touched (the
  historical pair set only).
- Novelty: CH25, CH40 (late-life adverse selection), J8's C-TTE (time-to-end improves forecasts); new: the funding-cost
  mechanism and its half-life-by-horizon prediction. N 3, EV 2, C 1.

### H. Measurement and text (parents E003, CH20, CH45, CH63, CH80)

**CH116. Reward-band-stripped book imbalance: the liquidity-rewards programme pays for two-sided quotes inside
`rewards_max_spread` of the size-cutoff midpoint, so bots keep nearly symmetric in-band depth at all times; the displayed
top-of-book imbalance is a subsidy artefact, which is why E003 found it uninformative; imbalance computed on depth
outside the band (natural orders) or on the in-band asymmetry that appears when a bot pulls one side predicts the 2h
print-based move, and a maker's own skew can key on it.**
- Mechanism: the band is public per market (sidecar `rewards_max_spread`, `rewards_min_size`; CB3 and CH19 found the
  parameters rarely change) and the in-band depth is the reward chase, not opinion. Stripping it is the imbalance
  analogue of CH80's dust filter.
- Test (`P` + `A`): a fresh pmxt pull of about 800 markets (range reads, 1-2 GB, disjoint from CB3's and CB9's pmxt
  populations) with full-depth books; the band from the sidecar's current parameters (PIT from 11 Oct; before that,
  assumed constant, with a sensitivity using the empirically symmetric plateau width); unit = market-hour; features =
  imbalance inside the band, imbalance outside the band (levels with >= 5 shares, CH80), the one-sided-pull indicator;
  target = 2h print-based move; primary = slope(outside) and slope(outside) - slope(inside), event-clustered, J4-R
  increment-shuffle placebo. Prospective: add a 10c-depth field to the sweep row (one field) so the outside measure
  exists live.
- Data: `P` (pmxt) + `A` (sidecar). 1-2 GB ingress.
- Economics: a maker filter and skew (no fee); the taker version is E003's and stays uneconomic unless the outside
  slope is several cents per SD.
- Kill: slope(outside) CI includes 0 and the difference CI includes 0.
- Leakage/confound: bots also quote outside the band; stale natural orders (CH80); parameter changes before 11 Oct
  (sensitivity); the midpoint definition is the size-cutoff-adjusted one (CB9 probe 8).
- Novelty: E003 (null imbalance), CH20, CH45, CH71, CH80; new: removing the subsidy layer from the measure. N 3, EV 2,
  C 2.

**CH117. Logical-form calibration: questions whose YES requires a conjunction ("A and B", "both", "all of") are
overpriced and questions whose YES is satisfied by a disjunction ("A or B", "either", "any of") are underpriced, by the
conjunction fallacy and disjunction neglect respectively; NO on conjunctions and YES on disjunctions, held to
resolution, pay beyond the price.**
- Mechanism: the literature's sign predictions (Tversky and Kahneman 1983; Bar-Hillel and Neter 1993) applied to the
  rules text rather than the question title. Fact 9: about 16% of recent closed questions carry a connective, many
  spurious, so a hand-audited logical parse (>= 200 questions) is the first gate.
- Test (`P`, prospective on the live `textorig` table; `h8_text` took the whole historical pool, so no key-disjoint
  historical sample exists): frozen regex plus the audited parse; unit = market at 7 days before the scheduled end;
  target = `Y - p`; primary = class contrast (conjunction vs disjunction vs neither) *within* strata of CH63's condition
  count (so this is not CB7-S again); event x resolution-week clusters; CB1's tail gate.
- Data: `P`. Under 20 MB.
- Economics: one-leg carries, fee <= 1c, half-spread 1-3c; the contrast must exceed about 3c.
- Kill: fewer than 150 markets per class in 8 weeks; or contrast < 2c; or the contrast vanishes within condition-count
  strata.
- Leakage/confound: CH63's specificity (handled by stratification); rules text vs title; the clarification-marker
  exclusion.
- Novelty: CH63 (condition count), CH87 (reporting standard); new: the disjunction side and the sign prediction from
  logical form. N 2, EV 2, C 2.

---

## 3. Ranked top 8

Rank = originality x plausibility x testability now x money route. "Runnable now" means the test can start this week
on existing stores or on keyless fetches that are not bound to the `T_seal` lane.

| Rank | ID | One line | Runnable now | Family |
|---|---|---|---|---|
| 1 | CH99 | Option-chain digital anchor for Pyth equity strike markets (keyless CBOE chain verified; professional counterparty; 20-50 markets a day) | yes, prospective from the first session | A |
| 2 | CH111 | Round-dollar footprint: the numeric shape of a print classifies flow without wallets; maker filter and flow re-weighting | yes (fresh print fetch; shape shares tabulable on the live monitor today) | F |
| 3 | CH112 | Mention-basket overpricing: sum of YES prices vs words said; maker sells the basket; fully keyless history | yes (fresh `h10_say`) | F |
| 4 | CH100 | Extended-hours anchor for next-day Up/Down dailies; historical window 2026-08-11 to 10-01 outside CB9-P | yes (CLOB history + Yahoo bars) | A |
| 5 | CH108 | Running-count convergence; the earthquake arm is fully historical with an exact public prior | yes (USGS + CLOB history) | E |
| 6 | CH110 | Alert-threshold discontinuity in print notional; wallet-free copy flow; maker fade | yes (fresh prints; live monitor for the prospective RD) | F |
| 7 | CH103 | Hidden long-dated books: 2,100+ inactive-but-open markets; CH12 pairs on hidden rungs; universe check | yes (census this week) | B |
| 8 | CH106 | Public hazard calendars for single timing markets (opinion days, cloture clocks, public inspection) | yes (fresh `h10_cal` + archived calendars) | D |

Next in line: CH115 (horizon staleness on the 316 pairs, one afternoon on `A`), CH102 (late-created 15-minute windows),
CH116 (band-stripped imbalance), CH113 (Kalshi implied CDF), CH109 (aggregator lag), CH104 (DVM tally), CH101
(non-equity Pyth), CH107 (EDGAR), CH114 (PredictIt), CH105, CH117.

**Screenable on data AREPO already holds (no fetch):** CH115 (the audited 316-pair history), CH110's prospective RD and
CH111's shape shares (live monitor prints since October, descriptive only), CH105's `endDate` census and CH103's
universe check (2h captures), CH116's band parameters (sidecar). Everything else in the top 8 needs a small keyless
fetch (`h10_*`) that can complete this week, except CH99, which is prospective by nature (the chain has no keyless
history) and could start collecting at the next session open.

**Screen sketches for the top 5.**
- **CH99.** Population: open Pyth equity strike markets ("close above $X") per session, text-flagged as CB9-P,
  excluding earnings sessions in the primary (reported separately). Decision time: 15:00Z, 17:00Z, 19:00Z, each after
  a chain read timestamped before the book read. Target: resolution from the public daily bar (sign of close vs `K`,
  equal = 50-50 cell). Statistic: slope of `(Y - p_pm)` on `(q - p_pm)`; economic net of buying the anchor side at the
  recorded ask when `|q - ask| >= 4c` after fee, held to 20:00Z. Clustering: session day (primary), underlying
  (secondary); 30 sessions, 1,800-4,500 units; floor 0.30 on the slope, 1.0c on the net.
- **CH111.** Population: `h10_shape` transactions in 1,500 markets, [2026-04-01, 2026-10-01), ambiguous price cells
  excluded. Decision time: the end of each market-hour with >= 1 transaction. Target: 2h and 6h print-based move.
  Statistic: difference of per-SD slopes of impact-signed flow by shape (non-round minus round); maker line: mark-out of
  paper touch fills by the filling transaction's shape. Clustering: event (two-way with hour-of-day); floors 0.15c per
  SD on the slope difference, 0.5c on the mark-out difference.
- **CH112.** Population: closed mention events with >= 8 members, [2025-06-01, 2026-10-01). Decision time: scheduled
  start - 2h (primary) and - 24h. Target: `N` = number of YES resolutions; per-word `Y`. Statistic: mean of `S_t - N`
  over events; per-word calibration slope; paper maker net per filled share at the touch ask. Clustering: event
  (events are units; a series cluster as the robustness layer); floors 0.3 words and 0.5c per filled share.
- **CH100.** Population: Pyth equity Up/Down markets with sessions in [2026-08-11, 2026-10-01). Decision time: 00:00Z,
  08:00Z, 13:00Z on the session day. Target: resolution from the public daily bars. Statistic: slope of `(Y - p)` on
  `(q_ext - p)` with the J4-R increment-shuffle placebo; Stage-2 economic net at recorded asks with a 5c filter.
  Clustering: session day; 600-700 units, 35 clusters; floor 0.30 on the slope.
- **CH108 (earthquake arm).** Population: closed earthquake-threshold markets since 2025-06-01 (date walk, not the
  capped search). Decision time: weekly checkpoints from listing to end. Target: the USGS catalogue outcome (never the
  Gamma field). Statistic: slope of `(Y - p)` on `(q_poisson - p)` with the declustered regional rate frozen before the
  census; economic net of buying the model side at the recorded ask (prints) when `|q - p| >= 8c`. Clustering: event
  (region x window); 150-200 markets, 50+ clusters; floors 0.25 on the slope, 1.0c on the net.

**How the families would be registered.**
- **A. TradFi dailies (CH99-CH101).** One prospective collector (chain, bars, books at three checkpoints; CB9-P's live
  job is the template) and one historical frame (`h10_ext`, `h10_cmdty`) with the public-path outcome guard; the slope
  test with a sign-shuffle placebo is common; CB9's exclusion keys are checked at every census.
- **B. New populations (CH102, CH103).** A census first in both; CH103's census doubles as a universe-completeness
  check for the capture job (a methods note if the hidden pool is missing).
- **C/D. Plumbing and calendars (CH104-CH107).** Log scans and archived calendars with stored publication times; CB1's
  tail gate and resolution-week clustering on every carry; counts before hypotheses (the CB4-N lesson).
- **E. Statistic-resolved (CH108, CH109).** One model per class frozen before the census, a pooled slope with class
  effects, the first-print rule for revisions.
- **F. Footprints (CH110-CH112).** One fresh print fetch can serve CH110 and CH111 if declared together, each with its
  own frozen classifier; CH112 is its own event walk. All side-free; CB9-S's verdict changes their interpretation, not
  their validity.
- **G/H. Cross-venue and measurement (CH113-CH117).** CH115 runs first on `A` because it re-scopes the others; CH113
  and CH114 are small pollers with audited matchers; CH116 is one pmxt pull; CH117 waits on `textorig`.

**What is honest to say about all of them.** Round 1 was carries, round 2 the maker in the right state, round 3 tails and
flow identity, round 4 measurement and new products. This round's bet is that the venue's crowd is weakest where a
*professional* price already exists for the same payoff (the option chain, the extended-hours tape, the Kalshi ladder),
where a *statistic* already determines the answer (running counts, formulas, calendars), and in *populations nobody
watches* (hidden books, late-created windows, mention baskets). None of it needs a wallet, and all of it is written
side-free because the sign of the public print is under audit. The counts in §0 are what makes these different from
CH90/CH91/CB4-N-style failures: every population here was counted before it was proposed, and the thin ones (CH104,
CH107, CH114, CH117) say so. Nothing here is edge until it has gone through screen, frozen replication, prospective
registration and an economic check at recorded prices.

---

## 4. Ideas considered and rejected, and why

- **In-game public win-probability anchor (ESPN's keyless scoreboard JSON).** The idea is CH23/CH44's object with a
  public model anchor; the probe returned 403 to the research user agent, so keyless access is unverified, and sports
  scope is the user's open decision. Parked with the same status as CH74: re-entry when a keyless scoreboard feed with a
  win-probability field is verified and the category is decided.
- **Up/Down-versus-ladder identity on the same asset and settlement minute** (the daily Up/Down equals the strike
  ladder's CDF at the prior close). True, but the interpolation error between strikes 2-3% apart is about the size of
  the gap, and both objects are sealed (CB8-B's daily Up/Down weeks, CB10-D's ladders). Re-entry after both report.
- **Pre-window "information-free hours" in 15-minute markets.** Killed by the 30th probe: the markets are created
  inside their window, so there is no pre-reference period to quote in. Only the streak residual survives (CH102).
- **Deposit-to-trade latency (large USDC inflows to a proxy predicting an imminent order).** Public on chain, but it is
  wallet work in all but name and its direction content is exactly what the freshness analyses found null.
- **Market-level paper-gain overhang (the share of holders in profit, from `/holders`).** The endpoint returns top
  holders only, the measure is CH42 (disposition) at a different unit, and it needs wallet-level cost bases.
- **Token-launch or airdrop-snapshot natural experiment on farmer flow.** A real regime change if a date exists; no date
  could be verified keyless. One line for the case catalogue when it happens; CH41 and CH53 hold the machinery.
- **Fee-shape "tail-first" information inside neg-risk events** (the fee is cheapest at the extremes, so informed
  traders express views in longshot NOs and the favourite lags). L1 and SB2-J5 already screened sibling information
  with weak results; the fee-shape sub-hypothesis is a moderator of those, not a new route.
- **Theta stickiness in single "by date" markets** (YES fails to decay between news). Under correct pricing the
  unconditional drift is zero (the price is a martingale); the conditional decay is the longshot-selling carry CH17/CH60
  already own.
- **Cost-of-capital anchor for decided-outcome carries** (compare CH01's discount with on-chain USDC lending rates).
  CB1-A found 57 units below the floor and a negative A2; a better cost model does not revive a population that small.
- **Two-wave reaction after surprise moves** (informed minutes 0-5, deposit-funded retail minutes 20-60; maker re-quotes
  between). The time profile of adverse selection after large prints is CB3-B's (CH39/CH40) object.
- **Sub-cent queue jumping at the 0.001 tick** (quote at 0.961 to lead the 0.96 queue). pmxt has no order ids, so queue
  position cannot be measured; fill-rate work belongs to CB6-C.
- **Two-book priority across mint and match** (a NO bid competes with YES asks for the same YES bid). A measurement of
  effective queue length, with no route.
- **Smarkets, Betfair, Pinnacle, Metaculus as anchors.** Keys or logins required (round 4's reason for Metaculus holds).
- **Crypto exchange listing announcements (Binance's announcement feed) as a first source for listing markets.** A
  CH28/CH107-type source with a few dozen markets a year and bots already watching the feed for the token price.
- **Weekday-only source classes (weekend hazard is zero).** CH49's mechanism exactly; folded into CH106's calendars.
- **Confirmation-lag NO bias near deadlines** (events that happen but are not "officially confirmed" in time). The text
  class is CB7-S's object (`h8_text`); not separable from specificity without CB7's result.
- **Re-running momentum, reversal, wallet freshness or the identical-pair Kalshi lead with new data.** Excluded by the
  brief; CH113-CH115 touch the lead only through new populations (structural pairs, a third venue, the horizon rule).
- **Order anticipation, spoofing, inducing cancellations, manipulation of any kind, insider identification as a route,
  holding rewards, maker-rebate loops, taker full-set arbitrage, comment sentiment, wash detection as alpha, API quirks,
  Combo RFQ data, Polymarket US.** Rejected in rounds 1-4 for reasons that still hold.

---

## 5. Sources consulted (external; AREPO documents are cited inline by name)

**Keyless probes run for this round (2026-10-17, 19:55-20:05Z; 30 requests; counts, field names, timestamps and rule
words only; no price, outcome, volume or wallet of any market was printed or stored; scripts ran from `/tmp` and wrote
nothing).** All GETs carried `User-Agent: arepo-research-probe` (the EDGAR request added a contact string as the SEC
requires), 40-second timeouts, no key.

| # | Request as sent (host + path + query) | Printed |
|---|---|---|
| 1 | `gamma-api.polymarket.com/markets?active=false&closed=false&limit=100` | status, row count (100), count with `acceptingOrders` (100), count with `events` (100) |
| 2 | `gamma-api.polymarket.com/markets?archived=true&closed=false&limit=100` | same (100 / 100 / 100) |
| 3 | `gamma-api.polymarket.com/markets?closed=true&limit=500&end_date_min=2026-09-08&end_date_max=2026-09-11` | rows (100, page cap), count with `umaResolutionStatuses` (100), status vocabulary counts (`proposed` 156, `resolved` 45) |
| 4-5 | request 1 with `offset=500` and `offset=2000` | rows (100, 100) |
| 6-7 | `gamma-api.polymarket.com/markets?closed=true&limit=100&end_date_min=2026-06-01&end_date_max=2026-06-04`; same for 2026-03-01..03-04 | rows (100, 100), status vocabulary (`proposed` 100 / `resolved` 97; `proposed` 102 / `resolved` 80), markets with more than two entries (0, 0) |
| 8 | `cdn.cboe.com/api/global/delayed_quotes/options/NVDA.json` | status, size (1,878 KB), option count (4,302), expiry tokens (25), first 12 field names |
| 9 | `query2.finance.yahoo.com/v8/finance/chart/NVDA?interval=1h&range=1mo&includePrePost=true` | status, bar count (360), trading-period keys (`post`, `pre`, `regular`) |
| 10 | `query2.finance.yahoo.com/v8/finance/chart/NVDA?interval=1m&range=1d&includePrePost=true` | status, bar count (917) |
| 11-16 | `gamma-api.polymarket.com/public-search?q=<Rotten Tomatoes | App Store | measles | earthquake | Supreme Court | say during>&events_status=closed&limit_per_type=50` | event count, total markets, max members per event (50/358/15; 50/881/26; 35/160/17; 50/198/9; 50/132/32; 50/970/44) |
| 17 | `gamma-api.polymarket.com/public-search?q=Bitcoin%20Up%20or%20Down%2015&events_status=closed&limit_per_type=20` | event count (20), slug patterns with digits masked (`bitcoin-up-or-down-july-#-#pm-et`, `btc-updown-#m-#`), whether a token id was present |
| 18 | `clob.polymarket.com/prices-history?market=<token>&interval=max&fidelity=1` | status, row count (0) |
| 19 | `gamma-api.polymarket.com/public-search?q=Gold%20up%20or%20down&events_status=closed&limit_per_type=5` | booleans for `pyth`, `comex`, `settlement`, `regular trading`, `final minute`, `1-minute`, `21:00`, `4:00 pm`, `5:00 pm` in one description; `endDate` hour (21:00) |
| 20 | `gamma-api.polymarket.com/markets?closed=true&limit=100&end_date_min=2026-09-20&end_date_max=2026-09-23&volume_num_min=5000` | rows (100), counts of questions matching `\b(or|either|any of)\b` (6) and `\b(and|both|all of)\b` (10) |
| 21 | `efts.sec.gov/LATEST/search-index?q=%22chapter%2011%22&forms=8-K&dateRange=custom&startdt=2026-09-01&enddt=2026-09-30` | status, total hits (44) |
| 22 | `www.predictit.org/api/marketdata/all/` | status, market count (207), contract count (635), top-level field names |
| 23 | `api.elections.kalshi.com/trade-api/v2/events?limit=200&status=open&with_nested_markets=true` | events on page (200), events with >= 5 markets by category, cursor present |
| 24 | `site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard` | HTTP 403 |
| 25-26 | `gamma-api.polymarket.com/public-search?q=<bankruptcy | acquisition%20announced>&events_status=closed&limit_per_type=50` | event and market counts (29/62; 4/4) |
| 27-28 | request 17 again (to pick one market's `startDate`/`endDate`), then `clob.polymarket.com/prices-history?market=<token>&startTs=<start-3600>&endTs=<end+3600>&fidelity=1` | slug pattern, life in minutes (1,436), row count (1,438) |
| 29 | `gamma-api.polymarket.com/markets?active=false&closed=false&limit=100&volume_num_min=1000` | rows (100), `endDate` year counts (2028: 98, 2027: 2) |
| 30 | request 17 again, restricted to `btc-updown-15m` slugs | slug and question patterns with digits masked, `createdAt` 09:36, `startDate` 09:38, `endDate` 09:45 (HH:MM Z), rule-word booleans (`chainlink` true, `begin` true, `equal` true, `window`/`start`/`binance` false), fee fields present |

**External documents.**
- CBOE delayed quotes JSON (public, 15-minute delayed option chains): https://cdn.cboe.com/api/global/delayed_quotes/options/
  (probed; CH99).
- Yahoo Finance chart endpoint (unofficial, keyless; `includePrePost`, `interval`, `range`): as probed (CH100, CH101).
- USGS FDSN Event Web Service (keyless earthquake catalogue): https://earthquake.usgs.gov/fdsnws/event/1/ (CH108; not
  probed today).
- CDC measles cases and outbreaks (weekly public table): https://www.cdc.gov/measles/data-research/ (CH108; not probed).
- Apple top-charts RSS (keyless): https://rss.marketingtools.apple.com/ (CH108; not probed).
- SEC EDGAR full-text search (keyless, user agent required): https://efts.sec.gov/LATEST/search-index and
  https://www.sec.gov/edgar/search/ (probed; CH107).
- Federal Register public-inspection API (keyless): https://www.federalregister.gov/developers/documentation/api/v1
  (CH106; not probed).
- Supreme Court of the United States, calendars and opinions: https://www.supremecourt.gov/ (CH106; not probed).
- US Senate executive calendar and cloture motions: https://www.senate.gov/legislative/ (CH106; not probed).
- PredictIt market data API (keyless, 60-second cadence, fee schedule): https://www.predictit.org/api/marketdata/all/
  and https://www.predictit.org/support/how-to-trade-on-predictit (probed; CH114).
- Kalshi trade API v2 (keyless market data; nested events): https://trading-api.readme.io/reference (probed; CH113).
- UMA Data Verification Mechanism (VotingV2 commit/reveal, Ethereum mainnet) and Optimistic Oracle events:
  https://docs.uma.xyz/ (CH104; not probed).
- Polymarket docs cited in rounds 1-4 and still used here: fees (`rate*p*(1-p)`, maker 0, rebates), liquidity rewards
  (size-cutoff-adjusted midpoint, `rewards_max_spread`, `rewards_min_size`), CLOB orders and `prices-history`, negative
  risk, UMA resolution: https://docs.polymarket.com/trading/fees,
  https://docs.polymarket.com/developers/market-makers/liquidity-rewards,
  https://docs.polymarket.com/developers/CLOB/orders/orders, https://docs.polymarket.com/developers/neg-risk/overview,
  https://docs.polymarket.com/developers/resolution/UMA.
- Tversky and Kahneman (1983), "Extensional versus intuitive reasoning: the conjunction fallacy", Psychological Review;
  Bar-Hillel and Neter (1993), "How alike is it versus how likely is it: a disjunction fallacy", Journal of Personality
  and Social Psychology (CH117).
- Gutenberg and Richter (1944) frequency-magnitude relation; Reasenberg (1985) declustering (CH108's earthquake prior).
- Dubach (arXiv:2604.24366), Nechepurenko (arXiv:2605.11640), Le (arXiv:2602.19520), Cardozo and Rivero-Wildemauwe
  (arXiv:2609.12878), Page and Clemen (2013): as cited in rounds 1 and 4 (context for families F and E).
