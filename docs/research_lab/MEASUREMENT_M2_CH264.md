# Measurement M2 (CH264, "the overdue mid"): the favoured side's realised payoff against its ask in markets first seen 2 h past their `end_date` with an interior mid, held to resolution, k = 0 (DRAFT)

**Status: DRAFT 2026-10-30, second draft plus re-check fixes (challenger R1, `reviews/M2_CHALLENGER_R1_2026-10-30.md`,
GO_WITH_CHANGES on `c075355b…0ca4`, mapped in section 18; re-check `reviews/M2_R1_RECHECK_2026-10-30.md`, NOT_READY on
two wording defects, MUST 1-2 and SHOULD 1-10 applied, mapped in section 19, plus the J1 ambiguity rulings, section 20; **M2-J0 ran (q0733b, 2026-10-30, on the ruled code `m2_j1.py` `c0538322…51dc`; seal
`docs/research_lab/seals/M2_J0_q0733b.json`, sha256 `31e3380c…1564`, `informed (M2-J0)`, counts only): rule (a) did not fire
(median full-day units 138 >= 75), rule (b) record-only line not met (projected 2,898 >= 1,500), rule (e) does not apply
(every committed poll line carries a parseable `finished_utc`; the per-record receipt-time reader stands), so the 21-day
window and the dates are unchanged (outcome in section 21); the final pre-freeze verification ran (`reviews/M2_FINAL_VERIFY_2026-10-30.md`, NOT_READY, text fixes MUST 1-4, disclosures D1-D6 and SHOULD 1/4/5/8 applied, mapped in section 22); next: a diff check that only those lines moved, then the freeze commit by 2026-11-16. Not frozen, not registered, nothing counted.** Evidence role
`prospective_measurement` (rule 26 of `CREATIVE_HYPOTHESES_2026-11-02.md` 0.3; role and conditions set by the binding
ruling `reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`, ACCEPT_WITH_CONDITIONS for the role, **REVISE** for CH264;
every REVISE item is mapped in section 17). Drafted on branch `feat/m2-ch264` from the `chore/arepo-claude-setup` tip
`8eb0ad9f`, a design-only commit. Since then the J1 code (`m2_j1.py`), the J0 runner, job q0733b and its seal exist (sections 20-21). The only host read is J0's counts-only read. Structure and every defect class caught
on M1 (`MEASUREMENT_M1_CH263.md`, its challenger R1 and its pre-freeze re-check) and on LT14's pre-freeze re-check are
carried over (section 17.2). Before anything is sealed this needs, in order: a challenger review (`science-reviewer`) of this
text (R1 done), the designer's response (section 18), a re-check, the J1 extractor code for 3.2, 3.3 and 3.5 written and
unit-tested on synthetic data (tests i-viii), **M2-J0 = that code in dry mode, its `code_sha` recorded in J0's seal**, a final
pre-freeze verification, the design-text freeze commit (sha256 in the ledger), the remaining code (J2, J3, A), a code-freeze
check that lists every change to the J1 code since J0's `code_sha` with its diff and reason (the list includes: `run_available` must be changed to judge missing slots by `finished_utc`, section 22), a host dry run with peak RSS,
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
  overwrite, and keeps only unit lines whose `spec_sha` (the sha256 of this file at the registration commit; the file is never edited after that, and outcomes go to the ledger) and `code_sha` equal the pins and whose role is
  `prospective_measurement`.
- **Overlaps (time only, no shared object).** M1 (same window), LT11 (11-18..12-09), E026 (to 12-07), LT12 (from 12-10) share
  captures with M2. M2 reads raw rows, sidecars and `gamma_rules` day files and computes none of their objects; E026's
  modules and stores are not read. The engine's eligibility requires `end_date` after the origin, so M2's units (past
  `end_date`) are disjoint from every engine row by construction.
- **Disclosure (final verification MUST 2).** M1's read-out (2027-01-15) publishes resolutions of `m1_overlap` markets before M2's read-out. M2's text, code and pins are fixed at registration, so this cannot change M2.
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
  `missing_capture` or `late_capture_ignored`). Else `no_previous_capture`. Every candidate at an in-window capture that is not classified is counted: `no_previous_capture` (k - 1 missing, not folded, or gone on resume) or `k_minus_1_before_window` (the first window capture).
