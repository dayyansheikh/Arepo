# Measurement M1 (CH263, "the carry"): the favoured side's discount after a UMA proposal state is first seen, against the reversal tail and the recorded cost, held to resolution, k = 0 (DRAFT)

**Status: DRAFT 2026-10-30, first draft, not frozen, not registered, nothing counted.** Evidence role
`prospective_measurement` (rule 26 of `CREATIVE_HYPOTHESES_2026-11-02.md` 0.3; role and conditions set by the binding
ruling `reviews/R19_RULE26_MEASUREMENT_RULING_2026-10-30.md`, ACCEPT_WITH_CONDITIONS). Drafted on branch `feat/m1-ch263`
from the `chore/arepo-claude-setup` tip `c0818dfe`, a design-only commit. No M1 code, no queue file, no seal, no host read.
Before anything is sealed this needs, in order: a challenger review (`science-reviewer`) of this text, the designer's
response, the counts-only pre-window check of 9.1 (its decision rules are declared in this text before it runs), a final
pre-freeze verification, the design-text freeze commit (sha256 in the ledger), the code, a code-freeze check on synthetic
data, a host dry run with peak RSS, and the registration commit (spec and code pins plus the ledger block of 16) at least
24 h before `REGISTERED_UTC` (section 2). Until the pins exist, every line a reader writes is `prospective_unregistered`.

