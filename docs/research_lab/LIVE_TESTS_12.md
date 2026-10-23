# Live tests 12 (LT12): the mirror and the fee (CH245, CH244, CH243), DRAFT pre-registrations

**Status: DRAFT. NOT FROZEN. Challenger R1 not run. Not registered. Nothing counted, no code, no seal, no census run.
E-numbers unassigned.** Drafted 2026-10-23 on branch `feat/live-tests-12` from the `chore/arepo-claude-setup` tip `1e89423d`,
a design-only first commit like the first commits of LT3-LT11. LT12 takes the next free E-numbers at its own registration,
in the order CH245, CH244, CH243 (round 17's rank order). If every test drops at its census, LT12 is not registered
(recorded in the ledger; nothing counted). Before registration this needs, in order:
1. a challenger review (`science-reviewer`, R1) of this file, a written response, and a re-check;
2. the **design-text freeze commit** (1.1) **before the LT12 seal commit and before `T_LT11`** (fast lane), planned by
   2026-11-06 so that it also precedes LT11's census commit (`T_LT11c`, 1.1); otherwise the ordered lane applies;
3. the code (section 8) with a `science-reviewer` freeze check of the census and size-check code against 1.8, 1.8.1 and 7,
   on synthetic data only;
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
*informed by the map*; 6 marks each design change made after it [map] and 10.1 lists the values. The map's span is disjoint
from LT12's census span [2026-11-07, 2026-11-17) (7), so every LT12 gate is still declared before its own census on a fresh
seal. The map is a planning input only; nothing in it enters a census, the size check or an analysis.

Source ideas: `CREATIVE_HYPOTHESES_2026-10-31.md` (round 17) section 3, ranks 1-3 and their sketches: **CH245** (the
mirror), **CH244** (the farmed half) and **CH243** (the fee as the price of urgency, conditional), taken in the round's own
recommendation ("CH245, CH244 and (conditionally) CH243 are the three ... after CH251's map"). Written to round 14's rules
1-11, round 15's 12-14, round 16's 15-17 and round 17's 18-20, to LT4's lessons L1-L15 and the rulings LT7-LT11 carry
(1.0). LT12 reuses LT11's conventions (`LIVE_TESTS_11.md`, frozen at 3627d7fd) unless a line here says otherwise and why.

## 0. Summary

| Handle | Hypothesis (direction, one-sided) | Unit of analysis (dependence) | Primary | Planning MDE low / high; quarter; F-MDE | Floor |
|---|---|---|---|---|---|
| **CH245** the mirror | In a complete two-member neg-risk event, the **thin** book's spread change over (k, k + 1] rises with the **dense** book's spread innovation over (k - 1, k], given the thin book's own innovation, both spread levels, the bid headroom and K (> 0); the dense book's slope on the thin book's innovation is < half (binding point condition); an unrelated pair's innovation is < half (binding placebo condition) | **one unit per asymmetric pair-capture** (the thin member; event-deduplicated by construction); clusters event | expanding-past event x UTC day demeaned OLS of `ds_T` on `zs_D`; event-phase block FL gate (one offset per event); F binding | 200 / 500 thin units a capture: DE 6 **0.32c / 0.20c** (quarter 0.64c), F 0.50c / 0.32c; DE 11 0.43c / 0.27c, F 0.68c / 0.43c; DE 31 0.72c / 0.46c, F 1.14c / 0.72c | 1.0c |
| **CH244** the farmed half | In a complete mixed ladder (3-10 members, >= 1 rewarded and >= 1 unrewarded), after a sibling shock (largest sibling 2 h move >= 2 ticks) the **unrewarded** members' spreads widen more than the rewarded members' in the same event-day (`shock x unrew` > 0), tier x shock held; the within-event low-liquidity twin is < half (binding point condition) | member x capture; clusters event; DE 31 (formula) | expanding-past event x UTC day demeaned OLS of `ds_i` on `shock x unrew`; event-phase block FL gate; F binding | 104 / 1,548 tested units a capture: **0.83c / 0.26c** (quarter 1.67c), F 1.32c / 0.42c | 1.0c |
| **CH243** the fee (conditional) | Within market, the traded-minus-quote-only continuation of 2 h movers is larger on the **fee-on** panel than on the **fee-free** panel, within census-fixed tier x category x age cells (`traded x fee_on` > 0); quote-only panel contrast < half in absolute value (binding point condition) | mover x capture; market panel fixed at its first unit (rule 20); clusters event | expanding-past market-demeaned OLS of `c` on `traded x fee_on`, cell x traded held; block FL gate (market); **F a reported label** (6 item 9) | 52 / 322 fee-free traded units a capture (750 fee-on): **0.84c / 0.39c** (quarter 1.65c); F 1.26c / 0.58c (label) | 0.5c |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E022), LT5-LT11, E025 and E026. **Provisional k <= 3.** Each test is killable independently at
  its census; a failed gate drops it before registration (`census_dropped`, uncounted, final in both lanes); a test whose
  coverage check fails is `census_unavailable (coverage)` (7) and may be re-censused only in the ordered lane as its own Holm
  family. k is fixed in the spec (`k_tests`) at registration. A primary that is unavailable or fails its gate enters Holm with
  p = 1. No replacement test after a drop.
- **Window (fast lane, 1.1):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, **`REGISTERED_UTC =
  2026-12-10T00:00:00Z`**, `END_UTC = 2026-12-31T00:00:00Z`, 21 days; single analysis on or after **2027-01-01T12:00:00Z**.
  Census on a fresh seal of **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**. Freeze before the seal commit and before `T_LT11`.
- **Labels certain in both lanes:** CH243 *informed (E015)* (the traded class; every LT12 census and pin follow `T_E015`);
  CH244 *informed (E022)* (E022's S2 reward split; the census follows `T_E022`). Lane-dependent: 1.1.
- **Honest survival priors (the designer's judgement after the CH251 map, not measurements; round 17's priors in brackets).**
  **CH245 0.30 [0.30]:** the map removed the round's main risk (639 complete pairs a capture against 100-400 events
  planned; receipt-span retention 1.000; completeness 0.97-1.00), but it exposed a new one: the two books move together in the
  same slot (pooled same-slot correlation 0.64 on unrewarded pairs, 0.38 on rewarded pairs), which feeds the same-slot
  correlation gate, the `VIF_w` gate and the within-event SD gate (a single book's spread innovation on a 1c grid may vary by
  less than one tick in most events). Count risk is now the post-midterm December panel only. Same level, different
  composition. **CH244 0.30 [0.20]:** the round's likeliest killer (the status-liquidity correlation) is weak on the map
  (-0.05 pooled, -0.09 within event) and the shock share is 0.51-0.53, inside its band; but the map read reward status as
  "`clob_rewards` non-empty at k", and that field is omitted on about 62% of rows (round 14 fact 3), so a large part of the
  map's "mixed" ladders may be rewarded members whose field was omitted. Under `listed_carry24h_v2` the mixed population can
  shrink by an unknown factor, and the count gate (362 tested units a capture) is set at twice the kill line. **CH243 0.04
  [0.10 conditional]:** the mean fee-free traded count (346 a capture) clears the round's 160 line, but the medians are 64
  (rewarded) and 7 (unrewarded) and a block of captures holds most of it; the gate is on the median (170) with a
  capture-concentration gate and a fee-switch gate, all of which the map's pattern would fail; and if the challenger rules
  that F must bind (A1, 11), CH243 leaves the family before the freeze. **Expected k at census about 0.64; P(no LT12 test)
  about 0.47** (0.70 x 0.70 x 0.96, treating the fates as independent, which they are not: CH245 and CH244 read the same event
  join and all three read the same captures). Expected valid verdicts about 0.25. Every taker cell is expected "not shown".
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
projected counts; **whether F binds is fixed per test now, by design**; `listed_carry24h_v2` for every reward status; distinct-
event gates unprojected; `census_unavailable (coverage)` distinct from `census_dropped`; Kish `G_eff >= 15`). Lessons (i) and
(ii) of LT11 1.0 bind: every count gate is at or above the binding kill line at the base planning values, and every share
gate is either measured by the map (margin stated) or flagged unprobed (10.1).

Round 17's rules map onto LT12 as follows (rules 1-17 as in LT11 1.0's table, applied to these units):

| Rule | LT12 rule |
|---|---|
| 1. Panel-complete units | every unit is a market x capture of the complete captures and their sidecar; no sweep, sample or monitor in any primary |
| 3. Innovations, not levels | CH245 the dense book's spread change over (k - 1, k]; CH244 a sibling move at (k - 1, k]; CH243 a move and its traded class at (k - 1, k]; every level is a control |
| 5. Field semantics first | 1.4.2 (tier from `liquidity`), 1.4.3 (fee panel), 1.4.4 (event key, pair and ladder completeness), 4.2 (`volume_num` classes) |
| 7. DE and kill line | planning DE 6 / 11 / 31 (CH245), 31 (CH244), 6.196 (CH243); census `max(floor, computed)`, floors 5.0, 5.0, 6.196; kill lines stated per test |
| 8. Floors | 1.0c (CH245, CH244 spread targets), 0.5c (CH243 2 h mid); the F-MDE cap equals the floor |
| 9. Fresh seal | `[2026-11-07, 2026-11-17)`, disjoint from the CH251 and CH240 map spans, LT11's census seal and LT11's window |
| 11. Maker-side money routes | every primary route is maker-side, gross, no fills; taker cells reported (1.10) |
| 16. Event-join completeness | CH245 pairs and CH244 ladders complete at k - 1 and k with the 120 s receipt span at both; incomplete ones counted, never filled |
| **18. The mirror rule** | CH245's state is the twin book's innovation on pair-captures complete at k - 1 and k; the twin's level and the own innovation are controls; demeaning stratum event x UTC day; the unrelated-pair placebo is a binding point condition (2.3) and a binding size world (1.8 world 3) |
| 19. Third price | not used (CH242 was killed at its own census on 2026-10-23; no LT12 test reads a resolution) |
| **20. Fee class is a panel** | CH243's fee class is a market-level constant fixed at the market's first unit; it never enters as a within-market state; the tested term is the panel contrast of a within-market coefficient; inference cluster-robust across events; the FL gate tests the within-market term only and the composition worlds of 1.8 carry the between-panel part |

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
  | CH243 | **E015** (`T_E015`, about 2026-11-15T12Z) | E015 tests the traded class, CH243's within-market term | *informed (E015)* in both lanes (census and pin follow it), certain; the freeze before it keeps the design text blind |
  | CH244 | **E022** (`T_E022`, about 2026-11-17T12Z) | E022's S2 splits traded movers' depth by reward status | *informed (E022)* in both lanes, certain |
  | CH244 | **LT9 CH213** (window from 2026-12-30) | the rewarded panel and `listed_carry24h_v2` | time overlap of at most one day; different states; no pooling |
  | all | LT10, E026 (to 2026-12-07), LT9's reader | time only | different streams or states; no pooling |

  If LT11's window is not the fast-lane window (LT11 lapsed), "LT11's window" in this file means LT11's registered window, and
  LT12's census span and window must be disjoint from it.
