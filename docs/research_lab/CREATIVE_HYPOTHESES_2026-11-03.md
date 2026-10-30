# Creative hypotheses, round 20: the pinned touch, the surviving side and the adding-up constraint (2026-11-03)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-30 from 07:26Z on parent
`88b5cdf2`, the merge of `0e1b41d5` (`chore/arepo-claude-setup`) into the worktree `feat/creative-r20`; the file carries the
round's planned date as earlier rounds did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md`
(CH35-CH59), round 3 `-17.md` (CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md`
(CH118-CH130), round 7 `-21.md` (CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10
`-24.md` (CH169-CH179), round 11 `-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201), round 13 `-27.md` (CH202-CH211),
round 14 `-28.md` (CH212-CH221), round 15 `-29.md` (CH222-CH231), round 16 `-30.md` (CH232-CH241), round 17 `-31.md`
(CH242-CH251), round 18 `-11-01.md` (CH252-CH261), round 19 `-11-02.md` (CH262-CH269); this file starts at **CH270** and
repeats none of them. Where an idea builds on an earlier one, the parent is named and the new mechanism, clock,
population, unit or join is stated. Every number quoted from an AREPO document is a development, census, map, probe or
operational figure, not evidence. One file; no code, no queue specs, no other commits. **No network request, no host probe
(no `ssh oracle`) and no `data-dumps` read were used for this round** (by instruction); every count below is taken from a
named AREPO document (`EXPERIMENT_LEDGER.md` from "Creative round 19 recorded" to its end, `reviews/CH269_MAP_2026-10-30.md`,
the summary keys of `seals/M1_J0_q0731.json`, `signal_engine/STATUS.md` (10-30 06:10 UTC+1), `signal_engine/NORTH_STAR.md`,
`signal_engine/CANDIDATES.md` (rows 1-31 and the round-19 note), `signal_engine/DESIGN_V1.md` sections 2, 3 and 27,
`COST_MODEL.md`, `NEW_STREAMS_2026-10-19.md`, `COLLECTION_HOST.md`, `queue/README.md`, `data_catalogue/README.md`,
`LIVE_TESTS_14.md` section 1.2, `MEASUREMENT_M1_CH263.md` sections 3.1 and 13, `LIVE_TRADE_MONITOR.md`'s pilot table,
`lab_dashboard/registry.json`, the lead sentences of CH01-CH269 and rounds 14-19's design rules) and is named as such.
Where no count exists the entry is marked **unprobed** and the counts-only map of section 2 E (CH276) is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities 2026-10-19 and 10-21; orchestrator brief for round 20).** Original
hypotheses about how money could be made on Polymarket lead the programme. This round's priorities, in order: ideas that
can become **light prospective live tests or registered measurements quickly**, on streams the host already captures (the
2 h snapshots and sidecars, the two book sweeps, the engine's write-once stores, the cross-venue poller, the live trade
monitor, the wallet and copy streams), with `mem_mb` < 500 and the `net` lane; each built against the recurring death
causes (count gates, within-market dependence, control availability, fee and cost hurdles, capacity); at least two
engine-family candidates whose features are computable at every capture from captured inputs with no resolution read in
a live primary; and genuinely original mechanisms. Category-agnostic, sports and crypto as the owner's parameters. No
data-rights topic is raised. Nothing here reads any registered live test's window objects; nothing here reads LT10's,
LT11's, LT12's, LT13's or LT14's window captures or census spans for any census. Round 14's design rules 1-11, round 15's
12-14, round 16's 15-17, round 17's 18-20, round 18's 21-23 and round 19's 24-27 **bind here unchanged**; this round adds
three (0.3).

**What this round does differently.** Round 19 opened three places (the engine's blind spots, the one-shot lane, the
engine's own stores) and the programme walked into them within a day: the CH269 map ran, M1, M2 and LT14 were drafted
(LT14 frozen), LT15 was not drafted, `resid` died at its census and `fragile` was not built. The **M1-J0 counts** then said
something no round had known: at the first capture that shows a UMA proposal, **the favoured side's ask is already at
0.999 or 1.000 on 97% of the eligible units** (S6: 1,195 of 1,232 at `c <= 0.001`), **three quarters of all proposal rows
are one-sided** (3,923 of 5,155 in scope: `not_two_sided`), the sweep covers 9 of 1,232 units, 99% of the units are
fee-free `other:zero_fees`, 42% are proposed **before** their `end_date`, and 79% are ladder members proposed as the
winner. So the carry at the touch is a tick; the money, if any, is in **the bid** (who sells the decided side under 1.00,
how much and when), in **the siblings** the sidecar does not flag, in **the wait** before the proposal rather than the
discount at it, and in the three quarters of the population that every track treats as missing because one side of the
book is gone. Those are this round's places. On the engine side the two unread objects are structural rather than
field-level: the **adding-up constraint** of a neg-risk event, which the champion ignores because it predicts each member
alone, and the **surviving side of a one-sided book**, which is a firm price that the engine throws away both as a label
and as a state. Seven entries: two engine families (CH270, CH271), two companions to M1 that are cheaper than any new test
because M1's extractor already builds the unit (CH272, CH273), one registered measurement of the quantity every carry
route divides by and no document holds (CH274), one verdict-shaped one-shot live test whose target is a sidecar state and
not a resolution (CH275), and the counts-only map that decides the rest (CH276).

### 0.0 The recurring death causes (the ledger's record, counts only; what each idea below is built against)

Round 19's tally binds (LT3-LT8's censuses dropped 23 candidates and 3 more died before their census; the survivors are
E015 and E022; LT11 k <= 3, LT12 k <= 2, LT13 k <= 1, LT14 k = 1; two thirds of verdict-shaped families register no test).
The nine causes are restated in one line each with what the last day added, and three readings M1-J0 forces are new.

1. **Units per market, not units.** Rare states empty the market x day stratum. Round 19's answer, the one-shot unit
   (rule 24), survived its first contact: 1,232 proposal units in 8 days, 740 events, DE at the formula about 1.0-1.2.
   Every unit below is one per market or an engine row.
2. **The MDE gate, not the count gate.** LT5 F at 1.01c against 0.5c with every count gate passing; whole-panel DE 31.
   The one verdict test here (CH275) has a binary target at a low base rate and says so: its MDE is quoted at the
   planning counts and at 42 days, and its census can kill it.
3. **Held share, strata and persistence.** Level states pay twice. Nothing below is a level as a primary; the engine's
   columns are deviations (CH270) and histories (CH271).
4. **Source coverage and field semantics.** Now with three new instances: **sweep-1 coverage of proposal units 0.73%**
   (M1-J0 rule (c)), **`open_interest` empty on all 25,256,781 sidecar rows** (CH269), and the **`uma_resolution_statuses`
   list**, whose recorded forms alternate `proposed, disputed, proposed, disputed, ...` up to 30 elements on 96 units
   (M1-J0 `status_forms`): whether the list is per market or per event is not established in any document read for this
   round, and two entries below (CH273, CH275) hinge on it. The map's first line is that reading.
5. **Non-stationarity.** The venue clock gate (<= 50% of units in one slot) and the per-day distribution are printed by
   every census here; M1-J0's per-day counts ran 85-233.
6. **Control availability and placebo coverage.** The placebo lives on the same unit: the shuffled event join (CH270),
   the same market's own earlier slots (CH271), the pre-proposal 24 h of the same market (CH272), the between-event
   permutation inside census-fixed strata (CH275).
7. **Common states.** None below; the one venue event of the fortnight (the fee step) is a map line for the cost model's
   refresh, never a test.
