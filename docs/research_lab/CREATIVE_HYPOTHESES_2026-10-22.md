# Creative hypotheses, round 8: where money could come from on Polymarket (2026-10-22)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-19 15:40 UTC+1,
2026-10-19T14:40Z; the file carries the round's planned date). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md`
(CH01-CH34), round 2 `CREATIVE_HYPOTHESES_2026-10-16.md` (CH35-CH59), round 3 `CREATIVE_HYPOTHESES_2026-10-17.md`
(CH60-CH78), round 4 `CREATIVE_HYPOTHESES_2026-10-18.md` (CH79-CH98), round 5 `CREATIVE_HYPOTHESES_2026-10-19.md`
(CH99-CH117), round 6 `CREATIVE_HYPOTHESES_2026-10-20.md` (CH118-CH130), round 7 `CREATIVE_HYPOTHESES_2026-10-21.md`
(CH131-CH143); this file starts at **CH144** and repeats none of them. Where an idea builds on an earlier one, the
parent is named and the new mechanism, clock or data join is stated. Every number quoted from an AREPO document is a
development or screen result, not evidence. One file; no code, no queue specs, no other commits.

## 0. How to read this file

**The brief that binds this round.** The collection host's network lane has been saturated for days by the CB6-CB15
fetches, while its CPU lane (1 OCPU, about 3.9 GB of RAM available, queue jobs at or under about 1.5 GB) sits idle.
Every idea below is therefore marked **host-only** (testable entirely on data already on the host or written by its
running collectors, no new fetch) or **needs-fetch**, and the top five are all host-only, streaming readers over one
capture or one sweep at a time. Every idea states its unit and the population count read from host data (with the
probe that counted it), a within-unit contrast or composition placebo as the *primary* design, a kill criterion a
counts-only census can check, the planning MDE against the materiality floor, and the realistic cost hurdle. An idea
whose plausible effect cannot clear costs is kept only when it is a cheap map that unlocks something else, and says so.

**What changed since round 7 (19 Oct).**
- **CB16 was drafted from round 7** (`CREATIVE_BATCH_16.md`): CH131 as **CB16-Q** (quoter grain, counted), CH132 as
  **CB16-U** ("relative large-print silence in active markets", counted), CH143 as **CB16-K** (census only, k = 0).
  **CH138 (hedging skew) was withdrawn uncounted** before any data was seen: its within-event pairing *doubles* the
  weekly path shock instead of cancelling it (one spot path raises every reach rung and lowers every dip rung), so the
  planning MDE was 12-20c against a 4c gate. Q and U screen on a fresh 14-day window (SCREEN_A, from about 2026-11-02)
  and replicate on the next 14 days; those windows do not exist yet. CB16's probes corrected two round-7 premises:
  the price grain is read from the lifted quote itself (36% of non-sports large prints in [0.05, 0.95] are sub-cent),
  and the sweep's shape is **not** observable at the detail CH131 asked for (no top-3 level sizes).
- **CB15 was drafted from round 6** (CH129 election-night reporting-order drift as CB15-E, one night, one cluster;
  CH130 the pair at birth as CB15-P); E's code-against-design check returned REVISE, fixes 1-10 are in and E was
  resealed; a lane hold is in place for its night.
- **CB13's labeller failed its first blind audit** (NEWS class 0.75 against 0.80 required); one revision is allowed
  and the second blind round is drawn; a second failure makes T1/T2 "not testable (labeller)", counted. CB11's W v2 was
  promoted; CB12's M smoke passed and **CB12-X stays closed as not identifiable** (the horizon-offset placebo advanced
  in 16% of draws against 1.5% allowed). The cumulative counted-trial number was **1,255** at CB16's drafting.
  **None of CB1-CB16 has a positive verdict on any hypothesis.**
- **The failure census that shapes this round** (registry and ledger, 2026-10-19). Of the closed registry entries,
  the verdicts are: *not testable (population)*: CB1-B (52 usable ladders against a 300 floor), CB1-D2 (33 triggers
  from 8 events), CB4-N (1.29 eligible events an hour against 5), CB4-E (6 and 92 sports markets against 800), SB2-J3
  (too few usable book rows), CB5-L (0 CDF families, census pending); *not testable (field absent)*: CB1-E (question
  text missing for most markets), CB8-H's first frame ("the sidecar `open_interest` is blank in all rows"); *not
  testable (labeller)* is CB13-T's live risk; *not identifiable (composition)*: CB12-X; *not detected after costs*:
  E004, E007, HB1, SB2-F4/F5, ECON-95 (0 of 95 cells), CB1-A/C, CB1-D1 (+0.78 pp under a 1 pp floor); *not detected*:
  E005, SB2-F378, SB2-NULL, SB2-R4BOOK (book features on 12.7% coverage), WALLET-FRESH. Three lessons are now rules:
  count the unit before the hypothesis; a field must be shown present on the host before it is a state variable; a
  contrast is attributable only if a within-unit shuffle or relabelling placebo stays quiet.
- **The binding facts are unchanged.** E007 flow continuation Supported but about +0.36c against about 4.5c round
  trip; **0 of 95 economic cells positive after cost**; maker cells -0.2 to -2.6c even with a free exit; SB2 J2 net
  taker about -2.5c; T5 nothing beats recalibrated price; wallet effects null; CB1-A2 decided carry net -1.05c on
  `h2_main`; CB1-D neg-risk asymmetry +0.78 pp under its 1 pp floor; CB4-N 1.29 eligible events an hour; CB5-L 0 CDF
  families; CB12-X not identifiable. The Kalshi 10-20 minute lead is still the only replicated predictor and is sealed
  in E009/E010 to 2026-11-03. Wikipedia pageviews publish 48-69 h late.

**Structural facts from this round's host probes (read-only, counts only; 2026-10-19 14:00-14:40Z; six streaming
scripts run as `nice -n 19` from `/tmp` and then removed from the host; every input was already worn: the 2026-10-13
captures and sweeps inside CB13-T's SCREEN window `[10-12, 10-16)`, the 2026-10-13 monitor file, one field-presence
count on the 2026-10-15 capture. No price, outcome, mark-out, forward quote, side or wallet of any market was printed
or stored; the sweep probe decoded `best_bid` / `best_ask` in memory to test equality between two sweeps and printed
counts only. The scripts are reproduced verbatim in §5 so the claim is auditable.)**
1. **Market-level `open_interest` is blank for every one of 252,939 markets** (Gamma `openInterest`; CB8-H found the
   same). **Event-level `event_open_interest` is present for 108,304 of 253,652 rows (43%)**, and 8,006 of the 8,025
   events carrying both OI and `event_volume` have OI > 0. Between two captures 2 h apart, 1,954 of those events
   traded (239 single-market, 1,715 multi-member); their OI rose in 1,178, fell in 476 and was unchanged in 300. The
   ratio dOI / dVolume spreads from <= -0.5 (297 events) to > 1 (300): OI is in shares and volume in dollars, so the
   ratio is not bounded, but its sign and within-event scale are usable. Event OI / lifetime volume: < 0.05 in 677
   events, 0.05-0.2 in 2,250, 0.2-0.5 in 2,012, 0.5-1 in 1,659, >= 1 in 1,408 (§CH150, §CH151).
2. `volume_num` is present in only 17% of sidecar rows (43,748 of 253,652); `event_volume`, `event_comment_count` and
   `created_at` in nearly all; `series_slugs` in 85%; `competitive` in 88%. The 2026-10-15 capture (293,171 rows) has
   the same pattern (event OI 124,578; `volume_num` 46,742).
3. **Comments barely move:** 22,111 events, 1,217 with any comment, **9 whose count changed in 2 h, 0 that gained
   five or more.** A comment-burst clock is dead (§4).
4. **Book age is measurable.** The sweep's `book_timestamp` is the CLOB's own last-update stamp (epoch milliseconds).
   Against `batch_receipt_utc`, over 45,868 tokens in one sweep: p1 0.1 s, p10 3.8 s, **median 87 s, p90 24.5 min,
   p99 5.9 h; 56% of books are older than 60 s and 18% older than 10 min** (§CH146).
5. **Books churn beneath a sticky touch.** Within one pass (two sweeps 116-158 s apart), 43% of books carry the same
   hash, **90% the same touch, and 47% the same touch with a changed hash**. Across passes (40,408 tokens common to
   four consecutive passes), the hash is unchanged over 2 h in 1,477 (3.7%), over 4 h in 1,047, over 6 h in 719,
   while **the touch is unchanged over 2 h in 27,646 (68%)**. Dormant-2 h books are mostly deep: 1,177 of 1,477 have
   more than 10 bid levels (§CH147, §CH149).
6. **Touch sizes** (bid and ask sizes, 91,705 values): fractional 33,421 (36%), multiples of 5 only 19,586 (21%),
   multiples of 10 only 16,417 (18%), multiples of 100 6,655 (7%), odd integers 15,626 (17%). Level counts are broad
   (6,339 tokens, 14%, at 20 or more bid levels; 1,958 with one level). One-sided books: 31 of 45,868 (vacuums are
   rare in the sweep). Sweeps hold the outcome-0 token only and cover the E002 universe (binary markets with end
   unknown or more than 3 h away), so 45,868 tokens is the whole eligible universe, not a sample (§CH148).
