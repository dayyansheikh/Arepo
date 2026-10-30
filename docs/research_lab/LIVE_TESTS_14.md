# Live tests 14 (LT14): the engine at the touch (CH262), DRAFT pre-registration

**Status: DRAFT (first draft, 2026-10-30 05:30 UTC+1).** Written before challenger R1. Not frozen, not registered;
E-numbers unassigned; nothing counted; no LT14 code, seal or census run. Drafted on branch `feat/live-tests-14` from the
`chore/arepo-claude-setup` tip `c0818dfe`, as a design-only commit (like the first commits of LT3-LT13). LT14 takes the next
free E-number at its own registration. If its primaries all drop at the census, LT14 is not registered (a ledger line
records it; nothing is counted). Before registration it needs these steps, in order:
1. challenger R1 (`science-reviewer`), the designer's response, a re-check and a final pre-freeze verification;
2. the **design-text freeze commit**, with its sha256 recorded in the ledger. It fills in the pinned champion `P` (1.3) by
   `model_id` and `spec_sha256` and files the `attrlimit_lt14` request (section 5);
3. the census code only (section 3, with its seal helper), and a `science-reviewer` code-freeze check on synthetic data;
4. the census inputs' seal (once, after the census span and its lag slots end), then the counts-only census (once). The
   census fixes `k_tests`;
5. **only if a primary survives:** the size-check and analysis code, a second code-freeze check against the frozen text,
   the size check (1.9), a host dry run with peak RSS measured, the pins, and the ledger entry at least 24 h before
   `REGISTERED_UTC`.

Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. **No claim is made or implied about tradability, calibration, profit or a
lasting market advantage.** LT14 measures one number: the pinned champion's top-decile 2 h gross move in the direction it
predicted, at the mids the engine recorded, set against the cost rungs that `COST_MODEL.md` already declares. Every count
quoted from round 19, the CH269 map, the cost model or the ledger is a counts-only operational or development figure,
never a target. Every MDE is a planning estimate on stated assumptions. Writing this file involved no host, network,
`ssh` or `data-dumps` read, and no prediction, target, mid after an origin, outcome or P&L (reads listed in 9).

**What the CH269 map says (declared up front, not softened below).** The map is `reviews/CH269_MAP_2026-10-30.md` and
`seals/CH269_map_q0730.json`, section `champion_top_decile_ch262`. It covered 104 engine captures from 2026-10-21T12:31Z to
10-30T02:31Z, used `se0_champion_lr_mm`, and read counts only. Its numbers:
- **10k-100k tier:** top-decile units a capture min 95 / p25 140 / **median 175** / mean 172.2 / max 370. That clears round
  19's drafting line (>= 100), and the median-to-mean ratio of 1.02 shows a steady count. The busiest slot of day holds
  10.2% of the tier's units.
- **>= 100k tier:** **median 0, mean 0.78 a capture** (81 units in 104 captures; 56 captures had none). That is far under
  round 19's line for this tier (>= 10 a capture, >= 40 markets). On the map's numbers the >= 100k primary cannot enter, so
  **k is expected to be 1**.
- **Decile:** about 1,216 units a capture (median 1,218) from about 12,174 eligible non-sports ex-crypto rows. The decile
  sits mostly in the < 1k tier (median 687.5) and the 1k-10k tier (331.5). Round 19 planned 425 a capture in 10k-100k from
  the cost model's token shares; the map counts 175, so the decile under-weights the liquid tiers.
- **Tenure:** completed runs average 1.84 captures, and 66.6% last one capture. There were 16,934 distinct markets over the
  window, about 7.5 decile units per market in 104 captures.
- **Unavailable at k + 1** (quotes status codes): top-decile share 0.17% in 10k-100k (30 of 17,748), against 0.011% for the
  rest. The gap is 0.16 points (1k-10k 0.34, < 1k 0.20, >= 100k 1.24 on 80 units), well under round 19's 10-point census line.
- **Two map readings that differ from this design (disclosed, item 10.2):**
  - The map ranked the decile by **signed** `s` (`argsort(-s)`, `census_map_ch269.py` l. 843), so it counted the top decile
    of the "up" calls. CH262 and this design rank by `|s|`, and the `|s|` decile's tier split is **unprobed**.
  - The map's fee-class split adds up to **1,059 units** (about one capture's decile) against 126,477 decile units. It is
    not a usable planning count; its cause is not investigated here (10.10).

**The map is not the census.** Its span (10-21..10-30) is disjoint from LT14's census span `[2026-11-07, 2026-11-17)` (3),
so every LT14 gate is still declared before its own census. Every value near a map number is marked [map] in 4 and 9.1.

Source idea: `CREATIVE_HYPOTHESES_2026-11-02.md` (round 19), CH262, section 2 A, and the LT14 lines of sections 1 and 3.
This file follows round 14's rules 1-11, round 15's 12-14, round 16's 15-17, round 17's 18-20, round 18's 21-23 and round
19's 24-27 (rule 27 binds directly: LT14's inputs are the engine's own stores). It also keeps LT4's lessons L1-L15 and the
rulings LT7-LT13 carry. LT14 reuses `LIVE_TESTS_13.md`'s conventions (design text frozen 2026-10-30) unless a line here says
otherwise and why.

## 0. Summary

| Handle | Hypothesis (one-sided) | Unit (dependence) | Primary | Planning MDE (DE 5 / DE 31); quarter count; F-MDE | Rung `H` |
|---|---|---|---|---|---|
| **CH262-A** (10k-100k) | Over the window, the mean 2 h gross move `g` of the pinned champion's top `|s|` decile in the 10k-100k tier, taken in the predicted direction at recorded mids, **exceeds 1.30c**. That is the most optimistic maker rung: both legs passive, fills independent of the signal (`COST_MODEL.md` 5). | eligible non-sports ex-crypto market x capture in the top decile at k; **cluster: event**; two-way event x UTC day | the mean of `g` minus `H`, cluster-robust, one-sided `H1: E[g] > H` | median 175 a capture: **0.081c / 0.20c**; quarter 0.16c / 0.40c; F 0.13c / 0.32c (SD 1.3c; at 2 x SD, all double) | **1.30c** |
| **CH262-B** (>= 100k) | The same quantity in the >= 100k tier **exceeds 0.50c**, the tier's half-spread at p50. | as A | as A | map mean 0.78 a capture: **1.76c / 4.39c**; at the tier's own line (10 a capture) 0.49c / 1.23c, F 0.78c / 1.94c | **0.50c** |

- **Family:** one Holm family over the k surviving primaries, **k <= 2** (the two tiers), one-sided, familywise alpha 0.05.
  It is separate from E009-E011, LT2-LT13, E025 and E026. Each tier can be dropped on its own at the census (3). A dropped
  tier is `census_dropped` (uncounted, final); a failed coverage check is `census_unavailable (coverage)`. A primary that
  is unavailable or fails a size scenario enters Holm with p = 1. There is no replacement primary. The < 1k and 1k-10k tiers
  are reported arms only: their cheapest rungs are 2.4c and above, and the cost model's recommendation 2 already puts a
  gross under about 2c below a registered economic test there.
- **Window, parallel lane (proposed; the challenger rules, 10.1):** `REGISTERED_UTC` **2026-12-10T00:00Z**, `END_UTC`
  **2026-12-31T00:00Z** (21 days), single analysis on or after **2027-01-01T12:00Z**. This runs in parallel with LT12's
  window, on disjoint objects.
- **Window, ordered lane (fallback):** **2027-02-12T00:00Z..2027-03-05T00:00Z**, single analysis on or after
  **2027-03-06T12:00Z**.
- **Census:** on the engine's files of LT12's census span `[2026-11-07T00:00Z, 2026-11-17T00:00Z)`, for the decile's tier
  split and the origin-side gates only. No mid after an origin is read.