- **Boundary.** A unit's oldest state input is capture k - 1, so the first origin is the first capture whose capture k - 1
  starts at or after `REGISTERED_UTC` (proposed 2026-12-10T02:31Z); earlier captures give no unit (`lt12_boundary`). Look-backs
  (`rv24*`, 6 h and 24 h changes, the 12-slot carry window) may read captures of 2026-12-09 (counted `pre_window_source`). Those
  captures lie after LT11's `END_UTC`; LT11 reads some of them as target or twin slots of its last origins. LT12 reads them as
  raw rows and sidecars only and computes none of LT11's objects (A15). The last origin is the last capture starting before
  `END_UTC`; its targets (k + 1) and twins (k + 3) are read.
- **Design-text freeze.** After the challenger's acceptance (R1 and its re-check), a commit records this file's sha256 in the
  ledger. Afterwards the text changes only by the census-fixed values named in 7 and by code-freeze-check fixes that change no
  state, unit, target, estimator, gate, threshold or verdict rule. The embargo requests of 9 are filed at the freeze.
- **Fixed end, no extension; one analysis** (`run_live_tests12.py analyze` refuses before the analysis date; `--out` refuses
  to overwrite). Effective start = max(`REGISTERED_UTC`, the first capture processed by the reader at the pinned commit); only
  lines whose `spec_sha` and `code_sha` equal the pins and whose role is `prospective_confirmation` are kept.
- **Time of year (disclosed).** No DST change in the census span or the window. The census span follows the US midterm
  (2026-11-03) and its resolution days 11-04..11-06, so it measures the post-midterm two-member panel, which is the one December
  will hold. The window holds the holiday fortnight: a sensitivity without origins in `[2026-12-24T00:00Z, 2026-12-27T00:00Z)`
  is reported (*holiday-sensitive*); no gate depends on activity level.

### 1.2 Streams read (all already written by the host's pass; no new collector, no network)
- **Captures** `snapshots/<id>/rows.csv.gz` (`state=complete` only): `bid`, `ask`, `spread`, `last_trade_price`, `volume24hr`,
  `liquidity`, `chg_1h` (and `chg_1d`, `chg_1w` if the header pre-check finds them), `end_date`, `event_id`, `neg_risk`,
  `neg_risk_market_id`, `neg_risk_other`, `event_neg_risk_augmented`, `closed`, `active`, `received_utc`, the manifest start.
- **Sidecar** `rows_ext.csv.gz`: `received_utc`, `fee_type`, `fee_category`, `fee_schedule`, `fees_enabled`, `created_at`,
  `series_slugs`, `order_price_min_tick_size`, `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, `volume_num`,
  `accepting_orders`, `event_ids`. A missing sidecar row sets category, tick, fee class and age unknown, reward status NaN and
  `volume_num` missing (`sidecar_missing`).
- **CLOB reward feed** `reward_params/<capture_id>/` (one feed clock: the last usable feed capture before capture k - 1's start):
  only CH244's *CLOB-disagreement* sensitivity and economics; never a state or a gate.
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
- **Decision time (all three): capture k's last row receipt** (the largest `received_utc` over capture k's complete rows and
  sidecar rows): CH245 reads two rows of capture k, CH244 every member of an event, CH243's cells read capture k's `liquidity`.
  States read captures k - 1 and k and the 12-slot look-back. **Targets start at capture k + 1.**
- **Within-capture receipt order (CH245, CH244; LT11 MUST 1's rule):** a pair or ladder whose eligible members' `rows.csv.gz`
  `received_utc` span exceeds **120 s** at k - 1 or k gives no unit (`receipt_span`, counted). The residual overlap (at most
  120 s of a 2 h target) is disclosed, and size world 2 (S31) plants the leak it could carry.
- **Late rule** as LT4 1.3 (*late-loss* above 2%). **Twins (F)** read captures k + 2 and k + 3 through the lag-slot loader; the
  unit builders do not read them (causality test, 8.3).

### 1.4 Shared origin-side eligibility
LT11 1.4 applies (vendored `move_join`, `classify`): binary, open, active; two-sided at k - 1 and k (bid > 0, ask < 1); tight
(spread <= 0.10 at both); end unknown or > `t` + 3 h (F arm: > `t` + 7 h, else `f_end_short`); category by
`cb17_census.is_sports_sidecar` (non-sports primaries; sports arm reported, uncounted); crypto excluded by the pinned
classifier (unknown counted and treated as crypto); `scope: non_sports_ex_crypto` fixed at the freeze unless an owner decision
is recorded before it; one row per `condition_id`; tick equal at k - 1 and k (`tick_changed`); series-family rule (census
top family > 40% of a primary population is excluded, `<test>.exclude_family`).

### 1.4.1 Reward status
Every `rewarded` flag is **`listed_carry24h_v2` exactly as `LIVE_TESTS_7.md` 13.7 and its erratum define it**, vendored from
`live_tests7.py` (sha256 `e1c5c0c6…`), with the 12-slot carry window ending at the slot named by each test (CH244: k - 1;
CH245 and CH243 controls: k); nothing after it is read; malformed or missing is NaN (excluded, counted).

### 1.4.2 Liquidity tier (defined from capture fields; the map found no tier definition)
`tier_{i,j}` = the cost model's liquidity bins (`COST_MODEL.md`, `cost-model-v1`) applied to the row's `liquidity` at capture
j: `< $1k`, `$1k-10k`, `$10k-100k`, `>= $100k` (four classes; a missing `liquidity` is NaN, excluded, counted). It is read at
k - 1 for CH244's tier x shock control and CH243's cells, and at k as a K control everywhere. No other tier exists in LT12.

### 1.4.3 Fee panel (CH243; rule 20)
From the origin sidecar only, in this order (the CH251 map's `fee_class`, vendored by hash): `fees_enabled` present, non-empty
and false -> `fee_free` (`fee_src = flag_off`); else `fee_schedule.rate` finite and <= 0 -> `fee_free` (`rate_zero`); rate > 0
-> `fee_on` (`rate_pos`); otherwise `fee_unknown` (excluded, counted; **never inferred from the category, the age or any other
field**; the category-rate reading is a reported sensitivity only). **The panel is a market constant:** fixed at the
market's first CH243 unit in the window (in the census, its first unit in the census span); a later unit whose reading differs
is excluded (`fee_switched`, counted). Age class from `created_at`: `pre_0330` (before 2026-03-30T00:00Z), `post_0330`,
`age_na` (its own class). Market age `log1p` days since `created_at` at k enters K for CH243 with an `age_unknown` indicator pair.

### 1.4.4 Neg-risk event key and completeness (CH245, CH244; LT11 3.2 vendored)
Event key `neg_risk_market_id` where present and non-empty, else Gamma `event_id` among `neg_risk` rows (`nr_key_conflict`
counted, keyed by `neg_risk_market_id`). Eligible members at capture j: rows with the key, `neg_risk` true, binary, open,
active; "Other" and placeholders are members. An event with any eligible member `event_neg_risk_augmented` true (or missing)
at k - 1 or k is outside both primaries (`augmented`; a reported arm). **Pair- or ladder-complete (k - 1, k):** identical
member set at k - 1 and k (`members_changed`), every member two-sided at both (`event_incomplete`), member receipt span <= 120 s
at both (`receipt_span`); sports, crypto or unknown category on any member excludes the event. Incomplete event-captures give
no unit for any member; nothing is filled, no bid set to 0, nothing carried. `tick_e,j` = the largest member tick at j.

### 1.5 Missing data, per-capture status and attrition (never imputed)
As LT11 1.5: every frozen unit receives one write-once status at every target slot (`two_sided`, `one_sided`, `closed_flag`,
`absent`, `capture_missing`); only `two_sided` has a target (CH245: the thin member's row at k + 1; CH244: the member's row;
CH243: the market's row). Indicator-pair exceptions only as LT11 1.5 (`hte_unknown`, `vol_missing`, `mom_missing`, `chg1d_missing`,
`chg1w_missing`) plus `age_unknown` (CH243). **`volume_num` is never an indicator pair:** for CH243 it defines the class (4.2);
elsewhere unused. A missing state or control is NaN (excluded, counted), never 0. A missing F state leaves the unit in the
primary and out of the F arm. **Attrition rule:** |a_1 - a_0| > 2 pp in target availability between the contrasted groups
(CH245: top against bottom census tercile of `zs_D`; CH244: unrewarded against rewarded members on shock captures; CH243:
fee-on against fee-free traded units) gives *attrition-differential* and Lee-type bounds, never a verdict change.

### 1.6 What is not looked at before the analysis date
No mid, spread, move, target, P&L, regression or plot from `live_tests12/` files or in-window captures for these hypotheses;
only `run_live_tests12.py ops-stats` (file, line, role, class, panel and status counts; reads no price, spread, volume or
liquidity column; unit test). No change of thresholds, scales, populations, estimators or k after registration. **No LT12
designer, coder or reviewer reads E015's, E022's, LT9's, LT10's or LT11's analysis outputs before the pin, nor LT11's census
output before the freeze** (after it, any change carries *informed (LT11 census)*). **Census-span data:** nobody opens any
capture or sidecar of the census inputs (span, look-back, lag slots) before the seal commit, except the header pre-check
(headers only) and the restore's byte and sha256 checks; development uses synthetic data or files outside those slots.

### 1.7 Estimators, units of analysis and inference
- **Sign convention.** Every tested coefficient is predicted > 0; every MDE a magnitude.
- **Units of analysis (dependence-aware, declared now).** CH245: **one unit per asymmetric complete pair-capture** (the thin
  member), so the two near-duplicate targets of a pair in one slot are never both in a model; the dense member is the point
  condition's unit on the same pair-captures. CH244: member x capture (the contrast is within event-capture); the reported
  event-capture aggregate (mean `ds` of unrewarded minus rewarded members per event-capture, regressed on `shock`) is the
  deduplicated sensitivity. CH243: mover x capture, at most one per market-capture; the market-deduplicated estimate (first
  unit per market-day) is reported. In all three the inference cluster is the event.
- **Expanding-past demeaning** (LT2-LT11): each regressor minus the mean of the stratum's strictly earlier units of the same
  test; target raw; the first unit of each stratum drops. **Demeaning strata:** CH245 and CH244 event x UTC day (rule 18 and
  round 17's sketch); CH243 the market (LT11 CH234's form; rule 20's within-market term).
- **Known-factor block K** (LT11 1.7 unchanged): `p_k`, spread_k, `log1p liquidity`, `log1p volume24hr` (`vol_missing`), log hours
  to end (`hte_unknown`), `1[tick = 0.001]`, `z log rv24*`, `rewarded_k`, non-sports `fee_category` dummies, 11 slot-of-day
  dummies, own `d_k`, own 6 h and 24 h changes (`mom_missing`), `chg_1h` (and `chg_1d`, `chg_1w` as indicator pairs if the
  header pre-check finds them; committed before the seal). CH243 adds market age (1.4.3). `neg_risk` is constant within CH245
  and CH244 and dropped there.
- **Standard errors and p (L10):** CR1 on event, two-way event x UTC day, and UTC day; one-sided **p = max(p_event on t with
  `G_event - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**; conservative 95% CI = hull of a 2,000-draw event
  bootstrap and the three Wald intervals; `G_eff` printed beside `G_event` and floored at 15.