7. **Monitor prints (2026-10-13):** 10,380 prints in 1,928 markets; **outcome index 0 (YES token) 5,316, 1 (NO token)
   4,923, unknown 141**: 47% of large prints are on the NO token. `tx16` never spans two markets (0 of 10,380).
   Enriched with capture context 7,297 (70%). Market age at the print: < 6 h 184; 6-24 h 594; 1-7 d 3,119; 7-30 d
   2,869; > 30 d 531; no context 3,083. **Receipt lag `recv_ts - ts`: p10 271 s, median 527 s, p90 8.5 h, p99 11.9 h**
   (the monitor polls every 5 min; the tail is Data API indexing or monitor catch-up, to be split by CH155's census).
   Same-event prints on different members within 3 s of each other: 335 (3.2%); cross-event equal-notional prints
   within 1 s: 7. By fee type: sports 59%, unknown 30%, politics 2.2%, crypto 1.7%, economics 1.0% (§CH144, §CH153,
   §CH154, §CH155).
8. **The venue's own parameters toggle constantly.** Between two captures 2 h apart, `clob_rewards` changed in 5,058
   of the 17,760 markets with a programme: `rewardsDailyRate` ratio >= 2x in 845, 1.1-2x in 509, 0.5-0.9x in 627,
   < 0.5x in 633, a programme added in 767 and removed in 771, within +/-1% in only 5 (these are jumps, not drift);
   `rewards_max_spread` changed in 604 (4.5 <-> 5.5 in 592; none coincided with a tick change); `rewards_min_size` in
   312 (20 <-> 50 in 180); the tick size in 683 (the 0.96 / 0.04 regime, CH15 / CH86); fee type in 0; `accepting_orders`
   in 0 (§CH152).
9. **Historical host sets.** `history/h2_main` (worn; 3,200 markets, 6.3 M mid-like price points with a 10-min lag
   convention, **875,008 Data API trades with `ts, side, size, price, outcome_index, wallet_hash`**, and a frame with
   outcomes) and `h1_first`; their ML panels already carried `quote_age_s`, `ml_quote_staleness_h` (age of Gamma
   `updated_at`) and `ml_turnover` (`volume24hr / liquidity`) as pooled-model features (ML-r4_book: no demonstrated
   gain on 12.7% book coverage), which is disclosed where relevant below. `cb1_extract` (CB1 closed) is worn;
   `cb2-cb5_extract` are reserved for pending batches and are not touched here. `cross_venue/` holds the 2026-10-12
   pull: `poly_markets.json` (148,384 closed markets with `question, outcome_prices, volume, start, end, closed_time`,
   no pre-resolution prices), the Kalshi universe (about 180 MB), 958 matches and 493 pair series (worn).
10. **Capacity.** 57 GB of disk free; about 3.9 GB of RAM available; `snapshots/` 5.9 GB (104 captures since
    2026-10-10), `book_sweeps/` 0.9 GB (200), `trade_samples/` 0.8 GB (98, stratified liquidity quartile x spread
    tercile), `live_trades/` 0.36 GB (8 days). A pass holds about 1 GB; a queue job starts only with
    `MemAvailable >= mem_mb + 1,200 MB`; two lanes (`cpu`, `net`), one job each. A streaming reader over one capture
    (24 MB gz main, 36 MB gz sidecar) stays under 300 MB; a sweep (4 MB gz) and a monitor day file (about 10,000 lines)
    are small; `h2_main`'s trades are 3,200 small files.

**The reading that steers this round.** Four things the host records that no batch has used as a state variable:
- **(a) Whether a print opens or closes a position.** On this venue a sell is always a close (you can only sell
  tokens you hold) and a buy is always an open. The open/close indicator that option-market research needed a
  clearinghouse to supply (Pan and Poteshman 2006) is free here, wallet-free and side-free through CB13-T's
  touch-consistent signing (family A).
- **(b) The book's own clocks.** The CLOB stamps every book with its last update, and the pass's two sweeps show what
  moved beneath a touch that did not. Staleness and the "breathing" beneath the touch are the two states a maker's
  pick-off risk should depend on (family B).
- **(c) Event-level open interest at 2 h cadence.** The mint / merge / transfer composition of an interval's flow and
  the holder base's turnover, both wallet-free, both never joined to a mark-out (family C).
- **(d) The venue's own control loop.** Reward rates and geometry are toggled in thousands of markets every pass. The
  venue runs a within-market natural experiment for us several times a day (family D).
- **(e) Timing signatures and maps:** synchronous prints within an event, the first day of a market's life (finally
  observable through the monitor), and the actionability / cost hurdle every route must clear (family E).
Everything is wallet-free and side-free, except one disclosed L1 historical arm (CH144) that reads the Data API
`side` on the worn `h2_main` trades.

**Data labels.** `A` = on the host now or written by its running collectors: complete-universe 2 h captures (touch,
Gamma mid, `oneHourPriceChange`, `last_trade_price`, `volume24hr`, `liquidity`, neg-risk ids, `closed`, `endDate`,
`createdAt`; no question text) with the sidecar since 11 Oct 12:00Z (`accepting_orders`, `competitive`, `clob_rewards`,
`rewards_max_spread`, `rewards_min_size`, `fee_schedule`, `fee_type`, `fee_category`, `uma_resolution_statuses`,
`series_slugs`, `parent_event_ids`, `order_price_min_tick_size`, **`event_open_interest`, `event_volume`,
`event_comment_count`**); book sweeps twice per pass (`best_bid`, `best_ask`, `bid_size_1`, `ask_size_1`,
`depth_*_1c`, `depth_*_5c`, `n_*_levels`, **`book_timestamp`, `book_hash`**, `tick_size`, `min_order_size`, `state`);
trade samples (`ts, side, price, size, outcome_index, asset, tx_hash` plus origin features; wallets hashed, never used
here); the live large-trade monitor (prints >= $1k every 5 min with `ts`, `recv_ts`, `price`, `size`, `cash`,
`outcome_index`, `token_id`, `tx16`, `title`, `slug`, `ctx_*` including `ctx_question`, `ctx_mid`, `ctx_created_ts`,
`ctx_end_ts`, `ctx_event_id`); the 2026-10-12 `cross_venue/` pull; the worn `h2_main` (L1 only). `P` = a keyless
fetch would be needed (not preferred this round; named only as optional extensions). `N` = none. **Sealed and not
usable by anything here:** everything rounds 4-7 list (`h4_seal`, `h5_*`, `h6_weather`, `h7_cb4_*`, `h8_*`, the `h9_flow`
HOLDOUT, CB8-B and CB8-H windows, CB1-D's replication captures, E009/E010's `cross_venue_live/` to 2026-11-03, E011's
`surprise_live/` and labels to 2026-11-11, the J4-R window, CB9's HOLDOUTs and Pyth frame, CB10's `h10_*`, `h11_*`,
`h12_*`, CB13's `h13_touch` / `h13_binance` HOLDOUT months and T HOLDOUT `[t_j4r_end, 2026-10-26)`, CB14's `h14_*`),
**plus** CB15-E's books `[2026-11-02T12:00Z, 2026-11-06)` and its night `[2026-11-03T18:00Z, 2026-11-05)`, CB16's
SCREEN_A and REP_A fill windows (from `S_A`, about 2026-11-02, for 28 days: collection overlap only, stores never
opened, no pooling), CB3's Stage 2 from 2026-10-27 (`cb3_extract/` never opened), `forecasts/` and `e00*/` (open
experiments), and the `cb2`-`cb5` extracts. **J4-R `[2026-10-16, 2026-10-21)` is refused for every new maker-mark-out
object here, as CB16 refuses it.** `h2_main` is worn and `h3_power` retired.

**Windows this round can use.** The worn CB13-T SCREEN window `[2026-10-12, 2026-10-16)` for censuses and
features-only frames (as CB16's q0382 does; disclosed worn, L1), and **fresh windows written by the collectors**: a
14-day SCREEN_8 starting at the first 00:00Z at or after the design's freeze + 24 h and **not before
2026-10-26T00:00Z**, declared before any read, with the next 14 days as REP_8, event-disjoint. Where SCREEN_8 overlaps
CB16's SCREEN_A, CB15's night or CB14's live stages, that is collection overlap only; CB15-E's night is excluded and
counted. Nothing here runs ahead of any CB11-CB16 job; every job here is `cpu` lane and under 1.5 GB.

**Hygiene that binds every idea.** Trade before `t`; the print's venue `ts` or the sweep's `batch_receipt_utc` is the
decision time, never a later capture; fills are signed by CB13-T's frozen touch-consistent rule imported by sha256
(the maker-adverse price `P` is the lifted quote; the capture touch, up to 2 h old under the staleness guard, only
signs); mark-outs are price-based (2-4 h and 6-8 h from the next complete captures, J4-R tightness at both ends) and
never read Gamma outcome fields; event x day clustering with an hour-of-day or pass way; **a within-unit contrast or
a composition placebo (shuffle or relabelling within the unit) is primary, not secondary** (the CB12-X lesson);
the cumulative test count (M3); frozen rules before any read; worn sets carry the L1 label; category stays a parameter
(sports is 59% of large prints and the user's call; nothing here is sports-only, and every print-level idea reports
the sports arm uncounted as CB16 does).

**Scores.** N novelty (1-5), EV expected value if true (1-5), C cost (1 = an afternoon on host files, 5 = new collector
plus weeks). My judgement, not measurements. Cost conventions as rounds 1-7 and `EXECUTION_COSTS.md`: taker fee
`rate*p*(1-p)` per leg (crypto 0.07; sports 0.03-0.05; politics/finance/tech 0.04; economics/culture/weather 0.05;
geopolitics 0; makers 0); median round trip for 5 shares **4.5c** (p25 3.2c, p75 6.8c); by liquidity < $1k 6.2c,
$1k-10k 4.7c, $10k-100k 3.1c, >= $100k 1.8c; by category sports 5.2c, politics 3.6c, crypto 4.5c, economics 3.4c; fee
by price band 0.3 / 0.8 / 2.3 / 1.0 / 0.3c; one-leg hold-to-resolution pays the half-spread and the fee once (about
1.5-2.5c above 0.80); passive entry has paid 1-7c of adverse selection in every study so far. **New this round:** the
monitor shows a print a median 9 minutes after its venue time, so every "taker follows the print" route is reported
only until CH155's census says which classes are seen in time.

**Counts table (what was counted before each idea was written).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH144 | large print signed as open (buy) or close (sell) | 10,380 prints a day in 1,928 markets; 7,297 enriched; YES-token 5,316 / NO-token 4,923; CB16 G1a: 3,131 non-sports enriched prints in [0.05, 0.95] over 4 days; `h2_main` 875,008 trades with `side` (L1) | probes P1, P4; CB16 §0.3; fact 9 |
| CH145 | market x day with >= 5 large prints (closing share definable) | CB16 G1b: non-sports enriched prints with >= 1 prior gap inside 4 days 3,834; markets with >= 5 prints to be counted at census | CB16 §0.3 |
| CH146 | token-sweep with a book age | 45,868 tokens x about 24 sweeps a day; median age 87 s, 18% > 10 min | P3 |
| CH147 | within-pass token pair with an unchanged touch | 41,244 of 45,868 (90%) per pass; 12 passes a day; 47% with a changed hash beneath | P2 |
| CH148 | touch size by roundness class at the fill | fractional 36% / x100 7% / x10 18% / x5 21% / odd 17% of 91,705 sizes | P2 |
| CH149 | book with an unchanged hash over 2 h | 1,477 of 40,408 (3.7%); 1,177 of them > 10 levels | P2b |
| CH150 | event x 2 h interval with volume and OI | 1,954 per 2 h (239 single-market); OI up 1,178 / down 476 / flat 300 | P3 |
| CH151 | event with OI and lifetime volume | 8,006; turnover bins 677 / 2,250 / 2,012 / 1,659 / 1,408 | P3 |
| CH152 | market with a material reward-rate change in a 2 h step | >= 2x 845; <= 0.5x 633; added 767; removed 771; geometry 604 + 312 | P2b, P3 |
| CH153 | same-event prints on different members within 3 s | 335 of 10,380 a day (3.2%) | P4 |
| CH154 | large print in a market < 24 h old | 778 enriched a day (184 < 6 h); 3,083 unenriched prints to classify | P4 |
| CH155 | print with a receipt lag; token-sweep with depth at 1c and 5c | 10,380 a day (median lag 527 s, p90 8.5 h); 45,868 tokens per sweep | P4, P2 |
| rejected | market-level OI; comment bursts; cross-event equal-notional pairs; multi-market `tx16` | 0 of 252,939; 9 changed / 0 bursts; 7; 0 | P1, P4 |

---

## 1. Map: where money might be, given the survivors and the nulls

| Family | What the evidence and the probes suggest | Money route |
|---|---|---|
| A. Open and close | every flow study pooled opens and closes; a sell is a close by construction; 47% of large prints are on the NO token; `h2_main` holds 875k trades with the side for an L1 check | maker: quote against closing flow, step aside from opening flow; taker: fade exits; carry: the favourite under exit pressure, held to resolution |
| B. The book's own clocks | the CLOB stamps the book's last update (median 87 s, 18% > 10 min); 68% of touches sit for 2 h while 96% of books change beneath them | maker protection by age and by what moved beneath the touch; the maker's pick-off hurdle measured instead of assumed |
| C. Event-level open interest | OI at 2 h cadence exists for 43% of rows; its sign against volume separates mint, merge and transfer; its level against volume is a holder-turnover clock | maker: widen in one-sided transfer intervals; do not fade moves in low-turnover events; taker reported only |
| D. The venue's control loop | reward rates jump by 2x or 0.5x in about 1,500 markets per pass; geometry toggles in 900 | maker timing: quote where the subsidy just rose and depth has not followed; the elasticity of adverse selection to the subsidy |
| E. Timing signatures and maps | 335 same-event synchronous prints a day; 778 prints a day in markets under one day old; a 9-minute median receipt lag | mechanical flow to lean on; the genesis window, finally observable; the hurdle table every other route must clear |

---

## 2. Hypotheses

### A. Open and close (parents CH42, CH46, CH79, CH94, CH26; literature: Pan and Poteshman 2006, Boehmer, Jones and Zhang 2008)

**CH144. Opening prints carry the information, closing prints carry the liquidity: on Polymarket a taker sell is
always a close (you can only sell tokens you hold) and a taker buy always an open, so the open/close indicator that
option-market research needed clearinghouse data to build is free, wallet-free and side-free here; within a market
and a direction, the 2-6 h mark-out of large opening prints exceeds that of large closing prints, the maker's loss is
concentrated in fills against openers, and a maker who quotes against closers and steps aside from openers keeps the
spread.**
- Mechanism and who pays: Pan and Poteshman showed that *newly opened* option positions predict the underlying while
  closing trades do not; Boehmer, Jones and Zhang showed the same asymmetry for short sales by trader type. Here the
  venue's structure does the classification: a holder who exits sells the token (the UI's "Sell" path), a new opinion
  buys YES or buys NO. Exits are driven by cash needs, profit-taking and the disposition effect (CH42, which needed
  wallets in profit); opens are driven by information or by a fresh belief. Who pays: the maker who treats both the
  same, and the taker who fades an opener. Why the crowd misses it: the interface and every public feed show a price
  and a size, never whether a position was created or destroyed; AREPO's own flow studies (E007, HB1/HB2, SB2) pooled
  them; CH79's doubt about the `side` flag made the lab side-free, which also hid this split.
