# Creative hypotheses, round 15: the keyless streams, the fine clock and the capture clock (2026-10-29)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-23 02:30-04:00Z on parent
`66bbc2fd` (`chore/arepo-claude-setup`) in the worktree `feat/creative-r15`; the file carries the round's planned date as
earlier rounds did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59),
round 3 `-17.md` (CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130),
round 7 `-21.md` (CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md`
(CH169-CH179), round 11 `-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201), round 13 `-27.md` (CH202-CH211), round 14
`-28.md` (CH212-CH221); this file starts at **CH222** and repeats none of them. Where an idea builds on an earlier one, the
parent is named and the new mechanism, clock, population or join is stated. Every number quoted from an AREPO document is
a development, census or probe result, not evidence. One file; no code, no queue specs, no other commits. **No network
request, no host probe (no `ssh oracle`) and no `data-dumps` read were used for this round** (by instruction); every count
below is taken from a named AREPO document (`NEW_STREAMS_2026-10-19.md` sections 1-4, `COLLECTION_HOST.md`,
`CROSS_VENUE_LIVE.md`, the ledger's E009 entry and its 2026-10-22 and 10-23 tail, `signal_engine/STATUS.md` (10-23
00:25 UTC+1), `signal_engine/CANDIDATES.md` rows 3, 4, 17 and round 6, `signal_engine/DESIGN_V1.md` section 3,
`LIVE_TESTS_9.md` section 0, `CREATIVE_BATCH_13.md` H6-H8, `EXECUTION_COSTS.md` and `COST_MODEL.md` (sports rows), the
four stream modules' docstrings (`streams/predictit.py`, `smarkets.py`, `espn_odds.py`, `gamma_rules.py`),
`cross_venue_live.py`'s Kalshi fields, and round 14's structural facts where unchanged) and is named as such. Where no
count exists the entry is marked **unprobed** and the pre-registration census is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities 2026-10-19 and 10-21; orchestrator brief for round 15).** Original
hypotheses about how money could be made now lead the programme, but every recent live-test batch has died at its
pre-registration census (round 14's section 0.1 tabulates the drop reasons; its five patterns and the eleven design rules
of its section 0.2 **bind here unchanged** and are restated only where this round adds to them). The brief for this
round: original mechanisms that survive the census, with the emphasis on the streams the host has collected since
2026-10-19/22 and has used least: **PredictIt** (whole open universe, 1 min), **Smarkets** (politics and current
affairs, top-3 levels and last executed prices, 5 min), **ESPN's sportsbook lines** (12 leagues, open and current
moneyline / spread / total, 10 min), **`gamma_rules`** (rule text of the top 3,000 by 24 h volume hourly, the full
volume frame 6-hourly) and the CLOB's **`reward_params`** feed (every 2 h); cross-venue joins and clocks (who moves
first, the stale venue against the fresh one, rules-text changes); and families the signal engine can take now.
Category-agnostic, sports as a parameter (the owner's call). No data-rights topic is raised.

**What changed since round 14 (from the ledger's 10-22 ~17:45Z to 10-23 ~01:30Z entries, `signal_engine/STATUS.md`,
`CANDIDATES.md` round 6, `LIVE_TESTS_9.md` section 0).**
- **LT9 is DRAFTED on round 14's top four** (CH213 the band break, CH214 the pool splits, CH212 the display's omission,
  CH215 the scheduled end as an optional fourth): challenger R1 = REVISE, the R1-revised draft awaits its re-check;
  design-text freeze before the earlier of 2026-11-14T12:00Z and `T_E015`; proposed window 2027-01-21..02-11; nothing
  counted. Its tokens are applied: `bandbreak`, `pool`, `rwblink` to 2027-02-14; `book` / `book0` moved to 2027-02-14
  (back to 01-23 if CH214 drops); `rwend` held for CH215's census. **CH213's binding F-MDE fails at both planning ends**
  (2.24c / 1.005c against 1.0c), so LT9's own author now expects it to need >= about 154 strict reward-panel breaks a
  capture (LT9 section 0). Nothing here reads LT9's objects.
- **LT7 CLOSED at census with no test** (STATUS 10-23): its five tokens (`resist`, `capath`, `deepbook`, `absorbed`,
  `ivr`) withdrawn effective 10-23T00:00Z; `movetype` back to 11-22. LT5, LT6, LT7 are now three families with zero
  registered tests; LT4 registered one (E022).
- **The engine built two round-14 engine-first families** (`dispgap` CH218 as `se22_lgbm_dispgap`, `dormant` CH220 as
  `se23_lgbm_dormant`; both hidden to 11-14 / 11-19; both passed their counts-only censuses: |dg_1d| >= 2 ticks on 4.72% of
  rows against a 2% kill line; `dm_still == 12` on 10.37% of non-sports rows against 3-60%). K = 7 now, 8 with se21, 10
  by 11-19. The engine's open list (STATUS next-actions 7): `rowq` (CH217), `bookclock` (CH219), `umaparams` (CH207),
  `theta` (CH198). The builder asks for families with a real prior only, since each raises K.
- **The four keyless streams are installed and polling** (the resize record of 10-22 03:xxZ lists each stream's last
  poll before and first after the restart: PredictIt 1 min, Smarkets 5 min, ESPN 10 min, `gamma_rules` hourly). **No
  registered experiment reads them**; the earliest window for any test on them starts at their install (the data before
  does not exist: `NEW_STREAMS` section 5). The host is 2 OCPU / 12 GB.
- E022 (LT4) and E026 are registered; E009/E010's `cross_venue_live/` stays sealed to 2026-11-03 (E009 analysis after
  11-03T02:00Z, E010 after 11-03T08:00Z); E011's `surprise_live/` to 11-10.

### 0.1 The frame arithmetic: why cross-venue ideas die at the capture clock and where they can live

Round 14's rule 6 (and round 13's rule 7) sent every PredictIt, Smarkets and Kalshi idea to the engine, on the record of
CB15-P (37 pairs in 12 events against >= 60 in 30), CH208's planning (200-400 matched markets in 30-60 events, unprobed)
and E026's design effect (23.9). This round makes the arithmetic explicit, because it decides where the brief's
cross-venue clocks can be tested at all. Under round 14's planning formula (stated in full below), a class contrast on a
2 h target (SD 4c) at the whole-panel design effect of 31 needs about **140,000 units per class** to reach a 0.5c MDE,
and a slope needs `n_eff` of about **21,000** on a spread target (SD 2c, floor 1.0c) or about **210,000** on a mid target.
A matched pair contributes 12 units a day at the capture clock, **252 in 21 days**; so a capture-clock cross-venue test
needs **>= 1,100 pairs** for a class contrast and >= 800 for a mid slope. The three venues together offer at most a few
hundred (fact 7 below). **At the capture clock, every cross-venue idea is engine-first by arithmetic, not by taste.**

