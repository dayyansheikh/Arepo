# Creative hypotheses, round 6: where money could come from on Polymarket (2026-10-20)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-18 15:41 UTC+1,
2026-10-18T14:41Z; the file carries the round's planned date). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md`
(CH01-CH34), round 2 `CREATIVE_HYPOTHESES_2026-10-16.md` (CH35-CH59), round 3 `CREATIVE_HYPOTHESES_2026-10-17.md`
(CH60-CH78), round 4 `CREATIVE_HYPOTHESES_2026-10-18.md` (CH79-CH98), round 5 `CREATIVE_HYPOTHESES_2026-10-19.md`
(CH99-CH117); this file starts at **CH118** and repeats none of them. Where an idea builds on an earlier one, the parent
is named and the new mechanism, clock or data source is stated. Every number quoted from an AREPO document is a
development or screen result, not evidence. One file; no code, no queue specs, no other commits.

## 0. How to read this file

**What changed since round 5 (17-18 Oct drafts, smokes and drops).**
- **CB11 (CH85 as CB11-W proposer clocks, CH88 as CB11-P political underconfidence, CH97 as CB11-A attention without
  news) is DRAFT-REVISED** after challenger round 1 ("accept with required changes"); the W family's code exists, P and A
  are not implemented. CB11 dropped CH81, CH86, CH94-CH96 and CH98 for wallet or side dependence or power. Its probes
  found that Gamma `closedTime` equals the UMA settlement time, that 307,658 distinct markets closed after their
  scheduled end, and that Wikipedia's per-article **pageviews publish with about a 48-hour lag** (the 12-hour assumption
  was contradicted): that is why CH123 below uses the *edit stream*, not pageviews.
- **CB12 (DRAFT, pre-challenger, nothing queued)** took CH112 (CB12-M mention baskets), CH110+CH111 (CB12-F, one print
  fetch), CH108's earthquake arm (CB12-E), CH115 (CB12-X, host files only) and CH99 (CB12-O, prospective only); CH103
  is a counts-only census (q0265). It dropped CH100 (overlaps CB9-P's frame; re-entry CB13), CH106 (no verified calendar
  archive) and CH108's measles, Rotten Tomatoes and App Store arms. Its counts: 553 earthquake markets in 108 events
  ending before 2026-10-01; 1,472 mention-basket markets in March 2026 alone; USGS M6.5+ about 43.8 a year; 12,630 CBOE
  SPY options on one chain read.
- **Smokes and collectors.** CB7 smoke v2 PASS; CB8-H q0160c PASS (10-18 01:02Z) and q0162/q0163 promoted to start no
  earlier than 10-21 06:00Z (after H-v4 to v6 overrode a pre-registered stop rule, disclosed and reviewer-accepted);
  CB9 smoke v2 PASS with the analysis side NO_GO pending fixes; CB10 smoke PASS, freeze check NO_GO, rules v2 in
  progress; `h8_tail_b` fetched 10-18 00:13Z with 10,297 origins. **None of CB1-CB12 has a verdict on any hypothesis.**
  The cumulative trial count is **1,156** (CB11/CB12 battery); every test here joins that denominator. `T_seal` is
  2026-10-22 00Z; E009/E010 run to 11-03, E011 to 11-10.
- **The ledger's binding facts are unchanged.** E007 flow continuation is Supported (beta 0.0036, 11 of 12 periods) but
  worth about +0.36c against about 4.5c round trip; HB1 +0.3 to +0.6c per SD; **0 of 95 economic cells positive after
  cost** (all trades combined -3.67c); T5: nothing beats recalibrated price (the 7-day gain was an artefact); wallet
  effects null (WA1/WA3, the HB1 wallet family, freshness); SB2 J2 net taker about -2.5c; J4 withheld (placebo not
  null); CB1-D +0.78 pp under the 1 pp floor; CB4-N 1.29 eligible events an hour against 15 assumed; CB5-L 0 CDF
  families. The Kalshi 10-20 minute lead (r about 0.24-0.26) is still the only replicated predictor and is sealed in
  E009/E010. The lesson of every batch stands: **count the population before the hypothesis**; every idea below carries
  a probe count, and three candidates died in the probes (§4).

**Structural facts from this round's probes (keyless, 2026-10-18 14:28-14:41Z, 39 requests; counts, field names, tag
names and rule-word booleans only; no price, outcome, volume or wallet of any market was printed or stored; every
request is listed in §5).**
1. **Barrier ladders are a large population.** "dip to" returns 50 closed events / 835 markets (up to 47 strikes per
   event); "reach" 50 / 283 (30 of 50 titles are "reach ... by <date>"). Race-form titles ("hit X before Y") are 3 of
   50 "before" events, so the race arm is thin (§CH118).
2. **Inclusive-threshold wording is common and the sources sit on grids.** "or higher" 50 events / 50 markets, "or
   more" 50 / 51, "at least" 38 / 64 (all capped searches). USGS reports magnitudes on a 0.1 grid: of 179 events in
   [6.85, 7.15] since 2010, 81 are 6.9, **53 exactly 7.0** and 45 are 7.1, so the grid point at 7.0 carries about 30%
   of the band (§CH119).
3. **Floor votes have a keyless live clock in the House.** `clerk.house.gov/evs/2026/rollNNN.xml` is served with tags
   `rollcall-num`, `legis-num`, `action-date`, `action-time`, yea/nay/not-voting totals and per-member records; the
   Senate's LIS XML returned 403 to the probe user agent. Closed "pass" events: 50 / 99 markets (21 titles name the
   House, the Senate or a bill); "Senate vote" 50 / 1,245 (43 neg-risk, mostly confirmation ladders) (§CH120).
4. **The Wikimedia EventStreams `recentchange` feed is keyless and real-time.** One event carries `timestamp`,
   `meta.dt`, `title`, `type`, `bot`, `user`, `length`, `revision`, `comment`. Closed "resign" 50 events / 93 markets,
   "out as" 50 / 95 (§CH123).
5. **Rules name their source URL often enough to watch.** 0, 16 and 20 of three pages of 100 open markets with volume
   >= $5k carry an `http(s)` link in `description`; 47 of 100 in a closed September window. Gamma also exposes
   `resolutionSource`, `automaticallyResolved`, `secondsDelay`, `gameStartTime`, `umaBond`, `umaReward`, `competitive`,
   `feeSchedule` and `negRiskOther` (field names only) (§CH124, §CH128).
6. **The "50-50 if cancelled" clause is a sports clause.** 14 of 100 closed September markets carry "50-50" in their
   rules and **all 14 have `gameStartTime`** (15 of the 100 do); 0 of 300 liquid open markets carry it. Parked with the
   sports decision (§4).
7. **Non-neg-risk multi-market events are not contests.** Of 200 open events with volume >= $10k, 146 have >= 3
   markets, 64 of those are `negRisk=false`, and only 5 of the 64 have contest-like titles; the 6 open "who will win"
   events are all neg-risk. Round 4's "census first" verdict on the non-neg-risk overround now reads **rejected** (§4).
   `negRiskAugmented` is false on every market and event probed; `negRiskOther` exists as a market field.
8. **The fine tick is the norm, not an extreme-price regime.** 261 of 300 liquid open markets report
   `orderPriceMinTickSize` 0.001 (100, 87, 74 by page) and 95 of 100 closed September markets. A note for the CH15/CH86
   record; nothing here depends on it.
9. **"Top AI model" closed events: 26 / 365 markets** (up to 28 members, 21 neg-risk); "Chatbot Arena" 4 / 74. The
   Hugging Face dataset API for the arena leaderboard returned 401, so leaderboard history needs the Wayback Machine or
   an own poller (§CH125).
10. **Hurricanes: 50 closed events / 147 markets** (up to 20 members); NHC's `CurrentStorms.json` is keyless
    (`activeStorms`; one storm active at the probe) (§CH126).
11. **Box office: "opening weekend" 50 / 192** (up to 27 buckets), "box office" 50 / 279 (all 50 neg-risk ladders)
    (§CH127).
12. **2026 midterms:** "Senate" active 50 events / 480 markets (10 titles name 2026), "Governor" active 50 / 661 (48
    neg-risk); election night is 2026-11-03, sixteen days from writing (§CH129).
13. **Kalshi's public market object** carries `created_time`, `open_time`, `close_time`, `expected_expiration_time`,
    `can_close_early`, `is_provisional`, `rules_primary` / `rules_secondary`, `settlement_timer_seconds`,
    `custom_strike`, `price_ranges` and **`mve_collection_ticker` / `mve_selected_legs`** (multivariate collections:
    public combo legs); `exchange/schedule` lists `standard_hours` and 0 `maintenance_windows` (§CH130, §4).
14. **The closed `btc-updown-15m` description probed names Binance as the resolution source, not Chainlink** (round
    5's probe 30 found `chainlink` true on a different market of the same family): the rule text varies by series and
    any oracle-quantisation idea is dead on arrival (§4).
15. **"How long" closed events: 40 / 292 markets** (36 neg-risk duration ladders; 7 titles are speeches or press
    conferences) (§CH122).
16. **GitHub's releases API is keyless** with `tag_name`, `created_at`, `published_at`, `draft`, `prerelease` (an arm of
    §CH124).

