# Measurement M3 (CH274, "the wait"): hours from a market's first two-sided capture with the favoured ask at 0.95 or more to the first capture that shows a UMA proposal state or its exit from the listing, by rule class and hours-to-end, with the early share, the ask path and the yield distribution, k = 0 (DRAFT)

**Status: DRAFT 2026-10-30, revised after challenger R1 (`reviews/M3_CHALLENGER_R1_2026-10-30.md`, GO_WITH_CHANGES on
69c32cff; MUST 1-9, SHOULD 1-9 and rulings Q1-Q12 applied, section 19). Not re-checked, not frozen, not registered,
nothing counted. Next: re-check of this response by `science-reviewer`, then the J1 code, M3-J0, the final pre-freeze
verification and the design-text freeze by 2026-11-16T23:59Z (section 20).** Evidence role
`prospective_measurement` (rule 26 of `CREATIVE_HYPOTHESES_2026-11-02.md` 0.3; role and conditions set by the binding
ruling `reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`, ACCEPT_WITH_CONDITIONS; each condition is mapped in section
16). Source: `CREATIVE_HYPOTHESES_2026-11-03.md` section 2 C (CH274) and section 3 ("M3 (CH274)": estimands and cost lines
frozen before 2026-11-24, window 2026-11-24..12-14 beside M1 and M2 on disjoint units, read-out on or after 2027-01-29).
That round file carries the planned date 11-03 but was written 2026-10-30. Drafted on branch `feat/m3-ch274` from the
`chore/arepo-claude-setup` tip `ed022848`. This is a design-only commit: no M3 code, no queue file, no seal, no host read,
no `data-dumps` read. Structure and every defect class caught on M1 and M2 (their challenger rounds, re-checks, final
verification, J1 ambiguity rulings and code-freeze check) are carried over before review (section 17).

**Before anything is sealed this needs, in order (section 20):** a challenger review (`science-reviewer`) of this text
(done, R1), the designer's response (done, section 19), a re-check, the J1 extractor and blind recorder code for 3.2-3.5 and 10.2 written and unit-tested
on synthetic data, **M3-J0 = that code in dry mode, its `code_sha` recorded in J0's seal**, a final pre-freeze
verification, the design-text freeze commit (sha256 in the ledger) by 2026-11-16T23:59Z, the remaining code (J2, J3, A),
a code-freeze check listing every change to the J1 code since J0's `code_sha`, a host dry run with peak RSS, and the
registration commit (spec and code pins plus the ledger block of 21) by 2026-11-22T23:59Z, at least 24 h before
`REGISTERED_UTC`. Until the pins exist, every line a reader writes is `prospective_unregistered`.
**J0 runs before the design-text freeze and is counts only.** It reads no capture after any hypothetical unit's k for that
unit, no proposal state of a hypothetical unit, no price after k, no resolution. **Its only effect on this text is rule (a)
of 10.1 (the window length).** Nothing else (estimand, weight, split, cell, cost line, class rule, threshold, date other
than by (a)) can change from its output.
**CH276 (R1 MUST 5).** M3's only population gate is M3-J0 rule (a). CH276's line-7 early-settlement share
(`proposed_before_end_date` by class, tier and hours-to-end, a pre-window version of estimand 2) has been REMOVED from
CH276 (orchestrator decision 2026-10-30, ledger entry "Three reviews ... 14:20Z"), so no CH276 line is a gate, threshold or
planning input of M3. Any other CH276 output read by the designer before the freeze is listed in the freeze commit. This
response and every section-18 ruling (as applied in section 19) are committed before q0760's output is opened; after that
commit, CH276 changes nothing in M3.

This is research tooling. AREPO never trades. M3 is a measurement: it reads a resolution only as the declared payoff of
a paper route after the window, it is not a verdict, it is in no Holm family, and it is counted apart from the registered
tests (as M1 and M2 are; the ledger correction entry of 2026-10-30 ~04:36Z; round 20's section 3 already counts
measurements apart). No sentence in this file is a claim that the route makes money. The money in CH274, if any, is a
yield number, not a mispricing (the round's own words). Every count quoted from M1-J0, M2-J0, CH269, CH242, DESIGN_V1 or
the round text is a **counts-only planning figure, never a target**. No outcome, resolution value, price after an origin,
P&L or evidence JSON was read to write it (section 15).

## 0. Summary

- **Object.** A non-sports ex-crypto binary market at the **first 2-hourly capture k** at which its row is two-sided and
  the favoured side's ask is at least 0.95 with the favoured mid at least 0.90, where capture k - 1 showed the same side's
  ask below 0.95 on a two-sided row (a crossing, not a level), the market was never near-certain at any earlier processed
  capture (look-back span or window), the UMA status at k is empty, `end_date` is more than 24 h after the decision time,
  and the market is at least 24 h old. One unit per market (one-shot, rule 24).
- **Favoured side.** YES if the YES ask is at least 0.95 (and the mid at least 0.90); NO if the YES bid is at most 0.05
  (the NO ask `1 - bid` at least 0.95, and the NO mid at least 0.90). The two cannot both hold (3.2).
- **The wait.** `W` = hours from the unit's decision time `t_d` to the first later processed capture that shows a UMA
  proposal state on the market (event P) or its exit from the open listing (event C), whichever first (the composite
  event S; C by absence needs a confirmed absence, 4.1). Read on the capture grid, so S is dated to an interval
  `(W-, W+]` bounded by receipt times (4.1); both ends are printed.
- **Headline estimand (one; R1 Q3).** `F_S(7 d)` = the share of **all** units whose S is observed with `W+ <= 168 h`,
  unit-weighted, event-bootstrap 95% CI with the CR1 event-clustered SE beside. It is a plain proportion: every unit has
  at least 45 days of follow-up, so no horizon up to 30 d is censored by the read-out. Always printed in the same line:
  the same figure on S8 = 1 (single-open-member events), `W50` (the unit-weighted Kaplan-Meier median of `W+`, possibly
  "not reached") and `W50-` (the same on the lower end), the censored share and the classed share.
- **Beside it (declared, all reported):** W quartiles by rule class x hours-to-end and by the other k-visible splits; the
  shares with P first and with C first at 24 h, 72 h, 7 d and 30 d (plain proportions); the early / on-time / late
  partition against `end_date_k` over units with `H_k < 43 d`; the ask path (the share reaching a favoured ask of 0.99
  before S and within 30 d); the realised outcome after the window (`r_eff`, an event-level bound, the realised net per
  share); the quoted yield `g` as Kaplan-Meier quantiles by class and the realised yield ratio `Y`. Two declared
  descriptive contrasts. **Capacity: not measured (no book read; R1 SHOULD 7).**
- **Window** 2026-11-24T00:00Z .. 2026-12-15T00:00Z (21 days; same calendar as M1 and M2; units disjoint from both by
  construction as (market, capture) objects, 2.3); **read-out on or after 2027-01-29T00:00Z** (45 days after the end; the
  round's date; the resolution fetch shared with M2's J3, 10.4); analysis on or after 2027-02-05T12:00Z (after J3's last
  retry pass, 10.4). Design-text freeze by 2026-11-16T23:59Z; registration commit by 2026-11-22T23:59Z.
- **Planning (unprobed population).** The round's bound: 21,516 resolutions at `min(p, 1 - p) <= 0.05` at the last origin
  in 12 days across all categories (CH242); planning **50-150 crossings a day, 1,050-3,150 units in 21 days** (R1 SHOULD 2),
  against the inflow ceiling of CH269's 821 non-sports ex-crypto proposals seen a day; classed share planning 0.70
  (DESIGN_V1 41: `rc_has` 0.700 of eligible non-sports rows on 10-30, against CH199's 44.7% on 10-22). Every number is
  planning; J0 counts the population (10.1); nobody has counted W.

## 1. Common rules (as M1 and M2; binding from this draft)

1. **Wording.** Estimands are definitions, never directional hypotheses. CH274's claim sentence ("the median wait differs
   by an order of magnitude across the classes...", "the early-settlement share is concentrated in the barrier class",
   "the annualised gross is large exactly where the discount is small") is **not** carried into this text: it is replaced
   by the estimand definitions of 4-6. The only ledger form is: "measured (prospective, k = 0; units seen at their first
   two-sided 2 h capture with the favoured ask >= 0.95 and the favoured mid >= 0.90 after a two-sided capture below 0.95,
   unproposed, more than 24 h before `end_date`, at least 24 h old): F_S(7 d) = F [95% CI] (CR1 SE s), on single-open-member
   events F1 [CI]; W50 = X h [CI] (grid lower end W50- = X- h), censored share C%, classed share K%; quoted yield g by class
   as Kaplan-Meier quartiles; capacity not measured (no book read); cost-model-v1, conservative fee, touch,
   size-unlimited." The six words listed in the ruling
   (condition 1) are used in no M3 output, ledger line or display; no p-value is computed or printed.
2. **Freeze before the window.** The headline estimand and weighting, every secondary, the complete split list and the two
   contrasts (8), the cost lines (6), the event definitions and censoring rules (4), the bound (7.2), the outcome and
   descriptive classes (9), the resolution source and floor (9.4), the read-out date, the coarse thresholds (11) and the
   void conditions (12) are frozen in this text and pinned by code hash before `REGISTERED_UTC`. Every declared split is
   reported; none is dropped or added.
3. **Causality.** Eligibility, splits and every unit field use only state visible at or before the unit's decision time
   (3.4). **Only state visible at <= k excludes a unit** (the ruling). Post-k facts (a proposal, an exit, a moved
   `end_date`, a later price) are the measured follow-up or counted descriptive classes and never remove a unit from any
   population.
4. **Missing data stays missing.** No class is filled, no unit is valued at a midpoint, no capture is reconstructed, no
   crossing time is imputed inside its slot, no wait is imputed for a censored unit.