- **Dependence sensitivities (reported, never the verdict):** event x two-day block CR1; the fixture-day group
  (`DEPENDENCE_CLUSTERING_ANALYSIS.md`'s `fixture_day_sidecar`) in place of the event; the deduplicated estimates above; the
  both-demeaned refit (LT6); a market-demeaned refit for CH245 and CH244.
- **Rolling states.** CH245: the dense member's innovation over (k, k + 1] is the next unit's state and overlaps this unit's
  target interval, and the two books co-move in the same slot (the map's 0.38-0.64), so the state at k + 1 is correlated with
  the target at k. CH244: the siblings' moves over (k, k + 1] are the next unit's shock and move the member's spread at k + 1.
  CH243: `d_{k+1}` (the target move) defines the next unit's mover status and sign. All three are rolling (LT7): block gates for
  all; F binding for CH245 and CH244; for CH243 F is a label and verdict-size worlds 13-15 carry its burden (6 item 9, A1).

### 1.8 Gates (valid within-unit nulls) and their size
- **Block (circular-shift) Freedman-Lane gate** (LT5's `block_fl_gate`, vendored unchanged; 200 draws; passes if `p_perm <
  0.05`; offsets from `[s, n - s]`, `s = max(4, ceil(n / 4))`; strata with fewer than 16 shiftable rows excluded and counted).
  **Gate strata:** CH245 and CH244 **the event, one common offset per event on the event's capture index** (LT11 CH233's
  event-phase form, including its omission rule: a member lacking the shifted position is omitted from that draw's refit, never
  filled; omitted share printed). Event x UTC day strata cannot be used for the gate: a pair holds at most 12 thin units a day,
  under the 16-row minimum (6 item 5). CH243 the market (shifts within fee-on and fee-free markets alike; it tests the
  within-market traded term only, rule 20).
- A failed gate on data gives p = 1 in Holm and "SE check failed (gate on data)".
- **Size check, after the census.** `size-check` runs once on the code to be pinned, **2,000 worlds x 200 draws, seed
  20261597**, limit **0.058** (= 0.05 + 1.645 sqrt(0.0475 / 2,000)), every gate scenario through the analysis's
  `block_fl_gate` path and minimum; a world is generated once and evaluated under each test it binds. No effect of the tested
  term in any world.

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | **S30:** common event volatility shock widening both books in the same slot, AR persistence, no lag effect | event-phase FL | CH245 | gate |
  | 2 | **S31:** one bot quoting both books with a sub-slot lag; the capture catches some updates half-done (receipt gaps from the census) | event-phase FL | CH245 | gate |
  | 3 | **S32:** a venue-wide spread factor loading on every pair ("any innovation anywhere predicts the spread") | event-phase FL | CH245 | gate |
  | 4 | **thin selection:** both books AR(0.7) around their own means, thin chosen at k - 1 (regression to the mean), no cross-book effect | event-phase FL | CH245 | gate |
  | 5 | **liquidity leak (CH245):** the thin book's reversion speed and the dense book's innovation variance share a latent liquidity seen noisily | event-phase FL | CH245 | gate |
  | 6 | **M-Q (CH245):** a slow event drift raising both books' spreads before and after the target | none | CH245 | verdict size |
  | 7 | **S26 (CH244):** a common event shock moving every member's mid and spread in the same slot, statuses random, no lag | event-phase FL | CH244 | gate |
  | 8 | **S27:** a dormant ladder whose only mover is the favourite; unrewarded status concentrated on longshots; longshot spreads revert | event-phase FL | CH244 | gate |
  | 9 | **S34:** post-shock widening proportional to 1 / liquidity, status correlated with liquidity at the census's measured within-event correlation; the model sees noisy tiers | event-phase FL | CH244 | gate |
  | 10 | **M-Q (CH244):** a slow event drift raising shocks and unrewarded spreads before and after alike | none | CH244 | verdict size |
  | 11 | **S28 (CH243):** a bounded logit walk with PX1's level drift, traded and quote-only alike, both panels alike | block FL (market) | CH243 | gate |
  | 12 | **missing-volume leak (CH243):** `volume_num` missing with a probability that falls with a latent activity that raises continuation, differentially by panel | block FL (market) | CH243 | gate |
  | 13 | **S33:** a fee-free panel that is older, larger and slower, with continuation a smooth function of liquidity and age seen noisily; same continuation per traded move on both panels | none | CH243 | verdict size |
  | 14 | **capture concentration:** fee-free traded units concentrated in a block of captures during which a venue-wide continuation factor is high; no panel effect | none | CH243 | verdict size |
  | 15 | **M-Q (CH243), panel-differential:** a slow drift entering the target and the traded indicator with loading 0.3 per SD on fee-on and 0.1 on fee-free markets | none | CH243 | verdict size |

  **Verdict size** (6, 10, 13-15) = the share of worlds in which the analytic one-sided p (1.7) is < 0.05 **and** the test's
  binding conditions (1.9: F for CH245 and CH244; the point conditions for all) hold; the gate is omitted. Criterion <= 0.058.
- **Also reported, never binding:** a planted-effect power run per test (500 worlds; CH245 1.0c per census tercile gap of
  `zs_D`, CH244 1.0c between classes on shock captures, CH243 0.5c between panels; seeds `20261597 x 100 + 51, 52, 53`).
- **Consequence of a failure:** a failing scenario makes only the tests it binds "SE check failed (size scenario)" (1-5, 7-9,
  11-12) or "SE check failed (mechanical world)" (6, 10, 13-15): p = 1 in Holm, **k unchanged**, no rerun, reseed, redesign or
  variant; `max_retries 1` for a deterministic crash only; no preliminary run at seed 20261597. **Expected:** worlds 2 and 4
  may fail for CH245, world 9 for CH244, worlds 13 and 14 for CH243; the rest are expected to pass.

### 1.8.1 Simulated worlds (declared now; census inputs only where named)
Common: units on a 2 h grid, `day = i // 12`, `block2 = day // 2`; 200 draws per world at a fresh sub-seed from one generator
seeded 20261597, scenarios in table order; spreads in cents on a 1c grid with a 1c floor; every world fits the test's primary
model with K replaced by the simulated controls named; in event worlds 10% of member units are removed at random after
generation (exercising the omission rule).
- **1 (S30):** 300 two-member events, `n` uniform on 120..252 captures; an event volatility state `v_t` AR(1) rho 0.8
  (stationary SD 1); each book's spread `s_{b,t} = max(1, round(2 + 1.0 x v_t + u_{b,t}))`, `u` AR(0.5) iid across books (SD
  0.8c); both books load on `v_t` in the same slot; the model sees `z log rv24` = `v_t + N(0, 0.7^2)`; no lag effect.
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
- **7 (S26, CH244):** 200 events of 3-10 members (uniform), `n` uniform on 120..252; member mids `m_{j,t} = m_j + e_t + w_{j,t}`
  with a common event shock `e_t ~ N(0, (1.5c)^2)`; spreads `max(1, round(2 + 1.5 x |e_t| + AR(0.7) noise))` in the same slot;
  each member unrewarded with probability 0.5 independently (at least one of each status per event); shock by 3.2's rule; no lag.
- **8 (S27):** world 7 with all moves on the favourite (rank 1), longshots static up to noise, longshot spreads AR(0.8) around 3c;
  the favourite rewarded with probability 0.8, longshots 0.4.
- **9 (S34):** world 7 with member liquidity `L_j ~ N(0, 1)`; post-shock spread change `E[ds] = 0.8c x exp(-0.7 L_j) x shock`;
  unrewarded status drawn so that the within-event correlation of `unrew` and `L_j` equals the census's measured value (census
  input; floor |0.20|); the model sees tiers cut from `L_j + N(0, 0.5^2)` at its quartiles; no status effect.
- **10 (M-Q, CH244):** world 7 plus `mu_t` as world 6 entering unrewarded members' targets and, at 0.3 per SD, the shock
  propensity before (k) and after (k + 3).
- **11 (S28, CH243):** LT11 world 1 (400 markets, logit walk step SD 0.25, PX1 drift, movers `|d| >= 0.01`, traded with
  probability 0.35), with 30% of markets fee-free; controls as 4.3; no panel or traded effect beyond the drift.
- **12 (missing-volume leak, CH243):** LT11 world 3 with `q` = the census unknown share among CH243 movers (floor 0.15) and the
  missingness logit shifted by +0.5 on fee-free markets.
- **13 (S33):** world 11 with fee-free markets' `log liquidity` +1.0 SD and age +1.0 SD on average; continuation `E[c] = 0.25c x
  z(liquidity) - 0.15c x z(age)` on traded and quote-only movers alike, and traded probability `logistic(-0.6 + 0.4
  z(liquidity))`; the model sees `log1p liquidity` and age each with noise SD 0.5 and the census-fixed cells built from the noisy
  liquidity; same continuation per traded move on both panels.
- **14 (capture concentration):** world 11 with fee-free traded movers drawn so that 10% of captures (contiguous blocks of 12)
  hold 50% of them (the map's pattern); a venue-wide factor adds `0.4c` to every traded mover's continuation in those blocks.
- **15 (M-Q, panel-differential):** world 11 plus `mu_t` AR(1) rho 0.99 (stationary SD 0.5c) entering `c` and the traded
  propensity with loading 0.3 per SD on fee-on markets and 0.1 on fee-free markets.

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **F rule (LT7's, unchanged).** The arm model is the primary with the far-future twin added, on units that have it.
  `Δ = beta(lead) - beta(twin)`; **F holds iff Δ's one-sided p < 0.05 (1.7 rule; not Holm-adjusted; counted 0) and Δ̂ >= 0.5 x
  betâ_primary**; an arm with < 50% of the primary's units is *falsification unavailable*. **F binds for CH245 and CH244, fixed
  now by design** (rolling states, 1.7). **F is a reported label for CH243, fixed now by design** (6 item 9; A1). Twins:
  CH245 `zs_D` over (k + 2, k + 3] for the same pair and the same dense member, NaN unless the pair is complete at k + 2 and
  k + 3 (1.4.4); CH244 `shock x unrew` with the shock over (k + 2, k + 3] on ladder-complete pairs at k + 2, k + 3; CH243
  `traded x fee_on` of the market's own move over (k + 2, k + 3] (NaN unless that move is a classed mover).
- **Point conditions (binding, fixed now; estimates only, no test, counted 0).** CH245 **(a) dense twin:** the model on the
  dense members of the same pair-captures (state the thin member's innovation, mirrored controls) has **betâ_dense < 0.5 x
  betâ_thin**; **(b) placebo:** the primary with `zs_D` replaced by the unrelated pair's `zs` (2.3) has **betâ_placebo < 0.5 x
  betâ_thin**. CH244: the twin model with `shock x lowliq` in place of `shock x unrew` (3.3) has **betâ_lowliq < 0.5 x
  betâ_unrew**. CH243: in the pooled cell-fixed-effect model (4.3) **|betâ_quote| < 0.5 x betâ_traded**. Each difference's
  one-sided p is reported as a label.
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate > 0, gate passed, F holds (CH245, CH244),
  every point condition holds. Else, with everything else holding: F fails or unavailable -> **Inconclusive** with *mechanical
  null not excluded* (or *falsification unavailable*); a point condition fails -> **Inconclusive** with *not thin-specific*,
  *placebo not null* (CH245), *not status-specific* (CH244) or *not traded-specific* (CH243). CH243 with F failing stays
  Supported if all else holds and carries *mechanical null not excluded (label)*.
- **Contradicted:** the conservative 95% CI lies entirely below 0. **Inconclusive:** otherwise. **Unavailable:** CH245 < 20,000
  thin units, < 300 events, < 100 events with >= 48 units; CH244 < 20,000 tested units (unrewarded x shock) or < 20,000
  rewarded shock units, < 300 events, < 100 events with >= 48 units; CH243 < 8,000 fee-free traded units, < 20,000 fee-on
  traded units, < 300 events on the fee-free panel; all three: Kish `G_eff` < 15 or < 10 UTC days with units.
- **Labels (never change a verdict):** *material* (CH245 >= 1.0c at the census tercile gap of `zs_D`; CH244 >= 1.0c; CH243 >=
  0.5c); *thin-difference significant*, *status-difference significant*, *panel-difference significant*; *informed (X)*;
  *analytic p oversized in simulation*; *underpowered* (as LT11); *attrition-differential*; *late-loss*; *series-concentrated*;
  *holiday-sensitive*; *mirror-gap mediated* (CH245: the refit with the mirror levels at k drops the estimate below half);
  *receipt-order sensitive* (CH245: the refit on pairs with the thin row received before the dense row at k changes sign);
  *ladder-dominated* (CH244: the 11+ arm has the opposite sign); *CLOB-disagreement sensitive* (CH244: the refit on members whose
  carry status and feed listing agree changes sign); *capture-concentrated* (CH243: the refit without the top 10% of captures by
  fee-free traded count changes sign); *volume-missing sensitive* (CH243: the unknown-class arm's estimate exceeds the traded
  one or has the opposite sign).
- **MDE multiplier** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (LT7-LT11), not lowered for k <= 3.

### 1.10 Economics (separate; descriptive; never changes a verdict)
- **Maker routes (gross, an upper bound, no fills, no queue, no reward income):** CH245 the thin book's maker widens by the dense
  book's widening for one slot after it (the pick-off avoided = the thin book's next spread change, cents a share); CH244 the
  unpaid member's maker pulls for one slot after a sibling shock (the fill avoided = the member's bid change at k + 1); CH243
  the maker re-centres by the full move after a fee-on traded move and by half after a fee-free one (the adverse selection
  avoided = the continuation difference).
- **Paper taker (reported):** LT3's `paper_taker` and `econ` at the recorded touches of the entry capture and the exit capture
  k + 1, fees on both legs from the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), event-
  clustered mean, one-sided p, >= 30 trades in >= 10 events; no depth, queue or latency. CH245 take the thin book's stale side
  for one slot after the dense book widened (the hurdle its own half-spread); CH244 the buyer of an unpaid member waits one slot
  after a shock; CH243 follow fee-on traded moves of >= 3c (the follow trade pays the fee, 1.0-1.25c at mid prices, on top of
  the spread; stated, not hidden). **CH245's cheaper-book line** (`min(ask_A, 1 - bid_B)` against `ask_A`, read at capture k
  only) is a cost-route descriptive, not a forecast and not a test.
- **Hurdles (`cost-model-v1`):** taker round trip about 2.9c at >= $100k liquidity, 3.9c at $10k-100k, 7.2c at $1k-10k; 5-share
  touch about 4.5c (politics 3.6c); passive fill 3.1% within an hour; makers about break-even before rewards (-0.37c).
  **No E026 frozen module (`costs.py` included) is imported, copied or edited.**
- **Declared in advance:** every AREPO taker check has failed (0 of 95 cells positive); "not shown" is the expected outcome.
  A Supported LT12 primary can at most nominate a later, separately registered economic test.

### 1.11 Overlaps, dependence and counting
- **Within LT12:** CH245 and CH244 read the same event join but disjoint events (two members against 3-10); a CH243 mover can be
  a CH244 member in the same capture. One Holm family; the census prints unit overlaps and, on shared units, the correlations
  of the tested terms.
- **Against other tests:**

  | LT12 | Closest prior | Same contrast? | Why not a double count |
  |---|---|---|---|
  | CH245 | LT11 CH233's two-member arm (the twin's *bid* change; reported, uncounted) | no: CH245's state is the twin's *spread* innovation, its target the thin book's spread | different state and window; blind freeze before `T_LT11c` or *informed (LT11 census)* |
  | CH245 | E005, HB1 XM1-XM3, round 13's L1-L4 (mids of ladders) | no: mids; CH245 reads spreads | closed records disclosed; M3 *informed (L1-L4)* |
  | CH244 | LT11 CH233 (siblings' signed bid-sum rise on all members of 3-10 member events) | no: an unsigned shock interacted with the member's own reward status | disjoint windows; `cl_sib` never computed by LT12 |
  | CH244 | E022's S2; LT9 CH213 | no | *informed (E022)* certain; LT9 overlaps in time only |
  | CH243 | E015 (anatomy); LT11 CH234 (collateral dose within traded movers) | no: the fee panel's moderation of the traded-minus-quote-only difference | *informed (E015)* certain; LT11's `xw` never computed |
  | CH243 | round 3 (zero-fee islands, parked), round 10 (within-market fee gradient, rejected) | no: a between-panel filter on the crosser | disclosed (10) |
- **Counting:** the analysis adds **k counted tests**, kind `live_tests12` (`battery2.KIND_RULES["live_tests12"]`, fail-closed).
  Gates, F, point conditions, placebos, secondaries, arms, economics, the census, the CH251 map and the size check count 0.

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
venue's cheapest price for the claim, it is picked off, and its makers widen a slot later. So the thin book's next spread
change should rise with the dense book's latest spread innovation, beyond the thin book's own innovation and the mirror's
level, and the reverse (the dense book following the thin one) should be much weaker.

### 2.2 Population and unit
- **Pair:** an event with exactly two eligible members at k - 1 and k, pair-complete (1.4.4), non-augmented; both members pass
  1.4 at k - 1 and k (tight on both; else `pair_wide`, counted); category non-sports ex-crypto on both.
- **Asymmetry at k - 1:** `|spread_{A,k-1} - spread_{B,k-1}| >= tick_e,k-1`. The **thin** member T is the wider at k - 1, the
  **dense** member D the narrower; a pair-capture with equal spreads on the grid is `sym` (a reported class, no unit).
- **Unit:** the thin member of an asymmetric pair-capture: **one unit per pair per capture** (1.7). Origin and decision clock:
  capture k's last row receipt. Target: `ds_T = spread_{T,k+1} - spread_{T,k}` (cents), over (k, k + 1]; `unavailable` unless
  T is `two_sided` at k + 1 (the pair need not be complete at k + 1).
- **Arms (reported, uncounted):** `sym` pair-captures (both members, each book's slope on the other's innovation); the reward
  cells rr / ru / uu separately; augmented two-member events; the sports arm.

### 2.3 State, controls and the primary statistic
- **State:** `zs_D = (spread_{D,k} - spread_{D,k-1}) / s_D`, `s_D` the census pooled SD of the dense member's spread innovation
  over CH245 census units (one scalar, fixed in the spec); positive = the dense book widened.
- **Controls (a non-redundant basis; 6 item 2):** the thin book's own innovation `spread_{T,k} - spread_{T,k-1}`; the dense
  book's level before its innovation `spread_{D,k-1}`; the bid headroom `hb_{k-1} = 1 - bid_{T,k-1} - bid_{D,k-1}`; with K's
  own spread at k these span the mirror gaps `g_ask,k-1 = ask_T + bid_D - 1 = spread_T - hb` and `g_bid,k-1 = bid_T + ask_D - 1
  = spread_D - hb` and the spread gap at k - 1, which are therefore not entered separately; `log1p liquidity` of the dense book;
  the dense book's `rewarded_k` (the thin book's is in K); K (the twin's mid change is near `-d_T` and is not entered).
- **Primary:** expanding-past event x UTC day demeaned OLS of `ds_T` on `zs_D` with the controls; **one-sided H1: beta > 0**;
  inference 1.7; event-phase block FL gate (1.8); **F binding** (twin `zs_D` over (k + 2, k + 3]); **dense-twin and placebo
  point conditions binding** (1.9).
- **Dense twin model:** units = the dense members of the same asymmetric pair-captures; target `ds_D`; state `zs_T =
  (spread_{T,k} - spread_{T,k-1}) / s_T` (`s_T` census-fixed); controls mirrored.
- **Placebo pair (rule 18):** for the unit of event e at capture k, the unrelated pair e' is the next CH245 asymmetric pair at
  capture k after e in the order of `sha256(event key)` (wrapping), e' != e; its `zs_D'` replaces `zs_D`; NaN if capture k has
  no other pair. The rule reads only capture k's keys.
- **Secondaries (reported, uncounted):** M1 the thin book's stale-side touch change at k + 1 (the ask where `g_ask,k < 0`, the
  bid where `g_bid,k < 0`), signed as the mechanism predicts; M2 the mirror gaps' change over (k, k + 1]; M3 the thin mid's change
  (*informed (L1-L4)*); M4 the round's form with the mirror levels at k as controls (the *mirror-gap mediated* label); M5 the
  receipt-order split; the arms of 2.2.