The same pair contributes **144 origins a day at the 10-minute grid**, 3,024 in 21 days, and the 20-minute target's SD is
a fraction of the 2 h target's (E009's object; its SD is **unprobed** here, planning 0.5-1.0c). At that clock 70-116
pairs give 200,000-350,000 origins, and the arithmetic passes the same gates by one to two orders of magnitude (the
entries below show it). The host already captures exactly one fine-clock panel with Polymarket on it: **E009/E010's
poller** (Polymarket CLOB `/books` and Kalshi `/markets?tickers=` every 120 s for up to 200 matched pairs, receipt-timed,
with Kalshi's `last_price`, `yes_bid`, `yes_ask` and both sizes stored per line: `cross_venue_live.py`), which is a
registered experiment's stream until 2026-11-03 and, after its analyses, a supervised monitor with no stated end date
(`COLLECTION_HOST.md` lists it under `supervise.sh`; whether it keeps polling after 11-03 is **unprobed** and is the
first dependency of family A). PredictIt (1 min) and Smarkets (5 min) are fine clocks on the *other* side only: the host
polls no Polymarket book for their matched markets, so their fine-clock use needs the poller's pair list extended (a
pair-list change to an existing collector, after E010's analysis, an owner decision: CH230), and until then they are
engine columns at the capture clock (CH229) and twins reported uncounted.

So the round has three lanes, each named in every entry:
1. **The fine-clock lane (family A).** Tests on E009's stream after its analyses, strata pair x UTC day with 144 units by
   construction, Freedman-Lane within them, CR1 on Polymarket event, the planning formula at DE 51 (events are uncapped
   there), labelled `informed (E009)` because E009's results will be known at registration; the design text is frozen
   before E009's earliest analysis time (2026-11-03T02:00Z) so the states are chosen blind. This is the only lane in which
   "who moves first" and "the stale venue" can be tested with data the host already captures.
2. **The sports arm (family B).** ESPN's board plus Polymarket's game markets is the one keyless-stream join that is
   complete and dense by construction (every game the board carries, every pre-game capture, clusters of one game); it is
   a test only if the owner puts sports in, and the non-sports twins of its ideas are reported uncounted. CH205 (steam)
   owns the line's move against Polymarket's unmoved price; the two ideas here read different objects (the sibling that
   lags, the price-free decided clock).
3. **The capture clock (families C and D).** Engine-first families on the three politics venues and `gamma_rules`, each
   with its coverage stated and a token named, and one map that would turn the fine-clock lane into a three-venue panel.

### 0.2 Design rules (round 14's 1-11 bind unchanged; three additions for the fine clock)

12. **Fine-clock units.** A unit is a pair x 10-minute grid origin `t` (E009's grid) with a valid two-sided Polymarket
    book and a valid Kalshi quote received before `t`; the state reads the Kalshi lines received in `[t - 600 s, t]` and
    the Polymarket lines before `t`; the target is Polymarket's mid or spread change from the last line before `t` to the
    line at `t + 20 min` (E009's `+-120 s` tolerance; `unavailable` otherwise, never filled). The stratum is pair x UTC
    day (144 origins by construction; share 1.0 on full days); non-overlapping origins per horizon as E009's `_design`.
13. **Fine-clock dependence.** Clusters are Polymarket events (E009's bootstrap unit); planning `DE_gate` **51**
    (uncapped whole-panel families; a pair's 21-day cluster is 3,024 units, so the formula's own value would be far
    larger and the rule's cap is a declared planning convention, disclosed); the size scenarios add **S19: a Polymarket
    mid that follows Kalshi's level with a two-poll lag and no information in the state** (the gate must hold when the
    lead runs through the level, not the state); `VIF_w` 1.5 for book states.
14. **The fine-clock floor.** 0.5c gross per share on a 20-minute mid target (E009's `trade` rule compares the
    prediction with `ask - bid + taker fees`; that rule, not the floor, is the money check); 1.0c on a spread target. Taker
    routes at 20 minutes are reported, never a verdict (2.9-7.2c round trips); maker routes are gross, no fills.

**Hygiene that binds every idea** (round 14's paragraph applies: decision time is the latest input's own receipt; targets
start after it; nothing reads outcome fields except engine-first `res_7d` features; the primary is a within-stratum
contrast or slope by expanding-past demeaned OLS, the Freedman-Lane gate in the census-fixed stratum is binding, the
liquidity-tier correlation gate and the AR(0.9) scenarios bind, F in LT7's one-rule form is a verdict condition where its
census F-MDE is under the target's floor). Sports stays a parameter (the sidecar's `fee_type` plus CB17's frozen list);
every non-sports entry reports its sports arm uncounted and every sports entry its non-sports twin uncounted.

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader over files the host
already writes with the population counted by a named probe; 4 = pure reader, population bounded above by a named count;
3 = pure reader with an unprobed population, or a matcher or map first; 2 = a stream whose coverage of the population is
unprobed, or a collection change needed; 1 = fetches or weeks. My judgement, not measurements.

**Planning-MDE arithmetic (round 14's, stated once).** Class contrast: `MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x
sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; slope per SD of a continuous state times the tercile gap (about 2.2 SD):
`MDE = 3.47 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap`. `n_eff` = 80% of raw (planning). `DE_gate`:
31 (events capped at <= 10 members), 51 (uncapped, and the fine-clock lane), 3.0 (one game is one cluster; daily-renewed
external frames), 6.196 (mover families). `VIF_w` 1.3 for sidecar states, 1.5 for book states. SDs: 2 h change 4c; |2 h
move| 3c; spread change 2c; 20-min Polymarket mid change **0.7c (planning; unprobed)**; |20-min move| 0.5c (planning);
20-min spread change 1.0c (planning); pre-game sports 2 h change 3c (CH205's planning). **F-MDE** = `MDE x sqrt(2 / (1 -
max(0, r_w)))`, capped at the floor as a verdict condition. Every MDE is quoted at the low and high planning counts and at
a quarter of the low one.

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Streams (`NEW_STREAMS` sections 1-3, the dry run of 10-19 21:55Z): PredictIt 867 keys (about 200 markets, 600+
   contracts; `buy_yes`, `buy_no`, `sell_yes`, `sell_no`, `last`, `last_close`, `status`, `date_end`; the market's own
   `timeStamp` kept raw as `src_ts`; 0-3 changed contracts a minute in the evening dry run); Smarkets 1,734 keys, 677
   books (top-3 levels per side in basis points, `last` executed price with Smarkets' own `timestamp`; catalogue of
   events, markets, contracts, volumes hourly; 123 of 677 books changed in one 5-minute poll); ESPN 94 games, 76 with
   odds (DraftKings moneyline / spread / total, `open` and `close` (= current until kick-off), `state`, `completed`,
   `period`, `clock`, competitors' scores); `gamma_rules` 3,799 market and event keys in the top-3,000 frame, the full
   frame of open markets with 24 h volume about 19k (cap 25k) at 00/06/12/18Z; **3 keys changed in 25 h (all event
   descriptions)**; 2,383 new frame keys a day (turnover, not edits); about 45 MB a day written in all.
2. E009/E010's poller (`CROSS_VENUE_LIVE.md`; the ledger's E009 entry): pairs from a daily refresh (hand verdicts, live
   conflict words, cap 200, ranked by the smaller 24 h volume), Kalshi `/markets?tickers=` (100 a request: `last_price`,
   `yes_bid`, `yes_ask`, both sizes) and Polymarket CLOB `POST /books` (100 tokens: best bid / ask and sizes, book
   timestamp) every 120 s, receipt-stamped, `quotes/YYYYMMDD.jsonl`; **pilot: about 70 pairs / 22 events with complete
   features a cycle, `dk1` non-zero on 12% of origins**; 116 pairs on the engine's 10-20 coverage check (DESIGN_V1
   section 3: `xvenue` 0.25% of 46,448 eligible); about 30 MB a day of raw quotes; the frozen E009 model's 20-minute
   coefficients dk1 0.339, dk6 0.123, gap 0.024, r1 -0.230; retired pairs polled 6 h 20 min; 4 requests per 120 s.
3. The monitor (CB13 H6-H8): 38,115 prints in four days, **sports 70%** (26,509); sweeps lack most printed sports tokens
   ("no touch" for about half of the sports prints); non-sports enriched prints crossing a touch aged <= 60 min about
   2,360 in 7 days (round 14 fact 6).
4. Costs (`EXECUTION_COSTS.md` row sports: n 21,209, round trip **5.2c**, 1.2c of it fees; `COST_MODEL.md`: sports fee
   rate 0.05 since 2026-07-10 with 15% rebate, some sports markets still 0.03; sports 6.2c with fees 2.1c in the
   model's by-category table; politics taker fee rate 0.0 in the docs rate table as the cost model quotes it; passive
   fill within 1 h 2.3% for sports, 1.7% for politics). Round 14 fact 9 for the rest (2.9c / 3.9c / 7.2c by tier; 4.5c
   median touch; 2.38c adverse selection against a 2 h mark).
5. Eligible markets a capture 42,161-51,790 (DESIGN_V1 sections 3 and 16 as rounds 13-14 quoted); non-sports about
   30,000; the rules stream covers **44.7%** of 18,232 eligible non-sports markets (CANDIDATES row 17, the CH199 census).
6. The engine: K = 7 (8 with se21); champion `se0_champion_lr_mm`; `xvenue` family = has-pair, Kalshi mid minus Gamma
   mid, Kalshi spread, quote age (<= 30 min), embargoed to 11-04 (se4 / se13); CANDIDATES row 3 `rules` ("idea; sparse;
   check coverage first"), row 4 `xvenue2` ("coverage likely tiny"; under `xvenue`), row 17 `rulesrc` killed (19.9% <
   30%); CH205's `steam` family and CH208's `xvenue2` timing extension are proposed, not built; `steam` and `rwstart` not
   requested as tokens (CANDIDATES round 5).
7. Frames: Kalshi 116 pairs; PredictIt about 200 markets; Smarkets 677 books; CB15-P 37 PredictIt pairs in 12 events;
   CH208's planning 200-400 matched Polymarket markets in 30-60 events across the three venues (unprobed).
8. Sports on the venue: 17,651 of 24,432 resolved markets in the resolution study's frame were sports
   (`RESOLUTION_DEV_STUDY.md`); `sports_fees_v2` rows 30,503 of 248,235 sidecar rows (`EXECUTION_COSTS.md` line 17).
   Polymarket's game markets have no stored `gameStartTime` or `sportsMarketType` in the sidecar (CH14's data note; the
   `ext_sidecar.py` column list has `fee_type`, `fee_category`, `series_slugs`, `event_ids`, no sports fields), so
   every sports join is CH205's declared matcher (league, UTC date within 1 day, both team names or abbreviations in the
   question; one-to-one; unmatched counted).

**Counts table (what was counted before each idea was written; the source named; `unprobed` where nothing was).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH222 | pair x 10-min origin on E009's stream with a Kalshi move >= 1c in `[t - 10 min, t]`, split by whether Kalshi's `last_price` changed in the same window | 70-116 pairs; 144 origins a pair a day; `dk1` non-zero on 12% of origins (pilot); the traded share of those moves **unprobed** (planning 40%) | fact 2 |
| CH223 | pair x origin with a Kalshi spread widening >= 2c or a touch-size fall >= 50% in `[t - 10 min, t]` and no Kalshi mid move | widening share **unprobed** (planning 3-6% of origins) | fact 2 |
| CH224 | pair x origin with Kalshi's spread innovation over `[t - 10 min, t]` (both signs) and Polymarket's spread at `t` | every valid origin; the SD of Kalshi's 10-min spread change **unprobed** | fact 2 |
| CH225 | matched game x pre-game capture x Polymarket sibling (moneyline, spread, total) | about 45 matched games a day (CH205's planning at 60% matcher coverage of 76); siblings per game **unprobed** (planning 2.5); 6-12 pre-game captures a game | fact 1; CH205 |
| CH226 | matched game with ESPN `completed` x the captures between the final and the UMA proposal | about 45 finals a day (planning); captures to proposal **unprobed** (planning 2-6) | fact 1; CH205 |
| CH227 | non-sports eligible market x capture whose question names an entity that a PredictIt, Smarkets or Kalshi contract also names | entity set and coverage **unprobed** (planning 50-150 entities, 1,000-3,000 markets) | facts 1, 7 |
| CH228 | eligible market x capture with a `gamma_rules` row before the origin (44.7% of eligible non-sports) and the hours since its last market or event edit | edits: 3 in 25 h on the top-3,000 frame (all event descriptions); full-frame edits a day **unprobed** (planning 3-15) | fact 1; fact 5 |
| CH229 | matched Polymarket market x capture with a PredictIt / Smarkets / Kalshi line before the origin | 37 PredictIt pairs (CB15-P); Smarkets overlap **unprobed**; Kalshi 116 | fact 7 |
| CH230 | PredictIt / Smarkets contract matched to a Polymarket CLOB token by a ladder-name matcher inside a matched event | **unprobed** (planning 100-300 contracts in 10-40 events) | fact 7 |
| CH231 | sports market x capture while ESPN's `state` is in-game | **unprobed** (in-game captures a day) | fact 1 |

---

## 1. Map: where money might be on the streams the host already captures

The cost model fixes the frame (2.9c in the most liquid tier, 4.5c at the median touch, 5.2c in sports; makers about
break-even before rewards; a 2.3-4.7% passive fill rate within an hour); the frame arithmetic of 0.1 fixes the clock:
cross-venue questions are testable at the 10-minute grid on E009's stream and nowhere else the host polls today, sports
questions are dense at the capture clock only if sports is in, and everything else on the keyless streams is an engine
column. So the money question for every state below is: **does an event the other venue's own feed dates (a trade that
moved its last price, a quote its makers pulled, a spread its makers tightened, a line the book took down, a final the
scoreboard stamped, a rule the venue edited) move the forecast of Polymarket's next 20 minutes or next capture, on a
population dense enough to be counted, and does it tell a Polymarket maker when to step aside, when to come in, and
which of its own moves are not news?**

| Family | What the host already dates that nobody has read | Money route |
|---|---|---|
| A. The fine clock: the other venue's book, not its price (CH222-CH224) | whether Kalshi's move came with a trade; whether Kalshi's makers pulled size or widened before any move; whether Kalshi's spread tightened (the hedge got cheaper) | maker: step aside when the other venue's makers do; re-centre only on traded moves elsewhere; quote inside when the hedge is cheap; taker (reported): E009's rule on traded moves only |
| B. The sports arm (CH225, CH226) | which Polymarket sibling of a game absorbed the book's joint move last; the scoreboard's `completed` as a price-free "decided" stamp, hours before the venue's proposal | taker on the lagging sibling, hold to the final (reported; 5.2c); hold-to-resolution on the decided side after the final, priced against the expected wait |
| C. The capture clock, engine-first (CH227-CH229) | news arriving on an entity's contracts elsewhere inside the two hours; the hours since a market's or its event's rule text last changed; PredictIt's published close as the morning's anchor | engine: a news-arrival magnitude column, a label-quality weight, a cross-venue anchor; maker: widen on entity news elsewhere; step aside after a rule edit until the first trade |
| D. The enabling map (CH230, CH231) | which PredictIt and Smarkets contracts the poller could add to its pair list after 11-03; the in-game state of a sports row at capture time | none directly; the map makes family A three-venue and family B in-game |

**The reading that steers this round.** Rounds 12-14 read Polymarket's own panels (levels, innovations, the rewarded
panel). The keyless streams add other venues' *books*, and the one cross-venue object AREPO has tested (E009's `dk1`) is
a *mid*. A mid moves for two reasons a book can tell apart: someone paid to move it (a trade: `last_price` changed, a
level was eaten) or its makers re-quoted without being paid (a quote revision: the touch moved, `last_price` did not,
sizes may have been pulled first). Glosten and Milgrom's maker updates on trades; Hasbrouck's information content is the
trade's; a quote revision without a trade is the other venue's makers reacting to something public, which Polymarket's
makers can see too. So the first family splits E009's lead by cause (CH222), reads the makers' withdrawal before any move
as the earliest public trace of pending information (CH223, the mirror of CH133 on the other venue), and reads the hedge
cost (Kalshi's spread) as what sets Polymarket's spread for a maker who can hedge there (CH224). The sports arm reads the
two objects CH205 does not: the sibling market that lags the game's joint move (CH225) and the scoreboard's final as a
decided clock that no price defines (CH226). The capture-clock families are honest engine columns with their coverage
stated (CH227-CH229), and CH230 is the one collection decision that would make the fine-clock lane three-venue.

**Data labels.** `A` = on the host now (captures, sidecar, two sweeps, trade samples, the monitor, the E009/E010 poller's
quotes, the engine's `quotes/`, `features/` and aux tables including `book0`, the four keyless streams, `reward_params`).
`A~` = on the host but a join, matcher or map has to be written and counted first. `A+` = on the host after a pair-list
change to an existing collector (CH230). `P` = a fetch is needed (none here). **Sealed and not usable by anything here:**
LT2's, LT3's, LT4's (E022's) and LT7's stores, LT8's and LT9's once registered, CB16's and CB17's stores, CB8-H's holders,
**E009/E010's `cross_venue_live/` to 2026-11-03** (family A's census runs only after E010's analysis commit; the design
text is frozen before 11-03T02:00Z), E011's `surprise_live/` to 2026-11-10, E025's and E026's stores and the E026 frozen
modules. J4-R `[2026-10-16, 2026-10-21)` and CB13-T's holdout `[2026-10-21, 2026-10-26)` are refused for every maker
mark-out object; nothing here is one.

**Windows and registration this round proposes (LT10).** A tenth family, **the fine-clock family**, registered separately
from LT2-LT9 with its own Holm family (k <= 3), on E009's stream:
- **Design-text freeze before 2026-11-03T02:00Z** (E009's earliest analysis time), so the states, estimators and gates
  are fixed blind; the label is `informed (E009)` regardless, because registration follows E009's and E010's analyses.
- **Census** (counts only) on the stream's worn days `[2026-10-13, 2026-11-03)` after E010's analysis commit (the seal
  lifts with it; if the ledger says otherwise, the census waits), per-day streaming reader, < 300 MB, net lane.
- **Window:** `REGISTERED_UTC` = the first 00:00Z at least 24 h after the LT10 registration commit and after E010's
  analysis commit, never before **2026-11-10T00:00Z**; 21 days; single analysis at least 36 h after the end (so not
  before 2026-12-02T12:00Z); no extension. The window overlaps E022, E026, E011 and LT2 in time only (different
  hypotheses, different streams, no pooling). The DST change of 11-01 precedes the window; the pair refresh's daily
  cadence is disclosed as the one venue cron the lane cannot avoid (it is not a state).
- **Dependencies, declared:** the poller must keep running after 11-03 (unprobed: if it is stopped at E010's close, LT10
  needs the owner's decision to keep it, which is a collection decision, not a new collector); the pair list must hold
  >= 60 pairs in >= 30 events on the census days (CB15-P's gate, adopted), else the whole family drops uncounted.
- **The sports arm (family B)** registers only on the owner's decision, under CH205's 42-day rule (0.1), from the
  earliest 10-day census the ESPN stream allows (its install plus 10 days).

## 2. Hypotheses

### A. The fine clock: the other venue's book, not its price (parents E009 / E010, CH133, CH165, CH166, CH203, CH208; literature: Glosten and Milgrom 1985, Hasbrouck 1991 and 1995, Cont, Kukanov and Stoikov 2014)

**CH222. The venue that traded first: E009 tests whether Kalshi's 10-minute mid change leads Polymarket's next 20
minutes. A Kalshi mid changes for two reasons its own feed tells apart: a trade moved it (`last_price` changed in the
same window, a touch size fell) or its makers re-quoted without a trade (`last_price` unchanged). A traded move is
someone paying to reveal private information; a quote-only move is Kalshi's makers reacting to something public, which
Polymarket's makers can see too. The lead should live in the traded moves; the quote-only moves are the falsification
twin inside the same stream, at the same clock, on the same pairs.**
- Mechanism and why it is non-obvious. Trades carry the information content of prices (Hasbrouck 1991); makers update
  on trades, not on their own revisions (Glosten and Milgrom 1985). E009's `dk1` pools both causes; CH165 reads the
  mirror (Polymarket-led moves Kalshi does not confirm); CH166 reads where the lead lives by spread; CH208 reads the
  minute of the move. None splits the other venue's move by whether anyone paid for it. The host already stores the
  split: every poll line carries `k_last`, `k_bid`, `k_ask` and both sizes (fact 2), so `traded_t = 1[k_last changed in
  [t - 10 min, t]]` costs nothing. Who pays: the Polymarket maker who re-centres on every Kalshi tick (including the
  quote-only ones, where there is nothing to catch up to) and the one who ignores the traded ones; the taker who
  follows E009's rule on a quote revision. Why the crowd misses it: cross-venue bots key off mids.
- Data join and decision clock (`A`, L 4; the fine-clock lane). Unit: pair x 10-minute grid origin `t` on E009's stream
  (rule 12) with a Kalshi move `|dk1| >= 1c` over `[t - 10 min, t]`. State: `traded` (above); `size_eaten` (the fall of
  the touch size on the side the move came from, Kalshi units; S2's dose). Decision time: the receipt of the latest
  Kalshi line used. Controls: `dk1` itself, `dk6`, `gap`, `r1`, `r6`, `lvl`, `lvl2` (E009's seven, so the test is whether
  the cause adds to E009's model), Polymarket's spread and touch sizes at `t`, hour-of-day dummies (24; a venue-clock
  gate as round 13's rule 8), the pair's tier.
- Target and horizon. `c = sign(dk1) x (midP_{t+20} - midP_t)` (Polymarket's 20-minute move in the direction of Kalshi's
  move; SD 0.7c planning); hypothesis (one-sided): E[c | traded] - E[c | quote-only] > 0 given the controls. M1: the
  same at +60 min (E010's horizon); M2: the slope of `c` on `size_eaten` within traded moves (the dose).
- Paper rule and economic check. Maker: re-centre the Polymarket quote on Kalshi's traded moves and hold it through its
  quote-only moves (the mirror of the taker's gain; gross, no fills). Taker (reported, never a verdict): E009's frozen
  rule `|M1_20| > ask - bid + fees` restricted to traded moves, against the same rule on all moves (E009's own
  executable metric); 2.9-7.2c round trips make this a reported arm.
- Population arithmetic. 70-116 pairs x 144 origins x 21 days = 200,000-350,000 origins; Kalshi moves >= 1c on 12%
  (pilot): 24,000-42,000; traded share planning 40% (unprobed): **9,600-16,800 traded, 14,400-25,200 quote-only**.
  Events: 22-60 (fact 2; the pair refresh's ranking by the smaller volume keeps the list liquid).
- Permutation and cluster structure. Rule 12: strata pair x UTC day, 144 units by construction; the Freedman-Lane null
  (given the pair-day, which of its Kalshi moves were traded does not matter for Polymarket's next 20 minutes) is the
  hypothesis's complement. Binding scenarios: LT5 1-2, L10 event clusters, **S19** (rule 13), and a declared **S20: a
  Kalshi `last_price` that changes on a venue cadence unrelated to the move** (the hour-of-day gate kills the state if
  > 50% of traded flags fall in one hour). Clusters: Polymarket event; `DE_gate` 51.
- Planning MDE. Class contrast, SD 0.7c, `n1_eff` 7,680 / `n2_eff` 11,520 (low): `3.47 x 0.7c x sqrt(1/7,680 +
  1/11,520) x sqrt(51) x 1.5 x sqrt(1.5)` = **0.47c**; high (13,440 / 20,160) **0.36c**; at a quarter of the low count
  0.94c. F: the far-future twin is the traded flag of the Kalshi move over `(t + 30, t + 40]` (planning `r_w` 0.1):
  F-MDE 1.49 x MDE = 0.70c / 0.53c, **over the 0.5c cap at both planning ends: F is a reported label**, a verdict
  condition only if the census `n1_eff` >= about 16,000 (the kill line stated as the count at which F passes); the
  MDE gate itself passes 0.5c with >= about 8,500 traded moves (`n1_eff` 6,800) at `n2 >= 1.5 n1`.
- Confounders and the control. Kalshi's traded moves are larger (controlled by `dk1`); traded moves cluster in liquid
  pairs (tier control; the within-pair stratum); a Polymarket trade in the same window that moved both (Polymarket's
  own `r1` is controlled, and CH165's object is the mirror: disclosed, not pooled); E009's results, known at
  registration (`informed (E009)`; the design text frozen before 11-03T02:00Z); the `xvenue` family of the engine reads
  Kalshi's mid and spread at the capture clock (an input overlap, not a hypothesis overlap).
- Most likely boring explanation. Kalshi's `last_price` changes on nearly every mid move (the traded share is > 85%, so
  the quote-only class is too small: the census kill line) or on almost none (the field lags); or the lead is the same
  for both causes because Polymarket's makers watch Kalshi's mid, not its tape. Then the split adds nothing to E009 and
  the test drops at census or returns a null that says E009's `dk1` is the whole story.
- Cheapest census (counts only; the stream's worn days after E010's analysis commit; no target read). Pairs and events
  on the census days (>= 60 in >= 30: CB15-P's gate); Kalshi moves >= 1c a day; the traded share (kill if < 15% or
  > 85%); the hour-of-day distribution of traded flags (<= 50% in one hour); `size_eaten` non-missing share; the
  within-pair SD of `traded` (>= 0.2 in >= 50% of pairs with >= 20 moves); `n1_eff`, `n2_eff`; pessimistic MDE <= 0.5c;
  F-MDE printed. Reader: per-day streaming over `quotes/`, < 300 MB.
- Challenger feature: **yes, as columns of the existing `xvenue` isolate** (se4 / se13) at their next spec version after
  11-04: `kx_last_chg_10m`, `kx_dk1_traded`, `kx_dk1_quote`, `kx_size_eaten`, from the last lines received before the
  capture start (DESIGN_V1 section 3's `xvenue` clock); no new challenger (coverage 0.25% of eligible rows: a real prior
  for the pairs, no K cost). Embargo: `xvenue` to 11-04 (E009 / E010) and, if LT10 registers, a new token **`kxbook`** to
  the later of LT10's analysis commit and 2026-12-04T00:00Z covering the three family-A column sets. Smarkets twin
  (uncounted until CH230): `last_executed_prices` has its own `timestamp`, the cleanest trade / quote split of any venue
  the host polls; PredictIt's `last` against `buy_yes` / `sell_yes`.
- Scores: N 4, EV 3, L 4. Parents: E009 / E010 (the pooled lead), CH165 (unconfirmed moves), CH166 (the lead and the
  spread), CH208 (the minute of the news), CH133 (depth fade on Polymarket's side). New: the cause of the other venue's
  move, read from its own tape, as the state; the quote-only moves as the twin.

**CH223. The other venue's makers flinch first: a maker who learns something cancels before re-quoting (CH133 read
that on Polymarket's book at 120 s). On the same stream Kalshi's touch sizes and spread are stored every poll. A fall in
Kalshi's touch size or a widening of its spread with *no* Kalshi mid move is Kalshi's makers withdrawing on pending
information; the mid has not moved on either venue yet, so it is the earliest public trace there is. It forecasts the
size of Polymarket's next move (magnitude) and, by the side withdrawn, its direction (reported). Polymarket's maker
should step aside when Kalshi's do.**
- Mechanism and why it is non-obvious. Cancellations lead price changes (Cont, Kukanov and Stoikov 2014: order-flow
  imbalance includes cancellations); CH133 reads Polymarket's own fade and conditions on Kalshi being quiet; nobody
  reads Kalshi's fade as the state for Polymarket's move. The two venues' makers are different firms with different
  information; if Kalshi's makers are better informed on a question (the lead E009 found says they often are), their
  withdrawal is a signal Polymarket's makers do not have and takers cannot see on Polymarket's book. Who pays: the
  Polymarket maker who keeps quoting at the old size while the other venue's makers have left; the taker who crosses a
  Polymarket touch that is about to move. Why the crowd misses it: the object is a size on another venue, visible only to
  someone polling both books.
- Data join and decision clock (`A`, L 4; the fine-clock lane). Unit: pair x origin `t` with **no Kalshi mid move**
  over `[t - 10 min, t]` (`|dk1| < 1c`). State: `pull_t = 1[Kalshi spread widened >= 2c or a touch size fell >= 50%
  over the window]`, `pull_side` (the side whose size fell, mapped to the Polymarket token). Decision time: the latest
  Kalshi line's receipt. Controls: E009's seven features, Polymarket's own spread and sizes at `t`, Kalshi's spread level
  at `t - 10 min`, hour-of-day dummies, tier.
- Target and horizon. Primary: `a = |midP_{t+20} - midP_t|` (SD 0.5c planning), one-sided E[a | pull] - E[a | no pull]
  > 0. M1 (signed, reported): `c = pull_side x (midP_{t+20} - midP_t)` > 0. M2: Polymarket's own spread change at +20
  (does Polymarket's maker follow?).
- Paper rule and economic check. Maker: widen or pull the Polymarket quote for 20 minutes when Kalshi's makers pull
  (step aside; the cost of stepping aside is the reward minute lost, which the rewarded subset of the pairs can price:
  rule 11); no taker route from a magnitude. The signed arm (M1) would be a taker route and is reported only.
- Population arithmetic. 200,000-350,000 origins; no-Kalshi-move origins 88%; pull share planning 3-6% (unprobed):
  **6,000-21,000 pull origins** against 150,000-300,000 quiet ones.
- Permutation and cluster structure. Rule 12 strata; the Freedman-Lane null (given the pair-day, which quiet origins
  carried a Kalshi withdrawal does not matter for Polymarket's next |move|); scenarios LT5 1-2, L10, **S19**, and a
  declared **S21: Kalshi sizes that are re-posted on a cadence (a bot's refresh) with no information** (the hour-of-day
  gate; and the state's own AR must be < 0.5 within pair). Clusters: event; `DE_gate` 51.
- Planning MDE. Class contrast, SD 0.5c, `n1_eff` 4,800 / `n2_eff` 152,000 (low): **0.33c**; high (16,800 / 260,000)
  **0.18c**; a quarter of the low count 0.67c. F: the far-future twin is a Kalshi pull over `(t + 30, t + 40]`
  (planning `r_w` 0.2): F-MDE 1.58 x MDE = 0.53c (low, just over the cap) / 0.29c (high): **a verdict condition if the
  census shows >= about 7,500 pull origins (`n1_eff` 6,000), else a reported label**; the MDE gate passes at >= 3,500.
- Confounders and the control. A Kalshi trade that ate a level (a size fall with a mid move) is excluded by the no-move
  condition and belongs to CH222; a Polymarket move in the same window that Kalshi's makers reacted to (Polymarket's
  `r1` is controlled; the state must add to it); the Kalshi spread level (controlled); E009's results at registration
  (`informed (E009)`); CH133's object is Polymarket's own fade (the two can be read together as a reported two-venue
  table, never pooled).
- Most likely boring explanation. Kalshi's sizes are a handful of bots' refresh cycles (S21), the pulls are a cron and
  the hour gate kills the state; or the pulls are real but Polymarket's makers see the same public news within the same
  10 minutes, so the |move| at +20 is no larger after a pull than after any other quiet origin.
- Cheapest census (counts only; the same seal as CH222). Pull origins a day and their share (kill if < 1% or > 15%);
  the hour-of-day distribution (<= 50% in one hour); the within-pair AR of `pull` (< 0.5); the share of pulls on the
  rewarded subset; `n1_eff`; pessimistic MDE <= 0.5c; F-MDE printed. Reader shared with CH222.
- Challenger feature: **yes**, two `xvenue` columns (`kx_pull_10m`, `kx_pull_side`) under the same rule as CH222;
  token `kxbook` if LT10 registers. Smarkets twin (uncounted): the top-3 quantities per side are stored every 5 minutes,
  so the pull is readable three levels deep; PredictIt has no sizes.
- Scores: N 4, EV 3, L 4. Parents: CH133 (the fade on Polymarket's book), CH203 (the quiet book's silent depth),
  E009 / E010, CH166. New: the *other* venue's withdrawal as the state, read before any mid moves anywhere; the
  magnitude primary that no sign ambiguity can kill. The sports twin (a DraftKings line taken off the board on ESPN's
  feed, re-listed later) is the same mechanism on a different stream; its count is tens a week (unprobed) and it is
  an engine column of CH231, not a test (section 4.1).

**CH224. The hedged maker's price: a Polymarket maker who can hedge on Kalshi quotes at Kalshi's half-spread plus the
cost of the hedge; when Kalshi's spread tightens, the hedge gets cheaper and Polymarket's spread should follow within
minutes; when it widens, the hedged quotes leave. CH166 reads the spread *ratio* as the lead's address; this reads
Kalshi's spread *innovation* as the cause of Polymarket's next spread change, with the ratio held as a level. The
money is the maker's: quote inside Polymarket's touch when the other venue's book has just tightened.**
- Mechanism and why it is non-obvious. If any participant quotes both venues, Polymarket's spread on a paired question
  is bounded by Kalshi's spread plus hedging costs, and the binding constraint moves when Kalshi's spread does. The
  level relation is CH166's and CH115's; the innovation relation is unread, and it is the one that says *when* to be
  inside. Who pays: the Polymarket maker quoting wide while the hedge is cheap (loses the reward minute and the fill to
  whoever quotes inside); the one quoting tight while the hedge got dear (adversely selected). Why the crowd misses it:
  it needs the other venue's spread at the minute, which the UI does not show.
- Data join and decision clock (`A`, L 4; the fine-clock lane). Unit: every valid pair x origin `t` (rule 12). State:
  `dsK = spreadK_t - spreadK_{t-10}` (Kalshi's 10-minute spread innovation, both signs), scaled by the census's per-pair
  SD; the level `spreadK_{t-10}` and the ratio `spreadP_{t-10} / spreadK_{t-10}` are controls. Decision time: the latest
  Kalshi line's receipt. Controls: E009's seven, `traded` (CH222's flag), Polymarket's own spread change over
  `[t - 10, t]` and its level, hour-of-day dummies, tier.
- Target and horizon. `dsP = spreadP_{t+20} - spreadP_t` (Polymarket's spread change over the next 20 minutes; SD 1.0c
  planning; floor 1.0c); hypothesis (one-sided): the slope of `dsP` on `z dsK` > 0 with the levels held fixed (Kalshi
  tightened, Polymarket tightens next). M1: the asymmetry (the slope on `max(0, dsK)` against `min(0, dsK)`; widening
  may travel faster than tightening). M2: Polymarket's touch sizes at +20 (do quotes arrive, or only re-price?).
- Paper rule and economic check. Maker: after a Kalshi tightening of >= 1 tick with no mid move, post inside
  Polymarket's touch for the next 20 minutes (gross; the reward formula's share where the market is rewarded, rule 11);
  after a widening, leave. No taker route (a spread target).
- Population arithmetic. 200,000-350,000 origins; `n_eff` 160,000-280,000; the state is nonzero on the origins where
  Kalshi's spread changed (share unprobed; planning 15-30%).
- Permutation and cluster structure. Rule 12 strata; the Freedman-Lane null (given the pair-day, which origins carried
  a Kalshi spread innovation does not matter for Polymarket's next spread change); scenarios LT5 1-2, L10, **S19**, and a
  declared **S22: a Polymarket spread that mean-reverts on its own with a Kalshi spread that random-walks** (the gate
  must hold when Polymarket's own reversion is the only structure). Clusters: event; `DE_gate` 51.
- Planning MDE. Slope at the tercile gap, SD 1.0c, `n_eff` 160,000: `3.47 x 1.0c / sqrt(160,000) x sqrt(51) x 1.5 x
  sqrt(1.5) x 2.2` = **0.25c**; at 280,000 **0.19c**; at a quarter of the low count 0.50c: all under the 1.0c floor. F:
  the far-future innovation `dsK` over `(t + 30, t + 40]` (planning `r_w` 0.1): F-MDE 0.37c / 0.28c, **a verdict
  condition**.
- Confounders and the control. A common public shock that widens both venues' spreads within the same 10 minutes
  (Polymarket's own contemporaneous spread change is controlled; what remains is Polymarket's *lag*, which is the maker
  route either way); a Kalshi trade that ate a level (the `traded` flag is a control; CH222's object); Kalshi's spread
  changing because its mid crossed a tick boundary (the level control; the per-pair scaling); E009 at registration
  (`informed`); `xvenue`'s `Kalshi spread` column (a level at the capture clock; input overlap only).
- Most likely boring explanation. Polymarket's spread on the paired questions is set by reward farmers at
  `rewards_max_spread` (CH45 / CH213's band) and does not respond to Kalshi at all: the slope is zero and the test is a
  clean null; or Kalshi's spread never changes on the pairs (the census kill line).
- Cheapest census (counts only; the same seal). The share of origins with `dsK != 0` (kill if < 10%); the per-pair SD
  of `dsK` (>= 1c in >= 50% of pairs); the within-pair AR of Polymarket's spread (reported for S22); the rewarded share of
  the pairs (the band's role); VIF(`z dsK` | levels) <= 2; `n_eff`; pessimistic MDE <= 1.0c; F-MDE printed.
- Challenger feature: **yes**, `xvenue` columns `kx_spread_chg_10m`, `kx_spread_ratio`; token `kxbook` if LT10
  registers. Smarkets twin (uncounted): its spread in basis points from the top level; its commission is on net
  winnings, so the hedge cost differs and is a declared constant.
- Scores: N 3, EV 3, L 4. Parents: CH166 (the lead where the liquidity is), CH115 (horizon staleness and the hedge
  hurdle), CH45 / CH213 (the band as the spread's floor), E009 / E010. New: the other venue's spread innovation as the
  cause, a spread target, and the maker's "when to be inside" rule.

### B. The sports arm: the board's joint move and the board's final (parents CH205, CH14, CH29, CH01, CH04, CH134, CH208's settlement label, CH23; sports is the owner's parameter; every entry's non-sports twin is reported uncounted; literature: Levitt 2004, Kaunitz, Zhou and Kreiner 2017, Stern 1991)

**CH225. The slow sibling: a sportsbook prices a game's moneyline, spread and total from one model, and when the line
moves all three move together (CH14's premise). Polymarket lists them as separate markets with separate books. CH205
asks whether the book's moneyline move leads Polymarket's moneyline; this asks which of a game's Polymarket siblings
absorbed the book's joint move *last*, within the same game at the same slot, so the game's common shock is removed by
construction and what is left is the lag of one book behind its siblings. The slow sibling's catch-up is the forecast
and the taker's route; the sibling that already moved is the control.**
- Mechanism and why it is non-obvious. CH14 reads the implied-consistency gap between the moneyline and the spread
  market as a level and says the spread market is slower; CH205 reads the book's move against the moneyline's unmoved
  price. Neither uses the book's *joint* move as an instrument inside the game: the three siblings face one exogenous
  shock (DraftKings' re-pricing, dated by ESPN's 10-minute poll) and the one whose own price absorbed the least of its
  own line's move is the one still to move. Within a game x slot the shock is identical, so the contrast across
  siblings is free of game-level news, league, kick-off hour and the day's attention. Who pays: the sibling's maker who
  did not re-centre when the moneyline's did; the taker who trades the slow sibling at its stale price. Why the crowd
  misses it: Polymarket's game page shows the three markets as unrelated tiles.
- Data join and decision clock (`A~`, L 3: CH205's matcher first, extended to the spread and total markets by the
  question's line text; sports only by construction). Unit: matched game x pre-game capture k x Polymarket sibling s
  (moneyline, spread, total; both sides are one market each). State: `unabsorbed_{s,k} = dbook_{s,(k-1,k]} -
  dmid_{s,(k-1,k]}` (the de-vigged move of the sibling's own DraftKings line over the interval, from the last ESPN poll
  received before capture k, minus the sibling's own mid change over the same interval; the proportional de-vig
  declared, the spread and total converted with Stern 1991's per-sport sigma, declared constants). Decision time: the
  max of the ESPN poll's `recv_utc` and the row's `received_utc`. Controls: the sibling's own change, its level gap to
  its line, spread, `log1p volume24hr`, hours to kick-off, sibling type dummies.
- Target and horizon. `c2 = mid_{s,k+1} - mid_{s,k}` signed as the sibling's own line moved; hypothesis (one-sided):
  within game x slot, the slope of `c2` on `z unabsorbed` > 0 (two-way demeaned: market, and game x slot). M1: the
  change to the last pre-game capture; M2: the sibling's spread change at k + 1 (does its maker widen late?).
- Paper rule and economic check. Taker: on a game whose moneyline absorbed the book's move and whose spread or total
  market did not, trade the slow sibling toward its line, hold to the final (reported; the sports round trip is 5.2c,
  fees 1.2c; the hold-to-final leg saves the exit). Maker: re-centre all three siblings on the book's joint move at once
  (the mirror; gross).
- Population arithmetic. 30-45 matched games a day (CH205's planning at 76 games with odds; the share of games with
  spread and total markets on Polymarket **unprobed**, planning 50%); siblings per game 2-2.5; pre-game captures 6-10:
  **360-1,125 units a day, 7,600-23,600 in 21 days** (`n_eff` 6,000-18,900); 15,000-47,000 in 42 days. Clusters: one
  game (both sides, all siblings): 630-950 games in 21 days.
- Permutation and cluster structure. Strata game x UTC day hold up to 30 units (3 siblings x 10 slots); the
  Freedman-Lane null (given the game-day, which sibling-slot carried the unabsorbed move does not matter for its next
  change) is the hypothesis's complement; scenarios LT5 1-3, CH205's **S13** (a mid that follows the level with a one-slot
  lag), and a declared **S23: siblings whose lines move together and whose mids follow with the same lag** (the
  contrast must then be zero). Clusters: game; `DE_gate` 3.0.
- Planning MDE. Slope at the tercile gap, SD 3c, `n_eff` 6,000: `3.47 x 3c / sqrt(6,000) x sqrt(3) x 1.5 x sqrt(1.3) x
  2.2` = **0.87c**; at 18,900 **0.49c**; at a quarter of the low count 1.7c. At 42 days 0.62c / 0.35c. **Declared now,
  as CH205 declared: proposed with a 42-day window or not at all**, and only at the high end of the sibling count. F:
  the far-future unabsorbed move (over `(k + 1, k + 2]`; `r_w` 0.1): 0.92c / 0.52c at 42 days: a reported label. The
  two-way demeaning may cut the residual SD below 3c (unprobed); the census prints it.
- Confounders and the control. The moneyline's own move in the interval (a sibling control, not the state); liability
  moves by the book that are not information (the state is the same either way); the matcher's errors on spread and
  total questions (the line text parse; audited 50 by hand, counts only); Polymarket listing no spread or total market
  for most games (the kill line); CH205 reads the moneyline on the same games (a different object, disclosed; if both
  register they share one Holm family).
- Most likely boring explanation. Polymarket lists spread and total markets for few games outside the NFL and the NBA,
  and those it lists do not trade before kick-off (the count kill line); or all three siblings are quoted by the same
  bot from the same line feed, so no sibling ever lags (S23: a clean null).
- Cheapest census (counts only; the ESPN stream's day files from the install plus 10 days; the sealed captures of the
  same days). Games a day with odds; matched games; games with >= 2 Polymarket siblings; sibling-slots with a nonzero
  line move (>= 20%); permutable share (>= 0.5); the residual SD after two-way demeaning; `n_eff`; pessimistic MDE at
  42 days <= 0.5c. Kill if games with >= 2 siblings < 15 a day on average or precision < 0.9.
- Challenger feature: **yes, as columns of CH205's proposed `steam` family** (`st_unabsorbed`, `st_sib_type`,
  `st_sib_lag_rank`), NaN outside matched pre-game sports rows; read against se1 on the sports breakdown; token `steam`
  (CH205's proposal; not requested until a sports test is drafted).
- Scores: N 3, EV 3 (if sports is in), L 3. Parents: CH14 (sibling consistency as a level), CH205 (the moneyline's
  steam), CH29 (the closing line), CH48 (a matcher caveat). New: the within-game x slot contrast with the book's joint
  move as the instrument; the slow sibling as the unit. Non-sports twin (uncounted; CH230): PredictIt's ladder
  contracts against Polymarket's ladder members in a matched event, the contract that moved against the siblings that
  did not.

**CH226. The resolver's clock: CH01 reads the decided-but-unresolved carry with "decided" defined by the market's own
price reaching 0.97, and CH04 reads the zombie quotes after a final; CH134 and CH208 use Kalshi's, Smarkets' and
PredictIt's settlements as decided labels on a few pairs. ESPN's `completed` flag is a decided label on every matched
game, stamped at the 10-minute poll, defined by no price. From that stamp the discount on the winner's side is a
function of two things the host can read: the wait to the venue's proposal (a map by hour and day of the final, built
on worn data before any test) and the oracle tail. The money is hold-to-resolution; the hypothesis is that the discount
tracks the expected wait, so the excess over the oracle tail is the venue's operating hours, not risk.**
- Mechanism and why it is non-obvious. Capital locked for an uncertain wait at a venue that proposes resolutions when
  its staff or its bots run: the wait is the price of the carry (CH01's mechanism), and the wait depends on *when* the
  game ended. CH01 could not separate "known" from "priced at 0.97" because its clock was the price; the scoreboard's
  final is a clock that is not a price, on hundreds of games a week, and the proposal time is in the sidecar
  (`uma_resolution_statuses`, every 2 h). Who pays: the holder of the winning side who sells at 0.97-0.985 at 03:00Z
  because resolution is twelve hours away; who collects: the buyer who holds. Why the crowd misses it: the carry is
  1-3c and the capacity is the ask's depth (5-50 shares in CH04's envelope).
- Data join and decision clock (`A~`, L 3; sports by construction; a map first). Unit: matched game g at the first
  complete capture after ESPN's `completed` (the decision time is the max of the poll's `recv_utc` and the row's
  `received_utc`), with the winner read from the final score (never from a price). State: `w(g)` = the expected wait
  to the venue's proposal from the hour-of-final x weekday cell of a **map built on worn captures before the design
  freeze (counts only; proposal times from the sidecar; the final from the stream)**, in two declared classes
  (short-wait, long-wait) at the map's median; `tail` = the share of games in the cell whose proposal disagreed with
  the scoreboard (the oracle tail; counts). Controls: the winner's pre-final mid, spread, `log1p liquidity`, league,
  fee rate.
- Target and horizon. `d = 1 - ask_winner` at that capture (the discount; SD **unprobed**, planning 1c); hypothesis
  (one-sided): E[d | long wait] - E[d | short wait] > 0 given the controls. M1: the discount's decay across the captures
  to the proposal (slope on hours since the final); M2: the loser's bid (the mirror). M3 (the map's own object): the
  realised wait by cell and the tail rate.
- Paper rule and economic check (rule 11: hold-to-resolution). Buy the winner at the ask at the first capture after
  the final, hold to redemption: gross `d`; cost one taker leg (half-spread about 0.5c at a 1c spread, the fee at
  p = 0.98 about 0.1c at the 0.05 rate); the tail from the map; net per share and annualised by the realised wait,
  reported against the cost model's sports row. Capacity: the ask's size at that capture (the sweep's `ask_size_1`
  where the token is swept; the monitor shows most sports tokens are not).
- Population arithmetic. 30-45 matched finals a day (planning): **630-950 games in 21 days**; one unit per game for
  the primary; 2-6 captures a game for M1 (unprobed). Clusters: game (`DE_gate` 3.0); strata league x UTC day.
- Permutation and cluster structure. The Freedman-Lane null (given the league-day, which games ended in a long-wait
  hour does not matter for the discount) within league x day strata (several games a day in the NBA, NHL and college
  football; one or none in others: the permutable share is the census's first number); scenarios LT5 1-2 and a declared
  **S24: a discount that depends on the pre-final mid and nothing else** (the control must absorb it). **Round 13's
  rule 8 (venue clocks) is disclosed:** the state is an hour-of-day class; it is admissible only because the clock *is*
  the mechanism (the wait) and enters through the map's expected wait, not as raw hour dummies; the challenger decides.
- Planning MDE. Class contrast, SD 1c, 380 / 380 effective games (21 days): `3.47 x 1c x sqrt(2/380) x sqrt(3) x 1.5 x
  sqrt(1.3)` = **0.75c**; at 42 days (760 / 760) **0.53c**; at the high count in 42 days (76 finals a day, 1,280 /
  1,280) 0.41c. Against a 0.5c floor the test passes only at 42 days and the high count: **a map first; a test only on
  its count**. F: no far-future twin exists for a one-unit-per-game state; a reported label by construction.
- Confounders and the control. The pre-final mid (a close game's winner was at 0.6 before the final and its discount
  reflects the makers' lag, CH04's object, not the wait: controlled, and the first capture is 0-2 h after the final,
  which the map's lag shares); the fee rate (sports 0.05 or 0.03, a control); games whose Polymarket market resolves
  on a different rule than the scoreboard (overtime, regulation-time clauses: CH48; the map's tail counts them); the
  monitor's and the sweeps' thin sports coverage (fact 3) means capacity is unprobed.
- Most likely boring explanation. The discount at the first post-final capture is the makers' lag (CH04), not the
  wait: it is the same at every hour and decays within one capture; the map then shows no wait structure and the test
  is not proposed. Or the ask is 1.00 within minutes of the final on every liquid game (bots) and `d` is zero.
- Cheapest census (counts only; the stream's day files and the sealed captures; the map comes first). Finals a day;
  matched finals; the proposal lag distribution by hour-of-final x weekday (the map; cells with >= 20 games); the
  disagreement rate (tail); the share of games with a two-sided ask at the first post-final capture; the permutable
  share within league-days; the SD of `d`; `n_eff`; pessimistic MDE at 42 days <= 0.5c.
- Challenger feature: **no** (a one-unit-per-game object; the engine's `res_7d` target could take `completed_elsewhere`
  as a label-quality feature, CH208's `xt_settled_elsewhere` already names that column for the three politics venues;
  the sports column is CH231's `gs_completed`).
- Scores: N 3, EV 2, L 3. Parents: CH01 (the carry and the expected wait), CH04 (zombie quotes), CH134 and CH208 (the
  settled-elsewhere label), CH23 (end-of-game), CH167 (the exit map). New: a price-free decided clock on a dense
  population and the venue's operating hours as the carry's explanation. Non-sports twin (uncounted): PredictIt's
  contract `status` closing at `last` 100 / 0 and Smarkets' settled state (CH208's columns), tens a week.

### C. The capture clock, engine-first (parents CH208, CH114, CH25, CH97, CH141, CH08, CH177, CH63, CH199, CH207; CANDIDATES rows 3, 4 and 17; the "breadth" and "mention basket" ideas of rounds 6-9, closed)

**CH227. The entity clock: a pair join gives tens of events; a category join gives one series for everyone (rule 8's
cron and the closed "breadth" idea). Between them is the entity: PredictIt's 600 contracts, Smarkets' 677 books and
Kalshi's 116 pairs name a few hundred people, parties, bodies and places, and so do thousands of Polymarket non-sports
questions. "Did any contract naming this market's entity move >= 1c on another venue inside the last two hours, and
when?" is a market-specific news-arrival clock on a population an order of magnitude larger than any pair list, with no
sign (news on Trump moves "Trump signs X" and "Trump approval > 45" in unknown directions), so its object is the
magnitude of the next move and the maker's spread, and its home is the engine.**
- Why engine-first. The frame arithmetic (0.1): planning 1,000-3,000 matched non-sports markets give `n_eff`
  200,000-600,000 and a magnitude-slope MDE of **0.62c / 0.36c** at DE 51 (SD 3c, VIF 1.3; a quarter of the low count
  1.2c), but the far-future twin of entity news is autocorrelated (news clusters; planning `r_w` 0.3), so the F-MDE is
  1.05c / 0.61c, over the cap at both ends; and the state is shared by every market naming the entity at the same
  slot, so the honest cluster is entity x day, which the planning convention does not price. A test would be a weak
  magnitude test with a reported F; the engine scores the column against se1 on every row where it is not NaN.
- State (`A~`, L 3: an entity dictionary and a matcher are maps first; counts only). `xe_n_moves_2h` (the number of
  other-venue contracts naming any of the market's entities that moved >= 1c in `(k - 1, k]`, from the three streams'
  change-only rows received before the capture start), `xe_min_since_move` (minutes from the latest such move to the
  origin; NaN without one), `xe_n_contracts` (the entity's contract count elsewhere, a coverage level), `xe_abs_move`
  (the largest such move in cents, fee-adjusted by CH208's constants). The entity dictionary is built once from the
  streams' contract names and Polymarket questions (proper nouns shared by >= 3 markets and >= 1 contract; no
  hand-curation after the first count; its sha256 pinned). Decision time: the latest stream poll's `recv_utc`.
- Engine mapping. New aux family `xent` (`se-aux-xent-v1`), LightGBM challenger `se24_lgbm_xent` against se1 on the
  non-sports breakdown; the `dir_2h` target has no sign from this family, so the gain, if any, comes through the
  learner's interaction with momentum (the champion's own change is more likely to persist when news arrived
  elsewhere: CH208's reading); the honest first use is as a **`res_7d` and calibration moderator** (news arrival widens
  the forecast's uncertainty). Coverage: the matched-entity share of non-sports rows (unprobed; kill line < 5%).
  Embargo: `xvenue` to 11-04 (the same hypothesis class as E009 / E010 for the Kalshi contracts; the builder's row 4
  rule); no new token (nothing registered reads entity joins). Memory: the three streams' day files are < 50 MB a day
  in all; the matcher runs once per capture on the changed keys only.
- Money route (paper). Maker: widen on Polymarket for the slot after entity news elsewhere (the 2.38c adverse
  selection concentrates there); no taker route (no sign).
- Boring explanation. The entity set is a dozen names (Trump, the Fed, the Supreme Court) whose contracts move every
  interval, so the state is a constant 1 on the matched rows; or the matched rows are the liquid politics markets the
  engine already forecasts best, and the column adds nothing to se1.
- Census (counts only). Entities; matched markets and events; the share of matched rows with `xe_n_moves_2h` > 0 by
  entity (kill the entity if > 80% or < 2%); the within-market SD of the state; coverage of non-sports rows.
- Scores: N 3, EV 2, L 3. Parents: CH208 (the minute of the news on pairs), CH97 (the entity's pageviews), CH141
  (named-person markets), CH114 / CH25 (the venues), the closed "breadth" and "mention basket" ideas (category-level
  and speech-level joins, not this). New: the entity as the join, between pair and category.

**CH228. Rule freshness: `gamma_rules` stores the time a market's or its event's rule text last changed (hourly for
the top 3,000, 6-hourly for the volume frame). An edit is rare (3 in 25 hours on the top frame, all event descriptions),
so an edit *event* fails pattern 1 and CB18-S closed the silent-edit test. The engine does not need an event: "hours
since the rules last changed", NaN where never seen, is a per-row level with a sharp recent-edit tail, and the natural
place for it is the `res_7d` target, where a market whose rules were edited in the last week resolves more often in the
way the edit implied than its price says, and the champion's calibration should differ by it.**
- Why engine-first. The test arithmetic: event-description edits propagate to every member (10-30 markets) and give
  a within-market-day contrast (the slot after the edit against the other eleven); planning 250 event edits in 21
  days on the full frame (unprobed: 3 a day on 1,500 top-frame events scaled to about 6,000 frame events gives about
  12 a day) x 15 members = 3,000 treated units against 33,000, SD 4c, event clusters of 180 units (`DE_gate` 4.6): MDE
  **0.97c**, F unaffordable (an edit has no twin). At 1,000 edits 0.54c: the kill line for any future test, stated;
  this round proposes none. Coverage is the second reason: the stream covers 44.7% of eligible non-sports markets
  (CH199's census), fine for a column, fatal for a panel.
- State (`A`, L 4; counts only). `re_h_since_m` (hours since the market's own `m:` row last changed; NaN if only ever
  `new`), `re_h_since_e` (the same for its event's `e:` row), `re_edited_7d`, `re_n_edits_30d`, `re_in_frame` (seen in
  the stream before the origin), `re_text_len`, `re_n_dates` (the number of dates in the description, a specificity
  count CH63 proposed as a level), `re_fallback` (the fallback-type class). Decision time: the latest stream poll's
  `recv_utc` before the capture start; the "edit time" is the row time of the `changed` row (the stream's caveat: a
  market entering the frame edited is `new`, not `changed`, so its edit time is unknown and NaN, never the row time).
- Engine mapping. Aux family `ruleedit` (`se-aux-ruleedit-v1`), challenger `se25_lgbm_ruleedit` on `res_7d` first
  (the label-quality reading), `dir_2h` second; read against se1. CANDIDATES row 3 (`rules`: "sparse; check coverage
  first") is this family with the coverage checked by CH199's census (44.7% / 19.9%); row 17's `rulesrc` host class is
  not re-used. Embargo: none (CB18-S is closed; no registered test reads rule edits; the `umaparams` idea CH207 shares
  the stream and would share the family's spec). Memory: the stream's daily hash checkpoints make the "last changed"
  table a few MB.
- Money route (paper). Maker: after an edit, step aside until the first trade (the edit's direction is readable by
  people, not by the row); a reported `res_7d` calibration split by `re_edited_7d` is the honest output.
- Boring explanation. Edits are typos and formatting (CB18-S's audit precision problem); the recent-edit tail is a few
  dozen rows a week and the learner never sees enough of them; the family's whole value is `re_in_frame` (a volume
  proxy the champion already holds).
- Census (counts only): edits a day on the full frame by `m:` / `e:`; the share of eligible rows with a non-NaN
  `re_h_since_*`; the recent-edit (7 d) share (kill line < 0.5% of covered rows).
- Scores: N 2, EV 2, L 4. Parents: CH08 (rule-edit events), CH177 (silent edits; CB18-S), CH63 (specificity), CH199
  (the source class; killed), CH207 (UMA parameters). New: the edit as a level with a tail on the `res_7d` target, and
  the event-edit propagation arithmetic that says what count a future test would need.

**CH229. The published close and the capture-clock columns of family A: PredictIt's `last_close` is the price the
press and the aggregators quote the next morning; Polymarket's politics twins may drift toward it in the US morning
captures (a display effect across venues, CH218's reading of a venue-computed number applied to another venue's
published number). And the fine-clock states of CH222-CH224 have capture-clock shadows the engine can read now on the
Kalshi pairs. All of it is `xvenue2` (CANDIDATES row 4): engine columns, no test, because the frame is 37 PredictIt
pairs (CB15-P) and 116 Kalshi pairs.**
- Why engine-first. Fact 7 and the frame arithmetic; CH208 already proposes the timing columns and the dispersion;
  this adds the published anchor and the book-cause columns. Nothing here is a hypothesis with a count.
- State (`A~`, L 3). `pi_close_gap` (PredictIt's `last_close` on the matched contract, fee-adjusted by CH208's
  constants, minus the Polymarket mid at the first capture after 05:00Z; NaN otherwise), `pi_src_age` (the market's
  own `src_ts` age at the poll, a staleness level kept raw as the stream keeps it), and the capture-clock shadows
  `kx_last_chg_2h`, `kx_pull_2h`, `kx_spread_chg_2h` (CH222-CH224's states over the two hours before the capture start,
  from the quotes lines received before it). Decision time: the latest line's receipt.
- Engine mapping. Columns of `xvenue2` (`se-aux-xvenue2-v1`, CH208's proposal) rather than a new family; no new
  challenger. Embargo: `xvenue` to 11-04 (E009 / E010); `kxbook` if LT10 registers (the three book-cause columns only).
- Scores: N 2, EV 2, L 3. Parents: CH114 (PredictIt's fee-adjusted anchor), CH25 (the level gap), CH208 (`xvenue2`
  timing), CH218 (the display's number). New: the published close as an anchor, and the capture-clock shadows of the
  fine-clock family.

### D. The enabling map and the in-game state (parents E009 / E010, CH208, CH230's own matcher; CH23, CH44, CH205)

**CH230. The three-venue fine-clock panel (a map and a collection decision, k = 0): the poller already polls
Polymarket's CLOB books for its Kalshi pair list every 120 s. PredictIt and Smarkets are polled by their own streams at
1 and 5 minutes, but no Polymarket book is polled for their matched markets, so every PredictIt and Smarkets clock is an
uncounted twin in family A. A ladder-name matcher inside matched events (the nominee ladders, the control markets, the
by-election and leadership questions) would give the poller 100-300 more tokens; adding them is a pair-list change to an
existing collector after E010's analysis, not a new collector, and it is the owner's decision because it changes what a
registered experiment's stream collects.**
- What the map counts (counts only; no price). PredictIt contracts and Smarkets contracts matched to Polymarket CLOB
  tokens by event (CH208's and CH114's matchers as designed; hand verdicts for the 2026 and 2028 ladders), the events,
  the share that survive 11-03 (the midterm markets resolve; the 2028 ladders persist), the per-venue change rates on
  the matched set (fact 1's 0-3 PredictIt changes a minute, 123 of 677 Smarkets books a poll), and the poller's budget:
  each 100 tokens is one more Polymarket request per 120 s (4 now; the ledger's 10-13 note says an extra request per
  venue once active plus retired pairs exceed 200), about 15 MB a day of raw quotes per 100 tokens, no new memory of
  note (the poller holds 115-132 MB).
- Why it matters. With it, CH222's trade / quote split is read on the one venue that stamps its trades (Smarkets'
  `last_executed_prices`), CH223's pull three levels deep, CH224's spread in basis points, and CH225's non-sports twin
  (the ladder contract that moved against the siblings that did not) on 10-40 ladder events; without it, family A is
  Kalshi-only and the politics venues stay capture-clock columns. The 2026-11-03 midterms fall before any such change
  could be made (E010's analysis is after 11-03T08:00Z), so nothing here is election-night (CB15-E owns that).
- Kill criteria: none (a map). Its count decides whether LT10's census is run on one venue or three; the decision is
  recorded in the ledger either way.
- Scores: N 2, EV 3 (as an enabler), L 2. Parents: E009 / E010 (the poller), CH208 (the matchers), CH130 (the pair at
  birth), CB15-P (the 37-pair count that closed the capture-clock frame).

**CH231. The in-game state (engine-first; sports parameter): ESPN's board carries `state`, `period`, `clock` and the
scores at every 10-minute poll, and DraftKings' current line during the game. Polymarket's in-game sports rows are
forecast by the engine with no game state at all; the capture that falls inside a game sees a mid the score explains.
A `gamestate` family is the cheapest sports family there is, it is where CH223's "line off the board" lives as a
column, and it is a test for nothing in this round.**
- Why engine-first. The in-game capture count is unprobed and the targets are hours from resolution (`dir_2h` inside a
  game is the score's next move; `res_7d` is the final); CH23 (the hope premium) and CH44 (the live pool) are the
  in-play ideas and both need a finer Polymarket clock than the captures (the monitor's sports prints lack a swept
  touch for about half, fact 3). The engine reads the columns on the sports breakdown and reports; the owner's scope
  decision gates anything more.
- State (`A~`, L 3; CH205's matcher). `gs_in_game`, `gs_period`, `gs_clock_s`, `gs_margin` (home minus away score,
  signed to the market's side), `gs_dk_live_prob` (the current moneyline de-vigged, NaN when the odds field is absent),
  `gs_off_board` (odds absent at the last poll after having been present pre-game or in-game: CH223's sports twin,
  tens a week, unprobed), `gs_completed` (CH226's decided stamp as a `res_7d` label-quality feature). Decision time: the
  last ESPN poll's `recv_utc` before the capture start.
- Engine mapping. Aux family `gamestate` (`se-aux-gamestate-v1`), read against se1 on the sports breakdown only;
  NaN on every non-sports row. Embargo: none (nothing registered reads sports lines; CH205's `steam` token is not yet
  requested); if a sports test is drafted, `steam` covers the line columns and a new `gamestate` token the rest.
- Scores: N 2, EV 2 (if sports is in), L 3. Parents: CH23, CH44, CH205, CH04, CH226. New: the in-game state as engine
  columns and the off-board flag's home.

---

## 3. Ranked shortlist for LT10 (the fine-clock family), the sports arm, then the rest

Rank = census survival (a complete panel, a dense state, an innovation or a cause, a declared DE, the MDE at the *low*
planning count under the floor, the F-MDE under its cap) x originality x plausibility x money route, with the rules of
round 14's 0.2 and this round's 12-14 as hard constraints. Every LT10 candidate has a state defined on E009's stream
for every pair x 10-minute origin, read strictly before the origin from the other venue's own lines, a within-pair
contrast or slope with the Freedman-Lane gate in pair x day strata that hold 144 units by construction, a falsification
twin that is the same object 30 minutes later, a counts-only census on the stream's worn days after E010's analysis
commit, a planning MDE under the floor at the low planning count, and one light per-day streaming reader shared by the
three (< 300 MB, net lane). The last column is my prior probability that the idea passes its own census as written,
before any count; it is a judgement, not a measurement. The sports entries carry two priors: ex-sports (zero by
construction) and with sports in.

| Rank | ID | One line | L | Population arithmetic (source) | Permutation structure | Primary | Planning MDE (quarter); F | Prior odds of surviving census |
|---|---|---|---|---|---|---|---|---|
| 1 | CH224 | The hedged maker's price: Kalshi's spread innovation moves Polymarket's spread 20 minutes later | 4 | every valid origin: 200,000-350,000 in 21 days (fact 2); `n_eff` 160,000-280,000 | continuous innovation on every unit; 144 units a pair-day; FL with S19, S22 | within pair, slope of `dsP(+20)` on `z dsK` > 0, levels fixed | **0.25c / 0.19c** against 1.0c (quarter 0.50c); **F verdict** 0.37c / 0.28c | 0.45 (the one risk is a Kalshi spread that never changes on the pairs, or a Polymarket spread pinned at the reward band; the poller's continuation after 11-03 is the family's shared risk) |
| 2 | CH223 | The other venue's makers flinch first: a Kalshi size pull or widening with no Kalshi mid move forecasts Polymarket's next \|move\| | 4 | pull origins 6,000-21,000 (3-6%, unprobed) against 150,000-300,000 quiet | per-interval event on quiet origins; 144 units a pair-day; FL with S19, S21; hour gate | within pair, E[a \| pull] - E[a \| quiet] > 0 | **0.33c / 0.18c** (quarter 0.67c); F verdict at >= 7,500 pulls (0.53c / 0.29c) | 0.35 (the pull share and the bot-refresh gate decide; power is not the question) |
| 3 | CH222 | The venue that traded first: Kalshi's traded moves lead, its quote-only moves do not | 4 | Kalshi moves 24,000-42,000 (12% of origins, pilot); traded 9,600-16,800 (40%, unprobed) | class split of a per-interval event; FL with S19, S20; hour gate | within pair, E[c \| traded] - E[c \| quote-only] > 0 given E009's seven | **0.47c / 0.36c** (quarter 0.94c); F reported (0.70c / 0.53c), verdict at `n1_eff` >= 16,000 | 0.30 (the traded share may be near 1 or near 0; the MDE sits at the floor at the low count) |
| 4 | CH225 | The slow sibling: the game's Polymarket sibling that absorbed the book's joint move last (sports arm) | 3 | 7,600-23,600 sibling-slots in 21 days, 15,000-47,000 in 42 (CH205's planning; the sibling share unprobed) | game x day strata of up to 30 units; FL with S13, S23 | within game x slot, slope of `c2` on `z unabsorbed` > 0 | **0.87c / 0.49c** at 21 days, 0.62c / 0.35c at 42 (quarter 1.7c); F reported | 0.0 ex-sports; 0.25 with sports in (42 days; the spread and total listings are the risk) |
| 5 | CH226 | The resolver's clock: the discount after the scoreboard's final tracks the expected wait (sports arm; map first) | 3 | 630-950 finals in 21 days (planning) | league x day strata; FL with S24; rule 8 disclosed | between games within league-day, E[d \| long wait] - E[d \| short wait] > 0 | 0.75c / 0.53c at 42 days (quarter 1.5c); F none | 0.0 ex-sports; 0.10 with sports in (a map first; the makers' lag may be the whole discount) |
| 6 | CH230 | The three-venue fine-clock panel (map; a collection decision) | 2 | 100-300 contracts in 10-40 events (unprobed) | n/a | n/a | n/a | n/a (its count decides whether LT10 is one-venue or three) |
| 7 | CH227 | The entity clock (engine-first; `xent`) | 3 | 1,000-3,000 matched non-sports markets (unprobed) | n/a | `res_7d` moderator; `dir_2h` via the learner | engine window (a test: 0.62c / 0.36c, F 1.05c / 0.61c) | n/a (kill if coverage < 5%) |
| 8 | CH228 | Rule freshness (engine-first; `ruleedit`; the `res_7d` label-quality reading) | 4 | 44.7% of eligible non-sports in the frame; edits 3-15 a day (unprobed) | n/a | `res_7d` against se1 | engine window (a test would need >= 1,000 edits for 0.54c) | n/a (kill if the recent-edit share < 0.5%) |
| 9 | CH229 | The published close and the capture-clock shadows (engine-first; `xvenue2` columns) | 3 | 37 PredictIt pairs; 116 Kalshi pairs | n/a | se4 / se13 isolates after 11-04 | engine window | n/a |
| 10 | CH231 | The in-game state (engine-first; sports; `gamestate`) | 3 | in-game captures a day unprobed | n/a | sports breakdown against se1 | engine window | n/a |

CH224 is first because it is the only state in the round that is defined on *every* unit of its panel, its target is a
spread (the cheaper floor), its twin is affordable (an innovation thirty minutes later), and its route is the maker's
"when to be inside", which no textbook reversion predicts. CH223 is second because its primary is a magnitude (no sign
to get wrong), its power is not in question and its risk is one honest gate (a bot's refresh cadence). CH222 is third
because its mechanism is the cleanest (the cause of the other venue's move, from the other venue's own tape) but its
MDE sits at the floor at the low count and its F is a reported label there. The sports pair follow because they are
tests only on the owner's call; CH225 is written so the designer can lift it the day sports is in. The map and the four
engine-first entries follow. **If the LT10 designer wants k = 3, CH224, CH223 and CH222 are the three (one spread
slope, one magnitude contrast, one signed contrast on the same stream; their dependence is disclosed and Holm handles
it), registered after E010's analysis and only if the poller still runs; CH225 joins a sports family under CH205's
42-day rule if the owner puts sports in; CH230 is the one decision that would make all three three-venue.**

**Pre-registration sketches for the top 4 (LT10 candidates and the first sports-arm candidate; each a separate
primary in one Holm family; written in LT8's and LT9's shape so the designer can lift them).**

- **CH224 (the hedged maker's price).** Unit: pair x 10-minute origin `t` on E009's stream with valid two-sided books on
  both venues at `t` and `t - 10 min` (rule 12). State: `z dsK` = Kalshi's spread change over `[t - 10, t]` scaled by
  the census's per-pair SD. Decision time: the latest Kalshi line's receipt. Primary: expanding-past pair-demeaned OLS
  of `dsP = spreadP_{t+20} - spreadP_t` on `z dsK` with `spreadK_{t-10}`, `spreadP_{t-10} / spreadK_{t-10}`, Polymarket's
  own `[t - 10, t]` spread change, E009's seven features, `traded`, 23 hour dummies and tier as controls; one-sided > 0;
  material reading top-against-bottom tercile. Targets: `dsP` at +20; M1 the asymmetry (`max(0, dsK)` against
  `min(0, dsK)`); M2 Polymarket's touch sizes at +20. Clustering: CR1 on Polymarket event, two-way event x UTC day and
  UTC day, p the largest; `DE_gate` 51. Planning MDE 0.25c (low) / 0.19c (high) against 1.0c; F-MDE 0.37c / 0.28c, a
  verdict condition. Census (the stream's days `[10-13, 11-03)` after E010's analysis commit; counts only): pairs >= 60
  in >= 30 events; `dsK != 0` on >= 10% of origins; per-pair SD of `dsK` >= 1c in >= 50% of pairs with >= 500 origins;
  VIF(`z dsK` | levels) <= 2; liquidity gates (within; pooled); the within-pair AR of `spreadP` printed (S22); `r_w`
  (lead, lag) <= 0.3; pessimistic MDE <= 1.0c; F-MDE <= 1.0c. Verdict condition: F (the far-future innovation). Cost
  hurdle: the maker's reward minute inside the touch on the rewarded subset of the pairs against the adverse selection
  of the next 20 minutes (gross; counts only; no verdict). Extends: a new per-day streaming reader over `quotes/`
  (shared by CH222 and CH223; < 300 MB). Embargo: `xvenue` to 11-04; `kxbook` new, to the later of LT10's analysis
  commit and 2026-12-04T00:00Z. Disclosure at the pin: E009's and E010's results were seen (`informed (E009)`); the
  design text's freeze commit before 2026-11-03T02:00Z is the proof the states were chosen blind.
- **CH223 (the other venue's makers flinch first).** Unit: pair x origin with `|dk1| < 1c` over `[t - 10, t]`. State:
  `pull` (Kalshi spread widened >= 2c or a touch size fell >= 50% in the window); `pull_side`. Decision time: the latest
  Kalshi line's receipt. Primary: expanding-past pair-demeaned OLS of `a = |midP_{t+20} - midP_t|` on `pull` with E009's
  seven, Polymarket's spread and sizes at `t`, Kalshi's spread at `t - 10`, hour dummies and tier as controls; one-sided
  > 0. Targets: `a`; M1 `c = pull_side x dP(+20)` (reported); M2 Polymarket's spread change at +20. Clustering as CH224;
  `DE_gate` 51. Planning MDE 0.33c / 0.18c; F-MDE 0.53c / 0.29c: a verdict condition if the census shows >= 7,500 pull
  origins, else a reported label (declared now). Census: pull origins a day and share (>= 1%, <= 15%); the hour-of-day
  share of pulls <= 50% in one hour (S21's gate); the within-pair AR of `pull` < 0.5; the rewarded share of the pairs;
  `n1_eff`; pessimistic MDE <= 0.5c; F-MDE printed. Verdict condition: as declared. Cost hurdle: the reward minute lost
  by stepping aside against the adverse selection avoided (gross; counts only). Extends: the shared reader. Embargo:
  `xvenue`; `kxbook`.
- **CH222 (the venue that traded first).** Unit: pair x origin with `|dk1| >= 1c` over `[t - 10, t]`. State: `traded`
  (`k_last` changed in the window); `size_eaten`. Decision time: the latest Kalshi line's receipt. Primary:
  expanding-past pair-demeaned OLS of `c = sign(dk1) x dP(+20)` on `traded` with E009's seven, Polymarket's spread and
  sizes, hour dummies and tier as controls; one-sided > 0. Targets: `c` at +20; M1 at +60; M2 the slope on
  `size_eaten` within traded moves. Clustering as CH224; `DE_gate` 51. Planning MDE 0.47c / 0.36c; F-MDE 0.70c / 0.53c:
  **a reported label at the planning counts**, a verdict condition only if the census `n1_eff` >= 16,000 (declared
  now). Census: Kalshi moves >= 1c a day; the traded share in [15%, 85%]; the hour-of-day share of traded flags <= 50%
  in one hour (S20); the within-pair SD of `traded` >= 0.2 in >= 50% of pairs with >= 20 moves; `size_eaten`
  non-missing share; `n1_eff`, `n2_eff`; pessimistic MDE <= 0.5c; F-MDE printed. Verdict condition: as declared. Cost
  hurdle: E009's own executable metric restricted to traded moves (reported). Extends: the shared reader. Embargo:
  `xvenue`; `kxbook`.
- **CH225 (the slow sibling; sports arm, on the owner's decision).** Unit: matched game x pre-game capture k x
  Polymarket sibling. State: `z unabsorbed` (the sibling's own de-vigged line move over `(k - 1, k]` minus its own mid
  change, from the last ESPN poll received before capture k). Decision time: the max of the poll's `recv_utc` and the
  row's `received_utc`. Primary: two-way demeaned (market; game x slot) expanding-past OLS of `c2 = mid_{k+1} - mid_k`
  (signed as the sibling's line moved) on `z unabsorbed` with the sibling's own change, its level gap, spread, `log1p
  volume24hr`, hours to kick-off and sibling-type dummies as controls; one-sided > 0. Targets: `c2`; M1 the change to
  the last pre-game capture; M2 the sibling's spread change at k + 1. Clustering: game; `DE_gate` 3.0. Planning MDE
  0.87c / 0.49c at 21 days, 0.62c / 0.35c at 42: **proposed with a 42-day window or not at all** (CH205's rule);
  F-MDE 0.92c / 0.52c at 42 days, a reported label. Census (the ESPN stream's day files from its install plus 10 days;
  the sealed captures of the same days): matched games >= 30 a day; games with >= 2 siblings >= 15 a day; precision
  >= 0.9 on 50 audited matches; sibling-slots with a nonzero line move >= 20%; permutable share >= 0.5; the residual
  SD after two-way demeaning printed; pessimistic MDE at 42 days <= 0.5c. Verdict condition: none beyond Holm (F
  reported). Cost hurdle: the sports round trip 5.2c against the slow sibling's catch-up (reported; the
  hold-to-final leg saves the exit). Extends: CH205's matcher (extended to spread and total questions) and a light
  reader over `stream_espn_odds/` and the captures. Embargo: `steam` (CH205's token, requested only when a sports test
  is drafted), covering `st_unabsorbed` and its siblings.

**How the families would be registered.**
- **A. The fine-clock family, LT10 (CH222, CH223, CH224).** One Holm family, k <= 3, on E009's stream after E010's
  analysis commit, design text frozen before 2026-11-03T02:00Z, census on the worn days, registration never before
  2026-11-10T00:00Z, 21 days, single analysis >= 36 h after the end; dropped whole if the poller stops or the pair gate
  fails; one shared reader; the three column sets go to the engine's `xvenue` isolate after 11-04 under `kxbook` once
  LT10 registers (no isolating challenger of the three before LT10's date). CH230's map decides whether the census runs
  on one venue or three.
- **B. The sports arm (CH225, CH226).** Registered only on the owner's decision, as a sports family with CH205 under the
  42-day rule; CH226 is a map first and a test only on its count.
- **C-D. Engine-first (CH227-CH229, CH231).** Challenger families and columns with the tokens named (`xvenue` to 11-04;
  `kxbook` conditional; none for `ruleedit`, `xent`, `gamestate`); each raises K and is built only with a real prior
  (the builder's rule): `ruleedit` on `res_7d` first, `xent` as a calibration moderator, `xvenue2` columns inside the
  existing isolate, `gamestate` on the sports breakdown.

**What is honest to say about all of them.** The streams the brief points at are other venues' feeds, and the
arithmetic of this programme's own planning rules says that at the capture clock no cross-venue join reaches a test on
the pairs that exist, which is why rounds 13 and 14 sent them to the engine. This round's contribution is to say where
they *can* be tested with data the host already captures: on the one fine-clock panel that has Polymarket on it, where
each pair gives 144 origins a day and the other venue's book, not its mid, carries the three states nobody has read
(whether its move was paid for, whether its makers left before any move, whether its spread just changed what a hedged
Polymarket quote costs). Each has a twin thirty minutes later, each is read from lines the poller already writes, and
each states the count that kills it. The sports arm is dense by construction and is written so it can be lifted the
day the owner decides; the capture-clock families are columns with their coverage stated. Nothing here is edge until it
has gone through census, frozen rules, prospective registration and an economic check at recorded prices; E009's own
result, due after 2026-11-03, is the first thing that will say whether the fine clock has anything in it at all, and
every family-A entry is labelled `informed (E009)` for that reason.

---

## 4. Ideas considered and rejected, and why

### 4.0 Dropped as duplicates or closed (this round's own candidates, each with the record that closes it)

Every idea below was drafted or seriously considered for this round and dropped before writing because an earlier CH,
a closed test, a null, an engine family or a rule already owns it. A closed idea is re-proposed only with a genuinely
new mechanism, clock, population or join, and none of these had one.

| Candidate this round | Why dropped | The record |
|---|---|---|
| The book's line moved and Polymarket's pre-game price did not (any form: moneyline, the open-to-current drift, the 10-minute clock) | held, owned | CH205 (steam; sports scope, the owner's call); its engine family `steam` and 42-day rule are the precedent CH225 adopts |
| Minutes since the last cross-venue move, the three venues' dispersion, settlement elsewhere as a label (PredictIt, Smarkets, Kalshi) | owned, engine-first | CH208 (`xvenue2` timing extension); CH134 (Kalshi settlement); CH229 adds only the published close and the book-cause shadows |
| The venue's attention frontier: entry into the top-N by 24 h volume (the `gamma_rules` frame's own boundary) as a crossing | duplicate | CH176 (the front page); round 14's 4.0 ("if the ordering is by volume it is CH193's `volume_num` object"); the `regime` family dropped |
| Unconfirmed Polymarket moves revert; the lead lives where the spread is tighter; the pair at birth | owned | CH165, CH166, CH130; E009's frozen M1 already carries `r1 -0.230` with `dk1 +0.339` |
| The postponement clause triggered by ESPN's `state` (a rules-text x external-event join) | rare, owned | CH07 (postponement optionality); tens a month at most (unprobed); pattern 1 |
| Moneyline against spread and total as a level inconsistency | owned | CH14; CH225 keeps only the within-game x slot contrast with the book's joint move as the instrument |
| The decided carry defined by the price reaching 0.97; zombie quotes after a final; the end-of-game hope premium | owned | CH01, CH04, CH23; CH226 keeps only the price-free clock and the wait map |
| A category-level news clock from PredictIt's minute changes or the monitor (breadth); mention baskets | closed | round 14's 4.0 ("breadth", rounds 8-9; CH208); CB12-M mention baskets (speech clocks) |
| Smarkets' lay-side or top-3 depth as a moderator at the capture clock; PredictIt as a bias-corrected twin | closed frame | CB15-P (37 pairs in 12 events); builder row 4 ("coverage likely tiny"); re-opened here only at the fine clock, and only after CH230's count |
| The rule-edit event as a test (market or event description changed; the slot after against the other eleven) | arithmetic | 0.97c at 250 edits in 21 days, 0.54c at 1,000; no twin; CB18-S closed silent edits; CH228 is the column |
| The resolution-source host class; UMA bond / liveness classes; rule specificity as a level | killed / owned | CH199 (`rulesrc` 19.9% < 30%), CH207, CH63 |
| A DraftKings line taken off the board as a test (pending-information clock) | count | tens a week (unprobed); DE 3 at 200 events gives 2.3c on a spread target; CH231's `gs_off_board` column and CH223's sports twin |
| PredictIt's published close as a test | frame | 37 pairs; CH229's column |
| The three-venue vote (the number of other venues confirming a Polymarket move) | owned | CH165 (confirmation) and CH208 (dispersion); E009's M1 |
| Cross-venue rule divergence as a gap explanation | owned | CH64 (rule-divergence twins), CH48 |
| A new collector for PredictIt- or Smarkets-matched Polymarket books | rule | LT9's "no new collector"; CH230 proposes a pair-list change to the existing poller instead, as an owner decision |
| In-game score-lag prints on the monitor (the print after the score at a stale price) | rule 1; sports | monitor prints are not units (round 14's rule 1); the sweeps lack most sports tokens (fact 3); CH231's columns |
| Reward-rate re-ratings and sponsor arrivals on the `reward_params` feed | rare | round 14's 4.1 ("band or rate re-ratings"); "the sponsor's side" a slow trait; LT9 owns the feed's test-grade objects (CH212-CH215) |
| Any sweep, sidecar or rewarded-panel state at the capture clock under a new name | owned by LT8 / LT9 | CH202-CH204 (LT8), CH212-CH215 (LT9), their tokens `quietbook`, `swclock`, `sched`, `bandbreak`, `pool`, `rwblink`, `rwend`; nothing here reads them |
| The LT4 / LT5 / LT6 / LT7 drops under any new name | closed at census | round 14's 0.1 table; a re-proposal needs a new panel, not a new name; the fine-clock lane is the one new panel this round names, and it is E009's |
| Anything wallet-level | sealed / frozen | E026 registered, its modules frozen to 12-07 |

### 4.1 Ideas rejected on the design rules, and why

- **Any cross-venue state at the capture clock as a test** (the gap, the lead, the minute of the move, the entity
  clock, the published close, the three venues' dispersion, the hedge ratio as a level). The frame arithmetic of 0.1:
  >= 1,100 pairs for a class contrast at 0.5c, >= 800 for a mid slope; the three venues offer at most a few hundred
  (fact 7). Engine columns (CH227, CH229) and twins reported uncounted; rule 6 of round 14 and rule 7 of round 13 stand,
  now with the number that enforces them.
- **Any fine-clock state read from the Polymarket side alone** (the depth fade at 120 s, the touch's own withdrawal,
  Polymarket's trade / quote split). CH133 owns the fade; a Polymarket-side state at 120 s with a Polymarket target is a
  single-venue microstructure test the sweeps cannot serve and the poller serves only on the pairs; every family-A
  state is the *other* venue's object, with Polymarket's own contemporaneous change as a control.
- **Fine-clock states whose cause is a venue cadence** (Kalshi's `last_price` refreshing on a schedule, size re-posts by
  a bot's cycle, the pair refresh's daily cadence). Round 13's rule 8; CH222 and CH223 carry hour-of-day gates (S20,
  S21) that kill them if their events are a cron; the pair refresh is disclosed as the one cadence the lane cannot
  avoid and it is not a state.
- **Rare-event states on the keyless streams** (rule edits as events, `endDate` edits seen hourly, a line taken off the
  board, a postponement, a sponsor's arrival, a PredictIt contract's settlement). Pattern 1; each is an engine column
  where it has a home (CH228, CH231) or a reported label (CH226's twin).
- **Level states on the streams** (the rules' specificity, the UMA parameters, the resolution source, PredictIt's
  staleness, Smarkets' depth, the spread ratio as a level, the open-to-current drift as a level). Pattern 3 (V's death,
  LT7's F-MDE); CH224 reads the spread's *innovation* with the level as a control; CH228 reads an edit's age as a level
  only for the engine, where the rule does not bind.
- **Sports tests without the owner's decision.** CH225 and CH226 are written to be lifted, not registered; their
  ex-sports prior is 0.0 by construction and the file says so in the shortlist.
- **The monitor's sports prints as units** (score-lag prints, in-game hope at the print clock). Round 14's rule 1 and
  fact 3 (half the sports prints have no swept touch); CH231 reads the in-game state at the capture clock only.
- **A venue-clock state as a primary without the mechanism** (hour-of-final dummies, weekends, the reward epoch). Rule
  8; CH226 admits an hour class only through a pre-built wait map and discloses the rule; the challenger decides.
- **Collection changes as part of a design** (a new poller, a bigger pair list, a faster ESPN cadence, Polymarket books
  for PredictIt matches). CH230 is a map and an owner decision, separate from LT10's design; LT10 is written to run on
  the pair list as it is.
- **Taker routes as primaries anywhere.** 2.9-7.2c round trips (5.2c in sports) against grosses of a fraction of a
  cent at 20 minutes; every taker route here is reported, never a verdict; E009's own `trade` rule is the only executable
  metric the fine-clock lane quotes.
- **Maker mark-out objects** (adverse selection judged on fills). J4-R's and CB13-T's holdouts; E025 part B; every
  maker route here is gross, no fills, with the reward formula's arithmetic as the economic check where the pair is
  rewarded.
- **E009 / E010 moderators during their window** and any read of `cross_venue_live/` before E010's analysis commit. The
  seal; the design-text freeze before 2026-11-03T02:00Z is what keeps the states blind.
- **Decided-but-unresolved carry, longshot ask-selling, round-number walls, tick-regime discounts, reward cliffs,
  holding rewards, genesis, seed anchors, series rolls and base rates, mention baskets, external anchors, barrier
  confusion, quoter grain, wake-up prints, breathing book, mint share, turnover, synchronous prints, exit pressure, cost
  maps, quoted against traded, walked flow, trains, attention surges, breadth, class-conditioned longshots, arrivals and
  cancellations, the age of the move, opens and closes, concentration, hollow liquidity, program against human,
  last-mid proxy, front page, silent edits, races, jump or grind, high-water mark, overhang, alone or with the crowd,
  the farmer's choice, clips, the makers' vote, deadline moves, sibling birth, provenance, overdue, grind at the capture
  clock, the hour-held move, implied against realised, absorbed flow, resistance, patient money, the last-print anchor,
  calendar theta, the resolution-source class, two minutes of quote news, reward yield, the sweep clock, the quiet
  book, the market's own clock, steam, the reward start, desk-set dispute insurance, the minute of the news, the farmer
  touch, two minutes before the origin, the ladder that travelled, the display's omission, the band break, the pool
  splits, the scheduled end, large prints without a sample, row quality, the display's disagreement, the touched book,
  dormancy, the siblings' proposal window.** CH01-CH221: not re-proposed; where an idea touches one, the parent is named
  and the new clock, population, state or join is stated (CH222 on E009/E010/CH165/CH166/CH208/CH133; CH223 on
  CH133/CH203/E009/CH166; CH224 on CH166/CH115/CH45/CH213/E009; CH225 on CH14/CH205/CH29/CH48; CH226 on
  CH01/CH04/CH134/CH208/CH23/CH167; CH227 on CH208/CH97/CH141/CH114/CH25; CH228 on CH08/CH177/CH63/CH199/CH207; CH229 on
  CH114/CH25/CH208/CH218; CH230 on E009/E010/CH208/CH130; CH231 on CH23/CH44/CH205/CH04/CH226).

---

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
`NEW_STREAMS_2026-10-19.md` (sections 1-5: the inventory, the four streams' sources, slots and fields, the dry-run
counts, the failure modes and caveats, the deploy steps and the "no registered experiment reads these streams" rule);
`COLLECTION_HOST.md` (the host, jobs, the monitors under `supervise.sh`, the resize record and the restart audit);
`CROSS_VENUE_LIVE.md` (the poller's pair list, poll, predictions, outcomes, the frozen spec's coefficients, the pilot's
counts, the resource notes, E010); the ledger's E009 entry (population, origins, inference, the executable metric),
its 10-13 operational note on retired pairs and request counts, its 10-22 resize line (the streams' last and first
polls), and its tail (the `dispgap` / `dormant` builds and censuses, the LT7 withdrawals, the LT9 tokens, the timestamp
correction); `signal_engine/STATUS.md` (10-23 00:25 UTC+1: the embargo table, K, the open list, the LT7 closure);
`signal_engine/CANDIDATES.md` (rows 3, 4, 17; round 5's "not requested"; round 6's LT9 tokens; the round-13 idea notes
on `steam` and `xvenue2`); `signal_engine/DESIGN_V1.md` section 3 (families, the `xvenue` clock and coverage) and the
section headings of 8, 16, 22 and 26; `signal_engine/NORTH_STAR.md`; `LIVE_TESTS_9.md` section 0 (the summary table,
the family, the window, the declared odds) and its section list; `CREATIVE_BATCH_13.md` H6-H8 (the monitor's sports
share and the sweeps' sports coverage); `EXECUTION_COSTS.md` (the sports row, the fee rates and the `sports_fees_v2`
count) and `COST_MODEL.md` (the sports fee history and the by-category table); `RESOLUTION_DEV_STUDY.md` (the frame's
category counts); `LIVE_TRADE_MONITOR.md` (the category labels); the four stream modules' docstrings
(`streams/predictit.py`, `smarkets.py`, `espn_odds.py`, `gamma_rules.py`: the fields kept per key, the source clocks,
the frame rule); `cross_venue_live.py`'s Kalshi field names (`k_last`, `k_bid`, `k_ask`, the sizes); `ext_sidecar.py`'s
column list (no sports fields); `backend/astrolabe/signal_engine/config.py`'s `EMBARGO` dates (the token names from
STATUS); `CREATIVE_HYPOTHESES_2026-10-28.md` (round 14: the whole of sections 0-1 and 3-5, the CH212 entry's shape, and
its structural facts 1-10 re-used where unchanged and named as such); `CREATIVE_HYPOTHESES_2026-10-27.md` (CH202-CH205,
CH208, CH209 in full); the lead paragraphs of CH01, CH04, CH07, CH08, CH14, CH23, CH25, CH29, CH44, CH48, CH63, CH64,
CH97, CH114, CH115, CH130, CH133, CH134, CH141, CH165, CH166, CH167, CH172, CH176, CH177, CH193, CH199, CH207, CH216 and
CH221, and the lead sentences of CH01-CH221 from all fourteen rounds (for the duplicates table). Still no host probe,
no network and no data-dumps read. Every count is as the named document states it on 2026-10-23; nothing was
recomputed.

### 5.2 External literature (named, not fetched)
Glosten and Milgrom 1985 (the maker's update on trades); Hasbrouck 1991 (the information content of trades) and 1995
(information shares across venues); Cont, Kukanov and Stoikov 2014 (order-flow imbalance including cancellations);
Levitt 2004 (why sportsbooks move lines); Kaunitz, Zhou and Kreiner 2017 (closing-line value, as CH205 cites it);
Stern 1991 (the margin model that converts spreads to win probabilities, as CH14 cites it); Kaniel and Liu 2006 and
Rosu 2009 (patient orders, as CH203 cites them).
