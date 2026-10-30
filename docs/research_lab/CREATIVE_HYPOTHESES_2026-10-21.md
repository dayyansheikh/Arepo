# Creative hypotheses, round 7: where money could come from on Polymarket (2026-10-21)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-19 05:30 UTC+1,
2026-10-19T04:30Z; the file carries the round's planned date). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md`
(CH01-CH34), round 2 `CREATIVE_HYPOTHESES_2026-10-16.md` (CH35-CH59), round 3 `CREATIVE_HYPOTHESES_2026-10-17.md`
(CH60-CH78), round 4 `CREATIVE_HYPOTHESES_2026-10-18.md` (CH79-CH98), round 5 `CREATIVE_HYPOTHESES_2026-10-19.md`
(CH99-CH117), round 6 `CREATIVE_HYPOTHESES_2026-10-20.md` (CH118-CH130); this file starts at **CH131** and repeats
none of them. Where an idea builds on an earlier one, the parent is named and the new mechanism, clock or data source
is stated. Every number quoted from an AREPO document is a development or screen result, not evidence. One file; no
code, no queue specs, no other commits.

## 0. How to read this file

**What changed since round 6 (18-19 Oct drafts, smokes, one null).**
- **CB12-X is closed with a null that teaches.** X1 (do cross-venue gaps decay more slowly at long horizons?) had a
  clean-looking contrast (half-lives 49 / 70 / 140 min, event-way p 0.003) and **the horizon-offset placebo advanced in
  16% of draws against 1.5% allowed**; the top-5 event and top-5 month drops failed too. Composition explained the
  contrast as well as the hypothesis did. Every idea below therefore carries a *within-unit* contrast (same event, same
  underlying, same market over time) or a composition placebo as its primary design, not as a robustness line.
- **CB13 (CH128 as CB13-T maker toxicity by resolution class, host files only; CH118 as CB13-R barrier-versus-terminal
  on 3,948 closed crypto barrier markets in 501 events) is DRAFT-REVISED with a REVISE freeze check (22 defects being
  fixed).** CH119 was deferred because its census fails (about 74 eligible markets after CB2-W and CB12-E keys).
  **CB14 (CH123 as CB14-W edit bursts; CH121 as CB14-S intra-speech decay) is DRAFT-REVISED.** CH127 was deferred (the
  "opening weekend" population is mostly AMM-era, where minute history is unusable). CB11's smoke passed (q0220) and
  its data chain holds the `net` lane; CB12's M smoke v2 passed. **None of CB1-CB14 has a positive verdict on any
  hypothesis.** The cumulative counted-trial number is **1,231** (`by_triage`, 2026-10-19); every test here joins it.
- **Three round-6 premises were corrected by CB13's probes** and bind this round: (1) no Binance archive exists on the
  host (CB8-B's q0165 never ran; CB13-R fetches its own); (2) **the 2 h capture rows carry no question text and no
  `resolutionSource`, `automaticallyResolved`, `secondsDelay` or `gameStartTime`**, while every live-monitor print
  carries `title` and `slug` and the sidecar carries `fee_type`, `fee_category`, `series_slugs`, `created_at`,
  `order_price_min_tick_size` and `rewards_*`; the 2026-10-12 `cross_venue/poly_markets.json` pull (148,384 closed
  markets with questions) is on the host for field-restricted text censuses; (3) the monitor's alerts are the five
  frozen `uf_*` rules, not `sm_learned`.
- **The binding facts are unchanged.** E007 flow continuation Supported but about +0.36c against about 4.5c round
  trip; **0 of 95 economic cells positive after cost**; maker cells -0.2 to -2.6c even with a free exit; SB2 J2 net
  taker about -2.5c; T5 nothing beats recalibrated price; wallet effects null; CB1-A2 decided carry net -1.05c on
  `h2_main`; CB1-D neg-risk asymmetry +0.78 pp under its 1 pp floor; CB4-N 1.29 eligible events an hour; CB5-L 0 CDF
  families; CB12-X not identifiable. The Kalshi 10-20 minute lead is still the only replicated predictor and is sealed
  in E009/E010 to 2026-11-03. Wikipedia pageviews publish 48-69 h late. **The lesson of every batch stands: count the
  population before the hypothesis** (two candidates died in this round's probes, §4).

**Structural facts from this round's probes (keyless, 2026-10-19 04:05-04:20Z, 37 requests; counts, field names,
end-year histograms and title-word booleans only; no price, outcome, volume or wallet of any market was printed or
stored; every request is listed in §5).**
1. **Neg-risk events do not take late entrants.** Of 200 open events with volume >= $10k, 82 are neg-risk with >= 5
   members, and in **0 of 82** do the members' `createdAt` span more than 7 days (1,559 members, 0 created more than
   7 days after the first). The "late-entrant overshoot" candidate is dead (§4).
2. **Series are launched at a rate of about 50 a month.** Gamma `/series` (fields include `createdAt`, `recurrence`,
   `seriesType`, `competitive`, `volume24hr`) ordered by `createdAt` descending puts rows 100-149 in 2026-08 (40) and
   2026-09 (10): **more than 150 series were created since August 2026** (§CH142).
3. **Kalshi's settled market object is a public, timestamped decider:** `result`, `settlement_ts`,
   `settlement_value_dollars`, `expiration_time`, `latest_expiration_time`, `status` (44 fields; names only) (§CH134).
4. **Scheduled-statistic bucket ladders are a large, clustered population.** Closed capped searches: "CPI" 50 events /
   388 markets (48 neg-risk), "GDP" 50 / 332 (44), "unemployment rate" 50 / 391 (37), "payrolls" 21 / 169 (16), "Fed
   decision" 47 / 250 (42); 12-25 members per event (§CH139).
5. **Crypto barrier ladders list reach and dip rungs in the same weekly event** (CB13 probe 11: 21 members, "reach $X"
   and "dip to $Y" templates, Binance 1-minute highs and lows, `negRisk` false): a within-event paired contrast exists
   (§CH138). 3,948 such markets in 501 events in the 2026-10-12 pull (CB13 H10); "dip to" 835 and "reach" 283 markets
   in round 6's capped searches.
6. **Statutory-clock classes:** "ETF" 50 closed events / 50 single markets (2025: 25, 2026: 23); "FDA" 50 / 106 (38
   titles say "approve"); "acquisition" 50 / 279; "merger" 23 / 54; "signed into law" 8 / 14; "downgrade" 10 / 29. The
   Federal Register API is keyless (HTTP 200; 5,323 documents for the 19b-4 exchange-traded term); GovInfo's
   BILLSTATUS bulk data is keyless (200) (§CH135).
7. **Non-US election nights are many:** "parliamentary election" 50 closed events / 1,213 markets (41 events end in
   2026), "presidential election" 50 / 957 (2024: 24, 2026: 14); "election" titles name Brazil, Argentina, Chile,
   Israel, Portugal, Bulgaria, Georgia and Mexico in the first 50 (§CH136).
8. **Launch markets:** "SpaceX" 50 closed events / 308 markets (2025: 11, 2026: 19; 20 titles name Starship), "Starship"
   37 / 178 (21 events end 2024 or later). The FAA TFR list is keyless (200); the 45th Weather Squadron's forecast page
   returned 403 to the probe user agent (§CH137).
9. **Central banks other than the Fed:** "ECB" 23 closed events / 81 markets, "Bank of England" 16 / 54, "Bank of
   Japan" 12 / 46, "rate decision" 50 / 186 (all 2026, all neg-risk), "interest rate" 50 / 350. The Bank of England's
   daily OIS curve archive is keyless (HTTP 200 on the zip); the ECB data API was not reachable from the probe
   (URLError; unverified, not refused) (§CH140).
10. **Mortality markets exist in bulk:** "die" 50 closed events / 959 markets (21 titles contain "die"; one event has 66
    members) (§CH141).
11. **Host stores relevant here (from CB13's read-only probes H1-H8):** monitor prints 7,000-13,600 a day across
    1,400-2,700 markets since 2026-10-12T01:30Z, 35 keys including `ts`, `recv_ts`, `price`, `size`, `cash`, `title`,
    `slug`, `ctx_*`; 38,115 prints in the four SCREEN days (70% sports); book sweeps with `best_bid`, `best_ask`,
    `bid_size_1`, `ask_size_1`, `depth_*_1c`, `depth_*_5c`, `n_bid_levels`, `n_ask_levels` (54,080 token rows per
    pass, a sample of tokens); 95 capture dirs 10-10..10-18; the audited 316-pair history (183 events) and the 958
    matched pairs (688 sports) of the cross-venue study; the E009/E010 stream (Kalshi `yes_bid/ask` with
    `yes_bid_size_fp` / `yes_ask_size_fp`, Polymarket `/books` levels, 120 s, up to 200 pairs), sealed to 11-03.
12. **Trade samples already compute `time_since_last_trade_s`** (`trade_sample.py`), which bounds the novelty of
    §CH132 (its prior-work check is a kill criterion).

**The reading that steers this round.** Round 6 hunted public clocks that run during the event, change detection on
named sources, model-anchored classes and the maker's class map. What is still unhunted:
- **(a) Who is resting and who is arriving, read without wallets** (family A): the grain and shape of resting quotes
  say whether a bot or a person is on the book; the silence before a print says whether the arrival had a reason; the
  120 s book stream says whether makers withdraw before moves. The maker's loss has an address in *time and type*,
  not only in class (CB13-T).
- **(b) External deciders and external clocks** (family B): Kalshi's settlement stamp, statutory deadlines, official
  count feeds and launch notices are public facts that settle or time a Polymarket question before the venue reprices.
- **(c) Risk premia the crowd pays** (family C): the insurance skew and the pre-announcement lottery premium are the two
  best-documented premia in option markets; neither has been looked for on this venue.
- **(d) Professional anchors in classes nobody has joined** (family D): OIS curves for non-Fed banks; life tables.
- **(e) Maps that tell the other families where to go** (family E): new series' first weeks; classes without a Kalshi
  twin. Everything is wallet-free and side-free; nothing reads the Data API `side` field.

**Data labels.** `A` = in AREPO's stores now: complete-universe 2 h captures (touch, Gamma mid, `oneHourPriceChange`,
`last_trade_price`, `volume24hr`, `liquidity`, neg-risk ids, `closed`, `endDate`, `createdAt`; **no question text**)
with the sidecar since 11 Oct 12:00Z (`accepting_orders`, `competitive`, `clob_rewards`, `rewards_max_spread`,
`rewards_min_size`, `fee_schedule`, `fee_type`, `fee_category`, `uma_resolution_statuses`, `series_slugs`,
`parent_event_ids`, `order_price_min_tick_size`); book sweeps twice per pass; trade samples (hashed wallets, never
used here); the live large-trade monitor (prints >= $1k every 5 min with receipt and venue times, `title`, `slug`,
Gamma context); the CB3 quote-state extracts; the audited cross-venue pair history (316 clean pairs, 10-minute) and the
958-pair matcher output; the 2026-10-12 `poly_markets.json` pull (questions, field-restricted reads only); the IF-H2
ladder metadata. `P` = collectable read-only from public keyless sources within a week (Gamma `description` and
`/series`, Data API `/trades`, CLOB `prices-history` with explicit bounds and `/book`, Kalshi market objects, the Bank
of England OIS archive, the Federal Register API, GovInfo BILLSTATUS, the FAA TFR list, official election-count feeds,
data.binance.vision klines, SSA and ONS life tables). `N` = no known keyless source. **Sealed and not usable by
anything here:** everything rounds 4-6 list (`h4_seal`, `h5_*`, `h6_weather`, `h7_cb4_*`, `h8_*`, the `h9_flow`
HOLDOUT, CB8-B and CB8-H windows, CB1-D's replication captures, the E009/E010 stream to 2026-11-03, E011 labels to
2026-11-11, the J4-R window, CB9's HOLDOUTs and Pyth frame, CB10's `h10_brk` and `h10_dlad`, every `h10_*`, `h11_*`,
`h12_*`) **plus** CB13's `h13_touch` / `h13_binance` HOLDOUT months (ends >= 2026-04-01) and T HOLDOUT window
`[2026-10-21, 2026-10-26)`, and CB14's `h14_wiki`, `h14_speech`, `h14_wiki_live`. `h2_main` is worn and `h3_power`
retired. Every historical test below names a **fresh** fetch (`h15_*`), disjoint by market id *and* event / neg-risk /
series key from every prior sample and seal copy, with rows before `T_hist_end` 2026-10-01 or collected prospectively;
none is bound to the 2026-10-22 `T_seal` lane, and none runs ahead of any CB11-CB14 job. Where an idea reuses a CB13
or CB14 frame it says so and takes the L1 label.

