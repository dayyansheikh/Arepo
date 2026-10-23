# Live tests 12 (LT12): the mirror and the farmed half (CH245, CH244), DRAFT pre-registrations

**Status: FROZEN (design text) 2026-10-23, after challenger R1 (`reviews/LT12_CHALLENGER_R1_2026-10-23.md`, 59d2a158):
REVISE, the R1 response (section 13), the re-check (`reviews/LT12_RECHECK_2026-10-23.md`, b038afaa): ACCEPT_WITH_FIXES, its
fixes 1-7 (section 13.x), and the final pre-freeze verification: FIXES_REQUIRED (wording), fixes 1-5 applied in this freeze
commit (section 13.y). Not registered; E-numbers unassigned; nothing counted, no code, no seal, no census run. This file's
sha256 is recorded in `EXPERIMENT_LEDGER.md` (the file cannot hold its own hash).** Drafted 2026-10-23 on branch `feat/live-tests-12`
from the `chore/arepo-claude-setup` tip `1e89423d` (first draft fd9c425f, sha256 `64fe3e7b…2cac`), a design-only commit like
the first commits of LT3-LT11. **CH243 (the fee) was dropped after R1 (MUST 1; section 4); LT12 is now a family of at most
two tests.** LT12 takes the next free E-numbers at its own registration, in the order CH245, CH244 (round 17's rank order).
If both tests drop at their census, LT12 is not registered (recorded in the ledger; nothing counted). Before registration
this needs, in order:
1. the **final pre-freeze verification**, the acceptance this freeze rests on (done: FIXES_REQUIRED, wording only, applied in
   the freeze commit; the re-check's fixes 1-2 are confirmed again in code at the code-freeze check, step 3);
2. the **design-text freeze commit** (1.1): this commit, made 2026-10-23, before the LT12 seal commit, before `T_LT11` and
   before LT11's census commit (`T_LT11c`), so the fast lane stands and no *informed (LT11 census)* label applies; its sha256 is
   recorded in the ledger;
3. the code (section 8) with a `science-reviewer` freeze check of the census, gate and size-check code against 1.8, 1.8.1
   and 7, on synthetic data only;
4. the census inputs' restore and seal (7), each once, after the freeze and after the census span and its lag slots end;
5. the counts-only census (7), once, which fixes k and every census-fixed value named in 7;
6. the size check at 2,000 worlds on the code to be pinned (1.8), after the census values are committed;
7. a host dry run of the reader with peak RSS measured (8.2);
8. the embargo entries of section 9 verified in `config.EMBARGO` and `signal_engine/CANDIDATES.md`; `SPEC_SHA256` and
   `code_sha256` pins; the ledger entry, at least 24 h before `REGISTERED_UTC` (8.4).
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from round 17, the CH251 or CH240 maps, the ledger or the cost model is a **counts-only operational or
development figure, never a target**. Every MDE is a **planning estimate** on stated assumptions. Nothing here read a price
after an origin, an outcome, a target, a prediction line, a census output or a P&L. No host, network, `ssh`, `data-dumps` or
evidence-JSON read was used to write it (reads listed in 10).

**The CH251 map and what it informed (declared up front).** `CH251_MAP_2026-10-23.md` (q0700, captures [2026-10-13,
2026-10-23), 9.25 covered days, counts only, k = 0, uncounted) read captures k - 1 and k only: **no target, no price change
after an origin, no resolution, no P&L.** It was read before this file was written, so every gate near a map number is
*informed by the map*; section 6 marks each design change made after it [map] and 10.1 lists the values. The map's span is
disjoint from LT12's census span [2026-11-07, 2026-11-17) (7), so every LT12 gate is still declared before its own census on
a fresh seal. The map is a planning input only; nothing in it enters a census, the size check or an analysis.

Source ideas: `CREATIVE_HYPOTHESES_2026-10-31.md` (round 17) section 3, ranks 1-2 and their sketches: **CH245** (the mirror)
and **CH244** (the farmed half). Rank 3, **CH243** (the fee as the price of urgency), was in the first draft and left after
R1 (section 4). Written to round 14's rules 1-11, round 15's 12-14, round 16's 15-17 and round 17's 18-20, to LT4's lessons
L1-L15 and the rulings LT7-LT11 carry (1.0). LT12 reuses LT11's conventions (`LIVE_TESTS_11.md`, frozen at 3627d7fd) unless
a line here says otherwise and why.

## 0. Summary

| Handle | Hypothesis (direction, one-sided) | Unit of analysis (dependence) | Primary | Planning MDE low / high; quarter; F-MDE | Floor |
|---|---|---|---|---|---|
| **CH245** the mirror | **Conditional on a complete two-member neg-risk pair-capture whose two spreads differ at k - 1**, the **thin** (wider) book's spread change over (k, k + 1] rises with the **dense** (narrower) book's spread innovation over (k - 1, k], given the thin book's own innovation, the dense book's level at k - 1, the bid headroom at k - 1 and K (> 0); the dense book's slope on the thin book's innovation is < half (binding point condition); an unrelated pair's innovation has an absolute slope < half (binding two-sided placebo condition) | **one unit per asymmetric pair-capture** (the thin member; event-deduplicated by construction); no pooling of the two members; clusters event | expanding-past event x UTC day demeaned OLS of `ds_T` on `zs_D`; event-phase **state-shift** gate (one offset per event, demeaning re-applied every draw); F binding | 200 / 500 thin units a capture: DE 6 **0.32c / 0.20c** (quarter 0.64c), F 0.50c / 0.32c; DE 11 0.43c / 0.27c, F 0.68c / 0.43c; DE 31 0.72c / 0.46c, F 1.14c / 0.72c | 1.0c |
| **CH244** the farmed half | In a complete mixed ladder (3-10 members; mixed on the day-fixed carry status), after a sibling shock (largest sibling 2 h move >= 2 ticks) the **unrewarded** members' spreads widen more than the rewarded members' in the same event-day (`shock x unrew` > 0), tier x shock held; the within-event low-liquidity twin is < half (binding point condition) | member x capture; clusters event; DE 31 (formula) | expanding-past event x UTC day demeaned OLS of `ds_i` on `shock x unrew`; event-phase state-shift gate; F binding | 104 / 1,548 tested units a capture (four-cell variance): **0.83c / 0.26c** (quarter 1.67c), F 1.32c / 0.42c | 1.0c |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E022), LT5-LT11, E025 and E026. **Provisional k <= 2.** Each test is killable independently at
  its census; a failed gate drops it before registration (`census_dropped`, uncounted, final in both lanes); a test whose
  coverage check fails is `census_unavailable (coverage)` (7) and may be re-censused only in the ordered lane as its own Holm
  family. k is fixed in the spec (`k_tests`) at registration. A primary that is unavailable or fails its gate enters Holm with
  p = 1. No replacement test after a drop; **CH243 is not a replacement candidate** (section 4).
- **Window (fast lane, 1.1):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, **`REGISTERED_UTC =
  2026-12-10T00:00:00Z`**, `END_UTC = 2026-12-31T00:00:00Z`, 21 days; single analysis on or after **2027-01-01T12:00:00Z**.
  Census on a fresh seal of **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**. Freeze before the seal commit and before `T_LT11`.
- **Label certain in both lanes:** CH244 *informed (E022)* (E022's S2 reward split; the census follows `T_E022`).
  Lane-dependent labels: 1.1.
- **Honest survival priors (the designer's judgement after the CH251 map and R1, not measurements; round 17's in brackets).**
  **CH245 0.30 [0.30]:** the map removed the round's main risk (639 complete pairs a capture against 100-400 events planned;
  receipt-span retention 1.000; completeness 0.97-1.00), but showed that the two books move together in the same slot (pooled
  same-slot correlation 0.64 on unrewarded pairs, 0.38 on rewarded pairs), which feeds the same-slot correlation gate and the
  `VIF_w` gate. R1 replaced the identification gate (MUST 4; the redefined gate tests within-stratum variation and leverage,
  which the map never probed) and tightened the placebo to two-sided with a series-family and event-id rule (MUST 5; an
  analysis condition, not a census gate, plus a coverage gate). Same level, different composition. **CH244 0.15 [0.20]:** R1
  SHOULD 5 asked for a revert to 0.20 or a justification; the designer reverts and lowers further. The map's counts used the
  simple reading (`clob_rewards` non-empty at k), the low planning count (104 tested units a capture) is under the gate (362),
  and R1 MUST 3 adds a feed-disagreement gate on an unprobed share whose evaluation needs the reward feed's coverage (7). The
  map's weak status-liquidity correlation (-0.05 / -0.09) is no longer counted in CH244's favour: if the omission of
  `clob_rewards` makes status partly noise, a weak correlation is what noise produces. **Expected k at census about 0.45;
  P(no LT12 test) about 0.60** (0.70 x 0.85, treating the fates as independent, which they are not: both read the same event
  join and captures). **Expected valid verdicts about 0.2 (re-check fix 6; derived, a judgement):** a valid verdict is a
  registered test that passes its size check and is not Unavailable; P(size check passes | registered) about 0.5 for CH245
  (worlds 2 and 4 are the expected risks, 1.8) and 0.6 for CH244 (world 9), P(not Unavailable | both) about 0.9, so 0.30 x 0.5 x
  0.9 + 0.15 x 0.6 x 0.9 = 0.135 + 0.081 = 0.216. Every taker cell is expected "not shown".
- **No LT12 result can satisfy the programme's economic check** (1.10). A Supported LT12 primary is an exploratory prospective
  finding, never an edge.

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)
`LIVE_TESTS_11.md` 1.0 applies unchanged (LT4 L1-L15; LT7-LT10 rulings; exact `%.17g` writes; NaN refusals; sealed census
inputs re-hashed; slots from the seal; pessimistic planning-MDE gate `max(declared, design)` with `sqrt(max(1, VIF_w))`; size
check >= 2,000 worlds with limit 0.058; spec and code pins; write-once series; clustering by event, event x UTC day and UTC
day with p the largest; Holm counted once; economics never changes a verdict; block (circular-shift) gates for rolling or
persistent states; `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`; liquidity correlation gates; the lag-slot loader; `T_X`
conditions; the pinned sports and crypto classifiers; LT7's one-rule F; `r_gate = max(r_w, r_pool)`; count gates on gross
projected counts; **whether F binds is fixed per test now, by design, and a label-only F chosen for power is rejected (LT11 R1
A4, applied to CH243 by LT12 R1 MUST 1)**; `listed_carry24h_v2` for every reward status; distinct-event gates unprojected;
`census_unavailable (coverage)` distinct from `census_dropped`; Kish `G_eff >= 15`). Lessons (i) and (ii) of LT11 1.0 bind:
every count gate is at or above the binding kill line at the base planning values, and every share gate is either measured by
the map (margin stated) or flagged unprobed (10.1).

Round 17's rules map onto LT12 as follows (rules 1-17 as in LT11 1.0's table, applied to these units):

| Rule | LT12 rule |
|---|---|
| 1. Panel-complete units | every unit is a market x capture of the complete captures and their sidecar; no sweep, sample or monitor in any primary |
| 3. Innovations, not levels | CH245 the dense book's spread change over (k - 1, k]; CH244 a sibling move at (k - 1, k]; every level is a control |
| 5. Field semantics first | 1.4.1 (the three reward-status cases), 1.4.2 (tier from `liquidity`), 1.4.3 (event key, pair and ladder completeness, series family) |
| 7. DE and kill line | planning DE 6 / 11 / 31 (CH245), 31 (CH244); census `max(5.0, computed)`; kill lines stated per test |
| 8. Floors | 1.0c (both spread targets); the F-MDE cap equals the floor |
| 9. Fresh seal | `[2026-11-07, 2026-11-17)`, disjoint from the CH251 and CH240 map spans, LT11's census seal and LT11's window |
| 11. Maker-side money routes | every primary route is maker-side, gross, no fills; taker cells reported (1.10) |
| 16. Event-join completeness | CH245 pairs and CH244 ladders complete at k - 1 and k with the 120 s receipt span at both; incomplete ones counted, never filled |
| **18. The mirror rule** | CH245's state is the twin book's innovation on pair-captures complete at k - 1 and k; the twin's level (at k - 1) and the own innovation are controls; demeaning stratum event x UTC day, re-applied on every gate draw (1.8); the unrelated-pair placebo is a binding two-sided point condition (2.3) and a binding size world (1.8 world 3) |
| 19. Third price | not used (CH242 was killed at its own census on 2026-10-23) |
| 20. Fee class is a panel | not used: CH243 left LT12 (section 4); its panel reading returns to the engine |

