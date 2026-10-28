# Live tests 13 (LT13): the payer's return and the listing batch (CH252, CH253), DRAFT pre-registrations

**Status: DRAFT (second draft, 2026-10-28: challenger R1 GO_WITH_CHANGES applied, section 12), for the R1 re-check. Not
frozen, not registered; E-numbers unassigned; nothing counted, no LT13 code, no seal, no census run.** Drafted on branch
`feat/live-tests-13` from the `chore/arepo-claude-setup` tip `0d760612`, a design-only commit like the first commits of LT3-LT12.
LT13 takes the next free E-numbers at its own registration, in the order CH252, CH253 (round 18's rank order). If both tests drop
at their census or are withdrawn before it, LT13 is not registered (recorded in the ledger; nothing counted). Before registration
this needs, in order (R1 MUST 2 stages the build):
1. challenger R1 (`science-reviewer`), the designer's response (12), a re-check, the **q0717 fee-reading probe and its declared
   decision rule (1.4.3, 7.5; R1 MUST 3)**, and a final pre-freeze verification;
2. the **design-text freeze commit** (1.1), its sha256 recorded in the ledger, before the LT13 seal commit and, planned,
   before LT12's census job starts (`T_LT12c`, about 2026-11-18); the worlds of 1.8.1 are fully specified in the frozen text;
3. the **census code only** (6, with the seal and restore helpers it needs), with a `science-reviewer` code-freeze check of it
   against 1.4, 6 and 1.14 on synthetic data only; **no world, size-check or analysis code is written yet**;
4. the census inputs' restore and seal (6), each once, after the freeze and after the census span and its lag slots end;
5. the counts-only census (6), once, which fixes k and every census-fixed value named in 6;
6. **only for the tests that survive the census:** the world, size-check, gate and analysis code (7.1), a second code-freeze check
   that verifies it against the frozen text of 1.7-1.10 and 1.8.1 (the code follows the text; the text is not changed to fit the
   code), then the size check at 2,000 worlds on the code to be pinned (1.8), after the census values are committed;
7. a host dry run of the reader with peak RSS measured (7.2);
8. the embargo entries of section 8 verified in `config.EMBARGO` and `signal_engine/CANDIDATES.md`; `SPEC_SHA256` and
   `code_sha256` pins; the ledger entry (the registration commit) before `T_LT12` and at least 24 h before `REGISTERED_UTC`.
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from round 18, the CH261 or CH251 maps, the ledger or the cost model is a **counts-only operational or
development figure, never a target**. Every MDE is a **planning estimate** on stated assumptions. Nothing here read a price
after an origin, an outcome, a target, a prediction line, a census output or a P&L. No host, network, `ssh`, `data-dumps` or
evidence-JSON read was used to write it (reads listed in 9).

**The CH261 map and what it informed (declared up front).** `CH261_MAP_2026-10-28.md` (q0701, declared span [2026-10-13,
2026-10-28), **93 captures covered, 7.75 days**, 90 with a previous capture; counts only, k = 0, uncounted) read captures
k - 1 and k only: **no target, no price change after an origin, no resolution, no P&L.** It was read before this file was
written, so every gate near a map number is *informed by the map*; section 5 marks each design change made after it [map]
and 9.1 lists the values. The map's span is disjoint from LT13's census span [2026-11-07, 2026-11-17) (6), so every LT13 gate
is still declared before its own census. **The map applied none of LT13's filters** (no tight rule, the simple reward
reading `clob_rewards` non-empty at k instead of `listed_carry24h_v2`, no k + 1 availability, no tick-change rule, no support
cells), so its counts are upper bounds of the design's population before an unprobed retention factor (planning 0.5, 2.4).

**What the map says about LT13's odds (stated before any design line, and not softened below; R1 MUST 1).** On the map's own
numbers **CH252 fails three census lines that round 18 itself wrote, and CH253 fails one**:
- **CH252, three round-18 lines:** **(1) non-stationarity:** the fee-on unrewarded widening arm, the arm the contrast rests on,
  has a per-capture **median 15 and mean 139.3**: the median capture holds **0.108** of the mean, under round 18's declared kill
  (median < 25% of the mean). **(2) "fee-on >= 5x fee-free"** (round 18, `CREATIVE_HYPOTHESES_2026-11-01.md` l. 460): the map's
  ratio is about **0.008** at the median (15 / 1,857.5). **(3) cell-matched coverage:** read as the round wrote it (fee-free units in
  cells holding >= 20 fee-on units), **0.096** on the map's proxy against 0.60. Lines (2) and (3) are restated in section 5 items 1-2
  [map] (direction reversed, reasons given; R1 accepted item 2, with MUST 4); line (1) is kept unchanged and still fails. On LT13's
  own restated count line, the pre-filter mean (139.3) at the planning retention 0.5 gives **about 70 units a capture against the
  count gate of 77** (2.4).
- **CH253, one line:** the pseudo-batch placebo coverage measured **0.755** on the map's reading (same age decile over all
  eligible rows, created >= 7 days apart, **without** the same-category match rule 21 requires), against rule 21's census gate of
  **0.90**; the design's stricter rule-21 reading is **expected to lower** it (not proven: the tight rule changes both the decile
  base and the mate count m; R1 MUST 6). The gate is kept unchanged (10 item 4, R1 MUST 5).
**The map is not the census (R1).** Round 18 puts its 0.25 and 0.90 lines on the census (the worn LT12 seal or the ordered lane's
fresh seal); CH261 had no kill criteria (it is a map) and ran on 10-20..10-28 without the design's filters. Neither 0.108 nor 0.755
is a measured census line, so neither test is recorded `census_dropped` on the map. A withdrawal before the census on the map's
values is allowed (`AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md` l. 102, 128: stop low-value work) and is labelled
**`withdrawn_pre_census (map-informed)`** (or, for CH252 under 1.4.3's rule, `withdrawn_pre_census (fee reading unresolved)`),
never `census_dropped` or "died at line X". Unless the census span's populations differ from the map's, **LT13 is expected to
register no test**. R1 ruled **GO** (10 item 1) with the staged build (MUST 2) and the q0717 decision rule declared before it
runs (MUST 3, 1.4.3).

Source ideas: `CREATIVE_HYPOTHESES_2026-11-01.md` (round 18) section 3, ranks 1-2 and their sketches: **CH252** (the payer's
return) and **CH253** (the listing batch). Rank 3 (CH261) is the map. No third candidate: CH255 is out by the map (median 11
traded first-of-day flips a capture against the 690 line). Written to round 14's rules 1-11, round 15's 12-14, round 16's
15-17, round 17's 18-20 and round 18's 21-23, to LT4's lessons L1-L15 and the rulings LT7-LT12 carry (1.0). LT13 reuses LT12's
conventions (`LIVE_TESTS_12.md`, frozen at sha256 `a543db63…2d62d`) unless a line here says otherwise and why.

## 0. Summary

| Handle | Hypothesis (direction, one-sided) | Unit of analysis (dependence) | Primary | Planning MDE low / high; quarter; F-MDE | Floor |
|---|---|---|---|---|---|
| **CH252** the payer's return | Among non-sports ex-crypto **unrewarded** books, after a widening of the spread by >= 2 ticks over (k - 1, k], the spread re-tightens **more** over (k, k + 1] in **fee-on** books (maker paid a rebate per fill) than in **fee-free** books (maker paid nothing), given the widening's size, the level, tick, tier and category (`b_wdFF` = `beta_fee_free - beta_fee_on` > 0); the same contrast on **narrowings** is less than half in absolute value (binding two-sided placebo); the contrast survives adding `wd x log age` at >= half (binding age condition) | market x capture, all two-sided tight unrewarded units of a market (widening, narrowing and unchanged); market x UTC-day demeaning; **cluster event**; fee class a market-day constant (rule 20) | expanding-past market x UTC-day demeaned OLS of `ds = spread_{k+1} - spread_k` on `wd`, `wd x FF`, `nw`, `nw x FF` and `wd x` cell interactions; tested `b_wdFF`; event-level fee-label permutation gate; F binding | thin arm 15 (median) / 139.3 (mean) fee-on widenings a capture before filters, retention 0.5: DE 6 **1.07c / 0.37c**, F 1.69c / 0.59c; DE 11 1.44c / 0.50c, F 2.28c / 0.80c; DE 31 2.42c / 0.85c, F 3.83c / 1.34c; quarter of low (DE 6) 2.13c | 1.0c |
| **CH253** the listing batch | Among non-sports ex-crypto units in a **cross-event creation batch** (>= 3 markets created within a 120 s chain, >= 2 events), the own spread change over (k, k + 1] rises with the **complete cross-event mates' mean spread innovation** over (k - 1, k], given the own innovation and the category x slot factor over non-mates (> 0); a rule-21 pseudo-batch's innovation has an absolute slope < half (binding two-sided placebo) | market x capture; same-event mates excluded; **cluster batch**; batch x UTC-day demeaning | expanding-past batch x UTC-day demeaned OLS of `ds_i` on `zs_bt`; batch-phase state-shift gate (one offset per batch, demeaning re-applied every draw); F binding | 2,965 (median) units a capture before filters, retention 0.5: DE 31 **0.27c**, DE 51 0.34c, DE 79 0.43c; F 0.42 / 0.54 / 0.67c; quarter (DE 79) 0.85c, F 1.34c | 1.0c |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E022), LT5-LT12, E025 and E026. **Provisional k <= 2.** Each test is killable independently at
  its census; a failed gate drops it before registration (`census_dropped`, uncounted, final in both lanes); a failed coverage
  check is `census_unavailable (coverage)` (6), re-censusable only in the ordered lane as its own Holm family. A test withdrawn
  before the census is `withdrawn_pre_census (<reason>)` (uncounted, final, never `census_dropped`; R1). `k_tests` is fixed
  in the spec at registration. A primary that is unavailable or fails its gate enters Holm with p = 1. No replacement test after
  a drop or a withdrawal.
- **Window (fast lane, 1.1):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, **`REGISTERED_UTC` proposed
  2027-01-21T00:00:00Z** (never earlier; it slides later with LT9's window, never earlier), `END_UTC` = `REGISTERED_UTC` + 21 days
  (proposed **2027-02-11T00:00:00Z**); single analysis on or after `END_UTC` + 36 h (proposed **2027-02-12T12:00:00Z**). Census
  on LT12's worn seal span **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**, re-sealed with LT13's own file list (6).
- **Labels certain in both lanes:** both tests *informed (LT12 census span)* (the census span is LT12's seal span; no LT12
  object is computed); CH252's M1 *informed (E015)* and *informed (E022)* (E015's traded class, about 2026-11-15; E022's S2,
  about 2026-11-17). Lane-dependent labels: 1.1.
- **Honest survival priors (the designer's judgement after the CH261 map, not measurements; round 18's in brackets).**
  **CH252 0.08 [0.22]:** **three** of round 18's own census lines fail on the map's numbers (non-stationarity median / mean 0.108
  < 0.25; fee-on >= 5x fee-free at about 0.008; cell coverage 0.096 < 0.60; the last two restated in 5 items 1-2), and LT13's
  restated count line too (about 70 < 77 a capture at retention 0.5); the census span would need a larger and steadier fee-on
  unrewarded arm, and the map also shows an unexplained shift in the fee panel against CH251 (1.4.3): if q0717 does not explain
  it, CH252 is withdrawn before the census (1.4.3 rule (b)). **CH253 0.10 [0.15]:**
  the map cleared the round's three named killers (coverage 0.873, VIF 1.001, same-slot correlation 0.059) and the count has
  margin, but the rule-21 placebo coverage gate is expected to fail (0.755 on a coarser reading than the design's). **Expected k
  at census about 0.18; P(no LT13 test) about 0.83** (0.92 x 0.90, treating the fates as independent, which they are not: both
  read the same captures). **Expected valid verdicts about 0.09** (0.08 x 0.5 x 0.9 + 0.10 x 0.6 x 0.9 = 0.036 + 0.054; a valid
  verdict = registered, size check passed, not Unavailable; P(size passes | registered) 0.5 for CH252 (worlds 1, 3, 4 are the
  expected risks) and 0.6 for CH253 (worlds 8, 10)). Every taker cell is expected "not shown".
- **No LT13 result can satisfy the programme's economic check** (1.10). CH252's mechanism is paid about **0.05-0.13c a filled
  share**; a Supported CH252 is a behavioural fact about quote timing, never a rebate return. A Supported primary is an
  exploratory prospective finding, never an edge.

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)
`LIVE_TESTS_12.md` 1.0 applies unchanged (LT4 L1-L15; LT7-LT12 rulings; exact `%.17g` writes; NaN refusals; sealed census
inputs re-hashed; slots from the seal; pessimistic MDE gate `max(declared, design)` with `sqrt(max(1, VIF_w))`; size check
>= 2,000 worlds, limit 0.058; spec and code pins; write-once series; clustering by the cluster unit, cluster x UTC day and UTC
day with p the largest; Holm counted once; economics never changes a verdict; block gates for rolling states; `DE_gate = max(5.0,
1 + (m_21 - 1) x 0.02)`, `m_21` the projected size-weighted mean cluster size; liquidity correlation gates; the lag-slot loader;
`T_X` conditions; the pinned sports and crypto classifiers; LT7's one-rule F; `r_gate = max(r_w, r_pool)`; count gates on gross
projected counts; **whether F binds is fixed per test now, by design; a label-only F chosen for power is rejected** (LT11 R1
A4, LT12 R1 MUST 1); `listed_carry24h_v2` for every reward status; distinct-cluster gates unprojected; `census_unavailable
(coverage)` distinct from `census_dropped`; Kish `G_eff >= 15`). **Defects found in LT12's reviews, each turned into a rule
here:**

| LT12 review item | LT13 rule |
|---|---|
| R1 MUST 4: an identification gate stated on a standardised state "in ticks" (units mismatch) | round 18 wrote CH253's gate as "within-batch-day SD of `zs_bt` >= 1 tick", the same mismatch; replaced by LT12's redefined form (3.4, 6) before any count |
| R1 MUST 5: a one-sided placebo passes a strongly negative placebo; a placebo sharing a story is not unrelated | both placebos two-sided (`|b| < 0.5 x b_primary`); CH253's pseudo-mates share no event, batch or series family with the unit (3.3) |
| R1 MUST 6 and re-check fix 1: gate path; the statistic and gate sample named; observed t refitted on the gate sample | 1.8 names each gate's path, statistic (cluster-CR1 t), gate sample and the refit; the size worlds call the same function |
| Re-check fix 2: world ranges that never exercise the small-cluster exclusion; loadings not calibrated | every world draws cluster lengths uniform on 8..252 captures; calibrated loadings by declared bisection with a failure rule (1.8.1) |
| Code check MUST 1: one market-wide drift in a "per-event drift" world, so the placebo partner carried the same drift | every drift world draws its drift **per cluster** (market for CH252, batch for CH253), never one venue-wide series; placebo partners carry their own cluster's drift; a unit test asserts it (7.3) |
| Code check SHOULD 3: the *analytic p oversized* label never set | verdict-size worlds aggregate the analytic rejection rate; the label is set above 0.058 (1.8) |
| Code check SHOULD 4: NaN draws counted as non-exceedances; untestable worlds counted as non-rejections | NaN draws are exceedances; untestable worlds are counted and printed per scenario and per test (1.8) |
| Code check SHOULD 5: `census_unavailable` and `census_dropped` conflated in code | the spec holds three mutually exclusive lists `k_tests`, `dropped_tests`, `census_unavailable`; the analysis refuses an unknown name or a test in none or two of them |
| Code check SHOULD 6: `analyze` without `--out` could repeat | `analyze --out` required; refuses to overwrite; exit 2 on refusal (1.1) |
| Code check fix 2: dry runs before code changes undisclosed | any run of census or world code on real or seeded data before the pin is logged with commit and time in the code notes |
| Final verification fix 2: a one-shot restore that could wait forever on a capture that never completes | 1.14 and 6: a capture in a final non-complete state, or past its tolerance with no capture, is missing, never awaited |