8. **The cost floor.** The hold-to-resolution regime is the only one under 1c (`COST_MODEL.md` 8), and M1-J0 now says the
   taker side of that regime is pinned at a tick on 97% of units. Every route below is maker-side (a resting bid) or
   hold-to-resolution on the side the market has already decided, and every cost line is printed at the served rate (0 on
   99% of M1-J0's units) and at the docs rate.
9. **Lanes and memory.** CH269 peaked at 558.8 MB against a 450 MB spec; M1-J0 at 297.6 MB. Light means `mem_mb` < 500,
   the `net` lane, and inputs the host keeps longer than 8 days wherever possible (`quotes/` and `features/` 45 days,
   `predictions/` 35 days, the monitor's day files, the label logs).

**Three readings M1-J0 adds (new; they shape every entry).** (a) **The pinned touch.** When the ask is at 0.999 the taker
carry is 0.1c a share before fees and the design question is no longer "how big is the discount" but "who sells into the
bid, how many dollars, and how long until settlement"; a capacity question and a wait question, neither of which the
touch answers. (b) **The one-sided majority.** A population in which three quarters of the units have one side of the
book missing is not a population with missing data; it is a population whose state *is* the missing side. A bid-only
book at 0.99 is a firm price at which a holder can sell; it is not an undefined mid. (c) **The proposal is not the
settlement.** 42% of proposals come before `end_date` and the market leaves the listing within one capture; the wait
from "decided" to "paid" is the carry's denominator and is unmeasured anywhere in the programme.

### 0.1 What changed since round 19 (ledger 10-30 02:06Z to 07:10Z; CH269; M1-J0; STATUS 10-30 06:10 UTC+1)

- **CH269 ran (q0730, 04:04-04:19Z, 96 of 96 slots of 10-22T04Z..10-30T04Z; peak RSS 558.8 MB):** proposals seen 821 a day
  non-sports ex-crypto (median 40 a capture; side readability 1,518 readable / 4,623 not two-sided / 103 unread;
  half-spread at k median 0.0005) so **M1 drafted**; overdue interior-mid units 159 a day so **M2 drafted** (REVISE applied);
  top-decile 10k-100k units 175 a capture so **LT14 drafted** (on the *signed* decile with a fee-split dict-overwrite
  defect, both disclosed; LT14's own census carries the binding |s| gate); scheduled-class usable closes 20 a day under
  the placeholder classifier so **LT15 not drafted** (closes 1,474 a day; class split barrier 2,263 / both 493 / no_rules
  286 / other 593 / scheduled 164 over the window; decided early 483); display crossings 588 a day so **CH266's sketch
  kept**; `resid` **killed** (within-market lag-1 residual autocorrelation -0.086 / -0.091); `fragile` not killed by the
  map but **not built** by the engine (the unavailable states are almost all whole missing captures; the market-specific
  share 0.0000, because a one-sided market has no features row). The label store holds 240,936 records (237,526 resolved,
  1,035 split, 2,375 not found).
- **Rule 26 ruled ACCEPT_WITH_CONDITIONS** (`reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`): estimand-only wording,
  everything frozen and code-pinned before the window, every split reported, later tests on the same object `informed
  (M1/M2)` on a disjoint later window, **measurements counted apart from registered tests**, void on any post-start change
  or early read, read-out >= 30 days after the window. M1 (`MEASUREMENT_M1_CH263.md`, third draft b71a3529): window
  **2026-11-24..12-14**, registration deadline 11-22, read-out on or after 2027-01-15; headline `c - r_eff`; cost line fee +
  capital, no half-spread; decision time the latest receipt of row, sidecar and sweep 1; tail bound at event level (about
  24,800 units needed for the planned precision, so a "coarse" read is expected and disclosed). M2 (`MEASUREMENT_M2_CH264.md`,
  second draft 1c12f2ed): the same window, disjoint units, text freeze by 11-16, read-out on or after 01-29; the size split
  on sidecar `liquidity` (open interest empty everywhere), capacity unavailable by construction.
- **M1-J0 (q0731, 05:41Z, `m1-j0-v2`, peak RSS 297.6 MB; `seals/M1_J0_q0731.json`; counts only, no price, outcome or
  resolution read):** 84 captures, 6 full days; **1,232 eligible units over 740 events; median 185 a full day; projected
  3,885 in 21 days** (rules (a) / (b) not fired; 21-day window kept). Funnel in scope: `already_proposed` 970, `contested` 83,
  `disputed_at_k` 1,597, `no_k_minus_1_row` 15, `not_two_sided` 3,923. Splits: tier 287 / 569 / 370 / 6 (< 1k / 1k-10k /
  10k-100k / >= 100k); fee key `other` 997, `unknown` 223, economics 6, politics 3, culture 2, weather 1; **fee_free 1,220 /
  fee_on 12**; ladder position **member_winner 976 / member_loser 85 / standalone 171**; side YES 1,147 / NO 85; **zone
  `c <= 0.001` 1,195**, (0.001, 0.005] 27, (0.005, 0.01] 6, (0.01, 0.03] 4; **`end_date` future 521 / past <= 24 h 631 / past
  > 24 h 79**; event members 1: 171 / 2-5: 327 / 6+: 734; tick 0.001 on 1,221; sweep-1 finite `ask_size_1` on **9 of 1,232**
  (0.73%; 10 units with any sweep row); 939 of 1,232 in the engine's `res_candidates`; sidecar-minus-row receipt gap 0 s;
  `status_forms`: 384 units with the 4-element form `proposed, disputed, proposed, disputed`, 96 with a 30-element form.
- **LT14 DESIGN TEXT FROZEN** (`LIVE_TESTS_14.md` 485c63dd, sha256 `f047c000…2f815`): one Holm family, **k = 1** (the 10k-100k
  tier, label-origin 2 h gross of the pinned champion's top decile by |s| against `H_A` 1.30c; the >= 100k tier a reported
  arm); pinned `P` = `se0_champion_lr_mm` (spec_sha256 `19549cb4…f919`); census on the engine files of [2026-11-07, 11-17);
  window **2026-12-10..12-31** beside LT12; **`attrlimit_lt14` in force**: no computation or display of `P`'s cents gross or
  top-decile hit rate by liquidity tier anywhere until LT14's analysis. Nothing below computes it.
- **The engine (STATUS 10-30 06:10 UTC+1):** 29 models; `se28_lr_rules` added (aux `rules`, nine columns from the hourly
  `gamma_rules` stream as it stood before each capture; `rc_has` 0.354 of 51,017 eligible rows, **0.700 of non-sports**;
  hand audit `cl_sched` 10 / 10, the borrowed barrier lexicon 3 / 13, so `rc_occur_by` was added and disclosed; no se28
  gain credited before about 11-18); `se27_lgbm_stress` registered 10-30 (no gain credited before a slotfac-only arm);
  `rsrev` gate not met (se1's own residual lag-1 -0.0021: the trees already absorb the reversal); disk cap 16 GB; first
  promotion reads about 11-04; LightGBM leads the logistic champion by about 0.045-0.048 nats on `dir_2h`. Next cheap
  family on the builder's list: CH207 `umaparams`.
- **Ops:** E009 / E010 end 11-03; E011 11-10; LT2's analysis from 11-13; E015's from 11-15; E022's window 10-26..11-16; E026's
  receipts 10-25..11-15 (analysis from 12-06); LT10 11-10..12-01; LT11 11-18..12-09; LT12 and LT14 12-10..12-31; M1 and M2
  11-24..12-14; LT9 12-30..01-20; LT13 01-21..02-11. The CB15-E election-night books run 11-02..11-06.

### 0.2 The census arithmetic, restated once, with the measurement reading

Round 16's table and round 19's one-shot reading bind (a 2 h mid class contrast needs about 690 units a capture in the
smaller class; a one-shot spread class contrast at 1,500 / 1,500 units and DE 1.1 gives 0.49c; the non-sports ex-crypto
universe produces about 740 resolutions a day). Two numbers from the day replace planning figures: **185 eligible
proposal units a day** (M1-J0; 821 a day seen in any state, CH269) and **1,474 closes a day** (CH269). For a measurement
(rule 26) the gate is precision, not an MDE: `SE` of a mean at `n` one-shot units is `SD / sqrt(n x 0.8)` with an
event-cluster bootstrap; a Clopper-Pearson bound on a rare share at 0 observed in `n` is about `3 / n`. For the one
verdict test here with a binary target at base rate `b`, the class contrast formula of round 14 applies with
`SD = sqrt(b (1 - b))`; at `b` 0.02 the SD is 0.14 and the arithmetic is unforgiving (CH275 quotes it).

### 0.3 Design rules (rounds 14-19's 1-27 bind unchanged; three additions)

28. **The surviving side is a firm price.** A one-sided book carries a bound, never a mid: a bid at `p` is a price at
    which a holder can sell, an ask at `p` a price at which a buyer can buy. A **label** may use the bound only where it
    alone decides the class (the surviving bid above `mid_k + delta` is up; the surviving ask below `mid_k - delta` is
    down; anything else stays `unavailable`, counted). A **state** may read which side survived and when, never an imputed
    mid. No one-sided row enters a mid-level estimand; a measurement that reads a bid-only row reports the bid as a bid.
29. **The companion measurement.** A second estimand on a registered measurement's own units (its capacity from another
    stream, its siblings, its wait) is an **amendment filed before that measurement's design-text freeze** or a separate
    measurement on a **disjoint later window**; never a verdict test on the same window, never a pooled read. The
    companion inherits the parent's decision time and unit list by sha256 and adds nothing to the parent's estimands.
30. **The adding-up constraint and the engine's own predictions.** A family built from the engine's own predictions on
    the *other* members of a unit's event is a meta-family under DESIGN_V1 section 37 (visible, non-embargoed, pinned
    spec, the same or an earlier capture); its placebo is the **shuffled join** (event ids permuted within the capture,
    sizes preserved); it may sum predictions across members, and it may not sum **quotes** across members while any
    token on event sums holds (LT11's to 12-09, LT12's to 2027-01-03).

**Hygiene that binds every idea** (round 14's paragraph applies: decision time is the latest input's own receipt; targets
start after it; nothing reads outcome fields of the unit except engine-first `res_7d` features and, under rule 26, the
declared payoff of a measurement after its window; the primary of a verdict test is a within-stratum contrast by expanding-
past demeaned OLS or, for a one-shot binary target, a between-market class contrast with rule 24's permutation null in the
census-fixed stratum; the liquidity-tier correlation gate and the AR(0.9) scenarios bind; F in LT7's one-rule form is a
verdict condition where its census F-MDE is under the target's floor). Sports stays a parameter (every non-sports entry
reports its sports arm uncounted; the sports classification follows the vendored rule on post-step values with 1,800
re-classified markets disclosed). Nothing here is a maker mark-out object; J4-R's and CB13-T's holdouts are not read.
Nothing here reads LT9's (`bandbreak`, `pool`, `rwblink`), LT10's (`kxbook`), LT11's (`xw`, `cl_sib`, `xo`, `dollarw`,
`nrslack`, `bandside`), LT12's (`zs_D`, `shock x unrew`, `mirror`, `mixedlad`), LT13's (`batch`) or LT14's (`P`'s gross by
tier) objects, their twins or targets, or their windows. Nothing here reads a wallet hash.

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5)** as round 18 defined it (5 = a pure
reader over stores the host already writes with the population counted by a named probe; 4 = pure reader, population
bounded above by a named count; 3 = pure reader with an unprobed population, or a map first; 2 = a stream whose coverage
is unprobed; 1 = fetches or weeks). **Priors** are two numbers, both my judgement: P(census) = the idea passes its own
census or map as written; P(replicates) = given a Supported verdict (or, for a measurement, a net above its cost line),
the number holds on a second prospective window; for engine families, that the isolate beats se1 on its target over 28
days.