### 1.1 Registration, window, single analysis
- **Fast lane (proposed).** `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT12 registration commit
  (spec pin plus ledger entry), **(b)** at least 24 h after the END_UTC of LT11's fast-lane window (2026-12-09T00:00Z), and
  **(c)** never earlier than **2026-12-10T00:00Z**. Proposed **2026-12-10T00:00Z**; `END_UTC` 2026-12-31T00:00Z; analysis date
  `END_UTC + 36 h` = 2027-01-01T12:00Z. Requirements: the design-text freeze **before the LT12 seal commit and before `T_LT11`**
  (LT11's analysis, proposed 2026-12-10T12:00Z), and the registration commit **before 2026-12-09T00:00Z**; else the fast lane
  lapses (recorded) and never slides day by day (a later start runs into LT9's window and the year-end). The *lapse time* is the
  earlier of the ledger line recording the lapse and 2026-12-09T00:00Z.
- **Ordered lane (fallback, declared now).** `REGISTERED_UTC` = the first 00:00Z at least 24 h after LT9's `END_UTC` (or its
  recorded drop) and after the LT12 registration commit, never before **2027-01-22T00:00Z**; 21 days; single analysis >= 36 h
  after the end. It needs a fresh seal and census of the 10 UTC days ending at least 4 days before the registration commit,
  disjoint from LT11's registered window, with every gate and value rule of 7 unchanged; fast-lane census outputs become
  descriptive; `census_dropped` stays dropped; `census_unavailable (coverage)` is re-censused as its own Holm family.
- **Adjacent analyses and labels (`T_X` = the earlier of X's analysis job start and X's analysis commit; `T_LT11c` = the earlier
  of LT11's census job start and its census commit, planned about 2026-11-08..11-12).**

  | Test | Adjacent (`T_X`) | Why | Consequence |
  |---|---|---|---|
  | CH245, CH244 | **LT11 census** (`T_LT11c`) | LT11's census prints CH233's two-member arm and completeness by size and status (counts) | freeze after `T_LT11c`: *informed (LT11 census)*, counts only; freeze before it: disclosed, no label |
  | CH245, CH244 | **LT11** (`T_LT11`) | LT11's two-member arm (CH233) and the same 3-10 member events and spread target | the fast-lane pin precedes `T_LT11` by construction; any pin after it (ordered lane): *informed (LT11)* |
  | CH244 | **E022** (`T_E022`, about 2026-11-17T12Z) | E022's S2 splits traded movers' depth by reward status | *informed (E022)* in both lanes, certain |
  | CH244 | **LT9 CH213** (window from 2026-12-30) | the rewarded panel and `listed_carry24h_v2` | time overlap of at most one day; different states; no pooling |
  | all | LT10, E026 (to 2026-12-07), LT9's reader | time only | different streams or states; no pooling |

  If LT11's window is not the fast-lane window (LT11 lapsed), "LT11's window" in this file means LT11's registered window, and
  LT12's census span and window must be disjoint from it.
- **Boundary.** A unit's oldest state input is capture k - 1, so the first origin is the first capture whose capture k - 1
  starts at or after `REGISTERED_UTC` (proposed 2026-12-10T02:31Z); earlier captures give no unit (`lt12_boundary`). Look-backs
  (`rv24*`, 6 h and 24 h changes, the 12-slot carry window) may read captures of 2026-12-09 (counted `pre_window_source`, the
  count printed in the analysis; R1 ruling A15). Those captures lie after LT11's `END_UTC`; LT11 reads some of them as target
  or twin slots of its last origins. LT12 reads them as raw rows and sidecars only and computes none of LT11's objects. The
  last origin is the last capture starting before `END_UTC`; its targets (k + 1) and twins (k + 3) are read.
- **Design-text freeze.** After the acceptance of the final pre-freeze verification (which followed R1 and its re-check), a
  commit records this file's sha256 in the ledger.
  Afterwards the text changes only by the census-fixed values named in 7 and by code-freeze-check fixes that change no state,
  unit, target, estimator, gate, threshold or verdict rule. The embargo requests of 9 are filed at the freeze.
- **Fixed end, no extension; one analysis** (`run_live_tests12.py analyze` refuses before the analysis date; `--out` refuses
  to overwrite). Effective start = max(`REGISTERED_UTC`, the first capture processed by the reader at the pinned commit); only
  lines whose `spec_sha` and `code_sha` equal the pins and whose role is `prospective_confirmation` are kept.
- **Time of year (disclosed).** No DST change in the census span or the window. The census span follows the US midterm
  (2026-11-03) and its resolution days 11-04..11-06, so it measures the post-midterm two-member panel, which is the one December
  will hold. The window holds the holiday fortnight: a sensitivity without origins in `[2026-12-24T00:00Z, 2026-12-27T00:00Z)`
  is reported (*holiday-sensitive*); no gate depends on activity level (R1 ruling A16: no change).

### 1.2 Streams read (all already written by the host's pass; no new collector, no network)
- **Captures** `snapshots/<id>/rows.csv.gz` (`state=complete` only): `bid`, `ask`, `spread`, `last_trade_price`, `volume24hr`,
  `liquidity`, `chg_1h` (and `chg_1d`, `chg_1w` if the header pre-check finds them), `end_date`, `event_id`, `neg_risk`,
  `neg_risk_market_id`, `neg_risk_other`, `event_neg_risk_augmented`, `closed`, `active`, `received_utc`, the manifest start.
- **Sidecar** `rows_ext.csv.gz`: `received_utc`, `fee_type`, `fee_category`, `series_slugs`, `order_price_min_tick_size`,
  `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, `volume_num`, `accepting_orders`, `event_ids`. An **absent sidecar
  row** sets category and tick unknown (the unit or event is excluded, counted `sidecar_missing`) and the reward status NaN
  (case (c) of 1.4.1); an empty `clob_rewards` cell on a present row is case (b), never NaN.
- **CLOB reward feed** `reward_params/<capture_id>/`, read only for CH244: the census's feed-disagreement gate and its coverage
  (7; R1 MUST 3), the analysis's CLOB-agreement sensitivity, and economics. Feed clock: the last usable feed capture whose start
  is before capture k - 1's start and at most **6 h** earlier (else the unit is `feed_uncovered`, counted). Feed coverage under
  50% of tested units (an outage included) makes CH244 `census_unavailable (coverage)`; a feed-listed share above 0.20 on
  adequate coverage makes it `census_dropped` (7; re-check fix 3). Never a state, control or target.
- **Not read:** sweeps, trade samples, the monitor, `cross_venue_live/`, `xv_quotes/`, `surprise_live/`, the stores
  `live_tests2/` .. `live_tests11/`, CB8-H holders, CB16-CB18, E025 and E026 stores and the **E026 frozen modules**, the keyless
  streams, `gamma_rules`, the engine's `quotes/`, `features/`, `aux/`, `predictions/` and label store, the CH240 and CH251 map
  outputs, Gamma outcome fields of any kind. **LT11's objects (`xw`, `cl_sib`, `xo`, their twins and targets) are never
  computed or read; LT11's window captures `[2026-11-18, 2026-12-09)` are read by no LT12 census, size check or test.** J4-R
  `[2026-10-16, 2026-10-21)` and CB13-T's holdout `[2026-10-21, 2026-10-26)` are refused for maker mark-out objects; LT12 holds
  none and its spans do not touch them.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3-LT11 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot); "k - j" and
  "k + h" are slots; a missing slot leaves every quantity that needs it NaN (counted), never interpolated.
- **Decision time (both): capture k's last row receipt** (the largest `received_utc` over capture k's complete rows and sidecar
  rows): CH245 reads two rows of capture k, CH244 every member of an event. States read captures k - 1 and k and the 12-slot
  look-back. **Targets start at capture k + 1.**
- **Within-capture receipt order (LT11 MUST 1's rule):** a pair or ladder whose eligible members' `rows.csv.gz` `received_utc`
  span exceeds **120 s** at k - 1 or k gives no unit (`receipt_span`, counted). The residual overlap (at most 120 s of a 2 h
  target) is disclosed, and size world 2 (S31) plants the leak it could carry.
- **Late rule** as LT4 1.3 (*late-loss* above 2%). **Twins (F)** read captures k + 2 and k + 3 through the lag-slot loader; the
  unit builders do not read them (causality test, 8.3).

### 1.4 Shared origin-side eligibility
LT11 1.4 applies (vendored `move_join`, `classify`): binary, open, active; two-sided at k - 1 and k (bid > 0, ask < 1); tight
(spread <= 0.10 at both); end unknown or > `t` + 3 h (F arm: > `t` + 7 h, else `f_end_short`); category by
`cb17_census.is_sports_sidecar` (non-sports primaries; sports arm reported, uncounted); crypto excluded by the pinned
classifier (unknown counted and treated as crypto); `scope: non_sports_ex_crypto` fixed at the freeze unless an owner decision
is recorded before it; one row per `condition_id`; tick equal at k - 1 and k (`tick_changed`); series-family rule (the census
top family holding > 40% of a primary population is excluded, `<test>.exclude_family`), with the series family of 1.4.3.

### 1.4.1 Reward status: the three cases of `listed_carry24h_v2` (R1 MUST 2)
Every `rewarded` flag is **`listed_carry24h_v2` exactly as `LIVE_TESTS_7.md` 13.7 and its erratum define it**, vendored from
`live_tests7.py` (sha256 `e1c5c0c6…`). For a market at a **status capture** s (CH244: s = k - 1; the K control `rewarded_k`
of both tests: s = k), with the causal window of 12 slots `[s - 11, s]`:
- **(a) Listed at s:** a parseable `clob_rewards` text at s is parsed at s: summed daily rate > 0 gives `rewarded = 1`; rate 0
  gives `rewarded = 0` (`rewards_listed_inactive`, counted).
- **(b) Null at s** (an empty cell on a present sidecar row: an absent key and a JSON null both write an empty cell): `rewarded
  = 1` if any **listed** text at a sealed capture of the window gives a summed daily rate > 0 when re-parsed for the UTC day of
  s (the latest such capture is the source; `rewards_null_carried`); **otherwise `rewarded = 0`** (`rewards_null_as_zero` when
  nothing is listed in the window, `rewards_null_window_listed_inactive` when only rate-0 texts are). A window slot with no
  sealed capture is skipped and counted (`reward_window_slots_missing`), never filled; no slot after s is read.
- **(c) NaN** only for a **malformed** `clob_rewards` cell at s or an **absent sidecar row** at s (excluded, counted); no earlier
  malformed text is read as listed.
**Disclosure (R1 MUST 3):** case (b)'s "otherwise 0" treats a field that Gamma omitted for 24 h as unrewarded. LT7 13.7
recorded 30,543 of 258,393 market-days switching between null and non-null within a day and read the omission as Gamma
leaving the field out; whether omission persists for 24 h on a rewarded market is **not measured**. CH244's census therefore
prints the carry-against-simple confusion and gates the share of carry-unrewarded tested units that the CLOB feed lists (7).

### 1.4.2 Liquidity tier (defined from capture fields; the map found no tier definition)
`tier_{i,j}` = the cost model's liquidity bins (`COST_MODEL.md`, `cost-model-v1`) applied to the row's `liquidity` at capture
j: `< $1k`, `$1k-10k`, `$10k-100k`, `>= $100k` (four classes; a missing `liquidity` is NaN, excluded, counted). It is read at
k - 1 for CH244's tier x shock control and at k as a K control. No other tier exists in LT12.

### 1.4.3 Neg-risk event key, completeness and series family (CH245, CH244; LT11 3.2 vendored)
Event key `neg_risk_market_id` where present and non-empty, else Gamma `event_id` among `neg_risk` rows (`nr_key_conflict`
counted, keyed by `neg_risk_market_id`). Eligible members at capture j: rows with the key, `neg_risk` true, binary, open,
active; "Other" and placeholders are members. An event with any eligible member `event_neg_risk_augmented` true (or missing)
at k - 1 or k is outside both primaries (`augmented`; a reported arm). **Pair- or ladder-complete (k - 1, k):** identical
member set at k - 1 and k (`members_changed`), every member two-sided at both (`event_incomplete`), member receipt span <= 120 s
at both (`receipt_span`); sports, crypto or unknown category on any member excludes the event. Incomplete event-captures give
no unit for any member; nothing is filled, no bid set to 0, nothing carried. `tick_e,j` = the largest member tick at j.
**Series family** of a market: the first entry of its sidecar `series_slugs` after strip and casefold; an empty value gives the
singleton family `none:<event key>`. **Event-id set** of a market: its sidecar `event_ids` (parsed as a set of strings) plus
its row `event_id`; empty if neither is present (counted `event_ids_missing`).

### 1.5 Missing data, per-capture status and attrition (never imputed)
As LT11 1.5: every frozen unit receives one write-once status at every target slot (`two_sided`, `one_sided`, `closed_flag`,
`absent`, `capture_missing`); only `two_sided` has a target (CH245: the thin member's row at k + 1; CH244: the member's row).
Indicator-pair exceptions only as LT11 1.5 (`hte_unknown`, `vol_missing`, `mom_missing`, `chg1d_missing`, `chg1w_missing`).
`volume_num` is used only by CH244's reported M3 (a counted `unknown` class, never inferred). A missing state or control is NaN
(excluded, counted), never 0. A missing F state leaves the unit in the primary and out of the F arm. **Attrition rule:** |a_1 -
a_0| > 2 pp in target availability between the contrasted groups (CH245: top against bottom census tercile of `zs_D`; CH244:
unrewarded against rewarded members on shock captures) gives *attrition-differential* and Lee-type bounds, never a verdict
change.

### 1.6 What is not looked at before the analysis date
No mid, spread, move, target, P&L, regression or plot from `live_tests12/` files or in-window captures for these hypotheses;
only `run_live_tests12.py ops-stats` (file, line, role, class, panel and status counts; reads no price, spread, volume or
liquidity column; unit test). No change of thresholds, scales, populations, estimators or k after registration. **No LT12
designer, coder or reviewer reads E015's, E022's, LT9's, LT10's or LT11's analysis outputs before the pin, nor LT11's census
output before the freeze** (after it, any change carries *informed (LT11 census)*). **Census-span data:** nobody opens any
capture, sidecar or feed capture of the census inputs (span, look-back, lag slots) before the seal commit, except the header
pre-check (headers only) and the restore's byte and sha256 checks; development uses synthetic data or files outside those slots.

### 1.7 Estimators, units of analysis and inference
- **Sign convention.** Every tested coefficient is predicted > 0; every MDE a magnitude.
- **Units of analysis (dependence-aware, declared now).** CH245: **one unit per asymmetric complete pair-capture** (the thin
  member), so the two near-duplicate targets of a pair in one slot are never both in a model; the estimand is **conditional on
  asymmetry at k - 1** (a causal selection on the k - 1 spreads; R1 ruling A2), and the two members are never pooled; the dense
  member is the point condition's unit on the same pair-captures. CH244: member x capture (the contrast is within
  event-capture); the reported event-capture aggregate (mean `ds` of unrewarded minus rewarded members per event-capture,
  regressed on `shock`) is the deduplicated sensitivity. In both the inference cluster is the event.
