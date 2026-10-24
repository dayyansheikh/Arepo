# Creative hypotheses, round 10: orders, clocks and displays on the streams the host already captures (2026-10-24)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-20 13:57 UTC+1,
2026-10-20T12:57Z, on parent `2993a5df`; the file carries the round's planned date). Round 1 is
`CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59), round 3 `-17.md` (CH60-CH78), round 4
`-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130), round 7 `-21.md` (CH131-CH143),
round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168); this file starts at **CH169** and repeats none of them.
Where an idea builds on an earlier one, the parent is named and the new mechanism, clock, target or data join is
stated. Every number quoted from an AREPO document is a development, census or probe result, not evidence. One file; no
code, no queue specs, no other commits. **No network request, no host probe and no window data were used for this
round** (by instruction); every count below is taken from round 9's probes (P1-P3), LT2's census re-run or LT3's
censuses and challenger round, and is named as such. Where no probe exists the count is marked **unprobed** and the
pre-registration census is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities, 2026-10-19, unchanged).** Three prospective live tests are running
(E009/E010 Kalshi lead to 2026-11-03, E011 surprise detector to 2026-11-10). LT2 (E012-E014) is in registration for a
2026-10-22 start (challenger re-check PROCEED_WITH_FIXES, census re-run done). LT3 (E015-E019) was drafted from round
9's top five within a day (`LIVE_TESTS_3.md`; challenger round 1: E015 ACCEPT_WITH_CHANGES, E016-E019 REVISE, nothing
fatal; proposed window 2026-10-24 to 2026-11-14). The owner wants **more registered prospective live tests, fast**, on
streams the host already captures, with pure readers or light `net`-lane collectors, and **original mechanisms ahead
of textbook re-tests**. So every idea here states its **unit, its expected daily count and the probe or census that
counted it**, and carries one of three labels: **live-ready** (a pre-registration can be drafted this week against
streams the pass already writes; a pure reader on the `cpu` lane or a light `net` job), **host-only historical**
(testable on files already on the host) or **needs-fetch**. The top five are live-ready, each with a daily population
in the thousands to tens of thousands, a within-unit contrast or a composition placebo as the primary, a counts-only
census that can kill it before any outcome is read, a planning MDE stated against the materiality floor with its
arithmetic, and a realistic cost hurdle. This round's family is **LT4**, registered separately from and after LT3.

**What changed since round 9 (20 Oct; from the ledger and the LT2/LT3 files).**
- **LT3 (E015-E019) exists** and is the first live-test family born entirely from a creative round on pure readers.
  Its challenger round 1 made six rulings that bind here: (1) E019's breadth contrast is *mechanically predicted by
  quote anatomy* and carries a binding composition label; (2) crypto-series clusters can dominate a capture-level test
  (t on `G_series − 1`; an ex-crypto primary if one series family exceeds 50% of units); (3) **trade samples older than
  three days are retired from the host by archive retention**, so a trade-sample reader must run every pass, never
  catch up later; (4) "walked" (>= 4 decimals) may be a float or micro-unit artefact and needs a grid-distance rule;
  (5) E017 takes a neg-risk-only primary (outcome 0 is Yes only there) and a lagged-volume control; (6) a "both-class
  market" population decides early units' inclusion from later units (LT2 fault 4) and was rejected in favour of
  expanding-past demeaned OLS over *all* eligible units. Every design in this file is built to those six rulings.
- **CB17's pre-censuses ran (q0400-q0403).** P1 reproduced; **Data API `side` agreed with the touch label in 906 of 971
  non-sports fills (93.3%) against a 97% bar: branch T, CB17-A withdrawn uncounted.** Round 9's CH160 and CH162 arm 1
  fell with it (LT3 §7.2-7.3). **No idea here signs a monitor print.** Flow signs come only from the trade samples'
  Data API `side` under the E007 convention that E013, E016 and E018 already use, and three of the top five need no
  sign at all.
- **Two more maps failed their audits, both for reasons that are now rules.** CB11-A's market-to-Wikipedia entity map
  scored 145/200 = 0.725 against 0.80 in a blind audit (A1, A2 "not testable"). CB11-W found one fee category with >= 200
  fitting units against six needed, because `fee_category` is empty for markets that ended before the 2026 fee rollout
  (a source limitation, TERMINAL). **Nothing here uses text, an entity map or a historical category label; category
  is the live sidecar's `fee_type` / `fee_category` plus CB17's frozen sports list, read at the origin.**
- **Host (from the ledger, not probed):** monitor cap raised 3 -> 8 GiB (effective at the next restart); CB8-H daily
  `/holders` snapshots (top-20 per token, hashed) begin 2026-10-21; LT2's census re-run read exactly its spec ids;
  the pass still writes 12 complete captures a day with sidecar, two universe sweeps a pass (65,771 tokens in a
  sweep, round 9 fact), one 2,000-market trade sample a pass, the >= $1k monitor every 5 minutes and the sealed
  cross-venue poller.
- **Counted trials: over 1,280; none of CB1-CB17 has a positive verdict on any hypothesis.** The binding facts are
  round 9's: E007 +0.36c against 4.5c; 0 of 95 economic cells positive after cost; maker cells −0.2 to −2.6c even with
  a free exit; wallet effects null; CB12-X not identifiable; the Kalshi 10-20 minute lead the only replicated
  predictor, sealed in E009/E010 to 2026-11-03.

### 0.1 What round 10 learned from rounds 6-9 outcomes

Rounds 6 and 7 (CH118-CH143) leaned on fetches, text and entity maps; rounds 8 and 9 (CH144-CH168) moved to the
host's own streams. What the batches and the live-test drafts did with them is the only outcome data a creative round
has, and it says seven things.
1. **Populations die in short windows unless the unit is a market-interval or a sampled market.** CB13-T had 163
   touch-consistent fills of 427 against 500; CB16-Q seven markets; CB15-E 26 of 511 races; CB14-S nothing; CB1-B 52
   ladders against 300; CB1-D2 33 triggers; CB4-N 1.29 events an hour against 5. The units that survive are the ones
   LT3 took: movers on the complete universe (tens of thousands a day) and market-samples with flow (about 12,000 a
   day). **Rule: every counted idea here has a unit with at least a thousand non-sports instances a day, counted by a
   named probe, or it is a map.**
2. **Print direction is unobservable at AREPO's bar.** Touch-signing drops half the prints and q0400 put the Data API
   `side` at 93.3% agreement for large fills. Two round-8 ideas and two round-9 ideas died of it. **Rule: no monitor
   print is signed. Signed objects live on the trade samples under the E007 convention (prospectively Supported),
   with its 93.3% disclosed as attenuation; the strongest ideas are sign-free.**
3. **Entity and category maps fail audits; sources change under the design.** CB11-A at 72.5% precision; CB11-W's
   `fee_category` empty before 2026; CB1-E's missing text. **Rule: no text, no map, no historical label. Category is
   the live sidecar at the origin; structure is `neg_risk` and member counts; everything else is numeric.**
4. **One value per pass is one value per day.** CH158 (the venue tilt) was dropped because its state takes 252 values
   in 21 days and the independent information is nearer 21. **Rule: every state is a per-unit quantity that varies
   within market or within event; nothing here is a venue-wide clock.**
5. **Quote anatomy predicts quote-based targets mechanically.** The LT3 challenger's E019 finding, and LT2's bounce
   critique of E012, are the same objection: a mid-based target after a one-sided quote move contains the move's own
   return. **Rule: where the state is a quote event, the primary target is something the moving quote's return
   cannot produce (the *unmoved* side's change; a skip-slot target after a taker's trade), and the mid-based
   continuation is reported as a secondary for comparability with E015.**
6. **Readers must run at the pass cadence.** Trade samples older than three days are retired from the host; a reader
   that catches up weekly loses its own population. **Rule: LT4's trade-sample members extend E016's per-pass reader;
   nothing here reads a sample older than its retention.**
7. **A creative round's top five can become a drafted family in a day if the designs are already in LT3's shape.**
   Round 9's top five became E015-E019 with one primary each, a Holm family, counts-only census gates and a 21-day
   window. **Rule: every top-five idea here is written as an LT4 sketch in LT3's shape (section 3), so the designer can
   lift it without re-deriving the unit, the placebo or the gate.**
Two smaller lessons: resolution is still needs-fetch (the monitor's `--outcomes` job fetches it for its own *alert*
markets only; CB1/CB4/CB5 pass extracts are read-only on captures), but the capture stream carries a price-based
outcome proxy for every market that leaves the listing (CH175 maps it); and the "both-class market" population that
round 9 sketched is out (fault 4), so every contrast here is estimated over all eligible units with expanding-past
demeaning, and both-class counts are census descriptives, not inclusion rules.

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. **Most 2 h moves are quoted, not traded** (round 9 P1/P1b, 2026-10-15): 77,732 movers >= 1c a day over 584,022
   eligible market-interval pairs; non-sports about 2,750 an interval (60% quote-only, 27% traded, 13% never-traded).
2. **Quote-only moves have an anatomy** (P1b, four non-sports intervals, 8,080 quote-only movers): parallel 1,016
   (13%), same-side unequal 3,402 (42%), **one-sided 2,212 (27%)**, spread-change 1,450 (18%); at >= 3c: 242 / 1,538 /
   396 / 608. Per day: about 3,050 parallel and **6,600 one-sided** non-sports quote-only movers (1,200 one-sided at
   >= 3c). **A one-sided quote-only move is, by the traded label's construction, an arrival (the spread narrowed: a new
   order inside it) or a cancellation (the spread widened: an order left); a fill would have changed `volume24hr`.**
   The arrival / cancellation split was not counted by P1b: **unprobed**, the first census number of CH169.
3. **Traded moves**: about 740 non-sports an interval, 8,900 a day (27% of 2,750). The share of them that fall in the
   2,000-market active frame (where a trade sample exists) is **unprobed**; the frame is selected on activity, so the
   share is well above the frame's 4% of the universe. Bound: 943-1,080 sampled markets a pass have a taker row in the
   6 h window (P2/P2c), so at most about 1,000 traded movers a pass carry a last-trade clock.
4. **Taker rows arrive in clusters and carry a second-level clock** (P2c): 78% of rows have a same-market neighbour
   within 300 s; `ts` is venue seconds; every row is one taker order (0 multi-fill transactions in 659,082 rows, P2).