**Hygiene that binds every idea.** Trade before `t`; scheduled anchors and source issuance times, never `closedTime`
and never the market's own move; outcomes that are public functions of public data are computed from the public data,
never read from Gamma's outcome fields (CB9-P's guard); event x resolution-week clustering for carries, session-day
or release clustering for scheduled objects, night / campaign / person clustering where those are the units; tightness
at both ends of any mid-based target (J4-R) and print-based targets where prints exist; rule text as of first sighting
or the clarification-marker exclusion; the cumulative test count (M3); frozen models fitted on data before a stated
date and tested after it; **a composition placebo (within-unit shuffle or relabelling) is primary, not secondary**
(the CB12-X lesson). Category stays a parameter (sports scope is the user's call; nothing here is sports-only).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = an afternoon on existing data or a small
keyless fetch, 5 = new collector plus weeks). My judgement, not measurements. Cost conventions as rounds 1-6: taker fee
`rate*p*(1-p)` per leg (crypto 0.07; sports 0.03-0.05; politics/finance/tech 0.04; economics/culture/weather 0.05;
geopolitics 0; makers 0, rebate 15-25% of the fee-equivalent of own fills); median spreads by price band
4.1 / 3.0 / 2.2 / 3.0 / 2.5c; liquid (>= $100k) round trip 1.8c; median round trip 4.5c; one-leg hold-to-resolution
pays the half-spread and the fee once; passive entry has paid 1-7c of adverse selection in every study so far.

**Counts table (what was counted before each idea was written).**

| ID | Population | Count | Source |
|---|---|---|---|
| CH131 | monitor prints with a capture or sweep touch; resting-quote grain and shape | 38,115 prints in 4 days, 6,042 markets; 54,080 sweep token rows per pass; 261 of 300 liquid markets at 0.001 tick | CB13 H6-H8; round 6 fact 8 (`A`) |
| CH132 | monitor prints with a measurable preceding silence | 7,000-13,600 prints a day, 1,400-2,700 markets | CB13 H2-H3 (`A`) |
| CH133 | pairs polled at 120 s with sizes on both venues | up to 200 pairs since 2026-10-12 | E009 design (`A`, sealed to 11-03) |
| CH134 | audited pairs with a Kalshi settlement before Polymarket's close | 316 clean pairs / 183 events; 958 matched; share with Kalshi-first settlement unknown (census) | cross-venue study (`A`); Kalshi fields (probe 24) |
| CH135 | statutory-clock markets | ETF 50 / 50; FDA 50 / 106; acquisition 50 / 279; merger 23 / 54; signed into law 8 / 14; downgrade 10 / 29 (capped) | probes 7-11, 36 |
| CH136 | non-US election nights with markets | parliamentary 50 / 1,213 (41 end in 2026); presidential 50 / 957 | probes 18-19 |
| CH137 | launch campaigns with markets | SpaceX 50 / 308; Starship 37 / 178 (21 events 2024+) | probes 2, 32 |
| CH138 | barrier rungs, reach and dip in one event | 3,948 markets / 501 events (2026-10-12 pull); more before 2025-10 | CB13 H10 and probes 2-4 |
| CH139 | scheduled-statistic bucket ladders | CPI 50 / 388; GDP 50 / 332; unemployment 50 / 391; payrolls 21 / 169; Fed 47 / 250 (capped) | probes 12-16 |
| CH140 | non-Fed central-bank decision events | ECB 23 / 81; BoE 16 / 54; BoJ 12 / 46; "rate decision" 50 / 186 | probes 3-6, 34 |
| CH141 | mortality markets | "die" 50 / 959; 21 titles | probe 35 |
| CH142 | series launched since August 2026 | > 150 | probes 22-23 |
| CH143 | markets with / without a Kalshi twin | 958 matched pairs among about 274,000 capture rows | cross-venue study; CB13 H4 (`A`) |
| rejected | neg-risk late entrants | 0 of 82 events | probes 20-21 |

---

## 1. Map: where money might be, given the survivors and the nulls

| Family | What the evidence and the probes suggest | Money route |
|---|---|---|
| A. Who is resting, who is arriving | the maker's loss (the number that blocked every route) is measured as an average over quoter types and arrival times; grain, shape, silence and withdrawal are all on the host | maker protection: quote only where the resting crowd is human and the arrival is noise; step aside on wake-ups and fades |
| B. External deciders and clocks | Kalshi settles hours to days before UMA; statutes fix decision days; official counts cross decisive thresholds before wire calls; launch notices precede launches | taker at stale asks after a public decider or clock; decided carry with an external label |
| C. Risk premia the crowd pays | insurance skew and pre-announcement lottery premia are robust in option markets and untested here; barrier events pair reach and dip rungs; releases cluster cleanly | sell insurance at the recorded ask (maker or taker NO) inside a tail gate; within-event contrasts |
| D. Anchors in unjoined classes | OIS curves and life tables are public probabilistic anchors for classes no batch has touched | hold-to-resolution taker on the anchor side when the gap clears fee plus spread |
| E. Maps | new series are born at 50 a month; classes without a Kalshi twin have no professional arbitrage channel | tells families A-D *when* and *where* to look first |

---

## 2. Hypotheses

### A. Who is resting and who is arriving (parents CH128/CB13-T, CH39, CH43, CH80, CH111; E003 is the sealed neighbour)

