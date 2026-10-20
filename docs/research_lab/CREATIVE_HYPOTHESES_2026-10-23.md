# Creative hypotheses, round 9: live-ready tests on the streams the host already captures (2026-10-23)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-20 02:55 UTC+1,
2026-10-20T01:55Z, on parent `8853f9cc`; the file carries the round's planned date). Round 1 is
`CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59), round 3 `-17.md` (CH60-CH78), round 4
`-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130), round 7 `-21.md` (CH131-CH143),
round 8 `-22.md` (CH144-CH155); this file starts at **CH156** and repeats none of them. Where an idea builds on an
earlier one, the parent is named and the new mechanism, clock or data join is stated. Every number quoted from an AREPO
document is a development or screen result, not evidence. One file; no code, no queue specs, no other commits.

## 0. How to read this file

**The brief that binds this round (owner priorities, 2026-10-19).** Only three prospective live tests are running
(E009/E010 Kalshi lead to 2026-11-03, E011 surprise detector to 2026-11-10); E012-E014 are being drafted separately
(`LIVE_TESTS_2.md`, branch `feat/live-tests-2`; challenger round 1 REVISE on 2026-10-20) and are not duplicated here.
The owner wants **more registered prospective live tests, fast**, on streams the host already captures, with light
collectors or pure readers. Recent counted tests died of small populations in short windows (CB13-T 163 fills of 427
against 500; CB16-Q 7 markets with both grains; CB15-E 26 of 511 races; CB14-S nothing returned; CB17's own probes
found 44 both-label cells and 7 both-period markets in four days). So every idea here states its **unit, its expected
daily count and the probe that counted it**, and carries one of three labels: **live-ready** (can be pre-registered
and collected prospectively from existing host streams within days: a pure reader or a light `net`-lane job),
**host-only historical** (testable on files already on the host, no fresh window needed) or **needs-fetch**. The top
five are live-ready and each has a daily population in the hundreds to hundreds of thousands. The design rules of
round 8 stand: a within-unit contrast or a composition placebo is the *primary* design, a counts-only census can kill
the idea before any outcome is read, the planning MDE is stated against the materiality floor, and the cost hurdle is
realistic. Creative mechanisms first; literature gaps (`PRIOR_ART_2026-10-19.md` top 10) where they fit.

**What changed since round 8 (19-20 Oct).**
- **CB17 was drafted from round 8** (`CREATIVE_BATCH_17.md`, DRAFT-REVISED after challenger round 1; part `pre` code
  at `cadaaf19`): CH144 as **CB17-A** (counted under branch S only), CH146/CH147 as **CB17-B** (B1, B2), CH150 as
  **CB17-C** (C1), CH154 as **CB17-E**, a census only. CB17's probes corrected four round-8 premises that bind here:
  touch-consistent fills are scarce (CB13-T's 60-minute touch-age rule drops 48% of transactions; 44 both-label cells
  in four days), first-day fills almost vanish under touch signing (7 both-period markets), `book_timestamp` is a true
  last-update stamp (65,771 of 65,771), and event OI updates in 87% of traded intervals. **Lesson taken here: no idea
  in this file depends on touch-signing a print.** Print directions come from the Data API `side` under CB17's
  declared branch rule (q0400's agreement count), or from the trade-sample `side` convention that E007 (registered,
  Supported) and E013 already use; most ideas need no print sign at all.