5. **The trade sample carries the taker's `side` and the token traded** (`side`, `outcome_index`, `asset`): a sell is a
   close by construction (you can only sell tokens you hold, round 8 fact), a buy is an open. On the monitor, 47% of
   large prints are on the NO token (round 8 fact 7); the share of trade-sample *rows* on the NO token is **unprobed**.
6. **Sweeps are universe-wide and minutes apart**: 65,771 tokens a sweep, `book_timestamp` a true last-update stamp
   (round 9), two sweeps a pass about two minutes apart, the touch unchanged within a pass in about 90% of books and
   the depth beneath it changed in about half (CH147's probe, round 8). Each sweep carries `best_bid/ask`, `*_size_1`,
   `depth_*_1c/5c`, `n_*_levels`, `tick_size`, `min_order_size`.
7. **Gamma's `liquidity` is a displayed dollar figure** whose relation to the sweep's near-touch depth has never been
   mapped by AREPO: **unprobed**, the first census number of CH174.
8. **Resolutions leave the listing**: 24,071 markets a day left the listing on 2026-10-15; 0 `closed` flips (round 9
   fact 6). The last two-sided mid before exit is a price-based outcome proxy whose quality (the share of exits from
   the middle band) is **unprobed** beyond CH167's design: CH175 maps it.
9. **The monitor is unsigned but counted**: 10,522 prints on 2026-10-15 (22% non-sports), a median 9 minutes after
   venue time; 2,164 non-sports prints on 2026-10-16.
10. **Costs are what they were**: median 5-share round trip 4.5c (liquid >= $100k 1.8c; politics 3.6c; crypto 4.5c);
    one-leg hold-to-resolution 1.5-2.5c above 0.80; passive entry has paid 1-7c of adverse selection in every study.

**The reading that steers this round.** Round 9 bet on three facts about the streams (quoted versus traded moves; the
walk written into the price; trains). Round 10 bets on four things the streams record that nobody has read as what
they are:
- **(a) A one-sided quote-only move is an *order event* with a sign the mid does not show.** The spread narrowed (an
  arrival inside the spread) or widened (a cancellation). E015 pools them as "one-sided" and the LT2/LT3 challengers
  call the class "bounce". Split, with a target the moving quote's own return cannot produce, the class becomes a
  wallet-free read of patient demand versus maker defence (family A).
- **(b) The trade sample carries the clock of the last trade before the capture.** A traded move caught minutes after
  its trade is a different object from one caught an hour after; SB2-J3 could not run this decomposition for want of
  rows and J4 could not for want of trade times; the live stream has both (family B).
- **(c) Takers reveal, for free, whether they are opening or closing, and whether they agree with the programs.** A
  sell is a close; a buy is an open; and a taker who trades *against* a parallel re-centering is a human disagreeing
  with a program in public (families B and C).
- **(d) The UI shows numbers the book does not back.** Gamma's `liquidity` and the event's volume rank are what retail
  sees; the sweep is what exists. Where the two part, the venue's own display is the mechanism (family D).
- **(e)** One map (the last-mid outcome proxy) turns every "needs-fetch" resolution arm of rounds 1-9 into a pure reader
  for markets that end inside a window, and prices what it cannot see (family E).

**Data labels.** `A` = on the host now or written by its running collectors: complete-universe 2 h captures
(`rows.csv.gz`: `received_utc`, `capture_start_utc`, `market_id`, `condition_id`, `event_id`, `closed`, `active`,
`binary`, `best_bid`, `best_ask`, `spread`, `last_trade_price`, `volume24hr`, `chg_1h/1d/1w`, `liquidity`, `end_date`,
`updated_at`, `clob_token_id_0`, `neg_risk`, `neg_risk_market_id`; no question text) with the sidecar `rows_ext.csv.gz`
(`fee_type`, `fee_category`, `fees_enabled`, `fee_schedule`, `taker_base_fee`, `order_price_min_tick_size`,
`order_min_size`, `rewards_*`, `clob_rewards`, `created_at`, `uma_resolution_statuses`, `event_open_interest`,
`event_volume`, `event_comment_count`, `series_slugs`, `parent_event_ids`); universe book sweeps twice a pass
(`best_bid/ask`, `*_size_1`, `depth_*_1c/5c`, `n_*_levels`, `book_timestamp`, `book_hash`, `tick_size`,
`min_order_size`); active-frame trade samples (2,000 markets a pass, the newest 500 taker rows each: `ts, side, price,
size, outcome_index, asset, tx_hash`; `features.csv.gz` with `origin_utc`, `stratum`, `n_trades_1h`,
`time_since_last_trade_s`, `trades_truncated`; **retired from the host after three days**); the live large-trade
monitor (prints >= $1k every 5 min; `side` and wallet fields exist and are not read by anything here); the cross-venue
poller (**sealed to 2026-11-03**); CB8-H `/holders` snapshots from 10-21 (CB8's store; not read here). `P` = a keyless
fetch is needed (named where light). **Sealed and not usable by anything here:** everything rounds 4-9 list, plus
LT2's `live_tests2/` and LT3's stores once registered, CB16's and CB17's stores, CB8-H's holders, E009/E010's
`cross_venue_live/` to 2026-11-03 and E011's `surprise_live/` to 2026-11-10. J4-R `[2026-10-16, 2026-10-21)` is
refused for every maker-mark-out object; nothing here is one.

**Windows and registration this round proposes (LT4).** A fourth live-test family, registered separately from LT2 and
LT3 and after LT3's registration commit, with its own Holm family (k <= 6: the top five plus CH172 if its census gate
passes): origin window of **21 days from the first 00:00Z at least 24 h after the LT4 registration commit and not
before 2026-10-28T00:00Z**, a single analysis at least 36 h after the end, a pre-declared 28-day extension only if a
declared counts-only gate falls short (the gate is read before any outcome). Collection overlap with LT2 (to 11-12),
LT3 (to 11-14), E011 (to 11-10), CB16, CB17 and CB8-H is disclosed and is overlap only: different hypotheses, no
pooling, stores never opened by one another. The trade-sample members run inside E016's per-pass reader cadence
(lesson 6). E-numbers are assigned at registration, not here.

**Hygiene that binds every idea.** Decision time is the latest input's own receipt (`received_utc` of the capture, or
the sweep's or sample's receipt where the state reads one), never a later file; states are computed from that input
and strictly earlier ones; targets are price-based (the next complete captures' mids or quotes, J4-R tightness at
both ends, 2 h / 6 h / 24 h; skip-slot where a taker's own trade sits at the origin) and never read Gamma outcome
fields; clustering is event x UTC day with the pass as a way and, where a series family exceeds 50% of units, t on
`G_series − 1` with an ex-crypto primary; **the primary is a within-unit contrast estimated by expanding-past demeaned
OLS over all eligible units, with a label shuffle within the unit as the placebo, never a cyclic shift and never an
inclusion rule that reads later units** (LT2 R1, LT3 R1); every quote-event idea states its bounce exposure and uses
the unmoved side or a skip slot in its primary; the cumulative count (M3) is recorded at every counting job; sports
stays a parameter (the sidecar rule plus CB17's frozen sports list; nothing here is sports-only; every idea reports
the sports arm uncounted).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = a pure reader on host streams, 5 = new
collector plus weeks). My judgement, not measurements. Cost conventions as rounds 1-9 and `EXECUTION_COSTS.md` (fact
10); the monitor's 9-minute median lag makes every taker-follows-the-print route reported only.

**Planning-MDE arithmetic used throughout (stated once).** `SE = SD x sqrt(1/n1 + 1/n2) x sqrt(DE)` for a two-class
contrast, `SE = SD / sqrt(n / DE)` per standard deviation of a continuous state, with `DE = 1 + (m − 1) rho` for
clusters of mean size `m` and intra-cluster correlation `rho` (assumed 0.05-0.3; event x UTC day clusters hold about
5-15 units); MDE = 3.2 x SE (one-sided alpha after Holm k = 6, about 0.0083, z 2.4, plus z 0.84 for 80% power). SDs:
2 h continuation about 4c, one side's 2 h change about 3c, 6 h move about 5c, 24 h move about 6c (round 9's
assumptions; LT3 uses the same). Flow-slope MDEs are stated in E013's units (per unit of signed share x standardised
moderator), as LT2 and E016 do, and are planning estimates.

**Counts table (what was counted before each idea was written; daily unless stated; the probe or census named).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH169 | non-sports market x 2 h interval with a one-sided quote-only move, split arrival / cancellation | about 6,600 one-sided a day (1,200 at >= 3c); split **unprobed** | P1b (anatomy) |
| CH170 | traded mover in the active frame with a last-trade clock from the pass's sample | <= about 1,000 a pass (12,000 a day) by the 6 h bound; the 2 h subset **unprobed** | P2/P2c bound; LT2 census |
| CH171 | market x trade sample with >= 1 buy row and >= 1 sell row in the 6 h window | 943-1,080 market-samples a pass with any row; the both-legs share **unprobed** | P2/P2c; LT3 C2 gate (>= 60,000 covered units projected) |
| CH172 | parallel quote-only re-centering at k in the active frame, with a taker trade in (k, k+1] | about 3,050 parallel a day universe-wide; active-frame share and taker-reaction share **unprobed** | P1b; census |
| CH173 | market x trade sample with >= 3 rows in the 6 h window | about 12,000 market-samples a day with any row; >= 3 rows **unprobed** (78% of rows have a neighbour) | P2c |
| CH174 | traded mover with a sweep in the same pass; hollowness `h` from sweep depth against Gamma `liquidity` | about 8,900 traded non-sports movers a day, all sweep-covered; `h` distribution **unprobed** | P1; round 9 sweep count |
| CH175 | market leaving the listing; its last two-sided mid | 24,071 exits a day; middle-band share **unprobed** | P1 (fact 6) |
| CH176 | non-sports event x pass near a volume-rank breakpoint within category | 12 passes x about 6 categories x a rank neighbourhood; rank churn **unprobed** | spec |
| CH177 | market x interval with `updated_at` changed and no numeric field changed | **unprobed** (may be a tick clock) | spec |
| CH178 | token x pass with a touch change between the two sweeps, traded or quoted from the sample | about 6,500 touch changes a pass (10% of 65,771); labelled subset in the 2,000 sampled markets **unprobed** | CH147's probe; round 9 |
| CH179 | same-market rows at the same venue second with different takers | **unprobed** | spec |
| rejected | fee-parabola limit to arbitrage; ladder lead-lag; venue-wide wealth shocks; price-space FLB; NO-token share as a sign | arithmetic; prior nulls (L1-L4, XM1-XM6, E005); CH158; HB1 PX1/PX2; 65% against 93% | section 4 |