**Planning-MDE arithmetic (round 14's, stated once).** Class contrast: `MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x
sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; `n_eff` = 80% of raw; `DE_gate` the LT11 formula `max(floor, 1 + (m - 1) x 0.02)`
at the event's member count for one-shot units (31 printed beside it, as the rules require); `VIF_w` 1.3 for row and
sidecar states. For a binary target `SD = sqrt(b (1 - b))`. Measurements quote precision, not an MDE.

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture 42,161-51,790 (DESIGN_V1 sections 3 and 16; 51,017 on 10-30, STATUS); eligible non-sports on
   single captures 18,232-18,349. Base eligibility: binary, open, active, two-sided, spread <= 0.10, mid in [0.02, 0.98],
   end after the origin, no UMA proposal in the origin sidecar row. Label states: `labelled`, `pending`,
   `unavailable_missing_capture`, `unavailable_absent`, `unavailable_closed / inactive / one_sided`, `unavailable_split`,
   `unavailable_other`, `unavailable_unresolved`; the leaderboard publishes their daily counts (DESIGN_V1 section 2; the
   counts themselves are in no document read here: **unprobed**).
2. **The engine's stores** (`data_catalogue/README.md`; `LIVE_TESTS_14.md` 1.2): `quotes/<capture>.parquet` holds every binary
   market of a complete capture with `market_id`, `t_off`, `bid`, `ask` **for open two-sided rows only**, and `st` (0 open
   two-sided, 1 closed, 2 inactive, 3 otherwise not two-sided); `features/` holds eligible rows with `event_id`, `category`,
   `t_row`, `end_ts`, `ms_*`, `mo_d2h`; `predictions/<capture>/<model>.parquet` write-once uint16 aligned with features;
   `logs/predictions-*.jsonl` the receipt times. Retention proposed 45 / 45 / 35 days, not active; `quotes/` and
   `features/` exist from 09-15, `predictions/` from 09-25 (CH269).
3. **The proposal population (M1-J0 and CH269, as 0.1 states them):** 185 eligible units a day, 821 seen a day; 97% at
   `c <= 0.001`; 76% of in-scope proposal rows not two-sided; 79% ladder winners; 42% before `end_date`; 99% fee-free;
   sweep coverage 0.73%; `disputed_at_k` 1,597 rows in 84 captures (about 19 a capture); 7 units a day are losers
   proposed at the same capture as their winner (85 in 8 days).
4. **Neg-risk structure (the CH240 map q0680, 10-16..10-22, non-sports ex-crypto, per capture; round 17 fact 2):** neg-risk
   events 1,664 rewarded / 825 unrewarded; member rows 14,123 / 4,933 (about 8.5 / 6.0 members an event); complete
   event-captures about 1,833; two-member events complete 1.00 / 0.97. The eligible-member count per event at a capture
   (the engine's `event` family carries it) is **unprobed** in any document read here.
5. **The cost model (`COST_MODEL.md` sections 2, 4, 5 and 7):** fee `rate x p (1 - p)` a share for the taker, makers never;
   at `p` 0.99 the docs-rate fee is 0.04c (0.04) to 0.07c (0.07) a share, at `p` 0.95 0.19c (0.04); the served schedule is
   `rate 0` on about 0.90-0.95 of non-sports ex-crypto rows since 10-20T18:31Z (q0717; LT12 disclosure), **unverified as a
   charged fee**; every cost line below is printed at both. Tier spreads p50 4.9 / 3.0 / 2.0 / 1.0c; $100 round trips 9.9 /
   7.2 / 3.9 / 2.9c; adverse selection 3.87 / 2.45 / 2.04 / 0.39c; queue fills within 1 h 1.9 / 4.3 / 2.9 / 3.4%; the only
   regime under 1c: passive entry held to resolution, plus fee-free rows. Rebates are funded by taker fees, so a fee-free
   row pays its makers nothing but the liquidity programme (section 2).
6. **The live trade monitor (`LIVE_TRADE_MONITOR.md`; `COLLECTION_HOST.md`):** every taker print of at least $1,000
   (`takerOnly`), 300 s cycles, stored with receipt time, venue time, market, side, outcome, size, price and an HMAC wallet
   hash; the pilot's steady state about 13 prints a cycle, about 160 an hour, all categories; day files
   `live_trades/trades-YYYYMMDD.jsonl`, a 7-day history on the host, archived nightly, 3 GB cap; enrichment is budgeted
   (50 markets a cycle) but the print line is stored regardless. The non-sports ex-crypto share of prints and the prints
   inside proposal windows are **unprobed**.
7. **Streams the host runs** (round 19 fact 5, unchanged): the pass at :31 every 2 h; the monitor; the E009 / E010 poller
   (sealed to 11-03, then `xv_quotes/`); `predictit`, `smarkets`, `espn_odds`, `gamma_rules`; `reward_params` every 2 h;
   CB15-E books 11-02..11-06; the engine's per-capture stores. The queue: lanes `cpu` and `net`, light jobs `mem_mb` < 500
   exempt from the exclusive drain and the 02:45-05:30Z blackout. Nothing here proposes a new collector.
8. **Row and sidecar fields** (round 18 fact 7; round 19 fact 6): the touch (`best_bid`, `best_ask`, with one null on a
   one-sided row), `last_trade_price`, `volume24hr`, `liquidity`, `chg_*`, `end_date`, `created_at`,
   `uma_resolution_statuses` (a list, parsed as a string; no proposal timestamp; **per-market or per-event: unprobed**),
   `fee_schedule`, `fees_enabled`, `fee_type`, `fee_category`, `clob_rewards`, `open_interest` (empty), `accepting_orders`,
   `order_price_min_tick_size`, `neg_risk_market_id`, `event_neg_risk_augmented`, `series_slugs`, the event fields and the
   comment count; no question text on the capture rows.
9. **The record this round must not repeat** (round 18 fact 11; round 19 fact 8; section 4 below): nothing here is a
   mover, a band, a ladder sum of quotes, a twin, a fee panel, a comment count, a halt, a flip, a collapse, a batch
   innovation, a Kalshi change, a wallet, a manipulation route, a trade-sample unit, a monitor print as a unit, a
   time-of-day effect, or a re-run of CH263 / CH264 / CH262 / CH267.

**Counts table (what was counted before each idea was written; the source named; `unprobed` where nothing was).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH270 | eligible non-sports ex-crypto market x capture inside a neg-risk event with >= 3 eligible members | neg-risk events about 2,489 a capture with about 8.5 / 6.0 members (CH240); the eligible-member distribution and the share of eligible rows in such events **unprobed** | fact 4 |
| CH271 | eligible market x capture whose k + 1 row is one-sided (label side); eligible market x capture with a one-sided slot in its last 12 (state side) | proposal rows arriving one-sided about 490 a day in scope (3,923 in 8 days, M1-J0); exits from the listing 24,071 a day all categories (CH167's map); the eligible-to-one-sided transition rate at k + 1 **unprobed** (the leaderboard holds it) | fact 1, 3; CH167 |
| CH272 | M1's proposal unit (one-shot) with the monitor's prints in (`t_k`, `t_exit`] | 185 units a day (M1-J0); prints >= $1,000 about 160 an hour all categories (pilot); prints inside proposal windows **unprobed** (planning 2-20 a day) | facts 3, 6 |
| CH273 | open, two-sided, unflagged sibling B of a proposed winner A in the same neg-risk group (one-shot per B) | winners 976 in 8 days in events of 2-5 (327) and 6+ (734) members (M1-J0 S3, S8); B rows about 976 x (members - 1), planning 5,000-6,000 in 8 days; two-sided share **unprobed** | fact 3 |
| CH274 | non-sports ex-crypto market at the first capture with the favoured side's ask >= 0.95, two-sided, no proposal, `end_date` > k + 24 h (one-shot) | resolutions at min(p, 1 - p) <= 0.05 at the last origin 21,516 in 12 days all categories (CH242); the non-sports ex-crypto crossings a day **unprobed** (planning 50-150) | round 19 fact 2 |
| CH275 | M1's proposal unit (one-shot) by the favoured side's insurance price `1 - bid_k`; target the sidecar dispute state within 12 slots | 185 units a day; `disputed_at_k` 1,597 rows in 84 captures (about 19 a capture); one-shot disputes a day and the insured class share **unprobed** (planning 1-3% and 3%) | fact 3 |
| CH276 | the field-semantics, surviving-side, adding-up, exit, flow, sibling, wait and dispute counts: counts only | a map; counts 0 until run | - |

---

## 1. Map: where money might be, given the pinned touch, the one-sided majority and the unmeasured wait

The cost model fixes the frame (hold-to-resolution and fee-free rows are the only regime under 1c; makers lose to
adverse selection in every tier but the largest); M1-J0 fixes the shape of the one hold-to-resolution route the programme
rates highest (a tick at the touch, a bid nobody has measured, three quarters of the population one-sided, 42% settled
before the clock says so, capacity unseen); the record fixes the odds (one verdict family in three registers). So this
round does not go back to the discount. It reads what the discount divides by (the wait), what funds it (the sellers into
the bid and the lottery bids on the losers), what the sidecar fails to flag (the siblings), and the two structural facts
the engine ignores (the adding-up constraint and the surviving side).

1. **A ladder's forecasts must add up, and the champion's do not.** In a neg-risk event the YES prices sum to one plus
   the overround; over two hours the members' mid changes sum to the overround's change, which is small. The champion
   forecasts each member from its own momentum and state, so when it says "up" for six members at once it is forecasting
   something the constraint forbids. Projecting its forecasts onto the constraint is the oldest result in hierarchical
   forecasting: every series gets better. The information is the deviation of a member's signal from its event's mean.
2. **A bid-only book is a firm price, not missing data.** Three quarters of the decided markets arrive at the proposal
   capture with one side gone; the engine labels them `unavailable` at k + 1 and never scores the champion on the moves
   that end in certainty, which are the largest moves there are and the ones every carry route lives on. A surviving bid
   above the old mid is an "up" that happened; the surviving ask below it is a "down". The same object, read at the
   origin, says which side of a market vanished last and when.
3. **The carry's denominator is time, and nobody has measured it.** A 3c discount on a market that settles tomorrow is
   not the same route as a 3c discount on one that settles in March, and M1-J0 says settlement is not the clock: 42% of
   proposals precede `end_date`. The wait from near-certainty to the proposal, by rule class, is the quantity that turns a
   discount into a yield, and the engine's `rules` family now classes 70% of non-sports markets.
4. **The decided side's bid is fed by impatient holders and lottery buyers, and both are already recorded.** The monitor
   stores every taker print of $1,000 or more with its side and price; a sell of the favoured side at 0.99 after the
   proposal is the fill a resting bid would have taken. The losers of a proposed ladder carry YES bids of a cent or two
   (CH47's lottery), which is exactly the NO carry's funding, on rows the sidecar never flags.
5. **The market prices its own dispute risk at the proposal, and the dispute is a sidecar state, not a resolution.** A
   bid under 0.99 on a proposed winner is insurance against the overturn; whether the insured markets are the ones that
   end in the `disputed` state is a one-shot test whose target the host writes every two hours.

| Family | What the host already dates that nobody has read | Money route |
|---|---|---|
| A. The engine's structure (CH270 `coh`, CH271 `edge`) | the champion's predictions on the other members of the same event; the surviving side of a one-sided row at k + 1 and in the market's own history | none claimed (forecast quality); the maker who skews member quotes by the event-coherent deviation stays event-neutral (gross, reported); the feed stops hiding "about to be decided" |
| B. M1's companions (CH272 the seller's flow, CH273 the losers' NO) | the monitor's prints inside (`t_k`, `t_exit`]; the YES bids of unflagged siblings at the winner's proposal capture | maker: a resting bid on the decided side, sized by the measured fill flow; taker, hold to resolution: buy the loser's NO at `1 - bid_YES` (fee at p 0.01 about 0.04c docs, 0 served) |
| C. The wait (CH274) | the first capture at which the favoured ask reaches 0.95; the first proposal or exit after it; the `rules` class at k | taker, hold to resolution: the favoured side of near-certain markets selected by expected wait (annualised gross `(1 - ask) / W`), reported against the fee at ask and a capital line |
| D. The dispute forecast (CH275) | the favoured side's `1 - bid_k` at the proposal capture; the sidecar `disputed` state within 12 slots | risk filter for the carry: skip insured proposals (the tail `r` concentrates there); the lottery buyer's side reported, never a verdict |
| E. The map (CH276) | counts only | decides the rest |

**Data labels.** `A` = on the host now (captures, sidecar, two sweeps, trade samples, the monitor, the poller's quotes,
the engine's `quotes/`, `features/`, `predictions/`, label logs, the four keyless streams, `reward_params`). `A~` = on the
host but a join or reader has to be written and counted first (the event join on predictions, the surviving-side reader,
the monitor-to-unit join, the sibling join, the 0.95 crossing reader, the dispute-state reader). `P` = a fetch is needed
(none here). **Sealed and not usable by anything here:** LT2's, LT3's, LT4's (E022's) stores, LT9's-LT14's once registered,
CB16's and CB17's stores, CB8-H's holders, E009 / E010's `cross_venue_live/` to 11-03, E011's `surprise_live/` to 11-10,
E025's and E026's stores and the E026 frozen modules (the monitor's **wallet hashes** are not read by anything here; CH272
reads print side, price, size and times only, and its window starts after E026's receipts end on 11-15). J4-R
`[2026-10-16, 2026-10-21)` and CB13-T's holdout `[2026-10-21, 2026-10-26)` are refused for every maker mark-out object;
nothing here is one.

**Windows and registration this round proposes.** Three lanes, registered separately, none reading another's objects.
- **The engine lane (CH270, CH271).** DESIGN_V1 notes before any column (section 37 for `coh`, a new section for the
  `quotes/` version and the `dir_2h_x` target); censuses committed before they run; no token found for either (checked
  against the embargo list of STATUS 10-30: `event` visible, `nrslack` under LT11 to 12-09, which is why `coh` sums
  predictions and not quotes).
- **The companion lane (CH272, CH273; rule 29).** Filed as **amendments to M1 before its design-text freeze** (deadline
  2026-11-22) if the `science-reviewer` accepts them as additional estimands on M1's units; else registered as separate
  measurements on the disjoint later window **2026-12-15..2027-01-04** with read-out on or after 2027-02-05. CH273 also
  needs CH276's semantics line first (0.0 cause 4).
- **The measurement lane (M3: CH274).** A registered measurement under rule 26 (k = 0) on a population no test or
  measurement owns (near-certain, unproposed, before `end_date`); window **2026-11-24..12-14** beside M1 and M2 (disjoint
  units: M1's are proposed, M2's are overdue, M3's are neither), read-out on or after 2027-01-29 (the last waits).
- **The one-shot lane (LT15 candidate re-used: CH275).** One Holm family k <= 1; the units are M1's object, so by the
  rule-26 ruling the window is **disjoint and later than M1's: 2026-12-15..2027-01-04**, analysis on or after 2027-01-06
  (before M1's read-out, so not `informed (M1)`); the census on the last 8 days of sidecars before the freeze; a 42-day
  extension declared at the census if the insured class is under 100.

## 2. Hypotheses

### A. The engine's structure (parents DESIGN_V1 sections 2, 3, 16, 37; the `event` family; CH184, CH159, CH238, CH259, CH233 for CH270; CH268, CH35, CH36, CH167, CH169, CH175 for CH271; literature: Hyndman, Ahmed, Athanasopoulos and Shang 2011 and Wickramasuriya, Athanasopoulos and Hyndman 2019 on coherent (reconciled) forecasts, Bates and Granger 1969 on combination, Glosten and Milgrom 1985 on the one-sided book as the maker's withdrawal)

**CH270. The adding-up constraint (`coh`): the champion forecasts each member of a neg-risk event alone, but the members'
2 h mid changes sum to the change in the event's overround, which is small and mean-reverting, so the part of a member's
signal shared across its event cannot be realised by all members and is mostly noise; the deviation of the member's
signal from its event's mean is the coherent part. A meta-family on the champion's own write-once predictions, joined by
`event_id`, improves `dir_2h` on ladder members, and the gain vanishes when the event join is shuffled.**
- Mechanism and why it is non-obvious. A complete set of mutually exclusive outcomes has prices that sum to one plus the
  overround; the overround's two-hour change is bounded by the makers' repricing, not by news. The champion's columns are
  the member's own momentum and state, so six members with the same displayed 1 d change get the same "up"; the
  hierarchical-forecasting result (Hyndman et al. 2011) is that projecting such base forecasts onto the constraint
  improves every series, and the projection for a sum-to-constant constraint is the within-event demeaning. The
  LightGBM `event` challengers (se8, se10) see the siblings' Gamma changes as inputs but never the champion's *forecasts*
  for the siblings, and no family demeans a prediction within its event. Who pays if it is true: the maker who re-centres
  every member on the common move (gross; the engine's quality gain is the yardstick, cents are LT14's and under
  `attrlimit_lt14`). Why the crowd misses it: the venue shows one market at a time; the engine scores one row at a time.
- Parent and what is new. The `event` family (DESIGN_V1 section 16: event size, overround, normalisation gap, own rank,
  largest sibling, siblings' Gamma changes), CH184 (a member's move split into the event's and its own part: a *move*
  decomposition), CH159 (ladder breadth of *moves*), CH238 (`nrslack`: headroom from *bids*, LT11's token), CH259 (`disp`:
  disagreement across *models* on the same row), CH233. New: the **reconciliation of the engine's own predictions** under
  the adding-up constraint (rule 30), the **deviation from the event mean** as the column, the **sums of P(up) and P(down)
  across members** as the incoherence measure, and the **shuffled-join placebo**.
- Data join and decision clock (`A~`, L 4: `predictions/<capture>/se0_champion_lr_mm.parquet` at the same capture k, read
  after the champion's file is written and before the challenger's, under section 37's rule; `features/<capture>.parquet`
  for `event_id` and `ms_neg_risk`; the sidecar's `neg_risk_market_id` for the exclusive group where an event mixes
  groups). Unit: eligible market x capture whose event has >= 3 eligible members at k (fewer: columns `NaN`, counted;
  two-member events are LT12's `mirror` object and are excluded by construction until 2027-01-03). Columns (aux `coh`):
  `co_n` (eligible members at k), `co_mean_s2h` (the event mean of `s_2h = P(up) - P(down)` over the *other* members),
  `co_dev_s2h` (own `s_2h` minus the event mean over all members), `co_rank_s2h` (own rank of `s_2h` in the event, scaled
  to [0, 1]), `co_sum_pup`, `co_sum_pdn` (sums of P(up) and P(down) over members: the incoherence), `co_sd_s2h`
  (within-event SD of `s_2h`), and the same four for `s_6h` and `s_24h`; **no sum of quotes** (the overround level is the
  `event` family's; its 2 h innovation is held back until LT11's analysis). Decision time: the champion file's `written_utc`
  for capture k, which precedes the challenger's write by construction.
- Scored on. `dir_2h` (primary), `dir_6h`, `dir_24h` against se1 and the champion, event-clustered, market-deduplicated,
  and **on ladder members only** as the declared sub-panel (the family is `NaN` elsewhere, so the isolate's gain on the
  whole panel is diluted and is printed beside the sub-panel's). Isolate `se29_lr_coh` (the champion's logistic learner +
  `coh`) and a LightGBM version on se1's parameters. **Placebo (declared):** the same columns computed after permuting
  `event_id` within the capture among neg-risk rows with the event-size distribution preserved must add less than a tenth
  of the real columns' gain. Diagnostic (printed, not a score): the realised sum of members' `dmid` per event against the
  champion's `co_sum_pup - co_sum_pdn`.
- Killed at its census (counts only, definitions committed first). The share of eligible non-sports ex-crypto rows in
  neg-risk events with `co_n >= 3` under 10%; within-event SD of the champion's `s_2h` under 0.02 on its median event
  (nothing to demean); |corr(`co_dev_s2h`, `s_2h`)| > 0.95 (the deviation is the signal under another name); or no gain
  over se1 on `dir_2h` for ladder members at 28 days with the CI excluding zero. Light: two parquet files a capture, a
  group-by on `event_id`; < 300 MB; no capture read.
- Embargo and tokens. `event` is visible (withdrawn 10-22); `nrslack`, `dollarw`, `bandside` (LT11, to 12-09) are
  bid-sum, dollar-weight and band objects and no column here reads a quote; `mirror` / `mixedlad` (LT12) own two-member
  events, excluded; `attrlimit_lt14` concerns `P`'s cents by tier, not computed. The section 37 meta-family note is
  required before the first column (rule 27 / 30).
- Population arithmetic. Neg-risk events about 2,489 a capture non-sports ex-crypto with about 8.5 / 6.0 members
  (CH240); if a third of members are eligible at a capture the family covers about 5,000-7,000 of the 18,232-18,349
  eligible non-sports ex-crypto rows (planning; the census counts).
- Most likely boring explanation. The champion's `s_2h` barely varies within an event (its inputs are nearly common to
  members), so `co_dev_s2h` is a few hundredths and adds nothing; or the LightGBM `event` challenger already captures the
  constraint through the siblings' changes and the isolate's gain over se10 is zero.
- Sports arm: the same columns on sports game ladders (the densest neg-risk events), uncounted (the owner's parameter).
- Scores: N 4, EV 3, L 4. Priors: **P(census) 0.6; P(beats se1 on ladder members at 28 days) 0.35.** Parents: the `event`
  family, CH184, CH159, CH238, CH259, CH233. New: reconciliation of the engine's own predictions, the deviation column, the
  prediction sums, the shuffled-join placebo.

**CH271. The surviving side (`edge`): a one-sided book is a firm price, and the engine discards it twice: at the label,
where a market that is bid-only at k + 1 is `unavailable` although its surviving bid above the old mid is an "up" that
has happened, so the champion is never scored on the moves that end in certainty; and at the origin, where the market's
own history of losing one side (which side, how often, how long ago, how far the mid jumped when the book re-formed) is
a state no family reads because `quotes/` stores no price for a one-sided row. The claim is that a sign-completed label
`dir_2h_x` changes the champion's measured calibration at the extremes of |s|, and that the signed vacuum history moves
`dir_2h` log-loss on the markets that have one.**
- Mechanism and why it is non-obvious. Glosten and Milgrom's maker withdraws the side the informed will hit; on this
  venue the decided side's ask vanishes at or before the proposal (M1-J0: 76% of in-scope proposal rows arrive one-sided).
  The engine's three-class label needs a mid at k + 1, so exactly the rows whose move was largest are dropped, and the
  dropped rows are not missing at random: they are the up-moves of favourites and the down-moves of longshots. A bid at
  `p` bounds the mid at k + 1 from below with no imputation (rule 28). The same store, read backwards, says which markets
  lose a side regularly (one intermittent quoter), which lost it once and came back a tick away (a heartbeat lapse, CH36)
  and which lost it and came back ten cents away (information). Who pays: the maker whose quote survives a one-sided
  interval on the wrong side; the taker who reads the feed's strength on a market whose other side is gone. Why the
  crowd misses it: a one-sided market shows no mid on any surface, including this programme's.
- Parent and what is new. CH268 (`fragile`: the slot-level `unavailable` share; the builder's own note that a market-level
  version "needs a new population: quotes/ history whether or not a features row exists" and is idea only), CH35 (the
  vacuum's re-quote level), CH36 (synchronised outages), CH167 (the exit map), CH169 (one-sided *moves* of a two-sided
  book), CH175 (the last-mid proxy), DESIGN_V1 section 2's label states. New: **the surviving side as a firm bound used as
  a label** (`dir_2h_x`), **the `quotes/` version that keeps the surviving price** for `st = 3` rows, and **the signed
  vacuum history** (`ox_*`) as a family computed without a features row for the past slots.
- Data join and decision clock (`A~`, L 3). (a) **Store:** `quotes/` v2 keeps `bid` or `ask` for `st = 3` rows (the other
  `NaN`) and a `side` code; additive, a new version string, old files unchanged (write-once); within the 8-day snapshot
  retention the labeller already reads the k + 1 capture, so the label needs no restore. (b) **Label `dir_2h_x`** (a
  target *version* scored beside `dir_2h`; the promotion rule is not touched): for a unit eligible at k whose k + 1 row is
  open and one-sided, up if the surviving bid >= `mid_k + 0.005`, down if the surviving ask <= `mid_k - 0.005`, else
  `unavailable_one_sided` as now; `unavailable_absent` (left the listing) stays unavailable (its sign would need a
  resolution, which is `res_7d`'s business). (c) **Family `ox`** (origin side, from `quotes/` v2's `st` and surviving
  side over slots k - 84..k): `ox_1s_12` (one-sided slots among the last 12), `ox_1s_84` (among the last 84), `ox_last_side`
  (+1 the bid survived, -1 the ask survived, 0 none), `ox_since` (slots since the last one-sided slot, capped), `ox_reform_d`
  (the first two-sided mid after the last vacuum minus the last two-sided mid before it, signed; `NaN` if none),
  `ox_absent_12` (slots absent from the listing then back). The unit is two-sided at k (eligible); only its history reads
  `st`. Decision time: the quotes files' receipts at or before k.
- Scored on. (b) the champion's and se1's `dir_2h_x` log-loss and calibration by |s| decile beside `dir_2h`'s, on the
  same rows (the difference is the censoring's effect; printed, never a promotion input until a declared rule says so).
  (c) `dir_2h` against se1 on rows with `ox_1s_84 > 0` (the declared sub-panel) and on the whole panel; isolate
  `se30_lgbm_ox`. Placebo for (c): the same columns from the market's own slots shifted back by 84 (a stale history must
  add nothing).
- Killed at its census (definitions committed first; counts only). (b) fewer than 1% of eligible rows have a
  sign-determinable one-sided k + 1 state over 7 days (then the label change is cosmetic and (b) is dropped; the store
  version may still be built for (c)); (c) `ox_1s_84 > 0` on fewer than 2% of eligible non-sports ex-crypto rows, or
  |corr(`ox_1s_84`, `ms_log_liq`)| > 0.8 (illiquidity under another name).
- Population arithmetic. Proposal rows arriving one-sided about 490 a day in scope (M1-J0); exits 24,071 a day all
  categories (CH167); the eligible-at-k, one-sided-at-k + 1 rate is published daily by the leaderboard and is **unprobed**
  here (planning 0.5-2% of 18,000 eligible non-sports ex-crypto rows a capture: 90-360 a capture, 1,100-4,300 a day).
- Confounders and how each is held. A one-sided row from a quoter outage, not information (the sign test requires the
  surviving side to be beyond `delta` of the old mid, and `ox_reform_d` separates the tick-away return from the jump);
  `attrlimit_lt14` (nothing here is cents by tier; `dir_2h_x` is log-loss); the fine-clock and spread tokens (no spread
  object; `st` is a status code).
- Most likely boring explanation. The sign-determinable one-sided rows are 0.3% of eligible rows and almost all at mids
  above 0.9 that the champion already calls up; the calibration curve moves in its last decile and nowhere else; the
  vacuum history is a liquidity proxy.
- Challenger feature: the family itself; the store version and the label are DESIGN_V1 notes for the builder (a new
  section, committed before the census).
- Sports arm: uncounted (game markets go one-sided at the final whistle; the densest version of (b)).
- Scores: N 3, EV 3, L 3. Priors: **P(census (b)) 0.55; P(census (c)) 0.45; P(beats se1 on the sub-panel) 0.3.** Parents:
  CH268, CH35, CH36, CH167, CH169, CH175. New: the firm-bound label, the store version, the signed vacuum history.

### B. M1's companions (parents CH263 / M1, CH216, CH47, CH68, CH144, CH171, CH77 for CH272; CH221, CH47, CH263 / M1, CH67, CH11, CH09 for CH273; literature: Duffie 2010 on slow-moving capital, Grossman and Miller 1988 on the price of immediacy paid by the impatient side, Thaler and Ziemba 1988 on lottery demand at long odds)

**CH272. The impatient seller: the bid side of the proposal window is fed by holders who sell the decided side under
1.00 rather than wait, the live trade monitor already records every such sale of $1,000 or more with its side and
price, and the fill flow available to a resting bid in the two hours after a proposal is a measurable capacity that no
touch size can give. A companion measurement to M1 (rule 29): dollars sold into bids per proposal unit, at what discount,
in how many units, and whether the units with impatient sellers before the proposal are the ones with impatient sellers
after it.**
- Mechanism and why it is non-obvious. M1-J0 says the ask is pinned at 0.999 on 97% of units and the sweep sees 9 of
  1,232 touches, so the taker version of the carry is a tick with unknown size and the route, if it exists, is the resting
  bid (M1's estimand 6, gross, "no fill is measured"). Grossman and Miller's price of immediacy is paid by whoever cannot
  wait: a holder recycling collateral into the next market (CH68) sells the winner at 0.99 into the bid. The monitor has
  stored every taker print of at least $1,000 since 10-12 with receipt time, venue time, market, side, outcome, size and
  price; the join to M1's units is a market id and a time interval. Who pays: the impatient holder (the fill is his
  discount); who collects: the resting bid, which is why its capacity is the number that decides whether the carry is a
  hobby or a business. Why the crowd misses it: the proposal window is two hours long and the market is already in the
  "ended" list.
- Parent and what is new. CH263 / M1 (the carry; its capacity line is the ask size on the covered 0.73%), CH216 (the
  monitor as a universe-wide print stream; an engine input, never a unit), CH47 (the lottery on the other side), CH68
  (redeployment after redemption), CH144 and CH171 (closing prints carry liquidity), CH77 (where the fills are). New: the
  **bid-side fill flow as the capacity estimand**, the **monitor as the capacity stream for a one-shot unit** (prints are
  measured quantities on the proposal unit, not units), the **pre-proposal impatience split** (the same flow in the 24 h
  before k, k-visible), and the **discount-at-sale distribution** (how far under 1.00 the impatient actually sell).
- Data join and decision clock (`A~`, L 3). Streams: M1's unit list for the window (unit, `t_k`, favoured side, `bid_k`,
  `ask_k`, `t_exit` = the start of the first capture after k at which the market is absent from the open listing or
  closed; inherited by sha256 under rule 29), and the monitor's day files `live_trades/trades-YYYYMMDD.jsonl` (print side,
  outcome, price, size, venue time, receipt time; **no wallet field is read**). Fill flow for a resting bid on the favoured
  side: a taker **sell** of the favoured outcome at price `p_s`, or a taker **buy** of the other outcome at `q` (which the
  CLOB matches against the favoured side's bids; recorded as a sale of the favoured side at `1 - q`), with venue time in
  (`t_k`, `t_exit`]; the mapping from the monitor's `side` / `outcome` fields is pinned before the census from the monitor's
  own docstring (complementary matching mapped to outcome 0, as the cost model's calibration used it). Decision time
  `t_k` (M1's); everything after it is the estimand (a capacity, read after the window, under rule 26). The pre-k window is
  [`t_k` - 24 h, `t_k`).
- Estimands (declared; no verdict). (1) `F_post` = notional of fill flow per unit in (`t_k`, `t_exit`] (USDC; 0 where
  none), mean, median, p90 and the sum per UTC day; (2) `N_post` = the count of such prints per unit; (3) `S_post` = the
  share of units with `N_post >= 1` (Wilson CI); (4) the discount at sale `1 - p_s` per print (the price the impatient
  accept), its quantiles, and the share at or under `bid_k` (sold into the standing bid) against above it (a better bid
  arrived); (5) the same four for the pre-k 24 h (`F_pre`, `N_pre`, `S_pre`); (6) the k-visible split of (1)-(3) by
  `N_pre >= 1` against `N_pre = 0` (impatience persists, or it does not), with event-bootstrap CIs; (7) splits by tier,
  ladder position, side, fee class and `end_date` relation (M1's S1, S3, S5, S4, S7); (8) the dollars a resting bid at
  `bid_k` would have filled per day summed over units, printed as a number of dollars, which is the capacity line.
- Paper rule and economic check (rule 11: maker, hold to resolution). Rest a bid at `bid_k` (or one tick above) on the
  favoured side at `t_k`; the fill is estimand (1) at the sale prices of (4); the gross per filled share is `1 - p_s`; the
  fee is none (makers are never charged); the capital line is M1's wait at 5% a year; the tail is M1's `r_eff` (not
  re-measured here; never pooled). Nothing is a verdict; the ledger line is "measured: F_post, N_post, S_post, the sale
  discount, F_pre, the split, capacity in dollars a day".
- Population arithmetic. Units 185 a day (M1-J0), 3,885 in 21 days; prints >= $1,000 about 160 an hour universe-wide
  (the pilot), so about 3,800 a day across all categories, of which the share landing in a non-sports ex-crypto market
  during its two-hour proposal window is **unprobed** (planning 2-20 a day, so 40-400 units with a print in 21 days).
  Precision: `S_post` at 3,885 units is known to +-1 point; the mean `F_post` on 100 units with a print to about +-30% of
  itself. **The kill is precision:** fewer than 100 units with `N_post >= 1` in the window makes (1), (4) and (6) coarse
  and the measurement reports `S_post` and the daily dollar sum only; a monitor cycle-gap share above 10% of the window's
  proposal intervals makes the whole read coarse (gaps are counted from the monitor's own cycle lines, never filled).
- Permutation and cluster structure. None (k = 0). Event bootstrap for every CI. Declared readings for the reader's size
  check (rule 26): **S56: the $1,000 floor** (every print under it is invisible, so every flow number is a lower bound;
  said in the headline); **S57: the cycle lag** (a print's receipt can trail its venue time by up to 300 s plus the 120 s
  watermark, so the window is cut on venue time and a print with venue time before `t_k` is pre-k even if received
  after); **S58: a sale that is a hedge, not impatience** (a cross-market position closing; indistinguishable here and
  not claimed otherwise).
- Confounders and how each is held. The monitor's enrichment budget (50 markets a cycle) affects scores, not the stored
  print line; the E026 window (receipts 10-25..11-15; no overlap with M1's 11-24..12-14 and no wallet hash read);
  survivorship (M1's units only; the one-sided three quarters are outside M1 and are CH271's and the map's); the fee step
  (no fee enters a maker line).
- Most likely boring explanation. Nine units in ten see no print of $1,000 or more in their two hours; the impatient
  sellers are small, the daily capacity for a resting bid at the $1,000 grain is a few hundred dollars across the whole
  non-sports ex-crypto population, and the route is a hobby. That is the answer the owner's capacity question needs.
- Cheapest census (counts only; the last 7 days of the monitor's day files on the host against the last 8 days of
  sidecars; no price read beyond the monitor's own print prices, which are not a target). Units a day with any print in
  (`t_k`, `t_exit`]; prints a day in scope; the monitor's cycle gaps; the pre-k 24 h counts; the side / outcome field
  forms seen (the mapping's pin).
- Route to registration (rule 29). An amendment to `MEASUREMENT_M1_CH263.md` section 5.3 (capacity) filed before M1's
  freeze (deadline 11-22) if the `science-reviewer` accepts the monitor as a second capacity stream on M1's units; else a
  separate measurement on 2026-12-15..2027-01-04 (disjoint, later), read-out on or after 2027-02-05.
- Challenger feature: **none** (proposed rows are ineligible; the monitor is already an engine input class under rule 1
  and nothing here changes that).
- Sports arm: uncounted (game markets are the bulk of the monitor's prints; the owner's parameter).
- Scores: N 3, EV 3, L 3. Priors: **P(census: >= 5 units a day with a print) 0.5; P(the share with a print holds within
  +-5 points on a second window) 0.6.** Parents: CH263 / M1, CH216, CH47, CH68, CH144, CH171, CH77. New: the bid-side fill
  flow as capacity, the monitor on a one-shot unit, the pre-proposal impatience split, the sale-discount distribution.

**CH273. The losers' NO: when member A of a mutually exclusive neg-risk event is proposed as the winner, every other
member B is decided NO at the same moment, yet B's own sidecar row carries no proposal (M1-J0: 976 winners against 85
losers flagged at the same capture), B stays eligible in the engine while its YES mid is above 0.02, and B's NO is for
sale at `1 - bid_YES(B)`, where the YES bid is the lottery demand of CH47. The claim, as a measurement: the loser's NO
carry `c_B = bid_YES(B)` is larger than the winner's pinned tick, is funded by bids that are larger in big ladders and on
the members ranked second and third before the proposal, reverses less often than the winner's proposal does, and is
available on five to six units for every winner.**
- Mechanism and why it is non-obvious. A neg-risk event pays exactly one YES; a proposal on A is a proposal of NO on every
  B, but the venue's resolution record is per market, so B's status stays empty until B is proposed or closed in its own
  right. The holder of B's YES who wants a cent back and the lottery buyer who hopes for a dispute meet at B's YES bid; the
  carry buyer who lifts B's NO at `1 - bid_YES(B)` is matched against that bid (complementary matching), so the lottery
  demand *is* the carry's capacity. M1 measures the winner's tick; nobody has measured the losers' cents, and the engine,
  blind to the sibling's proposal, keeps scoring B as if undecided. Who pays: the lottery buyer and the impatient loser;
  who collects: the NO buyer at a cent or two with a one-capture wait. Why the crowd misses it: five decided markets with
  an empty status field look exactly like five undecided ones.
- Parent and what is new. CH221 (the siblings' proposal window: the sidecar field on every member; a verdict-shaped
  idea on the siblings' prices), CH47 (the lottery as a trade from the buyer's side), CH263 / M1 (the winner's carry and
  the extractor), CH67 (the unwind after a member flips `closed`), CH11 (the augmented "Other" member's mechanics), CH09.
  New: **the loser as the one-shot unit**, the **measurement role** (rule 26) with the lottery bid as the carry's funding
  and capacity, the **mutual-exclusivity restriction** (neg-risk groups only; cumulative "by date" ladders have the
  opposite sign and are a counted class, never pooled), the **engine-exposure count** (decided-but-scored rows), and the
  **counts from M1-J0** that bound the population.
- Data join and decision clock (`A~`, L 4). At capture k where A first shows a proposal state with its YES at >= 0.90 (M1's
  unit; A's `neg_risk_market_id` non-null), every other market B with the same `neg_risk_market_id` that is open,
  two-sided at k, with no proposal state of its own and no proposal at k - 1; one unit per B at its first such k. Fields:
  B's `best_bid`, `best_ask` at k and k - 1, B's rank by mid at k - 1 within the group, the group's size, B's `end_date`,
  tier, fee fields, the `event_neg_risk_augmented` flag (the "Other" member is a counted class), and at read-out the
  engine's resolution logs for B's payoff. Decision time: the latest receipt of A's and B's rows and sidecar at k. Cluster:
  the event (every B of one proposal is one cluster; declared weights as M1's R1 MUST 3, never a cap).
- Estimands (declared; no verdict). (1) `c_B` = `bid_YES(B)` at k (the NO's discount under 1.00), mean, quantiles and the
  share at 0 (`no_bid`: B's book is ask-only, a counted class outside the two-sided unit), by group size, B's pre-proposal
  rank, tier, fee class and whether B's bid moved between k - 1 and k (a bid that did not move is a stale resting order,
  a split); (2) `E_B` = the share of B units that are eligible in the engine at k (YES mid in [0.02, 0.98], two-sided, no
  own proposal): the decided-but-scored count, printed for the builder; (3) the wait: hours from `t_k` to B's own proposal
  or absence from the listing (right-censored); (4) after the window: `r_B` = the share of B resolving YES or split
  (`split_50_50` as 0.5), bounded at event level as M1's T_U; (5) `net_B = c_B - r_B (1 + c_B) - fee - capital`, with the
  fee at the NO price `1 - c_B` (`rate x c_B (1 - c_B)`: 0.04c at the docs rate for `c_B` 0.01, 0 served) and the capital
  line at 5% a year over the wait; (6) capacity: sweep-1 `bid_size_1` on B's YES where covered (coverage printed; the
  sweep frame does not select proposed events, so low coverage is expected and said).
- Paper rule and economic check (rule 11: taker, hold to resolution, one leg). Lift B's NO at `1 - c_B` at `t_k`, hold to
  B's close; the net per share is estimand (5); the capital turn is estimand (3). Nothing is a verdict.
- Population arithmetic. Winners 976 in 8 days in events of 2-5 members (327 units) and 6+ (734) (M1-J0 S3, S8); B rows
  about 976 x (members - 1), planning **5,000-6,000 in 8 days, 13,000-15,000 in 21 days**, before the two-sided filter,
  whose share is **unprobed** (a dead ticket's book is often ask-only). At 2,000 two-sided units and SD 0.5c, `SE(c_B)` is
  0.01c; the event-level reversal bound at 0 observed in 300 events is about 1%. **The kill is precision:** fewer than 500
  two-sided B units in the census span (8 days) makes the read coarse (extend to 42 days, declared).
- Permutation and cluster structure. None (k = 0); event bootstrap. Declared readings: **S59: an event-level status
  field** (if `uma_resolution_statuses` on B's row already carries A's proposal, B is in M1's `already_proposed` /
  `contested` funnel, the population is M1's, and this entry collapses to an M1 split by ladder position: the map's first
  line decides before any design text); **S60: the stale bid** (a YES bid resting since before the decision is not lottery
  demand: the moved / unmoved split); **S61: the wrong winner** (A's proposal is overturned and some B wins: that is `r_B`,
  the payoff, read after the window and bounded at event level).
- Confounders and how each is held. Cumulative ladders (not neg-risk; excluded by the group key, counted as
  `non_exclusive`); augmented events (the "Other" member counted apart, CH11); crypto (parameter; dailies resolve by
  Chainlink without this structure); sports (parameter); the fee step (both cost lines); M1's own window (disjoint
  units: A is M1's, B is not; rule 29's amendment route keeps one decision time).
- Most likely boring explanation. `c_B` is 0.1-0.5c (the lottery bids one to five ticks of the zone), the wait is one
  capture, the net is a tenth of a cent on a one-day turn and the capacity is the lottery buyers' size, tens of dollars a
  unit; or most B books are ask-only and the two-sided population is a few hundred.
- Cheapest census (counts only; the last 8 days of sidecars and rows). B units a day by group size and two-sidedness;
  the `no_bid` share; `E_B`; the moved / unmoved bid share; the field-semantics line (S59) from the status list's length
  against the group's size; the per-day distribution.
- Route to registration (rule 29). An amendment to M1 (a sibling block with its own estimands, one decision time) before
  11-22 if accepted; else a separate measurement on 2026-12-15..2027-01-04, read-out on or after 2027-02-05.
- Challenger feature: **an eligibility note, not a column**: a `sib_proposed` flag (any member of the unit's neg-risk
  group with a proposal state at k) as a counted eligibility exclusion or a `res_7d` feature is the builder's call
  (CH221's engine form; disclosed as such; no token names it).
- Sports arm: uncounted (game ladders are the densest neg-risk events; the owner's parameter).
- Scores: N 3, EV 3, L 4. Priors: **P(census) 0.5; P(net_B > 0.1c holds on a second window) 0.5.** Parents: CH221, CH47,
  CH263 / M1, CH67, CH11, CH09. New: the loser unit, the measurement role, the exclusivity restriction, the engine-exposure
  count, the lottery bid as capacity.

### C. The wait (parents CH115, CH198, CH62, CH01, CH226, CH267 / the `rules` family, CH189 / M2; literature: Duffie 2010 on slow-moving capital, Garleanu and Pedersen 2011 on margin and the cost of carry, Merton 1973 on the time value of a claim with a known settlement date)

**CH274. The wait (M3): every carry route divides a discount by a time, and the time is unmeasured. A market whose
favoured side first reaches an ask of 0.95 settles when it is proposed, not when its `end_date` says (M1-J0: 42% of
proposals precede the end), and the wait from near-certainty to the proposal is set by the rule's class (a scheduled
publication waits to its minute, a barrier already hit is proposed within a day, a consensus rule waits for the
proposer's reading) and by the ladder. The claim, as a registered measurement: the median wait differs by an order of
magnitude across the `rules` classes at the same hours-to-end, the early-settlement share is concentrated in the barrier
class, and the annualised gross `(1 - ask_k) / W` is large exactly where the discount is small, so the route is capital
efficiency and not alpha.**
- Mechanism and why it is non-obvious. Duffie's slow capital earns its return per unit time; on this venue the time is
  not the clock on the card. The engine's `res_7d` eligibility uses `end_date` to decide whether a market can resolve
  within seven days, so an early proposal is never in its population; M2 measures the proposal hazard only for markets
  already past their end; M1 measures the wait only after the proposal. Nobody has measured how long a decided market
  waits to be proposed, by what class, and what that does to a discount. Who pays: the holder who sells a 0.95 on a
  barrier market "because it won't resolve for months" the day it is hit; who collects: the buyer who knows the class.
  Why the crowd misses it: the card shows a date, not a resolution mechanism.
- Parent and what is new. CH115 (capital lock-up at zero interest: horizon-dependent staleness, as a mispricing
  argument), CH198 (calendar theta), CH62 (calendar-decided NO carry), CH01 (the decided carry), CH226 (the resolver's
  clock), CH267 and the `rules` family (the class, now a column with 0.70 non-sports coverage), CH189 / M2 (the hazard on
  the overdue population). New: **the wait as the estimand on the pre-proposal near-certain population**, the
  **early-settlement share by class**, the **annualised-gross framing** of every carry line, the **ask-path estimand** (does
  the discount collapse before the proposal), and the **`settle_24h` engine target** as the builder's arm.
- Data join and decision clock (`A~`, L 3: rows and sidecar at k for the touch, the proposal state and `end_date`; the
  engine's `rules` aux table at k for the class (`cl_sched`, `rc_occur_by`, the barrier lexicon, consensus; unclassed =
  `unavailable`, counted; the family's poll-finished clock binds); later captures for the proposal or absence; the
  engine's resolution logs at read-out for the payoff; sweep 1 for capacity where covered). Unit: non-sports ex-crypto
  market at the first capture k in the window at which the favoured side's ask is >= 0.95 (YES ask >= 0.95, or YES bid <=
  0.05 read as the NO ask >= 0.95), two-sided at k and k - 1 with the favoured ask < 0.95 at k - 1 (a crossing, not a
  level), no proposal state at k, `end_date` > k + 24 h, market age >= 12 slots (a market listed near certainty is CH56's
  seed object: counted class `born_certain`); one unit per market; a market already at >= 0.95 at the window's start is
  `pre_window`, counted, excluded. The 0.95 line is a declared population edge for a measurement (rule 15 governs
  crossing *states* in verdict tests; a measurement has no permutation null); most units then sit in rule 25's 0.001
  zone. Decision time: the latest receipt of the row, the sidecar and the rules table at k.
- Estimands (declared; no verdict). (1) `W` = hours from `t_k` to the first later capture that shows a proposal state on
  the market or its absence from the open listing, whichever first (right-censored at read-out; the absent class
  cross-checked against the engine's resolution log by closed day at read-out, counts only), median and quartiles,
  **by class x hours-to-end bin** (< 3 d, 3-14 d, 14-60 d, > 60 d), by tier, ladder position and fee class; (2) the early
  share: units proposed or absent before `end_date` - 2 h, by class; (3) the ask path: the share whose favoured ask
  reaches >= 0.99 before the proposal and the slots to it (the discount a patient buyer loses by waiting for
  certainty); (4) after the window: the share resolving against the favoured side or split, bounded at event level; (5)
  the annualised gross per unit `g = (1 - ask_k - fee(ask_k)) / W` in percent a year, as a distribution by class (served
  and docs fee lines; a capital line at 5% a year subtracted and printed), **never a mean across classes**; (6) capacity:
  `ask_size_1` at k where sweep 1 covers (coverage printed; expected low).
- Paper rule and economic check (rule 11: taker, hold to resolution). Lift the favoured ask at `ask_k`; hold to the
  proposal and settlement; the gross is `1 - ask_k` (3-5c by construction of the population; 0.1-4c in the zone), the fee
  at `ask_k` is 0.19c at 0.95 and 0.04c at 0.99 (docs rate 0.04; 0 served), the capital line is `W x 5% / 8,760 h`, and the
  yield is estimand (5). Nothing is a verdict; the ledger line is "measured: W by class, the early share, the ask path,
  the yield distribution, capacity".
- Population arithmetic. **Unprobed.** Bound: 21,516 resolutions at `min(p, 1 - p) <= 0.05` at the last origin in twelve
  days across all categories (the CH242 census); if 7-10% are non-sports ex-crypto, about 125-180 a day resolve from
  near-certainty, and the units that *crossed* 0.95 inside a window (not born there, not already there) are a subset:
  planning **50-150 a day, 1,000-3,000 units in 21 days**, classed 0.70. Precision: the median `W` on 300 units of a class
  is known to a few hours; the early share on 300 to +-5 points. **Kill (precision):** fewer than 25 crossings a day in
  the census (extend to 42 days, declared); classed share under 0.5 (the unclassed line becomes the headline and the
  class split a secondary).
- Permutation and cluster structure. None (k = 0); event bootstrap (members of one ladder cross together). Declared
  readings: **S62: the end is the wait** (the ask reaches 0.95 only in the market's last day, so `W` is hours-to-end
  under another name: the hours-to-end bins are the disclosure and the < 3 d bin is reported apart); **S63: the lagged
  flag** (the sidecar shows the proposal a capture after the on-chain proposal: `W` is long by up to 2 h, said); **S64:
  absent is not settled** (a market delisted without a proposal: the read-out cross-check against the resolution log; a
  counted class).
- Confounders and how each is held. The `rules` frame's selection (the stream polls the top 3,000 by volume hourly and
  the whole frame six-hourly, so classed markets are busier: the unclassed share by tier is printed and the class split
  reported within the covered frame, said so); crypto (excluded: the dailies cross 0.95 every hour and resolve by
  Chainlink; the owner's parameter would add thousands); sports (parameter); the fee step (both lines); LT15's object
  (the spread into the close by class) is not read: nothing here is a spread.
- Most likely boring explanation. `W` is bimodal and boring: the scheduled class waits to its minute (so `W` equals
  hours-to-end and the yield is the discount over the calendar), the barrier class is proposed within a day of crossing,
  and the yield is high only in units whose discount is a tick; the measurement then says that the carry's capital
  efficiency is a property of the rule class, which is still the first time anyone has written it down.
- Cheapest census (counts only; the last 8 days of rows and sidecars, the `rules` tables, no later state read beyond the
  proposal flag's presence as a count). Crossings a day by class, tier and hours-to-end bin; the `born_certain` and
  `pre_window` shares; the per-day distribution; the classed share; sweep-1 coverage.
- Challenger feature (the builder's arm): a target version **`settle_24h`** = the market shows a proposal state or is
  absent from the open listing within 12 slots, given eligibility at k, scored like the direction targets (log-loss,
  event-clustered), reading the sidecar and the listing only (no resolution); candidate inputs the `rules` columns,
  `ms_hours_to_end`, |mid - 0.5|, CH271's `ox_*`, CH273's `sib_proposed`. A DESIGN_V1 note before any label; its display
  is a separate owner question.
- Sports arm: uncounted (game markets cross 0.95 in the last minutes and settle within hours; the owner's parameter).
- Scores: N 3, EV 3, L 3. Priors: **P(census) 0.55; P(the class ordering of W holds on a second window) 0.6.** Parents:
  CH115, CH198, CH62, CH01, CH226, CH267 / `rules`, CH189 / M2. New: the wait as the estimand before the proposal, the early
  share by class, the annualised framing, the ask path, the `settle_24h` target.

### D. The dispute forecast (parents CH65, CH47, CH03, CH207, CH263 / M1; literature: Glosten and Milgrom 1985 on the bid as the maker's conditional expectation, Easley and O'Hara 1992 on the information in the absence of a trade, the venue's UMA documentation as CH47 and CH207 cite it)

**CH275. The insurance price: at the first capture that shows a proposal, the favoured side's bid sits one or two ticks
under its pinned ask on most units and whole cents under it on a few, and the gap `1 - bid_k` is what the market pays to
be rid of the overturn and the delay a dispute would bring; the insured units are the ones that end in the sidecar's
`disputed` state. A one-shot verdict test (rule 24) whose target is a sidecar state written within 12 slots, never a
resolution; its money is a filter on the carry (the tail `r` concentrates in the insured class) and its arithmetic is
binding at a 2% base rate, which the census can refuse.**
- Mechanism and why it is non-obvious. A proposal can be disputed inside its liveness by posting the bond (CH207's
  `umaBond`), after which the question goes to the DVM for days and carries the split tail (CH47, CH03). The bid on a
  proposed winner is the maker's conditional expectation of 1.00 minus the overturn risk, the delay cost and his
  immediacy premium (Glosten and Milgrom); at 0.999 it says "none of the three"; at 0.98 it says one of them is large.
  M1-J0 saw the ask pinned on 97% of units and a half-spread median of 0.0005, so the information, if any, is in the few
  percent of units whose bid is not pinned. If the bid is informative, the disputed share is higher where `1 - bid_k` is
  larger, and the carry buyer who skips those units removes most of his tail. Who pays: the carry buyer who does not
  look at the bid; who collects: the one who does, and the lottery buyer on the right side (reported, never a verdict).
  Why the crowd misses it: nobody reads the bid of a market that is "already decided".
- Parent and what is new. CH65 (an ex-ante dispute predictor from text, bond and specificity), CH47 (the lottery as a
  trade), CH03 (the disputed market's price against the upheld rate), CH207 (the bond as desk-set insurance), CH263 / M1
  (the units and the gross maker carry `1 - bid_k`, M1's estimand 6). New: the **market's own insurance price at the
  proposal capture as the state**, the **sidecar `disputed` state as the target** (a state the host writes every two
  hours, not a resolution: rule 19 is respected), the **one-shot unit with rule 24's between-event permutation**, the
  **pre-proposal twin** on the same market, and the **risk-filter reading** of a Supported verdict.
- Data join and decision clock (`A~`, L 4: rows and sidecar at k - 1, k and k + 1..k + 12). Unit: M1's eligible unit (the
  first capture k showing a proposal state, two-sided at k, favoured side >= 0.90; one per market). State: `ins_k = 1 -
  bid_k` of the favoured side (the loser side's ask). Classes, declared before the census with the zone's tick 0.001:
  `uninsured` (`ins_k <= 0.002`), `insured` (`ins_k > 0.010`), the middle a reported arm. Target `D`: the market shows a
  `disputed` status in the sidecar at any capture k + 1..k + 12 (present and disputed) = 1; absent from the open listing
  at k + 1 with no disputed state at any later capture in the 12 = 0 (settled; cross-checked at the analysis against the
  engine's resolution log by closed day, counts only, never a value); present without a dispute through k + 12 = 0 and
  class `lingering` (counted). Decision time: the latest receipt of row and sidecar at k. Census-fixed strata: category x
  tier x UTC day x ladder position (winner / standalone; losers proposed at the same capture are M1's `member_loser` and a
  reported arm). Cluster: the event (a ladder disputed as one; declared weights, larger events a reported arm), CR1 on
  event and two-way event x UTC day, p the largest.
- Target and horizon. Primary: the between-market class contrast of `D` (insured minus uninsured) inside the strata,
  one-sided > 0, with rule 24's permutation of the class label within strata as the gate. Secondary: the slope of `D` on
  `log(ins_k)` within strata. M1: on ladder units, the largest loser YES bid in the group at k as the alternative state
  (CH273's object; reported). M2: the favoured side's spread at k - 1 as a control (pre-proposal uncertainty). M3: the
  status list's history form (if the field is per market, a unit with prior cycles is a counted class `repeat`, excluded
  from the primary; if per event, the design is re-read before the freeze: the map's first line). **Twin (F, LT7's one
  rule):** the same contrast with `ins_{k-1}` (the pre-proposal gap on the same market) in place of `ins_k`; the primary
  must exceed the twin's contrast by the declared margin (planning `r_w` 0.2); a twin that matches the primary says the
  insurance is the book's standing width, not the proposal's information.
- Paper rule and economic check (rule 11, read as a filter). The route is M1's carry with the insured class skipped; its
  economic line is M1's net on uninsured against insured units, reported **after M1's read-out and never pooled**
  (`informed (M1)` only if CH275's analysis follows 2027-01-15; as proposed it precedes it). The lottery side (buy the
  loser's YES at `ins_k` in insured units) is reported gross, never a verdict.
- Population arithmetic (planning; the census counts). Units 185 a day (M1-J0), 3,885 in 21 days; the insured class
  share **unprobed** (M1-J0 S6 has 37 of 1,232 units with the *ask* off its pin; the bid is wider: planning 3-5%, so
  **120-190 insured units** in 21 days against about 3,000 uninsured); the base rate `b` **unprobed** (`disputed_at_k`
  1,597 rows in 84 captures, about 19 a capture; a dispute that lasts 48-96 h shows on 24-48 captures, so about 35-65
  disputed markets in 8 days against 1,232 proposals: planning **b about 0.02**, SD 0.14).
- Planning MDE (class contrast; SD 0.14; DE 1.1 at the formula; VIF 1.3; 31 printed beside and failing everything).
  Low (120 insured / 3,000 uninsured): `3.47 x 0.14 x sqrt(1/96 + 1/2,400) x sqrt(1.1) x 1.5 x sqrt(1.3)` = **9.1 points**;
  high (190): **7.3 points**; 42 days at the low rate (240): **5.7 points**; a quarter of the low count: fails. So the
  design detects a disputed share of about 11% in the insured class against 2% elsewhere at the low count, which is the
  size the mechanism itself implies (a 1c gap on a 0.1c carry prices a tail an order of magnitude larger than the
  base), and nothing smaller. F-MDE at `r_w` 0.2: 14 / 11.5 / 9 points (a verdict condition only where the census's
  computed `r_w` makes it under the primary's own MDE; else F is reported). **Kill lines:** insured units under 100 in the
  census's 8 days scaled to 21 (declare 42 days; under 50, withdraw pre-census); `b` under 1% in the census span (nothing
  is testable: withdraw pre-census); an event-level status field (re-read before the freeze; the design does not proceed
  on the per-market reading if the map says otherwise).
- Permutation and cluster structure. Rule 24's between-market permutation of the insurance class inside census-fixed
  strata (the null: given category, tier, day and ladder position, the proposal capture's bid gap does not predict the
  dispute state); CR1 on event; worlds **S65: a lagged dispute flag** (the dispute appears a capture late: inside the 12
  slots, harmless; after them, a counted miss); **S66: the stale bid** (a resting bid from before the decision: the
  `ins_{k-1}` twin and the bid-moved split); **S67: insured is illiquid** (wide bids in small books: the strata hold tier
  and the contrast must survive within tier; the liquidity-tier correlation gate binds); **S68: the disputed ladder** (one
  dispute flags every member: cluster = event, declared weights).
- Confounders and how each is held. M1's window (the units are M1's object, so the window is disjoint and later:
  2026-12-15..2027-01-04; nothing of M1's estimands is read); the fee step (no fee in a state or a target); the DVM's
  calendar (a dispute filed on a Friday is still a dispute; no time-of-day arm); sports and crypto (parameters; crypto
  has no UMA path).
- Most likely boring explanation. The insured class is the thin-book class (small ladders in the < 1k tier whose bids
  are always wide), the disputed share is 2% in both classes, and the twin matches the primary; or disputes are too rare
  to test at all and the census says so before a line of design is written.
- Cheapest census (counts only; the last 8 days of sidecars and rows; `informed (M1-J0)`-style zone counts of `1 -
  bid_k`, never a value). Units a day by insurance class (zone counts); disputed-state first appearances a day and their
  duration in captures; the `lingering` and absent-at-k + 1 shares; the status list's length against the group's size
  (the semantics line); the per-day distribution; the within-stratum against between-stratum SD of the class (rule 24's
  identification gate); MDE and F-MDE at the computed DE and `b`.
- Challenger feature: **none inside eligibility** (proposed rows are ineligible by DESIGN_V1 section 2); CH207's
  `umaparams` (bond, liveness) is the builder's next family and is not asked for here.
- Sports arm: uncounted (sports proposals persist for many captures, M1-J0's 18,703 `already_proposed` sports rows; a
  different object; the owner's parameter).
- Scores: N 3, EV 3, L 4. Priors: **P(census) 0.3; P(replicates | Supported) 0.45.** Parents: CH65, CH47, CH03, CH207,
  CH263 / M1. New: the market's insurance price as the state, the sidecar dispute state as the target, the one-shot unit,
  the pre-proposal twin, the filter reading.

### E. The map (parents CH269, CH261, CH251, CH270-CH275)

**CH276. The surviving-side census: one light reader (k = 0, counts only, < 500 MB, `net` lane) over the last 8 days of
rows and sidecars on the host, 45 days of `quotes/`, 35 days of `predictions/`, the engine's `features/` and `rules`
tables, and the monitor's day files on the host, printing every unprobed count above:** (1) **field semantics first:**
the length of the `uma_resolution_statuses` list against the market's neg-risk group size and against the number of
members with any status, and whether an unflagged sibling B's row carries A's proposal (decides CH273's population and
CH275's reading; 0.0 cause 4); (2) at one-sided proposal rows, which side survives (bid-only against ask-only) by
favoured side and tier (CH271, CH272); (3) neg-risk events a capture with >= 3 eligible members, the eligible rows in
them, and the within-event against between-event SD of the champion's `s_2h` (CH270; the champion's predictions are read
as counts of a distribution, no label); (4) eligible rows at k by their k + 1 state (labelled; one-sided with a
sign-determinable surviving side; one-sided indeterminate; absent; closed) by mid bin and hours-to-end, and the `ox_1s_84`
distribution (CH271); (5) monitor prints of $1,000 or more a day inside (`t_k`, `t_exit`] of proposal units and in their
pre-k 24 h, the monitor's cycle gaps, and the side / outcome forms seen (CH272); (6) B units a day by group size,
two-sidedness and `no_bid`, the moved / unmoved bid share, and `E_B` (CH273); (7) near-certain first crossings a day by
`rules` class, tier and hours-to-end bin, the `born_certain` and `pre_window` shares, and the share proposed before
`end_date` among those with a proposal in the span (CH274; a lagged count); (8) proposal units a day by insurance class
(zone counts of `1 - bid_k`, never a value), disputed-state first appearances a day and their duration in captures
(CH275); (9) **an ops line for the cost model's refresh (qcm1), not a test:** spread p50 by liquidity tier from `quotes/`
for 10-13..10-19 against 10-21..10-29 (one venue event, rule 22; a disclosure for `COST_MODEL.md`, never a route). It
decides: **CH270** is built if >= 10% of eligible non-sports ex-crypto rows sit in neg-risk events with `co_n >= 3` and the
within-event SD of `s_2h` is >= 0.02 on the median event; **CH271 (b)** if >= 1% of eligible rows have a sign-determinable
one-sided k + 1 state and **(c)** if `ox_1s_84 > 0` on >= 2%; **CH272** is filed as M1's amendment if >= 5 proposal units a
day carry a print in (`t_k`, `t_exit`], else as a share-only line; **CH273** is drafted if >= 25 two-sided B units a day
and the status field is per market; **CH274** if >= 30 crossings a day; **CH275** goes to its census if the insured class
is >= 100 in the 8 days scaled to 21 and disputes are >= 1% of proposal events. No table, token, column or label is
created by it; nothing it prints is a target.

---

## 3. Ranked shortlist: the companions, the engine's structure, the wait, then the dispute test

Rank = the chance the object exists at the count its design needs x originality x the money's shape (hold-to-resolution
or a resting bid, never a taker mid route) x how light the reader is, with rounds 14-19's rules and this round's 28-30 as
hard constraints. The last two columns are judgements.

| Rank | ID | One line | L | Population arithmetic (source) | Inference | Primary or estimand | Planning precision; F | P(census) / P(replicates) |
|---|---|---|---|---|---|---|---|---|
| 1 | CH273 | The losers' NO: the unflagged siblings of a proposed winner, decided NO, funded by the lottery bid, five to six units a winner | 4 | winners 976 in 8 days, members 2-5 / 6+ (M1-J0); B rows 13,000-15,000 in 21 days before the two-sided filter (derived) | a measurement (rule 26 / 29), k = 0; event bootstrap | `c_B`, `E_B`, the wait, `r_B`, `net_B`, capacity | `SE(c_B)` 0.01c at 2,000; the tail bound about 1% at 300 events | **0.5 / 0.5** |
| 2 | CH270 | The adding-up constraint: the champion's predictions demeaned within their neg-risk event, with a shuffled-join placebo | 4 | neg-risk events about 2,489 a capture, 8.5 / 6.0 members (CH240); eligible members unprobed | engine (28 days vs se1 on ladder members); shuffled join | `dir_2h` log-loss gain | engine window | 0.6 / 0.35 |
| 3 | CH274 | The wait: hours from the first 0.95 ask to the proposal, by rule class and hours-to-end; the early share; the yield distribution | 3 | 21,516 tail resolutions in 12 days all categories (CH242); crossings a day unprobed (planning 50-150) | a measurement, k = 0; event bootstrap | `W` by class, the early share, the ask path, `g` | median `W` to hours at 300 a class | 0.55 / 0.6 |
| 4 | CH272 | The impatient seller: dollars sold into the decided side's bid in the two hours after a proposal, from the monitor | 3 | 185 units a day (M1-J0); prints about 160 an hour all categories (pilot); in-window prints unprobed | a measurement (rule 29), k = 0 | `F_post`, `N_post`, `S_post`, the sale discount, the pre-k split | `S_post` +-1 point at 3,885; coarse under 100 units with a print | 0.5 / 0.6 |
| 5 | CH271 | The surviving side: a one-sided row as a firm bound (the `dir_2h_x` label, the `quotes/` version) and the signed vacuum history (`ox`) | 3 | about 490 one-sided proposal rows a day in scope (M1-J0); the k + 1 one-sided rate unprobed | engine; a map first | `dir_2h_x` calibration by |s| decile; `dir_2h` gain on the sub-panel | engine window | 0.55 (b) / 0.45 (c) / 0.3 |
| 6 | CH275 | The insurance price: `1 - bid_k` at the proposal capture against the sidecar `disputed` state within 12 slots, one unit per market | 4 | 185 units a day; insured class 3-5% (planning); `b` about 0.02 (planning from 1,597 disputed rows) | rule 24's between-market permutation; CR1 on event | insured - uninsured contrast on `D` > 0 | **9.1 / 7.3 points** (42 days 5.7); F 14 / 11.5 points | **0.3 / 0.45** |
| 7 | CH276 | The surviving-side census (counts only; decides the rest) | 5 | n/a | n/a | n/a | n/a | n/a |

**Top three, in one line each.**
1. **CH273, the losers' NO.** The cheapest new measurement in the programme: M1's extractor already finds the winner, the
   group key names the losers, M1-J0 already bounds the count at five to six units a winner, the fee at a cent is nothing
   under either rate, and the only thing that can stop it is a field whose semantics the map reads in one line.
2. **CH270, the adding-up constraint.** The one engine idea this round that is structural rather than another field: the
   champion forecasts members of one event as if they were independent, the constraint says they are not, and the
   reconciled deviation is computable from two parquet files a capture with a placebo that cannot be gamed.
3. **CH274, the wait.** Every carry entry since CH01 has quoted a discount and none has quoted the time it takes to
   collect it; with 42% of proposals arriving before the clock and the `rules` class now a column on 70% of non-sports
   markets, the denominator is finally readable, and the honest expectation is that it turns "carry" into "capital
   efficiency by rule class".

**The recommended first screen: CH276**, one job, counts only, `net` lane, `mem_mb` < 500, with the field-semantics line
first because two entries (CH273, CH275) change shape on it, then the surviving-side, adding-up, exit, flow, sibling,
wait and dispute counts, and the cost model's ops line. In parallel and at no census cost: the builder's DESIGN_V1
section 37 note for `coh` (rule 30) and the new-section note for the `quotes/` version and `dir_2h_x` (rule 28); the
rule-29 amendment texts for M1 (CH272, CH273) drafted for the `science-reviewer` before 11-22. **Expected number of
registered tests from this round: about 0.2** (CH275 0.3 x the challenger's acceptance of the disjoint later window and
the binary-target arithmetic, about 0.7), against the programme's record of about 0.4 a family; **expected registered
measurements, counted apart (the rule-26 ruling's condition 4): about 1.5** (CH273 0.5 + CH274 0.55 + CH272 0.5 as an
amendment or a separate measurement); **expected engine families built: about 1.1** (CH270 0.6 + CH271 0.5). The round's
value is in the measurements and the engine, not in the verdict count, and it says so.

**Two levers that are the owner's, stated once.** (1) **Sports** (200,104 of the proposal rows M1-J0 saw were sports, and
18,703 of them `already_proposed`: sports proposals persist across captures, a different object from the one-capture
non-sports proposal; the game ladders are the densest neg-risk events for CH270 and CH273 and the densest one-sided
transitions for CH271): one sports arm beside any of CH270, CH273 or CH274 would be the cheapest additional work in the
programme; the round keeps it uncounted because the owner has not decided. (2) **Crypto** (the hourly and daily series
cross 0.95 every hour and resolve by Chainlink without a UMA proposal): CH274's wait and CH275's dispute have no crypto
version by construction; CH270's ladders do (the strike ladders), and CH30, CH76, CH89 and CH249 own the crypto fair-value
objects, so the round keeps crypto out of every primary as the owner's parameter.

**How the families would be registered.**
- **CH272, CH273 (rule 29):** amendments to `MEASUREMENT_M1_CH263.md` filed before its freeze (11-22) with their own
  estimand blocks and M1's decision time, accepted or refused by the `science-reviewer`; else separate measurements under
  rule 26 on 2026-12-15..2027-01-04, read-out on or after 2027-02-05; counted apart from tests; never pooled with M1.
- **M3 (CH274):** a registered measurement under rule 26, k = 0, estimands and cost lines frozen before 2026-11-24, window
  11-24..12-14 beside M1 and M2 on disjoint units, read-out on or after 2027-01-29; the `settle_24h` target a DESIGN_V1
  note for the builder.
- **LT15 (CH275):** one Holm family, k <= 1, after CH276's semantics and count lines; census on the last 8 days of sidecars
  before the freeze (`informed (M1-J0)` for the zone counts); window 2026-12-15..2027-01-04 (disjoint from and later than
  M1's, as the rule-26 ruling requires), analysis on or after 2027-01-06; a 42-day extension declared at the census;
  no token (proposed rows are ineligible; nothing in the engine reads the bid gap at a proposal).
- **Engine-first (CH270, CH271):** `coh` after the section 37 note and its census; `quotes/` v2, `dir_2h_x` and `ox` after a
  new DESIGN_V1 section and the CH276 lines; isolates `se29_lr_coh` and `se30_lgbm_ox`; nothing enters the promotion rule
  without the declared procedure.

**What is honest to say about all of them.** M1-J0 took the discount away (a tick at the touch) and left four smaller
questions in its place: who sells into the bid, what the siblings cost, how long the money waits, and whether the bid
knows about the dispute. Each is a measurement or a filter, not a route; the two engine entries are about what the
champion ignores (its own forecasts on the next row of the same event; the side of the book that survived), not about
new information. The money in CH273 is a cent or two a share on a one-day turn funded by lottery buyers, if the losers'
books are two-sided at all; the money in CH274 is a yield number, not a mispricing; CH272 will most likely report that
the impatient sellers at the $1,000 grain are rare. Nothing here is edge until it has gone through the map, a census,
frozen rules, prospective registration and an economic check at recorded prices, and the record says that about two
thirds of verdict-shaped families register no test at all. The first thing that will say whether any of it is worth a
design is CH276's reading of whether the status field belongs to the market or to the event.

## 4. Ideas considered and rejected, and why

### 4.0 Dropped as duplicates or closed (this round's own candidates, each with the record that closes it)

| Candidate this round | Why dropped | The record |
|---|---|---|
| The dispute's price as a registered measurement (the disputed market's mid against the upheld share) | owned; low count | CH03 (the disputed-state trade), CH47, CH104; about 35-65 disputed markets in 8 days (planning from M1-J0); folded into CH275's census lines and CH276 (8) |
| The pre-proposal vacuum as a route (the ask vanishes before the proposal: buy what nobody sells) | owned; no ask to buy | CH04 (decision-to-close lag), CH35 (the vacuum's re-quote level), CH169; the surviving side is CH271's label and state, never a route |
| The bid-only discount at the proposal capture (M1's estimand 6 extended to one-sided rows) | an M1 amendment, not an idea | M1 excludes one-sided rows by design; the extension is a line in the rule-29 amendment text, not an entry |
| The fee step as a natural experiment (spreads, rebates, make / take after 10-20) | one event; unverified | q0717; rule 22; the right action is the cost model's refresh (qcm1), so CH276 (9) prints the before / after spread line as a disclosure |
| The sibling-proposed flag as an engine family | CH221's engine form | CH221; an eligibility note inside CH273 for the builder, not a family |
| The monotone-ladder envelope family (the mid against the CDF bounds of a cumulative "by date" ladder) | owned; null record | CH12 (dominance), CH06 (hazard residual), CH05; IF-H2-DEV (deadline ladders, development, null) |
| The engine's own term structure (`s_24h - s_2h` as a column) | the same inputs | DESIGN_V1 sections 3-4: every horizon's prediction is a function of the same features, so a learner already holds it; `disp` (CH259) owns cross-model disagreement |
| The label-horizon jitter (the row's receipt offset `t_off` at k and k + 1) | not a mechanism | a nuisance of the capture's pagination; CH236 and CH176 own display rank; no money route |
| A series base-rate family (the same series' earlier resolutions as a feature, rule 23) | owned | CH50, CH51, CH142; the `crypto` family's templates; a calibration claim, not a route |
| The monitor as a universe-wide flow family | owned | CH216; round 16 B; rule 1 (prints are inputs, never units); CH272 uses prints as a measured quantity on M1's unit only |
| The `gamma_rules` frame's hourly churn as an attention clock | owned | CH176 (the front page), CH236 (`volage`), CH157 |
| Election night at 1 min (CB15-E, 11-02..11-06) | one cluster | CH129, CH208, CH230; a case for `CASE_CATALOGUE.md` |
| Cross-venue objects on `xv_quotes/` after 11-03 | owned | LT10 (`kxbook`), CH222-CH224, CH241, CH134 (the Kalshi-settled carry) |
| The sportsbook board (`espn_odds`) | the owner's parameter | CH29, CH205, CH225, CH231, CH247 |
| The 0.95 crossing as a verdict test (the near-certain market's next move) | rule 15 | 0.95 is a programme constant, not a venue-published one; CH86 owns 0.96 and CH266 the display line; kept as a measurement's population edge only |
| The loser's lottery as a trade (buy the dead YES in insured units) | owned | CH47; reported gross inside CH275, never a verdict |
| Early settlement as a verdict test (will this market be proposed within 24 h) | a proposal as a target | the proposal is the resolution's proxy; kept as CH274's measurement and the `settle_24h` engine target, where the engine's targets may read a sidecar state |
| The pre-proposal sell flow as a predictor of M1's `c` | an M1 split | M1's splits are fixed at its freeze; CH272 carries the pre-k flow as a split of the post-k flow instead |
| A quote-mechanics family (the expected bounce from the last trade's side and the spread) | owned | CH196 (the last-print anchor), CH80 (dust), CH147, CH174; `market_state` holds last trade minus mid |
| Residual reversal of the champion (`rsrev`) | gate not met | DESIGN_V1 section 39: se1's own residual lag-1 -0.0021; the trees absorb it |
| Anything wallet-level; any manipulation route; any Kalshi change column; any band, pool, omission, twin, sibling-sum of quotes or batch innovation | sealed / owned | E026 (to 12-07), rounds 1-2, LT9-LT14's tokens |

### 4.1 Ideas rejected on the design rules, and why

- **Common states as live primaries** (rule 22): the fee step; a disclosure line in the map.
- **Resolution targets as verdict primaries** (rule 19): CH273's `r_B` and CH274's payoff are measurement lines read after
  the window; CH275's target is the sidecar's dispute state, not the resolution, and the dispute's outcome is reported.
- **Imputed mids on one-sided rows** (rule 28): none; CH271's label uses the surviving side only where it alone decides
  the class; CH273 reads a bid as a bid.
- **A second estimand on a measurement's units as a test on the same window** (rule 29): none; CH272 and CH273 are
  amendments or disjoint later measurements; CH275 runs on a disjoint later window.
- **Sums of quotes across members while a token on event sums holds** (rule 30): none; CH270 sums predictions, and the
  overround's innovation waits for LT11's analysis.
- **Level states as primaries**: the insurance class in CH275 is a one-shot state at a dated event (the proposal), tested
  between markets inside census-fixed strata with its pre-proposal twin; nothing here is a level on a panel.
- **Whole-panel mid class contrasts under about 700 units a capture**: none; no entry reads a mid as a verdict target.
- **Latent joins without a pin** (rule 21): none (the neg-risk group key and `event_id` are the venue's own).
- **Label-only F chosen for power**: none; CH275's F is a state twin on the same market.
- **Taker routes as primaries**: CH273's and CH274's are hold-to-resolution, one leg, measurements.
- **Maker mark-out objects**: none; CH272 measures fills a resting bid *would* have taken from recorded prints, declares
  no mark-out, and J4-R's and CB13-T's holdouts are not read.
- **Trade-sample or monitor units as primaries**: none; CH272's prints are quantities on a one-shot market unit.
- **Reading the unit's own outcome**: only under rule 26, after the window, as the declared payoff of a measurement.
- **CH01-CH269: not re-proposed**; where an idea touches one, the parent is named and the new unit, role, clock, join or
  store is stated (CH270 on the `event` family, CH184, CH159, CH238, CH259, CH233; CH271 on CH268, CH35, CH36, CH167, CH169,
  CH175; CH272 on CH263 / M1, CH216, CH47, CH68, CH144, CH171, CH77; CH273 on CH221, CH47, CH263 / M1, CH67, CH11, CH09; CH274 on
  CH115, CH198, CH62, CH01, CH226, CH267 / `rules`, CH189 / M2; CH275 on CH65, CH47, CH03, CH207, CH263 / M1; CH276 on CH269,
  CH261, CH251).

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
`EXPERIMENT_LEDGER.md` from "Creative round 19 recorded" (line 4794) to its end (the CH269 queue and result entries, the
rule-26 ruling, the LT13 freeze and amendment 13, the `resid` / `fragile` / `rsrev` engine entries, the `rules` family
entry, the M1 drafts, R1, re-check and J0 entries, the LT14 drafts, R1, freeze and census-code entries, the M2 drafts and
R1, the CB9-P empty-frame ruling, the disk-cap entry); `reviews/CH269_MAP_2026-10-30.md` (in full); `seals/M1_J0_q0731.json`
(summary keys only, by a bounded Python print: `decisions`, `eligible_units`, `funnel`, `funnel_by_category`,
`splits_counts` S1-S10, `sweep_1_coverage`, `status_forms` (forms and counts), `receipt_gaps_s`, `engine_resolution_candidates`,
`span`, `peak_rss_mb`, `version`; no price, size, c value, resolution, label or outcome exists in the file, by its own
`not_printed` line); `signal_engine/STATUS.md` (10-30 06:10 UTC+1, in full); `signal_engine/NORTH_STAR.md` (in full);
`signal_engine/CANDIDATES.md` (the round-19 note, the round-18 reply and the builder table rows 1-31); `signal_engine/DESIGN_V1.md`
(section headings; sections 2, 3 and 27 in full); `COST_MODEL.md` (in full); `NEW_STREAMS_2026-10-19.md` (in full);
`COLLECTION_HOST.md` (in full); `queue/README.md` (in full); `data_catalogue/README.md` (in full); `LIVE_TESTS_14.md` section 1.2
(stores read); `MEASUREMENT_M1_CH263.md` sections 3.1 and 13 and the section list; `MEASUREMENT_M2_CH264.md` (the section
list); `LIVE_TRADE_MONITOR.md` (the "What runs" field lines and the pilot table); `CROSS_VENUE_LIVE.md` (the section list and
the analysis commands); `lab_dashboard/registry.json` (the experiment and live-test ids and statuses);
`CREATIVE_HYPOTHESES_2026-11-02.md` (round 19 in full); the design-rule lines of rounds 14-18 (`-10-28.md` rules 1-11,
`-10-29.md` 12-14, `-10-30.md` 15-17, `-10-31.md` 18-20, `-11-01.md` 21-23) and the CH240 map fact of `-10-31.md`; the lead
sentences of CH01-CH269 from all nineteen rounds (one line each, used for the duplicates table and the parents named);
`backend/astrolabe/research_lab/ext_sidecar.py` (the sidecar's field map, by grep, for fact 8); the memory notes
`creative-hypotheses-lead`, `signal-engine-north-star` and `category-scope-undecided`. Still no host probe, no network and
no data-dumps read. Every count is as the named document states it on 2026-10-30; nothing was recomputed except the
planning MDEs and precisions from round 14's stated formula and the derived sibling and crossing counts (a multiplication
and a share, marked as planning only).

### 5.2 External literature (named, not fetched)
Hyndman, Ahmed, Athanasopoulos and Shang 2011 (optimal combination forecasts for hierarchical time series) and
Wickramasuriya, Athanasopoulos and Hyndman 2019 (trace-minimisation reconciliation): coherent forecasts under an
adding-up constraint; Bates and Granger 1969 (combining forecasts); Glosten and Milgrom 1985 (the quote as the maker's
conditional expectation and the withdrawal of a side); Easley and O'Hara 1992 (the information in no trade); Grossman
and Miller 1988 (the price of immediacy); Duffie 2010 (slow-moving capital); Garleanu and Pedersen 2011 (margin and the
cost of carry); Merton 1973 (the time value of a claim with a known settlement date); Thaler and Ziemba 1988 (lottery
demand at long odds); the venue's fee, rebate, liquidity-reward, tick-size and UMA documentation as `COST_MODEL.md`
section 2, CH47 and CH207 quote them, to be re-read at any pin.
