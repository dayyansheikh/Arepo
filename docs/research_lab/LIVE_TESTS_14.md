# Live tests 14 (LT14): the engine at the touch (CH262; the label-origin gross), DRAFT pre-registration

**Status: DRAFT, second draft (2026-10-30 05:49 UTC+1).** This draft applies challenger R1
(`reviews/LT14_CHALLENGER_R1_2026-10-30.md`, GO_WITH_CHANGES, on first-draft sha256 `9012d0d0…d47d`). Every item is mapped in
section 12. Not frozen, not registered; E-numbers unassigned; nothing counted; no LT14 code, seal or census run. Drafted on
branch `feat/live-tests-14` (first draft `60bca07f`; this draft on the tip `c2ec0a16`), design-only. LT14 takes the next
free E-number at its own registration. If its primary drops at the census, LT14 is not registered (a ledger line;
nothing counted).

Before registration it needs, in order:
1. A re-check of this draft and a final pre-freeze verification (`science-reviewer`).
2. **The design-text freeze commit, before 2026-11-07T00:00Z (hard deadline, 1.1).** The commit records:
   - the sha256 of this file in the ledger;
   - the pinned model `P`, by `model_id` and `spec_sha256`;
   - `P`'s input-clock audit (1.3).

   The same commit files the `attrlimit_lt14` request (5).
3. The census code (3), with a `science-reviewer` code-freeze check on synthetic data.
4. The seal (once, after the census span and its lag slots end), then the counts-only census (once).
5. Only if the primary survives the census:
   - the size-check and analysis code;
   - a second code-freeze check;
   - the size check (1.9);
   - a host dry run with peak RSS measured;
   - the pins;
   - the ledger entry, at least 24 h before `REGISTERED_UTC`.

Until the pin exists, every line a reader writes is `prospective_unregistered`.

This is research tooling. AREPO never trades. **No claim is made or implied about tradability, calibration, profit or a
lasting market advantage.** LT14 measures one number, the **label-origin gross**: the pinned model's top-decile 2 h mid move
in the direction it predicted, from the mid the engine recorded at capture k (the engine's label origin) to the mid it
recorded at capture k + 1. **It starts before the prediction exists, and it is not an executable entry.** It is set against
declared cost hurdles from `COST_MODEL.md`. "At the touch" in this file always means this label-origin gross, compared
with touch-based costs. Every count quoted from round 19, the CH269 map, the cost model or the ledger is a counts-only
operational or development figure, never a target. Every MDE is a planning estimate. Writing this file read no host,
network, `ssh` or `data-dumps` data, and no prediction value, target, mid after an origin, outcome or P&L (reads: 9).

**What the CH269 map says, and what it does not (R1 MUST 5-6; ledger 2026-10-30 ~04:47Z, referenced, not duplicated).** The
map (`reviews/CH269_MAP_2026-10-30.md`, `seals/CH269_map_q0730.json` section `champion_top_decile_ch262`; 104 engine
captures, 10-21T12:31Z..10-30T02:31Z, `se0_champion_lr_mm`) counted the decile of **signed** `s` (up calls only;
`census_map_ch269.py:843`), with the engine's own `category` as scope (`:709`). It did not count CH262's object (the `|s|`
decile with the pinned sidecar classifiers). The ledger records this as "**LT14 drafted on a defective count; |s| line
unmeasured**". The map's recorded outcome stands; nothing is relabelled. **The binding `|s|` count gate (>= 100 units a
capture) is LT14's own census line (3).** No re-read of the CH269 inputs is planned. If one is ever made, it is declared in
the ledger first, labelled *informed (CH269 re-read)*, and changes no declared value.

The signed-decile counts (planning only, a different object) were:
- 10k-100k tier: median 175 a capture (p25 140, min 95, mean 172.2); median-to-mean ratio 1.02; busiest slot of day 10.2%;
- >= 100k tier: median 0, mean 0.78 a capture;
- runs average 1.84 captures; 16,934 distinct markets;
- k + 1 unavailable share, top decile minus rest, by tier: 0.16 points (10k-100k), 0.34 (1k-10k), 0.20 (< 1k), 1.24
  (>= 100k).

The map's fee-class split (1,059 units) is a defect: `:951-952` overwrote each capture's totals, so only the last capture
survives (ledger). LT14's census code sums across captures, with a unit test (3, 6). The map's span is disjoint from LT14's
census span `[2026-11-07, 2026-11-17)`. Values near a map number are marked [map] (4, 9.1).

Source idea: `CREATIVE_HYPOTHESES_2026-11-02.md` (round 19), CH262 (section 2 A; sections 1 and 3's LT14 lines). This file
is written to the design rules of rounds 14-19 (rules 1-27; rule 27 binds directly), LT4's L1-L15 and the rulings LT7-LT13
carry. It reuses `LIVE_TESTS_13.md`'s conventions unless a line here says otherwise and why.

## 0. Summary

| Handle | Hypothesis (one-sided) | Unit (dependence) | Primary | Planning MDE (DE 5 / DE 31); quarter; F-MDE | Hurdle `H` |
|---|---|---|---|---|---|
| **CH262** (10k-100k) | Over the window, the mean **label-origin gross** `g` of the pinned model `P`'s top `\|s\|` decile in the 10k-100k tier **exceeds 1.30c**. Here 1.30c = `2 x (AS - h) - rebates` with h = 1.34c from F4 / F5's mean spread of 2.68c (`COST_MODEL.md` 5). With the tier's own p50 half-spread (0.75c) the same formula gives **2.48c**, which is printed beside every result (1.8). | in-scope eligible market x capture in the top decile at k; **cluster: event**; two-way event x UTC day; UTC day | the mean of `g` minus `H`, cluster-robust; `H1: E[g] > H` | `\|s\|` decile **unmeasured**. At the signed decile's 175 a capture [map]: **0.081c / 0.20c**; quarter 0.16c / 0.40c; F 0.13c / 0.32c (SD 1.3c; all double at 2 x SD) | **1.30c** |

- **Family:** one Holm family, **k = 1** (R1 SHOULD 1), one-sided, alpha 0.05. With one test, Holm is the unadjusted p. The
  family is separate from E009-E011, LT2-LT13, E025, E026 and M1 / M2.
  - The **>= 100k tier is a reported arm** (M5), not a primary. Its 0.50c is a half-spread, not a round-trip hurdle; it
    fails its count line on the signed map (mean 0.78 a capture against 10); and it fails its F-MDE line even at 10 a
    capture (2).
  - The < 1k and 1k-10k tiers are reported arms.
  - A primary that drops at the census is `census_dropped` (uncounted, final); a failed coverage check is `census_unavailable
    (coverage)`; a failed input-clock audit is `withdrawn_pre_census (input clock)` (1.3). No replacement test.
- **Window, parallel lane (R1 open question 1: accepted, disjoint objects):** `REGISTERED_UTC` **2026-12-10T00:00Z**,
  `END_UTC` **2026-12-31T00:00Z**, single analysis on or after **2027-01-01T12:00Z**, beside LT12's window. The reader runs
  under the host's heavy-job lock convention. December thinning (thin books from 12-24) is disclosed (1.1).
- **Window, ordered lane (fallback):** 2027-02-12T00:00Z..2027-03-05T00:00Z; analysis on or after 2027-03-06T12:00Z.
- **Census:** on the engine's files (and the span's sidecars for scope and fee fields) of `[2026-11-07T00:00Z,
  2026-11-17T00:00Z)`, origin-side only. Label: **census span shared with LT12** (LT14 reads no LT12 output; R1 SHOULD 4).
- **Labels certain in both lanes:** *census span shared with LT12*; *informed (CH269)* (the signed-decile counts were seen).
- **Honest priors (7):**
  - **P(census) 0.65**, lowered from 0.80 by R1 MUST 6: the only count behind the drafting is of a different object;
  - **P(no LT14 test) about 0.35**, plus about 0.05 for a missed freeze deadline;
  - given registration, P(Supported) about 0.08 and P(Contradicted) about 0.75.