**CH131. Quoter-type footprint: the grain (sub-cent versus whole-cent price) and shape (level count, size uniformity,
1c-to-5c depth ratio) of the resting side of the book classify the resting quoter as a bot or a person without any
wallet; prints that lift human-grain, lumpy quotes are pick-offs (large continuation, the maker's loss), while prints
that lift bot-grain, uniform ladders carry little continuation (the taker paid the bot's model); so the maker's
adverse selection, and therefore the only place a maker can net positive, is a function of *who else is resting*, and
the taker's break-even is reachable only against human-grain books.**
- Mechanism and who pays: 261 of 300 liquid open markets quote on a 0.001 tick (round 6 fact 8). Reward bots and
  model makers quote at the finest grain and in uniform ladders (equal sizes at consecutive levels, flat 1c-to-5c depth
  ratios); people type whole cents and leave single lumpy orders. A person's resting order is stale by construction
  (no re-quote loop), so it is the order that informed takers lift; a bot's is fresh. The 95 economic cells and SB2-J2
  pooled both. Why the crowd misses it: nobody on the venue reads the book's grain; the UI shows one price.
- Population and count: the monitor's prints (38,115 in four SCREEN days, 6,042 markets; 7,000-13,600 a day since)
  joined to the latest book sweep of the token (sweeps carry `best_bid`, `best_ask`, `bid_size_1`, `ask_size_1`,
  `depth_*_1c`, `depth_*_5c`, `n_*_levels`; CB13 H7 found sweeps missing for about half of sports and most crypto
  prints, so the primary arm uses the **capture touch's grain** (the touch price's third decimal) and the sweep arm is
  secondary where present). Expect 10,000-20,000 classified prints a week outside sports.
- Test (`A`, historical on host files; within-market). Decision time: the print's venue `ts`. Resting class at the
  print: grain of the touch the print crossed (sub-cent / whole-cent; markets with 0.01 tick excluded from the grain
  arm) and shape from the sweep (uniformity = coefficient of variation of the top-3 level sizes; depth ratio
  `depth_5c / depth_1c`). Target: print-based 2 h and 6 h mark-out in the print's direction read from touch-consistent
  prices (CB13-T's side-free rule), and the next captures' mid as the mid-based secondary with J4-R tightness.
  Statistic: **within-market** difference of mean mark-out between human-grain and bot-grain prints (markets that have
  both kinds in the window), pooled across markets with event x day clustering and an hour-of-day way; floors: 0.5c on
  the difference; the sign condition (human-grain mark-out worse for the maker). Placebo: shuffle the grain label
  within market and hour. Clustering: event x day, two-way with hour-of-day.
- Economic route: maker protection first (the maker's net by resting-class of the *rest of the book*: a paper quote
  posted beside bots versus beside people); taker second (buy at human-grain asks when an anchor from another family
  disagrees by >= fee + spread; reported only in classes where the maker arm shows pick-offs >= 1c).
- Data source and cost: `A` only; an afternoon once CB13-T's fill table exists (the same prints, two more columns).
  No fetch. C 1.
- Kill criteria: the touch's third decimal is 0 in > 95% of 0.001-tick markets (people and bots both quote on cents;
  the grain arm is uninformative; only the shape arm remains); or the within-market difference < 0.5c; or the
  within-market placebo advances; or the sweep coverage leaves < 500 shape-classified non-sports prints.
- Leakage/confound: the capture touch is up to 2 h old (CB13-T's staleness guard applies; the sweep arm is the clean
  one where present); bots also quote whole cents in 0.01-tick markets (excluded); a sub-cent touch can be a person
  who typed 0.555 (the shape arm disambiguates); sports is 70% of prints and stays a parameter.
- Novelty: CH128/CB13-T classes markets by *resolution*; CH80 is dust at the touch; CH111 is the taker's size shape;
  CH39 the post-print retreat. New: the *resting quoter's* grain and shape as the maker's state variable. N 4, EV 3,
  C 1.

**CH132. Wake-up prints: the first >= $1k print after a long silence in a market (no print for >= 12 h, scaled to the
market's own inter-arrival distribution) carries more information than a print of the same size in an active market,
because the arrival had a reason; its print-based 2-6 h continuation is larger, and the maker's fill on it is the
worst fill of the day. Side-free, wallet-free, host-only.**
- Mechanism and who pays: in a dead book the resting quotes are the oldest on the venue; the taker who wakes the
  market read something (a wire, a filing, a sibling market). Who pays: whoever is resting. Why the crowd misses it:
  the arrival is one print in a market nobody watches; the venue's attention tools rank by volume, not by silence.
- Population and count: monitor prints (7,000-13,600 a day across 1,400-2,700 markets); silence measured on the
  monitor's own stream (>= $1k prints) and, as the robust arm, on the trade samples' all-size prints at the market's
  last sampled origin. Expect several hundred wake-up prints a week outside sports.
- Test (`A`, host files; within-market). Decision time: the print's venue `ts`. State: silence `s` = time since the
  previous print in the market, standardised by the market's median inter-arrival over the prior 7 days (so a
  "wake-up" is a print at the 90th percentile of its own market's gaps, not a fixed 12 h). Target: print-based 2 h and
  6 h continuation in the print's direction (touch-consistent side); the capture-mid secondary with J4-R tightness.
  Statistic: slope of the continuation on standardised log-silence within market (markets with >= 5 prints in the
  window), pooled with event x day clustering; floor 0.5c per silence-SD; placebo: shuffle silence within market.
  Clustering: event x day, two-way with hour-of-day.
- Economic route: maker protection (widen or pull after a wake-up print: the paper maker's net on the fills that
  follow a wake-up versus the market's other fills); the taker follow is reported at recorded prints and is expected
  to fail the 4.5c round trip (E007's lesson) unless the slope is > 3c per SD.
- Data source and cost: `A` only; an afternoon on the monitor files and the trade samples' `time_since_last_trade_s`.
  C 1.
- Kill criteria: **prior-work check first:** if HB1/HB2 or the flow screen already used `time_since_last_trade_s` as
  the conditioning variable of a print's mark-out (not merely as a feature in a pooled model), this is a re-run and
  dies before any read; or the slope < 0.5c per SD; or the within-market placebo advances; or the 2 h capture cadence
  makes the print-based and mid-based targets disagree in sign in > 30% of units.
- Leakage/confound: the monitor sees only >= $1k prints (silence on that stream is not market silence; the trade
  samples arm is the check); the first print after listing is a genesis event (CH22), excluded; sibling-market
  resolutions wake several markets at once (an event-day cluster, not a leak).
- Novelty: CH43 is a volatility filter; CH39 is size-relative post-print retreat; E011 is volatility-driven surprise.
  New: the market's own inter-arrival clock as the arrival's information content. N 3, EV 2-3, C 1.

**CH133. Depth fade at 120 s: in the cross-venue stream (Polymarket `/books` and Kalshi sizes every 120 s for up to
200 pairs), the size at Polymarket's touch on one side shrinks over two or three polls before a Polymarket mid move in
that direction, *without* a prior Kalshi move; the fade is makers withdrawing on information or on their own anchors,
it is visible to anyone reading the book, and it precedes the move by 2-6 minutes.**
- Mechanism and who pays: a maker who learns something cancels before re-quoting; the cancellation is the first public
  trace and costs nothing to observe. Who pays: takers who hit the remaining size and the slower makers. Why the
  crowd misses it: the lead is minutes and the object is a size, not a price; the UI shows depth only in a chart.
- Population and count: up to 200 pairs polled at 120 s since 2026-10-12 (sports-heavy by construction of the pair
  list); tens of thousands of poll steps a day. **Sealed to 2026-11-03 (E009/E010).**
- Test (`A`, after the E009/E010 analyses are committed; the same stream is then a worn set, L1; prospective
  continuation if the poller keeps running). Decision time: poll `t`. State: fade = `size_touch(t) / median size over
  [t - 30 min, t - 6 min]` on each side, computed only when Kalshi's mid changed by < 1c over the last 20 minutes (the
  sealed lead is excluded by construction). Target: Polymarket mid change over the next 10 and 20 minutes (J4-R
  tightness at both ends; both venues' quotes are receipt-timed). Statistic: slope of the signed next-10-minute move on
  the signed fade (ask fade -> up); placebo: shuffle the fade series within pair and hour; clusters: pair-day (two-way
  with 10-minute bucket of the day). Floors: 0.5c per fade-SD; the slope must hold with Kalshi-quiet filters at 1c and
  0.5c.
- Economic route: maker protection (pull or widen on the faded side; the paper maker's avoided-fill mark-out as in
  CH73/CB7-X); the taker follow pays the spread and is reported only.
- Data source and cost: `A` (host stream) after mid-November; a day of code. No fetch. C 1-2.
- Kill criteria: slope CI includes 0 or point < 0.5c per SD; or the effect vanishes when Kalshi-quiet is tightened to
  0.5c (then it is the sealed lead in disguise); or the within-pair placebo advances; or `/books` levels in the stream
  hold only the touch size with no history to normalise on (then the state is undefined; a design note, not a result).
- Leakage/confound: the stream's pair list is sports-heavy (category is a parameter; sports reported separately);
  bots cancel on their own heartbeat (the within-pair normalisation and the hour way absorb regular cancellations);
  the 120 s cadence undersamples fades shorter than 4 minutes (a loss of power, not a bias).
- Novelty: E003 (top-of-book imbalance and microprice, inconclusive, R2 about 0) is the *level* of imbalance at a
  point in time; CH116 strips the reward band; CH35-CH38 are vacuums (one side vanishing). New: the *rate of
  withdrawal* at 120 s, conditioned on the anchor venue being quiet. N 3, EV 3, C 1-2.

### B. External deciders and external clocks (parents CH01/CB1-A, CH106, CH120, CH129, CH130)

**CH134. Kalshi-settlement-labelled decided carry: when a Kalshi twin has settled (`settlement_ts`, `result`) and the
Polymarket market is still accepting orders at an ask below 1.00 for the Kalshi-result side, the position is decided by
an external, public, timestamped label, not by the market's own price; the carry to UMA resolution is a public wait
(CB11-W's object) and the only risk is a rule divergence the matcher audit can see.**
- Mechanism and who pays: Kalshi settles most contracts within hours of the determining event (`settlement_timer_seconds`
  is a field); Polymarket waits for a UMA proposal, the 2 h liveness and, often, days (CB11 found 307,658 markets closed
  after their scheduled end). In that window Polymarket's decided side trades at 0.97-0.995 because holders want cash
  and nobody wants to lock capital. Who pays: the sellers of the decided side. Why the crowd misses it: the label is on
  another venue and the gross is cents.
- Population and count: the 316 audited clean pairs (183 events) and the 958 matched pairs (688 sports) of the
  cross-venue study; the share where Kalshi settles *before* Polymarket's `closedTime` is unknown and is the census
  (expected high for sports and scheduled events, low for "by date" questions where Kalshi may wait too). Floor 60
  Kalshi-first pairs in 40 events.
- Test (`A` + `P`, historical). Decision time: `settlement_ts` + 10 minutes (Kalshi's own stamp; never Polymarket's
  move). Target: Polymarket's resolution for the Kalshi-result side (Gamma's resolution is the outcome here, since it
  is not a public function of other data) and the wait `closedTime − settlement_ts`. Statistic: mean net per share of
  buying the Kalshi-result side at the first recorded Polymarket ask after the decision time (Data API prints as the
  executable-price record; CLOB `prices-history` 1-minute as the cross-check), paying the fee once, receiving 1 at
  resolution; the **wrong-side rate** (Polymarket resolves against Kalshi) as a separate counted number with a Wilson
  upper bound; annualised rate from the wait. Clustering: event (and resolution week). Floors: net >= +0.5c per share
  after the realised wrong-side losses; wrong-side upper bound <= 0.5% (one wrong pair at 99c costs 200 right ones);
  median wait <= 72 h.
- Economic route: taker buy of the decided side at the recorded ask; capacity is the ask depth ($1-10k per market);
  the fee at p 0.99 is about 0.04c; the gross is the ask discount (0.5-3c). The honest prior is CB1-A2: decided carry
  by the market's *own* price netted -1.05c on `h2_main` (p 0.912), and the external label changes selection, not the
  ask discount.
- Data source and cost: `A` (pair history, captures for `accepting_orders`), `P` (one Kalshi market read per pair,
  one `prices-history` and one prints read per pair: about 1,000 requests). An afternoon after the census. C 1-2.
- Kill criteria: census < 60 Kalshi-first pairs; or the wrong-side upper bound > 0.5% on the audited set (the
  cross-venue study's post-hoc diagnostic found 929 of 946 matched pairs agreeing, 98.2%, *before* the audit; the
  audited set must do far better or the idea is dead); or net <= 0.5c; or the median wait > 72 h with the net below
  1c (capital lock makes the annualised number meaningless).
- Leakage/confound: pairs whose rules differ (CH64's twins) are excluded at the matcher audit, never after seeing the
  resolution; Kalshi's `is_provisional` settlements can be revised (take `settlement_ts` of the final record only, and
  count revisions); the sealed E009/E010 window is untouched (the pair history is the historical study's).
- Novelty: CH01/CB1-A used the market's own price as the decided label; CH130 is the pair at birth; CB11-W predicts
  the wait. New: an external, timestamped decider as the label, and the wrong-side rate as a counted quantity. N 3,
  EV 3, C 1-2.

**CH135. Statutory-deadline clocks: for questions decided by a regulator or officer under a legally fixed clock (SEC
19b-4 final deadlines of 240 days from Federal Register publication; EU merger Phase 1 at 25 working days; FDA PDUFA
goal dates; the ten-day presentment window; CRA sovereign review calendars), the decision lands on or within days of
the final deadline far more often than the crowd's "by <earlier date>" prices imply, so intermediate rungs are
overpriced and the final-deadline rung is fairly priced.**
- Mechanism and who pays: the deciders use the whole clock (the SEC delayed crypto ETP orders to the final deadline in
  nearly every 2021-2024 case; Phase 1 decisions cluster on the last working day; PDUFA actions arrive on the goal
  date). Who pays: buyers of "approved by <month>" rungs ahead of the deadline, priced on headline optimism. Why it
  persists: the clock is in a Federal Register notice or a case file, not in the market's rule; each class is small on
  its own, so nobody builds the calendar.
- Population and count: closed "ETF" 50 events / 50 markets (2025: 25, 2026: 23), "FDA" 50 / 106 (38 "approve"),
  "acquisition" 50 / 279, "merger" 23 / 54, "signed into law" 8 / 14, "downgrade" 10 / 29 (capped searches). Keyless
  archives verified: the Federal Register API (200; 5,323 documents for the 19b-4 ETP term) and GovInfo BILLSTATUS
  (200); EC merger case pages and FDA goal dates are public HTML (not probed). The number of markets with an
  *intermediate* rung is the census; floor 40 filings.
- Test (`P`, historical, pooled across classes with class effects). Decision time: listing + 24 h and `D_m − 14 d`
  (`D_m` the market's deadline). Target: the decision date from the public source (SEC order date in the FR; EC
  decision date; FDA approval letter date; presentment and signature dates in BILLSTATUS), never Gamma's field.
  Anchor `q`: a frozen per-class base rate of "decision before `D_m` given the final deadline `D_f`" fitted on
  2019-2024 cases from the archives (before any market is read). Statistic: slope of `(Y − p)` on `(q − p)` with the
  J4-R tightness filter and a sign-shuffle placebo; clusters = filing / case (and class as the outer layer). Floors:
  0.30 on the slope; 1.0c on the net.
- Economic route: buy NO on intermediate rungs at the recorded ask when `p − q >= 5c`, hold to `D_m` (a few weeks);
  fee `0.04-0.05*p*(1-p)` <= 1.25c; spreads 3-4c; capacity $1-10k per rung.
- Data source and cost: `P` (Gamma texts for the frame; FR API; GovInfo; case pages; CLOB history). Two afternoons
  plus the base-rate tables. C 2.
- Kill criteria: < 40 filings with an intermediate rung; or the crowd already prices the clock (mean `p − q` < 3c);
  or slope < 0.30; or the base rates are unstable across years (then no `q` is frozen honestly). **Regime note:** the
  SEC's generic listing standards (September 2025) remove the 19b-4 clock for most crypto ETPs going forward, so the SEC
  arm is historical and the prospective arm is EC / FDA / presentment.
- Leakage/confound: the market's deadline may be the final deadline itself (no rung; excluded); withdrawals and
  refilings restart clocks (take the clock from the notice that the rule names); earnings-type early approvals exist in
  the FDA class (the base rate carries them); few clusters in the presentment and CRA arms (reported, uncounted below
  20 cases).
- Novelty: CH106 (public hazard calendars) says which *days* are possible; CB12 dropped it for lack of a verified
  archive. New: the *deadline-day* base rate as the anchor, and two verified keyless archives. N 3, EV 3, C 2.

**CH136. Official-count clocks in non-US election nights: the official count feed crosses a "cannot be overtaken"
bound (leader's margin greater than the maximum remaining votes, computed from the feed's own progression) minutes to
hours before wire calls, and Polymarket's seat and winner markets, thin at 02:00-06:00Z, reprice after the call;
unlike CH129 this needs no reporting-order model and repeats dozens of times a year.**
- Mechanism and who pays: electoral authorities publish running totals in machine-readable form (Brazil's TSE,
  Argentina's national count, Germany's federal returning officer, Chile's Servel and others publish JSON or CSV
  updates every few minutes; the URLs vary per country and are verified before each night). A conservative bound uses
  only the published counted and registered totals. Who pays: holders selling into the first visible move and makers
  whose asks stay below 0.9 after the bound is crossed. Why the crowd misses it: the hour, the language and the
  per-country feed.
- Population and count: closed "parliamentary election" 50 events / 1,213 markets (41 events end in 2026),
  "presidential election" 50 / 957 (2026: 14), with Brazil, Argentina, Chile, Israel, Portugal, Bulgaria, Georgia and
  Mexico among the first 50 "election" titles. Historical nights with an archived count timeline are few (the census
  decides); the prospective arm is the real test. **Calendar: Brazil's second round on 2026-10-25** is the first boxed
  night, if the TSE feed is verified by 10-24.
- Test. **Stage 1 (`P`, historical descriptive):** for nights whose authority archives the count's timeline, align the
  bound-crossing time with CLOB `prices-history` at 1-minute; statistics: minutes from crossing to the first price >=
  0.9 (median; share > 5 min), the share of the terminal move completed before the crossing, and the asks available
  (Data API prints). **Stage 2 (prospective):** a per-night collector of the official feed (receipt-timed) and the
  CLOB book every 60 s for the mapped markets; unit = race or seat market; target = fills at recorded asks at crossing
  + 1 min, held to resolution; clusters = night (the binding way; a counted test needs >= 15 nights) with race as the
  inner way. Floors: median lead > 2 min; share > 5 min >= 25%; net >= 1.0c per share.
- Economic route: taker at stale asks; politics fee <= 1c; gaps of 10-40c; capacity $1-10k per race; the route exists
  only if asks persist > 1 minute after the bound is crossed.
- Data source and cost: `P` (official feeds per country, CLOB history, a small per-night collector). A day per country
  adapter; the honest cost is the adapters. C 3.
- Kill criteria: Stage 1 shows the move complete before the bound is crossed in > 75% of races (exit polls and wire
  projections already carry it); or median stale-ask life < 60 s; or fewer than 15 usable nights within a year.
- Leakage/confound: the bound must use only published totals as of the receipt time (no projections); recounts and
  annulments (rare; counted as wrong-side); "called" versus "resolved" (the target is both: price path and
  resolution); professionals cover large elections (the second tier is where it might live; report by liquidity).
- Novelty: CH129 is one US night with a reporting-order model; CH120 is a roll-call tally. New: a model-free bound on
  official feeds, repeated across many nights. N 3, EV 3, C 3.

**CH137. Launch-notice clocks and weather anchors: for "Will <vehicle> launch / reach <milestone> by <date>" markets,
the FAA temporary flight restriction, the maritime hazard notice and the county road closure are posted one to three
days before an attempt, and the launch-weather squadron publishes a probability of violating constraints at L-3 to
L-1; the hazard of a launch by the deadline is a public function of those notices, and the crowd prices on
announcements and tweets.**
- Mechanism and who pays: a launch cannot happen without the notices; a posted window with a 20% weather-violation
  probability is a 70-80% launch chance for that day given the vehicle's historical readiness rate; scrubs and slips
  are also visible in the notices. Who pays: buyers of "by <date>" rungs on announcement optimism, and holders slow to
  sell after a closure is cancelled. Why it persists: a dozen campaigns a year and five bespoke pages.
- Population and count: closed "SpaceX" 50 events / 308 markets (2025: 11, 2026: 19; 20 Starship titles), "Starship"
  37 / 178 (21 events 2024 or later). FAA TFR list keyless (200); the 45th Weather Squadron page refused the probe UA
  (403), so the weather arm needs a browser-UA check or a mirror (an honest open point). Floor 20 campaigns.
- Test (`P`, historical descriptive first). Decision time: notice publication + 1 h (FAA TFR issue time; closure
  posting time) and L-1 forecast + 1 h. Target: launch occurred by `D` (public record), and the first 1-minute price >=
  0.9. Statistics: Stage 1, the share of the terminal move completed before the first notice and the stale-ask life
  after it; Stage 2 (if Stage 1 shows room), slope of `(Y − p)` on `(q − p)` with `q` from a frozen launch-execution
  table (readiness rate given a primary closure date and a weather band, fitted on 2023-2025 attempts). Clusters =
  campaign (20-30). Floors: median lead > 10 min; slope 0.30; net 1.0c.
- Economic route: taker at stale asks at notice posting; tech/culture fee <= 1.25c; spreads 3-5c; capacity $1-10k.
- Data source and cost: `P` (FAA, county and USCG notices with their posting times; a weather mirror; CLOB history).
  Two afternoons. C 2.
- Kill criteria: < 20 campaigns with a mapped market; or the price moves within 10 minutes of the notice in > 75% of
  campaigns (the crowd watches the same pages); or no keyless weather source.
- Leakage/confound: notices are posted for backup days too (the table must be keyed on the primary date); regulatory
  holds (a licence modification pending) dominate some campaigns (reported as a class); the markets are few and
  correlated within a campaign (campaign is the unit).
- Novelty: CH124's generic watcher would catch a page change; this is a typed clock with a probabilistic anchor in a
  class no round has named. N 3, EV 2, C 2. Thin.

### C. Risk premia the crowd pays (parents CH118/CB13-R, CH17, CH60, CH28/CH90)

**CH138. Hedging-premium skew in barrier ladders: in the weekly crypto events that list "reach $U" and "dip to $L"
rungs side by side, the dip rungs (downside insurance for holders) are priced above their touch probability by more
than the reach rungs at the same standardised distance and horizon; the gap is the venue's version of the option
put skew, it is paid by hedgers, and selling it is a carry with a crash tail.**
- Mechanism and who pays: coin holders buy "dip to" YES as insurance and speculators buy "reach" YES as a lottery; the
  insurance demand is inelastic and one-sided; in listed options the put skew and the variance risk premium are the
  most persistent premia known. CB13-R tests the *level* confusion (touch versus terminal) and reports reach and dip
  separately only as a confound check. Who pays: insurance buyers. Why it persists: the premium is a few cents inside
  a payoff the crowd already misprices in level; a seller needs a tail gate.
- Population and count: 3,948 closed barrier markets in 501 events in the 2026-10-12 pull (CB13 H10), with reach and
  dip rungs in the same weekly event (CB13 probe 11: 21 members); more events before 2025-10 (CB13 probes 2-4). Expect
  400+ event-weeks with both sides, 2,000+ matched rung pairs.
- Test (`A` after CB13-R's fetch lands, or a fresh `h15_skew` with the same recipe; within-event paired). Decision
  time: daily 00:00Z checkpoints from listing to end (CB13-R's clock). Model probability `q`: the driftless reflection
  touch probability at the checkpoint from Binance 1-minute spot and trailing 30-day sigma (CB13-R's frozen recipe,
  reused unchanged). Target: touch outcome from the Binance path (public function; never Gamma's field). Statistic:
  within event and standardised-distance bin, `Delta = mean_dip(p − q) − mean_reach(p − q)` (the price-side skew) and,
  as the counted primary, `Delta_Y = mean_reach(Y − p) − mean_dip(Y − p)` (the dip side's realised overpricing relative
  to the reach side), pooled over events with event clustering (G about 500 event-weeks; underlying x month as the
  second way). Placebo: swap reach/dip labels within event at random. Floors: `Delta_Y >= 2c`; both signs agree; the
  effect holds in at least two underlyings.
- Economic route: sell dip-rung YES (buy NO at the recorded ask) at checkpoints where `p − q >= 5c`, hold to
  resolution; crypto fee `0.07*p*(1-p)` <= 1.75c; the CB1/CB6 tail gate on the crash weeks (a single crash week can
  erase a quarter of premia: the test reports the net with and without the worst 5% of weeks, and only the former
  counts). Maker variant: post asks on dip rungs at `q + 3c`.
- Data source and cost: `A` once `h13_touch` and `h13_binance` exist on the host (the SCREEN window only; the HOLDOUT
  is CB13-R's and is read for this idea only if its test is frozen before R's seal copy is opened); otherwise `P`
  (CB13-R's recipe: Gamma frame, CLOB history, data.binance.vision klines, about 0.3 GB). C 1 on R's frame, C 2
  standalone.
- Kill criteria: `Delta_Y` CI includes 0 or point < 2c; or the label-swap placebo advances; or the skew has the
  *opposite* sign (reach rungs overpriced: a lottery premium, CH17's object, not insurance); or the net after the tail
  gate <= 0 (the premium is fair compensation for crashes).
- Leakage/confound: drift (a trending week makes one side's touches likelier; the driftless `q` is wrong by the same
  amount for both sides only at equal standardised distance, hence the matching); the crowd's sigma versus realised
  sigma (common to both sides); the frame is CB13-R's (an L1 reuse, declared); category stays crypto.
- Novelty: CH118/CB13-R is the level; CH17 and CH60 are longshot selling and its tail; CH89 the Deribit anchor. New:
  the *sign asymmetry* between insurance and lottery rungs inside one event, and the option-skew mechanism. N 4, EV 4,
  C 1-2.

**CH139. Pre-release tail premium in scheduled-statistic bucket ladders: in CPI, payrolls, unemployment, GDP and Fed
decision ladders, the outer buckets (two or more away from the modal bucket at T−48 h) are overpriced at T−2 h by more
than at T−48 h, because lottery demand builds into the release; the premium is paid to whoever sells the tails into
the final hours, and it is distinct from the generic longshot bias because its *time structure* is the test.**
- Mechanism and who pays: in option markets, implied volatility rises into scheduled announcements and collapses after;
  the venue's analogue is retail buying "CPI 0.5% or more" at 08:00 ET. Who pays: pre-release lottery buyers. Why it
  persists: each release is one morning; makers step aside before releases (CH33), so the asks are retail's.
- Population and count: closed capped searches "CPI" 50 events / 388 markets, "GDP" 50 / 332, "unemployment rate"
  50 / 391, "payrolls" 21 / 169, "Fed decision" 47 / 250 (12-25 members per event); a date walk should give 150-250
  release clusters in 2025-2026. CB10 dropped CH90 for about 30 clusters per statistic; pooling five families with a
  family effect is the answer, and the release is the unit.
- Test (`P`, historical). Decision times: `T − 48 h` and `T − 2 h`, `T` = the scheduled release time from the BLS /
  BEA / FOMC calendars (public and fixed). Outer buckets defined at `T − 48 h` from the ladder's own modal bucket (a
  market quantity before `t`, allowed). Target: the bucket's resolution computed from the released value (first print
  per rule; Gamma's field as a cross-check only). Statistic: per release, `Pi_t = mean over outer buckets of (p_t − Y)`
  at both times; primary `Pi_{T−2h}` mean across releases >= 2c with release clustering (family as the outer way);
  **time-structure test** `Pi_{T−2h} − Pi_{T−48h} >= 1c` (the pre-release claim); placebo: the same statistics on the
  two buckets adjacent to the mode (the complement; should be <= 0). Floors as stated; >= 60 releases.
- Economic route: paper maker posting asks on outer buckets at the touch at `T − 2 h`, filled by trade-through prints
  (Data API), held to resolution, net per filled share >= 1.0c; taker NO at the recorded ask (economics fee
  `0.05*p*(1-p)` about 0.45c at p 0.10) with break-even hit rate about 8% against a modelled 2-4%.
- Data source and cost: `P` (Gamma frame, CLOB `prices-history` at 1-minute around the two decision times, Data API
  prints, the release calendars and values). About 1,500 markets; two afternoons. C 2.
- Kill criteria: `Pi_{T−2h}` CI includes 0; or the time-structure difference < 1c (then it is the generic longshot
  bias, already CH17's and CB6/CB7's object, not a pre-release premium); or the adjacent-bucket placebo has the same
  sign; or < 60 releases.
- Leakage/confound: consensus shifts between `T − 48 h` and `T − 2 h` move the mode (the outer set is frozen at
  `T − 48 h`; a drift in the mode is reported); Kalshi lists the same ladders and professional arbitrage may price
  them (the test is two-sided); releases are few per family (pooling with a family effect); the Fed arm is a decision,
  not a statistic (reported separately).
- Novelty: CH28 is release timing; CH75 first-print bias; CH90 nowcast anchors (dropped); CH119 the grid atom. New:
  the lottery premium's *time structure* into a scheduled release. N 4, EV 3, C 2.

### D. Professional anchors in unjoined classes (parents CH31, CH99, CH113, CH27)

**CH140. OIS-curve anchor for non-Fed central-bank decision ladders: the Bank of England publishes a daily OIS curve
(keyless archive), from which the market-implied probability of a 25 bp move at the next MPC meeting is a standard
calculation; the Polymarket BoE (and, where a keyless curve exists, ECB, BoC, RBA) ladders are priced by a crowd that
reads headlines, so the sign of (OIS-implied minus price) at the curve's publication predicts resolution.**
- Mechanism and who pays: the OIS market is where rate-setters' own staff read expectations; the mapping from the
  curve to meeting-step probabilities is textbook. Kalshi lists Fed meetings, not the BoE or ECB, so no cross-venue
  arbitrage channel exists for these ladders (see CH143). Who pays: buyers of "hold" or "cut" on commentary. Why it
  persists: a few meetings a year per bank, and the curve is a zip on a statistics page.
- Population and count: closed "Bank of England" 16 events / 54 markets (2024: 1, 2025: 6, 2026: 8), "ECB" 23 / 81,
  "Bank of Japan" 12 / 46, "rate decision" 50 / 186 (all 2026, neg-risk), "interest rate" 50 / 350. Verified keyless
  curve: BoE (HTTP 200 on the OIS zip). ECB's data API was not reachable from the probe (unverified). **Thin:** the
  BoE arm alone is 16 meetings; a counted test needs >= 30 meetings with a verified curve across banks.
- Test (`P`, historical). Decision time: the curve's publication day + 1 (the BoE publishes with a one-business-day
  lag) at 13:00Z, for each meeting at `M − 10 d` and `M − 2 d`. Anchor `q`: the meeting-step probabilities from the
  curve under a frozen recipe (linear step model, 25 bp grid, no term premium adjustment). Target: the decision from
  the bank's own statement (public function; never Gamma's field). Statistic: slope of `(Y − p)` on `(q − p)` across
  rungs with meeting clustering; floor 0.30; a sign-shuffle placebo.
- Economic route: buy the anchor side at the recorded ask when `|q − ask| >= 5c`, hold to the meeting (days); finance
  fee `0.04*p*(1-p)`; spreads 2-4c; capacity $5-50k on liquid meetings.
- Data source and cost: `P` (BoE zip history, CLOB history); an afternoon for the BoE arm; the other banks depend on a
  keyless curve each. C 2.
- Kill criteria: < 30 meetings with a verified curve (then descriptive only, uncounted); or slope < 0.30; or the price
  already equals the OIS-implied within 3c on average (the crowd includes rate traders).
- Leakage/confound: the one-day publication lag (the decision time respects it); the step model's own error near
  50-50 meetings (report sensitivity to a 10 bp grid); meeting clusters are few and correlated across banks in a
  cycle (bank x quarter as the outer way).
- Novelty: CH31 is the Fed against FedWatch (keyed); CH113 is Kalshi's ladder CDF. New: a keyless OIS archive and the
  banks Kalshi does not list. N 3, EV 3, C 2. Thin.

**CH141. Actuarial anchor for mortality markets: "Will <named person> die by <date>" markets (and the "who dies
first" neg-risk events) have a public probabilistic anchor in period life tables by age and sex, multiplied by a
frozen frailty class from public health status; the crowd overprices YES for the famous and ill (salience) and
underprices it for the quietly very old; the anchor's deviation predicts resolution.**
- Mechanism and who pays: the base hazard is public (SSA, ONS); the crowd's number is a story. Who pays: morbid
  lottery buyers and, on the other side, holders who treat survival to 95 as proof of immortality. Why it persists:
  nobody prices a market from a life table, and each market is small.
- Population and count: closed "die" 50 events / 959 markets (21 titles contain "die"; one event has 66 members).
  A date walk should give 100-300 markets on 50-150 persons (persons are the clusters). Floor 40 persons.
- Test (`P`, historical). Decision time: listing + 24 h and `T − 90 d`. Anchor `q`: `1 − exp(−h * tau)` with `h` the
  life-table hazard for age and sex times a frailty multiplier from a frozen three-class rule (public serious illness
  reported before listing; none; unknown), fitted on no market data. Target: resolution (Gamma's field is the outcome
  here; death is public). Statistic: slope of `(Y − p)` on `(q − p)` with person clustering; floor 0.25; the
  two-sided sign is reported (salient overpricing versus old-age underpricing as separate arms).
- Economic route: buy the anchor side at the recorded ask when `|q − ask| >= 5c`, hold to resolution (months; capital
  lock); fee <= 1.25c; the CB1 tail gate on NO carries.
- Data source and cost: `P` (Gamma texts, life tables, CLOB history). An afternoon. C 1-2.
- Kill criteria: < 40 persons; or slope < 0.25; or the frailty class cannot be assigned from public pre-listing
  information for > 30% of persons.
- Leakage/confound: hindsight in the frailty class (the rule reads only sources dated before listing); multi-person
  events share a clock (event as a second way); long holds at zero interest (CH115's lesson: annualise, and report the
  lock).
- Novelty: CH22 (sensational YES at genesis) and CH88 (political underconfidence) are calibration claims without an
  anchor. New: a public hazard table as the anchor in a class no round has named. N 3, EV 2, C 1-2. Thin; a research
  tooling note only, as with every class here.

### E. Maps (parents CH51, CH25, CH128)

**CH142. Series launch window: the first four weeks of a newly created series (Gamma `/series` `createdAt`; more
than 150 series since August 2026) are the soft spot of every anchored family: spreads are wider, depth thinner and
the deviation from any public anchor larger than in the same series' weeks 9-12, because the crowd and the bots learn
a template's quirks over weeks; so model-anchored strategies should be timed to launches.**
- Mechanism and who pays: a new template has no bot yet (bots are configured per series), no resolved history for
  base rates and a first crowd of curious retail. Who pays: the first weeks' takers and the first bots' slow learners.
  Why it persists: the venue launches templates faster than its crowd learns them (about 50 a month, fact 2).
- Population and count: > 150 series created since 2026-08; the sidecar's `series_slugs` (since 11 Oct) joins every
  capture row to its series; `recurrence` and `seriesType` classify them.
- Test. **Descriptive arm (`A`, host only):** within-series contrast of median spread, `depth_*_1c` and `liquidity`
  between weeks 1-4 and weeks 9-12 after the series' first event, series as the cluster, 30+ series; a composition
  placebo shuffles week labels within series. **Anchored arm (`A` + the anchor family's data):** for series whose
  outcome is a public function of a public path or statistic (Up/Down, strike, count series), the within-series
  difference in mean `|p − q_anchor|` at fixed checkpoints between the two windows; floor 2c; the anchors are those of
  CH83/CH84/CH99/CH118 and must be frozen per family. Decision time: each 2 h capture (descriptive) or the family's
  checkpoint (anchored). Target: realised spread and depth (descriptive) or the family's public-function outcome.
  Clustering: series. Floors: 2c on `|p − q|`; 1c on spread.
- Economic route: none of its own; it times the other families' routes (where the per-share edge is a few cents, a
  2c larger gap in the launch window is the difference between a route and none).
- Data source and cost: `A` (captures, sidecar, sweeps) plus 2-3 `/series` requests for `createdAt`; the anchored
  arm costs whatever the family costs. C 1 (descriptive), C 3 (anchored).
- Kill criteria: < 30 series with four weeks of captures; or the launch-window spread and gap are no larger (the crowd
  learns in days); or the within-series placebo advances.
- Leakage/confound: new series start with new markets (market age and series age are confounded in week 1; compare at
  equal market age within the series' weeks); survivorship (series that die young are the thin ones; report both);
  CB9-P's Pyth frames are sealed, so the anchored arm starts with series launched after the relevant freezes.
- Novelty: CH51 is a series' base rate once it is old; CH22/CH56 are a *market's* first day. New: the *series'*
  learning curve as a timing map. N 3, EV 2-3, C 1-3.

**CH143. The Kalshi-absent class map: markets without a Kalshi twin (by Kalshi's own listing restrictions on war,
terrorism, assassination and gaming, and by Kalshi's choices: crypto barrier ladders, mention baskets, culture) have
no professional cross-venue arbitrage channel, so their calibration residual at `T − 24 h` is larger and the anchored
families' slopes are larger there than in twin-present classes at the same liquidity; the map tells families A-D
where the room is.**
- Mechanism and who pays: the replicated Kalshi lead says a professional price disciplines Polymarket where a twin
  exists; where none exists the discipline is absent. Who pays: the twin-absent crowd. Why it persists: it is not a
  trade, it is a map.
- Population and count: the 958 matched pairs (688 sports) and 316 clean pairs mark twin presence; the captures hold
  about 274,000 market rows per pass; `fee_type` / `fee_category` give the category; a frozen text rule on the
  2026-10-12 pull's questions (field-restricted) gives the Kalshi-unlistable classes.
- Test (`A`, host only; within liquidity-decile x category cells). Decision time: `T − 24 h` capture. Target:
  resolution (Gamma's field; these are not public-function outcomes in general). Statistic: difference in the Brier
  residual `(Y − p)^2 − p(1 − p)` between twin-absent and twin-present markets *within cell*, event clustering; a
  relabelling placebo within cell (the CB12-X lesson applies with full force: composition is the null here); floor 1
  pp of residual. Secondary: the anchored families report their slopes split by this label.
- Economic route: none of its own; allocation of the anchored families' effort.
- Data source and cost: `A` only; an afternoon. C 1.
- Kill criteria: the within-cell difference < 1 pp or the relabelling placebo advances; or twin presence cannot be
  separated from liquidity (fewer than 5 cells with both labels and >= 30 events each).
- Leakage/confound: Kalshi's twin exists for the liquid and the American; the within-cell design and the text rule
  for *unlistable* (not merely unlisted) classes are the guards; sports dominate the matched set (a parameter).
- Novelty: CH25 is the sign of the Polymarket-Kalshi level gap on politics; CH113/CH114 are anchors. New: twin
  presence as the axis of a calibration and effort map. N 2-3, EV 2 (as a map, 3 for what it steers), C 1.

---

## 3. Ranked top 8

Rank = originality x plausibility x testability now x money route. "Runnable now" means the test can start this week
on existing stores or on keyless fetches that are not bound to the `T_seal` lane and yield to every CB11-CB14 job.

| Rank | ID | One line | Runnable now | Family |
|---|---|---|---|---|
| 1 | CH138 | Hedging-premium skew: dip versus reach rungs in the same weekly barrier event; the venue's put skew, within-event paired, on CB13-R's frame | yes once `h13_touch` / `h13_binance` land (SCREEN window; L1); standalone `h15_skew` otherwise | C |
| 2 | CH139 | Pre-release tail premium in CPI / GDP / unemployment / payrolls / Fed ladders; the time structure into the release is the test | yes (CLOB history + calendars; about 1,500 markets) | C |
| 3 | CH131 | Quoter-type footprint: grain and shape of the resting side classify bots and people; where the maker's pick-offs live | yes (`A` only, no fetch; two columns on CB13-T's fill table) | A |
| 4 | CH134 | Kalshi-settlement-labelled decided carry: an external, timestamped decider; the wrong-side rate counted | yes after a census (316 pairs on host + about 1,000 small requests) | B |
| 5 | CH135 | Statutory-deadline clocks: SEC 19b-4, EC Phase 1, PDUFA, presentment; decisions land on the deadline; two keyless archives verified | yes (FR API, GovInfo, case pages, CLOB history) | B |
| 6 | CH132 | Wake-up prints: the market's own inter-arrival clock as the arrival's information; maker steps aside | yes (`A` only) after the prior-work check | A |
| 7 | CH136 | Official-count clocks in non-US election nights; model-free "cannot be overtaken" bound; Brazil's second round 2026-10-25 is the first boxed night | Stage 1 yes where count timelines are archived; Stage 2 needs a per-country adapter | B |
| 8 | CH133 | Depth fade at 120 s in the cross-venue book stream with Kalshi quiet; maker protection | after the E009/E010 analyses are committed (mid-November) | A |

Next in line: CH143 (Kalshi-absent map; host only; cheap and steers the rest), CH142 (series launch window; host
descriptive now), CH140 (OIS anchor; thin until a second keyless curve is verified), CH137 (launch clocks; thin;
weather source open), CH141 (actuarial anchor; thin).

**Screenable on data AREPO already holds (no fetch):** CH131 in full (monitor prints, capture touches, sweeps);
CH132 in full (monitor prints, trade samples); CH143 in full (captures, sidecar, the pair lists, a text rule on the
2026-10-12 pull); CH142's descriptive arm (captures, sidecar `series_slugs`, sweeps; `/series` `createdAt` is 2-3
requests); CH134's Polymarket half of the census (the 316 pairs' history and `accepting_orders` in captures; the
Kalshi `settlement_ts` is one small request per pair); CH133 on the host stream after the E009/E010 commit; CH138's
crypto arm once CB13-R's `h13_touch` and `h13_binance` are on the host (no additional fetch). Everything else needs a
small keyless fetch (`h15_*`) that can complete within a week, except CH136's Stage 2 and CH137 (adapters and
sources to verify).

**Screen sketches for the top 5.**
- **CH138.** Population: CB13-R's SCREEN frame (weekly crypto barrier events with both reach and dip rungs; ends before
  2026-04-01) or `h15_skew` by the same recipe. Decision time: daily 00:00Z checkpoints. Target: touch outcome from
  Binance 1-minute highs and lows. Statistic: within event and standardised-distance bin,
  `Delta_Y = mean_reach(Y − p) − mean_dip(Y − p)`, event clusters (about 500), label-swap placebo; floor 2c; the
  price-side `Delta` reported. Economic: buy NO on dip rungs at the recorded ask when `p − q >= 5c`; net with and
  without the worst 5% of weeks; only the former counts.
- **CH139.** Population: closed CPI / GDP / unemployment / payrolls / Fed ladders by date walk, 2025-01 to 2026-10,
  150-250 releases. Decision times: `T − 48 h` (defines the outer set), `T − 2 h`. Target: bucket resolution from the
  released value. Statistic: `Pi_{T−2h}` mean over releases >= 2c; `Pi_{T−2h} − Pi_{T−48h} >= 1c`; adjacent-bucket
  placebo <= 0; release clusters with family as the outer way. Economic: paper maker asks on outer buckets at `T − 2 h`
  filled by trade-through prints; taker NO at the recorded ask; floors 1.0c.
- **CH131.** Population: CB13-T's SCREEN prints with a crossed capture touch (plus the sweep arm where present).
  Decision time: the print's venue `ts`. State: touch grain (third decimal), sweep shape (top-3 size CV, 5c/1c depth
  ratio). Target: print-based 2 h and 6 h mark-out (touch-consistent side). Statistic: within-market human-minus-bot
  difference, event x day clusters, hour way, within-market label shuffle; floor 0.5c and the sign condition.
- **CH134.** Population: the 316 clean pairs; census = pairs where Kalshi `settlement_ts` precedes Polymarket's
  `closedTime` and `accepting_orders` is still true at `settlement_ts + 10 min`. Decision time: `settlement_ts + 10
  min`. Target: Polymarket's resolution and the wait. Statistic: mean net of buying the Kalshi-result side at the first
  recorded ask, fee once, minus realised wrong-side losses; wrong-side Wilson upper bound <= 0.5%; event clusters;
  floors 0.5c, 72 h median wait.
- **CH135.** Population: `h15_statute` = closed ETF / FDA / merger / law markets with an intermediate rung before the
  statutory final deadline, by date walk; the clocks from the FR API, EC case pages, FDA goal dates and BILLSTATUS.
  Decision times: listing + 24 h, `D_m − 14 d`. Target: the decision date from the public source. Statistic: slope of
  `(Y − p)` on `(q − p)` with per-class deadline-day base rates frozen on 2019-2024 cases; filing clusters; floor 0.30.
  Economic: buy NO on intermediate rungs at the recorded ask when `p − q >= 5c`.

**How the families would be registered.**
- **A. Who is resting and arriving (CH131-CH133).** Host-only measurements with maker-protection routes; each is a
  within-market (or within-pair) contrast with a label-shuffle placebo as the primary design; CH131 and CH132 ride
  CB13-T's fill table and frozen side-free rule; CH133 waits for the E009/E010 commit and declares its Kalshi-quiet
  filter before any read.
- **B. External deciders and clocks (CH134-CH137).** Descriptive stages first (does the move precede the decider or
  the clock; do asks persist); counted economics only where the descriptive shows room; the external label or clock is
  the decision time, never the market's move; CH134's wrong-side rate is a counted number with its own floor.
- **C. Risk premia (CH138, CH139).** Within-event paired contrasts (reach versus dip; outer versus adjacent buckets)
  with label-swap placebos; the tail gate on every carry; time structure as the test that separates a premium from the
  generic longshot bias.
- **D. Anchors (CH140, CH141).** One frozen anchor recipe per class fitted on no market data; pooled slopes with
  class effects; count gates before any read (30 meetings; 40 persons).
- **E. Maps (CH142, CH143).** Within-series and within-cell contrasts with relabelling placebos; no route of their
  own; their output is a line in every later design's census.

**What is honest to say about all of them.** Round 1 was carries, round 2 the maker in the right state, round 3 tails
and flow identity, round 4 measurement and new products, round 5 professional anchors and unseen populations, round 6
public clocks and the class map. This round's bet is narrower and, I think, better aimed by the nulls: that the
maker's loss, the one number that has blocked every route, has an address in *who is resting and who is arriving*
that the host already records; that *external deciders and clocks* (a settlement stamp, a statute, an official count)
settle questions before the venue does; and that the two most robust premia in option markets, the insurance skew and
the pre-announcement lottery premium, have never been looked for on a venue whose products are options with a
different name. Every primary design is a within-unit contrast with a composition placebo, because CB12-X showed a
clean contrast advancing on composition alone. Every population was counted before it was proposed; the thin ones
(CH137, CH140, CH141) say so; two candidates died in their own probes (§4). Nothing here is edge until it has gone
through screen, frozen replication, prospective registration and an economic check at recorded prices.

---

## 4. Ideas considered and rejected, and why

- **Neg-risk late entrants (a new member joins an existing event; the sum of YES overshoots and the giver is
  predictable).** The census: of 82 open neg-risk events with >= 5 members and volume >= $10k, **0** have members whose
  `createdAt` span exceeds 7 days (1,559 members, 0 late). Whatever Polymarket does when a candidate is added, it does
  not show as a late member in Gamma. Rejected.
- **Deep-walk print reversion (prints that walk the book >= 10c revert; rest deep bids).** This is temporary price
  impact, which is E004's reversal conditioned on depth: a re-run of reversal with a new state variable, excluded by
  the brief. CH93 (round-level breaks) holds the nearest object.
- **Silent repricing (a tight book that moves without prints is the makers' consensus and continues).** Continuation
  conditioned on a new state variable: a momentum re-run, excluded. SB2-J3/J4's bounce decomposition already owns the
  quote-versus-trade split of 2 h moves.
- **Trending-list entry as the maker's calendar (a market entering the top-N by `volume24hr` draws uninformed flow).**
  CH24 and CH37 own the attention-flow object; the only new part is the list, not the mechanism.
- **Deadline extensions (`endDate` changes between captures impose a mechanical loss on NO).** No count is possible
  without a capture walk, and the known cases are sports postponements (CH07's clause). Parked with the sports
  decision.
- **Leaderboard-period-end volume races as uninformed flow.** The premise (prize deadlines on the public leaderboard)
  is unverified; CH72's fee-valley farming is the nearest tested object. Not proposed on an unverified premise.
- **Fee-boundary twins (a zero-fee geopolitics market and a fee-paying politics market on correlated questions; the
  zero-fee one leads).** Pairs across the boundary are a handful; CH64's twins were dropped by CB8 for thinness.
- **The 45th Weather Squadron forecast as a standalone anchor.** The page returned 403 to the probe user agent; kept
  only as an arm of CH137 with the source marked open.
- **Mortality markets as a longshot-selling carry without an anchor.** CH17 and CB6/CB7 own it; CH141 is proposed
  only with the life-table anchor and the two-sided sign.
- **ECB and BoJ OIS arms as counted tests.** No keyless curve verified at the probe (the ECB API did not respond; the
  BoJ publishes none); folded into CH140's availability gate.
- **Kalshi depth ratio as the lead's moderator; Kalshi-closed hours; the pair's price lead with new data.** The
  identical-pair lead is sealed in E009/E010 and excluded by the brief; CH133 conditions on Kalshi being *quiet* and
  CH134 uses the settlement stamp, not the price.
- **Re-proposals of CH01-CH130 with new data** (decided carry by own price, dispute lotteries, reward geometry, tick
  regimes, series base rates, genesis overpricing, mention baskets, Deribit and option-chain anchors, roll-call and
  speech clocks, Wikipedia edits, barrier level confusion, grid atoms, hidden books, round-dollar and alert-threshold
  footprints, horizon staleness, election-night reporting order, the pair at birth): not re-proposed; where a new idea
  touches one, the parent is named and the new clock, object or data source is stated.
- **Order anticipation, spoofing, inducing cancellations, manipulation of any kind, insider identification as a
  route, holding rewards, maker-rebate loops, taker full-set arbitrage, comment sentiment, wash detection as alpha,
  API quirks, Combo RFQ data, Polymarket US, keyed anchors (Betfair, Pinnacle, Smarkets, Metaculus), wallet-based
  signatures of any kind.** Rejected in rounds 1-6 for reasons that still hold.

---

## 5. Sources consulted (external; AREPO documents are cited inline by name)

**Keyless probes run for this round (2026-10-19, 04:05-04:20Z; 37 requests; counts, field names, end-year histograms
and title-word booleans only; no price, outcome, volume or wallet of any market was printed or stored; scripts ran from
`/tmp/ch7probe/` with `python3 -I`, wrote nothing but their own stdout, and are not committed).** All GETs and HEADs
carried `User-Agent: arepo-research-probe`, 40-second timeouts, 0.9 s pacing, no key. "e / m / max / nr" = events,
markets, maximum members per event, neg-risk events; "years" = events by `endDate` year.

| # | Request as sent (host + path + query) | Printed |
|---|---|---|
| 1 | `gamma-api.polymarket.com/public-search?q=launch&events_status=closed&limit_per_type=50` | 50 / 254 / 10 / 1; years 2023 1, 2024 1, 2026 1, 2027 8, 2028 39; titles with Starship 2, SpaceX 2, rocket 1, launch 48 |
| 2 | `...public-search?q=Starship&events_status=closed&limit_per_type=50` | 37 / 178 / 21 / 3; years 2021 3, 2022 1, 2023 4, 2024 11, 2025 6, 2026 4, 2027 5, 2028 2; titles flight 9, launch 15, reach 10 |
| 3 | `...public-search?q=ECB&events_status=closed&limit_per_type=50` | 23 / 81 / 5 / 17; years 2024 2, 2025 9, 2026 10, 2027 2 |
| 4 | `...public-search?q=Bank%20of%20England&events_status=closed&limit_per_type=50` | 16 / 54 / 5 / 11; years 2024 1, 2025 6, 2026 8, 2027 1 |
| 5 | `...public-search?q=Bank%20of%20Japan&events_status=closed&limit_per_type=50` | 12 / 46 / 5 / 10; years 2024 1, 2025 2, 2026 9 |
| 6 | `...public-search?q=rate%20decision&events_status=closed&limit_per_type=50` | 50 / 186 / 5 / 50; all 2026 |
| 7 | `...public-search?q=ETF&events_status=closed&limit_per_type=50` | 50 / 50 / 1 / 0; years 2024 2, 2025 25, 2026 23; titles approve 3 |
| 8 | `...public-search?q=FDA&events_status=closed&limit_per_type=50` | 50 / 106 / 33 / 2; years 2021 7, 2022 2, 2025 3, 2026 33, 2027 4, 2028 1; titles approve 38, by 10 |
| 9 | `...public-search?q=acquisition&events_status=closed&limit_per_type=50` | 50 / 279 / 23 / 3; years 2022 2, 2023 1, 2024 3, 2025 22, 2026 11, 2027 10, 2028 1; titles by 9, close 4 |
| 10 | `...public-search?q=signed%20into%20law&events_status=closed&limit_per_type=50` | 8 / 14 / 7 / 0; years 2022 1, 2025 5, 2027 2 |
| 11 | `...public-search?q=merger&events_status=closed&limit_per_type=50` | 23 / 54 / 16 / 0; years 2023 1, 2024 3, 2025 2, 2026 10, 2027 5, 2028 2; titles by 11, close 3 |
| 12 | `...public-search?q=CPI&events_status=closed&limit_per_type=50` | 50 / 388 / 12 / 48; years 2025 7, 2026 33, 2027 10 |
| 13 | `...public-search?q=payrolls&events_status=closed&limit_per_type=50` | 21 / 169 / 20 / 16; years 2025 5, 2026 15, 2027 1 |
| 14 | `...public-search?q=GDP&events_status=closed&limit_per_type=50` | 50 / 332 / 10 / 44; years 2023 1, 2025 4, 2026 38, 2027 6, blank 1 |
| 15 | `...public-search?q=unemployment%20rate&events_status=closed&limit_per_type=50` | 50 / 391 / 25 / 37; years 2024 5, 2025 17, 2026 25, 2027 1, blank 2 |
| 16 | `...public-search?q=Fed%20decision&events_status=closed&limit_per_type=50` | 47 / 250 / 9 / 42; years 2024 1, 2025 15, 2026 28, 2027 3 |
| 17 | `...public-search?q=election&events_status=closed&limit_per_type=50` | 50 / 1,012 / 128 / 43; years 2023 1, 2024 11, 2025 2, 2026 30, 2027 5, 2028 1; titles naming Brazil 3, Israel 5, Argentina 1, Chile 1, Portugal 1, Mexico 1, Georgia 1, Bulgaria 1; Presidential 12, Governor 12, Senate 16, Mayor 3, Parliamentary 1, Primary 2 |
| 18 | `...public-search?q=parliamentary%20election&events_status=closed&limit_per_type=50` | 50 / 1,213 / 44 / 48; years 2025 3, 2026 41, 2027 6; titles seats 6, win 22 |
| 19 | `...public-search?q=presidential%20election&events_status=closed&limit_per_type=50` | 50 / 957 / 128 / 35; years 2023 4, 2024 24, 2026 14, 2027 7, 2028 1; titles win 23, round 13 |
| 20-21 | `gamma-api.polymarket.com/events?closed=false&limit=100&volume_min=10000&offset={0,100}` | 200 events; 82 neg-risk with >= 5 members; 0 with member `createdAt` span > 7 d (0 > 30 d); 1,559 members, 0 created > 7 d after the first |
| 22 | `gamma-api.polymarket.com/series?limit=100&offset=0` | 50 rows; field names (`active`, `archived`, `closed`, `commentCount`, `commentsEnabled`, `competitive`, `createdAt`, `createdBy`, `description`, `events`, `featured`, `id`, `layout`, `new`, `publishedAt`, `recurrence`, `restricted`, `seriesType`, `slug`, `startDate`, `ticker`, `title`, `updatedAt`, `updatedBy`, `volume24hr`); `createdAt` months 2022-10 .. 2025-02 |
| 23 | `...series?limit=100&offset=100&order=createdAt&ascending=false` | 50 rows; `createdAt` 2026-08: 40, 2026-09: 10 |
| 24 | `api.elections.kalshi.com/trade-api/v2/markets?limit=1&status=settled` | HTTP 200; 44 field names including `result`, `settlement_ts`, `settlement_value_dollars`, `expiration_time`, `latest_expiration_time`, `settlement_timer_seconds`, `can_close_early`, `yes_bid_size_fp`, `yes_ask_size_fp` |
| 25 | HEAD `www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/oisddata.zip` | HTTP 200 |
| 26 | `data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_1Y?lastNObservations=1&format=jsondata` | URLError (not reached from the probe; unverified) |
| 27 | `www.federalregister.gov/api/v1/documents.json?per_page=1&conditions[term]="19b-4" exchange-traded` | HTTP 200; `count` 5,323 |
| 28 | HEAD `tfr.faa.gov/tfr3/?page=list` | HTTP 200 |
| 29 | HEAD `www.patrick.spaceforce.mil/Weather/` | HTTP 403 |
| 30 | HEAD `www.govinfo.gov/bulkdata/BILLSTATUS/119/hr` | HTTP 200 |
| 31 | `api.elections.kalshi.com/trade-api/v2/exchange/status` | HTTP 200 |
| 32 | `...public-search?q=SpaceX&events_status=closed&limit_per_type=50` | 50 / 308; years 2024 5, 2025 11, 2026 19, 2027 9, 2028 4, blank 2; titles launch 15, Starship 20 |
| 33 | `...public-search?q=rocket&events_status=closed&limit_per_type=50` | 50 / 561; years 2025 7, 2026 42, 2027 1; titles launch 1 |
| 34 | `...public-search?q=interest%20rate&events_status=closed&limit_per_type=50` | 50 / 350; years 2023 3, 2024 6, 2025 3, 2026 36, 2027 2; titles ECB 7, Bank 24, cut 1, hike 2 |
| 35 | `...public-search?q=die&events_status=closed&limit_per_type=50` | 50 / 959 / 66; years 2021 1, 2022 1, 2024 3, 2025 13, 2026 26, 2027 6; titles die 21 |
| 36 | `...public-search?q=downgrade&events_status=closed&limit_per_type=50` | 10 / 29 / 19; years 2025 5, 2026 3, 2027 2; titles downgrade 9, Moody 1, S&P 1 |
| 37 | `...public-search?q=sovereign&events_status=closed&limit_per_type=50` | 23 / 297 / 41; years 2025 12, 2026 7, 2027 4 |

Local read-only commands this round: `git status`, bounded `sed`/`grep` over `docs/research_lab/` (rounds 1-6, the
ledger tail, CB13/CB14 heads, `COLLECTION_HOST.md`, `LIVE_TRADE_MONITOR.md`, `CROSS_VENUE_LIVE.md`,
`ECONOMIC_CONDITIONS_STUDY.md`, `EXECUTION_COSTS.md`) and field-name greps in `ext_sidecar.py`, `book_sweep.py`,
`trade_sample.py`, `cross_venue_live.py`. No host access, no data file opened.

**External documents.**
- Kalshi trade API v2 (markets, settled markets, exchange status and schedule): https://trading-api.readme.io/reference
  (probed; CH133, CH134, CH143).
- Bank of England, yield curve data (government liability and OIS curves, daily archive):
  https://www.bankofengland.co.uk/statistics/yield-curves (probed; CH140).
- European Central Bank Data Portal API: https://data.ecb.europa.eu/help/api/overview (not reached by the probe; CH140).
- Office of the Federal Register API: https://www.federalregister.gov/developers/documentation/api/v1 (probed; CH135).
- GovInfo bulk data, BILLSTATUS: https://www.govinfo.gov/bulkdata/BILLSTATUS (probed; CH135).
- European Commission competition case search (merger deadlines): https://competition-cases.ec.europa.eu/ (not probed;
  CH135).
- US Securities and Exchange Commission, Rule 19b-4 and Section 19(b)(2) time limits (45 / 90 / 180 / 240 days):
  https://www.sec.gov/rules-regulations/self-regulatory-organization-rulemaking (not probed; CH135).
- FDA, PDUFA goal-date commitments: https://www.fda.gov/industry/prescription-drug-user-fee-amendments (not probed;
  CH135).
- FAA temporary flight restrictions list: https://tfr.faa.gov/ (probed; CH137). 45th Weather Squadron launch forecasts:
  https://www.patrick.spaceforce.mil/Weather/ (probed, 403; CH137). Cameron County road closures and USCG local notices
  to mariners (not probed; CH137).
- Tribunal Superior Eleitoral (Brazil) results services; Argentina's national electoral count; Germany's federal
  returning officer; Chile's Servel (not probed; feed URLs to be verified per night; CH136).
- US Social Security Administration period life tables and UK ONS national life tables (not probed; CH141).
- Polymarket docs cited in rounds 1-6 and still used here: fees (`rate*p*(1-p)`, maker 0, rebates), liquidity
  rewards, CLOB orders, books and `prices-history`, negative risk, UMA resolution: https://docs.polymarket.com/trading/fees,
  https://docs.polymarket.com/developers/market-makers/liquidity-rewards,
  https://docs.polymarket.com/developers/CLOB/orders/orders, https://docs.polymarket.com/developers/neg-risk/overview,
  https://docs.polymarket.com/developers/resolution/UMA.
- Bakshi and Kapadia (2003), "Delta-hedged gains and the negative market volatility risk premium"; Carr and Wu (2009),
  "Variance risk premiums"; Bollen and Whaley (2004), "Does net buying pressure affect the shape of implied volatility
  functions?" (the insurance skew and demand-based option pricing; CH138).
- Patell and Wolfson (1979, 1981) and Dubinsky, Johannes, Kaeck and Seeger (2019), "Option pricing of earnings
  announcement risks" (implied volatility into scheduled announcements; CH139).
- Glosten and Milgrom (1985); Easley and O'Hara (1987); Hasbrouck (1991), "Measuring the information content of stock
  trades" (adverse selection, trade timing and information; CH131, CH132, CH133).
- Shreve (2004), *Stochastic Calculus for Finance II*, chapter 7 (reflection principle; CH138, as in round 6).
- Foley (2013) and Foley and Stewart (2020) on the timing of the count (CH136, as cited in round 6 for CH129).
- Dubach (arXiv:2604.24366), Nechepurenko (arXiv:2605.11640), Le (arXiv:2602.19520), Cardozo and Rivero-Wildemauwe
  (arXiv:2609.12878), Page and Clemen (2013): as cited in rounds 1, 4, 5 and 6 (context for families B and D).