- **Labels certain in both lanes:** ***informed (LT12 census)*** (the census reads LT12's census span; no LT12 object is
  computed); *informed (CH269)* (the counts above were seen before every gate).
- **Honest priors (designer's judgement, section 7):**
  - P(census): 10k-100k **0.80**; >= 100k **0.02**.
  - **P(no LT14 test) about 0.20.**
  - Given registration, P(A Supported) about 0.08.
  - P(A below the rung, i.e. Contradicted) about 0.75.
- **Expected answer:** the gross is a few tenths of a cent, grows with the spread, and lies below 1.30c. In that case LT14
  closes the question of whether the current champion's strongest 2 h calls are worth anything at the touch. A Supported
  primary is an exploratory prospective finding. At most it nominates a later, separately registered maker-fill design with
  signal-conditional fills.

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)
`LIVE_TESTS_13.md` 1.0 applies unless 1.8-1.10 say otherwise. That covers: exact `%.17g` writes; NaN refusals; sealed inputs
re-hashed; slots from the seal; the pessimistic MDE gate `max(declared, design)`; a size check of >= 2,000 worlds at limit
0.058; spec and code pins; write-once series; clustering by the cluster unit, cluster x UTC day and UTC day, with p the
largest; Holm counted once; economics never changes a verdict; `DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)`; the lag-slot
loader; `T_X` conditions; the pinned sports and crypto classifiers; LT7's one-rule F; count gates on gross projected counts;
whether F binds is fixed now by design; distinct-cluster gates unprojected; `census_unavailable (coverage)` kept distinct
from `census_dropped`; Kish `G_eff >= 15`; NaN draws count as exceedances; untestable worlds count as rejections;
`analyze --out` is required and never overwrites; any dry run before the pin is logged. Round 19's rules map onto LT14 as
follows:

| Rule | LT14 |
|---|---|
| 1. Panel-complete units | every unit is a market x capture of the engine's complete-capture stores; no sweep, trade sample or monitor print |
| 3. Innovations, not levels | **not applied, and disclosed**: the primary is a level (a mean against a constant), as round 19 4.1 allows for CH262; no level is used as a contrast state |
| 5. Field semantics first | 1.3 (champion pin), 1.5 (tier, scope, the eligibility bit), 1.6 (status codes) |
| 7. DE and kill lines | `DE_gate` as 1.0; kill lines per tier (3) |
| 8. Floors | the 0.5c mid floor binds on the MDE and the F-MDE (3); the rung `H` is the tested constant, not a floor |
| 11. Economic check | this test *is* the economic check of the engine's `dir_2h` accuracy claim |
| 19. No resolution read by a live primary | none read; a market that closes before k + 1 is `unavailable_closed` (1.6) |
| 25. Zone floors | the 0.001-tick zone sits outside base eligibility (mid in [0.02, 0.98] excludes most of it); units with tick 0.001 are reported as an arm |
| 27. The engine's own stores | only files whose capture is at or before the origin feed the unit; only `P`'s visible files at its pinned spec; if `P` stops predicting, the unit is `unavailable`, counted, never filled; no new column, family or model |