Round 18's rules map onto LT13 as follows (rules 1-20 as in LT12 1.0's table, applied to these units):

| Rule | LT13 rule |
|---|---|
| 1. Panel-complete units | every unit is a market x capture of the complete captures and their sidecar; no sweep, sample or monitor in any primary |
| 3. Innovations, not levels | CH252 the widening over (k - 1, k]; CH253 the mates' spread innovation over (k - 1, k]; every level is a control |
| 5. Field semantics first | 1.4.1 (reward status), 1.4.2 (tier), 1.4.3 (fee class, day-fixed, three readings printed), 1.4.4 (the batch join) |
| 7. DE and kill line | planning DE 6 / 11 / 31 (CH252), 31 / 51 / 79 (CH253); census `max(5.0, computed)`; kill lines stated per test |
| 8. Floors | 1.0c (both spread targets); the F-MDE cap equals the floor |
| 9. Seal | LT12's worn census span `[2026-11-07, 2026-11-17)`, re-sealed with LT13's own file list (1.1); disjoint from the CH261 and CH251 map spans and from every registered window |
| 11. Maker-side money routes | both primary routes maker-side, gross, no fills; taker cells reported (1.10) |
| 16. Join completeness | CH253 batch-captures with < 60% of members complete at k - 1 and k give no unit (counted) |
| 20. Fee class is a panel | CH252's fee class is a market-day constant (1.4.3), never a within-market state; the contrast's inference is cluster-robust across events, with a label-permutation gate (1.8) |
| **21. The latent join** | CH253's batch join pinned by sha256 before any count (1.4.4); window 120 s, minimum 3, >= 2 events, same-event mates excluded, cap 30 cross-event mates, completeness 60%; the rule-21 pseudo-batch placebo, coverage gate 90% |
| 22. Common states | not used as a primary; CH253's category x slot factor is a control, not a state |
| 23. Other markets' facts | CH253 reads other markets' spreads at k - 1 and k (public before the decision time); no unit's own outcome is read |