- **Expected answer:** the label-origin gross is a few tenths of a cent, grows with the spread, and lies below 1.30c. Even a
  gross above 1.30c would sit below the tier-spread figure of 2.48c unless it were very large. A Supported primary is an
  exploratory prospective finding about the label-origin gross. It is not an executable return. At most it nominates a
  separately registered design with entries at or after the decision time and fills measured on the signal.

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)
`LIVE_TESTS_13.md` 1.0 applies unless 1.8-1.10 say otherwise. That covers:
- exact `%.17g` writes; NaN refusals; sealed inputs re-hashed; slots from the seal;
- the pessimistic MDE gate `max(declared, design)`; size check >= 2,000 worlds, limit 0.058;
- spec and code pins; write-once series;
- clustering by the cluster unit, cluster x UTC day and UTC day, p the largest; Holm counted once;
- economics never changes a verdict;
- `DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)`;
- the lag-slot loader; `T_X` conditions; the pinned sports and crypto classifiers; LT7's one-rule F, binding fixed now;
- distinct-cluster gates unprojected; `census_unavailable (coverage)` distinct from `census_dropped`; Kish `G_eff >= 15`;
- NaN draws count as exceedances; untestable worlds count as rejections;
- `analyze --out` required, never overwrites; dry runs before the pin logged;
- **LT13's pivoted-QR aliasing rule** (3.3 there; used here by M6, 1.11).

Round 19's rules map onto LT14 as follows:

| Rule | LT14 |
|---|---|
| 1. Panel-complete units | engine stores of complete captures only; no sweep, trade sample or monitor print |
| 3. Innovations, not levels | **not applied, disclosed:** the primary is a level against a constant (round 19 4.1) |
| 5. Field semantics first | 1.3 (pin, input clock), 1.5 (columns, bits, scope, tier), 1.6 (status codes) |
| 7. DE and kill lines | `DE_gate` as 1.0; kill lines (3) |
| 8. Floors | 0.5c mid floor on the MDE and the F-MDE (3); `H` is the tested constant |
| 11. Economic check | this test is the economic check of the engine's `dir_2h` claim, on the label-origin gross |
| 19. No resolution read | none read; a market closed at k + 1 is `unavailable_closed` |
| 25. Zone floors | tick 0.001 units reported as an arm |
| 27. Engine stores as inputs | only `P`'s files at its pinned spec; capture <= k for every input; `P` stopping -> `unavailable_spec`, never filled; no new column, family or model |

### 1.1 Registration, lanes, single analysis
- **Freeze deadline (R1 SHOULD 8): the design-text freeze commit is before 2026-11-07T00:00Z.** That way `P` is pinned
  before any census-span file exists. If the deadline is missed, LT14 is recorded `not registered (freeze deadline
  missed)`. Any later attempt is a new design round with its own census span. No lane uses the 11-07..11-17 span after a
  late freeze.
- **Parallel lane.** `REGISTERED_UTC` is the first 00:00Z at least 24 h after the registration commit and never earlier than
  2026-12-10T00:00Z. That gives a proposed window of 2026-12-10..12-31, with the analysis on or after
  `END_UTC + 36 h` = 2027-01-01T12:00Z.
  - R1 accepted that LT14 and LT12 may share these days. LT12 reads same-event spread innovations and sibling shocks; LT14
    reads `P`'s prediction against the row's own next mid.
  - The markets can overlap: the census prints the share of LT14 units in two-member neg-risk events. No LT12 object is
    computed.
  - The LT14 reader and any LT14 job take the heavy-job lock convention and never run beside a memory-heavy job.
- **Ordered lane (fallback).** It applies if the registration commit is not at least 24 h before 2026-12-10T00:00Z.
  `REGISTERED_UTC` is then the first 00:00Z at least 24 h after the later of LT13's fast-lane `END_UTC` (proposed
  2027-02-11T00:00Z) and the registration commit, never before 2027-02-12T00:00Z. The window is 21 days; the analysis is
  >= 36 h after its end. The census stands unchanged, because it reads no target. A pin after `T_LT12` adds
  *informed (LT12)*.
- **Adjacent analyses** (`T_X` = the earlier of X's analysis job start and its commit):

  | Adjacent | Why | Consequence |
  |---|---|---|
  | LT12 census (`T_LT12c`, about 11-18) | the same span (engine files and sidecars only) | *census span shared with LT12*; no LT12 census output read by any LT14 designer |
  | LT12 (`T_LT12`, about 2027-01-01T12Z) | same days (parallel lane) | none in the parallel lane; ordered lane *informed (LT12)* |
  | LT13 (2027-01-21..02-11) | the ordered lane follows it | time only |
  | LT11, LT10, E026 (to 12-07), E015, E022, M1 / M2 | time or different states | none computed; no E026 frozen file edited |
  | The engine's leaderboard (`dir_2h` log loss) | a public accuracy measure of the same predictions | not a cents measure; never an LT14 input or result |
- **Boundary.** The first origin is the first capture starting at or after `REGISTERED_UTC`. The last origin is the last
  capture starting before `END_UTC`; its k + 1..k + 3 are read through the lag-slot loader.
- **Freeze, fixed end, one analysis:** as LT13 1.1. `run_live_tests14.py analyze` refuses before the analysis date, requires
  `--out` and never overwrites. `k_tests`, `dropped_tests` and `census_unavailable` are mutually exclusive.
- **Time of year (disclosed).** The parallel window holds the December holidays (thin books from about 12-24, fewer
  in-scope units, possibly larger moves per unit). No correction is made; the Unavailable floors catch a collapse. There is
  no DST change in any span.

### 1.2 Stores read (already written by the pass and the engine's tick; no new collector, no network)
- **Engine stores** (`signal_engine/`, write-once; verified read-only in `predict.py`, `labels.py`, `features.py`,
  `specs.py`, `config.py`):
  - `predictions/<capture>/<P>.parquet`. Rows are aligned with `features/<capture>.parquet` (same order). Its columns:
    - `elig` (uint8 bit mask, `config.ELIG_BITS`: `dir_2h` = 1, `dir_6h` = 2, `dir_24h` = 4, `res_7d` = 8; target eligibility
      only, i.e. the scheduled end after the target slot or unknown, `labels.elig_mask`);
    - **`dir_2h_dn`, `dir_2h_up`** (uint16 = `floor(clip(p, 0, 1) x 65535)`);
    - `dir_6h_dn`, `dir_6h_up`, `dir_24h_dn`, `dir_24h_up`, `res_7d_yes`.

    The file metadata holds `spec_sha256`, `fit_id`, `features_sha256` and `aux_sha256`. Rows with the bit unset hold 0.
  - `logs/predictions-YYYYMMDD.jsonl`: the first valid line per (capture, `P`) gives `written_utc` (the **receipt time**),
    `spec_sha256`, `fit_id` and `sha256` of the file.
  - `quotes/<capture>.parquet`: `market_id`, `t_off` (row receipt minus capture start, s), `bid`, `ask` (open two-sided rows
    only), `st` (0 open two-sided, 1 closed, 2 inactive, 3 otherwise not two-sided).
  - `features/<capture>.parquet`: `market_id`, `event_id`, `category`, `t_row`, `end_ts`, `ms_mid`, `ms_spread`,
    `ms_log_liq`, `ms_hours_to_end`, `ms_rv24`, `ms_tick`, `ms_neg_risk`, `mo_d2h`. Its rows are the markets that pass base
    eligibility (`features.eligibility`: `panel.eligibility_mask` rules plus no UMA proposal).
  - `meta/<capture>.json` (slot, capture start and finish, sha256s); `specs/registry.json` (`P`'s `spec_sha256` and
    `status`); `champion/history.jsonl` (champion changes, disclosure only).
- **Capture sidecar** `rows_ext.csv.gz`: `fee_type`, `fee_category`, `series_slugs` (scope classifiers), `fee_schedule`,
  `fees_enabled` (the served-fee cost line). Never a state or target. In the window these are extracted on arrival (1.14);
  in the census they come from the sealed span (sha256-checked LT12 / LT13 copies accepted).
- **Not read:**
  - snapshot `rows.csv.gz` prices; sweeps; trade samples; the monitor; `cross_venue_live/`, `xv_quotes/`, `surprise_live/`;
    `aux/`;
  - the label store and label logs; `leaderboard/`; `dashboard.json`; other models' predictions;
  - `live_tests2/`..`live_tests13/`; map outputs beyond the bounded CH269 section named above; Gamma outcome fields.
  - No LT11-LT13 or M1 / M2 object is computed. J4-R and CB13-T's holdouts are untouched.

### 1.3 The pinned model `P` (pinned `P` only; R1 SHOULD 8)
- **Definition.** `P` is the model `champion/history.jsonl` records as champion at the design-text freeze commit (before
  2026-11-07T00:00Z). The frozen text pins it by `model_id`, `spec_sha256` and `FEATURES_VERSION`. Every sentence of this
  file speaks of "the pinned `P`", never of "the current champion".
  - Today that would be `se0_champion_lr_mm`.
  - The first `se-promotion-v2` read is due about 11-04, so `P` could instead be se1 / se17 / se18 if a promotion lands
    before the freeze.
- **Input-clock audit at the freeze (R1 MUST 2; binding).** The freeze commit lists every feature family and derived set in
  `P`'s spec, with its source stream, its receipt clock and the code line that reads it. **Every input must be received at
  or before the unit's own row receipt `t_row(i)` at capture k.** 'Received' is the receipt clock of the record read (fetch
  time), not its venue event timestamp. If any input fails, the reader refuses `P`, and LT14 is
  `withdrawn_pre_census (input clock)`, never re-pinned to another model.
  - The `book` family fails by construction: its sweep is received about 7 min after the origin (`DESIGN_V1.md` 3, 21:
    "can be credited for a move that has already happened").
  - `flow` and `wallet` read the pass's trade sample, which is fetched after the capture. The designer's reading is that
    they fail; the audit rules.
  - `xvenue` (quotes received before the capture start) and `book0` (a book strictly before the origin) are audited on
    their code.
  - **Pre-audit (designer, read-only, for the reviewer to check at the freeze):**
    - `market_state` and `momentum` read capture k's own row, earlier `quotes/` files, and sidecar fields.
    - `ext_sidecar.py` derives the sidecar from the same Gamma page bodies as the row, with the same `received_utc`.
    - So se0, se1 and se17 (market_state + momentum only) appear to pass.
    - se18 (`lgbm_all_b0`) holds `flow` and `wallet` and would appear to fail.
