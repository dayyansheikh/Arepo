# Measurement M2 (CH264, "the overdue mid"): the favoured side's realised payoff against its ask in markets first seen 2 h past their `end_date` with an interior mid, held to resolution, k = 0 (DRAFT)

**Status: DRAFT 2026-10-30, second draft plus re-check fixes (challenger R1, `reviews/M2_CHALLENGER_R1_2026-10-30.md`,
GO_WITH_CHANGES on `c075355b…0ca4`, mapped in section 18; re-check `reviews/M2_R1_RECHECK_2026-10-30.md`, NOT_READY on
two wording defects, MUST 1-2 and SHOULD 1-10 applied, mapped in section 19). Next: J1 extractor code and synthetic tests,
then M2-J0 (dry mode), final verification, freeze by 2026-11-16. Not frozen, not registered, nothing counted.** Evidence role
`prospective_measurement` (rule 26 of `CREATIVE_HYPOTHESES_2026-11-02.md` 0.3; role and conditions set by the binding
ruling `reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`, ACCEPT_WITH_CONDITIONS for the role, **REVISE** for CH264;
every REVISE item is mapped in section 17). Drafted on branch `feat/m2-ch264` from the `chore/arepo-claude-setup` tip
`8eb0ad9f`, a design-only commit. No M2 code, no queue file, no seal, no host read. Structure and every defect class caught
on M1 (`MEASUREMENT_M1_CH263.md`, its challenger R1 and its pre-freeze re-check) and on LT14's pre-freeze re-check are
carried over (section 17.2). Before anything is sealed this needs, in order: a challenger review (`science-reviewer`) of this
text (R1 done), the designer's response (section 18), a re-check, the J1 extractor code for 3.2, 3.3 and 3.5 written and
unit-tested on synthetic data (tests i-viii), **M2-J0 = that code in dry mode, its `code_sha` recorded in J0's seal**, a final
pre-freeze verification, the design-text freeze commit (sha256 in the ledger), the remaining code (J2, J3, A), a code-freeze
check that lists every change to the J1 code since J0's `code_sha` with its diff and reason, a host dry run with peak RSS,
and the registration commit (spec and code pins plus the ledger block of 16) at least 24 h before
`REGISTERED_UTC` (section 2). Until the pins exist, every line a reader writes is `prospective_unregistered`.
**J0 runs before the design-text freeze and is counts only (no resolution, outcome, follow-up state or post-k price). Its
only effects on this text are rules (a) and (e) of 9.1 (the window length and the choice between two rule-class
receipt readers declared now; rule (b) is redundant and kept only as a record); nothing else can change from its output.
J0 is J1 (9.2) run in dry mode with the J1 code at the commit recorded in J0's seal.**