**The reading that steers this round.** Round 5 hunted where a professional price already exists (option chains,
Kalshi ladders), where a statistic determines the answer, and in unseen populations; CB12 took the best of it. What is
still unhunted, and what this round is about:
- **(a) Public clocks that run *during* the event** (a roll-call tally, a speech's transcript position, a duration
  ladder's own clock): the information arrives on a schedule everyone can see but nobody on the venue models
  (family B).
- **(b) Change detection on the source the rule names** (the article, the page, the release tag) rather than on a
  venue: the resolution is a public artefact and the watcher is generic (family C).
- **(c) Model-anchored classes nobody has joined yet**: barrier ladders under the reflection principle, grid rounding
  at inclusive thresholds, NHC probability products, box-office preview multiples, leaderboard survival (families A, D).
- **(d) The maker's class map**: the economics studies say the maker side is the only side where 0.3-0.6c effects could
  ever matter, and the one thing never measured is *where* adverse selection is small (family E).
- Two prospectives are boxed by the calendar (election night 11-03; the tail of the hurricane season) and one is a
  cross-venue object at a clock the sealed experiments do not use (birth). Everything is wallet-free and side-free.

**Data labels.** `A` = in AREPO's stores now: complete-universe 2h captures (touch, Gamma mid, `oneHourPriceChange`,
`last_trade_price`, `volume24hr`, `liquidity`, neg-risk ids, `closed`, `endDate`, `createdAt`) with the sidecar since
11 Oct 12:00Z (`accepting_orders`, `competitive`, `clob_rewards`, `rewards_max_spread`, `rewards_min_size`,
`fee_schedule`, `uma_resolution_statuses`, `series_slugs`, `parent_event_ids`, `order_price_min_tick_size`); book
sweeps twice per pass (touch, 1c and 5c depth); trade samples (hashed wallets); the live large-trade monitor (prints
>= $1k every 5 min with receipt and venue times, since October); the CB extract tables; the audited cross-venue pair
history (316 clean pairs, 10-minute); the IF-H2 ladder metadata (1,338 open rungs in 622 ladder events at 2026-10-12);
pmxt v2 hourly L2 event files 2026-04-13 to 08-10; the Binance 1-minute public archive (CB8-B). `P` = collectable
read-only from public keyless sources within a week (Gamma `description` and `resolutionSource`, Data API `/trades`
(newest 20,000 prints per market, not time-windowed) and `/oi`, CLOB `prices-history` with explicit bounds and `/book`,
the House Clerk's vote XML, Wikimedia EventStreams and the MediaWiki revisions API, the Wayback CDX API, NHC advisories
and products, GitHub releases, USGS FDSN, box-office trackers' pages, Kalshi's market and candlestick endpoints).
`N` = no known keyless source. **Sealed and not usable by anything here:** everything rounds 4 and 5 list (`h4_seal`,
`h5_*`, `h6_weather`, `h7_cb4_*`, `h8_*` including `h8_tail_b`, the `h9_flow` HOLDOUT, CB8-B's HOLDOUT weeks, CB8-H's
windows from 10-21, CB1-D's replication captures, the E009/E010 poller to 2026-11-03, E011 labels to 2026-11-11, the
J4-R window, CB9's K/D HOLDOUT events, CB9-P's Pyth frame and Stage-2 sessions, CB9-S's receipt strata, CB10-B's
`h10_brk`, CB10-D's `h10_dlad` and Deribit windows) plus every `h10_*`, `h11_*` and `h12_*` object named by CB9-CB12
(`h10_sign`, `h10_say`, `h10_shape`, `h10_exit`, `h11_pol`, `h11_attn`, `h11_wprints`, `h12_say`, `h12_prints`,
`h12_quake`, `h12_opt_live`, `h12_quake_live`). `h2_main` is worn and `h3_power` retired. Every historical test below
names a **fresh** fetch (`h13_*`), disjoint by market id *and* event / neg-risk / series key from every prior sample
and seal copy, with rows before `T_hist_end` 2026-10-01 (CB8's convention) or collected prospectively; none is bound to
the 2026-10-22 `T_seal` lane, and none runs ahead of any CB11 or `T_seal`-bound job.

**Hygiene that binds every idea.** Trade before `t`; scheduled anchors and source issuance times, never `closedTime` and
never the market's own move; outcomes that are public functions of public data are computed from the public data,
never read from Gamma's outcome fields (CB9-P's guard); event x resolution-week clustering for carries, session-day
clustering for dailies, storm / film / vote / event clustering where those are the units; tightness at both ends of any
mid-based target (J4-R) and print-based targets where prints exist; rule text as of first sighting (`textorig`) or the
clarification-marker exclusion; hashed wallets only, and no idea here needs a wallet at all; the cumulative test count
(M3); frozen models (hazards, multiples, grids, classifiers) are fitted on data before a stated date and tested after
it. Category stays a parameter (sports scope is the user's call; nothing here is sports-only; the sports-only
candidates are in §4).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = an afternoon on existing data or a small
keyless fetch, 5 = new collector plus weeks). My judgement, not measurements. Cost conventions as rounds 1-5: taker fee
`rate*p*(1-p)` per leg (crypto 0.07; sports 0.03-0.05; politics/finance/tech 0.04; economics/culture/weather 0.05;
geopolitics 0; makers 0, rebate 15-25% of the fee-equivalent of own fills); median spreads by price band
4.1 / 3.0 / 2.2 / 3.0 / 2.5c; liquid (>= $100k) round trip 1.8c; median round trip 4.5c; one-leg hold-to-resolution
pays the half-spread and the fee once; passive entry has paid 1-7c of adverse selection in every study so far.

---

## 1. Map: where money might be, given the survivors and the nulls

| Family | What the evidence and the probes suggest | Money route |
|---|---|---|
| A. Path-settled structure | 1,100+ barrier markets priced by a crowd that thinks in terminal probabilities; inclusive thresholds on gridded sources carry an atom the wording hides | hold-to-resolution taker on the model side; model-anchored maker on far rungs |
| B. Public clocks during the event | roll-call tallies, speech transcripts and duration ladders all have a clock the crowd can see and does not price | taker at stale asks while the clock runs; maker selling decaying words and dead buckets |
| C. Change detection on named sources | edits and page changes are the resolution's first public trace; pageviews were 48 h late, edits are not | taker at stale asks in the minutes after the change; alert-then-read as the safe form |
| D. Model-anchored classes nobody has joined | leaderboards, NHC products and preview multiples are public, timestamped, probabilistic anchors in classes no batch has touched | hold-to-resolution taker when the anchor disagrees by more than fee plus spread |
| E. Where to make | every economics study pooled classes; the maker's loss is a class average | maker only in the classes whose mark-outs sit below the half-spread |
| F. Calendar-boxed prospectives and the pair at birth | one night of dozens of races; pairs whose Polymarket book is born under a standing Kalshi price | pre-registered sign on the night; taker toward the older venue in the first hour |

---

## 2. Hypotheses

### A. Path-settled structure (parents CH89, CH76, CH30; CB10-D is the sealed neighbour)

**CH118. Barrier-versus-terminal confusion in "reach / dip to $X by <date>" ladders: under a driftless log-diffusion a
touch (barrier) probability is about twice the terminal probability for far strikes (the reflection principle), the
ratio of touch probabilities across horizons for the same strike is a one-parameter function of volatility, and the
two-sided race form ("hit U before L") has a volatility-free fair value; the crowd prices these ladders as if they were
terminal ("close above") markets, so far-strike barrier YES is underpriced and the shortest horizon is overpriced
relative to the longest in a predictable way.**
- Mechanism: for a log-price diffusion with zero drift, `P(touch B by T) = 2 * (1 - Phi(|ln(B/S)| / (sigma sqrt T)))`
  while `P(S_T beyond B) = 1 - Phi(...)`; the factor approaches 2 for far strikes and short horizons. A race market
  "hit U before L" has `P = ln(S/L) / ln(U/L)`, independent of sigma. Three distinct, parameter-light, falsifiable
  predictions. Who pays: retail buying near strikes ("will it dip to 100k this week") priced with the daily ladders'
  terminal intuition, and reward bots centred on the mid. Why it persists: path-dependent payoffs are not what the UI's
  "chance" number invites, and no bot on the venue prices touch probabilities as far as AREPO has seen (CB10-D anchors
  *terminal* ladders only).