- **LT2 (E012-E014) challenger round 1 returned REVISE** (ledger 2026-10-20 ~01:50Z): the cyclic-shift timing gate is
  not a valid null (neighbouring flow overlaps the window and target; 2-3-row markets give too few shuffles); E012 is
  predicted by bid-ask bounce (E006 H1's 1 h version was "consistent with bounce"); 6 h coverage selects on post-origin
  trades; 21 UTC days make day-level inference optimistic. **Every design here therefore uses label shuffles within the
  unit or J4-R's increment bootstrap as the placebo, never a cyclic shift; states its bounce exposure; defines coverage
  from pre-origin facts only; and clusters on event x UTC day with the pass as a way.** Round 9's family A is, in part,
  a direct answer to the bounce critique: it splits the moves the reversal tests pool into the classes bounce can and
  cannot produce.
- **Counted trials stood at 1,282 at CB17's drafting; none of CB1-CB17 has a positive verdict on any hypothesis.** The
  binding facts are unchanged (E007 +0.36c against 4.5c; 0 of 95 economic cells positive after cost; maker cells -0.2
  to -2.6c even with a free exit; wallet effects null; CB12-X not identifiable; the Kalshi 10-20 minute lead the only
  replicated predictor, sealed in E009/E010 to 2026-11-03).
- **Host state at drafting (2026-10-20 01:30Z, listings only):** 110 complete captures since 10-10 (12 a day; 10-14
  has 6), 212 sweeps, 104 trade samples (**`trades.csv.gz` is on the host only from 2026-10-16**; earlier samples hold
  `plan.json` and `manifest.json` there, their CSVs are in the archive releases), monitor day files 10-12 to 10-20 with
  7,242 / 10,380 / 9,971 / 10,522 / 8,836 / 13,621 / 13,132 / 6,919 / 506 lines, `cross_venue_live/` 404 MB with 9 quote
  day-files (sealed), `surprise_live/alerts.jsonl` 18,000 lines over 75 passes (sealed), 56 GB of disk free, about 3.9 GB
  of RAM available, both monitors running, last pass end 00:57Z.

**Structural facts from this round's host probes (read-only, counts only; 2026-10-20 01:40-01:52Z; six streaming
scripts hashed locally and on the host before running, run as `nice -n 19 /home/opc/arepo/.venv/bin/python -I` from
`/tmp`, then removed; inputs: the 12 captures of 2026-10-15 (worn by CB17 P3), one sidecar, the 2026-10-15 monitor file
(worn by CB17 P1), and, disclosed, three 2026-10-16 trade samples and the 2026-10-16 monitor file for *features only*
(transaction-hash uniqueness, price decimals, timestamp clustering: no mark-out, no forward price, no outcome; 10-16 is
inside J4-R's window, which round 8 refuses only for maker-mark-out objects). Mid changes were read k-1 -> k only, the
interval itself, never a later capture. No `side`, wallet field, outcome or target was decoded. Scripts verbatim with
sha256 in §5.)**
1. **Most 2 h price moves on the venue happen without a trade.** Over the 11 intervals of 2026-10-15, 584,022 eligible
   market-interval pairs (two-sided, spread <= 10c, mid in [0.02, 0.98]; about 53,100 per interval) produced 77,732
   movers with |d mid| >= 1c (13.3%; 29,257 >= 3c). Among movers, Gamma `last_trade_price` was **unchanged in 28,842
   (37%) and absent at both ends in 37,058 (48%: markets that have never traded)**; it moved with the mid in 9,272
   (12%) and against it in 2,560 (3%). `volume24hr` was exactly unchanged for 56,063 movers (72%). Gamma's own
   `chg_1h` is non-zero for every quote-only mover where present (23,951 of 23,951), so it tracks quotes, not trades.
   **Non-sports share (four intervals 10:31-16:31Z): 11,017 movers of 67,879 eligible (16%); quote-only 6,610 (60%),
   never-traded 1,470 (13%), traded 2,937 (27%).** Sports: 20,432 movers; 73% in never-traded markets (§CH156).
2. **Quote-only moves have an anatomy.** Non-sports quote-only movers (8,080 in four intervals): both sides moved the
   same way by the same amount (**parallel re-centering**) 1,016 (13%); same way, unequal 3,402 (42%); **one side only**
   2,212 (27%); the two sides in opposite directions (a spread change) 1,450 (18%). At >= 3c: 242 / 1,538 / 396 / 608
   (§CH156). Ladders: 8,867 event-intervals with >= 3 eligible members had at least one quote-only mover; in **250 (2.8%)
   at least 80% of the members re-centred in the same interval**, in 1,156 half or more, in 7,461 fewer than half (§CH159).
3. **The venue tilts.** Movers went up (outcome-0 mid rose) in 44,630 and down in 33,102 (57% up), and up exceeded down
   in every one of the 11 intervals (55-60%). One day cannot say whether the tilt is the day's news, time decay of
   favourites or systematic flow; the census counts it by class (§CH158).
4. **Within-market contrasts have units.** In one day, 3,872 markets had both a quote-only and a traded mover, 9,091
   only quote-only movers, 2,720 only traded movers (§CH156).
5. **Volume surges are common and mostly come with a move.** `volume24hr` at least tripled with at least $500 added in
   2,229 market-intervals a day (203 per interval); **503 of them with |d mid| < 1c**. Non-sports (four intervals): 258
   surges, 77 without a move (about 775 and 230 a day) (§CH157).
6. **Resolutions are not observable in the snapshot stream.** Between the first and last capture of 2026-10-15 no
   market flipped `closed` false -> true; **24,071 markets simply left the listing.** Closed and resolved markets are
   not in the complete-universe capture; a resolution-based live test needs a light Gamma fetch of the departed ids
   (about 240 requests a day at 100 ids each) (§CH163, §CH167).
7. **Every trade-sample row is its own transaction.** In three 2026-10-16 samples (220,931 / 218,541 / 219,610 rows,
   2,000 markets each) **no `tx_hash` appears twice**: 659,082 rows, 659,082 transactions, 0 multi-fill groups; the
   union across the three samples is 569,590 distinct (market, tx). The Data API returns **one aggregated row per
   taker order** (round 8's `tx16` never spanning two markets was the same fact seen from the monitor). A multi-level
   fill cannot be seen as several rows (§CH168).
8. **But it can be seen in the price.** Of 220,931 taker rows in one sample, the price had <= 2 decimals in 133,960
   (61%), exactly 3 in 36,089 (16%) and **>= 4 in 50,882 (23%)**. In markets whose sidecar tick is 0.01 (136,476 rows),
   **31,126 prices (23%) have >= 4 decimals and 665 have 3**; in 0.001-tick markets 19,756 of 84,455 (23%) have >= 4. No
   resting order can sit off its market's tick grid, so an off-grid taker price is the volume-weighted average of a fill
   across two or more price levels (or two makers at different prices): **a walked book.** Large prints: on 2026-10-16,
   856 of 2,164 non-sports monitor prints (40%) and 2,134 of 6,672 sports prints (32%) had >= 4 decimals; in 1c-tick
   markets 2,575 of 5,976 prints (43%) were off-grid (§CH160, §CH161, §CH168). **This also bears on CB16-Q**, whose
   premise reads a sub-cent print as a bot-grain *quote*: in a 1c-tick market it cannot be a quote at all (§CH168).
9. **Taker rows arrive in clusters.** In one sample's 6 h pre-origin windows: 943 markets with a row, 7,105 rows, **5,523
   (78%) within 300 s of another row in the same market**; 587 markets with >= 2 rows, 303 with >= 5, **288 with both
   isolated and clustered rows** (the within-market contrast has units). Monitor (2026-10-15, 10,522 prints, 96% enriched,
   22% non-sports): **7,234 prints (69%) had a prior print in the same market within 30 min; non-sports 859 of 2,273
   (38%) in 277 markets**; 5,662 within 5 min; 1,993 markets printed (§CH162).
10. **Large longshot prints are few but present.** 2026-10-15: 3,803 prints >= $2,500; 790 at a token price <= 0.35;
    249 both; **95 non-sports (34 markets, 26 events; 19 at <= 0.20)**; 579 non-sports prints >= $2,500 at >= 0.65.
    Category labels on the monitor are `fee_type` with a slug fallback (politics 446, crypto 586, economics 195,
    culture 98, finance 85, unknown 422, slug-derived 400) (§CH164).

**The reading that steers this round.** The host records three things at scale that no batch has used as a state:
- **(a) Whether a move was traded or quoted.** Eighty-five percent of 2 h moves on the venue have no trade behind them.
  Every reversal and continuation test AREPO has run (E001, E002, E004, E006, E012's draft) pooled quote-only moves,
  one-sided quote moves and traded moves, and the bounce critique of E012 is really a statement about that mixture.
  Splitting it is free, universe-wide and within-market (family A).
- **(b) Whether a taker walked the book.** The Data API aggregates each taker order into one row; the aggregate's
  off-grid price is a wallet-free, side-free, universe-wide urgency marker that no AREPO test has read as such, and
  that CB16-Q is about to read as something else (family B).
- **(c) When, within a market, flow arrives in trains.** Seventy-eight percent of taker rows have a neighbour within
  five minutes; the position in the train is the copycat clock (family B).
- **(d)** Two literature gaps fit light collectors (resolution fetch) or the monitor plus the frozen LABELLER (family C),
  and the cross-venue stream has two cheap successors once E009/E010 close (family D). Two maps unlock the honesty of
  everything else (family E).

**Data labels.** `A` = on the host now or written by its running collectors: complete-universe 2 h captures
(`rows.csv.gz`: `best_bid`, `best_ask`, `spread`, `last_trade_price`, `chg_1h/1d/1w`, `liquidity`, `volume24hr`,
`end_date`, `updated_at`, `closed`, `active`, `binary`, `event_id`, `neg_risk*`; no question text) with the sidecar
`rows_ext.csv.gz` (`fee_type`, `fee_category`, `taker_base_fee`, `order_price_min_tick_size`, `order_min_size`,
`rewards_*`, `clob_rewards`, `created_at`, `uma_resolution_statuses`, `event_open_interest`, `event_volume`,
`event_comment_count`, `series_slugs`, `parent_event_ids`); book sweeps twice per pass (`best_bid/ask`, `*_size_1`,
`depth_*_1c/5c`, `n_*_levels`, `book_timestamp`, `book_hash`, `tick_size`); active-frame trade samples (2,000 markets a
pass, the newest 500 taker rows each: `ts, side, price, size, outcome_index, asset, tx_hash`; `features.csv.gz` with
`origin_utc`, `stratum`, `n_trades_1h`, `time_since_last_trade_s`, `trades_truncated`); the live large-trade monitor
(prints >= $1k every 5 min: `ts`, `recv_ts`, `price`, `size`, `cash`, `outcome_index`, `token_id`, `tx16`, `title`,
`slug`, `ctx_*` incl. `ctx_question`, `ctx_fee_type`, `ctx_market_id`, `ctx_event_id`, `ctx_created_ts`, `ctx_end_ts`;
`side` and wallet fields exist and are governed by CB17's branch rule and the standing wallet-free rule); the
cross-venue poller (200 pairs, 120 s: Kalshi `yes_bid/ask`, sizes, last; Polymarket CLOB best bid/ask, sizes,
`book_timestamp`; **sealed to 2026-11-03**). `P` = a keyless fetch is needed (named where light). **Sealed and not
usable by anything here:** everything rounds 4-8 list, plus LT2's windows and `live_tests2/` (if registered), CB17's
SCREEN_8/REP_8 stores (collection overlap only), E009/E010's `cross_venue_live/` to 2026-11-03 and E011's
`surprise_live/` to 2026-11-10. **J4-R `[2026-10-16, 2026-10-21)` is refused for every maker-mark-out object**; the
features-only reads of 10-16 above are disclosed and are not such objects.

**Windows and registration this round proposes.** A third live-test family, **LT3**, registered separately from LT2 and
after it, with its own Holm family: origin window of **21 days from the first 00:00Z at least 24 h after the registration
commit and not before 2026-10-24T00:00Z**, a single analysis at least 36 h after the end, a pre-declared 28-day
extension only if a declared counts-only gate falls short (the gate is read before any outcome). Collection overlap
with LT2, E011, CB17's SCREEN_8 and CB16's SCREEN_A is disclosed and is overlap only: different hypotheses, no pooling,
stores never opened by one another. E-numbers are assigned at registration, not here.

**Hygiene that binds every idea.** Decision time is the row's own receipt (`received_utc`), the sample's `origin_utc`
or the print's venue `ts`, never a later capture; states are computed from the decision-time capture and strictly
earlier ones; targets are price-based (the next complete captures' mids, J4-R tightness at both ends, 2 h / 6 h / 24 h)
and never read Gamma outcome fields; clustering is event x UTC day with the pass as a way; **the primary is a
within-unit contrast or a composition placebo (label shuffle within the unit; J4-R increment bootstrap for
reversal-type objects), never a cyclic shift** (LT2 round 1); the cumulative count (M3) is recorded at every counting
job; sports stays a parameter (the category rule is the sidecar `fee_type` / `fee_category` plus CB17's frozen sports
series list; nothing here is sports-only, and every print-level idea reports the sports arm uncounted).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = a pure reader on host streams, 5 = new
collector plus weeks). My judgement, not measurements. Cost conventions as rounds 1-8 and `EXECUTION_COSTS.md`: taker
fee `rate*p*(1-p)` per leg; median 5-share round trip **4.5c** (liquid >= $100k 1.8c; politics 3.6c; crypto 4.5c);
one-leg hold-to-resolution 1.5-2.5c above 0.80; passive entry has paid 1-7c of adverse selection in every study; the
monitor shows a print a median 9 minutes after its venue time, so taker-follows-the-print routes are reported only.

**Counts table (what was counted before each idea was written).**

| ID | Unit | Count on the host (daily unless stated) | Source |
|---|---|---|---|
| CH156 | eligible market x 2 h interval with a >= 1c mid move, classed traded / quote-only / one-sided / never-traded | 77,732 movers a day of 584,022 pairs; non-sports about 2,750 an interval (60% quote-only, 27% traded, 13% never-traded); 3,872 markets a day with both a quote-only and a traded mover | P1, P1b |
| CH157 | market x interval with `volume24hr` >= 3x and >= +$500 | 2,229 a day (503 without a move); non-sports about 775 (230 without a move) | P1, P1b |
| CH158 | pass x market: the venue-wide up-share among movers, excluding the market's event | 12 passes a day; 55-60% up in each of 11 intervals | P1 |
| CH159 | neg-risk event x interval with >= 3 eligible members and >= 1 quote-only mover | 8,867 per four intervals (about 26,000 a day); breadth >= 80% in 2.8% | P1b |
| CH160 | large print with an off-grid (aggregated) price | 2,164 non-sports prints a day, 856 (40%) >= 4 decimals; 1,919 prints in 1c-tick markets >= 4 decimals | P2b, wc |
| CH161 | market x trade sample with >= 1 taker row in the 6 h window; walk share definable | 943-1,080 of 2,000 per sample (12 a day); 23% of rows walked | P2, P2b, P2c |
| CH162 | print with a prior print in the same market within 30 min; taker row with a same-market neighbour within 300 s | 7,234 prints a day (non-sports 859 in 277 markets); 5,523 of 7,105 rows per sample | P3, P2c |
| CH163 | standalone binary market reaching its end (resolution via a light fetch) | 45,089 standalone eligible pairs a day (7.7%); 24,071 markets leave the listing a day | P1 |
| CH164 | non-sports print >= $2,500 at a token price <= 0.35 | 95 a day in 34 markets / 26 events (19 at <= 0.20) | P3 |
| CH165, CH166 | cross-venue pair x 120 s poll (from 2026-11-04) | 200 pairs x 720 polls a day (unprobed: sealed) | spec |
| CH167, CH168 | maps: listing exits; never-traded universe; aggregation and grain | 24,071 exits a day; 48% of movers never traded; 23% of rows off-grid | P1, P2b |
| rejected | multi-fill transactions; `closed` flips in captures; `ctx_mid` / `ctx_chg_1h` as print states | 0 of 659,082; 0; post-print (leak) | P2, P1, monitor doc |

---

## 1. Map: where money might be, given the survivors, the nulls and the probes

| Family | What the evidence and the probes suggest | Money route |
|---|---|---|
| A. Move composition on the complete universe | 85% of 2 h moves have no trade behind them; one-sided quote moves are the bounce the reversal tests may have been measuring; 57% of movers tilt up; 2.8% of ladder-intervals re-centre as a whole | maker: follow parallel re-centerings, quote inside one-sided withdrawals, do not fade traded moves that confirm; taker: fade only the class that reverts, reported against 4.5c; the common tilt as a fade clock |
| B. Transaction shape | every taker order is one aggregated row; 23% of rows and 40% of large non-sports prints are off-grid (walked); 78% of rows arrive in trains | maker protection: widen after walked prints, not after touch fills; a flow-continuation moderator that no pooled flow test had; copycat trains as the uninformed tail of the flow |
| C. Structure and class | standalone binaries are 7.7% of the eligible universe and have no complement constraint on YES-buying; 95 non-sports longshot prints >= $2.5k a day in leak-prone classes | NO-side carry in standalone binaries (gap 2); class-conditioned longshot follow (gap 1), both needing a light resolution fetch for the carry arm |
| D. Cross-venue successors (from 2026-11-04) | the Kalshi lead is the only replicated predictor; 30% of large moves are Polymarket-led | fade Polymarket-led moves Kalshi does not confirm; the lead as a liquidity-location fact |
| E. Maps | resolutions leave the listing; the Data API aggregates; CB16-Q's grain premise | the gates every idea above cites, and a correction to a drafted batch's premise |

---

## 2. Hypotheses

### A. Move composition on the complete universe (parents E002, E006, E012 draft, CH80, CH35, CH56; literature: Hasbrouck 1991, Copeland and Galai 1983, Nagel 2012)

**CH156. Quoted moves and traded moves are different animals: a 2 h mid move with no trade behind it is either a
maker's re-centering (both sides move together: information from outside the book) or a one-sided withdrawal (the
mid moves half-way because one quote left: the bounce), while a traded move is a taker pushing the touch; the venue's
documented short-horizon reversal lives in the one-sided class, parallel re-centerings persist, and traded moves sit
between; a maker who re-centres with the bots and quotes into one-sided withdrawals keeps the spread, and a taker who
fades only one-sided quote moves fades the only class that reverts.**
- Mechanism and who pays: Hasbrouck (1991) separates quote revisions that follow trades (private information revealed by
  order flow) from those that do not (public information absorbed by the quoter); Copeland and Galai (1983) make the
  one-sided withdrawal the maker's defence against a feared informed taker; the bid-ask bounce is the mechanical
  half-move of the mid when one side moves and returns. On Polymarket the three are distinguishable from the capture
  alone: `last_trade_price` and `volume24hr` say whether anything traded (fact 1), and the two sides' changes say how the
  quotes moved (fact 2). Who pays: whoever fades a parallel re-centering (a bot's model moved; it will not come back),
  and whoever chases a one-sided withdrawal (the side returns and the mid halves back). Why the crowd misses it: the
  interface shows a price chart, not whether the chart moved on a trade; every AREPO reversal test pooled the classes,
  and the LT2 challenger's bounce objection to E012 is exactly the pooled mixture.
- Population and count (`A`, live-ready): about 7,000 movers per interval (77,732 a day) over about 53,000 eligible
  pairs; **non-sports about 2,750 an interval: quote-only 60%, never-traded 13%, traded 27%**; quote-only anatomy
  parallel 13% / same-side unequal 42% / one-sided 27% / spread-change 18% (facts 1-2). In 21 days: about 690,000
  non-sports movers, of which about 185,000 traded, 415,000 quote-only and 90,000 never-traded. Within-market: 3,872
  markets a day hold both a quote-only and a traded mover (fact 4).
- Test (live-ready; within-market, composition placebo). Unit: market x interval with |x| >= 1c, `x = mid_k - mid_{k-1}`.
  Decision time: capture k's `received_utc`. State: class from captures k-1 and k only: **traded** (`last_trade_price`
  changed, or `volume24hr` changed when the price did not), **parallel** (both sides moved the same way within 0.5c of
  each other, no trade), **same-side unequal**, **one-sided** (one side within 0.05c of unchanged), **spread-change**
  (sides moved in opposite directions), **never-traded** (`last_trade_price` absent at both ends). Target: the signed
  continuation `c = sign(x) * (mid_{k+1} - mid_k)` at 2 h and the 6 h version (J4-R tightness at both ends; two-sided at
  the target). **Primary: within-market difference of mean `c` between the market's one-sided movers and its traded
  movers, over markets holding both classes in the window; a second primary, parallel minus traded; event x UTC-day
  clusters with the pass as a way; floor 0.5c; placebo: shuffle the class label across the market's movers (the
  within-unit shuffle), <= 1.5% of draws may qualify; and the J4-R increment bootstrap for the pooled reversal
  slope by class (reported).** Pre-declared direction: one-sided minus traded < 0 (one-sided reverts more); parallel
  minus traded > 0 (re-centerings persist more). Secondary: the never-traded class on its own (for sports it is a
  wallet-free proxy for the books' line moves, reported uncounted as the category parameter requires); the class x
  price-band cross-tab (fees are maximal at 0.5); the class x |x| dose.
- Economic route: (1) maker, primary: paper quotes re-centred with the parallel class (the avoided-fill mark-out of a
  maker who does not fade it) and paper bids inside a one-sided withdrawal (the half-spread captured when the side
  returns); (2) taker: fade one-sided quote moves of >= 3c at the recorded touch, round trip to k+1, reported against
  4.5c median / 1.8c liquid (E004's pooled reversal failed costs; the conditional class is reported, not promised).
- Kill criteria (counts only, features only): fewer than 2,000 non-sports markets with both a one-sided and a traded
  mover in the window; the traded class under 15% or over 60% of non-sports movers (one arm too thin or the label
  broken); `last_trade_price` absent for more than 60% of non-sports movers (then the label is a field-presence
  artefact and the census says so); or the within-market placebo advances.
- Planning MDE versus floor: with about 185,000 traded and 135,000 one-sided non-sports units in 21 days, clusters in
  the thousands and a 2 h continuation SD of about 4c, the planning MDE on the within-market difference is about
  0.1-0.2c against the 0.5c floor; the floor binds, not power. The risk is attribution (bounce versus information), which
  is why the class is defined from the two sides' changes and not from the mid alone.
- Cost hurdle: none for the maker arm; the taker fade must clear 4.5c on a 3c trigger and is reported only.
- Live-ready: **yes.** A pure reader over consecutive captures, `cpu` lane, under 350 MB (P1 ran at 311 MB over 12
  captures). Expected counts per day: 77,732 movers, 2,750 non-sports an interval. C 1.
- Leakage and confounds: a trade at the same price as the previous one leaves `last_trade_price` unchanged
  (`volume24hr` catches it; the strict class requires both unchanged); `volume24hr` is a rolling window, so an exact
  non-change means no trade in the interval and nothing rolling off (72% of movers); a one-sided move can be a fill
  that emptied a level without changing `last_trade_price` (rare, and the trade label catches most); stale quotes
  (CH146's clock) are a way; the capture is up to 2 h after the move. **Bounce exposure stated:** the one-sided class is
  the bounce by construction; that is the point, and the parallel class is where bounce cannot be. Sports is a parameter.
- Novelty: CH80 is dust at the touch, CH35 the vacuum, CH56 the seed anchor, E012 the liquidity moderator. New: the
  move's composition (traded / parallel / one-sided / never-traded), read from the capture pair, as the moderator of
  reversal, universe-wide. N 5, EV 4, C 1.

**CH157. Attention without a price: a market whose 24 h volume at least triples in one 2 h interval while its mid barely
moves has just been *noticed* (a share, a post, a listing on the front page); attention on this venue buys YES, so the
noticed market's YES drifts up over the next 24 h; the drift is a demand effect, not news, so it reverts by resolution,
and the NO side of a noticed standalone binary, bought after the drift, is the carry.**
- Mechanism and who pays: Gervais, Kaniel and Mingelgrin (2001) found that unusually high volume raises a stock's
  visibility and its subsequent return (the high-volume return premium); Barber and Odean (2008) that attention drives
  individual investors to *buy*; Miller (1977) that one-directional demand with limited shorting overprices. Here the
  surge-without-move isolates attention from information (information moves the price; attention moves the volume), and
  the venue's retail bias to buy YES (takers buy YES about 60% of the time on Kalshi; 78% of Polymarket markets resolve
  No) gives the demand a direction. Who pays: the attention buyer who holds. Why the crowd misses it: the surge is
  visible as a volume rank, but nobody separates the surges that moved the price from those that did not.
- Population and count (`A`, live-ready): 2,229 surges a day (`volume24hr` >= 3x and >= +$500 over one interval), 503
  without a move; **non-sports about 775 a day, 230 without a move** (fact 5). In 21 days: about 16,000 non-sports surges,
  about 4,800 without a move. Standalone binaries are 7.7% of eligible pairs (about 4,100 markets per capture), so the
  standalone subset is about 1,200 surges in 21 days.
- Test (live-ready; composition placebo primary, within-market secondary). Unit: market x interval with a surge.
  Decision time: capture k's `received_utc`. State: surge with |x| < 1c (attention only) versus surge with |x| >= 1c
  (attention with news), and the no-surge baseline. Target: the signed 24 h change of the outcome-0 mid (YES for yes/no
  and ladder-member markets; sports excluded in the primary because outcome 0 is a team). **Primary: mean 24 h YES
  change after attention-only surges minus the matched baseline (same market's non-surge intervals in the window, or
  the same category x volume decile x price band cell), event x UTC-day clusters; floor 1.0c; placebo: shuffle the surge
  label across the market's intervals (within-market) and, for the cell version, within cell (composition).**
  Pre-declared direction: positive. Secondary: ladder members versus standalone (both predicted positive at 24 h; only
  standalone lacks the complement constraint by resolution); the surge dose (3x, 5x, 10x); the 6 h version.
- Economic route: (1) maker, primary: skew quotes up after an attention-only surge (lift the ask: the avoided
  adverse fill); (2) carry (reported; the resolution arm is `P`, a light fetch per CH167): buy NO on a standalone
  binary at the recorded touch 24 h after the surge and hold to resolution, paying 1.5-2.5c once; (3) the taker buy of
  YES at the surge, round trip to +24 h, must clear 3.6-4.5c and is reported only.
- Kill criteria: fewer than 1,500 non-sports attention-only surges in the window; fewer than 300 standalone ones (then
  the carry arm is not powered and is dropped, the 24 h arm stays); surges concentrated in fewer than 100 events (a
  single news cycle); or the placebo advances.
- Planning MDE versus floor: about 4,800 non-sports attention-only units with clusters of about 2,500 and a 24 h SD of
  about 6c: planning MDE about 0.4c against the 1.0c floor; the standalone subset alone (about 1,200) gives about 1.0c,
  borderline, hence the 28-day pre-declaration for the carry arm.
- Cost hurdle: maker arm none; the carry pays 1.5-2.5c once and needs a 2c excess NO rate (the resolution arm only);
  the taker buy must clear 4.5c and is expected to fail.
- Live-ready: **yes** (24 h arm). The resolution arm needs CH167's light fetch (`P`). Pure reader, under 350 MB. C 1
  (24 h arm), 2 (carry arm).
- Leakage and confounds: a surge without a move can be a wash cycle or a reward farmer's own volume (CH41, CH72; the
  census reports the share of surges with `volume24hr` falling back within 24 h); `volume24hr` is a rolling window, so
  "3x" compares against the previous day's trailing volume (the dose is relative, by design); new markets have no
  trailing volume (`volume24hr` from 0: excluded, CH154 owns them); the YES-direction convention is outcome 0 in
  `rows.csv.gz`, which is "Yes" for yes/no markets and the named member for ladders (the C1/T5 label-ordering caveat is
  checked once at the census on `ctx_question` text from the monitor for the markets it covers).
- Novelty: CH24 is category attention shocks, CH97 Wikipedia attention, CH132 silence before a print, CH26 inattention.
  New: the market-level volume surge *without* a price move as the attention clock, and its YES-direction prediction.
  N 4, EV 3, C 1-2.

**CH158. The venue tilt as a common factor: on one day 57% of all movers moved up, in every interval; if the share of
movers going one way (computed over the whole universe excluding the market's own event) varies across passes, it is
a venue-wide flow or liquidity shock, not information about any one market; the component of a market's move that is
aligned with the tilt reverts and the orthogonal component persists; the tilt is a free fade clock.**
- Mechanism and who pays: Nagel (2012) shows that short-term reversal returns are the compensation for liquidity
  provision against common demand shocks; Hendershott and Menkveld (2014) that inventory pressure creates transitory
  common price components. On a venue whose takers buy YES, a retail inflow hour tilts thousands of unrelated markets
  the same way; makers absorb it and the tilt unwinds. Who pays: the inflow. Why the crowd misses it: nobody watches
  the cross-section of 50,000 markets at once; each trader sees one chart.
- Population and count (`A`, live-ready): every mover, with a pass-level state; 12 passes a day (252 in 21 days); fact 3
  (55-60% up in each interval of 10-15). Whether the tilt *varies* enough to be a state is the first census question.
- Test (live-ready; within-market, two-level). Unit: market x interval with |x| >= 1c. Decision time: capture k. State:
  the leave-one-event-out up-share `u_{-e}(k)` among non-sports movers at k, and the market's alignment `a = sign(x) *
  (2 u_{-e} - 1)`. Target: `c` at 2 h and 6 h (as CH156). **Primary: within-market slope of `c` on `a` (the market's own
  aligned versus anti-aligned moves), event x UTC-day clusters with the pass as a way and a pass-level cluster check
  (252 clusters); floor 0.5c per unit of `a`; placebo: shuffle the pass-level tilt across passes (the composition
  placebo: breaks the tilt, keeps every market's own moves).** Pre-declared direction: negative (aligned moves revert).
- Economic route: maker skew against the tilt in the following pass; taker fade of aligned >= 3c moves reported.
- Kill criteria: the interquartile range of `u_{-e}` across the window's passes is under 4 percentage points (no
  variation: then the tilt is a constant drift and the idea dies); fewer than 150 passes with movers; or the placebo
  advances.
- Planning MDE versus floor: units in the hundreds of thousands, but the effective sample is the pass (252): planning
  MDE about 0.3-0.5c per unit of `a` against 0.5c; borderline by design, honest about the cluster count.
- Cost hurdle: maker none; taker 4.5c.
- Live-ready: **yes**, the same reader as CH156 with one more pass-level number. C 1.
- Leakage and confounds: time decay of favourites tilts outcome-0 mids up mechanically if outcome 0 is more often the
  favourite (the census reports the up-share among movers with mid > 0.5 and < 0.5 separately, and the primary uses the
  demeaned tilt within price band); a single large event (an election night) can dominate a pass (leave-one-event-out
  handles the market's own event, and the census reports the top event's share of movers per pass).
- Novelty: CH36 is synchronised vacuums, CH24 category attention. New: the universe-wide tilt as a market-level state.
  N 3, EV 2-3, C 1.

**CH159. Ladder breadth: when at least 80% of a neg-risk event's members re-centre in the same interval with no trade,
one program updated its model of the whole distribution (the spot moved; the poll came out), and the move persists;
when one member re-centres alone and untraded, its maker left or revised alone, and the move reverts toward the
siblings' implied value; the breadth of a quote-only move is a wallet-free label of its author.**
- Mechanism and who pays: a ladder is quoted by few programs that price every member from one input; a model update
  moves all members at once with no trade (fact 2: 250 event-intervals in four intervals at >= 80% breadth). A single
  member's untraded move is a local quote event. Who pays: the taker who fades a whole-ladder re-centering, and the maker
  who follows a lone member's drift away from the ladder's implied value. Why the crowd misses it: ladder members are
  separate markets on the venue; the event view shows prices, not that they all moved without a trade.
- Population and count (`A`, live-ready): 8,867 event-intervals with >= 3 eligible members and >= 1 quote-only mover in
  four intervals (about 26,000 a day); breadth >= 80% in 250 (2.8%), 50-80% in 1,156, < 50% in 7,461. In 21 days: about
  15,000 high-breadth and 450,000 low-breadth event-intervals before the non-sports and neg-risk filters.
- Test (live-ready; within-event, composition placebo). Unit: event x interval (neg-risk events, >= 3 eligible members)
  with a quote-only mover. Decision time: capture k. State: breadth `b` = share of eligible members with a quote-only
  mover at k, binned (>= 0.8, 0.5-0.8, < 0.5). Target: members' signed continuation `c` at 2 h, averaged within the
  event-interval. **Primary: within-event difference of `c` between the event's high-breadth and low-breadth intervals,
  event x UTC-day clusters with the pass as a way; floor 0.5c; placebo: shuffle `b` across the event's intervals.**
  Pre-declared direction: high minus low > 0. Secondary: the sum-of-asks deviation (E005's object) before and after
  each class, reported; single-market events excluded (breadth undefined).
- Economic route: maker, primary (do not fade whole-ladder re-centerings; quote the lone mover back toward the ladder's
  implied value); taker reported only.
- Kill criteria: fewer than 300 non-sports neg-risk events with at least one high-breadth and one low-breadth interval
  in the window; or the placebo advances.
- Planning MDE versus floor: about 1,000-3,000 high-breadth non-sports event-intervals in 21 days against tens of
  thousands low-breadth, event clusters about 1,000: planning MDE about 0.4-0.6c against 0.5c: borderline; the 28-day
  pre-declaration carries it.
- Cost hurdle: maker none.
- Live-ready: **yes**, the CH156 reader grouped by event. C 1.
- Leakage and confounds: a traded move in one member re-centres the siblings mechanically (E005's band): intervals with
  any traded member are reported separately; sports ladders (game markets) are a parameter; crypto strike ladders are
  the natural high-breadth class and are reported as a class.
- Novelty: CH09/CH12/CH13 are ladder consistency and arbitrage; CH153 is synchronous *prints*; E005 the band. New: the
  breadth of *untraded* re-centering as the author label (program versus lone maker). N 3, EV 3, C 1.

### B. Transaction shape: walked prints and trains (parents CH131 / CB16-Q, CH69, CH55, E007, E013 draft; literature: Biais, Hillion and Spatt 1995, Harris and Hasbrouck 1996, Kaniel and Liu 2006, Barber, Odean and Zhu 2009)

**CH160. Walked prints: the Data API returns one row per taker order, so a taker who walked two or more price levels
leaves one row whose price is a volume-weighted average off the market's tick grid; an off-grid price is therefore a
wallet-free, side-free urgency marker (the taker paid more than the touch to get size now); within a market, the
maker's 2-4 h mark-out on walked prints is worse than on touch-only prints of the same size, and the maker who widens
after a walked print and not after a touch fill protects against the only flow that reliably hurts.**
- Mechanism and who pays: order aggressiveness carries information (Biais, Hillion and Spatt 1995; Harris and Hasbrouck
  1996); informed traders with short-lived information use market orders and accept price impact (Kaniel and Liu 2006).
  Here aggressiveness is written into the price's decimals: no resting order can sit off the tick grid, so a 1c-tick
  market cannot print 0.4537 unless the order filled across levels (fact 8). Who pays: the maker whose deeper levels were
  taken. Why the crowd misses it: the decimals look like noise; CB16-Q is about to read them as the *quoter's* grain,
  which in a 1c-tick market they cannot be.
- Population and count (`A`, live-ready): 2,164 non-sports prints on 2026-10-16, **856 (40%) with >= 4 decimals**; 1,919
  prints in 1c-tick markets with >= 4 decimals (plus 656 with 3: 43% off-grid), 6,672 sports prints with 2,134 walked
  (fact 8). In 21 days: about 18,000 walked and 27,000 touch-only non-sports prints. Markets with both kinds: to be
  counted by the census (fact 9's 277 non-sports multi-print markets a day bounds it).
- Test (live-ready; within-market, composition placebo). Unit: large print. Decision time: venue `ts`. State: walked
  (price off the market's tick grid at the print, from the sidecar `order_price_min_tick_size` of the last capture;
  strict class: >= 4 decimals, which is off-grid under both tick regimes) versus touch-only (on-grid). Direction:
  Data API `side` under CB17's branch S (q0400's >= 97% agreement rule); under branch T the print-level test is withdrawn
  uncounted and the family runs on CH161 only. Target: CB13-T's 2-4 h and 6-8 h print-based mark-out from the next
  complete captures (J4-R tightness). **Primary: within-market difference of the maker-adverse mark-out between walked
  and touch-only prints (markets with both in the window), event x UTC-day clusters with an hour-of-day way; floor
  0.5c; placebo: shuffle the walked label within market x size band.** Secondary: the dose (distance of the aggregate
  price from the last capture's touch, a lower bound on the walk depth); the walked share by class and hour.
- Economic route: maker protection (the paper maker's net on walked versus touch-only fills; widen or pull for one pass
  after a walked print); taker follow of walked prints at the recorded ask reported against 4.5c and the 9-minute lag.
- Kill criteria: fewer than 1,500 non-sports markets with both classes in the window; the walked share of non-sports
  prints under 15% or over 70%; branch T (then withdrawn uncounted, CB17 precedent); or the placebo advances.
- Planning MDE versus floor: about 18,000 walked and 27,000 touch-only non-sports prints, markets with both perhaps
  3,000, event clusters about 1,500, mark-out SD about 4c: planning MDE about 0.3-0.5c against 0.5c: adequate on 21
  days, comfortable on 28.
- Cost hurdle: maker none; taker 4.5c plus the receipt lag.
- Live-ready: **yes** (monitor file plus one sidecar per print; under 300 MB). C 1.
- Leakage and confounds: two makers at *different* prices filled by one order also yield an off-grid average (that is
  still a walk); a 0.001-tick market's on-grid prints have 3 decimals (the strict >= 4 rule is off-grid in both
  regimes; the tick is read at the print's last capture and the 0.96 / 0.04 regime flips are a way); the Data API
  could in principle round or truncate (CH168's map checks the decimal-length distribution against the two grids);
  size and walking are correlated (the size band way). Sports is a parameter.
- Novelty: CH131 / CB16-Q read the grain as the quoter's footprint; CH111 the taker's dollar shape; CH69 clip trains.
  New: the aggregation fact (7) and its consequence: the off-grid price as the taker's walk. N 4, EV 4, C 1.

**CH161. Walked flow continues: in the trade samples, the share of a market's 6 h signed taker flow that arrived in
walked rows (off-grid prices) moderates E007's flow continuation; flow that paid for immediacy continues, flow that
patiently took the touch does not; the moderator is wallet-free and uses the `side` convention E007 and E013 already
use.**
- Mechanism and who pays: as CH160, at the flow level: the same signed share, split by how it was executed. E007's
  pooled continuation is +0.36c; SB2's F4 and F5 moderators (volatility, spread) are liquidity states; this is a state
  of the *flow itself*. Who pays: the maker who treats patient and urgent flow alike; the taker who follows patient
  flow.
- Population and count (`A`, live-ready): 943-1,080 of 2,000 sampled markets per pass have a taker row in the 6 h
  pre-origin window (fact 9; LT2's census found about 1,000 rows per sample with 6 h flow); 23% of rows are walked
  (fact 8); 12 samples a day; in 21 days about 250,000 market-samples with 6 h flow, of which the walk share is
  non-degenerate (strictly between 0 and 1) in perhaps 40%.
- Test (live-ready; E013's estimator with a new moderator). Unit: market x trade sample. Decision time: `origin_utc`.
  Flow: `x6` as E013 (signed share over rows with `t - 6 h <= ts < t`, the E007 sign convention from `side` and
  `outcome_index`); moderator `W` = walked share of |signed volume| in the window, standardised to `zW` with a
  pre-window census scale; coverage defined from the page's oldest row being at or before `t - 6 h` *as recorded at the
  origin* (LT2 round 1's selection objection: nothing after the origin decides inclusion). Target: `y6 = mid(slot k+3)
  - mid_i`. **Primary: expanding-past demeaned OLS of `y6` on `x6 * zW` with E013's controls plus `zW` and `x6`,
  one-sided for > 0, event-clustered and two-way event x UTC-day SEs; placebo: shuffle `W` across the market's samples
  (keeps every market's flow and timing, breaks the moderator), 200 draws; floor: the gross mid-to-mid move in the
  upper-`W` tercile at |x6| >= 0.5 must exceed 0.5c for the result to be called material.** Secondary: within-market
  (FE) slope; a 1 h version on E007's own unit; `W` defined on row counts rather than volume.
- Economic route: maker protection (skew against urgent flow for one pass); the taker follow in the favourable cell
  reported against 4.5c (expected "not shown", as E007).
- Kill criteria: `W` non-degenerate in fewer than 60,000 market-samples; its within-market interquartile range zero
  for more than half the markets with >= 3 samples; the walked share of rows under 10% in the window (then the Data API
  changed its aggregation and CH168 says so); or the placebo advances.
- Planning MDE versus floor: on LT2's arithmetic for F4 (SE scaled from h3 by cluster count, times 1.5 for proxy
  noise), the planning MDE on the interaction is about 0.0016-0.002 per SD of `zW`, about the size of the development F4
  and F5 effects; there is no development evidence for `W` (none existed: the aggregation fact is new), so this is a
  genuine first test, and "inconclusive" is a plausible outcome.
- Cost hurdle: maker none; taker 4.5c.
- Live-ready: **yes.** Pure reader over trade samples and captures (features and trades files, no wallets), under 300
  MB per sample (P2 ran at 232 MB over three). C 1. **Not an LT2 test:** LT2's family (E012-E014) is fixed; this is an
  LT3 member on the same stream, disclosed as shared data.
- Leakage and confounds: walking is more likely in thin books (spread and depth ways; F5's spread moderator is a
  control); large orders walk more (a notional way); the 0.001-tick regime makes 3-decimal prices on-grid (strict
  rule: >= 4 decimals); a market's walk share is persistent (within-market demeaning handles the level; the
  shuffle-within-market placebo tests the timing).
- Novelty: E007 / E013 are pooled and liquidity-moderated flow; CH92 is flow-skewed quoting; HB1's size features were
  pooled. New: the execution shape of the flow as its own moderator. N 4, EV 3, C 1.

**CH162. Trains and herds: 69% of large prints (38% non-sports) follow another print in the same market within 30
minutes, and 78% of sampled taker rows have a neighbour within five minutes; the first print of a train carries the
information and the follow-ons are copycats and chasers, so the mark-out of position-1 prints exceeds that of
position-2+ prints within the same market, and the share of a market's 6 h flow that arrived in trains moderates
continuation downward; the maker who widens at the first print and tightens into the train sells liquidity to the
copycats.**
- Mechanism and who pays: herding by individual investors is driven by attention and imitation and does not predict
  returns (Barber, Odean and Zhu 2009); ACDC's census of informed longshot bets documents copycat flow following the
  first print; the venue's activity feed shows every large print to everyone within seconds. Who pays: the copycat,
  who pays the post-print price for information already in it. Why the crowd misses it: a train looks like
  confirmation.
- Population and count (`A`, live-ready): prints with a prior print in the same market within 30 min: 7,234 a day,
  **non-sports 859 in 277 markets**; within 5 min 5,662 (fact 9). Taker rows: 5,523 of 7,105 per sample with a 300 s
  neighbour; 288 markets per sample with both isolated and clustered rows. In 21 days: about 18,000 non-sports
  follow-on prints and 29,000 first prints; about 70,000 market-samples with a mixed train structure.
- Test (live-ready; within-market, two arms). **Arm 1 (prints):** unit large print; decision time venue `ts`; state
  train position (1 = no same-market print in the prior 30 min; 2+ otherwise) and, within 2+, the same-direction flag
  (requires `side`: branch S; under branch T, the arm uses |mark-out| and is reported only); target CB13-T's 2-4 h and
  6-8 h mark-out; **primary: within-market difference position-1 minus position-2+ (same direction), event x UTC-day
  clusters; floor 0.5c; placebo: shuffle the position label within market x hour.** **Arm 2 (flow):** unit market x
  trade sample; moderator `H` = share of the 6 h signed volume in rows with a same-signed same-market neighbour within
  300 s; **primary: E013-form slope of `y6` on `x6 * zH`, one-sided for < 0; placebo: shuffle `H` across the market's
  samples.** Pre-declared directions: position-1 better; `H` negative.
- Economic route: maker: widen at the first print, tighten into the train (paper fills by position); taker: follow
  position-1 prints only, reported against 4.5c and the 9-minute lag (which makes most position-1 follows impossible
  in time: CH155's table says which classes).
- Kill criteria: fewer than 1,500 non-sports markets with both positions in the window; `H` degenerate in more than
  60% of market-samples; the 30-minute train rate for non-sports prints under 20% or over 70%; or the placebo advances.
- Planning MDE versus floor: arm 1 about 18,000 versus 29,000 non-sports prints in perhaps 2,500 markets with both,
  event clusters about 1,200, mark-out SD about 4c: planning MDE about 0.4-0.6c against 0.5c (borderline; 28 days
  pre-declared); arm 2 as CH161 (about 0.002 per SD).
- Cost hurdle: maker none; taker 4.5c plus lag.
- Live-ready: **yes** (monitor file; trade samples). C 1.
- Leakage and confounds: a train can be one trader's worked order (CH69's clip train; adjacent, and the reason this
  idea's novelty is modest); news arriving over minutes creates informed trains (the within-market contrast measures,
  not assumes); sports in-play dominates train counts (parameter); position depends on the monitor seeing the earlier
  print (the $1k floor and the 5-minute poll: the train definition uses venue `ts`, so the poll does not matter, but
  prints under $1k are invisible and the census reports train rates against the trade samples where both exist).
- Novelty: CH55 needed the leaderboard, CH69 is the worked order, CB16-U the silence before a print. New: train
  position and herd share as the copycat clock, on two streams. N 2-3, EV 3, C 1.

### C. Structure- and class-conditioned calibration (parents CH117, CH62, CH63, CH88, CH61, CH60; literature: Bartlett and O'Hara 2026, Mitts and Ofir 2026, ACDC 2026; prior-art gaps 1 and 2)

**CH163. Standalone binaries carry the YES premium, ladder members cannot: in a neg-risk ladder the members' YES prices
sum to about one, so retail YES-buying can only redistribute within the event (the favourite-longshot bias); in a
standalone yes/no market there is no complement constraint and YES-optimism is priced outright; at equal price and
horizon, standalone binaries resolve YES less often than their price says by more than ladder members do, and NO on
standalone binaries, bought at the touch and held, is the carry.**
- Mechanism and who pays: Bartlett and O'Hara (2026) find Kalshi single-name markets 4.5 pp above realised YES with
  takers buying YES 60% of the time (gap 2); Polymarket's own accuracy page says 78% of markets resolve No. The
  structural reading here is new: the constraint that disciplines a ladder is absent in a standalone market. Who pays:
  the YES buyer in standalone binaries. Why the crowd misses it: the two look identical on the venue (a yes/no price).
- Population and count (`A` plus a light `P`): standalone eligible pairs 45,089 a day (7.7%; about 4,100 markets per
  capture); 24,071 markets leave the listing a day (fact 6), sports-heavy. Resolution requires the light fetch of CH167
  (about 240 Gamma requests a day). The non-sports standalone exit count is the census's first number (unprobed:
  standalone is a structure, and the fee-type split of exits was not counted).
- Test (needs-fetch, light; composition placebo primary). Unit: non-sports market reaching resolution in the window with
  a two-sided quote 24 h and 7 d before its listed end. State: standalone versus ladder member (members per event at the
  origin capture). Target: the resolved outcome against the origin mid (price-based calibration residual). **Primary:
  difference of the mean residual (price minus outcome) between standalone and ladder-member markets within category x
  price-band cells, event clusters (one unit per parent event for ladders, the Cardozo grouping); floor 2 pp; placebo:
  shuffle the structure label within cell.** The C1/T5 outcome-0 label-ordering artefact is checked first on the
  monitor's `ctx_question` text for covered markets.
- Economic route: buy NO at the recorded touch 7 d before end in standalone non-sports binaries at YES in [0.20, 0.80],
  hold to resolution, 1.5-2.5c once; needs a 3 pp excess.
- Kill criteria: fewer than 300 non-sports standalone resolutions in the window; fewer than 5 category x band cells with
  >= 30 of each structure; or the placebo advances.
- Planning MDE versus floor: on about 500 standalone and 2,000 ladder non-sports resolutions in 21 days (unprobed
  estimate from the exit count and the 22% non-sports share), event clusters about 1,000, outcome SD 0.45: planning MDE
  about 4-5 pp against 2 pp: **underpowered on 21 days**; this is a 60-90 day live test or a historical arm on the worn
  `h2_main` / `cross_venue/poly_markets.json` (148,384 closed markets with final prices but no pre-resolution prices on
  the host: the historical arm needs `P`). Ranked accordingly.
- Cost hurdle: 1.5-2.5c once.
- Live-ready: **no** (needs-fetch, light). C 2-3.
- Leakage and confounds: standalone markets are a different *subject* mix (events, announcements) from ladders (counts,
  prices); the category x band cells and CH117's logical-form label (conjunctions) as a way; survivorship of long-listed
  markets; the fetch must record `closed_time` and read nothing before the market left the listing.
- Novelty: CH117 is logical form, CH62 calendar-decided NO, CH63 specificity, CH88 political underconfidence. New: the
  complement constraint as the structural reason YES-optimism survives in one market type and not the other. N 3, EV 4,
  C 2-3.

**CH164. Class-conditioned longshot prints (gap 1, wallet-free): a large buy of a <= 0.35 token in a market the frozen
LABELLER classes as unscheduled news (military, geopolitics, personnel, privately decided announcements) has a positive
24 h mark-out and resolves YES more often than its price says, while the same print in scheduled or path-settled
classes does not; the class, not the wallet, is the leak-prone unit.**
- Mechanism and who pays: Mitts and Ofir (2026) and ACDC (2026) find informed flow concentrated in classes where a few
  people know first (52% win at <= 35c in military / defence against 14% overall). AREPO's generic wallet and flow tests
  were null; the class-conditioned, wallet-free version is the gap. Who pays: the maker's ask in those classes. Why the
  crowd misses it: copycats follow wallets, not classes.
- Population and count (`A`, live-ready for the 24 h arm): **95 non-sports prints >= $2,500 at <= 0.35 a day in 34
  markets and 26 events** (19 at <= 0.20); 579 non-sports prints >= $2,500 at >= 0.65 (the favourite control) (fact 10).
  In 21 days: about 2,000 longshot prints in perhaps 300 distinct events; the class split waits for the LABELLER.
- Test (live-ready 24 h arm; composition placebo). Unit: print. Decision time: venue `ts`. State: LABELLER class
  (CB13's frozen labeller, blind audit round 2 PASS) x longshot (<= 0.35) versus favourite (>= 0.65); direction from
  `side` under branch S (a *buy* of the cheap token; under branch T the arm is reported only). Target: 24 h print-based
  mark-out (next captures), and the resolution where it falls in the window (`P`, CH167's fetch). **Primary: difference
  of the mean 24 h mark-out of longshot buys between UNSCHEDULED-NEWS and the other classes, event clusters; floor 1.0c;
  placebo: shuffle the class label within price band x size band.** Secondary: the favourite control within class; the
  resolution arm (needs-fetch).
- Economic route: taker follow at the recorded ask 10 minutes after the print (the copy-latency test), round trip to
  +24 h, 3.6-4.5c; hold to resolution (the ACDC arithmetic: a 52% win rate at <= 0.35 is >= 15c gross; AREPO expects
  far less and says so).
- Kill criteria: fewer than 600 classified non-sports longshot buys in the window; the UNSCHEDULED-NEWS class under 25%
  of them; fewer than 60 distinct events in that class; or the placebo advances.
- Planning MDE versus floor: about 2,000 prints in 300 events, 24 h mark-out SD on longshots about 5c: planning MDE
  about 1.0-1.5c against 1.0c: borderline on 21 days; 42 days pre-declared.
- Cost hurdle: 3.6-4.5c (taker); 1.5-2.5c once for the carry.
- Live-ready: **yes** (24 h arm: monitor file, LABELLER on `ctx_question`, captures); resolution arm needs CH167's fetch.
  C 1-2.
- Leakage and confounds: branch T leaves the arm unsigned; the LABELLER's class is text-based and audited once; "no > 5c
  move in the prior hour" (prior-art H1a) is a filter from the last capture (<= 2 h old, a weak version); a literature
  re-test, not an original mechanism, ranked accordingly.
- Novelty: CH61 (geopolitics tails underpriced, price-only, CB7-G) and CH60 (ex-ante tail classifier) are the
  parents. New: the print-conditioned, class-conditioned, wallet-free form with the favourite control. N 2, EV 4, C 1-2.

### D. Cross-venue successors, from 2026-11-04 (parents E009, E010, CH38, CH58, CH133; the stream is sealed to 2026-11-03)

**CH165. Unconfirmed moves revert: 30% of large cross-venue moves are Polymarket-led; a Polymarket 10-minute move that
Kalshi does not match within the next 10 minutes is Polymarket-only flow (a retail print on the thinner venue) and
reverts, while a move Kalshi confirms persists; the Kalshi quote is a free confirmation filter for every Polymarket
reversal and continuation rule on the 200 paired markets.**
- Mechanism and who pays: with two venues pricing one event, information shows in both (Hasbrouck's information share);
  flow shows in one. Who pays: the Polymarket taker whose print Kalshi ignores. Why the crowd misses it: cross-venue
  watching is the arbitrageur's job, and the arbitrageur trades the gap, not the confirmation.
- Population and count (`A` from 2026-11-04; unprobed: the stream is sealed): 200 pairs x 720 polls a day; Polymarket
  10-minute moves >= 2c perhaps a few hundred a day (E009's own counts will say at its analysis).
- Test (live-ready from 2026-11-04, after E009/E010's analysis; within-pair). Unit: pair x origin on the 10-minute grid
  with a Polymarket move `r1 >= 2c`. State: confirmed (Kalshi mid moved the same way by >= half the amount within the next
  10 minutes) versus unconfirmed. Decision time: the confirmation poll. Target: the Polymarket mid change over the next
  20 and 60 minutes. **Primary: within-pair difference of the signed continuation between the pair's confirmed and
  unconfirmed moves, pair clusters (about 190 Polymarket events); floor 0.5c; placebo: shuffle the confirmed label
  across the pair's moves.** Direction: confirmed minus unconfirmed > 0.
- Economic route: fade unconfirmed moves at the recorded Polymarket touch (round trip from the poller's own cost field:
  `ask - bid + taker fees`); maker: widen into confirmed moves only.
- Kill criteria: fewer than 100 pairs with both classes in 21 days; the confirmed share under 15% or over 85%; or the
  placebo advances.
- Planning MDE versus floor: 200 pairs, perhaps 5,000 moves: planning MDE about 0.3-0.5c against 0.5c with pair
  clustering; adequate if the move count is in the thousands, not otherwise.
- Cost hurdle: the poller's recorded round trip (E009 reports the share of origins where `|M1_20| > cost`).
- Live-ready: **from 2026-11-04** (the running poller; a new predictions file; pure reader). C 1-2.
- Leakage and confounds: the matcher's residual pair errors (56 of 167 were different contracts before the live
  tightening); Kalshi's own 10-minute lead means "unconfirmed" partly means "Kalshi had already moved" (the state uses
  the Kalshi change *after* the Polymarket move only); retail hours (CH58) as a way.
- Novelty: CH38 is Kalshi as the anchor during vacuums, CH133 depth fade, E009/E010 the lead. New: confirmation as the
  flow-versus-information filter. N 3, EV 3, C 1-2.

**CH166. The lead is where the liquidity is: Kalshi leads Polymarket on average because its books on the paired
contracts are tighter; within a pair, when the Polymarket spread is tighter than Kalshi's, the lead reverses; the
spread ratio at the origin predicts which venue's 10-minute change forecasts the other's.**
- Mechanism and who pays: price discovery goes to the venue with lower trading cost (Hasbrouck 1995's information share
  and its determinants). Who pays: whoever assumes a fixed lead. Why the crowd misses it: E009 tests one direction.
- Population and count (`A` from 2026-11-04; unprobed): 200 pairs x 720 polls; both spreads in every poll.
- Test (live-ready from 2026-11-04; within-pair moderation). Unit: pair x poll. State: `s = log(spread_PM /
  spread_K)` at the origin. Targets: Polymarket's next 20-minute change on Kalshi's last 10-minute change (E009's
  object) and the reverse regression. **Primary: within-pair slope of the Kalshi-lead coefficient on `s` (the lead
  weakens as `s` falls), pair clusters; floor: a halving of the lead between the top and bottom `s` terciles; placebo:
  shuffle `s` across the pair's polls.**
- Economic route: a moderator of E009's route, not a route itself.
- Kill criteria: `s` degenerate within pair (interquartile range under 0.2 log points in more than half the pairs); or
  the placebo advances.
- Planning MDE: as E009's power on 200 pairs; a moderator needs more, so 28 days.
- Live-ready: **from 2026-11-04.** C 1.
- Novelty: CH58 is retail hours as the moderator. New: the spread ratio. N 2, EV 2, C 1.

### E. Maps (parents CH155, CH149; k = 0)

**CH167. The exit and never-traded map: 24,071 markets a day leave the complete-universe listing (resolutions, closures,
delistings) and resolutions cannot be read from the captures; 48% of 2 h movers are markets that have never traded; the
map counts exits by last mid band, structure, class and horizon, costs the light Gamma fetch that would restore
resolution to the live tests (about 240 requests a day), and sizes the never-traded universe by class.**
- Population: 24,071 exits a day; 37,058 never-traded movers a day (fact 6, fact 1).
- Test (host-only historical, descriptive; no counted test): (1) exits per day by last two-sided mid band ([0.02, 0.10],
  (0.10, 0.90), [0.90, 0.98]), structure (standalone / ladder), `fee_type` and horizon (`end_date` minus last capture);
  the share leaving from the middle band is the "unresolved at exit" rate CH163 and CH164 need; (2) the fetch budget and
  the share of exits that Gamma reports resolved within 24 h (a 1-day dry run on the `net` lane at priority below every
  CB job, ids only, counts only); (3) the never-traded universe by class, age and quote width (for sports it is the
  bookmaker-line proxy of CH156's secondary).
- Kill criteria: none (a map). It is the gate for every resolution arm above.
- Live-ready: the map is **host-only historical**; the fetch it costs is **needs-fetch (light)**. C 1.
- Novelty: CH155 is cost and lag; CH149 dormancy. New: what the snapshot stream cannot see, counted. N 1, EV 1 alone, C 1.

**CH168. The aggregation and grain map: the Data API returns one row per taker order (0 multi-fill transactions in
659,082 rows); 23% of rows and 32-40% of large prints carry off-grid prices; the map tabulates decimal length against
the market's tick regime, size, class and hour, tests the three possible readings (aggregated VWAP; a 0.001 grid;
rounding) by their fingerprints, and states the consequence for CB16-Q's premise and for CB13-T's touch-consistency
band before either reads its window.**
- Population: every trade-sample row and monitor print (facts 7-8).
- Test (host-only historical, descriptive): (1) decimal-length histogram by tick regime (0.01 / 0.001) and by size
  band; under the VWAP reading, off-grid shares should rise with size and with the thinness of the last sweep's touch
  (`ask_size_1` smaller than the print size), and 1c-tick markets should show *no* 3-decimal prices other than
  two-level averages at equal size (0.455-type), which is testable by the digit pattern; (2) the share of large prints
  whose price lies outside the last sweep's touch (walked past the displayed level); (3) the implication for CB16-Q:
  the share of its "bot-grain" fills that are in 1c-tick markets (and therefore cannot be quotes), written as a note to
  the batch before SCREEN_A is read, with no change to Q's frozen rules (a design change needs its own justification and
  review; this map only supplies the fact).
- Kill criteria: none (a map).
- Live-ready: **host-only historical** (one sample, one monitor day, one sweep). C 1.
- Novelty: CH131 / CB16-Q read the grain as the quoter's; CH148 the size roundness. New: the aggregation fact and its
  fingerprint tests. N 2, EV 2 alone (it unlocks CH160/CH161 and corrects a premise), C 1.

---

## 3. Ranked top 10, then the rest

Rank = originality x plausibility x **time to a registered live test** x population per day x money route. "Live-ready"
means: a pre-registration can be drafted this week against streams the collectors already write, the collector is a
pure reader (`cpu` lane, under 350 MB) or a light `net` job, and the counts-only census can run on worn files before any
rule binds.

| Rank | ID | One line | Label | Daily population (source) | Primary contrast |
|---|---|---|---|---|---|
| 1 | CH156 | Quoted versus traded moves: one-sided quote moves revert, parallel re-centerings persist, traded moves between | live-ready | 77,732 movers (2,750 non-sports an interval; 60% quote-only, 27% traded); 3,872 markets a day with both (P1, P1b) | within market: continuation by class; class shuffle within market |
| 2 | CH161 | Walked flow continues: the off-grid share of 6 h flow moderates E007-style continuation | live-ready | 943-1,080 market-samples per pass with 6 h flow x 12; 23% of rows walked (P2, P2b, P2c) | E013-form `x6 * zW`; `W` shuffle across the market's samples |
| 3 | CH160 | Walked prints: an off-grid large print is a walked book; worse maker mark-out within market | live-ready (branch S) | 2,164 non-sports prints, 856 walked; 1,919 walked in 1c-tick markets (P2b) | within market: walked minus touch-only; label shuffle |
| 4 | CH157 | Attention without a price: a volume surge with no move drifts YES over 24 h | live-ready (24 h arm) | 2,229 surges (503 no-move); non-sports about 775 / 230 (P1, P1b) | surge minus the market's own baseline; surge shuffle within market |
| 5 | CH162 | Trains and herds: first prints inform, follow-ons copy; herd share moderates continuation down | live-ready | 7,234 follow-on prints (859 non-sports in 277 markets); 5,523 of 7,105 rows clustered (P3, P2c) | within market: position 1 minus 2+; `H` shuffle |
| 6 | CH159 | Ladder breadth: whole-ladder untraded re-centerings persist, lone-member ones revert | live-ready | about 26,000 ladder-intervals a day; 2.8% at >= 80% breadth (P1b) | within event: high minus low breadth |
| 7 | CH158 | The venue tilt as a common factor to fade | live-ready | 12 passes a day; 55-60% up in each (P1) | within market: slope on alignment; tilt shuffle across passes |
| 8 | CH164 | Class-conditioned longshot prints (gap 1), wallet-free | live-ready (24 h arm; branch S) | 95 non-sports prints >= $2.5k at <= 0.35 in 26 events (P3) | class contrast within price x size band |
| 9 | CH165 | Unconfirmed Polymarket-led moves revert; Kalshi as the confirmation filter | live-ready from 2026-11-04 | 200 pairs x 720 polls (unprobed, sealed) | within pair: confirmed minus unconfirmed |
| 10 | CH163 | Standalone binaries carry the YES premium, ladders cannot (gap 2) | needs-fetch (light) | 45,089 standalone eligible pairs; 24,071 exits a day (P1) | structure contrast within category x band |

Next in line: CH166 (spread-ratio lead, from 11-04), CH167 and CH168 (maps; run first, an afternoon each, every design
above cites them). Nothing in this file needs the `net` lane except CH163/CH164's resolution arms (CH167's light fetch,
about 240 requests a day) and the cross-venue successors, which use the poller already running.

**Pre-registration sketches for the top 5 (LT3 candidates; each a separate primary in one Holm family).**

- **CH156 (quoted versus traded moves).** Hypothesis: within a market, the signed 2 h continuation after one-sided
  quote-only moves is lower than after traded moves (H1, one-sided), and after parallel re-centerings higher than after
  traded moves (H2, one-sided). Stream: complete-universe captures (`rows.csv.gz`; sidecar for `fee_type`, tick).
  Unit: non-sports market x interval with |x| >= 1c; class from captures k-1 and k only (traded: `last_trade_price` or
  `volume24hr` changed; parallel: both sides same way within 0.5c; one-sided: one side within 0.05c of unchanged;
  others reported). Decision time: capture k's `received_utc`; target `c = sign(x) * (mid_{k+1} - mid_k)`, J4-R tight at
  both ends, two-sided at k+1. Primary statistic: the market-demeaned difference of mean `c` (one-sided minus traded;
  parallel minus traded) over markets holding both classes, CR1 SEs clustered on event and two-way event x UTC day,
  one-sided p the larger of the two; 2,000-draw event bootstrap CI. Placebo: 200 within-market class shuffles, <= 1.5%
  qualifying; J4-R increment bootstrap on the pooled reversal slope by class, reported. Window: 21 days (about 185,000
  traded and 135,000 one-sided non-sports units; planning MDE 0.1-0.2c against the 0.5c floor); 28 days pre-declared if
  fewer than 2,000 both-class markets at the census. Kill (counts only, before any read): both-class markets < 2,000;
  traded share < 15% or > 60%; `last_trade_price` absent for > 60% of non-sports movers. Economics: paper maker net by
  class; taker fade of one-sided >= 3c moves at the recorded touch, reported against the recorded round trip.
- **CH161 (walked flow continues).** Hypothesis: the slope of the next-6 h mid change on 6 h signed taker flow is higher
  when more of that flow arrived in walked rows (`x6 * zW` > 0). Stream: trade samples (`trades.csv.gz`, `features.csv.gz`)
  and captures. Unit: market x trade sample with >= 1 row in `[t - 6 h, t)` and coverage decided at the origin (page
  oldest row at or before `t - 6 h`, or the page not full). `x6` as E013 (E007 sign convention); `W` = |signed volume| in
  rows whose price has >= 4 decimals divided by total |signed volume| in the window; `zW` by a pre-window census scale.
  Target `y6 = mid(slot k+3) - mid_i`. Primary: expanding-past demeaned OLS of `y6` on `x6 * zW` with E013's controls,
  `zW` and `x6`; one-sided p (larger of event and event x day CR1); event bootstrap CI. Placebo: 200 draws shuffling `W`
  across each market's samples (flow, timing and level kept; the moderator broken); gate p < 0.05. Window: 21 days
  (about 250,000 market-samples, about 100,000 with non-degenerate `W`; planning MDE about 0.002 per SD). Kill: `W`
  non-degenerate in < 60,000 market-samples; walked share of rows < 10% (CH168 then says the API changed). Economics:
  upper-`W` tercile, |x6| >= 0.5, follow the flow, taker round trip to the 6 h target; the gross mid-to-mid move in that
  cell must exceed 0.5c to be called material; "not shown" expected after costs. Disclosed: shares LT2's stream and
  origins; a separate family.
- **CH160 (walked prints).** Hypothesis: within a market, the maker-adverse 2-4 h mark-out on walked large prints (price
  with >= 4 decimals) exceeds that on touch-only prints. Stream: monitor day files, the last capture's sidecar tick,
  captures for marks. Unit: non-sports print in [0.05, 0.95] with cash >= $1,000, signed by Data API `side` only under
  CB17's branch S (q0400 >= 97% agreement, read before this design's rules bind); under branch T, withdrawn uncounted.
  Decision time: venue `ts`; target: CB13-T's print-based 2-4 h and 6-8 h marks (imported by sha256). Primary: the
  market-demeaned difference walked minus touch-only over markets with both, event and event x UTC-day CR1, one-sided p
  for > 0 (worse for the maker); placebo: 200 within-market x size-band label shuffles. Window: 21 days (about 18,000
  walked and 27,000 touch-only non-sports prints; planning MDE 0.3-0.5c against 0.5c); 28 days pre-declared if fewer
  than 1,500 both-class markets. Kill: both-class markets < 1,500; walked share < 15% or > 70%; branch T. Economics:
  paper maker net by class; the taker follow reported against 4.5c and the 9-minute lag.
- **CH157 (attention without a price).** Hypothesis: the 24 h change of the outcome-0 mid after an attention-only surge
  (`volume24hr` >= 3x and >= +$500 over one interval with |x| < 1c) is positive and exceeds the market's own non-surge
  baseline. Stream: captures and sidecar (`fee_type` to exclude sports). Unit: non-sports market x interval with a
  surge; baseline: the same market's non-surge intervals in the window. Decision time: capture k's `received_utc`;
  target `mid_{k+12} - mid_k` (two-sided at k+12; J4-R tight). Primary: the market-demeaned mean difference, event and
  event x UTC-day CR1, one-sided p for > 0; event bootstrap CI; floor 1.0c. Placebo: 200 within-market surge-label
  shuffles. Window: 21 days (about 4,800 attention-only non-sports units; planning MDE about 0.4c); the standalone carry
  arm (NO at the touch at +24 h, held to resolution) is reported only and needs CH167's fetch. Kill: attention-only
  surges < 1,500; events < 100; the outcome-0 = Yes convention fails the label check on covered markets.
- **CH162 (trains and herds).** Hypothesis: (arm 1) within a market, position-1 large prints have a better (for the
  taker) 2-4 h mark-out than same-direction position-2+ prints within 30 minutes; (arm 2) the slope of `y6` on `x6` is
  lower when more of the flow arrived in trains (`x6 * zH` < 0). Streams: monitor (arm 1; `side` under branch S, else
  |mark-out| reported only) and trade samples (arm 2; `H` = share of |signed volume| in rows with a same-signed
  same-market neighbour within 300 s). Primaries: arm 1 the market-demeaned difference, event and event x day CR1,
  one-sided; arm 2 E013-form OLS with a 200-draw `H` shuffle across the market's samples. Window: 21 days (arm 1 about
  18,000 versus 29,000 non-sports prints, planning MDE 0.4-0.6c against 0.5c, 28 days pre-declared; arm 2 about 70,000
  mixed market-samples, about 0.002 per SD). Kill: both-position markets < 1,500; `H` degenerate in > 60% of
  market-samples; non-sports train rate < 20% or > 70%. Economics: paper maker fills by position; taker follow of
  position-1 prints reported against 4.5c and the receipt lag.

**How the families would be registered.**
- **A. Move composition (CH156-CH159).** One reader, one class definition frozen once (sides' changes and the two
  trade flags), one target set; CH156 counted (two primaries), CH157 counted (24 h arm), CH158 and CH159 counted only
  if their counts-only gates pass at the census (tilt IQR >= 4 pp; >= 300 both-breadth events), else reported.
- **B. Transaction shape (CH160-CH162).** CH168's map first (an afternoon; it fixes the walk definition and the
  fingerprint tests); CH161 and CH162 arm 2 on the trade samples with E013's estimator and the shuffle-across-samples
  placebo; CH160 and CH162 arm 1 on the monitor under CB17's branch rule, withdrawn uncounted under branch T.
- **C. Structure and class (CH163, CH164).** CH167's exit map and the 1-day fetch dry run first; CH164's 24 h arm
  registers with LT3 if the LABELLER class count clears its gate; CH163 waits for a 60-90 day window or a historical
  `P` arm and is not an LT3 member.
- **D. Cross-venue successors (CH165, CH166).** Drafted now, registered only after E009/E010's analysis commit, window
  from 2026-11-04 on the running poller, a new predictions file, never the sealed one.
- **E. Maps (CH167, CH168).** Run first; cited by every census above.

**What is honest to say about all of them.** Round 8 bet on four fields nobody had read as states; this round bets on
three *facts* the probes established about the streams themselves: that most 2 h moves are quoted, not traded; that
the trade feed is per order and so writes the walk into the price; and that prints arrive in trains. Each gives a
within-unit contrast on a population of thousands to hundreds of thousands a day, which is the owner's first
requirement, and each is a maker-protection object first and a taker or carry route only where the counted numbers
say so. One probe killed an idea in its intended form (transaction grouping) and reopened it in another (the grain);
one probe closed a whole class of live tests on the snapshot stream (resolution) and priced the light fetch that
reopens it; one probe handed a drafted batch (CB16-Q) a fact about its own premise that it should see before it reads
its window. The bounce critique of E012 is answered here not by a better placebo but by splitting the mixture. Nothing
here is edge until it has gone through census, frozen rules, prospective registration and an economic check at
recorded prices.

---

## 4. Ideas considered and rejected, and why

- **Walk-the-book by transaction grouping (fills per `tx_hash`).** 0 multi-fill transactions in 659,082 trade-sample
  rows (fact 7): the Data API aggregates each taker order into one row. Dead in that form; reborn as the off-grid
  price (CH160, CH161, CH168).
- **Resolution-based live tests on the snapshot stream.** Closed and resolved markets leave the listing (24,071 a day; 0
  `closed` flips, fact 6). Every resolution arm here is `P` (light) and CH167 prices it.
- **`ctx_mid`, `ctx_chg_1h`, `ctx_spread` as print states.** The monitor fetches context after receipt, a median 9
  minutes after the venue time, so these fields already contain the print's own impact. A leak as a state; usable only
  as a reported post-print mark. The two-hour-old capture touch, or the trade sample's pre-origin rows, are the states.
- **Wallet age, wallet first-trade time, wallet profiles (gap 7, skilled-wallet flow).** The standing wallet-free rule
  of rounds 1-8 holds; WALLET-FRESH and every wallet feature were null; `/activity` histories are left-censored. Not
  proposed; the monitor's wallet fields are not read by anything here.
- **Last-trade direction from `last_trade_price` against the touch (a universe-wide tick-rule sign).** A single-trade
  sign is a weaker E007 with a new name; folded into CH156's traded class, not proposed.
- **Sweep level-count imbalance (`n_bid_levels` against `n_ask_levels`) as a "number of opinions".** E003's level is
  inconclusive and CH116 owns the stripped version; a re-run with a new name.
- **Depth withdrawal before moves (Gamma `liquidity` or sweep depth falling with no price change).** CH35 (vacuums),
  CH133 (depth fade) and CB3 own it; the one-sided quote class of CH156 is its capture-level trace.
- **Herding by distinct transactions per minute without sign.** Needs the sign to mean anything; absorbed into CH162.
- **Comment-count levels, `competitive`, cross-event equal-notional baskets, multi-market transactions, market-level
  OI.** Rejected in round 8 for reasons that still hold (dead clocks, undocumented semantics, 7 a day, 0, blank).
- **Cross-venue ideas on the sealed stream before 2026-11-04**, and **anything that reads E011's alerts, LT2's
  stores or CB17's windows** before their analyses. Collection overlap is disclosed; stores stay closed.
- **Sports in-play minutes, closing-line value (gap 10).** The user's scope decision is open; sports stays a parameter
  and nothing here is sports-only. CH156's never-traded class is noted as a free line-move proxy, uncounted.
- **Copy-trading P&L-ranked wallets; 15-minute crypto latency; reward-rebate loops; manipulation of any kind; insider
  identification as a route; taker full-set arbitrage; API quirks; keyed anchors.** Rejected in rounds 1-8 for
  reasons that still hold.
- **Re-proposals of CH01-CH155 with new data** (decided carry, dispute lotteries, reward geometry and shocks, tick
  regimes, series base rates, genesis prints, mention baskets, Deribit and OIS anchors, roll-call and speech clocks,
  Wikipedia, barrier confusion, quoter grain, wake-up prints, open versus close, book age, breathing book, mint share,
  turnover, synchronous prints, first-day prints, cost and lag): not re-proposed; where an idea touches one, the parent
  is named and the new field, clock or join is stated.

---

## 5. Sources consulted

### 5.1 Host probes run for this round (read-only; 2026-10-20 01:40-01:52Z; counts only)

Six streaming Python scripts, written locally, hashed (`shasum -a 256`), copied to the host's `/tmp`, re-hashed there
(`sha256sum`; identical), run as `nice -n 19 /home/opc/arepo/.venv/bin/python -I /tmp/<script>` under `/usr/bin/time
-v`, then removed from `/tmp` (verified: none left). Peak RSS 12-311 MB; longest run 45 s. Nothing was fetched, written,
moved or deleted on the host outside `/tmp`. Inputs: the 12 captures of 2026-10-15 (`rows.csv.gz`; the first capture's
`rows_ext.csv.gz` for `fee_type` and `order_price_min_tick_size`), `live_trades/trades-20261015.jsonl`, and, for features
only, the three 2026-10-16 trade samples (06:40, 12:41, 18:40), the 2026-10-16 06:31 sidecar and
`live_trades/trades-20261016.jsonl`. **Disclosed feature exposure:** P1 and P1b decoded `best_bid`, `best_ask`,
`last_trade_price`, `volume24hr`, `closed`, `active`, `binary`, `event_id`, `neg_risk`, `chg_1h` of consecutive captures
and computed mid changes k-1 -> k only; P2 decoded `tx_hash`, `price` (equality within a transaction only),
`outcome_index`, `ts`, `origin_utc`, `stratum`; P2b decoded the `price` string's decimal length and the sidecar tick;
P2c decoded `ts` and `market_id`; P3 decoded `ts`, `condition_id`, `price`, `cash`, `ctx_fee_type` / `ctx_category`,
`ctx_event_id` and tested `ctx_mid` for presence. **No `side`, no wallet field, no forward price, no mark-out, no
outcome and no target was decoded or printed.** Monitor day-file line counts came from `wc -l`.

| # | Script (sha256) | Inputs | Printed |
|---|---|---|---|
| P1 | `ch9_p1_moves.py` (`26d37144…3bc8`) | 12 captures of 10-15; first sidecar | 584,022 eligible pairs; movers 77,732 (>= 3c 29,257); up 44,630 / down 33,102; quote-only 28,842, ltp missing 37,058, trade-with 9,272, trade-against 2,560; vol24 unchanged 56,063; `chg_1h` non-zero for quote-only 23,951 / zero 0 / missing 4,891; standalone 45,089 / multi 538,933 / neg-risk 265,762; surges 2,229 (503 no-move); both-class markets 3,872 (9,091 / 2,720); closed flips 0, absent at last 24,071; per-interval table (fact 3); RSS 311 MB, 45 s |
| P1b | `ch9_p1b_quote.py` (`76169bbb…b025`) | captures 10:31-16:31 of 10-15 (4 intervals); first sidecar | per interval and totals: eligible non-sports 67,879 / sports 148,052; movers 11,017 / 20,432; never-traded 1,470 / 14,909; quote-only 6,610 / 4,024; traded 2,937 / 1,499; quote anatomy parallel 1,016 / 3,762, same-side unequal 3,402 / 4,558, one-sided 2,212 / 6,311, opposite 1,450 / 4,302 (>= 3c: 242, 1,538, 396, 608 non-sports); ladder event-intervals 8,867, breadth >= 80% 250, 50-80% 1,156, < 50% 7,461; surges non-sports 258 (77 no-move), sports 591 (179); RSS 223 MB, 20 s |
| P2 | `ch9_p2_tx.py` (`d3ec09fd…af9f`) | trade samples 10-16 06:40, 12:41, 18:40 | rows 220,931 / 218,541 / 219,610; transactions = rows; multi-fill 0; walk 0; fills-per-tx histogram {1: all}; markets with a 6 h row 943 / 969 / 1,080 (by stratum); union 569,590 of 659,082; RSS 232 MB, 7 s |
| P2b | `ch9_p2b_grain.py` (`f7a78faf…8e4e`) | sample 10-16 06:40; sidecar 10-16 06:31; monitor 10-16 | decimals <= 2 / 3 / >= 4: 133,960 / 36,089 / 50,882; by tick 0.01: 104,685 / 665 / 31,126; tick 0.001: 29,275 / 35,424 / 19,756; monitor non-sports 822 / 486 / 856, sports 3,617 / 921 / 2,134; tick 0.01 prints 3,401 / 656 / 1,919; tick 0.001 71 / 483 / 422; tick unknown 967 / 268 / 649; RSS 54 MB |
| P2c | `ch9_p2c_herd.py` (`47604eec…94d4`) | sample 10-16 06:40 | markets with 6 h rows 943; rows 7,105; rows with a 300 s neighbour 5,523; markets >= 2 rows 587, >= 5 rows 303, mixed 288; RSS 12 MB |
| P3 | `ch9_p3_prints.py` (`458a82cf…30d1`) | monitor 10-15 | prints 10,522; enriched 10,100; sports 8,249 / non-sports 2,273; categories; cash >= 2,500: 3,803; price <= 0.35: 790; both 249, non-sports 95 (34 markets, 26 events; <= 0.20: 19); favourites >= 0.65 and >= 2,500 non-sports 579; prior print within 30 min 7,234 (non-sports 859), within 5 min 5,662; first prints 1,993; non-sports markets with follow-ons 277; RSS 16 MB |

The scripts, verbatim (the bytes that ran; `ROOT` is `/home/opc/arepo/data-dumps/research_lab`):

```python
# P1 ch9_p1_moves.py
# CH9 P1: move composition on complete-universe captures (counts only; no forward target read).
# Reads the 12 captures of 2026-10-15 pairwise (k-1 -> k only). Prints counts.
import csv, gzip, os, sys
from collections import Counter, defaultdict
ROOT = "/home/opc/arepo/data-dumps/research_lab"
base = ROOT + "/snapshots"
caps = sorted(d for d in os.listdir(base) if d.startswith("20261015T"))
def num(x):
    try: return float(x) if x not in ("", "None", None) else None
    except ValueError: return None
def load(cap):
    out = {}; members = Counter()
    with gzip.open(f"{base}/{cap}/rows.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            if r["binary"] not in ("True", "true", "1"): continue
            ev = r["event_id"]; members[ev] += 1
            out[r["market_id"]] = (num(r["best_bid"]), num(r["best_ask"]), num(r["last_trade_price"]),
                                   num(r["volume24hr"]), r["closed"] in ("True", "true", "1"), ev, num(r["chg_1h"]),
                                   r["neg_risk"] in ("True", "true", "1"), r["active"] in ("True", "true", "1"))
    return out, members
def elig(t):
    b, a = t[0], t[1]
    if t[4] or not t[8] or b is None or a is None or not (0 < b < a < 1): return False
    m = (a + b) / 2
    return (a - b) <= 0.10 and 0.02 <= m <= 0.98
prev, pmem = load(caps[0])
first = prev; fmem = pmem
tot = Counter(); per_int = []; mk_flags = defaultdict(int)  # bit1 quote-only mover, bit2 traded mover
for cap in caps[1:]:
    cur, cmem = load(cap)
    c = Counter()
    for mid_, t0 in prev.items():
        if not elig(t0): continue
        t1 = cur.get(mid_)
        if t1 is None or t1[0] is None or t1[1] is None or t1[4]: continue
        c["elig_pairs"] += 1
        m0 = (t0[0] + t0[1]) / 2; m1 = (t1[0] + t1[1]) / 2; d = m1 - m0
        standalone = pmem[t0[5]] == 1
        c["elig_standalone" if standalone else "elig_multi"] += 1
        if t0[7]: c["elig_negrisk"] += 1
        # volume surge without move
        v0, v1 = t0[3], t1[3]
        if v0 is not None and v1 is not None and v0 > 0 and v1 >= 3 * v0 and (v1 - v0) >= 500:
            c["volsurge3x_500"] += 1
            if abs(d) < 0.01: c["volsurge3x_500_nomove"] += 1
        if abs(d) < 0.01: continue
        c["movers"] += 1; c["mov_up" if d > 0 else "mov_down"] += 1
        if abs(d) >= 0.03: c["movers3c"] += 1
        l0, l1 = t0[2], t1[2]
        if l0 is None or l1 is None: c["mov_ltp_missing"] += 1; cls = "na"
        elif l1 == l0: c["mov_quote_only"] += 1; cls = "q"; mk_flags[mid_] |= 1
        else:
            mk_flags[mid_] |= 2
            if (l1 - l0) * d > 0: c["mov_trade_with"] += 1; cls = "w"
            else: c["mov_trade_against"] += 1; cls = "a"
        g = t1[6]
        if cls == "q":
            if g is None: c["q_chg1h_missing"] += 1
            elif g == 0: c["q_chg1h_zero"] += 1
            else: c["q_chg1h_nonzero"] += 1
        if cls == "q" and standalone: c["q_standalone"] += 1
        if cls in ("w", "a") and standalone: c["t_standalone"] += 1
        if (v1 or 0) == (v0 or 0): c["mov_vol24_unchanged"] += 1
    per_int.append((cap[:13], c["elig_pairs"], c["movers"], c["mov_up"], c["mov_down"], c["mov_quote_only"],
                    c["mov_trade_with"], c["mov_trade_against"]))
    tot.update(c); prev, pmem = cur, cmem
last = prev
# closed flips first -> last capture of the day, by structure and fee type (sidecar of the first capture)
fee = {}
with gzip.open(f"{base}/{caps[0]}/rows_ext.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        fee[r["market_id"]] = sys.intern(r["fee_type"] or "unknown")
flips = Counter()
for mid_, t0 in first.items():
    if t0[4]: continue
    t1 = last.get(mid_)
    if t1 is None: flips["absent_at_last"] += 1; continue
    if t1[4]:
        flips["closed_flip"] += 1
        flips["flip_" + ("standalone" if fmem[t0[5]] == 1 else "multi")] += 1
        flips["flip_fee_" + fee.get(mid_, "unknown")] += 1
        if elig(t0): flips["flip_was_elig_first"] += 1; flips["flipelig_" + ("standalone" if fmem[t0[5]] == 1 else "multi")] += 1
both = sum(1 for v in mk_flags.values() if v == 3)
print("captures", len(caps), "intervals", len(caps) - 1)
print("TOTALS over intervals:", dict(sorted(tot.items())))
print("PER INTERVAL (cap, elig_pairs, movers, up, down, quote_only, trade_with, trade_against):")
for p in per_int: print("  ", p)
print("markets with >=1 quote-only mover AND >=1 traded mover in the day:", both,
      "| quote-only only:", sum(1 for v in mk_flags.values() if v == 1), "| traded only:", sum(1 for v in mk_flags.values() if v == 2))
print("CLOSED FLIPS first->last capture of 2026-10-15 (", caps[0][:13], "->", caps[-1][:13], "):", dict(sorted(flips.items())))
```

```python
# P1b ch9_p1b_quote.py
# CH9 P1b: quote-only move anatomy on 4 consecutive intervals of 2026-10-15 (counts only; k-1 -> k only).
import csv, gzip, os, sys
from collections import Counter, defaultdict
ROOT = "/home/opc/arepo/data-dumps/research_lab"; base = ROOT + "/snapshots"
caps = sorted(d for d in os.listdir(base) if d.startswith("20261015T"))[4:9]  # 08:31 .. 16:31 (4 intervals)
def num(x):
    try: return float(x) if x not in ("", "None", None) else None
    except ValueError: return None
fee = {}
with gzip.open(f"{base}/{caps[0]}/rows_ext.csv.gz", "rt") as f:
    for r in csv.DictReader(f): fee[r["market_id"]] = sys.intern((r["fee_type"] or "unknown").lower())
def load(cap):
    out = {}; members = defaultdict(list)
    with gzip.open(f"{base}/{cap}/rows.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            if r["binary"] not in ("True", "true", "1"): continue
            b, a = num(r["best_bid"]), num(r["best_ask"])
            closed = r["closed"] in ("True", "true", "1"); act = r["active"] in ("True", "true", "1")
            el = (not closed) and act and b is not None and a is not None and 0 < b < a < 1 and (a - b) <= 0.10 and 0.02 <= (a + b) / 2 <= 0.98
            out[r["market_id"]] = (b, a, num(r["last_trade_price"]), num(r["volume24hr"]), closed, r["event_id"], el)
            if el: members[r["event_id"]].append(r["market_id"])
    return out, members
prev, pmem = load(caps[0]); tot = Counter()
for cap in caps[1:]:
    cur, _ = load(cap); c = Counter(); ev_q = defaultdict(lambda: [0, 0])  # event -> [eligible members, quote-only movers]
    for mid_, t0 in prev.items():
        if not t0[6]: continue
        t1 = cur.get(mid_)
        if t1 is None or t1[0] is None or t1[1] is None or t1[4]: continue
        sp = "sports" if fee.get(mid_, "unknown").startswith("sport") else "nonsports"
        c["elig_" + sp] += 1
        db = t1[0] - t0[0]; da = t1[1] - t0[1]; d = (db + da) / 2
        v0, v1 = t0[3], t1[3]
        if v0 is not None and v1 is not None and v0 > 0 and v1 >= 3 * v0 and (v1 - v0) >= 500:
            c["surge_" + sp] += 1
            if abs(d) < 0.01: c["surge_nomove_" + sp] += 1
        if len(pmem[t0[5]]) >= 3: ev_q[t0[5]][0] += 1
        if abs(d) < 0.01: continue
        c["mov_" + sp] += 1
        l0, l1 = t0[2], t1[2]
        if l0 is None or l1 is None: cls = "nevertraded"
        elif l1 == l0: cls = "quoteonly"
        else: cls = "traded"
        c[f"{cls}_{sp}"] += 1
        if cls in ("quoteonly", "nevertraded"):
            if len(pmem[t0[5]]) >= 3: ev_q[t0[5]][1] += 1
            if db * da > 0 and abs(db - da) <= 0.005: sub = "parallel"
            elif db * da > 0: sub = "sameside_unequal"
            elif abs(db) < 0.0005 or abs(da) < 0.0005: sub = "onesided"
            else: sub = "opposite"
            c[f"q_{sub}_{sp}"] += 1
            if abs(d) >= 0.03: c[f"q3c_{sub}_{sp}"] += 1
    for ev, (n, q) in ev_q.items():
        if n >= 3 and q > 0:
            share = q / n
            c["ladder_ev_with_qmove"] += 1
            c["ladder_breadth_ge80" if share >= 0.8 else "ladder_breadth_lt50" if share < 0.5 else "ladder_breadth_50_80"] += 1
    print(cap[:13], dict(sorted(c.items()))); tot.update(c); prev = cur
print("TOTAL 4 intervals:", dict(sorted(tot.items())))
```

```python
# P2 ch9_p2_tx.py
# CH9 P2: transaction shape in trade samples (counts only). Prices decoded only to test equality within a transaction.
import csv, gzip, os, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
ROOT = "/home/opc/arepo/data-dumps/research_lab/trade_samples"
want = sys.argv[1:] or ["20261016T06", "20261016T12", "20261016T18"]
samples = [d for d in sorted(os.listdir(ROOT)) if any(d.startswith(w) for w in want) and os.path.exists(f"{ROOT}/{d}/trades.csv.gz")]
def pts(s):
    try: return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception: return None
union = set(); grand = Counter()
for s in samples:
    origin = {}; stratum = {}
    with gzip.open(f"{ROOT}/{s}/features.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            origin[r["market_id"]] = pts(r["origin_utc"]); stratum[r["market_id"]] = r["stratum"]
    tx = {}  # (market, tx16) -> [n_fills, first_price, multi_price, min_ts, same_outcome_flag, first_outcome]
    n_rows = 0
    with gzip.open(f"{ROOT}/{s}/trades.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            n_rows += 1
            k = (r["market_id"], r["tx_hash"][:18])
            p = r["price"]; oi = r["outcome_index"]
            try: t = float(r["ts"])
            except ValueError: t = None
            e = tx.get(k)
            if e is None: tx[k] = [1, p, False, t, True, oi]
            else:
                e[0] += 1
                if p != e[1]: e[2] = True
                if oi != e[5]: e[4] = False
    c = Counter(); hist = Counter(); per_mkt = defaultdict(lambda: [0, 0, 0])  # tx6h, walk6h, nonwalk6h
    for (m, h), e in tx.items():
        c["tx"] += 1; hist[min(e[0], 6)] += 1
        if e[0] >= 2: c["tx_multi_fill"] += 1
        if e[2]: c["tx_walk_2plus_prices"] += 1
        if e[0] >= 2 and not e[2]: c["tx_fragmented_one_price"] += 1
        if not e[4]: c["tx_mixed_outcome_index"] += 1
        c["fills_in_walk_tx" if e[2] else "fills_in_nonwalk_tx"] += e[0]
        o = origin.get(m)
        if o is not None and e[3] is not None and o - 6 * 3600 <= e[3] < o:
            pm = per_mkt[m]; pm[0] += 1
            if e[2]: pm[1] += 1
            else: pm[2] += 1
        union.add((m, h))
    mk = Counter()
    for m, (a, w, nw) in per_mkt.items():
        mk["mkts_with_tx_6h"] += 1
        if w: mk["mkts_with_walk_6h"] += 1
        if w and nw: mk["mkts_with_both_6h"] += 1
        mk["strat_" + stratum.get(m, "?") + ("_walk" if w else "_nowalk")] += 1
    print("SAMPLE", s, "rows", n_rows, "markets_in_features", len(origin), dict(sorted(c.items())))
    print("   fills-per-tx histogram (1..5, 6=6+):", dict(sorted(hist.items())))
    print("   6h-before-origin:", dict(sorted(mk.items())))
    grand.update(c)
print("SAMPLES", len(samples), "union distinct (market, tx) across samples:", len(union), "| summed tx:", grand["tx"],
      "| summed walk:", grand["tx_walk_2plus_prices"])
```

```python
# P2b ch9_p2b_grain.py
# CH9 P2b: price-grain decimals of taker rows (counts only). Decodes price strings to count decimals; no values printed.
import csv, gzip, os, sys, json
from collections import Counter
ROOT = "/home/opc/arepo/data-dumps/research_lab"
def decs(p):
    s = p.strip()
    if "e" in s or "E" in s:
        s = format(float(s), ".10f")
    if "." not in s: return 0
    frac = s.split(".", 1)[1].rstrip("0")
    return len(frac)
want = sys.argv[1] if len(sys.argv) > 1 else "20261016T06"
s = [d for d in sorted(os.listdir(ROOT + "/trade_samples")) if d.startswith(want) and os.path.exists(f"{ROOT}/trade_samples/{d}/trades.csv.gz")][0]
# tick size per market from the sidecar of the matching capture
cap = [d for d in sorted(os.listdir(ROOT + "/snapshots")) if d.startswith(want)][0]
tick = {}
with gzip.open(f"{ROOT}/snapshots/{cap}/rows_ext.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        tick[r["market_id"]] = r["order_price_min_tick_size"] or "?"
c = Counter(); bytick = Counter(); n = 0
with gzip.open(f"{ROOT}/trade_samples/{s}/trades.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        n += 1; d = decs(r["price"]); b = "d<=2" if d <= 2 else ("d=3" if d == 3 else "d>=4")
        c[b] += 1
        t = tick.get(r["market_id"], "?")
        bytick[(t, b)] += 1
print("trade sample", s, "rows", n, dict(sorted(c.items())))
print("by (sidecar tick, decimals bucket):", {f"{k[0]}|{k[1]}": v for k, v in sorted(bytick.items())})
# monitor prints of the same day: decimals by sports / non-sports
day = want[:8]
m = Counter()
with open(f"{ROOT}/live_trades/trades-{day}.jsonl") as f:
    for line in f:
        try: dd = json.loads(line)
        except Exception: continue
        p = dd.get("price");
        if p is None: continue
        d = decs(str(p)); b = "d<=2" if d <= 2 else ("d=3" if d == 3 else "d>=4")
        cat = (dd.get("ctx_fee_type") or dd.get("ctx_category") or "unknown").lower()
        m[("sports" if cat.startswith("sport") else "nonsports", b)] += 1
        t = tick.get(dd.get("ctx_market_id") or "", "?")
        m[("tick" + t, b)] += 1
print("monitor prints", day, {f"{k[0]}|{k[1]}": v for k, v in sorted(m.items())})
```

```python
# P2c ch9_p2c_herd.py
# CH9 P2c: temporal clustering of taker rows in one trade sample (counts only; reads ts and market only).
import csv, gzip, os, sys
from collections import Counter, defaultdict
from datetime import datetime
ROOT = "/home/opc/arepo/data-dumps/research_lab/trade_samples"
want = sys.argv[1] if len(sys.argv) > 1 else "20261016T06"
s = [d for d in sorted(os.listdir(ROOT)) if d.startswith(want) and os.path.exists(f"{ROOT}/{d}/trades.csv.gz")][0]
origin = {}
with gzip.open(f"{ROOT}/{s}/features.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        try: origin[r["market_id"]] = datetime.fromisoformat(r["origin_utc"].replace("Z", "+00:00")).timestamp()
        except Exception: pass
ts_by = defaultdict(list)
with gzip.open(f"{ROOT}/{s}/trades.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        o = origin.get(r["market_id"])
        try: t = float(r["ts"])
        except ValueError: continue
        if o is not None and o - 6 * 3600 <= t < o: ts_by[r["market_id"]].append(t)
c = Counter()
for m, ts in ts_by.items():
    ts.sort(); n = len(ts); c["mkts_6h"] += 1; c["rows_6h"] += n
    clustered = sum(1 for i in range(n) if (i > 0 and ts[i] - ts[i-1] <= 300) or (i + 1 < n and ts[i+1] - ts[i] <= 300))
    c["rows_with_neighbour_300s"] += clustered
    if n >= 2: c["mkts_ge2_rows"] += 1
    if 0 < clustered < n: c["mkts_mixed_isolated_and_clustered"] += 1
    if n >= 5: c["mkts_ge5_rows"] += 1
print("sample", s, dict(sorted(c.items())))
```

```python
# P3 ch9_p3_prints.py
# CH9 P3: monitor prints (counts only). Never reads side, wallet_hash, key, ctx_mid value or any outcome.
import json, sys
from collections import Counter, defaultdict
path = "/home/opc/arepo/data-dumps/research_lab/live_trades/trades-%s.jsonl" % (sys.argv[1] if len(sys.argv) > 1 else "20261015")
def num(x):
    try: return float(x) if x not in (None, "", "None") else None
    except (ValueError, TypeError): return None
rows = []
with open(path) as f:
    for line in f:
        try: d = json.loads(line)
        except Exception: continue
        rows.append((num(d.get("ts")), d.get("condition_id"), num(d.get("price")), num(d.get("cash")),
                     (d.get("ctx_fee_type") or d.get("ctx_category") or "unknown"), d.get("ctx_mid") not in (None, ""),
                     d.get("ctx_event_id")))
rows = [r for r in rows if r[0] is not None]; rows.sort(key=lambda r: r[0])
c = Counter(); last_by_mkt = {}; by_mkt_ls = defaultdict(int); ev_ls = set(); mk_ls = set()
for r in rows:
    ts, cid, p, cash, cat, enr, ev = r
    sports = cat.lower().startswith("sport")
    c["prints"] += 1; c["enriched"] += enr; c["sports" if sports else "non_sports"] += 1
    c["cat_" + cat.lower()[:12]] += 1
    big = cash is not None and cash >= 2500
    if big: c["cash_ge_2500"] += 1
    if p is not None and p <= 0.35:
        c["price_le_035"] += 1
        if big: c["ls_ge2500"] += 1
        if big and not sports: c["ls_ge2500_nonsports"] += 1; mk_ls.add(cid); ev_ls.add(ev)
        if big and not sports and p <= 0.20: c["ls_ge2500_nonsports_le020"] += 1
    if p is not None and p >= 0.65 and big and not sports: c["fav_ge2500_nonsports_ge065"] += 1
    prev = last_by_mkt.get(cid)
    if prev is not None:
        gap = ts - prev
        if gap <= 1800: c["train_pos2plus_30min"] += 1; c["train_pos2plus_30min_nonsports" if not sports else "x"] += 1
        if gap <= 300: c["train_pos2plus_5min"] += 1
        if gap <= 1800 and not sports: by_mkt_ls[cid] += 1
    else:
        c["first_print_of_market_in_day"] += 1
    last_by_mkt[cid] = ts
c.pop("x", None)
print("file", path.rsplit("/", 1)[-1], dict(sorted(c.items())))
print("longshot >=2500 non-sports: distinct markets", len(mk_ls), "distinct events", len(ev_ls))
print("non-sports markets with >=1 follow-on print within 30 min:", len(by_mkt_ls), "| distinct markets in day:", len(last_by_mkt))
```

Exact run commands (from the Mac): `scp <scripts> oracle:/tmp/`; `ssh oracle 'cd /tmp && sha256sum <scripts> &&
/usr/bin/time -v nice -n 19 /home/opc/arepo/.venv/bin/python -I /tmp/<script> [args]'` with args `20261015` (P3),
`20261016T06 20261016T12 20261016T18` (P2), `20261016T06` (P2b, P2c), none (P1, P1b); then `ssh oracle 'rm -f
/tmp/ch9_*.py; ls /tmp/ch9_* 2>/dev/null | wc -l'` (printed 0). Headers and key names were listed with `zcat … | head -1`
and one `json.loads` of the first monitor line (key names only); day-file line counts with `wc -l`. **Residual
limitation, stated plainly:** the scripts here are the drafting session's copies with their pre-run sha256; the host
copies were removed after running, so the host holds no record of the bytes. Round 10's probes should be committed
before they run (CB16 round 1 item 18).

### 5.2 AREPO documents read (cited inline by name)

`CLAUDE.md`, `AGENTS.md`; `CREATIVE_HYPOTHESES_2026-10-15.md` through `-21.md` (titles of CH01-CH143) and `-22.md` in
full (template); `CREATIVE_BATCH_16.md` §0 and `CREATIVE_BATCH_17.md` §0-§0.4 (selection, probes P1-P3, corrected
premises, queue ids); `LIVE_TESTS_2.md` (branch `feat/live-tests-2`: E012-E014 summary, common rules, estimators,
placebos, census) and the ledger's LT2 challenger round 1 entry (2026-10-20); `EXPERIMENT_LEDGER.md` section headers
(last 50), E011's registration terms, the host-move deviation; `PRIOR_ART_2026-10-19.md` §1 (top-10 gaps) and §4
(suggested hypotheses); `COLLECTION_HOST.md`; `data_catalogue/README.md`; `LIVE_TRADE_MONITOR.md`; `CROSS_VENUE_LIVE.md`
§what runs; `SURPRISE_MOVE_DETECTOR.md` (live path lines); `backend/astrolabe/research_lab/trade_sample.py` (docstring,
`TRADE_LIMIT`, `takerOnly`), `live_trade_monitor.py` (`taker_only`, `transactionHash`), `cross_venue_live.py` (Kalshi
size fields). Host listings: directory sizes, per-day capture / sweep / sample counts, the headers of `rows.csv.gz`,
`rows_ext.csv.gz`, a sweep's `rows.csv.gz`, a sample's `features.csv.gz`, `trades.csv.gz`, `wallets.csv.gz` (header
only), the key names of one monitor line and one scores line, `supervise.sh status`, the collector log tail.

### 5.3 External literature (named, not fetched)

Hasbrouck (1991), "Measuring the Information Content of Stock Trades", Journal of Finance (trade-correlated versus
trade-uncorrelated quote revisions). Copeland and Galai (1983), "Information Effects on the Bid-Ask Spread", Journal of
Finance. Nagel (2012), "Evaporating Liquidity", Review of Financial Studies (reversal as liquidity provision against
common shocks). Hendershott and Menkveld (2014), "Price pressures", Journal of Financial Economics. Gervais, Kaniel and
Mingelgrin (2001), "The High-Volume Return Premium", Journal of Finance. Barber and Odean (2008), "All That Glitters",
Review of Financial Studies (attention-driven buying). Miller (1977), "Risk, Uncertainty, and Divergence of Opinion",
Journal of Finance. Biais, Hillion and Spatt (1995), "An Empirical Analysis of the Limit Order Book and the Order Flow in
the Paris Bourse", Journal of Finance (order aggressiveness). Harris and Hasbrouck (1996), "Market vs. Limit Orders",
Journal of Financial and Quantitative Analysis. Kaniel and Liu (2006), "So What Orders Do Informed Traders Use?", Journal
of Business. Barber, Odean and Zhu (2009), "Do Retail Trades Move Markets?", Review of Financial Studies (herding).
Hasbrouck (1995), "One Security, Many Markets", Journal of Finance (information shares). Bartlett and O'Hara (2026),
NBER conference draft; Mitts and Ofir (2026), SSRN 6426778; ACDC (2026), insider-risk classification; Cardozo and
Rivero-Wildemauwe (2026), arXiv 2609.12878 (per-parent-event grouping): all as cited in `PRIOR_ART_2026-10-19.md`.