---

## 1. Map: where money might be, given the survivors, the nulls and what the streams record

| Family | What the evidence and the streams suggest | Money route |
|---|---|---|
| A. Order events in the quote stream | 6,600 one-sided quote-only non-sports moves a day are arrivals or cancellations; the mid shows neither; the unmoved side's reaction is a target the bounce cannot produce; `updated_at` may carry silent edits | maker: lean with arrivals, ignore cancellations (keep the spread); widen after silent edits; taker: fade cancellations only, reported against 4.5c |
| B. The clock of the trade | the sample timestamps the last trade before each capture; fresh and settled traded moves are different objects; a taker who fades a program's re-centering disagrees in public; same-second rows are races | maker: pull for one pass after fresh moves, quote through settled ones; the program-versus-human verdict says whom to follow; races mark toxic, arbitraged markets |
| C. Flow composition | sells are closes, buys are opens; one order versus a crowd | maker: quote against closers and dispersed flow, step aside from openers and concentrated flow; taker follow reported only |
| D. Displayed versus real | Gamma's `liquidity` is what retail sees; the sweep is what exists; the category's volume rank is the front page | maker: quote inside hollow books; fade traded moves in hollow books; the rank breakpoint as an attention clock |
| E. Maps | the last mid before exit is the outcome for everything that leaves the listing | the gate that makes every resolution arm of rounds 1-9 a pure reader for a long enough window |

---

## 2. Hypotheses

### A. Order events in the quote stream (parents E015 / CH156, CH80, CH35, CH147, CH08; literature: Hasbrouck and Saar 2009, Rosu 2009, Hollifield, Miller and Sandas 2004, Copeland and Galai 1983, Roll 1984)

**CH169. Arrivals and cancellations: a one-sided quote-only move is either a new order posted inside the spread (the
spread narrowed: someone wants to be filled at a better price than the touch and is willing to wait) or an order that
left (the spread widened: a maker's defence, or a bot's inventory being satisfied); the mid moves half the gap in both
cases and E015 pools them as "one-sided"; the unmoved side ratifies arrivals (it follows the new order) and ignores
cancellations (it stays, and the mid halves back when the side is re-posted); a maker who leans with arrivals and holds
through cancellations keeps the spread, and a taker who fades only cancellations fades the only one-sided class that
is pure bounce.**
- Mechanism and who pays: in a limit-order market an order posted inside the spread is the patient trader's signal
  (Rosu 2009; Hollifield, Miller and Sandas 2004: submissions inside the spread come from traders with private values
  away from the mid), while a cancellation is the writer of a free option withdrawing it (Copeland and Galai 1983;
  Hasbrouck and Saar 2009's fleeting orders). Roll (1984) is the bounce: a side leaves, the mid moves, the side returns.
  On Polymarket the two are distinguishable from the capture pair alone: with no trade in the interval (E015's
  quote-only label), a one-sided move that narrowed the spread is an arrival and one that widened it is a cancellation
  (fact 2). Who pays: whoever reads the mid as the price in both cases; the maker who fades an arrival on the other
  side; the taker who chases a cancellation. Why the crowd misses it: the chart shows a mid; the LT2 and LT3 challengers
  called the whole one-sided class "bounce", which only the cancellation half is.
- Population and count (`A`, live-ready): about 6,600 one-sided quote-only non-sports movers a day (1,200 at >= 3c;
  fact 2); in 21 days about 139,000, of which arrivals and cancellations split in a proportion the census counts first
  (**unprobed**; the design assumes nothing about it beyond the kill line). Markets holding both kinds in the window: a
  census descriptive, not an inclusion rule (lesson 7).
- Test (live-ready; within-market, composition placebo). Unit: non-sports market x interval under LT3 §1.4's
  eligibility with E015's quote-only label and the one-sided anatomy (one side within 0.05c of unchanged, the other
  moved >= 1c). Decision time: capture k's `received_utc`. State: `arrival` (spread_k < spread_{k−1}: the moved side
  moved toward the other) versus `cancellation` (spread_k > spread_{k−1}). Sign: `s = sign(mid_k − mid_{k−1})`.
  **Target (primary): the ratification `r = s x (unmoved side_{k+1} − unmoved side_k)`, the 2 h change of the side that
  did not move, which the moving side's own return cannot produce; J4-R tight at k and k+1, two-sided at k+1.**
  Secondary targets: E015's `c = s x (mid_{k+1} − mid_k)` for comparability; `r` at 6 h. **Primary statistic: expanding-
  past market-demeaned OLS of `r` on 1[arrival] over all one-sided units, with controls logit `mid_k`, `|mid_k − 0.5|`,
  spread_{k−1}, |x|, log1p `volume24hr_{k−1}`, as-of log hours-to-end and the reward flag; CR1 SEs clustered on event
  and two-way event x UTC day, p the larger; pre-declared direction > 0 (arrivals are ratified more); placebo: 200
  within-market shuffles of the arrival label across the market's one-sided units, <= 1.5% qualifying.** Secondaries:
  the sized split from sweep 1 of pass k (`*_size_1` at the new touch above twice `min_order_size` = a real order;
  below = CH80's dust; sweep 1 is minutes after the capture and is used only here, never in the primary); the
  reward-market split (the new touch at exactly `rewards_min_size` is a bot re-quoting one side); the |x| dose.
- Economic route: (1) maker, primary: the paper maker re-centres with arrivals (the avoided fill on the side the
  arrival will drag) and holds through cancellations (the half-spread kept when the side is re-posted); (2) taker: fade
  cancellations of >= 3c at the recorded touch, round trip to k+1, reported against 4.5c median / 1.8c liquid.
- Kill criteria (counts only, features only): the arrival share of one-sided units under 15% or over 85%; projected
  21-day arrivals under 15,000; `spread` absent or non-positive for more than 10% of one-sided units; or the placebo
  advances.
- Planning MDE versus floor: with about 55,000 arrivals and 84,000 cancellations in 21 days (a 40/60 split; the
  census replaces it), an unmoved-side 2 h SD of about 3c and DE 1.5-2.8: SE about 0.02-0.03c, **planning MDE about
  0.06-0.1c against the 0.5c floor; the floor binds.** The risk is attribution (defence versus bounce), which is why the
  primary reads the unmoved side and not the mid.
- Cost hurdle: none for the maker arm; the taker fade must clear 4.5c on a 3c trigger and is reported only.
- Live-ready: **yes.** E015's reader with two more flags per unit (which side moved; the sign of the spread change),
  `cpu` lane, under 350 MB. C 1.
- Leakage and confounds: a tick-regime flip at 0.96/0.04 changes the grid (excluded at the flip); a one-sided move
  can be a fill that left `last_trade_price` unchanged only if `volume24hr` is also unchanged (then nothing traded);
  `volume24hr` rolling off exactly offset by a fill is counted as impossible in practice and the census reports
  `last_trade_price`-changed-with-volume-unchanged cases separately; an arrival that is itself dust (CH80) is handled
  by the sized secondary; a bot tightening one side to stay inside its reward band is an arrival with no view (the
  reward split); stale quotes (CH146's clock) as a way. **Bounce exposure stated:** cancellations are the bounce by
  construction and the primary target excludes the returning side; arrivals are its mirror. Sports is a parameter.
- Novelty: CH80 is the dust anchor, CH35 the vacuum, CH147 the breathing book, E015 the quote-only class. New: the
  one-sided class read as an order event (arrival versus cancellation) and the unmoved-side ratification target.
  N 4, EV 4, C 1.

**CH177. Silent edits: Gamma's `updated_at` moves when any field of the market record changes; an interval in which it
moved while every numeric field the capture holds stayed put is a metadata edit (a rule clarification, a description
change, a date or image change), the capture-level trace of CH08's rule-edit events without the text; silent edits
precede disputes, early closures and re-pricings, so the market's next 24 h shows more movement and a wider spread
than its own quiet intervals; a maker who widens for a day after a silent edit sheds the re-pricing risk.**
- Mechanism and who pays: rule edits are the venue's resolution risk made visible (CH08; the UMA record); the edit is
  public on the market page but not on the price chart. Who pays: the maker whose quote survives the edit; the holder
  who learns of the clarification from the price. Why the crowd misses it: nobody diffs `updated_at`.
- Population and count (`A`, live-ready if the field behaves): **unprobed.** If `updated_at` moves with every price or
  volume tick it is a tick clock and the idea dies at the census (kill line below).
- Test (live-ready, census-gated; within-market, sign-free). Unit: market x interval. State: `silent` = `updated_at`
  changed and none of `best_bid`, `best_ask`, `last_trade_price`, `volume24hr`, `liquidity`, `end_date`, `closed`,
  `active` changed. Targets (sign-free): `|mid_{k+12} − mid_k|` and `spread_{k+12} − spread_k`. **Primary: market-
  demeaned OLS of the 24 h absolute move on 1[silent], event x UTC-day clusters; floor 1.0c; placebo: shuffle the
  silent label across the market's intervals.** Secondary: the time to listing exit after a silent edit (CH175's
  proxy); `end_date` changes (CH07) reported as their own class.
- Economic route: maker, widen for one day after a silent edit; no taker route (sign-free).
- Kill criteria: `updated_at` changes in more than 50% of market-intervals (a tick clock); fewer than 200 silent
  non-sports edits a day; or the placebo advances.
- Planning MDE versus floor: if 200-1,000 silent edits a day survive (4,000-21,000 in 21 days) against the markets' own
  quiet intervals, with a 24 h |move| SD of about 5c: MDE about 0.2-0.5c against 1.0c: adequate if the count holds.
- Cost hurdle: none.
- Live-ready: **yes**, E015's reader with one more comparison. C 1.
- Leakage and confounds: fields the capture does not hold (description, tags, image) change for reasons unrelated to
  resolution; `updated_at` may be set by the indexer on re-sync (a venue-wide burst: the census reports the top
  pass's share of silent edits and the primary excludes passes where more than 20% of markets are silent).
- Novelty: CH08 (rule-edit events) needs the text diff; CH07 postponements the date. New: the silent-update trace as
  a live, text-free edit detector. N 2-3, EV 2, C 1.

**CH178. Two minutes, not two hours: the pass's two sweeps are about two minutes apart and the trade sample taken after
them timestamps every taker order in between, so for the 2,000 sampled markets E015's traded-versus-quoted contrast
can be formed at the minute scale (a touch change between the sweeps with a row between them, or without one), and the
2 h continuation of a minute-scale quoted move versus a minute-scale traded move replicates E015 on a clock that cannot
be stale.**
- Mechanism and who pays: as E015; the point is the clock. The capture is up to 2 h after the move it records and the
  challenger's anatomy objection is partly a staleness objection; the sweep pair sees the move within minutes.
- Population and count (`A`, live-ready): about 6,500 touch changes a pass universe-wide (10% of 65,771 books, CH147's
  probe); the labelled subset is the 2,000 sampled markets' share of them: **unprobed**, plausibly 200-500 a pass
  (sampled markets are the active ones), 2,400-6,000 a day, 50,000-125,000 in 21 days.
- Test (live-ready; E015's contrast on a new clock). Unit: sampled market x pass with a touch change between sweep 1
  and sweep 2 (either side, >= 1 tick). Decision time: the trade sample's receipt. State: traded (a row with venue `ts`
  in `[t_sweep1, t_sweep2]`) versus quoted (no row). Target: `c = sign(mid_s2 − mid_s1) x (mid_{k+1} − mid_s2)` (the next
  capture's mid against sweep 2's). **Primary: expanding-past market-demeaned OLS of `c` on 1[traded], event x UTC-day
  clusters, direction pre-declared as E015's (quoted parallel moves persist more than traded moves: > 0 for the
  parallel subclass, with the anatomy label from the two sweeps); placebo: within-market label shuffle.**
- Economic route: as E015 (maker re-centres with quoted parallel moves; taker fade reported).
- Kill criteria: fewer than 100 labelled units a pass at the census; sweep spacing outside [60 s, 300 s] in more than
  10% of passes; or the placebo advances.
- Planning MDE versus floor: 50,000-125,000 units, SD 4c, DE 1.5-2.8: MDE about 0.1-0.2c against 0.5c.
- Cost hurdle: as E015.
- Live-ready: **yes**, a reader over two sweeps and one sample per pass. C 1. Not an LT3 member (LT3 reads sweep 1
  for mechanism secondaries only); disclosed as E015's replication on a different clock in a separate family.
- Leakage and confounds: a row's `ts` is venue time and the sweep's receipt is the host's clock (a 1-2 s skew; the
  census measures it on the pass's own `book_timestamp`); the sample may be truncated at 500 rows before the sweep
  window in frenzied markets (`trades_truncated` excludes); sampled markets are selected on activity.
- Novelty: a replication of E015, not a new mechanism, ranked as such. N 1, EV 3 (it answers the staleness objection
  directly), C 1.

### B. The clock of the trade (parents SB2-J3 / J4, E004, E007, E015, CH69, CH162; literature: Roll 1984, Dufour and Engle 2000, Engle and Russell 1998, Brogaard, Hendershott and Riordan 2014, Budish, Cramton and Shim 2015)

**CH170. The age of the move: a traded 2 h move whose last trade was minutes before the capture is a different object
from one whose last trade was an hour before; the fresh move still carries the trade's displacement of the touch (the
bounce has a half-life of minutes), the settled move is what the makers left standing after they had time to revise;
fresh traded moves revert over the next 2 h and settled traded moves persist; the pooled reversal that E004 found
"consistent with bounce" is the fresh class, and the trade sample's timestamps separate it for free.**
- Mechanism and who pays: Roll (1984) is the bounce; its half-life is the time makers take to re-centre after a fill.
  Dufour and Engle (2000) say the opposite about the *trade*: short durations between trades mean more information and
  larger permanent impact. The capture pair cannot tell the two apart because it does not know when the trade was;
  the pass's trade sample does (fact 4: `ts` in venue seconds). SB2-J3 was the bounce decomposition on a historical
  book table and could not run (too few rows); J4 decomposed capture-level quote changes without trade times. Who
  pays: the taker who chases a fresh move (buys the displaced touch) and the maker who fades a settled one. Why the
  crowd misses it: the 2 h chart has no clock.