- **Expanding-past demeaning** (LT2-LT11): each regressor minus the mean of the stratum's strictly earlier units of the same
  test; target raw; the first unit of each stratum drops. **Demeaning stratum (both tests): event x UTC day** (rule 18 and round
  17's sketch). The gate re-applies the same demeaning on every draw (1.8).
- **Known-factor block K** (LT11 1.7 unchanged): `p_k`, spread_k, `log1p liquidity`, `log1p volume24hr` (`vol_missing`), log hours
  to end (`hte_unknown`), `1[tick = 0.001]`, `z log rv24*`, `rewarded_k` (1.4.1 with s = k), non-sports `fee_category` dummies,
  11 slot-of-day dummies, own `d_k`, own 6 h and 24 h changes (`mom_missing`), `chg_1h` (and `chg_1d`, `chg_1w` as indicator
  pairs if the header pre-check finds them; committed before the seal). `neg_risk` is constant within both tests and dropped.
- **Standard errors and p (L10):** CR1 on event, two-way event x UTC day, and UTC day; one-sided **p = max(p_event on t with
  `G_event - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**; conservative 95% CI = hull of a 2,000-draw event
  bootstrap and the three Wald intervals; `G_eff` printed beside `G_event` and floored at 15.
- **Dependence sensitivities (reported, never the verdict):** event x two-day block CR1; the fixture-day group
  (`DEPENDENCE_CLUSTERING_ANALYSIS.md`'s `fixture_day_sidecar`) in place of the event; the deduplicated estimates above; the
  both-demeaned refit (LT6); a market-demeaned refit.
- **Rolling states.** CH245: the dense member's innovation over (k, k + 1] is the next unit's state and overlaps this unit's
  target interval, and the two books co-move in the same slot (the map's 0.38-0.64), so the state at k + 1 is correlated with
  the target at k. CH244: the siblings' moves over (k, k + 1] are the next unit's shock and move the member's spread at k + 1.
  Both are rolling (LT7): block gates and **F binding for both**.

### 1.8 Gates (valid within-unit nulls) and their size
- **Event-phase state-shift gate (both tests; R1 MUST 6).** A new wrapper `event_day_state_shift_gate` in `live_tests12.py`,
  built from LT5's `block_fl_gate` offset rule and LT11 CH233's event-phase index (vendored by hash) but **not** "vendored
  unchanged", because LT12 demeans by event x UTC day while LT11 CH233 demeaned by market. For each of 200 draws and each event
  e: `I_e` = the ordered captures at which e has at least one unit of the test, `n_e = |I_e|`, `s_e = max(4, ceil(n_e / 4))`,
  one offset `o` drawn from `[s_e, n_e - s_e]`. **Gate sample (re-check fix 1):** the units of events with `n_e >= 16`; events
  with `n_e < 16` are excluded from the gate (counted), and **the observed statistic is refitted on that same gate sample**, not
  taken from the primary fit on all units. **The raw state is
  shifted, never a demeaned value:** CH245 the unit at index position t receives the raw `zs_D` of position `(t + o) mod n_e`;
  CH244 every member's raw `shock` and `shock_size` at position t are replaced by that member's values at `(t + o) mod n_e`, and
  `shock x unrew` and `tier x shock` are recomputed from the shifted shock with the unit's own `unrew` and tier. **Then the
  expanding-past event x UTC-day demeaning is re-applied** to every shifted regressor in each unit's real stratum and real
  order; every other regressor and the target keep their analysis values; the full model is refitted on the gate sample and its
  tested statistic stored. **Statistic (re-check fix 1):** the tested coefficient's **event-clustered CR1 t** (clusters = events
  of the gate sample; the CR1 small-sample factor of 1.7), computed identically for the observed fit and for every draw. A
  member lacking a unit at the shifted position is omitted from that draw (never filled, never borrowed); the omitted share is
  printed. One-sided `p_perm = (1 + #{t_draw >= t_obs}) / 201`, both t's the gate-sample CR1 t; the gate passes if `p_perm <
  0.05`. Reason for shifting the raw
  state rather than LT5's reduced-model residuals: the demeaning stratum (event x day) is finer than the shift stratum (the
  event), so a shifted demeaned value would carry another day's stratum means into this day.
- A failed gate on data gives p = 1 in Holm and "SE check failed (gate on data)".
- **Size check, after the census.** `size-check` runs once on the code to be pinned, **2,000 worlds x 200 draws, seed
  20261597**, limit **0.058** (= 0.05 + 1.645 sqrt(0.0475 / 2,000)); **worlds 1-5 and 7-9 run the gate through
  `event_day_state_shift_gate` exactly as the analysis does** (raw shift, demeaning re-applied every draw, the gate-sample refit
  and its event-clustered CR1 t, same minimum and omission rule); a world is generated once and evaluated under each test it binds. No effect of the tested term in any world.

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | **S30:** common event volatility shock widening both books in the same slot, AR persistence, no lag effect | state-shift | CH245 | gate |
  | 2 | **S31:** one bot quoting both books with a sub-slot lag; the capture catches some updates half-done (receipt gaps from the census) | state-shift | CH245 | gate |
  | 3 | **S32:** a venue-wide spread factor loading on every pair ("any innovation anywhere predicts the spread") | state-shift | CH245 | gate |
  | 4 | **thin selection:** both books AR(0.7) around their own means, thin chosen at k - 1 (regression to the mean), no cross-book effect | state-shift | CH245 | gate |
  | 5 | **liquidity leak (CH245):** the thin book's reversion speed and the dense book's innovation variance share a latent liquidity seen noisily | state-shift | CH245 | gate |
  | 6 | **M-Q (CH245):** a slow event drift raising both books' spreads before and after the target | none | CH245 | verdict size |
  | 7 | **S26 (CH244):** a common event shock moving every member's mid and spread in the same slot, statuses random, no lag | state-shift | CH244 | gate |
  | 8 | **S27:** a dormant ladder whose only mover is the favourite; unrewarded status concentrated on longshots; longshot spreads revert | state-shift | CH244 | gate |
  | 9 | **S34:** post-shock widening proportional to 1 / liquidity, status correlated with liquidity at the census's measured within-event correlation; the model sees noisy tiers | state-shift | CH244 | gate |
  | 10 | **M-Q (CH244):** a slow event drift raising shocks and unrewarded spreads before and after alike | none | CH244 | verdict size |

  **Verdict size** (6, 10) = the share of worlds in which the analytic one-sided p (1.7) is < 0.05 **and** F and the test's point
  conditions (1.9) hold; the gate is omitted. Criterion <= 0.058.
- **Diagnostics printed beside the size check (not size criteria):** a planted-effect power run per test (500 worlds; CH245 1.0c per census tercile gap of
  `zs_D`, CH244 1.0c between classes on shock captures; seeds `20261597 x 100 + 51, 52`); and **world R1, the symmetric
  lead-lag (R1 SHOULD 1):** 500 worlds at seed `20261597 x 100 + 54`, world 4's pairs with each book's next spread change
  loading 0.4 per SD on the other book's innovation in **both** directions (no thin-dense asymmetry) and the 1c spread floor
  enforced on both books; reported statistic: the share of worlds in which the dense-twin point condition `betâ_dense < 0.5 x
  betâ_thin` holds on the full set, on the dense `spread_k >= 2` ticks set, and on both together (the binding form since
  re-check fix 7; the floor alone can make the dense book look like a non-follower, because a dense book at one tick cannot
  narrow).
- **Consequence of a failure:** a failing scenario makes only the tests it binds "SE check failed (size scenario)" (1-5, 7-9)
  or "SE check failed (mechanical world)" (6, 10): p = 1 in Holm, **k unchanged**, no rerun, reseed, redesign or variant;
  `max_retries 1` for a deterministic crash only; no preliminary run at seed 20261597. **Expected:** worlds 2 and 4 may fail for
  CH245, world 9 for CH244; the rest are expected to pass.

### 1.8.1 Simulated worlds (declared now; census inputs only where named)
Common: units on a 2 h grid, `day = i // 12`, `block2 = day // 2`; 200 draws per world at a fresh sub-seed from one generator
seeded 20261597, scenarios in table order; spreads in cents on a 1c grid with a 1c floor; every world fits the test's primary
model with K replaced by the simulated controls named; in every world 10% of member units are removed at random after
generation (exercising the omission rule); every world assigns each event a series family and event-id set so that the
placebo rule of 2.3 can be applied (worlds 1-6: 40 families, events assigned uniformly).
- **1 (S30):** 300 two-member events, **`n` uniform on 8..252 captures** (re-check fix 2: the range includes 8..119, so events
  with `n_e < 16` occur and the gate's exclusion and refit-on-the-gate-sample rule are exercised); an event volatility state
  `v_t` AR(1) rho 0.8 (stationary SD 1); each book's spread `s_{b,t} = max(1, round(2 + lambda x v_t + u_{b,t}))`, `u` AR(0.5)
  iid across books (SD 0.8c); both books load on `v_t` in the same slot; the model sees `z log rv24` = `v_t + N(0, 0.7^2)`; no lag
  effect. **Loading `lambda` (re-check fix 2):** set so that the planted within-event same-slot correlation of the two books'
  spread innovations (after rounding and the floor) equals **`rho_ss = max(rho_census, 0.64)`**, `rho_census` the census pooled
  same-slot correlation on CH245 thin units (census-fixed, 7); `lambda` is found by bisection on [0, 10] to within 0.005 of
  `rho_ss`, each step a calibration run on **a single two-member event of 20,000 slots** generated as world 1 at seed `20261597 x
  100 + 61` (no size-check world is generated by it), after the census values are committed and before the size check;
  `lambda` is recorded beside the size-check results. **Failure rule (final verification fix 3):** if `rho_census` is NaN, if
  `rho_ss` is not bracketed by the calibration correlations at `lambda = 0` and `lambda = 10`, or if the tolerance is not reached
  within **40** bisection steps, world 1 is not run and its outcome is **"SE check failed (size scenario)" for CH245** (1.8's
  consequence; no other bracket, step count, seed or loading is tried); world 2 has no `v_t` and is unaffected; world 3
  inherits `lambda` and then fails the same way. Worlds 2 and 3,
  built from world 1, inherit its `n` range (and world 3 its `lambda`).
- **2 (S31):** world 1 without `v_t`; one quote model per event moves both books' spreads by the same step at a Poisson time
  (rate 0.4 a slot); book B updates at that time and book A after a lag `L ~ Exp(mean 60 s)`; each capture reads the two rows
  at times differing by `g`, drawn from the census's receipt-gap distribution between pair rows (its q50 and q90, census
  input; floor q50 5 s), with the row order random; a step whose update window straddles the read appears in B at k and in A
  at k + 1; no other effect.
- **3 (S32):** world 1 plus a venue-wide factor `F_t` AR(1) rho 0.8 (SD 0.6c) added to every book of every pair; the model sees
  slot-of-day dummies only; the placebo pair is drawn by 2.3's rule; no event-specific lag effect.
- **4 (thin selection):** each book's spread AR(1) rho 0.7 around its own mean (means `2 + 2 x Exp(1)` c per book, SD 1c);
  the thin member chosen at k - 1 by 2.2's rule; no cross-book effect; the model's controls as 2.3.
- **5 (liquidity leak, CH245):** world 4 with the thin book's reversion `rho = 0.9 - 0.3 Phi(L_e)`, `L_e ~ N(0, 1)` per event,
  and the dense book's innovation SD scaled by `exp(0.5 L_e)`; the model sees `L_e + N(0, 0.5^2)`.
- **6 (M-Q, CH245):** world 4 plus `mu_t` AR(1) rho 0.99 (stationary SD 0.5c a slot) entering the thin book's target and, with
  loading 0.3 per SD, the dense book's innovation at k and its twin at k + 3.
- **7 (S26, CH244):** 200 events of 3-10 members (uniform), **`n` uniform on 8..252** (re-check fix 2; worlds 8-10 inherit it);
  member mids `m_{j,t} = m_j + e_t + w_{j,t}`
  with a common event shock `e_t ~ N(0, (1.5c)^2)`; spreads `max(1, round(2 + 1.5 x |e_t| + AR(0.7) noise))` in the same slot;
  each member unrewarded with probability 0.5 independently (at least one of each status per event), status fixed per member;
  shock by 3.2's rule; no lag.
- **8 (S27):** world 7 with all moves on the favourite (rank 1), longshots static up to noise, longshot spreads AR(0.8) around 3c;
  the favourite rewarded with probability 0.8, longshots 0.4.
- **9 (S34):** world 7 with member liquidity `L_j ~ N(0, 1)`; post-shock spread change `E[ds] = 0.8c x exp(-0.7 L_j) x shock`;
  unrewarded status drawn so that the within-event correlation of `unrew` and `L_j` equals the census's measured value (census
  input; floor |0.20|); the model sees tiers cut from `L_j + N(0, 0.5^2)` at its quartiles; no status effect.
- **10 (M-Q, CH244):** world 7 plus `mu_t` as world 6 entering unrewarded members' targets and, at 0.3 per SD, the shock
  propensity before (k) and after (k + 3).

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **F rule (LT7's, unchanged).** The arm model is the primary with the far-future twin added, on units that have it.
  `Δ = beta(lead) - beta(twin)`; **F holds iff Δ's one-sided p < 0.05 (1.7 rule; not Holm-adjusted; counted 0) and Δ̂ >= 0.5 x
  betâ_primary**; an arm with < 50% of the primary's units is *falsification unavailable*. **F binds for both tests, fixed now by
  design** (rolling states, 1.7). Twins: CH245 `zs_D` over (k + 2, k + 3] for the same pair and the same dense member, NaN unless
  the pair is complete at k + 2 and k + 3 (1.4.3); CH244 `shock x unrew` with the shock over (k + 2, k + 3] on ladder-complete
  pairs at k + 2, k + 3.
- **Point conditions (binding, fixed now; estimates only, no test, counted 0).** CH245 **(a) dense twin, on two sets
  (re-check fix 7):** the model on the dense members of the same pair-captures (state the thin member's innovation, mirrored
  controls) has **betâ_dense < 0.5 x betâ_thin on the full set and also on the set of pair-captures with the dense `spread_k >= 2`
  ticks** (each set's `betâ_thin` from the primary refitted on that set); both must hold; if the `>= 2` ticks set holds fewer than
  5,000 units (a quarter of the 20,000-unit Unavailable floor) condition (a) cannot be shown and the primary is at most
  Inconclusive (*dense-twin unavailable*); **(b) placebo, two-sided (R1 MUST 5):** the primary with `zs_D` replaced by the unrelated pair's `zs` (2.3) has
  **|betâ_placebo| < 0.5 x betâ_thin**. CH244: the twin model with `lowliq` and `shock x lowliq` in place of `unrew` and `shock x
  unrew` (3.3) has **betâ_lowliq < 0.5 x betâ_unrew**. Each difference's one-sided p is reported as a label.
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate > 0, gate passed, F holds, every point
  condition holds. Else, with everything else holding: F fails or unavailable -> **Inconclusive** with *mechanical null not
  excluded* (or *falsification unavailable*); a point condition fails or cannot be shown -> **Inconclusive** with *not
  thin-specific* (or *dense-twin unavailable*), *placebo not null* (CH245) or *not status-specific* (CH244).
- **Contradicted:** the conservative 95% CI lies entirely below 0. **Inconclusive:** otherwise. **Unavailable:** CH245 < 20,000
  thin units, < 300 events, < 100 events with >= 48 units, or the placebo defined on < 50% of thin units; CH244 < 20,000 tested
  units (unrewarded x shock) or < 20,000 rewarded shock units, < 300 events, < 100 events with >= 48 units; both: Kish `G_eff` <
  15 or < 10 UTC days with units.
- **Labels (never change a verdict):** *material* (>= 1.0c at the census tercile gap of `zs_D` for CH245; >= 1.0c for CH244);
  *thin-difference significant*, *status-difference significant*; *informed (X)*; *analytic p oversized in simulation*;
  *underpowered* (as LT11); *attrition-differential*; *late-loss*; *series-concentrated*; *holiday-sensitive*; **bid-sum
  mediated** (CH245: M4, the refit with the bid headroom at k, `hb_k`, in place of `hb_{k-1}`, drops the estimate below half; R1
  SHOULD 7: since own spread at k is in K and `g_ask,k = spread_T,k - hb_k`, `g_bid,k = spread_D,k - hb_k`, the round's k-level
  mirror gaps differ from LT12's k - 1 basis only through `hb_k` and the state itself, so this is a bid-sum mediation label, not
  a general mirror-gap one); *receipt-order sensitive* (CH245: the refit on pairs with the thin row
  received before the dense row at k changes sign); *ladder-dominated* (CH244: the 11+ arm has the opposite sign);
  *CLOB-disagreement sensitive* (CH244: the refit on members whose carry status and feed listing agree changes sign);
  *liquidity-shared* (CH244: in the joint model of 3.3, `shock x unrew` falls below half its primary value; R1 SHOULD 3).
- **MDE multiplier** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (LT7-LT11), not lowered for k <= 2.

### 1.10 Economics (separate; descriptive; never changes a verdict)
- **Maker routes (gross, an upper bound, no fills, no queue, no reward income):** CH245 the thin book's maker widens by the dense
  book's widening for one slot after it (the pick-off avoided = the thin book's next spread change, cents a share); CH244 the
  unpaid member's maker pulls for one slot after a sibling shock (the fill avoided = the member's bid change at k + 1).
- **Paper taker (reported):** LT3's `paper_taker` and `econ` at the recorded touches of the entry capture and the exit capture
  k + 1, fees on both legs from the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), event-
  clustered mean, one-sided p, >= 30 trades in >= 10 events; no depth, queue or latency. CH245 take the thin book's stale side
  for one slot after the dense book widened (the hurdle its own half-spread); CH244 the buyer of an unpaid member waits one slot
  after a shock. **CH245's cheaper-book line** (`min(ask_A, 1 - bid_B)` against `ask_A`, read at capture k only) is a cost-route
  descriptive, not a forecast and not a test.
- **Hurdles (`cost-model-v1`):** taker round trip about 2.9c at >= $100k liquidity, 3.9c at $10k-100k, 7.2c at $1k-10k; 5-share
  touch about 4.5c (politics 3.6c); passive fill 3.1% within an hour; makers about break-even before rewards (-0.37c).
  **No E026 frozen module (`costs.py` included) is imported, copied or edited.**
- **Declared in advance:** every AREPO taker check has failed (0 of 95 cells positive); "not shown" is the expected outcome.
  A Supported LT12 primary can at most nominate a later, separately registered economic test.

### 1.11 Overlaps, dependence and counting
- **Within LT12:** CH245 and CH244 read the same event join but disjoint events (two members against 3-10). One Holm family; the
  census prints the event overlap (none by construction) and the shared captures.
- **Against other tests:**

  | LT12 | Closest prior | Same contrast? | Why not a double count |
  |---|---|---|---|
  | CH245 | LT11 CH233's two-member arm (the twin's *bid* change; reported, uncounted) | no: CH245's state is the twin's *spread* innovation, its target the thin book's spread | different state and window; blind freeze before `T_LT11c` or *informed (LT11 census)* |
  | CH245 | E005, HB1 XM1-XM3, round 13's L1-L4 (mids of ladders) | no: mids; CH245 reads spreads | closed records disclosed; M3 *informed (L1-L4)* |
  | CH244 | LT11 CH233 (siblings' signed bid-sum rise on all members of 3-10 member events) | no: an unsigned shock interacted with the member's own reward status | disjoint windows; `cl_sib` never computed by LT12 |
  | CH244 | E022's S2; LT9 CH213 | no | *informed (E022)* certain; LT9 overlaps in time only |
- **Counting:** the analysis adds **k counted tests**, kind `live_tests12` (`battery2.KIND_RULES["live_tests12"]`, fail-closed).
  Gates, F, point conditions, placebos, secondaries, arms, economics, the census, the CH251 map and the size check count 0.
  CH243's drop counts 0 (it was never censused or registered).

### 1.12 Stop rules
As LT11 1.12: no interim look; runs to `END_UTC` whatever the counts; after 7 days a test whose units run below one third of its
census projection gets the ledger note "likely Unavailable" and nothing else changes; any change to a pinned file makes the
analysis refuse; gaps stay missing; the reader refuses above 3.0 GB in `live_tests12/`; no retention rule covers
`live_tests12/` before the analysis is committed; a kind not in `k_tests` is switched off.

## 2. CH245: the mirror (the dense book's spread innovation and the thin book's next spread change)

### 2.1 Hypothesis in plain words
A two-member neg-risk event is one question sold in two order books: the claim "A" is A's YES and B's NO, with separate makers
and a one-way conversion link. Under a perfect mirror the two spreads are equal. When the dense (narrower) book's makers widen
and the thin (wider) book's have not, the thin book's unchanged quote now sits inside the dense book's mirror: it is the
venue's cheapest price for the claim, it is picked off, and its makers widen a slot later. So, among pair-captures whose two
spreads differ, the thin book's next spread change should rise with the dense book's latest spread innovation, beyond the thin
book's own innovation and the mirror's prior level, and the reverse (the dense book following the thin one) should be weaker.

### 2.2 Population and unit
- **Pair:** an event with exactly two eligible members at k - 1 and k, pair-complete (1.4.3), non-augmented; both members pass
  1.4 at k - 1 and k (tight on both; else `pair_wide`, counted); category non-sports ex-crypto on both.
- **Asymmetry at k - 1:** `|spread_{A,k-1} - spread_{B,k-1}| >= tick_e,k-1`. The **thin** member T is the wider at k - 1, the
  **dense** member D the narrower; a pair-capture with equal spreads on the grid is `sym` (a reported class, no unit). The
  estimand is conditional on asymmetry (R1 ruling A2).
- **Unit:** the thin member of an asymmetric pair-capture: **one unit per pair per capture** (1.7). Origin and decision clock:
  capture k's last row receipt. Target: `ds_T = spread_{T,k+1} - spread_{T,k}` (cents), over (k, k + 1]; `unavailable` unless
  T is `two_sided` at k + 1 (the pair need not be complete at k + 1).
- **Arms (reported, uncounted):** `sym` pair-captures (each book's slope on the other's innovation, reported separately, never
  pooled with the primary); the reward cells rr / ru / uu separately; augmented two-member events; the sports arm.

### 2.3 State, controls and the primary statistic
- **State:** `zs_D = (spread_{D,k} - spread_{D,k-1}) / s_D`, `s_D` the census pooled SD of the dense member's spread innovation
  over CH245 census units (one scalar, fixed in the spec); positive = the dense book widened.
- **Controls (a non-redundant basis; 6 item 2):** the thin book's own innovation `spread_{T,k} - spread_{T,k-1}`; the dense
  book's level before its innovation `spread_{D,k-1}`; the bid headroom `hb_{k-1} = 1 - bid_{T,k-1} - bid_{D,k-1}`; with K's
  own spread at k these span the mirror gaps `g_ask,k-1 = ask_T + bid_D - 1 = spread_T - hb` and `g_bid,k-1 = bid_T + ask_D - 1
  = spread_D - hb` and the spread gap at k - 1, which are therefore not entered separately; `log1p liquidity` of the dense book;
  the dense book's `rewarded_k` (the thin book's is in K); K (the twin's mid change is near `-d_T` and is not entered).
- **Primary:** expanding-past event x UTC day demeaned OLS of `ds_T` on `zs_D` with the controls; **one-sided H1: beta > 0**;
  inference 1.7; state-shift gate (1.8); **F binding** (twin `zs_D` over (k + 2, k + 3]); **dense-twin and two-sided placebo
  point conditions binding** (1.9).
- **Dense twin model:** units = the dense members of the same asymmetric pair-captures; target `ds_D`; state `zs_T =
  (spread_{T,k} - spread_{T,k-1}) / s_T` (`s_T` census-fixed); controls mirrored. **Second binding set (R1 SHOULD 1, re-check
  fix 7):** the same model, and the primary, refitted on pair-captures with the dense `spread_k >= 2` ticks (a dense book at one
  tick cannot narrow); condition (a) of 1.9 must hold on both sets.
- **Placebo pair (rule 18; R1 MUST 5):** for the unit of event e at capture k, the unrelated pair e' is the first CH245
  asymmetric pair at capture k after e in the order of `sha256(event key)` (wrapping) such that **(i)** no member of e' shares a
  series family (1.4.3) with any member of e, and **(ii)** the event-id sets of e's members and e''s members are disjoint (an
  empty set counts as disjoint only if the pair keys differ). Its raw `zs_D'` (scaled by the same `s_D`) replaces `zs_D`; NaN if
  no such pair exists at capture k (`placebo_none`, counted). The rule reads only capture k's keys and sidecars.
