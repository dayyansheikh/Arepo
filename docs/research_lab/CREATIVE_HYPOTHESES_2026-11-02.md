# Creative hypotheses, round 19: the blind spots, the one-shot lane and the engine at the touch (2026-11-02)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-29 from 23:38Z on parent
`8dd7011b` (`chore/arepo-claude-setup`, fast-forwarded twice into the worktree `feat/creative-r19`); the file carries the
round's planned date as earlier rounds did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md`
(CH35-CH59), round 3 `-17.md` (CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md`
(CH118-CH130), round 7 `-21.md` (CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10
`-24.md` (CH169-CH179), round 11 `-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201), round 13 `-27.md` (CH202-CH211),
round 14 `-28.md` (CH212-CH221), round 15 `-29.md` (CH222-CH231), round 16 `-30.md` (CH232-CH241), round 17 `-31.md`
(CH242-CH251), round 18 `-11-01.md` (CH252-CH261); this file starts at **CH262** and repeats none of them. Where an idea
builds on an earlier one, the parent is named and the new mechanism, clock, population, unit or join is stated. Every
number quoted from an AREPO document is a development, census, map, probe or operational figure, not evidence. One file;
no code, no queue specs, no other commits. **No network request, no host probe (no `ssh oracle`) and no `data-dumps` read
were used for this round** (by instruction); every count below is taken from a named AREPO document (`EXPERIMENT_LEDGER.md`
through its 2026-10-29 entries, `CH261_MAP_2026-10-28.md`, `reviews/LT13_CHALLENGER_R1_2026-10-28.md`,
`reviews/LT13_Q0717_RESULT_2026-10-29.md`, `reviews/LT13_Q0717_RECHECK_2026-10-29.md`, `LIVE_TESTS_13.md` sections 0-1,
`signal_engine/STATUS.md` (10-29 23:58 UTC+1), `signal_engine/NORTH_STAR.md`, `signal_engine/CANDIDATES.md`,
`signal_engine/DESIGN_V1.md` sections 2-4, `COST_MODEL.md`, `NEW_STREAMS_2026-10-19.md`, `COLLECTION_HOST.md`,
`queue/README.md`, `data_catalogue/README.md`, `CROSS_VENUE_LIVE.md`, `LIVE_TRADE_MONITOR.md`, the lead sentences of
CH01-CH261 and rounds 14-18's design rules) and is named as such. Where no count exists the entry is marked **unprobed**
and the counts-only map of section 2 F (CH269) is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities 2026-10-19 and 10-21; orchestrator brief for round 19).** Original
hypotheses about how money could be made on Polymarket lead the programme, and the owner wants **more prospective live
tests**, each light (small memory, the `net` lane, a stream the host already captures) and built to survive the failure
modes that killed most earlier designs. So every idea below states its expected census population, its unit of
independence, a planning MDE against the cost model's realistic hurdles and the cheapest kill test, and says whether it
is a live test, a registered measurement, an engine family or a map. Category-agnostic, sports and crypto as the owner's
parameters. No data-rights topic is raised. Nothing here reads any registered live test's objects before its analysis;
nothing here reads LT11's, LT12's or LT13's window captures for any census. Round 14's design rules 1-11, round 15's
12-14, round 16's 15-17, round 17's 18-20 and round 18's 21-23 **bind here unchanged**; this round adds four (0.3).

**What this round does differently.** Eighteen rounds have given a parent to every row, sidecar and sweep field the 2 h
capture carries (the inventory of CH01-CH261 was read in full for this file; section 4 lists what was checked). Three
places are still unread, and they are unread for *structural* reasons, not for lack of ideas: **(a) the engine's blind
spots**: base eligibility drops every row with a UMA proposal at the origin and every mid outside [0.02, 0.98]
(DESIGN_V1 section 2), and round 17's rule 19 bars any live primary from reading a resolution, so the two populations
where the venue's money is *mechanical* (the decided side during the proposal window, the price tails below the display
threshold) have no home in either track; **(b) the within-market design effect**, which killed more tests than any count
gate (0.0), does not exist for a state that happens *once per market* (a proposal, the close, a first crossing), if the
unit is one observation per market and the null is a between-market permutation inside a census-fixed stratum; **(c) the
engine's own write-once stores** (predictions at every capture before outcomes, label states, the quotes file of every
binary market) are a dense, light, prospective stream that no test or family reads as a *history*. Each of the eight
entries below sits in one of those places. The round's first live candidate (CH263) is a **registered measurement** of a
route the programme has named since CH01 and never measured; its second (CH262) is the economic check of the engine the
owner's own standing rule asks for; its third (CH267) is the one verdict-shaped test here whose arithmetic clears the
floor at the low planning count. Two entries (CH265, CH268) are engine families, one (CH266) is a map with a live sketch
behind it, one (CH264) is the second measurement, and the last (CH269) is the counts-only map that decides the rest.

### 0.0 The recurring death causes (the ledger's record, counts only; what each idea below is built against)

The scout's tally of `EXPERIMENT_LEDGER.md` (4,737 lines): **LT3-LT8's censuses dropped 23 candidates and 3 more died
before their census; the survivors are E015 and E022.** LT5, LT6, LT7 and LT8 closed with zero tests; LT11 (k <= 3,
P(no test) about 0.35) and LT12 (k <= 2, P(no test) about 0.60) are frozen; LT13's CH252 is **withdrawn** before its census
(`withdrawn_pre_census (fee reading unresolved)`; re-check 10-29) and CH253 goes to census alone, `informed (q0717)`.
The causes, in the order of how many designs they took:

1. **Units per market, not units.** A state that occurs rarely per market empties the market x day stratum: LT8 CH204
   3.35 scheduled markets a capture against 1,200 (10-23); LT6 K 142 projected units against 8,400 (10-22); CB8-W 5 of 192
   worn markets against 20 (10-22); CH188's births 0 in 9 days; CH187's `end_date` edits 3 in 9 days; CH255's traded
   first-of-day flips 11 a capture against 690 (CH261). **Round 14's lesson stands: the count was never the problem where
   the state is dense; the problem is recurrence within market.** The one-shot lane (rule 24) is this round's answer:
   where the state happens once per market, stop asking for recurrence and use one unit per market.
2. **The MDE gate, not the count gate.** LT5 F died at 1.01c against 0.5c with every count and correlation gate passing
   (DE 10.3 from family clusters of 465); LT3 E017 at 1.83c against 1.0c; the ledger's own reading on 10-22: "E022's DE
   6.196 means LT7's five tests likely drop". Whole-panel families plan at DE 31 and that convention alone puts a 2 h mid
   class contrast at about 690 units a capture in the smaller class (round 16's table).
3. **Held share, strata and persistence.** LT8 CH202 held 0.067 against 0.15; LT4 E020 strata 0.055 against 0.50; LT6 V
   passed every count and died on its own persistence (corr 0.595 with its lag): level states pay twice.
4. **Source coverage and field semantics.** CB8-B's books on 73.1% of market-days against 90% (10-24); CB11-W one fee
   category against six; `gamma_rules` covering 44.7% of eligible non-sports markets; CH194 on a venue-computed field;
   LT7's day lost to the `clob_rewards` null (62%) and switching (11.8%); and now **q0717**: the served `fee_schedule` of
   23,888 non-sports ex-crypto markets moved to `rate 0` / `zero_fees` in one capture pair (10-20T16:31Z -> 18:31Z; 1,800
   former sports markets entered the non-sports population at the same step), so CH252's fee panel ceased to exist under
   the design (post-step fee-on unrewarded complete units mean 101.6 / median 91 a capture, which at CH261's widening
   share 0.153 is about 15 widenings a capture, about 8 at retention 0.5, against the count gate of 77). **Whether the
   venue really charges zero fees is not verified** (re-check). A panel
   whose content the venue can change in one capture is a hazard every fee-class entry carries; this round reads the fee
   only as a cost line (origin-row schedule with the docs rate as the conservative bound), never as a panel.
5. **Non-stationarity.** A block of captures carries the count: CH243's fee-free traded movers medians 64 / 7 against a
   mean 346; CH252's fee-on arm median 15 against mean 139 (0.108 < 0.25). The venue-clock gate (<= 50% of units in one
   slot) and the per-capture distribution are printed by every census here.
6. **Control availability and placebo coverage.** CH253's pseudo-batch placebo 0.755 against 0.90; D118 / D119 on control
   pairing; LT12's feed-disagreement gate. The rule this round follows: the placebo lives on the same unit (a second
   crossing constant, the same market a day earlier, a shuffled prediction file), never on a separately drawn control pool.
7. **Common states.** `regime` dropped by the engine; CH254 and CH258 engine-first by arithmetic (about 170 category-days
   in 21 days, F-MDE about 1.6c). Nothing below is a common state; the one venue event of the fortnight (the fee step) is
   a single cluster and is treated as a disclosure, not a test.
8. **The cost floor.** F4 / F5's replicated +0.94 / +1.03c gross against 2.41-3.52c hurdles ("forecasting facts, not
   routes"); taker $100 round trips 2.9c (>= 100k) to 9.9c (< 1k); `COST_MODEL.md` 8: "a candidate under about 2c gross
   is not worth a registered economic test in any tier below 100k" and "the only cost regime below 1c is passive entry in
   >= $100k markets held to resolution or long horizons, plus fee-free categories". Three of the eight entries here are
   hold-to-resolution or spread objects for that reason, and the one that reads a mid (CH262) is a measurement of gross
   against those hurdles, not a route.