- Population and count (`A`, live-ready): traded non-sports movers about 8,900 a day universe-wide (fact 3); those in
  the active frame with a sample: bounded by 943-1,080 sampled markets a pass with a 6 h row, so at most about 1,000 a
  pass carry a clock; the 2 h subset is **unprobed**, plausibly 500-700 a pass, 6,000-8,400 a day, 125,000-175,000 in 21
  days. The fresh / settled split is the census's first number (trains make the age distribution bimodal, fact 4).
- Test (live-ready; within-market, composition placebo). Unit: sampled non-sports market x pass that is a traded mover
  at capture k (E015's traded label, |x| >= 1c) with a row in the sample whose `ts` lies in `[t_{k−1}, t_k)`. Decision
  time: the trade sample's receipt (after the capture; states use the capture, earlier captures and rows with
  `ts < t_k` only). State: `age = t_k − max ts` of such rows; **fresh** (age <= 15 min), **settled** (age >= 60 min),
  middle reported. Target: `c = sign(x) x (mid_{k+1} − mid_k)` at 2 h, `c6` at 6 h; both J4-R tight. **Primary:
  expanding-past market-demeaned OLS of `c` on 1[fresh] over fresh and settled units with E015's anatomy label (M3) as
  a control, |x|, logit `mid_k`, spread_k, log1p `volume24hr_{k−1}`, as-of hours-to-end; CR1 on event and two-way
  event x UTC day; pre-declared direction < 0 (fresh reverts more); placebo: 200 within-market shuffles of the age
  label across the market's traded movers.** Secondaries: the Dufour-Engle reading (the sign of the age effect within
  the re-centred anatomy class, where the touch displacement is absent); the age as a continuous dose (log age); the
  6 h target; the never-traded and quote-only classes as E015 owns them.
- Economic route: (1) maker, primary: pull or widen for one pass after a fresh traded move (the avoided fill into a
  displaced touch), quote through settled ones; (2) taker: fade fresh >= 3c moves at the recorded touch, round trip to
  k+1, reported against 4.5c median / 1.8c liquid (E004's pooled fade failed costs; the conditional class is reported,
  not promised).
- Kill criteria: fresh share under 10% or over 90% of clocked traded movers; projected 21-day clocked units under
  40,000; `ts` granularity coarser than 60 s in the samples; or the placebo advances.
- Planning MDE versus floor: with about 45,000 fresh and 60,000 settled units (a 30/40 split of 150,000; the census
  replaces it), SD 4c, DE 1.5-2.8: SE about 0.03-0.04c, **planning MDE about 0.1c against the 0.5c floor; the floor
  binds.** The reader must run every pass (lesson 6).
- Cost hurdle: maker none; taker 4.5c.
- Live-ready: **yes.** E016's per-pass reader (rows, `features.csv.gz`, captures) with one more number per unit. C 1.
- Leakage and confounds: fresh moves are more often the "eaten touch" anatomy and settled ones the re-centred anatomy
  (the M3 control and the within-anatomy secondary); the sample is the newest 500 rows and may not reach back 2 h in
  frenzied markets (`trades_truncated` excluded, counted); the active frame is selected on activity; a trade at the
  capture's own second is excluded by `ts < t_k`. Bounce exposure stated: the fresh class is the bounce by design;
  that is the object.
- Novelty: E004/E006 pooled reversal; J4 the quote-change decomposition; J3 could not run; CH132 is the wake-up print
  (long silence *before* a print). New: the age of the last trade at the capture as the bounce clock, live, at scale.
  N 3-4, EV 4 (it settles the bounce question LT2 and LT3 argue about), C 1.

**CH172. Program versus human: when a market's quotes re-centre in parallel with no trade (E015's parallel class: a
program moved its model) and the next taker trades *against* the new level, a human has publicly disagreed with a
program; if programs price public inputs and humans know things, the faded re-centering gives way (the price continues
in the taker's direction from the next slot on); if humans are noise and programs are right, the taker's dent is
absorbed and the program's level holds; the pair tells a maker whose side to take when the two disagree.**
- Mechanism and who pays: Brogaard, Hendershott and Riordan (2014) find algorithmic traders' marketable orders carry
  information and their quotes are adversely selected; on this venue the programs are the quoters and the humans the
  takers, so the roles may invert. E007 says taker flow continues (+0.36c at 1 h); E015 says parallel re-centerings
  persist; a fade is where the two claims collide. Who pays: whichever of the two is wrong. Why the crowd misses it:
  nobody labels who moved the quote.
- Population and count (`A`, live-ready, census-gated): about 3,050 parallel non-sports quote-only movers a day
  universe-wide (fact 2); those in the active frame with a sample at the next pass, and with a taker row in
  `(t_k, t_{k+1})`: **unprobed**, plausibly 150-300 a day of which fades perhaps 40% (60-120 a day, 1,300-2,500 in 21
  days). The census gate is 2,000 projected fades.
- Test (live-ready; within-market, skip-slot target). Unit: sampled non-sports market x pass k+1 whose capture-k move
  was a parallel quote-only re-centering with sign `s` (both sides moved the same way within 0.5c of each other, no
  trade). Decision time: the pass k+1 sample's receipt. State: the net E007-signed taker flow `f` over rows with `ts`
  in `(t_k, t_{k+1})` (from the k+1 sample; `side` under the E007 convention, 93.3% agreement disclosed as attenuation):
  **fade** (`sign(f) = −s`), **follow** (`sign(f) = s`), **none** (no row). **Target: the skip-slot continuation
  `c = s x (mid_{k+4} − mid_{k+2})`, which excludes the slot holding the taker's own trade and its bounce (LT2's
  skip-slot rule). Primary: expanding-past market-demeaned OLS of `c` on 1[fade] and 1[follow] over all three classes,
  controls |f|, |x|, logit `mid_k`, spread_k, log1p volume; coefficient on 1[fade] against the none class; CR1 on event
  and event x UTC day; pre-declared direction < 0 (the human who fades a program knows something; the opposite sign is
  the "programs win" reading, reported); placebo: shuffle the fade / follow / none label across the market's parallel
  units.** Secondaries: the dose in |f|; the 24 h version; the same contrast for E015's one-sided class (CH169's
  arrivals) reported.