This is research tooling. AREPO never trades. M1 is a measurement: it reads a resolution as the declared payoff of a
paper route after the window, it is not a verdict, it is not part of any Holm family, it is counted apart from the
registered tests (it is not part of round 19's "about 1.8 registrations"), and no sentence in this file is a claim that the
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
  reversal bound `T_U`; the worst-case line for non-final units; ten k-visible splits; capacity at the touch; the wait;
  the bid-side quoted carry (gross, no fill).
- **Window** 2026-11-24T00:00Z .. 2026-12-15T00:00Z (21 days, last day 12-14); **read-out on or after 2027-01-15T00:00Z**
  (31 days after the end); analysis on or after 2027-01-15T12:00Z. Freeze deadlines in section 2.
- **Planning.** CH269: 821 first-seen proposal units a day (median full day, non-sports ex-crypto), of which about 24% had a
  readable side (1,518 readable / 103 two-sided unread / 4,623 not two-sided over the map's 6,244 units): about 200
  eligible units a day, about 4,200 in 21 days. Events among them and sweep-1 coverage are **not mapped** (9.1).

## 1. Common rules carried over (binding from the first draft)

1. **Wording.** Estimands are definitions, never directional hypotheses. The only ledger form is: "measured (prospective,
   k = 0): <estimand> = X [95% CI], cost-model-v1, conservative fee, touch, size-unlimited, capacity Y." Words not used in
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
  prior-state look-back (3.2, rule E3) reads the 12 captures before `REGISTERED_UTC` as raw sidecars only (counted
  `pre_window_source`).
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
- **Captures** `snapshots/<id>/rows.csv.gz` (manifest `state=complete` only): `market_id`, `event_id`, `binary`, `bid`, `ask`,
  `spread`, `closed`, `active`, `end_date`, `liquidity`, `clob_token_id_0`, the token id of outcome 1, `received_utc`; the
  manifest start.
- **Sidecar** `snapshots/<id>/rows_ext.csv.gz`: `received_utc`, `uma_resolution_statuses`, `accepting_orders`, `fee_type`,
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
- **E3 One-shot.** No proposal or dispute state for the market in any capture since the look-back start (12 captures before
  `REGISTERED_UTC`), and no earlier M1 unit for the market. Else `prior_proposal_state` (a re-proposal after a dispute is
  never a new unit).
- **E4 Open at k.** `binary = 1`, `closed` false, `active` true, `accepting_orders` not false. Else `not_open_at_k`.
- **E5 Scope.** Capture k's sidecar row exists (else `sidecar_missing`) and its category, by the CH269 map's reader
  (`boundary_map_ch240.category_of(fee_type, fee_category, series_slugs, True)`) applied to **capture k's own sidecar row**
  (not the latest capture, as the map did), is `nonsports_excrypto`. Else `out_of_scope_<category>` (sports and crypto
  counts printed).
- **E6 Two-sided at k.** `0 < bid < ask <= 1` on the row at k. Else `not_two_sided`.
- **E7 Readable side.** `mid_k = (bid + ask) / 2`; the favoured side is YES if `mid_k >= 0.90`, NO if `mid_k <= 0.10`.
  Else `contested` (counted class, its own c reported descriptively in 8.2; never folded into the headline).

### 3.3 Unit fields and decision time
- **Price on the favoured side** (rows' touch at k): YES: `ask_f = ask`, `bid_f = bid`; NO: `ask_f = 1 - bid`,
  `bid_f = 1 - ask`. `c = 1 - ask_f`. Recorded beside it: `mid_f`, `h = (ask - bid) / 2`, tick.
- **Sweep fields** (for capacity and a staleness descriptor only): sweep 1's row for the favoured side's token (outcome 0 for
  YES, outcome 1 for NO): `ask_size_1`, `best_ask`, `depth_ask_1c`, `batch_receipt_utc`. Absent row or non-finite
  `ask_size_1`: `sweep_uncovered` (capacity unavailable; the unit stays in every other estimand).
- **Decision time** `t_d` = the latest of the row's `received_utc`, the sidecar row's `received_utc` and, where present, the
  sweep row's `batch_receipt_utc` (the ruling's rule). The gaps (sidecar minus row, sweep minus row) are recorded.
- **Unit record.** Everything above plus `event_id`, the event's open binary member count at k, `end_date`, tier, category,
  fee fields and the two fee lines of 5, the raw status strings at k and k - 1, capture ids, `spec_sha`, `code_sha`. Nothing
  from after capture k.

### 3.4 Cluster
The cluster is the Gamma `event_id` at k (a ladder proposed together is one cluster, however many members become units).
No cap: weights are declared instead (4).

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
- **Fee, two lines,** per share at `p = ask_f` by `costs.taker_fee_ps` (formula `rate * p * (1 - p)`, 5 dp rounding as the
  model does), from capture k's sidecar fields:
  - **L1 (headline):** `costs.taker_rate(category, schedule_rate, fees_enabled, policy="conservative")`, i.e. max(served
    schedule, docs table), fees disabled giving 0, unknown giving 0.07.
  - **L2 (docs-rate bound):** the docs category rate (`COST_MODEL.md` 2: 0.04 finance / politics / mentions / tech; 0.05
    economics / culture / weather / other; geopolitics 0) applied **whatever `fees_enabled` says** (the ruling's "not
    verified: whether the venue charges the rate 0 it serves"). At `p = 0.99` this is at most about 0.05c a share.
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
[0.02, 0.98] and `end_date` more than 3 h after receipt (`book_sweep.select_tokens`, `panel.eligibility_mask`), so many M1
units may be `sweep_uncovered` by construction. If coverage is below 50% of eligible units, capacity is printed as
"covered subset only (coverage X%)". Capacity never selects or weights a unit.

## 6. Splits (complete list; every one reported; all k-visible)

Each cell reports `N` units, events, final-state count, mean `c`, `r_eff`, mean fee (L1), mean capital, `theta` with its
event-bootstrap CI, and the non-final class counts. Cells with fewer than 30 final-state units or 10 events print their
numbers labelled `thin` (never suppressed).

| # | Split | Cells |
|---|---|---|
| S1 | liquidity tier at k (CH269's `tier_of`) | lt1k, 1k-10k, 10k-100k, ge100k, tier_na |
| S2 | category at k (E5's reader) | each category returned inside scope, plus unknown |
| S3 | ladder position at k | standalone (event has one open binary market), member_winner (favoured side YES), member_loser (favoured side NO) |
| S4 | fee class at k | fee_free, fee_on, unknown |
| S5 | favoured side | YES, NO |
| S6 | price zone `c` | `c <= 0.001`, (0.001, 0.005], (0.005, 0.01], (0.01, 0.03], (0.03, 0.10], > 0.10 |
| S7 | scheduled end at `t_d` | end in future, past <= 24 h, past > 24 h, missing |
| S8 | event member count at k | 1, 2-5, 6+ |
| S9 | tick size at k | 0.001, 0.01, other / missing |
| S10 | window week | days 1-7, 8-14, 15-21 |

Hours to liveness end is **not** a split: the sidecar carries no proposal time (CH269 `not_mapped.proposal_time`).

## 7. Inference

### 7.1 Event bootstrap (headline and every CI)
Resample events with replacement (all of an event's final-state units together), B = 10,000, `numpy.random.default_rng(
20261124)`, percentile 95% interval; the same draws serve every component and split (a split's CI resamples its own events).
Sensitivity printed beside the headline only: a block bootstrap over the 21 UTC days (same B and seed). No p-value, no test.

### 7.2 The reversal tail, bounded at event level
A ladder proposed together can reverse together, so units are not independent draws. Declared:
- **Event reversal indicator** `I_e = 1` if any final-state unit of event e has `L > 0`. Reported: events with
  `I_e = 1` / final-state events, separately for losses and splits.
- **Event-level bound.** In each S8 stratum s (member count 1, 2-5, 6+), the one-sided 95% Clopper-Pearson upper bound
  `p_U,s` on the event reversal rate. The **unit-level tail bound** is `T_U = sum_s (N_s / N_F) * p_U,s`, which bounds the
  unit-weighted expected loss share under the worst case that every unit of a reversed event loses its full stake, with
  reversal probability allowed to differ by stratum (event size). `T_U` is reported in cents a share beside `r_eff`.
- **The conservative read** `theta_low = mean c - T_U - mean fee (L2) - mean capital` is printed beside the headline,
  labelled as a bound, not an estimate.

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
- Reads the last 8 days of sidecars, rows and sweep 1 on the host. Applies 3.2 and 3.3 exactly as specified and prints
  **counts only**: eligible units a day; events among eligible units and the member-count distribution (S8); the class
  funnel of 3.2; the cells of S1-S10 (counts, no prices beyond the k-time `c` zone counts of S6); **sweep-1 coverage of the
  favoured side's token with a finite `ask_size_1`** (the item CH269 did not map), overall and by S1 and S7; the receipt gaps
  (sidecar minus row, sweep minus row: median, p90); the share of units whose market is in the engine's resolution
  candidates (a count of the engine's state file, no resolution value).
- **Decision rules declared now:** (a) eligible units fewer than 100 a day (median full day): window extended to 42 days
  (CH263's line), dates rewritten before the freeze; (b) fewer than 2,000 eligible units projected over 21 days: extended
  to 42 days; (c) sweep coverage below 50%: capacity printed as covered-subset only (5.3), and the challenger is asked
  whether a light dedicated book fetch for M1 units is added before the freeze (15); (d) none of J0's numbers changes an
  estimand, split, cost line or threshold. Output labelled `informed (M1-J0)`, counts only, sealed with its code hash.
- Memory: under 600 MB (CH269's 8-day map peaked at 558.8 MB over a wider read); dry run measured.

### 9.2 M1-J1: window-time extractor (every pass; catch-up allowed within retention)
- After each pass, for each complete capture k in the window not yet processed: read captures k - 1 and k (rows and sidecar,
  `usecols` only) and sweep 1 of k; apply 3.2; write `units/<capture_id>.jsonl.gz` (unit records of 3.3) and
  `status/<capture_id>.json` (the funnel counts, the capture's completeness, the sweep's presence). Idempotent per capture;
  refuses to overwrite; every line carries `spec_sha`, `code_sha` and role `prospective_measurement`.
- Keeps only a small state file (market ids with any proposal or dispute state seen since the look-back start) between runs.
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
reversals the bootstrap CI narrows to the spread of `c` and `T_U` (about 3 / events) carries the tail, which needs about
1,000 final-state events to reach 0.30c. Round 19's "net to +-0.1c at 5,000 units" left out the variance of `L` and is not
used.

## 11. Void conditions

M1 is **void** (recorded in the ledger, its numbers not reported as a measurement) if any of:
1. any change to an estimand, weight, split, cost line, class rule, threshold or the read-out date after `REGISTERED_UTC`;
2. any read of a resolution, label, Gamma outcome field or any data from after a unit's k before `READOUT_UTC` (the J1
   extractor's causality test and the J2 manifest are the checks);
3. unit selection that uses information from after k;
4. resolution-source coverage below the floor of 8.3;
5. unit lines whose `spec_sha` or `code_sha` differs from the pins making up more than 1% of the units (below that they are
   dropped, counted);
6. the window started before the registration commit plus 24 h.

## 12. Later tests on the same object, and counting

- A later verdict test on the carry, the proposal window, the favoured side's discount or any S1-S10 cell is labelled
  **`informed (M1)`**, uses a window that starts after `READOUT_UTC` (disjoint and later), and counts none of M1's data as its
  evidence.
- If it targets a split or cell chosen after seeing M1, it reports M1's selection width: **10 splits, 32 declared cells plus
  S2's** (S1 5, S3 3, S4 3, S5 2, S6 6, S7 4, S8 3, S9 3, S10 3; S2's cell list is fixed from J0's category counts and
  written at the freeze).
- M1 may set planning SDs and population counts for a later design; it never sets a threshold after the fact.
- M1 is in no Holm family, is counted separately from registered tests, and does not change any verdict.

## 13. What this measurement can and cannot say

**Can say (allowed wording):**
- "Measured (prospective, k = 0): over N units in E events, the mean discount of the side priced at 0.90 or more at the first
  capture showing a UMA proposal state was c [CI]; the share lost or split, weighted as r_eff, was r [CI], bounded at event
  level by T_U; the mean net per share after the cost-model-v1 conservative fee and a 5% capital charge was theta [CI],
  touch, size-unlimited; capacity at the touch Y (coverage Z%)."
- How that number differs across the declared k-visible splits, as descriptive differences with CIs.
- How long the paper position waited for the market to close, and how often the late classes occurred.

**Cannot say:**
- That anyone could earn this: no fill, queue, latency or size beyond the touch is measured; the bid-side carry has no fill.
- That the side measured is the proposed side: the status field does not name it; M1 measures the favoured side at 0.90.
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

## 15. Open questions for the challenger (riskiest first)

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
> - `MEASUREMENT_M1_CH263.md` first draft on `feat/m1-ch263`; role `prospective_measurement` (R19 rule-26 ruling); k = 0; no
>   Holm; counted apart from registered tests. Headline: unit-weighted mean net per share after cost-model-v1 conservative
>   fee and 5% capital, ask-based `c`, event-bootstrap CI; event-level tail bound; 10 splits. Window 2026-11-24..12-14,
>   read-out on or after 2027-01-15. Next: challenger review, then M1-J0 (counts only).
