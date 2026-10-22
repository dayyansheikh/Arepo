# Creative hypotheses, round 13: innovations, direct clocks and the new streams, built for the census (2026-10-27)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-22, on parent `82e4295e`
(`chore/arepo-claude-setup`), worktree `feat/creative-r13`; the file carries the round's planned date as earlier rounds
did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59), round 3 `-17.md`
(CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130), round 7 `-21.md`
(CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md` (CH169-CH179), round 11
`-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201); this file starts at **CH202** and repeats none of them. Where an
idea builds on an earlier one, the parent is named and the new mechanism, clock, population or join is stated. Every
number quoted from an AREPO document is a development, census or probe result, not evidence. One file; no code, no
queue specs, no other commits. **No network request, no host probe (no `ssh oracle`) and no `data-dumps` read were used
for this round** (by instruction); every count below is taken from a named AREPO document (the ledger's LT4 censuses and
2026-10-22 entries, `LIVE_TESTS_7.md`, `signal_engine/DESIGN_V1.md` sections 3, 16, 21 and 22, `CANDIDATES.md` rows 17-19,
`NEW_STREAMS_2026-10-19.md`, the stream modules' docstrings, the cost-model calibration, the maker-rewards snapshot) and
is named as such. Where no count exists the entry is marked **unprobed** and the pre-registration census is the first
gate.

## 0. How to read this file

**The brief that binds this round (owner priorities, 2026-10-19, 10-21; orchestrator brief for round 13).** Ideas die
at the pre-registration census: populations too small, strata not permutable, planning MDE over the floor, and, new
since round 12, a falsification arm whose own MDE breaks the 0.5c cap. So every idea here states, before its mechanism is
argued, (1) a **population arithmetic**: units a day and distinct events in 21 days from a cited AREPO count, else
"unprobed"; (2) a **permutation and cluster structure** plausibly permutable within market x UTC day or market x
two-day block strata (>= 4 units in >= 50% of strata, the LT4-LT7 gate), with the size scenario it would bind; (3) a
**planning MDE** against a cost-aware floor, computed with LT5/LT6's pessimistic formula at LT7's multiplier and design
effect, and, for every level-built state, the **F-MDE** of its falsification arm. The owner wants original mechanisms
(how a taker or a maker could make money after costs: about 5c per dollar round trip for a median taker, maker rewards
where relevant), not textbook re-tests; a strong preference for ideas that become **light prospective live tests
quickly** on streams the host already captures (net lane, < 500 MB), especially the new keyless streams (PredictIt
1 min, Smarkets 5 min, ESPN odds 10 min, gamma rules hourly, reward params 2 h) and cross-stream joins; category-agnostic,
category as a parameter (sports inclusion is the owner's later call); every idea as a point-in-time **signal-engine
feature family** with a proposed embargo token and date. This round's family is **LT8**, registered after LT7.

**What changed since round 12 (from the ledger entries of 2026-10-21 20:47Z to 10-22 05:30Z, `LIVE_TESTS_7.md` sections
0, 6 and 7, `signal_engine/DESIGN_V1.md` sections 8, 21 and 22, `CANDIDATES.md` rows 17-19 and the round-4 embargo
request, `COLLECTION_HOST.md`, the dashboard of 10-22 06:26 UTC+1).**
- **LT7 is a frozen design of five** (CH195, CH191, CH197, CH193, CH192; design text at `cedfd6be`, sha256
  `840f4500…`), window not before 2026-12-08 (21 days, keyed to LT6's `END_UTC`), analysis about 12-30. **CH194 was
  withdrawn before registration (uncounted):** R1 found the held-against-fresh contrast on `chg_1h / x` informed by
  E002/E004 and `chg_1h`'s timing untestable by any available gate; R1 invited "a redesign with a direct timing gate".
  LT7's own planning at E022's measured design effect **6.196** (`m_21` 260.8) and the 0.5c F-MDE cap says **every
  remaining test is likely to drop at census; expected k is 0 to 2.** The F-MDE (`MDE x sqrt(2 / (1 - r_w))`) is what
  kills the level states: CH195 0.75c at `r_w` 0.5, CH197 0.66c at 0.6, CH193 0.41c, CH192 0.27c.
- **Embargo round 4 applied (10-22 ~01:00Z):** `book` and `movetype` to 2026-12-31; new tokens `resist`, `capath`,
  `deepbook`, `absorbed`, `ivr`; `mm_fresh` withdrawn with CH194. Every date is the later of 12-31 and LT7's analysis commit.
- **The book timing overlap (DESIGN_V1 section 21):** sweep 1 of pass k starts about 7 minutes after the capture whose
  Gamma mid anchors the labels; on two 10-21 captures 5.4-6.4% of eligible markets had already moved > DELTA by sweep
  time, about a third of all 2 h movers. `se7_lgbm_all`, `se3_lr_book` and `se14_lgbm_movetype` are promotion-ineligible;
  **CH200 (`sweep2`) was declined** (sweep 2 minus sweep 1 is part of the label's own path). **`book0` was built
  (section 22):** the eight book columns from the newest complete pass sweep finished before the origin (on the host the
  previous pass's last sweep, about 110 minutes earlier), plus `b0_lag_s`, `b0_spread` and `b0_gap` (origin Gamma mid
  minus the pre-origin sweep mid); coverage 92-94%; `se18_lgbm_all_b0` (broad, promotion-eligible, K = 4) and
  `se19_lr_book0` (embargoed to 12-31). A development diagnostic (seen before the specs were committed, nothing changed
  after it) showed `b0_gap` correlating -0.04 to -0.16 with the 2 h label move and `b0_spread` +0.09 to +0.15 with a move
  larger than DELTA. **Anything here that reads a pre-origin sweep against the origin's Gamma mid is informed by that
  diagnostic and says so.**
- **CH199 (`rulesrc`) was killed at its census (10-22 ~01:00Z):** 44.7% of the 18,232 eligible non-sports markets appear
  in the `gamma_rules` stream (the top-3,000 hourly frame plus the 6-hourly full frame of open markets with 24 h volume),
  and 19.9% carry a parseable resolution-source host, below its own 30% kill line. The frame, not the field, is the
  limit: **a `gamma_rules` idea lives on at most 45% of the eligible non-sports panel.**
- **The new streams are confirmed running by the resize record** (ledger, 10-22 ~05:30Z: last poll before and first
  after the 03:10-03:16Z outage: predictit 03:10 / 03:14, smarkets 03:05 / 03:15, espn_odds 03:02 / after 05:02,
  gamma_rules 02:51 / 04:50). This is the first documentary evidence of their cadences on the host (`streams_crontab.txt`
  in the repo is still commented: the install was by hand). The `reward_params` collector (2 h, since 10-20T23:20Z) keeps
  the CLOB's native and sponsored reward configurations, the sponsor count and the computed daily totals, which the
  Gamma sidecar does not (`reward_params_collector.py` docstring). The gaps of 10-22 are deviations, never backfilled.
- **Host:** resized to 2 OCPU / 12 GB on 10-22 03:10-03:16Z (6 minutes down; no problems). LT5's capture census q0561
  failed once on memory (a per-run series cache at the 3 GB address cap) and is re-armed at 5 GB; LT6's seals are done
  and its censuses queued; LT4 E022's size check runs 10-22 and registration is due by 10-25; E026 is registered
  (collection from 10-25). CB8-W1 is "not testable (source)" (counted); CB13, CB14, CB15 and CB18 are closed; SB2-J4-R
  is VOID.
- **Signal engine:** first prospective leaderboard 10-21 (one day; a pipeline check); development walk-forward se1
  +0.041, se7 +0.046 nats on `dir_2h`; `se17_lgbm_mm_900k` registered; the `regime` family dropped (worse than se1);
  promotion rule `se-promotion-v2` declared (event + UTC-day two-way bound).

### 0.1 What round 13 learned from LT7's planning, the timing overlap and the CH199/CH200 deaths (the design rules of this file)

1. **The falsification arm is now the binding gate, and a level state pays for it twice.** Rule 5 of round 12 (every
   level-built state carries a falsification arm in its verdict) was adopted by LT7 as F with a 0.5c F-MDE cap, and
   LT7's own planning says four of five tests fail it: the far-future twin of a persistent state is correlated with it
   (`r_w` 0.5-0.8), so F's MDE is 2-3x the primary's. **Rule: the tested term is an innovation (the change of a state
   between two pre-origin observations) or a per-interval label whose far-future twin is nearly independent of it
   (planning `r_w` <= 0.2, so F costs at most 1.6x); a level enters only as a control. Where a label is not level-built,
   F is a reported label (R1 accepted that for CH191).**
2. **No sweep state is read inside its own label window.** Sweep 1 of pass k is 7 minutes into the label of origin k and
   a third of 2 h movers have moved by then (DESIGN_V1 section 21). **Rule: every book state here is read from the
   previous pass's sweeps (`book0`'s construction: finished before the origin capture started, about 110 minutes
   earlier), or the decision time is the sweep's own receipt with the target starting at the next complete capture.
   Nothing here reads sweep 1 or sweep 2 of pass k against an origin-k target.**
3. **A whole-panel population has a whole-panel design effect.** `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)` grows with
   the units per event over the window: E022's mover family gave `m_21` 260.8 and DE 6.196; a whole-panel state with 252
   slots per market and 10-member events gives `m_21` about 2,500 and **DE about 50**. LT7 already warns that CH192 and
   CH197 "may compute a larger DE at census". **Rule: every whole-panel MDE below is computed at DE 51 (an uncapped
   size-weighted mean event size of 10) and at DE 31 (with a declared member cap: the primary runs on events with <= 10
   eligible members, larger ladders are a reported arm), never at the floor. The cap is declared now, before any count;
   it is a census knob, not a tuning knob.**
4. **A timing state needs a direct clock.** CH194 died because Gamma's `chg_1h` is a venue-computed field whose interval
   timing no gate could test, and because half its content (the 1 h reversal) was a confirmed E002/E004 effect. **Rule:
   timing here comes from receipts the host wrote itself (a sweep's receipt against the Gamma row's receipt, a stream
   poll's `recv_utc`), and any half of a state that a seen diagnostic already measured is named as informed in the entry
   (CH202's late part is `b0_gap`).**
5. **A stream's frame is its population.** CH199 had a field on every market it could see and died because it could
   see 45% of the panel (19.9% with the field parseable). **Rule: each stream idea states the stream's coverage of its
   population from a cited count (`gamma_rules` 44.7% of eligible non-sports; ESPN 76 games with odds on one evening;
   PredictIt 867 keys; Smarkets 677 books; Kalshi 116 pairs; `reward_params` 13,661 rewarded markets), and is an LT8
   candidate only if the covered population alone passes the arithmetic; otherwise it is engine-first or map first.**
6. **External frames give tens of events; the exception is a frame that renews every day.** CB13-R, CB14-W and CB15-P
   gave 58, 46 and 12 events. ESPN's scoreboard is today's games: 76 with odds on one evening, so about 1,000-1,600
   distinct game clusters in 21 days, with 2-4 markets each (DE near its floor). **Rule: the only external-frame LT8
   candidate is the one whose frame renews daily (CH205), and it is a category parameter the owner sets.**
7. **Few clusters, large design effects, Inconclusive by design (E026: DE 23.9, MDE 3x its floor).** **Rule: political
   cross-venue joins (PredictIt, Smarkets, Kalshi: a few dozen events) are engine-first and maps, never LT8 primaries.**
8. **Readers must be bounded.** q0561 failed at a 3 GB address cap because a per-run cache kept every series. **Rule: every
   LT8 reader here is a per-capture, per-market streaming pass over two or three files (< 500 MB, net lane), extending an
   existing LT reader by a few columns; nothing holds the panel in memory.**
9. **Pin early, run late, and name what was seen.** E015 (11-15), E022 (11-17), LT5 (about 11-22), LT6 (about 12-08) and
   LT7 (12-30) will be analysed before any LT8 window opens. **Rule: LT8's states, estimators and gates are pinned before
   2026-12-07T12:00Z; a state adjacent to a sealed test's construct (CH203 next to V's and CH197's book, CH202 next to
   E015's anatomy) discloses it, and the `b0_gap` diagnostic is disclosed wherever a pre-origin sweep meets an origin mid.**

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture (engine base eligibility): 42,161-51,790 (10-20 20:31Z to 10-21 14:31Z; DESIGN_V1 sections
   3 and 16). Non-sports share **unprobed** (sports are 31-36% of mover populations: E020, E021), so "about two thirds",
   about 30,000, is a derived planning figure. Eligible non-sports markets on the 10-21 22:31Z capture: 18,232 (the CH199
   census, CANDIDATES row 17; a narrower eligibility than the engine's base: the census's own filter). Both figures are
   quoted where used.
2. Movers: 2 h movers >= 1c about 2,750 an interval non-sports (P1b), 60% quote-only, 27% traded; E022's census 18,517
   sweep-covered traded non-sports movers in two days, 2,539 events, strata 0.446 (market x day) / 0.599 (block2), design
   effect 6.196; sweep coverage 0.9996.
3. Timing inside the interval (DESIGN_V1 section 21, two 10-21 captures, about 50k eligible each): |sweep-1 mid - origin
   Gamma mid| > DELTA on 5.4-6.4% of eligible markets; |2 h move| > DELTA on 16.6-19.9%; so about a third of 2 h movers had
   moved by the sweep (7 minutes). `book0` lag about 110 minutes, coverage 92-94% (section 22).
4. Sweeps: 65,771 tokens a sweep, two sweeps a pass about two minutes apart; `best_bid/ask`, `*_size_1`, `depth_*_1c/5c`,
   `n_*_levels`, `book_timestamp`, `tick_size`, `min_order_size`; one token per market; the touch unchanged in 90% of
   books within a pass (CH147's probe). Sidecar: `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, `fee_type`,
   `order_price_min_tick_size`, `created_at`, `uma_resolution_statuses`, `event_*`; rows: `end_date`, `liquidity`,
   `volume24hr` (present on 22% of rows), `chg_1h/1d/1w`, `last_trade_price` (omitted on 56%).
5. Own-path coverage from the engine's `quotes/`: `sp_rv6h` 98%, `sp_rv3d` 85%, `sp_rv7d` 78% (10-21 12:31Z).
6. Rewards: 13,661 rewarded markets on the CLOB's current feed (10-20, `reward_params_collector.py`); 13,683 in the
   maker-rewards snapshot; 5.2% of markets with a programme on 10-21; native pool $138k-182k a day; a two-sided minimum
   quote earns a median $0.05-1.00 a day on about $19 of capital (MAKER_REWARDS_STUDY section 1). The `reward_params`
   stream holds native and sponsored configurations (`markets_native`, `markets_sponsored`), rates, start and end dates,
   the sponsor count and the computed daily totals; the share of markets with a *future* configuration is **unprobed**.
7. Streams (dry run 10-19; `NEW_STREAMS` section 3; module docstrings): PredictIt 867 keys (about 200 markets, 600+
   contracts; `buy_yes`, `sell_yes`, `buy_no`, `sell_no`, `last`, `date_end`, `status`; `src_ts` raw); Smarkets 1,734
   keys, 677 books in politics and current affairs (top 3 levels a side, `last` with Smarkets' own `last_ts`); ESPN 94
   games, 76 with odds, 12 leagues (moneyline, spread, total, each with `open` and `close` (= current until kick-off),
   `state`, `period`, `clock`, scores); `gamma_rules` 3,799 keys in the top-3,000 frame, 3 changed keys in 25 h, 2,383 new
   keys a day, fields `question`, `description`, `resolutionSource`, `endDate`, `startDate`, `outcomes`, `groupItemTitle`,
   `customLiveness`, `umaBond`, `umaReward`, `resolvedBy`, `hasReviewedDates`, `fallbackResolutionType`, `negRiskOther`;
   every row carries the poll's `started_utc` / `finished_utc` and per-request `recv_utc`. Kalshi: 116 matched pairs,
   120 s (E009/E010, sealed to 11-03). Monitor: 10,522 prints >= $1k a day (22% non-sports), median 9 minutes late.
8. Event clusters: 33,849 event clusters over 2,581,045 triples in five UTC days (SB2-J4-R, whole universe); E022's
   2,539 in two days.
9. Costs (cost-model-v1): a $100 taker round trip 2.9c at >= $100k liquidity, 3.9c at 10k-100k, 7.2c at 1k-10k; a 5-share
   touch round trip 4.5c; a passive touch order fills 3.1% of the time within an hour and loses 2.38c to adverse selection
   against a 2 h mark (0.39c at >= $100k); makers about break-even before rewards (non-sports fill-weighted -0.37c); the
   sports round trip about 5.2c (prior art, gap 10).
10. Engine: se1 +0.0408 nats over the champion on `dir_2h` (development walk-forward); `book0` K = 4; `surprise` family
    holds UTC weekday and hour (embargoed to 11-19); `participation` to 11-25; `event` to 11-22.

**The reading that steers this round.** Round 12 read what every market shows at every capture; its six states were
levels, and LT7's planning shows that a level's falsification arm costs more than the level's own test. Round 13 reads
**what changed between two observations the host already made before the origin**, and **what clock the host itself
stamped**: the part of the previous move that the CLOB had already made seven minutes in (CH202), the depth and the
levels that arrived behind a touch that did not move (CH203), the slot at which this market, and not the venue, has
moved every day this week (CH204), the sportsbook line that moved since the last capture (CH205), the reward programme
that is scheduled to start (CH206). Innovations have near-independent far-future twins, so F is affordable; direct
clocks need no semantic gate. Five engine-first families follow on the streams whose frames do not reach a test
(CH207-CH211).

**Data labels.** `A` = on the host now, written by the running pass or a running stream (captures, sidecar, two sweeps,
trade samples, the monitor, the Kalshi poller, the engine's `quotes/`, `features/` and aux tables including `book0`, the
five keyless streams, `reward_params`). `A~` = on the host but a join or matcher has to be written and counted first
(ESPN game to Polymarket market; PredictIt or Smarkets contract to Polymarket market). `P` = a fetch is needed (none here).
**Sealed and not usable by anything here:** LT2's, LT3's, LT4's, LT5's, LT6's and LT7's stores once registered, CB16's
and CB17's stores, CB8-H's holders, E009/E010's `cross_venue_live/` to 2026-11-03, E011's `surprise_live/` to 2026-11-10,
E025's and E026's stores and the E026 frozen modules. J4-R `[2026-10-16, 2026-10-21)` and CB13-T's holdout
`[2026-10-21, 2026-10-26)` are refused for every maker mark-out object; nothing here is one.

**Windows and registration this round proposes (LT8).** An eighth live-test family, registered separately from LT2-LT7
and after LT7's registration commit (or its recorded drop), with its own Holm family (k <= 5): origin window of **21 days
from the first 00:00Z at least 24 h after the LT8 registration commit and not before 2026-12-30T00:00Z** (after LT7's
proposed `END_UTC` 12-29, so that CH203's book states share no origin with CH195 and CH197; the date slides later with
LT7's), single analysis at least 36 h after the end, no extension. The window spans the year-end holidays and the first
weeks of January; the census projects from worn October days and the registration discloses that late-December volumes
may be lower (a counts-only weekly line, never a look). **Pin early (rule 9):** states, estimators and gates by
2026-12-07T12:00Z. CH205 is a category parameter: it is registered only if the owner has set category to include sports
by the pin date; otherwise it is recorded as "not proposed (scope)" and never counted. Collection overlap with E011,
LT2-LT7, E025 and E026 is disclosed and is overlap only: different hypotheses, no pooling, stores never opened by one
another. E-numbers are assigned at registration.

**Hygiene that binds every idea.** Decision time is the latest input's own receipt (the Gamma row's `received_utc` for
capture states; the stream poll's `recv_utc` for stream states; never a sweep of the same pass), states are computed from
that input and strictly earlier ones; targets are price-based (the complete captures' Gamma mids) and start after the
decision time: `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})` for move-continuation primaries, the first interval's own
change `mid_{k+1} - mid_k` only where the state is not a move of the same market (CH203, CH205), daily units for slow
states; nothing reads Gamma outcome fields except the engine-first ideas, which use the engine's receipt-timed `res_7d`.
Clustering is CR1 on event, two-way event x UTC day and UTC day with p the largest, the event t on `G - 1` where a class
is sparse, and an ex-crypto primary everywhere (LT7's rule 7, adopted: crypto up/down ladders follow an external
reference and are a large share of mover populations; the crypto arm is reported; universe completeness is unchanged);
**the primary is a within-market contrast or slope estimated by expanding-past demeaned OLS over all eligible units, the
Freedman-Lane permutation gate within the census-fixed stratum (block2 by default) is the binding gate, the liquidity-tier
correlation gate (|corr| <= 0.5 within and pooled) and the AR(0.9) size scenarios bind for every state, and F (one rule:
Δ one-sided p < 0.05 and Δ̂ >= 0.5 x beta-hat, LT7's form) is a verdict condition for every level-built state whose
census F-MDE is <= 0.5c and a reported label otherwise.** Sports stays a parameter (the sidecar's `fee_type` plus
CB17's frozen sports list; CH205 is the one sports-scoped idea and says so; every other idea reports the sports arm
uncounted).

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader that extends an
existing LT reader by a few columns, population bounded by a named count, census on files already sealed (LT5's capture
and sweep seal, LT7's); 4 = pure reader, population unprobed but bounded above by a named count; 3 = pure reader with an
unprobed and possibly small population, or a map or a matcher first; 2 = needs a stream whose coverage of the population
is unprobed; 1 = needs fetches or weeks. My judgement, not measurements.

**Planning-MDE arithmetic used throughout (LT5/LT6's pessimistic form at LT7's constants, stated once).** Class contrast:
`MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; slope per SD of a continuous
state times the tercile gap (about 2.2 SD): `MDE = 3.47 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap`.
`n_eff` = units in markets with >= 2 units of the population in the census days (planning: 80% of raw). `DE_gate` =
`max(floor, 1 + (m_21 - 1) x 0.02)`: mover families use E022's measured **6.196**; whole-panel families use **51**
(uncapped) and **31** (<= 10-member events); daily-renewed external frames use the floor 3.0. `VIF_w` 1.3 for labels,
1.5 for book states. SDs: skip continuation 5c, 2 h change 4c (3c in quiet books), |2 h move| 3c, 24 h change 6c, spread
2c. **F-MDE** = `MDE x sqrt(2 / (1 - max(0, r_w)))` at the planning `r_w` stated per idea (innovations 0 to 0.2; levels
0.5 to 0.8), capped at 0.5c as a verdict condition. **Floors:** 0.5c gross per share in the favourable class or tercile for
a mid target; 0.5c of E|move| for a magnitude target; **1.0c (one tick on a 0.01 book) for a spread target** (CH206: a
maker's reward eligibility and the taker's cost both move by whole ticks). Every MDE is quoted at the planning count and
at a quarter of it.

**Counts table (what was counted before each idea was written; daily unless stated; the source named).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH202 | non-sports 2 h mover at k - 1 with sweep 1 of pass k - 1 received | about 2,750 non-sports movers an interval (P1b) x 12 x sweep coverage 0.93-0.9996: 30,000-33,000 a day; held share **unprobed** (about a third had moved by the sweep: section 21) | P1b; DESIGN_V1 sections 21-22; LT4 17.3 |
| CH203 | non-sports eligible market x capture with pass sweeps k - 2 and k - 1 both before the origin and a quiet touch | about 28,000 non-sports with `book0` a capture (30,000 x 0.93); quiet share planning 80% (movers are 17-20%: section 21): about 22,000 a capture | DESIGN_V1 sections 3, 21, 22 |
| CH204 | non-sports eligible market x capture with 7 days of own slots and a scheduled class | `sp_rv7d` coverage 78% of about 30,000: 23,000 a capture; scheduled class share **unprobed** (planning 10-20%) | DESIGN_V1 section 16 |
| CH205 | ESPN game with odds x pre-game 2 h capture of its matched Polymarket market | 76 games with odds on one evening (12 leagues); matcher coverage **unprobed** (planning 60%): about 45 matched games a day, 6-12 pre-game units each (NFL / CFB up to 80) | NEW_STREAMS section 3; `espn_odds.py` |
| CH206 | rewarded market x capture around a scheduled reward start | 13,661 rewarded markets; future configurations a day **unprobed** (planning 30-80 starts a day; kill line 30) | `reward_params_collector.py`; MAKER_REWARDS section 1 |
| CH207 | eligible non-sports market in the `gamma_rules` frame (trait) | 44.7% of 18,232 = about 8,150 markets; non-default `umaBond` / `customLiveness` share **unprobed** | CANDIDATES row 17; `gamma_rules.py` |
| CH208 | Polymarket political market matched to a PredictIt / Smarkets / Kalshi contract | 116 Kalshi pairs; PredictIt about 200 markets; Smarkets 677 books; overlap **unprobed** (planning 200-400 markets in 30-60 events) | DESIGN_V1 section 3; NEW_STREAMS section 3 |
| CH209 | rewarded market x capture with `book0` and the sidecar | 13,661 x 0.93: about 12,700 a capture, all categories; farmer-touch share **unprobed** | fact 6; DESIGN_V1 section 22 |
| CH210 | market x capture whose pass k - 1 sweeps 1 and 2 differ | 10% of 65,771 books change within a pass: about 6,500 a pass | CH147's probe (round 8) |
| CH211 | market x capture whose pre-origin sweep mid moved >= 1c between passes k - 2 and k - 1 | about 17-20% of 28,000: 4,800-5,600 a capture | DESIGN_V1 sections 21-22 |

---

## 1. Map: where money might be, given the costs, the nulls, the census deaths and the F cap

The cost model fixes the frame: a taker needs 2.9c gross in the most liquid tier and 4.5c at the median; a passive fill
costs 2.38c of adverse selection against a 2 h mark, 0.39c at >= $100k, and nothing on the exit leg if held to
resolution; sports costs 5.2c a round trip. The census fixes the population: whole-panel states and daily-renewed frames
recur; political cross-venue joins and rule edits do not. LT7's planning fixes the estimator: a level state pays for its
falsification arm, an innovation does not. So the money question for every state below is: **does the change the host
already observed before the origin, or the clock the host itself stamped, move the forecast of the next 2-24 h mid, the
next spread, or the resolution, on a population that recurs within market, and does it tell a maker which side to post,
when to step aside, or when to be first?**

| Family | What changed, or what clock, that nobody has read | Money route |
|---|---|---|
| A. Direct clocks on the own path (CH202, CH204) | the share of the previous move the CLOB had made seven minutes in; the slot at which this market has moved every day this week | maker: fade the late part, quote the held part at its new level; widen at the market's own hot slot; taker: follow held moves >= 3c (reported), never trade a scheduled market at its hot slot |
| B. Innovations in the resting book before the origin (CH203) | the depth and the price levels that arrived or left behind a touch that did not move | maker: lean toward the building side over 2-6 h, step aside from the thinning side; taker: nothing (fractions of a cent) |
| C. Clocks and innovations from the new streams (CH205, CH206) | the sportsbook line that moved since the last capture against a Polymarket price that did not; the reward programme scheduled to start | maker: skew toward the steam, be the first farmer in; taker: steam >= 5c de-vigged in >= $100k game markets (reported, sports scope) |
| D. Engine-first (CH207-CH211) | the desk's own dispute parameters; the minute of the news on three political venues; the touch that is a farmer's minimum; two minutes of book news read before the origin; the ladder that travelled | HTR passive entry by class (`res_7d`); maker protection (do not read a farmer touch as information; do not post against a program re-quote) |

---

## 2. Hypotheses

### A. Direct clocks on the own path (parents CH194 (withdrawn), E004/E006, E021/CH170, E015/CH156, CH191/LT7, CH57, CH33, round 11's rejected own-hours profile; literature: Glosten and Milgrom 1985, Easley and O'Hara 1992, Chae 2005, Hong and Stein 1999)

**CH202. Seven minutes or two hours: the sweep clock splits the previous move into the part the CLOB had already made
when pass k - 1's first sweep was received (seven minutes after capture k - 1's Gamma rows) and the part that arrived in
the 113 minutes after it. By origin k the early part has stood in the book for at least 113 minutes without being
re-centred away; the late part is fresh. A held move is ratified and persists; a fresh move carries the bounce. This is
CH194's question with the direct timing gate R1 asked for, from two receipts the host wrote itself, on every mover.**
- Mechanism and why it is non-obvious. A mid that the CLOB reached within minutes of the previous capture and still
  shows two hours later has been seen by every maker who could have faded it; they did not (a Glosten-Milgrom update
  accepted). A move that arrived late in the interval has not been tested, and part of it is the quote re-centering whose
  bounce E004 measured. The same split has a second reading that predicts the same sign: the early part is partly Gamma's
  display catching up with a CLOB that had already moved (a stale displayed mid, CH37's artefact in reverse), which is
  not news in this interval and has nothing to bounce; the late part is a real intra-interval move with a bounce
  component. Both readings say the early part persists more than the late part; the test does not separate them and
  does not need to: the maker's rule is the same. Nobody has read the two parts against each other; CH194 tried with
  `chg_1h` and died on the field's semantics. Who pays: the taker who chases the late part; the maker who fades the early
  part. Why the crowd misses it: the chart shows the 2 h change, not when inside the two hours it happened.
- Data join and decision clock (`A`, L 5). Unit: non-sports ex-crypto 2 h mover at k - 1 (LT3 1.4 eligibility; `x_{k-1}
  = mid_k - mid_{k-1}`, |x| >= 1c and >= 2 ticks) whose pass k - 1 sweep 1 is present for its outcome-0 token with a
  two-sided book, and capture k present. State: `early = sign(x) x (swmid_{k-1} - mid_{k-1})`, `late = x - early`
  (both in cents, signed by the move), `early_share = early / |x|`, clipped to [-0.5, 1.5]. Classes: **held** =
  `early_share >= 0.75` (the CLOB had made at least three quarters of the move seven minutes in); **fresh** =
  `early_share <= 0.25`; **mixed** = the rest (reported). Decision time: capture k's `received_utc` (the latest input;
  sweep 1 of pass k - 1 was received about 113 minutes earlier; nothing of pass k's sweeps is read). Controls: E015's
  anatomy label of the k - 1 move (traded, quoted parallel, one-sided, spread-change, never), `log |x|`, spread_k, spread
  at the k - 1 sweep, logit mid, |mid - 0.5|, `log1p volume24hr`, own 24 h change, `rv24`, tick stratum, `b0_lag_s`.
- Target and horizon. `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})` (SD 5c); M2: `c1 = sign(x) x (mid_{k+1} - mid_k)`
  reported (the bounce lives there and is the half a seen diagnostic already measured, below); 24 h secondary.
  Hypothesis (one-sided): within market, E[c_skip | held] - E[c_skip | fresh] > 0. Mirror M1 (reported): the whole-panel
  continuous version, the slope difference of `c_skip` on `early` and `late` over every eligible market with `book0`.
- Paper rule and economic check. Maker: after a fresh move, re-post toward the pre-move level for one pass; after a held
  move, quote at the new level (the adverse selection a passive fill suffers, 2.38c against a 2 h mark, is where the
  fresh class's bounce would pay the maker). Taker: follow held moves >= 3c in >= $100k markets, 2.9c round trip; reported
  only; the MDE below is a fraction of that hurdle.
- Population arithmetic. About 2,750 non-sports movers an interval (P1b) x 12 x sweep coverage 0.93 (book0's measure;
  E022's 0.9996 is the traded subset's) = 30,000-33,000 a day, 640,000-690,000 in 21 days before the ex-crypto cut
  (crypto share of movers **unprobed**; planning 25%: 480,000-520,000). Held share: section 21 says about a third of 2 h
  movers had moved > DELTA by the sweep, so held about 25%, fresh about 55% (planning; the census counts). Distinct
  events: E022's 2,539 in two days is the traded subset's count; all-mover events in 21 days **unprobed**, lower bound
  2,539.
- Permutation and cluster structure. Label per unit; strata market x UTC day, else block2; planning share 0.5-0.7
  (E022's 0.446 / 0.599 is the traded-mover floor; quote-only movers recur in program-quoted markets and raise it; CH194's
  planning said the same). Binding scenarios: LT5 1 (iid label), 2 (persistent market rates), 3 (control at corr 0.7 with
  a real effect: the anatomy label), 4 (MA(2) skip target). Clusters: event; `DE_gate` = E022's 6.196.
- Planning MDE. `n1_eff` 100,000 (held: 500,000 x 0.25 x 0.8), `n2_eff` 220,000 (fresh): `3.47 x 5c x sqrt(1/100,000 +
  1/220,000) x sqrt(6.196) x 1.5 x sqrt(1.3)` = **0.26c**; at a quarter of the units 0.52c (borderline, as every mover
  test is). F: the label is not level-built in LT7's sense (a timing share, not a level), and its far-future twin (the
  split of the move at k + 4 -> k + 5) exists only where that interval is also a mover; **F is a reported label** (R1's
  ruling for CH191); no F-MDE gate.
- Confounders and the control. Anatomy (a held quote-only move is a program re-centering that stayed: controlled; gate
  |corr(1[held], 1[parallel])| <= 0.5 within); momentum (24 h change controlled); bounce (skip target; M2 reports it);
  stale Gamma rows (the "display catch-up" reading, declared above as the same-signed alternative; the census prints
  the share of held units whose Gamma row `received_utc` precedes the sweep by more than 10 minutes, information only);
  crypto (ex-crypto primary); tick coarseness (>= 2 ticks; tick stratum). **Informed, disclosed (rule 4):** `late_{k-1}`
  is, up to sign, the engine's `b0_gap` at origin k (origin Gamma mid minus the pre-origin sweep mid), whose correlation
  with the 2 h label move (-0.04 to -0.16: a reversal of the late part over k -> k + 1) was seen in DESIGN_V1 section
  22's diagnostic on 10-22. That is M2's content, not the primary's: the primary is the held-against-fresh contrast on
  the skip target, which nothing has read. The broad `se18_lgbm_all_b0` (visible) holds `b0_gap`; its family attribution
  is hidden; the pin discloses the visible broad score as a development look at half the state.
- Cheapest census (counts only; LT5's sealed captures and LT7's sealed sweeps: the 23 pass-sweep days 10-19 .. 10-21 give
  the k - 1 sweep for every k). Distribution of `early_share` among movers; class shares; permutable share; corr gates;
  crypto share; `n_eff`; VIF; the stale-row share. Kill if movers with a k - 1 sweep < 1,500 a capture, if held or fresh
  < 15%, if the permutable share < 0.5, or if a corr gate fails.
- Challenger feature: **yes.** `swclock` (`se-aux-swclock-v1`): `sw_early_c`, `sw_late_c`, `sw_early_share`, `sw_held`,
  `sw_fresh`, for the k - 1 move, from the engine's `quotes/` and the `book0` table's sweep (the same sweep `book0`
  chooses); also `sw_early_share_6h` (the mean over the last three intervals). Read against `se1_lgbm_mm`. Embargo:
  `book0` to 12-31 (the sweep source) and a new token `swclock` to the later of 2027-01-23T00:00Z and LT8's analysis
  commit.
- Scores: N 3, EV 3, L 5. Parents: CH194 (withdrawn: the same question on `chg_1h`; here the clock is the host's own
  receipts), E004/E006 (the bounce), E021/CH170 (the age of the move; trade-sample clock, dropped at the strata gate),
  E015 (anatomy as a control), DESIGN_V1 sections 21-22 (the timing measurement and `b0_gap`, disclosed), CH37 (the
  stale displayed mid).

**CH204. The market's own clock: a market whose moves have landed in the same two-hour slot on five of the last seven
days has a schedule (a data release, a model run, a court calendar, a league's game time); at that slot today its move
is scheduled information and its makers should have widened; at the other eleven slots its moves are the ordinary
noise of the book. The schedule is per market, read from its own path, not a venue clock; it forecasts the size of the
next move and tells a maker when to step aside and a taker when not to trade.**
- Mechanism and why it is non-obvious. Scheduled information arrival is the textbook case where spreads widen and
  volume concentrates (Chae 2005; Easley and O'Hara 1992), but on this venue nobody has read a market's *own* schedule;
  round 11 rejected an "own-hours profile" (activity hours, ambiguous sign) and the engine dropped the venue-wide
  `regime` clock (rule 8). The construct here is different on both counts: it is the concentration of a market's own
  past |moves| across the 12 daily slots, it varies per market and rotates within the market-day (one hot slot, eleven
  cold), and its primary is a **magnitude** (whose sign is not ambiguous), with the signed continuation at the hot slot
  a reported arm. CH57 is the weather special case (model runs at 00/06/12/18Z); CH33 reads spreads around the
  resolution event; CH28 the scheduled source. Who pays: the maker whose quote sits tight through the market's release
  slot (the 2.38c adverse selection concentrates there); the taker who crosses the spread at the hot slot. Why the
  crowd misses it: the schedule is visible only to someone who has watched this market for a week at a fixed cadence,
  which is exactly what the pass does.
- Data join and decision clock (`A`, L 4). Unit: non-sports ex-crypto eligible market x capture k with >= 70 of the last
  84 slots observed in the engine's `quotes/`. State, from the 84 slots before k: the per-slot mean |2 h move| over the
  last 7 days, `m_s` for s = 1..12; concentration `sc_conc = max_s m_s / sum_s m_s` (1/12 .. 1); the hot slot `s* =
  argmax m_s`; **scheduled** = `sc_conc >= 0.35` and the daily argmax equals `s*` on >= 4 of the 7 days (a rule declared
  now, not fitted); `sc_hot = 1[slot(k) == s*]`. Decision time: capture k's receipt. Controls: `rv24`, `rv7d` (the level
  of volatility; the state is its *allocation* across slots), spread, logit mid, |mid - 0.5|, `log1p volume24hr`, hours
  to end, the market's E015 anatomy share over the week.
- Target and horizon. `a = |mid_{k+1} - mid_k|` (the magnitude of the next move; SD 3c); secondaries: the spread at k + 1
  (do makers widen into the hot slot: the spread at the hot slot minus the market's mean spread, reported), and the
  signed continuation `c_skip` of hot-slot moves against cold-slot moves (reported; sign undeclared). Hypothesis
  (one-sided): within scheduled markets, E[a | hot] - E[a | cold] > 0.5c.
- Paper rule and economic check. Maker: in a scheduled market, widen or pull two slots before `s*` and re-post after;
  the economic check is the share of the market's weekly |move| that falls in the hot slot (if 40% of the week's
  movement lands in one twelfth of its slots, the maker's adverse selection per hour is 4.8x there). Taker: trade
  scheduled markets at cold slots only (a cost rule, not an edge); no taker route is claimed.
- Population arithmetic. `sp_rv7d` coverage 78% of about 30,000 non-sports: 23,000 markets a capture; scheduled class
  share **unprobed** (planning 10-20%: weather ladders, macro releases, court and vote calendars; sports game days are
  the parameter; crypto dailies are excluded): 2,300-4,600 scheduled markets, one hot unit each a day (2,300-4,600 hot
  units a day, 48,000-97,000 in 21 days) against eleven cold units each. Events: weather and macro ladders of 5-10
  members; distinct events **unprobed** (planning 500-1,500 in 21 days: this is the risk).
- Permutation and cluster structure. `sc_hot` is a per-interval label that takes the value 1 once per market-day by
  construction and 0 eleven times: strata market x UTC day hold 12 units always (share 1.0 by construction among
  scheduled markets with full days). The Freedman-Lane null (the slot does not matter given the market and the day) is
  exactly the hypothesis's complement. Binding scenarios: LT5 2 (persistent market rates: the state is built from the
  market's own level of |move|, which the controls hold), a new scenario declared now, **S12: volatility clustering
  with no daily seasonality** (an AR(0.9) |move| process with a fixed random `s*`: the gate's size must be <= 0.058),
  and LT4 L10's event clusters. Clusters: event; `DE_gate` whole-panel 51 / 31 (ladders).
- Planning MDE. `n1_eff` 39,000 (hot, low end) against `n2_eff` 430,000 (cold): `3.47 x 3c x sqrt(1/39,000 + 1/430,000)
  x sqrt(41) x 1.5 x sqrt(1.3)` = **0.60c** at the low end (DE 41 for 8-member ladders, between the two whole-panel
  figures), 0.43c at the high end (4,600 scheduled markets), 0.52c / 0.37c with the <= 10-member cap (DE 31); at a
  quarter of the units 1.2c / 0.85c. **Borderline by construction; the census decides and the kill line is stated.** F:
  the state is level-built (past |moves|), so F applies: the **rotated schedule** (the same construction with `s*`
  shifted by six slots) must show no contrast; `r_w` between `sc_hot` and its rotation is -1/11 by construction
  (planning 0): F-MDE = 1.41 x MDE = 0.85c / 0.61c, above the 0.5c cap at the planning counts, so **F is a reported
  label unless the census count is at least twice the planning high end**; a second falsification, the **out-of-window
  schedule** (the same `s*` built from days 8-14 before k must predict as well as the 7-day one; a chance slot does
  not persist), is reported.
- Confounders and the control. Volatility level (controlled; the state is a share); a market whose only move in the week
  was one jump (the >= 4 of 7 days rule); the venue's own clock (sports game times and crypto dailies would make `s*`
  a category clock: crypto excluded, sports a parameter, and a **category-share gate**: no single category may hold
  more than 50% of scheduled units, else the primary is run per category and reported); the engine's `surprise` family
  holds UTC hour and weekday (embargoed to 11-19): the state is an interaction of own history with the slot, disclosed
  under that token. Placebo (rule 5): the rotation, above.
- Cheapest census (counts only; LT5's sealed captures 10-12 .. 10-21 give seven days of own slots for 10-19 .. 10-21).
  Distribution of `sc_conc`; scheduled share; category shares; hot-slot distribution over the 12 slots (a venue clock
  would show one spike; a market clock shows a spread); permutable share; `n_eff`; the S12 size run. Kill if scheduled
  markets < 1,200 a capture, if one category holds > 70% of them, if the hot-slot distribution has > 50% mass in one
  slot (then it is a venue clock and the idea is dead by rule 8), or if S12 fails.
- Challenger feature: **yes.** `sched` (`se-aux-sched-v1`): `sc_conc7d`, `sc_hot_now`, `sc_slots_to_hot` (0..11),
  `sc_hot_absmove7d` (the hot slot's mean |move|), `sc_scheduled`, from the engine's own `quotes/` of slots k - 84 .. k.
  Read against `se1_lgbm_mm` and against `se15_lgbm_surprise` once `surprise` lifts (11-19). Embargo: `surprise` to
  11-19 (hour and weekday live there) and a new token `sched` to the later of 2027-01-23T00:00Z and LT8's analysis commit.
- Scores: N 4, EV 3, L 4. Parents: CH57 (weather model-run lag: the special case), CH33 (pre-event spread cycle), CH28
  (scheduled-source markets), CH18 (UTC-hour maker share: a venue clock, which this is not), round 11 section 4's
  rejected own-hours profile (activity hours, ambiguous sign; here a magnitude primary on a move schedule), CH158 and
  the engine's `regime` (the venue tilt and the venue clock, both dead; this is per market).

### B. Innovations in the resting book before the origin (parents CH197/LT7, CH190/LT6 V, CH169/E020, CH133, CH147, CH116, CH195/LT7; literature: Kaniel and Liu 2006, Rosu 2009, Cao, Hansch and Wang 2009, Cont, Kukanov and Stoikov 2014)

**CH203. The quiet book: between two pass sweeps two hours apart, both received before the origin, the touch did not
move but the depth behind it did. Depth that arrives on one side of an unmoved touch is a patient trader building a
position with resting orders (the informed prefer limit orders when their information is long-lived); price levels that
leave one side are makers withdrawing from the side they fear. The *innovation* of the five-cent imbalance, with its
level held fixed, predicts the mid's next move; its far-future twin is nearly independent of it, so the falsification arm
is affordable.**
- Mechanism and why it is non-obvious. Order-flow imbalance (the change in resting sizes) moves prices at high frequency
  (Cont, Kukanov and Stoikov 2014); on this venue the book studies read levels: `book` was null at 12.7% coverage, V
  reads the post-move skew, CH197 the behind-touch level, CH195 the pre-move depth, E020 (cancellations as one-sided
  quote-only moves) died at the strata gate. Nobody has read the **silent** component: the depth that changed while the
  touch did not, on the whole panel, from two sweeps that both predate the origin. The patient-trader reading (Kaniel
  and Liu 2006: informed traders use limit orders when information is long-lived; Rosu 2009) says the building side is
  the informed side; the maker-withdrawal reading (levels leaving one side) says the thinning side is the feared side;
  both predict the mid moves toward the building side and away from the thinning one. Who pays: the maker who keeps
  quoting the thinning side at the old level; the taker who sells into a bid that has been building for hours. Why the
  crowd misses it: the touch, the spread and the displayed liquidity figure are all unchanged.
- Data join and decision clock (`A`, L 5). Unit: non-sports ex-crypto eligible market x capture k with the last sweeps of
  passes k - 2 and k - 1 both complete and finished before capture k started (the `book0` rule applied twice; the k - 1
  sweep is `book0`'s own), both two-sided, and a **quiet touch**: |swmid_{k-1} - swmid_{k-2}| < 0.5c and |mid_k -
  swmid_{k-1}| < 0.5c (the Gamma mid at the origin has not left the sweep mid either; all three inputs predate or are
  the origin). State: `dimb5 = imb5_{k-1} - imb5_{k-2}` with `imb5 = (Db5 - Da5) / (Db5 + Da5)` on the outcome-0 token's
  5c notional depths; `zdimb5` standardised within the expanding past of the market. Secondaries: `dlev = (nb_{k-1} -
  nb_{k-2}) - (na_{k-1} - na_{k-2})` (price levels arriving minus leaving, per side), `dgrain` (the change in mean size
  per level on each side: few large orders arriving is the patient reading, many small the farmer one), `dimb1` (the
  touch-size innovation). Decision time: capture k's `received_utc`. Controls: `imb5_{k-1}` (the level), `log1p (Db5 +
  Da5)_{k-1}`, `b0_spread`, `b0_lag_s`, logit mid, |mid - 0.5|, `log1p volume24hr`, own 24 h change, `rv24`, tick
  stratum, `rewarded` and `rw_in_band` (farmer re-posts are mechanical: CH209's flag as a control).
- Target and horizon. `c2 = mid_{k+1} - mid_k` signed as YES (the state is not a move of the same market, so the first
  interval is clean: no bounce sits at the origin by construction of the quiet filter); M1: `y6 = mid_{k+3} - mid_k`;
  24 h secondary. Hypothesis (one-sided): within market, the slope of `c2` on `zdimb5` > 0, `imb5_{k-1}` held fixed.
- Paper rule and economic check. Maker: lean the quote toward the building side (post the bid a tick higher when the bid
  side has been building) and step off the thinning side for one pass; gross, no fills modelled (E025 part B owns
  signal-conditional fills); the floor is 0.5c in the top tercile, a fifth of the median adverse selection. Taker: nothing
  (fractions of a cent against 2.9-7c).
- Population arithmetic. About 28,000 non-sports markets with `book0` a capture (30,000 x 0.93) x quiet share about 80%
  (movers are 17-20%; the second quiet condition removes a few more; planning 75%) = about 21,000 a capture, 250,000 a
  day, 5.3M in 21 days; ex-crypto planning 4.2M; `n_eff` 3.4M. Events: the whole eligible universe, tens of thousands
  (J4-R's 33,849 event clusters in five days).
- Permutation and cluster structure. Continuous state per unit on every eligible market: strata market x UTC day hold
  up to 12 units by construction (share near 1.0; the quiet filter removes movers, so planning 0.9). Binding scenarios:
  LT5 7 and 8 (persistent book states: the *level* persists, the innovation does not; the AR(0.9) world is run on the
  level and the innovation is derived from it, so the gate's size is tested where it matters), LT6 V's depletion
  asymmetry world (a one-sided depletion that is mechanical: the farmer control). Clusters: event; `DE_gate` 51 / 31.
- Planning MDE. Slope at the tercile gap, SD of `c2` in quiet books 3c, `n_eff` 3.4M: `3.47 x 3c / sqrt(3.4M) x sqrt(51)
  x 1.5 x sqrt(1.5) x 2.2` = **0.16c** (DE 51), 0.13c (DE 31); at a quarter of the units 0.33c / 0.25c. F: the far-future
  innovation (`imb5_{k+3} - imb5_{k+2}`, sweeps after the target, read through a sizes-only loader as LT7's lag-slot
  loader does) is the innovation of a mean-reverting level, so `r_w` <= 0 (planning 0): **F-MDE 1.41 x 0.16c = 0.23c
  (quarter 0.46c), under the 0.5c cap: F is a verdict condition** (the first book state in the programme for which it is).
- Confounders and the control. The level (controlled; the within-market VIF of `zdimb5` on `imb5_{k-1}` is printed and
  gated <= 2); mechanical farmer re-posts that move depth symmetrically or follow a reward-band change (`rewarded`,
  `rw_in_band`, CH209's farmer-touch flag and a `reward_params` rate-change flag as controls); depletion by a taker fill
  that did not move the touch (volume24hr's change over (k - 2, k - 1] as a control; a fill eats depth on the side it
  hit, which is the *opposite* sign of the building story and therefore a conservative confounder); the liquidity gate
  (|corr(zdimb5, log liquidity)| <= 0.5 within and pooled); `hollow` (none: the state has no Gamma liquidity in it);
  adjacency to V (post-move skew, after a move) and CH197 (the behind-touch level): disclosed; LT8's origins start after
  LT7's `END_UTC`; the pin precedes `T_LT6` and `T_LT7`. Placebo (rule 5): the far-future innovation above, and a
  **fake split**: `dimb1` in place of `dimb5` must not beat it (the touch's innovation is the farmers' and is reported).
- Cheapest census (counts only; LT7's sealed pass sweeps 10-19 22:36Z .. 10-21 22:38Z give 22 consecutive pass pairs).
  Quiet share; distribution of `dimb5` and its within-market SD (>= 0.05 in >= 50% of markets with >= 6 units); corr
  gates; VIF; `r_w` of the lead and lag innovations (sizes only); `n_eff`; `m_21` by event. Kill if quiet units < 10,000 a
  capture, if the within-market SD gate fails, if `r_w` > 0.3, or if a corr gate fails.
- Challenger feature: **yes.** `quietbook` (`se-aux-quietbook-v1`): `qb_dimb5`, `qb_dimb1`, `qb_dlev_b`, `qb_dlev_a`,
  `qb_dgrain_b`, `qb_dgrain_a`, `qb_quiet` (the filter as a flag), from `book0`'s sweep and the previous pass's last sweep
  (one more sweep per capture than `book0` reads; the same construction rule). Read against `se1_lgbm_mm` and
  `se19_lr_book0` once `book0` lifts. Embargo: `book0` and `book` to 12-31 and a new token `quietbook` to the later of
  2027-01-23T00:00Z and LT8's analysis commit.
- Scores: N 3, EV 3, L 5. Parents: CH197 / LT7 (the behind-touch level), CH190 / LT6 V (the post-move skew), CH169 / E020
  (arrivals and cancellations read at the touch of one-sided movers; dropped), CH133 (depth fade at 120 s on the
  cross-venue stream), CH147 (the breathing book within a pass), CH116 (band-stripped imbalance), CH195 / LT7 (pre-move
  depth), Cont, Kukanov and Stoikov 2014 (OFI; here its silent, pre-origin, two-hour form).

### C. Clocks and innovations from the new streams (parents CH29, CH14, CH19, CH152, CH201, CH16/CH45, CH183/LT5 R, E025; literature: Kaunitz, Zhou and Kreiner 2017, Levitt 2004, Foucault, Kadan and Kandel 2005, Telonex case study as MAKER_REWARDS cites it)

**CH205. Steam at the book: the sportsbook's moneyline moved since the last capture and Polymarket's price did not.
Sportsbooks move lines on sharp action within minutes; Polymarket's pre-game makers anchor on the book's line but
update on their own schedule, so the line's last move is information Polymarket's next two hours will absorb. CH29 reads
the level gap at kick-off; this reads the movement, at the 10-minute clock, on every game the ESPN board carries that
Polymarket lists. Sports only by construction: a category parameter the owner sets; registered only if sports is in.**
- Mechanism and why it is non-obvious. Closing-line value is the best-documented betting-market regularity (Kaunitz,
  Zhou and Kreiner 2017: +3.5% at closing odds over 479k games; Levitt 2004 on why books move lines); AREPO has never had
  a line stream. The new part is the clock: a line that moved from `open` toward one side between two captures is a
  *steam* move; a Polymarket game market whose mid did not follow in the same interval is lagging a public price. The
  question is whether the lag is absorbed in the next two hours (a forecast the engine can read) or only at kick-off
  (CH29's reading). Who pays: Polymarket's pre-game taker who buys the side the book has just moved against; the
  Polymarket maker who did not re-centre with the book. Why the crowd misses it: Polymarket's game page shows no line.
- Data join and decision clock (`A~`, L 3: the matcher is a map first). Unit: ESPN game g (12 leagues) with a DraftKings
  moneyline, matched to a Polymarket binary game market by a declared matcher (league, UTC date within 1 day, both team
  names or abbreviations in the market question; one-to-one; unmatched games counted), x complete capture k in the
  pre-game window (`state` pre and `date` after capture k's start). State: `steam = p_book(k) - p_book(k-1)`, the
  de-vigged home-win probability from the two moneylines (the standard proportional de-vig, declared), using the last
  ESPN poll received before capture k's start (the decision time is the max of that poll's `recv_utc` and the Gamma
  row's `received_utc`); `steam_open = p_book(k) - p_book(open)` as a secondary. Controls: Polymarket's own change over
  (k - 1, k], the level gap `p_book(k) - mid_k`, hours to kick-off, spread, logit mid, `log1p volume24hr`, league.
- Target and horizon. `c2 = mid_{k+1} - mid_k` signed as the home side (the state is the book's move, not Polymarket's,
  so the first interval is clean; a Polymarket bounce from its own move is held by the own-change control); M1: the
  change to the last pre-game capture; `c_skip` reported. Hypothesis (one-sided): within game market, the slope of `c2`
  on `z steam` > 0 with the level gap and the own change held fixed.
- Paper rule and economic check. Taker: buy the side the book moved toward when `steam` >= 2 pp de-vigged and the level
  gap is in the same direction, in markets with >= $100k liquidity; the sports round trip is about 5.2c (gap 10), so the
  route is reported and expected to fail the cost check. Maker: skew the quote toward the book's move within the
  interval (the maker's loss is the taker's gain above; the route is the mirror, gross, no fills).
- Population arithmetic. 76 games with odds on one evening (12 leagues; weekends with college football and the NFL run
  higher, weekdays lower); matcher coverage **unprobed** (planning 60%): about 45 matched games a day, 6-12 pre-game
  captures each (the ESPN board shows today's games; NFL and college football show the current week, up to 80 units):
  about 400-800 units a day, 8,000-17,000 in 21 days; `n_eff` 7,000-14,000. Events: one game is one cluster (both
  sides' markets, spread and total markets): about 950 games in 21 days.
- Permutation and cluster structure. Continuous state per unit on every pre-game capture: strata market x UTC day hold
  up to 12 units (share by construction >= 0.8 for games listed a full day ahead; planning 0.7). Binding scenarios: LT5
  1-3 and a declared **S13: a book that random-walks and a Polymarket mid that follows the book's level with a one-slot
  lag** (the level gap is a control; the gate's size must hold when the lag runs through the level, not the move).
  Clusters: game; `m_21` 10-20 units per game, `DE_gate` = floor 3.0.
- Planning MDE. Slope at the tercile gap, SD of `c2` in pre-game markets 3c, `n_eff` 7,000: `3.47 x 3c / sqrt(7,000) x
  sqrt(3) x 1.5 x sqrt(1.3) x 2.2` = **0.81c**; at 14,000 units 0.57c; at a quarter 1.6c / 1.1c. Above the 0.5c floor at
  the planning counts; a 42-day window (the NFL, NBA, NHL and European football seasons run through December and
  January) would give 0.57c / 0.40c. **Declared now: CH205 is proposed with a 42-day window or not at all.** F: the state
  is an innovation (the book's move), so the far-future steam (the book's move over (k + 1, k + 2]) has `r_w` near 0
  (planning 0.1): F-MDE 1.49 x MDE = 0.85c at 42 days, above the cap: **F is a reported label**; the level gap's own slope
  (CH29's object) is the second reported arm.
- Confounders and the control. The level gap (CH29's mechanism; controlled, reported as its own arm); Polymarket's own
  move in the same interval (controlled: the test is whether the book adds to Polymarket's own path); in-play states
  (`state` pre only; ESPN's `close` means current until kick-off, NEW_STREAMS section 4); books that move for liability
  reasons rather than information (unobservable; the de-vigged move is the state either way); the matcher's errors (the
  census audits 50 matches by hand, counts only, and reports precision); injuries announced on ESPN's own feed are the
  mechanism, not a confounder.
- Cheapest census (counts only; the stream's day files from the install, about 10-19, and the sealed captures 10-19 ..
  10-21). Games a day with odds; matcher coverage and audited precision; pre-game units per matched game; the
  distribution of |steam| per 2 h slot (the state must be nonzero in >= 20% of units); permutable share; `n_eff`. Kill if
  matched games < 30 a day on average over the census days, if precision < 0.9, if |steam| >= 0.5 pp in < 20% of units,
  or if the permutable share < 0.5.
- Challenger feature: **yes.** `steam` (`se-aux-steam-v1`): `st_steam_2h`, `st_steam_open`, `st_gap`, `st_h_to_kick`,
  `st_league`, NaN outside matched pre-game sports markets, from the last ESPN poll received before the origin capture
  started; the matcher table is a write-once artefact with its own sha256. Read against `se1_lgbm_mm` on the sports
  subset (the engine scores category breakdowns). Embargo: a new token `steam` to the later of 2027-02-13T00:00Z (a
  42-day window from 12-30) and LT8's analysis commit; no other token (nothing registered reads sportsbook lines).
- Scores: N 3, EV 4 (if sports is in), L 3. Parents: CH29 (closing-line value: the level at kick-off), CH14 (moneyline
  against spread and total consistency in one game), CH23 (end-of-game hope premium; in-play, not this), CH48
  (regulation-time rule misreads: a matcher caveat), NEW_STREAMS section 2 (the stream's stated use).

**CH206. The reward start: the `reward_params` stream serves the CLOB's current *and future* reward configurations
every two hours, so a programme scheduled to start on a market is visible before it starts. Farmers arrive within hours
of a start (depth 23x, makers 302 to 639 in the one documented case), the spread inside the band collapses to the
competition's limit, and the mid's quote-noise component shrinks. A per-market natural experiment with an exact,
pre-announced clock; the money is being the first farmer in, and the forecast is the spread and the flat class.**
- Mechanism and why it is non-obvious. CH19 reads the cliff at the *end* of a programme; CH152 reads rate shocks as
  within-market natural experiments (the population of shocks was judged "tens a day" in round 12 and left as a map);
  CH201 reads the yield per posted dollar as a maker-competition forecast. None reads the start, and none had a stream
  that shows a future configuration; the sidecar's `clob_rewards` shows the current one only. A start is the cleanest
  shock in the programme: the venue announces, in a public feed, that from a stated time it will pay for depth in this
  market. The first farmer earns the day's pool with the fewest competitors (the quadratic score divides the pool by
  the quoters' shares); the engine's interest is that the spread, and with it the DELTA-sized quote noise, falls
  predictably. Who pays: nobody directly; the venue pays, and the late farmer earns less. Why the crowd misses it: the
  future configurations are a cursor-paginated endpoint nobody reads.
- Data join and decision clock (`A`, L 3). Unit: market m with a configuration whose `start_date` is after capture k's
  start and within 48 h (read from the last `reward_params` capture received before capture k; its `received_utc` is the
  decision time), x complete capture k from 24 h before the start to 48 h after it (a 36-capture window per start),
  plus matched controls (rewarded markets of the same category and liquidity tier with no configuration change in the
  window, drawn from the same `reward_params` capture). State: `rw_h_to_start` (negative before, positive after; the
  event-time clock), `rw_rate_new`, `rw_max_spread_new`, `rw_sponsored` (the configuration's feed).
- Target and horizon. The **spread** (Gamma best ask minus best bid at the capture, in ticks of the market's own
  `order_price_min_tick_size`) at event time h, and the in-band depth (`book0`'s 1c depths, pre-origin, as the
  secondary); the engine's flat-class rate (|move| <= DELTA) over the 12 captures after the start against the 12 before,
  reported. Hypothesis (one-sided, event study): within market, the mean spread over the 24 h after the start is lower
  than over the 24 h before by at least one tick, net of the matched controls' change.
- Paper rule and economic check. Maker: post the minimum two-sided quote inside the new band at the start minute; the
  first day's reward per dollar posted is the economic quantity (MAKER_REWARDS section 1: a median $0.05-1.00 a day on
  about $19 of capital under *current* competition; the first-day figure is the census's own count of the configured
  daily rate against the in-band depth one capture after the start); the adverse-selection cost is the median 2.38c a
  fill at a 3.1% hourly fill rate. Taker: none (a spread forecast is a cost forecast: trade after the start, not before).
- Population arithmetic. **Unprobed.** The collector counts `markets_native` and `markets_sponsored` per capture (13,661
  rewarded on 10-20) but no count of future configurations exists; new markets probably receive a programme at listing
  (then the start is at creation and CH22's genesis window owns it) and the census must separate starts on markets
  older than 24 h. Planning 30-80 starts a day on existing markets: 630-1,700 starts in 21 days, each a market with 36
  units and a matched control; events: the starts' markets' events, planning 300-800.
- Permutation and cluster structure. The event-time design makes the unit a market-day pair (before, after) with the
  12 captures as repeated measures; strata market x UTC day hold 12 units by construction; the within-market
  before-after contrast is permuted by flipping the event time's sign within market (a declared Freedman-Lane variant
  on the market's own 36-capture window) and by the controls' fake starts. Binding scenarios: LT5 5 and 6 (per-day
  persistence of the spread), a declared **S14: a spread that trends down with market age** (new programmes land on
  young markets; the matched controls and `created_at` as a control bind). Clusters: event; `DE_gate` floor 3.0 (the
  units per event are small).
- Planning MDE. A before-after class contrast per market, SD of the daily mean spread change 2c, `n_eff` 500-1,400
  markets (80% of 630-1,700): `3.47 x 2c x sqrt(2 / 500) x sqrt(3) x 1.5 x sqrt(1.3)` = **1.1c** at the low end, 0.66c at
  the high end; at a quarter 2.2c / 1.3c; against the **1.0c (one tick) spread floor**: borderline at the low end, under
  at the high end. F: the **fake start** (the same window on a matched control with no change) and the **programme end**
  (CH19's cliff, the mirror) are both innovations with `r_w` 0: F-MDE 1.41 x MDE = 1.6c / 0.93c; **F is a verdict
  condition only at the high end**; otherwise a reported label.
- Confounders and the control. Market age (controlled; starts on markets younger than 24 h are excluded from the
  primary and reported); a venue-wide reward re-rating on the same day (a category clock: the share of starts on one
  UTC day is gated <= 30%); a start that coincides with a rate increase on an already-rewarded market (CH152's shock;
  classified separately); Gamma's spread against the CLOB's (the sidecar's best bid and ask are Gamma's; `book0`'s
  `b0_spread` is the CLOB's 110 minutes earlier: both reported); the sponsor's own quoting (a sponsored programme may
  come with the sponsor's depth: `rw_sponsored` splits the arm).
- Cheapest census (counts only; the `reward_params` captures since 10-20T23:20Z and the sealed captures). Future
  configurations per capture; starts a day on markets older than 24 h; the rate and band distribution of new
  programmes; control availability; the spread's within-market SD; the share of starts per UTC day. Kill if starts on
  existing markets < 30 a day, if controls are available for < 70% of starts, or if the one-day share > 30%.
- Challenger feature: **yes.** `rwstart` (`se-aux-rwstart-v1`): `rw_h_to_start` (NaN without a future configuration),
  `rw_started_h` (hours since the latest start, capped at 72), `rw_rate_new`, `rw_max_spread_new`, `rw_sponsored`,
  `rw_sponsor_n`, `rw_daily_total` (the CLOB's computed total: a `rewards` v2 column), from the last `reward_params`
  capture received before the origin. Read against `se1_lgbm_mm` and `se9_lr_rewards` once `rewards` lifts (11-22).
  Embargo: `rewards` to 11-22 (LT5 R's token; the start is a different object but the same programme) and a new token
  `rwstart` to the later of 2027-01-23T00:00Z and LT8's analysis commit.
- Scores: N 4, EV 3, L 3. Parents: CH19 (the reward cliff: the end), CH152 (rate shocks as natural experiments), CH201
  (yield per posted dollar), CH16 and CH45 (reward against adverse selection; geometry), CH183 / LT5 R (the farmer's
  choice of side), CH22 (genesis: excluded here), E025 (provisional; reward-inclusive maker P&L), MAKER_REWARDS section 1
  (the Telonex case and the median yield).

### D. Engine-first ideas (families whose frame, event count or target cannot pass a 21-day census; each states its coverage count, its kill line and its token; none is an LT8 primary)

**CH207. Desk-set dispute insurance: the `gamma_rules` stream stores each market's `umaBond`, `umaReward`,
`customLiveness`, `resolvedBy`, `fallbackResolutionType` and `hasReviewedDates`. The listing desk sets a higher bond or a
longer liveness on the questions it expects to be contested, and leaves dates unreviewed where it is unsure of them;
the crowd does not read these fields. The classes forecast resolution delay, dispute and the decided-side discount, on
`res_7d` and on the last-mid proxy.**
- Why engine-first. The fields are traits (one value per market, rarely edited: 3 changed keys in 25 h), the frame
  covers 44.7% of eligible non-sports markets (CANDIDATES row 17), and the target is a resolution or a pre-resolution
  discount, which only `res_7d` and CH175's proxy read without a window. CH65 (ex-ante dispute predictor) is text-based;
  CH03 and CH47 read the dispute once it exists; CH01 and CH134 read the decided-but-unresolved carry; CH199 (the source
  class) died on the frame's coverage, so this entry states its own: the UMA fields exist on every market Gamma returns,
  so coverage is the frame's 44.7% (parseability is not the limit here).
- State (`A`, L 2 for a test, 3 for the engine). `up_bond_z` (log bond standardised within category), `up_liveness_custom`
  (1 if `customLiveness` is set), `up_reviewed` (`hasReviewedDates`), `up_resolver` (UMA, automated, other: from
  `resolvedBy` and `fallbackResolutionType`, a fixed map declared before any score), joined by market id from the last
  `gamma_rules` row received before the capture (a market outside the frame is NaN; never filled). Decision time: the
  poll's `recv_utc`. Targets: `res_7d` (the calibration gap by class: the decided side's YES rate against its price in
  the last 7 days of life), CH175's last-mid proxy (the pre-resolution discount by class, reported), and the 24 h drift
  in the last 72 h of life (an HTR passive entry in >= $100k markets, reported with the cost model's 0.39c).
- Money route. HTR passive entry on the decided side in markets whose desk-set bond is high and whose dates are
  reviewed (the delay is priced but the outcome is not in doubt); a maker who steps aside in unreviewed-date markets in
  their last week (LT6 D's population: `deadline` token).
- Census (counts only; the stream's day files and the sealed captures). Coverage of eligible non-sports by the frame;
  the share with a non-default bond, with a custom liveness, with unreviewed dates; resolutions a week by class
  (ex-crypto, ex-sports). Kill if the non-default bond share < 5% or if any class has < 300 markets.
- Challenger feature: **yes.** `umaparams` (`se-aux-umaparams-v1`), the four columns above. Embargo: `deadline` to
  12-09 (LT6 D: `hasReviewedDates` is an end-date-risk flag; the column is hidden until then) and no other token.
- Scores: N 3, EV 3, L 2. Parents: CH65, CH03, CH47, CH01, CH134, CH85 (whitelisted proposers), CH199 (killed), CB7-S,
  prior-art honourable mention (UMA dispute and ambiguity premium: "nobody has tested whether ambiguity is priced").

**CH208. The minute of the news: for a Polymarket political market matched to a PredictIt contract (1 min), a Smarkets
contract (5 min) or a Kalshi pair (120 s), the stream's `recv_utc` of the last cross-venue move larger than one cent
before the origin dates the news inside the two-hour interval directly. It is CH194's external timing gate, and CH202's
mirror on a different clock, for the few hundred markets three venues share; plus the dispersion of the three crowds as
an uncertainty state, and settlement elsewhere as a decided-carry label.**
- Why engine-first. The join is tens of events (Kalshi 116 pairs; PredictIt about 200 markets; Smarkets 677 books in
  politics and current affairs; the overlap is **unprobed**, planning 200-400 Polymarket markets in 30-60 events); E026's
  census shows what few clusters do (DE 23.9, MDE 3x the floor); rule 7 binds. The timing columns are nonetheless the
  only direct measurement of news arrival the host has for any market, and the engine scores them on the matched subset
  without a test. The 2026-11-03 midterms fall inside the streams' first weeks: a one-off, disclosed; nothing here is
  election-night-specific (CB15-E owns that).
- State (`A~`, L 3: the matchers are maps first; CH114's PredictIt matcher and E009/E010's Kalshi pair list exist as
  designs). `xt_min_since_move` (minutes between the last cross-venue move >= 1c and the origin; NaN without a match),
  `xt_move_c` (its signed size, mapped to the Polymarket side), `xt_venue` (which venue), `xt_disp` (the range of the
  three venues' fee-adjusted probabilities at the last poll before the origin; PredictIt's 10% profit fee and the
  Smarkets commission applied as declared constants), `xt_settled_elsewhere` (a Smarkets `settled` state or a PredictIt
  contract closed at 0 or 100 while the Polymarket market is open: CH134's label on two new venues). Decision time: the
  latest poll's `recv_utc` before the capture's start.
- Money route. Maker: a Polymarket quote that has not moved while PredictIt and Smarkets did in the last 20 minutes is
  about to be picked off (step aside); taker: the decided-elsewhere carry (CH134's) with the two new venues' settlements
  as the label, held to resolution.
- Census (counts only). Matched markets per venue and in total; events; cross-venue moves >= 1c a day; the share of
  Polymarket movers in the matched set whose last cross-venue move is within 20 minutes of the origin; settlements
  elsewhere a week. Kill (for any test) if matched markets < 150 or events < 60 over 21 days; the engine family is built
  regardless once the `xvenue` embargo lifts (11-04).
- Challenger feature: **yes**, as an extension of `xvenue2` (CANDIDATES row 4): `se-aux-xvenue2-v1` with the five
  columns above. Embargo: `xvenue` to 11-04 (E009/E010; the same hypothesis class) and no new token; the `xt_settled_
  elsewhere` label is a `res_7d` feature only.
- Scores: N 3, EV 2, L 3. Parents: CH194 (withdrawn; the timing question), CH114 (fee-adjusted PredictIt anchor), CH25
  (partisan level gap), CH115 (horizon staleness), CH134 (Kalshi-settlement-labelled decided carry), CH165 / CH166
  (unconfirmed moves and where the liquidity is), E009 / E010, CB15-E.

**CH209. The farmer touch: in a rewarded market the best-level size on a side that equals the programme's minimum
(`bid_size_1 <= 1.05 x rewards_min_size`) is a farmer's quote, posted for the reward and re-posted mechanically when
the mid moves. A farmer touch carries no information about the side it sits on; the displayed spread is the band's,
not the market's; and a taker who crosses it is filled at the minimum and walks. Read from `book0` and the sidecar
before the origin, on every rewarded market, as a maker-protection family and as the control CH203 needs.**
- Why engine-first. The flag is slow within market (a farmer stays for days), so a within-market test would be a level
  test with an expensive F; its value is as a moderator (the imbalance's information content is lower where the touch
  is a farmer's) and as a control, which the engine reads directly. CH116 strips the band's depth from the imbalance;
  CH148 reads size roundness; CH45 the band's geometry; CH183 / LT5 R the farmer's choice of side; none reads the touch's
  ownership from the sweep's best-level size against the sidecar's minimum.
- State (`A`, L 4). `ft_bid`, `ft_ask`, `ft_both` (the flags above, `book0`'s sweep against the sidecar at the same
  pass), `ft_band_share` (the 1c-band depth over the 5c depth as a coarse share of paid depth: the stored sweeps hold band
  sums, not orders, so the exact share is not computable, rule 4 of round 12), `ft_true_spread` (NaN when both touches
  are farmers': the first non-minimum level is not stored, so this is a flag that the displayed spread is the band's,
  not a value). Decision time: capture k's receipt (`book0`'s lag applies).
- Money route. Maker protection: do not read a farmer touch's imbalance as a vote (`se3`/`se19` conditioned on
  `ft_both`); a non-farmer maker posting one tick inside a farmer touch is the only displayed real quote and earns the
  spread the farmers do not want. Taker: expect a minimum-size fill and a walk when crossing a farmer touch (a cost
  rule).
- Census (counts only; LT7's sealed sweeps and sidecars). Farmer-touch share of rewarded books per side; its persistence
  across passes; its correlation with `rw_in_band`; the share of all eligible books that are rewarded with a farmer
  touch (the population the moderator covers). Kill (as a family) if the share is < 5% or > 95% of rewarded books.
- Challenger feature: **yes.** `farmer` (`se-aux-farmer-v1`), the five columns above. Embargo: `rewards` to 11-22 and
  `book0` to 12-31 (both sources), a new token `farmer` to the later of 12-31 and LT8's date (CH203 uses it as a
  control).
- Scores: N 3, EV 2, L 4. Parents: CH116, CH148, CH45, CH71, CH183 / LT5 R, CH201, CH131 (quoter grain), MAKER_REWARDS
  section 1 (the minimum two-sided quote's yield).

**CH210. Two minutes before the origin: CH200 read the two sweeps of pass k against an origin-k label and was declined
because the second sweep is inside the label window. The two sweeps of pass k - 1 are both about 110 minutes before
origin k (the second is `book0`'s own); their difference is the most recent two minutes of book dynamics the host
observed before the forecast: the touch, the first-cent sizes and the level counts changing in 10% of books a pass.**
- Why engine-first. A two-minute book change read 110 minutes later is weak by construction; whether it adds to
  `book0`'s level on `dir_2h` is a leaderboard question, not a test; nothing sealed reads sweep 2 at all.
- State (`A`, L 4). `s20_dmid`, `s20_dimb1c`, `s20_changed`, `s20_levels_delta`, from pass k - 1's two sweeps (both
  finished before capture k started, the `book0` rule). Decision time: capture k's receipt.
- Challenger feature: **yes.** `sweep2_0` (`se-aux-sweep2_0-v1`), read against `se19_lr_book0`. Embargo: `book0` to 12-31.
- Scores: N 2, EV 2, L 4. Parents: CH200 (declined; here pre-origin), CH147 (the breathing book), CH178, E003.

**CH211. The ladder that travelled: between the pre-origin sweeps of passes k - 2 and k - 1 the sweep mid moved at
least a cent. If the 5c band sums and the level counts on both sides are nearly unchanged while the mid moved, the
whole resting ladder was re-posted around the new mid: a program re-quote, the book's own version of E015's quoted
parallel class. If the hit side lost depth and levels while the far side kept them, real orders were consumed or
cancelled: a human book. The travel share is a per-move footprint of who quotes this market, read from the book, before
the origin.**
- Why engine-first. It is a book-side reading of E015's anatomy (a moderator of a registered test's classes until E015's
  analysis commit, 11-15; the `movetype` token runs to 12-31), and CB18-P (CH172, program against human by the flow's
  reaction) was dropped at census. As an engine family it is a cheap footprint; as a test it would wait for E015 and be
  informed by it.
- State (`A`, L 4). `rq_travel = 1 - |D5_hit,k-1 - D5_hit,k-2| / D5_hit,k-2` clipped to [0, 1], `rq_levels_kept` (the
  level counts' ratio on the hit side), `rq_far_kept` (the same on the far side), `rq_program = 1[rq_travel >= 0.8 and
  rq_levels_kept >= 0.8]`, on the outcome-0 token's pre-origin pass sweeps. Decision time: capture k's receipt.
- Money route. Maker protection: do not post against a program re-quote (its move is a re-centering that a taker has not
  tested; E015 measures whether it reverts); against a human book's move, the consumed side's refill (V's object) is the
  vote.
- Challenger feature: **yes.** `requote` (`se-aux-requote-v1`). Embargo: `movetype` and `book0` to 12-31 (E015's classes;
  the sweep source), and `vote` to 12-09 (LT6 V reads the post-move refill).
- Scores: N 3, EV 2, L 4. Parents: CH172 / CB18-P (dropped), CH131 (quoter grain), CH147, E015 / CH156 (quoted against
  traded moves), CH190 / LT6 V (the makers' vote), CH169.

---

## 3. Ranked top 5 for LT8, then the rest

Rank = census survival (population recurrence, strata share, effective count, **and the F-MDE under its cap**) x
originality x plausibility x money route, with the rules of section 0.1 as hard constraints. Every LT8 candidate has a
state defined on the capture, sweep and sidecar panel or on a daily-renewed frame, read strictly before the origin, a
within-market contrast or slope with the Freedman-Lane gate, a falsification arm whose planning `r_w` is near zero
(innovations and direct clocks), a counts-only census on files LT5 and LT7 already sealed (or on stream day files that
exist), a planning MDE under 0.5c at the planning count, and a reader that extends an existing LT reader (E015's for
capture states, V's and CH195's for sweep states) by a few columns. The last column is my prior probability that the
idea passes its own census as written, before any count; it is a judgement, not a measurement.

| Rank | ID | One line | L | Population arithmetic (source) | Permutation structure | Primary | Planning MDE (quarter); F | Prior odds of surviving census |
|---|---|---|---|---|---|---|---|---|
| 1 | CH203 | The quiet book: the 5c-imbalance innovation behind an unmoved touch, two pre-origin sweeps | 5 | about 21,000 quiet non-sports books a capture (28,000 with `book0` x 0.75; DESIGN_V1 sections 3, 21, 22); 5.3M in 21 days; events in the tens of thousands (J4-R) | continuous state on the whole panel; market x day holds 12 units by construction; FL with LT5 7-8 on the level and V's depletion world | within market, slope of `c2` on `zdimb5`, the level fixed | 0.16c (0.33c); **F verdict** 0.23c (0.46c) | 0.35 (the whole-panel DE and the within-market SD gate are the risks) |
| 2 | CH202 | Seven minutes or two hours: the sweep clock's held-against-fresh split of the previous move | 5 | 30,000-33,000 non-sports movers a day with the k - 1 sweep (P1b x 12 x 0.93); 480,000-520,000 ex-crypto in 21 days; events >= 2,539 per two days (E022) | per-interval label; market x day, else block2 (E022's 0.446 / 0.599 floor); FL with LT5 1-4 | within market, held minus fresh on `c_skip` | 0.26c (0.52c); F reported label | 0.30 (a mover population at E022's floor; the stale-row share and the `b0_gap` disclosure are the design risks) |
| 3 | CH204 | The market's own clock: hot-slot against cold-slot |move| in scheduled markets | 4 | 2,300-4,600 scheduled markets (10-20% of 23,000 with 7 days of own slots, unprobed); 48,000-97,000 hot units in 21 days; events 500-1,500 (unprobed) | per-interval label rotating within market-day; 12 units by construction; FL with S12 (clustering, no seasonality) | within scheduled markets, hot minus cold on `a` | 0.60c / 0.43c (1.2c / 0.85c); F reported label unless 2x the high end | 0.20 (borderline MDE by construction; the category-share and venue-clock gates can kill it) |
| 4 | CH205 | Steam at the book: the sportsbook's line move against Polymarket's unmoved pre-game price (sports parameter; 42-day window) | 3 | about 45 matched games a day (76 with odds x 0.6, unprobed), 400-800 units a day; 950 games in 21 days, 1,900 in 42 | continuous state; market x day up to 12 units; FL with S13 (lagged level); DE at the floor | within game market, slope of `c2` on `z steam`, the level gap and own change fixed | 0.81c / 0.57c at 21 days, 0.57c / 0.40c at 42 (quarter 1.1c-1.6c); F reported label | 0.25 conditional on sports being in scope and a matcher precision >= 0.9; 0 otherwise |
| 5 | CH206 | The reward start: future reward configurations as a per-market natural experiment on the spread | 3 | 30-80 starts a day on markets older than 24 h (unprobed); 630-1,700 in 21 days; events 300-800 | event-time before-after per market; 12 units per market-day; sign-flip FL within market and the controls' fake starts | within market, the 24 h mean spread after minus before, net of controls | 1.1c / 0.66c against the 1.0c tick floor (2.2c / 1.3c); F verdict only at the high end | 0.10 (the count of starts is the whole question; a map first) |
| 6 | CH209 | The farmer touch (engine-first; CH203's control) | 4 | about 12,700 rewarded books with `book0` a capture, all categories (13,661 x 0.93) | slow trait; not a test | `dir_2h` against `se19`; moderator of the book families | engine window | n/a (family census: share in [5%, 95%]) |
| 7 | CH207 | Desk-set dispute insurance from `gamma_rules` (engine-first) | 2 | about 8,150 eligible non-sports in the frame (44.7% of 18,232); class shares unprobed | trait | `res_7d` calibration gap by class; last-mid proxy | engine window | n/a (kill if non-default bond < 5% or a class < 300) |
| 8 | CH211 | The ladder that travelled (engine-first; after E015's analysis for any test) | 4 | 4,800-5,600 pre-origin sweep movers a capture (17-20% of 28,000) | per-move footprint | `dir_2h` against `se19`; a moderator of E015's classes after 11-15 | engine window | n/a |
| 9 | CH208 | The minute of the news on three political venues (engine-first `xvenue2`; maps first) | 3 | 200-400 matched markets in 30-60 events (unprobed; Kalshi 116 pairs, PredictIt about 200 markets, Smarkets 677 books) | few events | `dir_2h` timing columns; `res_7d` settled-elsewhere label | engine window | 0.05 as any test (rule 7); the family is built regardless |
| 10 | CH210 | Two minutes before the origin (engine-first; CH200 made honest) | 4 | about 6,500 books a pass whose two sweeps differ (CH147) | per-pass | `dir_2h` against `se19` | engine window | n/a |

CH203 is first because it is the one state in the programme whose falsification arm is affordable by construction (an
innovation's far-future twin is independent), its population is the whole panel minus movers (so the strata gate is met
by construction and E020's recurrence death does not apply), and its reader is `book0`'s construction read twice. CH202
is second because it is the direct-clock answer to a question the challenger explicitly invited and reads two receipts
the host already stamped, at the cost of a mover population and a disclosed half. CH204 is third on originality (a
per-market schedule nobody has read; a magnitude primary with an unambiguous sign) and borderline on power by its own
arithmetic. CH205 is the strongest census profile among the stream ideas (a frame that renews daily, DE at the floor)
and is entirely the owner's scope call; CH206 is the cleanest natural experiment the new streams offer and needs its
first count before anything else. If the LT8 designer wants k = 3 with the strongest money routes, CH203, CH202 and
CH204 are the three; CH205 is added if and only if sports is in; CH206 is a map whose result decides.

**Pre-registration sketches for the top 5 (LT8 candidates; each a separate primary in one Holm family; written in
LT7's shape so the designer can lift them).**

- **CH203 (the quiet book).** Unit: non-sports ex-crypto eligible market x capture, pass sweeps k - 2 and k - 1 both
  finished before capture k started, both two-sided, |swmid_{k-1} - swmid_{k-2}| < 0.5c and |mid_k - swmid_{k-1}| < 0.5c.
  State: `zdimb5`. Decision time: capture k's receipt. Primary: expanding-past market-demeaned OLS of `c2 = mid_{k+1} -
  mid_k` on `zdimb5` with `imb5_{k-1}`, `log1p D5`, `b0_spread`, `b0_lag_s`, logit mid, |mid - 0.5|, `log1p volume24hr`,
  the (k - 2, k - 1] volume change, own 24 h change, `rv24`, tick stratum, `rewarded`, `rw_in_band`, `ft_both` as
  controls; one-sided > 0; material reading top-against-bottom tercile. Targets: `c2`; M1 `y6`; 24 h. Clustering: LT4
  L10 with the <= 10-member cap on the primary (larger ladders reported). Planning MDE 0.16c (DE 51), F-MDE 0.23c.
  Census (LT7's sealed pass sweeps, 22 consecutive pairs): quiet share; within-market SD of `dimb5` >= 0.05 in >= 50% of
  markets with >= 6 units; VIF(zdimb5 | imb5) <= 2; |corr(zdimb5, log liquidity)| <= 0.5 within and pooled; `r_w` (lead,
  lag innovations; sizes only) <= 0.3; permutable share >= 50%; pessimistic MDE <= 0.5c; F-MDE <= 0.5c. Verdict condition:
  F (the far-future innovation) by LT7's rule; the fake split (`dimb1`) a reported label. Cost hurdle: maker gross, no
  fills; taker not shown. Extends: V's reader (one more sweep per capture). Embargo: `book0`, `book` to 12-31; `quietbook`
  to the later of 2027-01-23 and LT8's date.
- **CH202 (seven minutes or two hours).** Unit: non-sports ex-crypto 2 h mover at k - 1 (|x| >= 1c and >= 2 ticks) with
  pass k - 1's sweep 1 two-sided and capture k present. State: `early_share`; held >= 0.75, fresh <= 0.25. Decision time:
  capture k's receipt. Primary: expanding-past market-demeaned OLS of `c_skip` on 1[held] over held and fresh units with
  anatomy, `log |x|`, spreads at k and at the k - 1 sweep, logit mid, |mid - 0.5|, `log1p volume24hr`, own 24 h change,
  `rv24`, tick stratum, `b0_lag_s` as controls; one-sided > 0. Targets: `c_skip`; M2 `c1` (disclosed as `b0_gap`'s
  object); M1 the whole-panel slope difference; 24 h. Clustering: LT6 V's; `DE_gate` E022's 6.196. Planning MDE 0.26c.
  Census (LT5's sealed captures with LT7's sealed sweeps for the k - 1 sweep): movers with a k - 1 sweep >= 1,500 a
  capture; held and fresh >= 15% each; |corr(1[held], 1[parallel])| <= 0.5 within; liquidity gate; crypto share;
  permutable share >= 50%; pessimistic MDE <= 0.5c; the stale-row share printed. Verdict condition: none beyond Holm (F a
  reported label: the far-future split where defined). Extends: E015's reader (one sweep mid at k - 1). Embargo: `book0`
  to 12-31; `swclock` to the later of 2027-01-23 and LT8's date. Disclosure at the pin: DESIGN_V1 section 22's `b0_gap`
  diagnostic and se18's visible broad score.
- **CH204 (the market's own clock).** Unit: non-sports ex-crypto eligible market x capture with >= 70 of 84 own slots;
  scheduled class by the declared rule. State: `sc_hot`. Decision time: capture k's receipt. Primary: expanding-past
  market-demeaned OLS of `a = |mid_{k+1} - mid_k|` on `sc_hot` over scheduled markets with `rv24`, `rv7d`, spread, logit
  mid, |mid - 0.5|, `log1p volume24hr`, hours to end and the weekly anatomy share as controls; one-sided > 0.5c (the
  magnitude floor as the null's boundary). Secondaries: the spread at the hot slot; the signed `c_skip` of hot-slot
  moves (sign undeclared, reported). Clustering: LT4 L10 with the member cap. Planning MDE 0.43-0.60c. Census (LT5's
  sealed captures, seven own days for 10-19 .. 10-21): scheduled share; category shares (<= 50% any one); hot-slot
  distribution (<= 50% mass in one slot); `n_eff`; S12 size; pessimistic MDE <= 0.5c. Verdict condition: F (the rotated
  schedule) if its census F-MDE <= 0.5c, else a reported label; the out-of-window schedule reported. Extends: E015's
  reader (the engine's `quotes/` window of 84 slots per market, streamed). Embargo: `surprise` to 11-19; `sched` to the
  later of 2027-01-23 and LT8's date.
- **CH205 (steam at the book; sports parameter; 42 days).** Unit: matched ESPN game x pre-game capture. State: `z steam`
  from the last ESPN poll received before the capture. Decision time: the later of that poll's `recv_utc` and the row's
  receipt. Primary: expanding-past game-demeaned OLS of `c2` on `z steam` with the level gap, Polymarket's own (k - 1, k]
  change, hours to kick-off, spread, logit mid, `log1p volume24hr` and league as controls; one-sided > 0. Clustering: by
  game, CR1 and the event t on `G - 1`; `DE_gate` 3.0. Planning MDE 0.57c at 42 days (the designer may decline it on that
  alone). Census (the stream's day files since the install and the sealed captures): matched games a day >= 30; audited
  precision >= 0.9; |steam| >= 0.5 pp in >= 20% of units; permutable share >= 50%; pessimistic MDE <= 0.5c at the 42-day
  projection (else dropped). Verdict condition: none beyond Holm (F, the far-future steam, a reported label; the level
  gap's slope reported as CH29's arm). Cost: the taker route at 5.2c is reported and expected not to clear. Extends: a new
  light reader on `stream_espn_odds/` plus the matcher artefact (< 100 MB). Embargo: `steam` to the later of 2027-02-13
  and LT8's date. Registered only if the owner has set sports in by the pin date.
- **CH206 (the reward start; map first).** Unit: a reward start on a market older than 24 h x the 36 captures around it,
  with a matched control. State: event time. Decision time: the `reward_params` capture's receipt. Primary: the within-
  market after-minus-before 24 h mean spread (in ticks), net of the control's, one-sided < -1 tick. Clustering: event;
  `DE_gate` 3.0. Planning MDE 0.66-1.1c against the 1.0c floor. Census (the `reward_params` captures since 10-20): starts
  a day >= 30 on existing markets; controls for >= 70%; the one-day share <= 30%. Verdict condition: F (the fake start on
  the control, the programme end as the mirror) if F-MDE <= 1.0c, else reported. Extends: a light reader on
  `reward_params/` and the captures' sidecar (< 100 MB). Embargo: `rewards` to 11-22; `rwstart` to the later of
  2027-01-23 and LT8's date.

**How the families would be registered.**
- **A. Direct clocks (CH202, CH204).** Both counted if their censuses pass, on E015's reader; the `swclock` and `sched`
  families go to the engine as challengers at once, under their tokens.
- **B. The quiet book (CH203).** Counted; origins start after LT7's `END_UTC`; pinned before `T_LT6` and `T_LT7`; the
  `quietbook` family and the `farmer` control go to the engine under `book0`.
- **C. The new streams (CH205, CH206).** CH205 counted only with sports in scope and a 42-day window, else "not proposed
  (scope)"; CH206 a map whose first count decides whether it is a sixth test or an engine family.
- **D. Engine-first (CH207-CH211).** Challenger families with the tokens named; CH207 and CH208 need a coverage census
  on their streams first; CH209 is built first because CH203 uses it as a control.

**What is honest to say about all of them.** Round 12's six were levels on the whole panel, and the design that
followed them found that a level's falsification arm costs more than its test. Round 13's five are innovations and
direct clocks: the change of the book behind an unmoved touch, the part of a move the CLOB had already made when the
host's own sweep arrived, the slot at which this market and no other has moved all week, the line that moved at the
book, the programme that is scheduled to start. Each has a falsification arm whose twin is independent by
construction, each is read strictly before the origin from files the host already writes, and each states the count
that will kill it. The new streams, read honestly, give one strong census profile (a daily-renewed sports frame the
owner may not want), one clean natural experiment whose population nobody has counted, and three families of traits
and timings that the engine can read and no 21-day test can. Nothing here is edge until it has gone through census,
frozen rules, prospective registration and an economic check at recorded prices; the engine's leaderboard, not this
file, is where any of it would first show.

---

## 4. Ideas considered and rejected, and why

- **Any trade-sample unit as an LT8 primary.** E021's strata share 0.005 / 0.018 is the measured fate of the rotating
  sample; LT5 J and O and LT6 K carry the risk and are drafted. Not proposed.
- **Any sweep-1-of-pass-k state against an origin-k target** (the round-12 book states as written, CH200, the touch
  size at k, `bk_age_s`). DESIGN_V1 section 21: inside the label window; se7, se3 and se14 promotion-ineligible. Every
  sweep state here is `book0`'s construction or later-starting.
- **Level states with a far-future falsification arm** (depth levels, spread levels, imbalance levels, `ivr`). LT7's
  planning: F-MDE 0.66-0.75c for CH195 and CH197. Levels enter here only as controls; CH203 is the innovation form of
  CH197's object.
- **`chg_1h` timing states (CH194 redesigns on the venue's field).** R1: no gate can test the field's timing; informed by
  E002/E004. CH202 uses the host's own receipts; CH208 the streams' `recv_utc`.
- **Rule-text edits as events (CH08, CH177, CH63, CH64), even with `gamma_rules` dating them.** 3 changed keys in 25 h
  in the top-3,000 frame; CB18-S dropped. CH207 reads the static UMA fields of the same stream, not edits.
- **The resolution-source class (CH199) and any other `gamma_rules` field on the whole panel.** Killed at census on the
  frame's 44.7% coverage; CH207 states the same coverage and is engine-first for that reason.
- **PredictIt, Smarkets and Kalshi price gaps or leads as LT8 primaries** (CH114, CH25, CH115, CH165, CH166, E009/E010's
  class). Tens of events (CB15-P's 37 pairs in 12 events; E026's DE 23.9 on 650 events); rule 7. CH208 is engine-first
  and reads timing and settlement, not gaps.
- **The three-crowd dispersion as a volatility test.** The same population; a column in CH208.
- **ESPN in-play states against the trade monitor's prints** (score-lag prints, CH23's hope premium at 10-minute
  resolution). Monitor units (strata) and sports scope; not proposed. CH205 is pre-game only.
- **Spread or displayed-liquidity withdrawal with no trade as a volatility forecast** (Gamma `liquidity` innovations,
  spread innovations). Rejected in rounds 11 and 12 as textbook ("both makers step back before news"); CH203 is the
  signed, per-side, depth form with a different mechanism and a maker route; the unsigned form is not proposed.
- **Volume that arrived after the move (the late crowd), the laggard catch-up, the volume24hr roll-off as yesterday's
  echo.** Ambiguous signs, E015 and CH193 adjacency, `participation` and `event` tokens. Not proposed.
- **Sponsored against native rewards as a stand-alone test.** A slow trait; columns of CH206's family (`rw_sponsored`,
  `rw_sponsor_n`).
- **The reward epoch, the UTC day boundary, weekends, holidays and any other venue clock.** Rule 8; CH204 is per market
  and carries a venue-clock kill line.
- **The venue's displayed 1 h / 1 d changes and front-page rank as retail triggers.** CH37, CH176; not proposed.
- **Wallet features, skilled-wallet toxicity, copy rules, holder snapshots.** E026 registered and frozen to 12-07; WS1
  P2-P4 null; CB8-H sealed. Not proposed.
- **Maker mark-out objects** (adverse selection by state judged on fills). J4-R's and CB13-T's holdouts refuse the worn
  days; E025 part B owns signal-conditional fills; every maker route here is gross, no fills.
- **E015, E022, LT5, LT6 and LT7 moderators during their windows.** Double counts on overlapping origins. CH211 is
  declared an E015 moderator and is engine-first until 11-15; CH203's adjacency to V and CH197 is disclosed and its
  origins start after LT7's `END_UTC`.
- **Resolution-level LT8 primaries** (calibration by UMA class, decided carry by venue settlement). Only crypto and
  sports resolve in the thousands in 21 days; CH207 and CH208 are engine-first on `res_7d` for that reason.
- **Taker routes as primaries anywhere.** The cost model's 2.9-7.2c hurdles (5.2c in sports) against grosses of a
  fraction of a cent; every taker route here is reported, never a verdict.
- **The `b0_gap` reversal as a test.** Seen in DESIGN_V1 section 22's diagnostic (2026-10-22); the engine holds it; a
  test of it now would be informed by construction. CH202 discloses it as M2 and tests the contrast instead.
- **UMA proposal and dispute objects, holding rewards, tick regimes, reward cliffs, series base rates and rolls,
  genesis and first-day prints, seed anchors, mention baskets, external anchors and clocks, barrier confusion, quoter
  grain, wake-up prints, book age, breathing book, mint share, turnover, synchronous prints, exit pressure, cost and
  lag maps, quoted against traded moves, walked flow, trains, attention surges, breadth, class-conditioned longshots,
  arrivals and cancellations, age of the move, opens and closes, concentration, hollow liquidity, program against
  human, last-mid proxy, front page, silent edits, races, jump or grind, high-water mark, overhang, alone or with the
  crowd, the farmer's choice, clips, the makers' vote, deadline moves, sibling birth, provenance, overdue, grind at the
  capture clock, the hour-held move, implied against realised, absorbed flow, resistance, patient money, the last-print
  anchor, calendar theta, the resolution-source class, two minutes of quote news, reward yield.** CH01-CH201: not
  re-proposed; where an idea touches one, the parent is named and the new clock, population, state or join is stated
  (CH202 on CH194/E004/E021/E015; CH203 on CH197/CH190/CH169/CH133/CH147/CH116; CH204 on CH57/CH33/CH28/CH18 and round
  11's own-hours rejection; CH205 on CH29/CH14; CH206 on CH19/CH152/CH201/CH16/CH45; CH207 on CH65/CH03/CH47/CH01/CH134/
  CH199; CH208 on CH194/CH114/CH25/CH115/CH134/CH165/CH166; CH209 on CH116/CH148/CH45/CH183/CH201; CH210 on CH200/CH147/
  CH178; CH211 on CH172/CH131/CH147/CH156/CH190).

---

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
The ledger's entries from 2026-10-21 ~18:55Z to 10-22 ~05:30Z (LT4 censuses q0482/q0483 and the E022 freeze; CB13-R,
CB14-W, CB15-P, CB18 routing; SB2-J4-R VOID; E026 registration; LT5 seal q0564 and q0561's first attempt; LT6 R1, re-check
and freeze checks; LT7 R1, re-check and design-text freeze; the signal engine's se15-se19, the book timing overlap, the
CH199 census, the CH200 decline, `book0`; the host resize deviation with the streams' last and first polls);
`LIVE_TESTS_7.md` sections 0, 1.0, 6.1-6.3 and 7 (the planning at DE 6.196, the F-MDE cap, the lag-slot loader, the seals
and gates); `signal_engine/DESIGN_V1.md` sections 3, 8, 16 (as round 12 quoted it), 21 and 22; `signal_engine/CANDIDATES.md`
(the four embargo request rounds, rows 1-19 of the builder status, the round-12 idea-level list); `NEW_STREAMS_2026-10-19.md`
sections 1-5; the stream modules' docstrings (`streams/predictit.py`, `smarkets.py`, `espn_odds.py`, `gamma_rules.py`)
and `reward_params_collector.py`'s docstring (fields and counts only); `data_catalogue/README.md` ("Prospective streams");
`COLLECTION_HOST.md` and `scripts/oracle/crontab.txt` / `streams_crontab.txt` (the installed jobs; the streams' lines still
commented in the repo); `MAKER_REWARDS_STUDY.md` section 1; `PRIOR_ART_2026-10-19.md` section 1 (the top-10 gaps);
`LIVE_TRADE_MONITOR.md` (fields); `AREPO_V2_CHECKPOINT.md` (live section and queue order, 10-22) and
`AREPO_PROGRESS_PLAIN_ENGLISH.md` (10-22 06:26 UTC+1); `CREATIVE_HYPOTHESES_2026-10-26.md` (round 12: header, sections 0,
0.1, 1, 2 lead entries, 3, 4, 5) and `-25.md` (round 11: sections 3 and 4); the lead sentences of CH01-CH201 from all
twelve rounds. The cost-model, maker-rewards and round-9 probe figures are quoted as rounds 11 and 12 quoted them.

### 5.2 External literature (named, not fetched)
Glosten and Milgrom 1985 (the maker's quote update); Easley and O'Hara 1992 (time and the process of price adjustment);
Chae 2005 (trading volume, information asymmetry and timing information around scheduled announcements); Hong and Stein
1999 (gradual diffusion); Kaniel and Liu 2006 (informed traders' choice of limit orders when information is long-lived);
Rosu 2009 (patient traders in limit-order markets); Cao, Hansch and Wang 2009 (the book beyond the touch); Cont, Kukanov
and Stoikov 2014 (order-flow imbalance and price changes); Foucault, Kadan and Kandel 2005 (limit-order book dynamics and
the cost of immediacy; section C only); Kaunitz, Zhou and Kreiner 2017 (closing-line value, 479k games); Levitt 2004
(why bookmakers move lines); the Telonex reward case study and Bartlett and O'Hara 2026 as `PRIOR_ART_2026-10-19.md` and
`MAKER_REWARDS_STUDY.md` cite them (section 1 and gap 6 only).