### 1.1 Registration, window, single analysis
- **Fast lane (proposed).** `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT13 registration commit
  (spec pin plus ledger entry), **(b)** at least 24 h after the `END_UTC` of LT9's registered window (LT9's `REGISTERED_UTC` is
  never before 2026-12-30, so its window ends no earlier than 2027-01-20T00:00Z) or its recorded drop, and **(c)** never earlier
  than **2027-01-21T00:00Z**. Proposed **2027-01-21T00:00Z**; `END_UTC` 2027-02-11T00:00Z; analysis date `END_UTC + 36 h` =
  **2027-02-12T12:00Z**. Requirements: the design-text freeze before the LT13 seal commit, and the **registration commit before
  `T_LT12`** (LT12's analysis, proposed 2027-01-01T12:00Z) and before `T_LT9`; else the fast lane lapses (recorded in the ledger)
  and the ordered lane applies. If LT9 slides later, rule (b) slides LT13 with it; LT13 never starts earlier than (c).
- **Ordered lane (fallback, declared now).** If the registration commit is not before `T_LT12`: `REGISTERED_UTC` = the first
  00:00Z at least 24 h after the later of LT9's `END_UTC` (or its recorded drop) and the registration commit, never before
  2027-01-21T00:00Z; 21 days; single analysis >= 36 h after the end. It needs a fresh seal and census of the 10 UTC days ending
  at least 4 days before the registration commit, disjoint from every registered window, with every gate and value rule of 6
  unchanged; fast-lane census outputs become descriptive; `census_dropped` stays dropped; `census_unavailable (coverage)` is
  re-censused as its own Holm family. A pin after `T_LT12` labels **both** tests *informed (LT12)* (CH252: LT12's CH244 reads
  reward status as a panel on mixed ladders; CH253: LT12's CH245 reads a same-event twin's spread innovation; both adjacent).
- **Adjacent analyses and labels (`T_X` = the earlier of X's analysis job start and X's analysis commit; `T_LT12c` = the earlier
  of LT12's census job start and its census commit, planned about 2026-11-18).**

  | Test | Adjacent (`T_X`) | Why | Consequence |
  |---|---|---|---|
  | both | **LT12 census** (`T_LT12c`) | LT13's census reads LT12's seal span; LT12's census prints spread innovations on two-member pairs and mixed ladders (counts) | *informed (LT12 census span)* in both lanes, certain; a freeze before `T_LT12c` keeps the designers blind to LT12's census output (planned); a freeze after it adds *informed (LT12 census)* |
  | both | **LT12** (`T_LT12`, about 2027-01-01T12Z) | CH244 (reward status x shock on mixed ladders), CH245 (twin spread innovation) | fast-lane pin before `T_LT12` by construction; ordered lane: *informed (LT12)* |
  | CH252 M1 | **E015** (about 2026-11-15), **E022** (`T_E022`, about 2026-11-17T12Z) | E015's traded class; E022's S2 reward split of traded movers' depth | *informed (E015)*, *informed (E022)* on M1 only, certain in both lanes |
  | CH252 M2 | **LT9 CH213** (window 2026-12-30..2027-01-20) | the rewarded panel's re-tightening after a band break | M2 (the rewarded arm) *informed (LT9)* if read after `T_LT9`; the primary reads only the unrewarded panel |
  | both | LT11 (window 11-18..12-09), LT10, E026 (to 12-07) | time only, or different states | no pooling; LT11's objects never computed |
- **Boundary.** A unit's oldest state input is capture k - 1, so the first origin is the first capture whose capture k - 1
  starts at or after `REGISTERED_UTC` (proposed 2027-01-21T02:31Z). Look-backs (`rv24`, the 12-slot carry window, the
  day-fixed statuses) may read captures of 2027-01-20 (counted `pre_window_source`), which lie inside LT9's window; LT13 reads
  them as raw rows and sidecars only and computes none of LT9's objects. The last origin is the last capture starting before
  `END_UTC`; its targets (k + 1) and twins (k + 3) are read.
- **Design-text freeze.** After the final pre-freeze verification's acceptance, a commit records this file's sha256 in the
  ledger. Afterwards the text changes only by the census-fixed values named in 6 and by code-freeze-check fixes that change no
  state, unit, target, estimator, gate, threshold or verdict rule (1.13). The embargo requests of 8 are filed at the freeze.
- **Fixed end, no extension; one analysis.** `run_live_tests13.py analyze` refuses before the analysis date, **requires `--out`**
  and refuses to overwrite it (exit 2); the spec's `k_tests`, `dropped_tests` and `census_unavailable` are mutually exclusive and
  the analysis refuses a test name in none or two of them. Effective start = max(`REGISTERED_UTC`, the first capture processed
  by the reader at the pinned commit); only lines whose `spec_sha` and `code_sha` equal the pins and whose role is
  `prospective_confirmation` are kept.
- **Time of year (disclosed).** No DST change in the census span or the window. The census span follows the US midterm
  (2026-11-03) and its resolution days; the window (late January to mid February) holds no US federal election. The fee-free
  panel shrinks over time by construction (markets deployed before 2026-03-30 resolve and are not replaced), so the window's
  fee-free population is expected to be smaller than the census's; projections do not correct for this (disclosed; the
  Unavailable floors catch it).

### 1.2 Streams read (all already written by the host's pass; no new collector, no network)
- **Captures** `snapshots/<id>/rows.csv.gz` (`state=complete` only): `bid`, `ask`, `spread`, `last_trade_price`, `volume24hr`,
  `liquidity`, `chg_1h` (and `chg_1d`, `chg_1w` if the header pre-check finds them), `end_date`, `event_id`, `neg_risk`,
  `neg_risk_market_id`, `closed`, `active`, `received_utc`, the manifest start.
- **Sidecar** `rows_ext.csv.gz`: `received_utc`, `fee_type`, `fee_category`, `series_slugs`, `order_price_min_tick_size`,
  `clob_rewards`, `fees_enabled`, `fee_schedule`, `created_at`, `volume_num`, `accepting_orders`, `event_ids`. An absent
  sidecar row sets category, tick, fee class, `created_at` unknown (the unit is excluded, counted `sidecar_missing`) and the
  reward status NaN.
- **CLOB reward feed** `reward_params/<capture_id>/`, read only for CH252's feed-disagreement gate and coverage (6), the
  analysis's feed-agreement sensitivity and M2. Feed clock and rules as `LIVE_TESTS_12.md` 1.2 (last usable feed capture <= 6 h
  before capture k - 1's start, else `feed_uncovered`). Never a state, control or target.
- **Not read:** sweeps, trade samples, the monitor, `cross_venue_live/`, `xv_quotes/`, `surprise_live/`, the stores
  `live_tests2/` .. `live_tests12/`, CB8-H holders, CB16-CB18, E025 and E026 stores and the **E026 frozen modules**, the keyless
  streams, `gamma_rules`, the engine's `quotes/`, `features/`, `aux/`, `predictions/` and label store, the CH240, CH251 and
  CH261 map outputs, Gamma outcome fields of any kind. **LT11's and LT12's objects (`xw`, `cl_sib`, `xo`, `zs_D`, `shock x
  unrew`, their twins and targets) are never computed or read; no registered test's window captures are read by any LT13
  census or size check.** J4-R `[2026-10-16, 2026-10-21)` and CB13-T's holdout `[2026-10-21, 2026-10-26)` are untouched; LT13
  holds no maker mark-out object.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3-LT12 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot); a missing slot
  leaves every quantity that needs it NaN (counted), never interpolated.
- **Decision time (both): capture k's last row receipt** (the largest `received_utc` over capture k's complete rows and sidecar
  rows). States read captures k - 1 and k and the 12-slot look-back. **Targets start at capture k + 1.**
- **Within-capture receipt order.** CH252 reads one market's rows only. CH253: a mate (or the unit itself) whose `rows.csv.gz`
  `received_utc` lies more than **120 s** from the batch-capture's median receipt at k - 1 or k is dropped from the mate set
  (the unit itself: no unit), counted `receipt_span` (LT11 MUST 1's rule; the map's reading). The residual overlap is
  disclosed and size world 8 plants it with the census's receipt gaps.
- **Late rule** as LT4 1.3. **Twins (F)** read captures k + 2 and k + 3 through the lag-slot loader; unit builders do not read
  them (causality test, 7.3).

### 1.4 Shared origin-side eligibility
LT12 1.4 applies (vendored `move_join`, `classify`): binary, open, active, `accepting_orders` not false; two-sided at k - 1 and
k (bid > 0, ask < 1); **tight** (spread <= 0.10 at k - 1 and k); end unknown or > `t` + 3 h (F arm: > `t` + 7 h, else
`f_end_short`); category by `cb17_census.is_sports_sidecar` (non-sports primaries; sports arm reported, uncounted); crypto
excluded by the pinned classifier (unknown counted and treated as crypto); `scope: non_sports_ex_crypto` fixed at the freeze;
one row per `condition_id`; tick equal at k - 1 and k (`tick_changed`); series-family rule (the census top family holding
> 40% of a primary population is excluded, `<test>.exclude_family`).

### 1.4.1 Reward status (CH252's population; a control in CH253)
`listed_carry24h_v2` exactly as `LIVE_TESTS_12.md` 1.4.1 states its three cases (vendored from `live_tests7.py`). **CH252's
unrewarded status is day-fixed** as LT12's CH244 (3.2): the status at the market's first eligible capture of the UTC day; a later
unit of that day whose status at its own k differs is excluded (`status_switched`, counted by status); a NaN own status is
`status_nan_unit` (excluded, never given the day-fixed status). The disclosure of LT12 1.4.1 applies: case (b)'s "otherwise 0"
treats a field Gamma omitted for 24 h as unrewarded; CH252's census gates the share of carry-unrewarded units the CLOB feed lists
(6). CH253 enters `rewarded_k` (case rules at s = k) as a control only.

### 1.4.2 Liquidity tier
As `LIVE_TESTS_12.md` 1.4.2: the cost model's bins on the row's `liquidity` at k (`< $1k`, `$1k-10k`, `$10k-100k`, `>= $100k`);
missing `liquidity` is NaN, excluded, counted.

### 1.4.3 Fee class (CH252's panel; rule 20; field semantics first, rule 5)
- **Reading (vendored `population_map_ch251.fee_class`, by hash):** `fee_free` if the sidecar carries `fees_enabled` with a
  non-empty false value (`fee_src = flag_off`) or a parseable `fee_schedule` rate <= 0 (`rate_zero`); `fee_on` if the rate is > 0
  (`rate_pos`); otherwise `unknown` (`no_schedule`, excluded, counted).
- **Day-fixed:** `FF_{m,day}` = 1 for fee-free at the market's first eligible capture of the UTC day; a later unit of that day
  with a different class is excluded (`fee_switched`, counted). Fee class is never a within-market state.
- **The documented rule as a print, never a substitute:** `doc_class` = fee-free if the sidecar category is geopolitics or
  `created_at` < 2026-03-30T00:00Z, else fee-on (`COST_MODEL.md` section 2). The census prints the sidecar-against-doc confusion
  table; the M5 sensitivity refits the primary on the doc reading; the primary always reads the sidecar.
- **Why gated (disclosed, [map]):** CH261's printed widening shares imply about **12,850 fee-free unrewarded and 910 fee-on
  unrewarded complete units a capture** (1,773.0 / 0.138 and 139.3 / 0.153), while CH251 counted **4,577 fee-free unrewarded and
  11,267 fee-on unrewarded open rows** a capture on an overlapping span (2026-10-13..10-23 against 10-20..10-28). Part of the
  gap is definitional (open rows against complete two-sided units: young fee-on unrewarded books are often one-sided), but a
  fee-free count of complete units almost three times the fee-free open-row count is not explained by any definition here. The
  cause (a change in how Gamma serves `fees_enabled` / `fee_schedule` / `feeType`, a denominator difference, a category
  reclassification, or the spans) is **unknown**; LT13 adds the fee-reading gates of 6 (finite class, switch share) and the
  per-capture prints, and the counts-only probe q0717 runs **before the freeze** (7.5; R1 MUST 3). Hypotheses the probe can
  separate, all from counts: (i) row against unit definitions (the CH251 open-row cell and the CH261 complete-unit cell are
  both printed per capture); (ii) the spans (the per-capture series is printed by date and over CH251's span, CH261's covered
  span and their overlap); (iii) sidecar field semantics changing over time (`fees_enabled` blank / true / false / absent,
  `fee_schedule` state and text hash, `taker_base_fee`, `ext_version`, by date); (iv) category reclassification (`fee_type` and
  `fee_category` verbatim by date; a missing `feeType` gives the literal category `unknown`, which the maps' reader counts as
  non-sports ex-crypto); (v) markets switching fee or category class between captures k - 1 and k.
- **Declared q0717 decision rule (R1 MUST 3, verbatim; declared before q0717 runs):**
  (a) q0717 may change only the field reading of 1.4.3 and the census prints, never a threshold (0.25, 77, 5x, 60%/20, 95%, 5%, 0.90).
  (b) If q0717 does not explain the CH251/CH261 shift with a field-semantics cause that a declared reading rule fixes,
  CH252 is `withdrawn_pre_census (fee reading unresolved)`.
  (c) If CH252 is withdrawn, CH253 still goes to census under item 2.
  Here "item 2" is R1's staging (step 3 of the status block: CH253's census code is written and frozen alone). A reading rule that
  q0717 motivates is written into this section before the freeze, with its reason, and carries *informed (q0717)*; it may not use
  any count of widenings, narrowings or spread changes (q0717 holds none). q0717 runs before the 8-day snapshot retention removes
  more of 2026-10-20..10-21 and prints its covered span; captures already gone stay missing (never restored for it).

### 1.4.4 The creation batch (CH253; rule 21; pinned by sha256 before any count)
- **Registry:** every market seen in any sealed capture of the census (or, in the window, any capture the reader has processed
  since its look-back start) with a finite sidecar `created_at`, all categories; the registry never forgets a market.
- **Chain:** sort the registry by (`created_at`, `condition_id`); a batch closes when the next creation is more than **120 s**
  after the previous one. **Batch key** = (`created_at` of the earliest member, the smallest `condition_id` among members with
  that `created_at`); stable because the registry never forgets. A batch is **cross-event** if its members span >= 2 event keys
  (event key = `neg_risk_market_id` where present, else Gamma `event_id`, else `m:<condition_id>`) and holds >= 3 markets.
- **Mates of unit i at k:** the batch's members outside i's event key, two-sided at k - 1 and k, tight at both, tick unchanged,
  within the receipt rule (1.3), any category except crypto (sports mates allowed: the quoter set is the batch's, not the
  category's; disclosed; the sports-only arm reported). A unit needs **>= 2 complete cross-event mates**; units whose batch holds
  **> 30 cross-event mates** form a reported arm (the season dumps; the map's cap). **Completeness:** a batch-capture with fewer
  than 60% of its members complete at k - 1 and k gives no unit (`batch_incomplete`, counted, never filled).
- **Pseudo-batch (rule 21, verbatim):** for unit i with m complete mates at k, the pseudo-mates are the first m eligible complete
  units at capture k, in the order of `sha256(condition_id || capture_id)`, that (i) share i's sidecar category, (ii) lie in i's
  `created_at` decile (deciles over capture k's eligible complete units), (iii) were created >= 7 days before or after i, (iv)
  are not in i's batch, event key or series family (1.4 family; `none:<event key>` singletons included). If fewer than m qualify,
  the placebo is NaN (`placebo_none`, counted). The rule reads capture k - 1 and k only.

### 1.5 Missing data, per-capture status and attrition (never imputed)
As LT12 1.5: every frozen unit receives one write-once status at every target slot (`two_sided`, `one_sided`, `closed_flag`,
`absent`, `capture_missing`); only `two_sided` has a target. A missing state or control is NaN (excluded, counted), never 0.
`volume_num` is used only by CH252's reported M1 (a counted `unknown` class, never inferred: LT11 MUST 5). **Attrition rule:**
|a_1 - a_0| > 2 pp in target availability between the contrasted groups (CH252: fee-free against fee-on widening units; CH253:
top against bottom census tercile of `zs_bt`) gives *attrition-differential* and Lee-type bounds, never a verdict change; size
world 6 plants the differential-attrition fake for CH252 (1.8.1).

### 1.6 What is not looked at before the analysis date
No mid, spread, move, target, P&L, regression or plot from `live_tests13/` files or in-window captures for these hypotheses;
only `run_live_tests13.py ops-stats` (file, line, role, class, panel and status counts; reads no price, spread, volume or
liquidity column; unit test). No change of thresholds, scales, populations, estimators or k after registration. **No LT13
designer, coder or reviewer reads E015's, E022's, LT9's, LT10's, LT11's or LT12's analysis outputs before the pin, nor LT12's
census output before the freeze.** **Census-span data:** nobody opens any capture, sidecar or feed capture of the census inputs
before the LT13 seal commit, except the header pre-check (headers only) and the restore's byte and sha256 checks.

### 1.7 Estimators, units of analysis and inference
- **Sign convention.** Every tested coefficient is predicted > 0; every MDE a magnitude.
- **Expanding-past demeaning** (LT2-LT12): each regressor minus the mean of the stratum's strictly earlier units of the same
  test; target raw; the first unit of each stratum drops. **Strata:** CH252 market x UTC day (rule 2; fee class is constant
  inside it, so its main effect is absorbed and only its interactions are estimated); CH253 batch x UTC day.
- **Known-factor block K** (LT12 1.7 unchanged): `p_k`, spread_k, `log1p liquidity`, `log1p volume24hr` (`vol_missing`), log
  hours to end (`hte_unknown`), `1[tick = 0.001]`, `z log rv24*`, `rewarded_k` (CH253 only; constant 0 in CH252), non-sports
  `fee_category` dummies, 11 slot-of-day dummies, own `d_k`, own 6 h and 24 h changes (`mom_missing`), `chg_1h` (and `chg_1d`,
  `chg_1w` as indicator pairs if present).
- **Standard errors and p (L10):** CR1 on the cluster (CH252 event; CH253 batch), two-way cluster x UTC day, and UTC day;
  one-sided **p = max(p_cluster on t with `G - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**; conservative 95% CI
  = hull of a 2,000-draw cluster bootstrap and the three Wald intervals; `G_eff` printed beside `G` and floored at 15. CH252
  also prints `G` and `G_eff` of the **fee-on events alone** (the thin arm decides the contrast's precision).
- **Dependence sensitivities (reported, never the verdict):** cluster x two-day block CR1; CH252 with capture fixed effects added
  (the lumpy arm's slot shocks, world 4); CH253 with event in place of batch; the both-demeaned refit (LT6).
- **Rolling states.** CH252: the next unit's state `wd_{k+1} = 1[spread_{k+1} - spread_k >= 2 ticks]` is a function of this unit's
  target, the strongest rolling link in the programme. CH253: the mates' innovation over (k, k + 1] is the next unit's state and
  overlaps this unit's target interval. **F binds for both, fixed now by design** (LT7's rule, 1.9).

### 1.8 Gates (valid nulls) and their size
- **CH252: event-level fee-label permutation gate (new; rule 20's panel contrast).** The within-market Freedman-Lane null of rule
  20 tests only the within-market term (that a widening is followed by re-tightening, which the mechanism and its boring
  alternative both predict); it is printed, never binding. The binding gate tests the panel contrast: **gate sample** = events
  whose units all carry one fee class (mixed events excluded, counted) in **strata** of category x tick class (an event's stratum
  is its first unit's); for each of 200 draws, the fee labels are permuted across the events of each stratum (an event keeps its
  units, timing and spreads; every market of the event takes the drawn label), every interaction with `FF` is recomputed, the
  expanding-past market x UTC-day demeaning is re-applied, and the full primary model is refitted; **statistic:** the tested
  coefficient's **event-clustered CR1 t**, identical for the observed fit (refitted on the gate sample) and every draw. NaN draws
  count as exceedances. One-sided `p_perm = (1 + #{t_draw >= t_obs}) / 201`; the gate passes if `p_perm < 0.05`. Why: the fee-on
  arm may hold few events, so the t reference is fragile; label permutation is exact under within-stratum exchangeability and
  is the one null that respects the arm's cluster count. It does not remove composition (fee class is not exchangeable with age);
  composition is held by the placebo, the age condition and the verdict-size worlds 1, 3, 5, 6.
- **CH253: batch-phase state-shift gate** (`batch_day_state_shift_gate`, new code modelled on LT12's
  `event_day_state_shift_gate`, vendored path by hash): per batch b, `I_b` = the ordered captures with a unit of b, `n_b = |I_b|`,
  `s_b = max(4, ceil(n_b / 4))`, one offset `o` from `[s_b, n_b - s_b]` per draw; **gate sample** = batches with `n_b >= 16`
  (others excluded, counted; the observed statistic refitted on the gate sample); the raw mates' innovation of position t takes
  the value at `(t + o) mod n_b` for every unit of b, `zs_bt` and `thin x zs_bt` are recomputed, the expanding-past batch x
  UTC-day demeaning is re-applied to every shifted regressor in each unit's real stratum and order, all else fixed; statistic the
  **batch-clustered CR1 t** on the gate sample; NaN draws count as exceedances; `p_perm` as above, 200 draws.
- A failed gate on data gives p = 1 in Holm and "SE check failed (gate on data)".
- **Size check, after the census.** `size-check` runs once on the code to be pinned, **2,000 worlds x 200 draws, seed
  20261797**, limit **0.058** (= 0.05 + 1.645 sqrt(0.0475 / 2,000)); gate worlds run each gate exactly as the analysis does; a
  world is generated once and evaluated under the test it binds; no effect of the tested term in any world. Untestable worlds
  (gate sample empty, model singular) are counted and printed per scenario and per test, and count as **rejections** for the
  size criterion (the conservative reading of LT12 code check SHOULD 4).

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | **S38 composition:** the fee-free panel older, more liquid and slower (higher spread persistence), fee class a step in age; no fee effect | none | CH252 | verdict size |
  | 2 | **S39 breathing book:** a venue-wide width cycle, identical AR and loading in both panels | label permutation | CH252 | gate |
  | 3 | **floor asymmetry:** the panels' spread levels differ relative to the one-tick floor; identical dynamics otherwise | none | CH252 | verdict size |
  | 4 | **lumpy thin arm:** fee-on units concentrated on burst captures (the census's median / mean ratio) and capture-level common spread shocks | label permutation | CH252 | gate |
  | 5 | **per-market drift (M-Q):** a slow drift per market, larger in fee-free markets, raising widenings and later changes alike | none | CH252 | verdict size |
  | 6 | **differential attrition:** fee-free books that would keep widening go one-sided at k + 1 more often | none | CH252 | verdict size |
  | 7 | **S41 category factor:** a category-wide AR spread shock on mates and non-mates in the same slot | state-shift | CH253 | gate |
  | 8 | **S42 one bot, sub-slot lag:** one quote model per batch moves all members, the own book a minute later; captures read rows at the census's receipt gaps | state-shift | CH253 | gate |
  | 9 | **S43 age co-movement:** an age-decile factor that the own book follows a slot later; batch-mates and pseudo-mates both carry it | none | CH253 | verdict size |
  | 10 | **S30-type batch volatility state:** an AR batch state loading on all members in the same slot, calibrated to the census's same-slot correlation | state-shift | CH253 | gate |
  | 11 | **per-batch drift (M-Q):** a slow drift per batch entering the mates' innovation and the own target | none | CH253 | verdict size |
  | 12 | **liquidity leak:** the own book's reversion speed and the mates' innovation variance share a latent liquidity seen noisily | state-shift | CH253 | gate |

  **Verdict size** (1, 3, 5, 6, 9, 11) = the share of worlds in which the analytic one-sided p (1.7) is < 0.05 **and** F and every
  point condition of the test (1.9) hold; the gate is omitted. The analytic rejection rate alone is also aggregated per world;
  above 0.058 it sets the label *analytic p oversized in simulation* (never a verdict change). Criterion <= 0.058.
- **Diagnostics beside the size check (not criteria):** a planted-effect power run per test (500 worlds; CH252 a 1.0c fee-on
  re-tightening after a widening, world 1's composition kept; CH253 1.0c per census tercile gap of `zs_bt`; seeds `20261797 x 100
  + 51, 52`); the CH252 permutable share and the CH253 omitted-position share per world; **world 1 (S38) also run under the
  label-permutation gate and its rejection rate reported as a diagnostic (R1 SHOULD 2)**: the gate is not a valid null under
  composition (fee class is not exchangeable with age), so world 1's criterion stays verdict size and this rate never sets a
  label or a verdict.
- **Consequence of a failure:** a failing scenario makes only the test it binds "SE check failed (size scenario)" (gate worlds) or
  "SE check failed (mechanical world)" (verdict-size worlds): p = 1 in Holm, **k unchanged**, no rerun, reseed, redesign or
  variant; `max_retries 1` for a deterministic crash only; no preliminary run at seed 20261797. **Expected:** worlds 1, 3 and 4
  may fail for CH252, worlds 8 and 10 for CH253.

### 1.8.1 Simulated worlds (declared now; census inputs only where named)
Common: units on a 2 h grid, `day = i // 12`; 200 draws per world at a fresh sub-seed from one generator seeded 20261797,
scenarios in table order; spreads in ticks with a 1-tick floor; **every cluster's length `n` uniform on 8..252 captures** (so
clusters under the 16-capture gate minimum occur); every drift, shock or state named "per market", "per batch" or "per event" is
drawn **inside that cluster's loop, independently**; 10% of units removed at random after generation; target availability 0.9
at random unless the world says otherwise; the model is the test's primary with K replaced by the simulated controls named.
- **CH252 common (worlds 1-6):** `M_on` fee-on markets and `M_ff = 5 x M_on` fee-free markets (`M_on` = the census's fee-on
  markets with >= 1 widening unit, capped at 400; floor 100), 90% standalone events and 10% two-member events; tick 1c or 0.1c with
  the census's tick shares per panel (census input); 4 categories assigned with the census's category shares per panel; a latent
  liquidity `L_m ~ N(0, 1)`; tiers cut from `L_m + N(0, 0.5^2)` at the census's tier quartiles; `log age` per market (fee-free
  uniform on [log 210, log 900] days, fee-on uniform on [log 1, log 210]); each market's spread `s_t = max(1, round(mu_m + x_t))`
  ticks, `x_t` AR(`rho_m`) with innovation SD 1.2 ticks; `wd`, `nw` by the +/- 2-tick rule; **no fee effect**.
  1. **S38:** fee-free `L_m ~ N(0.8, 1)`; `rho_m = 0.45 + 0.4 Phi(L_m)`; `mu_m = 2 + 2 exp(-0.5 L_m)`.
  2. **S39:** `rho_m = 0.6` in both panels, `mu_m = 3`; plus a venue-wide `W_t` AR(0.9), stationary SD 1 tick, added to every
     market's spread with loading 1.
  3. **Floor asymmetry:** `rho_m = 0.6` in both panels; `mu_m` drawn from each panel's census spread-level quantiles (q10..q90 of
     `spread_{k-1}` in ticks on widening units; census input; floor: fee-on from 1 + Exp(0.5), fee-free from 3 + Exp(2) if a
     panel's quantiles are NaN).
  4. **Lumpy thin arm:** world 2's markets without `W_t`; fee-on markets are two-sided only on a burst set holding a share `q`
     of captures, common to all fee-on markets, with `q` set so the simulated per-capture median / mean of fee-on widening units
     equals the census's ratio (census input); a capture-level shock `V_t` AR(0.5), SD 1 tick, added to every market's spread.
  5. **Per-market drift (M-Q):** world 2's markets without `W_t`, plus per market `mu_{m,t}` AR(0.99), stationary SD 1.0 tick in
     fee-free markets and 0.5 tick in fee-on markets, drawn per market.
  6. **Differential attrition:** world 2's markets without `W_t`; a fee-free unit is two-sided at k + 1 with probability 0.9
     if `x_{k+1} - x_k <= 1` tick and 0.6 otherwise; fee-on units 0.9 always.
- **CH253 common (worlds 7-12):** 300 batches of 3..31 markets (uniform), members spread over 2..min(members, 10) events, 4
  categories (70% of a batch's members in its modal category), 50 non-batch markets per category feeding the category x slot
  control; ages: each batch's `created_at` uniform over 300 days, members within 120 s; pseudo-mates drawn by 1.4.4's rule from a
  pool of 2,000 non-batch markets with their own batches and drifts; spreads in cents on a 1c grid, floor 1c.
  7. **S41:** a category factor `C_{c,t}` AR(0.8), SD 1c, loading 1 on every market of category c; own `u` AR(0.5); no lag.
  8. **S42:** no `C`; one quote model per batch moves every member's spread by the same step (+/- 1c) at a Poisson time (rate 0.4
     a slot); the own member updates after `L ~ Exp(mean 60 s)`; each capture reads the own row and each mate at times differing by
     a gap drawn from the census's own-to-mate receipt-gap distribution (its q50 and q90; floor q50 5 s), order random; the 120 s
     rule of 1.3 applied.
  9. **S43:** every market loads on an age-decile factor `A_{g,t}` AR(0.8), SD 1c; the own book's spread takes `A_{g,t-1}` (one
     slot late) with loading 0.5; batch-mates and pseudo-mates share g; no batch effect.
  10. **Batch volatility state:** a per-batch `v_t` AR(0.8) (stationary SD 1) loading `lambda` on every member's spread in the
      same slot; the model sees `z log rv24 = v_t + N(0, 0.7^2)`; `lambda` by bisection on [0, 10] to within 0.005 of `rho_ss =
      max(rho_census, 0.10)` (`rho_census` census-fixed, 6; the floor 0.10 sits above the map's 0.059) on a single batch of 10
      members and 20,000 slots at seed `20261797 x 100 + 61`; if `rho_census` is NaN, `rho_ss` is not bracketed, or 40 steps do not
      reach the tolerance, world 10 is not run and is "SE check failed (size scenario)" for CH253 (no other bracket or seed).
  11. **Per-batch drift (M-Q):** world 7 without `C`, plus per batch `mu_{b,t}` AR(0.99), stationary SD 0.5c, entering every
      member's spread; pseudo-mates carry their own batches' drifts.
  12. **Liquidity leak:** per batch `L_b ~ N(0, 1)`; the own book's reversion `rho = 0.9 - 0.3 Phi(L_b)`; the mates' innovation
      SD scaled by `exp(0.5 L_b)`; the model sees `L_b + N(0, 0.5^2)`.

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **F rule (LT7's, unchanged; binding for both, fixed now).** The arm model is the primary with the far-future twin added, on
  units that have it. `Δ = b(lead) - b(twin)`; **F holds iff Δ's one-sided p < 0.05 (1.7 rule; not Holm-adjusted; counted 0) and
  Δ̂ >= 0.5 x b̂_primary**; an arm with < 50% of the primary's units is *falsification unavailable*. Twins: CH252 `wd x FF` with the
  widening over (k + 2, k + 3] (NaN unless two-sided and tight at k + 2 and k + 3, tick unchanged); CH253 `zs_bt` over (k + 2,
  k + 3] for the same batch and mate rule.
- **Point conditions (binding, fixed now; estimates only, counted 0).** CH252 **(a) narrowing placebo, two-sided:** |b̂_nwFF| <
  0.5 x b̂_wdFF; **(b) age condition:** the primary refitted with `wd x RCS(log age)` and `nw x RCS(log age)` added (the restricted
  cubic spline of 2.3, knots declared there, none at the 2026-03-30 step; R1 MUST 4) gives b̂_wdFF(age) >= 0.5 x b̂_wdFF. CH253 **(a) pseudo-batch placebo, two-sided:** the primary with `zs_bt` replaced by `zs_pb` (1.4.4) has |b̂_pb| < 0.5 x
  b̂_bt, on the units where the placebo is defined (that set's b̂_bt refitted on it).
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate > 0, gate passed, F holds, every point
  condition holds. Else, with everything else holding: F fails or unavailable -> **Inconclusive** with *mechanical null not
  excluded* (or *falsification unavailable*); a point condition fails -> **Inconclusive** with *not payer-specific* (CH252 (a)),
  *age-confounded* (CH252 (b)) or *placebo not null* (CH253). **CH252's Supported text** reads "a **fee-on/post-03-30 versus
  fee-free/pre-03-30 contrast** in re-tightening after a widening", **never "fee effect"** (R1 MUST 4: fee and age are separated
  only by functional form, 2.3).
- **Contradicted:** the conservative 95% CI lies entirely below 0. **Inconclusive:** otherwise. **Unavailable:** CH252 < 5,000
  fee-on widening units, < 100 fee-on events with a widening unit, < 20,000 fee-free widening units on support, < 300 fee-free
  events, fee-on `G_eff` < 15, or < 2,500 fee-on narrowing units (the placebo cannot be shown); CH253 < 20,000 units, < 300
  batches, < 100 batches with >= 48 units, or the placebo defined on < 50% of units; both: < 10 UTC days with units. **Why 5,000
  for CH252's thin arm:** at DE 6 the F-MDE at `n_eff` 4,000 (5,000 x 0.8) is `26.54 x sqrt(6 / 4,000)` = 1.03c, the floor; below
  it no verdict can reach the floor.
- **Labels (never change a verdict):** *material* (CH252 b̂_wdFF >= 1.0c; CH253 >= 1.0c at the census tercile gap); *informed
  (X)*; *analytic p oversized in simulation*; *underpowered*; *attrition-differential*; *late-loss*; *series-concentrated*;
  *doc-reading sensitive* (CH252: M5 changes sign); *feed-disagreement sensitive* (CH252: the refit on units whose carry status
  and feed agree changes sign); *receipt-order sensitive* (CH253: the refit on units whose own row was received before every
  mate at k changes sign); *sports-mate dependent* (CH253: the refit with non-sports mates only falls below half).
- **MDE multiplier** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (LT7-LT12), not lowered for k <= 2.

### 1.10 Economics (separate; descriptive; never changes a verdict)
- **The rebate, stated honestly.** The maker rebate is funded by the market's taker fees (25% of them outside sports and crypto)
  and shared by fill share, paid daily: per filled share `0.25 x rate x p(1 - p)`, and the cost model's pool haircut 0.5 halves it.
  At p = 0.5 and rate 0.04: **0.25c, 0.125c after the haircut**; at p = 0.1: 0.09c, 0.045c. The cost model's own words: about
  **0.05-0.1c per fill**. Half-spreads are 0.5-2.0c and adverse selection on filled touch orders 0.39-3.87c by tier. **A rebate of
  this size may move no quote at all;** that is the most likely boring outcome, and a Supported CH252 would show that quote timing
  differs between the panels, not that the rebate pays. CH252's M3 (the contrast by price bin: the rebate is five times larger at
  p = 0.5 than at 0.05) is the dose check, reported with its expected sign; a Supported primary whose M3 dose runs the wrong way is
  reported as such.
- **Maker routes (gross, an upper bound, no fills, no queue, no rebate or reward income):** CH252 the fee-on maker re-posts inside
  the widened spread one slot earlier than the fee-free comparison (the quantity is the re-tightening in cents a share; its value,
  if any, is the stale wide quote's pick-off avoided, not the rebate); CH253 the batch-mate maker widens by the mates' widening
  for one slot (the pick-off avoided = `ds_i`).
- **Paper taker (reported):** LT3's `paper_taker` and `econ` at the recorded touches of capture k and k + 1, fees on both legs
  from the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), cluster mean, one-sided p, >= 30 trades in
  >= 10 clusters. CH252: the fee-free taker waits one slot after a widening; CH253: take the stale mate's quote for one slot after
  the set widened (hurdle its own half-spread). **No E026 frozen module (`costs.py` included) is imported, copied or edited.**
- **Declared in advance:** every AREPO taker check has failed (0 of 95 cells positive); "not shown" is the expected outcome. A
  Supported LT13 primary can at most nominate a later, separately registered economic test at recorded prices.

### 1.11 Overlaps, dependence and counting
- **Within LT13:** CH252 reads unrewarded markets; CH253's units may include the same markets at the same captures (a CH253 unit
  can be a CH252 unit). The census prints the overlap (units and markets in both). The two tests answer different questions
  (fee panel against the batch join); Holm treats them as separate primaries; no pooling.
- **Against other tests:**

  | LT13 | Closest prior | Same contrast? | Why not a double count |
  |---|---|---|---|
  | CH252 | LT12 CH244 (reward status x sibling shock on mixed ladders) | no: CH252 holds reward status fixed (unrewarded) and contrasts fee class | different panel, state and window; *informed (LT12 census span)*; ordered lane *informed (LT12)* |
  | CH252 | LT9 CH213 (rewarded panel re-tightening after a band break) | no: rewarded panel; CH252's primary excludes it | M2 (rewarded arm) *informed (LT9)* if read after `T_LT9` |
  | CH252 | CH243 (dropped at LT12 R1), CH250 (engine-first) | no: CH243 contrasted traded continuation by fee class; CH250 is levels | neither tested; disclosed |
  | CH253 | LT12 CH245 (a same-event twin's spread innovation) | no: CH253 excludes same-event mates by construction | different join; *informed (LT12 census span)* |
  | CH253 | LT11 CH233 (siblings' bid sum, same event) | no | `cl_sib` never computed |
- **Counting:** the analysis adds **k counted tests**, kind `live_tests13` (`battery2.KIND_RULES["live_tests13"]`, fail-closed).
  Gates, F, point conditions, placebos, secondaries, arms, economics, the census, the CH261 map and the size check count 0.

### 1.12 Stop rules
As LT12 1.12: no interim look; runs to `END_UTC` whatever the counts; after 7 days a test whose units run below one third of its
census projection gets the ledger note "likely Unavailable" and nothing else changes; any change to a pinned file makes the
analysis refuse; gaps stay missing; the reader refuses above 3.0 GB in `live_tests13/`; a kind not in `k_tests` is switched off.

### 1.13 Deviations policy (declared now)
- **Operational deviations** (host outage, missed capture, reader crash, a capture lost to retention before extraction): recorded
  in the ledger within 24 h of discovery; the affected quantities stay missing and are counted (`capture_missing`); never refilled
  from any other stream (sweeps, engine `quotes/`, trade samples, the monitor) and never interpolated.
- **Before the freeze:** any change is a draft revision mapped to the reviewer item that caused it (section 12 after R1).
- **After the freeze, before the census commit:** a change to a state, unit, target, estimator, gate, threshold or verdict rule
  needs a written scientific justification, a `science-reviewer` acceptance, a new design-text sha256 in the ledger and the label
  *amended after freeze*; a code-freeze-check fix that changes none of them is recorded in the code notes only.
- **After the census commit, before the pin:** no change to any gate, threshold or definition; a defect found then drops the
  affected test (`census_dropped (defect)`, uncounted) or moves LT13 to the ordered lane with a fresh seal and census, as its own
  Holm family; nothing is re-censused on the same seal.
- **After the pin:** none. A pinned file that changes makes the analysis refuse; a defect found in a pinned rule makes that test
  "SE check failed (deviation)" with p = 1 in Holm, k unchanged, never re-run. Every deviation is listed verbatim in the analysis
  output.

### 1.14 Data retention and the write-once extraction of k + 1 targets (never reconstructed)
- **The constraint.** Snapshot row files (`rows.csv.gz`, `rows_ext.csv.gz`) are deleted from the host after **8 days**
  (`scripts/oracle/archive_retention.json`; temporarily 12 days until CB7's q0147c, then 8 again), only after a verified archive
  copy with an identical sha256 exists in the arepo-data releases; manifests are kept.
- **The window reader extracts on arrival.** A host cron reader (7.2) runs every 2 h and, for each newly complete capture,
  writes **write-once** (`%.17g`, atomic hard link) `live_tests13/series/<capture>.csv.gz`: one line per non-sports ex-crypto
  (and, for CH253 mates, non-crypto) open binary row with `condition_id`, bid, ask, two-sided flag, tick, `received_utc`, event key,
  fee class and source, carry inputs, `created_at`, `liquidity` and K's fields; then the frozen units of capture k (states only)
  and the outcome lines for every unit whose k + 1 (target) or k + 3 (twin) capture has now been extracted. **Targets and twins are
  computed from the reader's own series files, never from the snapshots at analysis time**, so snapshot deletion cannot touch
  them once a capture's series exists (normally within 2 h of its completion).
- **Lag guard.** The reader prints the age of the oldest complete-but-unextracted capture; above **72 h** it writes a ledger alert
  line (`lt13_lag`) and the orchestrator promotes the fallback job (q0724) the same day. 72 h leaves at least 5 days before the
  8-day deletion.
- **One-shot restore rule.** If a window capture's row files are gone before its series exists, the reader restores that capture
  **once**, byte for byte, from the verified release (sha256 equal to the archive catalogue) into a scratch directory, extracts its
  series, deletes the scratch copy and records `restored_from_release` with the hashes. A capture found in neither place, a
  capture in a final non-complete state (failed or partial), or a slot past its 30-minute tolerance with no capture is
  `capture_missing` (counted), **never awaited and never reconstructed**. No capture is restored twice.
- **No retention rule covers `live_tests13/`** before the analysis is committed; the nightly archive must be verified to include
  `live_tests13/` before the window opens (7.4 step 10).
- **Census inputs** follow the same rule: restored or sha256-checked once (6), sealed once.

## 2. CH252: the payer's return (fee-on and fee-free unrewarded books after the same widening)

### 2.1 Hypothesis in plain words
On books that no liquidity programme pays, two kinds of maker remain: in fee-on markets a maker earns a small rebate on every fill,
in fee-free markets he earns nothing. When a spread widens, the per-fill maker has a reason to come back to the touch soon (the next
fill pays); the unpaid maker has none. So after the same widening, fee-on unrewarded spreads should re-tighten more over the next
slot than fee-free unrewarded spreads. If the difference were only that fee-free markets are older, larger and slower, narrowings
would show the mirror-image difference (a slower book is slow both ways), and the difference would shrink once age is held.

### 2.2 Population and unit
- **Unit:** non-sports ex-crypto market x capture passing 1.4, day-fixed **unrewarded** (1.4.1), with a day-fixed fee class (1.4.3),
  in a **support cell** (below). **All** such units enter the model (widening, narrowing and unchanged), since the within-market
  reference is the market's other slots.
- **Events at (k - 1, k]:** `wd_k = 1[spread_k - spread_{k-1} >= 2 x tick - eps]`, `nw_k = 1[spread_k - spread_{k-1} <= -(2 x tick -
  eps)]` (the map's reading, `eps` from the CH240 helper); `wsz_k = wd_k x (spread_k - spread_{k-1})` and `nsz_k = nw_k x
  (spread_{k-1} - spread_k)` in cents.
- **Target:** `ds = spread_{k+1} - spread_k` (cents), `unavailable` unless `two_sided` at k + 1 (the tight rule is not applied at
  k + 1; a widening past 0.10 is a valid target).
- **Support cells [map, 5 item 2]:** cell = tier at k x tick class x sidecar category. `support_cells` (census-fixed) = cells with
  >= 20 fee-free widening units **and** >= 5 fee-on widening units in the census. Units outside them are excluded (`off_support`,
  counted by panel). Age is deliberately not a cell dimension (5 item 2): it enters the age condition.
- **Arms (reported, uncounted):** the rewarded panel (M2); the sports arm (empty fee-free cell by construction; the fee-rate
  gradient 0.03 / 0.05 reported); geopolitics (fee-free only, no fee-on comparator); `status_switched` and `fee_switched` units.

### 2.3 Model, the primary statistic and the placebo
- **Primary:** expanding-past market x UTC-day demeaned OLS of `ds` on `wd`, `wd x FF`, `nw`, `nw x FF`, the "same widening"
  interactions `wsz`, `wsz x FF`, `nsz`, `wd x spread_{k-1}`, `wd x 1[tick = 0.001]`, `wd x` tier dummies, `wd x` category dummies,
  `nw x spread_{k-1}`, and K. **Tested coefficient `b_wdFF`** (the coefficient of `wd x FF`; fee-on is the reference, so `b_wdFF =
  beta_fee_free - beta_fee_on` evaluated at the reference widening size), one-sided **H1: b_wdFF > 0**. Inference 1.7 (cluster
  event); gate 1.8 (label permutation); **F binding** (twin `wd x FF` over (k + 2, k + 3]); point conditions (a) and (b) binding.
- **Placebo (built in): `b_nwFF`**, the coefficient of `nw x FF` in the same fit; condition (a) of 1.9: |b̂_nwFF| < 0.5 x b̂_wdFF.
  Under a pure persistence difference between the panels (AR coefficients `rho_ff > rho_on`), `b_wdFF` is about `(rho_ff -
  rho_on) x size` and `b_nwFF` about `-(rho_ff - rho_on) x size`, so |b_nwFF| ~ b_wdFF and (a) fails, as intended. **Disclosed
  weakness (10 item 3):** a payer whose maker also *stays* longer after a narrowing predicts `b_nwFF > 0`, which (a) also
  rejects; the two-sided form is kept because round 18 wrote it and a one-sided form would loosen it.
- **Age condition (b) (R1 MUST 4):** fee class is a step in `created_at` at 2026-03-30 within every category but geopolitics, so
  the contrast is old against new markets by the venue's own rule; round 18's age class (before / after 2026-03-30) **is** the fee
  rule, so exact matching on it is a positivity failure by construction, and fee and age are separated **only by functional
  form**. (b) asks that `b_wdFF` survive at >= half when `wd x RCS(la)` and `nw x RCS(la)` enter, where `age_k` = capture k's
  start minus `created_at` in days (floored at 1/24 day), `la = ln(age_k)`, and `RCS` is the restricted cubic spline (Harrell's
  truncated-power basis, linear beyond the outer knots, nonlinear terms scaled by `(t_5 - t_1)^2`; 4 basis terms) with **5 knots
  declared now at ln of 1, 7, 30, 120 and 720 days**. **No knot sits at the 03-30 step:** markets created on 2026-03-30 are 222-232
  days old over the census span and 297-318 days old over the window, both strictly inside (120, 720), so the spline is one
  smooth cubic across the step and cannot absorb it. The census prints `VIF_w(wd x FF)` with and without the spline terms; a
  large value warns that (b) will be noisy (print, no gate; 10 item 2).
- **Wording:** a Supported CH252 reads "**fee-on/post-03-30 versus fee-free/pre-03-30 contrast**", never "fee effect" (1.9).
- **Secondaries (reported, uncounted):** M1 traded widenings only (`volume_num` change > 0 at (k - 1, k]; `unknown` a class;
  *informed (E015)*, *informed (E022)*); M2 the rewarded panel's contrast (*informed (LT9)* if after `T_LT9`); M3 the contrast by
  `|p_k - 0.5|` tercile (the rebate's dose: expected largest in the central tercile); M4 the deployment-date neighbourhood (markets
  created within +/- 60 days of 2026-03-30, geopolitics excluded); M5 the doc-rule fee class (1.4.3); **M6 (R1 MUST 4) the
  geopolitics-young versus fee-on-young contrast:** the primary model on units of markets created on or after 2026-03-30 only, with
  `FF` = 1 for sidecar-geopolitics markets (fee-free by the venue's rule at any age, 1.4.3's `doc_class`) and 0 for fee-on markets,
  so fee is not a step in age inside it; category is then confounded with fee (disclosed; never binding); the feed-agreement refit;
  the per-capture distribution of fee-on widening units.

### 2.4 Planning counts and MDE (planning only; the map counted the population, never an effect)
- **Counts (CH261, per capture, non-sports ex-crypto, simple reward reading, no tight rule):** fee-on unrewarded widenings
  **median 15, mean 139.3, min 4** (total 12,538 over 90 captures); fee-free unrewarded widenings median 1,857.5, mean 1,773.0
  (total 159,567); fee-free unrewarded narrowings median 2,248.5. **Planning retention 0.5 (unprobed)** for the design's filters
  (tight rule, carry reading, k + 1 availability, tick rule, support cells); fee-free support share a further 0.5. 21 days = 252
  captures; `n_eff` = 0.8 x raw:
  - low (median-based): `n_on` = 15 x 252 x 0.5 x 0.8 = **1,512**; high (mean-based): 139.3 x 252 x 0.5 x 0.8 = **14,041**;
  - fee-free: 1,857.5 x 252 x 0.5 x 0.8 x 0.5 = **93,618** (it barely moves the MDE).
- **Design effect:** cluster = event; mostly standalone markets, so `m_21` about 252 and the formula gives DE about **6**; 11 for
  two-member events; 31 the convention, quoted only. The census computes `max(5.0, ...)` from the measured `m_21`.
- **MDE** (class contrast of two within-market contrasts, `sqrt(2)` for the difference of differences; no gap factor on an
  indicator; `16.786 = 3.47 x 2c x 1.5 x sqrt(1.3) x sqrt(2)`; `MDE = 16.786 x sqrt(1/n_on + 1/n_ff) x sqrt(DE)`):

  | DE | low (n_on 1,512) | high (n_on 14,041) | F-MDE low / high (x 1.5811, `r_w` 0.2) |
  |---|---|---|---|
  | 6 | **1.07c** | 0.37c | 1.69c / 0.59c |
  | 11 | 1.44c | 0.50c | 2.28c / 0.80c |
  | 31 | 2.42c | 0.85c | 3.83c / 1.34c |

  Quarter of the low count at DE 6: 2.13c (F 3.37c). The low end fails the floor at every DE; the high end passes F at DE 6 and 11.
- **Kill line (F-MDE <= 1.0c; the fee-free term ignored):** `n_on_eff >= (16.786 x 1.5811)^2 x DE = 704.4 x DE`: 4,226 at DE 6
  (**21.0 fee-on widening units a capture**, post-filter), 7,748 at DE 11 (**38.4**), 21,836 at DE 31 (108.3). **Count gate 77 a
  capture** (19,404 projected; twice the line at DE 11, LT9-LT12 practice). The MDE gates decide with the census's own DE, `VIF_w`
  and `r_gate`.
- **Against the map (said plainly; R1 MUST 1):** pre-filter mean 139.3 at retention 0.5 gives about **70 < 77**; a retention >= 0.55
  would clear it; no retention clears it on the median capture. On the map, CH252 fails **three of round 18's census lines**: the
  non-stationarity line (median >= 0.25 x mean) at **0.108**; round 18's "fee-on >= 5x fee-free" at about **0.008** (median 15 /
  1,857.5); round 18's cell-matched coverage at **0.096** (< 0.60). The last two are restated in 5 items 1-2 [map]; the first is
  unchanged. **The non-stationarity line and the count line are the census lines expected to drop CH252**; the map's values are
  not census values (the map is not the census, top of file).

### 2.5 Confounders and how each is held
- *Composition: old, large, slow fee-free books* (S38): support cells, `wd x` cell interactions, the narrowing placebo (a), the age
  condition (b), world 1 (verdict size).
- *Fee class is a step in age* (the venue's rule): (b) with the restricted cubic spline in log age (no knot at the step), M4 (the
  deployment-date neighbourhood), M6 (geopolitics-young against fee-on-young), the Supported wording of 1.9; disclosed as the
  identification limit: fee and age are separated only by functional form; no cell can separate them except near 2026-03-30.
- *The one-tick floor* (world 3): `wd x spread_{k-1}`, `nw x spread_{k-1}`, the size terms.
- *A lumpy thin arm* (median 15, mean 139): the non-stationarity gate, the venue-clock gate, the capture fixed-effect sensitivity,
  world 4 (gate).
- *Fee-reading instability* (1.4.3): day-fixed class, `fee_switched` excluded, the switch-share and finite-class gates, M5.
- *Reward-field omission:* the carry reading, the feed coverage and disagreement gates (LT12 7 reused), the feed-agreement label.
- *Differential attrition at k + 1* (world 6): the attrition rule's bounds and label.
- *Tick:* 2 ticks are 2c on a 0.01 tick and 0.2c on a 0.001 tick; `wd x 1[tick = 0.001]`, tick in the cells, `wsz` in cents.
- **Most likely boring outcome:** the rebate moves no quote and the contrast is composition (the placebo or the age condition fails),
  or the fee-on unrewarded arm is too thin and too lumpy and the census drops CH252 (the expected outcome on the map).

### 2.6 Data streams, jobs, timing
Rows and sidecars of captures k - 12 .. k + 3 (carry window, k + 1 target, twins); feed captures at the feed clock. Census CC13
(6); token `payreturn` (8).

## 3. CH253: the listing batch (cross-event batch-mates' spread innovation and the own next spread change)

### 3.1 Hypothesis in plain words
The venue lists markets in batches: a themed drop or a slate of questions is created within a minute or two, often across several
events, and the same quoters pick the batch up. When those quoters re-price (a volatility update, an inventory limit, a lapse), the
batch's books move together; a book whose spread did not move when its batch-mates widened is the stale one and should follow a slot
later. Same-event mates are excluded (LT11 and LT12 own that join), so the test asks whether a creation-time join that no venue key
names carries spread information across events, beyond the category's own movement.

### 3.2 Population and unit
- **Unit:** non-sports ex-crypto market x capture passing 1.4 (any reward status), in a cross-event batch (1.4.4) with >= 2 and <= 30
  complete cross-event mates at k, its batch-capture complete (>= 60%), the receipt rule met.
- **Target:** `ds_i = spread_{i,k+1} - spread_{i,k}` (cents), `unavailable` unless `two_sided` at k + 1.
- **Arms (reported, uncounted):** batches with > 30 cross-event mates; the sports arm (units in sports categories); the genesis arm
  (M3: units whose batch is <= 7 days old at k); non-sports-mates-only (the *sports-mate dependent* label).

### 3.3 State, controls, primary statistic and placebo
- **State:** `zs_bt = mbar_i / s_bt`, `mbar_i` the mean over the unit's complete cross-event mates of `spread_{j,k} - spread_{j,k-1}`
  (cents), `s_bt` the census pooled population SD of `mbar_i` over census units (one scalar, census-fixed; round 18's "per batch"
  standardisation is impossible for batches born in the window, so one scalar is used, as LT12's `s_D`).
- **Controls:** the own innovation `spread_{i,k} - spread_{i,k-1}`; **the category x slot factor** `cbar_{c,k}` = the mean spread
  innovation over (k - 1, k] of capture k's eligible complete units of the unit's category outside the unit's batch (all of them
  known at the decision time); `d_i`, `|d_i|`; `spread_{i,k-1}`; `thin_i = 1[spread_{i,k-1} > median of the mates' spread_{k-1}]`;
  `thin_i x zs_bt` (M1's term, a control in the primary); fee class; K (with `rewarded_k`).
- **Primary:** expanding-past batch x UTC-day demeaned OLS of `ds_i` on `zs_bt` with the controls; **one-sided H1: b_bt > 0** (the
  coefficient of `zs_bt`, read at `thin_i = 0` and scaled to the census tercile gap for the *material* label); inference 1.7 (cluster
  batch); gate 1.8 (batch-phase state shift); **F binding**; the placebo point condition binding.
- **Placebo:** `zs_pb` = the pseudo-mates' mean innovation (1.4.4) divided by `s_bt`; condition (a) of 1.9, two-sided.
- **Secondaries (reported, uncounted):** M1 the thin-follows-dense ordering (`thin x zs_bt` > 0, and the thin slope > twice the
  dense slope); M2 the own mid change at k + 1 (*informed (L1-L4, E005)*); M3 the genesis arm; M4 the receipt-order split; the arms
  of 3.2.

### 3.4 Planning counts and MDE (planning only)
- **Counts (CH261, per capture):** primary units (>= 2 complete cross-event mates, cap 30, no tight rule) **median 2,965, mean
  2,957.2, min 2,797** (stationary: median / mean 1.003); eligible rows in a cross-event batch of >= 3: **0.873**; same-slot
  correlation of the own and the mates' mean innovation **0.059** (n 266,149); mates against category non-mates **0.035** (VIF
  1.001); pseudo-batch coverage **0.755** (map reading: no category match, 1.4.4 differs). Planning retention 0.5 (unprobed): `n_eff` = 2,965 x 252 x
  0.5 x 0.8 = **298,872**.
- **Design effect:** cluster = batch; a batch of 31 members over 21 days at retention 0.5 holds 3,906 units, so the formula gives
  `1 + 3,905 x 0.02` = **79**; 31 (round 18's convention for events capped at 10 members) and 51 (round 18's formula value for a
  batch of 10 at full retention, `m_21` 2,520) are quoted beside it; the census computes `max(5.0, ...)` from the measured
  size-weighted `m_21`.
- **MDE** (slope; `26.112 = 3.47 x 2c x 1.5 x sqrt(1.3) x 2.2`; `MDE = 26.112 x sqrt(DE / n_eff)`, planning within-stratum SD of the
  demeaned state 1.0 in `s_bt` units): DE 31 **0.27c**, DE 51 0.34c, DE 79 0.43c; F (x 1.5811) 0.42c / 0.54c / 0.67c; a quarter of
  the count: 0.53c / 0.68c / 0.85c, F 0.84c / 1.08c / 1.34c. The census's declared MDE divides the gap by the measured SD `s_w` of
  the demeaned `zs_bt` (LT12 6 item 6), so a state that barely moves inside batch-days raises it.
- **Kill line (F-MDE <= 1.0c):** `n_eff >= 1,704.6 x DE`: 262 units a capture at DE 31, 431 at DE 51, 668 at DE 79. **Count gate
  862 a capture** (217,224 projected; twice the line at DE 51). Map: 2,965 x 0.5 = 1,482, margin about 1.7.
- **Against the map (said plainly):** power is not the question. The **placebo coverage gate (0.90)** is: the map's 0.755 used
  the age decile over the capture's complete eligible units and no category match (`population_map_ch261.py` l. 474-480), and rule
  21's pseudo-batch adds the category match, which is **expected to lower** coverage. This is not proven (R1 MUST 6): the design's
  tight rule changes both the decile base and the mate count m, which can move coverage either way. The structural reason is
  visible in advance: in the youngest age decile few markets were created >= 7 days apart from a young unit, and batches are
  young. **This is the census line expected to drop CH253.** It is not changed (R1 MUST 5): no nearby-batch placebo, and the cap
  stays 30 cross-event mates; a cap of 10 would raise placebo coverage by lowering m, a loosening made after the map.
- **Round 18's own cap inconsistency (disclosed, R1 MUST 5):** round 18 caps cross-event mates at **30** in CH253's sketch and its
  design lines (`CREATIVE_HYPOTHESES_2026-11-01.md` l. 507, 941) but writes **cap 10 for the primary** (DE 31; 11-30 a reported arm
  at DE 51) in its power and DE lines (l. 532, 952). LT13 keeps **cap 30** (the cap the sketch and the map used); the DE lines
  quote 31, 51 and the formula's 79 (above).

### 3.5 Confounders and how each is held
- *The batch is the category* (S41): `cbar_{c,k}` as a control, `VIF_w` gate, world 7.
- *One bot, no lag, a capture that reads rows mid-update* (S42): the 120 s receipt rule, M4, the same-slot correlation gate, world 8.
- *Age and listing week drive co-movement* (S43): the rule-21 pseudo-batch placebo (binding), world 9.
- *A batch volatility state* (S30-type): own innovation and `z log rv24` controls; world 10, calibrated to the census's same-slot
  correlation.
- *Slow per-batch drift* (M-Q): F binding; world 11.
- *Young illiquid books revert faster:* liquidity controls, the |corr| gates, world 12.
- *Sports mates:* the *sports-mate dependent* label; the sports arm reported.
- **Most likely boring outcome:** the placebo coverage gate drops it at census (expected on the map); else the mates are one bot
  updating every book within the same minute, so nothing is left to follow (same-slot correlation, `VIF_w`), or the pseudo-batch
  slope equals the batch slope (placebo not null).

### 3.6 Data streams, jobs, timing
Rows and sidecars of captures k - 1 .. k + 3 for every eligible market and its mates; the `created_at` registry (a few MB). Census
CC13; token `batch` (8).

## 4. Deferred and not taken (none counted)
- **CH255 (the leader flip):** out by the map (median 11 traded first-of-day flips a capture against 690). Engine-first.
- **CH254, CH258 (common states, rule 22), CH256, CH257, CH259, CH260:** engine-first by round 18's ranking; no LT13 request.
- **CH252's taker cell and CH253's stale-mate taker:** reported only (1.10).

## 5. Design changes from the round-18 sketches (made before any LT13 data; each needs the challenger's acceptance)
Items marked **[map]** were made after reading the CH261 map.
1. **CH252: the fee-on arm is the thin arm, so every count line is restated on it [map].** Round 18 planned fee-on unrewarded
   widenings at about 1,100 a capture and fee-free at 55-460, so it gated the fee-free count (>= 40 a capture) and required fee-on
   >= 5x fee-free. The map found the reverse (fee-on median 15, mean 139.3; fee-free median 1,857.5). The count gate is now on the
   fee-on arm (77 a capture, twice its own F line at DE 11), fee-free must be >= 5x fee-on, and round 18's non-stationarity line
   (median >= 25% of mean) is kept unchanged on both arms. Nothing is loosened: round 18's line 40 was on the arm that turned out
   large; the new fee-on line is stricter than any line round 18 put on fee-on. **Disclosed (R1 MUST 1):** on the map, round 18's
   own "fee-on >= 5x fee-free" fails at about 0.008 (median 15 / 1,857.5); this item restates it, so the failure is recorded here,
   not hidden (MUST 1 wording applied at the top, in 0 and in 11).
2. **CH252: support cells defined from the scarce arm, age removed from the cells [map; the riskiest change in this draft].**
   Round 18 required >= 60% of **fee-free** widening units in a tier x category x age cell holding >= 20 **fee-on** widening units;
   the map's proxy (category x age, no tier) measured 0.096. Two reasons for the change, both written before any census: **(i)** a
   matching rule draws comparators from the larger pool for the smaller one; the round's direction followed its planning premise
   that fee-on was larger, which the map reversed. **(ii)** The round's age class (before / after 2026-03-30) is the venue's fee rule
   itself; exact matching on it leaves only the rule's exceptions (flag anomalies) in common cells, so the contrast would be
   identified from fee-reading errors, not from the fee. Age therefore leaves the cells and enters the binding age condition (1.9
   (b)), M4 and world 1. The new gate (>= 60% of **fee-on** widening units in tier x tick x category cells holding >= 20 fee-free
   widening units) keeps round 18's 60% and 20. **This change turns a line the map says would fail into one it does not measure; if
   R1 rejects it, round 18's direction stands and CH252 is expected to drop on it.** **R1: accepted, with MUST 4** (ruling 10.2;
   the spline age condition, the Supported wording and M6; item 4). Round 18's own line in its own direction measured 0.096 on the
   map (disclosed, MUST 1).
3. **CH252: one model with widenings and narrowings, and "same widening" interactions.** Round 18 stated two contrasts (`wd`,
   `nw`); one model with both indicators and their `FF` interactions makes the unchanged-spread units the common reference and
   puts the placebo in the same fit; `wsz`, `wd x spread_{k-1}`, tick, tier and category interactions make "after the same
   widening" explicit.
4. **CH252: a binding age condition (new).** Written because of item 2(ii): with fee a step in age, the narrowing placebo alone does
   not hold an age-specific reversion that is asymmetric; (b) is a point condition, estimate only, like LT12's dense-twin condition.
   **Amended by R1 MUST 4:** (b) uses a restricted cubic spline in log age with 5 knots declared now (2.3; none at the 03-30 step)
   instead of a linear `log age` term; the Supported text reads "fee-on/post-03-30 versus fee-free/pre-03-30 contrast", never "fee
   effect" (1.9); M6 (geopolitics-young against fee-on-young) added as a reported secondary (2.3).
5. **CH252: the event-level label-permutation gate (new); the within-market Freedman-Lane gate printed only.** Rule 20 says the
   within-market null tests only the within-market term; LT13 adds a gate on the term actually tested, for the reason in 1.8.
6. **CH252: fee class day-fixed with a switch gate, and the doc rule printed [map].** 1.4.3: the unexplained CH251 / CH261 fee panel
   shift.
7. **CH253: the identification gate replaced (LT12 R1 MUST 4's lesson).** Round 18's "within-batch-day SD of `zs_bt` >= 1 tick"
   applies a tick unit to a standardised state; replaced by LT12's form (6), before any count of either form.
8. **CH253: one census scalar `s_bt`; decision time capture k's last receipt; the category x slot factor over the whole capture.**
   Round 18's per-batch standardisation and "rows received before the unit's own row" are replaced by LT12's conventions; with the
   decision time at capture k's last receipt, every non-mate at k is known.
9. **CH253: mates of any non-crypto category; batch key and registry stated.** The map chained over all categories; the quoter set
   is the batch's; the non-sports-mates-only refit is a label.
10. **CH253: DE 79 added beside 31 and 51 [map: the cap 30 the map used].** The formula at a 31-member batch gives 79; quoted.
    **R1 (MUST 5, ruling 10.8): cap 30 kept.** Round 18's own cap inconsistency (cap 30 at l. 507 / 941 against cap 10 for the
    primary at l. 532 / 952) is disclosed in 3.4; cap 10 would raise placebo coverage by lowering m, a loosening after the map.
11. **CH253: no placebo change (R1 MUST 5, ruling 10.4).** The nearby-batch placebo of 10 item 4 is rejected (a map-informed change
    to a rule-21 line after it failed); rule 21's pseudo-batch and its 0.90 coverage gate stand verbatim.
12. **Staged build (R1 MUST 2).** Census code first and frozen alone; world, size-check, gate and analysis code only for tests that
    survive the census (status block steps 3-6, 7.1, 7.4). The worlds stay fully specified in 1.8.1 at the freeze; the second code
    check verifies the code against that text.

## 6. Pre-registration census (counts only; before registration; worn pre-window data; no target read)
The census runs once, reads origin-side fields only (the only later-slot quantities are the twins' states, for `r_gate`, through
the lag-slot loader, which returns only the twin term; no mid, spread, bid, ask or volume of a later slot reaches census code; unit
test), prints counts, and is committed with its sha256 before the registration commit. **Every threshold below is stated now.** A
failed gate drops that test (`census_dropped`, uncounted); `k_tests` lists the survivors. **Input identity:** the census refuses
unless every input file is named in the LT13 seal with an equal sha256; slots and origins come from the seal.

**Inputs (LT12's worn census span, re-sealed for LT13).** Span **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**, 10 UTC days, 120
slots; the 12 slots `[2026-11-06T00:00Z, 11-07T00:00Z)` as look-back only (inside LT11's census seal span; raw rows only, no LT11 or
LT12 object computed); the 3 slots after the span (to 2026-11-17T04:31Z, before LT11's window opens on 11-18) for twins only.
Complete captures (rows, sidecar, manifest), 135 captures x 3 files, planning 1.0-1.4 GB; CLOB reward feed captures with start in
`[2026-11-06T00:00Z, 2026-11-17T00:00Z)` (CH252's feed gate). Byte-identical copies already restored for LT12 (q0710) are accepted
after a sha256 check against the archive catalogue; the rest are restored from the releases.
- **Restore, seal, census: each once** (LT12 7's rules: bytes measured first and the owner asked if the restore would exceed free
  disk; a file in neither place is missing, counted, never substituted; the restore refuses only while a lag-slot capture is in
  progress; a capture in a final non-complete state is missing; the seal records files, sha256s, slot assignment and the frozen LT13
  design-text sha256). Never run while LT12's census, size check or any other memory-heavy job runs.
- **Minimum covered days, checked first** (covered origins / 12): >= 7.0 (>= 5.0 for twin pairs); else the test is
  `census_unavailable (coverage)` and nothing else of it is printed. CH252's **feed coverage** is its second coverage check (LT12
  re-check fix 3): under 50% of tested units -> `census_unavailable (coverage)` at once.
- **Header pre-check** (headers only, before the census code is frozen; committed before the seal): 1.2's fields including
  `fees_enabled`, `fee_schedule`, `created_at`, `series_slugs`, `event_ids`, `liquidity`, `clob_rewards`.

**Definitions.** Projection = count x 21 / covered days. Distinct-cluster gates and ">= 48 units" counts are **unprojected**.
`DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)`. MDE gates `max(declared, design)` (multiplier 3.47; SD `ds` 2c). *Declared* = the
closed formula of 2.4 / 3.4 at the census's effective counts, `DE_gate` and `sqrt(max(1, VIF_w))` (CH253's gap divided by the census
`s_w`). *Design* = `3.47 x 1.5 x SD x se_1` from the census regressors after the analysis's expanding-past demeaning (LT8's working
covariance). F-MDE `= max(design MDE of Δ, MDE x sqrt(2 / (1 - max(0, r_gate))))`. Per-capture median and mean are taken over the
captures with a previous capture, zeros included.

| Test | Gate (all must hold; NaN fails) | Map number it sits near (planning only) | Values fixed into the spec |
|---|---|---|---|
| **CH252** | finite day-fixed carry status on >= 95% of eligible unrewarded market-days; **feed:** coverage >= 50% (else `census_unavailable (coverage)`, first) and feed-listed share among covered tested units <= 0.20 (else dropped); **fee reading:** finite fee class on >= 95% of eligible unrewarded units, and `fee_switched` market-days <= 5% of eligible unrewarded market-days; **projected fee-on widening units (all 2.2 filters, on support) >= 19,404 (>= 77 a capture)**; projected fee-free widening units on support >= 5x the fee-on count; **non-stationarity: per-capture median >= 0.25 x per-capture mean, for fee-on and for fee-free widening units**; **support coverage:** >= 60% of fee-on widening units in cells (tier x tick x category) holding >= 20 fee-free widening units; **distinct fee-on events with a widening unit >= 150**, fee-free >= 500, fee-free events with >= 48 units >= 100 (unprojected); **Kish `G_eff` >= 15 overall and on fee-on widening units**; **permutable share:** >= 50% of fee-on widening units in category x tick strata holding >= 2 single-class events of each class; pooled `|corr(FF, log1p liquidity)|` <= 0.5; within and pooled `|corr(wd, x)|` <= 0.5 for x in {`log1p liquidity`, `z log rv24`, `|d_k|`, `spread_{k-1}`}; **identification:** >= 50% of fee-on widening units in market x UTC-day strata holding >= 2 widening and >= 2 non-widening units; `VIF_w(wd x FF)` <= 2.0 (demeaned regressors, without the age terms); venue clock: the most common slot-of-day holds <= 50% of fee-on widening units; `r_gate` <= 0.3; **class MDE <= 1.0c; F-MDE <= 1.0c** | fee-on widenings median 15 / mean 139.3 (ratio **0.108**: fails the non-stationarity line); at retention 0.5 about 70 a capture (< 77); round-18 direction coverage proxy 0.096; feed shares, switch share, permutable share, fee-on events unprobed | `support_cells`; world inputs: `M_on`, tick and category shares by panel, spread-level quantiles by panel, the fee-on per-capture median / mean ratio; `exclude_family` |
| **CH253** | the batch join's code sha256 pinned in the seal before the count; **coverage:** >= 20% of eligible non-sports ex-crypto rows (1.4 at k) in a cross-event batch of >= 3; **completeness:** complete-member share pooled over batch-captures with an eligible member >= 60%; **projected units >= 217,224 (>= 862 a capture)**; **batches with a unit >= 500 and batches with >= 48 units >= 100** (unprojected); **Kish `G_eff` (batch) >= 15**; **same-slot:** among batches with >= 24 units, the share with within-batch `|corr(own innovation, mbar)|` >= 0.8 is <= 50%; **identification (LT12 form):** >= 50% of units in batch x UTC-day strata where the raw `mbar` is non-zero on >= 3 units; the top 1% of units by |demeaned `zs_bt`| hold <= 25% of its sum of squares and no batch holds > 5%; `VIF_w(zs_bt)` <= 2.0 against `cbar` and the own innovation (demeaned regressors); within and pooled `|corr(zs_bt, x)|` <= 0.5 for x in {`log1p liquidity`, `z log rv24`, `d_i`}; **placebo coverage (rule 21) >= 90% of units**; block-gate share >= 50% (units in batches with >= 16 shiftable captures); venue clock <= 50% of units with `|zs_bt|` >= 1 in one slot-of-day; `r_gate` <= 0.3; **slope MDE <= 1.0c; F-MDE <= 1.0c** | units 2,965 a capture (no tight rule); coverage 0.873; same-slot 0.059 pooled; VIF 1.001; **placebo coverage 0.755 on a looser reading (expected to fail)**; completeness, batches with units, identification unprobed | `s_bt`, `s_w`, `zs_bt` tercile cuts and gap, world 8's receipt-gap q50 / q90, `rho_census`, `exclude_family` |

- **Census-fixed values (exhaustive; each the exact census float).** (1) `k_tests`, `dropped_tests`, `census_unavailable`
  and `withdrawn_pre_census` (mutually exclusive). (2) `support_cells`. (3) CH252 world inputs: `M_on`; tick shares, category
  shares and the q10..q90 `spread_{k-1}` quantiles (ticks) of widening units, by panel; the fee-on per-capture median / mean ratio. (4) `s_bt`: population
  SD (ddof 0, cents) of `mbar_i` over census units. (5) `s_w`: population SD of the expanding-past batch x UTC-day demeaned `zs_bt`.
  (6) `zs_bt` tercile cuts (1/3, 2/3 quantiles) and the gap (top-tercile mean minus bottom-tercile mean). (7) World 8's receipt gaps:
  q50 and q90 of `|received_utc_i - received_utc_j|` at k over census unit-mate pairs (floor q50 5 s). (8) `rho_census`: the pooled
  Pearson correlation of the own innovation and `mbar_i`, both over (k - 1, k], over census units; NaN on zero variance. (9)
  `<test>.exclude_family`. The census's `DE_gate`, `VIF_w`, `r_gate`, feed shares and MDEs are gate values, recorded, never re-used to
  change a threshold.
- **Non-stationarity "each cell" (R1 SHOULD 1; round 18, `CREATIVE_HYPOTHESES_2026-11-01.md` l. 466-467).** The kill (median <
  0.25 x mean) binds on the two cells CH252's contrast uses: fee-on unrewarded and fee-free unrewarded widening units (all 2.2
  filters, on support). The **rewarded cells** (fee-on rewarded, fee-free rewarded) are **print-only** (per-capture min / median /
  mean): they are outside CH252's population (unrewarded only, 2.2) and enter only the M2 secondary, which carries no verdict, so a
  kill on them would drop the test for a population its primary never reads. The fee-class `unknown` cell is printed too.
- **Census prints (descriptive, no further gate).** CH252: the per-capture table of eligible non-sports ex-crypto rows by fee class x
  `fee_src` x carry status x {open, two-sided, tight, complete} (the CH251 / CH261 discrepancy, 1.4.3; extended by any print q0717
  motivates under 1.4.3 rule (a)); the sidecar-against-doc
  fee confusion; the carry-against-simple reward confusion and the 1.4.1 case counts; `fee_switched` and `status_switched` by class;
  the top-5 captures' share of fee-on widening units; `VIF_w(wd x FF)` with the age terms; the narrowing counts by panel; the
  off-support counts; the within-market Freedman-Lane gate is not run (no target). CH253: batch-size distribution, cross-event share,
  `batch_incomplete`, `receipt_span`, `placebo_none` by age decile, units by batch age (genesis share), the > 30 mates arm, the sports
  arm, sports-mate share; the overlap of CH252 and CH253 units.
- **Order:** one census job (CC13) streams the captures once and evaluates the two blocks independently.
- **Expected fates (declared now).** CH252: withdrawn before the census if q0717 leaves the fee shift unexplained (1.4.3 rule (b));
  else the non-stationarity line and the fee-on count decide; then support coverage, the fee switch share and fee-on events.
  CH253 (censused even if CH252 is withdrawn, 1.4.3 rule (c)): placebo coverage decides; then completeness and identification.

## 7. Implementation plan and queue drafts (no LT13 code yet; the q0717 probe is written, 7.5)

**Build order (R1 MUST 2).** Stage A, before the census: `live_tests13_base.py` (the vendored pieces the census uses),
the census, seal and restore paths of `live_tests13.py` and `run_live_tests13.py` (`seal`, `census`), their tests, and a
code-freeze check of that code alone. Stage B, only for the tests in `k_tests` after the census: the unit builders and reader,
`live_tests13_worlds.py`, `live_tests13_analysis.py`, `size-check`, `reader`, `backfill-series`, `ops-stats`, `analyze`, their tests,
and a second code-freeze check that verifies the code against the frozen text (1.7-1.10, 1.8.1); a world or gate for a dropped or
withdrawn test is never written. If no test survives, stage B is not written.

### 7.1 Modules to be written
- `backend/astrolabe/research_lab/live_tests13_base.py`: vendored, hash-pinned copies of `move_join`, `classify`, the slot grid,
  LT7's `RewardCarry` (`listed_carry24h_v2`), `population_map_ch251.fee_class` / `fee_parse`, LT12's `event_day_state_shift_gate`
  path (as the template of the new batch gate), LT3's `paper_taker` and `econ`, LT9's lag-slot loader and seal helpers, the sports
  and crypto classifiers; a provenance test checks each against its source hash. **No E026 frozen file is imported, copied or
  edited.**
- `backend/astrolabe/research_lab/live_tests13.py`: the batch registry and join (1.4.4), unit builders (2.2-2.3, 3.2-3.3), the reader
  with the lag guard and the one-shot restore (1.14), `ops-stats`, the census (6). `live_tests13_worlds.py`: worlds 1-12 and the
  power runs. `live_tests13_analysis.py`: 1.7-1.10, the two gates, Holm, counting, the spec-list refusals.
- `backend/scripts/run_live_tests13.py` (`seal`, `census`, `size-check`, `reader`, `backfill-series`, `ops-stats`, `analyze --out`).
- `backend/astrolabe/research_lab/model_specs/live_tests13_v1.json` (unpinned until 7.4); `battery2.KIND_RULES["live_tests13"]`.

### 7.2 Resources and install (light collector only)
- **No new collector, no network.** A pure reader of the pass's captures and sidecars (and the reward feed for CH252's gate and
  sensitivity), lane `cpu`, `network: none`.
- **Memory (planning, then a ladder):** per market the previous capture's row, the 12-slot carry texts, the day-fixed statuses and
  fee class; the `created_at` registry; per batch its member list: **steady 300-450 MB, peak 500-700 MB** (CH261's streaming map
  peaked at 642 MB computing more families). Ladder measured by a host dry run with the exact install command: (1) one reader under
  `ulimit -v 1572864`, accepted at peak RSS <= 750 MB; (2) else two readers (CH252; CH253) under one shared `flock`, each <= 750 MB;
  (3) else no pin (recorded).
- **Install: host cron** `45 */2 * * *` (a minute no other reader uses at install time; LT12's reader ends 12-31 and LT9's 01-20),
  own `flock`, `nice -n 19`, `oom_score_adj 1000`; q0724 is the fallback, never both.
- **Disk:** about 0.6-1.2 GB over the window (per-capture series dominate); refuse above 3.0 GB. **Analysis:** about 3-4 million
  CH252 unit rows (all unrewarded units) and 0.4-0.8 million CH253 rows; 200 refits per gate draw set; planning 3-4 GB, exclusive.
- **Host change:** the cron line, under the standing collection authorisation, by the orchestrator.

### 7.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests13.py`, synthetic only)
Causality (no unit builder reads capture k + 1 or later; decision time = capture k's last receipt); the widening and narrowing rule
at both ticks; day-fixed fee class and `fee_switched`; the three reward-status cases and day-fixed status; support cells and
`off_support`; the model's interaction set; the label-permutation gate (labels permuted across single-class events within strata,
interactions recomputed, demeaning re-applied, the observed t refitted on the gate sample, NaN draws counted as exceedances); the batch
registry never forgets, the 120 s chain, the batch key's stability when a new member joins, the cross-event and cap rules, same-event
mates excluded, completeness 60%, the receipt rule; the pseudo-batch rule (category, decile, 7 days, not batch / event / family,
`placebo_none`); the batch state-shift gate (raw state shifted with one offset per batch, demeaning re-applied, a pre-demeaned frame
refused); **every drift world draws its drift per cluster, and a placebo partner carries its own drift** (|corr| < 0.3 between a unit's
and its partner's drift over > 200 pairs); worlds generate clusters with `n < 16`; world 10's bisection and its failure rule; the
verdict-size worlds aggregate the analytic rate and set the label above 0.058; untestable worlds counted per scenario; the lag guard's
72 h alert; the one-shot restore (byte-identical only, once per capture, never a second time, a final non-complete capture missing);
`ops-stats` reads no price, spread, volume or liquidity column; the spec's four lists (`k_tests`, `dropped_tests`,
`census_unavailable`, `withdrawn_pre_census`) mutually exclusive; `analyze` refuses without
`--out`, before its date and on an existing `--out`; no test uses seed 20261797 (an AST and run-time guard, as LT12);
`test_pinned_files_hash_to_the_pins` (E026) stays green.

### 7.4 Registration steps and pins (in order)
1. R1, response, re-check, final pre-freeze verification.
2. **Design-text freeze commit**, sha256 in the ledger, planned by **2026-11-14** (before `T_LT12c` about 11-18 and before the LT13
   seal); the embargo requests of 8 filed in `signal_engine/CANDIDATES.md` in the same session.
3. **Stage A code** (census, seal, restore; 7 build order); a `science-reviewer` code-freeze check of it on synthetic data. A
   timing estimate of the size check per world (from 1.8.1's text, at a timing seed other than 20261797) is projected; if census
   commit + projected stage B + run + 24 h + the dry run cannot precede 2026-12-28T00:00Z, the ordered lane is declared by a ledger
   line before the seal.
4. q0720 restore and q0721 seal (not before 2026-11-17T09:00Z, after LT12's q0712 census finished); seal committed and pulled on the
   host.
5. Census q0722 (once); `census_dropped`, `census_unavailable (coverage)` and any `withdrawn_pre_census` recorded separately;
   census-fixed values filled.
6. **Stage B code for the surviving tests only**, its code-freeze check against the frozen text; then size check q0723 (2,000 worlds
   x 200 draws, seed 20261797), once; results per test; power runs reported.
7. Reader freeze check; host dry run following 7.2's ladder (on non-window captures).
8. Embargo entries verified (a missing entry blocks the pin); tokens of dropped tests withdrawn with a ledger line.
9. Pins `SPEC_SHA256`, `code_sha256`, `code_check`; E-numbers assigned; the ledger entry is the registration commit, **before
   `T_LT12` (2027-01-01T12:00Z)** and at least 24 h before `REGISTERED_UTC`.
10. Verify the nightly archive covers `live_tests13/`; install the cron line and run `backfill-series` within `[REGISTERED_UTC - 72 h,
    REGISTERED_UTC - 24 h]` (= [2027-01-18T00:00Z, 2027-01-20T00:00Z]); `pinned: true` and `nothing_new` verified; q0725 queued with
    `not_before` 2027-02-12T12:00Z.

**Timetable (fast lane, planning):** R1 done 10-28; q0717 at once (retention); response and re-check by 11-08; final verification
and freeze by 11-14; stage A code and its check 11-14..11-22; restore and seal from 11-17T09Z (after LT12's census); census
11-23..11-25; stage B code and its check for the survivors 11-25..12-03; size check by 12-10; reader check and dry run by 12-20;
embargo verification and pin by 12-28 (before `T_LT12`); window 2027-01-21..02-11; analysis on or after 2027-02-12T12:00Z.

### 7.5 Queue drafts (ids q0717 and q0720-q0725 checked unused on 2026-10-28; only q0717 is written under `queue/jobs/`)
Every job: DRAFT, counts 0 except q0725 (the single counted trials line, kind `live_tests13`); promoted only after the step named;
never while E015's, E022's or any LT9-LT12 census, size check or analysis runs (memory-heavy-jobs rule); `--data-dumps-cap-gb 50`
where the runner accepts it; restore, seal and census run once each, `max_retries 1` for a deterministic crash only.

| Id | Lane, mem, disk | `not_before` / `depends_on` | What it does |
|---|---|---|---|
| `q0717_lt13_fee_probe` (**required before the freeze**, R1 MUST 3; spec `queue/jobs/q0717_lt13_fee_probe.json`, code `lt13_fee_probe.py` / `run_lt13_fee_probe.py`) | cpu, `mem_mb` 450 (start-blackout exempt), `as_cap` 4,000, priority 65 | at once: the 8-day retention keeps deleting 2026-10-20..10-21 | counts only, k = 0, uncounted: per capture over the captures still on the host for [2026-10-13, 2026-10-28) (prints its covered span; captures whose rows are gone are counted missing, never restored), the raw sidecar fields (`fees_enabled`, `fee_schedule` state and sha256, `taker_base_fee`, `fee_type`, `fee_category`, `clob_rewards` non-empty, age class, `ext_version`) cross-tabbed by CH251's open-row cell, two-sided rows and CH261's complete-unit cell, by fee class x `fee_src` x reward x category, per capture and per date; fee / category class changes against k - 1; reads captures k - 1 and k only, never k + 1; no spread or price change, no target. **Decision rule declared in 1.4.3 (R1 MUST 3 (a)-(c), verbatim in the spec's notes).** *informed (q0717)* on every reading rule it motivates |
| `q0720_lt13_census_restore` | net, 400 MB, about 1,400 MB disk | 2026-11-17T09:00Z; the LT13 freeze; LT12's q0710-q0712 done | byte-identical restore of the census inputs (6) the host no longer holds; accepts q0710's restored copies after a catalogue sha256 check; bytes measured first, exit 3 "STOP AND ASK THE OWNER" if bytes + 1 GiB exceed free disk; the lag-slot rule of 1.14 |
| `q0721_lt13_seal` | net, 300 MB | q0720 | file list, sha256s, slot assignment, design-text sha256; committed before q0722 |
| `q0722_lt13_census` | cpu, 750 MB (exclusive if the dry run measures more) | q0721; code-freeze check accepted | CC13 (6), once |
| `q0723_lt13_size_check` | cpu, 800 MB | the census values committed | worlds 1-12 at 2,000 x 200, seed 20261797, once; `max_retries 1`, never a timeout retry at the registered seed |
| `q0724_lt13_reader` | cpu, 750 MB | 2027-01-21T00:00Z; fallback only | the window reader if the cron line cannot be installed, or after a `lt13_lag` alert; repeat until `END_UTC`; never both routes |
| `q0725_lt13_analysis` | cpu, 4,000 MB, exclusive | 2027-02-12T12:00Z | the single analysis, `--out` required |

## 8. Signal-engine mapping and embargo requests
Every family is point-in-time from the origin capture and its 12-slot look-back (DESIGN_V1 16) and an auxiliary family. **The LT13
date** = the later of **2027-02-14T00:00Z** and LT13's analysis commit (ordered lane: the later of its analysis date plus 36 h and its
analysis commit). Filed in `CANDIDATES.md` at the freeze, applied before the registration commit. This branch edits no engine code,
`config.EMBARGO` or `CANDIDATES.md`.

| Test | Family (aux version) | Columns | Token -> until |
|---|---|---|---|
| CH252 | `paymaker` spec version (`se-aux-payreturn-v1`) | `pr_wd`, `pr_nw`, `pr_wd_x_fee_free`, `pr_nw_x_fee_free`, `pr_wd_ticks`, `pr_wd_size_x_fee_free`; levels (`tilt`'s `tl_fee_ps`, `tl_rebate_ps`, `tl_fee_free`; `paymaker` cells after their dates) stay as filed | `payreturn` (new) -> LT13 date |
| CH253 | `batch` aux family (`se-aux-batch-v1`) | innovations `bt_mates_dspread`, `bt_thin_x_mates_dspread`, `bt_pseudo_dspread`; levels `bt_n`, `bt_n_events`, `bt_age_h`, `bt_cross_event`, `bt_mates_spread_med`, `bt_own_rank` may be built now (no test reads them) | `batch` (new) -> LT13 date |

- **Pre-freeze hold (in force since the signal-engine reply of 2026-10-28 ~10:50Z):** no scored family holds a fee class x widening
  (or narrowing) interaction on the spread, a cross-event mates' spread innovation, a thin x mates' product, or a `paymaker` fee x
  reward cell on the spread; the `event` family gets no cross-event spread innovation. If one is scored before the freeze, the
  matching test carries *informed (engine)* and the ledger records the first scored capture.
- **Attribution limit `attrlimit_lt13`** (`kind: attribution_limit`) to the LT13 date: no attribution of the champion, se1,
  `se24_lgbm_tilt`, `se25_lr_tilt`, `se26_lgbm_mm_full` or any broad model on fee class x spread-change interactions inside `tilt` /
  `paymaker`, or on batch-mate interactions; `no_broad_families: ["payreturn", "batch"]`.
- A test dropped at census has its token and any limit item made only for it withdrawn with a ledger line. An engine gain never
  changes an LT13 verdict; an LT13 verdict never promotes a model.

## 9. Disclosures
- **Read to write this file:** `CLAUDE.md`, `AGENTS.md`, `AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md` (sections 4-6),
  `CREATIVE_HYPOTHESES_2026-11-01.md` (sections 0, 0.1, 0.2, CH252, CH253, CH258, section 3), `CREATIVE_HYPOTHESES_2026-10-31.md`
  (rules 18-20), `CH261_MAP_2026-10-28.md` and `CH251_MAP_2026-10-23.md` (whole), `LIVE_TESTS_12.md` (whole), `LIVE_TESTS_11.md`
  and `LIVE_TESTS_9.md` (bounded greps: `m_21`, `G_eff`, the reader and retention lines), `reviews/LT12_*.md` (all four),
  `signal_engine/CANDIDATES.md` (round 18 notes and the signal-engine reply), `COST_MODEL.md` (sections 2 and 5),
  `EXECUTION_COSTS.md` (formula sources), `scripts/oracle/archive_retention.json`, `EXPERIMENT_LEDGER.md` (the CH261 entries),
  `lab_dashboard/registry.json` (the LT12 entry's shape), queue drafts q0710 and q0714, and the code of `population_map_ch261.py`
  and `population_map_ch251.fee_class` (definitions only). No host, network, `ssh`, `data-dumps`, evidence JSON, census output,
  prediction, target or P&L. **Second draft (R1 response) additionally read:** `reviews/LT13_CHALLENGER_R1_2026-10-28.md`,
  `population_map_ch251.py` and `population_map_ch261.py` (whole), the CH240 map's readers, `ext_sidecar.py` and
  `pairing.fee_category` (definitions only), `CREATIVE_HYPOTHESES_2026-11-01.md` l. 396-397, 460, 466-467, 507, 532, 941, 952, and
  `AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md` l. 102, 128. Still no host, network, `data-dumps` or evidence read.
- **The CH261 map** counted populations on captures 2026-10-20..10-28 (k - 1 and k only); seen before every gate here (9.1). It
  probed none of: the tight-rule retention, the carry reading's effect, k + 1 availability, support cells under the new rule, fee
  switches, fee-on events, CH253's completeness, batches with units, identification, or the rule-21 placebo coverage.
- **Development looks:** `tilt`'s visible fee levels (`tl_fee_ps`, `tl_rebate_ps`) and the `event` / `participation` families'
  levels; none reads an LT13 state as defined here; no LT13 designer has read se24, se25 or se26 scores.
- **Not known at the planned freeze:** E015, E022, LT9-LT12 results; LT12's census output.

### 9.1 Values declared now and their planning sources
| Value | Where | Source | Informed by the CH261 map? |
|---|---|---|---|
| CH252 count gate 77 a capture on the fee-on arm; fee-free >= 5x | 2.4, 6 | 2 x the F line at DE 11 | **yes** (the arms' sizes) |
| CH252 non-stationarity median >= 0.25 x mean, both arms | 6 | round 18, unchanged | values unchanged; the map's 0.108 seen |
| CH252 support cells (tier x tick x category; >= 20 fee-free and >= 5 fee-on); coverage 60% of fee-on units | 2.2, 6 | round 18's 60% and 20, direction changed (5 item 2); 5 fee-on a convention | **yes** |
| CH252 fee switch share <= 5%; finite fee class >= 95% | 6 | conventions (the 95% matches the carry status line) | **yes** (the unexplained fee shift) |
| CH252 fee-on events >= 150, `G_eff` on fee-on >= 15; Unavailable 5,000 / 100 / 2,500 | 1.9, 6 | 1.5 x the Unavailable event floor; the F-MDE floor arithmetic | partly |
| CH252 permutable share 50%; label-permutation gate | 1.8, 6 | new (5 item 5); 50% as LT designs' block-gate share | no |
| CH252 age condition at half | 1.9 | new (5 item 4); "half" as every LT point condition | no |
| CH253 count gate 862 a capture; DE 31 / 51 / 79 | 3.4, 6 | 2 x the F line at DE 51; the formula at 31 members | **yes** (the cap 30 used by the map) |
| CH253 coverage 20%, completeness 60%, same-slot 0.8 / 50%, `VIF_w` 2.0, placebo 90%, 120 s, cap 30, 7 days | 1.4.4, 6 | rule 21 and round 18, unchanged | values unchanged; map numbers seen |
| CH253 identification (LT12 form: >= 3 non-zero / 50%, top 1% <= 25%, batch <= 5%) | 6 | LT12 R1 MUST 4 and ruling B1 | no |
| World 10 floor `rho_ss >= 0.10`; bisection [0, 10], 0.005, 40 steps, seed `x 100 + 61` | 1.8.1 | LT12 re-check fix 2 form; 0.10 above the map's 0.059 | **yes** |
| Planning retention 0.5 | 2.4, 3.4 | designer's planning value | no (unprobed) |
| Seed 20261797; q0717, q0720-q0725 | 1.8, 7.5 | unused values (git grep, 2026-10-28) | no |
| CH252 age condition: restricted cubic spline in ln(age days), 5 knots at 1, 7, 30, 120, 720 days | 2.3, 1.9 | R1 MUST 4; knots at round ages spanning the planning age range, none inside (120, 720) where the 03-30 step lies (222-318 days) | no (the map holds no age-by-effect count) |
| q0717 decision rule (a)-(c) | 1.4.3, 7.5 | R1 MUST 3, verbatim | yes (the CH251 / CH261 shift) |
| Lag guard 72 h; reader cron `45 */2` | 1.14, 7.2 | 5 days of margin before the 8-day deletion | no |

## 10. Design-ambiguity items for the challenger (R1), the riskiest first
R1's ruling follows each item (**R1:**); the response is section 12.
1. **Go / no-go.** On the map, each test fails one of round 18's own census lines (CH252 0.108 < 0.25; CH253 0.755 < 0.90 on a
   looser reading). P(no test) about 0.83. Should LT13 proceed to the freeze and a census (cost: code, a restore, a census, a size check;
   value: a recorded census on fresh data), or should CH252 and CH253 go engine-first now (`payreturn` and `batch` as aux families after
   a recorded drop)? The designer's recommendation: run q0717 first; if it confirms the fee-on arm's lumpiness and the CH251 / CH261
   shift, record CH252 as dropped on the map without a census, and decide CH253 by R1's ruling on item 4.
   **R1: GO, with MUST 2 (staged build) and MUST 3 (q0717's decision rule declared before it runs).** A map-based "drop" would be a
   mis-record: the map is not the census; a value-based withdrawal is `withdrawn_pre_census (map-informed)` (top of file, 1.4.3).
2. **CH252's support cells (5 item 2).** Is reversing the matching direction and removing age from the cells a correction of a premise
   or a change that turns a failing line into an unmeasured one? Is the age condition (1.9 (b)) an adequate guard when fee is a step in
   age (VIF printed only)? Should the deployment-date neighbourhood (M4) be the primary instead, accepting that it is underpowered?
   **R1: accepted with MUST 4** (spline age condition with declared knots, none at the step; "fee-on/post-03-30 versus
   fee-free/pre-03-30 contrast" wording; M6). Applied in 2.3, 1.9, 2.5, 5 items 2 and 4.
3. **CH252's narrowing placebo.** The two-sided form rejects the composition story (|b_nwFF| ~ b_wdFF) but also a payer whose maker
   stays longer after a narrowing (b_nwFF > 0). Keep two-sided (designer), or rule a one-sided `b_nwFF > -0.5 x b_wdFF` with a written
   justification (a loosening)?
   **R1: keep two-sided** (LT12 R1 MUST 5). Unchanged.
4. **CH253's placebo coverage.** Rule 21's pseudo-batch is nearly infeasible for the youngest age decile by construction (few markets
   created >= 7 days apart within it). The designer keeps rule 21 and its 90% gate verbatim. An alternative R1 may rule on: a
   **nearby-batch placebo** (same category, created within +/- 7 days but in a different batch and event), which is *closer* to the
   treatment (it shares the listing week) and so harder to pass as a placebo, but has higher coverage. The designer does not adopt it:
   it would change a rule-21 line after the map showed the line fails.
   **R1: rejected (MUST 5).** No placebo change; 3.4 and 5 item 11.
5. **CH252's gate.** Is the event-level fee-label permutation within category x tick strata a valid and useful gate for a panel
   contrast (rule 20), given that fee class is not exchangeable with age? Should the within-market Freedman-Lane gate bind instead or
   as well?
   **R1: acceptable as an extra binding gate; the Freedman-Lane gate printed.** Unchanged (1.8); world 1 under this gate is a
   reported diagnostic (SHOULD 2).
6. **The fee reading (1.4.3).** Are the day-fixed class, the 5% switch gate and the 95% finite-class gate the right response to an
   unexplained shift in the fee panel, or should the doc rule (category, deployment date) be the primary reading?
   **R1: sidecar primary, contingent on MUST 3** (1.4.3's decision rule; CH252 withdrawn if the shift stays unexplained).
7. **The census span.** LT13 re-seals LT12's census span `[11-07, 11-17)` (round 18's proposal; label *informed (LT12 census span)*).
   Acceptable, or must LT13 wait for the ordered lane's fresh seal?
   **R1: acceptable; freeze before `T_LT12c`, else *informed (LT12 census)*.** Kept; the freeze is planned by 11-14 (7.4).
8. **CH253's DE and cap.** Cap 30 cross-event mates with DE up to 79 (the formula), against round 18's primary cap 10 (DE 31). The
   designer keeps the map's cap 30 because the map counted it; a cap 10 would shrink units by an unmeasured share.
   **R1: cap 30 (MUST 5).** Round 18's own cap inconsistency disclosed (3.4, 5 item 10).
9. **CH253's sports mates** (1.4.4): mates of any non-crypto category, with a label. Or non-sports mates only in the primary?
   **R1: acceptable with the label.** Unchanged.
10. **Planning retention 0.5** (unprobed) decides CH252's count line at the margin (70 against 77). Is the line fair at a value nobody
    has measured? (It is a planning number only; the census decides.)
    **R1: planning only; the census decides.** Unchanged.

## 11. Proposed registry entry and draft ledger block (DRAFT; not applied)
**`docs/research_lab/lab_dashboard/registry.json`, `live_tests` (proposed, not applied):**
```json
{
 "id": "LT13",
 "title": "Live tests 13: the payer's return and the listing batch (planned)",
 "plain": "Up to two planned live tests from ideas round 18: after a spread widens on books that no reward programme pays, do books where makers earn a small per-fill rebate tighten back faster than books where makers earn nothing; and do markets listed in the same two-minute batch across different events follow each other's spread changes a slot later. First draft written 28 Oct; the population map suggests both may fail their counting checks.",
 "batch": "LT13",
 "family": "mixed",
 "stage": "idea",
 "status": "waiting",
 "verdict": "pending",
 "effect": null,
 "next": "Fee-reading count (q0717) now; challenger re-check of the second draft; counting checks on 7-17 Nov data; collection proposed 21 Jan - 11 Feb 2027",
 "next_date": "2027-01-21",
 "candidate": false,
 "sources": {"verdict": "docs/research_lab/LIVE_TESTS_13.md (DRAFT)"},
 "stage_results": {"idea": "pending"},
 "reached": ["idea"]
}
```

**Ledger block (draft):**
```
## LT13 design draft, 2026-10-28 (experiments autopilot; DRAFT, nothing counted)
- docs/research_lab/LIVE_TESTS_13.md on feat/live-tests-13 (first draft; sha256 in the commit): one Holm family, k <= 2:
  CH252 (the payer's return: fee-on vs fee-free unrewarded re-tightening after a >= 2-tick widening; narrowing placebo and
  age condition binding; event-level fee-label permutation gate) and CH253 (the listing batch: cross-event batch-mates'
  spread innovation -> own next spread change; rule-21 pseudo-batch placebo; batch state-shift gate). F binds for both.
- Planning MDE: CH252 1.07c / 0.37c at DE 6 (thin fee-on arm 15 / 139.3 a capture, retention 0.5), F 1.69c / 0.59c; CH253
  0.27c-0.43c at DE 31-79, F 0.42c-0.67c. Count gates 77 (fee-on) and 862 a capture.
- On CH261's numbers CH252 fails three round-18 census lines (non-stationarity median/mean 0.108 < 0.25; fee-on >= 5x
  fee-free at about 0.008; cell coverage 0.096 < 0.60; the last two restated in 5 items 1-2) and LT13's restated count line
  (about 70 < 77); CH253 fails one (placebo coverage 0.755 < 0.90 on a looser reading). The map is not the census: nothing is
  census_dropped on it; a withdrawal is withdrawn_pre_census. Designer's odds 0.08 / 0.10, P(no test) about 0.83. CH251/CH261
  fee-panel shift unexplained: q0717 runs before the freeze under a declared rule (CH252 withdrawn_pre_census (fee reading
  unresolved) if it stays unexplained; CH253 still censused). Census on LT12's worn span [11-07, 11-17); window 2027-01-21..02-11 (fast lane, pin before
  T_LT12); analysis on or after 2027-02-12T12:00Z. Tokens payreturn, batch, attrlimit_lt13 requested at the freeze.
- R1 GO_WITH_CHANGES (2026-10-28) applied in the second draft (section 12). Next: q0717, then the R1 re-check.
```

## 12. R1 response (2026-10-28; `reviews/LT13_CHALLENGER_R1_2026-10-28.md`, GO_WITH_CHANGES)
No line round 18 set is loosened by any change below; every threshold (0.25, 77, 5x, 60% / 20, 95%, 5%, 0.90, cap 30) is unchanged.

| R1 item | Applied where |
|---|---|
| Go / no-go: the map is not the census; `withdrawn_pre_census (map-informed)`, never `census_dropped` | top of file ("The map is not the census"), 0 (family bullet), 6 (census-fixed list (1)), 7.3 (four lists), 10 item 1, 11 |
| MUST 1: CH252 fails three round-18 lines (0.108; 5x at about 0.008; coverage 0.096) | top of file, 0 (survival priors), 2.4 ("Against the map"), 5 items 1-2, 11 (ledger block) |
| MUST 2: staged build (census code first; worlds, size check and analysis only for survivors) | status block steps 1-6, 5 item 12, 7 (build order), 7.4 steps 3, 5, 6 and the timetable |
| MUST 3: q0717's decision rule declared before it runs; run before retention; print covered span | 1.4.3 (hypotheses and rule (a)-(c) verbatim), 6 (census prints, expected fates), 7.5 (q0717 row), 9.1; code `backend/astrolabe/research_lab/lt13_fee_probe.py`, `backend/scripts/run_lt13_fee_probe.py`, spec `queue/jobs/q0717_lt13_fee_probe.json` |
| MUST 4: spline age condition (knots declared, none at 03-30); "fee-on/post-03-30 versus fee-free/pre-03-30 contrast"; M6 | 2.3 (age condition, wording, M6), 1.9 (condition (b), Supported text), 2.5, 5 items 2 and 4, 9.1 |
| MUST 5: no CH253 placebo change; cap 30; round 18's cap inconsistency disclosed | 3.4 (two bullets), 5 items 10-11, 10 items 4 and 8 |
| MUST 6: "can only lower" -> "expected to lower" | top of file (CH253 bullet), 3.4 |
| SHOULD 1: non-stationarity "each cell": rewarded cells print-only, and why | 6 (new bullet before the census prints) |
| SHOULD 2: world 1 under the label-permutation gate as a diagnostic | 1.8 (diagnostics) |
| SHOULD 3: `population_map_ch261.py:16` docstring | its own commit (docstring only; the q0701 output's code sha256 refers to the pre-fix file) |
| Rulings on 10 (1-10) | each item of 10 carries its ruling |

**Left for the re-check:** q0717's output and the reading rule (if any) it motivates under 1.4.3 (a), or CH252's withdrawal under
(b); the spline knots (2.3) and M6's definition; the staged-build wording (status block, 7).