5. **Scope as a parameter (owner).** `scope = non_sports_ex_crypto`, a config parameter of the spec, not a constant of the
   code. **Crypto is excluded by construction**: the Chainlink-resolved hourly and daily series cross 0.95 every hour and
   resolve without a UMA proposal, so W has no crypto version (round 20 section 3, lever 2); the category reader also
   removes UMA-resolved crypto markets (disclosed; the owner's parameter). **Sports is excluded from the primary** because
   the owner has not decided; game markets cross 0.95 in the last minutes and settle within hours (CH274's sports line). A
   sports arm is added only if the owner decides before the design-text freeze; it is then a separate, parallel
   measurement with its own headline and its own seal, **uncounted** in this one, never pooled. J0 prints the sports and
   crypto candidate counts (as M1-J0 and M2-J0 did) so the owner can see the size of that arm.
6. **Nothing here is evidence for a verdict test**, and nothing from a verdict test enters M3 (13).

## 2. Registration, window, freeze deadline and read-out

### 2.1 Dates
- **Window.** `REGISTERED_UTC = 2026-11-24T00:00Z`, `END_UTC = 2026-12-15T00:00Z` (21 days, 252 slots). A capture belongs to
  the window if its manifest start lies in `[REGISTERED_UTC, END_UTC)`. A k is classified only if `start_k` is in
  `[REGISTERED_UTC, END_UTC)` and `start_{k-1} >= REGISTERED_UTC` (M2 ruling W8), so the first possible k is planned at
  2026-11-24T02:31Z. Captures at or after `END_UTC` serve the follow-up only (4.1, 10.2) and are never folded or classified.
- **Look-back (fixed span; M2 R1 MUST 5).** The near-certainty fold (3.2) reads the **fixed span `[REGISTERED_UTC - 7 d,
  REGISTERED_UTC)`** (84 slots) as raw rows and sidecars only (counted `pre_window_source`), whatever the host retains
  beyond it. A slot of the span with no complete capture is `missing_lookback_slot`, never filled; a market near-certain
  only in such a slot can later enter as a unit (disclosed; the slot count is printed). "First" therefore means first in
  the 7-day look-back plus the window: a market near-certain before 11-17 and below the line through the whole look-back
  can enter (disclosed; its earlier history is not read).
- **Freeze deadlines.** Design-text freeze commit by **2026-11-16T23:59Z**; code, code-freeze check and host dry run by
  2026-11-21T23:59Z; **registration commit by 2026-11-22T23:59Z** (at least 24 h before `REGISTERED_UTC`). The round's
  "estimands and cost lines frozen before 2026-11-24" is met by the 11-16 text freeze.
- **Slide rule (declared now).** If the registration commit is later than 2026-11-22T23:59Z, `REGISTERED_UTC` becomes the
  first 00:00Z at least 24 h after the registration commit (never earlier than 2026-11-24T00:00Z), the window stays 21 days
  (or 42 under 10.1 (a)), and the read-out is `END_UTC + 45 days`. Nothing else changes. The slid dates are written in the
  registration commit.
- **Read-out.** `READOUT_UTC = END_UTC + 45 days = 2027-01-29T00:00Z` (the ruling's >= 30 days; the round's date). Why 45,
  not M1's 31: W is right-censored at the read-out, and long-dated units wait to their `end_date`; 45 days gives every unit
  at least 45 days of follow-up (units at the window's start about 66). Under 10.1 (a) (42 days): `END_UTC =
  2027-01-05T00:00Z`, `READOUT_UTC = 2027-02-19T00:00Z`.
- **One analysis, fixed end, no extension.** The analysis refuses before `ANALYSIS_UTC = READOUT_UTC + 7 d + 12 h =
  2027-02-05T12:00Z` (after J3's last retry pass, 10.4; R1 SHOULD 6; under 10.1 (a) 2027-02-26T12:00Z), requires `--out`,
  refuses to overwrite, requires `registration_commit_utc` in the pins file (M1 code-freeze MUST 5), and keeps only unit
  lines whose `spec_sha` and `code_sha` equal the pins and whose role is `prospective_measurement`. **`spec_sha` = the
  sha256 of this file at the registration commit**; the file is never edited after that, and outcomes go to the ledger
  (M2 final SHOULD 4).

### 2.2 Overlaps in time (no shared object)
M1 and M2 (same window), LT10 (11-10..12-01), LT11 (11-18..12-09), E026 (to 12-07), LT12 and LT14 (12-10..12-31) share
captures with M3. M3 reads raw rows, sidecars and `gamma_rules` day files (no book sweep; 6.4) and computes none of their
objects: no engine prediction, no `P` gross by tier (`attrlimit_lt14`), no quote sum across event members, no band, pool,
twin, mover, wallet or spread-into-the-close object. E026's modules are imported read-only where M1 and M2 import them
(`costs.py`, never edited) and its stores are not read. **Objects named by CH id (R1 SHOULD 5; the label "LT15" has meant
two ideas):** DESIGN_V1 41 reserves the `cl_class x tte_h` *engine interaction* for the CH267 test (the spread into the
close; not drafted; token `close`, not requested); round 20 (l.864) uses the same label for CH275 (the insurance price
against disputes, k <= 1). M3's class x hours-to-end grid (S5) is a measurement split of a different target (the wait),
feeds no engine column and writes nothing the engine reads. Any later test on class x hours-to-end, for any target
(CH267, CH275 or another), is `informed (M3)` (section 13; R1 Q6).

### 2.3 Disjointness from M1 and M2 (declared rule) and how overlap is counted
- **Unit-level, by construction.** An M3 unit is a (`market_id`, `capture_id`) pair at which the UMA status is one of the
  empty forms (E6) and `end_date_k - t_d > 24 h` (E7). An M1 unit is a pair whose status contains `propos` at k
  (M1 3.2 E2); an M2 unit is a pair with `start_k - end_date_k >= 2 h` (M2 3.2). So no (market, capture) pair can be an M3
  unit and an M1 or M2 unit: **M1's units are proposed, M2's are overdue, M3's are neither** (the round's rule).
- **Market-level overlap is expected and is counted, never pooled.** The same market can be an M3 unit at k and later an
  M1 unit (its proposal seen at k' > k: that is M3's own event P) or an M2 unit (it falls back into [0.05, 0.95] and goes
  overdue). Counted at read-out only, from unit ids only, as M1 amendment 18(a) does for `m2_overlap`: inside the analysis,
  on or after `READOUT_UTC + 12 h`, M3 may open M1's and M2's write-once unit files (`m1_ch263/units/*.jsonl.gz`,
  `m2_ch264/units/*.jsonl.gz`) and take from each line its `market_id` and `capture_id` and nothing else. No other field,
  class, price, outcome, follow-up or status file is read, kept, printed or stored; J1, J2 and J3 never open those stores.
  Printed: `m1_market_overlap: N`, `m2_market_overlap: N` (M3 units whose market appears in that store) and
  `m1_pair_overlap`, `m2_pair_overlap` (equal (market, capture) pairs; a guard, expected 0; a non-zero count is printed and
  audited). Never used in any estimate, split or class. A store that does not exist prints `unavailable`.
- **M3's P is not read from M1.** M3 dates P from its own blind follow-up (10.2); M1's units are never a source of M3's event.

### 2.4 Time of year (disclosed)
US Thanksgiving (2026-11-26) falls in the window; Christmas and New Year fall in the follow-up (proposals may slow then,
lengthening W for late-window units; S13 is the k-visible split that shows it); no DST change; the US midterm (11-03) and
its resolution days fall before the window. The fee-free population shrinks over time by construction; nothing corrects
for it.

## 3. Unit, decision clock and eligibility

### 3.1 Streams read at window time (all already written by the host; no new collector)
- **Captures** `snapshots/<id>/rows.csv.gz` (manifest `state=complete` only; manifest `start` and `finished_utc`):
  `market_id`, `event_id`, `binary`, `best_bid`, `best_ask`, `closed`, `active`, `end_date`, `liquidity`,
  `clob_token_id_0`, `received_utc`. Below, `bid` and `ask` mean the row's `best_bid` and `best_ask` (the outcome-0 token's
  Gamma touch); YES = outcome 0, NO = outcome 1, also for non-Yes/No binaries (M2 re-check SHOULD 8).
- **Sidecar** `snapshots/<id>/rows_ext.csv.gz`: `received_utc`, `clob_token_id_1`, `uma_resolution_statuses`,
  `accepting_orders`, `created_at`, `fee_type`, `fee_category`, `series_slugs`, `fees_enabled`, `fee_schedule`,
  `order_price_min_tick_size`, `neg_risk_market_id`.
- **No book sweep is read** (capacity dropped, 6.4; R1 SHOULD 7). `book_sweeps/` is not an input of any M3 job.
- **Rule text** `stream_gamma_rules/YYYYMMDD.jsonl` (keyless change log, `streams/common.py` format): `row` / `hash`
  records for keys `m:<id>` of committed polls only; text is classified (3.5) and dropped, never stored.
- **Not read at window time:** book sweeps, trade samples, the monitor, every engine store (`quotes/`, `features/`, `predictions/`,
  `aux/`, resolution logs; the engine log only at the read-out cross-check of 9.4), every `live_tests*` store, E025 / E026
  stores, M1's and M2's stores (except unit ids at read-out, 2.3), any Gamma outcome field.
- **Retention.** Snapshots are kept about 8 days on the host, so J1 (10.2) runs during the window and writes write-once unit
  files; a capture it misses before retention removes it is `missing_capture` (counted, never rebuilt). The follow-up of 10.2
  is written by the same pass for the same reason.

### 3.2 The near-certainty state and the crossing, on the capture grid
All prices are rounded to 6 dp before every comparison and cell boundary (the LT14 / M2 R1 MUST 1 float lesson): `bid`, `ask`
as read; `mid = round((bid + ask) / 2, 6)`; NO-side prices `round(1 - bid, 6)`, `round(1 - ask, 6)`, `round(1 - mid, 6)`.
- **Usable price.** A touch value is usable iff it parses finite and lies strictly in (0, 1). **An ask of exactly 1.0 or a
  bid of exactly 0 is not a resting order** (M1 final verification D6: the venue grid tops out at 0.999 / 0.99, so 1.0 is a
  placeholder for an empty side); decided now, before any M3 data, and applied symmetrically to both sides.
- **Two-sided row:** both values usable and `bid < ask`. **One-sided row:** exactly one usable value. **Crossed or locked:**
  both usable and `bid >= ask` (counted `crossed_book` per row-capture, never near, never two-sided).
- **Favoured ask and mid on a two-sided row:** YES side `ask_Y = ask`, `mid_Y = mid`; NO side `ask_N = 1 - bid`,
  `mid_N = 1 - mid`.
- **Near-certain state `N_j(m)` at a processed capture j** (rule 28: the surviving side is a firm bound, never a mid):
  - (i) two-sided: for side s in {YES, NO}, `ask_s >= 0.95` and `mid_s >= 0.90`. At most one side can hold (YES needs
    `mid >= 0.90`, NO needs `mid <= 0.10`). The `mid_s >= 0.90` clause is M1's readable-side line (a programme constant,
    not set on M3 data): without it a wide book (bid 0.30, ask 0.96) would count as "near-certain".
  - (ii) one-sided beyond the line: the only usable value is a bid `>= 0.95` (YES near: a holder can sell YES at 0.95 or
    more) or an ask `<= 0.05` (NO near: NO can be had for `1 - ask >= 0.95` only by selling YES there, so the YES price is
    firm at `<= 0.05`). A one-sided row with only a bid `<= 0.05` or only an ask `>= 0.95` is **not** near (the surviving
    side alone does not decide it; rule 28).
- **The near-seen set.** Every market (any category) with `N_j` true at any processed capture of the look-back span or of
  the window before k. Every candidate at k enters it at k, whether or not it becomes a unit (one-shot).
- **Granularity is the capture grid.** The crossing of a unit happened in `(t_{k-1}, t_k]`; it is dated to capture k and
  never imputed inside the slot. **Left-censored crossings are recorded, never imputed:** a market whose first processed row
  (in the look-back plus the window) already shows `N` crossed before it was first seen; it is counted
  `left_censored_first_row` (its first row in the look-back: sub-count `pre_window`; its first row in the window, a newly
  listed or newly visible market: sub-count `in_window`) and is never a unit. Markets with `N` at the first look-back
  capture are the bulk of `pre_window` (the stock of near-certain markets on 11-17).

### 3.3 Eligibility (only state visible at <= k; each exclusion a counted class)
Every complete on-grid capture in the window is processed in chronological order (10.2). The **candidates** at k are the
markets whose row at k has `N_k` true and that are **not in the near-seen set**. Every candidate is classified by the first
failing rule below, in this order, and enters the near-seen set at k:
- **E1 Capture.** Captures k and k - 1 are complete, on the grid (`grid0 = 2026-10-01T00:31Z`, 2 h slots, tolerance 30 min,
  the first complete capture of the slot by the `(start, id)` key), k - 1 is the immediately previous slot and was folded
  (not `missing_capture` or `late_capture_ignored`). **k - 1 is the capture id recorded for the previous slot in J1's chain
  status, never a lookup in the capture list** (M1 R-diff MUST 1). Else, per candidate, `no_previous_capture` (k - 1 missing, not folded, or
  gone on resume) or `k_minus_1_before_window` (the first window capture) (M2 ruling N1).
- **E2 First near state is two-sided.** `N_k` holds by (i). Else `first_near_one_sided`, with sub-counts by the surviving
  side (`bid_only_ge_095`, `ask_only_le_005`) (rule 28: a state may read which side survived; printed per day).
- **E3 Crossing at k - 1.** The market has a row at k - 1 (else `no_k_minus_1_row`; if it has no row at any earlier
  processed capture: `left_censored_first_row`, 3.2), that row is two-sided (else `k_minus_1_not_two_sided`, sub-counts
  one-sided / crossed / unparseable), and the same side's ask at k - 1 is `< 0.95` (else `ask_not_crossed`: the side's ask
  was already at 0.95 or more at k - 1 but `N_{k-1}` failed on the mid clause, a wide book; a guard-like class, printed).
- **E4a Open by row at k:** `binary = 1`, `closed` false, `active` true; else `not_open_at_k`. **E4b Sidecar:** capture k's
  sidecar row exists; else `sidecar_missing`. **E4c** `accepting_orders` true; false is `not_open_at_k`; missing or
  unparseable is `accepting_unknown` (M2 ruling 3).
- **E5 Scope.** `boundary_map_ch240.category_of(fee_type, fee_category, series_slugs, True)` on **capture k's own sidecar
  row** is `nonsports_excrypto`. Else `out_of_scope_<category>` (sports and crypto counts printed).
- **E6 Empty UMA status at k (whitelist; M2 R1 MUST 2).** `str(uma_resolution_statuses).strip().lower()` at k is one of
  CH269's empty forms `""`, `"[]"`, `"nan"`, `"none"` (`census_map_ch269.py` `ui` reading). Else `uma_state_at_k` if the
  string contains `propos` (first-seen proposals are M1's domain), or `uma_other_at_k` for every other non-empty form
  (raw form printed, uncapped). No form outside the whitelist ever passes; no J0 output changes the whitelist. The status
  list accumulates history (M1-J0 D1), so an empty form at k means no proposal or dispute was ever listed for the market.
- **E7 End more than 24 h away.** `end_date_k` parses as UTC (else `end_date_missing`; row-captures and distinct markets
  printed, M2 ruling 6) and `H_k = end_date_k - t_d > 24 h` (else `end_within_24h`, which includes markets already past
  their end). Reason (CH274): a crossing in the market's last day makes W hours-to-end under another name (S62).
- **E8 Age at least 24 h.** Capture k's sidecar `created_at` parses (else `created_at_missing`), is not after `start_k`
  (else `created_at_after_k`, a k-visible clock anomaly counted apart from young markets; R1 SHOULD 8) and `start_k -
  created_at >= 24 h` (12 slots) (else `young_at_k`). This is CH274's "market age >= 12 slots"; the idea's name `born_certain` is
  kept for the different case of `left_censored_first_row` (a market listed already near-certain; CH56's seed object),
  because a market 10 h old that crossed at k was not listed near certainty.
- A candidate passing E1-E8 is a **unit**. Guard classes printed and audited: `prior_unit` (expected 0: a unit's market
  entered the near-seen set at its own k) and `near_seen_but_candidate` (expected 0).

**Side counts printed per capture (k-visible; never units):** `crossed_book` row-captures; two-sided rows with a favoured
ask >= 0.95 and the favoured mid < 0.90 (`wide_book_high_ask`); the near-seen set's size and its in-scope part; markets
that leave the listing while near-certain are not counted at window time (that could be a unit's follow-up content).

### 3.4 Unit fields and decision time
- **Decision time** `t_d` = the later of the row's `received_utc` and the sidecar row's `received_utc` at k. If one parses
  it is used alone; if neither parses, `t_d` = capture k's manifest start (`t_d_source = capture_start_fallback`, counted;
  M2 ruling 8). The gap (sidecar minus row) is recorded (M1-J0 and M2-J0: 0 s on every unit).
- **Why the sweep is not in `t_d` (a declared departure from the ruling's CH263 item; R1 Q2 ACCEPT).** For M1 the ruling
  set `t_d` to the latest receipt of row, sidecar and sweep 1, because M1's capacity belonged to its route; R1 rules that
  item specific to CH263's route. M3 reads no sweep at all (6.4), so `t_d` cannot depend on a price-selected stream. The
  gap is recorded here; capacity is not measured.
- **Price on the favoured side** (rows' touch at k, the only price source; M1 R1 Q2): YES: `ask_f = ask`, `bid_f = bid`,
  `mid_f = mid`; NO: `ask_f = 1 - bid`, `bid_f = 1 - ask`, `mid_f = 1 - mid` (all rounded). `h = round(ask - bid, 6) / 2`.
  `c = 1 - ask_f` (the quoted discount). The same side's `ask_f,k-1` is recorded. Tick at k recorded. The touch may be
  stale at `t_d` (disclosed, unmeasured; M2 R1 SHOULD 6; with no sweep read there is no agreement table).
- **Hours to end** `H_k = (end_date_k - t_d)` in hours (k-visible; S4).
- **Unit record.** Everything above plus `event_id` (empty: its own one-market event and cluster, M1 17.6), the event's open
  binary member count at k, `neg_risk_market_id`, `liquidity` at k, tier, `created_at` and age, category, `cat_k`, fee
  fields and the two fee lines of 6, the rule class, the deadline flag and the committing poll's receipt time and day file
  (3.5), the raw status strings at k and k - 1, capture ids k and k - 1, `t_d`, `t_d_source`,
  gaps, `spec_sha`, `code_sha`, role. **Nothing from after capture k.**

### 3.5 Rule class at `t_d` (S2 and S3; pinned; the as-of-k reader)
- **Why not the engine's `rules` aux table.** DESIGN_V1 41 builds `rules` columns only for the engine's eligible feature
  rows (`aux._rules_builder` keys on `ctx["f"]["market_id"]`), and engine eligibility needs mid in [0.02, 0.98] and spread
  <= 0.10; many M3 units sit above mid 0.98, so reading that table would select the class on price. M3 therefore applies
  the same text patterns with M2's k-visible reader to every unit.
- **Patterns (copied verbatim into M3's own module; the engine's and CH269's modules are not frozen and may change):**
  `SCHEDULED_RE` and `BARRIER_RE` (CH269's placeholder lexicons, identical in `census_map_ch269.py`, `m2_j1.py` and
  `signal_engine/rules_text.py`), `CONSENSUS_RE`, `OCCUR_Q_RE` and `OCCUR_D_RE` (`rules_text.py`, DESIGN_V1 41). The
  sha256 of the five pattern strings is a spec pin.
- **S2 class (CH267's derived split, as the engine's census computes it):** on `question + description +
  resolutionSource` lower-cased: `scheduled` (sched and not barrier), `barrier` (barrier and not sched), `both`,
  `consensus` (neither, consensus wording), `other` (none). No record for the market at or before `t_d`: `no_rules`
  (**unclassed, its own cell, never filled**). A `hash` record whose full row is not in a retained file or the ledger:
  `rules_unresolved` (its own cell; M2 R1 SHOULD 8). **`rules_gap` (R1 MUST 8, the reviewer's wording):** "`rules_gap`
  applies only to a unit with no visible record when at least one day file in [`RULES_FIRST_DAY`, k's day] was never
  merged. A unit with a visible record keeps its class (disclosed)." (`RULES_FIRST_DAY` = 20261020; its own cell; the
  engine's `RulesGap` guard read as a counted class so that a lost file cannot silently turn known text into `no_rules`,
  without one missing file reclassing every unit.) The number of units with a visible record whose class was computed
  while some day file in that range was unmerged is printed (`classed_with_gap`; they keep their class). **Ops guard, in
  the registration commit:** no `gamma_rules` day-file retention may activate on the host before every M-recorder's
  (M1, M2, M3) first pass has merged the retained day files.
- **S3 deadline flag `occur_by`:** 1 if `OCCUR_Q_RE` matches the question or `OCCUR_D_RE` the description, else 0; `na`
  for `no_rules`, `rules_unresolved` and `rules_gap`. Disclosed: the pattern was written from the 40-text hand audit and is
  in-sample there (DESIGN_V1 41: it marked 4 of 4 deadline questions and none of the other 36).
- **Reader (M2 3.5 and rulings 7, 12, 14, adopted verbatim).** A record's receipt time is the `finished_utc` of its
  committing `ok` poll line; a record with a parseable `finished_utc` is visible iff it is <= `t_d`; a record without one
  is visible only if its day file's UTC day is strictly before k's UTC day. The class is computed from the market's
  **latest** visible `row` (or `hash` resolved through any committed `row` with an equal sha), latest by commit time
  (`finished_utc`; a record without one sorts at 00:00Z of its day file's UTC day; ties by day file, then line), **never
  by list position** (M2 final SHOULD 2). `gone` records do not change the class.
  Event (`e:`) rows are not read (disclosed: some neg-risk rule text lives only there; DESIGN_V1 41). J1 keeps an
  append-only rule ledger in its state file (per market every committed record's receipt time, day file, kind and class,
  plus the sha-to-class map), merged from every retained day file at each pass and never pruned. No record after `t_d` is
  read for a unit.
- **Coverage is selected and drifts (disclosed; the round's 44.7% / 70%).** The frame is the latest complete capture's open
  markets with `volume24hr > 0`, top 3,000 hourly and the whole frame at 00/06/12/18Z (`streams/gamma_rules.py`). Coverage
  of eligible non-sports markets was 44.7% on 10-22 (CH199 census) and 0.700 on 10-30 (DESIGN_V1 41, `rc_has`), because the
  known set grows ("ever in the frame since 10-20"); it tracks liquidity (corr 0.290 with `ms_log_liq`), so `no_rules`
  collects the quietest markets. The classed share is printed in the ledger line, overall and by tier (S1) and by week
  (S13); the class split is reported within the covered frame and said so. Precision of the classes (DESIGN_V1 41 hand
  audit, information only): `scheduled` 10 of 10 correct, `barrier` **3 of 13** were deadline questions and the rest
  boilerplate or on-date wording, `both` mostly elections, awards and season totals, `consensus` mostly the venue's standard
  clause. **The class is a placeholder text reading, not a resolution mechanism**; S3 is the stricter deadline reading.

### 3.6 Cluster
The cluster is the Gamma `event_id` at k (members of one ladder cross together). A unit with an empty `event_id` is its own
cluster keyed by its market id. No cap: weights are declared instead (5).

### 3.7 Declared readings disclosed (CH274's worlds; no size check; M3 has no test)
- **S62, the end is the wait.** Where the ask reaches 0.95 only near the end, W is hours-to-end under another name; E7
  removes the last day, S4's hours-to-end bins are the disclosure, the `[1 d, 3 d)` bin is reported apart, and the on-time
  share of 4.3 shows it directly.
- **S63, the lagged flag.** The sidecar shows the proposal a capture after the on-chain proposal at worst, so `W+` is long by
  up to one slot and more after missing slots; `W-` is printed beside every `W+` (the grid interval).
- **S64, absent is not settled.** A market can leave the listing without a proposal (delisting, a venue close, an
  auto-resolution). C is therefore reported apart from P (4.2), and the read-out record classes every C unit (9.2).
- **S47 / M1 D2, length bias at the proposal.** A proposal flag is visible for about one capture (2 h liveness); a proposal
  that is made and settled between two captures shows only as C. So the P / C split is a property of the grid, not of the
  venue's process (disclosed; F_S is the grid-robust number).
- **Status semantics (round 20 cause 4; R1 MUST 7: be robust, do not switch definitions).** Whether
  `uma_resolution_statuses` belongs to the market or to its event is unprobed. If it is per event, a unit's P may be a
  sibling's proposal. **P stays as defined (4.1), whatever CH276 or anything else shows.** M3-J0 has no semantics line
  (dropped: siblings of hypothetical units can be hypothetical units after their own k, so the line would read their post-k
  status; CH276's line (1) covers the question outside M3). Robustness is carried by the headline line instead: it always
  prints `F_S(7 d)` on S8 = 1 (single-open-member events), where market and event semantics coincide. Disclosed: under
  per-event semantics, "by-date" ladders would shorten W (an earlier rung's proposal would also fire P for the later
  rungs). S6 (ladder position) shows where it would matter.

## 4. The wait and its companions (estimands 1-3; follow-up read only at the read-out)

### 4.1 Events and censoring (data: the blind follow-up of 10.2, read only on or after `READOUT_UTC`)
- **Follow-up captures** are the processed on-grid captures j > k up to the last one whose start is before `READOUT_UTC`.
  Each carries its manifest start `t_j`, its manifest `finished_utc`, and per unit the row's and the sidecar row's
  `received_utc` (recorded blind, 10.2).
- **Event P:** the first follow-up capture whose status string, split on non-letters and lower-cased, contains a **whole
  token** `proposed`, `disputed` or `resolved` (M2 R1 MUST 2). A non-empty form with none of them is counted
  `uma_other_followup` (descriptive, not P).
- **Event C (R1 Q4: confirmed absence).** C by `closed`: the first follow-up capture at which the row is present with
  `closed` true, with no earlier P; no confirmation is needed. C by absence: the first follow-up capture j at which the row
  is absent, with no earlier P, **only if the next processed capture also shows the market absent or `closed` true, or j is
  the last follow-up capture**; otherwise the absence is counted `absent_flicker` and the wait continues. No 2 h is added: a
  confirmed absence is dated at the first absent capture j. A market seen again open after its C is counted
  `reappeared_after_C`; the first-event rule stands (C is never revised).
- **Composite S** = the first of P and C, at capture `j_S`; `j_S'` is the last processed capture before `j_S` (capture k
  itself if `j_S` is the first follow-up capture). **Interval (R1 MUST 4, the reviewer's wording):** "`W+ = t⁺ − t_d`,
  where `t⁺` is the sidecar row's `received_utc` at `j_S` for P, the row's for C-by-`closed`, and capture `j_S`'s manifest
  `finished_utc` for C-by-absence." "`W− = max(0, t⁻ − t_d)`, where `t⁻` is the market's row `received_utc` at `j_S'`
  (`t_d` if `j_S'` = k)." "If a receipt is missing, fall back to `finished_utc` for `t⁺` and the manifest start for `t⁻`
  (counted)" (`receipt_fallback_plus`, `receipt_fallback_minus`; a `j_S'` at which the market was absent, an
  `absent_flicker` capture, has no row receipt and takes the fallback). The state change lies after the pre-S state was
  last observed (at `t⁻`) and no later than the observation of S (at `t⁺`), so the true time lies in `(W-, W+]`. An S observed
  after one or more `missing_capture` slots is attributed to the first observed capture and counted
  `interval_spans_missing` (its `W-` uses the last processed capture, so the interval widens; never filled).
- **Censoring:** a unit with no S at any follow-up capture is right-censored at `t_last - t_d` (`t_last` = the manifest
  `finished_utc` of the last processed follow-up capture before `READOUT_UTC`). Censoring is administrative (it depends
  on k only), declared now. Every unit has at least 45 days of follow-up (2.1), so **no horizon up to 30 d is censored by
  the read-out**; a unit with no S whose `t_last - t_d` is below a horizon h (possible only if the recorder stopped) is
  counted `horizon_unreached(h)` (expected 0) and every share at h prints the bounds [all such units without S, all with
  S] beside it.

### 4.2 Estimand 1: the wait W
- **Headline `F_S(7 d)` (R1 Q3, MUST 9):** the share of **all** units whose S is observed with `W+ <= 168 h`,
  **unit-weighted**, a plain proportion (no horizon up to 30 d is censored by the read-out; 4.1), with its 95%
  event-bootstrap CI (7.1) and the CR1 event-clustered SE printed beside, never substituted. Using `W+` makes it
  conservative by up to one slot; `F_S-(7 d)` on `W-` is printed beside.
- **Same line, always:** the same figure on S8 = 1 (single-open-member events, where market and event status semantics
  coincide; R1 MUST 7) with its CI; `W50` = the Kaplan-Meier median of `W+` over all units with its event-bootstrap CI,
  printed "not reached (> X h)" (X the largest censoring time) if the KM curve never falls to 0.5, a declared outcome, not
  a failure; `W50-` (KM median of `W-`); the censored share; the classed share (3.5).
- **Secondaries:** KM quartiles `W25`, `W75` of `W+` and `W-`; `F_S` at 24 h, 72 h, 7 d, 30 d; **`F_P(h)` and `F_C(h)`** =
  the shares of all units whose S is a P, respectively a C, with `W+ <= h`, at the same horizons (plain proportions, since
  no horizon up to 30 d is censored; `F_P + F_C = F_S`; no Aalen-Johansen estimator is needed or used); the discrete
  per-slot hazard of S for slots 1-12 with at-risk counts; the event-weighted `F_S,E(7 d)` and `W50_E` (each event weight
  1, split equally over its units), printed beside, never substituted. By every split cell of 8, and the class x
  hours-to-end grid S5 in particular.
- **What W is not:** the settlement or payment time. A proposal is followed by a 2 h liveness or a dispute; the read-out
  `closedTime` gives the time to close (6.2), printed beside W.

### 4.3 Estimand 2: the early share (against the card at k)
For each unit, with `E_k = end_date_k` (the k-visible card; a later move of `end_date` is a descriptive class, 9.2, never a
change of reference):
- With `t⁺` of 4.1 (`t⁺ = t_d + W+`): `early` if S is observed with `t⁺ <= E_k - 2 h`; `on_time` if
  `E_k - 2 h < t⁺ <= E_k + 24 h`; `late` if S is observed with `t⁺ > E_k + 24 h`, or no S is observed and
  `t_last >= E_k + 24 h`; `indeterminate` if no S is observed and `t_last < E_k + 24 h`.
- **Population (R1 MUST 3, the reviewer's wording):** "The early share and the three-way partition are computed over
  units with `H_k < 43 d` (k-visible). For these, `E_k + 24 h` falls before `t_last` by design. A residual
  `indeterminate` (missing final captures) is counted and bounded." (`E_k + 24 h < t_d + 44 d < END_UTC + 44 d`, about
  a day before the last on-grid capture before `READOUT_UTC`.) Reason: follow-up length, decided before any data; the draft's "determinate if S observed or `t_last >= E_k -
  2 h`" depended on the follow-up and dropped long-dated units with no S, which are mostly not early. Units with
  `H_k >= 43 d` stay in every other estimand and are counted beside (S4's `>= 43 d` cell).
- **The early share** = `early / N(H_k < 43 d)`, printed with the residual indeterminate count and the bounds [every
  indeterminate unit not early, every one early]. Using `t⁺` (the upper end) makes "early" conservative by up to one slot.
  The three-way partition is printed over the same denominator. P and C are shown separately within `early` (S64).
- By S2 (class), S3 (deadline flag), S4 (hours to end; its `>= 43 d` cell prints "not in this estimand") and every other
  cell.

### 4.4 Estimand 3: the ask path (does the discount close before S)
- **Event A99**, read at follow-up captures j with k < j < j_S only (up to the last follow-up capture when S is not observed): the favoured side's ask on a two-sided row is `>= 0.99`,
  or the row is one-sided and its only usable value is the favoured side's bid at `>= 0.99` (the favoured ask has vanished
  with the favoured price firm at 0.99 or more: the patient buyer's chance below 0.99 is gone; rule 28; sub-type recorded
  `two_sided` / `ask_vanished`). A one-sided row whose only value is a favoured ask `< 0.99` is not A99.
- **Estimands (R1 MUST 3, the reviewer's wording):** "A99 share = units with A99 observed before S and within 30 d of
  `t_d`, over all units." (Within 30 d: the A99 capture's start is at most `t_d + 30 d`.) Every unit is then determinate,
  because every unit has at least 45 d of follow-up. The slots from k to A99 are printed **labelled "conditional on
  A99"**. The favoured ask at the last two-sided follow-up capture before S (`ask_last`) and `ask_last - ask_f` (the
  discount a buyer who waited would have lost), as distributions. Grid caveats as W's.
- **This needs prices after k in the blind follow-up (10.2); R1 Q1 ACCEPT** (status strings are already outcome content,
  so bid / ask add no new risk class; same procedure and hashes). **Schedule fallback only (R1 feasibility):** if the J1
  code slips past 2026-11-12T23:59Z, estimand 3 is dropped before the freeze and `bid` / `ask` are removed from the
  recorder. Nothing else depends on it.

## 5. Weighting
Every estimand is **unit-weighted** (one unit per market). The event-weighted version of each headline-line number is a
declared secondary printed beside it. No event cap (the ruling: declare weights instead).

## 6. Cost lines, the realised outcome and the yield (estimands 4-5; capacity not measured, 6.4)

### 6.1 Fee lines and capital (cost-model-v1; recorded prices; one entry convention)
- **Entry convention: ask-based.** The paper route lifts the favoured ask at `ask_f` at k and holds to resolution; the
  half-spread is inside `ask_f`, so **no half-spread is subtracted again** (`COST_MODEL.md` 3, `taker_leg`'s
  hold-to-resolution case: no exit cost). The mid-based alternative is not used.
- **Fee, two lines,** per share at `p = ask_f` by `costs.taker_fee_ps` (`rate * (p * (1 - p)) ** exponent`, unrounded per
  share). Both lines and S9 use `cat_k = costs.category_key(capture k's sidecar fee_category)` (E5's `category_of` is the
  scope reader only; M1 re-check fix 2). `exponent` = the `fee_schedule`'s exponent where served, else 1.0;
  `schedule_rate` = its rate where served, else None.
  - **L1 (headline cost line):** `costs.taker_rate(cat_k, schedule_rate, fees_enabled, policy="conservative")`, with
    `fees_enabled` passed as False only for a literal served false, otherwise None (M1 code-freeze ambiguity 7, the
    conservative reading): max(served schedule, docs rate); 0 when the flag is a literal false; for a key outside the docs
    table, the served rate, possibly 0 (0.07 only when no schedule is served; `costs.py:93-104`, M2 R1 Q9).
  - **L2 (rate-0-not-trusted line):** `costs.taker_rate(cat_k, schedule_rate, fees_enabled=None, policy="conservative")`
    when `cat_k` is a `CATEGORY_TAKER_RATE` key; **`costs.MAX_TAKER_RATE` (0.07) when it is not** (M2 5: `taker_rate` drops a
    NaN docs rate, so an unknown key with a served 0 would return 0). Reason: the ruling's "not verified: whether the venue
    charges the rate 0 it serves". **Disclosed (R1 SHOULD 4):** L2 still returns 0 for `geopolitics`, whose docs rate is
    0.0 (`costs.py:52, 93-104`), so "rate 0 not trusted" does not hold in that cell; kept as written for consistency with
    M1 and M2 (the same line there), and S9's `geopolitics` cell is read with this caveat.
  - **Size here (arithmetic, not data).** `p (1 - p)` is 0.0475 at 0.95 and 0.0099 at 0.99: at docs rate 0.05 the fee is
    about 0.24c and 0.05c a share, at 0.07 about 0.33c and 0.07c, against a quoted discount `c` of 0-5c by construction. Fees
    are therefore material at the 0.95 end and immaterial at the 0.99 end; both lines are always printed (M1-J0 had 99%
    fee-free units; M3's share is unprobed).
- **Capital** `cap_i = ask_f * 0.05 * w_i / 8760` (5% a year; `w_i` of 6.2 in hours). Recorded with the line, not tuned.
- `costs.py` is E026-frozen; M3 imports it and never edits it. Rebates, liquidity rewards, holding rewards and the staleness
  haircut are in no line (disclosed).

### 6.2 Estimand 4: the realised outcome (read only on or after `READOUT_UTC`)
- **Per-unit net per share** (final-state units, 9.1): `n_i = Q_i - ask_f,i - fee_i(L1)`, `Q_i = 1` (resolved to the
  favoured side), `0` (to the other side), `0.5` (split 50-50); equivalently `c_i - L_i - fee_i` with `L = 1 - Q` (the
  ruling's payoff for M1; one formula, not two).
- Reported (all declared secondaries, never the headline): `theta = mean n_i` over final-state units with its event-
  bootstrap CI; `theta_NF` (`not_found` as `Q = 0`) and the attrition band `[theta_W, theta_B]` (every `pending`,
  `not_found`, `unavailable` unit at `Q = 0` / `Q = 1`) **in the same line as `theta`** (M2 rule 1); `theta` under L2;
  `theta_cap = theta - mean cap_i`; `r_eff = P(loss) + 0.5 P(split)`, `P(loss)`, `P(split)` with CIs; the event-level bound
  `T_U` of 7.2 and `theta_low = mean c - T_U - mean fee (L2) - mean cap`, labelled a bound.
- **The time to close** `w_i = closedTime - t_d` from the read-out record (M1 5.2): `closedTime` missing: `fetched_utc - t_d`
  (an upper bound, `wait_upper_bound`); `closedTime < t_d`: `w_i = 0`, counted `wait_clock_anomaly`. Kaplan-Meier median and
  the share closed by 7 d and 30 d over final-state and `pending` units (right-censored at `min(fetched_utc,
  READOUT_UTC)` for `pending`, so a retry pass of 10.4 adds no follow-up time),
  `not_found` and `unavailable` excluded and counted (M2 R1 SHOULD 4).
- **Conditioning disclosed (LT14's lesson).** `theta` is conditional on reaching a final state by the read-out, which is
  after k and may depend on the payoff (disputed units settle late), so `theta` alone can move with attrition; this is why
  `theta_NF` and the band sit in its line.

### 6.3 Estimand 5: the yield (`g` quoted; `Y` realised)
- **Quoted yield per unit** (CH274's estimand 5, defined per dollar of capital, simple annualisation; R1 Q10 ACCEPT):
  `g_i = 100 * 8760 * (1 - ask_f,i - fee_i(L1)) / (ask_f,i * W+_i)` in percent a year. Deviation from the idea, declared
  now: CH274 wrote `(1 - ask_k - fee) / W` per share; dividing by `ask_f` makes it a return on the capital paid (a factor
  of at most 1/0.95 = 1.053). `W+` (not `W-`) is used, so `g` is conservative by up to one slot.
- **Censoring treatment (R1 MUST 3, the reviewer's wording):** "Define `V_i = ask_f,i · W+_i / (1 - ask_f,i - fee_i)`,
  censored at `ask_f,i · (t_last - t_d) / (1 - ask_f,i - fee_i)`. Take KM quantiles of V and report `g_q = 100·8760 /
  V_(1-q)`." `g` falls as V rises, so the q-quantile of `g` is the (1 - q)-quantile of V, and every unit (S observed or
  not) is in the estimate; the draft's quantiles over S-observed units only overstated `g`. The numerator is positive for
  every unit at the docs exponent 1 (ask <= 0.999, so `1 - ask_f >= 0.001` against a fee of at most `0.07 * 0.000999`);
  a unit whose served fee exponent makes `1 - ask_f - fee_i <= 0` has no positive yield, is counted `g_nonpositive` and
  stays in V's risk set throughout (censored at +inf). "A quantile that is not reached prints '< bound'" (`g_q` below
  `100·8760` over the largest V time observed).
- **Reported as a distribution only:** p10, p25, median, p75, p90 (as KM quantiles of V) by S2, S3, S4 and S5 and every
  other cell, with the capital line (`g - 5` points) and the L2 version (V recomputed with the L2 fee) beside. **No mean
  of `g` is computed anywhere, and nothing is pooled across classes** (a short W makes an annualised number explode; the
  round's "never a mean across classes", extended to never a mean). `g` reads the time to the first settle signal, not to
  payment, and ignores losses: it is the quoted yield, not a return.
- **Realised yield ratio per cell** (the capital efficiency of buying every unit of the cell, final-state units only):
  `Y_c = 100 * 8760 * sum_i n_i / sum_i (ask_f,i * w_i)` over final-state units with `w_i > 0` of 6.2 (units with
  `w_i = 0` counted and left out of both sums), with its event-bootstrap CI (the ratio recomputed within each draw),
  printed with the capital line (`Y_c - 5` points). It carries the losses `g` ignores. Thin and coarse rules apply.

### 6.4 Capacity: not measured (declared now; R1 SHOULD 7 taken)
The draft's estimand 6 (`ask_size_1 * best_ask` of the favoured token in sweep 1 of capture k, on the covered subset) is
**dropped before the freeze**; every output prints **"capacity: not measured (no book read)"**. Reasons: sweep 1 selects
only markets with mid in [0.02, 0.98], `bid > 0`, `ask < 1`, spread <= 0.10 and `end_date` more than 3 h after receipt
(`book_sweep.select_tokens`, `panel.eligibility_mask`), so coverage depends on price by construction and units at mid
above 0.98 are never covered; the nearest figure for this price region is M1-J0's sweep coverage, 0.73% (cited by the
CH276 code and R1), so the covered subset would describe almost no unit. Keeping it is not trivially cheap: it adds one
file family per capture to J1's inputs and memory, a token-id join, and a price-selected stream next to the unit clock
(3.4). M2 declared capacity unavailable by construction (M2 5.3); M3 follows. **No dedicated book fetch is added** (M1 R1
MUST 4). The estimand numbers 1-5 are unchanged.

## 7. Inference

### 7.1 Event bootstrap (headline and every CI)
Resample events with replacement (all of an event's units together), B = 10,000, `numpy.random.default_rng(20261126)`
(M1 20261124, M2 20261125), percentile 95% interval. The same event draws serve every estimand, component and contrast; a
split cell's CI uses the same draws restricted to the cell's units, and draws with no unit (or no final-state unit, for
6.2-6.3) in the cell are counted and left out of that cell's percentiles (M2 re-check SHOULD 3). A KM median not reached in
a draw counts as `+inf` in the percentile, so a CI end can print "not reached". A component with no variation gives a
[0, 0] interval: **printed as degenerate; the bound of 7.2 is the bound** (M1 re-check fix 5). **Cross-event dependence
is not captured (disclosed; R1 SHOULD 1 option b):** the draft's day-block bootstrap over the UTC days of k is dropped (it
split ladders whose units cross on different days). Common follow-up shocks that move many events at once (several events
settled together on one news day; the Christmas and New Year slowdown in the follow-up, 2.4) are therefore not reflected
in any interval, which may be too narrow for that reason; S13 (window week) is the k-visible split that shows a holiday
slowdown. For the shares (`F_S(7 d)` and its S8 = 1 version, the early share, the A99 share) the CR1 event-clustered SE is
printed beside the bootstrap interval, never substituted. No p-value, no test.

### 7.2 Event-level bound on the loss share (M1's corrected `T_U`)
A ladder can reverse together. `I_e = 1` if any final-state unit of event e has `Q < 1`. Strata s = **final-state units
per event** (1, 2-3, 4-9, 10+; S = 4; an inference stratum, never a split). In each stratum `p_U,s` is the one-sided
Clopper-Pearson upper bound on the event rate at level **1 - 0.05 / S = 0.9875**; `T_U = sum_s (N_s / N_F) * p_U,s`, under
the worst case that every unit of a flagged event loses its full stake. A stratum with no final-state events contributes 0.
Assumption stated: within a stratum an event's rate does not depend on its unit count (homogeneity); without it `T_U` bounds
an event-weighted share. Printed beside: the 10 largest events' final-state unit counts and `I_e`; per-stratum events,
flags and `p_U,s`. With zero losses `p_U,s` is about 4.38 / E_s, so `T_U` is at least 4.38 / N_F times the sum over
non-empty strata of their units per event (at least 1, 2, 4, 10).

## 8. Splits and declared descriptive contrasts (complete list; every one reported; all k-visible)

Each cell reports `N` units, events, `F_S(7 d)` with CI, `F_P(7 d)`, `F_C(7 d)`, `W50` (+ and -) with CI, `W25`, `W75`,
the censored share, the early share with its bounds and indeterminate count (units with `H_k < 43 d` in the cell), the A99
share, `g` quartiles (KM quantiles of V), final-state count,
`r_eff`, `theta`, `Y_c`. Cells with fewer than 30 units or 10 events (for 6.2-6.3: 30 final-state units or 10 events)
print their numbers labelled `thin` (never suppressed).

| # | Split | Cells |
|---|---|---|
| S1 | liquidity tier at k (CH269's `tier_of` on the row's `liquidity`) | lt1k, 1k-10k, 10k-100k, ge100k, tier_na |
| S2 | rule class at `t_d` (3.5) | scheduled, barrier, both, consensus, other, no_rules, rules_unresolved, rules_gap |
| S3 | deadline flag `occur_by` at `t_d` (3.5) | 1, 0, na |
| S4 | hours to end `H_k` (R1 MUST 3: the 43 d edge is the early share's follow-up bound, fixed before any data) | [1 d, 3 d), [3 d, 14 d), [14 d, 43 d), >= 43 d |
| S5 | S2 x S4 (CH274's class x hours-to-end grid) | 8 x 4 = 32 cells |
| S6 | ladder position at k | standalone (one open binary market in the event at k; an empty `event_id` is its own one-market event), member_yes (favoured side YES), member_no (favoured side NO) |
| S7 | favoured side | YES, NO |
| S8 | event open binary member count at k | 1, 2-5, 6+ |
| S9 | fee category `cat_k` | economics, culture, weather, other, finance, politics, mentions, tech, geopolitics, unknown (= any `cat_k` outside those nine keys; E5 structurally excludes an empty `fee_category`, M2 re-check SHOULD 5); 10 cells fixed by rule; J0 prints the distribution |
| S10 | fee class at k, `population_map_ch251.fee_class(fees_enabled, has_fees_enabled_column, fee_schedule)[0]` on capture k's sidecar row | fee_free, fee_on, unknown |
| S11 | favoured ask zone `ask_f` at k (rounded) | [0.95, 0.96), [0.96, 0.97), [0.97, 0.98), [0.98, 0.99), [0.99, 1) |
| S12 | tick size at k | 0.001, 0.01, other / missing |
| S13 | window week of k | days 1-7, 8-14, 15-21 (and 22-28, 29-35, 36-42 under 10.1 (a)) |

**Structural notes and exact identities (disclosed; M1 re-check fix 4, M2 6):** among ladder members S6 equals S7, and S6
"standalone" equals S8 "1" by definition; S5 is S2 x S4 and adds no new variable; S3 is `na` exactly on S2's three unclassed
cells; at tick 0.01 (S12) `ask_f` is a multiple of 0.01, so S11's cells hold single prices there (0.95, 0.96, ...), resting on
the recorded tick being current (M1 D6); S4's first cell starts at 24 h because E7 removes the last day. **Likely thin or
empty cells (disclosed, unprobed for this population):** `scheduled` is small in non-sports scope (M2-J0: 7 of 1,024 units;
DESIGN_V1 41: 1,179 of 11,645 covered non-sports rows), so S5's scheduled row is expected thin; `rules_gap` and
`rules_unresolved` are expected empty; S2 is confounded with liquidity through the frame (S1 x S2 is not a split; the
`no_rules` share by tier is printed instead).

**Selection width for later tests:** **13 splits, 84 cells (87 under 10.1 (a))** (S1 5, S2 8, S3 3, S4 4, S5 32, S6 3, S7 2,
S8 3, S9 10, S10 3, S11 5, S12 3, S13 3) **plus 2 contrasts (5 contrast numbers)**.

**Declared descriptive contrasts (the ruling: a difference with a CI, never an identification):**
- **D1** = `F_S(7 d)(barrier) - F_S(7 d)(scheduled)` within each S4 bin (4 numbers; the idea's class difference at the
  same hours-to-end), on `W+` (R1 SHOULD 3: `scheduled` units were 7 of 1,024 in M2-J0, so the draft's `log(W50)` ratio
  would mostly print thin or "not reached"; a plain-proportion difference is always defined where both cells have units,
  and a bin where either cell is empty prints "empty").
- **D2** = early share (`occur_by = 1`) minus early share (`occur_by = 0`), overall (1 number).
Each with its event-bootstrap CI (events resampled once; the difference taken within each draw). No reading of D1 or D2 as a
resolution mechanism, an inattention effect or a mispricing is allowed (14).

## 9. Outcome classes, post-k descriptive classes, the resolution source and its floor

### 9.1 Classes at read-out (each counted; never filled; never valued at a midpoint)
| Class | Source reading | In `theta` | In `theta_NF` |
|---|---|---|---|
| `resolved_favoured` | `parse_outcome` gives the favoured side (`y = 1` and YES, or `y = 0` and NO), record `closed` true | yes, `Q = 1` | yes |
| `resolved_other` | `parse_outcome` gives the other side, `closed` true | yes, `Q = 0` | yes |
| `split_50_50` | reason `split_50_50`, `closed` true | yes, `Q = 0.5` | yes |
| `pending` | a record exists and is not closed, or `parse_outcome` reason `not_resolved` (sub-class `closed_not_uma_resolved` when `closed` is true); **resolved but not closed is pending** (M1 code-freeze MUST 3) | no; counted | no |
| `not_found` | no record in either batch pass and a single-id re-query answered HTTP 200 with no record both with and without `closed=true` (M2 re-check SHOULD 7) | no | yes, `Q = 0` |
| `unavailable` | no definite answer after the declared retries; or `other_price_vector` / `bad_prices` (named sub-classes) | no; counted | no |
| `no_readout_record` | the unit's market is missing from the read-out output entirely (a job defect, not a venue state; M1 code-freeze SHOULD 4) | no; counted | no |

W, the early share, the ask path and `g` (4, 6.3) do not use these classes; only 6.2 and `Y_c` do. The eligibility classes
of 3.3 are k-time exclusions counted in the funnel. The read-out record's `umaResolutionStatus` is printed as a descriptive
count for each class.

### 9.2 Post-k descriptive classes (never exclude; counts and mean `n_i` per class)
- `end_date_changed_after_k`: the read-out record's `endDate` (or any follow-up row's `end_date`) differs from `end_date_k`
  by more than 1 s (the early partition keeps `E_k`);
- `closed_before_t_d`: `closedTime < t_d` (a stale `accepting_orders`; a fill may not have been possible);
- `C_without_P`, by read-out class (S64: absent markets that resolved, closed unresolved, are still open, or are not found);
- `reappeared_after_C`; `absent_flicker` (4.1); `uma_other_followup`; `interval_spans_missing`; `receipt_fallback_plus`,
  `receipt_fallback_minus`; `horizon_unreached(h)`; `g_nonpositive`; `closed_after_readout` (10.4);
- `disputed_seen`: a `disputed` token at any follow-up capture (count and the class of 9.1 it ends in);
- `m1_market_overlap`, `m2_market_overlap` and the pair guards (2.3).

### 9.3 The `not_found` question
Its payoff is unknown, so it is never valued at the mid: `theta` excludes it, `theta_NF` books it as a full loss, the band
brackets every non-final class.

### 9.4 Resolution source (pinned) and coverage floor
- **Pinned source:** M3's own read-out fetch (10.4) of Gamma `/markets?id=` records for every unit's market, parsed by
  `calibration.parse_outcome` at the commit pinned at registration (the engine's endpoint and parser, `se-labels-v1`;
  `y = 1` iff outcome 0 won; reason `not_resolved` unless `umaResolutionStatus == "resolved"`). The engine's resolution log
  is not the source: it holds only `res_7d` candidates (CH269's note), and many M3 units are outside engine eligibility.
- **Cross-check (read-out only, never a substitute):** for units in the engine's resolution log, agreement of final states
  and `y` (counts; the engine's `not_resolved` / `not_found` are compared with M3's non-final classes, not with its final
  ones, M1 code-freeze SHOULD 7); disagreements listed; the pinned source governs. The idea's "absent class cross-checked
  against the engine's resolution log by closed day" is this check restricted to `C_without_P` units, counts only.
- **Coverage floor (M2 R1 MUST 3; M1 code-freeze MUST 4).** A unit is covered when the source gave a definite answer (a
  record, or absence established as `not_found`). Unit coverage = covered units / M3 units; event coverage = the share of
  events **all of whose units** are covered. **Floor 0.95 of units and 0.95 of events.** Below either, M3 is **void** (12),
  as the ruling's condition 5 states for the whole measurement, although the headline does not read the resolution (R1
  Q8: keep the whole-measurement void, because R19 condition 5 binds; mitigated by J3's three passes over 7 days, 10.4).

## 10. Collectors, stores and the job list (DRAFT specs in text only; no queue file, no code yet)

All jobs are light, `cpu` lane locally or `net` where they fetch, `mem_mb` < 600, and **none runs concurrently with a
multi-GB job or with M1's or M2's J1** (the memory rule; three J1 recorders run on the host to the read-out). **Host load
(R1 Q12):** feasible only with the three J1s run **serially within the 2 h cadence** (M1, M2, M3 one after another in
each pass). The host dry run (section 20 step 8) reports peak memory **at end-of-window state size** (near-seen set,
ever-seen set and rule ledger as after about 66 days; M2 final SHOULD 3) and the wall time per pass, for M3 alone and for
the serial M1 + M2 + M3 pass against the 2 h slot. Precedent for the gap between spec and measurement: CH269 peaked at
558.8 MB against a 450 MB spec. Store: `data-dumps/research_lab/m3_ch274/` on the host (write-once files; never edited).

### 10.1 M3-J0: pre-window counts-only check (before the design-text freeze; uncounted)
- **What J0 is.** J1 (10.2) run in dry mode with the J1 code at the commit recorded in J0's seal (M2 re-check MUST 1), so
  3.2-3.5 are applied exactly; it writes counts only, no unit file and **no follow-up file**. The idea's census line ("no
  later state read beyond the proposal flag's presence as a count") is **narrowed**: the proposal flag after k is M3's
  event, so J0 reads no proposal state, exit, price or any other capture content for a hypothetical unit after its k.
- Reads the last 8 days of rows and sidecars and the retained `gamma_rules` day files on the host (no sweep). **Prints counts
  only:** units a day and the per-day distribution; events and the units-per-event distribution (S8 and 7.2's strata as
  projected); the class funnel of 3.3 (every class, including `left_censored_first_row` with its sub-counts,
  `first_near_one_sided` by surviving side, `ask_not_crossed`, `young_at_k`, `end_within_24h`) and the side counts; the near-
  seen set size at the end of the fold; cells of S1-S13 (S11 as k-time zone counts); the classed share overall and by S1;
  the `cat_k` distribution with raw `fee_category` beside; the rule reader's day-file contiguity from `RULES_FIRST_DAY`,
  committed lines without a parseable `finished_utc`, commits crossing midnight, maximum poll duration; the forms of the
  status string (distinct normalised forms, every non-whitelist form at E6 uncapped); receipt gaps (sidecar minus row);
  `t_d_source` counts; sports and crypto candidate counts (the owner's arm sizes); the planned follow-up volume (units x
  captures to the read-out). **No status-semantics line** (dropped, R1 MUST 7: siblings of hypothetical units can be
  hypothetical units after their own k, so the line would read post-k status; CH276's line (1) covers the question).
- **Look-back in J0 (fixed now; M2 ruling 10).** J0 folds 12 captures (one day), then uses one more capture as k - 1 only.
  A short fold can only add units (markets near-certain only before the fold and back below the line leak in), so **J0's
  one-day fold overstates the unit count** (R1 MUST 6, disclosed) and understates `left_censored_first_row (pre_window)`;
  the overstatement makes rule (a) less likely to fire than a 7-day fold would. J0's look-back is not changed after its
  output is seen.
- **Decision rules declared now, before any count:** (a) **median full-day units fewer than 48 (= ⌈1,000/21⌉): window
  extended to 42 days**, dates rewritten before the freeze (2.1) (R1 MUST 6: the draft's 25, CH274's kill line, left 25-47
  units a day with no extension although coarse rule 1's N < 1,000 was then near-certain; 48 makes (a) and coarse rule 1
  consistent); (b) *record only, redundant* (fewer than 1,008 projected over 21 days; 48 x 21 = 1,008, so (a) always fires
  first); (c) none of J0's numbers changes an estimand, split, cell, cut, cost line, class rule, threshold or date other
  than by (a); the classed-share kill line of CH274 is **not** a J0 rule (it is coarse rule 3, applied to the window's own
  units). Output labelled `informed (M3-J0)`, counts only, sealed with its code hash and the pins of 5.
- Memory: under 600 MB (M2-J0 peaked at 457.7 MB with the rule ledger; M1-J0 297.6 MB); dry run measured.

### 10.2 M3-J1: window-time extractor and blind follow-up recorder (every pass; catch-up within retention)
- **Start gate (M1 code-freeze MUST 2).** J1 refuses to initialise its state before `REGISTERED_UTC`. Its first pass, at or
  after `REGISTERED_UTC` and planned before `REGISTERED_UTC + 12 h`, folds the look-back span in slot order from
  `slot_of(REGISTERED_UTC - 84 * 2 h)` (M2 ruling N4); a slot with no complete capture, or already removed by retention at
  that pass, is `missing_lookback_slot`; pre-window manifests that exist but are not complete are recorded. The same pass
  merges every retained `gamma_rules` day file from `RULES_FIRST_DAY` into the rule ledger and records any day file
  absent (the source of `rules_gap`).
- **Extractor.** For each complete on-grid capture k in the window not yet processed: read captures k - 1 (the capture id
  in the chain status of slot k - 1, M1 R-diff MUST 1) and k (rows and sidecar, `usecols` only) and the rule ledger up to
  `t_d`; apply 3.2-3.5; write `units/<capture_id>.jsonl.gz`
  and `status/<capture_id>.json` (the per-capture funnel of 3.3 and side counts, completeness, missingness notes; **no P,
  C or A99 count and nothing derived from follow-up content**: for follow-up files only their sha256 and line count, M2 R1
  Q1). Idempotent per capture; refuses to overwrite; every line carries `spec_sha`, `code_sha` and role
  `prospective_measurement`. J1 opens no sweep file (6.4).
- **State file between runs:** the near-seen set, the ever-seen market set (for `left_censored_first_row`), the M3 unit ids
  with their favoured side and k, and the append-only rule ledger (3.5). **The state used at capture k holds only captures
  before k and rule records committed at or before each unit's `t_d`.**
- **Strictly chronological, deterministic missing rule (M1 R1 MUST 1, re-check fix 3, code-freeze MUST 1).** Captures are
  processed in increasing manifest start, one at a time; a capture is processed only when every earlier slot is processed
  or recorded `missing_capture`; catch-up replays the backlog in the same order. A slot is recorded `missing_capture` once it
  has no complete capture whose **manifest `finished_utc`** is at or before the slot's grid time + 6 h (a fact about the
  capture, never the time J1 happens to run); a capture finishing later stays unprocessed (`late_capture_ignored`). **Every
  on-time capture for a slot already recorded missing is recorded as `delivered_after_missing_recorded`** (each one, not
  only the first; M1 fix-diff MUST 1), and an on-time capture that arrives after its slot was decided with another capture
  is recorded late with reason `on_time_but_delivered_after_slot_decided` (M1 R-diff MUST 1); neither is ever processed.
  **Duplicate slot:** the first complete capture of a slot by the **`(start, id)` key** is processed; others are
  `duplicate_slot_capture`, and ties on `start` use the same key for the label (M1 fix-diff SHOULD 1). **Off-grid:** a
  complete capture whose start is not within 30 min of a grid point is `off_grid_capture`, never folded, classified or used
  as follow-up (granularity is the grid). Late, duplicate and off-grid capture ids are written to the next processed
  capture's write-once status file, so J2's manifest carries them (M1 code-freeze SHOULD 5). The run refuses unless the
  state file's last folded capture is the last processed-or-missing capture before k. Each status file records that
  capture id and the state file's sha256 before and after.
- **Blind follow-up recorder (for 4 only; procedural blinding, M2 R1 Q1).** At every processed capture j (in the window
  and after it, up to `READOUT_UTC`), for every M3 unit with k < j, append to `followup/<capture_id>.jsonl.gz`: a header
  line with the capture id, manifest start and manifest `finished_utc`; per unit: unit id, row present, `closed`,
  `active`, `accepting_orders`, the raw status string, `end_date`, the row's and the sidecar row's `received_utc` (for
  4.1's interval, R1 MUST 4), **and the row's `best_bid` and `best_ask`** (for 4.4 only; removed with estimand 3 under its
  schedule fallback). No outcome field. Every unit is recorded at every
  capture regardless of its earlier follow-up state, so the writer never reads its own output. The extractor never opens a
  follow-up file; nothing reads one before `READOUT_UTC` (the analysis refuses; no other module imports the reader); each
  file's sha256 enters the status chain. The follow-up is written during the window because the host keeps captures only
  about 8 days; its non-reading before the read-out is a procedure, not a property the data can prove (12.2(b)).
- **Blind proposal-set recorder (for the survivorship line of 14 only; M1 amendment 18(b)'s form).** At every processed
  window capture j, J1 writes to `proposals/<capture_id>.json.gz` (write-once, blind like the follow-up) the sorted ids
  (deltas, gzip, base64) of in-scope markets (E5's reader on capture j's own sidecar) whose status turns from an empty form
  at the previous processed capture to a whole-token P form at j, with its count. Not opened before `READOUT_UTC`; its
  sha256 enters the status chain.
- **Counted missingness reaches the output (M1 code-freeze MUST 6, MUST 7).** Captures without a sidecar, missing columns,
  unparseable `market_id` rows, `t_d_source` fallbacks, `no_row_at_k` cases, the look-back record and every guard class are
  written to status files and summed by the analysis.
- **Synthetic tests to be written:** (i) out-of-order delivery processes in order and gives the same units; (ii) a state file
  holding a capture at or after k makes the run refuse; (iii) a 12-capture catch-up, including a capture that finished more
  than 6 h late after an outage, gives identical unit files to live processing; (iv) running with both blind recorders off,
  or deleting every follow-up and proposal-set file, leaves every unit file and the state file byte-identical, and every
  status file identical except its `followup` / `proposals` fields; (v) a `gamma_rules` record committed after `t_d` never
  changes a unit's S2 or S3 cell; (vi) boundary cases on rounded values: ask 0.95 / 0.949999, mid 0.90, ask exactly 1.0 and
  bid exactly 0 (not usable), `H_k` exactly 24 h, age exactly 24 h, every S11 boundary at ticks 0.01 and 0.001; (vii) E6 passes
  only the four empty forms; (viii) a market near-certain only by (ii) at its first near capture is `first_near_one_sided`
  and never a later unit; a market whose first row is near is `left_censored_first_row`; (ix) duplicate-slot and off-grid
  captures are counted and never processed; (x) J1 refuses to initialise before `REGISTERED_UTC`; (xi) the analysis refuses
  without `registration_commit_utc`, before its date, and when a pinned file is missing (`code_sha` parts refuse a missing
  file, M1 code-freeze SHOULD 9); (xii) a capture for slot s - 1 that appears after slot s - 1 was decided (the R-diff
  `race2` / `dup_label` probes) leaves k - 1 as the chain's capture and is recorded `on_time_but_delivered_after_slot_decided`;
  (xiii) two on-time captures arriving after their slot was recorded missing are both recorded
  `delivered_after_missing_recorded` (the `miss2 missing` probe); (xiv) two captures with the same `start` are ordered and
  labelled by `(start, id)` (the `miss2 tie` probe); (xv) a market with rule records out of commit order in the ledger is
  classed from the latest by commit time; (xvi) `rules_gap` with an unmerged day file: a unit with a visible record keeps
  its class, a unit without one is `rules_gap`. The analysis's own synthetic tests cover confirmed absence and
  `absent_flicker`, the receipt fallbacks of 4.1, `horizon_unreached`, the KM quantiles of V with censoring and
  `g_nonpositive`, and the `H_k < 43 d` early-share population.
- Planned peak RSS 300-500 MB; cap 600 MB. The code checks `code_sha` against the registered pins during the window (M1
  code-freeze SHOULD 10).

### 10.3 M3-J2: window close and follow-up close
**J2 not before 2026-12-15T07:00Z (`END_UTC + 7 h`; under 10.1 (a) 2027-01-05T07:00Z), and it refuses unless all 252
slots (504 under (a)) are decided** (processed or recorded `missing_capture`; M1 R-diff MUST 2: the last slot can be
decided at grid + 6 h = 04:31Z at the earliest, so a 06:00Z job could refuse). It writes the unit manifest (sha256 of every
unit and status file, slot coverage over the window's slots, the missing, late, `delivered_after_missing_recorded`,
duplicate and off-grid lists), its hash committed to the ledger; the unit set is closed; J1 refuses once the manifest
exists for any extractor write (M1 code-freeze SHOULD 6), and continues as the recorder only. At `READOUT_UTC`: the
follow-up and proposal-set manifest (sha256 of every file, follow-up slot coverage after the window) committed before any
read of either.

### 10.4 M3-J3: read-out resolution fetch, shared with M2-J3 (on or after `READOUT_UTC`)
- **Shared with M2 (R1 feasibility; M2 unchanged).** M2's read-out is also 2027-01-29T00:00Z. M3-J3 is **the procedure
  of `MEASUREMENT_M2_CH264.md` section 9.4 (M2-J3), adopted verbatim by reference**, run **in the same job on the same
  date with the same fetch code**: one J3 module, written once, pinned in both registration commits, which takes a
  measurement's unit-id list and write-once store as arguments. In the shared job M2's ids are fetched first, in their own
  batches, exactly as M2 9.4 states (M2's batches, attempts, records and store are not altered by M3's presence); M3's ids
  follow in their own batches of 50 into M3's own write-once `readout/`. A market in both stores is fetched in both lists
  independently; neither measurement reads the other's read-out records. Nothing in M2's text, pins, dates or outputs
  changes. **If the two `READOUT_UTC` differ** (M3's slide rule or 10.1 (a); or M2's own slide), M3-J3 runs the same
  module alone at M3's `READOUT_UTC`.
- **Procedure (M2 9.4, restated for M3's ids):** Gamma `/markets?id=` in batches of 50 with `closed=true`; ids not
  returned are fetched again without `closed`; an id absent in both passes is re-queried alone, with and without
  `closed=true`, and only two HTTP 200 empty answers make it `not_found` (whether Gamma returns archived markets to
  `/markets?id=` is unverified; a false `not_found` biases `theta_NF` downward). Up to 3 attempts per batch at least 1 h
  apart. Records M2 9.4's fields (`state`, which carries `closed`; `y`, reason, `closedTime`, `endDate`,
  `umaResolutionStatus`, `fetched_utc`). About 40-200 requests at the planning counts.
- **M3-only widened retries (R1 SHOULD 6; Q8 mitigation).** For M3's ids only, ids still `unavailable (fetch)` after the
  shared pass are retried in two further passes with the same procedure, at `READOUT_UTC + 3 d` and `READOUT_UTC + 7 d`
  (three passes over 7 days), so that a Gamma outage cannot void the measurement through the coverage floor of 9.4. Ids
  still without a definite answer after the third pass are `unavailable (fetch)`. A record from pass 2 or 3 whose
  `closedTime` is after `READOUT_UTC` is classed `pending` (`closed_after_readout`, counted; its payoff unused), so every
  class refers to the state at `READOUT_UTC`. M2's ids are not retried by M3's passes.

### 10.5 M3-A: analysis (on or after `ANALYSIS_UTC = READOUT_UTC + 7 d + 12 h`)
Verifies the pins (5), both J2 manifest hashes and `registration_commit_utc`; refuses before `ANALYSIS_UTC`
(2027-02-05T12:00Z) whether or not passes 2 and 3 were needed; computes sections 4-9 and 11; reads M1's and
M2's unit ids only as 2.3 allows; prints the ledger line of 1 rule 1; scans every output string for the banned words and
**raises** (not `assert`; M1 code-freeze SHOULD 8); refuses before its date; requires `--out`; refuses to overwrite.

## 11. Precision threshold ("coarse") and planning arithmetic

M3 is reported **coarse** (every number still printed) if any of:
1. units `N < 1,000` (the round's lower planning bound);
2. **the event-bootstrap 95% CI of `F_S(7 d)` wider than 10 points** (R1 MUST 9; the headline share is then not placed
   within plus or minus 5 points, the round's own precision language);
3. the classed share (S2 scheduled, barrier, both, consensus, other) below 0.5 (CH274's kill line, applied to the window's
   own units, not to J0);
4. window slot coverage below 75% of the 252 slots;
5. follow-up slot coverage (window start to `READOUT_UTC`) below 75%;
6. for 6.2 and `Y` only (labelled there): non-final units (`pending + not_found + unavailable + no_readout_record`) above
   10% of units.

**Planning (assumptions, not targets; marked planning wherever quoted; every figure from the round's stated arithmetic):**
- Units: the round's 50-150 crossings a day (CH242's 21,516 tail resolutions in 12 days all categories; 7-10% assumed
  non-sports ex-crypto, so 125-180 a day resolving from near-certainty, of which crossings inside a window are a subset):
  1,050-3,150 units in 21 days (the summary's figure, now the same; R1 SHOULD 2). M3's rule is stricter than the round's
  sketch (two-sided at k and k - 1, mid >= 0.90, strict ask < 1, age, `end_date` > 24 h), so the low end is the more
  likely; J0 counts it. **Inflow ceiling (R1 SHOULD 2):** CH269 saw 821 non-sports ex-crypto proposals a day (any state,
  10-22..10-30); in a steady state the daily flow of P events in any population of this scope cannot exceed it, and 50-150
  crossings a day is 6-18% of it. The ceiling bounds the P part of the flow only: units that end by C (CH269: 1,474 closes
  a day) or stay open are outside it, so it is a planning bound, not a check on J0.
- **Design effect (R1 SHOULD 2; planning, M1's population, not M3's):** M1-J0 projected events by units per event as 586
  (1 unit), 94 (2-3), 48 (4-9), 12 (10+). Taking each stratum at its lower end (1, 2, 4, 10 units) gives 1,086 units with
  `sum m^2 = 2,930`, so if every unit of an event shared its outcome (intra-event correlation 1) the design effect would be
  at least `2,930 / 1,086 = 2.70` (more with larger ladders); at a lower correlation it is smaller. Applied to the low
  planning count, 1,050 / 2.70 = about 389 effective units, and the 95% half-width of `F_S(7 d)` at p = 0.5 is
  1.96 x sqrt(0.25 / 389) = about 5.0 points: the headline sits **at** coarse rule 2's line in that worst case and inside
  it at higher counts or lower correlation. M3's clustering is unprobed (J0 prints it); this changes no rule.
- Classed share: planning 0.70 (DESIGN_V1 41) on engine-eligible non-sports rows; M3's units sit higher in price and lower
  in volume than the engine's panel, so the classed share is expected lower (unprobed; coarse rule 3 exists for this).
- Early share precision (the round's "+-5 points at 300 a class"): with `n_eff` = 80% of raw (round 14's convention), the
  independent-unit 95% half-width at p = 0.5 and 300 units is 1.96 x sqrt(0.25 / 240) = **6.3 points**; members of a ladder
  cross together, so the event-clustered half-width is wider by `sqrt(DE)` with DE unprobed for this population. The round's
  figure omitted both and is not used.
- Median precision (the round's "median W on 300 units of a class is known to a few hours"): a median's SE is
  `1 / (2 f(m) sqrt(n_eff))` with `f(m)` the density of W at its median, which nobody has measured; W is expected to be
  heavy-tailed and possibly bimodal (CH274's boring explanation: barrier units within a day, scheduled units at their end),
  so a class-pooled median may fall in a low-density gap and be imprecise. The round's figure is not used; this is why the
  headline is the fixed-horizon share `F_S(7 d)` (R1 Q3) and `W50` is printed beside it, not gated.
- Censoring: every unit has at least 45 days of follow-up, so the S4 `>= 43 d` cell is expected to be largely censored and
  its median "not reached"; it is kept in the population (R1 Q9) and disclosed in advance; it changes no rule.
- Fees: 0.05-0.33c a share (6.1 arithmetic) against `c` of 0-5c.
- The bound `T_U`: with zero losses at least 4.38 / N_F times the sum over non-empty strata of their units per event (7.2);
  printed, not a coarse rule.

## 12. Void conditions

M3 is **void** (recorded in the ledger, its numbers not reported as a measurement) if any of:
1. any change to an estimand, weight, event definition, censoring rule, split, cut, contrast, cost line, class rule,
   pattern, threshold or the read-out date after `REGISTERED_UTC`;
2. any read, **by an M3 job or for M3's purposes**, of a resolution, label, Gamma outcome field, follow-up file,
   proposal-set file or any data from after a unit's k before `READOUT_UTC`, other than the blind write-and-hash of 10.2
   (R1 MUST 1: M1's 2027-01-15 analysis and the engine read resolutions before 01-29 by design; that is not an M3 read,
   and no output of theirs is an M3 input); named case **(a)**: J1 processed a capture out of
   chronological order, or used state holding a capture at or after k or a rule record committed after `t_d` (audited from
   the status files' sha256 chain); named case **(b)** (procedural blinding; not auditable from the data, only from the
   process record): a follow-up or proposal-set file opened by any process other than its writer before `READOUT_UTC`, or
   the J2 follow-up manifest missing at the analysis;
3. unit selection that uses information from after k (including any exclusion by a post-k class of 9.2);
4. resolution-source coverage below the floor of 9.4;
5. unit lines whose `spec_sha` or `code_sha` differs from the pins making up more than 1% of units (below that dropped,
   counted); the pins include the sha256 of each imported module that sets a class or cell: `boundary_map_ch240.py` (E5),
   `cb17_census.py` and `cb13_label.py` (the sports reader under `category_of`), `live_tests8_base.py` (its
   `crypto_class`), `population_map_ch251.py` (S10), `census_map_ch269.py` (S1's `tier_of`; E6's empty forms are copied, not
   imported), `calibration.py` (the outcome parser), `costs.py` (fee lines, S9), **eight files**, plus the sha256 of the five
   rule pattern strings (3.5); a mismatch at run time refuses, and after `REGISTERED_UTC` is void 12.1 (M1 final MUST 1, M2
   re-check MUST 2);
6. the window started before the registration commit plus 24 h;
7. the J2 unit manifest missing, or its committed hash not matching the unit and status files at the analysis.

## 13. Later tests on the same object, and counting

- A later verdict test on the wait, the early share, the ask path, the yield, any S1-S13 cell or D1 / D2 (including a
  CH267 or CH275 test that reads rule class by hours-to-end, and CH274's `settle_24h` engine target if it is ever run as a verdict) is
  labelled **`informed (M3)`**, uses a window that starts after `READOUT_UTC` (disjoint and later), and counts none of M3's
  data as its evidence.
- If it targets a split, cell or contrast chosen after seeing M3, it reports M3's selection width: **13 splits, 84 cells, 2
  contrasts (5 numbers)** (8). **Any later test on class x hours-to-end, for any target** (the CH267 spread into the close,
  the CH275 insurance price, or another), is `informed (M3)` and reports 13 splits, 84 cells and 5 contrast numbers (R1 Q6).
- M3 may set planning SDs, design effects, censoring shares and population counts for a later design; it never sets a
  threshold after the fact.
- **The `settle_24h` engine target (CH274's builder arm) is not part of M3.** It needs its own DESIGN_V1 note before any
  label; it reads the sidecar and the listing under the engine's own clocks; M3's units, follow-up and read-out are never an
  engine input, and nothing in the engine reads M3's store.
- M3 is in no Holm family, is counted separately from registered tests (the ruling's condition 4; round 20 section 3's
  "expected registered measurements, counted apart"), and changes no verdict.

## 14. What this measurement can and cannot say

**Can say (allowed wording):**
- "Measured (prospective, k = 0): over N units in E events, **counting only non-sports ex-crypto markets seen at their
  first two-sided 2 h capture with the favoured ask at 0.95 or more and the favoured mid at 0.90 or more, after a two-sided
  capture with that ask below 0.95, with an empty UMA status, more than 24 h before `end_date` and at least 24 h old**, a
  share F_S(7 d) [CI] of units showed a UMA proposal state or a confirmed exit from the listing at a 2 h capture within a
  week (F1 [CI] on single-open-member events); the median time to that capture was W50 h [CI] (grid lower end W50- h);
  C% were still waiting at the end of follow-up."
- How W, the early share, the ask path and the quoted yield differ across the declared k-visible cells (rule class,
  hours to end, tier, ladder position, fee class), as descriptive differences with CIs; the realised outcome and the
  realised yield ratio with their bounds.
- **Survivorship line (count-only, read-out; the M1 amendment 18(b) form):** per UTC day of the window, the in-scope first-
  seen proposals (from the blind proposal sets of 10.2), the share whose market was an M3 unit, the share whose market was
  near-certain at an earlier processed capture without becoming a unit (by funnel class, including `first_near_one_sided`,
  the markets the one-sided fold removes; R1 Q5), and the share whose market was
  never near-certain at any processed capture (decided between captures, or one-sided throughout); counts only, labelled a
  coverage line of M3's definition, not a rate.
- The funnel: how many near-certain markets were first seen one-sided, left-censored, young, in their last day or already
  proposed.

**Cannot say:**
- That anyone could earn the yield: no fill, queue, latency or size beyond the touch is measured; capacity is not
  measured at all (no book read); the touch may be stale; `g` is a quoted number to a settle signal, not to payment, and ignores losses.
- When the proposal happened: the status field carries no time (CH269 `not_mapped.proposal_time`); only when a capture
  first showed a state, to one slot.
- Anything about markets that reach 0.95 one-sided, between captures without a two-sided capture below the line, in their
  last day, younger than 24 h, before the look-back, or in sports or crypto; or about other windows.
- Why the wait differs by class: the class is a placeholder text reading (barrier precision 3 of 13 in the hand audit);
  D1 and D2 are descriptive differences, not identifications of a resolution mechanism or of inattention.
- That a sibling's proposal is not a unit's P, until the status semantics are established (3.7); the S8 = 1 figure in the
  headline line is the semantics-robust reading.
- Anything about co-movement across events: common follow-up shocks are not in the intervals (7.1).
- Anything a verdict test would say: it is not a test, has no null and no p-value, and is never pooled with or re-read as one.

## 15. Inputs read to write this draft (bounded; no host, network, `data-dumps` or evidence JSON)
`CLAUDE.md`, `AGENTS.md`; `CREATIVE_HYPOTHESES_2026-11-03.md` 0 (0.0-0.3, the counts table and facts), 1, 2 C (CH274), 3;
`MEASUREMENT_M1_CH263.md` (frozen text with amendment 18); `MEASUREMENT_M2_CH264.md` (with sections 17-21);
`reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`, `reviews/M1_CHALLENGER_R1_2026-10-30.md`,
`reviews/M1_RECHECK_PREFREEZE_2026-10-30.md`, `reviews/M1_FINAL_VERIFY_2026-10-30.md`,
`reviews/M1_CODE_FREEZE_CHECK_2026-10-30.md`, `reviews/M2_CHALLENGER_R1_2026-10-30.md`, `reviews/M2_R1_RECHECK_2026-10-30.md`,
`reviews/M2_J1_AMBIGUITY_RULINGS_2026-10-30.md`; `COST_MODEL.md` 1-3, 6-8; `signal_engine/DESIGN_V1.md` 41 (and 42's head);
`signal_engine/CANDIDATES.md` (the 44.7% lines). Code read for field semantics only: `signal_engine/rules_text.py` (the
five patterns, `parse_rule`, `rules_at`), `signal_engine/aux.py` (`rules_features`, `_rules_builder`: rows keyed on
eligible features), `research_lab/m2_j1.py` (`classify_rule`, the pattern pin), `research_lab/streams/gamma_rules.py`
(frame, `M_FIELDS`), `research_lab/extract.py` and `research_lab/ext_sidecar.py` (row and sidecar columns; `created_at`
and `neg_risk_market_id` are sidecar fields).
**Read for the R1 response (bounded; no host, network, `data-dumps`, evidence JSON or CH276 output):**
`reviews/M3_CHALLENGER_R1_2026-10-30.md`; the M1/M2 diff checks whose defect classes R1 MUST 2 carries,
`reviews/M1_R_DIFF_CHECK_2026-10-30.md` (MUST 1-2), `reviews/M1_FIX_DIFF_CHECK_2026-10-30.md` (MUST 1, SHOULD 1),
`reviews/M2_FINAL_VERIFY_2026-10-30.md` (SHOULD 2-4), with `reviews/M1_FIX2_CONFIRM_2026-10-30.md` and
`reviews/M2_FREEZE_DIFF_CHECK_2026-10-30.md` located but not used for any rule here; `MEASUREMENT_M2_CH264.md` 2.1 and 9.3-9.5
(the J3 adopted by reference); `MEASUREMENT_M1_CH263.md` l.614-619 (M1-J0's units-per-event counts);
`CREATIVE_HYPOTHESES_2026-11-03.md` l.103 (CH269's 821 a day) and l.864 (the CH275 use of "LT15"); `EXPERIMENT_LEDGER.md`
entries of 2026-10-30 13:50Z and 14:20Z (the CH276 line-7 removal). No CH276 output was read.

## 16. The ruling (R19, ACCEPT_WITH_CONDITIONS), condition by condition

| Condition | How M3 meets it | Where |
|---|---|---|
| 1 Wording: estimand-only; ledger form; banned words; no p-values | CH274's claim sentence replaced by definitions; one ledger form; banned-word scan raises in the analysis; no p-value anywhere | 1 rule 1, 4-6, 10.5, 14 |
| 2 Freeze before the window: one headline with weighting (unit-weighted, event-bootstrap CI), complete split list, cost lines, read-out date, coarse threshold; every split reported | headline `F_S(7 d)` unit-weighted with event bootstrap and CR1 beside (R1 Q3); 13 splits / 84 cells / 2 contrasts fixed by rule; L1, L2 and capital; read-out 2027-01-29; 6 coarse rules; text freeze 11-16, pins at registration | 1 rule 2, 4.2, 6, 8, 11, 2.1 |
| 3 Later verdict tests `informed (M3)` on a disjoint later window; selection width; planning SDs only | stated, with the width and the CH267 / CH275 / `settle_24h` cases | 13 |
| 4 No Holm family, k = 0, counted apart from registered tests | stated; round 20 already counts measurements apart | status block, 13 |
| 5 Void: post-start change; any read of a resolution or post-k data before the read-out; post-k selection; source coverage below the floor | void 12.1-12.4 (plus pins, start gate, manifest); 12.2 scoped to reads by an M3 job or for M3's purposes (R1 MUST 1); post-k data written only by the blind recorders, read only at read-out (procedural blinding, 12.2(b)); J0 reads no follow-up; floor 0.95 of units and events, J3 three passes over 7 days | 12, 10.1, 10.2, 10.4, 9.4 |
| 6 `pending`, `not_found`, `split_50_50`, `unavailable`, `contested` separate, never filled, never at a midpoint | 9.1 classes; `contested` has no M3 analogue (the mid clause is in the near state), its role is taken by the counted k-time classes `wide_book_high_ask` and `ask_not_crossed`; censored waits never imputed | 9.1, 3.3, 4.1 |
| CH263 item: payoff `c - r_eff`; no double-counted half-spread | `n = Q - ask_f - fee` (= `c - L - fee`); ask-based, no half-spread subtracted | 6.1, 6.2 |
| CH263 item: tail bound at event level | `T_U` with strata, 1 - 0.05/4, homogeneity, top-10 events | 7.2 |
| CH263 item: declare weights, no event cap | unit-weighted; event-weighted secondary | 5 |
| CH263 item: decision time = latest receipt of row, sidecar and sweep 1 | **departure declared** (R1 Q2 ACCEPT: the item was specific to CH263's route): row and sidecar only; M3 reads no sweep, capacity not measured | 3.4, 6.4 |
| CH263 item: pinned resolution source and its coverage | own read-out fetch with the pinned parser; engine log a cross-check only | 9.4 |
| CH263 item: read-out >= 30 days after the window | 45 days | 2.1 |
| CH264 items: only k-visible state excludes; hazard under declared right-censoring; event-clustered precision | post-k classes never exclude; headline and `F_P`, `F_C` are plain proportions uncensored to 30 d; KM (for `W50`, quartiles and V) under administrative censoring at the read-out; follow-up-dependent denominators removed (R1 MUST 3); event bootstrap plus CR1 for shares; independent-unit planning figures not used | 1 rule 3, 4.1-4.4, 6.3, 7.1, 11 |

## 17. Carried over from M1 and M2 (defect classes pre-empted before review)

| Defect class (where caught) | Applied here as | Where |
|---|---|---|
| Catch-up look-ahead in the extractor (M1 R1 MUST 1) | strictly chronological; state at k holds only captures before k; refusal on a broken chain; tests (i)-(iii) | 10.2, 12.2(a) |
| Missing rule non-deterministic, judged on wall clock (M1 re-check fix 3; code-freeze MUST 1) | `missing_capture` judged on the manifest's `finished_utc` <= grid + 6 h; `late_capture_ignored`; test (iii) with a late capture | 10.2 |
| Duplicate and off-grid captures uncounted (M1 code-freeze ambiguity 8-10, SHOULD 5) | earliest start wins; `duplicate_slot_capture`, `off_grid_capture` in write-once status; off-grid never used | 10.2 |
| No start-date gate (M1 code-freeze MUST 2) | J1 refuses to initialise before `REGISTERED_UTC`; first pass folds the fixed span | 10.2 |
| Look-back depends on retention (M1 R1 MUST 2; M2 R1 MUST 5; ruling N4) | fixed 84-slot span; `missing_lookback_slot` from the span start | 2.1, 10.2 |
| `no_previous_capture` uncounted; unparseable k - 1 fields passing (M2 rulings N1, N2) | per-candidate `no_previous_capture` / `k_minus_1_before_window`; `k_minus_1_not_two_sided` sub-count `unparseable` | 3.3 E1, E3 |
| Status read as a token blacklist (M2 R1 MUST 2) | E6 whitelist of CH269's empty forms; follow-up P on whole tokens; `uma_other_*` | 3.3 E6, 4.1 |
| Float boundaries (LT14; M2 R1 MUST 1) | every price rounded to 6 dp before every comparison and cell boundary; test (vi) | 3.2, 8 |
| `ask = 1` placeholder (M1 final D6) | decided before any data: usable prices strictly in (0, 1), both sides | 3.2 |
| Event-level tail bound wrong (M1 R1 MUST 3; re-check fix 1) | strata by final-state units per event, 1 - 0.05/S, homogeneity, empty stratum 0, lower-limit wording | 7.2 |
| Degenerate CI unlabelled (M1 re-check fix 5) | printed as degenerate; the bound is the bound | 7.1 |
| Split-cell bootstrap ambiguous (M2 re-check SHOULD 3) | same draws restricted to the cell; empty draws counted and left out | 7.1 |
| Planning figures assuming independent units (ruling; M2 R1 arithmetic; round 19's error) | the round's +-5 points and "a few hours" recomputed or set aside; clustering stated | 11 |
| Dedicated book fetch / capacity selected on price (M1 R1 MUST 4) | no fetch; capacity dropped entirely, "not measured (no book read)" (R1 SHOULD 7) | 6.4 |
| Population wording missing from the ledger line (M1 R1 MUST 5) | the full unit definition in the ledger form and in 14; survivorship line | 1 rule 1, 14 |
| Counting with registered tests (M1 R1 MUST 6) | counted apart | 13 |
| L2 not computable; unknown key served 0 (M1 R1 MUST 7; M2 R1 Q9) | L2 with `fees_enabled=None`, `MAX_TAKER_RATE` for keys outside the table; L1 conservative flag parsing (M1 ambiguity 7) | 6.1 |
| Constant fee split; category from the scope reader (M1 re-check fix 2) | S9 and both lines on `costs.category_key`; 10 cells fixed by rule | 6.1, 8 |
| S4 / unknown cells undefined (M2 R1 SHOULD 1; re-check SHOULD 5) | S10 by `fee_class`; S9 `unknown` defined, empty structurally excluded | 8 |
| Undisclosed identities and empty cells (M1 re-check fix 4; M2 R1 SHOULD 2) | S6 = S7 among members, S6 standalone = S8 "1", S3 `na` = unclassed S2, tick-0.01 S11 cells, thin cells named | 8 |
| Imported class-setting readers unpinned (M1 final MUST 1; M2 re-check MUST 2) | eight files plus the pattern strings, refuse on mismatch, void after registration | 12.5 |
| Rule reader: receipt time per record; `hash` without its row; retirement of day files (M2 rulings 7, 12, 14; R1 SHOULD 8) | `finished_utc` per record, day-before rule, `rules_unresolved`, append-only ledger, plus `rules_gap` | 3.5 |
| J0 cannot run before the code exists; J0 effects too broad (M1 re-check; M2 re-check MUST 1) | J1 code with tests before J0; J0 = J1 dry mode with its `code_sha` sealed; only rule (a) can act | status block, 10.1, 20 |
| A census reading the measured outcome (new here: CH274's census line read the proposal flag after k) | J0 reads no follow-up of any hypothetical unit; J0's semantics line dropped (R1 MUST 7); CH276's line 7 removed and CH276 outputs listed at the freeze (R1 MUST 5) | status block, 10.1 |
| Post-k exclusions or post-k-conditioned secondaries (ruling CH264; M2 R1 MUST 4) | none; post-k facts are the follow-up or descriptive classes | 1 rule 3, 9.2 |
| Coverage floor contradicting `not_found` (M2 R1 MUST 3); event floor read as a fraction (M1 code-freeze MUST 4) | covered = a definite answer; event covered iff all its units are | 9.4 |
| Resolved but not closed counted final (M1 code-freeze MUST 3) | `pending` | 9.1 |
| `not_found` from batch absence only (M2 re-check SHOULD 7) | single-id re-query with and without `closed=true`, two HTTP 200 empties | 10.4 |
| Engine cross-check comparing unlike states (M1 code-freeze SHOULD 7) | final states compared with final, non-final with non-final | 9.4 |
| Cross-store reads not implementable (M1 code-freeze MUST 8; amendment 18) | overlap from unit ids only at read-out; survivorship from J1's own blind proposal sets | 2.3, 10.2, 14 |
| Follow-up content leaking through status files (M2 R1 Q1) | status files print follow-up hashes and line counts only; procedural blinding named; 12.2(b) | 10.2, 12 |
| Counted missingness never reaching the output; missing rows mislabelled (M1 code-freeze MUST 6, 7) | all notes summed; `no_row_at_k` counted | 10.2 |
| `t_d` fallback silent (M1 code-freeze SHOULD 3; M2 ruling 8) | `t_d_source` counted | 3.4 |
| Void 11.6 skippable; banned-word `assert`; missing code files skipped (M1 code-freeze MUST 5, SHOULD 8, 9) | `registration_commit_utc` required; raise; refuse | 2.1, 10.5, test (xi) |
| Estimand conditional on a post-k state (LT14) | `theta_NF` and the band in the same line; conditioning paragraph | 6.2 |
| Lagged flag and length-biased proposals (CH263 S47; M1 final D2) | S63, S47 / D2 disclosed; `W-` beside every `W+` | 3.7, 4.1 |
| Stale touch (M2 R1 SHOULD 6) | disclosed, unmeasured (no sweep, so no agreement table) | 3.4 |
| YES / NO for non-Yes/No binaries (M2 re-check SHOULD 8) | outcome 0 / outcome 1 | 3.1 |
| J2 scheduled before the last slot can be decided (M1 R-diff MUST 2; added after R1 MUST 2) | J2 not before 2026-12-15T07:00Z; refuses unless all 252 slots are decided | 10.3 |
| k - 1 looked up in the capture list, not the chain (M1 R-diff MUST 1; R1 MUST 2) | k - 1 = the chain status's capture id; late arrival recorded `on_time_but_delivered_after_slot_decided`; test (xii) | 3.3 E1, 10.2 |
| Second on-time capture for a slot already recorded missing unrecorded (M1 fix-diff MUST 1; R1 MUST 2) | every such capture recorded `delivered_after_missing_recorded`; in J2's lists; test (xiii) | 10.2, 10.3 |
| Same-start tie labelled on `start` only (M1 fix-diff SHOULD 1; R1 MUST 2) | `(start, id)` key for the choice and the label; test (xiv) | 3.3 E1, 10.2 |
| Rule-ledger lookup by list position (M2 final SHOULD 2; R1 MUST 2) | latest by commit time (`finished_utc`), ties by day file and line; test (xv) | 3.5 |
| Host dry run on a small state (M2 final SHOULD 3; R1 MUST 2) | dry run at end-of-window state size (near-seen set, ever-seen set, rule ledger after about 66 days), peak memory and wall time per pass, serial with M1 and M2 | 10, 20 step 8 |
| `spec_sha` undefined (M2 final SHOULD 4; R1 MUST 2) | `spec_sha` = sha256 of this file at the registration commit; never edited after | 2.1 |

## 18. Open questions for the challenger (riskiest first; first draft; answered by R1, rulings applied in section 19)

1. **Prices in the blind follow-up.** The ask path (4.4) needs the favoured ask after k, written blind during the window
   because the host keeps captures about 8 days. M2's recorder was accepted under condition 5 with "no price or outcome
   field". Is a procedurally blind store that holds `best_bid` / `best_ask` acceptable? Declared fallback: drop estimand 3
   and both fields before the freeze.
2. **Decision time without the sweep (3.4).** A departure from the ruling's CH263 item, for the stated reason (the sweep is
   price-selected and only a descriptor here). Acceptable, or must `t_d` include sweep 1's receipt where present?
3. **The headline.** KM median of `W+` with `W50-`, `F_S(7 d)` and the censored share in the same line, or the fixed-horizon
   `F_S(7 d)` as the headline (never censored by the read-out) with the median beside?
4. **C at the first absence.** One absent or closed capture ends the wait (M2's competing event). A listing flicker would
   shorten W; the alternative is two consecutive absent captures (adds up to 2 h). `reappeared_after_C` is printed either
   way. Which?
5. **The near-certainty state (3.2).** Favoured ask >= 0.95 with favoured mid >= 0.90 (M1's readable-side line), strict
   usable prices in (0, 1), and one-sided near states (rule 28) folded into the near-seen set so a market whose first near
   state is one-sided never becomes a unit. Is the mid clause right (rather than spread <= 0.10), and is folding the one-
   sided near state right (it removes the decided-while-one-sided markets, which the survivorship line then counts)?
6. **The CH267 test's reserved object (labelled "LT15" in DESIGN_V1 41).** DESIGN_V1 41 holds the `cl_class x tte_h` engine
   interaction for it (token `close`, not requested). M3's S5 is a measurement split of the wait, not of the spread into the
   close. Any conflict, and should a later CH267 test be `informed (M3)` by default?
7. **The class reader.** M3's own copy of the engine's five patterns with M2's k-visible reader on every unit (the engine's
   aux table covers eligible rows only). The barrier lexicon's precision is 3 of 13; should S2 stay CH267's five-way split
   with S3 (`occur_by`) beside it, or should `occur_by` replace `barrier` in S2 before the freeze?
8. **Coverage floor scope.** The ruling voids the measurement below the resolution-coverage floor, although the headline
   does not read the resolution. Keep the void for the whole of M3 (as written), or confine it to 6.2 and `Y`?
9. **Long-dated units.** With 45 days of follow-up, S4 `>= 60 d` will be mostly censored. Keep it in the headline population
   (as written; it is k-visible), or restrict the headline to `H_k < 60 d` before the freeze?
10. **`g` per dollar.** The idea's `g` was per share; M3 divides by `ask_f` (at most 5.3% larger). Acceptable?
11. **Age clock.** Sidecar `created_at` for E8 (12 slots), and the renaming of the idea's `born_certain` to the left-censored
    first-row case; acceptable?
12. **Host load.** Three J1 recorders (M1, M2, M3) to their read-outs, never concurrent with each other or a multi-GB job:
    feasible within the lanes? (M2-J0's 457.7 MB and its 1.9 M projected follow-up lines are the nearest figures.)

**Not verified (for the challenger and J0):** the crossings a day and units per event (J0); the classed share of this
population; whether `uma_resolution_statuses` is per market or per event (3.7; CH276's first line); whether the listing
keeps closed markets for a capture or drops them (it decides whether C is "closed" or "absent"); whether `created_at` is
populated on every sidecar row; `gamma_rules` day-file contiguity from 20261020 at the first pass (the 14-day host rule is
proposed, not active); Gamma's `/markets?id=` behaviour on archived markets; whether the venue charges the 0 rate it serves.
Added by R1 (still open): whether an open market can be absent from a `complete` capture (the capture universe's filters,
pagination flicker; R1 Q4's confirmed absence is the declared response); whether host `gamma_rules` retention is off (the
ops guard of 3.5); whether q0760 (CH276) has run (its output is not opened before this response is committed).
Sweep-1 coverage is no longer a question (capacity dropped, 6.4); status semantics are no longer a J0 question (3.7).

## 19. Response to challenger R1 (2026-10-30; `reviews/M3_CHALLENGER_R1_2026-10-30.md`, GO_WITH_CHANGES on 69c32cff `61bd55da…086d1a`)

Every item is applied; none is declined. Line numbers refer to this file at this commit. The reviewer's wording is used
where R1 gave it (MUST 1, 3, 4, 6, 8, 9; SHOULD 1; Q3, Q4). This response and every section-18 ruling as applied here are
committed before q0760's (CH276's) output is opened (MUST 5).

### 19.1 MUST
| R1 item | What changed | Lines |
|---|---|---|
| MUST 1 void 12.2 unscoped | 12.2 opens "any read, by an M3 job or for M3's purposes, ..."; M1's 01-15 analysis and the engine named as not M3 reads | 835 |
| MUST 2 six later-caught defects | J2 not before 12-15T07:00Z, refuses unless all 252 slots decided | 746 |
| | k - 1 from the chain status (E1 and the extractor); `on_time_but_delivered_after_slot_decided` | 228, 696 |
| | every on-time capture for a slot recorded missing is `delivered_after_missing_recorded` | 694 |
| | ties on the `(start, id)` key (E1 and duplicate rule) | 226, 697 |
| | rule-ledger lookup by latest commit time, never list position | 309 |
| | host dry run at end-of-window state size; `spec_sha` defined | 637, 136 |
| | one 17 row for each; tests (xii)-(xvi); the diff-check reviews added to 15 | 988-994, 733, 919 |
| MUST 3 three follow-up-dependent denominators | early share and partition over `H_k < 43 d` (k-visible), residual indeterminate counted and bounded; S4 bins `[1 d, 3 d), [3 d, 14 d), [14 d, 43 d), >= 43 d` | 404, 554 |
| | A99 share over all units, A99 before S and within 30 d of `t_d`; slots-to-A99 "conditional on A99" | 421 |
| | `g` from KM quantiles of V censored at the follow-up end; "< bound" when not reached; `g_nonpositive` for a served exponent below 1 | 486 |
| MUST 4 receipt-time bracket | `W+` from the sidecar / row receipt or `finished_utc` by event type, `W-` from the row receipt at `j_S'`, fallbacks counted; recorder writes both receipts and the capture's manifest times | 364, 708 |
| MUST 5 CH276 collision | the status-block paragraph in the orchestrator's terms: only population gate is M3-J0 rule (a); CH276's line-7 share REMOVED from CH276 (orchestrator decision 2026-10-30, ledger); other CH276 outputs read before the freeze listed in the freeze commit; this response committed before q0760's output is opened | 27 |
| MUST 6 rule (a) vs coarse rule 1 | (a) at median full-day units < 48 (= ⌈1,000/21⌉), declared before any count; (b) recomputed (1,008); the one-day fold's overstatement disclosed | 663, 660 |
| MUST 7 status semantics | J0's semantics line dropped; P unchanged whatever CH276 shows; the S8 = 1 figure in the headline line; per-event "by-date" ladders disclosed | 656, 341, 385, 345 |
| MUST 8 `rules_gap` | the reviewer's rule (only units with no visible record); `classed_with_gap` printed; ops guard on `gamma_rules` retention in the registration commit; test (xvi) | 293, 298 |
| MUST 9 headline | `F_S(7 d)` the headline; coarse rule 2 = its event-bootstrap 95% CI wider than 10 points; ledger form, summary, 14 and 16 rewritten | 381, 788, 83 |

### 19.2 SHOULD
| R1 item | Decision | Lines |
|---|---|---|
| SHOULD 1 day-block bootstrap splits ladders | option (b): dropped; common follow-up shocks (Christmas) not captured, disclosed; S13 shows a holiday slowdown | 524 |
| SHOULD 2 planning figures | CH269's 821 a day as the inflow ceiling of the P flow; M1-J0's 586/94/48/12 for a worst-case design effect (>= 2.70; about 5.0 points half-width at 1,050 units); 1,050-3,150 used in both places | 802, 806, 71 |
| SHOULD 3 D1 | `F_S(7 d)` difference (barrier minus scheduled) within S4 bins | 578 |
| SHOULD 4 L2 at `geopolitics` | disclosed; kept for consistency with M1 and M2 | 452 |
| SHOULD 5 "LT15" ambiguous | objects named by CH id (CH267, CH275) in 2.2, 13, 16 and question 6 | 145 |
| SHOULD 6 J3 retries | three passes over 7 days for M3's ids (shared pass, +3 d, +7 d); state at `READOUT_UTC` kept by `closed_after_readout`; analysis at `READOUT_UTC + 7 d + 12 h` | 771, 133 |
| SHOULD 7 capacity | **taken: dropped.** Not trivially cheap (a file family per capture, a token join, a price-selected stream beside the clock) and near-empty by construction (sweep excludes mid > 0.98; M1-J0 coverage 0.73%); prints "capacity: not measured (no book read)"; sweep removed from 3.1, 3.4, J0 and J1 | 504 |
| SHOULD 8 `created_at_after_k` | added to E8 | 250 |
| SHOULD 9 "eleven" vs twelve | the draft has **twelve** open questions (section 18); the ledger entry of 2026-10-30 13:50Z says "Eleven" in error. This commit edits only this file (design-only scope), so the ledger correction is left to the orchestrator's next ledger entry | 996 |

### 19.3 Rulings on section 18
| Q | Ruling | Applied | Lines |
|---|---|---|---|
| Q1 prices in the blind store | ACCEPT | kept; A99 fixed-horizon (MUST 3); fallback now a schedule fallback only (J1 later than 11-12) | 426 |
| Q2 `t_d` without the sweep | ACCEPT | kept; moot for capacity (no sweep read) | 265 |
| Q3 headline | `F_S(7 d)` over all units, event-bootstrap CI, CR1 beside; W50 and W50- in the same line | applied (with the S8 = 1 figure of MUST 7) | 381 |
| Q4 C at first absence | confirmed absence; `absent_flicker`; `closed` needs no confirmation; no 2 h added | applied | 357 |
| Q5 near state | keep the mid clause and the one-sided fold | unchanged; survivorship line names what the fold removes | 204, 887 |
| Q6 reserved object | no conflict; any later class x hours-to-end test is `informed (M3)`, 13 / 84 / 5 | applied | 862 |
| Q7 class reader | keep five-way S2 with S3 beside; lexicon unchanged | unchanged | 552 |
| Q8 coverage-floor scope | keep the whole-measurement void; mitigate by SHOULD 6 | applied | 630 |
| Q9 long-dated units | keep them; early share by MUST 3 | applied (S4 `>= 43 d` kept) | 825 |
| Q10 `g` per dollar | ACCEPT with MUST 3's censoring | applied | 482 |
| Q11 age clock | ACCEPT with SHOULD 8 | applied | 249 |
| Q12 host load | three J1s serially within the 2 h cadence; dry run reports peak memory at end-of-window state and wall time per pass | applied | 636 |

### 19.4 Feasibility simplifications (R1, adopted)
| Simplification | Applied | Lines |
|---|---|---|
| Share J3 with M2 | M2 9.4 adopted by reference; one module pinned in both registrations; same date and fetch code; M2's batches first and unaltered; M3's ids in their own batches and store; alone if the read-outs differ | 756 |
| Drop J0's semantics line | dropped (MUST 7) | 656 |
| Drop the day-block bootstrap | dropped (SHOULD 1 b) | 524 |
| Drop the Aalen-Johansen machinery | `F_P(h)`, `F_C(h)` are plain proportions to 30 d | 391 |
| Capacity optional | dropped (SHOULD 7) | 504 |
| Keep the ask path; fallback only if J1 slips past 11-12 | applied | 427 |

**Unchanged by R1:** the unit rule (3.2-3.3, apart from E1's chain and tie wording and E8's new class), the 13 splits, 84
cells (87 under 10.1 (a)) and 2 contrasts (5 numbers), the cost lines, the outcome classes, the floor, the window and the
read-out date. Changed dates: J2 at 12-15T07:00Z (was 06:00Z); analysis on or after 2027-02-05T12:00Z (was 01-29T12:00Z).

## 20. Ordered pre-registration path

1. Challenger review R1 of this text (`science-reviewer`): **done**, GO_WITH_CHANGES.
2. Designer's response (section 19): **done** (this commit, before q0760's output is opened); **next: a re-check of it
   by `science-reviewer`.**
3. The J1 extractor and both blind recorders for 3.2-3.6, 4.1's recorded fields and 10.2, written on a new branch with the
   synthetic tests (i)-(xvi); the pins (5, 12.5) computed. Built from `m2_j1.py`'s chain and rule reader where the rules
   match. If not done by 2026-11-12T23:59Z, estimand 3 takes its schedule fallback (4.4).
4. **M3-J0** = that code in dry mode, counts only (10.1), sealed with its `code_sha`; its only effect is rule (a) (48 a day).
5. Final pre-freeze verification (the J0 effect limited to (a); dates rewritten only under (a)).
6. Design-text freeze commit by **2026-11-16T23:59Z**, its sha256 in the ledger, listing every CH276 output the designer
   read before it (MUST 5).
7. Remaining code (J2, J3 shared with M2, A); a code-freeze check listing every change to the J1 code since J0's
   `code_sha`, with diffs and reasons.
8. Host dry run (peak RSS under 600 MB at end-of-window state size, wall time per pass, serial with M1's and M2's J1;
   `gamma_rules` day files contiguous from 20261020; never beside a multi-GB job) by 2026-11-21T23:59Z.
9. Registration commit by **2026-11-22T23:59Z** (spec and code pins, `spec_sha` = sha256 of this file then,
   `registration_commit_utc`, the `gamma_rules` retention ops guard of 3.5, the ledger block of 21), at least 24 h before
   `REGISTERED_UTC = 2026-11-24T00:00Z`.
10. J1 first pass at or after 2026-11-24T00:00Z (start gate), before 12:00Z; window to 2026-12-15T00:00Z; J2 not before
    2026-12-15T07:00Z; recorder to 2027-01-29T00:00Z; J2 follow-up manifest then; J3 (shared with M2) on or after
    2027-01-29T00:00Z, M3-only retry passes at 2027-02-01 and 2027-02-05; analysis on or after 2027-02-05T12:00Z.

## 21. Proposed ledger block (DRAFT; not applied)

> ## M3 (CH274) measurement design, R1 response, 2026-10-30 (DRAFT, nothing counted)
> - `MEASUREMENT_M3_CH274.md` revised on `feat/m3-ch274` after challenger R1 (GO_WITH_CHANGES): MUST 1-9, SHOULD 1-9 and
>   Q1-Q12 applied, none declined (section 19); role `prospective_measurement` (R19 rule-26 ruling); k = 0; no Holm; counted
>   apart from registered tests. Unit: a non-sports ex-crypto market at its first two-sided 2 h capture with the favoured
>   ask >= 0.95 and mid >= 0.90 after a two-sided capture below 0.95, unproposed, > 24 h before `end_date`, >= 24 h old; one
>   per market; disjoint from M1's and M2's units by construction. Headline: `F_S(7 d)`, the unit-weighted share with a UMA
>   proposal state or a confirmed listing exit within 7 days, event-bootstrap CI and CR1 beside, with the single-member
>   figure, W50 and W50- in the same line; 13 splits (rule class x hours-to-end among them), 2 contrasts; the early share
>   (`H_k < 43 d`), the ask path, the quoted yield `g` as KM quantiles, the realised outcome beside it; capacity not
>   measured. J3 shared with M2. J0 rule (a) at 48 units a day. Window 2026-11-24..12-14, read-out on or after 2027-01-29,
>   analysis on or after 2027-02-05T12:00Z. CH276's line 7 removed (orchestrator, 14:20Z); this response committed before
>   q0760's output is opened. Correction: the 13:50Z entry's "eleven" open questions should read twelve. Next: re-check.