- **Secondaries (reported, uncounted):** M1 the thin book's stale-side touch change at k + 1 (the ask where `g_ask,k < 0`, the
  bid where `g_bid,k < 0`), signed as the mechanism predicts; M2 the mirror gaps' change over (k, k + 1]; M3 the thin mid's change
  (*informed (L1-L4)*); M4 the primary with `hb_k` in place of `hb_{k-1}` (the *bid-sum mediated* label, 1.9); M5 the
  receipt-order split; the arms of 2.2.

### 2.4 Planning counts and MDE (planning only)
- **Counts (CH251 map, per capture, non-sports ex-crypto, before LT12's tight, tick and augmented rules):** two-member events 651;
  complete pairs 639 (rr 238.2, ru 19.1, uu 382.0); thin share of member units 0.26 / 0.41 / 0.47, so asymmetric pair-captures
  (= thin units) about 124 + 16 + 359 = **499 a capture**; receipt-span retention 1.000; distinct events 1,023 over 9.25 days.
  Planning after the tight rule, the post-midterm panel and the new filters (each unprobed): **200 (low) to 500 (high) thin
  units a capture**; `n_eff` 40,320-100,800 at 0.8. Within-stratum variation of the dense innovation, leverage concentration and
  placebo coverage under the series-family rule: **unprobed** (the map counted none of them).
- **Design effect:** one thin unit per event per capture, so `m_21 <= 252` and the formula gives DE about 6 (floor 5.0); 11 is
  the round's value for two units an event-capture (quoted as the pessimistic plan); 31 is the ladder convention, quoted only.
- **MDE** (`3.47 x 2c x 1.5 x sqrt(1.3) x 2.2 = 26.112`; `MDE = 26.112 x sqrt(DE / n_eff)`, planning within-stratum SD of the
  demeaned state 1.0 in `s_D` units): DE 6 **0.32c / 0.20c**, quarter 0.64c, F (x 1.5811, `r_w` 0.2) 0.50c / 0.32c; DE 11 0.43c /
  0.27c, quarter 0.86c, F 0.68c / 0.43c; DE 31 0.72c / 0.46c, F 1.14c / 0.72c. The census's declared MDE divides the gap by the
  measured within-stratum SD (7), so a state that barely moves inside event-days raises the MDE. The point conditions are
  estimates (no MDE gate); the dense-minus-thin difference's MDE is reported.
- **Kill line (F-MDE <= 1.0c):** `n_eff >= 1,704.6 x DE` (at within-stratum SD 1.0): 51 thin units a capture at DE 6, **93 at DE
  11**, 262 at DE 31. **Count gate 186 a capture** (twice the line at DE 11, LT9 CH214's and LT11 CH233's practice; R1 ruling A13:
  consistent); the MDE gates decide with the census's own DE, `VIF_w`, within-stratum SD and `r_gate`.

### 2.5 Confounders and how each is held
- *Common event shock* (S30): the own innovation is a control; world 1 binding.
- *One bot on both books* (S31): if both books are quoted from one model within minutes, the lead is a receipt artefact; the
  120 s span rule bounds it, world 2 plants it with the census's receipt gaps, M5 reports it; the same-slot correlation gate (7)
  measures how much of the panel moves in one slot.
- *Venue-wide or topic-wide spread moves* (S32): the two-sided placebo with a different series family and disjoint event ids
  (an unrelated pair on the same story would not test "unrelated"); world 3.
- *Selection on thin at k - 1* (regression to the mean): the dense member is narrow at k - 1, so its innovation tends to be
  positive while the thin member reverts down; this biases against H1, but world 4 is binding and both levels are controls.
- *The 1c floor:* a dense book at one tick cannot narrow, which can make the dense-twin condition pass by mechanics; world R1
  reports how often, and condition (a) must also hold on the dense `spread_k >= 2` ticks set (1.9).
- *Thin books are illiquid books:* dense liquidity and K's own liquidity as controls; the corr gates (7); world 5.
- *Reward status* (the paid book is usually the dense one): both books' status as controls; rr / ru / uu reported.
- *The record:* LT11's two-member arm (a different state; disclosed); the `event` family's visible levels (no twin-spread
  innovation exists in the engine; 9).
- **Most likely boring outcome:** the two books are one bot's quotes that move in the same slot, so nothing is left to follow
  (the census's same-slot correlation and `VIF_w` say so before any target); or the dense book's spread rarely moves inside an
  event-day on a 1c grid (the within-stratum variation gate).

### 2.6 Data streams, jobs, timing
Rows and sidecars of captures k - 1 .. k + 3 for every two-member event (the event join is a reader, no matcher); per event the
previous capture's two rows (a few hundred bytes; about 1,000 events). Census CC12 (7), size check, reader, analysis (8). Token
`mirror` (9).

## 3. CH244: the farmed half (a sibling shock and the unpaid members' next spread)

### 3.1 Hypothesis in plain words
The liquidity programme pays makers per market, but a ladder is priced per event. In a ladder where some members have a paid
maker and some do not, a maker paid per minute of resting inside the band re-centres and stays after a shock (pulling loses the
minutes), while an unpaid maker on the next rung has no such tie and steps back, or is hit first because his quote did not move
when the ladder's implied value did. So after the same sibling shock, the unrewarded members' spreads should widen more than
the rewarded members' in the same event-day, beyond what illiquid rungs do after any shock.

### 3.2 Population, unit and states
- **Day-fixed status (R1 SHOULD 4, ruling A9):** for each member and UTC day, `unrew_{i,day}` = 1 - `rewarded` (1.4.1, status
  capture s = k - 1) at the **first capture of the UTC day at which the member is an eligible member of the event**. A later unit
  of that day whose status at its own k - 1 differs is excluded (`status_switched`, counted by status). A member whose day-fixed
  status is NaN makes every event-capture of that event-day that includes it ineligible (`status_nan`). **A unit whose own
  status at its k - 1 is NaN (1.4.1 case (c)) is excluded and counted (`status_nan_unit`) and is never given the day-fixed
  status** (re-check fix 4); for the mixed rule below the member still counts by its finite day-fixed status, as a switched
  member does.
- **Ladder:** non-augmented, ladder-complete (1.4.3) events with **3-10** eligible members at k - 1 and k; **mixed** at capture k
  **on the day-fixed statuses**: among the eligible members at k - 1, >= 1 with `unrew_{i,day} = 0` and >= 1 with
  `unrew_{i,day} = 1` (switched members count by their day-fixed status). 11+ member ladders a reported arm (completeness 0.31 on
  the map; same rules); 2-member events are CH245's.
- **Unit:** member x capture of a mixed ladder-complete pair, the member passing 1.4 at k - 1 and k and not `status_switched`
  (a member failing a member-level rule gives no unit; the event-capture stays complete for the others). Target `ds_i =
  spread_{i,k+1} - spread_{i,k}` (cents); `unavailable` unless the member is `two_sided` at k + 1.
- **Shock:** `shock_{i,k} = 1[max_{j != i} |d_{j,k}| >= 2 x tick_e,k]` over the event's other eligible members (`d` the 2 h mid
  change over (k - 1, k]); `shock_size_{i,k} = max_{j != i} |d_{j,k}| / tick_e,k`, winsorised at 20 ticks, entered divided by its
  census scale (7).
- **Tested term:** `shock_{i,k} x unrew_{i,day}`. **Tested units** (for counts) = unrewarded members on shock captures.
- **Low-liquidity twin (point condition):** `lowliq_{i,k} = 1[liquidity_{i,k-1} < median_j liquidity_{j,k-1}]` over the event's
  eligible members at k - 1 (ties 0).

### 3.3 Controls and the primary statistic
- **Controls:** `unrew` (main), `shock`, `shock_size`; `tier_{i,k-1}` dummies and **tier x shock** (1.4.2); the own `d_i`, `|d_i|`
  and own spread change over (k - 1, k]; `hb_{k-1}` (the event's bid headroom, a level; LT11's `cl_sib` is never computed); the
  member's bid share and a favourite dummy (rank 1 by mid at k - 1); `n_members`; `neg_risk_other`; K.
- **Primary:** expanding-past event x UTC day demeaned OLS of `ds_i` on `shock x unrew` with the controls; **one-sided H1: beta
  > 0**; inference 1.7; state-shift gate (1.8); **F binding** (twin: the shock over (k + 2, k + 3]); **low-liquidity point
  condition binding:** the twin model replacing `unrew` and `shock x unrew` by `lowliq` and `shock x lowliq` gives betâ_lowliq <
  0.5 x betâ_unrew.
- **Joint model (reported; R1 SHOULD 3, ruling A8):** the primary with `lowliq` and `shock x lowliq` added beside `unrew` and
  `shock x unrew`; both interaction coefficients, their correlation and one-sided p printed; the *liquidity-shared* label (1.9).
- **Secondaries (reported):** M1 the member's bid change at k + 1 (predicted < 0); M2 the mid toward the siblings' implied value
  (*informed (L1-L4, E005)*); M3 the traded-shock arm (shock from a sibling's `volume_num` rise; `unknown` a counted class, never
  inferred); M4 (placebo) the shock's main effect on all-rewarded and all-unrewarded ladders; the CLOB-agreement refit; the
  event-capture aggregate (1.7); the 11+ arm; the sports arm.

### 3.4 Planning counts and MDE (planning only)
- **Counts (CH251 map, simple reward reading `clob_rewards` non-empty at k, not `listed_carry24h_v2`):** mixed ladders 1,363 a
  capture (3-5: 238, 6-10: 752, 11+: 373); complete 199 / 661 / 116 (shares 0.83 / 0.88 / 0.31); unrewarded two-sided 0.82
  (rewarded 0.97); shock share 0.51 (unrewarded) / 0.53 (rewarded); status-liquidity correlation pooled -0.05, within event -0.09
  (3-10 members); distinct mixed events 2,304 over 9.25 days. **Unprobed:** members by size class, the carry reading's effect on
  the mixed share, the feed-listed share of carry-unrewarded members, feed coverage, receipt spans, switchers.
- **Planning:** 860 complete 3-10 mixed ladders x 6 members = 5,160 member units; unrewarded share 0.4-0.6; then the carry
  correction 0.3-1.0, receipt span 0.6-1.0, tight 0.7-1.0, switchers 0.8-1.0; shock share 0.5. **Low:** 208 unrewarded member
  units, **104 tested units** and 156 rewarded shock units a capture; **high:** 3,096 unrewarded, **1,548 tested** and 1,032
  rewarded shock units. No-shock cells equal the shock cells at shock share 0.5.
- **Design effect:** a 6-member ladder present all window holds about 1,512 units: DE about 31 (cap 51); census `max(5.0, computed)`.
- **MDE (R1 SHOULD 2: the interaction's variance from all four cells):** `MDE = 3.47 x 2c x 1.5 x sqrt(1.3) x sqrt(31) x sqrt(1/n_us
  + 1/n_un + 1/n_rs + 1/n_rn) = 66.085 x sqrt(...)`, with `n_us`, `n_un`, `n_rs`, `n_rn` the effective unrewarded-shock,
  unrewarded-no-shock, rewarded-shock and rewarded-no-shock counts (units a capture x 201.6). At shock share 0.5 it equals the
  first draft's two-cell form times sqrt(2): low **0.83c**, high **0.26c**, quarter of low 1.67c; F (x 1.5811) **1.32c (fails) /
  0.42c**. The census computes it with the measured four cells.
- **Kill line (F-MDE <= 1.0c, rewarded cells 1.5 x unrewarded, shock share 0.5):** **181 tested units a capture.** **Count gate
  362** (twice the line) and rewarded shock units >= 181; the MDE gates decide with census values.

### 3.5 Confounders and how each is held
- *Unpaid rungs are illiquid rungs* (S34): tier x shock, the low-liquidity point condition, the joint model, the corr gates,
  world 9 (with the census's measured correlation).
- *Reward-field omission:* case (b) of 1.4.1 sets a market whose `clob_rewards` was omitted on all 12 slots to unrewarded (the
  disclosure of 1.4.1); the census gates the share of carry-unrewarded tested units that the CLOB feed lists, prints the
  carry-against-simple confusion (7), and the CLOB-agreement refit is reported; switchers are excluded and printed by status.
- *The favourite as the only mover* (S27): the favourite dummy, `shock_size`, world 8.
- *Common event shocks* (S26): the shock is at (k - 1, k], the target at (k, k + 1]; own changes controlled; world 7.
- *Completeness by status* (unrewarded members one-sided more often): rule 16 drops the pair, counted; completeness by status
  printed.
- *The record:* LT11 CH233 (a different state, disjoint window); E022's S2 (*informed (E022)*); the `event` family's levels.
- **Most likely boring outcome:** under the carry reading mixed ladders are rare (the count kills it), the feed lists many
  carry-unrewarded members (the feed gate kills it), or the widening is the liquidity gradient (the point condition fails).

### 3.6 Data streams, jobs, timing
Rows and sidecars of captures k - 12 .. k + 3 (the carry window), every member of each neg-risk event of 3-10 members; per event
the previous capture's member rows and per market the carry texts and the day-fixed status; the feed capture at the feed clock
for the census and the sensitivity. Census CC12; token `mixedlad` (9).

## 4. CH243: dropped before the freeze (R1 MUST 1); an engine-first note
- **What was dropped.** CH243 (the fee as the price of urgency: the fee-on minus fee-free panel contrast of the within-market
  traded-minus-quote-only continuation) is removed from LT12 with its census block, size worlds (first-draft worlds 11-15), the
  `feeclass` token, the fee-class attribution item and its *informed (E015)* line. LT12 is k <= 2. Nothing was censused,
  counted or registered for it.
- **Why.** The first draft made CH243's falsification check (F) a reported label because, with F binding, the kill line was
  about 522 fee-free traded movers a capture, above every map reading. R1 ruled (MUST 1, ruling A1) that this is the case LT11
  R1's ruling **A4** already decided: the state is rolling (`d_{k+1}`, the target move, defines the next unit's mover status and
  sign), so F binds, and **a label-only F chosen for power is rejected**; the panel contrast does not replace a falsification
  check, because the two panels differ in composition (geopolitics and old, large markets against the rest), and one planted
  loading pair (first-draft world 15) does not cover the drifts that could differ by panel. Tying F's treatment to a census
  count is also barred (`LIVE_TESTS_11.md`: whether F binds is fixed by design, never by a census count). Round 17's own
  default for CH243 was engine-first by rule 7. The designer accepts the ruling; no variant is kept in reserve.
- **Engine-first note (no LT12 request).** CH243 returns to the signal-engine lane under the builder's rules: `tilt`'s
  `tl_fee_free` and `tl_fee_src` as levels, and a fee-class x traded-move interaction only after `movetype`'s date
  (2026-11-22), each built only with a real prior; the panel must be read from sidecar fields as a market constant (rule 20),
  `volume_num`'s missing class counted and never inferred, and the CH251 map's warnings carried: the fee-free population was
  not stationary (mean 346 traded movers a capture against medians 64 and 7; R1 SHOULD 6: those are two separate medians, not
  one), and `created_at` gives the age class. LT12 requests no token for it; any future live test of it is a separate
  registration with its own census and a binding F.

## 5. Deferred and not taken (none counted)
- **CH243:** section 4 (engine-first). **CH246 (no-link twin):** no matcher and no rules text in the captures; not an arm here.
- **CH248 (who printed):** engine-first (`movetype` spec after 2026-11-22); the map's `twin_printed` share 7% clears its 5% line.
- **CH250 (who pays the maker):** engine-first; the map's fee-free cells are 29% of rows, above its 3% kill line.
- **CH242 (third price):** killed at its own census on 2026-10-23 (non-sports split share 0.004%).
- **CH247, CH249:** the owner's sports and crypto parameters. **Sports arms:** reported, uncounted, in both tests.

## 6. Design changes from the round-17 sketches (made before any LT12 data; each needs the challenger's acceptance)
Items marked **[map]** were made after reading the CH251 map; items marked **[R1]** in response to the challenger.
1. **CH245: the thin member only, one unit per asymmetric pair-capture [map].** The round pooled both members. The two members'
   targets in one slot are near-duplicates (the map's same-slot correlation 0.38-0.64 is on their innovations), the mechanism
   predicts a slope only for the thin book, and pooling averages in the predicted null of the dense book. The dense book is the
   point condition on the same pair-captures; `sym` pair-captures (0.47 of rr member units) are a reported class. R1 ruling A2
   accepted this, with the estimand stated as conditional on asymmetry and no pooling.
2. **CH245: a non-redundant control basis; mirror levels at k - 1.** The round's controls `g_A`, `g_B`, the spread gap and `hb`
   are linearly dependent (`g_A = spread_A - hb`, `g_B = spread_B - hb`, so `g_A - g_B` is the spread gap). LT12 enters own
   spread at k (K), own innovation, `spread_{D,k-1}` and `hb_{k-1}`. The levels are taken at k - 1, not k, because the mirror
   gap at k contains the state and is the mechanism's own channel; the k form is M4 (R1 ruling A3), which differs from the
   primary only through `hb_k` and is therefore labelled *bid-sum mediated* (R1 SHOULD 7).
3. **CH245: the placebo is a binding, two-sided point condition with a different series family and disjoint event ids [R1
   MUST 5].** Rule 18 says the placebo "must be null"; a one-sided "less than half" would pass a strongly negative placebo, which
   is not null; and a pair from the same series or sharing an event id can share the story, which is not "unrelated".
4. **CH245: planning DE 6 / 11 / 31 and the count gate 186 [map]** (twice the F line at DE 11; ruling A13).
5. **Both: demeaning in event x UTC day; the gate on whole events with the raw state shifted and the demeaning re-applied on
   every draw [R1 MUST 6].** A pair has at most 12 thin units an event-day, under the gate's 16-row minimum, so the gate shifts
   whole events; shifting demeaned values across days would mix day means, so the raw state is shifted and re-demeaned (1.8).
   R1 ruling A6: valid with this path.
6. **CH245: the identification gate redefined [R1 MUST 4].** Round 17 wrote it as "within-event SD of `zs_B` >= 1 tick in >= 50%
   of events with >= 48 units", which mixes a standardised quantity (`zs_B` has no tick unit) with a tick threshold; the first
   draft silently read it as the raw innovation's SD. The redefinition states what identification needs under event x UTC-day
   demeaning: **(i) within-stratum variation:** >= 50% of thin units lie in event x UTC-day strata in which the raw dense
   innovation is non-zero on >= 3 of the stratum's thin units; **(ii) leverage cap:** the 1% of thin units with the largest
   |demeaned `zs_D`| hold <= 25% of the sum of squared demeaned `zs_D`, and no single event holds > 5% of it; **(iii)** the
   declared MDE divides the census tercile gap by the census SD of the demeaned `zs_D` (7). **Rationale of each number:** 3
   non-zero innovations leave at least two varying units after the expanding-past demeaning drops a stratum's first unit; 50%
   is the share LT11's identification gates use; the 25% top-1% cap keeps a handful of jumps from carrying the slope (the tight
   rule caps a single innovation at 9c, so the cap binds only if the rest barely moves); 5% per event is about the share one
   event would hold at `G_eff = 20`, a margin over the `G_eff >= 15` floor. **Why this is not tuning:** no LT12 designer has seen
   any count of either the round's form or this one; the CH251 map did not probe the within-event SD, the within-stratum
   variation or leverage of any spread innovation (the map note lists what it counted), and no census has run. The change fixes
   a unit mismatch and aligns the gate with the estimator; it was written before any data could show which form passes.
7. **CH244: tier from the row's `liquidity` at k - 1 in the cost model's bins [map: no tier in captures]; the low-liquidity
   twin defined within event; carry status at k - 1 fixed per market-day, and "mixed" judged on the day-fixed statuses [R1
   SHOULD 4].** The round's "the CLOB feed adjudicating" is read as: carry status in the primary (R1 ruling A7), and the feed's
   disagreement gated in the census (item 9).
8. **CH244: own spread change and a favourite dummy added; `cl_sib` never used** (LT11's object); `hb_{k-1}` kept as a level.
9. **CH244: the feed-disagreement census gate [R1 MUST 3].** Among tested units at captures with a feed capture at the feed
   clock (1.2), the share whose market the feed lists with a positive rate (carry-unrewarded but feed-listed) must be **<= 0.20**,
   and the feed must cover **>= 50%** of tested units. **Outcomes (re-check fix 3):** coverage under 50% (an outage included)
   makes CH244 **`census_unavailable (coverage)`** (no other CH244 gate value is computed or printed; re-census only in the
   ordered lane, as its own Holm family); a feed-listed share above 0.20 on adequate coverage makes it **`census_dropped`**.
   **Gate, not label, because**
   a misclassified unrewarded class is not a sensitivity: it changes what the tested term measures, and omission is plausibly
   tied to activity (the S34-type confound), so a label after the result could not protect the verdict. **Why 0.20:** under
   non-differential misclassification of a share m of the tested class the contrast shrinks by about (1 - m); at m = 0.20 the
   high-end planning F-MDE 0.42c becomes about 0.53c, still under the 1.0c floor, while a larger share would make the test's
   object mostly the rewarded panel's own spread reaction. **Why 50% coverage:** below half the tested units the measured share
   describes a minority of the population. **Why a 6 h feed clock:** three capture slots, a quarter of the carry window, so a
   feed listing is near the status capture. All three are conventions declared before any feed count; none was measured.
10. **CH244: the count gate on tested units (362) [map]**, not on unrewarded members, so the measured shock share enters once.
11. **CH244: the interaction MDE from the four cells [R1 SHOULD 2]** (3.4); the planning figures do not change at shock share
    0.5.
12. **CH243 dropped [R1 MUST 1]** (section 4). The first draft's items on CH243 (F as a label, the median count gate, the fee
    panel, the cell-matched control, the market gate strata, the absolute quote-only condition) are withdrawn with it.
13. **Both: K as LT11 1.7.**

## 7. Pre-registration census (counts only; before registration; worn pre-window data; no target read)
The census runs once, reads origin-side fields only (the only later-slot quantities are the two twins' states, for `r_gate`,
through the lag-slot loader, which returns only the twin term; no mid, spread, bid, ask or volume of a later slot reaches census
code; unit test), prints counts, and is committed with its sha256 before the registration commit. **Every threshold below is
stated now.** A failed gate drops that test (`census_dropped`, uncounted); `k_tests` lists the survivors. **Input identity:** the
census refuses unless every input file is named in the LT12 seal with an equal sha256; slots and origins come from the seal.

**Inputs (fresh seal; rule 9).** Span **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**, 10 UTC days, 120 slots; the 12 slots
`[2026-11-06T00:00Z, 11-07T00:00Z)` as look-back only (inside LT11's census seal span; raw rows only, no LT11 object computed,
disclosed, ruling A15) and the 3 slots after the span (to 2026-11-17T04:31Z, before LT11's window) for twins only. Complete
captures (rows, sidecar, manifest), 135 captures x 3 files, planning 1.0-1.4 GB; **and the CLOB reward feed captures** whose
start lies in `[2026-11-06T00:00Z, 2026-11-17T00:00Z)` (for CH244's feed gate only; a few MB).
- **Restore, seal, census: each once** (LT11 7's rules: host copies checked against the archive catalogue, the rest restored byte
  for byte; bytes measured first and the owner asked if the restore would exceed free disk; a file in neither place is missing,
  counted, never substituted; the seal records files, sha256s, the seal's slot assignment and the frozen LT12 design-text sha256).
- **Minimum covered days, checked first** (covered origins / 12, from the seal manifest, identical for both tests): >= 7.0 (>= 5.0
  for twin pairs). If it fails for a test, no gate or descriptive line of it is computed or printed; the test is
  `census_unavailable (coverage)` (1.1). **CH244's feed coverage is a second coverage check (re-check fix 3):** it is evaluated
  first in CH244's block, before any other CH244 gate value is computed (it needs only the tested units' keys, statuses and feed
  timestamps); under 50% (an outage included), CH244 returns at once as `census_unavailable (coverage)`, with only the coverage
  counts printed. The feed-listed share is then a gate (`census_dropped` above 0.20).
- **Header pre-check** (headers only, before the census code is frozen; result committed before the seal): the 1.2 fields
  including `series_slugs`, `event_ids`, `liquidity`, `clob_rewards`; whether `chg_1d` / `chg_1w` exist; the feed's listing
  fields. A missing field makes every gate that needs it NaN.

**Definitions.** Projection = count x 21 / covered days. Distinct-event gates and ">= 48 units" counts are **unprojected**.
`DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)`. MDE gates `max(declared, design)` (multiplier 3.47; SD `ds` 2c). *Declared* =
the closed formula at the census's effective counts, `DE_gate`, `sqrt(max(1, VIF_w))` and gap, with **CH245's gap divided by the
census SD of the expanding-past event x day demeaned `zs_D`** (6 item 6) and **CH244's four-cell variance** (3.4). *Design* =
`3.47 x 1.5 x SD x se_1` from the census regressors **after the same expanding-past event x UTC-day demeaning the analysis
uses** (so within-stratum variance enters; LT8's working covariance: unit variance, within-event equicorrelation 0.02,
independence across events). F-MDE `= max(design MDE of Δ, MDE x sqrt(2 / (1 - max(0, r_gate))))`. Count gates on gross
projected counts.

| Test | Gate (all must hold; NaN fails) | Map number it sits near (planning only) | Values fixed into the spec |
|---|---|---|---|
| **CH245** | pair completeness: pair-complete two-member event-captures / eligible two-member event-captures (incl. `members_changed`) >= 60%; receipt span: span-retained pairs >= 60% of pair-complete pairs (span and receipt-gap quantiles q50 / q90 / q99 printed); **projected thin units (all 2.2 filters) >= 46,872 (>= 186 a capture)**; **distinct events with a thin unit >= 500 and events with >= 48 thin units >= 100** (unprojected); **Kish `G_eff` >= 15**; **same-slot correlation:** among events with >= 24 complete pair-captures, the share with within-event `|corr(Δspread_A, Δspread_B)|` >= 0.8 is <= 50%; **identification (6 item 6):** >= 50% of thin units in event x UTC-day strata with a non-zero raw dense innovation on >= 3 thin units; the top 1% of thin units by |demeaned `zs_D`| hold <= 25% of its sum of squares and no event holds > 5%; `VIF_w(zs_D)` <= 2.0 (computed on the expanding-past event x UTC-day demeaned regressors, as the analysis fits them; ruling B1); within and pooled `|corr(zs_D, x)|` <= 0.5 for x in {`log1p liquidity` of each book, `z log rv24*`, `d_T`}; venue clock: the most common slot holds <= 50% of units with `|zs_D| >= 1`; block-gate share >= 50% of thin units in events with >= 16 shiftable captures; **placebo coverage** (a pair satisfying 2.3's series-family and event-id rule) >= 90% of thin units; `r_gate` <= 0.3; **slope MDE <= 1.0c; F-MDE <= 1.0c** | thin units 499 a capture before the tight rule; retention 1.000; completeness 0.97-1.00; same-slot correlation pooled 0.38 / 0.11 / 0.64 (per-event shares unprobed); within-stratum variation, leverage and placebo coverage unprobed | `s_D`, `s_T`, `s_w`; `zs_D` tercile cuts and gap; world 2's receipt-gap q50 / q90; `exclude_family` |
| **CH244** | finite day-fixed status on >= 95% of eligible member-days of 3-10 member events (1.4.1 case (c) is the only NaN); ladder completeness: pair-complete member rows / eligible member rows (incl. `members_changed`) of 3-10 member events >= 60%; receipt span >= 60% of pair-complete pairs; **projected tested units (unrewarded x shock, all 3.2 filters) >= 91,224 (>= 362 a capture)**; projected rewarded shock units >= 45,612 (>= 181 a capture); **feed disagreement (6 item 9):** feed coverage >= 50% of tested units (else `census_unavailable (coverage)`, checked first) and, among covered tested units, the feed-listed (positive-rate) share <= 0.20 (else `census_dropped`); **shock share** of mixed event-captures in [0.10, 0.80]; within-event and pooled `|corr(unrew, log1p liquidity)|` <= 0.5; **within-stratum variation:** >= 50% of tested units in event x UTC day strata holding both shock and no-shock captures; `VIF_w(shock x unrew)` <= 2.0 (on the demeaned regressors); **distinct mixed events >= 500 and events with >= 48 units >= 100** (unprojected); **Kish `G_eff` >= 15**; venue clock <= 50% of tested units in one slot; block-gate share >= 50%; `r_gate` <= 0.3; **class MDE (four cells) <= 1.0c; F-MDE <= 1.0c** | mixed 3-10 ladders 990 (860 complete) on the simple reading; shock share 0.51-0.53; corr -0.05 / -0.09; the carry effect, feed-listed share, feed coverage, spans and switchers unprobed | world 9's correlation; `shock_size` scale; `exclude_family` |

- **Census-fixed values (the exhaustive list; each written into the spec as the exact census float; nothing else is left open).**
  (1) `k_tests`: the tests whose every gate above holds. (2) `s_D`, `s_T`: the population SD (ddof 0, cents) of the dense and the
  thin member's raw spread innovation over CH245 census thin units. (3) `s_w`: the population SD of the expanding-past event x
  UTC-day demeaned `zs_D` over the same units (in `s_D` units). (4) `zs_D` tercile cuts: its 1/3 and 2/3 quantiles; the gap =
  mean of the top tercile minus mean of the bottom tercile (the *material* label's and the MDE's gap). (5) World 2's receipt
  gaps: q50 and q90 of `|received_utc_A - received_utc_B|` at k over CH245 census pair-complete pairs (floor q50 5 s). (6) World
  9's correlation: the within-event `corr(unrew, log1p liquidity)` over CH244 census units (floor |0.20|). (7) `shock_size`
  scale: its population SD over CH244 census units. (8) `<test>.exclude_family`: 1.4's series-family rule on each census primary
  population. (9) **`rho_census`** (re-check fix 2): the pooled Pearson correlation of the raw `Δspread_T = spread_{T,k} -
  spread_{T,k-1}` and `Δspread_D = spread_{D,k} - spread_{D,k-1}`, both over the same interval (k - 1, k] at the same capture
  pair (the "same slot" of 1.8.1 world 1), over CH245 census thin units; NaN if either has zero variance; world 1 uses `rho_ss = max(rho_census, 0.64)` (1.8.1). The census's `DE_gate`, `VIF_w`, `r_gate`, the feed shares and the MDEs are gate values, recorded, never re-used to
  change a threshold.
- **Census prints for CH244 (R1 MUST 3; descriptive, no further gate):** the **carry-against-simple confusion**: on eligible
  member rows of 3-10 member events at k - 1, the 2 x 2 counts of `listed_carry24h_v2` status against the simple reading
  (`clob_rewards` non-empty at k - 1), with the 1.4.1 case counts (`rewards_null_carried`, `rewards_null_as_zero`,
  `rewards_null_window_listed_inactive`, `rewards_listed_inactive`, NaN), and the mixed-ladder counts under each reading; **the
  feed table**: tested units by carry status x feed listing (listed positive / listed zero / not listed / `feed_uncovered`), the
  feed coverage share, and the feed age distribution at the feed clock; switch shares by status (ruling A9).
- **Descriptive (no gate):** sports and crypto splits; series-family shares; the events and captures the two populations share.
  CH245: rr / ru / uu and `sym` shares; `pair_wide`, `augmented`, `members_changed`, `receipt_span`, `placebo_none`,
  `event_ids_missing` counts; the mirror gaps' distribution and the share within one tick of zero; the dense-twin units and the
  dense `spread_k >= 2` ticks share. CH244: completeness by status and size; `status_nan`, `status_switched` by status; the share
  of mixed events with both statuses two-sided on >= 24 units; the 11+ arm's counts.
- **Order:** one census job (CC12) streams the captures once and evaluates the two blocks independently.
- **Expected fates (declared now).** CH245: the same-slot correlation share, `VIF_w` and the redefined identification gate decide;
  count and retention are not expected to bind. CH244: the tested-unit count under the carry reading and the feed gate decide;
  then `VIF_w` and the receipt span.

**Jobs (to be drafted under `docs/research_lab/queue/drafts/`; ids q0710-q0715 checked unused on 2026-10-23; none written in this
commit).** `q0710_lt12_census_restore` (net, about 1,400 MB disk, `mem_mb` 400; `depends_on` the freeze; `not_before`
2026-11-17T09:00Z, moved from 06:00Z: the last lag slot's capture (slot 2026-11-17T04:31Z) may start as late as 05:01Z under the
30-minute tolerance and needs up to one slot (2 h) to be `state=complete` with its sidecar, so the inputs are final only at about
07:01Z; 06:00Z could open the restore before that capture is written, and 09:00Z keeps a 2 h margin; **the restore refuses only
while a lag-slot capture is still in progress** (started, not yet in a final state); a capture in a **final non-complete state**
(failed or partial) counts as **missing**, exactly as a file found nowhere does (above), and a slot past its tolerance with no
capture is missing; so the one-shot restore can never wait on a capture that will not complete); `q0711_lt12_seal` (net, 300); `q0712_lt12_census` (net, 600, streaming with a two-capture window and the
12-slot carry state; `cpu` 1,200 exclusive if the dry run measures more); `q0713_lt12_size_check` (cpu, 800, after the census
values are committed; `max_retries 1`); `q0714_lt12_reader` (fallback only); `q0715_lt12_analysis` (cpu, 4,000, exclusive,
`not_before` the analysis date). Never promoted while E015's or E022's analysis, or an LT9, LT10 or LT11 census, size check or
analysis, is running (memory-heavy-jobs rule). Each counts 0.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written
- `backend/astrolabe/research_lab/live_tests12_base.py`: vendored, hash-pinned copies of `move_join`, `classify`, the slot grid,
  LT7's `RewardCarry` (`listed_carry24h_v2`), LT5's offset rule from `block_fl_gate`, LT11's event-phase index, LT3's
  `paper_taker` and `econ`, LT9's lag-slot loader and seal helpers, the sports and crypto classifiers; a provenance test checks
  each against its source hash. **No E026 frozen file is imported, copied or edited.**
- `backend/astrolabe/research_lab/live_tests12.py`: unit builders (2.2-2.3, 3.2-3.3), **the new `event_day_state_shift_gate`
  (1.8; new code, not a vendored copy)**, reader, `ops-stats`, census (7), size-check worlds and world R1 (1.8, 1.8.1), analysis
  (1.7-1.10).
- `scripts/research_lab/run_live_tests12.py` (`seal`, `census`, `size-check`, `reader`, `backfill-series`, `ops-stats`, `analyze`).
- `backend/astrolabe/research_lab/model_specs/live_tests12_v1.json` (unpinned until 8.4); `battery2.KIND_RULES["live_tests12"]`.

### 8.2 Resources and install
- **No new collector, no network.** A pure reader of the pass's captures and sidecars (the reward feed for CH244's sensitivity).
- **Memory (planning, then a ladder):** per market the 12-slot carry texts, the day-fixed status and a few levels; per neg-risk
  event the previous capture's member rows: **steady 250-400 MB, peak 400-550 MB.** Ladder measured by a host dry run with the
  exact install command: (1) one reader under `ulimit -v 1572864`, accepted at peak RSS <= 650 MB; (2) else two readers (CH245;
  CH244) under one shared `flock`, each <= 650 MB; (3) else no pin (recorded).
- **Install: host cron** `25 */2 * * *`, own `flock`, `nice -n 19`, `oom_score_adj 1000`; q0714 is the fallback, never both.
  Concurrency: LT9's reader may install in late December; E026 runs to 12-07; LT11's reader ends with its window.
- **Disk:** about 1-2 GB over the window (CH244's member units dominate); refuse above 3.0 GB. **Analysis:** about 1-2 million
  unit rows, 200 refits per gate draw set, planning 3-4 GB, exclusive.
- **Host change:** the cron line, under the standing collection authorisation, by the orchestrator.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests12.py`, synthetic only)
Causality (no unit builder reads capture k + 1 or later; decision time = capture k's last receipt); the event key, pair and ladder
completeness, `members_changed`, `augmented`, the 120 s span at k - 1 and k; **the three reward-status cases of 1.4.1** (listed
positive -> 1, listed rate 0 -> 0, null with a positive listed text in the window re-parsed for the status day -> 1, null with
none -> 0, malformed or absent sidecar row -> NaN, a missing window slot skipped and counted, no slot after s read); CH245's
asymmetry rule (one tick of `tick_e`), the thin member as the only unit, `sym` giving no unit, the control basis (no collinear
mirror-gap column), the twin's NaN rule; **the placebo rule** (sha256 order at capture k only, a pair sharing a series family or
an event id skipped, `placebo_none` when none qualifies, the two-sided condition); the identification-gate quantities
(non-zero count per stratum, top-1% and per-event leverage shares); CH244's day-fixed status, the mixed rule on day-fixed
statuses, `status_switched`, the shock excluding the own move, `lowliq` within event, tier from `liquidity`, the four-cell MDE,
the feed clock (<= 6 h, else `feed_uncovered`) and the feed-listed share; **the gate path (R1 MUST 6): `event_day_state_shift_gate`
shifts raw state values with one offset per event, recomputes interactions from the shifted shock, re-applies expanding-past
event x UTC-day demeaning on every draw, keeps the target and other regressors fixed, omits (never fills) missing positions, and
a fixture shows that shifting pre-demeaned values gives a different design matrix and is refused by an assertion; the gate
statistic is the event-clustered CR1 t on the gate sample (events with `n_e >= 16`), and the observed t is refitted on that
sample, never taken from the all-units fit (re-check fix 1)**; world 1's `lambda` bisection reaches `rho_ss` within 0.005 on a
synthetic `rho_census`, and worlds 1 and 7 generate events with `n_e < 16` (re-check fix 2); a unit with a NaN own status at k - 1
is `status_nan_unit` and never takes the day-fixed status (fix 4); feed coverage under 50% returns `census_unavailable
(coverage)` before any other CH244 gate value, a feed-listed share above 0.20 returns `census_dropped` (fix 3); the dense-twin
condition is evaluated on both sets and the `>= 2` ticks set under 5,000 units gives *dense-twin unavailable* (fix 7); the size
worlds call the same gate function as the analysis; the lag-slot loader returns only twin terms; the coverage check returns
before any gate; `ops-stats` reads no price, spread, volume or liquidity column; spec NaN refusal; seal and pin refusals; the
analysis refuses before its date; the worlds generate the declared shapes; vendored copies match their hashes;
`test_pinned_files_hash_to_the_pins` (E026) stays green.

