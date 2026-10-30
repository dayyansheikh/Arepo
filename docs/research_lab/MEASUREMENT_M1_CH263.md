# Measurement M1 (CH263, "the carry"): the favoured side's discount after a UMA proposal state is first seen, against the reversal tail and the recorded cost, held to resolution, k = 0 (DRAFT)

**Status: DRAFT 2026-10-30, third draft plus the fee-line / S4 / float fix of 17.6 (after challenger R1, `reviews/M1_CHALLENGER_R1_2026-10-30.md`,
GO_WITH_CHANGES, and the pre-freeze re-check, `reviews/M1_RECHECK_PREFREEZE_2026-10-30.md`, NOT_READY; every item applied,
mapped in section 17), not frozen, not registered, nothing counted.** Evidence role
`prospective_measurement` (rule 26 of `CREATIVE_HYPOTHESES_2026-11-02.md` 0.3; role and conditions set by the binding
ruling `reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`, ACCEPT_WITH_CONDITIONS). Drafted on branch `feat/m1-ch263`
from the `chore/arepo-claude-setup` tip `c0818dfe`, a design-only commit. No M1 code, no queue file, no seal, no host read.
Before anything is sealed this needs, in order: a challenger review (`science-reviewer`) of this text (R1 done), the
designer's response (section 17), a re-check of it (done: NOT_READY, fixes applied in 17.5), **the counts-only
pre-freeze job M1-J0 of 9.1**, a final pre-freeze verification, the design-text freeze commit (sha256 in the ledger), the code, a code-freeze check on synthetic
data, a host dry run with peak RSS, and the registration commit (spec and code pins plus the ledger block of 16) at least
24 h before `REGISTERED_UTC` (section 2). Until the pins exist, every line a reader writes is `prospective_unregistered`.
**J0 runs before the design-text freeze and is counts only (no resolution, outcome or post-k price). Its only effects on
this text are rules (a) and (b) of 9.1 (the window length) and S2's cell list; nothing else can change from its output.
After the re-check's fix 2 S2's cell list is fixed by rule in section 6, so J0's S2 effect is only to write the list's
observed distribution into the frozen text; it adds, drops or merges no cell.**
**J0 has run (q0731; `seals/M1_J0_q0731.json`, sha256 `eedaa2b3…2c3d`, `m1-j0-v2`): rules (a) and (b) did not fire (median full-day
eligible units 185 >= 100; projected 21-day units 3,885 >= 2,000), so the 21-day window and every date are unchanged; the next step is the final
pre-freeze verification (17.7). Still DRAFT, not frozen.**

This is research tooling. AREPO never trades. M1 is a measurement: it reads a resolution as the declared payoff of a
paper route after the window, it is not a verdict, it is not part of any Holm family, it is counted apart from the
registered tests (round 19's "about 1.8 registrations" counted it in error; the ledger's correction entry "M1 challenger R1
GO_WITH_CHANGES; round-19 registration count corrected, 2026-10-30 ~04:36Z" puts the round's registered tests at about 0.9
and counts M1 and M2 apart; the idea file is not edited), and no sentence in this file is a claim that the
route makes money. Every count quoted from the CH269 map, the round-19 text or the cost model is a **counts-only planning
figure, never a target**. No outcome, resolution value, price after an origin, P&L or evidence JSON was read to write it
(reads listed in 14).

## 0. Summary