- Test (`A`+`P`, historical). Fresh frame `h13_touch` = closed "reach" / "dip to" / "hit" ladders on BTC, ETH, SOL and
  any equity or commodity names, ends before 2026-10-01, found by a Gamma date walk (not the capped search); strike `B`,
  horizon and resolution exchange from the rule text (`textorig`); the spot path from CB8-B's Binance 1-minute archive
  (`A`; an exchange-wick basis check against the named exchange's candles); realised sigma from the trailing 30 days
  frozen at each decision time; prices from CLOB `prices-history` with explicit bounds (1-minute) at daily decision
  times. Outcome computed from the public path (touched or not), never from Gamma's field. Primary: slope of `(Y - p)`
  on `(q_touch - p)` with `q` from the reflection formula and the J4-R tightness filter. Secondary: the cross-horizon
  test (same strike, two horizons: the hypothesis predicts the shorter horizon's crowd-implied sigma is higher) and
  the race arm's slope (only if >= 30 race markets exist at census; 3 of 50 "before" events were race-form). Clusters
  = underlying x week. Economic: buy the model side at the recorded ask when `|q - ask| >= 5c` and `q` in [0.05,
  0.95]; hold to touch or expiry; net per share, clustered. Population >= 1,100 markets from the capped searches alone,
  probably 3,000+ on a date walk; floors 0.30 on the slope and 1.0c on the net.
- Data: `A` (Binance archive), `P` (CLOB history, Gamma texts). A weekend of fetching; under 1 GB.
- Economics: crypto taker fee `0.07*p*(1-p)` <= 1.75c; median spread 2.2-4.1c by band; hold-to-resolution pays one
  half-spread and one fee; the model's own error from sigma misestimation is 3-6 pp for mid-range strikes (report
  sensitivity to sigma +/- 20%); break-even gap about 4c; the maker variant posts bids at `q - 2c` on far strikes and
  waits.
- Kill: slope CI includes 0 or point < 0.30; or the cross-horizon test shows the crowd's implied sigma flat or
  decreasing in horizon (the crowd already prices touch); or the economic net <= 0 at the 5c filter.
- Leakage/confound: drift (a crypto trend) moves touch probabilities asymmetrically for up and down barriers (report
  "reach" and "dip to" separately; +/- 50% a year changes far-strike touch probabilities by a few pp); jumps; the
  resolution exchange's wick versus Binance's; survivorship if only resolved-YES ladders are easy to find (date walk,
  both outcomes); sigma frozen before each decision time.
- Novelty: CH89/CB10-D anchor terminal ladders with Deribit; CH76/CB8-B the terminal minutes; CH30 the 15-minute
  digital. New: the barrier payoff, the reflection-principle ratio, the vol-free race identity and the cross-horizon
  consistency test. N 4, EV 4, C 2.

**CH119. Inclusive-threshold grid mass: when a resolution source reports on a grid (USGS magnitudes to 0.1; review and
approval percentages to 1; macro prints to 0.1 pp; counts to 1) and the question says "X or higher / or more / at
least", the point mass at the threshold itself belongs to YES; the crowd prices the threshold as if the variable were
continuous ("above X"), so the inclusive side is underpriced by about the grid mass, which is large exactly where the
density is steep (the 7.0 grid point carries about 30% of the [6.85, 7.15] magnitude band) and small where it is flat;
the sign reverses for "more than / above" wording.**
- Mechanism: a grid of step `h` with density `f` gives mass about `h * f(X)` at the threshold; under Gutenberg-Richter
  with `b` about 1 the mass at 7.0 is about 20% of `P(M >= 7.0)`; for a one-decimal macro print with sd 0.1 pp around
  consensus the atom at the consensus value is 30-40% of the inclusive side; for integer review scores near a mode,
  3-6%. The difference between ">=" and ">" is exactly what a hurried reader skips, and the venue does not display the
  inequality type. Who pays: buyers of the exclusive side at prices that ignore the atom. Why it persists: it is a
  reading edge of a few pp inside otherwise sensibly priced markets.
- Test (`P`, historical, pooled across classes with class effects). Frame `h13_grid` = closed single-threshold markets
  from the "or higher / or more / at least / more than / above / over" searches by date walk (>= 150 markets in the
  capped searches alone). Earthquakes (553 markets before 2026-10-01 per CB12) enter **only** if disjoint by event from
  CB12-E's frame; otherwise the class is dropped. Each market gets (i) the inclusive flag from the rule text as first
  sighted, (ii) the grid step from the named source, (iii) a frozen class model's density at the threshold giving the
  atom `m` (earthquakes: declustered regional rate and GR `b` frozen before the census; percentages: the aggregator's
  empirical score distribution; macro: consensus +/- a class sd; counts: Poisson at the running rate). Decision times:
  listing + 24 h and T - 48 h. Primary: slope of `(Y - p)` on `m * s`, `s = +1` for inclusive YES wording, `-1` for
  exclusive, with the J4-R tightness filter; clusters = event (and release for macro). Economic: hold the atom's side
  to resolution at the recorded ask when `m >= 3 pp` after fee. Floors: 0.25 on the slope, 1.0c on the net.
- Data: `P` (Gamma texts, CLOB history, USGS catalogue, aggregator pages, release archives). An afternoon plus the text
  job.
- Economics: fee `0.04-0.05*p*(1-p)` <= 1.25c; one half-spread; the edge is the atom (2-10 pp where densities are
  steep), so only steep classes clear 4c; capacity is the rung's depth.
- Kill: slope CI includes 0; or the atom-weighted gap is already in the price in every class with >= 20 markets; or
  fewer than 60 units with `m >= 3 pp`.
- Leakage/confound: first print versus revision (USGS revises magnitudes within hours; the rule's "as first reported"
  or "final" clause decides; CH75/CH108's first-print rule); wording without an inequality ("hits 7.0"); macro releases
  are few independent clusters (about 30 per statistic; CB10 dropped CH90 for that reason, so macro is a secondary arm,
  never primary); creators may place thresholds on round grid points where the atom is largest (selection, not
  leakage).
- Novelty: CH28/CH90 (scheduled statistics) and CH108 (running counts) are about *when* the value is known; this is
  about the *support* of the reported value. N 4, EV 3, C 1-2.

### B. Public clocks that run during the event (parents CH112, CH105, CH106)

**CH120. Live roll-call tally lead: House (and Senate) floor votes are open for 15-45 minutes while the yea/nay tally
accumulates on the Clerk's public page; passage is near-certain minutes before the gavel, and Polymarket's "Will the
House pass X by <date>" markets reprice after the gavel or after the headline. The lead is a public clock, not a leak.**
- Mechanism: roll-call votes display the running tally in real time (the Clerk's live vote page and C-SPAN); the
  per-vote XML is published with `action-time` at the close (fact 3). Passage markets ("pass" 50 closed events / 99
  markets, 21 titles naming the House, the Senate or a bill; "Senate vote" 50 / 1,245, mostly confirmation ladders)
  trade on headlines. Who pays: holders who sell into the first visible move and makers whose asks stay under 0.9
  during the vote. Why it persists: votes are late in the US evening, the tally page is unfamiliar, and passage markets
  are a few thousand dollars deep.
- Test. **Stage 1 (`P`, historical descriptive):** `h13_votes` = closed passage markets (House and Senate; nominations
  as a second class) mapped to the rule-named bill; the Clerk XML (`rollcall-num`, `legis-num`, `action-date`,
  `action-time`) or the Senate's public vote page (its XML refused the probe UA) gives the gavel time; CLOB
  `prices-history` at 1-minute fidelity with explicit bounds around it. Statistics: minutes from the gavel to the first
  price >= 0.9 (or <= 0.1); the share of the terminal move completed *before* the gavel (during the open vote); the
  asks available (Data API `/trades`, newest 20,000 prints suffice for these thin books). **Stage 2 (prospective):** a
  poller of the Clerk's live tally every 30 s during open votes with receipt times, and the CLOB book every 30 s for the
  mapped markets; unit = vote x market; target = fills available at <= 0.85 once the tally crosses the majority with
  >= 10% of members outstanding; clusters = vote. Population: a few dozen votes in two months; descriptive first.
- Data: `P` (Clerk XML keyless; CLOB history; Data API). Small.
- Economics: politics fee `0.04*p*(1-p)`; the gap is 10-40c on the event; capacity $1-10k per vote; the route is taker
  at stale asks, so it works only if Stage 1 shows asks persisting > 2 minutes after the majority is reached.
- Kill: Stage 1 shows the terminal move complete before the majority is reached (whip counts and the floor schedule
  already in the price); or median stale-ask life < 60 s; or fewer than 20 mapped votes.
- Leakage/confound: votes held open for arm-twisting can reverse (the tally is not the result until the gavel; report
  the reversal rate); the market may resolve on enactment or a later step (rule reading); no live Senate XML.
- Novelty: CH106's calendars say *which day*; this is the *minute-by-minute* public clock inside the day. N 4, EV 3,
  C 2.

**CH121. Intra-speech hazard decay for mention baskets: once a speech starts, the probability that an as-yet-unsaid
word is said by the end falls with elapsed time according to the within-speech position distribution of first mentions
in this speaker's past transcripts (topical words appear early); the crowd holds unsaid words' prices flat until the
final minutes, so selling unsaid-word YES progressively during the speech pays.**
- Mechanism: in "Will X say Y during Z" events (50+ closed events / 970 markets with up to 44 words in round 5's probe;
  1,472 mention-basket markets in March 2026 per CB12) each word is a hazard process on the speech clock. From public
  timestamped transcripts of the speaker's past speeches, the empirical CDF `F` of first-mention position (as a
  fraction of speech length) is computable per word class (policy nouns early; names and jokes diffuse). Conditional
  survival `P(said by end | unsaid at t) = (F(1) - F(t)) / (1 - F(t))` scaled by the per-word base rate (CH32's object)
  and the remaining time. Who pays: holders waiting for "he will get to it", and makers whose quotes ignore the clock.
  Why it persists: running the model needs only the clock and whether the word has been said, which anyone watching
  knows; nobody on the venue re-prices 40 words every two minutes.
- Test (`P`, historical). `h13_speech` = closed mention events with a public timestamped transcript (official
  transcripts, C-SPAN captions, the resolver's own source per rule) and a scheduled start; first-mention times per word;
  CLOB `prices-history` at 1-minute fidelity during the speech. Unit = word x 5-minute checkpoint while unsaid.
  Primary: slope of `(Y - p_t)` on `(q_t - p_t)` with `q_t` from the position model fitted on speeches before
  2026-06-01 and tested after; the J4-R tightness filter (these books are mid-like). Clusters = event. Economic: paper
  maker asks at `max(p_t, q_t + 2c)` on unsaid words after fraction 0.5, filled at recorded prints; and a taker variant
  buying NO at the ask when `p_t - q_t >= 8c`. Floors: 0.30 on the slope, 1.0c per filled share. Population 60-100
  events with transcripts, 1,500-3,000 word-units. **Overlap declared:** CB12-M uses the same events at start - 2 h and
  - 24 h; this uses in-speech checkpoints; if the challenger objects, the frame is events after CB12-M's frame end.
- Data: `P` (transcripts keyless; CLOB history). A weekend.
- Economics: culture fee `0.05*p*(1-p)` <= 1.25c; unsaid words trade at 0.10-0.40 during speeches with 3-4c spreads;
  the decay from 0.3 to 0 over 40 minutes is 30c of expected move against 3-5c of cost; capacity per word $0.5-5k.
- Kill: slope point < 0.30; or the price already tracks the model (the crowd re-prices on the clock); or transcripts
  exist for < 30 events.
- Leakage/confound: speech length unknown ex ante (use the scheduled slot; sensitivity); Q&A after the prepared text
  counts under some rules (read per event); transcript timestamps are coarse (30-60 s); words said in the first minute
  are information events, not decay (exclude the first 5% of the clock); the position model is speaker-specific.
- Novelty: CH112/CB12-M is the pre-event basket sum; CH32 the per-word base rate. New: the speech clock as the state
  variable and a per-word survival model. N 4, EV 3, C 2.

**CH122. Duration-ladder clock: "How long will X last" ladders (40 closed events / 292 markets; 36 neg-risk) have
buckets that die deterministically as the clock passes and live buckets whose fair values are a conditional hazard of a
public, repeatable process (shutdowns, strikes, speeches, trials, missions); the crowd leaves dead buckets with positive
asks and prices live buckets with a flat hazard.**
- Mechanism: once elapsed time exceeds a bucket's upper edge, its YES is worth 0 under the rule; the remaining
  buckets' probabilities are survival ratios; where an empirical duration distribution exists (past shutdowns, this
  speaker's past speeches, past strikes), the conditional hazard is public. Who pays: holders of dead buckets who never
  sell, makers quoting the mid with no clock, and buyers of the "soon" bucket in a process with increasing survival
  (the longer it lasts, the longer it lasts). Why it persists: duration ladders are rare enough that no bot prices them,
  and the UI shows no clock.
- Test (`P`, historical). `h13_dur` = closed duration ladders by date walk; for each, the public clock (start from the
  rule; end from the rule's source), the bucket edges, CLOB `prices-history` at hourly fidelity. Dead-bucket
  descriptive: price and ask presence after the edge passes (a count, not a route, unless asks > 1c persist). Live-bucket
  calibration: slope of `(Y - p)` on `(q - p)` with `q` from an empirical hazard frozen from the class history before
  the event (or a log-logistic fitted on the class's earlier ladders), daily checkpoints. Clusters = event. Economic:
  sell YES (post asks) on the bucket the hazard says is overpriced by >= 5c; hold to resolution; also the taker NO.
  Floors 0.25 on the slope, 1.0c net; population 30-40 events, 250-300 markets.
- Data: `P`. An afternoon on the frame; small hazard models.
- Economics: fee `0.04-0.05*p*(1-p)`; spreads 3-4c; capacity $1-10k per bucket; a dead-bucket residual, if any, is
  riskless to the seller but only as large as the residual asks (expect cents).
- Kill: < 25 events with a usable clock; or slope < 0.25; or the dead-bucket residual is 0 in > 95% of bucket-hours
  (then only the hazard arm remains and it needs a class with >= 10 events).
- Leakage/confound: the end time's definition (announcement versus effect); class hazards fitted on few events
  (shutdowns: about 20 since 1976); the speech sub-class (7 events) shares speakers with CH121 but not its object;
  survivorship in which ladders the venue lists.
- Novelty: CH05/CH06 (date-rung hazards) ask *whether by a date*; this is *how long*, with deterministic deaths and a
  survival model. N 3, EV 2-3, C 1-2.

### C. Change detection on the source the rule names (parents CH97/CB11-A, CH107, CH109)

**CH123. Wikipedia edit-stream lead for unscheduled personnel and status markets ("Will X resign / be out as / be fired
/ be indicted by <date>"): the subject's article receives a burst of edits within minutes of the event (for deaths and
resignations often within the minute of the first wire), the EventStreams feed is public with second-level `meta.dt`,
and Polymarket reprices over 5-60 minutes because the relevant books are thin and nobody watches them at 03:00Z.**
- Mechanism: CB11-A found Wikipedia *pageviews* publish with about a 48-hour lag, which killed them as a timing
  signal; *edits* are the pageview's cause and the `recentchange` stream is real-time (fact 4). A burst (>= 3 edits by
  >= 2 distinct non-bot users in 10 minutes with a length change or an infobox edit) on the subject's article is a
  public, timestamped marker. Who pays: stale asks in markets priced 0.05-0.40 before the event, and holders who sell
  the first move. Why it persists: the join (market to article) is a chore; events are rare per market; the feed is
  noisy.
- Test. **Stage 1 (`P`, historical):** `h13_edits` = closed "resign" (50 / 93), "out as" (50 / 95), "fired",
  "indicted", "dies" markets by date walk, both outcomes; the subject article from the question's named entity (a
  manual map for the frame; a frozen rule for the prospective); the article's revision history (MediaWiki API
  `prop=revisions`, keyless, exact timestamps and byte sizes) over the market's life; CLOB `prices-history` 1-minute
  with explicit bounds. Statistics: for YES-resolved markets, the lead of the first burst over the first 1-minute print
  >= 0.9 (distribution; median; share with lead > 5 minutes); for all markets, the false-burst rate (bursts with no 20c
  move within 2 hours) and the detector's precision, with the burst rule tuned on the first half of the frame only.
  **Stage 2 (prospective):** the stream filtered to the mapped articles of open markets; the CLOB book at burst + 1, 5,
  15 minutes; unit = burst; target = fills at recorded asks and the 2-hour print-based move; clusters = subject.
- Data: `P` (MediaWiki API; EventStreams; CLOB). A weekend for Stage 1; a small always-on client for Stage 2.
- Economics: politics/culture fee <= 1.25c; gaps of 20-60c on resolution-determining events; capacity is the stale
  asks ($1-20k); each false positive traded blind costs a 4-5c round trip, so precision is the economic parameter.
- Kill: median lead <= 1 minute (the crowd is as fast as the editors) or share with lead > 5 minutes < 25%; or
  precision < 0.3; or < 40 mapped YES events.
- Leakage/confound: edits follow X/Twitter and the market may move on the rumour before any edit (that is in the lead
  distribution, not a leak); vandalism and reverts (filter `bot`, revert comments, protected pages); deaths are a
  distinct, faster class (report separately); the burst rule frozen before the prospective; no wallet needed.
- Novelty: CH97/CB11-A (pageviews) is the parent; the clock (edits, second-level) and the object (burst lead over the
  print) are new; CH107 (EDGAR) and CH109 (aggregators) are the siblings. N 4, EV 3, C 2.

**CH124. Named-source page-change lead: 16-20 of each 100 liquid open markets and 47 of 100 closed September markets
name the exact URL that will carry the resolving fact; a keyless watcher that hashes the main content of each named page
every 5-15 minutes detects the change (a new release, a table update, a release tag with `published_at`, a status
page) before the crowd for low-attention sources, and stale asks persist for minutes to hours in those markets.**
- Mechanism: the venue says where to look; many named pages are agency tables, IR pages, GitHub releases, league pages
  and registries that nobody polls; the change *is* the resolution. Who pays: makers whose asks do not move because
  they do not watch the page, and holders of the other side. Why it persists: each source is tiny and bespoke; only a
  generic watcher makes the population large.
- Test. **Stage 1 (`P`, census plus historical where archives exist):** `h13_src` = open markets with a URL in
  `description` (36 of 300 liquid open markets probed), classified by source type (agency, company IR, GitHub,
  aggregator, registry, news); for the closed September window (47 of 100) the Wayback CDX API or GitHub's
  `published_at` gives a change timestamp, aligned to CLOB 1-minute history: the lead of the page change over the first
  print >= 0.9 / <= 0.1. **Stage 2 (prospective):** the watcher (robots.txt, 5-15 minute cadence, conditional GETs with
  `If-None-Match` / `If-Modified-Since`, main-content hash) plus the CLOB book at change + 1, 5, 15, 60 minutes; unit =
  change; target = fills at recorded asks and the 2-hour print move; clusters = source domain. Descriptive first; the
  economic test only in source types where Stage 1 shows leads > 5 minutes.
- Data: `P`. A week to build; small on disk.
- Economics: fee <= 1.25c; gaps 10-50c on resolution; capacity the stale asks; false changes cost nothing under
  "alert, then read" and a round trip if traded blind: the test counts both.
- Kill: < 30 watchable (non-JS, stable) named sources among liquid open markets; or Stage 1 median lead <= 2 minutes in
  every source type; or precision < 0.3.
- Leakage/confound: JS-rendered pages (unwatchable by hash; counted out); unrelated changes (diff the content region);
  embargoed releases where page and wire change together (zero lead); sports feeds dominate the September window (15
  of 100 markets carry `gameStartTime`; category is a parameter, sports reported separately).
- Novelty: CH107 (EDGAR), CH109 (aggregators) and CH106 (calendars) each watch one named class; this watches *whatever
  the rule names*, with GitHub releases (`tag_name`, `published_at` verified keyless) as the typed arm that replaces the
  rejected "exchange-listing announcements" idea. N 3, EV 3, C 3.

### D. Model-anchored classes nobody has joined (parents CH108, CH109, CH99, CH27)

**CH125. Leaderboard incumbency hazard for "top AI model at month-end" events (26 closed events / 365 markets; 4 / 74
"Chatbot Arena"): the incumbent's probability of still leading at the deadline is an empirical survival function of the
leaderboard's own public history (displacement frequency per week, new-entry rate), and the crowd prices the incumbent
on recency and lab rumours, so the deviation from the survival function predicts resolution.**
- Mechanism: a public, versioned leaderboard changes in batches (new models land together; style control and tie
  rules are published); over 2024-2026 the top spot changed hands at a measurable rate with an identifiable hazard
  shape (release, short-lived lead, consolidation). The month-end event is a survival question. Who pays: buyers of a
  challenger on a rumour with less than a week left, and incumbent holders who sell on any release headline. Why it
  persists: the history is scattered (the dataset API returned 401; the Wayback Machine and the operator's posts hold
  it) and each event is small.
- Test (`P`, historical). `h13_lb` = closed top-model events by date walk (26+); the leaderboard's state and change
  dates from Wayback snapshots (keyless CDX) frozen into a displacement history before the census; decision times
  T - 21, 14, 7, 2 days; `q = S(remaining days | incumbent age, release-calendar density)` from the hazard fitted on
  events before 2026-04-01 and tested after; unit = event x checkpoint for the incumbent's market and, as a second arm,
  for each top-3 challenger. Primary: slope of `(Y - p)` on `(q - p)`; clusters = event-month. Economic: buy the model
  side at the recorded ask when `|q - ask| >= 6c`, hold to resolution; net per share. Floors 0.30, 1.0c. 26-40 events,
  100-160 incumbent units: thin but clean.
- Data: `P` (Wayback; CLOB history; Gamma texts). An afternoon plus the reconstruction.
- Economics: tech fee `0.04*p*(1-p)`; spreads 2-3c; capacity $5-50k on the incumbent; holds of days.
- Kill: slope < 0.30; or the displacement hazard is unstable across years (then no model is frozen honestly); or < 20
  events after excluding months with a methodology change.
- Leakage/confound: labs' release timing is private information held by part of the crowd (which would make the crowd
  *better* than the hazard; the test is two-sided); tie and style-control clauses; the operator's methodology changes
  (exclude those months); the creator's listing choices reveal expectations at listing.
- Novelty: CH108/CH109 are running counts and aggregator formulas; this is a *survival* model of a ranking with its own
  public history, in a class no batch has touched. N 4, EV 3, C 2.

**CH126. NHC probability-product anchor for hurricane markets (50 closed events / 147 markets; `CurrentStorms.json`
keyless): the National Hurricane Center publishes, at fixed advisory times (03/09/15/21Z), wind-speed probabilities by
location, intensity forecasts and the cone; landfall-and-category markets are functions of those products; the crowd
prices on headlines and the previous advisory, so the sign of (NHC-implied minus price) at advisory + 15 minutes
predicts resolution.**
- Mechanism: the products are probabilistic by construction (the wind-speed probability product gives P(>= 64 kt
  within 120 h at a point)), free and timestamped; the mapping from product to question is a frozen rule per question
  type (landfall in state S as category >= k; peak category; the named-storm count arm with the seasonal outlook as
  prior). Who pays: retail buying "Cat 5 landfall" on a dramatic cone image, and holders slow to sell when the track
  shifts. Why it persists: a few storms a season, a dozen markets each, and the join between the probability grid and
  the state polygon is work.
- Test (`P`, historical). `h13_nhc` = closed hurricane markets of the 2024-2026 seasons by date walk; NHC's advisory
  archive (keyless) per storm: wind-speed probability products and forecast advisories at each advisory time; the
  frozen mapping gives `q` at advisory + 15 min; CLOB `prices-history` at 1-minute with explicit bounds at the same
  minute; outcome from the NHC tropical cyclone report, never from Gamma. Unit = market x advisory; clusters = storm
  (10-20 per season; 30-50 in the frame) with season as the outer layer. Primary: slope of `(Y - p)` on `(q - p)` with
  the J4-R tightness filter. Economic: buy the model side at the recorded ask when `|q - ask| >= 8c`; hold to
  resolution. Floors 0.30, 1.0c net; a prospective arm during the rest of the 2026 season (one storm active at the
  probe).
- Data: `P`. A week for the mapping and the archive walk.
- Economics: weather fee `0.05*p*(1-p)`; spreads 3-4c; holds of days; capacity $2-20k per market; the anchor's error is
  the NHC's own (their verification reports are public).
- Kill: slope < 0.30; or < 25 storm clusters with mapped markets; or the mapping is ambiguous for > 30% of questions.
- Leakage/confound: the product's issuance timestamp + 15 minutes, never the market's move; "landfall" is a point
  concept in rules and a probability field in products (the mapping is the risk); storm clusters are few and
  climatology errors are season-level.
- Novelty: CH27/CH57 (daily temperature; model-run lag) are the weather parents, sealed in `h6_weather`; hurricanes and
  the NHC's *probabilistic* products are untouched by any batch. N 3, EV 3, C 2-3.

**CH127. Preview-multiple anchor for opening-weekend box-office ladders (50 closed "opening weekend" events / 192
markets; 50 "box office" / 279, all neg-risk ladders): Thursday-preview grosses are public on Friday morning and the
preview-to-weekend multiple is a stable public function of class (family and animated high; fan-driven low; horror in
between), so a Friday 14:00Z model gives bucket probabilities two days before the Sunday estimate; the crowd's Friday
prices still carry Thursday's tracking.**
- Mechanism: the weekend number is close to a deterministic function of the preview number given the class multiple,
  with a known dispersion; the Sunday studio estimate (the usual resolution source; Monday actuals as the revision) is
  two days away; the ladder trades in between. Who pays: holders of Thursday's bucket and makers centred on Thursday's
  mid. Why it persists: multiple tables are trade knowledge published in prose, and the ladders are small.
- Test (`P`, historical). `h13_bo` = closed opening-weekend ladders by date walk (2025-06 onwards); preview and
  weekend figures from the public trackers' pages (keyless HTML; the rule-named source for the outcome; the
  first-print rule for Sunday estimate versus Monday actual); a class multiple model frozen on films before 2026-03-01
  and tested after; `q` per bucket from a lognormal around preview x multiple with the class dispersion; CLOB
  `prices-history` at 1-minute at Friday 14:00Z and Saturday 14:00Z. Unit = film x bucket x checkpoint; clusters = film
  (60-120 films). Primary: slope of `(Y - p)` on `(q - p)`. Economic: buy the model's modal bucket(s) at the recorded
  ask when `|q - ask| >= 6c`, hold to resolution; sell (NO at the ask) buckets the model puts below 2% when priced above
  8c. Floors 0.30, 1.0c net.
- Data: `P`. Two afternoons.
- Economics: culture fee `0.05*p*(1-p)`; ladder spreads 3-4c; capacity $1-10k per bucket; a two-day hold.
- Kill: slope < 0.30; or the Friday price already equals the preview model within 3c on average (the crowd includes
  box-office professionals and the trades' Friday-morning projections are public, so the edge is only the crowd's lag
  to them); or < 40 films.
- Leakage/confound: previews publish at different Friday times (tracker publication timestamp + 1 h); Sunday estimate
  versus Monday actual near a bucket edge (the resolution clause decides); class labels frozen before the census; wide
  dispersion for event films (report by class).
- Novelty: CH108 (running counts) and CH109 (aggregators) are the parents in spirit; box office is in no batch and the
  preview multiple is a public, class-specific statistic, not a running count. N 3, EV 3, C 1-2.

### E. Where to make: the class map (parents CH16, CH40, CH43, CH63, CH116)

**CH128. Toxicity by resolution class: the adverse selection a passive quote suffers (mark-out of a paper touch fill at
2 h and 6 h, side-free, wallet-free) differs by the market's *resolution class* (public-statistic, path-settled,
scheduled-event, unscheduled-news, sports-feed); in the public-statistic and path-settled classes it sits below the
half-spread, so a maker who quotes only there nets positive before rewards, while the unscheduled-news class is where
the economics studies' -2.5 to -3.7c came from.**
- Mechanism: the information that hurts a maker arrives differently by class: in public-statistic markets on a
  schedule everyone sees (the maker steps aside); in path-settled dailies as the spot price (a maker with the spot feed
  is never surprised); in unscheduled-news markets as a print from someone who read the wire first. The 95 economic
  cells and SB2 J2 pooled across classes; the class axis has never been the unit. Gamma's `resolutionSource`,
  `automaticallyResolved`, `secondsDelay`, `gameStartTime` and the rule text give a frozen classifier that reads no
  outcome. Who pays in the low-toxicity classes: retail and the reward bots' own hedges. Why it persists: the makers
  that exist (reward bots) quote by reward band, not by class.