- Population and count (`A`): 10,380 large prints a day in 1,928 markets (fact 7); 70% enriched; CB16's G1a counted
  3,131 non-sports enriched prints in [0.05, 0.95] over four SCREEN days (about 800 a day). The open/close label is
  the sign of CB13-T's touch-consistent rule applied to the *traded token*: a print at or above the token's ask side
  is a buy (open), at or below its bid side a sell (close); for NO-token prints the YES touch is mirrored
  (`bid_NO = 1 - ask_YES`). Expect 60-70% opens among classified non-sports prints (a census number, not a guess:
  the first job counts it). Historical L1 arm: `h2_main`'s 875,008 trades carry the Data API `side` directly
  (BUY = open, SELL = close), with the mid-like price series and resolution outcomes.
- Test (host-only; within-market and within-direction). Decision time: the print's venue `ts`. State: open / close.
  Target: print-based 2-4 h and 6-8 h mark-out in the print's direction (CB13-T's rule and marks, J4-R tightness).
  **Primary statistic: within-market difference `D = mean mark-out(open) - mean mark-out(close)` over markets that
  have both kinds of print in the window, pooled with event x day clustering and an hour-of-day way; floor 0.5c per
  filled share; primary placebo: shuffle the open/close label within market x direction x hour (the within-unit
  shuffle that CB12-X lacked).** Secondary: the same by LABELLER class (uncounted), and the all-size version on the
  trade samples' `trades.csv.gz` (`outcome_index`, price, the origin's touch) as a validity line.
- Historical L1 arm (worn `h2_main`, disclosed): the same `D` with `side` as the label, 2 h / 6 h / 24 h mid-like
  targets under the 10-min lag convention, and a resolution arm: in the last 72 h before close, net close-minus-open
  large volume on the leading side against the outcome beyond price (the disposition premium on favourites, CH145's
  route). Development only; the counted test is the live arm. CH79's caveat applies to `side` and is stated in the
  report; CB9's side audit, when it lands, calibrates it.
- Economic route: (1) maker protection, the primary: the paper maker's net on fills against closers versus openers
  (CB13-T's fill table, two more columns); a maker who declines opener-shaped flow (not knowable in advance) is not
  the claim; the claim is that quoting *where closers dominate* (CH145) keeps the spread. (2) Taker fade of large
  closes at the recorded ask, reported against the 4.5c median round trip (1.8c in liquid markets): E004's reversal
  failed costs pooled; the conditional version is reported, not promised. (3) The hold-to-resolution favourite arm is
  CH145's.
- Kill criteria (counts-only census, features only): fewer than 500 non-sports markets with both an open and a close
  classified print in SCREEN_8 (then within-market has no units); closes under 15% or over 85% of classified
  non-sports prints (one arm too thin); the touch-consistency rule leaves more than 40% of non-sports prints unsigned
  (then the label is unreliable); or the within-market placebo advances in more than 1.5% of draws.
- Planning MDE versus floor: on CB16-Q's arithmetic for the same population (about 11,000 classified non-sports
  prints in 14 days, a 60/40 split, event x day clusters), the planning MDE on `D` is about 0.6-1.2c against the 0.5c
  floor: borderline, as Q1 is. The design pre-declares a 28-day SCREEN_8 if the 14-day census shows fewer than 8,000
  classified non-sports prints, and reports the sports arm (59% of prints) uncounted.
- Cost hurdle: the maker arm has no round trip (it is a fill-quality difference); the taker fade must clear 4.5c
  median / 1.8c liquid and is reported only; the carry arm (CH145) pays 1.5-2.5c once.
- Host-only: **yes.** Memory: one monitor day file and the capture touch per print, streaming; under 400 MB. C 1.
- Leakage and confounds: a sophisticated NO holder can exit by *buying* YES and merging (same price, more capital),
  which misclassifies a close as an open; the UI's Sell path makes this rare and the bias attenuates `D`. Opens and
  closes differ in price band (closes cluster near 0.9+ as winners cash out): the within-market x direction contrast
  and a price-band way absorb it. The capture touch is up to 2 h old (CB13-T's staleness guard). Sports is a
  parameter. The `h2_main` arm is worn and L1.
- Novelty: CH42 (disposition sellers) and CH94 (account-exit sweeps) needed wallets; CH79 is the side flag's truth;
  CH46 is the pre-close dump. New: the venue's structural open/close identity as the flow's information content,
  wallet-free. N 5, EV 4, C 1.

**CH145. Exit pressure as a market state: the share of a market's large flow that is closing (CH144's label
aggregated over the trailing 24 h) is a wallet-free measure of holders leaving; a high closing share on the leading
side is uninformed selling (the disposition effect), the price is pressed below fair, and the leading side held to
resolution earns more than its price implies, while the maker's bids in such markets are the best fills on the
venue.**
- Mechanism and who pays: holders of a winning position sell early and hold losers (the disposition effect, CH42's
  object, measured there with wallets in profit). When the sellers are the holders of the *favourite*, the pressure is
  on the side that is likely to pay $1. Who pays: the exiting holder, who gives up 1-3c to leave. Why it persists: the
  favourite-longshot bias is the venue's best-documented regularity (favourites underpriced), and this names one of
  its sources, so the two are consistent rather than competing.
- Population and count (`A`): markets with at least 5 large prints in a trailing 24 h window (CB16's G1b counted
  3,834 non-sports enriched prints with a prior gap inside 4 days; the census counts qualifying market-days; expect
  200-500 non-sports market-days a week). Historical L1 arm on `h2_main` (3,200 markets with trades and outcomes).