### 8.4 Registration steps and pins (in order)
1. The final pre-freeze verification (the acceptance; done, its wording fixes applied in the freeze commit).
2. **Design-text freeze commit**, sha256 in the ledger, planned by 2026-11-06 (before `T_LT11c`), required before the seal commit
   and `T_LT11`; the embargo requests of 9 filed in `signal_engine/CANDIDATES.md` in the same session.
3. Code (8.1, 8.3), a `science-reviewer` freeze check of census, gate and size-check code; size-check run time per world measured
   at a timing seed other than 20261597 (20 worlds each; only the clock read) and projected; if census commit + projected run +
   24 h margin + the dry run cannot precede 2026-12-08T00:00Z, the ordered lane is declared by a ledger line before the seal.
4. q0710 restore, q0711 seal (after 2026-11-17T09:00Z; 7); seal committed and pulled on the host.
5. Census q0712; `census_dropped` and `census_unavailable (coverage)` recorded separately; `k_tests` and the census-fixed values
   filled with the exact census floats; a freeze record (module hashes, spec hash, census output hash re-verified).
6. Size check q0713 (2,000 worlds x 200 draws, seed 20261597); results recorded per test; world R1 and the power runs reported.
7. Reader freeze check; host dry run following 8.2's ladder.
8. Embargo entries verified (a missing entry blocks the pin); tokens of dropped tests withdrawn with a ledger line.
9. Pins `SPEC_SHA256`, `code_sha256`, `code_check`; E-numbers assigned; the ledger entry is the registration commit, **before
   2026-12-09T00:00Z** and at least 24 h before `REGISTERED_UTC`.