- Economic route: maker, primary: when the verdict is "humans win", step aside after a fade (do not re-post at the
  program's level); when "programs win", quote at the program's level into the fade (the taker's dent is the maker's
  spread); taker routes reported against 4.5c.
- Kill criteria (counts only): projected 21-day fades under 2,000; fades under 20% or over 80% of reacted units;
  `side` missing in more than 10% of rows; or the placebo advances.
- Planning MDE versus floor: 2,000 fades against about 3,000 none units, a 4 h move SD of about 5c, DE 1.5-2 (clusters
  are small: one re-centering per market-pass): SE about 0.12-0.16c, **planning MDE about 0.4-0.5c against the 0.5c
  floor: borderline on 21 days, adequate on 28 (pre-declared); the census gate decides whether it enters the family.**
- Cost hurdle: maker none; taker 4.5c.
- Live-ready: **yes**, E016's per-pass reader joined to E015's class code. C 1.
- Leakage and confounds: a fade may be a hedger or a closer, not a view (CH171's open / close split as a secondary);
  the program may re-centre again at k+1 in response to the fade (the state reads k+1's quotes as a label, not a
  target); the skip slot costs power; sampled markets are the active ones; crypto series may dominate parallel
  re-centerings (the series rule in the hygiene block).
- Novelty: E007 and E015 each own one side; CH159 is breadth; CH56 the seed. New: the disagreement event between a
  program's re-centering and a taker's fade, with a skip-slot target. N 4, EV 4, C 1; power is the risk.

**CH179. Races: two taker rows in the same market at the same venue second from different orders (two `tx_hash`
values) are a race, the signature of bots reacting to the same external input (a spot print, a Kalshi quote, a sibling
market); markets where races happen are externally anchored and arbitraged, so their moves carry nothing a slower
reader can use, while their makers face the most toxic flow on the venue; the race share is a wallet-free map of
where speed, not information, sets the price.**
- Mechanism and who pays: Budish, Cramton and Shim (2015) and Aquilina, Budish and O'Neill (2022): latency races are
  the signature of mechanical arbitrage. Who pays: the maker whose stale quote is the prize. Why the crowd misses it:
  a race is two rows one second apart, invisible on a chart.
- Population and count (`A`, live-ready): same-second multi-order rows per market-sample: **unprobed** (round 9 probed
  timestamp clustering as a feature only). Every sample has 220,000 rows; the census counts it in an afternoon.
- Test (live-ready, census-gated; a moderator and a map). Unit: market x trade sample. State: race share `R` = share of
  rows in the 6 h window that have another row in the same market, same venue second, different `tx_hash`.
  **Primary: E013-form expanding-past demeaned OLS of `y6` on `x6 x zR`, one-sided for < 0 (flow in race-prone markets
  continues less: it is arbitrage, not information); placebo: shuffle `R` across the market's samples.** Secondaries:
  the race share by category (crypto expected highest), by hour, and against the cross-venue pair list (a map, read
  only after 2026-11-03).
- Economic route: maker, widen in race-prone markets (the toxic-flow map); no taker route.
- Kill criteria: `R` non-degenerate in fewer than 20,000 covered market-samples; same-second multi-order rows under
  3% of rows; corr(zR, zH) above 0.5 (then it is E018's burst measure); or the placebo advances.
- Planning MDE versus floor: as E016/E018 (about 0.002-0.003 per SD in E013's units); the gross floor 0.5c in the
  favourable cell.
- Cost hurdle: none (a maker map).
- Live-ready: **yes**, E016's reader. C 1.
- Leakage and confounds: one taker splitting an order across two transactions in one second is not a race (the
  size-equality fingerprint is reported); `ts` is venue seconds, so a race is a lower bound on simultaneity.
- Novelty: CH69 is the worked order, CH162/E018 the train, CH36 bot outages. New: the same-second race as the
  external-anchor map. N 3, EV 2 (a map more than a route), C 1.

### C. Flow composition on the trade samples (parents CH144 / CB17-A, E007, E013, E016, E018, CH162, CH111; literature: Pan and Poteshman 2006, Chan and Lakonishok 1993, Easley and O'Hara 1987, Kyle 1985, Barber, Odean and Zhu 2009)

**CH171. Opens carry the information, closes carry the liquidity, measured where the sign exists: on Polymarket a taker
sell is always a close and a taker buy always an open, so the 6 h signed flow of a sampled market splits into an
opening leg (buys of YES minus buys of NO) and a closing leg (sells of NO minus sells of YES) with no wallet, no touch
and no text; the next-6 h continuation loads on the opening leg and not on the closing leg; a maker who quotes against
closers and steps aside from openers keeps the spread.**
- Mechanism and who pays: Pan and Poteshman (2006) needed clearinghouse open-interest data to show that newly opened
  option positions predict the underlying; here the open/close flag is structural (fact 5). CH144 (round 8) proposed
  this on the monitor's large prints and CB17-A was withdrawn when the print direction failed its agreement bar
  (branch T). The trade samples carry the Data API `side` that E007 used prospectively (Supported) and E013/E016/E018
  use; this is CH144's mechanism moved to the stream where the sign exists. Who pays: the maker who treats a closer's
  sell like an opener's sell. Why the crowd misses it: every flow measure on the venue is signed, never split.
- Population and count (`A`, live-ready): 943-1,080 sampled markets a pass with a row in the 6 h window (P2/P2c), about
  12,000 market-samples a day, about 250,000 in 21 days; LT3's C2 gate projects >= 60,000 *covered* units (coverage
  decided at the origin). The share with both legs non-zero is **unprobed**; the census counts it.
- Test (live-ready; E013's estimator, two legs). Unit: market x trade sample under E016's coverage rule. Decision time:
  `origin_utc`. Flow: `o6` = opening signed share (BUY YES + , BUY NO −) and `s6` = closing signed share (SELL NO + ,
  SELL YES −), each normalised by the window's total |volume| so that `x6 = o6 + s6`. Target: `y6 = mid(slot k+3) −
  mid_i`. **Primary: expanding-past demeaned OLS of `y6` on `o6` and `s6` with E013's controls; the test is
  `beta_open − beta_close > 0`, one-sided, CR1 on event and event x UTC day; placebo: 200 draws that shuffle the
  open / close label across each market-sample's rows (keeps `x6`, breaks the split); floor: the gross 6 h move in the
  top open-leg tercile at |o6| >= 0.5 must exceed 0.5c.** Secondaries: within opens, BUY NO versus BUY YES (the
  "bet-against" opener versus the default YES opener: the venue's YES bias makes the NO opener the deliberate one;
  47% of large prints are on the NO token, round 8 fact); the 1 h version on E007's unit; row counts instead of volume.
- Economic route: maker protection (quote against the closing leg, skew away from the opening leg for one pass); the
  taker follow of the opening leg reported against 4.5c (expected "not shown", as E007).
- Kill criteria: SELL rows under 15% or over 85% of rows; `side` missing in more than 10% of rows; both legs non-zero
  in fewer than 30,000 projected covered units; or the placebo advances.
- Planning MDE versus floor: a difference of two slopes is noisier than one; on LT2's arithmetic for E013 (SE scaled
  from h3 by cluster count, times 1.5 for proxy noise) the planning MDE on `beta_open − beta_close` is about
  0.003-0.004 in E013's units, against development F4/F5 effects of 0.002-0.006 for single slopes; there is no
  development evidence for the split, so "inconclusive" is a plausible outcome and the gross-move floor is the
  material test.
- Cost hurdle: maker none; taker 4.5c.
- Live-ready: **yes.** E016's per-pass reader, one more column per row. C 1.
- Leakage and confounds: `side` misclassification at the 93.3% rate attenuates both legs equally; a BUY NO may be a
  hedge of a YES holding (rare; disclosed); closing flow is mechanically larger in markets near their end (as-of
  hours-to-end control); opens and closes are correlated with |x6| (the controls).
- Novelty: CH144 is the parent (monitor prints, touch-signed, withdrawn). New: the stream (trade samples), the sign
  source (Data API `side`, no touch) and the two-leg regression with a label-shuffle placebo. N 2, EV 3, C 1.

**CH173. One order or a crowd: the share of a market's 6 h signed flow that came from its single largest taker order
(the concentration of the flow) moderates continuation; one large order is one agent's view (Kyle 1985; Easley and
O'Hara 1987: size carries information), dispersed same-direction flow is a crowd (Barber, Odean and Zhu 2009: retail
herding predicts nothing; round 9's copycat trains); concentrated flow continues, dispersed flow does not; the maker
fears the one order and sells liquidity to the crowd.**
- Mechanism and who pays: as stated; the Data API's one-row-per-order aggregation (fact 4) makes the largest row a
  clean "largest order". Who pays: the maker who treats a $5,000 order and fifty $100 orders alike. Why the crowd
  misses it: volume is a sum.
- Population and count (`A`, live-ready): market-samples with >= 3 rows in the 6 h window: **unprobed**, bounded by
  the 12,000 a day with any row; with 78% of rows having a neighbour the share with >= 3 rows is likely above half.
- Test (live-ready; E013's estimator with a new moderator). Unit: market x trade sample under E016's coverage rule
  with >= 3 rows. Decision time: `origin_utc`. Moderator: `C` = largest row's |volume| over the window's total
  |volume| (and the Herfindahl index as a secondary), standardised to `zC` with a pre-window census scale. **Primary:
  expanding-past demeaned OLS of `y6` on `x6 x zC` with E013's controls plus `zC`, `x6`, log total |volume|, log row
  count, `zW` and `zH`; one-sided for > 0; placebo: shuffle `C` across the market's samples; floor: gross 6 h move in
  the top-`C` tercile at |x6| >= 0.5 above 0.5c.** Secondaries: the monitor-based variant (the >= $1k print share of
  the interval's `volume24hr` increment, sign-free, universe-wide, reported); `C` on row counts.
- Economic route: maker protection (skew against concentrated flow for one pass); taker follow reported.
- Kill criteria: `C` non-degenerate in fewer than 40,000 projected covered units; corr(zC, zW) or corr(zC, zH) above
  0.5 (then it is E016's or E018's measure under a new name); or the placebo advances.
- Planning MDE versus floor: as E016 (about 0.002-0.003 per SD in E013's units); no development evidence exists for
  `C`; a first test.
- Cost hurdle: maker none; taker 4.5c.
- Live-ready: **yes**, E016's reader. C 1.
- Leakage and confounds: large orders walk (W) and arrive in trains (H): the controls and the correlation gate; the
  largest order's size scales with the market (log total volume control); a worked order (CH69) splits one view into
  many rows and looks dispersed (the size-equality fingerprint reported).
- Novelty: CH162/E018 is temporal clustering, CH69 the worked order, CH111 round dollars, CH70 holder concentration.
  New: the size concentration of the flow as its own moderator. N 3, EV 3, C 1.

### D. Displayed versus real (parents CH35, CH133, CH103, CH157 / E017, CH24, CH110; literature: Barber and Odean 2008, Hartzmark 2015, Bessembinder, Panayides and Venkataraman 2009)

**CH174. Hollow liquidity: Gamma's `liquidity` is the dollar figure the interface shows, and it counts resting orders
wherever they sit; the sweep's `depth_*_5c` is what a taker can actually hit near the mid; a book whose displayed
liquidity sits far from the touch is hollow, and takers who size orders by the display walk thin books and produce
moves that are impact, not information; within a market, traded moves made when the book was hollow revert more than
traded moves made when it was full; a maker who quotes inside a hollow book earns the real (wide) spread while the
displayed figure deters competitors.**
- Mechanism and who pays: displayed liquidity drives order placement (Bessembinder, Panayides and Venkataraman 2009
  on displayed versus hidden depth); impact in a thin book is transitory (Hendershott and Menkveld 2014). Who pays: the
  taker who trusts the number; the maker who quotes at the display's implied depth. Why the crowd misses it: the
  interface shows one number.
- Population and count (`A`, live-ready, census-gated): about 8,900 traded non-sports movers a day (fact 3), all with a
  universe sweep in the same pass (fact 6); about 187,000 in 21 days. The distribution of hollowness is **unprobed**
  (fact 7).
- Test (live-ready; within-market moderator). Unit: non-sports market x interval that is a traded mover at capture k.
  Decision time: sweep 1 of pass k's receipt (minutes after the capture; states use capture k, sweep 1 of pass k and
  earlier files only; the 2 h target runs from the capture k+1 mid, about 110 minutes later). State: hollowness
  `h = 1 − (depth_bid_5c + depth_ask_5c) / liquidity_gamma`, after the census reconciles units (sweep depth in shares x
  price against Gamma's dollars), clipped to [0, 1], standardised within category. Target: `c = sign(x) x (mid_{k+1} −
  mid_k)`. **Primary: expanding-past market-demeaned OLS of `c` on `zh` over traded movers with E015's anatomy label,
  |x|, spread_k, logit `mid_k`, log1p `volume24hr_{k−1}` and log `liquidity` as controls; one-sided for < 0 (hollow
  books' traded moves revert more); CR1 on event and event x UTC day; placebo: shuffle `h` across the market's traded
  movers.** Secondaries: the paper maker's net at a quote one tick inside each touch, by `h` tercile (the hollow
  book's real spread); `h` as a moderator of E017's attention surge (attention into a hollow book).
- Economic route: (1) maker, primary: quote inside hollow books (the recorded touch minus one tick on each side; the
  avoided-fill mark-out reported by `h` tercile); (2) taker: fade traded moves of >= 3c in top-tercile-`h` books at the
  recorded touch, round trip to k+1, reported against 4.5c (the hollow book's own spread is wider than the median, so
  the hurdle is the recorded round trip, not 4.5c).
- Kill criteria (counts only): Gamma's `liquidity` is not a superset of near-touch depth in at least 90% of books
  (then the two fields do not measure the same thing and `h` is undefined); the within-market interquartile range of
  `h` is under 0.1 for more than half the markets with >= 10 traded movers; or the placebo advances.
- Planning MDE versus floor: 187,000 units, SD 4c, DE 1.5-2.8: SE per SD of `zh` about 0.012-0.017c, MDE about
  0.04-0.05c per SD; the material test is the top-minus-bottom tercile contrast (about 2.2 SD apart), **MDE about 0.1c
  against the 0.5c floor; the floor binds.**
- Cost hurdle: maker none; taker the recorded round trip.
- Live-ready: **yes**, a reader over captures and sweep 1 (the sweep's 65,771 rows a pass are the cost: under 400 MB
  streamed). C 1-2.
- Leakage and confounds: Gamma's figure may lag the sweep by minutes (the census measures the agreement of the two
  touches); `liquidity` may count both tokens' books while the sweep reads outcome 0 (the unit reconciliation); dust at
  the touch (CH80) inflates `h`'s denominator by nothing and its numerator by nothing (sized depth is what `depth_5c`
  sums); hollow books are thin books (the spread control; the point is the *display*, which the spread does not show);
  reward markets have bot depth at the band (the reward flag as a way).
- Novelty: CH35 is the vacuum (a side absent), CH133 depth fade at 120 s, CH103 hidden long-dated books, CH80 dust.
  New: the displayed-versus-executable liquidity gap as a state, universe-wide, with the UI as the mechanism. N 4,
  EV 3, C 1-2.

**CH176. The front page as a clock: the venue's category lists are ranked by volume and show a fixed number of events
before "load more"; an event that crosses into the visible set is seen by everyone who opens the tab, and one that
drops out is not; within a category x pass, events just inside the breakpoint attract attention (a volume surge and
the YES tilt E017 predicts) that events just outside do not, and the crossing, not the volume, is the cause.**
- Mechanism and who pays: rank effects on attention (Hartzmark 2015); attention buys (Barber and Odean 2008). Who
  pays: the attention buyer. Why the crowd misses it: it is the crowd.
- Population and count (`A`, live-ready with one assumption): event-level 24 h volume is the sum of members'
  `volume24hr`; the rank within `fee_type` is computable at every capture; the breakpoint `B` is the venue's default
  list length, **to be fixed before registration from one documented look at the venue's own list (a no-data action)
  and stated as an assumption**; rank churn near `B` is **unprobed** and is the kill line.
- Test (live-ready, assumption-gated; within-event, composition placebo). Unit: non-sports event x pass with rank in
  `[B − 10, B + 10]`. State: `entry` (rank <= B at k and > B at k−1), `exit` (the reverse), `stayer`. Targets: the next
  2 h change in log event volume (attention) and, as the money target, the members' 24 h outcome-0 mid change (E017's
  target, neg-risk events only). **Primary: event-demeaned OLS of the 2 h log-volume change on 1[entry] − 1[exit],
  event x UTC-day clusters; placebo: shuffle the entry / exit label across the event's near-breakpoint passes.** The
  24 h price target is the secondary and the only route.
- Economic route: maker skew up after an entry (E017's route conditioned on the crossing); taker reported.
- Kill criteria: fewer than 20% of positions in `[B − 10, B + 10]` change hands per pass (no identification); `B`
  cannot be fixed; or the placebo advances.
- Planning MDE versus floor: about 6 categories x 12 passes x 20 events a day; perhaps 300-600 entries and exits in
  21 days: the attention target (log volume, SD about 0.5) has an MDE around 0.1 log points, adequate; the 24 h price
  target on a few hundred crossings has an MDE of 1.5-2c against 1.0c: **underpowered for the money target on 21
  days**, ranked accordingly.
- Cost hurdle: as E017.
- Live-ready: **yes** for the attention target; the price target needs 60+ days. C 1.
- Leakage and confounds: the venue's actual sort may be "trending" (undocumented) rather than 24 h volume; the
  breakpoint is assumed; entries are caused by surges that E017 already owns (E017's `S` label as a control: the
  crossing's effect net of the surge).
- Novelty: CH24 category attention, CH110 alert thresholds, CH157/E017 attention without a price. New: the visible-set
  breakpoint as the attention clock. N 3, EV 2, C 1.

### E. Maps (parents CH167, CH163, CH62, CH88; k = 0)

**CH175. The last-mid outcome proxy: every market that resolves leaves the listing, and the last two-sided mid before
it leaves is 0.95-0.99 or 0.01-0.05 for almost every decided market; the map counts, by class, structure and as-of
horizon, the share of exits whose last mid is in a tail (a price-decided outcome), in the middle (an early close, a
dispute, a delisting) or absent (no two-sided quote at the end), and the lag between the as-of `end_date` and the
exit; where the tail share is high the proxy is an outcome for every resolution arm of rounds 1-9 for markets whose
end falls inside a window, with no fetch at all.**
- Population: 24,071 exits a day (fact 8), sports-heavy; non-sports exits by class **unprobed**.
- Test (host-only historical, descriptive; no counted test): (1) exits per day by last two-sided mid band ([0.01,
  0.05], (0.05, 0.95), [0.95, 0.99], absent), `fee_type`, structure (standalone / ladder member) and as-of horizon at
  the last capture; (2) the lag from the as-of `end_date` to the exit, by class (the grace a reader must allow);
  (3) the proxy's self-consistency on markets that re-appear (none should) and on ladders (exactly one member in the
  upper tail); (4) the cost of the light Gamma fetch for the middle-band exits only (CH167's budget, now for a
  fraction of ids); (5) what it unlocks and for how long a window: CH163's standalone-versus-ladder YES premium,
  CH164's resolution arm, CH157/E017's carry arm and CH62's calendar-decided NO, each as a pure reader over markets
  with as-of end inside the window plus grace, with the population they would have in 21, 60 and 90 days (the first
  honest statement of which calibration tests can ever be live-ready on this stream).
- Kill criteria: none (a map). The tail share by class is the gate every resolution arm cites.
- Live-ready: the map is **host-only historical** (one week of captures); what it unlocks is **live-ready** for the
  windows it names. C 1.
- Novelty: CH167 counts exits and prices the fetch. New: the last mid as the outcome, its quality measured, and the
  window arithmetic for every calibration arm. N 2, EV 3 (as an enabler), C 1.

---

## 3. Ranked top 10, then the rest

Rank = originality x plausibility x **time to a registered live test** x population per day x money route, with the
lessons of section 0.1 as hard constraints. "Live-ready" means: a pre-registration can be drafted this week against
streams the collectors already write, the collector is a pure reader (`cpu` lane, under 400 MB) or a light `net` job,
the counts-only census can run on worn files before any rule binds, and the reader runs at the pass cadence.

| Rank | ID | One line | Label | Daily population (source) | Primary contrast |
|---|---|---|---|---|---|
| 1 | CH169 | Arrivals versus cancellations: the one-sided quote-only class split by the sign of the spread change, with the unmoved side's reaction as the target | live-ready | about 6,600 one-sided non-sports quote-only movers (1,200 at >= 3c) (P1b); split unprobed | within market: ratification by the unmoved side, arrival minus cancellation; label shuffle |
| 2 | CH170 | The age of the move: fresh versus settled traded moves from the sample's last-trade clock (SB2-J3 reborn live) | live-ready | up to about 1,000 clocked traded movers a pass (P2 bound); 2 h subset unprobed | within market: continuation, fresh minus settled, anatomy-controlled; age shuffle |
| 3 | CH174 | Hollow liquidity: displayed `liquidity` against executable near-touch depth as the moderator of traded-move reversal | live-ready (census-gated) | about 8,900 traded non-sports movers, all sweep-covered (P1; 65,771-token sweeps) | within market: continuation on hollowness; `h` shuffle |
| 4 | CH171 | Opens versus closes: the 6 h flow split into an opening and a closing leg on the stream where the sign exists (CH144 transplanted) | live-ready | about 12,000 market-samples with 6 h flow (P2/P2c); >= 60,000 covered units projected (LT3 C2) | `beta_open − beta_close`; open/close label shuffle within the sample |
| 5 | CH173 | One order or a crowd: flow concentration as a moderator of continuation | live-ready | market-samples with >= 3 rows (unprobed; above half of 12,000) | `x6 x zC`; `C` shuffle across the market's samples |
| 6 | CH172 | Program versus human: a taker's fade of a parallel re-centering, with a skip-slot target | live-ready (census-gated: >= 2,000 fades) | about 3,050 parallel movers (P1b); active-frame fades unprobed, 60-120 a day plausible | fade minus none on `s x (mid_{k+4} − mid_{k+2})`; label shuffle |
| 7 | CH175 | The last-mid outcome proxy and the window arithmetic for every calibration arm | host-only historical (map) | 24,071 exits (P1) | none (a map) |
| 8 | CH178 | Two minutes, not two hours: E015's contrast on the sweep pair | live-ready (replication) | about 6,500 touch changes a pass (CH147); labelled subset unprobed | within market: traded minus quoted at the minute scale |
| 9 | CH177 | Silent edits: `updated_at` without a numeric change as the rule-edit detector | live-ready (census-gated) | unprobed | within market: 24 h |move| and spread after silent edits |
| 10 | CH179 | Races: same-second multi-order rows as the external-anchor map and a continuation moderator | live-ready (census-gated) | unprobed | `x6 x zR` < 0 |

Next in line: CH176 (the front-page breakpoint; the attention target is powered, the price target is not). Nothing in
this file needs the `net` lane; CH175's optional fetch for middle-band exits is a fraction of CH167's 240 requests a
day.

**Pre-registration sketches for the top 5 (LT4 candidates; each a separate primary in one Holm family; written in
LT3's shape so the designer can lift them).**

- **CH169 (arrivals versus cancellations).** Unit: non-sports market x 2 h interval under LT3 §1.4 (binary, two-sided
  and tight at k−1 and k, mid in [0.02, 0.98], as-of end > t + 3 h, sidecar non-sports, one row per `condition_id`)
  with E015's quote-only label and the one-sided anatomy. Population per day: about 6,600 (P1b); the arrival share is
  the census's first number. Primary contrast: expanding-past market-demeaned OLS of the ratification `r = s x
  (unmoved side_{k+1} − unmoved side_k)` on 1[arrival], one-sided > 0, controls as in section 2. Target and horizon:
  the unmoved quote's change by slot k+1 (2 h), J4-R tight, two-sided at k+1; E015's mid-based `c` as secondary S1.
  Clustering: CR1 on event and two-way event x UTC day, p the larger; t on `G_series − 1` and an ex-crypto primary if a
  series family exceeds 50%. Planning MDE: about 0.06-0.1c (SD 3c, 55,000 against 84,000 units, DE 1.5-2.8) against
  the 0.5c floor. Kill-census (counts only, worn captures before the window): arrival share outside [15%, 85%];
  projected arrivals under 15,000; `spread` missing for more than 10% of one-sided units. Cost hurdle: maker none;
  the taker fade of cancellations reported against 4.5c / 1.8c. Extends: E015's reader (two flags per unit; sweep 1
  for the sized secondary only).
- **CH170 (the age of the move).** Unit: sampled non-sports market x pass that is a traded mover at capture k with a
  row whose `ts` lies in `[t_{k−1}, t_k)`. Population per day: up to about 1,000 a pass (P2 bound), 6,000-8,400
  plausible, counted by the census on the samples of two worn days. Primary contrast: expanding-past market-demeaned
  OLS of `c` on 1[fresh] over fresh (age <= 15 min) and settled (age >= 60 min) units with E015's anatomy label as a
  control, one-sided < 0. Target and horizon: `c = sign(x) x (mid_{k+1} − mid_k)` at 2 h; `c6` secondary. Clustering:
  as CH169. Planning MDE: about 0.1c (SD 4c, 45,000 against 60,000, DE 1.5-2.8) against 0.5c. Kill-census: fresh share
  outside [10%, 90%]; projected clocked units under 40,000; `ts` coarser than 60 s. Cost hurdle: maker none; taker
  fade of fresh >= 3c moves reported against 4.5c. Extends: E016's per-pass reader (rows and `features.csv.gz`) joined
  to E015's class code; the reader must run every pass (three-day retention).
- **CH174 (hollow liquidity).** Unit: non-sports market x interval that is a traded mover at capture k, with sweep 1 of
  pass k. Population per day: about 8,900 (P1), all sweep-covered. Primary contrast: expanding-past market-demeaned OLS
  of `c` on `zh` (hollowness, standardised within category after the unit reconciliation), one-sided < 0, with the
  anatomy label, |x|, spread, logit mid, lagged volume and log `liquidity` as controls; the material test is the
  top-minus-bottom tercile contrast. Target and horizon: `c` at 2 h from capture k+1 (decision time: sweep 1's
  receipt). Clustering: as CH169. Planning MDE: about 0.04-0.05c per SD, about 0.1c on the tercile contrast, against
  0.5c. Kill-census: Gamma `liquidity` not a superset of near-touch depth in >= 90% of books; within-market IQR of
  `h` under 0.1 for more than half the markets with >= 10 traded movers. Cost hurdle: maker none; taker fade
  reported against the recorded round trip. Extends: E015's reader plus a streamed read of sweep 1 (65,771 rows a
  pass).
- **CH171 (opens versus closes).** Unit: market x trade sample under E016's coverage rule (page oldest row at or before
  t − 6 h, or the page not full, decided at the origin). Population per day: about 12,000 with any row (P2/P2c); LT3
  C2 projects >= 60,000 covered units in 21 days; both legs non-zero is the census's number. Primary contrast:
  expanding-past demeaned OLS of `y6` on `o6` and `s6` with E013's controls; `beta_open − beta_close > 0`, one-sided.
  Target and horizon: `y6 = mid(slot k+3) − mid_i` (6 h). Clustering: event and event x UTC day CR1; far-future control
  as LT2 R1 (sources >= flow window + horizon later). Planning MDE: about 0.003-0.004 in E013's units; the gross 6 h
  move in the top open-leg tercile at |o6| >= 0.5 must exceed 0.5c to be called material. Kill-census: SELL rows
  outside [15%, 85%]; `side` missing in more than 10% of rows; both legs non-zero in fewer than 30,000 projected
  covered units. Cost hurdle: maker none; taker follow of the opening leg reported against 4.5c. Extends: E016's
  reader (one more column per row). Parent CH144 disclosed; CB17-A's withdrawal (branch T) does not bind here because
  no touch-signing is used.
- **CH173 (one order or a crowd).** Unit: market x trade sample under E016's coverage rule with >= 3 rows. Population
  per day: above half of 12,000 (unprobed; the census counts it). Primary contrast: expanding-past demeaned OLS of
  `y6` on `x6 x zC` with E013's controls plus `zC`, `x6`, log total |volume|, log row count, `zW`, `zH`; one-sided > 0.
  Target and horizon: `y6` (6 h). Clustering: as CH171. Planning MDE: about 0.002-0.003 per SD in E013's units; the
  gross floor 0.5c in the top-`C` tercile at |x6| >= 0.5. Kill-census: `C` non-degenerate in fewer than 40,000
  projected covered units; corr(zC, zW) or corr(zC, zH) above 0.5. Cost hurdle: maker none; taker follow reported.
  Extends: E016's reader.

**How the families would be registered.**
- **A. Order events (CH169, CH177, CH178).** CH169 counted; CH177 counted only if its census shows `updated_at` is not a
  tick clock and >= 200 silent non-sports edits a day; CH178 counted as E015's replication on the sweep clock in LT4,
  not LT3 (disclosed), if its labelled count clears 100 a pass.
- **B. The clock of the trade (CH170, CH172, CH179).** CH170 counted; CH172 counted only if its census projects
  >= 2,000 fades (28 days pre-declared); CH179 a map first, counted as a moderator only if same-second multi-order rows
  exceed 3% and `R` is not E018's burst measure (corr gate).
- **C. Flow composition (CH171, CH173).** Both counted on E016's reader and coverage rule; the correlation gates
  against `W` and `H` are read at the census; a measure that fails its gate is dropped uncounted.
- **D. Displayed versus real (CH174, CH176).** CH174 counted if the unit reconciliation passes; CH176's attention
  target reported, its price target deferred to a 60-day window.
- **E. Maps (CH175).** Run first (an afternoon on one week of worn captures); cited by every resolution arm in rounds
  1-9 and by CH177's exit secondary.

**What is honest to say about all of them.** Round 9's facts were about the streams; round 10's are about what the
streams let a reader *name*: an order event, a trade's age, an open or a close, a disagreement, a displayed number.
Each of the top five is a within-unit contrast on a population of thousands to tens of thousands a day, built to the
six LT3 rulings and the seven lessons above, and each is a maker-protection object first and a taker route only where
the counted numbers say so. Three of the top five need no sign at all; the two that do use the trade samples' Data
API `side` exactly as E013/E016/E018 do, with q0400's 93.3% disclosed as attenuation. One idea (CH170) revives a
decomposition that SB2 could not run; one (CH171) moves a withdrawn batch's mechanism to the stream where its sign
exists; one (CH169) answers the bounce objection with a target the bounce cannot produce; one (CH174) makes the
interface itself the mechanism; one (CH173) is a plain moderator and is ranked as such. The most original idea in
the file (CH172) is sixth because its population is the smallest and the deaths of CB13-T and CB16-Q were deaths of
small populations. Nothing here is edge until it has gone through census, frozen rules, prospective registration and
an economic check at recorded prices.

---

## 4. Ideas considered and rejected, and why

- **The fee parabola as a limit to arbitrage** (the taker fee `rate x p x (1 − p)` is largest at 0.5, so un-arbitraged
  predictability should peak there in fee-charging categories and not in fee-free ones). Arithmetic kills it: at a 2%
  rate the fee is 0.5c at p = 0.5 and 0.1c at p = 0.05, against a 1.8-4.5c spread round trip; the identifying gradient
  is a tenth of the cost. The fee is also category-determined (`fee_type`), so the contrast is a subject-matter
  comparison. Not proposed.
- **Ladder lead-lag: the program-quoted (liquid) member leads its stale siblings by one capture.** Sibling lead-lag and
  neg-risk drift were tested and null (L1-L4, XM1-XM6, E005 "not supported", SB2-J5); a quote-only moderator of a null
  base effect is not a round-10 bet. CH159/E019 keeps the breadth version.
- **Venue-wide wealth shocks (a crypto crash day sells political longshots) and any other venue-level clock.** One
  value per pass is one value per day (lesson 4, CH158's death). Not proposed.
- **Price-space favourite-longshot drift (prices extremise away from 0.5 over 7 days).** HB1 PX1/PX2 tested price-level
  drift (both tails drifted up, price only); the signed level-conditional version is a textbook re-test. Not proposed.
- **The NO-token share of rows as a sign proxy** (takers mostly buy, so the token traded gives the sign without `side`).
  About 65% accurate against `side`'s 93.3%; and CH144/CH171 own the token-and-side structure. Folded into CH171's
  BUY NO versus BUY YES secondary.
- **Up/Down daily and 15-minute markets' "Up" level bias.** CH30, CH76, CH100, CH102 and CB9 own these series; the
  bots price them off spot. Not proposed.
- **The ladder's own variance ratio (implied width from member prices against the realised movement of the ladder's
  centre), a fetch-free version of prior-art gap 4.** The capture has no question text, so strikes cannot be ordered
  without CB5's family map; CB10-D and CB13-R own the anchored version. Not live-ready; not proposed.
- **Sign-free volatility after large prints** (|move| and spread after any print). Volume-volatility clustering is
  textbook and CH39 owns the maker's post-print retreat. Not proposed.
- **Negated-question framing** (retail's YES bias flips for "Will X *not* happen" questions). Text; the capture has
  none and the monitor's titles cover printed markets only; CB1-E's text failure and lesson 3. Not proposed.
- **Holder breadth as the retail-participation rate.** CB8-H collects the top-20 holders per token, not a count; CH70
  and CH151 own concentration and turnover. Not proposed.
- **A display-lag map (Gamma's touch against the sweep's touch minutes later).** Worth an afternoon as a descriptive
  (it bears on CH174's unit reconciliation and on every capture-level test's staleness) but it is not a hypothesis.
  Listed for the census, not as an idea.
- **Resolution-fetch arms** (CH163, CH164's resolution arm, CH157's carry). Still needs-fetch; the monitor's
  `--outcomes` job resolves its own alert markets only and the CB1/CB4/CB5 pass extracts are read-only on captures.
  CH175 maps the price-based proxy that may replace the fetch for markets ending inside a window.
- **Deadline crowding (spreads before shared `end_date` instants) and the sticky-ask-after-a-drop (disposition wall).**
  The first is a spread target with no route beyond "stay"; the second is E015's same-side-unequal anatomy with a
  name. Not proposed.
- **Cross-venue ideas on the sealed stream before 2026-11-04** (CH165, CH166 stand as round 9 left them), **anything
  that reads E011's alerts before 2026-11-11, LT2's or LT3's stores, CB16's, CB17's or CB8-H's windows.** Collection
  overlap is disclosed; stores stay closed.
- **Sports in-play, closing-line value (gap 10).** The user's scope decision is open; sports stays a parameter and
  nothing here is sports-only.
- **Copy-trading, wallet features of any kind, 15-minute crypto latency, reward-rebate loops, manipulation, insider
  identification as a route, taker full-set arbitrage, API quirks, keyed anchors.** Rejected in rounds 1-9 for
  reasons that still hold.
- **Re-proposals of CH01-CH168 with new data** (decided and proposal-window carry, dispute lotteries, reward geometry
  and shocks, tick regimes, series base rates and rolls, genesis and first-day prints, seed anchors, mention baskets,
  external anchors and clocks, barrier confusion, quoter grain, wake-up prints, book age, breathing book, mint share,
  turnover, synchronous prints, exit pressure, cost and lag, quoted versus traded moves, walked flow, trains,
  attention surges, breadth, class-conditioned longshots): not re-proposed; where an idea touches one, the parent is
  named and the new field, clock, target or join is stated (CH169 on E015 and CH80; CH170 on J3/J4 and E004; CH171 on
  CH144; CH174 on CH35/CH133; CH177 on CH08; CH178 on E015; CH175 on CH167).

---

## 5. Sources consulted

### 5.1 No host probe this round (by instruction); what was read instead
No network request, no `ssh oracle`, no window file. The counts in section 0 and the counts table are quoted from
round 9's six host probes (P1, P1b, P2, P2b, P2c, P3; scripts and sha256 verbatim in `CREATIVE_HYPOTHESES_2026-10-23.md`
section 5.1; 2026-10-15 captures, one sidecar, the 2026-10-15 monitor file, three 2026-10-16 trade samples for features
only), from CH147's probe in round 8 (the sweep pair), from LT2's census re-run of 2026-10-20 (ledger: n reproduce, 6 h
truncation 0.12%, `vol24_cap` = +inf) and from LT3's census design (C1-C4 gates, section 8 of `LIVE_TESTS_3.md`). Every
count that no probe produced is marked **unprobed** and is the first number of that idea's pre-registration census.
The local working tree holds no worn data (`backend/data-dumps/` is 416 KB of history indexes), so no local counts
were possible either.

### 5.2 AREPO documents read (cited inline by name)
`CLAUDE.md`, `AGENTS.md`; `CREATIVE_HYPOTHESES_2026-10-23.md` (sections 0-5 in full) and the CH titles of rounds 1-8;
`LIVE_TESTS_2.md` section 0 and 1.1; `LIVE_TESTS_3.md` sections 0, 1.2-1.5, 4, 7 and 8; `lab_dashboard/registry.json`
(all entries); the last 150 lines of `EXPERIMENT_LEDGER.md` (CB17 part pre and q0400-q0403, creative round 9, CB11
unblocks and the CB11-A audit, CB11-W census and TERMINAL ruling, LT3 draft and challenger R1, the 06:14Z-07:18Z
session note, LT2 R1 response and re-check); `PRIOR_ART_2026-10-19.md` top-10 gaps; `COLLECTION_HOST.md`,
`scripts/oracle/arepo_pass.sh`, `scripts/oracle/supervise.sh`, `scripts/oracle/crontab.txt`; `LIVE_TRADE_MONITOR.md`
(the `--outcomes` job); the docstrings of `backend/scripts/run_cb1_extract.py`, `run_cb4.py`, `run_cb5.py`,
`run_cb3_quote_state.py`, `backend/astrolabe/research_lab/book_sweep.py` (sweep coverage) and `bounce_decomp.py`
(J3/J4); `CREATIVE_BATCH_8.md` (CB8-H's `/holders` fields); `SCREENING_BATCH_2.md` (J3's row), `HYPOTHESIS_BATTERY_1.md`
(PX1/PX2); the opening lines of CH09, CH39, CH56, CH80, CH132, CH144, CH146 and CH147 for overlap checks.

### 5.3 External literature (named, not fetched)
- Hasbrouck (1991), "Measuring the information content of stock trades" (quote revisions after trades); Hasbrouck and
  Saar (2009), "Technology and liquidity provision: the blurring of traditional definitions" (fleeting orders; CH169).
- Rosu (2009), "A dynamic model of the limit order book"; Hollifield, Miller and Sandas (2004), "Empirical analysis of
  limit order markets" (inside-spread submissions; CH169).
- Copeland and Galai (1983), "Information effects on the bid-ask spread"; Roll (1984), "A simple implicit measure of
  the effective bid-ask spread" (the bounce; CH169, CH170).
- Dufour and Engle (2000), "Time and the price impact of a trade"; Engle and Russell (1998), "Autoregressive
  conditional duration" (short durations and information; CH170's competing reading).
- Brogaard, Hendershott and Riordan (2014), "High-frequency trading and price discovery" (algorithmic quotes versus
  marketable orders; CH172).
- Budish, Cramton and Shim (2015), "The high-frequency trading arms race"; Aquilina, Budish and O'Neill (2022),
  "Quantifying the high-frequency trading arms race" (races; CH179).
- Pan and Poteshman (2006), "The information in option volume for future stock prices" (open versus close; CH171).
- Chan and Lakonishok (1993), "Institutional trades and intraday stock price behavior"; Easley and O'Hara (1987),
  "Price, trade size, and information in securities markets"; Kyle (1985), "Continuous auctions and insider trading"
  (size and information; CH173).
- Barber, Odean and Zhu (2009), "Do retail trades move markets?" (herding; CH173).
- Bessembinder, Panayides and Venkataraman (2009), "Hidden liquidity: an analysis of order exposure strategies";
  Hendershott and Menkveld (2014), "Price pressures" (displayed depth and transitory impact; CH174).
- Barber and Odean (2008), "All that glitters"; Hartzmark (2015), "The worst, the best, ignoring all the rest: the rank
  effect and trading behavior" (attention and rank; CH176).
- Nagel (2012), "Evaporating liquidity" (reversal as liquidity provision; the maker routes throughout).