- Test (`A`, historical). The live large-trade monitor's prints (>= $1k since October, receipt and venue times) and
  the CB extract tables; the captures' touch prices at the preceding pass (2 h cadence; the sidecar's `competitive` and
  rewards fields); a frozen class label per market from the fields above plus a text rule (`textorig`); the paper fill
  = a print that crosses the capture's touch within the pass; mark-out at 2 h and 6 h from the next captures' Gamma mid
  and from print-based moves where prints exist. Primary: class means of the mark-out with the half-spread subtracted;
  the hypothesis predicts public-statistic and path-settled >= 0 after the half-spread and unscheduled-news < 0;
  clusters = event x day, two-way with hour-of-day. Economic: net per paper fill by class; floors 0.5c on the class
  difference and the sign condition for the maker classes. Population: tens of thousands of prints since October; >= 500
  fills is the floor for a class to be reported.
- Data: `A` only (no fetch). One afternoon on host files once the class labeller is frozen.
- Economics: maker fee 0; the rebate (15-25% of the fee-equivalent in fee-on classes) is ignored in the primary; the
  quantity *is* the net; capacity is the class's depth at the touch (`rewards_min_size`, the 1c/5c sweeps).
- Kill: no class with >= 500 fills shows a non-negative net after the half-spread; or class differences < 0.5c; or the
  2 h cadence makes the mark-out uninformative (the print-based 2 h move must agree in sign with the capture-mid move in
  > 70% of fills).