10. Cron installed and `backfill-series` within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`; `pinned: true` and
    `nothing_new` verified; q0715 queued with `not_before` 2027-01-01T12:00Z.

**Timetable (fast lane, planning):** R1 re-check by 11-01; freeze by 11-06; code and check 11-06..11-16; restore and seal
11-17..11-18; census 11-18..11-19; size check 11-19..11-23; reader check and dry run 11-24..11-30; embargo verification and pin by
12-07; window 12-10..12-31; analysis on or after 2027-01-01T12:00Z.

## 9. Signal-engine mapping and embargo requests
Every family is point-in-time from the origin capture and its 12-slot look-back (DESIGN_V1 16) and an auxiliary family (own
write-once table and version). **The LT12 date** = the later of **2027-01-03T00:00Z** and LT12's analysis commit (ordered lane: the
later of its analysis date plus 36 h and its analysis commit). Filed in `CANDIDATES.md` at the freeze, applied before the
registration commit. This branch edits no engine code, `config.EMBARGO` or `CANDIDATES.md`.

| Test | Family (aux version) | Columns | Token -> until |
|---|---|---|---|
| CH245 | `nrslack` spec on two-member rows (`se-aux-nrslack-v2`) | innovations `nr_twin_dspread`, `nr_thin_x_twin_dspread`; levels `nr_twin_spread`, `nr_gap_ask`, `nr_gap_bid`, `nr_thin` may be built (they fall under LT11's `nrslack` token to 2026-12-12 anyway) | `mirror` (new) -> LT12 date |
| CH244 | `event` / `nrslack` (`se-aux-mixedlad-v1`) | interaction `nr_shock_x_unrew`; levels `nr_mixed`, `nr_unrew_share`, `nr_own_unrew` only after the `rewards` date (2026-11-18) | `mixedlad` (new) -> LT12 date |

- **Pre-freeze hold (now):** no scored family holds a two-member twin's spread innovation or a reward-status x sibling-shock
  interaction before LT12's freeze. If one is scored, the matching test carries *informed (engine)* and the ledger records the
  first scored capture. Levels (`event`'s existing columns) are not requested.
- **Attribution limit `attrlimit_lt12`** to the LT12 date: no attribution of the champion, se1 or any broad model on twin-spread
  interactions inside `event` / `nrslack` or on reward-status x shock interactions inside `event`; `no_broad_families:
  ["mirror", "mixedlad"]`. **No `feeclass` token and no fee-class attribution item** (CH243 dropped, section 4).
- A test dropped at census has its token and any limit item made only for it withdrawn with a ledger line. An engine gain never
  changes an LT12 verdict; an LT12 verdict never promotes a model.

## 10. Disclosures
- **Read to write this file:** `CREATIVE_HYPOTHESES_2026-10-31.md` (sections 0-1, CH243-CH245, CH248, CH250, CH251, section 3),
  `CH251_MAP_2026-10-23.md` (whole), `CH240_MAP_2026-10-23.md` (whole), `LIVE_TESTS_11.md` (sections 0-13), `LIVE_TESTS_10.md`
  (header, 1.1), a bounded read of `EXPERIMENT_LEDGER.md` (the CH251, CH242 and LT11-freeze entries), a grep of
  `population_map_ch251.py` (the fee-class and age definitions; code only), git greps for the seed and queue ids. **For the R1
  response:** `reviews/LT12_CHALLENGER_R1_2026-10-23.md` (whole), `LIVE_TESTS_7.md` 13.7 (the `listed_carry24h_v2` text) and a
  grep of `LIVE_TESTS_8.md` (the declared / design MDE definitions). No host, network, `ssh`, `data-dumps`, evidence JSON,
  census output, prediction, target or P&L.
- **The CH251 map** counted populations on captures 2026-10-13..10-23 (k - 1 and k only; no target, no P&L); seen before every
  gate here (10.1). **The CH240 map** likewise. Neither probed CH245's within-stratum variation or leverage, or CH244's feed
  disagreement.
- **Development looks:** the `event` family's level scores (visible since 2026-10-22T12:00Z); se1 (category one-hot, mid, own
  move); `tilt`'s level challengers se24 / se25; E005, HB1 XM1-XM3 and L1-L4 (ladder mids, closed). None reads an LT12 state as
  defined here; no LT12 designer has read se24 or se25 scores.
- **Not known at the planned freeze:** E015, E022, LT11 results; LT11's census output.

### 10.1 Values declared now and their planning sources
| Value | Where | Source | Informed by the CH251 map? |
|---|---|---|---|
| CH245 thin-only unit; `sym` a class; conditional on asymmetry | 2.2 | dependence, mechanism; ruling A2 | **yes** (thin / sym shares, the per-pair note) |
| CH245 count gate 186 a capture | 2.4, 7 | 2 x the F line at DE 11 | **yes** (chosen with 499 in view) |
| CH245 same-slot 0.8 / 50%, `VIF_w` 2.0, span and completeness 60% | 7 | round 17, unchanged | partly (map pooled correlations seen; values unchanged) |
| CH245 identification: >= 3 non-zero / 50%; top 1% <= 25%; event <= 5%; gap / `s_w` | 6 item 6, 7 | R1 MUST 4; conventions with stated rationale | **no** (none of these quantities was counted) |
| CH245 placebo: series family, disjoint event ids, two-sided; coverage 90% | 2.3, 7 | rule 18; R1 MUST 5 | no |
| CH244 count gates 362 / 181 | 3.4, 7 | 2 x the F line at shock share 0.5 | **yes** (the map's shock share 0.51) |
| CH244 feed gate <= 0.20, coverage >= 50%, feed clock 6 h | 1.2, 6 item 9, 7 | R1 MUST 3; conventions with stated rationale | no (unprobed) |
| CH244 shock 2 ticks, band [0.10, 0.80], corr 0.5, 3-10 members, day-fixed status | 3.2, 7 | round 17; R1 SHOULD 4 | values unchanged; the 11+ arm's thinness informed (0.31) |
| Tier bins $1k / $10k / $100k | 1.4.2 | `cost-model-v1` | yes (the map found no tier) |
| `DE_gate` floor 5.0; `G_eff >= 15` | 7 | LT11 | no |
| Seed 20261597; world R1 seed `x 100 + 54`; q0710-q0715 | 1.8, 7 | unused values | no |
| World 1: `rho_ss = max(rho_census, 0.64)`; bisection on [0, 10] to 0.005, at most 40 steps; one two-member event of 20,000 slots; seed `x 100 + 61` | 1.8.1, 7 | re-check fix 2, final verification fix 3; 0.64 the map's uu pooled same-slot correlation as the floor | **yes** (0.64 is a map number) |
| Dense-twin `>= 2` ticks set floor 5,000 units | 1.9 | re-check fix 7; a quarter of the 20,000-unit Unavailable floor | no |
| Restore `not_before` 2026-11-17T09:00Z | 7 | the last lag slot's start tolerance plus one slot plus 2 h | no |

## 11. Design-ambiguity items and their rulings (R1 A1-A16; re-check B1-B7)
**R1's rulings (2026-10-23), applied:** A1 F binds, CH243 leaves (section 4); A2 thin-only unit accepted, the estimand conditional
on asymmetry, no pooling (1.7, 2.2); A3 levels at k - 1, M4 reported and relabelled *bid-sum mediated* (1.9, 2.3); A4 the placebo
binds, two-sided with the series-family and event-id rule (1.9, 2.3); A5 redefined (6 item 6); A6 valid with the state-shift path
(1.8); A7 carry status primary, feed disagreement printed and gated (6 item 9, 7); A8 acceptable with the joint model (3.3); A9
day-fixed status acceptable, switch shares printed by status (3.2, 7); A10-A12 moot (CH243 dropped); A13 twice the kill line
consistent; A14 CH244's prior reverted and lowered (0); A15 acceptable, disclosure and `pre_window_source` counts kept (1.1, 7);
A16 no change. **Re-check rulings B1-B7 (`reviews/LT12_RECHECK_2026-10-23.md`), applied:**
1. **B1 (CH245 identification numbers): acceptable.** The 3-non-zero / 50% line, the top-1% <= 25% and per-event <= 5% caps and
   the `s_w` term stand; `VIF_w` is computed on the demeaned regressors (7).
2. **B2 (placebo rule): acceptable.** The first-entry `series_slugs` family and disjoint event-id sets stand; placebo coverage
   stays at 90%.
3. **B3 (state-shift gate): valid in principle** (the circular shift keeps serial dependence; one offset per event keeps the
   cross-member structure); its size is approximate, so the size worlds bind; adequate after re-check fix 2; `shock_size` shifts
   with `shock` (1.8).
4. **B4 (CH244 feed gate): a gate is right; 0.20 and 6 h acceptable;** missing coverage is `census_unavailable (coverage)`, not
   a drop (re-check fix 3; 1.2, 6 item 9, 7).
5. **B5 (mixed on day-fixed status): acceptable** (switched and `status_nan_unit` members count toward "mixed" by their finite
   day-fixed status; their own units are excluded; 3.2).
6. **B6 (the dense-twin floor): resolved by re-check fix 7.** The dense `spread_k >= 2` ticks set is **binding**: condition (a)
   of 1.9 must hold on the full set and on that set (both-sets rule; under 5,000 units on that set, at most Inconclusive). World
   R1 (1.8) prints the condition's pass rate on each set and on both together; its pass rate is a printed diagnostic of the
   binding rule, not a separate condition.
7. **B7 (priors): arithmetic correct; the lower CH244 prior justified** (0: CH245 0.30, CH244 0.15; expected k 0.45; P(no test)
   0.60).

## 12. Ledger block for the freeze (not registered, not counted)
```
## LT12 design-text freeze, 2026-10-23 (experiments autopilot; nothing counted)
- docs/research_lab/LIVE_TESTS_12.md on feat/live-tests-12 revised for R1 (REVISE; 6 must-fix, SHOULD 1-5 and 7, rulings
  A1-A16): CH243 dropped (LT11 R1 A4: no label-only F chosen for power); k <= 2: CH245 (the mirror), CH244 (the farmed half).
  Re-check ACCEPT_WITH_FIXES (fixes 1-7) and final verification FIXES_REQUIRED (wording 1-5) applied; DESIGN TEXT FROZEN
  2026-10-23 (sha256 in this entry), not registered. Census seal [11-07, 11-17); window 12-10..12-31; analysis after
  2027-01-01T12Z. Designer's census odds 0.30 / 0.15; P(no test) about 0.60.
