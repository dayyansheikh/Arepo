# Creative hypotheses, round 18: the payer's return, the listing batch, the loser's exit and the headline (2026-11-01)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-24 from 03:44Z on parent
`dab6c593` (`chore/arepo-claude-setup`) in the worktree `feat/creative-r18`; the file carries the round's planned date as
earlier rounds did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59),
round 3 `-17.md` (CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130),
round 7 `-21.md` (CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md`
(CH169-CH179), round 11 `-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201), round 13 `-27.md` (CH202-CH211), round 14
`-28.md` (CH212-CH221), round 15 `-29.md` (CH222-CH231), round 16 `-30.md` (CH232-CH241), round 17 `-31.md` (CH242-CH251);
this file starts at **CH252** and repeats none of them. Where an idea builds on an earlier one, the parent is named and
the new mechanism, clock, population or join is stated. Every number quoted from an AREPO document is a development,
census, map or probe result, not evidence. One file; no code, no queue specs, no other commits. **No network request, no
host probe (no `ssh oracle`) and no `data-dumps` read were used for this round** (by instruction); every count below is
taken from a named AREPO document (`EXPERIMENT_LEDGER.md`'s tail from 2026-10-22 through the LT12 design-text freeze
entry of 10-23 ~23:45Z, `CH240_MAP_2026-10-23.md`, `CH251_MAP_2026-10-23.md`, `LIVE_TESTS_11.md` sections 0 and 7,
`LIVE_TESTS_12.md` sections 0, 4, 5 and 7, `signal_engine/STATUS.md` (10-24 00:20 UTC+1), `signal_engine/NORTH_STAR.md`,
`signal_engine/CANDIDATES.md` (the round 12-17 notes, the "not candidates" list, the builder table rows 1-26, the LT11 and
LT12 freeze requests), `signal_engine/DESIGN_V1.md` sections 2-3, `EXECUTION_COSTS.md`, `COST_MODEL.md`,
`NEW_STREAMS_2026-10-19.md`, `COLLECTION_HOST.md`, `LIVE_TRADE_MONITOR.md`, `CROSS_VENUE_LIVE.md`, rounds 14-17's design
rules and round 17's sections 0-5) and is named as such. Two facts come from the orchestrator's brief for this round
and sit on the parent branch after this worktree's branch point (commits `bacc8e9c` and `6f0071e7`), not in this
worktree's ledger; they are marked **(brief)**. Where no count exists the entry is marked **unprobed** and the
pre-registration census is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities 2026-10-19 and 10-21; orchestrator brief for round 18).** Original
hypotheses about how money could be made on Polymarket lead the programme, ahead of textbook ideas, and the programme's
dominant failure mode is still the pre-registration census: too few units a capture, too few distinct events, a held or
scheduled share under its line, an MDE above the floor. **LT5, LT6, LT7 and LT8 closed with zero tests**; LT11 is frozen
with its designer's P(no test) about 0.35; **LT12 is frozen with k <= 2** (CH245 the mirror at 0.30, CH244 the farmed
half at 0.15, P(no test) about 0.60; CH243 the fee left at challenger R1 because a label-only F chosen for power is
rejected). Two batch tests died this week on their *sources*: **CB8-W** at its smoke (5 eligible worn markets of 192
found against 20 required; ledger 2026-10-22) and **CB8-B** at its book-coverage audit (pmxt books on 87 of 119
market-days, 73.1% < 90%: "not testable (source unavailable)", counted; **brief**). So this round is **census-first** as
rounds 16 and 17 were, with three further constraints from the brief: (a) prefer states on streams the host already
captures **densely and completely** (the 2 h captures and sidecar, the two sweeps a pass, the engine's own per-capture
stores; the monitor and the poller only as engine inputs under round 14's rules 1 and 6), with many units a capture and
many distinct events; (b) give, for every idea, the census line that would kill it and an honest prior that it survives
the census and that it would replicate; (c) name the LT13 candidates for one Holm family with k <= 3 separately from
the engine-first families (NORTH_STAR: champion = momentum + market state; challengers add one family each; scored at
every capture); and (d) include at least two genuinely new mechanisms, each with its mechanism, loser, persistence,
clock, population, dependence, economic check and falsifier. Round 14's design rules 1-11, round 15's 12-14, round 16's
15-17 and round 17's 18-20 **bind here unchanged**; this round adds three (0.2). Category-agnostic, sports as a parameter
(the owner's call). No data-rights topic is raised. Nothing here reads any registered live test's objects before its
analysis; nothing here reads LT11's or LT12's window captures for any census.

**What this round does differently from round 17.** Round 17 turned five facts about the venue's structure (two books
for one claim, the fee on the crosser only, the reward per market inside a per-event constraint, the third resolution
value, the maker's payer) into dated events, and LT12 took two of them. This round looks in four places those seventeen
rounds have walked past: **the clock of the quote's return** (the *widening* of a spread, not the print, as the dated
event, and who is paid to come back: the per-fill rebate exists only on fee-on markets, so the unrewarded panel splits
into makers paid per fill and makers paid nothing); **latent sets the venue's own fields imply but no key names** (markets
created in the same minute across different events are one listing batch quoted by one set of makers; the market makers'
balance sheet is shared across categories, so a crypto shock is an exogenous shock to politics' liquidity); **losses and
headlines as shocks to *other* markets** (the collapse of a favourite is a loss to holders who also hold the category's
other favourites; a leader change in a race is a headline somebody is willing to buy); and **fields and stores the engine
already holds but nobody reads as states** (the event's comment count, the `accepting_orders` flag, the engine's own
disagreement across its challengers, the fee's incidence per dollar staked). Each gives a dated, side-specific or
panel-specific prediction; none is momentum, reversal or imbalance under a new name; the two that clear the census
arithmetic on paper are the first two, and they are the LT13 shortlist.

**What changed since round 17 (from the ledger's 10-23 ~17:20Z LT11 freeze to the LT12 freeze at ~23:45Z, STATUS 10-24
00:20 UTC+1, CANDIDATES' round-17 note and freeze requests, `CH251_MAP_2026-10-23.md`, `LIVE_TESTS_12.md`, the brief).**
- **LT11 is FROZEN** (3627d7fd, sha256 `991100db…3583`, merged 1f353ca6; CH234 0.35, CH233 0.40, CH232 0.10; P(no test)
  about 0.35; window 11-18..12-09, analysis on or after 12-10T12:00Z, census seal `[10-28, 11-07)`); tokens `dollarw`,
  `nrslack`, `bandside`, `attrlimit_lt11` applied to 2026-12-12 (18:20Z). Its code-freeze check returned **REJECT** (7
  must-fix, mostly the size-check worlds; 22:50Z); the fixes were applied and the re-check returned ACCEPT_WITH_FIXES
  with a registered-seed test run disclosed as an uninformative deviation, to be fixed before merge (**brief**).
- **The CH251 map ran (q0700, 111 captures of [10-13, 10-23), 9.25 covered days; counts only, k = 0):** two-member
  complete pairs **639** a capture (rr 238 / ru 19 / uu 382; retention 1.000; same-slot spread-innovation correlation
  0.38 / 0.11 / 0.64); mixed ladders 1,363 (976 complete; unrewarded member units 5,009); fee-free traded movers mean
  **346 but medians 64 / 7** (not stationary over the span); the 2 x 2 of fee x reward in open binary rows a capture:
  **fee-free rewarded 2,690 (median 655), fee-free unrewarded 4,577 (median 555), fee-on rewarded 6,722, fee-on
  unrewarded 11,267** (shares 0.107 / 0.181 / 0.266 / 0.446; crypto has no fee-free rows; sports is 97.7% fee-on
  unrewarded, 231,473 rows a capture); movers in two-member events 63.5 (`twin_printed` 7%). Not mapped: CH242 (no label
  store in the captures), CH246 (no rules text), the tier-matched controls (no tier definition in the captures).
- **CH242 `p3` was killed at its census by the engine** (22:50Z; the engine's own label store, 132,539 final records of
  the 10-12..10-23 `res_7d` population): **2 splits in 46,596 non-sports resolutions (0.004%)**, 586 in 85,943 sports
  (0.68%); splits sit at last-origin mids 0.3-0.5, none at a cheap side <= 0.05. The three-valued reference row is not
  built. The same census is the only count of resolution *density* this round can quote (fact 4 below).
- **LT12 was drafted, reviewed and FROZEN the same night** (`LIVE_TESTS_12.md` at 01d6014c, sha256 `a543db63…b62d`,
  merged 2f819bf6; one Holm family, **k <= 2: CH245 and CH244**; CH243 dropped at R1 MUST 1; fast lane: census seal
  `[11-07, 11-17)`, window 12-10..12-31, analysis on or after 2027-01-01T12:00Z; priors 0.30 / 0.15; P(no test) about
  0.60; expected valid verdicts about 0.2). Tokens `mirror`, `mixedlad`, `attrlimit_lt12` requested (no `feeclass`). The
  LT12 census gates (section 7) are the reference for every gate this round states: projected thin units >= 46,872 (>=
  186 a capture) with distinct events >= 500 and events with >= 48 units >= 100 unprojected, `G_eff` >= 15, same-slot
  correlation, identification, leverage, `VIF_w` <= 2.0 on demeaned regressors, placebo coverage >= 90%, `r_gate` <= 0.3,
  slope and F-MDE <= 1.0c.
- **CB8-B** ran its declared variant (q0165b: 665 markets, 791 strikes; q0166b promoted with the coverage audit first,
  PASS iff >= 90%), then failed that audit at 73.1% (**brief**). **CB4 closewin and CB5 listings extracts** had been
  refused every pass since 10-17 (a cap line missed by the 40 GiB raise); nothing lost, delay only; fixed.
- **The engine (STATUS 10-24 00:20 UTC+1):** the input-coverage monitor is live (9 of 72 captures over six days would
  have alerted, all from the two missed passes of 10-21 00:31Z / 02:31Z); `tilt` tables 82 of 134 (se24 / se25 fit at
  the 10-24 refit); three days scored: **se1 (LightGBM, base families) is ahead of the logistic champion by about 0.05
  nats at 2 h, 0.06 at 6 h and 0.07 at 24 h**, a learner effect, no promotion before about 11-04; for `res_7d` the
  champion is no better than the market price itself; the 10-23 refit peaked at 3,204 MB RSS; `parentsib` (0.15% of
  eligible non-sports rows have a parent) and `p3` killed at census; the builder asks for families with a real prior
  only, since each raises K.
- **Ops:** E022 registered (window 10-26..11-16); E026's modules frozen to 12-07; E009 / E010's `cross_venue_live/`
  sealed to 11-03 (the `xv_quotes/` successor and LT10's `kxbook` to 12-04); E011's `surprise_live/` to 11-10; snapshot
  retention 8 days on the host, nightly archive to GitHub releases.

### 0.1 The census arithmetic, stated once: what a live test needs per capture

Round 16's 0.1 table binds unchanged (the effective count at which the pessimistic MDE equals the floor, and the units
a capture it implies over 21 days, 252 captures, at the planning effective share 0.8): a 2 h mid class contrast needs
about 690 units a capture in the smaller class (1,740 with F); a whole-panel mid slope about 1,680 (4,200 with F); a
mover-family mid slope at E022's design effect 335 (745 with F); a spread slope about 105 (260 with F); a 1 : 11 spread
class contrast about 24 event market-days a capture (60 with F). Round 17 added the two-member event as the one object
with a stratum by construction. This round adds two readings. **First, a *common* state is poor by arithmetic:** a state
shared by every unit of a category in a slot (a crypto shock, a category's losses, the venue tilt) has as many effective
clusters as category-days, about **170 in 21 days** for eight non-sports ex-crypto categories; at 0.8 of that, a spread
class contrast's MDE is `3.47 x 2c / sqrt(136) x 1.5 x sqrt(1.3)` = **1.02c** and its F-MDE **1.61c**, both over the
floor before any unit is counted, so such states are engine-first whatever their unit count (rule 22; the `regime`
family's REVISE of 2026-10-21 said the same in the engine's words). **Second, a *widening* is a dense dated event on
every two-sided row:** the touch is unchanged in 90% of books within a pass (round 14 fact 4), but across a 2 h interval
the spread changes on a large share of rows; at a planning widening share of 0.10 (**unprobed**; CH261 counts it) the
fee-free unrewarded cell alone gives 55 (median capture) to 460 (mean capture) widening units a capture, and the
fee-on unrewarded cell about 1,100, so a panel contrast on widenings (CH252) clears the spread table at the median
capture if the computed design effect is near the LT11 formula's value for standalone markets (about 6-11) and fails
at the planning convention 31 unless the mean count holds. Both readings steer the shortlist: the first removes two
mechanisms from the live lane before they are written; the second is why the payer's return is the one live candidate
here with margin.

### 0.2 Design rules (round 14's 1-11, round 15's 12-14, round 16's 15-17 and round 17's 18-20 bind unchanged; three additions)

21. **The latent join.** A join the venue's keys do not name (a creation batch by `created_at`; any later signature
    join) is pinned before any count: the window, the minimum size, the cross-event rule, the cap and the completeness
    rule (rule 16's analogue: a batch-capture with fewer than 60% of its mates two-sided at k - 1 and k is `unavailable`,
    counted, never filled); it carries a pseudo-join placebo (mates drawn from the same category and age decile, created
    at least 7 days apart, the same count), whose coverage is a census gate (>= 90% of units) and whose slope is an
    analysis condition (|slope| < half the join's); and mates in the unit's own event are excluded wherever LT11 or LT12
    owns the event join.
22. **Common states are engine-first by arithmetic.** A state shared by every unit of a category or of the venue in a
    slot has as many effective clusters as category-days (0.1), so its spread class MDE is about 1.0c and its F-MDE about
    1.6c in a 21-day window; such states are engine-first and said so, unless a design declares before its census a
    shock-level cluster count >= 500 that a 21-day window can reach, which none below can. The engine's walk-forward
    scores, which accumulate slots over months, are where a common state is read.
23. **Other markets' public facts are inputs; the unit's own outcome never is.** A state may read another market's
    price collapse, proposal or resolution received before the origin (a public fact at decision time), with the unit's
    own event excluded where a sibling rule owns it (CH67, CH221); no live primary reads the unit's own resolution (rule
    19 restated), and the category's *scheduled* resolutions (`end_date`) enter only as a control.

**Hygiene that binds every idea** (round 14's paragraph applies: decision time is the latest input's own receipt;
targets start after it; nothing reads outcome fields of the unit except engine-first `res_7d` features; the primary is a
within-stratum contrast or slope by expanding-past demeaned OLS, the Freedman-Lane gate in the census-fixed stratum is
binding, the liquidity-tier correlation gate (|corr| <= 0.5 within and pooled against `log1p liquidity` and `z log rv24`)
and the AR(0.9) scenarios bind, and F in LT7's one-rule form is a verdict condition where its census F-MDE is under the
target's floor; a label-only F chosen for power is rejected (LT11 R1 A4, LT12 R1 MUST 1)). Sports stays a parameter
(the sidecar's `fee_type` plus CB17's frozen list); every non-sports entry reports its sports arm uncounted. Nothing here
is a maker mark-out object; J4-R's and CB13-T's holdouts are not read. Nothing here reads LT11's objects (`xw`, `cl_sib`,
`xo`), LT12's (`zs_D`, `shock x unrew`), their twins or targets, or LT11's and LT12's window captures.

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader over the rows,
sidecar or engine stores the host already writes with the population counted by a named probe or map; 4 = pure reader,
population bounded above by a named count; 3 = pure reader with an unprobed population, or a join or map first; 2 = a
stream whose coverage is unprobed, or a collection change; 1 = fetches or weeks. **Priors** are two numbers, both my
judgement: P(census) = the probability the idea passes its own census as written; P(replicates) = the probability that,
given a Supported verdict, the effect would hold on a second prospective window in the predicted direction above the
floor (for engine-first ideas: that the family's isolate beats se1 on its target over 28 days).

**Planning-MDE arithmetic (round 14's, stated once).** Class contrast: `MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x
sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`, times `sqrt(2)` for a contrast of two within-market contrasts (rule 20);
slope per SD of a continuous state times the tercile gap (about 2.2 SD): `MDE = 3.47 x SD / sqrt(n_eff) x sqrt(DE_gate)
x 1.5 x sqrt(VIF_w) x gap`. `n_eff` = 80% of raw (planning). `DE_gate`: 31 (events capped at <= 10 members), 51
(uncapped), 6.196 (mover families), 3.0 (one game one cluster), and the LT11 formula `max(floor, 1 + (m_21 - 1) x 0.02)`
where the cluster is small (a standalone market over 21 days gives 6.0; a two-member event 11; both quoted). `VIF_w` 1.3
for row and sidecar states, 1.5 for book states. SDs: 2 h change 4c; |2 h move| 3c; spread change 2c. **F-MDE** = `MDE x
sqrt(2 / (1 - max(0, r_w)))` (planning `r_w` 0.2 gives x 1.58), capped at the floor as a verdict condition. Every MDE is
quoted at the low and high planning counts and at a quarter of the low one.

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture 42,161-51,790 (DESIGN_V1 sections 3 and 16, as rounds 13-17 quoted); 46,448 on the
   10-20 20:31Z capture (DESIGN_V1 section 3); non-sports about 30,000 (derived); eligible non-sports on single captures
   18,232 (CH199's filter) and 18,349 (`parentsib`'s census, CANDIDATES row 25).
2. **The CH251 map (q0700; non-sports ex-crypto, per capture, 9.25 covered days):** the 2 x 2 rows and medians as 0
   states them; traded movers by cell 304 / 42 (fee-free rewarded / unrewarded) and 738 / 99 (fee-on); fee-free movers in
   a covered category-by-age cell 0.956; two-member pairs 639 complete, distinct events 292 / 139 / 592 over the span;
   mixed ladders 976 complete, distinct mixed events 2,304, status-liquidity correlation -0.05 / -0.09 (3-10 members),
   0.15 / 0.005 (11+); `volume_num` missing on a further 213 fee-free movers a capture. **Widenings and narrowings a
   capture by cell, creation batches, favourite collapses, leader flips, comment coverage and halts are all unprobed**
   (no map has counted them).
3. **The CH240 map (q0680, 10-16..10-22, per capture):** traded movers 1,239 (rewarded 1,021 / unrewarded 218),
   quote-only 2,466, `volume_num` unusable 851 (83% of sidecar rows NaN); neg-risk events 1,664 / 825 with 14,123 / 4,933
   member rows; complete event-captures about 1,833; rewarded outward first crossings of 0.10 / 0.90 about 79; the
   within-market-day SD of `w` >= 0.1 on 0.70 of mover market-days.
4. **Resolution density (the engine's CH242 census, CANDIDATES row 26; ledger 10-23 ~22:50Z):** 133,559 markets with
   ids from the 10-12..10-23 captures, 131,951 `resolved`, 588 `split_50_50`, 1,020 `not_found`; of 132,539 final
   records, non-sports 46,596 (crypto 37,695, finance 1,417), sports 85,943; by `min(p, 1 - p)` at the last origin: 21,516
   at <= 0.05, 24,258 in (0.05, 0.15], 20,110 in (0.15, 0.3], 66,655 in (0.3, 0.5]. **Derived, planning only:** non-sports
   ex-crypto resolved records about 8,900 over a population of markets ending in about twelve days, about 740 a day,
   about 60 a 2 h slot; the share whose leading side sat at >= 0.85 at its last origin and lost (a *surprise*) is
   **unprobed**; half of all resolutions (66,655) sat at a near coin-flip at their last origin (the crypto Up / Down
   series), so the non-sports ex-crypto surprise count is small by construction.
5. **The reward probe (q0601c; round 14 fact 2):** rewarded non-sports ex-crypto market-captures about 9,000-10,700 a
   capture; the field omitted on 62.2% of rows; switching markets 2,112-3,995 a day; 13,661 rewarded markets on the
   CLOB feed (10-20); the native pool $138k-182k a day; a two-sided minimum quote earns a median $0.05-1.00 a day on about
   $19 of capital. The programme is per market; `listed_carry24h_v2` with the feed adjudicating is the control reading
   (LT7 13.7; LT12's feed-disagreement gate).
6. **Fees, rebates and costs (`COST_MODEL.md` sections 2, 4 and 7; `EXECUTION_COSTS.md`):** taker fee `rate x p(1 - p)`,
   takers only (politics, finance, tech, mentions 0.04; sports, economics, culture, weather, other 0.05; crypto 0.07;
   geopolitics 0; some sports 0.03); makers never pay; the rebate pool is 25% (other), 15% (sports), 20% (crypto) of the
   market's taker fees, shared by fill share, **about 0.05-0.1c per filled share** (section 7's own words: "rebate
   magnitudes are small"); markets deployed before 2026-03-30 and still open are fee-free. Adverse selection on filled
   touch orders at a 1-2 h mark: 3.87c (< 1k), 2.45c (1k-10k), 2.04c (10k-100k), 0.39c (>= 100k) against half-spreads
   2.0 / 1.0 / 0.75 / 0.5c; queue fills within 1 h 1.9-4.3%, touch fills 4.1-26.3%, fill probability driven by `p_active`
   not queue length; $100 round trips p50 9.9 / 7.2 / 3.9 / 2.9c by tier; the 10-11 sweep's fee-free cell 727 of 37,225
   tokens at 1.8c; maker entry held to resolution costs about AS - h - rebate, 0.65c (10k-100k) or about 0 (>= 100k).
   **The fee's incidence per dollar staked (a reading of the formula, not a measurement):** the buyer of the side priced
   p stakes p a share and pays `rate x p(1 - p)`, so his fee is `rate x (1 - p)` of his stake: 3.8% (0.04) to 6.65%
   (0.07) a leg at p = 0.05, 0.2-0.35% at p = 0.95.
7. **Row and sidecar fields (round 14 rule 1 and fact 5; round 16 fact 6; `NEW_STREAMS` section 1):** rows carry the
   touch, `last_trade_price` (omitted on 56%), `volume24hr` (present on 22%), `liquidity`, `chg_1h/1d/1w`, `end_date`,
   `updated_at` (changed on 116,940 of 246,961 rows between two captures: it cannot date an edit), the event and
   neg-risk keys; the sidecar carries `received_utc`, `page_index`, `rewards_min_size`, `rewards_max_spread`,
   `clob_rewards`, `volume_num`, `open_interest`, `competitive`, **`accepting_orders`**, `order_min_size`,
   `order_price_min_tick_size`, **`created_at`**, `start_date`, `uma_resolution_statuses`, `fee_schedule`,
   `fees_enabled`, `series_slugs`, `parent_event_ids`, `event_volume`, `event_liquidity`, `event_open_interest` and the
   **event comment count** on every row. The engine's `participation` family (se16) holds event volume and liquidity
   and **excludes event open interest and comment counts** (CANDIDATES row 14; the reason is not stated there; CB17's use
   of the field is to be checked before any column reads it).
8. **Sweeps (round 14 fact 4):** 65,771 tokens a sweep, two a pass; `*_size_1`, `depth_*_1c/5c`, `n_*_levels`,
   `book_timestamp`, `tick_size`; the touch unchanged in 90% of books within a pass; `book0` coverage 92-94%; the `book` /
   `book0` tokens to 2027-02-14 (LT9) bar any isolating engine challenger on sweep columns.
9. **Streams the host runs (`COLLECTION_HOST.md`; `NEW_STREAMS` sections 1-2; `LIVE_TRADE_MONITOR.md`;
   `CROSS_VENUE_LIVE.md`):** the pass at :31 every 2 h (snapshot about 249k rows and sidecar, forecast, two sweeps, the
   trade sample of 2,000 active-frame markets, the flow screen, E011's score); the monitor (300 s cycles, every taker
   print >= $1,000 universe-wide with receipt time, side, size, price, hashed wallet and market context; about 160 prints
   an hour in the 10-12 pilot; evidence role `prospective_unregistered`); the E009 / E010 poller (120 s, at most 200
   matched Kalshi pairs, executable books both sides; sealed to 11-03); CB8-H holders (sealed); CB12-O; CB15-E election
   night books at 1 min (11-02..11-06); the four keyless streams (`predictit` 1 min, `smarkets` 5 min, `espn_odds` 10 min,
   `gamma_rules` hourly top-3,000 plus the 6-hourly frame); the engine's per-capture stores (quotes, features, aux tables
   on 134 captures, predictions of every active spec written before outcomes, label states). Binance klines are fetched
   per capture by se20 and closed before the capture start. Nothing here proposes a new collector.
10. **The engine's targets (DESIGN_V1 section 2):** `dir_2h / 6h / 24h` three-class on the Gamma mid (flat at |dmid| <=
    0.005), `res_7d` on markets ending within 7 days; base eligibility: binary, open, active, two-sided, spread <= 0.10,
    mid in [0.02, 0.98], no UMA proposal on the origin row; label states published daily. The 3-class target already
    carries a magnitude forecast (P(flat)); the market-price reference row exists for `res_7d`.
11. **The record this round must not repeat (CANDIDATES "not candidates"; the rounds' section 4s):** time of day,
    weekday and category as beta moderators null in HB1; neg-risk sums and sibling lead-lag null (E005, L1-L4, XM1-XM6);
    manipulation of any kind as a *route*, wash detection as alpha, holding rewards, maker-rebate loops and taker
    full-set arbitrage rejected in rounds 1-2; comment-feed *sentiment* rejected (worse data than CH24); the `regime`
    common-activity family dropped by the engine; CH41 already names volume, airdrop and wash farmers as a flow class;
    CH185 the scalper's size-matched opposite prints; CH93 the first crossing of 0.25 / 0.50 / 0.75 in 24 h; CH176 the
    front page's rank effects; CH157 attention measured by volume; CH98 the cash returned on resolution days; CH68 the
    winners' redeployment; CH67 the siblings' unwind; CH36 the same-key quoter sets; CH158 the venue tilt.

**Counts table (what was counted before each idea was written; the source named; `unprobed` where nothing was).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH252 | unrewarded non-sports ex-crypto market x capture with a widening >= 2 ticks at (k - 1, k], by fee class | rows a capture: fee-free unrewarded **4,577 (median 555)**, fee-on unrewarded 11,267; the widening share **unprobed** (planning 0.10: 55-460 and about 1,100 widening units a capture) | fact 2; CH251 |
| CH253 | non-sports ex-crypto market x capture in a cross-event creation batch (>= 3 markets within 120 s, >= 2 events), batch >= 60% complete | **unprobed** (planning 20-50% of eligible rows, 3,600-9,000 units a capture; batches hundreds to low thousands) | fact 7 (`created_at` on every row) |
| CH254 | non-sports ex-crypto favourite collapse (leading side >= 0.85 at k - 1 to <= 0.15 at k, or a first proposal for the trailing side) and the category's other markets at k | collapses a capture **unprobed** (resolutions about 60 a slot derived; surprises a small share); category-days about 170 in 21 days (arithmetic) | fact 4; rule 22 |
| CH255 | first-of-day change of the two leaders' ordering in a complete neg-risk event (3-10 members; two-member events a held-out arm), by traded / quote-only / unknown and by visibility | **unprobed** (planning 20-80 traded first flips a capture); complete event-captures about 1,833 (CH240) | fact 3 |
| CH256 | eligible non-sports event x capture with a comment-count change at (k - 1, k] | coverage and change share **unprobed** (the field is on every row; the builder excluded it from `participation`) | fact 7 |
| CH257 | market x capture with `accepting_orders` false while active, and the reopening slot | **unprobed** (planning: rare; a few non-sports halts a week) | fact 7 |
| CH258 | non-crypto eligible row x capture, by the BTC / ETH realised-volatility state of the slot (se20's klines) | every non-crypto eligible row (about 30,000 a capture); stress slots in 21 days **unprobed** (planning 5-20); clusters = slots (rule 22) | facts 1, 9 |
| CH259 | eligible market x capture with predictions from >= 3 visible non-embargoed specs | every eligible row a capture since the specs' first fits (K specs; STATUS); the dispersion's distribution **unprobed** | facts 9, 10 |
| CH260 | `res_7d` row by fee class x price bin x tier (the fee's incidence per dollar staked) | fee-free cells 29% of non-sports ex-crypto rows (CH251); `res_7d` labels crypto-heavy in 21 days (CANDIDATES row 26) | facts 2, 4, 6 |
| CH261 | the LT13 population map: widenings by cell, batches, collapses, flips, comments, halts, stress slots, dispersion | a map; counts 0 until run | - |

---

## 1. Map: where money might be, given the costs, the census deaths and the clock of the quote's return

The cost model fixes the frame (2.9c in the most liquid tier, 4.5c at the median touch, 5.2c in sports; makers about
break-even before rebates and rewards; adverse selection above the half-spread in every tier but the largest; a 3.1%
passive fill rate within an hour driven by whether anyone trades at all); the arithmetic of 0.1 fixes the design (spread
targets on dense events; strata by construction; common states to the engine). The record since round 17 fixes the odds:
LT12 froze two of round 17's three, every LT since LT4 has lost most of its family at the census, and the two batch tests
that reached their sources this week died on coverage. So this round does not go back to the mover, the rewarded band,
the ladder's bid sum or the twin's spread; it reads four things the captures date on every row that nobody has read as a
state, and two stores the engine already holds.

1. **A widening is a dated event on every two-sided row, and who comes back first is fixed by who is paid.** A maker
   paid per fill (the rebate, fee-on markets only) wants to be hit again and returns to the touch; a maker paid nothing
   (fee-free unrewarded) has no reason to; a maker paid per minute (the rewarded panel) returns to the band edge, which is
   LT9's object (CH213) and is excluded here. The unrewarded panel splits cleanly into the first two, with no reward
   programme in either cell, so the contrast of their re-tightening after the same-sized widening is the cleanest reading
   of the rebate's effect on a quote the captures allow. The honest doubt is stated with it: the rebate is 0.05-0.1c a
   filled share, small against the half-spread, so the contrast may be composition and nothing else; the cell-matched
   control and the narrowing placebo are built to say so.
2. **Markets created in the same minute across different events are one listing and one set of quoters.** The venue
   lists in batches (a themed drop, a week's fixtures, a slate of races); the seed maker and the farmers who onboard a
   batch quote it as a set; when the set's makers re-parametrise (a volatility update, an inventory limit, a heartbeat
   lapse), the mates' spreads move together and the one that did not move is stale. `created_at` is on every row and no
   key names the batch; same-event mates are LT11 / LT12's and are excluded, so what remains is the *cross-event* set,
   which is the part no event join can see.
3. **A loss to holders is a shock to the markets they still hold.** When a favourite collapses (a surprise resolution,
   a crash), its holders are mostly the holders of the category's other favourites (the same style of position); they
   sell or stop bidding; the category's favourites dip and the makers widen for a slot. CH98 and CH68 read the winners'
   cash; nobody reads the losers' retreat. By rule 22 it is an engine family, and it is written here because the engine
   can read it across months while a 21-day test cannot.
4. **A headline can be bought.** The ordering of the two leaders in a race is a sentence ("X now leads on Polymarket")
   that campaigns, promoters and token projects want published; the flip is bought through the leader's ask, costs the
   buyer the spread and the reversal, and is worth it to him for reasons outside the market. The flip is visible on the
   captures (two mids at k - 1 and k), the visibility of the event is on the sidecar, and the signature of the mechanism
   is that traded flips in visible events revert more than quote-only flips or flips nobody sees.
5. **The engine already holds three things nobody reads as states:** the event's comment count (an attention meter that
   needs neither a print nor a price), the `accepting_orders` flag (the venue's own pause before a clarification), and
   its own challengers' disagreement (which family's isolate departs from the champion for this market this slot). And
   the fee's incidence per dollar staked is twenty times heavier on the cheap side than on the dear side, which is a
   composition fact about who buys longshots in fee-on markets.

| Family | What the host already dates that nobody has read | Money route |
|---|---|---|
| A. The payer's return (CH252) | the widening at (k - 1, k] on every unrewarded two-sided row, by fee class | maker: in fee-on unrewarded books re-post inside the widened spread a slot earlier than the fee-free comparison implies (gross; the stale wide quote's pick-off avoided); taker: none |
| B. The latent set (CH253, CH258) | the creation batch across events; the crypto stress slot on non-crypto rows | maker on a batch-mate: widen when the mates widen (gross); the unhedged maker quotes through crypto stress in politics where the bots pull (gross; engine) |
| C. Losses and headlines (CH254, CH255) | a favourite's collapse as the category's shock; the leaders' flip in a visible race | maker in the shocked category: widen for a slot, or bid one tick under the dipping favourites (gross; engine); maker fade of the bought flip (CH93's rule; gross; engine) |
| D. The venue's unread flags (CH256, CH257) | the comment-count change; the pause and the reopening | maker skew against attention flow (CH24's rule); the clarified side at reopening, reported |
| E. The engine's own store and the fee's incidence (CH259, CH260) | the challengers' disagreement per market per slot; the fee per dollar staked by side | maker widens where the families disagree; a calibration moderator for `res_7d`; no route |
| F. The map (CH261) | widenings by cell, batches, collapses, flips, comments, halts, stress slots, dispersion | decides whether LT13 is drafted at all |

**Data labels.** `A` = on the host now (captures, sidecar, two sweeps, trade samples, the monitor, the poller's quotes,
the engine's `quotes/`, `features/`, aux tables, predictions and label states, the four keyless streams, `reward_params`,
se20's klines). `A~` = on the host but a join has to be written and counted first (the fee x carry cells on widenings,
the creation batch, the favourite-collapse reader, the leader-flip reader, the comment delta, the halt flag, the
prediction-dispersion reader). `P` = a fetch is needed (none here). **Sealed and not usable by anything here:** LT2's,
LT3's, LT4's (E022's) stores, LT9's, LT10's, LT11's and LT12's once registered (LT11's `xw`, `cl_sib`, `xo` and LT12's
`zs_D`, `shock x unrew`, their twins and targets, and their window captures 11-18..12-09 and 12-10..12-31 are not read by
any census or test here), CB16's and CB17's stores, CB8-H's holders, E009 / E010's `cross_venue_live/` to 2026-11-03,
E011's `surprise_live/` to 11-10, E025's and E026's stores and the E026 frozen modules. J4-R `[2026-10-16, 2026-10-21)`
and CB13-T's holdout `[2026-10-21, 2026-10-26)` are refused for every maker mark-out object; nothing here is one.

**Windows and registration this round proposes (LT13, "the payer and the batch").** A thirteenth family on the captures
and sidecar, registered separately from LT2-LT12 with its own Holm family (**k <= 2**; a third only if CH261 opens a
door no arithmetic below expects): CH252, CH253, after CH261's map.
- **Fast lane.** Neither reads a state LT9, LT10, LT11 or LT12 tests (LT9: the band break, the pool, the omission on the
  rewarded panel; LT10: the Kalshi book; LT11: the collateral weight, the siblings' bid sum, the rewarded 0.10 / 0.90
  crossing; LT12: the twin's spread innovation, the sibling shock x status in mixed ladders; CH252 is the unrewarded
  panel's widening by fee class, CH253 the cross-event batch with same-event mates excluded), so they can run in the
  captures slot after LT9's window: **window 2027-01-21T00:00Z .. 2027-02-11T00:00Z** (LT9's `REGISTERED_UTC` is never
  before 2026-12-30 and its 21 days end by 01-20 if it takes that slot; the window slides later with LT9, never earlier),
  analysis on or after **2027-02-12T12:00Z**, design text frozen **before `T_LT12` (2027-01-01T12:00Z)** and before LT9's
  analysis. The census seal: every ten-day span from 10-28 to 02-11 is some test's seal or window (LT11's seal
  `[10-28, 11-07)`, LT12's `[11-07, 11-17)`, LT11's window `[11-18, 12-09)`, LT12's `[12-10, 12-31)`, LT9's `[12-30, 01-20)`),
  so the LT13 census reads **LT12's worn seal `[2026-11-07, 11-17)` for counts only** (re-sealed with LT13's own file list
  and sha256s; label `informed (LT12 census)`, round 17's convention; no LT12 object computed) or, in the ordered lane, a
  fresh seal `[2027-01-21, 01-31)` with the window from 02-12. Reading a registered test's window captures for a census
  is not done (round 17's own rule for LT11, kept).
- **Ordered lane.** If the pin is not before `T_LT12`, `REGISTERED_UTC` = the first 00:00Z at least 24 h after LT9's
  `END_UTC` and after the LT13 registration commit; 21 days; single analysis >= 36 h after the end; a pin after `T_LT12`
  labels CH252 `informed (LT12)` (CH244's reward-status reading in mixed ladders is a descriptive on the same carry
  field) and every pin after `T_E015` (11-15) labels CH252's M1 `informed (E015)` (the traded class), which is certain in
  both lanes and is said so in its entry.
- **Tokens (filed in CANDIDATES at the freeze, before any isolating challenger):** `payreturn` (CH252: fee class x
  widening interactions on the spread; the `paymaker` cells as levels are allowed after 11-18 / 11-22 as round 17 filed
  them), `batch` (CH253: the mates' spread innovation `bt_mates_dspread`; the batch's levels `bt_n`, `bt_n_events`,
  `bt_age_h`, `bt_cross_event` may be built now, no test reads them), and an attribution limit `attrlimit_lt13` on fee
  class x spread-change interactions inside `tilt` / `paymaker` and on batch-mate interactions, for the champion and the
  broad models, each to the later of LT13's analysis commit and the lane's date (fast lane 2027-02-14T00:00Z).

## 2. Hypotheses

### A. The payer's return (parents CH250, CH243, CH39, CH147, CH169, CH213 / LT9, CH244 / LT12's carry reading; literature: Foucault, Kadan and Kandel 2005 on the resting order's cost, Colliard and Foucault 2012 and Malinova and Park 2015 on make / take fees, Parlour 1998 and Foucault 1999 on the limit-versus-market choice as a function of the spread)

**CH252. The payer's return: a widening of the spread is a dated event on every two-sided row, and the speed at which
the touch comes back is fixed by who pays the maker. On the unrewarded panel no programme pays by the minute, so the
maker is paid per fill (the rebate, fee-on markets only) or paid nothing (fee-free unrewarded markets: geopolitics and the
pre-03-30 remainder). A maker paid per fill wants the next fill and re-posts at the touch; a maker paid nothing has no
pull back to it. So after the same-sized widening at (k - 1, k], the spread re-tightens more over (k, k + 1] in fee-on
unrewarded markets than in fee-free unrewarded ones, cell-matched on tier, category and age; on narrowings (the maker
arrived, nobody needs to return) the panel contrast is near zero, which separates the payer's motive from any generic
width mean-reversion that the composition of the two panels would share.**
- Mechanism and why it is non-obvious. Foucault, Kadan and Kandel 2005: a resting order's cost is the waiting; a payment
  per fill lowers the maker's reservation spread and shortens the time he will rest away from the touch. The rebate is
  funded by the market's own taker fees and shared by fill share (fact 6), so it exists only where a fee exists, and its
  per-share size is small (0.05-0.1c), which is exactly why nobody has read it as a *behavioural* difference: round 17's
  CH250 read the 2 x 2 as the maker's reaction to a *print* and found three of its four cells too thin on traded movers
  (CH251: 42 and 99 unrewarded traded movers a capture against a 105 line); the widening is the same question on a
  population ten to twenty times denser, because a spread widens on quote changes as well as on prints. Who pays: the
  maker in a fee-free unrewarded book whose wide quote stays wide and is the first picked off when the mid moves; who
  collects: the per-fill maker who is back at the touch a slot earlier (gross), and the taker in the fee-free book who
  waits a slot. Why the crowd misses it: the rebate is read as a cost line, not as a clock.
- Parent and what is new. CH250 (the payer 2 x 2 on prints; engine-first), CH243 (the fee as a filter on the crosser,
  dropped at LT12 R1 because its F could not bind on its count), CH39 (post-print quote retreat), CH147 (the sticky touch
  and the breathing book), CH169 (arrivals and cancellations as one-sided quote moves), CH213 / LT9 (the rewarded panel's
  re-tightening after a band break: *excluded here*, the rewarded panel is a reported arm `informed (LT9)`). New here:
  the **widening**, not the print, as the dated event (dense on every two-sided row), the **unrewarded** panel as the
  population (no programme in either cell, so the rebate is the only payer), the **re-tightening over the next slot** as
  the target, the **narrowing** as the built-in placebo, and the fee-on comparison units drawn from the fee-free units'
  tier x category x age cells (CH243's S33 control, now the primary's sampling rule).
- Data join and decision clock (`A~`, L 4: the rows' spread at k - 1, k and k + 1, the sidecar's `fees_enabled`,
  `fee_schedule`, `created_at`, `clob_rewards` with the carry reading and the CLOB feed adjudicating; the map's 2 x 2
  bounds the panel). Unit: non-sports ex-crypto, **unrewarded** (`listed_carry24h_v2` false on the day, the feed
  disagreement gate of LT12 7 reused; `rewards_null_*` cases counted) market x capture, two-sided at k - 1, k and k + 1
  (a one-sided k + 1 is `unavailable`, counted), with `wd_k = 1[spread_k - spread_{k-1} >= 2 x tick]` (the widening) and
  `nw_k = 1[spread_k - spread_{k-1} <= -2 x tick]` (the narrowing, the placebo class); the rest of the market's slots are
  its within-market reference. Panel: `fee_on` = `fees_enabled` and `fee_schedule.rate > 0` at k's sidecar; `fee_free`
  = flag false or rate 0; `fee_src` recorded (category, deployment date, flag). Decision time: the row's `received_utc`
  at k. Controls: `spread_{k-1}` (the level), the widening's size in ticks, `d_k` and `|d_k|`, `log1p liquidity`, `z log
  rv24`, tier (the cost model's bins on the row's `liquidity`), category, age class (`created_at`: before / after
  2026-03-30 and quartiles within), hours to end, `volume_num` change keyed by slot (`unknown` a counted class, used in
  M1 only, never inferred: LT11's MUST 5).
- Target and horizon. Primary: `ds = spread_{k+1} - spread_k` (SD 2c; floor 1.0c). Within market, `beta_panel` = the
  expanding-past market x UTC-day demeaned coefficient of `wd_k` on `ds` (negative: a widening reverts). Hypothesis
  (one-sided): `beta_fee_free - beta_fee_on > 0` (the fee-on book re-tightens more), the contrast of two within-market
  coefficients, cluster-robust across events (rule 20), the fee-on comparison units drawn from the fee-free units'
  tier x category x age cells. **Binding point condition:** the same panel contrast on `nw_k` (the subsequent re-widening
  after a narrowing) is less than half the widening contrast in absolute value (a composition story predicts equal
  contrasts on both; the payer's motive is a return *to the touch*). M1: the contrast on traded widenings alone (a fill
  just paid the fee-on maker; `informed (E015)` in both lanes; reported). M2: the rewarded panel's contrast (the
  per-minute payer; `informed (LT9)` after its analysis; reported). M3: the contrast by price bin (the rebate is
  `rate x p(1 - p)`, five times larger at 0.5 than at 0.05, so the contrast should be larger at mid prices: the
  mechanism's dose, reported with its declared expectation).
- Paper rule and economic check (rule 11: maker-side). Maker in a fee-on unrewarded book: after a widening, re-post
  inside the widened spread at the slot the fee-free comparison would still be wide (the quantity captured is the
  re-tightening in cents a share, gross, no fills); the per-fill pay that motivates it is 0.05-0.1c a share, so the
  route's value, if any, is the adverse selection avoided on stale wide quotes (AS 2.04-2.45c in the 1k-100k tiers
  against half-spreads 0.75-1.0c), not the rebate; this is said in the entry so that a Supported verdict is not read as
  a rebate return. Taker (reported, never a verdict): in a fee-free unrewarded book, wait one slot after a widening (the
  saving is the re-tightening that does not come; against 1.8-4.5c round trips: "not shown").
- Population arithmetic. Fee-free unrewarded rows 555 (median capture) to 4,577 (mean) a capture; fee-on unrewarded
  11,267 (CH251); widening share **unprobed** (planning 0.10): fee-free unrewarded widening units **55-460 a capture**,
  21 days 14k-116k, `n1_eff` 11k-93k; fee-on unrewarded about 1,100 a capture, 284k, `n2_eff` 227k. Events: the fee-free
  unrewarded panel is standalones and old ladders, so distinct events are near the market count (hundreds to low
  thousands over 21 days; >= 500 unprojected is a gate). Cluster = event; the LT11 formula gives about **6** for a
  standalone market over 21 days (m_21 = 252) and about 11 where events average three members; the convention 31 is
  quoted beside both.
- Permutation and cluster structure. Stratum: market x UTC day (rule 2; a widening occurs on a large share of
  market-days and is read on all 12 slots); the Freedman-Lane null tests the within-market term only (given the
  market-day, which slot carried the widening does not matter for the next spread change); the panel contrast is a
  between-market comparison and its null is the cluster-robust one (rule 20); binding scenarios: LT5 1-2, L10, **S38: a
  fee-free panel that is older, larger and slower with the same re-tightening per widening** (the cell-matched control
  must return zero), **S39: a common width cycle (CH147's breathing book) with AR persistence identical across panels**
  (the within-market term absorbs it; the contrast must return zero on a shared AR), **S40: differential `volume_num`
  missingness by panel** (CH251's 213 unusable fee-free movers; the primary does not read the traded flag, only M1
  does), and the VIF gate of rule 17 on the widening against `sign(d) x f(p)`.
- Planning MDE (spread class contrast of two within-market contrasts; `sqrt(2)` for the difference of differences; no
  gap factor on an indicator). At DE 11: low `3.47 x 2c x sqrt(1/11,000 + 1/227,000) x sqrt(11) x 1.5 x sqrt(1.3) x
  sqrt(2)` = **0.54c**; high **0.22c**; a quarter of the low count 1.07c. At DE 31: **0.91c / 0.36c**; quarter 1.80c. F
  (the twin is `wd` over `(k + 2, k + 3]`; planning `r_w` 0.2): at DE 11 **0.85c / 0.35c (a verdict condition at both
  ends)**; at DE 31 1.44c (low; over the cap, so the low count fails at the convention) / 0.57c (high: a verdict
  condition). **Kill lines (F binding):** about **40 fee-free unrewarded widening units a capture at DE 11, 113 at DE
  31**; the plain gate at about 15 / 45. The median capture's planning count (55) clears the formula's DE and not the
  convention's; the computed DE decides and is printed.
- Confounders and the control. The fee-free panel is geopolitics plus the venue's oldest, largest, longest-dated
  markets (round 10's objection; the cell-matched control's job; the pooled |corr| of `fee_free` with `log1p liquidity`
  is the census's first number and the likeliest killer); the fee-free population is **not stationary** over CH251's
  span (mean 4-8 times the median in every fee-free cell, "a block of captures carries most of it"), so the venue-clock
  gate (<= 50% of units in one slot) and the block-gate share bind and a per-capture distribution is printed; the carry
  reading's omission structure (62.2% of rows null; LT12's feed gate reused: coverage >= 50% else `census_unavailable
  (coverage)`, feed-listed share among "unrewarded" <= 0.20 else `census_dropped`); the maker rebate's smallness (the
  boring explanation, below); E015's traded class (M1 only; disclosed); E022's reward split of traded movers' depth (a
  different population; `informed (E022)` after 11-17 is certain and applies to M1's traded arm); LT12's CH244 (reward
  status as a within-event panel on mixed ladders in a different window; a pin before `T_LT12` keeps this blind);
  `tilt`'s visible `tl_fee_ps` and `tl_rebate_ps` levels (a development look at the fee's shape, disclosed; no fee x
  spread-change column exists).
- Most likely boring explanation. A rebate of 0.05-0.1c a share moves no quote, and the contrast is composition (the
  cell-matched control returns the same number as the raw contrast, and the narrowing placebo shows the same contrast);
  or the fee-free unrewarded widenings sit in a few dozen old markets on a few captures (the count or the venue-clock
  gate kills it).
- Cheapest census (counts only; the worn LT12 seal or the ordered lane's fresh seal; no target read). Finite carry
  status on >= 95% of eligible unrewarded market-days; the feed coverage and disagreement gates as LT12 7; projected
  fee-free unrewarded widening units >= 10,080 (>= 40 a capture) with the F line at the computed DE printed and binding;
  fee-on unrewarded widening units >= 5x that; cell-matched coverage >= 60% (fee-free widening units with >= 20 fee-on
  widening units in their tier x category x age cell); pooled |corr(fee_free, log1p liquidity)| <= 0.5 and within and
  pooled |corr(wd, x)| <= 0.5 for x in {`log1p liquidity`, `z log rv24`, `|d_k|`, `spread_{k-1}`}; identification: >= 50%
  of fee-free unrewarded market-days with a widening hold >= 2 widening and >= 2 non-widening slots; `VIF_w(wd)` <= 2.0
  on the demeaned regressors; distinct events >= 500 on the fee-free unrewarded panel and events with >= 48 units >= 100
  (unprojected); `G_eff` >= 15; venue clock <= 50%; block-gate share >= 50% on both panels; `r_gate` <= 0.3; class MDE
  and F-MDE <= 1.0c; the fee reading recorded (`schedule_below_docs`, `fee_src` shares); the per-capture min / median /
  mean of each cell printed with a declared kill: the median capture holds < 25% of the mean (the non-stationary world).
- Challenger feature: **yes, after LT13's freeze** (token `payreturn`): `pr_wd x pm_cell`, `pr_nw x pm_cell`,
  `pr_wd_size x pm_cell` as a spec version of `paymaker` (CH250; its cells after 11-18 / 11-22 as round 17 filed). No
  isolating challenger before the freeze. `tilt`'s fee levels stay as built.
- Sports arm: **empty by construction** (sports has no fee-free rows: CH251), so the sports version is the fee-rate
  gradient 0.03 / 0.05 with the 15% rebate share, uncounted, under the owner's parameter.
- Scores: N 3, EV 2, L 4. Priors: **P(census) 0.22; P(replicates | Supported) 0.25** (the rebate's size is the doubt).
  Parents: CH250, CH243, CH39, CH147, CH169, CH213 / LT9. New: the widening as the dated event, the unrewarded panel as
  the clean population, the narrowing as the placebo, the cell-matched sampling as the primary's rule.

### B. The latent set (parents CH22, CH142, CH154, CH188, CH36, CH131, CH158, CH245 / LT12, CH184, the `regime` family (dropped); literature: Chordia, Roll and Subrahmanyam 2000 on commonality in liquidity, Hasbrouck and Seppi 2001 on common factors in order flow, Brunnermeier and Pedersen 2009 on funding liquidity as the maker's shared constraint)

**CH253. The listing batch: markets created within the same two minutes across different events are one listing (a
themed drop, a slate of races, a week's questions) and are onboarded by one set of quoters, the venue's seed maker and
the farmers who pick up a batch; `created_at` is on every sidecar row and no venue key names the batch. When the set's
makers re-parametrise (a volatility update, an inventory limit, a heartbeat lapse: CH36's same-key cancellation), the
mates' spreads move in the same slot and the mate whose spread did not move is the stale one; it follows a slot later.
The dated object is the cross-event batch-mates' spread innovation over (k - 1, k]; the prediction is the own spread
change over (k, k + 1]; same-event mates are excluded (LT11 / LT12's object), so what is tested is the part of the
quoter set that no event join can see, against a pseudo-batch placebo of same-category, same-age markets created a week
apart.**
- Mechanism and why it is non-obvious. Commonality in liquidity (Chordia, Roll and Subrahmanyam 2000) has a *cause* on
  this venue that the equity literature only infers: the same accounts quote many books (CH36's heartbeat rule cancels
  every order of a key within 10 s; CH131's size signatures), and the set a bot quotes is largely the set it onboarded,
  which the venue creates in batches. The batch is therefore a *quoter-set proxy with a timestamp*, and its co-movement
  is mechanical (one model, many books) rather than informational. Who pays: the batch-mate whose maker is slower (the
  stale quote inside the set's new width is the one hit); who collects: the taker who knows the set, and the maker who
  widens with his mates. Why the crowd misses it: the venue shows one market page, the event is the only grouping anyone
  draws, and a cross-event batch has no name.
- Parent and what is new. CH22 (the genesis window: the first 24 h after listing), CH142 (the series launch window),
  CH154 (first-day prints), CH188 (sibling birth inside an event), CH36 (same-key outages across a quoter's set, mapped
  from vacuums), CH131 (quoter-type footprints), CH158 (the venue tilt as a common factor of *mids*), CH184 (alone or with
  the crowd, the event's share moving), CH245 / LT12 (the mirror: the twin book's spread innovation), the `regime`
  family (the venue-wide activity level, dropped for being a common per-capture shock). New here: the **creation
  timestamp as the join** (a latent set across events, rule 21), the **mates' spread innovation** as the state (not the
  venue's or the category's), the **own spread change** as the target, the **category x slot mean innovation over
  non-mates** as the common-factor control (so the batch must add to what the category already says), and the
  **pseudo-batch** as the placebo.
- Data join and decision clock (`A~`, L 3: the batch join over `created_at`, pinned before any count: window 120 s
  (a batch closes when 120 s pass without a new creation in the capture's universe), minimum 3 markets spanning >= 2
  `event_id`s, mates in the unit's own event excluded, batches capped at 30 cross-event mates (larger ones, the sports
  season dumps, a reported arm); completeness per rule 21). Unit: non-sports ex-crypto market x capture whose batch has
  >= 2 complete cross-event mates (two-sided at k - 1 and k, receipt span <= 120 s at both captures). State: `zs_bt =
  z(mean over complete mates of (spread_{j,k} - spread_{j,k-1}))`, standardised per batch by the census SD (positive =
  the mates widened); `thin_i = 1[spread_{i,k-1} > median mates' spread_{k-1}]` (the own book is the wide one; `sym` a
  reported class). Decision time: the latest mate row's `received_utc` at k. Controls: the own innovation `spread_{i,k} -
  spread_{i,k-1}` (what has already followed), the **category x slot mean spread innovation over non-mates** (the common
  factor; computed from rows received before the unit's own row where the capture's order allows, else the previous
  slot's), `d_i` and `|d_i|`, `log1p liquidity`, `z log rv24`, reward status (carry), fee class, tier, hours to end; batch
  age is constant within a batch and is absorbed by the stratum.
- Target and horizon. Primary: `ds_i = spread_{i,k+1} - spread_{i,k}` (SD 2c; floor 1.0c); hypothesis (one-sided):
  within batch x UTC day, the slope of `ds_i` on `zs_bt` > 0 given the controls. **Binding point condition (rule 21's
  placebo):** the slope on the unit's pseudo-batch innovation (`zs_pb`, same category and age decile, created >= 7 days
  apart, the same mate count) has absolute value less than half the batch slope (two-sided; an analysis condition with a
  census coverage gate). M1: the thin-follows-dense ordering (the slope on `thin_i = 1` units exceeds twice the slope on
  `thin_i = 0`; CH245's condition adapted; reported, since its MDE is about twice the slope's). M2: the own mid change
  at k + 1 (reported; `informed (L1-L4, E005)` by the record on sibling mids). M3: the genesis arm (units in the first 7
  days of the batch's life, where the seed maker is the common quoter; CH22's window; reported).
- Paper rule and economic check (rule 11: maker-side). Maker on a batch-mate: widen by the mates' widening for one slot
  as soon as the mates widen (the pick-off avoided is `ds_i` in cents a share, gross, no fills). Taker (reported, never
  a verdict): take the stale mate's old quote in the slot after the set widened, against the mate's own half-spread
  (1.0-2.0c in the 1k-10k and < 1k tiers where young batches live); expected "not shown".
- Population arithmetic. **Unprobed:** the share of eligible non-sports ex-crypto rows in a cross-event batch of >= 3
  (planning 20-50%, 3,600-9,000 units a capture), batches with units (hundreds to low thousands), the mates' completeness
  (young markets are one-sided more often: CH10's placeholders). 21 days: 0.9-2.3M units; `n_eff` 725k-1.8M. Cluster =
  batch (cap 10 mates for the primary: DE 31; 11-30 a reported arm at 51; the LT11 formula's value printed: a batch of
  10 over 21 days gives m_21 = 2,520 and DE 51, so the convention is the lenient one here and is disclosed as such).
- Permutation and cluster structure. Stratum: batch x UTC day; the Freedman-Lane null (given the batch-day, which slot
  carried the mates' widening does not matter for the own next spread change) with **one offset per batch** (the mates'
  series shifted together; LT11's event-phase form); binding scenarios: LT5 1-2, L10, **S41: the batch factor is the
  category factor** (every mate and every non-mate in the category widens in the same slot: the common-factor control
  must absorb it; the gate must return zero on a simulated category-wide AR shock), **S42: one bot quoting the whole batch
  with no lag** (the null world; the same-slot correlation of mates' innovations is the census's number, LT12's gate
  reused), **S43: the pseudo-batch placebo loads because age and category alone drive co-movement** (the condition's
  world; printed). Clusters: batch, two-way batch x UTC day and UTC day, p the largest; events are *not* the cluster
  since mates span events (a batch's events are nested inside it).
- Planning MDE (spread slope). At DE 31: low `3.47 x 2c / sqrt(725,000) x sqrt(31) x 1.5 x sqrt(1.3) x 2.2` = **0.17c**;
  high **0.11c**; a quarter of the low count 0.34c. At DE 51: 0.22c / 0.14c. F (the twin is `zs_bt` over `(k + 2, k + 3]`,
  planning `r_w` 0.2): **0.27c / 0.17c at 31, 0.35c / 0.22c at 51: a verdict condition at every count.** Power is not the
  question; the **kill lines are coverage (< 20% of eligible rows in a cross-event batch of >= 3), batches with units
  (< 500 unprojected), the same-slot correlation share (>= 0.8 in more than 50% of batches with >= 24 units), the VIF of
  `zs_bt` against the category-slot factor (> 2.0), and the placebo coverage (< 90%).**
- Confounders and the control. The category factor (S41; the control and the VIF gate); batch age (constant within the
  stratum); the sports season dumps (hundreds of markets in one minute: the arm; the cap); one bot per batch (S42);
  young, illiquid books (the |corr| gates against `log1p liquidity` within and pooled; the tier x state interaction
  reported); LT12's mirror (a pair of the *same event*; excluded by construction; disclosed as the adjacent object);
  LT11's bid-sum state (same-event; excluded); the `event` family's visible levels and `participation`'s event age
  (development looks, disclosed; no batch column exists anywhere).
- Most likely boring explanation. The venue lists one event at a time, so cross-event batches within 120 s are few and
  the coverage gate kills it; or the batch factor is the category factor (S41: the VIF gate kills it cleanly); or the
  mates are quoted by one bot that updates all its books in the same minute, so the lag is zero (S42: a clean null the
  same-slot correlation predicts before any test).
- Cheapest census (counts only; the worn LT12 seal or the ordered lane's fresh seal; no target read). The batch join
  pinned by sha256 before the count; the share of eligible non-sports ex-crypto rows in a cross-event batch of >= 3 and
  the batch-size distribution (kill if coverage < 20%); complete units a capture; completeness share by batch age
  (kill if < 60%); batches with units >= 500 and batches with >= 48 units >= 100 (unprojected); `G_eff` >= 15; the
  same-slot correlation share; within-batch-day SD of `zs_bt` >= 1 tick in >= 50% of batch-days with >= 24 units;
  `VIF_w(zs_bt)` <= 2.0 against the category-slot factor and the own innovation on the demeaned regressors; |corr| <= 0.5
  with the tiers, `z log rv24`, `d_i`; placebo coverage >= 90%; block-gate share >= 50%; venue clock <= 50%; `r_gate` <=
  0.3; slope MDE and F-MDE <= 1.0c; the `thin` / `sym` shares; the sports arm's batch sizes printed.
- Challenger feature: **levels now, the innovation after LT13's freeze** (token `batch`): `bt_n`, `bt_n_events`,
  `bt_age_h`, `bt_cross_event`, `bt_mates_spread_med`, `bt_own_rank` as levels in a new aux family (no test reads
  them); `bt_mates_dspread` and `bt_thin x bt_mates_dspread` under the token. Kill the family at the engine's census if
  coverage < 20% of eligible rows.
- Sports arm: uncounted (the season's fixture dumps are the largest batches on the venue and the sports version is where
  the join is densest; the owner's parameter).
- Scores: N 4, EV 3, L 3. Priors: **P(census) 0.15; P(replicates | Supported) 0.30.** Parents: CH22, CH142, CH154,
  CH188, CH36, CH131, CH158, CH184, CH245 / LT12. New: the creation timestamp as a latent join across events, the mates'
  spread innovation as the state, the category-slot factor as the control, the pseudo-batch as the placebo.

**CH258. The shared balance sheet (`stress`; engine-first by rule 22): the firms that quote crypto ladders on this venue
also quote politics and culture, and they hedge or fund on the crypto venues; a spike in BTC or ETH realised volatility
raises their inventory risk and margin usage everywhere at once, so they widen or pull in politics in the slot after a
crypto shock with no politics news. se20 already fetches the klines per capture, closed before the capture start; nothing
reads them on non-crypto rows. The dated input is the slot's crypto stress; the prediction is a wider spread and a lower
flat probability on non-crypto rows, more in bot-quoted books (fine tick, rewarded) than in human books.**
- Why engine-first. The state is common to every unit in a slot (rule 22: about 250 slots in 21 days are its effective
  observations, far too few for a test, and the within-market Freedman-Lane null cannot separate a per-slot state from
  the slot's own effect, which is the `regime` family's REVISE). The engine's walk-forward scores accumulate slots over
  months, which is where a common state can be read; the honest comparison is against se1 with the slot's own category
  factor held (the engine's `market_state` carries no slot factor, so the family must carry one as a control column).
- Columns (`A`, L 4; clock: the kline's close before the capture start). On every non-crypto eligible row:
  `st_btc_rv_1h`, `st_btc_rv_ratio` (1 h over 7 d), `st_btc_ret_2h`, `st_btc_absret_2h`, `st_eth_rv_1h`, `st_stress` =
  `1[st_btc_rv_ratio >= 2]`, and the slot's own non-crypto mean |2 h change| over rows received earlier in the capture as
  the common-factor control (the receipt-order proxy the `regime` review flagged; disclosed as such; the previous slot's
  value as the alternative), with interactions on `order_price_min_tick_size` and the carry reward status (after 11-18).
- Expected direction. Spread change and `dir_*`'s flat class: wider and less flat on non-crypto rows after a stress
  slot, more on fine-tick and rewarded books; `dir_2h`'s sign: none (the mechanism is liquidity, not direction).
- Why not already held. `crypto` (se20) is defined on crypto template rows only; `regime` read the venue's own
  activity, not an external shock; `market_state` holds own `rv24`; nothing holds an exogenous per-slot shock on
  non-crypto rows. No token covers it; the `crypto` spec is visible.
- Money route (gross; engine). The unhedged maker quotes through crypto stress in politics where the hedged bots pull:
  gross = the spread premium of the stress slot with no politics information; adverse selection unchanged if the
  mechanism holds (the premium is funding, not news). Taker: none.
- Falsifier. No relation of non-crypto spread changes or the flat class to `st_*` beyond the slot's own common factor
  over 28 days of scores; or the relation is explained by news days that are also crypto stress days (the common cause;
  the category factor control is the only guard a per-slot state allows).
- Boring explanation. Polymarket's makers do not fund on Binance; or the stress slots in a window are five and the
  column has no variance (the census prints the count of stress slots in the span).
- Census (counts only): stress slots in the span (kill the family if < 5 in 21 days); the share of non-crypto rows that
  are fine-tick; the correlation of `st_btc_rv_1h` with the slot's own common factor (|corr| > 0.8 kills the separate
  reading).
- Sports arm: uncounted (sports books are the most bot-quoted on the venue; the owner's parameter).
- Scores: N 4, EV 2, L 4. Priors: P(census) 0.60 (a count of slots); P(replicates) 0.20. Parents: CH158, CH36, CH184,
  se20, the `regime` family. New: an exogenous per-slot shock from another asset class as the maker's funding clock on
  non-crypto rows.

### C. Losses and headlines (parents CH98, CH68, CH67, CH24, CH128, CH175, CH93, CH176, CH157, CH20, CH110, E004; literature: Thaler and Johnson 1990 on prior losses and risk taking, Coval and Shumway 2005 on loss-driven behaviour of market makers, Hanson and Oprea 2009 and Rhode and Strumpf 2004 on manipulation attempts in prediction markets, Hartzmark 2015 on rank effects, Barber and Odean 2008 on attention buying)

**CH254. The loser's exit (`shock`; engine-first by rule 22, with a map): when a favourite collapses (a surprise
resolution against the side priced >= 0.85, or a crash to <= 0.15 in one interval), its holders lose most of their
stake, and those holders are disproportionately the holders of the category's other favourites, because buying
favourites is a style. They sell or stop bidding across the category; the category's other favourites dip against their
leading side and the makers widen for a slot, with no news about any of them. CH98 reads the cash the winners get on
resolution days and CH68 where the winners put it; nobody reads the losers' retreat. The collapse is visible on the
captures at k (two mids), the dollars behind it on the sidecar, and the category on every row.**
- Why engine-first. The state is shared by every unit of the category at the slot (rule 22: about 170 category-days in
  21 days; a spread class MDE of about 1.0c and an F-MDE of 1.6c before any unit is counted), and non-sports ex-crypto
  surprises are few by construction (fact 4: about 60 resolutions a slot, half of all resolutions at a coin-flip at
  their last origin). The engine reads it over months; the sports arm (upsets daily) and the crypto arm (the 15-minute
  series' losers every slot) are where the count is, under the owner's parameters.
- Columns (`A~`, L 3; clock: the capture at k; the collapse read from the rows at k - 1 and k and the sidecar's
  statuses at k; rule 23: other markets' public facts, the unit's own event excluded). On every eligible row:
  `sh_cat_collapse_2h` (the count of favourites in the market's category, other events, whose leading side fell from >=
  0.85 at k - 1 to <= 0.15 at k, or whose sidecar first shows a proposal or resolved status for the trailing side),
  `sh_cat_collapse_usd_2h` (their summed `log1p volume_num` at k - 1; unknown a counted class), `sh_cat_collapse_24h`,
  `sh_cat_due_24h` (the category's markets with `end_date` in the next 24 h and their summed `log1p open_interest`:
  CH98's scheduled wave, a control), `sh_own_fav` (the own leading side >= 0.85), and the interaction `sh_cat_collapse_2h
  x sh_own_fav` (the de-risking target).
- Expected direction. `dir_2h` and `dir_6h` on the category's other favourites: against the leading side after a
  collapse (sales), reverting by `dir_24h` (the engine scores all three); the spread widens; the flat class is less
  likely. Calibration: `res_7d` on favourites in shocked categories is better than their dipped mid says.
- Why not already held. `market_state` holds the category one-hot; `participation` event-level volume; nothing holds
  another market's collapse as a per-category shock. No token covers it; CH67's sibling unwind is the same-event case and
  is excluded here by construction.
- Money route (gross; engine). Maker in the shocked category: widen for one slot (the pick-off avoided), or bid one
  tick under the dipping favourites' bids (buy from the de-riskers; gross = the 24 h reversal against the half-spread
  0.5-1.0c of liquid favourites and AS 0.39-2.04c). Taker: none ("not shown").
- Falsifier. The category's other favourites show no dip and no widening in the collapse slot beyond the category's
  own activity factor over 28 days of scores; or the effect is entirely the same-event unwind (excluded) and the category
  level is zero.
- Boring explanation. Non-sports ex-crypto favourite collapses are two a day and the column is empty; or holders of
  one favourite do not hold the others (the style assumption fails) and nothing spills.
- Map (counts only; part of CH261): collapses a capture by category and kind (crash / proposal / vanished at k + 1 with
  a resolved status), their dollar size, the number of category-days with >= 1 collapse, the share of eligible rows that
  are favourites.
- Sports arm: uncounted (upsets are the dense version; the owner's parameter). Crypto arm: the Up / Down series'
  losers every slot; the owner's parameter.
- Scores: N 4, EV 2, L 3. Priors: P(census) 0.35 (the collapse count); P(replicates) 0.20. Parents: CH98, CH68, CH67,
  CH24, CH128, CH175. New: the losers' side of a resolution as a category-wide shock, the favourites' interaction, the
  scheduled wave as the control.

**CH255. The leader flip (`headline`; engine-first with a map): the ordering of the two leaders in a race is a sentence
("X now leads on Polymarket") that campaigns, promoters and token projects want published, and the sentence can be
bought: lift the new leader's ask through its depth until the two mids cross. The buyer pays the spread, the depth and
the reversal, and is paid outside the market by the embeds, posts and articles that quote the venue's odds. So a
*traded* first-of-day flip in a *visible* event (the top of the volume frame) reverts over the next 24 h more than a
quote-only flip, more than a flip in an event nobody sees, and more than a same-sized move that changes no ordering;
the visibility x traded interaction is the mechanism's signature, and a generic "large moves revert" story predicts none
of it.**
- Mechanism and who pays. Manipulation attempts in prediction markets lose money and move prices briefly (Hanson and
  Oprea 2009; Rhode and Strumpf 2004); rank is what attention responds to (Hartzmark 2015); the venue's odds are quoted
  by name in media and embeds, which gives the displayed ordering a value outside the market. Who loses: the buyer of
  the headline, knowingly, and the followers who buy the new leader after reading it; who collects: the maker who fades
  the flip (CH93's rule: a quote one tick beyond the new leader's price against the break) and the arbitrageur who sells
  the new leader against the displaced one. Why it persists: the headline's value is external and recurring (every
  race, every launch, every awards season). **This reads other participants' prints; it is not a route to cause a flip
  (manipulation of any kind as a route was rejected in rounds 1-2 and stays rejected).**
- Why engine-first. Traded first-of-day flips a capture: **unprobed** (planning 20-80 non-sports ex-crypto); a mid
  class contrast needs about 690 a capture in the smaller class (0.1), so at the planning count the MDE is 1.0-2.1c
  against a 0.5c floor: engine-first by rule 7, with the map as the first line. Two-member events' flips are held out
  of the family until LT12's date (2027-01-03): their two mids are the mirror's levels.
- Columns (`A~`, L 3; clock: the latest leader row's `received_utc` at k; the event join as LT11 / LT12 define it; the
  first flip of the UTC day the state, re-flips a counted class per rule 2). On both leaders and on the event's other
  members of complete 3-10 member events: `hl_flip` (the top-2 ordering by mid changed between k - 1 and k),
  `hl_flip_traded` (either leader's `volume_num` rose; `unknown` counted), `hl_leader_gap` (mid_1 - mid_2 at k),
  `hl_gap_change`, `hl_hours_since_flip` (within 24 h), `hl_is_new_leader`, `hl_visible` (the event's `event_volume`
  rank in the capture's non-sports top 200 and top 1,000; `page_index` as a secondary display proxy once the collector's
  sort order is confirmed from its code), `hl_reflips_24h`, and, on standalone binaries, `hl_cross50` (CH93's object,
  reported, not a new claim).
- Expected direction. `dir_2h`, `dir_6h`, `dir_24h` on the new leader: reversal, larger where `hl_flip_traded x
  hl_visible`; on the displaced leader the mirror; on the other members none (the flip's shadow is zero unless the
  buyer walked the whole ladder). Calibration: `res_7d` worse (the new leader overpriced) in visible traded flips.
- Why not already held. The `event` family holds own rank and the largest sibling as *levels*; `nrslack` (LT11) holds
  the siblings' bid- and ask-sum innovations, `mirror` (LT12) the twin's spread innovation; a change of the *mids'
  ordering* is held by nothing and is covered by no token or attribution limit (`attrlimit_lt11`: bid- / ask-sum
  differences and 0.10 / 0.90 crossings; `attrlimit_lt12`: twin-spread and status x shock interactions); adjacency to
  LT11's CH233 (the same events in its window) is disclosed and the family is scored on all events as a mids-ordering
  object.
- Money route (gross; engine). Maker fade of the flip (CH93's rule): gross = the 24 h reversal of the new leader's
  mid against the leaders' half-spread (0.5-1.0c in liquid politics) and AS (0.39c at >= 100k, 2.04c at 10k-100k), so a
  reversal of 1-3c is the hurdle; a taker fade pays 2.9-3.9c round trips at the leaders' tiers: "not shown" unless the
  reversal is 4c or more.
- Falsifier. Traded flips in visible events revert no more than quote-only flips or flips in invisible events (the
  interaction is zero) over 28 days of scores; or flips are re-flips in coin-toss races (the once-per-day rule and the
  re-flip share say so before any score).
- Boring explanation. Leader flips are rare outside coin-toss races, and in coin-toss races the ordering is noise with
  no buyer; or every visible race is also the most liquid, and liquidity, not visibility, sets the reversal (the tier
  control; the point of `hl_visible` within tier).
- Map (counts only; part of CH261): first-of-day flips a capture by traded / quote-only / unknown, by event size, by
  visibility rank and tier; distinct events with a flip; the re-flip share; two-member events' flips counted separately
  and held out.
- Sports arm: uncounted (the live favourite change in a game is CH23's and CH231's; futures leader changes the sports
  version; the owner's parameter). Crypto arm: the token project's own ladder; the owner's parameter.
- Scores: N 4, EV 2, L 3. Priors: P(census) 0.40 (the flip count and re-flip share); P(replicates) 0.20. Parents:
  CH93, CH176, CH157, CH20, CH110, E004, CH23. New: the ordering change as the dated object, the buyer of a headline as
  the actor, visibility x traded as the signature.

### D. The venue's unread flags (parents CH157, CH24, CH97, CH176, E017, CH08, CH177, CH04, CH48; the `participation` family's exclusion of comment counts)

**CH256. The comment clock (`attn`; engine-first): the sidecar carries the event's comment count on every row at every
capture, and nobody reads its change. A comment costs nothing and moves no price, so a burst of comments between two
captures is attention that has not yet traded; on this venue attention buys YES (CH157's and E017's reading), so a burst
without a move predicts a YES drift over the next day and a larger move either way, and a burst with a move is news
confirmed by a crowd. Comment *sentiment* was rejected in rounds 1-2 as worse data than CH24's volume; the *count's
change* is a different object, a clock on every event row that needs neither a print nor a price.**
- Why engine-first. Bursts a capture are **unprobed** (planning 25-75 non-sports ex-crypto), under the mid line of 690
  (rule 7); the spread's sign under attention is ambiguous (volatility widens, uninformed flow invites competition), so
  a one-sided spread primary cannot be declared honestly; the engine needs no sign.
- Columns (`A`, L 4; clock: the row's receipt; the field's staleness disclosed as a map line). `at_com` (level),
  `at_dcom_2h`, `at_com_rate_24h` (mean change a slot over the last 12), `at_burst` (`at_dcom_2h` >= 3 x the rate and
  >= 5), `at_com_per_vol` (comments per $1k of event volume: the talk-to-money ratio), `at_burst_no_move` (a burst with
  |d| < 1 tick and no `volume_num` rise), `at_burst_with_move`.
- Expected direction. `dir_6h` and `dir_24h`: YES drift after a burst without a move; the flat class less likely after
  any burst; `res_7d`: YES overpriced in high talk-to-money events (the drift reverts by resolution: CH157's carry).
- Why not already held. `participation` holds event volume and liquidity and **excludes comment counts** (CANDIDATES
  row 14; the reason is not recorded there; CB17's use of the field is to be checked before any column reads it, and if
  a registered CB17 test reads comment counts, the family waits for that analysis). No token names comments.
- Money route (gross; engine). CH24's maker skew against attention flow; the NO side of a noticed standalone after the
  drift is CH157's carry and is not re-proposed.
- Falsifier. No relation of bursts to the next day's direction or magnitude beyond `volume24hr`'s change over 28 days
  of scores; or |corr(`at_dcom_2h`, the volume change)| > 0.8 (volume under another name).
- Boring explanation. The field is sports-dominated or cached (changes on a few per cent of rows); or comments trail
  trades rather than lead them.
- Census (counts only; part of CH261): the field's presence on eligible non-sports event rows (kill if < 30%); the
  share of event-captures with a change (kill if < 2%); bursts a capture (kill if < 10); |corr| with the volume change.
- Sports arm: uncounted. Scores: N 3, EV 2, L 4. Priors: P(census) 0.50; P(replicates) 0.25. Parents: CH157, CH24,
  CH97, CH176, E017. New: the comment count's change as a dense attention clock without a print or a price.

**CH257. The pause (`pause`; engine-first with a map): the venue halts trading on a market when its rule is in dispute
or being clarified; the halt is visible on the sidecar as `accepting_orders` false while the market is active and not
closed, and the reopening slot is the moment the clarification meets the book. CH08 and CH177 read the edit's text and
time; CH04 the stale quotes after a decisive event; nobody reads the venue's own pause as the clock. The dated objects
are the halt and the reopening; the prediction is a large move at reopening on the clarified side (the side the text
diff favours, where `gamma_rules` covers the market: 44.7% of eligible non-sports markets), and a reader of the diff who is
ready at reopening collects from holders who misread the rule.**
- Why engine-first. Halts are **unprobed** and plausibly rare on non-sports markets (planning a few a week), far under
  any live line; the engine's own hygiene is the first use: a halted market with a frozen two-sided book may pass base
  eligibility ("open, active, two-sided") and its labels then read a frozen mid, which belongs in the input-coverage
  monitor's rules.
- Columns (`A`, L 3; clock: the row's receipt). `ps_halted`, `ps_reopened_2h` (false at k - 1, true at k),
  `ps_hours_since_reopen`, `ps_halt_len_slots`, `ps_halts_7d`; on reopening, CH08's diff direction where the rules
  stream holds the market (`ps_clarified_side`, NaN otherwise).
- Expected direction. `dir_2h` at reopening: toward the clarified side; the flat class far less likely; `res_7d`
  calibration after a halt better than the pre-halt mid (the ambiguity resolved).
- Money route. Taker at reopening on the clarified side against 4-7c round trips in thin books ("not shown" unless the
  clarification is decisive); hold-to-resolution on the clarified side where it is (CH01's carry, not re-proposed).
- Falsifier. Halts are sports postponements and crypto oracle issues only, and non-sports halts are a handful a month;
  or the reopening move is already in the pre-halt mid.
- Map (counts only; part of CH261): halts a capture by category, their lengths, the share of halted rows that pass base
  eligibility, the post-reopen |move| distribution (a level count; no P&L).
- Sports arm: uncounted (postponements are CH07's). Scores: N 3, EV 1, L 3. Priors: P(census) 0.25; P(replicates)
  0.30. Parents: CH08, CH177, CH04, CH48, CH07. New: the venue's own pause as the clarification clock.

### E. The engine's own store and the fee's incidence (parents the champion / challenger design (DESIGN_V1 sections 4, 17-19), CH235 / `tilt`, CH243, CH17, CH61, CH164; literature: Glosten and Milgrom 1985 with heterogeneous beliefs, the forecast-combination literature on disagreement as uncertainty (Bates and Granger 1969), Snowberg and Wolfers 2010 on the favourite-longshot bias)

**CH259. Disagreement as the maker's volatility forecast (`disp`; an engine meta-family; the builder's call under
DESIGN_V1 section 19): the engine writes, at every capture and before any outcome, the predictions of every active spec
for every eligible market, and each visible challenger is the champion plus one family. Their disagreement for a market
in a slot is therefore not only an uncertainty measure (textbook: disagreement forecasts volatility) but a *family
attribution*: the isolate that departs from the champion names the stream that carries something for this market now.
A maker widens where the families disagree; the engine's flat class should be less likely there.**
- Why it is written here. It is free (the files exist), dense (every eligible row), causal (written in the same tick
  before outcomes) and nobody has proposed reading the engine's own store as a state; its originality is low and said
  so, which is why it ranks last.
- Columns (`A`, L 5; built at predict time from the same capture's prediction files of the **visible, non-embargoed**
  specs only, so no embargoed family's score leaks through a meta-model; the limited interactions of every
  `attrlimit_*` entry stay out of `dp_lead_family` until their dates). `dp_sd_up` (the SD across specs of P(up)),
  `dp_range`, `dp_sign_split` (the share of specs whose argmax differs from the champion's), `dp_entropy_mean`,
  `dp_lead_family` (the family whose isolate departs most from the champion, categorical).
- Expected direction. The flat class less likely and |Δmid| larger with `dp_sd_up`; `dir_*` direction: the sign of
  the departing isolate where one family dominates (a stacking read, a learner change needing a design note).
- Why not already held. The engine scores specs separately and attributes per family (section 17); no spec reads
  another's prediction. It is a learner / scoring change under section 19 and raises no K by itself if built as a
  display column first.
- Money route (gross; engine). The maker widens where the families disagree (the adverse selection avoided on large
  moves); no taker route.
- Falsifier. `dp_sd_up` adds nothing to the flat class beyond `rv24` over 28 days (|corr| with `z log rv24` > 0.8 is the
  census kill).
- Census (counts only; the builder's map): the within-slot SD across markets of `dp_sd_up` (kill if < 0.01: the specs
  agree everywhere); its correlation with `rv24`.
- Scores: N 2, EV 2, L 5. Priors: P(census) 0.70; P(replicates) 0.30. Parents: the engine's own design; Bates and
  Granger. New: the per-family disagreement as a categorical state.

**CH260. The regressive fee (`tilt` columns and a `res_7d` moderator; engine-first): the taker fee is `rate x p(1 - p)`
a share, and the buyer of the side priced p stakes p a share, so the fee is `rate x (1 - p)` of his stake: 3.8-6.65% a
leg for the buyer of a 5c side and 0.2-0.35% for the buyer of a 95c side. The fee is twenty times heavier per dollar on
the cheap side, which is where the noise buyer lives (the longshot bettor; the buyer of the cheap NO on a strong
favourite). Since 2026-03-30 the fee therefore filters cheap-side buyers in fee-on markets and not in the fee-free
remainder, so the favourite-longshot bias should be smaller in fee-on markets than in fee-free ones within tier and age,
a `res_7d` calibration contrast nobody has drawn. CH61 predicts the opposite sign for geopolitics (fee-free tails
underpriced); the panel x bin calibration decides between the two.**
- Why engine-first. The object is a calibration slope by panel, a `res_7d` reading (crypto-heavy in 21 days; the
  long-dated political markets barely represented: CANDIDATES row 26's scope note); the dated version (cheap-side traded
  moves by fee panel) is CH243's and was dropped at LT12 R1 because its F could not bind on its count; it is not
  re-proposed.
- Columns (`A`, L 4; sidecar fields; clock: the row's receipt; levels, visible, no token). In `tilt`:
  `tl_fee_per_stake_cheap` = `rate x (1 - min(p, 1 - p))`, `tl_fee_per_stake_dear` = `rate x min(p, 1 - p)`, their ratio,
  and the fee-era class from `created_at` (before / after 03-30) beside `tl_fee_free`; the `res_7d` moderator: fee panel
  x price bin x tier.
- Expected direction. `res_7d`: at a given cheap-side price, YES resolves more often (less overpriced) in fee-on than
  in fee-free markets within tier and age; the market-price reference's gain over the model shrinks in fee-on tails
  once the column is held. `dir_*`: none.
- Economic check (`COST_MODEL.md`; a reading). For a cheap-side buyer at p = 0.05 in a 0.04 market the fee is 0.19c a
  share (3.8% of stake) and the entry half-spread 1.5-2.0c a share (30-40% of stake) in the tiers below 100k, so **the
  fee is second-order to the spread at the tails for every taker**; only at a 1c spread (>= 100k) does the fee reach a
  third of the half-spread. The reading's value is composition (who buys longshots where), not a route; the longshot
  seller's rebate at the tails is `25% x rate x p(1 - p) x 0.5` = 0.02c a share and is nothing.
- Why not already held. `tilt` holds `tl_fee_ps` (per share) and `tl_rebate_ps`; `market_state` the category; nothing
  holds the fee per dollar staked by side or the panel x bin calibration.
- Falsifier. Equal favourite-longshot calibration slopes by fee panel within tier and age over the engine's `res_7d`
  window; or the difference is the category composition (geopolitics against politics) and vanishes within category.
- Boring explanation. Geopolitics is a subject, not a fee regime, and its tails behave as CH61 says for reasons that
  have nothing to do with the fee; the within-category pre-03-30 remainder is the only clean cell and is small.
- Census (counts only; part of CH261): `res_7d` rows by fee panel x price bin x tier over the engine's label store
  (kill the moderator if any contrasted cell has < 200 labelled rows in 28 days).
- Sports arm: empty (no fee-free sports). Crypto: no fee-free rows (CH251). Scores: N 3, EV 2, L 4. Priors: P(census)
  0.50; P(replicates) 0.30. Parents: CH235 / `tilt`, CH243, CH17, CH61, CH164, Snowberg and Wolfers. New: the fee's
  incidence per dollar staked by side, and the fee panel as a calibration moderator of the longshot bias.

### F. The map (parents CH251, CH240, CH252-CH260)

**CH261. The LT13 population map (counts only, k = 0): before any LT13 census, one streaming reader over a ten-day seal
(LT12's worn seal `[11-07, 11-17)` for counts, labelled; or the ordered lane's fresh seal) counts, per capture and by
category and the carry reward status with the feed adjudicating, the widenings and narrowings (>= 2 ticks) by the 2 x 2
fee x reward cell with each cell's per-capture minimum, median and mean (CH252's non-stationarity), the cell-matched
coverage and the widening units' tier x category x age distribution; the creation batches under the pinned join (the
size distribution, the cross-event share, the share of eligible rows in a cross-event batch of >= 3, batches with >= 24
complete units a day, the same-slot correlation of mates' spread innovations, the pseudo-batch coverage: CH253); the
favourite collapses a capture by category and kind, their dollar size and the category-days with one (CH254); the
first-of-day leader flips by trade class, event size and visibility, the re-flip share, two-member flips separately
(CH255); the comment field's presence, change share, burst rate and its correlation with the volume change (CH256); the
halts and their lengths (CH257); the crypto stress slots in the span from se20's klines (CH258); the fee-per-stake
distribution by cell (CH260); and, from the engine's own files as a separate light step by the builder, the prediction
dispersion's distribution (CH259). It is the cheapest census in the programme and decides whether LT13 is drafted at
all.**
- What it counts. Populations, retentions and the distributions each design's gates sit on; nothing read after any
  origin; no price target; no P&L. Memory: a per-capture streaming reader with a two-capture window, < 300 MB, net
  lane; the engine-side read a separate light step.
- Why it matters. Every LT census death on record was a count the designer had planned, not measured; LT8 died on three
  of them, LT12's CH243 on one; this map replaces the planning ranges of 0's counts table with measurements before a
  single LT13 design line is written. Kill criteria: none (a map); its numbers are the drafts' census thresholds. It also
  prints the two numbers this round most wants and cannot guess: how many widenings the fee-free unrewarded cell
  carries on a *median* capture, and whether cross-event creation batches exist at all.
- Scores: N 2, EV 3 (as an enabler), L 4.

## 3. Ranked shortlist for LT13, then the engine-first families, then the rest

Rank = census survival (a complete panel, a dense state, an innovation or a crossing, a declared DE, the MDE at the *low*
planning count under the floor, the F-MDE under its cap) x originality x plausibility x money route, with round 14's
rules 1-11, round 15's 12-14, round 16's 15-17, round 17's 18-20 and this round's 21-23 as hard constraints. The last
two columns are my prior that the idea passes its own census as written and that it would replicate given a Supported
verdict (for engine-first ideas: that the isolate beats se1 on its target over 28 days); judgements, not measurements.

| Rank | ID | One line | L | Population arithmetic (source) | Permutation structure | Primary | Planning MDE (quarter); F | P(census) / P(replicates) |
|---|---|---|---|---|---|---|---|---|
| 1 | CH252 | The payer's return: after the same widening, fee-on unrewarded books re-tighten more than fee-free unrewarded ones; narrowings the placebo | 4 | fee-free unrewarded rows 555 (median) to 4,577 (mean) a capture (CH251); widening share unprobed (0.10 planned: 55-460 units); fee-on unrewarded about 1,100; DE 6-11 by the formula, 31 by convention | market x day strata; FL on the within-market term; the panel contrast cluster-robust (rule 20); S38-S40 with the cell-matched control | `beta_fee_free - beta_fee_on` of `wd` on `ds` > 0; point condition on `nw` < half | **0.54c / 0.22c** at DE 11 (quarter 1.07c); 0.91c / 0.36c at 31; F 0.85c / 0.35c at 11 (a verdict), 1.44c at the low end at 31 (fails) | **0.22 / 0.25** (the median capture's count at the computed DE and the liquidity correlation decide; the rebate's size is the doubt) |
| 2 | CH253 | The listing batch: the cross-event batch-mates' spread innovation predicts the own next spread change; a pseudo-batch is the placebo | 3 | 20-50% of eligible non-sports ex-crypto rows (unprobed; 3,600-9,000 units a capture); batches hundreds to low thousands; DE 31 (cap 10 mates), 51 uncapped | batch x day strata; one offset per batch; FL with S41-S43; the category-slot factor as the control | within batch-day, slope of `ds_i` on `zs_bt` > 0 given the own innovation and the category factor; placebo |slope| < half | **0.17c / 0.11c** (quarter 0.34c); F 0.27c / 0.17c: a verdict at every count | **0.15 / 0.30** (coverage, the category VIF and the same-slot correlation decide; power does not) |
| 3 | CH261 | The LT13 population map (counts only; decides LT13) | 4 | n/a | n/a | n/a | n/a | n/a |
| 4 | CH254 | The loser's exit (engine-first by rule 22; `shock`; the map first) | 3 | collapses a capture unprobed (resolutions about 60 a slot derived; surprises few); category-days about 170 | n/a (a common state) | `dir_*` and the spread on the category's other favourites against se1 | engine window (a 21-day test's F-MDE about 1.6c by arithmetic) | 0.35 / 0.20 |
| 5 | CH255 | The leader flip (engine-first; `headline`; the map first) | 3 | 20-80 traded first-of-day flips a capture (unprobed); complete event-captures about 1,833 (CH240) | n/a | `dir_24h` reversal of the new leader, visibility x traded, against se1 and the `event` isolate | engine window (a mid class contrast needs 690 a capture) | 0.40 / 0.20 |
| 6 | CH256 | The comment clock (engine-first; `attn`) | 4 | the field on every row; coverage, change share and bursts unprobed | n/a | `dir_24h` YES drift and the flat class after a burst, against se1 and `participation` | engine window | 0.50 / 0.25 |
| 7 | CH258 | The shared balance sheet (engine-first by rule 22; `stress`) | 4 | every non-crypto eligible row; stress slots in 21 days unprobed (5-20) | n/a (a common state) | spread change and the flat class on non-crypto rows after a crypto stress slot, against se1 with the slot factor | engine window | 0.60 / 0.20 |
| 8 | CH260 | The regressive fee (engine-first; `tilt` columns; a `res_7d` moderator) | 4 | fee-free cells 29% of rows (CH251); `res_7d` labels crypto-heavy | n/a | `res_7d` calibration by fee panel x price bin x tier against the market-price reference | engine window | 0.50 / 0.30 |
| 9 | CH257 | The pause (engine-first; `pause`; the map first) | 3 | halts unprobed (rare) | n/a | `dir_2h` at reopening toward the clarified side | engine window | 0.25 / 0.30 |
| 10 | CH259 | Disagreement as the maker's volatility forecast (`disp`; a meta-family; the builder's call) | 5 | every eligible row with >= 3 visible specs | n/a | the flat class and |Δmid| on `dp_sd_up` against `rv24` | engine window | 0.70 / 0.30 |

**LT13 candidates (one Holm family, k <= 2; a third only by the map).** CH252 first because it is the one design in
the round whose population the map has already bounded (CH251's 2 x 2), whose event is dense on every two-sided row
(the widening), whose placebo is built in (the narrowing), whose stratum is the market-day by rule 2 and whose MDE
clears the spread floor at the median capture if the computed design effect is the formula's and not the convention's;
its honest risk is that a 0.05-0.1c rebate moves no quote, so that a Supported verdict would be composition the control
failed to remove, which the narrowing placebo and the cell-matched sampling are there to catch. CH253 second because the
creation batch is the one latent join on a dense field that no round has drawn, with power to spare and three clean
killers (coverage, the category VIF, the same-slot correlation) that the map prints before a design line is written; its
risk is that cross-event batches barely exist or are the category factor under another name. **No third candidate
clears the arithmetic:** CH254 and CH258 are common states (rule 22; about 170 category-days or 250 slots in 21 days,
F-MDE about 1.6c), CH255 and CH256 are mid-target ideas at a twentieth of the 690-a-capture line, CH257 is rare. If
CH261 finds >= 690 traded first-of-day flips a capture, CH255 enters as the third; I do not expect it. **Expected k at
census about 0.37 (0.22 + 0.15); the chance that no LT13 test registers about 0.66** (0.78 x 0.85, treating the fates as
independent, which they are not: both read the same captures and sidecars). That is the programme's record, stated in
advance; if CH261 prints a median fee-free unrewarded widening count under 40 a capture, LT13 should not be drafted and
this round's value is its engine families.

**Top engine-first families** (each raises K; build only with a real prior; the priors here are mechanisms, none is a
replicated effect; the order is the round's): `shock` (CH254: the category's favourite collapses, their dollars and the
scheduled wave as a control; the one family here the engine can read and a test cannot), `headline` (CH255: the leaders'
ordering change, traded and visible; two-member events held out to LT12's date), `attn` (CH256: the comment count's
change; check CB17's use of the field first), `batch` levels (CH253: `bt_n`, `bt_n_events`, `bt_age_h`,
`bt_cross_event` now; the mates' innovation only under `batch` after LT13's freeze), `stress` (CH258: se20's klines on
non-crypto rows with the slot factor as a control; the `regime` lesson applies and is said), `tilt`'s fee-per-stake
columns and the `res_7d` fee x bin moderator (CH260), `pause` (CH257: a hygiene column before a feature), and `disp`
(CH259: a learner / scoring note under section 19 before any column). `payreturn` (CH252's interactions) only after
LT13's freeze.

**Pre-registration sketches for the two candidates (written in LT12's shape so the designer can lift them; each a
separate primary in one Holm family).**

- **CH252 (the payer's return).** Unit: non-sports ex-crypto **unrewarded** (`listed_carry24h_v2` false on the day;
  LT12's feed coverage and disagreement gates reused; `rewards_null_*` cases counted; a market whose status switches
  inside the day excluded and counted) market x capture, two-sided at k - 1, k and k + 1 (a one-sided k + 1
  `unavailable`, counted), with `wd_k = 1[spread_k - spread_{k-1} >= 2 x tick]` and `nw_k = 1[spread_k - spread_{k-1} <= -2
  x tick]`. Panel: `fee_on` (`fees_enabled` and rate > 0 at k) against `fee_free` (flag false or rate 0), `fee_src`
  recorded; the fee-on comparison units drawn from the fee-free units' tier x category x age cells (cells with < 20
  fee-on widening units drop the fee-free unit, counted). Decision time: the row's `received_utc` at k. Primary:
  expanding-past market x UTC-day demeaned OLS of `ds = spread_{k+1} - spread_k` on `wd_k` by panel with `spread_{k-1}`,
  the widening's size in ticks, `d_k`, `|d_k|`, `log1p liquidity`, `z log rv24`, tier, category, age class and hours to end
  as controls; the tested quantity `beta_fee_free - beta_fee_on` (one-sided > 0), cluster-robust across events (CR1 on
  event, two-way event x UTC day and UTC day, p the largest); the within-market term's Freedman-Lane gate in market x
  UTC-day strata, demeaning re-applied every draw. Binding point condition: the same contrast on `nw_k` has absolute
  value < half the `wd_k` contrast. Targets: `ds`; M1 the traded-widening arm (`informed (E015)`); M2 the rewarded panel
  (`informed (LT9)` after its analysis); M3 by price bin (the dose). `DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)` (about 6
  for standalones; the convention 31 printed beside it). Planning MDE 0.54c (low) / 0.22c (high) at DE 11, 0.91c / 0.36c
  at 31; F-MDE 0.85c / 0.35c at 11 (a verdict condition), 1.44c / 0.57c at 31 (a verdict only at the high end, declared
  now; **F binds in both cases; no label-only F**). Census (the worn LT12 seal, labelled, or the ordered lane's fresh
  seal; counts only): the gates of CH252's entry. Cost hurdle: the per-fill maker's earlier return (gross); the fee-free
  taker's wait reported; the rebate's 0.05-0.1c named in the verdict text so that no reader mistakes the mechanism's
  dollar for a return. Extends: a reader over the rows and sidecar with the carry store (no sweep). Embargo: `payreturn`
  new, to the later of LT13's analysis commit and the lane's date; `attrlimit_lt13` on fee class x spread-change
  interactions in `tilt` / `paymaker`. Disclosure at the pin: CH250's cells as engine levels (after 11-18 / 11-22; no
  interaction column exists), LT12's CH244 (reward status as a within-event panel on mixed ladders; blind if pinned
  before `T_LT12`), E022's S2 (`informed (E022)`, M1 only), CH251's non-stationarity warning.
- **CH253 (the listing batch).** Join pinned by sha256 before any count: batch = markets with `created_at` within a
  120 s rolling window (closed by 120 s without a creation), >= 3 markets spanning >= 2 `event_id`s, same-event mates
  excluded from every unit's mate set, cross-event mates capped at 30 (larger a reported arm). Unit: non-sports ex-crypto
  market x capture with >= 2 complete cross-event mates (two-sided at k - 1 and k; receipt span <= 120 s at both); a
  batch-capture with < 60% of its mates complete `unavailable`, counted. State: `zs_bt` (the complete mates' mean spread
  innovation over (k - 1, k], standardised per batch by the census SD); `thin_i` (the own spread wider than the mates'
  median at k - 1; `sym` reported). Decision time: the latest mate row's `received_utc` at k. Primary: expanding-past
  batch x UTC-day demeaned OLS of `ds_i` on `zs_bt` with the own innovation, the category x slot mean spread innovation
  over non-mates, `d_i`, `|d_i|`, `log1p liquidity`, `z log rv24`, carry reward status, fee class, tier and hours to end
  as controls; one-sided > 0; material reading top-against-bottom tercile. Binding point condition: the slope on the
  pseudo-batch innovation `zs_pb` (same category and age decile, created >= 7 days apart, the same mate count; coverage
  >= 90% a census gate) has |slope| < half the batch slope (two-sided). Targets: `ds_i`; M1 the thin-follows-dense
  ordering (reported); M2 the own mid change (reported; `informed (L1-L4, E005)`); M3 the genesis arm. Clustering: CR1 on
  batch, two-way batch x UTC day and UTC day, p the largest; `DE_gate` 31 (cap 10 mates), 51 for the arm, the formula's
  value printed. Planning MDE 0.17c / 0.11c; F-MDE 0.27c / 0.17c (a verdict condition at every count). Census: coverage
  >= 20% of eligible non-sports ex-crypto rows; complete units; completeness >= 60%; batches >= 500 and batches with >=
  48 units >= 100 (unprojected); `G_eff` >= 15; same-slot |corr| of mates' innovations < 0.8 in >= 50% of batches with >=
  24 units; within-batch-day SD of `zs_bt` >= 1 tick in >= 50% of batch-days with >= 24 units; `VIF_w` <= 2.0 against the
  category-slot factor and the own innovation; |corr| <= 0.5 with the tiers, `z log rv24`, `d_i`; placebo coverage >= 90%;
  block-gate share >= 50%; venue clock <= 50%; `r_gate` <= 0.3; slope and F-MDE <= 1.0c. Cost hurdle: the batch-mate
  maker's widening rule (gross); the stale-mate taker reported against the mate's half-spread. Extends: a batch reader
  over the rows and sidecar. Embargo: `batch` new (the innovation columns), to the later of LT13's analysis commit and
  the lane's date; levels allowed now; `attrlimit_lt13` on batch-mate interactions. Disclosure at the pin: LT12's mirror
  (same-event pairs, excluded by construction), LT11's bid sum (same-event, excluded), the `event` family's and
  `participation`'s visible levels (development looks), the sports arm's dominance of the join.

**How the families would be registered.**
- **LT13 (CH252, CH253).** One Holm family, k <= 2, on the captures and sidecar with the carry store; CH261's map
  first; the fast lane (window 2027-01-21..02-11 after LT9's window, pin before `T_LT12` 2027-01-01T12:00Z, census on
  LT12's worn seal `[11-07, 11-17)` for counts, labelled `informed (LT12 census)`) or the ordered lane after LT9 with a
  fresh seal; tokens `payreturn`, `batch`, `attrlimit_lt13` filed at the freeze; the engine-first column sets built only
  as levels or after the freeze, as each entry states.
- **Engine-first (CH254-CH260).** Development families under the builder's rules, in the order of the top-families
  paragraph; `shock`'s and `headline`'s maps before their first column; `attn` after the CB17 check; `stress` with the
  slot factor as a declared control and the `regime` REVISE cited in its design note; `disp` as a section 19 note first.

**What is honest to say about all of them.** Seventeen rounds have read the venue's prices, books, volumes, rewards,
rules, fees, resolutions and the other venues' feeds, and nearly every dated object a 2-hourly capture can see has a
parent and a token. What this round adds is a clock (the widening and who is paid to return), a join (the creation
batch), two shocks from other markets (the loser's collapse, the bought headline), and four states the engine already
holds and does not read (comments, the pause, its own disagreement, the fee per dollar staked). The arithmetic of 0.1 is
unkind to half of them before any count: a common state cannot be tested in 21 days, and the engine, which reads slots
over months, is the right place for it; that is not a failure of the ideas but of the window, and the file says which is
which. The one candidate with margin is the payer's return, and its mechanism's dollar is a tenth of a cent, which the
design names in its own verdict text. Nothing here is edge until it has gone through the map, a census, frozen rules,
prospective registration and an economic check at recorded prices, and the record says that about two thirds of such
families register no test at all; the first thing that will say whether any of it is worth a design is CH261's count of
widenings in the fee-free unrewarded cell on a median capture, and whether cross-event creation batches exist.

## 4. Ideas considered and rejected, and why

### 4.0 Dropped as duplicates or closed (this round's own candidates, each with the record that closes it)

| Candidate this round | Why dropped | The record |
|---|---|---|
| Points, airdrop and volume farmers as a deterministic loser whose flow is uninformed (round trips by one wallet, both sides within minutes) | owned | CH41 (farmer-flow share: "volume-tier and airdrop farmers, wash traders ... uninformed by construction"), CH185 (the scalper's size-matched opposite prints), rounds 1-2 ("wash detection as alpha" rejected); the `wallet` token to 12-07 and E026's frozen modules cover any wallet-identity feature |
| The full set as the maker's inventory (mint YES + NO, earn holding rewards, quote both sides without collateral) | rejected before | rounds 1-2 ("holding rewards, maker-rebate loops, taker full-set arbitrage"); CH21 owns the holding-rewards mark; CH09 the ask-sum carry |
| The first crossing of 0.50 in a market-day on standalone binaries (the headline's standalone version) | owned | CH93 (the first crossing of 0.25 / 0.50 / 0.75 in 24 h and the stop cascade); CH232 / LT11 owns the 0.10 / 0.90 crossings on the rewarded panel (`bandside` to 12-12); CH255 keeps `hl_cross50` as a reported column only |
| Comment-feed sentiment | rejected before | rounds 1-2 ("worse data than CH24"); CH256 reads the count's change, not the text |
| The own market's spread at its own UMA proposal | owned | CH02 (the proposal-window carry), CH04 (zombie quotes after the decision), CH221 (the siblings at the proposal); the engine's base eligibility excludes proposed rows |
| The one-sided book's refill (one side returns) as a dated event | owned | CH35 (quote-vacuum re-quoting), CH130 (the pair at birth), CH10 (placeholders); rule 16 treats one-sided members as `unavailable` |
| The `n_levels` innovation (a level appears behind the touch: a maker arrived) | owned; token | CH197 (patient money), CH214 / LT9 (`pool`: in-band depth arrival), CH169; the `book` / `book0` tokens to 2027-02-14 |
| The event's displayed liquidity innovation as the ladder's maker arrival / exit | owned | CH233 / LT11 and CH244 / LT12 own the event join on spreads; `participation` (se16, to 11-25) holds event liquidity as a level; CH174 / E022 the liquidity-against-depth reading |
| The scheduled resolution wave (`end_date` density in the category) as the maker's clock | owned; a control | CH98 (redemption-cash days from scheduled ends and OI), CH68 (redeployment), CH40 (the late-life schedule); folded into `shock` as `sh_cat_due_24h` (rule 23) |
| The series pair's mirror (the current and next instance of one series; the dense instance leads the thin one's spread) | a replication lane | CH245 / LT12 (the mirror; two-member neg-risk events), CH50 (series roll flow), CH12 (dominance pairs); round 17 listed the fine-clock mirror as a replication lane, not a proposal; the same applies here |
| The Gamma `liquidity` innovation alone, with an unmoved touch, as the venue's own depth meter | owned; token | E022's `hollow` (liquidity against depth, to 11-18), CH214 / LT9 (`pool`), CH203 (the quiet book, died at CS8), CH174 |
| The symmetric width innovation (both touches moved apart with no mid change: the quoter's volatility update) | closed | CH147 (the breathing book), CH192 (implied against realised; died at LT7's CC7; `ivr` withdrawn) |
| The fee's incidence per stake as a *dated* test (cheap-side traded moves by fee panel) | closed | CH243 (dropped at LT12 R1 MUST 1: F must bind, kill line about 522 fee-free traded movers a capture against CH251's medians 64 / 7); CH260 keeps the calibration reading only |
| Sponsored reward configurations as a signal of a sponsor's forthcoming interest | rare; owned | round 17's 4.0 ("reward-rate re-ratings and sponsor arrivals ... rare"); CH206 (the reward start), CH215 (the scheduled end), CH212 / LT9 (`rwblink`) |
| Polymarket US (QCX) as a second book under the same brand on the same questions | a fetch; not the venue | `COST_MODEL.md` section 2 ("not the venue of AREPO data and is not modelled"); L 1; no public coverage known to AREPO's documents |
| Causing a flip, a vacuum or a halt (any manipulation route) | rejected before | rounds 1-2 ("manipulation of any kind"); CH255 reads other participants' prints and is a fade |
| The human book's lag (fee-free unrewarded old markets catching up with the category's move) | taker route; owned | CH04, CH103 (hidden long-dated books), CH149 (dormant deep ladders), CH166 (the lead is where the liquidity is), CH220 (dormancy); the catch-up is a mid target on an illiquid panel whose round trips are 6-10c |
| The common-quoter panel from touch-size signatures (identical odd sizes across markets = one bot; its slow books follow its fast ones) | owned | CH36 (same-key outages mapped from vacuums), CH131 (quoter-type footprints), CH148 (size roundness and churn); CH253 reads the creation batch instead, a timestamp join with no signature matching |
| The tick-asymmetric twin (one member at 0.01, the other at 0.001: the fine book leads) | LT12's population | CH245 / LT12 (`mirror`); CH15, CH86 own the tick regime |
| LLM-agent flow (schedule-clustered, headline-driven, late) | owned | CH172 (program against human), CH54 (builder codes), CH162 (trains and herds), CH208 (the minute of the news) |
| The market-sort rank (`page_index`) innovation as a display promotion / demotion | owned; unverified sort | CH236 (the predictable demotion from the top-volume frame), CH176 (the front page as a clock); `page_index`'s sort order is AREPO's collector's, to be confirmed from its code before CH255 uses it as a visibility proxy |
| The venue's category reassignment as a within-market fee shock | rare | CH53 (the fee rollout), CH152 (reward-rate shocks); no count of reassignments exists |
| The venue tilt, a category's volume decile, the reward epoch, weekends, hours | venue clocks / closed | round 13's rule 8; CH158; CH24; HB1's nulls on time of day and weekday; the `regime` family dropped |
| Any state LT9, LT10, LT11 or LT12 tests under a new name (the band break, the pool, the omission, the fine-clock spread, the collateral weight, the bid sum, the 0.10 / 0.90 crossing, the twin's spread, the sibling shock x status) | owned | CH212-CH215, CH222-CH224, CH232-CH234, CH244-CH245 and their tokens `bandbreak`, `pool`, `rwblink`, `kxbook`, `dollarw`, `nrslack`, `bandside`, `mirror`, `mixedlad`; nothing here reads them |
| Anything wallet-level | sealed / frozen | E026 registered, its modules frozen to 12-07; the `wallet` and `wallet_skill` tokens |

### 4.1 Ideas rejected on the design rules, and why

- **Common states as live primaries** (rule 22): the category's losses (CH254), crypto stress (CH258), the venue tilt,
  a category's attention day; each has about 170 category-days or 250 slots as its clusters in 21 days, a spread class
  MDE of about 1.0c and an F-MDE of 1.6c; each is an engine family here, read over months.
- **Any whole-panel class state on a mid target with fewer than about 700 units a capture in its smaller class, or any
  whole-panel mid slope under about 1,700 units a capture** (0.1's table): the leader flip's reversal (CH255: 20-80 a
  capture), the comment burst's drift (CH256: 25-75), the halt's reopening move (CH257: a few a week), the favourites'
  dip (CH254); each is a column, an arm or a map here.
- **Level states as primaries** (the batch size, the comment count, the fee per stake, the dispersion level, the
  leaders' gap): pattern 3; each is a control, a column or a moderator.
- **Rare-event states** (the halt, the collapse, the flip outside coin-toss races, the stress slot): pattern 1; counted,
  never primaries.
- **Panels used as states** (rule 20): the fee class and the carry status are market-level constants and enter CH252
  only as a panel contrast of within-market contrasts, with cluster-robust inference across events and the planning MDE
  quoted as a contrast of two within-market coefficients.
- **Latent joins without a pin** (rule 21): a batch window chosen after seeing counts, a signature join without a
  placebo, a batch that includes same-event mates; CH253 pins the window, the size, the cross-event rule, the cap, the
  completeness rule and the pseudo-batch before any count.
- **Reading the unit's own outcome** (rule 23): none; `shock` reads other markets' collapses received before the
  origin, the unit's own event excluded; the scheduled wave is a control.
- **Label-only F chosen for power:** none; CH252's F binds at both planning ends at the formula's DE and the design
  says what happens at the convention's; CH253's F binds everywhere.
- **E015, E022, LT9, LT10, LT11 and LT12 moderators during their windows.** The fast lane follows LT9's window; the pin
  before `T_LT12` keeps CH252 blind to CH244's carry reading; CH252's M1 is `informed (E015)` and M2 `informed (LT9)` and
  both are reported arms.
- **Taker routes as primaries anywhere.** 2.9-9.9c hurdles against grosses of a fraction of a cent; every taker route
  here is reported, never a verdict; CH260 says in its own entry that the fee is second-order to the spread at the tails.
- **Maker mark-out objects** (adverse selection judged on fills). J4-R's and CB13-T's holdouts; every maker route here is
  gross, no fills.
- **Trade-sample or monitor units as primaries** (round 14's rules 1 and 6): none; the monitor's prints and the sample's
  trades enter only as engine inputs (`flow`, `movetype`, `printage`) under their tokens.
- **Decided-but-unresolved carry, longshot ask-selling, round-number walls, tick-regime discounts, reward cliffs,
  holding rewards, genesis, seed anchors, series rolls and base rates, mention baskets, external anchors, barrier
  confusion, quoter grain, wake-up prints, breathing book, mint share, turnover, synchronous prints, exit pressure,
  cost maps, quoted against traded, walked flow, trains, attention surges, breadth, class-conditioned longshots,
  arrivals and cancellations, the age of the move, opens and closes, concentration, hollow liquidity, program against
  human, last-mid proxy, front page, silent edits, races, jump or grind, high-water mark, overhang, alone or with the
  crowd, the farmer's choice, clips, the makers' vote, deadline moves, sibling birth, provenance, overdue, grind at the
  capture clock, the hour-held move, implied against realised, absorbed flow, resistance, patient money, the last-print
  anchor, calendar theta, the resolution-source class, two minutes of quote news, reward yield, the sweep clock, the
  quiet book, the market's own clock, steam, the reward start, desk-set dispute insurance, the minute of the news, the
  farmer touch, two minutes before the origin, the ladder that travelled, the display's omission, the band break, the
  pool splits, the scheduled end, large prints without a sample, row quality, the display's disagreement, the touched
  book, dormancy, the siblings' proposal window, the venue that traded first, the other venue's makers flinch first, the
  hedged maker's price, the slow sibling, the resolver's clock, the entity clock, rule freshness, the published close,
  the three-venue panel, the in-game state, the cheap side's cliff, the arb's footprint, the dollar weight of a move,
  the collateral tilt, the predictable demotion, the parent's other children, the ladder's headroom columns, the rules'
  class, the boundary map, the reverse fine clock, the venue's third price, the fee as the price of urgency, the farmed
  half, the mirror, the no-link twin, the elimination game, who printed, the dip side, who pays the maker, the LT12
  map.** CH01-CH251: not re-proposed; where an idea touches one, the parent is named and the new clock, population,
  state or join is stated (CH252 on CH250 / CH243 / CH39 / CH147 / CH169 / CH213; CH253 on CH22 / CH142 / CH154 / CH188 /
  CH36 / CH131 / CH158 / CH184 / CH245; CH254 on CH98 / CH68 / CH67 / CH24 / CH128 / CH175; CH255 on CH93 / CH176 / CH157 /
  CH20 / CH110 / CH23; CH256 on CH157 / CH24 / CH97 / CH176; CH257 on CH08 / CH177 / CH04 / CH48 / CH07; CH258 on CH158 /
  CH36 / CH184; CH259 on the engine's own design; CH260 on CH235 / CH243 / CH17 / CH61 / CH164; CH261 on CH251 / CH240).

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
`EXPERIMENT_LEDGER.md` (the tail from the 10-22 seals and census entries through the LT12 design-text freeze of 10-23
~23:45Z: LT5-LT8's census drops and closures, E022's registration, LT9's and LT10's freezes and round-6 / round-7 tokens,
the CH240 map, LT11's draft, R1, re-check and freeze, its code-freeze REJECT, CB8-B's empty frame, variant, ruling and
q0165b / q0166b, the CH251 map entry, CH242's engine census, LT12's draft, R1, re-check, verification and freeze, the CB4
/ CB5 extract deviation, the engine's input monitor; the CB8-W smoke FAIL entry of 10-22 for its 5-of-192 count);
`CH251_MAP_2026-10-23.md` and `CH240_MAP_2026-10-23.md` (in full); `LIVE_TESTS_12.md` (sections 0, 4, 5 and 7 in full);
`LIVE_TESTS_11.md` (sections 0 and 7 in full); `signal_engine/STATUS.md` (10-24 00:20 UTC+1); `signal_engine/NORTH_STAR.md`;
`signal_engine/CANDIDATES.md` (the round 12-17 notes, the "not candidates" list, the builder table rows 1-26, the LT11 and
LT12 freeze requests and replies, the CH242 split note); `signal_engine/DESIGN_V1.md` (sections 2 and 3); `COST_MODEL.md`
(in full: the fee and rebate facts, the calibration tables, the F4 / F5 reassessment, the rules for economic stages, the
limitations); `EXECUTION_COSTS.md` (in full); `NEW_STREAMS_2026-10-19.md` (sections 1-5); `COLLECTION_HOST.md` (the host,
layout, jobs and retention sections); `LIVE_TRADE_MONITOR.md` (what runs, storage, the pilot); `CROSS_VENUE_LIVE.md` (what
runs, the frozen spec); `CREATIVE_HYPOTHESES_2026-10-31.md` (round 17 in full); `-30.md` (round 16's 0.2 rules 15-17);
`-29.md` (round 15's 0.2 rules 12-14); `-28.md` (round 14's 0.2 rules 1-11 and its structural facts); the lead sentences of
CH01-CH251 from all seventeen rounds (for the duplicates table and the parents named), and the lead paragraphs of CH02,
CH04, CH08, CH17, CH20, CH22, CH24, CH35, CH36, CH40, CH41, CH50, CH54, CH61, CH93, CH97, CH98, CH110, CH130, CH142,
CH145, CH150, CH157, CH158, CH162, CH166, CH169, CH176, CH185, CH206, CH213, CH221; the keyword checks across all
seventeen rounds for wash, airdrop, points, comment, `accepting_orders`, sponsor, manipulation, halt, disagreement,
Polymarket US and fee-per-stake (the novelty gate of section 4.0). Two facts (**brief**) come from the orchestrator's brief
and the parent branch's commits `bacc8e9c` (LT11 code re-check ACCEPT_WITH_FIXES; the registered-seed test run disclosed)
and `6f0071e7` (CB8-B coverage audit FAIL 87 / 119 = 73.1% < 90%, not testable, counted), which post-date this worktree's
branch point `dab6c593`. Still no host probe, no network and no data-dumps read. Every count is as the named document
states it on 2026-10-24; nothing was recomputed except the planning MDEs from round 14's stated formula and the derived
resolution density of fact 4 (a subtraction and a division, marked as planning only).

### 5.2 External literature (named, not fetched)
Foucault, Kadan and Kandel 2005 (the cost of a resting limit order and the maker's return to the touch); Colliard and
Foucault 2012 and Malinova and Park 2015 (make / take fees and who the subsidy reaches); Parlour 1998 and Foucault 1999
(the limit-versus-market choice as a function of the spread); Chordia, Roll and Subrahmanyam 2000 (commonality in
liquidity); Hasbrouck and Seppi 2001 (common factors in order flow and liquidity); Brunnermeier and Pedersen 2009
(funding liquidity as the maker's shared constraint across assets); Thaler and Johnson 1990 (prior losses and subsequent
risk taking); Coval and Shumway 2005 (loss-driven behaviour of market makers); Hanson and Oprea 2009 and Rhode and
Strumpf 2004 (manipulation attempts in prediction markets lose money and move prices briefly); Hartzmark 2015 (rank
effects on attention); Barber and Odean 2008 (attention buying); Glosten and Milgrom 1985 (the maker's update);
Bates and Granger 1969 (forecast combination and disagreement); Snowberg and Wolfers 2010 (the favourite-longshot bias:
misperception against risk love); the venue's fee, rebate and liquidity-reward documentation as `COST_MODEL.md` section
2 quotes it.