- **Object.** A non-sports ex-crypto binary market at the first 2-hourly capture whose sidecar shows a UMA proposal state
  (none at the previous capture). The side priced at mid >= 0.90 at that capture is the *favoured side* (the venue field
  does not name the proposed side; the CH269 map's pinned reading). One unit per market.
- **Paper route.** Buy one share of the favoured side at its recorded ask at capture k, hold to resolution. Per share,
  `c = 1 - ask_k`; realised payoff `c - L` with `L = 1` (resolved against), `0.5` (split 50-50), `0` (resolved for).
- **Headline estimand (one).** `theta` = the unit-weighted mean over final-state units of `n_i = c_i - L_i - fee_i -
  cap_i`, cost-model-v1, conservative fee, touch, size-unlimited; event-bootstrap 95% CI. Its expectation is
  `E[c] - r_eff - E[cost]` with `r_eff = P(loss) + 0.5 * P(split)` (the ruling's payoff).
- **Beside it (declared, all reported):** components `c`, `r_eff`, fee, capital; an event-weighted secondary; an event-level
  reversal bound `T_U` and the conservative read `theta_low`; the worst-case line for non-final units; ten k-visible splits; capacity at the touch; the wait;
  the bid-side quoted carry (gross, no fill).
- **Window** 2026-11-24T00:00Z .. 2026-12-15T00:00Z (21 days, last day 12-14); **read-out on or after 2027-01-15T00:00Z**
  (31 days after the end); analysis on or after 2027-01-15T12:00Z. Freeze deadlines in section 2.
- **Planning.** CH269: 821 first-seen proposal units a day (median full day, non-sports ex-crypto), of which about 24% had a
  readable side (1,518 readable / 103 two-sided unread / 4,623 not two-sided over the map's 6,244 units): about 200
  eligible units a day, about 4,200 in 21 days. Events among them and sweep-1 coverage are **not mapped** (9.1). The population
  is proposals **seen at a 2 h capture and two-sided at k** only (13); a "coarse" read is likely and is disclosed in advance (10).

## 1. Common rules carried over (binding from the first draft)

1. **Wording.** Estimands are definitions, never directional hypotheses. The only ledger form is: "measured (prospective,
   k = 0; units seen at a 2 h capture and two-sided at k): <estimand> = X [95% CI], theta_low = X_low (bound),
   theta_W = X_W (worst case), cost-model-v1, conservative fee, touch, size-unlimited, capacity Y (covered subset Z%)."
   `theta_low` and `theta_W` always sit in the same line as `theta`. Words not used in
   any M1 output, ledger line or display: the six listed in the ruling (condition 1); no p-values are computed or printed.
2. **Freeze before the window.** The headline estimand and weighting, every secondary, the complete split list (6), the cost
   lines (5), the tail bound (7), the outcome classes (8), the resolution source and floor (8.3), the read-out date, the
   coarse thresholds (10) and the void conditions (11) are frozen in this text and pinned by code hash before
   `REGISTERED_UTC`. Every declared split is reported; none is dropped or added.
3. **Causality.** Eligibility, splits and every unit field use only state visible at or before the unit's decision time
   (3.3). Nothing from after k is written by the window-time extractor; the resolution is read only on or after the
   read-out date.
4. **Missing data stays missing.** No class is filled, no unit is valued at a midpoint, no capture is reconstructed. Missing
   captures, missing sidecar rows and missing sweep rows are counted classes.
5. **Scope as a parameter.** `scope = non_sports_ex_crypto` (the owner has not decided sports). A sports arm is added only
   if the owner decides before the design-text freeze; it is then a separate, parallel measurement with its own headline,
   never pooled with this one. Crypto stays out (its dailies resolve without a UMA proposal; CH76).
6. **Nothing here is evidence for a verdict test**, and nothing from a verdict test enters M1 (12).

## 2. Registration, window, freeze deadline and read-out

- **Window.** `REGISTERED_UTC = 2026-11-24T00:00Z`, `END_UTC = 2026-12-15T00:00Z` (21 days). A capture belongs to the window
  if its manifest start lies in `[REGISTERED_UTC, END_UTC)`. A unit's oldest state input is capture k - 1, so the first
  possible k is the first capture whose capture k - 1 starts at or after `REGISTERED_UTC` (planned 2026-11-24T02:31Z). The
  prior-state look-back (3.2, rule E3) reads **every retained capture before `REGISTERED_UTC`** (at least 84, the 7 days of
  the host's retention) as raw sidecars only (counted `pre_window_source`); fewer than 84 retained is printed, never filled.
- **Freeze deadlines.** Design-text freeze commit by **2026-11-16T23:59Z**; code, code-freeze check and host dry run by
  2026-11-21T23:59Z; **registration commit by 2026-11-22T23:59Z** (at least 24 h before `REGISTERED_UTC`).
- **Slide rule (declared now).** If the registration commit is later than 2026-11-22T23:59Z, `REGISTERED_UTC` becomes the
  first 00:00Z at least 24 h after the registration commit (never earlier than 2026-11-24T00:00Z), the window stays 21 days,
  and the read-out is `END_UTC + 31 days`. Nothing else changes. The slid dates are written in the registration commit.
- **Read-out.** `READOUT_UTC = END_UTC + 31 days = 2027-01-15T00:00Z` (the ruling's >= 30 days; it also equals the engine's
  `RES_GIVEUP_S` of 30 days after a scheduled end for the last units). The resolution fetch (9.4) runs on or after it; the
  analysis (9.5) on or after `READOUT_UTC + 12 h`. Units unresolved at the fetch stay `pending` (8.1).
- **One analysis, fixed end, no extension.** The analysis refuses before its date, requires `--out`, refuses to overwrite,
  and keeps only unit lines whose `spec_sha` and `code_sha` equal the pins and whose role is `prospective_measurement`.
- **Overlaps (time only, no shared object).** LT11 (window 11-18..12-09), E026 (to 12-07), LT12 (from 12-10) and any M2
  window share captures with M1. M1 reads raw rows, sidecars and sweep 1 of those captures and computes none of their
  objects; E026's modules and stores are not read. M1's units (proposal state at k) are disjoint from the engine's eligible
  rows by DESIGN_V1 section 2. An M1 unit that is also an M2 unit is counted (`m2_overlap`) and never pooled.
- **Time of year (disclosed).** US Thanksgiving (2026-11-26) falls in the window; no DST change; the US midterm (11-03) and
  its resolution days fall before it. The fee-free population shrinks over time by construction (markets deployed before
  2026-03-30 resolve and are not replaced); projections do not correct for this.

## 3. Unit, decision clock and eligibility

### 3.1 Streams read at window time (all already written by the host's 2-hourly pass; no new collector)
- **Captures** `snapshots/<id>/rows.csv.gz` (manifest `state=complete` only): `market_id`, `event_id`, `binary`, `best_bid`,
  `best_ask`, `spread`, `closed`, `active`, `end_date`, `liquidity`, `clob_token_id_0`, `received_utc`; the manifest start.
  Below, `bid` and `ask` mean the row's `best_bid` and `best_ask` (the outcome-0 token's Gamma touch).
- **Sidecar** `snapshots/<id>/rows_ext.csv.gz`: `received_utc`, `clob_token_id_1`, `uma_resolution_statuses`, `accepting_orders`, `fee_type`,
  `fee_category`, `series_slugs`, `fees_enabled`, `fee_schedule`, `order_price_min_tick_size`.
- **Sweep 1** `book_sweeps/<id>/rows.csv.gz` (`series_index` 0, `state` complete, whose manifest `snapshot_id` is capture k):
  `token_id`, `market_id`, `batch_receipt_utc`, `best_bid`, `best_ask`, `ask_size_1`, `depth_ask_1c`.
- **Not read:** trade samples, the monitor, the engine's `quotes/`, `features/`, `predictions/` and resolution logs (except
  the read-out cross-check of 8.3), `gamma_rules`, every `live_tests*` store, E025 / E026 stores and the E026 frozen
  modules' stores, M2's store, any Gamma outcome field at window time.
- **Retention.** Snapshots are kept about 8 days on the host, so the extractor (9.2) runs during the window and writes
  write-once unit files; a capture it misses before retention removes it is `missing_capture` (counted, never rebuilt).

### 3.2 Eligibility (only state visible at <= k; each exclusion a counted class)
A market enters at capture k if all of the following hold, checked in this order (the first failing rule names the class):
- **E1 Capture.** Captures k and k - 1 are complete and k - 1 is the immediately previous 2 h slot (`grid0 =
  2026-10-01T00:31Z`, tolerance 30 min, first complete capture of the slot). Else `no_previous_capture` (unavailable).
- **E2 Proposal state first seen.** The sidecar's `uma_resolution_statuses` at k contains the token `propos`
  (case-insensitive; the CH269 map's reading) and not `disput`; at k - 1 the market has a row and a sidecar row and its status
  contains neither `propos` nor `disput` nor `resolv`. Classes: `disputed_at_k`, `no_k_minus_1_row`, `already_proposed`.
- **E3 One-shot.** No proposal or dispute state for the market in any capture since the look-back start (every retained
  capture before `REGISTERED_UTC`, at least 84; section 2), and no earlier M1 unit for the market. Whether the status field
  keeps history is unverified (R1): a dispute reset followed by a new proposal more than the look-back earlier than k could
  still enter as a new unit; J0 counts the forms the status string takes (9.1) and the residual is disclosed. Else `prior_proposal_state` (a re-proposal after a dispute is
  never a new unit).
- **E4 Open at k.** `binary = 1`, `closed` false, `active` true, `accepting_orders` not false. Else `not_open_at_k`.
- **E5 Scope.** Capture k's sidecar row exists (else `sidecar_missing`) and its category, by the CH269 map's reader
  (`boundary_map_ch240.category_of(fee_type, fee_category, series_slugs, True)`) applied to **capture k's own sidecar row**
  (not the latest capture, as the map did), is `nonsports_excrypto`. Else `out_of_scope_<category>` (sports and crypto
  counts printed).
- **Prices are rounded to 6 dp before every comparison and cell edge** (the LT14 / M2 float lesson): `bid`, `ask` as read;
  `mid_k = round((bid + ask) / 2, 6)`; `ask_f`, `bid_f`, `c` and `h` of 3.3 each rounded to 6 dp; the tick rounded to 6 dp
  before S9's equality. The rounded values are the recorded values (exact at the venue's 0.001 / 0.01 ticks).
- **E6 Two-sided at k.** `0 < bid < ask <= 1` on the row at k. Else `not_two_sided`.
- **E7 Readable side.** `mid_k = (bid + ask) / 2`; the favoured side is YES if `mid_k >= 0.90`, NO if `mid_k <= 0.10`.
  Else `contested` (counted class, its own c reported descriptively in 8.2; never folded into the headline).

### 3.3 Unit fields and decision time
- **Price on the favoured side** (rows' touch at k): YES: `ask_f = ask`, `bid_f = bid`; NO: `ask_f = 1 - bid`,
  `bid_f = 1 - ask`. `c = 1 - ask_f`. Recorded beside it: `mid_f`, `h = (ask - bid) / 2`, tick.
- **Price source is the rows' touch only, for every unit.** Switching to the sweep's `best_ask` where a sweep row exists
  would select the price source on price (sweep coverage depends on price, 5.3), so the sweep's `best_ask` is a descriptor:
  an agreement table (rows' `ask_f` against sweep `best_ask`, counts by tick difference) on the covered subset. The touch is
  recorded before `t_d` (the sidecar comes from the same Gamma page bodies as the rows, gap about 0; the sweep minutes
  later), so `c` may be stale at `t_d`; this is staleness, not look-ahead, and the gaps are printed.
- **Sweep fields** (for capacity and a staleness descriptor only): sweep 1's row for the favoured side's token
  (`clob_token_id_0` for YES, the sidecar's `clob_token_id_1` for NO): `ask_size_1`, `best_ask`, `depth_ask_1c`, `batch_receipt_utc`. Absent row or non-finite
  `ask_size_1`: `sweep_uncovered` (capacity unavailable; the unit stays in every other estimand).
- **Decision time** `t_d` = the latest of the row's `received_utc`, the sidecar row's `received_utc` and, where present, the
  sweep row's `batch_receipt_utc` (the ruling's rule). The gaps (sidecar minus row, sweep minus row) are recorded.
- **Unit record.** Everything above plus `event_id`, the event's open binary member count at k, `end_date`, tier, category,
  fee fields and the two fee lines of 5, the raw status strings at k and k - 1, capture ids, `spec_sha`, `code_sha`. Nothing
  from after capture k.

### 3.4 Cluster
The cluster is the Gamma `event_id` at k (a ladder proposed together is one cluster, however many members become units).
A unit whose `event_id` is empty is its own cluster (keyed by its market id) and its own one-market event for S3 / S8.
No cap: weights are declared instead (4).

### 3.5 Declared readings disclosed (CH263's worlds; no size check, M1 has no test)
- **S47, a lagging flag.** If the sidecar's proposal state lags the on-chain proposal by one capture, the first capture with
  the flag is one slot later than the first after the proposal, so the measured `c` is lower than at the true first
  capture (the discount decays as liveness runs). The direction of this reading is disclosed; its size is not measured.
- **S48, a side mis-read.** The favoured side at 0.90 may not be the proposed side; the `contested` class is never folded,
  and section 13's wording names the favoured side, not the proposed side.

## 4. Headline estimand and weighting

- **Per-unit net per share** (final-state units only, 8.1): `n_i = c_i - L_i - fee_i - cap_i`, with `L_i = 0` (resolved to
  the favoured side), `1` (resolved to the other side), `0.5` (split 50-50); `fee_i` and `cap_i` as 5.
- **Headline:** `theta = (1 / N_F) * sum_i n_i` over the `N_F` final-state units: **unit-weighted**, cost line L1 (5),
  touch, size-unlimited. 95% CI by the event bootstrap (7.1). `E[theta] = E[c] - r_eff - E[fee + cap]`,
  `r_eff = P(loss) + 0.5 * P(split)`.
- **Declared secondary weighting (reported beside, never substituted):** `theta_E`, event-weighted (each event weight 1,
  split equally over its final-state units).
- **Components, each with its event-bootstrap CI:** mean `c` (and p10, p25, median, p75, p90, max); `r_eff` (unit-weighted);
  `P(loss)`; `P(split)`; mean fee under L1 and L2; mean capital; the decomposition `c = (1 - mid_f) + h` (descriptive: `h`
  is inside `c` and is **not** subtracted again).
- **Secondaries:** `theta` under L2 (5); the not_found-as-loss line and the worst-case line (8.2); capacity (5.3); the wait
  (5.2); the bid-side quoted carry `1 - bid_f`, gross only, no fill measured, no trade sample read.

## 5. Cost lines (cost-model-v1, recorded prices; one entry convention only)

- **Entry convention: ask-based `c`** (the ruling's first option). The half-spread is inside `c`, so the cost line is the
  fee plus capital and **no half-spread is subtracted** (`COST_MODEL.md` 3, `taker_leg`'s hold-to-resolution case: no exit
  cost). The mid-based alternative is not used.
- **Fee, two lines,** per share at `p = ask_f` by `costs.taker_fee_ps` (formula `rate * (p * (1 - p)) ** exponent`,
  unrounded per share as the model computes it; the venue's 5 dp per-order rounding is immaterial per share), from capture
  k's sidecar fields. **Both fee lines and S2 use `cat_k = costs.category_key(capture k's sidecar fee_category)`** (E5's
  `category_of` is the scope reader only; passed `nonsports_excrypto`, the docs rate would be NaN, `costs.py:48-53, 93`).
  `exponent` = the `fee_schedule`'s exponent where served, else 1.0; `schedule_rate` = the `fee_schedule`'s rate where
  served, else None.
  - **L1 (headline):** `costs.taker_rate(cat_k, schedule_rate, fees_enabled, policy="conservative")`, i.e. (as
    `costs.py:91-104` computes it) `fees_enabled` false giving 0; else max(served rate, docs rate) for a key in the docs
    table; for an **unknown key** (outside the table, or empty) **the served rate, possibly 0**, where a schedule is served,
    and 0.07 only when no schedule is served.
  - **L2 (rate-0-not-trusted bound):** `costs.taker_rate(cat_k, schedule_rate, fees_enabled=None,
    policy="conservative")`, i.e. max(served schedule, docs category rate) **ignoring the served `fees_enabled`**
    (`taker_rate` returns 0 whenever `fees_enabled is False`, `costs.py:91-92`, so L2 must pass `None`; R1 MUST 7). Docs
    rates (`COST_MODEL.md` 2): 0.04 finance / politics / mentions / tech; 0.05 economics / culture / weather / other;
    geopolitics 0. Unknown key: as in L1, the served rate, possibly 0, where a schedule is served, and 0.07 only when none
    is served (so L2 does not bound an unknown-key market whose served rate is 0; such units are counted in S2's `unknown`
    cell with their L1 / L2 rates printed). Reason: the ruling's "not verified: whether the venue charges the rate 0 it serves". At
    `p = 0.99` this is at most about 0.07c a share. **L1 is the headline** (the ruling's conservative fee); **L2 feeds
    `theta_low`** (7.2) and a `theta` under L2 printed beside.
- **Capital** `cap_i = ask_f * 0.05 * w_i / 8760` (5% a year; `w_i` in hours). Recorded with the line, not tuned.
- `costs.py` is E026-frozen; M1 imports it and never edits it; its sha256 is recorded in M1's pins. Staleness haircut,
  liquidity rewards, holding rewards and rebates are not in any line (disclosed).

### 5.2 The wait
`w_i = closedTime - t_d` in hours from the read-out record (8.3). `closedTime` missing: `w_i = fetched_utc - t_d` (an upper
bound, counted `wait_upper_bound`); `closedTime < t_d`: `w_i = 0`, counted `wait_clock_anomaly`. The wait's distribution
(median, p90, max) is reported; it is never a split (it is after k).

### 5.3 Capacity
`cap_usd_i = ask_size_1 * best_ask` of the favoured side's token in sweep 1 at k: median, p25, p75 and the sum per UTC day,
with `depth_ask_1c` beside it; **the sweep coverage share is printed with it**. The sweep selects only markets with mid in
[0.02, 0.98], `bid > 0`, `ask < 1`, spread <= 0.10 and `end_date` more than 3 h after receipt (`book_sweep.select_tokens`,
`panel.py:14, 53-63`, `forecast.py:32`), so sweep coverage **depends on price by construction** and is probably far below
50% (the median half-spread at k of 0.0005 suggests most units sit at mid above 0.98). Capacity is therefore always printed
as **"covered subset only (coverage X%)"**, with the covered subset's S6 (price zone) and S7 (scheduled end) composition
beside the population's, and labelled **not the population's capacity**. **No dedicated book fetch is added** (it would be
a new collector before the freeze deadline, and its receipt would move `t_d` past the touch; R1 MUST 4). Capacity never
selects or weights a unit.

## 6. Splits (complete list; every one reported; all k-visible)

Each cell reports `N` units, events, final-state count, mean `c`, `r_eff`, mean fee (L1), mean capital, `theta` with its
event-bootstrap CI, and the non-final class counts. Cells with fewer than 30 final-state units or 10 events print their
numbers labelled `thin` (never suppressed).

| # | Split | Cells |
|---|---|---|
| S1 | liquidity tier at k (CH269's `tier_of`) | lt1k, 1k-10k, 10k-100k, ge100k, tier_na |
| S2 | fee category at k, `cat_k` (5) | the `CATEGORY_TAKER_RATE` keys inside scope: economics, culture, weather, other, finance, politics, mentions, tech, geopolitics; plus `unknown` = any other `cat_k` (an empty key, a key outside the table, or an out-of-scope key such as `sports` / `crypto` on a unit that E5's reader placed in scope) (10 cells, fixed; J0 prints its distribution). This is M1's fee-category split; M2's "S3 unknown" corresponds to this cell |
| S3 | ladder position at k | standalone (event has one open binary market at k; a unit with an empty `event_id` is its own one-market event, 3.4), member_winner (favoured side YES), member_loser (favoured side NO); among ladder members S3 equals S5 by construction, and S3 "standalone" equals S8 cell "1" by definition (both disclosed; exact identities, not separate information); no `unknown` cell (every unit falls in one of the three) |
| S4 | fee class at k, by `population_map_ch251.fee_class(fees_enabled, has_fees_enabled_column, fee_schedule)[0]` on capture k's sidecar row (CH269's reading) | fee_free (the `fees_enabled` column present, non-empty and false; or a served schedule rate <= 0), fee_on (a served rate > 0), unknown (no parseable served schedule and the flag not false) |
| S5 | favoured side | YES, NO |
| S6 | price zone `c` | `c <= 0.001`, (0.001, 0.005], (0.005, 0.01], (0.01, 0.03], (0.03, 0.10], > 0.10 (**structurally empty**: mid_f >= 0.90 implies `ask_f` >= 0.90; kept so the cell list is unchanged, printed as 0) |
| S7 | scheduled end at `t_d` | end in future, past <= 24 h, past > 24 h, missing |
| S8 | event member count at k | 1, 2-5, 6+ |
| S9 | tick size at k | 0.001, 0.01, other / missing |
| S10 | window week | days 1-7, 8-14, 15-21 |

J0 observed distribution of S2 (informed (M1-J0), counts only; 1,232 eligible units): other 997, unknown 223, economics 6,
politics 3, culture 2, weather 1, finance 0, mentions 0, tech 0, geopolitics 0. Raw `fee_category` to key: `other:zero_fees` -> other 997,
`unknown` -> unknown 223, economics 6, politics 3, culture 2, weather 1. The cells are unchanged.

Structural zeros (disclosed): S6 `> 0.10` is empty by construction; at tick 0.01 (S9) `c` is a multiple of 0.01, so the
S6 x S9 cells (0.001, 0.005] at tick 0.01 are empty by construction.

Hours to liveness end is **not** a split: the sidecar carries no proposal time (CH269 `not_mapped.proposal_time`).

## 7. Inference

### 7.1 Event bootstrap (headline and every CI)
Resample events with replacement (all of an event's final-state units together), B = 10,000, `numpy.random.default_rng(
20261124)`, percentile 95% interval; the same draws serve every component and split (a split's CI resamples its own events).
Sensitivity printed beside the headline only: a block bootstrap over the 21 UTC days (same B and seed). No p-value, no test.
With zero reversals the `r_eff` and `P(loss)` bootstrap intervals are [0, 0]: **printed as degenerate; `T_U` is the bound**
(7.2).
**Cross-event dependence** (different events reversing together on the same news day) is not held by the event bootstrap;
it is handled **only** by this day-block sensitivity (stated; R1 SHOULD 6), and the wider of the two intervals is printed
beside the headline's.

### 7.2 The reversal tail, bounded at event level
A ladder proposed together can reverse together, so units are not independent draws. Declared:
- **Event reversal indicator** `I_e = 1` if any final-state unit of event e has `L > 0`. Reported: events with
  `I_e = 1` / final-state events, separately for losses and splits.
- **Event-level bound (R1 MUST 3).** Strata s are the **number of final-state units per event**: 1, 2-3, 4-9, 10+ (S = 4).
  This is an inference stratum, never a split or a selection rule (it counts units, not outcomes). In each stratum, `p_U,s` is
  the one-sided Clopper-Pearson upper bound on the event reversal rate at level **1 - 0.05 / S = 0.9875** (Bonferroni, so the
  four bounds hold together with probability at least 0.95). The **unit-level tail bound** is
  `T_U = sum_s (N_s / N_F) * p_U,s`, under the worst case that every unit of a reversed event loses its full stake.
- A stratum with no final-state events contributes 0.
- **Assumption stated:** within a stratum, an event's reversal probability does not depend on its unit count (homogeneity).
  Across strata it may differ freely. Without it, `T_U` bounds an event-weighted share, not the unit-weighted one.
- **Printed beside it:** the 10 largest events' final-state unit counts and their `I_e` (so a reader sees whether a few large
  events carry the unit-weighted tail), and the per-stratum events, reversals and `p_U,s`.
- **The conservative read** `theta_low = mean c - T_U - mean fee (L2) - mean capital`, the three means taken over the same
  `N_F` final-state units as `theta`, is printed beside the headline, labelled as a bound, not an estimate (it mixes an
  estimate, mean `c`, with a bound, `T_U`).

## 8. Outcome classes, the resolution source and its floor

### 8.1 Classes at read-out (each counted; never filled; never valued at a midpoint)
| Class | Source reading | In `theta` |
|---|---|---|
| `resolved_favoured` | `parse_outcome` gives the favoured side | yes, `L = 0` |
| `resolved_other` | `parse_outcome` gives the other side | yes, `L = 1` |
| `split_50_50` | state `split_50_50` | yes, `L = 0.5` |
| `pending` | a record exists but is not closed or not resolved at the fetch | no; counted |
| `not_found` | no Gamma record returned in either fetch pass (9.4) | no in the headline; reported both ways (8.2) |
| `unavailable` | fetch failed after the declared retries, or `other_price_vector` / `bad_prices` (named sub-class) | no; counted |
| `contested` (k-time) | E7 | no; descriptive c only |

`disputed_at_k` and the other eligibility classes of 3.2 are k-time exclusions and are counted in the funnel. The read-out
record's `umaResolutionStatus` (dispute history) is printed as a descriptive count for each class.

### 8.2 Reported both ways and the worst case
- `theta` with `not_found` excluded (headline) and with `not_found` as a loss of the stake (`L = 1`, the price paid lost).
- **Worst-case line** `theta_W`: every `pending`, `not_found` and `unavailable` unit at `L = 1`. Labelled a bound. Reason:
  disputed markets settle late, so a late class may hold the tail.
- `contested` units: mean `c` (on the side nearer 1) and count only.

### 8.3 Resolution source (pinned) and coverage floor
- **Pinned source:** M1's own read-out fetch (9.4) of Gamma `/markets?id=` records for every unit's market, parsed by
  `calibration.parse_outcome` at the commit pinned at registration (the same endpoint and parser as the engine's
  `labels.fetch_resolutions`, `se-labels-v1`). Reason: the engine's resolution log holds only its `res_7d` candidates
  (markets with a res-eligible feature row; CH269's note: "NOT every venue resolution"), and the engine drops proposed rows
  at eligibility, so its coverage of M1's population is partial by construction (the ruling's concern).
- **Cross-check (read-out only, never a substitute):** for units also present in the engine's resolution log, agreement of
  state and `y` is printed (counts). Disagreements are listed; the pinned source governs.
- **Coverage floor.** Source coverage = share of eligible units whose fetch returned a record (any class except `not_found`
  and `unavailable (fetch)`). **Floor 0.95 of units, and 0.95 of events.** Below either, M1 is **void** (11). The share of
  final-state units among eligible units is printed beside it (the coarse rule of 10 uses it).

## 9. Collectors, stores and the job list (DRAFT specs in text only; no queue file, no code yet)

All jobs are light, `net` lane where they fetch, otherwise local; none runs concurrently with a multi-GB job (memory rule).
Store: `data-dumps/research_lab/m1_ch263/` on the host (write-once files; never edited).

### 9.1 M1-J0: pre-window counts-only check (before the design-text freeze; uncounted; no resolution, no post-k price)
- **What J0 is.** A counts-only pre-freeze job. Its only effects on this text are rules (a) and (b) below and S2's cell list
  (fixed by rule in 6; J0 writes only its observed distribution into the frozen text, adding, dropping or merging no cell).
  Nothing else (no estimand, weight, split, cost line, class rule, threshold, date other than by (a) / (b)) changes from it.
- Reads the last 8 days of sidecars, rows and sweep 1 on the host. Applies 3.2 and 3.3 exactly as specified and prints
  **counts only**: eligible units a day; events among eligible units and the member-count distribution (S8); the class
  funnel of 3.2; the cells of S1-S10 (counts, no prices beyond the k-time `c` zone counts of S6); **sweep-1 coverage of the
  favoured side's token with a finite `ask_size_1`** (the item CH269 did not map), overall and by S1 and S7; the receipt gaps
  (sidecar minus row, sweep minus row: median, p90); the share of units whose market is in the engine's resolution
  candidates (a count of the engine's state file, no resolution value); **the forms the `uma_resolution_statuses` string
  takes** (distinct normalised forms, rows with both `propos` and `disput`, transitions proposed -> empty and disputed ->
  proposed between consecutive captures; counts only; R1 MUST 2); **the unavailable classes by category**
  (`no_k_minus_1_row`, `no_previous_capture`, by E5's category of capture k; R1 SHOULD 5, the CH269 counts 1,552 / 1,576
  being of unclear scope); final-state units per event as projected from units per event (T_U's strata, counts only);
  **the distribution of `cat_k` over eligible units** (S2's cells, raw `fee_category` values beside their keys).
- **Decision rules declared now:** (a) eligible units fewer than 100 a day (median full day): window extended to 42 days
  (CH263's line), dates rewritten before the freeze; (b) fewer than 2,000 eligible units projected over 21 days: extended
  to 42 days; (c) whatever the sweep coverage, capacity is printed as covered-subset only with its S6 / S7 composition (5.3);
  **no dedicated book fetch is added** (closed by R1 MUST 4); (d) none of J0's numbers changes an
  estimand, split, cost line or threshold. Output labelled `informed (M1-J0)`, counts only, sealed with its code hash.
- Memory: under 600 MB (CH269's 8-day map peaked at 558.8 MB over a wider read); dry run measured.

### 9.2 M1-J1: window-time extractor (every pass; catch-up allowed within retention)
- After each pass, for each complete capture k in the window not yet processed: read captures k - 1 and k (rows and sidecar,
  `usecols` only) and sweep 1 of k; apply 3.2; write `units/<capture_id>.jsonl.gz` (unit records of 3.3) and
  `status/<capture_id>.json` (the funnel counts, the capture's completeness, the sweep's presence). Idempotent per capture;
  refuses to overwrite; every line carries `spec_sha`, `code_sha` and role `prospective_measurement`.
- Keeps only a small state file (market ids with any proposal or dispute state seen since the look-back start) between runs.
- **Strictly chronological (R1 MUST 1; re-check fix 3).** Captures are processed in increasing manifest start, one at a
  time, and a capture is processed only when every earlier window slot is processed or recorded `missing_capture`; catch-up
  after an outage replays the backlog in the same order. A slot is recorded `missing_capture` once it has no complete
  capture 6 h after its grid time; a capture appearing later stays unprocessed (counted `late_capture_ignored`). The run
  refuses unless the state file's last folded capture is the last processed-or-missing capture before k. Each
  `status/<capture_id>.json` records that capture id and the state file's sha256 before and after. **The state file used
  at capture k holds only captures before k.** Synthetic tests to be
  written: (i) out-of-order delivery processes in order and gives the same units as in-order; (ii) a state file containing
  a capture at or after k makes the run refuse; (iii) a catch-up of a 12-capture backlog gives identical unit files to
  live processing. A breach is the named void case 11.2(a).
- Never reads a capture after k for a unit; never reads any resolution, label or Gamma outcome field.
- Planned peak RSS 300-500 MB (two captures with column selection); measured at the dry run; cap 600 MB.

### 9.3 M1-J2: window close
- At `END_UTC + 6 h`: writes the unit manifest (sha256 of every unit and status file, the slot coverage over the 252 slots
  of the window, the missing-capture list) and commits its hash to the ledger. After this the unit set is closed.

### 9.4 M1-J3: read-out resolution fetch (on or after `READOUT_UTC`)
- For every unit's market id: Gamma `/markets?id=` in batches of 50 with `closed=true` (the engine's call); ids not returned
  are fetched again without `closed` to separate `pending` (record present, not closed or unresolved) from `not_found` (no
  record). Up to 3 attempts per batch at least 1 h apart; remaining failures are `unavailable (fetch)`. Records `state`,
  `y`, `closedTime`, `umaResolutionStatus`, `fetched_utc`. About 100-400 requests in all. Write-once `readout/`.

### 9.5 M1-A: analysis (on or after `READOUT_UTC + 12 h`)
- Verifies the pins and the J2 manifest hash; computes sections 4-8 and 10; prints the ledger line of section 1 rule 1; refuses before
  the date; requires `--out`; refuses to overwrite.

## 10. Precision threshold ("coarse")

M1 is reported **coarse** (with every number still printed) if any of:
1. final-state units `N_F < 2,000`;
2. the headline's event-bootstrap 95% CI half-width > 0.30c a share;
3. the tail bound `T_U > 0.30c` a share;
4. non-final units (`pending + not_found + unavailable`) > 2% of eligible units;
5. window slot coverage < 75% of the 252 slots.

Planning (assumptions, not targets): about 4,200 eligible units; with `r_eff` near 0.5% the per-unit SD of `L` is about 7c,
so the independent-unit SE of `theta` is about 0.11c and the clustered CI half-width plausibly 0.3-0.5c; with zero
reversals the bootstrap CI narrows to the spread of `c` and `T_U` carries the tail: with zero reversals `p_U,s` is about
4.38 / E_s, so `T_U` is at least 4.38 / N_F times the sum over non-empty strata of their units per event (at least 1, 2, 4,
10): about 1,460 units if every event is a single unit, about 24,800 if all four strata are non-empty. With about 4,200
units, coarse rule 3 is expected to fire and `theta_low` is expected to be dominated by the sparsest stratum; disclosed in
advance, it changes no rule. Round 19's "net to +-0.1c at 5,000 units" left out the variance of `L` and is not
used.

## 11. Void conditions

M1 is **void** (recorded in the ledger, its numbers not reported as a measurement) if any of:
1. any change to an estimand, weight, split, cost line, class rule, threshold or the read-out date after `REGISTERED_UTC`;
2. any read of a resolution, label, Gamma outcome field or any data from after a unit's k before `READOUT_UTC` (the J1
   extractor's causality test and the J2 manifest are the checks); named case **(a)**: J1 processed a capture out of
   chronological order, or used a state file holding a capture at or after k (9.2); audited from the status files'
   chain (each records the last folded capture id and the state file's sha256 before and after; a broken chain is the
   breach);
3. unit selection that uses information from after k;
4. resolution-source coverage below the floor of 8.3;
5. unit lines whose `spec_sha` or `code_sha` differs from the pins making up more than 1% of the units (below that they are
   dropped, counted);
6. the window started before the registration commit plus 24 h.

## 12. Later tests on the same object, and counting

- A later verdict test on the carry, the proposal window, the favoured side's discount or any S1-S10 cell is labelled
  **`informed (M1)`**, uses a window that starts after `READOUT_UTC` (disjoint and later), and counts none of M1's data as its
  evidence.
- If it targets a split or cell chosen after seeing M1, it reports M1's selection width: **10 splits, 42 declared cells**
  (S1 5, S2 10, S3 3, S4 3, S5 2, S6 6, S7 4, S8 3, S9 3, S10 3; S2's list is fixed by rule in 6).
- M1 may set planning SDs and population counts for a later design; it never sets a threshold after the fact.
- M1 is in no Holm family, is counted separately from registered tests, and does not change any verdict. Round 19's
  "about 1.8" counted it; the ledger correction entry of 2026-10-30 ~04:36Z (R1 MUST 6) restates the round's registered
  tests as about 0.9 with M1 and M2 counted apart. The idea file is not edited.

## 13. What this measurement can and cannot say

**Can say (allowed wording):**
- "Measured (prospective, k = 0): over N units in E events, **counting only proposals seen at a 2 h capture and only
  units two-sided at k** (planning: readable 1,518 of 6,244 first-seen units, 24%; the lagged seen share in CH269 was 735 of
  1,735 non-sports ex-crypto resolutions on 10-23), the mean discount of the side priced at 0.90 or more at the first
  capture showing a UMA proposal state was c [CI]; the share lost or split, weighted as r_eff, was r [CI], bounded at event
  level by T_U; the mean net per share after the cost-model-v1 conservative fee and a 5% capital charge was theta [CI],
  touch, size-unlimited; the conservative read theta_low was X_low and the worst case theta_W was X_W; capacity at the
  touch Y on the covered subset (coverage Z%, not the population's)."
- **Survivorship line (count-only, read-out; CH263's line restored):** per UTC day of the window, M1's first-seen proposals
  (all classes) against the count of non-sports ex-crypto markets in the engine's resolution log by closed day, and the
  share seen before close; counts only, read at read-out, labelled a lagged partial read (the log holds only the engine's
  candidates).
- How that number differs across the declared k-visible splits, as descriptive differences with CIs.
- How long the paper position waited for the market to close, and how often the late classes occurred.

**Cannot say:**
- That anyone could earn this: no fill, queue, latency or size beyond the touch is measured; the bid-side carry has no fill.
- That the side measured is the proposed side: the status field does not name it; M1 measures the favoured side at 0.90.
- Anything about proposals not two-sided at k (about three quarters of first-seen units in CH269's span) or not seen at a
  2 h capture.
- Anything about proposals the sidecar never shows (the managed oracle's path, proposals between captures that resolve
  before the next capture), about sports or crypto, or about other windows.
- Why the discount exists (capital, attention, dispute risk): the splits are descriptive, not an identification.
- Anything a verdict test would say: it is not a test, has no null and no p-value, and is never pooled with or re-read as one.

## 14. Inputs read to write this draft (bounded; no host, network, `data-dumps` or evidence JSON)
`CLAUDE.md`, `AGENTS.md`; `CREATIVE_HYPOTHESES_2026-11-02.md` 0.3 (rules 24-27), 2 B (CH263), 3 (registration notes);
`reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`; `reviews/CH269_MAP_2026-10-30.md`; `seals/CH269_map_q0730.json`
(the `proposals_ch263`, `not_mapped`, `code_sha256` keys only); `COST_MODEL.md` 2, 3, 6, 7; `LIVE_TESTS_13.md` status block and
1.1-1.4 (structure and style); the ledger header and the rule-26 ruling entry; code read for field semantics only:
`signal_engine/labels.py` (resolution log), `signal_engine/config.py` (`RES_*`), `book_sweep.select_tokens`,
`panel.eligibility_mask`, `live_tests12_base.sweep_frame`, `census_map_ch269.py` (unit, category, tier, ladder readings).

## 15. Open questions for the challenger (riskiest first; first draft; answered by R1, see 17.3)

1. **Sweep coverage and the decision clock.** The sweep selects mid in [0.02, 0.98] with `end_date` > receipt + 3 h, so most
   M1 units may lack a sweep row. Is "decision time = latest of row, sidecar and (where present) sweep" acceptable, with
   capacity covered-subset only, or must a light dedicated book fetch for M1 units be added before the freeze?
2. **Price source.** `c` is read from the rows' touch (universal coverage) while the decision time can be minutes later
   (sweep). Should the sweep's `best_ask` be the price where present (a second source), or only a staleness descriptor?
3. **Resolution source.** Own read-out fetch (pinned parser) instead of the engine's log: acceptable? Is 0.95 of units and
   events the right floor?
4. **Headline fee line.** L1 (cost-model-v1 conservative, honours `fees_enabled`) as headline with L2 (docs rate always)
   beside, or L2 as headline given the unverified served rate 0? (At p near 0.99 the difference is under 0.05c.)
5. **The tail bound.** Is `T_U` (stratified one-sided Clopper-Pearson on events, all units of a reversed event lost) the
   right event-level bound, and should the strata be S8's or finer?
6. **Late-class bias.** Disputes settle late. Is the worst-case line plus the 2% coarse rule enough, or should the read-out be
   later (for example 45 days)?
7. **Prior-state look-back of 24 h** for E3: long enough to stop a re-proposal after a pre-window dispute entering as new?
8. **Category reader on capture k's own sidecar** (not the latest capture, as the map did): acceptable, with the map's counts kept as planning
   figures only under this difference?
9. **Thresholds of 10** (0.30c, 2%, 75%, 2,000) and the 50% capacity coverage line: set from planning arithmetic only; are
   they acceptable before J0 runs?

## 16. Proposed ledger block (DRAFT; not applied)

> ## M1 (CH263) measurement design draft, 2026-10-30 (DRAFT, nothing counted)
> - `MEASUREMENT_M1_CH263.md` second draft (R1 GO_WITH_CHANGES applied, section 17) on `feat/m1-ch263`; role `prospective_measurement` (R19 rule-26 ruling); k = 0; no
>   Holm; counted apart from registered tests. Headline: unit-weighted mean net per share after cost-model-v1 conservative
>   fee and 5% capital, ask-based `c`, event-bootstrap CI; event-level tail bound; 10 splits. Window 2026-11-24..12-14,
>   read-out on or after 2027-01-15. Next: R1 re-check, then M1-J0 (counts only).

## 17. R1 response (2026-10-30; `reviews/M1_CHALLENGER_R1_2026-10-30.md`, GO_WITH_CHANGES on draft `54fd5d49…c0d6`)

No window, registration or read-out date changed; no rule loosened; no threshold changed.

### 17.1 MUST
| Item | Fix | Where |
|---|---|---|
| 1 Catch-up look-ahead in J1 | strictly chronological processing; state at k holds only captures before k; three synthetic tests; breach = void 11.2(a) | 9.2, 11.2 |
| 2 E3 look-back 24 h | every retained pre-window capture (at least 84); J0 counts the status string's forms and transitions; residual disclosed | 2, 3.2 E3, 9.1 |
| 3 `T_U` not the bound claimed | strata = final-state units per event (1, 2-3, 4-9, 10+); level 1 - 0.05/4 each; homogeneity assumption stated; 10 largest events printed; planning updated (about 1,460 events) | 7.2, 10 |
| 4 J0 rule (c) | closed: no dedicated book fetch; capacity always covered-subset with its S6 / S7 composition, labelled not the population's | 5.3, 9.1 (c) |
| 5 Population wording | "seen at a 2 h capture and two-sided at k" in the ledger form and in 13 with the 24% and 735 / 1,735 counts; survivorship line restored (count-only, read-out); `theta_low` and `theta_W` in the same ledger line | 1 rule 1, 0, 13 |
| 6 Ruling condition 4 | handled by the ledger correction entry (2026-10-30 ~04:36Z); referenced; idea file not edited | status block, 12 |
| 7 L2 not computable | L2 = `taker_rate(..., fees_enabled=None, policy="conservative")`; fee formula wording corrected (unrounded per share) | 5 |

### 17.2 SHOULD
| Item | Fix | Where |
|---|---|---|
| 1 Column names | rows read `best_bid` / `best_ask`; `clob_token_id_1` from the sidecar | 3.1, 3.3 |
| 2 S6 `> 0.10` | labelled structurally empty, kept (cell list unchanged) | 6 |
| 3 S3 = S5 among members | stated | 6 |
| 4 S47 | restored as a disclosure (with S48) | 3.5 |
| 5 Unavailable classes by category | J0 prints them | 9.1 |
| 6 Cross-event dependence | handled only by the day-block sensitivity; stated; wider interval printed | 7.1 |

### 17.3 Designer's questions, as answered by R1
1. No dedicated fetch (MUST 4; 5.3). 2. Rows' touch is the only price source; sweep `best_ask` is a descriptor with an
agreement table on the covered subset (3.3). 3. Own read-out fetch with the pinned parser; floor 0.95 of units and events
kept (8.3). 4. L1 headline; L2 feeds `theta_low` (5). 5. Replaced by MUST 3's bound (7.2). 6. 31 days plus `theta_W` plus the
2% coarse rule kept (2, 8.2, 10). 7. Look-back extended (MUST 2). 8. Category from capture k's own sidecar kept (3.2 E5).
9. Thresholds kept; "coarse" likely, disclosed in advance (10).

### 17.4 Not verified (carried from R1; J0 or the dry run checks what it can)
Host retention, disk, cron and pass health; whether the UMA status field keeps history (J0 counts its forms); Gamma best ask
against the CLOB book (the agreement table on the covered subset); events per unit (J0); the scope of CH269's 1,552 count
(J0 by category); `labels.fetch_resolutions` batch behaviour (J3's dry run).

### 17.5 R1 re-check response (`reviews/M1_RECHECK_PREFREEZE_2026-10-30.md`, NOT_READY on `6362f3a7…9dca`)

Order kept: J0 (counts only) runs before the design-text freeze; the status block and 9.1 now say plainly that J0's only
effects are rules (a) / (b) and S2's cell list (the latter fixed by rule, so J0 only records its distribution). No threshold,
date, estimand, weight or cost line changed.

| Item | Fix (the reviewer's wording where given) | Where |
|---|---|---|
| Order (J0 before freeze; S2 "written at the freeze") | J0 declared a counts-only pre-freeze job with only the effects above; S2 no longer depends on J0 | status block, 9.1, 6, 12 |
| 1 MUST 3 planning figure | replaced with the reviewer's text (about 1,460 units at single-unit events, about 24,800 with all four strata; coarse rule 3 expected to fire); "A stratum with no final-state events contributes 0." | 10, 7.2 |
| 2 S2 constant; fee category | S2 and both fee lines use `costs.category_key(capture k's sidecar fee_category)`; S2's cells are the in-scope `CATEGORY_TAKER_RATE` keys plus `unknown`; J0 prints its distribution; exponent from `fee_schedule` where served, else 1.0; selection width now 42 cells | 5, 6, 9.1, 12 |
| 3 Chronological rule; void audit | the reviewer's `missing_capture` 6 h rule, `late_capture_ignored`, state-file refusal and per-capture sha256 chain; 11.2(a) audited from the chain | 9.2, 11.2 |
| 4 S8 "1" = S3 standalone | disclosed beside the S3 = S5 note | 6 |
| 5 Degenerate CI | "printed as degenerate; `T_U` is the bound" | 7.1 |
| Non-blocking: S6 x S9 zeros | disclosed (tick 0.01 empties (0.001, 0.005]) | 6 |
| Non-blocking: `theta_low` averaging set | the three means over the same `N_F` final-state units; labelled as mixing an estimate with a bound | 7.2 |

### 17.6 Fee-line, S4 and float fix (M2 R1 designer question 9 and SHOULD 1; ledger entry "M2 challenger R1 GO_WITH_CHANGES; M1 fee-line wording defect noted")

| Item | Fix | Where |
|---|---|---|
| L1 / L2 said "unknown giving 0.07" | corrected to `costs.py:93-104`: unknown key gives the served rate, possibly 0, where a schedule is served; 0.07 only when none is served; L2 does not bound such a unit (disclosed) | 5 |
| S4 undefined | `population_map_ch251.fee_class(...)[0]` on capture k's sidecar row, cells defined | 6 |
| "S3 unknown" (M2 numbering) | M1's fee-category split is S2: its `unknown` cell defined; M1's S3 (ladder) has no unknown cell; empty `event_id` = own one-market event and own cluster | 6, 3.4 |
| Float edges | prices rounded to 6 dp before E6, E7, S6 and S9 comparisons | 3.2 |

No threshold, date, estimand, weight or cell list changed. M1-J0 (`m1_j0.py`) applied the float edges and the empty-`event_id`
reading and was corrected with tests (it computes no fee line); its counts change only for units exactly at a 0.90 / 0.10 mid,
at an S6 edge, at a tick read with float noise, or with an empty `event_id`.

### 17.7 M1-J0 outcome (q0731; `seals/M1_J0_q0731.json`, sha256 `eedaa2b34953ab1d277572ce49c0485e6569f3524da2e3a1993647e926cd2c3d`, informed (M1-J0), counts only, k = 0)

Version `m1-j0-v2`; code sha256 `m1_j0.py` d16b1b8d…, `run_m1_j0.py` e36d7c7a…; queue job q0731, done 2026-10-30T05:41Z; peak RSS 297.6 MB.

- **Span.** 84 captures, 2026-10-22T04:31:03Z to 2026-10-30T04:31:03Z (last 8 days); the first 12 are warm-up only; 6 full UTC days
  (10-24 to 10-29); no missing slot.
- **Eligible units.** 1,232 over 740 events. Per day: 10-23 194, 10-24 85, 10-25 106, 10-26 233, 10-27 231, 10-28 192, 10-29 178,
  10-30 13 (10-23 and 10-30 are partial days).
- **Rules (a) / (b).** Median full-day eligible units 185 (threshold 100): (a) does not fire. Projected 21-day units 3,885 = 185 x 21
  (threshold 2,000): (b) does not fire. The 21-day window and all dates stay as drafted.
- **Rule (c).** Sweep-1 coverage of the favoured side's token with a finite `ask_size_1`: 9 of 1,232 units (0.73%; 10 units have any
  sweep row; by S1: lt1k 5, 1k-10k 1, 10k-100k 3, ge100k 0; by S7: future 8, missing 1, past <= 24 h 0, past > 24 h 0). Capacity
  therefore remains a covered-subset print only, as declared in 9.1 and 5.3.
- **Funnel (3.2, market-capture rows with a `propos` status at k).** unit 1,232; out of scope sports 200,104; already proposed 19,694;
  disputed at k 4,449; not two-sided 3,923; no k-1 row 1,350; out of scope crypto 292; contested 83; no previous capture 0;
  not open at k 0; prior proposal state 0; out of scope unknown 0.
- **Cells S1-S10 (units).** S1 lt1k 287, 1k-10k 569, 10k-100k 370, ge100k 6. S2 as in 6 (other 997, unknown 223, economics 6,
  politics 3, culture 2, weather 1, others 0). S3 standalone 171, member_winner 976, member_loser 85. S4 fee_free 1,220, fee_on 12.
  S5 YES 1,147, NO 85. S6 `c <= 0.001` 1,195, (0.001, 0.005] 27, (0.005, 0.01] 6, (0.01, 0.03] 4. S7 future 521, past <= 24 h 631,
  past > 24 h 79, missing 1. S8 members 1: 171, 2-5: 327, 6+: 734. S9 tick 0.001: 1,221, 0.01: 11. S10 days 1-7: 1,219, days 8-14: 13.
  S6 x S9: `c <= 0.001` at 0.001 1,184 and at 0.01 11; (0.001, 0.005] at 0.001 27; (0.005, 0.01] at 0.001 6; (0.01, 0.03] at 0.001 4.
- **Status forms.** 37 distinct normalised forms of `uma_resolution_statuses`, no row overflow of the form list; 5,081 rows carry
  both `propos` and `disput`. Transitions between consecutive captures: empty -> proposed 229,651; empty -> disputed 70;
  proposed -> disputed 67; no proposed -> empty and no disputed -> proposed transition appears in the output.
- **Unavailable classes by category (E5's category at k).** `no_k_minus_1_row`: sports 1,119, crypto 216, non-sports ex-crypto 15;
  `no_previous_capture` 0.
- **Receipt gaps.** Sidecar minus row: n 1,232, min / median / p90 / max all 0.0 s. Sweep minus row: n 10, min 144.2 s, median 410.2 s,
  p90 486.2 s, max 487.3 s.
- **Engine resolution candidates.** 939 of 1,232 units are in the engine's `res_candidates` (membership only; no resolution value read).
- **T_U units per event (every unit treated as final-state; counts of events).** 1 unit: 586; 2-3: 94; 4-9: 48; 10+: 12.
- **Other.** Open binary sidecar rows missing: 0; `prior_proposal_state_gap`: empty.

No estimand, split, cell, threshold, cost line or date changed from J0.