```

## 13. R1 response (2026-10-24; designer; every item mapped to the changed section and lines)
Line numbers in this table refer to the R1-response revision 6fc72f57 (sha256 `c879bbeb…31e9`); section 13.x maps the re-check
fixes to the lines of this revision.

| R1 item | Applied | Section and lines | What changed |
|---|---|---|---|
| **MUST 1** drop CH243 | applied | 0: 43-75; 1.0: 80-91, 107; 1.8: 272-319; 1.9: 354-386; 4: 593-613; 6 item 12: 673-674; 9: 813-832; 12: 889-896 | CH243 removed (census block, first-draft worlds 11-15, `feeclass`, the fee-class attribution item, *informed (E015)*); k <= 2; the drop and its reason recorded in section 4 with LT11 R1 A4 credited; CH243 kept as an engine-first note |
| **MUST 2** reward-status cases | applied | 1.2: 156-159; 1.4.1: 192-209; 8.3: 772-790 | the three cases of `listed_carry24h_v2` stated exactly: (a) listed at s, (b) null at s -> carried 1 or else 0, (c) NaN only for a malformed cell or an absent sidecar row; unit tests for each |
| **MUST 3** CH244 carry / feed | applied | 1.2: 160-163; 1.4.1: 205-208; 3.5: 574-587; 6 item 9: 660-669; 7: 711, 723-728 | null -> 0 disclosed; census prints the carry-against-simple confusion, the case counts, the mixed counts under both readings and the feed table with coverage; declared a **gate** (feed-listed share <= 0.20 among covered tested units, coverage >= 50%, NaN fails, feed clock 6 h), with the reason for a gate over a label and for each number |
| **MUST 4** CH245 identification gate | applied | 2.4: 470-487; 6 item 6: 641-654; 7: 699-707, 710, 713-722 | the round's unit-mismatched SD gate replaced by within-stratum variation (>= 3 non-zero innovations in strata holding >= 50% of units), a leverage cap (top 1% <= 25%, one event <= 5%) and an MDE that divides the gap by the measured SD `s_w` of the demeaned state; written justification, and the statement that it is not tuning (no form was ever counted) |
| **MUST 5** two-sided placebo | applied | 1.4.3: 215-226; 1.9: 363-364; 2.3: 460-463; 6 item 3: 633-635; 7: 710 | `|betâ_placebo| < 0.5 x betâ_thin`; e' must share no series family and no event id with e; `placebo_none` counted; coverage gate 90% kept |
| **MUST 6** gate path | applied | 1.8: 273-290; 6 item 5: 637-640; 8.1: 749-759; 8.3: 782-786 | `event_day_state_shift_gate` (new code, not "vendored unchanged"): raw state shifted with one offset per event, interactions recomputed, expanding-past event x UTC-day demeaning re-applied every draw, demeaned values never shifted; worlds 1-5 and 7-9 run this path; unit test plus a refusal fixture |
| **SHOULD 1** dense twin and the floor | applied | 1.8: 309-314; 1.9: 380; 2.3: 458-459; 2.5: 488-506 | variant on dense `spread_k >= 2` ticks (*floor-sensitive* label); reported world R1 (symmetric lead-lag with the 1c floor) printing the point-condition pass rate |
| **SHOULD 2** four-cell MDE | applied | 3.4: 566-571; 6 item 11: 671-672; 7: 699-707 | interaction variance from all four cells; the planning values are unchanged at shock share 0.5; the census uses the measured cells |
| **SHOULD 3** joint model | applied | 3.3: 548-549; 1.9: 384 | joint model with `shock x unrew` and `shock x lowliq` reported; *liquidity-shared* label |
| **SHOULD 4** mixed on day-fixed status | applied | 3.2: 522-532; 6 item 7: 655-658 | status fixed per member-day at its first eligible capture; mixed judged on day-fixed statuses; switch shares printed by status |
| **SHOULD 5** CH244 prior | applied | 0: 61-75; 11 B7: 887 | reverted and lowered to 0.15 (simple-reading counts, low planning 104 < 362, the new feed gate); the weak correlation no longer counted in its favour |
| **SHOULD 6** "median 71" | moot (CH243 dropped); corrected in the note | 4: 610 | the two medians (64, 7) stated as separate medians |
| **SHOULD 7** M4 is a bid-sum label | applied | 1.9: 376-379; 2.3: 467; 6 item 2: 628-632 | M4 = the primary with `hb_k` in place of `hb_{k-1}`; label renamed *bid-sum mediated*, with the algebra |
| **Rulings A1-A16** | applied | 11: 864-871 (and the sections each names) | A1 drop; A2 conditional-on-asymmetry wording, no pooling; A3 k - 1 levels; A4 placebo binding; A5 MUST 4; A6 with MUST 6; A7 MUST 3; A8 joint model; A9 switch prints; A10-A12 moot; A13 kept; A14 SHOULD 5; A15 disclosure and `pre_window_source` kept (1.1: 135-139); A16 no change |
| **Priors, P(no test), expected k** | applied | 0: 61-75; 12: 891-896 | CH245 0.30, CH244 0.15; expected k 0.45; P(no test) 0.70 x 0.85 = 0.595, about 0.60; expected valid verdicts about 0.15 |

**Not applied:** none. **No threshold was loosened, with one qualification (re-check fix 5):** part (i) of CH245's new
identification gate (non-zero innovations in event-day strata) is not comparable to the first draft's raw-SD reading, so it
cannot be called tighter or looser; it is compensated by two added conditions, the `s_w` term in the declared MDE (a state that
barely moves inside event-days raises the MDE) and the leverage caps (top 1% <= 25%, one event <= 5%). Changes that tighten or add
conditions: the two-sided placebo with the
series-family and event-id rule; the feed gate; the leverage caps and the `s_w` term in the MDE; CH244's prior. The one gate
that was replaced rather than tightened (CH245's identification gate) is replaced because its round-17 form mixed units; its
new form was written before any count of either form existed (6 item 6). **New thresholds declared in this revision, each with
its rationale in the section named:** >= 3 non-zero innovations / 50%, top 1% <= 25%, one event <= 5% (6 item 6); feed-listed
share <= 0.20, coverage >= 50%, feed clock 6 h (6 item 9); world R1's loading 0.4 and seed (1.8); **and, added by the re-check
and the final verification:** the 0.64 floor of `rho_ss`, the bisection bracket [0, 10], tolerance 0.005, calibration length
20,000 slots on one two-member event, seed `20261597 x 100 + 61` and the 40-step maximum (1.8.1); the 5,000-unit floor of the
dense `spread_k >= 2` ticks set (1.9); the restore `not_before` 09:00Z (7). Nothing is left to the census except the values
listed as census-fixed in 7.

### 13.x Re-check response (`reviews/LT12_RECHECK_2026-10-23.md`, ACCEPT_WITH_FIXES; fixes applied as worded)
Line numbers refer to this revision of the file. No threshold is loosened; fixes 1-4 and 7 add or tighten conditions.

| Re-check item | Section and lines | What changed |
|---|---|---|
| **Fix 1** gate statistic and sample | 1.8: 279-301; 8.3: 818-828 | the statistic is the tested coefficient's event-clustered CR1 t, identical for the observed fit and every draw; the gate sample is the events with `n_e >= 16`, and the observed t is refitted on that same sample; the size worlds run the same path; unit test added |
| **Fix 2** world 1 loading and `n` ranges | 1.8.1: 339-348, 362-363; 7: 753-755; 8.3: 818-828 | world 1's loading `lambda` is set by a declared bisection so the planted within-event same-slot correlation equals `rho_ss = max(rho_census, 0.64)`; `rho_census` (pooled same-slot correlation on CH245 census thin units) added to the census-fixed list as item (9); worlds 1 and 7 (and the worlds built on them) draw `n` uniform on 8..252, so `n_e < 16` occurs |
| **Fix 3** feed coverage and outcomes | 1.2: 165-169; 6 item 9: 687-698; 7: 722-727, 744; 8.3: 818-828; 11 B4: 924-925 | coverage under 50% (an outage included) -> CH244 `census_unavailable (coverage)`, checked first in CH244's block, re-census only in the ordered lane as its own Holm family; a feed-listed share above 0.20 on adequate coverage -> `census_dropped` |
| **Fix 4** NaN own status | 3.2: 546-553; 8.3: 818-828 | a unit whose own status at k - 1 is NaN is excluded and counted (`status_nan_unit`), never given the day-fixed status |
| **Fix 5** "no threshold loosened" qualified | 13: 963-968 | part (i) of CH245's identification gate is stated as not comparable to the first draft's raw reading, with the compensating `s_w` MDE term and leverage caps named |
| **Fix 6** expected valid verdicts | 0: 74-79 | derived: 0.30 x 0.5 x 0.9 + 0.15 x 0.6 x 0.9 = 0.216, about 0.2 (was an underived 0.15) |
| **Fix 7** dense-twin condition on both sets | 1.8: 320-327; 1.9: 382-394; 2.3: 480-483; 2.5: 522; 8.3: 818-828 | condition (a) must hold on the full set and on the dense `spread_k >= 2` ticks set; that set under 5,000 units -> at most Inconclusive (*dense-twin unavailable*); the *floor-sensitive* label is removed (now part of the condition); world R1 reports both sets and their conjunction |
| **B1 note** | 7: 743-744 | `VIF_w` stated as computed on the expanding-past event x UTC-day demeaned regressors (both tests) |
| **Restore margin (not a numbered fix; "not verified" in the re-check)** | 7: 773-779; 8.4: 841 | `q0710`'s `not_before` moved from 2026-11-17T06:00Z to **09:00Z**: the last lag slot (04:31Z) may start up to 05:01Z under the 30-minute tolerance and needs up to one slot to be `state=complete` with its sidecar (final about 07:01Z), so 06:00Z was too tight; 09:00Z keeps 2 h of margin, and the restore also refuses while a lag-slot capture is neither complete nor past its tolerance |
| **Rulings B1-B7** | 11: 907-930 | B4 recorded as ruled; the others accepted as ruled (B2 keeps 90% coverage; B3 `shock_size` shifts with `shock`, as written in 1.8) |
| **Status line** | header: 3-6, 12-13 | DRAFT: R1 REVISE, response, re-check ACCEPT_WITH_FIXES, fixes applied; final verification pending |

### 13.y Final pre-freeze verification response (FIXES_REQUIRED, wording only; applied in the freeze commit)
Line numbers refer to this frozen revision. Nothing is loosened; fixes 2 and 3 close a deadlock and an undefined branch.

| Item | Section and lines | What changed |
|---|---|---|
| **Fix 1** section 11 | 11: 920-945 | retitled as rulings; B1-B7 recorded as the re-check ruled them; B6 points to re-check fix 7 (the dense `spread_k >= 2` ticks set binding through the both-sets rule); no "reported and non-binding" wording remains (world R1 is a printed diagnostic of the binding rule, 1.8: 322-329) |
| **Fix 2** restore refusal | 7: 781-789 | the restore refuses only while a lag-slot capture is in progress; a capture in a final non-complete state (failed or partial) counts as missing, as a file found nowhere does, so the one-shot restore cannot deadlock |
| **Fix 3** bisection failure rule | 1.8.1: 343-357 | calibration on a single two-member event of 20,000 slots; `rho_census` NaN, `rho_ss` not bracketed in [0, 10], or no convergence within 40 steps -> world 1 (and world 3, which inherits `lambda`) "SE check failed (size scenario)" for CH245; nothing else tried |
| **Fix 4** `rho_census` interval | 7: 760-764 | `Δspread_T` and `Δspread_D` both over (k - 1, k] at the same capture pair, matching world 1's "same slot"; NaN on zero variance |
| **Fix 5** stale cross-references and lists | header: 13-17; 1.1: 148-149; 8.4: 845; 10.1: 916-918; 12: 946-955; 13: 987-990; 1.8: 304-305 | the final verification named as the acceptance in the header, 1.1 and 8.4 step 1; the ledger block no longer says "re-check pending"; 10.1 and section 13's threshold list add 0.64, [0, 10] / 0.005 / 20,000 slots, seed `x 100 + 61`, the 40-step maximum, the 5,000-unit floor (and the 09:00Z restore time); indent fixed |
| **Status line** | header: 3-7 | FROZEN (design text) 2026-10-23 after R1 REVISE, response, re-check ACCEPT_WITH_FIXES, fixes, final verification FIXES_REQUIRED (wording) applied; not registered; E-numbers unassigned; sha256 recorded in `EXPERIMENT_LEDGER.md` |