This is research tooling. AREPO never trades. M2 is a measurement: it reads a resolution as the declared payoff of a paper
route after the window, it is not a verdict, it is in no Holm family, and it is counted apart from the registered tests
(the ledger's correction entry of 2026-10-30 ~04:36Z already counts M1 and M2 apart). No sentence in this file is a claim
that the route makes money. Every count quoted from the CH269 map, the round-19 text or the cost model is a **counts-only
planning figure, never a target** (`informed (CH269)` where it fixes a constant, 6). No outcome, resolution value, price
after an origin, P&L or evidence JSON was read to write it (reads listed in 14).

## 0. Summary

- **Object.** A non-sports ex-crypto binary market at its **first overdue capture**: the first 2-hourly capture k whose
  manifest start is at least 2 h after the market's `end_date` (as capture k's row states it), where capture k - 1 showed the
  market with a row that was not yet 2 h past its own `end_date`. At k the market must be open and accepting orders, show
  an empty UMA status (CH269's empty forms, E6), be two-sided, and have `mid_k` in [0.05, 0.95]. One unit per market (one-shot, rule 24).
- **Favoured side.** YES if `mid_k > 0.5`, NO if `mid_k < 0.5`; `mid_k = 0.5` is its own counted class `no_favourite`
  (the ruling), never in the headline.
- **Paper route.** Buy one share of the favoured side at its recorded ask at k, hold to resolution. Payoff per share
  `Q - ask_f`, `Q = 1` (resolved to the favoured side), `0.5` (split 50-50), `0` (resolved against).
- **Headline estimand (one).** `theta` = the unit-weighted mean over final-state units of `n_i = Q_i - ask_f,i - fee_i`
  (the ruling's `net = q_eff - ask - fee`), cost-model-v1 conservative fee (L1), touch, size-unlimited; event-bootstrap 95%
  CI. `E[theta] = q_eff - E[ask_f] - E[fee]`, `q_eff = P(win) + 0.5 * P(split)` on final-state units.
- **Beside it (declared, all reported):** `theta_NF` (`not_found` as a loss of the stake) in the same ledger line; the
  attrition band `[theta_W, theta_B]`; components (`q_eff`, mean `mid_f`, mean half-spread, mean fee); the gross difference
  at the mid `q_eff - mean mid_f`; `theta` under L2 and with capital; twelve k-visible splits and two descriptive contrasts;
  an event-level bound on the non-payout share; the **proposal hazard under declared right-censoring** (7.3); the time to
  close; post-k descriptive classes (moved `end_date`, closed by k + 1) that **never exclude a unit**.
- **Window** 2026-11-24T00:00Z .. 2026-12-15T00:00Z (21 days; same calendar as M1, disjoint units by construction, 2);
  **read-out on or after 2027-01-29T00:00Z** (45 days after the end); analysis on or after 2027-01-29T12:00Z. Design-text
  freeze by 2026-11-16T23:59Z; registration commit by 2026-11-22T23:59Z.
- **Planning.** CH269: 159 overdue interior-mid units a day (median full day, the map's looser rule), 1,347 units over 556
  events (2.42 per event); M2's stricter one-shot rule gives an assumed 120-159 a day, 2,500-3,340 units in 21 days. **Open
  interest is empty on all 25,256,781 sidecar rows**, so the idea's open-interest terciles are impossible; the size split is
  the **liquidity proxy with CH269's census-fixed cuts** (6, decided now). Capacity at the touch is **unavailable by
  construction** (5.3). A "coarse" headline is about as likely as not, and coarse split cells are near certain (10).

## 1. Common rules (as M1; binding from this draft)

1. **Wording.** Estimands are definitions, never directional hypotheses. The only ledger form is: "measured (prospective,
   k = 0; units seen at their first overdue 2 h capture, open, unproposed, two-sided and interior at k): theta = X [95% CI],
   theta_NF = X_NF [95% CI], band [theta_W, theta_B], cost-model-v1, conservative fee, touch, size-unlimited, capacity
   unavailable (no book is read for past-end markets)." `theta_NF` and the band always sit in the same line as `theta`. The
   six words listed in the ruling (condition 1) are used in no M2 output, ledger line or display; no p-value is computed or
   printed.
2. **Freeze before the window.** The headline estimand and weighting, every secondary, the complete split list and the two
   contrasts (6), the cost lines (5), the bound (7.2), the hazard's event, competing event and censoring rule (7.3), the
   outcome and descriptive classes (8), the resolution source and floor (8.4), the read-out date, the coarse thresholds (10)
   and the void conditions (11) are frozen in this text and pinned by code hash before `REGISTERED_UTC`. Every declared split
   is reported; none is dropped or added.
3. **Causality.** Eligibility, splits and every unit field use only state visible at or before the unit's decision time
   (3.3). **Only state visible at <= k excludes a unit** (the ruling). Post-k facts (a moved `end_date`, a close by k + 1,
   a later proposal) are counted descriptive classes and never remove a unit from any estimand's population.
4. **Missing data stays missing.** No class is filled, no unit is valued at a midpoint, no capture is reconstructed.
5. **Scope as a parameter.** `scope = non_sports_ex_crypto` (the owner has not decided sports). A sports arm is added only if
   the owner decides before the design-text freeze; it is then a separate, parallel measurement with its own headline, never
   pooled. Crypto stays out (its dailies resolve without a UMA proposal; CH76).
6. **Nothing here is evidence for a verdict test**, and nothing from a verdict test enters M2 (12).

## 2. Registration, window, freeze deadline and read-out

- **Window.** `REGISTERED_UTC = 2026-11-24T00:00Z`, `END_UTC = 2026-12-15T00:00Z` (21 days, 252 slots). A capture belongs to
  the window if its manifest start lies in `[REGISTERED_UTC, END_UTC)`. A unit's oldest state input is capture k - 1, so the
  first possible k is the first capture whose capture k - 1 starts at or after `REGISTERED_UTC` (planned
  2026-11-24T02:31Z). The overdue look-back (3.2, E2) reads the **fixed span `[REGISTERED_UTC - 7 d, REGISTERED_UTC)`** (84
  slots; R1 MUST 5) as raw rows only (counted `pre_window_source`), whatever the host retains beyond it. A slot of that span
  with no complete capture is counted `missing_lookback_slot`, never filled; a market overdue only in such a slot can enter
  as a candidate later (disclosed; the slot count is printed; markets that were overdue only in a missing slot cannot be counted).
- **Why the same calendar as M1.** M1's unit requires a UMA proposal state first seen at k; M2's unit requires **no** UMA
  state at k. The two unit sets are disjoint as (market, k) objects by construction. A market can be an M2 unit and later an
  M1 unit (a proposal after k); it is counted `m1_overlap` at read-out from unit ids only and never pooled. Overlapping
  calendar is therefore fine; a later window would only delay the read-out.
- **Freeze deadlines.** Design-text freeze commit by **2026-11-16T23:59Z**; code, code-freeze check and host dry run by
  2026-11-21T23:59Z; **registration commit by 2026-11-22T23:59Z** (at least 24 h before `REGISTERED_UTC`).
- **Slide rule (declared now).** If the registration commit is later than 2026-11-22T23:59Z, `REGISTERED_UTC` becomes the
  first 00:00Z at least 24 h after the registration commit (never earlier than 2026-11-24T00:00Z), the window stays 21 days
  (or 42 under 9.1 (a) / (b)), and the read-out is `END_UTC + 45 days`. Nothing else changes.
- **Read-out.** `READOUT_UTC = END_UTC + 45 days = 2027-01-29T00:00Z` (the ruling's >= 30 days). **Why 45, not M1's 31:** the
  population is selected for being late (already past `end_date` with no proposal), so the late classes (`pending`,
  `not_found`) are central to the estimand, and the hazard of 7.3 is right-censored at the read-out; 45 days gives every unit
  at least 45 days of follow-up. Units unresolved at the fetch stay `pending`.
- **One analysis, fixed end, no extension.** The analysis refuses before `READOUT_UTC + 12 h`, requires `--out`, refuses to
  overwrite, and keeps only unit lines whose `spec_sha` and `code_sha` equal the pins and whose role is
  `prospective_measurement`.
- **Overlaps (time only, no shared object).** M1 (same window), LT11 (11-18..12-09), E026 (to 12-07), LT12 (from 12-10) share
  captures with M2. M2 reads raw rows, sidecars and `gamma_rules` day files and computes none of their objects; E026's
  modules and stores are not read. The engine's eligibility requires `end_date` after the origin, so M2's units (past
  `end_date`) are disjoint from every engine row by construction.
- **Time of year (disclosed).** US Thanksgiving (2026-11-26) falls in the window; no DST change; the US midterm (11-03) and its
  resolution days fall before it. The fee-free population shrinks over time by construction; projections do not correct.

## 3. Unit, decision clock and eligibility

### 3.1 Streams read at window time (all already written by the host; no new collector)
- **Captures** `snapshots/<id>/rows.csv.gz` (manifest `state=complete` only): `market_id`, `event_id`, `binary`, `best_bid`,
  `best_ask`, `closed`, `active`, `end_date`, `liquidity`, `clob_token_id_0`, `received_utc`; the manifest start. Below,
  `bid` and `ask` mean the row's `best_bid` and `best_ask` (the outcome-0 token's Gamma touch).
- **Sidecar** `snapshots/<id>/rows_ext.csv.gz`: `received_utc`, `uma_resolution_statuses`, `accepting_orders`, `fee_type`,
  `fee_category`, `series_slugs`, `fees_enabled`, `fee_schedule`, `order_price_min_tick_size`, `open_interest` (presence
  only, 6).
- **Rule text** `stream_gamma_rules/YYYYMMDD.jsonl` (keyless change log, `streams/common.py` format): `row` / `hash` records
  for keys `m:<id>` of **committed** polls only (a slot without a following `ok` poll line is torn and ignored); text is
  classified (3.5) and dropped, never stored.
- **Not read:** book sweeps (they never select a past-end market, 5.3), trade samples, the monitor, every engine store
  (`quotes/`, `features/`, `predictions/`, resolution logs except the read-out cross-check of 8.4), every `live_tests*` store,
  E025 / E026 stores, M1's store (except unit ids at read-out, 2), any Gamma outcome field at window time.
- **Retention.** Snapshots are kept about 8 days on the host, so J1 (9.2) runs during the window and writes write-once unit
  files; a capture it misses before retention removes it is `missing_capture` (counted, never rebuilt).

### 3.2 Eligibility (only state visible at <= k; each exclusion a counted class)
Every complete capture in the window is processed in chronological order (9.2). The candidates at k are the markets whose
row at k has `age_k = start_k - end_date_k >= 2 h` (`end_date` parsed as UTC; `start_k` the manifest start) and that are
**not in the overdue-seen set** (every market of any category seen with `age >= 2 h` at any processed capture of the fixed
look-back span or of the window before k). The overdue stock (about 1,363 past-end markets a capture in CH269) is therefore never re-read
as new candidates. A market in the overdue-seen set that was not overdue at k - 1 because its
`end_date` moved, and is overdue again at k, is not a candidate and is counted `reoverdue_seen` (funnel exhaustiveness). A candidate becomes a unit if all of the following hold, checked in this order (the first failing rule
names the class):
- **E1 Capture.** Captures k and k - 1 are complete and k - 1 is the immediately previous 2 h slot (`grid0 =
  2026-10-01T00:31Z`, tolerance 30 min, first complete capture of the slot), and k - 1 was folded into the state (not
  `missing_capture` or `late_capture_ignored`). Else `no_previous_capture`.
- **E2 First overdue slot.** The market has a row at k - 1 (else `no_k_minus_1_row`) whose own `age_{k-1} = start_{k-1} -
  end_date_{k-1} < 2 h` (else `already_overdue_at_k_minus_1`: a guard class, expected 0 because a folded k - 1 puts every
  market with `age >= 2 h` into the set; a non-zero count is printed and audited). `end_date` missing at k: `end_date_missing` (not a candidate; counted per
  capture for scope markets).
- **E3 One-shot.** No earlier M2 unit for the market (else `prior_unit`; a market whose `end_date` is extended and later
  passes again is never a new unit).
- **E4 Open at k.** `binary = 1`, `closed` false, `active` true, `accepting_orders` true (sidecar). Else `not_open_at_k`;
  `accepting_orders` missing or unparseable is its own class `accepting_unknown`.
- **E5 Scope.** Capture k's sidecar row exists (else `sidecar_missing`) and its category, by the CH269 map's reader
  (`boundary_map_ch240.category_of(fee_type, fee_category, series_slugs, True)`) applied to **capture k's own sidecar row**,
  is `nonsports_excrypto`. Else `out_of_scope_<category>` (sports and crypto counts printed).
- **E6 Empty UMA status at k (a whitelist; R1 MUST 2).** `str(uma_resolution_statuses).strip().lower()` at k is one of
  CH269's empty forms `""`, `"[]"`, `"nan"`, `"none"` (`census_map_ch269.py`, the `ui` reading). Else `uma_state_at_k` if
  the string contains `propos` (first-seen proposals here are M1's domain), or `uma_other_at_k` for every other non-empty
  form (counted; the raw form is printed). No form outside the whitelist ever passes.
- **E7 Two-sided at k.** `0 < bid < ask <= 1`. Else `not_two_sided`.
- **E8 Interior mid.** `mid_k = round((bid + ask) / 2, 6)` (prices are decimal strings on a >= 0.0001 tick, so the mid lies
  on a 0.00005 grid; rounding to 6 dp makes every boundary comparison exact on the stored value, the LT14 float lesson);
  `0.05 <= mid_k <= 0.95`. Else `mid_low` (< 0.05) or `mid_high` (> 0.95), counted separately.
- **E9 Favourite readable.** `mid_k == 0.5` (on the rounded value): `no_favourite` (counted k-time class; its YES-resolved
  share is printed at read-out, never in any estimand). Else the unit is eligible.

**Survivorship class (k-visible, counted, never a unit).** `left_before_overdue_slot`: scope markets present and open at
k - 1 whose `end_date_{k-1} <= start_k - 2 h` and that are absent from k's rows or `closed` at k. Printed per UTC day beside
the funnel so a reader sees how many ended markets close or vanish before a first overdue capture.

### 3.3 Unit fields and decision time
- **Price on the favoured side** (rows' touch at k): YES: `ask_f = ask`, `bid_f = bid`, `mid_f = mid_k`; NO:
  `ask_f = round(1 - bid, 6)`, `bid_f = round(1 - ask, 6)`, `mid_f = round(1 - mid_k, 6)`. Spread
  `spread_k = round(ask - bid, 6)`, half-spread `h = spread_k / 2`, so `ask_f = mid_f + h` (to floating-point error).
  **Every split boundary (S6, S11) and every boundary test is applied to these rounded values** (R1 MUST 1: unrounded
  `ask - bid <= 0.01` fails on 80 of 99 one-tick spreads at tick 0.01). Tick at k recorded.
- **The touch may be stale (disclosed, unmeasured; R1 SHOULD 6).** Gamma's best bid / ask on a past-end market may lag the
  book; no book is read (5.3), so the staleness of `ask_f` at `t_d` is not measured.
- **Decision time** `t_d` = the later of the row's `received_utc` and the sidecar row's `received_utc` (no sweep exists for
  these markets). The gap (sidecar minus row) is recorded. The rule-class input must be committed at or before `t_d` (3.5).
- **Unit record.** Everything above plus `event_id`, the event's open binary member count at k, `end_date_k`,
  `end_date_{k-1}` (the k-visible move flag of S7), `age_k`, `liquidity` at k, `open_interest` presence, category, `cat_k`,
  fee fields and the two fee lines of 5, the rule class and its commit time, the raw status strings at k and k - 1, capture
  ids, `spec_sha`, `code_sha`. **Nothing from after capture k.**

### 3.4 Cluster
The cluster is the Gamma `event_id` at k. No cap: weights are declared instead (4).

### 3.5 Rule class at `t_d` (the S2 reader; pinned)
- **Lexicon.** CH269's placeholder lexicon, copied verbatim into M2's own module (CH269's module is not frozen and may change):
  `classify_rule(question + description + resolutionSource)` with CH269's `SCHEDULED_RE` and `BARRIER_RE`, giving
  `scheduled`, `barrier`, `both` or `other`; no record for the market at or before `t_d`: `no_rules`; a `hash` record whose
  full row is no longer in a retained day file: `rules_unresolved` (its own cell, never `no_rules`; R1 SHOULD 8). The sha256 of the two pattern strings is a spec pin. It is a
  placeholder reading, **not** CH239's parser, and it does not detect consensus-sourced rules (disclosed; the idea's
  "consensus-sourced" cut is not available).
- **k-visible reader (declared now; the CH269 map's "last row wins" read rows after k and is not used).** The market's
  class is computed from its last `row` (or `hash` resolved to its full row) in a committed poll whose `poll` line was
  written at or before `t_d`, across retained day files. If J0 finds that committed poll lines carry no usable receipt time,
  rule (e) of 9.1 applies: only day files of UTC days strictly before k's UTC day are read. Either way no row after `t_d`
  is read.
- **Coverage is selected (disclosed).** The `gamma_rules` frame holds open markets with `volume24hr > 0` (top 3,000 hourly,
  the full frame four times a day), so `no_rules` collects the quietest markets; CH269 counted 180 `no_rules` of 1,347 units
  (13%) under its looser reader. `no_rules` is a reported cell, never filled.

### 3.6 Declared readings disclosed (no size check; M2 has no test)
- **S49, an `end_date` that is not the resolution clock.** Some rules resolve on a later publication, so "overdue" by
  `end_date` is not overdue by the rule. The rule class names some of these where read; the unclassed share is the
  disclosure. No unit is excluded for it.
- **S50, a stale `accepting_orders`.** The flag may be true on a market the venue has already closed. A buyer at k sees only
  the flag, so the unit stays; the read-out's `closedTime` gives the descriptive classes `closed_before_t_d` and
  `closed_within_one_slot` (8.2). The idea's "unavailable if closed at k + 1" exclusion is **removed** (the ruling).
- **Moved `end_date` after k.** The idea's "`unavailable` if `end_date` moved inside the window" exclusion is **removed** (the
  ruling). A move at k (`end_date_k != end_date_{k-1}`, more than 1 s) is k-visible and is split S7; a move after k is the
  read-out descriptive class `end_date_changed_after_k` (8.2). CH269 counted a moved share of 0.0 at entry.

## 4. Headline estimand and weighting

- **Per-unit net per share** (final-state units only, 8.1): `n_i = Q_i - ask_f,i - fee_i`, `Q_i = 1` (resolved to the
  favoured side), `0` (resolved to the other side), `0.5` (split 50-50); `fee_i` the L1 line of 5.
- **Headline:** `theta = (1 / N_F) * sum_i n_i` over the `N_F` final-state units: **unit-weighted**, cost line L1, touch,
  size-unlimited. 95% CI by the event bootstrap (7.1). `E[theta] = q_eff - E[ask_f] - E[fee]`,
  `q_eff = P(win) + 0.5 * P(split)` (final-state units).
- **`theta_NF` (the ruling's "both ways"; always printed in the same line):** `not_found` units added with `Q = 0` (the price
  paid lost), every other non-final class still excluded; its own event-bootstrap CI. **Never valued at the mid.**
- **Attrition band:** `theta_W` = every `pending`, `not_found` and `unavailable` unit at `Q = 0`; `theta_B` = every such unit
  at `Q = 1`. Both labelled bounds, not estimates.
- **Declared secondary weighting (reported beside, never substituted):** `theta_E`, event-weighted (each event weight 1,
  split equally over its final-state units).
- **Components, each with its event-bootstrap CI:** `q_eff`; `P(win)`, `P(loss)`, `P(split)`; mean `mid_f`; mean `h`; mean
  fee (L1 and L2); the **gross difference at the mid** `pi = q_eff - mean mid_f` (no fill; descriptive) and the identity
  `theta = pi - mean h - mean fee` on the same units, **checked within 1e-9, never with `==`** (R1 SHOULD 3).
- **Secondaries:** `theta` under L2; `theta_cap = theta - mean cap_i` (5.2); mean `Q` and count for `no_favourite`. No
  secondary drops a unit by a post-k state (the earlier `theta_open` is removed, R1 MUST 4; 8.2 prints each post-k class's
  count and mean `n_i` only).
- **Conditioning disclosed (LT14's lesson).** `theta` is conditional on reaching a final state by the read-out. Reaching it is
  after k and may depend on the payoff (ambiguous rules may settle late, split or vanish), so `theta` alone can move with
  attrition alone; this is why `theta_NF` and the band sit in the same line and why coarse rule 3 (10) exists. No reading of
  `theta` alone is allowed.

## 5. Cost lines (cost-model-v1, recorded prices; one entry convention only)

- **Entry convention: ask-based** (the ruling's `net = q_eff - ask - fee`). The half-spread is inside `ask_f`, so **no
  half-spread is subtracted again** (`COST_MODEL.md` 3, `taker_leg`'s hold-to-resolution case: no exit cost).
- **Fee, two lines,** per share at `p = ask_f` by `costs.taker_fee_ps` (`rate * (p * (1 - p)) ** exponent`, unrounded per
  share). Both lines and S3 use `cat_k = costs.category_key(capture k's sidecar fee_category)` (E5's `category_of` is the
  scope reader only). `exponent` = the `fee_schedule`'s exponent where served, else 1.0; `schedule_rate` = its rate where
  served, else None.
  - **L1 (headline):** `costs.taker_rate(cat_k, schedule_rate, fees_enabled, policy="conservative")`: max(served schedule,
    docs rate), 0 if `fees_enabled` is False; **for a key outside the docs table: the served rate, possibly 0** (0.07 only
    when no schedule is served; `costs.py:93-104`, R1 Q9). `fees_enabled` is passed as False when served and not `_truthy`,
    True when served and truthy, None when missing (the sidecar holds a string; `taker_rate` returns 0 only for `is False`).
    Disclosed: S4 `fee_free` units of the `rate_zero` kind (`fee_class`, `population_map_ch251.py:116`) still carry L1 = the
    docs rate unless the flag is off.
  - **L2 (docs-rate line; rate-0-not-trusted):** `costs.taker_rate(cat_k, schedule_rate, fees_enabled=None,
    policy="conservative")` when `cat_k` is a `CATEGORY_TAKER_RATE` key; **`costs.MAX_TAKER_RATE` (0.07) when it is not**.
    Reason for the second clause: `taker_rate` drops a NaN docs rate, so an unknown key with a served schedule of 0 returns
    0, not 0.07 (`costs.py` `taker_rate`, the `cands` filter); L2 must not inherit a served 0 it does not trust. Docs rates
    (`COST_MODEL.md` 2): 0.04 finance / politics / mentions / tech; 0.05 economics / culture / weather / other; geopolitics 0.
- **Size of the fee here.** Unlike M1, units sit in the interior, where `p(1 - p)` is 0.05-0.25: at `p = 0.8` and rate 0.05
  the fee is 0.8c a share, comparable to the CI (10). Both lines are always printed.
- `costs.py` is E026-frozen; M2 imports it and never edits it; its sha256 (`258856fc…844d` at this draft) is in M2's pins.
  The sha256 of every imported module whose function sets an eligibility class, split cell or outcome class
  (`boundary_map_ch240.py`, `cb17_census.py`, `live_tests11_base.py`, `population_map_ch251.py`, `calibration.py`,
  `costs.py`) is a spec pin, recorded in J0's seal and at registration. A difference at the analysis is void 11.1. Fact
  checked at this re-check: none of these files is pinned as a file by an earlier spec (LT11 pins only the source hashes of
  its vendored pieces by a provenance test; CB17 pins a bundle hash covering `cb17_census`), so the pins are new. Also
  pinned: `live_tests8_base.py`, because `boundary_map_ch240.category_of` calls its `crypto_class` (the same logic as the
  `live_tests11_base.py` copy at l. 718-727).
  Liquidity rewards, holding rewards and rebates are not in any line (disclosed).

### 5.2 Capital and the wait
`w_i = closedTime - t_d` in hours from the read-out record (8.4); `closedTime` missing: `w_i = fetched_utc - t_d` (upper
bound, `wait_upper_bound`); `closedTime < t_d`: `w_i = 0`, counted `wait_clock_anomaly` (and class `closed_before_t_d`).
`cap_i = ask_f * 0.05 * w_i / 8760` (5% a year), used only in `theta_cap`. The wait's distribution (median, p90, max) is
reported; it is never a split (it is after k).

### 5.3 Capacity: unavailable by construction (declared now)
Sweep 1 selects only markets with `end_date` more than 3 h after receipt (`book_sweep.select_tokens` ->
`panel.eligibility_mask(binary, t_i + forecast.FORECAST_END_MARGIN_H * 3600)`), so **no M2 unit ever has a sweep row**. The
rows carry no ask size. **No dedicated book fetch is added** (a new collector before the freeze; its receipt would move
`t_d` past the touch; M1 R1 MUST 4's reasoning). The ledger line says "capacity unavailable". The rows' `liquidity` at k is
printed as a descriptor (median, p25, p75, by S1), labelled **not capacity**.

### 5.4 Rule 25 reference lines (printed, never thresholds)
M2 has no decision line. Beside S9 (tick) only: for tick-0.01 units the cents floors (0.5c mid, 1.0c spread) are printed as
reference lines; for tick-0.001 units (the ruling: rule 25 applies inside [0.05, 0.95] only where the tick is 0.001) the
zone's recorded round trip (median `h` at k over tick-0.001 units plus the L2 fee at their median `ask_f`) and one tick
(0.1c) are printed instead. Computed from k-time fields only; they gate nothing.

## 6. Splits and declared descriptive contrasts (complete list; every one reported; all k-visible)

Each cell reports `N` units, events, final-state count, `q_eff`, mean `mid_f`, mean `h`, mean fee (L1), `theta` and
`theta_NF` with event-bootstrap CIs, and the non-final class counts. Cells with fewer than 30 final-state units or 10 events
print their numbers labelled `thin` (never suppressed).

**The size split, decided now.** Open interest is empty on all 25,256,781 sidecar rows of CH269's span (0 units with a
value), so an open-interest tercile would be one `na` cell. M2 uses the **liquidity proxy**: the row's `liquidity` at k,
cut at CH269's census-fixed values **47.46151 and 330.74525** (`seals/CH269_map_q0730.json`, `tercile_cuts_census_fixed`;
counts-only pre-window data, `informed (CH269)`). Reasons: (i) it is the only k-visible size field populated on these rows
(CH269: no `na` among 1,347 units); (ii) cuts fixed before the window keep the split k-visible (window terciles would let
later units' values set an earlier unit's cell); (iii) dropping it would remove the one descriptive contrast the ruling
allows. It is **not open interest** (it measures resting quotes, not positions outstanding), it is labelled "liquidity
(proxy)" wherever printed, and the window's cell shares will not be thirds (printed). If `open_interest` starts to be served
during the window it is **not** used; its presence share is printed only.

| # | Split | Cells |
|---|---|---|
| S1 | liquidity at k (proxy; fixed cuts) | low (< 47.46151), mid (< 330.74525), high, na |
| S2 | rule class at `t_d` (3.5) | scheduled, barrier, both, other, no_rules, rules_unresolved |
| S3 | fee category `cat_k` | economics, culture, weather, other, finance, politics, mentions, tech, geopolitics, unknown (= any `cat_k` outside those nine keys; E5 structurally excludes an empty `fee_category`, since `non_crypto` needs a non-empty one, `live_tests11_base.py:718-727`; 10 cells fixed by rule; J0 prints the distribution) |
| S4 | fee class at k, by `population_map_ch251.fee_class(fees_enabled, has_fe_col, fee_schedule)` (CH269's reader) | fee_free (`fees_enabled` served and false, or served schedule rate <= 0), fee_on (served rate > 0), unknown (no parseable schedule) |
| S5 | favoured side (YES = outcome 0, NO = outcome 1, also for non-Yes/No binaries) | YES, NO |
| S6 | favoured mid zone `mid_f` (rounded, 3.3) | (0.5, 0.6], (0.6, 0.7], (0.7, 0.8], (0.8, 0.9], (0.9, 0.95] |
| S7 | `end_date` moved at k (`end_date_k != end_date_{k-1}`) | no, yes |
| S8 | event member count at k | 1, 2-5, 6+ |
| S9 | tick size at k | 0.001, 0.01, other / missing |
| S10 | window week | days 1-7, 8-14, 15-21 |
| S11 | spread at k (`spread_k`, rounded, 3.3) | <= 0.01, (0.01, 0.03], (0.03, 0.10], > 0.10 |
| S12 | S1 x S2 (the idea's size x class grid) | 4 x 6 = 24 cells |

**Declared descriptive contrasts (the ruling: a difference with a CI, never an identification):**
- **D1** = `theta(S1 high) - theta(S1 low)`, and the same for `pi` and for the 24 h proposal incidence of 7.3.
- **D2** = `theta(S2 scheduled) - theta(S2 barrier)`, and the same for `pi`.
Each with its event-bootstrap CI (events resampled once; the difference taken within each draw). No reading of D1 or D2 as
"ambiguity" or "inattention" is allowed (13).

Structural notes (disclosed): S7 "yes" is near-empty by CH269 (moved share 0.0); S8 "1" means the event's only open binary
market; S6 cells mirror S5 under the YES / NO symmetry and are not independent of it; S12 is S1 x S2 and adds no new
variable. **Likely empty or thin cells (disclosed; R1 SHOULD 2; CH269 counts under its looser reader):** S2 `scheduled` 14
of 1,347 units, so D2's `scheduled` arm is expected `thin`; S12 high x `no_rules` 0; S1 is confounded with rule coverage
(154 of 180 `no_rules` units in the low cell), so S1 differences mix size and coverage. Selection width for later tests:
**12 splits, 69 cells** (S1 4, S2 6, S3 10, S4 3, S5 2, S6 5, S7 2, S8 3, S9 3, S10 3, S11 4, S12 24) **plus 2 contrasts**.

## 7. Inference

### 7.1 Event bootstrap (headline and every CI)
Resample events with replacement (all of an event's units together), B = 10,000, `numpy.random.default_rng(20261125)`,
percentile 95% interval; the same event draws serve every component, contrast and the hazard, and a split cell's CI uses the
same draws restricted to the cell's units; draws with no final-state unit in the cell are counted and left out of that cell's
percentiles. **Event-clustered SE cross-check:** the CR1 event-clustered SE of `theta` and `theta_NF` is printed beside the
bootstrap interval, never substituted. **Cross-event dependence** (events resolved together on one news day) is handled only
by a block bootstrap over the 21 UTC days of k (same B and seed; it splits events whose units have k on different days, disclosed), printed beside the headline; the wider of the two
intervals is printed with it. A component with no variation (for example `P(split)` with zero splits) gives a [0, 0]
interval: **printed as degenerate; the bound of 7.2 is the bound**.

### 7.2 Event-level bound on the non-payout share
`split_50_50` and `not_found` may be rare and arrive by event (a voided ladder). Declared, as M1's corrected `T_U`:
- **Unit basis** (R1 SHOULD 5): final-state units plus `not_found` units (`N_D` units, `E_D` events); `pending` and
  `unavailable` units are outside it and counted. `I_e = 1` if any basis unit of event e is `split_50_50` or `not_found`.
- Strata s = **basis units per event** (1, 2-3, 4-9, 10+; S = 4; an inference stratum, never a split). In each stratum `p_U,s` is the
  one-sided Clopper-Pearson upper bound on the event rate at level **1 - 0.05 / S = 0.9875**. `B_U = sum_s (N_s / N_D) *
  p_U,s`, under the worst case that every unit of a flagged event is flagged. **A stratum with no events contributes 0.**
- Assumption stated: within a stratum an event's rate does not depend on its unit count (homogeneity); without it `B_U`
  bounds an event-weighted share. Printed beside: the 10 largest events' unit counts and `I_e`; per-stratum events, flags
  and `p_U,s`. With zero flags `p_U,s` is about 4.38 / E_s, so `B_U` is at least 4.38 / N_D times the sum over non-empty strata of
  their units per event, and each non-empty stratum adds at least its lower limit (1, 2, 4, 10).

### 7.3 Proposal hazard (the idea's estimand 2; declared right-censoring)
- **Data.** The blind follow-up record of 9.2 (status tokens, `closed`, `active`, row presence and `end_date` of each unit's
  market at every processed capture j > k up to `READOUT_UTC`; no price), sealed until the read-out.
- **Event P:** the first follow-up capture whose status string, split on non-letters and lower-cased, contains a **whole
  token** `proposed`, `disputed` or `resolved` (R1 MUST 2); a non-empty form with none of them is counted
  `uma_other_followup` (descriptive, not P). **Competing event C:** the
  first follow-up capture at which the row is absent or `closed` is true, with no earlier P. **Censoring:** at the last
  processed capture before `READOUT_UTC` with neither (declared right-censoring at read-out, the ruling). Time is in 2 h slots
  from k; an event observed after one or more `missing_capture` slots is attributed to the first observed capture and counted
  `interval_spans_missing`.
- **Estimands:** the Aalen-Johansen cumulative incidence of P (and of C) at 6 h, 24 h, 72 h, 7 d and 30 d after k; the
  discrete per-slot hazard of P for slots 1-12 with at-risk counts; overall and by S1 and S2 only; event-bootstrap CIs. Also
  the share of final-state units with no P ever seen (resolved without a proposal state seen at a capture).
- **Disclosed:** the status field carries no proposal time (CH269 `not_mapped.proposal_time`), so P is the first *capture*
  showing a state, not the proposal; proposals made and resolved between captures appear as C.

### 7.4 Time to close (no follow-up read)
`w_i` of 5.2 as a time-to-event descriptor over final-state and `pending` units, right-censored at `fetched_utc` for
`pending` units; `not_found` and `unavailable` units are excluded and counted (R1 SHOULD 4): Kaplan-Meier median and the
share closed by 7 d and 30 d, overall and by S1 and S2; event-bootstrap CIs.

## 8. Outcome classes, post-k descriptive classes, the resolution source and its floor

### 8.1 Classes at read-out (each counted; never filled; never valued at a midpoint)
| Class | Source reading | In `theta` | In `theta_NF` |
|---|---|---|---|
| `resolved_favoured` | `parse_outcome` gives the favoured side (`y = 1` and YES, or `y = 0` and NO; YES and NO mean outcome 0 and outcome 1) | yes, `Q = 1` | yes |
| `resolved_other` | `parse_outcome` gives the other side | yes, `Q = 0` | yes |
| `split_50_50` | reason `split_50_50` | yes, `Q = 0.5` | yes |
| `pending` | a record exists, not closed, or `parse_outcome` reason `not_resolved` (sub-class `closed_not_uma_resolved` when `closed` is true) | no; counted | no |
| `not_found` | absence established: no record in either batch pass and a single-id re-query answered HTTP 200 with no record both with and without `closed=true` (9.4) | no | yes, `Q = 0` |
| `unavailable` | `unavailable (fetch)`: no definite answer after the declared retries (including a failed single-id re-query); or `other_price_vector` / `bad_prices` (named sub-classes) | no; counted | no |
| `no_favourite` (k-time) | E9 | no; count and YES share only | no |

All eligibility classes of 3.2 are k-time exclusions and are counted in the funnel. The read-out record's
`umaResolutionStatus` is printed as a descriptive count for each class.

### 8.2 Post-k descriptive classes (never exclude; the ruling's REVISE items)
Read only at read-out from the pinned source; each unit stays in every estimand; counts and mean `n_i` printed per class:
- `end_date_changed_after_k`: the read-out record's `endDate` differs from `end_date_k` by more than 1 s;
- `closed_before_t_d`: `closedTime < t_d` (the stale-flag case S50; a fill may not have been possible; count and mean `n_i`
  only, the unit stays in every estimand);
- `closed_within_one_slot`: `t_d <= closedTime < t_d + 2 h`;
- `m1_overlap`: the market is also an M1 unit (unit ids only);
- `backlog` label: if `not_found + split_50_50` exceed 30% of units, the line is printed with "the population behaves as the
  venue's backlog, not a route" beside it (the idea's line, kept as a label, never a void and never a suppression).

### 8.3 The `not_found` question
Its payoff is unknown, so it is never valued at the mid: `theta` excludes it, `theta_NF` books it as a full loss, the band
brackets every non-final class, and its count and share sit in the ledger line through `theta_NF`.

### 8.4 Resolution source (pinned) and coverage floor
- **Pinned source:** M2's own read-out fetch (9.4) of Gamma `/markets?id=` records for every unit's market, parsed by
  `calibration.parse_outcome` at the commit pinned at registration (the engine's endpoint and parser, `se-labels-v1`; `y = 1`
  iff outcome 0 won; reason `not_resolved` unless `umaResolutionStatus == "resolved"`). The engine's resolution log is not
  the source: its candidates are markets with a res-eligible feature row, and M2's markets are past the engine's eligibility.
- **Cross-check (read-out only, never a substitute):** for units also in the engine's resolution log, agreement of state and
  `y` (counts); disagreements listed; the pinned source governs.
- **Coverage floor (R1 MUST 3).** A unit is *covered* when the source gave a definite answer: a record, or absence established
  (`not_found` as 8.1 defines it). Unit coverage = covered units / M2 units (passed E1-E9; `no_favourite` excluded and its fetch coverage printed separately), i.e. 1 minus the `unavailable (fetch)`
  share. Event coverage = share of events all of whose units are covered. **Floor 0.95 of units and 0.95 of events.** Below
  either, M2 is **void** (11). `not_found` is a counted outcome class, never a coverage failure: it is carried by
  `theta_NF`, the band, coarse rule 3 and the backlog label, so a backlog-heavy population is reported, not voided.

## 9. Collectors, stores and the job list (DRAFT specs in text only; no queue file, no code yet)

All jobs are light, `net` lane where they fetch, otherwise local; none runs concurrently with a multi-GB job (memory rule).
Store: `data-dumps/research_lab/m2_ch264/` on the host (write-once files; never edited).

### 9.1 M2-J0: pre-window counts-only check (before the design-text freeze; uncounted)
- **What J0 is.** A counts-only pre-freeze job: no resolution, no outcome field, no follow-up state after any unit's k, no
  price after k. **J0 is J1 (9.2) run in dry mode with the J1 code at the commit recorded in J0's seal** (so 3.2, 3.3 and 3.5 are applied exactly; R1
  feasibility), writing counts only and no follow-up file. Its only effects on this text are rules (a) and (e); nothing else (estimand, weight, split, cut, cost
  line, class rule, threshold, date other than by (a) / (b)) changes from it.
- Reads the last 8 days of rows and sidecars and the retained `gamma_rules` day files on the host. Applies 3.2, 3.3 and 3.5
  exactly as specified and prints **counts only**: eligible units a day; events and the units-per-event distribution (S8 and
  7.2's strata); the class funnel of 3.2 including `left_before_overdue_slot` and `already_overdue_at_k_minus_1`; cells of
  S1-S12 (counts; k-time zone counts of S6 and S11 only); `no_favourite` count; `cat_k` distribution with raw
  `fee_category` beside; the rule-class reader's coverage at `t_d` against CH269's last-row reading (counts); **whether
  committed `poll` lines carry a parseable receipt time**; `gamma_rules` day-file retention (oldest file); the forms of the
  status string (distinct normalised forms, counts); the planned follow-up volume (units x captures to the read-out).
- **Decision rules declared now:** (a) eligible units fewer than 75 a day (median full day): window extended to 42 days,
  dates rewritten before the freeze; (b) *redundant, kept as a record only* (fewer than 1,500 projected over 21 days; since 75 x 21 = 1,575 > 1,500, rule (a)
  always fires first; R1);
  (c) the size split stays the liquidity proxy with CH269's cuts whatever J0 prints; (d) none of J0's numbers changes an
  estimand, split, cut, cost line or threshold; (e) if committed `poll` lines carry no parseable receipt time, S2's reader is
  the day-before rule of 3.5. No J0 output can change the E6 whitelist or the whole-token P tokens: unforeseen status forms stay `uma_other_at_k` / `uma_other_followup`. Output labelled `informed (M2-J0)`, counts only, sealed with its code hash.
- Memory: under 600 MB (CH269's 8-day map peaked at 558.8 MB over a wider read); dry run measured.

### 9.2 M2-J1: window-time extractor and blind follow-up recorder (every pass; catch-up within retention)
- **Extractor.** For each complete capture k in the window not yet processed: read captures k - 1 and k (rows and sidecar,
  `usecols` only) and the committed `gamma_rules` records up to `t_d`; apply 3.2; write `units/<capture_id>.jsonl.gz` and
  `status/<capture_id>.json` (the funnel counts, completeness; **no P or C count and nothing derived from follow-up
  content**: for follow-up files only their sha256 and line count, R1 Q1; monitoring prints the same and no more). Idempotent per capture; refuses to overwrite; every line
  carries `spec_sha`, `code_sha`, role `prospective_measurement`. State file between runs: the overdue-seen set, the M2 unit
  ids, the folded rule classes with their commit times.
- **Look-back fold timing (re-check SHOULD 4).** J1's first pass, after the registration commit and before the first window
  capture is processed, folds the look-back span in order. A slot whose capture is absent, or already removed by retention at
  that pass, is `missing_lookback_slot`.
- **Strictly chronological (M1's re-check fix 3, adopted verbatim).** Captures are processed in increasing manifest start,
  one at a time, and a capture is processed only when every earlier slot is processed or recorded `missing_capture`;
  catch-up replays the backlog in the same order. A slot is recorded `missing_capture` once it has no complete capture 6 h
  after its grid time; a capture appearing later stays unprocessed (`late_capture_ignored`). The run refuses unless the state
  file's last folded capture is the last processed-or-missing capture before k. Each `status/<capture_id>.json` records that
  capture id and the state file's sha256 before and after. **The state used at capture k holds only captures before k and
  rule records committed at or before `t_d`.**
- **Blind follow-up recorder (for 7.3 only).** At every processed capture j (in the window and after it, up to
  `READOUT_UTC`), for every M2 unit with k < j, append to `followup/<capture_id>.jsonl.gz`: unit id, row present, `closed`,
  `active`, `accepting_orders`, the raw status string, `end_date`. **No price, bid, ask or outcome field.** Every unit is
  recorded at every capture regardless of its earlier follow-up state, so the writer never reads its own output. The
  extractor never opens a follow-up file; nothing reads one before `READOUT_UTC` (the analysis refuses; no other module
  imports the reader); each file's sha256 enters the status chain. **Procedural blinding** (R1 Q1, accepted under condition 5:
  pinned code, no price or outcome field, hashed, read only at the read-out): the follow-up is written blind during the window
  because the host keeps captures only about 8 days. Its non-reading before the read-out is a procedure, not a property the
  data can prove (11.2(b)).
- **Synthetic tests to be written:** (i) out-of-order delivery processes in order and gives the same units; (ii) a state file
  holding a capture at or after k makes the run refuse; (iii) a 12-capture catch-up gives identical unit files; (iv) deleting
  every follow-up file leaves every unit and status file byte-identical; (v) a `gamma_rules` record committed after `t_d`
  never changes a unit's S2 cell; (vi) `mid_k` boundary cases (0.05, 0.95, 0.5) classify on the rounded value; (vii) S11 and S6 boundaries: every one-tick
  spread at ticks 0.01 and 0.001 and the 0.03 / 0.10 / zone boundaries classify into the intended cell on the rounded values
  (R1 MUST 1); (viii) E6 passes only the four empty forms.
- Planned peak RSS 300-500 MB; cap 600 MB.

### 9.3 M2-J2: window close and follow-up close
- At `END_UTC + 6 h`: the unit manifest (sha256 of every unit and status file, slot coverage over the 252 slots, the
  missing-capture list), its hash committed to the ledger; the unit set is closed. At `READOUT_UTC`: the follow-up manifest
  (sha256 of every follow-up file, slot coverage after the window) committed before any read of it.

### 9.4 M2-J3: read-out resolution fetch (on or after `READOUT_UTC`)
- For every unit's market id: Gamma `/markets?id=` in batches of 50 with `closed=true`; ids not returned are fetched again
  without `closed` to separate `pending` from absence; an id absent in both passes is re-queried alone (`/markets?id=<id>`)
  both with and without `closed=true`, and only two HTTP 200 empty answers make it `not_found`. Whether Gamma returns archived
  or closed markets to `/markets?id=` is unverified, and a false `not_found` would bias `theta_NF` downward. Up to 3 attempts per batch at least 1 h apart; remaining failures
  are `unavailable (fetch)`. Records `state`, `y`, reason, `closedTime`, `endDate`, `umaResolutionStatus`, `fetched_utc`.
  About 60-200 requests. Write-once `readout/`.

### 9.5 M2-A: analysis (on or after `READOUT_UTC + 12 h`)
- Verifies the pins and both J2 manifest hashes; computes sections 4-8 and 10; prints the ledger line of 1 rule 1; refuses
  before its date; requires `--out`; refuses to overwrite.

## 10. Precision threshold ("coarse") and planning arithmetic

M2 is reported **coarse** (every number still printed) if any of:
1. final-state units `N_F < 1,500`;
2. the headline's event-bootstrap 95% CI half-width > **3.0c** a share;
3. non-final units (`pending + not_found + unavailable`) > **10%** of M2 units (passed E1-E9; `no_favourite` excluded and its fetch coverage printed separately);
4. window slot coverage < 75% of the 252 slots;
5. follow-up slot coverage (window end to read-out) < 75% (affects the hazard's line only; labelled there).

**Planning (assumptions, not targets; event-clustered, not independent units):**
- Units: CH269's 159 a day used a looser rule (first covered capture up to 24 h past end, category from the latest sidecar);
  M2's one-shot rule is stricter, assumed 120-159 a day, so 2,500-3,340 units in 21 days, about 1,030-1,380 events at
  CH269's 2.42 units per event. The non-final share is **not mapped**; assumed 5-15%, so `N_F` about 2,100-3,200.
- Per-unit SD of `n_i` is about SD(`Q`): 0.40 at `q` near 0.8, 0.45 near 0.7. Independent-unit SE of `theta`: 0.71-0.99c.
- Design effect `1 + (m_u - 1) rho` with `m_u` the unit-weighted mean event size (not mapped; the mean is 2.42 but sizes are
  skewed, so `m_u` plausibly 5-10) and `rho` the within-event correlation of `Q` (assumed 0.3-0.6): DE about 2.2-6.4, SE about
  1.1-2.5c, **CI half-width about 2.1-4.9c** (R1's recompute; not load-bearing). Coarse rule 2 at 3.0c is therefore **about as likely as not to fire**; disclosed
  in advance, it changes no rule. The idea's "+-2.2 points at 1,000 units" assumed independent units and is not used.
- Splits: a third of the units widens a cell's interval by about sqrt(3): S1 cells about 4-8c. **D1's half-width is about
  5.4-11.5c, wider than the idea's own "boring" premium of 2-5 points**, so D1 is expected to be uninformative about its
  sign; disclosed in advance, it changes no rule.
- Fee scale: L1 0.6-1.25c a share in the interior, the same order as the headline SE.
- Hazard: the 24 h cumulative incidence over about 2,500 units has an independent SE under 1 point; with DE 2-6, a half-width
  of about 2-5 points.
- Bound `B_U`: with zero flags it is about 4.38 / N_D times the sum over non-empty strata of their units per event, as M1's
  `T_U`; it is printed, not a coarse rule (non-payout classes are in coarse rule 3 already).

## 11. Void conditions

M2 is **void** (recorded in the ledger, its numbers not reported as a measurement) if any of:
1. any change to an estimand, weight, split, cut, contrast, cost line, class rule, threshold or the read-out date after
   `REGISTERED_UTC`;
2. any read of a resolution, label, Gamma outcome field, follow-up file or any data from after a unit's k before
   `READOUT_UTC` other than the blind write-and-hash of 9.2; named case **(a)**: J1 processed a capture out of chronological
   order, or used state holding a capture at or after k or a rule record committed after `t_d` (audited from the status
   files' sha256 chain); named case **(b)** (procedural blinding; not auditable from the data, only from the process record): a follow-up file
   opened by any process other than its writer before `READOUT_UTC`, or the J2 follow-up manifest missing at the analysis;
3. unit selection that uses information from after k (including any exclusion by a post-k class of 8.2);
4. resolution-source coverage below the floor of 8.4;
5. unit lines whose `spec_sha` or `code_sha` differs from the pins making up more than 1% of units (below that dropped,
   counted);
6. the window started before the registration commit plus 24 h;
7. the J2 unit manifest missing, or its committed hash not matching the unit and status files at the analysis (R1 SHOULD 9).

## 12. Later tests on the same object, and counting

- A later verdict test on the overdue mid, its gross difference at the mid, its hazard, or any S1-S12 cell or D1 / D2 is labelled
  **`informed (M2)`**, uses a window that starts after `READOUT_UTC` (disjoint and later), and counts none of M2's data as its
  evidence.
- If it targets a split, cell or contrast chosen after seeing M2, it reports M2's selection width: **12 splits, 69 cells, 2
  contrasts** (6).
- M2 may set planning SDs, design effects and population counts for a later design; it never sets a threshold after the fact.
- M2 is in no Holm family, is counted separately from registered tests (ledger correction entry of 2026-10-30 ~04:36Z), and
  changes no verdict.

## 13. What this measurement can and cannot say

**Can say (allowed wording):**
- "Measured (prospective, k = 0): over N units in E events, **counting only non-sports ex-crypto markets seen at their first
  2 h capture at least 2 h past `end_date`, open, accepting orders, with an empty UMA status, two-sided and with a mid in [0.05,
  0.95] at k**, the mean of (resolution payoff of the side above 0.5 at k, minus its recorded ask, minus the cost-model-v1
  conservative fee) was theta [CI]; booking `not_found` as a loss it was theta_NF [CI]; with every unresolved unit at 0 or 1
  it lay in [theta_W, theta_B]; touch, size-unlimited; capacity unavailable."
- The gross difference at the mid, the shares won, lost, split, pending and not found, and how each differs across the declared
  k-visible splits, as descriptive differences with CIs.
- How soon a proposal state appeared at a capture after k (cumulative incidence under right-censoring at the read-out), and
  how long markets took to close.
- How many ended markets closed, vanished or showed a proposal before a first overdue capture (the funnel and
  `left_before_overdue_slot`).

**Cannot say:**
- That anyone could earn this: no fill, queue, latency or size is measured; capacity is unavailable; the Gamma touch at a
  past-end market may be stale; `closed_before_t_d` units may have been untradeable.
- **Why** the mid sits where it does. D1 and D2 are descriptive differences; they identify neither inattention nor ambiguity
  (the ruling). The size cut is liquidity, not open interest; the rule class is a placeholder lexicon that cannot see
  consensus-sourced rules.
- Anything about markets that close, are proposed or vanish within 2 h of `end_date`, markets first overdue with a mid outside
  [0.05, 0.95], markets missing at k - 1, sports, crypto, or other windows.
- When the proposal happened (the field carries no time): only when a capture first showed a state.
- Anything a verdict test would say: it is not a test, has no null and no p-value, and is never pooled with or re-read as one.

## 14. Inputs read to write this draft (bounded; no host, network, `data-dumps` or evidence JSON)
`CLAUDE.md`, `AGENTS.md`; `reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`; `MEASUREMENT_M1_CH263.md` (third draft);
`reviews/M1_CHALLENGER_R1_2026-10-30.md`; `reviews/M1_RECHECK_PREFREEZE_2026-10-30.md`;
`reviews/LT14_RECHECK_PREFREEZE_2026-10-30.md`; `reviews/CH269_MAP_2026-10-30.md`; `seals/CH269_map_q0730.json` (the
`overdue_ch264` and `not_mapped` keys only); `CREATIVE_HYPOTHESES_2026-11-02.md` 0.3 (rules 24-27, facts), the counts table,
2 B (CH264), 2 F (CH269), 3 (registration notes); the ledger header and the rule-26 ruling entry; `COST_MODEL.md` section
headings and 3. Code read for field semantics only: `costs.py` (`category_key`, `taker_rate`, `taker_fee_ps`;
`sha256 258856fc…844d`), `calibration.parse_outcome`, `census_map_ch269.py` (the overdue unit, the liquidity cuts, the rule
lexicon and `read_rules`), `book_sweep.select_tokens`, `panel.eligibility_mask`, `forecast.FORECAST_END_MARGIN_H`,
`streams/common.py` (the keyless file format), `streams/gamma_rules.py` (the frame).

## 15. Open questions for the challenger (riskiest first; first draft; answered by R1, see 18.3)

1. **The blind follow-up recorder and ruling condition 5.** The hazard needs proposal states after k, and the host keeps
   captures about 8 days, so they can only be written during the window. Is a blind, write-only, hashed follow-up store read
   only at `READOUT_UTC` (9.2, void 11.2(b)) an acceptable reading of "no read of data from after k before the read-out"? If
   not, the declared fallback is to drop 7.3 before the freeze and keep only 7.4 (time to close, read-out record only).
2. **First-overdue-slot rule (E2).** M2 requires capture k - 1 to show the market not yet 2 h overdue, which drops entrants
   after a missing slot or with a row absent at k - 1 (counted). Is this the right one-shot slot, or should k be the first
   processed capture with `age >= 2 h` whatever k - 1 showed (larger population, entry age up to 4+ h)?
3. **Headline at the ask with `not_found` excluded, `theta_NF` beside.** Should `theta_NF` be the headline instead, given that
   `not_found` may be common in this population and its exclusion conditions on a post-k state?
4. **Coverage floor counting `not_found` (8.4).** Does a 0.95 floor that counts `not_found` as uncovered void a backlog-heavy
   population by construction? Alternative: floor on `unavailable (fetch)` only, with `not_found` carried by `theta_NF`, the
   band and the backlog label.
5. **Liquidity proxy with CH269's fixed cuts.** Acceptable as S1, or should the size split be dropped (the cuts come from a
   pre-window 8-day map, the window's shares will drift)?
6. **Rule-class reader.** The placeholder lexicon pinned verbatim, read at `t_d` from committed polls; acceptable, or should S2
   wait for a pinned CH239 parser (not in the repository)?
7. **Read-out at 45 days** (not M1's 31): right for an already-late population, or later still?
8. **Coarse thresholds** (1,500; 3.0c; 10%; 75%): set from planning arithmetic only; acceptable before J0?
9. **L2 for unknown categories.** `taker_rate` returns 0 for an unknown key with a served schedule of 0 (the NaN docs rate is
   dropped), so M2's L2 uses `MAX_TAKER_RATE` there. M1's text says "unknown giving 0.07" for L1 / L2; the same case may
   apply to M1 (`cat_k` unknown with a served `rate 0`): worth checking in M1's final verification.

## 16. Proposed ledger block (DRAFT; not applied)

> ## M2 (CH264) measurement design draft, 2026-10-30 (DRAFT, nothing counted)
> - `MEASUREMENT_M2_CH264.md` second draft (R1 GO_WITH_CHANGES applied, section 18) on `feat/m2-ch264`; role `prospective_measurement` (R19 rule-26 ruling; CH264 REVISE
>   items applied, section 17); k = 0; no Holm; counted apart from registered tests. Headline: unit-weighted mean of
>   `Q - ask - fee` (cost-model-v1 conservative fee) at the first overdue capture with an interior mid, event-bootstrap CI;
>   `theta_NF` and the attrition band in the same line; 12 k-visible splits on a liquidity proxy (open interest empty);
>   capacity unavailable; proposal hazard under right-censoring at read-out. Window 2026-11-24..12-14 (units disjoint from
>   M1's), read-out on or after 2027-01-29. Next: J1 extractor code and synthetic tests, then M2-J0 (J1 in dry mode, counts only).

## 17. The binding inputs, mapped

### 17.1 Ruling (R19) CH264 REVISE items
| Item | How it is met | Where |
|---|---|---|
| Moved `end_date` exclusion uses the future | removed; k-visible move is split S7; post-k move is a descriptive class | 3.6, 6, 8.2 |
| "Closed at k + 1" exclusion uses the future | removed; read-out `closedTime` classes `closed_before_t_d`, `closed_within_one_slot`; units stay | 3.6, 8.2 |
| Ambiguity vs inattention claimed as identification | D1 / D2 declared as descriptive differences with CIs; banned reading stated | 6, 13 |
| `not_found` | never at the mid; `theta` without, `theta_NF` as a loss, both in the ledger line | 4, 8.3 |
| Payoff and cost | `n = Q - ask_f - fee`; no half-spread subtracted again | 4, 5 |
| `mid = 0.5` | class `no_favourite`, never in an estimand | 3.2 E9, 8.1 |
| Hazard | cumulative incidence with competing close, right-censored at read-out | 7.3 |
| Precision | event bootstrap plus CR1 event-clustered SE; independent-unit +-2.2 points not used | 7.1, 10 |
| Zone floors | rule 25 reference lines only where the tick is 0.001 | 5.4 |
| Role conditions 1-6 | wording (1), freeze list (1 rule 2), informed labels (12), counting (12), void (11), classes (8.1) | as named |

### 17.2 Defects caught on M1 and LT14, applied here before review
| Lesson | Applied as | Where |
|---|---|---|
| Event-level tail bound per units-per-event stratum at 1 - 0.05/S; empty stratum 0; homogeneity stated | `B_U` on split / not_found | 7.2 |
| Deterministic missing-capture rule, chronological processing, state chain | adopted verbatim, plus rule-record commit times | 9.2, 11.2 |
| Fee category from `costs.category_key`, L2 with `fees_enabled=None` | S3 and both lines; plus the unknown-key case | 5, 6 |
| Degenerate CIs printed as such | stated | 7.1 |
| Structural cells and exact identities disclosed | S6 / S5, S7, S8, S12 | 6 |
| Population wording in the ledger line and in 13 | one-shot first overdue capture, two-sided, interior | 1, 13 |
| Float storage equality (LT14) | mid rounded to 6 dp before every boundary test | 3.2 E8, E9 |
| Estimand conditional on a post-k state (LT14's null) | conditioning paragraph; `theta_NF`, band, coarse rule 3 | 4, 10 |
| Sweep coverage depends on price | capacity declared unavailable (no sweep row by construction) | 5.3 |
| J0 effects limited and named | (a) and (e) only; (b) redundant | status, 9.1 |

## 18. R1 response (2026-10-30; `reviews/M2_CHALLENGER_R1_2026-10-30.md`, GO_WITH_CHANGES on `c075355b…0ca4`)

No window, registration, read-out date, threshold, estimand, weight or cost line was loosened. The cell count rises from 64
to 69 (S2 gains `rules_unresolved`); no cell was dropped.

### 18.1 MUST
| Item | Fix | Where |
|---|---|---|
| 1 S11 / S6 boundaries fail by floating-point maths | `spread_k = round(ask - bid, 6)`, NO-side prices and `mid_f` rounded to 6 dp; every boundary tested on rounded values; synthetic test (vii) | 3.3, 6, 9.2 |
| 2 E6 a token blacklist | whitelist of CH269's empty forms (`""`, `"[]"`, `"nan"`, `"none"`); other non-empty forms `uma_other_at_k`; follow-up P on whole tokens (`proposed`, `disputed`, `resolved`), others `uma_other_followup`; test (viii) | 3.2 E6, 7.3, 9.2 |
| 3 Coverage floor contradicts the backlog label | covered = a definite answer (a record, or absence established in both passes plus a single-id re-query with HTTP 200); floor 0.95 on units and events against `unavailable (fetch)` only; event coverage defined; `not_found` an outcome class | 8.1, 8.4, 9.4 |
| 4 `theta_open` re-introduces a post-k exclusion | removed; 8.2 prints class count and mean `n_i` only | 4, 8.2 |
| 5 Look-back depends on retention | fixed span `[REGISTERED_UTC - 7 d, REGISTERED_UTC)`, 84 slots; `missing_lookback_slot` counted | 2, 3.2 |

### 18.2 SHOULD
| Item | Fix | Where |
|---|---|---|
| 1 S4 and S3 `unknown` undefined | S4 by `population_map_ch251.fee_class` with its three cells defined; S3 `unknown` = any key outside the nine | 6 |
| 2 Likely empty cells | `scheduled` 14 / 1,347, high x `no_rules` 0, S1 confounded with rule coverage (154 of 180): disclosed | 6 |
| 3 Identity checked by `==` | within 1e-9 | 4 |
| 4 7.4 classes | `not_found` and `unavailable` excluded and counted | 7.4 |
| 5 7.2 unit basis | final-state plus `not_found` units (`N_D`, `E_D`); lower-limit wording as M1's corrected text | 7.2, 10 |
| 6 Stale touch | disclosed (unmeasured) | 3.3, 13 |
| 7 "gross premium" | renamed "gross difference at the mid" | 0, 4, 12, 13 |
| 8 `hash` record without its row | `rules_unresolved`, its own S2 cell | 3.5, 6 |
| 9 Void list | J2 unit manifest missing or not matching | 11 |

### 18.3 Designer's questions, as answered by R1
1. Blind write-only follow-up accepted under condition 5; named **procedural blinding**; void 11.2(b) stated as not auditable
from the data; J1 status files and monitoring print no P / C counts, only follow-up file hashes and line counts (9.2, 11).
2. E2 kept. 3. `theta` stays the headline; `theta_NF` and the band mandatory in the same line (1 rule 1). 4. MUST 3 (8.4).
5. Liquidity proxy with fixed cuts and label kept (6). 6. Placeholder lexicon kept, pinned (3.5). 7. 45 days kept (2).
8. Coarse thresholds kept (10). 9. L1 now states "unknown key: served rate, possibly 0"; L2 keeps `MAX_TAKER_RATE` for
unknown keys (5). The same defect in M1's text is recorded for M1's final verification (the ledger note of 26af0e38); M1's
file is not edited here.

### 18.4 Feasibility (R1)
J0 is J1 in dry mode with the J1 code at the commit recorded in J0's seal (9.1). J0 rule (b) is redundant (75 x 21 = 1,575 > 1,500) and kept only as a
record. J1 runs on the host until 2027-01-29 (about 790 captures) beside M1's J1, light, never beside a multi-GB job.

## 19. R1 re-check response (2026-10-30; `reviews/M2_R1_RECHECK_2026-10-30.md`, NOT_READY on two wording defects)

No window, read-out, deadline, threshold, estimand, weight, seed, cut, cost line or cell was changed. SHOULD 10 only aligns
two planning figures that are not load-bearing.

| Item | What changed | Where |
|---|---|---|
| MUST 1 J0 order | the order now has the J1 code (tests i-viii) before J0, J0 = that code in dry mode with its `code_sha` in J0's seal, the remaining code and a code-freeze check listing J1 changes since that `code_sha` after the freeze; "the same pinned code" replaced by "the J1 code at the commit recorded in J0's seal" | status block, 9.1, 18.4 |
| MUST 2 imported readers | sha256 of the six imported modules is a spec pin recorded in J0's seal and at registration; a difference is void 11.1; `live_tests8_base.py` added (its `crypto_class` is what `category_of` calls); not pinned as files by an earlier spec | 5 |
| SHOULD 1 `fees_enabled` for L1 | passed False / True / None as served-and-not-truthy / truthy / missing; `rate_zero` fee-free units still carry the docs rate | 5 |
| SHOULD 2 denominators | "M2 units (passed E1-E9; `no_favourite` excluded and its fetch coverage printed separately)" | 8.4, 10 |
| SHOULD 3 split-cell bootstrap | same event draws restricted to the cell's units; draws without a final-state unit counted and left out; day-block split of events disclosed | 7.1 |
| SHOULD 4 look-back fold | first-pass fold after the registration commit; absent or retention-removed slot is `missing_lookback_slot`; slot count printed, markets overdue only in a missing slot cannot be counted | 2, 9.2 |
| SHOULD 5 S3 `unknown` | "structurally excludes empty" (verified: `crypto_class` gives `unknown` for an empty `fee_category`, `live_tests11_base.py:718-727`, same in `live_tests8_base.py`) | 6 |
| SHOULD 6 funnel | `reoverdue_seen` counted | 3.2 |
| SHOULD 7 `not_found` | re-query with and without `closed=true`; two HTTP 200 empties needed | 8.1, 9.4 |
| SHOULD 8 YES / NO | YES = outcome 0, NO = outcome 1 | 6, 8.1 |
| SHOULD 9 J0 status forms | no J0 output changes the E6 whitelist or P tokens; unforeseen forms stay `uma_other_*` | 9.1 |
| SHOULD 10 planning figures | SE 0.71-0.99c; half-width 2.1-4.9c (SE range 1.1-2.5c to match) | 10 |