### 2.4 Planning counts and MDE (planning only)
- **Counts (CH251 map, per capture, non-sports ex-crypto, before LT12's tight, tick and augmented rules):** two-member events 651;
  complete pairs 639 (rr 238.2, ru 19.1, uu 382.0); thin share of member units 0.26 / 0.41 / 0.47, so asymmetric pair-captures
  (= thin units) about 124 + 16 + 359 = **499 a capture**; receipt-span retention 1.000; distinct events 1,023 over 9.25 days.
  Planning after the tight rule, the post-midterm panel and the new filters (each unprobed): **200 (low) to 500 (high) thin
  units a capture**; `n_eff` 40,320-100,800 at 0.8.
- **Design effect:** one thin unit per event per capture, so `m_21 <= 252` and the formula gives DE about 6 (floor 5.0); 11 is
  the round's value for two units an event-capture (quoted as the pessimistic plan); 31 is the ladder convention, quoted only.
- **MDE** (`3.47 x 2c x 1.5 x sqrt(1.3) x 2.2 = 26.112`; `MDE = 26.112 x sqrt(DE / n_eff)`): DE 6 **0.32c / 0.20c**, quarter
  0.64c, F (x 1.5811, `r_w` 0.2) 0.50c / 0.32c; DE 11 0.43c / 0.27c, quarter 0.86c, F 0.68c / 0.43c; DE 31 0.72c / 0.46c, F
  1.14c / 0.72c. The point conditions are estimates (no MDE gate); the dense-minus-thin difference's MDE is reported.
- **Kill line (F-MDE <= 1.0c):** `n_eff >= 1,704.6 x DE`: 51 thin units a capture at DE 6, **93 at DE 11**, 262 at DE 31. **Count
  gate 186 a capture** (twice the line at DE 11, LT9 CH214's and LT11 CH233's practice); the MDE gates decide with the census's
  own DE, `VIF_w` and `r_gate`.

### 2.5 Confounders and how each is held
- *Common event shock* (S30): the own innovation is a control; world 1 binding.
- *One bot on both books* (S31): if both books are quoted from one model within minutes, the lead is a receipt artefact; the
  120 s span rule bounds it, world 2 plants it with the census's receipt gaps, M5 reports it; the same-slot correlation gate (7)
  measures how much of the panel moves in one slot.
- *Venue-wide spread moves* (S32): the placebo point condition and world 3.
- *Selection on thin at k - 1* (regression to the mean): the dense member is narrow at k - 1, so its innovation tends to be
  positive while the thin member reverts down; this biases against H1, but world 4 is binding and both levels are controls.
- *Thin books are illiquid books:* dense liquidity and K's own liquidity as controls; the corr gates (7); world 5.
- *Reward status* (the paid book is usually the dense one): both books' status as controls; rr / ru / uu reported.
- *The record:* LT11's two-member arm (a different state; disclosed); the `event` family's visible levels (no twin-spread
  innovation exists in the engine; 9).
- **Most likely boring outcome:** the two books are one bot's quotes that move in the same slot, so nothing is left to follow
  (the census's same-slot correlation and `VIF_w` say so before any target); or the dense book's spread rarely moves on a 1c
  grid (the within-event SD gate).

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
- **Ladder:** non-augmented, ladder-complete (1.4.4) events with **3-10** eligible members at k - 1 and k; **mixed** at k - 1:
  >= 1 member `listed_carry24h_v2`-rewarded and >= 1 unrewarded at k - 1 (carry window ending at k - 1); a member with NaN status
  excludes the event-capture (`status_nan`). 11+ member ladders a reported arm (their completeness is 0.31 on the map, so the arm
  uses the same completeness rule and is expected thin); 2-member events are CH245's.
- **Member status per market-day:** `unrew_i` is fixed at the member's first unit of the UTC day; a later unit of that day with a
  different carry status is excluded (`status_switched`, counted).
- **Unit:** member x capture of a mixed ladder-complete pair, the member passing 1.4 at k - 1 and k (a member failing it gives no
  unit; the event-capture stays complete for the others). Target `ds_i = spread_{i,k+1} - spread_{i,k}` (cents); `unavailable`
  unless the member is `two_sided` at k + 1.
- **Shock:** `shock_{i,k} = 1[max_{j != i} |d_{j,k}| >= 2 x tick_e,k]` over the event's other eligible members (`d` the 2 h mid
  change over (k - 1, k]); `shock_size_{i,k} = max_{j != i} |d_{j,k}| / tick_e,k`, winsorised at 20 ticks.
- **Tested term:** `shock_{i,k} x unrew_i`. **Tested units** (for counts) = unrewarded members on shock captures.
- **Low-liquidity twin (point condition):** `lowliq_{i,k} = 1[liquidity_{i,k-1} < median_j liquidity_{j,k-1}]` over the event's
  eligible members at k - 1 (ties 0).

### 3.3 Controls and the primary statistic
- **Controls:** `unrew_i` (main), `shock`, `shock_size`; `tier_{i,k-1}` dummies and **tier x shock** (1.4.2); the own `d_i`, `|d_i|`
  and own spread change over (k - 1, k]; `hb_{k-1}` (the event's bid headroom, a level; LT11's `cl_sib` is never computed); the
  member's bid share and a favourite dummy (rank 1 by mid at k - 1); `n_members`; `neg_risk_other`; K.
- **Primary:** expanding-past event x UTC day demeaned OLS of `ds_i` on `shock x unrew` with the controls; **one-sided H1: beta
  > 0**; inference 1.7; event-phase block FL gate; **F binding** (twin: the shock over (k + 2, k + 3]); **low-liquidity point
  condition binding:** the twin model replacing `unrew_i` and `shock x unrew` by `lowliq` and `shock x lowliq` gives betâ_lowliq <
  0.5 x betâ_unrew.
- **Secondaries (reported):** M1 the member's bid change at k + 1 (predicted < 0); M2 the mid toward the siblings' implied value
  (*informed (L1-L4, E005)*); M3 the traded-shock arm (shock from a sibling's `volume_num` rise; `unknown` counted); M4 (placebo)
  the shock's main effect on all-rewarded and all-unrewarded ladders; the CLOB-agreement refit; the event-capture aggregate
  (1.7); the 11+ arm; the sports arm.

### 3.4 Planning counts and MDE (planning only)
- **Counts (CH251 map, simple reward reading):** mixed ladders 1,363 a capture (3-5: 238, 6-10: 752, 11+: 373); complete 199 /
  661 / 116 (shares 0.83 / 0.88 / 0.31); unrewarded two-sided 0.82 (rewarded 0.97); shock share 0.51 (unrewarded) / 0.53
  (rewarded); status-liquidity correlation pooled -0.05, within event -0.09 (3-10 members); distinct mixed events 2,304 over 9.25
  days. **Unprobed:** members by size class, the carry reading's effect on the mixed share, receipt spans, switchers.
- **Planning:** 860 complete 3-10 mixed ladders x 6 members = 5,160 member units; unrewarded share 0.4-0.6; then the carry
  correction 0.3-1.0, receipt span 0.6-1.0, tight 0.7-1.0, switchers 0.8-1.0; shock share 0.5. **Low:** 208 unrewarded member
  units, **104 tested units** and 156 rewarded shock units a capture; **high:** 3,096 unrewarded, **1,548 tested** and 1,032
  rewarded shock units.
- **Design effect:** a 6-member ladder present all window holds about 1,512 units: DE about 31 (cap 51); census `max(5.0, computed)`.
- **MDE** (class contrast, `3.47 x 2c x 1.5 x sqrt(1.3) x sqrt(2) x sqrt(31) = 93.46`; `MDE = 93.46 x sqrt(1/n1 + 1/n2)`, `n` =
  units a capture x 201.6): low **0.83c**, high **0.26c**, quarter of low 1.67c; F (x 1.5811) **1.32c (fails) / 0.42c**.
- **Kill line (F-MDE <= 1.0c, rewarded shock units 1.5 x tested):** **181 tested units a capture.** **Count gate 362** (twice the
  line) and rewarded shock units >= 181; the MDE gates decide with census values.

### 3.5 Confounders and how each is held
- *Unpaid rungs are illiquid rungs* (S34): tier x shock, the low-liquidity point condition, the corr gates, world 9 (with the
  census's measured correlation).
- *Reward-field omission* (62% of rows omit `clob_rewards`): `listed_carry24h_v2`'s carry; NaN excluded; the CLOB-agreement
  refit; switchers excluded.
- *The favourite as the only mover* (S27): the favourite dummy, `shock_size`, world 8.
- *Common event shocks* (S26): the shock is at (k - 1, k], the target at (k, k + 1]; own changes controlled; world 7.
- *Completeness by status* (unrewarded members one-sided more often): rule 16 drops the pair, counted; completeness by status
  printed.
- *The record:* LT11 CH233 (a different state, disjoint window); E022's S2 (*informed (E022)*); the `event` family's levels.
- **Most likely boring outcome:** under the carry reading mixed ladders are rare (the count kills it), or the widening is the
  liquidity gradient (the point condition fails cleanly).

### 3.6 Data streams, jobs, timing
Rows and sidecars of captures k - 12 .. k + 3 (the carry window), every member of each neg-risk event of 3-10 members; per event
the previous capture's member rows and per market the carry texts. Census CC12; token `mixedlad` (9).

## 4. CH243: the fee as the price of urgency (conditional)

### 4.1 Hypothesis in plain words
A taker pays `rate x p(1 - p)` a share to cross; a maker never pays; on fee-free markets nobody pays. A fee does not stop a
trader whose expected gain is several cents but does stop some whose expected gain is about zero, so a crossed move on a fee
market should more often carry information than the same crossed move on a fee-free market. The hypothesis: within markets,
traded 2 h movers continue more than quote-only movers, and this difference is larger on the fee-on panel than on the
fee-free panel, within markets of the same liquidity tier, category and age class.

### 4.2 Population, unit and the `volume_num` classes
- **Unit:** a non-sports ex-crypto market x capture k with `|d_k| >= 0.01`, `p_{k-1}` in **[0.04, 0.96]**, passing 1.4 at k - 1
  and k, `n_members <= 10` (ladder arm reported), fee class `fee_on` or `fee_free` (1.4.3, not `fee_switched`), in a census-fixed
  covered cell (below; else `cell_uncovered`, counted).
- **Classes (LT11 2.3 vendored unchanged; keyed by slot, never carried):** **traded** (`v_k - v_{k-1} > 1e-6`, both finite),
  **quote-only** (`|v_k - v_{k-1}| <= 1e-6`), **unknown** (`vnum_missing_k`, `vnum_missing_km1`, `vnum_decrease`,
  `sidecar_missing`): a **counted third class, never classed, never inferred** from `volume24hr`, `last_trade_price` or anything
  else; excluded from the primary and fitted alone as a reported arm.
- **Cells:** `cell = tier_{k-1} x fee_category x age class` (1.4.2, 1.4.3). **Covered cells (census-fixed):** cells holding >=
  20 fee-free and >= 20 fee-on traded units over the census span; the list is pinned in the spec.
- Target `c = sign(d_k) x (mid_{k+1} - mid_k)` (cents) over (k, k + 1]; `unavailable` unless `two_sided` at k + 1.

### 4.3 State, controls and the primary statistic
- **Tested term:** `traded_k x fee_on_m` (fee_on fixed per market, 1.4.3).
- **Controls:** `traded_k` (main); `traded_k x cell` dummies (the cell-matched control: the traded coefficient is free in every
  cell, so the tested term compares panels within cells); `|d_k|` (winsorised at 0.20); LT11 2.4's piecewise-linear `sign(d_k) x
  bin` level drift (four bins of `p_{k-1}`, cuts 0.15 / 0.50 / 0.85); `log1p` of the `volume_num` change (0 on quote-only); the
  maker rebate a share `rebateRate x rate x p(1 - p)` from the origin sidecar (0 on fee-free); tier dummies; K (with market age).
- **Primary:** expanding-past market-demeaned OLS of `c` on `traded x fee_on` with the controls, on traded and quote-only units;
  **one-sided H1: beta > 0**; inference 1.7 (event clusters; rule 20's cluster-robust panel contrast); block FL gate in market
  strata (the within-market term); **F a reported label** (twin: `traded x fee_on` of the move over (k + 2, k + 3]).
- **Point condition (binding):** the pooled model without market demeaning, with cell fixed effects and the same controls, fitted
  separately on traded units and on quote-only units, each with a `fee_on` coefficient: **|betâ_quote| < 0.5 x betâ_traded**.
  Under market demeaning the quote-only panel contrast is not identified, so the pooled model is the only place it can be read;
  the absolute value is used because a quote-only panel difference of either sign would mean the primary's difference is not
  traded-specific (6 item 14).
- **Secondaries (reported):** M1 `c_skip`; M2 the contrast within the `pre_0330` age class only, geopolitics removed; M3 the
  contrast by `p_{k-1}` bin (the fee at 0.5 is five times the fee at 0.05: the mechanism predicts a larger contrast where the fee
  is larger); the category-rate fee reading; the unknown-class arm; the capture-concentration refit; the ladder arm; sports arm.

### 4.4 Planning counts and MDE (planning only)
- **Counts (CH251 map, per capture):** fee-free traded movers mean 346 (rewarded 304, median 64; unrewarded 42, median 7);
  fee-free quote-only 644; fee-free `volume_num` unusable 213; fee-on traded 837; mean 3-6 times the median in every fee-free
  cell, per-capture minimum 33 / 1; `rate_zero` traded movers median 1; category x age coverage proxy 0.956. **Not
  stationary:** a block of captures holds most of the fee-free population.
- **Planning:** fee-free traded units after LT12's rules (LT11's retention 0.73-0.93): **52 (low: the median 71 x 0.73) to 322
  (high: the mean 346 x 0.93) a capture**; fee-on traded in covered cells 750 (837 x 0.9).
- **MDE** (two within-market coefficients, `3.47 x 4c x sqrt(6.196) x 1.5 x sqrt(1.3) x sqrt(2) = 83.565`; `MDE = 83.565 x
  sqrt(1/n1 + 1/n2)`, `n2` = 151,200): low **0.84c**, high **0.39c**, quarter 1.65c; F (x 1.4907, `r_w` 0.1) 1.26c / 0.58c.
- **Kill line (plain MDE <= 0.5c):** **170 fee-free traded units a capture.** With F binding the line would be 522 (above every map
  reading), which is why F is a label here (6 item 9). **Count gate: the median over covered captures >= 170**, and the declared
  MDE uses `n1 = min(projected effective count, median x 252 x effective share)` (7).

### 4.5 Confounders and how each is held
- *Composition:* the fee-free panel is geopolitics plus older (`pre_0330`) markets, larger and slower; the cell x traded control,
  market age, the pooled |corr(fee_free, log1p liquidity)| gate, world 13 (verdict size) binding.
- *Capture-level concentration* (the map's pattern; possibly a field-path artefact): the median-based count gate, the
  concentration gate, the fee-switch gate (7), world 14 binding, the capture-concentrated label.
- *Differential missingness of `volume_num`:* the unknown-share and correlation gates (7); world 12 binding.
- *The maker rebate* (fee-on only): a control.
- *A slow drift loading differently by panel:* world 15 binding (it carries what F carries elsewhere).
- *The record:* E015's traded class (*informed (E015)*, certain); se1's category one-hot may have learned the fee's shape (a
  development look, disclosed); round 3 and round 10's fee readings (different mechanisms).
- **Most likely boring outcome:** the fee-free panel is a few captures' worth of flagged markets and geopolitics (the count,
  concentration or switch gate kills it), or a 1c fee filters nobody (a clean null).

### 4.6 Data streams, jobs, timing
Rows and sidecars of captures k - 12 .. k + 3; per market the last 12 mids, the `volume_num` of slot k - 1 keyed by slot, its fixed
fee class and first-unit cell. Census CC12; token `feeclass` only if CH243 survives its census (9).

## 5. Deferred and not taken (none counted)
- **CH246 (no-link twin):** no matcher and no rules text in the captures (the map could not count it); not an arm of CH245 here.
- **CH248 (who printed):** engine-first (`movetype` spec after 2026-11-22); the map's `twin_printed` share 7% clears its 5% line.
- **CH250 (who pays the maker):** engine-first; the map's fee-free cells are 29% of rows, above its 3% kill line.
- **CH242 (third price):** killed at its own census on 2026-10-23 (non-sports split share 0.004%).
- **CH247, CH249:** the owner's sports and crypto parameters. **Sports arms:** reported, uncounted, in every test.

## 6. Design changes from the round-17 sketches (made before any LT12 data; each needs the challenger's acceptance)
Items marked **[map]** were made after reading the CH251 map.
1. **CH245: the thin member only, one unit per asymmetric pair-capture [map].** The round pooled both members. The two members'
   targets in one slot are near-duplicates (the map's same-slot correlation 0.38-0.64 is on their innovations), the mechanism
   predicts a slope only for the thin book, and pooling averages in the predicted null of the dense book. The dense book becomes
   the point condition on the same pair-captures; `sym` pair-captures (0.47 of rr member units) are a reported class.
2. **CH245: a non-redundant control basis; mirror levels at k - 1.** The round's controls `g_A`, `g_B`, the spread gap and `hb`
   are linearly dependent (`g_A = spread_A - hb`, `g_B = spread_B - hb`, so `g_A - g_B` is the spread gap). LT12 enters own
   spread at k (K), own innovation, `spread_{D,k-1}` and `hb_{k-1}`. The levels are taken at k - 1, not k, because the mirror
   gap at k contains the state and is the mechanism's own channel (the thin quote inside the widened mirror), so controlling it
   would condition on a mediator; the round's k form is M4 and the *mirror-gap mediated* label.
3. **CH245: the placebo is a binding point condition** (rule 18 says "must be null"), with a deterministic sha256 pair rule.
4. **CH245: planning DE 6 / 11 / 31 and the count gate 186 [map]** (twice the F line at DE 11).
5. **CH245, CH244: demeaning in event x UTC day; the gate on the event.** A pair has at most 12 thin units an event-day, under the
   gate's 16-row minimum, so the gate shifts whole events (LT11 CH233's event-phase form) while demeaning keeps rule 18's stratum.
6. **CH244: tier from the row's `liquidity` at k - 1 in the cost model's bins [map: no tier in captures]; the low-liquidity
   twin defined within event; status by `listed_carry24h_v2` at k - 1, fixed per market-day.** The round's "the CLOB feed
   adjudicating" is replaced by the house rule (carry status in the primary; the CLOB-agreement refit a sensitivity), because
   the feed is not guaranteed for every capture and a feed-adjudicated status would make the population depend on a second
   stream's coverage (A7).
7. **CH244: own spread change and a favourite dummy added; `cl_sib` never used** (LT11's object); `hb_{k-1}` kept as a level.
8. **CH244: the count gate on tested units (362) [map]**, not on unrewarded members, so the measured shock share enters once.
9. **CH243: F is a reported label, accepted in writing (round 17's door).** Reasons: (a) the tested quantity is a contrast of two
   panels' within-market coefficients, so a mechanical bias common to both panels cancels in it; (b) the bias that would not
   cancel (a drift loading differently by panel) is planted in binding verdict-size world 15, and the composition and
   concentration paths in worlds 13-14, so the simulated size check carries the burden that F carries elsewhere; (c) with F
   binding the kill line is 522 fee-free traded units a capture, above every map reading, so the binding form is a test that
   cannot be run. This conflicts in spirit with LT11 R1's ruling A4 ("a label-only F chosen for power is rejected"); reason (c)
   is a power reason and is said so. **If the challenger rules that F must bind, CH243 leaves LT12 before the freeze (k <= 2)
   and returns to the engine; no census is run for it** (A1).
10. **CH243: the count gate on the median per-capture count, with a capture-concentration gate [map]**, because the map's mean is
    3-6 times its median and the window's total cannot be projected from a mean of a non-stationary series.
11. **CH243: the fee panel from sidecar fields only, fixed per market, with a switch gate [map: `fee_src` gaps]**; no category
    fallback in the primary (inference from the category would be imputation).
12. **CH243: the cell-matched control as `traded x cell` on census-fixed covered cells [map]** (tier from `liquidity`, age from the
    sidecar's `created_at`, which the map showed is present), in place of drawing matched fee-on units.
13. **CH243: the gate in market strata**, not market x UTC day (movers a market-day are far under 16 rows; LT11 CH234's form).
14. **CH243: the quote-only point condition on a pooled cell-fixed-effect model, in absolute value** (4.3).
15. **All: K as LT11 1.7, plus market age for CH243.**

## 7. Pre-registration census (counts only; before registration; worn pre-window data; no target read)
The census runs once, reads origin-side fields only (the only later-slot quantities are the three twins' states, for `r_gate`,
through the lag-slot loader, which returns only the twin term; no mid, spread, bid, ask or volume of a later slot reaches census
code; unit test), prints counts, and is committed with its sha256 before the registration commit. **Every threshold below is
stated now.** A failed gate drops that test (`census_dropped`, uncounted); `k_tests` lists the survivors. **Input identity:** the
census refuses unless every input file is named in the LT12 seal with an equal sha256; slots and origins come from the seal.

**Inputs (fresh seal; rule 9).** Span **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**, 10 UTC days, 120 slots; the 12 slots
`[2026-11-06T00:00Z, 11-07T00:00Z)` as look-back only (inside LT11's census seal span; raw rows only, no LT11 object computed,
disclosed, A15) and the 3 slots after the span (to 2026-11-17T04:31Z, before LT11's window) for twins only. Complete captures
(rows, sidecar, manifest), 135 captures x 3 files, planning 1.0-1.4 GB. No sweep and no feed is read.
- **Restore, seal, census: each once** (LT11 7's rules: host copies checked against the archive catalogue, the rest restored byte
  for byte; bytes measured first and the owner asked if the restore would exceed free disk; a file in neither place is missing,
  counted, never substituted; the seal records files, sha256s, the seal's slot assignment and the frozen LT12 design-text sha256).
- **Minimum covered days, checked first** (covered origins / 12, from the seal manifest, identical for all three tests): >= 7.0
  (>= 5.0 for twin pairs). If it fails for a test, no gate or descriptive line of it is computed or printed; the test is
  `census_unavailable (coverage)` (1.1).
- **Header pre-check** (headers only, before the census code is frozen; result committed before the seal): the 1.2 fields
  including `fees_enabled`, `fee_schedule`, `created_at`, `liquidity`; whether `chg_1d` / `chg_1w` exist. A missing field makes
  every gate that needs it NaN.

**Definitions.** Projection = count x 21 / covered days. Distinct-event gates and ">= 48 units" counts are **unprojected**.
`DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`, floors **5.0 (CH245, CH244), 6.196 (CH243)**. MDE gates `max(declared, design)`
(LT8's definitions; multiplier 3.47; SDs `ds` 2c, `c` 4c; declared MDE at the census's effective counts with the measured
effective share). F-MDE `= max(design MDE of Δ, MDE x sqrt(2 / (1 - max(0, r_gate))))`. Count gates on gross projected counts.

| Test | Gate (all must hold; NaN fails) | Map number it sits near (planning only) | Values fixed into the spec |
|---|---|---|---|
| **CH245** | pair completeness: pair-complete two-member event-captures / eligible two-member event-captures (incl. `members_changed`) >= 60%; receipt span: span-retained pairs >= 60% of pair-complete pairs (span and receipt-gap quantiles q50 / q90 / q99 printed); **projected thin units (all 2.2 filters) >= 46,872 (>= 186 a capture)**; **distinct events with a thin unit >= 500 and events with >= 48 thin units >= 100** (unprojected); **Kish `G_eff` >= 15**; **same-slot correlation:** among events with >= 24 complete pair-captures, the share with within-event `|corr(Δspread_A, Δspread_B)|` >= 0.8 is <= 50%; **identification:** within-event SD of the dense innovation >= 1 tick in >= 50% of events with >= 48 thin units; `VIF_w(zs_D)` <= 2.0; within and pooled `|corr(zs_D, x)|` <= 0.5 for x in {`log1p liquidity` of each book, `z log rv24*`, `d_T`}; venue clock: the most common slot holds <= 50% of units with `|zs_D| >= 1`; block-gate share >= 50% of thin units in events with >= 16 shiftable captures; placebo coverage (a defined unrelated pair) >= 90% of thin units; `r_gate` <= 0.3; **slope MDE <= 1.0c; F-MDE <= 1.0c** | thin units 499 a capture before the tight rule; retention 1.000; completeness 0.97-1.00; same-slot correlation pooled 0.38 / 0.11 / 0.64 (per-event shares unprobed); within-event SD unprobed | `s_D`, `s_T`; `zs_D` tercile cuts and gap; world 2's receipt-gap q50 / q90; `exclude_family` |
| **CH244** | finite carry status on >= 95% of eligible member rows of 3-10 member events at k - 1; ladder completeness: pair-complete member rows / eligible member rows (incl. `members_changed`) of 3-10 member events >= 60%; receipt span >= 60% of pair-complete pairs; **projected tested units (unrewarded x shock, all 3.2 filters) >= 91,224 (>= 362 a capture)**; projected rewarded shock units >= 45,612 (>= 181 a capture); **shock share** of mixed event-captures in [0.10, 0.80]; within-event and pooled `|corr(unrew, log1p liquidity)|` <= 0.5; **within-stratum variation:** >= 50% of tested units in event x UTC day strata holding both shock and no-shock captures; `VIF_w(shock x unrew)` <= 2.0; **distinct mixed events >= 500 and events with >= 48 units >= 100** (unprojected); **Kish `G_eff` >= 15**; venue clock <= 50% of tested units in one slot; block-gate share >= 50%; `r_gate` <= 0.3; **class MDE <= 1.0c; F-MDE <= 1.0c** | mixed 3-10 ladders 990 (860 complete) on the simple reading; shock share 0.51-0.53; corr -0.05 / -0.09; carry effect, spans and switchers unprobed | world 9's correlation; `shock_size` scale; `exclude_family` |
| **CH243** | fee class finite (`fee_on` or `fee_free`) on >= 90% of eligible movers; **fee switch:** markets with a CH243 unit whose fee reading changes within the span <= 5%; **median over covered captures of per-capture fee-free traded units (all 4.2 filters, covered cells) >= 170**, and projected >= 42,840; **concentration:** the top 10% of covered captures hold <= 30% of fee-free traded units; projected fee-on traded units in covered cells >= 126,000 (>= 500 a capture); projected fee-free quote-only units >= 21,420 (>= 85 a capture); **cell coverage:** fee-free traded units in covered cells >= 60% of fee-free traded units; unknown share among eligible movers <= 0.40 (pooled), captures whose movers are > 80% unknown <= 25% of covered captures, pooled `|corr(1[unknown], fee_free)|` <= 0.3; pooled `|corr(fee_free, log1p liquidity)|` <= 0.5; `VIF_w(traded x fee_on)` <= 2.0; block-gate share >= 50% on each panel; **distinct events with a fee-free traded unit >= 500** (unprojected); **Kish `G_eff` (fee-free traded by event) >= 15**; **class MDE <= 0.5c** (with the median-capped `n1`, 4.4); F-MDE printed (label) | fee-free traded mean 346, medians 64 / 7; concentration, switch share, liquidity corr unprobed; coverage proxy 0.956 | the covered-cell list; world 12's `q`; `exclude_family` |

- **Census-fixed values (the exhaustive list; each written into the spec as the exact census float; nothing else is left open).**
  (1) `k_tests`: the tests whose every gate above holds. (2) `s_D`, `s_T`: the population SD (ddof 0, cents) of the dense and the
  thin member's spread innovation over CH245 census thin units. (3) `zs_D` tercile cuts: its 1/3 and 2/3 quantiles over the same
  units; the gap = mean of the top tercile minus mean of the bottom tercile (the *material* label's and the MDE's gap). (4) World
  2's receipt gaps: q50 and q90 of `|received_utc_A - received_utc_B|` at k over CH245 census pair-complete pairs (floor q50 5 s).
  (5) World 9's correlation: the within-event `corr(unrew, log1p liquidity)` over CH244 census units (floor |0.20|). (6)
  `shock_size` scale: its population SD over CH244 census units (the regressor enters as `shock_size / scale`). (7) CH243's
  covered-cell list: every `tier x fee_category x age class` cell with >= 20 fee-free and >= 20 fee-on traded units over the
  census span. (8) World 12's `q`: the unknown share among CH243 eligible movers (floor 0.15). (9) `<test>.exclude_family`: 1.4's
  series-family rule on each census primary population. The census's `DE_gate`, `VIF_w`, `r_gate` and MDEs are gate values,
  recorded, never re-used to change a threshold.
- **Descriptive (no gate):** sports and crypto splits; series-family shares; overlaps among the three populations. CH245: rr / ru /
  uu and `sym` shares; `pair_wide`, `augmented`, `members_changed`, `receipt_span` counts; the mirror gaps' distribution and
  the share within one tick of zero; the dense-twin and placebo units. CH244: completeness by status and size; `status_nan`,
  `status_switched`; carry against the simple reading (counts only); the share of mixed events with both statuses two-sided on
  >= 24 units; the 11+ arm's counts. CH243: counts by `fee_src`, age class and cell; the per-capture time profile of fee-free
  traded units; unknown sub-classes by panel.
- **Order:** one census job (CC12) streams the captures once and evaluates the three blocks independently.
- **Expected fates (declared now).** CH245: the same-slot correlation share, `VIF_w` and the within-event SD gate decide; count and
  retention are not expected to bind. CH244: the tested-unit count under the carry reading decides; then `VIF_w` and receipt
  span. CH243: the median count, the concentration gate and the switch gate; expected to die at census about 24 times in 25.

**Jobs (to be drafted under `docs/research_lab/queue/drafts/`; ids q0710-q0715 checked unused in this branch's history on
2026-10-23; none is written in this commit).** `q0710_lt12_census_restore` (net, about 1,400 MB disk, `mem_mb` 400;
`depends_on` the freeze; `not_before` 2026-11-17T06:00Z); `q0711_lt12_seal` (net, 300); `q0712_lt12_census` (net, 600, streaming
with a two-capture window and the 12-slot carry state; `cpu` 1,200 exclusive if the dry run measures more); `q0713_lt12_size_check`
(cpu, 800, after the census values are committed; `max_retries 1`); `q0714_lt12_reader` (fallback only); `q0715_lt12_analysis`
(cpu, 4,000, exclusive, `not_before` the analysis date). Never promoted while E015's or E022's analysis, or an LT9, LT10 or LT11
census, size check or analysis, is running (memory-heavy-jobs rule). Each counts 0.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written
- `backend/astrolabe/research_lab/live_tests12_base.py`: vendored, hash-pinned copies of `move_join`, `classify`, the slot grid,
  LT7's `RewardCarry`, LT5's `block_fl_gate`, LT11's event-phase wrapper and `volume_num` classifier, LT3's `paper_taker` and
  `econ`, LT9's lag-slot loader and seal helpers, the CH251 map's `fee_class`, the sports and crypto classifiers; a provenance
  test checks each against its source hash. **No E026 frozen file is imported, copied or edited.**
- `backend/astrolabe/research_lab/live_tests12.py`: unit builders (2.2-2.3, 3.2-3.3, 4.2-4.3), reader, `ops-stats`, census (7),
  size-check worlds (1.8.1), analysis (1.7-1.10).
- `scripts/research_lab/run_live_tests12.py` (`seal`, `census`, `size-check`, `reader`, `backfill-series`, `ops-stats`, `analyze`).
- `backend/astrolabe/research_lab/model_specs/live_tests12_v1.json` (unpinned until 8.4); `battery2.KIND_RULES["live_tests12"]`.

### 8.2 Resources and install
- **No new collector, no network.** A pure reader of the pass's captures and sidecars (the reward feed for CH244's sensitivity).
- **Memory (planning, then a ladder):** per market 12 mids, the slot-keyed `volume_num`, the fee class and cell, the carry texts;
  per neg-risk event the previous capture's member rows: **steady 300-450 MB, peak 450-600 MB.** Ladder measured by a host dry
  run with the exact install command: (1) one reader under `ulimit -v 1572864`, accepted at peak RSS <= 650 MB; (2) else two
  readers (CH245 + CH244; CH243) under one shared `flock`, each <= 650 MB; (3) else no pin (recorded).
- **Install: host cron** `25 */2 * * *`, own `flock`, `nice -n 19`, `oom_score_adj 1000`; q0714 is the fallback, never both.
  Concurrency: LT9's reader may install in late December; E026 runs to 12-07; LT11's reader ends with its window.
- **Disk:** about 1-2 GB over the window (CH244's member units dominate); refuse above 3.0 GB. **Analysis:** about 1-2 million
  unit rows, 200 refits per gate, planning 3-4 GB, exclusive.
- **Host change:** the cron line, under the standing collection authorisation, by the orchestrator.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests12.py`, synthetic only)
Causality (no unit builder reads capture k + 1 or later; decision time = capture k's last receipt); the event key, pair and ladder
completeness, `members_changed`, `augmented`, the 120 s span at k - 1 and k; CH245's asymmetry rule (one tick of `tick_e`), the
thin member as the only unit, `sym` giving no unit, the sha256 placebo rule reading capture k only, the control basis (no
collinear mirror gap column), the twin's NaN rule; CH244's mixed rule at k - 1, `status_switched`, the shock excluding the own
move, `lowliq` within event, tier from `liquidity`; CH243's fee reading order, `fee_unknown` never inferred, the market-constant
panel and `fee_switched`, `created_at` age classes, covered cells read from the spec, the `volume_num` classes keyed by slot (no
carry-forward), the median-capped `n1`; the event-phase gate keeps one offset per event; the lag-slot loader returns only twin
terms; the coverage check returns before any gate; `ops-stats` reads no price, spread, volume or liquidity column; spec NaN
refusal; seal and pin refusals; the analysis refuses before its date; the worlds generate the declared shapes; vendored copies
match their hashes; `test_pinned_files_hash_to_the_pins` (E026) stays green.

### 8.4 Registration steps and pins (in order)
1. Challenger R1 on this file; the response and re-check.
2. **Design-text freeze commit**, sha256 in the ledger, planned by 2026-11-06 (before `T_LT11c`), required before the seal commit
   and `T_LT11`; the embargo requests of 9 filed in `signal_engine/CANDIDATES.md` in the same session.
3. Code (8.1, 8.3), a `science-reviewer` freeze check of census and size-check code; size-check run time per world measured at a
   timing seed other than 20261597 (20 worlds each; only the clock read) and projected; if census commit + projected run + 24 h
   margin + the dry run cannot precede 2026-12-08T00:00Z, the ordered lane is declared by a ledger line before the seal.
4. q0710 restore, q0711 seal (after 2026-11-17T06:00Z); seal committed and pulled on the host.
5. Census q0712; `census_dropped` and `census_unavailable (coverage)` recorded separately; `k_tests` and the census-fixed values
   filled with the exact census floats; a freeze record (module hashes, spec hash, census output hash re-verified).
6. Size check q0713 (2,000 worlds x 200 draws, seed 20261597); results recorded per test.
7. Reader freeze check; host dry run following 8.2's ladder.
8. Embargo entries verified (a missing entry blocks the pin); tokens of dropped tests withdrawn with a ledger line.
9. Pins `SPEC_SHA256`, `code_sha256`, `code_check`; E-numbers assigned; the ledger entry is the registration commit, **before
   2026-12-09T00:00Z** and at least 24 h before `REGISTERED_UTC`.
10. Cron installed and `backfill-series` within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`; `pinned: true` and
    `nothing_new` verified; q0715 queued with `not_before` 2027-01-01T12:00Z.

**Timetable (fast lane, planning):** R1, response, re-check 10-24..11-04; freeze by 11-06; code and check 11-06..11-16; restore and
seal 11-17..11-18; census 11-18..11-19; size check 11-19..11-24; reader check and dry run 11-25..11-30; embargo verification and
pin by 12-07; window 12-10..12-31; analysis on or after 2027-01-01T12:00Z.

## 9. Signal-engine mapping and embargo requests
Every family is point-in-time from the origin capture and its 12-slot look-back (DESIGN_V1 16) and an auxiliary family (own
write-once table and version). **The LT12 date** = the later of **2027-01-03T00:00Z** and LT12's analysis commit (ordered lane: the
later of its analysis date plus 36 h and its analysis commit). Filed in `CANDIDATES.md` at the freeze, applied before the
registration commit. This branch edits no engine code, `config.EMBARGO` or `CANDIDATES.md`.

| Test | Family (aux version) | Columns | Token -> until |
|---|---|---|---|
| CH245 | `nrslack` spec on two-member rows (`se-aux-nrslack-v2`) | innovations `nr_twin_dspread`, `nr_thin_x_twin_dspread`; levels `nr_twin_spread`, `nr_gap_ask`, `nr_gap_bid`, `nr_thin` may be built (they fall under LT11's `nrslack` token to 2026-12-12 anyway) | `mirror` (new) -> LT12 date |
| CH244 | `event` / `nrslack` (`se-aux-mixedlad-v1`) | interaction `nr_shock_x_unrew`; levels `nr_mixed`, `nr_unrew_share`, `nr_own_unrew` only after the `rewards` date (2026-11-18) | `mixedlad` (new) -> LT12 date |
| CH243 | `tilt` / `movetype` | `tl_fee_x_traded` (after `movetype`'s 2026-11-22); levels `tl_fee_free`, `tl_fee_src` may be built now | `feeclass` (new, only if CH243 survives its census) -> LT12 date |

- **Pre-freeze hold (now):** no scored family holds a two-member twin's spread innovation, a reward-status x sibling-shock
  interaction, or a fee-class x traded-move interaction before LT12's freeze. If one is scored, the matching test carries
  *informed (engine)* and the ledger records the first scored capture. Levels (`event`'s existing columns, `tilt`'s `tl_fee_ps`,
  `tl_rebate_ps`) are not requested.
- **Attribution limit `attrlimit_lt12`** to the LT12 date: no attribution of the champion, se1 or any broad model on twin-spread
  interactions inside `event` / `nrslack`, on reward-status x shock interactions inside `event`, or on fee-class x traded-move
  interactions inside `tilt` / `movetype`; `no_broad_families: ["mirror", "mixedlad", "feeclass"]`.
- A test dropped at census has its token and any limit item made only for it withdrawn with a ledger line. An engine gain never
  changes an LT12 verdict; an LT12 verdict never promotes a model.

## 10. Disclosures
- **Read to write this file:** `CREATIVE_HYPOTHESES_2026-10-31.md` (sections 0-1, CH243-CH245, CH248, CH250, CH251, section 3),
  `CH251_MAP_2026-10-23.md` (whole), `CH240_MAP_2026-10-23.md` (whole), `LIVE_TESTS_11.md` (sections 0-13), `LIVE_TESTS_10.md`
  (header, 1.1), a bounded read of `EXPERIMENT_LEDGER.md` (the CH251, CH242 and LT11-freeze entries), a grep of
  `population_map_ch251.py` (the fee-class and age definitions; code only), git greps for the seed and queue ids. No host,
  network, `ssh`, `data-dumps`, evidence JSON, census output, prediction, target or P&L.
- **The CH251 map** counted populations on captures 2026-10-13..10-23 (k - 1 and k only; no target, no P&L); seen before every
  gate here (10.1). **The CH240 map** likewise.
- **Development looks:** the `event` family's level scores (visible since 2026-10-22T12:00Z); se1 (category one-hot, mid, own
  move); `tilt`'s level challengers se24 / se25 (`tl_fee_ps`, `tl_rebate_ps` levels); E005, HB1 XM1-XM3 and L1-L4 (ladder mids,
  closed). None reads an LT12 state as defined here; no LT12 designer has read se24 or se25 scores.
- **Not known at the planned freeze:** E015, E022, LT11 results; LT11's census output.

### 10.1 Values declared now and their planning sources
| Value | Where | Source | Informed by the CH251 map? |
|---|---|---|---|
| CH245 thin-only unit; `sym` a class | 2.2 | dependence, mechanism | **yes** (thin / sym shares, the per-pair note) |
| CH245 count gate 186 a capture | 2.4, 7 | 2 x the F line at DE 11 | **yes** (chosen with 499 in view) |
| CH245 same-slot 0.8 / 50%, SD 1 tick / 50%, `VIF_w` 2.0, span and completeness 60% | 7 | round 17, unchanged | partly (map pooled correlations seen; values unchanged) |
| CH245 placebo rule and coverage 90% | 2.3, 7 | rule 18 | no |
| CH244 count gates 362 / 181 | 3.4, 7 | 2 x the F line at shock share 0.5 | **yes** (the map's shock share 0.51) |
| CH244 shock 2 ticks, band [0.10, 0.80], corr 0.5, 3-10 members | 3.2, 7 | round 17, unchanged | values unchanged; the 11+ arm's thinness informed (0.31) |
| CH243 median gate 170, concentration 30% of top 10%, switch 5% | 4.4, 7 | the plain kill line; conventions | **yes** (non-stationarity) |
| CH243 F as a label | 1.9, 6 item 9 | round 17's door | **yes** (the 522 line against map readings) |
| CH243 covered cells (>= 20 / >= 20), coverage 60% | 4.2, 7 | round 17 (20, 60%) | partly (age from `created_at`, seen in the map code) |
| CH243 unknown-share gates (0.40, 80% / 25%, corr 0.3) | 7 | LT11 CH234's values | partly (fee-free unusable 213 a capture) |
| Tier bins $1k / $10k / $100k | 1.4.2 | `cost-model-v1` | yes (the map found no tier) |
| `DE_gate` floors 5.0, 5.0, 6.196; `G_eff >= 15` | 7 | LT11 | no |
| Seed 20261597; q0710-q0715 | 1.8, 7 | unused values | no |

## 11. DESIGN-AMBIGUITY items for the challenger review
1. **A1 (CH243, F as a label).** Is accepting round 17's door (F reported, verdict-size worlds 13-15 binding) defensible given LT11
   R1's ruling A4, when one of the three reasons is power? If not, CH243 leaves LT12 before the freeze (6 item 9); should it?
2. **A2 (CH245, thin-only unit).** Is one unit per asymmetric pair-capture (the thin member) the right dependence-aware unit, or
   should the primary pool both members with event clusters as the round sketched? Is excluding `sym` pair-captures (half of rr)
   from the primary a selection on the state's past (the k - 1 spreads) that a reviewer should worry about?
3. **A3 (CH245, mirror levels at k - 1).** Is controlling the mirror at k - 1 (and reporting the k form) right under rule 18's
   "the level of the twin gap ... is a control", or does rule 18 intend the level at k?
4. **A4 (CH245, the placebo as binding).** Rule 18 says the placebo "must be null". Is a binding point condition (betâ_placebo <
   0.5 x betâ_thin) the right reading, or should it be a size world only? Is "the next pair by sha256 of the key at the same
   capture" an unrelated pair, given that two pairs can share news (two races, one election)?
5. **A5 (CH245, identification gate).** The round's "within-event SD of the dense innovation >= 1 tick in >= 50% of events" may
   fail on a 1c grid even where the state varies usefully (a book that moves one tick on one slot in four has SD 0.5 tick). Kept
   unchanged; is it the right identification line?
6. **A6 (gate strata).** Demeaning in event x UTC day but gating on whole events (one offset per event) because an event-day holds
   under 16 thin units. Is this mixed form valid for rule 18's "the stratum is event x UTC day"?
7. **A7 (CH244, the CLOB feed).** Round 17 says the feed adjudicates the status; LT12 uses carry status alone and reports the
   feed-agreement refit. Should feed disagreement instead exclude units (making the population depend on the feed's coverage)?
8. **A8 (CH244, the low-liquidity twin).** Is a within-event below-median liquidity indicator the right "tier twin" for the point
   condition, given that tier x shock (absolute bins) is already a control?
9. **A9 (CH244, status fixed per market-day).** The round says switchers are excluded; LT12 fixes status at the member's first unit
   of the UTC day and excludes later units that differ. Is the day the right horizon, given 2,112-3,995 switching markets a day?
10. **A10 (CH243, median gate).** Is the median over covered captures the right count statistic for a non-stationary population,
    and is the concentration gate (top 10% of captures <= 30%) a valid design condition or a gate that kills a real population
    whose activity is bursty?
11. **A11 (CH243, fee switch 5%).** An unprobed share gate (lesson (ii)); it guards rule 20 (a panel must be a market constant).
    Keep, loosen, or make it descriptive?
12. **A12 (CH243, point condition in absolute value on a pooled model).** Acceptable departure from LT11's signed, same-model
    point conditions?
13. **A13 (count gates at twice the kill line).** CH245 186 and CH244 362 follow LT11 CH233's practice; CH243's 170 is the line
    itself (on a median). Consistent enough?
14. **A14 (priors).** The designer moved CH244 up (0.20 to 0.30) on the weak status-liquidity correlation and moved CH243 down; the
    status reading behind the map's numbers is the simple one. Is the CH244 update justified given the omission caveat?
15. **A15 (adjacent captures).** LT12's census look-back reads 2026-11-06 captures (inside LT11's census seal span) and its window
    look-back reads 2026-12-09 captures (LT11 target and twin slots). Raw rows only, no LT11 object computed. Acceptable under
    round 17's exclusion of LT11's objects and window captures?
16. **A16 (time-of-year).** The holiday fortnight is in the window; only a sensitivity is declared. Should the analysis floors
    (Unavailable) be raised for it, given lower activity, or is the projection stop rule (1.12) enough?

## 12. Draft ledger block (DRAFT, not registered, not counted)
```
## LT12 design draft, 2026-10-23 (experiments autopilot; nothing counted)
- Draft docs/research_lab/LIVE_TESTS_12.md on feat/live-tests-12: CH245 (the mirror), CH244 (the farmed half), CH243 (the fee,
  conditional; F a label). DRAFT, not frozen, R1 not run, not registered. Planning inputs: CH251 map (counts only).
- Fast lane: freeze before the seal and T_LT11 (planned 11-06); census seal [11-07, 11-17); window 12-10..12-31; analysis after
  2027-01-01T12Z. Designer's census odds 0.30 / 0.30 / 0.04; P(no test) about 0.47.
```