9. **Lanes and memory.** q0085 OOM at 1,200 MB, q0183 / q0185 `MemoryError` at 800 MB, q0116i at the 14,000 MB limit; the
   8-day snapshot retention removed 80 of CH261's 180 slots before the map ran. Light means **`mem_mb` < 500** (exempt from
   the exclusive-job drain and the 02:45-05:30Z blackout; `queue/README.md`), the `net` lane, and inputs the host keeps
   longer than 8 days (the engine's `quotes/` and `features/` 45 days, `predictions/` 35 days, the label logs, the keyless
   streams' day files). Every reader below is specified against that.

**What survived and why (E022, restated from round 14, plus two readings this round adds).** A continuous state on
every unit of a complete panel, within-market spread, recurrence within market, small clusters, two streams the host
already wrote. **Reading one (rule 24):** recurrence within market is one way to a stratum; *one unit per market* is the
other, and it is the only way for states that occur once. **Reading two (rule 26):** a verdict needs a prediction and a
null; a *measurement* needs an estimand and a CI; a route whose payoff is the resolution itself (the decided carry) is
the second kind, and the programme has no evidence role for it, which is why CH01 is eighteen rounds old and unmeasured.

### 0.1 What changed since round 18 (ledger through 10-29; CH261; LT13 R1 and the q0717 re-check; STATUS 10-29)

- **The CH261 map ran (q0701, 93 captures of [10-20T04:31Z, 10-27T22:31Z], 7.75 days; peak RSS 642 MB):** fee-free
  unrewarded widenings median 1,857.5 a capture (the 40 line cleared), fee-on unrewarded median 15 / mean 139.3; CH253
  units 2,965 a capture (0.873 of eligible rows in a cross-event batch of >= 3; same-slot correlation 0.059; category VIF
  1.001; pseudo-batch coverage 0.755 < 0.90); traded first-of-day flips 11 (CH255 does not enter); favourite share of
  two-sided rows 0.054; category-days with a collapse 7 non-sports / 6 sports; comment change share 0.0034 with
  correlation 0.708 to the event volume change (CH256's clock is volume under another name).
- **LT13 R1 GO_WITH_CHANGES (10-28)**, then **q0717 (10-28, peak RSS 344.5 MB)** found the fee step above, and the re-check
  (10-29) applied the declared rule verbatim: **CH252 withdrawn pre-census**; CH253 to census `informed (q0717)`, with its
  category control largely lost (about 90-95% of its rows `other:zero_fees`); the LT13 design-text freeze is still to
  come, before `T_LT12c` (about 11-18). Every ten-day span from 10-28 to 02-11 is some test's seal or window, as round 18
  mapped it; nothing below reads a registered test's window captures for a census.
- **The engine (STATUS 10-29 22:58Z):** K = 11; the LightGBM models lead the logistic champion by about 0.045-0.048 nats
  on `dir_2h` over 9 days; first promotion reads about 11-04 (`se-promotion-v2`); `se26_lgbm_mm_full` new; the 10-29 refit
  peaked at 3,494 MB; **`pause` (CH257) killed at its map** (0 eligible rows halted in a day; 7 of about 257,600 rows false,
  none open and two-sided); `stress` (CH258) is the next round-18 family after its census; `attn` waits on the CB17 check;
  `disp` would be a display column; for `res_7d` the champion is no better than the market price (10-24). The engine's
  stores: `quotes/<capture>.parquet` (every binary market of a complete capture: bid / ask two-sided only, status code),
  `features/`, `predictions/<capture>/<model>.parquet` (write-once uint16, before outcomes), label logs and daily label
  states; proposed host retention 45 / 45 / 35 days (`data_catalogue/README.md`).
- **Ops:** E009 / E010 end 11-03; E011 11-10; LT2's analysis from 11-13; E015's from 11-15; E022's window 10-26..11-16;
  E026's receipts 10-25..11-15 (analysis from 12-06); LT10's window 11-10..12-01; LT11 11-18..12-09; LT12 12-10..12-31;
  LT9 12-30..01-20 (slides); LT13's fast lane 01-21..02-11 (CH253 alone, if it survives). Guards raised to 50 GiB;
  `data-dumps` 45.2 GiB with 36.8 in releases. No live test registered after 10-24.

### 0.2 The census arithmetic, restated once, with the one-shot reading

Round 16's 0.1 table binds (the effective count at which the pessimistic MDE equals the floor, over 21 days, 252 captures,
planning effective share 0.8): a 2 h mid class contrast needs about 690 units a capture in the smaller class (1,740 with
F); a whole-panel mid slope about 1,680 (4,200 with F); a spread slope about 105 (260 with F); a 1 : 11 spread class
contrast about 24 event market-days a capture. Round 18's reading on common states (about 170 category-days) binds.

**The one-shot reading (new).** For a state that occurs once per market, the unit is the market, the cluster is the event
in which it occurs (a ladder's members are proposed or close together), and the design effect is the LT11 formula at the
event's member count, `1 + (m - 1) x 0.02`, about **1.0-1.2** for standalones and small ladders (the convention 31 was
derived for twelve-slot panels and is quoted beside it, as the rules require, but it is not the design effect of a
one-shot unit). The arithmetic then runs on **units per window, not units per capture**: a spread class contrast at SD 2c
with `n1 = n2 = 1,500`, DE 1.1, VIF 1.3 gives `3.47 x 2c x sqrt(2 / 1,200) x sqrt(1.1) x 1.5 x sqrt(1.3)` = **0.49c**, under
the 1.0c spread floor; a mid-level measurement at SD 1.3c with `n = 5,000` one-shot units gives 0.04c. The non-sports
ex-crypto universe produces about **740 resolutions a day** (round 18's fact 4, derived) and therefore about that many
closes, proposals and last captures a day, so a 21-day window holds about 15,000 one-shot units before any filter: a
population that no twelve-slot panel of the same markets could match, because the proposal or the close is read once and
every other slot of that market is irrelevant to it. The price is that the Freedman-Lane null changes form (rule 24).

### 0.3 Design rules (rounds 14-18's 1-23 bind unchanged; four additions)

24. **The one-shot unit.** A state that occurs at most once per market (a UMA proposal, the scheduled close, a first
    crossing of a venue-published display or tick constant, a listing) is tested with **one unit per market** at a slot
    declared relative to the event (the first capture at or after it; the last capture at least 2 h before it); no
    within-market stratum exists, so the permutation null is a **between-market** permutation of the state inside a
    census-fixed stratum (category x liquidity tier x the event's UTC day, x rule class where a rule class is read), the
    cluster is the event (cap 10 members; larger a reported arm) with CR1 on event and two-way event x UTC day, p the
    largest; the twin where the design needs one is the *same market at a declared earlier slot* (the close's T - 26 h,
    the crossing's previous day); planning `DE_gate` is the LT11 formula at the event's member count, with 31 printed
    beside it; the identification gate (within-stratum SD of the state >= its between-stratum SD) replaces the IQR gate.
25. **Zone floors.** Where a population sits on the 0.001 tick (mid < 0.04 or > 0.96 by the venue's published rule), the
    0.5c mid and 1.0c spread floors are replaced by the zone's **recorded round trip** at the census (the zone's median
    half-spread on recorded touches plus the fee at that price from the cost model's formula, with the docs rate as the
    conservative bound), declared before any target is read; one tick of the zone (0.1c) is the spread floor's analogue
    (rule 8's logic); the cents floors bind everywhere else.
26. **Registered measurements beside verdict tests.** A hold-to-resolution route whose payoff *is* the resolution (the
    decided side's carry, the overdue mid's premium) cannot be a live primary (rule 19) and is outside the engine
    (eligibility drops proposed rows and the tails); it is registered as a **measurement**: evidence role
    `prospective_measurement`, k = 0, no Holm, no verdict; estimands, CIs, the cost line and the capacity line declared
    before the window; the resolution read **after** the window as the route's payoff, never as a prediction target;
    the ledger records *measured* with the numbers, never *Supported*; a measurement never changes a verdict, is never
    pooled with one, and is never re-read as a test. The `science-reviewer` accepts or refuses the role at the freeze.
27. **The engine's own stores as inputs.** A state built from `predictions/`, the label logs or `quotes/` reads only
    files whose capture is at or before the origin and only visible, non-embargoed specs at a pinned spec version; a spec
    that stops predicting inside a window makes the unit `unavailable`, counted, never filled; a family that stacks on
    the engine's own outputs needs a DESIGN_V1 section 19 learner / scoring note **before any column**.

**Hygiene that binds every idea** (round 14's paragraph applies: decision time is the latest input's own receipt; targets
start after it; nothing reads outcome fields of the unit except engine-first `res_7d` features and, under rule 26, the
declared payoff of a measurement; the primary of a verdict test is a within-stratum contrast or slope by expanding-past
demeaned OLS, the permutation gate in the census-fixed stratum is binding, the liquidity-tier correlation gate and the
AR(0.9) scenarios bind, and F in LT7's one-rule form is a verdict condition where its census F-MDE is under the target's
floor; a label-only F chosen for power is rejected). Sports stays a parameter (every non-sports entry reports its sports
arm uncounted; **since the fee step, sports classification follows the vendored rule on post-step values with 1,800
re-classified markets disclosed**, as the re-check requires). Nothing here is a maker mark-out object; J4-R's and
CB13-T's holdouts are not read. Nothing here reads LT9's (`bandbreak`, `pool`, `rwblink`), LT10's (`kxbook`), LT11's (`xw`,
`cl_sib`, `xo`), LT12's (`zs_D`, `shock x unrew`) or LT13's (`batch`) objects, their twins or targets, or their windows.

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5)** as round 18 defined it (5 = a pure
reader over stores the host already writes with the population counted by a named probe; 4 = pure reader, population
bounded above by a named count; 3 = pure reader with an unprobed population, or a map first; 2 = a stream whose coverage
is unprobed; 1 = fetches or weeks). **Priors** are two numbers, both my judgement: P(census) = the idea passes its own
census or map as written; P(replicates) = given a Supported verdict (or, for a measurement, a net above its cost line),
the number holds on a second prospective window; for engine families, that the isolate beats se1 on its target over 28
days.

**Planning-MDE arithmetic (round 14's, stated once).** Class contrast: `MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x
sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; a level against a declared constant: the same without the second count; slope
per SD times the tercile gap (about 2.2 SD). `n_eff` = 80% of raw. `DE_gate`: 31 (events capped at <= 10 members), 51
(uncapped), 6.196 (mover families), the LT11 formula `max(floor, 1 + (m - 1) x 0.02)` where the cluster is small (252
captures of one market give 6.0; a one-shot unit in a 3-member event 1.04). `VIF_w` 1.3 for row and sidecar states, 1.5
for book states. SDs: 2 h mid change 4c overall and 4.4 / 1.4 / 1.3 / 1.9c by tier (< 1k, 1k-10k, 10k-100k, >= 100k; the
cost model's calibration); spread change 2c; spread change in the 0.001 zone about 3 ticks (0.3c; **unprobed**). F-MDE =
`MDE x sqrt(2 / (1 - max(0, r_w)))` (planning `r_w` 0.2 gives x 1.58). Every MDE is quoted at the low and high planning
counts and at a quarter of the low one.

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture 42,161-51,790 (DESIGN_V1 sections 3 and 16); eligible non-sports on single captures 18,232
   (CH199's filter) and 18,349 (`parentsib`'s census). Base eligibility: binary, open, active, two-sided, spread <= 0.10,
   mid in [0.02, 0.98], end after the origin, **no UMA proposal in the origin sidecar row** (DESIGN_V1 section 2).
2. **Resolution density (the CH242 census; CANDIDATES row 26):** 133,559 markets with ids from the 10-12..10-23 captures,
   131,951 `resolved`, 588 `split_50_50`, 1,020 `not_found`; non-sports 46,596 (crypto 37,695, finance 1,417), sports
   85,943; by `min(p, 1 - p)` at the last origin: **21,516 at <= 0.05**, 24,258 in (0.05, 0.15], 20,110 in (0.15, 0.3],
   66,655 in (0.3, 0.5]. Derived, planning only: non-sports ex-crypto about 8,900 over about twelve days, **about 740 a
   day, about 60 a 2 h slot**; the share of those that pass through a visible proposal state at a capture, the share
   that are overdue with an interior mid, and the share whose last origin sat under 1c are **unprobed**.
3. **The cost model (`COST_MODEL.md` sections 2, 4, 5 and 7):** token-origin shares by tier 26.9% / 48.8% / 23.2% / 1.1%
   (226,658 / 411,016 / 195,718 / 9,587 of 842,979); spread p50 4.9 / 3.0 / 2.0 / 1.0c; $100 round trip p50 9.9 / 7.2 /
   3.9 / 2.9c (p25 6.3 / 5.2 / 2.9 / 1.9c); adverse selection on filled touch orders at a 1-2 h mark 3.87 / 2.45 / 2.04 /
   0.39c against half-spreads 2.0 / 1.0 / 0.75 / 0.5c; queue fills within 1 h 1.9 / 4.3 / 2.9 / 3.4%; break-even gross for
   the F4 / F5 inputs: taker both legs 3.52c, maker entry + taker exit 2.41c (independent) / 3.18c (conservative), maker
   both legs 1.30c (independent) / 2.84c (conservative), maker entry held to resolution about 0.65c (10k-100k) and about 0
   (>= 100k). Fee policy `conservative` = max(schedule rate, docs rate); the docs rates politics / finance / tech /
   mentions 0.04, sports / economics / culture / weather / other 0.05, crypto 0.07, geopolitics 0; **the served schedule
   on most non-sports rows has been `rate 0` since 10-20T18:31Z (q0717), unverified as a charged fee**, so every cost line
   below is printed twice: at the served rate and at the docs rate.
4. **The CH261 map (q0701)** as 0.1 states it; **the q0717 probe** as 0.1 states it.
5. **Streams the host runs (`COLLECTION_HOST.md`, `NEW_STREAMS` sections 1-3, `CROSS_VENUE_LIVE.md`,
   `LIVE_TRADE_MONITOR.md`):** the pass at :31 every 2 h (snapshot about 249k rows and sidecar, forecast, two sweeps, the
   trade sample of 2,000 markets, the flow screen, E011's score); the monitor (300 s, every taker print >= $1,000 with
   receipt time and a hashed wallet; about 160-270 prints an hour in the pilots); the E009 / E010 poller (120 s, <= 200
   matched Kalshi pairs; sealed to 11-03, then `xv_quotes/`); the four keyless streams (`predictit` 1 min about 10 MB a
   day, `smarkets` 5 min about 26 MB, `espn_odds` 10 min 2-5 MB, `gamma_rules` hourly top-3,000 plus the 6-hourly frame
   about 4 MB); CB15-E election-night books at 1 min (11-02..11-06); the engine's per-capture stores. The queue: lanes
   `cpu` and `net`, one job each; light jobs `mem_mb` < 500. Nothing here proposes a new collector.
6. **Row and sidecar fields** (round 18 fact 7): the touch, `last_trade_price`, `volume24hr`, `liquidity`, `chg_*`,
   `end_date`, `created_at`, `uma_resolution_statuses` (served as `umaResolutionStatuses`, a list; parsed as a string by
   the CB12 readers; **no proposal timestamp is known to be carried**, so any time-since-proposal arm is `unavailable`
   unless the field carries one, pinned before the census), `fee_schedule`, `fees_enabled`, `fee_type`, `clob_rewards`,
   `open_interest`, `accepting_orders`, `order_price_min_tick_size`, the event fields and the comment count; **no question
   text** on the capture rows (the text lives only in `gamma_rules`' frame, 44.7% of eligible non-sports markets).
7. **The venue's display convention (to be re-read and recorded at any pin, rule 15's precedent; not captured):** event
   cards show a rounded percent, with the tails displayed as "<1%" and ">99%"; the trade widget shows the price in cents
   with a 0.001 tick below 0.04 and above 0.96 (`COST_MODEL.md` section 2: tick sizes 0.01 and 0.001 seen).
8. **The record this round must not repeat** (round 18 fact 11 and section 4 below): nothing here is a mover, a band, a
   ladder sum, a twin, a fee panel, a comment count, a halt, a flip, a collapse, a batch innovation, a Kalshi change, a
   wallet, a manipulation route, a trade-sample unit or a monitor print as a unit.

**Counts table (what was counted before each idea was written; the source named; `unprobed` where nothing was).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH262 | eligible non-sports ex-crypto market x capture in the top decile of the pinned champion's `s_2h` = P(up) - P(down), by liquidity tier and fee class | eligible non-sports ex-crypto 18,232-18,349 a capture, so the decile about 1,830; by the cost model's tier shares about 490 / 890 / 425 / 20 (< 1k / 1k-10k / 10k-100k / >= 100k; planning); fee-free share 0.29 (CH251) before the fee step, **unprobed** after it | facts 1, 3; CH251; STATUS |
| CH263 | non-sports ex-crypto market at the first capture whose sidecar shows a UMA proposal (one-shot) | resolutions about 740 a day (derived); proposals seen at a capture **unprobed** (planning 300-700 a day; 6,300-14,700 in 21 days) | fact 2 |
| CH264 | non-sports ex-crypto market at the first capture >= 2 h past `end_date`, open, no proposal, two-sided, mid in [0.05, 0.95] (one-shot) | **unprobed** (CH189 named the population; planning 30-150 a day) | fact 2; CH189 |
| CH265 | eligible market x capture with >= 12 prior champion predictions and realised 2 h labels | every eligible row after 12 slots (about 42-52k a capture); the residual's autocorrelation **unprobed** | facts 1, 5; STATUS |
| CH266 | (map) resolved markets by last-origin mid in 0.1c bins below 3c; (sketch) non-sports ex-crypto market at its first downward crossing of 0.010, placebo 0.015 (one-shot) | 21,516 resolutions at <= 0.05 in 12 days (all categories); the sub-1c share and the crossings a day **unprobed** (planning 50-200 a day non-sports ex-crypto) | fact 2 |
| CH267 | non-sports ex-crypto market at the last capture 2-4 h before `end_date`, two-sided at k - 1 and k, no proposal (one-shot), by rule class | closes about 740 a day (derived); usable share and class split **unprobed** (planning 50% usable, 44.7% with a rule class: about 3,500 classed units in 21 days) | fact 2; `gamma_rules` coverage |
| CH268 | eligible market x capture with >= 12 prior label states | every eligible row after 12 slots; the `unavailable` share per market **unprobed** | fact 5; DESIGN_V1 section 2 |
| CH269 | the one-shot census and the tails map: counts only | a map; counts 0 until run | - |

---

## 1. Map: where money might be, given the costs, the deaths and the three unread places

The cost model fixes the frame (2.9c in the most liquid tier, 3.9c at the 10k-100k median, 7-10c below; makers about
break-even before rebates and rewards; adverse selection above the half-spread in every tier but the largest; fills
driven by whether anyone trades at all); the arithmetic fixes the design (one-shot units for once-per-market states;
spread or hold-to-resolution objects; common states to the engine); the record fixes the odds (two survivors in six LT
families; the fee step took the one LT13 candidate with margin). So this round does not go back to any field of the
capture. It reads the two populations the engine's eligibility drops and rule 19 bars, the one clock every market has
exactly once, and the engine's own history.

1. **The decided side is for sale below par every day, and nobody has measured the discount prospectively.** After a
   UMA proposal the market keeps trading until liveness ends; the proposed side's ask sits under 1.00 by an amount
   (CH01's development envelope: about 3c gross on 0.97; net about 0.6c after a 1.4c entry and a 1% tail) that pays for
   capital, the dispute tail and attention. The engine never sees it (proposed rows are dropped at eligibility); no live
   test may read the resolution that is its payoff (rule 19). It is dense (hundreds a day), one-shot by construction,
   hold-to-resolution (no exit leg), and its tail is measurable to a tenth of a cent in one window. Rule 26 gives it a
   role.
2. **The engine's signal has a gross, and the programme's standing rule asks what it is worth after costs.** Every
   capture writes the champion's P(up) - P(down) for every eligible market before outcomes; the mid 2 h later is on the
   next capture; the cost model has the hurdles by tier. The number "mean gross in the top decile, by tier, against the
   maker and taker rungs" has never been written down prospectively. It is the cheapest registered test in the programme
   (two parquet files a capture), and whichever way it comes out it closes a question the owner asked on 2026-10-21.
3. **Every market closes once, and the maker's adverse selection has a clock there.** For a market resolved by a
   scheduled publication the information arrives at a known minute; for a barrier market that was never hit the close is
   a formality; for a consensus-sourced market the deadline hour is the news. The spread's change into the close, read
   once per market and contrasted across those classes, is a verdict-shaped test with about 15,000 candidate units in a
   window and a design effect near one (rule 24).
4. **Below "<1%" there is no retail buyer, and the longshot bias has a lower edge.** The venue's cards round the price to
   a percent; below 1c every market reads the same. Attention cannot form on a price nobody sees, so the sub-display zone
   is a bot-only book and the overpricing of tails, if it exists, lives in the *visible* tail (1.0-1.9c) and stops at the
   display line. The engine cannot score it (mid < 0.02 is ineligible); the label store already holds 21,516 tail
   resolutions in twelve days to map it.
5. **The engine already knows which markets it keeps getting wrong, and in which direction.** Its predictions are
   write-once; its residual on market A at origin k - 1 is known at k (the mid at k is the label). A per-market residual
   history is the engine's own measure of *idiosyncratic* information flow (the champion's features are common: momentum,
   market state, category), and slow diffusion of idiosyncratic news is the oldest under-reaction story there is. The
   same store says which markets' labels keep coming back `unavailable` (the quote vanished), which is a quoter-reliability
   state the public feed should not ignore.

| Family | What the host already dates that nobody has read | Money route |
|---|---|---|
| A. The engine at the touch (CH262) | the champion's `s_2h` per eligible row at k; the mid at k + 1; the recorded touch and tier at k | none claimed: a measurement of gross against the cost model's rungs by tier and fee class; the flat decile as the maker's selection, reported |
| B. The blind spots: the proposal window (CH263), the overdue mid (CH264), the tails (CH266) | the first capture with a proposal; the first capture past `end_date` with an interior mid; the first crossing of 0.010 | taker, hold to resolution: buy the proposed side at its recorded ask; buy the overdue favourite at its mid; maker: the visible-tail ask (1.0-1.9c) held to resolution (gross; the zone's floor) |
| C. The one-shot lane: the close (CH267) and its census (CH269) | the last capture 2-4 h before `end_date`, by rule class | maker: widen or withdraw into the close of scheduled-publication markets (gross); taker: exit at T - 4 h, not T - 2 h (reported) |
| D. The engine's own history (CH265 `resid`, CH268 `fragile`) | the champion's per-market residuals at k - 1..k - 12; the per-market run of `unavailable` labels | none directly (forecast quality; CH262 is the yardstick); hygiene for the public feed |

**Data labels.** `A` = on the host now (captures, sidecar, two sweeps, trade samples, the monitor, the poller's quotes,
the engine's `quotes/`, `features/`, `predictions/`, label logs and states, the four keyless streams, `reward_params`,
se20's klines). `A~` = on the host but a join or reader has to be written and counted first (the proposal reader, the
overdue reader, the close-by-class reader, the tails map, the residual history, the label-availability history, the
decile-by-tier reader). `P` = a fetch is needed (none here). **Sealed and not usable by anything here:** LT2's, LT3's,
LT4's (E022's) stores, LT9's, LT10's, LT11's, LT12's and LT13's once registered, CB16's and CB17's stores, CB8-H's holders,
E009 / E010's `cross_venue_live/` to 2026-11-03, E011's `surprise_live/` to 11-10, E025's and E026's stores and the E026
frozen modules. J4-R `[2026-10-16, 2026-10-21)` and CB13-T's holdout `[2026-10-21, 2026-10-26)` are refused for every
maker mark-out object; nothing here is one.

**Windows and registration this round proposes.** Three lanes, registered separately, none reading another's objects.
- **The economic lane (LT14: CH262).** One Holm family, **k <= 2** (the 10k-100k tier's primary rung and the >= 100k
  tier's, if its census count holds); reads only the engine's `predictions/` (pinned specs), `quotes/`, `features/` and
  the sidecar's tier and fee fields; the census reads the engine's files of LT12's census span `[2026-11-07, 11-17)`
  **for the decile's tier split only** (no mid after an origin), labelled `informed (LT12 census)`. Because its objects
  are disjoint from LT11's and LT12's (their objects are same-event spread sums, twins and sibling shocks; CH262's is the
  engine's own prediction against the row's own next mid), the design asks the challenger whether it may run **in
  parallel with LT12 (window 2026-12-10..12-31, analysis on or after 2027-01-01T12:00Z)**; if refused, after LT13's fast
  lane (**2027-02-12..03-05**). Token: none (no feature is built); an attribution limit `attrlimit_lt14` on any display of
  the champion's *gross by tier* before the analysis, so that the public feed does not show the test's number.
- **The measurement lane (M1: CH263; M2: CH264).** Two registered measurements under rule 26 (k = 0 each), reading the
  sidecar's proposal and end fields, `quotes/` and the first sweep's touch sizes (capacity only), with the resolutions read
  from the engine's resolution logs after the window; window **2026-11-24..12-14** (any span is free of conflict: no test
  owns the proposal window or the overdue population), estimands fixed at the freeze, read-out **>= 14 days after the
  window's end** (the last resolutions). The role itself is the first thing the reviewer rules on.
- **The one-shot lane (LT15 candidate: CH267).** After CH269's census, one Holm family k <= 1 on the close by rule class;
  the fast lane needs a window free of LT11 / LT12 / LT9 / LT13 objects, which it is (the close of standalone and
  small-ladder markets; two-member events held out to LT12's date); proposed **2027-02-12..03-05** beside LT14, or earlier
  if the challenger accepts parallel running on disjoint objects. Token `close` (the rule-class x hours-to-end
  interaction) requested at the freeze; the `tte` family's levels stay as built.

## 2. Hypotheses

### A. The engine at the touch (parents: NORTH_STAR, DESIGN_V1 sections 2-4 and 17, `COST_MODEL.md` sections 5-6, CH77, CH156, CH172, CH186, CH196, CH43, CH259; literature: Grossman and Stiglitz 1980 on the equilibrium degree of mispricing, Roll 1984 on the bid-ask bounce as a spurious component of measured moves, Hasbrouck 1991 on the information content of trades against quote re-centring)

**CH262. The engine at the touch: the champion's top-decile 2 h signal carries a gross that is measurable to a few
hundredths of a cent by tier, and the programme's own cost rungs say what it is worth. The hypothesis is that in the
10k-100k tier the top decile's mean signed gross exceeds the most optimistic maker rung (1.30c, both legs passive, fills
independent of the signal), and that in the >= 100k tier it exceeds its half-spread (0.5c); the counter-hypothesis the
design is built to show is that the gross scales with the spread at the origin (quote re-centring of a stale side, Roll's
bounce), so that it vanishes in tight books and never clears a taker rung anywhere.**
- Mechanism and why it is non-obvious. A momentum-plus-state forecast on a 2 h Gamma mid can be right for two reasons:
  information diffusing (the move continues because the news is not yet in the quote) or the quote's own mechanics (the
  mid at k was a stale side's re-centre and the mid at k + 1 completes it). The first has a gross independent of the
  spread; the second has a gross proportional to it. The owner's standing rule asks for the signal to be as accurate as
  possible *and* for every edge claim to carry an economic check; the engine measures log-loss and nothing in cents
  (DESIGN_V1: "nothing here covers fees or spread"). The number is cheap and no document holds it. Who pays if the gross
  is informational: the maker whose quote the taker crosses (gross; the cost model's AS is exactly this quantity from the
  other side). Why the crowd misses it: the engine's own vocabulary ("signal strength") is deliberately not in cents.
- Parent and what is new. The champion / challenger design (DESIGN_V1), `COST_MODEL.md` section 5 (the F4 / F5
  reassessment, development, on historical cells), CH77 (where the fills are), CH156 and CH172 (quoted against traded
  moves), CH186 (calibration by provenance), CH196 (the last-print anchor), CH43 and CH259 (the engine's uncertainty as a
  maker filter). New: the **registered, prospective** measurement of the engine's gross by tier against the declared
  rungs, the **spread-scaling** test as the built-in alternative, the **flat decile** as the maker's selection object, and
  the engine's own write-once files as the only input (rule 27).
- Data join and decision clock (`A~`, L 5: `predictions/<capture>/se0_champion_lr_mm.parquet` and the pinned
  `se1_lgbm_mm` version, `quotes/<capture>.parquet` for the mid and touch at k and k + 1, `features/` for tier inputs,
  the sidecar's `fee_schedule` and `fee_type` for the cost line). Unit: eligible non-sports ex-crypto market x capture
  with a visible prediction at k from both pinned specs and a two-sided quote at k + 1 (a one-sided or missing k + 1 is
  `unavailable`, counted). State: `s_2h = P(up) - P(down)` at k; decile membership by the within-capture distribution of
  `|s_2h|` (the top decile; the middle deciles 4-6 as the within-market-day comparison). Decision time: the prediction
  file's own write time (before the capture's forecast step completes; the engine stamps it). Tier: the cost model's
  bins on the row's `liquidity` at k. Controls for the secondary: `spread_k`, `log1p liquidity`, `z log rv24`, hours to
  end, category.
- Target and horizon. Primary (per tier, a level against a declared constant): `g = sign(s_2h) x (mid_{k+1} - mid_k)` in
  cents, the mean over the top decile's units, cluster-robust on event (CR1; two-way event x UTC day; p the largest),
  one-sided against **H = 1.30c in the 10k-100k tier** (the optimistic maker rung; the 0.65c hold-to-resolution rung and
  the 2.41c and 3.9c rungs reported beside it) and **H = 0.5c in the >= 100k tier** (its half-spread; the 1.9c p25 taker
  round trip reported). Secondary (the Freedman-Lane-gated within-market term, market x UTC-day strata): the top decile's
  `g` against the middle deciles' within the same market-day. M1 (the alternative): within the top decile, the slope of
  `g` on `spread_k` with intercept, by tier; the spread-scaling world predicts intercept about 0 and slope about 0.3-0.5.
  M2 (the maker's selection): the top decile of `P(flat)`: the share of units with `|mid_{k+1} - mid_k| <= spread_k / 2`
  against the bottom decile's, by tier (a maker who quotes both sides at the touch is not picked off when the move is
  inside the half-spread), reported. M3: by fee class at the origin (served schedule and docs rate both printed).
- Paper rule and economic check (rule 11 read loosely, since this entry *is* the economic check). No route is claimed; the
  verdict is the rung cleared. The cost line per unit is the cost model's `cost_check` at the recorded touch and tier,
  `cost-model-v1`, fee policy `conservative` and, beside it, the served schedule (0 on most non-sports rows since 10-20).
- Population arithmetic. Top decile about 1,830 a capture; by tier about 490 / 890 / 425 / 20 (planning from the cost
  model's token-origin shares; the census counts). 10k-100k: 425 x 252 = 107k units; the LT11 formula at a planning
  decile tenure of 50 captures per market gives DE 1.98, the convention 31 beside; `n_eff` 43k (DE 2) or 2,760 (DE 31).
  >= 100k: 20 x 252 = 5,040 units in perhaps 60-100 markets; DE 2 gives `n_eff` 2,016; DE 31 gives 130.
- Permutation and cluster structure. The primary is a level, so its inference is the cluster-robust CI (the permutation
  gate does not apply to a level against a constant); the secondary carries the Freedman-Lane within-market-day gate.
  Binding scenarios: LT5 1-2, L10, **S44: a stale-side world** (mids re-centre by half the spread with no information; the
  M1 intercept must be about 0 and the primary must then fail in the >= 100k tier where spreads are 1c), **S45: a
  label-timing world** (the k + 1 mid read from a capture that received the row *later* than 2 h after k: the receipt
  offset in `quotes/` bounds the horizon to 2 h +- 15 min, else `unavailable`), **S46: a spec-change world** (a refit inside
  the window shifts the decile's composition: the specs are pinned by version, refits are part of the object as deployed,
  and the per-day decile composition is printed).
- Planning MDE (a level against a constant; SD by tier). 10k-100k (SD 1.3c): DE 2 **0.03c**, DE 31 **0.13c**; quarter
  counts 0.06c / 0.26c. >= 100k (SD 1.9c): DE 2 **0.22c**, DE 31 **0.87c** (over its 0.5c rung at the convention, under it
  at the formula; the census's computed DE decides and the >= 100k primary enters only if its MDE at the computed DE is
  under 0.5c; else reported). F (the twin is the same decile's `g` over `(k + 2, k + 3]`, which should be about 0): F-MDE
  0.05c / 0.35c (10k-100k). **Kill lines:** the 10k-100k tier needs >= 100 top-decile units a capture (any DE); the
  >= 100k tier >= 10 a capture and >= 40 distinct markets over the window.
- Confounders and how each is held. The engine's refits (pinned versions; the deployed object); the display pool (spread
  <= 2c) is *not* the population (the whole eligible set is; the pool reported as an arm); survivorship at k + 1 (the
  `unavailable` share by decile printed; a decile whose `unavailable` share exceeds the others' by 10 points fails the
  census); the fee step (both cost lines); the fine-clock tests (LT10 reads Kalshi pairs; none of its objects enter);
  the `movetype` and `flow` families are embargoed to 11-22 / 11-16 and are not read (the champion is `se0`, not
  embargoed; se1 is not embargoed).
- Most likely boring explanation. The gross is 0.3-0.8c in the 10k-100k tier, scales with the spread (M1 slope about 0.4,
  intercept about 0), and clears the 0.65c hold-to-resolution rung at best; the >= 100k tier's gross is under its
  half-spread. That outcome is itself the programme's answer to "is the champion a route": no, and by how much.
- Cheapest census (counts only; the engine's files of `[11-07, 11-17)`; no mid after an origin read). Top-decile units a
  capture by tier and fee class with min / median / mean per capture (venue clock <= 50%); distinct markets and events
  per tier; the decile's tenure distribution (the DE input); the `unavailable` share at k + 1 by decile (from `quotes/`
  status codes, which is not a target); `VIF_w` of decile membership against `spread_k`, `log1p liquidity`, `z log rv24`;
  the rung constants recomputed from the census span's recorded touches with `cost-model-v1`; MDE and F-MDE printed at
  the computed DE.
- Challenger feature: **none** (no feature is built; the engine's own number). The attribution limit `attrlimit_lt14`
  (no display of gross-by-tier before the analysis) is the only request.
- Sports arm: the same reader on sports rows, uncounted (the owner's parameter; the sports rungs from the cost model's
  sports round trip 6.2c, fees 2.1c, before the fee step).
- Scores: N 2, EV 4, L 5. Priors: **P(census) 0.85; P(replicates | the 10k-100k primary clears 1.30c) 0.4**; P(the primary
  clears 1.30c at all) about 0.10; P(it clears 0.65c) about 0.35. Parents: the engine's design, `COST_MODEL.md` 5, CH77,
  CH156, CH172, CH186, CH196, CH43, CH259. New: the registered prospective measurement of the engine's gross by tier, the
  spread-scaling alternative, the flat decile as the maker's object, the engine's files as the only input.

### B. The blind spots (parents CH01, CH02, CH03, CH04, CH47, CH62, CH65, CH85, CH134, CH175, CH189, CH207, CH221, CH226, CH242 for the proposal window and the overdue mid; CH15, CH17, CH60, CH86, CH164, CH232, CH260 for the tails; literature: Thaler and Ziemba 1988 and Snowberg and Wolfers 2010 on the favourite-longshot bias, Barber and Odean 2008 on attention and the visibility of a price, Duffie 2010 on slow-moving capital, Garleanu and Pedersen 2011 on margin-based pricing)

**CH263. The carry, registered: the decided side's discount during the UMA proposal window is a dense, one-shot,
hold-to-resolution route, and its three components (capital, the dispute tail, attention) can be separated by
measurement in one window. The claim is that the mean carry `c = 1 - ask(proposed side)` at the first capture after a
proposal exceeds the realised reversal rate `r` (proposals overturned or split) plus the recorded entry cost by more
than 0.3c a share on non-sports ex-crypto markets, that `c` falls with liquidity tier (the attention component: nobody
bothers for 2c in a small book) and does not fall with hours to settlement (the capital component is too small to see at
2 h), and that the tail `r` is under 0.5%.**
- Mechanism and why it is non-obvious. After a proposal the outcome is public; the market trades until liveness ends
  (about 2 h) and the venue settles after. Sellers at 0.98-0.99 are holders recycling capital (CH68) or impatient; buyers
  are the few who watch the proposal feed. The discount is bounded below by the dispute tail (a wrong or 50-50 resolution:
  CH03, CH47, CH242's 0.004% non-sports splits) and above by attention. CH01 priced it in development (about 3c gross on
  0.97, net about 0.6c after a 1.4c entry and a 1% tail) and no round since has measured it, because the engine drops the
  row at eligibility and rule 19 bars the resolution from a live primary. Who pays: the seller's time preference, which
  is not a mispricing of the outcome but of the wait; the route's persistence is Duffie's slow capital: the buyer needs
  idle collateral and a feed. Why the crowd misses it: the display shows ">99%" and the card is already in the "ended"
  list; the money is the kind nobody tweets.
- Parent and what is new. CH01 (the carry), CH02 (the proposal-window carry), CH226 (the resolver's clock), CH134 (the
  Kalshi-settled label), CH47 (the dispute lottery, the same object from the loser's side), CH221 (the siblings), CH85
  and CH207 (proposer whitelist, bond), CH242 (the third price). New: the **one-shot unit** at the first capture with a
  proposal (rule 24), the **registered measurement** role (rule 26) with estimands and CIs declared, the **decomposition**
  (tier for attention, hours-to-settlement for capital, the label store for the tail), the **capacity line** (the
  recorded ask size at the touch, dollars available per unit), and both cost lines (served and docs fee).
- Data join and decision clock (`A~`, L 4: the sidecar's `uma_resolution_statuses` at k and k - 1, the rows' touch at k,
  sweep 1's `ask_size_1` at k for capacity, the engine's resolution logs after the window). Unit: non-sports ex-crypto
  market whose sidecar shows a proposal state at k and none at k - 1 (the first capture after the proposal; a market
  first seen already proposed with no k - 1 row is `unavailable`, counted), two-sided at k, the proposed side read from
  the status (if the field does not name the side, the side at >= 0.90 at k is the proposed side and the reading is
  pinned; a market with neither side >= 0.90 is a counted class, `contested`). Decision time: the row's `received_utc`
  at k. Strata (for the descriptive splits only): tier x category x UTC day; cluster = event (a ladder proposed at once
  is one cluster; cap 10, larger a reported arm).
- Estimands (declared; no verdict). (1) `c` = `1 - ask_k` of the proposed side, mean and quantiles, by tier, category,
  ladder position (standalone / winner / loser member), fee class at the origin and, where the field carries a proposal
  time, hours to liveness end (else `unavailable`). (2) `r` = the share of units whose final resolution (read from the
  resolution logs after the window; a `split_50_50` counts as a loss of 0.5; `not_found` after 30 days a counted class)
  differs from the proposed side; Clopper-Pearson 95% CI. (3) `cost` = the recorded half-spread at k on the proposed side
  (the zone's tick is 0.001 above 0.96: rule 25's floor logic) plus the fee at `ask_k` under the served schedule and under
  the docs rate, plus a declared capital line (hours to settlement x 5% a year: about 0.001c an hour, so visible only if
  settlement lags by days; the time from k to the resolution log's receipt is the measured wait). (4) `net = c - r x
  (1 + c) - cost`, with a CI from the bootstrap over events. (5) Capacity: `ask_size_1 x ask_k` in dollars at k, median
  and sum per day. (6) The maker's version, gross only: `1 - bid_k` (the quoted carry a resting bid at the touch would
  collect; no fill is measured; sampled trades are not read).
- Paper rule and economic check (rule 11: hold to resolution). Taker: buy the proposed side at `ask_k`, hold to
  settlement; the net per share is estimand (4); the capital turn is the measured wait. Maker: rest a bid one tick under
  `ask_k` (reported gross; no fill claim). Nothing here is a verdict; the ledger line is "measured: c, r, cost, net,
  capacity, wait" with CIs.
- Population arithmetic. Resolutions about 740 a day (derived); proposals seen at a capture **unprobed**; with a 2 h
  liveness and a 2 h cadence nearly every proposal straddles one capture, so planning 300-700 a day seen (the managed
  oracle's path without a visible proposal state, CH85, is the unknown), 6,300-14,700 one-shot units in 21 days; events
  about a third of that. Precision: `SE(c)` about 1c / sqrt(5,000) = 0.014c; the Clopper-Pearson upper bound on `r` at 0
  observed reversals in 5,000 units is about 0.06%, so the tail term is bounded to 0.06c; `net` is known to about +-0.1c.
  **No MDE applies (a measurement); the kill is precision:** fewer than 2,000 units makes the tail bound 0.15c and the
  measurement is reported as coarse.
- Permutation and cluster structure. None (k = 0). The bootstrap is over events; the descriptive splits carry CR1 CIs.
  Declared worlds for the reader's size check (rule 26 asks for them even without a verdict): **S47: a proposal flag that
  lags the on-chain proposal by one capture** (the first capture after the flag is then one slot later than the first
  after the proposal; `c` is smaller; the reading is disclosed and the field's lag is a census line from the ledger's
  CH221 counts), **S48: a side mis-read** (the proposed side is the side at < 0.90: a `contested` class, never folded).
- Confounders and how each is held. Survivorship (markets that resolve without a visible proposal state are missing:
  the seen share against the label store's resolutions is printed); disputes (a disputed state at k is a separate class,
  CH03, reported); the sports and crypto arms (parameters; crypto's dailies resolve by Chainlink without a UMA proposal,
  CH76, so the population is non-crypto by construction); the fee step (two cost lines); E026's modules (wallets; not
  read); nothing of LT11 / LT12 (their objects are pre-proposal spreads; the engine's eligibility already separates the
  populations).
- Most likely boring explanation. `c` is 0.5-1.0c at the 0.001 tick, the half-spread in the zone is 0.2-0.4c and the
  reversal tail 0.2-0.5%, so `net` is 0 to +0.3c with a one-day capital turn: real but not worth a feed; or the capacity
  at the touch is tens of dollars in most units (the route exists for a hobbyist, not for capital).
- Cheapest census (counts only; the last 8 days of sidecars on the host plus `quotes/`; no resolution read). Proposals
  seen a day by category, tier and ladder position; the seen share against the resolution logs' count for the same days
  (a lagged read, counts only); the share with a readable side; the zone's recorded half-spread at k (the cost line's
  input); `ask_size_1` coverage from sweep 1; the per-day distribution (venue clock); fewer than 100 a day kills the
  window length as planned (extend to 42 days, declared).
- Challenger feature: **none** (the population is ineligible by DESIGN_V1 section 2; a `res_7d` extension to proposed
  rows is the builder's call and is not asked for here).
- Sports arm: sports game markets resolve by the sports oracle without a UMA proposal state on most rows (CH226's
  reading); uncounted.
- Scores: N 3, EV 4, L 4. Priors: **P(census) 0.7; P(net > 0.3c replicates) 0.5**. Parents: CH01, CH02, CH226, CH134, CH47,
  CH221, CH85, CH207, CH242. New: the one-shot unit, the measurement role, the decomposition by tier and wait, the capacity
  line, both cost lines.

**CH264. The overdue mid: a market past its `end_date`, open, unproposed and still quoted inside (0.05, 0.95) is either
unresolved by inattention (nobody has posted the bond on a small market) or by ambiguity (holders doubt the rule), and the
two leave different fingerprints: the inattention premium shrinks with open interest and vanishes at a proposal; the
ambiguity premium is flat in open interest, larger in consensus-sourced rules, and pays out as a split or a `not_found`
more often. The claim is that the favoured side's realised win rate `q` exceeds its mid by more than the entry cost in
the top open-interest tercile and not in the bottom one.**
- Mechanism and why it is non-obvious. The UMA proposer posts a bond (CH207; whitelisted proposers since the managed
  oracle, CH85) and earns a small reward; for a market with a few hundred dollars of open interest nobody hurries, so a
  decided question can sit at 0.80 for a day: CH189 named the population, CH62 the calendar-decided NO carry, CH175 the
  last-mid proxy. The split by open interest separates the two stories without reading any text; the rule class from
  `gamma_rules` (44.7% coverage; `unavailable` elsewhere) is the second cut. Who pays: the holder who sells the decided
  side at 0.80 because the deadline passed and nothing happened on his screen. Persistence: the bond and the attention.
- Parent and what is new. CH189 (overdue by the clock), CH62, CH175, CH226, CH65 and CH207 (dispute and bond), CH85
  (the proposer set), CH242 (the third price). New: the one-shot unit at the first overdue capture, the measurement role,
  the **open-interest x rule-class decomposition** as the identification of ambiguity against inattention, and the
  wait-to-proposal hazard as an estimand.
- Data join and decision clock (`A~`, L 3: the rows' `end_date`, touch and mid at k, the sidecar's proposal state and
  `open_interest`, `gamma_rules`' class where present, the resolution logs after the window). Unit: non-sports ex-crypto
  market at the first capture at least 2 h after `end_date` with `accepting_orders` true, no proposal state, two-sided,
  mid in [0.05, 0.95] (a market whose `end_date` moved inside the window is `unavailable`, counted: CH187). Decision
  time: the row's receipt at k. Strata for the splits: open-interest tercile (census-fixed) x rule class x category.
- Estimands. (1) `q - p_fav` by open-interest tercile and rule class, with event-bootstrap CIs; (2) the hazard of a
  proposal appearing per slot after k, by tercile (the inattention story predicts a steep hazard in the top tercile);
  (3) the share resolving as `split_50_50`, `not_found` or the unfavoured side, by class; (4) `net = (q - p_fav) - cost`
  with the recorded half-spread and both fee lines; (5) capacity at the touch.
- Paper rule and economic check. Taker, hold to resolution: buy the favoured side at its ask in the top open-interest
  tercile; the net is estimand (4). Nothing is a verdict.
- Population arithmetic. **Unprobed**; planning 30-150 a day (CH189's population on a capture was the venue's listing
  tail; the overdue-with-interior-mid subset is smaller), 600-3,000 one-shot units in 21 days. Precision at `n` = 1,000
  and `q` about 0.85: `SE(q)` 0.011, so the premium is known to about +-2.2 points per tercile at 333 units each (+-4
  points). Kill: fewer than 500 units in the window (extend to 42 days, declared), or a `not_found` + split share over
  30% (the population is the venue's backlog, not a route; reported as such).
- Permutation and cluster structure. None (k = 0); event bootstrap; worlds **S49: an `end_date` that is not the
  resolution clock** (markets whose rules resolve on a later publication: the rule class names them where read; the
  unclassed share is the disclosure) and **S50: a stale `accepting_orders`** (the flag true on a market the venue has
  closed: the next capture's status decides; `unavailable` if closed at k + 1).
- Confounders. The rule-class coverage (44.7%) selects larger markets (the frame is by volume); the fee step; the
  crypto dailies (excluded; CH76); sports (parameter).
- Most likely boring explanation. The overdue interior-mid population is a few dozen a day, half of them ambiguous rules
  that resolve `not_found`; the premium in the top tercile is 2-5 points with a +-4 point CI.
- Cheapest census. The overdue count a day by tercile and class from the last 8 days of sidecars; the share with a
  classed rule; the share whose `end_date` moved; the per-day distribution.
- Challenger feature: none (the rows are eligible only until `end_date`; after it the engine's `end after the origin`
  rule drops them).
- Sports arm: uncounted (game markets resolve within hours of the end by the sports oracle).
- Scores: N 3, EV 2, L 3. Priors: **P(census) 0.45; P(net > cost in the top tercile replicates) 0.35.** Parents: CH189,
  CH62, CH175, CH226, CH65, CH207, CH85. New: the one-shot measurement, the OI x class decomposition, the hazard estimand.

**CH266. Below the display: the venue's cards show "<1%" for every price under one cent, so attention cannot form on a
sub-cent price and the sub-display zone is a bot-only book. The claim, as a map first: the longshot overpricing (realised
win rate under the price) is concentrated in the visible tail (1.0-1.9c) and has a kink at the display line, with the
sub-cent bins closer to fair. As a live sketch behind the map: the first downward crossing of 0.010 is followed by a
larger widening of the spread in ticks than the crossing of 0.015 (the retail bid vanishes below the display), which is
the dated event a maker's ask above the line is sold into.**
- Mechanism and why it is non-obvious. Every longshot entry so far (CH17, CH60, CH164, CH232, CH260) read the price grid
  (0.05, 0.10) or the tick boundary (0.04, CH15 / CH86); none read the *display* boundary, which is where a retail buyer
  stops seeing a number. Barber and Odean's attention buying needs a visible price; a bot does not. The tails are a
  sixth of all resolutions (21,516 of 132,539 at <= 0.05 in twelve days) and the engine never scores them (mid < 0.02 is
  ineligible), so the kink, if it exists, is unmeasured by construction. Who pays: the retail buyer of the 1.0-1.9c YES
  (visible as "1%"); who collects: the maker's resting ask at 1.0-1.9c held to resolution (the zone's fee 0.04c at the
  docs rate, 0 served; the half-spread one or two ticks). Why the crowd misses it: it is below the number the site prints.
- Parent and what is new. CH17 (longshot ask-selling), CH60 (the tail classifier), CH164 (class-conditioned longshots),
  CH232 (the cheap side's cliff), CH15 and CH86 (the tick boundary at 0.04 / 0.96, which this entry excludes by
  construction: 0.010 and 0.015 are both inside the 0.001 regime), CH260 (the fee's incidence). New: the **display
  threshold** as the mechanism, the **kink** as the map's object, **rule 25's zone floor**, and the **0.010 crossing with
  the 0.015 placebo crossing** as a one-shot dated event (rules 15 and 24).
- Data join and decision clock. Map (`A`, L 5): the engine's label store (every resolved market's last-origin mid is in
  the CH242 census's own frame; the map re-bins it at 0.1c from 0.2c to 3c and the mirror 97c-99.8c, by category group,
  counts and win rates with Wilson CIs; k = 0; a counts-only reading of a store that already exists, no new resolution
  read). Sketch (`A~`, L 3): the rows' mid at k - 1 and k on the 0.001 tick; unit: non-sports ex-crypto market at its
  first capture with `mid_{k-1} >= 0.010 > mid_k` (the display crossing) or `mid_{k-1} >= 0.015 > mid_k` (the placebo
  crossing), two-sided at k - 1, k and k + 1, no proposal (a market crossing both inside one slot is the display class);
  decision time the row's receipt at k; the display convention re-read on the venue's page at the pin and recorded (rule
  15), the predicted sign fixed from that reading before the census.
- Target and horizon (sketch). Primary: `dt = spread_{k+1} - spread_k` in ticks (0.001), the between-market contrast of
  the display class against the placebo class inside census-fixed strata (category x tier x the crossing's UTC day),
  cluster = event, DE at the formula; one-sided (display > placebo). Twin: the same contrast at the markets' crossing of
  0.020 the previous day where it exists (declared, `r_w` planning 0.2). M1: the bid's share of the widening (the
  mechanism predicts the bid retreats). M2: the mid at k + 3 (reported; `informed (momentum)` by the champion's visible
  `tl_cheap_side` levels, disclosed).
- Paper rule and economic check (rule 11: maker, hold to resolution). Rest an ask at 1.0-1.9c on markets the map shows
  overpriced in that bin, hold to resolution; gross = the bin's (price - win rate); cost = the zone's recorded round
  trip under rule 25 (planning 0.1-0.2c half-spread plus 0.04c / 0 fee). The map's bins decide whether a bin's gross
  exceeds its zone floor; no fill is claimed.
- Population arithmetic. Map: non-sports ex-crypto tail resolutions **unprobed** (planning 10-15% of the 21,516: 2,000-3,000
  in twelve days, 600-1,000 in [0.5c, 2c)); at 600 units and a 1% base rate the Wilson CI is about +-0.8 points, so the
  map detects a kink of 1.5 points or more. Sketch: crossings of 0.010 a day **unprobed** (planning 50-200 non-sports
  ex-crypto), 1,000-4,000 one-shot units a window, the placebo of the same order.
- Permutation and cluster structure (sketch). Rule 24's between-market permutation in census-fixed strata; CR1 on event;
  worlds **S51: a mechanical tick world** (both crossings sit on the same tick, so any difference is the price level; the
  strata hold the level within 0.5c), **S52: a resolution-approach world** (markets cross 0.010 because they are about to
  resolve NO; hours to end is a control and a market with a proposal at k + 1 is `unavailable`).
- Planning MDE (sketch; SD 3 ticks = 0.3c, unprobed). `n1 = n2 = 1,000`, DE 1.2: `3.47 x 0.3c x sqrt(2 / 800) x sqrt(1.2) x
  1.5 x sqrt(1.3)` = **0.10c (one tick)**, equal to the zone floor's analogue; at 4,000 / 4,000 **0.05c**; a quarter of the
  low count 0.19c (fails). F-MDE 0.15c / 0.08c. **Kill line (sketch): about 1,000 display crossings in the window.**
- Confounders. The display convention is the venue's UI, not captured (recorded at the pin; a change inside the window
  is a deviation); the tails are sports-heavy (parameter); `bandside` (LT11) owns 0.10 / 0.90 on the rewarded panel and
  CH86 the 0.04 boundary, neither touched; the `tilt` family's `tl_cheap_side` and `tl_collat` levels are visible (a
  development look at the level, disclosed; no crossing column exists).
- Most likely boring explanation. The win rate is monotone in price through 1c with no kink (the bias is risk love or
  misperception, not attention); or the sub-cent bins hold too few non-sports resolutions to say.
- Cheapest census. The map (one reader over the label store's frame; < 300 MB; `net` lane; k = 0); then the crossing
  counts from `quotes/` (45 days on the host) by category and tier; the zone's recorded half-spread.
- Challenger feature: **none inside eligibility** (the zone is ineligible); the map's result is a DESIGN_V1 section 2 note
  for the builder (whether `res_7d` eligibility should carry a zone flag and extend to [0.005, 0.995]); no column is
  asked for.
- Sports arm: the map prints sports bins beside non-sports; the sketch is non-sports by construction (parameter).
- Scores: N 4, EV 2, L 5 (map) / 3 (sketch). Priors: **P(map shows a kink >= 1.5 points) 0.3; P(the sketch passes its
  census) 0.4; P(replicates) 0.3.** Parents: CH17, CH60, CH164, CH232, CH15, CH86, CH260. New: the display threshold, the
  kink, the zone floor, the paired crossing design.

### C. The one-shot lane (parents CH33, CH40, CH46, CH105, CH187, CH198, CH239, CH28, CH199, CH226; literature: Kyle 1985 on the informed trader's timing against a scheduled resolution, Admati and Pfleiderer 1988 on intraday patterns from scheduled information, Easley and O'Hara 1992 on the no-trade interval before an announcement, Jiang, Likitapiwat and McInish 2012 on spreads around scheduled releases)

**CH267. The close: every market has one, and the maker's adverse selection has a clock there that depends on the rule's
class. In a market resolved by a scheduled publication (a statistic at a known minute, a scheduled vote, a listed
release) the information arrives at the close, so the spread widens into it; in a barrier market the close is a
formality (the barrier was hit long before or never) and the spread does not move; in a consensus-sourced market the
deadline hour is itself the news and the spread widens less than in the scheduled class. The claim, as a one-shot test:
the spread's change from the capture at T - 4 h to the capture at T - 2 h is larger in the scheduled-publication class
than in the barrier class, with the same contrast at T - 26 h to T - 24 h near zero.**
- Mechanism and why it is non-obvious. Admati-Pfleiderer and Easley-O'Hara: makers widen when the informed are about to
  learn something the makers cannot pre-empt; on a prediction market the only scheduled such moment that *every* market
  has is its own resolution. CH33 read the spread cycle around scheduled *events* (FOMC), CH40 the late-life adverse
  selection schedule, CH46 the pre-close dump, CH105 the deadline hour; each was a level or a rare event on a panel. The
  close is once per market, dense (about 740 a day), and the rule class from `gamma_rules` (CH239's parser; CH28's
  scheduled-source class; CH199's source class, killed at census as an *engine* family for coverage, not as a contrast)
  gives the contrast its identification. Who pays: the taker who exits at T - 2 h instead of T - 4 h in a scheduled
  market (the widening); who collects: the maker who withdraws into the close of scheduled markets and keeps quoting
  barrier markets to their last slot (gross; the AS avoided). Why the crowd misses it: the close is read as the end of
  the market, not as the market's one scheduled event.
- Parent and what is new. CH33, CH40, CH46, CH105 (the clock), CH187 (end-date edits: the exclusion), CH198 (calendar
  theta: the barrier class's level), CH239 and CH28 (the classes), CH199 (the source class). New: the **one-shot unit at
  the close for every market** (rule 24), the **rule-class contrast** as the identification, the **T - 26 h twin** on the
  same market, and the end-cohort stratum.
- Data join and decision clock (`A~`, L 3: the rows' `end_date`, spread at the two captures before it, the sidecar's
  proposal state, `gamma_rules`' class fields at the market's last frame before T - 4 h). Unit: non-sports ex-crypto
  market with `end_date` inside the window, two-sided at the last capture `k` with `end_date - t_k` in [2 h, 4 h) and at
  `k - 1`, no proposal at either (a proposal before the close is a counted class, `decided_early`, reported: it is the
  barrier class's natural exit), `end_date` unchanged since T - 48 h (else `unavailable`, CH187), rule class read from
  the stream's last row before T - 4 h (unclassed = `unavailable`, counted; the uncovered share is the first disclosure).
  Decision time: the row's receipt at k - 1 for the T - 26 h twin and at k for the primary's state (the class is fixed
  days before). Classes: scheduled publication (a statistic, vote, release or price at a named time), barrier ("by",
  "before", "reach", "announce" without a named publication time), consensus (credible reporting), other.
- Target and horizon. Primary: `ds = spread_k - spread_{k-1}` (SD 2c; floor 1.0c), the between-market class contrast
  scheduled minus barrier inside census-fixed strata (category x tier x the close's UTC day), cluster = event (ladders
  close together; cap 10; the formula's DE at the member count), one-sided > 0. Twin (F): the same contrast on `ds` over
  (T - 26 h, T - 24 h] (planning `r_w` 0.2), a verdict condition where its F-MDE is under the floor. M1: the consensus
  class against the barrier class (reported, sign declared smaller than the scheduled contrast). M2: the mid's change
  into the close by class (reported; `informed (tte)` since the `tte` family holds hours-to-end as a level, to 11-14).
  M3: the traded share by class at k (E015's class; `informed (E015)` after 11-15; reported).
- Paper rule and economic check (rule 11: maker-side). Maker: withdraw at T - 4 h from scheduled-publication markets and
  keep quoting barrier markets (the quantity captured is the class contrast in cents a share, gross, no fills; the AS
  avoided in the scheduled class is the route's value against the half-spread forgone in the barrier class). Taker
  (reported, never a verdict): exit scheduled-market positions at T - 4 h (the saving is the widening; against 2.9-7.2c
  round trips: "not shown").
- Population arithmetic. Closes about 740 a day (derived); usable (two-sided at both captures, no early proposal,
  unchanged `end_date`) planning 50%: 370 a day, 7,800 in 21 days; classed 44.7%: about 3,500; planning class split
  scheduled 25% / barrier 50% / consensus 25%: about **900 scheduled against 1,750 barrier**. DE at the formula about
  1.04-1.2; 31 beside.
- Permutation and cluster structure. Rule 24's between-market permutation of the class label inside the census-fixed
  strata (the class is a market-level constant, so the null is "given category, tier and close-day, the class does not
  predict the into-close spread change"); CR1 on event, two-way event x UTC day; worlds **S53: a liquidity world** (the
  scheduled class is finance and economics, more liquid, with smaller spreads and smaller changes: the strata hold tier
  and the contrast must survive within tier), **S54: a frame-selection world** (`gamma_rules`' frame is by volume, so
  classed markets are the busier ones: the unclassed share by tier is printed and the contrast is reported within the
  frame only, said so), **S55: a decided-early world** (barrier markets whose barrier was hit are proposed before the
  close and leave the population: the `decided_early` share by class is printed; the remaining barrier markets are the
  ones heading to NO, which is the mechanism's own prediction and is said).
- Planning MDE (class contrast; SD 2c; VIF 1.3). Low (900 / 1,750, DE 1.2): `3.47 x 2c x sqrt(1/720 + 1/1,400) x sqrt(1.2)
  x 1.5 x sqrt(1.3)` = **0.61c**; high (twice the counts) **0.43c**; a quarter of the low count 1.22c (fails). At DE 31:
  3.1c (fails; the convention is not the one-shot design effect and the census's computed value decides). F-MDE 0.96c
  (low, a verdict condition just under the cap) / 0.68c (high). **Kill line:** about 600 scheduled-class units in the
  window at the formula's DE, which is about 30 a day.
- Confounders and the control. Category composition (strata); the frame's selection (S54); the fee step (no fee term in
  a spread target; the sports re-classification disclosed); the crypto dailies (excluded: the crypto parameter; they are
  the densest scheduled class and the owner's call would add thousands of units a day); `attrlimit_lt11` and `_lt12` (no
  overlap: no event sums, twins or shocks); the `tte` family's levels (M2 `informed`); LT9's band objects (not read; the
  rewarded panel's into-close band behaviour is a reported arm `informed (LT9)` after its analysis).
- Most likely boring explanation. Makers withdraw into *every* close (a liquidity drain that does not depend on class)
  and the contrast is the scheduled class's liquidity; or classed units are too few outside crypto.
- Cheapest census (counts only; the last 8 days of sidecars plus `quotes/`; no spread after an origin read). Closes a
  day; the usable share; the classed share by tier; the class split; `decided_early` by class; the per-day distribution;
  the within-stratum SD of the class label against its between-stratum SD (rule 24's identification gate); MDE at the
  computed DE.
- Challenger feature: **after LT15's freeze** (token `close`): `cl_class x tte_h` interactions in a `tte` spec version;
  the class levels alone (`cl_class`) may be built now as a `rules` column (R03's idea; the 44.7% coverage disclosed).
- Sports arm: every game closes once and the sports oracle resolves within hours; the arm is the densest version of the
  test and is uncounted (the owner's parameter).
- Scores: N 3, EV 3, L 3. Priors: **P(census) 0.35; P(replicates | Supported) 0.4.** Parents: CH33, CH40, CH46, CH105,
  CH187, CH198, CH239, CH28, CH199. New: the one-shot unit at the close, the rule-class contrast, the T - 26 h twin, the
  end-cohort stratum.

### D. The engine's own history (parents DESIGN_V1 sections 2, 4, 17 and 19, CH259, CH184, CH43, CH36, CH167, CH175, CH212, CH217, CH220; literature: Hong and Stein 1999 on the gradual diffusion of private information, Blitz, Huij and Martens 2011 on residual momentum, Grundy and Martin 2001 on factor-adjusted momentum, Bates and Granger 1969 on combining forecasts)

**CH265. Residual momentum (`resid`): the champion's own per-market forecast error, written at every capture before
outcomes, isolates the idiosyncratic part of a market's recent moves (its features are common: momentum, market state,
category), and the idiosyncratic part diffuses slowly, so a market whose last 6-12 moves exceeded the champion's forecast
in one direction continues in that direction more than the raw momentum family says. The family stacks the champion's
lagged residuals on the same market as columns beside the base families.**
- Mechanism and why it is non-obvious. Blitz, Huij and Martens: residual momentum (the return orthogonal to the factors)
  carries the momentum effect with half the volatility; Hong and Stein: the slow diffusion is of *firm-specific* news.
  On this venue the champion's `mo_*` columns are the raw move and its display changes (`chg_1h/1d/1w`), and its
  `market_state` is the level; the residual `y - p` per market is already computed by the scorer daily and discarded as
  a per-market object. Who pays: the maker who re-centres on the common move and not on the story (gross; CH262 is the
  cost yardstick for anything the family adds). Why the crowd misses it: the engine's attribution is per family, never
  per market history.
- Parent and what is new. CH259 (`disp`: the specs' disagreement at the same slot), CH184 (the own move's event and
  category share), CH43 (the surprise score), the engine's design. New: the **per-market history of the champion's
  residuals** as a state (a meta-family on the engine's write-once predictions, rule 27), the sign-run and
  absolute-error columns, and the shuffled-prediction placebo.
- Data join and decision clock (`A`, L 5: `predictions/<capture>/se0_champion_lr_mm.parquet` for origins k - 1..k - 12,
  the realised 3-class labels of those origins, which for the 2 h target are known at k from the mid at k, for the 6 h
  target at k - 3 and later, for 24 h at k - 12 and later; nothing after k is read). Columns (aux `resid`):
  `rs_2h_l1` (the residual `sign(dmid) - (P(up) - P(down))` at k - 1), `rs_2h_m6`, `rs_2h_m12` (means), `rs_6h_m4` (the
  last four 6 h residuals known at k), `rs_24h_l12`, `rs_abs_m12` (the mean absolute residual: the market's own surprise
  rate), `rs_run` (consecutive same-sign residuals), with `unavailable` flags where a prior prediction or label is
  missing (counted). Clock: the predictions' own write times; the labels' the capture at k.
- Scored on. `dir_2h` (primary), `dir_6h`, `dir_24h` against se1 and the champion, event-clustered, market-deduplicated;
  the isolate `se27_lr_resid` (champion + `resid`) and a LightGBM version. Placebo (declared): the same columns computed
  from a within-capture shuffle of the champion's predictions must add nothing (|gain| < a tenth of the real columns').
- Killed at its census. |corr(`rs_2h_m6`, `mo_chg_1d`)| > 0.8 on eligible rows (momentum under another name); the
  residual's lag-1 autocorrelation within market under 0.02 (nothing to stack); or no gain over se1 on `dir_2h` at 28
  days with the CI excluding zero. Light: two parquet files a capture; < 300 MB; no capture read.
- Embargo. None found (no token names the engine's residuals); the section 19 note is required before the first column
  (rule 27); `attrlimit_*` interactions are not formed.
- Sports arm: the same columns on sports rows (the engine scores them) uncounted.
- Scores: N 3, EV 3, L 5. Priors: **P(census) 0.6; P(beats se1 at 28 days) 0.3.** Parents: CH259, CH184, CH43. New: the
  per-market residual history, the shuffled placebo.

**CH268. The fragile quote (`fragile`): the engine's own label store says which markets' next-capture quote keeps
vanishing (the label `unavailable`: one-sided or missing at k + 1), and a market with a high recent `unavailable` share
is quoted by one intermittent bot; its mid is unreliable, its flat class is over-forecast, and the public feed should not
rank it. First use is hygiene (the display pool and the input monitor); second use a family if the columns move the
flat class's log-loss.**
- Mechanism. CH36 (same-key outages), CH220 (dormancy), CH167 (the exit map), CH175 (the last-mid proxy), CH212 and CH217
  (row quality) all read the *current* row; the engine's label logs hold, per market, the history of whether a quote
  existed two hours later, which no capture field carries. A maker should not quote against a book that will not be
  there; a taker cannot exit; the product should not show a signal strength on a mid that is one bot's heartbeat.
- Columns (aux `fragile`, `A`, L 5): `fr_unavail_12` (share of the last 12 origins' 2 h labels `unavailable`),
  `fr_unavail_run`, `fr_onesided_24h` (from `quotes/` status codes at k - 12..k), `fr_hazard` (the market's empirical
  per-slot rate of leaving the two-sided state over the last 7 days). Clock: the label logs' and `quotes/` receipts at
  or before k.
- Scored on. The flat class and |dmid| (diagnostic) against se1; `dir_*` none expected. **First use, no K:** a display-pool
  rule (`fr_unavail_12` > 0.25 excludes the market from the public ranking) and an input-monitor line.
- Killed at its census. `fr_unavail_12` > 0 on < 5% of eligible rows (fragility is rare: hygiene only, no family); or
  |corr| with `log1p liquidity` > 0.8 (illiquidity under another name).
- Embargo. None. Sports arm uncounted. Scores: N 2, EV 2, L 5. Priors: **P(census) 0.5; P(beats se1 on the flat class)
  0.25.** Parents: CH36, CH220, CH167, CH175, CH212, CH217. New: the engine's label-availability history as the state, the
  hazard framing, the hygiene-first use.

### F. The map (parents CH240, CH251, CH261, CH262-CH268)

**CH269. The one-shot census and the tails map: one light reader (k = 0, counts only, < 500 MB, `net` lane) over the last
8 days of sidecars on the host, 45 days of `quotes/`, 35 days of `predictions/` and the label store, printing every
unprobed count above:** proposals seen a capture by category, tier and ladder position, and the seen share against the
resolution logs' daily counts (CH263); overdue interior-mid markets a capture by open-interest tercile and class (CH264);
closes a day, the usable share, the classed share and the class split, `decided_early` by class (CH267); downward
crossings of 0.010 and 0.015 a day by category and tier, and the zone's recorded half-spread (CH266's sketch); the
label-store win rate by 0.1c bin below 3c and above 97c with counts (CH266's map; no new resolution is read: the store's
own frame); the top decile's tier and fee-class split per capture from the pinned champion's prediction files, its
tenure distribution and its `unavailable` share at k + 1 from `quotes/` status codes (CH262; no mid after an origin is
read); the residual's lag-1 autocorrelation and its correlation with `mo_chg_1d` (CH265); the `fr_unavail_12`
distribution (CH268). It decides: LT14 is drafted if the 10k-100k top decile holds >= 100 units a capture at its median;
M1 (CH263) is drafted if proposals seen exceed 100 a day; M2 (CH264) if overdue units exceed 25 a day; LT15 (CH267) if
scheduled-class closes exceed 30 a day; CH266's sketch if display crossings exceed 50 a day; `resid` and `fragile` are
the builder's by their own lines. No table, token or column is created by it; nothing it prints is a target.

---

## 3. Ranked shortlist: the measurement lane, the economic lane, the one-shot lane, then the engine

Rank = the chance the object exists at the count its design needs x originality x the money's shape (hold-to-resolution
or spread, never a taker mid route) x how light the reader is, with rounds 14-18's rules and this round's 24-27 as hard
constraints. The last two columns are judgements.

| Rank | ID | One line | L | Population arithmetic (source) | Inference | Primary or estimand | Planning precision; F | P(census) / P(replicates) |
|---|---|---|---|---|---|---|---|---|
| 1 | CH263 | The carry, registered: the decided side's discount after a UMA proposal against the reversal tail and the recorded cost, one-shot, hold to resolution | 4 | about 740 resolutions a day non-sports ex-crypto (derived); proposals seen unprobed (planning 300-700 a day; 6,300-14,700 units) | a measurement (rule 26), k = 0; event bootstrap | `net = c - r(1 + c) - cost`, by tier, ladder position, wait; capacity | `net` to +-0.1c at 5,000 units; the tail bounded to 0.06c | **0.7 / 0.5** |
| 2 | CH262 | The engine at the touch: the champion's top-decile 2 h gross by tier against the cost model's rungs; the spread-scaling alternative; the flat decile for the maker | 5 | top decile about 1,830 a capture; 10k-100k about 425, >= 100k about 20 (planning from tier shares) | cluster-robust level per tier (k <= 2); FL on the within-market secondary | mean `g` > 1.30c (10k-100k), > 0.5c (>= 100k) | **0.03c / 0.13c** (10k-100k, DE 2 / 31); 0.22c / 0.87c (>= 100k); F 0.05c | **0.85 / 0.4** (P(clears 1.30c) about 0.10) |
| 3 | CH267 | The close: into-close spread widening in scheduled-publication markets against barrier markets, one unit per market, T - 26 h twin | 3 | closes about 740 a day; classed about 3,500 in 21 days (planning 900 scheduled / 1,750 barrier) | rule 24's between-market permutation; CR1 on event; DE at the formula | scheduled - barrier contrast on `ds` > 0 | **0.61c / 0.43c** (quarter 1.22c); F 0.96c / 0.68c | **0.35 / 0.4** |
| 4 | CH265 | Residual momentum: the champion's per-market residual history as a meta-family | 5 | every eligible row after 12 slots | engine (28 days vs se1); shuffled placebo | `dir_2h` log-loss gain | engine window | 0.6 / 0.3 |
| 5 | CH266 | Below the display: the longshot kink at the "<1%" line (map); the 0.010 crossing against 0.015 (sketch) | 5 / 3 | 21,516 tail resolutions in 12 days (all categories); crossings unprobed | map k = 0; sketch rule 24 | kink >= 1.5 points; `dt` display > placebo | map +-0.8 points at 600; sketch 0.10c / 0.05c | 0.3 (kink) / 0.4 (sketch) / 0.3 |
| 6 | CH264 | The overdue mid: the favourite's premium past `end_date`, inattention against ambiguity by open interest and rule class | 3 | unprobed (planning 30-150 a day) | a measurement, k = 0 | `q - p_fav - cost` by tercile x class; the proposal hazard | +-2.2 points at 1,000 | 0.45 / 0.35 |
| 7 | CH268 | The fragile quote: the label-availability history as a quoter-reliability state; hygiene first | 5 | every eligible row after 12 slots | engine; display-pool rule first | the flat class's log-loss | engine window | 0.5 / 0.25 |
| 8 | CH269 | The one-shot census and the tails map (counts only; decides the rest) | 5 | n/a | n/a | n/a | n/a | n/a |

**Top three, in one line each.**
1. **CH263, the carry.** The one route the programme has named since its first idea and never measured, dense enough to
   bound its tail to a twentieth of a cent in a single window, hold-to-resolution (the only cost regime the cost model
   calls viable), and light; it needs the `science-reviewer` to accept rule 26's role, which is the first decision this
   round asks for.
2. **CH262, the engine at the touch.** The owner's own standing rule asks for an economic check beside every accuracy
   claim; this is that check, registered, on two parquet files a capture, with the honest expectation that it returns
   "0.3-0.8c, scaling with the spread" and closes the question of whether the current champion is a route.
3. **CH267, the close.** The one verdict-shaped test here whose MDE clears the spread floor at the low planning count,
   because the one-shot unit removes the design effect that killed LT5-LT8; its risk is the rule-class coverage (44.7%)
   and the liquidity composition of the scheduled class, both of which the census prints before a line is written.

**The recommended first screen: CH269**, one job, counts only, `net` lane, `mem_mb` < 500, over stores the host keeps
longer than the 8-day snapshot retention wherever possible (the engine's `quotes/`, `predictions/` and label store), with
the sidecar reads limited to the last 8 days. It prints every unprobed number above and the per-day distributions, and
its lines (section 2 F) decide which of LT14, M1, M2, LT15 and the CH266 sketch are drafted. In parallel and at no
census cost: the builder's DESIGN_V1 section 19 note for `resid` (rule 27) and the `fragile` display-pool rule (no K).
**Expected number of registrations from this round: about 1.8** (CH263 0.7 + CH262 0.85 x the challenger's acceptance of
the parallel window, about 0.6, giving 0.51 + CH267 0.35 + CH264 0.45 x 0.5, giving 0.23), against the programme's record
of about 0.4 a family. The two measurements are the difference; without rule 26 the number is about 0.9.

**Two levers that are the owner's, stated once.** (1) **Sports** (231,473 rows a capture, 97.7% fee-on unrewarded before
the fee step; every one-shot count above is five to ten times larger on sports game markets, and the close is the game
end): one sports arm registered alongside any of CH262, CH263 or CH267 would be the cheapest additional live test in the
programme; the round keeps it uncounted because the owner has not decided, and because a sports edge against sportsbook
prices is a different programme (CH29, CH205, CH225, CH231). (2) **Crypto** (37,695 of 46,596 non-sports resolutions in
the CH242 census are the Up / Down series): the hourly series resolve inside a capture interval and would turn CH267's
scheduled class into thousands of units a day; CH30, CH76 and CH249 own the crypto fair-value objects, and the round
keeps crypto out of every primary as the owner's parameter.

**How the families would be registered.**
- **LT14 (CH262):** one Holm family, k <= 2 (tiers), on the engine's write-once files; census on the engine's files of
  LT12's census span for the tier split only (`informed (LT12 census)`); window 2026-12-10..12-31 in parallel with LT12
  on disjoint objects if the challenger accepts, else 2027-02-12..03-05; `attrlimit_lt14` on any display of gross by tier.
- **M1, M2 (CH263, CH264):** registered measurements under rule 26, k = 0, estimands and cost lines frozen before the
  window 2026-11-24..12-14; read-out >= 14 days after its end; the role accepted or refused by the `science-reviewer`
  before anything is sealed; nothing pooled with any verdict test.
- **LT15 (CH267):** one Holm family, k <= 1, after CH269; token `close` at the freeze; two-member events held out to
  LT12's date; the rewarded panel's into-close band behaviour `informed (LT9)` after its analysis.
- **Engine-first (CH265, CH268; CH266's note):** `resid` after the section 19 note; `fragile` as a display-pool rule
  first; the tails map's result as a section 2 note on `res_7d` eligibility.

**What is honest to say about all of them.** The venue's fields are mined; what this round adds is a place (the two
populations both tracks exclude), a unit (one per market, for the states that happen once) and a role (a measurement for
a route whose payoff is the resolution). None of the eight is a new field or a new feed, and three of them are the oldest
ideas in the file (CH01, CH33, CH189) given the design they needed. The money in CH263 is a few tenths of a cent a share
on a one-day capital turn if it exists, and the capacity line will say whether it is a hobby or a business; the number in
CH262 is more likely to end a question than to open a route. Nothing here is edge until it has gone through the map, a
census, frozen rules, prospective registration and an economic check at recorded prices, and the record says that about
two thirds of verdict-shaped families register no test at all. The first thing that will say whether any of it is worth
a design is CH269's count of proposals seen at a capture on an ordinary day.

## 4. Ideas considered and rejected, and why

### 4.0 Dropped as duplicates or closed (this round's own candidates, each with the record that closes it)

| Candidate this round | Why dropped | The record |
|---|---|---|
| The conversion route: in fee-on ladders "the field" is bought as NO on the favourite and converted (no CLOB fee on the conversion), so the favourite's book carries the ladder's flow | owned; dead panel | CH66 (conversion dumps), CH09 (asymmetric deviations); fee class is a panel (rule 20) whose content the fee step removed (q0717); LT13 R1 MUST 4: fee and age separate only by functional form |
| A question-text family from the capture rows | no text | the capture rows carry no question text (rounds 7-17's inventories); `gamma_rules` holds it for 44.7% (R03 `rules`, CH239 `ruleclass`); CH117 owns logical form |
| The settlement cohort (markets closing at the same minute across events) as a latent join on spreads | CH253 under another key | the batch join (CH253 / LT13) with `end_date` instead of `created_at`; rule 21 would need a new pin for no new mechanism; CH98 owns the resolution wave |
| A one-shot birth test (the seed's width at age 12 slots by batch size) | LT13's levels | CH22, CH56, CH130, CH154 own the first day; `bt_n` is a `batch` level the builder may build (round 18); the mates' behaviour is LT13's object |
| Election night at 1 min (CB15-E books against `predictit`) | one cluster | CH129, CH208, CH230; one night is one event (pattern 4); a descriptive case for `CASE_CATALOGUE.md`, not a test |
| The `competitive` sidecar field's innovation as a display-rank clock | venue-computed semantics | CH194 died on a venue-computed field; CH176 and CH236 own display rank; a map of the field's meaning would come first and is not worth a slot |
| The midterm resolution wave as a maker-capital natural experiment | one event | CH98, CH68, CH254 (`shock`); rule 22 |
| The engine's `res_7d` decile held to resolution against the fee-only hurdle | the record | STATUS 10-24: for `res_7d` the champion is no better than the market price; would need rule 26; folded into CH262 as a note, not an arm |
| The flow screen's alerts at the touch (the same shape as CH262 on the exploratory screen) | later | the screen's rows are DEVELOPMENT trials; the `flow` family is embargoed to 11-16; a second economic lane after LT14 reports |
| PredictIt or Smarkets light tests on matched politics markets | tiny frames | CB15-P closed at 37 pairs in 12 events; R04 `xvenue2` "coverage likely tiny"; CH114, CH208, CH229, CH230 |
| The proposer's footprint (large prints in the hour before a proposal) | not a unit | round 14's rules 1 and 6 (monitor prints are engine inputs, never units); CH216; predicts nothing (the outcome is known) |
| The fee step itself as a natural experiment on spreads, volume and the rebate | one event; unverified | q0717: one capture pair, all markets at once (a common state, rule 22); whether fees are charged is unverified; the right action is a re-read of the venue's fee page and a `COST_MODEL.md` refresh (qcm1), which is an ops recommendation, not a hypothesis |
| The hourly crypto series as a fast-resolution test-bed for CH267's scheduled class | the owner's parameter | CH30, CH76, CH102, CH249 own the crypto series; kept as the second lever in section 3 |
| Residual momentum along joins (the batch-mates' or siblings' residuals) | owned | L1-L4 and E005 (null), CH166, CH246, CH253 own diffusion along joins; `resid` is the own history only |
| Markets with `accepting_orders` false | killed | `pause` (CH257) at its map: 0 eligible halted in a day |
| Anything wallet-level; any manipulation route; any Kalshi change column; any band, pool, omission, twin, sibling-sum or batch innovation | sealed / owned | E026 (to 12-07), rounds 1-2, LT9-LT13's tokens |

### 4.1 Ideas rejected on the design rules, and why

- **Common states as live primaries** (rule 22): the fee step, the midterm wave, a category's attention day; each a
  single cluster or about 170 category-days; disclosures or engine families.
- **Resolution targets as verdict primaries** (rule 19): the carry and the overdue premium are measurements (rule 26),
  never Supported; the tails' kink is a map; the engine's `res_7d` is the home of every calibration claim inside
  eligibility.
- **Level states as primaries**: the decile membership in CH262 is a level and is tested as a level against a constant
  (a measurement of gross), with the within-market contrast as the FL-gated secondary; the rule class in CH267 is a
  market-level constant and enters as a between-market contrast under rule 24, never as a within-market state.
- **Any whole-panel mid class contrast under about 700 units a capture in its smaller class**: none here reads a mid as
  a verdict target except CH262's level, whose tier counts are 425 (10k-100k) and whose MDE is quoted at both design
  effects.
- **Latent joins without a pin** (rule 21): none (no join is drawn this round).
- **Label-only F chosen for power**: none; CH267's F binds at both planning ends; CH262's F is a verdict condition.
- **Taker routes as primaries**: the carry and the overdue premium are taker routes but hold-to-resolution (no exit
  leg) and measurements; every taker mid route here is reported, never a verdict.
- **Maker mark-out objects**: none; every maker line is gross, no fills; J4-R's and CB13-T's holdouts are not read.
- **Trade-sample or monitor units as primaries**: none; sweep 1's `ask_size_1` enters CH263 only as a capacity line.
- **Reading the unit's own outcome**: only under rule 26, after the window, as the declared payoff of a measurement.
- **CH01-CH261: not re-proposed**; where an idea touches one, the parent is named and the new unit, role, clock, join or
  store is stated (CH262 on the engine's design, `COST_MODEL.md` 5, CH77, CH156, CH172, CH186, CH196, CH43, CH259; CH263 on
  CH01, CH02, CH226, CH134, CH47, CH221, CH85, CH207, CH242; CH264 on CH189, CH62, CH175, CH226, CH65, CH207, CH85; CH265 on
  CH259, CH184, CH43; CH266 on CH17, CH60, CH164, CH232, CH15, CH86, CH260; CH267 on CH33, CH40, CH46, CH105, CH187, CH198,
  CH239, CH28, CH199; CH268 on CH36, CH220, CH167, CH175, CH212, CH217; CH269 on CH240, CH251, CH261).

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
`EXPERIMENT_LEDGER.md` (the scout's bounded read of the last 600 lines and 457 keyword matches: the LT3-LT8 census drops
and closures with their numbers, E022's registration and DE, CB8-B's and CB11-W's coverage failures, CH243's medians, the
storage and failed-job lines, the registered windows, the CH261 and q0717 entries); `CH261_MAP_2026-10-28.md` (in full);
`reviews/LT13_CHALLENGER_R1_2026-10-28.md`, `reviews/LT13_Q0717_RESULT_2026-10-29.md` (sections on coverage and the facts
that decide the rule) and `reviews/LT13_Q0717_RECHECK_2026-10-29.md` (in full); `LIVE_TESTS_13.md` (the header and the
section list); `signal_engine/STATUS.md` (10-29 23:58 UTC+1, in full); `signal_engine/NORTH_STAR.md` (in full);
`signal_engine/CANDIDATES.md` (the embargo rounds, the round 16-18 notes, the builder table rows 1-26 and the round-18
reply); `signal_engine/DESIGN_V1.md` (sections 2-4 by grep: targets, base eligibility, the champion's families, the
signal-strength vocabulary and the display pool); `COST_MODEL.md` (in full); `NEW_STREAMS_2026-10-19.md` (sections 1-4);
`COLLECTION_HOST.md` (in full); `queue/README.md` (the lane, memory-gate and light-job lines); `data_catalogue/README.md`
(in full); `CROSS_VENUE_LIVE.md` ("What runs"); `LIVE_TRADE_MONITOR.md` (the pilots' counts); `LIVE_TESTS_2.md` (the
header); `CREATIVE_HYPOTHESES_2026-11-01.md` (round 18 in full, including its 0.1, 0.2, facts, section 3 and section 4);
`-31.md` (round 17's rules 18-20); `-30.md` (round 16's rules 15-17); `-29.md` (round 15's rules 12-14 and its lane
paragraphs); `-28.md` (round 14's failure patterns and rules 1-11); the lead sentences of CH01-CH261 from all eighteen
rounds (the scout's inventory, one line each, used for the duplicates table and the parents named), and keyword checks
across all eighteen rounds for open interest and mint share, `competitive`, the 15-minute and hourly crypto series,
residual momentum and own error, monotonicity and dominance, PredictIt's and Smarkets' structural facts, fill probability
and "where the fills are", capital cost and the short side, the display threshold and sub-cent prices, question text,
conversion and fees, and one-shot units (the novelty gate of section 4.0); `backend/astrolabe/research_lab/ext_sidecar.py`
(the sidecar's field map, one line) and the CB12 readers' use of `umaResolutionStatuses` (grep only), for fact 6. Still
no host probe, no network and no data-dumps read. Every count is as the named document states it on 2026-10-29; nothing
was recomputed except the planning MDEs and precisions from round 14's stated formula and the derived resolution density
of fact 2 (a subtraction and a division, marked as planning only).

### 5.2 External literature (named, not fetched)
Grossman and Stiglitz 1980 (the equilibrium degree of mispricing); Roll 1984 (the bid-ask bounce as a spurious component
of measured price changes); Hasbrouck 1991 (the information content of trades against quote revisions); Thaler and
Ziemba 1988 and Snowberg and Wolfers 2010 (the favourite-longshot bias); Barber and Odean 2008 (attention and the
visibility of a price); Duffie 2010 (slow-moving capital); Garleanu and Pedersen 2011 (margin-based asset pricing and the
cost of posting collateral); Kyle 1985 (the informed trader's timing against a scheduled resolution); Admati and
Pfleiderer 1988 (intraday patterns from scheduled information); Easley and O'Hara 1992 (the no-trade interval before an
announcement); Jiang, Likitapiwat and McInish 2012 (spreads around scheduled releases); Hong and Stein 1999 (the gradual
diffusion of private information); Blitz, Huij and Martens 2011 (residual momentum); Grundy and Martin 2001
(factor-adjusted momentum); Bates and Granger 1969 (combining forecasts); the venue's fee, rebate, liquidity-reward and
tick-size documentation as `COST_MODEL.md` section 2 quotes it, and the venue's display convention as fact 7 states it,
to be re-read at any pin.