- **E2 First overdue slot.** The market has a row at k - 1 (else `no_k_minus_1_row`; `end_date_{k-1}` unparseable: `k_minus_1_end_date_missing`, first overdue status cannot be checked, never a unit) whose own `age_{k-1} = start_{k-1} -
  end_date_{k-1} < 2 h` (else `already_overdue_at_k_minus_1`: a guard class, expected 0 because a folded k - 1 puts every
  market with `age >= 2 h` into the set; a non-zero count is printed and audited). `end_date` missing at k: `end_date_missing` (not a candidate; counted per capture as row-captures (every row of k with an unparseable `end_date` whose k sidecar row maps to scope, open or not), with distinct markets printed beside; never a unit).
- **E3 One-shot.** No earlier M2 unit for the market (else `prior_unit`; a market whose `end_date` is extended and later
  passes again is never a new unit). A guard class like E2, expected 0 (a unit's market entered the overdue-seen set at its own k); a non-zero count is printed and audited.
- **E4a Open by row at k:** `binary = 1`, `closed` false, `active` true; else `not_open_at_k`. **E4b Sidecar:** capture k's sidecar row exists; else `sidecar_missing`. **E4c** `accepting_orders` true; false is `not_open_at_k`; missing or unparseable is `accepting_unknown`.
- **E5 Scope:** the category of capture k's own sidecar row, by the CH269 map's reader
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

**Survivorship class (k-visible, counted, never a unit).** `left_before_overdue_slot`: scope markets (k - 1's own sidecar row) open by row flags at k - 1, with `age_{k-1} < 2 h` and `end_date_{k-1} <= start_k - 2 h`, that are absent from k's rows or `closed` at k. Printed per UTC day beside
the funnel so a reader sees how many ended markets close or vanish before a first overdue capture.

**Disclosure (final verification D6).** `left_before_overdue_slot` (1,123 in J0) is about the size of the unit count (1,024). Twenty scope markets have an unparseable `end_date` and can never become units.

### 3.3 Unit fields and decision time
- **Price on the favoured side** (rows' touch at k): YES: `ask_f = ask`, `bid_f = bid`, `mid_f = mid_k`; NO:
  `ask_f = round(1 - bid, 6)`, `bid_f = round(1 - ask, 6)`, `mid_f = round(1 - mid_k, 6)`. Spread
  `spread_k = round(ask - bid, 6)`, half-spread `h = spread_k / 2`, so `ask_f = mid_f + h` (to floating-point error).
  **Every split boundary (S6, S11) and every boundary test is applied to these rounded values** (R1 MUST 1: unrounded
  `ask - bid <= 0.01` fails on 80 of 99 one-tick spreads at tick 0.01). Tick at k recorded.
- **The touch may be stale (disclosed, unmeasured; R1 SHOULD 6).** Gamma's best bid / ask on a past-end market may lag the
  book; no book is read (5.3), so the staleness of `ask_f` at `t_d` is not measured.
- **Decision time** `t_d` = the later of the row's `received_utc` and the sidecar row's `received_utc` (no sweep exists for
  these markets). If neither `received_utc` parses, `t_d` = capture k's manifest start (`t_d_source = capture_start_fallback`, counted). If one parses, it is used alone. The gap (sidecar minus row) is recorded. The rule-class input must be committed at or before `t_d` (3.5).
- **Unit record.** Everything above plus `event_id`, the event's open binary member count at k, `end_date_k`,
  `end_date_{k-1}` (the k-visible move flag of S7), `age_k`, `liquidity` at k, `open_interest` presence, category, `cat_k`,
  fee fields and the two fee lines of 5, the rule class and its commit time, the raw status strings at k and k - 1, capture
  ids, `spec_sha`, `code_sha`. **Nothing from after capture k.**

### 3.4 Cluster
The cluster is the Gamma `event_id` at k. No cap: weights are declared instead (4). A unit whose `event_id` is empty is its own cluster (keyed `market:<market_id>`) and its own one-market event for S8 and 7.2.

### 3.5 Rule class at `t_d` (the S2 reader; pinned)
- **Lexicon.** CH269's placeholder lexicon, copied verbatim into M2's own module (CH269's module is not frozen and may change):
  `classify_rule(question + description + resolutionSource)` with CH269's `SCHEDULED_RE` and `BARRIER_RE`, giving
  `scheduled`, `barrier`, `both` or `other`; no record for the market at or before `t_d`: `no_rules`; a `hash` record whose
  full row is no longer in a retained day file: `rules_unresolved` (its own cell, never `no_rules`; R1 SHOULD 8). The sha256 of the two pattern strings is a spec pin. It is a
  placeholder reading, **not** CH239's parser, and it does not detect consensus-sourced rules (disclosed; the idea's
  "consensus-sourced" cut is not available).
- **k-visible reader (declared now; the CH269 map's "last row wins" read rows after k and is not used).** The market's
  class is computed from its last `row` (or `hash` resolved to its full row) in a committed poll whose `poll` line was
  written at or before `t_d`, across retained day files. A record's receipt time is the `finished_utc` of the committing `ok` poll line. A record with a parseable `finished_utc` is visible iff it is <= `t_d`. A record without one is visible only if its day file's UTC day is strictly before k's UTC day. Rule (e) is the case where no committed line parses. Day files are keyed by poll start (`streams/common.py:366`), so J0 prints the number of commits that cross midnight and the maximum poll duration (disclosed). A `hash` record resolves to the class of any committed `row` with an equal sha in a retained file or the ledger (equal sha means equal text). `gone` records do not change the class. No row after `t_d` is read.
- **Coverage is selected (disclosed).** The `gamma_rules` frame holds open markets with `volume24hr > 0` (top 3,000 hourly,
  the full frame four times a day), so `no_rules` collects the quietest markets; CH269 counted 180 `no_rules` of 1,347 units
  (13%) under its looser reader. `no_rules` is a reported cell, never filled.
- **Disclosure (final verification D5).** J0 found `no_rules` 222 (21.7%), against 13% in CH269. 82 of these units have rule text that was only polled after `t_d`, and 185 are in S1 low. With 7 `scheduled` units in J0's six full days, D2's `scheduled` arm will almost certainly be `thin`.

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
  (`boundary_map_ch240.py`, `cb17_census.py`, `cb13_label.py`, `live_tests8_base.py`, `population_map_ch251.py`, `calibration.py`,
  `costs.py`; these are the import graph of E5, S4, the fee lines and the outcome parser: `category_of` calls `cb17_census.is_sports_sidecar`, which reads `cb13_label.first_series_slug`, `SPORTS_CATEGORIES` and `SPORTS_SERIES_RE`, and `live_tests8_base.crypto_class`) plus `live_tests11_base.py`, which is pinned because the S3 note cites its copy (l. 718-727) and is not imported. Eight files. Each is a spec pin, recorded in J0's seal and at registration. A difference at the analysis is void 11.1. Fact
  checked at this re-check: none of these files is pinned as a file by an earlier spec (LT11 pins only the source hashes of
  its vendored pieces by a provenance test; CB17 pins a bundle hash covering `cb17_census`), so the pins are new. 
  Liquidity rewards, holding rewards and rebates are not in any line (disclosed).
- **Disclosure (final verification D2).** 966 of 1,024 J0 units are `other:zero_fees` -> `cat_k` other (docs rate 0.05). L2 charges that rate on markets the venue labels zero-fee. L1 charges it too unless `fees_enabled` is served false, and J0 did not print the L1 rate distribution. The statement above that the fee is comparable to the CI holds for L2 and possibly not for L1. S3 fills 3 of its 10 cells, and S4 `fee_on` has 3 units.

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
| S10 | window week | days 1-7, 8-14, 15-21 (and 22-28, 29-35, 36-42 under 9.1 (a)) |
| S11 | spread at k (`spread_k`, rounded, 3.3) | <= 0.01, (0.01, 0.03], (0.03, 0.10], > 0.10 |
| S12 | S1 x S2 (the idea's size x class grid) | 4 x 6 = 24 cells |

**J0 observed distribution (informed (M2-J0), counts only; q0733b, 1,024 eligible units, 6 full days; cells unchanged, a cell J0 did not print is not listed):**
- S1: low 338, mid 320, high 366 (`na` not printed). S2: barrier 623, both 161, no_rules 222, other 11, scheduled 7 (`rules_unresolved` not printed).
- S3: other 966, unknown 55, politics 3 (raw `fee_category` to `cat_k`: `other:zero_fees` -> other 966, `unknown` -> unknown 55, `politics` -> politics 3; the other seven keys not printed).
- S4: fee_free 1,021, fee_on 3 (`unknown` not printed). S5: NO 674, YES 350.
- S6 (k-time zone counts): (0.5,0.6] 349, (0.6,0.7] 160, (0.7,0.8] 155, (0.8,0.9] 175, (0.9,0.95] 185.
- S7: no 1,024 (`yes` not printed). S8: 1 = 9, 2-5 = 100, 6+ = 915. S9: 0.001 = 187, 0.01 = 837 (`other / missing` not printed).
- S10: days 1-7 = 1,024 (J0 is a dry run; no week structure). S11 (k-time zone counts): <= 0.01 38, (0.01,0.03] 138, (0.03,0.10] 282, > 0.10 566.
- S12 (printed cells): low|no_rules 185, high|barrier 288, mid|barrier 198, low|barrier 137, high|both 78, mid|both 74, mid|no_rules 37, low|both 9, mid|other 7, mid|scheduled 4, low|other 4, low|scheduled 3 (12 of 24 cells printed; high|no_rules, high|other and high|scheduled are not printed; the `rules_unresolved` and `na` cells are not printed either).
- `no_favourite` 24 (mid exactly 0.5; a funnel class, not a unit).
- **Disclosure (final verification D1, wide books).** J0 found S11 > 0.10 for 566 of 1,024 units, S6 (0.5, 0.6] for 349, and `no_favourite` 24. Many units may be near-empty books with `ask_f` close to 1. Expect `theta` near `pi - mean h` with mean `h` of several cents, which exceeds the planned CI half-width. E7 and E8 are kept as declared: changing them after seeing J0's zone counts would be post hoc.
- **Disclosure (final verification D5, pointer).** See 3.5: `scheduled` is 7 units in J0, so D2's `scheduled` arm is expected `thin`.

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
**12 splits, 69 cells (72 under 9.1 (a))** (S1 4, S2 6, S3 10, S4 3, S5 2, S6 5, S7 2, S8 3, S9 3, S10 3, S11 4, S12 24) **plus 2 contrasts**.

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
- **Disclosure (final verification D4).** In J0 no event has 10 or more units (the largest bucket is 4-9 units, 61 events), so the planning value `m_u` of 5-10 in 10 is probably too high. For S8, 915 units are in 6+, so cells "1" (9) and "2-5" will be thin.

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
  status string (distinct normalised forms, counts; every non-whitelist form seen at E6, uncapped, with counts); the planned follow-up volume (units x captures to the read-out).
- **Decision rules declared now:** (a) eligible units fewer than 75 a day (median full day): window extended to 42 days,
  dates rewritten before the freeze; (b) *redundant, kept as a record only* (fewer than 1,500 projected over 21 days; since 75 x 21 = 1,575 > 1,500, rule (a)
  always fires first; R1);
  (c) the size split stays the liquidity proxy with CH269's cuts whatever J0 prints; (d) none of J0's numbers changes an
  estimand, split, cut, cost line or threshold; (e) the receipt-time reading of 3.5 (computed, never a manual mode; records with no parseable `finished_utc` use the day-before rule). No J0 output can change the E6 whitelist or the whole-token P tokens: unforeseen status forms stay `uma_other_at_k` / `uma_other_followup`. Output labelled `informed (M2-J0)`, counts only, sealed with its code hash. J0 folds 12 captures, then uses one more capture as k - 1 only; this is fixed now. A short fold can only add candidates, because the current overdue stock enters the seen set at the first fold capture and only re-overdue markets leak. J0's look-back is not changed after its output is seen.
- **Disclosure (final verification D3).** In J0, `reoverdue_seen` (1,012) is about the size of the unit count (1,024). The 12-capture fold overstates units by an unknown amount. Rule (a) still holds unless the true median is at least 46% below J0's (lowest full day 114 against 75). `end_date_changed_after_k` may not be rare.
- Memory: under 600 MB (CH269's 8-day map peaked at 558.8 MB over a wider read); dry run measured.

### 9.2 M2-J1: window-time extractor and blind follow-up recorder (every pass; catch-up within retention)
- **Extractor.** For each complete capture k in the window not yet processed: read captures k - 1 and k (rows and sidecar,
  `usecols` only) and the committed `gamma_rules` records up to `t_d`; apply 3.2; write `units/<capture_id>.jsonl.gz` and
  `status/<capture_id>.json` (the funnel counts, completeness; **no P or C count and nothing derived from follow-up
  content**: for follow-up files only their sha256 and line count, R1 Q1; monitoring prints the same and no more). Idempotent per capture; refuses to overwrite; every line
  carries `spec_sha`, `code_sha`, role `prospective_measurement`. State file between runs: the overdue-seen set, the M2 unit
  ids, and an append-only rule ledger: per market, every committed record's receipt time, day file, kind and class, plus the sha-to-class map. It is merged from retained day files at each pass and never pruned, so retiring a day file never changes a later unit's class.
- **Look-back fold timing (re-check SHOULD 4).** J1's first pass, after the registration commit and before the first window
  capture is processed, folds the look-back span in order. A slot whose capture is absent, or already removed by retention at
  that pass, is `missing_lookback_slot`. A k is classified only if `start_k` is in [`REGISTERED_UTC`, `END_UTC`) and `start_{k-1} >= REGISTERED_UTC`. Captures at or after `END_UTC` serve follow-up only and are not folded.
- **Strictly chronological (M1's re-check fix 3, adopted verbatim).** Captures are processed in increasing manifest start,
  one at a time, and a capture is processed only when every earlier slot is processed or recorded `missing_capture`;
  catch-up replays the backlog in the same order. A slot is recorded `missing_capture` once it has no complete capture 6 h
  after its grid time, judged by the manifest's completion time (`finished_utc` <= grid + 6 h), never by when J1 runs; a capture appearing later stays unprocessed (`late_capture_ignored`). The run refuses unless the state
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
  holding a capture at or after k makes the run refuse; (iii) a 12-capture catch-up gives identical unit files; (iv) running with the recorder off, or deleting every follow-up file, leaves every unit file and the state file byte-identical, and every status file identical except its `followup` field; (v) a `gamma_rules` record committed after `t_d`
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
- **Disclosure (final verification D4).** J0 shows no event with 10 or more units, so `m_u` of 5-10 above is probably too high; see 7.2. It changes no rule.
- Splits: a third of the units widens a cell's interval by about sqrt(3): S1 cells about 4-8c. **D1's half-width is about
  5.4-11.5c, wider than the idea's own "boring" premium of 2-5 points**, so D1 is expected to be uninformative about its
  sign; disclosed in advance, it changes no rule.
- **Disclosure (final verification D1).** J0's wide books (S11 > 0.10 for 566 of 1,024 units) may put mean `h` at several cents; see 6. It changes no rule.
- Fee scale: L1 0.6-1.25c a share in the interior, the same order as the headline SE.
- Hazard: the 24 h cumulative incidence over about 2,500 units has an independent SE under 1 point; with DE 2-6, a half-width
  of about 2-5 points.
- Bound `B_U`: with zero flags it is about 4.38 / N_D times the sum over non-empty strata of their units per event, as M1's
  `T_U`; it is printed, not a coarse rule (non-payout classes are in coarse rule 3 already).

## 11. Void conditions

M2 is **void** (recorded in the ledger, its numbers not reported as a measurement) if any of:
1. any change to an estimand, weight, split, cut, contrast, cost line, class rule, threshold or the read-out date after
   `REGISTERED_UTC`;
2. any read, by an M2 job or for M2's purposes, of a resolution, label, Gamma outcome field, follow-up file or any data from after a unit's k before
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
>   M1's), read-out on or after 2027-01-29. Next: M2-J0 (q0733b) on the J1 code with the ambiguity rulings (section 20), counts only.

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
| MUST 2 imported readers | sha256 of the eight imported or cited files is a spec pin recorded in J0's seal and at registration; a difference is void 11.1; `live_tests8_base.py` added (its `crypto_class` is what `category_of` calls), then `cb13_label.py` and `live_tests11_base.py` (section 20); not pinned as files by an earlier spec | 5 |
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

## 20. J1 code ambiguity rulings response (2026-10-30; `reviews/M2_J1_AMBIGUITY_RULINGS_2026-10-30.md`, REVISE; code in `reviews/M2_J1_CODE_NOTE_2026-10-30.md`)

No window, read-out, deadline, threshold, estimand, weight, seed, cut or cost line was changed. Rulings 1-15 and defects N1-N5 were declared before any J0 output exists. The earlier q0733 stopped before any output on pre-ruling code and is superseded by q0733b.

| Ruling | Where applied in the text | Code |
|---|---|---|
| 1, 2 pins (W1) | 5 (eight files), 19 | `PIN_MODULES` |
| 3 E4a / E4b / E4c order (W2) | 3.2 | none |
| 4 E3 guard class (W3) | 3.2 | none |
| 5 survivorship definition (W4) | 3.2 | none |
| 6 E2 row-captures (W5) | 3.2 | distinct scope markets printed |
| 7 receipt time (W6) | 3.5, 9.1 (e) | per-record `finished_utc`, no mode switch, midnight and poll-duration prints |
| 8 `t_d` fallback (W7) | 3.3 | `t_d_source` counts |
| 9 k bounds (W8) | 9.2 | none |
| 10 12-slot look-back (W9) | 9.1 | none |
| 11 test (iv) (W10) | 9.2 | test reworded |
| 12 rule ledger (W11) | 9.2 | ledger in the state file |
| 13 S10 cells (W12) | 6 | none |
| 14 `hash` resolution (W13) | 3.5 | none |
| 15 non-whitelist E6 forms (W14) | 9.1 | uncapped |
| N1 (W15) | 3.2 E1 | `no_previous_capture`, `k_minus_1_before_window` per candidate |
| N2 (W16) | 3.2 E2 | `k_minus_1_end_date_missing` |
| N3 | none | per-capture funnel in J1 status |
| N4 | none | look-back counting from `slot_of(window_start - 84*GRID_S)` |
| N5 | 9.1 (e) | `--rules-mode` removed from the runner |

## 21. M2-J0 outcome (q0733b)

Facts only; counts only, `informed (M2-J0)`, k = 0, uncounted. Job q0733b finished 2026-10-30T07:30:48Z (646 s), dry run, version `m2-j1-v1`, on the ruled code: `m2_j1.py` `c0538322be740a2fc80654d93160415777b4f445fcf6737c18339dca3a7c51dc`, `run_m2_j0.py` `c0e4d061ddba75212565cf29142c20ee7870f94f1f6b4b4698994ce28d85793d`. Seal `docs/research_lab/seals/M2_J0_q0733b.json`, sha256 `31e3380c43b35dbeb0820166824b3af4a8ef64015f7d123604761dc5e3ec1564`; spec sha256 `690d7da5e70bba8cf49baf13e4f73764fd90a9ba6c67021f3549936061dd61e3`. Peak RSS 457.7 MB (limit 600 MB).

- **Span.** `last_days=8`, 2026-10-22T06:31:03Z to 2026-10-30T06:31:03Z; first window-start capture 2026-10-23T08:31:05Z. 83 classified captures; fold of 12 captures (fixed by W9) against the registered 84-slot look-back; 6 full days (10-24 to 10-29); no missing slot, `missing_capture` 0, `missing_lookback_slot` 0, `late_capture_ignored` 0, `pre_window_source` 12. Captures: first read 2026-10-22T08:31:02Z; fold 10-22T08:31 to 10-23T06:31; k - 1 only 10-23T08:31; classified 10-23T10:31 to 10-30T06:31. 10-23 is a partial day (7 classified captures), as 10-30 is. J0's note: `reoverdue_seen` is understated and units slightly overstated at the start because the fold is short.
- **Eligible units.** 1,024 in total, per day 10-23 123, 10-24 114, 10-25 152, 10-26 162, 10-27 123, 10-28 220, 10-29 124, 10-30 6 (partial day). Full-day median 138. 447 events; units per event (every unit counted as if final): 1 -> 141 events, 2-3 -> 245, 4-9 -> 61, 10+ -> none printed.
- **Funnel (row-captures and candidates, 83 captures).** `unit` 1,024; `out_of_scope_sports` 202,302; `not_two_sided` 5,600; `mid_low` 858; `mid_high` 357; `uma_state_at_k` 528; `out_of_scope_crypto` 31; `no_k_minus_1_row` 30; `no_favourite` 24. Zero: `not_open_at_k`, `sidecar_missing`, `accepting_unknown`, `uma_other_at_k`, `out_of_scope_unknown`, `no_previous_capture`, `k_minus_1_before_window`, `k_minus_1_end_date_missing`. Guard classes: `already_overdue_at_k_minus_1` 0, `prior_unit` 0 (E3), both as expected. Per-day funnel is in the seal (`funnel_by_day`).
- **Side classes.** `left_before_overdue_slot` 1,123 (per day 10-23 359, 10-24 134, 10-25 60, 10-26 221, 10-27 180, 10-28 81, 10-29 70, 10-30 18); `reoverdue_seen` 1,012 (counted over every category, whereas `end_date_missing` counts scope markets only; a market in the seen set with no row at k - 1 that is overdue at k falls in no class of the funnel, so the funnel has a gap of unknown size, disclosed here in words; it is to be recorded as the class `seen_without_k_minus_1_row`, a recorded class only, which changes no unit); `end_date_missing` 1,587 row-captures (per day 10-23 140, 10-24 240, 10-25 240, 10-26 240, 10-27 223, 10-28 216, 10-29 216, 10-30 72) over 20 distinct markets.
- **Rules.** (a) median full-day units 138 against 75: not fired. (b) projected 21-day units 2,898 against 1,500: not met (record only). (e) `rule_e_day_before_reader_applies` false: all 222 committed `ok` poll lines carry a parseable `finished_utc` (`records_without_receipt` 0), so the per-record receipt-time reader of 3.5 stands. Window, `REGISTERED_UTC`, `END_UTC` unchanged.
- **`t_d` source.** `receipt` 1,024 of 1,024 units.
- **Rule-class coverage at `t_d` (k-visible reader | CH269 last-row reader).** barrier|barrier 623, both|both 161, no_rules|no_rules 140, no_rules|barrier 74, no_rules|both 8, other|other 11, scheduled|scheduled 7. Rules stream: 11 day files (20261020.jsonl to 20261030.jsonl), 222 poll lines (all ok), 109,264 rows committed, 183,901 `hash` records committed, 107,798 markets, 0 torn or failed rows, 0 commits crossing midnight, maximum poll duration 237.9 s.
- **Status forms.** 37 distinct normalised forms over the 8 days (the largest are the empty `[]`, 21,622,698 rows, then `["proposed","proposed"]`, 222,694); `forms_overflow_rows` 0. Non-whitelist forms seen at E6: 3, all containing `propos`, so all fall in `uma_state_at_k` (528 rows) and none in `uma_other_at_k` (0): `["proposed","proposed"]` 526; two long proposed/disputed sequences 1 each (the seal files them under `uma_other_at_k_forms`). No change to the E6 whitelist or the P tokens.
- **Receipt gaps.** Sidecar minus row receipt time: n = 1,024, min = median = max = 0.0 s.
- **Planned follow-up volume.** 666 unit-capture lines per unit at the window midpoint; 1,930,068 projected lines over 21 days (counts only).
- **Open interest.** Present on 0 of 1,024 units (`units_with_nonempty_value` 0); the liquidity proxy of 6 stands.
- **Pins recorded (`imported_module_sha256`).** `boundary_map_ch240.py` `2bc9ff9edb97b76990579c90929e55f22cb4cfe9fdec852395bd07f7d3bea09a`; `calibration.py` `567cdbe9eab0a8fa5fccdf4350e44cb2fea0104d445e62188e3e363fba12dda1`; `cb13_label.py` `2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380`; `cb17_census.py` `6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a`; `costs.py` `258856fc360fbe70ce7a062a3f156b66d9d71fd50de56bf3669935c4227f844d`; `live_tests11_base.py` `7f4d3db50311088bb6fbd1ee1eafb7f142fb58133ea1d7f6c684694eb75a9a68`; `live_tests8_base.py` `4b26756d4d1934c4da9a0b2b26d4ff3f2ac72f199bbc55d4ae6365b8ebc394e0`; `population_map_ch251.py` `82db7a75995f0b637b469f4abc421ad9be430fdf38f0a4bad7ed5e9e43a55140`; rule lexicon `2209e0adc51fd0e48edd231574d37207a80b8f3ab34bca418cd910b7abe4b97e`.

No estimand, split, cell, threshold, cost line or date changed from J0.

## 22. Final verification mapping (2026-10-30; `reviews/M2_FINAL_VERIFY_2026-10-30.md`, NOT_READY -> text fixes applied here)

No estimand, weight, cell, cut, threshold, cost line, date, seed or window was changed. Lines refer to the text after this edit.

| Item | What landed | Where |
|---|---|---|
| MUST 1 empty `event_id` | own cluster `market:<market_id>`, own one-market event for S8 and 7.2 | 3.4 (l.186) |
| MUST 2 void 11.2 scope | "any read, by an M2 job or for M2's purposes, ..."; disclosure of M1's earlier read-out | 11.2 (l.541), 2 (l.112) |
| MUST 3 status block | J1 code, J0 runner, q0733b and seal exist; only host read is J0's counts-only read | status block (l.12-14) |
| MUST 4 missing-capture clock | "judged by the manifest's completion time (`finished_utc` <= grid + 6 h), never by when J1 runs"; code-freeze item: `run_available` judges missing slots by `finished_utc` | 9.2 (l.470), status block (l.19) |
| D1 wide books | disclosure | 6 (l.327), 10 (l.529) |
| D2 fees | disclosure | 5 (l.266) |
| D3 short fold | disclosure | 9.1 (l.454) |
| D4 clusters | disclosure | 7.2 (l.366), 10 (l.525) |
| D5 rules | disclosure | 3.5 (l.201), 6 (l.328) |
| D6 survivorship | disclosure | 3.2 (l.168) |
| SHOULD 1 `reoverdue_seen` | counts every category; gap named `seen_without_k_minus_1_row` (record only, no effect on units) | 21 (l.758) |
| SHOULD 2 rule-ledger lookup | code-freeze item: sort by commit time, not list position | code-freeze list (l.19), this table |
| SHOULD 3 600 MB cap | code-freeze item: the host dry run uses a ledger of end-of-window size | code-freeze list (l.19), this table |
| SHOULD 4 `spec_sha` | sha256 of this file at the registration commit; never edited after; outcomes to the ledger | 2 (l.106) |
| SHOULD 5 section 21 span | captures named; 10-23 marked a partial day | 21 (l.755) |
| SHOULD 6 missing-slot status files | code-freeze item: missing-slot state writes leave no status file, so the sha chain has gaps | code-freeze list (l.19), this table |
| SHOULD 7 section 16 ledger block | stale; refreshed at registration | at registration (l.792) |
| SHOULD 8 S12 not-printed list | `rules_unresolved` and `na` cells added | 6 (l.325) |