- Leakage/confound: the capture's touch is up to 2 h old when the print arrives (the paper fill is optimistic; J4-R
  tightness and the print-based mark-out are the guards); reward-bot fills inflate low-toxicity volumes without being
  fills a human maker would get (CH116's band-stripping as the robustness layer); class labels need the frozen rule;
  sports is one class and stays a parameter.
- Novelty: CH16 (reward per adverse selection), CH40 (late-life schedule), CH43 (surprise filter), CH63 (specificity)
  are states and times; the class axis and the field-based classifier are new, and the result reads *where* the
  economics studies' negative numbers come from. N 3, EV 4, C 1.

### F. Calendar-boxed prospectives and the pair at birth (parents CH38, CH73, CH106)

**CH129. Election-night reporting-order drift (2026 midterms, 3 November): the order in which counties and vote modes
report is known in advance from 2022 and 2024 timelines and state counting rules, early partials bias the live price in
a state-specific, predictable direction (the mirage and the shift), and a frozen pre-night model of expected drift from
25% to 90% reporting predicts the sign of the Polymarket price path in each second-tier state race. One night, dozens of
races, heavy professional competition: a case study with a pre-registered sign, not a programme result.**
- Mechanism: in 2020-2024 the direction of the count's drift by state was predictable from which jurisdictions report
  first and whether early votes are counted before or after election-day votes; the Polymarket crowd in 2024 was fast
  in liquid races and slower in governor and House races. Populations now: "Senate" active 50 events / 480 markets (10
  titles name 2026), "Governor" 50 / 661 (fact 12). Who pays: buyers of the early-leading side at 25-40% reporting in
  races whose later-reporting jurisdictions lean the other way. Why it persists: it does not in liquid races; the
  hypothesis is about the second tier.
- Test (prospective, one night, plus an ex-post audit). Before 2026-11-01 freeze, per state race listed on Polymarket:
  (i) the expected reporting order from public 2022/2024 timelines, (ii) the predicted sign of the drift from the first
  25% to 90% reporting, (iii) the tier (liquid / second tier by `liquidity`). On the night: the CLOB book every 60 s
  for the mapped markets with receipt times, and the public state result feeds with the reporting percentage (the SoS
  JSON endpoints vary by state and were not probed; the AP's are not keyless; the audit can use certified county
  results afterwards). Unit = race; target = realised drift sign and size; statistic = share of races with the
  predicted sign (binomial against 0.5) and the mean drift in the predicted direction; clusters = race *and* the one
  night (the primary limitation, stated as such). Economic: buy the predicted side at 30% reporting at the recorded
  ask, exit at 90% at the recorded bid; net per share. Ex-post: the 2024 paths from CLOB history against the same
  model, as a plausibility check only (hindsight-fitted).
- Data: `P` plus a one-night CLOB collector (under 1 GB).
- Economics: politics fee <= 1c; spreads 1-3c in liquid races, 5-10c in the second tier; gaps of 10-30c during the
  count; capacity large where the edge is probably zero and small where it might exist.
- Kill: the pre-night model cannot assign a sign to >= 25 races; or the sign share is <= 0.6 on the night; or the drift
  in the predicted direction is < 5c.
- Leakage/confound: a national swing moves every race the same way (the night is one cluster for that component; the
  design predicts *relative* drift by reporting order, which is orthogonal only if the model is frozen); professionals
  with the same model dominate liquid races; feeds differ in freshness; "called" versus "resolved" (the test is the
  price path, not resolution).
- Novelty: no round or batch has an election-night object; CH106's calendars are days; this is the count clock inside
  the night. **Calendar-forced:** either the collector and the frozen signs exist by 11-01 or the idea waits for the
  next cycle (runoffs and specials give a few more nights). N 3, EV 3 (large per unit, one night), C 2.

**CH130. The pair at birth: when Kalshi lists a question first (its `created_time` / `open_time` precede Gamma's
`createdAt`), Polymarket's opening price is set by a thin crowd while a standing Kalshi price already exists, so the
opening deviation predicts the first-day Polymarket drift toward Kalshi; this is level convergence at listing, not the
sealed 10-minute lead.**
- Mechanism: the two venues list the same question days apart; Polymarket's first prints are the seeding trader's and
  the first retail (CH22/CH56's genesis object) while Kalshi's price has had days of trading. Who pays: Polymarket's
  first-hour counterparties. Why it persists: the matcher is work and the first hours are thin.
- Test (`A`+`P`, historical). The audited 316 clean pairs (`A`) and E009's matcher; both listing times (Kalshi's
  `created_time` / `open_time` are public, fact 13; Gamma's `createdAt` is in the captures); frame = pairs where Kalshi
  listed >= 24 h earlier, born before the E009/E010 poller window (sealed to 2026-11-03) or after it; Kalshi's standing
  mid at Polymarket's first print from Kalshi's public candlesticks (keyless, minute bars); Polymarket's first-24 h
  path from CLOB history. Unit = pair; primary: slope of the first-24 h Polymarket move on (Kalshi mid minus first
  Polymarket print); clusters = event. Economic: buy toward Kalshi at the first-hour recorded ask when the gap >= 5c,
  exit at 24 h at the recorded bid. Population: unknown until the birth-order census on the 316 pairs (a host query on
  files CB5-K and CH115's work already hold); floor 40 Kalshi-first pairs with gap >= 5c; slope floor 0.30; net 1.0c.
- Data: `A` (pair history, captures) + `P` (Kalshi candlesticks, CLOB history). An afternoon if the census is positive.
- Economics: fee <= 1c; the first-hour spread is wide (5-10c), which is the hurdle; capacity tiny ($0.5-5k per pair);
  the route is taker.
- Kill: < 40 qualifying pairs; or slope < 0.30; or the gap closes within the first 10 minutes (then it is the sealed
  lead's object, not this one).
- Leakage/confound: the brief excludes re-running the identical-pair lead; this is a different clock (birth) and object
  (level) and must not touch the E009/E010 window; which venue lists first is itself informative about where demand
  came from (report by category); Kalshi's `is_provisional` and `can_close_early` can differ from Polymarket's rule
  (CH64's twins; exclude pairs with rule differences at the matcher audit).
- Novelty: CH38 (Kalshi during vacuums), CH73 (Kalshi-skewed maker, CB7-X) and CH115 (horizon) are the parents; the
  birth clock is new. N 3, EV 2-3, C 1-2.

---

## 3. Ranked top 8

Rank = originality x plausibility x testability now x money route. "Runnable now" means the test can start this week
on existing stores or on keyless fetches that are not bound to the `T_seal` lane and yield to every CB11 job.

| Rank | ID | One line | Runnable now | Family |
|---|---|---|---|---|
| 1 | CH128 | Toxicity by resolution class: the maker's class map on prints and captures already on the host; reads where the economics studies' losses come from | yes (`A` only, no fetch) | E |
| 2 | CH118 | Barrier-versus-terminal confusion in 1,100+ "reach / dip to" markets; reflection-principle ratio, vol-free race identity, cross-horizon consistency | yes (Binance archive + CLOB history) | A |
| 3 | CH123 | Wikipedia edit-stream lead (second-level, keyless, verified) for resign / out-as / indicted markets; pageviews were 48 h late, edits are not | yes (revisions API + CLOB history) | C |
| 4 | CH119 | Inclusive-threshold grid mass: the atom the wording hides, largest where the density is steep (7.0 carries about 30% of its band) | yes (texts + CLOB history + public grids) | A |
| 5 | CH121 | Intra-speech hazard decay for mention baskets: the speech clock as the state variable; maker sells unsaid words as the clock runs | yes (transcripts + CLOB history; overlap with CB12-M declared) | B |
| 6 | CH125 | Leaderboard incumbency hazard for top-model month-end events: a survival model of a ranking with public history | yes (Wayback + CLOB history) | D |
| 7 | CH120 | Live roll-call tally lead: the House Clerk's keyless clock inside the day; descriptive first, taker only if asks persist | yes for Stage 1 (Clerk XML + CLOB history) | B |
| 8 | CH127 | Preview-multiple anchor for opening-weekend ladders (400+ markets); cheap, two-day hold, professionals may already be there | yes (trackers + CLOB history) | D |

Next in line: CH124 (named-source watcher; cost 3, census first), CH126 (NHC anchor; a week of mapping, season-bound),
CH129 (election night; **calendar-forced**: the collector and the frozen signs must exist by 11-01 or it waits), CH130
(pair at birth; the birth-order census on the 316 pairs is a host query), CH122 (duration ladders; the smallest
population here).

**Screenable on data AREPO already holds (no fetch):** CH128 in full (live-monitor prints, captures, sidecar); CH130's
birth-order census (the audited pair history and `createdAt` in captures); CH118's spot paths and realised sigma
(CB8-B's Binance archive) and its census of open barrier ladders (captures by question text); CH119's inclusive-wording
census (capture question texts). Everything else needs a small keyless fetch (`h13_*`) that can complete within a
week, except CH129 (one night), CH124 and CH126 (a week each to build).

**Screen sketches for the top 5.**
- **CH128.** Population: prints >= $1k from the live monitor since October in markets with a frozen class label
  (public-statistic, path-settled, scheduled-event, unscheduled-news, sports-feed) from `resolutionSource`,
  `automaticallyResolved`, `secondsDelay`, `gameStartTime` and a text rule. Decision time: the print's venue time; the
  paper fill is the preceding capture's touch crossed by the print. Target: 2 h and 6 h mark-out (next captures' mid;
  print-based where prints exist). Statistic: class mean of mark-out minus half-spread; the sign condition for the
  maker classes; the class difference floor 0.5c. Clustering: event x day, two-way with hour-of-day. Floor of 500 fills
  per reported class.
- **CH118.** Population: `h13_touch` closed barrier ladders before 2026-10-01 by date walk; both outcomes; strike,
  horizon and exchange from `textorig`. Decision time: daily 00:00Z checkpoints from listing to end. Target: touch
  outcome from the Binance path (basis check against the named exchange). Statistic: slope of `(Y - p)` on
  `(q_touch - p)`; the cross-horizon implied-sigma comparison; the race arm if >= 30 exist. Clustering: underlying x
  week. Economic: buy the model side at the recorded ask at `|q - ask| >= 5c`; floors 0.30 and 1.0c.
- **CH123.** Population: `h13_edits` closed resign / out-as / fired / indicted / dies markets by date walk, both
  outcomes, mapped to a subject article. Decision time: the first burst (>= 3 edits, >= 2 non-bot users, 10 minutes,
  length change) on the article. Target: the first 1-minute print >= 0.9 (YES markets) and the 2-hour print-based
  move (all markets). Statistic: lead distribution (median, share > 5 min) and precision of the burst rule tuned on
  the first half of the frame. Clustering: subject. Floors: median lead > 1 min, share > 5 min >= 25%, precision >= 0.3.
- **CH119.** Population: `h13_grid` closed single-threshold markets with "or higher / or more / at least / more than /
  above / over" wording, by date walk; earthquakes only if disjoint from CB12-E by event. Decision times: listing + 24 h
  and T - 48 h. Target: resolution from the named source. Statistic: slope of `(Y - p)` on `m * s` with the atom `m`
  from a class model frozen before the census and `s` the wording sign. Clustering: event (release for macro, which is
  secondary). Economic: hold the atom's side at the recorded ask when `m >= 3 pp`; floors 0.25 and 1.0c.
- **CH121.** Population: `h13_speech` closed mention events with a public timestamped transcript; word x 5-minute
  checkpoint while unsaid, after the first 5% of the clock. Decision time: each checkpoint. Target: `Y` per word.
  Statistic: slope of `(Y - p_t)` on `(q_t - p_t)` with the position model fitted before 2026-06-01; paper maker net
  at `max(p_t, q_t + 2c)` after fraction 0.5. Clustering: event. Floors 0.30 and 1.0c per filled share.

**How the families would be registered.**
- **A. Path-settled structure (CH118, CH119).** Two historical frames with the public-path and public-source outcome
  guard; the slope test with a sign-shuffle placebo; CB10-D's and CB12-E's exclusion keys checked at every census.
- **B. Public clocks (CH120-CH122).** Descriptive stages first (how much of the move happens before the clock's
  decisive moment; whether asks persist); the economic test only where the descriptive says there is something to hit.
- **C. Change detection (CH123, CH124).** Burst and change rules frozen on the first half of each frame; precision
  reported with the lead; the prospective clients are small and always-on; alert-then-read is the default route.
- **D. Model-anchored classes (CH125-CH127).** One frozen model per class fitted before a stated date, pooled slope
  with class effects, first-print rules for revisions, source issuance timestamps as the clock.
- **E. The class map (CH128).** One host-only job; the class labeller is frozen before any mark-out is computed; the
  result feeds every maker-side design that follows.
- **F. Prospectives and the pair at birth (CH129, CH130).** CH129 is pre-registered as a one-night case study with its
  single-cluster caveat in the title; CH130 is census-gated and must not touch the E009/E010 window.

**What is honest to say about all of them.** Round 1 was carries, round 2 the maker in the right state, round 3 tails
and flow identity, round 4 measurement and new products, round 5 professional anchors and unseen populations. This
round's bet is that the venue's crowd is weakest where a *clock* it can see is running (a tally, a transcript, a
duration), where the *source the rule names* changes before the crowd looks, and in model-anchored classes that have
public histories but no bot (barriers, grids, leaderboards, advisories, previews); and that the maker's loss, the one
number that has blocked every economic route so far, is a class average that hides tradable classes. None of it needs a
wallet and all of it is side-free. The counts in §0 are what distinguish these from the CH90/CH91/CB4-N failures: every
population was counted before it was proposed, and the thin ones (CH120, CH122, CH125, CH130) say so, while three
candidates were killed by their own counts (§4). Nothing here is edge until it has gone through screen, frozen
replication, prospective registration and an economic check at recorded prices.

---

## 4. Ideas considered and rejected, and why

- **Non-neg-risk mutually exclusive events (the "orphan-exclusive" overround).** Round 4 said "census first". The
  census: of 200 open events with volume >= $10k, 64 multi-market events are `negRisk=false` and only 5 have
  contest-like titles; the 6 open "who will win" events are all neg-risk. The population is a handful. Rejected.
- **Cancellation 50-50 clause as a free option on longshots (parent CH07).** 14 of 100 closed September markets carry
  the clause and all 14 have `gameStartTime`; 0 of 300 liquid open markets do. It is a sports fixture clause. Parked
  with the sports decision, like CH74/ESPN.
- **Oracle quantisation at the end of 15-minute crypto windows (a Chainlink deviation-threshold step function).** The
  closed `btc-updown-15m` description probed names Binance as the resolution source; round 5's probe found `chainlink`
  on another; round 4 already rejected "Chainlink-vs-Binance last seconds" as unobservable. Dead on arrival.
- **Race-market invariance as its own hypothesis** (the vol-free `ln(S/L)/ln(U/L)` identity). 3 race-form titles in
  50 "before" events. An arm of CH118 only if >= 30 exist at census.
- **Tick-regime ideas (CH15, CH86).** The fine tick is the norm (261 of 300 liquid open markets); there is no new
  mechanism and CB2 already closed CH15 on its premise.
- **Payout and redemption tides (CH68, CH98), including the 21:00Z Pyth-settlement variant.** The same object; both
  were dropped by CB8-CB10 and nothing new has appeared.
- **Series base-rate priors (CH51) and series-roll flow (CH50).** Not re-proposed; CH125's survival model is a
  different object (a ranking's own history, not a series' resolutions).
- **Rule-divergence twins (CH64) and docket-first court rulings (CH74, including CourtListener).** Dropped by CB8; not
  re-proposed. CH124's generic watcher covers court pages only when the rule names them; CH130 excludes
  rule-divergent pairs at the matcher audit.
- **Fee rollout as a natural experiment on taker informedness (CH53).** Covered; CB3 holds it.
- **Kalshi maintenance-window reverse lead.** CH58's hour-of-day object; `exchange/schedule` lists 0 maintenance
  windows at the probe in any case.
- **Kalshi multivariate collections (`mve_collection_ticker`, `mve_selected_legs`) as a dependence anchor.** The legs
  are public, which is a new data fact for CH82's re-entry file, but there is no Polymarket combo to trade against and
  an implied correlation has no Polymarket route. Noted for CB13+, not an idea here.
- **Ex-dividend mechanical tilt in Pyth equity Up/Down dailies.** Only ETF-class names have a dividend-to-daily-sigma
  ratio that moves the probability by more than 5 pp (0.3-0.4 sigma quarterly); four dates a year per name. Case
  catalogue.
- **Market-holiday and half-day sessions in Pyth dailies (a stale close meets the "exactly equal" clause).** Two or
  three sessions a year; round 4 rejected resolution-holiday clauses for the same reason. Case catalogue.
- **Event-day volatility under-pricing in Pyth strike markets (FOMC and CPI days).** An arm of CH99/CB12-O: the option
  chain already prices event-day volatility. Not a separate idea.
- **Billboard from public streams, Netflix Top 10, Steam concurrents, YouTube views as public inputs.** Arms of
  CH108/CH109 (running counts and known formulas); listed for CB13's census, not new mechanisms.
- **Precursor-award anchors (guild awards to the Oscars).** Season is January-March 2027 and the awards crowd already
  aggregates precursors. Parked.
- **SCOTUS opinion-day fast reading (the syllabus at 10:00 ET).** A variant of CH106 with a few minutes of capacity
  against professional readers. Dropped.
- **BLS API at 08:30:00 ET as the first source for CPI buckets.** CH28's old form; whether Polymarket's asks persist
  after a print is a measurement E009/E010's lead result already motivates.
- **UI-lag flow (Gamma versus CLOB staleness).** A measurement of the venue's own latency; no route.
- **Monopoly-maker skew as information (one bid level, one ask level, persistent).** Depth imbalance is E003's and
  CH116's object.
- **Attention crowd-out during mega-events (makers thin out in unrelated markets).** CH24's and CH36's objects.
- **"Remain in role" incumbency outside leaderboards.** CH22's sensational-YES at genesis with no public hazard base.
- **Wikipedia pageviews (CH97).** CB11-A's object with a 48 h publication lag; superseded by edits (CH123).
- **Election-night liquid races.** Dropped inside CH129 (professionals with the same models); only the second tier
  is proposed, and only as a case study.
- **Sports-only candidates:** in-game feeds (ESPN 403 last round), `secondsDelay` maker economics, the 50-50 clause,
  fixture postponements. All parked with the user's category decision.
- **Order anticipation, spoofing, inducing cancellations, manipulation of any kind, insider identification as a route,
  holding rewards, maker-rebate loops, taker full-set arbitrage, comment sentiment, wash detection as alpha, API
  quirks, Combo RFQ data, Polymarket US, keyed anchors (Betfair, Pinnacle, Smarkets, Metaculus).** Rejected in rounds
  1-5 for reasons that still hold.
- **Re-running momentum, reversal, wallet freshness or the identical-pair Kalshi lead with new data.** Excluded by the
  brief; CH130 touches the pair only at birth and outside the sealed window.

---

## 5. Sources consulted (external; AREPO documents are cited inline by name)

**Keyless probes run for this round (2026-10-18, 14:28-14:41Z; 39 requests; counts, field names, tag names and
rule-word booleans only; no price, outcome, volume or wallet of any market was printed or stored; scripts ran from
`/tmp` and wrote nothing but their own stdout).** All GETs carried `User-Agent: arepo-research-probe`, 40-second
timeouts (15 s and a 6,000-byte read cap for the event stream), no key. Requests 35-37 repeat 1, 2 and 17 (the first
run's first lines were lost to a truncated terminal; 37 re-tallied 17 by `gameStartTime`); all are counted.

| # | Request as sent (host + path + query) | Printed |
|---|---|---|
| 1, 35 | `gamma-api.polymarket.com/public-search?q=before&events_status=closed&limit_per_type=50` | events 50, markets 543, max members 72, neg-risk events 4; titles race-form (hit/reach/dip ... before) 3; titles containing "before" 50 |
| 2, 36 | `...public-search?q=reach&events_status=closed&limit_per_type=50` | 50 / 283 / 48 / 1; titles "reach ... by" 30; titles with `$` or a digit 41 |
| 3 | `...public-search?q=dip%20to&events_status=closed&limit_per_type=50` | 50 / 835 / 47 / 0; titles with "by" 4 |
| 4 | `...public-search?q=or%20higher&events_status=closed&limit_per_type=50` | 50 / 50 / 1 / 0 |
| 5 | `...public-search?q=or%20more&events_status=closed&limit_per_type=50` | 50 / 51 / 2 / 0 |
| 6 | `...public-search?q=at%20least&events_status=closed&limit_per_type=50` | 38 / 64 / 9 / 0 |
| 7 | `...public-search?q=pass&events_status=closed&limit_per_type=50` | 50 / 99 / 10 / 1; titles naming House / Senate / Congress / bill / act 21 |
| 8 | `...public-search?q=Senate%20vote&events_status=closed&limit_per_type=50` | 50 / 1,245 / 47 / 43 |
| 9 | `clerk.house.gov/evs/2026/roll010.xml` | HTTP 200, 94 KB; XML tag names (`rollcall-vote`, `rollcall-num`, `legis-num`, `action-date`, `action-time`, `chamber`, `congress`, `session`, `majority`, `party`, `recorded-vote`, `legislator`, yea / nay / present / not-voting headers and totals) |
| 10 | `www.senate.gov/legislative/LIS/roll_call_votes/vote1192/vote_119_2_00010.xml` | HTTP 403 |
| 11 | `stream.wikimedia.org/v2/stream/recentchange` (6,000 bytes, 15 s) | HTTP 200; one event's field names (`$schema`, `bot`, `comment`, `id`, `length`, `meta`, `minor`, `namespace`, `notify_url`, `parsedcomment`, `revision`, `server_name`, `server_script_path`, `server_url`, `timestamp`, `title`, `title_url`, `type`, `user`, `wiki`); `timestamp` and `meta.dt` present |
| 12 | `...public-search?q=resign&events_status=closed&limit_per_type=50` | 50 / 93 / 16 / 0 |
| 13 | `...public-search?q=out%20as&events_status=closed&limit_per_type=50` | 50 / 95 / 9 / 0 |
| 14 | `gamma-api.polymarket.com/markets?closed=false&limit=100&volume_num_min=5000` | rows 100; `http(s)` in description 0; "50-50" 0; cancel/postpone words 0; `orderPriceMinTickSize` 0.001: 100; `negRisk` 98; `negRiskAugmented` 0; field names present (`acceptingOrders`, `clobRewards`, `competitive`, `createdAt`, `enableOrderBook`, `feeSchedule`, `lastTradePrice`, `negRiskOther`, `oneHourPriceChange`, `orderPriceMinTickSize`, `resolutionSource`, `rewardsMaxSpread`, `rewardsMinSize`, `startDate`, `umaBond`, `umaResolutionStatuses`, `umaReward`) |
| 15 | request 14 with `&offset=100` | 100; 16; 0; 0; ticks 0.001: 87, 0.01: 13; `negRisk` 85; augmented 0 |
| 16 | request 14 with `&offset=200` | 100; 20; 0; 0; ticks 0.001: 74, 0.01: 26; `negRisk` 94; augmented 0 |
| 17, 37 | `gamma-api.polymarket.com/markets?closed=true&limit=100&end_date_min=2026-09-15&end_date_max=2026-09-18` | 100; URL 47; "50-50" 14 (all 14 with `gameStartTime`; 15 of 100 rows have it); cancel/postpone 24; ticks 0.001: 95, 0.01: 5; `negRisk` 77; augmented 0; extra field names `automaticallyResolved`, `gameStartTime`, `secondsDelay` |
| 18 | `...public-search?q=top%20AI%20model&events_status=closed&limit_per_type=50` | 26 / 365 / 28 / 21 |
| 19 | `...public-search?q=Chatbot%20Arena&events_status=closed&limit_per_type=50` | 4 / 74 / 32 / 2 |
| 20 | `huggingface.co/api/datasets/lmarena-ai/chatbot-arena-leaderboard` | HTTP 401 |
| 21 | `...public-search?q=hurricane&events_status=closed&limit_per_type=50` | 50 / 147 / 20 / 15 |
| 22 | `www.nhc.noaa.gov/CurrentStorms.json` | HTTP 200; top-level field `activeStorms`; 1 active storm |
| 23 | `...public-search?q=opening%20weekend&events_status=closed&limit_per_type=50` | 50 / 192 / 27 / 13 |
| 24 | `...public-search?q=box%20office&events_status=closed&limit_per_type=50` | 50 / 279 / 10 / 50 |
| 25 | `...public-search?q=Senate&events_status=active&limit_per_type=50` | 50 / 480 / 64 / 29; titles containing 2026: 10 |
| 26 | `...public-search?q=Governor&events_status=active&limit_per_type=50` | 50 / 661 / 45 / 48; titles containing 2026: 0 |
| 27 | `api.elections.kalshi.com/trade-api/v2/markets?limit=5&status=open` | HTTP 200; 44 market field names (as listed in §0 fact 13, plus price, size and volume *field names* only) |
| 28 | `api.elections.kalshi.com/trade-api/v2/exchange/schedule` | HTTP 200; keys `maintenance_windows` (0 entries), `standard_hours` |
| 29 | `gamma-api.polymarket.com/events?closed=false&limit=100&volume_min=10000` | events 100; with >= 3 markets 87; of those `negRisk=false` 45; contest-like titles among them 2; event field names (`automaticallyActive`, `createdAt`, `enableNegRisk`, `gmpChartMode`, `negRisk`, `negRiskAugmented`, `negRiskMarketID`, `series`, `seriesSlug`, `showAllOutcomes`, `startDate`) |
| 30 | request 29 with `&offset=100` | 100; 59; 19; 3 |
| 31 | `...public-search?q=who%20will%20win&events_status=active&limit_per_type=50` | 6 / 22 / 4 / 6; non-neg-risk with >= 3 markets 0 |
| 32 | `...public-search?q=btc-updown-15m&events_status=closed&limit_per_type=3` | 3 / 3; rule-word booleans on one 504-character description: `binance` true, `resolution source` true; `chainlink`, `data streams`, `coinbase`, `polygon`, `aggregator`, `deviation`, `heartbeat`, `on-chain`, `stream`, `final` false |
| 33 | `api.github.com/repos/openai/openai-python/releases?per_page=1` | HTTP 200; field names `tag_name`, `created_at`, `published_at`, `draft`, `prerelease` |
| 34 | `earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=6.85&maxmagnitude=7.15&starttime=2010-01-01&endtime=2026-10-01` | HTTP 200; counts by reported magnitude 6.9: 81, 7.0: 53, 7.1: 45 |
| 38 | `...public-search?q=2026&events_status=active&limit_per_type=50` | 50 / 1,050 / 111 / 19; titles naming Senate / Governor / House / District / midterm 2 |
| 39 | `...public-search?q=how%20long&events_status=closed&limit_per_type=50` | 40 / 292 / 18 / 36; titles naming a speech, address, remarks or press conference 7; titles containing "minute" 1 |

**External documents.**
- US House of Representatives, Office of the Clerk, roll call votes (per-vote XML and the live vote page):
  https://clerk.house.gov/Votes (probed; CH120).
- US Senate, Legislative Information System roll call vote XML: https://www.senate.gov/legislative/votes_new.htm
  (probed, 403 to the research user agent; CH120).
- Wikimedia EventStreams (`recentchange`, Server-Sent Events) and the MediaWiki Action API (`prop=revisions`):
  https://wikitech.wikimedia.org/wiki/Event_Platform/EventStreams_HTTP_Service and
  https://www.mediawiki.org/wiki/API:Revisions (probed; CH123).
- Internet Archive Wayback Machine CDX server API: https://archive.org/developers/wayback-cdx-server.html (CH124,
  CH125; not probed).
- GitHub REST API, releases: https://docs.github.com/en/rest/releases/releases (probed; CH124).
- NOAA National Hurricane Center: `CurrentStorms.json`, advisory archive, wind-speed probability products and
  forecast verification reports: https://www.nhc.noaa.gov/ (probed for the current-storms feed; CH126).
- USGS FDSN Event Web Service: https://earthquake.usgs.gov/fdsnws/event/1/ (probed; CH119).
- Box Office Mojo and The Numbers, Thursday previews and weekend reports: https://www.boxofficemojo.com/ and
  https://www.the-numbers.com/ (not probed; CH127).
- LMArena leaderboard and methodology posts: https://lmarena.ai/ (not probed directly; the Hugging Face dataset API
  returned 401; CH125).
- Kalshi trade API v2 (markets, candlesticks, exchange schedule): https://trading-api.readme.io/reference (probed;
  CH130, §4).
- Polymarket docs cited in rounds 1-5 and still used here: fees (`rate*p*(1-p)`, maker 0, rebates), liquidity rewards,
  CLOB orders and `prices-history`, negative risk, UMA resolution: https://docs.polymarket.com/trading/fees,
  https://docs.polymarket.com/developers/market-makers/liquidity-rewards,
  https://docs.polymarket.com/developers/CLOB/orders/orders, https://docs.polymarket.com/developers/neg-risk/overview,
  https://docs.polymarket.com/developers/resolution/UMA.
- Shreve (2004), *Stochastic Calculus for Finance II*, chapter 7 (the reflection principle and barrier-hitting
  probabilities); Karatzas and Shreve (1991), *Brownian Motion and Stochastic Calculus*, section 2.6 (first-passage of
  two-sided barriers; the `ln(S/L)/ln(U/L)` identity for driftless log-price) (CH118).
- Gutenberg and Richter (1944) frequency-magnitude relation; Reasenberg (1985) declustering; USGS magnitude rounding
  conventions as observed in the catalogue (CH119).
- Kaplan and Meier (1958), nonparametric estimation from incomplete observations (the survival estimators in CH121,
  CH122, CH125).
- Glosten and Milgrom (1985), bid, ask and transaction prices with heterogeneously informed traders; Easley and O'Hara
  (1987), price, trade size and information (adverse selection by information arrival process; CH128).
- Foley (2013), "A Big Blue Shift: Measuring an Asymmetrically Increasing Margin of Litigation", *Journal of Law and
  Politics*; Foley and Stewart (2020) on the timing of the count (CH129).
- Dubach (arXiv:2604.24366), Nechepurenko (arXiv:2605.11640), Le (arXiv:2602.19520), Cardozo and Rivero-Wildemauwe
  (arXiv:2609.12878), Page and Clemen (2013): as cited in rounds 1, 4 and 5 (context for families C and D).