### 1.1 Registration, lanes, single analysis
- **Parallel lane (proposed).** `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT14
  registration commit and **(b)** never earlier than **2026-12-10T00:00Z**. The proposal is 2026-12-10T00:00Z, with
  `END_UTC` 2026-12-31T00:00Z and the analysis on or after `END_UTC + 36 h` = 2027-01-01T12:00Z. The lane needs the
  challenger's explicit acceptance that LT14 and LT12 may run in the same days on disjoint objects (10.1). LT12 reads
  same-event spread innovations of two-member neg-risk pairs and sibling shocks on mixed ladders. LT14 reads the engine's
  prediction against the row's own next mid. The same market can appear in both, so the objects are disjoint but the
  markets are not.
- **Ordered lane (fallback, declared now).** It applies if R1 refuses the parallel lane, or if the registration commit is
  not at least 24 h before 2026-12-10T00:00Z. Then `REGISTERED_UTC` = the first 00:00Z at least 24 h after the later of
  LT13's fast-lane `END_UTC` (proposed 2027-02-11T00:00Z) and the registration commit, and never before 2027-02-12T00:00Z.
  The window lasts 21 days, with a single analysis >= 36 h after the end. The census of 3 stands unchanged in both lanes,
  because it reads no target, so a later window does not wear it. A pin after LT12's analysis (`T_LT12`) adds
  *informed (LT12)*.
- **Adjacent analyses** (`T_X` = the earlier of X's analysis job start and its analysis commit):

  | Adjacent | Why | Consequence |
  |---|---|---|
  | **LT12 census** (`T_LT12c`, about 2026-11-18) | LT14's census reads the same span (engine files only) | *informed (LT12 census)*, certain in both lanes; no LT12 census output is read by any LT14 designer before the freeze |
  | **LT12** (`T_LT12`, about 2027-01-01T12Z) | same days in the parallel lane | parallel lane: none (both analyses after their own windows); ordered lane: *informed (LT12)* |
  | **LT13** (fast lane 2027-01-21..02-11) | ordered lane follows it | time only; no LT13 object (`batch`) computed |
  | **LT11** (11-18..12-09), LT10, E026 (to 12-07), E015, E022 | time only, or different states | none computed; no E026 frozen module edited (1.11) |
  | **The engine's own leaderboard** (`dir_2h` log loss, daily) | a public accuracy measure of the same predictions | not a cents measure; visible to everyone as the engine's operation; LT14 reads none of it as an input and never as a result |
- **Boundary.** The first origin is the first capture whose start is at or after `REGISTERED_UTC`. The last origin is the
  last capture starting before `END_UTC`; its k + 1 (target) and its k + 2 and k + 3 (F twin) are read through the lag-slot
  loader.
- **Design-text freeze.** After the final pre-freeze verification accepts, a commit records this file's sha256 in the
  ledger and fills `P`. After that the text changes only by the census-fixed values named in 3, and by code-check fixes
  that change no unit, target, estimator, gate, threshold or verdict rule (1.13).
- **Fixed end, no extension; one analysis.** `run_live_tests14.py analyze` refuses before the analysis date, requires
  `--out`, and refuses to overwrite (exit 2). The spec's `k_tests`, `dropped_tests` and `census_unavailable` lists are
  mutually exclusive.
- **Time of year (disclosed).** The parallel window holds the December holidays (thin books from 12-24); the ordered
  window holds no US federal election. There is no DST change in the census span or either window.

### 1.2 Stores read (all already written by the host's pass and the engine's tick; no new collector, no network)
- **Engine stores** (`signal_engine/`, write-once, `DESIGN_V1.md` 1, 6):
  - `predictions/<capture>/<P>.parquet`: the uint16-quantised `p_up`, `p_down`, `p_flat` and the eligibility bit;
  - `logs/predictions-YYYYMMDD.jsonl`: the first valid log line per (capture, `P`) is the **receipt time**, plus spec sha,
    fit id and features sha;
  - `quotes/<capture>.parquet`: `market_id`, `t_off`, `bid`, `ask`, `st`, where `st` is 0 ok, 1 closed, 2 inactive,
    3 one-sided;
  - `features/<capture>.parquet`: `market_id`, `event_id`, `category`, `ms_mid`, `ms_spread`, `ms_log_liq`,
    `ms_hours_to_end`, `ms_rv24`, `ms_tick`, `mo_d2h`, `t_row`, `end_ts`;
  - `meta/<capture>.json`: slot, capture start and finish, sha256s;
  - `specs/registry.json`: `P`'s `spec_sha256`;
  - `champion/history.jsonl`: champion changes, **disclosure only** (1.3).
- **Capture sidecar** `rows_ext.csv.gz`. Read only for the scope classifiers (`fee_type`, `fee_category`, `series_slugs`)
  and the served-fee cost line (`fee_schedule`, `fees_enabled`), never as a state or target. In the window these fields
  are extracted on arrival (1.14). In the census they come from the sealed span, where a byte-identical copy restored for
  LT12 or LT13 is accepted after a sha256 check.
- **Not read:** snapshot `rows.csv.gz` prices (the engine's `quotes/` and `features/` already hold the mids it recorded);
  sweeps; trade samples; the monitor; `cross_venue_live/`; `xv_quotes/`; `surprise_live/`; `aux/`; the label store and
  label logs (LT14 computes `g` from `quotes/`, not from the engine's 3-class label); `leaderboard/`; `dashboard.json`; any
  other model's predictions; `live_tests2/` .. `live_tests13/`; the CH240, CH251, CH261 and CH269 map outputs beyond the
  bounded section named above; Gamma outcome fields. **No LT11, LT12 or LT13 object is computed or read.** J4-R and
  CB13-T's holdouts are untouched; LT14 holds no maker mark-out object.

### 1.3 The pinned champion `P` (pinned champion only)
- **Definition.** `P` is the model that `champion/history.jsonl` records as champion at the **design-text freeze commit**,
  pinned in the frozen text by `model_id` and `spec_sha256` (as `specs/registry.json` holds it), with `FEATURES_VERSION`.
  Today that would be `se0_champion_lr_mm`. The first promotion read (`se-promotion-v2`) is due about 2026-11-04, so `P`
  may be `se1_lgbm_mm`, `se17_lgbm_mm_900k` or `se18_lgbm_all_b0` if a promotion happens before the freeze. The rule
  fixes `P` before any LT14 count either way.
- **The deployed object.** `P` is read at its pinned spec, with the walk-forward fits the engine makes on its own schedule
  (`DESIGN_V1.md` 5). Refits are part of the object as deployed. The fit id of every file is recorded, and the per-day
  decile composition is printed (world 8). A prediction file whose spec sha differs from the pin is not `P` (`spec_mismatch`,
  counted; the unit is `unavailable_spec`).
- **Champion changes during the window (declared rule).** LT14 reads **`P` only**, whatever the engine's champion becomes.
  A promotion inside the census span or the window changes nothing in LT14: it is recorded with its capture in the
  analysis output under the label *champion changed in window*, and that label never changes a verdict. If `P` stops
  writing prediction files (retired, disabled or embargoed), every later unit is `unavailable_spec`, counted, never filled
  from another model. If `P`'s files cover fewer than 80% of window captures, the primary is Unavailable (1.10). No LT14
  line promotes, demotes or refits a model; no engine gain or loss changes an LT14 verdict.
- **Embargo.** `P` must not be embargoed at the freeze (today's candidates are not). If an embargo entry is ever added for
  `P`, LT14 still reads its files under the registered role, and no LT14 number is displayed (5).

### 1.4 Clocks, slots and the decision time
- **Slots:** as LT3-LT13 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). A missing
  slot leaves every quantity that needs it NaN (counted), never interpolated.
- **Decision time:** the receipt time of `P`'s prediction file for capture k (the first valid log line, 1.2). The engine
  writes it after capture k's features. Every state input sits at or before capture k: the prediction, `features/<k>`,
  `quotes/<k>`, and the sidecar at k.
- **On time:** the unit exists only if `P`'s file for k was logged before slot k + 1's time (the engine's own rule,
  `DESIGN_V1.md` 6). A late file gives no unit and is counted as `late`.
- **The horizon rule (S45, round 19).** `g`'s end point is the mid in `quotes/<k + 1>`. The row's own receipt time,
  `t_row(k + 1) = capture start(k + 1) + t_off`, minus `t_row(k)` (from `features/<k>`) must lie in **2 h +/- 15 min**;
  otherwise the unit is `unavailable_timing` (counted).
- **Execution latency (disclosed; item 10.6).** `g` starts at capture k's recorded mid, which is the engine's label origin
  and is earlier than the decision time. So `g` credits any move between the row's receipt at k and the prediction write.
  The census and the analysis print the latency `L = receipt(P, k) - t_row(k)` (per capture: min / median / p90). The
  analysis reports the primary on units with `L` at or under the census median as a sensitivity, under the label
  *latency-sensitive* (1.10). No later quote at or after the decision time exists in the engine's stores, and none is
  taken from another stream.

### 1.5 Eligibility at <= k and the unit
Everything below is read at capture k or earlier.
- **Engine eligibility:** `P`'s eligibility bit = 1 at k. That is base eligibility, `DESIGN_V1.md` 2: binary, open,
  active, two-sided, spread <= 0.10, mid in [0.02, 0.98], end after the origin, and no UMA proposal in the origin sidecar
  row. On top of it, `dir_2h` eligibility (scheduled end after slot k + 1, or unknown).
- **Scope (a parameter; `scope: non_sports_ex_crypto` at the freeze):**
  - The pinned sports classifier `cb17_census.is_sports_sidecar(fee_type, fee_category, series_slugs)` is vendored by hash
    and applied unchanged to the values served after the 2026-10-20 fee step, as `LIVE_TESTS_13.md` 1.4 does. So the about
    1,800 markets q0717 saw re-classified count as non-sports (disclosed).
  - Crypto is excluded by LT13's pinned classifier; unknown is counted and treated as crypto.
  - A unit with no sidecar row is `sidecar_missing` (excluded, counted).
  - The census prints the confusion table of the engine's own `category` against this classifier (item 10.8). The sports
    and crypto arms are the same reader under `scope: sports` / `scope: crypto`; they are reported and not counted.
- **The decile.** `s = p_up - p_down` from `P`'s file (uint16 / 65535 as stored; never recomputed).
  - Within capture k, over the in-scope eligible on-time units (all tiers together), the top `ceil(n / 10)` by `|s|` form
    the **top decile**. Ties are broken by `market_id` ascending, a stable sort. A unit with `s = 0` exactly has no
    direction and is excluded (`s_zero`, counted).
  - Middle deciles 4-6 (the secondary's comparison) and the `P(flat)` deciles (M2) are cut the same way.
- **Tier:** the cost model's bins on `expm1(ms_log_liq)` at k, i.e. the row's Gamma `liquidity` as the engine stored it:
  `< $1k`, `$1k-10k`, `$10k-100k`, `>= $100k`. A NaN liquidity is `tier_na` (excluded, counted).
- **One row per `market_id`** per capture. The event key is `event_id` from `features/<k>` (the engine's; -1 means
  unknown, and those units cluster on the market).
- **Series family rule** (LT convention): a series family holding more than 40% of a tier's census top-decile units is
  excluded from that tier (`<tier>.exclude_family`, census-fixed).
- **Unit:** an in-scope market x capture k in the top decile, in tier T, with every field above finite.
- **Gross:** `g = 100 x sign(s) x (mid_{k+1} - mid_k)` in cents. `mid = (bid + ask) / 2` from `quotes/<k>` and
  `quotes/<k + 1>`, both as the engine wrote them (`mid_k` equals `ms_mid`; the census checks equality on every unit).

### 1.6 Outcome classes at k + 1 (write-once, never imputed)
Every unit gets one write-once class:
- `labelled`: `st = 0` in `quotes/<k + 1>` and the horizon rule holds. **Only these have `g`.**
- `unavailable_one_sided` (`st = 3`), `unavailable_closed` (`st = 1`), `unavailable_inactive` (`st = 2`).
- `unavailable_absent`: not in `quotes/<k + 1>`.
- `unavailable_missing_capture`: no complete capture in slot k + 1 within tolerance, or none 3 h after the slot.
- `unavailable_timing`: the horizon rule fails (1.4).
- `unavailable_spec`: `P` missing or at the wrong spec at k.

`late` and `s_zero` are counted before the unit forms.

**The unavailable classes are counted and reported separately, by tier and decile, and never enter the mean.** CH269 shows
small gaps (0.16 points in 10k-100k), so the attrition rule is: if the top decile's unavailable share exceeds the rest of
the tier's by more than 2 points in the window, the label is *attrition-differential*. The analysis always prints
**worst-case bounds**: every unavailable unit is set to its least favourable move (`-100 x mid_k` for an up call,
`-100 x (1 - mid_k)` for a down call, i.e. the price going to the losing extreme) and to its most favourable move. If the
lower bound falls below `H` while the primary clears it, the label is *attrition-sensitive*. Neither label changes a
verdict.

### 1.7 What is not looked at before the analysis date
- No mid after an origin, `g`, decile mean, regression, plot or cents summary of `P`'s predictions by tier, from the
  census span or the window, by any LT14 designer, coder or reviewer.
- During the window, only `run_live_tests14.py ops-stats`: file, line, class and status counts. It reads no price, spread,
  liquidity or `s` value (unit test).
- No change of `H`, thresholds, scope, decile rule, estimators or k after registration.
- Nobody opens the census-span engine files or sidecars before the LT14 seal commit, except the schema pre-check (column
  names and types only) and the seal's sha256 checks.
- No LT14 designer reads LT12's census output before the freeze, or E015's, E022's, LT9's-LT13's analysis outputs before
  the pin.
- The designer has read the engine's STATUS lines (the LightGBM models lead the champion by about 0.045 nats on `dir_2h`
  over 9 days). That is not by tier and not in cents; disclosed.

### 1.8 Estimand, estimator and inference (per tier T)
- **Estimand:** `theta_T = E[g | top decile, tier T, labelled] - H_T`, with `H_A = 1.30c` (10k-100k) and `H_B = 0.50c`
  (>= 100k), both **fixed constants declared now** from `COST_MODEL.md` 4-5. The census recomputes the rung constants from
  its own recorded touches with cost-model-v1 formulas and prints them; **they never replace `H`** (4 item 3).
  **H1 (one-sided): `theta_T > 0`.**
- **Estimator:** the unweighted mean of `g` over the tier's labelled units, minus `H_T`. Every unit weighs one share at
  the touch, size-unlimited. That is "touch, size-unlimited" in the cost model's words (rule 3 of `COST_MODEL.md` 6).
- **Standard errors and p (L10, as LT13 1.7):**
  - CR1 on **event** (`G - 1` df t);
  - two-way event x UTC day (normal);
  - UTC day (t with `G_day - 1` df).
  - **One-sided p = the largest of the three.** The conservative 95% CI is the hull of a 2,000-draw event-cluster
    bootstrap (seed 20261814) and the three Wald intervals. `G_eff` (Kish, on event unit counts) is printed and floored at 15.
  - Why event: markets of one event share news. A market re-enters the decile across captures, a 1.84-capture mean run
    in CH269, so units of one market are dependent. Event clusters nest markets. The day term holds venue-wide shocks: the
    decile is cut within a capture, so all units of a capture share its common move.
- **Sports arm (uncounted):** clusters are the event (the game) and the **fixture day** (the game's scheduled UTC day from
  `end_ts`), two-way, p the largest.
- **Dependence sensitivities (reported, never the verdict):** clusters on capture; market; event x two-day block.
- **MDE multiplier** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (LT7-LT13), not lowered for k <= 2.

### 1.9 Placebo, F and the size check
- **Placebo: the shuffled prediction file** (round 19 0.0 item 6: the placebo lives on the same units). The draw runs
  this way:
  1. Within each capture x tier stratum, the in-scope eligible units' `s` values are permuted across units (seeded, 200
     draws). Each unit keeps its own mids, timing and class.
  2. The placebo top decile of tier T is the tier's units whose shuffled `|s|` reaches capture k's real top-decile cut-off.
     The count matches the real one exactly, because the multiset of `s` in the tier is unchanged.
  3. `g_pl = 100 x sign(s_shuffled) x (mid_{k+1} - mid_k)` on labelled units. `gbar_pl` is the mean over draws of the
     placebo decile's mean.

  The shuffle breaks the link between a unit and its own prediction while keeping each stratum's mix of signs and
  magnitudes. What survives it is a common direction (the decile's predominant sign meeting a venue-wide drift) or a
  measurement artefact.
  **Binding point condition (two-sided, LT12 R1 MUST 5's form):** `|gbar_pl| < 0.5 x gbar`.
  **Diagnostic (reported, not a gate):** `p_shuffle = (1 + #{draw mean >= gbar}) / 201`.
- **F (LT7's one-rule form; binding for both tiers, fixed now; round 19 4.1).**
  - The twin is the same units' `g_tw = 100 x sign(s_k) x (mid_{k+3} - mid_{k+2})`. It is NaN unless the unit is `st = 0`
    at k + 2 and k + 3, each horizon rule holds, and the scheduled end is after k + 7 h (else `f_end_short`).
  - `Delta = gbar_lead - gbar_twin`, both on units that have both terms.
  - **F holds iff Delta's one-sided p < 0.05** (1.8's rule; not Holm-adjusted; counted 0) **and `Delta_hat >= 0.5 x
    gbar_lead`**. An arm with < 50% of the primary's units is *falsification unavailable*.
  - Why: a slow per-market drift that the champion's momentum inputs pick up gives `g` at every lag. F asks that the gross
    belong to the horizon the engine predicts (item 10.3 asks whether binding F is too strict for an economic level).
- **Size check, after the census, on the code to be pinned:** **2,000 worlds, seed 20261814**, limit **0.058**, 200
  placebo draws per world.
  - **Verdict size** = the share of worlds in which the analytic one-sided p (1.8) is < 0.05 **and** F and the placebo
    condition hold.
  - Untestable worlds count as rejections. A failing scenario makes the tier "SE check failed (size scenario)": p = 1 in
    Holm, k unchanged, no rerun, reseed or variant.
  - Common to every world: the census's event-size distribution and tier unit count; 252 captures; 10% of units removed at
    random; drifts and shocks drawn per cluster inside that cluster's loop.

  | # | World | True mean of `g` | What it checks |
  |---|---|---|---|
  | 1 | boundary null: event shocks N(0, 0.5c), day shocks AR(0.5) SD 0.3c, unit noise SD 1.3c | `= H` | the three-way p at the census's `G` |
  | 2 | heavy tails: unit noise t(3) scaled to SD 1.3c plus 1% jumps of +/-30-60c, symmetric about `H` | `= H` | small-sample t with jumps |
  | 3 | concentration: 10% of events hold 50% of units (or the census's top-decile event concentration if larger), event mean shifts N(0, 0.5c) | `= H` | CR1 with a few large clusters |
  | 4 | **S44 stale side:** `g = 0.4 x spread_k + noise`, spreads from the census's top-decile spread quantiles, shifted to mean `H` | `= H` | spread-linked heteroskedasticity |
  | 5 | **per-market drift (M-Q):** a per-market AR(0.99) drift, SD 1.0c, aligned with `sign(s)`, entering lead and twin alike | `= H + 0.5c` | F must block it |
  | 6 | **common direction:** a venue-wide drift `D_t` (AR(0.9), SD 0.5c) aligned with the decile's predominant sign at the census's up / down share, no unit information | `= H + 0.5c` | the placebo must block it |
  | 7 | **S45 label timing:** 5% of k + 1 rows received 2 h + 20-40 min after k, with SD x 2 | `= H` on the 2 h rows | the horizon rule |
  | 8 | **S46 spec change:** a refit at day 11 re-ranks `|s|` (rank correlation 0.5 with the old ranking) | `= H` in both halves | composition shift |
  | 9 | **differential attrition:** units with `g < H - 2c` go unavailable at 10 x the census's top-decile share, others at the census share | `= H` before attrition | selection on k + 1 availability |

  Diagnostics, not criteria: a planted-effect power run (500 worlds, true mean `H + 0.25c`, seed `20261814 x 100 + 51`),
  and world 4 with the M1 slope printed.

### 1.10 Verdicts and labels (per tier, after Holm over k)
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, `theta_hat > 0`, F holds, the placebo
  condition holds, and the size check passed. Its text reads: "*the pinned champion's top-decile mean 2 h gross at recorded
  mids exceeded the {1.30c / 0.50c} rung in tier T over the window (touch, size-unlimited; no fills measured)*". It never
  says "route", "tradable" or anything stronger.
- **Contradicted (below the rung):** the conservative 95% CI of `gbar` lies entirely below `H`. This is the expected
  outcome, and it is a result: "the gross does not reach the most optimistic maker rung".
- **Inconclusive:** otherwise. If F fails or is unavailable, *mechanical null not excluded* (or *falsification
  unavailable*). If the placebo fails, *common direction not excluded*.
- **Unavailable:**
  - A: < 15,000 labelled units, < 200 events, `G_eff` < 15, < 10 UTC days with units, or `P`'s files on < 80% of window
    captures.
  - B: < 2,000 labelled units, < 40 distinct markets, or the same day and file floors.
  - Why 15,000 for A: at `n_eff` 12,000 and DE 5 the F-MDE is `5.205 x 1.3 x sqrt(5 / 12,000) x 1.58` = 0.22c, still under
    the 0.5c floor at twice the planning SD.
- **Labels (never change a verdict):** *spread-scaling consistent* (M1: slope one-sided p < 0.05 and intercept CI
  including 0); *latency-sensitive* (1.4); *attrition-differential*, *attrition-sensitive* (1.6); *champion changed in
  window* (1.3); *informed (X)*; *analytic p oversized in simulation*; *underpowered* (the window's MDE above `0.5c`);
  *series-concentrated*; *fee regime changed* (1.13).

### 1.11 Secondaries and economics (reported; count 0; never change a verdict)
- **M1, the spread-scaling alternative (round 19, Roll 1984).** Within each tier's top decile: OLS of `g` on `spread_k`
  (cents) with an intercept, CR1 on event. The stale-side world predicts an intercept near 0 and a slope of about 0.3-0.5.
  The output prints the intercept, the slope, and the share of `gbar` that `slope x mean spread` accounts for. Also
  printed: the primary on spread terciles of the tier.
- **M2, the flat decile (the maker's selection).** Within capture x tier, the top and bottom deciles of `P(flat)` (`p_flat`
  as stored). The output prints the share of labelled units with `|mid_{k+1} - mid_k| <= spread_k / 2` in each, their
  difference with an event-CR1 CI, and mean `|Δmid|`. A maker quoting both touches is not picked off when the move stays
  inside the half-spread. This is a selection fact, not a fill measurement.
- **M3, the cost ladder, all at recorded touches, cost-model-v1 constants:**
  - `gbar - H_j` with CIs for every rung of `COST_MODEL.md` 5: 0.65c (maker entry held to resolution; a 2 h gross is not a
    hold gross, so this is printed only), 1.30c, 2.41c, 2.84c, 3.18c, 3.52c, and the tier's $100 taker round trip p50
    (3.9c for 10k-100k, 2.9c for >= 100k).
  - The per-unit taker round trip `spread_k + fees on both legs`, computed twice: at the docs rate (`conservative` policy:
    max of schedule and docs rate) and at the served `fee_schedule` rate (0 on most non-sports rows since 2026-10-20). Its
    mean `g - c_taker` is printed both ways.
  - The cost formulas are a **vendored copy** in a new LT14 file, with the source sha of `costs.py` recorded. A unit test
    checks equality against `costs.cost_check` on synthetic inputs. **No E026 frozen module is edited** (`costs.py` is
    E026-frozen; item 10.9 asks whether a read-only import is acceptable instead).
- **M4, arms by fee class and category:** fee class at k (served rate 0, > 0, unknown) and the engine's `category`.
- **M5, other arms:**
  - the up and down calls separately;
  - the **signed** top decile (the CH269 map's reading);
  - a within-tier decile (the top `|s|` decile cut inside each tier);
  - the display pool (spread <= 2c);
  - tick 0.001 units;
  - the < 1k and 1k-10k tiers against their own rungs;
  - B's numbers when B is dropped at the census (descriptive);
  - the sports and crypto arms.
- **M6, within-market secondary (round 19).** The top decile's `g` against the middle deciles' (4-6) in the same market x
  UTC day, by expanding-past demeaned OLS. Freedman-Lane gate on market x UTC-day strata (200 draws). Reported only.

### 1.12 Overlaps, dependence and counting
| LT14 | Closest prior | Same contrast? | Why not a double count |
|---|---|---|---|
| CH262 | LT12 CH245 / CH244 (spread innovations; parallel lane) | no: LT14's target is the mid move in the engine's direction | different object; same markets possible; the census prints the share of LT14 census units in two-member neg-risk events (no LT12 object computed) |
| CH262 | F4 / F5 (`COST_MODEL.md` 5; development) | no: those are flow interactions at 6 h on history | prospective, engine's own predictions, 2 h |
| CH262 | the engine's leaderboard | no: log loss on a 3-class label | LT14 reads no score; a verdict never promotes |
| CH262 | E002 (1 h reversal; ledger) | no | different signal and clock |

**Counting:** the analysis adds **k counted tests**, kind `live_tests14` (a fail-closed `battery2.KIND_RULES` entry).
Placebo, F, secondaries, arms, economics, the census, the CH269 map and the size check count 0.

### 1.13 Stop rules and deviations
- **Stop rules (LT13 1.12):** no interim look; the test runs to `END_UTC` whatever the counts. After 7 days, a tier whose
  units run below one third of its census projection gets the ledger note "likely Unavailable" and nothing else changes.
  Any change to a pinned file makes the analysis refuse. The reader refuses above 1.0 GB in `live_tests14/`.
- **Deviations (LT13 1.13 unchanged):**
  - Operational losses stay missing and are counted, never refilled from another stream.
  - A venue-side fee or category step like 2026-10-20's is recorded within 24 h. Values are read as served, and the label
    is *fee regime changed*.
  - Before the freeze: draft revisions mapped to the reviewer items.
  - After the freeze: written justification, `science-reviewer` acceptance, a new sha and the label *amended after freeze*.
  - After the census commit: no gate or definition change; a defect gives `census_dropped (defect)` for that tier.
  - After the pin: none; a defect gives "SE check failed (deviation)", with p = 1.

### 1.14 Retention and the write-once extraction
- **The constraint.** Engine retention is not yet active: the owner's decision on the drafted 35-day rule for
  `predictions/` and 45 days for `quotes/` and `features/` is due by about 11-15 (`signal_engine/STATUS.md`), and deletion
  happens only after a verified release. Snapshot sidecars are deleted after 8 days.
- **Window reader (light; `mem_mb` < 500; `net` lane or cron).** Every 2 h, for each new complete capture whose `P` file is
  logged, it writes **write-once** (`%.17g`, atomic hard link) to `live_tests14/series/<capture>.parquet`:
  - one line per in-scope eligible unit, with `market_id`, `event_id`, `s`, `p_flat`, the prediction receipt time, fit id,
    spec sha, `mid_k`, `bid_k`, `ask_k`, `t_row(k)`, tier inputs, `ms_hours_to_end`, `ms_rv24`, `ms_tick`, the sidecar's
    `fee_type`, `fee_category`, first series slug, `fee_schedule` and `fees_enabled`;
  - then the k + 1, k + 2 and k + 3 status, mid and `t_row` lines for earlier units, once those captures' `quotes/` exist.

  Every value is copied as the engine wrote it; nothing is recomputed or re-scored. `g` is computed only at analysis time,
  from these series files.
- **Lag guard:** above 72 h of complete-but-unextracted captures the reader writes a ledger alert (`lt14_lag`). One-shot
  restore from the verified release (sha256-equal) as LT13 1.14. A capture found nowhere is `unavailable_missing_capture`,
  never awaited and never reconstructed.
- **No retention rule covers `live_tests14/`** before the analysis is committed.

## 2. Planning counts and MDE (planning only; the map counted the decile, never an effect)
**Formula (round 19 0.3, a level against a constant):** `MDE = 3.47 x 1.5 x SD x sqrt(DE / n_eff)`, with `n_eff = 0.8 x n`,
and `VIF_w` = 1 because the primary has no regressor. `F-MDE = MDE x sqrt(2 / (1 - max(0, r)))`, with planning `r` 0.2,
giving x 1.581.

**Design effect, stated.** `DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)`, where `m_21` is the size-weighted mean event cluster
size projected to 21 days.
- From CH269: 126,477 decile units / 16,934 markets = 7.47 units per market in 104 captures, about **18 per market in 252
  captures** (an upper value, since markets resolve).
- With 1-5 decile markets per event (unprobed), `m_21` is about 18-90, and the formula gives DE **1.3-2.8**.
- **So the floor 5.0 binds at planning.** The whole-panel convention **DE 31** is quoted beside it.
- The 0.02 within-event correlation is an assumption. For a level, shared news inside an event may push it higher; the
  three-way p (1.8) carries that risk in the verdict, and the DE 31 column shows the pessimistic plan.

**SD.** The cost model's 2 h mid SD by tier is 1.3c (10k-100k) and 1.9c (>= 100k). The decile is chosen partly on recent
moves, so its SD may be higher, and every MDE is also given at 2 x SD.

| Tier, count | n (252 captures) | n_eff | MDE DE 5 / DE 31 (SD 1.3c or 1.9c) | F-MDE DE 5 / DE 31 | at 2 x SD (MDE DE 5 / DE 31) |
|---|---|---|---|---|---|
| A, median 175 a capture [map] | 44,100 | 35,280 | **0.081c / 0.20c** (`5.205 x 1.3 x sqrt(5 / 35,280)` = 0.0806) | 0.13c / 0.32c | 0.16c / 0.40c |
| A, p25 140 a capture [map] | 35,280 | 28,224 | 0.090c / 0.22c | 0.14c / 0.35c | 0.18c / 0.45c |
| A, quarter of the median | 11,025 | 8,820 | 0.16c / 0.40c | 0.26c / 0.63c | 0.32c / 0.80c |
| B, map mean 0.78 a capture [map] | 197 | 157 | 1.76c / 4.39c | 2.79c / 6.94c | - |
| B, at its line 10 a capture | 2,520 | 2,016 | 0.49c / 1.23c | 0.78c / 1.94c | - |

**Readings.**
- A's precision is not the risk. At the planning median, the test resolves `gbar` to about a tenth of a cent against a
  1.30c rung at DE 5, and a fifth of a cent at DE 31.
- B cannot enter on the map's count. Even at its own line of 10 a capture its F-MDE is 0.78c, over the 0.5c floor. B
  needs about **24 units a capture** to pass the F-MDE gate at DE 5 (`2,016 x (0.779 / 0.5)^2 / 0.8 / 252`).
- Round 19's planning (425 and 20 a capture from token shares) is superseded by the map [map].

## 3. Pre-registration census (counts only; once; before registration; no target read)
The census runs once on the sealed inputs. It reads origin-side fields of capture k. The only later-slot fields it reads
are the `quotes/` **status codes and row receipt offsets** at k + 1, k + 2 and k + 3, for the unavailable shares and the
horizon rule. It reads no bid, ask or mid of a later slot (unit test). It prints counts, is committed with its sha256
before the registration commit, and **every threshold below is stated now**. A failed line drops that tier
(`census_dropped`, uncounted).

**Inputs.**
- Span **`[2026-11-07T00:00Z, 2026-11-17T00:00Z)`**, 10 UTC days, 120 slots, plus the 3 slots after it (to
  2026-11-17T06:31Z) for k + 1..k + 3 status only. That is before LT11's window opens (2026-11-18).
- Engine files: `predictions/<cap>/<P>.parquet`, the predictions log lines, `quotes/`, `features/`, `meta/` for those
  captures (on the host within retention, else restored once from the verified release).
- Sidecars `rows_ext.csv.gz` of the span (scope and fee fields), with byte-identical LT12 / LT13 copies accepted after a
  sha256 check.
- The seal records files, sha256s, slot assignment, `P`'s spec sha and the frozen LT14 design-text sha256. It is sealed
  once, after 2026-11-17T08:31Z.
- The census never runs while another memory-heavy job runs.
- **What the census code must refuse:** an input not in the seal; a seal whose design-text sha is not the ledger's; any
  later-slot price; any `g`; any LT11-LT13 object; a second run.

**Coverage first.** Covered days (covered origins / 12) must be **>= 7.0**, and `P`'s on-time files must cover **>= 90%**
of census captures. If either fails, LT14 is `census_unavailable (coverage)` and nothing else is printed.

**Definitions.** Projection = count x 21 / covered days. Per-capture statistics are over covered captures, zeros included.
The **declared MDE** is section 2's formula at the census's projected `n_eff`, `DE_gate` and
`SD_plan = max(tier SD of 2, 100 x SD of mo_d2h over the tier's census top-decile units)`. `mo_d2h` is the own 2 h mid
change over (k - 1, k], an origin-side quantity. The **design MDE** is `3.47 x 1.5 x se`, with `se` the event-CR1 standard
error of a mean computed from the census's event sizes at `SD_plan`. The MDE gate uses `max(declared, design)`.

| Tier | Lines (all must hold; NaN fails) | Map number nearby (planning only) |
|---|---|---|
| **A (10k-100k)** | <ul><li>**median top-decile units a capture >= 100** (round 19's line, on the `\|s\|` decile)</li><li>projected labelled-eligible units >= 25,200</li><li>**non-stationarity:** per-capture median >= 0.25 x mean</li><li>**venue clock:** no slot of day > 50% of units</li><li>distinct events >= 300 (unprojected)</li><li>Kish `G_eff` >= 15</li><li>**unavailable gap** (top-decile minus rest-of-tier unavailable share at k + 1) <= **10 points** (round 19)</li><li>finite tier on >= 95% of in-scope eligible rows</li><li>`mid_k == ms_mid` on 100% of units</li><li>**MDE <= 0.5c and F-MDE <= 0.5c** at the computed `DE_gate` and `SD_plan`</li></ul> | 175 median (signed decile), ratio 1.02, max slot 10.2%, gap 0.16 points |
| **B (>= 100k)** | <ul><li>**median top-decile units a capture >= 10** and **>= 40 distinct markets** (round 19)</li><li>every A line except the counts, with distinct events >= 40</li></ul> | median 0, mean 0.78, 80 units |

- **Census-fixed values (exhaustive):**
  1. `k_tests`, `dropped_tests`, `census_unavailable` (mutually exclusive).
  2. `<tier>.exclude_family`.
  3. The world inputs:
     - the event-size distribution of each tier's top decile (quantiles q10..q90 and the top-10% share);
     - the top-decile spread quantiles q10..q90 (cents);
     - the up / down share;
     - the top-decile unavailable share;
     - the latency median (1.4).
  4. `SD_plan` per tier.

  `DE_gate`, the MDEs and the recomputed rungs are recorded gate values, never re-used to change a threshold.
- **Prints (descriptive):**
  - **Units per capture by tier** (min / median / mean / max), by tier x fee class (served rate 0 / > 0 / unknown, from
    the sidecar), by tier x engine category and x the pinned classifier (the confusion table), by up / down sign, and for
    the **signed** decile (the map's reading) beside the `|s|` decile.
  - Distinct markets and events per tier.
  - **Tenure** (completed and open runs).
  - **Unavailable shares by class**, decile and tier.
  - Latency `L` per capture.
  - `VIF_w` of decile membership against `spread_k`, `log1p liquidity` and `z log rv24` (for M6).
  - The rung constants recomputed from the span's recorded touches (cost-model-v1 formulas, both fee readings).
  - `P`'s spec sha per capture and any `spec_mismatch`; champion changes in the span.
  - The share of units in two-member neg-risk events (the LT12 overlap print).
  - The sports and crypto arms' counts.
- **Expected fates (declared now):**
  - A passes unless the `|s|` decile shifts strongly toward small books. The map's signed decile gives 175; the `|s|`
    decile adds the down calls, and its tier split is unprobed.
  - **B is expected to be `census_dropped`** on its count line (map mean 0.78 a capture), so k = 1 is the expected
    registration.

## 4. Design changes from the round-19 sketch (made before any LT14 data; each needs the challenger's acceptance)
1. **`DE_gate` floor 5.0** (LT13 1.0) in place of the sketch's 1.98, with DE 31 beside it. More conservative.
2. **Planning counts from CH269** [map]: 175 a capture in A (not 425) and 0.78 in B (not 20). B is expected to drop.
3. **`H` fixed now.** The sketch had the census recompute the rung constants; here they are print-only, so no threshold
   is set by data.
4. **Pinned champion only.** The sketch's unit needed visible predictions from both se0 and the pinned se1. LT14 reads
   `P` only, with the freeze-time pin and the declared rule for changes (1.3). se1 is not read.
5. **Scope by the pinned classifiers on the sidecar** (LT13 1.4) in place of the engine's `category`, because after the
   fee step `fee_category` is mostly `other:zero_fees`. The confusion is printed (10.8).
6. **A binding placebo** (the shuffled prediction file, 1.9). The sketch had F only.
7. **Outcome classes and worst-case bounds** (1.6), the horizon rule (S45), and the latency print (1.4).
8. **MDE and F-MDE gates at the 0.5c floor**, and **Unavailable floors** (1.10).
9. **`|s|` decile kept** as the sketch wrote it, although the map counted the signed decile [map]. The census re-counts it.

## 5. `attrlimit_lt14`: request text for `signal_engine/CANDIDATES.md` (to be filed at the freeze; not applied; CANDIDATES not edited here)
> **LT14 request (CH262; filed at LT14's design-text freeze).** No token: LT14 builds no feature, family or model. One
> **attribution limit `attrlimit_lt14`** (`kind: attribution_limit`) until **the LT14 date**. The LT14 date is the later of
> 2027-01-03T00:00Z and LT14's analysis commit (ordered lane: the later of 2027-03-08T00:00Z and the analysis commit). It
> is moved later only by a ledger line.
> - **Models:** the pinned champion `P` (named at the freeze by `model_id` and `spec_sha256`).
> - **Scope:** no public display (website feed, `/lab` dashboard, `dashboard.json`, any shared document or chart) of
>   `P`'s **realised gross in cents**, either by liquidity tier or for its top `|s|` (or signed) decile, and no cents-valued
>   economic summary of `P`'s signals by tier. That covers the mean move in the predicted direction, the hit-rate-times-move
>   products, and net-of-cost figures.
> - **Unchanged:** the engine's log-loss, Brier, calibration and AUC leaderboard, the promotion rule and the per-market
>   `se-feed-v1` signal-strength display stay as they are.
> - `no_broad_families: []`.
> - **Pre-freeze hold:** if any such cents-by-tier number for `P` is computed or shown before the freeze, the ledger
>   records the first one and LT14 carries *informed (engine)*.
> - A census drop of both tiers withdraws the limit with a ledger line. An engine result never changes an LT14 verdict;
>   an LT14 verdict never promotes a model.

## 6. Jobs (described in text only; no queue file, no code in this commit)
1. **Schema pre-check** (light): column names and types of `predictions/`, `quotes/`, `features/`, the predictions log
   and the sidecar fields of 1.2, plus `P`'s registry sha. It is committed before the census code freeze and reads no value.
2. **Seal** (light, once): the sha256 list of the census inputs (3), after 2026-11-17T08:31Z.
3. **Census `CC14`** (counts only, once; `net` lane, `mem_mb` < 500 planned; the peak RSS is measured and the job is
   refused above 800 MB; the CH269 map peaked at 558.8 MB against a 450 MB spec). It streams captures one at a time.
4. **Size check** (once; `cpu` lane; only if a tier survives): 2,000 worlds, seed 20261814.
5. **Window reader** (cron every 2 h, light): the write-once extraction of 1.14, with the lag guard and the one-shot
   restore.
6. **`ops-stats`** (any time): counts only (1.7).
7. **Analysis** (once, on or after the analysis date, `--out` required): primary, Holm, F, placebo, labels, secondaries,
   economics.

Modules to be written later, in new files only: `backend/astrolabe/research_lab/live_tests14.py`,
`backend/scripts/run_live_tests14.py`, `backend/tests/unit/test_research_lab_live_tests14.py` (synthetic only). No
signal-engine code or E026 frozen file is touched.

## 7. Priors (the designer's judgement, not measurements)
- **P(census):** A **0.80**. The map's signed decile clears the count line with margin, and the MDE is far under the floor.
  The risks are the `|s|` decile's tier split, an `L` or scope surprise, and `P`'s coverage. B **0.02**: its map mean is
  0.78 a capture against 10, and its F-MDE fails even at 10.
- **P(no LT14 test) = 1 - P(A or B survives) about 0.20.** That is `0.20 x 0.98` for the census alone. It excludes the
  chance that R1 refuses the design or that registration slips past both lanes (about 0.05 more).
- **Given A registered:**
  - P(Supported) **0.08**: round 19's P(clears 1.30c) 0.10, times about 0.8 for F and the placebo;
  - P(Contradicted, below the rung) **0.75**;
  - P(Inconclusive) 0.12;
  - P(Unavailable) 0.05.
- P(`gbar` clears 0.65c) about 0.35 (round 19). P(M1 *spread-scaling consistent*) about 0.6.
- **Given Supported, P(the number holds on a second prospective window) 0.4** (round 19's P(replicates)).

## 8. What LT14 can and cannot say
**It can say:**
- whether the pinned champion's strongest 2 h directional calls in the 10k-100k tier moved, at the mids the engine
  recorded, by more than the most optimistic maker cost the programme has measured (1.30c), over 21 prospective days,
  with event- and day-robust uncertainty;
- by how much the gross falls short of each rung on the cost ladder (M3);
- whether the gross scales with the spread (M1, the stale-side reading);
- whether the engine's flat calls pick books that stay inside the half-spread (M2);
- how much attrition and latency could move the number.

**It cannot say:**
- anything about fills, queue position, signal-conditional adverse selection, size beyond the touch, the exit leg,
  inventory risk, rewards or rebates. A gross over a rung is necessary for a maker route, not sufficient;
- anything about another champion, another horizon (6 h, 24 h, `res_7d`), another window or season, or a later fee regime;
- anything about the >= 100k tier, unless it unexpectedly enters;
- that the champion is uninformative if the gross is below the rung. Accuracy in log loss is the engine's own yardstick
  and is untouched.

A Supported primary is an exploratory prospective finding that can at most nominate a separately registered maker design
with fills measured on its own signal. A Contradicted primary is the programme's answer to "is the current champion's top
decile worth anything at the touch over 2 h": not at the rung, by the printed margin.

## 9. Disclosures
- **Read to write this file:**
  - `CLAUDE.md`, `AGENTS.md`;
  - `CREATIVE_HYPOTHESES_2026-11-02.md` (sections 0-0.3, 1's lanes, CH262, CH269, 3);
  - `reviews/CH269_MAP_2026-10-30.md` (whole);
  - `seals/CH269_map_q0730.json` (section `champion_top_decile_ch262`, plus `decisions`, `span`, `not_mapped`,
    `captures_engine`);
  - `census_map_ch269.py` l. 836-870 (the decile definition only);
  - `COST_MODEL.md` (sections 4-8);
  - `signal_engine/NORTH_STAR.md`;
  - `signal_engine/DESIGN_V1.md` (sections 1-6, 20, 28, 30, 33);
  - `signal_engine/STATUS.md` (head);
  - `signal_engine/CANDIDATES.md` (the LT13 request block and the round-19 LT14 note);
  - `backend/astrolabe/signal_engine/features.py` (column names and the quotes frame only);
  - `LIVE_TESTS_13.md` (sections 0-1.14, 6, 8-11), `LIVE_TESTS_12.md` (headings and window lines);
  - `EXPERIMENT_LEDGER.md` (header and the round-19 / CH269 lines).

  No host, network, `ssh`, `data-dumps`, census output, prediction value, target or P&L was read.
- **Seen before the gates:** the CH269 counts above [map]; the engine's STATUS lines (log-loss leads, not by tier or in
  cents).
- **Not known at the planned freeze:** LT12's census output; E015, E022, LT9-LT13 results; whether a promotion happens on
  about 11-04.

### 9.1 Values declared now and their sources
| Value | Where | Source | Informed by CH269? |
|---|---|---|---|
| `H_A` 1.30c, `H_B` 0.50c | 1.8 | `COST_MODEL.md` 5 (maker both legs, independent) and 4 (>= 100k half-spread p50) | no |
| decile by `\|s\|`, all tiers pooled, ties by `market_id` | 1.5 | round 19 | the map's signed reading seen |
| A count line 100 a capture; B 10 a capture and 40 markets | 3 | round 19 | the A line drafted the test [map] |
| unavailable gap 10 points | 3 | round 19 | values seen (0.16 points) [map] |
| non-stationarity 0.25; venue clock 50%; series family 40%; `G_eff` 15 | 3 | rounds 14-18 and LT13 conventions | values seen [map] |
| `DE_gate` floor 5.0; DE 31 beside it | 2, 3 | LT13 1.0 | tenure seen [map] |
| MDE and F-MDE <= 0.5c | 3 | rule 8 mid floor | no |
| horizon 2 h +/- 15 min | 1.4 | round 19 S45 | no |
| attrition-differential 2 points | 1.6 | LT13 1.5 | gap values seen [map] |
| Unavailable A 15,000 / 200 / 10 days / 80% files; B 2,000 / 40 | 1.10 | F-MDE arithmetic; conventions | no |
| placebo two-sided half; F half | 1.9 | LT12 R1 MUST 5; LT7 | no |
| seed 20261814 | 1.8, 1.9 | unused (git grep, 2026-10-30) | no |
| census span `[11-07, 11-17)` | 3 | round 19 section 3 | no |

## 10. Open questions for the challenger (R1), the riskiest first
1. **The parallel lane.** May LT14 run on 2026-12-10..12-31 beside LT12, given disjoint objects but overlapping markets
   (two-member neg-risk members can be decile units)? Or must it take the ordered lane (2027-02-12..03-05)?
2. **`|s|` versus the map's signed decile.** CH269 counted the top decile of signed `s` (up calls only). The design keeps
   `|s|`, and its tier split is unprobed. Is the drafting decision ("175 >= 100") still valid for the `|s|` decile, or is
   it re-decided only at the census (the designer's reading)?
3. **Binding F on an economic level.** F rejects a gross that persists at 4-6 h, which is a slow diffusion that a holder
   could still capture. It is conservative, but is it the right condition for a rung test, or should F be a label here?
4. **The shuffled-file placebo as a binding two-sided condition.** A common directional drift aligned with the decile's
   sign mix is a real component of the gross. Should it fail Supported (designer: yes, because the claim is the engine's
   unit-level signal), or only carry a label?
5. **The rung's provenance.** 1.30c was derived for F4 / F5's inputs (mean spread 2.68c, fee 0.84c round trip), not for
   the 10k-100k top decile. Under the served fee of 0 it would be lower. Is a fixed constant from the cost model correct,
   with the recomputed rungs print-only?
6. **Latency.** `g` starts at capture k's mid, before the prediction is written. Is "the engine's claim at its label
   origin" with a latency sensitivity acceptable, or must the primary exclude units above a latency bound?
7. **B's place in the family.** On the map, B cannot pass its count or F-MDE lines. Keep k <= 2 as round 19 registered
   it, or declare k = 1 now and make B a reported arm?
8. **Scope reading.** Pinned classifiers on the sidecar (needs the sidecar extraction) versus the engine's own `category`
   (`other:zero_fees` for most non-sports rows after 10-20).
9. **`costs.py`.** It is E026-frozen. Is a read-only import acceptable (its sha unchanged), or must the cost formulas be
   vendored (the designer's default)?
10. **The CH269 fee-class split** totals 1,059 units against 126,477 decile units. Is that a map defect that needs a
    ledger note before the census relies on the same code path?
11. **Champion pin timing.** Is the freeze-time champion the right `P` if a promotion happens between the freeze and
    `REGISTERED_UTC`, or should the pin move to the registration commit (after the census, so `P` could change after its
    census)? The designer's answer: the freeze, so the census and the window read the same model.

## 11. Proposed registry entry and draft ledger block (DRAFT; not applied)
**`docs/research_lab/lab_dashboard/registry.json`, `live_tests` (proposed, not applied):**
```json
{
 "id": "LT14",
 "title": "Live tests 14: the engine at the touch (planned)",
 "plain": "One planned live test from ideas round 19: do the signal engine's strongest two-hour calls in mid-liquidity markets move, at the prices the engine recorded, by more than the cheapest trading cost the programme has measured? A counting check on 7-17 Nov data comes first; the expected answer is no.",
 "batch": "LT14",
 "family": "economic",
 "stage": "idea",
 "status": "waiting",
 "verdict": "pending",
 "effect": null,
 "next": "Challenger review of the draft; counting check on 7-17 Nov engine files; collection proposed 10-31 Dec (or 12 Feb - 5 Mar 2027)",
 "next_date": "2026-12-10",
 "candidate": false,
 "sources": {"verdict": "docs/research_lab/LIVE_TESTS_14.md (DRAFT)"},
 "stage_results": {"idea": "pending"},
 "reached": ["idea"]
}
```

**Ledger block (draft):**
```
## LT14 design draft, 2026-10-30 (experiments autopilot; DRAFT, nothing counted)
- LIVE_TESTS_14.md drafted on feat/live-tests-14 (CH262, the engine at the touch): one Holm family k <= 2 (10k-100k at
  1.30c, >= 100k at 0.50c), pinned champion only, engine write-once files, census on [2026-11-07, 11-17) labelled
  informed (LT12 census); window 2026-12-10..12-31 (parallel with LT12, challenger to rule) else 2027-02-12..03-05;
  attrlimit_lt14 requested at the freeze. CH269: A 175 a capture (signed decile), B 0.78 (expected census_dropped).
  Priors: P(census) A 0.80 / B 0.02; P(no test) about 0.20. Nothing counted; no code; not frozen.
```