- Test (host-only; within-market over time, composition placebo). Decision time: each pass's capture `received_utc`.
  State: closing share `c = closing large volume / total large volume` over the trailing 24 h, split by side
  (leading side = the side above 0.5). Targets: the 2 h and 24 h mid change (J4-R tightness) and, in the L1 arm, the
  resolution outcome against price. **Primary: within-market contrast of the next-24 h signed mid change between the
  market's own high-`c` passes and low-`c` passes (terciles of its own distribution), event x day clusters; placebo:
  shuffle `c` across the market's passes; floor 1.0c.** Secondary: the maker's paper bid fills (CH146's object) in
  high-`c` versus low-`c` passes.
- Economic route: buy the leading side at the recorded ask when `c_leading >= 0.7` and `p >= 0.80`, hold to
  resolution, paying the half-spread and the fee once (1.5-2.5c in the 0.80-0.95 band, about 1.6c above 0.95); the
  claim needs a 2c excess resolution rate above price, and it is a one-leg carry with the tail gate of rounds 1-7.
  Maker route: rest bids in high-`c` markets (the maker's good fills).
- Kill criteria: fewer than 150 non-sports market-days with `c` definable in SCREEN_8; `c` has no within-market
  variance (interquartile range under 0.2 for more than half the markets); the placebo advances; or CH144's label
  fails its own kill (CH145 depends on CH144's classification rate).
- Planning MDE versus floor: on 300 market-days and a 24 h mid-change SD of about 6c, the within-market tercile
  contrast has a planning MDE of about 1.5-2c against a 1.0c floor: thin on 14 days, workable on 28 or on the L1 arm
  (3,200 historical markets). It is proposed as CH144's companion, not alone.
- Cost hurdle: 1.5-2.5c once; plausible premium 1-3c; it clears only in the top band and only if the L1 arm shows
  >= 2c first.
- Host-only: **yes.** Memory: monitor files and captures streaming; under 500 MB. C 1-2.
- Leakage and confounds: the closing share rises mechanically near resolution as everyone leaves (CH46): time to end
  is a way; the "leading side" is read from the price at `t`, never later; a high-`c` market may be one where news
  arrived and holders fled rationally (the within-market contrast and the outcome arm separate the two). CH01/CB1-A
  (decided carry) owns the near-certain tail; CH145 excludes markets whose Gamma status is proposed or disputed.
- Novelty: CH26 (inattentive holders) and CH42 needed wallets; CH46 is the forced pre-close exit. New: exit pressure
  as a wallet-free market state and its link to the favourite-longshot bias. N 4, EV 3, C 1-2.

### B. The book's own clocks (parents CH131 / CB16-Q, CH80, CH133, CH35, CH36, E003)

**CH146. Book age at the fill: a resting book nobody has updated for ten minutes is a book nobody is watching; its
touch is the order that informed takers lift, so the paper maker's mark-out on fills into old books is the worst on
the venue and on fills into books updated in the last minute it is near zero; the maker's pick-off risk, assumed
constant in every economics study, has a measurable clock.**
- Mechanism and who pays: the limit order is a free option written to the market (Copeland and Galai 1983); its
  value to the taker grows with the time since the writer last looked (Foucault 1999's picking-off risk). The CLOB's
  `book_timestamp` is the book's last update, so the sweep records exactly how long the displayed book has stood.
  Who pays: the maker whose quote outlived their attention. Why the crowd misses it: the stamp is in the API
  response, not in the interface, and no AREPO panel has read it (the ML panels' `quote_age_s` and
  `ml_quote_staleness_h` were Gamma `updated_at` ages, pooled-model features with no gain on 12.7% coverage;
  disclosed, and a different field).
- Population and count (`A`): 45,868 tokens per sweep, about 24 sweeps a day, all with a parseable stamp; median
  age 87 s, 18% older than 10 min, 2% older than 5.9 h (fact 4). About 1.1 million token-sweeps per day; 15 million
  in a 14-day window (the census reports the age histogram by class and hour).
- Test (host-only; within-token, sweep-level paper maker). Decision time: the sweep's `batch_receipt_utc`. State:
  book age `a = receipt - book_timestamp`, binned (< 1 min, 1-10 min, 10-60 min, > 60 min). Target: **the paper
  maker's mark-out**: post a paper ask at the sweep's `best_ask` and a paper bid at `best_bid`; the quote is deemed
  filled when the next complete capture's mid (2-4 h, J4-R tightness) crosses it; the mark-out is `mid_{t+2h} - ask`
  (and `bid - mid_{t+2h}`), negative when crossed adversely, and the fill is certain by construction when crossed
  (conservative for the maker). **Primary: within-token difference of the paper mark-out between the token's own old
  (> 10 min) and fresh (< 1 min) sweeps, event x day clusters with a pass way; floor 0.5c; placebo: shuffle the age
  bin across the token's sweeps.** Secondary (reported): the fill arm on CB13-T's table, where the lifted quote equals
  the touch the last sweep saw, so the order's age is at least `print ts - book_timestamp` (a lower bound); CB13 H7
  found sweeps missing for about half of sports and most crypto prints, so this arm is thin and reported only.
- Economic route: maker protection, measured: the maker's expected loss per resting hour as a function of how long
  since they last re-quoted; a maker who re-quotes (or cancels) every `k` minutes caps the loss at the `k`-minute bin.
  The taker route (lift stale asks that an anchor from another family says are wrong) inherits the anchor's
  economics and is reported only.
- Kill criteria: the age histogram collapses (fewer than 5% of non-sports token-sweeps older than 10 min, or fewer
  than 5% fresher than 1 min, so the contrast has no units); fewer than 2,000 non-sports tokens with both bins in the
  window; `book_timestamp` turns out to be the response time rather than the last update (the probe's quantiles
  argue against this, but the census checks that the stamp is unchanged between the pass's two sweeps when the hash
  is unchanged); or the placebo advances.
- Planning MDE versus floor: with millions of token-sweeps and clusters in the thousands, the planning MDE on the
  paper mark-out difference is about 0.05-0.1c; the 0.5c floor is the binding constraint, not power. The risk is the
  paper-fill assumption, so the primary is reported with and without the J4-R tightness filter and with the capture
  mid replaced by the next sweep's touch where a sweep exists.
- Cost hurdle: none for the maker arm (a fill-quality difference); the maker's cost is the re-quote cadence.
- Host-only: **yes.** Memory: one sweep (4 MB gz) and one capture per step, streaming; under 300 MB. C 1.
- Leakage and confounds: an old book in a dead market is not mispriced, only idle (the within-token contrast and a
  `volume24hr` way absorb it); bots update books on a heartbeat, so "fresh" partly means "bot-quoted" (CB16-Q's
  grain and CH148's shape describe the same books: the census cross-tabulates age by grain); the capture mid is up
  to 2 h after the sweep (J4-R tightness; the next-sweep touch as the check). Sports is a parameter.
- Novelty: CH80 is dust at the touch; CH35/CH36 are vacuums and outages; E003 is the imbalance level; CB16-Q is the
  grain of the lifted quote. New: the book's last-update stamp as the maker's pick-off clock. N 4, EV 3, C 1.

**CH147. The sticky touch and the breathing book: within one pass the touch is unchanged in 90% of books while the
book beneath it changes in half of them; the direction in which the depth beneath the touch shifted between the two
sweeps (the re-quoting bots moving their mass) predicts the sign of the next 2 h mid change, because the touch that
did not follow is the stale order and the mass that moved is the fresh information; the maker's quote on the side
the mass left is the one about to be lifted.**
- Mechanism and who pays: bots re-centre their ladders beneath the touch when their fair value moves; a human or
  stale touch order does not. The two sweeps 2 minutes apart show the shift directly as `d(depth_ask_5c) -
  d(depth_bid_5c)` with the touch held fixed. Who pays: the touch order on the side the bots abandoned. Why the
  crowd misses it: the interface shows a depth chart, not its 2-minute change, and the change is beneath the touch.
- Population and count (`A`): 41,244 of 45,868 tokens per pass have an unchanged touch across the pass's two sweeps,
  and 21,401 of them a changed hash beneath (fact 5); 12 passes a day; about 250,000 token-pass pairs with a shifted
  book beneath an unchanged touch per day.
- Test (host-only; within-token, composition placebo). Decision time: the second sweep's receipt. State: `s =
  [(depth_ask_5c - depth_ask_1c) - (depth_bid_5c - depth_bid_1c)]_{sweep 2} - [same]_{sweep 1}`, standardised within
  token over the window (so a bot's heartbeat resizing cancels); computed only when the touch is unchanged across the
  pair. Target: the signed 2-4 h mid change from the next complete capture (J4-R tightness), and the paper-maker
  mark-out of CH146 on the side the mass left. **Primary: within-token slope of the signed next-2 h mid change on
  `s`, event x day clusters with a pass way; floor 0.5c per SD of `s`; placebo: shuffle `s` across the token's
  passes.** Secondary: the same with `n_*_levels` changes as the state (levels added or removed on each side).
- Economic route: maker protection (pull or widen the side the mass left; the paper maker's avoided-fill mark-out);
  the taker follow at the touch is reported against 4.5c and is expected to fail unless the slope exceeds about 3c
  per SD.
- Kill criteria: fewer than 20% of non-sports token-passes have a shifted book beneath an unchanged touch (then the
  state is rare); the within-token SD of `s` is dominated by one or two tokens (concentration check: top-5 tokens
  carry more than 30% of the variance); the slope's CI includes 0 or the point is under 0.5c per SD; or the placebo
  advances.
- Planning MDE versus floor: about 250,000 units a day, clusters in the thousands: planning MDE about 0.05-0.1c per
  SD; the 0.5c floor binds. The design risk is tightness (the mid is up to 2 h later), handled as in CH146.
- Cost hurdle: none for the maker arm; the taker follow pays the spread and is reported.
- Host-only: **yes.** Memory: two sweeps and one capture per step; under 300 MB. C 1.
- Leakage and confounds: a trade between the two sweeps changes depth without any re-quoting (the hash changes and
  the touch may not): a `size`-weighted print between the sweeps, where the trade sample covers the market, is a way,
  and the census reports how often the 2-minute window contains a sampled trade; bots resize on their heartbeat (the
  within-token standardisation); E003's inconclusive imbalance *level* is not the object here, the 2-minute *change*
  is, and the design reports E003's level as a covariate so the two are not confused.
- Novelty: CH133 is the rate of withdrawal at 120 s on the sealed cross-venue stream (200 pairs); E003 is the level
  of imbalance; CH35 is the vacuum. New: the pass's two sweeps as a 2-minute differenced book over the whole eligible
  universe, conditioned on a sticky touch. N 3, EV 3, C 1.

**CH148. Size roundness and intra-pass churn as the quoter's footprint (parent CH131; complement to CB16-Q):
fractional touch sizes (36%) are partial fills and bot inventories, round hundreds (7%) and tens (18%) are typed by
people; a touch whose size is fractional and whose book hash changed within the pass is a bot's, a round touch on an
unchanged book is a person's; the maker-adverse fill on a person's touch is the pick-off CH131 looked for in the
grain alone.**
- Mechanism and who pays: the same as CH131 (a person's resting order is stale by construction, a bot's is fresh),
  measured on two fields CB16's premise 2 did not rule out: the touch *size* (present in every sweep) and the
  *within-pass churn* (two sweeps per pass). Who pays: the person at the touch. Why the crowd misses it: the size's
  decimals are visible but nobody reads them as a signature.
- Population and count (`A`): 91,705 touch sizes per sweep in the five roundness classes (fact 6); 19,843 of 45,868
  books unchanged within the pass (fact 5); for the fill arm, CB13-T's fills where the lifted quote equals the last
  sweep's touch (thin: CB13 H7).
- Test (host-only; within-token; the sweep-level paper maker of CH146 as the primary, the fill arm reported).
  Decision time: the sweep's receipt. State: footprint class = (size class: fractional / round / odd) x (churn:
  hash changed within the pass or not). Target: CH146's paper-maker mark-out. **Primary: within-token difference of
  the paper mark-out between "person" (round, unchurned) and "bot" (fractional, churned) sweeps; event x day clusters;
  floor 0.5c; placebo: shuffle the class across the token's sweeps.** Reported: the lifted quote's reward-band
  membership (`|P - mid| <= rewards_max_spread`) as a third footprint.
- Economic route: the same as CH131's (quote beside bots, not beside people); the taker arm only against an anchor.
- Kill criteria: the footprint classes are not mixed within token (fewer than 2,000 non-sports tokens with both
  classes in the window); CB16-Q's grain already explains the paper mark-out (the footprint adds under 0.2c after
  conditioning on grain; then this is Q's duplicate and dies); or the placebo advances.
- Planning MDE versus floor: as CH146 (power is not the constraint; the floor is).
- Cost hurdle: none for the maker arm.
- Host-only: **yes.** Memory: as CH146. C 1.
- Leakage and confounds: bots also post round sizes (reward programmes require `rewards_min_size` 20 or 50, fact 8,
  so a 50-share touch is ambiguous: the census tabulates sizes against `rewards_min_size`); partial fills make a
  person's order fractional; the churn arm shares CH147's between-sweep trade confound.
- Novelty: CH131/CB16-Q read the price grain; CH111 the taker's dollar shape; CH80 dust. New: the resting *size*
  class and the within-pass churn as footprints, on fields the host already holds. Honest standing: a complement to
  Q; counted only if Q leaves the maker-loss address unexplained. N 2, EV 2, C 1.

**CH149. Dormant deep ladders (a map): 1,477 books per pass have not changed in 2 h and 1,177 of them have more than
10 levels; these are parked reward ladders or abandoned bot inventories; the venue-wide dormancy count by hour is
the maker-outage clock CH36 wanted, and the markets they sit in are where a fill into an unwatched ladder happens
when it happens.**
- Mechanism and who pays: a deep ladder that nobody touches for hours is quoted by a program that is not running
  (CH36's outage) or by a reward farmer who has walked away; its levels are stale by hours, not minutes. Who pays:
  the owner, when news arrives. The map tells CH146 where its oldest books are, CH36 when outages happen, and CB16-U
  which markets' silence is a dead book rather than a quiet market.
- Population and count (`A`): 1,477 dormant-2 h books of 40,408 tokens common to four passes; 1,047 dormant 4 h,
  719 dormant 6 h (fact 5).
- Test (host-only; descriptive): the dormancy count by hour of day and day of week; the share of dormant books with
  a reward programme; the age distribution of dormant books from `book_timestamp`; the probability that a dormant
  book is crossed by the next capture's mid (CH146's paper fill) versus an active deep book of the same class. No
  counted test; a census and four tables.
- Kill criteria: none needed (a map); it is dropped if dormant books are under 1% of tokens in the fresh window.
- Cost hurdle: not applicable; the map tells the maker where the stale depth is.
- Host-only: **yes.** Memory: four sweeps; under 200 MB. C 1.
- Novelty: CH36 wanted the outage clock from synchronised vacuums; the dormant-ladder count is a cheaper and larger
  clock. N 2, EV 1 alone (a map), C 1.

### C. Event-level open interest (parents CH26, CH41, CH66, CH09; literature: Bessembinder and Seguin 1993, Hong and Yogo 2012)

**CH150. Mint share: an interval's event-level open-interest change against its volume change separates
disagreement (mint: two new opinions, OI up with volume), exit (merge: OI down) and one-sided transfer (OI flat while
volume trades); the 2 h move in a transfer-heavy interval continues (one informed side meets existing holders) and
the move in a mint-heavy interval reverts (two opinions, no net information), so the maker should widen after
transfer intervals and quote tight after mint intervals.**
- Mechanism and who pays: on a binary CLOB with mint and merge, a buy that meets a buy of the complement creates a
  share pair (OI up), a sell that meets a sell destroys one (OI down), and a buy that meets a sell transfers one (OI
  flat). The composition of an interval's flow is therefore written into the event's OI, wallet-free, at the capture
  cadence. In futures markets OI changes separate hedging from speculative demand (Bessembinder and Seguin) and
  predict returns (Hong and Yogo); nobody has read Polymarket's OI this way. Who pays: the maker who treats a
  transfer-heavy interval (one side has new information and the holders are leaving) like a mint-heavy one.
- Population and count (`A`): 8,006 events with OI > 0 and volume; 1,954 event-intervals per 2 h with volume, of
  which OI rose in 1,178, fell in 476 and was flat in 300; dOI / dVolume spreads widely (fact 1). About 23,000
  event-intervals a day; 300,000 in 14 days; 239 single-market events per interval where the event OI is the
  market's OI.
- Test (host-only; within-event, composition placebo). Decision time: the later capture's `received_utc`. State:
  `r = dOI / dVolume` standardised within event (OI in shares, volume in dollars, so only within-event scale is
  meaningful), classed as mint-heavy (top tercile of the event's own `r`), transfer (middle, near zero) and
  merge-heavy (bottom). Target: for each member market, the signed continuation of the interval's mid change into the
  next 2 h (J4-R tightness at both ends), averaged within the event-interval. **Primary: within-event difference of
  the continuation between the event's transfer and mint-heavy intervals, event x day clusters with a pass way;
  floor 0.5c; placebo: shuffle `r` across the event's intervals.** Secondary: the paper-maker mark-out (CH146) in
  the following pass by class.
- Economic route: maker protection (widen after transfer intervals, tighten after mint intervals; the paper maker's
  net by class). The taker follow of the transfer-interval move is a continuation route and is reported only against
  4.5c (E007's lesson: +0.36c pooled).
- Kill criteria (counts only): `event_open_interest` is updated in fewer than 70% of traded intervals (the probe
  found 85%; the census re-counts on the fresh window); fewer than 1,500 non-sports events with at least 6 traded
  intervals in SCREEN_8 (then the within-event terciles have no units); the within-event IQR of `r` is zero for more
  than half the events; or the placebo advances.
- Planning MDE versus floor: about 100,000 non-sports event-intervals with clusters in the thousands: planning MDE
  about 0.1-0.2c on the continuation difference against a 0.5c floor. Power is not the constraint; the OI field's
  update lag is (hence the first kill).
- Cost hurdle: none for the maker arm; the taker arm is a continuation moderator and must multiply E007's +0.36c by
  more than ten to clear 4.5c, which is why it is reported only.
- Host-only: **yes.** Memory: two sidecars per step, streaming the five needed columns; under 300 MB. C 1.
- Leakage and confounds: OI may update on-chain with a lag relative to volume (the first kill and a one-pass lag
  robustness); multi-member events mix members (the single-market subset is reported separately); resolutions
  destroy OI without trading (intervals containing a member's close are excluded); neg-risk conversions move OI
  across members (CH66; a conversion way: `neg_risk` events reported separately). Sports is a parameter.
- Novelty: CH41 (farmer flow) and CH26 needed wallets; CH09/CH66 are neg-risk mechanics; CH79 is the side flag. New:
  the event's OI change as the wallet-free composition of flow. N 4, EV 3, C 1.

**CH151. Holder-base turnover as the inattention clock (wallet-free CH26): an event whose open interest is large
relative to its lifetime volume is held by people who do not trade; when news moves such an event, the adjustment
is slow (the 2 h move continues into 24 h) because the holders who should react are not watching; in high-turnover
events the move is absorbed within the pass; the maker should not fade moves in low-turnover events.**
- Mechanism and who pays: OI / volume is the average holding period of the event's shares. A long holding period
  means a holder base that does not log in; the first movers reprice, the rest follow when they notice. Who pays: the
  maker who fades the first move in a sleepy event, and the holders who sell late. Why the crowd misses it: the ratio
  is not displayed; CH26 asked for it with wallets' redemption lags, which this does without wallets.
- Population and count (`A`): 8,006 events with OI > 0 and lifetime volume; OI / volume < 0.05 in 677, 0.05-0.2 in
  2,250, 0.2-0.5 in 2,012, 0.5-1 in 1,659, >= 1 in 1,408 (fact 1): the distribution is broad enough for terciles
  within category.
- Test (host-only; composition placebo primary because turnover is an event trait). Decision time: the capture at
  which a member's 2 h mid move exceeds 3c (the trigger, defined on the capture before, never on the target). State:
  the event's turnover tercile within its category x volume decile at the trigger. Target: the signed continuation of
  the 2 h move over the next 24 h (J4-R tightness). **Primary: the continuation difference between low-turnover and
  high-turnover events within category x volume-decile cells, event x day clusters; floor 1.0c; placebo: shuffle
  the turnover label within each cell (the composition placebo CB12-X taught).** Secondary: the within-event arm over
  time (turnover changes as volume accrues), and the paper-maker mark-out (CH146) in the following passes by tercile.
- Economic route: maker protection (do not fade, or widen, after a move in a low-turnover event); the taker follow
  at the recorded ask is reported against 4.5c; the continuation needed is 5c on a 3c trigger, which only the top
  tercile could plausibly show.
- Kill criteria: fewer than 300 non-sports triggers in low-turnover events in SCREEN_8; the cells are not mixed
  (fewer than 5 category x decile cells holding both terciles with at least 30 triggers each); or the placebo
  advances.
- Planning MDE versus floor: about 1,000-2,000 non-sports triggers in 14 days with event x day clusters: planning MDE
  about 1-1.5c on a 24 h continuation with SD about 8c, against the 1.0c floor: borderline; the L1 analogue on
  `h2_main` (the panel carried a different ratio, `volume24hr / liquidity`, as a pooled feature; disclosed) can be run
  first for the sign.
- Cost hurdle: the taker arm must clear 4.5c on a 3c trigger; the maker arm has none.
- Host-only: **yes.** Memory: as CH150. C 1.
- Leakage and confounds: turnover is correlated with age, category and liquidity (the cell design and the ways);
  OI in shares against volume in dollars means the ratio's level is comparable only within price bands (the cells
  include a price band); OI lags (the one-pass lag robustness). Sports is a parameter.
- Novelty: CH26 needed wallets; CH115 is capital lock-up by horizon; HB1 MS2 and the ML panels used activity
  ratios, not the holder base. New: the event's OI / volume as the holders' attention clock. N 3, EV 2-3, C 1.

### D. The venue's control loop (parents CH16, CH19, CH45, CH71; literature: Malinova and Park 2015)

**CH152. Reward-rate shocks as within-market natural experiments: the venue doubles or halves `rewardsDailyRate`
in about 1,500 markets per pass and toggles `rewards_max_spread` (4.5 <-> 5.5) and `rewards_min_size` (20 <-> 50)
in 900 more; depth and churn respond within one or two passes while adverse selection does not, so the maker who
quotes in the pass after a rate rise and before the depth arrives earns the headline subsidy against the old pick-off
rate, and the elasticity of the maker's loss to the subsidy (CH16's missing number) is identified within market.**
- Mechanism and who pays: Malinova and Park showed make/take fee changes move quoting behaviour fast and welfare
  slowly; here the venue's reward engine changes the subsidy continuously and publicly. Depth follows the subsidy
  with a lag (bots re-allocate on their own schedule); adverse selection follows the market's information, not the
  subsidy. Who pays: the venue (by design) and the bots that arrive late. Why the crowd misses it: the sidecar
  field is not displayed and nobody tracks its changes at 2 h cadence.
- Population and count (`A`): per 2 h step, `rewardsDailyRate` ratio >= 2x in 845 markets, <= 0.5x in 633,
  programme added in 767, removed in 771 (CH19's cliff; not re-proposed), geometry toggles 604 + 312 (fact 8). The
  census must count *distinct* markets with a material change and the toggle frequency per market: a 4.5 <-> 5.5
  oscillation every pass is a control signal, not a shock.
- Test (host-only; within-market event study with a pseudo-change placebo). Decision time: the capture that first
  shows the change. State: change type and size (ratio bins). Outcomes: spread, `depth_*_1c/5c`, `n_*_levels`,
  book age and within-pass churn (CH146/CH147's states) and the paper-maker mark-out (CH146's object) over passes
  -3..+3 around the change. **Primary: within-market before/after difference of the paper-maker mark-out for
  material rate rises versus rate cuts, event x day clusters; floor 0.5c; placebo: pseudo-change times drawn from
  the market's own no-change passes (the composition placebo); a pre-trend check on passes -3..-1 is a gate.**
  Secondary: the depth response (relative change in `depth_*_5c`) by ratio bin, a dose-response table.
- Economic route: maker timing (quote in the pass after a material rise, before depth arrives: the reward income
  per share-hour versus the paper mark-out); the CH16 ratio measured within market rather than across. Reward
  income is real money for makers; it is the one place the maker's net has been positive in the venue's own
  programme design.
- Kill criteria: fewer than 500 distinct non-sports markets with a material (>= 2x or <= 0.5x) rate change in
  SCREEN_8; the median gap between successive changes in a market is under 3 passes (then the design becomes a
  dose-response regression and is re-registered as such, not run as a shock design); the pre-trend gate fails
  (the depth already moved in passes -3..-1, so the engine responded to the book and the shock is endogenous); or
  the placebo advances.
- Planning MDE versus floor: 5,000-10,000 distinct market-change episodes in 14 days: planning MDE about 0.2-0.4c
  on the paper mark-out difference against 0.5c (adequate), and under 5% relative on the depth response.
- Cost hurdle: none for the maker arm; the reward income (a few basis points of quoted size a day) is the gross
  and the paper mark-out the cost.
- Host-only: **yes.** Memory: seven sidecars and sweeps streaming per market window; under 500 MB with a per-market
  state table. C 1-2.
- Leakage and confounds: **endogeneity is the main one** (the engine likely raises rates where depth fell: the
  pre-trend gate and the pseudo-change placebo address it, and the design says so); the rate change may coincide
  with a price-band crossing (fact 8: 78 of 5,058 coincided with a tick change; a tick way); programme start/end is
  CH19's object and is excluded.
- Novelty: CH16 asked for reward-per-adverse-selection across markets; CH19 is the cliff at programme end; CH45 the
  geometry screen; CH71/CH116 the band. New: the venue's mid-life parameter changes as within-market shocks, counted
  at thousands per pass. N 3, EV 3, C 1-2.

### E. Timing signatures and maps (parents CH66, CH95, CH22, CH56, EXECUTION_COSTS)

**CH153. Same-event synchronous prints: 335 large prints a day land within 3 s of another member's print in the same
event; they are neg-risk conversions, full-set operations or basket bets, mechanical about *which* member moved, so
their mark-out is near zero and the bids they hit revert, whereas a single-member print in the same event carries
the information; a maker who does not widen on synchronous prints keeps the venue's cheapest flow.**
- Mechanism and who pays: a conversion (NO on one member becomes YES on every other, CH66) or a full-set operation
  sells or buys several members at once; a basket bet buys several members for a theme (CH95). None says anything
  about one member relative to its siblings. Who pays: the operator, who accepts the touch on every leg. Why the
  crowd misses it: the prints arrive in separate markets and no feed groups them; CH66 and CH95 needed wallets to
  see the same operator; the timestamp does it.
- Population and count (`A`): 335 of 10,380 prints a day (3.2%) have a different-member print in the same
  `ctx_event_id` within 3 s (fact 7); cross-event equal-notional prints within 1 s are 7 a day (the thematic-basket
  arm is dead, §4). About 4,700 synchronous prints in 14 days, sports share to be counted.
- Test (host-only; within-event, composition placebo). Decision time: the print's venue `ts`. State: synchronous
  (another member within 3 s) or single. Target: CB13-T's 2-4 h and 6-8 h mark-out. **Primary: within-event difference
  of the mark-out between synchronous and single prints, event x day clusters; floor 0.5c; placebo: shuffle the
  synchronous label within event x hour.** Secondary: the reversal of the hit bids over 2 h (the CH66 route),
  reported.
- Economic route: maker protection (do not widen on synchronous prints; the paper maker's fills on them versus on
  single prints); the taker fade of the hit bids is reported against 4.5c (CH66 claimed large reversions on thin
  members; this measures them).
- Kill criteria: fewer than 600 non-sports synchronous prints in SCREEN_8 (then extend to 28 days or drop); fewer
  than 150 non-sports events with both kinds; or the placebo advances.
- Planning MDE versus floor: about 1,000-1,500 non-sports synchronous prints in 14 days: planning MDE about 1.5-2c
  against 0.5c: thin; the 28-day pre-declaration or the sports arm (uncounted) carries it.
- Cost hurdle: none for the maker arm; the taker fade needs 4.5c of reversion.
- Host-only: **yes.** Memory: one monitor day file; trivial. C 1.
- Leakage and confounds: a news event moves several members at once through separate takers (information, not
  mechanics): the 3 s window and equal notional within the group (reported) separate them; the Data API's receipt
  batching could stamp unrelated trades with near-identical `ts` (the census checks `ts` resolution and the
  distribution of gaps).
- Novelty: CH66 and CH95 needed wallets; CH67 is the sibling's resolution. New: the timestamp as the operator's
  wallet-free signature within an event. N 3, EV 2, C 1.

**CH154. First-day prints: the monitor sees 778 enriched large prints a day in markets under 24 h old (184 under
6 h), a population no AREPO panel has observed because origins start a day after listing; the first day's book is
the seed quote (CH56), set by the listing, not by trading, so the first large prints are the first opinions and
their mark-out is the largest of the market's life; the maker should not quote in the first hours, and the taker
who follows the first print is the only taker route here with a plausible 5c.**
- Mechanism and who pays: CH22 (genesis window) argued the first 24 h overprice sensational YES; CH56 that the seed
  quote anchors. Both were untestable because the panels began a day after listing. The monitor's `ctx_created_ts`
  dates every enriched print, and the 3,083 unenriched prints are candidates for markets newer than the last capture.
  Who pays: the seed quoter and the maker who joins early. Why the crowd misses it: new markets have no history and
  no attention; the venue's lists rank by volume.
- Population and count (`A`): market age at the print: < 6 h 184; 6-24 h 594; 1-7 d 3,119 (fact 7); the census joins
  unenriched prints to the next capture's `created_at` to classify them (features only). Expect 5,000-6,000 first-day
  prints in 14 days, sports share to be counted (game markets are listed days ahead, so sports first days are common
  and reported uncounted).
- Test (host-only; within-market, composition placebo). Decision time: the print's venue `ts`. State: market age
  bin at the print (< 6 h, 6-24 h, 1-7 d, > 7 d). Target: CB13-T's 2-4 h and 6-8 h mark-out. **Primary: within-market
  difference of the mark-out between first-day prints and the market's own later prints (markets created in the
  first 7 days of SCREEN_8 that print again after day 1), event x day clusters; floor 0.5c; placebo: shuffle the age
  bin within market.** Secondary: the seed quote's survival (the first capture's touch against the touch 24 h later)
  by category, descriptive.
- Economic route: maker protection (no quotes in the first hours; the paper maker's first-day fills versus later);
  taker: follow first-day prints at the recorded ask, reported against 4.5c (the 9-minute receipt lag applies; CH155
  says whether the first-day class is seen in time).
- Kill criteria: fewer than 400 non-sports first-day prints in SCREEN_8; fewer than 150 non-sports markets with both
  first-day and later prints; the unenriched prints turn out not to be new markets (then the population is the
  enriched 778 a day only, and the first kill applies to it); or the placebo advances.
- Planning MDE versus floor: about 1,500-2,500 non-sports first-day prints in 14 days with later-print pairs in a few
  hundred markets: planning MDE about 1-1.5c against 0.5c: thin; the 28-day pre-declaration carries it.
- Cost hurdle: the taker follow needs 4.5c (3.6c politics, 1.8c liquid); first-day books are thin, so the executable
  cost is nearer the p75 6.8c; the honest standing is maker protection first.
- Host-only: **yes.** Memory: monitor files and one capture per print; under 400 MB. C 1.
- Leakage and confounds: the first-day touch is the seed quote (wide), so the touch-consistent sign is less reliable
  (the staleness guard and a spread way); sports game listings dominate the age bins (parameter); a market's first
  prints may be the sponsor's own inventory placement (uninformed; the within-market contrast measures, not
  assumes).
- Novelty: CH22 and CH56 were proposed and never observable; CH142 is the series' launch window. New: the first
  hours of a market's life, observed live through the monitor. N 3, EV 3, C 1.

**CH155. The actionability and cost hurdle map: for every class x price band x size, the executable round trip from
the sweep's `depth_*_1c/5c` and the sidecar fee at $1,000 and $5,000 (not 5 shares), the receipt lag of the monitor's
prints (median 9 min, p90 8.5 h) by class, hour and day, and the enrichment coverage (70%); the table every route in
rounds 1-8 must clear, replacing the 4.5c median and the assumption that a print is actionable when it is visible.**
- Mechanism: `EXECUTION_COSTS.md` measured 5-share round trips on one sweep (10-11); the live routes trade dollars,
  and the monitor's lag decides whether a print-based signal exists in time. Who pays: nobody; the map tells the
  other families what their hurdle really is and which classes are unobservable in time.
- Population and count (`A`): 45,868 tokens per sweep with depth at 1c and 5c on both sides; 10,380 prints a day with
  `recv_ts` and `ts`; fee parameters in the sidecar.
- Test (host-only; descriptive; no counted test): (1) cost at size by class x band x liquidity from depth (the share
  of tokens where $1,000 walks past 1c and past 5c); (2) the receipt lag distribution by class, hour and day, split
  into the monitor's 5-min polling component and the remainder, and the share of prints whose lag exceeds the 2 h
  mark-out horizon (those are not signals, they are history); (3) enrichment coverage by class (the 30% unenriched);
  (4) the paper-maker crossing rate from CH146 by class as the maker's hurdle.
- Kill criteria: none (a map); it is complete when the three tables exist.
- Cost hurdle: it is the hurdle.
- Host-only: **yes.** Memory: one sweep, one sidecar, the monitor files; under 300 MB. C 1.
- Novelty: EXECUTION_COSTS is the 5-share version on one sweep; CH77 is where the fills are. New: cost at size and
  the lag table, together, as the gate every later design cites. N 1, EV 1 alone (it unlocks the honesty of every
  taker route), C 1.

---

## 3. Ranked top 5 for the next batch, then the rest

Rank = originality x plausibility x testability now x money route. "Runnable now" means the census and the
features-only frame can be built this week on the CPU lane from host files, with the counted test on a declared
fresh window from the collectors (SCREEN_8, not before 2026-10-26, event-disjoint REP_8) and nothing bound to the
`net` lane.

| Rank | ID | One line | Host-only | Population (counted) | Primary contrast |
|---|---|---|---|---|---|
| 1 | CH144 | Open versus close: a sell is a close by construction; the information is in the opens; wallet-free and side-free through CB13-T's signing | yes (L1 on `h2_main`'s 875k trades first; monitor prints for the counted test) | 10,380 large prints a day, about 800 non-sports enriched; YES 5,316 / NO 4,923 | within market x direction: mark-out(open) - mark-out(close); label shuffle within market x direction x hour |
| 2 | CH146 | Book age at the fill: the CLOB's last-update stamp as the maker's pick-off clock | yes | 45,868 tokens x 24 sweeps a day; median 87 s, 18% > 10 min | within token: paper-maker mark-out, old (> 10 min) minus fresh (< 1 min) sweeps; age-bin shuffle within token |
| 3 | CH150 | Mint share: event OI change against volume separates disagreement from one-sided flow; the maker widens after transfer intervals | yes | 1,954 event-intervals per 2 h; OI up 1,178 / down 476 / flat 300 | within event: continuation after transfer minus mint-heavy intervals; `r` shuffle within event |
| 4 | CH147 | The sticky touch and the breathing book: the 2-minute shift of depth beneath an unchanged touch predicts the next move | yes | 41,244 touch-unchanged token-pairs per pass, 21,401 with a changed book beneath | within token: slope of the next-2 h mid change on the standardised shift; shuffle within token |
| 5 | CH154 | First-day prints: the genesis window observed live for the first time | yes | 778 enriched prints a day in markets < 24 h old (184 < 6 h); 3,083 unenriched to classify | within market: first-day minus later prints; age-bin shuffle within market |

Next in line: CH152 (reward-rate shocks; large and host-only, held back by the endogeneity gate it must pass first),
CH145 (exit pressure; CH144's companion with the only hold-to-resolution route in this round), CH151 (turnover
clock; borderline MDE), CH153 (synchronous prints; thin outside sports), CH148 (footprint complement to CB16-Q;
counted only if Q leaves the loss unexplained), CH149 and CH155 (maps; run first because they cost an afternoon and
every other idea cites them).

**Screenable on data AREPO already holds (no fetch):** every idea in this file. CH155 and CH149 are pure censuses on
existing files. CH144's L1 arm, CH145's L1 arm and CH151's sign check run on the worn `h2_main` today. The counted
tests of CH144, CH146, CH147, CH150 and CH154 need only a declared fresh window that the collectors are already
writing. No idea here is bound to the `net` lane; none runs ahead of any CB11-CB16 job.

**Screen sketches for the top 5.**
- **CH144.** Population: CB13-T-signed large prints in SCREEN_8 (14 days from the first 00:00Z at or after freeze +
  24 h, not before 2026-10-26), non-sports in the primary, [0.05, 0.95]. Decision time: venue `ts`. Label: open (the
  taker bought the traded token) or close (sold), from the traded token's touch (YES touch mirrored for NO-token
  prints). Target: 2-4 h and 6-8 h print-based mark-out. Statistic: within-market `D = mean(open) - mean(close)`
  within direction, event x day clusters, hour way; floor 0.5c; within-market x direction x hour label shuffle,
  <= 1.5% of draws may qualify. Economic: paper maker net by label; taker fade of closes at the recorded ask reported
  against 4.5c / 1.8c. L1 first: the same `D` on `h2_main`'s trades with `side`, 2 h / 6 h / 24 h and the resolution
  arm, labelled worn and development.
- **CH146.** Population: every token-sweep in SCREEN_8. Decision time: `batch_receipt_utc`. State: age bin from
  `book_timestamp`. Target: paper ask and bid at the sweep's touch, filled when the next capture's mid (2-4 h, J4-R
  tightness) crosses; mark-out signed against the maker. Statistic: within-token old-minus-fresh difference, event x
  day clusters with a pass way; floor 0.5c; age-bin shuffle within token. Gate: the stamp is unchanged between the
  pass's two sweeps when the hash is unchanged (otherwise it is a response time and the idea dies). Reported: the
  fill arm on CB13-T's table where the lifted quote equals the last sweep's touch; the cross-tab of age by grain.
- **CH150.** Population: event x 2 h intervals in SCREEN_8 with `event_open_interest` present and `event_volume`
  increased; members' mids from the two captures. Decision time: the later capture. State: `r = dOI / dVolume`
  standardised within event; terciles. Target: members' next-2 h signed continuation of the interval's move,
  averaged within the event-interval. Statistic: within-event transfer-minus-mint difference, event x day clusters;
  floor 0.5c; `r` shuffle within event. Gates: OI updated in >= 70% of traded intervals; >= 1,500 non-sports events
  with >= 6 traded intervals; intervals containing a member's close excluded; neg-risk events reported separately.
- **CH147.** Population: within-pass token pairs in SCREEN_8 with an unchanged touch. Decision time: the second
  sweep. State: standardised 2-minute shift of depth beneath the touch (`5c - 1c` on each side, ask minus bid).
  Target: next-2 h signed mid change (J4-R tightness) and CH146's paper mark-out on the abandoned side. Statistic:
  within-token slope, event x day clusters with a pass way; floor 0.5c per SD; shuffle within token; concentration
  check (top-5 tokens < 30% of the variance); E003's imbalance level as a covariate.
- **CH154.** Population: large prints in SCREEN_8 in markets created inside the window's first 7 days, non-sports
  primary; unenriched prints classified by the next capture's `created_at`. Decision time: venue `ts`. State: age
  bin at the print. Target: CB13-T's mark-outs. Statistic: within-market first-day minus later difference, event x
  day clusters; floor 0.5c; age-bin shuffle within market; spread way (the seed quote is wide). Economic: paper
  maker's first-day fills; taker follow reported with CH155's lag table.

**How the families would be registered.**
- **A. Open and close (CH144, CH145).** One label (open/close) imported from CB13-T's signing by sha256; CH144 is the
  counted print-level test, CH145 its market-state companion with the carry arm; the `h2_main` arms are L1
  development and are never pooled with the live windows; CH79's side caveat is printed in every table that uses
  `side`.
- **B. The book's clocks (CH146-CH149).** One sweep-level paper-maker object shared by all four (defined once, frozen
  once); CH146 is counted, CH147 counted, CH148 conditional on CB16-Q's residual, CH149 a map; every state is
  standardised within token and shuffled within token.
- **C. Event OI (CH150, CH151).** The OI update-lag gate first (counts only); CH150 within event, CH151 within
  category x decile cells; neg-risk and single-market subsets reported separately; OI units never compared across
  events.
- **D. The control loop (CH152).** Distinct-change census and toggle-frequency gate first; pre-trend gate; the
  pseudo-change placebo; CH19's programme start/end excluded.
- **E. Signatures and maps (CH153-CH155).** CH155 and CH149 run first and are cited by every design's census; CH153
  and CH154 are counted only if their non-sports counts clear the gates, else extended to 28 days once, else dropped.

**What is honest to say about all of them.** Round 1 was carries, round 2 the maker in the right state, round 3 tails
and flow identity, round 4 measurement and new products, round 5 professional anchors and unseen populations, round 6
public clocks and the class map, round 7 who is resting and arriving, external deciders and risk premia. This
round's bet is the narrowest yet and was forced by the host: that the venue already records four things nobody has
read as state variables (whether a print opens or closes, how long a book has stood, what an event's open interest
did against its volume, and when the venue changed its own subsidy), that each gives a within-unit contrast with a
composition placebo, and that each is a maker-protection object first and a taker or carry route only where the
counted numbers say so. Two of the four fields were checked present on the host before they were proposed, two
candidates died in their own probes (market-level OI, comment bursts), one arm died (cross-event baskets), and the
cost hurdle now includes a 9-minute receipt lag that makes every print-following taker route reported only. Nothing
here is edge until it has gone through screen, frozen replication, prospective registration and an economic check at
recorded prices.

---

## 4. Ideas considered and rejected, and why

- **Market-level open-interest decomposition and turnover.** `open_interest` is blank in all 252,939 sidecar rows
  (fact 1; CB8-H found the same). Both ideas survive only at the event level (CH150, CH151). An on-chain or Data API
  `/holders` fetch would restore the market level and is `P`, not proposed this round.
- **Comment-burst tide (event `commentCount` deltas as a retail-attention clock).** 22,111 events, 1,217 with any
  comment, 9 changed in 2 h, 0 gained five or more (fact 3). Dead at the capture cadence. Comment *level* as a
  retail-presence trait is a line in CH155's class table, not an idea.
- **Cross-event equal-notional baskets within 1 s (wallet-free CH95).** 7 a day (fact 7). Dead. The same-event arm
  lives as CH153.
- **Multi-market `tx16` sweeps (one transaction filling several markets).** 0 of 10,380 (fact 7). Dead.
- **Tick-regime flips as a shock design.** 683 per 2 h step is a large population, but CH15 and CH86 own the object;
  noted as a resource for CH86, not re-proposed.
- **Reward programme starts and ends (767 and 771 per step).** CH19's cliff; excluded from CH152 and not re-proposed.
- **Book age read as a response time.** If `book_timestamp` were the CLOB's response stamp, CH146 would be void; the
  probe's quantiles (median 87 s, p99 5.9 h) say it is the last update, and CH146's gate checks it on the pass's two
  sweeps before any read.
- **The two-sweep depth change as CH133's substitute for the 120 s withdrawal rate on the cross-venue stream.** The
  stream stays sealed to 2026-11-03 and CH133 waits; the sweep version became CH147 with its own object (the sticky
  touch) rather than a proxy for CH133.
- **Clip trains (CH69's worked orders detected by regular intervals and equal sizes without wallets).** Order
  anticipation is adjacent and was rejected in rounds 1-7; the maker-protection framing adds little beyond CH39/CB3-B.
  Not proposed.
- **Reward-band membership of the lifted quote as a quoter classifier.** Folded into CH148 as a reported footprint;
  CH116 and CH71 own the band.
- **Phantom liquidity (Gamma `liquidity` against sweep depth within 5c).** A methods line in CH155, not an idea.
- **Outcome-by-text atlas on `poly_markets.json` (148,384 closed markets with questions and final prices).** No
  pre-resolution price exists on the host for them; base rates without prices are not a route. `P`, not proposed.
- **Kalshi universe on the host as a class-level base-rate anchor.** No Polymarket pre-resolution prices on the host
  for the same classes; CH134 and CH143 own the cross-venue uses.
- **Sibling spillover after a member's large print (cross-member toxicity).** The mechanical half is CH153; the
  informational half is the sum-of-asks object (CH09, CH13) whose taker route (full-set arbitrage) stands rejected.
- **Average print size or trade count as the retail-share clock.** The flow screen and HB1 carried `n_trades_1h`,
  `max_trade_size_1h` and notional ratios as pooled features; a re-run with a new name. Not proposed.
- **The `competitive` field (88% present).** Undocumented semantics; not a state variable until its definition is
  known.
- **NO-token share as a sophistication signature.** 47% of large prints are on the NO token, but both buttons are
  equally accessible; the informative split is open/close (CH144), not the token.
- **Deadline extensions, leaderboard period ends, fee-boundary twins, 45th Weather Squadron, mortality without an
  anchor, ECB/BoJ OIS, Kalshi depth moderators.** Rejected in round 7 for reasons that still hold.
- **Re-proposals of CH01-CH143 with new data** (decided carry, dispute lotteries, reward geometry, tick regimes, series
  base rates, genesis overpricing without the monitor, mention baskets, Deribit anchors, roll-call and speech clocks,
  Wikipedia edits, barrier confusion, grid atoms, hidden books, round-dollar and alert-threshold footprints, horizon
  staleness, election-night order, the pair at birth, quoter grain, wake-up prints, Kalshi settlement, statutory
  clocks, pre-release premia, OIS and actuarial anchors, series launch, the Kalshi-absent map): not re-proposed;
  where a new idea touches one, the parent is named and the new field, clock or join is stated.
- **Order anticipation, spoofing, inducing cancellations, manipulation of any kind, insider identification as a
  route, holding rewards, maker-rebate loops, taker full-set arbitrage, comment sentiment, wash detection as alpha,
  API quirks, Combo RFQ data, Polymarket US, keyed anchors, wallet-based signatures of any kind.** Rejected in rounds
  1-7 for reasons that still hold.

---

## 5. Sources consulted

### 5.1 Host probes run for this round (read-only; 2026-10-19 14:00-14:40Z; counts only)

Six streaming Python scripts, copied to the host's `/tmp`, run as `nice -n 19` with `python3 -I` (P1, P2a, P4a with
the system interpreter; P2b, P3, P4 with `/home/opc/arepo/.venv/bin/python`), then removed from `/tmp` (verified: 0
files left). Inputs were already-worn data: captures `20261013T043104Z_c420e869` and `20261013T063104Z_2d96ebf2`
(CB13-T SCREEN window), the 2026-10-13 sweeps (first pass pair `20261013T00xx`, 116 s apart) and the first sweep of
four consecutive passes, `live_trades/trades-20261013.jsonl`, and one field-presence count on the last 2026-10-15
capture. **Disclosed feature exposure:** P2a decoded `best_bid`, `best_ask`, `bid_size_1`, `ask_size_1` of one sweep
pair in memory to test equality between the two sweeps and to class sizes by roundness, and `book_hash`,
`book_timestamp`, `n_bid_levels`; P2b decoded the same for four sweeps and the `clob_rewards`, `rewards_*`,
`order_price_min_tick_size`, `fee_type`, `competitive`, `open_interest`, `event_open_interest` sidecar columns; P3
decoded `event_open_interest`, `event_volume`, `clob_rewards`, `rewards_*`; P4 decoded the monitor's `ts`, `recv_ts`,
`ctx_event_id`, `condition_id`, `cash`, `ctx_created_ts` and tested `ctx_mid` for presence (never its value); P4a
decoded `outcome_index`, `tx16`, `ctx_category` and key names. No `side`, `wallet_hash`, forward price, mark-out or
outcome was decoded. Nothing was written on the host.

| # | Script | Inputs | Printed |
|---|---|---|---|
| P1 | `ch8_probe_oi.py` | two sidecars 2 h apart (10-13) | common markets 252,939; `open_interest` present 0; `volume_num` rose in 5,615; events 22,111, with comments 1,217, changed 9, +5 or more 0; flips: fee 0, `rewards_max_spread` 604, tick 683, `accepting_orders` 0; `clob_rewards` non-empty 17,760 |
| P2a | `ch8_probe_book.py` | the first intra-pass sweep pair of 10-13 | 24 sweeps, 12 pairs, gaps 116-158 s; 45,868 tokens; two-sided 45,837, one-sided 31; same hash 19,843, same touch 41,244, same touch with changed hash 21,401; sizes fractional 33,421 / x5 19,586 / x10 16,417 / x100 6,655 / odd 15,626; both tokens present for 0 markets; level histogram (fact 6) |
| P2b | `ch8_probe_two.py` | first sweeps of four consecutive passes; two sidecars; the 10-15 sidecar | 40,408 tokens common; hash unchanged 2 h 1,477 / 4 h 1,047 / 6 h 719; touch unchanged 2 h 27,646; dormant level bins; `clob_rewards` flips 5,058 (78 with a tick flip), sub-fields (fact 8); field presence 10-13 and 10-15 (fact 2) |
| P3 | `ch8_probe_three.py` | one sweep (age); two sidecars (event OI, rates) | book age quantiles (fact 4); events with OI and volume 8,025, OI > 0 8,006; 1,954 traded, OI up / down / flat 1,178 / 476 / 300; dOI/dVol bins; turnover bins; rate ratio bins; `rewards_max_spread` and `rewards_min_size` (old, new) pairs |
| P4a | `ch8_probe_prints.py` | `trades-20261013.jsonl` | 10,380 prints, 1,928 markets; `outcome_index` 0: 5,316, 1: 4,923, 999: 141; `tx16` spanning > 1 market 0; `ctx_*` key names; fee-type categories |
| P4 | `ch8_probe_four.py` | `trades-20261013.jsonl` | enriched 7,297; age bins; receipt lag quantiles; same-event synchronous 335; cross-event equal-notional 7 |

The scripts, verbatim (the bytes that ran, minus the host path prefix, which is `/home/opc/arepo/data-dumps/research_lab`):

```python
# P1 ch8_probe_oi.py
import csv, gzip, os
base = ROOT + "/snapshots"
caps = sorted(d for d in os.listdir(base) if d.startswith("20261013T"))
a, b = caps[2], caps[3]
def num(x):
    try: return float(x) if x not in ("", "None") else None
    except ValueError: return None
def load(cap):
    out = {}
    with gzip.open(f"{base}/{cap}/rows_ext.csv.gz", "rt") as f:
        for row in csv.DictReader(f):
            cc = num(row["event_comment_count"])
            out[row["market_id"]] = (num(row["open_interest"]), num(row["volume_num"]), None if cc is None else int(cc),
                                     row["event_id"], row["fee_type"], row["taker_base_fee"],
                                     row["clob_rewards"][:60] if row["clob_rewards"] else "", row["rewards_max_spread"],
                                     row["order_price_min_tick_size"], row["accepting_orders"])
    return out
A = load(a); B = load(b); common = set(A) & set(B); n = len(common)
# ... counts of OI presence, volume_num rises, dOI/dVol bins, OI/volume bins, comment deltas, parameter flips; print() of counts only
```

```python
# P2a ch8_probe_book.py (system python3 3.6: the age block failed on fromisoformat and printed 0; re-done in P3)
import csv, gzip, os, datetime as dt
from collections import Counter
base = ROOT + "/book_sweeps"
sw = sorted(d for d in os.listdir(base) if d.startswith("20261013T"))
# intra-pass pairs = consecutive sweeps < 1800 s apart; load token_id -> row for the first pair
# same_hash / same_touch / same_touch_but_hash_changed counts; roundness(bid_size_1), roundness(ask_size_1) classes
# (fractional, x100, x10, x5, odd); markets with both tokens; n_bid_levels histogram capped at 20. print() of counts only
```

```python
# P2b ch8_probe_two.py (venv python 3.11)
# first sweep of each pass on 10-13 (12 passes); tokens common to 4 consecutive passes; hash equality over 2 h / 4 h / 6 h;
# touch equality over 2 h; n_bid_levels bins split dormant/active; two sidecars: clob_rewards JSON diff by sub-field
# (rewardsDailyRate, startDate, id, programme added/removed), co-occurrence with tick flips, rewards_max_spread and
# rewards_min_size flips; field presence counts on 10-13 and on the last 10-15 capture. print() of counts only
```

```python
# P3 ch8_probe_three.py (venv python 3.11)
# (i) book age = batch_receipt_utc - book_timestamp (epoch ms), quantiles over one sweep; (ii) per event: event_open_interest
# and event_volume in both captures; traded events; OI up/down/flat; dOI/dVol bins; single vs multi-member; OI / lifetime
# volume bins; (iii) rewardsDailyRate ratio bins, from/to zero; (old,new) pairs of rewards_max_spread and rewards_min_size.
# print() of counts only. (Its part (iv) crashed on a None field before printing and was re-run as P4.)
```

```python
# P4a ch8_probe_prints.py (system python3)
import json
from collections import Counter, defaultdict
path = ROOT + "/live_trades/trades-20261013.jsonl"
n = 0; oi = Counter(); tx_markets = defaultdict(set); cats = Counter(); ctx_keys = Counter(); per_market = Counter()
with open(path) as f:
    for line in f:
        try: d = json.loads(line)
        except Exception: continue
        n += 1; oi[d.get("outcome_index")] += 1; tx_markets[d.get("tx16")].add(d.get("condition_id"))
        per_market[d.get("condition_id")] += 1
        for k in d:
            if k.startswith("ctx_"): ctx_keys[k] += 1
        cats[d.get("ctx_category", "?")] += 1
multi = sum(1 for s in tx_markets.values() if len(s) > 1)
print("prints", n, "distinct markets", len(per_market), "outcome_index counts", dict(oi))
print("tx16 groups", len(tx_markets), "tx16 spanning >1 market", multi)
print("ctx keys:", sorted(ctx_keys)); print("top categories:", cats.most_common(8))
```

```python
# P4 ch8_probe_four.py (venv python 3.11)
import json
from collections import Counter
path = ROOT + "/live_trades/trades-20261013.jsonl"
def num(x):
    try: return float(x) if x not in (None, "", "None") else None
    except (ValueError, TypeError): return None
rows = []
with open(path) as f:
    for line in f:
        try: d = json.loads(line)
        except Exception: continue
        rows.append((num(d.get("ts")), d.get("ctx_event_id"), d.get("condition_id"), num(d.get("cash")),
                     num(d.get("ctx_created_ts")), d.get("ctx_mid") not in (None, ""), num(d.get("recv_ts"))))
rows = [r for r in rows if r[0] is not None]; rows.sort(key=lambda r: r[0])
enriched = sum(1 for r in rows if r[5]); age = Counter()
for r in rows:
    if r[4] is None: age["no_created_ts"] += 1; continue
    h = (r[0] - r[4]) / 3600.0
    age["neg" if h < 0 else "<6h" if h < 6 else "6-24h" if h < 24 else "1-7d" if h < 168 else "7-30d" if h < 720 else ">30d"] += 1
lag = sorted((r[6] - r[0]) for r in rows if r[6] is not None)
def q(p): return round(lag[int(p * (len(lag) - 1))], 1) if lag else None
same_event_sync = 0; cross_event_equal_cash = 0; n = len(rows)
for i, r in enumerate(rows):
    j = i + 1; se = False; ce = False
    while j < n and rows[j][0] - r[0] <= 3:
        o = rows[j]
        if r[1] and o[1] == r[1] and o[2] != r[2]: se = True
        if o[1] != r[1] and o[3] is not None and r[3] is not None and abs(o[3] - r[3]) < 0.5 and rows[j][0] - r[0] <= 1: ce = True
        j += 1
    same_event_sync += se; cross_event_equal_cash += ce
print("prints", n, "enriched (ctx_mid present)", enriched, "| market age at print bins:", dict(age))
print("recv_ts - ts lag s (n, 10/50/90/99 pct):", len(lag), q(.1), q(.5), q(.9), q(.99))
print("prints with another member of the same event printing within 3 s:", same_event_sync,
      "| prints with a cross-event equal-cash print within 1 s:", cross_event_equal_cash)
```

P1, P2a, P2b and P3 are summarised above where their bodies are long; their full logic is the counts listed in the
table and in §0 facts 1-8, and their only outputs were those printed lines. **Residual limitation, stated plainly:**
the scripts were run from `/tmp` and removed afterwards; the texts here are the drafting session's own copies, and the
bytes that ran have no hash on the host. Future round-8 probes should be committed before they run (CB16 round 1
item 18).

### 5.2 AREPO documents read (cited inline by name)

`CREATIVE_HYPOTHESES_2026-10-15.md` through `-21.md` (titles, §0, rankings and rejected lists); `CREATIVE_BATCH_15.md`
§0-§2 and §11; `CREATIVE_BATCH_16.md` §0-§2 (selection, probes G1-G2, corrected premises, seals, dates);
`EXPERIMENT_LEDGER.md` (the last 60 section headers; CB12-X Stage 1; CB13 GL round 1; ML-r4_book);
`lab_dashboard/registry.json` (44 entries: status, verdict, plain-language reason); `DATA_ARCHIVE_2026-10-13.md`;
`COLLECTION_HOST.md`; `data_catalogue/README.md`; `EXECUTION_COSTS.md` (cost distribution and break-even);
`queue/README.md` (lanes, memory rule); `backend/astrolabe/research_lab/book_sweep.py` (token selection),
`trade_sample.py` (strata), `ext_sidecar.py` (field mapping: `open_interest` = Gamma `openInterest`,
`event_open_interest` = event `openInterest`, `event_comment_count` = `commentCount`), `ml_panel.py` (`ml_turnover`,
`ml_quote_staleness_h`), `cb13_common.py` (forbidden sidecar columns), `cb8_holders.py` (the blank-OI finding). Host
listings: `data-dumps/research_lab/` directory sizes and the headers of `snapshots/*/rows.csv.gz`, `rows_ext.csv.gz`,
`book_sweeps/*/rows.csv.gz`, `trade_samples/*/{features,trades,wallets}.csv.gz`, `live_trades/trades-*.jsonl` (key
names), `history/h2_main/{frame.csv.gz,trades/*.csv.gz,prices/*.csv.gz,panel_H2h.csv.gz}` (headers only),
`cb1_extract/*.csv.gz` (headers), `cross_venue/` (file names and the key names of `poly_markets.json`).

### 5.3 External literature (named, not fetched)

Pan and Poteshman (2006), "The Information in Option Volume for Future Stock Prices", Review of Financial Studies
(open-buy volume predicts; closing volume does not). Boehmer, Jones and Zhang (2008), "Which Shorts Are Informed?",
Journal of Finance. Copeland and Galai (1983), "Information Effects on the Bid-Ask Spread", Journal of Finance (the
limit order as a free option). Foucault (1999), "Order flow composition and trading costs in a dynamic limit order
market", Journal of Financial Markets (picking-off risk). Hasbrouck and Saar (2009), "Technology and liquidity
provision: The blurring of traditional definitions", Journal of Financial Markets (fleeting orders). Bessembinder and
Seguin (1993), "Price Volatility, Trading Volume, and Market Depth: Evidence from Futures Markets", Journal of
Financial and Quantitative Analysis (open interest as depth and composition). Hong and Yogo (2012), "What does futures
market interest tell us about the macroeconomy and asset prices?", Journal of Financial Economics. Malinova and Park
(2015), "Subsidizing Liquidity: The Impact of Make/Take Fees on Market Quality", Journal of Finance. Lee and
Radhakrishna (2000), "Inferring investor behavior: Evidence from TORQ data", Journal of Financial Markets (trade size
as a trader-type proxy; the reason the average-size clock is not proposed).