- **The deployed object.** `P` is read at its pinned spec with its own walk-forward refits (`DESIGN_V1.md` 5).
  - Fit ids are recorded per file, and the per-day decile composition is printed.
  - A file whose `spec_sha256` differs from the pin is `spec_mismatch` (counted; its units `unavailable_spec`).
- **Champion changes during the census span or window (declared rule).** LT14 reads **`P` only**.
  - A promotion or demotion is recorded with its capture under the label *champion changed in window* and never changes a
    verdict.
  - Every model with `status: active` in `specs/registry.json` writes predictions (`specs.active_models`, `predict.py`);
    promotion does not change a model's status (`promotion.py` sets none). So a demoted `P` keeps writing.
  - If `P` stops writing (status not active), later units are `unavailable_spec`, never filled from another model. Under 80%
    file coverage, the result is Unavailable (1.10).
  - An embargo entry added for `P` does not stop LT14's reading, and no LT14 number is displayed (5).
- No LT14 line promotes, demotes or refits a model.

### 1.4 Clocks, slots and the decision time
- **Slots:** as LT3-LT13 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). Missing
  slots stay NaN (counted).
- **Decision time:** `P`'s file receipt time for capture k (`written_utc`). All state inputs are at capture k or earlier.
- **On time:** a unit exists only if `P`'s file for k was logged before slot k + 1's time (the engine's rule). Otherwise the
  whole capture is `late` (counted).
- **Horizon rule (S45):** `t_row(k + 1) = start(k + 1) + t_off(k + 1)` minus `t_row(k)` must lie in 2 h +/- 15 min. Otherwise
  the unit is `unavailable_timing`.
- **Start point (R1 MUST 1).** `g` starts at capture k's recorded mid, the engine's label origin, at `t_row(k)`. That is
  earlier than the decision time, so **`g` is the label-origin gross; it starts before the prediction exists and is not an
  executable entry.** No quote at or after the decision time exists in the engine's stores; none is taken from another
  stream. R1 rules no latency exclusion.
- **Latency (R1 SHOULD 3).**
  - Capture-level latency `L_c = written_utc(P, k) - finish(k)` (`meta/`). `L` hardly varies within a capture, so the
    sensitivity splits **captures**, not units.
  - The sensitivity is the primary refitted on captures with `L_c` at or under the census median of `L_c` (census-fixed).
  - Within-capture `t_off` quantiles are printed separately.
  - **Label *latency-sensitive* (numeric trigger):** set if (a) the primary's `gbar` exceeds `H` and the sensitivity's
    `gbar` does not, or (b) `|gbar_sens - gbar| > 0.25c`. Never a verdict change.

### 1.5 Eligibility at <= k, the unit and the order of exclusions (R1 MUST 7)
Everything below is read at capture k or earlier.
- **Columns.**
  - `s = (dir_2h_up - dir_2h_dn) / 65535`, from the stored uint16 values, never recomputed or renormalised (the engine's
    scored probabilities clip at 1e-6 and renormalise, `predict.dequantise_dir`; LT14 uses the stored values).
  - `p_flat = 1 - (dir_2h_up + dir_2h_dn) / 65535` (M2).
  - Up call: `s > 0`; down call: `s < 0`.
- **Candidate set and exclusions, in this order, all before the decile cut:**
  1. **capture-level:** `P`'s file absent, `late` or `spec_mismatch` -> no units at k (counted);
  2. a row of `P`'s file (= a base-eligible row of `features/<k>`) with `elig & 1 = 0` -> not `dir_2h` eligible (counted);
  3. duplicate `market_id` -> keep the first row (counted);
  4. `sidecar_missing` (no sidecar row at k);
  5. **scope** (a parameter; `scope: non_sports_ex_crypto` at the freeze; R1 open question 8):
     - the pinned `cb17_census.is_sports_sidecar(fee_type, fee_category, series_slugs)` is vendored by hash and applied to
       post-fee-step values as LT13 1.4 does, so the about 1,800 re-classified markets count as non-sports (disclosed);
     - crypto is excluded by LT13's pinned classifier, with unknown treated as crypto;
     - the sports and crypto arms use the same reader;
  6. `tier_na` (non-finite `ms_log_liq`);
  7. `s_zero` (`s = 0` exactly).

  Every step is counted per capture.
- **The decile cut:** over the remaining set `C_k` (all tiers together), sort by `|s|` descending, ties by `market_id`
  ascending (stable), and take the first `ceil(|C_k| / 10)`. Middle deciles 4-6 (M6) and the `p_flat` deciles (M2) use the
  same set, order rule and tie-break.
- **After the cut:** the series-family rule (a family holding > 40% of the tier's census top-decile units is excluded from
  the tier, `<tier>.exclude_family`, census-fixed). It removes units but never re-cuts the decile.
- **Tier:** cost-model bins on `expm1(ms_log_liq)` (the row's Gamma `liquidity` as stored): `< $1k`, `$1k-10k`,
  `$10k-100k`, `>= $100k`.
- **Spread:** `spread_k = ask_k - bid_k` from `quotes/<k>` (`ms_spread` is Gamma's `spread` field and is not used for
  `spread_k`).
- **Event key:** `event_id` from `features/<k>`; -1 (unknown) clusters on the market.
- **Unit:** a 10k-100k member of the top decile at k after all of the above.
- **Gross:** `g = 100 x sign(s) x (mid_{k+1} - mid_k)` cents, with `mid = (bid + ask) / 2` from `quotes/<k>` and
  `quotes/<k + 1>` as written. The census checks `|mid_k - ms_mid| <= 1e-6` (float32 storage; exact equality is not
  expected) on every unit.

### 1.6 Outcome classes at k + 1 (write-once, never imputed)
Each unit gets exactly one class:
- `labelled` (`st = 0` and the horizon rule holds): **only these have `g`**;
- `unavailable_one_sided` (`st = 3`), `unavailable_closed` (`st = 1`), `unavailable_inactive` (`st = 2`);
- `unavailable_absent`; `unavailable_missing_capture`; `unavailable_timing`; `unavailable_spec`.

**Unavailable units are counted and reported separately** by class, tier and decile, and never enter the mean. CH269's
signed-decile gaps were small, 0.16 points in 10k-100k [map].
- *attrition-differential*: the top decile's unavailable share exceeds the rest of the tier's by > 2 points in the window.
- **Worst-case bounds, always printed:** every unavailable unit is set to `-100 x mid_k` (up call) or `-100 x (1 - mid_k)`
  (down call), and then to the most favourable value.
- *attrition-sensitive*: the lower bound falls below `H` while the primary clears it.

Neither label changes a verdict.

### 1.7 What is not looked at before the analysis date
- No mid after an origin, `g`, decile mean, cents summary or plot of `P`'s predictions by tier, from the census span or the
  window, by any LT14 designer, coder or reviewer.
- During the window, only `ops-stats` (file, line, class and status counts; no price, spread, liquidity or `s`; unit test).
- Nobody opens census-span files before the LT14 seal commit, except the schema pre-check and the sha256 checks.
- No LT14 designer reads LT12's census output before the freeze, nor E015, E022 or LT9-LT13 analysis outputs before the pin.
- The pre-freeze hold in `signal_engine/CANDIDATES.md` (filed 2026-10-30; referenced, R1 SHOULD 7) bars any engine session
  from computing or displaying the champion's cents gross or top-decile hit rate by tier before the freeze.
- Seen by the designer: the engine's STATUS lines (log-loss leads, not by tier and not in cents).

### 1.8 Estimand, estimator and inference
- **Estimand:** `theta = E[g | top decile, 10k-100k, labelled] - H`, the mean label-origin gross minus a fixed hurdle.
- **The hurdle and its source (R1 MUST 3).** `H` = **1.30c**, fixed now.
  - Its source is `COST_MODEL.md` 5's "maker both legs, independent" figure, `2 x (AS - h) - rebates`: AS = 2.04c (the
    10k-100k filled-touch adverse selection at a 1-2 h mark, `COST_MODEL.md` 4) and h = 1.34c (half of F4 / F5's mean
    spread of 2.68c), with rebates about 0.10c over both legs: `2 x (2.04 - 1.34) - 0.10 = 1.30c`.
  - It assumes both legs fill passively, fills independent of the signal, and no non-fill or inventory cost.
  - **The tier's own p50 half-spread** (0.75c, `COST_MODEL.md` 4) in the same formula gives `2 x (2.04 - 0.75) - 0.10 =
    2.48c`. It is printed beside every result, including the Supported sentence (1.10).
  - `H` stays 1.30c: a lower bar makes a Contradicted result stronger (R1).
  - The census recomputes both figures from its recorded touches and prints them. **They never replace `H`.**
- **H1 (one-sided):** `theta > 0`.
- **Estimator:** the unweighted mean of `g` minus `H` (one share at the touch, size-unlimited).
- **Standard errors and p (as LT13 1.7):**
  - CR1 on **event** (t, `G - 1` df);
  - two-way event x UTC day (normal);
  - UTC day (t, `G_day - 1` df).

  **One-sided p = the largest of the three.** The conservative 95% CI is the hull of a 2,000-draw event-cluster bootstrap
  (seed 20261814) and the three Wald intervals. Kish `G_eff` is printed, with floor 15.
  Why event: markets of an event share news, and a market re-enters the decile across captures. The day term holds
  venue-wide moves, because the decile is cut within a capture.
- **Sports arm:** clusters on event (the game) and fixture day (the game's scheduled UTC day from `end_ts`), two-way, p the
  largest.
- **Sensitivities (reported):** clusters on capture; on market; event x two-day block.
- **MDE multiplier** 3.47, not lowered for k = 1.

### 1.9 Placebo, F and the size check
- **Placebo: the shuffled prediction file (binding; R1 open question 4).**
  1. In each capture x tier stratum of `C_k`, the units' `s` values are permuted across units (200 seeded draws). Each unit
     keeps its own mids, timing and class.
  2. The placebo top decile is recut by the same rule as the real one (1.5): over all of `C_k`, sort by shuffled `|s|`
     descending, **ties by `market_id` ascending**, and take the first `ceil(|C_k| / 10)`. Each tier's count equals the real
     count, except where ties sit at the cut-off value; the tie-break is the real cut's.
  3. `g_pl = 100 x sign(s_shuffled) x (mid_{k+1} - mid_k)` on labelled 10k-100k units. `gbar_pl` is the mean over draws.

  **Binding condition (two-sided):** `|gbar_pl| < 0.5 x gbar`. **Diagnostic:** `p_shuffle = (1 + #{draw mean >= gbar}) /
  201`.
- **F (LT7's one-rule form; binding; R1 open question 3).**
  - Twin: `g_tw = 100 x sign(s_k) x (mid_{k+3} - mid_{k+2})`. It is NaN unless `st = 0` at k + 2 and k + 3, both horizons
    hold, and the end is after k + 7 h (`f_end_short`).
  - `Delta = gbar_lead - gbar_twin` on units with both.
  - **F holds iff Delta's one-sided p < 0.05 (1.8's rule) and `Delta_hat >= 0.5 x gbar_lead`.** Under 50% of the primary's
    units in the arm, the result is *falsification unavailable*.
- **Size check (R1 MUST 4: able to fail).** It runs after the census, on the code to be pinned: **2,000 worlds, seed
  20261814**, limit **0.058**, 200 placebo draws per world.
  - Every world uses the census's 10k-100k event-size distribution, unit count, up / down share and spread quantiles; 252
    captures; 10% of units removed at random; shocks drawn per cluster inside the cluster's loop.
  - **Null worlds (1-4, 7-9) put the move on the unit and set the twin's mean to 0:**
    - `mid_{k+1} - mid_k = sign(s_i) x (H + u_i) / 100 + D_t + E_{e,t}`, with unit noise `u_i` and the world's
      common-direction-free day and event shocks entering the raw mid change;
    - the twin is `mid_{k+3} - mid_{k+2} = D'_t + E'_{e,t} + noise` with no sign-aligned part.

    The twin's sign-weighted expected mean is 0 by construction (shocks mean 0, independent of `sign(s)`); its realised
    mean varies around 0. So in a null world F and the placebo can both pass. With an up / down mix `q`, the placebo mean is about
    `(2q - 1)^2 x H`, under half of `H` unless `q` > 0.85 or < 0.15. Size is then decided by the analytic p.
  - **Verdict size** = the share of worlds in which the analytic one-sided p < 0.05 and F and the placebo hold. It must be
    <= 0.058, else "SE check failed (size scenario)": p = 1, k unchanged, no rerun.
  - **Binding diagnostic:** in each null world, the share with analytic p < 0.05 regardless of F and the placebo. Above
    0.058 in any null world, the label *analytic p oversized in simulation* is **set** (never a verdict change).
  - Verdict size and the analytic-p share are computed per world type.

  | # | World | True mean of `g` | Twin mean | Checks |
  |---|---|---|---|---|
  | 1 | boundary null: event shocks N(0, 0.5c), day shocks AR(0.5) SD 0.3c, `u` SD 1.3c | `H` | 0 | three-way p at the census `G` |
  | 2 | heavy tails: `u` t(3) scaled to SD 1.3c, plus 1% jumps +/-30-60c symmetric about `H` | `H` | 0 | small-sample t with jumps |
  | 3 | concentration: 10% of events hold 50% of units (or the census's share if larger), event mean shifts N(0, 0.5c) on the unit term | `H` | 0 | CR1 with few large clusters |
  | 4 | **S44 stale side:** the unit term is `0.4 x spread_k + u`, shifted to mean `H` | `H` | 0 | spread-linked heteroskedasticity |
  | 5 | **per-market drift (M-Q):** an AR(0.99) per-market drift aligned with `sign(s)`, SD 1.0c, in lead and twin alike | `H + 0.5c` | `H + 0.5c` | F must block it (mechanical) |
  | 6 | **common direction:** a venue-wide `D_t` (AR(0.9), SD 0.5c) aligned with the decile's predominant sign at the census `q`, no unit term | `H + 0.5c` | about 0 | the placebo must block it (mechanical) |
  | 7 | **S45 label timing:** 5% of k + 1 rows received 2 h + 20-40 min after k, SD x 2 | `H` on 2 h rows | 0 | the horizon rule |
  | 8 | **S46 spec change:** a refit at day 11 re-ranks `\|s\|` (rank correlation 0.5) | `H` both halves | 0 | composition shift |
  | 9 | **differential attrition:** units with `g < H - 2c` unavailable at 10 x the census top-decile share | `H` on labelled units (the unit term is shifted after attrition) | 0 | selection at k + 1 |

  Worlds 5 and 6 are mechanical. Their verdict-size criterion (<= 0.058) is the share of Supported verdicts. Diagnostics:
  planted-effect power (500 worlds, unit term `H + 0.25c`, seed `20261814 x 100 + 51`), world 4's M1 slope, and world 9
  unshifted: share Supported, printed, never a verdict change. Why world 9 is shifted: `theta` is defined on labelled units
  (1.8), so a world whose labelled mean exceeds `H` is not a null for it, and the unshifted version would fail the size
  check by construction (the attrition labels and worst-case bounds of 1.6 carry that risk instead).

### 1.10 Verdicts and labels
- **Supported (exploratory, prospective):** p < 0.05 (k = 1), `theta_hat > 0`, F holds, the placebo holds, and the size check
  passed. **The text, one sentence (R1 SHOULD 9):** "*The pinned `P`'s top-decile mean label-origin gross (from the mid at
  capture k, before the prediction existed; not an executable entry) exceeded 1.30c in the 10k-100k tier: `gbar - H` = x
  [CI], `gbar - gbar_pl - H` = y; the tier-spread figure is 2.48c (`gbar` - 2.48c = z); M1: {spread-scaling consistent /
  not}; touch, size-unlimited, no fills measured.*" It never says "route", "tradable" or anything stronger.
- **Contradicted (below the hurdle):** the conservative 95% CI of `gbar` lies entirely below 1.30c. This is the expected
  outcome.
- **Inconclusive:** otherwise. If F fails or is unavailable: *mechanical null not excluded* / *falsification
  unavailable*. If the placebo fails: *common direction not excluded*.
- **Unavailable:** < 15,000 labelled units, < 200 events, `G_eff` < 15, < 10 UTC days with units, or `P`'s files on < 80% of
  window captures. The 15,000: at `n_eff` 12,000 and DE 5 the F-MDE is `5.205 x 1.3 x sqrt(5 / 12,000) x 1.58` = 0.22c.
- **Labels (never change a verdict):**
  - *spread-scaling consistent* (M1: slope one-sided p < 0.05 and the zero-spread intercept's CI includes 0);
  - *latency-sensitive* (1.4); *attrition-differential*, *attrition-sensitive* (1.6);
  - *champion changed in window* (1.3); *informed (X)*; *analytic p oversized in simulation* (1.9);
  - *underpowered* (window MDE > 0.5c); *series-concentrated*; *fee regime changed* (1.13).

### 1.11 Secondaries and economics (reported; count 0; never change a verdict)
- **M1, the spread-scaling alternative.** Within the 10k-100k top decile: OLS of `g` on **centred** `spread_k` (`spread_k`
  minus its window mean over these units; R1 SHOULD 6), with an intercept, CR1 on event. It prints:
  - the slope;
  - the centred intercept;
  - the **implied zero-spread intercept** (centred intercept minus slope x mean spread; delta-method CI);
  - the share of `gbar` that `slope x mean spread` explains;
  - the primary by spread tercile.

  The stale-side reading predicts a zero-spread intercept near 0 and a slope of 0.3-0.5. The primary has no regressor, so
  no aliasing arises there.
- **M2, the flat decile.** Within capture x tier, the top and bottom deciles of `p_flat` (1.5). It prints the share with
  `|mid_{k+1} - mid_k| <= spread_k / 2` in each, their difference with an event-CR1 CI, and mean `|Δmid|`. A selection
  fact, not a fill measurement.
- **M3, the cost ladder** at recorded touches (cost-model-v1 constants):
  - `gbar - H_j` with CIs for 0.65c (maker entry held to resolution; a 2 h gross is not a hold gross, so print only), 1.30c,
    **2.48c (tier-spread figure)**, 2.41c, 2.84c, 3.18c, 3.52c and 3.9c (the tier's $100 taker round trip p50);
  - the per-unit taker round trip `spread_k + fees on both legs`, at the docs rate (`conservative`) and at the served
    `fee_schedule` rate;
  - the formulas are a **vendored copy** in a new LT14 file, with `costs.py`'s source sha recorded and an equality unit test
    against `costs.cost_check` on synthetic inputs. **No E026 frozen file is edited**, and LT14 does not depend on E026's
    pin, which expires 12-07 (R1 open question 9 allows either; vendoring chosen).
- **M4, arms:** fee class at k (served rate 0 / > 0 / unknown); the engine's `category`.
- **M5, arms:**
  - **the >= 100k tier against 0.50c** (its half-spread; R1 SHOULD 1) and 2.9c (its $100 round trip p50);
  - the < 1k and 1k-10k tiers against their own ladders;
  - up and down calls separately; the signed decile (the map's object);
  - a within-tier decile; the display pool (spread <= 2c); tick 0.001 units;
  - the sports and crypto arms.
- **M6, within-market secondary** (R1 SHOULD 6).
  - Model: the top decile's `g` against the middle deciles' (4-6), `D_i = 1[top]`, by expanding-past market x UTC-day
    demeaned OLS.
  - **Controls (declared now):** `spread_k`, `log1p liquidity`, `|ms_mid - 0.5|`, log1p hours to end with `hte_unknown`,
    `z log ms_rv24` with `rv_missing`, `mo_d2h`, and 11 slot-of-day dummies.
  - **Left out on purpose:** `category`, `ms_neg_risk` and the tick. Each is a market constant within a market x UTC-day
    stratum, so it is zero after demeaning.
  - **Disclosed:** `D_i` is a function of `P`'s inputs, several of which are these controls, so M6 measures the top-decile
    contrast net of a linear adjustment for part of the ranking's own inputs. It is reported only.
  - **Aliasing (LT13's rule, vendored):** before each fit, compute the rank of the demeaned control matrix without `D_i`
    (column-pivoted QR, tolerance `max(n, p) x eps x the largest singular value`). If it falls short of the column count,
    drop a column only if it lies in the span of the other retained columns, in this fixed order:
    1. slot-of-day dummies, latest slot first;
    2. `hte_unknown`, `rv_missing`;
    3. log1p hours to end;
    4. `|ms_mid - 0.5|`.

    `D_i` is never dropped. If the controls are still rank-deficient after these groups, or `D_i` lies in the span of the
    retained controls, the fit is NaN (`unavailable`, counted). No pseudo-inverse is used. Rank, column count and dropped
    columns are printed per fit and per gate draw.
  - Gate: Freedman-Lane on market x UTC-day strata, 200 draws.

### 1.12 Overlaps, dependence and counting
| LT14 | Closest prior | Same contrast? | Why not a double count |
|---|---|---|---|
| CH262 | LT12 CH245 / CH244 (spread innovations; same days in the parallel lane) | no: LT14's target is the mid move in `P`'s direction | different object; shared-market share printed; no LT12 object computed |
| CH262 | F4 / F5 (`COST_MODEL.md` 5; development) | no | prospective, `P`'s own predictions, 2 h |
| CH262 | the engine's leaderboard | no: log loss on a 3-class label | no score read; a verdict never promotes |
| CH262 | M1 / M2 (CH263 / CH264 measurements) | no | different units, k = 0 measurements; never pooled |

**Counting:** **k = 1 counted test**, kind `live_tests14` (a fail-closed `battery2.KIND_RULES` entry). Placebo, F,
secondaries, arms (including >= 100k), economics, the census, the CH269 map and the size check count 0.

### 1.13 Stop rules and deviations
- **Stop rules (LT13 1.12):**
  - no interim look; no extension;
  - after 7 days, units below one third of the census projection get the ledger note "likely Unavailable" and nothing else
    changes;
  - a pinned-file change makes the analysis refuse;
  - the reader refuses above 1.0 GB in `live_tests14/`.
- **Deviations (LT13 1.13):**
  - operational losses stay missing and are counted;
  - a venue fee or category step is recorded within 24 h and labelled *fee regime changed*;
  - after the freeze, any change needs a justification, a reviewer acceptance, a new sha and the label *amended after
    freeze*;
  - after the census commit, no gate or definition change (a defect gives `census_dropped (defect)`);
  - after the pin, a defect gives "SE check failed (deviation)", p = 1.

### 1.14 Retention and the write-once extraction
- **Retention.** The engine's retention is not active yet: the owner decides on the drafted 35-day rule for predictions and
  45 days for quotes and features about 11-15, with deletion only after a verified release. Sidecars are deleted after 8
  days.
- **Window reader** (cron every 2 h; `mem_mb` < 500; under the heavy-job lock). For each new complete capture whose `P` file
  is logged, it writes write-once (`%.17g`, atomic hard link) `live_tests14/series/<capture>.parquet`:
  - one line per row of `C_k` (1.5), with `market_id`, `event_id`, `dir_2h_dn`, `dir_2h_up` (verbatim uint16), `elig`,
    `written_utc`, `fit_id`, `spec_sha256`, `bid_k`, `ask_k`, `st_k`, `t_row(k)`, `ms_*` inputs, `mo_d2h`, and the sidecar's
    `fee_type`, `fee_category`, first series slug, `fee_schedule`, `fees_enabled`;
  - then the k + 1..k + 3 `st`, `bid`, `ask` and `t_off` lines once those `quotes/` exist.

  Values are copied as the engine wrote them; nothing is re-scored. `g` is computed only at analysis, from these files.
- **Lag guard:** 72 h of complete-but-unextracted captures triggers a ledger alert (`lt14_lag`). There is a one-shot
  sha-equal restore from the verified release. A capture found nowhere is `unavailable_missing_capture`, never awaited.
- No retention rule covers `live_tests14/` before the analysis commit.

## 2. Planning counts and MDE (planning only)
**Formula:** `MDE = 3.47 x 1.5 x SD x sqrt(DE / n_eff)`, with `n_eff = 0.8 n` and `VIF_w` = 1 (no regressor).
`F-MDE = MDE x sqrt(2 / (1 - max(0, r)))`, with planning `r` 0.2 (x 1.581).

**Design effect.** `DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)`.
- From the signed map [map]: 7.47 units per market in 104 captures, about 18 in 252.
- With 1-5 decile markets per event (unprobed), `m_21` is 18-90, so the formula gives 1.3-2.8 and **the floor 5.0 binds**.
  DE 31 is quoted beside it.
- The 0.02 within-event correlation is an assumption. The three-way p carries the risk in the verdict.

**SD:** 1.3c (the cost model's 10k-100k 2 h mid SD), and 2 x SD as a sensitivity (the decile is chosen partly on recent
moves).

| Count (10k-100k unless stated) | n (252 captures) | n_eff | MDE DE 5 / DE 31 | F-MDE DE 5 / DE 31 | 2 x SD (MDE DE 5 / DE 31) |
|---|---|---|---|---|---|
| signed-decile median 175 a capture [map; a different object] | 44,100 | 35,280 | **0.081c / 0.20c** (`5.205 x 1.3 x sqrt(5 / 35,280)` = 0.0806) | 0.13c / 0.32c | 0.16c / 0.40c |
| the census line, 100 a capture | 25,200 | 20,160 | 0.11c / 0.27c | 0.17c / 0.42c | 0.21c / 0.53c |
| a quarter of 175 | 11,025 | 8,820 | 0.16c / 0.40c | 0.26c / 0.63c | 0.32c / 0.80c |
| arm: >= 100k, signed mean 0.78 a capture (SD 1.9c) | 197 | 157 | 1.76c / 4.39c | 2.79c / 6.94c | - |
| arm: >= 100k at 10 a capture | 2,520 | 2,016 | 0.49c / 1.23c | 0.78c / 1.94c | - |

**Reading.** At the census's own count line (100 a capture), the primary resolves `gbar` to about a tenth of a cent at DE 5
and about a quarter at DE 31, against a 1.30c hurdle. Precision is not the risk; the count of the `|s|` decile is. The
>= 100k tier would need about 24 units a capture to pass an F-MDE line at DE 5, which is why it is an arm (R1 SHOULD 1).

## 3. Pre-registration census (counts only; once; before registration; no target read)
The census runs once on sealed inputs and reads origin-side fields of capture k. Its only later-slot reads are `quotes/`
`st` and `t_off` at k + 1..k + 3 (the unavailable shares and the horizon rule). It reads no later bid, ask or mid (unit
test). It is committed with its sha256 before the registration commit. **Every threshold below is stated now.**

**Inputs.**
- Span **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**, 10 UTC days, 120 slots, plus **the three slots 00:31Z, 02:31Z and
  04:31Z of 2026-11-17** for k + 1..k + 3 status only (R1 SHOULD 5). Those end before LT11's window (11-18).
- Engine files for those captures: `predictions/<cap>/<P>.parquet`, the predictions log lines, `quotes/`, `features/`,
  `meta/` (on the host within retention, else restored once from the verified release).
- The span's sidecars (scope and fee fields; sha256-checked LT12 / LT13 copies accepted).
- **Seal:** once, after the 04:31Z capture of 11-17 is complete or past its tolerance. It records files, sha256s, slots,
  `P`'s spec sha, the input-clock audit and the frozen design-text sha256.
- **Refusals:** an input not in the seal; a seal whose design-text sha is not the ledger's; any later-slot price; any `g`;
  any LT11-LT13 or M1 / M2 object; a second run; a `P` that fails the audit.
- **Fee-class prints sum across captures** (the CH269 defect, R1 MUST 5), with a unit test that a two-capture synthetic
  input gives the sum.

**Coverage first.** Covered days (covered origins / 12) must be >= 7.0, and `P`'s on-time files must cover >= 90% of census
captures. Otherwise LT14 is `census_unavailable (coverage)` and nothing more is printed.

**Definitions.** Projection = count x 21 / covered days. Per-capture statistics are over covered captures, zeros included.
- `SD_plan = max(1.3c, 100 x SD of mo_d2h over the census 10k-100k top-decile units)`. `mo_d2h` is the own 2 h change over
  (k - 1, k], an origin-side quantity.
- **Declared MDE:** section 2's formula at the projected `n_eff`, `DE_gate` and `SD_plan`. The F-MDE uses planning `r` =
  0.2; the census reads no twin value.
- **Design MDE (R1 SHOULD 2):** `3.47 x 1.5 x max(se_event, se_twoway, se_day)`, the three standard errors of a mean
  computed from the census's unit counts per event, per event x UTC day and per UTC day, at `SD_plan` with the 0.02
  within-cluster correlation.
- The gate uses `max(declared, design)`.

**Lines for the primary (10k-100k; all must hold; NaN fails):**
- **median `|s|`-decile units a capture >= 100** (round 19's line, on CH262's object; the binding `|s|` gate, R1 MUST 6);
- projected labelled-eligible units >= 25,200;
- **non-stationarity:** per-capture median >= 0.25 x mean;
- **venue clock:** no slot of day > 50% of units;
- distinct events >= 300 (unprojected); Kish `G_eff` >= 15;
- **unavailable gap** (top-decile minus rest-of-tier unavailable share at k + 1) <= 10 points (round 19);
- finite tier on >= 95% of in-scope eligible rows; `|mid_k - ms_mid| <= 1e-6` (float32 storage; exact equality is not expected) on 100% of units;
- **MDE <= 0.5c and F-MDE <= 0.5c** at the computed `DE_gate` and `SD_plan`.

The nearby map numbers (signed decile, engine scope; planning only) are: 175 median, ratio 1.02, busiest slot 10.2%, gap
0.16 points.

- **Census-fixed values (exhaustive):**
  1. `k_tests`, `dropped_tests`, `census_unavailable` (mutually exclusive);
  2. `<tier>.exclude_family`;
  3. the world inputs:
     - the 10k-100k top decile's event-size quantiles q10..q90 and its top-10% share;
     - its spread quantiles q10..q90;
     - its up / down share `q`;
     - its unavailable share;
  4. `SD_plan`;
  5. the census median of `L_c` (1.4).

  `DE_gate`, the MDEs and the recomputed hurdles (1.30c-formula and tier-spread) are recorded, never used to change a
  threshold.
- **Prints (descriptive):**
  - units a capture by tier (min / median / mean / max), for the `|s|` decile and the signed decile side by side;
  - by tier x fee class, summed over captures;
  - by tier x engine `category` and x the pinned classifier (the confusion table);
  - by up / down;
  - every exclusion step of 1.5 per capture;
  - distinct markets and events; tenure; unavailable shares by class, decile and tier;
  - `L_c` per capture, and `t_off` quantiles;
  - `VIF_w` of `D_i` against M6's controls, and M6's control rank and dropped columns on the census design (no target);
  - `P`'s spec sha per capture, any `spec_mismatch`, champion changes;
  - the share of units in two-member neg-risk events;
  - **the >= 100k arm's count lines as prints only** (median >= 10, >= 40 markets: printed pass / fail, never a gate);
  - the sports and crypto arms' counts.
- **Expected fate:** the primary passes unless the `|s|` decile under the pinned classifiers sits mostly in the small
  tiers. Adding the down calls doubles the candidate pool of signed extremes, so the 10k-100k count could fall or rise;
  it is unmeasured. The >= 100k arm is expected far under its print lines.

## 4. Design changes from the round-19 sketch (made before any LT14 data; R1 ruled on each)
1. `DE_gate` floor 5.0 in place of 1.98; DE 31 beside it.
2. Planning counts from CH269 [map], disclosed as a **different object** (signed decile, engine scope; MUST 6).
3. `H` fixed now (1.30c), with its formula and source, and the tier-spread figure (2.48c) printed beside it (MUST 3). The
   recomputed hurdles are print-only.
4. Pinned `P` only, with the freeze-time pin, an input-clock audit (MUST 2) and a declared rule for changes. se1 is not
   read.
5. Scope by the pinned sidecar classifiers (R1 open question 8), with the confusion against the engine's `category`
   printed.
6. A binding shuffled-file placebo (open question 4) and a binding F (open question 3).
7. Outcome classes, worst-case bounds, the horizon rule, and capture-level latency with a numeric label trigger (SHOULD 3).
   No latency exclusion (open question 6).
8. MDE and F-MDE gates at the 0.5c floor; the design MDE on the largest of three SEs (SHOULD 2); Unavailable floors.
9. **k = 1:** the >= 100k tier moved from the family to an arm (SHOULD 1).
10. The label-origin gross named everywhere (MUST 1); the exclusion order and tie-break declared (MUST 7); null worlds able
    to fail (MUST 4); M6's controls and the aliasing rule (SHOULD 6); the freeze deadline (SHOULD 8).

## 5. `attrlimit_lt14`: request text for `signal_engine/CANDIDATES.md` (filed at the freeze; not applied here)
The **pre-freeze hold is already filed** in `CANDIDATES.md` (2026-10-30, R1 SHOULD 7; referenced, not duplicated). The
freeze files this request:

> **LT14 request (CH262; filed at LT14's design-text freeze).** No token: LT14 builds no feature, family or model. One
> **attribution limit `attrlimit_lt14`** (`kind: attribution_limit`) until **the LT14 date**. The LT14 date is the later of
> 2027-01-03T00:00Z and LT14's analysis commit (ordered lane: the later of 2027-03-08T00:00Z and the analysis commit). It
> is moved later only by a ledger line.
> - **Models:** the pinned `P` (`model_id`, `spec_sha256` as frozen).
> - **Scope, display:** no public display (website feed, `/lab`, `dashboard.json`, any shared document or chart) of `P`'s
>   realised gross in cents, by liquidity tier or for its top `|s|` (or signed) decile. That includes the mean move in the
>   predicted direction, top-decile hit rates by tier and net-of-cost figures.
> - **Scope, computing (R1 SHOULD 7):** **no engine session computes** `P`'s cents gross or top-decile hit rate by tier,
>   whether displayed or not.
> - **Unchanged:** the log-loss, Brier, calibration and AUC leaderboard, the promotion rule and the `se-feed-v1`
>   signal-strength display.
> - `no_broad_families: []`.
> - If such a number is computed before the LT14 date, the ledger records it and LT14 carries *informed (engine)*.
> - A census drop withdraws the limit with a ledger line.
> - An engine result never changes an LT14 verdict; an LT14 verdict never promotes a model.

## 6. Jobs (described in text only; no queue file, no code in this commit)
1. **Schema and clock pre-check** (light; at the freeze). It records:
   - `P`'s registry sha and status;
   - the column names and types of 1.2 in `P`'s prediction file and in `quotes/` and `features/`;
   - the predictions log fields;
   - the sidecar fields;
   - `P`'s input-clock audit (1.3).

   It reads no value.
2. **Seal** (light, once): after the 04:31Z capture of 2026-11-17.
3. **Census `CC14`** (counts only, once; `net` lane; planned `mem_mb` < 500; the job is refused above 800 MB; runs under the
   heavy-job lock). It streams captures one at a time and sums the fee prints across captures (unit test).
4. **Size check** (once; `cpu` lane; only if the primary survives): 2,000 worlds, seed 20261814.
5. **Window reader** (cron every 2 h, light; 1.14).
6. **`ops-stats`** (counts only).
7. **Analysis** (once; `--out` required).

Modules to be written later, in new files only: `backend/astrolabe/research_lab/live_tests14.py`, `live_tests14_costs.py`
(the vendored formulas), `backend/scripts/run_live_tests14.py`, `backend/tests/unit/test_research_lab_live_tests14.py`
(synthetic only). No signal-engine code or E026 frozen file is touched.

## 7. Priors (the designer's judgement, not measurements)
**P(census) 0.65 (was 0.80; R1 MUST 6).** The reasoning:
1. The only count behind the drafting is of a different object, the signed decile with the engine's scope. The `|s|`
   decile adds the down calls, and its tier split is unmeasured: about -0.08.
2. The pinned sidecar classifiers may move units between scope classes relative to the engine's `category`: about -0.03.
3. If a promotion before the freeze makes `P` a model with `flow` / `wallet` / `book`, the audit refuses it (P about 0.1 x
   refusal about 0.8): about -0.04.
4. Coverage, `|mid_k - ms_mid| <= 1e-6` and the MDE gates: small.

From these:
- **P(no LT14 test) about 0.35**, plus about 0.05 for a missed 11-07 freeze deadline.
- Given registration: P(Supported) **0.08**; P(Contradicted) **0.75**; P(Inconclusive) 0.12; P(Unavailable) 0.05.
- P(`gbar` > 0.65c) about 0.35; P(`gbar` > 2.48c) about 0.03; P(*spread-scaling consistent*) about 0.6.
- Given Supported, P(the number holds on a second prospective window) 0.4.

## 8. What LT14 can and cannot say
**It can say:**
- whether the pinned `P`'s strongest 2 h directional calls in the 10k-100k tier carried a **label-origin gross** (from the
  mid at capture k, before the prediction existed) above a declared 1.30c hurdle over 21 prospective days, with event- and
  day-robust uncertainty;
- how far that gross sits from every rung of the cost ladder, including the 2.48c tier-spread figure;
- whether it scales with the spread;
- whether `P`'s flat calls pick books that stay inside the half-spread;
- how attrition and latency could move it.

**It cannot say:**
- what an order placed at or after the decision time would have earned (**the label-origin gross is not an executable
  entry**);
- anything about fills, queue position, signal-conditional adverse selection, size beyond the touch, the exit, inventory,
  rewards or rebates;
- anything about another model, horizon, window, season or fee regime, or about the >= 100k tier;
- that `P` is uninformative if the gross is below the hurdle. Log-loss accuracy is the engine's own yardstick and is
  untouched.

A Supported primary can at most nominate a separately registered design with entries at or after the decision time and
fills measured on the signal. A Contradicted primary says the label-origin gross does not reach the 1.30c hurdle, by the
printed margin, which is stronger still against 2.48c.

## 9. Disclosures
- **Read for the first draft:**
  - `CLAUDE.md`, `AGENTS.md`;
  - round 19 (sections 0-0.3, 1, CH262, CH269, 3); the CH269 map review; the seal section `champion_top_decile_ch262` and
    its `decisions` / `span` / `not_mapped` / `captures_engine`; `census_map_ch269.py` l. 836-870;
  - `COST_MODEL.md` 4-8;
  - `NORTH_STAR.md`; `DESIGN_V1.md` 1-6, 20, 28, 30, 33; `STATUS.md` (head); `CANDIDATES.md` (LT13 block, LT14 note);
    `features.py` (columns, quotes frame);
  - `LIVE_TESTS_13.md` 0-1.14, 6, 8-11; `LIVE_TESTS_12.md` (headings, window lines); the ledger header and the
    round-19 / CH269 lines.
- **Read for this draft:**
  - the R1 review (whole); the ledger's LT14 R1 entry; the `CANDIDATES.md` pre-freeze hold;
  - `predict.py` (l. 1-125), `labels.elig_mask` / `dir_eligible`, `config.ELIG_BITS` / `Q` / `P_CLIP`,
    `specs.active_models`, `promotion.py` (grep for status changes), `features.py` l. 476-490 (row selection);
  - `ext_sidecar.py` (docstring, `received_utc`);
  - `LIVE_TESTS_13.md` l. 743-752 (the aliasing rule).
- No host, network, `ssh`, `data-dumps`, census output, prediction value, target or P&L was read.
- **Verified read-only for R1's "could not verify" list:**
  - the column names (`dir_2h_dn` / `dir_2h_up`);
  - the bit encoding (`elig & 1` = `dir_2h`, target eligibility only; base eligibility is membership of `features/`);
  - demoted models keep writing while `status: active`;
  - sidecar rows share the page `received_utc`.
- **Still unverified:** the `|s|` distribution.

### 9.1 Values declared now and their sources
| Value | Where | Source | Informed by CH269? |
|---|---|---|---|
| `H` 1.30c; tier-spread figure 2.48c (printed) | 1.8 | `COST_MODEL.md` 4-5 formula | no |
| k = 1; >= 100k an arm | 0, 1.11 | R1 SHOULD 1 | yes (0.78 a capture) [map] |
| decile by `\|s\|`, all tiers pooled, exclusions before the cut, ties by `market_id` | 1.5 | round 19; R1 MUST 7 | the map's signed reading seen |
| count line 100 a capture (`\|s\|`) | 3 | round 19 | drafting on a defective count [map] |
| unavailable gap 10 points; attrition label 2 points | 3, 1.6 | round 19; LT13 1.5 | values seen [map] |
| non-stationarity 0.25; venue clock 50%; family 40%; `G_eff` 15; events 300 | 3 | conventions | values seen [map] |
| `DE_gate` floor 5.0; design MDE on max of three SEs | 2, 3 | LT13 1.0; R1 SHOULD 2 | tenure seen [map] |
| MDE and F-MDE <= 0.5c | 3 | rule 8 | no |
| horizon 2 h +/- 15 min; latency trigger 0.25c | 1.4 | round 19 S45; R1 SHOULD 3 | no |
| Unavailable 15,000 / 200 / 10 days / 80% | 1.10 | F-MDE arithmetic | no |
| placebo half, two-sided; F half | 1.9 | LT12 R1 MUST 5; LT7 | no |
| M6 controls and aliasing order | 1.11 | LT13 3.3; R1 SHOULD 6 | no |
| freeze deadline 2026-11-07T00:00Z | 1.1 | R1 SHOULD 8 | no |
| seed 20261814 | 1.8, 1.9 | unused (git grep; R1 checked) | no |
| census span and tail (to 11-17T04:31Z) | 3 | round 19; R1 SHOULD 5 | no |

## 10. The first draft's open questions, answered by R1
1. **Parallel lane: accepted** (disjoint objects). Readers run under the heavy-job lock, and December thinning is disclosed
   (1.1).
2. **`|s|` vs signed:** MUST 6. The map counted a different object; the binding `|s|` gate is the census's (3); P(census)
   lowered (7).
3. **F stays binding** (1.9).
4. **Placebo stays binding** (1.9).
5. **Keep 1.30c**, described by its formula and source, with 2.48c printed beside it (MUST 3; 1.8).
6. **No latency exclusion** (MUST 1-2); a capture-level sensitivity with a numeric trigger (SHOULD 3; 1.4).
7. **k = 1** (SHOULD 1).
8. **Pinned sidecar classifiers** (1.5).
9. **Either way.** Vendored (designer's choice; it avoids E026's pin, which expires 12-07; 1.11).
10. **Yes, a defect** (MUST 5; ledger); LT14's census sums across captures, with a unit test (3).
11. **Pin at the freeze**, before 2026-11-07T00:00Z (SHOULD 8; 1.1, 1.3).

## 11. Proposed registry text (for the coordinator, who edits `registry.json`; R1 SHOULD 10)
`plain` (proposed): "One planned live test from ideas round 19: do the signal engine's strongest two-hour calls in
mid-liquidity markets move, measured from the price the engine recorded just before it made the call, by more than a
declared trading-cost hurdle from the programme's cost model (1.3 cents; the tier's own spread would put it near 2.5)? A
counting check on 7-17 Nov data comes first; the expected answer is no." `next`: "Re-check of the second draft; design
freeze before 7 Nov; counting check on 7-17 Nov engine files; collection proposed 10-31 Dec (or 12 Feb - 5 Mar 2027)".
`family`: "economic"; `next_date`: "2026-11-07".

**Ledger block (draft, for the freeze; not applied):**
```
## LT14 second draft, 2026-10-30 (experiments autopilot; DRAFT, nothing counted)
- LIVE_TESTS_14.md second draft applies R1 (GO_WITH_CHANGES) MUST 1-7, SHOULD 1-10: k = 1 (10k-100k, H 1.30c, label-origin
  gross; tier-spread figure 2.48c printed beside it), >= 100k a reported arm; pinned P with an input-clock audit at the freeze
  (deadline 2026-11-07T00:00Z); exclusion order and tie-break; null worlds able to fail; M6 controls with LT13's aliasing rule;
  census span shared with LT12, tail to 11-17T04:31Z. P(census) 0.65; P(no test) about 0.35.
```

## 12. R1 response (`reviews/LT14_CHALLENGER_R1_2026-10-30.md`, GO_WITH_CHANGES; each item -> where it is applied)
| R1 item | Applied | Where |
|---|---|---|
| MUST 1 label-origin gross wording | "label-origin gross; it starts before the prediction exists; it is not an executable entry" in the estimand, title, header, 0, 1.4, 1.10 (Supported sentence), 8; "at the touch" only with that qualifier | header, 0, 1.4, 1.8, 1.10, 8 |
| MUST 2 input-clock audit | binding audit at the freeze; `P` refused -> `withdrawn_pre_census (input clock)`; designer pre-audit (se0 / se1 / se17 appear to pass; se18 appears to fail) | 1.3, 3, 6 item 1 |
| MUST 3 hurdle by its source | 1.30c = `2 x (2.04 - 1.34) - 0.10` from F4 / F5's spread; "most optimistic maker rung" deleted; 2.48c tier-spread figure printed beside every result and in the Supported sentence; `H` unchanged | 0, 1.8, 1.10, 1.11 M3, 8 |
| MUST 4 size check able to fail | null worlds put the move on the unit with twin mean 0; analytic-p share a binding diagnostic setting *analytic p oversized* | 1.9 |
| MUST 5 CH269 fee defect | cause referenced (ledger); census sums across captures with a unit test | header, 3, 6 item 3 |
| MUST 6 defective drafting count | "drafted on a defective count; \|s\| line unmeasured" (ledger, referenced); outcome not relabelled; binding \|s\| gate in the census; no re-read planned (rule for one stated); P(census) 0.80 -> 0.65 with reasons | header, 3, 7 |
| MUST 7 exclusion order and tie-break | seven ordered steps before the cut, the family rule after; the placebo recut with the same `market_id` tie-break | 1.5, 1.9 |
| SHOULD 1 k = 1 | >= 100k is a reported arm (M5); its census lines print-only | 0, 1.11, 1.12, 2, 3 |
| SHOULD 2 design MDE | `max(se_event, se_twoway, se_day)` | 3 |
| SHOULD 3 latency label | capture-level `L_c`, split of captures, numeric trigger (a) or (b) at 0.25c | 1.4, 1.10 |
| SHOULD 4 label rename | *census span shared with LT12* | 0, 1.1 |
| SHOULD 5 census tail | 00:31, 02:31, 04:31Z of 11-17; seal after the 04:31Z capture | 3, 6 item 2 |
| SHOULD 6 collinearity | M1 centred, zero-spread intercept implied; M6 controls listed, market constants left out, LT13's pivoted-QR rule with a drop order; `D_i` never dropped | 1.0, 1.11, 3 prints |
| SHOULD 7 attrlimit computing | the limit covers computing in any engine session; the hold already in `CANDIDATES.md` is referenced | 1.7, 5 |
| SHOULD 8 pinned `P`, deadline | "pinned `P`" throughout; freeze before 2026-11-07T00:00Z, with a lapse rule | 1.1, 1.3 |
| SHOULD 9 Supported sentence | `gbar - gbar_pl - H` and the M1 label in the same sentence | 1.10 |
| SHOULD 10 registry wording | "a declared trading-cost hurdle" (not "cheapest"), proposed text for the coordinator | 11 |
| Open questions 1-11 | answered per R1 | 10 |

**Not applied: none.** MUST 4's "set the twin's mean to 0" is implemented as the twin's raw mid change carrying no
sign-aligned component: the twin's sign-weighted expected mean is 0 by construction (shocks mean 0, independent of
`sign(s)`); its realised mean varies around 0 (re-check fix 3).

### 12.y Pre-freeze fixes (`reviews/LT14_RECHECK_PREFREEZE_2026-10-30.md`, FREEZE_AFTER_FIXES; reviewer's wording)
| Fix | Applied | Where |
|---|---|---|
| 1 (blocking) `mid_k` vs `ms_mid` float32 | `\|mid_k - ms_mid\| <= 1e-6` (float32 storage; exact equality is not expected) | 1.5 Gross; 3 primary lines; 7 item 4 |
| 2 (blocking) world 9 not a null | mean cell "`H` on labelled units (the unit term is shifted after attrition)"; diagnostic "world 9 unshifted: share Supported, printed, never a verdict change"; one-line justification | 1.9 table and diagnostics |
| 3 twin mean | "the twin's sign-weighted expected mean is 0 by construction (shocks mean 0, independent of `sign(s)`); its realised mean varies around 0" | 1.9 null worlds; 12 |
| 4 receipt clock | "'received' is the receipt clock of the record read (fetch time), not its venue event timestamp" | 1.3 audit bullet |
| 5 spread source | "`spread_k = ask_k - bid_k` from `quotes/<k>`" | 1.5 Spread |
| 6 F-MDE in the census | "the F-MDE uses planning `r` = 0.2; the census reads no twin value" | 3 Definitions |
| 7 per world type | "verdict size and the analytic-p share are computed per world type" | 1.9 size check |
